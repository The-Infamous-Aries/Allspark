import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from Systems.user_data_manager import UserDataManager

class TriviaSession:
    """Manages a trivia game session with questions, user tracking, and timing."""
    
    def __init__(self, channel_id: int, category: str, total_questions: int, questions: List[Dict]):
        self.channel_id = channel_id
        self.category = category
        self.total_questions = total_questions
        self.questions = questions[:total_questions]  # Limit to requested amount
        self.current_question_index = 0
        self.user_stats = {}  # {user_id: {"correct": 0, "attempted": 0}}
        self.current_question_answered = False
        self.answered_users: Set[int] = set()  # Users who answered current question
        self.start_time = datetime.now()
        self.is_active = True
        self.current_message = None  # Store reference to current question message
        
    def get_current_question(self) -> Optional[Dict]:
        """Get the current question or None if finished."""
        if self.current_question_index >= len(self.questions):
            return None
        return self.questions[self.current_question_index]
    
    def record_answer(self, user_id: int, is_correct: bool) -> bool:
        """Record a user's answer. Returns True if this was their first answer for this question."""
        if user_id in self.answered_users:
            return False
            
        self.answered_users.add(user_id)
        
        if user_id not in self.user_stats:
            self.user_stats[user_id] = {"correct": 0, "attempted": 0}
        
        self.user_stats[user_id]["attempted"] += 1
        if is_correct:
            self.user_stats[user_id]["correct"] += 1
            self.current_question_answered = True
            
        return True
    
    def next_question(self):
        """Move to the next question."""
        self.current_question_index += 1
        self.current_question_answered = False
        self.answered_users.clear()
    
    def is_finished(self) -> bool:
        """Check if the trivia session is complete."""
        return self.current_question_index >= len(self.questions) or not self.is_active

class TriviaView(discord.ui.View):
    """Interactive view with A, B, C, D buttons for trivia answers."""
    
    def __init__(self, session: TriviaSession, question: Dict, cog):
        super().__init__(timeout=120.0)  # 2 minute timeout
        self.session = session
        self.question = question
        self.cog = cog
        self.correct_answer = question.get('answer', 'A')
        
    async def on_timeout(self):
        """Handle timeout - move to next question."""
        if not self.session.current_question_answered and self.session.is_active:
            # Delete the question message when timeout occurs
            if self.session.current_message:
                try:
                    await self.session.current_message.delete()
                except discord.NotFound:
                    pass  # Message already deleted
                except discord.Forbidden:
                    pass  # Bot doesn't have permission to delete
                self.session.current_message = None
            await self.cog.next_question_or_finish(self.session)
    
    @discord.ui.button(label='A', style=discord.ButtonStyle.primary)
    async def answer_a(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_answer(interaction, 'A')
    
    @discord.ui.button(label='B', style=discord.ButtonStyle.primary)
    async def answer_b(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_answer(interaction, 'B')
    
    @discord.ui.button(label='C', style=discord.ButtonStyle.primary, emoji=None)
    async def answer_c(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_answer(interaction, 'C')
    
    @discord.ui.button(label='D', style=discord.ButtonStyle.primary, emoji=None)
    async def answer_d(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_answer(interaction, 'D')
    
    async def handle_answer(self, interaction: discord.Interaction, choice: str):
        """Handle a user's answer choice."""
        user_id = interaction.user.id
        
        # Check if user already answered this question
        if not self.session.record_answer(user_id, choice == self.correct_answer):
            await interaction.response.send_message(
                "❌ You've already answered this question!", 
                ephemeral=True
            )
            return
        
        is_correct = choice == self.correct_answer
        
        if is_correct:
            await interaction.response.send_message(
                f"✅ Correct! The answer was **{self.correct_answer}**", 
                ephemeral=True
            )
            # Delete the question message after a short delay
            if self.session.current_message:
                await asyncio.sleep(3)  # Give users time to see the result
                try:
                    await self.session.current_message.delete()
                except discord.NotFound:
                    pass  # Message already deleted
                except discord.Forbidden:
                    pass  # Bot doesn't have permission to delete
                self.session.current_message = None
            
            # Move to next question after a short delay
            await asyncio.sleep(2)
            await self.cog.next_question_or_finish(self.session)
        else:
            await interaction.response.send_message(
                f"❌ Incorrect! Try again or wait for the next question.", 
                ephemeral=True
            )

class Trivia(commands.Cog):
    """Trivia game system with interactive questions and user tracking."""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_manager = UserDataManager()
        self.active_sessions: Dict[int, TriviaSession] = {}  # channel_id -> session
        
    @app_commands.command(name="trivia", description="Start a trivia game with customizable category and question count")
    @app_commands.describe(
        category="Choose a trivia category",
        questions="Number of questions (1-100)"
    )
    @app_commands.choices(category=[
        app_commands.Choice(name="Culture", value="culture"),
        app_commands.Choice(name="Characters", value="characters"),
        app_commands.Choice(name="Factions", value="factions"),
        app_commands.Choice(name="Movies", value="movies"),
        app_commands.Choice(name="Shows", value="shows"),
        app_commands.Choice(name="Random Mix", value="random")
    ])
    async def trivia_command(
        self, 
        interaction: discord.Interaction, 
        category: app_commands.Choice[str],
        questions: app_commands.Range[int, 1, 100] = 10
    ):
        """Start a trivia game session."""
        channel_id = interaction.channel_id
        
        # Check if there's already an active session in this channel
        if channel_id in self.active_sessions:
            await interaction.response.send_message(
                "❌ There's already an active trivia session in this channel!", 
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            # Get trivia questions based on category
            if category.value == "random":
                all_questions = []
                categories = ["culture", "characters", "factions", "movies", "shows"]
                for cat in categories:
                    cat_questions = await self.get_trivia_questions(cat)
                    all_questions.extend(cat_questions)
                trivia_questions = random.sample(all_questions, min(questions, len(all_questions)))
                category_name = "Random Mix"
            else:
                trivia_questions = await self.get_trivia_questions(category.value)
                if len(trivia_questions) < questions:
                    questions = len(trivia_questions)
                trivia_questions = random.sample(trivia_questions, questions)
                category_name = category.name
            
            if not trivia_questions:
                await interaction.followup.send("❌ No trivia questions found for this category!")
                return
            
            # Create trivia session
            session = TriviaSession(channel_id, category_name, questions, trivia_questions)
            self.active_sessions[channel_id] = session
            
            # Send initial embed
            embed = discord.Embed(
                title="🧠 Trivia Game Started!",
                description=f"**Category:** {category_name}\n**Questions:** {questions}\n**Started by:** {interaction.user.mention}",
                color=0x00ff00
            )
            embed.add_field(
                name="📋 Rules",
                value="• Each user can answer once per question\n• First correct answer moves to next question\n• 2 minutes per question\n• Have fun!",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            
            # Start the first question
            await asyncio.sleep(2)
            await self.show_question(session)
            
        except Exception as e:
            error_msg = f"❌ Error starting trivia: {type(e).__name__}: {str(e)}"
            if not str(e):  # If error message is empty or just "0"
                error_msg = "❌ Error starting trivia: Unable to load trivia questions. Please check if trivia data files exist."
            await interaction.followup.send(error_msg)
    
    async def get_trivia_questions(self, category: str) -> List[Dict]:
        """Get trivia questions for a specific category."""
        method_map = {
            "culture": self.data_manager.get_trivia_transformers_culture,
            "characters": self.data_manager.get_trivia_transformers_characters,
            "factions": self.data_manager.get_trivia_transformers_factions,
            "movies": self.data_manager.get_trivia_transformers_movies,
            "shows": self.data_manager.get_trivia_transformers_shows
        }
        
        if category in method_map:
            try:
                result = await method_map[category]()
                if not result:
                    print(f"Warning: No trivia questions found for category '{category}'")
                return result
            except Exception as e:
                print(f"Error loading trivia questions for category '{category}': {type(e).__name__}: {str(e)}")
                raise Exception(f"Failed to load trivia questions for category '{category}': {str(e)}")
        return []
    
    async def show_question(self, session: TriviaSession):
        """Display the current question with interactive buttons."""
        question_data = session.get_current_question()
        if not question_data:
            await self.show_results(session)
            return
        
        channel = self.bot.get_channel(session.channel_id)
        if not channel:
            return
        
        # Create question embed
        embed = discord.Embed(
            title=f"❓ Question {session.current_question_index + 1}/{session.total_questions}",
            description=question_data.get('question', 'No question text'),
            color=0x3498db
        )

        options = question_data.get('options', {})
        if isinstance(options, dict) and len(options) >= 4:
            embed.add_field(name="📝 Answer Choices", value="", inline=False)
            embed.add_field(name="A", value=options.get('A', ''), inline=False)
            embed.add_field(name="B", value=options.get('B', ''), inline=False)
            embed.add_field(name="C", value=options.get('C', ''), inline=False)
            embed.add_field(name="D", value=options.get('D', ''), inline=False)
        elif isinstance(options, list) and len(options) >= 4:
            embed.add_field(name="📝 Answer Choices", value="", inline=False)
            embed.add_field(name="A", value=options[0], inline=False)
            embed.add_field(name="B", value=options[1], inline=False)
            embed.add_field(name="C", value=options[2], inline=False)
            embed.add_field(name="D", value=options[3], inline=False)
        
        embed.add_field(
            name="⏱️ Time Limit", 
            value="2 minutes to answer", 
            inline=False
        )
        embed.add_field(
            name="📊 Progress", 
            value=f"Category: {session.category}", 
            inline=False
        )
        
        # Create view with buttons
        view = TriviaView(session, question_data, self)
        
        try:
            message = await channel.send(embed=embed, view=view)
            session.current_message = message  # Store message reference for later deletion
        except Exception as e:
            print(f"Error sending question: {e}")
            session.current_message = None
    
    async def next_question_or_finish(self, session: TriviaSession):
        """Move to next question or finish the trivia session."""
        if not session.is_active:
            return
            
        session.next_question()
        
        if session.is_finished():
            await self.show_results(session)
        else:
            await self.show_question(session)
    
    async def show_results(self, session: TriviaSession):
        """Show final results and clean up the session."""
        channel = self.bot.get_channel(session.channel_id)
        if not channel:
            return
        
        # Remove session from active sessions
        if session.channel_id in self.active_sessions:
            del self.active_sessions[session.channel_id]
        
        session.is_active = False
        
        # Calculate total stats
        total_attempted = sum(stats["attempted"] for stats in session.user_stats.values())
        total_correct = sum(stats["correct"] for stats in session.user_stats.values())
        
        # Create results embed
        embed = discord.Embed(
            title="🏆 Trivia Results",
            description=f"**Category:** {session.category}\n**Total Questions:** {session.total_questions}",
            color=0xffd700
        )
        
        embed.add_field(
            name="📊 Overall Stats",
            value=f"Questions Attempted: {total_attempted}\nCorrect Answers: {total_correct}\nAccuracy: {(total_correct/total_attempted*100):.1f}%" if total_attempted > 0 else "No questions attempted",
            inline=False
        )
        
        # User performance
        if session.user_stats:
            user_performance = []
            for user_id, stats in sorted(session.user_stats.items(), key=lambda x: x[1]["correct"], reverse=True):
                user = self.bot.get_user(user_id)
                username = user.display_name if user else f"User {user_id}"
                accuracy = (stats["correct"]/stats["attempted"]*100) if stats["attempted"] > 0 else 0
                user_performance.append(f"**{username}:** {stats['correct']}/{stats['attempted']} ({accuracy:.1f}%)")
            
            embed.add_field(
                name="👥 Player Performance",
                value="\n".join(user_performance[:10]),  # Limit to top 10
                inline=False
            )
        else:
            embed.add_field(
                name="👥 Player Performance",
                value="No one participated 😢",
                inline=False
            )
        
        # Duration
        duration = datetime.now() - session.start_time
        embed.add_field(
            name="⏱️ Duration",
            value=f"{duration.seconds // 60}m {duration.seconds % 60}s",
            inline=True
        )
        
        embed.set_footer(text="Thanks for playing! Use /trivia to start another game.")
        
        try:
            await channel.send(embed=embed)
        except Exception as e:
            print(f"Error sending results: {e}")

async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(Trivia(bot))