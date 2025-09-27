import requests
import logging
from typing import List, Dict, Optional, Any
import os
import sys
import time
import asyncio
from datetime import datetime, timedelta

# Add parent directory to path for config import
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import PANDW_API_KEY

# Import UserDataManager for caching
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
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
            cache_key = f"alliance_data_{alliance_id}"
            now = time.time()

            # Try cache first unless forcing refresh
            if not force_refresh:
                try:
                    alliance_cache = await self.user_data_manager.get_json_data('alliance_cache', {})
                    cache_entry = alliance_cache.get(cache_key)
                    if cache_entry and isinstance(cache_entry, dict):
                        ts = cache_entry.get('timestamp', 0)
                        data = cache_entry.get('nations', [])
                        if data and (now - ts) < self.cache_ttl_seconds:
                            self.logger.debug(f"get_alliance_nations: cache hit for alliance {alliance_id} ({len(data)} nations)")
                            # Optionally enrich with discord usernames
                            if bot:
                                await self._fetch_discord_usernames(data, bot)
                            return data
                except Exception as cache_err:
                    self.logger.warning(f"get_alliance_nations: cache read failed, falling back to API: {cache_err}")

            # Build GraphQL query
            query = f"""
                query {{
                  alliances(id: {alliance_id}) {{
                    data {{
                      nations {{
                        id
                        nation_name
                        leader_name
                        continent
                        color
                        flag
                        discord_id
                        war_policy
                        domestic_policy
                        update_tz
                        vacation_mode_turns
                        beige_turns
                        tax_id
                        num_cities
                        score
                        population
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
                        soldier_casualties
                        tank_casualties
                        aircraft_casualties
                        ship_casualties
                        missile_casualties
                        nuke_casualties
                        spy_casualties
                        money_looted
                        projects
                        alliance_id
                        alliance_position
                        alliance {{
                          id
                          name
                          acronym
                          score
                          color
                          date
                          accept_members
                          flag
                          forum_link
                          discord_link
                          wiki_link
                        }}
                        missile_launch_pad
                        nuclear_research_facility
                        nuclear_launch_facility
                        iron_dome
                        vital_defense_system
                        propaganda_bureau
                        military_research_center
                        space_program
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
                          oilpower
                          windpower
                          coalpower
                          nuclearpower
                          coalmine
                          oilwell
                          uramine
                          leadmine
                          ironmine
                          bauxitemine
                          gasrefinery
                          aluminumrefinery
                          steelmill
                          munitionsfactory
                          factory
                          farm
                          policestation
                          hospital
                          recyclingcenter
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
            
            data = self._make_request(query)

            if not data.get('data', {}).get('alliances', {}).get('data'):
                error_msg = "No alliance data returned from API"
                self.logger.warning(f"get_alliance_nations: {error_msg} for alliance {alliance_id}")
                raise Exception(error_msg)

            nations = data['data']['alliances']['data'][0]['nations']
            self.logger.info(f"get_alliance_nations: Retrieved {len(nations)} nations for alliance {alliance_id}")

            # Persist to cache
            try:
                alliance_cache = await self.user_data_manager.get_json_data('alliance_cache', {})
                alliance_cache[cache_key] = {
                    'timestamp': now,
                    'nations': nations,
                }
                await self.user_data_manager.save_json_data('alliance_cache', alliance_cache)
                self.logger.debug(f"get_alliance_nations: cached alliance {alliance_id} with {len(nations)} nations")
            except Exception as save_err:
                self.logger.warning(f"get_alliance_nations: failed to write cache: {save_err}")

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
                      continent
                      color
                      flag
                      discord_id
                      war_policy
                      domestic_policy
                      update_tz
                      vacation_mode_turns
                      beige_turns
                      tax_id
                      num_cities
                      score
                      population
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
                      soldier_casualties
                      tank_casualties
                      aircraft_casualties
                      ship_casualties
                      missile_casualties
                      nuke_casualties
                      spy_casualties
                      money_looted
                      projects
                      alliance_id
                      alliance {{
                        id
                        name
                        acronym
                        score
                        color
                        date
                        accept_members
                        flag
                        forum_link
                        discord_link
                        wiki_link
                      }}
                      missile_launch_pad
                      nuclear_research_facility
                      nuclear_launch_facility
                      iron_dome
                      vital_defense_system
                      propaganda_bureau
                      military_research_center
                      space_program
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
                        oilpower
                        windpower
                        coalpower
                        nuclearpower
                        coalmine
                        oilwell
                        uramine
                        leadmine
                        ironmine
                        bauxitemine
                        gasrefinery
                        aluminumrefinery
                        steelmill
                        munitionsfactory
                        factory
                        farm
                        policestation
                        hospital
                        recyclingcenter
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
                      continent
                      color
                      flag
                      discord_id
                      war_policy
                      domestic_policy
                      update_tz
                      vacation_mode_turns
                      beige_turns
                      tax_id
                      num_cities
                      score
                      population
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
                      soldier_casualties
                      tank_casualties
                      aircraft_casualties
                      ship_casualties
                      missile_casualties
                      nuke_casualties
                      spy_casualties
                      money_looted
                      projects
                      alliance_id
                      alliance {{
                        id
                        name
                        acronym
                        score
                        color
                        date
                        accept_members
                        flag
                        forum_link
                        discord_link
                        wiki_link
                      }}
                      missile_launch_pad
                      nuclear_research_facility
                      nuclear_launch_facility
                      iron_dome
                      vital_defense_system
                      propaganda_bureau
                      military_research_center
                      space_program
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
                        oilpower
                        windpower
                        coalpower
                        nuclearpower
                        coalmine
                        oilwell
                        uramine
                        leadmine
                        ironmine
                        bauxitemine
                        gasrefinery
                        aluminumrefinery
                        steelmill
                        munitionsfactory
                        factory
                        farm
                        policestation
                        hospital
                        recyclingcenter
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
                      continent
                      color
                      flag
                      discord_id
                      war_policy
                      domestic_policy
                      update_tz
                      vacation_mode_turns
                      beige_turns
                      tax_id
                      num_cities
                      score
                      population
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
                      soldier_casualties
                      tank_casualties
                      aircraft_casualties
                      ship_casualties
                      missile_casualties
                      nuke_casualties
                      spy_casualties
                      money_looted
                      projects
                      alliance_id
                      alliance {{
                        id
                        name
                        acronym
                        score
                        color
                        date
                        accept_members
                        flag
                        forum_link
                        discord_link
                        wiki_link
                      }}
                      missile_launch_pad
                      nuclear_research_facility
                      nuclear_launch_facility
                      iron_dome
                      vital_defense_system
                      propaganda_bureau
                      military_research_center
                      space_program
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
                        oilpower
                        windpower
                        coalpower
                        nuclearpower
                        coalmine
                        oilwell
                        uramine
                        leadmine
                        ironmine
                        bauxitemine
                        gasrefinery
                        aluminumrefinery
                        steelmill
                        munitionsfactory
                        factory
                        farm
                        policestation
                        hospital
                        recyclingcenter
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
        """Get information about cached alliance data using UserDataManager cache file."""
        try:
            alliance_cache = await self.user_data_manager.get_json_data('alliance_cache', {})
            info = []
            now = time.time()
            for key, entry in alliance_cache.items():
                try:
                    if not isinstance(entry, dict):
                        continue
                    ts = entry.get('timestamp', 0)
                    nations = entry.get('nations', [])
                    age = max(0, int(now - ts))
                    if key.startswith('alliance_data_'):
                        alliance_id = key.replace('alliance_data_', '')
                    else:
                        alliance_id = key
                    info.append({
                        'key': key,
                        'alliance_id': alliance_id,
                        'count': len(nations) if isinstance(nations, list) else 0,
                        'age_seconds': age
                    })
                except Exception:
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

    async def clear_alliance_cache(self, alliance_id: str = None) -> Dict[str, Any]:
        """Clear alliance cache entries in UserDataManager file.
        
        Args:
            alliance_id: If provided, clear only this alliance; otherwise clear all
            
        Returns:
            Dict with operation results
        """
        try:
            alliance_cache = await self.user_data_manager.get_json_data('alliance_cache', {})
            cleared = 0
            if alliance_id is not None:
                key = f"alliance_data_{alliance_id}"
                if key in alliance_cache:
                    alliance_cache.pop(key, None)
                    cleared = 1
            else:
                # Clear all entries matching pattern
                keys = [k for k in list(alliance_cache.keys()) if k.startswith('alliance_data_')]
                for k in keys:
                    alliance_cache.pop(k, None)
                cleared = len(keys)
            await self.user_data_manager.save_json_data('alliance_cache', alliance_cache)
            return {
                'cleared_count': cleared,
                'message': 'Alliance cache cleared'
            }
        except Exception as e:
            self.logger.warning(f"clear_alliance_cache: failed to clear cache: {e}")
            return {
                'cleared_count': 0,
                'message': 'Failed to clear alliance cache'
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