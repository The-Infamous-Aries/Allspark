from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
import logging
import sys
import os

# Add parent directory to path for config import
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import ARIES_NATION_ID, CARNAGE_NATION_ID, PRIMAL_NATION_ID


class AllianceCalculator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def _log_error(self, error_msg: str, exception: Exception = None, context: str = ""):
        if exception:
            self.logger.error(f"{context}: {error_msg} - {str(exception)}")
        else:
            self.logger.error(f"{context}: {error_msg}")
    
    def _validate_input(self, data: Any, expected_type: type, field_name: str = "data") -> bool:
        if not isinstance(data, expected_type):
            self.logger.warning(f"Input validation failed: {field_name} expected {expected_type}, got {type(data)}")
            return False
        return True
    
    def _safe_get(self, data: dict, key: str, default: Any = None, expected_type: type = None) -> Any:
        try:
            value = data.get(key, default)
            if expected_type and value is not None:
                if not isinstance(value, expected_type):
                    try:
                        value = expected_type(value)
                    except (ValueError, TypeError):
                        return default
            return value
        except (AttributeError, TypeError):
            return default
             
    async def calculate_improvements_data(self, nations: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            active_nations = self.get_active_nations(nations)
            improvements = {
                'coalpower': 0,
                'oilpower': 0,
                'nuclearpower': 0,
                'windpower': 0,
                'oilwell': 0,
                'coalmine': 0,
                'uramine': 0,
                'ironmine': 0,
                'bauxitemine': 0,
                'leadmine': 0,
                'farm': 0,
                'gasrefinery': 0,
                'steelmill': 0,
                'aluminumrefinery': 0,
                'munitionsfactory': 0,
                'policestation': 0,
                'hospital': 0,
                'bank': 0,
                'supermarket': 0,
                'shopping_mall': 0,
                'stadium': 0,
                'subway': 0,
                'recyclingcenter': 0,
                'barracks': 0,
                'factory': 0,
                'hangar': 0,
                'drydock': 0
            }         
            total_cities = 0
            for nation in active_nations:
                try:
                    cities = nation.get('cities', [])
                    if not cities:
                        continue                    
                    total_cities += len(cities)
                    for city in cities:
                        if not isinstance(city, dict):
                            continue
                        improvements['coalpower'] += self._safe_get(city, 'coal_power', 0, int)
                        improvements['oilpower'] += self._safe_get(city, 'oil_power', 0, int)
                        improvements['nuclearpower'] += self._safe_get(city, 'nuclear_power', 0, int)
                        improvements['windpower'] += self._safe_get(city, 'wind_power', 0, int)
                        improvements['oilwell'] += self._safe_get(city, 'oil_well', 0, int)
                        improvements['coalmine'] += self._safe_get(city, 'coal_mine', 0, int)
                        improvements['uramine'] += self._safe_get(city, 'uranium_mine', 0, int)
                        improvements['ironmine'] += self._safe_get(city, 'iron_mine', 0, int)
                        improvements['bauxitemine'] += self._safe_get(city, 'bauxite_mine', 0, int)
                        improvements['leadmine'] += self._safe_get(city, 'lead_mine', 0, int)
                        improvements['farm'] += self._safe_get(city, 'farm', 0, int)
                        improvements['gasrefinery'] += self._safe_get(city, 'gasrefinery', 0, int)
                        improvements['steelmill'] += self._safe_get(city, 'steel_mill', 0, int)
                        improvements['aluminumrefinery'] += self._safe_get(city, 'aluminum_refinery', 0, int)
                        improvements['munitionsfactory'] += self._safe_get(city, 'munitions_factory', 0, int)
                        improvements['factory'] += self._safe_get(city, 'factory', 0, int)
                        improvements['policestation'] += self._safe_get(city, 'police_station', 0, int)
                        improvements['hospital'] += self._safe_get(city, 'hospital', 0, int)
                        improvements['bank'] += self._safe_get(city, 'bank', 0, int)
                        improvements['supermarket'] += self._safe_get(city, 'supermarket', 0, int)
                        improvements['shopping_mall'] += self._safe_get(city, 'shopping_mall', 0, int)
                        improvements['stadium'] += self._safe_get(city, 'stadium', 0, int)
                        improvements['subway'] += self._safe_get(city, 'subway', 0, int)
                        improvements['recyclingcenter'] += self._safe_get(city, 'recycling_center', 0, int)
                        improvements['barracks'] += self._safe_get(city, 'barracks', 0, int)
                        improvements['hangar'] += self._safe_get(city, 'airforcebase', 0, int)
                        improvements['drydock'] += self._safe_get(city, 'drydock', 0, int)             
                except Exception as e:
                    self._log_error(f"Error processing improvements for nation: {e}", e, "calculate_improvements_data")
                    continue
            total_power = (improvements['coalpower'] + improvements['oilpower'] + 
                          improvements['nuclearpower'] + improvements['windpower'])           
            total_improvements = sum(improvements.values())
            avg_per_city = total_improvements / total_cities if total_cities > 0 else 0
            self.logger.info(f"Improvements calculated: {improvements['barracks']} barracks, {improvements['factory']} factories, "
                           f"{improvements['hangar']} hangars, {improvements['drydock']} drydocks across {total_cities} cities "
                           f"({len(active_nations)} active nations)")
            improvements.update({
                'total_power': total_power,
                'total_improvements': total_improvements,
                'total_cities': total_cities,
                'avg_per_city': avg_per_city,
                'active_nations': len(active_nations)
            })            
            self.logger.info(f"Successfully calculated improvements data for {len(active_nations)} nations with {total_cities} cities")
            return improvements           
        except Exception as e:
            self._log_error(f"Error calculating improvements data: {e}", e, "calculate_improvements_data")
            return {
                'coalpower': 0, 'oilpower': 0, 'nuclearpower': 0, 'windpower': 0,
                'oilwell': 0, 'coalmine': 0, 'uramine': 0, 'ironmine': 0, 'bauxitemine': 0, 'leadmine': 0, 'farm': 0,
                'gasrefinery': 0, 'steelmill': 0, 'aluminumrefinery': 0, 'munitionsfactory': 0, 'factory': 0,
                'policestation': 0, 'hospital': 0, 'bank': 0, 'supermarket': 0, 'shopping_mall': 0, 'stadium': 0, 'subway': 0, 'recyclingcenter': 0,
                'barracks': 0, 'hangar': 0, 'drydock': 0,
                'total_power': 0, 'total_improvements': 0, 'total_cities': 0, 'avg_per_city': 0, 'active_nations': 0
            }
    
    def has_project(self, nation: Dict[str, Any], project_name: str) -> bool:
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
            self.logger.debug(f"has_project: Checking project '{project_name}'")
            project_field_mapping = {
                # Strategic Military Projects
                'Iron Dome': 'iron_dome',
                'Missile Launch Pad': 'missile_launch_pad',
                'Nuclear Research Facility': 'nuclear_research_facility',
                'Nuclear Launch Facility': 'nuclear_launch_facility',
                'Vital Defense System': 'vital_defense_system',
                'Propaganda Bureau': 'propaganda_bureau',
                'Military Research Center': 'military_research_center',
                'Space Program': 'space_program',
                'Activity Center': 'activity_center',
                'Advanced Engineering Corps': 'advanced_engineering_corps',
                'Advanced Pirate Economy': 'advanced_pirate_economy',
                'Arable Land Agency': 'arable_land_agency',
                'Arms Stockpile': 'arms_stockpile',
                'Bauxite Works': 'bauxite_works',
                'Bureau of Domestic Affairs': 'bureau_of_domestic_affairs',
                'Center Civil Engineering': 'center_for_civil_engineering',
                'Clinical Research Center': 'clinical_research_center',
                'Emergency Gasoline Reserve': 'emergency_gasoline_reserve',
                'Fallout Shelter': 'fallout_shelter',
                'Green Technologies': 'green_technologies',
                'Government Support Agency': 'government_support_agency',
                'Guiding Satellite': 'guiding_satellite',
                'Central Intelligence Agency': 'central_intelligence_agency',
                'International Trade Center': 'international_trade_center',
                'Iron Works': 'iron_works',
                'Mass Irrigation': 'mass_irrigation',
                'Military Doctrine': 'military_doctrine',
                'Military Salvage': 'military_salvage',
                'Mars Landing': 'mars_landing',
                'Moon Landing': 'moon_landing',
                'Pirate Economy': 'pirate_economy',
                'Recycling Initiative': 'recycling_initiative',
                'Research & Development Center': 'research_and_development_center',
                'Specialized Police Training Program': 'specialized_police_training_program',
                'Spy Satellite': 'spy_satellite',
                'Surveillance Network': 'surveillance_network',
                'Telecommunications Satellite': 'telecommunications_satellite',
                'Uranium Enrichment Program': 'uranium_enrichment_program'
            }
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
    
    def get_active_nations(self, nations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self._validate_input(nations, list, "nations"):
            self.logger.warning("get_active_nations: Invalid nations input, returning empty list")
            return []        
        if not nations:
            self.logger.debug("get_active_nations: Empty nations list provided")
            return []        
        try:
            self.logger.debug(f"get_active_nations: Processing {len(nations)} nations")            
            active_nations = []
            now = datetime.now(timezone.utc)
            fourteen_days_ago = now - timedelta(days=14)
            
            for i, nation in enumerate(nations):
                try:
                    if not isinstance(nation, dict):
                        self.logger.warning(f"get_active_nations: Nation at index {i} is not a dictionary, skipping")
                        continue
                    
                    # Check vacation mode
                    vacation_turns = self._safe_get(nation, 'vacation_mode_turns', 0, int)
                    if vacation_turns > 0:
                        self.logger.debug(f"get_active_nations: Skipping nation {nation.get('nation_name', 'Unknown')} - in vacation mode ({vacation_turns} turns)")
                        continue
                    
                    # Check applicant status
                    alliance_position = self._safe_get(nation, 'alliance_position', '', str)
                    if alliance_position == 'APPLICANT':
                        self.logger.debug(f"get_active_nations: Skipping nation {nation.get('nation_name', 'Unknown')} - applicant status")
                        continue
                    
                    # Check 14+ days inactive
                    last_active_str = self._safe_get(nation, 'last_active', '', str)
                    if last_active_str:
                        try:
                            if last_active_str.endswith('+00:00'):
                                last_active = datetime.fromisoformat(last_active_str.replace('+00:00', '')).replace(tzinfo=timezone.utc)
                            else:
                                last_active = datetime.fromisoformat(last_active_str).replace(tzinfo=timezone.utc)
                            
                            if last_active < fourteen_days_ago:
                                self.logger.debug(f"get_active_nations: Skipping nation {nation.get('nation_name', 'Unknown')} - inactive for 14+ days")
                                continue
                        except (ValueError, TypeError):
                            # If we can't parse last_active, skip the nation to be safe
                            self.logger.debug(f"get_active_nations: Skipping nation {nation.get('nation_name', 'Unknown')} - unable to parse last_active date")
                            continue
                    else:
                        # If last_active is missing or empty, exclude the nation to be safe
                        self.logger.debug(f"get_active_nations: Skipping nation {nation.get('nation_name', 'Unknown')} - missing last_active date")
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
    
    def calculate_nation_statistics(self, nations: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not nations:
            return {
                'total_nations': 0,
                'active_nations': 0,
                'applicant_nations': 0,
                'vacation_nations': 0,
                'grey_nations': 0,
                'beige_nations': 0,
                'inactive_7_days': 0,
                'inactive_14_days': 0
            }       
        try:
            total_nations = len(nations)
            active_nations = 0
            applicant_nations = 0
            vacation_nations = 0
            grey_nations = 0
            beige_nations = 0
            inactive_7_days = 0
            inactive_14_days = 0
            now = datetime.now(timezone.utc)
            seven_days_ago = now - timedelta(days=7)
            fourteen_days_ago = now - timedelta(days=14)           
            for nation in nations:
                if not isinstance(nation, dict):
                    continue
                vacation_turns = self._safe_get(nation, 'vacation_mode_turns', 0, int)
                alliance_position = self._safe_get(nation, 'alliance_position', '', str)
                color = self._safe_get(nation, 'color', '', str).upper()
                last_active_str = self._safe_get(nation, 'last_active', '', str)
                is_active = (vacation_turns == 0 and alliance_position.upper() != 'APPLICANT')
                last_active = None
                if last_active_str:
                    try:
                        if last_active_str.endswith('+00:00'):
                            last_active = datetime.fromisoformat(last_active_str.replace('+00:00', '')).replace(tzinfo=timezone.utc)
                        else:
                            last_active = datetime.fromisoformat(last_active_str).replace(tzinfo=timezone.utc)
                    except (ValueError, TypeError):
                        last_active = None
                if vacation_turns > 0 and alliance_position.upper() != 'APPLICANT':
                    vacation_nations += 1
                if alliance_position.upper() == 'APPLICANT':
                    applicant_nations += 1
                if is_active and last_active:
                    if last_active < fourteen_days_ago:
                        inactive_14_days += 1
                    elif last_active < seven_days_ago:
                        inactive_7_days += 1                
                if is_active:
                    active_nations += 1
                    if color == 'GREY' or color == 'GRAY':
                        grey_nations += 1
                    elif color == 'BEIGE':
                        beige_nations += 1           
            return {
                'total_nations': total_nations,
                'active_nations': active_nations,
                'applicant_nations': applicant_nations,
                'vacation_nations': vacation_nations,
                'grey_nations': grey_nations,
                'beige_nations': beige_nations,
                'inactive_7_days': inactive_7_days,
                'inactive_14_days': inactive_14_days
            }           
        except Exception as e:
            self._log_error("Error calculating nation statistics", e, "calculate_nation_statistics")
            return {
                'total_nations': 0,
                'active_nations': 0,
                'applicant_nations': 0,
                'vacation_nations': 0,
                'grey_nations': 0,
                'beige_nations': 0,
                'inactive_7_days': 0,
                'inactive_14_days': 0
            }

    def calculate_alliance_statistics(self, nations: List[Dict[str, Any]]) -> Dict[str, Any]:
        stats = {
            'total_nations': len(nations),
            'total_score': sum(nation.get('score', 0) for nation in nations),
            'total_cities': sum(nation.get('num_cities', 0) for nation in nations),
            'missile_capable': 0,
            'nuclear_capable': 0,
            'vital_defense_system': 0,
            'iron_dome': 0,
            'propaganda_bureau': 0,
            'military_research_center': 0,
            'space_program': 0,
            'missile_launch_pad': 0,
            'nuclear_research_facility': 0,
            'nuclear_launch_facility': 0,
            'total_military': {
                'soldiers': 0,
                'tanks': 0,
                'aircraft': 0,
                'ships': 0,
                'missiles': 0,
                'nukes': 0
            },
            'production_capacity': {
                'total_barracks': 0,
                'total_factories': 0,
                'total_hangars': 0,
                'total_drydocks': 0,
                'daily_soldiers': 0,
                'daily_tanks': 0,
                'daily_aircraft': 0,
                'daily_ships': 0,
                'daily_missiles': 0,
                'daily_nukes': 0,
                'max_soldiers': 0,
                'max_tanks': 0,
                'max_aircraft': 0,
                'max_ships': 0,
                'max_missiles': 0,
                'max_nukes': 0
            }
        }       
        for nation in nations:
            if self.has_project(nation, 'Missile Launch Pad'):
                stats['missile_capable'] += 1
                stats['missile_launch_pad'] += 1
            if self.has_project(nation, 'Nuclear Research Facility'):
                stats['nuclear_capable'] += 1
                stats['nuclear_research_facility'] += 1
            if self.has_project(nation, 'Vital Defense System'):
                stats['vital_defense_system'] += 1
            if self.has_project(nation, 'Iron Dome'):
                stats['iron_dome'] += 1
            if self.has_project(nation, 'Propaganda Bureau'):
                stats['propaganda_bureau'] += 1
            if self.has_project(nation, 'Military Research Center'):
                stats['military_research_center'] += 1
            if self.has_project(nation, 'Space Program'):
                stats['space_program'] += 1
            if self.has_project(nation, 'Nuclear Launch Facility'):
                stats['nuclear_launch_facility'] += 1
            military = nation.get('military', {}) or {}
            stats['total_military']['soldiers'] += (military.get('soldiers', 0)
                                                    if 'soldiers' in military else nation.get('soldiers', 0))
            stats['total_military']['tanks'] += (military.get('tanks', 0)
                                                 if 'tanks' in military else nation.get('tanks', 0))
            stats['total_military']['aircraft'] += (military.get('aircraft', 0)
                                                    if 'aircraft' in military else nation.get('aircraft', 0))
            stats['total_military']['ships'] += (military.get('ships', 0)
                                                 if 'ships' in military else nation.get('ships', 0))
            stats['total_military']['missiles'] += (military.get('missiles', 0)
                                                   if 'missiles' in military else nation.get('missiles', 0))
            stats['total_military']['nukes'] += (military.get('nukes', 0)
                                                 if 'nukes' in military else nation.get('nukes', 0))
            production_data = self.calculate_military_purchase_limits(nation)
            stats['production_capacity']['total_barracks'] += production_data.get('total_barracks', 0)
            stats['production_capacity']['total_factories'] += production_data.get('total_factories', 0)
            stats['production_capacity']['total_hangars'] += production_data.get('total_hangars', 0)
            stats['production_capacity']['total_drydocks'] += production_data.get('total_drydocks', 0)
            stats['production_capacity']['daily_soldiers'] += production_data.get('soldiers', 0)
            stats['production_capacity']['daily_tanks'] += production_data.get('tanks', 0)
            stats['production_capacity']['daily_aircraft'] += production_data.get('aircraft', 0)
            stats['production_capacity']['daily_ships'] += production_data.get('ships', 0)
            stats['production_capacity']['daily_missiles'] += production_data.get('missiles', 0)
            stats['production_capacity']['daily_nukes'] += production_data.get('nukes', 0)
            stats['production_capacity']['max_soldiers'] += production_data.get('soldiers_max', 0)
            stats['production_capacity']['max_tanks'] += production_data.get('tanks_max', 0)
            stats['production_capacity']['max_aircraft'] += production_data.get('aircraft_max', 0)
            stats['production_capacity']['max_ships'] += production_data.get('ships_max', 0)
            if self.has_project(nation, 'Missile Launch Pad'):
                stats['production_capacity']['max_missiles'] += 50           
            if self.has_project(nation, 'Nuclear Research Facility'):
                stats['production_capacity']['max_nukes'] += 50        
        return stats
    
    def calculate_full_mill_data(self, nations: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            active_nations = self.get_active_nations(nations)
            current_soldiers = 0
            current_tanks = 0
            current_aircraft = 0
            current_ships = 0
            current_missiles = 0
            current_nukes = 0           
            max_soldiers = 0
            max_tanks = 0
            max_aircraft = 0
            max_ships = 0            
            daily_soldiers = 0
            daily_tanks = 0
            daily_aircraft = 0
            daily_ships = 0
            daily_missiles = 0
            daily_nukes = 0            
            total_cities = 0
            total_score = 0
            
            # Track individual nation days for finding maximums
            max_soldier_days = 0
            max_tank_days = 0
            max_aircraft_days = 0
            max_ship_days = 0
            max_soldier_nation = ""
            max_tank_nation = ""
            max_aircraft_nation = ""
            max_ship_nation = ""
            
            for nation in active_nations:
                military = nation.get('military', {}) or {}
                current_soldiers += (military.get('soldiers', 0) if 'soldiers' in military else nation.get('soldiers', 0))
                current_tanks += (military.get('tanks', 0) if 'tanks' in military else nation.get('tanks', 0))
                current_aircraft += (military.get('aircraft', 0) if 'aircraft' in military else nation.get('aircraft', 0))
                current_ships += (military.get('ships', 0) if 'ships' in military else nation.get('ships', 0))
                current_missiles += (military.get('missiles', 0) if 'missiles' in military else nation.get('missiles', 0))
                current_nukes += (military.get('nukes', 0) if 'nukes' in military else nation.get('nukes', 0))
                total_cities += nation.get('num_cities', 0)
                total_score += nation.get('score', 0)
                
                # Calculate individual nation limits and days
                limits = self.calculate_military_purchase_limits(nation)
                nation_current_soldiers = (military.get('soldiers', 0) if 'soldiers' in military else nation.get('soldiers', 0))
                nation_current_tanks = (military.get('tanks', 0) if 'tanks' in military else nation.get('tanks', 0))
                nation_current_aircraft = (military.get('aircraft', 0) if 'aircraft' in military else nation.get('aircraft', 0))
                nation_current_ships = (military.get('ships', 0) if 'ships' in military else nation.get('ships', 0))
                
                nation_max_soldiers = limits.get('soldiers_max', 0)
                nation_max_tanks = limits.get('tanks_max', 0)
                nation_max_aircraft = limits.get('aircraft_max', 0)
                nation_max_ships = limits.get('ships_max', 0)
                
                nation_daily_soldiers = limits.get('soldiers_daily', 0)
                nation_daily_tanks = limits.get('tanks_daily', 0)
                nation_daily_aircraft = limits.get('aircraft_daily', 0)
                nation_daily_ships = limits.get('ships_daily', 0)
                
                nation_soldier_gap = max(0, nation_max_soldiers - nation_current_soldiers)
                nation_tank_gap = max(0, nation_max_tanks - nation_current_tanks)
                nation_aircraft_gap = max(0, nation_max_aircraft - nation_current_aircraft)
                nation_ship_gap = max(0, nation_max_ships - nation_current_ships)
                
                nation_soldier_days = nation_soldier_gap / nation_daily_soldiers if nation_daily_soldiers > 0 else 0
                nation_tank_days = nation_tank_gap / nation_daily_tanks if nation_daily_tanks > 0 else 0
                nation_aircraft_days = nation_aircraft_gap / nation_daily_aircraft if nation_daily_aircraft > 0 else 0
                nation_ship_days = nation_ship_gap / nation_daily_ships if nation_daily_ships > 0 else 0
                
                # Update maximum days and corresponding nation names
                if nation_soldier_days > max_soldier_days:
                    max_soldier_days = nation_soldier_days
                    max_soldier_nation = nation.get('nation_name', 'Unknown')
                if nation_tank_days > max_tank_days:
                    max_tank_days = nation_tank_days
                    max_tank_nation = nation.get('nation_name', 'Unknown')
                if nation_aircraft_days > max_aircraft_days:
                    max_aircraft_days = nation_aircraft_days
                    max_aircraft_nation = nation.get('nation_name', 'Unknown')
                if nation_ship_days > max_ship_days:
                    max_ship_days = nation_ship_days
                    max_ship_nation = nation.get('nation_name', 'Unknown')
                
                daily_soldiers += nation_daily_soldiers
                daily_tanks += nation_daily_tanks
                daily_aircraft += nation_daily_aircraft
                daily_ships += nation_daily_ships
                daily_missiles += limits.get('missiles', 0)
                daily_nukes += limits.get('nukes', 0)
                max_soldiers += nation_max_soldiers
                max_tanks += nation_max_tanks
                max_aircraft += nation_max_aircraft
                max_ships += nation_max_ships
            
            soldier_gap = max(0, max_soldiers - current_soldiers)
            tank_gap = max(0, max_tanks - current_tanks)
            aircraft_gap = max(0, max_aircraft - current_aircraft)
            ship_gap = max(0, max_ships - current_ships)
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
                'current_missiles': current_missiles,
                'current_nukes': current_nukes,
                'max_soldiers': max_soldiers,
                'max_tanks': max_tanks,
                'max_aircraft': max_aircraft,
                'max_ships': max_ships,
                'daily_soldiers': daily_soldiers,
                'daily_tanks': daily_tanks,
                'daily_aircraft': daily_aircraft,
                'daily_ships': daily_ships,
                'daily_missiles': daily_missiles,
                'daily_nukes': daily_nukes,
                'soldier_gap': soldier_gap,
                'tank_gap': tank_gap,
                'aircraft_gap': aircraft_gap,
                'ship_gap': ship_gap,
                'soldier_days': soldier_days,
                'tank_days': tank_days,
                'aircraft_days': aircraft_days,
                'ship_days': ship_days,
                # New fields for individual nation maximums
                'max_soldier_days': max_soldier_days,
                'max_tank_days': max_tank_days,
                'max_aircraft_days': max_aircraft_days,
                'max_ship_days': max_ship_days,
                'max_soldier_nation': max_soldier_nation,
                'max_tank_nation': max_tank_nation,
                'max_aircraft_nation': max_aircraft_nation,
                'max_ship_nation': max_ship_nation,
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
                'ship_days': 0,
                'max_soldier_days': 0,
                'max_tank_days': 0,
                'max_aircraft_days': 0,
                'max_ship_days': 0,
                'max_soldier_nation': '',
                'max_tank_nation': '',
                'max_aircraft_nation': '',
                'max_ship_nation': '',
            }
    
    def calculate_military_purchase_limits(self, nation: Dict[str, Any]) -> Dict[str, int]:
        cities_data = nation.get('cities', [])
        num_cities = nation.get('num_cities', 0)
        total_barracks = 0
        total_factories = 0
        total_hangars = 0
        total_drydocks = 0
        if isinstance(cities_data, list) and len(cities_data) > 0:
            for city in cities_data:
                total_barracks += city.get('barracks', 0)
                total_factories += city.get('factory', 0)
                total_hangars += city.get('airforcebase', 0)
                total_drydocks += city.get('drydock', 0)
        else:
            avg_improvements_per_city = 2 
            total_barracks = num_cities * avg_improvements_per_city
            total_factories = num_cities * avg_improvements_per_city
            total_hangars = num_cities * avg_improvements_per_city
            total_drydocks = num_cities * avg_improvements_per_city
        soldier_daily_limit = total_barracks * 1000 
        tank_daily_limit = total_factories * 50    
        aircraft_daily_limit = total_hangars * 3   
        ship_daily_limit = total_drydocks * 1
        ground_research = nation.get('ground_research', 0)
        air_research = nation.get('air_research', 0)
        naval_research = nation.get('naval_research', 0)
        aircraft_daily_limit += air_research * 15 
        tank_daily_limit += ground_research * 250 
        soldier_daily_limit += ground_research * 3000  
        ship_daily_limit += naval_research * 5        
        if self.has_project(nation, 'Propaganda Bureau'):
            soldier_daily_limit = int(soldier_daily_limit * 1.10)
            tank_daily_limit = int(tank_daily_limit * 1.10)
            aircraft_daily_limit = int(aircraft_daily_limit * 1.10)
            ship_daily_limit = int(ship_daily_limit * 1.10)
        soldier_max_capacity = total_barracks * 3000 
        tank_max_capacity = total_factories * 250    
        aircraft_max_capacity = total_hangars * 15  
        ship_max_capacity = total_drydocks * 5    
        aircraft_max_capacity += air_research * 15 
        tank_max_capacity += ground_research * 250  
        soldier_max_capacity += ground_research * 3000  
        ship_max_capacity += naval_research * 5  
        ground_bonus = nation.get('ground_capacity', 0) or 0
        air_bonus = nation.get('air_capacity', 0) or 0
        naval_bonus = nation.get('naval_capacity', 0) or 0
        if not ground_bonus and not air_bonus and not naval_bonus:
            military_research = nation.get('military_research', {})
            ground_bonus = military_research.get('ground_capacity', 0) or 0
            air_bonus = military_research.get('air_capacity', 0) or 0
            naval_bonus = military_research.get('naval_capacity', 0) or 0
        soldier_max_capacity += ground_bonus
        tank_max_capacity += ground_bonus 
        aircraft_max_capacity += air_bonus
        ship_max_capacity += naval_bonus
        missile_limit = 0
        nuke_limit = 0
        if self.has_project(nation, 'Missile Launch Pad'):
            missile_limit = 2
            if self.has_project(nation, 'Space Program'):
                missile_limit = 3
        if self.has_project(nation, 'Nuclear Research Facility'):
            nuke_limit = 1
            if (self.has_project(nation, 'Nuclear Launch Facility') and 
                self.has_project(nation, 'Missile Launch Pad') and
                self.has_project(nation, 'Space Program')):
                nuke_limit = 2           
        return {
            'soldiers_daily': soldier_daily_limit,
            'tanks_daily': tank_daily_limit,
            'aircraft_daily': aircraft_daily_limit,
            'ships_daily': ship_daily_limit,
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
    
    def get_nation_specialty(self, nation: Dict[str, Any]) -> str:
        try:
            military_advantages = self.calculate_military_advantage(nation)
            advantages = military_advantages.get('advantages', [])
            ground_advantage = 'Ground Advantage' in advantages
            air_advantage = 'Air Advantage' in advantages
            naval_advantage = 'Naval Advantage' in advantages
            if ground_advantage or air_advantage or naval_advantage:
                advantage_count = sum([ground_advantage, air_advantage, naval_advantage])
                if advantage_count == 1:
                    if ground_advantage:
                        return "Ground"
                    elif air_advantage:
                        return "Air"
                    else:
                        return "Naval"
                if advantage_count == 3:
                    return "Generalist"
                military = nation.get('military', {})                
                if military:
                    soldiers = military.get('soldiers', 0)
                    tanks = military.get('tanks', 0)
                    aircraft = military.get('aircraft', 0)
                    ships = nation.get('ships', 0) 
                else:
                    soldiers = nation.get('soldiers', 0)
                    tanks = nation.get('tanks', 0)
                    aircraft = nation.get('aircraft', 0)
                    ships = nation.get('ships', 0)               
                total_units = soldiers + tanks + aircraft + ships
                if total_units > 0:
                    ground_units = soldiers + tanks
                    air_units = aircraft
                    naval_units = ships
                    if ground_advantage and air_advantage:
                        return "Ground" if ground_units >= air_units else "Air"
                    elif ground_advantage and naval_advantage:
                        return "Ground" if ground_units >= naval_units else "Naval"
                    elif air_advantage and naval_advantage:
                        return "Air" if air_units >= naval_units else "Naval"
                if ground_advantage:
                    return "Ground"
                elif air_advantage:
                    return "Air"
                else:
                    return "Naval"           
            military = nation.get('military', {})            
            if military:
                soldiers = military.get('soldiers', 0)
                tanks = military.get('tanks', 0)
                aircraft = military.get('aircraft', 0)
                ships = military.get('ships', 0)
            else:
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
        except Exception as e:
            self._log_error(f"Error getting nation specialty: {e}", e, "get_nation_specialty")
            return 'Generalist'
    
    def calculate_combat_score(self, nation: Dict[str, Any]) -> float:
        """Calculate a normalized combat score (1-100) based on infrastructure, military build quality, and projects.
        
        Lower infrastructure = higher score (more war-focused)
        Balanced 5/5/5/3 military build = higher score
        More strategic projects = higher score
        """
        try:
            # Get infrastructure stats
            infra_stats = self.calculate_infrastructure_stats(nation)
            avg_infra = infra_stats.get('average_infrastructure', 1000)
            
            # Get current military units
            soldiers = nation.get('soldiers', 0)
            tanks = nation.get('tanks', 0)
            aircraft = nation.get('aircraft', 0)
            ships = nation.get('ships', 0)
            missiles = nation.get('missiles', 0)
            nukes = nation.get('nukes', 0)
            
            # Get number of cities for normalization
            num_cities = nation.get('num_cities', 1)
            if num_cities == 0:
                num_cities = 1
            
            # Infrastructure score (lower infra = higher war focus = higher score)
            # Perfect score at 500 infra, decreasing as infra increases
            if avg_infra <= 500:
                infra_score = 100.0
            elif avg_infra >= 3000:
                infra_score = 1.0
            else:
                # Exponential decay: higher infra = much lower score
                infra_score = max(1.0, 100.0 * (1 - (avg_infra - 500) / 2500) ** 2)
            
            # Military build quality score (5/5/5/3 optimal build)
            # Calculate ratios per city
            soldiers_per_city = soldiers / num_cities
            tanks_per_city = tanks / num_cities
            aircraft_per_city = aircraft / num_cities
            ships_per_city = ships / num_cities
            
            # Optimal ratios for 5/5/5/3 build
            optimal_soldiers = 15000  # 5 barracks * 3000
            optimal_tanks = 1250    # 5 factories * 250
            optimal_aircraft = 75   # 5 hangars * 15
            optimal_ships = 15      # 3 drydocks * 5
            
            # Calculate build quality (0-100)
            soldier_quality = min(100.0, (soldiers_per_city / optimal_soldiers) * 100)
            tank_quality = min(100.0, (tanks_per_city / optimal_tanks) * 100)
            aircraft_quality = min(100.0, (aircraft_per_city / optimal_aircraft) * 100)
            ship_quality = min(100.0, (ships_per_city / optimal_ships) * 100)
            
            # Weighted average (aircraft and ships more important)
            build_score = (
                soldier_quality * 0.15 +
                tank_quality * 0.20 +
                aircraft_quality * 0.35 +
                ship_quality * 0.30
            )
            
            # Strategic projects score
            strategic_projects = [
                'Missile Launch Pad', 'Nuclear Research Facility', 'Iron Dome',
                'Vital Defense System', 'Military Research Center', 'Space Program',
                'Nuclear Launch Facility', 'Propaganda Bureau'
            ]
            
            project_count = 0
            for project in strategic_projects:
                if self.has_project(nation, project):
                    project_count += 1
            
            # Project score (each project adds points, with diminishing returns)
            if project_count == 0:
                project_score = 1.0
            else:
                # First few projects give more points, then diminishing returns
                base_project_score = project_count * 12.5  # 8 projects = 100 points max
                project_score = min(100.0, base_project_score)
            
            # Special weapons bonus (missiles and nukes)
            special_weapons_score = 0.0
            if missiles > 0:
                special_weapons_score += 10.0
            if nukes > 0:
                special_weapons_score += 15.0
            
            final_score = (
                infra_score * 0.30 +
                build_score * 0.40 +
                project_score * 0.25 +
                special_weapons_score * 0.05
            )
            
            # Ensure score is between 1-100
            return max(1.0, min(100.0, final_score))
            
        except Exception as e:
            self._log_error(f"Error calculating combat score: {e}", e, "calculate_combat_score")
            return 50.0  # Return middle score on error
    
    def _get_default_military_limits(self) -> Dict[str, int]:
        """Return default military purchase limits."""
        return {
            'soldiers': 250,
            'tanks': 25,
            'aircraft': 5,
            'ships': 2,
            'soldiers_max': 1000,
            'tanks_max': 100,
            'aircraft_max': 20,
            'ships_max': 10
        }
    
    def calculate_infrastructure_stats(self, nation: Dict[str, Any]) -> Dict[str, float]:
        cities_data = nation.get('cities', [])
        num_cities = nation.get('num_cities', 0)       
        if not isinstance(cities_data, list) or len(cities_data) == 0:
            estimated_avg_infra = max(50, (nation.get('score', 0) / num_cities) * 12) if num_cities > 0 else 50
            return {
                'average_infrastructure': estimated_avg_infra,
                'total_infrastructure': estimated_avg_infra * num_cities,
                'min_infrastructure': estimated_avg_infra * 0.8,  # Estimate range
                'max_infrastructure': estimated_avg_infra * 1.2,
                'infrastructure_range': estimated_avg_infra * 0.4,
                'infrastructure_tier': self._get_infrastructure_tier(estimated_avg_infra),
                'has_detailed_data': False
            }
        infrastructure_levels = []
        for city in cities_data:
            infra = city.get('infrastructure', 0)
            if infra > 0:
                infrastructure_levels.append(infra)       
        if not infrastructure_levels:
            estimated_avg_infra = max(50, (nation.get('score', 0) / num_cities) * 12) if num_cities > 0 else 50
            return {
                'average_infrastructure': estimated_avg_infra,
                'total_infrastructure': estimated_avg_infra * num_cities,
                'min_infrastructure': estimated_avg_infra,
                'max_infrastructure': estimated_avg_infra,
                'infrastructure_range': 0,
                'infrastructure_tier': self._get_infrastructure_tier(estimated_avg_infra),
                'has_detailed_data': False
            }       
        avg_infra = sum(infrastructure_levels) / len(infrastructure_levels)
        min_infra = min(infrastructure_levels)
        max_infra = max(infrastructure_levels)
        infra_range = max_infra - min_infra
        total_infra = sum(infrastructure_levels)        
        return {
            'average_infrastructure': avg_infra,
            'total_infrastructure': total_infra,
            'min_infrastructure': min_infra,
            'max_infrastructure': max_infra,
            'infrastructure_range': infra_range,
            'infrastructure_tier': self._get_infrastructure_tier(avg_infra),
            'has_detailed_data': True
        }

    def _get_infrastructure_tier(self, avg_infrastructure: float) -> str:
        if avg_infrastructure < 500:
            return "Perfect"  
        elif avg_infrastructure < 1000:
            return "Great"    
        elif avg_infrastructure < 1500:
            return "Good" 
        elif avg_infrastructure < 2000:
            return "Average"
        elif avg_infrastructure < 2500:
            return "Bad"  
        elif avg_infrastructure < 3000:
            return "Horrible"  
        else:
            return "Terrible" 
    
    def _calculate_infrastructure_compatibility(self, nation1: Dict[str, Any], nation2: Dict[str, Any]) -> float:
        infra1 = nation1.get('infrastructure_stats', {})
        infra2 = nation2.get('infrastructure_stats', {})       
        avg1 = infra1.get('average_infrastructure', 0)
        avg2 = infra2.get('average_infrastructure', 0)        
        if avg1 == 0 or avg2 == 0:
            return 0.5        
        higher = max(avg1, avg2)
        lower = min(avg1, avg2)
        percentage_diff = (higher - lower) / higher
        compatibility = max(0.0, 1.0 - (percentage_diff * 2))        
        return compatibility
    
    def calculate_building_ratios(self, nation: Dict[str, Any]) -> Dict[str, float]:
        cities_data = nation.get('cities', [])
        num_cities = nation.get('num_cities', len(cities_data))        
        if not cities_data or num_cities == 0:
            return {
                'barracks_ratio': 0.0,
                'factories_ratio': 0.0,
                'airforcebase_ratio': 0.0,
                'drydock_ratio': 0.0,
                'mmr_string': '0/0/0/0'
            }        
        total_barracks = 0
        total_factories = 0
        total_airforcebases = 0
        total_drydocks = 0        
        for city in cities_data:
            total_barracks += city.get('barracks', 0)
            total_factories += city.get('factory', 0)
            total_airforcebases += city.get('airforcebase', 0)
            total_drydocks += city.get('drydock', 0)
        barracks_ratio = total_barracks / num_cities
        factories_ratio = total_factories / num_cities
        airforcebase_ratio = total_airforcebases / num_cities
        drydock_ratio = total_drydocks / num_cities
        mmr_string = f"{barracks_ratio:.1f}/{factories_ratio:.1f}/{airforcebase_ratio:.1f}/{drydock_ratio:.1f}"       
        return {
            'barracks_ratio': barracks_ratio,
            'factories_ratio': factories_ratio,
            'airforcebase_ratio': airforcebase_ratio,
            'drydock_ratio': drydock_ratio,
            'mmr_string': mmr_string
        }

    def calculate_military_advantage(self, nation: Dict[str, Any]) -> Dict[str, Any]:
        purchase_limits = self.calculate_military_purchase_limits(nation)
        current_military = {
            'soldiers': nation.get('soldiers', 0),
            'tanks': nation.get('tanks', 0),
            'aircraft': nation.get('aircraft', 0),
            'ships': nation.get('ships', 0),
            'missiles': nation.get('missiles', 0),
            'nukes': nation.get('nukes', 0)
        }
        cities_list = nation.get('cities', [])
        if isinstance(cities_list, list):
            num_cities = nation.get('num_cities', len(cities_list))
        else:
            num_cities = nation.get('num_cities', 0)       
        max_soldiers_per_city = 5 * 3000
        max_tanks_per_city = 5 * 250   
        max_aircraft_per_city = 5 * 15  
        max_ships_per_city = 3 * 5        
        theoretical_max_soldiers = num_cities * max_soldiers_per_city
        theoretical_max_tanks = num_cities * max_tanks_per_city
        theoretical_max_aircraft = num_cities * max_aircraft_per_city
        theoretical_max_ships = num_cities * max_ships_per_city
        soldier_percentage = (current_military['soldiers'] / theoretical_max_soldiers * 100) if theoretical_max_soldiers > 0 else 0
        tank_percentage = (current_military['tanks'] / theoretical_max_tanks * 100) if theoretical_max_tanks > 0 else 0
        aircraft_percentage = (current_military['aircraft'] / theoretical_max_aircraft * 100) if theoretical_max_aircraft > 0 else 0
        ship_percentage = (current_military['ships'] / theoretical_max_ships * 100) if theoretical_max_ships > 0 else 0
        current_ground_score = current_military['soldiers'] + (current_military['tanks'] * 2)
        theoretical_max_ground_score = theoretical_max_soldiers + (theoretical_max_tanks * 2)
        ground_percentage = (current_ground_score / theoretical_max_ground_score * 100) if theoretical_max_ground_score > 0 else 0
        heavy_threshold_percentage = 80.0   
        is_heavy_ground = ground_percentage > heavy_threshold_percentage
        is_heavy_air = aircraft_percentage > heavy_threshold_percentage
        is_heavy_naval = ship_percentage > heavy_threshold_percentage
        cities_data = nation.get('cities', [])
        num_cities = len(cities_data) if cities_data else nation.get('num_cities', 0)      
        high_ground_build = False
        high_air_build = False
        high_naval_build = False        
        if num_cities > 0 and cities_data:
            total_barracks = sum(city.get('barracks', 0) for city in cities_data)
            total_factories = sum(city.get('factory', 0) for city in cities_data)
            total_airforcebases = sum(city.get('airforcebase', 0) for city in cities_data)
            total_drydocks = sum(city.get('drydock', 0) for city in cities_data)
            avg_barracks = total_barracks / num_cities
            avg_factories = total_factories / num_cities
            avg_airforcebases = total_airforcebases / num_cities
            avg_drydocks = total_drydocks / num_cities
            high_ground_build = avg_barracks >= 4.5 and avg_factories >= 4.5
            high_air_build = avg_airforcebases >= 4.5
            high_naval_build = avg_drydocks >= 2.5       
        high_ground_purchase = high_ground_build
        high_air_purchase = high_air_build
        high_naval_purchase = high_naval_build
        advantages = []
        has_ground_advantage = high_ground_purchase
        has_air_advantage = high_air_purchase
        has_naval_advantage = high_naval_purchase        
        if has_ground_advantage:
            advantages.append("Ground Advantage")
        if has_air_advantage:
            advantages.append("Air Advantage")
        if has_naval_advantage:
            advantages.append("Naval Advantage")
        can_missile = self.has_project(nation, 'Missile Launch Pad')
        can_nuke = self.has_project(nation, 'Nuclear Research Facility')        
        if can_missile:
            advantages.append("Missile Capable")
        if can_nuke:
            advantages.append("Nuclear Capable")
        
        nation_id = nation.get('nation_id') or nation.get('id', '')
        if nation_id and str(nation_id) == str(ARIES_NATION_ID):
            advantages.append("🪓 Psycho")
            has_ground_advantage = True
            has_air_advantage = True
            has_naval_advantage = True

        if nation_id and str(nation_id) == str(CARNAGE_NATION_ID):
            advantages.append("💀 Scary")
            has_ground_advantage = True
            has_air_advantage = True
            has_naval_advantage = True

        if nation_id and str(nation_id) == str(PRIMAL_NATION_ID):
            advantages.append("👑 Primal")
            has_ground_advantage = True
            has_air_advantage = True
            has_naval_advantage = True
        nation_score = nation.get('score', 0)
        min_attack_score = nation_score * 0.75 
        max_attack_score = nation_score * 2.5       
        return {
            'advantages': advantages,
            'purchase_limits': purchase_limits,
            'current_military': current_military,
            'can_missile': can_missile,
            'can_nuke': can_nuke,
            'has_ground_advantage': has_ground_advantage,
            'has_air_advantage': has_air_advantage,
            'has_naval_advantage': has_naval_advantage,
            'attack_range': {
                'min_score': min_attack_score,
                'max_score': max_attack_score,
                'nation_score': nation_score
            },
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
                'is_heavy_naval': is_heavy_naval,
                'high_ground_purchase': high_ground_purchase,
                'high_air_purchase': high_air_purchase,
                'high_naval_purchase': high_naval_purchase,
                'heavy_threshold_percentage': heavy_threshold_percentage,
                'is_psycho': "🪓 Psycho" in advantages,  # Flag to indicate ARIES user
                'is_scary': "💀 Scary" in advantages,  # Flag to indicate CARNAGE user
                'is_primal': "👑 Primal" in advantages  # Flag to indicate PRIMAL user
            }
        }
    
    def validate_attack_range(self, attacker_score: float, defender_score: float) -> bool:
        min_score = attacker_score * 0.75 
        max_score = attacker_score * 2.5  
        return min_score <= defender_score <= max_score
    
    def calculate_party_war_range(self, party_members: List[Dict[str, Any]]) -> Dict[str, float]:
        if not party_members:
            return {'min_range': 0, 'max_range': 0, 'avg_score': 0, 'overlapping_min': 0, 'overlapping_max': 0, 'has_overlap': False}
        scores = [member.get('score', 0) for member in party_members]
        individual_ranges = []
        for score in scores:
            min_attack = score * 0.75 
            max_attack = score * 2.5   
            individual_ranges.append((min_attack, max_attack))
        overlapping_min = max(range[0] for range in individual_ranges)
        overlapping_max = min(range[1] for range in individual_ranges)
        has_overlap = overlapping_min <= overlapping_max
        if not has_overlap:
            overlapping_min = 0
            overlapping_max = 0
        total_score = sum(scores)
        avg_score = total_score / len(party_members)
        theoretical_min = avg_score * 0.75
        theoretical_max = avg_score * 2.5        
        return {
            'min_range': theoretical_min,   
            'max_range': theoretical_max, 
            'avg_score': avg_score,      
            'total_score': total_score,       
            'overlapping_min': overlapping_min,
            'overlapping_max': overlapping_max, 
            'individual_ranges': individual_ranges, 
            'has_overlap': has_overlap     
        }

    def _has_ground_advantage(self, nation: Dict[str, Any]) -> bool:
        try:
            military_analysis = nation.get('military_analysis', {})
            return military_analysis.get('has_ground_advantage', False)
        except Exception:
            return False
    
    def _has_air_advantage(self, nation: Dict[str, Any]) -> bool:
        try:
            military_analysis = nation.get('military_analysis', {})
            return military_analysis.get('has_air_advantage', False)
        except Exception:
            return False
    
    def _has_naval_advantage(self, nation: Dict[str, Any]) -> bool:
        try:
            military_analysis = nation.get('military_analysis', {})
            return military_analysis.get('has_naval_advantage', False)
        except Exception:
            return False
    
    def _has_strategic_advantage(self, nation: Dict[str, Any]) -> bool:
        try:
            military_analysis = nation.get('military_analysis', {})
            return military_analysis.get('can_missile', False) or military_analysis.get('can_nuke', False)
        except Exception:
            return False
    
    def _calculate_strategic_value(self, nation: Dict[str, Any]) -> float:
        try:
            score = 0.0
            try:
                limits = calculate_military_purchase_limits(nation)
                daily_soldiers = limits.get('soldiers_daily', 0)
                daily_tanks = limits.get('tanks_daily', 0)
                daily_aircraft = limits.get('aircraft_daily', 0)
                daily_ships = limits.get('ships_daily', 0)
                max_soldiers = limits.get('soldiers_max', 0)
                max_tanks = limits.get('tanks_max', 0)
                max_aircraft = limits.get('aircraft_max', 0)
                max_ships = limits.get('ships_max', 0)
            except Exception as e:
                self.logger.warning(f"Error calculating military purchase limits: {str(e)}")
                daily_soldiers = daily_tanks = daily_aircraft = daily_ships = 0
                max_soldiers = max_tanks = max_aircraft = max_ships = 0
            try:
                daily_production_value = (
                    daily_aircraft * 4.0 +  
                    daily_tanks * 2.5 +      
                    daily_ships * 1.5 +       
                    daily_soldiers * 0.5  
                )
                if daily_production_value >= 200:    
                    score += 40
                elif daily_production_value >= 150: 
                    score += 32
                elif daily_production_value >= 100:  
                    score += 24
                elif daily_production_value >= 75: 
                    score += 16
                elif daily_production_value >= 50:  
                    score += 8
                else:                                 
                    score += 2
                    
            except Exception as e:
                self.logger.warning(f"Error calculating daily production capacity bonus: {str(e)}")
            try:
                cities_data = nation.get('cities', [])
                num_cities = len(cities_data) if cities_data else nation.get('num_cities', 0)                
                if num_cities > 0 and cities_data:
                    total_barracks = sum(city.get('barracks', 0) for city in cities_data)
                    total_factories = sum(city.get('factory', 0) for city in cities_data)
                    total_hangars = sum(city.get('airforcebase', 0) for city in cities_data) 
                    total_drydocks = sum(city.get('drydock', 0) for city in cities_data)
                    avg_barracks_per_city = total_barracks / num_cities
                    avg_factories_per_city = total_factories / num_cities
                    avg_hangars_per_city = total_hangars / num_cities
                    avg_drydocks_per_city = total_drydocks / num_cities
                    barracks_deviation = max(0, 5 - avg_barracks_per_city) / 5  
                    factories_deviation = max(0, 5 - avg_factories_per_city) / 5
                    hangars_deviation = max(0, 5 - avg_hangars_per_city) / 5
                    drydocks_deviation = max(0, 3 - avg_drydocks_per_city) / 3
                    weighted_deviation = (
                        hangars_deviation * 0.4 +   
                        factories_deviation * 0.3 + 
                        drydocks_deviation * 0.2 +     
                        barracks_deviation * 0.1       
                    )
                    build_quality_score = max(1, int(25 * (1 - weighted_deviation)))                   
                    self.logger.info(f"Build quality for {nation.get('nation_name', 'Unknown')}: "
                                   f"{avg_barracks_per_city:.1f}b/{avg_factories_per_city:.1f}f/"
                                   f"{avg_hangars_per_city:.1f}h/{avg_drydocks_per_city:.1f}d per city "
                                   f"(deviation: {weighted_deviation:.2f}, score: {build_quality_score})")                    
                else:
                    max_capacity_value = (
                        max_aircraft * 2.0 +       
                        max_tanks * 1.5 +    
                        max_ships * 1.0 +       
                        max_soldiers * 0.3         
                    )
                    if max_capacity_value >= 1000:    
                        build_quality_score = 25
                    elif max_capacity_value >= 750:  
                        build_quality_score = 20
                    elif max_capacity_value >= 500:  
                        build_quality_score = 15
                    elif max_capacity_value >= 300:    
                        build_quality_score = 10
                    elif max_capacity_value >= 150:   
                        build_quality_score = 5
                    else:                               
                        build_quality_score = 1               
                score += build_quality_score                   
            except Exception as e:
                self.logger.warning(f"Error calculating maximum capacity bonus: {str(e)}")
            try:
                nation_score = nation.get('score', 0)
                
                if nation_score <= 0:
                    score += 1  
                else:
                    min_war_range = nation_score * 0.75
                    max_war_range = nation_score * 2.5
                    optimal_min = 2000
                    optimal_max = 5000
                    overlap_start = max(min_war_range, optimal_min)
                    overlap_end = min(max_war_range, optimal_max)                   
                    if overlap_start < overlap_end:
                        overlap_length = overlap_end - overlap_start
                        optimal_range_length = optimal_max - optimal_min
                        overlap_percentage = overlap_length / optimal_range_length
                        if overlap_percentage >= 1.0:  
                            score += 20
                        elif overlap_percentage >= 0.75:
                            score += 18
                        elif overlap_percentage >= 0.5: 
                            score += 15
                        elif overlap_percentage >= 0.25:  
                            score += 12
                        elif overlap_percentage >= 0.1: 
                            score += 8
                        else: 
                            score += 4
                    else:
                        distance_to_optimal = 0
                        if max_war_range < optimal_min:  
                            distance_to_optimal = optimal_min - max_war_range
                        elif min_war_range > optimal_max:  
                            distance_to_optimal = min_war_range - optimal_max
                        if distance_to_optimal <= 500:
                            score += 6
                        elif distance_to_optimal <= 1000:  
                            score += 4
                        elif distance_to_optimal <= 2000: 
                            score += 2
                        else: 
                            score += 1                    
            except Exception as e:
                self.logger.warning(f"Error calculating war range optimization bonus: {str(e)}")
            try:
                military_analysis = nation.get('military_analysis', {})
                if military_analysis.get('can_nuke', False):
                    score += 10  
                elif military_analysis.get('can_missile', False):
                    score += 6  
            except Exception as e:
                self.logger.warning(f"Error calculating strategic weapons bonus: {str(e)}")
            try:
                advantages_count = 0
                if self._has_ground_advantage(nation):
                    advantages_count += 1
                if self._has_air_advantage(nation):
                    advantages_count += 1
                if self._has_naval_advantage(nation):
                    advantages_count += 1
                if self._has_strategic_advantage(nation):
                    advantages_count += 1
                score += min(advantages_count * 3.0, 12)
            except Exception as e:
                self.logger.warning(f"Error calculating military advantage diversity bonus: {str(e)}")            
            return min(score, 100.0)            
        except Exception as e:
            self._log_error(f"Error in _calculate_strategic_value: {str(e)}", e, "_calculate_strategic_value")
            return 0.0

calculator = AllianceCalculator()

def get_active_nations(nations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return calculator.get_active_nations(nations)

def calculate_nation_statistics(nations: List[Dict[str, Any]]) -> Dict[str, Any]:
    return calculator.calculate_nation_statistics(nations)

def calculate_alliance_statistics(nations: List[Dict[str, Any]]) -> Dict[str, Any]:
    return calculator.calculate_alliance_statistics(nations)

def calculate_full_mill_data(nations: List[Dict[str, Any]]) -> Dict[str, Any]:
    return calculator.calculate_full_mill_data(nations)

def calculate_military_purchase_limits(nation: Dict[str, Any]) -> Dict[str, int]:
    return calculator.calculate_military_purchase_limits(nation)

def get_nation_specialty(nation: Dict[str, Any]) -> str:
    return calculator.get_nation_specialty(nation)

def calculate_combat_score(nation: Dict[str, Any]) -> float:
    return calculator.calculate_combat_score(nation)

def has_project(nation: Dict[str, Any], project_name: str) -> bool:
    return calculator.has_project(nation, project_name)

def calculate_infrastructure_stats(nation: Dict[str, Any]) -> Dict[str, float]:
    return calculator.calculate_infrastructure_stats(nation)

def calculate_military_advantage(nation: Dict[str, Any]) -> Dict[str, Any]:
    return calculator.calculate_military_advantage(nation)

def validate_attack_range(attacker_score: float, defender_score: float) -> bool:
    return calculator.validate_attack_range(attacker_score, defender_score)

def calculate_party_war_range(party_members: List[Dict[str, Any]]) -> Dict[str, float]:
    return calculator.calculate_party_war_range(party_members)

def calculate_strategic_value(nation: Dict[str, Any]) -> float:
    return calculator._calculate_strategic_value(nation)

async def calculate_improvements_data(nations: List[Dict[str, Any]]) -> Dict[str, Any]:
    return await calculator.calculate_improvements_data(nations)

def calculate_building_ratios(nation: Dict[str, Any]) -> str:
    return calculator.calculate_building_ratios(nation)