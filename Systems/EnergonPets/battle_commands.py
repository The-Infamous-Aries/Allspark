import discord
from discord.ext import commands
import asyncio
import logging
from typing import Optional

# Import the optimized battle system
from Systems.EnergonPets.battle_system import (
    BattleInfoView,
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

    @commands.hybrid_command(name="battle_info", description="Show comprehensive battle information and rules")
    async def battle_info(self, ctx):
        """Show comprehensive battle information and rules"""
        try:
            view = BattleInfoView(ctx)
            embed = view.get_battle_info_embed()
            view.message = await ctx.send(embed=embed, view=view)
        except Exception as e:
            logger.error(f"Error in battle_info: {e}")
            await ctx.send("❌ Error displaying battle information.")

    @commands.hybrid_command(name="battle", description="Start a solo battle against a monster")
    async def battle(self, ctx):
        """Start a solo battle with interactive enemy selection"""
        try:
            from Systems.EnergonPets.enemy_selection_view import EnemySelectionView
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
            from Systems.EnergonPets.enemy_selection_view import EnemySelectionView
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

    @commands.hybrid_command(name="pvp", description="Challenge another player to PvP battle")
    @discord.app_commands.describe(
        target="The Discord member you want to challenge"
    )
    async def pvp(self, ctx, target: discord.Member):
        """Challenge another player to PvP battle"""
        try:
            if target.id == ctx.author.id:
                await ctx.send("❌ You can't challenge yourself!")
                return
                
            # Create PvP battle
            battle = await battle_system.create_battle(
                ctx, 
                "pvp", 
                target_user=target
            )
            
            # Use GroupBattleJoinView for PvP battles with 2 fixed participants
            from Systems.EnergonPets.battle_system import GroupBattleJoinView
            join_view = GroupBattleJoinView(ctx, battle)
            
            # Pre-add the challenger and target
            await join_view.add_participant(ctx.author)
            await join_view.add_participant(target)
            
            embed = battle.build_join_embed()
            join_view.message = await ctx.send(embed=embed, view=join_view)
            
        except Exception as e:
            logger.error(f"Error in pvp command: {e}")
            await ctx.send("❌ Error starting PvP battle. Please try again.")

    @commands.hybrid_command(name="energon_challenge", description="Start an energon challenge with a bet")
    @discord.app_commands.describe(
        amount="Amount of energon to bet"
    )
    async def energon_challenge(self, ctx, amount: int):
        """Start an energon challenge with a bet"""
        try:
            if amount <= 0:
                await ctx.send("❌ Bet amount must be positive!")
                return
                
            # Check if user has a pet
            pet = await user_data_manager.get_pet_data(str(ctx.author.id))
            if not pet:
                await ctx.send("❌ You need a pet to start an energon challenge!")
                return

            from Systems.EnergonPets.battle_system import EnergonChallengeJoinView
            join_view = EnergonChallengeJoinView(ctx, amount)
            
            embed = join_view.build_join_embed()
            join_view.message = await ctx.send(embed=embed, view=join_view)
            
            # Update participants list with loaded pet data
            await join_view.update_participants_list()
            
        except Exception as e:
            logger.error(f"Error in energon_challenge command: {e}")
            await ctx.send("❌ Error starting energon challenge. Please try again.")

    @commands.hybrid_command(name="battle_stats", description="Show battle statistics for a user")
    @discord.app_commands.describe(
        member="The Discord member to check stats for (defaults to you)"
    )
    async def battle_stats(self, ctx, member: discord.Member = None):
        """Show battle statistics for a user"""
        try:
            target = member or ctx.author
            
            # Get pet data
            pet = await user_data_manager.get_pet_data(str(target.id))
            if not pet:
                await ctx.send("❌ No pet found for this user.")
                return
            
            battles_won = pet.get('battles_won', 0)
            battles_lost = pet.get('battles_lost', 0)
            total_battles = battles_won + battles_lost
            
            embed = discord.Embed(
                title=f"⚔️ Battle Stats - {target.display_name}",
                color=0x0099ff
            )
            
            embed.add_field(
                name="📊 Overall Stats",
                value=f"**Battles Won:** {battles_won}\n"
                      f"**Battles Lost:** {battles_lost}\n"
                      f"**Total Battles:** {total_battles}\n"
                      f"**Win Rate:** {(battles_won/total_battles*100):.1f}%" if total_battles > 0 else "**Win Rate:** N/A",
                inline=False
            )
            
            embed.add_field(
                name="🎯 Pet Info",
                value=f"**Name:** {pet.get('name', 'Unknown')}\n"
                      f"**Level:** {pet.get('level', 1)}\n"
                      f"**Experience:** {pet.get('experience', 0)}",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in battle_stats: {e}")
            await ctx.send("❌ Error retrieving battle statistics.")

    @commands.hybrid_command(name="group_pvp", description="Start a group PvP battle for up to 4 players")
    async def group_pvp(self, ctx):
        """Start a group PvP battle for up to 4 players"""
        try:
            # Create group PvP battle
            battle = await battle_system.create_battle(
                ctx, 
                "group_pvp"
            )
            
            # Use GroupBattleJoinView for group PvP battles
            from Systems.EnergonPets.battle_system import GroupBattleJoinView
            join_view = GroupBattleJoinView(ctx, battle)
            
            embed = battle.build_join_embed()
            join_view.message = await ctx.send(embed=embed, view=join_view)
            
        except Exception as e:
            logger.error(f"Error in group_pvp command: {e}")
            await ctx.send("❌ Error starting group PvP battle. Please try again.")

async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(BattleCommands(bot))
    logger.info("BattleCommands cog loaded successfully")