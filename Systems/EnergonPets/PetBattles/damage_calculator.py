"""
Unified Damage Calculator for Energon Pets Battle System
Handles consistent damage calculations across PvE and PvP battles
New roll-based system: 1-4 miss, 5-8 base, 9-12 stat*1/3*roll, 13-16 stat*2/3*roll, 17-20 stat*full*roll
"""

import random
from typing import Dict, Any, Tuple


class DamageCalculator:
    """Unified damage calculation system for all battle types"""

    MISS_RANGE = (1, 4)
    BASE_RANGE = (5, 8) 
    LOW_MULT_RANGE = (9, 12)
    MID_MULT_RANGE = (13, 16)  
    HIGH_MULT_RANGE = (17, 20) 
    MAX_CHARGE_MULTIPLIER = 16.0
    VULNERABILITY_WHEN_CHARGING = 1.25
    
    @staticmethod
    def calculate_roll_multiplier(roll: int, base_stat: int) -> Tuple[int, str]:
        """
        Calculate damage/defense based on roll result
        
        Args:
            roll: d20 roll result (1-20)
            base_stat: Base attack or defense stat
            
        Returns:
            Tuple of (final_value, result_type)
            - final_value: Calculated attack/defense value
            - result_type: Description of roll result
        """
        if DamageCalculator.MISS_RANGE[0] <= roll <= DamageCalculator.MISS_RANGE[1]:
            # Complete miss
            return 0, "miss"
        elif DamageCalculator.BASE_RANGE[0] <= roll <= DamageCalculator.BASE_RANGE[1]:
            # Base stat only
            return base_stat, "base"
        elif DamageCalculator.LOW_MULT_RANGE[0] <= roll <= DamageCalculator.LOW_MULT_RANGE[1]:
            # Stat * 1/3 * roll
            return int(base_stat * (roll / 3)), "low_mult"
        elif DamageCalculator.MID_MULT_RANGE[0] <= roll <= DamageCalculator.MID_MULT_RANGE[1]:
            # Stat * 2/3 * roll
            return int(base_stat * (2 * roll / 3)), "mid_mult"
        elif DamageCalculator.HIGH_MULT_RANGE[0] <= roll <= DamageCalculator.HIGH_MULT_RANGE[1]:
            # Stat * full * roll
            return int(base_stat * roll), "high_mult"
        else:
            # Fallback (shouldn't happen with d20)
            return base_stat, "base"
    
    @staticmethod
    def calculate_battle_action(
        attacker_attack: int,
        target_defense: int,
        charge_multiplier: float = 1.0,
        target_charge_multiplier: float = 1.0,
        action_type: str = "attack",
        attacker_action_type: str = "attack",
        target_action_type: str = "defend"
    ) -> Dict[str, Any]:
        """
        Calculate battle action result with new roll-based system
        
        Args:
            attacker_attack: Base attack power of the attacker
            target_defense: Base defense of the target
            charge_multiplier: Attacker's charge multiplier (1.0 to 16.0)
            target_charge_multiplier: Target's charge multiplier for defense (1.0 to 16.0)
            action_type: "attack" or "defend" (for logging purposes)
            
        Returns:
            Dict with battle result information
        """
        # Input validation and error handling
        try:
            attacker_attack = max(0, int(attacker_attack)) if attacker_attack is not None else 10
            target_defense = max(0, int(target_defense)) if target_defense is not None else 5
            charge_multiplier = max(1.0, min(16.0, float(charge_multiplier))) if charge_multiplier is not None else 1.0
            target_charge_multiplier = max(1.0, min(16.0, float(target_charge_multiplier))) if target_charge_multiplier is not None else 1.0
            action_type = str(action_type) if action_type is not None else "attack"
            attacker_action_type = (str(attacker_action_type or "attack").lower())
            target_action_type = (str(target_action_type or "defend").lower())
        except (ValueError, TypeError) as e:
            # Fallback to safe defaults if conversion fails
            attacker_attack = 10
            target_defense = 5
            charge_multiplier = 1.0
            target_charge_multiplier = 1.0
            action_type = "attack"
            attacker_action_type = "attack"
            target_action_type = "defend"

        # Normalize action types
        if attacker_action_type not in ("attack", "defend", "charge"):
            attacker_action_type = "attack"
        if target_action_type not in ("attack", "defend", "charge"):
            target_action_type = "defend"
        # Roll for attacker (attack action)
        attack_roll = random.randint(1, 20)
        attack_value, attack_result = DamageCalculator.calculate_roll_multiplier(attack_roll, attacker_attack)
        
        # Apply charge multiplier to attack
        final_attack = int(attack_value * charge_multiplier)
        
        # Target defense only applies if defending this round
        if target_action_type == "defend":
            defense_roll = random.randint(1, 20)
            defense_value, defense_result = DamageCalculator.calculate_roll_multiplier(defense_roll, target_defense)
            # Apply charge multiplier to defense
            final_defense = int(defense_value * target_charge_multiplier)
        else:
            defense_roll = None
            defense_result = "none"
            final_defense = 0
        
        # Calculate damage
        if attacker_action_type == "charge":
            # Attacker is charging; no outgoing attack this round
            final_damage = 0
            parry_damage = 0
        else:
            if target_action_type == "defend":
                if final_attack > final_defense:
                    # Attack succeeds through defense
                    final_damage = max(1, final_attack - final_defense)
                    parry_damage = 0
                elif final_attack == final_defense:
                    # Perfect block
                    final_damage = 0
                    parry_damage = 0
                else:
                    # Defense stronger; reflect remaining as counter
                    final_damage = 0
                    if defense_result != "miss":
                        parry_damage = max(1, final_defense - final_attack)
                    else:
                        parry_damage = 0
            elif target_action_type == "charge":
                # Target is charging: takes full attack, with vulnerability
                base_damage = final_attack
                final_damage = int(max(0, base_damage) * DamageCalculator.VULNERABILITY_WHEN_CHARGING)
                parry_damage = 0
            else:
                # Target is not defending: takes full attack, no mitigation
                final_damage = max(1, final_attack)
                parry_damage = 0
        
        return {
            'final_damage': final_damage,
            'parry_damage': parry_damage,
            'attack_roll': attack_roll,
            'defense_roll': defense_roll,
            'attack_result': attack_result,
            'defense_result': defense_result,
            'final_attack': final_attack,
            'final_defense': final_defense,
            'charge_used': charge_multiplier > 1.0 or target_charge_multiplier > 1.0,
            'attacker_action_type': attacker_action_type,
            'target_action_type': target_action_type
        }
    
    @staticmethod
    def calculate_monster_vs_players(
        monster_attack: int,
        player_defenses: Dict[str, Any],
        monster_charge_multiplier: float = 1.0
    ) -> Dict[str, Any]:
        """
        Calculate monster attacking multiple players
        
        Args:
            monster_attack: Monster's attack power
            player_defenses: Dict mapping player IDs to their defense info
            monster_charge_multiplier: Monster's charge multiplier (1.0 to 16.0)
            
        Returns:
            Dict with results for each player
        """
        # Input validation and error handling
        try:
            monster_attack = max(0, int(monster_attack)) if monster_attack is not None else 10
            monster_charge_multiplier = max(1.0, min(16.0, float(monster_charge_multiplier))) if monster_charge_multiplier is not None else 1.0
            if not isinstance(player_defenses, dict):
                player_defenses = {}
        except (ValueError, TypeError):
            # Fallback to safe defaults
            monster_attack = 10
            monster_charge_multiplier = 1.0
            player_defenses = {}
        results = {}
        
        # Calculate damage for each player individually
        for player_id, defense_info in player_defenses.items():
            player_defense = defense_info.get('defense', 0)
            player_charge_multiplier = defense_info.get('charge_multiplier', 1.0)
            # Determine target action for this round
            player_action = str(defense_info.get('action', '') or '').lower()
            if not player_action:
                # Infer from boolean flags if present
                if defense_info.get('defending', False):
                    player_action = 'defend'
                elif defense_info.get('charging', False):
                    player_action = 'charge'
                else:
                    player_action = 'attack'
            
            # Use the new battle action calculation
            battle_result = DamageCalculator.calculate_battle_action(
                attacker_attack=monster_attack,
                target_defense=player_defense,
                charge_multiplier=monster_charge_multiplier,
                target_charge_multiplier=player_charge_multiplier,
                action_type="monster_attack",
                attacker_action_type="attack",
                target_action_type=player_action
            )
            
            results[player_id] = {
                'final_damage': battle_result['final_damage'],
                'parry_damage': battle_result['parry_damage'],
                'attack_roll': battle_result['attack_roll'],
                'defense_roll': battle_result['defense_roll'],
                'attack_result': battle_result['attack_result'],
                'defense_result': battle_result['defense_result'],
                'final_attack': battle_result['final_attack'],
                'final_defense': battle_result['final_defense'],
                'charge_used': battle_result['charge_used'],
                'target_action_type': battle_result['target_action_type']
            }
        
        return results
    
    @staticmethod
    def get_charge_progression() -> list:
        """
        Get the charge multiplier progression: 1 -> 2 -> 4 -> 8 -> 16
        
        Returns:
            List of charge multipliers in order
        """
        return [1.0, 2.0, 4.0, 8.0, 16.0]
    
    @staticmethod
    def get_next_charge_multiplier(current_multiplier: float) -> float:
        """
        Get the next charge multiplier in the progression
        
        Args:
            current_multiplier: Current charge multiplier
            
        Returns:
            Next charge multiplier (capped at 16.0)
        """
        # Input validation and error handling
        try:
            current_multiplier = float(current_multiplier) if current_multiplier is not None else 1.0
            current_multiplier = max(1.0, min(16.0, current_multiplier))  # Clamp to valid range
        except (ValueError, TypeError):
            current_multiplier = 1.0  # Fallback to default
            
        progression = DamageCalculator.get_charge_progression()
        
        # Find current position in progression
        try:
            current_index = progression.index(current_multiplier)
            if current_index < len(progression) - 1:
                return progression[current_index + 1]
            else:
                return DamageCalculator.MAX_CHARGE_MULTIPLIER
        except ValueError:
            # If current multiplier not in progression, start from beginning
            return progression[1]  # Start at 2.0