import discord
from discord.ext import commands
from datetime import datetime
from typing import Dict, List, Any, Optional
import asyncio
import traceback
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)

# Set defaults for removed imports - no circular dependencies
PNWKIT_AVAILABLE = False
PNWKIT_ERROR = "PNWKit not available"
BLITZ_IMPORT_SUCCESS = True  # Will use cog lookup instead
BLITZ_IMPORT_ERROR = None


class PartiesView(discord.ui.View):
    """View for displaying saved blitz parties with navigation and management features."""
    
    def __init__(self, author_id: int, bot: commands.Bot, blitz_cog: Any, saved_parties_data: List[Dict] = None):
        super().__init__(timeout=300)  # 5 minute timeout
        self.author_id = author_id
        self.bot = bot
        self.blitz_cog = blitz_cog
        self.saved_parties_data = saved_parties_data or []
        self.current_party_index = 0
        self.current_parties = []
        self.error_count = 0
        self.max_errors = 5
        
        # Validate inputs
        if not self._validate_inputs():
            return
        
        # Load the most recent parties if no data provided
        if not self.saved_parties_data:
            asyncio.create_task(self._load_saved_parties())
        else:
            try:
                self.current_parties = self._convert_saved_data_to_display_format(self.saved_parties_data)
            except Exception as e:
                logger.error(f"Error converting saved data to display format: {e}")
                self.current_parties = []
                self._log_error("Data conversion error", e)
    
    def _validate_inputs(self) -> bool:
        """Validate constructor inputs and log any issues."""
        try:
            if not isinstance(self.author_id, int) or self.author_id <= 0:
                logger.error(f"Invalid author_id: {self.author_id}")
                self.current_parties = []
                return False
            
            if not self.bot:
                logger.error("Bot instance is None")
                self.current_parties = []
                return False
            
            if not self.blitz_cog:
                logger.warning("blitz_cog is None in PartiesView constructor")
                self.current_parties = []
                return False
            
            if not hasattr(self.blitz_cog, 'get_saved_blitz_parties'):
                logger.error("blitz_cog missing get_saved_blitz_parties method")
                self.current_parties = []
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating inputs: {e}")
            self.current_parties = []
            return False
    
    def _log_error(self, context: str, error: Exception):
        """Log errors with context and increment error counter."""
        self.error_count += 1
        logger.error(f"PartiesView Error ({context}): {error}")
        logger.error(f"Error count: {self.error_count}/{self.max_errors}")
        
        if self.error_count >= self.max_errors:
            logger.critical("Maximum error count reached in PartiesView")
    
    async def _load_saved_parties(self):
        """Load saved parties directly from JSON file with optimized performance."""
        try:
            # Import UserDataManager for direct access
            from Systems.user_data_manager import UserDataManager
            
            logger.info("Loading saved parties directly from JSON file")
            user_data_manager = UserDataManager()
            
            # Get data directly from UserDataManager with optimized caching
            saved_data = await user_data_manager.get_json_data('blitz_parties', {})
            
            if not saved_data:
                logger.warning("No saved party data found in blitz_parties.json")
                self.current_parties = []
                return
            
            # Handle new data structure - single object with parties key
            if isinstance(saved_data, dict):
                if 'parties' not in saved_data:
                    logger.error("Missing 'parties' key in saved data structure")
                    logger.debug(f"Available keys in saved_data: {list(saved_data.keys())}")
                    self.current_parties = []
                    return
                
                parties_data = saved_data['parties']
                if not isinstance(parties_data, list):
                    logger.error(f"Invalid parties data format: expected list, got {type(parties_data)}")
                    self.current_parties = []
                    return
                
                logger.info(f"Successfully loaded {len(parties_data)} parties from optimized JSON access")
                self.current_parties = self._convert_saved_data_to_display_format(parties_data)
                return
            
            # Handle legacy data structure - list of entries (fallback)
            elif isinstance(saved_data, list):
                if len(saved_data) == 0:
                    logger.warning("Saved parties list is empty")
                    self.current_parties = []
                    return
                
                # Get the latest parties entry for legacy format
                latest_parties = saved_data[-1]
                if not latest_parties or not isinstance(latest_parties, dict):
                    logger.error(f"Invalid latest parties format: expected dict, got {type(latest_parties)}")
                    self.current_parties = []
                    return
                
                if 'parties' not in latest_parties:
                    logger.error("Missing 'parties' key in latest parties data")
                    logger.debug(f"Available keys in latest_parties: {list(latest_parties.keys())}")
                    self.current_parties = []
                    return
                
                parties_data = latest_parties['parties']
                if not isinstance(parties_data, list):
                    logger.error(f"Invalid parties data format: expected list, got {type(parties_data)}")
                    self.current_parties = []
                    return
                
                logger.info(f"Successfully loaded {len(parties_data)} parties from legacy format")
                self.current_parties = self._convert_saved_data_to_display_format(parties_data)
                return
            
            else:
                logger.error(f"Invalid saved data format: expected dict or list, got {type(saved_data)}")
                self.current_parties = []
                return
            
        except asyncio.CancelledError:
            logger.warning("Party loading was cancelled")
            self.current_parties = []
            
        except Exception as e:
            self._log_error("Loading saved parties with optimized access", e)
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            self.current_parties = []
    
    def _validate_blitz_cog(self) -> bool:
        """Validate that blitz_cog is properly configured."""
        try:
            if not self.blitz_cog:
                logger.error("Blitz cog is None")
                return False
            
            if not hasattr(self.blitz_cog, 'get_saved_blitz_parties'):
                logger.error("Blitz cog missing get_saved_blitz_parties method")
                return False
            
            if not callable(self.blitz_cog.get_saved_blitz_parties):
                logger.error("get_saved_blitz_parties is not callable")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating blitz_cog: {e}")
            return False
    
    def _convert_saved_data_to_display_format(self, saved_parties: List[Dict]) -> List[Dict]:
        """Convert saved party data to display format with error handling."""
        display_parties = []
        conversion_errors = 0
        
        try:
            if not isinstance(saved_parties, list):
                logger.error(f"Invalid saved_parties format: expected list, got {type(saved_parties)}")
                return []
            
            for party_index, party in enumerate(saved_parties):
                try:
                    if not isinstance(party, dict):
                        logger.warning(f"Party at index {party_index} is not a dict: {type(party)}")
                        conversion_errors += 1
                        continue
                    
                    # Convert members to display format with validation
                    member_data_display = []
                    members = party.get('members', [])
                    
                    if not isinstance(members, list):
                        logger.warning(f"Members for party '{party.get('party_name', 'Unknown')}' is not a list: {type(members)}")
                        members = []
                    
                    for member_index, member in enumerate(members):
                        try:
                            if not isinstance(member, dict):
                                logger.warning(f"Member at index {member_index} in party '{party.get('party_name', 'Unknown')}' is not a dict: {type(member)}")
                                continue
                            
                            member_display = {
                                'nation_name': str(member.get('nation_name', 'Unknown')),
                                'leader_name': str(member.get('leader_name', 'Unknown')),
                                'score': self._safe_get_numeric(member, 'score', 0),
                                'advantages': ', '.join(self._safe_get_list(member, 'military_advantages', ['Standard'])),
                                'strategic': '✅' if (self._safe_get_bool(member, 'can_missile', False) or self._safe_get_bool(member, 'can_nuke', False)) else '❌'
                            }
                            member_data_display.append(member_display)
                            
                        except Exception as e:
                            logger.warning(f"Error converting member {member_index} in party '{party.get('party_name', 'Unknown')}': {e}")
                            conversion_errors += 1
                            continue
                    
                    # Convert party to display format with validation
                    party_display = {
                        'party_name': str(party.get('party_name', 'Unknown Party')),
                        'members': member_data_display,
                        'total_score': self._safe_get_numeric(party.get('party_stats', {}), 'total_score', 0),
                        'strategic_count': self._safe_get_numeric(party.get('party_stats', {}), 'strategic_count', 0),
                        'member_count': self._safe_get_numeric(party.get('party_stats', {}), 'member_count', 0),
                        'attack_range': self._safe_get_dict(party, 'attack_range', {}),
                        'military_advantages': self._safe_get_dict(party, 'military_advantages', {}),
                        'war_range_data': self._safe_get_dict(party, 'war_range_data', {})
                    }
                    display_parties.append(party_display)
                    
                except Exception as e:
                    logger.error(f"Error converting party at index {party_index}: {e}")
                    conversion_errors += 1
                    continue
            
            logger.info(f"Successfully converted {len(display_parties)} parties with {conversion_errors} conversion errors")
            return display_parties
            
        except Exception as e:
            logger.error(f"Critical error in _convert_saved_data_to_display_format: {e}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            return []
    
    def _safe_get_numeric(self, data: dict, key: str, default: float = 0) -> float:
        """Safely get a numeric value from a dictionary."""
        try:
            value = data.get(key, default)
            if isinstance(value, (int, float)):
                return float(value)
            else:
                return float(default)
        except (ValueError, TypeError):
            return float(default)
    
    def _safe_get_bool(self, data: dict, key: str, default: bool = False) -> bool:
        """Safely get a boolean value from a dictionary."""
        try:
            value = data.get(key, default)
            if isinstance(value, bool):
                return value
            else:
                return bool(default)
        except:
            return bool(default)
    
    def _safe_get_list(self, data: dict, key: str, default: list = None) -> list:
        """Safely get a list from a dictionary."""
        if default is None:
            default = []
        try:
            value = data.get(key, default)
            if isinstance(value, list):
                return value
            else:
                return list(default)
        except:
            return list(default)
    
    def _safe_get_dict(self, data: dict, key: str, default: dict = None) -> dict:
        """Safely get a dictionary from a dictionary."""
        if default is None:
            default = {}
        try:
            value = data.get(key, default)
            if isinstance(value, dict):
                return value
            else:
                return dict(default)
        except:
            return dict(default)
    
    def _calculate_party_optimization_score(self, party: dict) -> float:
        """Calculate overall optimization score for a party (0-100)."""
        try:
            if not isinstance(party, dict):
                return 0.0
            
            score = 0.0
            
            # War range efficiency (40% of total score)
            war_range_efficiency = self._calculate_war_range_efficiency(party)
            score += war_range_efficiency * 0.4
            
            # Military balance (30% of total score)
            military_balance = self._calculate_military_balance(party)
            score += military_balance * 0.3
            
            # Strategic distribution (20% of total score)
            strategic_distribution = self._calculate_strategic_distribution(party)
            score += strategic_distribution * 0.2
            
            # Member count optimization (10% of total score)
            member_count = self._safe_get_numeric(party.get('party_stats', {}), 'member_count', 0)
            if member_count == 3:  # Optimal party size
                score += 10.0
            elif member_count == 2:
                score += 7.0
            elif member_count == 1:
                score += 3.0
            
            return min(100.0, max(0.0, score))
            
        except Exception as e:
            logger.warning(f"Error calculating party optimization score: {e}")
            return 0.0
    
    def _calculate_war_range_efficiency(self, party: dict) -> float:
        """Calculate war range efficiency (0-100)."""
        try:
            attack_range = self._safe_get_dict(party, 'attack_range', {})
            if not attack_range:
                return 0.0
            
            min_attackable = self._safe_get_numeric(attack_range, 'min_attackable', 0)
            max_attackable = self._safe_get_numeric(attack_range, 'max_attackable', 0)
            
            if min_attackable <= 0 or max_attackable <= 0 or min_attackable >= max_attackable:
                return 0.0
            
            # Calculate range span efficiency
            range_span = max_attackable - min_attackable
            avg_range = (min_attackable + max_attackable) / 2
            
            if avg_range <= 0:
                return 0.0
            
            # Smaller range span relative to average is better
            efficiency_ratio = 1 - (range_span / avg_range)
            efficiency_percentage = max(0.0, min(100.0, efficiency_ratio * 100))
            
            return efficiency_percentage
            
        except Exception as e:
            logger.warning(f"Error calculating war range efficiency: {e}")
            return 0.0
    
    def _calculate_military_balance(self, party: dict) -> float:
        """Calculate military balance across different advantages (0-100)."""
        try:
            military_advantages = self._safe_get_dict(party, 'military_advantages', {})
            if not military_advantages:
                return 50.0  # Neutral score if no data
            
            ground_adv = self._safe_get_numeric(military_advantages, 'ground', 0)
            air_adv = self._safe_get_numeric(military_advantages, 'air', 0)
            naval_adv = self._safe_get_numeric(military_advantages, 'naval', 0)
            
            total_advantages = ground_adv + air_adv + naval_adv
            if total_advantages <= 0:
                return 0.0
            
            # Calculate balance - perfect balance would be 33.33% each
            ground_ratio = ground_adv / total_advantages
            air_ratio = air_adv / total_advantages
            naval_ratio = naval_adv / total_advantages
            
            # Calculate deviation from perfect balance (33.33% each)
            ideal_ratio = 1/3
            ground_deviation = abs(ground_ratio - ideal_ratio)
            air_deviation = abs(air_ratio - ideal_ratio)
            naval_deviation = abs(naval_ratio - ideal_ratio)
            
            # Average deviation (lower is better)
            avg_deviation = (ground_deviation + air_deviation + naval_deviation) / 3
            
            # Convert to balance score (higher is better)
            balance_score = max(0.0, min(100.0, (1 - avg_deviation * 3) * 100))
            
            return balance_score
            
        except Exception as e:
            logger.warning(f"Error calculating military balance: {e}")
            return 50.0
    
    def _calculate_strategic_distribution(self, party: dict) -> float:
        """Calculate strategic unit distribution efficiency (0-100)."""
        try:
            members = self._safe_get_list(party, 'members', [])
            if not members:
                return 0.0
            
            strategic_count = 0
            total_members = len(members)
            
            for member in members:
                if not isinstance(member, dict):
                    continue
                
                can_missile = self._safe_get_bool(member, 'can_missile', False)
                can_nuke = self._safe_get_bool(member, 'can_nuke', False)
                
                if can_missile or can_nuke:
                    strategic_count += 1
            
            if total_members == 0:
                return 0.0
            
            # Calculate strategic ratio
            strategic_ratio = strategic_count / total_members
            
            # Optimal strategic distribution: 1-2 strategic units per 3-member party
            if total_members == 3:
                if strategic_count == 1 or strategic_count == 2:
                    return 100.0  # Optimal
                elif strategic_count == 3:
                    return 80.0   # Good but overkill
                else:
                    return 30.0   # No strategic units
            elif total_members == 2:
                if strategic_count == 1:
                    return 100.0  # Optimal
                elif strategic_count == 2:
                    return 70.0   # Good
                else:
                    return 40.0   # No strategic units
            else:
                # For other party sizes, aim for 33-66% strategic ratio
                if 0.33 <= strategic_ratio <= 0.66:
                    return 100.0
                elif strategic_ratio > 0.66:
                    return 70.0
                else:
                    return strategic_ratio * 100
            
        except Exception as e:
            logger.warning(f"Error calculating strategic distribution: {e}")
            return 50.0
    
    def _get_optimization_status(self, score: float) -> dict:
        """Get optimization status emoji and text based on score."""
        try:
            if score >= 90:
                return {"emoji": "🟢", "text": "Excellent"}
            elif score >= 80:
                return {"emoji": "🔵", "text": "Very Good"}
            elif score >= 70:
                return {"emoji": "🟡", "text": "Good"}
            elif score >= 60:
                return {"emoji": "🟠", "text": "Fair"}
            elif score >= 40:
                return {"emoji": "🔴", "text": "Poor"}
            else:
                return {"emoji": "⚫", "text": "Very Poor"}
        except:
            return {"emoji": "❓", "text": "Unknown"}
    
    async def _validate_party_members(self, members: list) -> list:
        """Validate party members using cached alliance data from alliance_cache.json."""
        validation_results = []
        
        try:
            # Import UserDataManager for cache access
            from Systems.user_data_manager import UserDataManager
            
            # Get cached alliance data
            user_data_manager = UserDataManager()
            alliance_cache = await user_data_manager.get_json_data('alliance_cache', {})
            
            if not alliance_cache:
                logger.warning("No alliance cache data available for validation")
                # Return default results indicating no cache available
                for member in members:
                    validation_results.append({
                        'nation_name': str(member.get('nation_name', 'Unknown')),
                        'active': False,
                        'error': 'Alliance cache not available',
                        'updated_score': None
                    })
                return validation_results
            
            # Create a lookup dictionary for all cached nations by name
            nations_by_name = {}
            for alliance_key, alliance_data in alliance_cache.items():
                if isinstance(alliance_data, dict) and 'nations' in alliance_data:
                    nations = alliance_data['nations']
                    if isinstance(nations, list):
                        for nation in nations:
                            if isinstance(nation, dict) and 'nation_name' in nation:
                                nation_name = nation['nation_name'].lower()
                                nations_by_name[nation_name] = nation
            
            for member in members:
                try:
                    if not isinstance(member, dict):
                        validation_results.append({
                            'nation_name': 'Unknown',
                            'active': False,
                            'error': 'Invalid member data',
                            'updated_score': None
                        })
                        continue
                    
                    nation_name = str(member.get('nation_name', 'Unknown'))
                    
                    # Look up nation data in cache
                    try:
                        # Search for nation in cached data (case-insensitive)
                        nation_name_lower = nation_name.lower()
                        cached_nation = nations_by_name.get(nation_name_lower)
                        
                        if cached_nation:
                            # Check if nation is active (not in vacation mode)
                            vacation_turns = cached_nation.get('vacation_mode_turns', 0)
                            is_active = vacation_turns == 0
                            
                            validation_results.append({
                                'nation_name': nation_name,
                                'active': is_active,
                                'error': None,
                                'updated_score': cached_nation.get('score', 0) if is_active else None,
                                'vacation_turns': vacation_turns
                            })
                        else:
                            validation_results.append({
                                'nation_name': nation_name,
                                'active': False,
                                'error': 'Nation not found in cache',
                                'updated_score': None
                            })
                    
                    except Exception as cache_error:
                        logger.warning(f"Error looking up nation {nation_name} in cache: {cache_error}")
                        validation_results.append({
                            'nation_name': nation_name,
                            'active': False,
                            'error': f'Cache lookup failed: {str(cache_error)[:50]}',
                            'updated_score': None
                        })
                
                except Exception as member_error:
                    logger.warning(f"Error validating member: {member_error}")
                    validation_results.append({
                        'nation_name': str(member.get('nation_name', 'Unknown')),
                        'active': False,
                        'error': f'Validation error: {str(member_error)[:50]}',
                        'updated_score': None
                    })
            
            logger.info(f"Validated {len(validation_results)} party members")
            return validation_results
            
        except Exception as e:
            logger.error(f"Critical error in _validate_party_members: {e}")
            # Return error results for all members
            for member in members:
                validation_results.append({
                    'nation_name': str(member.get('nation_name', 'Unknown')),
                    'active': False,
                    'error': 'Validation system error',
                    'updated_score': None
                })
            return validation_results
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the interaction is from the command author with error handling."""
        try:
            if not interaction or not interaction.user:
                logger.error("Invalid interaction or user")
                return False
            
            if interaction.user.id != self.author_id:
                await interaction.response.send_message("❌ You cannot use this menu.")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in interaction_check: {e}")
            return False
    
    def create_embed(self) -> discord.Embed:
        """Create embed for current party with comprehensive error handling."""
        try:
            if not self.current_parties:
                logger.warning("No current parties available for embed creation")
                return discord.Embed(
                    title="❌ No Saved Parties",
                    description="No saved blitz parties found.",
                    color=discord.Color.red()
                )
            
            # Validate current party index
            if self.current_party_index < 0 or self.current_party_index >= len(self.current_parties):
                logger.error(f"Invalid party index: {self.current_party_index} (max: {len(self.current_parties) - 1})")
                self.current_party_index = 0
                if not self.current_parties:
                    return discord.Embed(
                        title="❌ No Saved Parties",
                        description="No saved blitz parties found.",
                        color=discord.Color.red()
                    )
            
            party = self.current_parties[self.current_party_index]
            
            # Validate party data
            if not isinstance(party, dict):
                logger.error(f"Current party is not a dict: {type(party)}")
                return discord.Embed(
                    title="❌ Data Error",
                    description="Invalid party data format.",
                    color=discord.Color.red()
                )
            
            party_name = str(party.get('party_name', 'Unknown Party'))
            
            embed = discord.Embed(
                title=f"👥 {party_name}",
                description=f"Blitz Party {self.current_party_index + 1} of {len(self.current_parties)}",
                color=discord.Color.from_rgb(0, 150, 255)
            )
            
            # Party overview with safe value extraction
            total_score = self._safe_get_numeric(party.get('party_stats', {}), 'total_score', 0)
            member_count = self._safe_get_numeric(party.get('party_stats', {}), 'member_count', 0)
            strategic_count = self._safe_get_numeric(party.get('party_stats', {}), 'strategic_count', 0)
            
            military_advantages = self._safe_get_dict(party, 'military_advantages', {})
            ground_adv = self._safe_get_numeric(military_advantages, 'ground', 0)
            air_adv = self._safe_get_numeric(military_advantages, 'air', 0)
            naval_adv = self._safe_get_numeric(military_advantages, 'naval', 0)
            
            # Calculate optimization metrics
            optimization_score = self._calculate_party_optimization_score(party)
            optimization_status = self._get_optimization_status(optimization_score)
            
            embed.add_field(
                name="📊 Party Overview",
                value=(
                    f"**Total Score:** {total_score:,.0f}\n"
                    f"**Members:** {member_count:,.0f}\n"
                    f"**Strategic Units:** {strategic_count:,.0f}\n"
                    f"**Ground Advantage:** {ground_adv:,.0f}\n"
                    f"**Air Advantage:** {air_adv:,.0f}\n"
                    f"**Naval Advantage:** {naval_adv:,.0f}"
                ),
                inline=False
            )
            
            # Add optimization status field
            embed.add_field(
                name="🎯 Optimization Status",
                value=(
                    f"**Quality Score:** {optimization_score:.1f}/100\n"
                    f"**Status:** {optimization_status['emoji']} {optimization_status['text']}\n"
                    f"**War Range Efficiency:** {self._calculate_war_range_efficiency(party):.1f}%\n"
                    f"**Military Balance:** {self._calculate_military_balance(party):.1f}%"
                ),
                inline=True
            )
            
            # Attack range with validation
            attack_range = self._safe_get_dict(party, 'attack_range', {})
            if attack_range:
                min_attackable = self._safe_get_numeric(attack_range, 'min_attackable', 0)
                max_attackable = self._safe_get_numeric(attack_range, 'max_attackable', 0)
                min_score = self._safe_get_numeric(attack_range, 'min_score', 0)
                max_score = self._safe_get_numeric(attack_range, 'max_score', 0)
                
                embed.add_field(
                    name="🎯 Attack Range",
                    value=(
                        f"**Targetable Range:** {min_attackable:,.0f} - {max_attackable:,.0f}\n"
                        f"**Party Score Range:** {min_score:,.0f} - {max_score:,.0f}"
                    ),
                    inline=True
                )
            
            # War range data with validation
            war_range_data = self._safe_get_dict(party, 'war_range_data', {})
            if war_range_data:
                ground_targets = self._safe_get_numeric(war_range_data.get('ground', {}), 'can_attack', 0)
                air_targets = self._safe_get_numeric(war_range_data.get('air', {}), 'can_attack', 0)
                naval_targets = self._safe_get_numeric(war_range_data.get('naval', {}), 'can_attack', 0)
                total_targets = self._safe_get_numeric(war_range_data.get('total', {}), 'can_attack', 0)
                
                embed.add_field(
                    name="⚔️ War Range Analysis",
                    value=(
                        f"**Ground:** {ground_targets:,.0f} targets\n"
                        f"**Air:** {air_targets:,.0f} targets\n"
                        f"**Naval:** {naval_targets:,.0f} targets\n"
                        f"**Total:** {total_targets:,.0f} targets"
                    ),
                    inline=True
                )
            
            # Members with validation
            members = self._safe_get_list(party, 'members', [])
            members_text = ""
            
            for i, member in enumerate(members, 1):
                try:
                    if not isinstance(member, dict):
                        logger.warning(f"Member {i} is not a dict: {type(member)}")
                        continue
                    
                    nation_name = str(member.get('nation_name', 'Unknown'))
                    leader_name = str(member.get('leader_name', 'Unknown'))
                    score = self._safe_get_numeric(member, 'score', 0)
                    advantages = ', '.join(self._safe_get_list(member, 'military_advantages', ['Standard']))
                    strategic = self._safe_get_bool(member, 'can_missile', False) or self._safe_get_bool(member, 'can_nuke', False)
                    strategic_icon = '✅' if strategic else '❌'
                    
                    members_text += (
                        f"**{i}. {nation_name}** ({leader_name})\n"
                        f"Score: {score:,.0f} | Advantages: {advantages}\n"
                        f"Strategic: {strategic_icon}\n\n"
                    )
                    
                except Exception as e:
                    logger.warning(f"Error processing member {i}: {e}")
                    continue
            
            # Truncate members text if too long
            if len(members_text) > 1024:
                members_text = members_text[:1021] + "..."
            
            embed.add_field(
                name="👥 Party Members",
                value=members_text or "No members",
                inline=False
            )
            
            embed.set_footer(text=f"Use buttons below to navigate • Generated at {datetime.now().strftime('%H:%M:%S')}")
            
            return embed
            
        except Exception as e:
            logger.error(f"Critical error in create_embed: {e}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            return discord.Embed(
                title="❌ Embed Creation Error",
                description="An error occurred while creating the party embed.",
                color=discord.Color.red()
            )
    
    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.secondary, row=0)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Navigate to previous party with error handling."""
        try:
            if not self.current_parties:
                logger.warning("Attempted to navigate previous with no parties")
                await interaction.response.send_message("❌ No parties to navigate.")
                return
            
            if len(self.current_parties) == 0:
                logger.warning("Current parties list is empty")
                await interaction.response.send_message("❌ No parties to navigate.")
                return
            
            # Calculate previous index with bounds checking
            self.current_party_index = (self.current_party_index - 1) % len(self.current_parties)
            
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
            
        except Exception as e:
            logger.error(f"Error in previous_button: {e}")
            await interaction.response.send_message("❌ Error navigating to previous party.")
    
    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.secondary, row=0)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Navigate to next party with error handling."""
        try:
            if not self.current_parties:
                logger.warning("Attempted to navigate next with no parties")
                await interaction.response.send_message("❌ No parties to navigate.")
                return
            
            if len(self.current_parties) == 0:
                logger.warning("Current parties list is empty")
                await interaction.response.send_message("❌ No parties to navigate.")
                return
            
            # Calculate next index with bounds checking
            self.current_party_index = (self.current_party_index + 1) % len(self.current_parties)
            
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
            
        except Exception as e:
            logger.error(f"Error in next_button: {e}")
            await interaction.response.send_message("❌ Error navigating to next party.")
    
    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.primary, row=1)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Refresh party data from saved files with error handling."""
        try:
            logger.info("Refreshing party data")
            await self._load_saved_parties()
            
            if not self.current_parties:
                logger.warning("No saved parties found after refresh")
                await interaction.response.send_message("❌ No saved parties found.")
                return
            
            # Reset to first party
            self.current_party_index = 0
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
            
        except Exception as e:
            logger.error(f"Error in refresh_button: {e}")
            await interaction.response.send_message("❌ Error refreshing party data.")
    
    @discord.ui.button(label="🔍 Validate", style=discord.ButtonStyle.primary, row=1)
    async def validate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Validate party members in real-time and update their status."""
        try:
            if not self.current_parties:
                await interaction.response.send_message("❌ No parties to validate.")
                return
            
            if self.current_party_index < 0 or self.current_party_index >= len(self.current_parties):
                await interaction.response.send_message("❌ Invalid party selected.")
                return
            
            # Defer the response as validation might take time
            await interaction.response.defer()
            
            party = self.current_parties[self.current_party_index]
            members = self._safe_get_list(party, 'members', [])
            
            if not members:
                await interaction.followup.send("❌ No members to validate in this party.")
                return
            
            # Validate each member using the query system
            validation_results = await self._validate_party_members(members)
            
            # Create validation results embed
            embed = discord.Embed(
                title="🔍 Real-Time Party Validation",
                description=f"Validation results for {party.get('party_name', 'Unknown Party')}",
                color=discord.Color.from_rgb(0, 200, 255)
            )
            
            active_count = 0
            inactive_count = 0
            error_count = 0
            
            validation_text = ""
            for i, result in enumerate(validation_results, 1):
                status_emoji = "✅" if result['active'] else "❌" if result['error'] else "⚠️"
                nation_name = result.get('nation_name', 'Unknown')
                
                if result['active']:
                    active_count += 1
                    status_text = "Active"
                    if result.get('updated_score'):
                        status_text += f" (Score: {result['updated_score']:,.0f})"
                elif result['error']:
                    error_count += 1
                    status_text = f"Error: {result['error']}"
                else:
                    inactive_count += 1
                    status_text = "Inactive/VM"
                
                validation_text += f"{status_emoji} **{nation_name}**: {status_text}\n"
            
            embed.add_field(
                name="📊 Validation Summary",
                value=(
                    f"**Active Members:** {active_count}\n"
                    f"**Inactive/VM Members:** {inactive_count}\n"
                    f"**Validation Errors:** {error_count}\n"
                    f"**Total Validated:** {len(validation_results)}"
                ),
                inline=True
            )
            
            # Truncate validation text if too long
            if len(validation_text) > 1024:
                validation_text = validation_text[:1021] + "..."
            
            embed.add_field(
                name="🔍 Member Status",
                value=validation_text or "No validation data",
                inline=False
            )
            
            embed.set_footer(text=f"Validated at {datetime.now().strftime('%H:%M:%S')}")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in validate_button: {e}")
            try:
                if interaction.response.is_done():
                    await interaction.followup.send("❌ Error validating party members.")
                else:
                    await interaction.response.send_message("❌ Error validating party members.")
            except:
                pass
    
    @discord.ui.button(label="📊 Stats", style=discord.ButtonStyle.success, row=1)
    async def stats_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show overall statistics for all parties with error handling."""
        try:
            if not self.current_parties:
                logger.warning("Attempted to show stats with no parties")
                await interaction.response.send_message("❌ No parties to analyze.")
                return
            
            if len(self.current_parties) == 0:
                logger.warning("Current parties list is empty for stats")
                await interaction.response.send_message("❌ No parties to analyze.")
                return
            
            # Calculate overall statistics with validation
            total_parties = len(self.current_parties)
            total_members = 0
            total_score = 0
            total_strategic = 0
            
            for party in self.current_parties:
                try:
                    total_members += self._safe_get_numeric(party.get('party_stats', {}), 'member_count', 0)
                    total_score += self._safe_get_numeric(party.get('party_stats', {}), 'total_score', 0)
                    total_strategic += self._safe_get_numeric(party.get('party_stats', {}), 'strategic_count', 0)
                except Exception as e:
                    logger.warning(f"Error calculating stats for party: {e}")
                    continue
            
            avg_members = total_members / total_parties if total_parties > 0 else 0
            avg_score = total_score / total_parties if total_parties > 0 else 0
            
            # Find max and min scores safely
            try:
                party_scores = [self._safe_get_numeric(party.get('party_stats', {}), 'total_score', 0) for party in self.current_parties]
                highest_score = max(party_scores) if party_scores else 0
                lowest_score = min(party_scores) if party_scores else 0
            except Exception as e:
                logger.warning(f"Error calculating score ranges: {e}")
                highest_score = 0
                lowest_score = 0
            
            embed = discord.Embed(
                title="📊 Blitz Parties Statistics",
                description=f"Overall analysis of {total_parties} saved parties",
                color=discord.Color.from_rgb(0, 255, 0)
            )
            
            embed.add_field(
                name="📈 Party Statistics",
                value=(
                    f"**Total Parties:** {total_parties:,.0f}\n"
                    f"**Total Members:** {total_members:,.0f}\n"
                    f"**Average Members per Party:** {avg_members:.1f}\n"
                    f"**Total Strategic Units:** {total_strategic:,.0f}"
                ),
                inline=False
            )
            
            embed.add_field(
                name="💰 Score Statistics",
                value=(
                    f"**Total Score:** {total_score:,.0f}\n"
                    f"**Average Score per Party:** {avg_score:,.0f}\n"
                    f"**Highest Party Score:** {highest_score:,.0f}\n"
                    f"**Lowest Party Score:** {lowest_score:,.0f}"
                ),
                inline=True
            )
            
            # Calculate military advantages
            try:
                total_ground_adv = sum(self._safe_get_numeric(party.get('military_advantages', {}), 'ground', 0) for party in self.current_parties)
                total_air_adv = sum(self._safe_get_numeric(party.get('military_advantages', {}), 'air', 0) for party in self.current_parties)
                total_naval_adv = sum(self._safe_get_numeric(party.get('military_advantages', {}), 'naval', 0) for party in self.current_parties)
                
                embed.add_field(
                    name="⚔️ Military Advantages",
                    value=(
                        f"**Total Ground Advantage:** {total_ground_adv:,.0f}\n"
                        f"**Total Air Advantage:** {total_air_adv:,.0f}\n"
                        f"**Total Naval Advantage:** {total_naval_adv:,.0f}"
                    ),
                    inline=True
                )
            except Exception as e:
                logger.warning(f"Error calculating military advantages: {e}")
                embed.add_field(
                    name="⚔️ Military Advantages",
                    value="Error calculating advantages",
                    inline=True
                )
            
            embed.set_footer(text=f"Generated at {datetime.now().strftime('%H:%M:%S')}")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in stats_button: {e}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            await interaction.response.send_message("❌ Error calculating party statistics.")
    
    @discord.ui.button(label="📊 Analysis", style=discord.ButtonStyle.secondary, row=2)
    async def analysis_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show detailed optimization breakdown and analysis."""
        try:
            await interaction.response.defer()
            
            if not self.saved_parties_data or self.current_party_index >= len(self.saved_parties_data):
                await interaction.followup.send("❌ No party data available for analysis.")
                return
            
            current_party = self.saved_parties_data[self.current_party_index]
            members = self._safe_get_list(current_party, 'members', [])
            
            if not members:
                await interaction.followup.send("❌ No members found in current party.")
                return
            
            # Calculate detailed metrics
            optimization_score = self._calculate_party_optimization_score(current_party)
            war_range_efficiency = self._calculate_war_range_efficiency(current_party)
            military_balance = self._calculate_military_balance(current_party)
            strategic_distribution = self._calculate_strategic_distribution(current_party)
            optimization_status = self._get_optimization_status(optimization_score)
            
            # Create analysis embed
            embed = discord.Embed(
                title="📊 Detailed Party Analysis",
                color=0x3498db,
                timestamp=datetime.utcnow()
            )
            
            # Overall optimization
            embed.add_field(
                name="🎯 Overall Optimization",
                value=f"{optimization_status['emoji']} **{optimization_status['text']}** ({optimization_score:.1f}/100)",
                inline=False
            )
            
            # War range analysis
            war_range_data = current_party.get('war_range', {})
            min_score = self._safe_get_numeric(war_range_data, 'min_score', 0)
            max_score = self._safe_get_numeric(war_range_data, 'max_score', 0)
            range_span = max_score - min_score if max_score > min_score else 0
            
            embed.add_field(
                name="⚔️ War Range Efficiency",
                value=f"**{war_range_efficiency:.1f}%**\n"
                      f"Range: {min_score:.0f} - {max_score:.0f}\n"
                      f"Span: {range_span:.0f} points",
                inline=True
            )
            
            # Military balance
            embed.add_field(
                name="🛡️ Military Balance",
                value=f"**{military_balance:.1f}%**\n"
                      f"Ground: {current_party.get('military_advantages', {}).get('ground', 0):.1f}\n"
                      f"Air: {current_party.get('military_advantages', {}).get('air', 0):.1f}\n"
                      f"Naval: {current_party.get('military_advantages', {}).get('naval', 0):.1f}",
                inline=True
            )
            
            # Strategic distribution
            embed.add_field(
                name="🏭 Strategic Distribution",
                value=f"**{strategic_distribution:.1f}%**\n"
                      f"Members: {len(members)}\n"
                      f"Avg Score: {sum(self._safe_get_numeric(m, 'score', 0) for m in members) / len(members):.0f}",
                inline=True
            )
            
            # Attack range analysis
            attack_range = current_party.get('attack_range', {})
            if attack_range:
                embed.add_field(
                    name="🎯 Attack Range",
                    value=f"Min: {self._safe_get_numeric(attack_range, 'min_score', 0):.0f}\n"
                          f"Max: {self._safe_get_numeric(attack_range, 'max_score', 0):.0f}\n"
                          f"Targets: {self._safe_get_numeric(attack_range, 'target_count', 0)}",
                    inline=True
                )
            
            # Party composition
            if members:
                member_names = [str(m.get('nation_name', 'Unknown'))[:15] for m in members[:5]]
                if len(members) > 5:
                    member_names.append(f"... +{len(members) - 5} more")
                
                embed.add_field(
                    name="👥 Party Composition",
                    value="\n".join(member_names),
                    inline=True
                )
            
            # Recommendations
            recommendations = []
            if optimization_score < 70:
                recommendations.append("• Consider rebalancing member scores")
            if war_range_efficiency < 80:
                recommendations.append("• Optimize war range coverage")
            if military_balance < 75:
                recommendations.append("• Improve military unit distribution")
            if strategic_distribution < 70:
                recommendations.append("• Review strategic unit allocation")
            
            if recommendations:
                embed.add_field(
                    name="💡 Recommendations",
                    value="\n".join(recommendations[:3]),  # Limit to 3 recommendations
                    inline=False
                )
            else:
                embed.add_field(
                    name="✅ Status",
                    value="Party is well-optimized across all metrics!",
                    inline=False
                )
            
            embed.set_footer(text="Analysis based on current party configuration")
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in analysis_button: {e}")
            await interaction.followup.send("❌ An error occurred during analysis.")


class PartiesManager:
    """Manager class for handling parties operations with comprehensive error handling."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.error_count = 0
        self.max_errors = 10
        
        # Validate bot instance
        if not self.bot:
            logger.error("Bot instance is None in PartiesManager constructor")
            raise ValueError("Bot instance cannot be None")
    
    def _log_error(self, context: str, error: Exception):
        """Log errors with context and increment error counter."""
        self.error_count += 1
        logger.error(f"PartiesManager Error ({context}): {error}")
        logger.error(f"Error count: {self.error_count}/{self.max_errors}")
        
        if self.error_count >= self.max_errors:
            logger.critical("Maximum error count reached in PartiesManager")
    
    def _safe_get_numeric(self, data: dict, key: str, default: float = 0) -> float:
        """Safely get a numeric value from a dictionary."""
        try:
            value = data.get(key, default)
            if isinstance(value, (int, float)):
                return float(value)
            else:
                return float(default)
        except (ValueError, TypeError):
            return float(default)
    
    async def get_parties_view(self, author_id: int, blitz_cog: Any) -> Optional[PartiesView]:
        """Get a PartiesView instance with loaded data and error handling."""
        try:
            if not blitz_cog:
                logger.error("Blitz cog is None in get_parties_view")
                return None
            
            if not hasattr(blitz_cog, 'get_saved_blitz_parties'):
                logger.error("Blitz cog missing get_saved_blitz_parties method")
                return None
            
            view = PartiesView(author_id, self.bot, blitz_cog)
            
            # Wait a moment for async loading to complete
            await asyncio.sleep(0.1)
            
            return view
            
        except Exception as e:
            self._log_error("Creating PartiesView", e)
            return None
    
    async def get_parties_statistics(self, blitz_cog: Any) -> Dict[str, Any]:
        """Get comprehensive statistics about saved parties with error handling."""
        try:
            if not blitz_cog:
                logger.error("Blitz cog is None in get_parties_statistics")
                return {
                    'total_parties': 0,
                    'total_members': 0,
                    'avg_members_per_party': 0,
                    'total_score': 0,
                    'avg_score_per_party': 0,
                    'total_strategic_units': 0,
                    'error': 'Blitz cog not available'
                }
            
            if not hasattr(blitz_cog, 'get_saved_blitz_parties'):
                logger.error("Blitz cog missing get_saved_blitz_parties method")
                return {
                    'total_parties': 0,
                    'total_members': 0,
                    'avg_members_per_party': 0,
                    'total_score': 0,
                    'avg_score_per_party': 0,
                    'total_strategic_units': 0,
                    'error': 'get_saved_blitz_parties method not available'
                }
            
            logger.info("Getting parties statistics")
            saved_data = await blitz_cog.get_saved_blitz_parties()
            
            if not saved_data:
                logger.warning("No saved party data returned")
                return {
                    'total_parties': 0,
                    'total_members': 0,
                    'avg_members_per_party': 0,
                    'total_score': 0,
                    'avg_score_per_party': 0,
                    'total_strategic_units': 0,
                    'error': 'No saved parties found'
                }
            
            if not isinstance(saved_data, list):
                logger.error(f"Invalid saved data format: expected list, got {type(saved_data)}")
                return {
                    'total_parties': 0,
                    'total_members': 0,
                    'avg_members_per_party': 0,
                    'total_score': 0,
                    'avg_score_per_party': 0,
                    'total_strategic_units': 0,
                    'error': 'Invalid data format'
                }
            
            if len(saved_data) == 0:
                logger.warning("Saved parties list is empty")
                return {
                    'total_parties': 0,
                    'total_members': 0,
                    'avg_members_per_party': 0,
                    'total_score': 0,
                    'avg_score_per_party': 0,
                    'total_strategic_units': 0,
                    'error': 'No saved parties found'
                }
            
            # Get the latest parties entry
            latest_parties = saved_data[-1]
            if not latest_parties or not isinstance(latest_parties, dict):
                logger.error("Invalid latest parties entry")
                return {
                    'total_parties': 0,
                    'total_members': 0,
                    'avg_members_per_party': 0,
                    'total_score': 0,
                    'avg_score_per_party': 0,
                    'total_strategic_units': 0,
                    'error': 'Invalid party data structure'
                }
            
            if 'parties' not in latest_parties:
                logger.error("Missing 'parties' key in latest parties data")
                return {
                    'total_parties': 0,
                    'total_members': 0,
                    'avg_members_per_party': 0,
                    'total_score': 0,
                    'avg_score_per_party': 0,
                    'total_strategic_units': 0,
                    'error': 'Missing party data'
                }
            
            parties = latest_parties['parties']
            if not isinstance(parties, list):
                logger.error(f"Invalid parties format: expected list, got {type(parties)}")
                return {
                    'total_parties': 0,
                    'total_members': 0,
                    'avg_members_per_party': 0,
                    'total_score': 0,
                    'avg_score_per_party': 0,
                    'total_strategic_units': 0,
                    'error': 'Invalid party list format'
                }
            
            total_parties = len(parties)
            if total_parties == 0:
                logger.warning("No parties in the list")
                return {
                    'total_parties': 0,
                    'total_members': 0,
                    'avg_members_per_party': 0,
                    'total_score': 0,
                    'avg_score_per_party': 0,
                    'total_strategic_units': 0,
                    'error': 'No parties found'
                }
            
            # Calculate statistics with safe value extraction
            total_members = 0
            total_score = 0
            total_strategic = 0
            
            for party in parties:
                try:
                    party_stats = party.get('party_stats', {})
                    if isinstance(party_stats, dict):
                        total_members += self._safe_get_numeric(party_stats, 'member_count', 0)
                        total_score += self._safe_get_numeric(party_stats, 'total_score', 0)
                        total_strategic += self._safe_get_numeric(party_stats, 'strategic_count', 0)
                except Exception as e:
                    logger.warning(f"Error processing party statistics: {e}")
                    continue
            
            # Calculate score ranges
            try:
                party_scores = []
                for party in parties:
                    party_stats = party.get('party_stats', {})
                    if isinstance(party_stats, dict):
                        score = self._safe_get_numeric(party_stats, 'total_score', 0)
                        party_scores.append(score)
                
                highest_score = max(party_scores) if party_scores else 0
                lowest_score = min(party_scores) if party_scores else 0
            except Exception as e:
                logger.warning(f"Error calculating score ranges: {e}")
                highest_score = 0
                lowest_score = 0
            
            avg_members = total_members / total_parties if total_parties > 0 else 0
            avg_score = total_score / total_parties if total_parties > 0 else 0
            
            logger.info(f"Successfully calculated statistics for {total_parties} parties")
            
            return {
                'total_parties': total_parties,
                'total_members': total_members,
                'avg_members_per_party': avg_members,
                'total_score': total_score,
                'avg_score_per_party': avg_score,
                'total_strategic_units': total_strategic,
                'highest_party_score': highest_score,
                'lowest_party_score': lowest_score,
                'success': True
            }
            
        except asyncio.CancelledError:
            logger.warning("Statistics calculation was cancelled")
            return {
                'total_parties': 0,
                'total_members': 0,
                'avg_members_per_party': 0,
                'total_score': 0,
                'avg_score_per_party': 0,
                'total_strategic_units': 0,
                'error': 'Operation cancelled'
            }
            
        except Exception as e:
            self._log_error("Getting parties statistics", e)
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            return {
                'total_parties': 0,
                'total_members': 0,
                'avg_members_per_party': 0,
                'total_score': 0,
                'avg_score_per_party': 0,
                'total_strategic_units': 0,
                'error': str(e)
            }
