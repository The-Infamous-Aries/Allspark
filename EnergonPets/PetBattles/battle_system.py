import discord
import random
import asyncio
import logging
import json
import os
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from Systems.user_data_manager import user_data_manager
from Systems.EnergonPets.PetBattles.damage_calculator import DamageCalculator

logger = logging.getLogger('battle_system')

MONSTER_EMOJIS = {
    "monster": "🤖",
    "boss": "👹", 
    "titan": "👑"
}
RARITY_EMOJIS = {
    "common": "⚪",
    "uncommon": "🟢",
    "rare": "🔵",
    "epic": "🟣",
    "legendary": "🟠",
    "mythic": "🔴"
}

class GroupBattleJoinView(discord.ui.View):
    """View for group battle joining with join/leave buttons"""
    
    def __init__(self, ctx, battle_view):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.battle_view = battle_view
        self.message = None
        self.channel_message = None  # Track the main channel message
        asyncio.create_task(self.add_participant(ctx.author))
    
    async def add_participant(self, user):
        """Add a participant to the battle"""
        try:
            pet = await user_data_manager.get_pet_data(str(user.id), user.display_name)
            if pet:
                self.battle_view.participants.append((user, pet))
                await self.refresh_channel_embed()
        except Exception as e:
            logger.error(f"Error adding participant: {e}")
    
    async def refresh_channel_embed(self):
        """Refresh the main channel embed with join buttons"""
        if self.channel_message:
            try:
                embed = self.battle_view.build_join_embed()
                # Keep the join buttons visible under the embed
                await self.channel_message.edit(embed=embed, view=self)
            except Exception as e:
                logger.error(f"Error refreshing channel embed: {e}")
    
    @discord.ui.button(label="Join Battle", style=discord.ButtonStyle.green, emoji="⚔️")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle user joining the battle"""
        if len(self.battle_view.participants) >= self.battle_view.max_participants:
            await interaction.response.send_message("❌ Battle is full!", delete_after=5)
            return
        for user, _ in self.battle_view.participants:
            if user.id == interaction.user.id:
                await interaction.response.send_message("❌ You're already in this battle!", delete_after=5)
                return        
        try:
            pet = await user_data_manager.get_pet_data(str(interaction.user.id), interaction.user.display_name)
            if not pet:
                await interaction.response.send_message("❌ You don't have a pet! Use `/get_pet` to get one.", delete_after=10)
                return
            self.battle_view.participants.append((interaction.user, pet))
            await self.refresh_channel_embed()
            await interaction.response.send_message("✅ Joined the battle!", delete_after=3)           
        except Exception as e:
            logger.error(f"Error joining battle: {e}")
            await interaction.response.send_message("❌ Error joining battle. Please try again.", delete_after=5)    

    @discord.ui.button(label="Leave Battle", style=discord.ButtonStyle.red, emoji="🚪")
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle user leaving the battle"""
        for i, (user, _) in enumerate(self.battle_view.participants):
            if user.id == interaction.user.id:
                self.battle_view.participants.pop(i)
                await self.refresh_channel_embed()
                await interaction.response.send_message("✅ Left the battle!", delete_after=3)
                return        
        await interaction.response.send_message("❌ You're not in this battle!", delete_after=5)   

    @discord.ui.button(label="Start Battle", style=discord.ButtonStyle.blurple, emoji="🚀")
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle battle start (only creator can start)"""
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Only the battle creator can start!", delete_after=5)
            return           
        if len(self.battle_view.participants) < 1:
            await interaction.response.send_message("❌ Need at least 1 participant!", delete_after=5)
            return
        await interaction.response.send_message("🚀 Starting battle...", delete_after=2)
        
        # Remove join buttons and start battle
        self.battle_view.battle_started = True
        spectator_embed = self.battle_view.build_spectator_embed("Battle started! Good luck!")
        await self.channel_message.edit(embed=spectator_embed, view=None)
        self.battle_view.message = self.channel_message
        self.battle_view.interaction = interaction
        await self.battle_view.start_action_collection()


class ResendActionView(discord.ui.View):
    """View with blue button to resend action buttons"""
    
    def __init__(self, battle_view):
        super().__init__(timeout=60)
        self.battle_view = battle_view
    
    @discord.ui.button(label="Resend My Actions", style=discord.ButtonStyle.blurple, emoji="🔄")
    async def resend_actions_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Resend action buttons to the user"""
        user_id = interaction.user.id
        
        # Check if user is in the battle and alive
        if user_id not in self.battle_view.player_data:
            await interaction.response.send_message("❌ You're not in this battle!", ephemeral=True, delete_after=3)
            return
            
        player_data = self.battle_view.player_data[user_id]
        if not player_data['alive'] or player_data['hp'] <= 0:
            await interaction.response.send_message("❌ You're not alive in this battle!", ephemeral=True, delete_after=3)
            return
            
        # Check if user already submitted an action
        if user_id in self.battle_view.player_actions:
            await interaction.response.send_message("✅ You've already chosen your action!", ephemeral=True, delete_after=3)
            return
        
        # Send or update action buttons
        try:
            action_view = EphemeralActionView(self.battle_view, user_id)
            embed = discord.Embed(
                title="⚔️ Battle Action Required",
                description=f"**{player_data['pet']['name']}** - Round {self.battle_view.turn_count + 1}\nChoose your action:",
                color=0x00ff00
            )
            
            # Check if we have an existing ephemeral message for this user
            if user_id in self.battle_view.ephemeral_messages:
                try:
                    # Try to edit the existing message
                    await self.battle_view.ephemeral_messages[user_id].edit(embed=embed, view=action_view)
                    await interaction.response.send_message("✅ Action buttons resent!", ephemeral=True, delete_after=3)
                    return
                except discord.NotFound:
                    # Message was deleted, remove from cache and create new one
                    del self.battle_view.ephemeral_messages[user_id]
                except Exception as e:
                    logger.debug(f"Error editing existing ephemeral message for user {user_id}: {e}")
                    # Fall through to create new message
            
            # Send new ephemeral message and store reference
            msg = await interaction.response.send_message(
                embed=embed,
                view=action_view,
                ephemeral=True
            )
            self.battle_view.ephemeral_messages[user_id] = msg
            
        except Exception as e:
            logger.error(f"Error resending action buttons to user {user_id}: {e}")
            await interaction.response.send_message("❌ Error sending action buttons. Please try again.", ephemeral=True, delete_after=5)


class UnifiedBattleView(discord.ui.View):
    """Main battle view for handling all battle types"""

    def __init__(self, ctx, battle_type="solo", participants=None, monster=None, 
                 selected_enemy_type=None, selected_rarity=None):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.battle_type = battle_type
        self.selected_enemy_type = selected_enemy_type
        self.selected_rarity = selected_rarity
        self.message = None
        self.participants = participants or []
        self.monster = monster
        self.player_data = {}
        self.monster_hp = 0
        self.max_monster_hp = 0
        self.monster_charge_multiplier = 1.0
        self.monster_defending = False
        self.current_turn_index = 0
        self.turn_count = 0
        self.battle_started = False
        self.battle_over = False
        self.battle_log = []
        self.join_mode = battle_type == "group"
        self.max_participants = 4
        self.defending_players = set()
        self.group_defense_active = False  
        self.group_defender = None 
        self.player_actions = {}
        self.waiting_for_actions = False
        self.round_actions = {}
        self.spectator_embed = None
        self.spectator_message = None  
        self.rewards = {}
        self.ephemeral_messages = {}  # Store ephemeral message references for reuse
        
        # Guard relationships - maps defender_id to the user_id they're protecting
        self.guard_relationships = {}
        
        # Damage tracking for final summary
        self.total_damage_dealt = {}
        self.total_damage_received = {}
        self.total_monster_damage_dealt = 0
        self.total_monster_damage_received = 0
        
        # Initialize damage calculator
        self.damage_calculator = DamageCalculator()
 
    @classmethod
    async def create_async(cls, ctx, battle_type="solo", participants=None, 
                          selected_enemy_type=None, selected_rarity=None, 
                          interaction=None):
        """Async factory method to create battle with loaded data"""
        view = cls(ctx, battle_type, participants, None, selected_enemy_type, selected_rarity)
        view.interaction = interaction
        
        # Set defaults
        selected_enemy_type = selected_enemy_type or "monster"
        selected_rarity = selected_rarity or "common"
        
        # Load participants with batch operations
        user_ids = []
        if battle_type == "solo":
            user_ids = [str(ctx.author.id)]
        elif battle_type == "group":
            if participants:
                user_ids = [str(user.id) for user, _ in participants]
            else:
                user_ids = [str(ctx.author.id)]
        
        # Batch load user data
        user_data_batch = await user_data_manager.batch_load_user_data(user_ids)
        
        # Create participants list
        view.participants = []
        for i, user_id in enumerate(user_ids):
            user = ctx.author if user_id == str(ctx.author.id) else (participants[i][0] if participants else ctx.author)
            user_data = user_data_batch.get(user_id, {})
            pet = user_data.get('pets', {}).get('pet_data') or {
                'name': 'Default Pet', 'attack': 10, 'defense': 5, 'energy': 100,
                'maintenance': 0, 'happiness': 0, 'level': 1, 'equipment': {}
            }
            view.participants.append((user, pet))
        
        # Load monster
        view.monster = await view.get_monster_by_type_and_rarity(selected_enemy_type, selected_rarity)
        if not view.monster:
            view.monster = view._create_fallback_monster(selected_enemy_type, selected_rarity)
        
        if view.monster:
            view.monster_hp = view.monster['health']
            view.max_monster_hp = view.monster['health']
            
        view.initialize_battle_data()
        return view

    async def get_monster_by_type_and_rarity(self, enemy_type: str, rarity: str) -> Dict[str, Any]:
        """Get monster data from user_data_manager with optimized loading"""
        try:
            data = await user_data_manager.get_monsters_and_bosses()
            filtered = []
            
            # Process all monster types in one loop
            for container_key in ['monsters', 'bosses', 'titans']:
                container = data.get(container_key, {})
                # Handle nested structure
                actual_data = container.get(container_key, container) if isinstance(container, dict) and container_key in container else container
                
                if isinstance(actual_data, dict):
                    for entity_data in actual_data.values():
                        if (isinstance(entity_data, dict) and 
                            str(entity_data.get('type', '')).lower() == enemy_type.lower() and 
                            str(entity_data.get('rarity', '')).lower() == rarity.lower()):
                            filtered.append(entity_data)
            
            if filtered:
                monster = random.choice(filtered)
                return {
                    "name": str(monster.get('name', f'{rarity.title()} {enemy_type.title()}')),
                    "health": int(monster.get('health', 100)),
                    "attack": int(monster.get('attack', 10)),
                    "defense": int(monster.get('defense', 5)),
                    "type": str(monster.get('type', enemy_type)),
                    "rarity": str(monster.get('rarity', rarity)),
                    "loot": monster.get('loot', [])
                }
                
        except Exception as e:
            logger.error(f"Error loading monster: {e}")
            
        return self._create_fallback_monster(enemy_type, rarity)

    def _create_fallback_monster(self, enemy_type: str, rarity: str) -> Dict[str, Any]:
        """Create fallback monster when data loading fails"""
        base_stats = {
            "common": {"health": 100, "attack": 8, "defense": 5},
            "uncommon": {"health": 150, "attack": 12, "defense": 8},
            "rare": {"health": 200, "attack": 16, "defense": 10},
            "epic": {"health": 300, "attack": 22, "defense": 15},
            "legendary": {"health": 400, "attack": 28, "defense": 20},
            "mythic": {"health": 500, "attack": 35, "defense": 25}
        }       
        stats = base_stats.get(rarity, base_stats["common"])        
        return {
            "name": f"{rarity.title()} {enemy_type.title()}",
            "health": stats["health"],
            "attack": stats["attack"],
            "defense": stats["defense"],
            "type": enemy_type,
            "rarity": rarity
        }
  
    def initialize_battle_data(self):
        """Initialize battle data for all participants"""
        for user, pet in self.participants:
            if pet:
                base_attack = pet.get('attack', 10)
                base_defense = pet.get('defense', 5)
                # Use current stats for battle calculations
                current_energy = pet.get('energy', 100)
                current_maintenance = pet.get('maintenance', 100)
                current_happiness = pet.get('happiness', 100)
                equipment = pet.get('equipment', {})
                equipment_stats = self.calculate_equipment_stats(equipment)        
                total_attack = base_attack + equipment_stats['attack']
                total_defense = base_defense + equipment_stats['defense']
                
                # Calculate max stats for reference (with equipment bonuses)
                base_max_energy = pet.get('max_energy', 100)
                base_max_maintenance = pet.get('max_maintenance', 100)
                base_max_happiness = pet.get('max_happiness', 100)
                total_max_energy = base_max_energy + equipment_stats['energy']
                total_max_maintenance = base_max_maintenance + equipment_stats['maintenance']
                total_max_happiness = base_max_happiness + equipment_stats['happiness']             
                max_hp = total_max_energy + total_max_maintenance + total_max_happiness
                
                # Use current stats for actual HP
                current_hp = current_energy + current_maintenance + current_happiness
                
                self.player_data[user.id] = {
                    'user': user,
                    'pet': pet,
                    'hp': current_hp,
                    'max_hp': max_hp,
                    'charge': 1.0,
                    'charging': False,
                    'alive': True,
                    'last_action': None,
                    'total_attack': total_attack,
                    'total_defense': total_defense
                }
                
                # Initialize damage tracking
                self.total_damage_dealt[user.id] = 0
                self.total_damage_received[user.id] = 0
                
        if self.monster:
            self.monster_hp = self.monster['health']
            self.max_monster_hp = self.monster['health']
            self.total_monster_damage_dealt = 0
            self.total_monster_damage_received = 0
  
    def create_hp_bar(self, current: int, max_hp: int, bar_type: str = "default", pet=None) -> str:
        """Create visual HP bar"""
        percentage = max(0, min(100, (current / max_hp) * 100))
        filled = int(percentage // 10)
        empty = 10 - filled       
        if bar_type == "pet" and pet:
            faction = pet.get('faction', '').lower()
            if faction == 'decepticon':
                filled_char, empty_char = "🟪", "⬛"
            elif faction == 'autobot':
                filled_char, empty_char = "🟥", "⬛"
            else:
                filled_char, empty_char = "🟩", "⬛"
        elif bar_type == "enemy":
            filled_char, empty_char = "🟨", "⬛"
        else:
            filled_char, empty_char = "█", "░"      
        bar = filled_char * filled + empty_char * empty
        return f"[{bar}] {current}/{max_hp} ({percentage:.0f}%)"
  
    def get_current_player(self):
        """Get current player's turn"""
        alive_players = [pid for pid, data in self.player_data.items() if data['alive']]
        if not alive_players:
            return None       
        current_id = alive_players[self.current_turn_index % len(alive_players)]
        return self.player_data[current_id]
 
    async def start_action_collection(self):
        """Start action collection - send ephemeral action buttons to each player"""
        self.waiting_for_actions = True
        self.player_actions.clear()
        
        # Create resend view for the main battle embed
        resend_view = ResendActionView(self)
        
        # Update the main battle message with resend button attached
        waiting_embed = self.build_spectator_embed("⏳ Waiting for players to choose actions...")
        try:
            await self.message.edit(embed=waiting_embed, view=resend_view)
        except discord.NotFound:
            logger.warning("Main battle message not found during action collection")
        except discord.HTTPException as e:
            logger.error(f"Error updating main battle message: {e}")
        
        # Send ephemeral action messages to each alive player
        if hasattr(self, 'interaction') and self.interaction:
            for user_id, player_data in self.player_data.items():
                if player_data['alive'] and player_data['hp'] > 0:
                    try:
                        action_view = EphemeralActionView(self, user_id)
                        
                        # Create the action embed
                        embed = discord.Embed(
                            title="⚔️ Battle Action Required",
                            description=f"**{player_data['pet']['name']}** - Round {self.turn_count + 1}\nChoose your action:",
                            color=0x00ff00
                        )
                        
                        # Check if we have an existing ephemeral message for this user
                        if user_id in self.ephemeral_messages:
                            try:
                                # Try to edit the existing message
                                await self.ephemeral_messages[user_id].edit(embed=embed, view=action_view)
                                continue
                            except discord.NotFound:
                                # Message was deleted, remove from cache and create new one
                                del self.ephemeral_messages[user_id]
                            except Exception as e:
                                logger.debug(f"Error editing existing ephemeral message for user {user_id}: {e}")
                                # Fall through to create new message
                        
                        # Send new ephemeral message and store reference
                        msg = await self.interaction.followup.send(
                            embed=embed,
                            view=action_view,
                            ephemeral=True
                        )
                        self.ephemeral_messages[user_id] = msg
                        
                    except Exception as e:
                        logger.error(f"Error sending action message to user {user_id}: {e}")
        else:
            logger.warning("No interaction context available for sending action messages")
        
        return True
 
    async def check_all_actions_submitted(self):
        """Check if all players have submitted actions"""
        if not self.waiting_for_actions:
            return            
        alive_players = [uid for uid, data in self.player_data.items() if data['alive'] and data['hp'] > 0]      
        if len(self.player_actions) == len(alive_players):
            self.waiting_for_actions = False
            
            # No need to clean up ephemeral messages - they auto-delete
            
            # Process the round
            if self.battle_type in ["solo", "group"] and self.monster:
                monster_action = self.get_monster_action()
                await self.process_combat_round(monster_action)
            else:
                await self.process_round()

    async def process_combat_round(self, monster_action: str):
        """Process a complete combat round with all player actions and monster action using new roll-based system"""
        
        # Initialize defense results storage
        self.defense_results = {}
        
        # Process player actions
        for player_id, action_data in self.player_actions.items():
            if player_id not in self.player_data or not self.player_data[player_id]['alive']:
                continue
                
            action = action_data['action']
            player_data = self.player_data[player_id]
            player_name = player_data['user'].display_name
            
            if action == "attack":
                # Use new roll-based attack system
                battle_result = DamageCalculator.calculate_battle_action(
                    attacker_attack=player_data['total_attack'],
                    target_defense=self.monster['defense'],
                    charge_multiplier=player_data.get('charge_multiplier', 1.0),
                    target_charge_multiplier=self.monster_charge_multiplier if self.monster_defending else 1.0,
                    action_type="attack"
                )
                
                # Apply damage to monster
                self.monster_hp = max(0, self.monster_hp - battle_result['final_damage'])
                self.total_damage_dealt[player_id] += battle_result['final_damage']
                self.total_monster_damage_received += battle_result['final_damage']
                
                # Add roll result to battle log
                if battle_result['attack_result'] == "miss":
                    self.battle_log.append(f"⚔️ {player_name} attacks but misses completely! (Roll: {battle_result['attack_roll']})")
                else:
                    charge_text = f" (Charged x{player_data.get('charge_multiplier', 1.0)}!)" if player_data.get('charge_multiplier', 1.0) > 1.0 else ""
                    # Calculate roll multiplier based on attack result type
                    roll_multiplier = self._get_roll_multiplier_from_result(battle_result['attack_result'], battle_result['attack_roll'])
                    self.battle_log.append(f"⚔️ {player_name} attacks for {battle_result['final_damage']} damage! (Roll: {battle_result['attack_roll']}, Result: {battle_result['attack_result']}){charge_text}")
                
                # Reset charge after attack
                player_data['charge_multiplier'] = 1.0
                if 'charge' in player_data:
                    player_data['charge'] = 1.0
                
            elif action == "defend":
                # Use new roll-based defend system
                target_id = action_data.get('target', player_id)
                
                battle_result = DamageCalculator.calculate_battle_action(
                    attacker_attack=player_data['total_defense'],
                    target_defense=0,  # Defense doesn't have an opposing stat
                    charge_multiplier=player_data.get('charge_multiplier', 1.0),
                    action_type="defend"
                )
                
                # Store defense information with roll result
                self.defending_players.add((player_id, target_id, battle_result['final_damage']))
                self.guard_relationships[player_id] = target_id
                self.defense_results[player_id] = battle_result
                
                # Add roll result to battle log
                target_name = self.player_data[target_id]['user'].display_name if target_id in self.player_data else "themselves"
                
                if battle_result['attack_result'] == "miss":
                    self.battle_log.append(f"🛡️ {player_name} tries to defend {target_name} but fails! (Roll: {battle_result['attack_roll']})")
                else:
                    charge_text = f" (Charged x{player_data.get('charge_multiplier', 1.0)}!)" if player_data.get('charge_multiplier', 1.0) > 1.0 else ""
                    roll_multiplier = self._get_roll_multiplier_from_result(battle_result['attack_result'], battle_result['attack_roll'])
                    self.battle_log.append(f"🛡️ {player_name} defends {target_name} with {roll_multiplier:.2f}x effectiveness! (Roll: {battle_result['attack_roll']}){charge_text}")
                
                # Reset charge after defend
                player_data['charge_multiplier'] = 1.0
                if 'charge' in player_data:
                    player_data['charge'] = 1.0
                
            elif action == "charge":
                # Use new charge progression system (2-4-8-16)
                current_multiplier = player_data.get('charge_multiplier', 1.0)
                if 'charge' in player_data:
                    current_multiplier = player_data['charge']
                    
                next_multiplier = DamageCalculator.get_next_charge_multiplier(current_multiplier)
                player_data['charge_multiplier'] = next_multiplier
                player_data['charge'] = next_multiplier  # Keep both for compatibility
                player_data['charging'] = True
                
                self.battle_log.append(f"⚡ {player_name} charges up! (Charge: x{next_multiplier})")
                
        # Process monster action
        if self.monster_hp > 0:
            if monster_action == "attack":
                # Prepare player defense data for the damage calculator
                player_defenses = {}
                for player_id, player_data in self.player_data.items():
                    if not player_data['alive']:
                        continue
                        
                    # Check if this player is being defended
                    defense_effectiveness = 1.0
                    charge_multiplier = 1.0
                    
                    for def_id, target_id, _ in self.defending_players:
                        if target_id == player_id and def_id in self.defense_results:
                            defense_result = self.defense_results[def_id]
                            if defense_result['attack_result'] != "miss":
                                # Use the defender's charge multiplier and effectiveness
                                charge_multiplier = self.player_data[def_id].get('charge_multiplier', 1.0)
                                defense_effectiveness = self._get_roll_multiplier_from_result(
                                    defense_result['attack_result'], 
                                    defense_result['attack_roll']
                                )
                            break
                    
                    player_defenses[player_id] = {
                        'defense': player_data['total_defense'],
                        'charge_multiplier': charge_multiplier
                    }
                
                # Calculate monster attack against all players
                battle_results = DamageCalculator.calculate_monster_vs_players(
                    monster_attack=self.monster['attack'],
                    player_defenses=player_defenses,
                    monster_charge_multiplier=self.monster_charge_multiplier
                )
                
                # Apply results to each player
                for player_id, battle_result in battle_results.items():
                    if player_id not in self.player_data or not self.player_data[player_id]['alive']:
                        continue
                        
                    player_data = self.player_data[player_id]
                    
                    # Apply damage to player
                    player_data['hp'] = max(0, player_data['hp'] - battle_result['final_damage'])
                    self.total_damage_received[player_id] += battle_result['final_damage']
                    self.total_monster_damage_dealt += battle_result['final_damage']
                    
                    # Apply parry damage to monster if defended
                    if battle_result['parry_damage'] > 0:
                        self.monster_hp = max(0, self.monster_hp - battle_result['parry_damage'])
                        # Find the defender to credit parry damage
                        for def_id, target_id, _ in self.defending_players:
                            if target_id == player_id:
                                self.total_damage_dealt[def_id] += battle_result['parry_damage']
                                break
                        self.total_monster_damage_received += battle_result['parry_damage']
                
                # Add monster action to battle log
                charge_text = f" (Charged x{self.monster_charge_multiplier}!)" if self.monster_charge_multiplier > 1.0 else ""
                self.battle_log.append(f"The {self.monster['name']} attacks the party!{charge_text}")
                
                # Add guard information
                if hasattr(self, 'guard_relationships') and self.guard_relationships:
                    guard_messages = []
                    for defender_id, target_id in self.guard_relationships.items():
                        if defender_id in self.player_data and target_id in self.player_data:
                            defender_name = self.player_data[defender_id]['user'].display_name
                            target_name = self.player_data[target_id]['user'].display_name
                            defense_result = self.defense_results.get(defender_id, {})
                            
                            if defense_result.get('is_miss', False):
                                continue  # Skip failed defenses
                                
                            if defender_id == target_id:
                                guard_messages.append(f"{defender_name} defends themselves")
                            else:
                                guard_messages.append(f"{defender_name} defends {target_name}")
                    
                    if guard_messages:
                        self.battle_log.append("\n".join(["🛡️ " + msg for msg in guard_messages]))
                        
            elif monster_action == "defend":
                self.monster_defending = True
                self.battle_log.append(f"🛡️ The {self.monster['name']} takes a defensive stance!")
                
            elif monster_action == "charge":
                # Use new charge progression for monster too
                self.monster_charge_multiplier = DamageCalculator.get_next_charge_multiplier(self.monster_charge_multiplier)
                self.battle_log.append(f"⚡ The {self.monster['name']} is powering up! (Charge: x{self.monster_charge_multiplier})")
                
        # Clear player actions after processing
        self.player_actions.clear()
        
        # Reset states
        self.defending_players.clear()
        if hasattr(self, 'guard_relationships'):
            self.guard_relationships.clear()
        if hasattr(self, 'defense_results'):
            self.defense_results.clear()
            
        for player_data in self.player_data.values():
            player_data['charging'] = False
            
        # Reset monster defense state (charge persists until used in attack)
        self.monster_defending = False
        # Reset monster charge after attack (like players)
        if monster_action == "attack":
            self.monster_charge_multiplier = 1.0
            
        # Increment turn counter after processing the round
        self.turn_count += 1
        
        await self.check_victory_conditions()        
        
        if not self.battle_over:
            # Show battle results with round completion message
            round_message = f"Round {self.turn_count} completed! Preparing next round..."
            spectator_embed = self.build_spectator_embed(round_message)
            try:
                await self.message.edit(embed=spectator_embed)
                await self.start_action_collection()
            except discord.NotFound:
                self.message = await self.ctx.channel.send(embed=spectator_embed)
                await self.start_action_collection()
        else:
            # Show final battle results with damage summary
            final_embed = self.build_final_battle_embed("")
            try:
                await self.message.edit(embed=final_embed, view=None)
            except discord.NotFound:
                self.message = await self.ctx.channel.send(embed=final_embed, view=None)

    async def process_round(self):
        """Process a single round for PvP battles using new roll-based system"""
        action_text = f"⚔️ **Round {self.turn_count + 1} Results**\n\n"
        
        # Process defend actions first to set up defense states
        for player_id, action_data in self.player_actions.items():
            if action_data['action'] == 'defend':
                player_data = self.player_data[player_id]
                player_name = player_data['user'].display_name
                
                # Use new roll-based defend system
                battle_result = DamageCalculator.calculate_battle_action(
                    attacker_attack=player_data['total_defense'],
                    target_defense=0,  # Defense doesn't have an opposing stat
                    charge_multiplier=player_data.get('charge_multiplier', 1.0),
                    action_type="defend"
                )
                
                # Store defense effectiveness for later use
                roll_multiplier = self._get_roll_multiplier_from_result(battle_result['attack_result'], battle_result['attack_roll'])
                player_data['defense_effectiveness'] = roll_multiplier if battle_result['attack_result'] != "miss" else 0.0
                player_data['charging'] = True  # Mark as defending for compatibility
                
                # Add roll result to action text
                if battle_result['attack_result'] == "miss":
                    action_text += f"🛡️ **{player_name}** tries to defend but fails! (Roll: {battle_result['attack_roll']})\n"
                else:
                    charge_text = f" (Charged x{player_data.get('charge_multiplier', 1.0)}!)" if player_data.get('charge_multiplier', 1.0) > 1.0 else ""
                    action_text += f"🛡️ **{player_name}** is defending with {roll_multiplier:.2f}x effectiveness! (Roll: {battle_result['attack_roll']}){charge_text}\n"
                
                # Reset charge after defend
                player_data['charge_multiplier'] = 1.0
                if 'charge' in player_data:
                    player_data['charge'] = 1.0
        
        # Process charge actions
        for player_id, action_data in self.player_actions.items():
            if action_data['action'] == 'charge':
                player_data = self.player_data[player_id]
                player_name = player_data['user'].display_name
                
                # Use new charge progression system (2-4-8-16)
                current_multiplier = player_data.get('charge_multiplier', 1.0)
                if 'charge' in player_data:
                    current_multiplier = player_data['charge']
                    
                next_multiplier = DamageCalculator.get_next_charge_multiplier(current_multiplier)
                player_data['charge_multiplier'] = next_multiplier
                player_data['charge'] = next_multiplier  # Keep both for compatibility
                
                action_text += f"⚡ **{player_name}** is charging! (Charge: x{next_multiplier})\n"
        
        # Process attack actions
        for player_id, action_data in self.player_actions.items():
            if action_data['action'] == 'attack' and action_data['target']:
                attacker_data = self.player_data[player_id]
                defender_data = self.player_data[action_data['target']]
                
                if not attacker_data['alive'] or attacker_data['hp'] <= 0:
                    continue
                
                attacker_name = attacker_data['user'].display_name
                defender_name = defender_data['user'].display_name
                
                # Check if defender is defending
                defender_defending = defender_data.get('charging', False)
                defense_effectiveness = defender_data.get('defense_effectiveness', 0.0) if defender_defending else 0.0
                
                # Use new roll-based attack system
                battle_result = DamageCalculator.calculate_battle_action(
                    attacker_attack=attacker_data['total_attack'],
                    target_defense=defender_data['total_defense'],
                    charge_multiplier=attacker_data.get('charge_multiplier', 1.0),
                    target_charge_multiplier=defender_data.get('charge_multiplier', 1.0) if defender_defending else 1.0,
                    action_type="attack"
                )
                
                # Apply defense effectiveness if defending
                final_damage = battle_result['final_damage']
                parry_damage = 0
                
                if defender_defending and defense_effectiveness > 0:
                    # Calculate parry damage based on defense effectiveness
                    parry_damage = int(final_damage * defense_effectiveness * 0.5)  # 50% of damage as parry
                    final_damage = max(0, final_damage - int(final_damage * defense_effectiveness))
                
                # Apply damage
                if parry_damage > 0:
                    # Parry successful - reflect damage
                    attacker_data['hp'] = max(0, attacker_data['hp'] - parry_damage)
                    defender_data['hp'] = max(0, defender_data['hp'] - final_damage)
                    
                    roll_multiplier = self._get_roll_multiplier_from_result(battle_result['attack_result'], battle_result['attack_roll'])
                    action_text += f"⚔️ **{attacker_name}** attacks **{defender_name}**! (Roll: {battle_result['attack_roll']}, Multiplier: {roll_multiplier:.2f}x)\n"
                    action_text += f"🛡️ **{defender_name}** parries! Defense effectiveness: {defense_effectiveness:.2f}x\n"
                    if final_damage > 0:
                        action_text += f"💥 {final_damage} damage dealt to {defender_name}\n"
                    action_text += f"⚡ {parry_damage} parry damage dealt to {attacker_name}\n"
                else:
                    # Normal attack or failed defense
                    defender_data['hp'] = max(0, defender_data['hp'] - final_damage)
                    
                    if battle_result['attack_result'] == "miss":
                        action_text += f"⚔️ **{attacker_name}** attacks **{defender_name}** but misses completely! (Roll: {battle_result['attack_roll']})\n"
                    else:
                        roll_multiplier = self._get_roll_multiplier_from_result(battle_result['attack_result'], battle_result['attack_roll'])
                        charge_text = f" (Charged x{attacker_data.get('charge_multiplier', 1.0)}!)" if attacker_data.get('charge_multiplier', 1.0) > 1.0 else ""
                        defend_text = f", reduced by defense" if defender_defending else ""
                        action_text += f"⚔️ **{attacker_name}** attacks **{defender_name}**! (Roll: {battle_result['attack_roll']}, Multiplier: {roll_multiplier:.2f}x){charge_text}{defend_text} → {final_damage} damage dealt\n"
                
                # Reset charge after attack
                attacker_data['charge_multiplier'] = 1.0
                if 'charge' in attacker_data:
                    attacker_data['charge'] = 1.0
        
        # Reset states and increment turn
        self.defending_players.clear()
        self.player_actions.clear()  # Clear actions after processing
        for player_data in self.player_data.values():
            player_data['charging'] = False
            if 'defense_effectiveness' in player_data:
                del player_data['defense_effectiveness']
        
        self.turn_count += 1
        
        # Check victory conditions
        await self.check_victory_conditions()
        
        if not self.battle_over:
            # Update spectator embed in channel
            spectator_embed = self.build_spectator_embed(action_text)
            try:
                await self.message.edit(embed=spectator_embed)
            except discord.NotFound:
                # Message was deleted, send new message instead
                self.message = await self.ctx.channel.send(embed=spectator_embed)
            
            # Start next action collection in channel for all players
            await self.start_action_collection()
        else:
            # Battle ended
            final_embed = self.build_final_battle_embed(action_text)
            try:
                await self.message.edit(embed=final_embed, view=None)
            except discord.NotFound:
                # Message was deleted, send new message instead
                self.message = await self.ctx.channel.send(embed=final_embed, view=None)
            
            # Send detailed battle log
            battle_log = self.generate_battle_log(action_text)
            for i, message in enumerate(battle_log):
                await asyncio.sleep(1)
                await self.ctx.channel.send(message)

    def build_join_embed(self) -> discord.Embed:
        """Build embed for group battle joining"""
        embed = discord.Embed(
            title=f"⚔️ {self.battle_type.title()} Battle Setup",
            description=f"{self.ctx.author.display_name} is forming a battle!",
            color=0x0099ff
        )
        
        # Build party members display
        party_display = []
        for i, (user, pet) in enumerate(self.participants, 1):
            if pet:
                party_display.append(f"{i}. **{user.display_name}** - {pet['name']} (Level {pet.get('level', 1)})")
        
        if not party_display:
            party_display = ["🎯 Waiting for players..."]
        
        embed.add_field(
            name=f"🐾 Party Members ({len(self.participants)}/{self.max_participants})", 
            value="\n".join(party_display), 
            inline=False
        )
        
        if self.monster:
            type_emoji = MONSTER_EMOJIS.get(self.monster.get('type', 'monster'), '🤖')
            rarity_emoji = RARITY_EMOJIS.get(self.monster.get('rarity', 'common'), '⚪')
            embed.add_field(
                name=f"{type_emoji} {rarity_emoji} {self.monster['name']}",
                value=f"❤️ {self.monster['health']} HP",
                inline=False
            )
        
        embed.set_footer(text="Click the buttons below to join or leave the battle!")
        return embed

    def build_battle_embed(self, action_text: str = "") -> discord.Embed:
        """Build battle embed"""
        
        # Handle battle over states
        if self.battle_over:
            return self.build_final_battle_embed(action_text)
            
        current_player = self.get_current_player()
        if not current_player:
            return discord.Embed(title="Battle Ended", color=0x808080)
        
        title = f"⚔️ {self.battle_type.title()} Battle"
        if self.monster:
            title = f"⚔️ Battle: {self.monster['name']}"
        else:
            title = "⚔️ Battle"
        
        embed = discord.Embed(
            title=title,
            description=f"Turn {self.turn_count + 1} - {current_player['user'].display_name}'s turn!",
            color=0x0099ff
        )
        
        # Show participants
        status_lines = []
        # Build guard relationship map for quick lookup
        guard_map = {}
        if hasattr(self, 'guard_relationships'):
            for defender_id, target_id in self.guard_relationships.items():
                if target_id not in guard_map:
                    guard_map[target_id] = []
                guard_map[target_id].append(defender_id)
        
        for player_id, data in self.player_data.items():
            if not data['alive']:
                continue
                
            user = data['user']
            pet = data['pet']
            hp_bar = self.create_hp_bar(data['hp'], data['max_hp'], "pet", pet)
            status_emojis = []
            
            # Check if defending someone
            if player_id in self.guard_relationships:
                target_id = self.guard_relationships[player_id]
                if target_id == player_id:
                    status_emojis.append("🛡️")  # Self-defense
                else:
                    status_emojis.append("🛡️💪")  # Defending someone else
            
            # Check if being defended
            if player_id in guard_map:
                defender_count = len(guard_map[player_id])
                if defender_count > 0:
                    status_emojis.append(f"🛡️x{defender_count}")
            
            if data['charging']:
                status_emojis.append(f"⚡x{data['charge']:.1f}")
                
            status = " ".join(status_emojis) if status_emojis else "⚪"
            status_lines.append(f"{status} {user.display_name} - {pet['name']}\n{hp_bar}")
        
        if len(status_lines) <= 2:
            embed.add_field(name="🛡️ Participants", value="\n".join(status_lines), inline=False)
        else:
            mid = len(status_lines) // 2
            embed.add_field(name="🛡️ Team (1/2)", value="\n".join(status_lines[:mid]), inline=True)
            embed.add_field(name="🛡️ Team (2/2)", value="\n".join(status_lines[mid:]), inline=True)
        
        # Show group defense status
        if self.group_defense_active and self.group_defender:
            defender_data = None
            for uid, data in self.player_data.items():
                if uid == str(self.group_defender):
                    defender_data = data
                    break
            if defender_data:
                defender_pet = defender_data['pet']
                defender_defense = defender_pet.get('defense', 5) * 2
                embed.add_field(
                    name="🛡️ GROUP DEFENSE ACTIVE",
                    value=f"**{defender_data['user'].display_name}** is defending the entire team!\n"
                          f"Defense: {defender_defense} (doubled)",
                    inline=False
                )
        
        # Show monster if exists
        if self.monster:
            monster_hp_bar = self.create_hp_bar(self.monster_hp, self.max_monster_hp, "enemy")
            type_emoji = MONSTER_EMOJIS.get(self.monster.get('type', 'monster'), '🤖')
            rarity_emoji = RARITY_EMOJIS.get(self.monster.get('rarity', 'common'), '⚪')
            embed.add_field(
                name=f"{type_emoji} {rarity_emoji} {self.monster['name']}",
                value=monster_hp_bar,
                inline=False
            )
        
        if action_text:
            embed.add_field(name="⚡ Action", value=action_text[:200], inline=False)
        

        
        alive_count = sum(1 for data in self.player_data.values() if data['alive'])
        embed.set_footer(text=f"Turn {self.turn_count} | {alive_count} active fighters")
        
        return embed

    def build_spectator_embed(self, action_text: str = "") -> discord.Embed:
        """Build spectator embed for channel view (no buttons)"""
        
        # Handle battle over states
        if self.battle_over:
            return self.build_final_battle_embed(action_text)
            
        title = f"⚔️ {self.battle_type.title()} Battle"
        if self.monster:
            title = f"⚔️ Battle: {self.monster['name']}"
        else:
            title = "⚔️ PvP Battle"
        
        embed = discord.Embed(
            title=title,
            description=f"Round {self.turn_count + 1} - Live Battle Status",
            color=0x0099ff
        )
        
        # Show participants with detailed status
        status_lines = []
        for user_id, data in self.player_data.items():
            user = data['user']
            pet = data['pet']
            hp_bar = self.create_hp_bar(data['hp'], data['max_hp'], "pet", pet)
            charge_info = f" ⚡x{data['charge']:.1f}" if data['charge'] > 1.0 else ""
            charging_info = " 🔋" if data['charging'] else ""
            defending_info = " 🛡️" if user_id in self.defending_players else ""
            
            # Status indicators
            if not data['alive'] or data['hp'] <= 0:
                status = "💀 Defeated"
            elif user_id in self.player_actions:
                status = "✅ Action Ready"
            elif data['hp'] > 0:
                status = "⏳ Choosing Action"
            else:
                status = "🟢 Alive"
                
            status_lines.append(
                f"**{user.display_name}** - {pet['name']}\n"
                f"{hp_bar} {data['hp']}/{data['max_hp']} HP{charge_info}{charging_info}{defending_info}\n"
                f"Status: {status}"
            )
        
        embed.add_field(
            name="🐾 Participants",
            value="\n".join(status_lines) if status_lines else "No participants",
            inline=False
        )
        
        # Show monster for PvE battles
        if self.monster and self.battle_type in ["solo", "group"]:
            monster_hp_bar = self.create_hp_bar(self.monster_hp, self.max_monster_hp, "monster", self.monster)
            monster_charge_info = f" ⚡x{self.monster_charge_multiplier:.1f}" if self.monster_charge_multiplier > 1.0 else ""
            monster_defense_info = " 🛡️" if self.monster_defending else ""
            
            embed.add_field(
                name=f"🤖 {self.monster['name']}",
                value=f"{monster_hp_bar} {self.monster_hp}/{self.max_monster_hp} HP{monster_charge_info}{monster_defense_info}",
                inline=False
            )
        
        if action_text:
            embed.add_field(name="⚡ Last Action", value=action_text, inline=False)
        
        # Action collection status
        if self.waiting_for_actions:
            alive_players = [uid for uid, data in self.player_data.items() if data['alive'] and data['hp'] > 0]
            ready_count = len(self.player_actions)
            total_count = len(alive_players)
            
            embed.add_field(
                name="⏳ Action Collection",
                value=f"{ready_count}/{total_count} players have chosen their actions",
                inline=False
            )
        
        embed.set_footer(text=f"Round {self.turn_count + 1} • Battle in progress")
        return embed

    def generate_battle_log(self, action_text: str = "") -> list[str]:
        """Generate simplified battle log messages"""
        messages = []
        
        # Determine victory/defeat
        if self.monster:
            if self.monster_hp <= 0:
                title = "🎉 VICTORY!"
                description = f"You defeated **{self.monster['name']}**!"
            else:
                title = "💀 DEFEAT"
                description = f"You were defeated by **{self.monster['name']}**!"
        else:
            title = "⚔️ BATTLE ENDED"
            description = "The battle has concluded"
        
        messages.append(f"**{title}**\n{description}")
        
        # Rewards
        if self.rewards:
            reward_lines = []
            if self.rewards['type'] == 'victory' and self.rewards['survivors']:
                for survivor in self.rewards['survivors']:
                    reward_lines.append(f"**{survivor['user'].display_name}** received **{survivor['reward']}** energon")
            
            if reward_lines:
                reward_msg = "💰 **Rewards**\n" + "\n".join(reward_lines)
                messages.append(reward_msg)
        
        return messages

    def build_final_battle_embed(self, action_text: str = "") -> discord.Embed:
        """Build final battle embed with total damage summary and loot"""
        # Determine victory/defeat
        if self.monster:
            if self.monster_hp <= 0:
                title = "🎉 VICTORY!"
                description = f"You defeated **{self.monster['name']}**!"
            else:
                title = "💀 DEFEAT"
                description = f"You were defeated by **{self.monster['name']}**!"
        else:
            title = "⚔️ BATTLE ENDED"
            description = "The battle has concluded"

        embed = discord.Embed(
            title=title,
            description=description,
            color=0x00ff00 if "VICTORY" in title else 0xff0000 if "DEFEAT" in title else 0x808080
        )
        
        # Add total damage summary
        if self.monster:
            monster_damage = f"**Monster ({self.monster['name']})**\n"
            monster_damage += f"• **Damage Dealt:** {self.total_monster_damage_dealt}\n"
            monster_damage += f"• **Damage Received:** {self.total_monster_damage_received}\n\n"
            monster_damage += "**Players**\n"
            
            player_damage = []
            for uid in self.player_data:
                player_name = self.player_data[uid]['user'].display_name
                dealt = self.total_damage_dealt[uid]
                received = self.total_damage_received[uid]
                player_damage.append(f"• **{player_name}:** {dealt} dealt, {received} received")
            
            monster_damage += "\n".join(player_damage)
            
            embed.add_field(
                name="📊 Total Damage Summary",
                value=monster_damage,
                inline=False
            )
        else:
            # PvP battle damage summary
            player_damage = []
            for uid in self.player_data:
                player_name = self.player_data[uid]['user'].display_name
                dealt = self.total_damage_dealt[uid]
                received = self.total_damage_received[uid]
                player_damage.append(f"• **{player_name}:** {dealt} dealt, {received} received")
            
            embed.add_field(
                name="📊 Total Damage Summary",
                value="**Players**\n" + "\n".join(player_damage),
                inline=False
            )
        
        # Add final standings and loot
        final_standings = []
        for user_id, data in self.player_data.items():
            status = "🟢 Alive" if data['hp'] > 0 else "🔴 Defeated"
            
            # Build standings text
            standings_text = f"Final HP: {data['hp']}/{data['max_hp']}"
            
            # Check for equipment loot
            if hasattr(self, 'rewards') and 'equipment_loot' in self.rewards:
                equipment_list = self.rewards['equipment_loot'].get(user_id, [])
                if equipment_list:
                    loot_text = "\n📦 **Looted:"
                    for equipment in equipment_list:
                        rarity_emoji = RARITY_EMOJIS.get(equipment.get('rarity', 'common'), '⚪')
                        type_emoji = {
                            'chassis_plating': '🩻',
                            'energy_cores': '🔋',
                            'utility_modules': '💾'
                        }.get(equipment.get('type'), '📦')
                        
                        loot_text += f"\n{type_emoji} {rarity_emoji} {equipment.get('name', 'Unknown Item')}"
                    standings_text += loot_text
            
            final_standings.append(f"**{data['user'].display_name}** - {status}\n{standings_text}")
        
        if final_standings:
            embed.add_field(
                name="🏆 Final Standings & Rewards",
                value="\n\n".join(final_standings),
                inline=False
            )
        
        if action_text:
            embed.add_field(name="📜 Final Round", value=action_text[:1024], inline=False)
        
        return embed

    def get_monster_action(self) -> str:
        """Determine monster's AI action"""
        if not self.monster:
            return "attack"
            
        monster_hp_percent = (self.monster_hp / self.max_monster_hp) * 100
        
        if monster_hp_percent <= 20:
            choices = ["attack", "attack", "attack", "defend", "defend", "charge"]
        elif monster_hp_percent <= 50:
            choices = ["attack", "attack", "defend", "defend", "charge"]
        else:
            choices = ["attack", "attack", "attack", "attack", "defend", "charge"]
            
        return random.choice(choices)

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

    async def check_victory_conditions(self):
        """Check if battle is over and handle rewards"""
        if self.battle_over:
            return
        
        # Check for victory against monster
        if self.monster and self.monster_hp <= 0:
            await self.handle_victory()
            self.battle_over = True
            
        # Check for defeat against monster
        elif self.monster and all(not data['alive'] or data['hp'] <= 0 for data in self.player_data.values()):
            await self.handle_defeat()
            self.battle_over = True

    def _get_roll_multiplier_from_result(self, result_type: str, roll: int) -> float:
        """Convert attack result type to roll multiplier for display purposes"""
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
            return 1.0  # Fallback

    def calculate_loot_chance(self, health_percentage: float) -> float:
        """Calculate loot chance based on health percentage remaining"""
 
        if health_percentage <= 0.1: 
            return 0.10
        elif health_percentage >= 0.9: 
            return 1.0
        else:
            return 0.10 + (health_percentage - 0.1) * (0.9 / 0.8)
    
    def determine_loot_rarity(self, enemy_type: str, health_percentage: float) -> str:
        """Determine loot rarity based on enemy type and health percentage remaining"""
        if enemy_type == 'monster':
            # Monster battles: <50% health = common, ≥50% health = uncommon
            return 'common' if health_percentage < 0.5 else 'uncommon'
        elif enemy_type == 'boss':
            # Boss battles: <50% health = rare, ≥50% health = epic
            return 'rare' if health_percentage < 0.5 else 'epic'
        elif enemy_type == 'titan':
            # Titan battles: <50% health = legendary, ≥50% health = mythic
            return 'legendary' if health_percentage < 0.5 else 'mythic'
        else:
            # Default fallback
            return 'common'
    
    async def get_random_equipment_by_rarity(self, rarity: str, exclude_ids: List[str] = None) -> Optional[Dict[str, Any]]:
        """Get a random piece of equipment from pet_equipment.json by rarity"""
        try:
            exclude_ids = exclude_ids or []
            equipment_data = await user_data_manager.get_pet_equipment_data()
            
            if not equipment_data:
                logger.warning(f"No equipment data available for rarity {rarity}")
                return None
            
            # Collect all equipment items of the specified rarity
            available_items = []
            
            # Check chassis_plating
            chassis_data = equipment_data.get("chassis_plating", {})
            equipment_by_rarity = chassis_data.get("equipment", {})
            if rarity in equipment_by_rarity:
                for item_id, item_data in equipment_by_rarity[rarity].items():
                    if item_id not in exclude_ids:
                        available_items.append({
                            **item_data,
                            "type": "chassis_plating"
                        })
            
            # Check energy_cores
            energy_data = equipment_data.get("energy_cores", {})
            equipment_by_rarity = energy_data.get("equipment", {})
            if rarity in equipment_by_rarity:
                for item_id, item_data in equipment_by_rarity[rarity].items():
                    if item_id not in exclude_ids:
                        available_items.append({
                            **item_data,
                            "type": "energy_cores"
                        })
            
            # Check utility_modules
            utility_data = equipment_data.get("utility_modules", {})
            equipment_by_rarity = utility_data.get("equipment", {})
            if rarity in equipment_by_rarity:
                for item_id, item_data in equipment_by_rarity[rarity].items():
                    if item_id not in exclude_ids:
                        available_items.append({
                            **item_data,
                            "type": "utility_modules"
                        })
            
            if available_items:
                selected_item = random.choice(available_items)
                logger.info(f"Generated equipment: {selected_item.get('name', 'Unknown')} ({rarity}) - {selected_item.get('type', 'unknown')}")
                return selected_item
            
            logger.warning(f"No available equipment items found for rarity {rarity}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting random equipment by rarity {rarity}: {e}")
            return None

    async def handle_victory(self):
        """Handle battle victory and rewards with batch operations"""
        try:
            base_reward = self.monster.get('health', 100) // 10
            rarity_multipliers = {"common": 1, "uncommon": 1.5, "rare": 2, "epic": 3, "legendary": 5, "mythic": 10}
            type_multipliers = {"monster": 1, "boss": 2, "titan": 5}
            
            total_reward = int(base_reward * 
                             rarity_multipliers.get(self.monster.get('rarity', 'common'), 1) * 
                             type_multipliers.get(self.monster.get('type', 'monster'), 1))
            
            self.rewards = {'type': 'victory', 'total_reward': total_reward, 'survivors': [], 'equipment_loot': {}}
            
            # Collect all survivor data for batch operations
            survivor_updates = {}
            user_data_updates = {}
            pet_data_updates = {}
            
            for user_id, data in self.player_data.items():
                if data['alive'] and data['hp'] > 0:
                    pet = data['pet']
                    pet['battles_won'] = pet.get('battles_won', 0) + 1
                    
                    # Handle experience gain and level-up
                    from ..pet_levels import add_experience
                    equipment_stats = self.calculate_equipment_stats(pet.get('equipment', {}))
                    leveled_up, level_up_details = await add_experience(str(user_id), total_reward, "battle", equipment_stats)
                    
                    # Initialize survivor_updates entry first
                    survivor_updates[str(user_id)] = {'reward': total_reward, 'equipment': []}
                    
                    if leveled_up and level_up_details:
                        # Store level-up info for display in final embed
                        survivor_updates[str(user_id)]['level_up'] = level_up_details
                    
                    # Calculate health loss
                    max_hp = pet.get('energy', 100) + pet.get('maintenance', 0) + pet.get('happiness', 0)
                    damage_taken = max_hp - data['hp']
                    health_loss_per_stat = damage_taken // 3
                    remaining_loss = damage_taken % 3
                    
                    pet['energy'] = max(0, pet['energy'] - health_loss_per_stat - (1 if remaining_loss > 0 else 0))
                    pet['maintenance'] = max(0, pet['maintenance'] - health_loss_per_stat - (1 if remaining_loss > 1 else 0))
                    pet['happiness'] = max(0, pet['happiness'] - health_loss_per_stat)
                    
                    # Handle loot
                    looted_equipment = []
                    if self.monster.get('type') in ['monster', 'boss', 'titan']:
                        health_percentage = data['hp'] / max_hp
                        num_loot_items = 0 if health_percentage <= 0.1 else (2 if health_percentage >= 0.9 else (1 if random.random() <= self.calculate_loot_chance(health_percentage) else 0))
                        
                        logger.info(f"User {user_id} ({pet['name']}) - Health: {health_percentage:.2f}, Loot items: {num_loot_items}")
                        
                        for i in range(num_loot_items):
                            loot_rarity = self.determine_loot_rarity(self.monster.get('type', 'monster'), health_percentage)
                            loot_item = await self.get_random_equipment_by_rarity(loot_rarity)
                            if loot_item:
                                looted_equipment.append(loot_item)
                                # Add to inventory
                                if "inventory" not in pet:
                                    pet["inventory"] = []
                                # Use original format from pet_equipment.json for consistency
                                inventory_item = {
                                    "id": loot_item.get("id"),
                                    "name": loot_item.get("name"),
                                    "type": loot_item.get("type"),  # Use 'type' not 'equipment_type'
                                    "rarity": loot_item.get("rarity"),
                                    "description": loot_item.get("description", ""),
                                    "unlock_message": loot_item.get("unlock_message", ""),
                                    "stat_bonus": loot_item.get("stat_bonus", {})  # Keep stat_bonus object
                                }
                                pet["inventory"].append(inventory_item)
                                logger.info(f"Looted item {i+1}: {loot_item.get('name', 'Unknown')} ({loot_rarity}) for user {user_id}")
                            else:
                                logger.warning(f"Failed to generate loot item {i+1} of rarity {loot_rarity} for user {user_id}")
                        
                        if num_loot_items > 0 and not looted_equipment:
                            logger.warning(f"No loot items were successfully generated for user {user_id} despite {num_loot_items} intended items")
                            # Fallback: give basic energon reward instead
                            fallback_reward = total_reward // 10
                            if fallback_reward > 0:
                                await user_data_manager.add_energon(str(user_id), fallback_reward)
                                logger.info(f"Fallback energon reward of {fallback_reward} given to user {user_id} for failed loot generation")
                    
                    # Update equipment in survivor_updates
                    survivor_updates[str(user_id)]['equipment'] = looted_equipment
                    
                    # Add loot to rewards for display in final embed
                    if looted_equipment:
                        # Store all looted equipment for proper display
                        self.rewards['equipment_loot'][user_id] = looted_equipment
                    
                    # Prepare batch updates
                    pet_data_updates[str(user_id)] = pet
                    
                    self.rewards['survivors'].append({
                        'user': data['user'], 'reward': total_reward, 'pet_name': pet['name'], 'equipment': looted_equipment
                    })
            
            # Save all pet data
            if pet_data_updates:
                for user_id, pet_data in pet_data_updates.items():
                    username = self.player_data[int(user_id)]['user'].display_name
                    await user_data_manager.save_pet_data(user_id, username, pet_data)
            
            # Update energon for survivors and send level-up embeds
            for user_id, survivor_data in survivor_updates.items():
                # Use proper energon tracking method to update total_earned
                await user_data_manager.add_energon(str(user_id), survivor_data['reward'])
                
                # Send level-up embed if pet leveled up
                if 'level_up' in survivor_data:
                    level_up_details = survivor_data['level_up']
                    # Create level-up embed from the details
                    from ..pet_levels import create_level_up_embed
                    user = self.player_data[int(user_id)]['user']
                    pet = self.player_data[int(user_id)]['pet']
                    try:
                        level_up_embed = await create_level_up_embed(pet, level_up_details, user.id)
                        await self.ctx.channel.send(embed=level_up_embed)
                    except Exception as e:
                        logger.error(f"Error sending level-up embed: {e}")
                        # Fallback to text message
                        try:
                            await self.ctx.channel.send(f"🎉 <@{user_id}>'s pet leveled up!")
                        except:
                            pass
            
            # Log loot summary for debugging
            total_loot_items = sum(len(survivor_data['equipment']) for survivor_data in survivor_updates.values())
            logger.info(f"Battle victory: {total_reward} energon awarded, {total_loot_items} total equipment items distributed")
            
            # Log individual loot distribution
            for user_id, survivor_data in survivor_updates.items():
                if survivor_data['equipment']:
                    pet_name = self.player_data[int(user_id)]['pet']['name']
                    loot_names = [item.get('name', 'Unknown') for item in survivor_data['equipment']]
                    logger.info(f"User {user_id} ({pet_name}) received {len(survivor_data['equipment'])} items: {', '.join(loot_names)}")
            
        except Exception as e:
            logger.error(f"Error handling victory: {e}")

    async def handle_defeat(self):
        """Handle battle defeat with batch operations"""
        try:
            pet_updates = {}
            for user_id, data in self.player_data.items():
                pet = data['pet']
                pet['battles_lost'] = pet.get('battles_lost', 0) + 1
                
                # Calculate damage taken during battle (current HP vs starting HP)
                max_hp = pet.get('energy', 100) + pet.get('maintenance', 0) + pet.get('happiness', 0)
                damage_taken = max_hp - data['hp']
                health_loss_per_stat = damage_taken // 3
                remaining_loss = damage_taken % 3
                
                pet['energy'] = max(0, pet['energy'] - health_loss_per_stat - (1 if remaining_loss > 0 else 0))
                pet['maintenance'] = max(0, pet['maintenance'] - health_loss_per_stat - (1 if remaining_loss > 1 else 0))
                pet['happiness'] = max(0, pet['happiness'] - health_loss_per_stat)
                
                # Check if pet died (any stat reached 0) and set all stats to 0
                if pet['energy'] == 0 or pet['maintenance'] == 0 or pet['happiness'] == 0:
                    pet['energy'] = 0
                    pet['maintenance'] = 0
                    pet['happiness'] = 0
                    logger.info(f"Pet {pet['name']} died in battle for user {user_id}")
                
                pet_updates[str(user_id)] = pet
            
            # Save all pet data
            if pet_updates:
                for user_id, pet_data in pet_updates.items():
                    username = self.player_data[int(user_id)]['user'].display_name
                    await user_data_manager.save_pet_data(user_id, username, pet_data)
                
            logger.info("Battle defeat handled")
            
        except Exception as e:
            logger.error(f"Error handling defeat: {e}")

class TargetSelect(discord.ui.Select):
    """Dropdown for selecting a guard target"""
    
    def __init__(self, battle_view: UnifiedBattleView, user_id: int):
        self.battle_view = battle_view
        self.user_id = user_id
        
        # Get alive players (including self) as options
        options = []
        for uid, data in battle_view.player_data.items():
            if data['alive'] and data['hp'] > 0:
                user = data['user']
                label = f"{user.display_name}"
                if uid == user_id:
                    label += " (Yourself)"
                options.append(discord.SelectOption(
                    label=label,
                    value=str(uid),
                    description=f"Current HP: {data['hp']}/{data['max_hp']}",
                    emoji="🛡️"
                ))
        
        super().__init__(
            placeholder="Select a pet to guard...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        target_id = int(self.values[0])
        self.battle_view.guard_relationships[self.user_id] = target_id
        
        # Store the defend action
        self.battle_view.player_actions[self.user_id] = {
            'action': 'defend',
            'target': target_id
        }
        
        # Defer the interaction to avoid timeout issues
        await interaction.response.defer()
        
        # Delete the original message immediately
        try:
            await interaction.message.delete()
        except discord.NotFound:
            # Message was already deleted, nothing to do
            pass
        except Exception as e:
            # Log any errors but don't fail the action
            logger.debug(f"Error deleting target selection message: {e}")
        
        # Check if all players have chosen actions
        await self.battle_view.check_all_actions_submitted()

class EphemeralActionView(discord.ui.View):
    """Ephemeral action view for individual players"""
    
    def __init__(self, battle_view: UnifiedBattleView, user_id: int):
        super().__init__(timeout=300)
        self.battle_view = battle_view
        self.user_id = user_id

    @discord.ui.button(label="Attack", style=discord.ButtonStyle.red, emoji="⚔️", row=0)
    async def attack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_action_selection(interaction, "attack")

    @discord.ui.button(label="Defend", style=discord.ButtonStyle.blurple, emoji="🛡️", row=0)
    async def defend_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Create a new view with target selection
        view = discord.ui.View(timeout=300)
        view.add_item(TargetSelect(self.battle_view, self.user_id))
        
        # Add cancel button
        async def cancel_callback(interaction: discord.Interaction):
            await interaction.message.delete()
            
        cancel_button = discord.ui.Button(
            label="Cancel",
            style=discord.ButtonStyle.danger,
            emoji="❌"
        )
        cancel_button.callback = cancel_callback
        view.add_item(cancel_button)
        
        await interaction.response.send_message(
            "🛡️ **Select a pet to defend:**",
            view=view,
            ephemeral=True
        )

    @discord.ui.button(label="Charge", style=discord.ButtonStyle.green, emoji="⚡", row=0)
    async def charge_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_action_selection(interaction, "charge")

    async def handle_action_selection(self, interaction: discord.Interaction, action: str):
        """Handle the action selection"""
        # Verify this is the correct user
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your action menu!", ephemeral=True, delete_after=3)
            return
        
        # Store the action
        self.battle_view.player_actions[self.user_id] = {
            'action': action,
            'target': None
        }
        
        # Defer the interaction to avoid timeout issues
        await interaction.response.defer()
        
        # Delete the original action message immediately
        try:
            await interaction.message.delete()
        except discord.NotFound:
            # Message was already deleted, nothing to do
            pass
        except Exception as e:
            # Log any errors but don't fail the action
            logger.debug(f"Error deleting action message: {e}")
        
        # Check if all players have chosen actions
        await self.battle_view.check_all_actions_submitted()

class BattleSystem:
    """Battle system class for managing battles"""
    
    def __init__(self):
        self.active_battles = {}
        
    async def create_battle(self, ctx, battle_type: str, **kwargs) -> UnifiedBattleView:
        """Create a new battle"""
        # Handle PvE battles only (PvP removed)
        battle = await UnifiedBattleView.create_async(ctx, battle_type, **kwargs)
        self.active_battles[ctx.channel.id] = battle
        return battle
        
    def get_battle(self, channel_id: int) -> Optional[UnifiedBattleView]:
        """Get active battle for channel"""
        return self.active_battles.get(channel_id)
        
    def end_battle(self, channel_id: int):
        """End battle for channel"""
        self.active_battles.pop(channel_id, None)

# Global battle system instance
battle_system = BattleSystem()

# Export classes for use in other modules
__all__ = [
    'UnifiedBattleView',
    'BattleSystem',
    'battle_system',
    'MONSTER_EMOJIS',
    'RARITY_EMOJIS'
]