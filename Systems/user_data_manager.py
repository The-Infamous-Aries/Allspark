import json
import os
import asyncio
import time
import threading
import heapq
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import logging
from contextlib import asynccontextmanager
import weakref


class UserDataManager:
    """
    High-performance optimized UserDataManager with advanced caching,
    async I/O optimization, and memory management.
    """
    
    def __init__(self, data_directory: str = "Systems/Users"):
        self.base_path = Path(data_directory)
        self.global_saves_path = Path("Systems/Global Saves")
        self.json_path = Path("Systems/Data")
        
        self._loaded_files = set()
        self._loading_in_progress = set()

        self._file_paths = {
            'monsters': self.json_path / "monsters.json",
            'bosses': self.json_path / "bosses.json",
            'titans': self.json_path / "titans.json",
            'pets_level': self.json_path / "pets_level.json",
            'transformation_items': self.json_path / "transformation_items.json",
            'pet_equipment': self.json_path / "pet_equipment.json",
            'recruit': self.json_path / "recruit.json",
            'bot_logs': self.json_path / "bot_logs.json",
            'energon_game': self.global_saves_path / "energon_game.json",
            'cybercoin_market_data': self.global_saves_path / "cybercoin_market_data.json",
            'what_talk': Path("Systems/Random/Talk/what.json"),
            'talk_templates': Path("Systems/Random/Talk/talk_templates.json"),
            'jokes_talk': Path("Systems/Random/Talk/jokes.json"),
            'grump_talk': Path("Systems/Random/Talk/grump.json"),
            'blessings_talk': Path("Systems/Random/Talk/blessings.json"),
            'user_lore': Path("Systems/Random/Talk/user_lore.json")
        }
           
        self._cache = {}
        self._cache_locks = {}
        self._cache_timestamps = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self._max_cache_size = 1000  
        self._cache_ttl = 300  
        self._lazy_cache_ttl = 600 
        self._file_locks = {}
        self._global_lock = asyncio.Lock()
        self._refresh_task = None
        self._shutdown_event = asyncio.Event()
        self._metrics = {
            'reads': 0,
            'writes': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0
        }
        
        self._ensure_directories()
        
        try:
            asyncio.get_running_loop()
            asyncio.create_task(self._start_background_refresh())
        except RuntimeError:

            pass
    
    def _ensure_directories(self):
        """Efficiently ensure all required directories exist"""
        directories = [
            self.base_path, 
            self.global_saves_path, 
            self.json_path,
            Path("Systems/Random/Talk")
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_key(self, file_path: Path) -> str:
        """Generate efficient cache key"""
        return str(file_path.name)
    
    def _should_cache(self, key: str) -> bool:
        """Check if cache entry is still valid"""
        if key not in self._cache_timestamps:
            return False
        
        timestamp = self._cache_timestamps[key]
        return (datetime.now() - timestamp).total_seconds() < self._cache_ttl
    
    def _evict_lru_cache(self):
        """Optimized LRU cache eviction with memory pressure handling"""
        if len(self._cache) <= self._max_cache_size:
            return
        
        to_remove = len(self._cache) - self._max_cache_size + 25
        
        items = list(self._cache_timestamps.items())
        items.sort(key=lambda x: x[1]) 
        
        for key, _ in items[:to_remove]:
            self._cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
            self._cache_locks.pop(key, None)
    
    @asynccontextmanager
    async def _acquire_file_lock(self, file_path: Path):
        """Acquire file-specific lock for concurrent access"""
        file_str = str(file_path)
        if file_str not in self._file_locks:
            self._file_locks[file_str] = asyncio.Lock()
        
        async with self._file_locks[file_str]:
            yield
    
    async def _load_json_optimized(self, file_path: Path, default_data: Any = None, lazy: bool = False) -> Any:
        """Optimized JSON loading with caching and error handling"""
        cache_key = self._get_cache_key(file_path)
        
        if cache_key in self._loading_in_progress:

            while cache_key in self._loading_in_progress:
                await asyncio.sleep(0.001)
            if cache_key in self._cache:
                return self._cache[cache_key]
        

        if cache_key in self._cache and self._should_cache(cache_key):
            self._metrics['cache_hits'] += 1
            return self._cache[cache_key]
        
        self._metrics['cache_misses'] += 1
        self._loading_in_progress.add(cache_key)
        
        try:
            async with self._acquire_file_lock(file_path):
                if cache_key in self._cache and self._should_cache(cache_key):
                    return self._cache[cache_key]
                
                if file_path.exists():
                    try:
                        import rapidjson
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = rapidjson.load(f)
                    except (ImportError, Exception):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                else:
                    data = default_data or {}

                    await self._save_json_optimized(file_path, data)
                
                self._cache[cache_key] = data
                ttl = self._lazy_cache_ttl if lazy else self._cache_ttl
                self._cache_timestamps[cache_key] = datetime.now()
                self._loaded_files.add(cache_key)
                self._evict_lru_cache()
                
                return data
                
        except Exception as e:
            self._metrics['errors'] += 1
            logging.error(f"Error loading {file_path}: {e}")
            return default_data or {}
        finally:
            self._loading_in_progress.discard(cache_key)
    
    async def _save_json_optimized(self, file_path: Path, data: Any) -> bool:
        async with self._acquire_file_lock(file_path):
            try:
                temp_path = file_path.with_suffix('.tmp')
                
                try:
                    import rapidjson
                    with open(temp_path, 'w', encoding='utf-8') as f:
                        rapidjson.dump(data, f, indent=2)
                except (ImportError, Exception):
                    with open(temp_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                
                temp_path.replace(file_path)
                
                cache_key = self._get_cache_key(file_path)
                self._cache[cache_key] = data
                self._cache_timestamps[cache_key] = datetime.now()
                
                self._metrics['writes'] += 1
                return True
                
            except Exception as e:
                self._metrics['errors'] += 1
                logging.error(f"Error saving {file_path}: {e}")
                return False
    
    async def _start_background_refresh(self):
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(60)
                
                current_time = datetime.now()
                expired_keys = []
                
                for key, timestamp in self._cache_timestamps.items():
                    ttl = self._lazy_cache_ttl if key in self._loaded_files else self._cache_ttl
                    if (current_time - timestamp).total_seconds() > ttl:
                        expired_keys.append(key)
                
                for key in expired_keys:
                    if key not in self._loaded_files or len(self._cache) > self._max_cache_size:
                        self._cache.pop(key, None)
                        self._cache_timestamps.pop(key, None)
                    
            except Exception as e:
                logging.error(f"Background refresh error: {e}")
    
    # User Data Methods (Optimized)
    def _get_user_file_path(self, user_id: str) -> Path:
        return self.base_path / f"{user_id}.json"
    
    def _create_default_user_data(self, user_id: str, username: str) -> Dict[str, Any]:
        now = datetime.now().isoformat()
        return {
            "user_id": user_id,
            "username": username,
            "created_at": now,
            "last_updated": now,
            "rpg": {
                "characters": [],
                "active_character": None,
                "energon_earned": 0,
                "combat_record": {
                    "monsters_defeated": {},
                    "monsters_lost_to": {},
                    "bosses_defeated": {},
                    "bosses_lost_to": {},
                    "titans_defeated": {},
                    "titans_lost_to": {},
                    "total_wins": 0,
                    "total_losses": 0,
                    "total_damage_dealt": 0
                }
            },
            "pets": {"pet_data": None},
            "energon_rush": {"high_score": 0, "games_played": 0, "total_energon_collected": 0},
            "shooting_range": {
                "high_score": 0, "games_played": 0, "accuracy": 0.0,
                "total_targets_hit": 0, "total_hits": 0, "total_shots": 0,
                "sessions_played": 0,
                "best_records": {"5": {"accuracy": 0, "hits": 0}, "15": {"accuracy": 0, "hits": 0},
                               "25": {"accuracy": 0, "hits": 0}, "50": {"accuracy": 0, "hits": 0},
                               "100": {"accuracy": 0, "hits": 0}},
                "round_attempts": {}
            },
            "mega_fights": {
                "mega_fights_won": 0, "mega_fights_lost": 0,
                "total_energon_won": 0, "total_energon_lost": 0, "total_fights": 0
            },
            "slot_machine": {
                "total_games_played": 0, "total_winnings": 0, "total_losses": 0,
                "jackpots_won": 0, "two_matches_won": 0, "highest_bet": 0,
                "highest_win": 0, "games_by_difficulty": {"easy": 0, "medium": 0, "hard": 0},
                "winnings_by_difficulty": {"easy": 0, "medium": 0, "hard": 0}
            },
            "energon": {"energon": 0},
            "cybercoin_market": {
                "portfolio": {"total_coins": 0, "total_invested": 0, "total_sold": 0, "total_profit": 0, "current_value": 0},
                "transactions": {"purchases": [], "sales": []},
                "holdings": []
            },
            "theme_system": {
                "transformer_name": None, "transformer_faction": None, "transformer_class": None,
                "combiner_teams": [], "current_combiner_team": None, "combiner_role": None,
                "combiner_history": []
            }
        }
    
    async def get_user_data(self, user_id: str, username: str = None) -> Dict[str, Any]:
        """Get user data with username update optimization"""
        file_path = self._get_user_file_path(user_id)
        
        if not file_path.exists():
            return self._create_default_user_data(user_id, username or "Unknown")
        
        data = await self._load_json_optimized(file_path)
        
        # Efficient username update
        if username and data.get("username") != username:
            data["username"] = username
            await self.save_user_data(user_id, username, data)
        
        return data
    
    async def save_user_data(self, user_id: str, username: str, data: Dict[str, Any]) -> bool:
        """Save user data with atomic operations"""
        file_path = self._get_user_file_path(user_id)
        
        # Update timestamp efficiently
        data["last_updated"] = datetime.now().isoformat()
        if username:
            data["username"] = username
        
        return await self._save_json_optimized(file_path, data)
    
    # RPG Methods (Batch Optimized)
    async def save_rpg_character(self, user_id: str, username: str, character: Dict[str, Any]) -> bool:
        """Save RPG character with batch optimization"""
        user_data = await self.get_user_data(user_id, username)
        characters = user_data.get("rpg", {}).get("characters", [])
        
        # Efficient character update/insert
        char_name = character.get("name")
        for i, char in enumerate(characters):
            if char.get("name") == char_name:
                characters[i] = character
                break
        else:
            characters.append(character)
        
        user_data.setdefault("rpg", {})["characters"] = characters
        return await self.save_user_data(user_id, username, user_data)
    
    async def get_rpg_character(self, user_id: str, username: str, character_name: str) -> Optional[Dict[str, Any]]:
        """Get RPG character efficiently"""
        user_data = await self.get_user_data(user_id, username)
        characters = user_data.get("rpg", {}).get("characters", [])
        
        return next((char for char in characters if char.get("name") == character_name), None)
    
    async def get_all_rpg_characters(self, user_id: str, username: str) -> list:
        """Get all RPG characters"""
        user_data = await self.get_user_data(user_id, username)
        return user_data.get("rpg", {}).get("characters", [])
    
    async def delete_rpg_character(self, user_id: str, username: str, character_name: str) -> bool:
        """Delete RPG character efficiently"""
        user_data = await self.get_user_data(user_id, username)
        characters = user_data.get("rpg", {}).get("characters", [])
        
        original_len = len(characters)
        characters[:] = [char for char in characters if char.get("name") != character_name]
        
        if len(characters) < original_len:
            return await self.save_user_data(user_id, username, user_data)
        return False

    async def get_slot_machine_data(self, player_id: str, username: str = None) -> Dict[str, Any]:
        """Get slot machine statistics for a player"""
        user_data = await self.get_user_data(player_id, username)
        return user_data.get("slot_machine", {
            "total_games_played": 0,
            "total_winnings": 0,
            "total_losses": 0,
            "jackpots_won": 0,
            "two_matches_won": 0,
            "highest_bet": 0,
            "highest_win": 0,
            "games_by_difficulty": {"easy": 0, "medium": 0, "hard": 0},
            "winnings_by_difficulty": {"easy": 0, "medium": 0, "hard": 0}
        })

    async def save_slot_machine_data(self, player_id: str, username: str, data: Dict[str, Any]) -> bool:
        """Save slot machine statistics for a player"""
        user_data = await self.get_user_data(player_id, username)
        user_data["slot_machine"] = data
        return await self.save_user_data(player_id, username, user_data)

    # Theme System Methods (Optimized)
    async def get_theme_system_data(self, user_id: str, username: str) -> Dict[str, Any]:
        """Get theme system data efficiently"""
        user_data = await self.get_user_data(user_id, username)
        return user_data.get("theme_system", {})
    
    async def get_user_theme_data(self, user_id: str, username: str = None) -> Dict[str, Any]:
        """Get theme system data (alias for get_theme_system_data)"""
        return await self.get_theme_system_data(user_id, username)
    
    async def save_theme_system_data(self, user_id: str, username: str, theme_data: Dict[str, Any]) -> bool:
        """Save theme system data"""
        user_data = await self.get_user_data(user_id, username)
        user_data["theme_system"] = theme_data
        return await self.save_user_data(user_id, username, user_data)
    
    async def add_user_to_combiner_team(self, user_id: str, username: str, team_id: str, role: str, team_data: Dict[str, Any]) -> bool:
        """Add user to combiner team with optimization"""
        user_data = await self.get_user_data(user_id, username)
        theme_data = user_data.get("theme_system", {})
        
        # Efficient team management
        current_team = theme_data.get("current_combiner_team")
        if current_team and current_team != team_id:
            await self.remove_user_from_combiner_team(user_id, username, current_team)
        
        # Update team data
        teams = theme_data.setdefault("combiner_teams", [])
        if team_id not in teams:
            teams.append(team_id)
        
        theme_data.update({
            "current_combiner_team": team_id,
            "combiner_role": role.lower()
        })
        
        # Add to history
        history = theme_data.setdefault("combiner_history", [])
        if not any(h.get("team_id") == team_id for h in history):
            history.append({
                "team_id": team_id,
                "role": role.lower(),
                "joined_at": datetime.now().isoformat(),
                "team_data": team_data
            })
        
        return await self.save_theme_system_data(user_id, username, theme_data)
    
    async def remove_user_from_combiner_team(self, user_id: str, username: str, team_id: str) -> bool:
        """Remove user from combiner team"""
        theme_data = await self.get_theme_system_data(user_id, username)
        
        teams = theme_data.get("combiner_teams", [])
        if team_id in teams:
            teams.remove(team_id)
        
        if theme_data.get("current_combiner_team") == team_id:
            theme_data["current_combiner_team"] = None
            theme_data["combiner_role"] = None
        
        return await self.save_theme_system_data(user_id, username, theme_data)
    
    async def get_user_combiner_team(self, user_id: str, username: str = None) -> Optional[Dict[str, Any]]:
        """Get user combiner team efficiently"""
        theme_data = await self.get_theme_system_data(user_id, username)
        current_team = theme_data.get("current_combiner_team")
        
        if not current_team:
            return None
        
        # Find most recent team info
        history = theme_data.get("combiner_history", [])
        return next((h for h in reversed(history) if h.get("team_id") == current_team), None)
    
    # JSON Data Methods (All Optimized)
    async def get_monsters_and_bosses(self) -> Dict[str, Any]:
        """Load monsters, bosses, and titans from separate JSON files and combine them"""
        try:
            # Load from separate files
            monsters = await self._load_json_optimized(self._file_paths['monsters'], {}, lazy=True)
            bosses = await self._load_json_optimized(self._file_paths['bosses'], {}, lazy=True)
            titans = await self._load_json_optimized(self._file_paths['titans'], {}, lazy=True)
            
            # Combine into the expected structure
            combined_data = {
                'rarity_colors': {},  # Will be populated from the first available file
                'monsters': monsters if isinstance(monsters, dict) else {},
                'bosses': bosses if isinstance(bosses, dict) else {},
                'titans': titans if isinstance(titans, dict) else {}
            }
            
            # Try to get rarity_colors from any file that has it
            for data in [monsters, bosses, titans]:
                if isinstance(data, dict) and 'rarity_colors' in data:
                    combined_data['rarity_colors'] = data['rarity_colors']
                    break
            
            return combined_data
            
        except Exception as e:
            logging.error(f"Error loading monsters and bosses from separate files: {e}")
            return {'rarity_colors': {}, 'monsters': {}, 'bosses': {}, 'titans': {}}

    async def save_monsters_and_bosses(self, data: Dict[str, Any]) -> bool:
        """Save to separate JSON files - splits the combined data"""
        try:
            # Split the data by type
            monsters_data = data.get('monsters', {})
            bosses_data = data.get('bosses', {})
            titans_data = data.get('titans', {})
            
            # Add rarity_colors to each file if it exists
            if 'rarity_colors' in data:
                for file_data in [monsters_data, bosses_data, titans_data]:
                    if file_data:  # Only add to non-empty files
                        file_data['rarity_colors'] = data['rarity_colors']
            
            # Save to separate files
            success = True
            if monsters_data:
                success &= await self._save_json_optimized(self._file_paths['monsters'], monsters_data)
            if bosses_data:
                success &= await self._save_json_optimized(self._file_paths['bosses'], bosses_data)
            if titans_data:
                success &= await self._save_json_optimized(self._file_paths['titans'], titans_data)
                
            return success
            
        except Exception as e:
            logging.error(f"Error saving monsters and bosses to separate files: {e}")
            return False
    
    async def get_monster(self, monster_id: str) -> Optional[Dict[str, Any]]:
        monsters = await self.get_monsters_and_bosses()
        return monsters.get(monster_id)
    
    async def add_monster(self, monster_id: str, monster_data: Dict[str, Any]) -> bool:
        monsters = await self.get_monsters_and_bosses()
        monsters[monster_id] = monster_data
        return await self.save_monsters_and_bosses(monsters)
    
    async def get_pets_level_data(self) -> Dict[str, Any]:
        return await self._load_json_optimized(self._file_paths['pets_level'], {}, lazy=True)
    
    async def get_monsters_and_bosses_data(self) -> Dict[str, Any]:
        """Alias for get_monsters_and_bosses to maintain backward compatibility"""
        return await self.get_monsters_and_bosses()
    
    async def get_transformation_items_data(self) -> Dict[str, Any]:
        return await self._load_json_optimized(self._file_paths['transformation_items'], {}, lazy=True)

    async def get_pet_equipment_data(self) -> Dict[str, Any]:
        """Load pet equipment data including chassis_plating, energy_cores, and utility_modules"""
        return await self._load_json_optimized(self._file_paths['pet_equipment'], {}, lazy=True)

    async def get_chassis_plating_by_rarity(self, rarity: str) -> Dict[str, Any]:
        """Get chassis plating items by rarity"""
        equipment_data = await self.get_pet_equipment_data()
        chassis_data = equipment_data.get('chassis_plating', {})
        return chassis_data.get('equipment', {}).get(rarity.lower(), {})

    async def get_energy_cores_by_rarity(self, rarity: str) -> Dict[str, Any]:
        """Get energy cores by rarity"""
        equipment_data = await self.get_pet_equipment_data()
        energy_data = equipment_data.get('energy_cores', {})
        return energy_data.get('equipment', {}).get(rarity.lower(), {})

    async def get_utility_modules_by_rarity(self, rarity: str) -> Dict[str, Any]:
        """Get utility modules by rarity"""
        equipment_data = await self.get_pet_equipment_data()
        utility_data = equipment_data.get('utility_modules', {})
        return utility_data.get('equipment', {}).get(rarity.lower(), {})

    async def get_all_pet_equipment_by_rarity(self, rarity: str) -> Dict[str, Dict[str, Any]]:
        """Get all pet equipment types (chassis_plating, energy_cores, utility_modules) by rarity"""
        return {
            'chassis_plating': await self.get_chassis_plating_by_rarity(rarity),
            'energy_cores': await self.get_energy_cores_by_rarity(rarity),
            'utility_modules': await self.get_utility_modules_by_rarity(rarity)
        }

    async def get_pet_equipment_item(self, item_type: str, rarity: str, item_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific pet equipment item by type, rarity, and ID"""
        equipment_data = await self.get_pet_equipment_data()
        type_data = equipment_data.get(item_type, {})
        return type_data.get('equipment', {}).get(rarity.lower(), {}).get(item_id)

    async def get_pet_equipment_by_type(self, item_type: str) -> Dict[str, Any]:
        """Get all pet equipment of a specific type across all rarities"""
        equipment_data = await self.get_pet_equipment_data()
        type_data = equipment_data.get(item_type, {})
        return type_data.get('equipment', {})

    async def save_pets_level_data(self, data: Dict[str, Any]) -> bool:
        return await self._save_json_optimized(self._file_paths['pets_level'], data)
    
    async def save_monsters_and_bosses_data(self, data: Dict[str, Any]) -> bool:
        return await self._save_json_optimized(self._file_paths['monsters_and_bosses'], data)
    
    async def save_transformation_items_data(self, data: Dict[str, Any]) -> bool:
        return await self._save_json_optimized(self._file_paths['transformation_items'], data)

    # Pet Data Management Methods
    async def get_pet_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a user's pet data from their user file with legacy migration"""
        user_data = await self.get_user_data(user_id)
        pet_data = user_data.get("pets", {}).get("pet_data")
        
        if pet_data:
            # Migrate legacy pet data if needed
            pet_data = await self._migrate_legacy_pet_data(pet_data)
            
        return pet_data

    async def save_pet_data(self, user_id: str, username: str, pet_data: Dict[str, Any]) -> bool:
        """Save a user's pet data to their user file"""
        user_data = await self.get_user_data(user_id, username)
        if "pets" not in user_data:
            user_data["pets"] = {}
        user_data["pets"]["pet_data"] = pet_data
        return await self.save_user_data(user_id, username, user_data)

    async def delete_pet_data(self, user_id: str) -> bool:
        """Delete a user's pet data from their user file"""
        user_data = await self.get_user_data(str(user_id))
        if "pets" in user_data and "pet_data" in user_data["pets"]:
            del user_data["pets"]["pet_data"]
            return await self.save_user_data(str(user_id), None, user_data)
        return False

    async def _migrate_legacy_pet_data(self, pet_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate legacy pet data to include inventory and equipment fields"""
        # Check if migration is needed
        if "inventory" not in pet_data or "equipment" not in pet_data:
            # Create backup of original data
            pet_data.setdefault("_legacy_backup", pet_data.copy())
            
            # Ensure inventory exists
            if "inventory" not in pet_data:
                pet_data["inventory"] = []
            
            # Ensure equipment exists with proper structure
            if "equipment" not in pet_data:
                pet_data["equipment"] = {
                    "chassis_plating": None,
                    "energy_cores": None,
                    "utility_modules": None
                }
            elif not isinstance(pet_data["equipment"], dict):
                # Handle case where equipment might be in old format
                pet_data["equipment"] = {
                    "chassis_plating": None,
                    "energy_cores": None,
                    "utility_modules": None
                }
            
            # Ensure all required fields exist
            pet_data.setdefault("attack", 10)
            pet_data.setdefault("defense", 5)
            pet_data.setdefault("max_energy", 100)
            pet_data.setdefault("max_maintenance", 100)
            pet_data.setdefault("max_happiness", 100)
            
        return pet_data

    async def get_all_pets_data(self) -> Dict[str, Dict[str, Any]]:
        """Get all pets data across all users (for admin/stats purposes)"""
        pets_data = {}
        users_dir = self.base_path

        if not users_dir.exists():
            return pets_data

        for user_file in users_dir.glob("*.json"):
            try:
                user_id = user_file.stem
                user_data = await self._load_json_optimized(user_file)
                pet_data = user_data.get("pets", {}).get("pet_data")
                if pet_data:
                    # Ensure migration happens when getting all pets
                    pet_data = await self._migrate_legacy_pet_data(pet_data)
                    pets_data[user_id] = pet_data
            except Exception as e:
                logging.error(f"Error loading pet data for user {user_file.stem}: {e}")

        return pets_data

    async def migrate_all_pet_data(self) -> Dict[str, Any]:
        """
        Migrate all existing pet data to include inventory and equipment fields
        Returns: Migration summary with counts
        """
        migration_summary = {
            "total_pets": 0,
            "migrated_pets": 0,
            "errors": [],
            "users_processed": []
        }
        
        try:
            users_dir = self.base_path
            if not users_dir.exists():
                return migration_summary

            for user_file in users_dir.glob("*.json"):
                user_id = user_file.stem
                try:
                    user_data = await self._load_json_optimized(user_file)
                    pet_data = user_data.get("pets", {}).get("pet_data")
                    
                    if pet_data:
                        migration_summary["total_pets"] += 1
                        
                        # Check if migration is needed
                        needs_migration = (
                            "inventory" not in pet_data or 
                            "equipment" not in pet_data or
                            not isinstance(pet_data.get("equipment"), dict)
                        )
                        
                        if needs_migration:
                            # Migrate the pet data
                            migrated_pet = await self._migrate_legacy_pet_data(pet_data)
                            user_data["pets"]["pet_data"] = migrated_pet
                            
                            # Save the migrated data
                            username = user_data.get("username", f"user_{user_id}")
                            success = await self.save_pet_data(user_id, username, migrated_pet)
                            
                            if success:
                                migration_summary["migrated_pets"] += 1
                                migration_summary["users_processed"].append(user_id)
                            else:
                                migration_summary["errors"].append(f"Failed to save migrated data for {user_id}")
                        
                except Exception as e:
                    migration_summary["errors"].append(f"Error processing {user_id}: {str(e)}")
                    logging.error(f"Error migrating pet data for {user_id}: {e}")

            logging.info(f"Pet data migration completed: {migration_summary}")
            return migration_summary
            
        except Exception as e:
            migration_summary["errors"].append(f"Migration failed: {str(e)}")
            logging.error(f"Pet data migration failed: {e}")
            return migration_summary

    async def get_pet_level_info(self, pet_type: str) -> Optional[Dict[str, Any]]:
        pets_data = await self.get_pets_level_data()
        return pets_data.get(pet_type)

    async def get_transformation_items(self) -> Dict[str, Any]:
        return await self._load_json_optimized(self._file_paths['transformation_items'], {}, lazy=True)

    async def get_transformation_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        items = await self.get_transformation_items()
        return items.get(item_id)

    # Recruitment Data
    async def get_recruit_data(self) -> Dict[str, Any]:
        return await self._load_json_optimized(self._file_paths['recruit'], {}, lazy=True)

    async def save_recruit_data(self, data: Dict[str, Any]) -> bool:
        return await self._save_json_optimized(self._file_paths['recruit'], data)

    async def get_recruit_entry(self, recruit_id: str) -> Optional[Dict[str, Any]]:
        recruits = await self.get_recruit_data()
        return recruits.get(recruit_id)

    async def add_recruit_entry(self, recruit_id: str, recruit_data: Dict[str, Any]) -> bool:
        recruits = await self.get_recruit_data()
        recruits[recruit_id] = recruit_data
        return await self.save_recruit_data(recruits)

    # Bot Logs Data
    async def get_bot_logs(self) -> Dict[str, Any]:
        return await self._load_json_optimized(self._file_paths['bot_logs'], {"logs": []}, lazy=True)

    async def save_bot_logs(self, data: Dict[str, Any]) -> bool:
        return await self._save_json_optimized(self._file_paths['bot_logs'], data)

    async def add_bot_log(self, log_entry: Dict[str, Any]) -> bool:
        logs = await self.get_bot_logs()
        logs.setdefault("logs", []).append(log_entry)
        return await self.save_bot_logs(logs)

    # CyberCoin Market Data
    async def get_cybercoin_market_data(self) -> Dict[str, Any]:
        return await self._load_json_optimized(self._file_paths['cybercoin_market_data'], 
                                           {"market_data": {}, "last_updated": None}, lazy=True)

    async def save_cybercoin_market_data(self, data: Dict[str, Any]) -> bool:
        return await self._save_json_optimized(self._file_paths['cybercoin_market_data'], data)



    # Backward compatibility methods

    async def get_what_talk_data(self) -> Dict[str, Any]:
        return await self._load_json_optimized(self._file_paths['what_talk'], {}, lazy=True)

    async def get_talk_templates_data(self) -> Dict[str, Any]:
        return await self._load_json_optimized(self._file_paths['talk_templates'], {}, lazy=True)

    async def get_jokes_talk_data(self) -> Dict[str, Any]:
        return await self._load_json_optimized(self._file_paths['jokes_talk'], {}, lazy=True)

    async def get_grump_talk_data(self) -> Dict[str, Any]:
        return await self._load_json_optimized(self._file_paths['grump_talk'], {}, lazy=True)

    async def get_blessings_talk_data(self) -> Dict[str, Any]:
        return await self._load_json_optimized(self._file_paths['blessings_talk'], {}, lazy=True)

    async def get_user_lore_data(self) -> Dict[str, Any]:
        return await self._load_json_optimized(self._file_paths['user_lore'], {}, lazy=True)

    async def save_user_lore_data(self, data: Dict[str, Any]) -> bool:
        return await self._save_json_optimized(self._file_paths['user_lore'], data)
    

    
    # Utility Methods
    async def reload_all_json_data(self) -> bool:
        """Clear all caches"""
        self._cache.clear()
        self._cache_timestamps.clear()
        self._cache_locks.clear()
        return True
    
    async def get_all_json_data(self) -> Dict[str, Any]:
        """Get all JSON data for debugging - optimized for all file types"""
        return {
            "monsters": await self._load_json_optimized(self._file_paths['monsters'], {}, lazy=True),
            "bosses": await self._load_json_optimized(self._file_paths['bosses'], {}, lazy=True),
            "titans": await self._load_json_optimized(self._file_paths['titans'], {}, lazy=True),
            "pets_level": await self.get_pets_level_data(),
            "transformation_items": await self.get_transformation_items(),
            "recruit": await self.get_recruit_data(),
            "bot_logs": await self.get_bot_logs(),
            "cybercoin_market_data": await self.get_cybercoin_market_data(),
            
            # Random talk data
            "what_talk": await self.get_what_talk_data(),
            "talk_templates": await self.get_talk_templates_data(),
            "jokes_talk": await self.get_jokes_talk_data(),
            "grump_talk": await self.get_grump_talk_data(),
            "blessings_talk": await self.get_blessings_talk_data(),
            "user_lore": await self.get_user_lore_data()
        }
    
    async def get_energon_data(self, player_id: str) -> Dict[str, Any]:
        """Get energon data for a player - unified across all systems"""
        try:
            user_data = await self.get_user_data(player_id, "EnergonPlayer")
            energon_data = user_data.get("energon", {})
            
            # Ensure all required fields exist
            default_data = self._get_default_energon_data()
            for key, default_value in default_data.items():
                if key not in energon_data:
                    energon_data[key] = default_value
            
            return energon_data
            
        except Exception as e:
            logging.error(f"Error getting energon data for {player_id}: {e}")
            return self._get_default_energon_data()

    async def save_energon_data(self, player_id: str, energon_data: Dict[str, Any]) -> bool:
        """Save energon data for a player"""
        try:
            user_data = await self.get_user_data(player_id, "EnergonPlayer")
            user_data["energon"] = energon_data
            return await self.save_user_data(player_id, "EnergonPlayer", user_data)
            
        except Exception as e:
            logging.error(f"Error saving energon data for {player_id}: {e}")
            return False

    async def update_energon_stat(self, player_id: str, stat_name: str, value: Any) -> bool:
        """Update a specific energon stat for a player - maintains backward compatibility"""
        try:
            energon_data = await self.get_energon_data(player_id)
            energon_data[stat_name] = value
            return await self.save_energon_data(player_id, energon_data)
        except Exception as e:
            logging.error(f"Error updating energon stat {stat_name} for {player_id}: {e}")
            return False

    async def get_energon_stats(self, player_id: str) -> Dict[str, Any]:
        """Get all energon stats for a player - backward compatibility"""
        return await self.get_energon_data(player_id)

    async def get_energon_game_state(self, channel_id: str = None) -> Dict[str, Any]:
        """Get energon game state for a channel or global state"""
        try:
            if channel_id is None:
                # Get global energon game state
                user_data = await self.get_user_data("energon_global")
                return user_data.get('energon_game_state', self._get_default_energon_game_state())
            else:
                # Get per-channel game state
                user_data = await self.get_user_data(str(channel_id))
                return user_data.get('energon_game_state', self._get_default_energon_game_state())
        except Exception as e:
            logging.error(f"Error getting energon game state for {channel_id}: {e}")
            return self._get_default_energon_game_state()

    async def save_energon_game_state(self, channel_id: str = None, data: Dict[str, Any] = None) -> bool:
        """Save energon game state for a channel or global state"""
        try:
            if channel_id is None:
                # Save global energon game state
                try:
                    user_data = await self.get_user_data("energon_global")
                except:
                    user_data = {}
                
                user_data['energon_game_state'] = data
                return await self.save_user_data("energon_global", "energon_system", user_data)
            else:
                # Save per-channel game state
                try:
                    user_data = await self.get_user_data(str(channel_id))
                except:
                    user_data = {}
                
                user_data['energon_game_state'] = data
                return await self.save_user_data(str(channel_id), "energon_channel", user_data)
        except Exception as e:
            logging.error(f"Error saving energon game state for {channel_id}: {e}")
            return False

    async def get_global_energon_game_state(self) -> Dict[str, Any]:
        """Get global energon game state (backward compatibility)"""
        return await self.get_energon_game_state()

    async def save_global_energon_game_state(self, data: Dict[str, Any]) -> bool:
        """Save global energon game state (backward compatibility)"""
        return await self.save_energon_game_state(None, data)

    def _get_default_energon_data(self) -> Dict[str, Any]:
        """Get optimized default energon data structure - unified across all game systems"""
        return {
            'energon': 0,           # Current game energon (in-game balance)
            'energon_bank': 0,      # Banked energon (persistent balance)
            'total_earned': 0,      # Lifetime energon earned
            'total_spent': 0,       # Lifetime energon spent
            'games_played': 0,      # Total games played across all systems
            'games_won': 0,         # Total games won
            'games_lost': 0,        # Total games lost
            'last_activity': None,  # Last energon activity timestamp
            'daily_energon_claimed': False,
            'last_daily_claim': None,
            'streak': 0,
            'achievements': [],
            'cybercoins': 0.0,
            'pet_bonus': 0,
            'in_energon_rush': False,
            'pet_energon_earned': 0,  # Energon earned through pet activities
            'battle_energon_earned': 0,  # Energon earned through battles
            'search_energon_earned': 0,  # Energon earned through searches
            'slots_energon_earned': 0,   # Energon earned through slots
            'challenge_energon_earned': 0  # Energon earned through challenges
        }

    def _get_default_energon_game_state(self) -> Dict[str, Any]:
        """Get optimized energon game state structure"""
        return {
            'game_data': {},           # Active game sessions by player
            'challenges': {},          # Active challenges
            'cooldowns': {},           # Player cooldowns
            'global_stats': {
                'total_games': 0,
                'total_energon_won': 0,
                'total_energon_lost': 0,
                'active_players': [],
                'last_game_end': None,
                'daily_reset': None
            },
            'leaderboard': {            # Cross-system leaderboard
                'daily': {},
                'weekly': {},
                'all_time': {}
            },
            'system_status': {        # System health tracking
                'last_cleanup': None,
                'active_games': 0,
                'total_players': 0
            },
            'last_updated': None
        }

    async def get_energon_summary(self, player_id: str) -> Dict[str, Any]:
        """Optimized energon summary with concurrent data loading"""
        try:
            energon_data = await self.get_energon_data(player_id)
            
            # Pre-calculate values to reduce lookups
            game_energon = energon_data.get('energon', 0)
            banked_energon = energon_data.get('energon_bank', 0)
            games_played = energon_data.get('games_played', 0)
            games_won = energon_data.get('games_won', 0)
            
            return {
                'current_balance': {
                    'game_energon': game_energon,
                    'banked_energon': banked_energon,
                    'total_energon': game_energon + banked_energon
                },
                'lifetime_stats': {
                    'total_earned': energon_data.get('total_earned', 0),
                    'total_spent': energon_data.get('total_spent', 0),
                    'games_played': games_played,
                    'win_rate': (games_won / games_played * 100) if games_played > 0 else 0.0
                },
                'source_breakdown': {
                    'pet_earnings': energon_data.get('pet_energon_earned', 0),
                    'battle_earnings': energon_data.get('battle_energon_earned', 0),
                    'search_earnings': energon_data.get('search_energon_earned', 0),
                    'slots_earnings': energon_data.get('slots_energon_earned', 0),
                    'challenge_earnings': energon_data.get('challenge_energon_earned', 0)
                },
                'last_activity': energon_data.get('last_activity'),
                'achievements': energon_data.get('achievements', [])
            }
            
        except Exception as e:
            logging.error(f"Error getting energon summary for {player_id}: {e}")
            return {}

    async def cleanup_inactive_data(self, days_inactive: int = 30) -> int:
        """Optimized cleanup for inactive player data"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_inactive)
            cleaned_count = 0
            
            # Use pathlib for efficient file operations
            user_files = list(self.base_path.glob("*.json"))
            
            # Process files in batches for better performance
            batch_size = 50
            for i in range(0, len(user_files), batch_size):
                batch = user_files[i:i+batch_size]
                
                # Process batch concurrently
                tasks = []
                for file_path in batch:
                    user_id = file_path.stem
                    if user_id not in ["energon_global", "energon_system"]:
                        tasks.append(self._cleanup_single_user(user_id, cutoff_date))
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                cleaned_count += sum(1 for r in results if r is True)
            
            return cleaned_count
            
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
            return 0
    
    async def _cleanup_single_user(self, user_id: str, cutoff_date: datetime) -> bool:
        """Clean up a single user's inactive data"""
        try:
            energon_data = await self.get_energon_data(user_id)
            last_activity = energon_data.get('last_activity')
            
            if last_activity:
                last_activity_date = datetime.fromisoformat(last_activity)
                if last_activity_date < cutoff_date:
                    # Clean only game state, preserve balances
                    energon_data.update({
                        'in_energon_rush': False,
                        'daily_energon_claimed': False,
                        'last_daily_claim': None
                    })
                    
                    await self.save_energon_data(user_id, energon_data)
                    return True
            
            return False
            
        except Exception:
            return False

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        total_ops = self._metrics['cache_hits'] + self._metrics['cache_misses']
        cache_ratio = (self._metrics['cache_hits'] / total_ops * 100) if total_ops > 0 else 0
        
        return {
            **self._metrics,
            'cache_ratio': cache_ratio,
            'cache_size': len(self._cache),
            'memory_usage': len(self._cache) * 1024  # Approximate
        }
    
    async def shutdown(self):
        """Graceful shutdown"""
        self._shutdown_event.set()
        if self._refresh_task:
            await self._refresh_task
    
    # Data Validation (Optimized)
    def _validate_structure(self, data: Dict[str, Any], required_fields: List[str]) -> bool:
        """Fast structure validation"""
        return all(field in data for field in required_fields)
    
    async def validate_all_json_files(self) -> Dict[str, bool]:
        """Fast validation of all JSON files with comprehensive coverage"""
        validators = {
            # Core game data - top-level keys
            'monsters': ['rarity_colors','monsters'],
            'bosses': ['rarity_colors','bosses'],
            'titans': ['rarity_colors','titans'],
            'pets_level': ['LEVEL_THRESHOLDS', 'PET_STAGES', 'STAGE_EMOJIS', 'AUTOBOT_PET_NAMES', 'DECEPTICON_PET_NAMES', 'MISSION_TYPES'],
            'transformation_items': ['rarity_colors', 'beast_modes', 'transformations', 'weapons', 'armor'],
            'recruit': ['subject', 'body'],  # This is a list, not dict
            'bot_logs': ['logs'],
            'cybercoin_market_data': ['current_price', 'price_history', 'user_portfolios', 'total_volume_24h', 'market_trend', 'last_update'],
            

            
            # Random talk data - top-level keys
            'what_talk': ['Allspark', 'Cybertron', 'Energon', 'Transformer', 'Autobot', 'Decepticon', 'Combiner', 'Primes', 'Unicron', 'Matrix of Leadership', 'Quintessons', 'Space Bridge', 'Seekers', 'Minicons', 'Vector Sigma', 'Omega Supreme', 'Dinobots', 'Wreckers', 'Vector Prime'],
            'talk_templates': ['dialogue_templates', 'duo_templates', 'trio_templates'],
            'jokes_talk': ['transformers_politics_war_jokes'],
            'grump_talk': ['greeting_templates', 'threatening_messages', 'nuclear_messages', 'ultra_nuclear_messages', 'witness_messages', 'threat_messages'],
            'blessings_talk': ['💪 Courage and Strength', '📖 Wisdom and Guidance', '🌈 Hope and Unity', '🛡️ Protection and Longevity', '🏛️ Legacy and Destiny', '💊 Healing and Renewal', '🚀 Exploration and Discovery', '⚖️ Honor and Justice', '🔥 Passion and Innovation', '🌌 Mystery and Fate', '⚡ Misfortune and Warnings', '💀 Bad Fortune and Curses'],
            'user_lore': ['title', 'description', 'author_id', 'timestamp']
        }
        
        results = {}
        for file_type, required_keys in validators.items():
            try:
                # Map file types to correct method names
                method_mapping = {
                    'monsters_and_bosses': 'get_monsters_and_bosses_data',
                    'pets_level': 'get_pets_level_data',
                    'transformation_items': 'get_transformation_items_data',
                    'recruit': 'get_recruit_data',
                    'bot_logs': 'get_bot_logs',
                    'cybercoin_market_data': 'get_cybercoin_market_data',
                    'what_talk': 'get_what_talk_data',
                    'talk_templates': 'get_talk_templates_data',
                    'jokes_talk': 'get_jokes_talk_data',
                    'grump_talk': 'get_grump_talk_data',
                    'blessings_talk': 'get_blessings_talk_data',
                    'user_lore': 'get_user_lore_data'
                }
                
                method_name = method_mapping.get(file_type, f'get_{file_type}')
                data = await getattr(self, method_name)()
                
                # Validate top-level structure
                if isinstance(data, dict):
                    results[file_type] = all(key in data for key in required_keys)
                elif isinstance(data, list) and file_type == 'recruit':
                    # Special handling for recruit which is a list
                    results[file_type] = len(data) > 0
                else:
                    results[file_type] = False
            except Exception:
                results[file_type] = False
        
        return results

    async def increment_game_stats(self, player_id: str, won: bool = True, energon_change: int = 0) -> bool:
        """
        Increment game statistics with energon tracking
        Returns: success status
        """
        try:
            energon_data = await self.get_energon_data(player_id)
            
            energon_data['games_played'] += 1
            if won:
                energon_data['games_won'] += 1
            else:
                energon_data['games_lost'] += 1
            
            if energon_change > 0:
                energon_data['total_earned'] += energon_change
            elif energon_change < 0:
                energon_data['total_spent'] += abs(energon_change)
            
            energon_data['last_activity'] = datetime.now().isoformat()
            
            return await self.save_energon_data(player_id, energon_data)
            
        except Exception as e:
            logging.error(f"Error incrementing game stats for {player_id}: {e}")
            return False

    async def get_energon_leaderboard(self, period: str = "all_time", limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get energon leaderboard for specified period
        Returns: List of player summaries sorted by energon
        """
        try:
            import glob
            import os
            
            user_files = glob.glob(str(self.base_path / "*.json"))
            players = []
            
            for file_path in user_files:
                try:
                    user_id = Path(file_path).stem
                    if user_id in ["energon_global", "energon_system"]:
                        continue
                    
                    summary = await self.get_energon_summary(user_id)
                    if summary and summary.get('current_balance', {}).get('total_energon', 0) > 0:
                        players.append({
                            'player_id': user_id,
                            'username': summary.get('username', 'Unknown'),
                            'total_energon': summary['current_balance']['total_energon'],
                            'total_earned': summary['lifetime_stats']['total_earned'],
                            'games_played': summary['lifetime_stats']['games_played'],
                            'win_rate': summary['lifetime_stats']['win_rate']
                        })
                        
                except Exception as e:
                    logging.error(f"Error processing leaderboard for {file_path}: {e}")
            
            # Sort by total energon
            players.sort(key=lambda x: x['total_energon'], reverse=True)
            return players[:limit]
            
        except Exception as e:
            logging.error(f"Error generating leaderboard: {e}")
            return []

    async def validate_energon_integrity(self, player_id: str) -> Dict[str, Any]:
        """
        Validate energon data integrity for a player
        Returns: validation report
        """
        try:
            energon_data = await self.get_energon_data(player_id)
            
            issues = []
            
            # Check for negative values
            for field in ['energon', 'energon_bank', 'total_earned', 'total_spent']:
                if energon_data.get(field, 0) < 0:
                    issues.append(f"Negative {field}: {energon_data[field]}")
            
            # Check consistency
            calculated_earned = (
                energon_data.get('pet_energon_earned', 0) +
                energon_data.get('battle_energon_earned', 0) +
                energon_data.get('search_energon_earned', 0) +
                energon_data.get('slots_energon_earned', 0) +
                energon_data.get('challenge_energon_earned', 0)
            )
            
            if calculated_earned > energon_data.get('total_earned', 0):
                issues.append("Source earnings exceed total earned")
            
            # Check game balance consistency
            games_played = energon_data.get('games_played', 0)
            games_won = energon_data.get('games_won', 0)
            games_lost = energon_data.get('games_lost', 0)
            
            if games_won + games_lost != games_played:
                issues.append("Game win/loss count mismatch")
            
            return {
                'valid': len(issues) == 0,
                'issues': issues,
                'data': energon_data
            }
            
        except Exception as e:
            logging.error(f"Error validating energon integrity for {player_id}: {e}")
            return {'valid': False, 'issues': [str(e)]}

    async def migrate_legacy_data(self, player_id: str) -> bool:
        """
        Migrate legacy energon data to new unified structure
        Returns: success status
        """
        try:
            user_data = await self.get_user_data(player_id)
            energon_data = user_data.get("energon", {})
            
            # Migrate from old structure
            legacy_fields = {
                'rush_wins': 'games_won',
                'rush_losses': 'games_lost',
                'search_wins': 'games_won',
                'search_losses': 'games_lost',
                'slots_wins': 'games_won',
                'slots_losses': 'games_lost',
                'challenge_wins': 'games_won',
                'challenge_losses': 'games_lost',
                'total_energon_gained': 'total_earned',
                'total_energon_lost': 'total_spent'
            }
            
            for legacy_field, new_field in legacy_fields.items():
                if legacy_field in energon_data and legacy_field != new_field:
                    if isinstance(energon_data.get(new_field), int):
                        energon_data[new_field] = energon_data.get(new_field, 0) + energon_data[legacy_field]
                    del energon_data[legacy_field]
            
            # Ensure all new fields exist
            default_data = self._get_default_energon_data()
            for key, default_value in default_data.items():
                if key not in energon_data:
                    energon_data[key] = default_value
            
            return await self.save_energon_data(player_id, energon_data)
            
        except Exception as e:
            logging.error(f"Error migrating legacy data for {player_id}: {e}")
            return False
    async def add_energon(self, player_id: str, amount: int, source: str = "general") -> tuple[bool, int, int]:
        """Optimized method to add energon with validation and atomic operations"""
        if amount <= 0:
            return False, 0, 0
            
        try:
            energon_data = await self.get_energon_data(player_id)
            
            # Ensure all fields exist
            energon_data.setdefault('energon_bank', 0)
            energon_data.setdefault('total_earned', 0)
            
            # Atomic updates
            energon_data['energon_bank'] += amount
            energon_data['total_earned'] += amount
            energon_data['last_activity'] = datetime.now().isoformat()
            
            # Source tracking
            source_field = f"{source}_energon_earned"
            energon_data[source_field] = energon_data.get(source_field, 0) + amount
            
            success = await self.save_energon_data(player_id, energon_data)
            return success, energon_data['energon_bank'], energon_data['total_earned']
            
        except Exception as e:
            logging.error(f"Error adding energon for {player_id}: {e}")
            return False, 0, 0

    async def subtract_energon(self, player_id: str, amount: int, source: str = "general") -> tuple[bool, int, int]:
        """Optimized method to subtract energon with balance checking"""
        if amount <= 0:
            return False, 0, 0
            
        try:
            energon_data = await self.get_energon_data(player_id)
            current_balance = energon_data.get('energon_bank', 0)
            current_spent = energon_data.get('total_spent', 0)
            
            if current_balance >= amount:
                energon_data['energon_bank'] = current_balance - amount
                energon_data['total_spent'] = current_spent + amount
                energon_data['last_activity'] = datetime.now().isoformat()
                
                success = await self.save_energon_data(player_id, energon_data)
                return success, energon_data['energon_bank'], energon_data['total_spent']
            
            return False, current_balance, current_spent
            
        except Exception as e:
            logging.error(f"Error subtracting energon for {player_id}: {e}")
            return False, 0, 0

    async def transfer_energon_to_game(self, player_id: str, amount: int) -> tuple[bool, int, int]:
        """Optimized method to transfer energon from bank to game"""
        if amount <= 0:
            return False, 0, 0
            
        try:
            energon_data = await self.get_energon_data(player_id)
            current_bank = energon_data.get('energon_bank', 0)
            current_game = energon_data.get('energon', 0)
            
            if current_bank >= amount:
                energon_data['energon_bank'] = current_bank - amount
                energon_data['energon'] = current_game + amount
                energon_data['last_activity'] = datetime.now().isoformat()
                
                success = await self.save_energon_data(player_id, energon_data)
                return success, energon_data['energon_bank'], energon_data['energon']
            
            return False, current_bank, current_game
            
        except Exception as e:
            logging.error(f"Error transferring energon to game for {player_id}: {e}")
            return False, 0, 0

    async def bank_game_energon(self, player_id: str) -> tuple[bool, int, int]:
        """Optimized method to bank all game energon"""
        try:
            energon_data = await self.get_energon_data(player_id)
            game_balance = energon_data.get('energon', 0)
            bank_balance = energon_data.get('energon_bank', 0)
            
            if game_balance > 0:
                energon_data['energon_bank'] = bank_balance + game_balance
                energon_data['energon'] = 0
                energon_data['last_activity'] = datetime.now().isoformat()
                
                success = await self.save_energon_data(player_id, energon_data)
                return success, energon_data['energon_bank'], game_balance
            
            return True, bank_balance, 0
            
        except Exception as e:
            logging.error(f"Error banking game energon for {player_id}: {e}")
            return False, 0, 0

user_data_manager = UserDataManager()

OptimizedUserDataManager = UserDataManager