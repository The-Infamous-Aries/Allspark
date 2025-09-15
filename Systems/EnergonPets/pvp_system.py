import discord
import asyncio
import random
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Import user_data_manager for pet data
from ..user_data_manager import user_data_manager

class PvPJoinView(discord.ui.View):
    """Standalone PvP join view for both PvP and Group PvP battles"""
    
    def __init__(self, ctx, challenger, battle_type="pvp"):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.challenger = challenger
        self.battle_type = battle_type
        self.participants = []
        self.message = None
        
    def build_join_embed(self) -> discord.Embed:
        """Build enhanced PvP join embed"""
        title = "⚔️ PvP Challenge" if self.battle_type == "pvp" else "👥 Group PvP Battle"
        description = f"{self.challenger.display_name} is challenging you to battle!"
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=0xff0000 if self.battle_type == "pvp" else 0x0099ff
        )
        
        # Add challenger info
        embed.add_field(
            name="🎯 Challenger",
            value=f"**{self.challenger.display_name}**",
            inline=False
        )
        
        # Add participants
        participants_text = []
        for i, (user, pet) in enumerate(self.participants, 1):
            if pet:
                participants_text.append(
                    f"{i}. **{user.display_name}** - {pet['name']} (Level {pet.get('level', 1)})")
            else:
                participants_text.append(f"{i}. **{user.display_name}** - No pet")
        
        if not participants_text:
            participants_text = ["🎯 Waiting for players..."]
        
        max_players = 2 if self.battle_type == "pvp" else 4
        embed.add_field(
            name=f"🐾 Participants ({len(self.participants)}/{max_players})",
            value="\n".join(participants_text),
            inline=False
        )
        
        # Add battle rules
        rules_text = []
        if self.battle_type == "pvp":
            rules_text.extend([
                "• **1v1 Duel** - Classic PvP battle",
                "• **Turn-based combat** - Choose actions via DM",
                "• **Last pet standing wins** - 25 Energon reward"
            ])
        else:
            rules_text.extend([
                "• **Free-for-all** - Up to 4 players",
                "• **Strategic combat** - Choose targets carefully",
                "• **Winner takes all** - 50 Energon reward"
            ])
        
        embed.add_field(
            name="📋 Battle Rules",
            value="\n".join(rules_text),
            inline=False
        )
        
        embed.set_footer(text="Click buttons below to join or start the battle!")
        return embed

    @discord.ui.button(label="Join Battle", style=discord.ButtonStyle.green, emoji="⚔️")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Join the PvP battle"""
        if interaction.user in [user for user, _ in self.participants]:
            await interaction.response.send_message("❌ You're already in this battle!", ephemeral=True)
            return
            
        if len(self.participants) >= (2 if self.battle_type == "pvp" else 4):
            await interaction.response.send_message("❌ Battle is full!", ephemeral=True)
            return
            
        # Check if user has a pet
        pet = await user_data_manager.get_pet_data(str(interaction.user.id))
        if not pet:
            await interaction.response.send_message("❌ You need a pet to join! Use `/hatch` to get one.", ephemeral=True)
            return
            
        self.participants.append((interaction.user, pet))
        embed = self.build_join_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Leave Battle", style=discord.ButtonStyle.red, emoji="❌")
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Leave the PvP battle"""
        user_found = False
        for i, (user, _) in enumerate(self.participants):
            if user.id == interaction.user.id:
                self.participants.pop(i)
                user_found = True
                break
                
        if not user_found:
            await interaction.response.send_message("❌ You're not in this battle!", ephemeral=True)
            return
            
        embed = self.build_join_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Start Battle", style=discord.ButtonStyle.blurple, emoji="🚀", row=1)
    async def start_battle(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Start the PvP battle (only challenger can start)"""
        if interaction.user.id != self.challenger.id:
            await interaction.response.send_message("❌ Only the challenger can start the battle!", ephemeral=True)
            return
            
        min_players = 2 if self.battle_type == "pvp" else 2
        if len(self.participants) < min_players:
            await interaction.response.send_message(f"❌ Need at least {min_players} participants to start!", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        try:
            # Create standalone PvP battle
            battle = StandalonePvPBattle(self.ctx, self.battle_type, self.participants)
            await battle.start_battle()
            
            if self.message:
                await self.message.edit(view=None)
                
        except Exception as e:
            logger.error(f"Error starting PvP battle: {e}")
            await interaction.response.send_message(f"❌ Error starting battle: {str(e)}", ephemeral=True)

class StandalonePvPBattle:
    """Complete standalone PvP battle system that doesn't rely on battle_system.py"""
    
    def __init__(self, ctx, battle_type="pvp", participants=None):
        self.ctx = ctx
        self.battle_type = battle_type
        self.participants = participants or []
        self.message = None
        self.player_data = {}
        self.current_turn_index = 0
        self.turn_count = 0
        self.battle_started = False
        self.battle_over = False
        self.battle_log = []
        self.player_actions = {}
        self.waiting_for_actions = False
        self.round_actions = {}
        
    async def start_battle(self):
        """Initialize and start the PvP battle"""
        try:
            # Initialize player data
            await self.initialize_player_data()
            
            # Create initial battle embed
            embed = self.build_battle_embed("PvP Battle Started! Choose your actions via DM...")
            
            # Send battle message
            self.message = await self.ctx.send(embed=embed)
            
            # Start the first round
            await self.start_action_collection()
            
        except Exception as e:
            logger.error(f"Error starting PvP battle: {e}")
            await self.ctx.send(f"❌ Error starting PvP battle: {str(e)}")
    
    async def initialize_player_data(self):
        """Initialize player data with pet stats"""
        for user, pet in self.participants:
            if pet:
                # Calculate equipment bonuses
                equipment = pet.get('equipment', {})
                equipment_stats = self.calculate_equipment_stats(equipment)
                
                base_attack = pet.get('attack', 10)
                base_defense = pet.get('defense', 5)
                base_hp = pet.get('max_hp', 100)
                
                total_attack = base_attack + equipment_stats['attack']
                total_defense = base_defense + equipment_stats['defense']
                total_hp = base_hp + equipment_stats['health']
                
                self.player_data[str(user.id)] = {
                    'user': user,
                    'pet': pet,
                    'hp': total_hp,
                    'max_hp': total_hp,
                    'attack': total_attack,
                    'defense': total_defense,
                    'charge_multiplier': 1.0,
                    'alive': True,
                    'defending': False,
                    'last_action': None
                }
    
    def calculate_equipment_stats(self, equipment: Dict[str, Any]) -> Dict[str, int]:
        """Calculate total stats from equipment"""
        total_attack = 0
        total_defense = 0
        total_health = 0
        
        for slot, item in equipment.items():
            if isinstance(item, dict):
                stat_bonus = item.get('stat_bonus', {})
                total_attack += stat_bonus.get('attack', 0)
                total_defense += stat_bonus.get('defense', 0)
                total_health += stat_bonus.get('energy', 0) + stat_bonus.get('maintenance', 0) + stat_bonus.get('happiness', 0)
        
        return {
            'attack': total_attack,
            'defense': total_defense,
            'health': total_health
        }
    
    def build_battle_embed(self, action_text: str = "") -> discord.Embed:
        """Build comprehensive battle embed"""
        title = "⚔️ PvP Battle" if self.battle_type == "pvp" else "👥 Group PvP Battle"
        
        embed = discord.Embed(
            title=title,
            description=action_text or "Battle in progress...",
            color=0xff0000 if self.battle_type == "pvp" else 0x0099ff
        )
        
        # Add player status
        status_lines = []
        for uid, data in self.player_data.items():
            user = data['user']
            pet = data['pet']
            hp_bar = self.create_hp_bar(data['hp'], data['max_hp'])
            status = "💀" if not data['alive'] else "❤️"
            
            status_lines.append(
                f"{status} **{user.display_name}** - {pet['name']}\n"
                f"   {hp_bar} {data['hp']}/{data['max_hp']} HP"
            )
        
        if status_lines:
            embed.add_field(
                name="🐾 Battle Status",
                value="\n".join(status_lines),
                inline=False
            )
        
        # Add turn information
        if not self.battle_over:
            current_player = self.get_current_player()
            if current_player:
                embed.add_field(
                    name="🎯 Current Turn",
                    value=f"Waiting for {current_player.display_name}",
                    inline=True
                )
        
        # Add battle log
        if self.battle_log:
            recent_log = "\n".join(self.battle_log[-5:])  # Last 5 entries
            embed.add_field(
                name="📊 Battle Log",
                value=recent_log,
                inline=False
            )
        
        embed.set_footer(text=f"Round {self.turn_count + 1}")
        return embed
    
    def create_hp_bar(self, current: int, max_hp: int) -> str:
        """Create visual HP bar"""
        percentage = max(0, min(100, (current / max_hp) * 100))
        filled = int(percentage // 10)
        empty = 10 - filled
        return "█" * filled + "░" * empty
    
    def get_current_player(self) -> Optional[discord.User]:
        """Get the current active player"""
        alive_players = [uid for uid, data in self.player_data.items() if data['alive']]
        if not alive_players:
            return None
        
        current_uid = alive_players[self.current_turn_index % len(alive_players)]
        return self.player_data[current_uid]['user']
    
    async def start_action_collection(self):
        """Start collecting actions from players"""
        if self.battle_over:
            return
            
        alive_players = [uid for uid, data in self.player_data.items() if data['alive']]
        if len(alive_players) <= 1:
            await self.end_battle()
            return
        
        self.player_actions.clear()
        self.waiting_for_actions = True
        
        # Send action requests to all alive players
        for uid in alive_players:
            user = self.player_data[uid]['user']
            try:
                action_view = PvPActionView(self, int(uid))
                embed = discord.Embed(
                    title="⚔️ Your Turn!",
                    description="Choose your action for this round:",
                    color=0xff0000
                )
                
                # Add player stats
                player_data = self.player_data[uid]
                embed.add_field(
                    name="Your Stats",
                    value=f"HP: {player_data['hp']}/{player_data['max_hp']}\n"
                          f"Attack: {player_data['attack']}\n"
                          f"Defense: {player_data['defense']}\n"
                          f"Charge: x{player_data['charge_multiplier']:.1f}",
                    inline=False
                )
                
                # Add available targets
                targets = [tid for tid, data in self.player_data.items() 
                          if tid != uid and data['alive']]
                if targets:
                    target_text = []
                    for tid in targets:
                        target_data = self.player_data[tid]
                        target_text.append(
                            f"• {target_data['user'].display_name} - {target_data['hp']}/{target_data['max_hp']} HP"
                        )
                    embed.add_field(name="Targets", value="\n".join(target_text), inline=False)
                
                await user.send(embed=embed, view=action_view)
                
            except Exception as e:
                logger.error(f"Error sending action request to {user.display_name}: {e}")
        
        # Update main battle embed
        if self.message:
            embed = self.build_battle_embed("Waiting for players to choose actions...")
            await self.message.edit(embed=embed)
    
    async def process_round(self):
        """Process a complete round of PvP combat"""
        if not self.player_actions:
            return
            
        battle_log_entries = []
        
        # Process all actions
        for player_id, action_data in self.player_actions.items():
            player_data = self.player_data.get(player_id)
            if not player_data or not player_data['alive']:
                continue
                
            action = action_data['action']
            target_id = action_data.get('target')
            
            if action == 'attack' and target_id and target_id in self.player_data:
                damage = await self.calculate_damage(player_id, target_id)
                
                target_data = self.player_data[target_id]
                target_data['hp'] = max(0, target_data['hp'] - damage)
                
                if target_data['hp'] <= 0:
                    target_data['alive'] = False
                
                attacker_name = player_data['user'].display_name
                target_name = target_data['user'].display_name
                
                battle_log_entries.append(
                    f"⚔️ **{attacker_name}** attacks **{target_name}** for **{damage}** damage!\n"
                    f"   {target_name} HP: {target_data['hp']}/{target_data['max_hp']}"
                )
                
            elif action == 'defend':
                player_data['defending'] = True
                battle_log_entries.append(
                    f"🛡️ **{player_data['user'].display_name}** takes a defensive stance!"
                )
                
            elif action == 'charge':
                player_data['charge_multiplier'] = min(5.0, player_data['charge_multiplier'] * 2)
                battle_log_entries.append(
                    f"⚡ **{player_data['user'].display_name}** charges up! Attack multiplier: x{player_data['charge_multiplier']:.1f}"
                )
        
        # Add battle log entries
        if battle_log_entries:
            self.battle_log.extend(battle_log_entries)
        
        # Reset defending status
        for player_data in self.player_data.values():
            player_data['defending'] = False
        
        # Check victory conditions
        alive_players = [uid for uid, data in self.player_data.items() if data['alive']]
        
        if len(alive_players) <= 1:
            await self.end_battle()
        else:
            # Next round
            self.turn_count += 1
            self.current_turn_index += 1
            await self.start_action_collection()
    
    async def calculate_damage(self, attacker_id: str, defender_id: str) -> int:
        """Calculate damage for PvP attack"""
        attacker = self.player_data[attacker_id]
        defender = self.player_data[defender_id]
        
        # Roll for attack multiplier
        roll = random.randint(1, 20)
        
        # Calculate multiplier based on roll
        if roll <= 4:
            multiplier = 0.2 + (roll - 1) * 0.2  # 0.2x to 0.8x
        elif roll <= 11:
            multiplier = 1.0
        elif roll <= 15:
            multiplier = 2.0 + (roll - 12) * 1.0  # 2x to 5x
        elif roll <= 19:
            multiplier = 6.0 + (roll - 16) * 1.0  # 6x to 9x
        else:  # roll == 20
            multiplier = 10.0  # Critical hit
        
        # Calculate attack and defense
        attack_power = int(attacker['attack'] * attacker['charge_multiplier'] * multiplier)
        defense = int(defender['defense'] * (1.5 if defender['defending'] else 1.0))
        
        # Ensure minimum damage of 1
        damage = max(1, attack_power - defense // 2)
        
        return damage
    
    async def end_battle(self):
        """End the PvP battle and distribute rewards"""
        self.battle_over = True
        self.waiting_for_actions = False
        
        # Find winner(s)
        alive_players = [uid for uid, data in self.player_data.items() if data['alive']]
        
        if len(alive_players) == 1:
            winner_id = alive_players[0]
            winner = self.player_data[winner_id]
            
            # Calculate reward
            reward = 25 if self.battle_type == "pvp" else 50
            
            # Update user energon
            try:
                await user_data_manager.add_energon(str(winner['user'].id), reward)
                
                final_text = (
                    f"🏆 **Battle Over!**\n\n"
                    f"**{winner['user'].display_name}** wins!\n"
                    f"💰 Reward: {reward} Energon"
                )
                
            except Exception as e:
                logger.error(f"Error awarding energon: {e}")
                final_text = f"🏆 **Battle Over!**\n\n**{winner['user'].display_name}** wins!"
                
        else:
            # Draw - no winner
            final_text = "🤝 **Battle Over!**\n\nIt's a draw! No winner this time."
        
        # Send final embed
        final_embed = self.build_battle_embed(final_text)
        if self.message:
            await self.message.edit(embed=final_embed, view=None)

class PvPActionView(discord.ui.View):
    """Action selection view for PvP battles"""
    
    def __init__(self, battle_instance, player_id: int):
        super().__init__(timeout=300)
        self.battle = battle_instance
        self.player_id = player_id
    
    def get_available_targets(self) -> List[str]:
        """Get list of available targets"""
        targets = []
        for uid, data in self.battle.player_data.items():
            if uid != str(self.player_id) and data['alive'] and data['hp'] > 0:
                targets.append(uid)
        return targets
    
    @discord.ui.button(label="Attack", style=discord.ButtonStyle.red, emoji="⚔️")
    async def attack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Select attack action"""
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("❌ This isn't your battle!", ephemeral=True)
            return
            
        targets = self.get_available_targets()
        if not targets:
            await interaction.response.send_message("❌ No targets available!", ephemeral=True)
            return
            
        if len(targets) == 1:
            # Auto-select single target
            target_id = targets[0]
            await self.submit_action(interaction, "attack", target_id)
        else:
            # Show target selection
            target_view = PvPTargetSelectionView(self.battle, self.player_id, "attack")
            embed = target_view.build_target_embed()
            await interaction.response.send_message(embed=embed, view=target_view, ephemeral=True)
    
    @discord.ui.button(label="Defend", style=discord.ButtonStyle.blurple, emoji="🛡️")
    async def defend_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Select defend action"""
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("❌ This isn't your battle!", ephemeral=True)
            return
            
        await self.submit_action(interaction, "defend")
    
    @discord.ui.button(label="Charge", style=discord.ButtonStyle.green, emoji="⚡")
    async def charge_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Select charge action"""
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("❌ This isn't your battle!", ephemeral=True)
            return
            
        await self.submit_action(interaction, "charge")
    
    async def submit_action(self, interaction: discord.Interaction, action: str, target_id: str = None):
        """Submit action to battle system"""
        try:
            # Store action in battle
            self.battle.player_actions[str(self.player_id)] = {
                'action': action,
                'target': target_id
            }
            
            # Delete the DM message
            await interaction.response.defer()
            try:
                await interaction.message.delete()
            except:
                await interaction.message.edit(content="✅ Action submitted!", view=None, delete_after=3)
            
            # Check if all players have submitted actions
            alive_players = [uid for uid, data in self.battle.player_data.items() if data['alive']]
            if len(self.battle.player_actions) >= len(alive_players):
                await self.battle.process_round()
                
        except Exception as e:
            logger.error(f"Error submitting PvP action: {e}")

class PvPTargetSelectionView(discord.ui.View):
    """Target selection view for PvP battles"""
    
    def __init__(self, battle_instance, player_id: int, action: str):
        super().__init__(timeout=60)
        self.battle = battle_instance
        self.player_id = player_id
        self.action = action
        
        # Add target buttons
        self.add_target_buttons()
    
    def build_target_embed(self) -> discord.Embed:
        """Build target selection embed"""
        embed = discord.Embed(
            title="🎯 Select Target",
            description=f"Choose your target for **{self.action.title()}**",
            color=0xff0000
        )
        
        targets = []
        for uid, data in self.battle.player_data.items():
            if uid != str(self.player_id) and data['alive'] and data['hp'] > 0:
                user = data['user']
                hp_bar = self.create_simple_hp_bar(data['hp'], data['max_hp'])
                targets.append(
                    f"**{user.display_name}**\n{hp_bar} {data['hp']}/{data['max_hp']} HP"
                )
        
        if targets:
            embed.add_field(name="Available Targets", value="\n".join(targets), inline=False)
        else:
            embed.description = "❌ No targets available!"
        
        return embed
    
    def create_simple_hp_bar(self, current: int, max_hp: int) -> str:
        """Create simple HP bar for target selection"""
        percentage = max(0, min(100, (current / max_hp) * 100))
        filled = int(percentage // 10)
        empty = 10 - filled
        return "█" * filled + "░" * empty
    
    def add_target_buttons(self):
        """Add target selection buttons"""
        targets = []
        for uid, data in self.battle.player_data.items():
            if uid != str(self.player_id) and data['alive'] and data['hp'] > 0:
                user = data['user']
                button = discord.ui.Button(
                    label=f"Target {user.display_name}",
                    style=discord.ButtonStyle.red,
                    custom_id=f"target_{uid}"
                )
                
                async def target_callback(interaction: discord.Interaction, target_uid=uid):
                    await self.select_target(interaction, target_uid)
                
                button.callback = target_callback
                self.add_item(button)
                targets.append(uid)
        
        if targets:
            # Add cancel button
            cancel_button = discord.ui.Button(
                label="Cancel",
                style=discord.ButtonStyle.grey,
                emoji="❌",
                row=1
            )
            
            async def cancel_callback(interaction: discord.Interaction):
                await interaction.response.defer()
                try:
                    await interaction.message.delete()
                except:
                    await interaction.message.edit(content="❌ Target selection cancelled", view=None, delete_after=3)
            
            cancel_button.callback = cancel_callback
            self.add_item(cancel_button)
    
    async def select_target(self, interaction: discord.Interaction, target_id: str):
        """Select target and submit action"""
        try:
            # Find the action view and submit
            await interaction.response.defer()
            
            # Submit action directly to battle
            self.battle.player_actions[str(self.player_id)] = {
                'action': self.action,
                'target': target_id
            }
            
            try:
                await interaction.message.delete()
            except:
                pass
            
            # Check if all players have submitted actions
            alive_players = [uid for uid, data in self.battle.player_data.items() if data['alive']]
            if len(self.battle.player_actions) >= len(alive_players):
                await self.battle.process_round()
                
        except Exception as e:
            logger.error(f"Error selecting PvP target: {e}")

class PvPSystem:
    """Main PvP system for managing PvP battles"""
    
    def __init__(self):
        self.active_battles = {}
    
    async def create_pvp_challenge(self, ctx, target_user: discord.User = None):
        """Create a 1v1 PvP challenge"""
        challenger = ctx.author
        
        if target_user:
            # Direct challenge
            join_view = PvPJoinView(ctx, challenger, "pvp")
            join_view.participants = [(challenger, await user_data_manager.get_pet_data(str(challenger.id)))]
            
            embed = join_view.build_join_embed()
            embed.add_field(
                name="🎯 Challenged Player",
                value=f"**{target_user.display_name}**",
                inline=False
            )
            
            message = await ctx.send(embed=embed, view=join_view)
            join_view.message = message
        else:
            # Open challenge
            join_view = PvPJoinView(ctx, challenger, "pvp")
            join_view.participants = [(challenger, await user_data_manager.get_pet_data(str(challenger.id)))]
            
            embed = join_view.build_join_embed()
            message = await ctx.send(embed=embed, view=join_view)
            join_view.message = message
    
    async def create_group_pvp(self, ctx):
        """Create a group PvP battle"""
        challenger = ctx.author
        
        join_view = PvPJoinView(ctx, challenger, "group")
        join_view.participants = [(challenger, await user_data_manager.get_pet_data(str(challenger.id)))]
        
        embed = join_view.build_join_embed()
        message = await ctx.send(embed=embed, view=join_view)
        join_view.message = message

# Global PvP system instance
pvp_system = PvPSystem()