import discord
from discord.ext import commands
from discord import app_commands, ui, ButtonStyle, Embed, File
import random
import logging
from typing import Dict, List, Any, Tuple, Optional
import math
import json
import os
from io import BytesIO
import asyncio
from datetime import datetime

try:
    from PIL import Image, ImageDraw, ImageFont, ImageChops
    PIL_AVAILABLE = True
except Exception:
    Image = None
    ImageDraw = None
    ImageFont = None
    ImageChops = None
    PIL_AVAILABLE = False

logger = logging.getLogger("allspark.cybertron_games")
DISCORD_CHAR_LIMIT = 2000

# Data paths (relative to Systems directory)
_SYSTEMS_DIR = os.path.dirname(os.path.dirname(__file__))
_DATA_DIR = os.path.join(_SYSTEMS_DIR, 'Data', 'Hunger Games')
_ACTIONS_PATH = os.path.join(_DATA_DIR, 'actions.json')
_ELIMS_PATH = os.path.join(_DATA_DIR, 'eliminations.json')
_VEHICLE_PATH = os.path.join(_DATA_DIR, 'vehicle.json')
_LOCATION_PATH = os.path.join(_DATA_DIR, 'location.json')


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


class DataPools:
    def __init__(self):
        self.actions_by_style: Dict[str, List[str]] = {}
        self.elims_by_style: Dict[str, List[str]] = {}
        self.vehicles: Dict[str, List[Any]] = {}
        self.locations: Dict[str, List[str]] = {}

    def reload(self):
        actions = _load_json(_ACTIONS_PATH)
        eliminations = _load_json(_ELIMS_PATH)
        vehicles = _load_json(_VEHICLE_PATH)
        locations = _load_json(_LOCATION_PATH)

        # Extract entries from the new format
        self.actions_by_style = {}
        self.elims_by_style = {}
        
        # Process actions
        if 'entries' in actions:
            for entry in actions['entries']:
                style = entry.get('style')
                if not style:
                    continue
                if style not in self.actions_by_style:
                    self.actions_by_style[style] = []
                if 'templates' in entry and isinstance(entry['templates'], list):
                    self.actions_by_style[style].extend(entry['templates'])
                elif 'template' in entry and isinstance(entry['template'], str):
                    self.actions_by_style[style].append(entry['template'])
        
        # Process eliminations
        if 'entries' in eliminations:
            for entry in eliminations['entries']:
                style = entry.get('style')
                if not style:
                    continue
                if style not in self.elims_by_style:
                    self.elims_by_style[style] = []
                if 'templates' in entry and isinstance(entry['templates'], list):
                    self.elims_by_style[style].extend(entry['templates'])
                elif 'template' in entry and isinstance(entry['template'], str):
                    self.elims_by_style[style].append(entry['template'])

        self.vehicles = vehicles
        # Flatten or keep styles for locations; pick randomly across styles at runtime
        self.locations = locations.get('locations', {})

    def _strip_style_prefix(self, style: str, name: str) -> str:
        key = style.replace('_', ' ').lower()
        lower = name.lower()
        if lower.startswith(key + ' '):
            return name[len(key) + 1:]
        return name

    def random_location(self) -> str:
        if not self.locations:
            return "Iacon plaza"
        style = random.choice(list(self.locations.keys()))
        pool = self.locations.get(style, [])
        if not pool:
            return "Iacon plaza"
        name = random.choice(pool)
        return self._strip_style_prefix(style, name)

    def random_location_with_style(self) -> Tuple[str, str]:
        """Return (style_key, location_name). Falls back to generic when empty."""
        if not self.locations:
            return ("urban_grid", "Urban Grid Plaza")
        style = random.choice(list(self.locations.keys()))
        pool = self.locations.get(style, [])
        loc = random.choice(pool) if pool else ("Urban Grid Plaza")
        return (style, self._strip_style_prefix(style, loc))

    def random_location_for_style(self, style: str) -> str:
        pool = self.locations.get(style, [])
        if not pool:
            return "Urban Grid Plaza"
        name = random.choice(pool)
        return self._strip_style_prefix(style, name)

    def random_vehicle_for_a_count(self, a_count: int) -> str:
        key = 'vehicles_1vANY' if a_count == 1 else 'vehicles_2vANY' if a_count == 2 else 'vehicles_3vANY'
        pool = self.vehicles.get(key, [])
        if not pool:
            return "Cybertronian interceptor"
        choice = random.choice(pool)
        if isinstance(choice, dict):
            return choice.get('Name', "Cybertronian interceptor")
        return str(choice)

    def random_combiner_for_a_count(self, a_count: int) -> str:
        key = 'combiners_4' if a_count == 4 else 'combiners_5'
        pool = self.vehicles.get(key, [])
        if not pool:
            return "Steelstorm"
        choice = random.choice(pool)
        if isinstance(choice, dict):
            return choice.get('Name', "Steelstorm")
        return str(choice)

    def random_alt_details_for_count(self, count: int) -> Tuple[str, str, str]:
        if count in (1, 2, 3):
            key = 'vehicles_1vANY' if count == 1 else 'vehicles_2vANY' if count == 2 else 'vehicles_3vANY'
        else:
            key = 'combiners_4' if count == 4 else 'combiners_5'
        pool = self.vehicles.get(key, [])
        if not pool:
            name = "Steelstorm" if count in (4, 5) else "Cybertronian interceptor"
            return (name, "", "")
        entry = random.choice(pool)
        if isinstance(entry, dict):
            name = entry.get('Name', "")
            attacks = entry.get('Attack', [])
            falses = entry.get('FalseAttack', [])
            attack = random.choice(attacks) if attacks else ""
            false = random.choice(falses) if falses else ""
            return (name, attack, false)
        return (str(entry), "", "")

    def random_alt_details_by_type(self, count: int, use_combiner: bool) -> Tuple[str, str, str]:
        if count in (1, 2, 3):
            key = 'vehicles_1vANY' if count == 1 else 'vehicles_2vANY' if count == 2 else 'vehicles_3vANY'
        else:
            if use_combiner:
                key = 'combiners_4' if count == 4 else 'combiners_5'
            else:
                key = 'vehicles_4vANY' if count == 4 else 'vehicles_5vANY'
        pool = self.vehicles.get(key, [])
        if not pool:
            name = "Steelstorm" if use_combiner and count in (4, 5) else ("Cybertronian interceptor")
            return (name, "", "")
        entry = random.choice(pool)
        if isinstance(entry, dict):
            name = entry.get('Name', "")
            attacks = entry.get('Attack', [])
            falses = entry.get('FalseAttack', [])
            attack = random.choice(attacks) if attacks else ""
            false = random.choice(falses) if falses else ""
            return (name, attack, false)
        return (str(entry), "", "")


def _format_a_open(names: List[str]) -> str:
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"Team {names[0]} and {names[1]}"
    return f"Team {', '.join(names[:-1])}, and {names[-1]}"

def _fill_template(template: str, style: str, side_a: List[str], side_b: List[str], pools: DataPools) -> str:
    # Participants
    mapping: Dict[str, str] = {}
    for i, name in enumerate(side_a, start=1):
        mapping[f"A{i}"] = name
    for i, name in enumerate(side_b, start=1):
        mapping[f"B{i}"] = name

    mapping['Location'] = pools.random_location()

    a_count = len(side_a)
    if a_count in (1, 2, 3):
        a_name, a_attack, a_false = pools.random_alt_details_by_type(a_count, False)
        mapping['VehicleA'] = a_name
    else:
        use_combiner_a = ('{CombinerA}' in template) and not ('{VehicleA}' in template)
        a_name, a_attack, a_false = pools.random_alt_details_by_type(a_count, use_combiner_a)
        if use_combiner_a:
            mapping['CombinerA'] = a_name
        else:
            mapping['VehicleA'] = a_name
    if a_attack:
        mapping['AttackA'] = a_attack
    if a_false:
        mapping['FalseAttackA'] = a_false

    b_count = len(side_b)
    if b_count in (1, 2, 3):
        b_name, b_attack, b_false = pools.random_alt_details_by_type(b_count, False)
        mapping['VehicleB'] = b_name
    else:
        use_combiner_b = ('{CombinerB}' in template) and not ('{VehicleB}' in template)
        b_name, b_attack, b_false = pools.random_alt_details_by_type(b_count, use_combiner_b)
        if use_combiner_b:
            mapping['CombinerB'] = b_name
        else:
            mapping['VehicleB'] = b_name
    if b_attack:
        mapping['AttackB'] = b_attack
    if b_false:
        mapping['FalseAttackB'] = b_false

    mapping['A_open'] = _format_a_open([mapping[f"A{i}"] for i in range(1, a_count + 1)])

    # Replace placeholders
    result = template
    for key, val in mapping.items():
        result = result.replace(f"{{{key}}}", val)

    # Clean any remaining placeholders like {A4} when not present
    for i in range(1, 6):
        result = result.replace(f"{{A{i}}}", "")
        result = result.replace(f"{{B{i}}}", "")
    for key in [
        'VehicleA','VehicleB','CombinerA','CombinerB',
        'AttackA','AttackB','FalseAttackA','FalseAttackB'
    ]:
        result = result.replace(f"{{{key}}}", "")
    result = result.replace("  ", " ").replace(" ,", ",").strip()
    return result


async def _send_long_message(channel: discord.abc.Messageable, text: str):
    if len(text) <= DISCORD_CHAR_LIMIT:
        await channel.send(text)
        return
    start = 0
    while start < len(text):
        chunk = text[start:start + DISCORD_CHAR_LIMIT]
        await channel.send(chunk)
        start += DISCORD_CHAR_LIMIT


def _fill_template_with_location(
    template: str,
    style: str,
    side_a: List[Any],
    side_b: List[Any],
    pools: DataPools,
    location_name: str
) -> str:
    """Fill the template using a provided location name, maintaining vehicle/combiner selection by style."""
    mapping: Dict[str, str] = {}
    
    for i, participant in enumerate(side_a, start=1):
        if hasattr(participant, 'display_name'):
            mapping[f"A{i}"] = participant.display_name
        else:
            mapping[f"A{i}"] = str(participant)
    
    for i, participant in enumerate(side_b, start=1):
        if hasattr(participant, 'display_name'):
            mapping[f"B{i}"] = participant.display_name
        else:
            mapping[f"B{i}"] = str(participant)

    style_display = style.replace('_', ' ').title()
    mapping['Location'] = f"{location_name} in {style_display}"

    a_count = len(side_a)
    if a_count in (1, 2, 3):
        a_name, a_attack, a_false = pools.random_alt_details_by_type(a_count, False)
        mapping['VehicleA'] = a_name
    else:
        use_combiner_a = ('{CombinerA}' in template) and not ('{VehicleA}' in template)
        a_name, a_attack, a_false = pools.random_alt_details_by_type(a_count, use_combiner_a)
        if use_combiner_a:
            mapping['CombinerA'] = a_name
        else:
            mapping['VehicleA'] = a_name
    if a_attack:
        mapping['AttackA'] = a_attack
    if a_false:
        mapping['FalseAttackA'] = a_false

    b_count = len(side_b)
    if b_count in (1, 2, 3):
        b_name, b_attack, b_false = pools.random_alt_details_by_type(b_count, False)
        mapping['VehicleB'] = b_name
    else:
        use_combiner_b = ('{CombinerB}' in template) and not ('{VehicleB}' in template)
        b_name, b_attack, b_false = pools.random_alt_details_by_type(b_count, use_combiner_b)
        if use_combiner_b:
            mapping['CombinerB'] = b_name
        else:
            mapping['VehicleB'] = b_name
    if b_attack:
        mapping['AttackB'] = b_attack
    if b_false:
        mapping['FalseAttackB'] = b_false

    mapping['A_open'] = _format_a_open([mapping[f"A{i}"] for i in range(1, a_count + 1)])

    result = template
    for key, val in mapping.items():
        result = result.replace(f"{{{key}}}", val)

    for i in range(1, 6):
        result = result.replace(f"{{A{i}}}", "")
        result = result.replace(f"{{B{i}}}", "")
    for key in [
        'VehicleA','VehicleB','CombinerA','CombinerB',
        'AttackA','AttackB','FalseAttackA','FalseAttackB'
    ]:
        result = result.replace(f"{{{key}}}", "")
    result = result.replace("  ", " ").replace(" ,", ",").strip()
    return result


class GameSession:
    def __init__(self, participants: List[Any], pools: DataPools, all_factions: bool = False, starting_factions: bool = False):
        self.participants = participants.copy()
        self.pools = pools
        self.alive = participants.copy()
        self.assignment = {}
        self.locations = {}
        self.elimination_locations = {}
        self.elimination_round = {}
        self.forms = {}
        self.round_index = 0
        self.started = False
        self.all_factions = all_factions
        self.starting_factions = starting_factions
        self.action_log: Dict[str, List[str]] = {}
        self.kill_log: Dict[str, List[Dict[str, Any]]] = {}
        self.round_markers: List[Dict[str, Any]] = []
        self.participant_names = {p: getattr(p, 'display_name', str(p)) for p in participants}
        
        # Faction names and colors
        self.color_palette = {
            'purple': (186, 85, 211),
            'red': (220, 20, 60),
            'orange': (255, 140, 0),
            'yellow': (255, 215, 0),
            'green': (60, 179, 113),
            'blue': (30, 144, 255)
        }

        self.faction_groups = {
            'red': [
                'Autobots', 'Wreckers', 'Elite Guard', 'Red Alert Division', 'Strike Force Omega',
                'Solar Knights', 'Chromia Squad', 'Ion Patrol', 'Forge Masters', 'Prime Vanguard',
                'Ark Sentinels', 'Matrix Guard', 'Alpha Trion Circle', 'Valor Brigade', 'Guardian Unit',
                'Rescue Corps', 'Flamewatch', 'Steel Sentinels', 'Rocket Rangers', 'Nova Wardens'
            ],
            'purple': [
                'Decepticons', 'Seekers', 'Elite Seekers', 'Nullray Corps', 'Fusion Syndicate',
                'Obsidian Circle', 'Phase Sixers', 'Scavengers', 'Nightwatch', 'Renegades',
                'Sky Reavers', 'Shadow Legion', 'Ravage Pack', 'Nova Strike', 'Apex Predators',
                'Annihilators', 'Voidclaw', 'Darkstar Unit', 'Subjugators', 'Ion Raiders'
            ],
            'orange': [
                'Constructicons', 'Combaticons', 'Battlechargers', 'Duocons', 'Triple Changers',
                'Vehicons', 'Forge Titans', 'Smelter Brigade', 'Iron Maulers', 'Copper Guard',
                'Molten Core Unit', 'Hammerfall Team', 'Crucible Squad', 'Alloy Hunters', 'Cinder Legion',
                'Gearbreakers', 'Rust Stalkers', 'Steelstormers', 'Torch Wardens', 'Foundry Rangers'
            ],
            'yellow': [
                'Technobots', 'Protectobots', 'Aerialbots', 'Stunticons', 'Headmasters',
                'Targetmasters', 'Powermasters', 'Micromasters', 'Omnibots', 'Circuit Wardens',
                'Signal Corps', 'Beacon Guard', 'Aurora Unit', 'Lumina Rangers', 'Radiant Squad',
                'Flash Faction', 'Glow Squad', 'Daylight Unit', 'Sunspot Guard', 'Radiance Team'
            ],
            'green': [
                'Dinobots', 'Monsterbots', 'Beastformers', 'Wilderbots', 'Jungle Squad',
                'Forest Rangers', 'Emerald Guard', 'Verdant Unit', 'Nature Force', 'Wild Guard',
                'Thorn Patrol', 'Leaf Brigade', 'Vine Warriors', 'Root Corps', 'Canopy Squad',
                'Moss Faction', 'Grassland Unit', 'Prairie Guard', 'Meadow Team', 'Greenzone Squad'
            ],
            'blue': [
                'Aerialbots', 'Seekers', 'Jet Corps', 'Sky Guard', 'Atmospheric Unit',
                'Cloud Squad', 'Stratosphere Force', 'Navy Wing', 'Cobalt Guard', 'Azure Unit',
                'Ice Brigade', 'Frost Squad', 'Arctic Force', 'Glacier Guard', 'Tundra Team',
                'Oceanic Unit', 'Aqua Squad', 'Marine Force', 'Deep Guard', 'Bluezone Corps'
            ]
        }
    
        # Initialize faction data
        self.faction_names = []
        for names in self.faction_groups.values():
            self.faction_names.extend(names)
        
        self.faction_color_map = {}
        for group, names in self.faction_groups.items():
            col = self.color_palette[group]
            for n in names:
                self.faction_color_map[n] = col
        
        # Map configuration
        self.style_order = [
            'urban_grid', 'foundry_complex', 'rust_dunes',
            'mountain_ridge', 'spire_labyrinth', 'sky_causeways'
        ]
        # Realistic, dark map colors
        self.style_bg_colors = {
            'urban_grid': (100, 20, 20),        # dark red
            'foundry_complex': (110, 55, 10),   # dark orange
            'rust_dunes': (135, 115, 30),       # dark yellow
            'mountain_ridge': (70, 70, 80),     # dark grey
            'spire_labyrinth': (55, 25, 75),    # dark purple
            'sky_causeways': (25, 50, 100)      # dark blue
        }
        self.map_size = (1200, 800)
        self.map_margin = 40
        self.border_inset = 20
        self.style_zones = self._compute_style_zones()
        # PATCHES: ORGANIC shapes
        self.style_patches = self._compute_style_patches()
        self._initialize_factions()
        self._initialize_locations()
    
    def get_faction_emoji(self, participant: str, form: str = 'robot', is_elimination: bool = False) -> str:
        """Get the appropriate emoji for a participant based on faction, form, and context."""
        faction = self.assignment.get(participant, 'Neutral')
        
        # Color mapping for factions
        color_emojis = {
            'purple': {'robot': '🟣', 'vehicle': '🟣', 'combiner': '🟣'},
            'red': {'robot': '🔴', 'vehicle': '🔴', 'combiner': '🔴'},
            'orange': {'robot': '🟠', 'vehicle': '🟠', 'combiner': '🟠'},
            'yellow': {'robot': '🟡', 'vehicle': '🟡', 'combiner': '🟡'},
            'green': {'robot': '🟢', 'vehicle': '🟢', 'combiner': '🟢'},
            'blue': {'robot': '🔵', 'vehicle': '🔵', 'combiner': '🔵'},
            'Neutral': {'robot': '⚪', 'vehicle': '⚪', 'combiner': '⚪'}
        }
        
        # Get faction color
        faction_color = None
        for color, factions in self.faction_groups.items():
            if faction in factions:
                faction_color = color
                break
        
        if not faction_color:
            faction_color = 'Neutral'
        
        # For eliminations, use skull with faction color
        if is_elimination:
            if form == 'vehicle':
                return f"💀{color_emojis[faction_color]['vehicle']}"
            elif form == 'combiner':
                return f"💀{color_emojis[faction_color]['combiner']}"
            else:
                return f"💀{color_emojis[faction_color]['robot']}"
        
        # Return appropriate emoji for form
        return color_emojis[faction_color].get(form, '⚪')
    
    def get_event_emojis(self, side_a: List[str], side_b: List[str], is_elimination: bool = False) -> str:
        if not side_a:
            return ""
        a_is_combiner = any(self.forms.get(p) == 'combiner' for p in side_a)
        b_is_combiner = any(self.forms.get(p) == 'combiner' for p in side_b)
        a_emoji = self._form_count_emoji(len(side_a), a_is_combiner)
        if not side_b:
            return a_emoji
        b_emoji = self._form_count_emoji(len(side_b), b_is_combiner)
        if is_elimination:
            return f"{a_emoji}💀{b_emoji}"
        return f"{a_emoji}{b_emoji}"

    def get_participant_name(self, participant: Any) -> str:
        """Get the display name for a participant, whether it's a Discord user object or string."""
        return self.participant_names.get(participant, str(participant))
    
    def _compute_style_zones(self) -> Dict[str, Tuple[int, int, int, int]]:
        width, height = self.map_size
        margin = self.map_margin
        cx = width // 2
        cy = height // 2
        band = int(min(width, height) * 0.18)
        zones: Dict[str, Tuple[int, int, int, int]] = {}
        zones['urban_grid'] = (margin, margin, cx - band // 2, height - margin)
        zones['foundry_complex'] = (cx + band // 2, margin, width - margin, height - margin)
        zones['mountain_ridge'] = (margin, margin, width - margin, cy - band // 2)
        zones['rust_dunes'] = (margin, cy + band // 2, width - margin, height - margin)
        zones['spire_labyrinth'] = (cx - band // 2, cy - band // 2, cx + band // 2, cy + band // 2)
        zones['sky_causeways'] = (margin, margin, width - margin, height - margin)
        return zones

    def _compute_style_patches(self, seed: Optional[int] = None) -> Dict[str, List[List[Tuple[int, int]]]]:
        w, h = self.map_size
        cx, cy = w // 2, h // 2
        m = self.map_margin
        rng = random.Random(seed) if seed is not None else random
        patches = {}

        # Rust Dunes base
        patches['rust_dunes'] = [self._organic_blob(cx, cy, w * 0.42, h * 0.33, points=28, spread=30, rng=rng)]

        # Foundry Complex: central organic blob
        patches['foundry_complex'] = [self._organic_blob(cx, cy, w * 0.16, h * 0.14, points=20, spread=34, rng=rng)]

        # Urban Grids: scattered many small ovals/polygons near foundry
        urbans = []
        for i in range(20):
            ang = rng.uniform(0, 2 * math.pi)
            rad = rng.uniform(w * 0.09, w * 0.22)
            px = cx + int(rad * math.cos(ang)) + rng.randint(-18, 18)
            py = cy + int(rad * math.sin(ang)) + rng.randint(-10, 10)
            size_w = rng.uniform(w * 0.026, w * 0.036)
            size_h = rng.uniform(h * 0.020, h * 0.032)
            urbans.append(self._organic_blob(px, py, size_w, size_h, points=8, spread=6, rng=rng))
        patches['urban_grid'] = urbans

        # Mountain Ridge: belt of medium blobs in a ring halfway
        mountains = []
        belt_radius = int(min(w, h) * 0.33)
        for i in range(8):
            ang = 2 * math.pi * i / 8 + rng.uniform(-0.2, 0.2)
            mx = cx + int(math.cos(ang) * belt_radius)
            my = cy + int(math.sin(ang) * belt_radius)
            mountains.append(self._organic_blob(mx, my, w*0.13, h*0.10, points=18, spread=16, rng=rng))
        patches['mountain_ridge'] = mountains

        # Spire Labyrinth: ring around each mountain patch
        spires = []
        for poly in mountains:
            mx = sum([p[0] for p in poly])//len(poly)
            my = sum([p[1] for p in poly])//len(poly)
            spires.append(self._organic_blob(mx, my, w*0.18, h*0.13, points=18, spread=22, rng=rng))
        patches['spire_labyrinth'] = spires

        # Sky Causeways: multiple small, organic patches simply in the middle
        sky = []
        for i in range(13):
            ang = rng.uniform(0, 2 * math.pi)
            rad = rng.uniform(w * 0.06, w * 0.19)
            px = cx + int(rad * math.cos(ang)) + rng.randint(-16, 16)
            py = cy + int(rad * math.sin(ang)) + rng.randint(-16, 16)
            size_w = rng.uniform(w * 0.04, w * 0.069)
            size_h = rng.uniform(h * 0.024, h * 0.036)
            sky.append(self._organic_blob(px, py, size_w, size_h, points=8, spread=6, rng=rng))
        patches['sky_causeways'] = sky

        return patches

    def _organic_blob(self, cx, cy, rx, ry, points=10, spread=8, rng=None):
        if rng is None: rng = random
        poly = []
        for i in range(points):
            ang = 2 * math.pi * i / points
            radx = rx + rng.randint(-spread, spread)
            rady = ry + rng.randint(-spread, spread)
            x = int(cx + math.cos(ang) * radx)
            y = int(cy + math.sin(ang) * rady)
            poly.append((x, y))
        return poly

    def _form_count_emoji(self, count: int, is_combiner: bool) -> str:
        if is_combiner:
            if count >= 5:
                return '⚜️'
            return '🔱'
        if count <= 1:
            return '🏍️'
        if count == 2:
            return '🚙'
        if count == 3:
            return '🚛'
        if count == 4:
            return '✈️'
        return '🛸'

    def _random_point_in_style(self, style: str) -> Tuple[int, int]:
        w, h = self.map_size
        m = self.map_margin
        bi = self.border_inset
        cx = w // 2
        cy = h // 2
        specs = self._ring_specs()
        rects = getattr(self, 'style_patches', {}).get(style)
        if rects:
            rx0, ry0, rx1, ry1 = random.choice(rects)
            px = random.randint(rx0 + 12, max(rx0 + 13, rx1 - 12))
            py = random.randint(ry0 + 12, max(ry0 + 13, ry1 - 12))
            return (px, py)
        if style in specs:
            r0, r1 = specs[style]
            ang = random.random() * 2 * math.pi
            r = random.randint(max(r0, 6), max(r0 + 1, r1))
            x = int(cx + r * math.cos(ang))
            y = int(cy + r * math.sin(ang))
            x = max(m + bi, min(x, w - m - bi))
            y = max(m + bi, min(y, h - m - bi))
            return (x, y)
        if style == 'sky_causeways':
            angles = [0, math.pi/2, math.pi, 3*math.pi/2, math.pi/4, 3*math.pi/4, 5*math.pi/4, 7*math.pi/4]
            ang = random.choice(angles)
            r_max = int(min(w, h) // 2 - m)
            r = random.randint(20, r_max)
            x = int(cx + r * math.cos(ang))
            y = int(cy + r * math.sin(ang))
            x = max(m + bi, min(x, w - m - bi))
            y = max(m + bi, min(y, h - m - bi))
            return (x, y)
        x0, y0, x1, y1 = self.style_zones.get(style, (m, m, w - m, h - m))
        px = random.randint(x0 + 20 + bi, max(x0 + 21, x1 - 20 - bi))
        py = random.randint(y0 + 20 + bi, max(y0 + 21, y1 - 20 - bi))
        return (px, py)

    def _random_point_free(self) -> Tuple[int, int]:
        w, h = self.map_size
        m = self.map_margin
        bi = self.border_inset
        return (
            random.randint(m + bi, w - m - bi),
            random.randint(m + bi, h - m - bi)
        )

    def _scatter_around(self, center: Tuple[int, int]) -> Tuple[int, int]:
        w, h = self.map_size
        m = self.map_margin
        bi = self.border_inset
        cx, cy = center
        r = random.randint(8, 60)
        ang = random.random() * 2 * math.pi
        x = int(cx + r * math.cos(ang))
        y = int(cy + r * math.sin(ang))
        x = max(m + bi, min(x, w - m - bi))
        y = max(m + bi, min(y, h - m - bi))
        return (x, y)
    
    def _initialize_factions(self):
        if not self.all_factions:
            for participant in self.participants:
                self.assignment[participant] = 'Neutral'
            return
        if self.starting_factions:
            group_size = 5
            idx = 0
            faction_i = 0
            while idx < len(self.participants):
                group = self.participants[idx:idx + group_size]
                # Find a faction with enough capacity for this group
                name = self._next_available_faction(len(group))
                for p in group:
                    self.assignment[p] = name
                idx += group_size
            return
        # Deferred formation: start as Neutral
        for participant in self.participants:
            self.assignment[participant] = 'Neutral'

    def _faction_member_count(self, name: str) -> int:
        return sum(1 for v in self.assignment.values() if v == name)

    def _next_available_faction(self, needed: int) -> str:
        # Prefer empty factions first, otherwise any with capacity >= needed
        empties = [n for n in self.faction_names if self._faction_member_count(n) == 0]
        for n in empties:
            return n
        for n in self.faction_names:
            if 5 - self._faction_member_count(n) >= needed:
                return n
        # Fallback: return any with space (will not exceed 600 capacity overall)
        for n in self.faction_names:
            if self._faction_member_count(n) < 5:
                return n
        return self.faction_names[0]
    
    def _initialize_locations(self):
        factions_map: Dict[str, List[str]] = {}
        for p in self.participants:
            f = self.assignment.get(p, 'Neutral')
            factions_map.setdefault(f, []).append(p)

        non_neutral_factions = [f for f in factions_map.keys() if f != 'Neutral']
        cluster_styles: Dict[str, str] = {}
        if len(non_neutral_factions) <= len(self.style_order):
            for i, f in enumerate(non_neutral_factions):
                cluster_styles[f] = self.style_order[i]
        else:
            for i, f in enumerate(non_neutral_factions):
                cluster_styles[f] = self.style_order[i % len(self.style_order)]

        cluster_centers: Dict[str, Tuple[int, int]] = {}
        zone_center_slots: Dict[str, List[Tuple[int, int]]] = {}
        for style, rect in self.style_zones.items():
            x0, y0, x1, y1 = rect
            w = x1 - x0
            h = y1 - y0
            cx1 = x0 + w // 4
            cx2 = x0 + w // 2
            cx3 = x0 + (3 * w) // 4
            cy1 = y0 + h // 4
            cy2 = y0 + h // 2
            cy3 = y0 + (3 * h) // 4
            zone_center_slots[style] = [(cx1, cy1), (cx3, cy1), (cx1, cy3), (cx3, cy3), (cx2, cy2)]

        for f in non_neutral_factions:
            style = cluster_styles[f]
            slots = zone_center_slots.get(style, [])
            if slots:
                center = slots.pop(0)
                zone_center_slots[style] = slots
                cluster_centers[f] = center
            else:
                rect = self.style_zones.get(style)
                if rect:
                    x0, y0, x1, y1 = rect
                    center = (random.randint(x0 + 40, x1 - 40), random.randint(y0 + 40, y1 - 40))
                    cluster_centers[f] = center

        for f, members in factions_map.items():
            if f == 'Neutral':
                for p in members:
                    style, location = self.pools.random_location_with_style()
                    self.locations[p] = {'style': style, 'location': location, 'x': 0, 'y': 0}
                    px, py = self._random_point_in_style(style)
                    self.locations[p]['x'] = px
                    self.locations[p]['y'] = py
                    self.forms[p] = 'robot'
            else:
                style = cluster_styles.get(f, random.choice(self.style_order))
                center = cluster_centers.get(f)
                for p in members:
                    if style in self.style_zones:
                        px, py = self._random_point_in_style(style)
                        loc_name = self.pools.random_location_for_style(style)
                        self.locations[p] = {'style': style, 'location': loc_name, 'x': px, 'y': py}
                        self.forms[p] = 'robot'
                    else:
                        style, location = self.pools.random_location_with_style()
                        self.locations[p] = {'style': style, 'location': location, 'x': 0, 'y': 0}
                        if style in self.style_zones:
                            px, py = self._random_point_in_style(style)
                            self.locations[p]['x'] = px
                            self.locations[p]['y'] = py
                        self.forms[p] = 'robot'
    
    def get_faction_color(self, participant: str) -> Tuple[int, int, int]:
        faction = self.assignment.get(participant, 'Neutral')
        if faction == 'Neutral':
            return (255, 255, 255)
        return self.faction_color_map.get(faction, (255, 255, 255))
    
    def render_map(self) -> Optional[BytesIO]:
        if not PIL_AVAILABLE:
            return None
        try:
            img = Image.new('RGBA', self.map_size, (235, 223, 200, 255))
            draw = ImageDraw.Draw(img)
            # Layer order: Rust Dunes (base), then biomes

            # Rust Dunes base - fills whole background
            for poly in self.style_patches['rust_dunes']:
                draw.polygon(poly, fill=(*self.style_bg_colors['rust_dunes'], 255))

            for biome in ['foundry_complex', 'mountain_ridge', 'spire_labyrinth', 'sky_causeways', 'urban_grid']:
                for poly in self.style_patches.get(biome, []):
                    col = self.style_bg_colors[biome]
                    draw.polygon(poly, fill=(col[0], col[1], col[2], 230))

            # Strict 1-pixel image frame
            border_col = (85, 70, 55, 255)
            margin = self.map_margin
            w, h = self.map_size
            draw.rectangle([margin, margin, w-margin-1, h-margin-1], outline=border_col, width=1)

            # --- Emoji Player Markers --- (no overlaps, real emoji Unicode, nice font!)
            size = 22
            stamp_cache: Dict[Tuple[str,int], Image.Image] = {}
            placed: List[Tuple[int,int]] = []
            emoji_font = self._get_emoji_font(size)
            for marker in self.round_markers:
                px, py = marker.get('x', 0), marker.get('y', 0)
                emoji = marker.get('emoji', '⚪')
                tries = 0
                while tries < 10:
                    ok = True
                    for ox, oy in placed:
                        if abs(px-ox) < 18 and abs(py-oy) < 18:
                            ok = False
                            break
                    if ok: break
                    px += random.randint(-6,6)
                    py += random.randint(-6,6)
                    px = max(margin, min(px, w-margin-2))
                    py = max(margin, min(py, h-margin-2))
                    tries += 1
                placed.append((px, py))
                if (emoji, size) not in stamp_cache:
                    stamp_cache[(emoji, size)] = self._emoji_stamp(emoji, size, font=emoji_font)
                stamp = stamp_cache[(emoji, size)]
                img.paste(stamp, (px - stamp.width // 2, py - stamp.height // 2), stamp)

            # --- Render eliminated emojis for players ---
            for participant in self.participants:
                if participant in self.elimination_locations and self.elimination_round.get(participant) == self.round_index:
                    loc = self.elimination_locations[participant]
                    px, py = loc['x'], loc['y']
                    px = max(margin, min(px, w-margin-2))
                    py = max(margin, min(py, h-margin-2))
                    if ('💀', size) not in stamp_cache:
                        stamp_cache[('💀', size)] = self._emoji_stamp('💀', size, font=emoji_font)
                    stamp = stamp_cache[('💀', size)]
                    img.paste(stamp, (px - stamp.width // 2, py - stamp.height // 2), stamp)

            buf = BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            return buf
        except Exception as e:
            logger.error(f"Error rendering map: {e}")
            return None

    def _get_emoji_font(self, size: int):
        if not ImageFont:
            return None
        try:
            return ImageFont.truetype("C:\\Windows\\Fonts\\seguiemj.ttf", size)
        except Exception: pass
        try:
            return ImageFont.truetype("Segoe UI Emoji", size)
        except Exception: pass
        try:
            return ImageFont.truetype("segoe ui emoji", size)
        except Exception:
            return ImageFont.load_default()

    # --- Renders Unicode emoji stamp, returns as RGBA Image! ---
    def _emoji_stamp(self, emoji: str, size: int, font=None) -> Image.Image:
        font = font or self._get_emoji_font(size)
        w = size * 2
        h = size * 2
        img = Image.new('RGBA', (w, h), (0,0,0,0))
        d = ImageDraw.Draw(img)
        try:
            bbox = d.textbbox((0, 0), emoji, font=font)
            tw = max(8, bbox[2] - bbox[0])
            th = max(8, bbox[3] - bbox[1])
        except Exception:
            tw, th = d.textsize(emoji, font=font)
        x = (w-tw)//2
        y = (h-th)//2
        try:
            d.text((x, y), emoji, font=font)
        except Exception:
            d.text((x, y), emoji, fill=(0,0,0,255), font=font)
        try:
            bb = img.getbbox()
            if bb: img = img.crop(bb)
        except Exception: pass
        return img

    def _draw_biome_texture(self, draw: Any, rect: Tuple[int, int, int, int], style: str):
        x0, y0, x1, y1 = rect
        if style == 'urban_grid':
            step = 24
            for gx in range(x0 + 6, x1, step):
                draw.line([(gx, y0 + 4), (gx, y1 - 4)], fill=(200, 200, 210, 40), width=1)
            for gy in range(y0 + 6, y1, step):
                draw.line([(x0 + 4, gy), (x1 - 4, gy)], fill=(200, 200, 210, 40), width=1)
            for gx in range(x0 + 12, x1, step * 2):
                draw.line([(gx, y0 + 4), (gx, y1 - 4)], fill=(240, 240, 250, 50), width=2)
        elif style == 'foundry_complex':
            for i in range(y0, y1, 10):
                draw.line([(x0, i), (x1, i + 20)], fill=(80, 50, 40, 60), width=1)
            for cx in range(x0 + 20, x1, 60):
                for cy in range(y0 + 20, y1, 60):
                    draw.ellipse([cx - 8, cy - 6, cx + 8, cy + 6], fill=(220, 130, 60, 90))
        elif style == 'rust_dunes':
            for dy in range(y0 + 10, y1, 18):
                points = []
                for dx in range(x0 + 10, x1 - 10, 12):
                    px = dx
                    py = dy + ((dx // 12) % 3 - 1) * 2
                    points.append((px, py))
                draw.line(points, fill=(200, 160, 120, 70), width=2)
        elif style == 'mountain_ridge':
            for k in range(5):
                ox = x0 + 20 + k * 20
                oy = y0 + 20 + k * 15
                draw.arc([ox, oy, x1 - 20 - k * 20, y1 - 20 - k * 15], start=0, end=180, fill=(180, 210, 210, 90), width=2)
        elif style == 'spire_labyrinth':
            for sx in range(x0 + 20, x1 - 10, 22):
                h = (sx % 40) + 40
                draw.rectangle([sx, y1 - h, sx + 6, y1 - 8], fill=(160, 140, 190, 120))
        elif style == 'sky_causeways':
            for gy in range(y0 + 25, y1 - 25, 40):
                draw.line([(x0 + 10, gy), (x1 - 10, gy)], fill=(190, 220, 250, 80), width=3)
            for gx in range(x0 + 30, x1 - 30, 60):
                draw.line([(gx, y0 + 10), (gx + 40, y1 - 10)], fill=(170, 200, 240, 60), width=2)

    def _draw_biome_region(self, draw: Any, rect: Tuple[int, int, int, int], style: str):
        x0, y0, x1, y1 = rect
        base = self.style_bg_colors.get(style, (120, 120, 120))

        if style == 'sky_causeways':
            w, h = self.map_size
            cx = w // 2
            cy = h // 2
            r0, r1 = self._ring_specs()['sky_causeways']
            # radial spokes within the inner circle
            for a in range(0, 360, 30):
                ang = a * math.pi / 180
                x0 = int(cx + r0 * math.cos(ang))
                y0 = int(cy + r0 * math.sin(ang))
                x1 = int(cx + r1 * math.cos(ang))
                y1 = int(cy + r1 * math.sin(ang))
                draw.line([(x0, y0), (x1, y1)], fill=(80, 140, 200, 40), width=4)
            # circular tracks
            step = max(8, (r1 - r0) // 5)
            for r in range(r0 + step // 2, r1, step):
                draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(190, 220, 250, 35), width=2)
            return

        if style == 'spire_labyrinth':
            w, h = self.map_size
            cx = w // 2
            cy = h // 2
            r0, r1 = self._ring_specs()['spire_labyrinth']
            step = max(10, (r1 - r0) // 5)
            for r in range(r0, r1, step):
                draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(90, 70, 120, 50), width=2)
            for a in range(0, 360, 45):
                ang = a * math.pi / 180
                x0 = int(cx + r0 * math.cos(ang))
                y0 = int(cy + r0 * math.sin(ang))
                x1 = int(cx + r1 * math.cos(ang))
                y1 = int(cy + r1 * math.sin(ang))
                draw.line([(x0, y0), (x1, y1)], fill=(160, 140, 190, 40), width=2)
            return

        if style == 'mountain_ridge':
            w, h = self.map_size
            cx = w // 2
            cy = h // 2
            r0, r1 = self._ring_specs()['mountain_ridge']
            inc = max(8, (r1 - r0) // 6)
            for k in range(5):
                r = r0 + k * inc
                draw.arc([cx - r, cy - r, cx + r, cy + r], start=200, end=340, fill=(180, 210, 210, 45), width=2)
                draw.arc([cx - r, cy - r, cx + r, cy + r], start=20, end=160, fill=(180, 210, 210, 45), width=2)
            return

        if style == 'foundry_complex':
            w, h = self.map_size
            cx = w // 2
            cy = h // 2
            r0, r1 = self._ring_specs()['foundry_complex']
            for r in range(r0 + 12, r1, 26):
                for a in range(0, 360, 36):
                    ang = a * math.pi / 180
                    x = int(cx + r * math.cos(ang))
                    y = int(cy + r * math.sin(ang))
                    draw.ellipse([x - 6, y - 4, x + 6, y + 4], fill=(220, 130, 60, 40))
            for a in range(0, 360, 22):
                ang = a * math.pi / 180
                x0 = int(cx + (r0 + 6) * math.cos(ang))
                y0 = int(cy + (r0 + 6) * math.sin(ang))
                x1 = int(cx + (r1 - 6) * math.cos(ang))
                y1 = int(cy + (r1 - 6) * math.sin(ang))
                draw.line([(x0, y0), (x1, y1)], fill=(80, 50, 40, 35), width=1)
            return

        if style == 'urban_grid':
            w, h = self.map_size
            cx = w // 2
            cy = h // 2
            r0, r1 = self._ring_specs()['urban_grid']
            step = 36
            for r in range(r0 + 12, r1 - 12, step):
                draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(200, 200, 210, 20), width=1)
            for a in range(0, 360, 45):
                ang = a * math.pi / 180
                x0 = int(cx + r0 * math.cos(ang))
                y0 = int(cy + r0 * math.sin(ang))
                x1 = int(cx + r1 * math.cos(ang))
                y1 = int(cy + r1 * math.sin(ang))
                draw.line([(x0, y0), (x1, y1)], fill=(240, 240, 250, 25), width=1)
            return

        if style == 'rust_dunes':
            w, h = self.map_size
            cx = w // 2
            cy = h // 2
            r0, r1 = self._ring_specs()['rust_dunes']
            for r in range(r0 + 16, r1, 26):
                points = []
                for a in range(0, 360, 18):
                    ang = a * math.pi / 180
                    ra = r + ((a // 12) % 3 - 1) * 2
                    x = int(cx + ra * math.cos(ang))
                    y = int(cy + ra * math.sin(ang))
                    points.append((x, y))
                draw.line(points, fill=(200, 160, 120, 35), width=2)
            return

        self._draw_biome_texture(draw, rect, style)

    def _generate_biome_polygon(self, rect: Tuple[int, int, int, int], style: str) -> List[Tuple[int, int]]:
        x0, y0, x1, y1 = rect
        amp_map = {
            'urban_grid': 8,
            'foundry_complex': 14,
            'rust_dunes': 16,
            'mountain_ridge': 20,
            'spire_labyrinth': 12,
            'sky_causeways': 16,
        }
        amp = amp_map.get(style, 12)
        over = amp // 2
        points: List[Tuple[int, int]] = []
        w = x1 - x0
        h = y1 - y0
        cols = 10
        rows = 10
        for t in range(cols + 1):
            x = x0 + int(t * w / cols)
            y = y0 + random.randint(-over, over)
            y = max(self.map_margin, min(y, self.map_size[1] - self.map_margin))
            points.append((x, y))
        for t in range(rows + 1):
            y = y0 + int(t * h / rows)
            x = x1 + random.randint(-over, over)
            x = max(self.map_margin, min(x, self.map_size[0] - self.map_margin))
            points.append((x, y))
        for t in range(cols + 1):
            x = x1 - int(t * w / cols)
            y = y1 + random.randint(-over, over)
            y = max(self.map_margin, min(y, self.map_size[1] - self.map_margin))
            points.append((x, y))
        for t in range(rows + 1):
            y = y1 - int(t * h / rows)
            x = x0 + random.randint(-over, over)
            x = max(self.map_margin, min(x, self.map_size[0] - self.map_margin))
            points.append((x, y))
        return points

    def _jitter_polygon(self, points: List[Tuple[int, int]], mag: int) -> List[Tuple[int, int]]:
        jp: List[Tuple[int, int]] = []
        for x, y in points:
            jx = max(self.map_margin, min(x + random.randint(-mag, mag), self.map_size[0] - self.map_margin))
            jy = max(self.map_margin, min(y + random.randint(-mag, mag), self.map_size[1] - self.map_margin))
            jp.append((jx, jy))
        return jp

    def _apply_parchment_overlay(self, img: Any):
        w, h = img.size
        d = ImageDraw.Draw(img)
        for i in range(8):
            pad = 8 + i * 6
            alpha = 80 - i * 9
            d.rectangle([pad, pad, w - pad, h - pad], outline=(70, 55, 40, max(alpha, 10)), width=2)

    def _hash_noise(self, ix: int, iy: int, seed: int) -> float:
        n = (ix * 374761393 + iy * 668265263 + seed * 144005 + 0x9e3779b9) & 0xffffffff
        n ^= (n >> 13)
        n = (n * 1274126177) & 0xffffffff
        return (n & 0xffffffff) / 4294967295.0

    def _noise_bilinear(self, x: float, y: float, scale: float, seed: int) -> float:
        gx = int(x / scale)
        gy = int(y / scale)
        fx = x / scale - gx
        fy = y / scale - gy
        def s(t: float) -> float:
            return t * t * (3.0 - 2.0 * t)
        sx = s(fx)
        sy = s(fy)
        v00 = self._hash_noise(gx, gy, seed)
        v10 = self._hash_noise(gx + 1, gy, seed)
        v01 = self._hash_noise(gx, gy + 1, seed)
        v11 = self._hash_noise(gx + 1, gy + 1, seed)
        i1 = v00 + (v10 - v00) * sx
        i2 = v01 + (v11 - v01) * sx
        return i1 + (i2 - i1) * sy

    def _generate_heightmap(self) -> Image.Image:
        w, h = self.map_size
        hm = Image.new('L', (w, h))
        px = hm.load()
        seed = random.randint(1, 10_000_000)
        octaves = [(160.0, 0.55), (80.0, 0.30), (38.0, 0.10), (18.0, 0.05)]
        ampsum = sum(a for _, a in octaves)
        for y in range(h):
            for x in range(w):
                v = 0.0
                for sc, amp in octaves:
                    v += amp * self._noise_bilinear(x, y, sc, seed)
                v /= ampsum
                px[x, y] = int(max(0.0, min(1.0, v)) * 255)
        return hm

    def _colorize_heightmap(self, hm: Image.Image) -> Image.Image:
        w, h = hm.size
        src = hm.load()
        out = Image.new('RGBA', (w, h))
        dst = out.load()
        for y in range(h):
            for x in range(w):
                t = src[x, y] / 255.0
                if t < 0.35:
                    col = (222, 206, 180)
                elif t < 0.55:
                    col = (184, 196, 160)
                elif t < 0.75:
                    col = (160, 150, 140)
                else:
                    col = (235, 235, 235)
                dst[x, y] = (col[0], col[1], col[2], 255)
        return out

    def _compute_shading(self, hm: Image.Image) -> Image.Image:
        w, h = hm.size
        src = hm.load()
        shade = Image.new('L', (w, h))
        spx = shade.load()
        lx, ly, lz = -0.6, -0.6, 0.5
        for y in range(h):
            for x in range(w):
                x0 = max(0, x - 1)
                x1 = min(w - 1, x + 1)
                y0 = max(0, y - 1)
                y1 = min(h - 1, y + 1)
                dzdx = (src[x1, y] - src[x0, y]) / 255.0
                dzdy = (src[x, y1] - src[x, y0]) / 255.0
                nx, ny, nz = -dzdx, -dzdy, 1.0
                invlen = 1.0 / max(1e-6, (nx * nx + ny * ny + nz * nz) ** 0.5)
                nx *= invlen
                ny *= invlen
                nz *= invlen
                dot = nx * lx + ny * ly + nz * lz
                val = int(max(0.0, min(1.0, 0.5 + 0.5 * dot)) * 255)
                spx[x, y] = val
        return shade

    def _render_terrain_base(self) -> Image.Image:
        hm = self._generate_heightmap()
        color = self._colorize_heightmap(hm)
        shade = self._compute_shading(hm)
        sh_rgb = Image.merge('RGBA', (shade, shade, shade, Image.new('L', color.size, 120)))
        return ImageChops.multiply(color, sh_rgb)

    def _get_emoji_font(self, size: int):
        if not ImageFont:
            return None
        try:
            return ImageFont.truetype("C:\\Windows\\Fonts\\seguiemj.ttf", size)
        except Exception:
            pass
        try:
            return ImageFont.truetype("Segoe UI Emoji", size)
        except Exception:
            pass
        try:
            return ImageFont.truetype("segoe ui emoji", size)
        except Exception:
            return ImageFont.load_default()

    def _get_label_font(self, size: int):
        if not ImageFont:
            return None
        try:
            return ImageFont.truetype("C:\\Windows\\Fonts\\segoeui.ttf", size)
        except Exception:
            pass
        try:
            return ImageFont.truetype("Segoe UI", size)
        except Exception:
            pass
        try:
            return ImageFont.truetype("Arial", size)
        except Exception:
            return ImageFont.load_default()

    def _emoji_stamp(self, emoji: str, size: int) -> Image.Image:
        font = self._get_emoji_font(size)
        w = size * 2
        h = size * 2
        img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        try:
            bbox = d.textbbox((0, 0), emoji, font=font)
            tw = max(8, bbox[2] - bbox[0])
            th = max(8, bbox[3] - bbox[1])
        except Exception:
            tw, th = d.textsize(emoji, font=font)
        x = (w - tw) // 2
        y = (h - th) // 2
        try:
            d.text((x, y), emoji, font=font)
        except Exception:
            d.text((x, y), emoji, fill=(0, 0, 0, 255), font=font)
        try:
            bb = img.getbbox()
            if bb:
                img = img.crop(bb)
        except Exception:
            pass
        return img


    def _draw_compass_rose(self, draw: Any, x: int, y: int, r: int):
        draw.ellipse([x, y, x + r, y + r], outline=(90, 70, 60, 255), width=3)
        draw.ellipse([x + 10, y + 10, x + r - 10, y + r - 10], outline=(120, 90, 70, 255), width=2)
        cx = x + r // 2
        cy = y + r // 2
        for a in range(0, 360, 22):
            dx = int(r // 2 * 0.9 * (ImageFont and 1))
            draw.line([(cx, cy), (cx + int(0.9 * (r // 2) * (1 if a % 44 == 0 else 0.8)), cy)], fill=(120, 90, 70, 255), width=1)
        draw.text((cx - 5, y - 18), "N", fill=(90, 70, 60, 255), font=ImageFont.load_default())

    def _draw_cartouche(self, draw: Any, x: int, y: int, title: str):
        w = 560
        h = 70
        draw.rectangle([x, y, x + w, y + h], fill=(245, 235, 210, 220), outline=(90, 70, 60, 255), width=2)
        font = getattr(self, '_get_label_font', None)
        if callable(font):
            ft = self._get_label_font(32)
        else:
            try:
                ft = ImageFont.truetype("C:\\Windows\\Fonts\\segoeui.ttf", 32)
            except Exception:
                ft = ImageFont.load_default()
        draw.text((x + 16, y + 18), title, fill=(90, 70, 60, 255), font=ft)

    def _draw_grid_labels(self, draw: Any):
        font = ImageFont.load_default()
        cols = 12
        rows = 8
        x_step = (self.map_size[0] - 2 * self.map_margin) // cols
        y_step = (self.map_size[1] - 2 * self.map_margin) // rows
        for c in range(cols):
            label = chr(ord('A') + c)
            x = self.map_margin + c * x_step + 4
            draw.text((x, self.map_margin - 24), label, fill=(100, 80, 70, 255), font=font)
            draw.text((x, self.map_size[1] - self.map_margin + 8), label, fill=(100, 80, 70, 255), font=font)
        for r in range(rows):
            label = str(r + 1)
            y = self.map_margin + r * y_step + 2
            draw.text((self.map_margin - 24, y), label, fill=(100, 80, 70, 255), font=font)
            draw.text((self.map_size[0] - self.map_margin + 6, y), label, fill=(100, 80, 70, 255), font=font)
    
    def process_round(self) -> Dict[str, Any]:
        """Process a single round of the game"""
        self.round_index += 1
        try:
            self.style_patches = self._compute_style_patches(seed=self.round_index)
        except Exception:
            self.style_patches = self._compute_style_patches()
        for p in self.alive:
            self.forms[p] = 'robot'
        self.round_markers = []
        
        if len(self.alive) <= 1:
            return {
                'round_index': self.round_index,
                'actions': [],
                'eliminations': [],
                'remaining': self.alive.copy(),
                'game_over': True
            }
        
        # Build per-round scheduling pool
        unassigned = list(self.alive)
        random.shuffle(unassigned)
        round_actions = []
        round_eliminations = []
        round_mode = random.choice(['actions_only', 'elims_only', 'mixed'])
        
        while unassigned:
            # Start a new event with the next participant
            leader = unassigned[0]
            leader_faction = self.assignment.get(leader, 'Neutral')
            
            # Determine sizes up-front to avoid leaving a single leftover participant
            k = len(unassigned)
            
            # For factions: use ALL remaining users for the event
            if leader_faction != 'Neutral':
                # Faction events: use all remaining users
                if k >= 2:
                    # Split all remaining users between sides
                    if k == 2:
                        desired_a = 1
                        desired_b = 1
                    else:
                        # Random split of all users, but ensure both sides have at least 1
                        desired_a = random.randint(1, k - 1)
                        desired_b = k - desired_a
                else:
                    desired_a = 1
                    desired_b = 0
            else:
                # Neutral users: biased probability toward 1vANY, less likely for larger groups
                # Create weighted probability distribution
                if k >= 2:
                    # Higher chance of 1vANY for neutrals
                    weights = []
                    for size in range(1, min(6, k)):  # 1 to 5 or max available
                        if size == 1:
                            weights.append(3)  # 3x more likely for 1vANY
                        elif size == 2:
                            weights.append(2)  # 2x for 2vANY
                        else:
                            weights.append(1)  # Normal weight for larger groups
                    
                    desired_a = random.choices(range(1, min(6, k)), weights=weights)[0]
                    remaining_after_a = k - desired_a
                    if remaining_after_a >= 1:
                        desired_b = random.randint(1, min(5, remaining_after_a))
                    else:
                        desired_b = 0
                else:
                    desired_a = 1
                    desired_b = 0
            
            leftover = k - desired_a - desired_b
            if leftover == 1:
                # Prefer increasing B if possible; otherwise increase A
                max_b = min(5, k - desired_a)
                if desired_b < max_b:
                    desired_b += 1
                else:
                    max_a = min(5, k - 1)
                    if desired_a < max_a:
                        desired_a += 1
            
            # Construct Side A: completely random selection
            side_a = [leader]
            available_pool = unassigned[1:]  # All available participants except leader
            random.shuffle(available_pool)
            side_a.extend(available_pool[:(desired_a - 1)])
            
            # Now select Side B
            remaining_pool = [p for p in unassigned if p not in side_a]
            if not remaining_pool:
                if len(side_a) > 1:
                    moved = side_a.pop()
                    remaining_pool = [moved]
                else:
                    loc_style = self.locations.get(leader, {}).get('style', random.choice(self.style_order))
                    loc_name = self.pools.random_location_for_style(loc_style)
                    solo_template = "{A1} scouts at {Location}."
                    text = _fill_template_with_location(solo_template, loc_style, side_a, [], self.pools, loc_name)
                    cluster_center = self._random_point_in_style(loc_style)
                    for participant in side_a:
                        self.locations[participant] = {
                            'style': loc_style,
                            'location': loc_name,
                            'x': 0,
                            'y': 0
                        }
                        px, py = self._scatter_around(cluster_center)
                        self.locations[participant]['x'] = px
                        self.locations[participant]['y'] = py
                        if participant in self.alive:
                            self.forms[participant] = 'vehicle'
                    solo_emoji = self.get_faction_emoji(side_a[0], 'robot', False)
                    self.round_markers.append({'x': cluster_center[0], 'y': cluster_center[1], 'style': loc_style, 'is_elimination': False, 'emoji': solo_emoji, 'side_a': side_a, 'side_b': []})
                    action_emojis = self.get_event_emojis(side_a, [], is_elimination=False)
                    emoji_text = f"{action_emojis} {text}"
                    round_actions.append(emoji_text)
                    for participant in side_a:
                        self.action_log.setdefault(participant, []).append(emoji_text)
                        if participant in unassigned:
                            unassigned.remove(participant)
                    if len(self.alive) == 0:
                        break
                    continue

            desired_b = min(desired_b, len(remaining_pool))
            # Side B: completely random selection from remaining pool
            random.shuffle(remaining_pool)
            side_b = remaining_pool[:desired_b]
            
            # Decide event type
            if round_mode == 'actions_only':
                is_elim = False
            elif round_mode == 'elims_only':
                is_elim = True
            else:
                is_elim = random.choice([True, False])
            style = f"{len(side_a)}v{len(side_b)}"
            
            # Get template
            if is_elim:
                pool = self.pools.elims_by_style
                templates = pool.get(style, [])
                if not templates:
                    templates = self.pools.actions_by_style.get(style, ["{A1} eliminates {B1} at {Location}."])
            else:
                pool = self.pools.actions_by_style
                templates = pool.get(style, [])
                if not templates:
                    templates = ["{A1} and {B1} exchange signals at {Location}."]
            
            template = random.choice(templates) if templates else "{A1} and {B1} interact at {Location}."
            
            # Choose location style based on where participants currently are
            style_counts: Dict[str, int] = {}
            for participant in side_a + side_b:
                loc = self.locations.get(participant)
                if loc and isinstance(loc, dict):
                    s = loc.get('style')
                    if s:
                        style_counts[s] = style_counts.get(s, 0) + 1
            if style_counts:
                loc_style = max(style_counts.items(), key=lambda kv: kv[1])[0]
            else:
                loc_style = random.choice(self.style_order)
            loc_name = self.pools.random_location_for_style(loc_style)
            text = _fill_template_with_location(template, loc_style, side_a, side_b, self.pools, loc_name)
            
            # Update clustered locations for participants in this event
            cluster_center = self._random_point_in_style(loc_style)
            for participant in side_a + side_b:
                self.locations[participant] = {
                    'style': loc_style,
                    'location': loc_name,
                    'x': 0,
                    'y': 0
                }
                px, py = self._scatter_around(cluster_center)
                self.locations[participant]['x'] = px
                self.locations[participant]['y'] = py
            if len(side_a) in (1, 2, 3):
                a_form = 'vehicle'
            else:
                a_form = 'combiner' if ('{CombinerA}' in template and not ('{VehicleA}' in template)) else 'vehicle'
            if len(side_b) in (1, 2, 3):
                b_form = 'vehicle'
            else:
                b_form = 'combiner' if ('{CombinerB}' in template and not ('{VehicleB}' in template)) else 'vehicle'
            for participant in side_a:
                if participant in self.alive:
                    self.forms[participant] = a_form
            for participant in side_b:
                if participant in self.alive:
                    self.forms[participant] = b_form
            event_emoji = self._form_count_emoji(len(side_a), a_form == 'combiner')
            self.round_markers.append({'x': cluster_center[0], 'y': cluster_center[1], 'style': loc_style, 'is_elimination': is_elim, 'emoji': event_emoji, 'side_a': side_a, 'side_b': side_b})

            # Mid-game faction formation rules
            if self.all_factions and not self.starting_factions:
                if not is_elim:
                    if len(side_a) >= 3:
                        neutrals = [p for p in side_a if self.assignment.get(p, 'Neutral') == 'Neutral']
                        if neutrals:
                            name = self._next_available_faction(len(neutrals))
                            for p in neutrals:
                                self.assignment[p] = name
                    if len(side_b) >= 3:
                        neutrals = [p for p in side_b if self.assignment.get(p, 'Neutral') == 'Neutral']
                        if neutrals:
                            name = self._next_available_faction(len(neutrals))
                            for p in neutrals:
                                self.assignment[p] = name
                else:
                    if len(side_a) >= 3:
                        neutrals = [p for p in side_a if self.assignment.get(p, 'Neutral') == 'Neutral']
                        if neutrals:
                            name = self._next_available_faction(len(neutrals))
                            for p in neutrals:
                                self.assignment[p] = name
            
            if is_elim:
                # Add emoji prefix for elimination messages
                elim_emojis = self.get_event_emojis(side_a, side_b, is_elimination=True)
                emoji_text = f"{elim_emojis} {text}"
                
                round_eliminations.append(emoji_text)
                for participant in side_a:
                    self.action_log.setdefault(participant, []).append(emoji_text)
                for participant in side_b:
                    self.action_log.setdefault(participant, []).append(emoji_text)
                for victim in side_b:
                    for killer in side_a:
                        self.kill_log.setdefault(killer, []).append({
                            'victim': victim,
                            'with': [p for p in side_a if p != killer],
                            'text': emoji_text
                        })
                for participant in side_b:
                    if participant in self.alive:
                        self.alive.remove(participant)
                        self.elimination_locations[participant] = self.locations[participant].copy()
                        self.elimination_round[participant] = self.round_index
            else:
                # Add emoji prefix for action messages
                action_emojis = self.get_event_emojis(side_a, side_b, is_elimination=False)
                emoji_text = f"{action_emojis} {text}"
                
                round_actions.append(emoji_text)
                for participant in side_a:
                    self.action_log.setdefault(participant, []).append(emoji_text)
                for participant in side_b:
                    self.action_log.setdefault(participant, []).append(emoji_text)
            
            # Mark all participants in this event as assigned this round
            for participant in side_a + side_b:
                if participant in unassigned:
                    unassigned.remove(participant)
            
            # If alive count drops to 0 mid-round, stop constructing events
            if len(self.alive) == 0:
                break
        
        return {
            'round_index': self.round_index,
            'actions': round_actions,
            'eliminations': round_eliminations,
            'remaining': self.alive.copy(),
            'game_over': len(self.alive) <= 1
        }


class GameSetupView(ui.View):
    def __init__(self, game_session: GameSession, ctx: commands.Context):
        super().__init__(timeout=300)
        self.game_session = game_session
        self.ctx = ctx
        self.message = None

    @ui.button(label="Start Game", style=ButtonStyle.green, emoji="⚔️")
    async def start_game(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Only the game creator can start the game!", ephemeral=True)
            return

        self.game_session.started = True
        await interaction.response.send_message("🎮 **Cybertron Games Started!** 🎮", ephemeral=False)

        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)

        control_view = RoundControlView(self.game_session, self.ctx)
        await control_view.send_round()

    @ui.button(label="Cancel Game", style=ButtonStyle.red, emoji="❌")
    async def cancel_game(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Only the game creator can cancel the game!", ephemeral=True)
            return

        await interaction.response.send_message("❌ **Game Cancelled** ❌", ephemeral=False)

        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)
        self.stop()

class RoundControlView(ui.View):
    def __init__(self, game_session: GameSession, ctx: commands.Context):
        super().__init__(timeout=600)
        self.game_session = game_session
        self.ctx = ctx
        self.message = None

    @ui.button(label="Next Round", style=ButtonStyle.primary, emoji="➡️")
    async def next_round(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Only the game creator can advance rounds!", ephemeral=True)
            return
        await interaction.response.defer()
        if len(self.game_session.alive) <= 1:
            await self._end_game()
            return
        await self.send_round()
        if self.message:
            await self.message.edit(view=self)

    @ui.button(label="End Games", style=ButtonStyle.red, emoji="🛑")
    async def end_games(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Only the game creator can end the game!", ephemeral=True)
            return
        await interaction.response.defer()
        await self._end_game()

    async def _end_game(self):
        if len(self.game_session.alive) == 1:
            winner = self.game_session.alive[0]
            winner_name = self.game_session.get_participant_name(winner)
            faction = self.game_session.assignment.get(winner, 'Neutral')
            buf = await self._generate_champion_image(winner)
            if buf:
                await self.ctx.send(f"🏆 **CHAMPION DETERMINED!** 🏆\n**{winner_name}** from **{faction}** wins the Cybertron Games!", file=File(buf, filename="champion_journey.png"))
            else:
                await self.ctx.send(f"🏆 **CHAMPION DETERMINED!** 🏆\n**{winner_name}** from **{faction}** wins the Cybertron Games!")
            kills_by_user: Dict[str, int] = {}
            for u in self.game_session.participants:
                c = len(self.game_session.kill_log.get(u, []))
                if c > 0:
                    kills_by_user[u] = c
            kills_by_faction: Dict[str, int] = {}
            for u, c in kills_by_user.items():
                f = self.game_session.assignment.get(u, 'Neutral')
                kills_by_faction[f] = kills_by_faction.get(f, 0) + c
            faction_rank = sorted(kills_by_faction.items(), key=lambda kv: (-kv[1], kv[0]))
            user_rank = sorted(kills_by_user.items(), key=lambda kv: (-kv[1], kv[0]))
            def medal(i: int) -> str:
                return '🥇' if i == 0 else '🥈' if i == 1 else '🥉' if i == 2 else ''
            if faction_rank:
                lines = []
                for i, (name, count) in enumerate(faction_rank):
                    m = medal(i)
                    prefix = f"{m} " if m else ""
                    lines.append(f"{prefix}{name}: {count}")
                await _send_long_message(self.ctx.channel, "**🏛️ Faction Total Eliminations**\n" + "\n".join(lines))
            else:
                await _send_long_message(self.ctx.channel, "**🏛️ Faction Total Eliminations**\nNone")
            if user_rank:
                lines = []
                for i, (user_obj, count) in enumerate(user_rank):
                    m = medal(i)
                    prefix = f"{m} " if m else ""
                    user_name = self.game_session.get_participant_name(user_obj)
                    lines.append(f"{prefix}{user_name}: {count}")
                await _send_long_message(self.ctx.channel, "**⚔️ User Total Eliminations**\n" + "\n".join(lines))
            else:
                await _send_long_message(self.ctx.channel, "**⚔️ User Total Eliminations**\nNone")
        else:
            await self.ctx.send("⚡ **Game ended by host**")
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)
        self.stop()

    async def send_round(self):
        result = self.game_session.process_round()
        header = f"**⚡ ROUND {result['round_index']} RESULTS ⚡**\n*Participants remaining: {len(result['remaining'])}*"
        await self.ctx.send(header)
        if result['actions']:
            actions_text = "**📋 ACTIONS:**\n" + "\n".join(f"• {a}" for a in result['actions'])
            await _send_long_message(self.ctx.channel, actions_text)
        if result['eliminations']:
            elim_text = "**💀 ELIMINATIONS:**\n" + "\n".join(f"• {e}" for e in result['eliminations'])
            await _send_long_message(self.ctx.channel, elim_text)
        if result['remaining']:
            remaining_text = "**⚔️ REMAINING WARRIORS:**\n"
            faction_groups: Dict[str, List[str]] = {}
            for p in result['remaining']:
                f = self.game_session.assignment.get(p, 'Neutral')
                participant_name = self.game_session.get_participant_name(p)
                faction_groups.setdefault(f, []).append(participant_name)
            for f, members in faction_groups.items():
                remaining_text += f"**{f}:** {', '.join(members)}\n"
            await _send_long_message(self.ctx.channel, remaining_text)
        buf = self.game_session.render_map()
        if buf:
            self.message = await self.ctx.send(file=File(buf, filename=f"cybertron_round_{result['round_index']}.png"), view=self)
        else:
            self.message = await self.ctx.send("Use the controls below to continue.", view=self)
        if result['game_over']:
            await self._end_game()

if __name__ == "__main__":
    pools = DataPools()
    pools.reload()
    participants = [f"Warrior-{i+1}" for i in range(50)]
    color_circles = {"🟣","🔴","🟠","🟡","🟢","🔵","⚪"}
    need_vehicles = {"🏍️","🚙","🚛"}
    need_combiners = {"🔱","⚜️"}
    found = False
    last_buf = None
    for attempt in range(40):
        random.seed()
        session = GameSession(participants, pools, all_factions=False, starting_factions=False)
        result = session.process_round()
        emojis = {m.get('emoji') for m in session.round_markers}
        has_solo = any(e in color_circles for e in emojis)
        has_elim = any(m.get('is_elimination') for m in session.round_markers)
        if need_vehicles.issubset(emojis) and need_combiners.issubset(emojis) and has_solo and has_elim:
            buf = session.render_map()
            if buf:
                with open("sample_map_demo.png", "wb") as f:
                    f.write(buf.getvalue())
                found = True
            break
        last_buf = session.render_map()
    if not found and last_buf:
        with open("sample_map_demo.png", "wb") as f:
            f.write(last_buf.getvalue())

    async def _generate_champion_image(self, winner: str) -> Optional[BytesIO]:
        if not PIL_AVAILABLE:
            return None
        try:
            kills = self.game_session.kill_log.get(winner, [])
            acts = self.game_session.action_log.get(winner, [])
            base_w = 900
            lines_k = max(1, len(kills))
            lines_a = max(1, len(acts))
            base_h = 500 + (lines_k * 28) + (lines_a * 22)
            img = Image.new('RGBA', (base_w, base_h), (235, 223, 200, 255))
            d = ImageDraw.Draw(img)
            self.game_session._apply_parchment_overlay(img)
            title = "Champion's Journey"
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None
            d.rectangle([20, 20, base_w - 20, 120], outline=(85, 70, 55, 255), width=3, fill=(245, 235, 210, 230))
            d.text((40, 50), title, fill=(90, 70, 60, 255), font=font)
            avatar = None
            member = None
            winner_name = self.game_session.get_participant_name(winner)
            
            # Find the Discord member object for the winner
            if hasattr(self.ctx, 'guild') and self.ctx.guild:
                # First try to find by the original user object if it's a Discord user
                if hasattr(winner, 'id'):
                    member = self.ctx.guild.get_member(winner.id)
                else:
                    # Fallback: search by display name
                    for m in self.ctx.guild.members:
                        if m.display_name == winner_name:
                            member = m
                            break
            if member:
                try:
                    b = await member.display_avatar.read()
                    avatar = Image.open(BytesIO(b)).convert('RGBA')
                except Exception:
                    avatar = None
            if avatar is None:
                avatar = Image.new('RGBA', (300, 300), (200, 200, 200, 255))
            av_size = 260
            avatar = avatar.resize((av_size, av_size))
            mask = Image.new('L', (av_size, av_size), 0)
            mdraw = ImageDraw.Draw(mask)
            mdraw.ellipse([0, 0, av_size, av_size], fill=255)
            img.paste(avatar, (40, 140), mask)
            cx = 40 + av_size // 2
            cy = 140
            crown_w = 180
            crown_h = 80
            cx0 = cx - crown_w // 2
            cy0 = cy - crown_h - 10
            pts = [
                (cx0, cy0 + crown_h),
                (cx0 + crown_w // 4, cy0 + crown_h // 2),
                (cx0 + crown_w // 2, cy0 + crown_h),
                (cx0 + 3 * crown_w // 4, cy0 + crown_h // 2),
                (cx0 + crown_w, cy0 + crown_h),
                (cx0 + crown_w, cy0),
                (cx0, cy0)
            ]
            d.polygon(pts, fill=(255, 215, 0, 220), outline=(150, 120, 20, 255))
            d.rectangle([330, 140, base_w - 40, 180], outline=(85, 70, 55, 255), width=2, fill=(245, 235, 210, 200))
            d.text((340, 150), f"Champion: {winner_name}", fill=(90, 70, 60, 255), font=font)
            d.text((340, 170), f"Eliminations: {len(kills)}", fill=(90, 70, 60, 255), font=font)
            y = 210
            d.text((330, y), "Eliminations", fill=(90, 70, 60, 255), font=font)
            y += 24
            for k in kills:
                victims = k.get('victim')
                allies = k.get('with', [])
                victim_name = self.game_session.get_participant_name(victims) if victims else "Unknown"
                ally_names = [self.game_session.get_participant_name(ally) for ally in allies]
                if ally_names:
                    line = f"Eliminated {victim_name} with {', '.join(ally_names)}"
                else:
                    line = f"Eliminated {victim_name} solo"
                d.text((330, y), line, fill=(60, 50, 45, 255), font=font)
                y += 24
            y += 12
            d.text((330, y), "Actions", fill=(90, 70, 60, 255), font=font)
            y += 24
            for a in acts:
                d.text((330, y), a, fill=(60, 50, 45, 255), font=font)
                y += 22
            buf = BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            return buf
        except Exception as e:
            logger.error(f"Champion image error: {e}")
            return None


class CybertronGames(commands.Cog):
    """Enhanced Cybertron Games with interactive maps and faction-based gameplay."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.pools = DataPools()
        try:
            self.pools.reload()
            logger.info("✅ Cybertron data pools loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load Cybertron data pools: {e}")

    @commands.hybrid_group(name="cybertronian")
    async def cybertron(self, ctx: commands.Context):
        """Base group for Cybertron Games commands."""
        pass

    @cybertron.command(name="games")
    @app_commands.describe(
        warriors="Total number of participants (10-100)",
        all_factions="Toggle all factions system (true/false)",
        starting_factions="Toggle starting factions assignment (true/false)",
        users="Mention users to include in the games (separate with spaces)",
        bots="Toggle random bot inclusion (true/false)",
        roles="Mention roles to randomly select users from those roles"
    )
    async def games(self, ctx: commands.Context, warriors: int, all_factions: bool = False, starting_factions: bool = False, users: str = "", bots: bool = False, roles: str = ""):
        """Start a new Cybertron Games session with interactive map and faction-based gameplay."""
        
        # Validate parameters
        if warriors < 10 or warriors > 100:
            return await ctx.send("❌ Warriors must be between 10 and 100.")
        
        # toggles are booleans; enforce consistency: starting_factions only works when all_factions is True
        starting_factions = starting_factions and all_factions
        
        # Parse participants - collect Discord user objects
        participants = []
        
        # Add mentioned users
        if ctx.message and ctx.message.mentions:
            participants.extend([user for user in ctx.message.mentions])
        
        # Add users from the users parameter (split by spaces) - these are display names
        if users:
            user_names = [name.strip() for name in users.split() if name.strip()]
            participants.extend(user_names)
        
        # Handle role mentions - randomly select users from mentioned roles
        if ctx.message and ctx.message.role_mentions:
            role_users = []
            for role in ctx.message.role_mentions:
                # Get members with this role who aren't already participants
                role_members = [member for member in role.members if member not in participants]
                role_users.extend(role_members)
            
            # Remove duplicates and shuffle
            role_users = list(set(role_users))
            random.shuffle(role_users)
            
            # Add role users to participants (respect warrior limit)
            needed = warriors - len(participants)
            if needed > 0:
                participants.extend(role_users[:needed])
        
        # Handle role names from parameter - find roles by name and select users
        elif roles:
            role_names = [name.strip() for name in roles.split() if name.strip()]
            role_users = []
            
            for role_name in role_names:
                # Find role by name in the guild
                found_role = None
                for guild_role in ctx.guild.roles:
                    if guild_role.name.lower() == role_name.lower():
                        found_role = guild_role
                        break
                
                if found_role:
                    # Get members with this role who aren't already participants
                    role_members = [member for member in found_role.members if member not in participants]
                    role_users.extend(role_members)
            
            # Remove duplicates and shuffle
            role_users = list(set(role_users))
            random.shuffle(role_users)
            
            # Add role users to participants (respect warrior limit)
            needed = warriors - len(participants)
            if needed > 0:
                participants.extend(role_users[:needed])
        
        # Fill remaining slots with server members if needed
        if len(participants) < warriors:
            remaining = warriors - len(participants)
            # Get random members from the server who aren't already participants
            server_members = [member for member in ctx.guild.members if member not in participants]
            if server_members:
                import random
                additional_members = random.sample(server_members, min(remaining, len(server_members)))
                participants.extend(additional_members)
        
        # Include bots if requested
        if bots and len(participants) < warriors:
            remaining = warriors - len(participants)
            # Get bot members from the server who aren't already participants
            bot_members = [member for member in ctx.guild.members if member.bot and member not in participants]
            if bot_members:
                additional_bots = random.sample(bot_members, min(remaining, len(bot_members)))
                participants.extend(additional_bots)
        
        # If still not enough, generate generic names for the remainder
        if len(participants) < warriors:
            remaining = warriors - len(participants)
            generated_names = [f"Warrior-{i+1}" for i in range(remaining)]
            participants.extend(generated_names)
        
        # Trim to exact warrior count
        participants = participants[:warriors]
        
        # Create game session
        game_session = GameSession(participants, self.pools, all_factions=all_factions, starting_factions=starting_factions)
        
        # Create setup embed
        embed = Embed(
            title="⚡ CYBERTRON GAMES SETUP ⚡",
            description="A round-based survival battle on Cybertron. Factions cluster and cooperate to eliminate outsiders first. Each round schedules all alive warriors into events that either narrate actions or eliminate the entire opposing side. Locations are drawn from Cybertron’s biomes; vehicles and combiners appear based on team sizes. The map updates each round: dots show alive warriors, skulls mark eliminated. Use the buttons to progress rounds or end the game.",
            color=0xffd700,
            timestamp=datetime.now()
        )
        
        embed.add_field(name="🎮 Game Info", value=f"**Warriors:** {warriors}\n**All Factions:** {'ON' if all_factions else 'OFF'}\n**Starting Factions:** {'ON' if starting_factions else 'OFF'}\n**Include Bots:** {'ON' if bots else 'OFF'}\n**Role Selection:** {'ON' if roles else 'OFF'}", inline=False)
        
        # Faction breakdown
        faction_counts = {}
        for participant in participants:
            faction = game_session.assignment.get(participant, 'Neutral')
            faction_counts[faction] = faction_counts.get(faction, 0) + 1
        faction_text = "\n".join([f"**{faction}:** {count} warriors" for faction, count in faction_counts.items()])
        embed.add_field(name="🏛️ Factions", value=faction_text if faction_text else f"**Neutral:** {warriors} warriors", inline=False)
        
        # Get display names for participants
        participant_names = []
        for p in participants:
            if hasattr(p, 'display_name'):
                participant_names.append(p.display_name)
            else:
                participant_names.append(str(p))
        
        embed.add_field(name="⚔️ Participants", value=f"{', '.join(participant_names[:20])}{'...' if len(participant_names) > 20 else ''}", inline=False)

        buf = game_session.render_map()
        file = None
        if buf:
            file = File(buf, filename="cybertron_setup.png")
            embed.set_image(url="attachment://cybertron_setup.png")
        
        embed.set_footer(text="Click Start Game to begin the battle for Cybertron!")
        
        # Create view with buttons
        view = GameSetupView(game_session, ctx)
        
        # Send embed with buttons
        if file:
            message = await ctx.send(embed=embed, view=view, file=file)
        else:
            message = await ctx.send(embed=embed, view=view)
        view.message = message


async def setup(bot: commands.Bot):
    await bot.add_cog(CybertronGames(bot))
    logger.info("✅ Enhanced Cybertron Games cog loaded successfully")
