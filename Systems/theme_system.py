import discord
from discord import app_commands
from discord.ext import commands
from discord import ui
import random
import asyncio
import json
import time
import os
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from config import RESULTS_CHANNEL_ID
import logging
import sys

# Import external dependencies
try:
    from config import ROLE_IDS
except ImportError:
    ROLE_IDS = {}

try:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), 'Json'))
    from cyberchronicles import get_rpg_system, add_energon_to_character, create_character_from_spark
except ImportError:
    def create_character_from_spark(user_id: str, name: str, faction: str, class_choice: str) -> None:
        pass

# Import user data manager
sys.path.append(os.path.dirname(__file__))
try:
    from user_data_manager import UserDataManager
except ImportError:
    class UserDataManager:
        pass


# Constants
# GAME_STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "Json", "game_state.json")  # No longer used
logger = logging.getLogger("allspark.theme_system")

class TransformerClass(Enum):
    """Enumeration of available Transformer classes."""
    COMMANDER = "commander"
    SCOUT = "scout"
    SCIENTIST = "scientist"
    ENGINEER = "engineer"
    MEDIC = "medic"
    WARRIOR = "warrior"
    SEEKER = "seeker"
    MARINER = "mariner"


class Faction(Enum):
    """Enumeration of available factions."""
    AUTOBOT = "autobot"
    DECEPTICON = "decepticon"


@dataclass
class TransformerData:
    """Data structure for storing transformer information."""
    name: str
    faction: str
    class_type: str


@dataclass
class CombinerTeam:
    """Data structure for storing combiner team information."""
    name: str
    members: List[str]
    timestamp: float


class ThemeConfig:
    """Configuration class containing all theme-related constants."""
    
    # Name generation data
    NAME_DATA = {
        "autobot": {
            "commander": {
                "prefixes": ["Aegis", "Apex", "Nova", "Valiant", "Praxis", "Vector", "Titan", "Magnus", "Ultra", "Fortress", "Sentinel", "Guardian", "Vanguard", "Citadel", "Bastion", "Rampart", "Bulwark", "Paladin", "Centurion", "Legion", "Sovereign", "Imperius", "Maximus", "Dominus", "Supremus", "Grandus", "Majestus", "Glorius", "Victorious", "Triumphant"],
                "suffixes": ["prime", "bolt", "fire", "tron", "force", "major", "max", "commander", "chief", "leader", "guard", "shield", "defender", "protector", "champion", "valor", "honor", "glory", "victory", "triumph", "might", "power", "strength", "courage", "noble", "royal", "supreme", "grand", "great", "mighty"]
            },
            "scout": {
                "prefixes": ["Quick", "Swift", "Aero", "Light", "Ghost", "Brave", "Stray", "Flash", "Dash", "Zoom", "Blur", "Streak", "Rapid", "Velocity", "Turbo", "Nitro", "Boost", "Rush", "Sprint", "Bolt", "Arrow", "Dart", "Comet", "Meteor", "Rocket", "Jet", "Wind", "Breeze", "Gale", "Storm"],
                "suffixes": ["wing", "blaze", "dash", "runner", "shot", "flare", "wind", "speed", "rush", "flash", "streak", "bolt", "arrow", "dart", "scout", "ranger", "tracker", "hunter", "seeker", "finder", "swift", "quick", "fast", "rapid", "turbo", "boost", "zoom", "blur", "comet", "meteor"]
            },
            "scientist": {
                "prefixes": ["Chrono", "Data", "Intel", "Logic", "Cerebral", "Omni", "Synthe", "Quantum", "Nano", "Micro", "Macro", "Meta", "Proto", "Cyber", "Digital", "Binary", "Matrix", "Vector", "Algorithm", "Cipher", "Code", "Nexus", "Neural", "Cortex", "Synaptic", "Cognitive", "Analytical", "Theoretical", "Empirical", "Experimental"],
                "suffixes": ["wave", "flux", "core", "mind", "scope", "scan", "matrix", "data", "byte", "bit", "code", "link", "net", "web", "grid", "node", "hub", "port", "drive", "disk", "chip", "processor", "circuit", "board", "panel", "screen", "display", "monitor", "sensor", "probe"]
            },
            "engineer": {
                "prefixes": ["Gear", "Wrench", "Spark", "Forge", "Scrap", "Fixit", "Claw", "Tool", "Build", "Craft", "Make", "Weld", "Rivet", "Bolt", "Nut", "Screw", "Hammer", "Drill", "Saw", "Grind", "Polish", "Repair", "Mend", "Patch", "Tune", "Adjust", "Calibrate", "Modify", "Upgrade", "Enhance"],
                "suffixes": ["lock", "head", "smith", "nut", "works", "jaw", "gasket", "wrench", "tool", "gear", "cog", "wheel", "axle", "shaft", "bearing", "joint", "hinge", "lever", "pulley", "spring", "coil", "wire", "cable", "pipe", "tube", "valve", "pump", "motor", "engine", "drive"]
            },
            "medic": {
                "prefixes": ["Triage", "First", "Lifeline", "Red", "Doc", "Patch", "Heal", "Mend", "Cure", "Fix", "Repair", "Restore", "Revive", "Rescue", "Save", "Aid", "Help", "Care", "Tend", "Nurse", "Medic", "Surgeon", "Doctor", "Physician", "Therapist", "Specialist", "Expert", "Professional", "Emergency", "Critical"],
                "suffixes": ["aid", "beam", "charge", "patch", "heal", "bot", "care", "cure", "fix", "mend", "help", "save", "rescue", "restore", "revive", "repair", "tend", "nurse", "medic", "doc", "surgeon", "physician", "therapist", "specialist", "expert", "professional", "emergency", "critical", "vital", "life"]
            },
            "warrior": {
                "prefixes": ["Iron", "Ground", "Steel", "Brave", "Valiant", "Gutsy", "Grit", "Battle", "War", "Fight", "Combat", "Strike", "Attack", "Assault", "Charge", "Rush", "Blitz", "Storm", "Thunder", "Lightning", "Fury", "Rage", "Wrath", "Vengeance", "Justice", "Honor", "Glory", "Victory", "Triumph", "Conquest"],
                "suffixes": ["hide", "slam", "fist", "charge", "strike", "breaker", "maul", "bash", "smash", "crush", "pound", "hammer", "punch", "kick", "blow", "hit", "impact", "force", "power", "might", "strength", "muscle", "brawn", "bulk", "mass", "weight", "heavy", "solid", "tough", "hard"]
            },
            "seeker": {
                "prefixes": ["Jet", "Sky", "Air", "Sonic", "Cloud", "Swoop", "Fly", "Soar", "Glide", "Dive", "Climb", "Rise", "Ascend", "Descend", "Float", "Hover", "Drift", "Cruise", "Navigate", "Pilot", "Captain", "Commander", "Leader", "Chief", "Major", "Colonel", "General", "Admiral", "Marshal", "Ace"],
                "suffixes": ["swoop", "dive", "raid", "boom", "wing", "storm", "flight", "soar", "glide", "climb", "rise", "fall", "drop", "plunge", "spiral", "loop", "roll", "turn", "bank", "pitch", "yaw", "thrust", "lift", "drag", "speed", "velocity", "altitude", "height", "sky", "air"]
            },
            "mariner": {
                "prefixes": ["Tidal", "Hydro", "Sea", "Harbor", "Wave", "Ocean", "Deep", "Blue", "Aqua", "Marine", "Naval", "Fleet", "Ship", "Boat", "Vessel", "Craft", "Submarine", "Torpedo", "Depth", "Current", "Stream", "Flow", "Tide", "Surf", "Splash", "Spray", "Foam", "Bubble", "Ripple", "Whirlpool"],
                "suffixes": ["surge", "guard", "breach", "wake", "blade", "fin", "tail", "scale", "gill", "shell", "pearl", "coral", "reef", "anchor", "mast", "sail", "rudder", "helm", "deck", "hull", "bow", "stern", "port", "starboard", "depth", "fathom", "league", "knot", "current", "tide"]
            }
        },
        "decepticon": {
            "commander": {
                "prefixes": ["Over", "Mega", "Stars", "Cyclo", "Galva", "Shock", "Cyber", "Dark", "Shadow", "Doom", "Death", "Destroy", "Devastate", "Demolish", "Annihilate", "Obliterate", "Eradicate", "Eliminate", "Terminate", "Execute", "Assassinate", "Murder", "Kill", "Slay", "Butcher", "Massacre", "Slaughter", "Carnage", "Mayhem", "Chaos"],
                "suffixes": ["tron", "storm", "lord", "con", "blade", "wave", "bane", "doom", "death", "destroyer", "devastator", "demolisher", "annihilator", "obliterator", "eradicator", "eliminator", "terminator", "executor", "assassin", "murderer", "killer", "slayer", "butcher", "master", "ruler", "tyrant", "dictator", "emperor", "overlord", "supreme"]
            },
            "scout": {
                "prefixes": ["Recon", "Acid", "Phantom", "Rumble", "Laser", "Sound", "Creep", "Sneak", "Stealth", "Silent", "Quiet", "Whisper", "Murmur", "Hush", "Mute", "Spy", "Agent", "Operative", "Infiltrator", "Saboteur", "Assassin", "Hunter", "Stalker", "Tracker", "Seeker", "Finder", "Locator", "Scanner", "Probe", "Sensor"],
                "suffixes": ["probe", "glide", "storm", "blast", "stalker", "strike", "shock", "spy", "agent", "operative", "infiltrator", "saboteur", "assassin", "hunter", "tracker", "seeker", "finder", "locator", "scanner", "sensor", "detector", "monitor", "observer", "watcher", "guard", "sentinel", "sentry", "patrol", "scout", "recon"]
            },
            "scientist": {
                "prefixes": ["Shock", "Void", "Quantum", "Cyber", "Data", "Null", "Zero", "Negative", "Anti", "Counter", "Reverse", "Inverse", "Opposite", "Contrary", "Paradox", "Anomaly", "Aberration", "Deviation", "Mutation", "Corruption", "Contamination", "Infection", "Virus", "Plague", "Disease", "Sickness", "Illness", "Malady", "Disorder", "Chaos"],
                "suffixes": ["blight", "null", "core", "flux", "scan", "mind", "pulse", "void", "zero", "negative", "anti", "counter", "reverse", "inverse", "opposite", "contrary", "paradox", "anomaly", "aberration", "deviation", "mutation", "corruption", "contamination", "infection", "virus", "plague", "disease", "sickness", "illness", "malady"]
            },
            "engineer": {
                "prefixes": ["Junk", "Grease", "Ravage", "Oil", "Rust", "Crank", "Scrap", "Waste", "Trash", "Garbage", "Refuse", "Debris", "Rubble", "Wreckage", "Ruin", "Decay", "Rot", "Corrosion", "Erosion", "Deterioration", "Degradation", "Decomposition", "Disintegration", "Destruction", "Demolition", "Devastation", "Annihilation", "Obliteration", "Eradication", "Elimination"],
                "suffixes": ["jaw", "gasket", "spit", "slick", "works", "bot", "breaker", "wrecker", "destroyer", "demolisher", "devastator", "annihilator", "obliterator", "eradicator", "eliminator", "terminator", "executor", "assassin", "murderer", "killer", "slayer", "butcher", "ripper", "tearer", "shredder", "grinder", "crusher", "smasher", "basher", "pounder"]
            },
            "medic": {
                "prefixes": ["Knock", "Flat", "Scalpel", "Hook", "Cut", "Slice", "Dice", "Chop", "Hack", "Slash", "Stab", "Pierce", "Puncture", "Perforate", "Penetrate", "Impale", "Skewer", "Spear", "Lance", "Needle", "Pin", "Tack", "Nail", "Spike", "Thorn", "Barb", "Point", "Tip", "Edge", "Blade"],
                "suffixes": ["out", "line", "bot", "claw", "saw", "blade", "knife", "scalpel", "razor", "edge", "point", "tip", "spike", "thorn", "barb", "needle", "pin", "tack", "nail", "hook", "claw", "talon", "fang", "tooth", "bite", "snap", "crack", "break", "fracture", "split"]
            },
            "warrior": {
                "prefixes": ["Star", "Rage", "Ground", "Terror", "Grim", "Chaos", "Fury", "Wrath", "Vengeance", "Revenge", "Retribution", "Retaliation", "Payback", "Justice", "Punishment", "Penalty", "Consequence", "Result", "Outcome", "Effect", "Impact", "Force", "Power", "Might", "Strength", "Muscle", "Brawn", "Bulk", "Mass", "Weight"],
                "suffixes": ["scream", "shatter", "maul", "shock", "claw", "blast", "gore", "blood", "carnage", "mayhem", "chaos", "destruction", "devastation", "annihilation", "obliteration", "eradication", "elimination", "termination", "execution", "assassination", "murder", "kill", "slay", "butcher", "massacre", "slaughter", "rampage", "riot", "revolt", "rebellion"]
            },
            "seeker": {
                "prefixes": ["Thund", "Sky", "Dirge", "Ram", "Blitz", "Storm", "Lightning", "Thunder", "Bolt", "Flash", "Spark", "Flame", "Fire", "Burn", "Scorch", "Sear", "Char", "Ash", "Ember", "Cinder", "Smoke", "Smolder", "Blaze", "Inferno", "Conflagration", "Holocaust", "Apocalypse", "Armageddon", "Doomsday", "Judgment"],
                "suffixes": ["cracker", "warp", "jet", "storm", "blade", "wing", "flight", "soar", "dive", "plunge", "drop", "fall", "crash", "smash", "bash", "pound", "hammer", "strike", "hit", "impact", "force", "power", "might", "strength", "speed", "velocity", "acceleration", "momentum", "thrust", "propulsion"]
            },
            "mariner": {
                "prefixes": ["Maelstrom", "Kraken", "Dread", "Abyss", "Black", "Dark", "Deep", "Void", "Empty", "Hollow", "Vacant", "Barren", "Desolate", "Forsaken", "Abandoned", "Lost", "Forgotten", "Ignored", "Neglected", "Rejected", "Refused", "Denied", "Forbidden", "Banned", "Prohibited", "Outlawed", "Illegal", "Criminal", "Guilty", "Condemned"],
                "suffixes": ["jaw", "fin", "slicer", "tide", "storm", "wave", "current", "flow", "stream", "river", "flood", "deluge", "torrent", "cascade", "waterfall", "rapids", "whirlpool", "vortex", "maelstrom", "typhoon", "hurricane", "cyclone", "tornado", "twister", "spiral", "swirl", "eddy", "turbulence", "chaos", "mayhem"]
            }
        }
    }

    # Combiner name generation data
    COMBINER_PREFIXES = [
        "Ultra", "Super", "Mega", "Giga", "Tera", "Omega", "Alpha", "Beta", "Gamma", "Delta",
        "Epsilon", "Zeta", "Eta", "Theta", "Iota", "Kappa", "Lambda", "Mu", "Nu", "Xi",
        "Omicron", "Pi", "Rho", "Sigma", "Tau", "Upsilon", "Phi", "Chi", "Psi", "Omega",
        "Prime", "Matrix", "Vector", "Nexus", "Apex", "Vertex", "Summit", "Peak", "Zenith",
        "Pinnacle", "Acme", "Crown", "Crest", "Ridge", "Edge", "Blade", "Point", "Tip",
        "Spike", "Thorn", "Barb", "Hook", "Claw", "Talon", "Fang", "Tooth", "Bite"
    ]
    
    COMBINER_SUFFIXES = [
        "tron", "con", "bot", "droid", "mech", "borg", "prime", "max", "ultra", "super",
        "mega", "giga", "tera", "omega", "alpha", "beta", "gamma", "delta", "epsilon",
        "zeta", "eta", "theta", "iota", "kappa", "lambda", "mu", "nu", "xi", "omicron",
        "pi", "rho", "sigma", "tau", "upsilon", "phi", "chi", "psi", "matrix", "vector",
        "nexus", "apex", "vertex", "summit", "peak", "zenith", "pinnacle", "acme", "crown",
        "crest", "ridge", "edge", "blade", "point", "tip", "spike", "thorn", "barb"
    ]


class DataManager:
    """Legacy DataManager - now uses UserDataManager for all operations."""
    
    def __init__(self, bot_instance: commands.Bot):
        self.bot = bot_instance
        self.game_state_file = None  # No longer used
        self._game_state_loaded = False
        self._ensure_data_structures()
        
        # Always use UserDataManager
        self.user_data_manager = UserDataManager()

    def _ensure_data_structures(self) -> None:
        """Ensure all required data structures are initialized."""
        if not hasattr(self.bot, 'transformer_names'):
            self.bot.transformer_names = {}
        if not hasattr(self.bot, 'combiner_teams'):
            self.bot.combiner_teams = {}
        if not hasattr(self.bot, 'combiner_names'):
            self.bot.combiner_names = {}

    def _ensure_state_loaded(self) -> None:
        """No-op for backward compatibility."""
        self._game_state_loaded = True

    def load_game_state(self) -> Dict[str, Any]:
        """Legacy method - returns empty dict."""
        return {}

    def save_game_state(self) -> None:
        """Legacy method - no longer saves to game_state.json."""
        pass

    def is_user_in_any_combiner(self, user_id: str) -> Tuple[bool, Optional[str]]:
        """Check if a user is already part of any combiner team."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            team_info = loop.run_until_complete(
                self.user_data_manager.get_user_combiner_team(str(user_id), None)
            )
            if team_info:
                return True, team_info.get("team_id")
        except Exception:
            pass
        return False, None

    def remove_user_from_all_combiners(self, user_id: str, username: str = None) -> None:
        """Remove a user from all combiner teams."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(
                self.user_data_manager.remove_user_from_combiner_team(str(user_id), username or "Unknown", None)
            )
        except Exception as e:
            print(f"Error removing user from combiner teams: {e}")


class NameGenerator:
    """Handles transformer name generation."""
    
    @staticmethod
    def generate_transformer_name(faction: str, class_type: str) -> str:
        """Generate a unique transformer name based on faction and class."""
        try:
            prefixes = ThemeConfig.NAME_DATA[faction][class_type]["prefixes"]
            suffixes = ThemeConfig.NAME_DATA[faction][class_type]["suffixes"]
            name = random.choice(prefixes) + random.choice(suffixes)
            
            # Ensure name length is within Discord limits
            return name[:32]
        except KeyError:
            return f"Unknown-{random.randint(1000, 9999)}"

    @staticmethod
    def generate_combiner_name(team_members: List[str]) -> str:
        """Generate a unique combiner name based on team composition."""
        prefix = random.choice(ThemeConfig.COMBINER_PREFIXES)
        suffix = random.choice(ThemeConfig.COMBINER_SUFFIXES)
        return f"{prefix}{suffix}"


class RoleChecker:
    """Utility class for checking Discord roles."""
    
    @staticmethod
    def has_cybertronian_role(member: discord.Member) -> bool:
        """Check if a member has any Cybertronian role."""
        cybertronian_roles = [ROLE_IDS.get(role) for role in ['Autobot', 'Decepticon', 'Maverick', 'Cybertronian_Citizen']]
        return any(role.id in cybertronian_roles for role in member.roles)


class CombinerManager:
    """Legacy CombinerManager - now uses UserDataManager for all operations."""
    
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager

    def initialize_team(self, message_id: str) -> None:
        """Legacy method - no longer needed as teams are managed through UserDataManager."""
        pass

    def get_team_status(self, message_id: str) -> Dict[str, any]:
        """Legacy method - returns empty dict as teams are now managed through UserDataManager."""
        return {}


class ThemeCommands(commands.Cog):
    """Discord bot commands for theme system."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data_manager = DataManager(bot)
        self.name_generator = NameGenerator()
        self.role_checker = RoleChecker()
        self.combiner_manager = CombinerManager(self.data_manager)

    @app_commands.command(name="spark", description="Become a Transformer! Pick your class and faction.")
    @app_commands.describe(
        class_choice="Choose your Transformer's class.",
        faction="Choose your faction, Autobot or Decepticon."
    )
    @app_commands.choices(
        class_choice=[
            app_commands.Choice(name="Scientist *Starting Stats ATT:4 DEF:2 DEX:2 CHA:0*", value="scientist"),
            app_commands.Choice(name="Warrior *Starting Stats ATT:4 DEF:1 DEX:2 CHA:1*", value="warrior"),
            app_commands.Choice(name="Engineer *Starting Stats ATT:2 DEF:4 DEX:2 CHA:0*", value="engineer"),
            app_commands.Choice(name="Mariner *Starting Stats ATT:1 DEF:4 DEX:0 CHA:2*", value="mariner"),
            app_commands.Choice(name="Scout *Starting Stats ATT:1 DEF:0 DEX:4 CHA:3*", value="scout"),   
            app_commands.Choice(name="Seeker *Starting Stats ATT:2 DEF:1 DEX:4 CHA:4*", value="seeker"),
            app_commands.Choice(name="Commander *Starting Stats ATT:2 DEF:1 DEX:1 CHA:4*", value="commander"),
            app_commands.Choice(name="Medic *Starting Stats ATT:0 DEF:1 DEX:3 CHA:4*", value="medic")
        ],
        faction=[
            app_commands.Choice(name="🔴 Autobot", value="autobot"),
            app_commands.Choice(name="🟣 Decepticon", value="decepticon")
        ]
    )
    async def spark(self, interaction: discord.Interaction, class_choice: str, faction: str):
        """Assigns a new Transformer identity to the user."""
        # Check for Cybertronian role
        if not self.role_checker.has_cybertronian_role(interaction.user):
            await interaction.response.send_message(
                "❌ Only Cybertronian Citizens can be assigned a Transformer identity! "
                "Please get a Cybertronian role first."
            )
            return
        
        # Generate transformer name
        new_name = self.name_generator.generate_transformer_name(faction, class_choice)
        
        # Save the transformer data using UserDataManager
        user_id = str(interaction.user.id)
        if self.data_manager.user_data_manager:
            # Use UserDataManager to save transformer data
            theme_data = await self.data_manager.user_data_manager.get_theme_system_data(user_id)
            theme_data["transformer"] = {
                "name": new_name,
                "faction": faction,
                "class": class_choice,
                "created_at": time.time()
            }
            await self.data_manager.user_data_manager.save_theme_system_data(user_id, theme_data)
        else:
            # Fallback to legacy system
            self.data_manager._ensure_state_loaded()
            self.data_manager.bot.transformer_names[user_id] = {
                "name": new_name,
                "faction": faction,
                "class": class_choice
            }
            self.data_manager.save_game_state()
        
        # Create character in RPG system
        create_character_from_spark(user_id, new_name, faction, class_choice)
        
        public_message = (
            f"**{interaction.user.mention}** has been mutated by the AllSpark! "
            f"Your Transformer identity is **{new_name}**, a {faction.capitalize()} {class_choice.capitalize()}! "
            f"Use `/me` to view your full profile."
        )
        await interaction.response.send_message(public_message)

    @commands.hybrid_command(name="combiner", description="Start forming a Combiner team!")
    async def combiner(self, ctx: commands.Context):
        """Start forming a combiner team."""
        embed = discord.Embed(
            title="🤖 Combiner Team Formation",
            description="React with the part you want to be! Each team needs:\n"
                       "🦿 2 Legs | 🦾 2 Arms | 🧠 1 Head | 🫀 1 Body\n\n"
                       "*Note: You can only be part of one combiner team at a time.*",
            color=0x00ff00
        )
        
        # Add empty fields for each part
        part_names = {"🦿": "Legs", "🦾": "Arms", "🧠": "Head", "🫀": "Body"}
        limits = {"🦿": 2, "🦾": 2, "🧠": 1, "🫀": 1}
        
        for emoji, name in part_names.items():
            embed.add_field(
                name=f"{emoji} {name} (0/{limits[emoji]})",
                value="*Empty*",
                inline=True
            )
        
        # Create the view with summon button
        view = CombinerView(None, ctx.guild)
        message = await ctx.send(embed=embed, view=view)
        
        # Update the view with the actual message ID
        view.message_id = str(message.id)
        
        # Initialize combiner data using UserDataManager
        message_id = str(message.id)
        if self.data_manager.user_data_manager:
            # Initialize combiner team in UserDataManager
            # Team data will be managed through individual user files
            pass  # Teams are managed through user assignments
        else:
            # Fallback to legacy system
            self.data_manager._ensure_state_loaded()
            self.combiner_manager.initialize_team(message_id)
        
        # Add reactions
        for emoji in ["🦿", "🦾", "🧠", "🫀"]:
            await message.add_reaction(emoji)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        """Handle reactions for combiner team formation."""
        if user.bot:
            return
        
        # Check if this is a combiner message
        if hasattr(reaction.message, 'embeds') and reaction.message.embeds:
            embed = reaction.message.embeds[0]
            if "Combiner Team Formation" in embed.title:
                await self._handle_combiner_reaction(reaction, user, True)

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction: discord.Reaction, user: discord.User):
        """Handle reaction removal for combiner teams."""
        if user.bot:
            return
        
        # Check if this is a combiner message
        if hasattr(reaction.message, 'embeds') and reaction.message.embeds:
            embed = reaction.message.embeds[0]
            if "Combiner Team Formation" in embed.title:
                await self._handle_combiner_reaction(reaction, user, False)

    async def _handle_combiner_reaction(self, reaction: discord.Reaction, user: discord.User, adding: bool):
        """Handle combiner team reactions using UserDataManager."""
        if not self.role_checker.has_cybertronian_role(user):
            return
        
        message_id = str(reaction.message.id)
        user_id = str(user.id)
        username = user.display_name
        
        # Ensure state is loaded before accessing data
        self.data_manager._ensure_state_loaded()
        
        # Check if user is already in any combiner team (including this one)
        in_combiner, existing_message_id = self.data_manager.is_user_in_any_combiner(user_id)
        
        if adding and in_combiner and existing_message_id != message_id:
            # User is trying to join a different combiner team
            try:
                await reaction.remove(user)
            except:
                pass
            return
        
        # Initialize combiner data if needed
        if message_id not in self.data_manager.bot.combiner_teams:
            self.combiner_manager.initialize_team(message_id)
        
        team_data = self.data_manager.bot.combiner_teams[message_id]
        emoji = str(reaction.emoji)
        
        # Define limits for each part
        limits = {"🦿": 2, "🦾": 2, "🧠": 1, "🫀": 1}
        
        if emoji in limits:
            if adding:
                # Remove user from all other positions in THIS team first
                for part in team_data:
                    if user_id in team_data[part]:
                        team_data[part].remove(user_id)
                
                # Add to new position if there's space
                if len(team_data[emoji]) < limits[emoji]:
                    team_data[emoji].append(user_id)
                    
                    # Update user data with new team assignment
                    if self.data_manager.user_data_manager:
                        try:
                            await self.data_manager.user_data_manager.add_user_to_combiner_team(
                                user_id, username, message_id, emoji, team_data
                            )
                        except Exception as e:
                            print(f"Error updating user data for {user_id}: {e}")
            else:
                # Remove user from this position
                if user_id in team_data[emoji]:
                    team_data[emoji].remove(user_id)
                    
                    # Update user data to remove team assignment
                    if self.data_manager.user_data_manager:
                        try:
                            await self.data_manager.user_data_manager.remove_user_from_combiner_team(
                                user_id, username, message_id
                            )
                        except Exception as e:
                            print(f"Error removing user data for {user_id}: {e}")
            
            # Save the updated data
            self.data_manager.save_game_state()
            
            # Update the embed
            await self._update_combiner_embed(reaction.message, message_id)

    async def _handle_combiner_reaction_legacy(self, reaction: discord.Reaction, user: discord.User, adding: bool):
        """Legacy combiner reaction handler for backward compatibility."""
        if not self.role_checker.has_cybertronian_role(user):
            return
        
        message_id = str(reaction.message.id)
        user_id = str(user.id)
        username = user.display_name
        
        # Ensure state is loaded before accessing data
        self.data_manager._ensure_state_loaded()
        
        # Check if user is already in any combiner team (including this one)
        in_combiner, existing_message_id = self.data_manager.is_user_in_any_combiner(user_id)
        
        if adding and in_combiner and existing_message_id != message_id:
            # User is trying to join a different combiner team
            try:
                await reaction.remove(user)
            except:
                pass
            return
        
        # Initialize combiner data if needed
        if message_id not in self.data_manager.bot.combiner_teams:
            self.combiner_manager.initialize_team(message_id)
        
        team_data = self.data_manager.bot.combiner_teams[message_id]
        emoji = str(reaction.emoji)
        
        # Define limits for each part
        limits = {"🦿": 2, "🦾": 2, "🧠": 1, "🫀": 1}
        
        if emoji in limits:
            if adding:
                # Remove user from all other positions in THIS team first
                for part in team_data:
                    if user_id in team_data[part]:
                        team_data[part].remove(user_id)
                
                # Add to new position if there's space
                if len(team_data[emoji]) < limits[emoji]:
                    team_data[emoji].append(user_id)
            else:
                # Remove user from this position
                if user_id in team_data[emoji]:
                    team_data[emoji].remove(user_id)
            
            # Save the updated data
            self.data_manager.save_game_state()
            
            # Update the embed
            await self._update_combiner_embed(reaction.message, message_id)

    async def _update_combiner_embed(self, message: discord.Message, message_id: str):
        """Update the combiner embed with current team composition."""
        self.data_manager._ensure_state_loaded()
        team_data = self.data_manager.bot.combiner_teams[message_id]
        
        embed = discord.Embed(
            title="🤖 Combiner Team Formation",
            description="React with the part you want to be! Each team needs:\n🦿 2 Legs | 🦾 2 Arms | 🧠 1 Head | 🫀 1 Body",
            color=0x00ff00
        )
        
        # Add fields for each part
        part_names = {"🦿": "Legs", "🦾": "Arms", "🧠": "Head", "🫀": "Body"}
        limits = {"🦿": 2, "🦾": 2, "🧠": 1, "🫀": 1}
        
        for emoji, name in part_names.items():
            members = team_data[emoji]
            if members:
                member_names = []
                for user_id in members:
                    try:
                        user = self.bot.get_user(int(user_id))
                        if user:
                            # Get their transformer name if available
                            transformer_data = self.data_manager.bot.transformer_names.get(user_id)
                            if isinstance(transformer_data, dict):
                                transformer_name = transformer_data.get("name", user.display_name)
                            else:
                                transformer_name = transformer_data or user.display_name
                            member_names.append(transformer_name)
                    except:
                        member_names.append(f"User {user_id}")
                
                value = "\n".join(member_names)
            else:
                value = "*Empty*"
            
            embed.add_field(
                name=f"{emoji} {name} ({len(members)}/{limits[emoji]})",
                value=value,
                inline=True
            )
        
        # Check if team is complete (6 members total)
        total_members = sum(len(team_data[part]) for part in team_data)
        if total_members == 6 and all(len(team_data[part]) == limits[part] for part in ["🦿", "🦾", "🧠", "🫀"]):
            # Generate combiner name
            all_members = []
            for part in team_data:
                all_members.extend(team_data[part])
            
            combiner_name = self.name_generator.generate_combiner_name(all_members)
            
            embed.color = 0x00ff00
            embed.add_field(
                name="✅ Team Status",
                value=f"**COMBINER TEAM COMPLETE!** 🎉\n**Combined Form: {combiner_name}**",
                inline=False
            )
            
            # Save the combiner name
            self.data_manager.bot.combiner_names[message_id] = {
                'name': combiner_name,
                'members': all_members,
                'timestamp': time.time()
            }
            self.data_manager.save_game_state()
            
        else:
            embed.color = 0xffaa00
            embed.add_field(
                name="⏳ Team Status",
                value=f"**{total_members}/6 members assigned**",
                inline=False
            )
        
        try:
            await message.edit(embed=embed)
        except:
            pass


class CombinerView(discord.ui.View):
    """Discord UI view for combiner team management."""
    
    def __init__(self, message_id: str, guild: discord.Guild, theme_cog: ThemeCommands):
        super().__init__(timeout=None)
        self.message_id = message_id
        self.guild = guild
        self.theme_cog = theme_cog

    @discord.ui.button(label="🔮 Summon", style=discord.ButtonStyle.secondary, emoji='🔮')
    async def summon_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        summon_view = SummonView(self.message_id, self.guild, self.theme_cog)
        embed = discord.Embed(
            title="🔮 Summon Cybertronian",
            description=f"Select a user to add to the combiner team\nPage 1/{summon_view.max_pages}",
            color=0x9932cc
        )
        
        current_users = summon_view.get_current_users()
        user_list = []
        for user in current_users:
            transformer_data = self.theme_cog.data_manager.bot.transformer_names.get(str(user.id))
            if isinstance(transformer_data, dict):
                display_name = transformer_data.get("name", user.display_name)
            else:
                display_name = transformer_data or user.display_name
            
            in_combiner, _ = self.theme_cog.data_manager.is_user_in_any_combiner(user.id)
            status = " (In Team)" if in_combiner else ""
            user_list.append(f"• {display_name}{status}")
        
        embed.add_field(
            name="Available Users",
            value="\n".join(user_list) if user_list else "No users found",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=summon_view, ephemeral=True)


class SummonView(discord.ui.View):
    """Discord UI view for summoning users to combiner teams."""
    
    def __init__(self, message_id: str, guild: discord.Guild, theme_cog: ThemeCommands):
        super().__init__(timeout=300)
        self.message_id = message_id
        self.guild = guild
        self.theme_cog = theme_cog
        self.current_page = 0
        self.users_per_page = 5
        self.cybertronian_users = []
        
        # Get all members with Cybertronian roles
        cybertronian_roles = [ROLE_IDS.get(role) for role in ['Autobot', 'Decepticon', 'Maverick', 'Cybertronian_Citizen']]
        for member in guild.members:
            if any(role.id in cybertronian_roles for role in member.roles):
                self.cybertronian_users.append(member)
        
        self.max_pages = max(1, (len(self.cybertronian_users) + self.users_per_page - 1) // self.users_per_page)
        self.update_buttons()

    def get_current_users(self) -> List[discord.Member]:
        """Get current page of users."""
        start = self.current_page * self.users_per_page
        end = start + self.users_per_page
        return self.cybertronian_users[start:end]

    def update_buttons(self) -> None:
        """Update the view buttons based on current state."""
        self.clear_items()
        
        # Add user selection buttons
        current_users = self.get_current_users()
        for i, user in enumerate(current_users):
            display_name = self._get_display_name(user)
            in_combiner, _ = self.theme_cog.data_manager.is_user_in_any_combiner(user.id)
            status = " (In Team)" if in_combiner else ""
            
            button = discord.ui.Button(
                label=f"{display_name}{status}",
                style=discord.ButtonStyle.secondary if in_combiner else discord.ButtonStyle.primary,
                custom_id=f"select_user_{user.id}",
                disabled=in_combiner
            )
            button.callback = self.create_user_callback(user)
            self.add_item(button)
        
        # Add pagination buttons
        if self.max_pages > 1:
            prev_button = discord.ui.Button(
                label="◀ Previous",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page == 0
            )
            prev_button.callback = self.previous_page
            self.add_item(prev_button)
            
            next_button = discord.ui.Button(
                label="Next ▶",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page >= self.max_pages - 1
            )
            next_button.callback = self.next_page
            self.add_item(next_button)
        
        # Add close button
        close_button = discord.ui.Button(
            label="Close",
            style=discord.ButtonStyle.danger
        )
        close_button.callback = self.close_summon
        self.add_item(close_button)

    def _get_display_name(self, user: discord.Member) -> str:
        """Get the display name for a user, including transformer name if available."""
        self.theme_cog.data_manager._ensure_state_loaded()
        transformer_data = self.theme_cog.data_manager.bot.transformer_names.get(str(user.id))
        if isinstance(transformer_data, dict):
            return transformer_data.get("name", user.display_name)
        else:
            return transformer_data or user.display_name

    def create_user_callback(self, user: discord.Member):
        """Create a callback for user selection."""
        async def user_callback(interaction: discord.Interaction):
            # Check if user is already in any combiner team
            in_combiner, existing_message_id = self.theme_cog.data_manager.is_user_in_any_combiner(user.id)
            if in_combiner:
                await interaction.response.send_message(
                    f"{user.display_name} is already part of another combiner team!",
                    ephemeral=True
                )
                return
            
            # Show role selection for this user
            role_view = RoleSelectionView(user, self.message_id, self)
            embed = discord.Embed(
                title="Select Role",
                description=f"Choose a role for {user.display_name}:",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed, view=role_view, ephemeral=True)
        return user_callback

    async def previous_page(self, interaction: discord.Interaction):
        """Go to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await self.update_embed(interaction)

    async def next_page(self, interaction: discord.Interaction):
        """Go to next page."""
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            self.update_buttons()
            await self.update_embed(interaction)

    async def close_summon(self, interaction: discord.Interaction):
        """Close the summon interface."""
        await interaction.response.edit_message(content="Summon interface closed.", embed=None, view=None)

    async def update_embed(self, interaction: discord.Interaction):
        """Update the embed with current page data."""
        embed = discord.Embed(
            title="🔮 Summon Cybertronian",
            description=f"Select a user to add to the combiner team\nPage {self.current_page + 1}/{self.max_pages}",
            color=0x9932cc
        )
        
        current_users = self.get_current_users()
        user_list = []
        for user in current_users:
            display_name = self._get_display_name(user)
            in_combiner, _ = self.theme_cog.data_manager.is_user_in_any_combiner(user.id)
            status = " (In Team)" if in_combiner else ""
            user_list.append(f"• {display_name}{status}")
        
        embed.add_field(
            name="Available Users",
            value="\n".join(user_list) if user_list else "No users found",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=self)


class RoleSelectionView(discord.ui.View):
    """Discord UI view for role selection in combiner teams."""
    
    def __init__(self, user: discord.Member, message_id: str, parent_view: SummonView):
        super().__init__(timeout=60)
        self.user = user
        self.message_id = message_id
        self.parent_view = parent_view

    @discord.ui.button(label="🧠", style=discord.ButtonStyle.primary)
    async def head_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "🧠")

    @discord.ui.button(label="🫀", style=discord.ButtonStyle.primary)
    async def body_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "🫀")

    @discord.ui.button(label="🦾", style=discord.ButtonStyle.primary)
    async def arms_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "🦾")

    @discord.ui.button(label="🦿", style=discord.ButtonStyle.primary)
    async def legs_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "🦿")

    async def assign_role(self, interaction: discord.Interaction, emoji: str):
        """Assign a user to a specific role in the combiner team."""
        user_id = str(self.user.id)
        theme_cog = self.parent_view.theme_cog
        
        # Initialize combiner data if needed
        theme_cog.data_manager._ensure_state_loaded()
        if self.message_id not in theme_cog.data_manager.bot.combiner_teams:
            theme_cog.combiner_manager.initialize_team(self.message_id)
        
        team_data = theme_cog.data_manager.bot.combiner_teams[self.message_id]
        limits = {"🦿": 2, "🦾": 2, "🧠": 1, "🫀": 1}
        
        # Check total team size
        total_members = sum(len(team_data[part]) for part in team_data)
        if total_members >= 6:
            await interaction.response.send_message(
                "❌ The combiner team is already complete (6/6 members)!",
                ephemeral=True
            )
            return
        
        # Check if position is full
        if len(team_data[emoji]) >= limits[emoji]:
            part_names = {"🦿": "Legs", "🦾": "Arms", "🧠": "Head", "🫀": "Body"}
            await interaction.response.send_message(
                f"The {part_names[emoji]} position is already full!",
                ephemeral=True
            )
            return
        
        # Check if user is already in any combiner team
        in_combiner, existing_message_id = theme_cog.data_manager.is_user_in_any_combiner(user_id)
        if in_combiner:
            await interaction.response.send_message(
                f"{self.user.display_name} is already part of another combiner team!",
                ephemeral=True
            )
            return
        
        # Add user to the position
        team_data[emoji].append(user_id)
        theme_cog.data_manager.save_game_state()
        
        # Update user data with combiner team info
        if hasattr(theme_cog.data_manager, 'user_data_manager') and theme_cog.data_manager.user_data_manager:
            try:
                username = str(self.user)
                user_link = f"https://discord.com/users/{user_id}"
                part_name = {"🦿": "Legs", "🦾": "Arms", "🧠": "Head", "🫀": "Body"}[emoji]
                
                # Add user to combiner team in user data
                await theme_cog.data_manager.user_data_manager.add_user_to_combiner_team(
                    user_id, self.message_id, username, user_link, part_name
                )
                
                # Update all team members' data to link the complete team
                all_members = []
                for part, members in team_data.items():
                    part_name_for_update = {"🦿": "Legs", "🦾": "Arms", "🧠": "Head", "🫀": "Body"}[part]
                    for member_id in members:
                        member = interaction.guild.get_member(int(member_id))
                        if member:
                            all_members.append({
                                'user_id': member_id,
                                'username': str(member),
                                'link': f"https://discord.com/users/{member_id}",
                                'part': part_name_for_update
                            })
                
                # Update all members with complete team info
                for member_info in all_members:
                    await theme_cog.data_manager.user_data_manager._update_combiner_team_members(
                        member_info['user_id'], self.message_id, all_members
                    )
                    
            except Exception as e:
                print(f"Error updating user data for combiner team: {e}")
        
        # Update the main combiner message
        try:
            channel = interaction.guild.get_channel(interaction.channel.id)
            message = await channel.fetch_message(int(self.message_id))
            await theme_cog._update_combiner_embed(message, self.message_id)
        except:
            pass
        
        part_names = {"🦿": "Legs", "🦾": "Arms", "🧠": "Head", "🫀": "Body"}
        await interaction.response.send_message(
            f"✅ {self.user.display_name} has been assigned to {part_names[emoji]}!",
            ephemeral=True
        )
        
        # Check if team is now complete
        new_total = sum(len(team_data[part]) for part in team_data)
        if new_total == 6 and all(len(team_data[part]) == limits[part] for part in ["🦿", "🦾", "🧠", "🫀"]):
            try:
                await interaction.edit_original_response(
                    content="🎉 **Combiner team complete!** The summon interface has been closed.",
                    embed=None, view=None
                )
                self.parent_view.stop()
            except:
                pass
        else:
            # Update parent view
            self.parent_view.update_buttons()


class ProfileView(discord.ui.View):
    """Discord UI view for comprehensive user profiles."""
    
    def __init__(self, target_member, ctx):
        super().__init__(timeout=300)
        self.target_member = target_member
        self.ctx = ctx
        self.current_view = "me"
    
    def get_rank_emojis(self, count):
        """Get rank emojis for leaderboards"""
        if count <= 5:
            return ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        else:
            return ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    async def _get_player_stats(self, player_id):
        """Get or create player statistics from UserDataManager."""
        try:
            if hasattr(self.ctx.bot, 'user_data_manager') and self.ctx.bot.user_data_manager:
                return await self.ctx.bot.user_data_manager.get_energon_stats(player_id)
            else:
                # Fallback to legacy system
                if player_id not in self.ctx.bot.player_stats:
                    self.ctx.bot.player_stats[player_id] = {
                        "games_won": 0,
                        "games_lost": 0,
                        "challenges_won": 0,
                        "challenges_lost": 0,
                        "total_energon_gained": 0,
                        "total_energon_lost": 0,
                        "energon_bank": 0,
                        "challenge_energon_won": 0,
                        "challenge_energon_lost": 0,
                        "current_energon": 0,
                        "lifetime_energon": 0
                    }
                else:
                    stats = self.ctx.bot.player_stats[player_id]
                    if "energon_bank" not in stats:
                        stats["energon_bank"] = 0
                    if "challenge_energon_won" not in stats:
                        stats["challenge_energon_won"] = 0
                    if "challenge_energon_lost" not in stats:
                        stats["challenge_energon_lost"] = 0
                    if "current_energon" not in stats:
                        stats["current_energon"] = 0
                    if "lifetime_energon" not in stats:
                        stats["lifetime_energon"] = 0
                return self.ctx.bot.player_stats[player_id]
        except Exception as e:
            print(f"Error getting player stats for {player_id}: {e}")
            return {
                "games_won": 0,
                "games_lost": 0,
                "challenges_won": 0,
                "challenges_lost": 0,
                "total_energon_gained": 0,
                "total_energon_lost": 0,
                "energon_bank": 0,
                "challenge_energon_won": 0,
                "challenge_energon_lost": 0,
                "current_energon": 0,
                "lifetime_energon": 0
            }
    
    async def create_me_embed(self):
        """Create the personal stats embed"""
        player_id = str(self.target_member.id)
        stats = await self._get_player_stats(player_id)
        
        # Get transformer data from UserDataManager
        transformer_name = "Not assigned"
        faction = "Unknown"
        transformer_class = "Unknown"
        color = discord.Color.blue()  # Default
        
        try:
            if hasattr(self.ctx.bot, 'user_data_manager') and self.ctx.bot.user_data_manager:
                theme_data = await self.ctx.bot.user_data_manager.get_theme_system_data(player_id, self.target_member.display_name)
                transformer_data = theme_data.get("transformer", {})
                
                if transformer_data:
                    transformer_name = transformer_data.get("name", "Not assigned")
                    faction = transformer_data.get("faction", "Unknown").capitalize()
                    transformer_class = transformer_data.get("class", "Unknown").capitalize()
                    
                    # Set color based on faction
                    if transformer_data.get("faction", "").lower() == "autobot":
                        color = discord.Color.blue()
                    elif transformer_data.get("faction", "").lower() == "decepticon":
                        color = discord.Color.red()
            else:
                # Fallback to legacy system
                self.ctx.bot.data_manager._ensure_state_loaded()
                transformer_data = getattr(self.ctx.bot, 'transformer_names', {}).get(player_id)
                
                if transformer_data and isinstance(transformer_data, dict):
                    transformer_name = transformer_data.get("name", "Not assigned")
                    faction = transformer_data.get("faction", "Unknown").capitalize()
                    transformer_class = transformer_data.get("class", "Unknown").capitalize()
                    
                    if transformer_data.get("faction", "").lower() == "autobot":
                        color = discord.Color.blue()
                    elif transformer_data.get("faction", "").lower() == "decepticon":
                        color = discord.Color.red()
                elif transformer_data:
                    transformer_name = transformer_data
                    if any(role.name.lower() == "autobot" for role in self.target_member.roles):
                        faction = "Autobot"
                    elif any(role.name.lower() == "decepticon" for role in self.target_member.roles):
                        faction = "Decepticon"
        except Exception as e:
            print(f"Error getting transformer data for {player_id}: {e}")
        
        embed = discord.Embed(
            title=f"📊 {self.target_member.display_name}'s Profile",
            description="Personal statistics and Transformer identity",
            color=color
        )
        
        # Add Transformer identity
        if transformer_name != "Not assigned":
            if transformer_class != "Unknown":
                embed.add_field(
                    name="🤖 Transformer Identity", 
                    value=f"**{transformer_name}**\n{faction} {transformer_class}", 
                    inline=False
                )
            else:
                embed.add_field(
                    name="🤖 Transformer Identity", 
                    value=f"**{transformer_name}** ({faction})", 
                    inline=False
                )
        else:
            embed.add_field(
                name="🤖 Transformer Identity", 
                value="*Use `/spark` to get your Transformer identity!*", 
                inline=False
            )
        
        # Add game statistics
        embed.add_field(name="🏆 Games Won", value=stats.get('games_won', 0), inline=True)
        embed.add_field(name="💀 Games Lost", value=stats.get('games_lost', 0), inline=True)
        embed.add_field(name="🏦 Banked Energon", value=stats.get('energon_bank', 0), inline=True)
        embed.add_field(name="⚔️ Challenges Won", value=stats.get('challenges_won', 0), inline=True)
        embed.add_field(name="💰 Challenge Winnings", value=stats.get('challenge_energon_won', 0), inline=True)
        embed.add_field(name="💎 Total Energon Gained", value=stats.get('total_energon_gained', 0), inline=True)
        embed.add_field(name="💔 Challenges Lost", value=stats.get('challenges_lost', 0), inline=True)
        embed.add_field(name="💸 Challenge Losses", value=stats.get('challenge_energon_lost', 0), inline=True)
        embed.add_field(name="💸 Total Energon Lost", value=stats.get('total_energon_lost', 0), inline=True)

        # Calculate win rates
        total_games = stats.get('games_won', 0) + stats.get('games_lost', 0)
        total_challenges = stats.get('challenges_won', 0) + stats.get('challenges_lost', 0)
        
        if total_games > 0:
            game_win_rate = (stats.get('games_won', 0) / total_games) * 100
            embed.add_field(name="📈 Game Win Rate", value=f"{game_win_rate:.1f}%", inline=True)
        
        if total_challenges > 0:
            challenge_win_rate = (stats.get('challenges_won', 0) / total_challenges) * 100
            embed.add_field(name="⚔️ Challenge Win Rate", value=f"{challenge_win_rate:.1f}%", inline=True)
        
        # Add current energon if available
        current_energon = stats.get('current_energon', 0)
        if current_energon > 0:
            embed.add_field(name="⚡ Current Game Energon", value=current_energon, inline=True)
        
        return embed
    
    def create_pet_embed(self):
        """Create the pet stats embed"""
        player_id = str(self.target_member.id)
        pet = getattr(self.ctx.bot, 'pet_system', None)
        
        if not pet:
            embed = discord.Embed(
                title="🤖 Pet System Unavailable",
                description="Pet system is not loaded.",
                color=discord.Color.red()
            )
            return embed
        
        pet_data = pet.get_user_pet(self.target_member.id)
        
        if not pet_data:
            embed = discord.Embed(
                title=f"🤖 {self.target_member.display_name}'s Pet",
                description="No pet found! Use `/get_pet autobot` or `/get_pet decepticon` to get one.",
                color=discord.Color.orange()
            )
            return embed
        
        # Import required modules from pets_system
        try:
            from Systems.Pets.pets_system import PET_STAGES, LEVEL_THRESHOLDS, get_stage_emoji
            stage = PET_STAGES[pet_data["level"]]
            
            # Set faction-based color
            faction = pet_data.get('faction', 'Unknown').lower()
            if faction == 'autobot':
                embed_color = 0xCC0000  # Red for Autobots
            elif faction == 'decepticon':
                embed_color = 0x800080  # Purple for Decepticons
            else:
                embed_color = 0x808080  # Gray for Unknown
                
            # Get faction-based emoji
            faction_emoji = "🔴" if faction == 'autobot' else "🟣" if faction == 'decepticon' else "⚡"
            
            # Get stage emoji
            try:
                stage_emoji = get_stage_emoji(pet_data['level'])
            except:
                stage_emoji = "🥚"
                
            embed = discord.Embed(
                title=f"{stage_emoji} {pet_data['name']} - {pet_data.get('faction', 'Unknown')}",
                color=embed_color
            )
            
            # Always show full date and time
            created = datetime.fromisoformat(pet_data["created_at"])
            age_text = created.strftime("%B %d, %Y at %I:%M %p")
            
            embed.add_field(name="🧬 Stage", value=f"{stage_emoji} {pet_data['level']} - {stage['name']}", inline=True)
            embed.add_field(name="🗓️ Created", value=age_text, inline=True)
            
            max_level = max(LEVEL_THRESHOLDS.keys())
            if pet_data['level'] < max_level:
                threshold = LEVEL_THRESHOLDS[pet_data['level']]
                progress = min(pet_data['experience'] / threshold, 1.0)
                bar_length = 10
                filled_length = int(bar_length * progress)
                
                # Determine faction color for progress bar
                filled_char = "🟥" if faction == 'autobot' else "🟪" if faction == 'decepticon' else "🟨"
                empty_char = "⬛"
                bar = filled_char * filled_length + empty_char * (bar_length - filled_length)
                embed.add_field(name="📊 Level Progress", value=f"{bar} {pet_data['experience']}/{threshold} XP", inline=False)
            
            # Get detailed stats like PetStatusView
            detailed_stats = self.get_pet_detailed_stats(player_id)
            
            embed.add_field(name="🔋 **Energy**", value=f"{pet_data['energy']:.0f}/{pet_data['max_energy']:.0f}", inline=True)
            embed.add_field(name="🔧 **Maintenance**", value=f"{pet_data['maintenance']:.0f}/{pet_data['max_maintenance']:.0f}", inline=True)
            embed.add_field(name="😊 **Happiness**", value=f"{pet_data['happiness']:.0f}/{pet_data['max_happiness']:.0f}", inline=True)
            embed.add_field(name="⚡ **Power**", value=f"⚔️ Attack: {pet_data['attack']} | 🛡️ Defense: {pet_data['defense']}", inline=False)
            
            embed.add_field(
                name="🏆 **Achievements**", 
                value=f"⚔️ **__Total Battle Wins__**: {detailed_stats['battles']['total']['wins']}\n"
                      f"💀 **__Total Battle Losses__**: {detailed_stats['battles']['total']['losses']}\n"
                      f"📋 **__Missions Completed__**: {pet_data.get('missions_completed', 0)}\n"
                      f"💰 **__Total Energon__**: {detailed_stats['energon']['total']:,}\n"
                      f"⭐ **__Total Experience__**: {detailed_stats['experience']['total']:,}", 
                inline=False
            )
            
            embed.set_footer(text="Use the buttons below for detailed stats or refresh")
            
        except (ImportError, KeyError):
            # Fallback if pets_system modules are not available
            embed = discord.Embed(
                title=f"🤖 {pet_data['name']} - {pet_data.get('faction', 'Unknown')}",
                description=f"**{self.target_member.display_name}'s Digital Pet**",
                color=discord.Color.blue() if pet_data.get('faction') == 'Autobot' else discord.Color.red()
            )
            
            # Always show full date and time
            created = datetime.fromisoformat(pet_data["created_at"])
            age_text = created.strftime("%B %d, %Y at %I:%M %p")
            
            embed.add_field(name="🧬 Stage", value=f"Level {pet_data['level']}", inline=True)
            embed.add_field(name="🗓️ Obtained", value=age_text, inline=True)
            
            embed.add_field(name="⚡ Energy", value=f"{pet_data['energy']}/100", inline=True)
            embed.add_field(name="😊 Happiness", value=f"{pet_data['happiness']}/100", inline=True)
            
        return embed

    def get_pet_detailed_stats(self, user_id: str) -> dict:
        """Get detailed pet statistics like PetStatusView does"""
        try:
            # Import user_data_manager to access user data
            from user_data_manager import user_data_manager
            
            # Load user data to get detailed stats
            user_data = user_data_manager.get_user_data(int(user_id))
            pet = user_data.get('pet_data', {})
            
            if not pet:
                return {
                    'pet': {},
                    'battles': {'total': {'wins': 0, 'losses': 0}},
                    'energon': {'total': 0},
                    'experience': {'total': 0, 'mission': 0, 'battle': 0, 'challenge': 0, 'search': 0, 'training': 0, 'charge': 0, 'play': 0, 'repair': 0}
                }
            
            # Calculate totals from pet data
            return {
                'pet': pet,
                'battles': {
                    'total': {
                        'wins': pet.get('battles_won', 0),
                        'losses': pet.get('battles_lost', 0)
                    }
                },
                'energon': {
                    'total': pet.get('total_energon_earned', 0)
                },
                'experience': {
                    'total': pet.get('experience', 0),
                    'mission': pet.get('mission_xp_earned', 0),
                    'battle': pet.get('battle_xp_earned', 0),
                    'challenge': pet.get('challenge_xp_earned', 0),
                    'search': pet.get('search_xp_earned', 0),
                    'training': pet.get('training_xp_earned', 0),
                    'charge': pet.get('charge_xp_earned', 0),
                    'play': pet.get('play_xp_earned', 0),
                    'repair': pet.get('repair_xp_earned', 0)
                }
            }
        except Exception as e:
            # Fallback to basic stats
            return {
                'pet': {},
                'battles': {'total': {'wins': 0, 'losses': 0}},
                'energon': {'total': 0},
                'experience': {'total': 0, 'mission': 0, 'battle': 0, 'challenge': 0, 'search': 0, 'training': 0, 'charge': 0, 'play': 0, 'repair': 0}
            }

    def create_combiner_embed(self):
        """Create the detailed combiner embed"""
        player_id = str(self.target_member.id)
        self.ctx.bot.data_manager._ensure_state_loaded()
        combiner_teams = getattr(self.ctx.bot, 'combiner_teams', {})
        combiner_names = getattr(self.ctx.bot, 'combiner_names', {})
        
        # Find user's combiner team
        user_team_data = None
        user_part = None
        team_message_id = None
        
        for message_id, team_data in combiner_teams.items():
            for part, members in team_data.items():
                if player_id in members:
                    user_team_data = team_data
                    user_part = part
                    team_message_id = message_id
                    break
            if user_team_data:
                break
        
        if not user_team_data:
            embed = discord.Embed(
                title=f"🔗 {self.target_member.display_name}'s Combiner Status",
                description="Not currently part of any combiner team.\n\nUse `/combiner` to start or join a combiner team!",
                color=discord.Color.orange()
            )
            return embed
        
        part_names = {"🦿": "Leg", "🦾": "Arm", "🧠": "Head", "🫀": "Body"}
        part_name = part_names.get(user_part, "Unknown")
        
        # Get combiner name and formation date
        combiner_data = combiner_names.get(team_message_id, {})
        if isinstance(combiner_data, dict):
            combiner_name = combiner_data.get('name', 'Unnamed Combiner')
            formation_timestamp = combiner_data.get('timestamp')
        else:
            combiner_name = combiner_data or 'Unnamed Combiner'
            formation_timestamp = None
        
        # Check if team is complete
        total_slots = sum(2 if part in ["🦿", "🦾"] else 1 for part in part_names.keys())  # 2 legs, 2 arms, 1 head, 1 body = 6 total
        filled_slots = sum(len(members) for members in user_team_data.values())
        is_complete = filled_slots == total_slots
        
        embed = discord.Embed(
            title=f"🔗 Combiner Team: {combiner_name}",
            description=f"**{self.target_member.display_name}'s Role:** {part_name}\n**Team Status:** {'✅ Complete' if is_complete else f'🔄 In Progress ({filled_slots}/{total_slots} slots filled)'}",
            color=discord.Color.green() if is_complete else discord.Color.yellow()
        )
        
        # Add detailed team composition with clear position indicators
        for part_emoji, part_display in part_names.items():
            members_in_part = user_team_data.get(part_emoji, [])
            max_slots = 2 if part_emoji in ["🦿", "🦾"] else 1

            if members_in_part:
                member_list = []
                for i, m_id in enumerate(members_in_part):
                    try:
                        member_obj = self.ctx.guild.get_member(int(m_id))
                        if member_obj:
                            t_data = getattr(self.ctx.bot, 'transformer_names', {}).get(m_id)
                            if isinstance(t_data, dict):
                                t_name = t_data.get("name", member_obj.display_name)
                                faction = t_data.get("faction", "Unknown")
                                t_class = t_data.get("class", "Unknown")
                                # Add position indicator for parts with multiple slots
                                if max_slots > 1:
                                    if part_emoji == "🦾":  # Arms
                                        position = f" (Left)" if i == 0 else f" (Right)"
                                    elif part_emoji == "🦿":  # Legs
                                        position = f" (Left)" if i == 0 else f" (Right)"
                                    else:
                                        position = f" ({part_display} {i+1})"
                                else:
                                    position = ""
                                member_list.append(f"**{t_name}**{position}\n{faction} {t_class}")
                            else:
                                t_name = t_data or member_obj.display_name
                                if max_slots > 1:
                                    if part_emoji == "🦾":  # Arms
                                        position = f" (Left)" if i == 0 else f" (Right)"
                                    elif part_emoji == "🦿":  # Legs
                                        position = f" (Left)" if i == 0 else f" (Right)"
                                    else:
                                        position = f" ({part_display} {i+1})"
                                else:
                                    position = ""
                                member_list.append(f"**{t_name}**{position}")
                    except:
                        continue
                
                value = "\n\n".join(member_list) if member_list else "*No members*"
                if len(members_in_part) < max_slots:
                    value += f"\n\n*{max_slots - len(members_in_part)} slot(s) available*"
            else:
                value = f"*{max_slots} slot(s) available*"
            
            embed.add_field(
                name=f"{part_emoji} {part_display} ({len(members_in_part)}/{max_slots})",
                value=value,
                inline=True
            )
        
        # Add team formation date if available
        if formation_timestamp and is_complete:
            from datetime import datetime
            formation_date = datetime.fromtimestamp(formation_timestamp)
            embed.add_field(
                name="📅 Team Formation",
                value=formation_date.strftime("%B %d, %Y at %I:%M %p"),
                inline=False
            )
        
        # Add instructions
        embed.add_field(
            name="ℹ️ How Combiners Work",
            value="• Teams need 6 members: 2 legs, 2 arms, 1 head, 1 body\n• Heads control the Combiner in Mega-Fights\n• Use `/combiner` to start a new team\n• Use `/mega_fight` to start Combiner Battle",
            inline=False
        )
        
        return embed

    async def create_coin_embed(self):
        """Create the CyberCoin portfolio embed"""
        player_id = str(self.target_member.id)
        
        # Try to get CyberCoin data from the market system
        try:
            # Check if market system is available
            if hasattr(self.ctx.bot, 'market_manager') and self.ctx.bot.market_manager:
                from Systems.Energon.energon_system import MarketManager
                market_manager = self.ctx.bot.market_manager
                
                # Get user's CyberCoin summary
                coin_summary = market_manager.get_user_cybercoin_summary(player_id)
                
                embed = discord.Embed(
                    title=f"💰 {self.target_member.display_name}'s CyberCoin Portfolio",
                    description="Detailed CyberCoin investment and trading history",
                    color=discord.Color.gold()
                )
                
                # Current holdings
                current_coins = coin_summary.get('total_coins', 0)
                total_invested = coin_summary.get('total_invested', 0)
                total_sold = coin_summary.get('total_sold', 0)
                total_made = coin_summary.get('total_made', 0)
                unrealized_pnl = coin_summary.get('unrealized_pnl', 0)
                realized_profit = coin_summary.get('realized_profit', 0)
                most_coins_ever = coin_summary.get('most_coins_ever', 0)
                
                # Calculate total profit
                total_profit = realized_profit + unrealized_pnl
                
                # Add main portfolio fields
                embed.add_field(
                    name="🏦 Current Holdings",
                    value=f"**Current Coins:** {current_coins:,}\n**Most Coins Ever:** {most_coins_ever:,}",
                    inline=True
                )
                
                embed.add_field(
                    name="💵 Investment Summary",
                    value=f"**Amount Invested:** {total_invested:,} Energon\n**Amount Made:** {total_made:,} Energon",
                    inline=True
                )
                
                embed.add_field(
                    name="📊 Profit Analysis",
                    value=f"**Realized Profit:** {realized_profit:,}\n**Unrealized P&L:** {unrealized_pnl:,}\n**Total Profit:** {total_profit:,}",
                    inline=True
                )
                
                # Add transaction history if available
                recent_transactions = coin_summary.get('recent_transactions', [])
                if recent_transactions:
                    recent_text = ""
                    for tx in recent_transactions[:5]:  # Show last 5 transactions
                        tx_type = "📈 Buy" if tx['type'] == 'buy' else "📉 Sell"
                        recent_text += f"{tx_type}: {tx['coins']} coins @ {tx['price']} Energon\n"
                    
                    embed.add_field(
                        name="🔄 Recent Transactions",
                        value=recent_text,
                        inline=False
                    )
                
                # Add ROI calculation
                if total_invested > 0:
                    roi = (total_profit / total_invested) * 100
                    roi_emoji = "📈" if roi > 0 else "📉" if roi < 0 else "➡️"
                    embed.add_field(
                        name="🎯 Overall ROI",
                        value=f"{roi_emoji} {roi:.2f}%",
                        inline=True
                    )
                
                embed.set_footer(text="Use /market to access the CyberCoin trading platform")
                
            else:
                # Fallback if market system is not available
                embed = discord.Embed(
                    title=f"💰 {self.target_member.display_name}'s CyberCoin Portfolio",
                    description="CyberCoin system is not available.",
                    color=discord.Color.red()
                )
                
        except Exception as e:
            # Error handling
            embed = discord.Embed(
                title=f"💰 {self.target_member.display_name}'s CyberCoin Portfolio",
                description=f"Error loading CyberCoin data: {str(e)}",
                color=discord.Color.red()
            )
        
        return embed
    
    async def get_current_embed(self):
        """Get the current embed based on the view"""
        if self.current_view == "me":
            return await self.create_me_embed()
        elif self.current_view == "pet":
            return await self.create_pet_embed()
        elif self.current_view == "combiner":
            return await self.create_combiner_embed()
        elif self.current_view == "coin":
            return await self.create_coin_embed()
        else:
            return await self.create_me_embed()
    
    @discord.ui.button(label='Me', style=discord.ButtonStyle.primary, emoji='🪞')
    async def me_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_view = "me"
        embed = await self.get_current_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='Pet', style=discord.ButtonStyle.secondary, emoji='🤖')
    async def pet_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_view = "pet"
        embed = await self.get_current_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='Combiner', style=discord.ButtonStyle.secondary, emoji='⛓️')
    async def combiner_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_view = "combiner"
        embed = await self.get_current_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='Coin', style=discord.ButtonStyle.secondary, emoji='🪙')
    async def coin_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_view = "coin"
        embed = await self.get_current_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @commands.hybrid_command(name='me', description="View your or another user's comprehensive profile with interactive navigation")
    async def me(self, ctx: commands.Context, member: discord.Member = None):
        """View comprehensive user profile with interactive navigation."""
        if not self.role_checker.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can view profiles! Please get the 'Cybertronian Citizen' role first.")
            return

        # Default to the command user if no member is specified
        target_member = member if member else ctx.author
        
        # Create the view and initial embed
        view = ProfileView(target_member, ctx)
        embed = await view.get_current_embed()
        
        await ctx.send(embed=embed, view=view)


def determine_user_class(answers: dict) -> str:
    """Determine user class based on their answers"""
    try:
        log_in = answers.get("log_in_frequency", "").lower()
        city_count = answers.get("city_count", "").lower()
        war_approach = answers.get("war_approach", "").lower()
        priority = answers.get("priority", "").lower()
        infrastructure = answers.get("infrastructure", "").lower()
        
        # Decepticon criteria
        is_decepticon = (
            ("destruction!" in priority or "raiding" in priority) and
            ("infra?" in infrastructure or "little as possible" in infrastructure) and
            ("i'll solo anyone!" in war_approach) and
            ("all day" in log_in or "daily" in log_in)
        )
        
        # Maverick criteria
        is_maverick = (
            ("peace" in priority or "raiding" in priority) and
            ("some is ok" in infrastructure or "little as possible" in infrastructure) and
            ("2nd wave" in war_approach or "1st wave" in war_approach) and
            ("all day" in log_in or "daily" in log_in or "2-3 times a week" in log_in)
        )
        
        if is_decepticon:
            return "Decepticon"
        elif is_maverick:
            return "Maverick"
        else:
            return "Autobot"
            
    except Exception as e:
        logger.exception(f"Error in determine_user_class: {e}")
        return "Autobot"

class AnalysisView(ui.View):
    """Main view for starting the analysis process"""
    
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(StartAnalysisButton())

class StartAnalysisButton(ui.Button):
    """Button to initiate the analysis process"""
    
    def __init__(self):
        super().__init__(
            label="Start Analysis",
            style=discord.ButtonStyle.primary,
            custom_id="start_analysis"
        )
    
    async def callback(self, interaction: discord.Interaction):
        try:
            # Initialize user data storage
            interaction.client.user_data.setdefault(interaction.user.id, {})
            
            # Start with first question
            view = LogInFrequencyView()
            await interaction.response.send_message(
                "**Question 1/5: How often do you log in?**",
                view=view,
                ephemeral=True
            )
        except Exception as e:
            logger.exception(f"Error starting analysis: {e}")
            await interaction.response.send_message(
                f"An error occurred: {str(e)}", 
                ephemeral=True
            )

class LogInFrequencyView(ui.View):
    """View for login frequency question"""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(LogInFrequencySelect())

class LogInFrequencySelect(ui.Select):
    """Select menu for login frequency options"""
    
    def __init__(self):
        options = [
            discord.SelectOption(label="All day", value="all day"),
            discord.SelectOption(label="Daily", value="daily"),
            discord.SelectOption(label="2-3 times a week", value="2-3 times a week"),
            discord.SelectOption(label="Weekly", value="weekly"),
            discord.SelectOption(label="Less than weekly", value="less than weekly")
        ]
        super().__init__(
            placeholder="Choose your login frequency...",
            options=options,
            custom_id="log_in_select"
        )
    
    async def callback(self, interaction: discord.Interaction):
        try:
            # Store answer
            user_data = interaction.client.user_data.setdefault(interaction.user.id, {})
            user_data["log_in_frequency"] = self.values[0]
            
            # Move to next question
            view = CityCountView()
            await interaction.response.edit_message(
                content="**Question 2/5: How many cities do you have?**",
                view=view
            )
        except Exception as e:
            logger.exception(f"Error in LogInFrequencySelect: {e}")
            await interaction.response.send_message(
                f"An error occurred: {str(e)}", 
                ephemeral=True
            )

class CityCountView(ui.View):
    """View for city count question"""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(CityCountSelect())

class CityCountSelect(ui.Select):
    """Select menu for city count options"""
    
    def __init__(self):
        options = [
            discord.SelectOption(label="1-11", value="1-11"),
            discord.SelectOption(label="12-19", value="12-19"),
            discord.SelectOption(label="20-25", value="20-25"),
            discord.SelectOption(label="25-30+", value="25-30+")
        ]
        super().__init__(
            placeholder="Choose your city count...",
            options=options,
            custom_id="city_count_select"
        )
    
    async def callback(self, interaction: discord.Interaction):
        try:
            # Store answer
            user_data = interaction.client.user_data.setdefault(interaction.user.id, {})
            user_data["city_count"] = self.values[0]
            
            # Move to next question
            view = WarApproachView()
            await interaction.response.edit_message(
                content="**Question 3/5: What's your approach to war?**",
                view=view
            )
        except Exception as e:
            logger.exception(f"Error in CityCountSelect: {e}")
            await interaction.response.send_message(
                f"An error occurred: {str(e)}", 
                ephemeral=True
            )

class WarApproachView(ui.View):
    """View for war approach question"""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(WarApproachSelect())

class WarApproachSelect(ui.Select):
    """Select menu for war approach options"""
    
    def __init__(self):
        options = [
            discord.SelectOption(label="I'll solo ANYONE!", value="i'll solo anyone!"),
            discord.SelectOption(label="I'll be 1st wave", value="1st wave"),
            discord.SelectOption(label="I'll be 2nd wave", value="2nd wave"),
            discord.SelectOption(label="Moral Support Only", value="Moral Support Only"),
            discord.SelectOption(label="I'll Delete if Attacked", value="i'll delete if attacked")
        ]
        super().__init__(
            placeholder="How do you approach war?",
            options=options,
            custom_id="war_approach_select"
        )
    
    async def callback(self, interaction: discord.Interaction):
        try:
            # Store answer
            user_data = interaction.client.user_data.setdefault(interaction.user.id, {})
            user_data["war_approach"] = self.values[0]
            
            # Move to next question
            view = PriorityView()
            await interaction.response.edit_message(
                content="**Question 4/5: What's your top priority or main objective?**",
                view=view
            )
        except Exception as e:
            logger.exception(f"Error in WarApproachSelect: {e}")
            await interaction.response.send_message(
                f"An error occurred: {str(e)}", 
                ephemeral=True
            )

class PriorityView(ui.View):
    """View for priority question"""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(PrioritySelect())

class PrioritySelect(ui.Select):
    """Select menu for priority options"""
    
    def __init__(self):
        options = [
            discord.SelectOption(label="Revenue", value="revenue"),
            discord.SelectOption(label="Resources", value="resources"),
            discord.SelectOption(label="Peace", value="peace"),
            discord.SelectOption(label="Raiding", value="raiding"),
            discord.SelectOption(label="DESTRUCTION!", value="destruction!")
        ]
        super().__init__(
            placeholder="Choose your priority...",
            options=options,
            custom_id="priority_select"
        )
    
    async def callback(self, interaction: discord.Interaction):
        try:
            # Store answer
            user_data = interaction.client.user_data.setdefault(interaction.user.id, {})
            user_data["priority"] = self.values[0]
            
            # Move to final question
            view = InfrastructureView()
            await interaction.response.edit_message(
                content="**Question 5/5: How do you feel about Infrastructure?**",
                view=view
            )
        except Exception as e:
            logger.exception(f"Error in PrioritySelect: {e}")
            await interaction.response.send_message(
                f"An error occurred: {str(e)}", 
                ephemeral=True
            )

class InfrastructureView(ui.View):
    """View for infrastructure question"""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(InfrastructureSelect())

class InfrastructureSelect(ui.Select):
    """Select menu for infrastructure options"""
    
    def __init__(self):
        options = [
            discord.SelectOption(label="Infra? What's that?", value="infra? what's that?"),
            discord.SelectOption(label="Little as possible", value="little as possible"),
            discord.SelectOption(label="Some is ok", value="some is ok"),
            discord.SelectOption(label="I love infra", value="i love infra")
        ]
        super().__init__(
            placeholder="Choose your infrastructure approach...",
            options=options,
            custom_id="infrastructure_select"
        )
    
    async def callback(self, interaction: discord.Interaction):
        try:
            # Store final answer
            user_data = interaction.client.user_data.setdefault(interaction.user.id, {})
            user_data["infrastructure"] = self.values[0]
            
            # Calculate results
            user_class = determine_user_class(user_data)
            
            # Assign role
            if user_class in ROLE_IDS:
                role = interaction.guild.get_role(ROLE_IDS[user_class])
                if role:
                    await interaction.user.add_roles(role)
            
            # Send results to admin channel
            await self._send_admin_results(interaction, user_class, user_data)
            
            # Show final results to user
            await self._show_user_results(interaction, user_class, user_data)
            
            # Clean up user data
            interaction.client.user_data.pop(interaction.user.id, None)
            
        except Exception as e:
            logger.exception(f"Error in InfrastructureSelect: {e}")
            await interaction.response.send_message(
                f"An error occurred: {str(e)}", 
                ephemeral=True
            )
    
    async def _send_admin_results(self, interaction: discord.Interaction, user_class: str, user_data: dict):
        """Send analysis results to admin channel"""
        try:
            results_channel = interaction.guild.get_channel(RESULTS_CHANNEL_ID)
            if not results_channel:
                logger.error(f"Results channel not found: {RESULTS_CHANNEL_ID}")
                return
            
            embed = discord.Embed(
                title="📊 New Analysis Results",
                color=0x00ff00,
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(
                name="User",
                value=f"{interaction.user.mention} ({interaction.user.display_name})",
                inline=False
            )
            embed.add_field(name="Assigned Class", value=user_class, inline=True)
            embed.add_field(name="User ID", value=str(interaction.user.id), inline=True)
            
            # Add all answers
            for key, value in user_data.items():
                embed.add_field(
                    name=key.replace('_', ' ').title(),
                    value=value.title(),
                    inline=True
                )
            
            await results_channel.send(embed=embed)
            logger.info(f"Results sent to admin channel for user {interaction.user.id}")
            
        except Exception as e:
            logger.exception(f"Failed to send results to admin channel: {e}")
    
    async def _show_user_results(self, interaction: discord.Interaction, user_class: str, user_data: dict):
        """Show final results to the user"""
        try:
            answers_text = "\n".join(
                f"- {k.replace('_', ' ').title()}: {v.title()}" 
                for k, v in user_data.items()
            )
            
            await interaction.response.edit_message(
                content=(
                    f"**🎉 Analysis Complete! 🎉**\n\n"
                    f"**Your Class:** {user_class}\n\n"
                    f"**Your Answers:**\n{answers_text}\n\n"
                    f"**Role assigned!** You now have the {user_class} role."
                ),
                view=None
            )
            
        except Exception as e:
            logger.exception(f"Error showing user results: {e}")


async def analysis_command(self, ctx: commands.Context):
    """Start an Allspark Analysis"""
    try:
        view = AnalysisView()
        embed = discord.Embed(
            title="🤖 Allspark Analysis",
            description=(
                "Welcome to the Allspark Analysis! This will help determine your faction classification.\n\n"
                "Click the button below to begin the 5-question assessment."
            ),
            color=0x00ff00
        )
        await ctx.send(embed=embed, view=view, ephemeral=True)
    except Exception as e:
        logger.exception(f"Error in analysis command: {e}")
        await ctx.send(f"An error occurred: {str(e)}", ephemeral=True)

# Add the analysis command to ThemeCommands
ThemeCommands.analysis = analysis_command

# Convenience functions for backward compatibility
async def setup(bot: commands.Bot) -> None:
    """Initialize the theme system with the bot instance."""
    await bot.add_cog(ThemeCommands(bot))

# Export the main components
__all__ = [
    'ThemeCommands',
    'setup_theme_system',
    'NameGenerator',
    'RoleChecker',
    'DataManager',
    'CombinerManager',
    'ThemeConfig',
    'ProfileView',
    'AnalysisView',
    'StartAnalysisButton',
    'LogInFrequencyView',
    'CityCountView',
    'WarApproachView',
    'PriorityView',
    'InfrastructureView'
]