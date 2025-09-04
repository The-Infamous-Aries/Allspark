import json
import os
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

class UserDataManager:
    def __init__(self, data_directory: str = "Systems/Users"):
        self.data_directory = data_directory
        self.global_saves_dir = "Systems/Global Saves"
        self.energon_game_file = os.path.join(self.global_saves_dir, "energon_game.json")
        self._ensure_directory_exists()
        self._ensure_global_saves_exists()
    
    def _ensure_directory_exists(self):
        """Ensure the Users directory exists"""
        if not os.path.exists(self.data_directory):
            os.makedirs(self.data_directory, exist_ok=True)
    
    def _ensure_global_saves_exists(self):
        """Ensure the Global Saves directory exists"""
        if not os.path.exists(self.global_saves_dir):
            os.makedirs(self.global_saves_dir, exist_ok=True)
    
    def _get_user_file_path(self, user_id: str, username: str = None) -> str:
        """Get the file path for a specific user using only user ID"""
        return os.path.join(self.data_directory, f"{user_id}.json")
    
    def _create_default_user_data(self, user_id: str, username: str) -> Dict[str, Any]:
        """Create default user data structure with all RPG and Pet fields."""
        return {
            "user_id": user_id,
            "username": username,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
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
            "pets": {
                "pet_data": None  # Single pet per user, null if no pet exists
            },
            "energon_rush": {
                "high_score": 0,
                "games_played": 0,
                "total_energon_collected": 0
            },
            "shooting_range": {
                "high_score": 0,
                "games_played": 0,
                "accuracy": 0.0,
                "total_targets_hit": 0,
                "total_hits": 0,
                "total_shots": 0,
                "sessions_played": 0,
                "best_records": {
                    "5": {"accuracy": 0, "hits": 0},
                    "15": {"accuracy": 0, "hits": 0},
                    "25": {"accuracy": 0, "hits": 0},
                    "50": {"accuracy": 0, "hits": 0},
                    "100": {"accuracy": 0, "hits": 0}
                },
                "round_attempts": {}
            },
            "mega_fights": {
                "mega_fights_won": 0,
                "mega_fights_lost": 0,
                "total_energon_won": 0,
                "total_energon_lost": 0,
                "total_fights": 0
            },
            "slot_machine": {
                "total_games_played": 0,
                "total_winnings": 0,
                "total_losses": 0,
                "jackpots_won": 0,
                "two_matches_won": 0,
                "highest_bet": 0,
                "highest_win": 0,
                "games_by_difficulty": {
                    "easy": 0,
                    "medium": 0,
                    "hard": 0
                },
                "winnings_by_difficulty": {
                    "easy": 0,
                    "medium": 0,
                    "hard": 0
                }
            },
            "energon": {
                "energon": 0
            },
            "cybercoin_market": {
                "portfolio": {
                    "total_coins": 0,
                    "total_invested": 0,
                    "total_sold": 0,
                    "total_profit": 0,
                    "current_value": 0
                },
                "transactions": {
                    "purchases": [],  # List of buy transactions
                    "sales": []       # List of sell transactions
                },
                "holdings": []  # FIFO queue of owned coins with purchase details
            },
            "theme_system": {
                "transformer_name": None,
                "transformer_faction": None,
                "transformer_class": None,
                "combiner_teams": [],  # List of team IDs this user is part of
                "current_combiner_team": None,  # Current active team ID
                "combiner_role": None,  # User's role in current team (leg, arm, head, body)
                "combiner_history": []  # Historical record of combiner teams
            }
        }
    
    async def get_user_data(self, user_id: str, username: str = None) -> Dict[str, Any]:
        """Get all user data for a specific user using ID-only file naming"""
        file_path = self._get_user_file_path(user_id)
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Update username in data if provided and different
                if username and data.get("username") != username:
                    data["username"] = username
                    await self.save_user_data(user_id, username, data)
                
                return data
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading user data for {user_id}: {e}")
        
        return self._create_default_user_data(user_id, username or "Unknown")
    
    async def save_user_data(self, user_id: str, username: str, data: Dict[str, Any]) -> bool:
        """Save all user data for a specific user using ID-only file naming"""
        file_path = self._get_user_file_path(user_id)
        
        try:
            # Update last modified timestamp
            data["last_updated"] = datetime.now().isoformat()
            
            # Ensure username is stored in the data
            if username:
                data["username"] = username
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"Error saving user data for {user_id}: {e}")
            return False

    async def save_rpg_character(self, user_id: str, username: str, character: Dict[str, Any]) -> bool:
        """Save a specific RPG character to user's data."""
        try:
            user_data = await self.get_user_data(user_id, username)
            
            # Check if character already exists
            existing_chars = user_data.get("rpg", {}).get("characters", [])
            char_index = None
            for i, char in enumerate(existing_chars):
                if char.get("name") == character.get("name"):
                    char_index = i
                    break
            
            if char_index is not None:
                # Update existing character
                existing_chars[char_index] = character
            else:
                # Add new character
                existing_chars.append(character)
            
            if "rpg" not in user_data:
                user_data["rpg"] = {}
            user_data["rpg"]["characters"] = existing_chars
            
            return await self.save_user_data(user_id, username, user_data)
        except Exception as e:
            print(f"Error saving RPG character for {user_id}: {e}")
            return False

    async def get_rpg_character(self, user_id: str, username: str, character_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific RPG character from user's data."""
        try:
            user_data = await self.get_user_data(user_id, username)
            characters = user_data.get("rpg", {}).get("characters", [])
            
            for char in characters:
                if char.get("name") == character_name:
                    return char
            return None
        except Exception as e:
            print(f"Error getting RPG character for {user_id}: {e}")
            return None

    async def get_all_rpg_characters(self, user_id: str, username: str) -> list:
        """Get all RPG characters for a user."""
        try:
            user_data = await self.get_user_data(user_id, username)
            return user_data.get("rpg", {}).get("characters", [])
        except Exception as e:
            print(f"Error getting all RPG characters for {user_id}: {e}")
            return []

    async def delete_rpg_character(self, user_id: str, username: str, character_name: str) -> bool:
        """Delete a specific RPG character from user's data."""
        try:
            user_data = await self.get_user_data(user_id, username)
            characters = user_data.get("rpg", {}).get("characters", [])
            
            # Filter out the character to delete
            new_characters = [char for char in characters if char.get("name") != character_name]
            
            if len(new_characters) == len(characters):
                return False  # Character not found
            
            user_data["rpg"]["characters"] = new_characters
            return await self.save_user_data(user_id, username, user_data)
        except Exception as e:
            print(f"Error deleting RPG character for {user_id}: {e}")
            return False
    
    async def get_character_data(self, user_id: str, username: str) -> Dict[str, Any]:
        """Get only character data"""
        user_data = await self.get_user_data(user_id, username)
        return user_data.get("character", {})
    
    async def save_character_data(self, user_id: str, username: str, character_data: Dict[str, Any]) -> bool:
        """Save character data"""
        user_data = await self.get_user_data(user_id, username)
        user_data["character"] = character_data
        return await self.save_user_data(user_id, username, user_data)

    # Theme System Methods
    async def get_theme_system_data(self, user_id: str, username: str) -> Dict[str, Any]:
        """Get only theme system data"""
        user_data = await self.get_user_data(user_id, username)
        return user_data.get("theme_system", {})
    
    async def save_theme_system_data(self, user_id: str, username: str, theme_data: Dict[str, Any]) -> bool:
        """Save theme system data"""
        user_data = await self.get_user_data(user_id, username)
        user_data["theme_system"] = theme_data
        return await self.save_user_data(user_id, username, user_data)
    
    async def add_user_to_combiner_team(self, user_id: str, username: str, team_id: str, role: str, team_data: Dict[str, Any]) -> bool:
        """Add user to a combiner team and update all team members"""
        try:
            # Update current user's data
            user_data = await self.get_user_data(user_id, username)
            theme_data = user_data.get("theme_system", {})
            
            # Remove from any existing team first
            if theme_data.get("current_combiner_team") and theme_data.get("current_combiner_team") != team_id:
                await self.remove_user_from_combiner_team(user_id, username, theme_data["current_combiner_team"])
            
            # Add to new team
            if team_id not in theme_data.get("combiner_teams", []):
                theme_data.setdefault("combiner_teams", []).append(team_id)
            
            theme_data["current_combiner_team"] = team_id
            theme_data["combiner_role"] = role.lower()
            
            # Add to history if not already there
            team_entry = {
                "team_id": team_id,
                "role": role.lower(),
                "joined_at": datetime.now().isoformat(),
                "team_data": team_data
            }
            
            history = theme_data.get("combiner_history", [])
            if not any(h.get("team_id") == team_id for h in history):
                history.append(team_entry)
                theme_data["combiner_history"] = history
            
            await self.save_theme_system_data(user_id, username, theme_data)
            
            # Update all team members' files with current team composition
            await self._update_combiner_team_members(team_id, team_data)
            
            return True
        except Exception as e:
            print(f"Error adding user to combiner team {user_id}: {e}")
            return False

    async def remove_user_from_combiner_team(self, user_id: str, username: str, team_id: str) -> bool:
        """Remove user from a combiner team and update team data"""
        try:
            theme_data = await self.get_theme_system_data(user_id, username)
            
            if team_id in theme_data.get("combiner_teams", []):
                theme_data["combiner_teams"].remove(team_id)
            
            if theme_data.get("current_combiner_team") == team_id:
                theme_data["current_combiner_team"] = None
                theme_data["combiner_role"] = None
            
            await self.save_theme_system_data(user_id, username, theme_data)
            
            # Update team members (this will be handled by theme_system.py)
            return True
        except Exception as e:
            print(f"Error removing user from combiner team for {user_id}: {e}")
            return False

    async def get_user_combiner_team(self, user_id: str, username: str = None) -> Optional[Dict[str, Any]]:
        """Get the current combiner team for a user"""
        try:
            user_data = await self.get_user_data(user_id, username)
            theme_data = user_data.get("theme_system", {})
            
            current_team_id = theme_data.get("current_combiner_team")
            if not current_team_id:
                return None
            
            # Find the most recent team info in history
            team_history = theme_data.get("combiner_history", [])
            for team_info in reversed(team_history):
                if team_info.get("team_id") == current_team_id:
                    return team_info
            
            return None
            
        except Exception as e:
            print(f"Error getting user combiner team {user_id}: {e}")
            return None
    
    async def _update_combiner_team_members(self, team_id: str, team_data: Dict[str, Any]) -> bool:
        """Update all team members with current team composition"""
        try:
            # This method will be called from theme_system.py when teams change
            # It updates the team_data in each member's file
            
            # Collect all member user IDs
            member_ids = []
            for part, members in team_data.items():
                member_ids.extend(members)
            
            # Update each member's file
            for member_id in set(member_ids):
                try:
                    # We need to get the member's username - this will be handled by theme_system.py
                    # For now, we'll just update the team data structure
                    pass
                except Exception as e:
                    print(f"Error updating member {member_id}: {e}")
                    continue
            
            return True
        except Exception as e:
            print(f"Error updating combiner team members for {team_id}: {e}")
            return False

    async def get_combiner_team_details(self, team_id: str) -> Dict[str, Any]:
        """Get detailed information about a combiner team"""
        try:
            # This will be used by theme_system.py to get complete team info
            return {
                "team_id": team_id,
                "members": {},
                "formation_date": None,
                "combiner_name": None
            }
        except Exception as e:
            print(f"Error getting combiner team details for {team_id}: {e}")
            return {}

    async def get_users_in_combiner_team(self, team_id: str) -> list:
        """Get all user IDs in a specific combiner team"""
        try:
            # This will be implemented to scan user files for team membership
            user_ids = []
            return user_ids
        except Exception as e:
            print(f"Error getting users in combiner team {team_id}: {e}")
            return []

    async def get_energon_stats(self, user_id: str, username: str = None) -> Dict[str, Any]:
        """Get Energon game statistics for a user"""
        try:
            user_data = await self.get_user_data(user_id, username)
            energon_stats = user_data.get("energon_stats", {})
            
            # Ensure all required fields exist
            default_stats = {
                "games_won": 0,
                "games_lost": 0,
                "challenges_won": 0,
                "challenges_lost": 0,
                "total_energon_gained": 0,
                "total_energon_lost": 0,
                "energon_bank": 0,
                "challenge_energon_won": 0,
                "challenge_energon_lost": 0,
                "current_energon": 0,
                "lifetime_energon": 0
            }
            
            # Merge existing stats with defaults
            for key, default_value in default_stats.items():
                if key not in energon_stats:
                    energon_stats[key] = default_value
                    
            return energon_stats
        except Exception as e:
            print(f"Error getting energon stats for {user_id}: {e}")
            return {
                "games_won": 0,
                "games_lost": 0,
                "challenges_won": 0,
                "challenges_lost": 0,
                "total_energon_gained": 0,
                "total_energon_lost": 0,
                "energon_bank": 0,
                "challenge_energon_won": 0,
                "challenge_energon_lost": 0,
                "current_energon": 0,
                "lifetime_energon": 0
            }

    async def save_energon_stats(self, user_id: str, username: str, energon_stats: Dict[str, Any]) -> bool:
        """Save Energon game statistics for a user"""
        try:
            user_data = await self.get_user_data(user_id, username)
            user_data["energon_stats"] = energon_stats
            success = await self.save_user_data(user_id, username, user_data)
            
            # Also update the centralized energon game file
            if success:
                await self._update_energon_game_file(user_id, username, energon_stats)
            
            return success
        except Exception as e:
            print(f"Error saving energon stats for {user_id}: {e}")
            return False

    async def update_energon_stat(self, user_id: str, username: str, stat_type: str, amount: int = 1) -> bool:
        """Update a specific Energon game statistic"""
        try:
            energon_stats = await self.get_energon_stats(user_id, username)
            if stat_type in energon_stats:
                energon_stats[stat_type] += amount
                success = await self.save_energon_stats(user_id, username, energon_stats)
                if success:
                    await self._update_energon_game_file(user_id, username, energon_stats)
                return success
            return False
        except Exception as e:
            print(f"Error updating energon stat {stat_type} for {user_id}: {e}")
            return False
    
    async def _update_energon_game_file(self, user_id: str, username: str, energon_stats: Dict[str, Any]) -> bool:
        """Update the centralized energon_game.json file with user data"""
        try:
            # Load existing energon game data
            energon_game_data = await self._load_energon_game_data()
            
            # Get current energon from user's energon data
            energon_data = await self.get_energon_data(user_id, username)
            current_energon = energon_data.get("energon", 0)
            
            # Update user entry in energon game data
            energon_game_data[user_id] = {
                "username": username,
                "current_energon": current_energon,
                "energon_bank": energon_stats.get("energon_bank", 0),
                "games_won": energon_stats.get("games_won", 0),
                "games_lost": energon_stats.get("games_lost", 0),
                "lifetime_energon": energon_stats.get("lifetime_energon", 0),
                "total_energon_gained": energon_stats.get("total_energon_gained", 0),
                "total_energon_lost": energon_stats.get("total_energon_lost", 0),
                "last_updated": datetime.now().isoformat()
            }
            
            # Save updated energon game data
            return await self._save_energon_game_data(energon_game_data)
        except Exception as e:
            print(f"Error updating energon game file for {user_id}: {e}")
            return False
    
    async def _load_energon_game_data(self) -> Dict[str, Any]:
        """Load the centralized energon_game.json file"""
        try:
            if os.path.exists(self.energon_game_file):
                with open(self.energon_game_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading energon game data: {e}")
            return {}
    
    async def _save_energon_game_data(self, data: Dict[str, Any]) -> bool:
        """Save data to the centralized energon_game.json file"""
        try:
            with open(self.energon_game_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"Error saving energon game data: {e}")
            return False
    
    async def get_energon_leaderboard_from_game_file(self, stat_type: str = "lifetime_energon", limit: int = 10) -> list:
        """Get leaderboard from the centralized energon_game.json file"""
        try:
            energon_game_data = await self._load_energon_game_data()
            leaderboard = []
            
            for user_id, user_data in energon_game_data.items():
                if stat_type in user_data and user_data[stat_type] > 0:
                    leaderboard.append({
                        "user_id": user_id,
                        "username": user_data["username"],
                        "value": user_data[stat_type],
                        "type": stat_type.replace("_", " ").title()
                    })
            
            # Sort by value descending
            leaderboard.sort(key=lambda x: x["value"], reverse=True)
            return leaderboard[:limit]
        except Exception as e:
            print(f"Error generating energon leaderboard from game file: {e}")
            return []

    async def get_energon_leaderboard(self, stat_type: str = "lifetime_energon", limit: int = 10) -> list:
        """Get leaderboard for Energon game statistics"""
        try:
            user_ids = await self.get_all_user_ids()
            leaderboard = []
            
            for user_id in user_ids:
                try:
                    energon_stats = await self.get_energon_stats(str(user_id))
                    if stat_type in energon_stats and energon_stats[stat_type] > 0:
                        leaderboard.append({
                            "user_id": user_id,
                            "value": energon_stats[stat_type],
                            "stats": energon_stats
                        })
                except Exception as e:
                    print(f"Error processing user {user_id} for leaderboard: {e}")
                    continue
            
            # Sort by value descending
            leaderboard.sort(key=lambda x: x["value"], reverse=True)
            return leaderboard[:limit]
        except Exception as e:
            print(f"Error generating energon leaderboard: {e}")
            return []

    # Fun System Methods - Shooting Range
    async def get_shooting_range_stats(self, user_id: str, username: str) -> Dict[str, Any]:
        """Get detailed shooting range statistics for a user"""
        try:
            user_data = await self.get_user_data(user_id, username)
            shooting_stats = user_data.get("shooting_range", {})
            
            # Ensure all required fields exist
            default_stats = {
                "total_hits": 0,
                "total_shots": 0,
                "sessions_played": 0,
                "best_records": {
                    "5": {"accuracy": 0, "hits": 0},
                    "15": {"accuracy": 0, "hits": 0},
                    "25": {"accuracy": 0, "hits": 0},
                    "50": {"accuracy": 0, "hits": 0},
                    "100": {"accuracy": 0, "hits": 0}
                },
                "round_attempts": {}
            }
            
            # Merge existing stats with defaults
            for key, default_value in default_stats.items():
                if key not in shooting_stats:
                    shooting_stats[key] = default_value
                    
            return shooting_stats
        except Exception as e:
            print(f"Error getting shooting range stats for {user_id}: {e}")
            return {
                "total_hits": 0,
                "total_shots": 0,
                "sessions_played": 0,
                "best_records": {
                    "5": {"accuracy": 0, "hits": 0},
                    "15": {"accuracy": 0, "hits": 0},
                    "25": {"accuracy": 0, "hits": 0},
                    "50": {"accuracy": 0, "hits": 0},
                    "100": {"accuracy": 0, "hits": 0}
                },
                "round_attempts": {}
            }

    async def save_shooting_range_stats(self, user_id: str, username: str, shooting_stats: Dict[str, Any]) -> bool:
        """Save shooting range statistics for a user"""
        try:
            user_data = await self.get_user_data(user_id, username)
            user_data["shooting_range"] = shooting_stats
            return await self.save_user_data(user_id, username, user_data)
        except Exception as e:
            print(f"Error saving shooting range stats for {user_id}: {e}")
            return False

    async def update_shooting_range_stats(self, user_id: str, username: str, hits: int, total_shots: int, rounds: int) -> Dict[str, Any]:
        """Update shooting range statistics with new session data"""
        try:
            shooting_stats = await self.get_shooting_range_stats(user_id, username)
            
            # Update overall stats
            shooting_stats["total_hits"] += hits
            shooting_stats["total_shots"] += total_shots
            shooting_stats["sessions_played"] += 1
            
            # Update round attempts
            rounds_key = str(rounds)
            if "round_attempts" not in shooting_stats:
                shooting_stats["round_attempts"] = {}
            shooting_stats["round_attempts"][rounds_key] = shooting_stats["round_attempts"].get(rounds_key, 0) + 1
            
            # Update best record for this round count if better
            accuracy = (hits / total_shots) * 100
            if rounds_key not in shooting_stats["best_records"]:
                shooting_stats["best_records"][rounds_key] = {
                    "accuracy": accuracy,
                    "hits": hits
                }
            else:
                current_best = shooting_stats["best_records"][rounds_key]
                if accuracy > current_best["accuracy"] or (accuracy == current_best["accuracy"] and hits > current_best["hits"]):
                    shooting_stats["best_records"][rounds_key] = {
                        "accuracy": accuracy,
                        "hits": hits
                    }
            
            await self.save_shooting_range_stats(user_id, username, shooting_stats)
            return shooting_stats
        except Exception as e:
            print(f"Error updating shooting range stats for {user_id}: {e}")
            return {}

    # Fun System Methods - Mega Fights
    async def get_mega_fight_stats(self, user_id: str, username: str) -> Dict[str, Any]:
        """Get Mega Fight statistics for a user"""
        try:
            user_data = await self.get_user_data(user_id, username)
            mega_stats = user_data.get("mega_fights", {})
            
            # Ensure all required fields exist
            default_stats = {
                "mega_fights_won": 0,
                "mega_fights_lost": 0,
                "total_energon_won": 0,
                "total_energon_lost": 0,
                "total_fights": 0
            }
            
            # Merge existing stats with defaults
            for key, default_value in default_stats.items():
                if key not in mega_stats:
                    mega_stats[key] = default_value
                    
            return mega_stats
        except Exception as e:
            print(f"Error getting mega fight stats for {user_id}: {e}")
            return {
                "mega_fights_won": 0,
                "mega_fights_lost": 0,
                "total_energon_won": 0,
                "total_energon_lost": 0,
                "total_fights": 0
            }

    async def save_mega_fight_stats(self, user_id: str, username: str, mega_stats: Dict[str, Any]) -> bool:
        """Save Mega Fight statistics for a user"""
        try:
            user_data = await self.get_user_data(user_id, username)
            user_data["mega_fights"] = mega_stats
            return await self.save_user_data(user_id, username, user_data)
        except Exception as e:
            print(f"Error saving mega fight stats for {user_id}: {e}")
            return False

    async def update_mega_fight_result(self, user_id: str, username: str, won: bool, energon_change: int) -> Dict[str, Any]:
        """Update Mega Fight result statistics"""
        try:
            mega_stats = await self.get_mega_fight_stats(user_id, username)
            
            if won:
                mega_stats["mega_fights_won"] += 1
                mega_stats["total_energon_won"] += energon_change
            else:
                mega_stats["mega_fights_lost"] += 1
                mega_stats["total_energon_lost"] += abs(energon_change)
            
            mega_stats["total_fights"] += 1
            
            await self.save_mega_fight_stats(user_id, username, mega_stats)
            return mega_stats
        except Exception as e:
            print(f"Error updating mega fight result for {user_id}: {e}")
            return {}
    
    async def update_nested_value(self, user_id: int, path: str, value: Any) -> bool:
        """Update a nested value using dot notation (e.g., 'character.stats.strength')"""
        user_data = await self.get_user_data(user_id)
        
        keys = path.split('.')
        current = user_data
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
        return await self.save_user_data(user_id, user_data)
    
    async def get_nested_value(self, user_id: int, path: str, default: Any = None) -> Any:
        """Get a nested value using dot notation"""
        user_data = await self.get_user_data(user_id)
        
        keys = path.split('.')
        current = user_data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        
        return current
    
    async def delete_user_data(self, user_id: int) -> bool:
        """Delete all user data for a specific user"""
        file_path = self._get_user_file_path(user_id)
        
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            return True
        except IOError as e:
            print(f"Error deleting user data for {user_id}: {e}")
            return False
    
    async def user_exists(self, user_id: int) -> bool:
        """Check if user data exists"""
        file_path = self._get_user_file_path(user_id)
        return os.path.exists(file_path)
    
    async def get_all_user_ids(self) -> list:
        """Get list of all user IDs that have data"""
        try:
            files = os.listdir(self.data_directory)
            user_ids = []
            for file in files:
                if file.endswith('.json'):
                    try:
                        user_id = int(file[:-5])  # Remove .json extension
                        user_ids.append(user_id)
                    except ValueError:
                        continue
            return user_ids
        except IOError:
            return []
    
    async def get_user_count(self) -> int:
        """Get total number of users with data"""
        user_ids = await self.get_all_user_ids()
        return len(user_ids)
    
    async def backup_user_data(self, user_id: int) -> Optional[str]:
        """Create a backup of user data"""
        user_data = await self.get_user_data(user_id)
        backup_path = os.path.join(self.data_directory, f"{user_id}_backup.json")
        
        try:
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(user_data, f, indent=2, ensure_ascii=False)
            return backup_path
        except IOError:
            return None


    async def get_cybercoin_data(self, user_id: str, username: str = None) -> dict:
        """Get cybercoin market data for a user"""
        user_data = await self.get_user_data(user_id, username)
        return user_data.get('cybercoin_market', {
            'portfolio': {'total_coins': 0, 'total_invested': 0, 'total_sold': 0, 'total_profit': 0, 'current_value': 0},
            'transactions': {'purchases': [], 'sales': []},
            'holdings': []
        })

    async def save_cybercoin_data(self, user_id: str, username: str, cybercoin_data: dict) -> bool:
        """Save cybercoin market data for a user"""
        user_data = await self.get_user_data(user_id, username)
        user_data['cybercoin_market'] = cybercoin_data
        return await self.save_user_data(user_id, username, user_data)

    async def record_cybercoin_purchase(self, user_id: str, username: str, quantity: float, price_per_coin: float) -> bool:
        """Record a cybercoin purchase using FIFO accounting"""
        try:
            cybercoin_data = await self.get_cybercoin_data(user_id, username)
            # Create purchase transaction
            purchase = {
                'type': 'purchase',
                'quantity': quantity,
                'price': price_per_coin,
                'timestamp': datetime.now().isoformat()
            }
            
            # Add to holdings (FIFO queue)
            cybercoin_data['holdings'].append({
                'quantity': quantity,
                'price': price_per_coin,
                'timestamp': purchase['timestamp']
            })
            
            # Add to transactions
            cybercoin_data['transactions']['purchases'].append(purchase)
            
            # Update portfolio
            total_cost = quantity * price_per_coin
            cybercoin_data['portfolio']['total_coins'] += quantity
            cybercoin_data['portfolio']['total_invested'] += total_cost
            
            return await self.save_cybercoin_data(user_id, username, cybercoin_data)
            
        except Exception as e:
            print(f"Error recording cybercoin purchase: {e}")
            return False

    async def record_cybercoin_sale(self, user_id: str, username: str, quantity: float, price_per_coin: float) -> dict:
        """Record a cybercoin sale using FIFO accounting"""
        try:
            cybercoin_data = await self.get_cybercoin_data(user_id, username)
            
            if cybercoin_data['portfolio']['total_coins'] < quantity:
                raise ValueError(f"Insufficient coins. Available: {cybercoin_data['portfolio']['total_coins']}, Requested: {quantity}")
            
            coins_to_sell = quantity
            cost_basis = 0.0
            
            # Process FIFO - sell oldest coins first
            while coins_to_sell > 0 and cybercoin_data['holdings']:
                oldest_holding = cybercoin_data['holdings'][0]
                
                if oldest_holding['quantity'] <= coins_to_sell:
                    # Sell entire batch
                    cost_basis += oldest_holding['quantity'] * oldest_holding['price']
                    coins_to_sell -= oldest_holding['quantity']
                    cybercoin_data['holdings'].pop(0)
                else:
                    # Sell partial batch
                    cost_basis += coins_to_sell * oldest_holding['price']
                    oldest_holding['quantity'] -= coins_to_sell
                    coins_to_sell = 0
            
            # Calculate profit/loss
            sale_revenue = quantity * price_per_coin
            profit_loss = sale_revenue - cost_basis
            
            # Create sale transaction
            sale = {
                'type': 'sale',
                'quantity': quantity,
                'price': price_per_coin,
                'cost_basis': cost_basis,
                'profit_loss': profit_loss,
                'timestamp': datetime.now().isoformat()
            }
            
            # Add to transactions
            cybercoin_data['transactions']['sales'].append(sale)
            
            # Update portfolio
            cybercoin_data['portfolio']['total_coins'] -= quantity
            cybercoin_data['portfolio']['total_sold'] += sale_revenue
            cybercoin_data['portfolio']['total_profit'] += profit_loss
            
            await self.save_cybercoin_data(user_id, username, cybercoin_data)
            
            return {
                'coins_sold': quantity,
                'sale_revenue': sale_revenue,
                'cost_basis': cost_basis,
                'profit_loss': profit_loss
            }
            
        except Exception as e:
            print(f"Error recording cybercoin sale: {e}")
            raise

    async def get_cybercoin_summary(self, user_id: str, username: str = None) -> dict:
        """Get summary of cybercoin portfolio"""
        cybercoin_data = await self.get_cybercoin_data(user_id, username)
        
        current_price = 15.0  # Placeholder - will be dynamic
        total_coins = cybercoin_data['portfolio']['total_coins']
        total_invested = cybercoin_data['portfolio']['total_invested']
        
        return {
            'total_coins': total_coins,
            'total_invested': total_invested,
            'average_price': total_invested / total_coins if total_coins > 0 else 0,
            'current_value': total_coins * current_price,
            'current_price': current_price
        }

    async def get_cybercoin_portfolio(self, user_id: str, username: str = None) -> dict:
        """Get detailed cybercoin portfolio"""
        cybercoin_data = await self.get_cybercoin_data(user_id, username)
        
        return {
            'holdings': cybercoin_data['holdings'],
            'portfolio': cybercoin_data['portfolio'],
            'transactions': cybercoin_data['transactions']
        }

    async def get_pet_data(self, user_id: str, username: str = None) -> Optional[Dict[str, Any]]:
        """Get pet data for a specific user"""
        try:
            user_data = await self.get_user_data(user_id, username)
            return user_data.get("pets", {}).get("pet_data")
        except Exception as e:
            print(f"Error getting pet data for {user_id}: {e}")
            return None

    async def save_pet_data(self, user_id: str, username: str, pet_data: Dict[str, Any]) -> bool:
        """Save pet data for a specific user"""
        try:
            user_data = await self.get_user_data(user_id, username)
            user_data.setdefault("pets", {})["pet_data"] = pet_data
            return await self.save_user_data(user_id, username, user_data)
        except Exception as e:
            print(f"Error saving pet data for {user_id}: {e}")
            return False

    async def delete_pet_data(self, user_id: str, username: str) -> bool:
        """Delete all pet data for a specific user"""
        try:
            user_data = await self.get_user_data(user_id, username)
            user_data.setdefault("pets", {})["pet_data"] = None
            return await self.save_user_data(user_id, username, user_data)
        except Exception as e:
            print(f"Error deleting pet data for {user_id}: {e}")
            return False

    async def get_energon_data(self, user_id: str, username: str = None) -> Dict[str, Any]:
        """Get energon data for a specific user"""
        try:
            user_data = await self.get_user_data(user_id, username)
            return user_data.get("energon", {"energon": 0})
        except Exception as e:
            print(f"Error getting energon data for {user_id}: {e}")
            return {"energon": 0}

    async def save_energon_data(self, user_id: str, username: str, energon_data: Dict[str, Any]) -> bool:
        """Save energon data for a specific user"""
        try:
            user_data = await self.get_user_data(user_id, username)
            user_data["energon"] = energon_data
            success = await self.save_user_data(user_id, username, user_data)
            
            # Also update the centralized energon game file
            if success:
                energon_stats = await self.get_energon_stats(user_id, username)
                await self._update_energon_game_file(user_id, username, energon_stats)
            
            return success
        except Exception as e:
            print(f"Error saving energon data for {user_id}: {e}")
            return False

# Global instance for easy access
user_data_manager = UserDataManager()


async def get_cybercoin_summary(user_id: str) -> dict:
    """Global function to get cybercoin summary"""
    return await user_data_manager.get_cybercoin_summary(user_id)

async def get_cybercoin_portfolio(user_id: str) -> dict:
    """Global function to get cybercoin portfolio"""
    return await user_data_manager.get_cybercoin_portfolio(user_id)

async def record_cybercoin_purchase(user_id: str, quantity: float, price_per_coin: float) -> bool:
    """Global function to record cybercoin purchase"""
    return await user_data_manager.record_cybercoin_purchase(user_id, None, quantity, price_per_coin)

async def record_cybercoin_sale(user_id: str, quantity: float, price_per_coin: float) -> dict:
    """Global function to record cybercoin sale"""
    return await user_data_manager.record_cybercoin_sale(user_id, None, quantity, price_per_coin)


def setup(bot):
    """
    Setup function for the user_data_manager module.
    This makes the UserDataManager instance available to other cogs.
    """
    # Add the user_data_manager instance to the bot for global access
    bot.user_data_manager = user_data_manager
    print("✅ UserDataManager initialized and available globally")