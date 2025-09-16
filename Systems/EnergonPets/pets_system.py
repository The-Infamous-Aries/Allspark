# Standard library imports
import asyncio
import logging
import random
import sys
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union

# Third-party imports
import discord
from discord.ext import commands
from discord import app_commands, ui

# Local application imports
from Systems.user_data_manager import user_data_manager
from .pet_levels import (
    LEVEL_THRESHOLDS, 
    PET_STAGES, 
    STAGE_EMOJIS, 
    MISSION_TYPES, 
    MISSION_DIFFICULTIES, 
    AUTOBOT_PET_NAMES, 
    DECEPTICON_PET_NAMES,
    get_stage_emoji, 
    get_stage_name, 
    get_pet_name, 
    load_level_data, 
    add_experience,
    create_level_up_embed, 
    send_level_up_embed
)

# Constants
MONSTER_EMOJIS = {
    "monster": "🤖",
    "boss": "👹",
    "titan": "👑"
}

RARITY_EMOJIS = {
    "common": "⚪",
    "uncommon": "🟢", 
    "rare": "🔵",
    "epic": "🟣", 
    "legendary": "🟠",
    "mythic": "🔴"
}

# Configure logging
logger = logging.getLogger('pets_system')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

class PetStatusView(discord.ui.View):
    """Interactive view for pet status with optimized performance and caching"""
    
    def __init__(self, user_id: int, pet_system, commands_cog, pet_data=None):
        super().__init__(timeout=300)  # 5 minute timeout
        self.user_id = user_id
        self.pet_system = pet_system
        self.commands_cog = commands_cog
        self.showing_breakdown = False
        self.pet_data = pet_data
        self._cached_equipment_stats = None
        self._cached_embed = None
        self._last_update = 0
        self._update_lock = asyncio.Lock()
        
        # Add buttons
        self.add_item(RefreshButton())
        self.add_item(BreakdownButton())
    
    async def create_main_embed(self) -> discord.Embed:
        """Create the main pet status embed with caching"""
        current_time = time.time()
        
        # Use cached embed if recent and valid
        if (self._cached_embed and 
            current_time - self._last_update < 60 and 
            self._cached_equipment_stats is not None):
            return self._cached_embed
        
        async with self._update_lock:
            # Double-check in case another task was updating
            if (self._cached_embed and 
                current_time - self._last_update < 60 and 
                self._cached_equipment_stats is not None):
                return self._cached_embed
                
            # Load pet data if not provided
            if not self.pet_data:
                self.pet_data = await self.pet_system.get_user_pet(self.user_id)
            
            pet = self.pet_data
            if not pet:
                return discord.Embed(
                    title="Error", 
                    description="Pet not found!", 
                    color=discord.Color.red()
                )
            
            # Get faction data
            faction = pet.get('faction', 'Unknown').lower()
            embed_color, faction_emoji = self._get_faction_style(faction)
            
            # Get stage info
            stage_emoji, stage_name = self._get_stage_info(pet)
            
            # Create embed
            embed = discord.Embed(
                title=f"{stage_emoji} {stage_name} - {faction.title()} - {pet['name']}",
                color=embed_color
            )
            
            # Get equipment stats
            self._cached_equipment_stats = await self.pet_system.get_equipment_stats(self.user_id)
            equipment_stats = self._cached_equipment_stats
            
            # Calculate totals
            totals = self._calculate_totals(pet, equipment_stats)
            
            # Add fields to embed
            self._add_embed_fields(embed, pet, totals, faction)
            
            # Cache the result
            self._cached_embed = embed
            self._last_update = current_time
            
            return embed
    
    def _get_faction_style(self, faction: str) -> Tuple[int, str]:
        """Get faction-specific styling"""
        if faction == 'autobot':
            return 0xCC0000, "🔴"
        elif faction == 'decepticon':
            return 0x800080, "🟣"
        return 0x808080, "⚡"
    
    def _get_stage_info(self, pet: Dict[str, Any]) -> Tuple[str, str]:
        """Get pet's stage emoji and name"""
        try:
            return get_stage_emoji(pet['level']), get_stage_name(pet['level'])
        except:
            return "🥚", f"Level {pet['level']}"
    
    def _calculate_totals(self, pet: Dict[str, Any], equipment_stats: Dict[str, int]) -> Dict[str, int]:
        """Calculate total stats including equipment bonuses"""
        return {
            'attack': pet['attack'] + equipment_stats['attack'],
            'defense': pet['defense'] + equipment_stats['defense'],
            'energy': pet['max_energy'] + equipment_stats['energy'],
            'maintenance': pet['max_maintenance'] + equipment_stats['maintenance'],
            'happiness': pet['max_happiness'] + equipment_stats['happiness']
        }
    
    def _add_embed_fields(self, embed: discord.Embed, pet: Dict[str, Any], 
                         totals: Dict[str, int], faction: str) -> None:
        """Add fields to the embed"""
        # Creation date
        created = datetime.fromisoformat(pet["created_at"])
        embed.add_field(name="🗓️ Created", value=created.strftime("%m/%d/%y at %I:%M %p"), inline=True)
        
        # Stats
        embed.add_field(
            name="⚡ Power", 
            value=f"⚔️ {totals['attack']} | 🛡️ {totals['defense']}", 
            inline=True
        )
        
        # Level progress
        self._add_level_progress(embed, pet, faction)
        
        # Resources
        embed.add_field(name="🔋 Energy", value=f"{int(pet['energy'])}/{totals['energy']}", inline=True)
        embed.add_field(name="🔧 Maintenance", value=f"{int(pet['maintenance'])}/{totals['maintenance']}", inline=True)
        embed.add_field(name="😊 Happiness", value=f"{int(pet['happiness'])}/{totals['happiness']}", inline=True)
        
        # Equipment
        self._add_equipment_info(embed, pet)
    
    def _add_level_progress(self, embed: discord.Embed, pet: Dict[str, Any], faction: str) -> None:
        """Add level progress bar to embed"""
        if pet['level'] < 500:
            threshold = LEVEL_THRESHOLDS.get(pet['level'], 1000)
            progress = min(pet['experience'] / threshold, 1.0) if threshold > 0 else 0
            filled_length = int(10 * progress)
            
            # Choose progress bar character based on faction
            if faction == 'autobot':
                filled_char = "🟥"
            elif faction == 'decepticon':
                filled_char = "🟪"
            else:
                filled_char = "🟨"
                
            bar = filled_char * filled_length + "⬛" * (10 - filled_length)
            embed.add_field(
                name="📊 Level Progress", 
                value=f"{bar} {pet['experience']}/{threshold} XP", 
                inline=False
            )
        else:
            embed.add_field(
                name="📊 Level Progress", 
                value="🌟 MAX LEVEL REACHED! 🌟", 
                inline=False
            )
    
    def _add_equipment_info(self, embed: discord.Embed, pet: Dict[str, Any]) -> None:
        """Add equipment information to embed"""
        equipment = pet.get('equipment', {})
        if not equipment:
            return
            
        equipped_items = []
        for slot, item in equipment.items():
            if item and isinstance(item, dict):
                emoji = RARITY_EMOJIS.get(item.get('rarity', 'common'), '⚪')
                equipped_items.append(f"{emoji} {item.get('name', 'Unknown')}")
        
        if equipped_items:
            embed.add_field(
                name="⚔️ Equipment", 
                value="\n".join(equipped_items), 
                inline=False
            )

class RefreshButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.primary, label="🔄 Refresh", custom_id="refresh_status")
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        view = self.view
        view._cached_embed = None  # Invalidate cache
        embed = await view.create_main_embed()
        await interaction.edit_original_response(embed=embed, view=view)

class BreakdownButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.secondary, label="📊 Stats Breakdown", custom_id="show_breakdown")
    
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        view.showing_breakdown = not view.showing_breakdown
        await interaction.response.defer()
        
        if view.showing_breakdown:
            embed = await view.create_breakdown_embed()
            await interaction.edit_original_response(embed=embed, view=view)
        else:
            embed = await view.create_main_embed()
            await interaction.edit_original_response(embed=embed, view=view)

class PetEquipmentView(discord.ui.View):
    """Interactive view for displaying and managing pet equipment with optimized performance"""
    
    # Class-level constants
    ITEMS_PER_PAGE = 10
    STAT_EMOJIS = {
        "attack": "⚔️",
        "defense": "🛡️",
        "energy": "⚡",
        "maintenance": "🔧",
        "happiness": "😊"
    }
    RARITY_EMOJIS = {
        "common": "⚪",
        "uncommon": "🟢", 
        "rare": "🔵",
        "epic": "🟣", 
        "legendary": "🟠",
        "mythic": "🔴"
    }
    TYPE_EMOJIS = {
        "chassis_plating": "🩻",
        "energy_cores": "🔋",
        "utility_modules": "💾"
    }
    
    def __init__(self, user_id: int, pet_system, items: List[Dict[str, Any]]):
        super().__init__(timeout=300)  # 5 minute timeout
        self.user_id = user_id
        self.pet_system = pet_system
        self.items = items
        self.current_page = 0
        self.total_pages = max(1, (len(items) + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE)
        self._cached_embeds = {}  # Cache for embeds
        self._pet_data = None  # Cache for pet data
        
        # Initialize UI components
        self._setup_ui()
    
    async def _get_pet_data(self) -> Dict[str, Any]:
        """Get and cache pet data"""
        if not self._pet_data:
            self._pet_data = await self.pet_system.get_user_pet(self.user_id)
        return self._pet_data
    
    def _setup_ui(self) -> None:
        """Initialize UI components"""
        # Add navigation buttons
        self.add_item(FirstPageButton())
        self.add_item(PrevPageButton())
        self.add_item(NextPageButton())
        self.add_item(LastPageButton())
        self.add_item(CloseViewButton())
        
        # Add equipment type filter dropdown
        self.add_item(EquipmentTypeSelect())
    
    def _get_embed_color(self) -> int:
        """Get embed color based on pet's faction"""
        pet = self._pet_data or {}
        faction = pet.get('faction', '').lower()
        return {
            'autobot': 0xCC0000,
            'decepticon': 0x800080
        }.get(faction, 0x00AE86)
    
    def _get_page_items(self, page: int) -> List[Dict[str, Any]]:
        """Get items for the specified page"""
        start_idx = page * self.ITEMS_PER_PAGE
        end_idx = start_idx + self.ITEMS_PER_PAGE
        return self.items[start_idx:end_idx]
    
    async def create_embed(self, page: int) -> discord.Embed:
        """Create or get cached embed for the specified page"""
        if page in self._cached_embeds:
            return self._cached_embeds[page]
            
        # Get pet data if not cached
        if not self._pet_data:
            self._pet_data = await self.pet_system.get_user_pet(self.user_id)
        
        # Create new embed
        embed = await self._build_embed(page)
        self._cached_embeds[page] = embed
        return embed
    
    async def _build_embed(self, page: int) -> discord.Embed:
        """Build embed for the specified page"""
        page_items = self._get_page_items(page)
        pet = self._pet_data or {}
        pet_name = pet.get('name', 'Your Pet')
        
        embed = discord.Embed(
            title=f"🎒 {pet_name}'s Equipment Collection",
            description=f"Page {page + 1}/{self.total_pages} • {len(self.items)} total items",
            color=self._get_embed_color()
        )
        
        if not page_items:
            embed.add_field(
                name="📭 No Items Found",
                value="You don't have any pet equipment items yet!",
                inline=False
            )
            return embed
            
        # Add items to embed
        for idx, item in enumerate(page_items, start=page * self.ITEMS_PER_PAGE):
            embed.add_field(
                **self._format_item_field(item, idx),
                inline=False
            )
            
        return embed
    
    def _format_item_field(self, item: Dict[str, Any], idx: int) -> Dict[str, str]:
        """Format an item as an embed field"""
        rarity = item.get('rarity', 'common').lower()
        item_type = item.get('type', 'unknown')
        name = item.get('name', 'Unknown Item')
        description = item.get('description', 'No description available')
        
        return {
            'name': f"{self.RARITY_EMOJIS.get(rarity, '⚪')} {self.TYPE_EMOJIS.get(item_type, '📦')} {name}",
            'value': self._format_item_value(description, item.get('stat_bonus', {})),
            'inline': False
        }
    
    def _format_item_value(self, description: str, stat_bonus: Dict[str, int]) -> str:
        """Format item value with description and stats"""
        if not stat_bonus:
            return f"*{description}*"
            
        stat_text = " | ".join(
            f"{self.STAT_EMOJIS.get(stat, '📊')} +{value}"
            for stat, value in stat_bonus.items()
        )
        return f"*{description}*\n{stat_text}"
    
    def update_buttons(self) -> None:
        """Update button states based on current page"""
        for child in self.children:
            if isinstance(child, (FirstPageButton, PrevPageButton)):
                child.disabled = self.current_page == 0
            elif isinstance(child, (NextPageButton, LastPageButton)):
                child.disabled = self.current_page >= self.total_pages - 1
    
    async def show_page(self, interaction: discord.Interaction, page: int) -> None:
        """Show the specified page"""
        if not 0 <= page < self.total_pages:
            return
            
        self.current_page = page
        self.update_buttons()
        
        embed = await self.create_embed(page)
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_timeout(self) -> None:
        """Handle view timeout"""
        for child in self.children:
            child.disabled = True
            
        if hasattr(self, 'message'):
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass

# Button Classes
class FirstPageButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.gray, emoji="⏮️", row=1)
        
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        await view.show_page(interaction, 0)

class PrevPageButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.gray, emoji="◀️", row=1)
        
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        await view.show_page(interaction, max(0, view.current_page - 1))

class NextPageButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.gray, emoji="▶️", row=1)
        
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        await view.show_page(interaction, min(view.total_pages - 1, view.current_page + 1))

class LastPageButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.gray, emoji="⏭️", row=1)
        
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        await view.show_page(interaction, view.total_pages - 1)

class CloseViewButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.danger, emoji="❌", row=1)
        
    async def callback(self, interaction: discord.Interaction):
        await interaction.message.delete()

class EquipmentTypeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="All Types", emoji="📦", value="all"),
            discord.SelectOption(label="Chassis Plating", emoji="🩻", value="chassis_plating"),
            discord.SelectOption(label="Energy Cores", emoji="🔋", value="energy_cores"),
            discord.SelectOption(label="Utility Modules", emoji="💾", value="utility_modules")
        ]
        super().__init__(
            placeholder="Filter by type...",
            min_values=1,
            max_values=1,
            options=options,
            row=0
        )
    
    async def callback(self, interaction: discord.Interaction):
        # Implementation for filtering by equipment type
        await interaction.response.defer()

class PetSystem:
    """Main pet system class with optimized performance and resource management"""
    
    def __init__(self, bot):
        self.bot = bot
        self._data_loaded = asyncio.Event()
        self._load_task = None
        self._cache = {}
        self._cache_lock = asyncio.Lock()
        self._last_save = {}
        self._pending_saves = asyncio.Queue()
        self._save_task = None
        self._shutdown = False
        
        # Data structures
        self.monsters_data = {}
        self.transformation_items = {}
        self.bosses_data = {}
        self.titans_data = {}
        
        # Start background tasks
        self._save_task = asyncio.create_task(self._save_worker())
        self._load_task = asyncio.create_task(self._preload_data())
    
    async def _preload_data(self) -> None:
        """Preload all required data asynchronously"""
        try:
            await asyncio.gather(
                self._load_monsters_and_bosses(),
                self._load_transformation_items()
            )
            self._data_loaded.set()
        except Exception as e:
            logger.error(f"Error preloading data: {e}")
            # Schedule retry with exponential backoff
            retry_delay = min(60, 2 ** (len(self._load_task.retries) if hasattr(self._load_task, 'retries') else 1))
            await asyncio.sleep(retry_delay)
            self._load_task.retries = getattr(self._load_task, 'retries', 0) + 1
            self._load_task = asyncio.create_task(self._preload_data())
    
    async def _load_monsters_and_bosses(self) -> None:
        """Load monsters, bosses, and titans with error handling"""
        try:
            data = await user_data_manager.get_monsters_and_bosses_data()
            self._process_monster_data(data)
        except Exception as e:
            logger.error(f"Error loading monster data: {e}")
            raise
    
    def _process_monster_data(self, data: Dict) -> None:
        """Process and categorize monster data"""
        self.monsters_data = {}
        self.bosses_data = {}
        self.titans_data = {}
        
        if 'monsters' in data:
            monsters_json = data['monsters']
            if isinstance(monsters_json, dict):
                for rarity, monster_list in monsters_json.items():
                    if isinstance(monster_list, list):
                        for monster in monster_list:
                            self._categorize_monster(monster, rarity.lower())
        
        # Process direct boss and titan structures
        for category in ['bosses', 'titans']:
            if category in data:
                category_json = data[category]
                if isinstance(category_json, dict):
                    for rarity, entity_list in category_json.items():
                        if isinstance(entity_list, list):
                            for entity in entity_list:
                                self._categorize_monster(entity, rarity.lower(), category)
        
        logger.info(
            f"Loaded monsters: {sum(len(m) for m in self.monsters_data.values())}, "
            f"bosses: {sum(len(b) for b in self.bosses_data.values())}, "
            f"titans: {sum(len(t) for t in self.titans_data.values())}"
        )
    
    def _categorize_monster(self, monster: Dict, rarity: str, force_type: str = None) -> None:
        """Categorize monster into appropriate collection"""
        monster_type = force_type or monster.get('type', 'monster').lower()
        target = {
            'monster': self.monsters_data,
            'boss': self.bosses_data,
            'titan': self.titans_data
        }.get(monster_type, self.monsters_data)
        
        if rarity not in target:
            target[rarity] = []
        target[rarity].append(monster)
    
    async def _load_transformation_items(self) -> None:
        """Load transformation items with error handling and metrics"""
        try:
            data = await user_data_manager.get_transformation_items_data()
            self._process_transformation_items(data)
        except Exception as e:
            logger.error(f"Error loading transformation items: {e}")
            raise
    
    def _process_transformation_items(self, data: Dict) -> None:
        """Process transformation items data"""
        if 'items_by_class' in data:
            self.transformation_items = data['items_by_class']
        else:
            self.transformation_items = data
        
        total_items = sum(
            len(items) 
            for class_dict in self.transformation_items.values() 
            if isinstance(class_dict, dict)
            for items in class_dict.values()
            if isinstance(items, dict)
        )
        logger.info(f"Loaded {total_items} transformation items across all classes")
    
    async def create_pet(self, user_id: int, faction: str) -> Dict[str, Any]:
        """Create a new pet with faction-based starting stats"""
        faction_lower = faction.lower()
        stats = self._get_faction_stats(faction_lower)
        
        pet_data = {
            "name": get_pet_name(faction),
            "faction": faction.capitalize(),
            "level": 1,
            "experience": 0,
            "energy": stats["energy"],
            "max_energy": stats["energy"],
            "happiness": stats["happiness"],
            "max_happiness": stats["happiness"],
            "maintenance": 100,
            "max_maintenance": 100,
            "attack": stats["attack"],
            "defense": stats["defense"],
            "created_at": datetime.utcnow().isoformat(),
            "equipment": {},
            "inventory": [],
            "battles_won": 0,
            "battles_lost": 0,
            "missions_completed": 0,
            "total_mission_energon": 0,
            "total_battle_energon": 0,
            "total_training_energon": 0,
            "total_challenge_energon": 0,
            "mission_xp_earned": 0,
            "battle_xp_earned": 0,
            "training_xp_earned": 0,
            "challenge_xp_earned": 0,
            "search_xp_earned": 0,
            "charge_xp_earned": 0,
            "play_xp_earned": 0,
            "repair_xp_earned": 0
        }
        
        # Save the new pet
        await self._queue_save(user_id, pet_data)
        return pet_data
    
    def _get_faction_stats(self, faction: str) -> Dict[str, int]:
        """Get starting stats based on faction"""
        if faction == 'autobot':
            return {"attack": 10, "defense": 12, "happiness": 200, "energy": 100}
        return {"attack": 12, "defense": 10, "happiness": 100, "energy": 200}
    
    async def _save_worker(self) -> None:
        """Background worker for batched saves"""
        while not self._shutdown:
            try:
                batch = []
                try:
                    # Wait for first item with timeout
                    item = await asyncio.wait_for(self._pending_saves.get(), timeout=5.0)
                    batch.append(item)
                    
                    # Get any other pending saves
                    while not self._pending_saves.empty() and len(batch) < 10:
                        batch.append(self._pending_saves.get_nowait())
                    
                    # Process batch
                    if batch:
                        await self._process_save_batch(batch)
                except asyncio.TimeoutError:
                    continue
            except Exception as e:
                logger.error(f"Error in save worker: {e}")
                await asyncio.sleep(1)
    
    async def _process_save_batch(self, batch: List[Tuple[int, Dict]]) -> None:
        """Process a batch of save operations"""
        updates = {}
        for user_id, pet_data in batch:
            updates[str(user_id)] = pet_data
        
        save_tasks = [
            user_data_manager.save_pet_data(uid, uid, data)
            for uid, data in updates.items()
        ]
        
        await asyncio.gather(*save_tasks, return_exceptions=True)
    
    async def _queue_save(self, user_id: int, pet_data: Dict[str, Any]) -> None:
        """Queue a save operation"""
        await self._pending_saves.put((user_id, pet_data))
    
    async def get_user_pet(self, user_id: int, *, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Get user's pet with caching and background refresh"""
        cache_key = str(user_id)
        current_time = time.time()
        
        # Check cache first
        if not force_refresh and cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if current_time - timestamp < 300:  # 5 minute cache
                return cached_data
        
        # Cache miss or forced refresh
        try:
            pet_data = await user_data_manager.get_pet_data(cache_key)
            if pet_data:
                # Schedule cache update without waiting
                asyncio.create_task(self._update_cache(cache_key, pet_data))
                return pet_data
            return None
        except Exception as e:
            logger.error(f"Error getting pet data for {user_id}: {e}")
            return None
    
    async def _update_cache(self, user_id: str, pet_data: Dict[str, Any]) -> None:
        """Update cache with new pet data"""
        async with self._cache_lock:
            self._cache[user_id] = (pet_data, time.time())
    
    async def shutdown(self) -> None:
        """Clean up resources"""
        self._shutdown = True
        if self._save_task:
            self._save_task.cancel()
            try:
                await self._save_task
            except asyncio.CancelledError:
                pass
        
        # Process any remaining saves
        if not self._pending_saves.empty():
            batch = []
            while not self._pending_saves.empty():
                batch.append(self._pending_saves.get_nowait())
            await self._process_save_batch(batch)

# Setup function for bot integration
async def setup(bot_instance: commands.Bot) -> None:
    """Setup function to integrate pets system with the bot"""
    try:
        # Initialize the pet system
        pet_system = PetSystem(bot_instance)
        
        # Load initial data
        await load_level_data()
        await pet_system.load_cyberchronicles_monsters()
        await pet_system.load_transformation_items()
        
        # Store the pet system instance in the bot
        bot_instance.pet_system = pet_system
        
        print("✅ Pets system initialized successfully")
        
    except Exception as e:
        print(f"❌ Error initializing pets system: {e}")
        raise

__all__ = [
    'PetSystem',
    'PetStatusView',
    'setup'
]