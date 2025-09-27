
import discord
from discord.ext import commands
import requests
import json
import os
from collections import defaultdict
from typing import List, Dict, Optional, Any
import asyncio
from datetime import datetime
import sys
import random
import logging
import traceback
import time
# AllianceManager will be imported dynamically when needed to avoid circular imports
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

# Import centralized query system only - no circular imports
try:
    from .query import create_query_instance
except ImportError:
    try:
        from Systems.PnW.MA.query import create_query_instance
    except ImportError:
        create_query_instance = None

# Import config for API keys and settings
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import PANDW_API_KEY, CYBERTRON_ALLIANCE_ID
from Systems.user_data_manager import UserDataManager

class NationListView(discord.ui.View):
    def __init__(self, nations: List[Dict[str, Any]], author_id: int, bot: commands.Bot, blitz_cog):
        super().__init__(timeout=300)  # 5 minute timeout
        self.nations = nations
        self.current_page = 0
        self.author_id = author_id
        self.bot = bot
        self.blitz_cog = blitz_cog
        self.nations_per_page = 3
        
        # Sort nations by score (descending)
        self.nations.sort(key=lambda n: n.get('score', 0), reverse=True)
        
        # Calculate total pages
        self.total_pages = (len(self.nations) + self.nations_per_page - 1) // self.nations_per_page

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensures only the person who triggered the command can use the buttons."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("⚠️ Only the command initiator can use these buttons!")
            return False
        return True

    def create_embed(self) -> discord.Embed:
        """Creates the embed for the current page of nations."""
        if not self.nations:
            embed = discord.Embed(
                title="⚠️ No Nations Found",
                description="No alliance nations could be retrieved.",
                color=discord.Color.red()
            )
            return embed

        start_idx = self.current_page * self.nations_per_page
        end_idx = min(start_idx + self.nations_per_page, len(self.nations))
        page_nations = self.nations[start_idx:end_idx]
        
        # Calculate page statistics
        total_score = sum(nation.get('score', 0) for nation in page_nations)
        total_cities = sum(nation.get('num_cities', 0) for nation in page_nations)
        
        party_number = self.current_page + 1
        total_parties = self.total_pages
        
        # Calculate war range for this party
        war_range_data = self.blitz_cog.calculate_party_war_range(page_nations)
        overlapping_min = war_range_data['overlapping_min']
        overlapping_max = war_range_data['overlapping_max']
        war_avg = war_range_data['avg_score']
        
        embed = discord.Embed(
            title=f"🎯 Cybertr0n Blitz Party #{party_number} - War Range: {overlapping_min:,.0f} - {overlapping_max:,.0f}",
            description=f"**War Range:** {overlapping_min:,.0f} - {overlapping_max:,.0f} (Avg Score: {war_avg:,.1f})\n**Total Parties:** {total_parties} | **Total Nations:** {len(self.nations)}",
            color=discord.Color.from_rgb(0, 150, 255)
        )
        embed.set_footer(text=f"Party {party_number} of {total_parties} | Generated at {datetime.now().strftime('%H:%M:%S')}")
        
        for i, nation in enumerate(page_nations, start_idx + 1):
            # Calculate MMR score
            mmr_score = (nation.get('num_cities', 0) * 10) + self.blitz_cog.calculate_combat_score(nation)
            
            # Strategic capabilities with comprehensive project detection
            strategic_info = []
            if self.blitz_cog.has_project(nation, 'Missile Launch Pad'):
                strategic_info.append("🚀")
            if self.blitz_cog.has_project(nation, 'Nuclear Research Facility'):
                strategic_info.append("☢️")
            if self.blitz_cog.has_project(nation, 'Iron Dome'):
                strategic_info.append("**ID**")
            if self.blitz_cog.has_project(nation, 'Vital Defense System'):
                strategic_info.append("**VDS**")
            
            strategic_text = ", ".join(strategic_info) if strategic_info else "❌ None"
            
            # Military specialty and advantages
            specialty = self.blitz_cog.get_nation_specialty(nation)
            specialty_emoji = {
                "Ground": "🪖",
                "Air": "✈️", 
                "Naval": "🚢",
                "Generalist": "⚖️"
            }
            
            # Get current military units
            current_soldiers = nation.get('soldiers', 0)
            current_tanks = nation.get('tanks', 0)
            current_aircraft = nation.get('aircraft', 0)
            current_ships = nation.get('ships', 0)
            
            # Calculate production limits
            try:
                limits = self.blitz_cog.calculate_military_purchase_limits(nation)
                daily_soldiers = limits.get('soldiers', 0)
                daily_tanks = limits.get('tanks', 0)
                daily_aircraft = limits.get('aircraft', 0)
                daily_ships = limits.get('ships', 0)
                max_soldiers = limits.get('soldiers_max', 0)
                max_tanks = limits.get('tanks_max', 0)
                max_aircraft = limits.get('aircraft_max', 0)
                max_ships = limits.get('ships_max', 0)
            except:
                # Fallback if calculation fails
                daily_soldiers = daily_tanks = daily_aircraft = daily_ships = 0
                max_soldiers = max_tanks = max_aircraft = max_ships = 0
            
            # Format military information compactly
            def format_military_line(emoji, current, daily, max_cap):
                return f"{emoji} {current:,}/{max_cap:,} (+{daily:,}/day)"
            
            # Create clickable leader name link
            leader_name = nation.get('leader_name', 'Unknown')
            nation_id = nation.get('id')
            if nation_id and leader_name != 'Unknown':
                leader_link = f"[{leader_name}](https://politicsandwar.com/nation/id={nation_id})"
            else:
                leader_link = leader_name
            
            # Add Discord username if available
            discord_info = ""
            discord_username = nation.get('discord_username')
            if discord_username:
                discord_display = nation.get('discord_display_name', discord_username)
                if discord_display != discord_username:
                    discord_info = f"**Discord:** {discord_display} (@{discord_username})\n"
                else:
                    discord_info = f"**Discord:** @{discord_username}\n"
            
            field_value = (
                f"**Leader:** {leader_link}\n"
                f"{discord_info}"
                f"**Cities:** {nation.get('num_cities', 0)} | **Score:** {nation.get('score', 0):,}\n"
                f"**MMR:** {mmr_score:.1f} | **Policy:** {nation.get('war_policy', 'Unknown')}\n"
                f"**Strategic:** {strategic_text}\n"
                f"{format_military_line('🪖', current_soldiers, daily_soldiers, max_soldiers)}\n"
                f"{format_military_line('🛡️', current_tanks, daily_tanks, max_tanks)}\n"
                f"{format_military_line('✈️', current_aircraft, daily_aircraft, max_aircraft)}\n"
                f"{format_military_line('🚢', current_ships, daily_ships, max_ships)}"
            )

            embed.add_field(
                name=f"{i}. {nation.get('nation_name', 'Unknown')} {specialty_emoji.get(specialty, '❓')}",
                value=field_value,
                inline=True
            )
            
        return embed

    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.secondary, disabled=True)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = max(0, self.current_page - 1)
        
        # Update button states
        self.previous_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page >= self.total_pages - 1)
        
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="▶️ Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = min(self.total_pages - 1, self.current_page + 1)
        
        # Update button states
        self.previous_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page >= self.total_pages - 1)
        
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        """Called when the view times out."""
        for item in self.children:
            item.disabled = True

class PartyView(discord.ui.View):
    def __init__(self, parties: List[Dict], blitz_cog):
        super().__init__(timeout=300)
        self.parties = parties
        self.current_page = 0
        self.blitz_cog = blitz_cog
        self.total_pages = len(parties)
        
        # Update button states
        if self.total_pages <= 1:
            self.previous_button.disabled = True
            self.next_button.disabled = True
        else:
            self.next_button.disabled = False

    def create_embed(self) -> discord.Embed:
        """Creates the embed for the current party."""
        if not self.parties:
            embed = discord.Embed(
                title="⚠️ No Blitz Parties Generated",
                description="No valid parties could be created with the current alliance data.",
                color=discord.Color.red()
            )
            return embed

        party = self.parties[self.current_page]
        party_members = party['members']
        
        party_name = party.get('party_name', f"Party {self.current_page + 1}")
        total_score = party.get('total_score', 0)
        strategic_count = party.get('strategic_count', 0)
        member_count = party.get('member_count', len(party_members))
        avg_score = total_score / member_count if member_count > 0 else 0
        
        # Get attack range and military advantages
        attack_range = party.get('attack_range', {})
        military_advantages = party.get('military_advantages', {})
        
        # Format attack range
        min_attackable = attack_range.get('min_attackable', 0)
        max_attackable = attack_range.get('max_attackable', 0)
        
        # Format military advantages
        ground_count = military_advantages.get('ground', 0)
        air_count = military_advantages.get('air', 0)
        naval_count = military_advantages.get('naval', 0)
        
        advantages_text = []
        if ground_count > 0:
            advantages_text.append(f"🪖 Ground: {ground_count}")
        if air_count > 0:
            advantages_text.append(f"✈️ Air: {air_count}")
        if naval_count > 0:
            advantages_text.append(f"🚢 Naval: {naval_count}")
        
        # Calculate party infrastructure statistics
        infrastructure_stats = []
        total_infra = 0
        infra_count = 0
        
        for member in party_members:
            if 'infrastructure_stats' in member:
                avg_infra = member['infrastructure_stats'].get('average', 0)
                if avg_infra > 0:
                    infrastructure_stats.append(avg_infra)
                    total_infra += avg_infra
                    infra_count += 1
        
        party_avg_infra = total_infra / infra_count if infra_count > 0 else 0
        infra_text = f"🏗️ Avg Infrastructure: {party_avg_infra:,.0f}" if party_avg_infra > 0 else ""
        
        # Calculate war range using the new function
        war_range_data = self.blitz_cog.calculate_party_war_range(party_members)
        overlapping_min = war_range_data['overlapping_min']
        overlapping_max = war_range_data['overlapping_max']
        war_avg = war_range_data['avg_score']
        
        # Format military specializations
        specializations = []
        if ground_count > 0:
            specializations.append(f"🪖 Ground ({ground_count})")
        if air_count > 0:
            specializations.append(f"✈️ Air ({air_count})")
        if naval_count > 0:
            specializations.append(f"🚢 Naval ({naval_count})")
        
        specialization_text = " | ".join(specializations) if specializations else "⚔️ Standard"
        
        # Enhanced description with war ranges
        embed = discord.Embed(
            title=f"🎯 {party_name} - War Range: {overlapping_min:,.0f} - {overlapping_max:,.0f}",
            description=(
                f"**War Range:** {overlapping_min:,.0f} - {overlapping_max:,.0f} (Avg Score: {war_avg:,.1f})\n"
                f"**Military Specializations:** {specialization_text}\n"
                f"**Strategic Capabilities:** {strategic_count}/3 nations with missiles/nukes\n"
                f"**Total Party Score:** {total_score:,} | **Members:** {member_count}/3\n"
                f"{infra_text}"
            ),
            color=discord.Color.from_rgb(0, 150, 255)
        )
        embed.set_footer(text=f"Party {self.current_page + 1} of {len(self.parties)} | War Range: {overlapping_min:,.0f} - {overlapping_max:,.0f} | Generated at {datetime.now().strftime('%H:%M:%S')}")
        
        for i, member in enumerate(party_members, 1):
            # Format advantages
            advantages = member.get('advantages', 'Standard')
            strategic = member.get('strategic', '❌')
            
            # Get infrastructure information
            infra_info = ""
            if 'infrastructure_stats' in member:
                avg_infra = member['infrastructure_stats'].get('average', 0)
                infra_tier = member['infrastructure_stats'].get('tier', 'Unknown')
                if avg_infra > 0:
                    infra_info = f"**Infrastructure:** {avg_infra:,.0f} ({infra_tier})\n"
            
            # Create clickable nation name link
            nation_name = member.get('nation_name', 'Unknown')
            nation_id = member.get('nation_id')
            if nation_id:
                nation_link = f"[{nation_name}](https://politicsandwar.com/nation/id={nation_id})"
            else:
                nation_link = nation_name
            
            # Create clickable leader name link
            leader_name = member.get('leader_name', 'Unknown')
            member_nation_id = member.get('nation_id')
            if member_nation_id and leader_name != 'Unknown':
                leader_link = f"[{leader_name}](https://politicsandwar.com/nation/id={member_nation_id})"
            else:
                leader_link = leader_name
            
            field_value = (
                f"**Leader:** {leader_link}\n"
                f"**Score:** {member.get('score', 0):,}\n"
                f"{infra_info}"
                f"**Advantages:** {advantages}\n"
                f"**Strategic:** {strategic}"
            )

            embed.add_field(
                name=f"{i}. {nation_link}",
                value=field_value,
                inline=True
            )
            
        return embed

    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.secondary, disabled=True)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = max(0, self.current_page - 1)
        
        # Update button states
        self.previous_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page >= self.total_pages - 1)
        
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="▶️ Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = min(self.total_pages - 1, self.current_page + 1)
        
        # Update button states
        self.previous_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page >= self.total_pages - 1)
        
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🔄 Resort Parties", style=discord.ButtonStyle.primary, emoji="🔄")
    async def resort_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Re-sort nations into new balanced parties."""
        await interaction.response.defer()
        
        try:
            # Get alliance nations again for fresh sorting
            alliance_id = str(interaction.guild.id)
            nations = await self.blitz_cog.get_alliance_nations(alliance_id)
            
            if not nations:
                embed = discord.Embed(
                    title="❌ No Nations Found",
                    description="No nations found for this alliance.",
                    color=discord.Color.red()
                )
                await interaction.followup.edit_message(embed=embed, view=None)
                return
            
            # Create new optimal parties
            parties = self.blitz_cog.create_balanced_parties(nations)
            
            if not parties:
                embed = discord.Embed(
                    title="❌ No Viable Parties",
                    description="Unable to create viable blitz parties.\n\n**Requirements:**\n• Parties of exactly 3 members\n• Compatible score ranges for same-target attacks\n• At least 1 member with Ground, Air, or Naval advantage\n• Preference for strategic capabilities (missiles/nukes)",
                    color=discord.Color.red()
                )
                await interaction.followup.edit_message(embed=embed, view=None)
                return
            
            # Load new team names and assign to parties
            team_names = self.blitz_cog._load_team_names()
            random.shuffle(team_names)
            
            # Prepare new party data
            party_info_display = []
            party_info_save = []
            
            for i, party in enumerate(parties):
                party_name = team_names[i % len(team_names)] if team_names else f"Party {i+1}"
                
                # Calculate party statistics
                total_score = sum(nation.get('score', 0) for nation in party)
                strategic_count = sum(1 for nation in party 
                                    if nation.get('military_analysis', {}).get('can_missile', False) or 
                                       nation.get('military_analysis', {}).get('can_nuke', False))
                
                # Calculate attack range for coordinated attacks
                scores = [nation.get('score', 0) for nation in party]
                min_score = min(scores)
                max_score = max(scores)
                min_attackable = max_score * 0.75  # Highest score's minimum target
                max_attackable = min_score * 2.5   # Lowest score's maximum target
                
                # Calculate military advantages
                ground_count = sum(1 for nation in party if self.blitz_cog._has_ground_advantage(nation))
                air_count = sum(1 for nation in party if self.blitz_cog._has_air_advantage(nation))
                naval_count = sum(1 for nation in party if self.blitz_cog._has_naval_advantage(nation))
                
                # Prepare member data
                member_data_display = []
                member_data_save = []
                
                for nation in party:
                    analysis = nation.get('military_analysis', {})
                    
                    # Display data
                    member_display = {
                        'nation_name': nation.get('nation_name', 'Unknown'),
                        'leader_name': nation.get('leader_name', 'Unknown'),
                        'score': nation.get('score', 0),
                        'advantages': ', '.join(analysis.get('advantages', ['Standard'])),
                        'strategic': '✅' if (analysis.get('can_missile', False) or analysis.get('can_nuke', False)) else '❌'
                    }
                    member_data_display.append(member_display)
                    
                    # Save data
                    member_save = {
                        'discord_id': nation.get('discord_id'),
                        'nation_id': nation.get('id'),
                        'nation_name': nation.get('nation_name', 'Unknown'),
                        'leader_name': nation.get('leader_name', 'Unknown'),
                        'score': nation.get('score', 0),
                        'party_name': party_name,
                        'military_advantages': analysis.get('advantages', []),
                        'can_missile': analysis.get('can_missile', False),
                        'can_nuke': analysis.get('can_nuke', False),
                        'purchase_limits': analysis.get('purchase_limits', {}),
                        'current_military': analysis.get('current_military', {}),
                        'attack_range': analysis.get('attack_range', {}),
                        'military_strength': analysis.get('military_strength', {}),
                        'soldiers': nation.get('soldiers', 0),
                        'tanks': nation.get('tanks', 0),
                        'aircraft': nation.get('aircraft', 0),
                        'ships': nation.get('ships', 0),
                        'missiles': nation.get('missiles', 0),
                        'nukes': nation.get('nukes', 0)
                    }
                    member_data_save.append(member_save)
                
                # Party info
                party_display = {
                    'party_name': party_name,
                    'members': member_data_display,
                    'total_score': total_score,
                    'strategic_count': strategic_count,
                    'member_count': len(party),
                    'attack_range': {
                        'min_attackable': min_attackable,
                        'max_attackable': max_attackable,
                        'min_score': min_score,
                        'max_score': max_score
                    },
                    'military_advantages': {
                        'ground': ground_count,
                        'air': air_count,
                        'naval': naval_count
                    }
                }
                party_info_display.append(party_display)
                
                party_save = {
                    'party_name': party_name,
                    'members': member_data_save,
                    'party_stats': {
                        'total_score': total_score,
                        'strategic_count': strategic_count,
                        'member_count': len(party),
                        'avg_score': total_score / len(party) if party else 0
                    },
                    'attack_range': {
                        'min_attackable': min_attackable,
                        'max_attackable': max_attackable,
                        'min_score': min_score,
                        'max_score': max_score
                    },
                    'military_advantages': {
                        'ground': ground_count,
                        'air': air_count,
                        'naval': naval_count
                    }
                }
                party_info_save.append(party_save)
            
            # Save the new party data
            await self.blitz_cog.save_blitz_parties(party_info_save)
            
            # Update this view with new data
            self.parties = party_info_display
            self.total_pages = len(party_info_display)
            self.current_page = 0
            
            # Update button states
            self.previous_button.disabled = True
            self.next_button.disabled = (self.total_pages <= 1)
            
            embed = self.create_embed()
            await interaction.followup.edit_message(embed=embed, view=self)
            
        except Exception as e:
            self.blitz_cog._log_error(f"Error in resort_button: {str(e)}", e, "PartyView.resort_button")
            embed = discord.Embed(
                title="❌ Resort Error",
                description=f"An error occurred while resorting parties: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.edit_message(embed=embed, view=None)

    @discord.ui.button(label="💾 Save Parties", style=discord.ButtonStyle.success, emoji="💾")
    async def save_parties_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Save all currently displayed blitz parties to the JSON file."""
        await interaction.response.defer()
        
        try:
            if not self.parties:
                embed = discord.Embed(
                    title="❌ No Parties to Save",
                    description="There are no parties currently displayed to save.",
                    color=discord.Color.red()
                )
                await interaction.followup.edit_message(embed=embed, view=self)
                return
            
            # Convert display data to save format
            party_info_save = []
            
            for party_display in self.parties:
                member_data_save = []
                
                for member_display in party_display['members']:
                    # Extract nation info from display data
                    member_save = {
                        'nation_name': member_display.get('nation_name', 'Unknown'),
                        'leader_name': member_display.get('leader_name', 'Unknown'),
                        'score': member_display.get('score', 0),
                        'party_name': party_display.get('party_name', 'Unknown'),
                        # Add other essential fields that might be missing
                        'discord_id': None,  # Will be None since we don't have it in display data
                        'nation_id': None,   # Will be None since we don't have it in display data
                        'military_advantages': member_display.get('advantages', '').split(', ') if member_display.get('advantages') else [],
                        'can_missile': '✅' in member_display.get('strategic', ''),
                        'can_nuke': '✅' in member_display.get('strategic', ''),
                        'purchase_limits': {},
                        'current_military': {},
                        'attack_range': {},
                        'military_strength': {},
                        'soldiers': 0,
                        'tanks': 0,
                        'aircraft': 0,
                        'ships': 0,
                        'missiles': 0,
                        'nukes': 0
                    }
                    member_data_save.append(member_save)
                
                party_save = {
                    'party_name': party_display.get('party_name', 'Unknown'),
                    'members': member_data_save,
                    'party_stats': {
                        'total_score': party_display.get('total_score', 0),
                        'strategic_count': party_display.get('strategic_count', 0),
                        'member_count': party_display.get('member_count', 0),
                        'avg_score': party_display.get('total_score', 0) / max(1, party_display.get('member_count', 1))
                    },
                    'attack_range': party_display.get('attack_range', {}),
                    'military_advantages': party_display.get('military_advantages', {})
                }
                party_info_save.append(party_save)
            
            # Save using the blitz cog's save function
            success = await self.blitz_cog.save_blitz_parties(party_info_save)
            
            if success:
                embed = discord.Embed(
                    title="✅ Parties Saved Successfully",
                    description=f"Saved {len(self.parties)} blitz parties with {sum(len(party.get('members', [])) for party in self.parties)} total nations.",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="📋 Saved Data Includes:",
                    value="• Nation names and leader names\n• Party assignments and names\n• Military advantages and strategic capabilities\n• Attack ranges and party statistics",
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="❌ Save Failed",
                    description="Failed to save the blitz parties data.",
                    color=discord.Color.red()
                )
            
            await interaction.followup.edit_message(embed=embed, view=self)
            
        except Exception as e:
            self.blitz_cog._log_error(f"Error in save_parties_button: {str(e)}", e, "PartyView.save_parties_button")
            embed = discord.Embed(
                title="❌ Save Error",
                description=f"An error occurred while saving parties: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        """Called when the view times out."""
        for item in self.children:
            item.disabled = True

class BlitzParties(commands.Cog):
    """Cybertr0n Blitz Party Generator - Creates balanced teams for coordinated attacks."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api_key = PANDW_API_KEY
        self.user_data_manager = UserDataManager()
        # Using centralized cache instead of local cache
        self._cache_expiry_seconds: int = 3600  # 1 hour (updated from 5 minutes)
        
        # Initialize logging
        self.logger = logging.getLogger(f"{__name__}.BlitzParties")
        self.error_count = 0
        
        # Initialize the centralized query instance
        try:
            if create_query_instance is not None:
                self.query_instance = create_query_instance(api_key=self.api_key, logger=self.logger)
                self.logger.info("Centralized query instance initialized successfully")
            else:
                self.query_instance = None
                self.logger.warning("Query instance creation function not available - import failed")
        except Exception as e:
            self.query_instance = None
            self.logger.error(f"Failed to initialize query instance: {str(e)}")
        
        # Initialize pnwkit only if available
        if PNWKIT_AVAILABLE:
            self.kit = pnwkit.QueryKit(self.api_key)
            self.logger.info(f"PNWKit initialized successfully from {PNWKIT_SOURCE}")
        else:
            self.kit = None
            self.logger.warning(f"PNWKit not available: {PNWKIT_ERROR}")
        
        # Cybertr0n Alliance ID from config
        self.cybertron_alliance_id = CYBERTRON_ALLIANCE_ID
        
        # Load team names from pets_level.json
        self.team_names = self._load_team_names()
        
        self.logger.info("BlitzParties cog initialized successfully")
    
    def _log_error(self, error_msg: str, exception: Exception = None, context: str = ""):
        """Centralized error logging with optional context."""
        self.error_count += 1
        
        if exception:
            self.logger.error(f"{error_msg}: {str(exception)}")
            self.logger.debug(f"Exception details: {traceback.format_exc()}")
        else:
            self.logger.error(error_msg)
        
        if context:
            self.logger.debug(f"Context: {context}")
    
    def _validate_input(self, data: Any, expected_type: type, field_name: str = "data") -> bool:
        """Validate input data type."""
        if not isinstance(data, expected_type):
            self.logger.warning(f"Invalid {field_name}: expected {expected_type.__name__}, got {type(data).__name__}")
            return False
        return True
    
    def _safe_get(self, data: dict, key: str, default: Any = None, expected_type: type = None) -> Any:
        """Safely get value from dictionary with optional type checking."""
        try:
            value = data.get(key, default)
            if expected_type and value is not None:
                if isinstance(expected_type, tuple):
                    if not isinstance(value, expected_type):
                        self.logger.warning(f"Type mismatch for key '{key}': expected {expected_type}, got {type(value)}")
                        return default
                else:
                    if not isinstance(value, expected_type):
                        if expected_type in (int, float) and isinstance(value, (int, float)):
                            return expected_type(value)
                        self.logger.warning(f"Type mismatch for key '{key}': expected {expected_type.__name__}, got {type(value).__name__}")
                        return default
            return value
        except Exception as e:
            self._log_error(f"Error accessing key '{key}' from data", e)
            return default

    def _load_team_names(self) -> List[str]:
        """Load team names from pets_level.json TEAM_NAMES category."""
        try:
            pets_level_path = os.path.join(os.path.dirname(__file__), '..', '..', 'Data', 'pets_level.json')
            
            if not os.path.exists(pets_level_path):
                self.logger.warning(f"pets_level.json not found at {pets_level_path}, using fallback team names")
                return self._get_fallback_team_names()
            
            with open(pets_level_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                team_names = data.get('TEAM_NAMES', [])
                
                if not team_names:
                    self.logger.warning("No team names found in pets_level.json, using fallback")
                    return self._get_fallback_team_names()
                
                self.logger.debug(f"Loaded {len(team_names)} team names from pets_level.json")
                return team_names
                
        except json.JSONDecodeError as e:
            self._log_error("Invalid JSON format in pets_level.json", e)
            return self._get_fallback_team_names()
        except FileNotFoundError as e:
            self._log_error("pets_level.json file not found", e)
            return self._get_fallback_team_names()
        except Exception as e:
            self._log_error("Unexpected error loading team names", e)
            return self._get_fallback_team_names()
    
    def _get_fallback_team_names(self) -> List[str]:
        """Fallback team names if pets_level.json is unavailable."""
        return ["Alpha Squad", "Beta Team", "Gamma Force", "Delta Unit", "Echo Division"]

    def calculate_infrastructure_stats(self, nation: Dict[str, Any]) -> Dict[str, float]:
        """Calculate infrastructure statistics for a nation including average infrastructure per city."""
        cities_data = nation.get('cities', [])
        num_cities = nation.get('num_cities', 0)
        
        if not isinstance(cities_data, list) or len(cities_data) == 0:
            # If no detailed city data, estimate based on nation score and city count
            estimated_avg_infra = max(50, (nation.get('score', 0) / num_cities) * 12) if num_cities > 0 else 50
            return {
                'average_infrastructure': estimated_avg_infra,
                'total_infrastructure': estimated_avg_infra * num_cities,
                'min_infrastructure': estimated_avg_infra * 0.8,  # Estimate range
                'max_infrastructure': estimated_avg_infra * 1.2,
                'infrastructure_range': estimated_avg_infra * 0.4,
                'infrastructure_tier': self._get_infrastructure_tier(estimated_avg_infra),
                'has_detailed_data': False
            }
        
        # Calculate from detailed city data
        infrastructure_levels = []
        for city in cities_data:
            infra = city.get('infrastructure', 0)
            if infra > 0:  # Only count cities with infrastructure data
                infrastructure_levels.append(infra)
        
        if not infrastructure_levels:
            # Fallback if no infrastructure data in cities
            estimated_avg_infra = max(50, (nation.get('score', 0) / num_cities) * 12) if num_cities > 0 else 50
            return {
                'average_infrastructure': estimated_avg_infra,
                'total_infrastructure': estimated_avg_infra * num_cities,
                'min_infrastructure': estimated_avg_infra,
                'max_infrastructure': estimated_avg_infra,
                'infrastructure_range': 0,
                'infrastructure_tier': self._get_infrastructure_tier(estimated_avg_infra),
                'has_detailed_data': False
            }
        
        avg_infra = sum(infrastructure_levels) / len(infrastructure_levels)
        min_infra = min(infrastructure_levels)
        max_infra = max(infrastructure_levels)
        infra_range = max_infra - min_infra
        total_infra = sum(infrastructure_levels)
        
        return {
            'average_infrastructure': avg_infra,
            'total_infrastructure': total_infra,
            'min_infrastructure': min_infra,
            'max_infrastructure': max_infra,
            'infrastructure_range': infra_range,
            'infrastructure_tier': self._get_infrastructure_tier(avg_infra),
            'has_detailed_data': True
        }
    
    def _get_infrastructure_tier(self, avg_infrastructure: float) -> str:
        """Categorize nations by infrastructure tier for war compatibility (lower infra is better)."""
        if avg_infrastructure < 500:
            return "Perfect"    # Ideal for war
        elif avg_infrastructure < 1000:
            return "Great"      # Very good for war
        elif avg_infrastructure < 1500:
            return "Good"       # Good for war
        elif avg_infrastructure < 2000:
            return "Average"    # Average for war
        elif avg_infrastructure < 2500:
            return "Bad"        # Poor for war
        elif avg_infrastructure < 3000:
            return "Horrible"   # Very poor for war
        else:
            return "Terrible"   # Worst for war
    
    def _calculate_infrastructure_compatibility(self, nation1: Dict[str, Any], nation2: Dict[str, Any]) -> float:
        """Calculate infrastructure compatibility score between two nations (0-1, higher is better)."""
        infra1 = nation1.get('infrastructure_stats', {})
        infra2 = nation2.get('infrastructure_stats', {})
        
        avg1 = infra1.get('average_infrastructure', 0)
        avg2 = infra2.get('average_infrastructure', 0)
        
        if avg1 == 0 or avg2 == 0:
            return 0.5  # Neutral compatibility if no data
        
        # Calculate percentage difference
        higher = max(avg1, avg2)
        lower = min(avg1, avg2)
        percentage_diff = (higher - lower) / higher
        
        # Convert to compatibility score (closer infrastructure = higher score)
        # 0% difference = 1.0 compatibility
        # 50% difference = 0.5 compatibility  
        # 100% difference = 0.0 compatibility
        compatibility = max(0.0, 1.0 - (percentage_diff * 2))
        
        return compatibility

    def calculate_military_purchase_limits(self, nation: Dict[str, Any]) -> Dict[str, int]:
        """Calculate daily military purchase limits and maximum capacities based on improvements."""
        # Direct implementation
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
            'soldiers_daily': soldier_daily_limit,
            'tanks_daily': tank_daily_limit,
            'aircraft_daily': aircraft_daily_limit,
            'ships_daily': ship_daily_limit,
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

    def calculate_military_advantage(self, nation: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate a nation's military advantages based on heavy unit concentrations and high purchase capacity."""
        purchase_limits = self.calculate_military_purchase_limits(nation)
        current_military = {
            'soldiers': nation.get('soldiers', 0),
            'tanks': nation.get('tanks', 0),
            'aircraft': nation.get('aircraft', 0),
            'ships': nation.get('ships', 0),
            'missiles': nation.get('missiles', 0),
            'nukes': nation.get('nukes', 0)
        }
        
        # Calculate theoretical maximum capacity based on 5/5/5/3 builds per city
        # Use explicit city count when available; otherwise fall back to detailed cities list length
        cities_list = nation.get('cities', [])
        if isinstance(cities_list, list):
            num_cities = nation.get('num_cities', len(cities_list))
        else:
            num_cities = nation.get('num_cities', 0)
        
        # Theoretical max units with 5/5/5/3 build per city
        # Each barracks can hold ~3000 soldiers, factory ~500 tanks, hangar ~51 aircraft, harbor ~18 ships
        max_soldiers_per_city = 5 * 3000  # 5 barracks * 3000 soldiers each
        max_tanks_per_city = 5 * 500     # 5 factories * 500 tanks each  
        max_aircraft_per_city = 5 * 51   # 5 hangars * 51 aircraft each
        max_ships_per_city = 3 * 18      # 3 harbors * 18 ships each
        
        theoretical_max_soldiers = num_cities * max_soldiers_per_city
        theoretical_max_tanks = num_cities * max_tanks_per_city
        theoretical_max_aircraft = num_cities * max_aircraft_per_city
        theoretical_max_ships = num_cities * max_ships_per_city
        
        # Calculate current unit percentages compared to theoretical max
        soldier_percentage = (current_military['soldiers'] / theoretical_max_soldiers * 100) if theoretical_max_soldiers > 0 else 0
        tank_percentage = (current_military['tanks'] / theoretical_max_tanks * 100) if theoretical_max_tanks > 0 else 0
        aircraft_percentage = (current_military['aircraft'] / theoretical_max_aircraft * 100) if theoretical_max_aircraft > 0 else 0
        ship_percentage = (current_military['ships'] / theoretical_max_ships * 100) if theoretical_max_ships > 0 else 0
        
        # Calculate combined ground percentage with tanks weighing 2x more than soldiers
        # Ground score = (soldiers * 1) + (tanks * 2), compared to theoretical max ground score
        current_ground_score = current_military['soldiers'] + (current_military['tanks'] * 2)
        theoretical_max_ground_score = theoretical_max_soldiers + (theoretical_max_tanks * 2)
        ground_percentage = (current_ground_score / theoretical_max_ground_score * 100) if theoretical_max_ground_score > 0 else 0
        
        # Determine if nation is "heavy" in each category (>60% of theoretical max)
        heavy_threshold_percentage = 60.0
        
        is_heavy_ground = ground_percentage > heavy_threshold_percentage
        is_heavy_air = aircraft_percentage > heavy_threshold_percentage
        is_heavy_naval = ship_percentage > heavy_threshold_percentage
        
        # Check for high purchase capacity (minimum thresholds for advantages)
        high_ground_purchase = (purchase_limits['soldiers'] >= 10000 or purchase_limits['tanks'] >= 1500)
        high_air_purchase = purchase_limits['aircraft'] >= 200
        high_naval_purchase = purchase_limits['ships'] >= 40
        
        # Determine advantages
        advantages = []
        has_ground_advantage = is_heavy_ground and high_ground_purchase
        has_air_advantage = is_heavy_air and high_air_purchase
        has_naval_advantage = is_heavy_naval and high_naval_purchase
        
        if has_ground_advantage:
            advantages.append("Ground Advantage")
        if has_air_advantage:
            advantages.append("Air Advantage")
        if has_naval_advantage:
            advantages.append("Naval Advantage")
        
        # Strategic capabilities
        can_missile = self.has_project(nation, 'Missile Launch Pad')
        can_nuke = self.has_project(nation, 'Nuclear Research Facility')
        
        if can_missile:
            advantages.append("Missile Capable")
        if can_nuke:
            advantages.append("Nuclear Capable")
            
        # Calculate attack range based on score
        nation_score = nation.get('score', 0)
        min_attack_score = nation_score * 0.75  # -25%
        max_attack_score = nation_score * 2.5   # +150%
        
        return {
            'advantages': advantages,
            'purchase_limits': purchase_limits,
            'current_military': current_military,
            'can_missile': can_missile,
            'can_nuke': can_nuke,
            'has_ground_advantage': has_ground_advantage,
            'has_air_advantage': has_air_advantage,
            'has_naval_advantage': has_naval_advantage,
            'attack_range': {
                'min_score': min_attack_score,
                'max_score': max_attack_score,
                'nation_score': nation_score
            },
            'military_composition': {
                'current_soldiers': current_military['soldiers'],
                'current_tanks': current_military['tanks'],
                'current_aircraft': current_military['aircraft'],
                'current_ships': current_military['ships'],
                'theoretical_max_soldiers': theoretical_max_soldiers,
                'theoretical_max_tanks': theoretical_max_tanks,
                'theoretical_max_aircraft': theoretical_max_aircraft,
                'theoretical_max_ships': theoretical_max_ships,
                'soldier_percentage': soldier_percentage,
                'tank_percentage': tank_percentage,
                'aircraft_percentage': aircraft_percentage,
                'ship_percentage': ship_percentage,
                'ground_percentage': ground_percentage,
                'current_ground_score': current_ground_score,
                'theoretical_max_ground_score': theoretical_max_ground_score,
                'is_heavy_ground': is_heavy_ground,
                'is_heavy_air': is_heavy_air,
                'is_heavy_naval': is_heavy_naval,
                'high_ground_purchase': high_ground_purchase,
                'high_air_purchase': high_air_purchase,
                'high_naval_purchase': high_naval_purchase,
                'heavy_threshold_percentage': heavy_threshold_percentage
            }
        }

    def validate_attack_range(self, attacker_score: float, defender_score: float) -> bool:
        """Validate if an attacker can attack a defender based on score range."""
        min_score = attacker_score * 0.75  # -25%
        max_score = attacker_score * 2.5   # +150%
        return min_score <= defender_score <= max_score
    
    def calculate_party_war_range(self, party_members: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate the war range for a party - showing the range that ALL members can attack together."""
        if not party_members:
            return {'min_range': 0, 'max_range': 0, 'avg_score': 0, 'overlapping_min': 0, 'overlapping_max': 0}
        
        # Get all nation scores
        scores = [member.get('score', 0) for member in party_members]
        
        # Calculate individual attack ranges for each nation (0.75x to 2.5x their score)
        individual_ranges = []
        for score in scores:
            min_attack = score * 0.75   # Can attack down to 75% of their score
            max_attack = score * 2.5    # Can attack up to 250% of their score
            individual_ranges.append((min_attack, max_attack))
        
        # Find the overlapping range that ALL nations can attack
        # The lowest target ALL can attack is the MAX of individual minimums
        # The highest target ALL can attack is the MIN of individual maximums
        overlapping_min = max(range[0] for range in individual_ranges)
        overlapping_max = min(range[1] for range in individual_ranges)
        
        # Calculate average party score
        total_score = sum(scores)
        avg_score = total_score / len(party_members)
        
        # Calculate theoretical range based on average (for reference)
        theoretical_min = avg_score * 0.75
        theoretical_max = avg_score * 2.5
        
        return {
            'min_range': theoretical_min,      # Theoretical range based on average
            'max_range': theoretical_max,      # Theoretical range based on average
            'avg_score': avg_score,            # Average score of party
            'total_score': total_score,        # Total score of party
            'overlapping_min': overlapping_min, # ACTUAL: Lowest target ALL 3 can attack
            'overlapping_max': overlapping_max, # ACTUAL: Highest target ALL 3 can attack
            'individual_ranges': individual_ranges # Individual ranges for debugging
        }

    async def get_alliance_nations(self, alliance_id: str, force_refresh: bool = False) -> Optional[List[Dict[str, Any]]]:
        """Fetch alliance nations using centralized cache from UserDataManager."""
        # Input validation
        if not alliance_id or not str(alliance_id).strip():
            self.logger.warning("get_alliance_nations: Invalid alliance_id provided")
            return None
        
        try:
            # Check centralized UserDataManager cache first unless forcing refresh
            if not force_refresh:
                try:
                    # Use centralized UserDataManager for caching
                    user_data_manager = UserDataManager()
                    cache_key = f"alliance_data_{alliance_id}"
                    
                    alliance_cache = await user_data_manager.get_json_data('alliance_cache', {})
                    cache_entry = alliance_cache.get(cache_key)
                    
                    if cache_entry and isinstance(cache_entry, dict):
                        nations = cache_entry.get('nations', [])
                        if nations:
                            self.logger.debug(f"get_alliance_nations: Using centralized cache for alliance {alliance_id}")
                            return nations
                except Exception as cache_err:
                    self.logger.warning(f"get_alliance_nations: Cache read failed: {cache_err}")
            
            # Local in-memory cache check (fast path) - fallback only
            cache_key = str(alliance_id)
            if not force_refresh and cache_key in self._alliance_nations_cache:
                entry = self._alliance_nations_cache[cache_key]
                if time.time() - entry.get('timestamp', 0) < self._cache_expiry_seconds:
                    data = entry.get('data') or []
                    if data:
                        self.logger.debug(f"get_alliance_nations: Local cache hit for alliance {alliance_id} ({len(data)} nations)")
                        return data

            # Try to use AllianceManager if available
            alliance_cog = self.bot.get_cog('AllianceManager')
            if alliance_cog:
                self.logger.debug(f"get_alliance_nations: Using AllianceManager cog for alliance {alliance_id}")
                nations = await alliance_cog.get_alliance_nations(int(alliance_id), force_refresh=force_refresh)
                if nations:
                    self._alliance_nations_cache[cache_key] = { 'data': nations, 'timestamp': time.time() }
                return nations
            
            # Use centralized query instance
            if self.query_instance:
                self.logger.debug(f"get_alliance_nations: Using centralized query instance for alliance {alliance_id}")
                nations = await self.query_instance.get_alliance_nations(alliance_id, bot=self.bot, force_refresh=force_refresh)
                if nations:
                    self._alliance_nations_cache[cache_key] = { 'data': nations, 'timestamp': time.time() }
                return nations
            else:
                error_msg = "Query instance not available and AllianceManager not found"
                self.logger.error(f"get_alliance_nations: {error_msg}")
                raise Exception(error_msg)
            
        except ValueError as e:
            # Re-raise configuration errors
            raise e
        except AttributeError as e:
            self._log_error(f"AllianceManager cog not available or method missing for alliance {alliance_id}", e, "get_alliance_nations")
            return None
        except Exception as e:
            self._log_error(f"Unexpected error while fetching alliance {alliance_id}", e, "get_alliance_nations")
            raise Exception(f"API error: {str(e)}")

    def get_nation_specialty(self, nation: Dict[str, Any]) -> str:
        """Get a nation's specialty - delegates to AllianceManager if available."""
        # Try to use AllianceManager if available
        alliance_cog = self.bot.get_cog('AllianceManager')
        if alliance_cog and hasattr(alliance_cog, 'get_nation_specialty'):
            return alliance_cog.get_nation_specialty(nation)
        
        # Fallback to original implementation
        soldiers = nation.get('soldiers', 0)
        tanks = nation.get('tanks', 0)
        aircraft = nation.get('aircraft', 0)  # Note: API uses 'aircraft' not 'planes'
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

    def calculate_combat_score(self, nation: Dict[str, Any]) -> float:
        """Calculate a nation's combat effectiveness score."""
        # Direct implementation
        soldiers = nation.get('soldiers', 0)
        tanks = nation.get('tanks', 0)
        aircraft = nation.get('aircraft', 0)
        ships = nation.get('ships', 0)
        
        # Weighted combat score (tanks and aircraft are more valuable)
        return soldiers + (tanks * 2) + (aircraft * 3) + (ships * 4)

    def has_project(self, nation: Dict[str, Any], project_name: str) -> bool:
        """Check if a nation has a specific project - delegates to AllianceManager if available."""
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
            # Try to use AllianceManager if available
            alliance_cog = self.bot.get_cog('AllianceManager')
            if alliance_cog:
                self.logger.debug(f"has_project: Using AllianceManager cog for project '{project_name}'")
                return alliance_cog.has_project(nation, project_name)
            
            # Fallback to original implementation
            self.logger.debug(f"has_project: Using fallback implementation for project '{project_name}'")
            
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
        
        except AttributeError as e:
            self._log_error(f"AllianceManager cog not available or method missing for project '{project_name}'", e, "has_project")
            return False
        except Exception as e:
            self._log_error(f"Unexpected error checking project '{project_name}'", e, "has_project")
            return False

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

    def get_active_nations(self, nations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter nations to exclude vacation mode and applicant members - delegates to AllianceManager if available."""
        # Input validation
        if not self._validate_input(nations, list, "nations"):
            self.logger.warning("get_active_nations: Invalid nations input, returning empty list")
            return []
        
        if not nations:
            self.logger.debug("get_active_nations: Empty nations list provided")
            return []
        
        try:
            # Try to use AllianceManager if available
            alliance_cog = self.bot.get_cog('AllianceManager')
            if alliance_cog:
                self.logger.debug("get_active_nations: Using AllianceManager cog")
                return alliance_cog.get_active_nations(nations)
            
            # Fallback to original implementation
            self.logger.debug(f"get_active_nations: Using fallback implementation for {len(nations)} nations")
            
            active_nations = []
            for i, nation in enumerate(nations):
                try:
                    if not isinstance(nation, dict):
                        self.logger.warning(f"get_active_nations: Nation at index {i} is not a dictionary, skipping")
                        continue
                    
                    # Skip vacation mode members
                    vacation_turns = self._safe_get(nation, 'vacation_mode_turns', 0, int)
                    if vacation_turns > 0:
                        continue
                    
                    # Skip applicants (alliance_position "APPLICANT")
                    alliance_position = self._safe_get(nation, 'alliance_position', '', str)
                    if alliance_position == 'APPLICANT':
                        continue
                    
                    active_nations.append(nation)
                except (AttributeError, TypeError) as e:
                    self._log_error(f"Error processing nation at index {i}", e, "get_active_nations")
                    continue
            
            self.logger.info(f"get_active_nations: Filtered {len(nations)} nations to {len(active_nations)} active nations")
            return active_nations
            
        except AttributeError as e:
            self._log_error("AllianceManager cog not available or method missing", e, "get_active_nations")
            return []
        except Exception as e:
            self._log_error("Unexpected error in get_active_nations", e, "get_active_nations")
            return []

    def create_balanced_parties(self, nations: List[Dict[str, Any]], num_parties: int = 3) -> List[List[Dict[str, Any]]]:
        """Create optimal parties of 3 for coordinated same-target attacks."""
        try:
            # Input validation
            if not self._validate_input(nations, list, "nations"):
                self.logger.warning("Invalid nations input provided to create_balanced_parties")
                return []
            
            if not nations:
                self.logger.info("No nations provided for party creation")
                return []
            
            if num_parties < 1:
                self.logger.warning(f"Invalid num_parties value: {num_parties}, defaulting to 3")
                num_parties = 3
            
            self.logger.info(f"Creating balanced parties from {len(nations)} nations")
            
            # Filter active nations (exclude VM and applicants) and calculate military advantages
            active_nations = []
            for nation in nations:
                try:
                    if not isinstance(nation, dict):
                        self.logger.warning(f"Skipping invalid nation data: {type(nation)}")
                        continue
                    
                    # Skip vacation mode members
                    vacation_turns = self._safe_get(nation, 'vacation_mode_turns', 0, int)
                    if vacation_turns > 0:
                        self.logger.debug(f"Skipping nation {nation.get('nation_name', 'Unknown')} - on vacation ({vacation_turns} turns)")
                        continue
                    
                    # Skip applicants (alliance_position "APPLICANT")
                    alliance_position = self._safe_get(nation, 'alliance_position', '', str)
                    if alliance_position == 'APPLICANT':
                        self.logger.debug(f"Skipping nation {nation.get('nation_name', 'Unknown')} - applicant status")
                        continue
                    
                    military_data = self.calculate_military_advantage(nation)
                    nation['military_analysis'] = military_data
                    
                    # Add infrastructure analysis for grouping compatibility
                    infrastructure_data = self.calculate_infrastructure_stats(nation)
                    nation['infrastructure_stats'] = infrastructure_data
                    
                    active_nations.append(nation)
                except Exception as e:
                    self._log_error(f"Error processing nation {nation.get('nation_name', 'Unknown')} in create_balanced_parties", e, "create_balanced_parties")
                    continue
            
            if len(active_nations) < 3:
                self.logger.warning(f"Insufficient active nations for party creation: {len(active_nations)} (need at least 3)")
                return []  # Need at least 3 nations for a party
            
            self.logger.info(f"Processing {len(active_nations)} active nations for party optimization")
            
            # Apply strategic exclusions for optimal party formation
            strategically_optimized_nations = self._find_optimal_exclusions(active_nations)
            
            # Create optimal parties of exactly 3 members each
            optimal_parties = self._create_optimal_three_member_parties(strategically_optimized_nations)
            
            self.logger.info(f"Successfully created {len(optimal_parties)} balanced parties")
            return optimal_parties
            
        except Exception as e:
            self._log_error("Error in create_balanced_parties", e, "create_balanced_parties")
            return []

    def _create_optimal_three_member_parties(self, nations: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Create parties of exactly 3 members with optimal composition."""
        try:
            # Input validation
            if not self._validate_input(nations, list, "nations"):
                self.logger.warning("Invalid nations input provided to _create_optimal_three_member_parties")
                return []
            
            if not nations:
                self.logger.info("No nations provided for optimal party creation")
                return []
            
            if len(nations) < 3:
                self.logger.warning(f"Insufficient nations for party creation: {len(nations)} (need at least 3)")
                return []
            
            self.logger.info(f"Creating optimal 3-member parties from {len(nations)} nations")
            
            parties = []
            used_nations = set()
            
            # Sort nations by score for better distribution and grouping
            try:
                sorted_nations = sorted(nations, key=lambda x: self._safe_get(x, 'score', 0, (int, float)))
                self.logger.debug(f"Sorted {len(sorted_nations)} nations by score")
            except Exception as e:
                self._log_error("Error sorting nations by score", e, "_create_optimal_three_member_parties")
                sorted_nations = nations  # Fallback to unsorted
            
            # Enhanced categorization for optimal party formation
            strategic_nations = []
            ground_nations = []
            air_nations = []
            naval_nations = []
            
            try:
                strategic_nations = [n for n in sorted_nations if n.get('military_analysis', {}).get('can_missile') or n.get('military_analysis', {}).get('can_nuke')]
                ground_nations = [n for n in sorted_nations if self._has_ground_advantage(n)]
                air_nations = [n for n in sorted_nations if self._has_air_advantage(n)]
                naval_nations = [n for n in sorted_nations if self._has_naval_advantage(n)]
                
                self.logger.debug(f"Categorized nations - Strategic: {len(strategic_nations)}, Ground: {len(ground_nations)}, Air: {len(air_nations)}, Naval: {len(naval_nations)}")
            except Exception as e:
                self._log_error("Error categorizing nations in _create_optimal_three_member_parties", e, "_create_optimal_three_member_parties")
            
            all_nations = sorted_nations.copy()
            
            # Create parties until we can't make more valid 3-member parties
            while len([n for n in all_nations if id(n) not in used_nations]) >= 3:
                try:
                    available_nations = [n for n in all_nations if id(n) not in used_nations]
                    self.logger.debug(f"Creating party from {len(available_nations)} available nations")
                    
                    party = self._create_single_optimal_party(
                        available_nations,
                        strategic_nations,
                        ground_nations,
                        air_nations,
                        naval_nations,
                        used_nations
                    )
                    
                    if party and len(party) == 3:
                        parties.append(party)
                        for nation in party:
                            used_nations.add(id(nation))
                        self.logger.debug(f"Created party {len(parties)} with 3 members")
                    else:
                        self.logger.debug("Could not create valid 3-member party, stopping")
                        break  # Can't create more valid parties
                except Exception as e:
                    self._log_error("Error creating single optimal party", e, "_create_optimal_three_member_parties")
                    break
            
            self.logger.info(f"Successfully created {len(parties)} optimal 3-member parties")
            return parties
            
        except Exception as e:
            self._log_error("Error in _create_optimal_three_member_parties", e, "_create_optimal_three_member_parties")
            return []

    def _create_single_optimal_party(self, available_nations: List[Dict[str, Any]], 
                                   strategic_nations: List[Dict[str, Any]], 
                                   ground_nations: List[Dict[str, Any]],
                                   air_nations: List[Dict[str, Any]],
                                   naval_nations: List[Dict[str, Any]], 
                                   used_nations: set) -> List[Dict[str, Any]]:
        """Create a single optimal party of 3 members - PRIORITIZING WAR RANGE MATCHING."""
        try:
            # Input validation
            if not self._validate_input(available_nations, list, "available_nations"):
                self.logger.warning("Invalid available_nations input for single optimal party creation")
                return []
                
            if len(available_nations) < 3:
                self.logger.debug(f"Insufficient nations for party creation: {len(available_nations)} < 3")
                return []
            
            # Filter out already used nations
            available_unused = [n for n in available_nations if id(n) not in used_nations]
            if len(available_unused) < 3:
                self.logger.debug(f"Insufficient unused nations for party creation: {len(available_unused)} < 3")
                return []
            
            # Find the best combination of 3 nations
            best_party = None
            best_score = -1
            
            # FIRST PRIORITY: Find parties with VERY TIGHT war ranges
            # Sort by score to find nations with similar scores more efficiently
            try:
                score_sorted = sorted(available_unused, key=lambda x: self._safe_get(x, 'score', 0, int))
                self.logger.debug(f"Successfully sorted {len(score_sorted)} nations by score")
            except Exception as e:
                self.logger.warning(f"Error sorting nations by score: {e}")
                score_sorted = available_unused
            
            combinations_evaluated = 0
            valid_parties_found = 0
            
            for i in range(len(available_unused)):
                for j in range(i + 1, len(available_unused)):
                    for k in range(j + 1, len(available_unused)):
                        try:
                            combinations_evaluated += 1
                            candidate_party = [available_unused[i], available_unused[j], available_unused[k]]
                            
                            # Check if this party meets basic requirements
                            if self._is_valid_party(candidate_party):
                                valid_parties_found += 1
                                party_score = self._evaluate_party_quality(candidate_party)
                                
                                if party_score > best_score:
                                    best_party = candidate_party
                                    best_score = party_score
                                    self.logger.debug(f"New best party found with score: {party_score}")
                        except Exception as e:
                            self.logger.warning(f"Error evaluating party combination {i},{j},{k}: {e}")
                            continue
            
            self.logger.info(f"Evaluated {combinations_evaluated} combinations, found {valid_parties_found} valid parties")
            if best_party:
                self.logger.info(f"Best party created with score: {best_score}")
            else:
                self.logger.warning("No valid party could be created from available nations")
                
            return best_party if best_party else []
            
        except Exception as e:
            self._log_error("Error in _create_single_optimal_party", e, "single_optimal_party_creation")
            return []

    def _is_valid_party(self, party: List[Dict[str, Any]]) -> bool:
        """Check if a party meets the basic requirements."""
        try:
            # Input validation
            if not self._validate_input(party, list, "party"):
                self.logger.warning("Invalid party input for validation")
                return False
                
            if len(party) != 3:
                self.logger.debug(f"Invalid party size: {len(party)} (expected 3)")
                return False
            
            # Check score range compatibility (all members can attack same targets)
            try:
                scores = [self._safe_get(nation, 'score', 0, (int, float)) for nation in party]
                min_score = min(scores)
                max_score = max(scores)
                
                # Calculate overlapping attack range
                # Each nation can attack 0.75x to 2.5x their score
                min_attackable = max_score * 0.75  # Highest score's minimum target
                max_attackable = min_score * 2.5   # Lowest score's maximum target
                
                # There must be an overlapping range where all can attack
                if min_attackable > max_attackable:
                    self.logger.debug(f"No overlapping attack range: min_attackable={min_attackable}, max_attackable={max_attackable}")
                    return False
                    
                self.logger.debug(f"Valid attack range overlap: {min_attackable}-{max_attackable}")
            except Exception as e:
                self.logger.warning(f"Error checking score range compatibility: {e}")
                return False
            
            # Must have at least one member with Ground, Air, or Naval advantage
            try:
                has_military_advantage = any(self._has_military_advantage(nation) for nation in party)
                if not has_military_advantage:
                    self.logger.debug("Party lacks military advantage")
                    return False
            except Exception as e:
                self.logger.warning(f"Error checking military advantage: {e}")
                return False
            
            # MUST have at least one missile AND one nuke maker (CRITICAL REQUIREMENT)
            try:
                has_missile_capability = any(
                    self._safe_get(nation, 'military_analysis', {}).get('can_missile', False)
                    for nation in party
                )
                has_nuke_capability = any(
                    self._safe_get(nation, 'military_analysis', {}).get('can_nuke', False)
                    for nation in party
                )
                has_strategic_capability = has_missile_capability and has_nuke_capability
                
                if not has_strategic_capability:
                    self.logger.debug(f"Party lacks strategic capability: missile={has_missile_capability}, nuke={has_nuke_capability}")
                    return False
            except Exception as e:
                self.logger.warning(f"Error checking strategic capability: {e}")
                return False
            
            self.logger.debug("Party passed all validation checks")
            return has_military_advantage and has_strategic_capability
            
        except Exception as e:
            self._log_error("Error in _is_valid_party", e, "party_validation")
            return False

    def _evaluate_party_quality(self, party: List[Dict[str, Any]]) -> float:
        """Evaluate the quality of a party composition - WAR RANGE MATCHING IS PRIMARY."""
        try:
            # Input validation
            if not self._validate_input(party, list, "party"):
                self.logger.warning("Invalid party input for quality evaluation")
                return -1
                
            if not self._is_valid_party(party):
                self.logger.debug("Party failed validation checks")
                return -1
            
            score = 0
            
            # PRIMARY PRIORITY: War range matching - THE MOST IMPORTANT FACTOR
            try:
                war_range_data = self.calculate_party_war_range(party)
                attack_range_span = war_range_data['max_range'] - war_range_data['min_range']
                avg_war_range = (war_range_data['min_range'] + war_range_data['max_range']) / 2
                
                # MASSIVE bonuses for tight war ranges - this is the PRIMARY GOAL
                if attack_range_span > 0:
                    range_ratio = attack_range_span / avg_war_range if avg_war_range > 0 else 1
                    if range_ratio < 0.05:  # Ultra tight range (within 5% of average) - PERFECT
                        score += 500  # MASSIVE bonus for ultra-tight war ranges
                        self.logger.debug(f"Ultra tight war range bonus: +500 (ratio: {range_ratio:.3f})")
                    elif range_ratio < 0.1:  # Very tight range (within 10% of average) - EXCELLENT
                        score += 300  # Huge bonus for very tight war ranges
                        self.logger.debug(f"Very tight war range bonus: +300 (ratio: {range_ratio:.3f})")
                    elif range_ratio < 0.15:  # Tight range (within 15% of average) - GOOD
                        score += 200
                        self.logger.debug(f"Tight war range bonus: +200 (ratio: {range_ratio:.3f})")
                    elif range_ratio < 0.2:  # Acceptable range (within 20% of average) - OK
                        score += 100
                        self.logger.debug(f"Acceptable war range bonus: +100 (ratio: {range_ratio:.3f})")
                    elif range_ratio < 0.3:  # Wide range (within 30% of average) - POOR
                        score += 25
                        self.logger.debug(f"Wide war range bonus: +25 (ratio: {range_ratio:.3f})")
                    # No bonus for very wide ranges - we want tight coordination
            except Exception as e:
                self.logger.warning(f"Error calculating war range quality: {e}")
            
            # SECONDARY PRIORITY: Score balance - closely related to war ranges
            try:
                scores = [self._safe_get(nation, 'score', 0, (int, float)) for nation in party]
                score_range = max(scores) - min(scores)
                avg_score = sum(scores) / len(scores)
                
                # MASSIVE bonuses for tight score grouping
                if score_range < avg_score * 0.03:  # Within 3% of average (ULTRA tight)
                    score += 250  # MASSIVE bonus for ultra-tight score grouping
                    self.logger.debug(f"Ultra tight score grouping bonus: +250")
                elif score_range < avg_score * 0.05:  # Within 5% of average (ultra tight)
                    score += 150  # Huge bonus for ultra-tight score grouping
                    self.logger.debug(f"Very tight score grouping bonus: +150")
                elif score_range < avg_score * 0.10:  # Within 10% of average (very tight)
                    score += 75
                    self.logger.debug(f"Tight score grouping bonus: +75")
                elif score_range < avg_score * 0.15:  # Within 15% of average (tight)
                    score += 25
                    self.logger.debug(f"Acceptable score grouping bonus: +25")
                # No bonus for wide score ranges
            except Exception as e:
                self.logger.warning(f"Error calculating score balance quality: {e}")
            
            # TERTIARY PRIORITY: Strategic capability (missiles/nukes) - ensure each party has at least one
            try:
                strategic_count = sum(1 for nation in party if 
                                    self._safe_get(nation, 'military_analysis', {}).get('can_missile', False) or 
                                    self._safe_get(nation, 'military_analysis', {}).get('can_nuke', False))
                if strategic_count >= 1:
                    score += 50  # Each party should have strategic capability
                    self.logger.debug(f"Strategic capability bonus: +50 ({strategic_count} nations)")
                if strategic_count >= 2:
                    score += 25   # Small bonus for multiple strategic nations
                    self.logger.debug(f"Multiple strategic nations bonus: +25")
            except Exception as e:
                self.logger.warning(f"Error calculating strategic capability quality: {e}")
            
            # QUATERNARY PRIORITY: Military advantage diversity - nice to have but not critical
            try:
                ground_advantage = sum(1 for nation in party if self._has_ground_advantage(nation))
                air_advantage = sum(1 for nation in party if self._has_air_advantage(nation))
                naval_advantage = sum(1 for nation in party if self._has_naval_advantage(nation))
                
                # Small bonus for having different military types
                advantage_types = sum([1 for count in [ground_advantage, air_advantage, naval_advantage] if count > 0])
                diversity_bonus = advantage_types * 10
                score += diversity_bonus  # Small bonus for military diversity
                self.logger.debug(f"Military diversity bonus: +{diversity_bonus} ({advantage_types} types)")
            except Exception as e:
                self.logger.warning(f"Error calculating military advantage diversity: {e}")
            
            # Infrastructure compatibility bonus (minimal)
            try:
                infrastructure_compatibility_score = self._calculate_party_infrastructure_compatibility(party)
                infra_bonus = infrastructure_compatibility_score * 5
                score += infra_bonus  # Tiny bonus for infrastructure compatibility
                self.logger.debug(f"Infrastructure compatibility bonus: +{infra_bonus:.1f}")
            except Exception as e:
                self.logger.warning(f"Error calculating infrastructure compatibility quality: {e}")
            
            self.logger.debug(f"Final party quality score: {score}")
            return score
            
        except Exception as e:
            self._log_error("Error in _evaluate_party_quality", e, "party_quality_evaluation")
            return -1

    def _calculate_party_infrastructure_compatibility(self, party: List[Dict[str, Any]]) -> float:
        """Calculate overall infrastructure compatibility for a party (0-1, higher is better)."""
        try:
            if len(party) < 2:
                return 1.0  # Single nation is perfectly compatible with itself
            
            # Get infrastructure stats for all party members
            infra_stats = []
            for nation in party:
                try:
                    stats = nation.get('infrastructure_stats', {})
                    avg_infra = stats.get('average_infrastructure', 0)
                    if avg_infra > 0:
                        infra_stats.append(avg_infra)
                except Exception as e:
                    self.logger.warning(f"Error getting infrastructure stats for nation: {str(e)}")
                    continue
            
            if len(infra_stats) < 2:
                return 0.5  # Neutral if insufficient data
            
            # Calculate pairwise compatibility scores
            compatibility_scores = []
            for i in range(len(party)):
                for j in range(i + 1, len(party)):
                    try:
                        compatibility = self._calculate_infrastructure_compatibility(party[i], party[j])
                        compatibility_scores.append(compatibility)
                    except Exception as e:
                        self.logger.warning(f"Error calculating infrastructure compatibility for party members {i},{j}: {str(e)}")
                        continue
            
            if not compatibility_scores:
                return 0.5
            
            # Return average compatibility
            avg_compatibility = sum(compatibility_scores) / len(compatibility_scores)
            
            # Additional bonus for same infrastructure tier
            try:
                tiers = [nation.get('infrastructure_stats', {}).get('infrastructure_tier', 'Unknown') for nation in party]
                same_tier_count = len([tier for tier in tiers if tier == tiers[0] and tier != 'Unknown'])
                
                if same_tier_count == len(party):
                    avg_compatibility += 0.2  # Bonus for all same tier
                elif same_tier_count >= len(party) - 1:
                    avg_compatibility += 0.1  # Bonus for mostly same tier
            except Exception as e:
                self.logger.warning(f"Error calculating tier bonus: {str(e)}")
            
            return min(1.0, avg_compatibility)  # Cap at 1.0
            
        except Exception as e:
            self._log_error(f"Error in _calculate_party_infrastructure_compatibility: {str(e)}", e, "_calculate_party_infrastructure_compatibility")
            return 0.5

    def _has_military_advantage(self, nation: Dict[str, Any]) -> bool:
        """Check if nation has any military advantage (Ground, Air, Naval, or Strategic)."""
        try:
            return (self._has_ground_advantage(nation) or 
                    self._has_air_advantage(nation) or 
                    self._has_naval_advantage(nation) or
                    self._has_strategic_advantage(nation))
        except Exception as e:
            self.logger.warning(f"Error checking military advantage: {str(e)}")
            return False

    def _has_ground_advantage(self, nation: Dict[str, Any]) -> bool:
        """Check if nation has ground advantage (heavy in soldiers/tanks with high purchase capacity)."""
        try:
            analysis = nation.get('military_analysis', {})
            return analysis.get('has_ground_advantage', False)
        except Exception as e:
            self.logger.warning(f"Error checking ground advantage: {str(e)}")
            return False

    def _has_air_advantage(self, nation: Dict[str, Any]) -> bool:
        """Check if nation has air advantage (heavy in aircraft with high purchase capacity)."""
        try:
            analysis = nation.get('military_analysis', {})
            return analysis.get('has_air_advantage', False)
        except Exception as e:
            self.logger.warning(f"Error checking air advantage: {str(e)}")
            return False

    def _has_naval_advantage(self, nation: Dict[str, Any]) -> bool:
        """Check if nation has naval advantage (heavy in ships with high purchase capacity)."""
        try:
            analysis = nation.get('military_analysis', {})
            return analysis.get('has_naval_advantage', False)
        except Exception as e:
            self.logger.warning(f"Error checking naval advantage: {str(e)}")
            return False

    def _has_strategic_advantage(self, nation: Dict[str, Any]) -> bool:
        """Check if nation has strategic advantage (missile or nuclear capabilities)."""
        try:
            analysis = nation.get('military_analysis', {})
            return analysis.get('can_missile', False) or analysis.get('can_nuke', False)
        except Exception as e:
            self.logger.warning(f"Error checking strategic advantage: {str(e)}")
            return False

    def _calculate_strategic_value(self, nation: Dict[str, Any]) -> float:
        """Calculate comprehensive strategic value for war party optimization.
        
        Factors considered:
        - Military capabilities (ground, air, naval, strategic)
        - Infrastructure level and development
        - Strategic weapons (missiles, nukes)
        - City count (development potential)
        - Nation score (overall power)
        
        Returns: Strategic value score (0-100, higher is better)
        """
        try:
            score = 0.0
            
            # Get analysis data
            try:
                military_analysis = nation.get('military_analysis', {})
                infrastructure_stats = nation.get('infrastructure_stats', {})
            except Exception as e:
                self.logger.warning(f"Error getting analysis data: {str(e)}")
                military_analysis = {}
                infrastructure_stats = {}
            
            # 1. Strategic Weapons Bonus (25 points max) - HIGHEST PRIORITY
            try:
                if military_analysis.get('can_nuke', False):
                    score += 25  # Nuclear capability is extremely valuable
                elif military_analysis.get('can_missile', False):
                    score += 15  # Missile capability is very valuable
            except Exception as e:
                self.logger.warning(f"Error calculating strategic weapons bonus: {str(e)}")
            
            # 2. Military Strength (20 points max)
            try:
                military_strength = military_analysis.get('military_strength', {})
                ground_strength = military_strength.get('ground', 0)
                air_strength = military_strength.get('air', 0)
                naval_strength = military_strength.get('naval', 0)
                
                # Normalize military strength based on nation score
                nation_score = nation.get('score', 1)
                if nation_score > 0:
                    # Calculate military efficiency (strength per score point)
                    ground_efficiency = ground_strength / nation_score
                    air_efficiency = air_strength / nation_score
                    naval_efficiency = naval_strength / nation_score
                    
                    # Award points for strong military relative to score
                    score += min(ground_efficiency * 0.01, 8)  # Max 8 points for ground
                    score += min(air_efficiency * 0.05, 6)     # Max 6 points for air
                    score += min(naval_efficiency * 0.1, 6)    # Max 6 points for naval
            except Exception as e:
                self.logger.warning(f"Error calculating military strength bonus: {str(e)}")
            
            # 3. Infrastructure Quality (15 points max)
            try:
                avg_infrastructure = infrastructure_stats.get('average_infrastructure', 0)
                infrastructure_tier = infrastructure_stats.get('infrastructure_tier', 'Unknown')
                
                # Award points based on infrastructure tier
                tier_scores = {
                    'Maximum': 15,
                    'Very High': 12,
                    'High': 9,
                    'Medium': 6,
                    'Low': 3,
                    'Unknown': 0
                }
                score += tier_scores.get(infrastructure_tier, 0)
            except Exception as e:
                self.logger.warning(f"Error calculating infrastructure quality bonus: {str(e)}")
            
            # 4. City Count Development (15 points max)
            try:
                city_count = nation.get('num_cities', 0)
                if city_count >= 20:
                    score += 15  # Highly developed
                elif city_count >= 15:
                    score += 12  # Well developed
                elif city_count >= 10:
                    score += 9   # Moderately developed
                elif city_count >= 5:
                    score += 6   # Developing
                else:
                    score += 3   # Early stage
            except Exception as e:
                self.logger.warning(f"Error calculating city development bonus: {str(e)}")
            
            # 5. Nation Score Power (15 points max)
            try:
                # Normalize score relative to typical ranges
                nation_score = nation.get('score', 0)
                if nation_score >= 10000:
                    score += 15  # Very high score
                elif nation_score >= 5000:
                    score += 12  # High score
                elif nation_score >= 2500:
                    score += 9   # Medium-high score
                elif nation_score >= 1000:
                    score += 6   # Medium score
                elif nation_score >= 500:
                    score += 3   # Low-medium score
                else:
                    score += 1   # Low score
            except Exception as e:
                self.logger.warning(f"Error calculating nation score power bonus: {str(e)}")
            
            # 6. Military Advantage Diversity Bonus (10 points max)
            try:
                advantages_count = 0
                if self._has_ground_advantage(nation):
                    advantages_count += 1
                if self._has_air_advantage(nation):
                    advantages_count += 1
                if self._has_naval_advantage(nation):
                    advantages_count += 1
                if self._has_strategic_advantage(nation):
                    advantages_count += 1
                
                score += advantages_count * 2.5  # Up to 10 points for diverse advantages
            except Exception as e:
                self.logger.warning(f"Error calculating military advantage diversity bonus: {str(e)}")
            
            return min(score, 100.0)  # Cap at 100
            
        except Exception as e:
            self._log_error(f"Error in _calculate_strategic_value: {str(e)}", e, "_calculate_strategic_value")
            return 0.0

    def _find_optimal_exclusions(self, nations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Include ALL nations for party formation - no exclusions.
        
        Args:
            nations: List of all available nations
            
        Returns:
            All nations without exclusions (may not be divisible by 3)
        """
        try:
            total_nations = len(nations)
            remainder = total_nations % 3
            
            self.logger.info(f"🎯 Including ALL Nations for Party Formation:")
            self.logger.info(f"   Total Nations: {total_nations} ({total_nations//3} full parties + {remainder} remainder)")
            self.logger.info(f"   All nations will be included - no exclusions based on strategic value")
            
            # Return all nations without any exclusions
            return nations
        except Exception as e:
            self._log_error(f"Error in _find_optimal_exclusions: {str(e)}", e, "_find_optimal_exclusions")
            return []

    def _select_two_for_exclusion(self, nation_values: List[Dict]) -> List[Dict]:
        """Intelligently select 2 nations for exclusion when remainder is 2.
        
        Strategy:
        1. Never exclude nations with nukes if possible
        2. Prefer excluding nations with lowest strategic value
        3. Consider overall balance of remaining parties
        """
        try:
            # Separate nations by strategic weapon capability
            nuke_nations = [nv for nv in nation_values if nv['can_nuke']]
            missile_nations = [nv for nv in nation_values if nv['can_missile'] and not nv['can_nuke']]
            regular_nations = [nv for nv in nation_values if not nv['can_missile'] and not nv['can_nuke']]
            
            excluded = []
            
            # Strategy 1: If we have enough regular nations, exclude from them first
            if len(regular_nations) >= 2:
                excluded = regular_nations[:2]  # Two lowest strategic value regular nations
            
            # Strategy 2: If we need to exclude from strategic nations
            elif len(regular_nations) == 1:
                excluded.append(regular_nations[0])  # Exclude the regular nation
                # Choose between lowest missile nation or lowest overall
                if missile_nations:
                    excluded.append(missile_nations[0])  # Lowest missile nation
                else:
                    # Must exclude a nuke nation (least preferred)
                    excluded.append(nuke_nations[0])
            
            # Strategy 3: No regular nations, must exclude strategic nations
            else:
                if len(missile_nations) >= 2:
                    excluded = missile_nations[:2]  # Two lowest missile nations
                elif len(missile_nations) == 1:
                    excluded.append(missile_nations[0])
                    excluded.append(nuke_nations[0])  # Lowest nuke nation
                else:
                    # Worst case: exclude two nuke nations
                    excluded = nuke_nations[:2]
            
            return excluded
        except Exception as e:
            self._log_error(f"Error in _select_two_for_exclusion: {str(e)}", e, "_select_two_for_exclusion")
            return []

    def _find_best_party_for_nation(self, parties: List[List[Dict]], party_capabilities: List[Dict], nation_analysis: Dict) -> int:
        """Find the best party for a nation based on military advantages needed."""
        try:
            num_parties = len(parties)
            party_scores = []
            
            for i in range(num_parties):
                score = 0
                try:
                    capabilities = party_capabilities[i]
                    
                    # Prefer parties that lack the nation's advantages
                    for advantage in nation_analysis['advantages']:
                        if 'Soldier' in advantage or 'Tank' in advantage:
                            if capabilities['ground'] == 0:
                                score += 10  # High priority for first ground advantage
                            elif capabilities['ground'] < 2:
                                score += 5   # Medium priority for additional ground
                        elif 'Aircraft' in advantage:
                            if capabilities['air'] == 0:
                                score += 10
                            elif capabilities['air'] < 2:
                                score += 5
                        elif 'Naval' in advantage:
                            if capabilities['naval'] == 0:
                                score += 10
                            elif capabilities['naval'] < 2:
                                score += 5
                    
                    # Prefer parties with fewer total members for balance
                    party_size = len(parties[i])
                    if party_size < min(len(p) for p in parties):
                        score += 3
                    
                except Exception as e:
                    self.logger.warning(f"Error processing party {i} in _find_best_party_for_nation: {str(e)}")
                    score = 0
                
                party_scores.append(score)
            
            # Return party with highest score (most need for this nation's advantages)
            return max(range(num_parties), key=lambda i: party_scores[i])
        except Exception as e:
            self._log_error(f"Error in _find_best_party_for_nation: {str(e)}", e, "_find_best_party_for_nation")
            return 0

    async def get_saved_blitz_parties(self) -> List[Dict[str, Any]]:
        """Retrieve saved blitz parties data."""
        try:
            user_data_manager = UserDataManager()
            return await user_data_manager.get_json_data('blitz_parties', [])
        except Exception as e:
            self._log_error(f"Error retrieving saved blitz parties: {str(e)}", e, "get_saved_blitz_parties")
            return []

    async def save_blitz_parties(self, party_data: List[Dict[str, Any]]) -> bool:
        """Save blitz parties data with enhanced military information. Completely overwrites existing data."""
        try:
            user_data_manager = UserDataManager()
            
            # Create new data structure with timestamp - COMPLETELY OVERWRITE existing data
            new_data = {
                "timestamp": datetime.now().isoformat(),
                "parties": party_data,
                "total_parties": len(party_data),
                "total_nations": sum(len(party.get('members', [])) for party in party_data),
                "party_summary": {
                    party['party_name']: {
                        'members': party['party_stats']['member_count'],
                        'total_score': party['party_stats']['total_score'],
                        'strategic_count': party['party_stats']['strategic_count'],
                        'avg_score': party['party_stats']['avg_score']
                    } for party in party_data
                }
            }
            
            # Save using user_data_manager - this completely overwrites the file
            success = await user_data_manager.save_json_data('blitz_parties', new_data)
            
            if success:
                self.logger.info(f"Successfully saved blitz parties data (OVERWRITE): {len(party_data)} parties")
            else:
                self.logger.warning("Failed to save blitz parties data")
                
            return success
            
        except Exception as e:
            self._log_error(f"Error saving blitz parties: {str(e)}", e, "save_blitz_parties")
            return False

    async def save_party(self, party_data: Dict[str, Any]) -> bool:
        """Save a single party to the alliance's saved parties."""
        try:
            user_data_manager = UserDataManager()
            
            # Load existing saved parties for this alliance
            saved_parties = await user_data_manager.get_json_data('saved_parties', {})
            
            # Get alliance ID (use guild ID as alliance identifier)
            alliance_id = str(party_data['members'][0].get('discord_id', 'unknown')) if party_data['members'] else 'unknown'
            
            # Initialize alliance entry if it doesn't exist
            if alliance_id not in saved_parties:
                saved_parties[alliance_id] = []
            
            # Add timestamp and save the party
            party_entry = {
                "timestamp": datetime.now().isoformat(),
                "party_name": party_data['party_name'],
                "party_data": party_data
            }
            
            # Add to alliance's saved parties
            saved_parties[alliance_id].append(party_entry)
            
            # Keep only the last 50 saved parties per alliance to prevent excessive data
            if len(saved_parties[alliance_id]) > 50:
                saved_parties[alliance_id] = saved_parties[alliance_id][-50:]
            
            # Save using user_data_manager
            success = await user_data_manager.save_json_data('saved_parties', saved_parties)
            
            if success:
                self.logger.info(f"Successfully saved party: {party_data['party_name']} for alliance {alliance_id}")
            else:
                self.logger.warning("Failed to save party data")
                
            return success
            
        except Exception as e:
            self._log_error(f"Error saving party: {str(e)}", e, "save_party")
            return False

    def process_parties_for_display(self, parties: List[List[Dict[str, Any]]], team_names: List[str] = None) -> tuple:
        """
        Process parties for display and save, handling all party statistics and data preparation.
        
        Args:
            parties: List of party lists (each party is a list of nations)
            team_names: Optional list of team names to assign to parties
            
        Returns:
            Tuple of (party_info_display, party_info_save) for use in UI and storage
        """
        try:
            if not parties:
                return [], []
            
            # Load team names if not provided
            if not team_names:
                team_names = self._load_team_names()
                random.shuffle(team_names)
            
            party_info_display = []
            party_info_save = []
            
            for i, party in enumerate(parties):
                party_name = team_names[i % len(team_names)] if team_names else f"Party {i+1}"
                
                # Calculate party statistics using existing methods
                total_score = sum(nation.get('score', 0) for nation in party)
                strategic_count = sum(1 for nation in party 
                                    if nation.get('military_analysis', {}).get('can_missile', False) or 
                                       nation.get('military_analysis', {}).get('can_nuke', False))
                
                # Calculate attack range for coordinated attacks
                scores = [nation.get('score', 0) for nation in party]
                min_score = min(scores) if scores else 0
                max_score = max(scores) if scores else 0
                min_attackable = max_score * 0.75
                max_attackable = min_score * 2.5
                
                # Calculate war range data using existing method
                war_range_data = self.calculate_party_war_range(party)
                
                # Calculate military advantages using existing methods
                ground_count = sum(1 for nation in party if self._has_ground_advantage(nation))
                air_count = sum(1 for nation in party if self._has_air_advantage(nation))
                naval_count = sum(1 for nation in party if self._has_naval_advantage(nation))
                
                # Prepare member data for display and save
                member_data_display = []
                member_data_save = []
                
                for nation in party:
                    analysis = nation.get('military_analysis', {})
                    
                    # Build advantages list from boolean flags
                    advantages_list = []
                    if analysis.get('has_ground_advantage', False):
                        advantages_list.append('Ground Advantage')
                    if analysis.get('has_air_advantage', False):
                        advantages_list.append('Air Advantage')
                    if analysis.get('has_naval_advantage', False):
                        advantages_list.append('Naval Advantage')
                    
                    # If no advantages, show Standard
                    if not advantages_list:
                        advantages_list = ['Standard']
                    
                    # Member data for display
                    member_display = {
                        'nation_name': nation.get('nation_name', 'Unknown'),
                        'leader_name': nation.get('leader_name', 'Unknown'),
                        'score': nation.get('score', 0),
                        'advantages': ', '.join(advantages_list),
                        'strategic': '✅' if (analysis.get('can_missile', False) or analysis.get('can_nuke', False)) else '❌'
                    }
                    member_data_display.append(member_display)
                    
                    # Build military advantages list for save data
                    military_advantages = []
                    if analysis.get('has_ground_advantage', False):
                        military_advantages.append('Ground Advantage')
                    if analysis.get('has_air_advantage', False):
                        military_advantages.append('Air Advantage')
                    if analysis.get('has_naval_advantage', False):
                        military_advantages.append('Naval Advantage')
                    
                    # Member data for save
                    member_save = {
                        'discord_id': nation.get('discord_id'),
                        'nation_id': nation.get('id'),
                        'nation_name': nation.get('nation_name', 'Unknown'),
                        'leader_name': nation.get('leader_name', 'Unknown'),
                        'score': nation.get('score', 0),
                        'party_name': party_name,
                        'military_advantages': military_advantages,
                        'can_missile': analysis.get('can_missile', False),
                        'can_nuke': analysis.get('can_nuke', False)
                    }
                    member_data_save.append(member_save)
                
                # Party info for display
                party_display = {
                    'party_name': party_name,
                    'members': member_data_display,
                    'total_score': total_score,
                    'strategic_count': strategic_count,
                    'member_count': len(party),
                    'attack_range': {
                        'min_attackable': min_attackable,
                        'max_attackable': max_attackable,
                        'min_score': min_score,
                        'max_score': max_score
                    },
                    'military_advantages': {
                        'ground': ground_count,
                        'air': air_count,
                        'naval': naval_count
                    }
                }
                party_info_display.append(party_display)
                
                # Party info for save
                party_save = {
                    'party_name': party_name,
                    'members': member_data_save,
                    'total_score': total_score,
                    'strategic_count': strategic_count,
                    'member_count': len(party),
                    'attack_range': {
                        'min_attackable': min_attackable,
                        'max_attackable': max_attackable,
                        'min_score': min_score,
                        'max_score': max_score
                    },
                    'military_advantages': {
                        'ground': ground_count,
                        'air': air_count,
                        'naval': naval_count
                    }
                }
                party_info_save.append(party_save)
            
            return party_info_display, party_info_save
            
        except Exception as e:
            self._log_error(f"Error processing parties for display: {str(e)}", e, "process_parties_for_display")
            return [], []
