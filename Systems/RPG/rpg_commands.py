import discord
import os
import json
import random
import asyncio
from typing import List, Dict, Any, Optional
from discord.ext import commands
from discord import app_commands
from .rpg_system import TransformersAIDungeonMaster, get_rpg_system

class RPGCommands(commands.Cog):
    """Unified Discord commands for the Transformers RPG system"""
    
    def __init__(self, bot):
        self.bot = bot
        self.JSON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Json")
        self.rpg_system = TransformersAIDungeonMaster(self.JSON_DIR)
        self.monsters_data = {}
        self.events_data = {}
        self.story_data = {}
        self.active_sessions = {}
        self.ai_director = None
        self.transformation_items = {}
        
        # Lazy loading flags
        self._data_loaded = False
        self._transformation_items_loaded = False
        
        # Initialize AI if API key available
        try:
            import google.generativeai as genai
            genai.configure(api_key=os.getenv('GEMINI_API_KEY', ''))
            self.gemini_model = genai.GenerativeModel('gemini-pro')
            self.ai_director = self.rpg_system
        except:
            self.gemini_model = None
            self.ai_director = self.rpg_system

    def load_data(self):
        """Load JSON data files (lazy loading)"""
        if self._data_loaded:
            return
            
        self.monsters_data = self._load_json_file('monsters_and_bosses.json', {"monsters": [], "bosses": [], "titans": []})
        self.events_data = self._load_json_file('random_events.json', {"events": []})
        self.story_data = self._load_json_file('story_segments.json', {"segments": []})
        self._data_loaded = True
        
    def _load_json_file(self, filename: str, default_data: dict = None) -> dict:
        """Load a JSON file from the JSON directory"""
        if default_data is None:
            default_data = {}
        try:
            file_path = os.path.join(self.JSON_DIR, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: {filename} not found in {self.JSON_DIR}")
            return default_data
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return default_data

    def save_characters_data(self):
        """Save character data to unified storage"""
        # The RPG system now handles saving to unified storage automatically
        pass

    def calculate_xp_needed(self, level: int) -> int:
        """Calculate XP needed for next level"""
        return 100 * level * level

    def calculate_stat_increase(self, level: int) -> int:
        """Calculate stat increase based on level"""
        return 2 + (level // 5)

    def get_loot_drops(self, rarity: str) -> List[Dict]:
        """Get loot drops based on rarity from actual transformation items"""
        # Ensure transformation items are loaded
        if not self._transformation_items_loaded:
            self.load_transformation_items()
            
        if not self.transformation_items:
            return []
        
        # Filter items by rarity
        rarity_map = {
            "common": "common",
            "uncommon": "uncommon", 
            "rare": "rare",
            "epic": "epic",
            "legendary": "legendary"
        }
        
        target_rarity = rarity_map.get(rarity.lower(), "common")
        
        # Collect all items from transformation_items.json
        all_items = []
        
        # Check if transformation_items is dict (from JSON) or list (processed)
        if isinstance(self.transformation_items, dict):
            # Raw JSON format
            for category in ['beast_modes', 'transformations', 'weapons', 'armor']:
                if category in self.transformation_items:
                    for item_id, item_data in self.transformation_items[category].items():
                        if item_data.get('rarity', '').lower() == target_rarity:
                            item_copy = dict(item_data)
                            item_copy['id'] = item_id
                            all_items.append(item_copy)
        else:
            # Processed list format
            for item in self.transformation_items:
                if isinstance(item, dict) and item.get('rarity', '').lower() == target_rarity:
                    all_items.append(item)
        
        # Return up to 3 random items of the correct rarity
        if all_items:
            return random.sample(all_items, min(3, len(all_items)))
        
        # Fallback to generic if no items found
        return [{"name": f"{rarity} Energon Cube", "type": "consumable", "value": 10}]

    async def award_xp_and_check_level(self, user_id: str, xp_amount: int, username: str = None):
        """Award XP and check for level up"""
        character = self.rpg_system.get_character(user_id)
        if not character:
            return False

        old_level = character.level
        self.rpg_system.gain_experience(user_id, xp_amount)
        new_level = character.level

        if new_level > old_level:
            stat_increase = self.calculate_stat_increase(new_level)
            # Apply stat increases
            character.base_stats.ATT += stat_increase
            character.base_stats.DEF += stat_increase
            character.base_stats.DEX += stat_increase
            character.base_stats.CHA += stat_increase
            
            # Save with username for unified storage
            self.rpg_system.save_character(user_id, username)
            return True
        return False

    def calculate_group_skill(self, players: List[discord.User], skill_type: str) -> int:
        """Calculate combined skill for a group"""
        total_skill = 0
        for player in players:
            character = self.rpg_system.get_character(str(player.id))
            if character:
                if skill_type == "combat":
                    total_skill += character.base_stats.ATT + character.base_stats.DEF
                elif skill_type == "stealth":
                    total_skill += character.base_stats.DEX + character.base_stats.CHA
                elif skill_type == "tech":
                    total_skill += character.base_stats.DEX * 2
        return total_skill

    @commands.hybrid_command(name="cyber_random")
    async def cyber_random(self, ctx):
        """Start a random group adventure"""
        embed = discord.Embed(
            title="🤖 Cybertronian Group Adventure",
            description="Form your party and embark on an adventure!",
            color=discord.Color.blue()
        )
        embed.add_field(name="Players", value="No players yet", inline=False)
        
        view = self.rpg_system.BattleSetupView(self)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @commands.hybrid_command(name="cyber_battle")
    async def cyber_battle(self, ctx):
        """Start a group battle adventure"""
        embed = discord.Embed(
            title="⚔️ Battle Formation",
            description="Form your party for battle!",
            color=discord.Color.red()
        )
        embed.add_field(name="Players", value="No players yet", inline=False)
        
        view = self.rpg_system.BattleSetupView(self)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @commands.hybrid_command(name="cyber_event")
    async def cyber_event(self, ctx):
        """Start a group event adventure"""
        embed = discord.Embed(
            title="🎲 Event Challenge",
            description="Form your party for an event challenge!",
            color=discord.Color.green()
        )
        embed.add_field(name="Players", value="No players yet", inline=False)
        
        view = self.rpg_system.BattleSetupView(self)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @commands.hybrid_command(name="cyber_story")
    async def cyber_story(self, ctx):
        """Start a group story adventure"""
        embed = discord.Embed(
            title="📖 Story Adventure",
            description="Form your party for a story adventure!",
            color=discord.Color.purple()
        )
        embed.add_field(name="Players", value="No players yet", inline=False)
        
        view = self.rpg_system.BattleSetupView(self)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    async def start_battle(self, channel, players: List[discord.User], rarity: str, battle_type: str):
        """Start a battle with the specified parameters"""
        battle_data = {
            "enemy_name": f"{rarity} {battle_type}",
            "enemy_hp": 100,
            "enemy_max_hp": 100,
            "damage_multiplier": 1.0,
            "enemy_multiplier": 1.0,
            "enemy_rarity": rarity.lower(),
            "enemy_type": battle_type.lower()
        }
        
        enemy = None
        if battle_type == "Monster":
            enemy = self.rpg_system.get_monster_by_rarity("monsters", rarity.lower())
            if enemy:
                battle_data["enemy_name"] = enemy["name"]
                battle_data["enemy_hp"] = enemy.get("health", 100)
                battle_data["enemy_max_hp"] = enemy.get("health", 100)
                battle_data["enemy_attack"] = enemy.get("attack", 15)
                battle_data["enemy_defense"] = enemy.get("defense", 10)
        elif battle_type == "Boss":
            enemy = self.rpg_system.get_monster_by_rarity("bosses", rarity.lower())
            if enemy:
                battle_data["enemy_name"] = enemy["name"]
                battle_data["enemy_hp"] = enemy.get("health", 200)
                battle_data["enemy_max_hp"] = enemy.get("health", 200)
                battle_data["enemy_attack"] = enemy.get("attack", 25)
                battle_data["enemy_defense"] = enemy.get("defense", 15)
                battle_data["enemy_multiplier"] = 1.5
        elif battle_type == "Titan":
            enemy = self.rpg_system.get_titan_for_fight()
            if enemy:
                battle_data["enemy_name"] = enemy["name"]
                battle_data["enemy_hp"] = enemy.get("health", 500)
                battle_data["enemy_max_hp"] = enemy.get("health", 500)
                battle_data["enemy_attack"] = enemy.get("attack", 40)
                battle_data["enemy_defense"] = enemy.get("defense", 25)
                battle_data["enemy_multiplier"] = 2.0

        embed = self.rpg_system.CybertronianBattleView(battle_data, players, self.rpg_system).get_battle_embed()
        view = self.rpg_system.CybertronianBattleView(battle_data, players, self.rpg_system)
        message = await channel.send(embed=embed, view=view)
        view.message = message

    async def handle_event_challenge(self, channel, players: List[discord.User], event: Dict, chosen_skill: str):
        """Handle an event challenge"""
        group_skill = self.calculate_group_skill(players, chosen_skill.lower())
        
        # Find the chosen skill in event
        skill_data = None
        for skill in event["skill_choices"]:
            if skill == chosen_skill:
                skill_data = {"skill": skill, "difficulty": event.get("difficulty", "moderate")}
                break

        if not skill_data:
            skill_data = {"skill": chosen_skill, "difficulty": "moderate"}

        # Roll for success
        roll = roll_d5()
        success_threshold = {"easy": 3, "moderate": 4, "hard": 5, "very_hard": 5}.get(skill_data["difficulty"], 4)
        
        success = (roll + group_skill) >= success_threshold

        # Award rewards
        base_xp = {"easy": 50, "moderate": 100, "hard": 150, "very_hard": 200}.get(skill_data["difficulty"], 100)
        
        if success:
            xp_reward = base_xp
            energon_reward = base_xp // 2
            loot = self.get_loot_drops("Rare")
            outcome_text = f"Success! The group used {chosen_skill} to overcome the challenge!"
        else:
            xp_reward = base_xp // 2
            energon_reward = base_xp // 4
            loot = []
            outcome_text = f"Partial success... The {chosen_skill} attempt wasn't fully successful."

        # Award to all players
        for player in players:
            await self.award_xp_and_check_level(str(player.id), xp_reward)
            self.rpg_system.add_energon_earned(str(player.id), energon_reward)

        self.save_characters_data()

        embed = discord.Embed(
            title="🎲 Event Result",
            description=outcome_text,
            color=discord.Color.green() if success else discord.Color.orange()
        )
        embed.add_field(name="Group Skill", value=f"{group_skill} (rolled {roll})", inline=False)
        embed.add_field(name="XP Reward", value=xp_reward, inline=True)
        embed.add_field(name="Energon Reward", value=energon_reward, inline=True)
        if loot:
            embed.add_field(name="Loot", value=", ".join([item["name"] for item in loot]), inline=False)

        await channel.send(embed=embed)

    async def handle_story_segment(self, channel, players: List[discord.User], story: Dict):
        """Handle a story segment with choices"""
        embed = discord.Embed(
            title=f"📖 {story['title']}",
            description=story['content'],
            color=discord.Color.purple()
        )
        
        if story.get('choices'):
            choices = [choice['text'] for choice in story['choices']]
            view = VotingView(choices, players)
            message = await channel.send(embed=embed, view=view)
            view.message = message
            await view.wait()
            
            chosen_choice = view.get_winner()
            
            # Find chosen choice data
            choice_data = None
            for choice in story['choices']:
                if choice['text'] == chosen_choice:
                    choice_data = choice
                    break
            
            if choice_data:
                # Award rewards
                xp_reward = choice_data.get('xp', 100)
                energon_reward = choice_data.get('energon', 50)
                
                for player in players:
                    await self.award_xp_and_check_level(str(player.id), xp_reward)
                    self.rpg_system.add_energon_earned(str(player.id), energon_reward)
                
                self.save_characters_data()
                
                result_embed = discord.Embed(
                    title="📖 Story Choice Result",
                    description=choice_data.get('outcome', 'Your choice affects the story...'),
                    color=discord.Color.purple()
                )
                result_embed.add_field(name="XP Reward", value=xp_reward, inline=True)
                result_embed.add_field(name="Energon Reward", value=energon_reward, inline=True)
                
                await channel.send(embed=result_embed)
        else:
            await channel.send(embed=embed)

    @commands.hybrid_command(name="cyber_info")
    async def cyber_info(self, ctx):
        """Show information about the Cybertronian RPG system"""
        embed = discord.Embed(
            title="🤖 Cybertronian RPG System",
            description="Welcome to the Transformers RPG! Here's how to play:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🎯 Getting Started",
            value="Use `/create_character` to create your character, then join group adventures!",
            inline=False
        )
        
        embed.add_field(
            name="⚔️ Battle System",
            value="Group battles against monsters, bosses, and titans. Work together to defeat powerful enemies!",
            inline=False
        )
        
        embed.add_field(
            name="🎲 Events",
            value="Random events with skill challenges. Choose your approach and see if your group succeeds!",
            inline=False
        )
        
        embed.add_field(
            name="📖 Stories",
            value="Interactive story segments with choices that affect your adventure!",
            inline=False
        )
        
        embed.add_field(
            name="🎮 Commands",
            value="`/cyber_random` - Random adventure\n`/cyber_battle` - Battle only\n`/cyber_event` - Event only\n`/cyber_story` - Story only",
            inline=False
        )
        
        await ctx.send(embed=embed)


    # ========== CORE RPG SYSTEM METHODS ==========

    def load_data(self):
        """Load all RPG system data (lazy loading)"""
        if self._data_loaded:
            return
            
        try:
            with open(os.path.join(JSON_DIR, 'monsters_and_bosses.json'), 'r') as f:
                self.monsters_data = json.load(f)
        except:
            self.monsters_data = {}
            
        try:
            with open(os.path.join(JSON_DIR, 'random_events.json'), 'r') as f:
                self.events_data = json.load(f)
        except:
            self.events_data = {}
            
        try:
            with open(os.path.join(JSON_DIR, 'story_segments.json'), 'r') as f:
                self.story_data = json.load(f)
        except:
            self.story_data = {}
            
        self._data_loaded = True

    def load_monsters_and_bosses(self):
        """Load monsters and bosses data"""
        try:
            file_path = os.path.join(self.json_base_path, "monsters_and_bosses.json")
            with open(file_path, 'r', encoding='utf-8') as f:
                self.monsters_and_bosses = json.load(f)
            self._monsters_loaded = True
        except FileNotFoundError:
            print(f"Warning: monsters_and_bosses.json not found")
            self.monsters_and_bosses = {}
        except Exception as e:
            print(f"Error loading monsters_and_bosses.json: {e}")
            self.monsters_and_bosses = {}

    def load_story_segments(self):
        """Load story segments data"""
        try:
            file_path = os.path.join(self.json_base_path, "story_segments.json")
            with open(file_path, 'r', encoding='utf-8') as f:
                self.story_segments = json.load(f)
            self._story_loaded = True
        except FileNotFoundError:
            print(f"Warning: story_segments.json not found")
            self.story_segments = {}
        except Exception as e:
            print(f"Error loading story_segments.json: {e}")
            self.story_segments = {}

    def load_random_events(self):
        """Load random events data"""
        try:
            file_path = os.path.join(self.json_base_path, "random_events.json")
            with open(file_path, 'r', encoding='utf-8') as f:
                self.random_events = json.load(f)
            self._events_loaded = True
        except FileNotFoundError:
            print(f"Warning: random_events.json not found")
            self.random_events = {}
        except Exception as e:
            print(f"Error loading random_events.json: {e}")
            self.random_events = {}

    def load_transformation_items(self):
        """Load transformation items (lazy loading)"""
        if self._transformation_items_loaded:
            return
            
        try:
            file_path = os.path.join(self.json_base_path, "transformation_items.json")
            with open(file_path, 'r', encoding='utf-8') as f:
                self.transformation_items = json.load(f)
        except FileNotFoundError:
            print(f"Warning: transformation_items.json not found")
            self.transformation_items = {}
        except Exception as e:
            print(f"Error loading transformation_items.json: {e}")
            self.transformation_items = {}
            
        self._transformation_items_loaded = True

    # ========== GROUP ADVENTURE HANDLERS ==========

    async def start_battle(self, channel, players, rarity, enemy_type):
        """Start a battle for group adventure"""
        enemy_data = None
        if enemy_type.lower() == "monster":
            enemy_data = self.rpg_system.get_monster_by_rarity("monster", rarity)
        elif enemy_type.lower() == "boss":
            enemy_data = self.rpg_system.get_monster_by_rarity("boss", rarity)
        elif enemy_type.lower() == "titan":
            enemy_data = self.rpg_system.get_titan_for_fight()
            
        if not enemy_data:
            await channel.send("❌ Could not find an enemy for this battle!")
            return
            
        battle_data = {
            'enemy_name': enemy_data['name'],
            'enemy_hp': enemy_data['health'],
            'enemy_max_hp': enemy_data['health'],
            'enemy_attack': enemy_data.get('attack', 10),
            'enemy_defense': enemy_data.get('defense', 5),
            'enemy_type': enemy_type.lower(),
            'enemy_rarity': enemy_data.get('rarity', 'common')
        }
        
        view = self.rpg_system.CybertronianBattleView(battle_data, players, self.rpg_system)
        
        embed = discord.Embed(
            title=f"⚔️ Group Battle: {enemy_data['name']}",
            description=f"Enemy HP: {enemy_data['health']}/{enemy_data['health']}",
            color=discord.Color.red()
        )
        
        message = await channel.send(embed=embed, view=view)
        view.message = message

    async def handle_event_challenge(self, channel, players, event, chosen_skill):
        """Handle event challenge for group adventure"""
        results = []
        
        for player in players:
            result = self.rpg_system.process_random_event(str(player.id), event.get('id'), chosen_skill)
            results.append((player, result))
            
        embed = discord.Embed(
            title=f"🎲 Event: {event['name']}",
            description=event['description'],
            color=discord.Color.green()
        )
        
        for player, result in results:
            if 'error' not in result:
                outcome = "✅ Success" if result.get('success', False) else "❌ Failed"
                embed.add_field(
                    name=f"{player.display_name}",
                    value=f"{outcome} - {result.get('result_text', 'No outcome')}",
                    inline=False
                )
        
        await channel.send(embed=embed)

    # Character management commands
    @app_commands.command(name='character_new', description='Create a new Transformers character')
    @app_commands.describe(
        name='Your character name',
        faction='Choose your faction',
        class_type='Choose your class - see /class_info for details'
    )
    @app_commands.choices(
        faction=[
            app_commands.Choice(name='🔴 Autobot', value='autobot'),
            app_commands.Choice(name='🟣 Decepticon', value='decepticon'),
        ],
        class_type=[
            app_commands.Choice(name="Scientist *Starting Stats ATT:4 DEF:2 DEX:2 CHA:0*", value="scientist"),
            app_commands.Choice(name="Warrior *Starting Stats ATT:4 DEF:1 DEX:2 CHA:1*", value="warrior"),
            app_commands.Choice(name="Engineer *Starting Stats ATT:2 DEF:4 DEX:2 CHA:0*", value="engineer"),
            app_commands.Choice(name="Mariner *Starting Stats ATT:1 DEF:4 DEX:0 CHA:2*", value="mariner"),
            app_commands.Choice(name="Scout *Starting Stats ATT:1 DEF:0 DEX:4 CHA:3*", value="scout"),   
            app_commands.Choice(name="Seeker *Starting Stats ATT:2 DEF:1 DEX:4 CHA:4*", value="seeker"),
            app_commands.Choice(name="Commander *Starting Stats ATT:2 DEF:1 DEX:1 CHA:4*", value="commander"),
            app_commands.Choice(name="Medic *Starting Stats ATT:0 DEF:1 DEX:3 CHA:4*", value="medic")
        ]
    )
    async def character_new(self, interaction: discord.Interaction, name: str, faction: str, class_type: str):
        """Create a new character with the given parameters"""
        # Check role requirement
        if not self.has_cybertronian_role(interaction.user):
            await interaction.response.send_message(
                "❌ You need a Cybertronian role (Autobot, Decepticon, Maverick, or Cybertronian_Citizen) to create characters!",
                ephemeral=True
            )
            return

        user_id = str(interaction.user.id)
        
        # Check character limit
        user_characters = self.rpg_system.get_user_characters(user_id)
        if len(user_characters) >= 3:
            await interaction.response.send_message(
                "❌ You already have 3 characters! Please delete one first.",
                ephemeral=True
            )
            return

        # Check if character name already exists
        user_characters = self.rpg_system.get_user_characters(user_id)
        for char in user_characters:
            if char.name.lower() == name.lower():
                await interaction.response.send_message(
                    f"❌ Character name '{name}' already exists! Please choose a different name.",
                    ephemeral=True
                )
                return

        # Create character with username
        username = interaction.user.display_name
        character = self.rpg_system.create_character(user_id, name, faction, class_type, username)
        
        # Get the main stat for this class type
        main_stat = self.rpg_system.get_stat_class_for_character(class_type)
        stat_emoji = {
            "ATT": "⚔️",
            "DEF": "🛡️", 
            "DEX": "🥷",
            "CHA": "💬"
        }
        
        embed = discord.Embed(
            title=f"✅ Character Created: {name}",
            description=f"**{faction.title()} {class_type.title()}** has joined the battle!",
            color=0x00ff00
        )
        embed.add_field(
            name="🎯 Main Stat Focus",
            value=f"{stat_emoji[main_stat]} **{main_stat}** - This class specializes in {main_stat} for health scaling and combat effectiveness!",
            inline=False
        )
        embed.set_footer(text="Use /character_view to see your characters")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name='character_view', description='View your characters with detailed stats')
    @app_commands.describe(character_name='Optional: View a specific character by name')
    async def character_view(self, interaction: discord.Interaction, character_name: Optional[str] = None):
        """View your characters with detailed stats"""
        await interaction.response.defer(ephemeral=True)
        
        if not self.has_cybertronian_role(interaction.user):
            await interaction.followup.send("❌ You need a Cybertronian role to use RPG commands!", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        username = interaction.user.display_name
        user_characters = self.rpg_system.get_user_characters(user_id, username)

        if not user_characters:
            embed = discord.Embed(
                title="🤖 No Characters Found",
                description="You haven't created any characters yet! Use `/character_new` to create your first character.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        if character_name:
            character = None
            for char in user_characters:
                if char.name.lower() == character_name.lower():
                    character = char
                    break
            
            if not character:
                await interaction.followup.send(f"❌ Character '{character_name}' not found!", ephemeral=True)
                return
            
            await self._show_detailed_character(interaction, character)
        else:
            await self._show_character_overview(interaction, user_characters)

    async def _show_detailed_character(self, interaction: discord.Interaction, character):
        """Show detailed view of a single character"""
        total_stats = self.rpg_system.calculate_total_stats_for_character(character)
        
        faction_emoji = "🔴" if character.faction == "autobot" else "🟣"
        color = 0x00ff00 if character.faction == "autobot" else 0xff4500
        
        embed = discord.Embed(
            title=f"{faction_emoji} {character.name}",
            description=f"**{character.faction.title()} {character.class_type.title()}**",
            color=color
        )
        
        embed.add_field(name="📊 Level", value=character.level, inline=True)
        embed.add_field(name="⭐ Experience", value=f"{character.experience} XP", inline=True)
        embed.add_field(name="💎 Energon Earned", value=character.energon_earned, inline=True)
        
        embed.add_field(
            name="🧮 Stats",
            value=f"⚔️ **ATT:** {total_stats.ATT}\n🛡️ **DEF:** {total_stats.DEF}\n🥷 **DEX:** {total_stats.DEX}\n💬 **CHA:** {total_stats.CHA}",
            inline=True
        )
        
        combat = character.combat_record
        embed.add_field(
            name="📋 Combat Record",
            value=f"🏅 **Wins:** {combat.total_wins}\n💀 **Losses:** {combat.total_losses}\n💥 **Damage Dealt:** {combat.total_damage_dealt}",
            inline=True
        )
        
        equipment_text = f"**Beast Modes:** {len(character.beast_modes)}\n**Transformations:** {len(character.transformations)}\n**Weapons:** {len(character.weapons)}\n**Armor:** {len(character.armor)}"
        embed.add_field(name="🎒 Equipment", value=equipment_text, inline=True)
        
        monsters_defeated = len(combat.monsters_defeated or [])
        bosses_defeated = len(combat.bosses_defeated or [])
        titans_defeated = len(combat.titans_defeated or [])
        
        embed.add_field(
            name="🏆 Victories",
            value=f"⚱️ **Monsters:** {monsters_defeated}\n⚰️ **Bosses:** {bosses_defeated}\n🪦 **Titans:** {titans_defeated}",
            inline=True
        )
        
        equipped_items = []
        if character.beast_modes:
            equipped_items.append(f"🦁 **Beast Mode:** {character.beast_modes[0] if character.beast_modes else 'None'}")
        if character.transformations:
            equipped_items.append(f"🔄 **Transformation:** {character.transformations[0] if character.transformations else 'None'}")
        if character.weapons:
            equipped_items.append(f"⚔️ **Weapon:** {character.weapons[0] if character.weapons else 'None'}")
        if character.armor:
            equipped_items.append(f"🪖 **Armor:** {character.armor[0] if character.armor else 'None'}")
        
        if equipped_items:
            embed.add_field(name="🔗 Currently Equipped", value="\n".join(equipped_items), inline=False)
        
        await interaction.followup.send(embed=embed)

    async def _show_character_overview(self, interaction: discord.Interaction, characters):
        """Show overview of all user characters"""
        embed = discord.Embed(
            title="🤖 Your Transformers Characters",
            description=f"You have {len(characters)}/3 characters",
            color=0x00ff99
        )
        
        for i, character in enumerate(characters, 1):
            faction_emoji = "🔴" if character.faction == "autobot" else "🟣"
            
            combat = character.combat_record
            monsters_defeated = len(combat.monsters_defeated or [])
            bosses_defeated = len(combat.bosses_defeated or [])
            titans_defeated = len(combat.titans_defeated or [])
            total_enemies = monsters_defeated + bosses_defeated + titans_defeated
            
            equipped = []
            if character.beast_modes:
                equipped.append(f"🦁{character.beast_modes[0]}")
            if character.transformations:
                equipped.append(f"🔄{character.transformations[0]}")
            if character.weapons:
                equipped.append(f"⚔️{character.weapons[0]}")
            if character.armor:
                equipped.append(f"🛡️{character.armor[0]}")
            
            equipped_text = ", ".join(equipped) if equipped else "None equipped"
            
            # Get class emoji based on main stat
            main_stat = self.rpg_system.get_stat_class_for_character(character.class_type)
            stat_emoji = {
                "ATT": "⚔️",
                "DEF": "🛡️",
                "DEX": "🥷",
                "CHA": "💬"
            }
            class_emoji = stat_emoji.get(main_stat, "⚔️")
            
            character_info = (
                f"{faction_emoji} **{character.faction.title()} {class_emoji} {character.class_type.title()}**\n"
                f"📊 Level {character.level} | ⭐ {character.experience} XP\n"
                f"👹 Enemies Defeated: {total_enemies}\n"
                f"🔗 Equipped: {equipped_text}"
            )
            
            embed.add_field(
                name=f"{i}. {character.name}",
                value=character_info,
                inline=True
            )
        
        await interaction.followup.send(embed=embed)

    async def character_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete for character names"""
        user_id = str(interaction.user.id)
        username = interaction.user.display_name
        characters = self.rpg_system.get_user_characters(user_id, username)
        return [
            app_commands.Choice(name=char.name, value=char.name)
            for char in characters
            if current.lower() in char.name.lower()
        ][:25]

    async def equipment_type_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete for equipment types"""
        types = ['characters', 'beast_modes', 'transformations', 'weapons', 'armor']
        return [
            app_commands.Choice(name=type.replace('_', ' ').title(), value=type)
            for type in types
            if current.lower() in type.lower()
        ]

    async def item_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete for items"""
        # Get the current command parameters
        namespace = interaction.namespace
        character_name = getattr(namespace, 'character_name', None)
        equipment_type = getattr(namespace, 'equipment_type', None)
        
        if not character_name or not equipment_type:
            return []
        
        user_id = str(interaction.user.id)
        characters = self.rpg_system.get_user_characters(user_id)
        
        # Find the selected character
        character = None
        for char in characters:
            if char.name.lower() == character_name.lower():
                character = char
                break
        
        if not character:
            return []
        
        # Get items of the selected type that the character owns
        items = getattr(character, equipment_type, [])
        
        # Filter items based on current input
        filtered_items = []
        for item_id in items:
            item_data = self.rpg_system.get_item_by_id(item_id)
            if item_data:
                item_name = item_data.get('name', item_id)
                if current.lower() in item_name.lower():
                    filtered_items.append(app_commands.Choice(name=item_name, value=item_id))
        
        return filtered_items[:25]
        
    @app_commands.command(name='equip', description='Equip items to your character')
    @app_commands.describe(
        character_name='Select your character',
        equipment_type='Select equipment type',
        item_name='Select item to equip',
        action='Equip or unequip the item'
    )
    @app_commands.choices(action=[
        app_commands.Choice(name='Equip', value='equip'),
        app_commands.Choice(name='Unequip', value='unequip')
    ])
    @app_commands.autocomplete(
        character_name=character_autocomplete,
        equipment_type=equipment_type_autocomplete,
        item_name=item_autocomplete
    )
    async def equip(self, interaction: discord.Interaction, character_name: str, equipment_type: str, item_name: str, action: str = 'equip'):
        """Equip or unequip items to/from your character"""
        if not self.has_cybertronian_role(interaction.user):
            await interaction.response.send_message("❌ Only Cybertronian Citizens can equip items!", ephemeral=True)
            return
            
        user_id = str(interaction.user.id)
        username = interaction.user.display_name
        
        user_characters = self.rpg_system.get_user_characters(user_id, username)
        character = None
        for char in user_characters:
            if char.name.lower() == character_name.lower():
                character = char
                break
        
        if not character:
            await interaction.response.send_message(f"❌ Character '{character_name}' not found!", ephemeral=True)
            return
        
        if action == 'equip':
            success, message = self.rpg_system.equip_item(user_id, character_name, item_name, equipment_type, username)
        else:
            success, message = self.rpg_system.unequip_item(user_id, character_name, item_name, equipment_type, username)
        
        if success:
            embed = discord.Embed(title="✅ Equipment Updated", description=message, color=0x00ff00)
            
            equipment_status = []
            if character.equipped_transformation:
                trans_data = self.rpg_system.get_item_by_id(character.equipped_transformation)
                equipment_status.append(f"🔄 **Transformation:** {trans_data.get('name', character.equipped_transformation) if trans_data else character.equipped_transformation}")
            
            if character.equipped_beast_mode:
                beast_data = self.rpg_system.get_item_by_id(character.equipped_beast_mode)
                equipment_status.append(f"🦁 **Beast Mode:** {beast_data.get('name', character.equipped_beast_mode) if beast_data else character.equipped_beast_mode}")
            
            if character.equipped_weapons:
                weapon_names = []
                for weapon_id in character.equipped_weapons:
                    weapon_data = self.rpg_system.get_item_by_id(weapon_id)
                    weapon_names.append(weapon_data.get('name', weapon_id) if weapon_data else weapon_id)
                equipment_status.append(f"⚔️ **Weapons ({len(character.equipped_weapons)}/2):** {', '.join(weapon_names)}")
            
            if character.equipped_armor:
                armor_data = self.rpg_system.get_item_by_id(character.equipped_armor)
                equipment_status.append(f"🛡️ **Armor:** {armor_data.get('name', character.equipped_armor) if armor_data else character.equipped_armor}")
            
            if equipment_status:
                embed.add_field(name="🔗 Currently Equipped", value="\n".join(equipment_status), inline=False)
            
            total_stats = self.rpg_system.calculate_total_stats_for_character(character)
            embed.add_field(
                name="📈 Total Stats",
                value=f"🗡️ ATT: {total_stats.ATT}|🛡️ **DEF:** {total_stats.DEF}|🥷 **DEX:** {total_stats.DEX}| 💬 **CHA:** {total_stats.CHA}",
                inline=True
            )
        else:
            embed = discord.Embed(title="❌ Equipment Error", description=message, color=0xff0000)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="start_cyberchronicles", description="Begin an AI-generated CyberChronicles adventure")
    async def start_cyberchronicles(self, interaction: discord.Interaction, character: str):
        """Start a CyberChronicles adventure session"""
        if not self.has_cybertronian_role(interaction.user):
            await interaction.response.send_message(
                "❌ You need a Cybertronian role to use this command!",
                ephemeral=True
            )
            return
        
        user_id = str(interaction.user.id)
        username = interaction.user.display_name
        
        user_characters = self.rpg_system.get_user_characters(user_id, username)
        selected_character = None
        for char in user_characters:
            if char.name.lower() == character.lower():
                selected_character = char
                break
        
        if not selected_character:
            await interaction.response.send_message("❌ Character not found!", ephemeral=True)
            return

        session = self.rpg_system.CyberChroniclesSession(interaction.channel, self.rpg_system)
        session.add_step_participant(user_id, selected_character.name)
        session.reset_step_participants()
        
        story_content = await self._generate_initial_story(selected_character)
        next_preview = session.generate_next_event_preview()
        
        embed = discord.Embed(
            title="🌟 CyberChronicles Adventure Begins!",
            description=story_content,
            color=0x00ff99
        )
        
        embed.add_field(name="🎭 Current Participants", value=f"👤 {interaction.user.display_name} ({selected_character.name})", inline=False)
        embed.add_field(name="🔮 Coming Next", value=f"{next_preview['type']}\n*{next_preview['description']}*", inline=False)
        
        view = self.rpg_system.CyberChroniclesView(session, show_start_button=True)
        
        await interaction.response.send_message(embed=embed, view=view)
        
        self.active_sessions[interaction.channel.id] = session
        asyncio.create_task(self._auto_update_story(session))

    @app_commands.command(name="stop_cyberchronicles", description="Stop the current CyberChronicles adventure session")
    async def stop_cyberchronicles(self, interaction: discord.Interaction):
        """Stop the current CyberChronicles adventure session"""
        if interaction.channel.id not in self.active_sessions:
            await interaction.response.send_message("❌ No active session in this channel!", ephemeral=True)
            return
        
        session = self.active_sessions[interaction.channel.id]
        
        embed = discord.Embed(
            title="🛑 CyberChronicles Adventure Ended",
            description="The adventure has been concluded.",
            color=0xff0000
        )
        
        if session.step_participants:
            participants_text = "\n".join([
                f"👤 {user_id} ({char_name})" 
                for user_id, char_name in session.step_participants.items()
            ])
            embed.add_field(name="Final Participants", value=participants_text, inline=False)
        
        del self.active_sessions[interaction.channel.id]
        await interaction.response.send_message(embed=embed)

    def has_cybertronian_role(self, user):
        """Check if user has required role"""
        required_roles = ['Autobot', 'Decepticon', 'Maverick', 'Cybertronian_Citizen']
        return any(role.name in required_roles for role in user.roles)

    @app_commands.command(name="kill_character", description="Delete one of your characters permanently")
    async def kill_character(self, interaction: discord.Interaction):
        """Delete one of your characters from the system"""
        if not self.has_cybertronian_role(interaction.user):
            await interaction.response.send_message(
                "❌ You need a Cybertronian role to use this command!",
                ephemeral=True
            )
            return
            
        user_id = str(interaction.user.id)
        characters = self.rpg_system.get_user_characters(user_id)
        
        if not characters:
            await interaction.response.send_message(
                "❌ You don't have any characters to delete!",
                ephemeral=True
            )
            return
        
        if len(characters) == 1:
            # Only one character, show confirmation
            character = characters[0]
            view = self.rpg_system.ConfirmCharacterDeletionView(self.rpg_system, user_id, character.name)
            
            embed = discord.Embed(
                title="⚠️ Delete Character",
                description=f"Are you sure you want to permanently delete **{character.name}**?",
                color=0xff0000
            )
            
            embed.add_field(
                name="Character Details",
                value=f"**Level:** {character.level}\n**Faction:** {character.faction.title()}\n**Class:** {character.class_type.title()}",
                inline=False
            )
            embed.set_footer(text="This action cannot be undone!")
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            # Multiple characters, show dropdown
            view = self.rpg_system.CharacterSelectionView(self.rpg_system, user_id)
            
            embed = discord.Embed(
                title="⚠️ Select Character to Delete",
                description="Choose which character you want to permanently delete from the dropdown below.",
                color=0xff0000
            )
            embed.set_footer(text="This action cannot be undone!")
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def handle_story_segment(self, channel, players, story):
        """Handle story segment for group adventure"""
        embed = discord.Embed(
            title="📖 Story Segment",
            description=story.get('text', 'An interesting story unfolds...'),
            color=discord.Color.blue()
        )
        
        await channel.send(embed=embed)

    async def cleanup_session(self, channel_id):
        """Clean up active session"""
        if channel_id in self.active_sessions:
            del self.active_sessions[channel_id]

    # ========== SETUP ==========

    @commands.Cog.listener()
    async def on_ready(self):
        """Called when the cog is ready"""
        print(f"✅ RPGCommands cog loaded successfully!")

async def setup(bot):
    """Setup function for Discord.py"""
    await bot.add_cog(RPGCommands(bot))