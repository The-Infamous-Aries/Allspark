import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
import logging
from groq import Groq
from typing import Dict, List, Any, Union
import json
from datetime import datetime, timedelta
from discord.ui import Button, View
import sys
import os
import re

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import GROQ_API_KEY, ROLE_IDS

logger = logging.getLogger("allspark.cybertron_games")

class CybertronGamesGenerator:
    """AI-powered Transformers-themed Cybertron Games story generator"""
    
    def __init__(self, api_key: str = None):
        """Initialize the AI Cybertron Games Generator with Groq API"""
        self.game_state: Dict[str, Any] = {}
        self.round_history: List[str] = []
        self.faction_tracker = {}   # Track faction assignments
        self.active_games = {}
        self.active_views = {}
        
        if api_key:
            try:
                self.client = Groq(api_key=api_key)
                self.model = "llama-3.1-8b-instant" # or "mixtral-8x7b-32768"
                self.use_ai = True
                print(f"✅ AI initialized successfully with Groq API for Cybertron Games")
            except Exception as e:
                print(f"❌ Failed to initialize AI: {e}")
                self.use_ai = False
                self.model = None
        else:
            print("⚠️  No API key provided - using fallback cybertronian narratives")
            self.use_ai = False
            self.model = None

    def has_cybertronian_role(self, member: discord.Member) -> bool:
        """Check if a member has any Cybertronian role using the new multiple role ID system"""
        cybertronian_roles = []
        for role_name in ['Autobot', 'Decepticon', 'Maverick', 'Cybertronian_Citizen']:
            role_ids = ROLE_IDS.get(role_name, [])
            if isinstance(role_ids, list):
                cybertronian_roles.extend(role_ids)
            else:
                cybertronian_roles.append(role_ids)
        
        member_role_ids = [role.id for role in member.roles]
        return any(role_id in member_role_ids for role_id in cybertronian_roles)

    def assign_factions(self, warriors: List[Union[str, discord.Member]], faction_count: int = 2) -> Dict[str, Dict[str, str]]:
        """Assign random factions to warriors for the game"""
        
        faction_names = [
            "Autobot", "Decepticon", "Maximal", "Predacon", "Neutral",
            "Seeker", "Wrecker", "Dinobot", "Guardian", "Titan",
            "Cybertronian Knight", "Technobot", "Monsterbot", "Targetmaster",
            "Headmaster", "Powermaster", "Micromaster", "Action Master",
            "Stunticon", "Combaticon", "Constructicon", "Terrorcon",
            "Protectobot", "Aerialbot", "Technobot", "Seacon",
            "Throttlebot", "Clones", "Delorean", "Omnibot",
            "Sparklings", "Scavengers", "Reflectors", "Junkions",
            "Bounty Hunter", "Gladiators", "Science Division", "Explorers",
            "Peacekeepers", "Rebel Alliance", "Black Ops", "Shadow Syndicate"
        ]
        
        factions = faction_names[:faction_count]
        assignments = {}
        
        for i, warrior in enumerate(warriors):
            warrior_name = warrior.display_name if isinstance(warrior, discord.Member) else str(warrior)
            faction = factions[i % len(factions)]
            
            self.faction_tracker[warrior_name] = faction
            assignments[warrior_name] = {"faction": faction}
        
        return assignments

    def _generate_cybertron_round(self, round_num: int, participants: List[discord.Member], previous_round: str = None) -> str:
        """Generate a pure Transformers-themed round using AI"""
        
        if not self.use_ai or not self.model or not self.client:
            logger.warning(f"AI not available: use_ai={self.use_ai}, model={self.model}, client={self.client}")
            return self._generate_fallback_cybertron_round(round_num, participants)

        alive_tributes = [p.display_name for p in participants]
        
        # Build faction data for the prompt
        faction_prompt_part = ""
        factions_dict = {}
        for p in participants:
            faction = self.faction_tracker.get(p.display_name, 'Neutral')
            if faction not in factions_dict:
                factions_dict[faction] = []
            factions_dict[faction].append(p.display_name)
        
        faction_prompt_part += "**CURRENT FACTIONS:**\n"
        for faction, members in factions_dict.items():
            faction_prompt_part += f"- **{faction}**: {', '.join(members)}\n"

        # Build simple history context
        history_context = ""
        if previous_round:
            history_context = f"\n**LAST ROUND'S NARRATIVE:**\n{previous_round}\n"

        prompt = f"""
        You are the **Oracle of Cybertron**, master storyteller for the **Cybertron Games**.
        Create a narrative for ROUND {round_num} involving the remaining sparks.
        
        **CURRENT IGNITED SPARKS:**
        {", ".join(alive_tributes)}
        
        {faction_prompt_part}
        
        {history_context}
        
        Your narrative must describe energon-fueled combat, alliance shifts, faction changes, and eliminations. Do not use human terms. Return ONLY the narrative text.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            response_text = response.choices[0].message.content.strip()
            
            if not response_text:
                raise ValueError("Empty response from AI")
            
            self._process_narrative(response_text, participants)
            
            logger.info(f"✅ AI generated Cybertron Round {round_num} successfully")
            return response_text
            
        except Exception as e:
            print(f"❌ AI generation failed: {e}, using enhanced cybertronian fallback")
            return self._generate_fallback_cybertron_round(round_num, participants)

    def _process_narrative(self, story_text: str, participants: List[discord.Member]):
        """Parse AI-generated text to update game state"""
        survivors = set(self.game_state['survivors'])
        
        faction_keywords = {
            "autobot": ["autobot", "joins the Autobots"],
            "decepticon": ["decepticon", "defects to the Decepticons"],
            "maximal": ["maximal", "joins the Maximals"],
            "predacon": ["predacon", "joins the Predacons"],
            "neutral": ["neutral", "becomes a Neutral"]
        }
        
        elimination_keywords = ["eliminated", "extinguished", "offline", "spark faded"]

        for warrior in participants:
            warrior_name = warrior.display_name
            
            if warrior_name in survivors:
                for keyword in elimination_keywords:
                    if re.search(f"({warrior_name}.*?{keyword})", story_text, re.IGNORECASE):
                        survivors.discard(warrior_name)
                        self.game_state['eliminations'].append(warrior_name)
                        print(f"💀 Elimination detected: {warrior_name} was eliminated.")
                        break

            for faction, keywords in faction_keywords.items():
                for keyword in keywords:
                    if re.search(f"({warrior_name}.*?{keyword})", story_text, re.IGNORECASE):
                        if self.faction_tracker.get(warrior_name) != faction:
                            self.faction_tracker[warrior_name] = faction
                            print(f"⚙️ Faction change detected: {warrior_name} is now a {faction}")
                        break

        self.game_state['survivors'] = list(survivors)

    def _generate_fallback_cybertron_round(self, round_num: int, participants: List[discord.Member]) -> str:
        """Generate a minimal fallback round when AI generation fails."""
        eliminations = []
        story_text = ""
        if len(participants) > 1:
            num_to_eliminate = random.randint(1, min(2, len(participants) - 1))
            random_eliminated = random.sample(participants, num_to_eliminate)
            
            for eliminated_warrior in random_eliminated:
                killer = random.choice([p for p in participants if p != eliminated_warrior])
                method = random.choice([
                    "was overloaded with a dark energon blast", 
                    "was caught in a plasma conduit explosion",
                    "had their spark core disrupted by a cunning enemy"
                ])
                
                story_text += f"**{eliminated_warrior.display_name}** {method} and was eliminated from the games by **{killer.display_name}**.\n"
                
                eliminations.append(eliminated_warrior)
            
            remaining_warriors = [p for p in participants if p not in eliminations]
            
            story_text += f"\n**Remaining warriors:** {', '.join([p.display_name for p in remaining_warriors])}"

        else:
            story_text = f"Only one warrior remains: {participants[0].display_name}. They are the champion of the Cybertron Games!"
        
        logger.info(f"✅ Fallback Cybertron Round {round_num} generated successfully")
        return story_text

    async def initialize_game(
        self,
        ctx: commands.Context,
        include_bots: bool = False,
        warriors: int = 0,
        factions: int = 5,
        specific_participants: str = None,
        cybertronian_only: bool = False
    ):
        """Handle the /cybertron_games command logic"""
        await ctx.defer()
        
        game_key = str(ctx.channel.id)
        
        if game_key in self.active_games:
            embed = discord.Embed(
                title="⚡ A GAME IS ALREADY IN PROGRESS ⚡",
                description="Please wait for the current Cybertron Games to finish.",
                color=0xff0000
            )
            await ctx.followup.send(embed=embed)
            return
        
        guild_members = ctx.guild.members
        participants = []
        
        if specific_participants:
            user_ids = []
            for part in specific_participants.split():
                try:
                    user_id = int(part.replace('<@!', '').replace('<@', '').replace('>', ''))
                    user_ids.append(user_id)
                except ValueError:
                    pass
            
            participants = [m for m in guild_members if m.id in user_ids]
            
        else:
            participants = [m for m in guild_members if (include_bots or not m.bot)]
        
        # Filter for cybertronian roles if requested
        if cybertronian_only:
            participants = [m for m in participants if self.has_cybertronian_role(m)]
            if len(participants) == 0:
                embed = discord.Embed(
                    title="⚡ NO CYBERTRONIAN WARRIORS FOUND ⚡",
                    description="No members with Cybertronian roles (Autobot, Decepticon, Maverick, or Cybertronian_Citizen) were found!",
                    color=0xff0000
                )
                await ctx.followup.send(embed=embed)
                return
            
        if 2 <= warriors <= 50 and warriors <= len(participants):
            participants = random.sample(participants, warriors)
        elif warriors > len(participants):
            await ctx.followup.send(f"Not enough warriors available. Only found {len(participants)}.")
            return
        
        if len(participants) < 2:
            embed = discord.Embed(
                title="⚡ INSUFFICIENT WARRIORS ⚡",
                description="Need at least 2 cybertronian warriors to start the games!",
                color=0xff0000
            )
            await ctx.followup.send(embed=embed)
            return

        assignments = self.assign_factions(participants, factions)
        
        self.game_state = {
            'participants': participants,
            'assignments': assignments,
            'survivors': [p.display_name for p in participants],
            'eliminations': [],
            'current_round': 0,
            'round_history': [],
            'start_time': datetime.now()
        }
        self.active_games[game_key] = self.game_state
        
        embed = discord.Embed(
            title="🌌 CYBERTRON GAMES INITIALIZED 🌌",
            description="The Arena of Cybertron awakens! Click **Start Games** to begin the first round.",
            color=0x00aaff
        )
        
        factions_text = "\n".join(
            f"**{faction_name}** - {len(faction_participants)} warriors" 
            for faction_name, faction_participants in self._get_factions(participants).items()
        )
        embed.add_field(name="🤖 FACTIONS", value=factions_text, inline=False)
        embed.add_field(name="Total Warriors", value=len(participants), inline=True)
        
        view = CybertronGamesView(self, game_key, game_state="setup")
        self.active_views[game_key] = view
        view.message = await ctx.followup.send(embed=embed, view=view)

    async def _advance_cybertron_round(self, game_key: str, interaction: discord.Interaction):
        """Advance to the next round of the Cybertron Games"""
        try:
            game_data = self.active_games[game_key]
            game_data['current_round'] += 1

            current_participants = [p for p in game_data['participants'] if p.display_name in game_data['survivors']]
            
            if len(current_participants) <= 1:
                await self._end_cybertron_games(game_key, interaction)
                return

            round_story = self._generate_cybertron_round(
                game_data['current_round'], 
                current_participants, 
                previous_round=game_data['round_history'][-1] if game_data['round_history'] else None
            )

            game_data['round_history'].append(round_story)
            
            remaining_warriors = [p for p in game_data['participants'] if p.display_name in game_data['survivors']]

            await interaction.channel.send(content=round_story, view=self.active_views.get(game_key))

            embed = discord.Embed(
                title="📊 CURRENT GAME STATUS",
                description=f"**Round:** {game_data['current_round']}\n**Survivors:** {len(remaining_warriors)}",
                color=0x00aaff
            )
            factions_text = "\n".join(
                f"**{faction_name}** - {len(faction_participants)} warriors" 
                for faction_name, faction_participants in self._get_factions(remaining_warriors).items()
            )
            embed.add_field(name="🤖 FACTIONS", value=factions_text, inline=False)
            
            view = self.active_views.get(game_key)
            if view:
                await interaction.channel.send(embed=embed, view=view)
            
            if len(game_data['survivors']) <= 1:
                await self._end_cybertron_games(game_key, interaction)

        except Exception as e:
            logger.error(f"Error advancing Cybertron round: {e}")
            try:
                await interaction.followup.send(f"❌ Failed to advance round: {str(e)}", ephemeral=True)
            except:
                pass

    def _get_factions(self, participants: List[discord.Member]) -> Dict[str, List[discord.Member]]:
        """Helper to get a dictionary of participants grouped by faction"""
        factions = {}
        for p in participants:
            faction = self.faction_tracker.get(p.display_name, "Neutral")
            if faction not in factions:
                factions[faction] = []
            factions[faction].append(p)
        return factions

    async def _end_cybertron_games(self, game_key: str, interaction: discord.Interaction):
        """End the Cybertron Games session"""
        game_data = self.active_games.pop(game_key, None)
        
        if not game_data:
            return

        survivors = game_data['survivors']
        eliminations = game_data['eliminations']
        
        if len(survivors) == 1:
            champion = survivors[0]
            embed = discord.Embed(
                title="👑 A CHAMPION IS CROWNED 👑",
                description=f"{champion} stands alone as the final champion of the Cybertron Games! All other sparks have been extinguished.",
                color=0xffd700
            )
        else:
            embed = discord.Embed(
                title="💀 ALL SPARKS EXTINGUISHED 💀",
                description="All warriors have been eliminated. The arena has claimed every spark.",
                color=0xff0000
            )
        
        embed.add_field(name="Total Rounds", value=game_data['current_round'], inline=False)
        embed.add_field(name="Warriors Eliminated", value=len(eliminations), inline=True)
        embed.add_field(name="Final Survivors", value=len(survivors), inline=True)
        
        view = self.active_views.get(game_key)
        if view:
            view._setup_buttons(end_game=True)
            await interaction.channel.send(embed=embed, view=view)
            
        if game_key in self.active_views:
            del self.active_views[game_key]
            
class CybertronGamesView(View):
    def __init__(self, bot_cog: Any, game_key: str, game_state: str = "setup"):
        super().__init__(timeout=None)
        self.bot_cog = bot_cog
        self.game_key = game_key
        self.game_state = game_state
        self.message = None
        self._setup_buttons()

    def _setup_buttons(self, end_game=False):
        self.clear_items()
        if not end_game:
            start_button = Button(label="Start Games", style=discord.ButtonStyle.green, custom_id="start_cybertron_games")
            next_round_button = Button(label="Next Round", style=discord.ButtonStyle.blurple, custom_id="next_cybertron_round")
            
            if self.game_state == "setup":
                start_button.callback = self.start_callback
                self.add_item(start_button)
            else:
                next_round_button.callback = self.next_round_callback
                self.add_item(next_round_button)
            
            end_button = Button(label="End Games", style=discord.ButtonStyle.red, custom_id="end_cybertron_games")
            end_button.callback = self.end_callback
            self.add_item(end_button)
        else:
            self.stop()
            
    async def start_callback(self, interaction: discord.Interaction):
        self.game_state = "active"
        self._setup_buttons()
        await interaction.response.edit_message(content="The games have begun!", view=self)
        await self.bot_cog._advance_cybertron_round(self.game_key, interaction)

    async def next_round_callback(self, interaction: discord.Interaction):
        await self.bot_cog._advance_cybertron_round(self.game_key, interaction)

    async def end_callback(self, interaction: discord.Interaction):
        await self.bot_cog._end_cybertron_games(self.game_key, interaction)

class CybertronGames(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.generator = CybertronGamesGenerator(GROQ_API_KEY)
        
    async def cog_load(self) -> None:
        pass  # Commands are automatically registered via decorators

    async def cog_unload(self) -> None:
        pass  # Commands are automatically unregistered
    
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get('custom_id')
            game_key = str(interaction.channel.id)

            if custom_id == 'start_cybertron_games':
                view = self.generator.active_views.get(game_key)
                if view and view.message.id == interaction.message.id:
                    await view.start_callback(interaction)

            elif custom_id == 'next_cybertron_round':
                view = self.generator.active_views.get(game_key)
                if view and view.message.id == interaction.message.id and game_key in self.generator.active_games:
                    await interaction.response.defer()
                    await self.generator._advance_cybertron_round(game_key, interaction)

            elif custom_id == 'end_cybertron_games':
                await interaction.response.defer()
                await self.generator._end_cybertron_games(game_key, interaction)

    @commands.hybrid_command(name='cybertron_games', description="Initiate the ultimate Transformers deathmatch - The Cybertron Games")
    @app_commands.describe(
        include_bots="Include cybertronian AI units in the games",
        warriors="Number of warriors to select (2-50, default: all)",
        factions="Number of factions (2-5, default: 5)",
        specific_participants="Specific Discord users to include (space-separated names or mentions)",
        cybertronian_only="Only include Cybertronian citizens (Autobot, Decepticon, Maverick, or Cybertronian_Citizen roles)"
    )
    async def cybertron_games(
        self,
        ctx: commands.Context,
        include_bots: bool = False,
        warriors: int = 0,
        factions: int = 5,
        specific_participants: str = None,
        cybertronian_only: bool = False
    ):
        await self.generator.initialize_game(ctx, include_bots, warriors, factions, specific_participants, cybertronian_only)


async def setup(bot):
    await bot.add_cog(CybertronGames(bot))
    print("✅ Cybertron Games cog loaded successfully")