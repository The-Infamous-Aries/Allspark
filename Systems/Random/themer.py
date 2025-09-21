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
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from user_data_manager import OptimizedUserDataManager

logger = logging.getLogger("allspark.theme_system")

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

    # Combiner name generation data
    COMBINER_PREFIXES = [
        "Ultra", "Super", "Mega", "Giga", "Tera", "Omega", "Alpha", "Beta", "Gamma", "Delta",
        "Epsilon", "Zeta", "Eta", "Theta", "Iota", "Kappa", "Lambda", "Mu", "Nu", "Xi",
        "Omicron", "Pi", "Rho", "Sigma", "Tau", "Upsilon", "Phi", "Chi", "Psi", "Omega",
        "Prime", "Matrix", "Vector", "Nexus", "Apex", "Vertex", "Summit", "Peak", "Zenith",
        "Pinnacle", "Acme", "Crown", "Crest", "Ridge", "Edge", "Blade", "Point", "Tip",
        "Spike", "Thorn", "Barb", "Hook", "Claw", "Talon", "Fang", "Tooth", "Bite",
        "Quantum", "Cosmic", "Stellar", "Solar", "Lunar", "Galactic", "Nebula", "Quasar",
        "Pulsar", "Nova", "Meteor", "Comet", "Asteroid", "Planet", "Star", "Void",
        "Chrono", "Temporal", "Eternal", "Infinite", "Absolute", "Supreme", "Ultimate",
        "Final", "Perfect", "Complete", "Total", "Maximum", "Extreme", "Intense",
        "Vicious", "Brutal", "Savage", "Fierce", "Wild", "Raging", "Storm", "Thunder",
        "Lightning", "Electric", "Plasma", "Laser", "Photon", "Neutron", "Proton",
        "Electron", "Atomic", "Nuclear", "Radiation", "Gamma", "X-Ray", "Microwave",
        "Radar", "Sonar", "Infra", "Ultra", "Hyper", "Superior", "Inferior", "Greater",
        "Lesser", "Minor", "Major", "Senior", "Junior", "Ancient", "Elder", "Prime",
        "First", "Last", "Final", "End", "Beginning", "Origin", "Source", "Core",
        "Center", "Middle", "Balance", "Harmony", "Chaos", "Order", "Discord", "Peace",
        "War", "Battle", "Combat", "Fight", "Struggle", "Conflict", "Crisis", "Doom",
        "Destiny", "Fate", "Fortune", "Luck", "Chance", "Risk", "Gamble", "Bet",
        "Wager", "Stake", "Prize", "Reward", "Treasure", "Wealth", "Rich", "Poor",
        "Gold", "Silver", "Bronze", "Iron", "Steel", "Metal", "Alloy", "Crystal",
        "Gem", "Jewel", "Diamond", "Ruby", "Emerald", "Sapphire", "Topaz", "Opal",
        "Pearl", "Jade", "Obsidian", "Quartz", "Feldspar", "Mica", "Granite", "Marble",
        "Stone", "Rock", "Boulder", "Mountain", "Hill", "Valley", "Canyon", "Cliff",
        "Crag", "Peak", "Summit", "Ridge", "Range", "Chain", "Series", "Sequence",
        "Pattern", "Design", "Style", "Form", "Shape", "Structure", "Build", "Make",
        "Create", "Destroy", "Build", "Break", "Fix", "Repair", "Mend", "Heal",
        "Hurt", "Harm", "Damage", "Wound", "Scar", "Mark", "Brand", "Label", "Tag",
        "Name", "Title", "Rank", "Grade", "Level", "Tier", "Class", "Type", "Kind",
        "Sort", "Category", "Group", "Team", "Squad", "Unit", "Force", "Army",
        "Navy", "Air", "Space", "Land", "Sea", "Ocean", "River", "Lake", "Pond",
        "Stream", "Creek", "Brook", "Spring", "Well", "Fountain", "Water", "Aqua",
        "Hydro", "Fluid", "Liquid", "Gas", "Vapor", "Steam", "Mist", "Fog", "Cloud",
        "Sky", "Heaven", "Hell", "Underworld", "Nether", "Abyss", "Void", "Space",
        "Time", "Dimension", "Reality", "Dream", "Nightmare", "Illusion", "Fantasy",
        "Reality", "Truth", "Lie", "Deception", "Trick", "Trap", "Snare", "Net",
        "Web", "Thread", "String", "Rope", "Chain", "Link", "Bond", "Tie", "Connect",
        "Join", "Merge", "Combine", "Unite", "Together", "Apart", "Separate", "Divide",
        "Split", "Break", "Crack", "Shatter", "Smash", "Crush", "Squash", "Flatten",
        "Compress", "Press", "Squeeze", "Pinch", "Grip", "Hold", "Grab", "Catch",
        "Throw", "Toss", "Launch", "Fire", "Shoot", "Blast", "Explode", "Detonate",
        "Boom", "Bang", "Pop", "Snap", "Crackle", "Sizzle", "Hiss", "Buzz", "Hum",
        "Whirr", "Click", "Clack", "Clank", "Clink", "Clang", "Crash", "Smash",
        "Bang", "Boom", "Roar", "Scream", "Shout", "Yell", "Cry", "Weep", "Sob",
        "Laugh", "Giggle", "Chuckle", "Snicker", "Grin", "Smile", "Frown", "Scowl",
        "Glare", "Stare", "Look", "See", "Watch", "Observe", "Notice", "Spot",
        "Find", "Discover", "Uncover", "Reveal", "Hide", "Conceal", "Cover", "Mask",
        "Disguise", "Costume", "Outfit", "Suit", "Armor", "Shield", "Guard", "Protect",
        "Defend", "Attack", "Strike", "Hit", "Punch", "Kick", "Slap", "Smack",
        "Whack", "Bash", "Thump", "Bump", "Crash", "Collide", "Impact", "Ram",
        "Charge", "Rush", "Dash", "Sprint", "Run", "Jog", "Walk", "Stroll", "Wander",
        "Roam", "Explore", "Adventure", "Journey", "Trip", "Travel", "Move", "Go",
        "Stop", "Halt", "Freeze", "Still", "Motion", "Action", "Active", "Idle",
        "Lazy", "Slow", "Fast", "Quick", "Swift", "Rapid", "Speed", "Velocity",
        "Acceleration", "Momentum", "Force", "Power", "Strength", "Might", "Muscle",
        "Brawn", "Bulk", "Size", "Mass", "Weight", "Heavy", "Light", "Dark", "Bright",
        "Shine", "Glow", "Glitter", "Sparkle", "Twinkle", "Flash", "Glare", "Gleam"
    ]
    
    COMBINER_SUFFIXES = [
        "tron", "con", "bot", "droid", "mech", "borg", "prime", "max", "ultra", "super",
        "mega", "giga", "tera", "omega", "alpha", "beta", "gamma", "delta", "epsilon",
        "zeta", "eta", "theta", "iota", "kappa", "lambda", "mu", "nu", "xi", "omicron",
        "pi", "rho", "sigma", "tau", "upsilon", "phi", "chi", "psi", "matrix", "vector",
        "nexus", "apex", "vertex", "summit", "peak", "zenith", "pinnacle", "acme", "crown",
        "crest", "ridge", "edge", "blade", "point", "tip", "spike", "thorn", "barb",
        "zor", "xar", "vox", "nox", "lux", "flux", "crux", "trux", "drux", "phlux",
        "morph", "form", "mode", "state", "phase", "stage", "level", "tier", "grade",
        "class", "type", "kind", "sort", "style", "design", "model", "version", "edition",
        "series", "line", "brand", "mark", "stamp", "seal", "sigil", "rune", "glyph",
        "symbol", "sign", "token", "badge", "emblem", "icon", "logo", "label", "tag",
        "code", "key", "lock", "gate", "door", "portal", "window", "mirror", "screen",
        "display", "monitor", "panel", "board", "plate", "sheet", "layer", "coat", "cover",
        "shell", "case", "box", "crate", "container", "vessel", "ship", "craft", "vehicle",
        "transport", "carrier", "bearer", "holder", "keeper", "guardian", "warden", "jailer",
        "prisoner", "captive", "slave", "servant", "worker", "laborer", "miner", "digger",
        "driller", "borer", "piercer", "stabber", "slasher", "cutter", "slicer", "dicer",
        "chopper", "hacker", "slayer", "killer", "destroyer", "wrecker", "ruiner", "damager",
        "breaker", "crusher", "smasher", "basher", "thrasher", "trasher", "crasher", "smasher",
        "basher", "thrasher", "trasher", "crasher", "slicer", "dicer", "chopper", "hacker",
        "slayer", "killer", "destroyer", "wrecker", "ruiner", "damager", "breaker", "crusher",
        "mancer", "master", "lord", "king", "queen", "prince", "princess", "duke", "duchess",
        "earl", "count", "countess", "baron", "baroness", "knight", "sir", "dame", "lady",
        "lord", "master", "mancer", "wright", "smith", "maker", "builder", "creator", "forger",
        "caster", "thrower", "slinger", "hurler", "pitcher", "tosser", "launcher", "firing",
        "blaster", "shooter", "gunner", "sniper", "archer", "bowman", "crossbow", "catapult",
        "trebuchet", "ballista", "cannon", "mortar", "howitzer", "artillery", "battery", "arsenal",
        "armory", "depot", "storage", "warehouse", "silo", "bunker", "fortress", "citadel",
        "castle", "palace", "temple", "shrine", "altar", "sanctuary", "haven", "refuge",
        "shelter", "cover", "hideout", "lair", "den", "nest", "hive", "colony", "settlement",
        "village", "town", "city", "metropolis", "megalopolis", "megacity", "megatown", "megaville",
        "ville", "burg", "borough", "district", "zone", "region", "area", "sector", "quarter",
        "division", "section", "part", "piece", "bit", "chunk", "block", "brick", "stone",
        "rock", "pebble", "grain", "speck", "dot", "point", "spot", "mark", "stain", "smudge",
        "smear", "streak", "stripe", "band", "strip", "ribbon", "tape", "cord", "rope", "string",
        "thread", "yarn", "fiber", "strand", "line", "wire", "cable", "chain", "link", "ring",
        "circle", "loop", "cycle", "ring", "band", "hoop", "wheel", "gear", "cog", "sprocket",
        "pulley", "lever", "handle", "grip", "grasp", "clutch", "grab", "snatch", "seize",
        "take", "steal", "rob", "plunder", "loot", "pillage", "raid", "attack", "assault",
        "strike", "hit", "blow", "punch", "kick", "slap", "smack", "whack", "bash", "thump",
        "bump", "crash", "smash", "crush", "squash", "flatten", "compress", "squeeze", "press",
        "pinch", "nip", "bite", "snap", "crack", "pop", "bang", "boom", "blast", "explosion",
        "detonation", "eruption", "outburst", "burst", "break", "shatter", "fragment", "shred",
        "tear", "rip", "rend", "split", "crack", "fracture", "rupture", "burst", "explode",
        "implode", "collapse", "fall", "drop", "plummet", "dive", "sink", "submerge", "drown",
        "float", "drift", "glide", "soar", "fly", "hover", "levitate", "rise", "ascend",
        "climb", "scale", "mount", "board", "enter", "exit", "leave", "depart", "arrive",
        "come", "go", "move", "travel", "journey", "voyage", "trip", "trek", "hike", "march",
        "parade", "procession", "line", "queue", "row", "column", "file", "rank", "formation",
        "array", "arrangement", "layout", "design", "pattern", "structure", "framework",
        "skeleton", "frame", "shell", "husk", "skin", "coat", "layer", "cover", "lid", "top",
        "bottom", "base", "foundation", "ground", "floor", "roof", "ceiling", "wall", "barrier",
        "fence", "gate", "door", "window", "opening", "hole", "gap", "space", "void", "emptiness",
        "nothing", "zero", "null", "void", "abyss", "chasm", "gulf", "gap", "rift", "split",
        "crack", "crevice", "fissure", "fracture", "break", "rupture", "tear", "rip", "hole",
        "cavity", "hollow", "dent", "depression", "pit", "well", "shaft", "tunnel", "cave",
        "cavern", "grotto", "den", "lair", "hideout", "shelter", "refuge", "haven", "sanctuary",
        "temple", "shrine", "altar", "church", "chapel", "cathedral", "monastery", "convent",
        "abbey", "priory", "hermitage", "retreat", "hideaway", "getaway", "escape", "flight",
        "flee", "run", "dash", "rush", "hurry", "hasten", "speed", "race", "compete", "contest",
        "match", "game", "play", "sport", "fun", "joy", "happiness", "pleasure", "delight",
        "bliss", "ecstasy", "euphoria", "elation", "excitement", "thrill", "adventure", "risk",
        "danger", "peril", "hazard", "threat", "menace", "terror", "fear", "dread", "horror",
        "terror", "panic", "alarm", "warning", "alert", "notice", "message", "signal", "sign",
        "symbol", "emblem", "badge", "mark", "stamp", "seal", "brand", "label", "tag", "name",
        "title", "designation", "appellation", "moniker", "nickname", "alias", "pseudonym",
        "anonym", "unknown", "mystery", "secret", "hidden", "concealed", "covered", "masked",
        "disguised", "camouflaged", "blended", "merged", "fused", "joined", "connected", "linked",
        "tied", "bound", "attached", "fastened", "secured", "fixed", "set", "placed", "positioned",
        "located", "situated", "found", "discovered", "uncovered", "revealed", "exposed", "shown",
        "displayed", "presented", "offered", "given", "taken", "received", "accepted", "welcomed",
        "greeted", "met", "encountered", "faced", "confronted", "challenged", "tested", "tried",
        "attempted", "effort", "endeavor", "venture", "undertaking", "project", "task", "job",
        "work", "labor", "toil", "drudgery", "slavery", "servitude", "bondage", "captivity",
        "imprisonment", "confinement", "restriction", "limitation", "boundary", "border", "edge",
        "rim", "brim", "lip", "mouth", "jaw", "chin", "cheek", "face", "head", "skull",
        "brain", "mind", "thought", "idea", "concept", "notion", "belief", "faith", "trust",
        "confidence", "certainty", "doubt", "uncertainty", "confusion", "chaos", "disorder",
        "mess", "muddle", "jumble", "tangle", "knot", "snarl", "web", "net", "trap", "pitfall",
        "obstacle", "barrier", "hurdle", "challenge", "problem", "issue", "matter", "concern",
        "worry", "trouble", "difficulty", "hardship", "struggle", "fight", "battle", "war",
        "conflict", "dispute", "argument", "quarrel", "fight", "clash", "collision", "impact",
        "crash", "accident", "disaster", "catastrophe", "tragedy", "calamity", "misfortune",
        "bad luck", "hardship", "suffering", "pain", "agony", "torment", "torture", "misery",
        "anguish", "distress", "anxiety", "worry", "concern", "care", "responsibility", "duty",
        "obligation", "commitment", "promise", "pledge", "vow", "oath", "swear", "curse",
        "hex", "jinx", "spell", "charm", "enchantment", "magic", "sorcery", "witchcraft",
        "wizardry", "alchemy", "transmutation", "transformation", "change", "conversion",
        "metamorphosis", "evolution", "growth", "development", "progress", "advancement",
        "improvement", "enhancement", "upgrade", "boost", "increase", "gain", "profit", "benefit",
        "advantage", "edge", "lead", "margin", "difference", "contrast", "comparison", "analogy",
        "metaphor", "simile", "symbol", "representation", "depiction", "portrait", "picture",
        "image", "photo", "snapshot", "moment", "instant", "second", "minute", "hour", "time",
        "duration", "period", "era", "age", "epoch", "eon", "eternity", "forever", "always",
        "never", "sometimes", "often", "rarely", "seldom", "occasionally", "frequently",
        "regularly", "constantly", "continuously", "endlessly", "perpetually", "eternally",
        "infinitely", "boundlessly", "limitlessly", "endlessly", "ceaselessly", "unceasingly",
        "relentlessly", "persistently", "determinedly", "stubbornly", "obstinately", "firmly",
        "solidly", "strongly", "powerfully", "forcefully", "violently", "fiercely", "intensely",
        "severely", "extremely", "utterly", "completely", "totally", "absolutely", "definitely",
        "certainly", "surely", "undoubtedly", "unquestionably", "indisputably", "irrefutably",
        "incontrovertibly", "obviously", "clearly", "evidently", "apparently", "seemingly",
        "presumably", "supposedly", "allegedly", "reportedly", "rumored", "claimed", "stated",
        "declared", "announced", "proclaimed", "pronounced", "uttered", "spoken", "said", "told",
        "narrated", "recounted", "described", "explained", "clarified", "elucidated", "revealed",
        "disclosed", "divulged", "confessed", "admitted", "acknowledged", "recognized", "accepted",
        "approved", "endorsed", "supported", "backed", "sponsored", "funded", "financed",
        "paid", "purchased", "bought", "sold", "traded", "exchanged", "swapped", "replaced",
        "substituted", "alternated", "rotated", "cycled", "circulated", "distributed",
        "dispersed", "scattered", "spread", "diffused", "dissipated", "dissolved", "melted",
        "liquefied", "vaporized", "evaporated", "sublimated", "condensed", "precipitated",
        "crystallized", "solidified", "hardened", "softened", "weakened", "strengthened",
        "fortified", "reinforced", "supported", "braced", "buttressed", "shored", "propped",
        "bolstered", "boosted", "enhanced", "improved", "upgraded", "advanced", "progressed",
        "developed", "evolved", "matured", "ripened", "aged", "seasoned", "experienced",
        "skilled", "talented", "gifted", "blessed", "fortunate", "lucky", "favored",
        "privileged", "elite", "select", "exclusive", "rare", "uncommon", "unusual",
        "unique", "singular", "individual", "personal", "private", "secret", "hidden",
        "mysterious", "enigmatic", "puzzling", "confusing", "perplexing", "bewildering",
        "baffling", "stumping", "defying", "resisting", "opposing", "fighting", "battling",
        "struggling", "striving", "endeavoring", "attempting", "trying", "testing",
        "experimenting", "exploring", "investigating", "researching", "studying", "learning",
        "educating", "teaching", "instructing", "training", "coaching", "guiding", "leading",
        "directing", "commanding", "ordering", "instructing", "directing", "guiding",
        "steering", "navigating", "piloting", "flying", "soaring", "gliding", "floating",
        "drifting", "sailing", "cruising", "traveling", "journeying", "voyaging", "trekking",
        "hiking", "marching", "parading", "proceeding", "advancing", "progressing",
        "developing", "evolving", "growing", "expanding", "enlarging", "increasing",
        "gaining", "adding", "accumulating", "collecting", "gathering", "assembling",
        "organizing", "arranging", "ordering", "sorting", "categorizing", "classifying",
        "grouping", "clustering", "bunching", "bundling", "packing", "boxing", "crating",
        "storing", "saving", "preserving", "protecting", "guarding", "defending",
        "shielding", "sheltering", "harboring", "hosting", "accommodating", "housing",
        "dwelling", "residing", "living", "existing", "being", "present", "current",
        "contemporary", "modern", "recent", "new", "fresh", "original", "initial",
        "first", "primary", "principal", "main", "major", "chief", "head", "leader",
        "boss", "chief", "captain", "commander", "general", "admiral", "marshal",
        "officer", "official", "authority", "power", "control", "command", "rule",
        "reign", "govern", "manage", "administer", "regulate", "supervise", "oversee",
        "monitor", "watch", "observe", "witness", "see", "view", "look", "glance",
        "glimpse", "peek", "peep", "spy", "observe", "examine", "inspect", "scrutinize",
        "analyze", "study", "research", "investigate", "explore", "probe", "dig", "delve",
        "search", "seek", "hunt", "pursue", "chase", "follow", "trail", "track", "trace",
        "path", "way", "road", "route", "course", "direction", "bearing", "heading",
        "destination", "goal", "target", "objective", "aim", "purpose", "intent",
        "intention", "plan", "scheme", "plot", "conspiracy", "secret", "mystery",
        "puzzle", "riddle", "enigma", "dilemma", "problem", "trouble", "difficulty",
        "challenge", "obstacle", "barrier", "hurdle", "block", "stop", "halt", "end",
        "finish", "complete", "conclude", "terminate", "cease", "desist", "quit",
        "give up", "surrender", "yield", "submit", "succumb", "capitulate", "relent",
        "accede", "agree", "consent", "assent", "approve", "accept", "embrace",
        "welcome", "greet", "meet", "encounter", "face", "confront", "challenge",
        "defy", "resist", "oppose", "fight", "battle", "struggle", "strive", "try",
        "attempt", "endeavor", "undertake", "begin", "start", "commence", "initiate",
        "launch", "open", "activate", "trigger", "spark", "ignite", "light", "fire",
        "burn", "flame", "blaze", "inferno", "conflagration", "holocaust", "catastrophe",
        "disaster", "tragedy", "calamity", "misfortune", "hardship", "suffering", "pain",
        "agony", "torment", "torture", "misery", "anguish", "distress", "anxiety",
        "worry", "concern", "care", "trouble", "problem", "issue", "matter", "affair",
        "business", "work", "job", "task", "duty", "obligation", "responsibility",
        "commitment", "promise", "pledge", "vow", "oath", "swear", "curse", "hex",
        "jinx", "spell", "charm", "enchantment", "magic", "sorcery", "witchcraft",
        "wizardry", "alchemy", "transmutation", "transformation", "change", "conversion",
        "metamorphosis", "evolution", "growth", "development", "progress", "advancement",
        "improvement", "enhancement", "upgrade", "boost", "increase", "gain", "profit",
        "benefit", "advantage", "edge", "lead", "margin", "difference", "contrast",
        "comparison", "analogy", "metaphor", "simile", "symbol", "representation",
        "depiction", "portrait", "picture", "image", "photo", "snapshot", "moment",
        "instant", "second", "minute", "hour", "time", "duration", "period", "era",
        "age", "epoch", "eon", "eternity", "forever", "always", "never", "sometimes",
        "often", "rarely", "seldom", "occasionally", "frequently", "regularly",
        "constantly", "continuously", "endlessly", "perpetually", "eternally", "infinitely",
        "boundlessly", "limitlessly", "endlessly", "ceaselessly", "unceasingly", "relentlessly",
        "persistently", "determinedly", "stubbornly", "obstinately", "firmly", "solidly",
        "strongly", "powerfully", "forcefully", "violently", "fiercely", "intensely",
        "severely", "extremely", "utterly", "completely", "totally", "absolutely",
        "definitely", "certainly", "surely", "undoubtedly", "unquestionably", "indisputably",
        "irrefutably", "incontrovertibly", "obviously", "clearly", "evidently", "apparently",
        "seemingly", "presumably", "supposedly", "allegedly", "reportedly", "rumored",
        "claimed", "stated", "declared", "announced", "proclaimed", "pronounced", "uttered",
        "spoken", "said", "told", "narrated", "recounted", "described", "explained",
        "clarified", "elucidated", "revealed", "disclosed", "divulged", "confessed",
        "admitted", "acknowledged", "recognized", "accepted", "approved", "endorsed",
        "supported", "backed", "sponsored", "funded", "financed", "paid", "purchased",
        "bought", "sold", "traded", "exchanged", "swapped", "replaced", "substituted",
        "alternated", "rotated", "cycled", "circulated", "distributed", "dispersed",
        "scattered", "spread", "diffused", "dissipated", "dissolved", "melted", "liquefied",
        "vaporized", "evaporated", "sublimated", "condensed", "precipitated", "crystallized",
        "solidified", "hardened", "softened", "weakened", "strengthened", "fortified",
        "reinforced", "supported", "braced", "buttressed", "shored", "propped", "bolstered",
        "boosted", "enhanced", "improved", "upgraded", "advanced", "progressed", "developed",
        "evolved", "matured", "ripened", "aged", "seasoned", "experienced", "skilled",
        "talented", "gifted", "blessed", "fortunate", "lucky", "favored", "privileged",
        "elite", "select", "exclusive", "rare", "uncommon", "unusual", "unique", "singular",
        "individual", "personal", "private", "secret", "hidden", "mysterious", "enigmatic",
        "puzzling", "confusing", "perplexing", "bewildering", "baffling", "stumping",
        "defying", "resisting", "opposing", "fighting", "battling", "struggling", "striving",
        "endeavoring", "attempting", "trying", "testing", "experimenting", "exploring",
        "investigating", "researching", "studying", "learning", "educating", "teaching",
        "instructing", "training", "coaching", "guiding", "leading", "directing", "commanding",
        "ordering", "instructing", "directing", "guiding", "steering", "navigating", "piloting"
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
            team_info = await self.user_data_manager.get_user_pet_combiner_team(str(user_id))
            return bool(team_info), team_info.get("team_id") if team_info else None
        except Exception as e:
            logger.error(f"Error checking combiner team for user {user_id}: {e}")
            return False, None

    async def remove_user_from_all_combiners(self, user_id: str, username: str = None) -> bool:
        """Remove a user from all combiner teams."""
        try:
            return await self.user_data_manager.remove_user_from_pet_combiner_team(
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
        cybertronian_roles = []
        for role_name in ['Autobot', 'Decepticon', 'Maverick', 'Cybertronian_Citizen']:
            role_ids = ROLE_IDS.get(role_name, [])
            if isinstance(role_ids, list):
                cybertronian_roles.extend(role_ids)
            else:
                cybertronian_roles.append(role_ids)
        
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
            return {"🦾": [], "🦿": [], "🦵": [], "🦶": []}

    async def is_team_complete(self, team_id: str) -> bool:
        """Check if a team is complete (has all 4 pets)."""
        team_data = await self.get_team_composition(team_id)
        total_members = sum(len(members) for members in team_data.values())
        return total_members == 4

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
            title="🔮 Summon Pet",
            description=f"Select a user to add to the pet combiner team\nPage 1/{summon_view.max_pages}",
            color=0x9932cc
        )
        
        current_users = summon_view.get_current_users()
        user_list = []
        for user in current_users:
            # Get pet data instead of transformer data
            pet_data = await self.theme_cog.data_manager.user_data_manager.get_pet_data(str(user.id), user.display_name)
            pet_name = pet_data.get("name") if pet_data else None
            display_name = f"{user.display_name} (Pet: {pet_name})" if pet_name else user.display_name
            
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
        
        # Get all members with pets
        for member in guild.members:
            pet_data = self.theme_cog.data_manager.user_data_manager.get_pet_data(str(member.id), member.display_name)
            if pet_data and pet_data.get("name"):
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
        """Get the display name for a user, including pet name if available."""
        user_id = str(user.id)
        
        # Get user's pet data
        pet_data = self.theme_cog.data_manager.user_data_manager.get_pet_data(user_id, user.display_name)
        
        if pet_data and pet_data.get("name"):
            return f"{user.display_name} (Pet: {pet_data['name']})"
        else:
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
            title="🔮 Summon Pet",
            description=f"Select a user to add to the pet combiner team\nPage {self.current_page + 1}/{self.max_pages}",
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

    @discord.ui.button(label="🦾", style=discord.ButtonStyle.primary)
    async def left_arm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "🦾")

    @discord.ui.button(label="🦿", style=discord.ButtonStyle.primary)
    async def right_arm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "🦿")

    @discord.ui.button(label="🦵", style=discord.ButtonStyle.primary)
    async def left_leg_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "🦵")

    @discord.ui.button(label="🦶", style=discord.ButtonStyle.primary)
    async def right_leg_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "🦶")

    async def assign_role(self, interaction: discord.Interaction, emoji: str):
        """Assign a user to a specific role in the combiner team."""
        user_id = str(self.user.id)
        theme_cog = self.parent_view.theme_cog
        
        # Get combiner team data through UserDataManager
        team_data = await theme_cog.data_manager.get_user_theme_data_section(
            self.message_id, "combiner_teams", {"🦾": [], "🦿": [], "🦵": [], "🦶": []}
        )
        limits = {"🦾": 1, "🦿": 1, "🦵": 1, "🦶": 1}
        
        # Check total team size
        total_members = sum(len(team_data[part]) for part in team_data)
        if total_members >= 4:
            await interaction.response.send_message(
                "❌ The pet combiner team is already complete (4/4 pets)!",
                ephemeral=True
            )
            return
        
        # Check if position is full
        if len(team_data[emoji]) >= limits[emoji]:
            part_names = {"🦾": "Left Arm", "🦿": "Right Arm", "🦵": "Left Leg", "🦶": "Right Leg"}
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
            await theme_cog.data_manager.user_data_manager.add_user_to_pet_combiner_team(
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
        
        part_names = {"🦾": "Left Arm", "🦿": "Right Arm", "🦵": "Left Leg", "🦶": "Right Leg"}
        await interaction.response.send_message(
            f"✅ {self.user.display_name} has been assigned to {part_names[emoji]}!",
            ephemeral=True
        )
        
        # Check if team is now complete
        new_total = sum(len(team_data[part]) for part in team_data)
        if new_total == 4 and all(len(team_data[part]) == limits[part] for part in ["🦾", "🦿", "🦵", "🦶"]):
            try:
                await interaction.edit_original_response(
                    content="🎉 **Pet combiner team complete!** The summon interface has been closed.",
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
                    role_ids = ROLE_IDS[user_class]
                    if isinstance(role_ids, list):
                        # Try each role ID until we find one that exists
                        for role_id in role_ids:
                            role = interaction.guild.get_role(role_id)
                            if role:
                                await interaction.user.add_roles(role)
                                break
                    else:
                        # Single role ID (backward compatibility)
                        role = interaction.guild.get_role(role_ids)
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



    @commands.hybrid_command(name="combiner", description="Start forming a Pet Combiner team!")
    async def combiner(self, ctx: commands.Context):
        """Start forming a pet combiner team."""
        embed = discord.Embed(
            title="🤖 Pet Combiner Team Formation",
            description="React to assign your pet! 🦾 = Arms | 🦿 = Legs\n"
                       "Each team needs 4 pets total (2 Arms, 2 Legs).\n\n"
                       "*Note: You can only have one pet in a combiner team at a time.*",
            color=0x00ff00
        )
        
        # Add empty fields for the 2 parts
        part_names = {"🦾": "Arms", "🦿": "Legs"}
        limits = {"🦾": 2, "🦿": 2}
        
        for emoji, name in part_names.items():
            embed.add_field(
                name=f"{emoji} {name} (0/{limits[emoji]})",
                value="*Empty*",
                inline=True
            )
        
        # Create the view with summon button
        view = CombinerView(None, ctx.guild, self)
        message = await ctx.send(embed=embed, view=view)

        view.message_id = str(message.id)

        message_id = str(message.id)

        for emoji in ["🦾", "🦿"]:
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
        """Handle combiner team reactions using optimized DataManager for pets."""
        if not self.role_checker.has_cybertronian_role(user):
            return
        
        message_id = str(reaction.message.id)
        user_id = str(user.id)
        username = user.display_name
        
        # Check if user has a pet
        pet_data = await self.data_manager.user_data_manager.get_pet_data(user_id, username)
        if not pet_data:
            try:
                await reaction.remove(user)
            except:
                pass
            await user.send("You need a pet to join a combiner team! Use `/adopt_pet` to get one.")
            return
        
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
            # Initialize team data if doesn't exist - only 2 positions now
            team_data = {"🦾": [], "🦿": []}
        
        emoji = str(reaction.emoji)
        
        # Define limits for the 2 parts (2 pets each for total of 4)
        limits = {"🦾": 2, "🦿": 2}
        
        # Map reaction emojis to available positions
        if emoji == "🦾":  # Arms reaction
            if adding and len(team_data["🦾"]) < limits["🦾"]:
                # Remove user from all other positions in THIS team first
                for part in team_data:
                    if user_id in team_data[part]:
                        team_data[part].remove(user_id)
                
                team_data["🦾"].append(user_id)
                
                # Update user data with new team assignment
                await self.data_manager.user_data_manager.add_user_to_pet_combiner_team(
                    user_id, message_id, username, "Arms"
                )
                
                # Send confirmation
                await user.send(f"Your pet has been assigned as **Arms** in the combiner team!")
                
            elif not adding:
                # Remove user from arms position
                if user_id in team_data["🦾"]:
                    team_data["🦾"].remove(user_id)
                    await self.data_manager.user_data_manager.remove_user_from_pet_combiner_team(
                        user_id, username
                    )
                        
        elif emoji == "🦿":  # Legs reaction
            if adding and len(team_data["🦿"]) < limits["🦿"]:
                # Remove user from all other positions in THIS team first
                for part in team_data:
                    if user_id in team_data[part]:
                        team_data[part].remove(user_id)
                
                team_data["🦿"].append(user_id)
                
                # Update user data with new team assignment
                await self.data_manager.user_data_manager.add_user_to_pet_combiner_team(
                    user_id, message_id, username, "Legs"
                )
                
                # Send confirmation
                await user.send(f"Your pet has been assigned as **Legs** in the combiner team!")
                
            elif not adding:
                # Remove user from legs position
                if user_id in team_data["🦿"]:
                    team_data["🦿"].remove(user_id)
                    await self.data_manager.user_data_manager.remove_user_from_pet_combiner_team(
                        user_id, username
                    )
            
            # Save the updated team data
            await self.data_manager.save_user_theme_data_section(message_id, "System", "combiner_teams", team_data)
            
            # Update the embed
            await self._update_combiner_embed(reaction.message, message_id, team_data)



    async def _update_combiner_embed(self, message: discord.Message, message_id: str, team_data=None):
        """Update the combiner embed with current pet team composition."""
        if team_data is None:
            team_data = await self.data_manager.get_user_theme_data_section(message_id, "combiner_teams", {})
            if not team_data:
                team_data = {"🦾": [], "🦿": []}
        
        embed = discord.Embed(
            title="🤖 Pet Combiner Team Formation",
            description="React to assign your pet! 🦾 = Arms | 🦿 = Legs\nEach team needs 4 pets total (2 Arms, 2 Legs).",
            color=0x00ff00
        )
        
        # Add fields for the 2 parts (2 pets each)
        part_names = {"🦾": "Arms", "🦿": "Legs"}
        limits = {"🦾": 2, "🦿": 2}
        
        for emoji, name in part_names.items():
            members = team_data[emoji]
            if members:
                member_names = []
                for user_id in members:
                    try:
                        user = self.bot.get_user(int(user_id))
                        if user:
                            # Use pet data instead of transformer data
                            pet_data = await self.data_manager.user_data_manager.get_pet_data(user_id, user.display_name)
                            pet_name = pet_data.get("name", user.display_name) if pet_data else user.display_name
                            member_names.append(f"{pet_name} ({user.display_name})")
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
        
        # Check if team is complete (4 members total - 2 per position)
        total_members = sum(len(team_data[part]) for part in team_data)
        if total_members == 4 and all(len(team_data[part]) == limits[part] for part in ["🦾", "🦿"]):
            # Generate combiner name
            all_members = []
            for part in team_data:
                all_members.extend(team_data[part])
            
            combiner_name = self.name_generator.generate_combiner_name(all_members)
            
            embed.color = 0x00ff00
            embed.add_field(
                name="✅ Team Status",
                value=f"**PET COMBINER TEAM COMPLETE!** 🎉\n**Combined Form: {combiner_name}**",
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
                value=f"**{total_members}/4 pets assigned**",
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