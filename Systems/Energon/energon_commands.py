import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from datetime import datetime

from Systems.Energon.energon_system import EnergonGameManager, WIN_CONDITION, SLOT_THEMES, DIFFICULTY_MULTIPLIERS, SlotMachineView, PlayAgainView, MarketManager, CryptoMarketView, BuyCoinModal, SellCoinModal, create_market_embed

# Import user_data_manager for leaderboard functionality
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from user_data_manager import user_data_manager

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
    
    @commands.hybrid_command(name='start_energon_rush', description='Start a new round of Transformers: Energon Rush')
    @commands.has_permissions(administrator=True)
    async def start_energon_rush(self, ctx: commands.Context) -> None:
        """Start the Energon Rush game (Admin only)."""
        try:
            # Initialize all players with starting Energon
            cybertronian_role = None
            for role in ctx.guild.roles:
                if role.name == "Cybertronian Citizen":
                    cybertronian_role = role
                    break
            
            if cybertronian_role:
                members = cybertronian_role.members
                for member in members:
                    energon_data = await user_data_manager.get_energon_data(str(member.id))
                    energon_data['energon'] = 1000  # Starting amount
                    await user_data_manager.save_energon_data(str(member.id), member.display_name, energon_data)
            
            embed = discord.Embed(
                title="⚡ ENERGON RUSH ACTIVATED! ⚡",
                description="The Energon Rush has begun! All Cybertronian Citizens can now:",
                color=discord.Color.gold(),
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(
                name="🔍 Available Commands",
                value="`/scout` - Search for Energon deposits\n"
                      "`/search` - Deep exploration for larger finds\n"
                      "`/slots` - Try your luck at the slot machine\n"
                      "`/cybercoin_market` - Trade CyberCoin cryptocurrency",
                inline=False
            )
            
            embed.add_field(
                name="🎯 Game Rules",
                value="• Each player starts with 1000 Energon\n"
                      "• Find more Energon through exploration\n"
                      "• Use Energon to buy CyberCoins\n"
                      "• Compete for the leaderboard!",
                inline=False
            )
            
            embed.set_footer(
                text="Energon Rush Game Started",
                icon_url=ctx.guild.me.display_avatar.url
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"Error starting Energon Rush: {str(e)}")
    
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
            
        # Check if user has Energon data (indicates game is active)
        from Systems.user_data_manager import UserDataManager
        user_data_manager = UserDataManager()
        energon_data = await user_data_manager.get_energon_data(str(ctx.author.id), ctx.author.display_name)
        
        if energon_data.get('energon', 0) == 0:
            await ctx.send("The game hasn't started yet! Type `/start_energon_rush` to begin.")
            return

        player_id = str(ctx.author.id)
        username = str(ctx.author.display_name)
        
        # Get current energon from user_data_manager
        energon_data = await user_data_manager.get_energon_data(player_id)
        current_energon = energon_data.get("energon", 0)

        energon_gained = random.randint(50, 200)
        new_energon = current_energon + energon_gained
        
        # Update energon in user_data_manager
        energon_data["energon"] = new_energon
        await user_data_manager.save_energon_data(player_id, username, energon_data)
        
        # Update stats
        await user_data_manager.update_energon_stat(player_id, username, "total_energon_gained", energon_gained)

        await ctx.send(f"You scout a ruined sector and find **{energon_gained} Energon**! Your Energon level is now **{new_energon}**.")

        if new_energon >= WIN_CONDITION:
            await ctx.send(f"🎉 **{ctx.author.display_name} has reached {WIN_CONDITION} Energon and wins the game!** 🎉\n"
                           "Type `/start_energon_rush` to play again.")
            
            # Award final energon to all players and track stats
            from Systems.user_data_manager import UserDataManager
            user_data_manager = UserDataManager()
            
            # Get all Cybertronian Citizens
            cybertronian_role = None
            for role in ctx.guild.roles:
                if role.name == "Cybertronian Citizen":
                    cybertronian_role = role
                    break
            
            if cybertronian_role:
                members = cybertronian_role.members
                for member in members:
                    pid = str(member.id)
                    if pid != player_id:
                        # Get other players' energon
                        other_data = await user_data_manager.get_energon_data(pid)
                        other_energon = other_data.get("energon", 0)
                        await user_data_manager.update_energon_stat(pid, member.display_name, "energon_bank", other_energon)
                        await user_data_manager.update_energon_stat(pid, member.display_name, "games_lost")
            
            # Award winner
            await user_data_manager.update_energon_stat(player_id, username, "games_won")
    
    @commands.hybrid_command(name='search', description='Embark on a dangerous search for Energon')
    async def search(self, ctx: commands.Context) -> None:
        """Embark on a dangerous search for Energon."""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can search for Energon! Please get the 'Cybertronian Citizen' role first.")
            return
            
        # Check if user has Energon data (indicates game is active)
        from Systems.user_data_manager import UserDataManager
        user_data_manager = UserDataManager()
        energon_data = await user_data_manager.get_energon_data(str(ctx.author.id), ctx.author.display_name)
        
        if energon_data.get('energon', 0) == 0:
            await ctx.send("The game hasn't started yet! Type `/start_energon_rush` to begin.")
            return

        player_id = str(ctx.author.id)
        username = str(ctx.author.display_name)
        
        # Get current energon from user_data_manager
        energon_data = await user_data_manager.get_energon_data(player_id)
        current_energon = energon_data.get("energon", 0)

        pet_bonus, has_pet = self._calculate_pet_bonus(ctx.author.id)
        outcome_energon = await self._process_search_outcome(ctx, player_id, pet_bonus, has_pet, current_energon)
        
        # Update energon in user_data_manager
        new_energon = max(0, current_energon + outcome_energon)
        energon_data["energon"] = new_energon
        await user_data_manager.save_energon_data(player_id, username, energon_data)
        
        # Update player stats based on outcome
        if outcome_energon > 0:
            await user_data_manager.update_energon_stat(player_id, username, "total_energon_gained", outcome_energon)
        elif outcome_energon < 0:
            await user_data_manager.update_energon_stat(player_id, username, "total_energon_lost", abs(outcome_energon))
    
    def _calculate_pet_bonus(self, player_id: int) -> tuple[int, bool]:
        """Calculate pet bonus for search operations."""
        player_str = str(player_id)
        pet_bonus = 0
        has_pet = False
        
        if hasattr(self.bot, 'pet_system') and hasattr(self.bot, 'pet_data'):
            if not self.bot.pet_data:
                self.bot.pet_system.load_pet_data()
            
            if player_str in self.bot.pet_data:
                pet_level = self.bot.pet_data[player_str]['level']
                pet_bonus = pet_level * 2  # 2% per level
                has_pet = True
                
                # Ensure pet has required stats
                for stat in ['maintenance', 'att', 'def']:
                    if stat not in self.bot.pet_data[player_str]:
                        self.bot.pet_data[player_str][stat] = 100 if stat == 'maintenance' else 1
        
        return pet_bonus, has_pet
    
    async def _process_search_outcome(self, ctx: commands.Context, player_id: str, pet_bonus: int, has_pet: bool, current_energon: int) -> int:
        """Process the search outcome and return the energon change."""
        # Pet participation tracking
        if has_pet:
            pet_data = self.bot.pet_data[player_id]
            for field in ['searches_helped', 'search_xp_earned', 'total_bonuses_given', 'last_interaction']:
                if field not in pet_data:
                    pet_data[field] = 0 if field != 'last_interaction' else datetime.now().isoformat()
            
            pet_data['searches_helped'] += 1
            pet_data['total_bonuses_given'] += pet_bonus
            pet_data['last_interaction'] = datetime.now().isoformat()
            
            search_xp = random.randint(5, 15)
            leveled_up, level_gains = self.bot.pet_system.add_experience(ctx.author.id, search_xp, "search")
            pet_data['search_xp_earned'] += search_xp
            
            if leveled_up and hasattr(self.bot.pet_system, 'send_level_up_embed'):
                asyncio.create_task(self.bot.pet_system.send_level_up_embed(ctx.author.id, level_gains, ctx.channel))

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
                pet_maintenance_loss = random.randint(20, 40)
                self.bot.pet_data[player_id]['maintenance'] = max(0, self.bot.pet_data[player_id]['maintenance'] - pet_maintenance_loss)
                message += f"\n🐾 Your pet {self.bot.pet_data[player_id]['name']} was damaged in the disaster and lost {pet_maintenance_loss} maintenance!"
            
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
                pet_maintenance_loss = random.randint(5, 15)
                self.bot.pet_data[player_id]['maintenance'] = max(0, self.bot.pet_data[player_id]['maintenance'] - pet_maintenance_loss)
                message += f"\n🐾 Your pet {self.bot.pet_data[player_id]['name']} was damaged during the incident and lost {pet_maintenance_loss} maintenance!"
            
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



    @commands.hybrid_command(name='slots', description='Play Emoji Slots for Fun or Energon!')
    @app_commands.choices(mode=[
        app_commands.Choice(name='Fun - Energon Not Required', value='fun'),
        app_commands.Choice(name='Bet - Requires Energon', value='bet')
    ])
    @app_commands.choices(difficulty=[
        app_commands.Choice(name='Easy - Skills Theme - 1:64', value='easy'),
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
                # Check if user has Energon data (indicates game is active)
                from Systems.user_data_manager import UserDataManager
                user_data_manager = UserDataManager()
                energon_data = await user_data_manager.get_energon_data(str(ctx.author.id), ctx.author.display_name)
                
                if energon_data.get('energon', 0) == 0:
                    await ctx.send("The Energon Rush game hasn't started yet! Type `/start_energon_rush` to begin.")
                    return
            
            current_energon = 0
            if mode == "bet":
                from Systems.user_data_manager import UserDataManager
                user_data_manager = UserDataManager()
                energon_data = await user_data_manager.get_energon_data(str(ctx.author.id), ctx.author.display_name)
                current_energon = energon_data.get('energon', 0)
            
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
        view = SlotMachineView(user, mode, difficulty, bet, current_energon, slot_emojis, multiplier)
        
        if hasattr(ctx_or_interaction, 'send'):
            message = await ctx_or_interaction.send(embed=embed, view=view)
        else:
            message = await ctx_or_interaction.followup.send(embed=embed, view=view)
        
        view.message = message

    @commands.hybrid_command(name="cybercoin_market", description="View the CyberCoin market dashboard with live updates")
    async def cybercoin_market(self, ctx: commands.Context):
        """Display the CyberCoin market dashboard with auto-refreshing chart."""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can access the CyberCoin market!", ephemeral=True)
            return
        
        # Show dashboard with auto-refresh
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
        
        player_id = str(ctx.author.id)
        market_manager = MarketManager()
        
        portfolio = user_data_manager.get_cybercoin_portfolio(player_id)
        if not portfolio or portfolio["portfolio"]["total_coins"] <= 0:
            embed = discord.Embed(
                title="📊 Your CyberCoin Portfolio",
                description="You don't own any CyberCoins yet! Use `/cybercoin_market` to start trading.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return
        
        current_price = market_manager.market_data["current_price"]
        
        portfolio_data = portfolio["portfolio"]
        total_coins = portfolio_data["total_coins"]
        total_invested = portfolio_data["total_invested"]
        total_value = total_coins * current_price
        profit_loss = total_value - total_invested
        
        embed = discord.Embed(
            title=f"📊 {ctx.author.display_name}'s CyberCoin Portfolio",
            color=discord.Color.green() if profit_loss >= 0 else discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        
        # Current Holdings Section
        embed.add_field(
            name="💰 Current Holdings",
            value=f"**{total_coins:.4f}** CyberCoins\n"
                  f"**{total_value:.2f}** Energon (@ {current_price:.2f}/coin)",
            inline=True
        )
        
        # Investment Summary Section
        embed.add_field(
            name="💸 Investment Summary",
            value=f"**Total Invested:** {total_invested:.2f} Energon\n"
                  f"**Total Sold:** {portfolio_data['total_sold']:.4f} coins\n"
                  f"**Realized Profit:** {portfolio_data['total_profit']:+.2f} Energon",
            inline=True
        )
        
        # Performance Section
        roi = (profit_loss / max(total_invested, 1)) * 100
        embed.add_field(
            name="📈 Performance",
            value=f"**Unrealized P&L:** {profit_loss:+.2f} Energon\n"
                  f"**ROI:** {roi:+.1f}%\n"
                  f"**Current Price:** {current_price:.2f} Energon",
            inline=True
        )
        
        # Recent Transactions
        transactions = portfolio["transactions"]
        if transactions["purchases"] or transactions["sales"]:
            recent_tx = []
            all_tx = transactions["purchases"][-5:] + transactions["sales"][-5:]
            all_tx.sort(key=lambda x: x["timestamp"], reverse=True)
            
            for tx in all_tx[:5]:
                tx_type = "🟢 BUY" if tx["type"] == "purchase" else "🔴 SELL"
                tx_time = datetime.fromisoformat(tx["timestamp"]).strftime("%m/%d %H:%M")
                recent_tx.append(
                    f"{tx_type} {tx['quantity']:.4f} @ {tx['price']:.2f} ({tx_time})"
                )
            
            embed.add_field(
                name="📋 Recent Transactions",
                value="\n".join(recent_tx) if recent_tx else "No recent transactions",
                inline=False
            )
        
        embed.set_footer(text="Use /cybercoin_market to trade • Updated in real-time")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='energon_stats', description='Check your Energon game statistics and global leaderboards')
    async def energon_stats(self, ctx: commands.Context) -> None:
        """Display Energon game statistics and leaderboards."""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can view Energon statistics! Please get the 'Cybertronian Citizen' role first.")
            return

        player_id = str(ctx.author.id)
        stats = self.game_manager.get_player_stats(player_id)
        
        # Create personal stats embed
        embed = discord.Embed(
            title=f"⚡ {ctx.author.display_name}'s Energon Statistics",
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow()
        )
        
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        
        # Personal stats
        total_games = stats['games_won'] + stats['games_lost']
        win_rate = (stats['games_won'] / max(1, total_games)) * 100
        
        embed.add_field(
            name="🏆 Game Statistics",
            value=f"**Games Won:** {stats['games_won']}\n**Games Lost:** {stats['games_lost']}",
            inline=True
        )
        embed.add_field(
            name="📊 Win Rate",
            value=f"**{win_rate:.1f}%**",
            inline=True
        )
        
        embed.add_field(
            name="💰 Energon Statistics",
            value=f"**Total Gained:** {stats['total_energon_gained']:,}\n**Total Lost:** {stats['total_energon_lost']:,}\n**Net:** {stats['total_energon_gained'] - stats['total_energon_lost']:,}",
            inline=True
        )
        
        embed.add_field(
            name="🏦 Bank & Challenges",
            value=f"**Energon Bank:** {stats['energon_bank']:,}\n**Challenges Won:** {stats['challenges_won']}\n**Challenges Lost:** {stats['challenges_lost']}",
            inline=True
        )
        
        embed.add_field(
            name="⚔️ Challenge Energon",
            value=f"**Won in Challenges:** {stats['challenge_energon_won']:,}\n**Lost in Challenges:** {stats['challenge_energon_lost']:,}",
            inline=True
        )
        
        # Global leaderboard
        leaderboard = await user_data_manager.get_energon_leaderboard_from_game_file()
        if leaderboard:
            leaderboard_text = []
            for i, entry in enumerate(leaderboard[:10]):
                medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "🔸"
                leaderboard_text.append(
                    f"{medal} **{i+1}.** {entry['username']}: {entry['value']:,} {entry['type']}"
                )
            
            embed.add_field(
                name="🌟 Global Leaderboard - Top 10",
                value="\n".join(leaderboard_text),
                inline=False
            )
        
        embed.set_footer(text="Energon Rush Statistics - Updated in real-time")
        await ctx.send(embed=embed)
        
async def setup(bot):
    """Setup function to add the EnergonCommands cog to the bot."""
    game_manager = EnergonGameManager(bot)
    await bot.add_cog(EnergonCommands(game_manager))