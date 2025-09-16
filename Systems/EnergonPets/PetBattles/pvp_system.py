import discord
import random
import asyncio
import logging
import json
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from enum import Enum, auto
from collections import defaultdict
from Systems.EnergonPets import user_data_manager
from Systems.EnergonPets.pet_levels import calculate_xp_gain, create_level_up_embed

logger = logging.getLogger('pvp_system')

class BattleMode(Enum):
    ONE_VS_ONE = auto()
    TEAM_2V2 = auto()
    TEAM_3V3 = auto()
    TEAM_4V4 = auto()
    FREE_FOR_ALL = auto()

class PvPBattleView(discord.ui.View):
    """View for PvP battles between players"""
    
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
        
        # Load team names from JSON as fallback
        with open('Systems/Data/pets_level.json', 'r') as f:
            pet_data = json.load(f)
            default_team_names = pet_data.get('TEAM_NAMES', [])
        
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
                    'attack': 10, 'defense': 5, 'speed': 5,
                    'charge': 1.0, 'charging': False,
                    'pet': None, 'alive': True,
                    'xp_earned': 0, 'damage_dealt': 0,
                    'damage_taken': 0, 'kills': 0, 'assists': 0
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
            
            # Set up turn order based on speed
            self.turn_order = [
                p for p in self.players.values() 
                if p['alive']
            ]
            self.turn_order.sort(key=lambda x: x['speed'], reverse=True)
            
            await self.start_battle()
        except Exception as e:
            logger.error(f"Battle init error: {e}", exc_info=True)
            if self.message:
                await self.message.edit(content=f"❌ Error: {str(e)}", view=None)
    
    async def _load_pet_data(self, player_id: str, player_data: dict):
        """Load pet data for a single player"""
        try:
            user_data = await user_data_manager.get_user_data(int(player_id), "pet_data")
            if user_data and 'active_pet' in user_data and user_data['active_pet']:
                pet = user_data['pets'][str(user_data['active_pet'])]
                player_data.update({
                    'pet': pet,
                    'hp': pet.get('hp', 100),
                    'max_hp': pet.get('max_hp', 100),
                    'attack': pet.get('attack', 10),
                    'defense': pet.get('defense', 5),
                    'speed': pet.get('speed', 5)
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
                            msg = await self.ctx.send(
                                f"{player['user'].mention} it's your turn to act! (FFA)", 
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
                                msg = await self.ctx.send(
                                    f"{member.mention} it's your turn to act!", 
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
        """Process all actions for the current turn in initiative order"""
        # Process actions in initiative order (based on speed)
        initiative_order = sorted(
            [p_id for p_id, p in self.players.items() if p['alive']],
            key=lambda x: self.players[x]['speed'],
            reverse=True
        )
        
        # Process all actions in order
        for player_id in initiative_order:
            if player_id in self.player_actions and self.players[player_id]['alive']:
                action_data = self.player_actions[player_id]
                await self.process_action(player_id, action_data)
                
                # Update battle log after each action
                if len(self.battle_log) > 0:
                    embed = self.build_battle_embed(f"🎬 Round {self.turn_count} - Action in Progress")
                    log_text = "\n".join(self.battle_log[-3:])  # Show last 3 log entries
                    embed.add_field(name="Latest Actions", value=log_text, inline=False)
                    await self.message.edit(embed=embed)
                
                # Small delay between actions for better readability
                await asyncio.sleep(2)
        
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
        
        # Start next turn if battle is still going
        if not self.battle_over:
            await self.start_turn()
    
    async def process_action(self, player_id: str, action_data: dict):
        """Process a single player's action with enhanced battle mechanics"""
        if player_id not in self.players or not self.players[player_id]['alive']:
            return  # Skip if player is no longer alive
            
        player = self.players[player_id]
        action = action_data['action']
        target_id = action_data.get('target')
        
        # Check if target is still valid
        if target_id and (target_id not in self.players or not self.players[target_id]['alive']):
            # Target is no longer valid, find a new target or skip
            if action == 'attack':
                # Find another living target (excluding self)
                alive_targets = [p_id for p_id, p in self.players.items() 
                               if p['alive'] and p_id != player_id]
                if alive_targets:
                    target_id = random.choice(alive_targets)
                    action_data['target'] = target_id
                else:
                    self.battle_log.append(f"{player['user'].display_name} has no valid targets!")
                    return
            elif action == 'defend':
                # Default to self-defense if target is invalid
                target_id = player_id
                action_data['target'] = target_id
        
        # Process the action
        if action == 'attack' and target_id:
            await self.process_attack(player_id, target_id)
        elif action == 'defend' and target_id:
            await self.process_defend(player_id, target_id)
        elif action == 'charge':
            # Increase charge multiplier (capped at 3.0x)
            player['charge'] = min(3.0, player.get('charge', 1.0) * 1.5)
            self.battle_log.append(
                f"⚡ {player['user'].display_name} charges up! "
                f"(Power: {player['charge']:.1f}x)"
            )
    
    async def process_attack(self, attacker_id: str, target_id: str):
        """Process an attack from one player to another with enhanced mechanics"""
        if (attacker_id not in self.players or not self.players[attacker_id]['alive'] or
            target_id not in self.players or not self.players[target_id]['alive']):
            return  # Skip if attacker or target is invalid
            
        attacker = self.players[attacker_id]
        target = self.players[target_id]
        
        # Check for guard/counter-attack
        guard_target = self.guard_relationships.get(target_id)
        if guard_target and guard_target != attacker_id:
            # The attack is being guarded, redirect to the defender
            guard = self.players[guard_target]
            if guard['alive']:
                self.battle_log.append(
                    f"🛡️ {guard['user'].display_name} intercepts the attack "
                    f"for {target['user'].display_name}!"
                )
                target = guard
                target_id = guard_target
        
        # Calculate damage with charge multiplier
        charge_multiplier = attacker.get('charge', 1.0)
        base_damage = max(1, attacker['attack'] - target['defense'] // 2)
        damage = int(base_damage * charge_multiplier)
        
        # Check for critical hit (5% chance)
        is_critical = random.random() < 0.05
        if is_critical:
            damage = int(damage * 1.5)
        
        # Apply damage reduction from defense bonus
        defense_bonus = target.get('defense_bonus', 0)
        if defense_bonus > 0:
            damage_reduction = int(damage * defense_bonus)
            damage = max(1, damage - damage_reduction)
        
        # Apply damage
        target['hp'] = max(0, target['hp'] - damage)
        
        # Update damage stats
        attacker['damage_dealt'] += damage
        target['damage_taken'] += damage
        
        # Add to battle log
        crit_text = "💥 CRITICAL HIT! " if is_critical else ""
        charge_text = f" (Charged x{charge_multiplier:.1f}!)" if charge_multiplier > 1.0 else ""
        defense_text = f" (Reduced by {defense_bonus*100:.0f}% defense!)" if defense_bonus > 0 else ""
        
        self.battle_log.append(
            f"{crit_text}⚔️ {attacker['user'].display_name} attacks {target['user'].display_name} "
            f"for {damage} damage!{charge_text}{defense_text}"
        )
        
        # Check for defeat
        if target['hp'] <= 0:
            target['alive'] = False
            self.battle_log.append(f"💀 {target['user'].display_name} has been defeated!")
            
            # Award XP and track kills
            if attacker_id in self.players:
                xp_gain = 50 + (target.get('level', 1) * 5)
                self.players[attacker_id]['xp_earned'] += xp_gain
                self.players[attacker_id]['kills'] += 1
                
                # Check for level up
                if self.players[attacker_id]['xp_earned'] >= self.players[attacker_id].get('xp_to_next_level', 100):
                    await self.level_up_player(attacker_id)
        
        # Reset charge after attacking
        attacker['charge'] = 1.0
        
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
        
        # Add defense bonus (reduces damage taken by 25%)
        defender['defense_bonus'] = 0.25
        
        # Store base defense if not already stored
        if 'base_defense' not in defender:
            defender['base_defense'] = defender['defense']
            
        # Add temporary defense boost (lasts until next turn)
        defender['defense'] = int(defender['base_defense'] * 1.25)
        
        # Add to defending players set for this turn
        self.defending_players.add((defender_id, target_id, 1))  # 1 = defense boost level
        
        # Add to battle log
        if target_id == defender_id:
            self.battle_log.append(
                f"🛡️ {defender['user'].display_name} takes a defensive stance! "
                f"(Defense +25% for this turn!)"
            )
        else:
            self.battle_log.append(
                f"🛡️ {defender['user'].display_name} prepares to defend {target['user'].display_name}! "
                f"(Defense +25% for this turn!)"
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
        for member_id, player in {**self.team_a, **self.team_b}.items():
            if not player['pet']:
                continue
                
            # Base XP for participation
            xp = 50 + (self.turn_count * 5)
            
            # Bonus for being on winning team
            if member_id in winning_team:
                xp += 30
            
            # Bonus for kills and assists
            xp += player['kills'] * 25
            xp += player['assists'] * 10
            
            # Bonus for damage dealt
            xp += min(50, player['damage_dealt'] // 2)
            
            # Store XP reward
            xp_rewards[member_id] = xp
            player['xp_earned'] = xp
        
        # Apply XP to pets
        level_ups = []
        for member_id, xp in xp_rewards.items():
            try:
                user_data = await user_data_manager.get_user_data(int(member_id), "pet_data")
                if user_data and 'active_pet' in user_data and user_data['active_pet']:
                    pet_id = str(user_data['active_pet'])
                    pet = user_data['pets'][pet_id]
                    
                    # Apply XP
                    pet['xp'] = pet.get('xp', 0) + xp
                    
                    # Check for level up
                    old_level = pet.get('level', 1)
                    new_level = await user_data_manager.calculate_pet_level(pet)
                    
                    if new_level > old_level:
                        level_ups.append((member_id, pet, old_level, new_level))
                    
                    # Save updated pet data
                    await user_data_manager.update_user_data(
                        int(member_id), 
                        {"pets": {pet_id: pet}},
                        "pet_data"
                    )
            except Exception as e:
                logger.error(f"Error updating pet XP for {member_id}: {e}")
        
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
        
        # Add level up messages
        if level_ups:
            level_text = []
            for member_id, pet, old_level, new_level in level_ups:
                player = self.get_player(member_id)
                if player:
                    level_text.append(
                        f"🎉 {player['user'].mention}'s {pet['name']} "
                        f"leveled up from {old_level} to {new_level}!"
                    )
            
            if level_text:
                embed.add_field(
                    name="Level Ups!",
                    value="\n".join(level_text),
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
            label="⚡ Charge (x1.5 next attack)",
            custom_id="charge",
            row=1
        )
        charge_button.callback = self.charge_callback
        self.add_item(charge_button)
    
    async def attack_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        target_id = interaction.data['values'][0]
        
        # Clean up the action message
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
        
        await interaction.followup.send(
            f"You will attack {target_name}{charge_text}", 
            ephemeral=True
        )
        await self.battle_view.check_turn_completion()
    
    async def defend_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        target_id = interaction.data['values'][0]
        
        # Clean up the action message
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
        
        await interaction.followup.send(
            f"🛡️ You will defend {target_name}! "
            f"You'll take {int((1 - defense_bonus) * 100)}% of damage for them "
            f"and counter-attack their next attacker!",
            ephemeral=True
        )
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
            
        # Clean up the action message
        if self.message:
            try:
                await self.message.delete()
            except:
                pass
        
        player_data = self.battle_view.players.get(self.player_id)
        if not player_data:
            return await interaction.response.send_message("You're not in this battle!", ephemeral=True)
        
        # Set charging state
        player_data['charging'] = True
        player_data['charge'] = 2.0  # Double damage on next attack
        
        # Add to battle log
        self.battle_view.battle_log.append(f"⚡ {interaction.user.display_name} is charging up a powerful attack!")
        
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
