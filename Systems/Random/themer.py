import discord
from discord import app_commands
from discord.ext import commands
from discord import ui
import random
import asyncio
import time
import os
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from config import RESULTS_CHANNEL_ID
import logging
import sys

# Import external dependencies
from config import ROLE_IDS
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'Json'))
from cyberchronicles import get_rpg_system, add_energon_to_character, create_character_from_spark

# Import optimized user data manager
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from user_data_manager import OptimizedUserDataManager

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
    """Optimized DataManager - fully integrated with OptimizedUserDataManager."""
    
    def __init__(self, bot_instance: commands.Bot):
        self.bot = bot_instance
        self.user_data_manager = getattr(bot_instance, 'user_data_manager', OptimizedUserDataManager())
        logger.info("DataManager initialized with OptimizedUserDataManager")

    async def is_user_in_any_combiner(self, user_id: str) -> Tuple[bool, Optional[str]]:
        """Check if a user is already part of any combiner team."""
        try:
            team_info = await self.user_data_manager.get_user_combiner_team(str(user_id))
            return bool(team_info), team_info.get("team_id") if team_info else None
        except Exception as e:
            logger.error(f"Error checking combiner team for user {user_id}: {e}")
            return False, None

    async def remove_user_from_all_combiners(self, user_id: str, username: str = None) -> bool:
        """Remove a user from all combiner teams."""
        try:
            return await self.user_data_manager.remove_user_from_combiner_team(
                str(user_id), username or "Unknown"
            )
        except Exception as e:
            logger.error(f"Error removing user {user_id} from combiner teams: {e}")
            return False

    async def get_user_theme_data(self, user_id: str, username: str = None) -> Dict[str, Any]:
        """Get theme system data for a user."""
        try:
            return await self.user_data_manager.get_theme_system_data(user_id, username)
        except Exception as e:
            logger.error(f"Error getting theme data for user {user_id}: {e}")
            return {}

    async def save_user_theme_data(self, user_id: str, username: str, theme_data: Dict[str, Any]) -> bool:
        """Save theme system data for a user."""
        try:
            return await self.user_data_manager.save_theme_system_data(user_id, username, theme_data)
        except Exception as e:
            logger.error(f"Error saving theme data for user {user_id}: {e}")
            return False

    async def get_user_theme_data_section(self, user_id: str, section: str, default=None):
        """Get specific section from user theme data."""
        if default is None:
            default = {}
        
        theme_data = await self.get_user_theme_data(user_id)
        return theme_data.get(section, default)

    async def save_user_theme_data_section(self, user_id: str, username: str, section: str, data):
        """Save specific section to user theme data."""
        theme_data = await self.get_user_theme_data(user_id, username)
        theme_data[section] = data
        return await self.save_user_theme_data(user_id, username, theme_data)


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
    """Optimized CombinerManager - uses UserDataManager for all operations."""
    
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager

    async def get_team_composition(self, team_id: str) -> Dict[str, List[str]]:
        """Get team composition for a given team ID."""
        try:
            team_data = await self.data_manager.get_user_theme_data_section(
                team_id, "combiner_teams", {}
            )
            return team_data
        except Exception as e:
            logger.error(f"Error getting team composition for {team_id}: {e}")
            return {"🦿": [], "🦾": [], "🧠": [], "🫀": []}

    async def is_team_complete(self, team_id: str) -> bool:
        """Check if a team is complete (has all 6 members)."""
        team_data = await self.get_team_composition(team_id)
        total_members = sum(len(members) for members in team_data.values())
        return total_members == 6

    async def update_buttons(self):
        """Update the buttons based on current selection and team status."""
        # Get current user
        user = self.ctx.author if hasattr(self, 'ctx') else None
        if not user:
            return
            
        # Check if user is in any combiner team
        in_combiner, _ = await self.theme_cog.data_manager.is_user_in_any_combiner(user.id)
        
        # Update button states
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                if in_combiner:
                    item.disabled = True
                else:
                    item.disabled = False


class CombinerView(discord.ui.View):
    """Discord UI view for combiner team management."""
    
    def __init__(self, message_id: str, guild: discord.Guild, theme_cog: "ThemeSystem"):
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
            user_data = await self.theme_cog.data_manager.get_user_theme_data(str(user.id), str(user))
            transformer_name = user_data.get("transformer_name")
            display_name = transformer_name if transformer_name else user.display_name
            
            in_combiner, _ = await self.theme_cog.data_manager.is_user_in_any_combiner(user.id)
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
    
    def __init__(self, message_id: str, guild: discord.Guild, theme_cog: "ThemeSystem"):
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

    def get_current_users(self) -> List[discord.Member]:
        """Get current page of users."""
        start = self.current_page * self.users_per_page
        end = start + self.users_per_page
        return self.cybertronian_users[start:end]

    async def update_buttons_async(self) -> None:
        """Update the view buttons based on current state."""
        self.clear_items()
        
        # Add user selection buttons
        current_users = self.get_current_users()
        for i, user in enumerate(current_users):
            display_name = self._get_display_name(user)
            in_combiner, _ = await self.theme_cog.data_manager.is_user_in_any_combiner(user.id)
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
        return user.display_name

    def create_user_callback(self, user: discord.Member):
        """Create a callback for user selection."""
        async def user_callback(interaction: discord.Interaction):
            # Check if user is already in any combiner team
            in_combiner, existing_message_id = await self.theme_cog.data_manager.is_user_in_any_combiner(user.id)
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
            await self.update_buttons_async()
            await self.update_embed(interaction)

    async def next_page(self, interaction: discord.Interaction):
        """Go to next page."""
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            await self.update_buttons_async()
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
            in_combiner, _ = await self.theme_cog.data_manager.is_user_in_any_combiner(user.id)
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
        
        # Get combiner team data through UserDataManager
        team_data = await theme_cog.data_manager.get_user_theme_data_section(
            self.message_id, "combiner_teams", {"🦿": [], "🦾": [], "🧠": [], "🫀": []}
        )
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
        in_combiner, existing_message_id = await theme_cog.data_manager.is_user_in_any_combiner(user_id)
        if in_combiner:
            await interaction.response.send_message(
                f"{self.user.display_name} is already part of another combiner team!",
                ephemeral=True
            )
            return
        
        # Add user to the position
        team_data[emoji].append(user_id)
        
        # Save team data through optimized DataManager
        await theme_cog.data_manager.save_user_theme_data_section(
            self.message_id, "System", "combiner_teams", team_data
        )
        
        # Update user data with combiner team info using optimized DataManager
        try:
            username = str(self.user)
            user_link = f"https://discord.com/users/{user_id}"
            part_name = {"🦿": "Legs", "🦾": "Arms", "🧠": "Head", "🫀": "Body"}[emoji]
            
            # Add user to combiner team in user data
            await theme_cog.data_manager.user_data_manager.add_user_to_combiner_team(
                user_id, self.message_id, username, user_link, part_name
            )
            
        except Exception as e:
            logger.error(f"Error updating user data for combiner team: {e}")
        
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
            await self.parent_view.update_buttons_async()

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
            view = QuestionView(1, interaction.user.id)
            embed = view.create_embed()
            await interaction.response.send_message(
                embed=embed,
                view=view,
                ephemeral=True
            )
        except Exception as e:
            logger.exception(f"Error starting analysis: {e}")
            await interaction.response.send_message(
                f"An error occurred: {str(e)}", 
                ephemeral=True
            )

class QuestionView(ui.View):
    """View that presents questions with button answers"""
    
    def __init__(self, question_number: int, user_id: int):
        super().__init__(timeout=300)
        self.question_number = question_number
        self.user_id = user_id
        self.questions = {
            1: {
                "question": "How often do you log in?",
                "options": ["All day", "Daily", "2-3 times a week", "Weekly", "Less than weekly"]
            },
            2: {
                "question": "How many cities do you have?",
                "options": ["1-11", "12-19", "20-25", "25-30+"]
            },
            3: {
                "question": "What's your approach to war?",
                "options": ["I'll solo ANYONE!", "I'll be 1st wave", "I'll be 2nd wave", "Moral Support Only", "I'll Delete if Attacked"]
            },
            4: {
                "question": "What's your top priority or main objective?",
                "options": ["Revenue", "Resources", "Peace", "Raiding", "DESTRUCTION!"]
            },
            5: {
                "question": "How do you feel about Infrastructure?",
                "options": ["Infra? What's that?", "Little as possible", "Some is ok", "I love infra"]
            }
        }
        
        # Add answer buttons
        question_data = self.questions[question_number]
        for i, option in enumerate(question_data["options"]):
            self.add_item(AnswerButton(option, i, question_number))
    
    def create_embed(self):
        """Create the question embed"""
        question_data = self.questions[self.question_number]
        embed = discord.Embed(
            title=f"🤖 Allspark Analysis - Question {self.question_number}/5",
            description=f"**{question_data['question']}**",
            color=0x00ff00
        )
        embed.set_footer(text=f"Progress: {self.question_number}/5 questions")
        return embed

class AnswerButton(ui.Button):
    """Button for answering a question"""
    
    def __init__(self, label: str, position: int, question_number: int):
        super().__init__(
            label=label,
            style=discord.ButtonStyle.secondary,
            custom_id=f"answer_{question_number}_{position}"
        )
        self.answer = label.lower()
        self.question_number = question_number
    
    async def callback(self, interaction: discord.Interaction):
        try:
            # Store answer
            user_data = interaction.client.user_data.setdefault(interaction.user.id, {})
            question_key = {
                1: "log_in_frequency",
                2: "city_count", 
                3: "war_approach",
                4: "priority",
                5: "infrastructure"
            }[self.question_number]
            user_data[question_key] = self.answer
            
            # Move to next question or finish
            if self.question_number < 5:
                view = QuestionView(self.question_number + 1, interaction.user.id)
                embed = view.create_embed()
                await interaction.response.edit_message(embed=embed, view=view)
            else:
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
            logger.exception(f"Error in AnswerButton: {e}")
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
            
            embed = discord.Embed(
                title="🎉 Analysis Complete! 🎉",
                description=(
                    f"**Your Class:** {user_class}\n\n"
                    f"**Your Answers:**\n{answers_text}\n\n"
                    f"**Role assigned!** You now have the {user_class} role."
                ),
                color=0x00ff00
            )
            
            await interaction.response.edit_message(embed=embed, view=None)
            
        except Exception as e:
            logger.exception(f"Error showing user results: {e}")

class ThemeSystem(commands.Cog):
    """Discord bot commands for theme system."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data_manager = DataManager(bot)
        self.name_generator = NameGenerator()
        self.role_checker = RoleChecker()
        self.combiner_manager = CombinerManager(self.data_manager)

    @app_commands.command(name="spark", description="Become a Transformer! Pick your Autobot or Decepticon class.")
    @app_commands.describe(
        autobot_class="Choose your Autobot class (pick ONE from this OR Decepticon list)",
        decepticon_class="Choose your Decepticon class (pick ONE from this OR Autobot list)"
    )
    @app_commands.choices(
        autobot_class=[
            app_commands.Choice(name="🔴🤺 Autobot Warrior - ATT:5 DEF:5 DEX:2 INT:1 CHA:2 HP:135", value="warrior"),
            app_commands.Choice(name="🔴🔬 Autobot Scientist - ATT:1 DEF:2 DEX:2 INT:5 CHA:5 HP:110", value="scientist"),
            app_commands.Choice(name="🔴🧰 Autobot Engineer - ATT:1 DEF:5 DEX:1 INT:5 CHA:3 HP:125", value="engineer"),
            app_commands.Choice(name="🔴🛟 Autobot Mariner - ATT:5 DEF:5 DEX:2 INT:1 CHA:2 HP:130", value="mariner"),
            app_commands.Choice(name="🔴🦸 Autobot Commander - ATT:2 DEF:1 DEX:1 INT:5 CHA:5 HP:120", value="commander"),
            app_commands.Choice(name="🔴⛑️ Autobot Medic - ATT:1 DEF:2 DEX:1 INT:5 CHA:5 HP:115", value="medic"),
            app_commands.Choice(name="🔴🔭 Autobot Scout - ATT:2 DEF:2 DEX:5 INT:1 CHA:5 HP:110", value="scout"),
            app_commands.Choice(name="🔴🧭 Autobot Seeker - ATT:5 DEF:1 DEX:5 INT:2 CHA:2 HP:125", value="seeker")
        ],
        decepticon_class=[
            app_commands.Choice(name="🟣🤺 Decepticon Warrior - ATT:5 DEF:5 DEX:3 INT:1 CHA:1 HP:140", value="warrior"),
            app_commands.Choice(name="🟣🔬 Decepticon Scientist - ATT:1 DEF:2 DEX:2 INT:5 CHA:5 HP:100", value="scientist"),
            app_commands.Choice(name="🟣🧰 Decepticon Engineer - ATT:3 DEF:5 DEX:1 INT:5 CHA:1 HP:125", value="engineer"),
            app_commands.Choice(name="🟣🛟 Decepticon Mariner - ATT:5 DEF:2 DEX:5 INT:1 CHA:2 HP:130", value="mariner"),
            app_commands.Choice(name="🟣🦹 Decepticon Commander - ATT:5 DEF:1 DEX:2 INT:5 CHA:2 HP:115", value="commander"),
            app_commands.Choice(name="🟣⛑️ Decepticon Medic - ATT:1 DEF:1 DEX:2 INT:5 CHA:6 HP:105", value="medic"),
            app_commands.Choice(name="🟣🔭 Decepticon Scout - ATT:3 DEF:1 DEX:5 CHA:5 INT:1 HP:110", value="scout"),
            app_commands.Choice(name="🟣🧭 Decepticon Seeker - ATT:5 DEF:1 DEX:5 INT:2 CHA:1 HP:120", value="seeker")
        ]
    )
    async def spark(self, interaction: discord.Interaction, autobot_class: str = None, decepticon_class: str = None):
        """Assigns a new Transformer identity to the user."""
        # Check for Cybertronian role
        if not self.role_checker.has_cybertronian_role(interaction.user):
            await interaction.response.send_message(
                "❌ Only Cybertronian Citizens can be assigned a Transformer identity! "
                "Please get a Cybertronian role first."
            )
            return
        
        # Determine faction and class based on which parameter was provided
        if autobot_class and not decepticon_class:
            faction = "autobot"
            class_choice = autobot_class
        elif decepticon_class and not autobot_class:
            faction = "decepticon"
            class_choice = decepticon_class
        else:
            await interaction.response.send_message(
                "❌ Please choose either an Autobot class OR a Decepticon class, not both."
            )
            return
        
        # Generate transformer name
        new_name = self.name_generator.generate_transformer_name(faction, class_choice)
        
        # Save the transformer data using optimized DataManager
        user_id = str(interaction.user.id)
        theme_data = await self.data_manager.get_user_theme_data(user_id)
        theme_data["transformer"] = {
            "name": new_name,
            "faction": faction,
            "class": class_choice,
            "created_at": time.time()
        }
        await self.data_manager.save_user_theme_data(user_id, interaction.user.display_name, theme_data)
        
        # Create character in RPG system
        spark_data = {
            'name': new_name,
            'faction': faction,
            'class': class_choice
        }
        success = await create_character_from_spark(user_id, spark_data)
        if not success:
            await interaction.response.send_message("❌ Failed to create RPG character!", ephemeral=True)
            return
        
        # Get actual stats from RPG system for display
        from Systems.RPG.rpg_system import RPGSystem
        rpg_system = RPGSystem()
        base_stats = rpg_system.base_stats_config.get(faction.lower(), {}).get(class_choice.lower())
        
        if base_stats:
            stats_display = f"**Stats:** ATT:{base_stats.ATT} DEF:{base_stats.DEF} DEX:{base_stats.DEX} INT:{base_stats.INT} CHA:{base_stats.CHA} HP:{base_stats.HP}"
        else:
            stats_display = "**Stats:** Ready for battle!"
        
        public_message = (
            f"**{interaction.user.mention}** has been mutated by the AllSpark! "
            f"Your Transformer identity is **{new_name}**, a {faction.capitalize()} {class_choice.capitalize()}!\n"
            f"{stats_display}\n"
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
        view = CombinerView(None, ctx.guild, self)
        message = await ctx.send(embed=embed, view=view)
        
        # Update the view with the actual message ID
        view.message_id = str(message.id)
        
        # Initialize combiner data using UserDataManager
        message_id = str(message.id)
        # Team data will be managed through individual user files via UserDataManager
        # No legacy initialization needed
        
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
        """Handle combiner team reactions using optimized DataManager."""
        if not self.role_checker.has_cybertronian_role(user):
            return
        
        message_id = str(reaction.message.id)
        user_id = str(user.id)
        username = user.display_name
        
        # Check if user is already in any combiner team (including this one)
        in_combiner, existing_message_id = await self.data_manager.is_user_in_any_combiner(user_id)
        
        if adding and in_combiner and existing_message_id != message_id:
            # User is trying to join a different combiner team
            try:
                await reaction.remove(user)
            except:
                pass
            return
        
        # Get current team data
        team_data = await self.data_manager.get_user_theme_data_section(message_id, "combiner_teams", {})
        if not team_data:
            # Initialize team data if doesn't exist
            team_data = {"🦿": [], "🦾": [], "🧠": [], "🫀": []}
        
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
                    
                    # Update user data with new team assignment using optimized DataManager
                    part_name = {"🦿": "Legs", "🦾": "Arms", "🧠": "Head", "🫀": "Body"}[emoji]
                    await self.data_manager.user_data_manager.add_user_to_combiner_team(
                        user_id, message_id, username, f"https://discord.com/users/{user_id}", part_name
                    )
            else:
                # Remove user from this position
                if user_id in team_data[emoji]:
                    team_data[emoji].remove(user_id)
                    
                    # Update user data to remove team assignment using optimized DataManager
                    await self.data_manager.user_data_manager.remove_user_from_combiner_team(
                        user_id, username
                    )
            
            # Save the updated team data
            await self.data_manager.save_user_theme_data_section(message_id, "System", "combiner_teams", team_data)
            
            # Update the embed
            await self._update_combiner_embed(reaction.message, message_id, team_data)



    async def _update_combiner_embed(self, message: discord.Message, message_id: str, team_data=None):
        """Update the combiner embed with current team composition."""
        if team_data is None:
            team_data = await self.data_manager.get_user_theme_data_section(message_id, "combiner_teams", {})
            if not team_data:
                team_data = {"🦿": [], "🦾": [], "🧠": [], "🫀": []}
        
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
                            user_data = await self.data_manager.get_user_theme_data(user_id)
                            transformer_name = user_data.get("transformer_name", user.display_name)
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
            
            # Save the combiner name through optimized DataManager
            await self.data_manager.save_user_theme_data_section(
                message_id, "System", "combiner_name", {
                    'name': combiner_name,
                    'members': all_members,
                    'timestamp': time.time()
                }
            )
            
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

    @app_commands.command(name="analysis", description="Start an Allspark Analysis")
    async def analysis(self, interaction: discord.Interaction):
        """Start an Allspark Analysis via slash command"""
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
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            logger.exception(f"Error in analysis slash command: {e}")
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    """Initialize the theme system with the bot instance."""
    await bot.add_cog(ThemeSystem(bot))

__all__ = [
    'ThemeSystem',
    'NameGenerator',
    'RoleChecker',
    'DataManager',
    'CombinerManager',
    'ThemeConfig',
    'ProfileView',
    'AnalysisView',
    'StartAnalysisButton',
    'QuestionView',
    'AnswerButton'
]