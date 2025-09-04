import json
import random
import asyncio
import math
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any
import os
from datetime import datetime
import google.generativeai as genai
import discord
from discord.ext import commands
from discord import app_commands

# Import UserDataManager
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from user_data_manager import user_data_manager

# Constants - Remove CHARACTERS_DIR since we use unified storage
JSON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Json")
# Don't create JSON_DIR as it already exists at root level

@dataclass
class Stats:
    ATT: int = 10  # Attack
    DEF: int = 10  # Defense
    DEX: int = 10  # Dexterity
    CHA: int = 10  # Charisma

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

class TransformersAIDungeonMaster:
    """
    AI Dungeon Master for Transformers RPG that dynamically generates stories
    by pulling from JSON files containing enemies, events, story segments, and loot.
    Maintains narrative continuity and can regenerate events with same parameters.
    """
    
    def __init__(self, json_base_path: str = None, api_key: str = None):
        if json_base_path is None:
            json_base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Json")
        # Configure Gemini API
        if api_key:
            genai.configure(api_key=api_key)
        
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        self.json_base_path = json_base_path
        
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
        
        # RPG System backup functionality
        self.characters: Dict[str, Character] = {}
        self.base_stats_config = {
            "autobot": {
                "warrior": Stats(ATT=4, DEF=1, DEX=2, CHA=1),
                "scientist": Stats(ATT=4, DEF=2, DEX=2, CHA=0),
                "engineer": Stats(ATT=2, DEF=4, DEX=2, CHA=0),
                "mariner": Stats(ATT=1, DEF=4, DEX=0, CHA=2),
                "commander": Stats(ATT=2, DEF=1, DEX=1, CHA=4),
                "medic": Stats(ATT=0, DEF=1, DEX=3, CHA=4),
                "scout": Stats(ATT=1, DEF=0, DEX=4, CHA=3),
                "seeker": Stats(ATT=2, DEF=1, DEX=4, CHA=1)
            },
            "decepticon": {
                "warrior": Stats(ATT=4, DEF=1, DEX=2, CHA=1),
                "scientist": Stats(ATT=4, DEF=2, DEX=2, CHA=0),
                "engineer": Stats(ATT=2, DEF=4, DEX=2, CHA=0),
                "mariner": Stats(ATT=1, DEF=4, DEX=0, CHA=2),
                "commander": Stats(ATT=2, DEF=1, DEX=1, CHA=4),
                "medic": Stats(ATT=0, DEF=1, DEX=3, CHA=4),
                "scout": Stats(ATT=1, DEF=0, DEX=4, CHA=3),
                "seeker": Stats(ATT=2, DEF=1, DEX=4, CHA=1)
            }
        }
        
        # Cache for story continuity
        self.story_cache = {}
        self.last_encounter = None
        self.last_event = None
        
    def _load_json(self, filename: str) -> Dict[str, Any]:
        """Load JSON file from the Json directory"""
        try:
            file_path = os.path.join(self.json_base_path, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: {filename} not found at {file_path}")
            return {}

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

    # RPG System backup methods
    def create_character(self, user_id: str, name: str, faction: str, class_type: str, username: str = None) -> Character:
        """Create a new character with base stats using unified data storage."""
        import asyncio
        
        base_stats = self.base_stats_config.get(faction.lower(), {}).get(class_type.lower(), Stats())
        max_health = 100 + (base_stats.DEF * 10)
        
        character = Character(
            user_id=user_id,
            name=name,
            faction=faction.lower(),
            class_type=class_type.lower(),
            base_stats=base_stats,
            current_health=max_health,
            max_health=max_health
        )
        
        # Save character to unified storage
        async def _save_character():
            # Store in memory cache
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
        
        asyncio.run(_save_character())
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

    def get_character(self, user_id: str) -> Optional[Character]:
        """Get character by user ID from memory cache."""
        return self.characters.get(user_id)

    def save_character(self, user_id: str, username: str = None) -> bool:
        """Save character data to unified storage using character name."""
        if user_id not in self.characters:
            return False
        
        character = self.characters[user_id]
        return self.save_character_by_name(user_id, character.name, character, username)

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

    def resolve_combat(self, user_id: str, enemy_name: str, enemy_type: str, won: bool, damage_dealt: int = 0, username: str = None) -> bool:
        """Update character combat record after battle."""
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

    def get_character_stats(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get character statistics for display."""
        character = self.get_character(user_id)
        if not character:
            return None
        
        return {
            "name": character.name,
            "level": character.level,
            "faction": character.faction,
            "class": character.class_type,
            "stats": asdict(character.base_stats),
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

    def calculate_health_for_level(self, level: int, class_type: str) -> int:
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
        """Add experience and handle level ups."""
        character = self.get_character(user_id)
        if not character:
            return {"leveled_up": False, "levels_gained": 0, "attributes_increased": []}
        
        old_level = character.level
        character.experience += exp_amount
        
        # Calculate new level
        new_level = self.calculate_level_from_xp(character.experience)
        levels_gained = new_level - old_level
        
        if levels_gained > 0:
            character.level = new_level
            
            # Update max health based on new level
            old_max_health = character.max_health
            character.max_health = self.calculate_health_for_level(character.level, character.class_type)
            
            # Full heal on level up
            character.current_health = character.max_health
            
            return {
                "leveled_up": True,
                "levels_gained": levels_gained,
                "new_level": character.level,
                "health_gained": character.max_health - old_max_health,
                "new_max_health": character.max_health,
                "xp_for_next_level": self.calculate_xp_required_for_level(character.level + 1),
                "current_xp": character.experience
            }
        
        return {
            "leveled_up": False,
            "levels_gained": 0,
            "new_level": character.level,
            "current_xp": character.experience
        }

    def record_combat_result(self, user_id: str, enemy_type: str, enemy_name: str, won: bool) -> bool:
        """Record combat result for a user."""
        return self.resolve_combat(user_id, enemy_name, enemy_type, won)

    def distribute_loot_to_players(self, players: List[discord.User], enemy_rarity: str, enemy_type: str) -> Dict[str, List[Dict[str, Any]]]:
        """Distribute loot to players after battle."""
        loot_results = {}
        
        for player in players:
            user_id = str(player.id)
            character = self.get_character(user_id)
            if not character:
                continue
            
            # Generate loot based on enemy rarity and type
            items = []
            
            # Determine loot tier based on enemy rarity
            rarity_map = {
                "common": ["common", "uncommon"],
                "rare": ["uncommon", "rare"],
                "epic": ["rare", "epic"],
                "legendary": ["epic", "legendary"],
                "mythic": ["legendary", "mythic"]
            }
            
            possible_rarities = rarity_map.get(enemy_rarity.lower(), ["common"])
            chosen_rarity = random.choice(possible_rarities)
            
            # Get appropriate loot items
            loot_items = self._get_transformation_loot("weapon", chosen_rarity)
            if loot_items:
                items.append(random.choice(loot_items))
            
            loot_items = self._get_transformation_loot("transformation", chosen_rarity)
            if loot_items:
                items.append(random.choice(loot_items))
            
            loot_items = self._get_transformation_loot("beast_mode", chosen_rarity)
            if loot_items:
                items.append(random.choice(loot_items))
            
            loot_results[user_id] = items

    def load_character_data(self):
        """DEPRECATED: Use lazy loading instead. Kept for backward compatibility."""
        pass

    def save_character_data(self):
        """Save all character data to JSON files"""
        for user_id in self.characters:
            self.save_character(user_id)
    
    def _get_enemies_by_type(self, enemy_type: str, rarity: str = None) -> List[Dict[str, Any]]:
        """Get enemies by type (monster, boss, titan) and optional rarity"""
        # Ensure monsters and bosses are loaded
        if not self._monsters_loaded:
            self.load_monsters_and_bosses()
            
        enemies = []
        
        # Handle all enemy types from all rarities
        if enemy_type.lower() in ["monster", "monsters"]:
            # Load from monsters key
            monsters_by_rarity = self.monsters_and_bosses.get("monsters", {})
            for rarity_key, monster_list in monsters_by_rarity.items():
                if isinstance(monster_list, list):
                    for monster in monster_list:
                        if rarity is None or monster.get("rarity") == rarity:
                            enemies.append(monster)
            
            # Also check for any monsters in the root structure
            for key, value in self.monsters_and_bosses.items():
                if key != "rarity_colors" and isinstance(value, dict):
                    for rarity_key, enemy_list in value.items():
                        if isinstance(enemy_list, list):
                            for enemy in enemy_list:
                                if isinstance(enemy, dict) and enemy.get("type") == "monster":
                                    if rarity is None or enemy.get("rarity") == rarity:
                                        enemies.append(enemy)
        
        elif enemy_type.lower() in ["boss", "bosses"]:
            # Load from bosses key
            bosses_by_rarity = self.monsters_and_bosses.get("bosses", {})
            for rarity_key, boss_list in bosses_by_rarity.items():
                if isinstance(boss_list, list):
                    for boss in boss_list:
                        if rarity is None or boss.get("rarity") == rarity:
                            enemies.append(boss)
            
            # Check for bosses in monsters
            monsters_by_rarity = self.monsters_and_bosses.get("monsters", {})
            for rarity_key, monster_list in monsters_by_rarity.items():
                if isinstance(monster_list, list):
                    for monster in monster_list:
                        if isinstance(monster, dict) and monster.get("type") == "boss":
                            if rarity is None or monster.get("rarity") == rarity:
                                enemies.append(monster)
            
            # Check for bosses in any other structure
            for key, value in self.monsters_and_bosses.items():
                if key != "rarity_colors" and isinstance(value, dict):
                    for rarity_key, enemy_list in value.items():
                        if isinstance(enemy_list, list):
                            for enemy in enemy_list:
                                if isinstance(enemy, dict) and enemy.get("type") == "boss":
                                    if rarity is None or enemy.get("rarity") == rarity:
                                        enemies.append(enemy)
        
        elif enemy_type.lower() in ["titan", "titans"]:
            # Load from titans key
            titans_by_rarity = self.monsters_and_bosses.get("titans", {})
            for rarity_key, titan_list in titans_by_rarity.items():
                if isinstance(titan_list, list):
                    for titan in titan_list:
                        if rarity is None or titan.get("rarity") == rarity:
                            enemies.append(titan)
            
            # Check for titans in monsters
            monsters_by_rarity = self.monsters_and_bosses.get("monsters", {})
            for rarity_key, monster_list in monsters_by_rarity.items():
                if isinstance(monster_list, list):
                    for monster in monster_list:
                        if isinstance(monster, dict) and monster.get("type") == "titan":
                            if rarity is None or monster.get("rarity") == rarity:
                                enemies.append(monster)
            
            # Check for titans in any other structure
            for key, value in self.monsters_and_bosses.items():
                if key != "rarity_colors" and isinstance(value, dict):
                    for rarity_key, enemy_list in value.items():
                        if isinstance(enemy_list, list):
                            for enemy in enemy_list:
                                if isinstance(enemy, dict) and enemy.get("type") == "titan":
                                    if rarity is None or enemy.get("rarity") == rarity:
                                        enemies.append(enemy)
        
        # If no specific type requested, get all enemies
        elif enemy_type.lower() == "all":
            for key, value in self.monsters_and_bosses.items():
                if key != "rarity_colors" and isinstance(value, dict):
                    for rarity_key, enemy_list in value.items():
                        if isinstance(enemy_list, list):
                            for enemy in enemy_list:
                                if isinstance(enemy, dict) and enemy.get("type") in ["monster", "boss", "titan"]:
                                    if rarity is None or enemy.get("rarity") == rarity:
                                        enemies.append(enemy)
        
        return enemies
    
    def _get_random_story_segment(self, segment_type: str) -> Optional[Dict[str, Any]]:
        """Get a random story segment of specified type"""
        # Ensure story segments are loaded
        if not self._story_loaded:
            self.load_story_segments()
            
        all_segments = []
        
        # Main structure: story_segments -> segment_type -> list
        story_segments = self.story_segments.get("story_segments", {})
        if isinstance(story_segments, dict) and segment_type in story_segments:
            segments = story_segments[segment_type]
            if isinstance(segments, list):
                all_segments.extend(segments)
            elif isinstance(segments, dict):
                all_segments.extend(segments.values())
        
        # Check for other structures
        for key, value in self.story_segments.items():
            if key != "story_system" and key != "transition_types":
                if isinstance(value, dict):
                    # Handle segment_type directly
                    if segment_type in value:
                        segments = value[segment_type]
                        if isinstance(segments, list):
                            all_segments.extend(segments)
                        elif isinstance(segments, dict):
                            all_segments.extend(segments.values())
                    # Handle nested structure
                    for sub_key, sub_value in value.items():
                        if sub_key == segment_type:
                            if isinstance(sub_value, list):
                                all_segments.extend(sub_value)
                            elif isinstance(sub_value, dict):
                                all_segments.extend(sub_value.values())
                elif isinstance(value, list):
                    # Handle direct list of segments
                    for segment in value:
                        if isinstance(segment, dict) and segment.get("type") == segment_type:
                            all_segments.append(segment)
        
        # Filter valid segments
        valid_segments = [segment for segment in all_segments if isinstance(segment, dict) and "text" in segment]
        
        return random.choice(valid_segments) if valid_segments else None
    
    def _get_random_event(self) -> Optional[Dict[str, Any]]:
        """Get a random event from the events pool"""
        # Ensure random events are loaded
        if not self._events_loaded:
            self.load_random_events()
            
        all_events = []
        
        # Main structure: events under "random_encounters"
        encounters = self.random_events.get("random_encounters", {})
        if isinstance(encounters, dict):
            all_events.extend(encounters.values())
        elif isinstance(encounters, list):
            all_events.extend(encounters)
        
        # Check for events in other structures
        for key, value in self.random_events.items():
            if key != "roll_system":
                if isinstance(value, dict):
                    # Handle nested structure
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, dict) and ("description" in sub_value or "name" in sub_value):
                            all_events.append(sub_value)
                    # Handle direct event structure
                    if "description" in value or "name" in value:
                        all_events.append(value)
                elif isinstance(value, list):
                    # Handle list of events
                    for item in value:
                        if isinstance(item, dict) and ("description" in item or "name" in item):
                            all_events.append(item)
        
        # Filter valid events
        valid_events = [event for event in all_events if isinstance(event, dict) and ("description" in event or "name" in event)]
        
        return random.choice(valid_events) if valid_events else None
    
    def _get_transformation_loot(self, item_type: str, rarity: str = None) -> List[Dict[str, Any]]:
        """Get transformation items by type (beast_mode, weapon, armor, transformation) and optional rarity"""
        # Ensure transformation items are loaded
        if not self._transformation_items_loaded:
            self.load_transformation_items()
            
        items = []
        
        # Map item types to class names in the JSON structure
        type_to_class = {
            "beast_mode": "Beast Mode",
            "weapon": "Weapon",
            "armor": "Armor",
            "transformation": "Transformation"
        }
        
        # Handle both new and old structures
        class_name = type_to_class.get(item_type, item_type)
        
        # New structure: items organized by class and then by rarity
        items_by_class = self.transformation_items.get("items_by_class", {})
        
        if class_name in items_by_class:
            rarity_items = items_by_class[class_name]
            if rarity and rarity in rarity_items:
                # Get items for specific rarity
                items.extend(list(rarity_items[rarity].values()))
            elif rarity is None:
                # Get all items for this class across all rarities
                for rarity_key, rarity_dict in rarity_items.items():
                    if isinstance(rarity_dict, dict):
                        items.extend(list(rarity_dict.values()))
        
        # Also check for items in other possible structures
        for key, value in self.transformation_items.items():
            if key != "rarity_colors" and isinstance(value, dict):
                # Handle direct rarity mapping
                if rarity and rarity in value and isinstance(value[rarity], dict):
                    for item_key, item_data in value[rarity].items():
                        if isinstance(item_data, dict) and item_data.get("type") == item_type:
                            items.append(item_data)
                elif rarity is None:
                    # Get all items of this type across all rarities
                    for rarity_key, rarity_dict in value.items():
                        if isinstance(rarity_dict, dict):
                            for item_key, item_data in rarity_dict.items():
                                if isinstance(item_data, dict) and item_data.get("type") == item_type:
                                    items.append(item_data)
        
        return items
    
    def generate_cohesive_encounter(self, character, enemy_type: str = "monster", 
                                   rarity: str = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate a complete encounter with story setup, enemy, and narrative flow
        """
        # Get appropriate enemies
        enemies = self._get_enemies_by_type(enemy_type, rarity)
        if not enemies:
            enemies = self._get_enemies_by_type(enemy_type)
        
        selected_enemy = random.choice(enemies) if enemies else None
        
        # Get story segments for setup
        pre_battle = self._get_random_story_segment("pre_encounter")
        
        # Generate cohesive story
        story = self._build_encounter_story(character, selected_enemy, pre_battle, context)
        
        # Cache for continuity
        encounter_data = {
            "enemy": selected_enemy,
            "story_setup": story,
            "pre_battle_segment": pre_battle,
            "timestamp": datetime.now().isoformat(),
            "context": context or {}
        }
        
        self.last_encounter = encounter_data
        return encounter_data
    
    def _build_encounter_story(self, character, enemy, pre_battle_segment, context) -> str:
        """Build a cohesive story for the encounter"""
        if not enemy:
            return "A mysterious enemy approaches..."
        
        character_context = self._build_character_context(character)
        context = context or {}
        
        prompt = f"""
        You are a master storyteller for a Transformers RPG. Create a cohesive narrative that connects:
        
        Character: {character.name} ({character.faction} {character.class_type})
        Enemy: {enemy.get('name', 'Unknown')} ({enemy.get('type', 'enemy')})
        Enemy Description: {enemy.get('description', '')}
        
        Previous Context: {context.get('last_event', 'Starting fresh adventure')}
        
        Story Setup: {pre_battle_segment.get('text', 'Combat approaches') if pre_battle_segment else 'Battle awaits'}
        
        Create a seamless narrative (250-400 words) that:
        1. Flows naturally from any previous events
        2. Sets up this specific enemy encounter
        3. Incorporates the character's background and equipment
        4. Builds appropriate tension
        5. Ends with the enemy clearly identified and battle imminent
        
        Write in second person ("you") and maintain Transformers universe tone.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"As you explore, {enemy.get('name', 'a hostile force')} appears before you!"
    
    def generate_dynamic_event(self, character, event_type: str = None, 
                             previous_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate a dynamic event that fits the current story flow
        """
        event = self._get_random_event() if not event_type else None
        
        # Ensure context is not None
        previous_context = previous_context or {}
        
        # Generate story context
        story_context = self._build_event_story(character, event, previous_context)
        
        event_data = {
            "event": event,
            "story": story_context,
            "choices": event.get("choices", {}) if event else {},
            "timestamp": datetime.now().isoformat(),
            "context": previous_context
        }
        
        self.last_event = event_data
        return event_data
    
    def _build_event_story(self, character, event, previous_context) -> str:
        """Build story for random events"""
        if not event:
            return "An unexpected situation arises..."
        
        character_context = self._build_character_context(character)
        previous_context = previous_context or {}
        
        prompt = f"""
        You are a master storyteller for a Transformers RPG. Create a narrative for this event:
        
        Character: {character.name} ({character.faction} {character.class_type})
        Event: {event.get('name', 'Unknown Event')}
        Event Description: {event.get('description', '')}
        
        Previous Context: {previous_context.get('last_encounter', 'Fresh start')}
        
        Create an engaging story (200-350 words) that:
        1. Flows naturally from previous events
        2. Sets up the event situation
        3. Shows how the character encounters this situation
        4. Presents the choices in an organic way
        5. Maintains narrative continuity
        
        Write in second person ("you") and maintain Transformers universe tone.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"You encounter {event.get('name', 'a mysterious situation')}. {event.get('description', '')}"
    
    def generate_loot_discovery(self, character, item_type: str = None, 
                              rarity: str = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate a loot discovery that fits the story progression
        """
        items = self._get_transformation_loot(item_type, rarity) if item_type else []
        
        if not items:
            # Get all possible items from new structure
            all_items = []
            items_by_class = self.transformation_items.get("items_by_class", {})
            
            for class_name, rarity_dict in items_by_class.items():
                if isinstance(rarity_dict, dict):
                    for rarity_key, item_dict in rarity_dict.items():
                        if isinstance(item_dict, dict):
                            all_items.extend(list(item_dict.values()))
            
            # Filter by rarity if specified
            if rarity:
                items = [item for item in all_items if item.get("rarity") == rarity]
            else:
                items = all_items
        
        selected_item = random.choice(items) if items else None
        
        # Ensure context is not None
        context = context or {}
        discovery_story = self._build_loot_story(character, selected_item, context)
        
        loot_data = {
            "item": selected_item,
            "discovery_story": discovery_story,
            "timestamp": datetime.now().isoformat(),
            "context": context
        }
        
        return loot_data
    
    def _build_loot_story(self, character, item, context) -> str:
        """Build story for item discovery"""
        if not item:
            return "You find something valuable..."
        
        character_context = self._build_character_context(character)
        
        prompt = f"""
        You are a master storyteller for a Transformers RPG. Create a discovery story:
        
        Character: {character.name} ({character.faction} {character.class_type})
        Item: {item.get('name', 'Unknown Item')}
        Item Type: {item.get('type', 'item')}
        Item Description: {item.get('description', '')}
        
        Story Context: {context.get('last_event', 'During exploration')}
        
        Create an exciting discovery story (200-300 words) that:
        1. Makes the discovery feel earned and contextual
        2. Describes how the character finds the item
        3. Shows the transformation/upgrade process
        4. Reflects the character's growth
        5. Builds anticipation for future adventures
        
        Write in second person ("you") and maintain Transformers universe tone.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"You discover {item.get('name', 'a powerful item')}! {item.get('unlock_message', 'Your power grows!')}"

    def generate_next_event(self, character):
        """Generate a random story event for a character"""
        # Randomly choose between different story types
        story_types = ['encounter', 'event', 'discovery']
        story_type = random.choice(story_types)
        
        if story_type == 'encounter':
            # Get a random monster
            monsters = self._get_enemies_by_type('monster', 'common')
            if monsters:
                monster = random.choice(monsters)
                story = self._build_encounter_story(character, monster, None, {})
                return {
                    'narrative': story,
                    'type': 'monster_encounter',
                    'enemy': monster
                }
        
        elif story_type == 'event':
            # Get a random event
            event = self._get_random_event()
            if event:
                story = self._build_event_story(character, event, {})
                return {
                    'narrative': story,
                    'type': 'random_event',
                    'event': event
                }
        
        elif story_type == 'discovery':
            # Get a random loot item
            loot_items = self._get_transformation_loot('beast_mode')
            if loot_items:
                item = random.choice(loot_items)
                story = self._build_loot_story(character, item, {})
                return {
                    'narrative': story,
                    'type': 'item_discovery',
                    'item': item
                }
        
        # Fallback generic story
        return {
            'narrative': f"As {character.name}, you continue your journey across Cybertron, ever vigilant for new adventures and challenges.",
            'type': 'story'
        }

    # Discord UI Classes for RPG System
    class VotingView(discord.ui.View):
        """Voting system for group decisions"""
        def __init__(self, options: List[str], players: List[discord.User]):
            super().__init__(timeout=60)
            self.options = options
            self.players = players
            self.votes = {}
            self.message = None
            
            for option in options:
                button = discord.ui.Button(
                    label=option,
                    style=discord.ButtonStyle.primary,
                    custom_id=f"vote_{option}"
                )
                button.callback = self.vote_callback
                self.add_item(button)

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.user not in self.players:
                await interaction.response.send_message("You're not part of this adventure!", ephemeral=True)
                return False
            return True

        async def vote_callback(self, interaction: discord.Interaction):
            option = interaction.data['custom_id'].replace('vote_', '')
            
            if interaction.user in self.votes:
                await interaction.response.send_message("You've already voted!", ephemeral=True)
                return

            self.votes[interaction.user] = option
            
            embed = self.message.embeds[0]
            new_embed = discord.Embed(title=embed.title, description=embed.description, color=embed.color)
            
            votes_text = "\n".join([f"{player.display_name}: {vote}" for player, vote in self.votes.items()])
            new_embed.add_field(name="Current Votes", value=votes_text or "No votes yet")
            
            await interaction.response.edit_message(embed=new_embed)

            if len(self.votes) == len(self.players):
                self.stop()

        def tally_votes(self) -> Dict[str, int]:
            vote_counts = {option: 0 for option in self.options}
            for vote in self.votes.values():
                if vote in vote_counts:
                    vote_counts[vote] += 1
            return vote_counts

        def get_winner(self) -> str:
            if not self.votes:
                return random.choice(self.options)
            vote_counts = self.tally_votes()
            max_votes = max(vote_counts.values())
            winners = [opt for opt, count in vote_counts.items() if count == max_votes]
            return random.choice(winners)

    class CharacterSelectionView(discord.ui.View):
        """View for selecting which character to delete via dropdown"""
        
        def __init__(self, rpg_system, user_id):
            super().__init__(timeout=60)
            self.rpg_system = rpg_system
            self.user_id = user_id
            
            # Create dropdown with user's characters
            characters = rpg_system.get_user_characters(user_id)
            options = []
            
            for character in characters:
                faction_emoji = "🔴" if character.faction == "autobot" else "🟣"
                options.append(
                    discord.SelectOption(
                        label=character.name,
                        description=f"Level {character.level} {character.faction.title()} {character.class_type.title()}",
                        emoji=faction_emoji,
                        value=character.name
                    )
                )
            
            self.select_menu = discord.ui.Select(
                placeholder="Select a character to delete...",
                options=options,
                min_values=1,
                max_values=1
            )
            self.select_menu.callback = self.select_callback
            self.add_item(self.select_menu)
        
        async def select_callback(self, interaction: discord.Interaction):
            """Handle character selection"""
            if str(interaction.user.id) != self.user_id:
                await interaction.response.send_message(
                    "❌ You can only delete your own characters!", 
                    ephemeral=True
                )
                return
                
            character_name = self.select_menu.values[0]
            
            # Replace dropdown with confirmation view
            view = ConfirmCharacterDeletionView(self.rpg_system, self.user_id, character_name)
            
            character = None
            for char in self.rpg_system.get_user_characters(self.user_id):
                if char.name == character_name:
                    character = char
                    break
            
            embed = discord.Embed(
                title="⚠️ Confirm Character Deletion",
                description=f"Are you sure you want to permanently delete **{character_name}**?",
                color=0xff0000
            )
            
            embed.add_field(
                name="Character Details",
                value=f"**Level:** {character.level}\n**Faction:** {character.faction.title()}\n**Class:** {character.class_type.title()}",
                inline=False
            )
            embed.set_footer(text="This action cannot be undone!")
            
            await interaction.response.edit_message(embed=embed, view=view)

    class BattleSetupView(discord.ui.View):
        """Setup view for group adventures"""
        def __init__(self, cog):
            super().__init__(timeout=180)
            self.cog = cog
            self.players = []
            self.message = None

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.user.id not in [p.id for p in self.players] and len(self.players) >= 4 and interaction.custom_id == 'join_button':
                await interaction.response.send_message("The party is full!", ephemeral=True)
                return False
            return True

        @discord.ui.button(label="Join Adventure", style=discord.ButtonStyle.success, custom_id='join_button')
        async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user in self.players:
                await interaction.response.send_message("You're already in the party!", ephemeral=True)
                return

            if len(self.players) >= 4:
                await interaction.response.send_message("The party is full!", ephemeral=True)
                return

            self.players.append(interaction.user)
            embed = self.message.embeds[0]
            embed.set_field_at(0, name="Players", value="\n".join([p.display_name for p in self.players]) or "No players yet", inline=False)
            await interaction.response.edit_message(embed=embed)

        @discord.ui.button(label="Leave", style=discord.ButtonStyle.danger)
        async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user not in self.players:
                await interaction.response.send_message("You're not in the party!", ephemeral=True)
                return

            self.players.remove(interaction.user)
            embed = self.message.embeds[0]
            embed.set_field_at(0, name="Players", value="\n".join([p.display_name for p in self.players]) or "No players yet", inline=False)
            await interaction.response.edit_message(embed=embed)

        @discord.ui.button(label="Start Adventure", style=discord.ButtonStyle.primary)
        async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if not self.players:
                await interaction.response.send_message("Need at least one player to start!", ephemeral=True)
                return

            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)

            adventure_type = random.choice(['battle', 'event', 'story'])

            if adventure_type == 'battle':
                battle_types = ['Monster', 'Boss', 'Titan']
                battle_embed = discord.Embed(
                    title="⚔️ Battle Type Selection",
                    description="Choose your opponent wisely...",
                    color=discord.Color.gold()
                )
                battle_view = VotingView(battle_types, self.players)
                await self.message.edit(embed=battle_embed, view=battle_view)
                battle_view.message = self.message
                await battle_view.wait()
                chosen_battle = battle_view.get_winner()

                rarity_options = ['Common', 'Rare', 'Epic', 'Legendary']
                rarity_embed = discord.Embed(
                    title="✨ Enemy Rarity Selection",
                    description="Select the challenge level...",
                    color=discord.Color.gold()
                )
                rarity_view = VotingView(rarity_options, self.players)
                await self.message.edit(embed=rarity_embed, view=rarity_view)
                rarity_view.message = self.message
                await rarity_view.wait()
                chosen_rarity = rarity_view.get_winner()

                await self.cog.start_battle(interaction.channel, self.players, chosen_rarity, chosen_battle)
            elif adventure_type == 'event':
                event = random.choice(self.cog.events_data['events'])
                skill_choices = event['skill_choices']
                
                event_embed = discord.Embed(
                    title="🎲 Event Challenge",
                    description=event['description'],
                    color=discord.Color.green()
                )
                event_embed.add_field(name="Choose Your Approach", value="\n".join(skill_choices))
                
                skill_view = VotingView(skill_choices, self.players)
                await self.message.edit(embed=event_embed, view=skill_view)
                skill_view.message = self.message
                await skill_view.wait()
                chosen_skill = skill_view.get_winner()
                
                await self.cog.handle_event_challenge(interaction.channel, self.players, event, chosen_skill)
            else:
                story = random.choice(self.cog.story_data['segments'])
                await self.cog.handle_story_segment(interaction.channel, self.players, story)

            if hasattr(self.cog, 'cleanup_session'):
                await self.cog.cleanup_session(interaction.channel.id)
            self.stop()

    class CybertronianBattleView(discord.ui.View):
        """Battle view for turn-based combat"""
        def __init__(self, battle_data: Dict, players: List[discord.User], rpg_system):
            super().__init__(timeout=180)
            self.battle_data = battle_data
            self.players = players
            self.rpg_system = rpg_system
            self.current_turn = 0
            self.battle_log = []
            self.message = None
            
            # Initialize player health tracking
            self.player_health = {}
            self.player_max_health = {}
            for player in players:
                character = rpg_system.get_character(str(player.id))
                if character:
                    max_hp = rpg_system.calculate_health_for_level(character.level, character.class_type)
                    self.player_health[str(player.id)] = character.current_health
                    self.player_max_health[str(player.id)] = max_hp
                else:
                    # Default health for new players
                    self.player_health[str(player.id)] = 100
                    self.player_max_health[str(player.id)] = 100

        @discord.ui.button(label="Attack", style=discord.ButtonStyle.danger, custom_id="battle_attack")
        async def attack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user != self.players[self.current_turn]:
                await interaction.response.send_message("It's not your turn!", ephemeral=True)
                return

            # Get character for the attacking player
            character = self.rpg_system.get_character(str(interaction.user.id))

            damage, hit_type, description = process_combat_roll_player(character, self.rpg_system)
            
            if hit_type != "miss":
                self.battle_data['enemy_hp'] -= damage
                self.battle_log.append(f"{interaction.user.display_name}: {description}")
            else:
                self.battle_log.append(f"{interaction.user.display_name}: {description}")
            
            embed = self.get_battle_embed()
            await interaction.response.edit_message(embed=embed, view=self)
            
            if self.battle_data['enemy_hp'] > 0:
                # Enemy turn - get enemy stats
                target = random.choice(self.players)
                
                # For enemies, we'll use base stats from monster data or defaults
                enemy_attack = self.battle_data.get('enemy_attack', 15)
                enemy_defense = self.battle_data.get('enemy_defense', 10)
                
                enemy_damage, enemy_hit_type, enemy_description = process_combat_roll_enemy(enemy_attack, enemy_defense)
                
                if enemy_hit_type != "miss":
                    self.battle_log.append(f"{self.battle_data['enemy_name']}: {enemy_description}")
                else:
                    self.battle_log.append(f"{self.battle_data['enemy_name']}: {enemy_description}")
                
                self.current_turn = (self.current_turn + 1) % len(self.players)
                embed = self.get_battle_embed()
                await self.message.edit(embed=embed, view=self)
            else:
                self.battle_log.append(f"{self.battle_data['enemy_name']} has been defeated!")
                
                # Handle victory rewards and loot distribution
                enemy_name = self.battle_data['enemy_name']
                enemy_rarity = self.battle_data.get('enemy_rarity', 'common')
                enemy_type = self.battle_data.get('enemy_type', 'monster')
                
                # Record combat results for all players
                for player in self.players:
                    self.rpg_system.record_combat_result(str(player.id), enemy_type, enemy_name, True)
                    # Award experience based on enemy type
                    xp_reward = 50 if enemy_type == "monster" else 100 if enemy_type == "boss" else 200
                    self.rpg_system.gain_experience(str(player.id), xp_reward)
                    
                    # Update player health after battle
                    character = self.rpg_system.get_character(str(player.id))
                    if character:
                        character.current_health = self.player_health[str(player.id)]
                
                # Distribute loot to all participating players
                loot_results = self.rpg_system.distribute_loot_to_players(self.players, enemy_rarity, enemy_type)
                
                # Create victory embed with loot information
                victory_embed = discord.Embed(
                    title="🏆 Victory!",
                    description=f"{enemy_name} has been defeated!",
                    color=discord.Color.green()
                )
                
                # Add loot information
                loot_text = ""
                for player in self.players:
                    player_loot = loot_results.get(str(player.id), [])
                    if player_loot:
                        loot_names = [item.get('name', 'Unknown Item') for item in player_loot]
                        loot_text += f"**{player.display_name}:** {', '.join(loot_names)}\n"
                    else:
                        loot_text += f"**{player.display_name}:** No loot dropped\n"
                
                if loot_text:
                    victory_embed.add_field(name="💎 Loot Found", value=loot_text, inline=False)
                
                # Add experience rewards
                xp_reward = 50 if enemy_type == "monster" else 100 if enemy_type == "boss" else 200
                victory_embed.add_field(name="🎯 Experience", value=f"All players gained {xp_reward} XP", inline=True)
                
                # Update the battle embed and send victory message
                embed = self.get_battle_embed()
                for child in self.children:
                    child.disabled = True
                await self.message.edit(embed=embed, view=self)
                
                # Send victory message
                await self.message.channel.send(embed=victory_embed)
                self.stop()

        async def handle_defeat(self):
            """Handle battle defeat when all players are defeated"""
            enemy_name = self.battle_data['enemy_name']
            enemy_rarity = self.battle_data.get('enemy_rarity', 'common')
            enemy_type = self.battle_data.get('enemy_type', 'monster')
            
            # Record combat results for all players
            for player in self.players:
                self.rpg_system.record_combat_result(str(player.id), enemy_type, enemy_name, False)
                
                # Update player health after defeat
                character = self.rpg_system.get_character(str(player.id))
                if character:
                    character.current_health = max(1, self.player_health[str(player.id)])  # Don't let health go to 0 permanently
            
            # Create defeat embed
            defeat_embed = discord.Embed(
                title="💀 Defeat!",
                description=f"All players have been defeated by {enemy_name}!",
                color=discord.Color.red()
            )
            
            # Update the battle embed and send defeat message
            embed = self.get_battle_embed()
            for child in self.children:
                child.disabled = True
            await self.message.edit(embed=embed, view=self)
            
            # Send defeat message
            await self.message.channel.send(embed=defeat_embed)
            self.stop()

        def get_battle_embed(self) -> discord.Embed:
            embed = discord.Embed(
                title=f"⚔️ Battle: {self.battle_data['enemy_name']}",
                description=f"Enemy HP: {self.battle_data['enemy_hp']}/{self.battle_data['enemy_max_hp']}",
                color=discord.Color.red()
            )
            
            # Show player health
            players_text = ""
            for player in self.players:
                player_id = str(player.id)
                health = self.player_health[player_id]
                max_health = self.player_max_health[player_id]
                status = "💀" if health <= 0 else "❤️"
                players_text += f"{status} {player.display_name}: {health}/{max_health} HP\n"
            
            if players_text:
                embed.add_field(name="Players", value=players_text.strip(), inline=False)
            
            # Find current alive player
            alive_players = [p for p in self.players if self.player_health[str(p.id)] > 0]
            if alive_players:
                current_player = alive_players[self.current_turn % len(alive_players)]
                embed.add_field(name="Current Turn", value=current_player.display_name, inline=False)
            
            log_text = "\n".join(self.battle_log[-5:]) if self.battle_log else "Battle started!"
            embed.add_field(name="Battle Log", value=log_text, inline=False)
            
            return embed

    class ConfirmCharacterDeletionView(discord.ui.View):
        """View for confirming character deletion"""
        
        def __init__(self, rpg_system, user_id, character_name):
            super().__init__(timeout=30)
            self.rpg_system = rpg_system
            self.user_id = user_id
            self.character_name = character_name

    class AdventureView(discord.ui.View):
        """Unified adventure view for all battle types"""
        
        def __init__(self, session, show_start_button=False):
            super().__init__()
            self.session = session
            
            if show_start_button:
                self.add_item(self.StartAdventureButton(session))
            
            self.add_item(self.JoinAdventureButton(session))

        class StartAdventureButton(discord.ui.Button):
            def __init__(self, session):
                super().__init__(
                    label="Start Adventure",
                    style=discord.ButtonStyle.green,
                    emoji="🚀",
                    custom_id="start_adventure"
                )
                self.session = session

            async def callback(self, interaction: discord.Interaction):
                """Start the adventure immediately"""
                await interaction.response.send_message("Adventure started!", ephemeral=True)

        class JoinAdventureButton(discord.ui.Button):
            def __init__(self, session):
                super().__init__(
                    label="Join Adventure",
                    style=discord.ButtonStyle.blurple,
                    emoji="👥",
                    custom_id="join_adventure"
                )
                self.session = session

            async def callback(self, interaction: discord.Interaction):
                """Allow user to join the adventure"""
                await interaction.response.send_message("You've joined the adventure!", ephemeral=True)
        
        @discord.ui.button(label="Delete Character", style=discord.ButtonStyle.danger, emoji="💀")
        async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
            """Confirm and delete the character"""
            if str(interaction.user.id) != self.user_id:
                await interaction.response.send_message(
                    "❌ You can only delete your own characters!", 
                    ephemeral=True
                )
                return
            
            try:
                # Delete the character
                success = self.rpg_system.delete_character(self.user_id, self.character_name)
                
                if success:
                    embed = discord.Embed(
                        title="✅ Character Deleted",
                        description=f"**{self.character_name}** has been permanently deleted.",
                        color=0x00ff00
                    )
                    
                    # Disable all buttons
                    for child in self.children:
                        child.disabled = True
                    
                    await interaction.response.edit_message(embed=embed, view=self)
                else:
                    embed = discord.Embed(
                        title="❌ Deletion Failed",
                        description="Could not delete the character. Please try again.",
                        color=0xff0000
                    )
                    await interaction.response.edit_message(embed=embed, view=self)
                    
            except Exception as e:
                embed = discord.Embed(
                    title="❌ Error",
                    description=f"An error occurred while deleting the character: {str(e)}",
                    color=0xff0000
                )
                await interaction.response.edit_message(embed=embed, view=self)
        
        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
        async def cancel_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
            """Cancel character deletion"""
            if str(interaction.user.id) != self.user_id:
                await interaction.response.send_message(
                    "❌ You can only cancel your own deletion!", 
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title="❌ Deletion Cancelled",
                description="Character deletion has been cancelled.",
                color=0x808080
            )
            
            # Disable all buttons
            for child in self.children:
                child.disabled = True
            
            await interaction.response.edit_message(embed=embed, view=self)

    def _build_character_context(self, character) -> str:
        """Build comprehensive character context for AI"""
        return f"""
        Character: {character.name}
        Faction: {character.faction.title()}
        Class: {character.class_type.title()}
        Level: {character.level}
        Experience: {character.experience}
        
        Combat Record:
        - Total Wins: {character.combat_record.total_wins}
        - Total Losses: {character.combat_record.total_losses}
        - Monsters Defeated: {len(character.combat_record.monsters_defeated)}
        - Bosses Defeated: {len(character.combat_record.bosses_defeated)}
        - Titans Defeated: {len(character.combat_record.titans_defeated)}
        
        Equipment:
        - Beast Modes: {', '.join(character.beast_modes) if character.beast_modes else 'None'}
        - Transformations: {', '.join(character.transformations) if character.transformations else 'None'}
        - Weapons: {', '.join(character.weapons) if character.weapons else 'None'}
        - Armor: {', '.join(character.armor) if character.armor else 'None'}
        
        Energon Earned: {character.energon_earned}
        """
    
    # Combat utility functions
    def roll_d5(self) -> int:
        """Roll a d5."""
        return random.randint(1, 5)

    def roll_d6(self) -> int:
        """Roll a d6."""
        return random.randint(1, 6)

    def get_character_main_attribute(self, character) -> int:
        """Get the character's main attribute based on their class."""
        if not character:
            return 10
        
        # Map character classes to their main attribute
        class_attribute_mapping = {
            "warrior": "ATT",
            "scientist": "ATT",
            "mariner": "DEF", 
            "engineer": "DEF",
            "scout": "DEX",
            "seeker": "DEX",
            "commander": "CHA",
            "medic": "CHA"
        }
        
        class_type = character.class_type.lower()
        attribute_name = class_attribute_mapping.get(class_type, "ATT")
        
        return getattr(character.base_stats, attribute_name, 10)

    def process_combat_roll_player(self, character, enemy_data=None) -> tuple:
        """Process combat roll for player attack."""
        if not character:
            return 0, "miss", "No character found"
        
        # Get base attack from character stats
        base_attack = character.base_stats.ATT
        
        # Roll for attack
        roll = self.roll_d6()
        
        # Calculate damage based on roll and stats
        if roll >= 4:  # Hit
            damage = base_attack * roll
            if roll == 6:
                return damage, "critical", f"Critical hit! Dealt {damage} damage"
            else:
                return damage, "hit", f"Hit! Dealt {damage} damage"
        else:
            return 0, "miss", "Attack missed!"

    def process_combat_roll_enemy(self, enemy_attack: int, enemy_defense: int) -> tuple:
        """Process combat roll for enemy attack."""
        # Roll for enemy attack
        roll = self.roll_d6()
        
        # Calculate damage based on roll and stats
        if roll >= 4:  # Hit
            damage = enemy_attack * roll
            if roll == 6:
                return damage, "critical", f"Enemy critical hit! Dealt {damage} damage"
            else:
                return damage, "hit", f"Enemy hit! Dealt {damage} damage"
        else:
            return 0, "miss", "Enemy attack missed!"

    def regenerate_with_same_context(self, character, original_data: Dict[str, Any], 
                                     regeneration_type: str = "encounter") -> Dict[str, Any]:
        """
        Regenerate content with same parameters for continuity
        """
        if regeneration_type == "encounter":
            enemy_type = original_data.get("enemy", {}).get("type", "monster")
            rarity = original_data.get("enemy", {}).get("rarity")
            context = original_data.get("context", {})
            return self.generate_cohesive_encounter(character, enemy_type, rarity, context)
        
        elif regeneration_type == "event":
            context = original_data.get("context", {})
            return self.generate_dynamic_event(character, context=context)
        
        elif regeneration_type == "loot":
            item_type = original_data.get("item", {}).get("type")
            rarity = original_data.get("item", {}).get("rarity")
            context = original_data.get("context", {})
            return self.generate_loot_discovery(character, item_type, rarity, context)
        
        return {}
    
    def save_story_state(self, character_id: str, story_state: Dict[str, Any]) -> bool:
        """Save current story state for continuity"""
        try:
            state_file = os.path.join(self.json_base_path, "story_states", f"{character_id}_story_state.json")
            os.makedirs(os.path.dirname(state_file), exist_ok=True)
            
            with open(state_file, 'w') as f:
                json.dump(story_state, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving story state: {e}")
            return False
    
    def load_story_state(self, character_id: str) -> Dict[str, Any]:
        """Load saved story state for continuity"""
        try:
            state_file = os.path.join(self.json_base_path, "story_states", f"{character_id}_story_state.json")
            with open(state_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}





    def has_cybertronian_role(self, member: discord.Member) -> bool:
        """Check if a member has any Cybertronian role."""
        cybertronian_roles = ['Autobot', 'Decepticon', 'Maverick', 'Cybertronian_Citizen']
        return any(role.name in cybertronian_roles for role in member.roles)

    # CyberChronicles Session and View classes
    class CyberChroniclesSession:
        """Session management for CyberChronicles adventures"""
        
        def __init__(self, channel, rpg_system):
            self.channel = channel
            self.rpg_system = rpg_system
            self.step_participants = {}
            self.current_story = None
            self.current_step = 0
            self.max_steps = 10
            
        def add_step_participant(self, user_id, character_name):
            """Add a participant to the current step"""
            self.step_participants[user_id] = character_name
            
        def reset_step_participants(self):
            """Reset participants for the next step"""
            self.step_participants.clear()
            
        def generate_next_event_preview(self):
            """Generate preview for next event"""
            events = [
                {"type": "Combat", "description": "A fierce battle awaits!"},
                {"type": "Exploration", "description": "Discover hidden secrets of Cybertron"},
                {"type": "Social", "description": "Interact with other Cybertronians"},
                {"type": "Puzzle", "description": "Solve ancient Cybertronian mysteries"}
            ]
            return random.choice(events)

    class CyberChroniclesView(discord.ui.View):
        """View for CyberChronicles adventure interactions"""
        
        def __init__(self, session, show_start_button=False):
            super().__init__(timeout=300)
            self.session = session
            self.message = None
            
            if show_start_button:
                self.add_item(self.StartButton(session))
                
        class StartButton(discord.ui.Button):
            def __init__(self, session):
                super().__init__(label="Start Adventure", style=discord.ButtonStyle.green)
                self.session = session
                
            async def callback(self, interaction: discord.Interaction):
                await interaction.response.send_message("Adventure started!", ephemeral=True)
                self.view.stop()

_rpg_system_instance = None

def get_rpg_system():
    """Get the global RPG system instance (lazy loading)."""
    global _rpg_system_instance
    if _rpg_system_instance is None:
        _rpg_system_instance = TransformersAIDungeonMaster()
    return _rpg_system_instance