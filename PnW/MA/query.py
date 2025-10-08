import requests
import logging
from typing import List, Dict, Optional, Any, Union
import os
import sys
import time
import asyncio
from datetime import datetime, timedelta

# Add parent directory to path for config import
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
try:
    from config import PANDW_API_KEY
except ImportError:
    # Fallback for when running from different directory
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from config import PANDW_API_KEY

# Import UserDataManager for caching
try:
    from Systems.user_data_manager import UserDataManager
except ImportError:
    # Fallback for when running from different directory
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from Systems.user_data_manager import UserDataManager

class PNWAPIQuery:
    """Centralized class for handling all PNW API GraphQL queries with optimized caching."""
    
    def __init__(self, api_key: str = None, logger: logging.Logger = None):
        """Initialize the PNW API Query handler.
        
        Args:
            api_key: P&W API key. If None, will use PANDW_API_KEY from config.
            logger: Logger instance. If None, will create a default logger.
        """
        self.api_key = api_key or PANDW_API_KEY
        self.logger = logger or logging.getLogger(__name__)
        self.base_url = "https://api.politicsandwar.com/graphql"
        self.cache_ttl_seconds = 3600  # 1 hour TTL for alliance cache (updated from 5 minutes)
        self.user_data_manager = UserDataManager()
        
        # Validate API key
        if not self.api_key or self.api_key == "YOUR_API_KEY_HERE":
            error_msg = "P&W API key not configured. Please set PANDW_API_KEY in your .env file."
            self.logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _make_request(self, query: str, timeout: int = 30) -> Dict[str, Any]:
        """Make a GraphQL request to the P&W API.
        
        Args:
            query: GraphQL query string
            timeout: Request timeout in seconds
            
        Returns:
            Dict containing the API response data
            
        Raises:
            Exception: If the API request fails or returns errors
        """
        url = f"{self.base_url}?api_key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        
        try:
            self.logger.debug(f"Making API request to P&W GraphQL API")
            response = requests.post(url, json={'query': query}, headers=headers, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            
            # Check for GraphQL errors
            if 'errors' in data:
                error_messages = [error.get('message', str(error)) for error in data['errors']]
                error_msg = f"GraphQL errors: {error_messages}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
            
            return data
            
        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during API request: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
    
    async def get_alliance_nations(self, alliance_id: str, bot=None, force_refresh: bool = False) -> Optional[List[Dict[str, Any]]]:
        """Get all nations from a specific alliance with caching via UserDataManager.
        
        Args:
            alliance_id: The alliance ID to query
            bot: Discord bot instance for fetching Discord usernames (optional)
            force_refresh: If True, bypass cache and fetch fresh data
            
        Returns:
            List of nation dictionaries or None if failed
        """
        try:
            now = time.time()

            if not force_refresh:
                try:
                    alliance_data = await self.user_data_manager.get_json_data(f'alliance_{alliance_id}', {})
                    if alliance_data and isinstance(alliance_data, dict):
                        nations = alliance_data.get('nations', [])
                        last_updated = alliance_data.get('last_updated')
                        if nations and last_updated:
                            # Check if cache is still valid
                            cache_time = datetime.fromisoformat(last_updated)
                            age_seconds = (datetime.now() - cache_time).total_seconds()
                            if age_seconds < self.cache_ttl_seconds:
                                self.logger.debug(f"get_alliance_nations: cache hit for alliance {alliance_id} ({len(nations)} nations) from alliance_{alliance_id}.json")
                                # Optionally enrich with discord usernames
                                if bot:
                                    await self._fetch_discord_usernames(nations, bot)
                                return nations
                except Exception as cache_err:
                    self.logger.warning(f"get_alliance_nations: cache read failed for alliance_{alliance_id}.json, falling back to API: {cache_err}")

            # Build GraphQL query
            query = f"""
                query {{
                  alliances(id: {alliance_id}) {{
                    data {{
                      nations {{
                        id
                        alliance_position
                        nation_name
                        leader_name
                        continent
                        color
                        flag
                        discord
                        discord_id
                        war_policy
                        domestic_policy
                        social_policy
                        government_type
                        economic_policy
                        update_tz
                        vacation_mode_turns
                        beige_turns
                        tax_id
                        num_cities
                        score
                        population
                        baseball_team {{
                            id
                            date
                            name
                            stadium
                            quality
                            seating
                            rating
                            wins
                            glosses
                            runs
                            homers
                            strikeouts
                            games_played
                        }}
                        gross_national_income
                        gross_domestic_product
                        espionage_available
                        date
                        last_active
                        turns_since_last_city
                        turns_since_last_project
                        soldiers
                        tanks
                        aircraft
                        ships
                        missiles
                        nukes
                        spies
                        money
                        coal
                        oil
                        uranium
                        iron
                        bauxite
                        lead
                        gasoline
                        munitions
                        steel
                        aluminum
                        food
                        wars_won
                        wars_lost
                        offensive_wars_count
                        defensive_wars_count
                        offensive_wars {{
                          id
                          date
                          war_type
                          groundcontrol
                          airsuperiority
                          navalblockade
                          winner
                          turns_left
                        }}
                        defensive_wars {{
                          id
                          date
                          war_type
                          groundcontrol
                          airsuperiority
                          navalblockade
                          winner
                          turns_left
                        }}
                        soldier_casualties
                        tank_casualties
                        aircraft_casualties
                        ship_casualties
                        missile_casualties
                        missile_kills
                        nuke_casualties
                        nuke_kills
                        spy_casualties
                        spy_kills
                        spy_attacks
                        soldier_kills
                        tank_kills
                        aircraft_kills
                        ship_kills
                        money_looted
                        total_infrastructure_destroyed
                        total_infrastructure_lost
                        projects
                        project_bits
                        alliance_id
                        alliance_seniority
                        alliance_join_date
                        tax_id
                        credits
                        credits_redeemed_this_month
                        vip
                        commendations
                        denouncements
                        turns_since_last_city
                        turns_since_last_project
                        cities_discount
                        alliance_position
                        activity_center
                        advanced_engineering_corps
                        advanced_pirate_economy
                        arable_land_agency
                        arms_stockpile
                        bauxite_works
                        bureau_of_domestic_affairs
                        center_for_civil_engineering
                        clinical_research_center
                        emergency_gasoline_reserve
                        fallout_shelter
                        government_support_agency
                        green_technologies
                        guiding_satellite
                        central_intelligence_agency
                        international_trade_center
                        iron_dome
                        iron_works
                        moon_landing
                        mars_landing
                        mass_irrigation
                        military_doctrine
                        military_research_center
                        military_salvage
                        missile_launch_pad
                        nuclear_launch_facility
                        nuclear_research_facility
                        pirate_economy
                        propaganda_bureau
                        recycling_initiative
                        research_and_development_center
                        space_program
                        specialized_police_training_program
                        spy_satellite
                        surveillance_network
                        telecommunications_satellite
                        uranium_enrichment_program
                        vital_defense_system
                        military_research {{
                          ground_capacity
                          air_capacity
                          naval_capacity
                          ground_cost
                          air_cost
                          naval_cost
                        }}
                        cities {{
                          id
                          name
                          date
                          infrastructure
                          land
                          powered
                          nuke_date
                          oil_power
                          wind_power
                          coal_power
                          nuclear_power
                          coal_mine
                          oil_well
                          uranium_mine
                          lead_mine
                          iron_mine
                          bauxite_mine
                          gasrefinery
                          aluminum_refinery
                          steel_mill
                          munitions_factory
                          factory
                          farm
                          police_station
                          hospital
                          recycling_center
                          subway
                          supermarket
                          bank
                          shopping_mall
                          stadium
                          barracks
                          airforcebase
                          drydock
                        }}
                      }}
                    }}
                  }}
                }}
            """
            
            # Run blocking HTTP in a thread to avoid blocking event loop
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(None, self._make_request, query)

            if not data.get('data', {}).get('alliances', {}).get('data'):
                error_msg = "No alliance data returned from API"
                self.logger.warning(f"get_alliance_nations: {error_msg} for alliance {alliance_id}")
                raise Exception(error_msg)

            nations = data['data']['alliances']['data'][0]['nations']
            self.logger.info(f"get_alliance_nations: Retrieved {len(nations)} nations for alliance {alliance_id}")

            # Save alliance data to the appropriate alliance_*.json file through user_data_manager
            try:
                alliance_data = {
                    'nations': nations,
                    'alliance_id': alliance_id,
                    'last_updated': datetime.now().isoformat(),
                    'total_nations': len(nations)
                }
                await self.user_data_manager.save_json_data(f'alliance_{alliance_id}', alliance_data)
                self.logger.debug(f"get_alliance_nations: saved alliance {alliance_id} data to alliance_{alliance_id}.json")
            except Exception as save_err:
                self.logger.warning(f"get_alliance_nations: failed to save alliance data to alliance_{alliance_id}.json: {save_err}")

            # Fetch Discord usernames for nations that have Discord IDs
            if bot:
                await self._fetch_discord_usernames(nations, bot)

            return nations
            
        except Exception as e:
            self.logger.error(f"get_alliance_nations: Error retrieving alliance nations: {str(e)}")
            return None
    
    async def _fetch_discord_usernames(self, nations: List[Dict[str, Any]], bot) -> None:
        """Fetch Discord usernames for nations with Discord IDs."""
        discord_fetch_count = 0
        for nation in nations:
            discord_id = nation.get('discord_id', '')
            if discord_id and str(discord_id).strip():
                try:
                    discord_id_int = int(discord_id)
                    # Try to fetch Discord user
                    user = bot.get_user(discord_id_int)
                    if user:
                        nation['discord_username'] = user.name
                        nation['discord_display_name'] = user.display_name
                        discord_fetch_count += 1
                    else:
                        # If not in cache, try to fetch from API
                        try:
                            user = await bot.fetch_user(discord_id_int)
                            if user:
                                nation['discord_username'] = user.name
                                nation['discord_display_name'] = user.display_name
                                discord_fetch_count += 1
                        except:
                            # If fetch fails, continue without Discord info
                            pass
                except (ValueError, TypeError):
                    # Invalid Discord ID, skip
                    pass
        
        if discord_fetch_count > 0:
            self.logger.info(f"Fetched Discord info for {discord_fetch_count} nations")
    
    async def get_nation_by_id(self, nation_id: str) -> Optional[Dict[str, Any]]:
        """Get a single nation by ID with comprehensive fields.
        
        Args:
            nation_id: The nation ID to query
            
        Returns:
            Nation dictionary or None if not found
        """
        try:
            query = f"""
                query {{
                  nations(id: {nation_id}) {{
                    data {{
                      id
                      nation_name
                      leader_name
                      color
                      flag
                      discord
                      discord_id
                      beige_turns
                      num_cities
                      score
                      espionage_available
                      date
                      last_active
                      soldiers
                      tanks
                      aircraft
                      ships
                      missiles
                      nukes
                      spies
                      missile_launch_pad
                      nuclear_research_facility
                      nuclear_launch_facility
                      iron_dome
                      vital_defense_system
                      propaganda_bureau
                      military_research_center
                      space_program
                      activity_center
                      advanced_engineering_corps
                      advanced_pirate_economy
                      arable_land_agency
                      arms_stockpile
                      bauxite_works
                      bureau_of_domestic_affairs
                      center_for_civil_engineering
                      clinical_research_center
                      emergency_gasoline_reserve
                      fallout_shelter
                      green_technologies
                      government_support_agency
                      guiding_satellite
                      central_intelligence_agency
                      international_trade_center
                      iron_works
                      mass_irrigation
                      military_doctrine
                      military_salvage
                      mars_landing
                      pirate_economy
                      recycling_initiative
                      research_and_development_center
                      specialized_police_training_program
                      spy_satellite
                      surveillance_network
                      telecommunications_satellite
                      uranium_enrichment_program
                      military_research {{
                        ground_capacity
                        air_capacity
                        naval_capacity
                        ground_cost
                        air_cost
                        naval_cost
                      }}
                      projects
                      alliance_id
                      alliance_position
                      cities {{
                        id
                        name
                        infrastructure
                        stadium
                        barracks
                        factory
                        airforcebase
                        drydock
                      }}
                    }}
                  }}
                }}
            """
            
            # Run blocking HTTP in a thread to avoid blocking event loop
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(None, self._make_request, query)
            
            nations = data.get('data', {}).get('nations', {}).get('data', [])
            if not nations:
                self.logger.warning(f"get_nation_by_id: No nation found with ID {nation_id}")
                return None
            
            return nations[0]
            
        except Exception as e:
            self.logger.error(f"get_nation_by_id: Error retrieving nation {nation_id}: {str(e)}")
            return None
    
    async def get_nation_by_name(self, nation_name: str) -> Optional[Dict[str, Any]]:
        """Get a single nation by name with comprehensive fields.
        
        Args:
            nation_name: The nation name to query
            
        Returns:
            Nation dictionary or None if not found
        """
        try:
            query = f"""
                query {{
                  nations(first: 1, nation_name: "{nation_name}") {{
                    data {{
                      id
                      nation_name
                      leader_name
                      color
                      flag
                      discord
                      discord_id
                      beige_turns
                      num_cities
                      score
                      espionage_available
                      date
                      last_active
                      soldiers
                      tanks
                      aircraft
                      ships
                      missiles
                      nukes
                      spies
                      missile_launch_pad
                      nuclear_research_facility
                      nuclear_launch_facility
                      iron_dome
                      vital_defense_system
                      propaganda_bureau
                      military_research_center
                      space_program
                      activity_center
                      advanced_engineering_corps
                      advanced_pirate_economy
                      arable_land_agency
                      arms_stockpile
                      bauxite_works
                      bureau_of_domestic_affairs
                      center_for_civil_engineering
                      clinical_research_center
                      emergency_gasoline_reserve
                      fallout_shelter
                      green_technologies
                      government_support_agency
                      guiding_satellite
                      central_intelligence_agency
                      international_trade_center
                      iron_works
                      mass_irrigation
                      military_doctrine
                      military_salvage
                      mars_landing
                      pirate_economy
                      recycling_initiative
                      research_and_development_center
                      specialized_police_training_program
                      spy_satellite
                      surveillance_network
                      telecommunications_satellite
                      uranium_enrichment_program
                      military_research {{
                        ground_capacity
                        air_capacity
                        naval_capacity
                        ground_cost
                        air_cost
                        naval_cost
                      }}
                      projects
                      alliance_id
                      alliance_position
                      cities {{
                        id
                        name
                        infrastructure
                        stadium
                        barracks
                        factory
                        airforcebase
                        drydock
                      }}
                    }}
                  }}
                }}
            """
            
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(None, self._make_request, query)
            
            nations = data.get('data', {}).get('nations', {}).get('data', [])
            if not nations:
                self.logger.warning(f"get_nation_by_name: No nation found with name '{nation_name}'")
                return None
            
            return nations[0]
            
        except Exception as e:
            self.logger.error(f"get_nation_by_name: Error retrieving nation '{nation_name}': {str(e)}")
            return None
    
    async def get_nation_by_leader(self, leader_name: str) -> Optional[Dict[str, Any]]:
        """Get a single nation by leader name with comprehensive fields.
        
        Args:
            leader_name: The leader name to query
            
        Returns:
            Nation dictionary or None if not found
        """
        try:
            query = f"""
                query {{
                  nations(first: 1, leader_name: "{leader_name}") {{
                    data {{
                      id
                      nation_name
                      leader_name
                      color
                      flag
                      discord
                      discord_id
                      beige_turns
                      num_cities
                      score
                      espionage_available
                      date
                      last_active
                      soldiers
                      tanks
                      aircraft
                      ships
                      missiles
                      nukes
                      spies
                      missile_launch_pad
                      nuclear_research_facility
                      nuclear_launch_facility
                      iron_dome
                      vital_defense_system
                      propaganda_bureau
                      military_research_center
                      space_program
                      activity_center
                      advanced_engineering_corps
                      advanced_pirate_economy
                      arable_land_agency
                      arms_stockpile
                      bauxite_works
                      bureau_of_domestic_affairs
                      center_for_civil_engineering
                      clinical_research_center
                      emergency_gasoline_reserve
                      fallout_shelter
                      green_technologies
                      government_support_agency
                      guiding_satellite
                      central_intelligence_agency
                      international_trade_center
                      iron_works
                      mass_irrigation
                      military_doctrine
                      military_salvage
                      mars_landing
                      pirate_economy
                      recycling_initiative
                      research_and_development_center
                      specialized_police_training_program
                      spy_satellite
                      surveillance_network
                      telecommunications_satellite
                      uranium_enrichment_program
                      military_research {{
                        ground_capacity
                        air_capacity
                        naval_capacity
                        ground_cost
                        air_cost
                        naval_cost
                      }}
                      projects
                      alliance_id
                      alliance_position
                      cities {{
                        id
                        name
                        infrastructure
                        stadium
                        barracks
                        factory
                        airforcebase
                        drydock
                      }}
                    }}
                  }}
                }}
            """
            
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(None, self._make_request, query)
            
            nations = data.get('data', {}).get('nations', {}).get('data', [])
            if not nations:
                self.logger.warning(f"get_nation_by_leader: No nation found with leader '{leader_name}'")
                return None
            
            return nations[0]
            
        except Exception as e:
            self.logger.error(f"get_nation_by_leader: Error retrieving nation with leader '{leader_name}': {str(e)}")
            return None

    async def get_cache_info(self) -> Dict[str, Any]:
        """Get information about cached alliance data using UserDataManager individual alliance files."""
        try:
            info = []
            now = time.time()
            
            # Get alliance files from the Data/Bloc directory
            base_systems_dir = Path(__file__).parent.parent.parent
            bloc_dir = base_systems_dir / "Data" / "Bloc"
            
            if bloc_dir.exists():
                for alliance_file in bloc_dir.glob("alliance_*.json"):
                    try:
                        alliance_id = alliance_file.stem.replace('alliance_', '')
                        nations_data = await self.user_data_manager.get_json_data(alliance_file.stem, [])
                        
                        # Calculate file age
                        file_age = max(0, int(now - alliance_file.stat().st_mtime))
                        
                        info.append({
                            'key': alliance_file.stem,
                            'alliance_id': alliance_id,
                            'cache_file': str(alliance_file),
                            'count': len(nations_data) if isinstance(nations_data, list) else 0,
                            'age_seconds': file_age
                        })
                    except Exception as e:
                        self.logger.warning(f"get_cache_info: failed to read {alliance_file}: {e}")
                        continue
            
            return {
                'total_cached_alliances': len(info),
                'cached_alliances': info,
                'cache_status': f'Active, TTL={self.cache_ttl_seconds}s'
            }
        except Exception as e:
            self.logger.warning(f"get_cache_info: failed to read cache info: {e}")
            return {
                'total_cached_alliances': 0,
                'cached_alliances': [],
                'cache_status': 'Error reading cache'
            }

# Convenience function for creating a query instance
def create_query_instance(api_key: str = None, logger: logging.Logger = None) -> PNWAPIQuery:
    """Create a new PNWAPIQuery instance.
    
    Args:
        api_key: P&W API key. If None, will use PANDW_API_KEY from config.
        logger: Logger instance. If None, will create a default logger.
        
    Returns:
        PNWAPIQuery instance
    """
    return PNWAPIQuery(api_key=api_key, logger=logger)