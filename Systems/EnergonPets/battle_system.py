import discord
import random
import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

# Import the unified user data manager
from Systems.user_data_manager import user_data_manager

# Set up logging
logger = logging.getLogger('battle_system')

# Emoji mappings for battle system
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
        
        # Auto-add the command initiator
        asyncio.create_task(self.add_participant(ctx.author))
    
    async def add_participant(self, user):
        """Add a participant to the battle"""
        try:
            pet = await user_data_manager.get_pet_data(str(user.id))
            if pet:
                self.battle_view.participants.append((user, pet))
                if self.message:
                    embed = self.battle_view.build_join_embed()
                    await self.message.edit(embed=embed)
        except Exception as e:
            logger.error(f"Error adding participant: {e}")
    
    @discord.ui.button(label="Join Battle", style=discord.ButtonStyle.green, emoji="⚔️")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle user joining the battle"""
        if len(self.battle_view.participants) >= self.battle_view.max_participants:
            await interaction.response.send_message("❌ Battle is full!", ephemeral=True)
            return
            
        # Check if user is already in
        for user, _ in self.battle_view.participants:
            if user.id == interaction.user.id:
                await interaction.response.send_message("❌ You're already in this battle!", ephemeral=True)
                return
        
        try:
            # Load user's pet data
            pet = await user_data_manager.get_pet_data(str(interaction.user.id))
            if not pet:
                await interaction.response.send_message("❌ You don't have a pet! Use `/hatch` to get one.", ephemeral=True)
                return
                
            # Add user to participants
            self.battle_view.participants.append((interaction.user, pet))
            
            # Update the embed
            embed = self.battle_view.build_join_embed()
            await interaction.message.edit(embed=embed)
            
            await interaction.response.send_message("✅ Joined the battle!", ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error joining battle: {e}")
            await interaction.response.send_message("❌ Error joining battle. Please try again.", ephemeral=True)
    
    @discord.ui.button(label="Leave Battle", style=discord.ButtonStyle.red, emoji="🚪")
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle user leaving the battle"""
        # Find and remove user
        for i, (user, _) in enumerate(self.battle_view.participants):
            if user.id == interaction.user.id:
                self.battle_view.participants.pop(i)
                
                # Update the embed
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
        
        # Disable buttons and start battle
        await interaction.response.defer()
        await interaction.message.edit(view=None)
        
        # Start the actual battle
        self.battle_view.battle_started = True
        
        # Update main message without buttons - actions will be sent via DM
        embed = self.battle_view.build_battle_embed("Battle started! Good luck!")
        await interaction.message.edit(embed=embed)
        
        # Start action collection via DM for all players
        await self.battle_view.start_action_collection()

class EnergonChallengeJoinView(discord.ui.View):
    """Join view for energon challenges with proper participant management"""
    
    def __init__(self, ctx, energon_bet: int):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.energon_bet = energon_bet
        self.participants = [(ctx.author, None)]  # Store (user, pet) tuples
        self.message = None
        self.max_participants = 4
        
    def build_join_embed(self) -> discord.Embed:
        """Build embed for energon challenge joining"""
        embed = discord.Embed(
            title=f"💎 Energon Challenge Setup",
            description=f"{self.ctx.author.display_name} started an energon challenge with **{self.energon_bet}** energon bet!",
            color=0x0099ff
        )
        
        participants_list = []
        for user, pet in self.participants:
            if pet:
                participants_list.append(f"{user.display_name} - {pet['name']} (Level {pet.get('level', 1)})")
            else:
                participants_list.append(f"{user.display_name} - Loading...")
        
        embed.add_field(
            name="🐾 Participants", 
            value="\n".join(participants_list) or "No participants yet", 
            inline=False
        )
        
        embed.add_field(
            name="💰 Prize Pool", 
            value=f"**{self.energon_bet * len(self.participants)}** energon", 
            inline=True
        )
        
        embed.set_footer(
            text=f"Click 'Join Challenge' to participate! (Max {self.max_participants} players)"
        )
        return embed
        
    async def update_participants_list(self):
        """Update the participants list with loaded pet data"""
        updated_participants = []
        for user, _ in self.participants:
            pet = await user_data_manager.get_pet_data(str(user.id))
            updated_participants.append((user, pet))
        self.participants = updated_participants
        
        if self.message:
            embed = self.build_join_embed()
            await self.message.edit(embed=embed)
    
    @discord.ui.button(label="Join Challenge", style=discord.ButtonStyle.green, emoji="⚔️")
    async def join_challenge(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle player joining the energon challenge"""
        try:
            # Check if user is already participating
            if any(user.id == interaction.user.id for user, _ in self.participants):
                await interaction.response.send_message("❌ You're already in this challenge!", ephemeral=True)
                return
                
            # Check if challenge is full
            if len(self.participants) >= self.max_participants:
                await interaction.response.send_message("❌ This challenge is full!", ephemeral=True)
                return
                
            # Check if user has a pet
            pet = await user_data_manager.get_pet_data(str(interaction.user.id))
            if not pet:
                await interaction.response.send_message("❌ You need a pet to join the challenge!", ephemeral=True)
                return
                
            # Add participant
            self.participants.append((interaction.user, pet))
            
            # Update embed
            embed = self.build_join_embed()
            await interaction.response.edit_message(embed=embed, view=self)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error joining challenge: {str(e)}", ephemeral=True)
    
    @discord.ui.button(label="Start Challenge", style=discord.ButtonStyle.blurple, emoji="🚀", row=1)
    async def start_challenge(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Start the energon challenge (only creator can start)"""
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Only the challenge creator can start the battle!", ephemeral=True)
            return
            
        if len(self.participants) < 2:
            await interaction.response.send_message("❌ Need at least 2 participants to start!", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        try:
            # Create the actual battle
            battle = await battle_system.create_battle(
                self.ctx, 
                "energon_challenge", 
                participants=self.participants,
                energon_bet=self.energon_bet
            )
            
            # Mark battle as started
            battle.battle_started = True
            
            # Update main message without buttons - actions will be sent via DM
            embed = battle.build_battle_embed("Energon Challenge started! Winner takes all!")
            await self.message.edit(embed=embed)
            
            # Start action collection via DM for all players
            await battle.start_action_collection()
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error starting challenge: {str(e)}", ephemeral=True)


class BattleInfoView(discord.ui.View):
    """Information view for battle mechanics and rules"""
    
    def __init__(self, ctx):
        super().__init__(timeout=600)
        self.ctx = ctx
        
    def get_battle_info_embed(self):
        """Create comprehensive battle information embed"""
        embed = discord.Embed(
            title="⚔️ Pet Battle Guide",
            description="Complete guide to pet battles, rolls, enemies, and loot!",
            color=0x0099ff
        )
        
        embed.add_field(
            name="🎯 How Battles Work",
            value="**Battle Types:**\n• **Solo** - You vs monsters\n• **Group** - Up to 4 players vs bosses\n• **PvP** - Challenge other players\n\n**Combat Flow:**\n1️⃣ Choose battle type and opponent\n2️⃣ Pick Attack, Defend, or Charge\n3️⃣ Roll 1d20 for damage multiplier\n4️⃣ Apply damage based on roll and action\n5️⃣ Continue until someone wins!",
            inline=False
        )
        
        embed.add_field(
            name="🎲 Roll System & Damage",
            value="**d20 Roll Multipliers:**\n• **1-4**: Reduced damage (0.2x to 0.8x)\n• **5-11**: Normal damage (1x)\n• **12-15**: Good damage (2x-5x)\n• **16-19**: Great damage (6x-9x)\n• **20**: Critical damage (10x)\n\n**Damage Formula:**\n`Damage = Pet Attack × Charge × Roll Multiplier`\n\n**Actions:**\n• **Attack**: Roll d20 for multiplier\n• **Defend**: 50% damage reduction\n• **Charge**: 2x multiplier stack (1.5x damage taken)",
            inline=False
        )
        
        embed.add_field(
            name="👾 Enemy Types",
            value="**By Category:**\n• **Monsters** 🤖 - Standard enemies\n• **Bosses** 👹 - Powerful single enemies\n• **Titans** 👑 - Real Transformers (hardest)\n\n**Rarity Tiers:**\n• **Common** ⚪ - Basic enemies\n• **Uncommon** 🟢 - Stronger foes\n• **Rare** 🔵 - Challenging battles\n• **Epic** 🟣 - Difficult encounters\n• **Legendary** 🟠 - Powerful adversaries\n• **Mythic** 🔴 - Ultimate challenges",
            inline=False
        )
        
        embed.add_field(
            name="💎 Loot & Rewards",
            value="**Lootable Objects:**\n• **Beast Modes**: Transform into powerful animals\n• **Transformations**: Vehicle and alternate forms\n• **Weapons**: Combat equipment and upgrades\n• **Armor**: Defensive gear and protection",
            inline=False
        )
        
        embed.set_footer(text="Battle smart, train hard, and may the Allspark be with you! ✨")
        return embed
        
    @discord.ui.button(label="Close", style=discord.ButtonStyle.grey, emoji="❌")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Only the command user can close!", ephemeral=True)
            return
        await interaction.message.delete()
        
    async def on_timeout(self):
        try:
            await self.message.edit(view=None)
        except:
            pass

class UnifiedBattleView(discord.ui.View):
    """Main battle view for handling all battle types"""
    
    def __init__(self, ctx, battle_type="solo", participants=None, monster=None, 
                 selected_enemy_type=None, selected_rarity=None, energon_bet=0):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.battle_type = battle_type
        self.selected_enemy_type = selected_enemy_type
        self.selected_rarity = selected_rarity
        self.energon_bet = energon_bet
        self.message = None
        
        # Battle state
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
        
        # Group battle settings
        self.join_mode = battle_type == "group"
        self.max_participants = 4
        
        # Group defense mechanics
        self.defending_players = set()  # Track which players are defending
        self.group_defense_active = False  # Track if group defense is active
        self.group_defender = None  # Track the player providing group defense
        
        # Group PvP turn-based mechanics
        self.player_actions = {}  # Store {player_id: {'action': str, 'target': user_id}}
        self.waiting_for_actions = False  # Flag for action collection phase
        self.round_actions = {}  # Store actions for current round processing
        
        # Rewards tracking
        self.rewards = {}  # Store rewards for final display

    @classmethod
    async def create_async(cls, ctx, battle_type="solo", participants=None, 
                          selected_enemy_type=None, selected_rarity=None, 
                          target_user=None, energon_bet=0):
        """Async factory method to create battle with loaded data"""
        view = cls(ctx, battle_type, participants, None, selected_enemy_type, 
                  selected_rarity, energon_bet)
        
        # Load pets based on battle type
        if battle_type == "solo":
            pet = await user_data_manager.get_pet_data(str(ctx.author.id))
            view.participants = [(ctx.author, pet)]
            view.monster = await view.get_monster_by_type_and_rarity(selected_enemy_type, selected_rarity)
            
        elif battle_type == "group":
            if not participants:
                pet = await user_data_manager.get_pet_data(str(ctx.author.id))
                view.participants = [(ctx.author, pet)]
            else:
                loaded_participants = []
                for user, _ in participants:
                    pet = await user_data_manager.get_pet_data(str(user.id))
                    loaded_participants.append((user, pet))
                view.participants = loaded_participants
            view.monster = await view.get_monster_by_type_and_rarity(selected_enemy_type, selected_rarity)
            
        elif battle_type == "pvp":
            pet = await user_data_manager.get_pet_data(str(ctx.author.id))
            view.participants = [(ctx.author, pet)]
            
            if target_user:
                target_pet = await user_data_manager.get_pet_data(str(target_user.id))
                view.participants.append((target_user, target_pet))
            view.monster = None
            
        elif battle_type == "energon_challenge":
            if not participants:
                pet = await user_data_manager.get_pet_data(str(ctx.author.id))
                view.participants = [(ctx.author, pet)]
            else:
                # Use pre-loaded participants from EnergonChallengeJoinView
                view.participants = participants
            view.monster = None  # PvP battle between participants
            
        view.initialize_battle_data()
        return view

    async def get_monster_by_type_and_rarity(self, enemy_type: str, rarity: str) -> Dict[str, Any]:
        """Get monster data from user_data_manager"""
        try:
            monster_data = await user_data_manager.get_monsters_and_bosses()
            
            # Select appropriate collection
            collection_map = {
                "monster": monster_data.get("monsters", {}),
                "boss": monster_data.get("bosses", {}),
                "titan": monster_data.get("titans", {})
            }
            collection = collection_map.get(enemy_type, collection_map["monster"])
            
            # Get the actual entity dictionary (nested structure)
            if enemy_type == "monster":
                entities_dict = collection.get("monsters", {})
            elif enemy_type == "boss":
                entities_dict = collection.get("bosses", {})
            elif enemy_type == "titan":
                entities_dict = collection.get("titans", {})
            else:
                entities_dict = collection.get(enemy_type + "s", {})
            
            # Filter by rarity and collect matching monsters
            matching_monsters = []
            for entity_name, entity_data in entities_dict.items():
                if isinstance(entity_data, dict) and entity_data.get('rarity') == rarity:
                    matching_monsters.append(entity_data)
            
            if matching_monsters:
                monster = random.choice(matching_monsters)
                return {
                    "name": monster["name"],
                    "health": monster["health"],
                    "attack": monster["attack"],
                    "defense": monster.get("defense", 0),
                    "type": enemy_type,
                    "rarity": rarity
                }
            else:
                # Fallback monster
                base_stats = {
                    "common": {"health": 100, "attack": 8},
                    "uncommon": {"health": 150, "attack": 12},
                    "rare": {"health": 200, "attack": 16},
                    "epic": {"health": 300, "attack": 22},
                    "legendary": {"health": 400, "attack": 28},
                    "mythic": {"health": 500, "attack": 35}
                }
                
                stats = base_stats.get(rarity, base_stats["common"])
                
                return {
                    "name": f"{rarity.title()} {enemy_type.title()}",
                    "health": stats["health"],
                    "attack": stats["attack"],
                    "type": enemy_type,
                    "rarity": rarity
                }
                
        except Exception as e:
            logger.error(f"Error loading monster: {e}")
            return self._create_fallback_monster(enemy_type, rarity)

    def _create_fallback_monster(self, enemy_type: str, rarity: str) -> Dict[str, Any]:
        """Create fallback monster when data loading fails"""
        base_stats = {
            "common": {"health": 100, "attack": 8},
            "uncommon": {"health": 150, "attack": 12},
            "rare": {"health": 200, "attack": 16},
            "epic": {"health": 300, "attack": 22},
            "legendary": {"health": 400, "attack": 28},
            "mythic": {"health": 500, "attack": 35}
        }
        
        stats = base_stats.get(rarity, base_stats["common"])
        
        return {
            "name": f"{rarity.title()} {enemy_type.title()}",
            "health": stats["health"],
            "attack_min": stats["attack"],
            "attack_max": int(stats["attack"] * 1.5),
            "type": enemy_type,
            "rarity": rarity
        }

    def initialize_battle_data(self):
        """Initialize battle data for all participants"""
        for user, pet in self.participants:
            if pet:
                # Calculate total stats including equipment
                base_attack = pet.get('attack', 10)
                base_defense = pet.get('defense', 5)
                base_energy = pet.get('energy', 100)
                base_maintenance = pet.get('maintenance', 0)
                base_happiness = pet.get('happiness', 0)
                
                # Add equipment bonuses
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
        """Start action collection - send new dismissable action messages to all players"""
        self.waiting_for_actions = True
        self.player_actions.clear()
        
        # Update the main battle embed to show waiting status
        embed = self.build_battle_embed("⏳ Waiting for players to choose their actions...")
        await self.message.edit(embed=embed)
        
        # Determine action view type based on battle type
        is_pvp = self.battle_type == "pvp"
        
        # Send new dismissable action messages to all alive players
        for user_id, data in self.player_data.items():
            if data['alive'] and data['hp'] > 0:
                if is_pvp:
                    action_view = GroupPvPActionView(self, int(user_id))
                else:
                    action_view = BattleActionDMView(self, int(user_id))
                
                try:
                    # Send new message with action buttons for each round
                    await data['user'].send(
                        f"🎯 **Round {self.turn_count + 1}** - Choose your action!",
                        view=action_view
                    )
                except discord.Forbidden:
                    # Fallback to channel if DMs disabled
                    await self.ctx.channel.send(
                        f"{data['user'].mention}, Round {self.turn_count + 1} - Choose your action:",
                        view=action_view,
                        delete_after=60  # Auto-delete after 1 minute
                    )
        
        return True

    async def check_all_actions_submitted(self):
        """Check if all players have submitted actions"""
        if not self.waiting_for_actions:
            return
            
        alive_players = [uid for uid, data in self.player_data.items() if data['alive'] and data['hp'] > 0]
        
        if len(self.player_actions) == len(alive_players):
            # All actions submitted, process the round
            self.waiting_for_actions = False
            
            # Handle PvE battles (need to add monster action)
            if self.battle_type in ["solo", "group"] and self.monster:
                monster_action = self.get_monster_action()
                await self.process_combat_round(monster_action)
            else:
                # PvP battles
                await self.process_round()

    async def process_combat_round(self, monster_action: str):
        """Process a round for PvE battles"""
        action_text = f"⚔️ **Round {self.turn_count + 1} Results**\n\n"
        
        # Process player actions first
        for player_id, action_data in self.player_actions.items():
            player_data = self.player_data[str(player_id)]
            
            if action_data['action'] == "attack":
                # Player attacks monster
                player_roll = self.roll_d20()
                player_multiplier = self.calculate_attack_multiplier(player_roll)
                total_attack = player_data.get('total_attack', player_data['pet'].get('attack', 10))
                attack_power = int(total_attack * player_data['charge'] * player_multiplier)
                monster_defense = self.monster.get('defense', 5) // 2
                reduced_damage = max(1, attack_power - monster_defense)
                self.monster_hp = max(0, self.monster_hp - reduced_damage)
                action_text += f"⚔️ **{player_data['user'].display_name}** attacks! Rolled {player_roll} → {attack_power} damage, reduced by {monster_defense} defense → {reduced_damage} damage dealt\n"
                
            elif action_data['action'] == "defend":
                # Player defends
                block_roll = self.roll_d20()
                total_defense = player_data.get('total_defense', player_data['pet'].get('defense', 5))
                block_stat = int(total_defense * self.calculate_attack_multiplier(block_roll))
                self.defending_players.add(player_data['user'].id)
                action_text += f"🛡️ **{player_data['user'].display_name}** is defending! Rolled {block_roll} → Block: {block_stat}\n"
                
            elif action_data['action'] == "charge":
                # Player charges
                player_data['charge'] = min(5.0, player_data['charge'] * 2)
                player_data['charging'] = True
                action_text += f"⚡ **{player_data['user'].display_name}** is charging! Next attack multiplier: x{player_data['charge']:.1f}\n"
        
        # Process monster action if still alive
        if self.monster_hp > 0:
            monster_roll = self.roll_d20()
            monster_multiplier = self.calculate_attack_multiplier(monster_roll)
            
            if monster_action == "attack":
                monster_attack = int(self.monster.get('attack', 15) * monster_multiplier)
                
                # Individual parry system for group battles
                defending_pets = [data for uid, data in self.player_data.items() if uid in self.defending_players]
                
                if defending_pets:
                    action_text += f"💥 **{self.monster['name']}** attacks! Rolled {monster_roll} → {monster_attack} damage\n"
                    
                    # Split damage among defending pets
                    damage_per_defender = max(1, monster_attack // len(defending_pets))
                    
                    for defender_data in defending_pets:
                        block_roll = self.roll_d20()
                        total_defense = defender_data.get('total_defense', defender_data['pet'].get('defense', 5))
                        block_stat = int(total_defense * self.calculate_attack_multiplier(block_roll))
                        
                        if block_stat >= damage_per_defender:
                            # Successful parry
                            parry_damage = block_stat - damage_per_defender
                            action_text += f"🛡️ **{defender_data['user'].display_name}** parries! Block: {block_stat} ≥ Attack: {damage_per_defender}\n"
                            if parry_damage > 0:
                                self.monster_hp = max(0, self.monster_hp - parry_damage)
                                action_text += f"⚡ Parry damage: {parry_damage} dealt to {self.monster['name']}\n"
                        else:
                            # Take damage
                            damage_taken = damage_per_defender - block_stat
                            defender_data['hp'] = max(0, defender_data['hp'] - damage_taken)
                            action_text += f"💔 **{defender_data['user'].display_name}** takes {damage_taken} damage\n"
                else:
                    # No defenders - damage split among all players
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
        
        # Reset defending players
        self.defending_players.clear()
        for player_data in self.player_data.values():
            player_data['charging'] = False
        
        # Check victory conditions
        await self.check_victory_conditions()
        
        if not self.battle_over:
            # Update main message without buttons
            embed = self.build_battle_embed(action_text)
            await self.message.edit(embed=embed)
            
            # Start next action collection via DM
            await self.start_action_collection()
        else:
            # Battle ended
            final_embed = self.build_final_battle_embed(action_text)
            await self.message.edit(embed=final_embed, view=None)
            
            # Send detailed battle log
            battle_log = self.generate_battle_log(action_text)
            for i, message in enumerate(battle_log):
                await asyncio.sleep(1)
                await self.ctx.channel.send(message)

    async def process_round(self):
        """Process a single round for all battle types"""
        action_text = f"⚔️ **Round {self.turn_count + 1} Results**\n\n"
        
        # Process defend actions first (set charging flag)
        for player_id, action_data in self.player_actions.items():
            if action_data['action'] == 'defend':
                self.player_data[str(player_id)]['charging'] = True
                action_text += f"🛡️ **{self.player_data[str(player_id)]['user'].display_name}** is defending!\n"
        
        # Process charge actions
        for player_id, action_data in self.player_actions.items():
            if action_data['action'] == 'charge':
                player_data = self.player_data[str(player_id)]
                player_data['charge'] = min(5.0, player_data['charge'] * 2)
                action_text += f"⚡ **{player_data['user'].display_name}** is charging! (Charge: x{player_data['charge']:.1f})\n"
        
        # Process attack actions
        for player_id, action_data in self.player_actions.items():
            if action_data['action'] == 'attack' and action_data['target']:
                attacker_data = self.player_data[str(player_id)]
                defender_data = self.player_data[action_data['target']]
                
                # Skip if attacker is dead
                if not attacker_data['alive'] or attacker_data['hp'] <= 0:
                    continue
                
                # Roll for attack
                roll = self.roll_d20()
                multiplier = self.calculate_attack_multiplier(roll)
                total_attack = attacker_data.get('total_attack', attacker_data['pet'].get('attack', 10))
                attack_damage = int(total_attack * attacker_data['charge'] * multiplier)
                
                # Check if defender is defending (parry system)
                if defender_data['charging']:
                    # Defender is using defend action - calculate block for parry
                    block_roll = self.roll_d20()
                    total_defense = defender_data.get('total_defense', defender_data['pet'].get('defense', 5))
                    block_stat = int(total_defense * self.calculate_attack_multiplier(block_roll))
                    
                    if block_stat >= attack_damage:
                        # Successful parry - no damage taken, excess as parry damage
                        parry_damage = block_stat - attack_damage
                        attacker_data['hp'] = max(0, attacker_data['hp'] - parry_damage)
                        action_text += f"⚔️ **{attacker_data['user'].display_name}** attacks **{defender_data['user'].display_name}**! Rolled {roll} → {attack_damage} damage\n"
                        action_text += f"🛡️ **{defender_data['user'].display_name}** parries! Block: {block_stat} ≥ Attack: {attack_damage}\n"
                        if parry_damage > 0:
                            action_text += f"⚡ Parry damage: {parry_damage} dealt to {attacker_data['user'].display_name}\n"
                    else:
                        # Failed parry - take remaining damage
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
            # Update main message without buttons
            embed = self.build_battle_embed(action_text)
            await self.message.edit(embed=embed)
            
            # Start next action collection via DM for all players
            await self.start_action_collection()
        else:
            # Battle ended
            final_embed = self.build_final_battle_embed(action_text)
            await self.message.edit(embed=final_embed, view=None)
            
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
        if self.battle_type == "energon_challenge":
            title = f"💎 Energon Challenge (Bet: {self.energon_bet})"
        
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
        
        if self.battle_type == "group_pvp" and len(self.participants) > 2 and self.waiting_for_actions:
            alive_players = [data for data in self.player_data.values() if data['alive'] and data['hp'] > 0]
            embed.add_field(
                name="⏳ Waiting for Actions",
                value=f"{len(self.player_actions)}/{len(alive_players)} players have chosen their actions",
                inline=False
            )
        
        alive_count = sum(1 for data in self.player_data.values() if data['alive'])
        embed.set_footer(text=f"Turn {self.turn_count} | {alive_count} active fighters")
        
        return embed

    def generate_battle_log(self, action_text: str = "") -> list[str]:
        """Generate detailed battle log messages"""
        messages = []
        
        # Determine victory/defeat
        if self.monster:
            if self.monster_hp <= 0:
                title = "🎉 VICTORY!"
                description = f"You defeated **{self.monster['name']}**!"
            else:
                title = "💀 DEFEAT"
                description = f"You were defeated by **{self.monster['name']}**!"
        elif self.battle_type == "pvp":
            alive_players = [data for data in self.player_data.values() if data['alive'] and data['hp'] > 0]
            if len(alive_players) == 1:
                winner = alive_players[0]
                title = "🏆 PvP VICTORY!"
                description = f"**{winner['user'].display_name}** is the winner!"
            else:
                title = "🤝 DRAW"
                description = "The battle ended in a draw!"
        else:
            title = "⚔️ BATTLE ENDED"
            description = "The battle has concluded"
        
        messages.append(f"**{title}**\n{description}")
        
        # Battle summary
        battle_summary = f"📊 **Battle Summary**\n"
        battle_summary += f"Type: {self.battle_type.title()}\n"
        battle_summary += f"Turns: {self.turn_count}\n"
        battle_summary += f"Participants: {len(self.player_data)}"
        if self.energon_bet > 0:
            battle_summary += f"\nEnergon Bet: {self.energon_bet}"
        messages.append(battle_summary)
        
        # Final participant states
        participant_lines = []
        for user_id, data in self.player_data.items():
            user = data['user']
            pet = data['pet']
            status = "💀 DEFEATED" if not data['alive'] or data['hp'] <= 0 else "🟢 SURVIVED"
            damage_taken = data['max_hp'] - data['hp']
            participant_lines.append(
                f"**{user.display_name}** ({pet['name']}) - "
                f"{data['hp']}/{data['max_hp']} HP "
                f"({status}, {damage_taken} damage taken)"
            )
        
        if participant_lines:
            participant_msg = "🐾 **Final Participant States**\n" + "\n".join(participant_lines)
            messages.append(participant_msg)
        
        # Monster final state if exists
        if self.monster:
            monster_status = "💀 DEFEATED" if self.monster_hp <= 0 else "🟢 ALIVE"
            damage_taken = self.max_monster_hp - self.monster_hp
            monster_msg = (
                f"🤖 **Monster: {self.monster['name']}**\n"
                f"{self.monster_hp}/{self.max_monster_hp} HP "
                f"({monster_status}, {damage_taken} damage taken)"
            )
            messages.append(monster_msg)
        
        # Rewards
        if self.rewards:
            reward_lines = []
            if self.rewards['type'] == 'victory' and self.rewards['survivors']:
                for survivor in self.rewards['survivors']:
                    reward_lines.append(
                        f"🏆 {survivor['user'].display_name} ({survivor['pet_name']}): "
                        f"+{survivor['reward']} energon"
                    )
            elif self.rewards['type'] == 'pvp_victory' and 'winner' in self.rewards:
                winner = self.rewards['winner']
                reward_lines.append(
                    f"🏆 {winner['user'].display_name} ({winner['pet_name']}): "
                    f"+{winner['reward']} energon, +{winner['exp_reward']} experience"
                )
            
            if reward_lines:
                messages.append("💰 **Rewards**\n" + "\n".join(reward_lines))
        
        # Last action
        if action_text:
            messages.append(f"⚡ **Final Action**\n{action_text}")
        
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
        elif self.battle_type == "pvp":
            alive_players = [data for data in self.player_data.values() if data['alive'] and data['hp'] > 0]
            if len(alive_players) == 1:
                winner = alive_players[0]
                title = "🏆 PvP VICTORY!"
                description = f"**{winner['user'].display_name}** is the winner!"
            else:
                title = "🤝 DRAW"
                description = "The battle ended in a draw!"
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
            
        # Check PvP victory conditions
        elif self.battle_type == "pvp":
            alive_players = [data for data in self.player_data.values() if data['alive'] and data['hp'] > 0]
            if len(alive_players) == 1:
                await self.handle_pvp_victory(alive_players[0])
                self.battle_over = True
            elif len(alive_players) == 0:
                await self.handle_draw()
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
                                        item_to_add = {
                                            "id": looted_equipment.get("id"),
                                            "name": looted_equipment.get("name"),
                                            "equipment_type": looted_equipment.get("equipment_type"),
                                            "rarity": looted_equipment.get("rarity"),
                                            "attack": looted_equipment.get("attack", 0),
                                            "defense": looted_equipment.get("defense", 0),
                                            "energy": looted_equipment.get("energy", 0),
                                            "maintenance": looted_equipment.get("maintenance", 0),
                                            "happiness": looted_equipment.get("happiness", 0)
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

    async def handle_pvp_victory(self, winner_data: Dict[str, Any]):
        """Handle PvP victory"""
        try:
            # Update all participants' health based on battle outcome
            for user_id, data in self.player_data.items():
                pet = data['pet']
                max_hp = pet.get('energy', 100) + pet.get('maintenance', 0) + pet.get('happiness', 0)
                damage_taken = max_hp - data['hp']
                
                # Distribute health loss equally among Energy, Maintenance, and Happiness
                health_loss_per_stat = damage_taken // 3
                remaining_loss = damage_taken % 3
                
                # Apply health loss
                pet['energy'] = max(0, pet['energy'] - health_loss_per_stat - (1 if remaining_loss > 0 else 0))
                pet['maintenance'] = max(0, pet['maintenance'] - health_loss_per_stat - (1 if remaining_loss > 1 else 0))
                pet['happiness'] = max(0, pet['happiness'] - health_loss_per_stat)
                
                # Award winner
                if user_id == str(winner_data['user'].id):
                    pet['battles_won'] = pet.get('battles_won', 0) + 1
                    pet['experience'] = pet.get('experience', 0) + 50
                    
                    user_data = await user_data_manager.get_user_data(str(user_id), data['user'].display_name)
                    current_energon = user_data['energon'].get('energon', 0)
                    new_total = current_energon + 25
                    user_data['energon']['energon'] = new_total
                    
                    # Check for energon rush win condition
                    WIN_CONDITION = 10000  # Energon rush win threshold
                    
                    # Get energon game state directly from user_data_manager
                    game_state = await user_data_manager.get_energon_data(str(user_id))
                    
                    try:
                        if game_state.get("in_energon_rush", False):
                            # Check if this gain puts them over the win threshold
                            if current_energon < WIN_CONDITION and new_total >= WIN_CONDITION:
                                # Mark game as ended and announce winner
                                game_state['in_energon_rush'] = False
                                await user_data_manager.save_energon_data(str(user_id), game_state)
                                # Add win message to PvP results
                                self.rewards['winner']['win_message'] = f"\n🎉 **ENERGON RUSH CHAMPION!** With {new_total} total energon, you've won the energon rush game!"
                    except Exception as e:
                        logger.error(f"Error checking energon rush win: {e}")
                    
                    await user_data_manager.save_user_data(str(user_id), data['user'].display_name, user_data)
                else:
                    pet['battles_lost'] = pet.get('battles_lost', 0) + 1
                
                await user_data_manager.save_pet_data(str(user_id), data['user'].display_name, pet)
            
            # Store rewards for final display
            self.rewards = {
                'type': 'pvp_victory',
                'winner': {
                    'user': winner_data['user'],
                    'pet_name': winner_data['pet']['name'],
                    'reward': 25,
                    'exp_reward': 50
                }
            }
            
            logger.info(f"PvP victory: {winner_data['user'].display_name} won")
            
        except Exception as e:
            logger.error(f"Error handling PvP victory: {e}")

    async def handle_draw(self):
        """Handle draw condition"""
        try:
            # Update all participants' health based on battle outcome
            for user_id, data in self.player_data.items():
                pet = data['pet']
                max_hp = pet.get('energy', 100) + pet.get('maintenance', 0) + pet.get('happiness', 0)
                damage_taken = max_hp - data['hp']
                
                # Distribute health loss equally among Energy, Maintenance, and Happiness
                health_loss_per_stat = damage_taken // 3
                remaining_loss = damage_taken % 3
                
                # Apply health loss
                pet['energy'] = max(0, pet['energy'] - health_loss_per_stat - (1 if remaining_loss > 0 else 0))
                pet['maintenance'] = max(0, pet['maintenance'] - health_loss_per_stat - (1 if remaining_loss > 1 else 0))
                pet['happiness'] = max(0, pet['happiness'] - health_loss_per_stat)
                
                await user_data_manager.save_pet_data(str(user_id), data['user'].display_name, pet)
                
            logger.info("Battle ended in draw")
            
        except Exception as e:
            logger.error(f"Error handling draw: {e}")

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

class GroupPvPActionView(discord.ui.View):
    """Action selection view for group PvP battles - dismissable"""
    
    def __init__(self, battle_view: UnifiedBattleView, player_id: int):
        super().__init__(timeout=600)
        self.battle_view = battle_view
        self.player_id = player_id
        self.selected_action = None
        self.selected_target = None

    @discord.ui.button(label="Attack", style=discord.ButtonStyle.red, emoji="⚔️", row=0)
    async def attack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("❌ This isn't your action selection!", ephemeral=True)
            return
            
        # Show target selection for attack
        target_view = TargetSelectionView(self.battle_view, self.player_id, "attack")
        await interaction.response.send_message("Select your target:", view=target_view, ephemeral=True)

    @discord.ui.button(label="Defend", style=discord.ButtonStyle.blurple, emoji="🛡️", row=0)
    async def defend_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("❌ This isn't your action selection!", ephemeral=True)
            return
            
        self.selected_action = "defend"
        await self.submit_action(interaction)

    @discord.ui.button(label="Charge", style=discord.ButtonStyle.green, emoji="⚡", row=0)
    async def charge_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("❌ This isn't your action selection!", ephemeral=True)
            return
            
        self.selected_action = "charge"
        await self.submit_action(interaction)

    async def submit_action(self, interaction: discord.Interaction):
        """Submit the chosen action and dismiss the message"""
        self.battle_view.player_actions[self.player_id] = {
            'action': self.selected_action,
            'target': self.selected_target
        }
        
        # Delete the message instead of just disabling buttons
        await interaction.response.defer()
        try:
            await interaction.message.delete()
        except:
            # Fallback to editing if deletion fails
            await interaction.message.edit(
                content=f"✅ Action chosen: **{self.selected_action.title()}**",
                view=None,
                delete_after=3
            )
        
        # Check if all players have chosen actions
        await self.battle_view.check_all_actions_submitted()


class TargetSelectionView(discord.ui.View):
    """Target selection for attacks in group PvP using dropdown"""
    
    def __init__(self, battle_view: UnifiedBattleView, attacker_id: int, action: str):
        super().__init__(timeout=600)
        self.battle_view = battle_view
        self.attacker_id = attacker_id
        self.action = action
        
        # Create dropdown with valid targets
        target_options = []
        for user_id, data in self.battle_view.player_data.items():
            if user_id != str(attacker_id) and data['alive'] and data['hp'] > 0:
                target_options.append(
                    discord.SelectOption(
                        label=data['user'].display_name,
                        value=user_id,
                        description=f"{data['hp']}/{data['max_hp']} HP",
                        emoji="🎯"
                    )
                )
        
        # Create the dropdown
        self.target_select = discord.ui.Select(
            placeholder="Select a target to attack...",
            options=target_options,
            min_values=1,
            max_values=1
        )
        self.target_select.callback = self.target_selected
        self.add_item(self.target_select)

    async def target_selected(self, interaction: discord.Interaction):
        """Handle target selection from dropdown"""
        if interaction.user.id != self.attacker_id:
            await interaction.response.send_message("❌ Not your selection!", ephemeral=True)
            return
            
        target_id = self.target_select.values[0]
        
        # Submit attack with target
        self.battle_view.player_actions[self.attacker_id] = {
            'action': self.action,
            'target': target_id
        }
        
        target_name = self.battle_view.player_data[target_id]['user'].display_name
        await interaction.response.edit_message(
            content=f"✅ Target selected: **{target_name}**",
            view=None
        )
        
        # Check if all players have chosen actions
        await self.battle_view.check_all_actions_submitted()

class BattleActionDMView(discord.ui.View):
    """Action view for PvE battles via DM - dismissable"""
    
    def __init__(self, battle_view: UnifiedBattleView, player_id: int):
        super().__init__(timeout=600)
        self.battle_view = battle_view
        self.player_id = player_id

    @discord.ui.button(label="Attack", style=discord.ButtonStyle.red, emoji="⚔️")
    async def attack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.submit_action(interaction, "attack")

    @discord.ui.button(label="Defend", style=discord.ButtonStyle.blurple, emoji="🛡️")
    async def defend_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.submit_action(interaction, "defend")

    @discord.ui.button(label="Charge", style=discord.ButtonStyle.green, emoji="⚡")
    async def charge_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.submit_action(interaction, "charge")

    async def submit_action(self, interaction: discord.Interaction, action: str):
        """Submit action to battle system and dismiss message"""
        if str(self.player_id) not in self.battle_view.player_data:
            await interaction.response.send_message("❌ You're not in this battle!", ephemeral=True)
            return
            
        player_data = self.battle_view.player_data[str(self.player_id)]
        if not player_data['alive'] or player_data['hp'] <= 0:
            await interaction.response.send_message("❌ You've been defeated!", ephemeral=True)
            return
            
        # Store the action
        self.battle_view.player_actions[self.player_id] = {
            'action': action,
            'target': None  # PvE doesn't need targeting
        }
        
        # Delete the message instead of just disabling buttons
        await interaction.response.defer()
        try:
            await interaction.message.delete()
        except:
            # Fallback to editing if deletion fails
            await interaction.message.edit(
                content=f"✅ Action chosen: **{action.title()}**",
                view=None,
                delete_after=3
            )
        
        # Check if all players have chosen actions
        await self.battle_view.check_all_actions_submitted()

class BattleSystem:
    """Battle system class for managing battles"""
    
    def __init__(self):
        self.active_battles = {}
        
    async def create_battle(self, ctx, battle_type: str, **kwargs) -> UnifiedBattleView:
        """Create a new battle"""
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
    'BattleInfoView',
    'UnifiedBattleView',
    'EnergonChallengeJoinView',
    'BattleSystem',
    'battle_system',
    'MONSTER_EMOJIS',
    'RARITY_EMOJIS'
]