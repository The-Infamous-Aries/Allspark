import discord
from discord.ext import commands
from discord import app_commands
import random
import json
import sys
import os
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config import ROLE_IDS

# Import the unified user data manager
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from user_data_manager import user_data_manager

# Constants and Configuration
ENERGON_PETS_DIR = os.path.dirname(__file__)
JSON_DIR = os.path.join(os.path.dirname(os.path.dirname(ENERGON_PETS_DIR)), "Json")
MONSTERS_PATH = os.path.join(JSON_DIR, "monsters_and_bosses.json")
ITEMS_PATH = os.path.join(JSON_DIR, "transformation_items.json")

# Level Progression System - Loaded from JSON
LEVEL_THRESHOLDS = {}
PET_STAGES = {}
STAGE_EMOJIS = {}

# Load level progression data from JSON
def load_level_data():
    """Load level progression data from pets_level.json"""
    try:
        level_data_path = os.path.join(os.path.dirname(__file__), '..', '..', 'Json', 'pets_level.json')
        with open(level_data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Convert string keys to integers for LEVEL_THRESHOLDS and PET_STAGES
        global LEVEL_THRESHOLDS, PET_STAGES, STAGE_EMOJIS, AUTOBOT_PET_NAMES, DECEPTICON_PET_NAMES, MISSION_TYPES
        LEVEL_THRESHOLDS = {int(k): v for k, v in data['LEVEL_THRESHOLDS'].items()}
        PET_STAGES = {int(k): v for k, v in data['PET_STAGES'].items()}
        STAGE_EMOJIS = data['STAGE_EMOJIS']
        AUTOBOT_PET_NAMES = data['AUTOBOT_PET_NAMES']
        DECEPTICON_PET_NAMES = data['DECEPTICON_PET_NAMES']
        MISSION_TYPES = data['MISSION_TYPES']
        
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"Error loading pets_level.json: {e}")
        raise RuntimeError("Failed to load pets_level.json - critical system file missing")

# Load level data on module import
load_level_data()

def get_stage_emoji(level: int) -> str:
    """Get the appropriate stage emoji for a given level based on STAGE_EMOJIS ranges"""
    for range_str, emoji in STAGE_EMOJIS.items():
        if '-' in range_str:
            start, end = map(int, range_str.split('-'))
            if start <= level <= end:
                return emoji
    return "❓"

# Mission System Configuration
MISSION_DIFFICULTIES = {
    "easy": {
        "name": "Easy", "emoji": "🟢",
        "energy_cost": (10, 20), "maintenance_risk": 5,
        "maintenance_loss": (5, 15), "success_rate": 75,
        "experience_reward": (15, 25), "energon_reward": (50, 100),
        "happiness_loss_fail": (10, 20), "happiness_gain_success": (5, 10)
    },
    "average": {
        "name": "Average", "emoji": "🟡",
        "energy_cost": (20, 35), "maintenance_risk": 15,
        "maintenance_loss": (10, 25), "success_rate": 60,
        "experience_reward": (25, 40), "energon_reward": (100, 200),
        "happiness_loss_fail": (15, 25), "happiness_gain_success": (8, 15)
    },
    "hard": {
        "name": "Hard", "emoji": "🔴",
        "energy_cost": (30, 50), "maintenance_risk": 25,
        "maintenance_loss": (15, 35), "success_rate": 45,
        "experience_reward": (40, 60), "energon_reward": (200, 400),
        "happiness_loss_fail": (20, 30), "happiness_gain_success": (10, 20)
    }
}



# Battle System Configuration
BATTLE_DIFFICULTY_MAP = {
    "easy": {
        "rarities": ["common", "uncommon", "rare", "epic", "legendary"],
        "rarity_weights": {"common": 50, "uncommon": 30, "rare": 15, "epic": 4, "legendary": 1},
        "att_gain_chance": 15, "def_gain_chance": 10,
        "experience_multiplier": 1.0, "energon_multiplier": 1.0,
        "maintenance_loss": (5, 15), "happiness_loss": (5, 10),
        "loot_chance": 25
    },
    "average": {
        "rarities": ["common", "uncommon", "rare", "epic", "legendary"],
        "rarity_weights": {"common": 25, "uncommon": 35, "rare": 25, "epic": 12, "legendary": 3},
        "att_gain_chance": 25, "def_gain_chance": 20,
        "experience_multiplier": 1.5, "energon_multiplier": 1.5,
        "maintenance_loss": (10, 25), "happiness_loss": (8, 15),
        "loot_chance": 25
    },
    "hard": {
        "rarities": ["common", "uncommon", "rare", "epic", "legendary"],
        "rarity_weights": {"common": 10, "uncommon": 20, "rare": 35, "epic": 25, "legendary": 10},
        "att_gain_chance": 40, "def_gain_chance": 35,
        "experience_multiplier": 2.0, "energon_multiplier": 2.5,
        "maintenance_loss": (15, 35), "happiness_loss": (10, 20),
        "loot_chance": 25
    }
}

# Monster Type and Rarity Emojis
MONSTER_EMOJIS = {
    # Type emojis
    "monster": "🤖",
    "boss": "👹", 
    "titan": "👑",
    
    # Rarity emojis
    "common": "⚪",
    "uncommon": "🟢",
    "rare": "🔵",
    "epic": "🟣",
    "legendary": "🟠",
    "mythic": "🔴"
}

# Battle Monsters Configuration
BATTLE_MONSTERS = {
    "easy": {"att": (1, 5), "def": (1, 5), "health": (10, 25), "name": "Weak Monster"},
    "average": {"att": (5, 15), "def": (5, 15), "health": (25, 50), "name": "Average Monster"},
    "hard": {"att": (15, 30), "def": (15, 30), "health": (50, 100), "name": "Strong Monster"}
}

# Battle System Helper Functions
class BattleSystem:
    @staticmethod
    def calculate_damage(attacker_attack: int, defender_defense: int) -> int:
        """Calculate damage dealt in battle"""
        base_damage = max(1, attacker_attack - (defender_defense // 2))
        variance = random.uniform(0.8, 1.2)
        return max(1, int(base_damage * variance))

    @staticmethod
    def determine_battle_outcome(pet_power: int, monster_power: int, success_rate: int) -> bool:
        """Determine if battle is won based on power comparison and success rate"""
        power_ratio = pet_power / max(monster_power, 1)
        adjusted_chance = min(95, max(5, success_rate + (power_ratio - 1) * 25))
        return random.random() < (adjusted_chance / 100)

    @staticmethod
    def generate_battle_message(pet_name: str, monster_name: str, won: bool, loot: Optional[Dict] = None) -> str:
        """Generate descriptive battle outcome message"""
        if won:
            messages = [
                f"{pet_name} unleashed a devastating attack and defeated {monster_name}!",
                f"{pet_name} outmaneuvered {monster_name} and emerged victorious!",
                f"{pet_name} overcame {monster_name} with superior tactics!"
            ]
            message = random.choice(messages)
            if loot:
                message += f"\n💰 Found: **{loot['name']}** ({loot['type']})"
        else:
            messages = [
                f"{pet_name} fought bravely but {monster_name} proved too powerful...",
                f"{monster_name} overwhelmed {pet_name} with relentless attacks...",
                f"{pet_name} retreated after a fierce battle with {monster_name}..."
            ]
            message = random.choice(messages)
        return message

    @staticmethod
    def get_battle_rewards(monster_rarity: str, won: bool) -> Dict[str, int]:
        """Calculate rewards based on battle outcome using monster rarity directly"""
        # Base rewards by rarity
        rarity_configs = {
            "common": {"base_xp": (20, 35), "base_energon": (50, 80), "loot_chance": 25},
            "uncommon": {"base_xp": (25, 40), "base_energon": (60, 100), "loot_chance": 30},
            "rare": {"base_xp": (30, 50), "base_energon": (80, 130), "loot_chance": 35},
            "epic": {"base_xp": (40, 65), "base_energon": (100, 170), "loot_chance": 40},
            "legendary": {"base_xp": (50, 80), "base_energon": (130, 220), "loot_chance": 45},
            "mythic": {"base_xp": (60, 100), "base_energon": (160, 280), "loot_chance": 50}
        }
        
        config = rarity_configs.get(monster_rarity, rarity_configs["common"])
        
        if won:
            base_xp = random.randint(*config["base_xp"])
            base_energon = random.randint(*config["base_energon"])
            
            return {
                "experience": base_xp,
                "energon": base_energon,
                "loot_chance": config["loot_chance"]
            }
        else:
            # Reduced rewards for loss
            return {
                "experience": random.randint(5, 15),
                "energon": random.randint(10, 30),
                "loot_chance": 0
            }


# Interactive Pet Status View
class PetStatusView(discord.ui.View):
    """Interactive view for pet status with Breakdown and Refresh buttons"""
    
    def __init__(self, user_id: int, pet_system, commands_cog):
        super().__init__(timeout=300)  # 5 minute timeout
        self.user_id = user_id
        self.pet_system = pet_system
        self.commands_cog = commands_cog
        self.showing_breakdown = False
    
    async def create_main_embed(self) -> discord.Embed:
        """Create the main pet status embed"""
        pet = await self.pet_system.get_user_pet(self.user_id)
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
            title=f"{stage_emoji} {pet['name']} - {pet.get('faction', 'Unknown')}",
            color=embed_color
        )
        
        # Always show full date and time
        created = datetime.fromisoformat(pet["created_at"])
        age_text = created.strftime("%B %d, %Y at %I:%M %p")
        
        embed.add_field(name="🧬 Stage", value=f"{stage_emoji} {pet['level']} - {stage['name']}", inline=True)
        embed.add_field(name="🗓️ Created", value=age_text, inline=True)
        
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
        
        embed.add_field(name="🔋 **Energy**", value=f"{pet['energy']:.0f}/{pet['max_energy']:.0f}", inline=True)
        embed.add_field(name="🔧 **Maintenance**", value=f"{pet['maintenance']:.0f}/{pet['max_maintenance']:.0f}", inline=True)
        embed.add_field(name="😊 **Happiness**", value=f"{pet['happiness']:.0f}/{pet['max_happiness']:.0f}", inline=True)
        embed.add_field(name="⚡ **Power**", value=f"⚔️ Attack: {pet['attack']} | 🛡️ Defense: {pet['defense']}", inline=False)
        
        # Calculate totals
        detailed_stats = self.get_pet_detailed_stats(self.user_id)
        
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
        pet = await self.pet_system.get_user_pet(user_id)
        if not pet:
            return None
            
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
            
        # Refresh data
        self.pet_system.load_pet_data()
        
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
    

    
    
    
    def load_cyberchronicles_monsters(self) -> None:
        """Load monsters, bosses, and titans from JSON file"""
        try:
            monsters_file = MONSTERS_PATH
            if os.path.exists(monsters_file):
                with open(monsters_file, 'r') as f:
                    data = json.load(f)
                    
                    # Reset data structures
                    self.monsters_data = {}
                    self.bosses_data = {}
                    self.titans_data = {}
                    
                    # Load monsters by type and rarity (new structure)
                    if 'monsters' in data:
                        monsters_data = data['monsters']
                        
                        # Handle new structure where monsters are organized by rarity
                        if isinstance(monsters_data, dict):
                            for rarity, monster_list in monsters_data.items():
                                if isinstance(monster_list, list):
                                    for monster in monster_list:
                                        monster_type = monster.get('type', 'monster')
                                        if monster_type == 'monster':
                                            self._add_to_collection(self.monsters_data, rarity.lower(), monster)
                                        elif monster_type == 'boss':
                                            self._add_to_collection(self.bosses_data, rarity.lower(), monster)
                                        elif monster_type == 'titan':
                                            self._add_to_collection(self.titans_data, rarity.lower(), monster)
                        
                        # Handle old structure (fallback)
                        elif isinstance(monsters_data, dict):
                            for monster_id, monster in monsters_data.items():
                                if isinstance(monster, dict):
                                    rarity = monster.get('rarity', 'common').lower()
                                    monster_type = monster.get('type', 'monster')
                                    
                                    if monster_type == 'monster':
                                        self._add_to_collection(self.monsters_data, rarity, monster)
                                    elif monster_type == 'boss':
                                        self._add_to_collection(self.bosses_data, rarity, monster)
                                    elif monster_type == 'titan':
                                        self._add_to_collection(self.titans_data, rarity, monster)
                    
                    # Check for direct boss and titan structures
                    if 'bosses' in data:
                        bosses_data = data['bosses']
                        if isinstance(bosses_data, dict):
                            for rarity, boss_list in bosses_data.items():
                                if isinstance(boss_list, list):
                                    for boss in boss_list:
                                        self._add_to_collection(self.bosses_data, rarity.lower(), boss)
                    
                    if 'titans' in data:
                        titans_data = data['titans']
                        if isinstance(titans_data, dict):
                            for rarity, titan_list in titans_data.items():
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
    
    def load_transformation_items(self) -> None:
        """Load transformation items from JSON file"""
        try:
            items_file = ITEMS_PATH
            if os.path.exists(items_file):
                with open(items_file, 'r') as f:
                    data = json.load(f)
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


    


    def load_cyberchronicles_monsters_lazy(self) -> Dict[str, Dict[str, List[Dict]]]:
        """Lazy load monsters, bosses, and titans from JSON file"""
        monsters_data = {}
        bosses_data = {}
        titans_data = {}
        
        try:
            if os.path.exists(MONSTERS_PATH):
                with open(MONSTERS_PATH, 'r') as f:
                    data = json.load(f)
                    
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
                                            if rarity.lower() not in monsters_data:
                                                monsters_data[rarity.lower()] = []
                                            monsters_data[rarity.lower()].append(monster)
                                        elif monster_type == 'boss':
                                            if rarity.lower() not in bosses_data:
                                                bosses_data[rarity.lower()] = []
                                            bosses_data[rarity.lower()].append(monster)
                                        elif monster_type == 'titan':
                                            if rarity.lower() not in titans_data:
                                                titans_data[rarity.lower()] = []
                                            titans_data[rarity.lower()].append(titan)
                    
                    # Check for direct boss and titan structures
                    if 'bosses' in data:
                        bosses_json = data['bosses']
                        if isinstance(bosses_json, dict):
                            for rarity, boss_list in bosses_json.items():
                                if isinstance(boss_list, list):
                                    bosses_data[rarity.lower()] = boss_list
                    
                    if 'titans' in data:
                        titans_json = data['titans']
                        if isinstance(titans_json, dict):
                            for rarity, titan_list in titans_json.items():
                                if isinstance(titan_list, list):
                                    titans_data[rarity.lower()] = titan_list
        except Exception as e:
            print(f"Error loading monsters: {e}")
        
        return {
            'monsters': monsters_data,
            'bosses': bosses_data,
            'titans': titans_data
        }


    def load_transformation_items_lazy(self) -> Dict[str, Dict[str, Dict]]:
        """Lazy load transformation items from JSON file"""
        try:
            if os.path.exists(ITEMS_PATH):
                with open(ITEMS_PATH, 'r') as f:
                    data = json.load(f)
                    # Handle new structure with items_by_class
                    if 'items_by_class' in data:
                        return data['items_by_class']
                    else:
                        # Fallback to old structure
                        return data
        except Exception as e:
            print(f"Error loading transformation items: {e}")
        return {}
    
    def _add_to_collection(self, collection: Dict[str, List], rarity: str, item: Dict) -> None:
        """Helper method to add items to collection by rarity"""
        if rarity not in collection:
            collection[rarity] = []
        collection[rarity].append(item)
    
    async def create_pet(self, user_id: int, faction: str) -> Dict[str, Any]:
        """Create a new pet for a user"""
        # Select appropriate name list based on faction
        name_list = AUTOBOT_PET_NAMES if faction.lower() == 'autobot' else DECEPTICON_PET_NAMES
        pet_name = random.choice(name_list)
        
        # Initialize pet data with faction-based starting stats
        faction_lower = faction.lower()
        if faction_lower == 'autobot':
            attack = 4
            defense = 5
            happiness = 200
            energy = 100
        else:  # Decepticon
            attack = 5
            defense = 4
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
            "created_at": datetime.now().isoformat()
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
    
    def create_enemy_monster(self, enemy_type: str, enemy_rarity: str) -> Dict[str, Any]:
        """Create an enemy monster based on type and rarity"""
        try:
            # Ensure monsters are loaded
            if not self._monsters_loaded:
                self.load_cyberchronicles_monsters()
            
            # Normalize case for rarity
            enemy_rarity = enemy_rarity.lower()
            
            # Get appropriate enemy collection
            if enemy_type == "monster":
                enemies = self.monsters_data
            elif enemy_type == "boss":
                enemies = self.bosses_data
            elif enemy_type == "titan":
                enemies = self.titans_data
            else:
                enemies = self.monsters_data
            
            # Get monsters by rarity
            matching_enemies = enemies.get(enemy_rarity, [])
            
            if matching_enemies:
                monster = random.choice(matching_enemies)
                # Ensure proper attack formatting
                if "attack" in monster:
                    attack_value = monster["attack"]
                    monster["attack_min"] = attack_value
                    monster["attack_max"] = int(attack_value * 1.2)
                else:
                    monster["attack_min"] = monster.get("attack_min", 10)
                    monster["attack_max"] = monster.get("attack_max", 15)
                
                monster["health"] = monster.get("health", 50)
                monster["type"] = enemy_type
                monster["rarity"] = enemy_rarity
                return monster
            else:
                # Create fallback monster with scaling based on type and rarity
                base_health = {
                    "common": 100, "uncommon": 150, "rare": 200, 
                    "epic": 300, "legendary": 400, "mythic": 500
                }.get(enemy_rarity, 100)
                
                base_attack = {
                    "common": 8, "uncommon": 12, "rare": 16, 
                    "epic": 22, "legendary": 28, "mythic": 35
                }.get(enemy_rarity, 8)

                # Scale based on enemy type
                if enemy_type == "boss":
                    base_health *= 2.5
                    base_attack *= 1.8
                elif enemy_type == "titan":
                    base_health *= 5
                    base_attack *= 2.5

                return {
                    "name": f"{enemy_rarity.title()} {enemy_type.title()}",
                    "health": int(base_health),
                    "attack_min": int(base_attack),
                    "attack_max": int(base_attack * 1.5),
                    "type": enemy_type,
                    "rarity": enemy_rarity
                }
                
        except Exception as e:
            print(f"Error creating enemy monster: {e}")
            # Fallback monster
            return {
                "name": f"{enemy_rarity.title()} {enemy_type.title()}",
                "health": 100,
                "attack_min": 10,
                "attack_max": 15,
                "type": enemy_type,
                "rarity": enemy_rarity
            }

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
            "15min": {"multiplier": 1.0, "xp_base": 5, "energy_percent": 50},
            "30min": {"multiplier": 2.5, "xp_base": 12, "energy_percent": 75},
            "1hour": {"multiplier": 6.0, "xp_base": 25, "energy_percent": 100}
        }
        
        pet = await self.get_user_pet(user_id)
        if not pet:
            return False, "No pet found"
        
        if duration not in DURATION_CONFIG:
            return False, "Invalid duration! Choose: 15min, 30min, 1hour"
        
        config = DURATION_CONFIG[duration]
        
        if pet['energy'] >= pet['max_energy']:
            return False, f"{pet['name']} is already fully charged!"
        
        # Calculate energy gain based on duration and pet's max energy
        energy_gain = int(pet['max_energy'] * (config["energy_percent"] / 100) * config["multiplier"])
        new_energy = min(pet['max_energy'], pet['energy'] + energy_gain)
        actual_gain = new_energy - pet['energy']
        pet['energy'] = new_energy
        
        # Award scaled XP for charging
        xp_gain = int(config["xp_base"] * config["multiplier"])
        leveled_up, level_gains = await self.add_experience(user_id, xp_gain, "charge")
        pet["charge_xp_earned"] = pet.get("charge_xp_earned", 0) + xp_gain
        
        await user_data_manager.save_pet_data(str(user_id), str(user_id), pet)
        
        duration_emoji = {"15min": "🪫", "30min": "🔋", "1hour": "🏭"}
        message = f"{duration_emoji[duration]} Charged {pet['name']} for {duration} - gained {actual_gain}⚡ energy and {xp_gain} XP!"
        
        return True, message, level_gains if leveled_up else None
    
    async def play_with_pet(self, user_id: int, duration: str = "15min") -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Play with pet to increase happiness with duration-based scaling"""
        DURATION_CONFIG = {
            "15min": {"multiplier": 1.0, "xp_base": 3, "happiness_percent": 25},
            "30min": {"multiplier": 2.5, "xp_base": 8, "happiness_percent": 50},
            "1hour": {"multiplier": 6.0, "xp_base": 15, "happiness_percent": 100}
        }
        
        pet = await self.get_user_pet(user_id)
        if not pet:
            return False, "No pet found", None
        
        if duration not in DURATION_CONFIG:
            return False, "Invalid duration! Choose: 15min, 30min, 1hour", None
        
        config = DURATION_CONFIG[duration]
        
        if pet['happiness'] >= pet['max_happiness']:
            return False, f"{pet['name']} is already maximally happy!", None
        
        # Calculate happiness gain based on duration and pet's max happiness
        base_happiness = int(pet['max_happiness'] * (config["happiness_percent"] / 100))
        happiness_gain = int(base_happiness * config["multiplier"])
        new_happiness = min(pet['max_happiness'], pet['happiness'] + happiness_gain)
        actual_gain = new_happiness - pet['happiness']
        pet['happiness'] = new_happiness
        
        # Award scaled XP for playing
        xp_gain = int(config["xp_base"] * config["multiplier"])
        leveled_up, level_gains = await self.add_experience(user_id, xp_gain, "play")
        pet["play_xp_earned"] = pet.get("play_xp_earned", 0) + xp_gain
        
        await user_data_manager.save_pet_data(str(user_id), str(user_id), pet)
        
        duration_emoji = {"15min": "🎮", "30min": "🃏", "1hour": "🎳"}
        message = f"{duration_emoji[duration]} Played with {pet['name']} for {duration} - gained {actual_gain}😊 happiness and {xp_gain} XP!"
        
        return True, message, level_gains if leveled_up else None
    
    async def train_pet(self, user_id: int, difficulty: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Train pet with difficulty-based rewards and penalties"""
        TRAINING_CONFIG = {
            "average": {
                "energy_cost": 50,
                "happiness_penalty": 10,
                "xp_reward": (25, 35),
                "energon_reward": 10,
                "stat_chance": 0.05,  # 5% chance
                "stat_gain": 1
            },
            "intense": {
                "energy_cost": 150,
                "happiness_penalty": 25,
                "xp_reward": (75, 100),
                "energon_reward": 50,
                "stat_chance": 0.15,  # 15% chance
                "stat_gain": 2
            },
            "godmode": {
                "energy_cost": 300,
                "happiness_penalty": 50,
                "xp_reward": (200, 300),
                "energon_reward": 200,
                "stat_chance": 0.35,  # 35% chance
                "stat_gain": 3
            }
        }
        
        pet = await self.get_user_pet(user_id)
        if not pet:
            return False, "No pet found"
        
        difficulty = difficulty.lower()
        if difficulty not in TRAINING_CONFIG:
            return False, "Invalid difficulty! Choose: average, intense, godmode"
        
        config = TRAINING_CONFIG[difficulty]
        
        if pet['energy'] < config["energy_cost"]:
            return False, f"{pet['name']} doesn't have enough energy! Needs {config['energy_cost']}, has {pet['energy']}"
        
        if pet['happiness'] < config["happiness_penalty"]:
            return False, f"{pet['name']} is too unhappy to train at this intensity!"
        
        # Apply energy cost and happiness penalty
        pet['energy'] -= config["energy_cost"]
        pet['happiness'] = max(0, pet['happiness'] - config["happiness_penalty"])
        
        # Award XP and Energon
        xp_gain = random.randint(*config["xp_reward"])
        energon_gain = config["energon_reward"]
        
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
        
        # Add energon reward to global balance
        try:
            # Use the global energon balance system
            user_energon = await user_data_manager.get_energon_data(str(user_id))
            user_energon["energon"] += energon_gain
            await user_data_manager.save_energon_data(str(user_id), user_energon)
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
            "15min": {"multiplier": 1.0, "xp_base": 8, "maintenance_percent": 40},
            "30min": {"multiplier": 2.5, "xp_base": 20, "maintenance_percent": 70},
            "1hour": {"multiplier": 6.0, "xp_base": 50, "maintenance_percent": 100}
        }
        
        pet = await self.get_user_pet(user_id)
        if not pet:
            return False, "No pet found"
        
        if duration not in DURATION_CONFIG:
            return False, "Invalid duration! Choose: 15min, 30min, 1hour"
        
        config = DURATION_CONFIG[duration]
        
        if pet['maintenance'] >= pet['max_maintenance']:
            return False, f"{pet['name']} is already in perfect condition!"
        
        # Calculate maintenance gain based on duration and pet's max maintenance
        maintenance_gain = int(pet['max_maintenance'] * (config["maintenance_percent"] / 100) * config["multiplier"])
        new_maintenance = min(pet['max_maintenance'], pet['maintenance'] + maintenance_gain)
        actual_gain = new_maintenance - pet['maintenance']
        pet['maintenance'] = new_maintenance
        
        # Award scaled XP for repairing
        xp_gain = int(config["xp_base"] * config["multiplier"])
        leveled_up, level_gains = await self.add_experience(user_id, xp_gain, "repair")
        pet["repair_xp_earned"] = pet.get("repair_xp_earned", 0) + xp_gain
        
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
                
                # Level up rewards: 3 random points to attack/defense and +50 max to energy/maintenance/happiness
                total_points = 3
                att_gain = random.randint(0, total_points)
                def_gain = total_points - att_gain
                
                pet["attack"] += att_gain
                pet["defense"] += def_gain
                
                # Add 50 to max values and current values
                energy_gain = 50
                maintenance_gain = 50
                happiness_gain = 50
                
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

    def create_level_up_embed(self, pet: Dict[str, Any], level_gains: Dict[str, Any]) -> discord.Embed:
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
        
        embed.add_field(
            name="Current Stats",
            value=f"Level: **{new_level}**\n"
                  f"Attack: **{pet['attack']}**\n"
                  f"Defense: **{pet['defense']}**\n"
                  f"Energy: **{pet['energy']}/{pet['max_energy']}**\n"
                  f"Maintenance: **{pet['maintenance']}/{pet['max_maintenance']}**\n"
                  f"Happiness: **{pet['happiness']}/{pet['max_happiness']}**",
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
            
        embed = self.create_level_up_embed(pet, level_gains)
        
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
    
    def calculate_battle_chance(self, pet: Dict[str, Any], monster_difficulty: str) -> Tuple[int, int, int]:
        """Calculate battle success chance based on pet stats vs monster"""
        monster = BATTLE_MONSTERS[monster_difficulty]
        
        # Get random monster stats
        monster_att = random.randint(*monster["att"])
        monster_def = random.randint(*monster["def"])
        
        # Calculate power difference
        pet_power = (pet["attack"] + pet["defense"]) * pet["level"]
        monster_level = {"easy": 2, "average": 4, "hard": 6}[monster_difficulty]
        monster_power = (monster_att + monster_def) * monster_level
        
        # Base chance calculation
        power_ratio = pet_power / max(monster_power, 1)
        base_chance = min(85, max(15, 50 + (power_ratio - 1) * 30))
        
        # Happiness bonus (up to +15%)
        happiness_bonus = (pet["happiness"] / pet["max_happiness"]) * 15
        
        # Maintenance penalty (up to -20%)
        maintenance_penalty = ((pet["max_maintenance"] - pet["maintenance"]) / pet["max_maintenance"]) * 20
        
        final_chance = max(5, min(95, base_chance + happiness_bonus - maintenance_penalty))
        
        return int(final_chance), monster_att, monster_def
    
    async def delete_pet(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Delete a user's pet permanently"""
        pet = await user_data_manager.get_pet_data(str(user_id))
        if pet:
            await user_data_manager.delete_pet_data(user_id)
            return pet
        return None
    
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
            'search_xp_earned': 0, 'charge_xp_earned': 0, 'play_xp_earned': 0, 'repair_xp_earned': 0
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
        base_success = MISSION_DIFFICULTIES[difficulty]["success_rate"]
        happiness_bonus = (pet["happiness"] / pet["max_happiness"]) * 0.3  # Up to 30% bonus
        maintenance_penalty = max(0, (pet["max_maintenance"] - pet["maintenance"]) / pet["max_maintenance"]) * 0.2  # Up to 20% penalty
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
            
            # Happiness gain
            min_happy, max_happy = MISSION_DIFFICULTIES[difficulty]["happiness_gain_success"]
            happy_gain = random.randint(min_happy, max_happy)
            pet["happiness"] = min(pet["max_happiness"], pet["happiness"] + happy_gain)
            
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
        await user_data_manager.save_pet_data(user_id, pet)
        
        return True, message

class BattleInfoView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        
    def get_battle_info_embed(self):
        embed = discord.Embed(
            title="⚔️ Pet Battle Guide",
            description="Complete guide to pet battles, rolls, enemies, and loot!",
            color=0x0099ff
        )
        
        embed.add_field(
            name="🎯 How Battles Work",
            value="**Battle Types:**\n• **Solo** - You vs monsters\n• **Group** - Up to 4 players vs bosses\n• **PvP** - Challenge other players\n\n**Combat Flow:**\n1️⃣ Choose battle type and opponent\n2️⃣ Pick Attack, Defend, or Charge\n3️⃣ Roll 1d20 for damage multiplier\n4️⃣ Apply damage based on roll and action\n5️⃣ Continue until someone wins!",
            inline=False
        )
        
        embed.add_field(
            name="🎲 Roll System & Damage",
            value="**d20 Roll Multipliers:**\n• **1-4**: Reduced damage (0.2x to 0.8x)\n• **5-11**: Normal damage (1x)\n• **12-15**: Good damage (2x-5x)\n• **16-19**: Great damage (6x-9x)\n• **20**: Critical damage (10x)\n\n**Damage Formula:**\n`Damage = Pet Attack × Charge × Roll Multiplier`\n\n**Actions:**\n• **Attack**: Roll d20 for multiplier\n• **Defend**: 50% damage reduction\n• **Charge**: 2x multiplier stack (1.5x damage taken)",
            inline=False
        )
        
        embed.add_field(
            name="👾 Enemy Types",
            value="**By Difficulty:**\n• **Easy**: Weak monsters, low health\n• **Normal**: Balanced enemies\n• **Hard**: Strong bosses, high health\n• **Extreme**: Titan-level threats\n\n**By Category:**\n• **Monsters**: Standard enemies\n• **Bosses**: Powerful single enemies\n• **Titans**: Real Transformers (hardest)",
            inline=False
        )
        
        embed.add_field(
            name="💎 Loot & Rarity",
            value="**Lootable Objects:**\n• **Beast Modes**: Transform into powerful animals\n• **Transformations**: Vehicle and alternate forms\n• **Weapons**: Combat equipment and upgrades\n• **Armor**: Defensive gear and protection\n\n**Rarity Tiers:**\n• **Common** ⚪ - Basic items with minimal boosts\n• **Uncommon** 🟢 - Better stats and effects\n• **Rare** 🔵 - Significant stat improvements\n• **Epic** 🟣 - Powerful upgrades with special abilities\n• **Legendary** 🟡 - Ultimate items with massive bonuses\n• **Mythic** 🔴 - Transcendent items beyond imagination",
            inline=False
        )
        
        embed.set_footer(text="Battle smart, train hard, and may the Allspark be with you! ✨")
        return embed
        
    @discord.ui.button(label="Close", style=discord.ButtonStyle.grey, emoji="❌")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Only the command user can close!", ephemeral=True)
            return
        await interaction.message.delete()
        
    async def on_timeout(self):
        try:
            await self.message.edit(view=None)
        except:
            pass

class UnifiedBattleView(discord.ui.View):
    def __init__(self, ctx, pet_system, battle_type="solo", participants=None, monster=None, difficulty="normal", target_user=None, energon_bet=0):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.pet_system = pet_system
        self.battle_type = battle_type  # "solo", "group", "pvp", "energon_challenge"
        self.selected_difficulty = difficulty  # Store difficulty for battle rewards
        self.selected_rarity = difficulty  # Also store as rarity for loot calculations
        self.energon_bet = energon_bet  # For energon challenges
        self.message = None
        
        # These will be populated by create_async
        self.participants = participants or []
        self.monster = monster
        self.player_data = {}
        self.monster_hp = 0
        self.max_monster_hp = 0
        self.monster_charge_multiplier = 1.0
        self.current_turn_index = 0
        self.turn_count = 0
        self.battle_started = False
        self.battle_over = False
        self.battle_log = []
        
        # For group battles - join functionality
        self.join_mode = battle_type == "group"
        self.max_participants = 4

    @classmethod
    async def create_async(cls, ctx, pet_system, battle_type="solo", participants=None, monster=None, difficulty="normal", target_user=None, energon_bet=0):
        """Async factory method to create a battle view with properly loaded pets"""
        view = cls(ctx, pet_system, battle_type, participants, monster, difficulty, target_user, energon_bet)
        
        # Load pets asynchronously
        if battle_type == "solo":
            pet = await user_data_manager.get_pet_data(str(ctx.author.id), ctx.author.display_name)
            view.participants = [(ctx.author, pet)]
            view.monster = monster or view.get_random_monster(difficulty)
        elif battle_type == "group":
            if not participants:
                pet = await user_data_manager.get_pet_data(str(ctx.author.id), ctx.author.display_name)
                view.participants = [(ctx.author, pet)]
            else:
                # Load pets for all provided participants
                loaded_participants = []
                for user, _ in participants:
                    pet = await user_data_manager.get_pet_data(str(user.id), user.display_name)
                    loaded_participants.append((user, pet))
                view.participants = loaded_participants
            view.monster = monster or view.get_random_monster(difficulty)
        elif battle_type == "pvp":
            pet = await user_data_manager.get_pet_data(str(ctx.author.id), ctx.author.display_name)
            view.participants = [(ctx.author, pet)]
            if target_user:
                target_pet = await user_data_manager.get_pet_data(str(target_user.id), target_user.display_name)
                view.participants.append((target_user, target_pet))
            view.monster = None  # PvP has no monster
        
        # Initialize battle data with loaded pets
        view.initialize_battle_data()
        
        return view

    def get_random_monster(self, difficulty):
        """Get a random monster based on difficulty"""
        try:
            # Ensure monsters are loaded
            if not self.pet_system._monsters_loaded:
                self.pet_system.load_cyberchronicles_monsters()
            
            difficulty_config = BATTLE_DIFFICULTY_MAP[difficulty]
            rarities = difficulty_config["rarities"]
            weights = difficulty_config["rarity_weights"]
            
            # Select rarity based on weights
            selected_rarity = random.choices(rarities, weights=[weights[r] for r in rarities])[0]
            
            # Get random monster from selected rarity
            if selected_rarity in self.pet_system.monsters_data and self.pet_system.monsters_data[selected_rarity]:
                monster = random.choice(self.pet_system.monsters_data[selected_rarity])
                return {
                    "name": monster["name"],
                    "health": monster["health"],
                    "attack": monster["attack"],
                    "defense": monster["defense"],
                    "type": monster.get("type", "monster"),
                    "rarity": monster["rarity"]
                }
            else:
                # Fallback monster
                return {
                    "name": f"{selected_rarity.title()} Monster",
                    "health": 100,
                    "attack": 12,
                    "defense": 8,
                    "type": "monster",
                    "rarity": selected_rarity
                }
        except Exception as e:
            print(f"Error getting random monster: {e}")
            return {"name": "Generic Monster", "health": 100, "attack": 12, "defense": 8, "type": "monster", "rarity": "common"}

    def initialize_battle_data(self):
        """Initialize battle data for all participants"""
        for user, pet in self.participants:
            if pet:
                max_hp = pet['energy'] + pet['maintenance']
                self.player_data[user.id] = {
                    'user': user,
                    'pet': pet,
                    'hp': max_hp,
                    'max_hp': max_hp,
                    'charge': 1.0,
                    'charging': False,
                    'alive': True,
                    'last_action': None
                }
        
        if self.monster:
            self.monster_hp = self.monster['health']
            self.max_monster_hp = self.monster['health']
            self.monster_charge = 1.0
            self.monster_charging = False

    def create_hp_bar(self, current, max_hp, bar_type="default", pet=None):
        """Create a visual HP bar with faction-based colors"""
        percentage = max(0, min(100, (current / max_hp) * 100))
        filled = int(percentage // 10)
        empty = 10 - filled
        
        if bar_type == "pet" and pet:
            # Check faction for player pets
            faction = pet.get('faction', '').lower()
            if faction == 'decepticon':
                filled_char, empty_char = "🟪", "⬛"  # Purple for Decepticons
            elif faction == 'autobot':
                filled_char, empty_char = "🟥", "⬛"  # Red for Autobots
            else:
                filled_char, empty_char = "🟩", "⬛"  # Default green
        elif bar_type == "enemy":
            filled_char, empty_char = "🟨", "⬛"  # Yellow for enemies
        else:
            filled_char, empty_char = "█", "░"
        
        bar = filled_char * filled + empty_char * empty
        return f"[{bar}] {current}/{max_hp} ({percentage:.0f}%)"

    def get_current_player(self):
        """Get the current player's turn"""
        alive_players = [pid for pid, data in self.player_data.items() if data['alive']]
        if not alive_players:
            return None
        
        current_id = alive_players[self.current_turn_index % len(alive_players)]
        return self.player_data[current_id]

    def build_join_embed(self):
        """Build embed for group battle joining phase"""
        embed = discord.Embed(
            title=f"⚔️ {self.battle_type.title()} Battle Setup",
            description=f"{self.ctx.author.display_name} is forming a battle!",
            color=0x0099ff
        )
        
        # Show participants
        participants_list = []
        for user, pet in self.participants:
            if pet:
                participants_list.append(f"{user.display_name} - {pet['name']} (Level {pet['level']})")
        
        embed.add_field(name="🐾 Participants", value="\n".join(participants_list) or "No participants yet", inline=False)
        
        if self.monster:
            # Get type and rarity emojis
            type_emoji = MONSTER_EMOJIS.get(self.monster.get('type', 'monster'), '🤖')
            rarity_emoji = MONSTER_EMOJIS.get(self.monster.get('rarity', 'common'), '⚪')
            
            embed.add_field(
                name=f"{type_emoji} {rarity_emoji} {self.monster['name']}", 
                value=f"❤️ {self.monster['health']} HP", 
                inline=False
            )
        
        embed.add_field(name="📊 Type", value=self.battle_type.title(), inline=True)
        embed.set_footer(text=f"Click 'Join Battle' to participate! (Max {self.max_participants} players)")
        
        return embed

    def build_battle_embed(self, action_text=""):
        """Build the battle embed"""
        current_player = self.get_current_player()
        if not current_player:
            return discord.Embed(title="Battle Ended", color=0x808080)
        
        title = f"⚔️ {self.battle_type.title()} Battle"
        if self.battle_type == "energon_challenge":
            title = f"💎 Energon Challenge (Bet: {self.energon_bet})"
        
        embed = discord.Embed(
            title=title,
            description=f"Turn {self.turn_count + 1} - {current_player['user'].display_name}'s turn!",
            color=0x0099ff
        )
        
        # Show participants
        status_lines = []
        for user_id, data in self.player_data.items():
            user = data['user']
            pet = data['pet']
            hp_bar = self.create_hp_bar(data['hp'], data['max_hp'], "pet", pet)
            charge_info = f" ⚡x{data['charge']:.1f}" if data['charge'] > 1.0 else ""
            charging_info = " 🔋" if data['charging'] else ""
            status = "💀" if not data['alive'] else "➡️" if user_id == current_player['user'].id else "🟢"
            status_lines.append(f"{status} {user.display_name} - {pet['name']}{charge_info}{charging_info}\n{hp_bar}")
        
        if len(status_lines) <= 2:
            embed.add_field(name="🛡️ Participants", value="\n".join(status_lines), inline=False)
        else:
            mid = len(status_lines) // 2
            embed.add_field(name="🛡️ Team (1/2)", value="\n".join(status_lines[:mid]), inline=True)
            embed.add_field(name="🛡️ Team (2/2)", value="\n".join(status_lines[mid:]), inline=True)
        
        # Show monster if exists
        if self.monster:
            monster_charge_info = f" 🔋" if self.monster_charging else ""
            monster_hp_bar = self.create_hp_bar(self.monster_hp, self.max_monster_hp, "enemy")
            
            # Get type and rarity emojis
            type_emoji = MONSTER_EMOJIS.get(self.monster.get('type', 'monster'), '🤖')
            rarity_emoji = MONSTER_EMOJIS.get(self.monster.get('rarity', 'common'), '⚪')
            
            embed.add_field(
                name=f"{type_emoji} {rarity_emoji} {self.monster['name']}{monster_charge_info}", 
                value=monster_hp_bar, 
                inline=False
            )
        
        # Always show actions regardless of damage dealt
        if action_text:
            embed.add_field(name="⚡ Action", value=action_text[:200], inline=False)
        else:
            # Show basic turn info even when no special actions
            current_pet = current_player['pet']
            embed.add_field(name="⚡ Turn Action", value=f"{current_pet['name']} takes their turn!", inline=False)
        
        alive_count = sum(1 for data in self.player_data.values() if data['alive'])
        embed.set_footer(text=f"Turn {self.turn_count} | {alive_count} active fighters")
        
        return embed

    def roll_d20(self):
        """Roll a d20 for battle mechanics"""
        return random.randint(1, 20)

    def calculate_attack_multiplier(self, roll):
        """Calculate attack multiplier based on d20 roll value"""
        if 1 <= roll <= 5:
            # Divides attack by 5 for 1, 4 for 2, 3 for 3, 2 for 4, 1 for 5
            divisor_map = {1: 5, 2: 4, 3: 3, 4: 2, 5: 1}
            return 1.0 / divisor_map[roll]
        elif 6 <= roll <= 10:
            # No multiplier or divider
            return 1.0
        elif 11 <= roll <= 20:
            # Multiplies attack by 1-10 (11=1x, 12=2x, ..., 20=10x)
            return roll - 10
        return 1.0

    def calculate_damage_with_action(self, attack_power, defense, action_type, charge_multiplier=1.0, is_defending=False):
        """Calculate damage based on competitive d20 roll system"""
        # This method is now used for individual rolls in competitive system
        roll = self.roll_d20()
        
        if action_type == "attack":
            damage = int(attack_power * charge_multiplier)
            text = f"Attack power: {damage}"
        elif action_type == "defend":
            defense_value = int(defense)
            text = f"Defense: {defense_value}"
            damage = defense_value
        else:  # charge
            damage = 0
            text = ""
            
        return damage, roll, text

    def get_monster_action(self):
        """Determine monster's action based on AI"""
        if not self.monster:
            return None
            
        monster_hp_percent = (self.monster_hp / self.max_monster_hp) * 100
        
        if monster_hp_percent <= 20:
            choices = ["attack", "attack", "attack", "defend", "defend", "charge"]
        elif monster_hp_percent <= 50:
            choices = ["attack", "attack", "defend", "defend", "charge"]
        else:
            choices = ["attack", "attack", "attack", "attack", "defend", "charge"]
            
        return random.choice(choices)

    async def process_turn(self, player_action: str, user_id: int):
        """Process a single turn"""
        if self.battle_over:
            return "Battle is over!"
        
        player_data = self.player_data.get(user_id)
        if not player_data or not player_data['alive']:
            return "Invalid or defeated player!"
        
        action_text = ""
        
        if self.battle_type in ["solo", "group"]:
            # Battle against monster
            monster_action = self.get_monster_action()
            
            # Process combat based on action combinations
            damage_result = self.process_combat_action(player_data, monster_action, player_action)
            action_text += damage_result
            
        elif self.battle_type == "pvp":
            # PvP battle logic
            target_player = self.find_pvp_target(user_id)
            if target_player:
                damage_result = self.process_pvp_action(player_data, target_player, player_action)
                action_text += damage_result
        
        # Check for victory conditions
        self.check_victory_conditions()
        
        # Move to next turn
        if not self.battle_over:
            self.turn_count += 1
            self.current_turn_index += 1
        
        return action_text

    def process_combat_action(self, player_data, monster_action, player_action):
        """Process combat between player and monster using new d20 multiplier system"""
        action_text = ""
        pet = player_data['pet']
        
        # Single d20 roll for attack multiplier
        player_roll = self.roll_d20()
        attack_multiplier = self.calculate_attack_multiplier(player_roll)
        
        # Handle charging damage multiplier
        player_damage_multiplier = 1.5 if player_data['charging'] else 1.0
        monster_damage_multiplier = 1.5 if self.monster_charging else 1.0
        
        # Player attack vs Monster attack
        if player_action == "attack" and monster_action == "attack":
            player_damage = int(pet['attack'] * player_data['charge'] * attack_multiplier)
            monster_damage = int(self.monster.get('attack', 10) * self.monster_charge_multiplier)
            
            # Monster always attacks back (no competitive roll)
            final_player_damage = int(player_damage * player_damage_multiplier)
            final_monster_damage = int(monster_damage * monster_damage_multiplier)
            
            self.monster_hp = max(0, self.monster_hp - final_player_damage)
            player_data['hp'] = max(0, player_data['hp'] - final_monster_damage)
            if player_data['hp'] <= 0:
                player_data['alive'] = False
                
            action_text += f"**{pet['name']} attacks!** 🎲{player_roll} ({attack_multiplier:.1f}x) → **{final_player_damage} damage dealt!**\n"
            action_text += f"**{self.monster['name']} attacks back!** → **{final_monster_damage} damage received!**\n"
            
            player_data['charge'] = 1.0
            self.monster_charge_multiplier = 1.0
            
        elif player_action == "attack" and monster_action == "defend":
            player_damage = int(pet['attack'] * player_data['charge'] * attack_multiplier)
            monster_defense = self.monster.get('defense', 5)
            
            # Defense reduces damage by 50% but doesn't block completely
            reduced_damage = int(player_damage * 0.5)
            final_damage = max(1, reduced_damage)  # Ensure at least 1 damage
            
            self.monster_hp = max(0, self.monster_hp - final_damage)
            action_text += f"**{pet['name']} attacks!** 🎲{player_roll} ({attack_multiplier:.1f}x) → **{final_damage} damage through defense!**\n"
            action_text += f"**{self.monster['name']} defends!** → **Defense reduced damage!**\n"
            
            player_data['charge'] = 1.0
            
        elif player_action == "defend" and monster_action == "charge":
            # Defense has a 50% chance to prevent charging
            if random.random() < 0.5:
                # Defense prevents charging
                action_text += f"**{pet['name']} defends!** → **Prevents charging!**\n"
                action_text += f"**{self.monster['name']} tries to charge!** → **Charge interrupted!**\n"
            else:
                # Monster charge succeeds
                self.monster_charge_multiplier *= 2
                self.monster_charging = True
                action_text += f"**{pet['name']} defends!** → **Defense ineffective!**\n"
                action_text += f"⚡ **{self.monster['name']} charges up!** → **Next attack x{self.monster_charge_multiplier:.1f} (takes 1.5x damage)**\n"
            
        elif player_action == "charge" and monster_action == "defend":
            # Charge has a 75% chance to succeed against defense
            if random.random() < 0.75:
                # Player charge succeeds
                player_data['charge'] *= 2
                player_data['charging'] = True
                action_text += f"⚡ **{pet['name']} charges up!** → **Next attack x{player_data['charge']:.1f} (takes 1.5x damage)**\n"
                action_text += f"**{self.monster['name']} defends!** → **Defense failed!**\n"
            else:
                # Monster defense wins
                action_text += f"⚡ **{pet['name']} tries to charge!** → **Charge interrupted!**\n"
                action_text += f"**{self.monster['name']} defends!** → **Defense successful!**\n"
        
        return action_text

    def find_pvp_target(self, user_id):
        """Find PvP target (next player in turn order)"""
        alive_players = [pid for pid, data in self.player_data.items() if data['alive'] and pid != user_id]
        if alive_players:
            target_id = alive_players[self.current_turn_index % len(alive_players)]
            return self.player_data[target_id]
        return None

    def process_pvp_action(self, attacker_data, target_data, action):
        """Process PvP combat action using new d20 multiplier system"""
        action_text = ""
        
        # Single d20 roll for attack multiplier
        attacker_roll = self.roll_d20()
        attack_multiplier = self.calculate_attack_multiplier(attacker_roll)
        
        # Handle charging damage multiplier
        target_damage_multiplier = 1.5 if target_data['charging'] else 1.0
        if target_data['charging']:
            target_data['charging'] = False
        
        if action == "attack":
            base_damage = int(attacker_data['pet']['attack'] * attacker_data['charge'] * attack_multiplier)
            
            # Attack always hits with multiplier applied
            final_damage = int(base_damage * target_damage_multiplier)
            target_data['hp'] = max(0, target_data['hp'] - final_damage)
            if target_data['hp'] <= 0:
                target_data['alive'] = False
            action_text += f"**{attacker_data['pet']['name']} attacks {target_data['pet']['name']}!** 🎲{attacker_roll} ({attack_multiplier:.1f}x) → **{final_damage} damage dealt!**\n"
            
            attacker_data['charge'] = 1.0
            
        elif action == "defend":
            action_text += f"**{attacker_data['pet']['name']} takes a defensive stance!**\n"
            
        elif action == "charge":
            attacker_data['charge'] *= 2
            attacker_data['charging'] = True
            action_text += f"**{attacker_data['pet']['name']} charges up!** Next attack x{attacker_data['charge']:.1f} (takes 1.5x damage)\n"
        
        return action_text

    def check_victory_conditions(self):
        """Check if battle is over"""
        if self.battle_type in ["solo", "group"]:
            # Check if monster defeated
            if self.monster and self.monster_hp <= 0:
                self.battle_over = True
                return
            
            # Check if all players defeated
            alive_players = [data for data in self.player_data.values() if data['alive']]
            if not alive_players:
                self.battle_over = True
                return
                
        elif self.battle_type == "pvp":
            # Check if only one player remains
            alive_players = [data for data in self.player_data.values() if data['alive']]
            if len(alive_players) <= 1:
                self.battle_over = True
                return

    async def handle_victory(self):
        """Handle battle victory/defeat"""
        if self.battle_type == "energon_challenge":
            await self.handle_energon_challenge_victory()
        elif self.battle_type in ["solo", "group"]:
            await self.handle_monster_battle_victory()
        elif self.battle_type == "pvp":
            await self.handle_pvp_battle_victory()

    async def handle_monster_battle_victory(self):
        """Handle victory/defeat for monster battles"""
        alive_players = [data for data in self.player_data.values() if data['alive']]
        monster_defeated = self.monster and self.monster_hp <= 0
        
        if monster_defeated:
            # Victory
            total_xp = random.randint(100, 250) if self.battle_type == "solo" else random.randint(200, 400)
            
            # Get type and rarity emojis for victory message
            type_emoji = MONSTER_EMOJIS.get(self.monster.get('type', 'monster'), '🤖')
            rarity_emoji = MONSTER_EMOJIS.get(self.monster.get('rarity', 'common'), '⚪')
            
            embed = discord.Embed(
                title="🏆 Victory!",
                description=f"{'You have' if self.battle_type == 'solo' else 'The team has'} defeated {type_emoji} {rarity_emoji} {self.monster['name']}!",
                color=0x00ff00
            )
            
            rewards_text = ""
            loot_text = ""
            
            for data in self.player_data.values():
                if data['alive']:
                    xp_gain = total_xp // len(alive_players) if self.battle_type == "group" else total_xp
                    
                    # Calculate battle rewards
                    monster_rarity = self.monster.get('rarity', 'common')
                    battle_rewards = BattleSystem.get_battle_rewards(monster_rarity, True)
                    energon_gain = battle_rewards['energon']
                    
                    # Use add_experience to properly handle level-ups
                    leveled_up, level_gains = await self.pet_system.add_experience(data['user'].id, xp_gain, "battle")
                    if leveled_up and level_gains:
                        # Send level-up embed
                        asyncio.create_task(self.send_level_up_embed(data['user'], data['pet'], level_gains))
                    if self.battle_type == "group":
                        data['pet']['group_battles_won'] = data['pet'].get('group_battles_won', 0) + 1
                    else:
                        data['pet']['battles_won'] = data['pet'].get('battles_won', 0) + 1
                    data['pet']['battle_xp_earned'] = data['pet'].get('battle_xp_earned', 0) + xp_gain
                    data['pet']['total_battle_energon'] = data['pet'].get('total_battle_energon', 0) + energon_gain
                    happiness_gain = random.randint(15, 30)
                    data['pet']['happiness'] = min(100, data['pet']['happiness'] + happiness_gain)
                    
                    rewards_text += f"{data['user'].display_name}: +{xp_gain} XP, +{energon_gain} Energon\n"
                    
                    # Update global energon balance
                    try:
                        user_energon = await user_data_manager.get_energon_data(str(data['user'].id))
                        user_energon["energon"] += energon_gain
                        await user_data_manager.save_energon_data(str(data['user'].id), user_energon)
                    except Exception as e:
                        print(f"Error updating energon for user {data['user'].id}: {e}")
                    
                    # Loot drop chance based on monster type
                    enemy_type = self.monster.get('type', 'monster')
                    if enemy_type == "monster":
                        loot_chance = 33
                    elif enemy_type == "boss":
                        loot_chance = 66
                    elif enemy_type == "titan":
                        loot_chance = 99
                    else:
                        loot_chance = 33  # Default fallback
                    
                    loot_items = []
                    
                    # Check for perfect group victory against mythic
                    is_perfect_group_mythic = (
                        self.battle_type == "group" and 
                        len(self.participants) == 4 and
                        self.selected_rarity == "mythic" and
                        all(data['alive'] for data in self.player_data.values())
                    )
                    
                    if is_perfect_group_mythic:
                        # Guaranteed mythic loot for perfect group victory
                        mythic_loot = self.pet_system.get_random_transformation_item("mythic")
                        if mythic_loot:
                            loot_items.append(mythic_loot)
                        
                        # Bonus loot from lower rarity
                        lower_rarities = ["common", "uncommon", "rare", "epic", "legendary"]
                        bonus_rarity = random.choice(lower_rarities)
                        bonus_loot = self.pet_system.get_random_transformation_item(bonus_rarity)
                        if bonus_loot:
                            loot_items.append(bonus_loot)
                    else:
                        # Normal loot chance
                        if random.random() < loot_chance / 100:
                            loot_item = self.pet_system.get_random_transformation_item(self.selected_rarity)
                            if loot_item:
                                loot_items.append(loot_item)
                    
                    # Process loot for this player
                    for loot_item in loot_items:
                        loot_text += f"{data['user'].display_name}: **{loot_item['name']}** ({loot_item['type']})\n"
                    
                    if not loot_items:
                        loot_text += f"{data['user'].display_name}: No loot dropped\n"
                
                await user_data_manager.save_pet_data(str(data['user'].id), str(data['user']), data['pet'])
            
            embed.add_field(name="🎉 Rewards", value=rewards_text, inline=False)
            if loot_text:
                embed.add_field(name="💎 Loot Drops", value=loot_text, inline=False)
            
        else:
            # Defeat
            # Get type and rarity emojis for defeat message
            type_emoji = MONSTER_EMOJIS.get(self.monster.get('type', 'monster'), '🤖')
            rarity_emoji = MONSTER_EMOJIS.get(self.monster.get('rarity', 'common'), '⚪')
            
            embed = discord.Embed(
                title="💀 Defeat",
                description=f"{'You were' if self.battle_type == 'solo' else 'The team was'} defeated by {type_emoji} {rarity_emoji} {self.monster['name']}...",
                color=0xff0000
            )
            
            for data in self.player_data.values():
                xp_gain = random.randint(20, 50)
                
                # Calculate defeat rewards
                monster_rarity = self.monster.get('rarity', 'common')
                battle_rewards = BattleSystem.get_battle_rewards(monster_rarity, False)
                energon_gain = battle_rewards['energon']
                
                # Use add_experience to properly handle level-ups
                leveled_up, level_gains = await self.pet_system.add_experience(data['user'].id, xp_gain, "battle")
                if leveled_up and level_gains:
                    # Send level-up embed
                    asyncio.create_task(self.send_level_up_embed(data['user'], data['pet'], level_gains))
                
                if self.battle_type == "group":
                        data['pet']['group_battles_lost'] = data['pet'].get('group_battles_lost', 0) + 1
                else:
                        data['pet']['challenge_losses'] = data['pet'].get('challenge_losses', 0) + 1
                data['pet']['battle_xp_earned'] = data['pet'].get('battle_xp_earned', 0) + xp_gain
                data['pet']['total_battle_energon'] = data['pet'].get('total_battle_energon', 0) + energon_gain
                
                # Update global energon balance even on defeat
                try:
                    user_energon = await user_data_manager.get_energon_data(str(data['user'].id))
                    user_energon["energon"] += energon_gain
                    await user_data_manager.save_energon_data(str(data['user'].id), user_energon)
                except Exception as e:
                    print(f"Error updating energon for user {data['user'].id}: {e}")
                
                await user_data_manager.save_pet_data(str(data['user'].id), str(data['user']), data['pet'])
        
        await self.ctx.send(embed=embed)

    async def handle_pvp_battle_victory(self):
        """Handle PvP battle victory"""
        alive_players = [data for data in self.player_data.values() if data['alive']]
        
        if len(alive_players) == 1:
            winner = alive_players[0]
            embed = discord.Embed(
                title="🏆 Arena Champion!",
                description=f"{winner['user'].display_name}'s {winner['pet']['name']} is the champion!",
                color=0x00ff00
            )
            
            xp_award = random.randint(200, 400)
            energon_award = random.randint(75, 150)  # Standard PvP energon reward
            
            # Use add_experience to properly handle level-ups
            leveled_up, level_gains = await self.pet_system.add_experience(winner['user'].id, xp_award, "battle")
            if leveled_up and level_gains:
                # Send level-up embed
                asyncio.create_task(self.send_level_up_embed(winner['user'], winner['pet'], level_gains))
            winner['pet']['battle_xp_earned'] = winner['pet'].get('battle_xp_earned', 0) + xp_award
            winner['pet']['total_battle_energon'] = winner['pet'].get('total_battle_energon', 0) + energon_award
            winner['pet']['happiness'] = min(100, winner['pet'].get('happiness', 0) + random.randint(30, 50))
            
            # Track PvP wins based on battle type
            if hasattr(self, 'battle_type') and self.battle_type == "open_challenge":
                winner['pet']['open_challenge_wins'] = winner['pet'].get('open_challenge_wins', 0) + 1
            else:
                winner['pet']['challenge_wins'] = winner['pet'].get('challenge_wins', 0) + 1
            
            embed.add_field(name="🎉 Rewards", value=f"XP: +{xp_award}\nEnergon: +{energon_award}", inline=False)
            
            # Update global energon balance for winner
            try:
                user_energon = await user_data_manager.get_energon_data(str(winner['user'].id))
                user_energon["energon"] += energon_award
                await user_data_manager.save_energon_data(str(winner['user'].id), user_energon)
            except Exception as e:
                print(f"Error updating energon for winner {winner['user'].id}: {e}")
            
            # Handle losses for defeated players
            for data in self.player_data.values():
                if not data['alive'] and data != winner:
                    # Track PvP losses based on battle type
                    if hasattr(self, 'battle_type') and self.battle_type == "open_challenge":
                        data['pet']['open_challenge_losses'] = data['pet'].get('open_challenge_losses', 0) + 1
                    else:
                        data['pet']['challenge_losses'] = data['pet'].get('challenge_losses', 0) + 1
                    
        else:
            embed = discord.Embed(
                title="⚔️ Battle Draw",
                description="The battle ended in a draw!",
                color=0x808080
            )
        
        for data in self.player_data.values():
            await user_data_manager.save_pet_data(str(data['user'].id), str(data['user']), data['pet'])
        
        await self.ctx.send(embed=embed)

    async def handle_energon_challenge_victory(self):
        """Handle victory/defeat for energon challenges"""
        alive_players = [data for data in self.player_data.values() if data['alive']]
        monster_defeated = self.monster and self.monster_hp <= 0
        
        if monster_defeated and len(alive_players) == 1:
            winner = alive_players[0]
            
            # Calculate energon reward based on bet amount
            energon_reward = int(self.energon_bet * 2)  # Double the bet as reward
            
            embed = discord.Embed(
                title="💎 Energon Challenge Victory!",
                description=f"{winner['user'].display_name}'s {winner['pet']['name']} has won the energon challenge!",
                color=0x00ff00
            )
            
            # Award XP and energon
            xp_gain = random.randint(150, 300)
            # Use add_experience to properly handle level-ups
            leveled_up, level_gains = await self.pet_system.add_experience(winner['user'].id, xp_gain, "battle")
            if leveled_up and level_gains:
                # Send level-up embed
                asyncio.create_task(self.send_level_up_embed(winner['user'], winner['pet'], level_gains))
            winner['pet']['challenge_wins'] = winner['pet'].get('challenge_wins', 0) + 1
            winner['pet']['battle_xp_earned'] = winner['pet'].get('battle_xp_earned', 0) + xp_gain
            winner['pet']['challenge_xp_earned'] = winner['pet'].get('challenge_xp_earned', 0) + xp_gain
            winner['pet']['total_challenge_energon'] = winner['pet'].get('total_challenge_energon', 0) + energon_reward
            happiness_gain = random.randint(25, 40)
            winner['pet']['happiness'] = min(100, winner['pet']['happiness'] + happiness_gain)
            
            # Update global energon balance
            try:
                user_energon = await user_data_manager.get_energon_data(str(winner['user'].id))
                user_energon["energon"] += energon_reward
                await user_data_manager.save_energon_data(str(winner['user'].id), user_energon)
            except Exception as e:
                print(f"Error updating energon for winner {winner['user'].id}: {e}")
            
            embed.add_field(name="🎉 Rewards", value=f"XP: +{xp_gain}\nEnergon: +{energon_reward}", inline=False)
            
        else:
            # Defeat - lose the bet
            embed = discord.Embed(
                title="💀 Energon Challenge Failed",
                description="Your pet was defeated in the energon challenge...",
                color=0xff0000
            )
            
            # Deduct energon bet from user's global balance
            if hasattr(self, 'energon_bet') and self.energon_bet > 0:
                for data in self.player_data.values():
                    user_id = str(data['user'].id)
                    energon_data = await user_data_manager.get_energon_data(user_id)
                    current_energon = energon_data.get('energon', 0)
                    new_energon = max(0, current_energon - self.energon_bet)
                    energon_data['energon'] = new_energon
                    await user_data_manager.save_energon_data(user_id, energon_data)
            
            # Still award some XP for participation
            for data in self.player_data.values():
                xp_gain = random.randint(50, 100)
                # Use add_experience to properly handle level-ups
                leveled_up, level_gains = await self.pet_system.add_experience(data['user'].id, xp_gain, "battle")
                if leveled_up and level_gains:
                    # Send level-up embed
                    asyncio.create_task(self.send_level_up_embed(data['user'], data['pet'], level_gains))
                data['pet']['challenge_losses'] = data['pet'].get('challenge_losses', 0) + 1
                data['pet']['battle_xp_earned'] = data['pet'].get('battle_xp_earned', 0) + xp_gain
                data['pet']['challenge_xp_earned'] = data['pet'].get('challenge_xp_earned', 0) + xp_gain
        
        for data in self.player_data.values():
            await user_data_manager.save_pet_data(str(data['user'].id), str(data['user']), data['pet'])
        
        await self.ctx.send(embed=embed)

    async def send_level_up_embed(self, user, pet, level_gains):
        """Send level-up embed for battle XP gains"""
        embed = discord.Embed(
            title="🎉 Level Up!",
            description=f"{user.display_name}'s **{pet['name']}** has leveled up!",
            color=0x00ff00
        )
        
        embed.add_field(
            name="Level Progression",
            value=f"**Previous Level:** {level_gains['previous_level']}\n"
                  f"**New Level:** {level_gains['new_level']}\n"
                  f"**XP Required:** {level_gains['xp_required']} XP\n"
                  f"**Stat Gains:**\n"
                  f"• Attack: +{level_gains['stat_gains']['attack']}\n"
                  f"• Defense: +{level_gains['stat_gains']['defense']}\n"
                  f"• Health: +{level_gains['stat_gains']['health']}",
            inline=False
        )
        
        embed.set_footer(text="Keep battling to reach new heights! ⚔️")
        
        try:
            await self.ctx.send(embed=embed)
        except Exception as e:
            print(f"Error sending level-up embed: {e}")

    @discord.ui.button(label="Join Battle", style=discord.ButtonStyle.green, emoji="⚔️")
    async def join_battle(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle joining battle (for group battles)"""
        if self.battle_type != "group":
            await interaction.response.send_message("❌ This is not a group battle!", ephemeral=True)
            return
            
        if self.battle_started:
            await interaction.response.send_message("❌ Battle has already started!", ephemeral=True)
            return
            
        if interaction.user.id in self.player_data:
            await interaction.response.send_message("❌ You're already in this battle!", ephemeral=True)
            return
            
        if len(self.participants) >= self.max_participants:
            await interaction.response.send_message("❌ Battle is at maximum capacity!", ephemeral=True)
            return

        # Check Cybertronian role
        cybertronian_roles = [discord.utils.get(interaction.user.roles, name=role) for role in ['Autobot', 'Decepticon', 'Maverick', 'Cybertronian_Citizen']]
        if not any(role in interaction.user.roles for role in cybertronian_roles if role):
            await interaction.response.send_message("❌ Only Cybertronian Citizens can battle!", ephemeral=True)
            return

        # Check pet and energy
        pet = await self.pet_system.get_user_pet(str(interaction.user.id))
        if not pet:
            await interaction.response.send_message("❌ You need a pet to battle! Use `/get_pet`", ephemeral=True)
            return
            
        if pet['energy'] < 10:
            await interaction.response.send_message("❌ Your pet needs more energy!", ephemeral=True)
            return

        # Add participant
        self.participants.append((interaction.user, pet))
        max_hp = pet['energy'] + pet['maintenance']
        self.player_data[interaction.user.id] = {
            'user': interaction.user,
            'pet': pet,
            'hp': max_hp,
            'max_hp': max_hp,
            'charge': 1.0,
            'alive': True,
            'last_action': None
        }
        
        # Deduct energy
        pet['energy'] -= 10
        await user_data_manager.save_pet_data(str(interaction.user.id), str(interaction.user), pet)
        
        await interaction.response.edit_message(embed=self.build_join_embed(), view=self)

    @discord.ui.button(label="Start Battle", style=discord.ButtonStyle.red, emoji="⚔️")
    async def start_battle(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Start the battle"""
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Only the battle initiator can start!", ephemeral=True)
            return
            
        if self.battle_type == "group" and len(self.participants) < 2:
            await interaction.response.send_message("❌ Need at least 2 players for group battle!", ephemeral=True)
            return

        self.battle_started = True
        
        # Switch to battle view
        battle_view = UnifiedBattleActionView(self)
        await interaction.response.edit_message(embed=self.build_battle_embed(), view=battle_view)

class UnifiedBattleActionView(discord.ui.View):
    def __init__(self, battle_view):
        super().__init__(timeout=300)
        self.battle_view = battle_view

    def get_current_player(self):
        """Get the current player"""
        return self.battle_view.get_current_player()

    def update_buttons(self):
        """Update button states based on current turn"""
        current_player = self.get_current_player()
        if not current_player:
            return

        # Enable all buttons for current player
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = False

    @discord.ui.button(label="Attack", style=discord.ButtonStyle.red, emoji="⚔️")
    async def attack_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Attack action"""
        current_player = self.get_current_player()
        if not current_player or interaction.user.id != current_player['user'].id:
            await interaction.response.send_message("❌ It's not your turn!", ephemeral=True)
            return

        action_text = await self.battle_view.process_turn("attack", interaction.user.id)
        
        if self.battle_view.battle_over:
            await self.battle_view.handle_victory()
            await interaction.message.edit(embed=self.battle_view.build_battle_embed(action_text), view=None)
        else:
            self.update_buttons()
            await interaction.response.edit_message(embed=self.battle_view.build_battle_embed(action_text), view=self)

    @discord.ui.button(label="Defend", style=discord.ButtonStyle.blurple, emoji="🛡️")
    async def defend_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Defend action"""
        current_player = self.get_current_player()
        if not current_player or interaction.user.id != current_player['user'].id:
            await interaction.response.send_message("❌ It's not your turn!", ephemeral=True)
            return

        action_text = await self.battle_view.process_turn("defend", interaction.user.id)
        
        if self.battle_view.battle_over:
            await self.battle_view.handle_victory()
            await interaction.message.edit(embed=self.battle_view.build_battle_embed(action_text), view=None)
        else:
            self.update_buttons()
            await interaction.response.edit_message(embed=self.battle_view.build_battle_embed(action_text), view=self)

    @discord.ui.button(label="Charge", style=discord.ButtonStyle.green, emoji="⚡")
    async def charge_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Charge action"""
        current_player = self.get_current_player()
        if not current_player or interaction.user.id != current_player['user'].id:
            await interaction.response.send_message("❌ It's not your turn!", ephemeral=True)
            return

        action_text = await self.battle_view.process_turn("charge", interaction.user.id)
        
        if self.battle_view.battle_over:
            await self.battle_view.handle_victory()
            await interaction.message.edit(embed=self.battle_view.build_battle_embed(action_text), view=None)
        else:
            self.update_buttons()
            await interaction.response.edit_message(embed=self.battle_view.build_battle_embed(action_text), view=self)

class UnifiedBattleSetupView(discord.ui.View):
    def __init__(self, ctx, pet, pet_system, battle_type="solo", energon_bet=None, use_current=None):
        super().__init__()
        self.ctx = ctx
        self.pet = pet
        self.pet_system = pet_system
        self.battle_type = battle_type
        self.energon_bet = energon_bet
        self.use_current = use_current
        self.message = None
        self.selected_enemy_type = None
        self.selected_rarity = None
        
    def save_challenge_to_game_state(self, challenge_data):
        """Save challenge data to game_state.json"""
        try:
            from Systems.Energon.energon_system import EnergonGameManager
            
            game_manager = EnergonGameManager()
            game_manager.load_game_state()
            
            # Save challenge data with channel ID as key
            channel_id = str(self.ctx.channel.id)
            if channel_id not in game_manager.challenges:
                game_manager.challenges[channel_id] = []
            
            # Add metadata
            challenge_data.update({
                "timestamp": discord.utils.utcnow().isoformat(),
                "status": "active"
            })
            
            game_manager.challenges[channel_id].append(challenge_data)
            game_manager.save_game_state()
            
        except Exception as e:
            print(f"Error saving challenge to game state: {e}")

    @discord.ui.select(
        placeholder="Choose enemy type...",
        options=[
            discord.SelectOption(label="Monster", value="monster", description="Standard enemy", emoji="🤖"),
            discord.SelectOption(label="Boss", value="boss", description="Enhanced enemy", emoji="👹"),
            discord.SelectOption(label="Titan", value="titan", description="Massive enemy", emoji="👑")
        ]
    )
    async def enemy_type_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected_enemy_type = select.values[0]
        await interaction.response.defer()

    @discord.ui.select(
        placeholder="Choose rarity...",
        options=[
            discord.SelectOption(label="Common", value="common", description="Basic enemies", emoji="⚪"),
            discord.SelectOption(label="Uncommon", value="uncommon", description="Stronger enemies", emoji="🟢"),
            discord.SelectOption(label="Rare", value="rare", description="Powerful enemies", emoji="🔵"),
            discord.SelectOption(label="Epic", value="epic", description="Very powerful enemies", emoji="🟣"),
            discord.SelectOption(label="Legendary", value="legendary", description="Extremely powerful enemies", emoji="🟠"),
            discord.SelectOption(label="Mythic", value="mythic", description="Ultimate enemies", emoji="🔴")
        ]
    )
    async def rarity_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected_rarity = select.values[0]
        await interaction.response.defer()

    @discord.ui.button(label="Create Battle", style=discord.ButtonStyle.green, emoji="⚔️")
    async def create_battle(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Skip dropdown checks for energon challenges
        if self.battle_type not in ["pvp", "energon_challenge"] and (self.selected_enemy_type is None or self.selected_rarity is None):
            await interaction.response.send_message("❌ Please select both enemy type and rarity!", ephemeral=True)
            return

        # Create monster for non-PvP battles
        monster = None
        if self.battle_type in ["solo", "group"]:
            try:
                # Ensure monsters are loaded
                if not self.pet_system.monsters_data:
                    self.pet_system.load_cyberchronicles_monsters()
                
                # Get the appropriate enemy collection based on type
                if self.selected_enemy_type == "monster":
                    enemies = self.pet_system.monsters_data
                elif self.selected_enemy_type == "boss":
                    enemies = self.pet_system.bosses_data
                elif self.selected_enemy_type == "titan":
                    enemies = self.pet_system.titans_data
                else:
                    enemies = self.pet_system.monsters_data
                
                # Get monsters by rarity - enemies is a dict with rarity as keys
                matching_enemies = enemies.get(self.selected_rarity, [])
                
                if matching_enemies:
                    monster = random.choice(matching_enemies)
                    # Ensure attack field is properly formatted for battle system
                    if "attack" in monster:
                        attack_value = monster["attack"]
                        monster["attack_min"] = attack_value
                        monster["attack_max"] = int(attack_value * 1.2)
                    else:
                        # Default attack values if not specified
                        monster["attack_min"] = 10
                        monster["attack_max"] = 15
                    self.selected_difficulty = self.selected_rarity
                else:
                    # Fallback to generic enemy if no matching enemies found
                    base_health = {
                        "common": 100, "uncommon": 150, "rare": 200, "epic": 300, "legendary": 400, "mythic": 500
                    }.get(self.selected_rarity, 100)
                    
                    base_attack = {
                        "common": 8, "uncommon": 12, "rare": 16, "epic": 22, "legendary": 28, "mythic": 35
                    }.get(self.selected_rarity, 8)

                    # Scale based on enemy type
                    if self.selected_enemy_type == "boss":
                        base_health *= 2.5
                        base_attack *= 1.8
                    elif self.selected_enemy_type == "titan":
                        base_health *= 5
                        base_attack *= 2.5

                    monster = {
                        "name": f"{self.selected_rarity.title()} {self.selected_enemy_type.title()}",
                        "health": int(base_health),
                        "attack_min": int(base_attack),
                        "attack_max": int(base_attack * 1.5),
                        "type": self.selected_enemy_type,
                        "rarity": self.selected_rarity
                    }

            except Exception as e:
                print(f"Error loading monster data: {e}")
                # Fallback monster if JSON file doesn't exist or has errors
                base_health = {
                    "common": 100, "uncommon": 150, "rare": 200, "epic": 300, "legendary": 400, "mythic": 500
                }.get(self.selected_rarity, 100)
                
                base_attack = {
                    "common": 8, "uncommon": 12, "rare": 16, "epic": 22, "legendary": 28, "mythic": 35
                }.get(self.selected_rarity, 8)

                if self.selected_enemy_type == "boss":
                    base_health *= 2.5
                    base_attack *= 1.8
                elif self.selected_enemy_type == "titan":
                    base_health *= 5
                    base_attack *= 2.5

                monster = {
                    "name": f"{self.selected_rarity.title()} {self.selected_enemy_type.title()}",
                    "health": int(base_health),
                    "attack_min": int(base_attack),
                    "attack_max": int(base_attack * 1.5),
                    "type": self.selected_enemy_type,
                    "rarity": self.selected_rarity
                }
            
            # Store monster rarity for battle rewards - using rarity directly now
        elif self.battle_type == "energon_challenge":
            # For energon challenges, create a PvP-style battle
            monster = {
                "name": "Energon Challenge",
                "health": 100,  # Standard challenge health
                "attack_min": 15,
                "attack_max": 25,
                "type": "challenge"
            }
            # Energon challenges use direct rarity-based rewards

        # Save challenge data for energon challenges and PvP
        if self.battle_type in ["energon_challenge", "pvp"]:
            challenge_data = {
                "type": self.battle_type,
                "enemy_type": self.selected_enemy_type,
                "enemy_rarity": self.selected_rarity,
                "monster": monster if self.battle_type == "energon_challenge" else None,
                "energon_bet": self.energon_bet,
                "use_current": self.use_current,
                "channel_id": str(self.ctx.channel.id),
                "guild_id": str(self.ctx.guild.id) if self.ctx.guild else None,
                "participants": [{
                    "user_id": str(self.ctx.author.id),
                    "user_name": self.ctx.author.display_name,
                    "pet_name": self.pet['name'],
                    "pet_level": self.pet['level']
                }],
                "status": "active",
                "created_at": discord.utils.utcnow().isoformat(),
                "initiator": str(self.ctx.author.id),
                "initiator_name": self.ctx.author.display_name
            }
            self.save_challenge_to_game_state(challenge_data)
            
        # Create unified battle
        participants = [(self.ctx.author, self.pet)]
        view = await UnifiedBattleView.create_async(self.ctx, self.pet_system, self.battle_type, participants, monster, self.selected_difficulty, energon_bet=self.energon_bet)
        
        if self.battle_type in ["group", "energon_challenge"]:
            embed = view.build_join_embed()
        else:
            # For solo and PvP, start immediately
            view.battle_started = True
            action_view = UnifiedBattleActionView(view)
            embed = view.build_battle_embed()
            view = action_view
        
        await interaction.response.edit_message(embed=embed, view=view)
        view.message = self.message

def get_player_stats(user_id):
    """Get player stats from energon system"""
    try:
        from Systems.Energon.energon_system import get_player_stats as energon_get_stats
        return energon_get_stats(str(user_id))
    except ImportError as e:
        print(f"Error importing energon stats: {e}")
        return None
    except Exception as e:
        print(f"Error getting player stats: {e}")
        return None

def save_energon_game_state():
    """Save energon game state"""
    try:
        from Systems.Energon.energon_system import save_energon_game_state as energon_save
        energon_save()
    except ImportError as e:
        print(f"Error importing energon save: {e}")
    except Exception as e:
        print(f"Error saving energon game state: {e}")  

# Simple setup function for pet system core
async def setup(bot_instance):
    """Async setup function for pet system core functionality"""
    bot_instance.pet_system = PetSystem(bot_instance)
    print("Pet system core loaded successfully")


# Export key components
__all__ = [
    'PetSystem',
    'LEVEL_THRESHOLDS',
    'PET_STAGES',
    'STAGE_EMOJIS',
    'get_stage_emoji',
    'MISSION_TYPES',
    'MISSION_DIFFICULTIES',
    'BATTLE_DIFFICULTY_MAP',
    'AUTOBOT_PET_NAMES',
    'DECEPTICON_PET_NAMES',
    'PetStatusView'
]