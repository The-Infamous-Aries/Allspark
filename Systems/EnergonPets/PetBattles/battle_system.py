import discord
import random
import asyncio
import logging
import json
import os
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from Systems.user_data_manager import user_data_manager

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
            pet = await user_data_manager.get_pet_data(str(user.id))
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
            pet = await user_data_manager.get_pet_data(str(interaction.user.id))
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
        
        # Send new action buttons
        try:
            action_view = EphemeralActionView(self.battle_view, user_id)
            embed = discord.Embed(
                title="⚔️ Battle Action Required",
                description=f"**{player_data['pet']['name']}** - Round {self.battle_view.turn_count + 1}\nChoose your action:",
                color=0x00ff00
            )
            await interaction.response.send_message(
                embed=embed,
                view=action_view,
                ephemeral=True
            )
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
        
        # Guard relationships - maps defender_id to the user_id they're protecting
        self.guard_relationships = {}
        
        # Damage tracking for final summary
        self.total_damage_dealt = {}
        self.total_damage_received = {}
        self.total_monster_damage_dealt = 0
        self.total_monster_damage_received = 0 
 
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
        
        # Batch load pet data
        pet_data_batch = await user_data_manager.batch_load_user_data(user_ids, "pet_data")
        
        # Create participants list
        view.participants = []
        for i, user_id in enumerate(user_ids):
            user = ctx.author if user_id == str(ctx.author.id) else (participants[i][0] if participants else ctx.author)
            pet = pet_data_batch.get(user_id) or {
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
                base_energy = pet.get('energy', 100)
                base_maintenance = pet.get('maintenance', 0)
                base_happiness = pet.get('happiness', 0)
                equipment = pet.get('equipment', {})
                equipment_stats = self.calculate_equipment_stats(equipment)        
                total_attack = base_attack + equipment_stats['attack']
                total_defense = base_defense + equipment_stats['defense']
                total_energy = base_energy + equipment_stats['energy']
                total_maintenance = base_maintenance + equipment_stats['maintenance']
                total_happiness = base_happiness + equipment_stats['happiness']             
                max_hp = total_energy + total_maintenance + total_happiness
                self.player_data[user.id] = {
                    'user': user,
                    'pet': pet,
                    'hp': max_hp,
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
        
        # Update the main battle message without action buttons
        waiting_embed = self.build_spectator_embed("⏳ Waiting for players to choose actions...")
        try:
            await self.message.edit(embed=waiting_embed, view=None)
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
                        
                        # Send ephemeral message to this specific player (no dismiss option)
                        embed = discord.Embed(
                            title="⚔️ Battle Action Required",
                            description=f"**{player_data['pet']['name']}** - Round {self.turn_count + 1}\nChoose your action:",
                            color=0x00ff00
                        )
                        await self.interaction.followup.send(
                            embed=embed,
                            view=action_view,
                            ephemeral=True
                        )
                        
                    except Exception as e:
                        logger.error(f"Error sending action message to user {user_id}: {e}")
                        
            # Add a blue link button in the main channel for players who dismissed their ephemeral message
            resend_view = ResendActionView(self)
            await self.ctx.channel.send(
                "🔄 **Dismissed your action buttons?** Click below to get them back:",
                view=resend_view,
                delete_after=60
            )
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
        """Process a round for PvE battles - now tracks damage instead of detailed messages"""
        # Process player actions and track damage
        for player_id, action_data in self.player_actions.items():
            player_data = self.player_data[player_id]           
            if action_data['action'] == "attack":
                player_roll = self.roll_d20()
                player_multiplier = self.calculate_attack_multiplier(player_roll)
                total_attack = player_data.get('total_attack', player_data['pet'].get('attack', 10))
                attack_power = int(total_attack * player_data['charge'] * player_multiplier)
                monster_defense = self.monster.get('defense', 5) // 2
                reduced_damage = max(1, attack_power - monster_defense)
                self.monster_hp = max(0, self.monster_hp - reduced_damage)
                
                # Track damage dealt by player
                self.total_damage_dealt[player_id] += reduced_damage
                self.total_monster_damage_received += reduced_damage
                
                # Add action message to battle log
                action_text = f"{player_data['user'].mention} attacks with a {player_data['charge']:.1f}x charge!"
                self.battle_log.append(action_text)
                
            elif action_data['action'] == "defend":
                block_roll = self.roll_d20()
                total_defense = player_data.get('total_defense', player_data['pet'].get('defense', 5))
                block_stat = int(total_defense * self.calculate_attack_multiplier(block_roll))                   
                target_id = action_data.get('target', player_id)  # Default to self if no target
                
                # Add action message to battle log
                if target_id == player_id:
                    action_text = f"{player_data['user'].mention} takes a defensive stance!"
                else:
                    target_name = next((data['user'].display_name for uid, data in 
                                     self.player_data.items() if uid == target_id), "Unknown")
                    action_text = f"{player_data['user'].mention} guards {target_name}!"
                self.battle_log.append(action_text)
                
                # Store defender's block stat and target
                self.defending_players.add((player_id, target_id, block_stat))
                
            elif action_data['action'] == "charge":
                player_data['charge'] = min(5.0, player_data['charge'] * 2)
                player_data['charging'] = True
                
                # Add action message to battle log
                action_text = f"{player_data['user'].mention} charges up their next attack! ({player_data['charge']:.1f}x)"
                self.battle_log.append(action_text)
                
        # Process monster action and track damage
        if self.monster_hp > 0:
            monster_roll = self.roll_d20()
            monster_multiplier = self.calculate_attack_multiplier(monster_roll)           
            if monster_action == "attack":
                monster_attack = int(self.monster.get('attack', 15) * monster_multiplier)
                
                # Group defenders by their target
                target_defenses = {}
                for defender_id, target_id, block_stat in self.defending_players:
                    if target_id not in target_defenses:
                        target_defenses[target_id] = []
                    target_defenses[target_id].append((defender_id, block_stat))
                
                # If no one is defending, distribute damage to all players
                if not target_defenses:
                    alive_players = [data for data in self.player_data.values() if data['alive']]
                    if alive_players:
                        damage_per_player = max(1, monster_attack // len(alive_players))
                        for player_data in alive_players:
                            player_data['hp'] = max(0, player_data['hp'] - damage_per_player)
                            self.total_damage_received[player_data['user'].id] += damage_per_player
                            self.total_monster_damage_dealt += damage_per_player
                else:
                    # Process each target that's being defended
                    for target_id, defenders in target_defenses.items():
                        if target_id not in self.player_data:
                            continue
                            
                        target_data = self.player_data[target_id]
                        if not target_data['alive']:
                            continue
                            
                        # Split monster attack among all targets being defended
                        damage_per_target = max(1, monster_attack // len(target_defenses))
                        
                        # Calculate total block power from all defenders of this target
                        total_block = sum(block_stat for _, block_stat in defenders)
                        
                        if total_block >= damage_per_target:
                            # Successful block - calculate parry damage
                            parry_damage = total_block - damage_per_target
                            if parry_damage > 0:
                                self.monster_hp = max(0, self.monster_hp - parry_damage)
                                # Distribute parry damage credit among defenders
                                for defender_id, _ in defenders:
                                    if defender_id in self.player_data:
                                        self.total_damage_dealt[defender_id] += (parry_damage // len(defenders))
                                self.total_monster_damage_received += parry_damage
                        else:
                            # Partial block - calculate remaining damage
                            damage_taken = damage_per_target - total_block
                            target_data['hp'] = max(0, target_data['hp'] - damage_taken)
                            
                            # Track damage received by target and dealt by monster
                            self.total_damage_received[target_id] += damage_taken
                            self.total_monster_damage_dealt += damage_taken
                            
                # Add monster action to battle log
                self.battle_log.append(f"The {self.monster['name']} attacks the party!")
                
                # Add guard information
                if hasattr(self, 'guard_relationships') and self.guard_relationships:
                    guard_messages = []
                    for defender_id, target_id in self.guard_relationships.items():
                        if defender_id in self.player_data and target_id in self.player_data:
                            defender_name = self.player_data[defender_id]['user'].display_name
                            target_name = self.player_data[target_id]['user'].display_name
                            if defender_id == target_id:
                                guard_messages.append(f"{defender_name} defends themselves")
                            else:
                                guard_messages.append(f"{defender_name} defends {target_name}")
                    
                    if guard_messages:
                        self.battle_log.append("\n".join(["🛡️ " + msg for msg in guard_messages]))
                        
            elif monster_action == "defend":
                self.battle_log.append(f"The {self.monster['name']} takes a defensive stance!")
            elif monster_action == "charge":
                self.battle_log.append(f"The {self.monster['name']} is powering up!")
                
        # Reset states
        self.defending_players.clear()
        self.guard_relationships.clear()
        for player_data in self.player_data.values():
            player_data['charging'] = False
            
        await self.check_victory_conditions()        
        
        if not self.battle_over:
            # Show simple round completion message
            spectator_embed = self.build_spectator_embed(f"Round {self.turn_count + 1} completed")
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
        """Process a single round for all battle types"""
        action_text = f"⚔️ **Round {self.turn_count + 1} Results**\n\n"
        for player_id, action_data in self.player_actions.items():
            if action_data['action'] == 'defend':
                self.player_data[player_id]['charging'] = True
                action_text += f"🛡️ **{self.player_data[player_id]['user'].display_name}** is defending!\n"
        for player_id, action_data in self.player_actions.items():
            if action_data['action'] == 'charge':
                player_data = self.player_data[player_id]
                player_data['charge'] = min(5.0, player_data['charge'] * 2)
                action_text += f"⚡ **{player_data['user'].display_name}** is charging! (Charge: x{player_data['charge']:.1f})\n"
        for player_id, action_data in self.player_actions.items():
            if action_data['action'] == 'attack' and action_data['target']:
                attacker_data = self.player_data[player_id]
                defender_data = self.player_data[action_data['target']]
                if not attacker_data['alive'] or attacker_data['hp'] <= 0:
                    continue
                roll = self.roll_d20()
                multiplier = self.calculate_attack_multiplier(roll)
                total_attack = attacker_data.get('total_attack', attacker_data['pet'].get('attack', 10))
                attack_damage = int(total_attack * attacker_data['charge'] * multiplier)
                if defender_data['charging']:
                    block_roll = self.roll_d20()
                    total_defense = defender_data.get('total_defense', defender_data['pet'].get('defense', 5))
                    block_stat = int(total_defense * self.calculate_attack_multiplier(block_roll))                   
                    if block_stat >= attack_damage:
                        parry_damage = block_stat - attack_damage
                        attacker_data['hp'] = max(0, attacker_data['hp'] - parry_damage)
                        action_text += f"⚔️ **{attacker_data['user'].display_name}** attacks **{defender_data['user'].display_name}**! Rolled {roll} → {attack_damage} damage\n"
                        action_text += f"🛡️ **{defender_data['user'].display_name}** parries! Block: {block_stat} ≥ Attack: {attack_damage}\n"
                        if parry_damage > 0:
                            action_text += f"⚡ Parry damage: {parry_damage} dealt to {attacker_data['user'].display_name}\n"
                    else:
                        damage_taken = attack_damage - block_stat
                        defender_data['hp'] = max(0, defender_data['hp'] - damage_taken)
                        action_text += f"⚔️ **{attacker_data['user'].display_name}** attacks **{defender_data['user'].display_name}**! Rolled {roll} → {attack_damage} damage\n"
                        action_text += f"🛡️ **{defender_data['user'].display_name}** attempts to parry! Block: {block_stat} < Attack: {attack_damage}\n"
                        action_text += f"💔 Takes {damage_taken} damage\n"
                else:
                    # Regular attack with defense reduction
                    total_defense = defender_data.get('total_defense', defender_data['pet'].get('defense', 5))
                    defender_defense = total_defense // 2
                    reduced_damage = max(1, attack_damage - defender_defense)
                    defender_data['hp'] = max(0, defender_data['hp'] - reduced_damage)
                    action_text += f"⚔️ **{attacker_data['user'].display_name}** attacks **{defender_data['user'].display_name}**! Rolled {roll} → {attack_damage} damage, reduced by {defender_defense} defense → {reduced_damage} damage dealt\n"
        
        # Reset defending players and increment turn
        self.defending_players.clear()
        for player_data in self.player_data.values():
            player_data['charging'] = False
        
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
            monster_charging_info = " 🔋" if hasattr(self, 'monster_charging') and self.monster_charging else ""
            
            embed.add_field(
                name=f"🤖 {self.monster['name']}",
                value=f"{monster_hp_bar} {self.monster_hp}/{self.max_monster_hp} HP{monster_charge_info}{monster_charging_info}",
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
                equipment = self.rewards['equipment_loot'].get(user_id)
                if equipment:
                    rarity_emoji = RARITY_EMOJIS.get(equipment.get('rarity', 'common'), '⚪')
                    type_emoji = {
                        'chassis_plating': '🩻',
                        'energy_cores': '🔋',
                        'utility_modules': '💾'
                    }.get(equipment.get('equipment_type'), '📦')
                    
                    standings_text += f"\n{type_emoji} **Looted:** {rarity_emoji} {equipment.get('name', 'Unknown Item')}"
            
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

    def roll_d20(self) -> int:
        """Roll a d20"""
        return random.randint(1, 20)

    def calculate_attack_multiplier(self, roll: int) -> float:
        """Calculate attack multiplier based on roll"""
        if 1 <= roll <= 5:
            divisor_map = {1: 5, 2: 4, 3: 3, 4: 2, 5: 1}
            return 1.0 / divisor_map[roll]
        elif 6 <= roll <= 10:
            return 1.0
        elif 11 <= roll <= 20:
            return roll - 10
        return 1.0

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
                            "equipment_type": "chassis_plating"
                        })
            
            # Check energy_cores
            energy_data = equipment_data.get("energy_cores", {})
            equipment_by_rarity = energy_data.get("equipment", {})
            if rarity in equipment_by_rarity:
                for item_id, item_data in equipment_by_rarity[rarity].items():
                    if item_id not in exclude_ids:
                        available_items.append({
                            **item_data,
                            "equipment_type": "energy_cores"
                        })
            
            # Check utility_modules
            utility_data = equipment_data.get("utility_modules", {})
            equipment_by_rarity = utility_data.get("equipment", {})
            if rarity in equipment_by_rarity:
                for item_id, item_data in equipment_by_rarity[rarity].items():
                    if item_id not in exclude_ids:
                        available_items.append({
                            **item_data,
                            "equipment_type": "utility_modules"
                        })
            
            if available_items:
                return random.choice(available_items)
            
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
                    from .pet_levels import add_experience, create_level_up_embed
                    leveled_up, level_gains = await add_experience(user_id, total_reward, "battle")
                    
                    # Initialize survivor_updates entry first
                    survivor_updates[str(user_id)] = {'reward': total_reward, 'equipment': []}
                    
                    if leveled_up and level_gains:
                        # Store level-up info for display in final embed
                        survivor_updates[str(user_id)]['level_up'] = level_gains
                    
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
                        
                        for _ in range(num_loot_items):
                            loot_rarity = self.determine_loot_rarity(self.monster.get('type', 'monster'), health_percentage)
                            loot_item = await self.get_random_equipment_by_rarity(loot_rarity)
                            if loot_item:
                                looted_equipment.append(loot_item)
                                # Add to inventory
                                if "inventory" not in pet:
                                    pet["inventory"] = []
                                stat_bonus = loot_item.get("stat_bonus", {})
                                pet["inventory"].append({
                                    "id": loot_item.get("id"), "name": loot_item.get("name"),
                                    "equipment_type": loot_item.get("equipment_type"), "rarity": loot_item.get("rarity"),
                                    "attack": stat_bonus.get("attack", 0), "defense": stat_bonus.get("defense", 0),
                                    "energy": stat_bonus.get("energy", 0), "maintenance": stat_bonus.get("maintenance", 0),
                                    "happiness": stat_bonus.get("happiness", 0)
                                })
                    
                    # Update equipment in survivor_updates
                    survivor_updates[str(user_id)]['equipment'] = looted_equipment
                    
                    # Prepare batch updates
                    pet_data_updates[str(user_id)] = pet
                    
                    self.rewards['survivors'].append({
                        'user': data['user'], 'reward': total_reward, 'pet_name': pet['name'], 'equipment': looted_equipment
                    })
            
            # Batch save all pet data
            if pet_data_updates:
                await user_data_manager.batch_save_user_data(pet_data_updates, "pet_data")
            
            # Update energon for survivors and send level-up embeds
            for user_id, survivor_data in survivor_updates.items():
                user_data = await user_data_manager.get_user_data(user_id, None)
                current_energon = user_data['energon'].get('energon', 0)
                user_data['energon']['energon'] = current_energon + survivor_data['reward']
                await user_data_manager.save_user_data(user_id, None, user_data)
                
                # Send level-up embed if pet leveled up
                if 'level_up' in survivor_data:
                    from .pet_levels import create_level_up_embed
                    pet = await user_data_manager.get_pet_data(user_id)
                    if pet:
                        level_up_embed = await create_level_up_embed(pet, survivor_data['level_up'], int(user_id))
                        try:
                            await self.ctx.channel.send(embed=level_up_embed)
                        except Exception as e:
                            logger.error(f"Error sending level-up embed: {e}")
            
            logger.info(f"Battle victory: {total_reward} energon awarded")
            
        except Exception as e:
            logger.error(f"Error handling victory: {e}")

    async def handle_defeat(self):
        """Handle battle defeat with batch operations"""
        try:
            pet_updates = {}
            for user_id, data in self.player_data.items():
                pet = data['pet']
                pet['battles_lost'] = pet.get('battles_lost', 0) + 1
                
                max_hp = pet.get('energy', 100) + pet.get('maintenance', 0) + pet.get('happiness', 0)
                health_loss_per_stat = max_hp // 3
                remaining_loss = max_hp % 3
                
                pet['energy'] = max(0, pet['energy'] - health_loss_per_stat - (1 if remaining_loss > 0 else 0))
                pet['maintenance'] = max(0, pet['maintenance'] - health_loss_per_stat - (1 if remaining_loss > 1 else 0))
                pet['happiness'] = max(0, pet['happiness'] - health_loss_per_stat)
                
                pet_updates[str(user_id)] = pet
            
            # Batch save all pet data
            if pet_updates:
                await user_data_manager.batch_save_user_data(pet_updates, "pet_data")
                
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
        
        target_name = next((data['user'].display_name for uid, data in 
                          self.battle_view.player_data.items() if uid == target_id), "Unknown")
        
        await interaction.response.send_message(
            f"🛡️ You will defend **{target_name}** this turn!",
            ephemeral=True,
            delete_after=5
        )
        
        # Delete the original message
        try:
            await interaction.message.delete()
        except:
            pass
        
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
        
        # Send ephemeral confirmation and delete the message
        action_emojis = {"attack": "⚔️", "defend": "🛡️", "charge": "⚡"}
        emoji = action_emojis.get(action, "✅")
        
        await interaction.response.send_message(
            f"{emoji} **{action.title()}** selected!", 
            ephemeral=True, 
            delete_after=2
        )
        
        # Delete the original action message
        try:
            await interaction.message.delete()
        except:
            # Fallback if deletion fails
            await interaction.message.edit(view=None, delete_after=1)
        
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