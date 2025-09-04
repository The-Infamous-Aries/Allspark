import discord
import os
import json
import random
import asyncio
from typing import List, Dict, Any, Optional
from collections import defaultdict
from discord.ext import commands
from discord import app_commands
from .rpg_system import TransformersAIDungeonMaster, get_rpg_system

# It's good practice to define constants for values used multiple times.
# This avoids "magic strings" and makes future changes easier.
RARITIES = ["common", "uncommon", "rare", "epic", "legendary"]
SKILL_TYPES = {"COMBAT": "combat", "STEALTH": "stealth", "TECH": "tech"}
DIFFICULTY_THRESHOLDS = {"easy": 3, "moderate": 4, "hard": 5, "very_hard": 5}
DIFFICULTY_XP = {"easy": 50, "moderate": 100, "hard": 150, "very_hard": 200}
BATTLE_TYPE_CONFIG = {
    "monster": {"json_key": "monsters", "health": 100, "attack": 15, "defense": 10, "multiplier": 1.0},
    "boss": {"json_key": "bosses", "health": 200, "attack": 25, "defense": 15, "multiplier": 1.5},
    "titan": {"json_key": "titans", "health": 500, "attack": 40, "defense": 25, "multiplier": 2.0},
}

class RPGCommands(commands.Cog):
    """Unified Discord commands for the Transformers RPG system"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.JSON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Json")
        self.rpg_system = TransformersAIDungeonMaster(self.JSON_DIR)
        
        self.monsters_data = {}
        self.events_data = {}
        self.story_data = {}
        self.active_sessions = {}
        self.ai_director = self.rpg_system
        
        # This optimized structure pre-sorts items by rarity for instant lookups later.
        self.transformation_items_by_rarity = defaultdict(list)

        # Lazy loading flags
        self._data_loaded = False

        # Optimized AI initialization
        try:
            import google.generativeai as genai
            api_key = os.getenv('GEMINI_API_KEY')
            if api_key:
                genai.configure(api_key=api_key)
                self.gemini_model = genai.GenerativeModel('gemini-pro')
            else:
                self.gemini_model = None
        except ImportError:
            print("Warning: google.generativeai package not found. AI features disabled.")
            self.gemini_model = None

    @commands.Cog.listener()
    async def on_ready(self):
        """Load data once the bot is ready."""
        print("RPGCommands Cog is ready. Loading data...")
        self.load_all_data()

    def _load_json_file(self, filename: str, default_data: Any = None) -> Any:
        """Helper to load a single JSON file safely."""
        if default_data is None:
            default_data = {}
        file_path = os.path.join(self.JSON_DIR, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load or parse {filename}. Using default. Error: {e}")
            return default_data
        
    def load_all_data(self):
        """Consolidated method to load all necessary JSON data."""
        if self._data_loaded:
            return
            
        self.monsters_data = self._load_json_file('monsters_and_bosses.json', {"monsters": [], "bosses": [], "titans": []})
        self.events_data = self._load_json_file('random_events.json', {"events": []})
        self.story_data = self._load_json_file('story_segments.json', {"segments": []})
        self._load_transformation_items()
        
        self._data_loaded = True
        print("All RPG data loaded successfully.")

    def _load_transformation_items(self):
        """Load and pre-process transformation items for efficient access."""
        items_data = self._load_json_file('transformation_items.json', {})
        if not items_data:
            return

        # Pre-process items into a dictionary keyed by rarity for O(1) lookups.
        self.transformation_items_by_rarity.clear()
        for category_data in items_data.values():
            if isinstance(category_data, dict):
                for item_id, item_details in category_data.items():
                    rarity = item_details.get('rarity', 'common').lower()
                    item_details['id'] = item_id # Ensure item has its ID
                    self.transformation_items_by_rarity[rarity].append(item_details)

    def save_characters_data(self):
        """Save character data. The RPG system now handles this automatically."""
        # This function is kept for API consistency as requested,
        # but its logic is delegated to the rpg_system.
        pass

    def calculate_xp_needed(self, level: int) -> int:
        """Calculate XP needed for the next level using a quadratic formula."""
        return 100 * (level ** 2)

    def calculate_stat_increase(self, level: int) -> int:
        """Calculate stat increase based on level."""
        return 2 + (level // 5)

    def get_loot_drops(self, rarity: str) -> List[Dict[str, Any]]:
        """
        Get loot drops based on rarity from pre-processed transformation items.
        This is now much faster as it doesn't need to iterate through all items every time.
        """
        target_rarity = rarity.lower()
        
        # Directly access the pre-filtered list of items by rarity.
        possible_items = self.transformation_items_by_rarity.get(target_rarity, [])
        
        if possible_items:
            # Return up to 3 random items.
            num_to_sample = min(3, len(possible_items))
            return random.sample(possible_items, num_to_sample)
        
        # Fallback to a generic item if no specific loot is found.
        return [{"name": f"{rarity.title()} Energon Cube", "type": "consumable", "value": 10}]

    async def award_xp_and_check_level(self, user: discord.User, xp_amount: int) -> bool:
        """
        Award XP and check for level up.
        Accepts a discord.User object for reliable access to both ID and name.
        """
        user_id = str(user.id)
        character = self.rpg_system.get_character(user_id)
        if not character:
            return False

        old_level = character.level
        leveled_up = self.rpg_system.gain_experience(user_id, xp_amount)

        if leveled_up:
            stat_increase = self.calculate_stat_increase(character.level)
            character.base_stats.ATT += stat_increase
            character.base_stats.DEF += stat_increase
            character.base_stats.DEX += stat_increase
            character.base_stats.CHA += stat_increase
            
            # Save using the user's name for unified storage.
            self.rpg_system.save_character(user_id, user.name)
            return True
        return False

    def calculate_group_skill(self, players: List[discord.User], skill_type: str) -> int:
        """Calculate the combined skill for a group of players."""
        total_skill = 0
        for player in players:
            character = self.rpg_system.get_character(str(player.id))
            if not character:
                continue

            if skill_type == SKILL_TYPES["COMBAT"]:
                total_skill += character.base_stats.ATT + character.base_stats.DEF
            elif skill_type == SKILL_TYPES["STEALTH"]:
                total_skill += character.base_stats.DEX + character.base_stats.CHA
            elif skill_type == SKILL_TYPES["TECH"]:
                total_skill += character.base_stats.DEX * 2
        return total_skill

    async def _create_adventure_setup(self, ctx: commands.Context, title: str, description: str, color: discord.Color):
        """Helper function to reduce code duplication in adventure setup commands."""
        embed = discord.Embed(title=title, description=description, color=color)
        embed.add_field(name="Players", value="No players have joined yet.", inline=False)
        
        view = self.rpg_system.BattleSetupView(self)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @commands.hybrid_command(name="cyber_random")
    async def cyber_random(self, ctx: commands.Context):
        """Start a random group adventure."""
        await self._create_adventure_setup(ctx, "🤖 Cybertronian Group Adventure", "Form your party and embark on an adventure!", discord.Color.blue())

    @commands.hybrid_command(name="cyber_battle")
    async def cyber_battle(self, ctx: commands.Context):
        """Start a group battle adventure."""
        await self._create_adventure_setup(ctx, "⚔️ Battle Formation", "Form your party for battle!", discord.Color.red())

    @commands.hybrid_command(name="cyber_event")
    async def cyber_event(self, ctx: commands.Context):
        """Start a group event adventure."""
        await self._create_adventure_setup(ctx, "🎲 Event Challenge", "Form your party for an event challenge!", discord.Color.green())

    @commands.hybrid_command(name="cyber_story")
    async def cyber_story(self, ctx: commands.Context):
        """Start a group story adventure."""
        await self._create_adventure_setup(ctx, "📖 Story Adventure", "Form your party for a story adventure!", discord.Color.purple())

    async def start_battle(self, channel: discord.TextChannel, players: List[discord.User], rarity: str, battle_type: str):
        """Start a battle using a more scalable, data-driven approach."""
        battle_type_key = battle_type.lower()
        config = BATTLE_TYPE_CONFIG.get(battle_type_key)
        if not config:
            await channel.send(f"Error: Unknown battle type '{battle_type}'.")
            return

        enemy = self.rpg_system.get_monster_by_rarity(config["json_key"], rarity.lower())
        if not enemy:
             await channel.send(f"Could not find a {rarity} {battle_type} to fight!")
             return

        battle_data = {
            "enemy_name": enemy.get("name", f"Unnamed {battle_type.title()}"),
            "enemy_hp": enemy.get("health", config["health"]),
            "enemy_max_hp": enemy.get("health", config["health"]),
            "enemy_attack": enemy.get("attack", config["attack"]),
            "enemy_defense": enemy.get("defense", config["defense"]),
            "enemy_multiplier": config["multiplier"],
            "enemy_rarity": rarity.lower(),
            "enemy_type": battle_type_key,
        }

        view = self.rpg_system.CybertronianBattleView(battle_data, players, self.rpg_system)
        embed = view.get_battle_embed()
        message = await channel.send(embed=embed, view=view)
        view.message = message

    async def handle_event_challenge(self, channel: discord.TextChannel, players: List[discord.User], event: Dict[str, Any], chosen_skill: str):
        """Handle an event challenge using defined constants."""
        group_skill = self.calculate_group_skill(players, chosen_skill.lower())
        difficulty = event.get("difficulty", "moderate")
        
        # Assumes roll_d5() is defined elsewhere.
        roll = random.randint(1, 5) # Placeholder for roll_d5()
        success_threshold = DIFFICULTY_THRESHOLDS.get(difficulty, 4)
        is_success = (roll + group_skill) >= success_threshold

        base_xp = DIFFICULTY_XP.get(difficulty, 100)
        
        if is_success:
            xp_reward = base_xp
            energon_reward = base_xp // 2
            loot = self.get_loot_drops("rare") # Rarity could be tied to difficulty
            outcome_text = f"**Success!** The group masterfully used `{chosen_skill}` to overcome the challenge!"
            color = discord.Color.green()
        else:
            xp_reward = base_xp // 2
            energon_reward = base_xp // 4
            loot = self.get_loot_drops("uncommon")
            outcome_text = f"**Partial Success...** The `{chosen_skill}` attempt wasn't enough to fully succeed, but you managed."
            color = discord.Color.orange()

        for player in players:
            await self.award_xp_and_check_level(player, xp_reward)
            self.rpg_system.add_energon_earned(str(player.id), energon_reward)

        embed = discord.Embed(title="🎲 Event Result", description=outcome_text, color=color)
        embed.add_field(name="Group Effort", value=f"Skill: {group_skill} + Roll: {roll} vs Difficulty: {success_threshold}", inline=False)
        embed.add_field(name="XP Gained", value=f"`{xp_reward}` per player", inline=True)
        embed.add_field(name="Energon Gained", value=f"`{energon_reward}` per player", inline=True)
        if loot:
            loot_text = ", ".join(f"**{item['name']}**" for item in loot)
            embed.add_field(name="💎 Loot Found", value=loot_text, inline=False)

        await channel.send(embed=embed)

    async def handle_story_segment(self, channel: discord.TextChannel, players: List[discord.User], story: Dict[str, Any]):
        """Handle a story segment with choices."""
        embed = discord.Embed(title=f"📖 {story.get('title', 'A New Chapter')}", description=story.get('content', '...'), color=discord.Color.purple())
        
        story_choices = story.get('choices')
        if not story_choices:
            await channel.send(embed=embed)
            return

        # Assumes VotingView is defined elsewhere
        # from .views import VotingView 
        choices_text = [choice['text'] for choice in story_choices]
        view = VotingView(choices_text, players)
        message = await channel.send(embed=embed, view=view)
        view.message = message
        await view.wait()
        
        chosen_text = view.get_winner()
        chosen_choice = next((c for c in story_choices if c['text'] == chosen_text), None)
            
        if chosen_choice:
            xp_reward = chosen_choice.get('xp', 100)
            energon_reward = chosen_choice.get('energon', 50)
            
            for player in players:
                await self.award_xp_and_check_level(player, xp_reward)
                self.rpg_system.add_energon_earned(str(player.id), energon_reward)
            
            result_embed = discord.Embed(
                title="📖 The Story Unfolds...",
                description=chosen_choice.get('outcome', 'Your choice affects the story...'),
                color=discord.Color.purple()
            )
            result_embed.add_field(name="XP Gained", value=f"`{xp_reward}` per player", inline=True)
            result_embed.add_field(name="Energon Gained", value=f"`{energon_reward}` per player", inline=True)
            
            await channel.send(embed=result_embed)

    @commands.hybrid_command(name="cyber_info")
    async def cyber_info(self, ctx: commands.Context):
        """Show information about the Cybertronian RPG system."""
        embed = discord.Embed(
            title="🤖 Cybertronian RPG System",
            description="Welcome to the Transformers RPG! Here's how to play:",
            color=discord.Color.blue()
        )
        embed.add_field(name="🎯 Getting Started", value="Use `/create_character` to begin, then join group adventures!", inline=False)
        embed.add_field(name="⚔️ Adventures", value="Use the `/cyber_...` commands to start adventures with friends.", inline=False)
        embed.add_field(name="🎮 Commands", value="`/cyber_random` - Random adventure\n`/cyber_battle` - Battle only\n`/cyber_event` - Event only\n`/cyber_story` - Story only", inline=False)
        
        await ctx.send(embed=embed)


# Note: The duplicate loading methods from the original file have been removed
# as their logic was consolidated into the single `load_all_data` method.
