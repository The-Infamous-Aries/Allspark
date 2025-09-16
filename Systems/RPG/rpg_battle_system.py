import discord
import random
import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

# Import the unified user data manager
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from user_data_manager import user_data_manager

# Set up logging
logger = logging.getLogger('rpg_battle_system')

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

class RPGBattleInfoView(discord.ui.View):
    """Information view for RPG battle mechanics and rules"""
    
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        
    def get_battle_info_embed(self):
        """Create comprehensive RPG battle information embed"""
        embed = discord.Embed(
            title="⚔️ Transformers RPG Battle Guide",
            description="Complete guide to RPG battles, rolls, enemies, and loot!",
            color=0x0099ff
        )
        
        embed.add_field(
            name="🎯 How RPG Battles Work",
            value="**Battle Types:**\n• **Solo** - You vs enemies\n• **Group** - Up to 4 players vs bosses\n• **PvP** - Challenge other players\n\n**Combat Flow:**\n1️⃣ Choose battle type and opponent\n2️⃣ Pick Attack, Defend, or Charge\n3️⃣ Roll 1d20 for damage multiplier\n4️⃣ Apply damage based on roll and action\n5️⃣ Continue until someone wins!",
            inline=False
        )
        
        embed.add_field(
            name="🎲 Roll System & Damage",
            value="**d20 Roll Multipliers:**\n• **1-4**: Reduced damage (0.2x to 0.8x)\n• **5-11**: Normal damage (1x)\n• **12-15**: Good damage (2x-5x)\n• **16-19**: Great damage (6x-9x)\n• **20**: Critical damage (10x)\n\n**Damage Formula:**\n`Damage = Character Attack × Charge × Roll Multiplier`\n\n**Actions:**\n• **Attack**: Roll d20 for multiplier\n• **Defend**: 50% damage reduction\n• **Charge**: 2x multiplier stack (1.5x damage taken)",
            inline=False
        )
        
        embed.add_field(
            name="👾 Enemy Types",
            value="**By Category:**\n• **Monsters** 🤖 - Standard enemies\n• **Bosses** 👹 - Powerful single enemies\n• **Titans** 👑 - Legendary Transformers\n\n**Rarity Tiers:**\n• **Common** ⚪ - Basic enemies\n• **Uncommon** 🟢 - Stronger foes\n• **Rare** 🔵 - Challenging battles\n• **Epic** 🟣 - Difficult encounters\n• **Legendary** 🟠 - Powerful adversaries\n• **Mythic** 🔴 - Ultimate challenges",
            inline=False
        )
        
        embed.add_field(
            name="💎 Loot & Rewards",
            value="**Lootable Objects:**\n• **Beast Modes**: Transform into powerful animals\n• **Transformations**: Vehicle and alternate forms\n• **Weapons**: Combat equipment and upgrades\n• **Armor**: Defensive gear and protection\n• **Energon**: Currency for upgrades",
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

class RPGUnifiedBattleView(discord.ui.View):
    """Main battle view for handling all RPG battle types"""
    
    def __init__(self, ctx, battle_type="solo", participants=None, monster=None, 
                 selected_enemy_type=None, selected_rarity=None):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.battle_type = battle_type
        self.selected_enemy_type = selected_enemy_type
        self.selected_rarity = selected_rarity
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

    @classmethod
    async def create_async(cls, ctx, battle_type="solo", participants=None, 
                          selected_enemy_type=None, selected_rarity=None, 
                          target_user=None):
        """Async factory method to create RPG battle with loaded data"""
        view = cls(ctx, battle_type, participants, None, selected_enemy_type, 
                  selected_rarity)
        
        # Load characters based on battle type
        if battle_type == "solo":
            character = await user_data_manager.get_rpg_character(str(ctx.author.id))
            view.participants = [(ctx.author, character)]
            view.monster = await view.get_monster_by_type_and_rarity(selected_enemy_type, selected_rarity)
            
        elif battle_type == "group":
            if not participants:
                character = await user_data_manager.get_rpg_character(str(ctx.author.id))
                view.participants = [(ctx.author, character)]
            else:
                loaded_participants = []
                for user, _ in participants:
                    character = await user_data_manager.get_rpg_character(str(user.id))
                    loaded_participants.append((user, character))
                view.participants = loaded_participants
            view.monster = await view.get_monster_by_type_and_rarity(selected_enemy_type, selected_rarity)
            
        elif battle_type == "pvp":
            character = await user_data_manager.get_rpg_character(str(ctx.author.id))
            view.participants = [(ctx.author, character)]
            
            if target_user:
                target_character = await user_data_manager.get_rpg_character(str(target_user.id))
                view.participants.append((target_user, target_character))
            view.monster = None
            
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
            "attack": stats["attack"],
            "type": enemy_type,
            "rarity": rarity
        }

    def initialize_battle_data(self):
        """Initialize battle data for all participants"""
        for user, character in self.participants:
            if character:
                # Calculate max HP based on character stats
                max_hp = character.get('current_health', 100)
                self.player_data[user.id] = {
                    'user': user,
                    'character': character,
                    'hp': max_hp,
                    'max_hp': max_hp,
                    'charge': 1.0,
                    'charging': False,
                    'alive': True,
                    'last_action': None
                }
        
        if self.monster:
            self.monster_hp = self.monster['health']
            self.max_monster_hp = self.monster['health']

    def create_hp_bar(self, current: int, max_hp: int, bar_type: str = "default", character=None) -> str:
        """Create visual HP bar"""
        percentage = max(0, min(100, (current / max_hp) * 100))
        filled = int(percentage // 10)
        empty = 10 - filled
        
        if bar_type == "character" and character:
            faction = character.get('faction', '').lower()
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

    def build_join_embed(self) -> discord.Embed:
        """Build embed for group battle joining"""
        embed = discord.Embed(
            title=f"⚔️ {self.battle_type.title()} Battle Setup",
            description=f"{self.ctx.author.display_name} is forming a battle!",
            color=0x0099ff
        )
        
        participants_list = []
        for user, character in self.participants:
            if character:
                participants_list.append(f"{user.display_name} - {character.get('name', 'Unknown')} (Level {character.get('level', 1)})")
        
        embed.add_field(name="🤖 Participants", value="\n".join(participants_list) or "No participants yet", inline=False)
        
        if self.monster:
            type_emoji = MONSTER_EMOJIS.get(self.monster.get('type', 'monster'), '🤖')
            rarity_emoji = RARITY_EMOJIS.get(self.monster.get('rarity', 'common'), '⚪')
            embed.add_field(
                name=f"{type_emoji} {rarity_emoji} {self.monster['name']}",
                value=f"❤️ {self.monster['health']} HP",
                inline=False
            )
        
        embed.set_footer(text=f"Click 'Join Battle' to participate! (Max {self.max_participants} players)")
        return embed

    def build_battle_embed(self, action_text: str = "") -> discord.Embed:
        """Build battle embed"""
        current_player = self.get_current_player()
        if not current_player:
            return discord.Embed(title="Battle Ended", color=0x808080)
        
        title = f"⚔️ {self.battle_type.title()} Battle"
        
        embed = discord.Embed(
            title=title,
            description=f"Turn {self.turn_count + 1} - {current_player['user'].display_name}'s turn!",
            color=0x0099ff
        )
        
        # Show participants
        status_lines = []
        for user_id, data in self.player_data.items():
            user = data['user']
            character = data['character']
            hp_bar = self.create_hp_bar(data['hp'], data['max_hp'], "character", character)
            charge_info = f" ⚡x{data['charge']:.1f}" if data['charge'] > 1.0 else ""
            charging_info = " 🔋" if data['charging'] else ""
            status = "💀" if not data['alive'] else "➡️" if user_id == current_player['user'].id else "🟢"
            status_lines.append(f"{status} {user.display_name} - {character.get('name', 'Unknown')}{charge_info}{charging_info}\n{hp_bar}")
        
        if len(status_lines) <= 2:
            embed.add_field(name="🛡️ Participants", value="\n".join(status_lines), inline=False)
        else:
            mid = len(status_lines) // 2
            embed.add_field(name="🛡️ Team (1/2)", value="\n".join(status_lines[:mid]), inline=True)
            embed.add_field(name="🛡️ Team (2/2)", value="\n".join(status_lines[mid:]), inline=True)
        
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

    def roll_d20(self) -> int:
        """Roll a d20"""
        return random.randint(1, 20)

    def calculate_attack_multiplier(self, roll: int) -> float:
        """Calculate attack multiplier based on roll"""
        if 1 <= roll <= 4:
            divisor_map = {1: 5, 2: 4, 3: 3, 4: 2}
            return 1.0 / divisor_map[roll]
        elif 5 <= roll <= 11:
            return 1.0
        elif 12 <= roll <= 20:
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

    def find_pvp_target(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Find PvP target"""
        for uid, data in self.player_data.items():
            if uid != user_id and data['alive']:
                return data
        return None

    async def process_turn(self, player_action: str, user_id: int) -> str:
        """Process a single turn"""
        if self.battle_over:
            return "Battle is over!"
        
        player_data = self.player_data.get(user_id)
        if not player_data or not player_data['alive']:
            return "Invalid or defeated player!"
        
        action_text = ""
        
        if self.battle_type in ["solo", "group"] and self.monster:
            # Battle against monster
            monster_action = self.get_monster_action()
            action_text = await self.process_combat_action(player_data, monster_action, player_action)
            
        elif self.battle_type == "pvp":
            # PvP battle
            target_player = self.find_pvp_target(user_id)
            if target_player:
                action_text = await self.process_pvp_action(player_data, target_player, player_action)
        
        # Check victory conditions
        await self.check_victory_conditions()
        
        # Move to next turn
        if not self.battle_over:
            self.turn_count += 1
            self.current_turn_index += 1
        
        return action_text

    async def process_combat_action(self, player_data: Dict[str, Any], monster_action: str, player_action: str) -> str:
        """Process combat between player and monster"""
        action_text = f"**{player_data['user'].display_name}** vs **{self.monster['name']}**\n"
        
        # Player action
        player_roll = self.roll_d20()
        player_multiplier = self.calculate_attack_multiplier(player_roll)
        
        if player_action == "attack":
            # Calculate attack based on character stats
            character = player_data['character']
            base_attack = character.get('base_stats', {}).get('ATT', 10)
            attack_power = int(base_attack * player_data['charge'] * player_multiplier)
            self.monster_hp = max(0, self.monster_hp - attack_power)
            action_text += f"⚔️ Attack! Rolled {player_roll} → {attack_power} damage\n"
            
        elif player_action == "defend":
            action_text += f"🛡️ Defending! Damage reduced by 50%\n"
            
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
                
                # Apply defense if player is defending
                if player_action == "defend":
                    monster_attack = int(monster_attack * 0.5)
                    
                player_data['hp'] = max(0, player_data['hp'] - monster_attack)
                action_text += f"🤖 {self.monster['name']} attacks! Rolled {monster_roll} → {monster_attack} damage\n"
                
            elif monster_action == "defend":
                action_text += f"🛡️ {self.monster['name']} is defending!\n"
                
            elif monster_action == "charge":
                self.monster_charge_multiplier = min(5.0, self.monster_charge_multiplier * 2)
                action_text += f"⚡ {self.monster['name']} is charging! Attack power increased\n"
        
        return action_text

    async def process_pvp_action(self, attacker_data: Dict[str, Any], defender_data: Dict[str, Any], action: str) -> str:
        """Process PvP combat between players"""
        action_text = f"**{attacker_data['user'].display_name}** vs **{defender_data['user'].display_name}**\n"
        
        # Attacker action
        attacker_roll = self.roll_d20()
        attacker_multiplier = self.calculate_attack_multiplier(attacker_roll)
        
        if action == "attack":
            attacker = attacker_data['character']
            base_attack = attacker.get('base_stats', {}).get('ATT', 10)
            attack_power = int(base_attack * attacker_data['charge'] * attacker_multiplier)
            defender_data['hp'] = max(0, defender_data['hp'] - attack_power)
            action_text += f"⚔️ {attacker_data['user'].display_name} attacks! Rolled {attacker_roll} → {attack_power} damage\n"
            
        elif action == "defend":
            action_text += f"🛡️ {attacker_data['user'].display_name} is defending!\n"
            
        elif action == "charge":
            attacker_data['charge'] = min(5.0, attacker_data['charge'] * 2)
            action_text += f"⚡ {attacker_data['user'].display_name} is charging! Attack multiplier increased\n"
        
        return action_text

    async def check_victory_conditions(self):
        """Check if battle is over"""
        if self.battle_type in ["solo", "group"] and self.monster:
            # Check if monster is defeated
            if self.monster_hp <= 0:
                self.battle_over = True
                await self.handle_victory()
                return
                
            # Check if all players are defeated
            alive_players = [data for data in self.player_data.values() if data['alive'] and data['hp'] > 0]
            if not alive_players:
                self.battle_over = True
                await self.handle_defeat()
                return
                
        elif self.battle_type == "pvp":
            # Check if one player remains
            alive_players = [data for data in self.player_data.values() if data['alive'] and data['hp'] > 0]
            if len(alive_players) <= 1:
                self.battle_over = True
                await self.handle_pvp_result(alive_players)

    async def handle_victory(self):
        """Handle victory rewards"""
        try:
            # Update character health
            for user_id, data in self.player_data.items():
                if data['alive']:
                    character = data['character']
                    character['current_health'] = data['hp']
                    await user_data_manager.save_rpg_character(str(user_id), character)
            
            # Record combat results
            from Systems.RPG.rpg_system import TransformersAIDungeonMaster
            rpg_system = TransformersAIDungeonMaster()
            
            enemy_name = self.monster['name']
            enemy_type = self.monster['type']
            enemy_rarity = self.monster['rarity']
            
            for user, character in self.participants:
                if user.id in self.player_data and self.player_data[user.id]['alive']:
                    # Record victory
                    rpg_system.resolve_combat(str(user.id), enemy_name, enemy_type, True, 
                                            self.max_monster_hp - self.monster_hp, user.display_name)
                    
                    # Award experience
                    xp_reward = 50 if enemy_type == "monster" else 100 if enemy_type == "boss" else 200
                    rpg_system.gain_experience(str(user.id), xp_reward)
            
            # Create victory embed
            victory_embed = discord.Embed(
                title="🏆 Victory!",
                description=f"{self.monster['name']} has been defeated!",
                color=discord.Color.green()
            )
            
            # Add participants
            participants_text = "\n".join([f"🎖️ {user.display_name}" for user, _ in self.participants])
            victory_embed.add_field(name="Heroes", value=participants_text, inline=False)
            
            await self.message.edit(embed=victory_embed, view=None)
            
        except Exception as e:
            logger.error(f"Error handling victory: {e}")

    async def handle_defeat(self):
        """Handle defeat"""
        try:
            # Update character health
            for user_id, data in self.player_data.items():
                character = data['character']
                character['current_health'] = data['hp']
                await user_data_manager.save_rpg_character(str(user_id), character)
            
            # Record combat results
            from Systems.RPG.rpg_system import TransformersAIDungeonMaster
            rpg_system = TransformersAIDungeonMaster()
            
            enemy_name = self.monster['name']
            enemy_type = self.monster['type']
            
            for user, character in self.participants:
                if user.id in self.player_data:
                    # Record defeat
                    rpg_system.resolve_combat(str(user.id), enemy_name, enemy_type, False, 0, user.display_name)
            
            # Create defeat embed
            defeat_embed = discord.Embed(
                title="💀 Defeat",
                description=f"{self.monster['name']} has defeated the team!",
                color=discord.Color.red()
            )
            
            await self.message.edit(embed=defeat_embed, view=None)
            
        except Exception as e:
            logger.error(f"Error handling defeat: {e}")

    async def handle_pvp_result(self, alive_players):
        """Handle PvP battle result"""
        try:
            # Update character health
            for user_id, data in self.player_data.items():
                character = data['character']
                character['current_health'] = data['hp']
                await user_data_manager.save_rpg_character(str(user_id), character)
            
            if alive_players:
                winner = alive_players[0]
                winner_embed = discord.Embed(
                    title="🏆 PvP Victory!",
                    description=f"{winner['user'].display_name} has won the battle!",
                    color=discord.Color.gold()
                )
                await self.message.edit(embed=winner_embed, view=None)
            else:
                draw_embed = discord.Embed(
                    title="🤝 Draw",
                    description="Both fighters have been defeated!",
                    color=discord.Color.orange()
                )
                await self.message.edit(embed=draw_embed, view=None)
                
        except Exception as e:
            logger.error(f"Error handling PvP result: {e}")