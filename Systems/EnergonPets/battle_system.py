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
        asyncio.create_task(self.add_participant(ctx.author))
    
    async def add_participant(self, user):
        """Add a participant to the battle"""
        try:
            pet = await user_data_manager.get_pet_data(str(user.id))
            if pet:
                self.battle_view.participants.append((user, pet))
                if self.message:
                    try:
                        embed = self.battle_view.build_join_embed()
                        await self.message.edit(embed=embed)
                    except Exception as e:
                        logger.error(f"Error updating join embed: {e}")
        except Exception as e:
            logger.error(f"Error adding participant: {e}")
    
    @discord.ui.button(label="Join Battle", style=discord.ButtonStyle.green, emoji="⚔️")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle user joining the battle"""
        if len(self.battle_view.participants) >= self.battle_view.max_participants:
            await interaction.response.send_message("❌ Battle is full!", ephemeral=True)
            return
        for user, _ in self.battle_view.participants:
            if user.id == interaction.user.id:
                await interaction.response.send_message("❌ You're already in this battle!", ephemeral=True)
                return        
        try:
            pet = await user_data_manager.get_pet_data(str(interaction.user.id))
            if not pet:
                await interaction.response.send_message("❌ You don't have a pet! Use `/hatch` to get one.", ephemeral=True)
                return
            self.battle_view.participants.append((interaction.user, pet))
            embed = self.battle_view.build_join_embed()
            await interaction.message.edit(embed=embed)            
            await interaction.response.send_message("✅ Joined the battle!", ephemeral=True)           
        except Exception as e:
            logger.error(f"Error joining battle: {e}")
            await interaction.response.send_message("❌ Error joining battle. Please try again.", ephemeral=True)    

    @discord.ui.button(label="Leave Battle", style=discord.ButtonStyle.red, emoji="🚪")
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle user leaving the battle"""
        for i, (user, _) in enumerate(self.battle_view.participants):
            if user.id == interaction.user.id:
                self.battle_view.participants.pop(i)
                embed = self.battle_view.build_join_embed()
                await interaction.message.edit(embed=embed)               
                await interaction.response.send_message("✅ Left the battle!", ephemeral=True)
                return        
        await interaction.response.send_message("❌ You're not in this battle!", ephemeral=True)   

    @discord.ui.button(label="Start Battle", style=discord.ButtonStyle.blurple, emoji="🚀")
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle battle start (only creator can start)"""
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Only the battle creator can start!", ephemeral=True)
            return           
        if len(self.battle_view.participants) < 1:
            await interaction.response.send_message("❌ Need at least 1 participant!", ephemeral=True)
            return
        await interaction.response.defer()
        await interaction.message.edit(view=None)
        self.battle_view.battle_started = True
        spectator_embed = self.battle_view.build_spectator_embed("Battle started! Good luck!")
        await interaction.message.edit(embed=spectator_embed)
        await self.battle_view.start_action_collection()

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
 
    @classmethod
    async def create_async(cls, ctx, battle_type="solo", participants=None, 
                          selected_enemy_type=None, selected_rarity=None, 
                          target_user=None):
        """Async factory method to create battle with loaded data"""
        # PvP battles are no longer supported view
            
        view = cls(ctx, battle_type, participants, None, selected_enemy_type, 
                  selected_rarity)
        
        # Ensure we have valid enemy type and rarity
        if not selected_enemy_type or not selected_rarity:
            selected_enemy_type = selected_enemy_type or "monster"
            selected_rarity = selected_rarity or "common"
            
        if battle_type == "solo":
            pet = await user_data_manager.get_pet_data(str(ctx.author.id))
            if not pet:
                # Create a basic pet if user doesn't have one
                pet = {
                    'name': 'Default Pet',
                    'attack': 10,
                    'defense': 5,
                    'energy': 100,
                    'maintenance': 0,
                    'happiness': 0,
                    'level': 1,
                    'equipment': {}
                }
            view.participants = [(ctx.author, pet)]
            view.monster = await view.get_monster_by_type_and_rarity(selected_enemy_type, selected_rarity)
            if not view.monster:
                view.monster = view._create_fallback_monster(selected_enemy_type, selected_rarity)
                           
        elif battle_type == "group":
            if not participants:
                pet = await user_data_manager.get_pet_data(str(ctx.author.id))
                if not pet:
                    pet = {
                        'name': 'Default Pet',
                        'attack': 10,
                        'defense': 5,
                        'energy': 100,
                        'maintenance': 0,
                        'happiness': 0,
                        'level': 1,
                        'equipment': {}
                    }
                view.participants = [(ctx.author, pet)]
            else:
                loaded_participants = []
                for user, _ in participants:
                    pet = await user_data_manager.get_pet_data(str(user.id))
                    if not pet:
                        pet = {
                            'name': 'Default Pet',
                            'attack': 10,
                            'defense': 5,
                            'energy': 100,
                            'maintenance': 0,
                            'happiness': 0,
                            'level': 1,
                            'equipment': {}
                        }
                    loaded_participants.append((user, pet))
                view.participants = loaded_participants
            view.monster = await view.get_monster_by_type_and_rarity(selected_enemy_type, selected_rarity)
            if not view.monster:
                view.monster = view._create_fallback_monster(selected_enemy_type, selected_rarity)
                
        # Ensure monster is properly initialized
        if view.monster:
            view.monster_hp = view.monster['health']
            view.max_monster_hp = view.monster['health']
            
        view.initialize_battle_data()
        return view

    async def get_monster_by_type_and_rarity(self, enemy_type: str, rarity: str) -> Dict[str, Any]:
        """Get monster data from user_data_manager"""
        try:
            # Load monsters and bosses data from user_data_manager
            data = await user_data_manager.get_monsters_and_bosses()
            
            # Handle nested structure - fix data loading issue
            filtered = []
            
            # Load monsters (handle nested structure)
            monsters_container = data.get('monsters', {})
            if isinstance(monsters_container, dict) and 'monsters' in monsters_container:
                actual_monsters = monsters_container['monsters']
            else:
                actual_monsters = monsters_container if isinstance(monsters_container, dict) else {}
            
            for monster_id, monster_data in actual_monsters.items():
                if isinstance(monster_data, dict):
                    monster_type = str(monster_data.get('type', '')).lower()
                    monster_rarity = str(monster_data.get('rarity', '')).lower()
                    
                    if monster_type == str(enemy_type).lower() and monster_rarity == str(rarity).lower():
                        filtered.append(monster_data)
            
            # Load bosses (handle nested structure)
            bosses_container = data.get('bosses', {})
            if isinstance(bosses_container, dict) and 'bosses' in bosses_container:
                actual_bosses = bosses_container['bosses']
            else:
                actual_bosses = bosses_container if isinstance(bosses_container, dict) else {}
            
            for boss_id, boss_data in actual_bosses.items():
                if isinstance(boss_data, dict):
                    boss_type = str(boss_data.get('type', '')).lower()
                    boss_rarity = str(boss_data.get('rarity', '')).lower()
                    
                    if boss_type == str(enemy_type).lower() and boss_rarity == str(rarity).lower():
                        filtered.append(boss_data)
            
            # Load titans (handle nested structure)
            titans_container = data.get('titans', {})
            if isinstance(titans_container, dict) and 'titans' in titans_container:
                actual_titans = titans_container['titans']
            else:
                actual_titans = titans_container if isinstance(titans_container, dict) else {}
            
            for titan_id, titan_data in actual_titans.items():
                if isinstance(titan_data, dict):
                    titan_type = str(titan_data.get('type', '')).lower()
                    titan_rarity = str(titan_data.get('rarity', '')).lower()
                    
                    if titan_type == str(enemy_type).lower() and titan_rarity == str(rarity).lower():
                        filtered.append(titan_data)
            
            if filtered:
                monster = random.choice(filtered)
                return {
                    "name": str(monster.get('name', f'{rarity.title()} {enemy_type.title()}')),
                    "health": int(monster.get('health', 100)),
                    "attack": int(monster.get('attack', 10)),
                    "defense": int(monster.get('defense', 5)),
                    "type": str(monster.get('type', enemy_type)),
                    "rarity": str(monster.get('rarity', rarity)),
                    "description": str(monster.get('description', f'A {rarity} {enemy_type}')),
                    "energon_reward": int(monster.get('energon_reward', 10)),
                    "experience_reward": int(monster.get('experience_reward', 5)),
                    "loot": monster.get('loot', []),  # Include loot data if available
                    "special_abilities": monster.get('special_abilities', []),
                    "weaknesses": monster.get('weaknesses', [])
                }
                
        except Exception as e:
            logger.error(f"Error loading monster from user_data_manager: {e}")
            
        # Return fallback monster
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
        if self.monster:
            self.monster_hp = self.monster['health']
            self.max_monster_hp = self.monster['health']
  
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
        
        # Send ephemeral action buttons to each alive player
        for user_id, player_data in self.player_data.items():
            if player_data['alive'] and player_data['hp'] > 0:
                try:
                    user = player_data['user']
                    action_view = ChannelBattleActionView(self, user_id)
                    
                    # Send ephemeral message with action buttons (no embed)
                    await self.ctx.channel.send(
                        f"⚔️ **{player_data['pet']['name']}** - Choose your action:",
                        view=action_view,
                        ephemeral=True,
                        delete_after=300  # Auto-delete after 5 minutes
                    )
                except discord.HTTPException as e:
                    logger.error(f"Error sending ephemeral action message to user {user_id}: {e}")
        
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
        """Process a round for PvE battles"""
        action_text = f"⚔️ **Round {self.turn_count + 1} Results**\n\n"
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
                action_text += f"⚔️ **{player_data['user'].display_name}** attacks! Rolled {player_roll} → {attack_power} damage, reduced by {monster_defense} defense → {reduced_damage} damage dealt\n"           
            elif action_data['action'] == "defend":
                block_roll = self.roll_d20()
                total_defense = player_data.get('total_defense', player_data['pet'].get('defense', 5))
                block_stat = int(total_defense * self.calculate_attack_multiplier(block_roll))
                self.defending_players.add(player_data['user'].id)
                action_text += f"🛡️ **{player_data['user'].display_name}** is defending! Rolled {block_roll} → Block: {block_stat}\n"          
            elif action_data['action'] == "charge":
                player_data['charge'] = min(5.0, player_data['charge'] * 2)
                player_data['charging'] = True
                action_text += f"⚡ **{player_data['user'].display_name}** is charging! Next attack multiplier: x{player_data['charge']:.1f}\n"
        if self.monster_hp > 0:
            monster_roll = self.roll_d20()
            monster_multiplier = self.calculate_attack_multiplier(monster_roll)           
            if monster_action == "attack":
                monster_attack = int(self.monster.get('attack', 15) * monster_multiplier)
                defending_pets = [data for uid, data in self.player_data.items() if uid in self.defending_players]
                if defending_pets:
                    action_text += f"💥 **{self.monster['name']}** attacks! Rolled {monster_roll} → {monster_attack} damage\n"
                    damage_per_defender = max(1, monster_attack // len(defending_pets))                   
                    for defender_data in defending_pets:
                        block_roll = self.roll_d20()
                        total_defense = defender_data.get('total_defense', defender_data['pet'].get('defense', 5))
                        block_stat = int(total_defense * self.calculate_attack_multiplier(block_roll))                       
                        if block_stat >= damage_per_defender:
                            parry_damage = block_stat - damage_per_defender
                            action_text += f"🛡️ **{defender_data['user'].display_name}** parries! Block: {block_stat} ≥ Attack: {damage_per_defender}\n"
                            if parry_damage > 0:
                                self.monster_hp = max(0, self.monster_hp - parry_damage)
                                action_text += f"⚡ Parry damage: {parry_damage} dealt to {self.monster['name']}\n"
                        else:
                            damage_taken = damage_per_defender - block_stat
                            defender_data['hp'] = max(0, defender_data['hp'] - damage_taken)
                            action_text += f"💔 **{defender_data['user'].display_name}** takes {damage_taken} damage\n"
                else:
                    alive_players = [data for data in self.player_data.values() if data['alive']]
                    if alive_players:
                        damage_per_player = max(1, monster_attack // len(alive_players))
                        for player_data in alive_players:
                            player_data['hp'] = max(0, player_data['hp'] - damage_per_player)
                        action_text += f"💥 **{self.monster['name']}** attacks everyone! Rolled {monster_roll} → {monster_attack} damage split among {len(alive_players)} players → {damage_per_player} each\n"                      
            elif monster_action == "defend":
                action_text += f"🛡️ **{self.monster['name']}** is defending!\n"                
            elif monster_action == "charge":
                self.monster_charge_multiplier = min(5.0, self.monster_charge_multiplier * 2)
                action_text += f"⚡ **{self.monster['name']}** is charging! Next attack multiplier: x{self.monster_charge_multiplier:.1f}\n"
        self.defending_players.clear()
        for player_data in self.player_data.values():
            player_data['charging'] = False
        await self.check_victory_conditions()        
        if not self.battle_over:
            spectator_embed = self.build_spectator_embed(action_text)
            try:
                await self.message.edit(embed=spectator_embed)
                await self.start_action_collection()
            except discord.NotFound:
                # Message was deleted, send new message instead
                self.message = await self.ctx.channel.send(embed=spectator_embed)
                await self.start_action_collection()
        else:
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
        for user_id, data in self.player_data.items():
            user = data['user']
            pet = data['pet']
            hp_bar = self.create_hp_bar(data['hp'], data['max_hp'], "pet", pet)
            charge_info = f" ⚡x{data['charge']:.1f}" if data['charge'] > 1.0 else ""
            charging_info = " 🔋" if data['charging'] else ""
            defending_info = " 🛡️" if user_id in self.defending_players else ""
            status = "💀" if not data['alive'] else "➡️" if user_id == current_player['user'].id else "🟢"
            status_lines.append(f"{status} {user.display_name} - {pet['name']}{charge_info}{charging_info}{defending_info}\n{hp_bar}")
        
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
        """Build simple victory message embed"""
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

    def find_pvp_target(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Find PvP target"""
        for uid, data in self.player_data.items():
            if uid != user_id and data['alive']:
                return data
        return None

    async def process_turn(self, player_action: str, user_id: int) -> str:
        """Process a single turn - now used for action collection in DM mode"""
        if self.battle_over:
            return "Battle is over!"
        
        player_data = self.player_data.get(user_id)
        if not player_data or not player_data['alive']:
            return "Invalid or defeated player!"
        
        # Store action for DM-based processing
        self.player_actions[user_id] = {
            'action': player_action,
            'target': None  # Will be set by PvP targeting if needed
        }
        
        # Check if all players have submitted actions
        await self.check_all_actions_submitted()
        
        return "Action collected! Waiting for all players to choose their actions..."

    async def process_combat_action(self, player_data: Dict[str, Any], monster_action: str, player_action: str) -> str:
        """Process combat between player and monster"""
        action_text = f"**{player_data['user'].display_name}** vs **{self.monster['name']}**\n"
        
        # Player action
        player_roll = self.roll_d20()
        player_multiplier = self.calculate_attack_multiplier(player_roll)
        
        if player_action == "attack":
            total_attack = player_data.get('total_attack', player_data['pet'].get('attack', 10))
            attack_power = int(total_attack * player_data['charge'] * player_multiplier)
            monster_defense = self.monster.get('defense', 5) // 2
            reduced_damage = max(1, attack_power - monster_defense)
            self.monster_hp = max(0, self.monster_hp - reduced_damage)
            action_text += f"⚔️ Attack! Rolled {player_roll} → {attack_power} damage, reduced by {monster_defense} defense → {reduced_damage} damage dealt\n"
            
        elif player_action == "defend":
            # Individual defense for all battle types
                if self.battle_type in ["solo", "group"] and self.monster:
                    # Each defending pet defends individually
                    self.defending_players.add(player_data['user'].id)
                    
                    block_roll = self.roll_d20()
                    total_defense = player_data.get('total_defense', player_data['pet'].get('defense', 5))
                    block_stat = int(total_defense * self.calculate_attack_multiplier(block_roll))
                    
                    action_text += f"🛡️ **{player_data['user'].display_name}** is defending! Rolled {block_roll} → Block: {block_stat}\n"
                else:
                    # Parry system for solo battles
                    block_roll = self.roll_d20()
                    total_defense = player_data.get('total_defense', player_data['pet'].get('defense', 5))
                    block_stat = int(total_defense * self.calculate_attack_multiplier(block_roll))
                    action_text += f"🛡️ **{player_data['user'].display_name}** is defending! Rolled {block_roll} → Block: {block_stat}\n"
            
        elif player_action == "charge":
            player_data['charge'] = min(5.0, player_data['charge'] * 2)
            player_data['charging'] = True
            action_text += f"⚡ Charging! Next attack multiplier: x{player_data['charge']:.1f}\n"
        
        # Monster action (if alive)
        if self.monster_hp > 0:
            monster_roll = self.roll_d20()
            monster_multiplier = self.calculate_attack_multiplier(monster_roll)
            
            if monster_action == "attack":
                monster_attack = int(self.monster.get('attack', 15) * monster_multiplier)
                
                # Individual parry system for group battles
                defending_pets = [data for uid, data in self.player_data.items() if uid in self.defending_players]
                
                if defending_pets:
                    action_text += f"💥 Monster attacks! Rolled {monster_roll} → {monster_attack} damage\n"
                    
                    # Each defending pet gets their own parry attempt
                    for defender_data in defending_pets:
                        block_roll = self.roll_d20()
                        block_stat = int(defender_data['pet'].get('defense', 5) * self.calculate_attack_multiplier(block_roll))
                        
                        if block_stat >= monster_attack:
                            # Successful parry - no damage taken, excess as parry damage
                            parry_damage = block_stat - monster_attack
                            self.monster_hp = max(0, self.monster_hp - parry_damage)
                            action_text += f"🛡️ **{defender_data['user'].display_name}** parries! Block: {block_stat} ≥ Attack: {monster_attack}\n"
                            if parry_damage > 0:
                                action_text += f"⚡ Parry damage: {parry_damage} dealt to {self.monster['name']}\n"
                        else:
                            # Failed parry - take remaining damage
                            damage_taken = monster_attack - block_stat
                            defender_data['hp'] = max(0, defender_data['hp'] - damage_taken)
                            action_text += f"🛡️ **{defender_data['user'].display_name}** attempts to parry! Block: {block_stat} < Attack: {monster_attack}\n"
                            action_text += f"💔 Takes {damage_taken} damage\n"
                    
                    # Non-defending pets take full damage (with defense reduction)
                    non_defending_pets = [data for uid, data in self.player_data.items() if uid not in self.defending_players]
                    for defender_data in non_defending_pets:
                        total_defense = defender_data.get('total_defense', defender_data['pet'].get('defense', 5))
                        player_defense = total_defense // 2
                        reduced_damage = max(1, monster_attack - player_defense)
                        defender_data['hp'] = max(0, defender_data['hp'] - reduced_damage)
                        action_text += f"💔 **{defender_data['user'].display_name}** takes {reduced_damage} damage (defense reduced by {player_defense})\n"
                
                # New parry system for non-group battles
                elif player_action == "defend":
                    # Calculate block stat for parry (using the same roll as player action)
                    block_roll = self.roll_d20()
                    block_stat = int(player_data['pet'].get('defense', 5) * self.calculate_attack_multiplier(block_roll))
                    
                    if block_stat >= monster_attack:
                        # Successful parry - no damage taken, excess as parry damage
                        parry_damage = block_stat - monster_attack
                        self.monster_hp = max(0, self.monster_hp - parry_damage)
                        action_text += f"💥 Monster attacks! Rolled {monster_roll} → {monster_attack} damage\n"
                        action_text += f"🛡️ **{player_data['user'].display_name}** parries! Block: {block_stat} ≥ Attack: {monster_attack}\n"
                        if parry_damage > 0:
                            action_text += f"⚡ Parry damage: {parry_damage} dealt to {self.monster['name']}\n"
                    else:
                        # Failed parry - take remaining damage
                        damage_taken = monster_attack - block_stat
                        player_data['hp'] = max(0, player_data['hp'] - damage_taken)
                        action_text += f"💥 Monster attacks! Rolled {monster_roll} → {monster_attack} damage\n"
                        action_text += f"🛡️ **{player_data['user'].display_name}** attempts to parry! Block: {block_stat} < Attack: {monster_attack}\n"
                        action_text += f"💔 Takes {damage_taken} damage\n"
                else:
                    # Regular attack against all players in group battle with defense reduction
                    for uid, data in self.player_data.items():
                        player_defense = data['pet'].get('defense', 5) // 2
                        reduced_damage = max(1, monster_attack - player_defense)
                        data['hp'] = max(0, data['hp'] - reduced_damage)
                    action_text += f"💥 Monster attacks! Rolled {monster_roll} → {monster_attack} damage, reduced by defense → {reduced_damage} damage dealt\n"
                
            elif monster_action == "charge":
                self.monster_charge_multiplier = min(5.0, self.monster_charge_multiplier * 2)
                action_text += f"🔋 Monster is charging!\n"
        
        # Reset defending players at end of turn
        self.defending_players.clear()
        
        return action_text

    async def process_pvp_action(self, attacker_data: Dict[str, Any], defender_data: Dict[str, Any], action: str) -> str:
        """Process PvP combat action"""
        action_text = f"**{attacker_data['user'].display_name}** vs **{defender_data['user'].display_name}**\n"
        
        roll = self.roll_d20()
        multiplier = self.calculate_attack_multiplier(roll)
        
        if action == "attack":
            attack_damage = int(attacker_data['pet'].get('attack', 10) * attacker_data['charge'] * multiplier)
            
            # Check if defender is defending (parry system)
            if defender_data['charging']:
                # Defender is using defend action - calculate block for parry
                block_roll = self.roll_d20()
                block_stat = int(defender_data['pet'].get('defense', 5) * self.calculate_attack_multiplier(block_roll))
                
                if block_stat >= attack_damage:
                    # Successful parry - no damage taken, excess as parry damage
                    parry_damage = block_stat - attack_damage
                    attacker_data['hp'] = max(0, attacker_data['hp'] - parry_damage)
                    action_text += f"⚔️ {attacker_data['user'].display_name} attacks! Rolled {roll} → {attack_damage} damage\n"
                    action_text += f"🛡️ **{defender_data['user'].display_name}** parries! Block: {block_stat} ≥ Attack: {attack_damage}\n"
                    if parry_damage > 0:
                        action_text += f"⚡ Parry damage: {parry_damage} dealt to {attacker_data['user'].display_name}\n"
                else:
                    # Failed parry - take remaining damage
                    damage_taken = attack_damage - block_stat
                    defender_data['hp'] = max(0, defender_data['hp'] - damage_taken)
                    action_text += f"⚔️ {attacker_data['user'].display_name} attacks! Rolled {roll} → {attack_damage} damage\n"
                    action_text += f"🛡️ **{defender_data['user'].display_name}** attempts to parry! Block: {block_stat} < Attack: {attack_damage}\n"
                    action_text += f"💔 Takes {damage_taken} damage\n"
            else:
                # Regular attack with defense reduction
                defender_defense = defender_data['pet'].get('defense', 5) // 2
                reduced_damage = max(1, attack_damage - defender_defense)
                defender_data['hp'] = max(0, defender_data['hp'] - reduced_damage)
                action_text += f"⚔️ {attacker_data['user'].display_name} attacks! Rolled {roll} → {attack_damage} damage, reduced by {defender_defense} defense → {reduced_damage} damage dealt\n"
            
        elif action == "defend":
            # New parry system for PvP battles
            block_roll = self.roll_d20()
            block_stat = int(attacker_data['pet'].get('defense', 5) * self.calculate_attack_multiplier(block_roll))
            action_text += f"🛡️ **{attacker_data['user'].display_name}** is defending! Rolled {block_roll} → Block: {block_stat}\n"
            
        elif action == "charge":
            attacker_data['charge'] = min(5.0, attacker_data['charge'] * 2)
            action_text += f"⚡ {attacker_data['user'].display_name} is charging!\n"
        
        return action_text

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
        """Handle battle victory and rewards"""
        try:
            # Calculate rewards
            base_reward = self.monster.get('health', 100) // 10
            rarity_multipliers = {"common": 1, "uncommon": 1.5, "rare": 2, "epic": 3, "legendary": 5, "mythic": 10}
            type_multipliers = {"monster": 1, "boss": 2, "titan": 5}
            
            total_reward = int(base_reward * 
                             rarity_multipliers.get(self.monster.get('rarity', 'common'), 1) * 
                             type_multipliers.get(self.monster.get('type', 'monster'), 1))
            
            # Store rewards for final display
            self.rewards = {
                'type': 'victory',
                'total_reward': total_reward,
                'survivors': [],
                'equipment_loot': {}  # Track equipment looted by user
            }
            
            looted_equipment_ids = []
            
            for user_id, data in self.player_data.items():
                if data['alive'] and data['hp'] > 0:
                    # Update pet stats
                    pet = data['pet']
                    pet['battles_won'] = pet.get('battles_won', 0) + 1
                    pet['experience'] = pet.get('experience', 0) + total_reward
                    
                    max_hp = pet.get('energy', 100) + pet.get('maintenance', 0) + pet.get('happiness', 0)
                    damage_taken = max_hp - data['hp']

                    health_loss_per_stat = damage_taken // 3
                    remaining_loss = damage_taken % 3
                    
                    pet['energy'] = max(0, pet['energy'] - health_loss_per_stat - (1 if remaining_loss > 0 else 0))
                    pet['maintenance'] = max(0, pet['maintenance'] - health_loss_per_stat - (1 if remaining_loss > 1 else 0))
                    pet['happiness'] = max(0, pet['happiness'] - health_loss_per_stat)
                    
                    user_data = await user_data_manager.get_user_data(str(user_id), data['user'].display_name)
                    current_energon = user_data['energon'].get('energon', 0)
                    new_total = current_energon + total_reward
                    user_data['energon']['energon'] = new_total
                    
                    WIN_CONDITION = 10000 
                    
                    game_state = await user_data_manager.get_energon_data(str(user_id))
                    
                    try:
                        if game_state.get("in_energon_rush", False):
                            # Check if this gain puts them over the win threshold
                            if current_energon < WIN_CONDITION and new_total >= WIN_CONDITION:
                                # Mark game as ended and announce winner
                                game_state['in_energon_rush'] = False
                                await user_data_manager.save_energon_data(str(user_id), game_state)
                                # Add win message to battle results
                                self.rewards['survivors'][-1]['win_message'] = f"\n🎉 **ENERGON RUSH CHAMPION!** With {new_total} total energon, you've won the energon rush game!"
                    except Exception as e:
                        print(f"Error checking energon rush win: {e}")
                    
                    # Save updates
                    await user_data_manager.save_pet_data(str(user_id), data['user'].display_name, pet)
                    await user_data_manager.save_user_data(str(user_id), data['user'].display_name, user_data)
                    
                    # Equipment looting for NPC battles (monsters, bosses, titans)
                    looted_equipment = None
                    if self.monster.get('type') in ['monster', 'boss', 'titan']:
                        # Calculate health percentage remaining
                        max_hp = pet.get('energy', 100) + pet.get('maintenance', 0) + pet.get('happiness', 0)
                        health_percentage = data['hp'] / max_hp
                        
                        # Calculate loot chance based on health remaining
                        loot_chance = self.calculate_loot_chance(health_percentage)
                        
                        # Check if we should loot an item
                        if random.random() <= loot_chance:
                            monster_rarity = self.monster.get('rarity', 'common')
                            looted_equipment = await self.get_random_equipment_by_rarity(
                                monster_rarity, 
                                exclude_ids=looted_equipment_ids
                            )
                            
                            if looted_equipment:
                                looted_equipment_ids.append(looted_equipment['id'])
                                self.rewards['equipment_loot'][user_id] = looted_equipment
                                
                                # Add looted equipment to user's inventory
                                try:
                                    pet_data = await user_data_manager.get_pet_data(user_id)
                                    if pet_data:
                                        if "inventory" not in pet_data:
                                            pet_data["inventory"] = []
                                        
                                        # Ensure item has required fields
                                        stat_bonus = looted_equipment.get("stat_bonus", {})
                                        item_to_add = {
                                            "id": looted_equipment.get("id"),
                                            "name": looted_equipment.get("name"),
                                            "equipment_type": looted_equipment.get("equipment_type"),
                                            "rarity": looted_equipment.get("rarity"),
                                            "attack": stat_bonus.get("attack", 0),
                                            "defense": stat_bonus.get("defense", 0),
                                            "energy": stat_bonus.get("energy", 0),
                                            "maintenance": stat_bonus.get("maintenance", 0),
                                            "happiness": stat_bonus.get("happiness", 0)
                                        }
                                        
                                        pet_data["inventory"].append(item_to_add)
                                        await user_data_manager.save_pet_data(user_id, None, pet_data)
                                        logger.info(f"Added looted equipment '{looted_equipment['name']}' to user {user_id}'s inventory")
                                except Exception as e:
                                    logger.error(f"Error adding looted equipment to inventory: {e}")
                    
                    # Store survivor info for rewards display
                    self.rewards['survivors'].append({
                        'user': data['user'],
                        'reward': total_reward,
                        'pet_name': pet['name'],
                        'equipment': looted_equipment
                    })
            
            logger.info(f"Battle victory: {total_reward} energon awarded")
            
        except Exception as e:
            logger.error(f"Error handling victory: {e}")

    async def handle_defeat(self):
        """Handle battle defeat"""
        try:
            for user_id, data in self.player_data.items():
                pet = data['pet']
                pet['battles_lost'] = pet.get('battles_lost', 0) + 1
                
                # Calculate health loss - defeat means full health loss
                max_hp = pet.get('energy', 100) + pet.get('maintenance', 0) + pet.get('happiness', 0)
                
                # Distribute health loss equally among Energy, Maintenance, and Happiness
                health_loss_per_stat = max_hp // 3
                remaining_loss = max_hp % 3
                
                # Apply health loss
                pet['energy'] = max(0, pet['energy'] - health_loss_per_stat - (1 if remaining_loss > 0 else 0))
                pet['maintenance'] = max(0, pet['maintenance'] - health_loss_per_stat - (1 if remaining_loss > 1 else 0))
                pet['happiness'] = max(0, pet['happiness'] - health_loss_per_stat)
                
                await user_data_manager.save_pet_data(str(user_id), data['user'].display_name, pet)
                
            logger.info("Battle defeat handled")
            
        except Exception as e:
            logger.error(f"Error handling defeat: {e}")

    def build_final_battle_embed(self, action_text: str = "") -> discord.Embed:
        """Build final battle embed showing results"""
        embed = discord.Embed(
            title="🏁 Battle Results",
            color=0x00ff00
        )
        
        # Determine winner(s)
        alive_players = [data for data in self.player_data.values() if data['alive'] and data['hp'] > 0]
        
        if self.monster and self.monster_hp <= 0:
            embed.description = f"🎉 Victory! {self.monster['name']} has been defeated!"
        elif len(alive_players) == 1:
            embed.description = f"🏆 **{alive_players[0]['user'].display_name}** is the winner!"
        elif len(alive_players) == 0:
            embed.description = "🤝 The battle ended in a draw!"
        else:
            embed.description = "🎮 Battle concluded!"
        
        # Show final standings and rewards
        for user_id, data in self.player_data.items():
            status = "🟢 Alive" if data['hp'] > 0 else "🔴 Defeated"
            
            # Build reward text
            reward_text = f"Final HP: {data['hp']}/{data['max_hp']}"
            
            # Check for equipment loot
            if hasattr(self, 'rewards') and 'equipment_loot' in self.rewards:
                equipment = self.rewards['equipment_loot'].get(user_id)
                if equipment:
                    rarity_emoji = RARITY_EMOJIS.get(equipment.get('rarity', 'common'), '⚪')
                    type_emoji = {
                        'chassis_plating': '🛡️',
                        'energy_cores': '⚡',
                        'utility_modules': '🔧'
                    }.get(equipment.get('equipment_type'), '📦')
                    
                    reward_text += f"\n{type_emoji} **Looted:** {rarity_emoji} {equipment.get('name', 'Unknown Item')}"
            
            embed.add_field(
                name=f"{data['user'].display_name} - {status}",
                value=reward_text,
                inline=False
            )
        
        if action_text:
            embed.add_field(name="📜 Final Round", value=action_text[:1024], inline=False)
        
        return embed

    def generate_battle_log(self, action_text: str) -> List[str]:
        """Generate detailed battle log messages"""
        messages = []
        
        # Split action text into manageable chunks
        lines = action_text.split('\n')
        current_message = ""
        
        for line in lines:
            if len(current_message + line + '\n') > 1800:
                messages.append(current_message)
                current_message = line + '\n'
            else:
                current_message += line + '\n'
        
        if current_message:
            messages.append(current_message)
        
        return messages

class ChannelBattleActionView(discord.ui.View):
    """Channel-based action view for ephemeral battle actions"""
    
    def __init__(self, battle_view: UnifiedBattleView, user_id: int):
        super().__init__(timeout=300)  # 5 minute timeout
        self.battle_view = battle_view
        self.user_id = user_id

    @discord.ui.button(label="Attack", style=discord.ButtonStyle.red, emoji="⚔️", row=0)
    async def attack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your action message!", ephemeral=True, delete_after=3)
            return
        await self.handle_player_action(interaction, "attack")

    @discord.ui.button(label="Defend", style=discord.ButtonStyle.blurple, emoji="🛡️", row=0)
    async def defend_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your action message!", ephemeral=True, delete_after=3)
            return
        await self.handle_player_action(interaction, "defend")

    @discord.ui.button(label="Charge", style=discord.ButtonStyle.green, emoji="⚡", row=0)
    async def charge_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your action message!", ephemeral=True, delete_after=3)
            return
        await self.handle_player_action(interaction, "charge")

    async def handle_player_action(self, interaction: discord.Interaction, action: str):
        """Handle player action selection via ephemeral messages in main channel"""
        player_id = interaction.user.id
        
        # Check if player is in the battle
        if player_id not in self.battle_view.player_data:
            await interaction.response.send_message("❌ You're not in this battle!", ephemeral=True, delete_after=5)
            return
            
        player_data = self.battle_view.player_data[player_id]
        
        # Check if player is alive
        if not player_data['alive'] or player_data['hp'] <= 0:
            await interaction.response.send_message("❌ You've been defeated!", ephemeral=True, delete_after=5)
            return
            
        # Check if action was already submitted
        if player_id in self.battle_view.player_actions:
            await interaction.response.send_message("✅ You've already chosen your action!", ephemeral=True, delete_after=5)
            return
            
        # Store the action
        self.battle_view.player_actions[player_id] = {
            'action': action,
            'target': None
        }
        
        # Delete the ephemeral message (dismissable)
        try:
            await interaction.message.delete()
        except:
            pass
            
        # Send ephemeral confirmation
        await interaction.response.send_message(f"✅ Action **{action.title()}** selected!", ephemeral=True, delete_after=2)
        
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