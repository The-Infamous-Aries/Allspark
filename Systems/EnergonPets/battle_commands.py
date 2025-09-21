import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
from typing import Optional, List, Dict, Any, Union

from .PetBattles.pvp_lobby import PvPLobbyView
from .PetBattles.battle_system import (
    UnifiedBattleView,
    battle_system,
    MONSTER_EMOJIS,
    RARITY_EMOJIS
)

# Set up logging
logger = logging.getLogger('battle_commands')

class BattleCommands(commands.Cog):
    """Battle commands for EnergonPets"""
    
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="battle_stats", description="Show comprehensive battle statistics for a user")
    @discord.app_commands.describe(
        member="The Discord member to check stats for (defaults to you)"
    )
    async def battle_stats(self, ctx, member: discord.Member = None):
        """Show comprehensive battle statistics for a user including all battle types"""
        try:
            target = member or ctx.author
            
            # Get pet data and user data
            pet = await user_data_manager.get_pet_data(str(target.id))
            user_data = await user_data_manager.get_user_data(str(target.id))
            
            if not pet:
                await ctx.send("❌ No pet found for this user.")
                return
            
            # Pet battle statistics (solo, group, PvP)
            battles_won = pet.get('battles_won', 0)
            battles_lost = pet.get('battles_lost', 0)
            total_pet_battles = battles_won + battles_lost
            
            # Mega fight statistics (from user data)
            mega_fights_won = user_data.get('mega_fights', {}).get('mega_fights_won', 0)
            mega_fights_lost = user_data.get('mega_fights', {}).get('mega_fights_lost', 0)
            total_mega_fights = mega_fights_won + mega_fights_lost
            
            # Combined totals
            total_battles_won = battles_won + mega_fights_won
            total_battles_lost = battles_lost + mega_fights_lost
            total_all_battles = total_battles_won + total_battles_lost
            
            embed = discord.Embed(
                title=f"⚔️ Battle Stats - {target.display_name}",
                description=f"**{pet.get('name', 'Unknown')}** - Level {pet.get('level', 1)}",
                color=0x0099ff
            )
            
            # Overall statistics
            if total_all_battles > 0:
                overall_win_rate = (total_battles_won / total_all_battles) * 100
                embed.add_field(
                    name="📊 Overall Battle Record",
                    value=f"**Total Won:** {total_battles_won:,}\n"
                          f"**Total Lost:** {total_battles_lost:,}\n"
                          f"**Total Battles:** {total_all_battles:,}\n"
                          f"**Overall Win Rate:** {overall_win_rate:.1f}%",
                    inline=False
                )
            
            # Pet battles breakdown (solo, group, PvP)
            if total_pet_battles > 0:
                pet_win_rate = (battles_won / total_pet_battles) * 100
                embed.add_field(
                    name="🐾 Pet Battles (Solo/Group/PvP)",
                    value=f"**Won:** {battles_won:,}\n"
                          f"**Lost:** {battles_lost:,}\n"
                          f"**Total:** {total_pet_battles:,}\n"
                          f"**Win Rate:** {pet_win_rate:.1f}%",
                    inline=True
                )
            
            # Mega fights (combiner battles)
            if total_mega_fights > 0:
                mega_win_rate = (mega_fights_won / total_mega_fights) * 100
                embed.add_field(
                    name="🤖 Mega-Fights (Combiner Battles)",
                    value=f"**Won:** {mega_fights_won:,}\n"
                          f"**Lost:** {mega_fights_lost:,}\n"
                          f"**Total:** {total_mega_fights:,}\n"
                          f"**Win Rate:** {mega_win_rate:.1f}%",
                    inline=True
                )
            
            # Additional statistics
            total_energon_won = (
                user_data.get('mega_fights', {}).get('total_energon_won', 0) +
                pet.get('total_battle_energon', 0)
            )
            
            if total_energon_won > 0:
                embed.add_field(
                    name="💰 Battle Earnings",
                    value=f"**Total Energon Won:** {total_energon_won:,}",
                    inline=False
                )
            
            await ctx.send(embed=embed)
             
        except Exception as e:
             logger.error(f"Error in battle_stats: {e}")
             await ctx.send("❌ Error retrieving battle statistics.")

    @commands.hybrid_command(name="battle", description="Start a solo battle against a monster")
    async def battle(self, ctx):
        """Start a solo battle with interactive enemy selection"""
        try:
            from .PetBattles.enemy_selection_view import EnemySelectionView
            view = EnemySelectionView(ctx, battle_type="solo")
            embed = discord.Embed(
                title="⚔️ Solo Battle Setup",
                description="Choose your opponent type and rarity:",
                color=0x0099ff
            )
            view.message = await ctx.send(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Error in battle command: {e}")
            await ctx.send("❌ Error starting battle. Please try again.")

    @commands.hybrid_command(name="group_battle", description="Start a group battle for up to 4 players")
    async def group_battle(self, ctx):
        """Start a group battle with interactive enemy selection"""
        try:
            from .PetBattles.enemy_selection_view import EnemySelectionView
            view = EnemySelectionView(ctx, battle_type="group")
            embed = discord.Embed(
                title="⚔️ Group Battle Setup",
                description="Choose enemy type and rarity for your group battle:",
                color=0x0099ff
            )
            view.message = await ctx.send(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Error in group_battle command: {e}")
            await ctx.send("❌ Error starting group battle. Please try again.")

class PvPCog(commands.Cog):
    """Commands for player vs player battles"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_battles = {}  # user_id: battle_view
        self.pending_challenges = {}  # challenger_id: {'targets': [], 'battle_mode': BattleMode}

    async def battle_mode_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete for battle mode selection"""
        modes = [
            ("1v1 Duel (2 players)", "1v1"),
            ("2v2 Team Battle (4 players)", "2v2"),
            ("3v3 Team Battle (6 players)", "3v3"),
            ("4v4 Team Battle (8 players)", "4v4"),
            ("Free For All (2-8 players)", "ffa")
        ]
        return [
            app_commands.Choice(name=name, value=value)
            for name, value in modes
            if current.lower() in name.lower()
        ][:25]

    @app_commands.command(name="pvp", description="Start a PvP battle lobby")
    @app_commands.describe(
        mode="Type of battle (1v1, 2v2, 3v3, 4v4, ffa)",
    )
    @app_commands.autocomplete(mode=battle_mode_autocomplete)
    async def pvp(self, interaction: discord.Interaction, mode: str):
        """Start a PvP battle lobby where players can join"""
        try:
            # Check if user is already in a battle
            if str(interaction.user.id) in self.active_battles:
                return await interaction.response.send_message(
                    "You're already in a battle!", 
                    ephemeral=True
                )
            
            # Set max players based on mode
            max_players = {
                "1v1": 2,
                "2v2": 4,
                "3v3": 6,
                "4v4": 8,
                "ffa": 8
            }.get(mode, 2)
            
            # Create and send the lobby
            lobby_view = PvPLobbyView(self.bot, interaction.user, mode, max_players)
            await interaction.response.send_message(embed=lobby_view.get_embed(), view=lobby_view)
            lobby_view.message = await interaction.original_response()
            
        except Exception as e:
            logger.error(f"Error in pvp command: {e}", exc_info=True)
            try:
                await interaction.response.send_message(
                    "❌ An error occurred while creating the PvP lobby. Please try again.",
                    ephemeral=True
                )
            except:
                await interaction.followup.send(
                    "❌ An error occurred while creating the PvP lobby. Please try again.",
                    ephemeral=True
                )
    
    async def start_1v1_battle(self, player1: discord.Member, player2: discord.Member):
        """Start a 1v1 battle"""
        from .pvp_system import PvPBattleView, BattleMode
        
        participants = {'a': [player1], 'b': [player2]}
        battle_view = PvPBattleView(self.bot, participants, BattleMode.ONE_VS_ONE)
        
        # Track players in active battles
        self.active_battles.update({
            str(player1.id): battle_view,
            str(player2.id): battle_view
        })
        
        # Start the battle
        await battle_view.start_battle()
    
    async def start_team_battle(self, mode: str, team1: list, team2: list, team_names: dict = None):
        """Start a team battle"""
        from .pvp_system import PvPBattleView, BattleMode
        
        battle_mode = {
            "2v2": BattleMode.TEAM_2V2,
            "3v3": BattleMode.TEAM_3V3,
            "4v4": BattleMode.TEAM_4V4
        }.get(mode, BattleMode.TEAM_2V2)
        
        participants = {'a': team1, 'b': team2}
        
        # Use provided team names or generate defaults
        if team_names is None:
            # Load team names from JSON for fallback
            import json
            import random
            try:
                with open('Systems/Data/pets_level.json', 'r') as f:
                    pet_data = json.load(f)
                    team_name_list = pet_data.get('TEAM_NAMES', [])
                random.shuffle(team_name_list)
                team_names = {
                    'a': team_name_list[0] if team_name_list else "Team A",
                    'b': team_name_list[1] if len(team_name_list) > 1 else "Team B"
                }
            except:
                team_names = {'a': "Team A", 'b': "Team B"}
        
        battle_view = PvPBattleView(self.bot, participants, battle_mode, team_names)
        
        # Track players in active battles
        for player in team1 + team2:
            self.active_battles[str(player.id)] = battle_view
        
        # Start the battle
        await battle_view.start_battle()
    
    async def start_ffa_battle(self, players: list):
        """Start a free-for-all battle"""
        from .pvp_system import PvPBattleView, BattleMode
        
        battle_view = PvPBattleView(self.bot, players, BattleMode.FREE_FOR_ALL)
        
        # Track players in active battles
        for player in players:
            self.active_battles[str(player.id)] = battle_view
        
        # Start the battle
        await battle_view.start_battle()
    
async def setup(bot):
    """Setup function for battle commands with dependency handling"""
    try:
        # Wait for pet system to be available (with timeout)
        max_wait = 10  # seconds
        waited = 0
        while not hasattr(bot, 'pet_system') and waited < max_wait:
            await asyncio.sleep(0.5)
            waited += 0.5
            
        if not hasattr(bot, 'pet_system'):
            logger.error("Pet system not found after waiting! Make sure pets_system.py is loaded first.")
            return False
            
        # Add battle cogs
        await bot.add_cog(BattleCommands(bot))
        await bot.add_cog(PvPCog(bot))
        logger.info("BattleCommands and PvPCog loaded successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to load battle commands: {e}")
        raise