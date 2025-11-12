import discord
from discord.ext import commands
import requests
import json
import os
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any, Optional
import asyncio
import random
import logging
import traceback
import sys
import time
from pathlib import Path

# Try to import pnwkit, handle gracefully if not available
try:
    import pnwkit
    PNWKIT_AVAILABLE = True
    PNWKIT_ERROR = None
    PNWKIT_SOURCE = "system"
except ImportError as e:
    # Try to use local pnwkit if system version is not available
    try:
        import sys
        import os
        local_packages_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'local_packages')
        if local_packages_dir not in sys.path:
            sys.path.insert(0, local_packages_dir)
        
        import pnwkit
        PNWKIT_AVAILABLE = True
        PNWKIT_ERROR = None
        PNWKIT_SOURCE = "local"
    except ImportError as local_e:
        pnwkit = None
        PNWKIT_AVAILABLE = False
        PNWKIT_ERROR = f"System: {str(e)}, Local: {str(local_e)}"
        PNWKIT_SOURCE = "none"
    except Exception as local_e:
        pnwkit = None
        PNWKIT_AVAILABLE = False
        PNWKIT_ERROR = f"System: {str(e)}, Local unexpected error: {str(local_e)}"
        PNWKIT_SOURCE = "none"
except Exception as e:
    pnwkit = None
    PNWKIT_AVAILABLE = False
    PNWKIT_ERROR = f"Unexpected error: {str(e)}"
    PNWKIT_SOURCE = "none"

# Import json for cache reading
import json

# Import config for API keys and settings
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import PANDW_API_KEY, CYBERTRON_ALLIANCE_ID, PRIME_BANK_ALLIANCE_ID
from Systems.user_data_manager import UserDataManager

# Import calculation utilities
from .calc import (
    get_active_nations,
    calculate_nation_statistics,
    calculate_alliance_statistics,
    calculate_full_mill_data,
    calculate_military_purchase_limits,
    get_nation_specialty,
    calculate_combat_score,
    has_project,
    calculate_improvements_data
)
 
# Import centralized query system for direct API access
try:
    from .query import create_query_instance
except ImportError:
    try:
        from Systems.PnW.MA.query import create_query_instance
    except ImportError:
        create_query_instance = None

# Import Bloc AllianceManager with alias to avoid name clash
try:
    from .bloc import AllianceManager as BlocAllianceManager
except ImportError:
    try:
        from Systems.PnW.MA.bloc import AllianceManager as BlocAllianceManager
    except ImportError:
        BlocAllianceManager = None

# Import leadership role check from snipe.py
try:
    from Systems.PnW.snipe import leadership_role_check
except Exception:
    try:
        from snipe import leadership_role_check
    except Exception:
        def leadership_role_check():
            return commands.check(lambda ctx: True)

class FullMillView(discord.ui.View):
    """View for displaying Full Mill calculations and alliance data."""
    
    def __init__(self, author_id: int, bot: commands.Bot, alliance_cog: 'AllianceManager', nations: List[Dict] = None):
        super().__init__(timeout=300)  # 5 minute timeout
        self.author_id = author_id
        self.bot = bot
        self.alliance_cog = alliance_cog
        self.current_data = None
        self.current_nations = nations
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the interaction is from the command author."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ You cannot use this menu.")
            return False
        return True

    async def generate_full_mill_embed(self, nations: List[Dict] = None) -> discord.Embed:
        """Generate the full mill embed without handling interaction."""
        try:
            # Use provided nations or current nations
            current_nations = nations or self.current_nations
            
            if not current_nations:
                # Get alliance data based on guild
                guild_alliance_id = await self.alliance_cog.get_alliance_id_for_guild(self.guild)
                guild_nations = await self.alliance_cog.get_alliance_nations(guild_alliance_id)
                
                # Conditionally fetch Prime Bank data if configured and different
                prime_bank_nations = []
                if hasattr(self.alliance_cog, 'prime_bank_alliance_id') and self.alliance_cog.prime_bank_alliance_id and self.alliance_cog.prime_bank_alliance_id != guild_alliance_id:
                    prime_bank_nations = await self.alliance_cog.get_alliance_nations(self.alliance_cog.prime_bank_alliance_id)
                
                current_nations = (guild_nations or []) + (prime_bank_nations or [])
                if not current_nations:
                    return discord.Embed(
                        title="❌ No Alliance Data",
                        description="Failed to retrieve alliance data.",
                        color=discord.Color.red()
                    )
                self.current_nations = current_nations
            
            # Use ALL − Vacation Mode − APPLICANT for totals
            total_nations = len(current_nations)
            non_vm_non_app = [n for n in current_nations if (((n.get('vacation_mode_turns', 0) or 0) == 0) and ((n.get('alliance_position','') or '').strip().upper() != 'APPLICANT'))]
            
            # Calculate full mill data for ALL − VM − APPS
            full_mill_data = self.alliance_cog.calculate_full_mill_data(non_vm_non_app)
            
            # Create Full Mill embed
            embed = discord.Embed(
                title="🏭 Cybertr0n Military Analysis",
                description="Alliance military capacity and production analysis (ALL − Vacation Mode − APPS)",
                color=discord.Color.from_rgb(255, 140, 0)
            )
            
            # Overall statistics
            embed.add_field(
                name="📊 Overall Statistics",
                value=(
                    f"**Total Nations:** {total_nations}\n"
                    f"**Active Nations:** {full_mill_data['active_nations']}\n"
                    f"**Total Cities:** {full_mill_data['total_cities']:,}\n"
                    f"**Total Score:** {full_mill_data['total_score']:,}"
                ),
                inline=False
            )
            
            # Military Units - Current/Max
            embed.add_field(
                name="⚔️ Military Units",
                value=(
                    f"🪖 **Soldiers:** {full_mill_data['current_soldiers']:,}/{full_mill_data['max_soldiers']:,}\n"
                    f"🚙 **Tanks:** {full_mill_data['current_tanks']:,}/{full_mill_data['max_tanks']:,}\n"
                    f"🛩️ **Aircraft:** {full_mill_data['current_aircraft']:,}/{full_mill_data['max_aircraft']:,}\n"
                    f"⚓ **Ships:** {full_mill_data['current_ships']:,}/{full_mill_data['max_ships']:,}"
                ),
                inline=False
            )
            
            # Daily Production
            embed.add_field(
                name="🏭 Daily Production",
                value=(
                    f"🪖 **Soldiers:** {full_mill_data['daily_soldiers']:,}/day\n"
                    f"🚙 **Tanks:** {full_mill_data['daily_tanks']:,}/day\n"
                    f"🛩️ **Aircraft:** {full_mill_data['daily_aircraft']:,}/day\n"
                    f"⚓ **Ships:** {full_mill_data['daily_ships']:,}/day\n"
                    f"🚀 **Missiles:** {full_mill_data['daily_missiles']:,}/day\n"
                    f"☢️ **Nukes:** {full_mill_data['daily_nukes']:,}/day"
                ),
                inline=False
            )
            
            # Military unit gaps
            embed.add_field(
                name="⚔️ Units Needed",
                value=(
                    f"🪖 **Soldiers:** {full_mill_data['soldier_gap']:,}\n"
                    f"🚙 **Tanks:** {full_mill_data['tank_gap']:,}\n"
                    f"🛩️ **Aircraft:** {full_mill_data['aircraft_gap']:,}\n"
                    f"⚓ **Ships:** {full_mill_data['ship_gap']:,}"
                ),
                inline=False
            )
            
            import math
            embed.add_field(
                name="⏱️ Time to Max",
                value=(
                    f"🪖 **Soldiers:** {math.ceil(full_mill_data['max_soldier_days'])} days ({full_mill_data['max_soldier_nation']})\n"
                    f"🚙 **Tanks:** {math.ceil(full_mill_data['max_tank_days'])} days ({full_mill_data['max_tank_nation']})\n"
                    f"🛩️ **Aircraft:** {math.ceil(full_mill_data['max_aircraft_days'])} days ({full_mill_data['max_aircraft_nation']})\n"
                    f"⚓ **Ships:** {math.ceil(full_mill_data['max_ship_days'])} days ({full_mill_data['max_ship_nation']})"
                ),
                inline=False
            )
            
            embed.set_footer(text=f"Generated at {datetime.now().strftime('%H:%M:%S')} | Use Alliance Totals button to refresh data")
            
            return embed
            
        except Exception as e:
            self.alliance_cog._log_error(f"Error in generate_full_mill_embed: {e}", e, "FullMillView.generate_full_mill_embed")
            return discord.Embed(
                title="❌ Full Mill Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
    
    @discord.ui.button(label="Improvements", style=discord.ButtonStyle.secondary, emoji="🏗️")
    async def improvements_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show improvements breakdown for all alliance nations."""
        try:
            await interaction.response.defer()
            
            if not self.current_nations:
                # Fetch alliance data based on guild
                guild_alliance_id = await self.alliance_cog.get_alliance_id_for_guild(self.guild)
                nations = await self.alliance_cog.get_alliance_nations(guild_alliance_id)
                if not nations:
                    embed = discord.Embed(
                        title="❌ No Alliance Data",
                        description="Failed to retrieve alliance data.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)
                    return
                self.current_nations = nations
            
            # Create ImprovementsView and use its generator method
            view = ImprovementsView(self.author_id, self.bot, self.alliance_cog, self.current_nations)
            embed = await view.generate_improvements_embed(self.current_nations)
            
            # Update the message with Improvements embed and switch to ImprovementsView
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=view
            )
            
        except Exception as e:
            self.alliance_cog._log_error(f"Error in improvements_button: {e}", e, "FullMillView.improvements_button")
            embed = discord.Embed(
                title="❌ Improvements Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

    @discord.ui.button(label="Project Totals", style=discord.ButtonStyle.secondary, emoji="🧩")
    async def project_totals_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show project totals for active nations only (excludes Applicants & VM)."""
        try:
            await interaction.response.defer()

            if not self.current_nations:
                # Fetch alliance data based on guild
                guild_alliance_id = await self.alliance_cog.get_alliance_id_for_guild(self.guild)
                nations = await self.alliance_cog.get_alliance_nations(guild_alliance_id)
                if not nations:
                    embed = discord.Embed(
                        title="❌ No Alliance Data",
                        description="Failed to retrieve alliance data.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)
                    return
                self.current_nations = nations

            view = ProjectTotalsView(self.author_id, self.bot, self.alliance_cog, self.current_nations)
            embed = await view.generate_project_totals_embed(self.current_nations)

            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=view
            )
        except Exception as e:
            self.alliance_cog._log_error(f"Error in project_totals_button: {e}", e, "FullMillView.project_totals_button")
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")
    
    @discord.ui.button(label="Alliance Totals", style=discord.ButtonStyle.secondary, emoji="📊")
    async def alliance_totals_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show alliance totals and statistics."""
        try:
            await interaction.response.defer()
            
            if not self.current_nations:
                # Fetch alliance data based on guild
                guild_alliance_id = await self.alliance_cog.get_alliance_id_for_guild(self.guild)
                nations = await self.alliance_cog.get_alliance_nations(guild_alliance_id)
                if not nations:
                    embed = discord.Embed(
                        title="❌ No Alliance Data",
                        description="Failed to retrieve alliance data.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)
                    return
                self.current_nations = nations
            
            # Create AllianceTotalsView and use its generator method
            view = AllianceTotalsView(self.author_id, self.bot, self.alliance_cog, self.current_nations)
            embed = await view.generate_alliance_totals_embed(self.current_nations)
            
            # Update the message with Alliance Totals embed and switch to AllianceTotalsView
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=view
            )
            
        except Exception as e:
            self.alliance_cog._log_error(f"Error in alliance_totals_button: {e}", e, "FullMillView.alliance_totals_button")
            embed = discord.Embed(
                title="❌ Alliance Totals Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

class AllianceTotalsView(discord.ui.View):
    """View for displaying Alliance Totals with Full Mill button."""
    
    def __init__(self, author_id: int, bot: commands.Bot, alliance_cog: 'AllianceManager', nations: List[Dict] = None):
        super().__init__(timeout=300)  # 5 minute timeout
        self.author_id = author_id
        self.bot = bot
        self.alliance_cog = alliance_cog
        self.current_nations = nations
        # Ensure compatibility with bloc-level components that may access bloc_data
        self.bloc_data = {}
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the interaction is from the command author."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ You cannot use this menu.")
            return False
        return True
        
    async def generate_alliance_totals_embed(self, nations: List[Dict] = None) -> discord.Embed:
        """Generate the alliance totals embed without handling interaction."""
        try:
            current_nations = nations or self.current_nations
            if not current_nations:
                # Get alliance data based on guild
                guild_alliance_id = await self.alliance_cog.get_alliance_id_for_guild(self.guild)
                guild_nations = await self.alliance_cog.get_alliance_nations(guild_alliance_id)
                
                # Conditionally fetch Prime Bank data if configured and different
                prime_bank_nations = []
                if hasattr(self.alliance_cog, 'prime_bank_alliance_id') and self.alliance_cog.prime_bank_alliance_id and self.alliance_cog.prime_bank_alliance_id != guild_alliance_id:
                    prime_bank_nations = await self.alliance_cog.get_alliance_nations(self.alliance_cog.prime_bank_alliance_id)
                
                current_nations = (guild_nations or []) + (prime_bank_nations or [])
                if not current_nations:
                    return discord.Embed(
                        title="❌ No Alliance Data",
                        description="Failed to retrieve alliance data.",
                        color=discord.Color.red()
                    )
                self.current_nations = current_nations
            
            # Get active nations for statistics
            active_nations = self.alliance_cog.get_active_nations(current_nations)
            # Build simplified active set: ALL - Vacation Mode - APPLICANT
            apps = [n for n in current_nations if ((n.get('alliance_position','') or '').strip().upper() == 'APPLICANT')]
            non_vm_non_app = [n for n in current_nations if (((n.get('vacation_mode_turns', 0) or 0) == 0) and ((n.get('alliance_position','') or '').strip().upper() != 'APPLICANT'))]
            stats_simple = self.alliance_cog.calculate_alliance_statistics(non_vm_non_app)
            
            # Calculate nation statistics for all nations (including inactive)
            nation_stats = self.alliance_cog.calculate_nation_statistics(current_nations)
            
            # Calculate averages manually based on simplified active set
            avg_score = stats_simple['total_score'] / stats_simple['total_nations'] if stats_simple['total_nations'] > 0 else 0
            avg_cities = stats_simple['total_cities'] / stats_simple['total_nations'] if stats_simple['total_nations'] > 0 else 0
            
            # Create comprehensive statistics embed
            embed = discord.Embed(
                title="📊 Cybertr0n Alliance Totals",
                description="Comprehensive alliance statistics and capabilities",
                color=discord.Color.from_rgb(0, 150, 255)
            )
            
            embed.add_field(
                name="📊 Nation Counts",
                value=(
                    f"📇 **Total:** {len(current_nations)}\n"
                    f"✅ **Active:** {len(non_vm_non_app)}\n"
                    f"📝 **Applicants:** {len(apps)}\n"
                    f"🧮 **Total Score:** {stats_simple['total_score']:,}\n"
                    f"⚖️ **Average Score:** {avg_score:,.0f}\n"
                    f"🌇 **Total Cities:** {stats_simple['total_cities']:,}\n"
                    f"🌆 **Average Cities:** {avg_cities:.1f}"
                ),
                inline=False
            )
            
            # Calculate resource totals for active nations (excluding vacation mode, applicants, and 14+ days inactive)
            filtered_nations = get_active_nations(current_nations)
            
            total_money = sum(n.get('money', 0) or 0 for n in filtered_nations)
            total_credits = sum(n.get('credits', 0) or 0 for n in filtered_nations)
            total_gasoline = sum(n.get('gasoline', 0) or 0 for n in filtered_nations)
            total_munitions = sum(n.get('munitions', 0) or 0 for n in filtered_nations)
            total_steel = sum(n.get('steel', 0) or 0 for n in filtered_nations)
            total_aluminum = sum(n.get('aluminum', 0) or 0 for n in filtered_nations)
            total_food = sum(n.get('food', 0) or 0 for n in filtered_nations)
            total_coal = sum(n.get('coal', 0) or 0 for n in filtered_nations)
            total_oil = sum(n.get('oil', 0) or 0 for n in filtered_nations)
            total_uranium = sum(n.get('uranium', 0) or 0 for n in filtered_nations)
            total_iron = sum(n.get('iron', 0) or 0 for n in filtered_nations)
            total_bauxite = sum(n.get('bauxite', 0) or 0 for n in filtered_nations)
            total_lead = sum(n.get('lead', 0) or 0 for n in filtered_nations)
            
            resources_held = (
                f"**Money:** ${total_money:,}\n"
                f"**Credits:** {total_credits:,}\n"
                f"**Gasoline:** {total_gasoline:,}\n"
                f"**Munitions:** {total_munitions:,}\n"
                f"**Steel:** {total_steel:,}\n"
                f"**Aluminum:** {total_aluminum:,}\n"
                f"**Food:** {total_food:,}\n"
                f"**Coal:** {total_coal:,}\n"
                f"**Oil:** {total_oil:,}\n"
                f"**Uranium:** {total_uranium:,}\n"
                f"**Iron:** {total_iron:,}\n"
                f"**Bauxite:** {total_bauxite:,}\n"
                f"**Lead:** {total_lead:,}"
            )
            embed.add_field(name="💰 Resources Held", value=resources_held, inline=False)
            
            # Add categories directly to main embed (replacing old buttons)
            from datetime import datetime as _dt_dt, timedelta as _dt_td, timezone as _dt_tz
            now = _dt_dt.now(_dt_tz.utc)

            def _days_inactive(n):
                s = n.get('last_active')
                if not s:
                    return None
                try:
                    if isinstance(s, str):
                        la = s.strip()
                        if la.endswith('Z'):
                            la = la.replace('Z', '+00:00')
                        dt = _dt_dt.fromisoformat(la)
                    else:
                        dt = s
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=_dt_tz.utc)
                    else:
                        dt = dt.astimezone(_dt_tz.utc)
                    return (now - dt).days
                except Exception:
                    return None

            def _make_links(items, with_days=False):
                links = []
                for n in items:
                    nid = n.get('id')
                    name = n.get('nation_name', 'Unknown')
                    
                    if nid:
                        # Add nation link with optional days inactive (no Discord info)
                        if with_days:
                            d = _days_inactive(n)
                            if isinstance(d, int):
                                links.append(f"[{name}](https://politicsandwar.com/nation/id={nid}) ({d}d)")
                            else:
                                links.append(f"[{name}](https://politicsandwar.com/nation/id={nid})")
                        else:
                            links.append(f"[{name}](https://politicsandwar.com/nation/id={nid})")
                
                links.sort(key=lambda x: x.lower())
                value = ""
                used = 0
                for link in links:
                    add = ("\n" if value else "") + link  # Single newline for proper spacing between nations
                    if len(value) + len(add) > 1000:
                        remaining = len(links) - used
                        if remaining > 0:
                            value = value + ("\n" if value else "") + f"... and {remaining} more"
                        break
                    value += add
                    used += 1
                if not value:
                    value = "None"
                return value

            # Compute categories - exclude Vacation Mode, APPLICANT nations, and 14+ days inactive
            filtered_nations = get_active_nations(current_nations)
            grey = [n for n in filtered_nations if (n.get('color', '') or '').strip().upper() in ('GREY', 'GRAY')]
            beige = [n for n in filtered_nations if (n.get('color', '') or '').strip().upper() == 'BEIGE']
            vm = [n for n in current_nations if (n.get('vacation_mode_turns', 0) or 0) > 0 and ((n.get('alliance_position', '') or '').strip().upper() != 'APPLICANT')]

            seven_to_thirteen = []
            fourteen_plus = []
            for n in non_vm_non_app:
                d = _days_inactive(n)
                if isinstance(d, int):
                    if 7 <= d < 14:
                        seven_to_thirteen.append(n)
                    elif d >= 14:
                        fourteen_plus.append(n)

            non_applicants = [n for n in current_nations if ((n.get('alliance_position','') or '').strip().upper() != 'APPLICANT')]
            embed.add_field(name=f"⏲️ GREY Nations - Total: {len(grey)}", value=_make_links(grey), inline=False)
            embed.add_field(name=f"🩼 BEIGE Nations - Total: {len(beige)}", value=_make_links(beige), inline=False)
            embed.add_field(name=f"🏖️ Vacation Mode - Total: {len(vm)}", value=_make_links(vm), inline=False)
            embed.add_field(name=f"⏰ Inactive 7–13 Days - Total: {len(seven_to_thirteen)}", value=_make_links(seven_to_thirteen, with_days=True), inline=False)
            embed.add_field(name=f"📅 Inactive 14+ Days - Total: {len(fourteen_plus)}", value=_make_links(fourteen_plus, with_days=True), inline=False)
            
            embed.set_footer(text=f"Generated at {datetime.now().strftime('%H:%M:%S')} | Use other buttons to view different data")
            
            return embed
            
        except Exception as e:
            self.alliance_cog._log_error(f"Error in generate_alliance_totals_embed: {e}", e, "AllianceTotalsView.generate_alliance_totals_embed")
            return discord.Embed(
                title="❌ Alliance Totals Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
    
    @discord.ui.button(label="Military", style=discord.ButtonStyle.primary, emoji="⚔️")
    async def full_mill_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show full military capacity analysis."""
        try:
            await interaction.response.defer()
            
            if not self.current_nations:
                # Fetch alliance data based on guild
                guild_alliance_id = await self.alliance_cog.get_alliance_id_for_guild(self.guild)
                nations = await self.alliance_cog.get_alliance_nations(guild_alliance_id)
                if not nations:
                    embed = discord.Embed(
                        title="❌ No Alliance Data",
                        description="Failed to retrieve alliance data.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)
                    return
                self.current_nations = nations
            
            # Create FullMillView and generate the embed
            view = FullMillView(self.author_id, self.bot, self.alliance_cog, self.current_nations)
            embed = await view.generate_full_mill_embed(self.current_nations)
            
            # Update the message with Full Mill embed and switch to FullMillView
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=view
            )
            
        except Exception as e:
            self.alliance_cog._log_error(f"Error in full_mill_button: {e}", e, "AllianceTotalsView.full_mill_button")
            embed = discord.Embed(
                title="❌ Full Mill Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
    
    @discord.ui.button(label="Improvements", style=discord.ButtonStyle.secondary, emoji="🏗️")
    async def improvements_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show improvements breakdown for all alliance nations."""
        try:
            await interaction.response.defer()
            
            if not self.current_nations:
                # Fetch alliance data based on guild
                guild_alliance_id = await self.alliance_cog.get_alliance_id_for_guild(self.guild)
                nations = await self.alliance_cog.get_alliance_nations(guild_alliance_id)
                if not nations:
                    embed = discord.Embed(
                        title="❌ No Alliance Data",
                        description="Failed to retrieve alliance data.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)
                    return
                self.current_nations = nations
            
            # Create ImprovementsView and use its generator method
            view = ImprovementsView(self.author_id, self.bot, self.alliance_cog, self.current_nations)
            embed = await view.generate_improvements_embed(self.current_nations)
            
            # Update the message with Improvements embed and add navigation buttons
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=view
            )
            
        except Exception as e:
            self.alliance_cog._log_error(f"Error in improvements_button: {e}", e, "AllianceTotalsView.improvements_button")
            embed = discord.Embed(
                title="❌ Improvements Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

    @discord.ui.button(label="Project Totals", style=discord.ButtonStyle.secondary, emoji="🧩")
    async def project_totals_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show project totals for active nations only (excludes Applicants & VM)."""
        try:
            await interaction.response.defer()

            if not self.current_nations:
                # Fetch alliance data based on guild
                guild_alliance_id = await self.alliance_cog.get_alliance_id_for_guild(self.guild)
                nations = await self.alliance_cog.get_alliance_nations(guild_alliance_id)
                if not nations:
                    embed = discord.Embed(
                        title="❌ No Alliance Data",
                        description="Failed to retrieve alliance data.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)
                    return
                self.current_nations = nations

            view = ProjectTotalsView(self.author_id, self.bot, self.alliance_cog, self.current_nations)
            embed = await view.generate_project_totals_embed(self.current_nations)

            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=view
            )
        except Exception as e:
            self.alliance_cog._log_error(f"Error in project_totals_button: {e}", e, "AllianceTotalsView.project_totals_button")
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")

    

class ImprovementsView(discord.ui.View):
    """View for displaying Improvements Breakdown with navigation buttons."""
    
    def __init__(self, author_id: int, bot: commands.Bot, alliance_cog: 'AllianceManager', nations: List[Dict] = None):
        super().__init__(timeout=300)  # 5 minute timeout
        self.author_id = author_id
        self.bot = bot
        self.alliance_cog = alliance_cog
        self.current_nations = nations
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the interaction is from the command author."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ You cannot use this menu.")
            return False
        return True
        
    async def generate_improvements_embed(self, nations: List[Dict] = None) -> discord.Embed:
        """Generate the improvements breakdown embed without handling interaction."""
        try:
            current_nations = nations or self.current_nations
            if not current_nations:
                # Get alliance data based on guild
                guild_alliance_id = await self.alliance_cog.get_alliance_id_for_guild(self.guild)
                guild_nations = await self.alliance_cog.get_alliance_nations(guild_alliance_id)
                
                # Conditionally fetch Prime Bank data if configured and different
                prime_bank_nations = []
                if hasattr(self.alliance_cog, 'prime_bank_alliance_id') and self.alliance_cog.prime_bank_alliance_id and self.alliance_cog.prime_bank_alliance_id != guild_alliance_id:
                    prime_bank_nations = await self.alliance_cog.get_alliance_nations(self.alliance_cog.prime_bank_alliance_id)
                
                current_nations = (guild_nations or []) + (prime_bank_nations or [])
                if not current_nations:
                    return discord.Embed(
                        title="❌ No Alliance Data",
                        description="Failed to retrieve alliance data.",
                        color=discord.Color.red()
                    )
                self.current_nations = current_nations
            
            # Use ALL − Vacation Mode − APPLICANT for totals
            active_nations = [n for n in current_nations if (((n.get('vacation_mode_turns', 0) or 0) == 0) and ((n.get('alliance_position','') or '').strip().upper() != 'APPLICANT'))]

            # Calculate improvements data for ALL − VM − APPS
            improvements_data = await self.alliance_cog.calculate_improvements_data(active_nations)
            
            # Create Improvements Breakdown embed
            embed = discord.Embed(
                title="🏗️ Cybertr0n Improvements Breakdown",
                description="Total improvements across ALL − Vacation Mode − APPS",
                color=discord.Color.from_rgb(34, 139, 34)
            )
            
            # Power Plants
            embed.add_field(
                name="⚡ Power Plants",
                value=(
                    f"**Coal Power Plant:** {improvements_data['coalpower']:,}\n"
                    f"**Oil Power Plant:** {improvements_data['oilpower']:,}\n"
                    f"**Nuclear Power Plant:** {improvements_data['nuclearpower']:,}\n"
                    f"**Wind Power Plant:** {improvements_data['windpower']:,}\n"
                    f"**Total:** {improvements_data['total_power']:,}"
                ),
                inline=False
            )
            
            # Raw Resources
            embed.add_field(
                name="⛏️ Raw Resources",
                value=(
                    f"**Oil Well:** {improvements_data['oilwell']:,}\n"
                    f"**Coal Mine:** {improvements_data['coalmine']:,}\n"
                    f"**Uranium Mine:** {improvements_data['uramine']:,}\n"
                    f"**Iron Mine:** {improvements_data['ironmine']:,}\n"
                    f"**Bauxite Mine:** {improvements_data['bauxitemine']:,}\n"
                    f"**Lead Mine:** {improvements_data['leadmine']:,}\n"
                    f"**Farm:** {improvements_data['farm']:,}"
                ),
                inline=False
            )
            
            # Manufacturing
            embed.add_field(
                name="🏭 Manufacturing",
                value=(
                    f"**Gas Refinery:** {improvements_data['gasrefinery']:,}\n"
                    f"**Steel Mill:** {improvements_data['steelmill']:,}\n"
                    f"**Aluminum Refinery:** {improvements_data['aluminumrefinery']:,}\n"
                    f"**Munitions Factory:** {improvements_data['munitionsfactory']:,}"
                ),
                inline=False
            )
            
            # Civil
            embed.add_field(
                name="🏛️ Civil",
                value=(
                    f"**Police Station:** {improvements_data['policestation']:,}\n"
                    f"**Hospital:** {improvements_data['hospital']:,}\n"
                    f"**Subway:** {improvements_data['subway']:,}\n"
                    f"**Recycling Center:** {improvements_data['recyclingcenter']:,}"
                ),
                inline=False
            )
            
            # Commerce
            embed.add_field(
                name="💰 Commerce",
                value=(
                    f"**Bank:** {improvements_data['bank']:,}\n"
                    f"**Supermarket:** {improvements_data['supermarket']:,}\n"
                    f"**Shopping Mall:** {improvements_data['shopping_mall']:,}\n"
                    f"**Stadium:** {improvements_data['stadium']:,}"
                ),
                inline=False
            )
            
            # Military
            embed.add_field(
                name="⚔️ Military",
                value=(
                    f"**Barracks:** {improvements_data['barracks']:,}\n"
                    f"**Factory:** {improvements_data['factory']:,}\n"
                    f"**Hangar:** {improvements_data['hangar']:,}\n"
                    f"**Drydock:** {improvements_data['drydock']:,}"
                ),
                inline=False
            )
            
            # Summary Statistics
            embed.add_field(
                name="📊 Summary",
                value=(
                    f"**Total Improvements:** {improvements_data['total_improvements']:,}\n"
                    f"**Total Cities:** {improvements_data['total_cities']:,}\n"
                    f"**Avg per City:** {improvements_data['avg_per_city']:.1f}\n"
                    f"**Active Nations:** {improvements_data['active_nations']:,}"
                ),
                inline=False
            )
            
            embed.set_footer(text=f"Generated at {datetime.now().strftime('%H:%M:%S')} | Use other buttons to view different data")
            
            return embed
            
        except Exception as e:
            self.alliance_cog._log_error(f"Error in generate_improvements_embed: {e}", e, "ImprovementsView.generate_improvements_embed")
            return discord.Embed(
                title="❌ Improvements Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
    
    @discord.ui.button(label="Alliance Totals", style=discord.ButtonStyle.secondary, emoji="📊")
    async def alliance_totals_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show alliance totals and statistics."""
        try:
            await interaction.response.defer()
            
            if not self.current_nations:
                # Fetch alliance data if not already loaded
                nations = await self.alliance_cog.get_alliance_nations(self.alliance_cog.cybertron_alliance_id)
                if not nations:
                    embed = discord.Embed(
                        title="❌ No Alliance Data",
                        description="Failed to retrieve alliance data.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)
                    return
                self.current_nations = nations
            
            # Create AllianceTotalsView and use its generator method
            view = AllianceTotalsView(self.author_id, self.bot, self.alliance_cog, self.current_nations)
            embed = await view.generate_alliance_totals_embed(self.current_nations)
            
            # Update the message with Alliance Totals embed and switch to AllianceTotalsView
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=view
            )
            
        except Exception as e:
            self.alliance_cog._log_error(f"Error in alliance_totals_button: {e}", e, "ImprovementsView.alliance_totals_button")
            embed = discord.Embed(
                title="❌ Alliance Totals Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

    @discord.ui.button(label="Project Totals", style=discord.ButtonStyle.secondary, emoji="🧩")
    async def project_totals_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show project totals for active nations only (excludes Applicants & VM)."""
        try:
            await interaction.response.defer()

            if not self.current_nations:
                nations = await self.alliance_cog.get_alliance_nations(self.alliance_cog.cybertron_alliance_id)
                if not nations:
                    embed = discord.Embed(
                        title="❌ No Alliance Data",
                        description="Failed to retrieve alliance data.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)
                    return
                self.current_nations = nations

            view = ProjectTotalsView(self.author_id, self.bot, self.alliance_cog, self.current_nations)
            embed = await view.generate_project_totals_embed(self.current_nations)

            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=view
            )
        except Exception as e:
            self.alliance_cog._log_error(f"Error in project_totals_button: {e}", e, "ImprovementsView.project_totals_button")
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")
    
    @discord.ui.button(label="Military", style=discord.ButtonStyle.secondary, emoji="🏭")
    async def full_mill_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show full military capacity analysis."""
        try:
            await interaction.response.defer()
            
            if not self.current_nations:
                # Fetch alliance data if not already loaded
                nations = await self.alliance_cog.get_alliance_nations(self.alliance_cog.cybertron_alliance_id)
                if not nations:
                    embed = discord.Embed(
                        title="❌ No Alliance Data",
                        description="Failed to retrieve alliance data.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)
                    return
                self.current_nations = nations
            
            # Create FullMillView and generate the embed
            view = FullMillView(self.author_id, self.bot, self.alliance_cog, self.current_nations)
            embed = await view.generate_full_mill_embed(self.current_nations)
            
            # Update the message with Full Mill embed and switch to FullMillView
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=view
            )
            
        except Exception as e:
            self.alliance_cog._log_error(f"Error in full_mill_button: {e}", e, "ImprovementsView.full_mill_button")
            embed = discord.Embed(
                title="❌ Full Mill Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

class ProjectTotalsView(discord.ui.View):
    """View for displaying Project Totals (active nations only)."""

    def __init__(self, author_id: int, bot: commands.Bot, alliance_cog: 'AllianceManager', nations: List[Dict] = None):
        super().__init__(timeout=300)
        self.author_id = author_id
        self.bot = bot
        self.alliance_cog = alliance_cog
        self.current_nations = nations

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ You cannot use this menu.")
            return False
        return True

    async def generate_project_totals_embed(self, nations: List[Dict] = None) -> discord.Embed:
        try:
            current_nations = nations or self.current_nations
            if not current_nations:
                # Get alliance data dynamically based on guild
                guild_alliance_id = await self.alliance_cog.get_alliance_id_for_guild(self.guild_id)
                if not guild_alliance_id:
                    return discord.Embed(
                        title="❌ No Alliance Data",
                        description="Failed to determine alliance ID for this guild.",
                        color=discord.Color.red()
                    )
                
                # Get main alliance nations
                current_nations = await self.alliance_cog.get_alliance_nations(guild_alliance_id)
                current_nations = current_nations or []
                
                # Conditionally add Prime Bank nations if configured and different
                if hasattr(self.alliance_cog, 'prime_bank_alliance_id') and self.alliance_cog.prime_bank_alliance_id and self.alliance_cog.prime_bank_alliance_id != guild_alliance_id:
                    prime_bank_nations = await self.alliance_cog.get_alliance_nations(self.alliance_cog.prime_bank_alliance_id)
                    if prime_bank_nations:
                        current_nations.extend(prime_bank_nations)
                
                if not current_nations:
                    return discord.Embed(
                        title="❌ No Alliance Data",
                        description="Failed to retrieve alliance data.",
                        color=discord.Color.red()
                    )
                self.current_nations = current_nations

            # Count nations for project totals using ALL − Vacation Mode − APPLICANT
            total_nations = [n for n in current_nations if (((n.get('vacation_mode_turns', 0) or 0) == 0) and ((n.get('alliance_position','') or '').strip().upper() != 'APPLICANT'))]

            def count_project(field: str, group: List[Dict[str, Any]]) -> int:
                try:
                    return sum(1 for n in group if bool(n.get(field, False)))
                except Exception:
                    return 0

            project_categories = {
                '⚔️ War': [
                    ("Advanced Pirate Economy", "advanced_pirate_economy"),
                    ("Central Intelligence Agency", "central_intelligence_agency"),
                    ("Fallout Shelter", "fallout_shelter"),
                    ("Guiding Satellite", "guiding_satellite"),
                    ("Iron Dome", "iron_dome"),
                    ("Military Doctrine", "military_doctrine"),
                    ("Military Research Center", "military_research_center"),
                    ("Military Salvage", "military_salvage"),
                    ("Missile Launch Pad", "missile_launch_pad"),
                    ("Nuclear Launch Facility", "nuclear_launch_facility"),
                    ("Nuclear Research Facility", "nuclear_research_facility"),
                    ("Pirate Economy", "pirate_economy"),
                    ("Propaganda Bureau", "propaganda_bureau"),
                    ("Space Program", "space_program"),
                    ("Spy Satellite", "spy_satellite"),
                    ("Surveillance Network", "surveillance_network"),
                    ("Vital Defense System", "vital_defense_system")
                ],
                '🏭 Industry': [
                    ("Arms Stockpile", "arms_stockpile"),
                    ("Bauxite Works", "bauxite_works"),
                    ("Clinical Research Center", "clinical_research_center"),
                    ("Emergency Gasoline Reserve", "emergency_gasoline_reserve"),
                    ("Green Technologies", "green_technologies"),
                    ("International Trade Center", "international_trade_center"),
                    ("Iron Works", "iron_works"),
                    ("Mass Irrigation", "mass_irrigation"),
                    ("Recycling Initiative", "recycling_initiative"),
                    ("Specialized Police Training Program", "specialized_police_training_program"),
                    ("Telecommunications Satellite", "telecommunications_satellite"),
                    ("Uranium Enrichment Program", "uranium_enrichment_program")
                ],
                '🏛️ Government': [
                    ("Activity Center", "activity_center"),
                    ("Advanced Engineering Corps", "advanced_engineering_corps"),
                    ("Arable Land Agency", "arable_land_agency"),
                    ("Bureau of Domestic Affairs", "bureau_of_domestic_affairs"),
                    ("Center for Civil Engineering", "center_for_civil_engineering"),
                    ("Government Support Agency", "government_support_agency"),
                    ("Research & Development Center", "research_and_development_center")
                ],
                '👽 Alien': [
                    ("Mars Landing", "mars_landing"),
                    ("Moon Landing", "moon_landing")
                ]
            }

            embed = discord.Embed(
                title="🧩 Cybertr0n Project Totals",
                description="Total projects across ALL − Vacation Mode − APPS",
                color=discord.Color.from_rgb(100, 181, 246)
            )

            # Add fields with totals for all groups, no emojis
            def add_chunked_field(embed_obj: discord.Embed, base_name: str, line_items: List[str], inline: bool = False):
                """Add one or more embed fields ensuring each value <= 1024 chars.
                Splits by lines and appends an index suffix when chunked."""
                if not line_items:
                    embed_obj.add_field(name=base_name, value="None", inline=inline)
                    return
                chunks = []
                current = []
                current_len = 0
                for line in line_items:
                    # +1 for newline separator
                    line_len = len(line) + 1
                    if current_len + line_len > 1024:
                        chunks.append("\n".join(current))
                        current = [line]
                        current_len = line_len
                    else:
                        current.append(line)
                        current_len += line_len
                if current:
                    chunks.append("\n".join(current))
                # Add chunks with suffixes when needed
                if len(chunks) == 1:
                    embed_obj.add_field(name=base_name, value=chunks[0], inline=inline)
                else:
                    for idx, chunk in enumerate(chunks, start=1):
                        embed_obj.add_field(name=f"{base_name} ({idx})", value=chunk, inline=inline)

            lines = []
            # Process projects by category
            for category_name, project_list in project_categories.items():
                category_lines = []
                for display, field in project_list:
                    total = count_project(field, total_nations)
                    category_lines.append(f"**{display}**: {total}")
                
                if category_lines:  # Only add if category has projects
                    lines.append(f"\n**{category_name}**")
                    lines.extend(category_lines)
            
            # Auto-chunk into multiple fields named "Projects (n)"
            add_chunked_field(embed, "Projects", lines, inline=False)

            embed.set_footer(text=f"Generated at {datetime.now().strftime('%H:%M:%S')} | Total Nations: {len(total_nations)}")
            return embed
        except Exception as e:
            self.alliance_cog._log_error(f"Error generating project totals embed: {e}", e, "ProjectTotalsView.generate_project_totals_embed")
            return discord.Embed(
                title="❌ Project Totals Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )

    @discord.ui.button(label="Alliance Totals", style=discord.ButtonStyle.secondary, emoji="📊")
    async def alliance_totals_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer()
            
            # Create AllianceTotalsView and use its generator method
            view = AllianceTotalsView(self.author_id, self.bot, self.alliance_cog, self.current_nations)
            embed = await view.generate_alliance_totals_embed(self.current_nations)
            
            # Update the message with Alliance Totals embed and switch to AllianceTotalsView
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=view
            )
        except Exception as e:
            self.alliance_cog._log_error(f"Error in alliance_totals_button: {e}", e, "ProjectTotalsView.alliance_totals_button")
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")

    @discord.ui.button(label="Improvements", style=discord.ButtonStyle.secondary, emoji="🏗️")
    async def improvements_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer()
            
            # Create ImprovementsView and use its generator method
            view = ImprovementsView(self.author_id, self.bot, self.alliance_cog, self.current_nations)
            embed = await view.generate_improvements_embed(self.current_nations)
            
            # Update the message with Improvements embed and switch to ImprovementsView
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=view
            )
        except Exception as e:
            self.alliance_cog._log_error(f"Error in improvements_button: {e}", e, "ProjectTotalsView.improvements_button")
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")

    @discord.ui.button(label="Military", style=discord.ButtonStyle.secondary, emoji="⚔️")
    async def full_mill_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer()
            view = FullMillView(self.author_id, self.bot, self.alliance_cog, self.current_nations)
            embed = await view.generate_full_mill_embed(self.current_nations)
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=view
            )
        except Exception as e:
            self.alliance_cog._log_error(f"Error in full_mill_button: {e}", e, "ProjectTotalsView.full_mill_button")
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")

class AllianceManager(commands.Cog):
    """Alliance Management System for Cybertr0n."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cybertron_alliance_id = CYBERTRON_ALLIANCE_ID  # Cybertr0n alliance ID from config
        
        # Setup logging
        self.logger = logging.getLogger(f"{__name__}.AllianceManager")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # Error tracking
        self.error_count = 0
        
        # Initialize UserDataManager (no longer used for cache access)
        self.user_data_manager = UserDataManager()
        
        # Initialize query system for fetching nations directly from API
        # This is now the primary and only data source
        self.query_system = None
        if create_query_instance is not None:
            try:
                self.query_system = create_query_instance(api_key=PANDW_API_KEY, logger=self.logger)
                self.logger.info("AllianceManager query_system initialized successfully")
            except Exception as e:
                self._log_error("Failed to initialize query system", e, "__init__")
                raise RuntimeError("Query system initialization failed - required for current data fetching")
        else:
            error_msg = "AllianceManager: create_query_instance not available; API queries disabled"
            self.logger.error(error_msg)
            raise ImportError(error_msg)
        
        self.logger.info("AllianceManager initialized successfully")
    
    def _log_error(self, error_msg: str, exception: Exception = None, context: str = ""):
        """Centralized error logging with tracking."""
        self.error_count += 1
        full_msg = f"[Error #{self.error_count}] {error_msg}"
        if context:
            full_msg += f" | Context: {context}"
        
        if exception:
            full_msg += f" | Exception: {str(exception)}"
            self.logger.error(full_msg)
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
        else:
            self.logger.error(full_msg)
    
    def _validate_input(self, data: Any, expected_type: type, field_name: str = "data") -> bool:
        """Validate input data type."""
        if not isinstance(data, expected_type):
            self._log_error(f"Invalid {field_name} type. Expected {expected_type.__name__}, got {type(data).__name__}")
            return False
        return True
    
    def _safe_get(self, data: dict, key: str, default: Any = None, expected_type: type = None) -> Any:
        """Safely get value from dictionary with type checking."""
        try:
            value = data.get(key, default)
            if expected_type and value is not None:
                if expected_type in (int, float):
                    return expected_type(value) if value != "" else default
                elif not isinstance(value, expected_type):
                    self._log_error(f"Type mismatch for key '{key}'. Expected {expected_type.__name__}, got {type(value).__name__}")
                    return default
            return value
        except (ValueError, TypeError) as e:
            self._log_error(f"Error getting key '{key}' from data", e)
            return default
    
    def _get_default_alliance_statistics(self) -> Dict[str, Any]:
        """Return default alliance statistics structure."""
        return {
            'total_nations': 0,
            'total_score': 0,
            'total_cities': 0,
            'avg_score': 0,
            'avg_cities': 0,
            'propaganda_bureau': 0,
            'missile_capable': 0,
            'space_program': 0,
            'iron_dome': 0,
            'nuclear_capable': 0,
            'nuclear_launch_facility': 0,
            'vital_defense_system': 0,
            'military_research_center': 0,
            'total_military': {
                'soldiers': 0, 'tanks': 0, 'aircraft': 0, 'ships': 0, 'missiles': 0, 'nukes': 0
            },
            'production_capacity': {
                'daily_soldiers': 0, 'daily_tanks': 0, 'daily_aircraft': 0, 'daily_ships': 0,
                'max_soldiers': 0, 'max_tanks': 0, 'max_aircraft': 0, 'max_ships': 0
            }
        }
    
    # Load from individual alliance files instead of centralized cache
    async def get_alliance_nations(self, alliance_id: str, force_refresh: bool = False) -> Optional[List[Dict[str, Any]]]:
        """Fetch alliance nations from individual alliance files.
        
        Args:
            alliance_id: The alliance ID to fetch nations for
            force_refresh: If True, bypass cache and fetch fresh data (not used for file loading)
        """
        # Input validation
        if not alliance_id or not str(alliance_id).strip():
            self.logger.warning("get_alliance_nations: Invalid alliance_id provided")
            return None
        
        try:
            # Load from individual alliance file
            user_data_manager = UserDataManager()
            alliance_file_key = f"alliance_{alliance_id}"
            alliance_data = await user_data_manager.get_json_data(alliance_file_key, {})
            
            if alliance_data and isinstance(alliance_data, dict) and 'nations' in alliance_data:
                nations = alliance_data.get('nations', [])
                if nations:
                    self.logger.info(f"get_alliance_nations: Loaded {len(nations)} nations from alliance file {alliance_file_key}")
                    return nations
            
            # If individual file not found, try loading the specific alliance file from Bloc directory
            bloc_dir = Path(__file__).parent.parent.parent / 'Data' / 'Bloc'
            if bloc_dir.exists():
                # Look for the specific alliance file
                specific_file = bloc_dir / f'alliance_{alliance_id}.json'
                if specific_file.exists():
                    try:
                        file_data = await user_data_manager.get_json_data(f'alliance_{alliance_id}', {})
                        if isinstance(file_data, dict) and 'nations' in file_data:
                            nations = file_data['nations']
                            self.logger.info(f"get_alliance_nations: Loaded {len(nations)} nations from specific alliance file {specific_file.name}")
                            return nations
                    except Exception as e:
                        self.logger.warning(f"Error loading specific alliance file {specific_file.name}: {e}")
                        return None
            
            # Fallback to API if files not available
            if self.query_system:
                nations = await self.query_system.get_alliance_nations(alliance_id, bot=self.bot, force_refresh=True)
                if nations:
                    self.logger.info(f"get_alliance_nations: Retrieved {len(nations)} nations for alliance {alliance_id} from API")
                    return nations
            
            self.logger.warning(f"get_alliance_nations: No nations found for alliance {alliance_id}")
            return None
            
        except Exception as e:
            self._log_error(f"Error fetching alliance data for alliance {alliance_id}", e, "get_alliance_nations")
            raise RuntimeError(f"Failed to fetch alliance data: {str(e)}")
            
    def get_active_nations(self, nations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter nations to exclude vacation mode and applicant members using centralized logic."""
        return get_active_nations(nations)

    def calculate_nation_statistics(self, nations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate comprehensive nation statistics using centralized logic."""
        return calculate_nation_statistics(nations)

    def calculate_alliance_statistics(self, nations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate alliance statistics using centralized logic."""
        return calculate_alliance_statistics(nations)

    def calculate_full_mill_data(self, nations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate full mill data using centralized logic."""
        return calculate_full_mill_data(nations)

    def calculate_military_purchase_limits(self, nation: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate military purchase limits using centralized logic."""
        return calculate_military_purchase_limits(nation)

    def get_nation_specialty(self, nation: Dict[str, Any]) -> str:
        """Get nation specialty using centralized logic."""
        return get_nation_specialty(nation)

    def calculate_combat_score(self, nation: Dict[str, Any]) -> float:
        """Calculate combat score using centralized logic."""
        return calculate_combat_score(nation)

    def has_project(self, nation: Dict[str, Any], project_name: str) -> bool:
        """Check if nation has a specific project using centralized logic."""
        return has_project(nation, project_name)

    async def calculate_improvements_data(self, nations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate improvements data using centralized logic."""
        return await calculate_improvements_data(nations)

    @commands.hybrid_command(name='testalliance', description='Test alliance UI and dropdown functionality')
    @commands.guild_only()
    async def test_alliance_command(self, ctx: commands.Context):
        """Test command to verify alliance dropdown functionality (slash-enabled)."""
        try:
            # Create AllianceTotalsView with combined Cybertron + Prime Banking data
            view = AllianceTotalsView(ctx.author.id, self.bot, self, None)
            embed = await view.generate_alliance_totals_embed()
            
            await ctx.send(embed=embed, view=view)
            
        except Exception as e:
            self._log_error(f"Error in test_alliance_command: {e}", e, "test_alliance_command")
            await ctx.send(f"❌ Test command failed: {str(e)}")

    @commands.hybrid_command(name='alliance', description='Display alliance overview with navigation')
    @commands.guild_only()
    async def alliance(self, ctx: commands.Context):
        """Show alliance overview with interactive UI and working buttons."""
        try:
            # Send initial loading message to be edited later
            initial_msg = await ctx.send("🔄 Loading Alliance Data...")

            # Refresh bloc data to ensure freshest alliance files
            try:
                if BlocAllianceManager:
                    bloc_manager = BlocAllianceManager(self.bot)
                    await bloc_manager.refresh_bloc_data()
                else:
                    self._log_error("BlocAllianceManager import unavailable", None, "alliance.refresh_bloc")
            except Exception as e:
                self._log_error(f"Failed to refresh bloc data: {e}", e, "alliance.refresh_bloc")

            # Force refresh Cybertr0n alliance data (equivalent to running refresh_alliance)
            try:
                if hasattr(self, 'query_system') and self.query_system:
                    await self.query_system.get_alliance_nations(
                        self.cybertron_alliance_id,
                        bot=self.bot,
                        force_refresh=True
                    )
            except Exception as e:
                self._log_error(f"Failed to refresh Cybertr0n alliance data: {e}", e, "alliance.refresh_cybertron")

            # Fetch nations for Cybertr0n and optionally Prime Bank, then combine
            nations: List[Dict] = []

            try:
                main_nations = await self.get_alliance_nations(self.cybertron_alliance_id)
                if isinstance(main_nations, list):
                    nations.extend(main_nations)
            except Exception as e:
                self._log_error(f"Failed to load Cybertr0n nations: {e}", e, "alliance.load_main")

            # Include Prime Bank if configured and different from main
            try:
                if PRIME_BANK_ALLIANCE_ID and PRIME_BANK_ALLIANCE_ID != self.cybertron_alliance_id:
                    prime_nations = await self.get_alliance_nations(PRIME_BANK_ALLIANCE_ID)
                    if isinstance(prime_nations, list):
                        nations.extend(prime_nations)
            except Exception as e:
                self._log_error(f"Failed to load Prime Bank nations: {e}", e, "alliance.load_prime")

            if not nations:
                await initial_msg.edit(content="❌ No alliance data available.")
                return

            # Build initial view and embed for Alliance Totals
            view = AllianceTotalsView(
                author_id=ctx.author.id,
                bot=self.bot,
                alliance_cog=self,
                nations=nations
            )
            embed = await view.generate_alliance_totals_embed(nations)

            # Edit the initial message to display the embed and attach the interactive view
            await initial_msg.edit(content=None, embed=embed, view=view)
        
        except Exception as e:
            self._log_error(f"Error in alliance command: {e}", e, "AllianceManager.alliance")
            await ctx.send(f"❌ An error occurred: {str(e)}")

    @commands.hybrid_command(name='refresh_alliance', description='Refresh Cybertr0n alliance data')
    @commands.guild_only()
    @leadership_role_check()
    async def refresh_alliance_command(self, ctx: commands.Context):
        """Refresh only the Cybertr0n alliance data."""
        try:
            # Prepare initial response for slash vs prefix invocation
            refresh_msg = None
            is_slash = hasattr(ctx, 'interaction') and getattr(ctx, 'interaction', None)

            if is_slash:
                try:
                    if not ctx.interaction.response.is_done():
                        await ctx.interaction.response.send_message("🔄 Refreshing Cybertr0n alliance data…")
                except Exception:
                    # If already responded or failed, fall back to a follow-up
                    try:
                        await ctx.interaction.followup.send("🔄 Refreshing Cybertr0n alliance data…")
                    except Exception:
                        pass
            else:
                refresh_msg = await ctx.send("🔄 Refreshing Cybertr0n alliance data…")
            
            # Use the query system to refresh Cybertr0n alliance data
            if self.query_system:
                try:
                    # Force refresh the Cybertr0n alliance data
                    nations = await self.query_system.get_alliance_nations(
                        self.cybertron_alliance_id, 
                        bot=self.bot, 
                        force_refresh=True
                    )
                    
                    if nations:
                        # Count active nations (exclude applicants and vacation mode)
                        active_nations = [
                            nation for nation in nations 
                            if (nation.get('alliance_position') != 'APPLICANT' and 
                                not nation.get('vacation_mode', False))
                        ]
                        content = (
                            f"✅ **Cybertr0n alliance data refreshed!**\n"
                            f"📊 Total nations: {len(nations)}\n"
                            f"⚔️ Active nations: {len(active_nations)}"
                        )
                    else:
                        content = "❌ Failed to refresh alliance data - no nations returned."

                    # Deliver the content using appropriate edit method
                    try:
                        if is_slash:
                            await ctx.interaction.edit_original_response(content=content)
                        elif refresh_msg is not None:
                            await refresh_msg.edit(content=content)
                        else:
                            await ctx.send(content)
                    except Exception:
                        # Fallback if edit fails (e.g., original message deleted)
                        try:
                            if is_slash:
                                await ctx.interaction.followup.send(content)
                            else:
                                await ctx.send(content)
                        except Exception:
                            pass
                        
                except Exception as e:
                    self._log_error(f"Error refreshing alliance data: {e}", e, "refresh_alliance.query")
                    # Attempt to report the error safely
                    error_content = f"❌ Error refreshing alliance data: {str(e)}"
                    try:
                        if is_slash:
                            await ctx.interaction.edit_original_response(content=error_content)
                        elif refresh_msg is not None:
                            await refresh_msg.edit(content=error_content)
                        else:
                            await ctx.send(error_content)
                    except Exception:
                        try:
                            if is_slash:
                                await ctx.interaction.followup.send(error_content)
                            else:
                                await ctx.send(error_content)
                        except Exception:
                            pass
            else:
                # Query system not available; report using appropriate method
                no_qs = "❌ Query system not available for refreshing data."
                try:
                    if is_slash:
                        await ctx.interaction.edit_original_response(content=no_qs)
                    elif refresh_msg is not None:
                        await refresh_msg.edit(content=no_qs)
                    else:
                        await ctx.send(no_qs)
                except Exception:
                    try:
                        if is_slash:
                            await ctx.interaction.followup.send(no_qs)
                        else:
                            await ctx.send(no_qs)
                    except Exception:
                        pass
                
        except Exception as e:
            self._log_error(f"Error in refresh_alliance command: {e}", e, "AllianceManager.refresh_alliance")
            try:
                if hasattr(ctx, 'interaction') and getattr(ctx, 'interaction', None):
                    await ctx.interaction.followup.send(f"❌ An error occurred: {str(e)}")
                else:
                    await ctx.send(f"❌ An error occurred: {str(e)}")
            except Exception:
                pass

    async def generate_alliance_totals_embed(self, nations: List[Dict[str, Any]]) -> discord.Embed:
        """Generate the alliance totals embed."""
        try:
            if not nations:
                return discord.Embed(
                    title="❌ No Alliance Data",
                    description="Failed to retrieve alliance data.",
                    color=discord.Color.red()
                )
            
            # Create a temporary AllianceTotalsView to use its embed generation method
            view = AllianceTotalsView(None, self.bot, self, nations)
            return await view.generate_alliance_totals_embed(nations)
            
        except Exception as e:
            self._log_error(f"Error in generate_alliance_totals_embed: {e}", e, "AllianceManager.generate_alliance_totals_embed")
            return discord.Embed(
                title="❌ Alliance Totals Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )

    _active_nations_cache = {}

async def setup(bot: commands.Bot):
    """Setup function for loading the cog."""
    try:
        await bot.add_cog(AllianceManager(bot))
        logging.info("Alliance Management System loaded successfully!")
    except Exception as e:
        logging.error(f"Failed to load Alliance Management System: {e}")
        logging.error(traceback.format_exc())
        raise
