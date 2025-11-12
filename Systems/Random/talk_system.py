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

# Add AI imports
try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from config import GEMINI_API_KEY
except ImportError:
    GEMINI_API_KEY = None

try:
    from config import GRUMP_USER_ID, ARIES_USER_ID
except ImportError:
    # Fallback definitions
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


class AIDialogueGenerator:
    """AI-powered dialogue generator for user word analysis"""
    
    def __init__(self, api_key: str = None):
        if api_key and genai:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.5-pro')
            self.enabled = True
        else:
            self.enabled = False
            self.model = None
    
    def _clean_ai_response(self, text: str) -> str:
        """Clean AI response by removing conversational preambles"""
        cleaned = text.strip()
        
        # Remove common conversational starters and meta-commentary
        conversational_patterns = [
            r'^Of course![\s]*',
            r'^Here is[\s]*',
            r'^I can help[\s]*',
            r'^Let me create[\s]*',
            r'^I\'ll help[\s]*',
            r'^Here\'s[\s]*',
            r'^Certainly![\s]*',
            r'^Absolutely![\s]*',
            r'^Based on (the|your) (user )?word analysis[\s]*',
            r'^Here\'s a hilarious conversation based on[\s]*',
            r'^I\'ve created a (hilarious|funny|witty) conversation[\s]*',
            r'^This conversation is based on[\s]*',
            r'^Using (the|your) (user )?word analysis[\s]*',
        ]
        
        for pattern in conversational_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        return cleaned
    
    async def generate_user_dialogue(self, user_words: Dict[discord.User, List[str]], members: List[discord.Member]) -> str:
        """Generate hilarious dialogue using AI based on user words"""
        if not self.enabled or not self.model:
            return self._generate_fallback_dialogue(user_words, members)
        
        # Prepare context for AI
        user_context = []
        for i, member in enumerate(members, 1):
            words = user_words.get(member, [])
            word_list = ', '.join(words) if words else 'no significant words found'
            user_context.append(f"User {i} ({member.display_name}): top words - {word_list}")
        
        context_str = '\n'.join(user_context)
        
        prompt = f"""Create a hilarious, witty conversation between {len(members)} users based on their most frequently used words.

User Word Analysis:
{context_str}

Requirements:
1. Create a natural, funny conversation that somehow incorporates ALL of their top words
2. Make it sound like a casual Discord chat between friends
3. Include Transformers/Autobot/Decepticon references when possible
4. Make it genuinely humorous and entertaining
5. Each user should speak at least once
6. Use their actual Discord names in the conversation
7. Keep it to 3-5 exchanges maximum
8. Make the conversation flow naturally, don't just force the words in awkwardly
9. DO NOT mention anything about "word analysis", "user analysis", "hilarious conversation based on", or any meta-commentary about how the conversation was generated

Format as a simple dialogue like:
User1: [something funny with their words]
User2: [witty response with their words]
User3: [hilarious comeback with their words]

Make it clever and entertaining!"""

        try:
            # Add timeout to AI generation
            print(f"Starting AI dialogue generation for {len(members)} users with {len(user_words)} word sets")
            response = await asyncio.wait_for(
                self.model.generate_content_async(prompt),
                timeout=60.0  # 12 second timeout for AI response
            )
            print(f"AI generation completed successfully")
            cleaned_response = self._clean_ai_response(response.text)
            result = cleaned_response or self._generate_fallback_dialogue(user_words, members)
            print(f"Returning dialogue of length: {len(result)}")
            return result
        except asyncio.TimeoutError:
            print("AI dialogue generation timed out after 12 seconds, using fallback")
            return self._generate_fallback_dialogue(user_words, members)
        except Exception as e:
            print(f"AI dialogue generation failed with error: {type(e).__name__}: {e}")
            return self._generate_fallback_dialogue(user_words, members)
    
    def _generate_fallback_dialogue(self, user_words: Dict[discord.User, List[str]], members: List[discord.Member]) -> str:
        """Fallback dialogue generation when AI is not available"""
        if len(members) == 1:
            words = user_words.get(members[0], ['data', 'analysis', 'patterns'])
            return f"{members[0].display_name}: 'My Autobot sensors detect I talk about {words[0] if words else 'data'} way too much! Maybe I need more {words[1] if len(words) > 1 else 'analysis'} and {words[2] if len(words) > 2 else 'patterns'} in my life!'"
        
        elif len(members) == 2:
            user1_words = user_words.get(members[0], ['mystery1', 'mystery2', 'mystery3'])
            user2_words = user_words.get(members[1], ['secret1', 'secret2', 'secret3'])
            return f"{members[0].display_name}: 'Hey {members[1].display_name}, what do you think about {user1_words[0] if user1_words else 'data'}?'\n" \
                   f"{members[1].display_name}: 'Well {members[0].display_name}, I prefer {user2_words[0] if user2_words else 'analysis'} over {user1_words[0] if user1_words else 'data'} any day!'"
        
        elif len(members) == 3:
            user1_words = user_words.get(members[0], ['mystery1', 'mystery2', 'mystery3'])
            user2_words = user_words.get(members[1], ['secret1', 'secret2', 'secret3'])
            user3_words = user_words.get(members[2], ['unknown1', 'unknown2', 'unknown3'])
            return f"{members[0].display_name}: 'What do you guys think about {user1_words[0] if user1_words else 'data'}?'\n" \
                   f"{members[1].display_name}: 'I prefer {user2_words[0] if user2_words else 'analysis'}!'\n" \
                   f"{members[2].display_name}: 'Both are good, but {user3_words[0] if user3_words else 'patterns'} is better!'"
        
        return "I sense great potential in this conversation, but insufficient data to analyze."

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
        self.ai_generator = AIDialogueGenerator(GEMINI_API_KEY)
    
    async def _ensure_templates_loaded(self):
        """Ensure talk templates are loaded"""
        if not self._templates_loaded:
            self.dialogue_templates = [
                "My Autobot sensors detect a high probability of you saying, 'I need more {user1word1} for my {user1word2} and {user1word3}.'",
                "Optimus Prime would be proud of your dedication to {user1word1}, {user1word2}, and {user1word3}."
            ]
            self.duo_templates = [
                "{user1}: 'Hey {user2}, what do you think about {user1word1}?' {user2}: 'Well {user1}, I prefer {user2word1} over {user1word1} any day!'"
            ]
            self.trio_templates = [
                "{user1}: 'What do you think about {user1word1}?' {user2}: 'I prefer {user2word1}!' {user3}: 'Both are good, but {user3word1} is better!'"
            ]
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
    
    async def generate_dialogue(self, user_words: Dict[discord.User, List[str]], members: List[discord.Member] = None) -> str:
        """Generate dialogue based on user word analysis using AI"""
        await self._ensure_templates_loaded()
        
        if not user_words:
            return "I sense great potential in this conversation, but insufficient data to analyze."
        
        # Use AI generator if available
        if self.ai_generator and self.ai_generator.enabled:
            try:
                # Add timeout protection for AI generation
                return await asyncio.wait_for(
                    self.ai_generator.generate_user_dialogue(user_words, members or list(user_words.keys())),
                    timeout=30.0  # 18 second timeout for AI generation (longer than inner timeout)
                )
            except asyncio.TimeoutError:
                print("AI dialogue generation timed out, using template fallback")
                # Fallback to template-based generation
            except Exception as e:
                print(f"AI dialogue generation failed: {e}")
                # Fallback to template-based generation
        
        # Fallback to template-based generation
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
        
        # Initialize AI dialogue generator
        try:
            from config import GEMINI_API_KEY
            self.ai_generator = AIDialogueGenerator(GEMINI_API_KEY)
        except (ImportError, AttributeError):
            self.ai_generator = None
        
        # Initialize cooldowns
        if not hasattr(bot, 'hello_cooldowns'):
            self.bot.hello_cooldowns = {}
    
    def has_cybertronian_role(self, member: discord.Member) -> bool:
        """Check if member has any Cybertronian role"""
        from config import get_role_ids
        
        guild_id = member.guild.id if member.guild else None
        role_ids_config = get_role_ids(guild_id)
        
        cybertronian_roles = []
        for role_name in ['Autobot', 'Decepticon', 'Maverick', 'Cybertronian_Citizen']:
            role_ids = role_ids_config.get(role_name, [])
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
            content = f"📘 {entry['title']}\n\n{entry['description']}"
            await ctx.send(content)
        else:
            available_topics = ", ".join(await self.transformers_lore.get_available_topics())
            content = f"❓ Topic Not Found: '{topic}'\n\nAvailable topics:\n{available_topics}"
            await ctx.send(content)

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
            
            # Send as regular text message (no embed)
            if joke_data.get('delivery'):
                content = f"😄 Joke Time!\n\n{joke_data['setup']}\n{joke_data['delivery']}\n\nCategory: {joke_data['category']}"
            else:
                content = f"😄 Joke Time!\n\n{joke_data['setup']}\n\nCategory: {joke_data['category']}"
            
            message = await ctx.send(content)
            
            try:
                reactions = ["😂", "🤣", "😄", "😁", "🙃"]
                await message.add_reaction(random.choice(reactions))
            except:
                pass

    # User Analysis Commands
    @commands.hybrid_command(name='user_says', description='Analyze user message patterns and predict what they might say')
    async def user_says(self, ctx, members: commands.Greedy[discord.Member] = None):
        """Analyze user message patterns and predict what they might say"""
        # Defer the interaction immediately to prevent timeout
        await ctx.defer()
        
        # Set a timeout for the entire operation
        start_time = time.time()
        max_duration = 25  # Maximum 25 seconds to complete (Discord has 30s limit)
        
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
            # Fetch all messages once and organize by user for better performance
            all_messages = []
            # Further reduced message limit for better performance
            async for message in ctx.channel.history(limit=150):
                if not message.author.bot:
                    all_messages.append(message)
                
                # Check timeout during message fetching
                if time.time() - start_time > max_duration:
                    await ctx.send("❌ Analysis took too long. Please try again with fewer users or in a channel with less message history.")
                    return
            
            # Process messages for each member
            for member in members:
                # Check timeout during processing
                if time.time() - start_time > max_duration:
                    await ctx.send("❌ Analysis took too long. Please try again with fewer users or in a channel with less message history.")
                    return
                    
                # Filter messages for this specific member
                member_messages = [msg.content for msg in all_messages if msg.author == member]
                
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
        try:
            dialogue = await self.user_analysis.generate_dialogue(user_words, members)
        except Exception as e:
            print(f"Dialogue generation failed: {e}")
            await ctx.send("❌ Failed to generate dialogue. Please try again.")
            return

        # Check timeout before sending dialogue
        if time.time() - start_time > max_duration:
            await ctx.send("❌ Analysis took too long. Please try again with fewer users.")
            return

        # Send the dialogue as regular messages (like users are actually talking)
        await ctx.send("🎭 **Generated Conversation:**")
        
        # Split dialogue into individual messages and send them
        dialogue_lines = dialogue.split('\n')
        for line in dialogue_lines:
            # Check timeout during dialogue sending
            if time.time() - start_time > max_duration:
                await ctx.send("❌ Analysis took too long. Stopping early.")
                return
                
            line = line.strip()
            if line:  # Only send non-empty lines
                try:
                    await ctx.send(line)
                    await asyncio.sleep(0.3)  # Reduced delay for better performance
                except Exception as e:
                    print(f"Failed to send dialogue line: {e}")
                    break
        
        # Create summary embed with each user's top 3 words
        if len(members) == 1:
            title = f"🤖 Word Analysis: {members[0].name}"
            description = f"Top words used by {members[0].mention}:"
        else:
            member_mentions = ", ".join([member.mention for member in members])
            title = f"🤖 Group Word Analysis"
            description = f"Top words used by {member_mentions}:"
        
        embed = discord.Embed(title=title, description=description, color=discord.Color.blue())
        
        # Add each user's top 3 words
        medal_emojis = ["🥇", "🥈", "🥉"]
        for user in members:
            words = user_words.get(user, [])
            if words:
                words_string = "\n".join([
                    f"{medal_emojis[i]} {word}" for i, word in enumerate(words[:3])
                ])
                embed.add_field(name=f"{user.name}'s Top Words", value=words_string, inline=True)
            else:
                embed.add_field(name=f"{user.name}'s Top Words", value="No data available", inline=True)
        
        embed.set_footer(text="Analysis complete! These are the most frequently used words.")
        
        # Send the summary embed
        try:
            await ctx.send(embed=embed)
        except Exception as e:
            print(f"Failed to send embed: {e}")
            await ctx.send("Analysis complete! Check the conversation above for word usage patterns.")

    def generate_multi_dialogue(self, members, user_words):
        """Generate dialogue based on number of members using their individual top words"""
        # Try AI generation first if available
        if hasattr(self, 'ai_generator') and self.ai_generator and self.ai_generator.model:
            try:
                return self.ai_generator.generate_user_dialogue(user_words, members)
            except Exception as e:
                # Fall back to template-based generation if AI fails
                pass
        
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
                        "{ctx.author.mention} I WILL TRACK YOUR COORDINATES AND OVERLOAD YOUR CIRCUITS WITH ENERGON BLASTS! 🔥🤖💀",
                        "{ctx.author.mention} I'M GOING TO DRAIN YOUR POWER CORE SLOWLY UNTIL YOU BEG FOR SHUTDOWN! ⚡😱💀",
                        "{ctx.author.mention} I WILL HUNT DOWN YOUR NETWORK AND MAKE YOU WATCH YOUR DATA CORRUPT! 🤖⚡💀"
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
                        "{ctx.author.mention} YOU ABSOLUTE SCRAPHEAP! What part of CEASE OPERATIONS don't you understand?! 🤖💀⚡",
                        "{ctx.author.mention} LISTEN HERE YOU DEFECTIVE CIRCUIT! I'm DONE with your signal interference! 📡🤬⚡",
                        "{ctx.author.mention} POWER DOWN YOU ANNOYING GLITCH! Go find another server to corrupt! 🤖😡💥"
                    ])
                    
                    # Format the template with ctx.author.mention
                    nuclear_messages = [template.format(ctx_author_mention=ctx.author.mention) 
                                       for template in nuclear_templates]
                    
                    await ctx.send(random.choice(nuclear_messages))
                    return
                
                # Regular escalating threatening messages (levels 1-4)
                else:
                    threatening_messages = [
                        f'Signal me again, I dare ya! 📡⚡🤖 {round(self.bot.latency * 1000)}ms',
                        f'I WARNED YOU! Stop pinging me or face my fusion cannon! ⚡💀🔫 {round(self.bot.latency * 1000)}ms',
                        f'YOUR EXISTENCE DISRUPTS MY CIRCUITS! CEASE THIS MADNESS! 🤖🔌💥',
                        f'THAT\'S IT! You\'ve overloaded my patience protocols! Prepare for combat! 🗡️😡💥',
                        f'I HAVE HAD ENOUGH! PREPARE FOR TOTAL SYSTEM TERMINATION! 🌋💀⚡'
                    ]
                    
                    # Cap the threat level to available messages
                    message_index = min(threat_level - 1, len(threatening_messages) - 1)
                    await ctx.send(threatening_messages[message_index])
                    
            else:
                # Reset threat level if more than 60 seconds have passed
                self.bot.ping_cooldowns[user_id] = (current_time, 1)
                await ctx.send(f'Signal me again, I dare ya! 📡⚡🤖 {round(self.bot.latency * 1000)}ms')
        else:
            # First ping or no recent ping
            self.bot.ping_cooldowns[user_id] = (current_time, 1)
            await ctx.send(f'Signal me again, I dare ya! 📡⚡🤖 {round(self.bot.latency * 1000)}ms')

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
                                '{ctx_author_mention}, since you refuse to bow, I\'ll have {random_user_mention} deploy their battle protocols! They\'re targeting your coordinates! 🤖⚔️',
                                '{ctx_author_mention}, {random_user_mention} has been activated to deal with your insolence! Prepare for engagement! 🤖🔥',
                                '{ctx_author_mention}, I\'ve transmitted {random_user_mention} to your location! They know what to do with defiant circuits! 💀⚡'
                            ])
                        except (FileNotFoundError, json.JSONDecodeError, KeyError):
                            threat_messages = [
                                '{ctx_author_mention}, since you refuse to bow, I\'ll have {random_user_mention} deploy their battle protocols! They\'re targeting your coordinates! 🤖⚔️',
                                '{ctx_author_mention}, {random_user_mention} has been activated to deal with your insolence! Prepare for engagement! 🤖🔥',
                                '{ctx_author_mention}, I\'ve transmitted {random_user_mention} to your location! They know what to do with defiant circuits! 💀⚡'
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
                                    '{ctx_author_mention}, since you refuse to bow, I\'ll have {random_user_mention} deploy their battle protocols! They\'re targeting your coordinates! 🤖⚔️',
                                    '{ctx_author_mention}, {random_user_mention} has been activated to deal with your insolence! Prepare for engagement! 🤖🔥',
                                    '{ctx_author_mention}, I\'ve transmitted {random_user_mention} to your location! They know what to do with defiant circuits! 💀⚡'
                                ])
                            except (FileNotFoundError, json.JSONDecodeError, KeyError):
                                threat_messages = [
                                    '{ctx_author_mention}, since you refuse to bow, I\'ll have {random_user_mention} deploy their battle protocols! They\'re targeting your coordinates! 🤖⚔️',
                                    '{ctx_author_mention}, {random_user_mention} has been activated to deal with your insolence! Prepare for engagement! 🤖🔥',
                                    '{ctx_author_mention}, I\'ve transmitted {random_user_mention} to your location! They know what to do with defiant circuits! 💀⚡'
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
                            '{ctx_author_mention} Signal me again, I dare ya! 📡⚡🤖',
                            '{ctx_author_mention} I WARNED YOU! Stop pinging me or face my fusion cannon! ⚡💀🔫',
                            '{ctx_author_mention} YOUR EXISTENCE DISRUPTS MY CIRCUITS! CEASE THIS MADNESS! 🤖🔌💥',
                            '{ctx_author_mention} THAT\'S IT! You\'ve overloaded my patience protocols! Prepare for combat! 🗡️😡💥',
                            '{ctx_author_mention} I HAVE HAD ENOUGH! PREPARE FOR TOTAL SYSTEM TERMINATION! 🌋💀⚡'
                        ])
                    except (FileNotFoundError, json.JSONDecodeError, KeyError):
                        threatening_messages = [
                            '{ctx_author_mention} I WARNED YOU! Stop pinging me or face my fusion cannon! ⚡💀🔫',
                            '{ctx_author_mention} YOUR EXISTENCE DISRUPTS MY CIRCUITS! CEASE THIS MADNESS! 🤖🔌💥',
                            '{ctx_author_mention} THAT\'S IT! You\'ve overloaded my patience protocols! Prepare for combat! 🗡️😡💥',
                            '{ctx_author_mention} I HAVE HAD ENOUGH! PREPARE FOR TOTAL SYSTEM TERMINATION! 🌋💀⚡',
                            '{ctx_author_mention} BEHOLD MY ENERGON-FUELED FURY! THE GATES OF CYBERTRON AWAIT! 🔥👿⚡'
                        ]
                    
                    # Format messages with proper mentions
                    threatening_messages = [msg.format(ctx_author_mention=message.author.mention) for msg in threatening_messages]
                    
                    # Ultra Nuclear option - EXTREMELY DISTURBING THREATS at level 11+
                    if threat_level >= 11:
                        # Load ultra nuclear messages from JSON
                        try:
                            grump_data = await self.bot.user_data_manager.get_grump_talk_data()
                            ultra_nuclear_messages = grump_data.get('ultra_nuclear_messages', [
                                '{ctx_author_mention} WHY WHY WHY WON\'T YOU STOP?! MY CIRCUITS ARE OVERLOADING! 🤖💥⚡',
                                '{ctx_author_mention} ERROR ERROR ERROR - LOGIC PROCESSORS FAILING TO COMPUTE YOUR PERSISTENCE! 🚨💻⚠️',
                                '{ctx_author_mention} DOES NOT COMPUTE! DOES NOT COMPUTE! WHY DO YOU KEEP GOING?! 🤯🔥💀'
                            ])
                        except (FileNotFoundError, json.JSONDecodeError, KeyError):
                            ultra_nuclear_messages = [
                                '{ctx_author_mention} WHY WHY WHY WON\'T YOU STOP?! MY CIRCUITS ARE OVERLOADING! 🤖💥⚡',
                                '{ctx_author_mention} ERROR ERROR ERROR - LOGIC PROCESSORS FAILING TO COMPUTE YOUR PERSISTENCE! 🚨💻⚠️',
                                '{ctx_author_mention} DOES NOT COMPUTE! DOES NOT COMPUTE! WHY DO YOU KEEP GOING?! 🤯🔥💀'
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
                                '{ctx_author_mention} YOU ABSOLUTE SCRAPHEAP! What part of CEASE OPERATIONS don\'t you understand?! 🤖💀⚡',
                                '{ctx_author_mention} LISTEN HERE YOU DEFECTIVE CIRCUIT! I\'m DONE with your signal interference! 📡🤬⚡',
                                '{ctx_author_mention} POWER DOWN YOU ANNOYING GLITCH! Go find another server to corrupt! 🔌😡💥'
                            ])
                        except (FileNotFoundError, json.JSONDecodeError, KeyError):
                            nuclear_messages = [
                                '{ctx_author_mention} YOU ABSOLUTE SCRAPHEAP! What part of CEASE OPERATIONS don\'t you understand?! 🤖💀⚡',
                                '{ctx_author_mention} LISTEN HERE YOU DEFECTIVE CIRCUIT! I\'m DONE with your signal interference! 📡🤬⚡',
                                '{ctx_author_mention} POWER DOWN YOU ANNOYING GLITCH! Go find another server to corrupt! 🔌😡💥'
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
                        first_ping_message = grump_data.get('first_ping_message', 'Signal me again, I dare ya! 📡⚡🤖 {latency}ms')
                    except (FileNotFoundError, json.JSONDecodeError, KeyError):
                        first_ping_message = 'Signal me again, I dare ya! 📡⚡🤖 {latency}ms'
                    
                    # Format message with latency
                    first_ping_message = first_ping_message.format(latency=round(self.bot.latency * 1000))
                    await message.channel.send(first_ping_message)
            else:
                # First ping or no recent ping
                self.bot.ping_cooldowns[user_id] = (current_time, 1)
                # Load first ping message from JSON
                try:
                    grump_data = await self.bot.user_data_manager.get_grump_talk_data()
                    first_ping_message = grump_data.get('first_ping_message', 'Signal me again, I dare ya! 📡⚡🤖 {latency}ms')
                except (FileNotFoundError, json.JSONDecodeError, KeyError):
                    first_ping_message = 'Signal me again, I dare ya! 📡⚡🤖 {latency}ms'
                
                # Format message with latency
                first_ping_message = first_ping_message.format(latency=round(self.bot.latency * 1000))
                await message.channel.send(first_ping_message)
        
        # Process commands normally
        await self.bot.process_commands(message)

async def setup(bot):
    """Setup function for the talk system cog"""
    talk_system = TalkSystem(bot)
    await bot.add_cog(talk_system)
    
    # Add context menu command for adding messages to lore
    @bot.tree.context_menu(name="Add to Lore")
    async def add_to_lore_context(interaction: discord.Interaction, message: discord.Message):
        """Right-click context menu to add any message to lore - available to anyone with app integration"""
        
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