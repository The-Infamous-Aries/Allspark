import discord
from discord.ext import commands
import logging
import os
import sys
import json
import time
from typing import List, Dict, Optional, Any
from datetime import datetime

# Import user data manager for cache access
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from Systems.user_data_manager import UserDataManager

# Import config for API keys and settings
from config import PANDW_API_KEY, CYBERTRON_ALLIANCE_ID


class NationListView(discord.ui.View):
    """View for displaying alliance nations with pagination and detailed military information."""
    
    def __init__(self, nations: List[Dict[str, Any]], author_id: int, bot: commands.Bot, nations_cog):
        super().__init__(timeout=300)  # 5 minute timeout
        self.nations = nations
        self.current_page = 0
        self.author_id = author_id
        self.bot = bot
        self.nations_cog = nations_cog
        self.nations_per_page = 3
        
        # Sort nations by score (descending)
        self.nations.sort(key=lambda n: n.get('score', 0), reverse=True)
        
        # Calculate total pages
        self.total_pages = (len(self.nations) + self.nations_per_page - 1) // self.nations_per_page

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensures only the person who triggered the command can use the buttons."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("⚠️ Only the command initiator can use these buttons!")
            return False
        return True

    def create_embed(self) -> discord.Embed:
        """Creates the embed for the current page of nations."""
        if not self.nations:
            embed = discord.Embed(
                title="⚠️ No Nations Found",
                description="No alliance nations could be retrieved.",
                color=discord.Color.red()
            )
            return embed

        start_idx = self.current_page * self.nations_per_page
        end_idx = min(start_idx + self.nations_per_page, len(self.nations))
        page_nations = self.nations[start_idx:end_idx]
        
        # Calculate page statistics
        total_score = sum(nation.get('score', 0) for nation in page_nations)
        total_cities = sum(nation.get('num_cities', 0) for nation in page_nations)
        
        party_number = self.current_page + 1
        total_parties = self.total_pages
        
        # Calculate war range for this party
        war_range_data = self.nations_cog.calculate_party_war_range(page_nations)
        overlapping_min = war_range_data['overlapping_min']
        overlapping_max = war_range_data['overlapping_max']
        war_avg = war_range_data['avg_score']
        
        embed = discord.Embed(
            title=f"🎯 Cybertr0n Blitz Party #{party_number} - War Range: {overlapping_min:,.0f} - {overlapping_max:,.0f}",
            description=f"**War Range:** {overlapping_min:,.0f} - {overlapping_max:,.0f} (Avg Score: {war_avg:,.1f})\n**Total Parties:** {total_parties} | **Total Nations:** {len(self.nations)}",
            color=discord.Color.from_rgb(0, 150, 255)
        )
        embed.set_footer(text=f"Party {party_number} of {total_parties} | Generated at {datetime.now().strftime('%H:%M:%S')}")
        
        for i, nation in enumerate(page_nations, start_idx + 1):
            # Calculate MMR score
            mmr_score = (nation.get('num_cities', 0) * 10) + self.nations_cog.calculate_combat_score(nation)
            
            # Strategic capabilities with comprehensive project detection
            strategic_info = []
            if self.nations_cog.has_project(nation, 'Missile Launch Pad'):
                strategic_info.append("🚀")
            if self.nations_cog.has_project(nation, 'Nuclear Research Facility'):
                strategic_info.append("☢️")
            if self.nations_cog.has_project(nation, 'Iron Dome'):
                strategic_info.append("**ID**")
            if self.nations_cog.has_project(nation, 'Vital Defense System'):
                strategic_info.append("**VDS**")
            
            strategic_text = ", ".join(strategic_info) if strategic_info else "❌ None"
            
            # Military specialty and advantages
            specialty = self.nations_cog.get_nation_specialty(nation)
            specialty_emoji = {
                "Ground": "🪖",
                "Air": "✈️", 
                "Naval": "🚢",
                "Generalist": "⚖️"
            }
            
            # Get current military units
            current_soldiers = nation.get('soldiers', 0)
            current_tanks = nation.get('tanks', 0)
            current_aircraft = nation.get('aircraft', 0)
            current_ships = nation.get('ships', 0)
            
            # Calculate production limits
            try:
                limits = self.nations_cog.calculate_military_purchase_limits(nation)
                daily_soldiers = limits.get('soldiers_daily', limits.get('soldiers', 0))
                daily_tanks = limits.get('tanks_daily', limits.get('tanks', 0))
                daily_aircraft = limits.get('aircraft_daily', limits.get('aircraft', 0))
                daily_ships = limits.get('ships_daily', limits.get('ships', 0))
                max_soldiers = limits.get('soldiers_max', 0)
                max_tanks = limits.get('tanks_max', 0)
                max_aircraft = limits.get('aircraft_max', 0)
                max_ships = limits.get('ships_max', 0)
            except:
                # Fallback if calculation fails
                daily_soldiers = daily_tanks = daily_aircraft = daily_ships = 0
                max_soldiers = max_tanks = max_aircraft = max_ships = 0
            
            # Format military information compactly
            def format_military_line(emoji, current, daily, max_cap):
                return f"{emoji} {current:,}/{max_cap:,} (+{daily:,}/day)"
            
            # Create clickable leader name link
            leader_name = nation.get('leader_name', 'Unknown')
            nation_id = nation.get('id')
            if nation_id and leader_name != 'Unknown':
                leader_link = f"[{leader_name}](https://politicsandwar.com/nation/id={nation_id})"
            else:
                leader_link = leader_name
            
            # Add Discord username if available
            discord_info = ""
            discord_username = nation.get('discord_username')
            if discord_username:
                discord_display = nation.get('discord_display_name', discord_username)
                if discord_display != discord_username:
                    discord_info = f"**Discord:** {discord_display} (@{discord_username})\n"
                else:
                    discord_info = f"**Discord:** @{discord_username}\n"
            
            field_value = (
                f"**Leader:** {leader_link}\n"
                f"{discord_info}"
                f"**Cities:** {nation.get('num_cities', 0)} | **Score:** {nation.get('score', 0):,}\n"
                f"**MMR:** {mmr_score:.1f} | **Policy:** {nation.get('war_policy', 'Unknown')}\n"
                f"**Strategic:** {strategic_text}\n"
                f"{format_military_line('🪖', current_soldiers, daily_soldiers, max_soldiers)}\n"
                f"{format_military_line('🛡️', current_tanks, daily_tanks, max_tanks)}\n"
                f"{format_military_line('✈️', current_aircraft, daily_aircraft, max_aircraft)}\n"
                f"{format_military_line('🚢', current_ships, daily_ships, max_ships)}"
            )

            embed.add_field(
                name=f"{i}. {nation.get('nation_name', 'Unknown')} {specialty_emoji.get(specialty, '❓')}",
                value=field_value,
                inline=True
            )
            
        return embed

    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.secondary, disabled=True)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = max(0, self.current_page - 1)
        
        # Update button states
        self.previous_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page >= self.total_pages - 1)
        
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="▶️ Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = min(self.total_pages - 1, self.current_page + 1)
        
        # Update button states
        self.previous_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page >= self.total_pages - 1)
        
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        """Called when the view times out."""
        for item in self.children:
            item.disabled = True


class NationsManager(commands.Cog):
    """Cog for managing nation viewing and analysis functionality."""
    
    # Using centralized cache instead of local cache
    _cache_expiry = 3600  # Cache expiry in seconds (1 hour)
    
    # Cache for active nations
    _active_nations_cache = {}
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.query_system = None
        
    async def get_alliance_nations(self, alliance_id: str, force_refresh: bool = False) -> Optional[List[Dict[str, Any]]]:
        """Fetch alliance nations with caching to reduce redundant API calls.
        
        Args:
            alliance_id: The alliance ID to fetch nations for
            force_refresh: If True, bypass cache and fetch fresh data
        """
        # Input validation
        if not alliance_id or not str(alliance_id).strip():
            self.logger.warning("get_alliance_nations: Invalid alliance_id provided")
            return None
        
        # Check cache first if not forcing refresh
        cache_key = str(alliance_id)
        current_time = time.time()
        
        if not force_refresh and cache_key in self._alliance_nations_cache:
            cache_entry = self._alliance_nations_cache[cache_key]
            # Use cached data if it's less than expiry time old
            if current_time - cache_entry['timestamp'] < self._cache_expiry:
                self.logger.debug(f"get_alliance_nations: Using cached data for alliance {alliance_id} ({len(cache_entry['data'])} nations)")
                return cache_entry['data']
        
        try:
            # Try to get the query system if not already available
            if not self.query_system:
                from .query import PNWAPIQuery
                self.query_system = PNWAPIQuery()
            
            # Fetch fresh data from API
            nations = await self.query_system.get_alliance_nations(alliance_id, bot=self.bot)
            if nations:
                # Update cache with fresh data
                self._alliance_nations_cache[cache_key] = {
                    'data': nations,
                    'timestamp': current_time
                }
                self.logger.info(f"get_alliance_nations: Retrieved {len(nations)} nations for alliance {alliance_id} from API")
                return nations
            else:
                self.logger.warning(f"get_alliance_nations: No nations returned from API for alliance {alliance_id}")
                return None
            
        except Exception as e:
            self.logger.error(f"Error fetching alliance data for alliance {alliance_id}: {str(e)}")
            return None
            
    def get_active_nations(self, nations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter nations to exclude vacation mode and applicant members."""
        # Input validation
        if not isinstance(nations, list):
            self.logger.warning("get_active_nations: Invalid nations input, returning empty list")
            return []
        
        if not nations:
            self.logger.debug("get_active_nations: Empty nations list provided")
            return []
        
        # Generate a cache key based on the nations list
        # Use a simple hash of nation IDs to identify this specific list
        try:
            nation_ids = tuple(sorted([str(nation.get('id', '')) for nation in nations if isinstance(nation, dict)]))
            cache_key = hash(nation_ids)
            
            # Check if we have this result cached
            if cache_key in self._active_nations_cache:
                self.logger.debug(f"get_active_nations: Using cached result for {len(nations)} nations")
                return self._active_nations_cache[cache_key]
                
            self.logger.debug(f"get_active_nations: Processing {len(nations)} nations")
            
            active_nations = []
            for nation in nations:
                if not isinstance(nation, dict):
                    continue
                
                # Skip vacation mode members
                vacation_turns = nation.get('vacation_mode_turns', 0)
                if vacation_turns > 0:
                    continue
                
                # Skip applicants (alliance_position "APPLICANT")
                alliance_position = nation.get('alliance_position', '')
                if alliance_position == 'APPLICANT':
                    continue
                
                active_nations.append(nation)
            
            # Cache the result
            self._active_nations_cache[cache_key] = active_nations
            
            self.logger.info(f"get_active_nations: Filtered {len(nations)} nations to {len(active_nations)} active nations")
            return active_nations
            
        except Exception as e:
            self.logger.error(f"Unexpected error in get_active_nations: {str(e)}")
            return []
        
        # Initialize user data manager for cache access
        self.user_data_manager = UserDataManager()
        self.logger.info("NationsManager: UserDataManager initialized for cache access")

    def _validate_input(self, value: Any, expected_type: type, param_name: str) -> bool:
        """Validate input parameters."""
        if not isinstance(value, expected_type):
            self.logger.warning(f"Invalid {param_name}: expected {expected_type.__name__}, got {type(value).__name__}")
            return False
        return True

    def _safe_get(self, data: Dict[str, Any], key: str, default: Any = None, expected_type: type = None) -> Any:
        """Safely get a value from a dictionary with type checking."""
        try:
            value = data.get(key, default)
            if expected_type and value is not None and not isinstance(value, expected_type):
                return default
            return value
        except Exception:
            return default

    def _log_error(self, message: str, exception: Exception, method_name: str):
        """Log error with context."""
        self.logger.error(f"{method_name}: {message} - {str(exception)}")

    async def get_alliance_nations(self, alliance_id: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch alliance nations from alliance cache file."""
        # Input validation
        if not alliance_id or not str(alliance_id).strip():
            self.logger.warning("get_alliance_nations: Invalid alliance_id provided")
            return None
        
        try:
            # Read from alliance cache
            alliance_cache = await self.user_data_manager.get_json_data('alliance_cache', {})
            
            if not alliance_cache:
                self.logger.warning("get_alliance_nations: No alliance cache data found. Run /ma command first to populate cache.")
                return None
            
            # Generate cache key (same format as query.py)
            cache_key = f"alliance_data_{alliance_id}"
            
            if cache_key not in alliance_cache:
                self.logger.warning(f"get_alliance_nations: No cached data found for alliance {alliance_id}. Run /ma command first.")
                return None
            
            cache_entry = alliance_cache[cache_key]
            nations_data = cache_entry.get('nations', [])
            
            if not nations_data:
                self.logger.warning(f"get_alliance_nations: Empty nations data in cache for alliance {alliance_id}")
                return None
            
            self.logger.info(f"get_alliance_nations: Retrieved {len(nations_data)} nations from cache for alliance {alliance_id}")
            return nations_data
            
        except Exception as e:
            self._log_error(f"Error reading alliance cache for alliance {alliance_id}", e, "get_alliance_nations")
            return None

    def get_nation_specialty(self, nation: Dict[str, Any]) -> str:
        """Get a nation's military specialty based on unit distribution."""
        soldiers = nation.get('soldiers', 0)
        tanks = nation.get('tanks', 0)
        aircraft = nation.get('aircraft', 0)
        ships = nation.get('ships', 0)
        
        total_units = soldiers + tanks + aircraft + ships
        if total_units == 0:
            return "Generalist"

        ground_percent = (soldiers + tanks) / total_units
        air_percent = aircraft / total_units
        naval_percent = ships / total_units

        if ground_percent >= air_percent and ground_percent >= naval_percent:
            return "Ground"
        elif air_percent >= naval_percent:
            return "Air"
        else:
            return "Naval"

    def calculate_combat_score(self, nation: Dict[str, Any]) -> float:
        """Calculate a nation's combat effectiveness score."""
        soldiers = nation.get('soldiers', 0)
        tanks = nation.get('tanks', 0)
        aircraft = nation.get('aircraft', 0)
        ships = nation.get('ships', 0)
        
        # Weighted combat score (tanks and aircraft are more valuable)
        return soldiers + (tanks * 2) + (aircraft * 3) + (ships * 4)

    def has_project(self, nation: Dict[str, Any], project_name: str) -> bool:
        """Check if a nation has a specific project."""
        # Input validation
        if not self._validate_input(nation, dict, "nation"):
            self.logger.warning("has_project: Invalid nation input")
            return False
        
        if not self._validate_input(project_name, str, "project_name"):
            self.logger.warning("has_project: Invalid project_name input")
            return False
        
        if not project_name.strip():
            self.logger.warning("has_project: Empty project_name provided")
            return False
        
        try:
            # Map project names to their corresponding API field names
            project_field_mapping = {
                'Iron Dome': 'iron_dome',
                'Missile Launch Pad': 'missile_launch_pad',
                'Nuclear Research Facility': 'nuclear_research_facility',
                'Nuclear Launch Facility': 'nuclear_launch_facility',
                'Vital Defense System': 'vital_defense_system',
                'Propaganda Bureau': 'propaganda_bureau',
                'Military Research Center': 'military_research_center',
                'Space Program': 'space_program'
            }
            
            # Use individual Boolean fields from the API
            field_name = project_field_mapping.get(project_name)
            if field_name:
                project_value = self._safe_get(nation, field_name, False, bool)
                self.logger.debug(f"has_project: Project '{project_name}' -> field '{field_name}' = {project_value}")
                return project_value
            else:
                self.logger.warning(f"has_project: Unknown project name '{project_name}'")
                return False
        
        except Exception as e:
            self._log_error(f"Unexpected error checking project '{project_name}'", e, "has_project")
            return False

    def calculate_military_purchase_limits(self, nation: Dict[str, Any]) -> Dict[str, int]:
        """Calculate daily military purchase limits and maximum capacities based on improvements."""
        cities_data = nation.get('cities', [])
        num_cities = nation.get('num_cities', 0)
        
        # Initialize totals
        total_barracks = 0
        total_factories = 0
        total_hangars = 0
        total_drydocks = 0
        
        # Check if we have detailed city data or just city count
        if isinstance(cities_data, list) and len(cities_data) > 0:
            # Sum improvements across all cities (detailed data)
            for city in cities_data:
                total_barracks += city.get('barracks', 0)
                total_factories += city.get('factory', 0)
                total_hangars += city.get('airforcebase', 0)  # API uses 'airforcebase' for hangars
                total_drydocks += city.get('drydock', 0)
        else:
            # Use estimated values based on city count (fallback)
            avg_improvements_per_city = 2  # Conservative estimate
            total_barracks = num_cities * avg_improvements_per_city
            total_factories = num_cities * avg_improvements_per_city
            total_hangars = num_cities * avg_improvements_per_city
            total_drydocks = num_cities * avg_improvements_per_city
        
        # Daily production limits
        soldier_daily_limit = total_barracks * 1000  # 1,000 soldiers per barracks per day
        tank_daily_limit = total_factories * 50      # 50 tanks per factory per day
        aircraft_daily_limit = total_hangars * 3     # 3 aircraft per hangar per day
        ship_daily_limit = total_drydocks * 1        # 1 ship per drydock per day
        
        # Apply military research bonuses (each level adds 20% capacity)
        ground_research = nation.get('ground_research', 0)
        air_research = nation.get('air_research', 0)
        naval_research = nation.get('naval_research', 0)
        
        ground_research_multiplier = 1 + (ground_research * 0.2)
        air_research_multiplier = 1 + (air_research * 0.2)
        naval_research_multiplier = 1 + (naval_research * 0.2)
        
        soldier_daily_limit = int(soldier_daily_limit * ground_research_multiplier)
        tank_daily_limit = int(tank_daily_limit * ground_research_multiplier)
        aircraft_daily_limit = int(aircraft_daily_limit * air_research_multiplier)
        ship_daily_limit = int(ship_daily_limit * naval_research_multiplier)
        
        # Apply Propaganda Bureau bonus (50% increase to soldier production only)
        if self.has_project(nation, 'Propaganda Bureau'):
            soldier_daily_limit = int(soldier_daily_limit * 1.5)
        
        # Base capacity limits from infrastructure
        soldier_max_capacity = total_barracks * 3000  # 3,000 soldiers max per barracks
        tank_max_capacity = total_factories * 250     # 250 tanks max per factory
        aircraft_max_capacity = total_hangars * 15    # 15 aircraft max per hangar
        ship_max_capacity = total_drydocks * 5        # 5 ships max per drydock
        
        # Apply military research multipliers to max capacities
        soldier_max_capacity = int(soldier_max_capacity * ground_research_multiplier)
        tank_max_capacity = int(tank_max_capacity * ground_research_multiplier)
        aircraft_max_capacity = int(aircraft_max_capacity * air_research_multiplier)
        ship_max_capacity = int(ship_max_capacity * naval_research_multiplier)
        
        # Apply purchased capacities (from Military Research Center or direct purchases)
        ground_bonus = nation.get('ground_capacity', 0) or 0
        air_bonus = nation.get('air_capacity', 0) or 0
        naval_bonus = nation.get('naval_capacity', 0) or 0
        
        # Also check under military_research if it exists (fallback for API format)
        if not ground_bonus and not air_bonus and not naval_bonus:
            military_research = nation.get('military_research', {})
            ground_bonus = military_research.get('ground_capacity', 0) or 0
            air_bonus = military_research.get('air_capacity', 0) or 0
            naval_bonus = military_research.get('naval_capacity', 0) or 0

        # Apply purchased capacities as flat bonuses
        soldier_max_capacity += ground_bonus
        tank_max_capacity += ground_bonus  # Same ground bonus applies to both soldiers and tanks
        aircraft_max_capacity += air_bonus
        ship_max_capacity += naval_bonus
        
        soldier_max_capacity = min(soldier_max_capacity, 60000)
        tank_max_capacity = min(tank_max_capacity, 5000)
        aircraft_max_capacity = min(aircraft_max_capacity, 300)
        ship_max_capacity = min(ship_max_capacity, 100)

        missile_limit = 0
        nuke_limit = 0
        
        # Enhanced missile production with Space Program
        if self.has_project(nation, 'Missile Launch Pad'):
            missile_limit = 2
            # Space Program allows +1 missile per day (3 total)
            if self.has_project(nation, 'Space Program'):
                missile_limit = 3
        
        # Enhanced nuke production with Space Program
        if self.has_project(nation, 'Nuclear Research Facility'):
            nuke_limit = 1
            if (self.has_project(nation, 'Nuclear Launch Facility') and 
                self.has_project(nation, 'Missile Launch Pad') and
                self.has_project(nation, 'Space Program')):
                nuke_limit = 2
            
        return {
            'soldiers': soldier_daily_limit,
            'tanks': tank_daily_limit,
            'aircraft': aircraft_daily_limit,
            'ships': ship_daily_limit,
            'missiles': missile_limit,
            'nukes': nuke_limit,
            'soldiers_max': soldier_max_capacity,
            'tanks_max': tank_max_capacity,
            'aircraft_max': aircraft_max_capacity,
            'ships_max': ship_max_capacity,
            'total_barracks': total_barracks,
            'total_factories': total_factories,
            'total_hangars': total_hangars,
            'total_drydocks': total_drydocks
        }

    def get_active_nations(self, nations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter nations to exclude vacation mode and applicant members."""
        # Input validation
        if not self._validate_input(nations, list, "nations"):
            self.logger.warning("get_active_nations: Invalid nations input, returning empty list")
            return []
        
        if not nations:
            self.logger.debug("get_active_nations: Empty nations list provided")
            return []
        
        try:
            self.logger.debug(f"get_active_nations: Filtering {len(nations)} nations")
            
            active_nations = []
            for i, nation in enumerate(nations):
                try:
                    if not isinstance(nation, dict):
                        self.logger.warning(f"get_active_nations: Nation at index {i} is not a dictionary, skipping")
                        continue
                    
                    # Skip vacation mode members
                    vacation_turns = self._safe_get(nation, 'vacation_mode_turns', 0, int)
                    if vacation_turns > 0:
                        self.logger.debug(f"get_active_nations: Skipping nation {nation.get('nation_name', 'Unknown')} - on vacation ({vacation_turns} turns)")
                        continue
                    
                    # Skip applicants (alliance_position "APPLICANT")
                    alliance_position = self._safe_get(nation, 'alliance_position', '', str)
                    if alliance_position == 'APPLICANT':
                        self.logger.debug(f"get_active_nations: Skipping nation {nation.get('nation_name', 'Unknown')} - applicant status")
                        continue
                    
                    active_nations.append(nation)
                except (AttributeError, TypeError) as e:
                    self._log_error(f"Error processing nation at index {i}", e, "get_active_nations")
                    continue
            
            self.logger.info(f"get_active_nations: Filtered {len(nations)} nations to {len(active_nations)} active nations")
            return active_nations
            
        except Exception as e:
            self._log_error("Unexpected error in get_active_nations", e, "get_active_nations")
            return []

    def calculate_party_war_range(self, party_members: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate the overlapping war range for a party of nations."""
        if not party_members:
            return {
                'overlapping_min': 0.0,
                'overlapping_max': 0.0,
                'avg_score': 0.0,
                'individual_ranges': []
            }
        
        individual_ranges = []
        total_score = 0
        
        for member in party_members:
            score = member.get('score', 0)
            total_score += score
            
            # Calculate individual attack range (0.75x to 2.5x score)
            min_target = score * 0.75
            max_target = score * 2.5
            
            individual_ranges.append({
                'nation': member.get('nation_name', 'Unknown'),
                'score': score,
                'min_target': min_target,
                'max_target': max_target
            })
        
        # Calculate overlapping range - the range ALL members can attack
        overlapping_min = max(range_data['min_target'] for range_data in individual_ranges)
        overlapping_max = min(range_data['max_target'] for range_data in individual_ranges)
        
        # If there's no overlap, set to 0
        if overlapping_min > overlapping_max:
            overlapping_min = overlapping_max = 0.0
        
        avg_score = total_score / len(party_members) if party_members else 0
        
        return {
            'overlapping_min': overlapping_min,
            'overlapping_max': overlapping_max,
            'avg_score': avg_score,
            'individual_ranges': individual_ranges
        }

def calculate_full_mill_data(self, nations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate Full Mill data - units needed and days to max capacity."""
    try:
        # Get active nations (exclude vacation mode and applicants)
        active_nations = self.get_active_nations(nations)
        
        # Initialize counters for military units
        current_soldiers = 0
        current_tanks = 0
        current_aircraft = 0
        current_ships = 0
        
        max_soldiers = 0
        max_tanks = 0
        max_aircraft = 0
        max_ships = 0
        
        daily_soldiers = 0
        daily_tanks = 0
        daily_aircraft = 0
        daily_ships = 0
        
        total_cities = 0
        total_score = 0
        
        # Process each active nation individually
        for nation in active_nations:
            # Add current military units
            current_soldiers += nation.get('soldiers', 0)
            current_tanks += nation.get('tanks', 0)
            current_aircraft += nation.get('aircraft', 0)
            current_ships += nation.get('ships', 0)
            
            # Add to total cities and score
            total_cities += nation.get('num_cities', 0)
            total_score += nation.get('score', 0)
            
            # Calculate production capabilities
            production_data = self.calculate_military_purchase_limits(nation)
            
            # Add max capacities
            max_soldiers += production_data.get('soldiers_max', 0)
            max_tanks += production_data.get('tanks_max', 0)
            max_aircraft += production_data.get('aircraft_max', 0)
            max_ships += production_data.get('ships_max', 0)
            
            # Add daily production
            daily_soldiers += production_data.get('soldiers', 0)
            daily_tanks += production_data.get('tanks', 0)
            daily_aircraft += production_data.get('aircraft', 0)
            daily_ships += production_data.get('ships', 0)
        
        # Calculate gaps (units needed to reach max)
        soldier_gap = max(0, max_soldiers - current_soldiers)
        tank_gap = max(0, max_tanks - current_tanks)
        aircraft_gap = max(0, max_aircraft - current_aircraft)
        ship_gap = max(0, max_ships - current_ships)
        
        # Calculate days to max (handle division by zero)
        soldier_days = soldier_gap / daily_soldiers if daily_soldiers > 0 else float('inf')
        tank_days = tank_gap / daily_tanks if daily_tanks > 0 else float('inf')
        aircraft_days = aircraft_gap / daily_aircraft if daily_aircraft > 0 else float('inf')
        ship_days = ship_gap / daily_ships if daily_ships > 0 else float('inf')
        
        return {
            'total_nations': len(active_nations),
            'active_nations': len(active_nations),
            'total_cities': total_cities,
            'total_score': total_score,
            'current_soldiers': current_soldiers,
            'current_tanks': current_tanks,
            'current_aircraft': current_aircraft,
            'current_ships': current_ships,
            'max_soldiers': max_soldiers,
            'max_tanks': max_tanks,
            'max_aircraft': max_aircraft,
            'max_ships': max_ships,
            'daily_soldiers': daily_soldiers,
            'daily_tanks': daily_tanks,
            'daily_aircraft': daily_aircraft,
            'daily_ships': daily_ships,
            'soldier_gap': soldier_gap,
            'tank_gap': tank_gap,
            'aircraft_gap': aircraft_gap,
            'ship_gap': ship_gap,
            'soldier_days': soldier_days,
            'tank_days': tank_days,
            'aircraft_days': aircraft_days,
            'ship_days': ship_days
        }
    
    except Exception as e:
        self._log_error(f"Error calculating full mill data: {e}", e, "calculate_full_mill_data")
        return {
            'total_nations': 0,
            'active_nations': 0,
            'total_cities': 0,
            'total_score': 0,
            'current_soldiers': 0,
            'current_tanks': 0,
            'current_aircraft': 0,
            'current_ships': 0,
            'max_soldiers': 0,
            'max_tanks': 0,
            'max_aircraft': 0,
            'max_ships': 0,
            'daily_soldiers': 0,
            'daily_tanks': 0,
            'daily_aircraft': 0,
            'daily_ships': 0,
            'soldier_gap': 0,
            'tank_gap': 0,
            'aircraft_gap': 0,
            'ship_gap': 0,
            'soldier_days': 0,
            'tank_days': 0,
            'aircraft_days': 0,
            'ship_days': 0
        }

async def setup(bot: commands.Bot):
    """Setup function for loading the NationsManager cog."""
    try:
        await bot.add_cog(NationsManager(bot))
        print("✅ NationsManager cog loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load NationsManager cog: {str(e)}")
        raise e
