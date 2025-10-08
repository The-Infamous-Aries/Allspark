import discord
from discord.ext import commands
import requests
import json
import os
import re
from pathlib import Path
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
    try:
        from query import create_query_instance
    except ImportError:
        # Handle case when running as standalone script
        from Systems.PnW.MA.query import create_query_instance
from config import PANDW_API_KEY, CYBERTRON_ALLIANCE_ID
from Systems.user_data_manager import UserDataManager
import time

try:
    from .sorter import BlitzPartySorter
except ImportError:
    try:
        from sorter import BlitzPartySorter
    except ImportError:
        from Systems.PnW.MA.sorter import BlitzPartySorter

try:
    from .calc import AllianceCalculator
except ImportError:
    try:
        from calc import AllianceCalculator
    except ImportError:
        from Systems.PnW.MA.calc import AllianceCalculator

class DestroyCog(commands.Cog):
    """Cog for managing war destruction commands."""
    
    def __init__(self, bot: commands.Bot):
        try:
            self.bot = bot
            self.api_key = PANDW_API_KEY
            self.user_data_manager = UserDataManager()
            self.cybertron_alliance_id = CYBERTRON_ALLIANCE_ID
            self.logger = logging.getLogger(__name__)
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)
            self.error_count = 0
            self.max_errors = 100 
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
            try:
                self.query_instance = create_query_instance()
                self.logger.info("Centralized query instance initialized successfully")
                if hasattr(self.query_instance, 'cache_ttl_seconds'):
                    self.query_instance.cache_ttl_seconds = 3600
            except Exception as e:
                self.logger.error(f"Failed to initialize query instance: {e}")
                self.query_instance = None
            try:
                self.party_sorter = BlitzPartySorter(logger=self.logger)
                self.logger.info("BlitzPartySorter initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize BlitzPartySorter: {e}")
                self.party_sorter = None
            try:
                self.calculator = AllianceCalculator()
                self.logger.info("AllianceCalculator initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize AllianceCalculator: {e}")
                self.calculator = None
        except Exception as e:
            print(f"Error initializing DestroyCog: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            self.bot = bot
            self.api_key = PANDW_API_KEY
            self.user_data_manager = UserDataManager()
            self.cybertron_alliance_id = CYBERTRON_ALLIANCE_ID
            self.error_count = 0
            self.max_errors = 100
            self.pnwkit_available = False
            self.query_instance = None
            self.party_sorter = None
            self.calculator = None 
                
    async def get_alliance_nations(self, alliance_id: str, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Get alliance nations data from individual alliance files or API.
        
        Args:
            alliance_id: The alliance ID to fetch data for
            force_refresh: Whether to force refresh from API
            
        Returns:
            List of nation dictionaries or empty list if not found
        """
        try:
            alliance_key = f"alliance_{alliance_id}"
            
            # Try to get from individual alliance file first
            nations_data = await self.user_data_manager.get_json_data(alliance_key, [])
            
            if nations_data and not force_refresh:
                self.logger.info(f"get_alliance_nations: Retrieved {len(nations_data)} nations from file for alliance {alliance_id}")
                return nations_data
            
            # If we get here, file is missing or we need to refresh
            self.logger.info(f"get_alliance_nations: File missing or refresh needed for alliance {alliance_id}, fetching from API")
            
            # Try to use query instance if available
            if self.query_instance:
                nations = await self.query_instance.get_alliance_nations(alliance_id, bot=self.bot, force_refresh=force_refresh)
                
                # Store in individual alliance file for future use
                if nations:
                    try:
                        await self.user_data_manager.save_json_data(alliance_key, nations)
                        self.logger.info(f"get_alliance_nations: Stored {len(nations)} nations in file for alliance {alliance_id}")
                    except Exception as file_error:
                        self.logger.error(f"Error storing alliance data in file: {file_error}")
                
                return nations or []
            
            # Fallback to empty list if all methods fail
            self.logger.warning(f"get_alliance_nations: Failed to get nations for alliance {alliance_id}")
            return []
            
        except Exception as e:
            self._log_error(f"Error in get_alliance_nations for alliance {alliance_id}", e, "get_alliance_nations")
            return []
    
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
                theoretical_max_aircraft = num_cities * 5 * 15   # 5 Hangars per city, 15 aircraft per Hangar
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
            
            # Determine if "heavy" in each unit type (75% threshold)
            is_heavy_ground = ground_percentage > 75
            is_heavy_air = aircraft_percentage > 75
            is_heavy_naval = ship_percentage > 75
            
            # Check for high purchase capacity (minimum thresholds for advantages)
            high_ground_purchase = (purchase_limits.get('soldiers_max', 0) >= 100000 or purchase_limits.get('tanks_max', 0) >= 4000)
            high_air_purchase = purchase_limits.get('aircraft_max', 0) >= 250
            high_naval_purchase = purchase_limits.get('ships_max', 0) >= 40
            
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



    # Helper methods for calc.py functions
    def get_active_nations(self, nations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get active nations from a list of nations."""
        try:
            # Use the calculator instead of party_sorter
            return self.calculator.get_active_nations(nations)
        except Exception as e:
            self._log_error(f"Error getting active nations: {str(e)}", e, "get_active_nations")
            return []
    
    def _calculate_strategic_value(self, nation: Dict[str, Any]) -> float:
        """Calculate strategic value for a nation."""
        try:
            # Use the calculator instead of party_sorter
            return self.calculator._calculate_strategic_value(nation)
        except Exception as e:
            self._log_error(f"Error calculating strategic value: {str(e)}", e, "_calculate_strategic_value")
            return 0.0
    
    def calculate_infrastructure_stats(self, nation: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate infrastructure stats for a nation."""
        try:
            # Use the calculator instead of party_sorter
            return self.calculator.calculate_infrastructure_stats(nation)
        except Exception as e:
            self._log_error(f"Error calculating infrastructure stats: {str(e)}", e, "calculate_infrastructure_stats")
            return {}
    
    def calculate_military_advantage(self, nation: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate military advantage for a nation."""
        try:
            # Use the calculator instead of party_sorter
            return self.calculator.calculate_military_advantage(nation)
        except Exception as e:
            self._log_error(f"Error calculating military advantage: {str(e)}", e, "calculate_military_advantage")
            return {}
    
    def validate_attack_range(self, attacker_score: float, defender_score: float) -> bool:
        """Validate if attacker can attack defender based on score range."""
        try:
            # War range validation: attacker can hit targets from 75% to 250% of their score
            if attacker_score <= 0:
                return False
            
            min_range = attacker_score * 0.75  # 75% of attacker's score
            max_range = attacker_score * 2.5   # 250% of attacker's score
            
            return min_range <= defender_score <= max_range
            
        except Exception as e:
            self._log_error(f"Error validating attack range: {str(e)}", e, "validate_attack_range")
            return False
    
    def calculate_group_war_range(self, group_members: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate war range for a group."""
        try:
            # Use the calculator instead of party_sorter
            return self.calculator.calculate_group_war_range(group_members)
        except Exception as e:
            self._log_error(f"Error calculating group war range: {str(e)}", e, "calculate_group_war_range")
            return {}
    
    def calculate_nation_statistics(self, nation: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate nation statistics."""
        try:
            # Use the calculator instead of party_sorter
            return self.calculator.calculate_nation_statistics(nation)
        except Exception as e:
            self._log_error(f"Error calculating nation statistics: {str(e)}", e, "calculate_nation_statistics")
            return {}
    
    def calculate_alliance_statistics(self, nations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate alliance statistics."""
        try:
            # Use the calculator instead of party_sorter
            return self.calculator.calculate_alliance_statistics(nations)
        except Exception as e:
            self._log_error(f"Error calculating alliance statistics: {str(e)}", e, "calculate_alliance_statistics")
            return {}
    
    def calculate_full_mill_data(self, nation: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate full mill data for a nation."""
        try:
            # Use the calculator instead of party_sorter
            return self.calculator.calculate_full_mill_data(nation)
        except Exception as e:
            self._log_error(f"Error calculating full mill data: {str(e)}", e, "calculate_full_mill_data")
            return {}
    
    def calculate_improvements_data(self, nation: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate improvements data for a nation."""
        try:
            # Use the calculator instead of party_sorter
            return self.calculator.calculate_improvements_data(nation)
        except Exception as e:
            self._log_error(f"Error calculating improvements data: {str(e)}", e, "calculate_improvements_data")
            return {}
    
    def get_nation_specialty(self, nation: Dict[str, Any]) -> str:
        """Get nation specialty."""
        try:
            # Use the calculator instead of party_sorter
            return self.calculator.get_nation_specialty(nation)
        except Exception as e:
            self._log_error(f"Error getting nation specialty: {str(e)}", e, "get_nation_specialty")
            return "Unknown"
    
    def calculate_military_purchase_limits(self, nation: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate military purchase limits for a nation."""
        try:
            # Use the standalone function from calc.py
            from .calc import calculate_military_purchase_limits
            return calculate_military_purchase_limits(nation)
        except Exception as e:
            self._log_error(f"Error calculating military purchase limits: {str(e)}", e, "calculate_military_purchase_limits")
            return {'soldiers': 0, 'tanks': 0, 'aircraft': 0, 'ships': 0}

    async def find_optimal_attackers(self, target_nation: Dict[str, Any] = None, max_groups: int = 10) -> Dict[str, Any]:
        """
        Find optimal groups of three alliance members for war targeting using efficient sorting approach.
        
        Args:
            target_nation: Target nation data to check war range against
            max_groups: Maximum number of optimal groups to return
            
        Returns:
            Dictionary containing a list of optimal attacker groups and their analyses
        """
        try:
            # Load alliance data from individual alliance files
            bloc_dir = Path(__file__).parent.parent.parent / 'Data' / 'Bloc'
            eligible_members = []
            
            # Get target score for war range validation (define early to avoid scope issues)
            target_score = target_nation.get('score', 0) if target_nation else 0
            
            if not bloc_dir.exists():
                return {'error': 'Bloc directory not found'}
            
            # Load data from all alliance files
            for alliance_file in bloc_dir.glob('alliance_*.json'):
                try:
                    alliance_data = await self.user_data_manager.get_json_data(alliance_file.stem, {})
                    if isinstance(alliance_data, dict) and 'nations' in alliance_data:
                        for nation in alliance_data['nations']:
                            if (isinstance(nation, dict) and 
                                nation.get('alliance_position') != 'APPLICANT' and 
                                not nation.get('vacation_mode', False)):
                                # If target provided, check war range
                                if target_nation:
                                    member_score = nation.get('score', 0)
                                    if self.validate_attack_range(member_score, target_score):
                                        eligible_members.append(nation)
                                else:
                                    eligible_members.append(nation)
                except Exception as e:
                    self.logger.warning(f"Error loading alliance data from {alliance_file.name}: {e}")
                    continue
            
            if len(eligible_members) < 3:
                return {'error': f'Not enough eligible alliance members found (need 3, found {len(eligible_members)})'}
            
            # Filter members with military data and calculate infrastructure averages
            members_with_military = []
            for member in eligible_members:
                if (member.get('soldiers') is not None and 
                    member.get('tanks') is not None and 
                    member.get('aircraft') is not None and 
                    member.get('ships') is not None and
                    member.get('score') is not None):
                    
                    # Calculate infrastructure average
                    cities = member.get('cities', [])
                    if cities:
                        total_infra = sum(city.get('infrastructure', 0) for city in cities)
                        member['infra_average'] = total_infra / len(cities)
                    else:
                        member['infra_average'] = member.get('infrastructure', 0)
                    
                    members_with_military.append(member)
            
            if len(members_with_military) < 3:
                return {'error': f'Not enough members with complete military data (need 3, found {len(members_with_military)})'}
            
            # Sort by infrastructure (lowest first) - prioritize lower infra nations
            members_with_military.sort(key=lambda x: x.get('infra_average', 0))
            
            # Create optimal groups using efficient approach
            optimal_groups = []
            used_nations = set()
            
            # Process nations in order of lowest infrastructure
            for i, nation in enumerate(members_with_military):
                nation_id = nation.get('nation_id') or nation.get('id')
                if nation_id in used_nations:
                    continue
                
                # Find 2 compatible nations for a party
                party = [nation]
                used_nations.add(nation_id)
                
                # Look for compatible nations (within war range and good unit coverage)
                for potential_nation in members_with_military[i+1:]:
                    potential_id = potential_nation.get('nation_id') or potential_nation.get('id')
                    if potential_id in used_nations or len(party) >= 3:
                        continue
                    
                    # Check if this nation is compatible with all current party members
                    is_compatible = True
                    for party_member in party:
                        if not self._check_war_range_compatibility(party_member, potential_nation):
                            is_compatible = False
                            break
                    
                    if is_compatible and len(party) < 3:
                        party.append(potential_nation)
                        used_nations.add(potential_id)
                
                # Only keep parties of exactly 3
                if len(party) == 3:
                    # Analyze the party
                    group_analysis = self._analyze_party(party, target_nation)
                    if group_analysis['is_valid']:
                        optimal_groups.append({
                            'attackers': party,
                            'score': group_analysis['score'],
                            'analysis': group_analysis
                        })
                
                # Stop if we have enough groups
                if len(optimal_groups) >= max_groups:
                    break
            
            if not optimal_groups:
                return {'error': 'No valid groups found with required unit coverage'}
            
            # Sort groups by score (highest first)
            optimal_groups.sort(key=lambda x: x['score'], reverse=True)
            
            return {
                'optimal_groups': optimal_groups,
                'total_found': len(optimal_groups)
            }
            
        except Exception as e:
            self._log_error(f"Error finding optimal attackers: {str(e)}", e, "find_optimal_attackers")
            return {'error': f'Error finding optimal attackers: {str(e)}'}
    
    def _check_war_range_compatibility(self, nation1: Dict[str, Any], nation2: Dict[str, Any]) -> bool:
        """Check if two nations can war each other based on score range (-25% to 150%)"""
        try:
            score1 = nation1.get('score', 0)
            score2 = nation2.get('score', 0)
            
            if score1 <= 0 or score2 <= 0:
                return False
            
            # War range: -25% to +150% of their score
            min_range = score1 * 0.75  # -25%
            max_range = score1 * 2.5   # +150%
            
            return min_range <= score2 <= max_range
            
        except Exception as e:
            self._log_error("Error checking war range compatibility", e)
            return False
    
    def _analyze_party(self, party: List[Dict[str, Any]], target_nation: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a party for unit coverage and calculate a score"""
        try:
            if len(party) != 3:
                return {'is_valid': False, 'error': 'Party must have exactly 3 members'}
            
            # Check unit coverage
            has_ground = False
            has_air = False
            has_navy = False
            has_missile_or_nuke = False
            
            # Target's military for comparison
            target_soldiers = target_nation.get('soldiers', 0) if target_nation else 0
            target_tanks = target_nation.get('tanks', 0) if target_nation else 0
            target_aircraft = target_nation.get('aircraft', 0) if target_nation else 0
            target_ships = target_nation.get('ships', 0) if target_nation else 0
            
            total_infra = 0
            total_military_score = 0
            unit_coverage_count = 0
            
            for member in party:
                # Get current military units
                soldiers = member.get('soldiers', 0)
                tanks = member.get('tanks', 0)
                aircraft = member.get('aircraft', 0)
                ships = member.get('ships', 0)
                
                # Check if this member has more units than target (good indicator)
                member_has_advantage = (
                    (soldiers + tanks * 10) > (target_soldiers + target_tanks * 10) or
                    aircraft > target_aircraft or
                    ships > target_ships
                )
                
                # Check unit types (including daily purchase capacity)
                try:
                    purchase_limits = self.calculate_military_purchase_limits(member)
                    soldiers += purchase_limits.get('soldiers_max', 0)
                    tanks += purchase_limits.get('tanks_max', 0)
                    aircraft += purchase_limits.get('aircraft_max', 0)
                    ships += purchase_limits.get('ships_max', 0)
                except:
                    pass  # If purchase limits fail, use current values
                
                if soldiers > 0 or tanks > 0:
                    has_ground = True
                if aircraft > 0:
                    has_air = True
                if ships > 0:
                    has_navy = True
                
                # Check missile/nuke capability
                if (member.get('missiles', 0) > 0 or 
                    member.get('nukes', 0) > 0 or
                    self.has_project(member, 'missile_pad') or
                    self.has_project(member, 'nuclear_facility')):
                    has_missile_or_nuke = True
                
                # Calculate infrastructure
                total_infra += member.get('infra_average', member.get('infrastructure', 0))
                
                # Calculate military score
                total_military_score += (
                    soldiers * 0.1 +
                    tanks * 5 +
                    aircraft * 50 +
                    ships * 100
                )
            
            # Count unit coverage types
            unit_coverage_count = sum([has_ground, has_air, has_navy])
            
            # Must have at least 2 unit types for basic coverage
            if unit_coverage_count < 2:
                return {'is_valid': False, 'error': 'Insufficient unit coverage'}
            
            # Calculate scores
            avg_infra = total_infra / 3
            
            # Infrastructure score (lower is better for attackers)
            infra_score = 1000 / (avg_infra + 1)
            
            # Military strength score
            military_score = total_military_score / 1000
            
            # Strategic bonus for missile/nuke capability
            strategic_bonus = 200 if has_missile_or_nuke else 0
            
            # Unit coverage bonus (more coverage = better)
            unit_coverage_bonus = unit_coverage_count * 50
            
            # Final score
            final_score = infra_score + military_score + unit_coverage_bonus + strategic_bonus
            
            return {
                'is_valid': True,
                'score': final_score,
                'total_infrastructure': total_infra,
                'avg_infrastructure': avg_infra,
                'total_military_score': total_military_score,
                'unit_coverage': {
                    'ground': has_ground,
                    'air': has_air,
                    'navy': has_navy,
                    'unit_types_count': unit_coverage_count
                },
                'strategic_capabilities': {
                    'missile_or_nuke': has_missile_or_nuke
                }
            }
            
        except Exception as e:
            self._log_error("Error analyzing party", e)
            return {'is_valid': False, 'error': str(e)}

    def create_optimal_attackers_view(self, ctx: commands.Context, target_nation: Dict[str, Any], optimal_attackers: Dict[str, Any]) -> 'OptimalAttackersView':
        """Create an OptimalAttackersView instance for displaying optimal attacker groups."""
        try:
            return OptimalAttackersView(ctx, target_nation, optimal_attackers.get('optimal_groups', []), self)
        except Exception as e:
            self._log_error(f"Error creating optimal attackers view: {str(e)}", e, "create_optimal_attackers_view")
            return None

    @commands.command(name='destroy', aliases=['target', 'findattackers'])
    async def destroy(self, ctx: commands.Context, *, target: str = None):
        """
        Find optimal attackers for a target nation with comprehensive analysis.
        
        Usage:
        !destroy <nation_name>
        !destroy <leader_name>
        !destroy <nation_id>
        !destroy <nation_link>
        
        Examples:
        !destroy Testlandia
        !destroy https://politicsandwar.com/nation/id=12345
        !destroy 12345
        """
        try:
            # Validate input
            if not target or not target.strip():
                embed = discord.Embed(
                    title="❌ Missing Target",
                    description="Please provide a target nation. Usage: `!destroy <target>`",
                    color=discord.Color.red()
                )
                embed.add_field(
                    name="Examples:",
                    value=(
                        "`!destroy Testlandia`\n"
                        "`!destroy https://politicsandwar.com/nation/id=12345`\n"
                        "`!destroy 12345`\n"
                        "`!destroy <leader_name>`"
                    ),
                    inline=False
                )
                await ctx.send(embed=embed)
                return

            # Parse target input
            target_data, input_type = await self.parse_target_input(target.strip())
            
            if input_type == 'nation_name' and target_data is None:
                target_data = target.strip()
            elif input_type == 'leader_name' and target_data is None:
                target_data = target.strip()
            
            # Send initial loading message
            loading_embed = discord.Embed(
                title="🔍 Searching for Target...",
                description=f"Looking up: **{target.strip()}**",
                color=discord.Color.blue()
            )
            loading_message = await ctx.send(embed=loading_embed)
            
            # Fetch target nation data
            target_nation = await self.fetch_target_nation(target_data, input_type)
            
            if not target_nation:
                error_embed = discord.Embed(
                    title="❌ Target Not Found",
                    description=f"Could not find nation: **{target.strip()}**",
                    color=discord.Color.red()
                )
                error_embed.add_field(
                    name="Try:",
                    value=(
                        "- Check the spelling\n"
                        "- Use the nation ID instead\n"
                        "- Try the leader name\n"
                        "- Use a nation link"
                    ),
                    inline=False
                )
                await loading_message.edit(embed=error_embed)
                return
            
            # Update loading message
            loading_embed.title = "⚔️ Finding Optimal Attackers..."
            loading_embed.description = (
                f"Target: **{target_nation.get('nation_name', 'Unknown')}**\n"
                "Searching for optimal attacker groups..."
            )
            await loading_message.edit(embed=loading_embed)
            
            # Find optimal attackers
            optimal_attackers = await self.find_optimal_attackers(target_nation, max_groups=10)
            
            if 'error' in optimal_attackers:
                error_embed = discord.Embed(
                    title="❌ Error Finding Attackers",
                    description=optimal_attackers['error'],
                    color=discord.Color.red()
                )
                await loading_message.edit(embed=error_embed)
                return
            
            if not optimal_attackers.get('optimal_groups'):
                error_embed = discord.Embed(
                    title="❌ No Attackers Found",
                    description="Could not find any valid attacker groups for this target.",
                    color=discord.Color.red()
                )
                error_embed.add_field(
                    name="Possible Reasons:",
                    value=(
                        "- Target is too strong for available alliance members\n"
                        "- Not enough active alliance members\n"
                        "- Alliance members don't meet unit coverage requirements"
                    ),
                    inline=False
                )
                await loading_message.edit(embed=error_embed)
                return
            
            # Create the interactive view
            view = self.create_optimal_attackers_view(ctx, target_nation, optimal_attackers)
            
            if not view:
                error_embed = discord.Embed(
                    title="❌ Error Creating View",
                    description="Failed to create the interactive attacker display.",
                    color=discord.Color.red()
                )
                await loading_message.edit(embed=error_embed)
                return
            
            # Get the initial embed (target information)
            initial_embed = view.create_target_embed()
            
            # Update the message with the interactive view
            await loading_message.edit(embed=initial_embed, view=view)
            
            self.logger.info(
                f"Destroy command completed successfully for target: {target_nation.get('nation_name', 'Unknown')} "
                f"by user {ctx.author.name}#{ctx.author.discriminator}"
            )
            
        except Exception as e:
            self._log_error(f"Error in destroy command: {str(e)}", e, "destroy")
            error_embed = discord.Embed(
                title="❌ Command Error",
                description="An unexpected error occurred while processing the destroy command.",
                color=discord.Color.red()
            )
            error_embed.add_field(name="Error", value=str(e), inline=False)
            
            try:
                if 'loading_message' in locals():
                    await loading_message.edit(embed=error_embed)
                else:
                    await ctx.send(embed=error_embed)
            except:
                await ctx.send(embed=error_embed)

class OptimalAttackersView(discord.ui.View):
    """Interactive view for displaying optimal attacker groups with pagination."""
    
    def __init__(self, ctx: commands.Context, target_nation: Dict[str, Any], optimal_groups: List[Dict[str, Any]], cog: DestroyCog):
        super().__init__(timeout=300)  # 5 minute timeout
        try:
            self.ctx = ctx
            self.target_nation = target_nation or {}
            self.cog = cog
            self.current_page = 0
            self.back_button = None
            self.main_button = None
            self.next_button = None
            
            # Flatten all attackers and split into groups of 3
            all_attackers = []
            for group in (optimal_groups or []):
                if group and group.get('attackers'):
                    all_attackers.extend(group['attackers'])
            
            # Split attackers into groups of 3
            self.attacker_pages = []
            for i in range(0, len(all_attackers), 3):
                group_attackers = all_attackers[i:i+3]
                if group_attackers:
                    # Create a simple group structure for display
                    page_data = {
                        'attackers': group_attackers,
                        'page_num': (i // 3) + 1
                    }
                    self.attacker_pages.append(page_data)
            
            self._create_buttons()
            self.update_buttons()
        except Exception as e:
            if cog and hasattr(cog, '_log_error'):
                cog._log_error(f"Error initializing OptimalAttackersView: {e}", e, "OptimalAttackersView.__init__")
            else:
                logging.error(f"Error initializing OptimalAttackersView: {e}")
            self.ctx = ctx
            self.cog = cog
            self.target_nation = {}
            self.attacker_pages = []
            self.current_page = 0
            self.back_button = None
            self.main_button = None
            self.next_button = None
    
    def _create_buttons(self):
        """Create and store button references."""
        try:
            self.clear_items()
            back_btn = discord.ui.Button(label="⬅️ Back", style=discord.ButtonStyle.secondary, row=0)
            back_btn.callback = self._back_callback
            self.back_button = back_btn           
            main_btn = discord.ui.Button(label="📋 Target Info", style=discord.ButtonStyle.primary, row=0)
            main_btn.callback = self._main_callback
            self.main_button = main_btn          
            next_btn = discord.ui.Button(label="➡️ Next", style=discord.ButtonStyle.secondary, row=0)
            next_btn.callback = self._next_callback
            self.next_button = next_btn
            self.add_item(back_btn)
            self.add_item(main_btn)
            self.add_item(next_btn)            
        except Exception as e:
            if self.cog and hasattr(self.cog, '_log_error'):
                self.cog._log_error(f"Error creating buttons: {e}", e, "OptimalAttackersView._create_buttons")
            else:
                logging.error(f"Error creating buttons: {e}")
    
    async def _back_callback(self, interaction: discord.Interaction):
        """Navigate to previous page."""
        try:
            if self.current_page > 0:
                self.current_page -= 1
                if self.current_page == 0:
                    embed = self.create_target_embed()
                else:
                    page_index = self.current_page - 1
                    embed = self.create_attacker_page_embed(self.attacker_pages[page_index], page_index)  
                self.update_buttons()
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                await interaction.response.send_message("You're already at the first page!")
        except Exception as e:
            if self.cog and hasattr(self.cog, '_log_error'):
                self.cog._log_error(f"Error in _back_callback: {e}", e, "OptimalAttackersView._back_callback")
            else:
                logging.error(f"Error in _back_callback: {e}")
            await interaction.response.send_message("An error occurred while navigating. Please try again.")
    
    async def _main_callback(self, interaction: discord.Interaction):
        """Show target information page."""
        try:
            self.current_page = 0
            embed = self.create_target_embed()
            self.update_buttons()
            await interaction.response.edit_message(embed=embed, view=self)
        except Exception as e:
            if self.cog and hasattr(self.cog, '_log_error'):
                self.cog._log_error(f"Error in _main_callback: {e}", e, "OptimalAttackersView._main_callback")
            else:
                logging.error(f"Error in _main_callback: {e}")
            await interaction.response.send_message("An error occurred while loading the target info. Please try again.")
    
    async def _next_callback(self, interaction: discord.Interaction):
        """Navigate to next page."""
        try:
            max_pages = len(self.attacker_pages) + 1
            if self.current_page < max_pages - 1:
                self.current_page += 1               
                if self.current_page == 0:
                    embed = self.create_target_embed()
                else:
                    page_index = self.current_page - 1
                    embed = self.create_attacker_page_embed(self.attacker_pages[page_index], page_index)                
                self.update_buttons()
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                await interaction.response.send_message("You're already at the last page!")
        except Exception as e:
            if self.cog and hasattr(self.cog, '_log_error'):
                self.cog._log_error(f"Error in _next_callback: {e}", e, "OptimalAttackersView._next_callback")
            else:
                logging.error(f"Error in _next_callback: {e}")
            await interaction.response.send_message("An error occurred while navigating. Please try again.")
    
    def update_buttons(self):
        """Update button states based on current page."""
        try:
            self.back_button.disabled = self.current_page <= 0
            max_pages = max(1, len(self.attacker_pages) + 1)
            self.next_button.disabled = self.current_page >= max_pages - 1
        except Exception as e:
            if self.cog and hasattr(self.cog, '_log_error'):
                self.cog._log_error(f"Error updating buttons: {e}", e, "OptimalAttackersView.update_buttons")
            else:
                logging.error(f"Error updating buttons: {e}")
            self.back_button.disabled = True
            self.next_button.disabled = True
    
    def create_target_embed(self) -> discord.Embed:
        """Create embed for target nation information."""
        try:
            if not self.target_nation:
                return discord.Embed(
                    title="❌ Error",
                    description="No target nation data available",
                    color=discord.Color.red()
                )
            
            # Safe military extraction
            safe_soldiers = self.target_nation.get('soldiers', 0) or 0
            safe_tanks = self.target_nation.get('tanks', 0) or 0
            safe_aircraft = self.target_nation.get('aircraft', 0) or 0
            safe_ships = self.target_nation.get('ships', 0) or 0
            safe_missiles = self.target_nation.get('missiles', 0) or 0
            safe_nukes = self.target_nation.get('nukes', 0) or 0
            
            # Safe basic info extraction
            nation_name = self.target_nation.get('nation_name', 'Unknown')
            leader_name = self.target_nation.get('leader_name', 'Unknown')
            nation_score = self.target_nation.get('score', 0) or 0
            num_cities = self.target_nation.get('num_cities', 0) or 0
            
            # Calculate infrastructure and land from cities data
            cities = self.target_nation.get('cities', [])
            total_infra = 0
            total_land = 0
            if cities:
                total_infra = sum((city.get('infrastructure', 0) or 0) for city in cities if isinstance(city, dict))
                total_land = sum((city.get('land', 0) or 0) for city in cities if isinstance(city, dict))
            infrastructure = total_infra
            
            # Calculate averages per city
            avg_infra_per_city = total_infra / num_cities if num_cities > 0 else 0
            avg_land_per_city = total_land / num_cities if num_cities > 0 else 0
            
            # Get purchase limits
            try:
                purchase_limits = self.cog.calculate_target_purchase_limits(self.target_nation)
            except Exception:
                purchase_limits = {'soldiers': 0, 'tanks': 0, 'aircraft': 0, 'ships': 0}
            
            embed = discord.Embed(
                title=f"🎯 Target: {nation_name}",
                description=f"**Leader:** {leader_name}",
                color=discord.Color.red()
            )
            
            # Purchase Limits section (replacing Current Resources)
            purchase_limits_info = (
                f"**Soldiers:** {purchase_limits.get('soldiers', 0):,}\n"
                f"**Tanks:** {purchase_limits.get('tanks', 0):,}\n"
                f"**Aircraft:** {purchase_limits.get('aircraft', 0):,}\n"
                f"**Ships:** {purchase_limits.get('ships', 0):,}"
            )
            embed.add_field(name="Purchase Limits", value=purchase_limits_info, inline=False)
            
            # Calculate MMR using calculator
            try:
                building_ratios = self.cog.calculator.calculate_building_ratios(self.target_nation)
                mmr_string = building_ratios.get('mmr_string', '0/0/0/0')
            except Exception:
                mmr_string = '0/0/0/0'
            
            # Get nation specialty
            try:
                specialty = self.cog.calculator.get_nation_specialty(self.target_nation)
            except Exception:
                specialty = 'Unknown'
            
            # Basic info field from blitz.py lines 767-784 format
            field_value = (
                f"**Score:** {nation_score:,}\n"
                f"**MMR:** {mmr_string}\n"
                f"**Specialty:** {specialty}\n"
                f"**Cities:** {num_cities:,}\n"
                f"**Avg Infra/City:** {avg_infra_per_city:,.0f}\n"
                f"**Avg Land/City:** {avg_land_per_city:,.0f}\n"
                f"**Total Infrastructure:** {infrastructure:,.0f}\n"
                f"**Strategic:** {'Missile' if safe_missiles > 0 else ''}{' Nuke' if safe_nukes > 0 else ''}\n"
                f"**Units (Current):**\n"
                f"👥 {safe_soldiers:,}\n"
                f"🚗 {safe_tanks:,}\n"
                f"✈️ {safe_aircraft:,}\n"
                f"🚢 {safe_ships:,}"
            )
            embed.add_field(name="1. Target Info", value=field_value, inline=True)
            
            embed.set_footer(text=f"Page 1/{len(self.attacker_pages) + 1} - Target Information")
            return embed
            
        except Exception as e:
            if self.cog and hasattr(self.cog, '_log_error'):
                self.cog._log_error(f"Error creating target embed: {e}", e, "OptimalAttackersView.create_target_embed")
            else:
                logging.error(f"Error creating target embed: {e}")
            return discord.Embed(
                title="❌ Error",
                description="Failed to create target embed",
                color=discord.Color.red()
            )
    
    def create_attacker_page_embed(self, page_data: Dict[str, Any], page_index: int) -> discord.Embed:
        """Create embed for an attacker page showing up to 3 attackers."""
        try:
            if not page_data or not page_data.get('attackers'):
                return discord.Embed(
                    title="❌ Error",
                    description="No attacker data available",
                    color=discord.Color.red()
                )
            
            attackers = page_data['attackers']
            page_num = page_data['page_num']
            
            embed = discord.Embed(
                title=f"⚔️ Optimal Attackers (Page {page_num})",
                description=f"Showing {len(attackers)} attacker(s)",
                color=discord.Color.green()
            )
            
            # Individual attacker details - each nation gets its own field like blitz.py format
            for i, attacker in enumerate(attackers):
                if attacker and isinstance(attacker, dict):
                    nation_name = attacker.get('nation_name', 'Unknown')
                    leader_name = attacker.get('leader_name', 'Unknown')
                    score = attacker.get('score', 0) or 0
                    infrastructure = attacker.get('infrastructure', 0) or 0
                    
                    # Military units
                    soldiers = attacker.get('soldiers', 0) or 0
                    tanks = attacker.get('tanks', 0) or 0
                    aircraft = attacker.get('aircraft', 0) or 0
                    ships = attacker.get('ships', 0) or 0
                    
                    # Strategic weapons
                    missiles = attacker.get('missiles', 0) or 0
                    nukes = attacker.get('nukes', 0) or 0
                    
                    # Calculate MMR and specialty for attacker
                    try:
                        building_ratios = self.cog.calculator.calculate_building_ratios(attacker)
                        mmr_string = building_ratios.get('mmr_string', '0/0/0/0')
                    except Exception:
                        mmr_string = '0/0/0/0'
                    
                    try:
                        specialty = self.cog.calculator.get_nation_specialty(attacker)
                    except Exception:
                        specialty = 'Unknown'
                    
                    # Calculate warchest status
                    gasoline = attacker.get('gasoline', 0) or 0
                    munitions = attacker.get('munitions', 0) or 0
                    aluminum = attacker.get('aluminum', 0) or 0
                    steel = attacker.get('steel', 0) or 0
                    
                    # Determine warchest level (6 levels with moon emojis + stacked)
                    warchest_resources = [gasoline, munitions, aluminum, steel]
                    min_resource = min(warchest_resources) if warchest_resources else 0

                    if min_resource >= 10000:
                        warchest_emoji = "🤑"  
                        warchest_status = "Stacked"                    
                    elif min_resource >= 5000:
                        warchest_emoji = "🌝" 
                        warchest_status = "Full"
                    elif min_resource >= 3750:
                        warchest_emoji = "🌖" 
                        warchest_status = "3/4"
                    elif min_resource >= 2500:
                        warchest_emoji = "🌗"  
                        warchest_status = "1/2"
                    elif min_resource >= 1250:
                        warchest_emoji = "🌘" 
                        warchest_status = "1/4"
                    else:
                        warchest_emoji = "🌚" 
                        warchest_status = "No"
                    
                    field_value = (
                        f"**Leader:** {leader_name}\n"
                        f"**Score:** {score:,}\n"
                        f"**MMR:** {mmr_string}\n"
                        f"**Specialty:** {specialty}\n"
                        f"**Infrastructure:** {infrastructure:,.0f}\n"
                        f"**Has Warchest:** {warchest_emoji} ({warchest_status})\n"
                        f"**Strategic:** {'Missile' if missiles > 0 else ''}{' Nuke' if nukes > 0 else ''}\n"
                        f"**Units (Current):**\n"
                        f"👥 {soldiers:,}\n"
                        f"🚗 {tanks:,}\n"
                        f"✈️ {aircraft:,}\n"
                        f"🚢 {ships:,}"
                    )
                    
                    embed.add_field(name=f"{i+1}. {nation_name}", value=field_value, inline=True)
            
            embed.set_footer(text=f"Page {page_num + 1}/{len(self.attacker_pages) + 1} - Optimal Attackers")
            return embed
            
        except Exception as e:
            if self.cog and hasattr(self.cog, '_log_error'):
                self.cog._log_error(f"Error creating attacker page embed: {e}", e, "OptimalAttackersView.create_attacker_page_embed")
            else:
                logging.error(f"Error creating attacker page embed: {e}")
            return discord.Embed(
                title="❌ Error",
                description="Failed to create attacker page embed",
                color=discord.Color.red()
            )
    

    
    async def on_timeout(self) -> None:
        """Disable buttons when view times out."""
        try:
            for item in self.children:
                if hasattr(item, 'disabled'):
                    item.disabled = True
        except Exception as e:
            if self.cog and hasattr(self.cog, '_log_error'):
                self.cog._log_error(f"Error in on_timeout: {e}", e, "OptimalAttackersView.on_timeout")
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
