import json
import random
import asyncio
import math
import uuid
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import google.generativeai as genai
import discord
from discord.ext import commands
from discord import app_commands

# Import UserDataManager - optimized for bot integration
import sys
import os
from pathlib import Path

# Import the global user_data_manager instance
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from user_data_manager import user_data_manager

# Import battle system for dynamic enemy generation
from RPG.rpg_battle_system import RPGUnifiedBattleView

@dataclass
class Stats:
    ATT: int = 10  # Attack
    DEF: int = 10  # Defense
    DEX: int = 10  # Dexterity
    INT: int = 10  # Intelligence (replacing CHA split)
    CHA: int = 10  # Charisma
    HP: int = 100  # Health Points

@dataclass
class CombatRecord:
    monsters_defeated: Dict[str, int] = None
    monsters_lost_to: Dict[str, int] = None
    bosses_defeated: Dict[str, int] = None
    bosses_lost_to: Dict[str, int] = None
    titans_defeated: Dict[str, int] = None
    titans_lost_to: Dict[str, int] = None
    total_wins: int = 0
    total_losses: int = 0
    total_damage_dealt: int = 0
    
    def __post_init__(self):
        if self.monsters_defeated is None:
            self.monsters_defeated = {}
        if self.monsters_lost_to is None:
            self.monsters_lost_to = {}
        if self.bosses_defeated is None:
            self.bosses_defeated = {}
        if self.bosses_lost_to is None:
            self.bosses_lost_to = {}
        if self.titans_defeated is None:
            self.titans_defeated = {}
        if self.titans_lost_to is None:
            self.titans_lost_to = {}

@dataclass
class Character:
    user_id: str
    name: str
    faction: str
    class_type: str
    level: int = 1
    experience: int = 0
    base_stats: Stats = None
    beast_modes: List[str] = None
    transformations: List[str] = None
    weapons: List[str] = None
    armor: List[str] = None
    characters: List[str] = None
    equipped_character: str = None
    equipped_transformation: str = None
    equipped_beast_mode: str = None
    equipped_weapons: List[str] = None
    equipped_armor: str = None
    energon_earned: int = 0
    combat_record: CombatRecord = None
    current_health: int = 0
    max_health: int = 0
    
    def __post_init__(self):
        if self.base_stats is None:
            self.base_stats = Stats()
        if self.beast_modes is None:
            self.beast_modes = []
        if self.transformations is None:
            self.transformations = []
        if self.weapons is None:
            self.weapons = []
        if self.armor is None:
            self.armor = []
        if self.characters is None:
            self.characters = []
        if self.equipped_weapons is None:
            self.equipped_weapons = []
        if self.combat_record is None:
            self.combat_record = CombatRecord()


class FirstReactView(discord.ui.View):
    """View for group events where the first player to react makes the decision for the party"""
    
    def __init__(self, ctx, event_data, participants):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.event_data = event_data
        self.participants = participants
        self.decision_made = False
        self.chosen_action = None
        self.decision_maker = None
        
    def create_event_embed(self):
        """Create an embed for the group event"""
        embed = discord.Embed(
            title=f"🤖 {self.event_data['name']}",
            description=self.event_data['description'],
            color=0x0099ff
        )
        
        # Add choices
        choices_text = ""
        for action_key, choice_data in self.event_data['choices'].items():
            choices_text += f"**{action_key.title()}**: {choice_data['description']}\n"
        
        embed.add_field(
            name="🎯 Available Actions",
            value=choices_text,
            inline=False
        )
        
        # Add participants
        participant_names = [f"{user.display_name} ({character.name})" for user, character in self.participants]
        embed.add_field(
            name="👥 Party Members",
            value="\n".join(participant_names),
            inline=False
        )
        
        embed.set_footer(text="⚡ First player to react chooses the action for the entire party!")
        return embed
        
    async def handle_decision(self, interaction: discord.Interaction, action: str):
        """Handle the first player's decision"""
        if self.decision_made:
            await interaction.response.send_message("❌ A decision has already been made!", ephemeral=True)
            return
            
        self.decision_made = True
        self.chosen_action = action
        self.decision_maker = interaction.user
        
        # Get the chosen action data
        action_data = self.event_data['choices'][action]
        
        # Create response embed
        embed = discord.Embed(
            title=f"🎯 Decision Made: {action.title()}",
            description=f"**{interaction.user.display_name}** has chosen **{action.title()}** for the party!",
            color=0x00ff00
        )
        
        embed.add_field(
            name="Chosen Action",
            value=action_data['description'],
            inline=False
        )
        
        embed.add_field(
            name="Next Steps",
            value="Processing the outcome based on your party's collective skills...",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
        
        # Stop the view
        self.stop()
        
    @discord.ui.button(label="Attack", style=discord.ButtonStyle.red, emoji="⚔️")
    async def attack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_decision(interaction, "attack")
        
    @discord.ui.button(label="Defense", style=discord.ButtonStyle.blurple, emoji="🛡️")
    async def defense_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_decision(interaction, "defense")
        
    @discord.ui.button(label="Dexterity", style=discord.ButtonStyle.green, emoji="🏃")
    async def dexterity_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_decision(interaction, "dexterity")
        
    @discord.ui.button(label="Intelligence", style=discord.ButtonStyle.grey, emoji="🧠")
    async def intelligence_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_decision(interaction, "intelligence")
        
    @discord.ui.button(label="Charisma", style=discord.ButtonStyle.green, emoji="💬")
    async def charisma_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_decision(interaction, "charisma")
        
    async def on_timeout(self):
        """Handle timeout if no one reacts"""
        if not self.decision_made:
            try:
                embed = discord.Embed(
                    title="⏰ Event Timed Out",
                    description="No one made a decision in time. The opportunity passes...",
                    color=0xff0000
                )
                await self.message.edit(embed=embed, view=None)
            except:
                pass

class TransformersAIDungeonMaster:
    """
    AI Dungeon Master for Transformers RPG that dynamically generates stories
    by pulling from JSON files containing enemies, events, story segments, and loot.
    Maintains narrative continuity and can regenerate events with same parameters.
    """
    
    def __init__(self, api_key: str = None):
        # Configure Gemini API
        if api_key:
            genai.configure(api_key=api_key)
        
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Initialize data containers (lazy loading)
        self.monsters_and_bosses = {}
        self.story_segments = {}
        self.random_events = {}
        self.transformation_items = {}
        
        # Lazy loading flags
        self._monsters_loaded = False
        self._story_loaded = False
        self._events_loaded = False
        self._items_loaded = False
        
        # RPG System functionality
        self.characters: Dict[str, Character] = {}
        self.base_stats_config = {
            "autobot": {
                # Heroic Autobots - 5 in 2 primary stats, 5 distributed among remaining 3
                "warrior": Stats(ATT=5, DEF=5, DEX=2, INT=1, CHA=2, HP=135),      # Noble protector
                "scientist": Stats(ATT=1, DEF=2, DEX=2, INT=5, CHA=5, HP=110),   # Brilliant inventor
                "engineer": Stats(ATT=1, DEF=5, DEX=1, INT=5, CHA=3, HP=125),     # Master builder
                "mariner": Stats(ATT=5, DEF=5, DEX=2, INT=1, CHA=2, HP=130),     # Sea guardian
                "commander": Stats(ATT=2, DEF=1, DEX=1, INT=5, CHA=5, HP=120),    # Inspiring leader
                "medic": Stats(ATT=1, DEF=2, DEX=1, INT=5, CHA=5, HP=115),      # Compassionate healer
                "scout": Stats(ATT=2, DEF=2, DEX=5, INT=1, CHA=5, HP=110),       # Noble scout
                "seeker": Stats(ATT=5, DEF=1, DEX=5, INT=2, CHA=2, HP=125)      # Aerial ace
            },
            "decepticon": {
                # Villainous Decepticons - dark and ruthless themed
                "warrior": Stats(ATT=5, DEF=5, DEX=3, INT=1, CHA=1, HP=140),      # Brutal enforcer - pure combat focus
                "scientist": Stats(ATT=1, DEF=2, DEX=2, INT=5, CHA=5, HP=100),   # Mad scientist - intelligence for schemes, charisma for manipulation
                "engineer": Stats(ATT=3, DEF=5, DEX=1, INT=5, CHA=1, HP=125),     # Weapons master - defense and intelligence for destruction
                "mariner": Stats(ATT=5, DEF=2, DEX=5, INT=1, CHA=2, HP=130),     # Naval raider - attack and dexterity for piracy
                "commander": Stats(ATT=5, DEF=1, DEX=2, INT=5, CHA=2, HP=115),    # Ruthless leader - attack and intelligence for domination
                "medic": Stats(ATT=1, DEF=1, DEX=2, INT=5, CHA=6, HP=105),      # Sinister experimenter - intelligence and charisma for twisted experiments
                "scout": Stats(ATT=3, DEF=1, DEX=5, CHA=5, INT=1, HP=110),       # Sneaky infiltrator - dexterity and charisma for deception
                "seeker": Stats(ATT=5, DEF=1, DEX=5, INT=2, CHA=1, HP=120)      # Aerial assassin - attack and dexterity for lethal strikes
            }
        }
        
        # Cache for story continuity
        self.story_cache = {}
        self.last_encounter = None
        self.last_event = None
        
        # Set up logging
        self.logger = logging.getLogger('rpg_system')
        
    async def __aenter__(self):
        """Async context manager entry for bot integration"""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit for cleanup"""
        await self.cleanup()
        
    async def cleanup(self):
        """Cleanup resources and save any pending data"""
        try:
            # Save all cached characters
            for user_id, character in self.characters.items():
                await self._save_character_async(user_id, character)
            self.logger.info("RPG system cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during RPG system cleanup: {e}")
            
    async def _save_character_async(self, user_id: str, character: Character, username: str = None) -> bool:
        """Async version of character saving for bot integration"""
        try:
            character_dict = {
                "user_id": character.user_id,
                "name": character.name,
                "faction": character.faction,
                "class_type": character.class_type,
                "level": character.level,
                "experience": character.experience,
                "base_stats": asdict(character.base_stats),
                "beast_modes": character.beast_modes,
                "transformations": character.transformations,
                "weapons": character.weapons,
                "armor": character.armor,
                "characters": character.characters,
                "equipped_character": character.equipped_character,
                "equipped_transformation": character.equipped_transformation,
                "equipped_beast_mode": character.equipped_beast_mode,
                "equipped_weapons": character.equipped_weapons,
                "equipped_armor": character.equipped_armor,
                "energon_earned": character.energon_earned,
                "combat_record": asdict(character.combat_record),
                "current_health": character.current_health,
                "max_health": character.max_health
            }
            return await user_data_manager.save_rpg_character(user_id, username or f"user_{user_id}", character_dict)
        except Exception as e:
            self.logger.error(f"Error saving character {character.name}: {e}")
            return False
        
    def _load_json(self, filename: str) -> Dict[str, Any]:
        """Load JSON file from the unified data storage"""
        import asyncio
        
        async def _load_json_async():
            try:
                # Map RPG data files to user_data_manager methods
                filename_map = {
                    'monsters_and_bosses.json': 'get_monsters_and_bosses_data',
                    'story_segments.json': 'get_story_segments',
                    'random_events.json': 'get_random_events',
                    'transformation_items.json': 'get_transformation_items_data'
                }
                
                if filename in filename_map:
                    method_name = filename_map[filename]
                    method = getattr(user_data_manager, method_name)
                    return await method()
                else:
                    # Fallback for custom files
                    file_path = user_data_manager._file_paths['bot_logs'].parent / "rpg_data" / filename
                    return await user_data_manager._load_json_optimized(file_path, {}, lazy=True)
                    
            except Exception as e:
                print(f"Warning: {filename} not found or error loading: {e}")
                return {}
        
        return asyncio.run(_load_json_async())

    def get_user_characters(self, user_id: str, username: str = None) -> List[Character]:
        """Get all characters for a user using unified data storage."""
        import asyncio
        
        async def _get_characters():
            characters_data = await user_data_manager.get_all_rpg_characters(user_id, username)
            characters = []
            
            for char_data in characters_data:
                # Convert nested dicts to dataclasses
                if 'base_stats' in char_data:
                    char_data['base_stats'] = Stats(**char_data['base_stats'])
                if 'combat_record' in char_data:
                    char_data['combat_record'] = CombatRecord(**char_data['combat_record'])
                
                character = Character(**char_data)
                characters.append(character)
            
            return sorted(characters, key=lambda x: x.name)
        
        # Run async function synchronously
        return asyncio.run(_get_characters())
        
    async def get_user_characters_async(self, user_id: str, username: str = None) -> List[Character]:
        """Async version of get_user_characters for bot integration"""
        characters_data = await user_data_manager.get_all_rpg_characters(user_id, username)
        characters = []
        
        for char_data in characters_data:
            # Convert nested dicts to dataclasses
            if 'base_stats' in char_data:
                char_data['base_stats'] = Stats(**char_data['base_stats'])
            if 'combat_record' in char_data:
                char_data['combat_record'] = CombatRecord(**char_data['combat_record'])
            
            character = Character(**char_data)
            characters.append(character)
        
        return sorted(characters, key=lambda x: x.name)

    def delete_character(self, user_id: str, character_name: str, username: str = None) -> bool:
        """Delete a character for a user using unified data storage."""
        import asyncio
        
        async def _delete_character():
            # Remove from memory cache
            if user_id in self.characters and self.characters[user_id].name == character_name:
                del self.characters[user_id]
            
            # Delete from unified storage
            return await user_data_manager.delete_rpg_character(user_id, username, character_name)
        
        # Run async function synchronously
        return asyncio.run(_delete_character())

    def has_cybertronian_role(self, member: discord.Member) -> bool:
        """Check if a member has any Cybertronian role."""
        cybertronian_roles = ['Autobot', 'Decepticon', 'Maverick', 'Cybertronian_Citizen']
        return any(role.name in cybertronian_roles for role in member.roles)

    # RPG System methods
    def create_character(self, user_id: str, name: str, faction: str, class_type: str, username: str = None) -> Character:
        """Create a new character with battle-ready stats using unified data storage."""
        import asyncio
        
        # Check if user already has a character (1 character per user limit)
        existing_character = self.get_character(user_id)
        if existing_character:
            raise ValueError(f"User already has a character: {existing_character.name}")
        
        # Load from storage to double-check
        loaded_character = self.load_character(user_id, username=username)
        if loaded_character:
            self.characters[user_id] = loaded_character  # Update memory cache
            raise ValueError(f"User already has a character: {loaded_character.name}")
        
        # Get base stat template for the class
        base_template = self.base_stats_config.get(faction.lower(), {}).get(class_type.lower(), Stats())
        
        # Create starting stats based on class template
        starting_stats = Stats(
            ATT=base_template.ATT + 5,  # Base + bonus to be combat ready
            DEF=base_template.DEF + 5,
            DEX=base_template.DEX + 5,
            INT=base_template.INT + 5,
            CHA=base_template.CHA + 5,
            HP=base_template.HP + 50     # Extra health for battle readiness
        )
        
        character = Character(
            user_id=user_id,
            name=name,
            faction=faction.lower(),
            class_type=class_type.lower(),
            base_stats=starting_stats,
            current_health=starting_stats.HP,
            max_health=starting_stats.HP,
            equipped_weapons=[],  # Initialize empty equipment slots
            equipped_armor=None
        )
        
        # Store in memory cache immediately
        self.characters[user_id] = character
        return character

    async def create_character_async(self, user_id: str, name: str, faction: str, class_type: str, username: str = None) -> Character:
        """Async version of create_character that properly saves to storage."""
        # Check if user already has a character (1 character per user limit)
        existing_character = self.get_character(user_id)
        if existing_character:
            raise ValueError(f"User already has a character: {existing_character.name}")
        
        # Load from storage to double-check
        loaded_character = await self.load_character_async(user_id, username=username)
        if loaded_character:
            self.characters[user_id] = loaded_character  # Update memory cache
            raise ValueError(f"User already has a character: {loaded_character.name}")
        
        # Get base stat template for the class
        base_template = self.base_stats_config.get(faction.lower(), {}).get(class_type.lower(), Stats())
        
        # Create starting stats based on class template
        starting_stats = Stats(
            ATT=base_template.ATT + 5,  # Base + bonus to be combat ready
            DEF=base_template.DEF + 5,
            DEX=base_template.DEX + 5,
            INT=base_template.INT + 5,
            CHA=base_template.CHA + 5,
            HP=base_template.HP + 50     # Extra health for battle readiness
        )
        
        character = Character(
            user_id=user_id,
            name=name,
            faction=faction.lower(),
            class_type=class_type.lower(),
            base_stats=starting_stats,
            current_health=starting_stats.HP,
            max_health=starting_stats.HP,
            equipped_weapons=[],  # Initialize empty equipment slots
            equipped_armor=None
        )
        
        # Store in memory cache
        self.characters[user_id] = character
        
        # Save to unified storage
        character_dict = {
            "user_id": character.user_id,
            "name": character.name,
            "faction": character.faction,
            "class_type": character.class_type,
            "level": character.level,
            "experience": character.experience,
            "base_stats": asdict(character.base_stats),
            "beast_modes": character.beast_modes,
            "transformations": character.transformations,
            "weapons": character.weapons,
            "armor": character.armor,
            "characters": character.characters,
            "equipped_character": character.equipped_character,
            "equipped_transformation": character.equipped_transformation,
            "equipped_beast_mode": character.equipped_beast_mode,
            "equipped_weapons": character.equipped_weapons,
            "equipped_armor": character.equipped_armor,
            "energon_earned": character.energon_earned,
            "combat_record": asdict(character.combat_record),
            "current_health": character.current_health,
            "max_health": character.max_health
        }
        
        await user_data_manager.save_rpg_character(user_id, username, character_dict)
        return character

    def save_character_by_name(self, user_id: str, name: str, character: Character, username: str = None) -> bool:
        """Save character data to unified data storage."""
        import asyncio

        async def _save_character():
            # Update memory cache
            self.characters[user_id] = character
            
            # Convert Character to dict for storage
            character_dict = {
                "user_id": character.user_id,
                "name": character.name,
                "faction": character.faction,
                "class_type": character.class_type,
                "level": character.level,
                "experience": character.experience,
                "base_stats": asdict(character.base_stats),
                "beast_modes": character.beast_modes,
                "transformations": character.transformations,
                "weapons": character.weapons,
                "armor": character.armor,
                "characters": character.characters,
                "equipped_character": character.equipped_character,
                "equipped_transformation": character.equipped_transformation,
                "equipped_beast_mode": character.equipped_beast_mode,
                "equipped_weapons": character.equipped_weapons,
                "equipped_armor": character.equipped_armor,
                "energon_earned": character.energon_earned,
                "combat_record": asdict(character.combat_record),
                "current_health": character.current_health,
                "max_health": character.max_health
            }
            
            return await user_data_manager.save_rpg_character(user_id, username, character_dict)

        return asyncio.run(_save_character())
        
    async def save_character_by_name_async(self, user_id: str, name: str, character: Character, username: str = None) -> bool:
        """Async version of save_character_by_name for bot integration"""
        self.characters[user_id] = character
        return await self._save_character_async(user_id, character, username)

    def get_character(self, user_id: str) -> Optional[Character]:
        """Get character by user ID from memory cache."""
        return self.characters.get(user_id)

    def save_character(self, user_id: str, username: str = None) -> bool:
        """Save character data to unified storage using character name."""
        if user_id not in self.characters:
            return False
        
        character = self.characters[user_id]
        return self.save_character_by_name(user_id, character.name, character, username)

    async def save_character_async(self, user_id: str, username: str = None) -> bool:
        """Async version of save_character for bot integration."""
        if user_id not in self.characters:
            return False
        
        character = self.characters[user_id]
        return await self.save_character_by_name_async(user_id, character.name, character, username)

    def load_character(self, user_id: str, name: str = None, username: str = None) -> Optional[Character]:
        """Load character data from unified storage by user_id and optionally name."""
        import asyncio
        
        async def _load_character():
            if name:
                # Load specific character by name
                character_data = await user_data_manager.get_rpg_character(user_id, username, name)
            else:
                # Load first character found for this user
                characters_data = await user_data_manager.get_all_rpg_characters(user_id, username)
                if not characters_data:
                    return None
                character_data = characters_data[0]  # Load first character found
            
            if not character_data:
                return None
            
            try:
                # Convert nested dicts back to dataclasses
                if 'base_stats' in character_data:
                    character_data['base_stats'] = Stats(**character_data['base_stats'])
                if 'combat_record' in character_data:
                    character_data['combat_record'] = CombatRecord(**character_data['combat_record'])
                
                character = Character(**character_data)
                self.characters[user_id] = character
                return character
            except Exception as e:
                print(f"Error loading character: {e}")
                return None
        
        return asyncio.run(_load_character())

    def update_combat_record(self, user_id: str, enemy_name: str, enemy_type: str, won: bool, damage_dealt: int = 0, username: str = None) -> bool:
        """Update character combat record after battle - used by battle system."""
        character = self.get_character(user_id)
        if not character:
            return False
        
        record = character.combat_record
        record.total_damage_dealt += damage_dealt
        
        if won:
            record.total_wins += 1
            if enemy_type == "monster":
                record.monsters_defeated[enemy_name] = record.monsters_defeated.get(enemy_name, 0) + 1
            elif enemy_type == "boss":
                record.bosses_defeated[enemy_name] = record.bosses_defeated.get(enemy_name, 0) + 1
            elif enemy_type == "titan":
                record.titans_defeated[enemy_name] = record.titans_defeated.get(enemy_name, 0) + 1
        else:
            record.total_losses += 1
            if enemy_type == "monster":
                record.monsters_lost_to[enemy_name] = record.monsters_lost_to.get(enemy_name, 0) + 1
            elif enemy_type == "boss":
                record.bosses_lost_to[enemy_name] = record.bosses_lost_to.get(enemy_name, 0) + 1
            elif enemy_type == "titan":
                record.titans_lost_to[enemy_name] = record.titans_lost_to.get(enemy_name, 0) + 1
        
        return self.save_character(user_id, username)

    def calculate_equipment_stats(self, character: Character) -> Dict[str, int]:
        """Calculate total stats from equipped equipment."""
        equipment_stats = {
            "ATT": 0,
            "DEF": 0,
            "DEX": 0,
            "INT": 0,
            "CHA": 0,
            "HP": 0
        }
        
        # Calculate bonuses from equipped weapons
        for weapon_name in character.equipped_weapons:
            if weapon_name in character.weapons:
                weapon = character.weapons[weapon_name]
                if isinstance(weapon, dict):
                    # Handle different weapon stat formats
                    equipment_stats["ATT"] += weapon.get("attack", 0)
                    equipment_stats["DEX"] += weapon.get("dexterity", 0)
                    equipment_stats["HP"] += weapon.get("health", 0)
                else:
                    # Handle legacy format or direct values
                    equipment_stats["ATT"] += getattr(weapon, 'attack', 0)
        
        # Calculate bonuses from equipped armor
        if character.equipped_armor and character.equipped_armor in character.armor:
            armor = character.armor[character.equipped_armor]
            if isinstance(armor, dict):
                equipment_stats["DEF"] += armor.get("defense", 0)
                equipment_stats["HP"] += armor.get("health", 0)
                equipment_stats["INT"] += armor.get("intelligence", 0)
            else:
                equipment_stats["DEF"] += getattr(armor, 'defense', 0)
        
        return equipment_stats

    def get_character_total_stats(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get character total stats including equipment bonuses."""
        character = self.get_character(user_id)
        if not character:
            return None
        
        equipment_stats = self.calculate_equipment_stats(character)
        
        total_stats = {
            "Attack": character.base_stats.ATT + equipment_stats["ATT"],
            "Defense": character.base_stats.DEF + equipment_stats["DEF"],
            "Dexterity": character.base_stats.DEX + equipment_stats["DEX"],
            "Intelligence": character.base_stats.INT + equipment_stats["INT"],
            "Charisma": character.base_stats.CHA + equipment_stats["CHA"],
            "Health": character.base_stats.HP + equipment_stats["HP"]
        }
        
        return {
            "name": character.name,
            "level": character.level,
            "faction": character.faction,
            "class": character.class_type,
            "base_stats": {
                "Attack": character.base_stats.ATT,
                "Defense": character.base_stats.DEF,
                "Dexterity": character.base_stats.DEX,
                "Intelligence": character.base_stats.INT,
                "Charisma": character.base_stats.CHA,
                "Health": character.base_stats.HP
            },
            "equipment_stats": equipment_stats,
            "total_stats": total_stats,
            "health": f"{character.current_health}/{character.max_health}",
            "experience": character.experience,
            "combat_record": asdict(character.combat_record),
            "equipped": {
                "character": character.equipped_character,
                "transformation": character.equipped_transformation,
                "beast_mode": character.equipped_beast_mode,
                "weapons": character.equipped_weapons,
                "armor": character.equipped_armor
            }
        }

    def get_character_stats(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get character battle statistics for display (legacy compatibility)."""
        return self.get_character_total_stats(user_id)

    def calculate_max_health_for_level(self, class_type: str, level: int) -> int:
        """Calculate max health based on character level and class type."""
        # Map character classes to stat classes
        stat_class_mapping = {
            "warrior": "ATT",
            "scientist": "ATT",
            "mariner": "DEF",
            "engineer": "DEF",
            "scout": "DEX",
            "seeker": "DEX",
            "commander": "CHA",
            "medic": "CHA"
        }
        
        # Get the stat class for this character
        stat_class = stat_class_mapping.get(class_type.lower(), "ATT")
        
        # Use base stats from config
        faction = "autobot"  # Default, could be parameterized
        base_stats = self.base_stats_config.get(faction, {}).get(class_type.lower(), Stats())
        
        # Get the corresponding skill value
        skill_value = getattr(base_stats, stat_class, 10)
        
        # Calculate health: Skill * Level * 50
        total_health = skill_value * level * 50
        
        return max(50, total_health)  # Minimum 50 health

    def calculate_level_from_xp(self, experience: int) -> int:
        """Calculate character level based on experience points."""
        level = 1
        while True:
            xp_needed = self.calculate_xp_required_for_level(level + 1)
            if experience >= xp_needed:
                level += 1
            else:
                break
        return level

    def calculate_xp_required_for_level(self, level: int) -> int:
        """Calculate XP required for a specific level."""
        return 100 * (level - 1) ** 2 + 50 * (level - 1)

    def gain_experience(self, user_id: str, exp_amount: int) -> dict:
        """Add experience and handle level ups with stat increases."""
        character = self.get_character(user_id)
        if not character:
            return {"leveled_up": False, "levels_gained": 0, "stats_increased": {}}
        
        old_level = character.level
        character.experience += exp_amount
        
        # Calculate new level
        new_level = self.calculate_level_from_xp(character.experience)
        levels_gained = new_level - old_level
        
        if levels_gained > 0:
            character.level = new_level
            
            # Get class template for stat progression
            base_template = self.base_stats_config.get(character.faction, {}).get(character.class_type, Stats())
            
            # Calculate stat increases based on class with random elements
            total_stats_increased = {}
            
            for level_gained in range(1, levels_gained + 1):
                # Base stat increases based on class strengths
                stat_increases = {
                    'ATT': 0,
                    'DEF': 0,
                    'DEX': 0,
                    'INT': 0,
                    'CHA': 0,
                    'HP': 0
                }
                
                # Primary stat increases (based on class template)
                if base_template.ATT >= 5:
                    stat_increases['ATT'] += 3
                if base_template.DEF >= 5:
                    stat_increases['DEF'] += 3
                if base_template.DEX >= 5:
                    stat_increases['DEX'] += 3
                if base_template.INT >= 5:
                    stat_increases['INT'] += 3
                if base_template.CHA >= 5:
                    stat_increases['CHA'] += 3
                
                # Always increase HP
                stat_increases['HP'] += 50 + random.randint(50, 100)
                
                # Random bonus points to distribute
                bonus_points = 4
                stats_to_boost = ['ATT', 'DEF', 'DEX', 'INT', 'CHA']
                for _ in range(bonus_points):
                    stat = random.choice(stats_to_boost)
                    stat_increases[stat] += 1
                
                # Apply increases
                new_stats = character.base_stats
                new_stats.ATT += stat_increases['ATT']
                new_stats.DEF += stat_increases['DEF']
                new_stats.DEX += stat_increases['DEX']
                new_stats.INT += stat_increases['INT']
                new_stats.CHA += stat_increases['CHA']
                new_stats.HP += stat_increases['HP']
                
                character.base_stats = new_stats
                
                # Track total increases
                for stat, increase in stat_increases.items():
                    if stat in total_stats_increased:
                        total_stats_increased[stat] += increase
                    else:
                        total_stats_increased[stat] = increase
            
            # Update health
            old_max_health = character.max_health
            character.max_health = character.base_stats.HP
            character.current_health = character.max_health  # Full heal on level up
            
            return {
                "leveled_up": True,
                "levels_gained": levels_gained,
                "new_level": character.level,
                "stats_increased": total_stats_increased,
                "health_gained": character.max_health - old_max_health,
                "new_max_health": character.max_health
            }
        
        return {"leveled_up": False, "levels_gained": 0, "stats_increased": {}}

    def delete_character(self, user_id: str, character_name: str, username: str = None) -> bool:
        """Delete a character by name for a user from unified storage."""
        import asyncio
        
        # Remove from memory
        if user_id in self.characters and self.characters[user_id].name == character_name:
            del self.characters[user_id]
        
        async def _delete_character():
            try:
                return await user_data_manager.delete_rpg_character(user_id, username, character_name)
            except Exception as e:
                print(f"Error deleting character: {e}")
                return False
        
        return asyncio.run(_delete_character())

    def equip_item(self, user_id: str, character_name: str, item_name: str, equipment_type: str, username: str = None) -> dict:
        """Equip an item to a character."""
        character = self.get_character(user_id)
        if not character:
            return {"success": False, "message": "Character not found"}
        
        if character.name != character_name:
            return {"success": False, "message": "Character name mismatch"}
        
        # Check if item exists in inventory
        if item_name not in character.inventory:
            return {"success": False, "message": f"Item '{item_name}' not found in inventory"}
        
        item = character.inventory[item_name]
        
        # Validate equipment type
        if equipment_type == "weapon":
            # Check weapon limit (2 weapons max)
            if len(character.equipped_weapons) >= 2:
                return {"success": False, "message": "Maximum 2 weapons can be equipped"}
            
            # Check if already equipped
            if item_name in character.equipped_weapons:
                return {"success": False, "message": f"'{item_name}' is already equipped"}
            
            character.equipped_weapons.append(item_name)
            
        elif equipment_type == "armor":
            # Check armor limit (1 armor max)
            if character.equipped_armor:
                return {"success": False, "message": "Only 1 armor can be equipped. Unequip current armor first"}
            
            character.equipped_armor = item_name
            
        else:
            return {"success": False, "message": "Invalid equipment type"}
        
        # Save character
        self._save_character_async(user_id, character, username)
        
        return {"success": True, "message": f"Successfully equipped '{item_name}' as {equipment_type}"}

    def unequip_item(self, user_id: str, character_name: str, item_name: str, equipment_type: str, username: str = None) -> dict:
        """Unequip an item from a character."""
        character = self.get_character(user_id)
        if not character:
            return {"success": False, "message": "Character not found"}
        
        if character.name != character_name:
            return {"success": False, "message": "Character name mismatch"}
        
        if equipment_type == "weapon":
            if item_name not in character.equipped_weapons:
                return {"success": False, "message": f"'{item_name}' is not equipped as weapon"}
            
            character.equipped_weapons.remove(item_name)
            
        elif equipment_type == "armor":
            if character.equipped_armor != item_name:
                return {"success": False, "message": f"'{item_name}' is not equipped as armor"}
            
            character.equipped_armor = None
            
        else:
            return {"success": False, "message": "Invalid equipment type"}
        
        # Save character
        self._save_character_async(user_id, character, username)
        
        return {"success": True, "message": f"Successfully unequipped '{item_name}'"}

    # Story and encounter generation methods
    async def generate_cohesive_encounter(self, character: Character, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate a story encounter for the character using AI."""
        if context is None:
            context = {}
        
        # Select appropriate content using AI generation
        encounter_type = context.get('type', 'exploration')
        
        if encounter_type == 'combat':
            return await self._generate_ai_combat_encounter(character, context)
        elif encounter_type == 'group_combat':
            # Handle group combat using dynamic enemy generation
            if 'characters' in context:
                return await self.generate_group_combat_encounter(context['characters'], context)
            else:
                return await self._generate_ai_combat_encounter(character, context)
        elif encounter_type == 'group_event':
            # Handle group random events
            if 'characters' in context:
                return await self.generate_group_random_event(context['characters'], context)
            else:
                return await self._generate_ai_random_event(character, context)
        elif encounter_type == 'exploration':
            return await self._generate_ai_story_segment(character, context)
        else:
            return await self._generate_ai_random_event(character, context)

    async def _generate_ai_story_segment(self, character: Character, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate an AI-powered story segment for exploration."""
        try:
            faction = character.faction
            class_type = character.class_type
            level = character.level
            
            prompt = f"""
            Generate a compelling exploration story segment for a Transformers RPG character.
            
            Character Details:
            - Name: {character.name}
            - Faction: {faction.title()}
            - Class: {class_type.title()}
            - Level: {level}
            
            Context: {context.get('description', 'Exploring the vast world of Cybertron')}
            
            Create a rich, immersive narrative that:
            1. Fits the character's faction and class background
            2. Provides meaningful exploration content
            3. Includes potential discoveries or challenges
            4. Has appropriate tone for the character's level
            5. Can lead to further encounters or story development
            
            Return a JSON object with:
            {{
                "type": "exploration",
                "story": "detailed narrative text",
                "rewards": [{{"type": "experience", "amount": number}}, {{"type": "item", "name": "item name"}}],
                "next_hooks": ["potential follow-up scenarios"],
                "mood": "atmospheric mood description"
            }}
            """
            
            response = await self.model.generate_content_async(prompt)
            
            try:
                # Try to parse JSON from response
                json_start = response.text.find('{')
                json_end = response.text.rfind('}') + 1
                if json_start != -1 and json_end != 0:
                    json_str = response.text[json_start:json_end]
                    return json.loads(json_str)
            except:
                pass
            
            # Fallback response
            return {
                "type": "exploration",
                "story": response.text,
                "rewards": [{"type": "experience", "amount": 50}],
                "next_hooks": ["Continue exploring", "Investigate further"],
                "mood": "mysterious"
            }
            
        except Exception as e:
            print(f"Error generating AI story segment: {e}")
            return {
                "type": "exploration",
                "story": "You continue exploring the vast landscapes of Cybertron, discovering new areas and potential adventures.",
                "rewards": [{"type": "experience", "amount": 25}],
                "next_hooks": ["Continue journey"],
                "mood": "exploratory"
            }

    async def _generate_ai_random_event(self, character: Character, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate an AI-powered random event."""
        try:
            faction = character.faction
            class_type = character.class_type
            level = character.level
            
            prompt = f"""
            Generate an engaging random event for a Transformers RPG character.
            
            Character Details:
            - Name: {character.name}
            - Faction: {faction.title()}
            - Class: {class_type.title()}
            - Level: {level}
            
            Context: {context.get('description', 'A random encounter in the world of Cybertron')}
            
            Create an interesting random event that:
            1. Fits Transformers lore and setting
            2. Provides meaningful choices or challenges
            3. Has appropriate difficulty for the character's level
            4. Can involve skill checks (Attack, Defense, Dexterity, Intelligence, Charisma)
            5. Has clear success/failure outcomes with rewards/consequences
            
            Return a JSON object with:
            {{
                "type": "event",
                "name": "event title",
                "description": "detailed event description",
                "choices": {{
                    "attack": {{
                        "skill": "Attack",
                        "description": "aggressive approach description",
                        "success": "success outcome",
                        "failure": "failure outcome"
                    }},
                    "defense": {{
                        "skill": "Defense",
                        "description": "defensive approach description",
                        "success": "success outcome",
                        "failure": "failure outcome"
                    }},
                    "dexterity": {{
                        "skill": "Dexterity",
                        "description": "skillful approach description",
                        "success": "success outcome",
                        "failure": "failure outcome"
                    }},
                    "intelligence": {{
                        "skill": "Intelligence",
                        "description": "intellectual approach description",
                        "success": "success outcome",
                        "failure": "failure outcome"
                    }},
                    "charisma": {{
                        "skill": "Charisma",
                        "description": "diplomatic approach description",
                        "success": "success outcome",
                        "failure": "failure outcome"
                    }}
                }},
                "skill_thresholds": {{
                    "attack": {max(2, min(12, level + 1))},
                    "defense": {max(2, min(12, level + 1))},
                    "dexterity": {max(2, min(12, level + 1))},
                    "intelligence": {max(2, min(12, level + 1))},
                    "charisma": {max(2, min(12, level + 1))}
                }},
                "rewards": {{
                    "success": [{{"type": "experience", "amount": {level * 25}}}],
                    "failure": [{{"type": "experience", "amount": {level * 10}}}]
                }}
            }}
            """
            
            response = await self.model.generate_content_async(prompt)
            
            try:
                # Try to parse JSON from response
                json_start = response.text.find('{')
                json_end = response.text.rfind('}') + 1
                if json_start != -1 and json_end != 0:
                    json_str = response.text[json_start:json_end]
                    return json.loads(json_str)
            except:
                pass
            
            # Fallback response
            return {
                "type": "event",
                "name": "Unexpected Discovery",
                "description": response.text,
                "choices": {
                    "attack": {
                        "skill": "Attack",
                        "description": "Take direct action",
                        "success": "You successfully handle the situation",
                        "failure": "Your approach causes complications"
                    },
                    "defense": {
                        "skill": "Defense",
                        "description": "Proceed cautiously",
                        "success": "Your careful approach works well",
                        "failure": "Your caution leads to missed opportunities"
                    },
                    "dexterity": {
                        "skill": "Dexterity",
                        "description": "Use agility and precision",
                        "success": "Your nimble approach succeeds",
                        "failure": "Your attempt at finesse fails"
                    },
                    "intelligence": {
                        "skill": "Intelligence",
                        "description": "Apply knowledge and strategy",
                        "success": "Your intellect provides the solution",
                        "failure": "Your analysis proves incorrect"
                    },
                    "charisma": {
                        "skill": "Charisma",
                        "description": "Use diplomacy and persuasion",
                        "success": "Your words win the day",
                        "failure": "Your attempt at diplomacy backfires"
                    }
                },
                "skill_thresholds": {
                    "attack": max(2, min(8, level + 1)),
                    "defense": max(2, min(8, level + 1)),
                    "dexterity": max(2, min(8, level + 1)),
                    "intelligence": max(2, min(8, level + 1)),
                    "charisma": max(2, min(8, level + 1))
                },
                "rewards": {
                    "success": [{"type": "experience", "amount": level * 20}],
                    "failure": [{"type": "experience", "amount": level * 5}]
                }
            }
            
        except Exception as e:
            print(f"Error generating AI random event: {e}")
            return {
                "type": "event",
                "name": "Simple Encounter",
                "description": "You encounter a situation that requires your attention and skills.",
                "choices": {
                    "attack": {
                        "skill": "Attack",
                        "description": "Use force or direct action",
                        "success": "Your direct approach succeeds",
                        "failure": "Force creates new problems"
                    }
                },
                "skill_thresholds": {
                    "attack": 3
                },
                "rewards": {
                    "success": [{"type": "experience", "amount": 15}],
                    "failure": [{"type": "experience", "amount": 5}]
                }
            }

    async def _generate_ai_combat_encounter(self, character: Character, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a combat encounter using dynamic enemy generation from battle system."""
        try:
            # Create a mock context for battle system integration
            mock_ctx = type('MockCtx', (), {'author': type('MockAuthor', (), {'id': character.user_id, 'display_name': character.name})()})()
            
            # Create battle view to use dynamic enemy generation
            battle_view = RPGUnifiedBattleView(mock_ctx, battle_type="solo")
            
            # Generate dynamic enemy based on character stats
            enemy = await battle_view.generate_dynamic_enemy([(
                mock_ctx.author, 
                {
                    'level': character.level,
                    'current_health': character.current_health,
                    'base_stats': character.base_stats.__dict__,
                    'faction': character.faction,
                    'class_type': character.class_type
                }
            )])
            
            # Create immersive combat encounter using the generated enemy
            faction = character.faction
            class_type = character.class_type
            level = character.level
            
            # Determine enemy type and rarity from generated enemy
            enemy_type = enemy.get('type', 'monster')
            rarity = enemy.get('rarity', 'common')
            enemy_name = enemy.get('name', f"{enemy_type.title()} Enemy")
            
            prompt = f"""
            Generate an exciting combat encounter for a Transformers RPG character.
            
            Character Details:
            - Name: {character.name}
            - Faction: {faction.title()}
            - Class: {class_type.title()}
            - Level: {level}
            
            Enemy Details:
            - Name: {enemy_name}
            - Type: {enemy_type}
            - Rarity: {rarity}
            - Health: {enemy.get('health', 100)}
            - Attack: {enemy.get('attack', 15)}
            
            Context: {context.get('description', 'A challenging battle on Cybertron')}
            
            Create a compelling combat encounter that:
            1. Features this specific enemy type and rarity
            2. Includes rich narrative description and atmosphere
            3. Provides enemy stats balanced for the character's level
            4. Has Transformers-themed combat elements
            5. Can lead to loot, experience, or story progression
            
            Return a JSON object with:
            {{
                "type": "combat",
                "monster": {{
                    "name": "{enemy_name}",
                    "description": "detailed enemy description",
                    "health": {enemy.get('health', 100)},
                    "attack": {enemy.get('attack', 15)},
                    "defense": {enemy.get('defense', 10)},
                    "rarity": "{rarity}",
                    "type": "{enemy_type}"
                }},
                "story": "immersive combat narrative",
                "battlefield": "description of the combat environment",
                "special_abilities": ["unique enemy abilities"],
                "potential_loot": ["possible rewards"]
            }}
            """
            
            response = await self.model.generate_content_async(prompt)
            
            try:
                # Try to parse JSON from response
                json_start = response.text.find('{')
                json_end = response.text.rfind('}') + 1
                if json_start != -1 and json_end != 0:
                    json_str = response.text[json_start:json_end]
                    return json.loads(json_str)
            except:
                pass
            
            # Use the generated enemy data directly
            return {
                "type": "combat",
                "monster": {
                    "name": enemy_name,
                    "description": f"A formidable {rarity} {enemy_type} encountered on Cybertron",
                    "health": enemy.get('health', 100),
                    "attack": enemy.get('attack', 15),
                    "defense": enemy.get('defense', 10),
                    "rarity": rarity,
                    "type": enemy_type
                },
                "story": response.text,
                "battlefield": "A contested area on Cybertron",
                "special_abilities": ["Energy blast", "Shield deployment"],
                "potential_loot": ["Energon cube", "Weapon upgrade"]
            }
            
        except Exception as e:
            print(f"Error generating AI combat encounter: {e}")
            return {
                "type": "combat",
                "monster": {
                    "name": "Enemy Combatant",
                    "description": "A hostile Transformer challenges you to battle",
                    "health": 100,
                    "attack": 20,
                    "defense": 15,
                    "rarity": "common",
                    "type": "monster"
                },
                "story": "You encounter a hostile force that must be overcome through combat.",
                "battlefield": "Cybertron battlefield",
                "special_abilities": ["Basic attack"],
                "potential_loot": ["Basic energon"]
            }

    async def _load_monsters_and_bosses(self) -> Dict[str, Any]:
        """Legacy method - now uses AI generation. Returns empty dict."""
        return {}

    async def _load_transformation_items(self) -> Dict[str, Any]:
        """Legacy method - now uses AI generation. Returns empty dict."""
        return {}

            
    async def load_character_async(self, user_id: str, name: str = None, username: str = None) -> Optional[Character]:
        """Async version of load_character for bot integration"""
        try:
            if name:
                # Load specific character by name
                character_data = await user_data_manager.get_rpg_character(user_id, username, name)
            else:
                # Load first character found for this user
                characters_data = await user_data_manager.get_all_rpg_characters(user_id, username)
                if not characters_data:
                    return None
                character_data = characters_data[0]
            
            if not character_data:
                return None
            
            # Convert nested dicts back to dataclasses
            if 'base_stats' in character_data:
                character_data['base_stats'] = Stats(**character_data['base_stats'])
            if 'combat_record' in character_data:
                character_data['combat_record'] = CombatRecord(**character_data['combat_record'])
            
            character = Character(**character_data)
            self.characters[user_id] = character
            return character
            
        except Exception as e:
            logger.error(f"Error loading character {user_id}: {e}")
            return None

    async def _generate_combat_encounter(self, character: Character, monsters_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a combat encounter using AI."""
        return await self._generate_ai_combat_encounter(character, context)


class FirstReactView(discord.ui.View):
    """First-to-react view for group events - fastest click wins!"""
    def __init__(self, participants, timeout=30):
        super().__init__(timeout=timeout)
        self.participants = participants
        self.chosen_skill = None
        self.chosen_by = None
        self.message = None
        
    @discord.ui.button(label="⚔️ Attack", style=discord.ButtonStyle.red, emoji="⚔️")
    async def attack(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "Attack")
        
    @discord.ui.button(label="🛡️ Defense", style=discord.ButtonStyle.green, emoji="🛡️")
    async def defense(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "Defense")
        
    @discord.ui.button(label="🎯 Dexterity", style=discord.ButtonStyle.blurple, emoji="🎯")
    async def dexterity(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "Dexterity")
        
    @discord.ui.button(label="🧠 Intelligence", style=discord.ButtonStyle.grey, emoji="🧠")
    async def intelligence(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "Intelligence")
        
    @discord.ui.button(label="💬 Charisma", style=discord.ButtonStyle.green, emoji="💬")
    async def charisma(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "Charisma")
    
    async def handle_choice(self, interaction: discord.Interaction, skill: str):
        if interaction.user.id not in [p['user_id'] for p in self.participants]:
            await interaction.response.send_message("You're not part of this party!", ephemeral=True)
            return
            
        if self.chosen_skill is None:
            self.chosen_skill = skill
            self.chosen_by = interaction.user
            
            # Disable all buttons
            for child in self.children:
                child.disabled = True
                
            # Update embed to show winner
            embed = discord.Embed(
                title="🎯 Skill Chosen!",
                description=f"**{skill}** chosen by **{interaction.user.display_name}**!",
                color=discord.Color.green()
            )
            embed.set_footer(text="Processing skill check...")
            
            await interaction.response.edit_message(embed=embed, view=self)
            self.stop()
        else:
            await interaction.response.send_message(
                f"{self.chosen_by.display_name} already chose {self.chosen_skill}!", 
                ephemeral=True
            )

    async def on_timeout(self):
        if self.message and self.chosen_skill is None:
            embed = discord.Embed(
                title="⏰ Time's Up!",
                description="No one made a choice in time!",
                color=discord.Color.red()
            )
            await self.message.edit(embed=embed, view=None)

    async def send_initial_message(self, channel, embed):
        self.message = await channel.send(embed=embed, view=self)
        return self.message

class BattleSetupView(discord.ui.View):
    """Setup view for group battles and events"""
    def __init__(self, rpg_commands):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.rpg_commands = rpg_commands
        self.players = []
        self.message = None
        
    @discord.ui.button(label="Join Party", style=discord.ButtonStyle.green, emoji="🤖")
    async def join_party(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.players:
            self.players.append(interaction.user)
            await self.update_embed()
            await interaction.response.send_message("Joined the party!", ephemeral=True)
        else:
            await interaction.response.send_message("You're already in the party!", ephemeral=True)
    
    @discord.ui.button(label="Leave Party", style=discord.ButtonStyle.red, emoji="❌")
    async def leave_party(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in self.players:
            self.players.remove(interaction.user)
            await self.update_embed()
            await interaction.response.send_message("Left the party!", ephemeral=True)
        else:
            await interaction.response.send_message("You're not in the party!", ephemeral=True)
    
    @discord.ui.button(label="Start Event", style=discord.ButtonStyle.blurple, emoji="🎲")
    async def start_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.players) < 1:
            await interaction.response.send_message("Need at least 1 player!", ephemeral=True)
            return
            
        if interaction.user not in self.players:
            await interaction.response.send_message("Only party members can start!", ephemeral=True)
            return
            
        # Disable buttons
        for child in self.children:
            child.disabled = True
            
        await interaction.response.edit_message(view=self)
        
        # Generate event using the new first-react system
        characters = []
        for player in self.players:
            char = await self.rpg_commands.rpg_system.get_character_async(str(player.id))
            if char:
                characters.append(char)
        
        if characters:
            event = await self.rpg_commands.rpg_system.generate_group_random_event(characters)
            await self.rpg_commands.handle_first_react_event(interaction.channel, self.players, event)
    
    async def update_embed(self):
        if self.message:
            embed = self.message.embeds[0]
            
            if self.players:
                player_names = [p.display_name for p in self.players]
                embed.set_field_at(0, name="🤖 Party Members", value=", ".join(player_names), inline=False)
            else:
                embed.set_field_at(0, name="🤖 Party Members", value="No players yet", inline=False)
            
            await self.message.edit(embed=embed)
    
    async def on_timeout(self):
        if self.message:
            embed = self.message.embeds[0]
            embed.title = "⏰ Party Timed Out"
            embed.description = "The party formation has timed out."
            embed.color = discord.Color.red()
            
            for child in self.children:
                child.disabled = True
                
            await self.message.edit(embed=embed, view=None)

    async def generate_group_random_event(self, characters: List[Character], context: Dict[str, Any] = None, use_first_react: bool = False) -> Dict[str, Any]:
        """Generate a random event for multiple characters using AI."""
        if context is None:
            context = {}
        
        try:
            # Calculate party statistics
            avg_level = sum(c.level for c in characters) // len(characters)
            party_names = [c.name for c in characters]
            party_factions = list(set([c.faction for c in characters]))
            party_classes = list(set([c.class_type for c in characters]))
            
            # Create context for group dynamics
            group_context = {
                "party_size": len(characters),
                "average_level": avg_level,
                "members": party_names,
                "factions": party_factions,
                "classes": party_classes,
                "description": context.get('description', 'A group encounter on Cybertron')
            }
            
            prompt = f"""
            Generate an engaging random group event for a Transformers RPG party.
            
            Party Details:
            - Characters: {', '.join(party_names)}
            - Average Level: {avg_level}
            - Party Size: {len(characters)}
            - Factions: {', '.join(party_factions)}
            - Classes: {', '.join(party_classes)}
            
            Context: {group_context['description']}
            
            Create an interesting group random event that:
            1. Involves the entire party working together or making choices
            2. Fits Transformers lore and setting
            3. Has appropriate difficulty for the party's combined strength
            4. Can involve skill checks using any of: Attack, Defense, Dexterity, Intelligence, Charisma
            5. Has clear success/failure outcomes with rewards/consequences for all members
            6. Includes group decision-making or individual contributions
            7. Can lead to party bonding, conflict, or story development
            
            Return a JSON object with:
            {{
                "type": "group_event",
                "name": "event title",
                "description": "detailed group event description",
                "choices": {{
                    "attack": {{
                        "skill": "Attack",
                        "description": "coordinated aggressive approach",
                        "success": "success outcome for party",
                        "failure": "failure outcome for party"
                    }},
                    "defense": {{
                        "skill": "Defense",
                        "description": "protective group strategy",
                        "success": "success outcome for party",
                        "failure": "failure outcome for party"
                    }},
                    "dexterity": {{
                        "skill": "Dexterity",
                        "description": "coordinated precision approach",
                        "success": "success outcome for party",
                        "failure": "failure outcome for party"
                    }},
                    "intelligence": {{
                        "skill": "Intelligence",
                        "description": "tactical group planning",
                        "success": "success outcome for party",
                        "failure": "failure outcome for party"
                    }},
                    "charisma": {{
                        "skill": "Charisma",
                        "description": "diplomatic group resolution",
                        "success": "success outcome for party",
                        "failure": "failure outcome for party"
                    }}
                }},
                "skill_thresholds": {{
                    "attack": {max(2, min(12, avg_level + 2))},
                    "defense": {max(2, min(12, avg_level + 2))},
                    "dexterity": {max(2, min(12, avg_level + 2))},
                    "intelligence": {max(2, min(12, avg_level + 2))},
                    "charisma": {max(2, min(12, avg_level + 2))}
                }},
                "rewards": {{
                    "success": [{{"type": "experience", "amount": {avg_level * 30}}}],
                    "failure": [{{"type": "experience", "amount": {avg_level * 15}}}]
                }},
                "individual_contributions": true,
                "party_size": {len(characters)}
            }}
            """
            
            response = await self.model.generate_content_async(prompt)
            
            try:
                json_start = response.text.find('{')
                json_end = response.text.rfind('}') + 1
                if json_start != -1 and json_end != 0:
                    json_str = response.text[json_start:json_end]
                    parsed_response = json.loads(json_str)
                    # Ensure individual_contributions is set
                    parsed_response["individual_contributions"] = True
                    parsed_response["party_size"] = len(characters)
                    return parsed_response
            except:
                pass
            
            # Use the generated data directly
            return {
                "type": "group_event",
                "name": "Group Challenge",
                "description": response.text,
                "choices": {
                    "attack": {
                        "skill": "Attack",
                        "description": "The party coordinates an aggressive response",
                        "success": "Your combined strength overcomes the challenge",
                        "failure": "The aggressive approach creates complications"
                    },
                    "defense": {
                        "skill": "Defense",
                        "description": "The party works together to protect and defend",
                        "success": "Your defensive strategy succeeds",
                        "failure": "Your cautious approach allows the challenge to escalate"
                    },
                    "dexterity": {
                        "skill": "Dexterity",
                        "description": "The party uses precision and coordination",
                        "success": "Your agile teamwork prevails",
                        "failure": "Your precision attempt falls short"
                    },
                    "intelligence": {
                        "skill": "Intelligence",
                        "description": "The party applies collective knowledge and strategy",
                        "success": "Your combined intellect solves the challenge",
                        "failure": "Your strategic approach proves flawed"
                    },
                    "charisma": {
                        "skill": "Charisma",
                        "description": "The party uses diplomacy and social skills",
                        "success": "Your unified diplomatic effort succeeds",
                        "failure": "Your social approach creates misunderstandings"
                    }
                },
                "skill_thresholds": {
                    "attack": max(2, min(12, avg_level + 2)),
                    "defense": max(2, min(12, avg_level + 2)),
                    "dexterity": max(2, min(12, avg_level + 2)),
                    "intelligence": max(2, min(12, avg_level + 2)),
                    "charisma": max(2, min(12, avg_level + 2))
                },
                "rewards": {
                    "success": [{"type": "experience", "amount": avg_level * 30}],
                    "failure": [{"type": "experience", "amount": avg_level * 15}]
                },
                "individual_contributions": True,
                "party_size": len(characters)
            }
            
        except Exception as e:
            print(f"Error generating group random event: {e}")
            return {
                "type": "group_event",
                "name": "Party Challenge",
                "description": "Your party faces a challenge that requires everyone's skills and cooperation.",
                "choices": {
                    "attack": {
                        "skill": "Attack",
                        "description": "Work together to overcome through force",
                        "success": "Your combined strength wins the day",
                        "failure": "The challenge proves too great"
                    },
                    "intelligence": {
                        "skill": "Intelligence",
                        "description": "Use collective knowledge to solve",
                        "success": "Your wisdom guides you to victory",
                        "failure": "The puzzle remains unsolved"
                    }
                },
                "skill_thresholds": {
                    "attack": max(2, min(10, 5)),
                    "intelligence": max(2, min(10, 5))
                },
                "rewards": {
                    "success": [{"type": "experience", "amount": 50}],
                    "failure": [{"type": "experience", "amount": 25}]
                },
                "individual_contributions": True,
                "party_size": len(characters)
            }

    async def handle_group_event_with_first_react(self, ctx, event_data, participants):
        """Handle a group event using the first-to-react decision system"""
        try:
            # Create the FirstReactView
            view = FirstReactView(ctx, event_data, participants)
            
            # Send the event message with the view
            embed = view.create_event_embed()
            message = await ctx.send(embed=embed, view=view)
            view.message = message
            
            # Wait for the decision
            await view.wait()
            
            if view.decision_made and view.chosen_action:
                # Process the chosen action
                chosen_action = view.chosen_action
                action_data = event_data['choices'][chosen_action]
                skill_name = action_data['skill']
                
                # Calculate success based on party's collective skills
                success_count = 0
                total_attempts = 0
                individual_results = []
                
                for user, character in participants:
                    # Get the relevant skill value
                    skill_value = getattr(character.base_stats, skill_name.upper(), 10)
                    threshold = event_data['skill_thresholds'].get(chosen_action, 10)
                    
                    # Roll for success
                    roll = random.randint(1, 20)
                    success = roll + skill_value >= threshold
                    
                    individual_results.append({
                        'user': user,
                        'character': character,
                        'skill': skill_name,
                        'skill_value': skill_value,
                        'roll': roll,
                        'threshold': threshold,
                        'success': success
                    })
                    
                    if success:
                        success_count += 1
                    total_attempts += 1
                
                # Determine overall success (majority wins)
                overall_success = success_count > total_attempts // 2
                
                # Create results embed
                results_embed = discord.Embed(
                    title=f"{'✅ Success!' if overall_success else '❌ Partial Success'}",
                    description=f"The party's attempt using **{skill_name}** has been resolved!",
                    color=0x00ff00 if overall_success else 0xffaa00
                )
                
                # Add individual results
                results_text = ""
                for result in individual_results:
                    emoji = "✅" if result['success'] else "❌"
                    results_text += f"{emoji} **{result['character'].name}**: Rolled {result['roll']} + {result['skill_value']} vs {result['threshold']}\n"
                
                results_embed.add_field(
                    name="Individual Contributions",
                    value=results_text,
                    inline=False
                )
                
                # Add outcome
                outcome_text = action_data['success'] if overall_success else action_data['failure']
                results_embed.add_field(
                    name="Outcome",
                    value=outcome_text,
                    inline=False
                )
                
                # Calculate and distribute rewards
                rewards = event_data['rewards']
                reward_type = 'success' if overall_success else 'failure'
                party_rewards = rewards.get(reward_type, [])
                
                reward_text = ""
                for reward in party_rewards:
                    if reward['type'] == 'experience':
                        for user, character in participants:
                            self.gain_experience(str(user.id), reward['amount'])
                            reward_text += f"🏆 **{character.name}** gained {reward['amount']} XP\n"
                
                if reward_text:
                    results_embed.add_field(
                        name="Rewards",
                        value=reward_text,
                        inline=False
                    )
                
                await ctx.send(embed=results_embed)
                
                # Record event completion for all participants
                for user, character in participants:
                    self.record_event_completion(
                        str(user.id), 
                        event_data['name'], 
                        overall_success, 
                        user.display_name
                    )
                
                return {
                    'success': overall_success,
                    'chosen_action': chosen_action,
                    'individual_results': individual_results,
                    'rewards': party_rewards
                }
            else:
                # Timeout or no decision
                await ctx.send("⏰ The group event timed out. The opportunity has passed.")
                return {'success': False, 'timeout': True}
                
        except Exception as e:
            logger.error(f"Error handling group event with first-react: {e}")
            await ctx.send("❌ An error occurred while processing the group event.")
            return {'success': False, 'error': str(e)}

    async def trigger_group_event_with_first_react(self, ctx, characters: List[Character], context: Dict[str, Any] = None):
        """Trigger a group event using the first-to-react system"""
        try:
            # Generate the event data
            event_data = await self.generate_group_random_event(characters, context, use_first_react=True)
            
            # Get Discord users for the characters
            participants = []
            for character in characters:
                user = ctx.guild.get_member(int(character.user_id))
                if user:
                    participants.append((user, character))
            
            if not participants:
                await ctx.send("❌ Could not find Discord users for the characters.")
                return
            
            # Use the new first-to-react handler
            return await self.handle_group_event_with_first_react(ctx, event_data, participants)
            
        except Exception as e:
            logger.error(f"Error triggering group event with first-react: {e}")
            await ctx.send("❌ An error occurred while triggering the group event.")
            return {'success': False, 'error': str(e)}

    async def generate_group_combat_encounter(self, characters: List[Character], context: Dict[str, Any] = None) -> Dict[str, Any]:
        if context is None:
            context = {}
        
        try:
            # Create a mock context for battle system integration
            mock_ctx = type('MockCtx', (), {'author': type('MockAuthor', (), {'id': characters[0].user_id, 'display_name': characters[0].name})()})()
            
            # Create battle view to use dynamic enemy generation
            battle_view = RPGUnifiedBattleView(mock_ctx, battle_type="group")
            
            # Prepare character data for dynamic generation
            party_data = []
            for character in characters:
                party_data.append((
                    type('MockUser', (), {'id': character.user_id, 'display_name': character.name})(),
                    {
                        'level': character.level,
                        'current_health': character.current_health,
                        'base_stats': character.base_stats.__dict__,
                        'faction': character.faction,
                        'class_type': character.class_type
                    }
                ))
            
            # Generate dynamic enemy based on party composition
            enemy = await battle_view.generate_dynamic_enemy(party_data)
            
            # Create immersive group combat encounter
            avg_level = sum(c.level for c in characters) // len(characters)
            party_names = [c.name for c in characters]
            
            enemy_type = enemy.get('type', 'monster')
            rarity = enemy.get('rarity', 'common')
            enemy_name = enemy.get('name', f"{enemy_type.title()} Enemy")
            
            prompt = f"""
            Generate an exciting group combat encounter for a Transformers RPG party.
            
            Party Details:
            - Characters: {', '.join(party_names)}
            - Average Level: {avg_level}
            - Party Size: {len(characters)}
            
            Enemy Details:
            - Name: {enemy_name}
            - Type: {enemy_type}
            - Rarity: {rarity}
            - Health: {enemy.get('health', 100)}
            - Attack: {enemy.get('attack', 15)}
            
            Context: {context.get('description', 'A challenging group battle on Cybertron')}
            
            Create a compelling group combat encounter that:
            1. Features this specific enemy type and rarity
            2. Includes rich narrative description and atmosphere
            3. Provides enemy stats balanced for the party's combined strength
            4. Has Transformers-themed combat elements
            5. Can lead to loot, experience, or story progression for all party members
            
            Return a JSON object with:
            {{
                "type": "combat",
                "monster": {{
                    "name": "{enemy_name}",
                    "description": "detailed enemy description",
                    "health": {enemy.get('health', 100)},
                    "attack": {enemy.get('attack', 15)},
                    "defense": {enemy.get('defense', 10)},
                    "rarity": "{rarity}",
                    "type": "{enemy_type}"
                }},
                "story": "immersive group combat narrative",
                "battlefield": "description of the combat environment",
                "special_abilities": ["unique enemy abilities"],
                "potential_loot": ["possible rewards"],
                "party_size": {len(characters)}
            }}
            """
            
            response = await self.model.generate_content_async(prompt)
            
            try:
                json_start = response.text.find('{')
                json_end = response.text.rfind('}') + 1
                if json_start != -1 and json_end != 0:
                    json_str = response.text[json_start:json_end]
                    return json.loads(json_str)
            except:
                pass
            
            # Use the generated enemy data directly
            return {
                "type": "combat",
                "monster": {
                    "name": enemy_name,
                    "description": f"A formidable {rarity} {enemy_type} that challenges the entire party",
                    "health": enemy.get('health', 100),
                    "attack": enemy.get('attack', 15),
                    "defense": enemy.get('defense', 10),
                    "rarity": rarity,
                    "type": enemy_type
                },
                "story": response.text,
                "battlefield": "A contested area on Cybertron",
                "special_abilities": ["Energy blast", "Shield deployment"],
                "potential_loot": ["Energon cube", "Weapon upgrade"],
                "party_size": len(characters)
            }
            
        except Exception as e:
            print(f"Error generating group combat encounter: {e}")
            return {
                "type": "combat",
                "monster": {
                    "name": "Group Enemy",
                    "description": "A powerful enemy that requires teamwork to defeat",
                    "health": 200,
                    "attack": 30,
                    "defense": 20,
                    "rarity": "common",
                    "type": "monster"
                },
                "story": "Your party encounters a formidable foe that must be overcome through coordinated combat.",
                "battlefield": "Cybertron battlefield",
                "special_abilities": ["Area attack", "Team buff"],
                "potential_loot": ["Group energon", "Shared upgrade"],
                "party_size": len(characters)
            }

    async def _generate_exploration_encounter(self, character: Character, story_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate an exploration encounter using AI."""
        return await self._generate_ai_story_segment(character, context)

    async def _generate_random_event(self, character: Character, events_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a random event encounter using AI."""
        return await self._generate_ai_random_event(character, context)

    async def generate_loot(self, character: Character, encounter_type: str, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Generate loot based on encounter type and character, matching battle system standards."""
        try:
            transformation_items = await self._load_transformation_items()
            
            # Determine rarity based on context and character level
            rarity = context.get('rarity', 'common') if context else 'common'
            
            # Map rarity levels for consistency
            rarity_map = {
                "common": "common",
                "uncommon": "uncommon", 
                "rare": "rare",
                "epic": "epic",
                "legendary": "legendary",
                "mythic": "mythic"
            }
            
            target_rarity = rarity_map.get(rarity.lower(), "common")
            all_items = []
            
            # Handle both dict and list formats like battle system
            if isinstance(transformation_items, dict):
                for category in ['beast_modes', 'transformations', 'weapons', 'armor', 'items']:
                    if category in transformation_items:
                        category_data = transformation_items[category]
                        if isinstance(category_data, dict):
                            for item_id, item_data in category_data.items():
                                if isinstance(item_data, dict) and item_data.get('rarity', '').lower() == target_rarity:
                                    item_copy = dict(item_data)
                                    item_copy['id'] = item_id
                                    item_copy['category'] = category
                                    all_items.append(item_copy)
                        elif isinstance(category_data, list):
                            for item_data in category_data:
                                if isinstance(item_data, dict) and item_data.get('rarity', '').lower() == target_rarity:
                                    item_copy = dict(item_data)
                                    item_copy['category'] = category
                                    all_items.append(item_copy)
            else:
                # Handle list format
                for item in transformation_items:
                    if isinstance(item, dict) and item.get('rarity', '').lower() == target_rarity:
                        all_items.append(item)
            
            # Scale rewards based on character level and encounter type
            level_factor = max(1, character.level // 5)
            encounter_multipliers = {
                "monster": 1,
                "boss": 2,
                "titan": 3,
                "combat": 1.5,
                "event": 1.2,
                "exploration": 1
            }
            
            multiplier = encounter_multipliers.get(encounter_type.lower(), 1)
            
            # Determine number of items based on encounter difficulty
            base_items = min(3, 1 + level_factor)
            num_items = min(len(all_items), random.randint(1, int(base_items * multiplier)))
            
            if all_items:
                selected_items = random.sample(all_items, num_items)
                
                # Add value scaling based on level
                for item in selected_items:
                    if 'value' in item:
                        item['value'] = max(1, int(item['value'] * (1 + character.level * 0.1)))
                
                return selected_items
            
            # Fallback loot for empty results
            fallback_loot = [
                {
                    "name": f"{target_rarity.title()} Energon Cube",
                    "type": "consumable", 
                    "value": max(10, 10 * character.level),
                    "rarity": target_rarity,
                    "description": f"A {target_rarity} energon cube for healing"
                }
            ]
            
            # Add additional fallback items for higher rarities
            if target_rarity in ["rare", "epic", "legendary", "mythic"]:
                fallback_loot.append({
                    "name": f"{target_rarity.title()} Upgrade Core",
                    "type": "upgrade",
                    "value": max(25, 25 * character.level),
                    "rarity": target_rarity,
                    "description": f"A {target_rarity} upgrade core for equipment"
                })
            
            return fallback_loot[:num_items]
            
        except Exception as e:
            print(f"Error generating loot: {e}")
            
            # Return fallback loot
            return [{
                "name": f"Basic Energon Cube",
                "type": "consumable",
                "value": max(5, 5 * character.level),
                "rarity": "common",
                "description": "A basic energon cube for healing"
            }]

    async def distribute_group_rewards(self, participants: List[discord.User], event_data: Dict[str, Any], success: bool = True):
        """Distribute rewards to group participants, matching battle system standards."""
        try:
            rewards = []
            
            # Base XP and loot scaling
            base_xp = event_data.get('base_xp', 50)
            base_loot_value = event_data.get('base_loot_value', 25)
            difficulty_multiplier = {"easy": 0.8, "moderate": 1.0, "hard": 1.5, "very_hard": 2.0}.get(
                event_data.get('difficulty', 'moderate'), 1.0
            )
            
            # Success/failure modifiers
            success_multiplier = 1.5 if success else 0.5
            
            for participant in participants:
                try:
                    user_id = str(participant.id)
                    character = await self.get_character_async(user_id)
                    if not character:
                        continue
                    
                    # Calculate scaled rewards
                    level_factor = max(1, character.level)
                    scaled_xp = int(base_xp * level_factor * difficulty_multiplier * success_multiplier)
                    
                    # Award XP
                    self.gain_experience(user_id, scaled_xp)
                    
                    # Generate loot based on encounter type and success
                    encounter_type = event_data.get('type', 'event')
                    context = {
                        'rarity': event_data.get('rarity', 'common'),
                        'success': success,
                        'difficulty': event_data.get('difficulty', 'moderate')
                    }
                    
                    loot_items = await self.generate_loot(character, encounter_type, context)
                    
                    # Award loot items
                    for loot_item in loot_items:
                        await self.award_item(user_id, loot_item)
                    
                    # Record event completion
                    self.record_event_completion(
                        user_id, 
                        event_data.get('name', 'Group Event'), 
                        success, 
                        participant.display_name
                    )
                    
                    rewards.append({
                        'user': participant,
                        'xp': scaled_xp,
                        'loot': loot_items,
                        'success': success
                    })
                    
                except Exception as e:
                    logger.error(f"Error distributing rewards to {participant.display_name}: {e}")
                    continue
            
            return rewards
            
        except Exception as e:
            logger.error(f"Error in distribute_group_rewards: {e}")
            return []

    async def award_item(self, user_id: str, item: Dict[str, Any]):
        """Award an item to a player's inventory."""
        try:
            character = await self.get_character_async(user_id)
            if not character:
                return False
            
            if not hasattr(character, 'inventory'):
                character.inventory = []
            
            # Ensure item has required fields
            item_copy = dict(item)
            if 'id' not in item_copy:
                item_copy['id'] = str(uuid.uuid4())
            item_copy['acquired_date'] = datetime.now().isoformat()
            
            character.inventory.append(item_copy)
            await self.save_character_async(user_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error awarding item to {user_id}: {e}")
            return False

    def record_event_completion(self, user_id: str, event_name: str, success: bool, username: str = None):
        """Record event completion in character's history."""
        try:
            character = self.get_character(user_id)
            if not character:
                return
            
            if not hasattr(character, 'event_history'):
                character.event_history = []
            
            event_record = {
                'name': event_name,
                'success': success,
                'date': datetime.now().isoformat(),
                'type': 'group_event'
            }
            
            character.event_history.append(event_record)
            self.save_character(user_id, username)
            
        except Exception as e:
            logger.error(f"Error recording event completion for {user_id}: {e}")

    async def save_character_async(self, user_id: str, username: str = None):
        """Asynchronously save character data."""
        try:
            await user_data_manager.save_rpg_character(user_id, self.get_character(user_id))
        except Exception as e:
            logger.error(f"Error saving character {user_id}: {e}")

    async def get_character_async(self, user_id: str):
        """Asynchronously get character data."""
        try:
            return await user_data_manager.get_rpg_character(user_id)
        except Exception as e:
            logger.error(f"Error getting character {user_id}: {e}")
            return None


# Module-level interface for easy import
_rpg_system_instance = None

def get_rpg_system() -> TransformersAIDungeonMaster:
    """Get the global RPG system instance."""
    global _rpg_system_instance
    if _rpg_system_instance is None:
        _rpg_system_instance = TransformersAIDungeonMaster()
    return _rpg_system_instance

async def setup_rpg_system():
    """Initialize the RPG system for bot startup."""
    system = get_rpg_system()
    await system.__aenter__()
    return system

async def cleanup_rpg_system():
    """Cleanup the RPG system on bot shutdown."""
    global _rpg_system_instance
    if _rpg_system_instance is not None:
        await _rpg_system_instance.__aexit__(None, None, None)
        _rpg_system_instance = None

async def setup(bot):
    """Setup function for Discord.py bot integration"""
    system = get_rpg_system()
    await system.__aenter__()
    return system