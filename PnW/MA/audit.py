import discord
from discord.ext import commands
from discord import app_commands
from typing import List, Dict, Any, Optional, Callable, Literal
from datetime import datetime, timezone, timedelta
import logging
import os
import sys
import asyncio
import math

# Prefer vendored local_packages so Treaty Web image deps use them
try:
    _project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    _local_packages = os.path.join(_project_root, 'local_packages')
    if os.path.isdir(_local_packages) and _local_packages not in sys.path:
        sys.path.insert(0, _local_packages)
    # Prevent user site-packages precedence over vendored copies
    os.environ.setdefault('PYTHONNOUSERSITE', '1')
except Exception as _vend_err:
    logging.getLogger('AuditManager').warning(f"Vendored path setup failed: {_vend_err}")

# Optional dependencies for image processing and HTTP fetch
try:
    import aiohttp  # type: ignore
    import io  # type: ignore
    from PIL import Image, ImageOps, ImageDraw, ImageFont  # type: ignore
except Exception:
    aiohttp = None
    io = None
    Image = None
    ImageOps = None
    ImageDraw = None
    ImageFont = None

# Ensure parent paths for config import
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import (
    CYBERTRON_ALLIANCE_ID,
    GRUMP_USER_ID,
    ARIES_USER_ID,
    PRIMAL_USER_ID,
    CARNAGE_USER_ID,
    BENEVOLENT_USER_ID,
    TECH_USER_ID,
    get_role_ids,
    get_guild_id_from_context,
)

# Optional import of AERO bloc definitions
try:
    from Systems.PnW.MA.bloc import AERO_ALLIANCES  # type: ignore
except Exception:
    AERO_ALLIANCES = {}

LEADERSHIP_USER_IDS = {
    uid for uid in [
        GRUMP_USER_ID,
        ARIES_USER_ID,
        PRIMAL_USER_ID,
        CARNAGE_USER_ID,
        BENEVOLENT_USER_ID,
        TECH_USER_ID,
    ] if uid and uid != 0
}


def _nation_link(n: Dict[str, Any]) -> str:
    """Return markdown link to a nation's PnW page."""
    nid = n.get('nation_id') or n.get('id') or n.get('nationid')
    name = (n.get('nation_name') or n.get('name') or 'Unknown').strip()
    try:
        nid_str = str(int(nid)) if nid is not None else ''
    except Exception:
        nid_str = str(nid) if nid is not None else ''
    url = f"https://politicsandwar.com/nation/id={nid_str}" if nid_str else "https://politicsandwar.com/nation/"
    return f"[{name}]({url})"


def _days_inactive(n: Dict[str, Any]) -> Optional[int]:
    """Compute days since last_active from a nation dict."""
    s = n.get('last_active')
    if not s:
        return None
    try:
        # Normalize common formats; handle 'Z' and missing timezone
        if isinstance(s, str):
            last = s.strip()
            if last.endswith('Z'):
                last = last.replace('Z', '+00:00')
            # If there's no timezone part, assume UTC
            if '+' not in last and last.count(':') >= 2:
                last += '+00:00'
            dt = datetime.fromisoformat(last)
        else:
            dt = s
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        now = datetime.now(timezone.utc)
        return (now - dt).days
    except Exception:
        return None


class AuditManager(commands.Cog):
    """Cog to audit alliance nations and surface issues in an embed."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cybertron_id = CYBERTRON_ALLIANCE_ID
        # Track the last posted treaties message per channel to edit instead of posting new
        self.treaties_message_map: Dict[int, int] = {}

    # Dynamic autocomplete for mmr_mode: only suggest when view=="mmr"
    async def _mmr_mode_autocomplete(self, interaction: discord.Interaction, current: str):
        try:
            view_sel = getattr(interaction.namespace, 'view', None)
        except Exception:
            view_sel = None
        if view_sel == 'mmr':
            base = [
                app_commands.Choice(name="Basic", value="basic"),
                app_commands.Choice(name="Max", value="max"),
            ]
            cur = (current or "").lower()
            if cur:
                return [c for c in base if (cur in c.name.lower()) or (cur in c.value)]
            return base
        # When not in MMR view, no suggestions (keeps UI clean)
        return []

    # Autocomplete for treaties command alliance argument
    async def _treaties_alliance_autocomplete(self, interaction: discord.Interaction, current: str):
        try:
            cur = (current or "").strip().lower()
            choices: List[app_commands.Choice[str]] = []

            # Numeric ID direct entry
            if cur.isdigit():
                choices.append(app_commands.Choice(name=f"Alliance ID {current}", value=current))

            # Suggest Cybertr0n explicitly
            if (not cur) or ("cyber" in cur):
                try:
                    choices.append(app_commands.Choice(name="Cybertr0n", value=str(int(self.cybertron_id))))
                except Exception:
                    choices.append(app_commands.Choice(name="Cybertr0n", value=str(self.cybertron_id)))

            # Suggest from known AERO alliances if available
            try:
                seen = set()
                for k, v in (AERO_ALLIANCES or {}).items():
                    name = (v.get('name') or '').strip()
                    acr = (v.get('acr') or v.get('acronym') or '').strip()
                    aid = ''
                    try:
                        aid = str(int(v.get('id') or 0))
                    except Exception:
                        aid = str(v.get('id') or '')
                    disp = (f"{name} ({acr})" if acr else name).strip()
                    # Name/acronym match
                    if disp and ((not cur) or (cur in disp.lower())):
                        key = (disp, name)
                        if key not in seen:
                            choices.append(app_commands.Choice(name=disp[:100], value=name or disp))
                            seen.add(key)
                    # ID match
                    if aid and ((cur and cur in aid) or cur.isdigit()):
                        key = (aid, aid)
                        if key not in seen:
                            nm = disp or (f"Alliance {aid}")
                            choices.append(app_commands.Choice(name=f"{nm} [ID {aid}]"[:100], value=aid))
                            seen.add(key)
            except Exception:
                pass

            # Limit to 25
            return choices[:25]
        except Exception:
            return []

    async def _fetch_flag_image(self, url: str) -> Optional["Image.Image"]:
        """Download an image from URL and return a PIL Image, or None on failure.
        This is safe to call even if Pillow/aiohttp are unavailable; it will return None.
        """
        try:
            if not url:
                return None
            if aiohttp is None or Image is None or io is None:
                # Dependencies not available; skip image processing
                return None
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.read()
            bio = io.BytesIO(data)
            img = Image.open(bio)
            return img
        except Exception:
            return None

    def _normalize_treaty_type(self, ttype: str) -> str:
        """Normalize various treaty type labels/abbreviations to canonical keys.
        Returns one of: 'MDP', 'MDoAP', 'ODP', 'ODoAP', 'Protectorate', 'NAP', 'PIAT', 'Extension'.
        """
        s = (ttype or '').strip().lower()
        s_compact = s.replace(' ', '').replace('-', '')
        # Direct abbreviation hits
        if s_compact in {"mdp"} or s.startswith("mutual defense"):
            return "MDP"
        if s_compact in {"mdoap"} or s.startswith("mutual defense/optional aggression") or s_compact in {"mutualdefenseoptionalaggression"}:
            return "MDoAP"
        if s_compact in {"odp"} or s.startswith("optional defense"):
            return "ODP"
        if s_compact in {"odoap"} or s.startswith("optional defense/optional aggression") or s_compact in {"optionaldefenseoptionalaggression"}:
            return "ODoAP"
        if s_compact in {"protectorate", "prot"}:
            return "Protectorate"
        if s_compact in {"nap"} or s.startswith("non-aggression") or s.startswith("no aggression"):
            return "NAP"
        if s_compact in {"piat"} or s.startswith("peace, intelligence and aid"):
            return "PIAT"
        if s_compact in {"extension", "ext"} or s.startswith("extension"):
            return "Extension"
        # Fallback to original for unknown types
        return ttype.strip() or ""

    def _resize_flag_image(self, img: "Image.Image", size: tuple[int, int] = (24, 24)) -> Optional["Image.Image"]:
        """Resize the given PIL image to size, maintaining aspect ratio and adding padding if needed."""
        try:
            if Image is None or ImageOps is None:
                return None
            # Convert to RGBA for consistent output
            if img.mode not in ("RGBA", "LA"):
                img = img.convert("RGBA")
            # Fit into target box, maintain aspect
            resized = ImageOps.contain(img, size)
            # Pad to exact size
            out = Image.new("RGBA", size, (0, 0, 0, 0))
            ox = (size[0] - resized.width) // 2
            oy = (size[1] - resized.height) // 2
            # Use resized as mask to preserve transparency
            out.paste(resized, (ox, oy), resized)
            return out
        except Exception:
            return None

    async def _compose_treaty_web_image(self, treaties: List[Dict[str, Any]], center_alliance_id: Optional[int] = None) -> Optional[discord.File]:
        """
        Create the treaty web image using pulled alliance flags with three tiers:
        - Center: Cybertron flag
        - Inner ring: Protectorates and Extensions (and Prime Bank closest to center)
        - Middle ring: AERO Bloc alliances (closed loop ring)
        - Outer ring: All other treaties (connected only to Cybertron)
        Returns a discord.File attachment (PNG) or None if dependencies are missing.
        """
        if Image is None or ImageDraw is None or io is None:
            return None

        # Gather treaty partners, their treaty types, and center alliance flag
        cy_flag_url: Optional[str] = None
        partners: List[Dict[str, Any]] = []
        partner_types: Dict[int, set] = {}

        # Determine center alliance id (default to Cybertron)
        try:
            center_id = int(center_alliance_id if center_alliance_id is not None else int(self.cybertron_id))
        except Exception:
            center_id = int(self.cybertron_id)

        # Identify AERO alliance IDs and Prime Bank (include prime bank specially)
        try:
            aero_ids = {
                int(v.get('id')) for k, v in (AERO_ALLIANCES or {}).items()
                if v and v.get('id')
            }
            prime_bank_id = 0
            if isinstance(AERO_ALLIANCES, dict) and 'prime_bank' in AERO_ALLIANCES:
                try:
                    prime_bank_id = int(AERO_ALLIANCES['prime_bank'].get('id') or 0)
                except Exception:
                    prime_bank_id = 0
        except Exception:
            aero_ids = set()
            prime_bank_id = 0

        for t in treaties or []:
            a1 = t.get('alliance1') or {}
            a2 = t.get('alliance2') or {}
            a1_id = int(str(a1.get('id') or t.get('alliance1_id') or 0)) if (a1.get('id') or t.get('alliance1_id')) else 0
            a2_id = int(str(a2.get('id') or t.get('alliance2_id') or 0)) if (a2.get('id') or t.get('alliance2_id')) else 0
            ttype = self._normalize_treaty_type(t.get('treaty_type') or '')

            # Capture center alliance flag URL from either side
            if a1_id == center_id:
                if not cy_flag_url:
                    cy_flag_url = (a1.get('flag') or '').strip()
                other = a2
                other_id = a2_id
            elif a2_id == center_id:
                if not cy_flag_url:
                    cy_flag_url = (a2.get('flag') or '').strip()
                other = a1
                other_id = a1_id
            else:
                continue

            if other_id and other_id != center_id:
                partners.append({
                    'id': other_id,
                    'name': (other.get('name') or 'Unknown').strip(),
                    'acr': (other.get('acronym') or '').strip(),
                    'flag_url': (other.get('flag') or '').strip(),
                })
                # Track treaty types per partner for layout grouping
                if ttype:
                    partner_types.setdefault(other_id, set()).add(ttype)

        # Split partners into AERO vs non-AERO and dedupe by id
        seen = set()
        aero_partners: List[Dict[str, Any]] = []
        inner_partners: List[Dict[str, Any]] = []  # Protectorates & Extensions
        non_aero_partners: List[Dict[str, Any]] = []
        prime_bank_entry: Optional[Dict[str, Any]] = None
        # Only show a dedicated AERO circle when center is Cybertron or an AERO member
        show_aero_circle = (center_id == int(self.cybertron_id)) or (center_id in aero_ids)

        for p in partners:
            pid = int(p.get('id') or 0)
            if not pid or pid in seen:
                continue
            seen.add(pid)
            if pid == prime_bank_id:
                prime_bank_entry = p
            else:
                # Inner ring if partner has Protectorate/Extension
                types = partner_types.get(pid) or set()
                if ('Protectorate' in types) or ('Extension' in types):
                    inner_partners.append(p)
                elif pid in aero_ids and show_aero_circle:
                    aero_partners.append(p)
                else:
                    # Only include non-AERO partners with specific treaty types for outer ring
                    target_types = {'MDoAP', 'MDP', 'ODoAP', 'ODP', 'PIAT', 'NAP'}
                    if types & target_types:  # Has at least one of the target treaty types
                        non_aero_partners.append(p)

        # Center flag size
        CENTER_SIZE = 80  # Slightly smaller center flag

        # Fetch and place center alliance flag
        cy_img = await self._fetch_flag_image(cy_flag_url or '')
        if cy_img:
            cy_img = self._resize_flag_image(cy_img, (CENTER_SIZE, CENTER_SIZE))

        # Helper to fetch and resize list of flags (with placeholder if missing)
        async def fetch_resized(list_items: List[Dict[str, Any]], size: int) -> List[Dict[str, Any]]:
            tasks = [self._fetch_flag_image(p.get('flag_url') or '') for p in list_items]
            raws = await asyncio.gather(*tasks) if tasks else []
            out: List[Dict[str, Any]] = []
            for i, raw in enumerate(raws):
                if raw:
                    resized = self._resize_flag_image(raw, (size, size))
                else:
                    # Create a simple placeholder if flag missing
                    ph = Image.new("RGBA", (size, size), (40, 40, 40, 200)) if Image else None
                    if ph is not None:
                        d = ImageDraw.Draw(ph)
                        text = (list_items[i].get('acr') or list_items[i].get('name') or "?")
                        text = (text[:3] or "?").upper()
                        try:
                            # center text roughly
                            tw, th = d.textsize(text)
                            d.text(((size - tw) // 2, (size - th) // 2), text, fill=(255, 255, 255, 220))
                        except Exception:
                            d.text((size // 4, size // 3), text, fill=(255, 255, 255, 220))
                    resized = ph
                item = dict(list_items[i])
                item['img'] = resized
                out.append(item)
            return out

        # Annotate items with a line_type for coloring by treaty type
        def choose_outer_type(types: set) -> str:
            order = ['MDoAP', 'MDP', 'ODoAP', 'ODP', 'PIAT', 'NAP']
            for t in order:
                if t in types:
                    return t
            return 'MDP' if 'MDP' in types else (next(iter(types)) if types else 'MDP')

        inner_annotated: List[Dict[str, Any]] = []
        for p in inner_partners:
            pid = int(p.get('id') or 0)
            types = partner_types.get(pid) or set()
            lt = 'Protectorate' if 'Protectorate' in types else 'Extension'
            item = dict(p)
            item['line_type'] = lt
            inner_annotated.append(item)

        aero_annotated = []
        for p in aero_partners:
            item = dict(p)
            item['line_type'] = 'AERO'
            aero_annotated.append(item)

        non_annotated: List[Dict[str, Any]] = []
        for p in non_aero_partners:
            pid = int(p.get('id') or 0)
            types = partner_types.get(pid) or set()
            lt = choose_outer_type(types)
            item = dict(p)
            item['line_type'] = lt
            non_annotated.append(item)

        # Split non-AERO partners into distinct treaty-type groups for separate rings
        non_by_type: Dict[str, List[Dict[str, Any]]] = {
            'MDoAP': [], 'MDP': [], 'ODoAP': [], 'ODP': [], 'PIAT': [], 'NAP': []
        }
        for item in non_annotated:
            lt = item.get('line_type') or ''
            if lt in non_by_type:
                non_by_type[lt].append(item)

        # Reduced flag sizes to prevent overlaps with many flags on rings
        inner_items = await fetch_resized(inner_annotated, 48)  # Smaller for inner ring with many flags
        aero_items = await fetch_resized(aero_annotated, 56)    # Medium for AERO ring
        # Resize per treaty type for outer rings
        mdoap_items = await fetch_resized(non_by_type['MDoAP'], 52)
        mdp_items   = await fetch_resized(non_by_type['MDP'],   52)
        odoap_items = await fetch_resized(non_by_type['ODoAP'], 52)
        odp_items   = await fetch_resized(non_by_type['ODP'],   52)
        piat_items  = await fetch_resized(non_by_type['PIAT'],  52)
        nap_items   = await fetch_resized(non_by_type['NAP'],   52)
        if prime_bank_entry:
            prime_item = dict(prime_bank_entry)
            prime_item['line_type'] = 'AERO'
            prime_items = await fetch_resized([prime_item], 60)  # Slightly larger for Prime Bank
            prime_img = prime_items[0].get('img') if prime_items else None
        else:
            prime_img = None

        # Assign unique angles across all flags to avoid overlapping radials
        used_angles: set = set()

        def _norm_angle(a: float) -> float:
            while a < 0:
                a += 2 * math.pi
            while a >= 2 * math.pi:
                a -= 2 * math.pi
            return a

        def reserve_angles(items: List[Dict[str, Any]], base_offset: float) -> None:
            n = len(items)
            if n <= 0:
                return
            step = (2 * math.pi) / n
            jitter_step = math.pi / 180 * 2  # 2 degrees if collision
            for i, it in enumerate(items):
                angle = _norm_angle(base_offset + step * i)
                tries = 0
                key = round(angle, 5)
                while key in used_angles and tries < 180:
                    angle = _norm_angle(angle + jitter_step)
                    key = round(angle, 5)
                    tries += 1
                used_angles.add(key)
                it['angle'] = angle

        # Define ring radii and dynamically size canvas to ensure all flags fit
        INNER_RADIUS = 180                     # inner ring for protectorates/extensions
        AERO_RADIUS  = 280                     # AERO ring radius
        PRIME_RADIUS = 120                     # Prime Bank closest to center
        # Outer rings by treaty type in ordered distances
        MDOAP_RADIUS = 320
        MDP_RADIUS   = 360
        ODOAP_RADIUS = 400
        ODP_RADIUS   = 440
        PIAT_RADIUS  = 480
        NAP_RADIUS   = 520

        def compute_required_radius(items: List[Dict[str, Any]], base_radius: int) -> int:
            n = len(items)
            if n == 0:
                return base_radius
            max_flag_size = max((it.get('img').width if it.get('img') else 48) for it in items) if items else 48
            min_arc_length = max_flag_size + 8
            min_angle_sep = min_arc_length / float(base_radius)
            required_angle = min_angle_sep * n
            if required_angle > 2 * math.pi:
                return int(min_arc_length * n / (2 * math.pi)) + 10
            return base_radius

        INNER_RADIUS = compute_required_radius(inner_items, INNER_RADIUS)
        AERO_RADIUS  = compute_required_radius(aero_items,  AERO_RADIUS)
        MDOAP_RADIUS = compute_required_radius(mdoap_items, MDOAP_RADIUS)
        MDP_RADIUS   = compute_required_radius(mdp_items,   MDP_RADIUS)
        ODOAP_RADIUS = compute_required_radius(odoap_items, ODOAP_RADIUS)
        ODP_RADIUS   = compute_required_radius(odp_items,   ODP_RADIUS)
        PIAT_RADIUS  = compute_required_radius(piat_items,  PIAT_RADIUS)
        NAP_RADIUS   = compute_required_radius(nap_items,   NAP_RADIUS)

        MARGIN = 28
        def half_size(items: List[Dict[str, Any]]) -> int:
            try:
                return max(((it.get('img').width or 0) // 2) for it in items) if items else 0
            except Exception:
                return 0

        max_extent = max([
            INNER_RADIUS + half_size(inner_items),
            AERO_RADIUS  + half_size(aero_items),
            MDOAP_RADIUS + half_size(mdoap_items),
            MDP_RADIUS   + half_size(mdp_items),
            ODOAP_RADIUS + half_size(odoap_items),
            ODP_RADIUS   + half_size(odp_items),
            PIAT_RADIUS  + half_size(piat_items),
            NAP_RADIUS   + half_size(nap_items),
            PRIME_RADIUS + (prime_img.width // 2 if prime_img else 0),
        ])
        CANVAS_SIZE = max(800, int(2 * (max_extent + MARGIN)))
        CENTER_X, CENTER_Y = CANVAS_SIZE // 2, CANVAS_SIZE // 2

        # Prepare offsets now that angles are reserved
        inner_offset = 0.0
        aero_offset = math.pi / max(1, len(aero_items) + 1)
        # Distinct base offsets for each outer ring to distribute around the circle
        mdoap_offset = math.pi / 6
        mdp_offset   = math.pi / 5
        odoap_offset = math.pi / 4
        odp_offset   = math.pi / 3
        piat_offset  = math.pi / 2.5
        nap_offset   = math.pi / 2

        reserve_angles(inner_items, inner_offset)
        reserve_angles(aero_items, aero_offset)
        reserve_angles(mdoap_items, mdoap_offset)
        reserve_angles(mdp_items, mdp_offset)
        reserve_angles(odoap_items, odoap_offset)
        reserve_angles(odp_items, odp_offset)
        reserve_angles(piat_items, piat_offset)
        reserve_angles(nap_items, nap_offset)

        # Compute positions around circle with collision avoidance
        def place_circle(items: List[Dict[str, Any]], radius: int) -> List[Dict[str, Any]]:
            n = len(items)
            placed: List[Dict[str, Any]] = []
            if n == 0:
                return placed
            
            # Calculate minimum angular separation needed to prevent overlaps
            max_flag_size = max((it.get('img').width if it.get('img') else 48) for it in items) if items else 48
            min_arc_length = max_flag_size + 8  # 8px padding between flags
            min_angle_sep = min_arc_length / radius
            
            # Ensure we have enough space - if not, increase radius dynamically
            required_angle = min_angle_sep * n
            if required_angle > 2 * math.pi:
                # Need to increase radius for this ring
                radius = int(min_arc_length * n / (2 * math.pi)) + 10
            
            for i, it in enumerate(items):
                angle = it.get('angle') if it.get('angle') is not None else (2 * math.pi * i / n)
                img_width = it.get('img').width if it.get('img') else 48
                img_height = it.get('img').height if it.get('img') else 48
                x = CENTER_X + int(radius * math.cos(angle)) - img_width // 2
                y = CENTER_Y + int(radius * math.sin(angle)) - img_height // 2
                it['pos'] = (x, y)
                it['angle'] = angle
                placed.append(it)
            return placed

        # Place inner ring (Protectorates/Extensions) inside AERO ring
        inner_placed = place_circle(inner_items, INNER_RADIUS)
        # Place AERO ring
        aero_placed = place_circle(aero_items, AERO_RADIUS)
        # Place outer rings by treaty type in ordered distances
        mdoap_placed = place_circle(mdoap_items, MDOAP_RADIUS)
        mdp_placed   = place_circle(mdp_items,   MDP_RADIUS)
        odoap_placed = place_circle(odoap_items, ODOAP_RADIUS)
        odp_placed   = place_circle(odp_items,   ODP_RADIUS)
        piat_placed  = place_circle(piat_items,  PIAT_RADIUS)
        nap_placed   = place_circle(nap_items,   NAP_RADIUS)

        # Create canvas and draw straight connection lines from Cybertron center to each flag
        canvas = Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        LINE_WIDTH = 2
        cy_center = (CENTER_X, CENTER_Y)
        # Color mapping by treaty type
        COLOR_MAP: Dict[str, tuple] = {
            'Protectorate': (50, 205, 50, 200),  # green
            'Extension':    (50, 205, 50, 200),  # green
            'AERO':         (0, 122, 255, 200),  # blue
            'MDoAP':        (0, 122, 255, 200),  # blue
            'MDP':          (128, 0, 128, 200),  # purple
            'ODoAP':        (255, 0, 0, 200),    # red
            'ODP':          (255, 165, 0, 200),  # orange
            'PIAT':         (255, 255, 0, 200),  # yellow
            'NAP':          (165, 42, 42, 200),  # brown
        }

        def pick_line_color(line_type: Optional[str]) -> tuple:
            return COLOR_MAP.get(line_type or '', (255, 255, 255, 180))

        # Inner ring: straight lines
        for it in inner_placed:
            img_obj = it.get('img')
            pos = it.get('pos') or (CENTER_X, CENTER_Y)
            cx = pos[0] + (img_obj.width // 2 if img_obj else 0)
            cy = pos[1] + (img_obj.height // 2 if img_obj else 0)
            draw.line([cy_center, (cx, cy)], fill=pick_line_color(it.get('line_type')), width=LINE_WIDTH)

        # AERO ring: straight lines and connect adjacent items to form closed loop
        for it in aero_placed:
            img_obj = it.get('img')
            pos = it.get('pos') or (CENTER_X, CENTER_Y)
            cx = pos[0] + (img_obj.width // 2 if img_obj else 0)
            cy = pos[1] + (img_obj.height // 2 if img_obj else 0)
            draw.line([cy_center, (cx, cy)], fill=pick_line_color('AERO'), width=LINE_WIDTH)

        if len(aero_placed) >= 2:
            for i in range(len(aero_placed)):
                a = aero_placed[i]
                b = aero_placed[(i + 1) % len(aero_placed)]
                ax, ay = a['pos'][0] + (a['img'].width // 2 if a.get('img') else 0), a['pos'][1] + (a['img'].height // 2 if a.get('img') else 0)
                bx, by = b['pos'][0] + (b['img'].width // 2 if b.get('img') else 0), b['pos'][1] + (b['img'].height // 2 if b.get('img') else 0)
                draw.line([(ax, ay), (bx, by)], fill=pick_line_color('AERO'), width=LINE_WIDTH)

        # Draw outer rings: straight lines per treaty type
        for it in mdoap_placed:
            img_obj = it.get('img')
            pos = it.get('pos') or (CENTER_X, CENTER_Y)
            cx = pos[0] + (img_obj.width // 2 if img_obj else 0)
            cy = pos[1] + (img_obj.height // 2 if img_obj else 0)
            draw.line([cy_center, (cx, cy)], fill=pick_line_color('MDoAP'), width=LINE_WIDTH)

        for it in mdp_placed:
            img_obj = it.get('img')
            pos = it.get('pos') or (CENTER_X, CENTER_Y)
            cx = pos[0] + (img_obj.width // 2 if img_obj else 0)
            cy = pos[1] + (img_obj.height // 2 if img_obj else 0)
            draw.line([cy_center, (cx, cy)], fill=pick_line_color('MDP'), width=LINE_WIDTH)

        for it in odoap_placed:
            img_obj = it.get('img')
            pos = it.get('pos') or (CENTER_X, CENTER_Y)
            cx = pos[0] + (img_obj.width // 2 if img_obj else 0)
            cy = pos[1] + (img_obj.height // 2 if img_obj else 0)
            draw.line([cy_center, (cx, cy)], fill=pick_line_color('ODoAP'), width=LINE_WIDTH)

        for it in odp_placed:
            img_obj = it.get('img')
            pos = it.get('pos') or (CENTER_X, CENTER_Y)
            cx = pos[0] + (img_obj.width // 2 if img_obj else 0)
            cy = pos[1] + (img_obj.height // 2 if img_obj else 0)
            draw.line([cy_center, (cx, cy)], fill=pick_line_color('ODP'), width=LINE_WIDTH)

        for it in piat_placed:
            img_obj = it.get('img')
            pos = it.get('pos') or (CENTER_X, CENTER_Y)
            cx = pos[0] + (img_obj.width // 2 if img_obj else 0)
            cy = pos[1] + (img_obj.height // 2 if img_obj else 0)
            draw.line([cy_center, (cx, cy)], fill=pick_line_color('PIAT'), width=LINE_WIDTH)

        for it in nap_placed:
            img_obj = it.get('img')
            pos = it.get('pos') or (CENTER_X, CENTER_Y)
            cx = pos[0] + (img_obj.width // 2 if img_obj else 0)
            cy = pos[1] + (img_obj.height // 2 if img_obj else 0)
            draw.line([cy_center, (cx, cy)], fill=pick_line_color('NAP'), width=LINE_WIDTH)

        # Prime Bank: place inside AERO ring and connect to Cybertron
        if prime_img is not None:
            # Place Prime Bank with a unique angle away from others
            prime_angle = _norm_angle(math.pi / 7)
            key = round(prime_angle, 5)
            jitter_step = math.pi / 180 * 3
            tries = 0
            while key in used_angles and tries < 180:
                prime_angle = _norm_angle(prime_angle + jitter_step)
                key = round(prime_angle, 5)
                tries += 1
            used_angles.add(key)
            px = CENTER_X + int(PRIME_RADIUS * math.cos(prime_angle)) - prime_img.width // 2
            py = CENTER_Y + int(PRIME_RADIUS * math.sin(prime_angle)) - prime_img.height // 2
            # Connect straight line to Cybertron (treat as AERO color)
            draw.line([cy_center, (px + prime_img.width // 2, py + prime_img.height // 2)], fill=pick_line_color('AERO'), width=LINE_WIDTH)

        # Paste flags (order: inner ring, AERO ring, outer rings, Prime, Cybertron)
        for it in inner_placed:
            if it.get('img') is not None:
                canvas.paste(it['img'], it['pos'], it['img'])
        for it in aero_placed:
            if it.get('img') is not None:
                canvas.paste(it['img'], it['pos'], it['img'])
        # Outer rings
        for it in mdoap_placed:
            if it.get('img') is not None:
                canvas.paste(it['img'], it['pos'], it['img'])
        for it in mdp_placed:
            if it.get('img') is not None:
                canvas.paste(it['img'], it['pos'], it['img'])
        for it in odoap_placed:
            if it.get('img') is not None:
                canvas.paste(it['img'], it['pos'], it['img'])
        for it in odp_placed:
            if it.get('img') is not None:
                canvas.paste(it['img'], it['pos'], it['img'])
        for it in piat_placed:
            if it.get('img') is not None:
                canvas.paste(it['img'], it['pos'], it['img'])
        for it in nap_placed:
            if it.get('img') is not None:
                canvas.paste(it['img'], it['pos'], it['img'])
        # Prime Bank image
        if prime_img is not None:
            canvas.paste(prime_img, (px, py), prime_img)

        # Paste Cybertron last in center
        if cy_img is not None:
            canvas.paste(cy_img, (CENTER_X - CENTER_SIZE // 2, CENTER_Y - CENTER_SIZE // 2), cy_img)

        # Export PNG to buffer
        buf = io.BytesIO()
        canvas.save(buf, format='PNG')
        buf.seek(0)
        return discord.File(buf, filename="treaty_web.png")

    async def _compose_category_image(self, items: List[Dict[str, Any]], title: str, alliance_id: int, row_height: int = 28) -> Optional[discord.File]:
        """Compose a simple image for a category: each row shows a resized flag followed by alliance name.
        Returns a discord.File attachment or None if dependencies are missing or an error occurs.
        """
        try:
            if Image is None or ImageDraw is None or ImageFont is None:
                return None
            font = ImageFont.load_default()
            # Build rows info: (flag_img, text)
            rows: List[tuple[Optional["Image.Image"], str]] = []
            for t in items:
                a1 = t.get('alliance1') or {}
                a2 = t.get('alliance2') or {}
                a1_id = int(str(a1.get('id') or t.get('alliance1_id') or 0)) if (a1.get('id') or t.get('alliance1_id')) else 0
                other = a2 if a1_id == int(alliance_id) else a1
                name = (other.get('name') or 'Unknown').strip()
                acr = (other.get('acronym') or '').strip()
                text = f"{name} ({acr})" if acr else name
                flag_url = (other.get('flag') or '').strip()
                img = await self._fetch_flag_image(flag_url)
                if img is not None:
                    img = self._resize_flag_image(img, (24, 24))
                rows.append((img, text))

            # Determine image width by measuring text
            max_text_w = 0
            for _, text in rows:
                w, _ = font.getsize(text)
                if w > max_text_w:
                    max_text_w = w
            # Image width: padding + flag(24) + gap + text + padding
            padding = 8
            gap = 8
            width = padding + 24 + gap + max_text_w + padding
            # Title height
            title_h = font.getsize(title)[1] + padding
            # Total height: title + rows * row_height + padding
            height = title_h + len(rows) * row_height + padding
            # Create canvas
            canvas = Image.new("RGBA", (max(width, 200), max(height, 50)), (255, 255, 255, 0))
            draw = ImageDraw.Draw(canvas)
            # Draw title
            draw.text((padding, padding // 2), title, fill=(255, 255, 255, 255), font=font)
            # Draw rows
            y = title_h
            for img, text in rows:
                # Flag
                if img is not None:
                    canvas.paste(img, (padding, y + (row_height - img.height) // 2), img)
                # Text
                draw.text((padding + 24 + gap, y + (row_height - font.getsize(text)[1]) // 2), text, fill=(255, 255, 255, 255), font=font)
                y += row_height

            # Save to buffer as PNG
            if io is None:
                return None
            buf = io.BytesIO()
            canvas.save(buf, format='PNG')
            buf.seek(0)
            # Filename based on title
            safe_name = ''.join(c for c in title if c.isalnum()).lower() or "category"
            file = discord.File(buf, filename=f"treaties_{safe_name}.png")
            return file
        except Exception:
            return None

    async def _get_alliance_nations(self, alliance_id: int, force_refresh: bool = True) -> List[Dict[str, Any]]:
        """Use AllianceManager cog if available to fetch nations; otherwise return empty list."""
        try:
            alliance_cog = self.bot.get_cog('AllianceManager')
            if alliance_cog and hasattr(alliance_cog, 'get_alliance_nations'):
                # AllianceManager signature supports (alliance_id, force_refresh=True)
                nations_raw = await alliance_cog.get_alliance_nations(str(alliance_id), force_refresh=force_refresh)
                # Support both list and dict payloads
                if isinstance(nations_raw, dict):
                    nations_list = nations_raw.get('nations', []) or []
                else:
                    nations_list = nations_raw or []
                return nations_list
        except Exception as e:
            self.logger.error(f"Error fetching alliance nations for {alliance_id}: {e}")
        return []

    async def _get_combined_nations(self) -> List[Dict[str, Any]]:
        """Fetch nations from Cybertron only."""
        cy = await self._get_alliance_nations(self.cybertron_id, force_refresh=True)
        # AllianceManager returns nations for the specific alliance; no extra filter needed.
        return cy or []

    def _filter_active_members(self, nations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Exclude applicants and vacation mode for resource checks."""
        active = []
        for n in nations:
            pos = (n.get('alliance_position', '') or '').strip().upper()
            if pos == 'APPLICANT':
                continue
            vm = int(n.get('vacation_mode_turns', 0) or 0)
            if vm > 0:
                continue
            active.append(n)
        return active

    def _format_treaties_chunks(self, treaties: List[Dict[str, Any]]) -> List[str]:
        """Format treaties into plain-text chunks under 2000 chars, grouped by type.
        - Shows all treaties
        - Suppresses link embeds via angle-bracketed URLs
        - No counts in headers, no repeated treaty type per item
        """
        # Default center to Cybertron for plain-text output
        try:
            center_id = int(self.cybertron_id)
        except Exception:
            center_id = 0
        categories = [
            ("Protectorate", "🟢", "Protectorate"),
            ("Extension", "🟢", "Extension"),
            ("MDoAP", "🔵", "Mutual Defense / Optional Aggression (MDoAP)"),
            ("MDP", "🟣", "Mutual Defense (MDP)"),
            ("ODoAP", "🔴", "Optional Defense / Optional Aggression (ODoAP)"),
            ("ODP", "🟠", "Optional Defense (ODP)"),
            ("PIAT", "🟡", "Peace, Intelligence and Aid (PIAT)"),
            ("NAP", "🟤", "Non-Aggression Pact (NAP)"),
        ]

        by_type: Dict[str, List[Dict[str, Any]]] = {}
        for t in treaties or []:
            ttype = self._normalize_treaty_type(t.get('treaty_type') or '')
            if not ttype:
                continue
            by_type.setdefault(ttype, []).append(t)

        # If no treaties, return a single message
        if not by_type:
            return ["No treaties found."]

        messages: List[str] = []
        current = ""
        max_len = 1900

        def add_line(line: str):
            nonlocal current, messages
            add = ("\n" if current else "") + line
            if len(current) + len(add) > max_len:
                if current:
                    messages.append(current)
                current = line
            else:
                current += add

        # AERO Bloc category first (excluding Prime Bank)
        try:
            aero_ids = {
                int(v.get('id')) for k, v in (AERO_ALLIANCES or {}).items()
                if k != 'prime_bank' and v and v.get('id')
            }
        except Exception:
            aero_ids = set()

        # Only show a dedicated AERO section when center is Cybertron or an AERO member
        show_aero_section = (center_id in aero_ids) or (center_id == int(self.cybertron_id))

        # Only show AERO if there are items
        aero_seen = set()
        aero_items: List[str] = []
        if show_aero_section:
            for t in (treaties or []):
                a1 = t.get('alliance1') or {}
                a2 = t.get('alliance2') or {}
                a1_id = int(str(a1.get('id') or t.get('alliance1_id') or 0)) if (a1.get('id') or t.get('alliance1_id')) else 0
                a2_id = int(str(a2.get('id') or t.get('alliance2_id') or 0)) if (a2.get('id') or t.get('alliance2_id')) else 0
                other = a2 if a1_id == center_id else a1
                other_id = a2_id if a1_id == center_id else a1_id
                if other_id and other_id in aero_ids and other_id not in aero_seen:
                    other_name = (other.get('name') or 'Unknown').strip()
                    other_acr = (other.get('acronym') or '').strip()
                    disp = f"{other_name} ({other_acr})" if other_acr else other_name
                    url = f"https://politicsandwar.com/alliance/id={other_id}"
                    aero_items.append(f"  - [{disp}](<{url}>)")
                    aero_seen.add(other_id)
            aero_items.sort(key=lambda s: s.lower())
            if aero_items:
                add_line("## 💠 AERO Bloc")
                for line in aero_items:
                    add_line(line)
                add_line("")

        # Then render other categories, excluding AERO alliances
        for ttype, emoji, display in categories:
            items = by_type.get(ttype) or []
            if show_aero_section:
                filtered = []
                for t in items:
                    a1 = t.get('alliance1') or {}
                    a2 = t.get('alliance2') or {}
                    a1_id = int(str(a1.get('id') or t.get('alliance1_id') or 0)) if (a1.get('id') or t.get('alliance1_id')) else 0
                    a2_id = int(str(a2.get('id') or t.get('alliance2_id') or 0)) if (a2.get('id') or t.get('alliance2_id')) else 0
                    other_id = a2_id if a1_id == center_id else a1_id
                    if other_id not in aero_ids:
                        filtered.append(t)
            else:
                filtered = items
            if not filtered:
                continue
            add_line(f"{emoji} {display}")
            for t in filtered:
                a1 = t.get('alliance1') or {}
                a2 = t.get('alliance2') or {}
                a1_id = int(str(a1.get('id') or t.get('alliance1_id') or 0)) if (a1.get('id') or t.get('alliance1_id')) else 0
                a2_id = int(str(a2.get('id') or t.get('alliance2_id') or 0)) if (a2.get('id') or t.get('alliance2_id')) else 0
                other = a2 if a1_id == center_id else a1
                other_name = (other.get('name') or 'Unknown').strip()
                other_acr = (other.get('acronym') or '').strip()
                other_disp = f"{other_name} ({other_acr})" if other_acr else other_name
                other_id = a2_id if a1_id == center_id else a1_id
                pnw_url = f"https://politicsandwar.com/alliance/id={other_id}" if other_id else ""
                if pnw_url:
                    add_line(f"  - [{other_disp}](<{pnw_url}>)")
                else:
                    add_line(f"  - {other_disp}")
            add_line("")

        # (Removed duplicate AERO section)

        if current:
            messages.append(current)
        return messages

    def _format_treaties_embed(self, treaties: List[Dict[str, Any]], center_alliance_id: Optional[int] = None, center_name: Optional[str] = None) -> discord.Embed:
        """Format treaties into a rich Discord embed with proper categories and emojis.
        Uses regular URLs (not angle-bracketed) since embeds don't auto-expand links in embed fields.
        """
        # Determine center id and title
        try:
            center_id = int(center_alliance_id if center_alliance_id is not None else int(self.cybertron_id))
        except Exception:
            center_id = int(self.cybertron_id)

        title = "🤖 Cybertr0nian Treaty Web 📜🕸️" if center_id == int(self.cybertron_id) else f"{(center_name or 'Alliance').strip()} Treaty Web 📜🕸️"

        embed = discord.Embed(
            title=title,
            color=0x00ff00,  # Green color
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text="Last updated")

        # Attempt to set the embed image to Cybertron's flag from treaty data
        try:
            cy_flag_url: Optional[str] = None
            for t in treaties or []:
                a1 = t.get('alliance1') or {}
                a2 = t.get('alliance2') or {}
                a1_id = int(str(a1.get('id') or t.get('alliance1_id') or 0)) if (a1.get('id') or t.get('alliance1_id')) else 0
                a2_id = int(str(a2.get('id') or t.get('alliance2_id') or 0)) if (a2.get('id') or t.get('alliance2_id')) else 0
                source = a1 if a1_id == center_id else (a2 if a2_id == center_id else None)
                if source:
                    flag_url = (source.get('flag') or '').strip()
                    if flag_url:
                        cy_flag_url = flag_url
                        break
            if cy_flag_url and len(cy_flag_url) < 1000:
                embed.set_image(url=cy_flag_url)
        except Exception:
            # Best-effort only; continue without image on failure
            pass

        categories = [
            ("Protectorate", "🟢", "Protectorate"),
            ("Extension", "🟢", "Extension"),
            ("MDoAP", "🔵", "Mutual Defense / Optional Aggression (MDoAP)"),
            ("MDP", "🟣", "Mutual Defense (MDP)"),
            ("ODoAP", "🔴", "Optional Defense / Optional Aggression (ODoAP)"),
            ("ODP", "🟠", "Optional Defense (ODP)"),
            ("PIAT", "🟡", "Peace, Intelligence and Aid (PIAT)"),
            ("NAP", "🟤", "Non-Aggression Pact (NAP)"),
        ]

        # Group treaties by type
        by_type: Dict[str, List[Dict[str, Any]]] = {}
        for t in treaties or []:
            ttype = self._normalize_treaty_type(t.get('treaty_type') or '')
            if not ttype:
                continue
            by_type.setdefault(ttype, []).append(t)

        def other_info(t: Dict[str, Any]) -> Dict[str, Any]:
            a1 = t.get('alliance1') or {}
            a2 = t.get('alliance2') or {}
            a1_id = int(str(a1.get('id') or t.get('alliance1_id') or 0)) if (a1.get('id') or t.get('alliance1_id')) else 0
            other = a2 if a1_id == center_id else a1
            other_id = int(str((a2.get('id') if a1_id == center_id else a1.get('id')) or 0)) if ((a2.get('id') if a1_id == center_id else a1.get('id')) or 0) else 0
            other_name = (other.get('name') or 'Unknown').strip()
            other_acr = (other.get('acronym') or '').strip()
            sort_key = (other_acr or other_name).lower()
            return {
                'id': other_id,
                'name': other_name,
                'acr': other_acr,
                'sort_key': sort_key,
            }

        # Add AERO Bloc category first (excluding Prime Bank)
        try:
            aero_ids = {
                int(v.get('id')) for k, v in (AERO_ALLIANCES or {}).items()
                if k != 'prime_bank' and v and v.get('id')
            }
        except Exception:
            aero_ids = set()

        # Only show a dedicated AERO section when center is Cybertron or an AERO member
        show_aero_section = (center_id in aero_ids) or (center_id == int(self.cybertron_id))

        aero_seen = set()
        aero_lines: List[str] = []
        if show_aero_section:
            for t in treaties or []:
                oi = other_info(t)
                if oi['id'] and oi['id'] in aero_ids and oi['id'] not in aero_seen:
                    disp = f"{oi['name']} ({oi['acr']})" if oi['acr'] else oi['name']
                    pnw_url = f"https://politicsandwar.com/alliance/id={oi['id']}"
                    aero_lines.append(f"[{disp}]({pnw_url})")
                    aero_seen.add(oi['id'])

            aero_lines.sort(key=lambda s: s.lower())
            if aero_lines:
                aero_value = "\n".join(aero_lines)
                if len(aero_value) > 1024:
                    # Split into multiple fields if too long
                    chunks = []
                    current_chunk = ""
                    for line in aero_lines:
                        if len(current_chunk) + len(line) + 1 > 1024:
                            if current_chunk:
                                chunks.append(current_chunk)
                            current_chunk = line
                        else:
                            current_chunk += ("\n" if current_chunk else "") + line
                    if current_chunk:
                        chunks.append(current_chunk)
                    
                    for i, chunk in enumerate(chunks):
                        field_name = f"💠 AERO Bloc" if i == 0 else f"💠 AERO Bloc (cont.)"
                        embed.add_field(name=field_name, value=chunk, inline=False)
                else:
                    embed.add_field(name="💠 AERO Bloc", value=aero_value, inline=False)

        # Add other treaty categories; exclude AERO only when dedicated AERO section is shown
        for ttype, emoji, display in categories:
            items = by_type.get(ttype) or []
            filtered = [t for t in items if other_info(t)['id'] not in aero_ids] if show_aero_section else items
            if not filtered:
                continue
            
            items_sorted = sorted(filtered, key=lambda t: other_info(t)['sort_key'])
            treaty_lines: List[str] = []
            
            for t in items_sorted:
                oi = other_info(t)
                disp = f"{oi['name']} ({oi['acr']})" if oi['acr'] else oi['name']
                pnw_url = f"https://politicsandwar.com/alliance/id={oi['id']}" if oi['id'] else ""
                line = f"[{disp}]({pnw_url})" if pnw_url else f"{disp}"
                treaty_lines.append(line)
            
            if treaty_lines:
                field_value = "\n".join(treaty_lines)
                field_name = f"{emoji} {display} ({len(treaty_lines)})"
                
                if len(field_value) > 1024:
                    # Split into multiple fields if too long
                    chunks = []
                    current_chunk = ""
                    for line in treaty_lines:
                        if len(current_chunk) + len(line) + 1 > 1024:
                            if current_chunk:
                                chunks.append(current_chunk)
                            current_chunk = line
                        else:
                            current_chunk += ("\n" if current_chunk else "") + line
                    if current_chunk:
                        chunks.append(current_chunk)
                    
                    for i, chunk in enumerate(chunks):
                        chunk_name = field_name if i == 0 else f"{emoji} {display} (cont.)"
                        embed.add_field(name=chunk_name, value=chunk, inline=False)
                else:
                    embed.add_field(name=field_name, value=field_value, inline=False)

        # If no treaties found, add a field indicating this
        if not embed.fields:
            embed.add_field(name="📭 No Treaties", value="No treaties found.", inline=False)

        return embed

    def _build_multi_field_values(self, items: List[Dict[str, Any]], with_days: bool = False, suffix_builder: Optional[Callable[[Dict[str, Any]], Optional[str]]] = None) -> List[str]:
        """Build multiple field values to show all nations, splitting across fields when needed.
        
        Returns a list of strings, each under 1024 characters, to display all nations
        across multiple embed fields if necessary.
        """
        try:
            if not items:
                return ["None"]

            links: List[str] = []
            for n in items:
                nid = n.get('nation_id') or n.get('id') or n.get('nationid')
                name = (n.get('nation_name') or n.get('name') or 'Unknown').strip()
                if not nid:
                    continue
                link = f"[{name}](https://politicsandwar.com/nation/id={nid})"
                if with_days:
                    d = _days_inactive(n)
                    if isinstance(d, int):
                        link = f"{link} ({d}d)"
                if suffix_builder is not None:
                    try:
                        suffix = suffix_builder(n)
                        if suffix:
                            link = f"{link} {suffix}"
                    except Exception:
                        # Ignore suffix errors and continue
                        pass
                links.append(link)

            # Sort for stable display
            links.sort(key=lambda x: x.lower())

            if not links:
                return ["None"]

            # Split links into multiple field values, each under 1024 characters
            field_values = []
            current_value = ""
            
            for link in links:
                add = ("\n" if current_value else "") + link
                if len(current_value) + len(add) > 1024:
                    # Current field is full, start a new one
                    if current_value:
                        field_values.append(current_value)
                    current_value = link
                else:
                    current_value += add
            
            # Add the last field if it has content
            if current_value:
                field_values.append(current_value)
            
            return field_values if field_values else ["None"]
            
        except Exception:
            # Fallback to a safe representation if any issue occurs
            safe = [(_nation_link(n)) for n in items]
            text = "\n".join(safe)
            # Split the fallback text into chunks if needed
            if len(text) <= 1024:
                return [text] if text else ["None"]
            
            chunks = []
            while text:
                if len(text) <= 1024:
                    chunks.append(text)
                    break
                # Find the last newline before 1024 chars
                split_pos = text.rfind('\n', 0, 1024)
                if split_pos == -1:
                    split_pos = 1024
                chunks.append(text[:split_pos])
                text = text[split_pos:].lstrip('\n')
            
            return chunks if chunks else ["None"]

    def _add_category_fields(self, embed: discord.Embed, category_name: str, emoji: str, items: List[Dict[str, Any]], with_days: bool = False, suffix_builder: Optional[Callable[[Dict[str, Any]], Optional[str]]] = None):
        """Add one or more fields for a category, splitting across multiple fields if needed."""
        field_values = self._build_multi_field_values(items, with_days=with_days, suffix_builder=suffix_builder)
        
        for i, value in enumerate(field_values):
            if len(field_values) == 1:
                # Single field, use original name
                field_name = f"{emoji} {category_name} ({len(items)})"
            else:
                # Multiple fields, add part numbers
                field_name = f"{emoji} {category_name} ({len(items)}) - Part {i + 1}"
            
            embed.add_field(name=field_name, value=value, inline=False)

    def _chunk_lines(self, lines: List[str], max_len: int = 1024) -> List[str]:
        """Split a list of lines into chunks under Discord's field length limit."""
        chunks: List[str] = []
        current = ""
        for line in lines:
            add = ("\n" if current else "") + line
            if len(current) + len(add) > max_len:
                if current:
                    chunks.append(current)
                current = line
            else:
                current += add
        if current:
            chunks.append(current)
        return chunks or ["None"]

    def _format_treaty_line(self, t: Dict[str, Any], alliance_id: int) -> str:
        """Format a single treaty line with an angle-bracketed raw URL to suppress embeds."""
        try:
            a1 = t.get('alliance1') or {}
            a2 = t.get('alliance2') or {}
            a1_id = int(str(a1.get('id') or t.get('alliance1_id') or 0)) if (a1.get('id') or t.get('alliance1_id')) else 0
            a2_id = int(str(a2.get('id') or t.get('alliance2_id') or 0)) if (a2.get('id') or t.get('alliance2_id')) else 0
            other = a2 if a1_id == int(alliance_id) else a1
            other_name = (other.get('name') or 'Unknown').strip()
            other_acr = (other.get('acronym') or '').strip()
            other_disp = f"{other_name} ({other_acr})" if other_acr else other_name

            # Build masked link with angle-bracketed URL to suppress embeds
            other_id = a2_id if a1_id == int(alliance_id) else a1_id
            name_link = f"[{other_disp}](<https://politicsandwar.com/alliance/id={other_id}>)" if other_id else other_disp
            
            # Return alliance name with suppressed URL
            return name_link
        except Exception:
            return str(t)

    @app_commands.describe(
        view="Select what to display: Food & Uranium, Inactives, Color, or MMR Build",
        mmr_mode="If MMR Build is selected, choose Basic or Max"
    )
    @app_commands.choices(view=[
        app_commands.Choice(name="Food & Uranium", value="resources"),
        app_commands.Choice(name="Inactives", value="inactives"),
        app_commands.Choice(name="Color", value="color"),
        app_commands.Choice(name="MMR Build", value="mmr"),
    ])
    @app_commands.autocomplete(mmr_mode=_mmr_mode_autocomplete)
    @commands.hybrid_command(name="audit", description="Audit alliance issues for Cybertron")
    async def audit_command(self, ctx: commands.Context, view: Literal["resources", "inactives", "color", "mmr"], mmr_mode: Optional[Literal["basic", "max"]] = "basic"):
        """Generate an "Audit Issues" embed listing issue categories as nation links."""
        try:
            # Safely defer for slash invocation; skip for prefix commands
            try:
                if hasattr(ctx, 'interaction') and ctx.interaction and not ctx.interaction.response.is_done():
                    await ctx.interaction.response.defer()
            except Exception:
                pass

            # Inline leadership access check to ensure slash command registers cleanly
            try:
                # Allow by explicit leadership user IDs
                author_id = getattr(getattr(ctx, "author", None), "id", None)
                is_authorized = bool(author_id in LEADERSHIP_USER_IDS)

                # Check IA/MG/HG roles on this server
                if not is_authorized and getattr(ctx, "guild", None):
                    guild_id = get_guild_id_from_context(ctx)
                    role_map = get_role_ids(guild_id)
                    leadership_roles = set(role_map.get("IA", [])) | set(role_map.get("MG", [])) | set(role_map.get("HG", []))
                    member_roles = {role.id for role in getattr(getattr(ctx, "author", None), "roles", [])}
                    is_authorized = bool(leadership_roles and (member_roles & leadership_roles))

                if not is_authorized:
                    embed = discord.Embed(
                        title="❌ Access Denied",
                        description="Only Alliance Leadership can run audit.",
                        color=discord.Color.red()
                    )
                    if hasattr(ctx, 'interaction') and ctx.interaction:
                        await ctx.interaction.followup.send(embed=embed)
                    else:
                        await ctx.reply(embed=embed)
                    return
            except Exception:
                # If any error occurs, fail closed
                if hasattr(ctx, 'interaction') and ctx.interaction:
                    await ctx.interaction.followup.send("❌ Access check failed.")
                else:
                    await ctx.reply("❌ Access check failed.")
                return

            # Pre-refresh Cybertron alliance data before building the audit embed
            try:
                alliance_cog = self.bot.get_cog('AllianceManager')
                if alliance_cog and hasattr(alliance_cog, 'query_system') and getattr(alliance_cog, 'query_system', None):
                    # Use centralized query system to force refresh and persist to alliance file
                    await alliance_cog.query_system.get_alliance_nations(
                        str(getattr(alliance_cog, 'cybertron_alliance_id', self.cybertron_id)),
                        bot=self.bot,
                        force_refresh=True
                    )
                elif alliance_cog and hasattr(alliance_cog, 'get_alliance_nations'):
                    # Fallback: call AllianceManager getter with refresh flag (may read file)
                    await alliance_cog.get_alliance_nations(str(self.cybertron_id), force_refresh=True)
            except Exception as e:
                # Non-fatal: continue with whatever data is available
                self.logger.warning(f"Pre-refresh before /audit failed: {e}")

            nations = await self._get_combined_nations()
            if not nations:
                if hasattr(ctx, 'interaction') and ctx.interaction:
                    await ctx.interaction.followup.send("❌ No alliance data found for Cybertron.")
                else:
                    await ctx.reply("❌ No alliance data found for Cybertron.")
                return

            active_members = self._filter_active_members(nations)

            # New: MMR Build audit
            if view == "mmr":
                try:
                    # Thresholds per city average
                    if (mmr_mode or "basic") == "max":
                        thresh = {"barracks": 5.0, "factory": 5.0, "air": 5.0, "drydock": 3.0}
                        title = "⚙️ MMR Build Audit — Max"
                        note = "Shows ALL nations below 5/5/5/3 per-city average."
                    else:
                        thresh = {"barracks": 0.0, "factory": 2.0, "air": 5.0, "drydock": 1.0}
                        title = "⚙️ MMR Build Audit — Basic"
                        note = "Shows nations below minimum 0/2/5/1 per-city average (more is fine)."

                    # Use a small epsilon to avoid floating-point rounding issues (display is 1 decimal)
                    EPSILON = 0.05

                    def compute_mmr_avgs(n: Dict[str, Any]) -> Dict[str, float]:
                        cities = n.get("cities") or []
                        num = len(cities) if isinstance(cities, list) else (n.get("num_cities") or 0)
                        if not num:
                            return {"barracks": 0.0, "factory": 0.0, "air": 0.0, "drydock": 0.0, "num": 0,
                                    "b_total": 0, "f_total": 0, "a_total": 0, "d_total": 0}
                        b = f = a = d = 0
                        for c in cities or []:
                            if not isinstance(c, dict):
                                continue
                            b += c.get("barracks", 0) or 0
                            # Factories are keyed as "factory" in city data
                            f += c.get("factory", 0) or 0
                            # Air can be "airforcebase" or sometimes "hangar" depending on source
                            a += (c.get("airforcebase", 0) or c.get("hangar", 0) or 0)
                            d += c.get("drydock", 0) or 0
                        return {
                            "barracks": b / float(num),
                            "factory": f / float(num),
                            "air": a / float(num),
                            "drydock": d / float(num),
                            "num": float(num),
                            "b_total": int(b),
                            "f_total": int(f),
                            "a_total": int(a),
                            "d_total": int(d),
                        }

                    def _normalize_avgs(avg: Dict[str, float]) -> Dict[str, float]:
                        # Round to one decimal to match displayed values
                        return {
                            "barracks": round(float(avg.get("barracks", 0.0) or 0.0), 1),
                            "factory": round(float(avg.get("factory", 0.0) or 0.0), 1),
                            "air": round(float(avg.get("air", 0.0) or 0.0), 1),
                            "drydock": round(float(avg.get("drydock", 0.0) or 0.0), 1),
                            "num": float(avg.get("num", 0.0) or 0.0),
                        }

                    def below_threshold(avg: Dict[str, float]) -> bool:
                        navg = _normalize_avgs(avg)
                        def is_below(key: str) -> bool:
                            t = float(thresh.get(key, 0.0) or 0.0)
                            a = float(navg.get(key, 0.0) or 0.0)
                            if t <= 0:
                                return False
                            # Treat values within EPSILON of threshold as meeting the threshold
                            return (a + EPSILON) < t
                        return any(is_below(k) for k in ("barracks", "factory", "air", "drydock"))
                    # Compute a single percent-off metric relative to thresholds
                    def compute_percent_off(avg: Dict[str, float], thr: Dict[str, float]) -> float:
                        keys = ("barracks", "factory", "air", "drydock")
                        total_thr = sum(v for k, v in thr.items() if k in keys and v > 0)
                        if total_thr <= 0:
                            return 0.0
                        navg = _normalize_avgs(avg)
                        deficit_sum = 0.0
                        for k in keys:
                            t = float(thr.get(k, 0.0) or 0.0)
                            a = float(navg.get(k, 0.0) or 0.0)
                            if t > 0 and (a + EPSILON) < t:
                                deficit_sum += (t - a)
                        return max(0.0, min(100.0, (deficit_sum / total_thr) * 100.0))

                    # Bucket offenders by percent off to avoid massive single-field values
                    bucket_50_plus: List[Dict[str, Any]] = []  # 50% or more off
                    bucket_25_49: List[Dict[str, Any]] = []    # 25% to 49% off
                    bucket_10_24: List[Dict[str, Any]] = []    # 10% to 24% off
                    bucket_0_9: List[Dict[str, Any]] = []      # 0% to 9% off

                    for n in active_members:
                        avg = compute_mmr_avgs(n)
                        if avg["num"] <= 0:
                            continue
                        if below_threshold(avg):
                            perc = compute_percent_off(avg, thresh)
                            mmr_str = f"{avg['barracks']:.1f}/{avg['factory']:.1f}/{avg['air']:.1f}/{avg['drydock']:.1f}"
                            # Compute target totals for selected mode (thresholds are per-city)
                            try:
                                num_cities = int(round(float(avg.get("num", 0) or 0)))
                            except Exception:
                                num_cities = 0
                            totals_map = {
                                "barracks": int(round((thresh.get("barracks", 0) or 0) * num_cities)),
                                "factory": int(round((thresh.get("factory", 0) or 0) * num_cities)),
                                "air": int(round((thresh.get("air", 0) or 0) * num_cities)),
                                "drydock": int(round((thresh.get("drydock", 0) or 0) * num_cities)),
                            }
                            current_totals = {
                                "barracks": int(avg.get("b_total", 0) or 0),
                                "factory": int(avg.get("f_total", 0) or 0),
                                "air": int(avg.get("a_total", 0) or 0),
                                "drydock": int(avg.get("d_total", 0) or 0),
                            }
                            # Identify which single category is below, if any
                            navg = {
                                "barracks": round(float(avg.get("barracks", 0.0) or 0.0), 1),
                                "factory": round(float(avg.get("factory", 0.0) or 0.0), 1),
                                "air": round(float(avg.get("air", 0.0) or 0.0), 1),
                                "drydock": round(float(avg.get("drydock", 0.0) or 0.0), 1),
                            }
                            below_keys = []
                            for k in ("barracks", "factory", "air", "drydock"):
                                tval = float(thresh.get(k, 0.0) or 0.0)
                                aval = float(navg.get(k, 0.0) or 0.0)
                                if tval > 0 and (aval + EPSILON) < tval:
                                    below_keys.append(k)
                            enriched = dict(n)
                            enriched["__mmr_avg"] = avg
                            enriched["__mmr_percent_off"] = perc
                            enriched["__mmr_str"] = mmr_str
                            enriched["__mmr_totals"] = totals_map
                            enriched["__mmr_current_totals"] = current_totals
                            enriched["__mmr_below_keys"] = below_keys
                            if perc >= 50.0:
                                bucket_50_plus.append(enriched)
                            elif perc >= 25.0:
                                bucket_25_49.append(enriched)
                            elif perc >= 10.0:
                                bucket_10_24.append(enriched)
                            else:
                                bucket_0_9.append(enriched)

                    embed = discord.Embed(
                        title=title,
                        description=note,
                        color=discord.Color.orange(),
                        timestamp=datetime.now(timezone.utc)
                    )
                    # Add categorized fields with automatic chunking under 1024 chars per field
                    def suffix_builder(nation: Dict[str, Any]) -> Optional[str]:
                        try:
                            totals = nation.get("__mmr_totals", {}) or {}
                            current = nation.get("__mmr_current_totals", {}) or {}
                            avg = nation.get("__mmr_avg", {}) or {}
                            mode_label = "Max" if (mmr_mode or "basic") == "max" else "Basic"
                            mmr_s = str(nation.get("__mmr_str", ""))
                            # Normalize per-city averages to 1dp for comparison against thresholds with EPSILON
                            navg = {
                                "barracks": round(float(avg.get("barracks", 0.0) or 0.0), 1),
                                "factory": round(float(avg.get("factory", 0.0) or 0.0), 1),
                                "air": round(float(avg.get("air", 0.0) or 0.0), 1),
                                "drydock": round(float(avg.get("drydock", 0.0) or 0.0), 1),
                            }
                            # Compute needed totals with threshold tolerance so display matches "at-threshold" logic
                            def need_for(key: str) -> int:
                                t = float(thresh.get(key, 0.0) or 0.0)
                                a = float(navg.get(key, 0.0) or 0.0)
                                if t <= 0:
                                    return 0
                                if (a + EPSILON) >= t:
                                    return 0
                                required_total = int(round(t * float(avg.get("num", 0.0) or 0.0)))
                                current_total = int(current.get(key, 0) or 0)
                                return max(0, required_total - current_total)

                            need_b = need_for("barracks")
                            need_f = need_for("factory")
                            need_a = need_for("air")
                            need_d = need_for("drydock")
                            needed_str = f"{need_b}/{need_f}/{need_a}/{need_d}"
                            # Two-line suffix: current build on line 1, target line shows needed totals in B/F/A/D (no text list)
                            return f" - {mmr_s}\n   * Target {mode_label}: {needed_str}"
                        except Exception:
                            return None

                    total_offenders = (
                        len(bucket_50_plus) + len(bucket_25_49) + len(bucket_10_24) + len(bucket_0_9)
                    )

                    if total_offenders == 0:
                        embed.add_field(name="Members Below Threshold", value="✅ All members meet the threshold.", inline=False)
                    else:
                        # Use emojis to signal severity
                        self._add_category_fields(embed, "50%+ off", "🟥", bucket_50_plus, suffix_builder=suffix_builder)
                        self._add_category_fields(embed, "25–49% off", "🟧", bucket_25_49, suffix_builder=suffix_builder)
                        self._add_category_fields(embed, "10–24% off", "🟨", bucket_10_24, suffix_builder=suffix_builder)
                        self._add_category_fields(embed, "0–9% off", "🟩", bucket_0_9, suffix_builder=suffix_builder)

                    embed.set_footer(text=f"Active members checked: {len(active_members)} • Offenders: {total_offenders}")

                    if hasattr(ctx, 'interaction') and ctx.interaction:
                        await ctx.interaction.followup.send(embed=embed)
                    else:
                        await ctx.reply(embed=embed)
                    return
                except Exception as mmr_err:
                    self.logger.error(f"MMR audit error: {mmr_err}")
                    embed = discord.Embed(
                        title="❌ MMR Audit Error",
                        description=f"An error occurred during MMR calculation: {mmr_err}",
                        color=discord.Color.red()
                    )
                    if hasattr(ctx, 'interaction') and ctx.interaction:
                        await ctx.interaction.followup.send(embed=embed)
                    else:
                        await ctx.reply(embed=embed)
                    return

            # Resource-based issues (use active members set) - exclude zero values from "less than" categories
            food_lt_10k = [n for n in active_members if 0 < (n.get('food', 0) or 0) < 50000]
            uran_lt_500 = [n for n in active_members if 0 < (n.get('uranium', 0) or 0) < 1000]
            food_zero = [n for n in active_members if (n.get('food', 0) or 0) == 0]
            uran_zero = [n for n in active_members if (n.get('uranium', 0) or 0) == 0]

            # Color-based issues (use active members set)
            beige = [n for n in active_members if (n.get('color', '') or '').strip().upper() == 'BEIGE']
            grey = [n for n in active_members if (n.get('color', '') or '').strip().upper() in ('GREY', 'GRAY')]
            wrong_color = [
                n for n in active_members
                if (n.get('color', '') or '').strip().upper() not in ('LIME', 'GREY', 'GRAY', 'BEIGE')
            ]

            # Inactivity (use non-VM/non-applicants for meaningful review) - non-overlapping ranges
            inactive_7_to_13: List[Dict[str, Any]] = []
            inactive_14_to_23: List[Dict[str, Any]] = []
            inactive_24_plus: List[Dict[str, Any]] = []
            for n in active_members:
                d = _days_inactive(n)
                if isinstance(d, int):
                    if 7 <= d <= 13:
                        inactive_7_to_13.append(n)
                    elif 14 <= d <= 23:
                        inactive_14_to_23.append(n)
                    elif d >= 24:
                        inactive_24_plus.append(n)

            embed = discord.Embed(
                title="🧮 Audit Issues",
                description="Irregularities in the Cybertron alliance.",
                color=discord.Color.orange()
            )

            # Determine view filter via dropdown Literal; no default
            view_key = view

            if view_key == "resources":
                # Only show food/uranium categories
                self._add_category_fields(
                    embed,
                    "Food < 50,000",
                    "🍞",
                    food_lt_10k,
                    suffix_builder=lambda n: f"- {int(n.get('food', 0)):,}"
                )
                self._add_category_fields(
                    embed,
                    "Uranium < 1,000",
                    "☢️",
                    uran_lt_500,
                    suffix_builder=lambda n: f"- {int(n.get('uranium', 0)):,}"
                )
                self._add_category_fields(embed, "Food = 0", "🚫", food_zero)
                self._add_category_fields(embed, "Uranium = 0", "🚫", uran_zero)
            elif view_key == "inactives":
                # Only show inactivity categories
                self._add_category_fields(embed, "Inactive 7-13 days", "⏲️", inactive_7_to_13, with_days=True)
                self._add_category_fields(embed, "Inactive 14-23 days", "⚠️", inactive_14_to_23, with_days=True)
                self._add_category_fields(embed, "Inactive 24+ days", "🛑", inactive_24_plus, with_days=True)
            elif view_key == "color":
                # Show color categories: Beige, Grey, and Wrong Color (not Lime)
                self._add_category_fields(embed, "Beige", "🩼", beige)
                self._add_category_fields(embed, "Grey", "⚪", grey)
                self._add_category_fields(embed, "Wrong Color", "🎨", wrong_color)
            # No default 'all' view — users must select one

            embed.set_footer(text=f"Generated at {datetime.now().strftime('%H:%M:%S')} | Excludes APPLICANTS and Vacation Mode")

            if hasattr(ctx, 'interaction') and ctx.interaction:
                await ctx.interaction.followup.send(embed=embed)
            else:
                await ctx.reply(embed=embed)
        except Exception as e:
            self.logger.error(f"/audit error: {e}")
            try:
                if hasattr(ctx, 'interaction') and ctx.interaction:
                    await ctx.interaction.followup.send(f"❌ An error occurred: {str(e)}")
                else:
                    await ctx.reply(f"❌ An error occurred: {str(e)}")
            except Exception:
                pass

    @commands.hybrid_command(name="treaties", description="Show treaties and treaty web for any alliance")
    @app_commands.describe(alliance="Alliance name or ID (optional)")
    async def treaties_command(self, ctx: commands.Context, alliance: Optional[str] = None):
        """Query alliance treaties and display them in a rich embed."""
        try:
            # Slash invocation: quickly acknowledge without showing a thinking placeholder
            try:
                if hasattr(ctx, 'interaction') and ctx.interaction and not ctx.interaction.response.is_done():
                    await ctx.interaction.response.send_message("🔄 Refreshing treaties…", ephemeral=True, delete_after=1)
            except Exception:
                pass

            # Fetch treaties via AllianceManager's query system if available
            treaties: List[Dict[str, Any]] = []
            center_id: Optional[int] = None
            center_name: Optional[str] = None
            try:
                alliance_cog = self.bot.get_cog('AllianceManager')
                if alliance_cog and hasattr(alliance_cog, 'query_system') and alliance_cog.query_system:
                    # Resolve target alliance (name or ID if provided; default Cybertr0n)
                    arg = (alliance or "").strip()
                    if arg:
                        resolved = await alliance_cog.query_system.resolve_alliance(arg)
                        try:
                            if resolved and isinstance(resolved, dict) and resolved.get('id'):
                                center_id = int(str(resolved.get('id')))
                                center_name = (resolved.get('name') or '').strip() or None
                            elif arg.isdigit():
                                center_id = int(arg)
                            else:
                                center_id = None
                        except Exception:
                            center_id = None

                        if not center_id or int(center_id) <= 0:
                            msg = "❌ Could not resolve alliance. Enter a valid name or ID."
                            if hasattr(ctx, 'interaction') and ctx.interaction:
                                await ctx.interaction.followup.send(msg)
                            else:
                                await ctx.reply(msg)
                            return
                    else:
                        # Default to Cybertr0n when no alliance is specified
                        try:
                            center_id = int(self.cybertron_id)
                        except Exception:
                            center_id = self.cybertron_id
                        center_name = "Cybertr0n"

                    # Explicitly force fresh data from API on each use
                    res = await alliance_cog.query_system.get_alliance_treaties(str(center_id), force_refresh=True)
                    treaties = res or []
                else:
                    # Fall back gracefully
                    treaties = []
            except Exception as qerr:
                self.logger.error(f"Error querying treaties: {qerr}")

            # Generate treaty web image and rich embed
            treaty_file = await self._compose_treaty_web_image(treaties, center_alliance_id=center_id or 0)
            embed = self._format_treaties_embed(treaties, center_alliance_id=center_id or 0, center_name=center_name)
            files: List[discord.File] = []
            if treaty_file:
                embed.set_image(url=f"attachment://{treaty_file.filename}")
                files = [treaty_file]

            # Create the refresh view only for Cybertron
            view = None
            if center_id and int(center_id) == int(self.cybertron_id):
                view = TreatiesRefreshView(self, center_id)

            # Send or edit the channel message with the embed (handle files correctly)
            try:
                channel_id = getattr(getattr(ctx, 'channel', None), 'id', None)
                has_new_file = bool(files)
                edited = False
                if channel_id and channel_id in self.treaties_message_map:
                    try:
                        last_msg_id = self.treaties_message_map[channel_id]
                        last_msg = await ctx.channel.fetch_message(last_msg_id)
                        if not has_new_file:
                            # Edit embed/view and preserve any existing attachments on the message
                            await last_msg.edit(embed=embed, view=view, attachments=list(last_msg.attachments))
                            edited = True
                        else:
                            # Cannot upload new files via edit; send a new message instead
                            edited = False
                    except Exception:
                        edited = False
                if not edited:
                    sent = await ctx.send(embed=embed, view=view, files=files if files else [])
                    try:
                        if channel_id:
                            self.treaties_message_map[channel_id] = sent.id
                    except Exception:
                        pass

                # Clear any interaction placeholder so thinking does not linger
                try:
                    if hasattr(ctx, 'interaction') and ctx.interaction:
                        try:
                            await ctx.interaction.delete_original_response()
                        except Exception:
                            try:
                                await ctx.interaction.edit_original_response(content="", embed=None, view=None, attachments=[])
                            except Exception:
                                pass
                except Exception:
                    pass
            except Exception as send_error:
                # Fallback to a simple embed or error message
                self.logger.error(f"Error sending treaties embed: {send_error}")
                fallback_embed = discord.Embed(
                    title="❌ Error Loading Treaties",
                    description="An error occurred while loading treaty information.",
                    color=0xff0000
                )
                try:
                    if hasattr(ctx, 'interaction') and ctx.interaction:
                        await ctx.interaction.edit_original_response(embed=fallback_embed)
                    else:
                        await ctx.send(embed=fallback_embed)
                except Exception:
                    pass

        except Exception as e:
            self.logger.error(f"/treaties error: {e}")
            try:
                error_embed = discord.Embed(
                    title="❌ An error occurred",
                    description=str(e),
                    color=0xff0000
                )
                if hasattr(ctx, 'interaction') and ctx.interaction:
                    # Clear the placeholder, then send error
                    try:
                        await ctx.interaction.edit_original_response(content="", embed=None, view=None, attachments=[])
                    except Exception:
                        pass
                    await ctx.interaction.followup.send(embed=error_embed)
                else:
                    await ctx.reply(embed=error_embed)
            except Exception:
                pass

class TreatiesRefreshView(discord.ui.View):
    def __init__(self, cog: AuditManager, alliance_id: int, timeout: Optional[float] = None):
        # timeout=None => persistent view (when registered via bot.add_view)
        super().__init__(timeout=timeout)
        self.cog = cog
        self.alliance_id = alliance_id

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.primary, custom_id="treaties_refresh")
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        try:
            treaties: List[Dict[str, Any]] = []
            try:
                alliance_cog = self.cog.bot.get_cog('AllianceManager')
                if alliance_cog and hasattr(alliance_cog, 'query_system') and alliance_cog.query_system:
                    res = await alliance_cog.query_system.get_alliance_treaties(str(self.alliance_id), force_refresh=True)
                    treaties = res or []
            except Exception as qerr:
                self.cog.logger.error(f"Refresh treaties query error: {qerr}")

            # Generate treaty web image and new embed
            treaty_file = await self.cog._compose_treaty_web_image(treaties, center_alliance_id=int(self.alliance_id))
            embed = self.cog._format_treaties_embed(treaties, center_alliance_id=int(self.alliance_id))
            files: List[discord.File] = []
            if treaty_file:
                embed.set_image(url=f"attachment://{treaty_file.filename}")
                files = [treaty_file]

            # Delete the old message and post a new one with a fresh view
            new_view = TreatiesRefreshView(self.cog, int(self.alliance_id), timeout=None)
            try:
                try:
                    await interaction.message.delete()
                except Exception as del_err:
                    self.cog.logger.error(f"TreatiesRefreshView: delete failed: {del_err}")
                new_msg = await interaction.channel.send(embed=embed, view=new_view, files=files if files else [])
                try:
                    # Update channel->message mapping for treaties posts
                    self.cog.treaties_message_map[getattr(interaction.channel, 'id', 0)] = getattr(new_msg, 'id', 0)
                except Exception:
                    pass
            except Exception:
                # Fallback to editing if delete/send fails
                try:
                    await interaction.message.edit(embed=embed, view=new_view)
                except Exception:
                    try:
                        await interaction.edit_original_response(embed=embed, view=new_view)
                    except Exception:
                        pass
        except Exception as e:
            try:
                error_embed = discord.Embed(
                    title="❌ Refresh Failed",
                    description=f"Error: {str(e)}",
                    color=0xFF0000
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            except Exception:
                pass

async def setup(bot: commands.Bot):
    audit = AuditManager(bot)
    await bot.add_cog(audit)
    # Register a persistent view so the Refresh button survives bot restarts
    try:
        bot.add_view(TreatiesRefreshView(audit, audit.cybertron_id, timeout=None))
    except Exception:
        pass
        # Define base radii for rings
        INNER_RADIUS = 180                     # inner ring for protectorates/extensions
        AERO_RADIUS  = 280                     # AERO ring radius
        PRIME_RADIUS = 120                     # Prime Bank closest to center
        # Outer rings by treaty type in ordered distances
        MDOAP_RADIUS = 320
        MDP_RADIUS   = 360
        ODOAP_RADIUS = 400
        ODP_RADIUS   = 440
        PIAT_RADIUS  = 480
        NAP_RADIUS   = 520

        # Compute required radii to prevent flag overlap (pre-pass)
        def compute_required_radius(items: List[Dict[str, Any]], base_radius: int) -> int:
            n = len(items)
            if n == 0:
                return base_radius
            max_flag_size = max((it.get('img').width if it.get('img') else 48) for it in items) if items else 48
            min_arc_length = max_flag_size + 8
            min_angle_sep = min_arc_length / float(base_radius)
            required_angle = min_angle_sep * n
            if required_angle > 2 * math.pi:
                return int(min_arc_length * n / (2 * math.pi)) + 10
            return base_radius

        INNER_RADIUS = compute_required_radius(inner_items, INNER_RADIUS)
        AERO_RADIUS  = compute_required_radius(aero_items,  AERO_RADIUS)
        MDOAP_RADIUS = compute_required_radius(mdoap_items, MDOAP_RADIUS)
        MDP_RADIUS   = compute_required_radius(mdp_items,   MDP_RADIUS)
        ODOAP_RADIUS = compute_required_radius(odoap_items, ODOAP_RADIUS)
        ODP_RADIUS   = compute_required_radius(odp_items,   ODP_RADIUS)
        PIAT_RADIUS  = compute_required_radius(piat_items,  PIAT_RADIUS)
        NAP_RADIUS   = compute_required_radius(nap_items,   NAP_RADIUS)

        # Dynamically size canvas to ensure all flags are fully visible within bounds
        MARGIN = 28
        def half_size(items: List[Dict[str, Any]]) -> int:
            try:
                return max(((it.get('img').width or 0) // 2) for it in items) if items else 0
            except Exception:
                return 0

        max_extent = max([
            INNER_RADIUS + half_size(inner_items),
            AERO_RADIUS  + half_size(aero_items),
            MDOAP_RADIUS + half_size(mdoap_items),
            MDP_RADIUS   + half_size(mdp_items),
            ODOAP_RADIUS + half_size(odoap_items),
            ODP_RADIUS   + half_size(odp_items),
            PIAT_RADIUS  + half_size(piat_items),
            NAP_RADIUS   + half_size(nap_items),
            PRIME_RADIUS + (prime_img.width // 2 if prime_img else 0),
        ])
        CANVAS_SIZE = max(800, int(2 * (max_extent + MARGIN)))
        CENTER_X, CENTER_Y = CANVAS_SIZE // 2, CANVAS_SIZE // 2

        # Create canvas after sizing is finalized
        canvas = Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)