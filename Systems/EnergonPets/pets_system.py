# Standard library imports
import asyncio
import logging
import random
import sys
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union

# Third-party imports
import discord
from discord.ext import commands
from discord import app_commands, ui

# Local application imports
from Systems.user_data_manager import user_data_manager
from .pet_levels import (
    LEVEL_THRESHOLDS, 
    PET_STAGES, 
    STAGE_EMOJIS, 
    MISSION_TYPES, 
    MISSION_DIFFICULTIES, 
    AUTOBOT_PET_NAMES, 
    DECEPTICON_PET_NAMES,
    get_next_level_xp,
    get_stage_emoji, 
    get_stage_name, 
    get_pet_name, 
    load_level_data, 
    add_experience, 
    create_level_up_embed, 
    send_level_up_embed
)

# Constants
MONSTER_EMOJIS = {
    "monster": "🤖",
    "boss": "👹",
    "titan": "👑"
}

RARITY_EMOJIS = {
    "common": "⚪",
    "uncommon": "🟢", 
    "rare": "🔵",
    "epic": "🟣", 
    "legendary": "🟠",
    "mythic": "🔴"
}

# Configure logging
logger = logging.getLogger('pets_system')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

class PetStatusView(discord.ui.View):
    """Interactive view for pet status with optimized performance and caching"""
    
    def __init__(self, user_id: int, pet_system, commands_cog, pet_data=None):
        super().__init__(timeout=300)  # 5 minute timeout
        self.user_id = user_id
        self.pet_system = pet_system
        self.commands_cog = commands_cog
        self.showing_breakdown = False
        self.pet_data = pet_data
        self._cached_equipment_stats = None
        self._cached_embed = None
        self._last_update = 0
        self._update_lock = asyncio.Lock()
        
        # Add buttons
        self.add_item(RefreshButton())
        self.add_item(BreakdownButton())
    
    async def create_main_embed(self) -> discord.Embed:
        """Create the main pet status embed with caching"""
        current_time = time.time()
        
        # Use cached embed if recent and valid
        if (self._cached_embed and 
            current_time - self._last_update < 60 and 
            self._cached_equipment_stats is not None):
            return self._cached_embed
        
        async with self._update_lock:
            # Double-check in case another task was updating
            if (self._cached_embed and 
                current_time - self._last_update < 60 and 
                self._cached_equipment_stats is not None):
                return self._cached_embed
                
            # Load pet data if not provided
            if not self.pet_data:
                self.pet_data = await self.pet_system.get_user_pet(self.user_id)
            
            pet = self.pet_data
            if not pet:
                return discord.Embed(
                    title="Error", 
                    description="Pet not found!", 
                    color=discord.Color.red()
                )
            
            # Get faction data
            faction = pet.get('faction', 'Unknown').lower()
            embed_color, faction_emoji = self._get_faction_style(faction)
            
            # Get stage info
            stage_emoji, stage_name = self._get_stage_info(pet)
            
            # Create embed
            embed = discord.Embed(
                title=f"{stage_emoji} {stage_name} - {faction.title()} - {pet['name']}",
                color=embed_color
            )
            
            # Get equipment stats
            self._cached_equipment_stats = await self.pet_system.get_equipment_stats(self.user_id)
            equipment_stats = self._cached_equipment_stats
            
            # Calculate totals
            totals = self._calculate_totals(pet, equipment_stats)
            
            # Add fields to embed
            await self._add_embed_fields(embed, pet, totals, faction, self.user_id)
            
            # Cache the result
            self._cached_embed = embed
            self._last_update = current_time
            
            return embed
    
    def _get_faction_style(self, faction: str) -> Tuple[int, str]:
        """Get faction-specific styling"""
        if faction == 'autobot':
            return 0xCC0000, "🔴"
        elif faction == 'decepticon':
            return 0x800080, "🟣"
        return 0x808080, "⚡"
    
    def _get_stage_info(self, pet: Dict[str, Any]) -> Tuple[str, str]:
        """Get pet's stage emoji and name"""
        try:
            return get_stage_emoji(pet['level']), get_stage_name(pet['level'])
        except:
            return "🥚", f"Level {pet['level']}"
    
    def _calculate_totals(self, pet: Dict[str, Any], equipment_stats: Dict[str, int]) -> Dict[str, int]:
        """Calculate total stats including equipment bonuses"""
        return {
            'attack': pet['attack'] + equipment_stats['attack'],
            'defense': pet['defense'] + equipment_stats['defense'],
            'energy': pet['max_energy'] + equipment_stats['energy'],
            'maintenance': pet['max_maintenance'] + equipment_stats['maintenance'],
            'happiness': pet['max_happiness'] + equipment_stats['happiness']
        }
    
    async def _add_embed_fields(self, embed: discord.Embed, pet: Dict[str, Any], 
                         totals: Dict[str, int], faction: str, user_id: str) -> None:
        """Add fields to the embed"""
        # Creation date
        created = datetime.fromisoformat(pet["created_at"])
        embed.add_field(name="🗓️ Created", value=created.strftime("%m/%d/%y at %I:%M %p"), inline=True)
        
        # Stats
        embed.add_field(
            name="⚡ Power", 
            value=f"⚔️ {totals['attack']} | 🛡️ {totals['defense']}", 
            inline=True
        )
        
        # Level progress
        self._add_level_progress(embed, pet, faction)
        
        # Resources
        embed.add_field(name="🔋 Energy", value=f"{int(pet['energy'])}/{totals['energy']}", inline=True)
        embed.add_field(name="🔧 Maintenance", value=f"{int(pet['maintenance'])}/{totals['maintenance']}", inline=True)
        embed.add_field(name="😊 Happiness", value=f"{int(pet['happiness'])}/{totals['happiness']}", inline=True)
        
        # Battle Statistics (Combined Regular + Mega-Fights)
        battles_won = pet.get('battles_won', 0)
        battles_lost = pet.get('battles_lost', 0)
        
        # Get mega-fight statistics
        try:
            user_data = await user_data_manager.get_user_data(user_id)
            mega_fights_won = user_data.get('stats', {}).get('mega_fights_won', 0)
            mega_fights_lost = user_data.get('stats', {}).get('mega_fights_lost', 0)
        except Exception:
            mega_fights_won = 0
            mega_fights_lost = 0
        
        # Calculate combined totals for REAL battle statistics
        total_battles_won = battles_won + mega_fights_won
        total_battles_lost = battles_lost + mega_fights_lost
        total_battles = total_battles_won + total_battles_lost
        
        if total_battles > 0:
            win_rate = (total_battles_won / total_battles) * 100
            battle_stats = f"**Won:** {total_battles_won} | **Lost:** {total_battles_lost} | **Rate:** {win_rate:.1f}%"
        else:
            battle_stats = f"**Won:** {total_battles_won} | **Lost:** {total_battles_lost} | **Rate:** N/A"
        
        embed.add_field(name="⚔️ REAL Battle Stats", value=battle_stats, inline=False)
        
        # Total Energon Earned (including search energon which can be negative)
        total_energon = (
            pet.get('total_battle_energon', 0) +
            pet.get('total_mission_energon', 0) +
            pet.get('total_training_energon', 0)
        )

        # Add pet search energon from user data
        try:
            user_data = await user_data_manager.get_user_data(user_id)
            pet_search_energon = user_data.get('pet_search_energon', 0)
            total_energon += pet_search_energon
        except Exception:
            pass  
        
        embed.add_field(name="💰 Total Energon Earned", value=f"**{total_energon:,}**", inline=True)
        
        # Pet Search Helps (if any)
        try:
            energon_data = await user_data_manager.get_energon_data(user_id)
            pet_search_helps = energon_data.get('pet_search_helps', 0)
            if pet_search_helps > 0:
                embed.add_field(name="🔍 Pet Search Helps", value=f"**{pet_search_helps:,}**", inline=True)
        except Exception:
            pass 
        
        # Combiner Team Information
        await self._add_combiner_info(embed, user_id)
        
        # Equipment
        self._add_equipment_info(embed, pet)
    
    async def _add_combiner_info(self, embed: discord.Embed, user_id: str) -> None:
        """Add combiner team information to the embed"""
        try:
            # Get user's combiner team data
            combiner_data = await user_data_manager.get_user_pet_combiner_team(user_id)
            
            if combiner_data:
                team_id = combiner_data.get("team_id")
                user_role = combiner_data.get("role", "Unknown")
                
                if team_id:
                    # Get the full team composition from the theme system
                    from ..Random.themer import DataManager
                    data_manager = DataManager()
                    team_composition = await data_manager.get_user_theme_data_section(
                        team_id, "combiner_teams", {"🦾": [], "🦿": []}
                    )
                    
                    # Get combiner name if available
                    combiner_name_data = await data_manager.get_user_theme_data_section(
                        team_id, "combiner_name", {}
                    )
                    combiner_name = combiner_name_data.get("name", "Unnamed Combiner")
                    
                    # Build team member list
                    team_members = []
                    part_names = {"🦾": "Arms", "🦿": "Legs"}
                    
                    for emoji, part_name in part_names.items():
                        members = team_composition.get(emoji, [])
                        for member_id in members:
                            try:
                                # Get pet data for each member
                                member_pet = await user_data_manager.get_pet_data(member_id)
                                if member_pet:
                                    pet_name = member_pet.get("name", f"Pet {member_id}")
                                    # Try to get Discord user for display name
                                    try:
                                        user = self.pet_system.bot.get_user(int(member_id))
                                        display_name = user.display_name if user else f"User {member_id}"
                                    except:
                                        display_name = f"User {member_id}"
                                    
                                    team_members.append(f"{emoji} **{pet_name}** ({display_name})")
                            except Exception as e:
                                logger.error(f"Error getting member data for {member_id}: {e}")
                                team_members.append(f"{emoji} Unknown Pet")
                    
                    if team_members:
                        team_info = "\n".join(team_members)
                        embed.add_field(
                            name=f"🤖 Combiner Team: {combiner_name}",
                            value=f"**Your Role:** {user_role}\n\n**Team Members:**\n{team_info}",
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name="🤖 Combiner Team",
                            value=f"**Team:** {combiner_name}\n**Your Role:** {user_role}\n*Team data loading...*",
                            inline=False
                        )
        except Exception as e:
            logger.error(f"Error adding combiner info: {e}")
            # Don't add field if there's an error to avoid breaking the embed
    
    def _add_level_progress(self, embed: discord.Embed, pet: Dict[str, Any], faction: str) -> None:
        """Add level progress bar to embed"""
        if pet['level'] < 500:
            # Use the dedicated function from pet_levels.py for accurate XP thresholds
            from .pet_levels import get_next_level_xp
            threshold = get_next_level_xp(pet['level'])
            if threshold == 0:  # Fallback for edge cases
                threshold = LEVEL_THRESHOLDS.get(pet['level'], 1000)
            
            progress = min(pet['experience'] / threshold, 1.0) if threshold > 0 else 0
            filled_length = int(10 * progress)
            
            # Choose progress bar character based on faction
            if faction == 'autobot':
                filled_char = "🟥"
            elif faction == 'decepticon':
                filled_char = "🟪"
            else:
                filled_char = "🟨"
                
            bar = filled_char * filled_length + "⬛" * (10 - filled_length)
            embed.add_field(
                name="📊 Level Progress", 
                value=f"**Level {pet['level']}** - {bar} {pet['experience']}/{threshold} XP", 
                inline=False
            )
        else:
            embed.add_field(
                name="📊 Level Progress", 
                value=f"**Level {pet['level']}** - 🌟 MAX LEVEL REACHED! 🌟", 
                inline=False
            )
    
    def _add_equipment_info(self, embed: discord.Embed, pet: Dict[str, Any]) -> None:
        """Add equipment information to embed"""
        equipment = pet.get('equipment', {})
        if not equipment:
            return
            
        equipped_items = []
        for slot, item in equipment.items():
            if item and isinstance(item, dict):
                emoji = RARITY_EMOJIS.get(item.get('rarity', 'common'), '⚪')
                equipped_items.append(f"{emoji} {item.get('name', 'Unknown')}")
        
        if equipped_items:
            embed.add_field(
                name="⚔️ Equipment", 
                value="\n".join(equipped_items), 
                inline=False
            )

    async def create_breakdown_embed(self, user_id: str):
        """Create a detailed breakdown embed for the pet."""
        try:
            pet = await self.pet_system.get_user_pet(user_id)
            if not pet:
                embed = discord.Embed(
                    title="❌ No Pet Found",
                    description="You don't have a pet yet! Use `/pet recruit` to get one.",
                    color=discord.Color.red()
                )
                return embed

            embed = discord.Embed(
                title=f"📊 {pet['name']}'s Stats Breakdown",
                description=f"**Level {pet['level']}** - {pet['faction']} {pet.get('type', 'Pet')}",
                color=discord.Color.red() if pet.get('faction', '').lower() == 'autobot' else discord.Color.purple()
            )

            # XP Statistics
            xp_stats = []
            if 'mission_xp_earned' in pet:
                xp_stats.append(f"**Mission XP:** {pet['mission_xp_earned']:,} XP")
            if 'battle_xp_earned' in pet:
                xp_stats.append(f"**Battle XP:** {pet['battle_xp_earned']:,} XP")
            if 'training_xp_earned' in pet:
                xp_stats.append(f"**Training XP:** {pet['training_xp_earned']:,} XP")
            if 'repair_xp_earned' in pet:
                xp_stats.append(f"**Repair XP:** {pet['repair_xp_earned']:,} XP")
            if 'charge_xp_earned' in pet:
                xp_stats.append(f"**Charge XP:** {pet['charge_xp_earned']:,} XP")
            if 'play_xp_earned' in pet:
                xp_stats.append(f"**Play XP:** {pet['play_xp_earned']:,} XP")
            if 'search_xp_earned' in pet:
                xp_stats.append(f"**Search XP:** {pet['search_xp_earned']:,} XP")

            if xp_stats:
                embed.add_field(
                    name="📈 XP Sources",
                    value="\n".join(xp_stats),
                    inline=False
                )

            # Energon Statistics
            energon_stats = []
            if 'total_mission_energon' in pet:
                energon_stats.append(f"**Mission Energon:** {pet['total_mission_energon']:,} ")
            if 'total_battle_energon' in pet:
                energon_stats.append(f"**Battle Energon:** {pet['total_battle_energon']:,} ")
            if 'total_training_energon' in pet:
                energon_stats.append(f"**Training Energon:** {pet['total_training_energon']:,} ")
            # Get pet search energon directly from user data
            try:
                user_data = await user_data_manager.get_user_data(user_id)
                pet_search_energon = user_data.get('pet_search_energon', 0)
                if pet_search_energon != 0:  # Show even if negative or zero
                    if pet_search_energon >= 0:
                        energon_stats.append(f"**Search Energon:** {pet_search_energon:,} ")
                    else:
                        energon_stats.append(f"**Search Energon:** {pet_search_energon:,} ")
                
            except Exception:
                pass  # Skip if user data is not available

            if energon_stats:
                embed.add_field(
                    name="💰 Energon Sources",
                    value="\n".join(energon_stats),
                    inline=False
                )

            # Mega-Fight Statistics
            mega_fight_stats = []
            try:
                user_data = await user_data_manager.get_user_data(user_id)
                mega_fights_won = user_data.get('stats', {}).get('mega_fights_won', 0)
                mega_fights_lost = user_data.get('stats', {}).get('mega_fights_lost', 0)
                total_mega_fights = mega_fights_won + mega_fights_lost
                
                if total_mega_fights > 0:
                    mega_fight_rate = (mega_fights_won / total_mega_fights) * 100
                    mega_fight_stats.append(f"**Mega-Fights Won:** {mega_fights_won:,}")
                    mega_fight_stats.append(f"**Mega-Fights Lost:** {mega_fights_lost:,}")
                    mega_fight_stats.append(f"**Win Rate:** {mega_fight_rate:.1f}%")
                else:
                    mega_fight_stats.append(f"**Mega-Fights Won:** {mega_fights_won:,}")
                    mega_fight_stats.append(f"**Mega-Fights Lost:** {mega_fights_lost:,}")
                    mega_fight_stats.append(f"**Win Rate:** N/A")
                    
            except Exception:
                # If user data is not available, show default stats
                mega_fight_stats.append(f"**Mega-Fights Won:** 0")
                mega_fight_stats.append(f"**Mega-Fights Lost:** 0")
                mega_fight_stats.append(f"**Win Rate:** N/A")
            
            if mega_fight_stats:
                embed.add_field(
                    name="🤖 Mega-Fight Statistics",
                    value="\n".join(mega_fight_stats),
                    inline=False
                )

            # Summary
            total_xp_earned = pet.get('mission_xp_earned', 0) + pet.get('battle_xp_earned', 0) + \
                             pet.get('training_xp_earned', 0) + \
                             pet.get('repair_xp_earned', 0) + pet.get('charge_xp_earned', 0) + \
                             pet.get('play_xp_earned', 0) + pet.get('search_xp_earned', 0)
            
            total_energon_earned = pet.get('total_mission_energon', 0) + pet.get('total_battle_energon', 0) + \
                                   pet.get('total_training_energon', 0)
            
            # Add pet search energon from user data
            try:
                user_data = await user_data_manager.get_user_data(user_id)
                pet_search_energon = user_data.get('pet_search_energon', 0)
                total_energon_earned += pet_search_energon
            except Exception:
                pass  # Skip if user data is not available
            
            summary_text = f"**Current Level:** {pet['level']}\n**Total XP Earned:** {total_xp_earned:,}\n**Total Energon Earned:** {total_energon_earned:,} 💰"
            embed.add_field(name="📋 Summary", value=summary_text, inline=False)

            embed.set_footer(text="💡 Use /pet train or /pet battle to earn more XP!")
            return embed

        except Exception as e:
            logger.error(f"Error creating breakdown embed: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to load pet statistics.",
                color=discord.Color.red()
            )
            return embed

class RefreshButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.primary, label="🔄 Refresh", custom_id="refresh_status")
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        view = self.view
        view._cached_embed = None  # Invalidate cache
        embed = await view.create_main_embed()
        await interaction.edit_original_response(embed=embed, view=view)

class BreakdownButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.secondary, label="📊 Stats Breakdown", custom_id="show_breakdown")
    
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        view.showing_breakdown = not view.showing_breakdown
        await interaction.response.defer()
        
        if view.showing_breakdown:
            embed = await view.create_breakdown_embed(str(view.user_id))
            await interaction.edit_original_response(embed=embed, view=view)
        else:
            embed = await view.create_main_embed()
            await interaction.edit_original_response(embed=embed, view=view)

class PetEquipmentView(discord.ui.View):
    """Interactive view for displaying and managing pet equipment with optimized performance"""
    
    # Class-level constants
    ITEMS_PER_PAGE = 10
    STAT_EMOJIS = {
        "attack": "⚔️",
        "defense": "🛡️",
        "energy": "⚡",
        "maintenance": "🔧",
        "happiness": "😊"
    }
    RARITY_EMOJIS = {
        "common": "⚪",
        "uncommon": "🟢", 
        "rare": "🔵",
        "epic": "🟣", 
        "legendary": "🟠",
        "mythic": "🔴"
    }
    TYPE_EMOJIS = {
        "chassis_plating": "🩻",
        "energy_cores": "🔋",
        "utility_modules": "💾"
    }
    
    def __init__(self, user_id: int, pet_system, items: List[Dict[str, Any]]):
        super().__init__(timeout=300)  # 5 minute timeout
        self.user_id = user_id
        self.pet_system = pet_system
        self.items = items
        self.current_page = 0
        self.total_pages = max(1, (len(items) + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE)
        self._cached_embeds = {}  # Cache for embeds
        self._pet_data = None  # Cache for pet data
        
        # Initialize UI components
        self._setup_ui()
    
    async def _get_pet_data(self) -> Dict[str, Any]:
        """Get and cache pet data"""
        if not self._pet_data:
            self._pet_data = await self.pet_system.get_user_pet(self.user_id)
        return self._pet_data
    
    def _setup_ui(self) -> None:
        """Initialize UI components"""
        # Add navigation buttons
        self.add_item(FirstPageButton())
        self.add_item(PrevPageButton())
        self.add_item(NextPageButton())
        self.add_item(LastPageButton())
        self.add_item(CloseViewButton())
        
        # Add equipment type filter dropdown
        self.add_item(EquipmentTypeSelect())
    
    def _get_embed_color(self) -> int:
        """Get embed color based on pet's faction"""
        pet = self._pet_data or {}
        faction = pet.get('faction', '').lower()
        return {
            'autobot': 0xCC0000,
            'decepticon': 0x800080
        }.get(faction, 0x00AE86)
    
    def _get_page_items(self, page: int) -> List[Dict[str, Any]]:
        """Get items for the specified page"""
        start_idx = page * self.ITEMS_PER_PAGE
        end_idx = start_idx + self.ITEMS_PER_PAGE
        return self.items[start_idx:end_idx]
    
    async def create_embed(self, page: int) -> discord.Embed:
        """Create or get cached embed for the specified page"""
        if page in self._cached_embeds:
            return self._cached_embeds[page]
            
        # Get pet data if not cached
        if not self._pet_data:
            self._pet_data = await self.pet_system.get_user_pet(self.user_id)
        
        # Create new embed
        embed = await self._build_embed(page)
        self._cached_embeds[page] = embed
        return embed
    
    async def _build_embed(self, page: int) -> discord.Embed:
        """Build embed for the specified page"""
        page_items = self._get_page_items(page)
        pet = self._pet_data or {}
        pet_name = pet.get('name', 'Your Pet')
        
        embed = discord.Embed(
            title=f"🎒 {pet_name}'s Equipment Collection",
            description=f"Page {page + 1}/{self.total_pages} • {len(self.items)} total items",
            color=self._get_embed_color()
        )
        
        if not page_items:
            embed.add_field(
                name="📭 No Items Found",
                value="You don't have any pet equipment items yet!",
                inline=False
            )
            return embed
            
        # Add items to embed
        for idx, item in enumerate(page_items, start=page * self.ITEMS_PER_PAGE):
            embed.add_field(
                **self._format_item_field(item, idx),
                inline=False
            )
            
        return embed
    
    def _format_item_field(self, item: Dict[str, Any], idx: int) -> Dict[str, str]:
        """Format an item as an embed field"""
        rarity = item.get('rarity', 'common').lower()
        item_type = item.get('type', 'unknown')
        name = item.get('name', 'Unknown Item')
        description = item.get('description', 'No description available')
        
        return {
            'name': f"{self.RARITY_EMOJIS.get(rarity, '⚪')} {self.TYPE_EMOJIS.get(item_type, '📦')} {name}",
            'value': self._format_item_value(description, item.get('stat_bonus', {})),
            'inline': False
        }
    
    def _format_item_value(self, description: str, stat_bonus: Dict[str, int]) -> str:
        """Format item value with description and stats"""
        if not stat_bonus:
            return f"*{description}*"
            
        stat_text = " | ".join(
            f"{self.STAT_EMOJIS.get(stat, '📊')} +{value}"
            for stat, value in stat_bonus.items()
        )
        return f"*{description}*\n{stat_text}"
    
    def update_buttons(self) -> None:
        """Update button states based on current page"""
        for child in self.children:
            if isinstance(child, (FirstPageButton, PrevPageButton)):
                child.disabled = self.current_page == 0
            elif isinstance(child, (NextPageButton, LastPageButton)):
                child.disabled = self.current_page >= self.total_pages - 1
    
    async def show_page(self, interaction: discord.Interaction, page: int) -> None:
        """Show the specified page"""
        if not 0 <= page < self.total_pages:
            return
            
        self.current_page = page
        self.update_buttons()
        
        embed = await self.create_embed(page)
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_timeout(self) -> None:
        """Handle view timeout"""
        for child in self.children:
            child.disabled = True
            
        if hasattr(self, 'message'):
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass

# Button Classes
class FirstPageButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.gray, emoji="⏮️", row=1)
        
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        await view.show_page(interaction, 0)

class PrevPageButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.gray, emoji="◀️", row=1)
        
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        await view.show_page(interaction, max(0, view.current_page - 1))

class NextPageButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.gray, emoji="▶️", row=1)
        
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        await view.show_page(interaction, min(view.total_pages - 1, view.current_page + 1))

class LastPageButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.gray, emoji="⏭️", row=1)
        
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        await view.show_page(interaction, view.total_pages - 1)

class CloseViewButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.danger, emoji="❌", row=1)
        
    async def callback(self, interaction: discord.Interaction):
        await interaction.message.delete()

class EquipmentTypeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="All Types", emoji="📦", value="all"),
            discord.SelectOption(label="Chassis Plating", emoji="🩻", value="chassis_plating"),
            discord.SelectOption(label="Energy Cores", emoji="🔋", value="energy_cores"),
            discord.SelectOption(label="Utility Modules", emoji="💾", value="utility_modules")
        ]
        super().__init__(
            placeholder="Filter by type...",
            min_values=1,
            max_values=1,
            options=options,
            row=0
        )
    
    async def callback(self, interaction: discord.Interaction):
        # Implementation for filtering by equipment type
        await interaction.response.defer()

class PetSystem:
    """Main pet system class with optimized performance and resource management"""
    
    def __init__(self, bot):
        self.bot = bot
        self._data_loaded = asyncio.Event()
        self._load_task = None
        self._cache = {}
        self._cache_lock = asyncio.Lock()
        self._last_save = {}
        self._pending_saves = asyncio.Queue()
        self._save_task = None
        self._shutdown = False
        self.monsters_data = {}
        self.bosses_data = {}
        self.titans_data = {}
        self.charge_cooldowns = {}  
        self.play_cooldowns = {}
        self.repair_cooldowns = {}
        self._save_task = asyncio.create_task(self._save_worker())
        self._load_task = asyncio.create_task(self._preload_data())
    
    async def _preload_data(self) -> None:
        """Preload all required data asynchronously"""
        try:
            await self._load_monsters_and_bosses()
            self._data_loaded.set()
        except Exception as e:
            logger.error(f"Error preloading data: {e}")
            # Schedule retry with exponential backoff
            retry_delay = min(60, 2 ** (len(self._load_task.retries) if hasattr(self._load_task, 'retries') else 1))
            await asyncio.sleep(retry_delay)
            self._load_task.retries = getattr(self._load_task, 'retries', 0) + 1
            self._load_task = asyncio.create_task(self._preload_data())
    
    async def _load_monsters_and_bosses(self) -> None:
        """Load monsters, bosses, and titans with error handling"""
        try:
            data = await user_data_manager.get_monsters_and_bosses_data()
            self._process_monster_data(data)
        except Exception as e:
            logger.error(f"Error loading monster data: {e}")
            raise
    
    def _process_monster_data(self, data: Dict) -> None:
        """Process and categorize monster data"""
        self.monsters_data = {}
        self.bosses_data = {}
        self.titans_data = {}
        
        if 'monsters' in data:
            monsters_json = data['monsters']
            if isinstance(monsters_json, dict):
                for rarity, monster_list in monsters_json.items():
                    if isinstance(monster_list, list):
                        for monster in monster_list:
                            self._categorize_monster(monster, rarity.lower())
        
        # Process direct boss and titan structures
        for category in ['bosses', 'titans']:
            if category in data:
                category_json = data[category]
                if isinstance(category_json, dict):
                    for rarity, entity_list in category_json.items():
                        if isinstance(entity_list, list):
                            for entity in entity_list:
                                self._categorize_monster(entity, rarity.lower(), category)
        
        logger.info(
            f"Loaded monsters: {sum(len(m) for m in self.monsters_data.values())}, "
            f"bosses: {sum(len(b) for b in self.bosses_data.values())}, "
            f"titans: {sum(len(t) for t in self.titans_data.values())}"
        )
    
    def _categorize_monster(self, monster: Dict, rarity: str, force_type: str = None) -> None:
        """Categorize monster into appropriate collection"""
        monster_type = force_type or monster.get('type', 'monster').lower()
        target = {
            'monster': self.monsters_data,
            'boss': self.bosses_data,
            'titan': self.titans_data
        }.get(monster_type, self.monsters_data)
        
        if rarity not in target:
            target[rarity] = []
        target[rarity].append(monster)
    



    
    async def create_pet(self, user_id: int, faction: str) -> Dict[str, Any]:
        """Create a new pet with faction-based starting stats"""
        faction_lower = faction.lower()
        stats = self._get_faction_stats(faction_lower)
        
        pet_data = {
            "name": get_pet_name(faction),
            "faction": faction.capitalize(),
            "level": 1,
            "experience": 0,
            "energy": stats["energy"],
            "max_energy": stats["energy"],
            "happiness": stats["happiness"],
            "max_happiness": stats["happiness"],
            "maintenance": 100,
            "max_maintenance": 100,
            "attack": stats["attack"],
            "defense": stats["defense"],
            "created_at": datetime.utcnow().isoformat(),
            "equipment": {},
            "inventory": [],
            "battles_won": 0,
            "battles_lost": 0,
            "missions_completed": 0,
            "total_mission_energon": 0,
            "total_battle_energon": 0,
            "total_training_energon": 0,
            "mission_xp_earned": 0,
            "battle_xp_earned": 0,
            "training_xp_earned": 0,
            "search_xp_earned": 0,
            "charge_xp_earned": 0,
            "play_xp_earned": 0,
            "repair_xp_earned": 0
        }
        
        # Save the new pet
        await self._queue_save(user_id, pet_data)
        return pet_data
    
    def _get_faction_stats(self, faction: str) -> Dict[str, int]:
        """Get starting stats based on faction"""
        if faction == 'autobot':
            return {"attack": 10, "defense": 12, "happiness": 200, "energy": 100}
        return {"attack": 12, "defense": 10, "happiness": 100, "energy": 200}

    def _get_cooldown_duration(self, command_type: str, percentage: str) -> int:
        """Get cooldown duration in seconds based on command type and percentage"""
        # Different cooldown durations for different command types
        cooldown_maps = {
            "charge": {
                "50%": 900,    # 15 minutes
                "75%": 1800,   # 30 minutes  
                "100%": 3600   # 1 hour
            },
            "play": {
                "50%": 900,    # 15 minutes
                "75%": 1800,   # 30 minutes  
                "100%": 3600   # 1 hour
            },
            "repair": {
                "50%": 15,     # 15 seconds
                "75%": 30,     # 30 seconds  
                "100%": 60     # 1 minute
            }
        }
        
        command_map = cooldown_maps.get(command_type, cooldown_maps["charge"])
        return command_map.get(percentage, command_map.get("50%", 900))

    def _is_command_on_cooldown(self, command_type: str, user_id: int) -> Tuple[bool, int]:
        """Check if a command is on cooldown for user"""
        # Get the cooldown dictionary for this command type
        cooldown_dict = getattr(self, f'{command_type}_cooldowns', {})
        
        if user_id not in cooldown_dict:
            return False, 0
        
        current_time = time.time()
        cooldown_end = cooldown_dict[user_id]
        
        if current_time >= cooldown_end:
            # Cooldown expired, remove it
            del cooldown_dict[user_id]
            return False, 0
        
        # Still on cooldown
        remaining_time = int(cooldown_end - current_time)
        return True, remaining_time

    def _set_command_cooldown(self, command_type: str, user_id: int, percentage: str) -> None:
        """Set cooldown for a command"""
        # Ensure the cooldown dictionary exists for this command type
        cooldown_attr = f'{command_type}_cooldowns'
        if not hasattr(self, cooldown_attr):
            setattr(self, cooldown_attr, {})
        
        cooldown_dict = getattr(self, cooldown_attr)
        cooldown_duration = self._get_cooldown_duration(command_type, percentage)
        cooldown_dict[user_id] = time.time() + cooldown_duration

    async def add_experience(self, user_id: int, xp_amount: int, source: str = "unknown") -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Add experience to a user's pet - wraps the imported add_experience function"""
        return await add_experience(user_id, xp_amount, source)

    async def charge_pet(self, user_id: int, percentage: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Charge pet's energy by percentage (50%, 75%, or 100%)"""
        pet = await self.get_user_pet(user_id)
        if not pet:
            return False, "You don't have a pet!", []
        
        # Check cooldown
        on_cooldown, remaining_time = self._is_command_on_cooldown("charge", user_id)
        if on_cooldown:
            minutes_remaining = remaining_time // 60
            seconds_remaining = remaining_time % 60
            return False, f"Your pet is still charging! Wait {minutes_remaining}m {seconds_remaining}s", []
        
        # Validate percentage input
        valid_percentages = {"50%", "75%", "100%"}
        if percentage not in valid_percentages:
            return False, "Invalid percentage! Choose from: 50%, 75%, or 100%", []
        
        # Calculate total max energy including equipment bonuses
        equipment_stats = await self.get_equipment_stats(user_id)
        max_energy = pet['max_energy'] + equipment_stats.get('energy', 0)
        
        if pet['energy'] >= max_energy:
            return False, f"Your pet is already fully charged! ({int(pet['energy'])}/{max_energy})", []
        
        # Calculate energy gain based on percentage
        percentage_map = {"50%": 0.5, "75%": 0.75, "100%": 1.0}
        energy_percentage = percentage_map[percentage]
        target_energy = max_energy * energy_percentage
        
        # Calculate actual energy gain (don't exceed max)
        energy_gain = min(target_energy - pet['energy'], max_energy - pet['energy'])
        pet['energy'] = min(pet['energy'] + energy_gain, max_energy)
        
        # Set cooldown based on percentage charged
        self._set_command_cooldown("charge", user_id, percentage)
        
        # Add XP based on percentage (more XP for higher percentages)
        xp_map = {"50%": 10, "75%": 25, "100%": 50}
        xp_gain = xp_map[percentage]
        leveled_up, level_gains = await self.add_experience(user_id, xp_gain, "charge")
        
        await self._queue_save(user_id, pet)
        return True, f"Charged your pet to {percentage}! (+{int(energy_gain)}⚡, +{xp_gain}XP)", level_gains

    async def play_with_pet(self, user_id: int, percentage: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Play with pet to increase happiness by percentage (50%, 75%, or 100%)"""
        pet = await self.get_user_pet(user_id)
        if not pet:
            return False, "You don't have a pet!", []
        
        # Check cooldown
        on_cooldown, remaining_time = self._is_command_on_cooldown("play", user_id)
        if on_cooldown:
            minutes_remaining = remaining_time // 60
            seconds_remaining = remaining_time % 60
            return False, f"Your pet needs rest from playing! Wait {minutes_remaining}m {seconds_remaining}s", []
        
        # Validate percentage input
        valid_percentages = {"50%", "75%", "100%"}
        if percentage not in valid_percentages:
            return False, "Invalid percentage! Choose from: 50%, 75%, or 100%", []
        
        # Calculate total max happiness including equipment bonuses
        equipment_stats = await self.get_equipment_stats(user_id)
        max_happiness = pet['max_happiness'] + equipment_stats.get('happiness', 0)
        
        if pet['happiness'] >= max_happiness:
            return False, f"Your pet is already maximally happy! ({int(pet['happiness'])}/{max_happiness})", []
        
        # Calculate happiness gain based on percentage
        percentage_map = {"50%": 0.5, "75%": 0.75, "100%": 1.0}
        happiness_percentage = percentage_map[percentage]
        target_happiness = max_happiness * happiness_percentage
        
        # Calculate actual happiness gain (don't exceed max)
        happiness_gain = min(target_happiness - pet['happiness'], max_happiness - pet['happiness'])
        pet['happiness'] = min(pet['happiness'] + happiness_gain, max_happiness)
        
        # Set cooldown based on percentage played
        self._set_command_cooldown("play", user_id, percentage)
        
        # Add XP based on percentage (more XP for higher percentages)
        xp_map = {"50%": 10, "75%": 25, "100%": 50}
        xp_gain = xp_map[percentage]
        leveled_up, level_gains = await self.add_experience(user_id, xp_gain, "play")
        
        await self._queue_save(user_id, pet)
        return True, f"Played with your pet to {percentage}! (+{int(happiness_gain)}😊, +{xp_gain}XP)", level_gains

    async def repair_pet(self, user_id: int, percentage: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Repair pet's maintenance by percentage (50%, 75%, or 100%)"""
        pet = await self.get_user_pet(user_id)
        if not pet:
            return False, "You don't have a pet!", []
        
        # Check cooldown
        on_cooldown, remaining_time = self._is_command_on_cooldown("repair", user_id)
        if on_cooldown:
            minutes_remaining = remaining_time // 60
            seconds_remaining = remaining_time % 60
            return False, f"Your pet is still being repaired! Wait {minutes_remaining}m {seconds_remaining}s", []
        
        # Validate percentage input
        valid_percentages = {"50%", "75%", "100%"}
        if percentage not in valid_percentages:
            return False, "Invalid percentage! Choose from: 50%, 75%, or 100%", []
        
        # Calculate total max maintenance including equipment bonuses
        equipment_stats = await self.get_equipment_stats(user_id)
        max_maintenance = pet['max_maintenance'] + equipment_stats.get('maintenance', 0)
        
        if pet['maintenance'] >= max_maintenance:
            return False, f"Your pet is already fully repaired! ({int(pet['maintenance'])}/{max_maintenance})", []
        
        # Calculate maintenance gain based on percentage
        percentage_map = {"50%": 0.5, "75%": 0.75, "100%": 1.0}
        maintenance_percentage = percentage_map[percentage]
        target_maintenance = max_maintenance * maintenance_percentage
        
        # Calculate actual maintenance gain (don't exceed max)
        maintenance_gain = min(target_maintenance - pet['maintenance'], max_maintenance - pet['maintenance'])
        pet['maintenance'] = min(pet['maintenance'] + maintenance_gain, max_maintenance)
        
        # Set cooldown based on percentage repaired
        self._set_command_cooldown("repair", user_id, percentage)
        
        # Add XP based on percentage (more XP for higher percentages)
        xp_map = {"50%": 10, "75%": 25, "100%": 50}
        xp_gain = xp_map[percentage]
        leveled_up, level_gains = await self.add_experience(user_id, xp_gain, "repair")
        
        await self._queue_save(user_id, pet)
        return True, f"Repaired your pet to {percentage}! (+{int(maintenance_gain)}🔧, +{xp_gain}XP)", level_gains

    async def train_pet(self, user_id: int, difficulty: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Train pet to gain stats"""
        pet = await self.get_user_pet(user_id)
        if not pet:
            return False, "You don't have a pet!", []
        
        difficulty_map = {"easy": 1, "medium": 2, "hard": 3}
        multiplier = difficulty_map.get(difficulty.lower(), 1)
        
        # Check energy
        energy_cost = 10 * multiplier
        if pet['energy'] < energy_cost:
            return False, f"Not enough energy! Need {energy_cost}⚡", []
        
        pet['energy'] -= energy_cost
        
        # Calculate rewards with better scaling
        energon_gain = random.randint(5, 15) * multiplier
        stat_gain = random.randint(1, 3) * multiplier
        
        # Improved XP scaling based on difficulty
        xp_ranges = {"easy": (10, 100), "medium": (100, 250), "hard": (250, 500)}
        xp_min, xp_max = xp_ranges.get(difficulty.lower(), (8, 15))
        xp_gain = random.randint(xp_min, xp_max)
        
        # Fixed percentage losses based on difficulty (no level scaling)
        # Easy: 25%, Medium: 50%, Hard: 75% of max values
        percentage_losses = {"easy": 0.25, "medium": 0.50, "hard": 0.75}
        percentage_loss = percentage_losses.get(difficulty.lower(), 0.25)
        
        # Get current max values for percentage calculations (including equipment bonuses)
        equipment_stats = await self.get_equipment_stats(user_id)
        max_happiness = pet.get('max_happiness', 100) + equipment_stats.get('happiness', 0)
        max_energy = pet.get('max_energy', 100) + equipment_stats.get('energy', 0)
        max_maintenance = pet.get('max_maintenance', 100) + equipment_stats.get('maintenance', 0)
        
        # Calculate actual losses (fixed percentage of max values)
        happiness_loss = int(max_happiness * percentage_loss)
        energy_loss = int(max_energy * percentage_loss)
        maintenance_loss = int(max_maintenance * percentage_loss * 0.5)  # Half maintenance loss
        
        # 5% chance to increase attack or defense by 1-10 points
        if random.random() < 0.05:  # 5% chance
            stat_gain = random.randint(1, 10)  # 1-10 stat gain
            if random.choice([True, False]):
                pet['attack'] += stat_gain
                stat_type = "attack"
            else:
                pet['defense'] += stat_gain
                stat_type = "defense"
        else:
            stat_gain = 0
            stat_type = "none"
        
        # Apply all percentage-based losses (don't go below 0)
        pet['happiness'] = max(0, pet.get('happiness', 100) - happiness_loss)
        pet['energy'] = max(0, pet['energy'] - energy_loss)  # Additional energy drain from training
        pet['maintenance'] = max(0, pet.get('maintenance', 100) - maintenance_loss)
        
        leveled_up, level_gains = await self.add_experience(user_id, xp_gain, "training")
        
        # Track training energon
        pet['total_training_energon'] = pet.get('total_training_energon', 0) + energon_gain
        
        # Update user's main energon balance for training
        try:
            # Use proper energon tracking method to update total_earned
            await user_data_manager.add_energon(str(user_id), energon_gain)
            
            # Track energon earned through pet activities
            await user_data_manager.update_energon_stat(str(user_id), "pet_energon_earned", energon_gain)
        except Exception as e:
            logger.error(f"Error updating user energon for training: {e}")
        
        await self._queue_save(user_id, pet)
        if stat_gain > 0:
            return True, f"Training complete! (+{energon_gain}💰, +{stat_gain} {stat_type}, +{xp_gain}XP, -{happiness_loss}😊, -{energy_loss}⚡, -{maintenance_loss}🔧)", level_gains
        else:
            return True, f"Training complete! (+{energon_gain}💰, +{xp_gain}XP, -{happiness_loss}😊, -{energy_loss}⚡, -{maintenance_loss}🔧)", level_gains

    async def send_mission(self, user_id: int, difficulty: str) -> Tuple[bool, str]:
        """Send pet on a mission"""
        pet = await self.get_user_pet(user_id)
        if not pet:
            return False, "You don't have a pet!"
        
        difficulty_map = {"easy": 1, "medium": 2, "hard": 3}
        difficulty_level = difficulty_map.get(difficulty.lower(), 1)
        
        # Check energy
        energy_cost = 25 * difficulty_level
        if pet['energy'] < energy_cost:
            return False, f"Not enough energy! Need {energy_cost}⚡"
        
        pet['energy'] -= energy_cost
        
        # Calculate success - easier missions have higher success rates
        success_rates = {"easy": 0.8, "medium": 0.6, "hard": 0.4}
        success_rate = success_rates.get(difficulty.lower(), 0.6)
        success = random.random() < success_rate
        
        if success:
            # Better rewards for harder missions
            energon_ranges = {"easy": (10, 20), "medium": (20, 40), "hard": (40, 80)}
            xp_ranges = {"easy": (5, 10), "medium": (15, 45), "hard": (55, 75)}
            
            energon_min, energon_max = energon_ranges.get(difficulty.lower(), (10, 20))
            xp_min, xp_max = xp_ranges.get(difficulty.lower(), (5, 10))
            
            energon_gain = random.randint(energon_min, energon_max)
            xp_gain = random.randint(xp_min, xp_max)
            
            pet['missions_completed'] = pet.get('missions_completed', 0) + 1
            pet['total_mission_energon'] = pet.get('total_mission_energon', 0) + energon_gain
            
            leveled_up, level_gains = await self.add_experience(user_id, xp_gain, "mission")
            
            # Update user's main energon balance
            try:
                # Use proper energon tracking method to update total_earned
                await user_data_manager.add_energon(str(user_id), energon_gain)
                
                # Track energon earned through pet activities
                await user_data_manager.update_energon_stat(str(user_id), "pet_energon_earned", energon_gain)
            except Exception as e:
                logger.error(f"Error updating user energon for mission: {e}")
            
            await self._queue_save(user_id, pet)
            return True, f"Mission successful! (+{energon_gain}💰, +{xp_gain}XP)"
        else:
            # Mission failed - give small XP for attempt but no energon
            failure_xp_ranges = {"easy": (1, 3), "medium": (2, 5), "hard": (3, 8)}
            xp_min, xp_max = failure_xp_ranges.get(difficulty.lower(), (1, 3))
            xp_gain = random.randint(xp_min, xp_max)
            pet['missions_failed'] = pet.get('missions_failed', 0) + 1
            
            # Apply maintenance and happiness losses for failed missions
            maintenance_loss_ranges = {"easy": (5, 10), "medium": (15, 45), "hard": (55, 75)}
            happiness_loss_ranges = {"easy": (5, 10), "medium": (15, 45), "hard": (55, 75)}
            
            maint_min, maint_max = maintenance_loss_ranges.get(difficulty.lower(), (5, 10))
            happy_min, happy_max = happiness_loss_ranges.get(difficulty.lower(), (5, 10))
            
            maintenance_loss = random.randint(maint_min, maint_max)
            happiness_loss = random.randint(happy_min, happy_max)
            
            # Apply losses (don't go below 0)
            pet['maintenance'] = max(0, pet.get('maintenance', 100) - maintenance_loss)
            pet['happiness'] = max(0, pet.get('happiness', 100) - happiness_loss)
            
            leveled_up, level_gains = await self.add_experience(user_id, xp_gain, "mission")
            
            await self._queue_save(user_id, pet)
            return True, f"Mission failed! Your pet gained {xp_gain}XP but lost {maintenance_loss}🔧 maintenance and {happiness_loss}😊 happiness."

    async def delete_pet(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Delete a user's pet permanently"""
        pet = await self.get_user_pet(user_id)
        if not pet:
            return None
        
        # Remove from cache
        async with self._cache_lock:
            if str(user_id) in self._cache:
                del self._cache[str(user_id)]
        
        # Delete from storage
        await user_data_manager.delete_pet_data(str(user_id))
        return pet

    async def unequip_item(self, user_id: int, slot: str) -> Tuple[bool, str]:
        """Unequip an item from a pet"""
        pet = await self.get_user_pet(user_id)
        if not pet:
            return False, "You don't have a pet!"
        
        equipment = pet.get('equipment', {})
        if slot not in equipment or not equipment[slot]:
            return False, f"No item equipped in {slot.replace('_', ' ')} slot!"
        
        item = equipment[slot]
        item_name = item.get('name', 'Unknown Item')
        
        # Add to inventory
        inventory = pet.get('inventory', [])
        inventory.append(item)
        pet['inventory'] = inventory
        
        # Remove from equipment
        equipment[slot] = None
        
        await self._queue_save(user_id, pet)
        return True, f"Unequipped {item_name} from {slot.replace('_', ' ')}!"

    async def equip_item(self, user_id: int, item_id: str) -> Tuple[bool, str]:
        """Equip an item to a pet"""
        if item_id == "none":
            return True, "No item selected."
            
        pet = await self.get_user_pet(user_id)
        if not pet:
            return False, "You don't have a pet!"
        
        # Get equipment data
        equipment_data = await self.get_pet_equipment_data()
        if item_id not in equipment_data:
            return False, "Invalid item ID!"
        
        item_data = equipment_data[item_id]
        item_type = item_data.get('type')
        if not item_type:
            return False, "Invalid item type!"
        
        # Check if item exists in inventory
        inventory = pet.get('inventory', [])
        item_to_equip = None
        for item in inventory:
            if isinstance(item, dict) and item.get('id') == item_id:
                item_to_equip = item
                break
        
        if not item_to_equip:
            return False, f"You don't have {item_data.get('name', 'this item')} in your inventory!"
        
        # Check if slot is already occupied
        equipment = pet.get('equipment', {})
        current_item = equipment.get(item_type)
        
        # Remove from inventory
        inventory.remove(item_to_equip)
        pet['inventory'] = inventory
        
        # If slot has item, add it back to inventory
        if current_item:
            inventory.append(current_item)
        
        # Equip new item
        equipment[item_type] = item_to_equip
        pet['equipment'] = equipment
        
        await self._queue_save(user_id, pet)
        return True, f"Equipped {item_data.get('name', 'item')} to {item_type.replace('_', ' ')}!"

    async def get_all_pet_items(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all pet items for a user"""
        pet = await self.get_user_pet(user_id)
        if not pet:
            return []
        
        inventory = pet.get('inventory', [])
        equipment = pet.get('equipment', {})
        
        # Add equipped items to the list
        all_items = inventory.copy()
        for slot, item in equipment.items():
            if item and isinstance(item, dict):
                item['equipped'] = True
                item['slot'] = slot
                all_items.append(item)
        
        return all_items

    async def get_pet_equipment_data(self) -> Dict[str, Dict[str, Any]]:
        """Get pet equipment data from JSON"""
        try:
            data = await user_data_manager.get_pet_equipment_data()
            return data.get('items', {})
        except Exception as e:
            logger.error(f"Error loading pet equipment data: {e}")
            return {}

    async def migrate_pet_data(self, pet: Dict[str, Any]) -> None:
        """Migrate old pet data to new format"""
        # Ensure all required fields exist
        defaults = {
            'total_wins': 0,
            'total_losses': 0,
            'total_mission_energon': 0,
            'total_battle_energon': 0,
            'total_training_energon': 0,
            'missions_completed': 0,
            'missions_failed': 0,
            'battles_won': 0,
            'battles_lost': 0,
            'mission_xp_earned': 0,
            'battle_xp_earned': 0,
            'training_xp_earned': 0,
            'search_xp_earned': 0,
            'charge_xp_earned': 0,
            'play_xp_earned': 0,
            'repair_xp_earned': 0
        }
        
        for key, default_value in defaults.items():
            if key not in pet:
                pet[key] = default_value

    async def battle_pet(self, user_id: int, opponent_id: int) -> Tuple[bool, str, Dict[str, Any]]:
        """Battle another player's pet using the battle system"""
        pet1 = await self.get_user_pet(user_id)
        pet2 = await self.get_user_pet(opponent_id)
        
        if not pet1:
            return False, "You don't have a pet!", {}
        if not pet2:
            return False, "Opponent doesn't have a pet!", {}
        if user_id == opponent_id:
            return False, "You can't battle yourself!", {}
        
        # Check energy
        energy_cost = 20
        if pet1['energy'] < energy_cost:
            return False, f"Not enough energy! Need {energy_cost}⚡", {}
        
        pet1['energy'] -= energy_cost
        await self._queue_save(user_id, pet1)
        
        # Use battle system for PvP combat
        try:
            from .PetBattles.pvp_system import PvPBattleView, BattleMode
            
            # Create PvP battle
            participants = [user_id, opponent_id]
            battle_view = PvPBattleView(self.bot, participants, BattleMode.ONE_VS_ONE)
            
            # Start the battle and get result
            battle_result = await battle_view.start_battle()
            
            if battle_result['success']:
                winner = battle_result['winner']
                xp_gain = battle_result.get('xp_gain', 0)
                energon_gain = battle_result.get('energon_gain', 0)
                
                # Update pet stats based on result
                if winner == user_id:
                    pet1['battles_won'] = pet1.get('battles_won', 0) + 1
                    pet1['total_battle_energon'] = pet1.get('total_battle_energon', 0) + energon_gain
                    result = "win"
                    message = f"Victory! You defeated {pet2['name']}! (+{energon_gain}💰, +{xp_gain}XP)"
                else:
                    pet1['battles_lost'] = pet1.get('battles_lost', 0) + 1
                    result = "loss"
                    message = f"Defeat! {pet2['name']} was too strong! (+{xp_gain}XP)"
                
                # Update user's main energon balance for battle win
                if energon_gain > 0:
                    try:
                        await user_data_manager.add_energon(str(user_id), energon_gain)
                        await user_data_manager.update_energon_stat(str(user_id), "pet_energon_earned", energon_gain)
                    except Exception as e:
                        logger.error(f"Error updating user energon for battle win: {e}")
                
                # Add experience
                leveled_up, level_gains = await self.add_experience(user_id, xp_gain, "battle")
                
                # Return detailed battle result
                detailed_result = {
                    'winner': winner,
                    'pet1_name': pet1['name'],
                    'pet2_name': pet2['name'],
                    'result': result,
                    'energon_gain': energon_gain,
                    'xp_gain': xp_gain,
                    'battle_log': battle_result.get('battle_log', []),
                    'turns': battle_result.get('turns', 0)
                }
                
                return True, message, detailed_result
            else:
                return False, "Battle failed to start", {}
                
        except ImportError:
            logger.error("PvP battle system not available, falling back to simple comparison")
            return await self._simple_battle_pet(user_id, opponent_id, pet1, pet2)
        except Exception as e:
             logger.error(f"Error in battle_pet: {e}")
             return False, "Battle system error occurred", {}
    
    async def _simple_battle_pet(self, user_id: int, opponent_id: int, pet1: Dict, pet2: Dict) -> Tuple[bool, str, Dict[str, Any]]:
        """Simple fallback battle method when battle system is unavailable"""
        # Calculate stats with equipment
        stats1 = await self.get_equipment_stats(user_id)
        stats2 = await self.get_equipment_stats(opponent_id)
        
        attack1 = pet1['attack'] + stats1.get('attack', 0)
        defense1 = pet1['defense'] + stats1.get('defense', 0)
        attack2 = pet2['attack'] + stats2.get('attack', 0)
        defense2 = pet2['defense'] + stats2.get('defense', 0)
        
        # Calculate power levels
        power1 = attack1 + defense1
        power2 = attack2 + defense2
        
        # Battle outcome
        energon_gain = 0
        xp_gain = 0
        if power1 > power2:
            winner = user_id
            energon_gain = random.randint(20, 50)
            xp_gain = random.randint(10, 25)
            pet1['battles_won'] = pet1.get('battles_won', 0) + 1
            pet1['total_battle_energon'] = pet1.get('total_battle_energon', 0) + energon_gain
            result = "win"
            message = f"Victory! You defeated {pet2['name']}! (+{energon_gain}💰, +{xp_gain}XP)"
            
            # Update user's main energon balance for battle win
            try:
                await user_data_manager.add_energon(str(user_id), energon_gain)
                await user_data_manager.update_energon_stat(str(user_id), "pet_energon_earned", energon_gain)
            except Exception as e:
                logger.error(f"Error updating user energon for battle win: {e}")
        else:
            winner = opponent_id
            xp_gain = random.randint(5, 15)
            pet1['battles_lost'] = pet1.get('battles_lost', 0) + 1
            result = "loss"
            message = f"Defeat! {pet2['name']} was too strong! (+{xp_gain}XP)"
        
        leveled_up, level_gains = await self.add_experience(user_id, xp_gain, "battle")
        
        await self._queue_save(user_id, pet1)
        await self._queue_save(opponent_id, pet2)
        
        battle_result = {
            'winner': winner,
            'pet1_name': pet1['name'],
            'pet2_name': pet2['name'],
            'power1': power1,
            'power2': power2,
            'result': result,
            'energon_gain': energon_gain if result == "win" else 0,
            'xp_gain': xp_gain
        }
        
        return True, message, battle_result
  
    async def _save_worker(self) -> None:
        """Background worker for batched saves"""
        while not self._shutdown:
            try:
                batch = []
                try:
                    # Wait for first item with timeout
                    item = await asyncio.wait_for(self._pending_saves.get(), timeout=5.0)
                    batch.append(item)
                    
                    # Get any other pending saves
                    while not self._pending_saves.empty() and len(batch) < 10:
                        batch.append(self._pending_saves.get_nowait())
                    
                    # Process batch
                    if batch:
                        await self._process_save_batch(batch)
                except asyncio.TimeoutError:
                    continue
            except Exception as e:
                logger.error(f"Error in save worker: {e}")
                await asyncio.sleep(1)
    
    async def _process_save_batch(self, batch: List[Tuple[int, Dict]]) -> None:
        """Process a batch of save operations"""
        updates = {}
        for user_id, pet_data in batch:
            updates[str(user_id)] = pet_data
        
        save_tasks = [
            user_data_manager.save_pet_data(uid, uid, data)
            for uid, data in updates.items()
        ]
        
        await asyncio.gather(*save_tasks, return_exceptions=True)
    
    async def _queue_save(self, user_id: int, pet_data: Dict[str, Any]) -> None:
        """Queue a save operation"""
        await self._pending_saves.put((user_id, pet_data))
    
    async def get_user_pet(self, user_id: int, *, force_refresh: bool = False, username: str = None) -> Optional[Dict[str, Any]]:
        """Get user's pet with caching and background refresh"""
        cache_key = str(user_id)
        current_time = time.time()
        
        # Check cache first
        if not force_refresh and cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if current_time - timestamp < 300:  # 5 minute cache
                return cached_data
        
        # Cache miss or forced refresh
        try:
            pet_data = await user_data_manager.get_pet_data(cache_key, username)
            if pet_data:
                # Schedule cache update without waiting
                asyncio.create_task(self._update_cache(cache_key, pet_data))
                return pet_data
            return None
        except Exception as e:
            logger.error(f"Error getting pet data for {user_id}: {e}")
            return None
    
    async def _update_cache(self, user_id: str, pet_data: Dict[str, Any]) -> None:
        """Update cache with new pet data"""
        async with self._cache_lock:
            self._cache[user_id] = (pet_data, time.time())

    async def get_equipment_stats(self, user_id: int) -> Dict[str, int]:
        """Calculate total equipment stats for a user's pet"""
        pet = await self.get_user_pet(user_id)
        if not pet:
            return {'attack': 0, 'defense': 0, 'energy': 0, 'maintenance': 0, 'happiness': 0}
        
        equipment = pet.get('equipment', {})
        total_stats = {'attack': 0, 'defense': 0, 'energy': 0, 'maintenance': 0, 'happiness': 0}
        
        for slot, item in equipment.items():
            if item and isinstance(item, dict):
                stat_bonus = item.get('stat_bonus', {})
                for stat, value in stat_bonus.items():
                    if stat in total_stats:
                        total_stats[stat] += value
                    elif stat == 'max_energy':
                        total_stats['energy'] += value
                    elif stat == 'max_maintenance':
                        total_stats['maintenance'] += value
                    elif stat == 'max_happiness':
                        total_stats['happiness'] += value
        
        return total_stats

    def get_stage_emoji(self, level: int) -> str:
        """Get emoji for pet stage based on level"""
        return get_stage_emoji(level)

    async def shutdown(self) -> None:
        """Clean up resources"""
        self._shutdown = True
        if self._save_task:
            self._save_task.cancel()
            try:
                await self._save_task
            except asyncio.CancelledError:
                pass
        
        # Process any remaining saves
        if not self._pending_saves.empty():
            batch = []
            while not self._pending_saves.empty():
                batch.append(self._pending_saves.get_nowait())
            await self._process_save_batch(batch)

# Setup function for bot integration
async def setup(bot_instance: commands.Bot) -> None:
    """Setup function to integrate pets system with the bot"""
    try:
        # Initialize the pet system
        pet_system = PetSystem(bot_instance)
        
        # Load initial data
        await load_level_data()
        await pet_system._preload_data()
        
        # Store the pet system instance in the bot
        bot_instance.pet_system = pet_system
        
        print("✅ Pets system initialized successfully")
        
    except Exception as e:
        print(f"❌ Error initializing pets system: {e}")
        raise

__all__ = [
    'PetSystem',
    'PetStatusView',
    'setup'
]