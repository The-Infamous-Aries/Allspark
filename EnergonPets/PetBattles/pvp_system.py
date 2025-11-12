import discord
import random
import asyncio
import logging
import json
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from enum import Enum, auto
from collections import defaultdict
from Systems.user_data_manager import user_data_manager
from Systems.EnergonPets.pet_levels import calculate_xp_gain, create_level_up_embed
from Systems.EnergonPets.PetBattles.damage_calculator import DamageCalculator

logger = logging.getLogger('pvp_system')

class BattleMode(Enum):
    ONE_VS_ONE = auto()
    TEAM_2V2 = auto()
    TEAM_3V3 = auto()
    TEAM_4V4 = auto()
    FREE_FOR_ALL = auto()

class PvPBattleView(discord.ui.View):
    """View for PvP battles between players"""
    
    _cached_team_names = None
    
    @classmethod
    def _get_cached_team_names(cls):
        """Get team names from cache or load from file (non-blocking)"""
        if cls._cached_team_names is None:
            try:
                with open('Systems/Data/PetsInfo/pets_level.json', 'r') as f:
                    pet_data = json.load(f)
                    cls._cached_team_names = pet_data.get('TEAM_NAMES', [
                        'Alpha Squad', 'Beta Team', 'Gamma Force', 'Delta Unit',
                        'Echo Squad', 'Foxtrot Team', 'Golf Force', 'Hotel Unit'
                    ])
            except Exception:
                # Fallback team names if file read fails
                cls._cached_team_names = [
                    'Alpha Squad', 'Beta Team', 'Gamma Force', 'Delta Unit',
                    'Echo Squad', 'Foxtrot Team', 'Golf Force', 'Hotel Unit'
                ]
        return cls._cached_team_names.copy()
    
    def __init__(self, ctx, participants: Union[List[discord.Member], Dict[str, List[discord.Member]]], 
                 battle_mode: BattleMode = BattleMode.ONE_VS_ONE, team_names: Optional[Dict[str, str]] = None):
        """
        Initialize a PvP battle view
        
        Args:
            ctx: The command context
            participants: Either a list of members (for FFA) or a dict with 'team_a' and 'team_b' keys
            battle_mode: The type of battle (1v1, 2v2, 3v3, 4v4, FFA)
            team_names: Optional dict mapping team IDs to team names (from lobby)
        """
        super().__init__(timeout=300)
        self.ctx = ctx
        self.battle_mode = battle_mode
        self.action_messages = {}  # Store ephemeral action messages for cleanup
        
        # Load team names from JSON as fallback (cached to avoid blocking)
        default_team_names = self._get_cached_team_names()
        
        # Shuffle default team names for fallback
        import random
        random.shuffle(default_team_names)
        
        # Initialize teams based on battle mode
        if battle_mode == BattleMode.FREE_FOR_ALL:
            # For FFA, each participant is their own team
            self.teams = {str(i): [member] for i, member in enumerate(participants[:8])}  # Max 8 for FFA
            # Use provided team names or assign random ones
            if team_names:
                self.team_names = team_names
            else:
                self.team_names = {str(i): default_team_names[i % len(default_team_names)] for i in range(len(participants[:8]))}
        else:
            # For team battles, use the provided teams
            self.teams = {team_id: members for team_id, members in participants.items()}
            
            # Use provided team names or assign from lobby
            if team_names:
                self.team_names = team_names
            else:
                # Map team IDs to specific names if provided, otherwise use defaults
                self.team_names = {}
                for i, team_id in enumerate(participants.keys()):
                    if team_id == 'a' and len(default_team_names) >= 1:
                        self.team_names[team_id] = default_team_names[0]
                    elif team_id == 'b' and len(default_team_names) >= 2:
                        self.team_names[team_id] = default_team_names[1]
                    elif i < len(default_team_names):
                        self.team_names[team_id] = default_team_names[i]
                    else:
                        self.team_names[team_id] = f"Team {team_id.upper()}"
        
        # Initialize player data
        self.players = {}
        self.team_assignments = {}
        
        for team_id, members in self.teams.items():
            for member in members:
                member_id = str(member.id)
                self.players[member_id] = {
                    'user': member,
                    'team_id': team_id,
                    'hp': 100, 'max_hp': 100,
                    'attack': 10, 'defense': 5,
                    'charge': 1.0, 'charging': False,
                    'pet': None, 'alive': True,
                    'xp_earned': 0, 'damage_dealt': 0,
                    'damage_taken': 0, 'kills': 0, 'assists': 0,
                    # Last action tracking for UI parity with battle_system
                    'last_action': None,
                    'last_action_info': {}
                }
                self.team_assignments[member_id] = team_id
        
        # Set up team colors and emojis
        self.team_colors = {
            'a': discord.Color.blue(),
            'b': discord.Color.red(),
            'c': discord.Color.green(),
            'd': discord.Color.gold()
        }
        
        # Set up team emojis (using numbers for teams beyond 2)
        self.team_emojis = {
            'a': '🔵', 'b': '🔴', 'c': '🟢', 'd': '🟡',
            '0': '1️⃣', '1': '2️⃣', '2': '3️⃣', '3': '4️⃣',
            '4': '5️⃣', '5': '6️⃣', '6': '7️⃣', '7': '8️⃣'
        }
        
        # Initialize battle state
        self.message = None
        self.turn_count = 0
        self.battle_over = False
        self.battle_log = []
        self.defending_players = set()
        self.guard_relationships = {}
        self.player_actions = {}
        self.waiting_for_actions = False
        self.death_log = []
        self.turn_order = []
        
        # Start battle initialization
        asyncio.create_task(self.initialize_battle_data())

    def _get_roll_multiplier_from_result(self, result_type: str, roll: int) -> float:
        """Convert attack/defense result type to roll multiplier for display purposes
        Mirrored from battle_system.py for UI consistency."""
        if result_type == "miss":
            return 0.0
        elif result_type == "base":
            return 1.0
        elif result_type == "low_mult":
            return roll / 3.0
        elif result_type == "mid_mult":
            return (2 * roll) / 3.0
        elif result_type == "high_mult":
            return float(roll)
        else:
            return 1.0
    
    def get_team_members(self, team_id: str) -> List[dict]:
        """Get all players in a specific team"""
        return [p for p in self.players.values() if p.get('team_id') == team_id]
    
    def get_alive_team_members(self, team_id: str) -> List[dict]:
        """Get all alive players in a specific team"""
        return [p for p in self.players.values() if p.get('team_id') == team_id and p['alive']]
    
    def get_opposing_teams(self, team_id: str) -> List[str]:
        """Get all team IDs that are opponents of the given team"""
        return [tid for tid in self.teams.keys() if tid != team_id]
    
    def is_team_mode(self) -> bool:
        """Check if this is a team battle (not FFA)"""
        return self.battle_mode != BattleMode.FREE_FOR_ALL
    
    async def initialize_battle_data(self):
        """Initialize pet data for all participants"""
        try:
            tasks = []
            for player_id, player in self.players.items():
                tasks.append(self._load_pet_data(player_id, player))
            
            # Wait for all pet data to load
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Set up turn order (no speed sorting - purely turn-based)
            self.turn_order = [
                p for p in self.players.values() 
                if p['alive']
            ]
            
            await self.start_battle()
        except Exception as e:
            logger.error(f"Battle init error: {e}", exc_info=True)
            if self.message:
                await self.message.edit(content=f"❌ Error: {str(e)}", view=None)
    
    def calculate_equipment_stats(self, equipment):
        """Calculate total stats from equipped items"""
        total_stats = {'attack': 0, 'defense': 0, 'energy': 0, 'maintenance': 0, 'happiness': 0}
        
        if not equipment:
            return total_stats
            
        for slot, item in equipment.items():
            if item and isinstance(item, dict):  # Item is equipped
                stat_bonus = item.get('stat_bonus', {})
                for stat, value in stat_bonus.items():
                    if stat in total_stats:
                        total_stats[stat] += value
                    # Handle max stat mappings for equipment
                    elif stat == 'max_energy':
                        total_stats['energy'] += value
                    elif stat == 'max_maintenance':
                        total_stats['maintenance'] += value
                    elif stat == 'max_happiness':
                        total_stats['happiness'] += value
                    
        return total_stats

    async def _load_pet_data(self, player_id: str, player_data: dict):
        """Load pet data for a single player"""
        try:
            username = player_data.get('user', {}).display_name if player_data.get('user') else None
            user_data = await user_data_manager.get_user_data(str(player_id), username)
            if user_data and 'active_pet' in user_data and user_data['active_pet']:
                pet = user_data['pets'][str(user_data['active_pet'])]
                
                # Calculate base stats
                base_attack = pet.get('attack', 10)
                base_defense = pet.get('defense', 5)
                current_energy = pet.get('energy', 100)
                current_maintenance = pet.get('maintenance', 100)
                current_happiness = pet.get('happiness', 100)
                base_max_energy = pet.get('max_energy', 100)
                base_max_maintenance = pet.get('max_maintenance', 100)
                base_max_happiness = pet.get('max_happiness', 100)
                
                # Calculate equipment bonuses
                equipment_stats = self.calculate_equipment_stats(pet.get('equipment', {}))
                
                # Calculate total stats (base + equipment)
                total_attack = base_attack + equipment_stats['attack']
                total_defense = base_defense + equipment_stats['defense']
                total_max_energy = base_max_energy + equipment_stats['energy']
                total_max_maintenance = base_max_maintenance + equipment_stats['maintenance']
                total_max_happiness = base_max_happiness + equipment_stats['happiness']
                
                # Calculate HP (current stats for HP, max stats for max_hp)
                # Include equipment bonuses in current HP calculation
                current_hp = current_energy + current_maintenance + current_happiness
                current_hp += equipment_stats['energy'] + equipment_stats['maintenance'] + equipment_stats['happiness']
                max_hp = total_max_energy + total_max_maintenance + total_max_happiness
                
                player_data.update({
                    'pet': pet,
                    'hp': current_hp,
                    'max_hp': max_hp,
                    'attack': total_attack,
                    'defense': total_defense
                })
        except Exception as e:
            logger.error(f"Error loading pet data for {player_id}: {e}")
    
    async def start_battle(self):
        embed = self.build_battle_embed("⚔️ Battle starting!")
        self.message = await self.ctx.send(embed=embed)
        await self.start_turn()
    
    async def start_turn(self):
        """Start a new turn in the battle"""
        self.turn_count += 1
        self.waiting_for_actions = True
        self.player_actions = {}
        self.defending_players = set()
        self.guard_relationships = {}
        
        # Reset charge for players who didn't use it
        for player_id, player in self.players.items():
            if player['alive'] and player_id not in self.player_actions:
                player['charge'] = 1.0
        
        # Notify players about the new round
        embed = self.build_battle_embed(f"🔄 Round {self.turn_count} - Select your actions!")
        await self.message.edit(embed=embed)
        
        # Start action collection
        await self.start_action_collection()
    
    async def start_action_collection(self):
        """Start collecting actions from all alive players"""
        self.waiting_for_actions = True
        
        # For FFA, everyone is an enemy
        if self.battle_mode == BattleMode.FREE_FOR_ALL:
            # For FFA, each participant is their own team
            for player_id, player in self.players.items():
                if player['alive']:
                    try:
                        # In FFA, enemies are all other alive players
                        enemies = {
                            pid: p for pid, p in self.players.items() 
                            if p['alive'] and pid != player_id
                        }
                        view = PvPActionView(self, player_id, enemies, is_ffa=True)
                        try:
                            embed = discord.Embed(
                                title="⚔️ PvP Battle Action Required",
                                description=f"{player['user'].mention} it's your turn to act! (FFA)",
                                color=0x00ff00
                            )
                            # Show this player's last action details (FFA)
                            pdata = self.players.get(player_id, {})
                            la = pdata.get('last_action')
                            info = pdata.get('last_action_info', {})
                            if la:
                                if la == 'attack':
                                    tgt = self.players.get(info.get('target_id'), {}).get('user', None)
                                    tgt_name = tgt.display_name if tgt else 'Unknown'
                                    dmg = info.get('damage')
                                    roll = info.get('roll')
                                    res = info.get('result')
                                    eff = info.get('effective_multiplier')
                                    cm = info.get('charge_multiplier_used')
                                    text = f"⚔️ You attacked {tgt_name} for {dmg} • roll {roll} {res} x{eff:.1f}"
                                    if cm and cm != 1.0:
                                        text += f" • ⚡x{cm:.1f}"
                                    embed.add_field(name="Last Action", value=text, inline=False)
                                elif la == 'defend':
                                    prot = self.players.get(info.get('protected_id'), {}).get('user', None)
                                    prot_name = prot.display_name if prot else ('yourself' if info.get('protected_id') == player_id else 'Unknown')
                                    parry = info.get('parry_damage', 0)
                                    roll = info.get('roll')
                                    res = info.get('result')
                                    eff = info.get('defense_effectiveness')
                                    eff_text = f" x{eff:.1f}" if isinstance(eff, (int, float)) else ""
                                    text = f"🛡️ You defended {prot_name} • parry {parry} • roll {roll} {res}{eff_text}"
                                    embed.add_field(name="Last Action", value=text, inline=False)
                                elif la == 'charge':
                                    cm = info.get('charge_multiplier')
                                    text = f"⚡ You charged to x{cm:.1f}"
                                    embed.add_field(name="Last Action", value=text, inline=False)
                            
                            # Check if we have an existing ephemeral message for this user
                            if player_id in self.action_messages:
                                try:
                                    # Try to edit the existing message
                                    await self.action_messages[player_id].edit(embed=embed, view=view)
                                    continue
                                except discord.NotFound:
                                    # Message was deleted, remove from cache and create new one
                                    del self.action_messages[player_id]
                                except Exception as e:
                                    logger.debug(f"Error editing existing ephemeral message for user {player_id}: {e}")
                                    # Fall through to create new message
                            
                            # Send new ephemeral message and store reference
                            msg = await self.ctx.send(
                                embed=embed,
                                view=view,
                                delete_after=60,
                                ephemeral=True
                            )
                            self.action_messages[player_id] = msg
                        except Exception as e:
                            logger.error(f"Error sending action view to {player_id}: {e}")
                            # Fallback to DM if ephemeral message fails
                            await player['user'].send("Failed to send action buttons in channel. Please enable DMs from server members.")
                            await player['user'].send("⚔️ Your turn to act! (FFA)", view=view)
                    except Exception as e:
                        logger.error(f"Error sending action view to {player_id}: {e}")
        else:
            # For team battles, show only enemy team members as targets
            for team_id, members in self.teams.items():
                # Get all enemy teams
                enemy_teams = self.get_opposing_teams(team_id)
                
                for member in members:
                    member_id = str(member.id)
                    if self.players[member_id]['alive']:
                        try:
                            # Get all enemies from all opposing teams
                            enemies = {}
                            for enemy_team_id in enemy_teams:
                                for enemy in self.get_alive_team_members(enemy_team_id):
                                    enemies[str(enemy['user'].id)] = enemy
                            
                            view = PvPActionView(
                                self, 
                                member_id, 
                                enemies,
                                is_team_battle=True,
                                allies={
                                    str(m['user'].id): m 
                                    for m in self.get_team_members(team_id) 
                                    if m['user'].id != member.id and m['alive']
                                }
                            )
                            try:
                                embed = discord.Embed(
                                    title="⚔️ PvP Battle Action Required",
                                    description=f"{member.mention} it's your turn to act!",
                                    color=0x00ff00
                                )
                                # Show this player's last action details (Team battles)
                                pdata = self.players.get(member_id, {})
                                la = pdata.get('last_action')
                                info = pdata.get('last_action_info', {})
                                if la:
                                    if la == 'attack':
                                        tgt = self.players.get(info.get('target_id'), {}).get('user', None)
                                        tgt_name = tgt.display_name if tgt else 'Unknown'
                                        dmg = info.get('damage')
                                        roll = info.get('roll')
                                        res = info.get('result')
                                        eff = info.get('effective_multiplier')
                                        cm = info.get('charge_multiplier_used')
                                        text = f"⚔️ You attacked {tgt_name} for {dmg} • roll {roll} {res} x{eff:.1f}"
                                        if cm and cm != 1.0:
                                            text += f" • ⚡x{cm:.1f}"
                                        embed.add_field(name="Last Action", value=text, inline=False)
                                    elif la == 'defend':
                                        prot = self.players.get(info.get('protected_id'), {}).get('user', None)
                                        prot_name = prot.display_name if prot else ('yourself' if info.get('protected_id') == member_id else 'Unknown')
                                        parry = info.get('parry_damage', 0)
                                        roll = info.get('roll')
                                        res = info.get('result')
                                        eff = info.get('defense_effectiveness')
                                        eff_text = f" x{eff:.1f}" if isinstance(eff, (int, float)) else ""
                                        text = f"🛡️ You defended {prot_name} • parry {parry} • roll {roll} {res}{eff_text}"
                                        embed.add_field(name="Last Action", value=text, inline=False)
                                    elif la == 'charge':
                                        cm = info.get('charge_multiplier')
                                        text = f"⚡ You charged to x{cm:.1f}"
                                        embed.add_field(name="Last Action", value=text, inline=False)
                                
                                # Check if we have an existing ephemeral message for this user
                                if member_id in self.action_messages:
                                    try:
                                        # Try to edit the existing message
                                        await self.action_messages[member_id].edit(embed=embed, view=view)
                                        continue
                                    except discord.NotFound:
                                        # Message was deleted, remove from cache and create new one
                                        del self.action_messages[member_id]
                                    except Exception as e:
                                        logger.debug(f"Error editing existing ephemeral message for user {member_id}: {e}")
                                        # Fall through to create new message
                                
                                # Send new ephemeral message and store reference
                                msg = await self.ctx.send(
                                    embed=embed,
                                    view=view,
                                    delete_after=60,
                                    ephemeral=True
                                )
                                self.action_messages[member_id] = msg
                            except Exception as e:
                                logger.error(f"Error sending action view to {member_id}: {e}")
                                # Fallback to DM if ephemeral message fails
                                await member.send("Failed to send action buttons in channel. Please enable DMs from server members.")
                                await member.send("⚔️ Your turn to act!", view=view)
                        except Exception as e:
                            logger.error(f"Error sending action view to {member_id}: {e}")
        
        embed = self.build_battle_embed("⚔️ Players are choosing actions...")
        await self.message.edit(embed=embed)
        asyncio.create_task(self.check_all_actions_ready())
    
    async def check_all_actions_ready(self):
        """Check if all players have submitted their actions"""
        alive_players = [p_id for p_id, p in self.players.items() if p['alive']]
        if all(p_id in self.player_actions for p_id in alive_players):
            self.waiting_for_actions = False
            
            # Show selected actions summary
            action_summary = []
            for player_id, action_data in self.player_actions.items():
                player = self.players[player_id]
                target = self.players.get(action_data.get('target', ''), {})
                action_text = f"{player['user'].display_name} "
                
                if action_data['action'] == 'attack':
                    action_text += f"attacks {target.get('user', 'Unknown').display_name if target else 'nothing'}"
                elif action_data['action'] == 'defend':
                    target_name = target.get('user', 'themselves').display_name if target else 'themselves'
                    target_name = target_name if target_name != player['user'].display_name else 'themselves'
                    action_text += f"defends {target_name}"
                elif action_data['action'] == 'charge':
                    action_text += "charges up a powerful attack"
                
                action_summary.append(action_text)
            
            # Update battle message with actions summary
            embed = self.build_battle_embed("🎬 Processing round actions...")
            summary = "\n".join(f"• {action}" for action in action_summary)
            embed.add_field(name="Selected Actions", value=summary, inline=False)
            await self.message.edit(embed=embed)
            
            # Small delay to let players see the actions
            await asyncio.sleep(2)
            
            # Process the turn
            await self.process_turn()
    
    async def process_turn(self):
        """Process all actions for the current turn with new mechanics"""
        alive_players = [p_id for p_id, p in self.players.items() if p['alive']]
        
        # Group actions by type for simultaneous processing
        attackers = []
        defenders = []
        chargers = []
        
        for player_id in alive_players:
            if player_id in self.player_actions and self.players[player_id]['alive']:
                action_data = self.player_actions[player_id]
                action = action_data['action']
                
                if action == 'attack':
                    attackers.append((player_id, action_data))
                elif action == 'defend':
                    defenders.append((player_id, action_data))
                elif action == 'charge':
                    chargers.append((player_id, action_data))
        
        # Process charges first (they just increase multipliers)
        for player_id, action_data in chargers:
            await self.process_charge(player_id)
        
        # Process attacks and defenses simultaneously
        await self.process_combat_interactions(attackers, defenders)
        
        # Check for battle end conditions
        if self.check_battle_end():
            await self.end_battle()
        else:
            # Small delay before starting next round
            await asyncio.sleep(2)
            # Start next turn
            await self.start_turn()
        
        # Clean up dead players from turn order
        self.turn_order = [p for p in self.turn_order if p['alive']]
    
    async def process_charge(self, player_id: str):
        """Process a charge action using the new progression system"""
        player = self.players[player_id]
        current_charge = player.get('charge', 1.0)
        new_charge = DamageCalculator.get_next_charge_multiplier(current_charge)
        player['charge'] = new_charge
        # Track last action for UI
        player['last_action'] = 'charge'
        player['last_action_info'] = {
            'charge_multiplier': new_charge
        }

        self.battle_log.append(
            f"⚡ {player['user'].display_name} charges up! "
            f"(Power: {new_charge:.0f}x)"
        )
    
    async def process_combat_interactions(self, attackers, defenders):
        """Process combat interactions based on the new mechanics"""
        # Create a map of who is defending whom
        defending_map = {}
        for defender_id, action_data in defenders:
            target_id = action_data.get('target', defender_id)
            defending_map[target_id] = defender_id
        
        # Create a map of who is attacking whom
        attacking_map = {}
        for attacker_id, action_data in attackers:
            target_id = action_data.get('target')
            if not target_id or target_id not in self.players or not self.players[target_id]['alive']:
                # Find a valid target
                alive_targets = [p_id for p_id, p in self.players.items() 
                               if p['alive'] and p_id != attacker_id]
                if alive_targets:
                    target_id = random.choice(alive_targets)
                    action_data['target'] = target_id
                else:
                    continue
            attacking_map[attacker_id] = target_id
        
        # Handle mutual attacks (both attacking each other)
        processed_pairs = set()
        for attacker_id, target_id in attacking_map.items():
            if target_id in attacking_map and attacking_map[target_id] == attacker_id:
                # Mutual attack - both take full damage
                pair = tuple(sorted([attacker_id, target_id]))
                if pair not in processed_pairs:
                    processed_pairs.add(pair)
                    await self.process_mutual_attack(attacker_id, target_id)
        
        # Process remaining attacks
        for attacker_id, action_data in attackers:
            target_id = action_data.get('target')
            if not target_id:
                continue
                
            # Skip if this was already processed as a mutual attack
            pair = tuple(sorted([attacker_id, target_id]))
            if pair in processed_pairs:
                continue
            
            # Check if target is being defended
            defender_id = defending_map.get(target_id)
            if defender_id and defender_id in self.players and self.players[defender_id]['alive']:
                # Attack vs Defense - use parry mechanics
                await self.process_attack_vs_defense(attacker_id, target_id, defender_id)
            else:
                # Attack vs no defense - full damage
                await self.process_undefended_attack(attacker_id, target_id)
    
    async def process_attack_vs_defense(self, attacker_id: str, target_id: str, defender_id: str):
        """Process attack vs defense with parry mechanics"""
        attacker = self.players[attacker_id]
        target = self.players[target_id]
        defender = self.players[defender_id]
        
        # Use new damage calculator
        result = DamageCalculator.calculate_battle_action(
            attacker_attack=attacker.get('total_attack', attacker.get('attack', 10)),
            target_defense=defender.get('total_defense', defender.get('defense', 5)),
            charge_multiplier=attacker.get('charge', 1.0),
            # Charge does not boost defense in new rules
            target_charge_multiplier=1.0,
            action_type="attack"
        )
        
        # Apply damage and parry
        damage_to_target = result['final_damage']
        # Apply 25% extra incoming damage if target is charging
        if target.get('charging', False) and damage_to_target > 0:
            damage_to_target = int(damage_to_target * 1.25)
        parry_damage = result['parry_damage']
        
        # Apply damage to target
        if damage_to_target > 0:
            target['hp'] = max(0, target['hp'] - damage_to_target)
            attacker['damage_dealt'] = attacker.get('damage_dealt', 0) + damage_to_target
            target['damage_taken'] = target.get('damage_taken', 0) + damage_to_target
            # Apply health loss to pet stats (energy, maintenance, happiness)
            await self.apply_health_loss_to_pet(target_id, damage_to_target)
        
        # Apply parry damage to attacker
        if parry_damage > 0:
            attacker['hp'] = max(0, attacker['hp'] - parry_damage)
            defender['damage_dealt'] = defender.get('damage_dealt', 0) + parry_damage
            attacker['damage_taken'] = attacker.get('damage_taken', 0) + parry_damage
            # Apply health loss to pet stats (energy, maintenance, happiness)
            await self.apply_health_loss_to_pet(attacker_id, parry_damage)
        
        # Reset charge multipliers after use
        attacker['charge'] = 1.0
        defender['charge'] = 1.0

        # Track last actions for UI parity
        attacker_effective = self._get_roll_multiplier_from_result(result.get('attack_result', 'base'), result.get('attack_roll', 0))
        defender_effective = 0.0
        if result.get('attack_result') != 'miss':
            defender_effective = self._get_roll_multiplier_from_result(result.get('defense_result', 'base'), result.get('defense_roll', 0))
        attacker['last_action'] = 'attack'
        attacker['last_action_info'] = {
            'target_id': target_id,
            'damage': damage_to_target,
            'parry_taken': parry_damage,
            'roll': result.get('attack_roll', 0),
            'result': result.get('attack_result', 'base'),
            'effective_multiplier': attacker_effective,
            'charge_multiplier_used': attacker.get('charge', 1.0)
        }
        defender['last_action'] = 'defend'
        defender['last_action_info'] = {
            'protected_id': target_id,
            'parry_damage': parry_damage,
            'roll': result.get('defense_roll', 0),
            'result': result.get('defense_result', 'base'),
            'defense_effectiveness': defender_effective
        }
        
        # Add to battle log
        self.battle_log.append(
            f"⚔️ {attacker['user'].display_name} attacks {target['user'].display_name} "
            f"(Roll: {result['attack_roll']}, {result['attack_result']}) "
            f"🛡️ {defender['user'].display_name} defends "
            f"(Roll: {result['defense_roll']}, {result['defense_result']})"
        )
        
        if damage_to_target > 0:
            self.battle_log.append(f"💥 {target['user'].display_name} takes {damage_to_target} damage!")
        
        if parry_damage > 0:
            self.battle_log.append(f"🔄 {attacker['user'].display_name} takes {parry_damage} parry damage!")
        
        # Check for defeats and award XP
        await self.check_defeat_and_award_xp(target_id, attacker_id)
        await self.check_defeat_and_award_xp(attacker_id, defender_id)
    
    async def process_undefended_attack(self, attacker_id: str, target_id: str):
        """Process attack with no defense - full damage"""
        attacker = self.players[attacker_id]
        target = self.players[target_id]
        
        # Use new damage calculator with no defense
        result = DamageCalculator.calculate_battle_action(
            attacker_attack=attacker.get('total_attack', attacker.get('attack', 10)),
            target_defense=0,  # No defense
            charge_multiplier=attacker.get('charge', 1.0),
            target_charge_multiplier=1.0,
            action_type="attack"
        )
        
        # Apply full damage, with charging vulnerability if target is charging
        damage = result['final_damage']
        if target.get('charging', False) and damage > 0:
            damage = int(damage * 1.25)
        target['hp'] = max(0, target['hp'] - damage)
        attacker['damage_dealt'] = attacker.get('damage_dealt', 0) + damage
        target['damage_taken'] = target.get('damage_taken', 0) + damage
        
        # Apply health loss to pet stats (energy, maintenance, happiness)
        await self.apply_health_loss_to_pet(target_id, damage)
        
        # Reset charge multiplier after use
        attacker['charge'] = 1.0

        # Track last action for UI parity
        effective = self._get_roll_multiplier_from_result(result.get('attack_result', 'base'), result.get('attack_roll', 0))
        attacker['last_action'] = 'attack'
        attacker['last_action_info'] = {
            'target_id': target_id,
            'damage': damage,
            'roll': result.get('attack_roll', 0),
            'result': result.get('attack_result', 'base'),
            'effective_multiplier': effective,
            'charge_multiplier_used': attacker.get('charge', 1.0)
        }
        
        # Add to battle log
        self.battle_log.append(
            f"⚔️ {attacker['user'].display_name} attacks {target['user'].display_name} "
            f"(Roll: {result['attack_roll']}, {result['attack_result']}) "
            f"💥 {damage} damage! (No defense)"
        )
        
        # Check for defeat and award XP
        await self.check_defeat_and_award_xp(target_id, attacker_id)
    
    async def process_mutual_attack(self, player1_id: str, player2_id: str):
        """Process mutual attacks where both players attack each other simultaneously"""
        player1 = self.players[player1_id]
        player2 = self.players[player2_id]
        
        # Calculate damage for player1 attacking player2
        result1 = DamageCalculator.calculate_battle_action(
            attacker_attack=player1.get('total_attack', player1.get('attack', 10)),
            target_defense=0,  # No defense when both attacking
            charge_multiplier=player1.get('charge', 1.0),
            target_charge_multiplier=1.0,
            action_type="attack"
        )
        
        # Calculate damage for player2 attacking player1
        result2 = DamageCalculator.calculate_battle_action(
            attacker_attack=player2.get('total_attack', player2.get('attack', 10)),
            target_defense=0,  # No defense when both attacking
            charge_multiplier=player2.get('charge', 1.0),
            target_charge_multiplier=1.0,
            action_type="attack"
        )
        
        # Apply damage simultaneously
        damage1 = result1['final_damage']
        damage2 = result2['final_damage']
        # Apply 25% vulnerability if the targets are charging
        if player2.get('charging', False) and damage1 > 0:
            damage1 = int(damage1 * 1.25)
        if player1.get('charging', False) and damage2 > 0:
            damage2 = int(damage2 * 1.25)
        
        player2['hp'] = max(0, player2['hp'] - damage1)
        player1['hp'] = max(0, player1['hp'] - damage2)
        
        # Update damage stats
        player1['damage_dealt'] = player1.get('damage_dealt', 0) + damage1
        player2['damage_taken'] = player2.get('damage_taken', 0) + damage1
        player2['damage_dealt'] = player2.get('damage_dealt', 0) + damage2
        player1['damage_taken'] = player1.get('damage_taken', 0) + damage2
        
        # Apply health loss to pet stats (energy, maintenance, happiness)
        await self.apply_health_loss_to_pet(player2_id, damage1)
        await self.apply_health_loss_to_pet(player1_id, damage2)
        
        # Reset charge multipliers after use
        player1['charge'] = 1.0
        player2['charge'] = 1.0

        # Track last actions for UI
        eff1 = self._get_roll_multiplier_from_result(result1.get('attack_result', 'base'), result1.get('attack_roll', 0))
        eff2 = self._get_roll_multiplier_from_result(result2.get('attack_result', 'base'), result2.get('attack_roll', 0))
        player1['last_action'] = 'attack'
        player1['last_action_info'] = {
            'target_id': player2_id,
            'damage': damage1,
            'roll': result1.get('attack_roll', 0),
            'result': result1.get('attack_result', 'base'),
            'effective_multiplier': eff1,
            'charge_multiplier_used': player1.get('charge', 1.0)
        }
        player2['last_action'] = 'attack'
        player2['last_action_info'] = {
            'target_id': player1_id,
            'damage': damage2,
            'roll': result2.get('attack_roll', 0),
            'result': result2.get('attack_result', 'base'),
            'effective_multiplier': eff2,
            'charge_multiplier_used': player2.get('charge', 1.0)
        }
        
        # Add to battle log
        self.battle_log.append(
            f"⚔️💥 MUTUAL ATTACK! {player1['user'].display_name} and {player2['user'].display_name} "
            f"attack each other simultaneously!"
        )
        self.battle_log.append(
            f"⚔️ {player1['user'].display_name} deals {damage1} damage "
            f"(Roll: {result1['attack_roll']}, {result1['attack_result']})"
        )
        self.battle_log.append(
            f"⚔️ {player2['user'].display_name} deals {damage2} damage "
            f"(Roll: {result2['attack_roll']}, {result2['attack_result']})"
        )
        
        # Check for defeats and award XP
        await self.check_defeat_and_award_xp(player2_id, player1_id)
        await self.check_defeat_and_award_xp(player1_id, player2_id)
    
    async def check_defeat_and_award_xp(self, victim_id: str, killer_id: str):
        """Check if a player is defeated and award XP to the killer"""
        if victim_id not in self.players or killer_id not in self.players:
            return
            
        victim = self.players[victim_id]
        killer = self.players[killer_id]
        
        if victim['hp'] <= 0 and victim['alive']:
            victim['alive'] = False
            self.battle_log.append(f"💀 {victim['user'].display_name} has been defeated!")
            
            # Set all pet stats to 0 when pet dies
            await self.set_pet_stats_to_zero(victim_id)
            
            # Award XP and track kills
            xp_gain = 50 + (victim.get('level', 1) * 5)
            killer['xp_earned'] = killer.get('xp_earned', 0) + xp_gain
            killer['kills'] = killer.get('kills', 0) + 1
            
            # Check for level up
            if killer['xp_earned'] >= killer.get('xp_to_next_level', 100):
                await self.level_up_player(killer_id)
    
    async def apply_health_loss_to_pet(self, player_id: str, damage: int):
        """Apply health loss evenly across pet's energy, maintenance, and happiness"""
        try:
            player = self.players.get(player_id)
            if not player:
                return
                
            username = player['user'].display_name
            user_data = await user_data_manager.get_user_data(str(player_id), username)
            if not user_data or 'active_pet' not in user_data or not user_data['active_pet']:
                return
                
            pet_id = str(user_data['active_pet'])
            pet = user_data['pets'][pet_id]
            
            # Distribute damage evenly across the three stats
            damage_per_stat = damage / 3
            
            # Apply damage to each stat, ensuring they don't go below 0
            pet['energy'] = max(0, pet.get('energy', 100) - damage_per_stat)
            pet['maintenance'] = max(0, pet.get('maintenance', 100) - damage_per_stat)
            pet['happiness'] = max(0, pet.get('happiness', 100) - damage_per_stat)
            
            # Save updated pet data
            await user_data_manager.update_user_data(
                str(player_id), 
                {"pets": {pet_id: pet}},
                "pet_data"
            )
            
        except Exception as e:
            logger.error(f"Error applying health loss to pet for {player_id}: {e}")
    
    async def set_pet_stats_to_zero(self, player_id: str):
        """Set all pet stats (energy, maintenance, happiness) to 0 when pet dies"""
        try:
            player = self.players.get(player_id)
            if not player:
                return
                
            username = player['user'].display_name
            user_data = await user_data_manager.get_user_data(str(player_id), username)
            if not user_data or 'active_pet' not in user_data or not user_data['active_pet']:
                return
                
            pet_id = str(user_data['active_pet'])
            pet = user_data['pets'][pet_id]
            
            # Set all stats to 0 when pet dies
            pet['energy'] = 0
            pet['maintenance'] = 0
            pet['happiness'] = 0
            
            # Save updated pet data
            await user_data_manager.update_user_data(
                str(player_id), 
                {"pets": {pet_id: pet}},
                "pet_data"
            )
            
        except Exception as e:
            logger.error(f"Error setting pet stats to zero for {player_id}: {e}")
     
    async def process_defend(self, defender_id: str, target_id: str):
        """Process a defend action with enhanced mechanics
        
        Args:
            defender_id: ID of the player defending
            target_id: ID of the player being defended (can be self)
        """
        if defender_id not in self.players or not self.players[defender_id]['alive']:
            return  # Skip if defender is invalid
            
        defender = self.players[defender_id]
        
        # If target is invalid, default to self-defense
        if target_id not in self.players or not self.players[target_id]['alive']:
            target_id = defender_id
            
        target = self.players[target_id]
        
        # Set up guard relationship (can defend others or self)
        self.guard_relationships[defender_id] = target_id
        
        # Store base defense if not already stored
        if 'base_defense' not in defender:
            defender['base_defense'] = defender['defense']
            
        # Add to defending players set for this turn (double defense)
        self.defending_players.add((defender_id, target_id, 2))  # 2 = double defense level

        # Track last action for UI
        defender['last_action'] = 'defend'
        defender['last_action_info'] = {
            'protected_id': target_id,
            'parry_damage': 0,
            'roll': None,
            'result': 'base',
            'defense_effectiveness': None
        }
        
        # Add to battle log
        if target_id == defender_id:
            self.battle_log.append(
                f"🛡️ {defender['user'].display_name} takes a defensive stance! "
                f"(Defense DOUBLED for this turn!)"
            )
        else:
            self.battle_log.append(
                f"🛡️ {defender['user'].display_name} prepares to defend {target['user'].display_name}! "
                f"(Defense DOUBLED for this turn!)"
            )
    
    def check_battle_end(self) -> bool:
        """Check if the battle should end based on the battle mode"""
        if self.battle_over:
            return True
            
        if self.battle_mode == BattleMode.FREE_FOR_ALL:
            # In FFA, battle ends when only one player remains
            alive_players = [p for p in self.players.values() if p['alive']]
            if len(alive_players) <= 1:
                self.battle_over = True
                return True
        else:
            # In team battles, check if any team has been eliminated
            teams_alive = set()
            for player in self.players.values():
                if player['alive']:
                    teams_alive.add(player['team_id'])
            
            # If only one team remains, battle is over
            if len(teams_alive) <= 1:
                self.battle_over = True
                return True
                
        return False
    
    async def end_battle(self):
        """Handle battle conclusion and distribute rewards"""
        # Determine winners and losers based on battle mode
        if self.battle_mode == BattleMode.FREE_FOR_ALL:
            # In FFA, the last player standing wins
            alive_players = [p for p in self.players.values() if p['alive']]
            if alive_players:
                winner = alive_players[0]
                self.battle_log.append(f"🏆 {winner['user'].mention} is the last one standing!")
                winner['xp_earned'] += 100  # Bonus for winning FFA
        else:
            # In team battles, find the winning team(s)
            winning_teams = set()
            for team_id, members in self.teams.items():
                if any(m['alive'] for m in members):
                    winning_teams.add(team_id)
            
            # If it's a draw (shouldn't happen in standard battles)
            if len(winning_teams) > 1:
                self.battle_log.append("⚖️ The battle ended in a draw!")
            elif winning_teams:
                team_name = self.team_names.get(next(iter(winning_teams)), "Unknown Team")
                self.battle_log.append(f"🏆 {team_name} wins the battle!")
                
                # Give bonus XP to winning team
                for player in self.players.values():
                    if player['team_id'] in winning_teams:
                        player['xp_earned'] += 50  # Team win bonus
        
        # Calculate XP and rewards
        xp_rewards = {}
        energon_rewards = {}
        
        # Determine winning team(s)
        winning_teams = set()
        for team_id, members in self.teams.items():
            if any(m['alive'] for m in members):
                winning_teams.add(team_id)
        
        for member_id, player in {**self.team_a, **self.team_b}.items():
            if not player['pet']:
                continue
                
            # Base XP for participation
            xp = 50 + (self.turn_count * 5)
            
            # Bonus for being on winning team
            if member_id in winning_teams:
                xp += 30
                energon_reward = random.randint(25, 75)  # Energon for winners
            else:
                energon_reward = random.randint(10, 30)  # Smaller reward for losers
            
            # Bonus for kills and assists
            xp += player['kills'] * 25
            xp += player['assists'] * 10
            
            # Bonus for damage dealt
            xp += min(50, player['damage_dealt'] // 2)
            
            # Store rewards
            xp_rewards[member_id] = xp
            energon_rewards[member_id] = energon_reward
            player['xp_earned'] = xp
        
        # Apply XP and rewards to pets
        level_ups = []
        for member_id, xp in xp_rewards.items():
            try:
                player = self.get_player(member_id)
                username = player['user'].display_name if player else None
                user_data = await user_data_manager.get_user_data(str(member_id), username)
                if user_data and 'active_pet' in user_data and user_data['active_pet']:
                    pet_id = str(user_data['active_pet'])
                    pet = user_data['pets'][pet_id]
                    
                    # Apply XP
                    pet['experience'] = pet.get('experience', pet.get('xp', 0)) + xp
                    
                    # Update battle statistics
                    if member_id in winning_teams:
                        pet['battles_won'] = pet.get('battles_won', 0) + 1
                    else:
                        pet['battles_lost'] = pet.get('battles_lost', 0) + 1
                    
                    # Add energon reward
                    energon_reward = energon_rewards[member_id]
                    pet['total_battle_energon'] = pet.get('total_battle_energon', 0) + energon_reward
                    
                    # Check for level up using proper pet_levels system
                    old_level = pet.get('level', 1)
                    
                    # Get equipment stats for proper level up calculation
                    equipment_stats = self.calculate_equipment_stats(pet.get('equipment', {}))
                    
                    # Use the proper add_experience function from pet_levels
                    from Systems.EnergonPets.pet_levels import add_experience
                    leveled_up, level_up_details = await add_experience(int(member_id), xp, username, equipment_stats=equipment_stats)
                    
                    if leveled_up and level_up_details:
                        new_level = level_up_details.get('new_level', old_level)
                        level_ups.append((member_id, pet, old_level, new_level, level_up_details))
                    
                    # Save updated pet data
                    await user_data_manager.update_user_data(
                        str(member_id), 
                        {"pets": {pet_id: pet}},
                        "pet_data"
                    )
                    
                    # Also update user's energon
                    user_energon_data = await user_data_manager.get_user_data(str(member_id), username)
                    # Use proper energon tracking method to update total_earned
                    await user_data_manager.add_energon(str(member_id), energon_reward)
                    
            except Exception as e:
                logger.error(f"Error updating pet data for {member_id}: {e}")
        
        # Build result embed
        embed = self.build_battle_embed("🏆 Battle Over!")
        
        # Add XP rewards
        xp_text = []
        for member_id, player in {**self.team_a, **self.team_b}.items():
            if player['xp_earned'] > 0:
                xp_text.append(
                    f"{player['user'].mention}: "
                    f"{player['xp_earned']} XP "
                    f"({player['kills']} kills, {player['assists']} assists, "
                    f"{player['damage_dealt']} damage)"
                )
        
        if xp_text:
            embed.add_field(
                name="XP Rewards",
                value="\n".join(xp_text),
                inline=False
            )
        
        # Send level up embeds
        if level_ups:
            for member_id, pet, old_level, new_level, level_up_details in level_ups:
                player = self.get_player(member_id)
                if player and level_up_details:
                    # Create and send the level up embed
                    from Systems.EnergonPets.pet_levels import create_level_up_embed
                    try:
                        level_up_embed = await create_level_up_embed(pet, level_up_details, int(member_id))
                        await self.ctx.send(embed=level_up_embed)
                    except Exception as e:
                        logger.error(f"Error sending level up embed: {e}")
                        # Fallback to simple text
                        embed.add_field(
                            name="Level Up!",
                            value=f"🎉 {player['user'].mention}'s {pet['name']} leveled up from {old_level} to {new_level}!",
                            inline=False
                        )
        
        # Disable all buttons and update message
        for item in self.children:
            item.disabled = True
        
        await self.message.edit(embed=embed, view=self)
    
    def get_player(self, player_id: str) -> Optional[dict]:
        return self.team_a.get(player_id) or self.team_b.get(player_id)
    
    def build_battle_embed(self, title: str) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            color=discord.Color.blue(),
            description="\n".join(self.battle_log[-5:]) if self.battle_log else "Battle starting..."
        )

        # Add team status
        def format_team_status(team_name: str, team: dict):
            lines = []
            for member_id, data in team.items():
                if not data['alive']:
                    lines.append(f"💀 ~~{data['user'].display_name}~~")
                    continue
                    
                # HP bar
                hp_pct = (data['hp'] / data['max_hp']) * 100
                hp_bar = self._get_hp_bar(hp_pct)
                
                # Status effects
                status = []
                if data['charging']:
                    status.append(f"⚡x{data['charge']:.1f}")
                
                # Guard relationships
                if member_id in self.guard_relationships:
                    target_id = self.guard_relationships[member_id]
                    if target_id == member_id:
                        status.append("🛡️ (Self)")
                    else:
                        target = self.get_player(target_id)
                        if target:
                            status.append(f"🛡️→{target['user'].display_name[:5]}...")
                
                # Count how many people are defending this player
                defender_count = sum(1 for _, tid, _ in self.defending_players if tid == member_id)
                if defender_count > 0:
                    status.append(f"🛡️×{defender_count}")

                line = f"❤️ {hp_bar} {data['hp']}/{data['max_hp']} {data['user'].display_name}"
                if status:
                    line += f" [{' '.join(status)}]"

                # Append last action summary for parity with battle_system spectator UI
                la = data.get('last_action')
                info = data.get('last_action_info', {})
                if la:
                    if la == 'attack':
                        tgt = self.players.get(info.get('target_id'), {}).get('user', None)
                        tgt_name = tgt.display_name if tgt else 'Unknown'
                        dmg = info.get('damage')
                        roll = info.get('roll')
                        res = info.get('result')
                        eff = info.get('effective_multiplier')
                        cm = info.get('charge_multiplier_used')
                        line += f" \n   ⚔️ Last: {dmg} dmg → {tgt_name} • roll {roll} {res} x{eff:.1f}"
                        if cm and cm != 1.0:
                            line += f" • ⚡x{cm:.1f}"
                    elif la == 'defend':
                        prot = self.players.get(info.get('protected_id'), {}).get('user', None)
                        prot_name = prot.display_name if prot else ('self' if info.get('protected_id') == member_id else 'Unknown')
                        parry = info.get('parry_damage', 0)
                        roll = info.get('roll')
                        res = info.get('result')
                        eff = info.get('defense_effectiveness')
                        eff_text = f" x{eff:.1f}" if isinstance(eff, (int, float)) else ""
                        line += f" \n   🛡️ Last: defended {prot_name} • parry {parry} • roll {roll} {res}{eff_text}"
                    elif la == 'charge':
                        cm = info.get('charge_multiplier')
                        line += f" \n   ⚡ Last: charged to x{cm:.1f}"

                lines.append(line)

            return "\n".join(lines) if lines else "No players"
        
        embed.add_field(
            name=f"🔵 Team A ({sum(1 for p in self.team_a.values() if p['alive'])}/{len(self.team_a)} alive)",
            value=format_team_status("Team A", self.team_a),
            inline=True
        )
        
        embed.add_field(
            name=f"🔴 Team B ({sum(1 for p in self.team_b.values() if p['alive'])}/{len(self.team_b)} alive)",
            value=format_team_status("Team B", self.team_b),
            inline=True
        )
        
        # Add turn counter
        embed.set_footer(text=f"Turn {self.turn_count} • React with ⚔️ to join the battle!")
        
        return embed
    
    @staticmethod
    def _get_hp_bar(percentage: float, length: int = 10) -> str:
        filled = '█'
        empty = '░'
        filled_length = int(round(length * percentage / 100))
        return f"{filled * filled_length}{empty * (length - filled_length)}"

class PvPActionView(discord.ui.View):
    """View for players to select actions in PvP battles"""
    
    def __init__(self, battle_view, player_id: str, enemies: Dict[str, dict], 
                 is_ffa: bool = False, is_team_battle: bool = False, allies: Dict[str, dict] = None):
        """
        Initialize the action view
        
        Args:
            battle_view: The parent PvPBattleView
            player_id: ID of the current player
            enemies: Dict of enemy players (id -> player data)
            is_ffa: Whether this is a free-for-all battle
            is_team_battle: Whether this is a team battle
            allies: Dict of ally players (id -> player data) for team battles
        """
        super().__init__(timeout=60)
        self.battle_view = battle_view
        self.player_id = player_id
        self.enemies = enemies
        self.is_ffa = is_ffa
        self.is_team_battle = is_team_battle
        self.allies = allies or {}
        self.message = None  # Store the message for cleanup
        self.add_buttons()
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the intended player can interact with these buttons"""
        if str(interaction.user.id) != self.player_id:
            await interaction.response.send_message("These action buttons aren't for you!", ephemeral=True)
            return False
        return True
    
    def add_buttons(self):
        # Attack button with target selection
        attack_options = []
        
        if self.is_ffa:
            # In FFA, show all other players as potential targets
            attack_options = [
                discord.SelectOption(
                    label=f"{enemy['user'].display_name} (HP: {enemy['hp']}/{enemy['max_hp']})",
                    value=member_id,
                    emoji="🎯"
                )
                for member_id, enemy in self.enemies.items()
                if enemy.get('alive', False)
            ]
        elif self.is_team_battle:
            # In team battles, group targets by team
            team_targets = {}
            for member_id, enemy in self.enemies.items():
                if enemy.get('alive', False):
                    team_id = enemy.get('team_id', 'unknown')
                    if team_id not in team_targets:
                        team_targets[team_id] = []
                    team_targets[team_id].append((member_id, enemy))
            
            # Sort teams to maintain consistent order
            for team_id in sorted(team_targets.keys()):
                # Add a team header
                attack_options.append(
                    discord.SelectOption(
                        label=f"--- Team {team_id.upper()} ---",
                        value=f"team_{team_id}",
                        emoji="🎯",
                        default=False,
                        description=f"Target Team {team_id.upper()}"
                    )
                )
                # Add team members
                for member_id, enemy in team_targets[team_id]:
                    attack_options.append(
                        discord.SelectOption(
                            label=f"  {enemy['user'].display_name} (HP: {enemy['hp']}/{enemy['max_hp']})",
                            value=member_id,
                            emoji="🎯"
                        )
                    )
        
        # Only add attack select if there are valid targets
        if attack_options:
            attack_select = discord.ui.Select(
                placeholder="⚔️ Select target to attack",
                options=attack_options,
                min_values=1,
                max_values=1
            )
            attack_select.callback = self.attack_callback
            self.add_item(attack_select)
        
        # Defend button with target selection
        defend_options = [
            discord.SelectOption(
                label=f"Yourself",
                value="self",
                emoji="🛡️"
            )
        ]
        
        # Add allies for team battles only if there are alive teammates
        if self.is_team_battle and self.allies:
            alive_allies = [
                (member_id, ally) 
                for member_id, ally in self.allies.items() 
                if ally.get('alive', False) and member_id != self.player_id
            ]
            
            if alive_allies:  # Only add ally options if there are alive teammates
                defend_options.append(
                    discord.SelectOption(
                        label="--- Teammates ---",
                        value="team_header",
                        emoji="🛡️",
                        default=False,
                        description="Protect a teammate"
                    )
                )
                
                for member_id, ally in alive_allies:
                    defend_options.append(
                        discord.SelectOption(
                            label=f"  {ally['user'].display_name} (HP: {ally['hp']}/{ally['max_hp']})",
                            value=member_id,
                            emoji="🛡️"
                        )
                    )
        
        defend_select = discord.ui.Select(
            placeholder="🛡️ Select who to defend",
            options=defend_options,
            min_values=1,
            max_values=1
        )
        defend_select.callback = self.defend_callback
        self.add_item(defend_select)

        surrender_button = discord.ui.Button(
            style=discord.ButtonStyle.secondary, 
            label="Surrender", 
            emoji="🏳️",
            row=0
        )
        surrender_button.callback = self.surrender_callback
        self.add_item(surrender_button)

        # Charge button
        charge_button = discord.ui.Button(
            style=discord.ButtonStyle.blurple,
            label="⚡ Charge (2x→4x→8x→16x)",
            custom_id="charge",
            row=1
        )
        charge_button.callback = self.charge_callback
        self.add_item(charge_button)
    
    async def attack_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        target_id = interaction.data['values'][0]
        
        # Clean up the action message immediately
        if self.message:
            try:
                await self.message.delete()
            except:
                pass
        
        # Handle team targeting (if a team was selected instead of a specific player)
        if target_id.startswith('team_'):
            team_id = target_id.split('_', 1)[1]
            # Find all alive enemies in the selected team
            team_enemies = [
                (member_id, enemy) 
                for member_id, enemy in self.enemies.items()
                if enemy.get('alive', False) and enemy.get('team_id') == team_id
            ]
            
            if team_enemies:
                # Select a random enemy from the team
                target_id, target_data = random.choice(team_enemies)
                target_name = f"a member of Team {team_id.upper()} ({target_data['user'].display_name})"
            else:
                await interaction.followup.send("No valid targets in that team!", ephemeral=True)
                return
        else:
            # Handle single target selection
            if target_id not in self.enemies or not self.enemies[target_id].get('alive', False):
                await interaction.followup.send("Invalid target selected!", ephemeral=True)
                return
            target_name = self.enemies[target_id]['user'].display_name
        
        # Apply charge multiplier if charging
        player_data = self.battle_view.players.get(self.player_id, {})
        charge_multiplier = player_data.get('charge', 1.0)
        
        # Clear charge after attacking
        if player_data.get('charging', False):
            player_data['charging'] = False
            charge_text = f" (charged x{charge_multiplier:.1f} damage!)"
        else:
            charge_text = ""
        
        self.battle_view.player_actions[self.player_id] = {
            'action': 'attack',
            'target': target_id,
            'charge_multiplier': charge_multiplier
        }
        
        # No confirmation message - action is recorded silently
        await self.battle_view.check_turn_completion()
    
    async def defend_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        target_id = interaction.data['values'][0]
        
        # Clean up the action message immediately
        if self.message:
            try:
                await self.message.delete()
            except:
                pass
        
        # Handle team header selection (shouldn't be selectable, but just in case)
        if target_id == "team_header":
            await interaction.followup.send("Please select a specific teammate to defend.", ephemeral=True)
            return
            
        if target_id == "self":
            target_id = self.player_id
            target_name = "yourself"
            defense_bonus = 0.5  # 50% damage reduction when defending self
        else:
            # Check if target is a valid ally and alive
            if target_id not in self.allies or not self.allies[target_id].get('alive', False):
                await interaction.followup.send("You can only defend alive teammates!", ephemeral=True)
                return
                
            # In team battles, only allow defending teammates
            if self.is_team_battle:
                defender_team = self.battle_view.players.get(self.player_id, {}).get('team_id')
                target_team = self.allies[target_id].get('team_id')
                
                if defender_team != target_team:
                    await interaction.followup.send("You can only defend your teammates!", ephemeral=True)
                    return
            
            target_name = self.allies[target_id]['user'].display_name
            defense_bonus = 0.3  # 30% damage reduction when defending others
        
        # Set up defense state
        self.battle_view.player_actions[self.player_id] = {
            'action': 'defend',
            'target': target_id,
            'defense_bonus': defense_bonus,
            'counter_attack': True  # Enable counter-attack for the next turn
        }
        
        # Clear any existing guard relationships for this player
        for guarder_id, guarded_id in list(self.battle_view.guard_relationships.items()):
            if guarder_id == self.player_id:
                del self.battle_view.guard_relationships[guarder_id]
        
        # Set up guard relationship for counter-attacks
        self.battle_view.guard_relationships[self.player_id] = target_id
        
        # No confirmation message - action is recorded silently
        await self.battle_view.check_turn_completion()

    async def on_timeout(self):
        # Default to attack a random target if player doesn't choose
        if self.player_id not in self.battle_view.player_actions:
            alive_enemies = [mid for mid, e in self.enemies.items() if e['alive']]
            if alive_enemies:
                target_id = random.choice(alive_enemies)
                self.battle_view.player_actions[self.player_id] = {
                    'action': 'attack',
                    'target': target_id
                }
                await self.battle_view.check_all_actions_ready()
    
    async def surrender_callback(self, interaction: discord.Interaction):
        """Handle surrender button click"""
        if str(interaction.user.id) != self.player_id:
            return await interaction.response.send_message("This isn't your battle!", ephemeral=True)
            
        # Clean up the action message
        if self.message:
            try:
                await self.message.delete()
            except:
                pass
        
        # Mark player as defeated
        player_data = self.battle_view.players.get(self.player_id)
        if not player_data:
            return await interaction.response.send_message("You're not in this battle!", ephemeral=True)
        
        # Set player as defeated
        player_data['alive'] = False
        player_data['hp'] = 0
        
        # Add to battle log
        self.battle_view.battle_log.append(f"🏳️ {interaction.user.display_name} has surrendered!")
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        # Update the message
        await interaction.response.edit_message(view=self)
        
        # Check if battle should end
        if self.battle_view.check_battle_end():
            await self.battle_view.end_battle()
        else:
            await self.battle_view.update_battle_embed()

    async def charge_callback(self, interaction: discord.Interaction):
        """Handle charge button click"""
        if str(interaction.user.id) != self.player_id:
            return await interaction.response.send_message("This isn't your battle!", ephemeral=True)
            
        # Clean up the action message immediately
        if self.message:
            try:
                await self.message.delete()
            except:
                pass
        
        player_data = self.battle_view.players.get(self.player_id)
        if not player_data:
            return await interaction.response.send_message("You're not in this battle!", ephemeral=True)
        
        # Set charging state using proper progression system
        player_data['charging'] = True
        current_charge = player_data.get('charge', 1.0)
        new_charge = DamageCalculator.get_next_charge_multiplier(current_charge)
        player_data['charge'] = new_charge
        
        # Add to battle log
        self.battle_view.battle_log.append(f"⚡ {interaction.user.display_name} is charging up a powerful attack! (Charge: x{new_charge})")
        
        # Disable charge button after use
        for item in self.children:
            if getattr(item, 'custom_id', None) == 'charge':
                item.disabled = True
                break
        
        # Update the message
        await interaction.response.edit_message(view=self)
        
        # Mark action as complete
        self.battle_view.player_actions[self.player_id] = {
            'action': 'charge',
            'target': self.player_id
        }
        
        await self.battle_view.check_turn_completion()

async def setup(bot):
    # This function will be called by the bot's setup_hook
    pass
