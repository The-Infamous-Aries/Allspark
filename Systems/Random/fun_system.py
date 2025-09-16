import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
import time
import logging
from pathlib import Path
from config import ROLE_IDS

logger = logging.getLogger("allspark.hg_sorting")

class ShootingRange(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_ready(self):
        """Initialize story map manager when bot is ready"""
        from .walktru import StoryMapManager
        
        # Initialize story map manager on the bot instance
        if not hasattr(self.bot, 'story_map_manager'):
            self.bot.story_map_manager = StoryMapManager(self.bot)
        
        self.active_games = {}  # Track active games per user
        
    async def update_shooting_stats(self, user_id, hits, total_shots, rounds):
        """Update shooting statistics for a user using UserDataManager"""
        try:
            from Systems.user_data_manager import user_data_manager
            user = self.bot.get_user(user_id)
            username = user.name if user else str(user_id)
            
            updated_stats = await user_data_manager.update_shooting_range_stats(
                str(user_id), username, hits, total_shots, rounds
            )
            return updated_stats
        except Exception as e:
            print(f"Error updating shooting stats: {e}")
            return {}
    
    def has_cybertronian_role(self, member):
        """Check if a member has any Cybertronian role."""
        cybertronian_roles = [ROLE_IDS.get(role) for role in ['Autobot', 'Decepticon', 'Maverick', 'Cybertronian_Citizen']]
        return any(role.id in cybertronian_roles for role in member.roles)
    
    @commands.hybrid_command(name='range', description='Start a shooting range session')
    async def shooting_range(self, ctx, rounds: int = 10):
        """
        Start a shooting range session!
        Usage: /range [rounds]
        Available rounds: 5, 15, 25, 50, 100
        """
        # Check if user has Cybertronian role
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can access the training range! Please get a Cybertronian role first.")
            return
            
        # Validate rounds
        valid_rounds = [5, 15, 25, 50, 100]
        if rounds not in valid_rounds:
            embed = discord.Embed(
                title="🎯 Autobot Training Range - Invalid Selection",
                description=f"Please select from available rounds: {', '.join(map(str, valid_rounds))}",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
            
        # Check if user already has an active game
        if ctx.author.id in self.active_games:
            embed = discord.Embed(
                title="🎯 Training Already in Progress",
                description="You already have an active shooting range session!",
                color=0xff9900
            )
            await ctx.send(embed=embed)
            return
            
        # Mark user as having an active game
        self.active_games[ctx.author.id] = True
        
        try:
            await self._run_shooting_range(ctx, rounds)
        finally:
            # Clean up active game tracking
            if ctx.author.id in self.active_games:
                del self.active_games[ctx.author.id]

    @shooting_range.autocomplete('rounds')
    async def rounds_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete for rounds parameter"""
        valid_rounds = [5, 15, 25, 50, 100]
        choices = []
        
        for rounds in valid_rounds:
            rounds_str = str(rounds)
            if current.lower() in rounds_str.lower():
                choices.append(discord.app_commands.Choice(name=f"{rounds} rounds", value=rounds))
        
        return choices[:25]   

    @shooting_range.error
    async def shooting_range_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                title="🎯 Invalid Input",
                description="Please enter a valid number of rounds (5, 15, 25, 50, or 100)",
                color=0xff0000
            )
            await ctx.send(embed=embed)
        else:
            # Clean up active game on error
            if ctx.author.id in self.active_games:
                del self.active_games[ctx.author.id]
            raise error

    async def _run_shooting_range(self, ctx, rounds):
        hits = 0
        total_shots = 0
        
        # Initial setup message
        setup_embed = discord.Embed(
            title="🔫🤖 Transformer Training Initializing...",
            description=f"**Transformer:** {ctx.author.mention}\n**Mission:** {rounds} rounds of target practice\n**Objective:** Click the 🎯 target button!",
            color=0x0099ff
        )
        setup_embed.add_field(
            name="📋 Instructions", 
            value="• Target will appear for 1 second\n• Click quickly on the correct button\n• Miss buttons: 🔴 (red circles)\n• Hit button: 🎯 (target)\n• This is great practice for Beige Sniping!", 
            inline=False
        )
        setup_msg = await ctx.send(embed=setup_embed)
        
        # Let the setup message stay visible for 5 seconds
        await asyncio.sleep(8)
        
        # Countdown
        for i in range(3, 0, -1):
            countdown_embed = discord.Embed(
                title=f"🎯 Starting in {i}...",
                description="Get ready to shoot!",
                color=0xff9900
            )
            await setup_msg.edit(embed=countdown_embed)
            await asyncio.sleep(1)
        
        # Delete setup message
        await setup_msg.delete()
        
        for round_num in range(1, rounds + 1):
            # Randomly select target position (0-4)
            target_position = random.randint(0, 4)
            
            # Create and send target message with buttons
            target_embed = discord.Embed(
                title=f"🎯 Round {round_num}/{rounds}",
                description="**FIRE!** Click the target button!",
                color=0x00ff00
            )
            
            # Create view with buttons
            view = ShootingView(target_position, ctx.author.id)
            target_msg = await ctx.send(embed=target_embed, view=view)
            
            # Wait for user interaction or timeout (2 seconds to match view timeout)
            await asyncio.sleep(1.0)
            
            # Check if user clicked and if it was a hit
            if view.user_clicked and view.hit:
                hits += 1
            
            total_shots += 1
            
            # Brief pause before next round
            await asyncio.sleep(0.5)
            
            # Delete the target message
            try:
                await target_msg.delete()
            except discord.NotFound:
                pass
        
        accuracy = (hits / total_shots * 100) if total_shots > 0 else 0
        
        # Update stats
        updated_stats = await self.update_shooting_stats(ctx.author.id, hits, total_shots, rounds)
        
        await self._display_results(ctx, hits, total_shots, accuracy, rounds, updated_stats)
    
    async def _display_results(self, ctx, hits, total_shots, accuracy, rounds, user_stats):
        # Determine rank based on accuracy
        if accuracy == 100:
            rank = "💯 **MATRIX BEARER**"
            rank_color = 0xff6b35  # Bright orange
            rank_desc = "Legendary precision! You wield the power of the Matrix!"
        elif accuracy >= 95:
            rank = "🌟 **SPARK GUARDIAN**"
            rank_color = 0x00ffff  # Cyan
            rank_desc = "Divine accuracy! Your spark burns brightest!"
        elif accuracy >= 90:
            rank = "🏆 **PRIME COMMANDER**"
            rank_color = 0xffd700  # Gold
            rank_desc = "Exceptional marksmanship! Optimus Prime would be proud!"
        elif accuracy >= 85:
            rank = "💎 **CRYSTAL SNIPER**"
            rank_color = 0x9932cc  # Dark orchid
            rank_desc = "Crystalline precision! Your aim is flawless!"
        elif accuracy >= 80:
            rank = "🔥 **INFERNO MARKSMAN**"
            rank_color = 0xff4500  # Orange red
            rank_desc = "Blazing accuracy! You're on fire!"
        elif accuracy >= 75:
            rank = "⭐ **ELITE WARRIOR**"
            rank_color = 0xc0c0c0  # Silver
            rank_desc = "Outstanding performance! You're ready for battle!"
        elif accuracy >= 60:
            rank = "🎖️ **SKILLED SOLDIER**"
            rank_color = 0xcd7f32  # Bronze
            rank_desc = "Good shooting! Keep training to improve!"
        elif accuracy >= 50:
            rank = "🔧 **TRAINEE**"
            rank_color = 0x808080  # Gray
            rank_desc = "Not bad for a rookie. More practice needed!"
        else:
            rank = "⚙️ **RECRUIT**"
            rank_color = 0x8b4513  # Brown
            rank_desc = "Back to basic training! Even Bumblebee shoots better!"
        
        # Check if this is a new personal best
        rounds_key = str(rounds)
        is_new_best = False
        if rounds_key in user_stats['best_records']:
            best_record = user_stats['best_records'][rounds_key]
            if accuracy == best_record['accuracy'] and hits == best_record['hits']:
                is_new_best = True
        
        # Create results embed
        results_embed = discord.Embed(
            title="🎯 Training Range Results" + (" 🆕 NEW PERSONAL BEST!" if is_new_best else ""),
            color=rank_color
        )
        
        results_embed.add_field(
            name="📊 Performance Stats",
            value=f"**Hits:** {hits}/{total_shots}\n**Accuracy:** {accuracy:.1f}%\n**Rounds Completed:** {rounds}",
            inline=True
        )
        
        results_embed.add_field(
            name="🏅 Rank Achieved",
            value=f"{rank}\n*{rank_desc}*",
            inline=True
        )
        
        # Show personal best for this round count
        if rounds_key in user_stats['best_records']:
            best_record = user_stats['best_records'][rounds_key]
            results_embed.add_field(
                name=f"🏆 Personal Best ({rounds} rounds)",
                value=f"**Accuracy:** {best_record['accuracy']:.1f}%\n**Hits:** {best_record['hits']}/{rounds}",
                inline=True
            )
        
        # Add accuracy bar
        bar_length = 20
        filled_length = int(bar_length * accuracy // 100)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        results_embed.add_field(
            name="📈 Accuracy Meter",
            value=f"`{bar}` {accuracy:.1f}%",
            inline=False
        )
        
        # Add overall stats
        overall_accuracy = (user_stats['total_hits'] / user_stats['total_shots'] * 100) if user_stats['total_shots'] > 0 else 0
        results_embed.add_field(
            name="📈 Overall Stats",
            value=f"**Sessions:** {user_stats['sessions_played']}\n**Total Hits:** {user_stats['total_hits']}/{user_stats['total_shots']}\n**Overall Accuracy:** {overall_accuracy:.1f}%",
            inline=False
        )
        
        results_embed.set_footer(text=f"{rank} | {ctx.author.display_name} | Use /range [rounds] to play again!")
        
        await ctx.send(embed=results_embed)
    
    async def get_leaderboard_ranking(self, user_id, rounds, stat_type='accuracy'):
        """Get user's ranking in leaderboard for specific round count"""
        # This would need to be implemented using UserDataManager's leaderboard functionality
        # For now, return None as UserDataManager doesn't have global leaderboard yet
        return None

    @commands.hybrid_command(name='rangestats', description='View shooting range statistics')
    async def range_stats(self, ctx, user: discord.Member = None):
        """View shooting range statistics"""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can view training records! Please get a Cybertronian role first.")
            return
            
        target_user = user or ctx.author
        stats = await self.bot.user_data_manager.get_shooting_range_stats(str(target_user.id))
        
        overall_accuracy = (stats['total_hits'] / stats['total_shots'] * 100) if stats['total_shots'] > 0 else 0
        
        # Create view with pagination
        view = RangeStatsView(target_user, stats, self)
        embed = view.create_stats_embed()
        
        await ctx.send(embed=embed, view=view)

class ShootingView(discord.ui.View):
    def __init__(self, target_position, user_id):
        super().__init__(timeout=1.0)  # 1 second timeout
        self.target_position = target_position
        self.user_id = user_id
        self.user_clicked = False
        self.hit = False
        
        # Create 5 buttons - 4 red circles (misses) and 1 target (hit)
        button_emojis = ['🔴', '🔴', '🔴', '🔴', '🎯']
        
        for i in range(5):
            if i == target_position:
                # Target button (hit)
                button = discord.ui.Button(
                    style=discord.ButtonStyle.danger,
                    emoji='🎯',
                    custom_id=f'target_{i}'
                )
                button.callback = self.create_callback(i, True)
            else:
                # Miss button
                miss_emoji = button_emojis[i if i < target_position else i-1]
                button = discord.ui.Button(
                    style=discord.ButtonStyle.danger,
                    emoji=miss_emoji,
                    custom_id=f'miss_{i}'
                )
                button.callback = self.create_callback(i, False)
            
            self.add_item(button)
    
    def create_callback(self, position, is_hit):
        async def button_callback(interaction: discord.Interaction):
            # Only allow the original user to click
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ This isn't your shooting session!", ephemeral=True)
                return
            
            # Only allow one click
            if self.user_clicked:
                await interaction.response.send_message("❌ You already shot!", ephemeral=True)
                return
            
            self.user_clicked = True
            self.hit = is_hit
            
            # Disable all buttons
            for item in self.children:
                item.disabled = True
            
            # Update the message
            if is_hit:
                embed = discord.Embed(
                    title="🎯 HIT!",
                    description="Perfect shot! 🔥",
                    color=0x00ff00
                )
            else:
                embed = discord.Embed(
                    title="❌ MISS!",
                    description="Better luck next time!",
                    color=0xff0000
                )
            
            await interaction.response.edit_message(embed=embed, view=self)
        
        return button_callback
    
    async def on_timeout(self):
        # Disable all buttons when timeout occurs
        for item in self.children:
            item.disabled = True

class RangeStatsView(discord.ui.View):
    def __init__(self, user, stats, cog):
        super().__init__(timeout=300)
        self.user = user
        self.stats = stats
        self.cog = cog
        self.current_page = 0  # 0 = stats, 1 = leaderboards
        
    def create_stats_embed(self):
        """Create the personal stats embed"""
        overall_accuracy = (self.stats['total_hits'] / self.stats['total_shots'] * 100) if self.stats['total_shots'] > 0 else 0
        
        embed = discord.Embed(
            title=f"🎯 {self.user.display_name}'s Training Records",
            color=0x0099ff
        )
        
        embed.add_field(
            name="📊 Overall Performance",
            value=f"**Sessions Played:** {self.stats['sessions_played']}\n**Total Hits:** {self.stats['total_hits']}/{self.stats['total_shots']}\n**Overall Accuracy:** {overall_accuracy:.1f}%",
            inline=False
        )
        
        # Show all round types in descending order
        rounds_data = ""
        for rounds in ['100', '50', '25', '15', '5']:
            if rounds in self.stats['best_records']:
                record = self.stats['best_records'][rounds]
                accuracy = record['accuracy']
                hits = record['hits']
            else:
                accuracy = 0.0
                hits = 0
            
            # Get play count for this round
            play_count = self.stats.get('round_attempts', {}).get(rounds, 0)
            
            rounds_data += f"**{rounds} rounds:** {accuracy:.1f}% ({hits}/{rounds}) - Played: {play_count}x\n"
        
        if rounds_data:
            embed.add_field(
                name="🏆 Round Performance",
                value=rounds_data,
                inline=False
            )
        
        embed.set_footer(text="Use the buttons below to navigate or refresh")
        return embed

# =============================================================================
# RPG COMMANDS (from walktru.py)
# =============================================================================

class FunSystemCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name='walktru', description='Start an interactive adventure')
    async def walktru(self, ctx):
        """Start an interactive adventure experience"""
        try:
            from .walktru import StoryMapManager, WalktruView
            
            # Initialize story map manager if not already done
            if not hasattr(self.bot, 'story_map_manager'):
                self.bot.story_map_manager = StoryMapManager(self.bot)
            
            # Load story maps using optimized user_data_manager
            story_maps = await self.bot.story_map_manager.load_story_maps_lazy()
            
            if not story_maps:
                embed = discord.Embed(
                    title="❌ Adventure System Error",
                    description="Unable to load adventure data. Please try again later.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
                
            view = WalktruView(story_maps, ctx.author.id)
            
            embed = discord.Embed(
                title="🎭 Choose Your Adventure",
                description="Select an adventure from the dropdown menu below to begin your interactive story experience!",
                color=discord.Color.purple()
            )
            
            embed.add_field(
                name="📚 Available Adventures",
                value="👻 **Horror** - Escape supernatural terrors\n"
                      "🔫 **Gangster** - Build your crime empire\n"
                      "🗡️ **Knight** - Embark on noble quests\n"
                      "🤖 **Robot** - Survive the AI uprising\n"
                      "🤠 **Western** - Conquer the frontier\n"
                      "🧙‍♂️ **Wizard** - Master magical arts",
                inline=False
            )
            
            await ctx.send(embed=embed, view=view)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to load adventures: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

class MegaFightView(discord.ui.View):
    def __init__(self, cog, challenger_team_info, ctx):
        super().__init__(timeout=MEGA_FIGHT_TIMEOUT)
        self.cog = cog
        self.challenger_team_info = challenger_team_info
        self.opponent_team_info = None
        self.ctx = ctx
        self.fight_started = False
        self.current_round = 1
        self.max_rounds = 3
        self.challenger_wins = 0
        self.opponent_wins = 0
        
    def get_team_display_name(self, team_info):
        """Get a display name for the team."""
        return team_info['name'] if team_info['name'] != "Unnamed Combiner" else f"Team {team_info['team_id'][:8]}"
    
    def update_embed(self, interaction_or_ctx, status="waiting", round_result=None):
        """Update the mega fight embed."""
        challenger_name = self.get_team_display_name(self.challenger_team_info)
        
        if status == "waiting":
            embed = discord.Embed(
                title="🤖⚔️ MEGA-FIGHT CHALLENGE!",
                description=f"**{challenger_name}** challenges another combiner team to a Mega-Fight!\n\n🎲 **Rules:**\n• No energon required to start\n• Head member controls the fight\n• Winners get energon + pet XP\n• Losers lose 50 energon + pet health\n• Pure 1-100 random rolls (pets don't affect odds)",
                color=discord.Color.orange()
            )
            embed.add_field(name="🗣️ Challenger Head", value=f"<@{self.challenger_team_info['head_id']}>", inline=True)
            embed.add_field(name="⏰ Status", value="Waiting for opponent team...", inline=True)
            
        elif status == "ready":
            opponent_name = self.get_team_display_name(self.opponent_team_info)
            embed = discord.Embed(
                title="🤖⚔️ MEGA-FIGHT READY!",
                description=f"**{challenger_name}** vs **{opponent_name}**\n\nBoth heads can now roll for their teams!",
                color=discord.Color.blue()
            )
            embed.add_field(name="🗣️ Challenger Head", value=f"<@{self.challenger_team_info['head_id']}>", inline=True)
            embed.add_field(name="🗣️ Opponent Head", value=f"<@{self.opponent_team_info['head_id']}>", inline=True)
            embed.add_field(name="🎯 Round", value=f"{self.current_round}/{self.max_rounds}", inline=True)
            
        elif status == "round_result":
            challenger_name = self.get_team_display_name(self.challenger_team_info)
            opponent_name = self.get_team_display_name(self.opponent_team_info)
            
            embed = discord.Embed(
                title=f"🎲 Round {self.current_round} Results",
                description=f"**{challenger_name}** vs **{opponent_name}**",
                color=discord.Color.green() if round_result else discord.Color.red()
            )
            
            if round_result:
                embed.add_field(name="🏆 Round Winner", value=round_result, inline=False)
            
            embed.add_field(name="📊 Score", value=f"{challenger_name}: {self.challenger_wins}\n{opponent_name}: {self.opponent_wins}", inline=True)
            embed.add_field(name="🎯 Round", value=f"{self.current_round}/{self.max_rounds}", inline=True)
            
        return embed
    
    @discord.ui.button(label='Join Mega-Fight', style=discord.ButtonStyle.green, emoji='🤖')
    async def join_mega_fight(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.opponent_team_info:
            await interaction.response.send_message("❌ This mega-fight already has an opponent!", ephemeral=True)
            return
            
        # Check if user has a complete combiner team
        user_team = self.cog.find_user_combiner_team(interaction.user.id)
        if not user_team:
            await interaction.response.send_message("❌ You need to be part of a complete combiner team to join mega-fights!", ephemeral=True)
            return
            
        # Only the head can join mega-fights
        if not user_team['is_head']:
            await interaction.response.send_message(f"❌ Only the head member (<@{user_team['head_id']}>) can join mega-fights for your combiner team!", ephemeral=True)
            return
            
        # Can't fight yourself
        if user_team['team_id'] == self.challenger_team_info['team_id']:
            await interaction.response.send_message("❌ You can't fight your own team!", ephemeral=True)
            return
            
        self.opponent_team_info = user_team
        
        # Enable roll buttons and disable join button
        button.disabled = True
        self.roll_challenger.disabled = False
        self.roll_opponent.disabled = False
        
        embed = self.update_embed(interaction, "ready")
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label='Roll (Challenger)', style=discord.ButtonStyle.primary, emoji='🎲', disabled=True)
    async def roll_challenger(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.challenger_team_info['head_id']:
            await interaction.response.send_message("❌ Only the challenger team's head can roll!", ephemeral=True)
            return
            
        if not self.opponent_team_info:
            await interaction.response.send_message("❌ Waiting for an opponent team!", ephemeral=True)
            return
            
        await self.execute_round(interaction, "challenger")
    
    @discord.ui.button(label='Roll (Opponent)', style=discord.ButtonStyle.secondary, emoji='🎲', disabled=True)
    async def roll_opponent(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.opponent_team_info['head_id']:
            await interaction.response.send_message("❌ Only the opponent team's head can roll!", ephemeral=True)
            return
            
        await self.execute_round(interaction, "opponent")
    
    async def execute_round(self, interaction, roller):
        """Execute a round of the mega-fight."""
        challenger_roll = random.randint(1, 100)
        opponent_roll = random.randint(1, 100)
        
        challenger_name = self.get_team_display_name(self.challenger_team_info)
        opponent_name = self.get_team_display_name(self.opponent_team_info)
        
        round_result = f"🎲 **{challenger_name}** rolled: **{challenger_roll}**\n🎲 **{opponent_name}** rolled: **{opponent_roll}**\n\n"
        
        if challenger_roll > opponent_roll:
            self.challenger_wins += 1
            round_result += f"🏆 **{challenger_name}** wins this round!"
        elif opponent_roll > challenger_roll:
            self.opponent_wins += 1
            round_result += f"🏆 **{opponent_name}** wins this round!"
        else:
            round_result += "🤝 **TIE!** No points awarded."
        
        self.current_round += 1
        
        # Check if fight is over
        if self.current_round > self.max_rounds or self.challenger_wins >= 2 or self.opponent_wins >= 2:
            await self.complete_mega_fight(interaction, round_result)
        else:
            embed = self.update_embed(interaction, "round_result", round_result)
            await interaction.response.edit_message(embed=embed, view=self)
    
    async def complete_mega_fight(self, interaction, final_round_result):
        """Complete the mega-fight and distribute rewards/penalties."""
        challenger_name = self.get_team_display_name(self.challenger_team_info)
        opponent_name = self.get_team_display_name(self.opponent_team_info)
        
        # Determine winner
        if self.challenger_wins > self.opponent_wins:
            winning_team = self.challenger_team_info
            losing_team = self.opponent_team_info
            winner_name = challenger_name
        else:
            winning_team = self.opponent_team_info
            losing_team = self.challenger_team_info
            winner_name = opponent_name
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        # Apply rewards and penalties
        energon_reward = random.randint(100, 300)
        energon_penalty = 50
        
        reward_messages = []
        penalty_messages = []
        
        # Process winning team
        for member_id in winning_team['all_members']:
            # Update stats
            await self.cog.update_player_stats(member_id, "mega_fights_won", 1)
            
            # Award energon using UserDataManager
            member_stats = await self.cog.get_player_stats(member_id)
            await self.cog.bot.user_data_manager.update_energon_stat(str(member_id), "energon_bank", energon_reward)
            reward_messages.append(f"<@{member_id}> gained {energon_reward} energon")
            
            # Pet XP reward
            if hasattr(self.cog.bot, 'pet_system') and hasattr(self.cog.bot, 'pet_data') and member_id in self.cog.bot.pet_data:
                xp_gain = random.randint(25, 50)
                leveled_up, level_gains = self.cog.bot.pet_system.add_experience(int(member_id), xp_gain, "mega_fight")
                reward_messages.append(f"<@{member_id}>'s pet gained {xp_gain} XP")
                
                if leveled_up and level_gains:
                    # Send level-up embed
                    user = self.cog.bot.get_user(int(member_id))
                    if user and hasattr(self.cog.bot.pet_system, 'send_level_up_embed'):
                        asyncio.create_task(self.cog.bot.pet_system.send_level_up_embed(user, self.cog.bot.pet_data[member_id], level_gains))
        
        # Process losing team
        for member_id in losing_team['all_members']:
            # Update stats
            await self.cog.update_player_stats(member_id, "mega_fights_lost", 1)
            
            # Deduct energon using UserDataManager
            member_stats = await self.cog.get_player_stats(member_id)
            await self.cog.bot.user_data_manager.update_energon_stat(str(member_id), "energon_bank", -energon_penalty)
            penalty_messages.append(f"<@{member_id}> lost {energon_penalty} energon")
            
            # Pet health penalty
            if hasattr(self.cog.bot, 'pet_system') and hasattr(self.cog.bot, 'pet_data') and member_id in self.cog.bot.pet_data:
                health_loss = random.randint(15, 30)
                self.cog.bot.pet_data[member_id]['health'] = max(0, self.cog.bot.pet_data[member_id]['health'] - health_loss)
                penalty_messages.append(f"<@{member_id}>'s pet lost {health_loss} health")
        
        # Data is automatically saved by UserDataManager - no manual saving needed
        
        # Create final embed
        embed = discord.Embed(
            title="🏆 MEGA-FIGHT COMPLETE!",
            description=f"{final_round_result}\n\n**🎉 WINNER: {winner_name}!**",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="📊 Final Score",
            value=f"{challenger_name}: {self.challenger_wins}\n{opponent_name}: {self.opponent_wins}",
            inline=True
        )
        
        if reward_messages:
            embed.add_field(
                name="🎁 Rewards (Winners)",
                value="\n".join(reward_messages[:10]),  # Limit to prevent embed overflow
                inline=False
            )
        
        if penalty_messages:
            embed.add_field(
                name="💸 Penalties (Losers)",
                value="\n".join(penalty_messages[:10]),  # Limit to prevent embed overflow
                inline=False
            )
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_timeout(self):
        """Handle timeout."""
        for item in self.children:
            item.disabled = True
        
        embed = discord.Embed(
            title="⏰ Mega-Fight Expired",
            description="No opponent joined in time. The mega-fight has been cancelled.",
            color=discord.Color.red()
        )
        
        try:
            await self.ctx.edit(embed=embed, view=self)
        except:
            pass

    @commands.hybrid_command(name='mega_fight', description="Challenge another combiner team to a Mega-Fight!")
    async def mega_fight(self, ctx):
        """Start a mega-fight between combiner teams."""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can start mega-fights! Please get a Cybertronian role first.")
            return
        
        # Check if user has a complete combiner team
        user_team = self.find_user_combiner_team(ctx.author.id)
        if not user_team:
            await ctx.send("❌ You need to be part of a complete combiner team to start mega-fights! Use `/combiner` to form a team.")
            return
        
        # Only the head can start mega-fights
        if not user_team['is_head']:
            await ctx.send(f"❌ Only the head member (<@{user_team['head_id']}>) can start mega-fights for your combiner team!")
            return
        
        # Create the mega-fight view
        view = MegaFightView(self, user_team, ctx)
        embed = view.update_embed(ctx, "waiting")
        
        await ctx.send(embed=embed, view=view)

# =============================================================================
# SETUP FUNCTION
# =============================================================================

async def setup(bot):
    """Setup function to add all cogs"""
    await bot.add_cog(ShootingRange(bot))
    await bot.add_cog(FunSystemCommands(bot))
    await bot.add_cog(HungerGamesSorter(bot))

# Export all components
__all__ = [
    'ShootingRange',
    'FunSystemCommands', 
    'HungerGamesSorter'
]