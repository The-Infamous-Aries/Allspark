import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from datetime import datetime, timedelta
import json
import os
from typing import Dict, Any, Optional, Tuple

from Systems.user_data_manager import UserDataManager
from Systems.EnergonPets.energon_system import (
    EnergonGameManager, WIN_CONDITION, SLOT_THEMES, DIFFICULTY_MULTIPLIERS,
    MarketManager, CryptoMarketView,
    BuyCoinModal, SellCoinModal, create_market_embed
)

# Game state management
active_games = {}  # channel_id -> set of player_ids
from Systems.EnergonPets.slots import SlotMachineView, PlayAgainView

user_data_manager = UserDataManager()

class EnergonCommands(commands.Cog):
    """Command handlers for Energon game functionality."""
    
    def __init__(self, game_manager: EnergonGameManager):
        self.game_manager = game_manager
        self.bot = game_manager.bot
    
    @staticmethod
    def has_cybertronian_role(member: discord.Member) -> bool:
        """Check if a member has any Cybertronian role."""
        from config import ROLE_IDS
        cybertronian_roles = [ROLE_IDS.get(role) for role in ['Autobot', 'Decepticon', 'Maverick', 'Cybertronian_Citizen']]
        return any(role.id in cybertronian_roles for role in member.roles)
    
    def create_game_info_embed(self) -> discord.Embed:
        """Create a rich embed with game information."""
        embed = discord.Embed(
            title="🚀 Transformers: Energon Rush",
            description="A new round has begun across all channels!",
            color=0x00ff00
        )
        embed.add_field(
            name="🎯 Objective",
            value=f"First Cybertronian to reach **{WIN_CONDITION} Energon** wins!",
            inline=False
        )
        embed.add_field(
            name="⚡ Commands",
            value="`/scout` - Low-risk Energon search\n`/search` - High-risk, high-reward search\n`/challenge <amount>` - Challenge other players\n`/energon_stats` - Check stats and leaderboards",
            inline=False
        )
        embed.add_field(
            name="🏆 Features",
            value="• Global cross-channel gameplay\n• Banking system for persistent Energon\n• Player vs Player challenges\n• Comprehensive statistics tracking",
            inline=False
        )
        embed.set_footer(text="Good luck, Cybertronians!")
        return embed
    
    
    
    @commands.hybrid_command(name='rush_info', description='Display information about Transformers: Energon Rush')
    async def rush_info(self, ctx: commands.Context) -> None:
        """Display information about Transformers: Energon Rush."""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can view Energon Rush info! Please get the 'Cybertronian Citizen' role first.")
            return
            
        embed = self.create_game_info_embed()
        embed.description = "Learn about the Energon Rush game!"
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='scout', description='Perform a low-risk scout for Energon')
    async def scout(self, ctx: commands.Context) -> None:
        """Perform a low-risk scout for Energon."""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can scout for Energon! Please get the 'Cybertronian Citizen' role first.")
            return

        try:
            player_id = str(ctx.author.id)
            energon_data = await user_data_manager.get_energon_data(player_id)
            
            # Check if there's an active game in this channel/server
            channel_id = str(ctx.channel.id)
            game_active = await self._is_game_active(channel_id)
            
            energon_gained = random.randint(50, 200)
            
            if game_active or energon_data.get('in_energon_rush', False):
                # Ensure player is added to the active game
                if not energon_data.get('in_energon_rush', False):
                    await self._add_player_to_game(channel_id, player_id)
                    energon_data['in_energon_rush'] = True
                    energon_data['energon'] = 0  # Start fresh
                    await ctx.send(f"🎮 Welcome to the Energon Rush! You've been added to the current game.")
                
                # Add energon to current game
                new_energon = energon_data['energon'] + energon_gained
                energon_data['energon'] = new_energon
                await user_data_manager.save_energon_data(player_id, energon_data)
                
                await ctx.send(f"You scout a ruined sector and find **{energon_gained} Energon**! Your Energon level is now **{new_energon}**.")
                
                # Check for win condition
                if new_energon >= WIN_CONDITION:
                    await ctx.send(f"🎉 **{ctx.author.display_name} has reached {WIN_CONDITION} Energon and wins the game!** 🎉")
                    await self._end_game(channel_id, ctx)
            else:
                # No active game - start a new one and add this player
                await self._start_new_game(channel_id, player_id)
                energon_data['in_energon_rush'] = True
                energon_data['energon'] = energon_gained
                await user_data_manager.save_energon_data(player_id, energon_data)
                
                await ctx.send(f"🎮 **New Energon Rush game started!**\n"
                               f"You scout a ruined sector and find **{energon_gained} Energon**! Your Energon level is now **{energon_gained}**.")
            
            # Update stats regardless of game state
            await user_data_manager.update_energon_stat(player_id, "total_energon_gained", energon_gained)

            if new_energon >= WIN_CONDITION:
                await ctx.send(f"🎉 **{ctx.author.display_name} has reached {WIN_CONDITION} Energon and wins the game!** 🎉\n"
                               "Type `/start_energon_rush` to play again.")
                
                # Award final energon to all players and track stats
                cybertronian_role = discord.utils.get(ctx.guild.roles, name="Cybertronian Citizen")
                if cybertronian_role:
                    for member in cybertronian_role.members:
                        pid = str(member.id)
                        other_data = await user_data_manager.get_energon_data(pid)
                        other_energon = other_data.get("energon", 0)
                        
                        # Bank the final energon amount for each player
                        await user_data_manager.update_energon_stat(pid, "energon_bank", other_energon)
                        
                        # Reset game flag and energon
                        other_data["in_energon_rush"] = False
                        other_data["energon"] = 0
                        await user_data_manager.save_energon_data(pid, other_data)
                        
                        # Track game results
                        if pid != player_id:
                            await user_data_manager.update_energon_stat(pid, "games_lost")
                        else:
                            await user_data_manager.update_energon_stat(pid, "games_won")
                
        except Exception as e:
            await ctx.send(f"❌ Error during scouting: {str(e)}")
            print(f"Error in scout: {e}")
    
    @commands.hybrid_command(name='search', description='Embark on a dangerous search for Energon')
    async def search(self, ctx: commands.Context) -> None:
        """Embark on a dangerous search for Energon."""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can search for Energon! Please get the 'Cybertronian Citizen' role first.")
            return

        try:
            player_id = str(ctx.author.id)
            energon_data = await user_data_manager.get_energon_data(player_id)
            
            # Check if there's an active game in this channel/server
            channel_id = str(ctx.channel.id)
            game_active = await self._is_game_active(channel_id)
            
            # Pet bonus calculation (for both game and non-game states)
            pet_bonus, has_pet = await self._calculate_pet_bonus(ctx.author.id)
            
            if game_active or energon_data.get('in_energon_rush', False):
                # Ensure player is added to the active game
                if not energon_data.get('in_energon_rush', False):
                    await self._add_player_to_game(channel_id, player_id)
                    energon_data['in_energon_rush'] = True
                    energon_data['energon'] = 0  # Start fresh
                    await ctx.send(f"🎮 Welcome to the Energon Rush! You've been added to the current game.")
                
                # In active game - process outcome normally
                current_energon = energon_data['energon']
                outcome_energon = await self._process_search_outcome(ctx, player_id, pet_bonus, has_pet, current_energon)
                
                if outcome_energon != 0:
                    new_energon = current_energon + outcome_energon
                    energon_data['energon'] = max(0, new_energon)
                    
                    if outcome_energon > 0:
                        await user_data_manager.update_energon_stat(player_id, "total_energon_gained", outcome_energon)
                    else:
                        await user_data_manager.update_energon_stat(player_id, "total_energon_lost", abs(outcome_energon))
                    
                    await user_data_manager.save_energon_data(player_id, energon_data)
                    
                    if new_energon >= WIN_CONDITION:
                        await ctx.send(f"🎉 **{ctx.author.display_name} has reached {WIN_CONDITION} Energon and wins the game!** 🎉")
                        await self._end_game(channel_id, ctx)
            else:
                # No active game - start a new one and add this player
                await self._start_new_game(channel_id, player_id)
                energon_data['in_energon_rush'] = True
                energon_data['energon'] = 0  # Start fresh
                
                # Simplified search with guaranteed find for new game
                base_find = random.randint(100, 300)
                total_find = base_find + pet_bonus
                
                energon_data['energon'] = total_find
                await user_data_manager.save_energon_data(player_id, energon_data)
                
                embed = discord.Embed(
                    title="🎯 Successful Search!",
                    description=f"🎮 **New Energon Rush game started!**\nYou search the Energon mines and find **{total_find} Energon**!",
                    color=discord.Color.green(),
                    timestamp=discord.utils.utcnow()
                )
                
                if pet_bonus > 0:
                    embed.add_field(name="🐾 Pet Bonus", value=f"**+{pet_bonus}** Energon from your companion", inline=True)
                
                embed.add_field(name="⚡ Current Energon", value=f"**{total_find}** in current game", inline=True)
                embed.set_footer(text="Game started! First to 10,000 Energon wins!", icon_url=ctx.guild.me.display_avatar.url)
                
                await ctx.send(embed=embed)
                
        except Exception as e:
            await ctx.send(f"❌ Error during search: {str(e)}")
            print(f"Error in search: {e}")
    
    async def _calculate_pet_bonus(self, player_id: int) -> tuple[int, bool]:
        """Calculate pet bonus for search operations."""
        player_str = str(player_id)
        pet_bonus = 0
        has_pet = False
        
        try:
            pet_data = await user_data_manager.get_pet_data(player_str)
            if pet_data:
                pet_level = pet_data.get('level', 1)
                pet_bonus = pet_level * 2  # 2% per level
                has_pet = True
        except Exception as e:
            print(f"Error calculating pet bonus: {e}")
        
        return pet_bonus, has_pet
    
    async def _process_search_outcome(self, ctx: commands.Context, player_id: str, pet_bonus: int, has_pet: bool, current_energon: int) -> int:
        """Process the search outcome and return the energon change."""
        # Pet participation tracking
        if has_pet:
            pet_data = await user_data_manager.get_pet_data(player_id)
            if pet_data:
                # Update pet stats using the new system
                searches_helped = pet_data.get('searches_helped', 0) + 1
                total_bonuses = pet_data.get('total_bonuses_given', 0) + pet_bonus
                
                # Update pet data
                pet_data['searches_helped'] = searches_helped
                pet_data['total_bonuses_given'] = total_bonuses
                
                search_xp = random.randint(5, 15)
                leveled_up, level_gains = await self.bot.pet_system.add_experience(ctx.author.id, search_xp, "search")
                
                # Save updated pet data
                await user_data_manager.save_pet_data(player_id, player_id, pet_data)

        # Calculate outcome probabilities
        base_chances = {
            'disaster': 5,
            'loss': 15,
            'nothing': 45,
            'small_find': 20,
            'major_find': 15
        }
        
        # Apply pet bonus
        adjusted_chances = {
            'disaster': max(0, base_chances['disaster'] - (pet_bonus * 0.2)),
            'loss': max(0, base_chances['loss'] - (pet_bonus * 0.3)),
            'nothing': max(0, base_chances['nothing'] - (pet_bonus * 0.5))
        }
        
        # Redistribute reduced chances
        reduced_bad = sum(base_chances[k] - adjusted_chances[k] for k in ['disaster', 'loss', 'nothing'])
        adjusted_chances['small_find'] = base_chances['small_find'] + (reduced_bad * 0.6)
        adjusted_chances['major_find'] = base_chances['major_find'] + (reduced_bad * 0.4)

        # Determine outcome
        random_chance = random.uniform(0, 100)
        outcome_energon = 0

        bonus_text = f" (Pet Bonus: +{pet_bonus}% better odds)" if pet_bonus > 0 else ""

        if random_chance < adjusted_chances['disaster']:
            outcome_energon = -current_energon
            
            disaster_messages = [
                f"💀 **CATASTROPHIC FAILURE!** You fell into a hidden trap and lost all your Energon!{bonus_text}",
                f"💀 **TOTAL DISASTER!** A cave-in buried all your equipment and Energon!{bonus_text}",
                f"💀 **COMPLETE LOSS!** You triggered an ancient security system that drained all your Energon!{bonus_text}",
                f"💀 **DEVASTATING ACCIDENT!** A toxic gas leak forced you to abandon everything!{bonus_text}",
                f"💀 **CRITICAL FAILURE!** You fell through unstable ground and lost all your Energon in the depths!{bonus_text}"
            ]
            message = random.choice(disaster_messages)
            
            if has_pet:
                pet_data = await user_data_manager.get_pet_data(player_id)
                if pet_data:
                    pet_maintenance_loss = random.randint(20, 40)
                    new_maintenance = max(0, pet_data.get('maintenance', 100) - pet_maintenance_loss)
                    pet_data['maintenance'] = new_maintenance
                    await user_data_manager.save_pet_data(player_id, player_id, pet_data)
                    message += f"\n🐾 Your pet {pet_data.get('name', 'Unknown')} was damaged in the disaster and lost {pet_maintenance_loss} maintenance!"
            
            await ctx.send(message)
            
        elif random_chance < adjusted_chances['disaster'] + adjusted_chances['loss']:
            loss_amount = min(current_energon, random.randint(1, 500))
            outcome_energon = -loss_amount
            
            loss_messages = [
                f"❌ You encountered dangerous terrain and lost **{loss_amount} Energon** in the process!{bonus_text}",
                f"❌ Unstable ground caused equipment damage, costing you **{loss_amount} Energon**!{bonus_text}",
                f"❌ A minor cave-in damaged your gear, losing **{loss_amount} Energon**!{bonus_text}",
                f"❌ Toxic fumes forced you to retreat, abandoning **{loss_amount} Energon** worth of equipment!{bonus_text}",
                f"❌ You got lost and had to use **{loss_amount} Energon** to power emergency beacons!{bonus_text}",
                f"❌ Equipment malfunction drained **{loss_amount} Energon** from your reserves!{bonus_text}"
            ]
            message = random.choice(loss_messages)
            
            if has_pet and random.randint(1, 100) <= 30:
                pet_data = await user_data_manager.get_pet_data(player_id)
                if pet_data:
                    pet_maintenance_loss = random.randint(5, 15)
                    new_maintenance = max(0, pet_data.get('maintenance', 100) - pet_maintenance_loss)
                    pet_data['maintenance'] = new_maintenance
                    await user_data_manager.save_pet_data(player_id, player_id, pet_data)
                    message += f"\n🐾 Your pet {pet_data.get('name', 'Unknown')} was damaged during the incident and lost {pet_maintenance_loss} maintenance!"
            
            await ctx.send(message)
            
        elif random_chance < adjusted_chances['disaster'] + adjusted_chances['loss'] + adjusted_chances['nothing']:
            nothing_messages = [
                f"🔍 You searched extensively but found nothing valuable in this area.{bonus_text}",
                f"🔍 After hours of searching, you came up empty-handed.{bonus_text}",
                f"🔍 The area showed promise but yielded no Energon deposits.{bonus_text}",
                f"🔍 Your scans detected false readings - no Energon here.{bonus_text}",
                f"🔍 You thoroughly explored the region but found only empty caverns.{bonus_text}",
                f"🔍 Despite careful investigation, this location was already stripped clean.{bonus_text}",
                f"🔍 Your search turned up interesting geology but no Energon.{bonus_text}",
                f"🔍 You found old mining equipment but no remaining Energon.{bonus_text}"
            ]
            await ctx.send(random.choice(nothing_messages))
            
        elif random_chance < adjusted_chances['disaster'] + adjusted_chances['loss'] + adjusted_chances['nothing'] + adjusted_chances['small_find']:
            outcome_energon = random.randint(1, 500)
            
            small_find_messages = [
                f"💎 Your thorough search paid off! You discovered **{outcome_energon} Energon**!{bonus_text}",
                f"💎 You found a small but pure Energon crystal worth **{outcome_energon} Energon**!{bonus_text}",
                f"💎 Hidden beneath rubble, you uncovered **{outcome_energon} Energon**!{bonus_text}",
                f"💎 Your persistence revealed a concealed cache of **{outcome_energon} Energon**!{bonus_text}",
                f"💎 A lucky break in the rock face exposed **{outcome_energon} Energon**!{bonus_text}",
                f"💎 You discovered remnants from an old mining operation: **{outcome_energon} Energon**!{bonus_text}",
                f"💎 Your advanced scanning detected a small vein yielding **{outcome_energon} Energon**!{bonus_text}"
            ]
            await ctx.send(random.choice(small_find_messages))
            
        else:  # Major find
            outcome_energon = random.randint(501, 1000)
            
            major_find_messages = [
                f"🏆 **INCREDIBLE DISCOVERY!** You found a massive Energon deposit worth **{outcome_energon} Energon**!{bonus_text}!",
                f"🏆 **LEGENDARY FIND!** An untouched Energon vein yielded **{outcome_energon} Energon**!{bonus_text}!",
                f"🏆 **AMAZING BREAKTHROUGH!** You discovered an ancient Energon storage chamber with **{outcome_energon} Energon**!{bonus_text}!",
                f"🏆 **SPECTACULAR SUCCESS!** A hidden geode contained **{outcome_energon} Energon** in pure form!{bonus_text}!",
                f"🏆 **EXTRAORDINARY DISCOVERY!** You struck a rich Energon seam worth **{outcome_energon} Energon**!{bonus_text}!",
                f"🏆 **PHENOMENAL FIND!** An underground river of liquid Energon provided **{outcome_energon} Energon**!{bonus_text}!"
            ]
            await ctx.send(random.choice(major_find_messages))
        
        return outcome_energon



    @commands.hybrid_command(name='slots', description='Play the Energon slot machine')
    @app_commands.choices(mode=[
        app_commands.Choice(name='Fun - No Risk', value='fun'),
        app_commands.Choice(name='Bet - Requires Energon', value='bet')
    ])
    @app_commands.choices(difficulty=[
        app_commands.Choice(name='Easy - Skills Theme - 1:80', value='easy'),
        app_commands.Choice(name='Medium - Characters Theme - 1:512', value='medium'),
        app_commands.Choice(name='Hard - Zodiac Theme - 1:1728', value='hard')
    ])
    async def slots_command(self, ctx: commands.Context, mode: str = "fun", 
                           difficulty: str = "easy", bet: int = 10) -> None:
        """Play Emoji Slots for Fun or Energon!"""
        try:
            if not self.has_cybertronian_role(ctx.author):
                await ctx.send("❌ Only Cybertronian Citizens can use the slot machine! Please get the 'Cybertronian Citizen' role first.")
                return
            
            if mode == "bet":
                # Use the new energon system for bets
                success, message = await self.game_manager.use_energon_for_bet_or_challenge(str(ctx.author.id), bet)
                if not success:
                    await ctx.send(f"❌ {message}")
                    return
                
                # Get updated energon data for display
                energon_data = await user_data_manager.get_energon_data(str(ctx.author.id))
                current_energon = energon_data.get('energon', 0)
            else:
                current_energon = 0
            
            await self.start_slot_game(ctx, mode, difficulty, bet, ctx.author, current_energon)
            
        except Exception as e:
            error_embed = discord.Embed(
                title="🎰 Slot Machine Error!",
                description="The Energon slot machine is temporarily out of order! Please try again later.",
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed, ephemeral=True)
    
    async def start_slot_game(self, ctx_or_interaction, mode: str, difficulty: str, bet: int, 
                            user: discord.Member, current_energon: int) -> None:
        """Start a new slot machine game."""
        slot_emojis = SLOT_THEMES[difficulty]
        multiplier = DIFFICULTY_MULTIPLIERS[difficulty]
        
        # Validate betting mode
        if mode == "bet":
            if bet < 10:
                error_embed = discord.Embed(
                    title="❌ Invalid Bet",
                    description="Minimum bet is **10 Energon**! Even small risks require some investment.",
                    color=discord.Color.red()
                )
                if hasattr(ctx_or_interaction, 'send'):
                    await ctx_or_interaction.send(embed=error_embed, ephemeral=True)
                else:
                    await ctx_or_interaction.response.send_message(embed=error_embed, ephemeral=True)
                return
                
            if bet > 1000:
                error_embed = discord.Embed(
                    title="❌ Bet Too High",
                    description="Maximum bet is **1000 Energon**! We're not running a high-roller casino here.",
                    color=discord.Color.red()
                )
                if hasattr(ctx_or_interaction, 'send'):
                    await ctx_or_interaction.send(embed=error_embed, ephemeral=True)
                else:
                    await ctx_or_interaction.response.send_message(embed=error_embed, ephemeral=True)
                return
        
        # Create initial game embed
        embed = discord.Embed(
            title=f"🎰 SLOT MACHINE - {difficulty.upper()} 🎰",
            color=discord.Color.gold() if mode == "bet" else discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        embed.set_author(
            name=f"{user.display_name} at the slot machine",
            icon_url=user.display_avatar.url
        )
        
        # Add game info
        embed.add_field(
            name="🎲 Difficulty",
            value=f"**{difficulty.title()}** ({len(slot_emojis)} symbols)",
            inline=True
        )

        if mode == "bet":
            embed.add_field(
                name="💰 Game Mode",
                value=f"**Betting Energon** ({multiplier}x payout)",
                inline=True
            )
            embed.add_field(
                name="⚡ Your Energon",
                value=f"**{current_energon}** Energon",
                inline=True
            )
            embed.add_field(
                name="💵 Bet Amount",
                value=f"**{bet}** Energon",
                inline=True
            )
        else:
            embed.add_field(
                name="🎮 Game Mode",
                value="**Just for Fun**",
                inline=True
            )
            embed.add_field(
                name="🎯 Stakes",
                value="**No Risk, No Reward**",
                inline=True
            )
        
        # Initial slot display
        embed.add_field(
            name="🎯 Slot Machine",
            value="```\n🎰 ❓ ❓ ❓ 🎰\n```",
            inline=False
        )
        
        embed.add_field(
            name="🎲 Ready to Play!",
            value="Click the **SPIN** button below to start the reels!",
            inline=False
        )
        
        embed.set_footer(
            text=f"🎰 Jackpot = All 3 identical symbols ({multiplier}x bet)! • Good luck!",
            icon_url=user.guild.me.display_avatar.url
        )
        
        # Create view with spin button
        view = SlotMachineView(self.bot, user, mode, difficulty, bet, current_energon, slot_emojis, multiplier)
        
        try:
            # Handle both interaction and context scenarios
            if hasattr(ctx_or_interaction, 'response') and ctx_or_interaction.response.is_done():
                # Interaction already responded, use followup
                message = await ctx_or_interaction.followup.send(embed=embed, view=view)
            elif hasattr(ctx_or_interaction, 'send'):
                # Context object
                message = await ctx_or_interaction.send(embed=embed, view=view)
            else:
                # Fresh interaction
                message = await ctx_or_interaction.response.send_message(embed=embed, view=view)
                
            view.message = message
        except discord.NotFound:
            # Fallback for expired webhooks
            if hasattr(ctx_or_interaction, 'channel'):
                message = await ctx_or_interaction.channel.send(embed=embed, view=view)
            else:
                message = await ctx_or_interaction.followup.send(embed=embed, view=view)
            view.message = message

    @commands.hybrid_command(name="cybercoin_market", description="View the CyberCoin market dashboard with live updates")
    async def cybercoin_market(self, ctx: commands.Context):
        """Display the CyberCoin market dashboard with auto-refreshing chart."""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can access the CyberCoin market!", ephemeral=True)
            return
        
        embed = create_market_embed()
        view = CryptoMarketView()
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @commands.hybrid_command(name="cybercoin_profile", description="View your personal CyberCoin portfolio and transaction history")
    async def cybercoin_profile(self, ctx: commands.Context):
        """Display your personal CyberCoin portfolio and transaction history."""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can access CyberCoin portfolios!", ephemeral=True)
            return
        
        portfolio = user_data_manager.get_cybercoin_portfolio(str(ctx.author.id))
        if not portfolio or portfolio["portfolio"]["total_coins"] <= 0:
            await ctx.send(embed=discord.Embed(
                title="📊 Your CyberCoin Portfolio",
                description="You don't own any CyberCoins yet! Use `/cybercoin_market` to start trading.",
                color=discord.Color.blue()
            ))
            return
        
        market_manager = MarketManager()
        current_price = market_manager.market_data["current_price"]
        portfolio_data = portfolio["portfolio"]
        
        total_coins = portfolio_data["total_coins"]
        total_invested = portfolio_data["total_invested"]
        total_value = total_coins * current_price
        profit_loss = total_value - total_invested
        roi = (profit_loss / max(total_invested, 1)) * 100
        
        embed = discord.Embed(
            title=f"📊 {ctx.author.display_name}'s CyberCoin Portfolio",
            color=discord.Color.green() if profit_loss >= 0 else discord.Color.red(),
            timestamp=discord.utils.utcnow()
        ).set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        
        embed.add_field(name="💰 Current Holdings", 
                       value=f"**{total_coins:.4f}** CyberCoins\n**{total_value:.2f}** Energon (@ {current_price:.2f}/coin)", 
                       inline=True)
        embed.add_field(name="💸 Investment Summary", 
                       value=f"**Total Invested:** {total_invested:.2f} Energon\n**Total Sold:** {portfolio_data['total_sold']:.4f} coins\n**Realized Profit:** {portfolio_data['total_profit']:+.2f} Energon", 
                       inline=True)
        embed.add_field(name="📈 Performance", 
                           value=f"**Unrealized P&L:** {profit_loss:+.2f} Energon\n**ROI:** {roi:+.1f}%\n**Current Price:** {current_price:.2f} Energon", 
                           inline=True)
        
        # Recent Transactions

    async def _is_game_active(self, channel_id):
        """Check if there's an active game in this channel."""
        return channel_id in active_games

    async def _start_new_game(self, channel_id, starter_player_id):
        """Start a new game in this channel."""
        active_games[channel_id] = {starter_player_id}

    async def _add_player_to_game(self, channel_id, player_id):
        """Add a player to the active game."""
        if channel_id in active_games:
            active_games[channel_id].add(player_id)

    async def _end_game(self, channel_id, ctx):
        """End the current game and bank energon for all players."""
        if channel_id not in active_games:
            return
            
        # Get all players in this game
        game_players = active_games[channel_id]
        winner = str(ctx.author.id)
        
        # Award final energon to all players and track stats
        cybertronian_role = discord.utils.get(ctx.guild.roles, name="Cybertronian Citizen")
        if cybertronian_role:
            for member in cybertronian_role.members:
                pid = str(member.id)
                other_data = await user_data_manager.get_energon_data(pid)
                
                if other_data.get('in_energon_rush', False):
                    other_energon = other_data.get("energon", 0)
                    
                    # Bank the final energon amount for each player
                    await user_data_manager.update_energon_stat(pid, "energon_bank", other_energon)
                    
                    # Reset game flag and energon
                    other_data["in_energon_rush"] = False
                    other_data["energon"] = 0
                    await user_data_manager.save_energon_data(pid, other_data)
                    
                    # Track game results
                    if pid != winner:
                        await user_data_manager.update_energon_stat(pid, "games_lost")
                    else:
                        await user_data_manager.update_energon_stat(pid, "games_won")
        
        # Remove the game from active games
        del active_games[channel_id]
        transactions = portfolio["transactions"]
        if transactions["purchases"] or transactions["sales"]:
            recent_tx = []
            all_tx = transactions["purchases"][-5:] + transactions["sales"][-5:]
            all_tx.sort(key=lambda x: x["timestamp"], reverse=True)
            
            for tx in all_tx[:5]:
                tx_type = "🟢 BUY" if tx["type"] == "purchase" else "🔴 SELL"
                tx_time = datetime.fromisoformat(tx["timestamp"]).strftime("%m/%d %H:%M")
                recent_tx.append(f"{tx_type} {tx['quantity']:.4f} @ {tx['price']:.2f} ({tx_time})")
            
            embed.add_field(name="📋 Recent Transactions", 
                           value="\n".join(recent_tx) if recent_tx else "No recent transactions", 
                           inline=False)
        
        embed.set_footer(text="Use /cybercoin_market to trade • Updated in real-time")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='energon_stats', description='Check your Energon game statistics and global leaderboards')
    async def energon_stats(self, ctx: commands.Context) -> None:
        """Display Energon game statistics and leaderboards."""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can view Energon statistics! Please get the 'Cybertronian Citizen' role first.")
            return

        player_id = str(ctx.author.id)
        stats = await self.game_manager.get_player_stats(player_id)
        
        total_games = stats['games_won'] + stats['games_lost']
        win_rate = (stats['games_won'] / max(1, total_games)) * 100
        
        embed = discord.Embed(
            title=f"⚡ {ctx.author.display_name}'s Energon Statistics",
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow()
        ).set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        
        embed.add_field(name="🏆 Game Statistics", 
                       value=f"**Games Won:** {stats['games_won']}\n**Games Lost:** {stats['games_lost']}", 
                       inline=True)
        embed.add_field(name="📊 Win Rate", value=f"**{win_rate:.1f}%**", inline=True)
        embed.add_field(name="💰 Energon Statistics", 
                       value=f"**Total Gained:** {stats['total_energon_gained']:,}\n**Total Lost:** {stats['total_energon_lost']:,}\n**Net:** {stats['total_energon_gained'] - stats['total_energon_lost']:,}", 
                       inline=True)
        embed.add_field(name="🏦 Bank & Challenges", 
                       value=f"**Energon Bank:** {stats['energon_bank']:,}\n**Challenges Won:** {stats['challenges_won']}\n**Challenges Lost:** {stats['challenges_lost']}", 
                       inline=True)
        embed.add_field(name="⚔️ Challenge Energon", 
                       value=f"**Won in Challenges:** {stats['challenge_energon_won']:,}\n**Lost in Challenges:** {stats['challenge_energon_lost']:,}", 
                       inline=True)
        
        # Global leaderboard
        leaderboard = await user_data_manager.get_energon_leaderboard_from_game_file()
        if leaderboard:
            medals = ["🥇", "🥈", "🥉"] + ["🔸"] * 7
            leaderboard_text = [
                f"{medals[i]} **{i+1}.** {entry['username']}: {entry['value']:,} {entry['type']}"
                for i, entry in enumerate(leaderboard[:10])
            ]
            
            embed.add_field(name="🌟 Global Leaderboard - Top 10", 
                           value="\n".join(leaderboard_text), 
                           inline=False)
        
        embed.set_footer(text="Energon Rush Statistics - Updated in real-time")
        await ctx.send(embed=embed)
        
async def setup(bot):
    """Setup function to add the EnergonCommands cog to the bot."""
    game_manager = EnergonGameManager(bot)
    await bot.add_cog(EnergonCommands(game_manager))