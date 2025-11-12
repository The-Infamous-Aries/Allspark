"""
PvP Lobby System for EnergonPets
Handles PvP matchmaking with join/leave/start functionality
"""
import discord
from discord import app_commands
from discord.ext import commands
from typing import Dict, List, Optional, Set, Tuple, Any, Union
import asyncio
import logging
import json
import os
import random
from enum import Enum, auto

logger = logging.getLogger('pvp_lobby')

class LobbyState(Enum):
    WAITING = auto()
    STARTING = auto()
    IN_PROGRESS = auto()

class PvPLobbyView(discord.ui.View):
    """View for PvP lobby with join/leave/start buttons"""
    
    def __init__(self, bot, creator: discord.Member, battle_mode: str, max_players: int = 2):
        super().__init__(timeout=3600)  # 1 hour timeout
        self.bot = bot
        self.creator = creator
        self.battle_mode = battle_mode
        self.max_players = max_players
        self.state = LobbyState.WAITING
        self.players: List[discord.Member] = [creator]
        self.message: Optional[discord.Message] = None
        self.start_task: Optional[asyncio.Task] = None
        
        # Load team names from JSON
        self.team_names = self.load_team_names()
        self.team_a_name: Optional[str] = None
        self.team_b_name: Optional[str] = None
        self.player_teams: Dict[discord.Member, str] = {}
        
        # Assign teams for team battles
        if self.is_team_battle():
            self.assign_team_names()
        
        # Set up initial buttons
        self.update_buttons()
    
    @classmethod
    def _get_cached_team_names(cls) -> List[str]:
        """Get team names from cache or load from file (cached to avoid blocking)"""
        if not hasattr(cls, '_cached_team_names') or cls._cached_team_names is None:
            try:
                pets_level_path = os.path.join('Systems', 'Data', 'PetsInfo', 'pets_level.json')
                if os.path.exists(pets_level_path):
                    with open(pets_level_path, 'r') as f:
                        data = json.load(f)
                        cls._cached_team_names = data.get('TEAM_NAMES', [])
                else:
                    cls._cached_team_names = []
            except Exception as e:
                logger.error(f"Error loading team names: {e}")
                cls._cached_team_names = []
            
            # Use fallback if no team names found
            if not cls._cached_team_names:
                cls._cached_team_names = [
                    "Team Alpha", "Team Beta", "Team Gamma", "Team Delta",
                    "Team Red", "Team Blue", "Team Green", "Team Yellow"
                ]
        return cls._cached_team_names.copy()
    
    def load_team_names(self) -> List[str]:
        """Load team names from cached data"""
        return self._get_cached_team_names()
    
    def is_team_battle(self) -> bool:
        """Check if this is a team battle mode"""
        return self.battle_mode in ["2v2", "3v3", "4v4"]
    
    def assign_team_names(self):
        """Assign random team names for team battles"""
        if len(self.team_names) >= 2:
            selected_names = random.sample(self.team_names, 2)
            self.team_a_name, self.team_b_name = selected_names
        else:
            self.team_a_name = "Team A"
            self.team_b_name = "Team B"
    
    def get_team_for_player(self, player: discord.Member) -> Optional[str]:
        """Get the team name for a player"""
        if not self.is_team_battle():
            return None
        return self.player_teams.get(player)
    
    def update_buttons(self):
        """Update the buttons based on current lobby state"""
        self.clear_items()
        
        # Join/Leave buttons
        join_button = discord.ui.Button(style=discord.ButtonStyle.primary, label="Join", custom_id="join")
        join_button.callback = self.join_callback
        self.add_item(join_button)
        
        leave_button = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Leave", custom_id="leave")
        leave_button.callback = self.leave_callback
        self.add_item(leave_button)
        
        # Start button (only for creator)
        if len(self.players) >= 2:
            start_button = discord.ui.Button(style=discord.ButtonStyle.green, label="Start Battle", custom_id="start")
            start_button.callback = self.start_callback
            self.add_item(start_button)
    
    def get_embed(self) -> discord.Embed:
        """Create an embed showing the current lobby status"""
        embed = discord.Embed(
            title=f"⚔️ {self.battle_mode.upper()} PvP Lobby",
            description=f"**Battle Type:** {self.battle_mode.upper()}\n"
                      f"**Players:** {len(self.players)}/{self.max_players}\n"
                      f"**Status:** {self.state.name.replace('_', ' ').title()}",
            color=discord.Color.blue()
        )
        
        # Add team information for team battles
        if self.is_team_battle() and self.team_a_name and self.team_b_name:
            team_a_players = [p for p in self.players if self.player_teams.get(p) == self.team_a_name]
            team_b_players = [p for p in self.players if self.player_teams.get(p) == self.team_b_name]
            unassigned_players = [p for p in self.players if p not in self.player_teams]
            
            # Team A
            team_a_list = "\n".join(
                f"{i+1}. {member.mention} {'👑' if member == self.creator else ''}"
                for i, member in enumerate(team_a_players)
            ) if team_a_players else "No players yet"
            embed.add_field(name=f"🔵 {self.team_a_name}", value=team_a_list, inline=True)
            
            # Team B
            team_b_list = "\n".join(
                f"{i+1}. {member.mention} {'👑' if member == self.creator else ''}"
                for i, member in enumerate(team_b_players)
            ) if team_b_players else "No players yet"
            embed.add_field(name=f"🔴 {self.team_b_name}", value=team_b_list, inline=True)
            
            # Unassigned players (for non-team battles or new players)
            if not self.is_team_battle() or unassigned_players:
                unassigned_list = "\n".join(
                    f"{i+1}. {member.mention} {'👑' if member == self.creator else ''}"
                    for i, member in enumerate(unassigned_players)
                ) if unassigned_players else ""
                if unassigned_list:
                    embed.add_field(name="📝 Unassigned", value=unassigned_list, inline=False)
        else:
            # Standard player list for non-team battles
            player_list = "\n".join(
                f"{i+1}. {member.mention} {'👑' if member == self.creator else ''}"
                for i, member in enumerate(self.players)
            )
            embed.add_field(name="Players", value=player_list or "No players yet", inline=False)
        
        # Add instructions
        if self.state == LobbyState.WAITING:
            instructions = ""
            if self.is_team_battle() and self.team_a_name and self.team_b_name:
                instructions = (
                    f"• Click **Join {self.team_a_name}** or **Join {self.team_b_name}** to pick your team\n"
                    f"• Click **Leave** to exit the lobby\n"
                    f"• Creator can click **Start Battle** when ready"
                )
            else:
                instructions = (
                    "• Click **Join** to enter the battle\n"
                    "• Click **Leave** to exit the lobby\n"
                    "• Creator can click **Start Battle** when ready"
                )
            embed.add_field(name="How to Play", value=instructions, inline=False)
        
        embed.set_footer(text=f"Created by {self.creator.display_name}")
        return embed
    
    async def join_callback(self, interaction: discord.Interaction):
        """Handle join button click"""
        if interaction.user in self.players:
            await interaction.response.send_message("You're already in the lobby!", ephemeral=True)
            return
            
        if len(self.players) >= self.max_players:
            await interaction.response.send_message("This lobby is full!", ephemeral=True)
            return
            
        # For team battles, show dropdown menu
        if self.is_team_battle() and self.team_a_name and self.team_b_name:
            view = TeamSelectView(self, interaction.user)
            await interaction.response.send_message(
                "Select which team you'd like to join:",
                view=view,
                ephemeral=True
            )
            return
            
        self.players.append(interaction.user)
        await self.update_lobby(interaction)
        await interaction.response.send_message("You've joined the lobby!", ephemeral=True)
    

    
    async def leave_callback(self, interaction: discord.Interaction):
        """Handle leave button click"""
        if interaction.user not in self.players:
            await interaction.response.send_message("You're not in this lobby!", ephemeral=True)
            return
            
        # Creator can't leave, they must cancel
        if interaction.user == self.creator:
            await interaction.response.send_message(
                "You're the lobby creator! Use /pvp cancel to close the lobby.",
                ephemeral=True
            )
            return
            
        self.players.remove(interaction.user)
        if interaction.user in self.player_teams:
            del self.player_teams[interaction.user]
        await self.update_lobby(interaction)
        await interaction.response.send_message("You've left the lobby.", ephemeral=True)
    
    async def start_callback(self, interaction: discord.Interaction):
        """Handle start button click"""
        if interaction.user != self.creator:
            await interaction.response.send_message("Only the lobby creator can start the battle!", ephemeral=True)
            return
            
        if len(self.players) < 2:
            await interaction.response.send_message("You need at least 2 players to start!", ephemeral=True)
            return
            
        self.state = LobbyState.STARTING
        await self.update_lobby(interaction)
        await interaction.response.defer()
        
        # Start the battle
        await self.start_battle()
    
    async def update_lobby(self, interaction: discord.Interaction):
        """Update the lobby message with current status"""
        self.update_buttons()
        try:
            await interaction.message.edit(embed=self.get_embed(), view=self)
        except Exception as e:
            logger.error(f"Error updating lobby: {e}")
    
    async def update_lobby_by_interaction(self, interaction: discord.Interaction):
        """Update the lobby message when called from dropdown interaction"""
        self.update_buttons()
        try:
            await self.message.edit(embed=self.get_embed(), view=self)
        except Exception as e:
            logger.error(f"Error updating lobby: {e}")
    
    async def start_battle(self):
        """Start the PvP battle"""
        self.state = LobbyState.IN_PROGRESS
        
        try:
            # Get the PvPCog instance
            pvp_cog = self.bot.get_cog("PvPCog")
            if not pvp_cog:
                logger.error("PvPCog not found!")
                return
            
            # Start the battle based on mode
            if self.battle_mode == "1v1" and len(self.players) == 2:
                await pvp_cog.start_1v1_battle(self.players[0], self.players[1])
            elif self.battle_mode == "2v2" and len(self.players) == 4:
                team_a = [p for p in self.players if self.player_teams.get(p) == self.team_a_name]
                team_b = [p for p in self.players if self.player_teams.get(p) == self.team_b_name]
                
                # Balance teams if they're uneven
                while len(team_a) < 2 and len(team_b) > 2:
                    player_to_move = team_b.pop()
                    team_a.append(player_to_move)
                    self.player_teams[player_to_move] = self.team_a_name
                while len(team_b) < 2 and len(team_a) > 2:
                    player_to_move = team_a.pop()
                    team_b.append(player_to_move)
                    self.player_teams[player_to_move] = self.team_b_name
                
                # Pass the lobby's team names to the battle system
                team_names = {'a': self.team_a_name, 'b': self.team_b_name}
                await pvp_cog.start_team_battle("2v2", team_a, team_b, team_names)
            elif self.battle_mode == "3v3" and len(self.players) == 6:
                team_a = [p for p in self.players if self.player_teams.get(p) == self.team_a_name]
                team_b = [p for p in self.players if self.player_teams.get(p) == self.team_b_name]
                
                # Balance teams if they're uneven
                while len(team_a) < 3 and len(team_b) > 3:
                    player_to_move = team_b.pop()
                    team_a.append(player_to_move)
                    self.player_teams[player_to_move] = self.team_a_name
                while len(team_b) < 3 and len(team_a) > 3:
                    player_to_move = team_a.pop()
                    team_b.append(player_to_move)
                    self.player_teams[player_to_move] = self.team_b_name
                
                # Pass the lobby's team names to the battle system
                team_names = {'a': self.team_a_name, 'b': self.team_b_name}
                await pvp_cog.start_team_battle("3v3", team_a, team_b, team_names)
            elif self.battle_mode == "4v4" and len(self.players) == 8:
                team_a = [p for p in self.players if self.player_teams.get(p) == self.team_a_name]
                team_b = [p for p in self.players if self.player_teams.get(p) == self.team_b_name]
                
                # Balance teams if they're uneven
                while len(team_a) < 4 and len(team_b) > 4:
                    player_to_move = team_b.pop()
                    team_a.append(player_to_move)
                    self.player_teams[player_to_move] = self.team_a_name
                while len(team_b) < 4 and len(team_a) > 4:
                    player_to_move = team_a.pop()
                    team_b.append(player_to_move)
                    self.player_teams[player_to_move] = self.team_b_name
                
                # Pass the lobby's team names to the battle system
                team_names = {'a': self.team_a_name, 'b': self.team_b_name}
                await pvp_cog.start_team_battle("4v4", team_a, team_b, team_names)
            elif self.battle_mode == "ffa" and 2 <= len(self.players) <= 8:
                await pvp_cog.start_ffa_battle(self.players)
            else:
                logger.error(f"Invalid battle mode or player count: {self.battle_mode} with {len(self.players)} players")
                
        except Exception as e:
            logger.error(f"Error starting battle: {e}", exc_info=True)
            
        # Clean up the lobby
        await self.cleanup()
    
    async def cleanup(self):
        """Clean up the lobby"""
        # Disable all buttons
        for item in self.children:
            if hasattr(item, 'disabled'):
                item.disabled = True
        
        # Edit the message to show it's closed
        try:
            if self.message:
                embed = self.get_embed()
                embed.title = f"⚔️ {self.battle_mode.upper()} PvP Lobby (Closed)"
                embed.color = discord.Color.dark_gray()
                await self.message.edit(embed=embed, view=self)
        except Exception as e:
            logger.error(f"Error cleaning up lobby: {e}")
    
    async def on_timeout(self):
        """Handle view timeout"""
        await self.cleanup()
        
        # Notify players
        if self.message:
            try:
                await self.message.channel.send("⏱️ This PvP lobby has timed out.")
            except:
                pass

class TeamSelectView(discord.ui.View):
    """Dropdown view for team selection in team battles"""
    
    def __init__(self, lobby_view: PvPLobbyView, player: discord.Member):
        super().__init__(timeout=60)  # 1 minute timeout
        self.lobby_view = lobby_view
        self.player = player
        
        # Create dropdown with team options
        options = [
            discord.SelectOption(
                label=lobby_view.team_a_name,
                description=f"Join {lobby_view.team_a_name}",
                emoji="🔵",
                value="team_a"
            ),
            discord.SelectOption(
                label=lobby_view.team_b_name,
                description=f"Join {lobby_view.team_b_name}",
                emoji="🔴",
                value="team_b"
            )
        ]
        
        select = discord.ui.Select(
            placeholder="Choose your team...",
            options=options,
            min_values=1,
            max_values=1
        )
        select.callback = self.select_callback
        self.add_item(select)
    
    async def select_callback(self, interaction: discord.Interaction):
        """Handle team selection"""
        if interaction.user != self.player:
            await interaction.response.send_message("This selection is for someone else!", ephemeral=True)
            return
            
        selected_value = interaction.data['values'][0]
        
        # Check if lobby is full
        if len(self.lobby_view.players) >= self.lobby_view.max_players:
            await interaction.response.send_message("This lobby is now full!", ephemeral=True)
            return
            
        # Remove player from teams if they're switching
        if self.player in self.lobby_view.player_teams:
            del self.lobby_view.player_teams[self.player]
            
        # Add player to selected team
        if selected_value == "team_a":
            self.lobby_view.player_teams[self.player] = self.lobby_view.team_a_name
            team_name = self.lobby_view.team_a_name
        else:
            self.lobby_view.player_teams[self.player] = self.lobby_view.team_b_name
            team_name = self.lobby_view.team_b_name
            
        # Add player to lobby
        if self.player not in self.lobby_view.players:
            self.lobby_view.players.append(self.player)
            
        # Update lobby display
        await self.lobby_view.update_lobby_by_interaction(interaction)
        
        # Confirm selection
        await interaction.response.send_message(
            f"✅ You've successfully joined **{team_name}**!",
            ephemeral=True
        )
        
        # Disable the view after selection
        self.stop()
        
        # Disable all items in the view
        for item in self.children:
            item.disabled = True
            
        # Update the ephemeral message to show selection
        try:
            await interaction.message.edit(view=self)
        except:
            pass