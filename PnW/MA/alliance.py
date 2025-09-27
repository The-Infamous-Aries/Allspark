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
from config import PANDW_API_KEY, CYBERTRON_ALLIANCE_ID
from Systems.user_data_manager import UserDataManager
 
# Import centralized query system for direct API access
try:
    from .query import create_query_instance
except ImportError:
    try:
        from Systems.PnW.MA.query import create_query_instance
    except ImportError:
        create_query_instance = None

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
                # Fetch alliance data if not already loaded
                current_nations = await self.alliance_cog.get_alliance_nations(self.alliance_cog.cybertron_alliance_id)
                if not current_nations:
                    return discord.Embed(
                        title="❌ No Alliance Data",
                        description="Failed to retrieve alliance data.",
                        color=discord.Color.red()
                    )
                self.current_nations = current_nations
            
            # Calculate full mill data
            full_mill_data = await self.alliance_cog.calculate_full_mill_data(current_nations)
            nation_stats = self.alliance_cog.calculate_nation_statistics(current_nations)
            
            # Create Full Mill embed
            embed = discord.Embed(
                title="🏭 Cybertr0n Full Mill Analysis",
                description="Units needed to reach maximum military capacity",
                color=discord.Color.from_rgb(255, 140, 0)
            )
            
            # Overall statistics
            embed.add_field(
                name="📊 Overall Statistics",
                value=(
                    f"**Total Nations:** {nation_stats['total_nations']}\n"
                    f"**Active Nations:** {nation_stats['active_nations']}\n"
                    f"**Total Cities:** {full_mill_data['total_cities']:,}\n"
                    f"**Total Score:** {full_mill_data['total_score']:,}"
                ),
                inline=False
            )
            
            # Military unit gaps
            embed.add_field(
                name="⚔️ Military Unit Gaps",
                value=(
                    f"🪖 **Soldiers:** {full_mill_data['soldier_gap']:,} needed\n"
                    f"🛡️ **Tanks:** {full_mill_data['tank_gap']:,} needed\n"
                    f"✈️ **Aircraft:** {full_mill_data['aircraft_gap']:,} needed\n"
                    f"🚢 **Ships:** {full_mill_data['ship_gap']:,} needed"
                ),
                inline=True
            )
            
            # Time to max capacity (days)
            embed.add_field(
                name="⏱️ Days to Max Capacity",
                value=(
                    f"🪖 **Soldiers:** {full_mill_data['soldier_days']:.1f} days\n"
                    f"🛡️ **Tanks:** {full_mill_data['tank_days']:.1f} days\n"
                    f"✈️ **Aircraft:** {full_mill_data['aircraft_days']:.1f} days\n"
                    f"🚢 **Ships:** {full_mill_data['ship_days']:.1f} days"
                ),
                inline=True
            )
            
            # Current vs Max capacity
            embed.add_field(
                name="📈 Current vs Maximum Capacity",
                value=(
                    f"🪖 **Current:** {full_mill_data['current_soldiers']:,} / {full_mill_data['max_soldiers']:,}\n"
                    f"🛡️ **Current:** {full_mill_data['current_tanks']:,} / {full_mill_data['max_tanks']:,}\n"
                    f"✈️ **Current:** {full_mill_data['current_aircraft']:,} / {full_mill_data['max_aircraft']:,}\n"
                    f"🚢 **Current:** {full_mill_data['current_ships']:,} / {full_mill_data['max_ships']:,}"
                ),
                inline=False
            )
            
            # Daily production capacity
            embed.add_field(
                name="🏭 Daily Production Capacity",
                value=(
                    f"🪖 **Soldiers:** {full_mill_data['daily_soldiers']:,}/day\n"
                    f"🛡️ **Tanks:** {full_mill_data['daily_tanks']:,}/day\n"
                    f"✈️ **Aircraft:** {full_mill_data['daily_aircraft']:,}/day\n"
                    f"🚢 **Ships:** {full_mill_data['daily_ships']:,}/day"
                ),
                inline=True
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

    @discord.ui.button(label="Full Mill", style=discord.ButtonStyle.primary, emoji="⚔️", disabled=True)
    async def full_mill_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show Full Mill calculations - units needed to reach max capacity."""
        try:
            await interaction.response.defer()
            
            # Generate the full mill embed using the new method
            embed = await self.generate_full_mill_embed()
            
            # Update the message with Full Mill embed and keep current view
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=self
            )
            
        except Exception as e:
            self.alliance_cog._log_error(f"Error in full_mill_button: {e}", e, "FullMillView.full_mill_button")
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
            self.alliance_cog._log_error(f"Error in project_totals_button: {e}", e, "FullMillView.project_totals_button")
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")
    
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
                current_nations = await self.alliance_cog.get_alliance_nations(self.alliance_cog.cybertron_alliance_id)
                if not current_nations:
                    return discord.Embed(
                        title="❌ No Alliance Data",
                        description="Failed to retrieve alliance data.",
                        color=discord.Color.red()
                    )
                self.current_nations = current_nations
            
            # Get active nations for statistics
            active_nations = self.alliance_cog.get_active_nations(current_nations)
            stats = self.alliance_cog.calculate_alliance_statistics(active_nations)
            
            # Calculate nation statistics for all nations (including inactive)
            nation_stats = self.alliance_cog.calculate_nation_statistics(current_nations)
            
            # Calculate averages manually since they're not in stats
            avg_score = stats['total_score'] / stats['total_nations'] if stats['total_nations'] > 0 else 0
            avg_cities = stats['total_cities'] / stats['total_nations'] if stats['total_nations'] > 0 else 0
            
            # Create comprehensive statistics embed
            embed = discord.Embed(
                title="📊 Cybertr0n Alliance Totals",
                description="Comprehensive alliance statistics and capabilities",
                color=discord.Color.from_rgb(0, 150, 255)
            )
            
            embed.add_field(
                name="📊 Nation Counts",
                value=(
                    f"📇 **Total:** {nation_stats['total_nations']}\n"
                    f"✅ **Active:** {nation_stats['active_nations']}\n"
                    f"📝 **Applicants:** {nation_stats['applicant_nations']}\n"
                    f"🧮 **Total Score:** {stats['total_score']:,}\n"
                    f"⚖️ **Average Score:** {avg_score:,.0f}\n"
                    f"🌇 **Total Cities:** {stats['total_cities']:,}\n"
                    f"🌆 **Average Cities:** {avg_cities:.1f}"
                ),
                inline=False
            )
            
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
                    add = ("\n" if value else "") + link
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

            # Compute categories - exclude Vacation Mode and APPLICANT nations
            filtered_nations = [n for n in current_nations if (n.get('vacation_mode_turns', 0) or 0) == 0 and ((n.get('alliance_position', '') or '').strip().upper() != 'APPLICANT')]
            grey = [n for n in filtered_nations if (n.get('color', '') or '').strip().upper() in ('GREY', 'GRAY')]
            beige = [n for n in filtered_nations if (n.get('color', '') or '').strip().upper() == 'BEIGE']
            vm = [n for n in current_nations if (n.get('vacation_mode_turns', 0) or 0) > 0 and ((n.get('alliance_position', '') or '').strip().upper() != 'APPLICANT')]

            seven_to_thirteen = []
            fourteen_plus = []
            for n in active_nations:
                d = _days_inactive(n)
                if isinstance(d, int):
                    if 7 <= d < 14:
                        seven_to_thirteen.append(n)
                    elif d >= 14:
                        fourteen_plus.append(n)

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
    
    @discord.ui.button(label="Full Mill", style=discord.ButtonStyle.primary, emoji="⚔️")
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
                current_nations = await self.alliance_cog.get_alliance_nations(self.alliance_cog.cybertron_alliance_id)
                if not current_nations:
                    return discord.Embed(
                        title="❌ No Alliance Data",
                        description="Failed to retrieve alliance data.",
                        color=discord.Color.red()
                    )
                self.current_nations = current_nations
            
            # Calculate improvements data
            improvements_data = await self.alliance_cog.calculate_improvements_data(current_nations)
            
            # Create Improvements Breakdown embed
            embed = discord.Embed(
                title="🏗️ Cybertr0n Improvements Breakdown",
                description="Total improvements across all alliance nations",
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
    
    @discord.ui.button(label="Full Mill", style=discord.ButtonStyle.secondary, emoji="🏭")
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
                current_nations = await self.alliance_cog.get_alliance_nations(self.alliance_cog.cybertron_alliance_id)
                if not current_nations:
                    return discord.Embed(
                        title="❌ No Alliance Data",
                        description="Failed to retrieve alliance data.",
                        color=discord.Color.red()
                    )
                self.current_nations = current_nations

            # Use only active nations (exclude Applicants and VM)
            active_nations = self.alliance_cog.get_active_nations(current_nations)
            stats = self.alliance_cog.calculate_alliance_statistics(active_nations)

            embed = discord.Embed(
                title="🧩 Cybertr0n Project Totals",
                description="Projects among active nations (excludes Applicants & VM)",
                color=discord.Color.from_rgb(100, 181, 246)
            )

            # Project counts
            embed.add_field(
                name="🏗️ Project Totals",
                value=(
                    f"📢 **Propaganda Bureau:** {stats['propaganda_bureau']}\n"
                    f"🚀 **Missile Launch Pad:** {stats['missile_launch_pad']}\n"
                    f"🌌 **Space Program:** {stats['space_program']}\n"
                    f"🛡️ **Iron Dome:** {stats['iron_dome']}\n"
                    f"☢️ **Nuclear Research Facility:** {stats['nuclear_research_facility']}\n"
                    f"💥 **Nuclear Launch Facility:** {stats['nuclear_launch_facility']}\n"
                    f"🔰 **Vital Defense System:** {stats['vital_defense_system']}\n"
                    f"🔬 **Military Research Center:** {stats['military_research_center']}"
                ),
                inline=False
            )

            embed.set_footer(text=f"Generated at {datetime.now().strftime('%H:%M:%S')} | Active nations: {len(active_nations)}")
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

    @discord.ui.button(label="Full Mill", style=discord.ButtonStyle.secondary, emoji="⚔️")
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
    
    # Using centralized cache instead of local cache
    async def get_alliance_nations(self, alliance_id: str, force_refresh: bool = False) -> Optional[List[Dict[str, Any]]]:
        """Fetch alliance nations using centralized cache from UserDataManager.
        
        Args:
            alliance_id: The alliance ID to fetch nations for
            force_refresh: If True, bypass cache and fetch fresh data
        """
        # Input validation
        if not alliance_id or not str(alliance_id).strip():
            self.logger.warning("get_alliance_nations: Invalid alliance_id provided")
            return None
        
        try:
            # Use centralized UserDataManager for caching
            user_data_manager = UserDataManager()
            cache_key = f"alliance_data_{alliance_id}"
            
            # Check centralized cache first unless forcing refresh
            if not force_refresh:
                try:
                    alliance_cache = await user_data_manager.get_json_data('alliance_cache', {})
                    cache_entry = alliance_cache.get(cache_key)
                    
                    if cache_entry and isinstance(cache_entry, dict):
                        nations = cache_entry.get('nations', [])
                        if nations:
                            self.logger.debug(f"get_alliance_nations: Using centralized cache for alliance {alliance_id}")
                            return nations
                except Exception as cache_err:
                    self.logger.warning(f"get_alliance_nations: Cache read failed: {cache_err}")
            
            # Ensure query system is available
            if not self.query_system:
                self.logger.error("get_alliance_nations: Query system not available - cannot fetch current data")
                raise RuntimeError("Query system not available - cannot fetch current data")
            
            # Fetch fresh data from API
            nations = await self.query_system.get_alliance_nations(alliance_id, bot=self.bot, force_refresh=True)
            if nations:
                self.logger.info(f"get_alliance_nations: Retrieved {len(nations)} nations for alliance {alliance_id} from API")
                return nations
            else:
                self.logger.warning(f"get_alliance_nations: No nations returned from API for alliance {alliance_id}")
                return None
            
        except Exception as e:
            self._log_error(f"Error fetching alliance data for alliance {alliance_id}", e, "get_alliance_nations")
            raise RuntimeError(f"Failed to fetch current alliance data: {str(e)}")
            
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
    
    # Cache for active nations
    _active_nations_cache = {}
    
    def get_active_nations(self, nations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter nations to exclude vacation mode and applicant members."""
        # Input validation
        if not self._validate_input(nations, list, "nations"):
            self.logger.warning("get_active_nations: Invalid nations input, returning empty list")
            return []
        
        if not nations:
            self.logger.debug("get_active_nations: Empty nations list provided")
            return []
        
        # Generate a cache key based on the nations list
        # Use a simple hash of nation IDs to identify this specific list
        try:
            nation_ids = tuple(sorted([str(nation.get('id', '')) for nation in nations if isinstance(nation, dict)]))
            cache_key = hash(nation_ids)
            
            # Check if we have this result cached
            if cache_key in self._active_nations_cache:
                self.logger.debug(f"get_active_nations: Using cached result for {len(nations)} nations")
                return self._active_nations_cache[cache_key]
                
            self.logger.debug(f"get_active_nations: Processing {len(nations)} nations")
            
            active_nations = []
            for i, nation in enumerate(nations):
                try:
                    if not isinstance(nation, dict):
                        self.logger.warning(f"get_active_nations: Nation at index {i} is not a dictionary, skipping")
                        continue
                    
                    # Skip vacation mode members
                    vacation_turns = self._safe_get(nation, 'vacation_mode_turns', 0, int)
                    if vacation_turns > 0:
                        self.logger.debug(f"get_active_nations: Skipping nation {nation.get('nation_name', 'Unknown')} - in vacation mode ({vacation_turns} turns)")
                        continue
                    
                    # Skip applicants (alliance_position "APPLICANT")
                    alliance_position = self._safe_get(nation, 'alliance_position', '', str)
                    if alliance_position == 'APPLICANT':
                        self.logger.debug(f"get_active_nations: Skipping nation {nation.get('nation_name', 'Unknown')} - applicant status")
                        continue
                    
                    active_nations.append(nation)
                except (AttributeError, TypeError) as e:
                    self._log_error(f"Error processing nation at index {i}", e, "get_active_nations")
                    continue
            
            # Cache the result
            self._active_nations_cache[cache_key] = active_nations
            
            self.logger.info(f"get_active_nations: Filtered {len(nations)} nations to {len(active_nations)} active nations")
            return active_nations
            
        except Exception as e:
            self._log_error("Unexpected error in get_active_nations", e, "get_active_nations")
            return []
    
    def calculate_nation_statistics(self, nations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate statistics for different nation categories."""
        if not nations:
            return {
                'total_nations': 0,
                'active_nations': 0,
                'applicant_nations': 0,
                'vacation_nations': 0,
                'grey_nations': 0,
                'beige_nations': 0,
                'inactive_7_days': 0,
                'inactive_14_days': 0
            }
        
        try:
            from datetime import datetime, timezone, timedelta
            
            total_nations = len(nations)
            active_nations = 0
            applicant_nations = 0
            vacation_nations = 0
            grey_nations = 0
            beige_nations = 0
            inactive_7_days = 0
            inactive_14_days = 0
            
            # Calculate cutoff dates for inactivity
            now = datetime.now(timezone.utc)
            seven_days_ago = now - timedelta(days=7)
            fourteen_days_ago = now - timedelta(days=14)
            
            for nation in nations:
                if not isinstance(nation, dict):
                    continue
                
                # Get nation data
                vacation_turns = self._safe_get(nation, 'vacation_mode_turns', 0, int)
                alliance_position = self._safe_get(nation, 'alliance_position', '', str)
                color = self._safe_get(nation, 'color', '', str).upper()
                last_active_str = self._safe_get(nation, 'last_active', '', str)
                
                # Determine active status (exclude VM and Applicants)
                is_active = (vacation_turns == 0 and alliance_position.upper() != 'APPLICANT')
                
                # Parse last active date
                last_active = None
                if last_active_str:
                    try:
                        # Handle ISO format with timezone
                        if last_active_str.endswith('+00:00'):
                            last_active = datetime.fromisoformat(last_active_str.replace('+00:00', '')).replace(tzinfo=timezone.utc)
                        else:
                            last_active = datetime.fromisoformat(last_active_str).replace(tzinfo=timezone.utc)
                    except (ValueError, TypeError):
                        last_active = None
                
                # Count vacation mode nations (exclude applicants)
                if vacation_turns > 0 and alliance_position.upper() != 'APPLICANT':
                    vacation_nations += 1
                
                # Count applicant nations
                if alliance_position.upper() == 'APPLICANT':
                    applicant_nations += 1
                
                # Count inactive nations based on last activity (ACTIVE nations only)
                if is_active and last_active:
                    if last_active < fourteen_days_ago:
                        inactive_14_days += 1
                    elif last_active < seven_days_ago:
                        inactive_7_days += 1
                
                if is_active:
                    active_nations += 1
                    
                    # Count color bloc nations ONLY for active nations
                    if color == 'GREY' or color == 'GRAY':
                        grey_nations += 1
                    elif color == 'BEIGE':
                        beige_nations += 1
            
            return {
                'total_nations': total_nations,
                'active_nations': active_nations,
                'applicant_nations': applicant_nations,
                'vacation_nations': vacation_nations,
                'grey_nations': grey_nations,
                'beige_nations': beige_nations,
                'inactive_7_days': inactive_7_days,
                'inactive_14_days': inactive_14_days
            }
            
        except Exception as e:
            self._log_error("Error calculating nation statistics", e, "calculate_nation_statistics")
            return {
                'total_nations': 0,
                'active_nations': 0,
                'applicant_nations': 0,
                'vacation_nations': 0,
                'grey_nations': 0,
                'beige_nations': 0,
                'inactive_7_days': 0,
                'inactive_14_days': 0
            }
    
    def calculate_alliance_statistics(self, nations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate comprehensive alliance statistics."""
        # Direct implementation
        stats = {
            'total_nations': len(nations),
            'total_score': sum(nation.get('score', 0) for nation in nations),
            'total_cities': sum(nation.get('num_cities', 0) for nation in nations),
            'missile_capable': 0,
            'nuclear_capable': 0,
            'vital_defense_system': 0,
            'iron_dome': 0,
            'propaganda_bureau': 0,
            'military_research_center': 0,
            'space_program': 0,
            'missile_launch_pad': 0,
            'nuclear_research_facility': 0,
            'nuclear_launch_facility': 0,
            'total_military': {
                'soldiers': 0,
                'tanks': 0,
                'aircraft': 0,
                'ships': 0,
                'missiles': 0,
                'nukes': 0
            },
            'production_capacity': {
                'total_barracks': 0,
                'total_factories': 0,
                'total_hangars': 0,
                'total_drydocks': 0,
                'daily_soldiers': 0,
                'daily_tanks': 0,
                'daily_aircraft': 0,
                'daily_ships': 0,
                'daily_missiles': 0,
                'daily_nukes': 0,
                'max_soldiers': 0,
                'max_tanks': 0,
                'max_aircraft': 0,
                'max_ships': 0,
                'max_missiles': 0,
                'max_nukes': 0
            }
        }
        
        for nation in nations:
            # Count strategic and defensive projects
            if self.has_project(nation, 'Missile Launch Pad'):
                stats['missile_capable'] += 1
                stats['missile_launch_pad'] += 1
            if self.has_project(nation, 'Nuclear Research Facility'):
                stats['nuclear_capable'] += 1
                stats['nuclear_research_facility'] += 1
            if self.has_project(nation, 'Vital Defense System'):
                stats['vital_defense_system'] += 1
            if self.has_project(nation, 'Iron Dome'):
                stats['iron_dome'] += 1
            if self.has_project(nation, 'Propaganda Bureau'):
                stats['propaganda_bureau'] += 1
            if self.has_project(nation, 'Military Research Center'):
                stats['military_research_center'] += 1
            if self.has_project(nation, 'Space Program'):
                stats['space_program'] += 1
            
            # Count Nuclear Launch Facility separately
            if self.has_project(nation, 'Nuclear Launch Facility'):
                stats['nuclear_launch_facility'] += 1
            
            # Sum military units
            stats['total_military']['soldiers'] += nation.get('soldiers', 0)
            stats['total_military']['tanks'] += nation.get('tanks', 0)
            stats['total_military']['aircraft'] += nation.get('aircraft', 0)
            stats['total_military']['ships'] += nation.get('ships', 0)
            stats['total_military']['missiles'] += nation.get('missiles', 0)
            stats['total_military']['nukes'] += nation.get('nukes', 0)
            
            # Calculate production capabilities
            production_data = self.calculate_military_purchase_limits(nation)
            stats['production_capacity']['total_barracks'] += production_data.get('total_barracks', 0)
            stats['production_capacity']['total_factories'] += production_data.get('total_factories', 0)
            stats['production_capacity']['total_hangars'] += production_data.get('total_hangars', 0)
            stats['production_capacity']['total_drydocks'] += production_data.get('total_drydocks', 0)
            stats['production_capacity']['daily_soldiers'] += production_data.get('soldiers', 0)
            stats['production_capacity']['daily_tanks'] += production_data.get('tanks', 0)
            stats['production_capacity']['daily_aircraft'] += production_data.get('aircraft', 0)
            stats['production_capacity']['daily_ships'] += production_data.get('ships', 0)
            stats['production_capacity']['daily_missiles'] += production_data.get('missiles', 0)
            stats['production_capacity']['daily_nukes'] += production_data.get('nukes', 0)
            
            # Use actual calculated maximum capacities (includes research bonuses and purchased capacities)
            stats['production_capacity']['max_soldiers'] += production_data.get('soldiers_max', 0)
            stats['production_capacity']['max_tanks'] += production_data.get('tanks_max', 0)
            stats['production_capacity']['max_aircraft'] += production_data.get('aircraft_max', 0)
            stats['production_capacity']['max_ships'] += production_data.get('ships_max', 0)
            
            # Calculate missile and nuke maximum capacity based on project availability
            if self.has_project(nation, 'Missile Launch Pad'):
                stats['production_capacity']['max_missiles'] += 50
            
            if self.has_project(nation, 'Nuclear Research Facility'):
                stats['production_capacity']['max_nukes'] += 50
        
        return stats
    
    async def calculate_full_mill_data(self, nations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate Full Mill data - units needed and days to max capacity."""
        try:
            # Get active nations (exclude vacation mode and applicants)
            active_nations = self.get_active_nations(nations)
            
            # Initialize counters for military units
            current_soldiers = 0
            current_tanks = 0
            current_aircraft = 0
            current_ships = 0
            
            max_soldiers = 0
            max_tanks = 0
            max_aircraft = 0
            max_ships = 0
            
            daily_soldiers = 0
            daily_tanks = 0
            daily_aircraft = 0
            daily_ships = 0
            
            total_cities = 0
            total_score = 0
            
            # Process each active nation individually
            for nation in active_nations:
                # Add current military units
                current_soldiers += nation.get('soldiers', 0)
                current_tanks += nation.get('tanks', 0)
                current_aircraft += nation.get('aircraft', 0)
                current_ships += nation.get('ships', 0)
                
                # Add to total cities and score
                total_cities += nation.get('num_cities', 0)
                total_score += nation.get('score', 0)
                
                # Calculate military limits for this nation
                limits = self.calculate_military_purchase_limits(nation)
                
                # Add daily production
                daily_soldiers += limits.get('soldiers_daily', limits.get('soldiers', 0))
                daily_tanks += limits.get('tanks_daily', limits.get('tanks', 0))
                daily_aircraft += limits.get('aircraft_daily', limits.get('aircraft', 0))
                daily_ships += limits.get('ships_daily', limits.get('ships', 0))
                
                # Add maximum capacities
                max_soldiers += limits.get('soldiers_max', 0)
                max_tanks += limits.get('tanks_max', 0)
                max_aircraft += limits.get('aircraft_max', 0)
                max_ships += limits.get('ships_max', 0)
            
            # Ensure max values are not less than current values
            max_soldiers = max(max_soldiers, current_soldiers)
            max_tanks = max(max_tanks, current_tanks)
            max_aircraft = max(max_aircraft, current_aircraft)
            max_ships = max(max_ships, current_ships)
            
            # Calculate gaps between current and max capacity
            soldier_gap = max(0, max_soldiers - current_soldiers)
            tank_gap = max(0, max_tanks - current_tanks)
            aircraft_gap = max(0, max_aircraft - current_aircraft)
            ship_gap = max(0, max_ships - current_ships)
            
            # Calculate days to max capacity (avoid division by zero)
            soldier_days = soldier_gap / daily_soldiers if daily_soldiers > 0 else float('inf')
            tank_days = tank_gap / daily_tanks if daily_tanks > 0 else float('inf')
            aircraft_days = aircraft_gap / daily_aircraft if daily_aircraft > 0 else float('inf')
            ship_days = ship_gap / daily_ships if daily_ships > 0 else float('inf')
            
            return {
                'total_nations': len(active_nations),
                'active_nations': len(active_nations),
                'total_cities': total_cities,
                'total_score': total_score,
                'current_soldiers': current_soldiers,
                'current_tanks': current_tanks,
                'current_aircraft': current_aircraft,
                'current_ships': current_ships,
                'max_soldiers': max_soldiers,
                'max_tanks': max_tanks,
                'max_aircraft': max_aircraft,
                'max_ships': max_ships,
                'daily_soldiers': daily_soldiers,
                'daily_tanks': daily_tanks,
                'daily_aircraft': daily_aircraft,
                'daily_ships': daily_ships,
                'soldier_gap': soldier_gap,
                'tank_gap': tank_gap,
                'aircraft_gap': aircraft_gap,
                'ship_gap': ship_gap,
                'soldier_days': soldier_days,
                'tank_days': tank_days,
                'aircraft_days': aircraft_days,
                'ship_days': ship_days
            }
            
        except Exception as e:
            self._log_error(f"Error calculating full mill data: {e}", e, "calculate_full_mill_data")
            return {
                'total_nations': 0,
                'active_nations': 0,
                'total_cities': 0,
                'total_score': 0,
                'current_soldiers': 0,
                'current_tanks': 0,
                'current_aircraft': 0,
                'current_ships': 0,
                'max_soldiers': 0,
                'max_tanks': 0,
                'max_aircraft': 0,
                'max_ships': 0,
                'daily_soldiers': 0,
                'daily_tanks': 0,
                'daily_aircraft': 0,
                'daily_ships': 0,
                'soldier_gap': 0,
                'tank_gap': 0,
                'aircraft_gap': 0,
                'ship_gap': 0,
                'soldier_days': 0,
                'tank_days': 0,
                'aircraft_days': 0,
                'ship_days': 0
            }
    
    async def calculate_improvements_data(self, nations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate improvements breakdown data for all alliance nations."""
        try:
            # Get active nations
            active_nations = self.get_active_nations(nations)
            
            # Initialize improvement counters
            improvements = {
                # Power Plants
                'coalpower': 0,
                'oilpower': 0,
                'nuclearpower': 0,
                'windpower': 0,
                
                # Raw Resources
                'oilwell': 0,
                'coalmine': 0,
                'uramine': 0,
                'ironmine': 0,
                'bauxitemine': 0,
                'leadmine': 0,
                'farm': 0,
                
                # Manufacturing
                'gasrefinery': 0,
                'steelmill': 0,
                'aluminumrefinery': 0,
                'munitionsfactory': 0,
                
                # Civil
                'policestation': 0,
                'hospital': 0,
                'bank': 0,
                'supermarket': 0,
                'shopping_mall': 0,
                'stadium': 0,
                'subway': 0,
                'recyclingcenter': 0,
                
                # Military
                'barracks': 0,
                'factory': 0,
                'hangar': 0,
                'drydock': 0
            }
            
            total_cities = 0
            
            # Process each active nation
            for nation in active_nations:
                try:
                    cities = nation.get('cities', [])
                    if not cities:
                        continue
                    
                    total_cities += len(cities)
                    
                    # Sum improvements across all cities for this nation
                    for city in cities:
                        if not isinstance(city, dict):
                            continue
                        
                        # Power Plants
                        improvements['coalpower'] += self._safe_get(city, 'coalpower', 0, int)
                        improvements['oilpower'] += self._safe_get(city, 'oilpower', 0, int)
                        improvements['nuclearpower'] += self._safe_get(city, 'nuclearpower', 0, int)
                        improvements['windpower'] += self._safe_get(city, 'windpower', 0, int)
                        
                        # Raw Resources
                        improvements['oilwell'] += self._safe_get(city, 'oilwell', 0, int)
                        improvements['coalmine'] += self._safe_get(city, 'coalmine', 0, int)
                        improvements['uramine'] += self._safe_get(city, 'uramine', 0, int)
                        improvements['ironmine'] += self._safe_get(city, 'ironmine', 0, int)
                        improvements['bauxitemine'] += self._safe_get(city, 'bauxitemine', 0, int)
                        improvements['leadmine'] += self._safe_get(city, 'leadmine', 0, int)
                        improvements['farm'] += self._safe_get(city, 'farm', 0, int)
                        
                        # Manufacturing
                        improvements['gasrefinery'] += self._safe_get(city, 'gasrefinery', 0, int)
                        improvements['steelmill'] += self._safe_get(city, 'steelmill', 0, int)
                        improvements['aluminumrefinery'] += self._safe_get(city, 'aluminumrefinery', 0, int)
                        improvements['munitionsfactory'] += self._safe_get(city, 'munitionsfactory', 0, int)
                        improvements['factory'] += self._safe_get(city, 'factory', 0, int)
                        
                        # Civil
                        improvements['policestation'] += self._safe_get(city, 'policestation', 0, int)
                        improvements['hospital'] += self._safe_get(city, 'hospital', 0, int)
                        improvements['bank'] += self._safe_get(city, 'bank', 0, int)
                        improvements['supermarket'] += self._safe_get(city, 'supermarket', 0, int)
                        improvements['shopping_mall'] += self._safe_get(city, 'shopping_mall', 0, int)
                        improvements['stadium'] += self._safe_get(city, 'stadium', 0, int)
                        improvements['subway'] += self._safe_get(city, 'subway', 0, int)
                        improvements['recyclingcenter'] += self._safe_get(city, 'recyclingcenter', 0, int)
                        
                        # Military
                        improvements['barracks'] += self._safe_get(city, 'barracks', 0, int)
                        improvements['hangar'] += self._safe_get(city, 'airforcebase', 0, int)  # API uses 'airforcebase'
                        improvements['drydock'] += self._safe_get(city, 'drydock', 0, int)
                
                except Exception as e:
                    self._log_error(f"Error processing improvements for nation: {e}", e, "calculate_improvements_data")
                    continue
            
            # Calculate totals and averages
            total_power = (improvements['coalpower'] + improvements['oilpower'] + 
                          improvements['nuclearpower'] + improvements['windpower'])
            
            total_improvements = sum(improvements.values())
            avg_per_city = total_improvements / total_cities if total_cities > 0 else 0
            
            # Add calculated fields
            improvements.update({
                'total_power': total_power,
                'total_improvements': total_improvements,
                'total_cities': total_cities,
                'avg_per_city': avg_per_city,
                'active_nations': len(active_nations)
            })
            
            self.logger.info(f"Successfully calculated improvements data for {len(active_nations)} nations with {total_cities} cities")
            return improvements
            
        except Exception as e:
            self._log_error(f"Error calculating improvements data: {e}", e, "calculate_improvements_data")
            # Return empty structure on error
            return {
                'coalpower': 0, 'oilpower': 0, 'nuclearpower': 0, 'windpower': 0,
                'oilwell': 0, 'coalmine': 0, 'uramine': 0, 'ironmine': 0, 'bauxitemine': 0, 'leadmine': 0, 'farm': 0,
                'gasrefinery': 0, 'steelmill': 0, 'aluminumrefinery': 0, 'munitionsfactory': 0, 'factory': 0,
                'policestation': 0, 'hospital': 0, 'bank': 0, 'supermarket': 0, 'shopping_mall': 0, 'stadium': 0, 'subway': 0, 'recyclingcenter': 0,
                'barracks': 0, 'hangar': 0, 'drydock': 0,
                'total_power': 0, 'total_improvements': 0, 'total_cities': 0, 'avg_per_city': 0, 'active_nations': 0
            }
    
    def has_project(self, nation: Dict[str, Any], project_name: str) -> bool:
        """Check if a nation has a specific project."""
        # Input validation
        if not self._validate_input(nation, dict, "nation"):
            self.logger.warning("has_project: Invalid nation input")
            return False
        
        if not self._validate_input(project_name, str, "project_name"):
            self.logger.warning("has_project: Invalid project_name input")
            return False
        
        if not project_name.strip():
            self.logger.warning("has_project: Empty project_name provided")
            return False
        
        try:
            self.logger.debug(f"has_project: Checking project '{project_name}'")
            
            # Map project names to their corresponding API field names
            project_field_mapping = {
                'Iron Dome': 'iron_dome',
                'Missile Launch Pad': 'missile_launch_pad',
                'Nuclear Research Facility': 'nuclear_research_facility',
                'Nuclear Launch Facility': 'nuclear_launch_facility',
                'Vital Defense System': 'vital_defense_system',
                'Propaganda Bureau': 'propaganda_bureau',
                'Military Research Center': 'military_research_center',
                'Space Program': 'space_program'
            }
            
            # Use individual Boolean fields from the API
            field_name = project_field_mapping.get(project_name)
            if field_name:
                project_value = self._safe_get(nation, field_name, False, bool)
                self.logger.debug(f"has_project: Project '{project_name}' -> field '{field_name}' = {project_value}")
                return project_value
            else:
                self.logger.warning(f"has_project: Unknown project name '{project_name}'")
                return False
        
        except Exception as e:
            self._log_error(f"Unexpected error checking project '{project_name}'", e, "has_project")
            return False
    
    def calculate_military_purchase_limits(self, nation: Dict[str, Any]) -> Dict[str, int]:
        """Calculate daily military purchase limits and maximum capacities based on improvements."""
        cities_data = nation.get('cities', [])
        num_cities = nation.get('num_cities', 0)
        
        # Initialize totals
        total_barracks = 0
        total_factories = 0
        total_hangars = 0
        total_drydocks = 0
        
        # Check if we have detailed city data or just city count
        if isinstance(cities_data, list) and len(cities_data) > 0:
            # Sum improvements across all cities (detailed data)
            for city in cities_data:
                total_barracks += city.get('barracks', 0)
                total_factories += city.get('factory', 0)
                total_hangars += city.get('airforcebase', 0)  # API uses 'airforcebase' for hangars
                total_drydocks += city.get('drydock', 0)
        else:
            # Use estimated values based on city count (fallback)
            avg_improvements_per_city = 2  # Conservative estimate
            total_barracks = num_cities * avg_improvements_per_city
            total_factories = num_cities * avg_improvements_per_city
            total_hangars = num_cities * avg_improvements_per_city
            total_drydocks = num_cities * avg_improvements_per_city
        
        # Daily production limits
        soldier_daily_limit = total_barracks * 1000  # 1,000 soldiers per barracks per day
        tank_daily_limit = total_factories * 50      # 50 tanks per factory per day
        aircraft_daily_limit = total_hangars * 3     # 3 aircraft per hangar per day
        ship_daily_limit = total_drydocks * 1        # 1 ship per drydock per day
        
        # Apply military research bonuses (each level adds 20% capacity)
        ground_research = nation.get('ground_research', 0)
        air_research = nation.get('air_research', 0)
        naval_research = nation.get('naval_research', 0)
        
        ground_research_multiplier = 1 + (ground_research * 0.2)
        air_research_multiplier = 1 + (air_research * 0.2)
        naval_research_multiplier = 1 + (naval_research * 0.2)
        
        soldier_daily_limit = int(soldier_daily_limit * ground_research_multiplier)
        tank_daily_limit = int(tank_daily_limit * ground_research_multiplier)
        aircraft_daily_limit = int(aircraft_daily_limit * air_research_multiplier)
        ship_daily_limit = int(ship_daily_limit * naval_research_multiplier)
        
        # Apply Propaganda Bureau bonus (50% increase to soldier production only)
        if self.has_project(nation, 'Propaganda Bureau'):
            soldier_daily_limit = int(soldier_daily_limit * 1.5)
        
        # Base capacity limits from infrastructure
        soldier_max_capacity = total_barracks * 3000  # 3,000 soldiers max per barracks
        tank_max_capacity = total_factories * 250     # 250 tanks max per factory
        aircraft_max_capacity = total_hangars * 15    # 15 aircraft max per hangar
        ship_max_capacity = total_drydocks * 5        # 5 ships max per drydock
        
        # Apply military research multipliers to max capacities
        soldier_max_capacity = int(soldier_max_capacity * ground_research_multiplier)
        tank_max_capacity = int(tank_max_capacity * ground_research_multiplier)
        aircraft_max_capacity = int(aircraft_max_capacity * air_research_multiplier)
        ship_max_capacity = int(ship_max_capacity * naval_research_multiplier)
        
        # Apply purchased capacities (from Military Research Center or direct purchases)
        ground_bonus = nation.get('ground_capacity', 0) or 0
        air_bonus = nation.get('air_capacity', 0) or 0
        naval_bonus = nation.get('naval_capacity', 0) or 0
        
        # Also check under military_research if it exists (fallback for API format)
        if not ground_bonus and not air_bonus and not naval_bonus:
            military_research = nation.get('military_research', {})
            ground_bonus = military_research.get('ground_capacity', 0) or 0
            air_bonus = military_research.get('air_capacity', 0) or 0
            naval_bonus = military_research.get('naval_capacity', 0) or 0

        # Apply purchased capacities as flat bonuses (matching test expectations)
        soldier_max_capacity += ground_bonus
        tank_max_capacity += ground_bonus  # Same ground bonus applies to both soldiers and tanks
        aircraft_max_capacity += air_bonus
        ship_max_capacity += naval_bonus
        
        soldier_max_capacity = min(soldier_max_capacity, 60000)
        tank_max_capacity = min(tank_max_capacity, 5000)
        aircraft_max_capacity = min(aircraft_max_capacity, 300)
        ship_max_capacity = min(ship_max_capacity, 100)

        missile_limit = 0
        nuke_limit = 0
        
        # Enhanced missile production with Space Program
        if self.has_project(nation, 'Missile Launch Pad'):
            missile_limit = 2
            # Space Program allows +1 missile per day (3 total)
            if self.has_project(nation, 'Space Program'):
                missile_limit = 3
        
        # Enhanced nuke production with Space Program
        if self.has_project(nation, 'Nuclear Research Facility'):
            nuke_limit = 1
            if (self.has_project(nation, 'Nuclear Launch Facility') and 
                self.has_project(nation, 'Missile Launch Pad') and
                self.has_project(nation, 'Space Program')):
                nuke_limit = 2
            
        return {
            'soldiers': soldier_daily_limit,
            'tanks': tank_daily_limit,
            'aircraft': aircraft_daily_limit,
            'ships': ship_daily_limit,
            'missiles': missile_limit,
            'nukes': nuke_limit,
            'soldiers_max': soldier_max_capacity,
            'tanks_max': tank_max_capacity,
            'aircraft_max': aircraft_max_capacity,
            'ships_max': ship_max_capacity,
            'total_barracks': total_barracks,
            'total_factories': total_factories,
            'total_hangars': total_hangars,
            'total_drydocks': total_drydocks
        }
    
    def _get_default_military_limits(self) -> Dict[str, int]:
        """Return default military purchase limits."""
        return {
            'soldiers': 250,
            'tanks': 25,
            'aircraft': 5,
            'ships': 2,
            'soldiers_max': 1000,
            'tanks_max': 100,
            'aircraft_max': 20,
            'ships_max': 10
        }
    
    @commands.hybrid_command(name="alliance", help="🏭 Alliance Management - View Full Mill analysis and alliance statistics")
    async def alliance(self, ctx: commands.Context):
        """Alliance Management Command - Access Full Mill analysis and alliance statistics."""
        
        # Defer the response to prevent timeout for slash commands
        if hasattr(ctx, 'defer'):
            await ctx.defer()
        
        # Send initial loading message (ephemeral)
        loading_embed = discord.Embed(
            title="🏭 Cybertr0n Alliance Management",
            description="⏳ Loading alliance data...\n\nPlease select an operation.",
            color=discord.Color.from_rgb(255, 140, 0)
        )
        loading_msg = await ctx.send(embed=loading_embed)
        
        try:
            # Create alliance management view with Full Mill button
            alliance_view = FullMillView(ctx.author.id, self.bot, self)
            
            # Update embed with operation selection
            operation_embed = discord.Embed(
                title="🏭 Cybertr0n Alliance Management",
                description="Select an operation:\n\n"
                           "🎯 **Full Mill** - Analyze military capacity and units needed\n"
                           "📊 **Alliance Totals** - View comprehensive alliance statistics",
                color=discord.Color.from_rgb(255, 140, 0)
            )
            operation_embed.set_footer(text="Use the Full Mill button to start analysis")
            
            await loading_msg.edit(embed=operation_embed, view=alliance_view)
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error Loading Alliance Management",
                description=f"An error occurred while initializing Alliance Management:\n```{str(e)}```",
                color=discord.Color.red()
            )
            await loading_msg.edit(embed=error_embed)

    def get_nation_specialty(self, nation: Dict[str, Any]) -> str:
        """Get a nation's specialty based on military composition."""
        try:
            # Try to get military data from 'military' key first
            military = nation.get('military', {})
            
            # If military dict is empty, try to get units directly from nation dict
            if military:
                soldiers = military.get('soldiers', 0)
                tanks = military.get('tanks', 0)
                aircraft = military.get('aircraft', 0)
                ships = military.get('ships', 0)
            else:
                # Fallback to direct nation dict access (API format)
                soldiers = nation.get('soldiers', 0)
                tanks = nation.get('tanks', 0)
                aircraft = nation.get('aircraft', 0)
                ships = nation.get('ships', 0)
            
            total_units = soldiers + tanks + aircraft + ships
            if total_units == 0:
                return "Generalist"

            ground_percent = (soldiers + tanks) / total_units
            air_percent = aircraft / total_units
            naval_percent = ships / total_units

            if ground_percent >= air_percent and ground_percent >= naval_percent:
                return "Ground"
            elif air_percent >= naval_percent:
                return "Air"
            else:
                return "Naval"
                
        except Exception as e:
            self._log_error(f"Error getting nation specialty: {e}", e, "get_nation_specialty")
            return 'Generalist'

    def calculate_combat_score(self, nation: Dict[str, Any]) -> float:
        """Calculate a nation's combat effectiveness score."""
        # Direct implementation
        soldiers = nation.get('soldiers', 0)
        tanks = nation.get('tanks', 0)
        aircraft = nation.get('aircraft', 0)
        ships = nation.get('ships', 0)
        
        # Weighted combat score (tanks and aircraft are more valuable)
        return soldiers + (tanks * 2) + (aircraft * 3) + (ships * 4)

async def setup(bot: commands.Bot):
    """Setup function for loading the cog."""
    try:
        await bot.add_cog(AllianceManager(bot))
        logging.info("Alliance Management System loaded successfully!")
    except Exception as e:
        logging.error(f"Failed to load Alliance Management System: {e}")
        logging.error(traceback.format_exc())
        raise
