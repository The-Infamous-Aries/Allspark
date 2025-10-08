import discord
from discord.ext import commands
from discord import app_commands
import random
import json
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Optional, Tuple
import sys


try:
    import stocks
except ImportError:
    stocks = None

WIN_CONDITION = 10000
CHALLENGE_TIMEOUT = 300
ENERGON_PETS_DIR = os.path.dirname(__file__)
JSON_DIR = os.path.join(os.path.dirname(ENERGON_PETS_DIR), "Json")

# Slot Machine Configuration
SLOT_THEMES = {
    "easy": ["⚔️", "🛡️", "🥷", "💬", "🧠"],
    "medium": ["🦸", "🦹", "🧙", "🧝", "🧟", "🧞", "🧛", "🧌"],
    "hard": ["🐀", "🐂", "🐅", "🐇", "🐉", "🐍", "🐎", "🐐", "🐒", "🐓", "🐕", "🐖"]
}

DIFFICULTY_MULTIPLIERS = {
    "easy": 80,      # Increased from 64 to 80 for 5 emojis (16x5)
    "medium": 512,
    "hard": 1728
}

bot = None

class EnergonGameManager:
    """Main manager class for all Energon-related games and data."""
    
    def __init__(self, bot_instance: commands.Bot):
        self.bot = bot_instance
        self.game_data: Dict[str, Any] = {}
        self.challenges: Dict[str, Any] = {}
        self.cooldowns: Dict[str, Any] = {}
        
        # Lazy loading flag
        self._game_state_loaded = False
        
    async def load_game_state(self) -> None:
        """Load all Energon game state from user_data_manager."""
        try:
            from Systems.user_data_manager import user_data_manager
            
            # Get game state from user_data_manager using the bot's data manager
            if hasattr(self.bot, 'user_data_manager'):
                state = await self.bot.user_data_manager.get_energon_game_state(None)
            else:
                # Fallback to direct import if bot doesn't have it
                state = await user_data_manager.get_energon_game_state(None)
            
            if state:
                # Load game data (active games)
                game_data = state.get("game_data", {})
                self.game_data = {}
                for channel_id_str, players in game_data.items():
                    if channel_id_str == "global_game":
                        self.game_data["global_game"] = set(players) if isinstance(players, list) else players
                    else:
                        try:
                            channel_id_int = int(channel_id_str)
                            # Convert list to set for internal use
                            self.game_data[channel_id_int] = set(players) if isinstance(players, list) else players
                        except ValueError:
                            print(f"Warning: Invalid channel ID format: {channel_id_str}")
                
                # Load challenges
                challenges = state.get("challenges", {})
                self.challenges = {}
                for channel_id_str, challenge_data in challenges.items():
                    try:
                        channel_id_int = int(channel_id_str)
                        self.challenges[channel_id_int] = challenge_data
                    except ValueError:
                        print(f"Warning: Invalid channel ID format in challenges: {channel_id_str}")
                
                # Load cooldowns
                cooldowns = state.get("cooldowns", {})
                self.cooldowns = {}
                for channel_id_str, cooldown_data in cooldowns.items():
                    try:
                        channel_id_int = int(channel_id_str)
                        self.cooldowns[channel_id_int] = cooldown_data
                    except ValueError:
                        print(f"Warning: Invalid channel ID format in cooldowns: {channel_id_str}")
                
                print(f"Game state loaded successfully. Channels: {len(self.game_data)}")
                
                # Sync with active_games global variable if it exists
                if 'active_games' in globals():
                    # Update the global active_games dictionary
                    global active_games
                    active_games.clear()
                    for channel_id, players in self.game_data.items():
                        if isinstance(channel_id, int) and isinstance(players, (list, set)):
                            active_games[channel_id] = set(players) if isinstance(players, list) else players
                    print(f"Synced {len(active_games)} active games from saved state")
                
            else:
                self._initialize_empty_state()
                print("No existing game state found. Initialized empty game state.")
                
        except Exception as e:
            print(f"Error loading game state: {e}")
            self._initialize_empty_state()
        
        # Mark as loaded
        self._game_state_loaded = True
    
    async def save_game_state(self) -> None:
        """Save all Energon game state to both global and user files."""
        self._ensure_state_loaded()
            
        try:
            from Systems.user_data_manager import user_data_manager
            
            # Convert sets to lists for JSON serialization
            serializable_game_data = {}
            for channel_id, players in self.game_data.items():
                serializable_game_data[channel_id] = list(players)
            
            # Prepare state data to save globally
            state_data = {
                "game_data": serializable_game_data,
                "challenges": self.challenges,
                "cooldowns": self.cooldowns
            }
            
            # Save game state using the bot's user_data_manager
            if hasattr(self.bot, 'user_data_manager'):
                await self.bot.user_data_manager.save_energon_game_state(None, state_data)
            else:
                # Fallback to direct import
                await user_data_manager.save_energon_game_state(None, state_data)
            
            print(f"Game state saved successfully. Channels: {len(self.game_data)}")
            
        except Exception as e:
            print(f"Error saving game state: {e}")

    async def save_player_energon_to_global(self, player_id: str, energon_amount: int) -> None:
        """Save player's energon to the global leaderboard for quick loading."""
        try:
            from Systems.user_data_manager import user_data_manager
            
            # Get current global state from the correct file path
            global_data = await user_data_manager.get_energon_game_state()
            
            # Ensure we have the correct structure
            if "global_stats" not in global_data:
                global_data["global_stats"] = {
                    "total_games": 0,
                    "total_energon_won": 0,
                    "total_energon_lost": 0,
                    "active_players": [],
                    "last_game_end": None,
                    "daily_reset": None
                }
            
            if "leaderboard" not in global_data:
                global_data["leaderboard"] = {"daily": {}, "weekly": {}, "all_time": {}}
            
            # Get player info for leaderboard
            try:
                user_data = await user_data_manager.get_user_data(player_id, str(player_id))
                username = user_data.get("username", f"Player_{player_id}")
            except:
                username = f"Player_{player_id}"
            
            # Update all_time leaderboard
            leaderboard_entry = {
                "player_id": player_id,
                "username": username,
                "energon_bank": energon_amount,
                "last_updated": datetime.now().isoformat()
            }
            
            global_data["leaderboard"]["all_time"][player_id] = leaderboard_entry
            
            # Ensure player is in active players list
            if player_id not in global_data["global_stats"]["active_players"]:
                global_data["global_stats"]["active_players"].append(player_id)
            
            # Save updated global state to the correct file
            await user_data_manager.save_energon_game_state(None, global_data)
            
            print(f"Saved player {player_id} energon {energon_amount} to global leaderboard")
            
        except Exception as e:
            print(f"Error saving player energon to global: {e}")
            import traceback
            traceback.print_exc()
    
    def _initialize_empty_state(self) -> None:
        """Initialize empty game state."""
        self.game_data = {}
        self.challenges = {}
        self.cooldowns = {}
    
    def is_game_active(self, channel_id: int) -> bool:
        """Check if there's an active game in this channel."""
        self._ensure_state_loaded()
        return channel_id in self.game_data
    
    async def start_new_game(self, channel_id: int, starter_player_id: str) -> bool:
        """Start a new game in this channel."""
        self._ensure_state_loaded()
        
        try:
            # Initialize game data for this channel
            if channel_id not in self.game_data:
                self.game_data[channel_id] = set()
            
            # Add starter player
            self.game_data[channel_id].add(starter_player_id)
            
            # Update global active_games if it exists
            if 'active_games' in globals():
                global active_games
                if channel_id not in active_games:
                    active_games[channel_id] = set()
                active_games[channel_id].add(starter_player_id)
            
            # Save state immediately
            await self.save_game_state()
            
            print(f"Started new game in channel {channel_id} with player {starter_player_id}")
            return True
            
        except Exception as e:
            print(f"Error starting new game: {e}")
            return False
    
    async def add_player_to_game(self, channel_id: int, player_id: str) -> bool:
        """Add a player to the active game."""
        self._ensure_state_loaded()
        
        try:
            if channel_id not in self.game_data:
                # No active game, return False
                return False
            
            # Add player to game
            self.game_data[channel_id].add(player_id)
            
            # Update global active_games if it exists
            if 'active_games' in globals():
                global active_games
                if channel_id not in active_games:
                    active_games[channel_id] = set()
                active_games[channel_id].add(player_id)
            
            # Save state immediately
            await self.save_game_state()
            
            print(f"Added player {player_id} to game in channel {channel_id}")
            return True
            
        except Exception as e:
            print(f"Error adding player to game: {e}")
            return False
    
    async def end_game(self, channel_id: int, winner_id: str = None) -> bool:
        """End the current game and distribute rewards."""
        self._ensure_state_loaded()
        
        try:
            if channel_id not in self.game_data:
                return False
            
            # Get all players in this game
            game_players = list(self.game_data[channel_id])
            
            # Bank energon for all players and reset game state
            for player_id in game_players:
                try:
                    # Get player energon data
                    if hasattr(self.bot, 'user_data_manager'):
                        energon_data = await self.bot.user_data_manager.get_energon_data(player_id)
                    else:
                        from Systems.user_data_manager import user_data_manager
                        energon_data = await user_data_manager.get_energon_data(player_id)
                    
                    # Bank the final energon amount
                    current_energon = energon_data.get("energon", 0)
                    if current_energon > 0:
                        if hasattr(self.bot, 'user_data_manager'):
                            await self.bot.user_data_manager.update_energon_stat(player_id, "energon_bank", current_energon)
                        else:
                            from Systems.user_data_manager import user_data_manager
                            await user_data_manager.update_energon_stat(player_id, "energon_bank", current_energon)
                    
                    # Reset game flag and energon
                    energon_data["in_energon_rush"] = False
                    energon_data["energon"] = 0
                    
                    if hasattr(self.bot, 'user_data_manager'):
                        await self.bot.user_data_manager.save_energon_data(player_id, energon_data)
                    else:
                        from Systems.user_data_manager import user_data_manager
                        await user_data_manager.save_energon_data(player_id, energon_data)
                    
                    # Track game results
                    if player_id == winner_id:
                        if hasattr(self.bot, 'user_data_manager'):
                            await self.bot.user_data_manager.update_energon_stat(player_id, "games_won", 1)
                        else:
                            from Systems.user_data_manager import user_data_manager
                            await user_data_manager.update_energon_stat(player_id, "games_won", 1)
                    else:
                        if hasattr(self.bot, 'user_data_manager'):
                            await self.bot.user_data_manager.update_energon_stat(player_id, "games_lost", 1)
                        else:
                            from Systems.user_data_manager import user_data_manager
                            await user_data_manager.update_energon_stat(player_id, "games_lost", 1)
                    
                except Exception as e:
                    print(f"Error processing player {player_id} game end: {e}")
            
            # Remove the game from active games
            if channel_id in self.game_data:
                del self.game_data[channel_id]
            
            # Update global active_games if it exists
            if 'active_games' in globals():
                global active_games
                if channel_id in active_games:
                    del active_games[channel_id]
            
            # Save state immediately
            await self.save_game_state()
            
            print(f"Ended game in channel {channel_id}. Winner: {winner_id}")
            return True
            
        except Exception as e:
            print(f"Error ending game: {e}")
            return False

    async def get_global_leaderboard(self) -> Dict[str, Any]:
        """Get the global leaderboard for quick loading."""
        try:
            from Systems.user_data_manager import user_data_manager
            
            # Load from the actual global energon game file
            global_data = await user_data_manager.get_energon_game_state(None)
            return global_data.get("leaderboard", {"daily": {}, "weekly": {}, "all_time": {}})
            
        except Exception as e:
            print(f"Error loading global leaderboard: {e}")
            return {"daily": {}, "weekly": {}, "all_time": {}}

    async def get_player_global_rank(self, player_id: str) -> Dict[str, Any]:
        """Get a player's rank from the global leaderboard."""
        try:
            leaderboard = await self.get_global_leaderboard()
            
            player_data = {}
            for period in ["daily", "weekly", "all_time"]:
                if player_id in leaderboard.get(period, {}):
                    player_data[period] = leaderboard[period][player_id]
                else:
                    player_data[period] = None
            
            return player_data
            
        except Exception as e:
            print(f"Error getting player global rank: {e}")
            return {"daily": None, "weekly": None, "all_time": None}
        
    def _ensure_state_loaded(self) -> None:
        """Ensure game state is loaded before accessing data."""
        # In async setup, state is loaded immediately
        if not self._game_state_loaded:
            print("Warning: Game state not loaded. Ensure setup() is called properly.")
            # We'll skip auto-loading in async contexts to avoid blocking
    
    async def get_player_stats(self, player_id: str) -> Dict[str, Any]:
        """Get or create player statistics."""
        self._ensure_state_loaded()
        
        # Use bot's user_data_manager to get energon stats
        if hasattr(self.bot, 'user_data_manager'):
            return await self.bot.user_data_manager.get_energon_stats(player_id)
        else:
            from Systems.user_data_manager import user_data_manager
            return await user_data_manager.get_energon_stats(player_id)

    def update_player_stats(self, player_id: str, stat_type: str, amount: int = 1) -> None:
        """Update player statistics and save immediately."""
        self._ensure_state_loaded()
            
        if hasattr(self.bot, 'user_data_manager'):
            self.bot.user_data_manager.update_energon_stat(player_id, stat_type, amount)
        else:
            from Systems.user_data_manager import user_data_manager
            user_data_manager.update_energon_stat(player_id, stat_type, amount)

    async def bank_player_energon(self, player_id: str, final_energon: int) -> None:
        """Save player's final energon to their bank for future games and update global leaderboard."""
        try:
            from Systems.user_data_manager import user_data_manager
            
            # Update the player's banked energon in their user file
            await user_data_manager.update_energon_stat(player_id, "energon_bank", final_energon)
            
            # Also save to global leaderboard for quick loading
            await self.save_player_energon_to_global(player_id, final_energon)
            
            print(f"Banked {final_energon} energon for player {player_id} (user file + global leaderboard)")
            
        except Exception as e:
            print(f"Error banking energon for player {player_id}: {e}")
            
    async def get_player_banked_energon(self, player_id: str) -> int:
        """Get player's banked energon amount."""
        try:
            from Systems.user_data_manager import user_data_manager
            
            energon_data = await user_data_manager.get_energon_data(player_id)
            return energon_data.get("energon_bank", 0)
            
        except Exception as e:
            print(f"Error getting banked energon for player {player_id}: {e}")
            return 0

    async def use_energon_for_bet(self, player_id: str, amount: int) -> tuple[bool, str]:
        """
        Use energon for bets. Checks current energon first, then banked energon.
        Returns (success, message)
        """
        try:
            from Systems.user_data_manager import user_data_manager
            
            energon_data = await user_data_manager.get_energon_data(player_id)
            current_energon = energon_data.get("energon", 0)
            banked_energon = energon_data.get("energon_bank", 0)
            
            # Check if in active energon rush game (current energon > 0)
            in_game = current_energon > 0 or energon_data.get("in_energon_rush", False)
            
            if in_game:
                # In game: use current energon, fallback to banked if needed
                if current_energon >= amount:
                    # Use current energon (game balance - doesn't affect total_earned tracking)
                    energon_data["energon"] = current_energon - amount
                    await user_data_manager.save_energon_data(player_id, energon_data)
                    return True, f"Used {amount} Energon from current game balance."
                elif banked_energon >= amount:
                    # Use banked energon as backup (this affects main balance, use proper tracking)
                    await user_data_manager.subtract_energon(player_id, amount, "game_bet")
                    return True, f"Used {amount} Energon from banked balance."
                else:
                    return False, f"Insufficient energon. Need {amount}, have {current_energon} (current) + {banked_energon} (banked)."
            else:
                # Not in game: use banked energon for challenges/bets (affects main balance)
                if banked_energon >= amount:
                    await user_data_manager.subtract_energon(player_id, amount, "bet")
                    return True, f"Used {amount} Energon from banked balance."
                else:
                    return False, f"Insufficient banked energon. Need {amount}, have {banked_energon} banked."
                    
        except Exception as e:
            print(f"Error using energon for bet: {e}")
            return False, "Error processing energon transaction."

    async def award_energon_to_bank(self, player_id: str, amount: int) -> None:
        """Award energon directly to player's bank (for bets, etc.)"""
        try:
            from Systems.user_data_manager import user_data_manager
            
            energon_data = await user_data_manager.get_energon_data(player_id)
            banked_energon = energon_data.get("energon_bank", 0)
            
            energon_data["energon_bank"] = banked_energon + amount
            await user_data_manager.save_energon_data(player_id, energon_data)
            
            print(f"Awarded {amount} energon to bank for player {player_id}")
            
        except Exception as e:
            print(f"Error awarding energon to bank: {e}")

    async def initialize_player(self, player_id: str, player_name: str) -> None:
        """Initialize a player for the Energon Rush game - starts at 0 energon."""
        try:
            from Systems.user_data_manager import user_data_manager
            
            # Always start energon rush with 0 energon - it's a race to 10,000
            new_energon_data = {
                "energon": 0,  # Race starts at 0 energon
                "username": player_name,
                "in_energon_rush": True  # Flag to indicate player is in active game
            }
            
            # Save the initial energon data
            await user_data_manager.save_energon_data(player_id, new_energon_data)
            
            # Initialize player stats if new player
            player_stats = await user_data_manager.get_energon_data(player_id)
            if "games_played" not in player_stats:
                await user_data_manager.update_energon_stat(player_id, "games_played")
            
            print(f"Initialized player {player_name} ({player_id}) for Energon Rush starting at 0 energon")
            
        except Exception as e:
            print(f"Error initializing player {player_name} ({player_id}): {e}")
            raise e

class MarketConfig:
    """Configuration constants for the market system."""
    
    # File paths
    
    
    # Market settings
    UPDATE_INTERVAL = 3600  # 1 hour in seconds for realistic market updates
    MIN_INVESTMENT = 10.0
    MAX_PRICE = 1000000.0
    MIN_PRICE = 0.01
    
    # Event probabilities
    EVENT_CHANCE = 0.25  # 25% chance of new event
    HOLIDAY_EVENT_CHANCE = 0.8  # 80% chance for Christmas, etc.
    
    # Holiday event cycling settings
    HOLIDAY_EVENT_CYCLE_INTERVAL = 300  # 5 minutes between holiday events
    HOLIDAY_EVENT_DURATION = 24  # 24 hours of guaranteed holiday events

class HolidayData:
    """Holiday definitions and their market effects."""
    
    HOLIDAYS = {
        (1, 1): {"name": "New Year", "type": "surge", "multiplier_range": (1.3, 2.5), "message_prefix": "🎆", "probability": 0.7},
        (1, 25): {"name": "Chinese New Year", "type": "surge", "multiplier_range": (1.3, 2.2), "message_prefix": "🧧", "probability": 0.6},
        (2, 14): {"name": "Valentine's Day", "type": "surge", "multiplier_range": (1.1, 1.8), "message_prefix": "💝", "probability": 0.5},
        (2, 21): {"name": "Carnival", "type": "surge", "multiplier_range": (1.3, 2.4), "message_prefix": "🎭", "probability": 0.7},
        (3, 8): {"name": "Holi", "type": "surge", "multiplier_range": (1.2, 2.3), "message_prefix": "🌈", "probability": 0.6},
        (3, 17): {"name": "St. Patrick's Day", "type": "mixed", "multiplier_range": (0.7, 1.6), "message_prefix": "🍀", "probability": 0.6},
        (3, 21): {"name": "Nowruz", "type": "surge", "multiplier_range": (1.2, 2.1), "message_prefix": "🌸", "probability": 0.6},
        (4, 1): {"name": "April Fools", "type": "chaos", "multiplier_range": (0.2, 4.0), "message_prefix": "🎯", "probability": 0.9},
        (4, 9): {"name": "Easter", "type": "surge", "multiplier_range": (1.3, 2.2), "message_prefix": "🐰", "probability": 0.6},
        (4, 21): {"name": "Tiradentes Day", "type": "surge", "multiplier_range": (1.1, 1.9), "message_prefix": "🇧🇷", "probability": 0.5},
        (4, 23): {"name": "Passover", "type": "mixed", "multiplier_range": (0.9, 1.6), "message_prefix": "🍞", "probability": 0.5},
        (4, 24): {"name": "Ramadan", "type": "mixed", "multiplier_range": (0.8, 1.5), "message_prefix": "🌙", "probability": 0.5},
        (4, 25): {"name": "Anzac Day", "type": "mixed", "multiplier_range": (0.8, 1.4), "message_prefix": "🦘", "probability": 0.5},
        (5, 4): {"name": "Decepticon Uprising", "type": "crash", "multiplier_range": (0.2, 0.6), "message_prefix": "💀", "probability": 0.8},
        (5, 5): {"name": "Cinco de Mayo", "type": "surge", "multiplier_range": (1.2, 2.0), "message_prefix": "🪅", "probability": 0.6},
        (5, 6): {"name": "Children's Day", "type": "surge", "multiplier_range": (1.1, 1.8), "message_prefix": "👶", "probability": 0.5},
        (5, 8): {"name": "V-E Day", "type": "mixed", "multiplier_range": (0.9, 1.5), "message_prefix": "🕊️", "probability": 0.5},
        (6, 15): {"name": "Cybertron Day", "type": "surge", "multiplier_range": (2.0, 5.0), "message_prefix": "🤖", "probability": 0.9},
        (6, 18): {"name": "Dragon Boat Festival", "type": "surge", "multiplier_range": (1.2, 2.1), "message_prefix": "🐉", "probability": 0.6},
        (7, 1): {"name": "Canada Day", "type": "surge", "multiplier_range": (1.2, 2.0), "message_prefix": "🍁", "probability": 0.6},
        (7, 4): {"name": "Independence Day", "type": "surge", "multiplier_range": (1.2, 2.0), "message_prefix": "🎆", "probability": 0.6},
        (7, 14): {"name": "Bastille Day", "type": "surge", "multiplier_range": (1.3, 2.2), "message_prefix": "🗼", "probability": 0.6},
        (8, 8): {"name": "Energon Discovery Day", "type": "surge", "multiplier_range": (1.8, 3.5), "message_prefix": "⚡", "probability": 0.8},
        (8, 22): {"name": "Qixi Festival", "type": "surge", "multiplier_range": (1.1, 1.9), "message_prefix": "💕", "probability": 0.5},
        (9, 11): {"name": "Remembrance Day", "type": "crash", "multiplier_range": (0.5, 0.9), "message_prefix": "🕊️", "probability": 0.6},
        (9, 21): {"name": "Oktoberfest", "type": "mixed", "multiplier_range": (0.9, 1.7), "message_prefix": "🍻", "probability": 0.6},
        (9, 29): {"name": "Chuseok", "type": "surge", "multiplier_range": (1.2, 2.0), "message_prefix": "🌕", "probability": 0.6},
        (10, 24): {"name": "Diwali", "type": "surge", "multiplier_range": (1.4, 2.8), "message_prefix": "🪔", "probability": 0.7},
        (10, 31): {"name": "Halloween", "type": "crash", "multiplier_range": (0.3, 0.8), "message_prefix": "🎃", "probability": 0.7},
        (11, 2): {"name": "Día de los Muertos", "type": "mixed", "multiplier_range": (0.8, 1.7), "message_prefix": "💀", "probability": 0.6},
        (11, 24): {"name": "Thanksgiving", "type": "surge", "multiplier_range": (1.2, 2.0), "message_prefix": "🦃", "probability": 0.5},
        (12, 18): {"name": "Hanukkah", "type": "surge", "multiplier_range": (1.2, 2.0), "message_prefix": "🕎", "probability": 0.6},
        (12, 25): {"name": "Christmas", "type": "surge", "multiplier_range": (1.5, 3.0), "message_prefix": "🎄", "probability": 0.8},
    }

class EventData:
    """Market event definitions with weighted probabilities."""
    
    WEIGHTED_EVENTS = {}
    
    @classmethod
    def load_events(cls):
        """Load events from JSON file."""
        try:
            events_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Data", "coinevents.json")
            with open(events_file, 'r', encoding='utf-8') as f:
                events_data = json.load(f)
                
            # Convert multiplier_range lists to tuples
            for event_type, event_data in events_data.items():
                if 'multiplier_range' in event_data and isinstance(event_data['multiplier_range'], list):
                    event_data['multiplier_range'] = tuple(event_data['multiplier_range'])
                
            cls.WEIGHTED_EVENTS = events_data
            print("Market events loaded from coinevents.json")
            
        except Exception as e:
            print(f"Error loading events from JSON: {e}")
            # Fallback to hardcoded events if JSON loading fails
            cls.WEIGHTED_EVENTS = {
                "catastrophic_crashes": {
                    "weight": 5,
                    "multiplier_range": (0.1, 0.4),
                    "duration": 4,
                    "events": ["Market crash event - Fallback data"]
                },
                "minor_events": {
                    "weight": 15,
                    "multiplier_range": (0.85, 1.15),
                    "duration": 4,
                    "events": ["Minor market event - Fallback data"]
                }
            }

# Market Utility Functions
def get_current_holiday() -> Optional[Dict]:
    """Detect if today is a holiday and return holiday information."""
    now = datetime.utcnow()
    today = (now.month, now.day)
    return HolidayData.HOLIDAYS.get(today)

def get_holiday_events(holiday_info) -> Dict[str, List[str]]:
    """Generate holiday-specific events based on holiday type."""
    try:
        holidays_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Data", "holidays.json")
        with open(holidays_file, 'r', encoding='utf-8') as f:
            holiday_events = json.load(f)
        
        # Handle both dictionary input and string input
        holiday_name = holiday_info["name"] if isinstance(holiday_info, dict) else holiday_info
        
        # Return the holiday events dict with both surge and crash events
        default_events = {
            "surge": [f"🎉 {holiday_name.upper()} SURGE - Holiday celebration boosts energon markets!"],
            "crash": [f"💥 {holiday_name.upper()} CRASH - Holiday disaster strikes energon markets!"]
        }
        
        return holiday_events.get(holiday_name, default_events)
        
    except Exception as e:
        print(f"Error loading holiday events from JSON: {e}")
        # Fallback to generic holiday events if JSON loading fails
        holiday_name = holiday_info["name"] if isinstance(holiday_info, dict) else holiday_info
        return {
            "surge": [f"🎉 {holiday_name.upper()} SURGE - Holiday celebration boosts energon markets!"],
            "crash": [f"💥 {holiday_name.upper()} CRASH - Holiday disaster strikes energon markets!"]
        }

def select_weighted_event() -> Tuple[str, Dict]:
    """Select a random market event based on weighted probabilities."""
    total_weight = sum(event["weight"] for event in EventData.WEIGHTED_EVENTS.values())
    random_value = random.uniform(0, total_weight)
    
    current_weight = 0
    for event_type, event_data in EventData.WEIGHTED_EVENTS.items():
        current_weight += event_data["weight"]
        if random_value <= current_weight:
            return event_type, event_data
    
    # Fallback to minor events
    return "minor_events", EventData.WEIGHTED_EVENTS["minor_events"]

def generate_price_chart(price_history: List[float]) -> str:
    """Generate an ASCII chart of price history."""
    if len(price_history) < 2:
        return "Market initializing..."
    
    # Get last 15 updates
    recent_prices = price_history[-15:] if len(price_history) >= 15 else price_history
    
    if len(recent_prices) < 2:
        return "Insufficient data..."
    
    min_price = min(recent_prices)
    max_price = max(recent_prices)
    
    if max_price == min_price:
        return "─" * len(recent_prices)
    
    chart_height = 8
    chart = []
    
    for price in recent_prices:
        normalized = (price - min_price) / (max_price - min_price)
        bar_height = int(normalized * chart_height)
        bar = "█" * max(1, bar_height) + " " * (chart_height - bar_height)
        chart.append(bar)
    
    # Transpose to horizontal
    result = []
    for i in range(chart_height):
        line = ""
        for bar in chart:
            line += bar[chart_height - 1 - i] if len(bar) > chart_height - 1 - i else " "
        result.append(line)
    
    return "\n".join(result)

# Initialize event data after all functions are defined
def initialize_event_data():
    """Initialize event data from JSON files."""
    try:
        EventData.load_events()
    except Exception as e:
        print(f"Failed to initialize event data: {e}")

# Initialize on module load
initialize_event_data()

# Market Management Classes
class MarketManager:
    """Manages CyberCoin market data and operations."""
    
    def __init__(self):
        self.market_data = self.get_default_market_data()
    
    async def initialize(self):
        """Initialize market data asynchronously."""
        self.market_data = await self.load_market_data()
    
    async def load_market_data(self) -> Dict:
        """Load market data from user_data_manager or initialize defaults."""
        try:
            from Systems.user_data_manager import user_data_manager
            
            # Get market data from user_data_manager using proper async/await
            data = await user_data_manager.get_cybercoin_market_data()
            
            if data and "market_data" in data and data["market_data"]:
                # Extract the actual market data from the nested structure
                market_data = data["market_data"]
                # Convert string timestamps back to datetime objects
                if "last_update" in market_data:
                    if isinstance(market_data["last_update"], str):
                        market_data["last_update"] = datetime.fromisoformat(market_data["last_update"])
                return market_data
                
        except Exception as e:
            print(f"Error loading market data: {e}")
        
        return self.get_default_market_data()
    
    def get_default_market_data(self) -> Dict:
        """Return default market data structure."""
        return {
            "current_price": 100.0,
            "price_history": [100.0],
            "total_volume_24h": 0.0,
            "market_trend": "stable",
            "last_update": datetime.utcnow(),
            "buy_pressure": 0.0,
            "sell_pressure": 0.0,
            "market_events": [],
            "active_event": None,
            "event_updates_remaining": 0,
            "current_holiday": None,
            "total_coins_in_circulation": 0.0
        }
    
    async def save_market_data(self) -> None:
        """Save market data to user_data_manager."""
        try:
            from Systems.user_data_manager import user_data_manager
            
            # Convert datetime objects to ISO strings for JSON serialization
            data_to_save = self.market_data.copy()
            if isinstance(data_to_save["last_update"], datetime):
                data_to_save["last_update"] = data_to_save["last_update"].isoformat()
            
            # Wrap market data in the expected structure
            wrapped_data = {
                "market_data": data_to_save,
                "last_updated": datetime.utcnow().isoformat()
            }
            
            # Save market data using user_data_manager with proper async/await
            await user_data_manager.save_cybercoin_market_data(wrapped_data)
                    
        except Exception as e:
            print(f"Error saving market data: {e}")
    
    def get_next_holiday_event(self, current_holiday: dict, is_surge: bool) -> str:
        """Get the next holiday event from the cycling system."""
        holiday_events = get_holiday_events(current_holiday)
        event_type = "surge" if is_surge else "crash"
        events_list = holiday_events.get(event_type, [])
        
        if not events_list:
            # Fallback to default events if no events found
            return f"🎉 {current_holiday['name']} {'SURGE' if is_surge else 'CRASH'} - Holiday {'celebration' if is_surge else 'disaster'}!"
        
        # Cycle through events (use current hour as index for variety)
        current_hour = datetime.utcnow().hour
        event_index = current_hour % len(events_list)
        return events_list[event_index]
    
    def calculate_dynamic_price(self) -> float:
        """Calculate new price based on market forces, supply/demand, and volatility."""
        current_price = self.market_data["current_price"]
        
        # Base volatility (random market movement)
        base_volatility = random.uniform(-0.05, 0.05)  # ±5% random movement
        
        # Supply and demand pressure
        buy_pressure = self.market_data.get("buy_pressure", 0)
        sell_pressure = self.market_data.get("sell_pressure", 0)
        net_pressure = (buy_pressure - sell_pressure) * 0.001  # Scale factor
        
        # Market sentiment based on recent trend
        sentiment_factor = 0
        if len(self.market_data["price_history"]) >= 3:
            recent_prices = self.market_data["price_history"][-3:]
            if recent_prices[-1] > recent_prices[0]:
                sentiment_factor = 0.02  # Positive momentum
            elif recent_prices[-1] < recent_prices[0]:
                sentiment_factor = -0.02  # Negative momentum
        
        # Event multiplier (if active event)
        event_multiplier = 1.0
        if self.market_data.get("active_event") and self.market_data.get("event_updates_remaining", 0) > 0:
            event_data = self.market_data["active_event"]
            event_multiplier = event_data.get("multiplier", 1.0)
        
        # Holiday effects - 100% guaranteed on holiday days
        holiday_multiplier = 1.0
        current_holiday = get_current_holiday()
        if current_holiday:
            # Force holiday multiplier - no random chance, guaranteed to happen
            holiday_multiplier = random.uniform(*current_holiday["multiplier_range"])
            
            # Track that we're in a holiday event for guaranteed cycling
            if "holiday_event_active" not in self.market_data:
                self.market_data["holiday_event_active"] = True
                self.market_data["holiday_event_start_time"] = datetime.utcnow()
                self.market_data["last_holiday_event_type"] = "surge"  # Start with surge
        
        # Calculate total price change
        total_change = base_volatility + net_pressure + sentiment_factor
        new_price = current_price * (1 + total_change) * event_multiplier * holiday_multiplier
        
        # Ensure price stays within bounds
        new_price = max(MarketConfig.MIN_PRICE, min(MarketConfig.MAX_PRICE, new_price))
        
        return new_price
    
    def update_market_trend(self) -> None:
        """Update market trend based on recent price history."""
        if len(self.market_data["price_history"]) >= 5:
            recent_trend = self.market_data["price_history"][-5:]
            trend_changes = [recent_trend[i+1] - recent_trend[i] for i in range(len(recent_trend)-1)]
            avg_change = sum(trend_changes) / len(trend_changes)
            current_price = self.market_data["current_price"]
            
            if avg_change > current_price * 0.05:
                self.market_data["market_trend"] = "bullish"
            elif avg_change < -current_price * 0.05:
                self.market_data["market_trend"] = "bearish"
            else:
                self.market_data["market_trend"] = "stable"
    
    def update_supply_demand(self, transaction_type: str, amount: float) -> None:
        """Update buy/sell pressure based on transactions."""
        # Ensure pressure fields exist
        if "buy_pressure" not in self.market_data:
            self.market_data["buy_pressure"] = 0.0
        if "sell_pressure" not in self.market_data:
            self.market_data["sell_pressure"] = 0.0
            
        if transaction_type == "buy":
            self.market_data["buy_pressure"] += amount
        elif transaction_type == "sell":
            self.market_data["sell_pressure"] += amount
        
        # Decay pressure over time (simulate market equilibrium)
        self.market_data["buy_pressure"] *= 0.95
        self.market_data["sell_pressure"] *= 0.95
    
    def add_market_event(self, event_message: str) -> None:
        """Add a new market event to history."""
        self.market_data["market_events"].append(event_message)
        if len(self.market_data["market_events"]) > 15:
            self.market_data["market_events"] = self.market_data["market_events"][-15:]
    
    async def get_user_cybercoin_summary(self, user_id: str) -> dict:
        """Get comprehensive CyberCoin summary for a user using new transaction system."""
        from Systems.user_data_manager import get_cybercoin_summary
        return await get_cybercoin_summary(user_id)
    
    def record_purchase(self, user_id: str, amount_invested: float, coins_received: float, price_per_coin: float) -> None:
        """Record a CyberCoin purchase using the new transaction system."""
        from Systems.user_data_manager import record_cybercoin_purchase
        record_cybercoin_purchase(user_id, amount_invested, coins_received, price_per_coin)
        
        # Update supply/demand pressure
        self.update_supply_demand("buy", amount_invested)
        
        # Update total volume
        self.market_data["total_volume_24h"] += amount_invested
        self.market_data["total_coins_in_circulation"] += coins_received
    
    def record_sale(self, user_id: str, coins_sold: float, sale_amount: float, price_per_coin: float) -> dict:
        """Record a CyberCoin sale using the new transaction system and return sale details."""
        from Systems.user_data_manager import record_cybercoin_sale
        result = record_cybercoin_sale(user_id, coins_sold, sale_amount, price_per_coin)
        
        # Update supply/demand pressure
        self.update_supply_demand("sell", sale_amount)
        
        # Update total volume
        self.market_data["total_volume_24h"] += sale_amount
        self.market_data["total_coins_in_circulation"] -= coins_sold
        
        return result
    
    def get_user_available_coins(self, user_id: str) -> float:
        """Get the total number of coins a user currently holds."""
        from Systems.user_data_manager import get_cybercoin_portfolio
        portfolio = get_cybercoin_portfolio(user_id)
        return portfolio.get('total_coins', 0)
    
    async def get_user_portfolio_value(self, user_id: str, current_price: float) -> dict:
        """Calculate user's portfolio value and profit/loss."""
        summary = await self.get_user_cybercoin_summary(user_id)
        total_value = summary['portfolio']['total_coins'] * current_price
        unrealized_pnl = total_value - summary['portfolio']['total_invested']
        
        return {
            'total_coins': summary['portfolio']['total_coins'],
            'total_value': total_value,
            'total_invested': summary['portfolio']['total_invested'],
            'total_sold': summary['portfolio']['total_sold'],
            'realized_profit': summary['portfolio']['total_profit'],
            'unrealized_pnl': unrealized_pnl,
            'total_return': summary['portfolio']['total_profit'] + unrealized_pnl
        }

    def should_cycle_holiday_event(self) -> bool:
        """Check if we should cycle to the next holiday event (50/50 crash/surge)."""
        if not self.market_data.get("holiday_event_active"):
            return False
            
        last_cycle = self.market_data.get("last_holiday_cycle", datetime.utcnow())
        time_since_last_cycle = (datetime.utcnow() - last_cycle).total_seconds()
        
        # Cycle every 5 minutes during holidays
        return time_since_last_cycle >= MarketConfig.HOLIDAY_EVENT_CYCLE_INTERVAL

    def cycle_holiday_event(self, current_holiday: dict) -> None:
        """Cycle to the next holiday event with 50/50 crash/surge chance."""
        # 50/50 chance for crash or surge
        is_surge = random.random() < 0.5
        
        # Get the next event from our cycling system
        event_message = self.get_next_holiday_event(current_holiday, is_surge)
        holiday_multiplier = random.uniform(*current_holiday["multiplier_range"])
        
        # Update the active holiday event
        self.market_data["active_event"] = {
            'type': f"holiday_{current_holiday['name'].lower().replace(' ', '_')}_cycle",
            'message': event_message,
            'multiplier': holiday_multiplier,
            'holiday_name': current_holiday['name']
        }
        
        # Track cycling state
        self.market_data["last_holiday_cycle"] = datetime.utcnow()
        self.market_data["last_holiday_event_type"] = "surge" if is_surge else "crash"
        
        # Add market event notification
        self.add_market_event(f"🎉 Holiday Event Cycle: {event_message}")
        
        # Reset cycle timer for next event
        self.market_data["event_updates_remaining"] = MarketConfig.HOLIDAY_EVENT_CYCLE_INTERVAL // 3600  # Convert to hours

# Discord UI Components for CyberCoin Market
class CryptoMarketView(discord.ui.View):
    """Discord UI view for the CyberCoin market interface."""
    
    def __init__(self):
        super().__init__(timeout=None)
        self.message = None
    
    @discord.ui.button(label="💰 Buy CyberCoin", style=discord.ButtonStyle.success, emoji="📈")
    async def buy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle buy button click."""
        if not has_cybertronian_role(interaction.user):
            await interaction.response.send_message("❌ Only verified users can trade!", ephemeral=True)
            return
        
        player_id = str(interaction.user.id)
        current_energon = await get_player_energon(player_id)
        
        if current_energon < MarketConfig.MIN_INVESTMENT:
            await interaction.response.send_message(
                f"❌ You need at least {MarketConfig.MIN_INVESTMENT} Energon to buy!", 
                ephemeral=True
            )
            return
        
        await interaction.response.send_modal(BuyCoinModal(interaction.user, current_energon, self.message))
    
    @discord.ui.button(label="💸 Sell CyberCoin", style=discord.ButtonStyle.danger, emoji="📉")
    async def sell_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle sell button click."""
        player_id = str(interaction.user.id)
        market_manager = MarketManager()
        await market_manager.initialize()
        
        available_coins = market_manager.get_user_available_coins(player_id)
        current_energon = await get_player_energon(player_id)
        
        if available_coins <= 0:
            await interaction.response.send_message("❌ You don't have any CyberCoins to sell!", ephemeral=True)
            return
        
        await interaction.response.send_modal(SellCoinModal(interaction.user, available_coins, current_energon, self.message))

class BuyCoinModal(discord.ui.Modal):
    """Modal for buying CyberCoin."""
    
    def __init__(self, user: discord.Member, current_energon: float, message: discord.Message):
        super().__init__(title="💰 Buy CyberCoin")
        self.user = user
        self.current_energon = current_energon
        self.message = message
        
        self.amount = discord.ui.TextInput(
            label="Number of CyberCoins to buy",
            placeholder="Enter the amount of coins you want to purchase",
            min_length=1,
            max_length=10
        )
        self.add_item(self.amount)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Process the buy order."""
        try:
            coins_to_buy = float(self.amount.value)
            
            if coins_to_buy <= 0:
                await interaction.response.send_message(
                    f"❌ You must buy at least some coins!",
                    ephemeral=True
                )
                return
            
            market_manager = MarketManager()
            await market_manager.initialize()
            current_price = market_manager.market_data["current_price"]
            invest_amount = coins_to_buy * current_price
            
            # Check minimum investment requirement
            if invest_amount < MarketConfig.MIN_INVESTMENT:
                min_coins = MarketConfig.MIN_INVESTMENT / current_price
                await interaction.response.send_message(
                    f"❌ Minimum investment is **{MarketConfig.MIN_INVESTMENT} Energon** (≈**{min_coins:.4f} coins** at current price)!",
                    ephemeral=True
                )
                return
            
            if invest_amount > self.current_energon:
                max_coins = self.current_energon / current_price
                await interaction.response.send_message(
                    f"❌ You only have **{self.current_energon} Energon** available (≈**{max_coins:.4f} coins** at current price)!",
                    ephemeral=True
                )
                return
            
            coins_received = coins_to_buy
            
            player_id = str(self.user.id)
            
            # Record the purchase using the new transaction system
            market_manager.record_purchase(player_id, invest_amount, coins_received, current_price)
            
            # Update player energon
            await update_player_energon(player_id, -invest_amount)
            
            # Update market data (legacy system for compatibility)
            market_manager.market_data["buy_pressure"] += 1
            market_manager.market_data["total_volume_24h"] += invest_amount
            market_manager.market_data["total_coins_in_circulation"] += coins_received
            await market_manager.save_market_data()
            
            # Get updated portfolio info
            portfolio_info = await market_manager.get_user_portfolio_value(player_id, current_price)
            
            embed = discord.Embed(
                title="✅ Purchase Successful!",
                description=f"You purchased **{coins_received:.4f}** CyberCoins for **{invest_amount:.2f}** Energon at **{current_price:.2f}** Energon per coin",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(
                name="💰 Amount Invested",
                value=f"**{invest_amount:.2f}** Energon",
                inline=True
            )
            
            embed.add_field(
                name="📊 New Holdings",
                value=f"**{portfolio_info['total_coins']:.4f}** CyberCoins",
                inline=True
            )
            
            embed.add_field(
                name="💎 Total Invested",
                value=f"**{portfolio_info['total_invested']:.2f}** Energon",
                inline=True
            )
            
            embed.set_footer(text="CyberCoin Market - Transaction complete")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Update the market message
            if self.message:
                new_embed = await create_market_embed()
                await self.message.edit(embed=new_embed)
                
        except ValueError:
            await interaction.response.send_message(
                "❌ Please enter a valid number!",
                ephemeral=True
            )

class SellCoinModal(discord.ui.Modal):
    """Modal for selling CyberCoin."""
    
    def __init__(self, user: discord.Member, owned_coins: float, current_energon: float, message: discord.Message):
        super().__init__(title="💸 Sell CyberCoin")
        self.user = user
        self.owned_coins = owned_coins
        self.current_energon = current_energon
        self.message = message
        
        self.amount = discord.ui.TextInput(
            label="Amount to sell (CyberCoins)",
            placeholder=f"Max: {owned_coins:.4f}",
            min_length=1,
            max_length=10
        )
        self.add_item(self.amount)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Process the sell order."""
        try:
            sell_amount = float(self.amount.value)
            
            if sell_amount <= 0:
                await interaction.response.send_message(
                    "❌ Please enter a positive amount!",
                    ephemeral=True
                )
                return
            
            if sell_amount > self.owned_coins:
                await interaction.response.send_message(
                    f"❌ You only have **{self.owned_coins:.4f}** CyberCoins!",
                    ephemeral=True
                )
                return
            
            market_manager = MarketManager()
            await market_manager.initialize()
            current_price = market_manager.market_data["current_price"]
            energon_received = sell_amount * current_price
            
            player_id = str(self.user.id)
            
            # Record the sale using the new transaction system (FIFO)
            sale_details = market_manager.record_sale(player_id, sell_amount, energon_received, current_price)
            
            # Update player energon
            await update_player_energon(player_id, energon_received)
            
            # Update market data (legacy system for compatibility)
            market_manager.market_data["sell_pressure"] += 1
            market_manager.market_data["total_volume_24h"] += energon_received
            market_manager.market_data["total_coins_in_circulation"] -= sell_amount
            await market_manager.save_market_data()
            
            # Get updated portfolio info
            portfolio_info = await market_manager.get_user_portfolio_value(player_id, current_price)
            
            embed = discord.Embed(
                title="✅ Sale Successful!",
                description=f"You sold **{sell_amount:.4f}** CyberCoins at **{current_price:.2f}** Energon per coin",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(
                name="💰 Energon Received",
                value=f"**{energon_received:.2f}** Energon",
                inline=True
            )
            
            embed.add_field(
                name="📊 Remaining Holdings",
                value=f"**{portfolio_info['total_coins']:.4f}** CyberCoins",
                inline=True
            )
            
            embed.add_field(
                name="💰 Profit from Sale",
                value=f"**{sale_details['profit_loss']:+.2f}** Energon",
                inline=True
            )
            
            embed.add_field(
                name="📈 Total Realized Profit",
                value=f"**{portfolio_info['realized_profit']:+.2f}** Energon",
                inline=True
            )
            
            embed.set_footer(text="CyberCoin Market - Transaction complete")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Update the market message
            if self.message:
                new_embed = await create_market_embed()
                await self.message.edit(embed=new_embed)
                
        except ValueError:
            await interaction.response.send_message(
                "❌ Please enter a valid number!",
                ephemeral=True
            )

# Market Commands and Functions
async def create_market_embed() -> discord.Embed:
    """Create an embed for the CyberCoin market."""
    market_manager = MarketManager()
    await market_manager.initialize()
    data = market_manager.market_data
    
    embed = discord.Embed(
        title="🚀 CyberCoin Market Dashboard",
        description="Trade CyberCoin cryptocurrency with real-time market events!",
        color=discord.Color.gold(),
        timestamp=discord.utils.utcnow()
    )
    
    # Price information with change indicator
    price_change = 0
    price_change_percent = 0
    if len(data['price_history']) >= 2:
        price_change = data['current_price'] - data['price_history'][-2]
        price_change_percent = (price_change / data['price_history'][-2]) * 100
    
    change_emoji = "📈" if price_change > 0 else "📉" if price_change < 0 else "➡️"
    change_color = "+" if price_change > 0 else ""
    
    embed.add_field(
        name="💰 Current Price",
        value=f"**{data['current_price']:.2f}** Energon\n{change_emoji} **{change_color}{price_change:+.2f}** ({price_change_percent:+.1f}%)",
        inline=True
    )
    
    # Market trend with pressure indicators
    trend_emoji = {
        "bullish": "📈",
        "bearish": "📉",
        "stable": "➡️"
    }
    buy_pressure = data.get('buy_pressure', 0)
    sell_pressure = data.get('sell_pressure', 0)
    pressure_indicator = "🟢" if buy_pressure > sell_pressure else "🔴" if sell_pressure > buy_pressure else "🟡"
    
    embed.add_field(
        name="📊 Market Trend",
        value=f"{trend_emoji.get(data['market_trend'], '➡️')} **{data['market_trend'].title()}**\n{pressure_indicator} Pressure: {abs(buy_pressure - sell_pressure):.1f}",
        inline=True
    )
    
    # Price chart
    chart = generate_price_chart(data['price_history'])
    if chart and chart != "Market initializing...":
        embed.add_field(
            name="📈 Price Chart (Last 15 Updates)",
            value=f"```\n{chart}\n```",
            inline=False
        )
    
    # Market stats with enhanced data
    market_cap = data['current_price'] * data['total_coins_in_circulation']
    
    # Calculate 24h high/low
    recent_24h = data['price_history'][-24:] if len(data['price_history']) >= 24 else data['price_history']
    high_24h = max(recent_24h) if recent_24h else data['current_price']
    low_24h = min(recent_24h) if recent_24h else data['current_price']
    
    embed.add_field(
        name="💎 Market Stats",
        value=f"**24h Volume:** {data['total_volume_24h']:.2f} Energon\n"
               f"**Market Cap:** {market_cap:.2f} Energon\n"
               f"**24h High:** {high_24h:.2f} | **Low:** {low_24h:.2f}\n"
               f"**Total Supply:** {data['total_coins_in_circulation']:.4f}\n"
               f"**Last Update:** {data['last_update'].strftime('%H:%M UTC')}",
        inline=True
    )
    
    # Active events
    if data['active_event']:
        event_info = data['active_event']
        embed.add_field(
            name="⚡ Active Event",
            value=f"**{event_info['message']}**\n"
                   f"_Updates remaining: {data['event_updates_remaining']}_",
            inline=False
        )
    
    # Recent events
    if data['market_events']:
        recent_events = data['market_events'][-3:]
        embed.add_field(
            name="📰 Recent Events",
            value="\n".join(f"• {event}" for event in recent_events),
            inline=False
        )
    
    # Holiday info
    current_holiday = get_current_holiday()
    if current_holiday:
        embed.add_field(
            name="🎉 Holiday Special",
            value=f"**{current_holiday['message_prefix']} {current_holiday['name']}** - Special market conditions active!",
            inline=False
        )
    
    embed.set_footer(text="CyberCoin Market - Live trading platform")
    return embed

async def market_update_loop():
    """Background task to update market prices and events."""
    await bot.wait_until_ready()
    
    # Store market dashboard messages for auto-refresh
    market_messages = []
    
    while not bot.is_closed():
        try:
            market_manager = MarketManager()
            await market_manager.initialize()
            data = market_manager.market_data
            
            # Use dynamic pricing system
            new_price = market_manager.calculate_dynamic_price()
            data['current_price'] = new_price
            data['price_history'].append(new_price)
            
            if len(data['price_history']) > 50:
                data['price_history'] = data['price_history'][-50:]
            
            # Handle holiday events - 100% guaranteed to happen on holiday days
            current_holiday = get_current_holiday()
            
            if current_holiday:
                # Initialize holiday event system if not already active
                if not data.get('holiday_event_active'):
                    data['holiday_event_active'] = True
                    data['holiday_event_start_time'] = datetime.utcnow()
                    data['last_holiday_event_type'] = 'surge'  # Start with surge
                    data['last_holiday_cycle'] = datetime.utcnow()
                
                # Check if we should cycle to the next holiday event (every 5 minutes)
                if market_manager.should_cycle_holiday_event():
                    market_manager.cycle_holiday_event(current_holiday)
                
                # Ensure holiday event is always active during the holiday
                if not data['active_event'] or not data['active_event']['type'].startswith('holiday_'):
                    # Force create initial holiday event
                    is_surge = random.random() < 0.5  # 50/50 initial chance
                    event_message = market_manager.get_next_holiday_event(current_holiday, is_surge)
                    holiday_multiplier = random.uniform(*current_holiday["multiplier_range"])
                    
                    data['active_event'] = {
                        'type': f"holiday_{current_holiday['name'].lower().replace(' ', '_')}_guaranteed",
                        'message': event_message,
                        'multiplier': holiday_multiplier,
                        'holiday_name': current_holiday['name']
                    }
                    data['event_updates_remaining'] = 1  # Keep it active for cycling
                    
                    market_manager.add_market_event(f"🎉 GUARANTEED Holiday Event: {event_message}")
            else:
                # Not a holiday - clean up holiday event tracking
                if data.get('holiday_event_active'):
                    data['holiday_event_active'] = False
                    data.pop('holiday_event_start_time', None)
                    data.pop('last_holiday_event_type', None)
                    data.pop('last_holiday_cycle', None)
                
                # Handle non-holiday events
                if data['active_event'] and data['event_updates_remaining'] > 0:
                    data['event_updates_remaining'] -= 1
                    
                    # Event has ended
                    if data['event_updates_remaining'] <= 0:
                        market_manager.add_market_event(f"⚡ Event ended: {data['active_event']['message']}")
                        data['active_event'] = None
                    
            # Handle holiday events - 100% guaranteed to happen on holiday days
            current_holiday = get_current_holiday()
            
            if current_holiday:
                # Initialize holiday event system if not already active
                if not data.get('holiday_event_active'):
                    data['holiday_event_active'] = True
                    data['holiday_event_start_time'] = datetime.utcnow()
                    data['last_holiday_event_type'] = 'surge'  # Start with surge
                    data['last_holiday_cycle'] = datetime.utcnow()
                
                # Check if we should cycle to the next holiday event (every 5 minutes)
                if market_manager.should_cycle_holiday_event():
                    market_manager.cycle_holiday_event(current_holiday)
                
                # Ensure holiday event is always active during the holiday
                if not data['active_event'] or not data['active_event']['type'].startswith('holiday_'):
                    # Force create initial holiday event
                    is_surge = random.random() < 0.5  # 50/50 initial chance
                    event_message = market_manager.get_next_holiday_event(current_holiday, is_surge)
                    holiday_multiplier = random.uniform(*current_holiday["multiplier_range"])
                    
                    data['active_event'] = {
                        'type': f"holiday_{current_holiday['name'].lower().replace(' ', '_')}_guaranteed",
                        'message': event_message,
                        'multiplier': holiday_multiplier,
                        'holiday_name': current_holiday['name']
                    }
                    data['event_updates_remaining'] = 1  # Keep it active for cycling
                    
                    market_manager.add_market_event(f"🎉 GUARANTEED Holiday Event: {event_message}")
            else:
                # Not a holiday - clean up holiday event tracking
                if data.get('holiday_event_active'):
                    data['holiday_event_active'] = False
                    data.pop('holiday_event_start_time', None)
                    data.pop('last_holiday_event_type', None)
                    data.pop('last_holiday_cycle', None)
                
                # Handle non-holiday events
                if data['active_event'] and data['event_updates_remaining'] > 0:
                    data['event_updates_remaining'] -= 1
                    
                    # Event has ended
                    if data['event_updates_remaining'] <= 0:
                        market_manager.add_market_event(f"⚡ Event ended: {data['active_event']['message']}")
                        data['active_event'] = None
                        
                # Random events (only when not a holiday)
                elif random.random() < MarketConfig.EVENT_CHANCE:
                    event_type, event_data = select_weighted_event()
                    event_message = random.choice(event_data["events"])
                    multiplier = random.uniform(*event_data["multiplier_range"])
                    
                    data['active_event'] = {
                        'type': event_type,
                        'message': event_message,
                        'multiplier': multiplier
                    }
                    data['event_updates_remaining'] = event_data["duration"]
                    
                    market_manager.add_market_event(f"⚡ New Event: {event_message}")
            
            # Update last update timestamp
            data['last_update'] = datetime.utcnow()
            
            market_manager.update_market_trend()
            await market_manager.save_market_data()
            
            # Update market dashboard messages every hour
            try:
                # Get the bot instance
                if bot.is_ready():
                    # Try to find market dashboard messages in configured channels
                    from config import get_channel_ids
                    # Note: We don't have guild context here, so we'll use None
                    channel_ids = get_channel_ids(None)
                    market_channel_id = channel_ids.get('cybercoin_market')
                    
                    if market_channel_id:
                        channel = bot.get_channel(market_channel_id)
                        if channel:
                            # Find the latest market dashboard message
                            async for message in channel.history(limit=10):
                                if message.author == bot.user and "🚀 CyberCoin Market Dashboard" in message.embeds[0].title if message.embeds else "":
                                    new_embed = await create_market_embed()
                                    await message.edit(embed=new_embed)
                                    break
            except Exception as e:
                print(f"Error updating market dashboard: {e}")
            
        except Exception as e:
            print(f"Error in market update loop: {e}")
        
        await asyncio.sleep(MarketConfig.UPDATE_INTERVAL)

game_manager: Optional[EnergonGameManager] = None

async def setup(bot_instance: commands.Bot) -> None:
    """Initialize the Energon system with the bot instance."""
    global game_manager
    
    game_manager = EnergonGameManager(bot_instance)
    await game_manager.load_game_state()
    
    print("Energon system initialized successfully!")


# Convenience functions for external use
async def save_energon_game_state() -> None:
    """Convenience function to save game state."""
    if game_manager:
        await game_manager.save_game_state()


async def get_player_stats(player_id: str) -> Dict[str, Any]:
    """Convenience function to get player stats."""
    if game_manager:
        return await game_manager.get_player_stats(player_id)
    return {}


def update_player_stats(player_id: str, stat_type: str, amount: int = 1) -> None:
    """Convenience function to update player stats."""
    if game_manager:
        game_manager.update_player_stats(player_id, stat_type, amount)

# Energon access functions using unified UserDataManager
async def get_player_energon(player_id: str) -> int:
    """Get player's current energon from user_data_manager."""
    try:
        from Systems.user_data_manager import user_data_manager
        
        energon_data = await user_data_manager.get_energon_data(player_id)
        return energon_data.get("energon", 0)
    except Exception:
        return 0

async def update_player_energon(player_id: str, amount: int) -> bool:
    """Update player's energon using user_data_manager."""
    try:
        from Systems.user_data_manager import user_data_manager
        
        # Use proper energon tracking methods for gains/losses
        if amount > 0:
            return await user_data_manager.add_energon(player_id, amount)
        else:
            return await user_data_manager.subtract_energon(player_id, abs(amount))
    except Exception:
        return False

# Standalone functions for backwards compatibility
async def load_energon_game_state() -> Dict[str, Any]:
    """Load energon game state - backwards compatibility function."""
    if game_manager:
        await game_manager.load_game_state()
        return {
            "game_data": game_manager.game_data,
            "challenges": game_manager.challenges,
            "cooldowns": game_manager.cooldowns,
            "player_stats": game_manager.player_stats
        }
    return {}

def has_cybertronian_role(member: discord.Member) -> bool:
    """Check if member has Cybertronian role - standalone function."""
    from config import get_role_ids
    
    guild_id = member.guild.id if member.guild else None
    role_ids_config = get_role_ids(guild_id)
    
    cybertronian_roles = []
    for role in ['Autobot', 'Decepticon', 'Maverick', 'Cybertronian_Citizen']:
        role_id = role_ids_config.get(role)
        if isinstance(role_id, list):
            cybertronian_roles.extend(role_id)
        elif role_id:
            cybertronian_roles.append(role_id)
    return any(role.id in cybertronian_roles for role in member.roles)


def create_game_info_embed(title: str, description: str, color: discord.Color) -> discord.Embed:
    """Create a game info embed - standalone function."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=discord.utils.utcnow()
    )
    return embed

__all__ = [
    'EnergonGameManager',
    'WIN_CONDITION',
    'SLOT_THEMES',
    'DIFFICULTY_MULTIPLIERS',
    'MarketManager',
    'CryptoMarketView',
    'BuyCoinModal',
    'SellCoinModal',
    'create_market_embed',
    'market_update_loop',
    'setup'
]