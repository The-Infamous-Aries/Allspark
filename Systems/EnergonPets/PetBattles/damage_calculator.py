"""
Unified Damage Calculator for Energon Pets Battle System
Handles consistent damage calculations across PvE and PvP battles
"""

import random
from typing import Dict, Any, Tuple


class DamageCalculator:
    """Unified damage calculation system for all battle types"""
    
    CRITICAL_HIT_CHANCE = 0.05  # 5% critical hit chance
    CRITICAL_HIT_MULTIPLIER = 1.5  # 50% bonus damage on critical
    DEFENSE_REDUCTION_DIVISOR = 2  # Defense is halved when not defending
    DEFENSE_MULTIPLIER_DEFENDING = 2.0  # Double defense when defending
    PARRY_DAMAGE_MULTIPLIER = 1.0  # 1:1 ratio for parry damage
    
    @staticmethod
    def calculate_attack_damage(
        attacker_attack: int,
        target_defense: int,
        charge_multiplier: float = 1.0,
        attack_multiplier: float = 1.0,
        target_is_defending: bool = False,
        target_defense_bonus: float = 0.0,
        attacker_is_charging: bool = False
    ) -> Tuple[int, bool, int]:
        """
        Calculate damage dealt from attacker to target
        
        Args:
            attacker_attack: Base attack power of the attacker
            target_defense: Base defense of the target
            charge_multiplier: Multiplier from charge actions (default 1.0)
            attack_multiplier: Multiplier from attack rolls/buffs (default 1.0)
            target_is_defending: Whether the target is currently defending
            target_defense_bonus: Additional defense bonus (default 0.0)
            attacker_is_charging: Whether the attacker is charging (takes 50% more damage)
            
        Returns:
            Tuple of (final_damage, is_critical, parry_damage)
            - final_damage: Damage dealt to target (0 if fully blocked)
            - is_critical: Whether this was a critical hit
            - parry_damage: Damage dealt back to attacker (0 if no parry)
        """
        # Apply attack multipliers first (charge + attack roll/buffs)
        # If attacker was charging (charged last round), apply double damage
        if attacker_is_charging:
            charge_multiplier *= 2.0
        total_attack_power = int(attacker_attack * charge_multiplier * attack_multiplier)
        
        # Check for critical hit
        is_critical = random.random() < DamageCalculator.CRITICAL_HIT_CHANCE
        if is_critical:
            total_attack_power = int(total_attack_power * DamageCalculator.CRITICAL_HIT_MULTIPLIER)
        
        # Calculate effective defense based on target's state
        if target_is_defending:
            # Double defense when defending
            effective_defense = int(target_defense * DamageCalculator.DEFENSE_MULTIPLIER_DEFENDING)
        else:
            # Normal defense (halved when not defending)
            effective_defense = target_defense // DamageCalculator.DEFENSE_REDUCTION_DIVISOR
        
        # Apply any additional defense bonuses
        if target_defense_bonus > 0:
            effective_defense = int(effective_defense * (1 + target_defense_bonus))
        
        # Calculate final damage
        if total_attack_power > effective_defense:
            # Normal hit - damage exceeds defense
            final_damage = max(1, total_attack_power - effective_defense)
            parry_damage = 0
            
        elif total_attack_power == effective_defense:
            # Perfect block - no damage either way
            final_damage = 0
            parry_damage = 0
            
        else:
            # Parry - defense exceeds attack, deal parry damage back
            # But only if target is actually defending
            final_damage = 0
            if target_is_defending:
                parry_damage = max(1, effective_defense - total_attack_power)
            else:
                parry_damage = 0
        
        return final_damage, is_critical, parry_damage
    
    @staticmethod
    def calculate_monster_damage(
        monster_attack: int,
        player_defenses: Dict[str, Any],
        attack_multiplier: float = 1.0
    ) -> Dict[str, Any]:
        """
        Calculate damage from monster to players with defending mechanics
        
        Args:
            monster_attack: Base attack power of the monster
            player_defenses: Dict mapping player_id to their defense info
            attack_multiplier: Multiplier for monster attack (default 1.0)
            
        Returns:
            Dict with damage results for each player
        """
        total_monster_attack = int(monster_attack * attack_multiplier)
        
        # Group players by who they're defending
        defending_groups = {}
        undefended_players = []
        
        for player_id, defense_info in player_defenses.items():
            if defense_info.get('is_defending', False):
                target_id = defense_info.get('defending_target', player_id)
                if target_id not in defending_groups:
                    defending_groups[target_id] = []
                defending_groups[target_id].append(player_id)
            else:
                undefended_players.append(player_id)
        
        results = {}
        
        # Process defended targets
        for target_id, defenders in defending_groups.items():
            # Split monster attack among all defended targets
            damage_per_target = max(1, total_monster_attack // max(1, len(defending_groups)))
            
            # Calculate total defense for this target
            total_defense = 0
            for defender_id in defenders:
                defender_info = player_defenses[defender_id]
                base_defense = defender_info.get('defense', 0)
                defense_bonus = defender_info.get('defense_bonus', 0.0)
                
                # Double defense when defending
                effective_defense = int(base_defense * DamageCalculator.DEFENSE_MULTIPLIER_DEFENDING)
                if defense_bonus > 0:
                    effective_defense = int(effective_defense * (1 + defense_bonus))
                
                total_defense += effective_defense
            
            # Calculate damage for this target
            if damage_per_target > total_defense:
                # Normal damage
                final_damage = max(1, damage_per_target - total_defense)
                parry_damage = 0
                
            elif damage_per_target == total_defense:
                # Perfect block
                final_damage = 0
                parry_damage = 0
                
            else:
                # Parry - deal damage back to monster
                # Only if at least one defender is actually defending
                final_damage = 0
                if any(player_defenses[d].get('is_defending', False) for d in defenders):
                    parry_damage = max(1, total_defense - damage_per_target)
                else:
                    parry_damage = 0
            
            # Store results for all defenders of this target
            for defender_id in defenders:
                results[defender_id] = {
                    'final_damage': final_damage,
                    'is_critical': False,  # Monsters don't crit for simplicity
                    'parry_damage': parry_damage,
                    'is_defending': True,
                    'defending_target': target_id
                }
        
        # Process undefended players
        if undefended_players:
            damage_per_undefended = max(1, total_monster_attack // max(1, len(undefended_players)))
            
            for player_id in undefended_players:
                player_info = player_defenses[player_id]
                base_defense = player_info.get('defense', 0)
                is_charging = player_info.get('is_charging', False)
                
                # Halved defense when not defending
                effective_defense = base_defense // DamageCalculator.DEFENSE_REDUCTION_DIVISOR
                
                # Players take 50% more damage when charging
                if is_charging:
                    effective_damage = int(damage_per_undefended * 1.5)
                else:
                    effective_damage = damage_per_undefended
                
                if effective_damage > effective_defense:
                    final_damage = max(1, effective_damage - effective_defense)
                    parry_damage = 0
                else:
                    final_damage = 0
                    parry_damage = 0
                
                results[player_id] = {
                    'final_damage': final_damage,
                    'is_critical': False,
                    'parry_damage': parry_damage,
                    'is_defending': False,
                    'defending_target': player_id
                }
        
        return results