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
        cybertronian_roles = []
        for role in ['Autobot', 'Decepticon', 'Maverick', 'Cybertronian_Citizen']:
            role_id = ROLE_IDS.get(role)
            if isinstance(role_id, list):
                cybertronian_roles.extend(role_id)
            elif role_id:
                cybertronian_roles.append(role_id)
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
            
            # Wait for user interaction or timeout (1.2 seconds to match view timeout + 0.2s)
            await asyncio.sleep(1.2)
            
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
        
        # Ensure we have valid stats data
        if not updated_stats or 'best_records' not in updated_stats:
            updated_stats = {
                'sessions_played': 0,
                'total_hits': 0,
                'total_shots': 0,
                'best_records': {
                    '5': {'accuracy': 0, 'hits': 0},
                    '15': {'accuracy': 0, 'hits': 0},
                    '25': {'accuracy': 0, 'hits': 0},
                    '50': {'accuracy': 0, 'hits': 0},
                    '100': {'accuracy': 0, 'hits': 0}
                }
            }
        
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
        
        # Ensure we have valid stats data
        if not stats or 'best_records' not in stats:
            stats = {
                'sessions_played': 0,
                'total_hits': 0,
                'total_shots': 0,
                'best_records': {
                    '5': {'accuracy': 0, 'hits': 0},
                    '15': {'accuracy': 0, 'hits': 0},
                    '25': {'accuracy': 0, 'hits': 0},
                    '50': {'accuracy': 0, 'hits': 0},
                    '100': {'accuracy': 0, 'hits': 0}
                },
                'round_attempts': {}
            }
        
        overall_accuracy = (stats['total_hits'] / stats['total_shots'] * 100) if stats['total_shots'] > 0 else 0
        
        # Create view with pagination
        view = RangeStatsView(target_user, stats, self)
        embed = view.create_stats_embed()
        
        await ctx.send(embed=embed, view=view)

class ShootingView(discord.ui.View):
    def __init__(self, target_position, user_id):
        super().__init__(timeout=1.2)  # 1.2 second timeout to match sleep timing
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

class FunSystemCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def has_cybertronian_role(self, member):
        """Check if a member has any Cybertronian role."""
        cybertronian_roles = [ROLE_IDS.get(role) for role in ['Autobot', 'Decepticon', 'Maverick', 'Cybertronian_Citizen']]
        return any(role.id in cybertronian_roles for role in member.roles)

    @commands.hybrid_command(name='walktru', description='Start an interactive adventure')
    async def walktru(self, ctx):
        """Start an interactive adventure experience"""
        # Check if user has Cybertronian role
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can access the adventure system! Please get a Cybertronian role first.")
            return
            
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

async def setup(bot):
    """Setup function to add all cogs"""
    await bot.add_cog(ShootingRange(bot))
    await bot.add_cog(FunSystemCommands(bot))

# Export all components
__all__ = [
    'ShootingRange',
    'FunSystemCommands', 
    'CybertronGames'
]