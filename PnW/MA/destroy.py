import discord
from discord.ext import commands
import requests
import json
import os
import re
from typing import List, Dict, Optional, Any, Tuple
import asyncio
from datetime import datetime
import sys
import logging
import traceback

# Try to import pnwkit, handle gracefully if not available
try:
    import pnwkit
    PNWKIT_AVAILABLE = True
    PNWKIT_ERROR = None
    PNWKIT_SOURCE = "system"
except ImportError as e:
    # Try to use local pnwkit if system version is not available
    try:
        import sys
        import os
        local_packages_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'local_packages')
        if local_packages_dir not in sys.path:
            sys.path.insert(0, local_packages_dir)
        
        import pnwkit
        PNWKIT_AVAILABLE = True
        PNWKIT_ERROR = None
        PNWKIT_SOURCE = "local"
    except ImportError as local_e:
        pnwkit = None
        PNWKIT_AVAILABLE = False
        PNWKIT_ERROR = f"System: {str(e)}, Local: {str(local_e)}"
        PNWKIT_SOURCE = "none"
    except Exception as local_e:
        pnwkit = None
        PNWKIT_AVAILABLE = False
        PNWKIT_ERROR = f"System: {str(e)}, Local unexpected error: {str(local_e)}"
        PNWKIT_SOURCE = "none"
except Exception as e:
    pnwkit = None
    PNWKIT_AVAILABLE = False
    PNWKIT_ERROR = f"Unexpected error: {str(e)}"
    PNWKIT_SOURCE = "none"

# Import config for API keys and settings
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
try:
    from .query import create_query_instance
except ImportError:
    from query import create_query_instance
from config import PANDW_API_KEY, CYBERTRON_ALLIANCE_ID
from Systems.user_data_manager import UserDataManager
import time

class DestroyCog(commands.Cog):
    """Cog for managing war destruction commands."""
    
    def __init__(self, bot: commands.Bot):
        try:
            self.bot = bot
            self.api_key = PANDW_API_KEY
            self.user_data_manager = UserDataManager()
            self.cybertron_alliance_id = CYBERTRON_ALLIANCE_ID
            self.alliance_cache = {}
            self.alliance_cache_timestamp = 0
            self.alliance_cache_ttl = 3600 

            # Setup logging
            self.logger = logging.getLogger(f"{__name__}.DestroyCog")
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)
            
            # Error tracking
            self.error_count = 0
            self.max_errors = 100  # Reset after this many errors to prevent memory issues
            
            # Initialize pnwkit if available
            self.pnwkit_available = False
            try:
                if pnwkit:
                    self.query_kit = pnwkit.QueryKit(self.api_key)
                    self.pnwkit_available = True
                    self.logger.info("pnwkit initialized successfully")
                else:
                    self.logger.warning("pnwkit not available - using fallback methods")
            except Exception as e:
                self.logger.error(f"Error initializing pnwkit: {e}")
                self.pnwkit_available = False
            
            # Initialize centralized query instance
            try:
                self.query_instance = create_query_instance()
                self.logger.info("Centralized query instance initialized successfully")
                # Set to use 1-hour cache expiry for alliance data
                if hasattr(self.query_instance, 'cache_ttl_seconds'):
                    self.query_instance.cache_ttl_seconds = 3600  # 1 hour

            except Exception as e:
                self.logger.error(f"Failed to initialize query instance: {e}")
                self.query_instance = None
        except Exception as e:
            # Fallback logging if logger setup failed
            print(f"Error initializing DestroyCog: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            # Set safe defaults
            self.bot = bot
            self.api_key = None
            self.user_data_manager = None
            self.error_count = 0
            self.max_errors = 100
            self.pnwkit_available = False
            self.bot = bot
            self.api_key = PANDW_API_KEY
            self.user_data_manager = UserDataManager()
            self.cybertron_alliance_id = CYBERTRON_ALLIANCE_ID
            self.alliance_cache = {}
            self.alliance_cache_timestamp = 0
            self.alliance_cache_ttl = 3600 

            # Setup logging
            self.logger = logging.getLogger(f"{__name__}.DestroyCog")
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)
            
            # Error tracking
            self.error_count = 0
            self.max_errors = 100  # Reset after this many errors to prevent memory issues
            
            # Initialize pnwkit if available
            self.pnwkit_available = False
            try:
                if pnwkit:
                    self.query_kit = pnwkit.QueryKit(self.api_key)
                    self.pnwkit_available = True
                    self.logger.info("pnwkit initialized successfully")
                else:
                    self.logger.warning("pnwkit not available - using fallback methods")
            except Exception as e:
                self.logger.error(f"Error initializing pnwkit: {e}")
                self.pnwkit_available = False
            
            # Initialize centralized query instance
            try:
                self.query_instance = create_query_instance()
                self.logger.info("Centralized query instance initialized successfully")
                # Set to use 1-hour cache expiry for alliance data
                if hasattr(self.query_instance, 'cache_ttl_seconds'):
                    self.query_instance.cache_ttl_seconds = 3600  # 1 hour

            except Exception as e:
                self.logger.error(f"Failed to initialize query instance: {e}")
                self.query_instance = None
                
    async def get_alliance_nations(self, alliance_id: str) -> List[Dict[str, Any]]:
        """
        Get alliance nations data from cache or API.
        
        Args:
            alliance_id: The alliance ID to fetch data for
            
        Returns:
            List of nation dictionaries or empty list if not found
        """
        try:
            # Try to get from centralized cache first
            cache_key = f"alliance_data_{alliance_id}"
            alliance_cache = await self.user_data_manager.get_json_data('alliance_cache', {})
            
            if cache_key in alliance_cache:
                cache_entry = alliance_cache[cache_key]
                cache_timestamp = cache_entry.get('timestamp', 0)
                cache_age = time.time() - cache_timestamp
                
                # If cache is fresh (less than TTL), use it
                if cache_age < self.alliance_cache_ttl:
                    nations_data = cache_entry.get('nations', [])
                    self.logger.info(f"get_alliance_nations: Retrieved {len(nations_data)} nations from cache for alliance {alliance_id}")
                    return nations_data
            
            # If we get here, cache is missing or stale
            self.logger.info(f"get_alliance_nations: Cache miss for alliance {alliance_id}, fetching from API")
            
            # Try to use query instance if available
            if self.query_instance:
                nations = await self.query_instance.get_alliance_nations(alliance_id, bot=self.bot)
                
                # Store in cache for future use
                if nations:
                    try:
                        alliance_cache[cache_key] = {
                            'timestamp': time.time(),
                            'nations': nations
                        }
                        await self.user_data_manager.save_json_data('alliance_cache', alliance_cache)
                        self.logger.info(f"get_alliance_nations: Stored {len(nations)} nations in cache for alliance {alliance_id}")
                    except Exception as cache_error:
                        self.logger.error(f"Error storing alliance data in cache: {cache_error}")
                
                return nations or []
            
            # Fallback to empty list if all methods fail
            self.logger.warning(f"get_alliance_nations: Failed to get nations for alliance {alliance_id}")
            return []
            
        except Exception as e:
            self._log_error(f"Error in get_alliance_nations for alliance {alliance_id}", e, "get_alliance_nations")
            return []
                
        except Exception as e:
            # Fallback logging if logger setup failed
            print(f"Error initializing DestroyCog: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            # Set safe defaults
            self.bot = bot
            self.api_key = None
            self.user_data_manager = None
            self.error_count = 0
            self.max_errors = 100
            self.pnwkit_available = False
    
    def _log_error(self, error_msg: str, exception: Exception = None, context: str = ""):
        """
        Centralized error logging with tracking.
        
        Args:
            error_msg: Error message to log
            exception: Optional exception object
            context: Optional context information
        """
        try:
            self.error_count += 1
            
            # Reset error count if it gets too high
            if self.error_count > self.max_errors:
                self.error_count = 1
                self.logger.warning(f"Error count reset after reaching {self.max_errors}")
            
            # Format error message
            full_msg = f"[Error #{self.error_count}] {error_msg}"
            if context:
                full_msg += f" (Context: {context})"
            
            # Log the error
            if hasattr(self, 'logger') and self.logger:
                self.logger.error(full_msg)
                if exception:
                    self.logger.error(f"Exception details: {str(exception)}")
                    self.logger.error(f"Traceback: {traceback.format_exc()}")
            else:
                # Fallback to print if logger not available
                print(full_msg)
                if exception:
                    print(f"Exception details: {str(exception)}")
                    print(f"Traceback: {traceback.format_exc()}")
                    
        except Exception as log_error:
            # Last resort error handling
            print(f"Error in error logging: {log_error}")
            print(f"Original error: {error_msg}")
    
    def _validate_input(self, data: Any, expected_type: type, field_name: str = "data") -> bool:
        """
        Validate input data type and log errors if invalid.
        
        Args:
            data: Data to validate
            expected_type: Expected data type
            field_name: Name of the field for error messages
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if not isinstance(data, expected_type):
                self._log_error(f"Invalid {field_name} type. Expected {expected_type.__name__}, got {type(data).__name__}")
                return False
            return True
        except Exception as e:
            self._log_error(f"Error validating {field_name}", e)
            return False
    
    def _safe_get(self, data: Dict[str, Any], key: str, default: Any = None, expected_type: type = None) -> Any:
        """
        Safely get value from dictionary with type checking.
        
        Args:
            data: Dictionary to get value from
            key: Key to retrieve
            default: Default value if key not found
            expected_type: Expected type for validation
            
        Returns:
            Value from dictionary or default
        """
        try:
            if not isinstance(data, dict):
                self._log_error(f"Expected dict for _safe_get, got {type(data).__name__}")
                return default
            
            value = data.get(key, default)
            
            if expected_type and value is not None and not isinstance(value, expected_type):
                self._log_error(f"Invalid type for key '{key}'. Expected {expected_type.__name__}, got {type(value).__name__}")
                return default
            
            return value
            
        except Exception as e:
            self._log_error(f"Error in _safe_get for key '{key}'", e)
            return default

    async def parse_target_input(self, target_data: str) -> Tuple[Optional[str], str]:
        """
        Parse target input and determine the type and value.
        
        Args:
            target_data: Input string containing nation name, leader name, nation ID, or nation link
            
        Returns:
            Tuple of (nation_id, input_type) where input_type is one of:
            'nation_id', 'nation_name', 'leader_name', 'nation_link'
        """
        try:
            target_data = target_data.strip()
            
            # Check if it's a nation link
            link_patterns = [
                r'https?://politicsandwar\.com/nation/id=(\d+)',
                r'https?://www\.politicsandwar\.com/nation/id=(\d+)',
                r'politicsandwar\.com/nation/id=(\d+)',
                r'www\.politicsandwar\.com/nation/id=(\d+)'
            ]
            
            for pattern in link_patterns:
                try:
                    match = re.search(pattern, target_data)
                    if match:
                        return match.group(1), 'nation_link'
                except Exception as e:
                    self.logger.warning(f"Error processing link pattern {pattern}: {str(e)}")
                    continue
            
            # Check if it's a pure nation ID (numeric)
            if target_data.isdigit():
                return target_data, 'nation_id'
            
            # If it contains spaces or special characters, likely a nation name
            if ' ' in target_data or any(char in target_data for char in ['-', '_', '.', "'"]):
                return None, 'nation_name'
            
            # Otherwise, assume it's a leader name
            return None, 'leader_name'
        except Exception as e:
            self._log_error(f"Error in parse_target_input: {str(e)}", e, "parse_target_input")
            return None, 'leader_name'

    async def fetch_target_nation(self, target_data: str, input_type: str) -> Optional[Dict[str, Any]]:
        """
        Fetch comprehensive target nation data from P&W API with military analysis.
        
        Args:
            target_data: The target identifier
            input_type: Type of input ('nation_id', 'nation_name', 'leader_name', 'nation_link')
            
        Returns:
            Nation data dictionary with comprehensive military analysis or None if not found
        """
        try:
            # Input validation
            if not self._validate_input(target_data, str, "target_data"):
                return None
            
            if not self._validate_input(input_type, str, "input_type"):
                return None
            
            if not target_data.strip():
                self._log_error("Empty target_data provided", context="fetch_target_nation")
                return None
            
            valid_input_types = ['nation_id', 'nation_name', 'leader_name', 'nation_link']
            if input_type not in valid_input_types:
                self._log_error(f"Invalid input_type: {input_type}. Must be one of {valid_input_types}", context="fetch_target_nation")
                return None
            
            # Use centralized query instance
            if not hasattr(self, 'query_instance') or self.query_instance is None:
                self._log_error("Query instance not available", context="fetch_target_nation")
                return None
            
            self.logger.info(f"Fetching target nation data for {input_type}: {target_data}")
            
            # Use appropriate method from query instance based on input type
            target_nation = None
            try:
                if input_type == 'nation_id' or input_type == 'nation_link':
                    # For nation ID, we already have the ID from parsing
                    if input_type == 'nation_link':
                        nation_id = target_data  # This is already extracted from the link
                    else:
                        nation_id = target_data
                    target_nation = await self.query_instance.get_nation_by_id(nation_id)
                elif input_type == 'nation_name':
                    target_nation = await self.query_instance.get_nation_by_name(target_data)
                elif input_type == 'leader_name':
                    target_nation = await self.query_instance.get_nation_by_leader(target_data)
                
                if not target_nation:
                    self.logger.info(f"No nation found for {input_type}: {target_data}")
                    return None
                
                # Add comprehensive military analysis similar to blitz.py
                try:
                    target_nation['military_analysis'] = self.calculate_target_military_analysis(target_nation)
                    self.logger.info(f"Successfully fetched and analyzed nation: {target_nation.get('nation_name', 'Unknown')}")
                except Exception as e:
                    self._log_error("Error calculating military analysis", e, "fetch_target_nation")
                    target_nation['military_analysis'] = {}
                
                return target_nation
                
            except Exception as e:
                self._log_error("Error fetching nation data from query instance", e, "fetch_target_nation")
                return None
                
        except Exception as e:
            self._log_error("Unexpected error in fetch_target_nation", e, "fetch_target_nation")
            return None

    def load_blitz_parties(self) -> List[Dict[str, Any]]:
        """
        Load the most recent blitz party data from user_data_manager.
        
        Returns:
            List of blitz party dictionaries
        """
        try:
            return self.user_data_manager.get_saved_blitz_parties()
        except Exception as e:
            self._log_error(f"Error loading blitz parties: {str(e)}", e, "load_blitz_parties")
            return []

    def calculate_target_military_analysis(self, nation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate comprehensive military analysis for a target nation using the same logic as blitz.py.
        
        Args:
            nation: Nation data dictionary
            
        Returns:
            Military analysis dictionary matching blitz.py structure
        """
        try:
            # Validate input
            if not self._validate_input(nation, dict, "nation"):
                self._log_error("Invalid nation data for military analysis", context="calculate_target_military_analysis")
                return self._get_default_target_military_analysis()
            
            # Get basic military data with safe extraction
            try:
                current_military = {
                    'soldiers': max(0, int(self._safe_get(nation, 'soldiers', 0, (int, float)) or 0)),
                    'tanks': max(0, int(self._safe_get(nation, 'tanks', 0, (int, float)) or 0)),
                    'aircraft': max(0, int(self._safe_get(nation, 'aircraft', 0, (int, float)) or 0)),
                    'ships': max(0, int(self._safe_get(nation, 'ships', 0, (int, float)) or 0))
                }
            except (ValueError, TypeError) as e:
                self._log_error("Error extracting military unit data", e, "calculate_target_military_analysis")
                current_military = {'soldiers': 0, 'tanks': 0, 'aircraft': 0, 'ships': 0}
            
            # Calculate purchase limits
            purchase_limits = {}
            try:
                purchase_limits = self.calculate_target_purchase_limits(nation)
            except Exception as e:
                self._log_error("Error calculating purchase limits", e, "calculate_target_military_analysis")
                purchase_limits = {
                    'soldiers': 0,
                    'tanks': 0,
                    'aircraft': 0,
                    'ships': 0
                }
            
            # Calculate theoretical maximum capacities (same logic as blitz.py)
            try:
                num_cities = max(0, int(self._safe_get(nation, 'num_cities', 0, (int, float)) or 0))
                theoretical_max_soldiers = num_cities * 5 * 3000  # 5 Barracks per city, 3000 soldiers per Barracks
                theoretical_max_tanks = num_cities * 5 * 250     # 5 Factories per city, 250 tanks per Factory
                theoretical_max_aircraft = num_cities * 5 * 18   # 5 Hangars per city, 18 aircraft per Hangar
                theoretical_max_ships = num_cities * 3 * 5       # 3 Harbors per city, 5 ships per Harbor
            except (ValueError, TypeError, OverflowError) as e:
                self._log_error("Error calculating theoretical maximum capacities", e, "calculate_target_military_analysis")
                num_cities = 0
                theoretical_max_soldiers = theoretical_max_tanks = theoretical_max_aircraft = theoretical_max_ships = 0
            
            # Calculate unit percentages
            soldier_percentage = (current_military['soldiers'] / theoretical_max_soldiers * 100) if theoretical_max_soldiers > 0 else 0
            tank_percentage = (current_military['tanks'] / theoretical_max_tanks * 100) if theoretical_max_tanks > 0 else 0
            aircraft_percentage = (current_military['aircraft'] / theoretical_max_aircraft * 100) if theoretical_max_aircraft > 0 else 0
            ship_percentage = (current_military['ships'] / theoretical_max_ships * 100) if theoretical_max_ships > 0 else 0
            
            # Calculate ground score (tanks weighted twice as much as soldiers)
            current_ground_score = current_military['soldiers'] + (current_military['tanks'] * 2)
            theoretical_max_ground_score = theoretical_max_soldiers + (theoretical_max_tanks * 2)
            ground_percentage = (current_ground_score / theoretical_max_ground_score * 100) if theoretical_max_ground_score > 0 else 0
            
            # Determine if "heavy" in each unit type (60% threshold)
            is_heavy_ground = ground_percentage > 60
            is_heavy_air = aircraft_percentage > 60
            is_heavy_naval = ship_percentage > 60
            
            # Check for high purchase capacity (minimum thresholds for advantages)
            high_ground_purchase = (purchase_limits.get('soldiers', 0) >= 10000 or purchase_limits.get('tanks', 0) >= 1500)
            high_air_purchase = purchase_limits.get('aircraft', 0) >= 200
            high_naval_purchase = purchase_limits.get('ships', 0) >= 40
            
            # Determine advantages
            advantages = []
            has_ground_advantage = is_heavy_ground and high_ground_purchase
            has_air_advantage = is_heavy_air and high_air_purchase
            has_naval_advantage = is_heavy_naval and high_naval_purchase
            
            if has_ground_advantage:
                advantages.append("Ground Advantage")
            if has_air_advantage:
                advantages.append("Air Advantage")
            if has_naval_advantage:
                advantages.append("Naval Advantage")
            
            # Strategic capabilities
            can_missile = self.has_project(nation, 'Missile Launch Pad')
            can_nuke = self.has_project(nation, 'Nuclear Research Facility')
            
            if can_missile:
                advantages.append("Missile Capable")
            if can_nuke:
                advantages.append("Nuclear Capable")
            
            # Calculate attack range
            attack_range = {}
            try:
                attack_range = self.calculate_target_attack_range(nation)
            except Exception as e:
                self._log_error("Error calculating attack range", e, "calculate_target_military_analysis")
                attack_range = {}
            
            return {
                'advantages': advantages,
                'purchase_limits': purchase_limits,
                'current_military': current_military,
                'can_missile': can_missile,
                'can_nuke': can_nuke,
                'has_ground_advantage': has_ground_advantage,
                'has_air_advantage': has_air_advantage,
                'has_naval_advantage': has_naval_advantage,
                'attack_range': attack_range,
                'military_composition': {
                    'current_soldiers': current_military['soldiers'],
                    'current_tanks': current_military['tanks'],
                    'current_aircraft': current_military['aircraft'],
                    'current_ships': current_military['ships'],
                    'theoretical_max_soldiers': theoretical_max_soldiers,
                    'theoretical_max_tanks': theoretical_max_tanks,
                    'theoretical_max_aircraft': theoretical_max_aircraft,
                    'theoretical_max_ships': theoretical_max_ships,
                    'soldier_percentage': soldier_percentage,
                    'tank_percentage': tank_percentage,
                    'aircraft_percentage': aircraft_percentage,
                    'ship_percentage': ship_percentage,
                    'ground_percentage': ground_percentage,
                    'current_ground_score': current_ground_score,
                    'theoretical_max_ground_score': theoretical_max_ground_score,
                    'is_heavy_ground': is_heavy_ground,
                    'is_heavy_air': is_heavy_air,
                    'is_heavy_naval': is_heavy_naval
                },
                'strategic_capabilities': {
                    'missiles': nation.get('missiles', 0) > 0,
                    'nukes': nation.get('nukes', 0) > 0,
                    'projects': {
                        'missile_launch_pad': can_missile,
                        'nuclear_research_facility': can_nuke,
                        'iron_dome': self.has_project(nation, 'Iron Dome'),
                        'vital_defense_system': self.has_project(nation, 'Vital Defense System'),
                        'propaganda_bureau': self.has_project(nation, 'Propaganda Bureau'),
                        'military_research_center': self.has_project(nation, 'Military Research Center'),
                        'space_program': self.has_project(nation, 'Space Program')
                    }
                },
                'military_research': nation.get('military_research', {})
            }
            
        except Exception as e:
            self._log_error("Unexpected error in target military analysis calculation", e, "calculate_target_military_analysis")
            return self._get_default_target_military_analysis()
    
    def _get_default_target_military_analysis(self) -> Dict[str, Any]:
        """Return default target military analysis structure for error cases"""
        return {
            'advantages': [],
            'purchase_limits': {},
            'current_military': {},
            'can_missile': False,
            'can_nuke': False,
            'has_ground_advantage': False,
            'has_air_advantage': False,
            'has_naval_advantage': False,
            'attack_range': {},
            'military_composition': {},
            'strategic_capabilities': {
                'missiles': False,
                'nukes': False,
                'projects': {}
            },
            'military_research': {}
        }
    
    def calculate_target_purchase_limits(self, nation: Dict[str, Any]) -> Dict[str, int]:
        """
        Calculate purchase limits for target nation based on cities and infrastructure.
        
        Args:
            nation: Nation data dictionary
            
        Returns:
            Dictionary with purchase limits for each unit type
        """
        try:
            # Validate input
            if not self._validate_input(nation, dict, "nation"):
                self._log_error("Invalid nation data for purchase limits calculation", context="calculate_target_purchase_limits")
                return {'soldiers': 0, 'tanks': 0, 'aircraft': 0, 'ships': 0}
            
            # Extract num_cities safely
            try:
                num_cities = max(0, int(self._safe_get(nation, 'num_cities', 0, (int, float)) or 0))
            except (ValueError, TypeError) as e:
                self._log_error("Error extracting num_cities", e, "calculate_target_purchase_limits")
                num_cities = 0
            
            avg_infrastructure = 0
            
            # Calculate average infrastructure across all cities
            cities = self._safe_get(nation, 'cities', [], list)
            if cities and isinstance(cities, list):
                try:
                    total_infra = 0
                    valid_cities = 0
                    for city in cities:
                        if isinstance(city, dict):
                            infra = self._safe_get(city, 'infrastructure', 0, (int, float))
                            if infra is not None:
                                total_infra += float(infra)
                                valid_cities += 1
                    
                    if valid_cities > 0:
                        avg_infrastructure = total_infra / valid_cities
                except Exception as e:
                    self._log_error("Error calculating average infrastructure", e, "calculate_target_purchase_limits")
                    avg_infrastructure = 0
            
            # Calculate purchase limits (similar to blitz.py logic)
            limits = {
                'soldiers': min(15, num_cities * 3),
                'tanks': min(15, num_cities * 2),
                'aircraft': min(15, num_cities),
                'ships': min(15, num_cities // 2)
            }
            
            # Infrastructure-based bonuses
            try:
                if avg_infrastructure >= 1000:
                    limits['soldiers'] = min(25, limits['soldiers'] + 5)
                    limits['tanks'] = min(20, limits['tanks'] + 3)
                if avg_infrastructure >= 2000:
                    limits['aircraft'] = min(20, limits['aircraft'] + 3)
                if avg_infrastructure >= 3000:
                    limits['ships'] = min(20, limits['ships'] + 3)
            except Exception as e:
                self._log_error("Error applying infrastructure bonuses", e, "calculate_target_purchase_limits")
            
            self.logger.debug(f"Purchase limits calculated: {limits} (cities: {num_cities}, avg_infra: {avg_infrastructure:.1f})")
            return limits
            
        except Exception as e:
            self._log_error("Unexpected error calculating target purchase limits", e, "calculate_target_purchase_limits")
            return {
                'soldiers': 0,
                'tanks': 0,
                'aircraft': 0,
                'ships': 0
            }
    
    def calculate_target_attack_range(self, nation: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate attack range for target nation.
        
        Args:
            nation: Nation data dictionary
            
        Returns:
            Dictionary with min and max attack range
        """
        try:
            nation_score = nation.get('score', 0)
            
            if nation_score <= 0:
                self.logger.warning(f"Invalid nation score: {nation_score}")
                return {
                    'min_range': 0.0,
                    'max_range': 0.0,
                    'current_score': 0.0
                }
            
            # Calculate attack range based on nation score
            min_range = nation_score * 0.75
            max_range = nation_score * 1.25
            
            return {
                'min_range': min_range,
                'max_range': max_range,
                'current_score': nation_score
            }
            
        except Exception as e:
            self._log_error(f"Error calculating target attack range: {str(e)}", e, "calculate_target_attack_range")
            return {
                'min_range': 0.0,
                'max_range': 0.0,
                'current_score': 0.0
            }

    def calculate_combat_score(self, nation: Dict[str, Any]) -> float:
        """
        Calculate combat score for a nation.
        
        Args:
            nation: Nation data dictionary
            
        Returns:
            Combat score as float
        """
        try:
            # Basic combat score calculation
            soldiers = nation.get('soldiers', 0)
            tanks = nation.get('tanks', 0) * 3
            aircraft = nation.get('aircraft', 0) * 4
            ships = nation.get('ships', 0) * 6
            
            return soldiers + tanks + aircraft + ships
            
        except Exception as e:
            self._log_error(f"Error calculating combat score: {str(e)}", e, "calculate_combat_score")
            return 0.0

    def has_project(self, nation: Dict[str, Any], project_name: str) -> bool:
        """Check if a nation has a specific project.
        Supports both human-readable names (e.g., 'Missile Launch Pad') and
        API field names (e.g., 'missile_launch_pad'). Prefers boolean fields
        returned by our GraphQL queries and falls back to scanning the
        projects list if present.
        """
        try:
            # Map display names to API boolean fields
            name_to_field = {
                'Iron Dome': 'iron_dome',
                'Missile Launch Pad': 'missile_launch_pad',
                'Nuclear Research Facility': 'nuclear_research_facility',
                'Nuclear Launch Facility': 'nuclear_launch_facility',
                'Vital Defense System': 'vital_defense_system',
                'Propaganda Bureau': 'propaganda_bureau',
                'Military Research Center': 'military_research_center',
                'Space Program': 'space_program',
            }
            field_set = set(name_to_field.values())

            # Determine the API field key to check
            if project_name in name_to_field:
                field_key = name_to_field[project_name]
                display_name = project_name
            elif project_name in field_set:
                field_key = project_name
                # Recover a reasonable display name from mapping or fallback
                display_name = next((k for k, v in name_to_field.items() if v == project_name), project_name.replace('_', ' ').title())
            else:
                # Unknown project identifier; try fallback only
                field_key = None
                display_name = project_name

            # Prefer boolean field on the nation (from GraphQL)
            if field_key is not None:
                value = nation.get(field_key, False)
                if isinstance(value, bool):
                    return value

            # Fallback: scan the projects list if provided as names/objects
            projects = nation.get('projects', [])
            if isinstance(projects, list):
                for project in projects:
                    if isinstance(project, str):
                        if display_name.lower() in project.lower():
                            return True
                    elif isinstance(project, dict):
                        project_obj_name = str(project.get('name', ''))
                        if display_name.lower() in project_obj_name.lower():
                            return True

            # If projects is an int or anything else, we cannot reliably infer
            return False
        except Exception as e:
            self._log_error(f"Error checking project {project_name}: {str(e)}", e, "has_project")
            return False

    def validate_attack_range(self, attacker_score: float, defender_score: float) -> bool:
        """
        Validate if attacker can attack defender based on score range.
        
        Args:
            attacker_score: Attacker's nation score
            defender_score: Defender's nation score
            
        Returns:
            True if attack is valid, False otherwise
        """
        try:
            if attacker_score <= 0:
                self.logger.warning(f"Invalid attacker score: {attacker_score}")
                return False
            
            min_range = attacker_score * 0.75
            max_range = attacker_score * 1.75
            
            return min_range <= defender_score <= max_range
            
        except Exception as e:
            self._log_error(f"Error validating attack range: {str(e)}", e, "validate_attack_range")
            return False

    async def find_suitable_parties(self, target_nation: Dict[str, Any], parties: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Find blitz parties suitable for attacking the target nation.
        
        Args:
            target_nation: Target nation data
            parties: List of blitz party data
            
        Returns:
            List of suitable parties with attack analysis
        """
        try:
            target_score = target_nation.get('score', 0)
            suitable_parties = []
            
            if not target_nation:
                self.logger.warning("No target nation provided")
                return []
            
            if not parties:
                self.logger.warning("No parties provided")
                return []
            
            for party in parties:
                try:
                    party_members = party.get('members', [])
                    if not party_members:
                        continue
                    
                    # Check if any party member can attack the target
                    attackers_in_range = []
                    for member in party_members:
                        member_score = member.get('score', 0)
                        if self.validate_attack_range(member_score, target_score):
                            attackers_in_range.append(member)
                    
                    if not attackers_in_range:
                        continue  # No one in this party can attack the target
                    
                    # Calculate party military strength vs target
                    party_analysis = self.analyze_party_vs_target(party, target_nation, attackers_in_range)
                    
                    if party_analysis and party_analysis.get('recommended', False):
                        suitable_parties.append({
                            'party': party,
                            'analysis': party_analysis,
                            'attackers_in_range': attackers_in_range
                        })
                except Exception as e:
                    self.logger.warning(f"Error processing party: {str(e)}")
                    continue
            
            # Sort by recommendation score (highest first)
            try:
                suitable_parties.sort(key=lambda x: x.get('analysis', {}).get('recommendation_score', 0), reverse=True)
            except Exception as e:
                self.logger.warning(f"Error sorting suitable parties: {str(e)}")
            
            return suitable_parties
            
        except Exception as e:
            self._log_error(f"Error finding suitable parties: {str(e)}", e, "find_suitable_parties")
            return []

    def analyze_party_vs_target(self, party: Dict[str, Any], target_nation: Dict[str, Any], attackers_in_range: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze party's chances against target nation.
        
        Args:
            party: Party data dictionary
            target_nation: Target nation data
            attackers_in_range: List of party members who can attack
            
        Returns:
            Analysis dictionary with recommendation score and risk level
        """
        try:
            if not party or not target_nation or not attackers_in_range:
                self.logger.warning("Invalid input to analyze_party_vs_target")
                return {
                    'recommended': False,
                    'recommendation_score': 0.0,
                    'risk_level': 'high',
                    'military_ratio': 0.0,
                    'party_combat_score': 0.0,
                    'target_combat_score': 0.0,
                    'strategic_advantages': {},
                    'target_strategic_defenses': {}
                }
            
            # Calculate military strength comparison
            try:
                target_combat_score = self.calculate_combat_score(target_nation)
                party_combat_score = sum(self.calculate_combat_score(attacker) for attacker in attackers_in_range)
            except Exception as e:
                self.logger.warning(f"Error calculating combat scores: {str(e)}")
                target_combat_score = 0.0
                party_combat_score = 0.0
            
            # Calculate strategic advantages
            try:
                target_strategic = {
                    'missiles': target_nation.get('missiles', 0) > 0,
                    'nukes': target_nation.get('nukes', 0) > 0,
                    'projects': {
                        'iron_dome': self.has_project(target_nation, 'iron_dome'),
                        'vital_defense_system': self.has_project(target_nation, 'vital_defense_system')
                    }
                }
                
                # Calculate party strategic capabilities
                party_missiles = sum(attacker.get('missiles', 0) for attacker in attackers_in_range)
                party_nukes = sum(attacker.get('nukes', 0) for attacker in attackers_in_range)
                party_strategic = {
                    'missiles': party_missiles > 0,
                    'nukes': party_nukes > 0
                }
            except Exception as e:
                self.logger.warning(f"Error calculating strategic capabilities: {str(e)}")
                target_strategic = {'missiles': False, 'nukes': False, 'projects': {}}
                party_strategic = {'missiles': False, 'nukes': False}
            
            # Calculate recommendation score (0.0 to 1.0)
            try:
                military_ratio = party_combat_score / (target_combat_score + 1)  # Avoid division by zero
                
                # Strategic advantage bonus
                strategic_bonus = 0
                if party_strategic.get('missiles', False) and not target_strategic.get('projects', {}).get('iron_dome', False):
                    strategic_bonus += 0.2
                if party_strategic.get('nukes', False) and not target_strategic.get('projects', {}).get('vital_defense_system', False):
                    strategic_bonus += 0.3
                
                # Risk assessment
                risk_level = 'low'
                if military_ratio < 0.8:
                    risk_level = 'high'
                elif military_ratio < 1.2:
                    risk_level = 'medium'
                
                recommendation_score = min(1.0, military_ratio + strategic_bonus)
                
                return {
                    'recommended': recommendation_score >= 0.5,
                    'recommendation_score': recommendation_score,
                    'risk_level': risk_level,
                    'military_ratio': military_ratio,
                    'party_combat_score': party_combat_score,
                    'target_combat_score': target_combat_score,
                    'strategic_advantages': party_strategic,
                    'target_strategic_defenses': target_strategic['projects']
                }
                
            except Exception as e:
                self.logger.warning(f"Error calculating recommendation score: {str(e)}")
                return {
                    'recommended': False,
                    'recommendation_score': 0.0,
                    'risk_level': 'high',
                    'military_ratio': 0.0,
                    'party_combat_score': party_combat_score,
                    'target_combat_score': target_combat_score,
                    'strategic_advantages': party_strategic,
                    'target_strategic_defenses': target_strategic.get('projects', {})
                }
                
        except Exception as e:
            self._log_error(f"Error analyzing party vs target: {str(e)}", e, "analyze_party_vs_target")
            return {
                'recommended': False,
                'recommendation_score': 0.0,
                'risk_level': 'high',
                'military_ratio': 0.0,
                'party_combat_score': 0.0,
                'target_combat_score': 0.0,
                'strategic_advantages': {},
                'target_strategic_defenses': {}
            }

    def create_target_info_embed(self, target_nation: Dict[str, Any]) -> discord.Embed:
        """
        Create Discord embed with target nation information.
        
        Args:
            target_nation: Target nation data
            
        Returns:
            Discord embed with target information
        """
        try:
            if not target_nation:
                self.logger.warning("No target nation provided for embed")
                return discord.Embed(
                    title="❌ Error",
                    description="No target nation data available",
                    color=discord.Color.red()
                )
            
            embed = discord.Embed(
                title=f"🎯 Target: {target_nation.get('nation_name', 'Unknown')} ({target_nation.get('leader_name', 'Unknown')})",
                description=f"Alliance: {target_nation.get('alliance', {}).get('name', 'No Alliance')}",
                color=discord.Color.red()
            )
            
            # Basic stats
            try:
                embed.add_field(name="🌍 Cities", value=f"{target_nation.get('num_cities', 0)}", inline=True)
                embed.add_field(name="📊 Score", value=f"{target_nation.get('score', 0):,.0f}", inline=True)
                embed.add_field(name="🏛️ War Policy", value=target_nation.get('war_policy', 'Unknown'), inline=True)
            except Exception as e:
                self.logger.warning(f"Error adding basic stats to embed: {str(e)}")
            
            # Military units
            try:
                military_text = f"""
                🪖 Soldiers: {target_nation.get('soldiers', 0):,}
                ⚔️ Tanks: {target_nation.get('tanks', 0):,}
                ✈️ Aircraft: {target_nation.get('aircraft', 0):,}
                🚢 Ships: {target_nation.get('ships', 0):,}
                """
                embed.add_field(name="Military Units", value=military_text.strip(), inline=False)
            except Exception as e:
                self.logger.warning(f"Error adding military units to embed: {str(e)}")
            
            # Strategic assets
            try:
                strategic_text = f"""
                🚀 Missiles: {target_nation.get('missiles', 0):,}
                ☢️ Nukes: {target_nation.get('nukes', 0):,}
                """
                embed.add_field(name="Strategic Assets", value=strategic_text.strip(), inline=False)
            except Exception as e:
                self.logger.warning(f"Error adding strategic assets to embed: {str(e)}")
            
            # Projects (prefer API boolean fields, fallback to list if present)
            try:
                project_text = ""
                strategic_projects = [
                    'Missile Launch Pad',
                    'Nuclear Research Facility',
                    'Nuclear Launch Facility',
                    'Iron Dome',
                    'Vital Defense System'
                ]
                for project_name in strategic_projects:
                    if self.has_project(target_nation, project_name):
                        project_text += f"✅ {project_name}\n"
                if project_text:
                    embed.add_field(name="Key Projects", value=project_text.strip(), inline=False)
            except Exception as e:
                self.logger.warning(f"Error adding projects to embed: {str(e)}")
            
            return embed
            
        except Exception as e:
            self._log_error(f"Error creating target info embed: {str(e)}", e, "create_target_info_embed")
            return discord.Embed(
                title="❌ Error",
                description="Failed to create target information embed",
                color=discord.Color.red()
            )

class TargetPartyView(discord.ui.View):
    """Interactive view for displaying target attack parties with pagination and strategic sorting."""
    
    def __init__(self, ctx: commands.Context, target_nation: Dict[str, Any], suitable_parties: List[Dict[str, Any]], cog: DestroyCog):
        super().__init__(timeout=300)  # 5 minute timeout
        try:
            self.ctx = ctx
            self.target_nation = target_nation or {}
            self.suitable_parties = suitable_parties or []
            self.cog = cog
            self.current_page = 0
            self.items_per_page = 1  # Show one party per page for detailed analysis
            
            # Initialize button references
            self.back_button = None
            self.main_button = None
            self.next_button = None
            
            # Update button states
            self.update_buttons()
        except Exception as e:
            if cog and hasattr(cog, '_log_error'):
                cog._log_error(f"Error initializing TargetPartyView: {e}", e, "TargetPartyView.__init__")
            else:
                logging.error(f"Error initializing TargetPartyView: {e}")
            # Set safe defaults
            self.ctx = ctx
            self.cog = cog
            self.target_nation = {}
            self.suitable_parties = []
            self.current_page = 0
            self.items_per_page = 1
            self.back_button = None
            self.main_button = None
            self.next_button = None
    
    def update_buttons(self):
        """Update button states based on current page."""
        try:
            # Back button
            self.back_button.disabled = self.current_page <= 0
            
            # Next button
            max_pages = max(1, len(self.suitable_parties))
            self.next_button.disabled = self.current_page >= max_pages - 1
        except Exception as e:
            if self.cog and hasattr(self.cog, '_log_error'):
                self.cog._log_error(f"Error updating buttons: {e}", e, "TargetPartyView.update_buttons")
            else:
                logging.error(f"Error updating buttons: {e}")
            # Set safe defaults
            self.back_button.disabled = True
            self.next_button.disabled = True
    
    def create_strategic_percentage(self, analysis: Dict[str, Any]) -> str:
        """
        Create strategic percentage based on analysis.
        
        Args:
            analysis: Analysis dictionary containing recommendation score and risk level
            
        Returns:
            Strategic percentage as a formatted string
        """
        try:
            if not analysis:
                if self.cog and hasattr(self.cog, 'logger'):
                    self.cog.logger.warning("No analysis provided for strategic percentage")
                else:
                    logging.warning("No analysis provided for strategic percentage")
                return "0%"
            
            score = analysis.get('recommendation_score', 0)
            risk = analysis.get('risk_level', 'Unknown')
            
            # Validate score
            try:
                score = float(score)
            except (ValueError, TypeError):
                if self.cog and hasattr(self.cog, 'logger'):
                    self.cog.logger.warning(f"Invalid score value: {score}")
                else:
                    logging.warning(f"Invalid score value: {score}")
                score = 0
            
            # Calculate base percentage from score
            base_percentage = min(100, max(0, score * 10))
            
            # Adjust based on risk level
            if risk == 'Low':
                base_percentage += 20
            elif risk == 'High':
                base_percentage -= 30
            elif risk == 'Extreme':
                base_percentage -= 50
                
            # Cap between 0-100
            final_percentage = min(100, max(0, base_percentage))
            
            return f"{final_percentage:.0f}%"
            
        except Exception as e:
            if self.cog and hasattr(self.cog, '_log_error'):
                self.cog._log_error(f"Error creating strategic percentage: {e}", e, "TargetPartyView.create_strategic_percentage")
            else:
                logging.error(f"Error creating strategic percentage: {e}")
            return "0%"
    
    def create_party_embed(self, party_data: Dict[str, Any], page: int) -> discord.Embed:
        """
        Create embed for a single party.
        
        Args:
            party_data: Party data including analysis and military information
            page: Page number for display
            
        Returns:
            Discord embed for the party
        """
        try:
            if not party_data:
                if self.cog and hasattr(self.cog, 'logger'):
                    self.cog.logger.warning("No party data provided for embed")
                else:
                    logging.warning("No party data provided for embed")
                return discord.Embed(
                    title="❌ Error",
                    description="No party data available",
                    color=discord.Color.red()
                )
            
            party = party_data.get('party', {})
            analysis = party_data.get('analysis', {})
            
            if not party or not analysis:
                if self.cog and hasattr(self.cog, 'logger'):
                    self.cog.logger.warning("Missing party or analysis data for embed")
                else:
                    logging.warning("Missing party or analysis data for embed")
                return discord.Embed(
                    title="❌ Error",
                    description="Incomplete party data",
                    color=discord.Color.red()
                )
            
            # Basic party info
            embed = discord.Embed(
                title=f"⚔️ Attack Party #{page + 1}",
                description=f"**Members:** {len(party.get('members', []))} | **Total Score:** {party.get('total_score', 0):,.0f}",
                color=discord.Color.blue()
            )
            
            # Strategic recommendation
            try:
                strategic_percentage = self.create_strategic_percentage(analysis)
                recommendation_text = f"**Strategic Rating:** {strategic_percentage}"
                
                risk_level = analysis.get('risk_level', 'Unknown')
                risk_emoji = '🟢' if risk_level == 'Low' else '🟡' if risk_level == 'Medium' else '🔴'
                recommendation_text += f"\n**Risk Level:** {risk_emoji} {risk_level}"
                
                embed.add_field(name="📊 Strategic Recommendation", value=recommendation_text, inline=False)
            except Exception as e:
                if self.cog and hasattr(self.cog, 'logger'):
                    self.cog.logger.warning(f"Error adding strategic recommendation to embed: {e}")
                else:
                    logging.warning(f"Error adding strategic recommendation to embed: {e}")
            
            # Military comparison
            try:
                military_ratios = analysis.get('military_ratios', {})
                military_text = f"""
                **Overall Ratio:** {military_ratios.get('overall', 0):.1f}x
                **Soldiers:** {military_ratios.get('soldiers', 0):.1f}x
                **Tanks:** {military_ratios.get('tanks', 0):.1f}x
                **Aircraft:** {military_ratios.get('aircraft', 0):.1f}x
                **Ships:** {military_ratios.get('ships', 0):.1f}x
                """
                embed.add_field(name="⚔️ Military Comparison", value=military_text.strip(), inline=True)
            except Exception as e:
                if self.cog and hasattr(self.cog, 'logger'):
                    self.cog.logger.warning(f"Error adding military comparison to embed: {e}")
                else:
                    logging.warning(f"Error adding military comparison to embed: {e}")
            
            # Strategic advantages
            try:
                strategic = analysis.get('strategic_advantages', {})
                strategic_text = f"""
                **Missile Advantage:** {'✅' if strategic.get('missile_advantage', False) else '❌'}
                **Nuke Advantage:** {'✅' if strategic.get('nuke_advantage', False) else '❌'}
                **Iron Dome:** {'✅' if strategic.get('has_iron_dome', False) else '❌'}
                **Vital Defense System:** {'✅' if strategic.get('has_vital_defense_system', False) else '❌'}
                """
                embed.add_field(name="🎯 Strategic Advantages", value=strategic_text.strip(), inline=True)
            except Exception as e:
                if self.cog and hasattr(self.cog, 'logger'):
                    self.cog.logger.warning(f"Error adding strategic advantages to embed: {e}")
                else:
                    logging.warning(f"Error adding strategic advantages to embed: {e}")
            
            # Party military strength
            try:
                party_military = party_data.get('party_military', {})
                party_military_text = f"""
                **Total Soldiers:** {party_military.get('soldiers', 0):,}
                **Total Tanks:** {party_military.get('tanks', 0):,}
                **Total Aircraft:** {party_military.get('aircraft', 0):,}
                **Total Ships:** {party_military.get('ships', 0):,}
                """
                embed.add_field(name="🪖 Party Military Strength", value=party_military_text.strip(), inline=False)
            except Exception as e:
                if self.cog and hasattr(self.cog, 'logger'):
                    self.cog.logger.warning(f"Error adding party military strength to embed: {e}")
                else:
                    logging.warning(f"Error adding party military strength to embed: {e}")
            
            # Attacker information
            try:
                attacker_text = ""
                members = party.get('members', [])
                for i, attacker in enumerate(members):
                    if attacker and isinstance(attacker, dict):
                        leader_name = attacker.get('leader_name', 'Unknown')
                        score = attacker.get('score', 0)
                        attacker_text += f"**{i+1}.** {leader_name} ({score:,.0f})\n"
                
                if attacker_text:
                    embed.add_field(name="👥 Attackers", value=attacker_text.strip(), inline=False)
            except Exception as e:
                if self.cog and hasattr(self.cog, 'logger'):
                    self.cog.logger.warning(f"Error adding attacker information to embed: {e}")
                else:
                    logging.warning(f"Error adding attacker information to embed: {e}")
            
            return embed
            
        except Exception as e:
            if self.cog and hasattr(self.cog, '_log_error'):
                self.cog._log_error(f"Error creating party embed: {e}", e, "TargetPartyView.create_party_embed")
            else:
                logging.error(f"Error creating party embed: {e}")
            return discord.Embed(
                title="❌ Error",
                description="Failed to create party embed",
                color=discord.Color.red()
            )
    
    @discord.ui.button(label="⬅️ Back", style=discord.ButtonStyle.secondary, row=0)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Navigate to previous party."""
        try:
            if self.current_page > 0:
                self.current_page -= 1
                embed = self.create_party_embed(self.suitable_parties[self.current_page], self.current_page)
                self.update_buttons()
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                await interaction.response.send_message("You're already at the first page!")
        except Exception as e:
            if self.cog and hasattr(self.cog, '_log_error'):
                self.cog._log_error(f"Error in back_button: {e}", e, "TargetPartyView.back_button")
            else:
                logging.error(f"Error in back_button: {e}")
            await interaction.response.send_message("An error occurred while navigating. Please try again.")

    @discord.ui.button(label="📋 Main Menu", style=discord.ButtonStyle.primary, row=0)
    async def main_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show main menu with all parties."""
        try:
            embed = self.create_target_info_embed(self.target_nation)
            embed.title = f"🎯 Target Analysis: {self.target_nation.get('nation_name', 'Unknown')}"
            embed.description = f"**Found {len(self.suitable_parties)} suitable attack parties**\n\nUse the buttons below to explore attack options."
            
            # Add summary of parties
            try:
                if self.suitable_parties:
                    summary_text = ""
                    for i, party_data in enumerate(self.suitable_parties[:5]):  # Show first 5
                        try:
                            party = party_data.get('party', {})
                            analysis = party_data.get('analysis', {})
                            percentage = self.create_strategic_percentage(analysis)
                            summary_text += f"**Party {i+1}:** {len(party.get('members', []))} members, {percentage} recommendation\n"
                        except Exception as e:
                            if self.cog and hasattr(self.cog, 'logger'):
                                self.cog.logger.warning(f"Error processing party {i} for summary: {e}")
                            else:
                                logging.warning(f"Error processing party {i} for summary: {e}")
                            continue
                    
                    if len(self.suitable_parties) > 5:
                        summary_text += f"\n*... and {len(self.suitable_parties) - 5} more parties*"
                    
                    if summary_text:
                        embed.add_field(name="📋 Attack Party Summary", value=summary_text.strip(), inline=False)
            except Exception as e:
                if self.cog and hasattr(self.cog, 'logger'):
                    self.cog.logger.warning(f"Error creating party summary: {e}")
                else:
                    logging.warning(f"Error creating party summary: {e}")
            
            self.update_buttons()
            await interaction.response.edit_message(embed=embed, view=self)
        except Exception as e:
            if self.cog and hasattr(self.cog, '_log_error'):
                self.cog._log_error(f"Error in main_button: {e}", e, "TargetPartyView.main_button")
            else:
                logging.error(f"Error in main_button: {e}")
            await interaction.response.send_message("An error occurred while loading the main menu. Please try again.")

    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.secondary, row=0)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Navigate to next party."""
        try:
            if self.current_page < len(self.suitable_parties) - 1:
                self.current_page += 1
                embed = self.create_party_embed(self.suitable_parties[self.current_page], self.current_page)
                self.update_buttons()
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                await interaction.response.send_message("You're already at the last page!")
        except Exception as e:
            if self.cog and hasattr(self.cog, '_log_error'):
                self.cog._log_error(f"Error in next_button: {e}", e, "TargetPartyView.next_button")
            else:
                logging.error(f"Error in next_button: {e}")
            await interaction.response.send_message("An error occurred while navigating. Please try again.")

    async def on_timeout(self) -> None:
        """Disable buttons when view times out."""
        try:
            for item in self.children:
                if hasattr(item, 'disabled'):
                    item.disabled = True
        except Exception as e:
            if self.cog and hasattr(self.cog, '_log_error'):
                self.cog._log_error(f"Error in on_timeout: {e}", e, "TargetPartyView.on_timeout")
            else:
                logging.error(f"Error in on_timeout: {e}")

async def setup(bot):
    """
    Setup function to add the cog to the bot.
    
    Args:
        bot: Discord bot instance
    """
    try:
        await bot.add_cog(DestroyCog(bot))
        logging.info("DestroyCog loaded successfully")
    except Exception as e:
        logging.error(f"Error loading DestroyCog: {e}")
        logging.error(traceback.format_exc())
