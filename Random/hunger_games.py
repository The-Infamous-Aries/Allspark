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
from config import GROQ_API_KEY

logger = logging.getLogger("allspark.cybertron_games")

DISCORD_CHAR_LIMIT = 2000

# Helper function to break a long message into chunks
async def _send_long_message_in_chunks(channel: discord.TextChannel, content: str, view: View = None):
    """Sends a message, breaking it into chunks <= 2000 characters if necessary."""
    if not content:
        return
        
    chunks = [content[i:i + DISCORD_CHAR_LIMIT] for i in range(0, len(content), DISCORD_CHAR_LIMIT)]
    
    # Send all chunks
    for i, chunk in enumerate(chunks):
        # Only attach the view to the final chunk
        current_view = view if i == len(chunks) - 1 else None
        
        # Use a minimal separator for continuation, or nothing if the first part
        prefix = ""
        if i > 0:
            prefix = "*(... continuation ...)*\n"
            
        await channel.send(content=prefix + chunk, view=current_view)

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
        """Check if a member has any Cybertronian role using the server-specific role ID system"""
        if not member or not member.roles:
            return False
            
        from config import get_role_ids
        
        guild_id = member.guild.id if member.guild else None
        role_ids_config = get_role_ids(guild_id)
        
        cybertronian_roles = []
        for role_name in ['Autobot', 'Decepticon', 'Maverick', 'Cybertronian_Citizen']:
            role_ids = role_ids_config.get(role_name, [])
            if isinstance(role_ids, list):
                cybertronian_roles.extend(role_ids)
            elif role_ids:  # Only add non-None, non-zero values
                cybertronian_roles.append(role_ids)
        
        # Filter out any None or 0 values that might have slipped through
        cybertronian_roles = [role_id for role_id in cybertronian_roles if role_id and role_id != 0]
        
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
        
        # Get the list of allowed factions from the game state
        allowed_factions = []
        for faction_name in self.game_state.get('assignments', {}).values():
            if isinstance(faction_name, dict) and 'faction' in faction_name:
                faction = faction_name['faction'].lower()
                if faction not in [f.lower() for f in allowed_factions]:
                    allowed_factions.append(faction_name['faction'])
        
        # If no factions are found in assignments, use these defaults
        if not allowed_factions:
            allowed_factions = ["Autobot", "Decepticon", "Maximal", "Predacon", "Neutral"]
        
        # Create faction keywords dictionary only with allowed factions
        faction_keywords = {}
        for faction in allowed_factions:
            faction_lower = faction.lower()
            faction_keywords[faction_lower] = [faction_lower, f"joins the {faction}s", f"defects to the {faction}s"]
        
        # Always include Neutral as a fallback
        if "neutral" not in faction_keywords:
            faction_keywords["neutral"] = ["neutral", "becomes a Neutral"]
            
        # Enhanced elimination keywords for better detection
        elimination_keywords = [
            "eliminated", "extinguished", "offline", "spark faded", 
            "destroyed", "deactivated", "terminated", "crushed", "fallen",
            "no longer functions", "ceased to function"
        ]

        # Process eliminations first to ensure accurate survivor count
        for warrior in participants:
            warrior_name = warrior.display_name
            
            if warrior_name in survivors:
                for keyword in elimination_keywords:
                    if re.search(f"({warrior_name}.*?{keyword})", story_text, re.IGNORECASE):
                        survivors.discard(warrior_name)
                        if warrior_name not in self.game_state['eliminations']:
                            self.game_state['eliminations'].append(warrior_name)
                        print(f"💀 Elimination detected: {warrior_name} was eliminated.")
                        break

        # Then process faction changes only for survivors
        for warrior in participants:
            warrior_name = warrior.display_name
            
            if warrior_name in survivors:  # Only process faction changes for survivors
                for faction, keywords in faction_keywords.items():
                    for keyword in keywords:
                        if re.search(f"({warrior_name}.*?{keyword})", story_text, re.IGNORECASE):
                            if self.faction_tracker.get(warrior_name, "").lower() != faction:
                                # Get proper case from allowed_factions
                                proper_faction = next((f for f in allowed_factions if f.lower() == faction), faction.capitalize())
                                self.faction_tracker[warrior_name] = proper_faction
                                print(f"⚙️ Faction change detected: {warrior_name} is now a {proper_faction}")
                            break

        # Update survivors list in game state
        self.game_state['survivors'] = list(survivors)

    def _generate_fallback_cybertron_round(self, round_num: int, participants: List[discord.Member]) -> str:
        """Generate a Transformers-themed fallback round when AI generation fails."""
        eliminations = []
        story_text = f"🌌 **CYBERTRON GAMES - ROUND {round_num}** 🌌\n\n"
        
        if len(participants) > 1:
            num_to_eliminate = random.randint(1, min(2, len(participants) - 1))
            random_eliminated = random.sample(participants, num_to_eliminate)
            
            # Enhanced Transformers-themed elimination methods
            elimination_methods = [
                "was overloaded with a devastating dark energon blast",
                "was caught in a catastrophic plasma conduit explosion", 
                "had their spark core disrupted by a cunning enemy's ion cannon",
                "was crushed by falling debris from a collapsing energon refinery",
                "fell into a pit of molten cybermatter during fierce combat",
                "was short-circuited by an electromagnetic pulse weapon",
                "had their transformation cog damaged beyond repair",
                "was overwhelmed by a swarm of mechanical scraplets",
                "was frozen solid by a cryo-cannon blast",
                "had their energon supply drained by a parasitic techno-virus",
                "was vaporized by a concentrated photon beam",
                "fell victim to a booby-trapped energon cache",
                "was crushed in the gears of a massive mechanical trap",
                "had their neural circuits scrambled by a logic bomb",
                "was consumed by unstable synthetic energon"
            ]
            
            # Get current survivors from game state
            survivors = set(self.game_state.get('survivors', []))
            
            for eliminated_warrior in random_eliminated:
                killer = random.choice([p for p in participants if p != eliminated_warrior])
                method = random.choice(elimination_methods)
                
                story_text += f"⚡ **{eliminated_warrior.display_name}** {method} and was eliminated from the Cybertron Games by **{killer.display_name}**.\n\n"
                
                # Update game state directly
                warrior_name = eliminated_warrior.display_name
                if warrior_name in survivors:
                    survivors.discard(warrior_name)
                    if 'eliminations' in self.game_state and warrior_name not in self.game_state['eliminations']:
                        self.game_state['eliminations'].append(warrior_name)
                
                eliminations.append(eliminated_warrior)
            
            # Update game state survivors
            if 'survivors' in self.game_state:
                self.game_state['survivors'] = list(survivors)
            
            remaining_warriors = [p for p in participants if p not in eliminations]
            
            # Add faction changes randomly for some survivors (10% chance)
            if self.game_state.get('assignments') and len(remaining_warriors) > 0:
                # Get allowed factions from game state
                allowed_factions = []
                for faction_data in self.game_state.get('assignments', {}).values():
                    if isinstance(faction_data, dict) and 'faction' in faction_data:
                        faction = faction_data['faction']
                        if faction not in allowed_factions:
                            allowed_factions.append(faction)
                
                if allowed_factions:
                    for warrior in remaining_warriors:
                        # 10% chance of faction change
                        if random.random() < 0.1:
                            warrior_name = warrior.display_name
                            current_faction = self.faction_tracker.get(warrior_name)
                            available_factions = [f for f in allowed_factions if f != current_faction]
                            
                            if available_factions:
                                new_faction = random.choice(available_factions)
                                self.faction_tracker[warrior_name] = new_faction
                                story_text += f"⚙️ **{warrior_name}** has defected to the **{new_faction}** faction!\n\n"
            
            story_text += f"🤖 **Remaining Cybertronian Warriors:** {', '.join([p.display_name for p in remaining_warriors])}\n"
            story_text += f"💀 **Sparks Extinguished This Round:** {len(eliminations)}"

        else:
            story_text += f"👑 **VICTORY ACHIEVED!** 👑\n\n"
            story_text += f"Only one warrior's spark still burns bright: **{participants[0].display_name}**. "
            story_text += f"They stand triumphant as the ultimate champion of the Cybertron Games, their energon reserves intact and their will unbroken!"
        
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
        game_key = str(ctx.channel.id)
        
        if game_key in self.active_games:
            embed = discord.Embed(
                title="⚡ A GAME IS ALREADY IN PROGRESS ⚡",
                description="Please wait for the current Cybertron Games to finish.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
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
                await ctx.send(embed=embed)
                return
            
        if 2 <= warriors <= 50 and warriors <= len(participants):
            participants = random.sample(participants, warriors)
        elif warriors > len(participants):
            await ctx.send(f"Not enough warriors available. Only found {len(participants)}.")
            return
        
        if len(participants) < 2:
            embed = discord.Embed(
                title="⚡ INSUFFICIENT WARRIORS ⚡",
                description="Need at least 2 cybertronian warriors to start the games!",
                color=0xff0000
            )
            await ctx.send(embed=embed)
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
            title="⚡ THE CYBERTRON GAMES HAVE BEEN INITIATED ⚡",
            description="*The ancient Arena of Cybertron stirs to life, its energon-powered systems humming with anticipation. Warriors from across the galaxy prepare for the ultimate test of survival...*\n\n🔥 **Click START GAMES to begin the first round of combat!** 🔥",
            color=0x00aaff
        )
        
        factions_text = "\n".join(
            f"⚔️ **{faction_name}** - {len(faction_participants)} warriors" 
            for faction_name, faction_participants in self._get_factions(participants).items()
        )
        embed.add_field(name="🤖 CYBERTRONIAN FACTIONS", value=factions_text, inline=False)
        embed.add_field(name="⚡ Total Warriors", value=f"**{len(participants)}** brave souls", inline=True)
        embed.add_field(name="🌌 Arena Status", value="**ENERGIZED & READY**", inline=True)
        embed.set_footer(text="May the AllSpark guide the worthy to victory...")
        
        view = CybertronGamesView(self, game_key, game_state="setup")
        self.active_views[game_key] = view
        view.message = await ctx.send(embed=embed, view=view)

    async def _advance_cybertron_round(self, game_key: str, interaction: discord.Interaction = None, channel: discord.TextChannel = None):
        """Advance to the next round of the Cybertron Games"""
        try:
            # Use channel from interaction if available, otherwise use provided channel
            target_channel = interaction.channel if interaction else channel
            
            game_data = self.active_games[game_key]
            game_data['current_round'] += 1

            # Get current participants based on survivors list
            current_participants = [p for p in game_data['participants'] if p.display_name in game_data['survivors']]
            
            if len(current_participants) <= 1:
                await self._end_cybertron_games(game_key, interaction, channel)
                return

            # Store previous survivors count to detect new eliminations
            previous_survivors_count = len(game_data['survivors'])
            previous_eliminations_count = len(game_data.get('eliminations', []))

            round_story = self._generate_cybertron_round(
                game_data['current_round'], 
                current_participants, 
                previous_round=game_data['round_history'][-1] if game_data['round_history'] else None
            )

            game_data['round_history'].append(round_story)
            
            # Get updated list of remaining warriors after the round
            remaining_warriors = [p for p in game_data['participants'] if p.display_name in game_data['survivors']]
            
            # Calculate new eliminations this round
            new_eliminations_count = previous_survivors_count - len(remaining_warriors)
            total_eliminations = len(game_data.get('eliminations', []))

            # --- CHUNKED MESSAGE LOGIC APPLIED HERE ---
            view = self.active_views.get(game_key)
            await _send_long_message_in_chunks(target_channel, round_story, view)
            # --- END CHUNKED MESSAGE LOGIC ---

            # Create a more detailed status embed
            embed = discord.Embed(
                title="⚡ CYBERTRON ARENA STATUS ⚡",
                description=f"🌌 **Round {game_data['current_round']} Complete**\n💀 **{len(remaining_warriors)} Warriors Remain**\n\n*The arena's energon fields pulse with the echoes of battle...*",
                color=0x00aaff
            )
            
            # Add faction information with accurate survivor counts
            factions_text = "\n".join(
                f"⚔️ **{faction_name}** - {len(faction_participants)} survivors" 
                for faction_name, faction_participants in self._get_factions(remaining_warriors).items()
            )
            if factions_text:
                embed.add_field(name="🤖 SURVIVING FACTIONS", value=factions_text, inline=False)
            else:
                embed.add_field(name="🤖 SURVIVING FACTIONS", value="*No factions remain*", inline=False)
            
            # Add elimination information
            if new_eliminations_count > 0:
                # Get the names of warriors eliminated this round
                new_eliminations = game_data.get('eliminations', [])[previous_eliminations_count:]
                if new_eliminations:
                    embed.add_field(
                        name=f"💀 SPARKS EXTINGUISHED THIS ROUND ({new_eliminations_count})",
                        value=", ".join([f"**{name}**" for name in new_eliminations]),
                        inline=False
                    )
            
            # Add total eliminations count
            embed.add_field(
                name="⚰️ TOTAL FALLEN",
                value=f"**{total_eliminations}** warriors have fallen",
                inline=True
            )
            
            embed.set_footer(text="The AllSpark watches... who will prove worthy?")
            
            if view:
                await target_channel.send(embed=embed, view=view)
            
            if len(game_data['survivors']) <= 1:
                await self._end_cybertron_games(game_key, interaction, channel)

        except Exception as e:
            logger.error(f"Error advancing Cybertron round: {e}")
            # Don't try to respond to interaction since it may already be acknowledged
            try:
                await target_channel.send(f"❌ Failed to advance round: {str(e)}")
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

    async def _end_cybertron_games(self, game_key: str, interaction: discord.Interaction = None, channel: discord.TextChannel = None):
        """End the Cybertron Games session"""
        # Use channel from interaction if available, otherwise use provided channel
        target_channel = interaction.channel if interaction else channel
        
        game_data = self.active_games.pop(game_key, None)
        
        if not game_data:
            return

        survivors = game_data['survivors']
        eliminations = game_data['eliminations']
        assignments = game_data['assignments']
        
        # Group survivors by faction
        surviving_factions = {}
        for warrior in survivors:
            faction = assignments.get(warrior, "Unknown")
            if faction not in surviving_factions:
                surviving_factions[faction] = []
            surviving_factions[faction].append(warrior)
        
        if len(survivors) == 1:
            champion = survivors[0]
            champion_faction = assignments.get(champion, "Unknown")
            embed = discord.Embed(
                title="🏆 THE ALLSPARK HAS CHOSEN ITS CHAMPION! 🏆",
                description=f"**{champion}** of the **{champion_faction}** emerges victorious from the Arena of Cybertron!\n\n*The ancient energon crystals pulse with approval as the last warrior standing claims the Matrix of Leadership. All other sparks have returned to the AllSpark, their sacrifice honored in the halls of Cybertron.*\n\n⚡ **TILL ALL ARE ONE!** ⚡",
                color=0xffd700
            )
            embed.set_footer(text="The champion's name shall be etched in energon for all eternity...")
        elif len(survivors) > 1:
            # Multiple survivors
            embed = discord.Embed(
                title="🏆 THE ALLSPARK HAS CHOSEN ITS CHAMPIONS! 🏆",
                description=f"**{len(survivors)}** warriors have proven their worth in the Arena of Cybertron!\n\n*The ancient energon crystals pulse with approval as the remaining warriors share the Matrix of Leadership. The fallen have returned to the AllSpark, their sacrifice honored in the halls of Cybertron.*\n\n⚡ **TILL ALL ARE ONE!** ⚡",
                color=0xffd700
            )
            embed.set_footer(text="Their names shall be etched in energon for all eternity...")
        else:
            embed = discord.Embed(
                title="💀 THE ARENA CLAIMS ALL SPARKS 💀",
                description="*The Arena of Cybertron falls silent... No warrior proved worthy of the AllSpark's blessing. All sparks have been extinguished, their energon absorbed into the ancient battleground.*\n\n🌌 **The Matrix of Leadership remains unclaimed...** 🌌",
                color=0xff0000
            )
            embed.set_footer(text="Perhaps the next generation will prove more worthy...")
        
        embed.add_field(name="⚡ Total Rounds of Combat", value=f"**{game_data['current_round']}** epic battles", inline=False)
        embed.add_field(name="💀 Warriors Fallen", value=f"**{len(eliminations)}** sparks extinguished", inline=True)
        embed.add_field(name="🏆 Final Champions", value=f"**{len(survivors)}** victorious", inline=True)
        
        # Add detailed elimination information
        if eliminations:
            elimination_text = "\n".join([f"• **{warrior}** ({assignments.get(warrior, 'Unknown')})" for warrior in eliminations[-5:]])
            if len(eliminations) > 5:
                elimination_text += f"\n*...and {len(eliminations) - 5} more warriors*"
            embed.add_field(name="💀 The Fallen", value=elimination_text, inline=False)
        
        # Add surviving factions information
        if surviving_factions:
            faction_text = "\n".join([f"• **{faction}**: {', '.join(warriors)}" for faction, warriors in surviving_factions.items()])
            embed.add_field(name="🛡️ Surviving Factions", value=faction_text, inline=False)
        
        view = self.active_views.get(game_key)
        if view:
            view._setup_buttons(end_game=True)
            await target_channel.send(embed=embed, view=view)
            
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
        # Edit the initial message to show the games have started and update buttons
        await interaction.response.edit_message(content="The games have begun! Processing Round 1...", view=self)
        # Pass None for interaction since it's already been acknowledged
        await self.bot_cog._advance_cybertron_round(self.game_key, None, interaction.channel)

    async def next_round_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.bot_cog._advance_cybertron_round(self.game_key, None, interaction.channel)

    async def end_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.bot_cog._end_cybertron_games(self.game_key, None, interaction.channel)

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
                if view and view.message and view.message.id == interaction.message.id:
                    # The start_callback already handles acknowledgment and round advancement
                    await view.start_callback(interaction)

            elif custom_id == 'next_cybertron_round':
                view = self.generator.active_views.get(game_key)
                if view and view.message and view.message.id == interaction.message.id and game_key in self.generator.active_games:
                    # Defer acknowledgement handled in next_round_callback
                    await view.next_round_callback(interaction)

            elif custom_id == 'end_cybertron_games':
                # Defer acknowledgement handled in end_callback
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
        # Acknowledge the command immediately
        await ctx.defer()
        await self.generator.initialize_game(ctx, include_bots, warriors, factions, specific_participants, cybertronian_only)


async def setup(bot):
    await bot.add_cog(CybertronGames(bot))
    print("✅ Cybertron Games cog loaded successfully")