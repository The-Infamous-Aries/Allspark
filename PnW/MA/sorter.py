import logging
from typing import List, Dict, Optional, Any
import traceback

# Avoid circular imports by using lazy imports
# Define a placeholder class that will be replaced at runtime
class AllianceCalculator:
    def get_active_nations(self, nations):
        return [n for n in nations if not n.get('is_applicant', False) and not n.get('vacation_mode', False)]
    
    def calculate_party_war_range(self, party):
        scores = [n.get('score', 0) for n in party]
        if not scores:
            return {'has_overlap': False}                
        min_score = min(scores)
        max_score = max(scores)
        return {
            'has_overlap': True,
            'overlapping_min': min_score * 0.75,
            'overlapping_max': max_score * 1.25
        }
    
    def _get_infrastructure_tier(self, infra_avg):
        if infra_avg >= 2000:
            return 'high'
        elif infra_avg >= 1000:
            return 'medium'
        else:
            return 'low'
    
    def get_nation_specialty(self, nation):
        return nation.get('speciality', 'Generalist')
    
    def has_project(self, nation, project_name):
        return False

class BlitzPartySorter:  
    def __init__(self, calculator = None, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Use lazy loading to avoid circular imports
        if calculator is None:
            # Only import AllianceCalculator when needed
            self.calculator = AllianceCalculator()
        else:
            self.calculator = calculator
    
    def _safe_get(self, data: dict, key: str, default: Any = None, expected_type: type = None) -> Any:
        try:
            value = data.get(key, default)
            if expected_type and value is not None:
                if isinstance(expected_type, tuple):
                    if not isinstance(value, expected_type):
                        return default
                else:
                    if not isinstance(value, expected_type):
                        if expected_type in (int, float) and isinstance(value, (int, float)):
                            return expected_type(value)
                        return default
            return value
        except Exception as e:
            self.logger.error(f"Error accessing key '{key}' from data: {str(e)}")
            return default
    
    def _log_error(self, error_msg: str, exception: Exception = None, context: str = ""):
        if exception:
            self.logger.error(f"{error_msg}: {str(exception)}")
            self.logger.debug(f"Exception details: {traceback.format_exc()}")
        else:
            self.logger.error(error_msg)       
        if context:
            self.logger.debug(f"Context: {context}")
    
    def get_active_nations(self, nations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        try:
            if not nations:
                return []

            active_nations = []
            for nation in nations:
                if not isinstance(nation, dict):
                    continue
                
                vacation_turns = self._safe_get(nation, 'vacation_mode_turns', 0, int)
                if vacation_turns > 0:
                    continue
                
                alliance_position = self._safe_get(nation, 'alliance_position', '', str)
                if alliance_position.upper() == 'APPLICANT':
                    continue
                
                # Check 14+ days inactive
                last_active_str = self._safe_get(nation, 'last_active', '', str)
                if last_active_str:
                    try:
                        from datetime import datetime, timezone, timedelta
                        now = datetime.now(timezone.utc)
                        fourteen_days_ago = now - timedelta(days=14)
                        if last_active_str.endswith('+00:00'):
                            last_active = datetime.fromisoformat(last_active_str.replace('+00:00', '')).replace(tzinfo=timezone.utc)
                        else:
                            last_active = datetime.fromisoformat(last_active_str).replace(tzinfo=timezone.utc)
                        if last_active < fourteen_days_ago:
                            continue
                    except (ValueError, TypeError):
                        # If we can't parse last_active, skip the nation to be safe
                        continue
                else:
                    # If last_active is missing or empty, exclude the nation to be safe
                    continue
                
                active_nations.append(nation)
            
            return active_nations
        except Exception as e:
            self._log_error("Error filtering active nations", e)
            return []
    
    def _calculate_infrastructure_average(self, nation: Dict[str, Any]) -> float:
        try:
            cities = nation.get('cities', [])
            if not cities:
                return 0.0             
            total_infra = sum(city.get('infrastructure', 0) for city in cities)
            num_cities = len(cities)            
            if num_cities <= 0:
                return 0.0           
            return total_infra / num_cities           
        except Exception as e:
            self._log_error("Error calculating infrastructure average", e, f"nation: {nation.get('nation_name', 'Unknown')}")
            return 0.0
    
    def _check_war_range_compatibility(self, nation1: Dict[str, Any], nation2: Dict[str, Any]) -> bool:
        """Check if two nations can war each other based on score range (-25% to 150%)"""
        try:
            score1 = self._safe_get(nation1, 'score', 0, (int, float))
            score2 = self._safe_get(nation2, 'score', 0, (int, float))
            
            if score1 <= 0 or score2 <= 0:
                return False
            
            # War range: -25% to +150% of their score
            min_range = score1 * 0.75  # -25%
            max_range = score1 * 2.5   # +150%
            
            return min_range <= score2 <= max_range
            
        except Exception as e:
            self._log_error("Error checking war range compatibility", e)
            return False
    
    def sort_nations_by_infrastructure_and_war_range(self, nations: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Sort nations by infrastructure average and group by war range compatibility.
        Returns a list of parties (each party is a list of nations).
        """
        try:
            if not nations:
                return []
            
            active_nations = self.get_active_nations(nations)
            if not active_nations:
                return []
            
            # Calculate infrastructure averages and add metadata
            for nation in active_nations:
                infra_avg = self._calculate_infrastructure_average(nation)
                nation['infra_average'] = infra_avg
            
            # Sort by infrastructure average (descending)
            active_nations.sort(key=lambda x: x.get('infra_average', 0), reverse=True)
            
            # Group into parties based on war range compatibility
            parties = []
            used_nations = set()
            
            for nation in active_nations:
                # Handle both 'nation_id' and 'id' key names
                nation_id = nation.get('nation_id') or nation.get('id')
                if not nation_id or nation_id in used_nations:
                    continue
                
                # Try to find compatible nations for a party
                party = [nation]
                used_nations.add(nation_id)
                
                # Look for compatible nations (within war range)
                for potential_nation in active_nations:
                    # Handle both 'nation_id' and 'id' key names
                    potential_id = potential_nation.get('nation_id') or potential_nation.get('id')
                    if not potential_id or potential_id in used_nations:
                        continue
                    
                    # Check if this nation is compatible with all current party members
                    is_compatible = True
                    for party_member in party:
                        if not self._check_war_range_compatibility(party_member, potential_nation):
                            is_compatible = False
                            break
                    
                    # Also check if adding this nation would create a party with overlapping war range
                    if is_compatible and len(party) < 3:  # Max party size of 3
                        # Test if the party would have overlapping war range
                        test_party = party + [potential_nation]
                        war_range_info = self.calculator.calculate_party_war_range(test_party)
                        if war_range_info and war_range_info.get('has_overlap', False):
                            party.append(potential_nation)
                            used_nations.add(potential_id)
                
                if len(party) >= 2:  # Only keep parties of 2 or 3
                    parties.append(party)
            
            return parties
            
        except Exception as e:
            self._log_error("Error sorting nations by infrastructure and war range", e)
            return []
    
    def get_war_range_info(self, party: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get war range information for a party"""
        try:
            if not party:
                return {}
            
            scores = [n.get('score', 0) for n in party]
            if not scores:
                return {}
            
            min_score = min(scores)
            max_score = max(scores)
            
            # Calculate war range overlap
            war_range_data = self.calculator.calculate_party_war_range(party)
            
            return {
                'min_score': min_score,
                'max_score': max_score,
                'score_range': max_score - min_score,
                'overlapping_min': war_range_data.get('overlapping_min', 0) if war_range_data else 0,
                'overlapping_max': war_range_data.get('overlapping_max', 0) if war_range_data else 0,
                'has_overlap': war_range_data.get('has_overlap', False) if war_range_data else False
            }
            
        except Exception as e:
            self._log_error("Error getting war range info", e)
            return {}
    
    def get_military_advantages_display(self, party: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get military advantages for display only (not used for sorting)"""
        try:
            if not party:
                return {}
            
            advantages = {'ground': 0, 'air': 0, 'naval': 0}
            for nation in party:
                # Try to get military advantages from calculator if available
                try:
                    if hasattr(self.calculator, 'get_military_advantages'):
                        nation_advantages = self.calculator.get_military_advantages(nation)
                        if isinstance(nation_advantages, dict):
                            for key in advantages:
                                if key in nation_advantages:
                                    advantages[key] += nation_advantages[key]
                except:
                    # Fallback to basic calculation
                    soldiers = self._safe_get(nation, 'soldiers', 0, int)
                    tanks = self._safe_get(nation, 'tanks', 0, int)
                    aircraft = self._safe_get(nation, 'aircraft', 0, int)
                    ships = self._safe_get(nation, 'ships', 0, int)
                    
                    advantages['ground'] += soldiers + (tanks * 10)
                    advantages['air'] += aircraft * 15
                    advantages['naval'] += ships * 20
            
            return advantages
            
        except Exception as e:
            self._log_error("Error getting military advantages display", e)
            return {}
    
    def create_balanced_parties(self, nations: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Create balanced parties from a list of nations.
        
        Args:
            nations: List of nation dictionaries (can be from multiple alliances)
            
        Returns:
            List of balanced parties (each party is a list of nations)
        """
        try:
            if not nations:
                self.logger.warning("create_balanced_parties: No nations provided")
                return []
            
            # Filter for active nations
            active_nations = self.get_active_nations(nations)
            if not active_nations:
                self.logger.warning("create_balanced_parties: No active nations found")
                return []
            
            # Sort nations by infrastructure and war range compatibility
            sorted_nations = self.sort_nations_by_infrastructure_and_war_range(active_nations)
            
            # Create balanced parties
            parties = self._distribute_nations_to_parties(sorted_nations)
            
            self.logger.info(f"create_balanced_parties: Created {len(parties)} parties from {len(active_nations)} active nations")
            return parties
            
        except Exception as e:
            self._log_error("Error creating balanced parties", e, "create_balanced_parties")
            return []

    def create_balanced_parties_multi_alliance(self, alliance_data: Dict[str, List[Dict[str, Any]]], selected_alliances: List[str] = None) -> List[List[Dict[str, Any]]]:
        """
        Create balanced parties from multiple alliance data efficiently.
        
        Args:
            alliance_data: Dictionary mapping alliance keys to nation lists
            selected_alliances: List of alliance keys to include (if None, uses all)
            
        Returns:
            List of balanced parties (each party is a list of nations)
        """
        try:
            if not alliance_data:
                self.logger.warning("create_balanced_parties_multi_alliance: No alliance data provided")
                return []
            
            # Combine nations from selected alliances
            combined_nations = self._combine_alliance_nations(alliance_data, selected_alliances)
            
            if not combined_nations:
                self.logger.warning("create_balanced_parties_multi_alliance: No nations found in selected alliances")
                return []
            
            # Use existing party creation logic
            return self.create_balanced_parties(combined_nations)
            
        except Exception as e:
            self._log_error("Error creating multi-alliance balanced parties", e, "create_balanced_parties_multi_alliance")
            return []

    def _combine_alliance_nations(self, alliance_data: Dict[str, List[Dict[str, Any]]], selected_alliances: List[str] = None) -> List[Dict[str, Any]]:
        """
        Efficiently combine nations from multiple alliances, removing duplicates.
        
        Args:
            alliance_data: Dictionary mapping alliance keys to nation lists
            selected_alliances: List of alliance keys to include (if None, uses all)
            
        Returns:
            Combined list of unique nations
        """
        try:
            combined_nations = []
            seen_nation_ids = set()
            
            # Determine which alliances to process
            alliances_to_process = selected_alliances if selected_alliances else list(alliance_data.keys())
            
            for alliance_key in alliances_to_process:
                nations = alliance_data.get(alliance_key, [])
                if not nations:
                    continue
                
                # Add nations, avoiding duplicates by nation_id
                for nation in nations:
                    nation_id = self._safe_get(nation, 'nation_id') or self._safe_get(nation, 'id')
                    if nation_id and nation_id not in seen_nation_ids:
                        seen_nation_ids.add(nation_id)
                        # Add alliance source info for tracking
                        nation_copy = nation.copy()
                        nation_copy['_source_alliance'] = alliance_key
                        combined_nations.append(nation_copy)
            
            self.logger.info(f"_combine_alliance_nations: Combined {len(combined_nations)} unique nations from {len(alliances_to_process)} alliances")
            return combined_nations
            
        except Exception as e:
            self._log_error("Error combining alliance nations", e, "_combine_alliance_nations")
            return []

    def _distribute_nations_to_parties(self, sorted_nations: List[List[Dict[str, Any]]]) -> List[List[Dict[str, Any]]]:
        """
        Distribute sorted nations into balanced parties.
        
        Args:
            sorted_nations: List of parties from sort_nations_by_infrastructure_and_war_range
            
        Returns:
            List of balanced parties
        """
        try:
            # The sorting function already returns parties, so we just return them
            return sorted_nations
            
        except Exception as e:
            self._log_error("Error distributing nations to parties", e, "_distribute_nations_to_parties")
            return []
    
    def get_party_analysis(self, party: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get basic party analysis without complex scoring"""
        try:
            if not party:
                return {}
            
            # Basic stats
            total_score = sum(n.get('score', 0) for n in party)
            avg_score = total_score / len(party) if party else 0
            avg_infra = sum(n.get('infra_average', 0) for n in party) / len(party) if party else 0
            
            # War range info
            war_range_info = self.get_war_range_info(party)
            
            # Military advantages (for display only)
            military_advantages = self.get_military_advantages_display(party)
            
            # Simple quality assessment based on war range overlap
            if war_range_info.get('has_overlap', False):
                score_range = war_range_info.get('score_range', 0)
                if score_range <= avg_score * 0.3:  # Good overlap
                    quality = 'Excellent'
                elif score_range <= avg_score * 0.6:  # Decent overlap
                    quality = 'Good'
                else:  # Some overlap
                    quality = 'Fair'
            else:
                quality = 'Poor'
            
            return {
                'total_score': total_score,
                'avg_score': avg_score,
                'avg_infra': avg_infra,
                'member_count': len(party),
                'war_range_info': war_range_info,
                'military_advantages': military_advantages,
                'quality': quality
            }
            
        except Exception as e:
            self._log_error("Error getting party analysis", e)
            return {}