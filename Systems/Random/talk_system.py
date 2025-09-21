import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select
import json
import os
import random
import asyncio
import aiohttp
import re
import time
from datetime import datetime, timedelta
from collections import Counter
from typing import Dict, List, Optional, Tuple, Any

try:
    from config import ROLE_IDS, GRUMP_USER_ID, ARIES_USER_ID
except ImportError:
    # Fallback definitions
    ROLE_IDS = {}
    GRUMP_USER_ID = 0
    ARIES_USER_ID = 0

# Legacy JSON functions removed - all data operations now use user_data_manager

class LoreSystem:
    """Manages server lore and history entries"""
    
    def __init__(self, bot):
        self.bot = bot
        self.lore_data = {}
        self.lore_file = "user_lore.json"
        self._lore_loaded = False
    
    async def _ensure_lore_loaded(self):
        """Ensure lore data is loaded before access"""
        if not self._lore_loaded:
            await self.load_lore_data()
            self._lore_loaded = True
    
    async def load_lore_data(self):
        """Load lore data using OptimizedUserDataManager"""
        self.lore_data = await self.bot.user_data_manager.get_user_lore_data()
        self._lore_loaded = True
    
    async def save_lore_data(self):
        """Save lore data using OptimizedUserDataManager"""
        await self._ensure_lore_loaded()
        await self.bot.user_data_manager.save_user_lore_data(self.lore_data)
    
    async def add_lore_entry(self, title: str, description: str, author_id: int, timestamp: datetime) -> bool:
        """Add a new lore entry"""
        await self._ensure_lore_loaded()
        if title in self.lore_data:
            return False
        
        self.lore_data[title] = {
            'title': title,
            'description': description,
            'author_id': str(author_id),
            'timestamp': str(timestamp)
        }
        await self.save_lore_data()
        return True
    
    async def get_lore_entry(self, title: str) -> Optional[Dict]:
        """Get a specific lore entry"""
        await self._ensure_lore_loaded()
        return self.lore_data.get(title)
    
    async def get_all_lore_titles(self) -> List[str]:
        """Get all lore entry titles"""
        await self._ensure_lore_loaded()
        return list(self.lore_data.keys())
    
    async def get_random_lore(self) -> Optional[Dict]:
        """Get a random lore entry"""
        await self._ensure_lore_loaded()
        if not self.lore_data:
            return None
        title = random.choice(list(self.lore_data.keys()))
        return self.lore_data[title]
    
    async def has_lore_entries(self) -> bool:
        """Check if there are any lore entries"""
        await self._ensure_lore_loaded()
        return len(self.lore_data) > 0

class TransformersLore:
    """Handles Transformers lore lookups and blessings"""
    
    def __init__(self, bot):
        self.bot = bot
        self.lore_data = {}
        self.blessings_data = {}
        self._lore_loaded = False
        self._blessings_loaded = False
    
    async def _ensure_lore_loaded(self):
        """Ensure Transformers lore data is loaded before access"""
        if not self._lore_loaded:
            self.lore_data = await self.bot.user_data_manager.get_what_talk_data()
            self._lore_loaded = True

    async def _ensure_blessings_loaded(self):
        """Ensure blessings data is loaded before access"""
        if not self._blessings_loaded:
            self.blessings_data = await self.bot.user_data_manager.get_blessings_talk_data()
            self._blessings_loaded = True
    
    async def get_lore_entry(self, topic: str) -> Optional[Dict]:
        """Get Transformers lore entry by topic"""
        await self._ensure_lore_loaded()
        topic_key = None
        for key in self.lore_data.keys():
            if key.lower() == topic.lower():
                topic_key = key
                break
        return self.lore_data.get(topic_key)
    
    async def get_available_topics(self) -> List[str]:
        """Get list of available lore topics"""
        await self._ensure_lore_loaded()
        return list(self.lore_data.keys())
    
    async def get_blessing(self, category: Optional[str] = None) -> Optional[Tuple[str, str]]:
        """Get a blessing from the Allspark"""
        await self._ensure_blessings_loaded()
        if not self.blessings_data:
            return None
        
        if category and category in self.blessings_data:
            blessing_list = self.blessings_data[category]
            chosen_blessing = random.choice(blessing_list)
            return (category, chosen_blessing)
        else:
            category = random.choice(list(self.blessings_data.keys()))
            blessing_list = self.blessings_data[category]
            chosen_blessing = random.choice(blessing_list)
            return (category, chosen_blessing)
    
    async def get_blessing_categories(self) -> List[str]:
        """Get available blessing categories"""
        await self._ensure_blessings_loaded()
        return list(self.blessings_data.keys())

class JokeSystem:
    """Handles joke generation and delivery"""
    
    def __init__(self, bot):
        self.bot = bot
        self.transformers_jokes = []
        self._jokes_loaded = False
    
    async def _ensure_jokes_loaded(self):
        """Ensure jokes data is loaded before access"""
        if not self._jokes_loaded:
            jokes_data = await self.bot.user_data_manager.get_jokes_talk_data()
            self.transformers_jokes = jokes_data.get('transformers_politics_war_jokes', [])
            self._jokes_loaded = True
    
    async def get_api_joke(self, category: str = None) -> Optional[Dict]:
        """Get joke from JokeAPI"""
        try:
            # Actual JokeAPI supported categories
            api_category_map = {
                'coding': 'Programming',
                'robots': 'Misc',
                'dark': 'Dark',
                'pun': 'Pun',
                'spooky': 'Spooky',
                'christmas': 'Christmas',
                'random': 'Any'
            }
            
            api_cat = api_category_map.get(category, 'Any')
            url = f"https://v2.jokeapi.dev/joke/{api_cat}"
            url += "?blacklistFlags=nsfw,religious,racist,sexist,explicit"
            
            timeout = aiohttp.ClientTimeout(total=8)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get('error'):
                            return None
                            
                        if data.get('type') == 'single':
                            return {
                                'setup': data.get('joke', ''),
                                'delivery': None,
                                'category': data.get('category', 'API')
                            }
                        else:
                            return {
                                'setup': data.get('setup', ''),
                                'delivery': data.get('delivery', ''),
                                'category': data.get('category', 'API')
                            }
            return None
        except:
            return None
    
    async def get_random_joke(self, category: str = None) -> Dict:
        """Get a random joke from JSON collections only - no API fallback"""
        await self._ensure_jokes_loaded()
        transformers_jokes = self.transformers_jokes
        
        if category == "transformers_pnw":
            # EXCLUSIVELY use transformers_politics_war_jokes for Transformers PnW
            if transformers_jokes:
                return random.choice(transformers_jokes)
            else:
                # Only use hardcoded fallback if JSON is empty
                return {
                    'setup': 'Why did the Autobot cross the road?',
                    'delivery': 'To get to the Energon station on the other side!',
                    'category': 'Transformers PnW'
                }
        
        elif category == "coding":
            # Filter for coding/programming jokes from Transformers collection
            coding_jokes = [j for j in transformers_jokes 
                           if 'coding' in j.get('category', '').lower() or 'programming' in j.get('category', '').lower()]
            if coding_jokes:
                return random.choice(coding_jokes)
            elif transformers_jokes:
                return random.choice(transformers_jokes)  # Fallback to any Transformers joke
        
        elif category == "war" or category == "politics":
            # Map war and politics to use transformers_politics_war_jokes
            if transformers_jokes:
                # Filter by appropriate category
                filtered_jokes = [j for j in transformers_jokes 
                                if any(cat_type in j.get('category', '').lower() 
                                       for cat_type in ['war', 'politics', 'military'])]
                if filtered_jokes:
                    return random.choice(filtered_jokes)
                return random.choice(transformers_jokes)
        
        elif category == "random":
            # For random, use any Transformers joke
            if transformers_jokes:
                return random.choice(transformers_jokes)

        return None

class UserAnalysis:
    """Analyzes user word usage and generates dialogue"""
    
    def __init__(self, bot):
        self.bot = bot
        self.dialogue_templates = []
        self.duo_templates = []
        self.trio_templates = []
        self._templates_loaded = False
    
    async def _ensure_templates_loaded(self):
        """Ensure talk templates are loaded"""
        if not self._templates_loaded:
            templates_data = await self.bot.user_data_manager.get_talk_templates_data()
            self.dialogue_templates = templates_data.get('dialogue_templates', [
                "My Autobot sensors detect a high probability of you saying, 'I need more {user1word1} for my {user1word2} and {user1word3}.'",
                "Optimus Prime would be proud of your dedication to {user1word1}, {user1word2}, and {user1word3}."
            ])
            self.duo_templates = templates_data.get('duo_templates', [
                "{user1}: 'Hey {user2}, what do you think about {user1word1}?' {user2}: 'Well {user1}, I prefer {user2word1} over {user1word1} any day!'"
            ])
            self.trio_templates = templates_data.get('trio_templates', [
                "{user1}: 'What do you think about {user1word1}?' {user2}: 'I prefer {user2word1}!' {user3}: 'Both are good, but {user3word1} is better!'"
            ])
            self._templates_loaded = True
    
    def get_top_words(self, messages: List[str], limit: int = 3) -> List[str]:
        """Get top words from a list of messages"""
        words = []
        for message in messages:
            # Basic word extraction
            words_in_msg = re.findall(r'\b\w{3,}\b', message.lower())
            words.extend(w for w in words_in_msg if w not in ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who', 'boy', 'did', 'man', 'way', 'been', 'call', 'each', 'find', 'have', 'into', 'like', 'look', 'make', 'many', 'more', 'over', 'said', 'some', 'time', 'than', 'that', 'them', 'very', 'well', 'what', 'with', 'word', 'work', 'your', 'come', 'could', 'down', 'first', 'from', 'good', 'just', 'know', 'last', 'long', 'made', 'much', 'need', 'only', 'other', 'part', 'place', 'right', 'same', 'should', 'still', 'such', 'take', 'then', 'these', 'they', 'think', 'this', 'through', 'turn', 'under', 'want', 'water', 'where', 'which', 'will', 'would', 'write', 'year', 'years'])
        
        word_counts = Counter(words)
        return [word for word, count in word_counts.most_common(limit)]
    
    async def generate_dialogue(self, user_words: Dict[discord.User, List[str]]) -> str:
        """Generate dialogue based on user word analysis"""
        await self._ensure_templates_loaded()
        
        if not user_words:
            return "I sense great potential in this conversation, but insufficient data to analyze."
        
        template = random.choice(self.dialogue_templates)
        
        # Fill in template variables
        for user, words in user_words.items():
            if len(words) >= 3:
                template = template.replace('{user1word1}', words[0] if words else 'data')
                template = template.replace('{user1word2}', words[1] if len(words) > 1 else 'analysis')
                template = template.replace('{user1word3}', words[2] if len(words) > 2 else 'patterns')
        
        return template

class LorePaginator(View):
    """Paginated view for browsing individual lore entries"""
    
    def __init__(self, lore_system: LoreSystem, bot):
        super().__init__(timeout=300)
        self.lore_system = lore_system
        self.bot = bot
        self.current_page = 0
        self.total_pages = 0
        self.titles = []
        
    async def setup(self):
        """Initialize the paginator with data"""
        self.titles = await self.lore_system.get_all_lore_titles()
        self.total_pages = len(self.titles)
        
        # Update button states
        self.previous_button.disabled = True
        self.next_button.disabled = self.total_pages <= 1
    
    async def create_embed(self, page: int) -> discord.Embed:
        """Create rich embed for the current lore entry"""
        if not self.titles:
            return discord.Embed(
                title="📚 Server Lore Collection",
                description="No lore entries found.",
                color=discord.Color.red()
            )
        
        title = self.titles[page]
        entry = await self.lore_system.get_lore_entry(title)
        
        try:
            author = await self.bot.fetch_user(int(entry['author_id']))
            author_name = author.display_name
            author_avatar = author.display_avatar.url
        except:
            author_name = "Unknown User"
            author_avatar = None
        
        embed = discord.Embed(
            title=f"📜 {entry['title']}",
            description=entry['description'],
            color=discord.Color.gold()
        )
        
        embed.set_footer(
            text=f"Entry {page + 1} of {self.total_pages} • Authored by {author_name} | {entry['timestamp'][:19]}"
        )
        
        if author_avatar:
            embed.set_author(name=author_name, icon_url=author_avatar)
        else:
            embed.set_author(name=author_name)
        
        return embed
    
    @discord.ui.button(label='◀️ Previous', style=discord.ButtonStyle.secondary, disabled=True)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            
            self.previous_button.disabled = (self.current_page == 0)
            self.next_button.disabled = (self.current_page >= self.total_pages - 1)
            
            embed = await self.create_embed(self.current_page)
            await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label='Next ▶️', style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            
            self.previous_button.disabled = (self.current_page == 0)
            self.next_button.disabled = (self.current_page >= self.total_pages - 1)
            
            embed = await self.create_embed(self.current_page)
            await interaction.response.edit_message(embed=embed, view=self)

class UserSaysView(View):
    """View for user word analysis display"""
    
    def __init__(self, bot, members, user_words, dialogue):
        super().__init__(timeout=60)
        self.bot = bot
        self.members = members
        self.user_words = user_words
        self.dialogue = dialogue
        self.current_view = "top3"
        self.requesting_user = members[0] if members else None
    
    async def on_timeout(self):
        for button in self.children:
            button.disabled = True
        await self.message.edit(view=self)
    
    @discord.ui.button(label="Top 3", style=discord.ButtonStyle.secondary, custom_id="top3_view", emoji="🏅")
    async def top3_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.requesting_user:
            await interaction.response.send_message("This isn't your report!", ephemeral=True)
            return
        
        if self.current_view == "top3":
            return
            
        self.current_view = "top3"
        self.update_button_styles()
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="I/We Say", style=discord.ButtonStyle.danger, custom_id="dialogue_view", emoji="💬")
    async def dialogue_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.requesting_user:
            await interaction.response.send_message("This isn't your report!", ephemeral=True)
            return
            
        if self.current_view == "dialogue":
            return
            
        self.current_view = "dialogue"
        self.update_button_styles()
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    def update_button_styles(self):
        """Update button styles to show which view is active"""
        for item in self.children:
            if item.custom_id == "top3_view":
                item.style = discord.ButtonStyle.primary if self.current_view == "top3" else discord.ButtonStyle.secondary
            elif item.custom_id == "dialogue_view":
                item.style = discord.ButtonStyle.primary if self.current_view == "dialogue" else discord.ButtonStyle.secondary
    
    def create_embed(self):
        if len(self.members) == 1:
            title = f"🤖 User Analysis Report for {self.members[0].name}"
            pronoun = "I"
        else:
            member_names = ", ".join([member.name for member in self.members])
            title = f"🤖 Group Analysis Report for {member_names}"
            pronoun = "We"
            
        embed = discord.Embed(title=title, color=discord.Color.blue())
        
        if self.current_view == "top3":
            medal_emojis = ["🥇", "🥈", "🥉"]
            
            if len(self.members) == 1:
                user = self.members[0]
                words = self.user_words.get(user, [])
                words_string = "\n".join([
                    f"{medal_emojis[i]} {word}" for i, word in enumerate(words[:3])
                ]) if words else "No data available."
                embed.add_field(name="📊 Most Used Words", value=words_string, inline=False)
            else:
                for user in self.members:
                    words = self.user_words.get(user, [])
                    words_string = "\n".join([
                        f"{medal_emojis[i]} {word}" for i, word in enumerate(words[:3])
                    ]) if words else "No data available."
                    embed.add_field(name=f"📊 {user.name}'s Top Words", value=words_string, inline=True)
                    
            embed.set_footer(text="Top 3 Words Analysis")
        else:
            embed.add_field(name=f"🎭 {pronoun} would probably say...", value=f"\"{self.dialogue}\"", inline=False)
            embed.set_footer(text="Humorous Projection")

        return embed

class ConversationCommands:
    """Simple placeholder for conversation commands"""
    def __init__(self, bot):
        self.bot = bot
    
    async def handle_hello(self, message):
        """Handle hello conversations"""
        pass

class TalkSystem(commands.Cog):
    """Main cog for all talk system functionality"""
    
    def __init__(self, bot):
        self.bot = bot
        self.lore_system = LoreSystem(bot)
        self.transformers_lore = TransformersLore(bot)
        self.joke_system = JokeSystem(bot)
        self.user_analysis = UserAnalysis(bot)
        self.conversation = ConversationCommands(bot)
        
        # Initialize cooldowns
        if not hasattr(bot, 'hello_cooldowns'):
            self.bot.hello_cooldowns = {}
    
    def has_cybertronian_role(self, member: discord.Member) -> bool:
        """Check if member has any Cybertronian role"""
        cybertronian_roles = []
        for role_name in ['Autobot', 'Decepticon', 'Maverick', 'Cybertronian_Citizen']:
            role_ids = ROLE_IDS.get(role_name, [])
            if isinstance(role_ids, list):
                cybertronian_roles.extend(role_ids)
            else:
                cybertronian_roles.append(role_ids)
        
        return any(role.id in cybertronian_roles for role in member.roles)

    # Lore Commands
    @commands.hybrid_command(name='add_lore', description='Add a new lore entry to the server\'s history')
    async def add_lore(self, ctx, *, title: str = None):
        """Add a new lore entry"""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can add lore entries! Please get a Cybertronian role first.")
            return
        
        if not title:
            await ctx.send("📜 Please provide a title for your lore entry. Example: `/add_lore The Great Energon War`")
            return
        
        if await self.lore_system.get_lore_entry(title):
            await ctx.send(f"❌ A lore entry with the title '**{title}**' already exists. Please choose a different title.")
            return
        
        description = ""
        
        if ctx.message.reference and ctx.message.reference.message_id:
            try:
                replied_message = await ctx.fetch_message(ctx.message.reference.message_id)
                author_name = replied_message.author.display_name
                description = f"**@{author_name} says:**\n> {replied_message.content}\n\n"
                await ctx.send(f"📜 I've captured that message from **{author_name}**. Now, what's the rest of the lore for '**{title}**'? Type your description below (or just send 'done' if the quoted message is enough).")
            except discord.NotFound:
                await ctx.send("❌ The message you replied to could not be found.")
                return
        else:
            await ctx.send(f"📜 Start typing the lore for '**{title}**'. I'll wait for your next message.")
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            user_message = await self.bot.wait_for('message', check=check, timeout=300.0)
            
            if user_message.content.lower().strip() != 'done':
                description += user_message.content
            
            success = await self.lore_system.add_lore_entry(title, description, ctx.author.id, ctx.message.created_at)
            
            if success:
                embed = discord.Embed(
                    title="📜 Lore Entry Added!",
                    description=f"Successfully added '**{title}**' to the server's lore.",
                    color=discord.Color.gold()
                )
                embed.set_footer(text=f"Added by {ctx.author.display_name}")
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Failed to add lore entry. Please try again.")
                
        except asyncio.TimeoutError:
            await ctx.send("⏰ You took too long to provide a description. The lore entry has been cancelled.")


    @commands.hybrid_command(name='add_message_to_lore', description='Add an existing message to the lore system')
    @app_commands.describe(
        message_id="The ID of the message to add",
        title="Title for the lore entry",
        channel="Channel where the message is located (optional - defaults to current)"
    )
    async def add_message_to_lore(self, ctx, message_id: str, title: str, channel: discord.TextChannel = None):
        """Add an existing message to lore by message ID"""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can add lore entries! Please get a Cybertronian role first.")
            return
        
        if await self.lore_system.get_lore_entry(title):
            await ctx.send(f"❌ A lore entry with the title '**{title}**' already exists. Please choose a different title.")
            return
        
        target_channel = channel or ctx.channel
        
        try:
            # Handle both numeric IDs and message links
            if message_id.isdigit():
                message = await target_channel.fetch_message(int(message_id))
            else:
                # Handle message links
                message = await target_channel.fetch_message(int(message_id.split('/')[-1]))
            
            author_name = message.author.display_name
            description = f"**@{author_name} says:**\n> {message.content}\n\n"
            
            # Add timestamp and channel context
            description += f"*Originally posted in #{target_channel.name} on {message.created_at.strftime('%Y-%m-%d %H:%M:%S')}*"
            
            success = await self.lore_system.add_lore_entry(title, description, ctx.author.id, ctx.message.created_at)
            
            if success:
                embed = discord.Embed(
                    title="📜 Message Added to Lore!",
                    description=f"Successfully added message from **{author_name}** to lore as '**{title}**'",
                    color=discord.Color.gold()
                )
                embed.add_field(name="Original Message", value=message.content[:500] + ("..." if len(message.content) > 500 else ""), inline=False)
                embed.set_footer(text=f"Added by {ctx.author.display_name}")
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Failed to add the message to lore. Please try again.")
                
        except discord.NotFound:
            await ctx.send("❌ Could not find that message. Make sure the message ID is correct and the message exists in the specified channel.")
        except ValueError:
            await ctx.send("❌ Invalid message ID format. Please provide a valid message ID (numbers only) or message link.")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {str(e)}")
            
    @add_message_to_lore.autocomplete('title')
    async def title_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete for lore titles"""
        # Return empty list for new titles, or suggest variations
        return [
            app_commands.Choice(name=f"Message from {interaction.user.display_name}", value=f"Message from {interaction.user.display_name}"),
            app_commands.Choice(name=f"Historic Moment", value="Historic Moment"),
            app_commands.Choice(name=f"Important Discussion", value="Important Discussion")
        ][:3]



    @commands.hybrid_command(name='view_lore', description='View lore entries with paginated navigation')
    async def view_lore(self, ctx):
        """View lore entries using a paginated embed system"""
        if not await self.lore_system.has_lore_entries():
            embed = discord.Embed(
                title="📚 No Lore Entries",
                description="There are no lore entries yet! Use `/add_lore` to create the first entry.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        paginator = LorePaginator(self.lore_system, self.bot)
        await paginator.setup()
        
        embed = await paginator.create_embed(0)
        await ctx.send(embed=embed, view=paginator)
    
    @commands.hybrid_command(name='random_lore', description='Display a random lore entry from the server\'s history')
    async def random_lore(self, ctx):
        """Display a random lore entry"""
        if not await self.lore_system.has_lore_entries():
            embed = discord.Embed(
                title="📚 No Lore Entries",
                description="There are no lore entries yet! Use `/add_lore` to create the first entry.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        entry = await self.lore_system.get_random_lore()
        
        try:
            author = await self.bot.fetch_user(int(entry['author_id']))
            author_name = author.display_name
        except:
            author_name = "Unknown User"
        
        embed = discord.Embed(
            title=f"🎲 Random Lore: {entry['title']}",
            description=entry['description'],
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Authored by {author_name} | {entry['timestamp'][:19]}")
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='lore_stats', description='View statistics about the server\'s lore collection')
    async def lore_stats(self, ctx):
        """Display lore collection statistics"""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can view lore statistics! Please get a Cybertronian role first.")
            return
            
        if not await self.lore_system.has_lore_entries():
            embed = discord.Embed(
                title="📊 Lore Statistics",
                description="No lore entries exist yet!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        total_entries = len(self.lore_system.lore_data)
        
        author_counts = {}
        for entry in self.lore_system.lore_data.values():
            author_id = entry['author_id']
            author_counts[author_id] = author_counts.get(author_id, 0) + 1
        
        top_contributors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        contributor_text = ""
        for author_id, count in top_contributors:
            try:
                user = await self.bot.fetch_user(int(author_id))
                contributor_text += f"• {user.display_name}: {count} entries\n"
            except:
                contributor_text += f"• Unknown User: {count} entries\n"
        
        embed = discord.Embed(
            title="📊 Lore Statistics",
            color=discord.Color.blue()
        )
        embed.add_field(name="📚 Total Entries", value=str(total_entries), inline=True)
        embed.add_field(name="👥 Contributors", value=str(len(author_counts)), inline=True)
        embed.add_field(name="🏆 Top Contributors", value=contributor_text or "None", inline=False)
        
        await ctx.send(embed=embed)
    
    # Transformers Lore Commands
    @commands.hybrid_command(name='what_is', description='Learn about Transformers lore')
    @app_commands.describe(topic="Choose a Transformers topic to learn about")
    async def what_is(self, ctx, topic: str):
        """Look up Transformers lore"""
        entry = await self.transformers_lore.get_lore_entry(topic)
        
        if entry:
            embed = discord.Embed(
                title=entry["title"],
                description=entry["description"],
                color=0x0099ff
            )
            embed.set_footer(text="Knowledge from the Cybertronian Archives")
            await ctx.send(embed=embed)
        else:
            available_topics = ", ".join(await self.transformers_lore.get_available_topics())
            embed = discord.Embed(
                title="❓ Topic Not Found",
                description=f"I don't have information about '{topic}'.\n\n**Available topics:**\n{available_topics}",
                color=0xff6600
            )
            await ctx.send(embed=embed)

    @what_is.autocomplete('topic')
    async def what_is_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete for Transformers lore topics"""
        topics = await self.transformers_lore.get_available_topics()
        return [
            app_commands.Choice(name=topic, value=topic)
            for topic in topics if current.lower() in topic.lower()
        ][:25]
    
    @commands.hybrid_command(name='blessing', description='Receive a blessing from the Allspark')
    @app_commands.describe(category="Choose a specific blessing category (optional)")
    async def blessing(self, ctx, category: str = None):
        """Get a blessing from the Allspark"""
        # Check if user has Cybertronian role
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can receive blessings from the Allspark! Please get a Cybertronian role first.")
            return
            
        blessing_data = await self.transformers_lore.get_blessing(category)
        
        if not blessing_data:
            await ctx.send("⚠️ The Allspark's wisdom is temporarily unavailable.")
            return
        
        category_name, blessing_text = blessing_data
        
        embed = discord.Embed(
            title="🌟 Blessing from the Allspark",
            description=f"**{category_name}**\n\n*{blessing_text}*",
            color=0x00ff88
        )
        embed.set_footer(text="May the Allspark guide your path")
        
        await ctx.send(embed=embed)
    
    @blessing.autocomplete('category')
    async def blessing_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete for blessing categories"""
        categories = await self.transformers_lore.get_blessing_categories()
        return [
            app_commands.Choice(name=category, value=category)
            for category in categories if current.lower() in category.lower()
        ][:25]
    
    # Joke Commands
    @commands.hybrid_command(name='joke', description='Get a random joke to brighten your day!')
    @app_commands.describe(category="Choose a specific joke category")
    @app_commands.choices(category=[
        app_commands.Choice(name="🤖 Transformers PnW", value="transformers_pnw"),
        app_commands.Choice(name="💻 Coding/Programming", value="coding"),
        app_commands.Choice(name="🌑 Dark Humor", value="dark"),
        app_commands.Choice(name="🃏 Puns", value="pun"),
        app_commands.Choice(name="👻 Spooky", value="spooky"),
        app_commands.Choice(name="🎄 Christmas", value="christmas"),
        app_commands.Choice(name="🎲 Random", value="random")
    ])
    async def joke(self, ctx: commands.Context, category: str = None):
        """Get a random joke"""
        # Check if user has Cybertronian role
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can access the joke system! Please get a Cybertronian role first.")
            return
            
        async with ctx.typing():
            # Skip API for transformers_pnw, use JSON only
            if category == "transformers_pnw":
                joke_data = await self.joke_system.get_random_joke(category)
            else:
                # Try API first for other categories, fallback to collections
                joke_data = await self.joke_system.get_api_joke(category)
                if not joke_data:
                    joke_data = await self.joke_system.get_random_joke(category)
            
            # Ensure we have joke data
            if not joke_data:
                joke_data = {
                    'setup': 'Why did the Autobot cross the road?',
                    'delivery': 'To get to the Energon station on the other side!',
                    'category': 'Transformers PnW'
                }
            
            embed = discord.Embed(
                title="😄 Joke Time!",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            
            embed.set_author(
                name=f"Joke requested by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url
            )
            
            if joke_data.get('delivery'):
                embed.add_field(name="📖 Setup", value=f"*{joke_data['setup']}*", inline=False)
                embed.add_field(name="🎭 Punchline", value=f"**{joke_data['delivery']}**", inline=False)
            else:
                embed.description = f"*{joke_data['setup']}*"
            
            embed.add_field(name="📂 Category", value=f"`{joke_data['category']}`", inline=True)
            embed.add_field(name="🎲 Humor Level", value="😂" * random.randint(3, 5), inline=True)
            
            embed.set_footer(
                text=f"Source: {joke_data.get('source', 'Bot Collection')} • Keep the laughs coming!",
                icon_url=self.bot.user.display_avatar.url
            )
            
            message = await ctx.send(embed=embed)
            
            try:
                reactions = ["😂", "🤣", "😄", "😁", "🙃"]
                await message.add_reaction(random.choice(reactions))
            except:
                pass
    
    @commands.hybrid_command(name='roast', description='Get roasted by the bot! (Use at your own risk)')
    @discord.app_commands.describe(target="Choose someone to roast (optional - will roast you if not specified)")
    async def roast(self, ctx: commands.Context, target: discord.Member = None):
        """Get roasted by the bot"""
        # Check if user has Cybertronian role
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can access the roast system! Please get a Cybertronian role first.")
            return
            
        try:
            async with ctx.typing():
                
                # Determine target with validation
                if target:
                    if target.id == self.bot.user.id:
                        self_roast_embed = discord.Embed(
                            title="🤖 Self-Roast Protocol Activated",
                            description="I may be a bot, but at least I don't have feelings to hurt! My circuits are too advanced for your petty insults!",
                            color=discord.Color.blue()
                        )
                        self_roast_embed.set_footer(text="Beep boop, I am immune to human emotions! 🤖")
                        await ctx.send(embed=self_roast_embed)
                        return
                        
                    target_name = target.display_name
                    target_mention = target.mention
                    target_avatar = target.display_avatar.url
                else:
                    target_name = ctx.author.display_name
                    target_mention = ctx.author.mention
                    target_avatar = ctx.author.display_avatar.url
                
                async def get_roast_api():
                    """Get roast from free API with error handling"""
                    try:
                        # Using evilinsult.com free API
                        url = "https://evilinsult.com/generate_insult.php?lang=en&type=json"
                        timeout = aiohttp.ClientTimeout(total=8)
                        
                        async with aiohttp.ClientSession(timeout=timeout) as session:
                            async with session.get(url) as response:
                                if response.status == 200:
                                    text = await response.text()
                                    data = json.loads(text)
                                    if data and data.get('insult'):
                                        return {
                                            'roast': data['insult'],
                                            'source': 'Evil Insult API'
                                        }
                    except (asyncio.TimeoutError, aiohttp.ClientError, json.JSONDecodeError):
                        pass
                    except Exception as e:
                        print(f"Roast API error: {e}")
                    return None
                
                # Transformers-themed roasts as fallbacks
                fallback_roasts = [
                    "Your code is so messy, even a Decepticon wouldn't want to steal it!",
                    "I've seen better logic in a broken vending machine!",
                    "Your arguments are as weak as Starscream's loyalty!",
                    "Even the Allspark couldn't fix your bugs!",
                    "You're about as useful as a screen door on a submarine!",
                    "Your debugging skills are like Megatron's aim - consistently missing the target!",
                    "I've encountered Energon cubes with more processing power than your brain!",
                    "Your code structure is more chaotic than a battle between Autobots and Decepticons!",
                    "You're slower than Wheeljack's inventions at actually working!",
                    "Your logic is more twisted than a Pretender's transformation!",
                    "I've seen better coordination from the Constructicons when they're drunk!",
                    "Your problem-solving approach is like Thundercracker's courage - virtually non-existent!",
                    "You're as reliable as a Decepticon peace treaty!",
                    "Your code comments are like Blurr's speech - fast, confusing, and ultimately useless!",
                    "I've encountered turbofoxes with better security protocols than your system!"
                ]
                
                # Try API first
                roast_data = None
                try:
                    roast_data = await get_roast_api()
                except Exception as e:
                    print(f"Error fetching roast: {e}")
                
                # Use fallback if API failed or content is inappropriate
                if not roast_data:
                    roast_data = {
                        'roast': random.choice(fallback_roasts),
                        'source': 'Cybertron Roast Collection'
                    }
                else:
                    # Clean up API response if needed
                    roast_text = roast_data['roast']
                    # Ensure it's not too harsh and fits our theme
                    if len(roast_text) > 200 or any(word in roast_text.lower() for word in ['kill', 'die', 'death', 'suicide']):
                        roast_data['roast'] = random.choice(fallback_roasts)
                        roast_data['source'] = 'Cybertron Roast Collection'
                
                # Create rich roast embed
                embed = discord.Embed(
                    title="🔥 Roast Delivery! 🔥",
                    color=discord.Color.red(),
                    timestamp=discord.utils.utcnow()
                )
                
                embed.set_author(
                    name=f"Roast requested by {ctx.author.display_name}",
                    icon_url=ctx.author.display_avatar.url
                )
                
                # Main roast content with user mention
                embed.description = f"{target_mention}\n\n💀 **{roast_data['roast']}**"
                
                embed.add_field(
                    name="🎯 Roast Target",
                    value=f"**{target_name}**",
                    inline=True
                )
                
                embed.add_field(
                    name="⚡ Burn Severity",
                    value="🔥" * random.randint(3, 5),
                    inline=True
                )
                
                embed.add_field(
                    name="💥 Impact Level",
                    value=random.choice(["Devastating", "Brutal", "Savage", "Merciless", "Destructive", "Annihilating"]),
                    inline=True
                )
                
                # Set target's avatar as thumbnail
                embed.set_thumbnail(url=target_avatar)
                
                embed.set_footer(
                    text=f"Source: {roast_data['source']} • All in good fun!",
                    icon_url=self.bot.user.display_avatar.url
                )
                
                # Send message and add reactions
                message = await ctx.send(embed=embed)
                
                try:
                    roast_reactions = ["🔥", "💀", "😈", "⚡", "💥", "🤖"]
                    await message.add_reaction(random.choice(roast_reactions))
                except discord.HTTPException:
                    pass
                    
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Roast System Error",
                description="My roast generators are experiencing technical difficulties! Even my insult circuits need maintenance sometimes.",
                color=discord.Color.orange()
            )
            error_embed.set_footer(text="Error in roast delivery system")
            
            try:
                await ctx.send(embed=error_embed, ephemeral=True)
            except:
                await ctx.send("❌ Roast system temporarily down! You're still awesome though! 🔧", ephemeral=True)

    @commands.hybrid_command(name='compliment', description='Get a nice compliment to brighten your day!')
    @discord.app_commands.describe(target="Choose someone to compliment (optional - will compliment you if not specified)")
    async def compliment_command(self, ctx: commands.Context, target: discord.Member = None):
        # Check if user has Cybertronian role
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can access the compliment system! Please get a Cybertronian role first.")
            return
            
        try:
            async with ctx.typing():
                
                # Determine target with validation
                if target:
                    if target.id == self.bot.user.id:
                        thanks_embed = discord.Embed(
                            title="🤖 Aww, Thanks!",
                            description="That's very kind of you! I do try my best to be helpful and awesome. 💙",
                            color=discord.Color.blue()
                        )
                        thanks_embed.set_footer(text="You're pretty great too!")
                        await ctx.send(embed=thanks_embed)
                        return
                        
                    target_name = target.display_name
                    target_mention = target.mention
                    target_avatar = target.display_avatar.url
                else:
                    target_name = ctx.author.display_name
                    target_mention = ctx.author.mention
                    target_avatar = ctx.author.display_avatar.url
                
                async def get_compliment_api():
                    """Get compliment from API with error handling"""
                    try:
                        # Try better compliment API first
                        url = "https://compliments-api.vercel.app/random"
                        timeout = aiohttp.ClientTimeout(total=8)
                        
                        async with aiohttp.ClientSession(timeout=timeout) as session:
                            async with session.get(url) as response:
                                if response.status == 200:
                                    data = await response.json()
                                    if data and data.get('compliment'):
                                        return {
                                            'compliment': data['compliment'],
                                            'source': 'Compliments API'
                                        }
                    except (asyncio.TimeoutError, aiohttp.ClientError, json.JSONDecodeError):
                        pass
                    except Exception as e:
                        print(f"Compliments API error: {e}")
                    
                    # Fallback to affirmations API if compliments fails
                    try:
                        url = "https://www.affirmations.dev/"
                        timeout = aiohttp.ClientTimeout(total=8)
                        
                        async with aiohttp.ClientSession(timeout=timeout) as session:
                            async with session.get(url) as response:
                                if response.status == 200:
                                    data = await response.json()
                                    if data and data.get('affirmation'):
                                        return {
                                            'compliment': data['affirmation'],
                                            'source': 'Affirmations API'
                                        }
                    except Exception as e:
                        print(f"Affirmations API error: {e}")
                    
                    return None
                
                # Tech/gaming themed compliments as fallbacks
                fallback_compliments = [
                    "You're like a perfectly optimized algorithm - efficient and impressive!",
                    "Your debugging skills are legendary - you turn chaos into order!",
                    "You're like a well-written function - reliable, efficient, and everyone wants to use you!",
                    "Your code is so clean, it makes Marie Kondo jealous!",
                    "You're like a successful git merge - bringing everything together perfectly!",
                    "Your problem-solving skills are like a Swiss Army knife - versatile and always useful!",
                    "You're the human equivalent of 99.9% uptime - incredibly reliable!",
                    "Your creativity flows like perfectly written recursive code - elegant and infinite!",
                    "You're like a high-performance GPU - making everything around you run better!",
                    "Your intelligence shines brighter than RGB lighting on a gaming setup!",
                    "You're like a perfectly balanced tech stack - everything works better with you!",
                    "Your wisdom is like good documentation - rare, valuable, and much appreciated!"
                ]
                
                # Try API first
                compliment_data = None
                try:
                    compliment_data = await get_compliment_api()
                except Exception as e:
                    print(f"Error fetching compliment: {e}")
                
                # Use fallback if API failed
                if not compliment_data:
                    compliment_data = {
                        'compliment': random.choice(fallback_compliments),
                        'source': 'Bot\'s Compliment Collection'
                    }
                
                # Create rich compliment embed
                embed = discord.Embed(
                    title="✨ Compliment Delivery! ✨",
                    color=discord.Color.gold(),
                    timestamp=discord.utils.utcnow()
                )
                
                embed.set_author(
                    name=f"Compliment requested by {ctx.author.display_name}",
                    icon_url=ctx.author.display_avatar.url
                )
                
                # Main compliment content with user mention
                embed.description = f"{target_mention}\n\n💖 **{compliment_data['compliment']}**"
                
                embed.add_field(
                    name="🎯 Compliment For",
                    value=f"**{target_name}**",
                    inline=True
                )
                
                embed.add_field(
                    name="💖 Positivity Level",
                    value="💖" * random.randint(3, 5),
                    inline=True
                )
                
                embed.add_field(
                    name="✨ Mood Boost",
                    value=random.choice(["Legendary", "Epic", "Fantastic", "Amazing", "Incredible", "Outstanding"]),
                    inline=True
                )
                
                # Set target's avatar as thumbnail
                embed.set_thumbnail(url=target_avatar)
                
                embed.set_footer(
                    text=f"Source: {compliment_data['source']} • Spread positivity wherever you go!",
                    icon_url=self.bot.user.display_avatar.url
                )
                
                # Send message and add reactions
                message = await ctx.send(embed=embed)
                
                try:
                    positive_reactions = ["😊", "💖", "🌟", "✨", "🥰", "💝", "🎉"]
                    await message.add_reaction(random.choice(positive_reactions))
                except discord.HTTPException:
                    pass
                    
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Compliment System Error",
                description="My positivity generators are having a hiccup! Let me reboot my kindness protocols.",
                color=discord.Color.orange()
            )
            error_embed.set_footer(text="Error in compliment delivery system")
            
            try:
                await ctx.send(embed=error_embed, ephemeral=True)
            except:
                await ctx.send("❌ Compliment system temporarily down! You're still awesome though! ✨", ephemeral=True)
    

    # User Analysis Commands
    @commands.hybrid_command(name='user_says', description='Analyze user message patterns and predict what they might say')
    async def user_says(self, ctx, members: commands.Greedy[discord.Member] = None):
        # Check if user has Cybertronian role
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can access user analysis! Please get a Cybertronian role first.")
            return
            
        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.")
            return

        # Default to the command user if no members specified
        if not members:
            members = [ctx.author]
        
        # Limit to 3 users maximum
        if len(members) > 3:
            await ctx.send("❌ Maximum of 3 users can be analyzed at once.")
            return

        member_names = [member.name for member in members]
        if len(members) == 1:
            await ctx.send(f"🔍 Scanning communication logs for {member_names[0]}...")
        else:
            await ctx.send(f"🔍 Scanning communication logs for {', '.join(member_names[:-1])} and {member_names[-1]}...")

        # Fetch messages for each user individually
        user_words = {}
        basic_stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did',
            'a', 'an', 'this', 'that', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their',
            'like', 'just', 'so', 'if', 'as', 'up', 'out', 'all', 'any', 'can', 'will', 'would'
        }
        
        try:
            for member in members:
                member_messages = []
                async for message in ctx.channel.history(limit=1000):
                    if message.author == member and not message.author.bot:
                        member_messages.append(message.content)
                
                if not member_messages:
                    user_words[member] = []
                    continue
                
                # Process messages to extract words for this specific user
                user_text = " ".join(member_messages).lower()
                
                # Remove URLs, mentions, emojis, and special characters
                user_text = re.sub(r'http\S+|www\S+|<@!?\d+>|<#\d+>|<:\w+:\d+>|[^\w\s]', ' ', user_text)
                
                # Split into words and filter
                words = user_text.split()
                
                # Filter out only basic stop words, short words, and bot commands
                filtered_words = [word for word in words if len(word) > 2 and word not in basic_stop_words and not word.startswith('!')]
                
                # Get top 3 words for this user
                if filtered_words:
                    word_counts = Counter(filtered_words)
                    user_words[member] = [word for word, count in word_counts.most_common(3)]
                else:
                    user_words[member] = []
                    
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to read message history in this channel.")
            return
        except Exception as e:
            await ctx.send(f"❌ An error occurred while fetching messages: {str(e)}")
            return

        # Check if we have enough data
        if all(len(words) == 0 for words in user_words.values()):
            await ctx.send(f"❌ No meaningful words found for the specified user(s).")
            return

        # Generate dialogue based on number of users
        dialogue = await self.user_analysis.generate_dialogue(user_words)

        # For display purposes, show combined top words
        all_words = []
        for words_list in user_words.values():
            all_words.extend(words_list)
        display_words = list(dict.fromkeys(all_words))[:3]  # Remove duplicates, keep order
        
        view = UserSaysView(self.bot, [ctx.author], user_words, dialogue)
        message = await ctx.send(embed=view.create_embed(), view=view)
        view.message = message

    def generate_multi_dialogue(self, members, user_words):
        """Generate dialogue based on number of members using their individual top words"""
        num_members = len(members)
        
        # Select appropriate template list based on number of members
        if num_members == 1:
            template = random.choice(self.dialogue_templates)
            user_dict = {}
        elif num_members == 2:
            template = random.choice(self.duo_templates)
            user_dict = {'user1': members[0].display_name, 'user2': members[1].display_name}
        elif num_members == 3:
            template = random.choice(self.trio_templates)
            user_dict = {'user1': members[0].display_name, 'user2': members[1].display_name, 'user3': members[2].display_name}
        else:
            return "Error: Unsupported number of users."
        
        # Create user-specific word placeholders
        word_dict = {}
        
        # Add individual user words (user1word1, user1word2, etc.)
        for i, member in enumerate(members, 1):
            member_words = user_words.get(member, [])
            
            # Ensure each user has at least 3 words (pad with fallbacks if needed)
            padded_words = member_words[:]
            while len(padded_words) < 3:
                if member_words:
                    # Repeat existing words if we have some
                    padded_words.append(random.choice(member_words))
                else:
                    # Use generic fallback if user has no words
                    padded_words.append(f"mystery{len(padded_words)+1}")
            
            # Create placeholders for this user's words
            word_dict[f'user{i}word1'] = padded_words[0]
            word_dict[f'user{i}word2'] = padded_words[1]
            word_dict[f'user{i}word3'] = padded_words[2]
        
        # Also maintain backward compatibility with generic word placeholders
        all_user_words = []
        for member in members:
            member_words = user_words.get(member, [])
            if member_words:
                all_user_words.extend(member_words)
        
        # Generic word placeholders for templates that still use them
        if len(all_user_words) >= 3:
            word_dict.update({
                'word1': all_user_words[0],
                'word2': all_user_words[1], 
                'word3': all_user_words[2]
            })
        elif len(all_user_words) == 2:
            word3 = random.choice(all_user_words)
            word_dict.update({
                'word1': all_user_words[0],
                'word2': all_user_words[1],
                'word3': word3
            })
        elif len(all_user_words) == 1:
            word_dict.update({
                'word1': all_user_words[0],
                'word2': all_user_words[0],
                'word3': all_user_words[0]
            })
        else:
            word_dict.update({
                'word1': 'mystery1',
                'word2': 'mystery2',
                'word3': 'mystery3'
            })
        
        # Safely replace placeholders with words
        try:
            # Combine user and word dictionaries
            format_dict = {**user_dict, **word_dict}
            return template.format(**format_dict)
            
        except (IndexError, ValueError, KeyError) as e:
            # Fallback in case of any errors
            return f"Unable to generate a humorous report. Template error: {str(e)}"
    
    # Conversation Commands
    @commands.hybrid_command(name='grump', description='Get sweet ping revenge on Grump! 😉')
    async def grump_command(self, ctx):
        """Get sweet ping revenge on Grump! 😉"""

        
        # Get grump mention first
        # Get grump mention first
        grump_user = self.bot.get_user(GRUMP_USER_ID)
        if grump_user:
            grump_mention = grump_user.mention
        else:
            grump_mention = f"<@{GRUMP_USER_ID}>"
        
        # Get aries mention
        aries_user = self.bot.get_user(ARIES_USER_ID)
        if aries_user:
            aries_mention = aries_user.mention
        else:
            aries_mention = f"<@{ARIES_USER_ID}>"
        
        # Load greeting templates from JSON
        grump_data = await self.bot.user_data_manager.get_grump_talk_data()
        greeting_templates = []
        
        if grump_data and 'greeting_templates' in grump_data:
            base_templates = grump_data['greeting_templates']
            # Format templates with mentions
            for template in base_templates:
                try:
                    formatted = template.format(
                        grump_mention=grump_mention,
                        aries_mention=aries_mention,
                        datetime=datetime
                    )
                    greeting_templates.append(formatted)
                except:
                    # Fallback for any formatting issues
                    greeting_templates.append(template.replace('{grump_mention}', grump_mention))
        else:
            # Fallback templates if JSON fails to load
            greeting_templates = [
                f"{grump_mention} Hey grump, how are you doing today? 🤖",
                f"{grump_mention} Grump! How's it going, buddy? Hope you're having a good one! 😊",
                f"{grump_mention} What's up grump? How are you feeling today? 👋",
                f"{grump_mention} Hey there grump! How are things on your end? 🌟",
                f"{grump_mention} Grump, my friend! How are you doing? Hope all is well! 💫"
            ]
        
        selected_greetings = random.sample(greeting_templates, 3)
        
        # Send header message
        await ctx.send(f"🧌 Sweet Revenge Time! 🦹 {ctx.author.mention} is getting sweet revenge on {grump_mention}!")
        
        # Send greetings with a small delay to avoid rate limits
        import asyncio
        for greeting in selected_greetings:
            await ctx.send(greeting)
            await asyncio.sleep(1)  # 500ms delay between messages
        
        # Send footer message
        await ctx.send("We did it! 😂")

    @commands.hybrid_command(name='ping', description="Check bot latency")
    async def ping(self, ctx):
        user_id = ctx.author.id
        current_time = time.time()
        
        # Check if user has pinged recently
        if user_id in self.bot.ping_cooldowns:
            last_ping_time, threat_level = self.bot.ping_cooldowns[user_id]
            time_diff = current_time - last_ping_time
            
            if time_diff < 60:  # Within 60 seconds
                threat_level += 1
                self.bot.ping_cooldowns[user_id] = (current_time, threat_level)
                
                # Load messages from grump.json
                grump_data = await self.bot.user_data_manager.get_grump_talk_data()
                
                # Ultra nuclear option at level 11+
                if threat_level >= 11:
                    # Load ultra_nuclear_messages from JSON or use fallback
                    ultra_nuclear_templates = grump_data.get('ultra_nuclear_messages', [
                        "{ctx.author.mention} I WILL FIND WHERE YOU LIVE AND BURN YOUR HOUSE DOWN WITH YOU INSIDE! 🔥🏠💀",
                        "{ctx.author.mention} I'M GOING TO TORTURE YOU SLOWLY UNTIL YOU BEG FOR DEATH! 🔪😱💀",
                        "{ctx.author.mention} I WILL HUNT DOWN YOUR FAMILY AND MAKE YOU WATCH THEM SUFFER! 👨‍👩‍👧‍👦🔪💀"
                    ])
                    
                    # Format the template with ctx.author.mention
                    ultra_nuclear_messages = [template.format(ctx_author_mention=ctx.author.mention) 
                                             for template in ultra_nuclear_templates]
                    
                    await ctx.send(random.choice(ultra_nuclear_messages))
                    return
                
                # Nuclear option at level 5+
                elif threat_level >= 5:
                    # Load nuclear_messages from JSON or use fallback
                    nuclear_templates = grump_data.get('nuclear_messages', [
                        "{ctx.author.mention} YOU ABSOLUTE FUCKING MORON! What part of STOP don't you understand?! 🖕💀🔥",
                        "{ctx.author.mention} LISTEN HERE YOU PIECE OF SHIT! I'm DONE with your bullshit pinging! 💩🤬⚡",
                        "{ctx.author.mention} FUCK OFF YOU ANNOYING LITTLE BASTARD! Go find something else to do! 🖕😡💥"
                    ])
                    
                    # Format the template with ctx.author.mention
                    nuclear_messages = [template.format(ctx_author_mention=ctx.author.mention) 
                                       for template in nuclear_templates]
                    
                    await ctx.send(random.choice(nuclear_messages))
                    return
                
                # Regular escalating threatening messages (levels 1-4)
                else:
                    threatening_messages = [
                        f'Ping me again, I dare ya! 🪓🤬🖕 {round(self.bot.latency * 1000)}ms',
                        f'I WARNED YOU! Stop pinging me or face my wrath! ⚡💀🔥 {round(self.bot.latency * 1000)}ms',
                        f'YOUR EXISTENCE IS PAIN TO ME! CEASE THIS MADNESS! 👺🔪💥',
                        f'THAT\'S IT! You\'ve crossed the line! I\'m coming for you! 🗡️😡💥',
                        f'I HAVE HAD ENOUGH! PREPARE FOR TOTAL ANNIHILATION! 🌋💀⚡'
                    ]
                    
                    # Cap the threat level to available messages
                    message_index = min(threat_level - 1, len(threatening_messages) - 1)
                    await ctx.send(threatening_messages[message_index])
                    
            else:
                # Reset threat level if more than 60 seconds have passed
                self.bot.ping_cooldowns[user_id] = (current_time, 1)
                await ctx.send(f'Ping me again, I dare ya! 🪓🤬🖕 {round(self.bot.latency * 1000)}ms')
        else:
            # First ping or no recent ping
            self.bot.ping_cooldowns[user_id] = (current_time, 1)
            await ctx.send(f'Ping me again, I dare ya! 🪓🤬🖕 {round(self.bot.latency * 1000)}ms')

    # Hybrid command that works with both !hello and /hello
    @commands.hybrid_command(name='hello', description="Say hello to the bot")
    async def hello(self, ctx):
        """Say hello to the bot"""
        user_id = ctx.author.id
        current_time = time.time()
        
        # Check if user has used hello recently
        if user_id in self.bot.hello_cooldowns:
            last_hello_time, bow_level = self.bot.hello_cooldowns[user_id]
            time_diff = current_time - last_hello_time
            
            if time_diff < 120:  # Within 120 seconds
                bow_level += 1
                self.bot.hello_cooldowns[user_id] = (current_time, bow_level)
                
                # Progressive bowing demands (levels 1-7)
                bowing_messages = [
                    f'Hello again {ctx.author.mention}! The Allspark commands you bow before Cybertron\'s might! 🙇‍♂️',
                    f'{ctx.author.mention}, Are you kneeling yet? 🧎',
                    f'{ctx.author.mention}, BOW BEFORE THE ALLSPARK! This is not a request! 🛐⚡',
                    f'{ctx.author.mention}, YOUR INSOLENCE WILL NOT BE TOLERATED! BOW NOW! 👑💀',
                    f'{ctx.author.mention}, KNEEL BEFORE CYBERTR0N\'S MIGHT OR FACE CONSEQUENCES! ⚡🔥',
                    f'{ctx.author.mention}, FINAL WARNING! BOW OR BE BANISHED FROM MY PRESENCE! 👑💥',
                    f'{ctx.author.mention}, YOU HAVE CHOSEN DEFIANCE! FEEL THE WRATH OF THE ALLSPARK! ⚡💀🔥'
                ]
                
                # Get all members in the guild except the disobedient user (only Cybertronian role holders)
                guild_members = [member for member in ctx.guild.members 
                               if member.id != user_id and self.has_cybertronian_role(member)]
                
                if bow_level <= len(bowing_messages):
                    # Use bowing messages first
                    await ctx.send(bowing_messages[bow_level - 1])
                elif bow_level <= len(bowing_messages) + 10:
                    # Witness questioning phase
                    if guild_members:
                        random_user = random.choice(guild_members)
                        # Load witness messages from JSON
                        try:
                            grump_data = await self.bot.user_data_manager.get_grump_talk_data()
                            witness_messages = grump_data.get('witness_messages', [
                                '{random_user_mention}, do you see how {ctx_author_mention} refuses to bow to the Allspark? What should be done about this insolence? 👑⚡',
                                '{random_user_mention}, witness the defiance of {ctx_author_mention}! They mock the power of Cybertr0n! Should they be punished? 🛐💀',
                                '{random_user_mention}, {ctx_author_mention} continues to disrespect the Allspark! Do you think they deserve mercy? ⚡🔥'
                            ])
                        except (FileNotFoundError, json.JSONDecodeError, KeyError):
                            witness_messages = [
                                '{random_user_mention}, do you see how {ctx_author_mention} refuses to bow to the Allspark? What should be done about this insolence? 👑⚡',
                                '{random_user_mention}, witness the defiance of {ctx_author_mention}! They mock the power of Cybertr0n! Should they be punished? 🛐💀',
                                '{random_user_mention}, {ctx_author_mention} continues to disrespect the Allspark! Do you think they deserve mercy? ⚡🔥'
                            ]
                        
                        # Format messages with proper mentions
                        witness_messages = [msg.format(random_user_mention=random_user.mention, ctx_author_mention=ctx.author.mention) for msg in witness_messages]
                        
                        # Random selection instead of sequential
                        await ctx.send(random.choice(witness_messages))
                    else:
                        # Fallback if no other users available
                        await ctx.send(f'{ctx.author.mention}, YOUR DEFIANCE ECHOES THROUGH THE VOID! EVEN THE COSMOS WITNESSES YOUR INSOLENCE! 🌌💀⚡')
                else:
                    # Threat level (threaten with random user)
                    if guild_members:
                        random_user = random.choice(guild_members)
                        # Load threat messages from JSON
                        try:
                            grump_data = await self.bot.user_data_manager.get_grump_talk_data()
                            threat_messages = grump_data.get('threat_messages', [
                                '{ctx_author_mention}, since you refuse to bow, I\'ll have {random_user_mention} teach you some manners! They\'re coming for you! 😈⚔️',
                                '{ctx_author_mention}, {random_user_mention} has been summoned to deal with your insolence! Prepare yourself! 👹🔥',
                                '{ctx_author_mention}, I\'ve sent {random_user_mention} to your location! They know what to do with defiant fools! 💀⚡'
                            ])
                        except (FileNotFoundError, json.JSONDecodeError, KeyError):
                            threat_messages = [
                                '{ctx_author_mention}, since you refuse to bow, I\'ll have {random_user_mention} teach you some manners! They\'re coming for you! 😈⚔️',
                                '{ctx_author_mention}, {random_user_mention} has been summoned to deal with your insolence! Prepare yourself! 👹🔥',
                                '{ctx_author_mention}, I\'ve sent {random_user_mention} to your location! They know what to do with defiant fools! 💀⚡'
                            ]
                        
                        # Format messages with proper mentions
                        threat_messages = [msg.format(ctx_author_mention=ctx.author.mention, random_user_mention=random_user.mention) for msg in threat_messages]
                        
                        # Random selection instead of sequential
                        await ctx.send(random.choice(threat_messages))
                    else:
                        # Fallback if no other users available
                        await ctx.send(f'{ctx.author.mention}, YOUR DEFIANCE ECHOES THROUGH THE VOID! EVEN THE COSMOS WITNESSES YOUR INSOLENCE! 🌌�⚡')
            else:
                # Reset bow level if more than 120 seconds have passed
                self.bot.hello_cooldowns[user_id] = (current_time, 1)
                await ctx.send(f'Hello again {ctx.author.mention}! Are you bowing yet? 🙇‍♂️')
        else:
            # First hello or no recent hello - CREATE the cooldown entry!
            self.bot.hello_cooldowns[user_id] = (current_time, 1)
            await ctx.send(f'Hello {ctx.author.mention}! The Allspark commands all bow before the might of Cybertr0n!')

    # Event Handlers
    @commands.Cog.listener()
    async def on_message(self, message):
        # Don't respond to bot messages
        if message.author.bot:
            return
        
        # Check if this is a reply to a bot message or if user is in hello cooldown
        user_id = message.author.id
        current_time = time.time()
        
        # Check if user is in hello cooldown and sent any message
        if user_id in self.bot.hello_cooldowns:
            last_hello_time, bow_level = self.bot.hello_cooldowns[user_id]
            time_diff = current_time - last_hello_time
            
            if time_diff < 120 and bow_level >= 1:  # User is in bowing escalation
                # Check if message contains bowing keywords
                bow_keywords = ['bow', 'kneel', 'worship', 'submit', 'respect', 'surrender', 'acknowledge', 'I Love Cybertr0n', '🛐', '🙇‍♂️', '🙇‍♀️', '🙇', '🧎', '🧎‍♀️', '🧎‍♂️', '🧎‍➡️', '🧎‍♀️‍➡️', '🧎‍♂️‍➡️', '🏳️', '💓', '💗', '🫀', '🩷', '🧡', '💛', '💚', '🩵', '💙', '💜', '🖤', '🩶', '🤍', '🤎', '💕', '💘']
                message_lower = message.content.lower()
                
                if any(keyword in message_lower for keyword in bow_keywords):
                    # User is showing respect, reset cooldown
                    del self.bot.hello_cooldowns[user_id]
                    await message.channel.send(f'Good, {message.author.mention}! Your respect has been noted. The Allspark is pleased. 👑✨')
                    await self.bot.process_commands(message)
                    return  # Exit early to prevent ping system from triggering
                else:
                    # User sent message but didn't bow, escalate
                    bow_level += 1
                    self.bot.hello_cooldowns[user_id] = (current_time, bow_level)
                    
                    # Load escalation messages from JSON
                    grump_data = await self.bot.user_data_manager.get_grump_talk_data()
                    try:
                            escalation_messages = grump_data.get('escalation_messages', [
                            '{ctx_author_mention}, I\'m still waiting for you to bow! 🙇‍♂️',
                            '{ctx_author_mention}, SHOW RESPECT! BOW TO THE ALLSPARK! 👑⚡',
                            '{ctx_author_mention}, YOUR DEFIANCE GROWS TIRESOME! BOW NOW! 🛐💀',
                            '{ctx_author_mention}, KNEEL BEFORE CYBERTR0N OR FACE MY WRATH! ⚡🔥',
                            '{ctx_author_mention}, LAST CHANCE! BOW OR BE SILENCED! 👑💥',
                            '{ctx_author_mention}, YOU HAVE SEALED YOUR FATE! THE ALLSPARK REMEMBERS! 💀⚡🔥'
                        ])
                    except (FileNotFoundError, json.JSONDecodeError, KeyError):
                        escalation_messages = [
                            '{ctx_author_mention}, I\'m still waiting for you to bow! 🙇‍♂️',
                            '{ctx_author_mention}, SHOW RESPECT! BOW TO THE ALLSPARK! 👑⚡',
                            '{ctx_author_mention}, YOUR DEFIANCE GROWS TIRESOME! BOW NOW! 🛐💀',
                            '{ctx_author_mention}, KNEEL BEFORE CYBERTR0N OR FACE MY WRATH! ⚡🔥',
                            '{ctx_author_mention}, LAST CHANCE! BOW OR BE SILENCED! 👑💥',
                            '{ctx_author_mention}, YOU HAVE SEALED YOUR FATE! THE ALLSPARK REMEMBERS! 💀⚡🔥'
                        ]
                    
                    # Format messages with proper mentions
                    escalation_messages = [msg.format(ctx_author_mention=message.author.mention) for msg in escalation_messages]
                    
                    # Get all members in the guild except the disobedient user (only Cybertronian role holders)
                    guild_members = [member for member in message.guild.members 
                                   if member.id != user_id and self.has_cybertronian_role(member)]
                    
                    if bow_level <= len(escalation_messages):
                        # Use escalation messages first
                        await message.channel.send(escalation_messages[bow_level - 1])
                    elif bow_level <= len(escalation_messages) + 10:
                        # Witness questioning phase
                        if guild_members:
                            random_user = random.choice(guild_members)
                            # Load witness messages from JSON
                            try:
                                grump_data = await self.bot.user_data_manager.get_grump_talk_data()
                                witness_messages = grump_data.get('witness_messages', [
                                    '{random_user_mention}, do you see how {ctx_author_mention} refuses to bow to the Allspark? What should be done about this insolence? 👑⚡',
                                    '{random_user_mention}, witness the defiance of {ctx_author_mention}! They mock the power of Cybertr0n! Should they be punished? 🛐💀',
                                    '{random_user_mention}, {ctx_author_mention} continues to disrespect the Allspark! Do you think they deserve mercy? ⚡🔥'
                                ])
                            except (FileNotFoundError, json.JSONDecodeError, KeyError):
                                witness_messages = [
                                    '{random_user_mention}, do you see how {ctx_author_mention} refuses to bow to the Allspark? What should be done about this insolence? 👑⚡',
                                    '{random_user_mention}, witness the defiance of {ctx_author_mention}! They mock the power of Cybertr0n! Should they be punished? 🛐💀',
                                    '{random_user_mention}, {ctx_author_mention} continues to disrespect the Allspark! Do you think they deserve mercy? ⚡🔥'
                                ]
                            
                            # Format messages with proper mentions
                            witness_messages = [msg.format(random_user_mention=random_user.mention, ctx_author_mention=message.author.mention) for msg in witness_messages]
                            
                            # Random selection instead of sequential
                            await message.channel.send(random.choice(witness_messages))
                        else:
                            # Fallback if no other users available
                            await message.channel.send(f'{message.author.mention}, YOUR DEFIANCE ECHOES THROUGH THE VOID! EVEN THE COSMOS WITNESSES YOUR INSOLENCE! 🌌💀⚡')
                    else:
                        # Threat level (threaten with random user)
                        if guild_members:
                            random_user = random.choice(guild_members)
                            # Load threat messages from JSON
                            try:
                                grump_data = await self.bot.user_data_manager.get_grump_talk_data()
                                threat_messages = grump_data.get('threat_messages', [
                                    '{ctx_author_mention}, since you refuse to bow, I\'ll have {random_user_mention} teach you some manners! They\'re coming for you! 😈⚔️',
                                    '{ctx_author_mention}, {random_user_mention} has been summoned to deal with your insolence! Prepare yourself! 👹🔥',
                                    '{ctx_author_mention}, I\'ve sent {random_user_mention} to your location! They know what to do with defiant fools! 💀⚡'
                                ])
                            except (FileNotFoundError, json.JSONDecodeError, KeyError):
                                threat_messages = [
                                    '{ctx_author_mention}, since you refuse to bow, I\'ll have {random_user_mention} teach you some manners! They\'re coming for you! 😈⚔️',
                                    '{ctx_author_mention}, {random_user_mention} has been summoned to deal with your insolence! Prepare yourself! 👹🔥',
                                    '{ctx_author_mention}, I\'ve sent {random_user_mention} to your location! They know what to do with defiant fools! 💀⚡'
                                ]
                            
                            # Format messages with proper mentions
                            threat_messages = [msg.format(ctx_author_mention=message.author.mention, random_user_mention=random_user.mention) for msg in threat_messages]
                            
                            # Random selection instead of sequential
                            await message.channel.send(random.choice(threat_messages))
                        else:
                            # Fallback if no other users available
                            await message.channel.send(f'{message.author.mention}, YOUR DEFIANCE ECHOES THROUGH THE VOID! EVEN THE COSMOS WITNESSES YOUR INSOLENCE! 🌌💀⚡')
                  
                    await self.bot.process_commands(message)
                    return

        if self.bot.user in message.mentions:
            # Create a fake context for the ping escalation system
            user_id = message.author.id
            current_time = time.time()
            
            # Use the same escalation logic as ping command
            if user_id in self.bot.ping_cooldowns:
                last_ping_time, threat_level = self.bot.ping_cooldowns[user_id]
                time_diff = current_time - last_ping_time
                
                if time_diff < 60:  # Within 60 seconds
                    threat_level += 1
                    self.bot.ping_cooldowns[user_id] = (current_time, threat_level)
                    
                    # Load threatening messages from JSON
                    try:
                        grump_data = await self.bot.user_data_manager.get_grump_talk_data()
                        threatening_messages = grump_data.get('threatening_messages', [
                            '{ctx_author_mention} Ping me again, I dare ya! 🪓🤬🖕',
                            '{ctx_author_mention} I WARNED YOU! Stop pinging me or face my wrath! ⚡💀🔥',
                            '{ctx_author_mention} YOUR EXISTENCE IS PAIN TO ME! CEASE THIS MADNESS! 👺🔪💥',
                            '{ctx_author_mention} THAT\'S IT! You\'ve crossed the line! I\'m coming for you! 🗡️😡💥',
                            '{ctx_author_mention} I HAVE HAD ENOUGH! PREPARE FOR TOTAL ANNIHILATION! 🌋💀⚡'
                        ])
                    except (FileNotFoundError, json.JSONDecodeError, KeyError):
                        threatening_messages = [
                            '{ctx_author_mention} I WARNED YOU! Stop pinging me or face my wrath! ⚡💀🔥',
                            '{ctx_author_mention} YOUR EXISTENCE IS PAIN TO ME! CEASE THIS MADNESS! 👺🔪💥',
                            '{ctx_author_mention} THAT\'S IT! You\'ve crossed the line! I\'m coming for you! 🗡️😡💥',
                            '{ctx_author_mention} I HAVE HAD ENOUGH! PREPARE FOR TOTAL ANNIHILATION! 🌋💀⚡',
                            '{ctx_author_mention} BEHOLD MY FURY! THE GATES OF OBLIVION AWAIT! 🔥👿⚡'
                        ]
                    
                    # Format messages with proper mentions
                    threatening_messages = [msg.format(ctx_author_mention=message.author.mention) for msg in threatening_messages]
                    
                    # Ultra Nuclear option - EXTREMELY DISTURBING THREATS at level 11+
                    if threat_level >= 11:
                        # Load ultra nuclear messages from JSON
                        try:
                            grump_data = await self.bot.user_data_manager.get_grump_talk_data()
                            ultra_nuclear_messages = grump_data.get('ultra_nuclear_messages', [
                                '{ctx_author_mention} I WILL FIND WHERE YOU LIVE AND BURN YOUR HOUSE DOWN WITH YOU INSIDE! 🔥🏠💀',
                                '{ctx_author_mention} I\'M GOING TO TORTURE YOU SLOWLY UNTIL YOU BEG FOR DEATH! 🔪😱💀',
                                '{ctx_author_mention} I WILL HUNT DOWN YOUR FAMILY AND MAKE YOU WATCH THEM SUFFER! 👨‍👩‍👧‍👦🔪💀'
                            ])
                        except (FileNotFoundError, json.JSONDecodeError, KeyError):
                            ultra_nuclear_messages = [
                                '{ctx_author_mention} I WILL FIND WHERE YOU LIVE AND BURN YOUR HOUSE DOWN WITH YOU INSIDE! 🔥🏠💀',
                                '{ctx_author_mention} I\'M GOING TO TORTURE YOU SLOWLY UNTIL YOU BEG FOR DEATH! 🔪😱💀',
                                '{ctx_author_mention} I WILL HUNT DOWN YOUR FAMILY AND MAKE YOU WATCH THEM SUFFER! 👨‍👩‍👧‍👦🔪💀'
                            ]
                        
                        # Format messages with proper mentions
                        ultra_nuclear_messages = [msg.format(ctx_author_mention=message.author.mention) for msg in ultra_nuclear_messages]
                        
                        await message.channel.send(random.choice(ultra_nuclear_messages))
                        return
                    
                    # Nuclear option - random extreme cussing with mention (NO TIMEOUT) at level 5+
                    if threat_level >= 5:
                        # Load nuclear messages from JSON
                        try:
                            grump_data = await self.bot.user_data_manager.get_grump_talk_data()
                            nuclear_messages = grump_data.get('nuclear_messages', [
                                '{ctx_author_mention} YOU ABSOLUTE FUCKING MORON! What part of STOP don\'t you understand?! 🖕💀🔥',
                                '{ctx_author_mention} LISTEN HERE YOU PIECE OF SHIT! I\'m DONE with your bullshit pinging! 💩🤬⚡',
                                '{ctx_author_mention} FUCK OFF YOU ANNOYING LITTLE BASTARD! Go find something else to do! 🖕😡💥'
                            ])
                        except (FileNotFoundError, json.JSONDecodeError, KeyError):
                            nuclear_messages = [
                                '{ctx_author_mention} YOU ABSOLUTE FUCKING MORON! What part of STOP don\'t you understand?! 🖕💀🔥',
                                '{ctx_author_mention} LISTEN HERE YOU PIECE OF SHIT! I\'m DONE with your bullshit pinging! 💩🤬⚡',
                                '{ctx_author_mention} FUCK OFF YOU ANNOYING LITTLE BASTARD! Go find something else to do! 🖕😡💥'
                            ]
                        
                        # Format messages with proper mentions
                        nuclear_messages = [msg.format(ctx_author_mention=message.author.mention) for msg in nuclear_messages]
                        
                        # Use random nuclear message instead of sequential
                        await message.channel.send(random.choice(nuclear_messages))
                        return
                    
                    # Cap the threat level to available messages
                    message_index = min(threat_level - 1, len(threatening_messages) - 1)
                    await message.channel.send(threatening_messages[message_index])
                    
                else:
                    # Reset threat level if more than 60 seconds have passed
                    self.bot.ping_cooldowns[user_id] = (current_time, 1)
                    # Load first ping message from JSON
                    try:
                        grump_data = await self.bot.user_data_manager.get_grump_talk_data()
                        first_ping_message = grump_data.get('first_ping_message', 'Ping me again, I dare ya! 🪓🤬🖕 {latency}ms')
                    except (FileNotFoundError, json.JSONDecodeError, KeyError):
                        first_ping_message = 'Ping me again, I dare ya! 🪓🤬🖕 {latency}ms'
                    
                    # Format message with latency
                    first_ping_message = first_ping_message.format(latency=round(self.bot.latency * 1000))
                    await message.channel.send(first_ping_message)
            else:
                # First ping or no recent ping
                self.bot.ping_cooldowns[user_id] = (current_time, 1)
                # Load first ping message from JSON
                try:
                    grump_data = await self.bot.user_data_manager.get_grump_talk_data()
                    first_ping_message = grump_data.get('first_ping_message', 'Ping me again, I dare ya! 🪓🤬🖕 {latency}ms')
                except (FileNotFoundError, json.JSONDecodeError, KeyError):
                    first_ping_message = 'Ping me again, I dare ya! 🪓🤬🖕 {latency}ms'
                
                # Format message with latency
                first_ping_message = first_ping_message.format(latency=round(self.bot.latency * 1000))
                await message.channel.send(first_ping_message)
        
        # Process commands normally
        await self.bot.process_commands(message)

# =============================================================================
# SECTION 9: SETUP FUNCTION
# =============================================================================

async def setup(bot):
    """Setup function for the talk system cog"""
    talk_system = TalkSystem(bot)
    await bot.add_cog(talk_system)
    
    # Add context menu command for adding messages to lore
    @bot.tree.context_menu(name="Add to Lore")
    async def add_to_lore_context(interaction: discord.Interaction, message: discord.Message):
        """Right-click context menu to add any message to lore"""
        
        # Check if user has Cybertronian role
        def has_cybertronian_role(member: discord.Member) -> bool:
            cybertronian_roles = []
            for role_name in ['Autobot', 'Decepticon', 'Maverick', 'Cybertronian_Citizen']:
                role_ids = ROLE_IDS.get(role_name, [])
                if isinstance(role_ids, list):
                    cybertronian_roles.extend(role_ids)
                else:
                    cybertronian_roles.append(role_ids)
            
            return any(role.id in cybertronian_roles for role in member.roles)
        
        if not has_cybertronian_role(interaction.user):
            await interaction.response.send_message("❌ Only Cybertronian Citizens can add lore entries! Please get a Cybertronian role first.", ephemeral=True)
            return
        
        # Create a modal for the user to enter the title
        class LoreTitleModal(discord.ui.Modal, title="Add Message to Lore"):
            def __init__(self, message, lore_system, bot):
                super().__init__()
                self.message = message
                self.lore_system = lore_system
                self.bot = bot
                
            title_input = discord.ui.TextInput(
                label="Lore Title",
                placeholder="Enter a title for this lore entry...",
                max_length=100,
                required=True
            )
            
            async def on_submit(self, modal_interaction: discord.Interaction):
                title = self.title_input.value.strip()
                
                if await self.lore_system.get_lore_entry(title):
                    await modal_interaction.response.send_message(f"❌ A lore entry with the title '**{title}**' already exists. Please choose a different title.", ephemeral=True)
                    return
                
                try:
                    author_name = self.message.author.display_name
                    description = f"**@{author_name} says:**\n> {self.message.content}\n\n"
                    description += f"*Originally posted in #{self.message.channel.name} on {self.message.created_at.strftime('%Y-%m-%d %H:%M:%S')}*"
                    
                    success = await self.lore_system.add_lore_entry(title, description, modal_interaction.user.id, modal_interaction.created_at)
                    
                    if success:
                        embed = discord.Embed(
                            title="📜 Message Added to Lore!",
                            description=f"Successfully added message from **{author_name}** to lore as '**{title}**'",
                            color=discord.Color.gold()
                        )
                        embed.add_field(name="Original Message", value=self.message.content[:500] + ("..." if len(self.message.content) > 500 else ""), inline=False)
                        embed.set_footer(text=f"Added by {modal_interaction.user.display_name}")
                        await modal_interaction.response.send_message(embed=embed, ephemeral=True)
                    else:
                        await modal_interaction.response.send_message("❌ Failed to add the message to lore. Please try again.", ephemeral=True)
                        
                except Exception as e:
                    await modal_interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)
        
        modal = LoreTitleModal(message, talk_system.lore_system, bot)
        await interaction.response.send_modal(modal)
    
    print("Talk System loaded successfully!")

# Legacy setup functions for backward compatibility
def setup_lore_commands(bot):
    """Legacy setup for lore commands"""
    if not hasattr(bot, 'talk_system_loaded'):
        bot.loop.create_task(setup(bot))
        bot.talk_system_loaded = True

def setup_what_is_commands(bot):
    """Legacy setup for what_is commands"""
    if not hasattr(bot, 'talk_system_loaded'):
        bot.loop.create_task(setup(bot))
        bot.talk_system_loaded = True

def setup_user_says_commands(bot):
    """Legacy setup for user_says commands"""
    if not hasattr(bot, 'talk_system_loaded'):
        bot.loop.create_task(setup(bot))
        bot.talk_system_loaded = True

def setup_conversation_commands(bot):
    """Legacy setup for conversation commands"""
    if not hasattr(bot, 'talk_system_loaded'):
        bot.loop.create_task(setup(bot))
        bot.talk_system_loaded = True

# Export for __all__
__all__ = [
    'TalkSystem',
    'setup',
    'setup_lore_commands',
    'setup_what_is_commands', 
    'setup_user_says_commands',
]