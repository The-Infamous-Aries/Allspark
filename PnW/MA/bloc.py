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
from config import (
    PANDW_API_KEY, 
    CYBERTRON_ALLIANCE_ID, 
    PRIME_BANK_ALLIANCE_ID,
    NORTHERN_CONCORD_ALLIANCE_ID,
    ETERNAL_PHOENIX_ALLIANCE_ID,
    RECLAIMED_FLAME_ALLIANCE_ID,
    ETERNAL_ACCORDS_ALLIANCE_ID,
    TCO_ALLIANCE_ID,
    PRIMAL_USER_ID,
    ARIES_USER_ID,
    CARNAGE_USER_ID,
    BENEVOLENT_USER_ID,
    TECH_USER_ID,
    get_role_ids
)
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

# Define AERO alliance configuration
AERO_ALLIANCES = {
    'cybertron': {
        'id': CYBERTRON_ALLIANCE_ID,
        'name': 'Cybertr0n',
        'color': discord.Color.from_rgb(127, 182, 127),  # Mixed color
        'emoji': '🤖'
    },
    'prime_bank': {
        'id': PRIME_BANK_ALLIANCE_ID,
        'name': 'Prime Bank',
        'color': discord.Color.from_rgb(100, 150, 100),  # Similar but distinct color
        'emoji': '🏦'
    },
    'northern_concord': {
        'id': NORTHERN_CONCORD_ALLIANCE_ID,
        'name': 'Northern Concord',
        'color': discord.Color.from_rgb(70, 130, 180),
        'emoji': '❄️'
    },
    'eternal_phoenix': {
        'id': ETERNAL_PHOENIX_ALLIANCE_ID,
        'name': 'Eternal Phoenix',
        'color': discord.Color.from_rgb(255, 69, 0),
        'emoji': '🐦‍🔥'
    },
    'reclaimed_flame': {
        'id': RECLAIMED_FLAME_ALLIANCE_ID,
        'name': 'Reclaimed Flame',
        'color': discord.Color.from_rgb(139, 0, 0),
        'emoji': '🔥'
    },
    'eternal_accords': {
        'id': ETERNAL_ACCORDS_ALLIANCE_ID,
        'name': 'Eternal Accords',
        'color': discord.Color.from_rgb(128, 0, 128),
        'emoji': '📜'
    },
    'tco': {
        'id': TCO_ALLIANCE_ID,
        'name': 'Commonwealth of Orbis',
        'color': discord.Color.from_rgb(255, 255, 0),
        'emoji': '🎖️'
    }
}

class AllianceSelect(discord.ui.Select):
    """Dropdown menu for selecting alliance or bloc totals."""
    
    def __init__(self, author_id: int, view_instance: discord.ui.View, alliance_keys: List[str], bloc_data: Dict[str, List[Dict]]):
        self.author_id = author_id
        self.view_instance = view_instance
        self.alliance_keys = alliance_keys
        self.bloc_data = bloc_data
        
        # Create options for dropdown
        options = [
            discord.SelectOption(
                label="📊 Total (All Combined)",
                description="View bloc totals for all alliances",
                emoji="📊",
                value="bloc_totals"
            )
        ]
        
        # Add individual alliance options
        for alliance_key in alliance_keys:
            alliance_config = AERO_ALLIANCES[alliance_key]
            nations = bloc_data.get(alliance_key, [])
            active_nations = get_active_nations(nations)
            
            options.append(
                discord.SelectOption(
                    label=f"{alliance_config['emoji']} {alliance_config['name']}",
                    description=f"{len(active_nations)} active nations",
                    emoji=alliance_config['emoji'],
                    value=alliance_key
                )
            )
        
        super().__init__(
            placeholder="Select an alliance...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle dropdown selection."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ You cannot use this menu.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            selected_value = self.values[0]
            
            if selected_value == "bloc_totals":
                # Show bloc totals
                if hasattr(self.view_instance, 'generate_bloc_totals_embed'):
                    embed = await self.view_instance.generate_bloc_totals_embed()
                else:
                    # For non-BlocTotalsView instances, create a temporary view
                    # Handle case where view_instance might be a BlocManager (has alliance_manager) vs a view (has alliance_cog)
                    if hasattr(self.view_instance, 'alliance_cog'):
                        alliance_cog = self.view_instance.alliance_cog
                    elif hasattr(self.view_instance, 'alliance_manager'):
                        alliance_cog = self.view_instance.alliance_manager
                    else:
                        # Fallback - shouldn't happen, but provide a clear error
                        await interaction.followup.send("❌ Internal error: Unable to access alliance manager.", ephemeral=True)
                        return
                    
                    temp_view = BlocTotalsView(self.author_id, self.view_instance.bot, alliance_cog, self.bloc_data)
                    embed = await temp_view.generate_bloc_totals_embed()
                    
                    # Update the current view's data if it has the attributes
                    if hasattr(self.view_instance, 'bloc_data'):
                        self.view_instance.bloc_data = self.bloc_data
                    
                    # Update the message with the new BlocTotalsView instead of keeping the old view
                    await interaction.followup.edit_message(
                        message_id=interaction.message.id,
                        embed=embed,
                        view=temp_view
                    )
                    return  # Exit early since we've already updated the message
            else:
                # Show specific alliance
                alliance_key = selected_value
                nations = self.bloc_data.get(alliance_key, [])
                
                if hasattr(self.view_instance, 'generate_alliance_embed'):
                    # BlocTotalsView can generate alliance embeds
                    embed = await self.view_instance.generate_alliance_embed(alliance_key, nations)
                    # Update current alliance index for navigation consistency
                    if hasattr(self.view_instance, 'current_alliance_index'):
                        self.view_instance.current_alliance_index = self.alliance_keys.index(alliance_key)
                elif hasattr(self.view_instance, 'alliance_key'):
                    # Other views - update their data and regenerate embed
                    self.view_instance.alliance_key = alliance_key
                    self.view_instance.current_nations = nations
                    self.view_instance.alliance_config = AERO_ALLIANCES[alliance_key]
                    
                    # Regenerate appropriate embed based on view type
                    if hasattr(self.view_instance, 'generate_military_embed'):
                        embed = await self.view_instance.generate_military_embed(nations)
                    elif hasattr(self.view_instance, 'generate_improvements_embed'):
                        embed = await self.view_instance.generate_improvements_embed(nations)
                    elif hasattr(self.view_instance, 'generate_project_totals_embed'):
                        embed = await self.view_instance.generate_project_totals_embed(nations)
                    else:
                        # Fallback to alliance totals
                        # Handle case where view_instance might be a BlocManager (has alliance_manager) vs a view (has alliance_cog)
                        if hasattr(self.view_instance, 'alliance_cog'):
                            alliance_cog = self.view_instance.alliance_cog
                        elif hasattr(self.view_instance, 'alliance_manager'):
                            alliance_cog = self.view_instance.alliance_manager
                        else:
                            # Fallback - shouldn't happen, but provide a clear error
                            await interaction.followup.send("❌ Internal error: Unable to access alliance manager.", ephemeral=True)
                            return
                        
                        temp_view = BlocTotalsView(self.author_id, self.view_instance.bot, alliance_cog, {alliance_key: nations})
                        embed = await temp_view.generate_alliance_embed(alliance_key, nations)
                else:
                    # Fallback
                    # Handle case where view_instance might be a BlocManager (has alliance_manager) vs a view (has alliance_cog)
                    if hasattr(self.view_instance, 'alliance_cog'):
                        alliance_cog = self.view_instance.alliance_cog
                    elif hasattr(self.view_instance, 'alliance_manager'):
                        alliance_cog = self.view_instance.alliance_manager
                    else:
                        # Fallback - shouldn't happen, but provide a clear error
                        await interaction.followup.send("❌ Internal error: Unable to access alliance manager.", ephemeral=True)
                        return
                    
                    temp_view = BlocTotalsView(self.author_id, self.view_instance.bot, alliance_cog, {alliance_key: nations})
                    embed = await temp_view.generate_alliance_embed(alliance_key, nations)
            
            # Update the message with new embed, keeping the same view
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=self.view_instance
            )
            
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)


class BlocAllianceSelect(discord.ui.Select):
    """Multi-select dropdown for choosing alliance combinations in bloc totals."""
    
    def __init__(self, author_id: int, view_instance: discord.ui.View, bloc_data: Dict[str, List[Dict]]):
        self.author_id = author_id
        self.view_instance = view_instance
        self.bloc_data = bloc_data
        
        # Create options for dropdown - dynamically include all alliances from AERO_ALLIANCES
        options = []
        default_alliances = ['cybertron_combined', 'northern_concord', 'eternal_phoenix', 'reclaimed_flame', 'eternal_accords', 'tco']
        
        # Add Cybertron (includes Prime Bank) - special case for combined alliance
        cybertron_config = AERO_ALLIANCES['cybertron']
        cybertron_nations_data = bloc_data.get('cybertron', [])
        prime_bank_nations_data = bloc_data.get('prime_bank', [])
        
        # Extract nations lists properly
        cybertron_nations = self._extract_nations_list(cybertron_nations_data, 'cybertron')
        prime_bank_nations = self._extract_nations_list(prime_bank_nations_data, 'prime_bank')
        
        combined_nations = cybertron_nations + prime_bank_nations
        active_combined = get_active_nations(combined_nations)
        
        options.append(
            discord.SelectOption(
                label=f"{cybertron_config['emoji']} Cybertron",
                description=f"{len(active_combined)} active nations (combined)",
                emoji=cybertron_config['emoji'],
                value="cybertron_combined",
                default="cybertron_combined" in default_alliances
            )
        )
        
        for alliance_key, alliance_config in AERO_ALLIANCES.items():
            if alliance_key == 'cybertron':
                continue
                
            nations_data = bloc_data.get(alliance_key, [])
            nations = self._extract_nations_list(nations_data, alliance_key)
            active_nations = get_active_nations(nations)
            
            options.append(
                discord.SelectOption(
                    label=f"{alliance_config['emoji']} {alliance_config['name']}",
                    description=f"{len(active_nations)} active nations",
                    emoji=alliance_config['emoji'],
                    value=alliance_key,
                    default=alliance_key in default_alliances
                )
            )
        
        super().__init__(
            placeholder="Select alliances to combine...",
            min_values=1,
            max_values=len(options),
            options=options
        )
    
    def _extract_nations_list(self, nations_data: Any, alliance_key: str) -> List[Dict]:
        """Extract a list of nation dictionaries from various possible data structures.
        
        This method handles edge cases where nations_data might be:
        - A list of dictionaries (expected case)
        - A single dictionary (convert to list with one item)
        - A dictionary containing a 'nations' key with list/dict
        - None or empty (return empty list)
        - Any other invalid structure (return empty list)
        """
        try:
            if nations_data is None:
                return []
            
            # Case 1: Already a list
            if isinstance(nations_data, list):
                # Filter for valid dictionary items
                return [item for item in nations_data if isinstance(item, dict)]
            
            # Case 2: Single dictionary - convert to list
            if isinstance(nations_data, dict):
                # Check if it contains a 'nations' key
                if 'nations' in nations_data:
                    nations_subdata = nations_data['nations']
                    if isinstance(nations_subdata, list):
                        return [item for item in nations_subdata if isinstance(item, dict)]
                    elif isinstance(nations_subdata, dict):
                        # If it's a dict of nations, convert values to list
                        return list(nations_subdata.values())
                    else:
                        return []
                else:
                    # Single nation dict - wrap in list
                    return [nations_data]
            
            # Case 3: Invalid type
            return []
            
        except Exception as e:
            # Silently return empty list on error
            return []
    
    async def callback(self, interaction: discord.Interaction):
        """Handle dropdown selection for alliance combinations."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ You cannot use this menu.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            selected_alliances = self.values
            
            # Update the view's selected alliances
            if hasattr(self.view_instance, 'selected_alliances'):
                self.view_instance.selected_alliances = selected_alliances
            
            # Generate new embed based on selection
            if hasattr(self.view_instance, 'generate_custom_bloc_embed'):
                embed = await self.view_instance.generate_custom_bloc_embed(selected_alliances)
            elif hasattr(self.view_instance, 'generate_bloc_totals_embed'):
                # Fallback to regular bloc totals
                embed = await self.view_instance.generate_bloc_totals_embed()
            else:
                # For views that don't have bloc totals method, create a temporary BlocTotalsView
                # Handle case where view_instance might be a BlocManager (has alliance_manager) vs a view (has alliance_cog)
                if hasattr(self.view_instance, 'alliance_cog'):
                    alliance_cog = self.view_instance.alliance_cog
                elif hasattr(self.view_instance, 'alliance_manager'):
                    alliance_cog = self.view_instance.alliance_manager
                else:
                    # Fallback - shouldn't happen, but provide a clear error
                    await interaction.followup.send("❌ Internal error: Unable to access alliance manager.", ephemeral=True)
                    return
                
                temp_view = BlocTotalsView(self.author_id, self.view_instance.bot, alliance_cog, self.bloc_data)
                embed = await temp_view.generate_bloc_totals_embed()
                
                # Update the message with the new BlocTotalsView
                await interaction.followup.edit_message(
                    message_id=interaction.message.id,
                    embed=embed,
                    view=temp_view
                )
                return  # Exit early since we've already updated the message
            
            # Update the message
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=self.view_instance
            )
            
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)


class BlocTotalsView(discord.ui.View):
    """View for displaying Eternal Accords bloc totals with navigation between alliances."""
    
    def __init__(self, author_id: int, bot: commands.Bot, alliance_cog: 'AllianceManager', bloc_data: Dict[str, List[Dict]] = None):
        super().__init__(timeout=300)  # 5 minute timeout
        self.author_id = author_id
        self.bot = bot
        self.alliance_cog = alliance_cog
        self.current_data = None
        self.bloc_data = bloc_data or {}
        self.current_alliance_index = 0
        self.alliance_keys = list(AERO_ALLIANCES.keys())
        self.current_alliance_key = None
        self.current_nations = None
        self.current_combined_nations = None  # Store combined nations for other views
        self.selected_alliances = ['cybertron_combined'] + [key for key in AERO_ALLIANCES.keys() if key != 'cybertron']  # Default to all alliances
        
        # Add the alliance selection dropdown at the top
        self.add_item(BlocAllianceSelect(author_id, self, self.bloc_data))

    def _extract_nations_list(self, nations_data: Any, alliance_key: str) -> List[Dict]:
        """Extract a list of nation dictionaries from various possible data structures.
        
        This method handles edge cases where nations_data might be:
        - A list of dictionaries (expected case)
        - A single dictionary (convert to list with one item)
        - A dictionary containing a 'nations' key with list/dict
        - None or empty (return empty list)
        - Any other invalid structure (return empty list)
        """
        try:
            if nations_data is None:
                return []
            
            # Case 1: Already a list
            if isinstance(nations_data, list):
                # Filter for valid dictionary items
                return [item for item in nations_data if isinstance(item, dict)]
            
            # Case 2: Single dictionary - convert to list
            if isinstance(nations_data, dict):
                # Check if it contains a 'nations' key
                if 'nations' in nations_data:
                    nations_subdata = nations_data['nations']
                    if isinstance(nations_subdata, list):
                        return [item for item in nations_subdata if isinstance(item, dict)]
                    elif isinstance(nations_subdata, dict):
                        # If it's a dict of nations, convert values to list
                        return list(nations_subdata.values())
                    else:
                        # Log warning if we have access to logger, otherwise silently handle
                        return []
                else:
                    # Single nation dict - wrap in list
                    return [nations_data]
            
            # Case 3: Invalid type
            return []
            
        except Exception as e:
            # Silently return empty list on error
            return []
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the interaction is from the command author."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ You cannot use this menu.")
            return False
        return True

    async def generate_bloc_totals_embed(self) -> discord.Embed:
        """Generate the bloc totals overview embed."""
        try:
            if not self.bloc_data:
                return discord.Embed(
                    title="❌ No Bloc Data",
                    description="Failed to retrieve bloc data.",
                    color=discord.Color.red()
                )
            
            # Validate data structure
            if not isinstance(self.bloc_data, dict):
                return discord.Embed(
                    title="❌ Invalid Data Format",
                    description="Bloc data is not in expected dictionary format.",
                    color=discord.Color.red()
                )
            
            # Calculate bloc-wide statistics
            total_nations = 0
            total_active_nations = 0
            total_score = 0
            total_cities = 0
            alliance_breakdown = []
            
            for alliance_key, alliance_config in AERO_ALLIANCES.items():
                nations_data = self.bloc_data.get(alliance_key, [])
                nations = self._extract_nations_list(nations_data, alliance_key)
                
                if not nations:
                    continue
                    
                active_nations = get_active_nations(nations)
                nation_stats = calculate_nation_statistics(nations)
                alliance_stats = calculate_alliance_statistics(active_nations)
                
                total_nations += nation_stats['total_nations']
                total_active_nations += nation_stats['active_nations']
                total_score += alliance_stats['total_score']
                total_cities += alliance_stats['total_cities']
                
                alliance_breakdown.append(
                    f"{alliance_config['emoji']} **{alliance_config['name']}**: "
                    f"{nation_stats['total_nations']} nations "
                    f"({nation_stats['active_nations']} active), "
                    f"{alliance_stats['total_score']:,} score"
                )
            
            embed = discord.Embed(
                title="📊 Eternal Accords Bloc Totals",
                description=f"Comprehensive statistics across all {len(AERO_ALLIANCES)} alliances",
                color=discord.Color.from_rgb(75, 0, 130)  # Dark purple for bloc
            )
            
            # Calculate average score safely
            avg_score = total_score / total_nations if total_nations > 0 else 0
            
            embed.add_field(
                name="🌍 Bloc Overview",
                value=(
                    f"**Total Nations:** {total_nations:,}\n"
                    f"**Active Nations:** {total_active_nations:,}\n"
                    f"**Total Score:** {total_score:,}\n"
                    f"**Total Cities:** {total_cities:,}\n"
                    f"**Average Score:** {avg_score:,.0f}"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🏛️ Alliance Breakdown",
                value="\n".join(alliance_breakdown),
                inline=False
            )
            
            embed.set_footer(text=f"Generated at {datetime.now().strftime('%H:%M:%S')} | Use navigation buttons to view individual alliances")
            
            return embed
            
        except Exception as e:
            return discord.Embed(
                title="❌ Bloc Totals Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )

    async def generate_custom_bloc_embed(self, selected_alliances: List[str]) -> discord.Embed:
        """Generate bloc totals embed for selected alliance combinations."""
        try:
            if not self.bloc_data:
                return discord.Embed(
                    title="❌ No Bloc Data",
                    description="Failed to retrieve bloc data.",
                    color=discord.Color.red()
                )
            
            # Calculate statistics for selected alliances
            total_nations = 0
            total_active_nations = 0
            total_score = 0
            total_cities = 0
            alliance_breakdown = []
            all_selected_nations = []
            
            for alliance_key in selected_alliances:
                if alliance_key == "cybertron_combined":
                    cybertron_nations_data = self.bloc_data.get('cybertron', [])
                    prime_bank_nations_data = self.bloc_data.get('prime_bank', [])
                    
                    # Validate and clean data - handle various data structures
                    cybertron_nations = self._extract_nations_list(cybertron_nations_data, 'cybertron')
                    prime_bank_nations = self._extract_nations_list(prime_bank_nations_data, 'prime_bank')
                    
                    nations = cybertron_nations + prime_bank_nations
                    alliance_config = AERO_ALLIANCES['cybertron']
                    display_name = "Cybertron (incl. Prime Bank)"
                else:
                    nations_data = self.bloc_data.get(alliance_key, [])
                    nations = self._extract_nations_list(nations_data, alliance_key)
                    alliance_config = AERO_ALLIANCES.get(alliance_key, {})
                    display_name = alliance_config.get('name', alliance_key)
                
                if not nations:
                    continue
                
                # nations is guaranteed to be a list from _extract_nations_list
                all_selected_nations.extend(nations)
                active_nations = get_active_nations(nations)
                nation_stats = calculate_nation_statistics(nations)
                alliance_stats = calculate_alliance_statistics(active_nations)
                
                total_nations += nation_stats['total_nations']
                total_active_nations += nation_stats['active_nations']
                total_score += alliance_stats['total_score']
                total_cities += alliance_stats['total_cities']
                
                alliance_breakdown.append(
                    f"{alliance_config.get('emoji', '🏛️')} **{display_name}**: "
                    f"{nation_stats['total_nations']} nations "
                    f"({nation_stats['active_nations']} active), "
                    f"{alliance_stats['total_score']:,} score"
                )
            
            # Calculate overall averages
            avg_score = total_score / total_nations if total_nations > 0 else 0
            avg_cities = total_cities / total_nations if total_nations > 0 else 0
            
            embed = discord.Embed(
                title="📊 Custom Bloc Combination",
                description=f"Statistics for selected alliance combination ({len(selected_alliances)} alliances)",
                color=discord.Color.from_rgb(75, 0, 130)  # Dark purple for bloc
            )
            
            embed.add_field(
                name="🌍 Selected Alliances Overview",
                value=(
                    f"**Total Nations:** {total_nations:,}\n"
                    f"**Active Nations:** {total_active_nations:,}\n"
                    f"**Total Score:** {total_score:,}\n"
                    f"**Total Cities:** {total_cities:,}\n"
                    f"**Average Score:** {avg_score:,.0f}\n"
                    f"**Average Cities:** {avg_cities:.1f}"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🏛️ Alliance Breakdown",
                value="\n".join(alliance_breakdown) if alliance_breakdown else "No alliances selected",
                inline=False
            )
            
            # Store the combined nations for other views to use
            self.current_combined_nations = all_selected_nations
            
            embed.set_footer(text=f"Generated at {datetime.now().strftime('%H:%M:%S')} | Use buttons below for detailed views")
            
            return embed
            
        except Exception as e:
            return discord.Embed(
                title="❌ Custom Bloc Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )

    async def generate_alliance_embed(self, alliance_key: str, nations: List[Dict]) -> discord.Embed:
        """Generate embed for a specific alliance."""
        try:
            alliance_config = AERO_ALLIANCES[alliance_key]
            
            # Validate nations data
            if not nations:
                return discord.Embed(
                    title=f"❌ {alliance_config['name']} - No Data",
                    description="Failed to retrieve alliance data.",
                    color=alliance_config['color']
                )
            
            # Ensure nations is a list of dictionaries
            if not isinstance(nations, list):
                logger.error(f"Expected nations to be a list, got {type(nations)}")
                nations = []
            
            # Filter out invalid nation entries
            valid_nations = []
            for nation in nations:
                if isinstance(nation, dict):
                    valid_nations.append(nation)
                else:
                    logger.warning(f"Invalid nation entry in alliance {alliance_key}: {type(nation)}")
            
            if not valid_nations:
                return discord.Embed(
                    title=f"❌ {alliance_config['name']} - Invalid Data",
                    description="No valid nation data found.",
                    color=alliance_config['color']
                )
            
            nations = valid_nations
            
            # Get active nations for statistics
            active_nations = get_active_nations(nations)
            stats = calculate_alliance_statistics(active_nations)
            nation_stats = calculate_nation_statistics(nations)
            
            # Calculate averages
            avg_score = stats['total_score'] / nation_stats['total_nations'] if nation_stats['total_nations'] > 0 else 0
            avg_cities = stats['total_cities'] / nation_stats['total_nations'] if nation_stats['total_nations'] > 0 else 0
            
            embed = discord.Embed(
                title=f"{alliance_config['emoji']} {alliance_config['name']} Alliance Totals",
                description=f"Comprehensive statistics for {alliance_config['name']}",
                color=alliance_config['color']
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

            filtered_nations = get_active_nations(nations)
            
            total_money = sum(n.get('money', 0) or 0 for n in filtered_nations)
            total_credits = sum(n.get('credits', 0) or 0 for n in filtered_nations)
            total_gasoline = sum(n.get('gasoline', 0) or 0 for n in filtered_nations)
            total_munitions = sum(n.get('munitions', 0) or 0 for n in filtered_nations)
            total_steel = sum(n.get('steel', 0) or 0 for n in filtered_nations)
            total_aluminum = sum(n.get('aluminum', 0) or 0 for n in filtered_nations)
            total_food = sum(n.get('food', 0) or 0 for n in filtered_nations)
            
            resources_held = (
                f"**Money:** ${total_money:,}\n"
                f"**Credits:** {total_credits:,}\n"
                f"**Gasoline:** {total_gasoline:,}\n"
                f"**Munitions:** {total_munitions:,}\n"
                f"**Steel:** {total_steel:,}\n"
                f"**Aluminum:** {total_aluminum:,}\n"
                f"**Food:** {total_food:,}"
            )
            embed.add_field(name="💰 Resources Held", value=resources_held, inline=False)
            
            # Military units
            total_soldiers = sum(n.get('soldiers', 0) or 0 for n in active_nations)
            total_tanks = sum(n.get('tanks', 0) or 0 for n in active_nations)
            total_aircraft = sum(n.get('aircraft', 0) or 0 for n in active_nations)
            total_ships = sum(n.get('ships', 0) or 0 for n in active_nations)
            total_missiles = sum(n.get('missiles', 0) or 0 for n in active_nations)
            total_nukes = sum(n.get('nukes', 0) or 0 for n in active_nations)
            
            military_units = (
                f"🪖 **Soldiers:** {total_soldiers:,}\n"
                f"🛡️ **Tanks:** {total_tanks:,}\n"
                f"✈️ **Aircraft:** {total_aircraft:,}\n"
                f"🚢 **Ships:** {total_ships:,}\n"
                f"🚀 **Missiles:** {total_missiles:,}\n"
                f"☢️ **Nukes:** {total_nukes:,}"
            )
            embed.add_field(name="⚔️ Military Units", value=military_units, inline=False)
            
            embed.set_footer(text=f"Generated at {datetime.now().strftime('%H:%M:%S')} | Alliance {self.current_alliance_index + 1} of {len(self.alliance_keys)}")
            
            return embed
            
        except Exception as e:
            return discord.Embed(
                title="❌ Alliance Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )

    @discord.ui.button(label="📊 Bloc Totals", style=discord.ButtonStyle.primary, row=1)
    async def bloc_totals_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Return to bloc totals overview."""
        await interaction.response.defer()
        
        embed = await self.generate_bloc_totals_embed()
        
        await interaction.followup.edit_message(
            message_id=interaction.message.id,
            embed=embed,
            view=self
        )

    async def military_callback(self, interaction: discord.Interaction):
        """Show military details for current alliance."""
        await interaction.response.defer()
        
        alliance_key = self.alliance_keys[self.current_alliance_index]
        nations = self.bloc_data.get(alliance_key, [])
        
        view = MilitaryView(self.author_id, self.bot, self.alliance_cog, nations, alliance_key)
        embed = await view.generate_military_embed(nations)
        
        await interaction.followup.edit_message(
            message_id=interaction.message.id,
            embed=embed,
            view=view
        )

    async def improvements_callback(self, interaction: discord.Interaction):
        """Show improvements breakdown for current alliance."""
        await interaction.response.defer()
        
        alliance_key = self.alliance_keys[self.current_alliance_index]
        nations = self.bloc_data.get(alliance_key, [])
        
        view = ImprovementsView(self.author_id, self.bot, self.alliance_cog, nations, alliance_key)
        embed = await view.generate_improvements_embed(nations)
        
        await interaction.followup.edit_message(
            message_id=interaction.message.id,
            embed=embed,
            view=view
        )

    @discord.ui.button(label="Military", style=discord.ButtonStyle.secondary, row=1)
    async def military_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show military details for selected alliances."""
        try:
            await interaction.response.defer()
            
            # Use selected_alliances to get combined data
            combined_nations = []
            for alliance_key in self.selected_alliances:
                if alliance_key == "cybertron_combined":
                    cybertron_nations = self.bloc_data.get('cybertron', [])
                    prime_bank_nations = self.bloc_data.get('prime_bank', [])
                    combined_nations.extend(cybertron_nations)
                    combined_nations.extend(prime_bank_nations)
                else:
                    nations_data = self.bloc_data.get(alliance_key, [])
                    combined_nations.extend(nations_data)
            
            # Use the first alliance key for view initialization (will be overridden by selected_alliances)
            primary_alliance_key = self.selected_alliances[0] if self.selected_alliances else self.alliance_keys[0]
            if primary_alliance_key == "cybertron_combined":
                primary_alliance_key = "cybertron"
            
            view = MilitaryView(self.author_id, self.bot, self.alliance_cog, combined_nations, primary_alliance_key, self.selected_alliances)
            embed = await view.generate_military_embed(combined_nations)
            
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=view
            )
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")

    @discord.ui.button(label="Improvements", style=discord.ButtonStyle.secondary, row=1)
    async def improvements_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show improvements breakdown for selected alliances."""
        try:
            await interaction.response.defer()
            
            # Use selected_alliances to get combined data
            combined_nations = []
            for alliance_key in self.selected_alliances:
                if alliance_key == "cybertron_combined":
                    cybertron_nations = self.bloc_data.get('cybertron', [])
                    prime_bank_nations = self.bloc_data.get('prime_bank', [])
                    combined_nations.extend(cybertron_nations)
                    combined_nations.extend(prime_bank_nations)
                else:
                    nations_data = self.bloc_data.get(alliance_key, [])
                    combined_nations.extend(nations_data)
            
            # Use the first alliance key for view initialization (will be overridden by selected_alliances)
            primary_alliance_key = self.selected_alliances[0] if self.selected_alliances else self.alliance_keys[0]
            if primary_alliance_key == "cybertron_combined":
                primary_alliance_key = "cybertron"
            
            view = ImprovementsView(self.author_id, self.bot, self.alliance_cog, combined_nations, primary_alliance_key, self.selected_alliances)
            embed = await view.generate_improvements_embed(combined_nations)
            
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=view
            )
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")

    @discord.ui.button(label="Projects", style=discord.ButtonStyle.secondary, row=1)
    async def projects_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show project totals for selected alliances."""
        try:
            await interaction.response.defer()
            
            # Use selected_alliances to get combined data
            combined_nations = []
            for alliance_key in self.selected_alliances:
                if alliance_key == "cybertron_combined":
                    cybertron_nations = self.bloc_data.get('cybertron', [])
                    prime_bank_nations = self.bloc_data.get('prime_bank', [])
                    combined_nations.extend(cybertron_nations)
                    combined_nations.extend(prime_bank_nations)
                else:
                    nations_data = self.bloc_data.get(alliance_key, [])
                    combined_nations.extend(nations_data)
            
            # Use the first alliance key for view initialization (will be overridden by selected_alliances)
            primary_alliance_key = self.selected_alliances[0] if self.selected_alliances else self.alliance_keys[0]
            if primary_alliance_key == "cybertron_combined":
                primary_alliance_key = "cybertron"
            
            view = ProjectTotalsView(self.author_id, self.bot, self.alliance_cog, combined_nations, primary_alliance_key, self.selected_alliances)
            embed = await view.generate_project_totals_embed(combined_nations)
            
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=view
            )
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")


class AllianceManager:
    """Manages Eternal Accords bloc data fetching and caching."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        
        # Set up cache file path
        self.bloc_cache_file = os.path.join('Systems', 'Data', 'Bloc', 'bloc_cache.json')
        
        # Initialize bloc data and load from cache
        self.bloc_data = {}
        self.last_update = None
        
        # Load existing cache if available
        self.load_bloc_cache()
        
        self.logger.info(f"AllianceManager initialized with cache file: {self.bloc_cache_file}")
    
    def load_bloc_cache(self):
        """Load bloc data from individual alliance files in Bloc directory."""
        try:
            self.logger.info("Attempting to load bloc data from individual alliance files")
            
            # Initialize empty bloc data
            self.bloc_data = {}
            self.last_update = None
            
            # Path to Bloc directory
            bloc_dir = os.path.join('Systems', 'Data', 'Bloc')
            
            if not os.path.exists(bloc_dir):
                self.logger.warning(f"Bloc directory does not exist: {bloc_dir}")
                return
            
            # Map alliance IDs to their keys from AERO_ALLIANCES
            alliance_id_to_key = {}
            for key, config in AERO_ALLIANCES.items():
                alliance_id_to_key[str(config['id'])] = key
            
            # List of alliance files to load (based on actual alliance IDs)
            alliance_files = [
                f'alliance_{CYBERTRON_ALLIANCE_ID}.json',
                f'alliance_{PRIME_BANK_ALLIANCE_ID}.json', 
                f'alliance_{NORTHERN_CONCORD_ALLIANCE_ID}.json',
                f'alliance_{ETERNAL_PHOENIX_ALLIANCE_ID}.json',
                f'alliance_{RECLAIMED_FLAME_ALLIANCE_ID}.json',
                f'alliance_{ETERNAL_ACCORDS_ALLIANCE_ID}.json',
                f'alliance_{TCO_ALLIANCE_ID}.json'
            ]
            
            loaded_count = 0
            for filename in alliance_files:
                file_path = os.path.join(bloc_dir, filename)
                
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            alliance_data = json.load(f)
                            
                        # Extract alliance ID from filename
                        alliance_id = filename.replace('alliance_', '').replace('.json', '')
                        
                        # Get alliance key from our mapping
                        alliance_key = alliance_id_to_key.get(alliance_id)
                        
                        if alliance_key and alliance_data:
                            # Extract nations list from the alliance data
                            nations_list = alliance_data.get('nations', [])
                            if nations_list:
                                # Store the nations list directly in bloc_data
                                self.bloc_data[alliance_key] = nations_list
                                loaded_count += 1
                                self.logger.info(f"Loaded {len(nations_list)} nations for {alliance_key} from {filename}")
                            else:
                                # If no nations found, store empty list
                                self.bloc_data[alliance_key] = []
                                self.logger.warning(f"No nations found in {filename}")
                            
                            # Update last_update if this file is newer
                            if alliance_data.get('last_update'):
                                if not self.last_update or alliance_data['last_update'] > self.last_update:
                                    self.last_update = alliance_data['last_update']
                    
                    except Exception as file_error:
                        self.logger.warning(f"Error loading {filename}: {file_error}")
                else:
                    self.logger.warning(f"Alliance file not found: {file_path}")
            
            self.logger.info(f"Successfully loaded {loaded_count} alliances from individual files")
            
            # If no data was loaded, try to set a default last_update
            if loaded_count > 0 and not self.last_update:
                self.last_update = datetime.now().isoformat()
                
        except Exception as e:
            self.logger.error(f"Error loading bloc cache from alliance files: {e}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            self.bloc_data = {}
            self.last_update = None
    
    def save_bloc_cache(self):
        """Save bloc data to individual alliance files in Bloc directory."""
        try:
            self.logger.info(f"Attempting to save bloc data to individual alliance files")
            
            # Path to Bloc directory
            bloc_dir = os.path.join('Systems', 'Data', 'Bloc')
            
            # Ensure directory exists
            if not os.path.exists(bloc_dir):
                os.makedirs(bloc_dir, exist_ok=True)
                self.logger.info(f"Created Bloc directory: {bloc_dir}")
            
            saved_count = 0
            for alliance_key, alliance_data in self.bloc_data.items():
                try:
                    # Get alliance ID from AERO_ALLIANCES
                    alliance_config = AERO_ALLIANCES.get(alliance_key)
                    if not alliance_config:
                        self.logger.warning(f"No configuration found for alliance key: {alliance_key}")
                        continue
                    
                    alliance_id = alliance_config['id']
                    filename = f'alliance_{alliance_id}.json'
                    file_path = os.path.join(bloc_dir, filename)
                    
                    # Create the proper JSON structure with nations list
                    if isinstance(alliance_data, list):
                        # If we have a list of nations, wrap it in the expected format
                        save_data = {
                            'nations': alliance_data,
                            'last_update': datetime.now().isoformat()
                        }
                    elif isinstance(alliance_data, dict):
                        # If it's already a dict, update the last_update
                        alliance_data['last_update'] = datetime.now().isoformat()
                        save_data = alliance_data
                    else:
                        self.logger.warning(f"Unexpected data type for {alliance_key}: {type(alliance_data)}")
                        continue
                    
                    # Save to individual file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(save_data, f, indent=2)
                    
                    saved_count += 1
                    self.logger.info(f"Saved alliance data for {alliance_key} to {filename}")
                    
                except Exception as save_error:
                    self.logger.error(f"Error saving alliance {alliance_key}: {save_error}")
            
            self.logger.info(f"Successfully saved {saved_count} alliances to individual files")
            
        except Exception as e:
            self.logger.error(f"Error saving bloc cache to alliance files: {e}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
    
    async def calculate_full_mill_data(self, nations: List[Dict]) -> Dict[str, Any]:
        """Calculate full military data for a list of nations."""
        return await calculate_full_mill_data(nations)
    
    async def get_alliance_nations(self, alliance_id: int) -> List[Dict]:
        """Get nations for a specific alliance from individual alliance files in Bloc directory."""
        try:
            self.logger.info(f"Getting nations for alliance {alliance_id}")
            
            # Priority 1: Load from individual alliance files in Bloc directory
            user_data_manager = UserDataManager()
            alliance_id_str = str(alliance_id)
            
            # Try to load from individual alliance file in Bloc directory
            try:
                # Look for alliance_{alliance_id}.json file in Bloc directory
                bloc_alliance_file = f'alliance_{alliance_id_str}'
                alliance_data = await user_data_manager.get_json_data(bloc_alliance_file, {})
                
                if alliance_data and isinstance(alliance_data, dict):
                    nations = alliance_data.get('nations', [])
                    if nations:
                        self.logger.info(f"Using Bloc directory data for alliance {alliance_id} ({len(nations)} nations)")
                        return nations
                    
                    # Check for combined_alliances format
                    combined_alliances = alliance_data.get('combined_alliances', [])
                    total_nations = alliance_data.get('total_nations', 0)
                    
                    if combined_alliances and total_nations > 0:
                        # This is a combined cache file, extract nations from it
                        nations_list = []
                        for alliance_key in combined_alliances:
                            alliance_nations = alliance_data.get(alliance_key, [])
                            if alliance_nations:
                                nations_list.extend(alliance_nations)
                        
                        if nations_list:
                            self.logger.info(f"Using combined Bloc data for alliance {alliance_id} ({len(nations_list)} nations)")
                            return nations_list
                        
            except Exception as bloc_err:
                self.logger.warning(f"Bloc directory load failed for alliance {alliance_id}: {bloc_err}")
            
            # Priority 2: Try loading all alliance files from Bloc directory
            try:
                from pathlib import Path
                bloc_dir = Path('Systems/Data/Bloc')
                if bloc_dir.exists():
                    all_nations = []
                    for alliance_file in bloc_dir.glob('alliance_*.json'):
                        try:
                            file_data = await user_data_manager.get_json_data(alliance_file.stem, {})
                            if file_data and isinstance(file_data, dict):
                                nations = file_data.get('nations', [])
                                if nations:
                                    all_nations.extend(nations)
                        except Exception as file_err:
                            self.logger.warning(f"Failed to load {alliance_file}: {file_err}")
                    
                    if all_nations:
                        self.logger.info(f"Using all Bloc alliance files for alliance {alliance_id} ({len(all_nations)} nations)")
                        return all_nations
                        
            except Exception as all_err:
                self.logger.warning(f"Failed to load all Bloc alliance files: {all_err}")
            
            # Priority 3: Use query.py's built-in caching system (fallback)
            if create_query_instance:
                try:
                    query_instance = create_query_instance()
                    nations_data = await query_instance.get_alliance_nations(str(alliance_id), bot=self.bot)
                    if nations_data:
                        self.logger.info(f"Using query.py cached data for alliance {alliance_id} ({len(nations_data)} nations)")
                        return nations_data
                    else:
                        self.logger.warning(f"query.py returned no data for alliance {alliance_id}")
                except Exception as e:
                    self.logger.error(f"query.py failed for alliance {alliance_id}: {e}")
            
            # Priority 4: Fetch from API using _fetch_alliance_nations_from_api (last resort)
            self.logger.info(f"No cache found for alliance {alliance_id}, fetching from API")
            nations_data = await self._fetch_alliance_nations_from_api(alliance_id)
            
            if nations_data:
                self.logger.info(f"Successfully fetched {len(nations_data)} nations for alliance {alliance_id}")
                return nations_data
            else:
                self.logger.warning(f"No nations data available for alliance {alliance_id}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error fetching alliance nations for ID {alliance_id}: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return []
    
    async def _fetch_alliance_nations_from_api(self, alliance_id: int) -> List[Dict]:
        """Fetch nations for a specific alliance from the API using centralized query system."""
        nations_data = []
        
        # Priority 1: Use query.py system (fully centralized with caching)
        if create_query_instance:
            try:
                query_instance = create_query_instance()
                nations = await query_instance.get_alliance_nations(str(alliance_id), bot=self.bot)
                
                if nations:
                    # Transform query.py format to expected bloc.py format
                    for nation in nations:
                        nation_dict = self._transform_query_nation_to_bloc_format(nation)
                        nations_data.append(nation_dict)
                    
                    self.logger.info(f"Successfully fetched {len(nations_data)} nations for alliance {alliance_id} using query.py system")
                    return nations_data
                else:
                    self.logger.warning(f"query.py returned no nations for alliance {alliance_id}")
            except Exception as e:
                self.logger.error(f"query.py system failed for alliance {alliance_id}: {e}")
        
        # Priority 2: Use pnwkit if available (fallback)
        if PNWKIT_AVAILABLE:
            try:
                query = pnwkit.Query()
                nations = await query.nations(
                    alliance_id=alliance_id,
                    first=500
                )
                
                # Convert to dict format
                for nation in nations:
                    nation_dict = {
                        'nation_id': nation.nation_id,
                        'nation_name': nation.nation_name,
                        'leader_name': nation.leader_name,
                        'continent': nation.continent,
                        'war_policy': nation.war_policy,
                        'domestic_policy': nation.domestic_policy,
                        'color': nation.color,
                        'alliance_id': nation.alliance_id,
                        'alliance_position': nation.alliance_position,
                        'cities': nation.cities,
                        'score': nation.score,
                        'population': nation.population,
                        'flag': nation.flag,
                        'vacation_mode_turns': nation.vacation_mode_turns,
                        'last_active': nation.last_active,
                        'soldiers': nation.soldiers,
                        'tanks': nation.tanks,
                        'aircraft': nation.aircraft,
                        'ships': nation.ships,
                        'missiles': nation.missiles,
                        'nukes': nation.nukes,
                        'spies': nation.spies,
                        'money': nation.money,
                        'credits': nation.credits,
                        'food': nation.food,
                        'uranium': nation.uranium,
                        'coal': nation.coal,
                        'oil': nation.oil,
                        'gasoline': nation.gasoline,
                        'munitions': nation.munitions,
                        'steel': nation.steel,
                        'aluminum': nation.aluminum,
                        'iron': nation.iron,
                        'bauxite': nation.bauxite,
                        'lead': nation.lead,
                        'projects': nation.projects,
                        'city_improvements': nation.city_improvements,
                        'war_policy': nation.war_policy,
                        'domestic_policy': nation.domestic_policy,
                        'alliance_position': nation.alliance_position
                    }
                    nations_data.append(nation_dict)
                
                self.logger.info(f"Successfully fetched {len(nations_data)} nations for alliance {alliance_id} using pnwkit")
                return nations_data
            except Exception as e:
                self.logger.error(f"pnwkit failed for alliance {alliance_id}: {e}")
        
        # Priority 3: Direct API call (last resort)
        self.logger.error(f"All API methods failed for alliance {alliance_id}. This should not happen if query.py is properly configured.")
        return nations_data
    
    def _transform_query_nation_to_bloc_format(self, query_nation: Dict) -> Dict:
        """Transform query.py nation format to expected bloc.py format."""
        # Handle the nested data structure from query.py
        nation_data = query_nation
        
        # Extract basic nation information
        nation_dict = {
            'nation_id': nation_data.get('id'),
            'nation_name': nation_data.get('nation_name'),
            'leader_name': nation_data.get('leader_name'),
            'continent': nation_data.get('continent', ''),  # May not be available in query.py
            'war_policy': nation_data.get('war_policy', ''),  # May not be available
            'domestic_policy': nation_data.get('domestic_policy', ''),  # May not be available
            'color': nation_data.get('color'),
            'alliance_id': nation_data.get('alliance_id'),
            'alliance_position': nation_data.get('alliance_position'),
            'cities': nation_data.get('num_cities', 0),
            'score': nation_data.get('score', 0),
            'population': nation_data.get('population', 0),
            'flag': nation_data.get('flag'),
            'vacation_mode_turns': nation_data.get('vacation_mode_turns', 0),
            'last_active': nation_data.get('last_active'),
            'soldiers': nation_data.get('soldiers', 0),
            'tanks': nation_data.get('tanks', 0),
            'aircraft': nation_data.get('aircraft', 0),
            'ships': nation_data.get('ships', 0),
            'missiles': nation_data.get('missiles', 0),
            'nukes': nation_data.get('nukes', 0),
            'spies': nation_data.get('spies', 0),
            'money': nation_data.get('money', 0),
            'credits': nation_data.get('credits', 0),
            'food': nation_data.get('food', 0),
            'uranium': nation_data.get('uranium', 0),
            'coal': nation_data.get('coal', 0),
            'oil': nation_data.get('oil', 0),
            'gasoline': nation_data.get('gasoline', 0),
            'munitions': nation_data.get('munitions', 0),
            'steel': nation_data.get('steel', 0),
            'aluminum': nation_data.get('aluminum', 0),
            'iron': nation_data.get('iron', 0),
            'bauxite': nation_data.get('bauxite', 0),
            'lead': nation_data.get('lead', 0),
            'projects': nation_data.get('projects', []),
            'city_improvements': self._extract_city_improvements(nation_data)
        }
        
        return nation_dict
    
    def _extract_city_improvements(self, nation_data: Dict) -> List[Dict]:
        """Extract city improvements from query.py format."""
        cities = nation_data.get('cities', [])
        if not cities:
            return []
        
        improvements_list = []
        for city in cities:
            if isinstance(city, dict):
                improvements_list.append({
                    'infrastructure': city.get('infrastructure', 0),
                    'stadium': city.get('stadium', 0),
                    'barracks': city.get('barracks', 0),
                    'airforcebase': city.get('airforcebase', 0),
                    'drydock': city.get('drydock', 0)
                })
        
        return improvements_list
    
    def _extract_nations_list(self, nations_data: Any, alliance_key: str) -> List[Dict]:
        """Extract a list of nation dictionaries from various possible data structures.
        
        This method handles edge cases where nations_data might be:
        - A list of dictionaries (expected case)
        - A single dictionary (convert to list with one item)
        - A dictionary containing a 'nations' key with list/dict
        - None or empty (return empty list)
        - Any other invalid structure (return empty list)
        """
        try:
            if nations_data is None:
                return []
            
            # Case 1: Already a list
            if isinstance(nations_data, list):
                # Filter for valid dictionary items
                return [item for item in nations_data if isinstance(item, dict)]
            
            # Case 2: Single dictionary - convert to list
            if isinstance(nations_data, dict):
                # Check if it contains a 'nations' key
                if 'nations' in nations_data:
                    nations_subdata = nations_data['nations']
                    if isinstance(nations_subdata, list):
                        return [item for item in nations_subdata if isinstance(item, dict)]
                    elif isinstance(nations_subdata, dict):
                        # If it's a dict of nations, convert values to list
                        return list(nations_subdata.values())
                    else:
                        self.logger.warning(f"Invalid 'nations' structure for {alliance_key}: {type(nations_subdata)}")
                        return []
                else:
                    # Single nation dict - wrap in list
                    return [nations_data]
            
            # Case 3: Invalid type
            self.logger.warning(f"Invalid nations data type for {alliance_key}: {type(nations_data)}")
            return []
            
        except Exception as e:
            self.logger.error(f"Error extracting nations list for {alliance_key}: {e}")
            self.logger.error(f"Data was: {type(nations_data)}")
            return []
    
    async def fetch_bloc_data(self) -> Dict[str, List[Dict]]:
        """Fetch data for all AERO alliances with 1.5 second delay between API calls."""
        bloc_data = {}
        user_data_manager = UserDataManager()
        
        for alliance_key, alliance_config in AERO_ALLIANCES.items():
            try:
                alliance_id = alliance_config.get('id')
                
                if alliance_id:  # Only fetch if alliance ID is configured
                    nations = await self.get_alliance_nations(alliance_id)
                    bloc_data[alliance_key] = nations
                    self.logger.info(f"Fetched {len(nations)} nations for {alliance_config['name']}")
                    self.logger.info(f"Fetched alliance {alliance_id} data ({len(nations)} nations) - data cached by query.py")
                    await asyncio.sleep(1.5)
                else:
                    self.logger.warning(f"No alliance ID configured for {alliance_key}")
                    bloc_data[alliance_key] = []
                    
            except Exception as e:
                self.logger.error(f"Error fetching data for {alliance_key}: {e}")
                bloc_data[alliance_key] = []
                    
            except Exception as e:
                self.logger.error(f"Error fetching data for {alliance_key}: {e}")
                bloc_data[alliance_key] = []
        
        return bloc_data
    
    async def refresh_bloc_data(self) -> bool:
        """Refresh all bloc data and update individual alliance files."""
        try:
            self.logger.info("Refreshing AERO bloc data...")
            
            # Fetch fresh data
            new_bloc_data = await self.fetch_bloc_data()
            
            # Update cache
            self.bloc_data = new_bloc_data
            self.last_update = datetime.now().isoformat()
            
            # Save the main bloc cache
            self.save_bloc_cache()
            
            # Save each alliance's data to its individual file
            user_data_manager = UserDataManager()
            for alliance_key, nations in self.bloc_data.items():
                alliance_config = AERO_ALLIANCES.get(alliance_key)
                if alliance_config:
                    alliance_id = alliance_config.get('id')
                    if alliance_id:
                        alliance_data = {
                            'nations': nations,
                            'alliance_id': alliance_id,
                            'alliance_name': alliance_config.get('name'),
                            'last_updated': self.last_update
                        }
                        alliance_file_key = f'alliance_{alliance_id}'
                        await user_data_manager.save_json_data(alliance_file_key, alliance_data)
                        self.logger.info(f"Saved {len(nations)} nations for alliance {alliance_id} to individual file")
            
            # Log summary
            total_nations = sum(len(nations) for nations in self.bloc_data.values())
            self.logger.info(f"Successfully refreshed bloc data: {total_nations} total nations across {len(self.bloc_data)} alliances")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error refreshing bloc data: {e}")
            return False
    
    def get_bloc_data(self) -> Dict[str, List[Dict]]:
        """Get current bloc data."""
        return self.bloc_data.copy()
    
    def get_alliance_data(self, alliance_key: str) -> List[Dict]:
        """Get data for a specific alliance."""
        return self.bloc_data.get(alliance_key, []).copy()
    
    def get_cache_age(self) -> Optional[float]:
        """Get cache age in minutes."""
        if not self.last_update:
            return None
        
        try:
            last_update_time = datetime.fromisoformat(self.last_update)
            age_minutes = (datetime.now() - last_update_time).total_seconds() / 60
            return age_minutes
        except:
            return None
    
    def is_cache_stale(self, max_age_minutes: int = 30) -> bool:
        """Check if cache is stale."""
        cache_age = self.get_cache_age()
        if cache_age is None:
            return True
        return cache_age > max_age_minutes


class BlocManager(commands.Cog):
    """Discord cog for AERO bloc management."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        
        try:
            self.logger.info("Initializing BlocManager...")
            self.alliance_manager = AllianceManager(bot)
            self.logger.info("BlocManager initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize BlocManager: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
    
    async def fetch_all_bloc_data(self) -> Dict[str, List[Dict]]:
        """Fetch all AERO bloc data."""
        try:
            # Check if cache is stale and refresh if needed
            if self.alliance_manager.is_cache_stale():
                await self.alliance_manager.refresh_bloc_data()
            
            # Return the current bloc data
            return self.alliance_manager.get_bloc_data()
        except Exception as e:
            self.logger.error(f"Error fetching bloc data: {e}")
            raise
    
    async def generate_bloc_totals_embed(self, bloc_data: Dict[str, List[Dict]]) -> discord.Embed:
        """Generate bloc totals embed from bloc data."""
        try:
            # Create a temporary BlocTotalsView to generate the embed
            temp_view = BlocTotalsView(0, self.bot, self.alliance_manager, bloc_data)
            return await temp_view.generate_bloc_totals_embed()
        except Exception as e:
            self.logger.error(f"Error generating bloc totals embed: {e}")
            raise
    
    def ma_role_check():
        """Role check decorator for MA commands - same as ma.py"""
        async def predicate(ctx):
            # Allow specific authorized users unconditionally
            authorized_users = [
                PRIMAL_USER_ID,
                ARIES_USER_ID,
                CARNAGE_USER_ID,
                BENEVOLENT_USER_ID,
                TECH_USER_ID,
            ]

            is_authorized = ctx.author.id in authorized_users

            # If in a guild, allow leadership roles: Predaking, IA, MG, HG
            if not is_authorized and ctx.guild:
                try:
                    role_map = get_role_ids(ctx.guild.id)
                except Exception:
                    role_map = {}

                leadership_roles = ["Predaking", "IA", "MG", "HG"]
                author_role_ids = {role.id for role in getattr(ctx.author, "roles", [])}

                for role_name in leadership_roles:
                    for role_id in role_map.get(role_name, []) or []:
                        if role_id in author_role_ids:
                            is_authorized = True
                            break
                    if is_authorized:
                        break

            return is_authorized

        return commands.check(predicate)
    
    @commands.hybrid_command(name='bloc_totals', description='Display AERO bloc totals')
    @ma_role_check()
    async def bloc_totals_command(self, ctx: commands.Context):
        """Display AERO bloc totals."""
        try:
            # Check if cache is stale and refresh if needed
            if self.alliance_manager.is_cache_stale():
                refresh_msg = await ctx.send("🔄 Refreshing bloc data...")
                success = await self.alliance_manager.refresh_bloc_data()
                if success:
                    await refresh_msg.edit(content="✅ Bloc data refreshed successfully!")
                else:
                    await refresh_msg.edit(content="⚠️ Using cached bloc data (refresh failed)")
            
            # Get bloc data
            bloc_data = self.alliance_manager.get_bloc_data()
            
            self.logger.info(f"Bloc data retrieved: {len(bloc_data)} alliances, keys: {list(bloc_data.keys())}")
            
            if not bloc_data:
                await ctx.send("❌ No bloc data available.")
                return
            
            # Create view with bloc data
            view = BlocTotalsView(
                author_id=ctx.author.id,
                bot=self.bot,
                alliance_cog=self.alliance_manager,
                bloc_data=bloc_data
            )

            embed = await view.generate_custom_bloc_embed(view.selected_alliances)
            
            await ctx.send(embed=embed, view=view)
            
        except Exception as e:
            self.logger.error(f"Error in bloc_totals command: {e}")
            await ctx.send(f"❌ An error occurred: {str(e)}")
    
    @commands.hybrid_command(name='bloc_refresh', description='Manually refresh AERO bloc data')
    @ma_role_check()
    async def bloc_refresh_command(self, ctx: commands.Context):
        """Manually refresh AERO bloc data."""
        try:
            refresh_msg = await ctx.send("🔄 Refreshing AERO bloc data...")
            
            success = await self.alliance_manager.refresh_bloc_data()
            
            if success:
                bloc_data = self.alliance_manager.get_bloc_data()
                total_nations = sum(len(nations) for nations in bloc_data.values())
                
                await refresh_msg.edit(
                    content=f"✅ Bloc data refreshed successfully!\n"
                           f"📊 Fetched data for {len(bloc_data)} alliances\n"
                           f"🏛️ Total nations: {total_nations:,}"
                )
            else:
                await refresh_msg.edit(content="❌ Failed to refresh bloc data.")
                
        except Exception as e:
            self.logger.error(f"Error in bloc_refresh command: {e}")
            await ctx.send(f"❌ An error occurred: {str(e)}")
    
    @commands.hybrid_command(name='bloc_status', description='Show AERO bloc cache status')
    @ma_role_check()
    async def bloc_status_command(self, ctx: commands.Context):
        """Show AERO bloc cache status."""
        try:
            cache_age = self.alliance_manager.get_cache_age()
            bloc_data = self.alliance_manager.get_bloc_data()
            
            embed = discord.Embed(
                title="📊 AERO Bloc Status",
                description="Current bloc data cache status",
                color=discord.Color.blue()
            )
            
            # Cache age
            if cache_age is not None:
                embed.add_field(
                    name="⏱️ Cache Age",
                    value=f"{cache_age:.1f} minutes old",
                    inline=False
                )
            else:
                embed.add_field(
                    name="⏱️ Cache Age",
                    value="No cache available",
                    inline=False
                )
            
            # Alliance breakdown
            alliance_status = []
            for alliance_key, alliance_config in AERO_ALLIANCES.items():
                nations = bloc_data.get(alliance_key, [])
                alliance_status.append(
                    f"{alliance_config['emoji']} **{alliance_config['name']}**: {len(nations)} nations"
                )
            
            embed.add_field(
                name="🏛️ Alliance Data",
                value="\n".join(alliance_status),
                inline=False
            )
            
            # Total nations
            total_nations = sum(len(nations) for nations in bloc_data.values())
            embed.add_field(
                name="📊 Totals",
                value=f"**Total Nations:** {total_nations:,}",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in bloc_status command: {e}")
            await ctx.send(f"❌ An error occurred: {str(e)}")


async def setup(bot: commands.Bot):
    """Setup function for loading the cog."""
    try:
        logger = logging.getLogger(__name__)
        logger.info("Setting up BlocManager cog...")
        bloc_manager = BlocManager(bot)
        await bot.add_cog(bloc_manager)
        logger.info("BlocManager cog setup completed successfully")
    except Exception as e:
        logger.error(f"Failed to setup BlocManager cog: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise


class MilitaryView(discord.ui.View):
    """View for displaying military analysis for a specific alliance."""
    
    def __init__(self, author_id: int, bot: commands.Bot, alliance_cog: 'AllianceManager', nations: List[Dict], alliance_key: str, selected_alliances: List[str] = None):
        super().__init__(timeout=300)  # 5 minute timeout
        self.author_id = author_id
        self.bot = bot
        self.alliance_cog = alliance_cog
        self.current_nations = nations
        self.alliance_key = alliance_key
        self.selected_alliances = selected_alliances or [alliance_key]
        self.alliance_config = AERO_ALLIANCES[alliance_key]
        # Create bloc data with just this alliance's data for the dropdown
        bloc_data = {self.alliance_key: self.current_nations}
        bloc_alliance_select = BlocAllianceSelect(author_id, self, bloc_data)
        self.add_item(bloc_alliance_select)

    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the interaction is from the command author."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ You cannot use this menu.")
            return False
        return True

    async def generate_military_embed(self, nations: List[Dict] = None) -> discord.Embed:
        """Generate the military analysis embed."""
        try:
            # Handle multiple selected alliances
            if hasattr(self, 'selected_alliances') and len(self.selected_alliances) > 1:
                # Combine nations from all selected alliances
                combined_nations = []
                for alliance_key in self.selected_alliances:
                    if alliance_key == "cybertron_combined":
                        cybertron_nations = self.alliance_cog.get_alliance_nations(AERO_ALLIANCES['cybertron'].get('id') or AERO_ALLIANCES['cybertron'].get('ids', [])[0])
                        prime_bank_nations = self.alliance_cog.get_alliance_nations(AERO_ALLIANCES['prime_bank'].get('id') or AERO_ALLIANCES['prime_bank'].get('ids', [])[0])
                        combined_nations.extend(cybertron_nations or [])
                        combined_nations.extend(prime_bank_nations or [])
                    else:
                        alliance_config = AERO_ALLIANCES.get(alliance_key, {})
                        alliance_nations = self.alliance_cog.get_alliance_nations(alliance_config.get('id') or alliance_config.get('ids', [])[0])
                        if alliance_nations:
                            combined_nations.extend(alliance_nations)
                current_nations = combined_nations
                alliance_name = f"{len(self.selected_alliances)} Selected Alliances"
                alliance_emoji = "⚔️"
                alliance_color = discord.Color.from_rgb(75, 0, 130)  # Dark purple for bloc
            else:
                # Single alliance mode (original behavior)
                current_nations = nations or self.current_nations
                if not current_nations:
                    current_nations = await self.alliance_cog.get_alliance_nations(self.alliance_config.get('id') or self.alliance_config.get('ids', [])[0])
                    if not current_nations:
                        return discord.Embed(
                            title=f"❌ {self.alliance_config['name']} - No Data",
                            description="Failed to retrieve alliance data.",
                            color=self.alliance_config['color']
                        )
                    self.current_nations = current_nations
                alliance_name = self.alliance_config['name']
                alliance_emoji = self.alliance_config['emoji']
                alliance_color = self.alliance_config['color']
            
            # Get active nations for military analysis
            active_nations = get_active_nations(current_nations)
            full_mill_data = await self.alliance_cog.calculate_full_mill_data(active_nations)
            
            embed = discord.Embed(
                title=f"{alliance_emoji} {alliance_name} Military Analysis",
                description="Alliance military capacity and production analysis",
                color=alliance_color
            )
            
            # Military Units - Current/Max
            embed.add_field(
                name="⚔️ Military Units (Current/Max)",
                value=(
                    f"🪖 **Soldiers:** {full_mill_data['current_soldiers']:,}/{full_mill_data['max_soldiers']:,}\n"
                    f"🛡️ **Tanks:** {full_mill_data['current_tanks']:,}/{full_mill_data['max_tanks']:,}\n"
                    f"✈️ **Aircraft:** {full_mill_data['current_aircraft']:,}/{full_mill_data['max_aircraft']:,}\n"
                    f"🚢 **Ships:** {full_mill_data['current_ships']:,}/{full_mill_data['max_ships']:,}"
                ),
                inline=False
            )
            
            # Daily Production
            embed.add_field(
                name="🏭 Daily Production",
                value=(
                    f"🪖 **Soldiers:** {full_mill_data['daily_soldiers']:,}/day\n"
                    f"🛡️ **Tanks:** {full_mill_data['daily_tanks']:,}/day\n"
                    f"✈️ **Aircraft:** {full_mill_data['daily_aircraft']:,}/day\n"
                    f"🚢 **Ships:** {full_mill_data['daily_ships']:,}/day\n"
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
                    f"🛡️ **Tanks:** {full_mill_data['tank_gap']:,}\n"
                    f"✈️ **Aircraft:** {full_mill_data['aircraft_gap']:,}\n"
                    f"🚢 **Ships:** {full_mill_data['ship_gap']:,}"
                ),
                inline=False
            )
            
            # Time to max capacity (days)
            import math
            embed.add_field(
                name="⏱️ Time to Max Capacity",
                value=(
                    f"🪖 **Soldiers:** {math.ceil(full_mill_data['soldier_days'])} days\n"
                    f"🛡️ **Tanks:** {math.ceil(full_mill_data['tank_days'])} days\n"
                    f"✈️ **Aircraft:** {math.ceil(full_mill_data['aircraft_days'])} days\n"
                    f"🚢 **Ships:** {math.ceil(full_mill_data['ship_days'])} days"
                ),
                inline=False
            )
            
            embed.set_footer(text=f"Generated at {datetime.now().strftime('%H:%M:%S')} | Use other buttons to view different data")
            
            return embed
            
        except Exception as e:
            alliance_name = getattr(self, 'alliance_config', {}).get('name', 'Unknown') if not (hasattr(self, 'selected_alliances') and len(self.selected_alliances) > 1) else f"{len(self.selected_alliances)} Selected Alliances"
            alliance_color = getattr(self, 'alliance_config', {}).get('color', discord.Color.red()) if not (hasattr(self, 'selected_alliances') and len(self.selected_alliances) > 1) else discord.Color.red()
            return discord.Embed(
                title=f"❌ {alliance_name} Military Error",
                description=f"An error occurred: {str(e)}",
                color=alliance_color
            )
    
    @discord.ui.button(label="Bloc Totals", style=discord.ButtonStyle.primary, emoji="📊", row=1)
    async def bloc_totals_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show bloc totals overview."""
        try:
            await interaction.response.defer()
            
            # Get the full bloc data from alliance manager
            bloc_data = self.alliance_cog.get_bloc_data()
            view = BlocTotalsView(self.author_id, self.bot, self.alliance_cog, bloc_data)
            embed = await view.generate_custom_bloc_embed(view.selected_alliances)
            
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=view
            )
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")

    @discord.ui.button(label="Improvements", style=discord.ButtonStyle.secondary, emoji="🏗️", row=1)
    async def improvements_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show improvements breakdown."""
        try:
            await interaction.response.defer()
            
            view = ImprovementsView(self.author_id, self.bot, self.alliance_cog, self.current_nations, self.alliance_key)
            embed = await view.generate_improvements_embed(self.current_nations)
            
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=view
            )
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")

    @discord.ui.button(label="Projects", style=discord.ButtonStyle.secondary, emoji="🧩", row=1)
    async def projects_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show project totals."""
        try:
            await interaction.response.defer()
            
            view = ProjectTotalsView(self.author_id, self.bot, self.alliance_cog, self.current_nations, self.alliance_key)
            embed = await view.generate_project_totals_embed(self.current_nations)
            
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=view
            )
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")


class ImprovementsView(discord.ui.View):
    """View for displaying improvements breakdown for a specific alliance."""
    
    def __init__(self, author_id: int, bot: commands.Bot, alliance_cog: 'AllianceManager', nations: List[Dict], alliance_key: str, selected_alliances: List[str] = None):
        super().__init__(timeout=300)  # 5 minute timeout
        self.author_id = author_id
        self.bot = bot
        self.alliance_cog = alliance_cog
        self.current_nations = nations
        self.alliance_key = alliance_key
        self.selected_alliances = selected_alliances or [alliance_key]
        self.alliance_config = AERO_ALLIANCES[alliance_key]
        # Create bloc data with just this alliance's data for the dropdown
        bloc_data = {self.alliance_key: self.current_nations}
        bloc_alliance_select = BlocAllianceSelect(author_id, self, bloc_data)
        self.add_item(bloc_alliance_select)

    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the interaction is from the command author."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ You cannot use this menu.")
            return False
        return True

    async def generate_improvements_embed(self, nations: List[Dict] = None) -> discord.Embed:
        """Generate the improvements breakdown embed."""
        try:
            # Handle multiple selected alliances
            if hasattr(self, 'selected_alliances') and len(self.selected_alliances) > 1:
                # Combine nations from all selected alliances
                combined_nations = []
                for alliance_key in self.selected_alliances:
                    if alliance_key == "cybertron_combined":
                        cybertron_nations = self.alliance_cog.get_alliance_nations(AERO_ALLIANCES['cybertron'].get('id') or AERO_ALLIANCES['cybertron'].get('ids', [])[0])
                        prime_bank_nations = self.alliance_cog.get_alliance_nations(AERO_ALLIANCES['prime_bank'].get('id') or AERO_ALLIANCES['prime_bank'].get('ids', [])[0])
                        combined_nations.extend(cybertron_nations or [])
                        combined_nations.extend(prime_bank_nations or [])
                    else:
                        alliance_config = AERO_ALLIANCES.get(alliance_key, {})
                        alliance_nations = self.alliance_cog.get_alliance_nations(alliance_config.get('id') or alliance_config.get('ids', [])[0])
                        if alliance_nations:
                            combined_nations.extend(alliance_nations)
                current_nations = combined_nations
                alliance_name = f"{len(self.selected_alliances)} Selected Alliances"
                alliance_emoji = "🏗️"
                alliance_color = discord.Color.from_rgb(75, 0, 130)  # Dark purple for bloc
            else:
                # Single alliance mode (original behavior)
                current_nations = nations or self.current_nations
                if not current_nations:
                    current_nations = await self.alliance_cog.get_alliance_nations(self.alliance_config.get('id') or self.alliance_config.get('ids', [])[0])
                    if not current_nations:
                        return discord.Embed(
                            title=f"❌ {self.alliance_config['name']} - No Data",
                            description="Failed to retrieve alliance data.",
                            color=self.alliance_config['color']
                        )
                    self.current_nations = current_nations
                alliance_name = self.alliance_config['name']
                alliance_emoji = self.alliance_config['emoji']
                alliance_color = self.alliance_config['color']
            
            # Get active nations for improvements analysis
            active_nations = get_active_nations(current_nations)
            improvements_data = await calculate_improvements_data(active_nations)
            
            embed = discord.Embed(
                title=f"{alliance_emoji} {alliance_name} Improvements Breakdown",
                description="City improvements breakdown across active alliance members (excludes Applicants & VM)",
                color=alliance_color
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
            # Determine alliance info for error message
            if hasattr(self, 'selected_alliances') and len(self.selected_alliances) > 1:
                alliance_name = f"{len(self.selected_alliances)} Selected Alliances"
                alliance_color = discord.Color.from_rgb(75, 0, 130)
            else:
                alliance_name = self.alliance_config['name']
                alliance_color = self.alliance_config['color']
            
            return discord.Embed(
                title=f"❌ {alliance_name} Improvements Error",
                description=f"An error occurred: {str(e)}",
                color=alliance_color
            )
    


    @discord.ui.button(label="Bloc Totals", style=discord.ButtonStyle.primary, emoji="📊", row=1)
    async def bloc_totals_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show bloc totals overview."""
        try:
            await interaction.response.defer()
            
            # Get the full bloc data from alliance manager
            bloc_data = self.alliance_cog.get_bloc_data()
            view = BlocTotalsView(self.author_id, self.bot, self.alliance_cog, bloc_data)
            embed = await view.generate_custom_bloc_embed(view.selected_alliances)
            
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=view
            )
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")

    @discord.ui.button(label="Military", style=discord.ButtonStyle.secondary, emoji="⚔️", row=1)
    async def military_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show military analysis."""
        try:
            await interaction.response.defer()
            
            view = MilitaryView(self.author_id, self.bot, self.alliance_cog, self.current_nations, self.alliance_key, self.selected_alliances)
            embed = await view.generate_military_embed(self.current_nations)
            
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=view
            )
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")

    @discord.ui.button(label="Projects", style=discord.ButtonStyle.secondary, emoji="🧩", row=1)
    async def projects_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show project totals."""
        try:
            await interaction.response.defer()
            
            view = ProjectTotalsView(self.author_id, self.bot, self.alliance_cog, self.current_nations, self.alliance_key, self.selected_alliances)
            embed = await view.generate_project_totals_embed(self.current_nations)
            
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=view
            )
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")


class ProjectTotalsView(discord.ui.View):
    """View for displaying project totals for a specific alliance."""
    
    def __init__(self, author_id: int, bot: commands.Bot, alliance_cog: 'AllianceManager', nations: List[Dict], alliance_key: str, selected_alliances: List[str] = None):
        super().__init__(timeout=300)  # 5 minute timeout
        self.author_id = author_id
        self.bot = bot
        self.alliance_cog = alliance_cog
        self.current_nations = nations
        self.alliance_key = alliance_key
        self.selected_alliances = selected_alliances or [alliance_key]
        self.alliance_config = AERO_ALLIANCES[alliance_key]
        # Create bloc data with just this alliance's data for the dropdown
        bloc_data = {self.alliance_key: self.current_nations}
        bloc_alliance_select = BlocAllianceSelect(author_id, self, bloc_data)
        self.add_item(bloc_alliance_select)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the interaction is from the command author."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ You cannot use this menu.")
            return False
        return True

    async def generate_project_totals_embed(self, nations: List[Dict] = None) -> discord.Embed:
        """Generate the project totals embed."""
        try:
            # Handle multiple selected alliances
            if hasattr(self, 'selected_alliances') and len(self.selected_alliances) > 1:
                # Combine nations from all selected alliances
                combined_nations = []
                for alliance_key in self.selected_alliances:
                    if alliance_key == "cybertron_combined":
                        cybertron_nations = self.alliance_cog.get_alliance_nations(AERO_ALLIANCES['cybertron'].get('id') or AERO_ALLIANCES['cybertron'].get('ids', [])[0])
                        prime_bank_nations = self.alliance_cog.get_alliance_nations(AERO_ALLIANCES['prime_bank'].get('id') or AERO_ALLIANCES['prime_bank'].get('ids', [])[0])
                        combined_nations.extend(cybertron_nations or [])
                        combined_nations.extend(prime_bank_nations or [])
                    else:
                        alliance_config = AERO_ALLIANCES.get(alliance_key, {})
                        alliance_nations = self.alliance_cog.get_alliance_nations(alliance_config.get('id') or alliance_config.get('ids', [])[0])
                        if alliance_nations:
                            combined_nations.extend(alliance_nations)
                current_nations = combined_nations
                alliance_name = f"{len(self.selected_alliances)} Selected Alliances"
                alliance_emoji = "🏗️"
                alliance_color = discord.Color.from_rgb(75, 0, 130)  # Dark purple for bloc
            else:
                # Single alliance mode (original behavior)
                current_nations = nations or self.current_nations
                if not current_nations:
                    current_nations = await self.alliance_cog.get_alliance_nations(self.alliance_config.get('id') or self.alliance_config.get('ids', [])[0])
                    if not current_nations:
                        return discord.Embed(
                            title=f"❌ {self.alliance_config['name']} - No Data",
                            description="Failed to retrieve alliance data.",
                            color=self.alliance_config['color']
                        )
                    self.current_nations = current_nations
                alliance_name = self.alliance_config['name']
                alliance_emoji = self.alliance_config['emoji']
                alliance_color = self.alliance_config['color']
            
            # Get active nations for project analysis
            active_nations = get_active_nations(current_nations)
            
            # Count projects
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
            
            # Count projects by category
            category_counts = {}
            for category, projects in project_categories.items():
                category_counts[category] = {}
                for project_name, project_key in projects:
                    count = 0
                    for nation in active_nations:
                        nation_projects = nation.get('projects', [])
                        if isinstance(nation_projects, list):
                            for project in nation_projects:
                                if isinstance(project, str) and project.lower() == project_key.lower():
                                    count += 1
                                elif isinstance(project, dict) and project.get('name', '').lower() == project_key.lower():
                                    count += 1
                    category_counts[category][project_name] = count
            
            embed = discord.Embed(
                title=f"{alliance_emoji} {alliance_name} Project Totals",
                description="National project statistics (active members only)",
                color=alliance_color
            )
            
            # Add fields for each category
            for category, projects in category_counts.items():
                category_text = ""
                total_projects = 0
                for project_name, count in sorted(projects.items(), key=lambda x: x[1], reverse=True):
                    if count > 0:
                        category_text += f"**{project_name}:** {count} nations\n"
                        total_projects += count
                
                if category_text:
                    embed.add_field(
                        name=f"{category} Projects",
                        value=category_text,
                        inline=False
                    )
            
            # Nations without projects
            nations_without_projects = []
            for nation in active_nations:
                nation_projects = nation.get('projects', [])
                if not nation_projects or (isinstance(nation_projects, list) and len(nation_projects) == 0):
                    nations_without_projects.append(nation.get('nation_name', 'Unknown'))
            
            if nations_without_projects:
                no_projects_text = "\n".join(nations_without_projects[:10])  # Show first 10
                if len(nations_without_projects) > 10:
                    no_projects_text += f"\n... and {len(nations_without_projects) - 10} more"
                
                embed.add_field(
                    name="❌ Nations Without Projects",
                    value=no_projects_text,
                    inline=False
                )
            
            embed.set_footer(text=f"Generated at {datetime.now().strftime('%H:%M:%S')} | Use other buttons to view different data")
            
            return embed
            
        except Exception as e:
            # Determine alliance info for error message
            if hasattr(self, 'selected_alliances') and len(self.selected_alliances) > 1:
                alliance_name = f"{len(self.selected_alliances)} Selected Alliances"
                alliance_color = discord.Color.from_rgb(75, 0, 130)
            else:
                alliance_name = self.alliance_config['name']
                alliance_color = self.alliance_config['color']
            
            return discord.Embed(
                title=f"❌ {alliance_name} Projects Error",
                description=f"An error occurred: {str(e)}",
                color=alliance_color
            )
    


    @discord.ui.button(label="Bloc Totals", style=discord.ButtonStyle.primary, emoji="📊", row=1)
    async def bloc_totals_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show bloc totals overview."""
        try:
            await interaction.response.defer()
            
            # Get the full bloc data from alliance manager
            bloc_data = self.alliance_cog.get_bloc_data()
            view = BlocTotalsView(self.author_id, self.bot, self.alliance_cog, bloc_data)
            embed = await view.generate_custom_bloc_embed(view.selected_alliances)
            
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=view
            )
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")

    @discord.ui.button(label="Military", style=discord.ButtonStyle.secondary, emoji="⚔️", row=1)
    async def military_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show military analysis."""
        try:
            await interaction.response.defer()
            
            view = MilitaryView(self.author_id, self.bot, self.alliance_cog, self.current_nations, self.alliance_key, self.selected_alliances)
            embed = await view.generate_military_embed(self.current_nations)
            
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=view
            )
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")

    @discord.ui.button(label="Improvements", style=discord.ButtonStyle.secondary, emoji="🏗️", row=1)
    async def improvements_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show improvements breakdown."""
        try:
            await interaction.response.defer()
            
            view = ImprovementsView(self.author_id, self.bot, self.alliance_cog, self.current_nations, self.alliance_key, self.selected_alliances)
            embed = await view.generate_improvements_embed(self.current_nations)
            
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=view
            )
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")


# Export the view for use in other modules
__all__ = ['BlocTotalsView', 'MilitaryView', 'ImprovementsView', 'ProjectTotalsView', 'AllianceManager', 'BlocManager', 'AERO_ALLIANCES']


async def setup(bot: commands.Bot):
    """Setup function for loading the cog."""
    await bot.add_cog(BlocManager(bot))