import discord
import os
import json
import random
import asyncio
from typing import List, Dict, Any, Optional
from discord.ext import commands
from discord import app_commands
from .rpg_system import TransformersAIDnD, get_rpg_system, RPGEvent, StoryMoment

# Utility function for rolling
import logging
logger = logging.getLogger('rpg_commands')

class RPGCommands(commands.Cog):
    """Unified Discord commands for the Transformers RPG system"""
    
    def __init__(self, bot):
        self.bot = bot
        self.rpg_system = TransformersAIDnD()
        self.active_sessions = {}
        self.ai_director = None
        
        # Use user_data_manager for all data operations
        # Use relative import for better portability
        try:
            from ..user_data_manager import user_data_manager
            self.user_data_manager = user_data_manager
        except ImportError:
            # Fallback to absolute import if relative fails
            import sys
            import os
            # Add parent directory to path dynamically
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            from Systems.user_data_manager import user_data_manager
            self.user_data_manager = user_data_manager
        
        # Initialize AI if API key available
        try:
            import google.generativeai as genai
            genai.configure(api_key=os.getenv('GEMINI_API_KEY', ''))
            self.gemini_model = genai.GenerativeModel('gemini-pro')
            self.ai_director = self.rpg_system
        except:
            self.gemini_model = None
            self.ai_director = self.rpg_system

    async def _load_data_async(self, data_type: str) -> Dict[str, Any]:
        """Optimized data loading using user_data_manager"""
        try:
            if data_type == "monsters_and_bosses":
                return await self.user_data_manager.get_monsters_and_bosses_data()
            elif data_type == "random_events":
                return await self.user_data_manager.get_random_events()
            elif data_type == "story_segments":
                return await self.user_data_manager.get_story_segments()
            return {}
        except Exception as e:
            print(f"Error loading {data_type}: {e}")
            return {}

    async def save_pets_data(self):
        """Save all characters to JSON - now handled by user_data_manager"""
        # This method is now redundant as user_data_manager handles saving
        pass

    def calculate_xp_needed(self, level: int) -> int:
        """Calculate XP needed for next level"""
        return 100 * level * level

    def calculate_stat_increase(self, level: int) -> int:
        """Calculate stat increase based on level"""
        return 2 + (level // 5)

    async def get_loot_drops(self, rarity: str) -> List[Dict]:
        """Get loot drops based on rarity from pet equipment"""
        try:
            # Load pet equipment data instead of transformation items
            equipment_data = await self.user_data_manager.get_pet_equipment_data()
            
            if not equipment_data:
                return [{"name": f"{rarity} Energon Cube", "type": "consumable", "value": 10}]
            
            # Filter items by rarity
            rarity_map = {
                "common": "common",
                "uncommon": "uncommon", 
                "rare": "rare",
                "epic": "epic",
                "legendary": "legendary"
            }
            
            target_rarity = rarity_map.get(rarity.lower(), "common")
            all_items = []
            
            # Process pet equipment data structure
            # Equipment categories in pet_equipment.json: chassis_plating, energy_cores, utility_modules
            equipment_categories = ['chassis_plating', 'energy_cores', 'utility_modules']
            
            for category in equipment_categories:
                if category in equipment_data and isinstance(equipment_data[category], dict):
                    category_data = equipment_data[category]
                    if 'equipment' in category_data and target_rarity in category_data['equipment']:
                        # Get items from the specific rarity tier
                        rarity_items = category_data['equipment'][target_rarity]
                        for item_id, item_data in rarity_items.items():
                            if isinstance(item_data, dict):
                                item_copy = dict(item_data)
                                item_copy['id'] = item_id
                                item_copy['category'] = category
                                all_items.append(item_copy)
            
            # Return up to 3 random items of the correct rarity
            if all_items:
                return random.sample(all_items, min(3, len(all_items)))
            
            return [{"name": f"{rarity} Energon Cube", "type": "consumable", "value": 10}]
            
        except Exception as e:
            print(f"Error getting loot drops: {e}")
            return [{"name": f"{rarity} Energon Cube", "type": "consumable", "value": 10}]

    async def award_xp_and_check_level(self, user_id: str, xp_amount: int, username: str = None):
        """Award XP and check for level up using the pet leveling system"""
        level_up_result = await self.rpg_system.gain_pet_experience(user_id, xp_amount, "rpg_activity")
        
        if level_up_result["leveled_up"]:
            return True
        return False

    def has_cybertronian_role(self, user):
        """Check if user has required role"""
        required_roles = ['Autobot', 'Decepticon', 'Maverick', 'Cybertronian_Citizen']
        return any(role.name in required_roles for role in user.roles)

    async def handle_ai_event(self, channel, players: List[discord.User], pets: List):
        """Handle AI-generated event with resource costs"""
        try:
            # Get the new AI D&D system
            ai_system = self.rpg_system
            
            # Generate AI event
            event = await ai_system.generate_ai_event(pets)
            
            # Create event embed
            embed = discord.Embed(
                title=f"🎯 {event.name}",
                description=event.description,
                color=discord.Color.blue()
            )
            
            # Show resource costs
            if event.resource_costs:
                cost_text = ""
                for cost in event.resource_costs:
                    cost_text += f"{cost.resource_type}: {cost.amount} "
                embed.add_field(name="💰 Resource Costs", value=cost_text, inline=False)
            
            # Show party members and their pets
            party_text = ""
            for i, player in enumerate(players):
                if i < len(pets):
                    pet = pets[i]
                    party_text += f"👤 {player.display_name} ({pet.name} - Lv.{pet.level})\n"
            embed.add_field(name="🤖 Party Members", value=party_text, inline=False)
            
            # Create choice view
            view = AIEventChoiceView(event, players, pets, ai_system, self)
            message = await channel.send(embed=embed, view=view)
            view.message = message
            
        except Exception as e:
            logger.error(f"Error in handle_ai_event: {e}")
            error_embed = discord.Embed(
                title="❌ Event Error",
                description=f"Failed to generate AI event: {str(e)}",
                color=discord.Color.red()
            )
            await channel.send(embed=error_embed)

    async def handle_ai_battle(self, channel, players: List[discord.User], pets: List, enemy_type: str = "random"):
        """Handle AI-generated battle with encounter text"""
        try:
            ai_system = self.rpg_system
            
            # Generate enemy and encounter text
            battle_data = await ai_system.generate_ai_battle(pets, enemy_type)
            
            # Create battle embed with AI-generated encounter text
            embed = discord.Embed(
                title=f"⚔️ {battle_data['enemy_name']}",
                description=battle_data['encounter_text'],
                color=discord.Color.red()
            )
            
            embed.add_field(
                name="❤️ Enemy HP", 
                value=f"{battle_data['enemy_hp']}/{battle_data['enemy_max_hp']}", 
                inline=True
            )
            
            # Show party
            party_text = ""
            for i, player in enumerate(players):
                if i < len(pets):
                    pet = pets[i]
                    party_text += f"👤 {player.display_name} ({pet.name} - Lv.{pet.level})\n"
            embed.add_field(name="🤖 Your Party", value=party_text, inline=False)
            
            # Create battle view (integrate with existing battle system)
            from ..PetBattles.battle_system import UnifiedBattleView
            battle_view = UnifiedBattleView(battle_data, players, self)
            
            message = await channel.send(embed=embed, view=battle_view)
            battle_view.message = message
            
            # Store battle data for post-battle AI text generation
            battle_view.ai_system = ai_system
            battle_view.pets = pets
            
        except Exception as e:
            logger.error(f"Error in handle_ai_battle: {e}")
            error_embed = discord.Embed(
                title="❌ Battle Error",
                description=f"Failed to generate AI battle: {str(e)}",
                color=discord.Color.red()
            )
            await channel.send(embed=error_embed)

    async def handle_ai_story(self, channel, players: List[discord.User], pets: List):
        """Handle AI-generated story segment"""
        try:
            ai_system = self.rpg_system
            
            # Generate AI story
            story = await ai_system.generate_ai_story_segment(pets)
            
            # Create story embed
            embed = discord.Embed(
                title=f"📖 {story.title}",
                description=story.content,
                color=discord.Color.purple()
            )
            
            # Show party
            party_text = ""
            for i, player in enumerate(players):
                if i < len(pets):
                    pet = pets[i]
                    party_text += f"👤 {player.display_name} ({pet.name} - Lv.{pet.level})\n"
            embed.add_field(name="🤖 Your Party", value=party_text, inline=False)
            
            # Add story context
            if story.context:
                embed.add_field(name="🌍 Context", value=story.context, inline=False)
            
            await channel.send(embed=embed)
            
            # If there are choices, create a voting view
            if story.choices:
                choices = [choice.text for choice in story.choices]
                view = AIStoryChoiceView(choices, players, story, ai_system, self)
                message = await channel.send("What should the party do next?", view=view)
                view.message = message
                
        except Exception as e:
            logger.error(f"Error in handle_ai_story: {e}")
            error_embed = discord.Embed(
                title="❌ Story Error",
                description=f"Failed to generate AI story: {str(e)}",
                color=discord.Color.red()
            )
            await channel.send(embed=error_embed)

    async def _generate_initial_story(self, pet):
        """Generate initial story content for a pet adventure"""
        prompt = f"""Create an engaging starting scene for a Transformers-themed RPG adventure featuring a mechanical pet.
        
Pet: {pet.name}
Faction: {pet.faction}
Stats: ATT {pet.ATT}, DEF {pet.DEF}, DEX {pet.DEX}, CHA {pet.CHA}

The adventure should begin in a mysterious location on Cybertron. Include:
- A vivid description of the environment
- An interesting situation or mystery to investigate
- 2-3 meaningful choices for the pet to make
- Keep it concise but atmospheric (150-200 words)

Format the response as:
**Scene: [Scene Name]**
[Description]

**Choices:**
1. [Choice 1]
2. [Choice 2] 
3. [Choice 3]"""

        return await self.generate_ai_story(prompt)

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
        
        # Load data asynchronously
        if battle_type == "Monster":
            monsters_data = await self._load_data_async("monsters_and_bosses")
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

    async def handle_first_react_event(self, channel, players: List[discord.User], event: Dict):
        """Handle a group event using first-to-react system"""
        # Create event embed
        embed = discord.Embed(
            title=f"🎯 {event['name']}",
            description=event['description'],
            color=discord.Color.blue()
        )
        
        # Add party info
        party_names = [player.display_name for player in players]
        embed.add_field(name="🤖 Party Members", value=", ".join(party_names), inline=False)
        
        # Create participants list for FirstReactView
        participants = [{'user_id': str(p.id), 'name': p.display_name} for p in players]
        
        # Create and send FirstReactView
        view = self.rpg_system.FirstReactView(participants)
        message = await channel.send(embed=embed, view=view)
        view.message = message
        
        # Wait for choice
        await view.wait()
        
        if view.chosen_skill and view.chosen_by:
            chosen_skill = view.chosen_skill
            chosen_by = view.chosen_by
            
            # Get skill data from event choices (now using success chances)
            skill_data = None
            for skill_key, skill_info in event.get('choices', {}).items():
                if skill_key == chosen_skill or skill_info.get('skill') == chosen_skill:
                    skill_data = skill_info
                    break
            
            if not skill_data:
                # Create fallback skill data with success chance
                skill_data = {
                    'skill': chosen_skill,
                    'description': f'Use {chosen_skill} to overcome the challenge',
                    'success': f'Your {chosen_skill} approach succeeds!',
                    'failure': f'Your {chosen_skill} approach falls short...',
                    'success_chance': 65  # Default success chance
                }
            
            # Roll for success based on success chance (not skill check)
            success_chance = skill_data.get('success_chance', 65)
            roll = random.randint(1, 100)
            success = roll <= success_chance
            
            # Award rewards using the new system
            try:
                # Prepare event data for reward distribution
                event_data = {
                    'name': event['name'],
                    'type': 'event',
                    'difficulty': event.get('difficulty', 'moderate'),
                    'rarity': event.get('rarity', 'common'),
                    'base_xp': {"easy": 50, "moderate": 100, "hard": 150, "very_hard": 200}.get(difficulty, 100),
                    'base_loot_value': {"easy": 25, "moderate": 50, "hard": 75, "very_hard": 100}.get(difficulty, 50)
                }
                
                # Distribute rewards using the new system
                rewards = await self.rpg_system.distribute_group_rewards(players, event_data, success)
                
                # Create outcome embed
                if success:
                    outcome_text = f"🎉 **{chosen_by.display_name}** led the party using **{chosen_skill}** to succeed!"
                    result_desc = skill_data.get('success', 'The party overcomes the challenge!')
                    color = discord.Color.green()
                else:
                    outcome_text = f"⚠️ **{chosen_by.display_name}** chose **{chosen_skill}**, but it wasn't enough..."
                    result_desc = skill_data.get('failure', 'The challenge proves difficult...')
                    color = discord.Color.orange()
                
                result_embed = discord.Embed(
                    title="🎯 Event Result",
                    description=outcome_text,
                    color=color
                )
                result_embed.add_field(name="📋 Result", value=result_desc, inline=False)
                result_embed.add_field(name="🎲 Success Chance", value=f"{success_chance}% (rolled {roll})", inline=False)
                
                # Display rewards summary
                if rewards:
                    reward_text = ""
                    for reward in rewards:
                        if reward['user']:
                            loot_names = [item['name'] for item in reward['loot']]
                            loot_str = ", ".join(loot_names) if loot_names else "None"
                            reward_text += f"**{reward['user'].display_name}**: {reward['xp']} XP, {loot_str}\n"
                    
                    if reward_text:
                        result_embed.add_field(name="🎖️ Rewards", value=reward_text, inline=False)
                
                await channel.send(embed=result_embed)
                
            except Exception as e:
                logger.error(f"Error in handle_first_react_event: {e}")
                error_embed = discord.Embed(
                    title="❌ Error",
                    description=f"An error occurred during the event: {str(e)}",
                    color=discord.Color.red()
                )
                await channel.send(embed=error_embed)
            
        else:
            # Timeout
            timeout_embed = discord.Embed(
                title="⏰ Event Timeout",
                description="No one chose an approach in time!",
                color=discord.Color.red()
            )
            await channel.send(embed=timeout_embed)

    async def handle_event_challenge(self, channel, players: List[discord.User], event: Dict, chosen_skill: str):
        """Handle an event challenge using success chances instead of skill checks"""
        
        # Find the chosen skill in event choices
        skill_data = None
        for skill_key, skill_info in event.get('choices', {}).items():
            if skill_key == chosen_skill or skill_info.get('skill') == chosen_skill:
                skill_data = skill_info
                break

        if not skill_data:
            # Create fallback skill data with success chance
            skill_data = {
                'skill': chosen_skill,
                'description': f'Use {chosen_skill} to overcome the challenge',
                'success': f'Your {chosen_skill} approach succeeds!',
                'failure': f'Your {chosen_skill} approach falls short...',
                'success_chance': 65  # Default success chance
            }

        # Roll for success based on success chance (not skill check)
        success_chance = skill_data.get('success_chance', 65)
        roll = random.randint(1, 100)
        success = roll <= success_chance

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
            await self.user_data_manager.add_energon(str(player.id), energon_reward, "rpg_activity")

        embed = discord.Embed(
            title="🎲 Event Result",
            description=outcome_text,
            color=discord.Color.green() if success else discord.Color.orange()
        )
        embed.add_field(name="Success Chance", value=f"{success_chance}% (rolled {roll})", inline=False)
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
                    await self.user_data_manager.add_energon(str(player.id), energon_reward, "rpg_activity")
                
                self.save_pets_data()
                
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
        """Show information about the AI-powered Cybertronian RPG system"""
        embed = discord.Embed(
            title="🤖 Cybertronian RPG System",
            description="Welcome to the AI-powered Transformers RPG! Experience dynamic adventures with Google Gemini AI storytelling.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🎯 Getting Started",
            value="Create your pet using the EnergonPets system, then form parties for AI-generated adventures! Each pet's level and equipment affect their effectiveness.",
            inline=False
        )
        
        embed.add_field(
            name="⚡ Resource System",
            value="Pets have three resources that affect adventures:\n🔋 **Energy** - Physical activities and combat\n🔧 **Maintenance** - Repairs and technical challenges\n😊 **Happiness** - Social interactions and diplomacy",
            inline=False
        )
        
        embed.add_field(
            name="🎲 AI Event System",
            value="Dynamic events with resource costs and success chances based on your pet's level and equipment. AI generates unique scenarios with meaningful consequences!",
            inline=False
        )
        
        embed.add_field(
            name="⚔️ AI Battle Encounters",
            value="AI-generated battle descriptions and outcomes. Victory brings XP and loot scaled to your effective level (base level + equipment bonuses).",
            inline=False
        )
        
        embed.add_field(
            name="📖 Story Continuity",
            value="AI remembers your adventure history and creates connected story segments. Each choice affects future events and builds your unique narrative!",
            inline=False
        )
        
        embed.add_field(
            name="🎮 Adventure Types",
            value="**`/cyber_random`** - AI chooses adventure type\n**`/cyber_battle`** - Combat-focused encounters\n**`/cyber_event`** - Resource challenge events\n**`/cyber_story`** - Narrative story segments\n**`/start_cyberchronicles`** - Solo AI adventure session",
            inline=False
        )
        
        embed.add_field(
            name="🏆 Rewards & Progression",
            value="Earn XP, loot, and resources. Equipment provides stat bonuses that increase your effective level. Story moments are tracked for continuity.",
            inline=False
        )
        
        embed.set_footer(text="Form parties and let the AI create your unique Transformers adventure!")
        
        await ctx.send(embed=embed)



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

    @app_commands.command(name="start_cyberchronicles", description="Begin an AI-generated CyberChronicles adventure")
    async def start_cyberchronicles(self, interaction: discord.Interaction, pet: str):
        """Start a CyberChronicles adventure session"""
        if not self.has_cybertronian_role(interaction.user):
            await interaction.response.send_message(
                "❌ You need a Cybertronian role to use this command!",
                ephemeral=True
            )
            return
        
        user_id = str(interaction.user.id)
        username = interaction.user.display_name
        
        user_pets = self.rpg_system.get_user_pets(user_id, username)
        selected_pet = None
        for p in user_pets:
            if p.name.lower() == pet.lower():
                selected_pet = p
                break
        
        if not selected_pet:
            await interaction.response.send_message("❌ Pet not found!", ephemeral=True)
            return

        session = self.rpg_system.CyberChroniclesSession(interaction.channel, self.rpg_system)
        session.add_step_participant(user_id, selected_pet.name)
        session.reset_step_participants()
        
        story_content = await self._generate_initial_story(selected_pet)
        next_preview = session.generate_next_event_preview()
        
        embed = discord.Embed(
            title="🌟 CyberChronicles Adventure Begins!",
            description=story_content,
            color=0x00ff99
        )
        
        embed.add_field(name="🎭 Current Participants", value=f"👤 {interaction.user.display_name} ({selected_pet.name})", inline=False)
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
                f"👤 {user_id} ({pet_name})" 
                for user_id, pet_name in session.step_participants.items()
            ])
            embed.add_field(name="Final Participants", value=participants_text, inline=False)
        
        del self.active_sessions[interaction.channel.id]
        await interaction.response.send_message(embed=embed)

    @commands.hybrid_command(name="cyber_random")
    async def cyber_random(self, ctx):
        """Start a random AI-generated group adventure"""
        embed = discord.Embed(
            title="🤖 AI Cybertronian Adventure",
            description="Form your party and embark on an AI-generated adventure!",
            color=discord.Color.blue()
        )
        embed.add_field(name="Players", value="No players yet", inline=False)
        embed.add_field(name="🎲 Adventure Type", value="Random AI Event", inline=False)
        
        view = self.rpg_system.AIAdventureSetupView(self, "random")
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @commands.hybrid_command(name="cyber_battle")
    async def cyber_battle(self, ctx):
        """Start an AI-generated group battle adventure"""
        embed = discord.Embed(
            title="⚔️ AI Battle Formation",
            description="Form your party for an AI-generated battle!",
            color=discord.Color.red()
        )
        embed.add_field(name="Players", value="No players yet", inline=False)
        embed.add_field(name="🎯 Battle Type", value="AI-Generated Enemy", inline=False)
        
        view = self.rpg_system.AIAdventureSetupView(self, "battle")
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @commands.hybrid_command(name="cyber_event")
    async def cyber_event(self, ctx):
        """Start an AI-generated group event adventure"""
        embed = discord.Embed(
            title="🎲 AI Event Challenge",
            description="Form your party for an AI-generated event challenge!",
            color=discord.Color.green()
        )
        embed.add_field(name="Players", value="No players yet", inline=False)
        embed.add_field(name="🎯 Event Type", value="AI-Generated Event with Resource Costs", inline=False)
        
        view = self.rpg_system.AIAdventureSetupView(self, "event")
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @commands.hybrid_command(name="cyber_story")
    async def cyber_story(self, ctx):
        """Start an AI-generated group story adventure"""
        embed = discord.Embed(
            title="📖 AI Story Adventure",
            description="Form your party for an AI-generated story adventure!",
            color=discord.Color.purple()
        )
        embed.add_field(name="Players", value="No players yet", inline=False)
        embed.add_field(name="📚 Story Type", value="AI-Generated Story with Choices", inline=False)
        
        view = self.rpg_system.AIAdventureSetupView(self, "story")
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    async def cleanup_session(self, channel_id):
        """Clean up active session"""
        if channel_id in self.active_sessions:
            del self.active_sessions[channel_id]

    async def load_data_async(self):
        """Async version of data loading using user_data_manager"""
        return await self._load_data_async("all")

    async def load_monsters_and_bosses_async(self):
        """Load monsters and bosses data using user_data_manager"""
        data = await self._load_data_async("monsters_and_bosses")
        self.monsters_and_bosses = data or {}

    async def load_story_segments_async(self):
        """Load story segments data using user_data_manager"""
        data = await self._load_data_async("story_segments")
        self.story_segments = data or {}

    async def load_random_events_async(self):
        """Load random events data using user_data_manager"""
        data = await self._load_data_async("random_events")
        self.random_events = data or {}

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

    @commands.Cog.listener()
    async def on_ready(self):
        """Called when the cog is ready"""
        print(f"✅ RPGCommands cog loaded successfully!")

class AIEventChoiceView(discord.ui.View):
    """View for handling AI event choices with resource costs"""
    
    def __init__(self, event: RPGEvent, players: List[discord.User], pets: List, ai_system, rpg_commands):
        super().__init__(timeout=60)
        self.event = event
        self.players = players
        self.pets = pets
        self.ai_system = ai_system
        self.rpg_commands = rpg_commands
        self.message = None
        self.choice_made = False
        
        # Add choice buttons
        self.add_item(discord.ui.Button(
            label="Pay Resource Cost",
            style=discord.ButtonStyle.green,
            emoji="💰",
            custom_id="pay_cost"
        ))
        self.add_item(discord.ui.Button(
            label="Refuse & Fight!",
            style=discord.ButtonStyle.red,
            emoji="⚔️",
            custom_id="refuse_fight"
        ))
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the user can interact with this view"""
        return interaction.user in self.players
    
    async def on_timeout(self):
        """Handle timeout"""
        if not self.choice_made and self.message:
            timeout_embed = discord.Embed(
                title="⏰ Event Timeout",
                description="No choice was made in time! The event passes...",
                color=discord.Color.red()
            )
            await self.message.edit(embed=timeout_embed, view=None)
    
    @discord.ui.button(label="Pay Resource Cost", style=discord.ButtonStyle.green, emoji="💰", custom_id="pay_cost")
    async def pay_cost_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle paying the resource cost"""
        if interaction.user not in self.players:
            await interaction.response.send_message("❌ You're not part of this party!", ephemeral=True)
            return
        
        self.choice_made = True
        
        try:
            # Process resource cost payment
            result = await self.ai_system.handle_event_choice(
                self.players, self.pets, self.event, accept_cost=True
            )
            
            # Create result embed
            result_embed = discord.Embed(
                title="✅ Event Success!",
                description=result['story_text'],
                color=discord.Color.green()
            )
            
            # Show resource costs paid
            if result['resources_spent']:
                cost_text = ""
                for resource, amount in result['resources_spent'].items():
                    cost_text += f"{resource}: -{amount}\n"
                result_embed.add_field(name="💰 Resources Spent", value=cost_text, inline=False)
            
            # Show rewards
            if result['rewards']:
                reward_text = ""
                for reward in result['rewards']:
                    reward_text += f"{reward['type']}: {reward['value']}\n"
                result_embed.add_field(name="🎁 Rewards", value=reward_text, inline=False)
            
            # Show XP and loot
            if result['xp_earned'] > 0 or result['loot']:
                xp_text = f"XP: +{result['xp_earned']}" if result['xp_earned'] > 0 else ""
                loot_text = f"Loot: {', '.join(result['loot'])}" if result['loot'] else ""
                result_embed.add_field(name="🎖️ Gains", value=f"{xp_text}\n{loot_text}", inline=False)
            
            await interaction.response.edit_message(embed=result_embed, view=None)
            
        except Exception as e:
            logger.error(f"Error processing event cost payment: {e}")
            error_embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to process event: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=error_embed, view=None)
    
    @discord.ui.button(label="Refuse & Fight!", style=discord.ButtonStyle.red, emoji="⚔️", custom_id="refuse_fight")
    async def refuse_fight_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle refusing cost and starting battle"""
        if interaction.user not in self.players:
            await interaction.response.send_message("❌ You're not part of this party!", ephemeral=True)
            return
        
        self.choice_made = True
        
        try:
            # Process refusal and trigger battle
            result = await self.ai_system.handle_event_choice(
                self.players, self.pets, self.event, accept_cost=False
            )
            
            # Create battle trigger embed
            battle_embed = discord.Embed(
                title="⚔️ Battle Triggered!",
                description=result['story_text'],
                color=discord.Color.red()
            )
            
            await interaction.response.edit_message(embed=battle_embed, view=None)
            
            # Start the battle
            await self.rpg_commands.handle_ai_battle(
                interaction.channel, self.players, self.pets, "random"
            )
            
        except Exception as e:
            logger.error(f"Error processing battle trigger: {e}")
            error_embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to trigger battle: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=error_embed, view=None)


class AIStoryChoiceView(discord.ui.View):
    """View for handling AI story choices"""
    
    def __init__(self, choices: List[str], players: List[discord.User], story: StoryMoment, ai_system, rpg_commands):
        super().__init__(timeout=60)
        self.choices = choices
        self.players = players
        self.story = story
        self.ai_system = ai_system
        self.rpg_commands = rpg_commands
        self.message = None
        self.choice_made = False
        
        # Add choice buttons
        for i, choice in enumerate(choices):
            self.add_item(discord.ui.Button(
                label=f"Choice {i+1}: {choice[:50]}{'...' if len(choice) > 50 else ''}",
                style=discord.ButtonStyle.blurple,
                custom_id=f"choice_{i}"
            ))
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the user can interact with this view"""
        return interaction.user in self.players
    
    async def on_timeout(self):
        """Handle timeout"""
        if not self.choice_made and self.message:
            timeout_embed = discord.Embed(
                title="⏰ Story Timeout",
                description="No choice was made in time! The story continues...",
                color=discord.Color.red()
            )
            await self.message.edit(embed=timeout_embed, view=None)
    
    @discord.ui.button(label="Choice 1", style=discord.ButtonStyle.blurple, custom_id="choice_0")
    async def choice_1_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle choice 1"""
        await self.process_story_choice(interaction, 0)
    
    @discord.ui.button(label="Choice 2", style=discord.ButtonStyle.blurple, custom_id="choice_1")
    async def choice_2_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle choice 2"""
        await self.process_story_choice(interaction, 1)
    
    @discord.ui.button(label="Choice 3", style=discord.ButtonStyle.blurple, custom_id="choice_2")
    async def choice_3_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle choice 3"""
        await self.process_story_choice(interaction, 2)
    
    async def process_story_choice(self, interaction: discord.Interaction, choice_index: int):
        """Process the selected story choice"""
        if interaction.user not in self.players:
            await interaction.response.send_message("❌ You're not part of this party!", ephemeral=True)
            return
        
        self.choice_made = True
        
        try:
            # Get the chosen choice
            if choice_index < len(self.story.choices):
                chosen_choice = self.story.choices[choice_index]
                
                # Process the choice and get next story segment
                next_story = await self.ai_system.process_story_choice(
                    self.players, chosen_choice
                )
                
                # Create result embed
                result_embed = discord.Embed(
                    title=f"📖 Story Continues",
                    description=next_story.content,
                    color=discord.Color.purple()
                )
                
                # Show consequences if any
                if chosen_choice.consequences:
                    result_embed.add_field(
                        name="⚡ Consequences", 
                        value=chosen_choice.consequences, 
                        inline=False
                    )
                
                # Show rewards if any
                if chosen_choice.rewards:
                    reward_text = ""
                    for reward in chosen_choice.rewards:
                        reward_text += f"{reward['type']}: {reward['value']}\n"
                    result_embed.add_field(name="🎁 Rewards", value=reward_text, inline=False)
                
                await interaction.response.edit_message(embed=result_embed, view=None)
                
                # If the next story has choices, create a new view
                if next_story.choices:
                    choices = [choice.text for choice in next_story.choices]
                    new_view = AIStoryChoiceView(choices, self.players, next_story, self.ai_system, self.rpg_commands)
                    new_message = await interaction.channel.send("What should the party do next?", view=new_view)
                    new_view.message = new_message
                
            else:
                await interaction.response.edit_message(
                    embed=discord.Embed(
                        title="❌ Invalid Choice",
                        description="That choice is not available.",
                        color=discord.Color.red()
                    ), 
                    view=None
                )
                
        except Exception as e:
            logger.error(f"Error processing story choice: {e}")
            error_embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to process story choice: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=error_embed, view=None)


async def setup(bot):
    """Setup function for Discord.py"""
    await bot.add_cog(RPGCommands(bot))