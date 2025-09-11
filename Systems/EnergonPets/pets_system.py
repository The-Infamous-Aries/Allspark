import asyncio
import random
import sys
import os
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

import discord
from discord.ext import commands
from discord import app_commands

# Import the unified user data manager
from Systems.user_data_manager import user_data_manager

# Set up logging
logger = logging.getLogger('pets_system')

# Initialize empty globals - will be loaded from JSON
LEVEL_THRESHOLDS = {}
PET_STAGES = {}
STAGE_EMOJIS = {}
MISSION_TYPES = {}
MISSION_DIFFICULTIES = {}
AUTOBOT_PET_NAMES = []
DECEPTICON_PET_NAMES = []

MONSTER_EMOJIS = {
    "monster": "🤖",
    "boss": "👹",
    "titan": "👑"
}

MONSTER_TYPE_EMOJIS = {
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

# Load level progression data from JSON
async def load_level_data():
    """Load level progression data from pets_level.json"""
    try:
        data = await user_data_manager.get_pets_level_data()
        
        # Convert string keys to integers for LEVEL_THRESHOLDS and PET_STAGES
        global LEVEL_THRESHOLDS, PET_STAGES, STAGE_EMOJIS, AUTOBOT_PET_NAMES, DECEPTICON_PET_NAMES, MISSION_TYPES, MISSION_DIFFICULTIES
        LEVEL_THRESHOLDS = {int(k): v for k, v in data.get('LEVEL_THRESHOLDS', {}).items()}
        PET_STAGES = {int(k): v for k, v in data.get('PET_STAGES', {}).items()}
        STAGE_EMOJIS = data.get('STAGE_EMOJIS', {})
        AUTOBOT_PET_NAMES = data.get('AUTOBOT_PET_NAMES', [])
        DECEPTICON_PET_NAMES = data.get('DECEPTICON_PET_NAMES', [])
        MISSION_TYPES = data.get('MISSION_TYPES', {})
        MISSION_DIFFICULTIES = data.get('MISSION_DIFFICULTIES', {})
        
    except Exception as e:
        print(f"Error loading pets_level.json: {e}")
        raise RuntimeError("Failed to load pets_level.json - critical system file missing")


class PetStatusView(discord.ui.View):
    """Interactive view for pet status with Breakdown and Refresh buttons"""
    
    def __init__(self, user_id: int, pet_system, commands_cog, pet_data=None):
        super().__init__(timeout=300)  # 5 minute timeout
        self.user_id = user_id
        self.pet_system = pet_system
        self.commands_cog = commands_cog
        self.showing_breakdown = False
        self.pet_data = pet_data  # Store pet data to avoid re-loading
    
    async def create_main_embed(self) -> discord.Embed:
        """Create the main pet status embed"""
        if not self.pet_data:
            self.pet_data = await self.pet_system.get_user_pet(self.user_id)
        
        pet = self.pet_data
        if not pet:
            return discord.Embed(title="Error", description="Pet not found!", color=discord.Color.red())
        
        # Migrate old pet data
        await self.pet_system.migrate_pet_data(pet)
        
        stage = PET_STAGES[pet["level"]]
        
        # Set faction-based color
        faction = pet.get('faction', 'Unknown').lower()
        if faction == 'autobot':
            embed_color = 0xCC0000  # Red for Autobots
        elif faction == 'decepticon':
            embed_color = 0x800080  # Purple for Decepticons
        else:
            embed_color = 0x808080  # Gray for Unknown
            
        # Get faction-based emoji
        faction_emoji = "🔴" if faction == 'autobot' else "🟣" if faction == 'decepticon' else "⚡"
        
        # Get stage emoji
        try:
            stage_emoji = get_stage_emoji(pet['level'])
        except:
            stage_emoji = "🥚"
            
        embed = discord.Embed(
            title=f"{pet['name']} - {stage_emoji} LVL: {pet['level']} - {faction_emoji} {pet.get('faction', 'Unknown')}",
            color=embed_color
        )

        max_level = max(LEVEL_THRESHOLDS.keys())
        if pet['level'] < max_level:
            threshold = LEVEL_THRESHOLDS[pet['level']]
            progress = min(pet['experience'] / threshold, 1.0)
            bar_length = 10
            filled_length = int(bar_length * progress)
            
            # Determine faction color for progress bar
            filled_char = "🟥" if faction == 'autobot' else "🟪" if faction == 'decepticon' else "🟨"
            empty_char = "⬛"
            bar = filled_char * filled_length + empty_char * (bar_length - filled_length)
            embed.add_field(name="📊 Level Progress", value=f"{bar} {pet['experience']}/{threshold} XP", inline=False)

        # Show date in MM/DD/YY at HH:MM AM/PM format
        created = datetime.fromisoformat(pet["created_at"])
        age_text = created.strftime("%m/%d/%y at %I:%M %p")
        equipment_stats = await self.pet_system.get_equipment_stats(self.user_id)
        total_attack = pet['attack'] + equipment_stats['attack']
        total_defense = pet['defense'] + equipment_stats['defense']        

        embed.add_field(name="🗓️ Created", value=age_text, inline=True)
        embed.add_field(name="⚡ **Power**", value=f"⚔️ ATT: {total_attack} ({pet['attack']} base + {equipment_stats['attack']} equip) | 🛡️ DEF: {total_defense} ({pet['defense']} base + {equipment_stats['defense']} equip)", inline=False)

        # Show equipped items
        equipment = pet.get('equipment', {})
        equipped_items = []
        for slot, item in equipment.items():
            if item:
                stat_bonus = item.get('stat_bonus', {})
                stats_text = ""
                for stat, value in stat_bonus.items():
                    stats_text += f" +{value} {stat}"
                slot_name = slot.replace('_', ' ').title()
                equipped_items.append(f"**{slot_name}**: {item['name']}{stats_text}")
        
        if equipped_items:
            embed.add_field(name="🛡️ **Equipment**", value="\n".join(equipped_items), inline=False)    
    
        # Calculate total stats with equipment bonuses
        total_energy = pet['max_energy'] + equipment_stats['energy']
        total_maintenance = pet['max_maintenance'] + equipment_stats['maintenance']
        total_happiness = pet['max_happiness'] + equipment_stats['happiness']
        
        embed.add_field(name="🔋 **Energy**", value=f"{pet['energy']:.0f}/{total_energy:.0f}", inline=True)
        embed.add_field(name="🔧 **Maintenance**", value=f"{pet['maintenance']:.0f}/{total_maintenance:.0f}", inline=True)
        embed.add_field(name="😊 **Happiness**", value=f"{pet['happiness']:.0f}/{total_happiness:.0f}", inline=True)
        
        # Calculate totals
        detailed_stats = await self.get_pet_detailed_stats(self.user_id)
        
        embed.add_field(
            name="🏆 **Achievements**", 
            value=f"⚔️ **__Total Battle Wins__**: {detailed_stats['battles']['total']['wins']}\n"
                  f"💀 **__Total Battle Losses__**: {detailed_stats['battles']['total']['losses']}\n"
                  f"📋 **__Missions Completed__**: {pet.get('missions_completed', 0)}\n"
                  f"💰 **__Total Energon__**: {detailed_stats['energon']['total']:,}\n"
                  f"⭐ **__Total Experience__**: {detailed_stats['experience']['total']:,}", 
            inline=False
        )
        
        embed.set_footer(text="Use the buttons below for detailed stats or refresh")
        return embed
    
    async def create_breakdown_embed(self) -> discord.Embed:
        """Create the detailed breakdown embed"""
        detailed_stats = await self.get_pet_detailed_stats(self.user_id)
        if not detailed_stats:
            return discord.Embed(title="Error", description="Pet not found!", color=discord.Color.red())
        
        pet = detailed_stats['pet']
        faction = pet.get('faction', 'Unknown').lower()
        embed_color = 0xCC0000 if faction == 'autobot' else 0x800080 if faction == 'decepticon' else 0x808080
        
        try:
            stage_emoji = get_stage_emoji(pet['level'])
        except:
            stage_emoji = "🔩"
            
        embed = discord.Embed(
            title=f"📊 {pet['name']} - Detailed Breakdown",
            color=embed_color
        )
        
        # Experience Breakdown
        exp_breakdown = (
            f"🤹 **Total Experience**: {detailed_stats['experience']['total']:,} XP\n"
            f"🧭 **Mission XP**: {detailed_stats['experience']['mission']:,}\n"
            f"⚔️ **Battle XP**: {detailed_stats['experience']['battle']:,}\n"
            f"🥊 **Challenge XP**: {detailed_stats['experience']['challenge']:,}\n"
            f"🔍 **Search XP**: {detailed_stats['experience']['search']:,}\n"
            f"💪 **Training XP**: {detailed_stats['experience']['training']:,}\n"
            f"⚡ **Charge XP**: {detailed_stats['experience']['charge']:,}\n"
            f"🎮 **Play XP**: {detailed_stats['experience']['play']:,}\n"
            f"🔧 **Repair XP**: {detailed_stats['experience']['repair']:,}"
        )
        embed.add_field(name="⭐ **Experience Breakdown**", value=exp_breakdown, inline=False)
        
        # Energon Breakdown
        energon_breakdown = (
            f"💎 **Total Energon**: {detailed_stats['energon']['total']:,}\n"
            f"📋 **Mission Energon**: {detailed_stats['energon']['mission']:,}\n"
            f"🏋️ **Training Energon**: {detailed_stats['energon']['training']:,}\n"
            f"⚔️ **Battle Energon**: {detailed_stats['energon']['battle']:,}\n"
            f"🥊 **Challenge Energon**: {detailed_stats['energon']['challenge']:,}"
        )
        embed.add_field(name="💰 **Energon Breakdown**", value=energon_breakdown, inline=False)
        
        # Battle Stats Breakdown
        battles = detailed_stats['battles']
        total_battles = battles['total']['wins'] + battles['total']['losses']
        win_rate = (battles['total']['wins'] / max(total_battles, 1)) * 100
        
        battle_breakdown = (
            f"🤼 **Total Battles**: {total_battles} (W/L: {battles['total']['wins']}/{battles['total']['losses']})\n"
            f"🥋 **Win Rate**: {win_rate:.1f}%\n\n"
            f"😈 **Solo Battles**: {battles['solo']['wins']}W / {battles['solo']['losses']}L\n"
            f"🤖 **Group Battles**: {battles['group']['wins']}W / {battles['group']['losses']}L\n"
            f"🤺 **PvP Challenges**: {battles['challenge']['wins']}W / {battles['challenge']['losses']}L\n"
            f"🏟️ **Open Challenges**: {battles['open_challenge']['wins']}W / {battles['open_challenge']['losses']}L"
        )
        embed.add_field(name="⚔️ **Battle Statistics**", value=battle_breakdown, inline=False)
        
        embed.set_footer(text="Click 'Main Stats' to return to the overview")
        return embed
    
    async def get_pet_detailed_stats(self, user_id):
        """Get detailed stats for a pet including breakdown by category"""
        if not self.pet_data:
            self.pet_data = await self.pet_system.get_user_pet(user_id)
        
        pet = self.pet_data
        if not pet:
            return False, "No pet found", None
        
        # Migrate old pet data
        await self.pet_system.migrate_pet_data(pet)
        
        # Calculate totals by category
        total_energon = {
            'mission': pet.get('total_mission_energon', 0),
            'training': pet.get('total_training_energon', 0),
            'battle': pet.get('total_battle_energon', 0),
            'challenge': pet.get('total_challenge_energon', 0),
            'total': 0
        }
        total_energon['total'] = sum([total_energon['mission'], total_energon['training'], 
                                     total_energon['battle'], total_energon['challenge']])
        
        total_experience = {
            'mission': pet.get('mission_xp_earned', 0),
            'battle': pet.get('battle_xp_earned', 0),
            'challenge': pet.get('challenge_xp_earned', 0),
            'search': pet.get('search_xp_earned', 0),
            'charge': pet.get('charge_xp_earned', 0),
            'play': pet.get('play_xp_earned', 0),
            'repair': pet.get('repair_xp_earned', 0),
            'training': pet.get('training_xp_earned', 0),
            'total': 0
        }
        total_experience['total'] = sum([total_experience['mission'], total_experience['battle'],
                                        total_experience['challenge'], total_experience['search'],
                                        total_experience['charge'], total_experience['play'],
                                        total_experience['repair'], total_experience['training']])
        
        battle_stats = {
            'solo': {
                'wins': pet.get('battles_won', 0),
                'losses': pet.get('battles_lost', 0)
            },
            'group': {
                'wins': pet.get('group_battles_won', 0),
                'losses': pet.get('group_battles_lost', 0)
            },
            'challenge': {
                'wins': pet.get('challenge_wins', 0),
                'losses': pet.get('challenge_losses', 0)
            },
            'open_challenge': {
                'wins': pet.get('open_challenge_wins', 0),
                'losses': pet.get('open_challenge_losses', 0)
            },
            'total': {'wins': 0, 'losses': 0}
        }
        battle_stats['total']['wins'] = sum([battle_stats['solo']['wins'], battle_stats['group']['wins'],
                                           battle_stats['challenge']['wins'], battle_stats['open_challenge']['wins']])
        battle_stats['total']['losses'] = sum([battle_stats['solo']['losses'], battle_stats['group']['losses'],
                                             battle_stats['challenge']['losses'], battle_stats['open_challenge']['losses']])
        
        return {
            'pet': pet,
            'energon': total_energon,
            'experience': total_experience,
            'battles': battle_stats
        }

    @discord.ui.button(label="📋 Overview", style=discord.ButtonStyle.gray, disabled=True)
    async def main_stats_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Return to main stats view"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your pet status!", ephemeral=True)
            return
            
        self.showing_breakdown = False
        
        # Update button states
        self.breakdown_button.disabled = False
        self.refresh_button.disabled = False
        self.main_stats_button.disabled = True
        
        embed = await self.create_main_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="📊 Breakdown", style=discord.ButtonStyle.blurple)
    async def breakdown_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show detailed breakdown"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your pet status!", ephemeral=True)
            return
            
        self.showing_breakdown = True
        
        # Update button states
        self.breakdown_button.disabled = True
        self.refresh_button.disabled = False
        self.main_stats_button.disabled = False
        
        embed = await self.create_breakdown_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="🔄", style=discord.ButtonStyle.green)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Refresh the embed with current data"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your pet status!", ephemeral=True)
            return
            
        # Refresh data by fetching fresh pet data
        self.pet_data = await self.pet_system.get_user_pet(self.user_id)
        
        if not self.pet_data:
            await interaction.response.send_message("❌ Pet data not found!", ephemeral=True)
            return
            
        if self.showing_breakdown:
            embed = await self.create_breakdown_embed()
        else:
            embed = await self.create_main_embed()
            
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_timeout(self):
        """Disable all buttons when view times out"""
        for child in self.children:
            child.disabled = True
        if hasattr(self, 'message') and self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass


class PetEquipmentView(discord.ui.View):
    """Interactive view for displaying all pet items with pagination"""
    
    def __init__(self, user_id: int, pet_system, items: List[Dict[str, Any]]):
        super().__init__(timeout=300)  # 5 minute timeout
        self.user_id = user_id
        self.pet_system = pet_system
        self.items = items
        self.current_page = 0
        self.items_per_page = 10
        self.total_pages = max(1, (len(items) + self.items_per_page - 1) // self.items_per_page)
        
        # Only show navigation buttons if there are multiple pages
        if self.total_pages <= 1:
            self.clear_items()
        else:
            self.update_buttons()
    
    def get_rarity_emoji(self, rarity: str) -> str:
        """Get emoji for item rarity"""
        rarity_emojis = {
            "common": "⚪",
            "uncommon": "🟢", 
            "rare": "🔵",
            "epic": "🟣", 
            "legendary": "🟠",
            "mythic": "🔴"
        }
        return rarity_emojis.get(rarity.lower(), "⚪")
    
    def get_type_emoji(self, item_type: str) -> str:
        """Get emoji for item type"""
        type_emojis = {
            "chassis_plating": "🛡️",
            "energy_cores": "⚡",
            "utility_modules": "🔧"
        }
        return type_emojis.get(item_type.lower(), "📦")
    
    def format_stat_bonus(self, stat_bonus: Dict[str, int]) -> str:
        """Format stat bonus text"""
        if not stat_bonus:
            return ""
        
        stat_emojis = {
            "attack": "⚔️",
            "defense": "🛡️",
            "energy": "⚡",
            "maintenance": "🔧",
            "happiness": "😊"
        }
        
        parts = []
        for stat, value in stat_bonus.items():
            emoji = stat_emojis.get(stat, "📊")
            parts.append(f"{emoji} +{value}")
        
        return " | ".join(parts)
    
    async def create_embed(self, page: int) -> discord.Embed:
        """Create embed for current page"""
        start_idx = page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.items))
        page_items = self.items[start_idx:end_idx]
        
        # Get pet info for color scheme
        pet = await self.pet_system.get_user_pet(self.user_id)
        if pet:
            faction = pet.get('faction', 'Unknown').lower()
            color = 0xCC0000 if faction == 'autobot' else 0x800080 if faction == 'decepticon' else 0x00AE86
            pet_name = pet.get('name', 'Your Pet')
        else:
            color = 0x00AE86
            pet_name = 'Your Pet'
        
        embed = discord.Embed(
            title=f"🎒 {pet_name}'s Equipment Collection",
            description=f"Showing items {start_idx + 1}-{end_idx} of {len(self.items)} total items",
            color=color
        )
        
        if not page_items:
            embed.add_field(
                name="📭 No Items Found",
                value="You don't have any pet equipment items yet! Obtain items through missions, battles, and other activities.",
                inline=False
            )
        else:
            for item in page_items:
                rarity = item.get('rarity', 'common').lower()
                item_type = item.get('type', 'unknown')
                name = item.get('name', 'Unknown Item')
                description = item.get('description', 'No description available')
                stat_bonus = item.get('stat_bonus', {})
                
                rarity_emoji = self.get_rarity_emoji(rarity)
                type_emoji = self.get_type_emoji(item_type)
                stat_text = self.format_stat_bonus(stat_bonus)
                
                embed.add_field(
                    name=f"{rarity_emoji} {type_emoji} {name}",
                    value=f"*{description}*\n{stat_text}",
                    inline=False
                )
        
        if self.total_pages > 1:
            embed.set_footer(text=f"Page {page + 1} of {self.total_pages} • Use buttons to navigate")
        else:
            embed.set_footer(text="All your pet equipment items")
        
        return embed
    
    def update_buttons(self):
        """Update button states based on current page"""
        self.previous_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page >= self.total_pages - 1)
    
    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.blurple)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to previous page"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your equipment collection!", ephemeral=True)
            return
        
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = await self.create_embed(self.current_page)
            await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.blurple)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to next page"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your equipment collection!", ephemeral=True)
            return
        
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            embed = await self.create_embed(self.current_page)
            await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_timeout(self):
        """Disable all buttons when view times out"""
        for child in self.children:
            child.disabled = True
        if hasattr(self, 'message') and self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass

class PetSystem:
    """Main pet system class managing all pet-related functionality"""
    
    def __init__(self, bot):
        self.bot = bot
        self.monsters_data = {}
        self.transformation_items = {}
        self.bosses_data = {}
        self.titans_data = {}
        
        # Pet data is now managed through UserDataManager
        # No need for separate JSON file storage
        
        # Flags to track lazy loading
        self._monsters_loaded = False
        self._items_loaded = False
    
    async def load_cyberchronicles_monsters(self) -> None:
        """Load monsters, bosses, and titans from JSON file using user_data_manager"""
        try:
            data = await user_data_manager.get_monsters_and_bosses_data()
            
            # Reset data structures
            self.monsters_data = {}
            self.bosses_data = {}
            self.titans_data = {}
            
            # Load monsters by type and rarity (new structure)
            if 'monsters' in data:
                monsters_json = data['monsters']
                
                # Handle new structure where monsters are organized by rarity
                if isinstance(monsters_json, dict):
                    for rarity, monster_list in monsters_json.items():
                        if isinstance(monster_list, list):
                            for monster in monster_list:
                                monster_type = monster.get('type', 'monster')
                                if monster_type == 'monster':
                                    self._add_to_collection(self.monsters_data, rarity.lower(), monster)
                                elif monster_type == 'boss':
                                    self._add_to_collection(self.bosses_data, rarity.lower(), monster)
                                elif monster_type == 'titan':
                                    self._add_to_collection(self.titans_data, rarity.lower(), monster)
            
            # Check for direct boss and titan structures
            if 'bosses' in data:
                bosses_json = data['bosses']
                if isinstance(bosses_json, dict):
                    for rarity, boss_list in bosses_json.items():
                        if isinstance(boss_list, list):
                            for boss in boss_list:
                                self._add_to_collection(self.bosses_data, rarity.lower(), boss)
            
            if 'titans' in data:
                titans_json = data['titans']
                if isinstance(titans_json, dict):
                    for rarity, titan_list in titans_json.items():
                        if isinstance(titan_list, list):
                            for titan in titan_list:
                                self._add_to_collection(self.titans_data, rarity.lower(), titan)
            
            # Log loading results
            total_monsters = sum(len(monsters) for monsters in self.monsters_data.values())
            total_bosses = sum(len(bosses) for bosses in self.bosses_data.values())
            total_titans = sum(len(titans) for titans in self.titans_data.values())
            print(f"Loaded: {total_monsters} monsters, {total_bosses} bosses, {total_titans} titans")
            self._monsters_loaded = True
        except Exception as e:
            print(f"Error loading monsters: {e}")
            self.monsters_data = {}
            self.bosses_data = {}
            self.titans_data = {}
    
    async def load_transformation_items(self) -> None:
        """Load transformation items from JSON file using user_data_manager"""
        try:
            data = await user_data_manager.get_transformation_items_data()
            
            # Handle new structure with items_by_class
            if 'items_by_class' in data:
                self.transformation_items = data['items_by_class']
            else:
                # Fallback to old structure
                self.transformation_items = data
            
            # Count items across all classes and rarities
            total_items = 0
            for class_name, rarity_dict in self.transformation_items.items():
                if isinstance(rarity_dict, dict):
                    for rarity, items in rarity_dict.items():
                        if isinstance(items, dict):
                            total_items += len(items)
            
            print(f"Loaded: {total_items} transformation items across all classes")
            self._items_loaded = True
        except Exception as e:
            print(f"Error loading transformation items: {e}")
            self.transformation_items = {}

    async def create_pet(self, user_id: int, faction: str) -> Dict[str, Any]:
        """Create a new pet for a user"""
        # Select appropriate name list based on faction
        name_list = AUTOBOT_PET_NAMES if faction.lower() == 'autobot' else DECEPTICON_PET_NAMES
        pet_name = random.choice(name_list)
        
        # Initialize pet data with faction-based starting stats
        faction_lower = faction.lower()
        if faction_lower == 'autobot':
            attack = 10
            defense = 12
            happiness = 200
            energy = 100
        else:  # Decepticon
            attack = 12
            defense = 10
            energy = 200
            happiness = 100
            
        pet_data = {
            "name": pet_name,
            "faction": faction.capitalize(),
            "level": 1,
            "experience": 0,
            "energy": energy,
            "max_energy": 200 if faction_lower == 'decepticon' else 100,
            "maintenance": 150,
            "max_maintenance": 150,
            "happiness": happiness,
            "max_happiness": 200 if faction_lower == 'autobot' else 100,
            "attack": attack,
            "defense": defense,
            "battles_won": 0,
            "battles_lost": 0,
            "group_battles_won": 0,
            "group_battles_lost": 0,
            "challenge_wins": 0,
            "challenge_losses": 0,
            "open_challenge_wins": 0,
            "open_challenge_losses": 0,
            "battle_xp_earned": 0,
            "missions_completed": 0,
            "total_mission_energon": 0,
            "total_training_energon": 0,
            "total_battle_energon": 0,
            "total_challenge_energon": 0,
            "mission_xp_earned": 0,
            "challenge_xp_earned": 0,
            "battle_xp_earned": 0,
            "search_xp_earned": 0,
            "charge_xp_earned": 0,
            "play_xp_earned": 0,
            "repair_xp_earned": 0,
            "created_at": datetime.now().isoformat(),
            "equipment": {
                "chassis_plating": None,
                "energy_cores": None,
                "utility_modules": None
            },
            "inventory": []
        }
        
        # Save pet data using UserDataManager
        await user_data_manager.save_pet_data(str(user_id), str(user_id), pet_data)
        return pet_data
    
    async def get_user_pet(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get a user's pet data"""
        pet_data = await user_data_manager.get_pet_data(str(user_id))
        
        if pet_data:
            print(f"Found pet for user {user_id}: {pet_data.get('name', 'Unknown')}")
        else:
            print(f"No pet found for user {user_id}")
        
        return pet_data

    def get_random_monster(self, difficulty: str, opponent_type: str = "monster") -> Optional[Dict[str, Any]]:
        """Get a random monster based on difficulty and type"""
        try:
            # Ensure data is loaded
            if not self._monsters_loaded:
                self.load_cyberchronicles_monsters()
            
            difficulty_config = BATTLE_DIFFICULTY_MAP[difficulty]
            rarities = difficulty_config["rarities"]
            weights = difficulty_config["rarity_weights"]
            
            # Select rarity based on weights
            selected_rarity = random.choices(rarities, weights=[weights[r] for r in rarities])[0]
            
            # Get appropriate collection
            if opponent_type == "monster":
                collection = self.monsters_data
            elif opponent_type == "boss":
                collection = self.bosses_data
            elif opponent_type == "titan":
                collection = self.titans_data
            else:
                return None
            
            # For bosses and titans, filter by type from monsters_data if collection is empty
            if opponent_type in ["boss", "titan"] and (not collection or selected_rarity not in collection or not collection[selected_rarity]):
                # Filter monsters by type and rarity
                if selected_rarity in self.monsters_data:
                    filtered_monsters = [m for m in self.monsters_data[selected_rarity] if m.get('type') == opponent_type]
                    if filtered_monsters:
                        monster = random.choice(filtered_monsters)
                    else:
                        return None
                else:
                    return None
            else:
                # Use the appropriate collection
                if selected_rarity in collection and collection[selected_rarity]:
                    monster = random.choice(collection[selected_rarity])
                else:
                    return None
            
            # Scale monster stats based on difficulty
            health_multiplier = {"easy": 1.0, "average": 1.5, "hard": 2.0, "boss": 3.0}
            attack_multiplier = {"easy": 1.0, "average": 1.2, "hard": 1.5, "boss": 2.0}
            
            monster["health"] = int(monster.get("health", 50) * health_multiplier.get(difficulty, 1.0))
            monster["attack"] = int(monster.get("attack", 10) * attack_multiplier.get(difficulty, 1.0))
            monster["defense"] = int(monster.get("defense", 5) * attack_multiplier.get(difficulty, 1.0))
            
            return monster
                
        except Exception as e:
            print(f"Error getting random monster: {e}")
        
        return None
    
    def get_random_transformation_item(self, rarity: str = None) -> Optional[Dict[str, Any]]:
        """Get a random transformation item from the specified rarity with type-based selection"""
        # Ensure data is loaded
        if not self._items_loaded:
            self.load_transformation_items()
        
        if not self.transformation_items or not rarity:
            return None
        
        # Collect items by type from the specified rarity
        weapon_armor_items = []
        transformation_beast_items = []
        
        for class_name, class_data in self.transformation_items.items():
            if isinstance(class_data, dict) and rarity in class_data:
                items = class_data[rarity]
                if isinstance(items, dict):
                    for item in items.values():
                        # Ensure item has type field
                        if "type" not in item:
                            item_type = class_name
                            if "Beast" in class_name:
                                item_type = "Beast Mode"
                            elif "Transformation" in class_name:
                                item_type = "Transformation"
                            elif "Weapon" in class_name:
                                item_type = "Weapon"
                            elif "Armor" in class_name:
                                item_type = "Armor"
                            else:
                                item_type = "Transformation"
                            item["type"] = item_type
                        
                        # Categorize items by type
                        if item["type"] in ["Weapon", "Armor"]:
                            weapon_armor_items.append(item)
                        elif item["type"] in ["Transformation", "Beast Mode"]:
                            transformation_beast_items.append(item)
        
        # Determine which category to select from
        category_roll = random.random()
        selected_items = []
        
        if category_roll < 0.30:  # 30% chance for Weapons/Armor
            selected_items = weapon_armor_items
        elif category_roll < 0.50:  # 20% chance for Transformations/Beast Modes
            selected_items = transformation_beast_items
        else:  # 50% chance for no loot (will return None)
            return None
        
        if not selected_items:
            return None
        
        # Random selection from the chosen category
        return random.choice(selected_items)
    
    async def charge_pet(self, user_id: int, duration: str = "15min") -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Charge a pet's energy with duration-based scaling"""
        DURATION_CONFIG = {
            "15min": {"multiplier": 1.0, "xp_base": (5,10), "energy_percent": 33},
            "30min": {"multiplier": 2.5, "xp_base": (10,25), "energy_percent": 50},
            "1hour": {"multiplier": 6.0, "xp_base": (25,50), "energy_percent": 100}
        }
        
        pet = await self.get_user_pet(user_id)
        if not pet:
            return False, "No pet found", None
        
        if duration not in DURATION_CONFIG:
            return False, "Invalid duration! Choose: 15min, 30min, 1hour", None
        
        # Check cooldown
        can_charge, remaining = self.check_cooldown(pet, "charge", duration)
        if not can_charge:
            return False, f"{pet['name']} is still charging! Cooldown: {remaining}", None
        
        config = DURATION_CONFIG[duration]
        
        total_max_stats = await self.get_total_max_stats(user_id)
        max_energy = total_max_stats["energy"]
        
        if pet['energy'] >= max_energy:
            return False, f"{pet['name']} is already fully charged!", None
        
        # Calculate energy gain based on duration and pet's max energy
        base_energy = int(max_energy * (config["energy_percent"] / 100))
        energy_gain = int(base_energy * config["multiplier"])
        new_energy = min(max_energy, pet['energy'] + energy_gain)
        actual_gain = new_energy - pet['energy']
        pet['energy'] = new_energy
        
        # Award scaled XP for charging
        xp_base = random.randint(*config["xp_base"])
        xp_gain = int(xp_base * config["multiplier"])
        leveled_up, level_gains = await self.add_experience(user_id, xp_gain, "charge")
        pet["charge_xp_earned"] = pet.get("charge_xp_earned", 0) + xp_gain
        
        # Set cooldown
        self.set_cooldown(pet, "charge", duration)
        
        await user_data_manager.save_pet_data(str(user_id), str(user_id), pet)
        
        duration_emoji = {"15min": "🪫", "30min": "🔋", "1hour": "🏭"}
        message = f"{duration_emoji[duration]} Charged {pet['name']} for {duration} - gained {actual_gain}⚡ energy and {xp_gain} XP!"
        
        return True, message, level_gains if leveled_up else None
    
    async def play_with_pet(self, user_id: int, duration: str = "15min") -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Play with pet to increase happiness with duration-based scaling"""
        DURATION_CONFIG = {
            "15min": {"multiplier": 1.0, "xp_base": (5,10), "happiness_percent": 33},
            "30min": {"multiplier": 2.5, "xp_base": (10,25), "happiness_percent": 50},
            "1hour": {"multiplier": 6.0, "xp_base": (25,50), "happiness_percent": 100}
        }
        
        pet = await self.get_user_pet(user_id)
        if not pet:
            return False, "No pet found", None
        
        if duration not in DURATION_CONFIG:
            return False, "Invalid duration! Choose: 15min, 30min, 1hour", None
        
        # Check cooldown
        can_play, remaining = self.check_cooldown(pet, "play", duration)
        if not can_play:
            return False, f"{pet['name']} is still tired from playing! Cooldown: {remaining}", None
        
        config = DURATION_CONFIG[duration]
        
        total_max_stats = await self.get_total_max_stats(user_id)
        max_happiness = total_max_stats["happiness"]
        
        if pet['happiness'] >= max_happiness:
            return False, f"{pet['name']} is already maximally happy!", None
        
        # Calculate happiness gain based on duration and pet's max happiness
        base_happiness = int(max_happiness * (config["happiness_percent"] / 100))
        happiness_gain = int(base_happiness * config["multiplier"])
        new_happiness = min(max_happiness, pet['happiness'] + happiness_gain)
        actual_gain = new_happiness - pet['happiness']
        pet['happiness'] = new_happiness
        
        # Award scaled XP for playing
        xp_base = random.randint(*config["xp_base"])
        xp_gain = int(xp_base * config["multiplier"])
        leveled_up, level_gains = await self.add_experience(user_id, xp_gain, "play")
        pet["play_xp_earned"] = pet.get("play_xp_earned", 0) + xp_gain
        
        # Set cooldown
        self.set_cooldown(pet, "play", duration)
        
        await user_data_manager.save_pet_data(str(user_id), str(user_id), pet)
        
        duration_emoji = {"15min": "🎮", "30min": "🃏", "1hour": "🎳"}
        message = f"{duration_emoji[duration]} Played with {pet['name']} for {duration} - gained {actual_gain}😊 happiness and {xp_gain} XP!"
        
        return True, message, level_gains if leveled_up else None
    
    async def train_pet(self, user_id: int, difficulty: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Train pet with difficulty-based rewards and penalties"""
        TRAINING_CONFIG = {
            "average": {
                "energy_cost": 75,
                "happiness_penalty": 38,
                "xp_reward": (50, 100),
                "energon_reward": (50, 100),
                "stat_chance": 0.10, 
                "stat_gain": 1
            },
            "intense": {
                "energy_cost": 250,
                "happiness_penalty": 125,
                "xp_reward": (200, 300),
                "energon_reward": (200, 300),
                "stat_chance": 0.10, 
                "stat_gain": 2
            },
            "godmode": {
                "energy_cost": 500,
                "happiness_penalty": 250,
                "xp_reward": (400, 600),
                "energon_reward": (400,600),
                "stat_chance": 0.10, 
                "stat_gain": 3
            }
        }
        
        pet = await self.get_user_pet(user_id)
        if not pet:
            return False, "No pet found"
        
        difficulty = difficulty.lower()
        if difficulty not in TRAINING_CONFIG:
            return False, "Invalid difficulty! Choose: average, intense, godmode", None
        
        config = TRAINING_CONFIG[difficulty]
        
        if pet['energy'] < config["energy_cost"]:
            return False, f"{pet['name']} doesn't have enough energy! Needs {config['energy_cost']}, has {pet['energy']}", None
        
        if pet['happiness'] < config["happiness_penalty"]:
            return False, f"{pet['name']} is too unhappy to train at this intensity!", None
        
        # Apply energy cost and happiness penalty
        pet['energy'] -= config["energy_cost"]
        pet['happiness'] = max(0, pet['happiness'] - config["happiness_penalty"])
        
        # Award XP and Energon
        xp_gain = random.randint(*config["xp_reward"])
        energon_gain = random.randint(*config["energon_reward"])
        
        # Track total training energon earned
        pet["total_training_energon"] = pet.get("total_training_energon", 0) + energon_gain

        # Check for stat improvements
        att_gain = 0
        def_gain = 0
        stat_improved = False
        
        if random.random() < config["stat_chance"]:
            # 50/50 chance for attack or defense
            if random.random() < 0.5:
                att_gain = config["stat_gain"]
                pet['attack'] += att_gain
                stat_improved = True
            else:
                def_gain = config["stat_gain"]
                pet['defense'] += def_gain
                stat_improved = True
        
        # Award experience
        leveled_up, level_gains = await self.add_experience(user_id, xp_gain, "train")
        pet["training_xp_earned"] = pet.get("training_xp_earned", 0) + xp_gain
        
        # Add energon reward to global balance and check energon rush win condition
        try:
            # Use the global energon balance system
            user_energon = await user_data_manager.get_energon_data(str(user_id))
            
            # Check if user is in energon rush game
            is_in_energon_rush = user_energon.get("in_energon_rush", False)
            current_energon = user_energon.get("energon", 0)
            
            # Add energon gain
            user_energon["energon"] = current_energon + energon_gain
            new_total = user_energon["energon"]
            
            # Save updated energon data
            await user_data_manager.save_energon_data(str(user_id), user_energon)
            
            # Check energon rush win condition if in game
            if is_in_energon_rush and new_total >= 10000:
                # Import here to avoid circular imports
                try:
                    from Systems.EnergonPets.energon_system import game_manager
                    if game_manager:
                        # End the game and announce winner
                        user = self.bot.get_user(int(user_id))
                        if user:
                            # Find the channel where the game is active
                            # This is a simplified approach - in practice, you might need to track game channels
                            channel = None
                            await game_manager._end_game(None, user)
                except ImportError:
                    pass  # energon_system not available, skip win check
                    
        except Exception as e:
            print(f"Error updating energon for user {user_id}: {e}")
        
        await user_data_manager.save_pet_data(str(user_id), str(user_id), pet)
        
        # Build response message
        difficulty_emoji = {
            "average": "⚡",
            "intense": "🔥",
            "godmode": "⚡🔥💀"
        }
        
        message = f"{difficulty_emoji[difficulty]} **{difficulty.upper()}** training complete!\n"
        message += f"{pet['name']} used {config['energy_cost']} energy and lost {config['happiness_penalty']} happiness.\n"
        message += f"💫 Gained {xp_gain} XP and {energon_gain} Energon!\n"
        
        if stat_improved:
            if att_gain > 0:
                message += f"⚔️ **STAT BOOST!** +{att_gain} ATT!\n"
            elif def_gain > 0:
                message += f"🛡️ **STAT BOOST!** +{def_gain} DEF!\n"
        else:
            message += "No stat improvements this time.\n"
            
        if leveled_up:
            new_stage = PET_STAGES[pet["level"]]
            stage_emoji = self.get_stage_emoji(pet["level"])
            message += f"🎉 **LEVEL UP!** {pet['name']} is now a {stage_emoji} {new_stage['name']}!"
        
        return True, message, level_gains if leveled_up else None
    
    async def repair_pet(self, user_id: int, duration: str = "15min") -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Repair pet's maintenance with duration-based scaling"""
        DURATION_CONFIG = {
            "15min": {"multiplier": 1.0, "xp_base": (5, 10), "maintenance_percent": 33},
            "30min": {"multiplier": 2.5, "xp_base": (10, 25), "maintenance_percent": 50},
            "1hour": {"multiplier": 6.0, "xp_base": (25, 50), "maintenance_percent": 100}
        }
        
        pet = await self.get_user_pet(user_id)
        if not pet:
            return False, "No pet found", None
        
        if duration not in DURATION_CONFIG:
            return False, "Invalid duration! Choose: 15min, 30min, 1hour", None
        
        # Check cooldown
        can_repair, remaining = self.check_cooldown(pet, "repair", duration)
        if not can_repair:
            return False, f"{pet['name']} is still being repaired! Cooldown: {remaining}", None
        
        config = DURATION_CONFIG[duration]
        
        total_max_stats = await self.get_total_max_stats(user_id)
        max_maintenance = total_max_stats["maintenance"]
        
        if pet['maintenance'] >= max_maintenance:
            return False, f"{pet['name']} is already fully maintained!", None
        
        # Calculate maintenance gain based on duration and pet's max maintenance
        base_maintenance = int(max_maintenance * (config["maintenance_percent"] / 100))
        maintenance_gain = int(base_maintenance * config["multiplier"])
        new_maintenance = min(max_maintenance, pet['maintenance'] + maintenance_gain)
        actual_gain = new_maintenance - pet['maintenance']
        pet['maintenance'] = new_maintenance
        
        # Award scaled XP for repairing
        xp_base = random.randint(*config["xp_base"])
        xp_gain = int(xp_base * config["multiplier"])
        leveled_up, level_gains = await self.add_experience(user_id, xp_gain, "repair")
        pet["repair_xp_earned"] = pet.get("repair_xp_earned", 0) + xp_gain
        
        # Set cooldown
        self.set_cooldown(pet, "repair", duration)
        
        await user_data_manager.save_pet_data(str(user_id), str(user_id), pet)
        
        duration_emoji = {"15min": "⚙️", "30min": "🔨", "1hour": "🛠️"}
        message = f"{duration_emoji[duration]} Repaired {pet['name']} for {duration} - gained {actual_gain}🔧 maintenance and {xp_gain} XP!"
        
        return True, message, level_gains if leveled_up else None
    
    async def add_experience(self, user_id: int, amount: int, source: str = "general") -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Add experience to a pet and handle level ups"""
        pet = await user_data_manager.get_pet_data(str(user_id))
        if not pet:
            return False, None
        
        pet["experience"] += amount
        
        # Check for level up
        current_level = pet["level"]
        max_level = max(LEVEL_THRESHOLDS.keys())
        
        if current_level < max_level:
            threshold = LEVEL_THRESHOLDS.get(current_level, float('inf'))
            if pet["experience"] >= threshold:
                old_level = current_level
                pet["level"] += 1
                pet["experience"] = 0
                
                # Level up rewards: Faction-specific stat + 150 to one random stat
                
                # Faction-specific bonuses: Decepticons get +150 Energy, Autobots get +150 Happiness
                faction = pet.get('faction', '').upper()
                if faction == 'DECEPTICON':
                    att_gain = 3  # 3 attack points
                    def_gain = 0
                    energy_gain = 150  # 150 faction-determined energy points
                    happiness_gain = 0
                    maintenance_gain = 0
                elif faction == 'AUTOBOT':
                    att_gain = 0
                    def_gain = 3  # 3 defense points
                    energy_gain = 0
                    happiness_gain = 150  # 150 faction-determined happiness points
                    maintenance_gain = 0
                else:
                    att_gain = 3  # Default 3 attack points for no faction
                    def_gain = 0
                    energy_gain = 0
                    happiness_gain = 0
                    maintenance_gain = 0
                
                # Add 3 random points to either attack or defense
                random_points = 3
                random_att = random.randint(0, random_points)
                random_def = random_points - random_att
                
                att_gain += random_att
                def_gain += random_def

                # Add 150 to exactly one random stat (energy, maintenance, or happiness)
                resource_types = ['energy', 'maintenance', 'happiness']
                chosen_stat = random.choice(resource_types)
                
                if chosen_stat == 'energy':
                    energy_gain += 150
                elif chosen_stat == 'maintenance':
                    maintenance_gain += 150
                elif chosen_stat == 'happiness':
                    happiness_gain += 150
                
                pet["attack"] += att_gain
                pet["defense"] += def_gain
                
                pet['max_energy'] += energy_gain
                pet['max_maintenance'] += maintenance_gain
                pet['max_happiness'] += happiness_gain
                
                pet['energy'] = min(pet['energy'] + energy_gain, pet['max_energy'])
                pet['maintenance'] = min(pet['maintenance'] + maintenance_gain, pet['max_maintenance'])
                pet['happiness'] = min(pet['happiness'] + happiness_gain, pet['max_happiness'])
                
                await user_data_manager.save_pet_data(str(user_id), str(user_id), pet)
                return True, {
                    "old_level": old_level,
                    "new_level": pet["level"],
                    "att_gain": att_gain, "def_gain": def_gain,
                    "energy_gain": energy_gain,
                    "maintenance_gain": maintenance_gain,
                    "happiness_gain": happiness_gain
                }
        
        await user_data_manager.save_pet_data(str(user_id), str(user_id), pet)
        return False, None

    async def get_equipment_stats(self, user_id: int) -> Dict[str, int]:
        """Get total stats from equipped equipment"""
        pet = await self.get_user_pet(user_id)
        if not pet:
            return {"attack": 0, "defense": 0, "energy": 0, "maintenance": 0, "happiness": 0}
        
        total_stats = {"attack": 0, "defense": 0, "energy": 0, "maintenance": 0, "happiness": 0}
        equipment = pet.get("equipment", {})
        
        for slot, item in equipment.items():
            if item and isinstance(item, dict):
                stat_bonus = item.get("stat_bonus", {})
                for stat, value in stat_bonus.items():
                    if stat in total_stats:
                        total_stats[stat] += value
        
        return total_stats

    async def get_equipment_details(self, user_id: int) -> Dict[str, Any]:
        """Get detailed equipment information for a pet"""
        pet = await self.get_user_pet(user_id)
        if not pet:
            return None
        
        equipment = pet.get("equipment", {})
        inventory = pet.get("inventory", [])
        
        return {
            "equipment": equipment,
            "inventory": inventory,
            "total_stats": await self.get_equipment_stats(user_id)
        }

    async def get_total_max_stats(self, user_id: int) -> Dict[str, int]:
        """Get total max stats including equipment bonuses"""
        pet = await self.get_user_pet(user_id)
        if not pet:
            return {"energy": 100, "maintenance": 100, "happiness": 100}
        
        equipment_stats = await self.get_equipment_stats(user_id)
        
        return {
            "energy": pet.get('max_energy', 100) + equipment_stats.get('energy', 0),
            "maintenance": pet.get('max_maintenance', 100) + equipment_stats.get('maintenance', 0),
            "happiness": pet.get('max_happiness', 100) + equipment_stats.get('happiness', 0)
        }

    async def equip_item(self, user_id: int, item_id: str) -> Tuple[bool, str]:
        """Equip an item from inventory to a slot"""
        pet = await self.get_user_pet(user_id)
        if not pet:
            return False, "You don't have a pet yet!"
        
        inventory = pet.get("inventory", [])
        equipment = pet.get("equipment", {
            "chassis_plating": None,
            "energy_cores": None,
            "utility_modules": None
        })
        
        # Find item in inventory
        item_to_equip = None
        for item in inventory:
            if isinstance(item, dict) and item.get("id") == item_id:
                item_to_equip = item
                break
        
        if not item_to_equip:
            return False, f"Item '{item_id}' not found in your inventory!"
        
        item_type = item_to_equip.get("type")
        if item_type not in equipment:
            return False, f"Invalid equipment type: {item_type}"
        
        # Unequip current item if exists
        current_equipped = equipment[item_type]
        if current_equipped:
            inventory.append(current_equipped)
        
        # Equip new item
        equipment[item_type] = item_to_equip
        inventory.remove(item_to_equip)
        
        # Update pet data
        pet["equipment"] = equipment
        pet["inventory"] = inventory
        
        await user_data_manager.save_pet_data(str(user_id), str(user_id), pet)
        
        item_name = item_to_equip.get("name", "Unknown Item")
        stat_bonus = item_to_equip.get("stat_bonus", {})
        stat_text = ""
        for stat, value in stat_bonus.items():
            stat_text += f" +{value} {stat}"
        
        return True, f"Successfully equipped **{item_name}**!{stat_text}"

    async def unequip_item(self, user_id: int, slot: str) -> Tuple[bool, str]:
        """Unequip an item from a slot and add to inventory"""
        pet = await self.get_user_pet(user_id)
        if not pet:
            return False, "You don't have a pet yet!"
        
        equipment = pet.get("equipment", {})
        inventory = pet.get("inventory", [])
        
        if slot not in equipment:
            return False, f"Invalid equipment slot: {slot}"
        
        item = equipment[slot]
        if not item:
            return False, f"No item equipped in {slot} slot!"
        
        # Move item to inventory
        inventory.append(item)
        equipment[slot] = None
        
        # Update pet data
        pet["equipment"] = equipment
        pet["inventory"] = inventory
        
        await user_data_manager.save_pet_data(str(user_id), str(user_id), pet)
        
        item_name = item.get("name", "Unknown Item")
        return True, f"Successfully unequipped **{item_name}**!"

    async def get_equippable_items(self, user_id: int, slot: str = None) -> List[Dict[str, Any]]:
        """Get list of items that can be equipped from inventory"""
        pet = await self.get_user_pet(user_id)
        if not pet:
            return []
        
        inventory = pet.get("inventory", [])
        equippable = []
        
        for item in inventory:
            if isinstance(item, dict) and "type" in item:
                if slot is None or item["type"] == slot:
                    equippable.append(item)
        
        return equippable

    async def get_all_pet_items(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all pet items from user's inventory"""
        pet = await self.get_user_pet(user_id)
        if not pet:
            return []
        
        return pet.get("inventory", [])

    async def add_item_to_inventory(self, user_id: int, item: Dict[str, Any]) -> bool:
        """Add an equipment item to user's pet inventory"""
        pet = await self.get_user_pet(user_id)
        if not pet:
            return False
        
        if "inventory" not in pet:
            pet["inventory"] = []
        
        # Ensure item has required fields
        item_to_add = {
            "id": item.get("id"),
            "name": item.get("name"),
            "equipment_type": item.get("equipment_type"),
            "rarity": item.get("rarity"),
            "attack": item.get("attack", 0),
            "defense": item.get("defense", 0),
            "energy": item.get("energy", 0),
            "maintenance": item.get("maintenance", 0),
            "happiness": item.get("happiness", 0)
        }
        
        pet["inventory"].append(item_to_add)
        return await user_data_manager.save_pet_data(str(user_id), None, pet)

    async def create_level_up_embed(self, pet: Dict[str, Any], level_gains: Dict[str, Any], user_id: int = None) -> discord.Embed:
        """Create a level up embed for a pet"""
        old_level = level_gains["old_level"]
        new_level = level_gains["new_level"]
        
        old_stage = PET_STAGES[old_level]
        new_stage = PET_STAGES[new_level]
        
        old_emoji = self.get_stage_emoji(old_level)
        new_emoji = self.get_stage_emoji(new_level)
        
        embed = discord.Embed(
            title="🎉 Level Up!",
            description=f"**{pet['name']}** has leveled up!",
            color=0x00ff00
        )
        
        embed.add_field(
            name="Level Progression",
            value=f"{old_emoji} **Level {old_level}** → {new_emoji} **Level {new_level}**\n"
                  f"**{old_stage['name']}** → **{new_stage['name']}**",
            inline=False
        )
        
        embed.add_field(
            name="Stat Increases",
            value=f"⚔️ **Attack**: +{level_gains['att_gain']}\n"
                  f"🛡️ **Defense**: +{level_gains['def_gain']}\n"
                  f"⚡ **Max Energy**: +{level_gains['energy_gain']}\n"
                  f"🔧 **Max Maintenance**: +{level_gains['maintenance_gain']}\n"
                  f"😊 **Max Happiness**: +{level_gains['happiness_gain']}",
            inline=False
        )
        
        # Calculate total max stats including equipment
        equipment_stats = await self.get_equipment_stats(user_id)
        total_max_energy = pet['max_energy'] + equipment_stats.get('energy', 0)
        total_max_maintenance = pet['max_maintenance'] + equipment_stats.get('maintenance', 0)
        total_max_happiness = pet['max_happiness'] + equipment_stats.get('happiness', 0)
        
        embed.add_field(
            name="Current Stats",
            value=f"Level: **{new_level}**\n"
                  f"Attack: **{pet['attack']}**\n"
                  f"Defense: **{pet['defense']}**\n"
                  f"Energy: **{pet['energy']}/{total_max_energy}**\n"
                  f"Maintenance: **{pet['maintenance']}/{total_max_maintenance}**\n"
                  f"Happiness: **{pet['happiness']}/{total_max_happiness}**",
            inline=True
        )
        
        embed.set_thumbnail(url=pet.get('image_url', 'https://via.placeholder.com/100'))
        embed.set_footer(text=f"Congratulations on your pet's growth! 🌟")
        
        return embed

    async def send_level_up_embed(self, user_id: int, level_gains: Dict[str, Any], channel=None) -> None:
        """Send a level up embed to the user"""
        pet = await user_data_manager.get_pet_data(str(user_id))
        if not pet:
            return
            
        embed = await self.create_level_up_embed(pet, level_gains, user_id)
        
        try:
            # Try to get the user's DM channel or use provided channel
            if channel:
                await channel.send(embed=embed)
            else:
                user = await self.bot.fetch_user(user_id)
                if user:
                    await user.send(embed=embed)
        except discord.Forbidden:
            # User has DMs disabled, try to send in a guild channel if possible
            pass
        except Exception as e:
            print(f"Error sending level up embed: {e}")
    
    async def delete_pet(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Delete a user's pet permanently"""
        pet = await user_data_manager.get_pet_data(str(user_id))
        if pet:
            await user_data_manager.delete_pet_data(user_id)
            return pet
        return None
    
    def check_cooldown(self, pet: Dict[str, Any], action: str, duration: str) -> tuple[bool, str]:
        """Check if action is on cooldown and return remaining time"""
        cooldown_key = f"{action}_cooldown_{duration}"
        if cooldown_key not in pet:
            return True, ""
        
        cooldown_end = pet[cooldown_key]
        if cooldown_end <= time.time():
            return True, ""
        
        remaining = cooldown_end - time.time()
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        
        if minutes > 0:
            return False, f"{minutes}m {seconds}s"
        else:
            return False, f"{seconds}s"
    
    def set_cooldown(self, pet: Dict[str, Any], action: str, duration: str) -> None:
        """Set cooldown for an action based on duration"""
        DURATION_SECONDS = {
            "15min": 15 * 60,
            "30min": 30 * 60,
            "1hour": 60 * 60
        }
        
        cooldown_key = f"{action}_cooldown_{duration}"
        pet[cooldown_key] = time.time() + DURATION_SECONDS[duration]

    def get_stage_emoji(self, level: int) -> str:
        """Get the emoji for a pet's stage based on level"""
        # Handle range-based emoji mapping from STAGE_EMOJIS
        for range_key, emoji in STAGE_EMOJIS.items():
            if '-' in range_key:
                start, end = map(int, range_key.split('-'))
                if start <= level <= end:
                    return emoji
        return "🥚"

    async def migrate_pet_data(self, pet: Dict[str, Any]) -> None:
        """Migrate old pet data to new format"""
        # Ensure all required fields exist
        defaults = {
            'max_energy': 100, 'max_maintenance': 100, 'max_happiness': 100,
            'attack': 1, 'defense': 1, 'battles_won': 0, 'battles_lost': 0,
            'group_battles_won': 0, 'group_battles_lost': 0,
            'challenge_wins': 0, 'challenge_losses': 0,
            'open_challenge_wins': 0, 'open_challenge_losses': 0,
            'battle_xp_earned': 0, 'missions_completed': 0, 'total_mission_energon': 0,
            'total_training_energon': 0, 'total_battle_energon': 0, 'total_challenge_energon': 0,
            'mission_xp_earned': 0, 'challenge_xp_earned': 0, 'battle_xp_earned': 0,
            'search_xp_earned': 0, 'charge_xp_earned': 0, 'play_xp_earned': 0, 'repair_xp_earned': 0,
            'play_cooldown_15min': 0, 'play_cooldown_30min': 0, 'play_cooldown_1hour': 0,
            'charge_cooldown_15min': 0, 'charge_cooldown_30min': 0, 'charge_cooldown_1hour': 0,
            'repair_cooldown_15min': 0, 'repair_cooldown_30min': 0, 'repair_cooldown_1hour': 0,
            'equipment': {
                'chassis_plating': None,
                'energy_cores': None,
                'utility_modules': None
            },
            'inventory': []
        }
        
        for key, default_value in defaults.items():
            if key not in pet:
                pet[key] = default_value

    async def send_mission(self, user_id: int, difficulty: str) -> Tuple[bool, str]:
        """Send pet on a mission to earn experience and energon"""
        pet = await user_data_manager.get_pet_data(str(user_id))
        if not pet:
            return False, "You don't have a pet yet!"
        
        # Validate difficulty
        difficulty = difficulty.lower()
        if difficulty not in MISSION_DIFFICULTIES:
            return False, "Invalid difficulty! Choose: easy, average, hard"
        
        # Check if pet has enough energy
        min_cost, max_cost = MISSION_DIFFICULTIES[difficulty]["energy_cost"]
        energy_cost = random.randint(min_cost, max_cost)
        if pet["energy"] < energy_cost:
            return False, f"Not enough energy! Need {energy_cost}, have {pet['energy']:.0f}"
        
        # Check if pet needs maintenance
        if pet["maintenance"] < 20:
            return False, f"{pet['name']} needs maintenance! Use /repair_pet first."
        
        # Calculate success chance based on happiness and maintenance
        total_max_stats = await self.get_total_max_stats(user_id)
        max_happiness = total_max_stats["happiness"]
        max_maintenance = total_max_stats["maintenance"]
        
        base_success = MISSION_DIFFICULTIES[difficulty]["success_rate"]
        happiness_bonus = (pet["happiness"] / max_happiness) * 0.3  # Up to 30% bonus
        maintenance_penalty = max(0, (max_maintenance - pet["maintenance"]) / max_maintenance) * 0.2  # Up to 20% penalty
        success_chance = base_success + happiness_bonus - maintenance_penalty
        success_chance = max(0.1, min(0.9, success_chance))  # Clamp between 10-90%
        
        # Deduct energy
        pet["energy"] -= energy_cost
        
        # Determine success
        success = random.random() < success_chance
        
        if success:
            # Success rewards
            min_xp, max_xp = MISSION_DIFFICULTIES[difficulty]["experience_reward"]
            min_energon, max_energon = MISSION_DIFFICULTIES[difficulty]["energon_reward"]
            xp_gain = random.randint(min_xp, max_xp)
            energon_gain = random.randint(min_energon, max_energon)
            
            # Add experience and check for level up
            leveled_up, level_gains = await self.add_experience(user_id, xp_gain)
            
            # Update stats
            pet["missions_completed"] = pet.get("missions_completed", 0) + 1
            pet["total_mission_energon"] = pet.get("total_mission_energon", 0) + energon_gain
            pet["mission_xp_earned"] = pet.get("mission_xp_earned", 0) + xp_gain
            
            # Add energon reward to global balance and check for energon rush win
            try:
                user_energon = await user_data_manager.get_energon_data(str(user_id))
                current_energon = user_energon.get("energon", 0)
                new_total = current_energon + energon_gain
                user_energon["energon"] = new_total
                
                # Check for energon rush win condition
                try:
                    WIN_CONDITION = 10000  # Energon rush win threshold
                    
                    # Get energon game state directly from user_data_manager
                    game_state = await user_data_manager.get_energon_data(str(user_id))
                    
                    if game_state.get("in_energon_rush", False):
                        # Check if this gain puts them over the win threshold
                        if current_energon < WIN_CONDITION and new_total >= WIN_CONDITION:
                            # Mark game as ended and announce winner
                            game_state['in_energon_rush'] = False
                            await user_data_manager.save_energon_data(str(user_id), game_state)
                            message += f"\n🎉 **ENERGON RUSH CHAMPION!** With {new_total} total energon, you've won the energon rush game!"
                except Exception as e:
                      print(f"Error checking energon rush win: {e}")
                await user_data_manager.save_energon_data(str(user_id), user_energon)
            except Exception as e:
                print(f"Error updating energon for user {user_id}: {e}")
            
            # Happiness gain
            total_max_stats = await self.get_total_max_stats(user_id)
            max_happiness = total_max_stats["happiness"]
            
            min_happy, max_happy = MISSION_DIFFICULTIES[difficulty]["happiness_gain_success"]
            happy_gain = random.randint(min_happy, max_happy)
            pet["happiness"] = min(max_happiness, pet["happiness"] + happy_gain)
            
            # Generate success message
            mission_desc = random.choice(MISSION_TYPES[difficulty])
            message = f"✅ Mission successful! {pet['name']} {mission_desc} and earned {xp_gain} XP and {energon_gain} Energon!"
            
            if leveled_up:
                new_stage = PET_STAGES[pet["level"]]
                stage_emoji = self.get_stage_emoji(pet["level"])
                message += f"\n🎉 Level up! {pet['name']} is now a {stage_emoji} {new_stage['name']}!"
                
                # Send level up embed
                asyncio.create_task(self.send_level_up_embed(user_id, level_gains))
            
        else:
            # Failure penalties
            min_happy_loss, max_happy_loss = MISSION_DIFFICULTIES[difficulty]["happiness_loss_fail"]
            min_main_loss, max_main_loss = MISSION_DIFFICULTIES[difficulty]["maintenance_loss"]
            happiness_loss = random.randint(min_happy_loss, max_happy_loss)
            maintenance_loss = random.randint(min_main_loss, max_main_loss)
            
            pet["happiness"] = max(0, pet["happiness"] - happiness_loss)
            pet["maintenance"] = max(0, pet["maintenance"] - maintenance_loss)
            
            # Small XP gain even on failure
            min_xp, max_xp = MISSION_DIFFICULTIES[difficulty]["experience_reward"]
            xp_gain = random.randint(min_xp, max_xp) // 3
            leveled_up, level_gains = await self.add_experience(user_id, xp_gain)
            pet["mission_xp_earned"] = pet.get("mission_xp_earned", 0) + xp_gain
            
            # Generate failure message
            mission_desc = random.choice(MISSION_TYPES[difficulty])
            message = f"❌ Mission failed! {pet['name']} tried to {mission_desc} but encountered difficulties."
            message += f" Lost {happiness_loss} happiness and {maintenance_loss} maintenance."
            message += f" Gained {xp_gain} XP from the experience."
            
            if leveled_up:
                new_stage = PET_STAGES[pet["level"]]
                stage_emoji = self.get_stage_emoji(pet["level"])
                message += f"\n🎉 Level up! {pet['name']} is now a {stage_emoji} {new_stage['name']}!"
                
                # Send level up embed
                asyncio.create_task(self.send_level_up_embed(user_id, level_gains))
        
        # Save changes
        await user_data_manager.save_pet_data(str(user_id), str(user_id), pet)
        
        return True, message

# Setup function for bot integration
async def setup(bot_instance: commands.Bot) -> None:
    """Setup function to integrate pets system with the bot"""
    try:
        # Initialize the pet system
        pet_system = PetSystem(bot_instance)
        
        # Load initial data
        await load_level_data()
        await pet_system.load_cyberchronicles_monsters()
        await pet_system.load_transformation_items()
        
        # Store the pet system instance in the bot
        bot_instance.pet_system = pet_system
        
        print("✅ Pets system initialized successfully")
        
    except Exception as e:
        print(f"❌ Error initializing pets system: {e}")
        raise

def get_stage_emoji(level: int) -> str:
    """Get the emoji for a pet's stage based on level"""
    # Handle range-based emoji mapping from STAGE_EMOJIS
    for range_key, emoji in STAGE_EMOJIS.items():
        if '-' in range_key:
            start, end = map(int, range_key.split('-'))
            if start <= level <= end:
                return emoji
    return "🥚"

__all__ = [
    'PetSystem',
    'PetStatusView',
    'load_level_data',
    'get_stage_emoji',
    'setup'
]