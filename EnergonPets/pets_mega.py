import discord
import random
import asyncio
from discord.ext import commands
import logging
from typing import Dict, List, Optional, Any, Union
from Systems.user_data_manager import user_data_manager
from .PetBattles.pvp_system import PvPBattleView, BattleMode
from .PetBattles.damage_calculator import DamageCalculator

logger = logging.getLogger(__name__)

# Constants
MEGA_FIGHT_TIMEOUT = 300  # 5 minutes

class MegaFightModeView(discord.ui.View):
    """Mode selection view for MegaFights (PvE/PvP)"""
    
    def __init__(self, cog, user_team_info, ctx):
        super().__init__(timeout=MEGA_FIGHT_TIMEOUT)
        self.cog = cog
        self.user_team_info = user_team_info
        self.ctx = ctx
        self.selected_mode = None
    
    @discord.ui.button(label='PvE Battle', style=discord.ButtonStyle.primary, emoji='🤖')
    async def pve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Select PvE mode - fight against AI enemies"""
        if str(interaction.user.id) != self.user_team_info['head_id']:
            await interaction.response.send_message("❌ Only the combiner team head can select the battle mode!", ephemeral=True)
            return
        
        self.selected_mode = "PvE"
        await self.start_pve_battle(interaction)
    
    @discord.ui.button(label='PvP Battle', style=discord.ButtonStyle.danger, emoji='⚔️')
    async def pvp_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Select PvP mode - fight against other combiner teams"""
        if str(interaction.user.id) != self.user_team_info['head_id']:
            await interaction.response.send_message("❌ Only the combiner team head can select the battle mode!", ephemeral=True)
            return
        
        self.selected_mode = "PvP"
        await self.start_pvp_battle(interaction)
    
    async def start_pve_battle(self, interaction: discord.Interaction):
        """Start PvE battle using enemy selection for combiner teams"""
        try:
            # Import enemy selection view
            from .PetBattles.enemy_selection_view import EnemySelectionView
            from .PetBattles.battle_system import UnifiedBattleView
            
            # Calculate combiner stats for display
            combiner_stats = await self.cog.calculate_combiner_stats(self.user_team_info)
            
            # Create a custom enemy selection view that handles combiner battles
            class CombinerEnemySelectionView(EnemySelectionView):
                """Custom enemy selection that creates combiner battles with combined stats"""
                
                def __init__(self, ctx, battle_type="combiner", combiner_team=None, combiner_stats=None):
                    super().__init__(ctx, battle_type=battle_type)
                    self.combiner_team = combiner_team
                    self.combiner_stats = combiner_stats
                    self.combiner_battle = True
                
                async def start_battle_callback(self, interaction: discord.Interaction):
                    """Override to create combiner battle with combined stats"""
                    try:
                        # Import battle system
                        from .PetBattles.battle_system import UnifiedBattleView
                        
                        # Load monster using proper method
                        monster = await UnifiedBattleView.get_monster_by_type_and_rarity(
                            self.selected_enemy_type, 
                            self.selected_rarity
                        )
                        
                        if not monster:
                            await interaction.response.send_message("❌ Failed to load monster data. Please try again.", ephemeral=True)
                            return
                        
                        # Create a custom combiner battle view
                        class CombinerBattleView(UnifiedBattleView):
                            """Custom battle view that uses combiner stats instead of individual pet stats"""
                            
                            def __init__(self, ctx, battle_type, participants, monster, selected_enemy_type, selected_rarity, combiner_team=None, combiner_stats=None):
                                super().__init__(ctx, battle_type, participants, monster, selected_enemy_type, selected_rarity)
                                self.combiner_team = combiner_team
                                self.combiner_stats = combiner_stats
                                self.combiner_battle = True
                            
                            def initialize_battle_data(self):
                                """Override to use combiner stats instead of individual pet stats"""
                                # For combiner battles, we treat the entire team as one entity
                                if self.combiner_stats and len(self.participants) > 0:
                                    user, pet = self.participants[0]  # Get the team leader
                                    
                                    # Use combiner stats instead of individual pet stats
                                    max_hp = self.combiner_stats['max_health']
                                    total_attack = self.combiner_stats['attack']
                                    total_defense = self.combiner_stats['defense']
                                    
                                    # Create a special "combiner pet" for display
                                    combiner_pet = {
                                        'name': f"🤖 {self.combiner_team['name']}",
                                        'attack': total_attack,
                                        'defense': total_defense,
                                        'energy': max_hp,
                                        'level': self.combiner_stats.get('level', 1),
                                        'faction': 'combiner',
                                        'battles_won': pet.get('battles_won', 0),
                                        'battles_lost': pet.get('battles_lost', 0),
                                        'equipment': {}
                                    }
                                    
                                    self.player_data[user.id] = {
                                        'user': user,
                                        'pet': combiner_pet,
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
                                else:
                                    # Fallback to normal initialization
                                    super().initialize_battle_data()
                            
                            def create_hp_bar(self, current: int, max_hp: int, bar_type: str = "default", pet=None) -> str:
                                """Override to use combiner-specific HP bar styling"""
                                if pet and pet.get('faction') == 'combiner':
                                    # Use special combiner styling
                                    percentage = max(0, min(100, (current / max_hp) * 100))
                                    filled = int(percentage // 10)
                                    empty = 10 - filled
                                    filled_char, empty_char = "🟦", "⬛"  # Blue for combiners
                                    bar = filled_char * filled + empty_char * empty
                                    return f"[{bar}] {current}/{max_hp} ({percentage:.0f}%)"
                                else:
                                    return super().create_hp_bar(current, max_hp, bar_type, pet)
                            
                            async def handle_victory(self):
                                """Override to distribute rewards to all combiner team members"""
                                # First handle normal victory processing
                                await super().handle_victory()
                                
                                # Then distribute rewards to all combiner team members
                                if self.combiner_team and hasattr(self, 'rewards'):
                                    await self.distribute_combiner_rewards()
                            
                            async def apply_damage_to_combiner_pets(self, damage_amount: int):
                                """Apply damage to all pets in the combiner team when the combiner takes damage"""
                                if not self.combiner_team or 'all_members' not in self.combiner_team:
                                    return
                                
                                try:
                                    # Distribute damage evenly across all team members
                                    damage_per_pet = damage_amount // len(self.combiner_team['all_members'])
                                    remaining_damage = damage_amount % len(self.combiner_team['all_members'])
                                    
                                    for i, member_id in enumerate(self.combiner_team['all_members']):
                                        # Get pet data for this member
                                        pet_data = await self.bot.user_data_manager.get_pet_data(str(member_id))
                                        if pet_data:
                                            pet_damage = damage_per_pet + (1 if i < remaining_damage else 0)
                                            max_hp = pet_data.get('energy', 100) + pet_data.get('maintenance', 0) + pet_data.get('happiness', 0)
                                            if max_hp > 0:
                                                energy_damage = (pet_damage * pet_data.get('energy', 100)) // max_hp
                                                maintenance_damage = (pet_damage * pet_data.get('maintenance', 0)) // max_hp
                                                happiness_damage = pet_damage - energy_damage - maintenance_damage
                                                pet_data['energy'] = max(0, pet_data.get('energy', 100) - energy_damage)
                                                pet_data['maintenance'] = max(0, pet_data.get('maintenance', 0) - maintenance_damage)
                                                pet_data['happiness'] = max(0, pet_data.get('happiness', 0) - happiness_damage)
                                                await self.bot.user_data_manager.save_pet_data(str(member_id), str(member_id), pet_data)
                                                logger.info(f"Applied {pet_damage} damage to combiner pet {member_id}: Energy -{energy_damage}, Maintenance -{maintenance_damage}, Happiness -{happiness_damage}")
                                
                                except Exception as e:
                                    logger.error(f"Error applying damage to combiner pets: {e}")

                            async def process_combat_round(self, monster_action: str):
                                """Override to apply damage to combiner pets instead of player HP"""
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
                                        self.total_damage_dealt[player_id] += reduced_damage
                                        self.total_monster_damage_received += reduced_damage
                                        action_text = f"{player_data['user'].mention} attacks with a {player_data['charge']:.1f}x charge!"
                                        self.battle_log.append(action_text)
                                        
                                    elif action_data['action'] == "defend":
                                        block_roll = self.roll_d20()
                                        block_multiplier = self.calculate_attack_multiplier(block_roll)
                                        total_defense = player_data.get('total_defense', player_data['pet'].get('defense', 5))
                                        block_stat = int(total_defense * block_multiplier)
                                        if player_id not in self.defending_players:
                                            self.defending_players.append((player_id, player_id, block_stat))
                                        defend_text = f"{player_data['user'].mention} takes a defensive stance!"
                                        self.battle_log.append(defend_text)
                                        
                                    elif action_data['action'] == "charge":
                                        player_data['charge'] = min(5.0, player_data['charge'] * 2)
                                        charge_text = f"{player_data['user'].mention} charges up! (Charge: x{player_data['charge']:.1f})"
                                        self.battle_log.append(charge_text)

                                monster_roll = self.roll_d20()
                                monster_multiplier = self.calculate_attack_multiplier(monster_roll)           
                                if monster_action == "attack":
                                    monster_attack = int(self.monster.get('attack', 15) * monster_multiplier)
                                    target_defenses = {}
                                    for defender_id, target_id, block_stat in self.defending_players:
                                        if target_id not in target_defenses:
                                            target_defenses[target_id] = []
                                        target_defenses[target_id].append((defender_id, block_stat))

                                    if not target_defenses:
                                        await self.apply_damage_to_combiner_pets(monster_attack)
                                        self.total_monster_damage_dealt += monster_attack
                                        
                                        self.battle_log.append(f"The {self.monster['name']} attacks the combiner!")
                                    else:
                                        for target_id, defenders in target_defenses.items():
                                            if target_id not in self.player_data:
                                                continue
                                                
                                            target_data = self.player_data[target_id]
                                            if not target_data['alive']:
                                                continue
                                            damage_per_target = max(1, monster_attack // len(target_defenses))
                                            total_block = sum(block_stat for _, block_stat in defenders)                               
                                            if total_block >= damage_per_target:
                                                parry_damage = total_block - damage_per_target
                                                if parry_damage > 0:
                                                    self.monster_hp = max(0, self.monster_hp - parry_damage)
                                                    # Distribute parry damage credit among defenders
                                                    for defender_id, _ in defenders:
                                                        if defender_id in self.player_data:
                                                            self.total_damage_dealt[defender_id] += (parry_damage // len(defenders))
                                                    self.total_monster_damage_received += parry_damage
                                            else:
                                                # Partial block - apply remaining damage to combiner pets
                                                damage_taken = damage_per_target - total_block
                                                await self.apply_damage_to_combiner_pets(damage_taken)
                                                self.total_monster_damage_dealt += damage_taken
                                                
                                                # Add block attempt to battle log
                                                defender_names = [self.player_data[def_id]['user'].display_name for def_id, _ in defenders]
                                                self.battle_log.append(f"The {self.monster['name']} attacks! {' '.join(defender_names)} attempts to block!")
                                                
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
                            
                            async def distribute_combiner_rewards(self):
                                """Distribute battle rewards to all combiner team members"""
                                if not self.combiner_team or 'all_members' not in self.combiner_team:
                                    return
                                
                                try:
                                    # Get the base reward
                                    base_reward = self.rewards.get('total_reward', 100)
                                    
                                    # Distribute to all team members
                                    for member_id in self.combiner_team['all_members']:
                                        if str(member_id) != str(self.ctx.author.id):  # Skip the leader who already got rewards
                                            # Add experience to each member
                                            from .pet_levels import add_experience
                                            await add_experience(str(member_id), base_reward // 2, "combiner_battle")
                                            
                                            # Add energon to each member
                                            try:
                                                energon_gain = base_reward // 4
                                                await user_data_manager.add_energon(str(member_id), energon_gain, "combiner_battle_victory")
                                            except Exception as e:
                                                logger.error(f"Error distributing energon to combiner member {member_id}: {e}")
                                
                                except Exception as e:
                                    logger.error(f"Error distributing combiner rewards: {e}")
                        
                        # Create the combiner battle
                        participants = [(interaction.user, {})]  # Single participant representing the combiner team
                        battle_view = CombinerBattleView(
                            self.ctx,
                            "combiner",
                            participants,
                            monster,  # Use the loaded monster
                            self.selected_enemy_type,
                            self.selected_rarity,
                            combiner_team=self.combiner_team,
                            combiner_stats=self.combiner_stats
                        )
                        
                        # Stop the selection view
                        self.stop()
                        
                        # Send battle start message
                        embed = discord.Embed(
                            title="🤖 Combiner Battle Begins!",
                            description=f"**{self.combiner_team['name']}** (ATK {self.combiner_stats['attack']} | DEF {self.combiner_stats['defense']} | HP {self.combiner_stats['max_health']})\n\nvs\n\n**{monster['name']}** (HP {monster['health']})",
                            color=discord.Color.blue()
                        )
                        
                        await interaction.response.send_message(embed=embed, view=battle_view, ephemeral=False)
                        battle_view.message = await interaction.original_response()
                        
                        # Start the battle
                        await battle_view.start_battle()
                        
                    except Exception as e:
                        logger.error(f"Error starting combiner battle: {e}", exc_info=True)
                        await interaction.response.send_message("❌ An error occurred while starting the combiner battle.", ephemeral=True)
            
            # Create the custom enemy selection view
            view = CombinerEnemySelectionView(
                self.ctx,
                battle_type="combiner",
                combiner_team=self.user_team_info,
                combiner_stats=combiner_stats
            )
            
            # Create a custom embed showing combiner team info
            embed = discord.Embed(
                title="🤖 Combiner PvE Battle Setup",
                description=f"**Team:** {self.user_team_info['name']}\n**Members:** {len(self.user_team_info.get('all_members', []))}\n**Combined Power:** ATK {combiner_stats['attack']} | DEF {combiner_stats['defense']} | HP {combiner_stats['max_health']}",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Select Your Challenge",
                value="Choose an enemy type and rarity to battle against your combined combiner team.",
                inline=False
            )
            
            # Stop current view
            self.stop()
            
            # Send the enemy selection with combiner context
            await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
            view.message = await interaction.original_response()
            
        except ImportError:
            await interaction.response.send_message("❌ Enemy selection system is not available.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error starting PvE battle: {e}", exc_info=True)
            await interaction.response.send_message("❌ An error occurred while starting the PvE battle.", ephemeral=True)
    
    async def start_pvp_battle(self, interaction: discord.Interaction):
        """Start PvP battle by creating a lobby for combiner teams"""
        try:
            # Import PvP lobby
            from .PetBattles.pvp_lobby import PvPLobbyView
            
            # Create combiner stats
            combiner_stats = await self.cog.calculate_combiner_stats(self.user_team_info)

            class CombinerPvPLobbyView(PvPLobbyView):
                """Custom PvP lobby that enforces combiner-only restrictions"""
                
                def __init__(self, bot, creator, battle_mode, max_players, creator_combiner_team, creator_combiner_stats):
                    super().__init__(bot, creator, battle_mode, max_players)
                    self.creator_combiner_team = creator_combiner_team
                    self.creator_combiner_stats = creator_combiner_stats
                    self.combiner_teams = {creator: creator_combiner_team}  # Store combiner teams for all players
                    self.combiner_stats = {creator: creator_combiner_stats}  # Store combiner stats for all players
                
                async def join_callback(self, interaction: discord.Interaction):
                    """Override join to enforce combiner-only restrictions"""
                    # Check if player has a complete combiner team
                    combiner_team = await self.cog.find_user_combiner_team(interaction.user.id)
                    if not combiner_team:
                        await interaction.response.send_message(
                            "❌ You need a complete combiner team to join this battle! Use `/combiner` to form a team.",
                            ephemeral=True
                        )
                        return
                    
                    # Check if player is the head of their combiner team
                    if not combiner_team['is_head']:
                        await interaction.response.send_message(
                            f"❌ Only the head member (<@{combiner_team['head_id']}>) of your combiner team can join battles!",
                            ephemeral=True
                        )
                        return
                    
                    # Check player limits based on battle mode
                    if self.battle_mode == "1v1" and len(self.players) >= 2:
                        await interaction.response.send_message(
                            "❌ This 1v1 lobby is already full! Maximum 2 players allowed.",
                            ephemeral=True
                        )
                        return
                    elif self.battle_mode == "ffa" and len(self.players) >= 4:
                        await interaction.response.send_message(
                            "❌ This FFA lobby is already full! Maximum 4 players allowed.",
                            ephemeral=True
                        )
                        return
                    
                    # Calculate combiner stats for the joining player
                    pets_mega_cog = self.bot.get_cog("PetsMegaCog")
                    if pets_mega_cog:
                        combiner_stats = await pets_mega_cog.calculate_combiner_stats(combiner_team)
                        self.combiner_teams[interaction.user] = combiner_team
                        self.combiner_stats[interaction.user] = combiner_stats
                    
                    # Call parent join method
                    await super().join_callback(interaction)
                
                async def find_user_combiner_team(self, user_id):
                    """Find user's combiner team using the PetsMegaCog method"""
                    pets_mega_cog = self.bot.get_cog("PetsMegaCog")
                    if pets_mega_cog:
                        return pets_mega_cog.find_user_combiner_team(user_id)
                    return None
                
                def get_embed(self):
                    """Override embed to show combiner-specific information"""
                    embed = super().get_embed()
                    
                    # Add combiner stats for each player
                    if self.combiner_stats:
                        stats_text = ""
                        for player, stats in self.combiner_stats.items():
                            team_name = self.combiner_teams[player].get('name', 'Unknown')
                            stats_text += f"\n**{player.display_name}** ({team_name}): ATK {stats['attack']} | DEF {stats['defense']} | HP {stats['max_health']}"
                        
                        if stats_text:
                            embed.add_field(
                                name="🤖 Combiner Stats",
                                value=stats_text,
                                inline=False
                            )
                    
                    # Update description to emphasize combiner-only nature and current mode
                    mode_info = f"**Mode:** {self.battle_mode.upper()}"
                    if self.battle_mode == "1v1":
                        mode_info += " (2 players max)"
                    elif self.battle_mode == "ffa":
                        mode_info += " (2-4 players max)"
                    
                    embed.description = f"**COMBINER-ONLY BATTLE**\n{mode_info}\n\n{embed.description}"
                    
                    return embed
                
                def update_buttons(self):
                    """Update the buttons based on current lobby state"""
                    self.clear_items()
                    
                    # Join/Leave buttons
                    join_button = discord.ui.Button(style=discord.ButtonStyle.primary, label="Join", custom_id="join")
                    join_button.callback = self.join_callback
                    self.add_item(join_button)
                    
                    leave_button = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Leave", custom_id="leave")
                    leave_button.callback = self.leave_callback
                    self.add_item(leave_button)
                    
                    # Mode switch button (only for creator)
                    if len(self.players) < 2:  # Only allow mode switch when lobby isn't full
                        mode_button = discord.ui.Button(
                            style=discord.ButtonStyle.blurple, 
                            label=f"Switch to {'FFA' if self.battle_mode == '1v1' else '1v1'}", 
                            custom_id="switch_mode"
                        )
                        mode_button.callback = self.switch_battle_mode
                        self.add_item(mode_button)
                    
                    # Start button (only for creator)
                    if len(self.players) >= 2:
                        start_button = discord.ui.Button(style=discord.ButtonStyle.green, label="Start Battle", custom_id="start")
                        start_button.callback = self.start_callback
                        self.add_item(start_button)
                
                async def switch_battle_mode(self, interaction: discord.Interaction):
                    """Switch between 1v1 and FFA modes"""
                    if interaction.user != self.creator:
                        await interaction.response.send_message(
                            "❌ Only the lobby creator can change the battle mode!",
                            ephemeral=True
                        )
                        return
                    
                    # Switch between modes
                    if self.battle_mode == "1v1":
                        self.battle_mode = "ffa"
                        self.max_players = 4
                        # Clear any existing players beyond the limit
                        if len(self.players) > 4:
                            self.players = self.players[:4]
                            # Update combiner teams and stats
                            for player in list(self.combiner_teams.keys()):
                                if player not in self.players:
                                    del self.combiner_teams[player]
                                    if player in self.combiner_stats:
                                        del self.combiner_stats[player]
                    else:
                        self.battle_mode = "1v1"
                        self.max_players = 2
                        # Clear any existing players beyond the limit
                        if len(self.players) > 2:
                            self.players = self.players[:2]
                            # Update combiner teams and stats
                            for player in list(self.combiner_teams.keys()):
                                if player not in self.players:
                                    del self.combiner_teams[player]
                                    if player in self.combiner_stats:
                                        del self.combiner_stats[player]
                    
                    await interaction.response.send_message(
                        f"✅ Battle mode switched to {self.battle_mode.upper()}!",
                        ephemeral=True
                    )
                    
                    # Update the lobby display
                    self.update_buttons()
                    await self.message.edit(embed=self.get_embed(), view=self)
                
                async def start_battle(self):
                    """Override to use custom combiner PvP battle view"""
                    self.state = LobbyState.IN_PROGRESS
                    
                    try:
                        # Get the PvPCog instance
                        pvp_cog = self.bot.get_cog("PvPCog")
                        if not pvp_cog:
                            logger.error("PvPCog not found!")
                            return
                        
                        # Start the battle based on mode using custom combiner battle view
                        # Only allow 1v1 and FFA modes for combiner battles
                        if self.battle_mode == "1v1" and len(self.players) == 2:
                            await self.start_combiner_1v1_battle(self.players[0], self.players[1])
                        elif self.battle_mode == "ffa" and 2 <= len(self.players) <= 4:
                            await self.start_combiner_ffa_battle(self.players)
                        else:
                            logger.error(f"Invalid battle configuration: {self.battle_mode} with {len(self.players)} players - Combiner battles only support 1v1 and FFA (2-4 players)")
                            return
                        
                        # Clean up the lobby message
                        if self.message:
                            try:
                                await self.message.edit(view=None)
                            except:
                                pass
                        
                    except Exception as e:
                        logger.error(f"Error starting combiner battle: {e}", exc_info=True)
                
                async def start_combiner_1v1_battle(self, player1: discord.Member, player2: discord.Member):
                    """Start a 1v1 combiner battle using custom battle view"""
                    from . import CombinerPvPBattleView, BattleMode
                    
                    participants = {'a': [player1], 'b': [player2]}
                    
                    # Get combiner teams and stats
                    combiner_teams = {
                        player1: self.combiner_teams.get(player1),
                        player2: self.combiner_teams.get(player2)
                    }
                    combiner_stats = {
                        player1: self.combiner_stats.get(player1),
                        player2: self.combiner_stats.get(player2)
                    }
                    
                    battle_view = CombinerPvPBattleView(
                        self.ctx,
                        participants,
                        BattleMode.ONE_VS_ONE,
                        combiner_teams=combiner_teams,
                        combiner_stats=combiner_stats
                    )
                    
                    # Track players in active battles
                    pvp_cog = self.bot.get_cog("PvPCog")
                    if pvp_cog:
                        pvp_cog.active_battles.update({
                            str(player1.id): battle_view,
                            str(player2.id): battle_view
                        })
                    
                    # Start the battle
                    await battle_view.start_battle()
                

                
                async def start_combiner_ffa_battle(self, players: list):
                    """Start a free-for-all combiner battle using custom battle view"""
                    from . import CombinerPvPBattleView, BattleMode
                    
                    battle_view = CombinerPvPBattleView(
                        self.ctx,
                        players,
                        BattleMode.FREE_FOR_ALL,
                        combiner_teams=self.combiner_teams,
                        combiner_stats=self.combiner_stats
                    )
                    
                    # Track players in active battles
                    pvp_cog = self.bot.get_cog("PvPCog")
                    if pvp_cog:
                        for player in players:
                            pvp_cog.active_battles[str(player.id)] = battle_view
                    
                    # Start the battle
                    await battle_view.start_battle()
                
                async def handle_battle_completion(self, winner, loser, battle_log):
                    """Override to distribute rewards to all combiner team members"""
                    try:
                        # Call parent completion handler first
                        await super().handle_battle_completion(winner, loser, battle_log)
                        
                        # Distribute rewards to all combiner team members
                        await self.distribute_combiner_rewards(winner, loser)
                    except Exception as e:
                        logger.error(f"Error in combiner battle completion: {e}")
                
                async def distribute_combiner_rewards(self, winner, loser):
                    """Distribute PvP battle rewards to all combiner team members"""
                    try:
                        # Determine winner and loser teams
                        winner_team = self.combiner_teams.get(winner)
                        loser_team = self.combiner_teams.get(loser)
                        
                        if not winner_team or not loser_team:
                            return
                        
                        # Base rewards for PvP
                        winner_reward = 200
                        loser_reward = 50
                        
                        # Distribute rewards to winner team members
                        if 'all_members' in winner_team:
                            for member_id in winner_team['all_members']:
                                # Add experience
                                from .pet_levels import add_experience
                                await add_experience(str(member_id), winner_reward, "combiner_pvp_victory")
                                
                                # Add energon
                                try:
                                    await user_data_manager.add_energon(str(member_id), winner_reward // 2, "combiner_pvp_victory")
                                except Exception as e:
                                    logger.error(f"Error distributing winner energon to combiner member {member_id}: {e}")
                        
                        # Distribute consolation rewards to loser team members
                        if 'all_members' in loser_team:
                            for member_id in loser_team['all_members']:
                                # Add small experience
                                from .pet_levels import add_experience
                                await add_experience(str(member_id), loser_reward, "combiner_pvp_defeat")
                                
                                # Add small energon
                                try:
                                    await user_data_manager.add_energon(str(member_id), loser_reward // 4, "combiner_pvp_defeat")
                                except Exception as e:
                                    logger.error(f"Error distributing loser energon to combiner member {member_id}: {e}")
                    
                    except Exception as e:
                        logger.error(f"Error distributing combiner PvP rewards: {e}")
            
            # Create the custom combiner PvP lobby
            # Allow both 1v1 and FFA modes - user can choose battle type
            view = CombinerPvPLobbyView(
                self.cog.bot,
                interaction.user,
                "1v1",  # Default to 1v1 mode
                max_players=2,  # Start with 1v1, can be changed to FFA (up to 4) in the lobby
                creator_combiner_team=self.user_team_info,
                creator_combiner_stats=combiner_stats
            )
            
            # Stop current view
            self.stop()
            
            # Send lobby creation with combiner-specific information
            embed = discord.Embed(
                title="⚔️ Combiner PvP Lobby",
                description=f"**{self.user_team_info['name']}** is looking for combiner opponents!\n\nOnly players with complete combiner teams can join.\n**Battle Modes:** 1v1 or FFA (2-4 players)",
                color=discord.Color.red()
            )
            embed.add_field(
                name="Your Combiner Stats",
                value=f"**Team:** {self.user_team_info['name']}\n**Members:** {len(self.user_team_info.get('all_members', []))}\n**ATK:** {combiner_stats['attack']} | **DEF:** {combiner_stats['defense']} | **HP:** {combiner_stats['max_health']}",
                inline=False
            )
            embed.add_field(
                name="Requirements",
                value="• Must have a complete combiner team\n• Only head members can start battles\n• 1v1: Exactly 2 players\n• FFA: 2-4 players maximum",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
            view.message = await interaction.original_response()
            
        except ImportError:
            await interaction.response.send_message("❌ PvP lobby system is not available.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error starting PvP battle: {e}", exc_info=True)
            await interaction.response.send_message("❌ An error occurred while starting the PvP battle.", ephemeral=True)

class CombinerPvPBattleView(PvPBattleView):
    """Custom PvP battle view for combiner teams that applies damage to pets instead of player HP"""
    
    def __init__(self, ctx, participants: Union[List[discord.Member], Dict[str, List[discord.Member]]], 
                 battle_mode: BattleMode = BattleMode.TEAM_2V2, team_names: Optional[Dict[str, str]] = None,
                 combiner_teams: Optional[Dict[discord.Member, dict]] = None, combiner_stats: Optional[Dict[discord.Member, dict]] = None):
        """
        Initialize a combiner PvP battle view
        
        Args:
            ctx: The command context
            participants: Either a list of members (for FFA) or a dict with 'team_a' and 'team_b' keys
            battle_mode: The type of battle (1v1, 2v2, 3v3, 4v4, FFA)
            team_names: Optional dict mapping team IDs to team names
            combiner_teams: Dict mapping player to their combiner team data
            combiner_stats: Dict mapping player to their combiner stats
        """
        super().__init__(ctx, participants, battle_mode, team_names)
        self.combiner_teams = combiner_teams or {}
        self.combiner_stats = combiner_stats or {}
        self.cog = ctx.bot.get_cog("PetsMegaCog")
    
    async def apply_damage_to_target(self, attacker_id: str, target_id: str, base_damage: int, is_critical: bool = False):
        """Override damage application to apply to combiner pets instead of player HP"""
        try:
            # Get the target player object
            target_player = self.players.get(target_id)
            if not target_player:
                return
            
            target_member = target_player.get('user')
            if not target_member:
                return
            
            # Get the combiner team for the target
            combiner_team = self.combiner_teams.get(target_member)
            if not combiner_team:
                # Fallback to regular damage if no combiner team
                await super().apply_damage_to_target(attacker_id, target_id, base_damage, is_critical)
                return
            
            # Use the new DamageCalculator system instead of old damage calculation
            # Get attacker and target stats
            attacker_player = self.players.get(attacker_id)
            if not attacker_player:
                return
                
            attacker_attack = attacker_player.get('attack', 0)
            target_defense = target_player.get('defense', 0)
            attacker_charge = attacker_player.get('charge', 1.0)
            target_charge = target_player.get('charge', 1.0)
            
            # Calculate damage using the new system
            battle_result = DamageCalculator.calculate_battle_action(
                attacker_attack=attacker_attack,
                target_defense=target_defense,
                charge_multiplier=attacker_charge,
                target_charge_multiplier=target_charge,
                action_type="attack"
            )
            
            final_damage = battle_result['final_damage']
            parry_damage = battle_result['parry_damage']
            
            # Apply damage to combiner pets instead of player HP
            if final_damage > 0:
                await self.apply_damage_to_combiner_pets(combiner_team, final_damage)
            
            # Apply parry damage to attacker if any
            if parry_damage > 0:
                attacker_member = attacker_player.get('user')
                attacker_combiner_team = self.combiner_teams.get(attacker_member)
                if attacker_combiner_team:
                    await self.apply_damage_to_combiner_pets(attacker_combiner_team, parry_damage)
            
            # Log the damage with roll information
            attacker_name = attacker_player['user'].display_name
            target_name = target_player['user'].display_name
            
            self.battle_log.append(
                f"⚔️ {attacker_name} attacks {target_name}'s combiner team "
                f"(Roll: {battle_result['attack_roll']}, {battle_result['attack_result']}) "
                f"🛡️ {target_name} defends "
                f"(Roll: {battle_result['defense_roll']}, {battle_result['defense_result']})"
            )
            
            if final_damage > 0:
                self.battle_log.append(f"💥 {target_name}'s combiner team takes {final_damage} damage!")
            
            if parry_damage > 0:
                self.battle_log.append(f"🔄 {attacker_name}'s combiner team takes {parry_damage} parry damage!")
            
            # Reset charge multipliers after use
            attacker_player['charge'] = 1.0
            target_player['charge'] = 1.0
            
            # Check if combiner team is defeated (all pets dead or low health)
            if await self.is_combiner_defeated(combiner_team):
                target_player['alive'] = False
                self.battle_log.append(f"💀 {target_name}'s combiner team has been defeated!")
                
                # Check if battle is over
                await self.check_battle_end()
            
            # Check if attacker's combiner team is defeated from parry damage
            if parry_damage > 0:
                attacker_member = attacker_player.get('user')
                attacker_combiner_team = self.combiner_teams.get(attacker_member)
                if attacker_combiner_team and await self.is_combiner_defeated(attacker_combiner_team):
                    attacker_player['alive'] = False
                    self.battle_log.append(f"💀 {attacker_name}'s combiner team has been defeated by parry damage!")
                    await self.check_battle_end()
            
        except Exception as e:
            logger.error(f"Error applying combiner damage in PvP: {e}")
            # Fallback to regular damage
            await super().apply_damage_to_target(attacker_id, target_id, base_damage, is_critical)
    
    async def apply_damage_to_combiner_pets(self, combiner_team: dict, total_damage: int):
        """Apply damage to combiner pets, distributing among team members"""
        try:
            if not combiner_team or 'all_members' not in combiner_team:
                return
            
            # Get all pets from team members, keeping track of which member owns each pet
            pet_owners = []  # List of tuples: (pet, member_id)
            for member_id in combiner_team['all_members']:
                pet_data = await self.bot.user_data_manager.get_pet_data(str(member_id))
                if pet_data:
                    pet_owners.append((pet_data, member_id))
            
            if not pet_owners:
                return
            
            # Distribute damage among pets
            damage_per_pet = total_damage // len(pet_owners)
            remainder = total_damage % len(pet_owners)
            
            # Apply damage to each pet
            for i, (pet, member_id) in enumerate(pet_owners):
                pet_damage = damage_per_pet + (1 if i < remainder else 0)
                
                # Apply damage proportionally to energy, maintenance, and happiness
                energy_damage = pet_damage // 3
                maintenance_damage = pet_damage // 3
                happiness_damage = pet_damage - energy_damage - maintenance_damage
                
                # Update pet stats
                pet['energy'] = max(0, pet.get('energy', 100) - energy_damage)
                pet['maintenance'] = max(0, pet.get('maintenance', 100) - maintenance_damage)
                pet['happiness'] = max(0, pet.get('happiness', 100) - happiness_damage)
                
                # Check if pet died (any stat reached 0) and set all stats to 0
                if pet['energy'] <= 0 or pet['maintenance'] <= 0 or pet['happiness'] <= 0:
                    pet['energy'] = 0
                    pet['maintenance'] = 0
                    pet['happiness'] = 0
                    logger.info(f"Pet for member {member_id} died in mega fight - all stats set to 0")
                
                # Save pet data using user_data_manager with the correct member_id
                await self.bot.user_data_manager.save_pet_data(str(member_id), str(member_id), pet)
            
            logger.info(f"Applied {total_damage} damage to combiner team {combiner_team.get('name', 'Unknown')}, distributed among {len(pet_owners)} pets")
            
        except Exception as e:
            logger.error(f"Error applying damage to combiner pets in PvP: {e}")
    
    async def is_combiner_defeated(self, combiner_team: dict) -> bool:
        """Check if a combiner team is defeated (all pets dead or very low stats)"""
        try:
            if not combiner_team or 'all_members' not in combiner_team:
                return True
            
            # Get all pets from team members
            all_pets = []
            for member_id in combiner_team['all_members']:
                pet_data = await self.bot.user_data_manager.get_pet_data(str(member_id))
                if pet_data:
                    all_pets.append(pet_data)
            
            if not all_pets:
                return True
            
            # Check if all pets are defeated (very low energy, maintenance, or happiness)
            defeated_pets = 0
            for i, pet in enumerate(all_pets):
                energy = pet.get('energy', 100)
                maintenance = pet.get('maintenance', 100)
                happiness = pet.get('happiness', 100)
                
                # Pet is considered defeated if any stat is below 10
                if energy < 10 or maintenance < 10 or happiness < 10:
                    defeated_pets += 1
                    # Set all stats to 0 when pet is defeated
                    pet['energy'] = 0
                    pet['maintenance'] = 0
                    pet['happiness'] = 0
                    # Save the updated pet data
                    member_id = combiner_team['all_members'][i]
                    await self.bot.user_data_manager.save_pet_data(str(member_id), str(member_id), pet)
                    logger.info(f"Pet for member {member_id} defeated in mega fight - all stats set to 0")
            
            # Team is defeated if more than 75% of pets are defeated
            return defeated_pets >= len(all_pets) * 0.75
            
        except Exception as e:
            logger.error(f"Error checking if combiner is defeated in PvP: {e}")
            return True


class MegaFightView(discord.ui.View):
    def __init__(self, cog, challenger_team_info, ctx):
        super().__init__(timeout=MEGA_FIGHT_TIMEOUT)
        self.cog = cog
        self.challenger_team_info = challenger_team_info
        self.opponent_team_info = None
        self.ctx = ctx
        self.fight_started = False
        self.current_round = 1
        self.max_rounds = 3
        self.challenger_wins = 0
        self.opponent_wins = 0
        
    def get_team_display_name(self, team_info):
        """Get a display name for the team."""
        return team_info['name'] if team_info['name'] != "Unnamed Combiner" else f"Team {team_info['team_id'][:8]}"
    
    def update_embed(self, interaction_or_ctx, status="waiting", round_result=None):
        """Update the mega fight embed."""
        challenger_name = self.get_team_display_name(self.challenger_team_info)
        
        if status == "waiting":
            embed = discord.Embed(
                title="🤖⚔️ MEGA-FIGHT CHALLENGE!",
                description=f"**{challenger_name}** challenges another combiner team to a Mega-Fight!\n\n🎲 **Rules:**\n• No energon required to start\n• Head member controls the fight\n• Winners get energon + pet XP\n• Losers lose 50 energon + pet health\n• Pure 1-100 random rolls (pets don't affect odds)",
                color=discord.Color.orange()
            )
            embed.add_field(name="🗣️ Challenger Head", value=f"<@{self.challenger_team_info['head_id']}>", inline=True)
            embed.add_field(name="⏰ Status", value="Waiting for opponent team...", inline=True)
            
        elif status == "ready":
            opponent_name = self.get_team_display_name(self.opponent_team_info)
            embed = discord.Embed(
                title="🤖⚔️ MEGA-FIGHT READY!",
                description=f"**{challenger_name}** vs **{opponent_name}**\n\nBoth heads can now roll for their teams!",
                color=discord.Color.blue()
            )
            embed.add_field(name="🗣️ Challenger Head", value=f"<@{self.challenger_team_info['head_id']}>", inline=True)
            embed.add_field(name="🗣️ Opponent Head", value=f"<@{self.opponent_team_info['head_id']}>", inline=True)
            embed.add_field(name="🎯 Round", value=f"{self.current_round}/{self.max_rounds}", inline=True)
            
        elif status == "round_result":
            challenger_name = self.get_team_display_name(self.challenger_team_info)
            opponent_name = self.get_team_display_name(self.opponent_team_info)
            
            embed = discord.Embed(
                title=f"🎲 Round {self.current_round} Results",
                description=f"**{challenger_name}** vs **{opponent_name}**",
                color=discord.Color.green() if round_result else discord.Color.red()
            )
            
            if round_result:
                embed.add_field(name="🏆 Round Winner", value=round_result, inline=False)
            
            embed.add_field(name="📊 Score", value=f"{challenger_name}: {self.challenger_wins}\n{opponent_name}: {self.opponent_wins}", inline=True)
            embed.add_field(name="🎯 Round", value=f"{self.current_round}/{self.max_rounds}", inline=True)
            
        return embed
    
    @discord.ui.button(label='Join Mega-Fight', style=discord.ButtonStyle.green, emoji='🤖')
    async def join_mega_fight(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.opponent_team_info:
            await interaction.response.send_message("❌ This mega-fight already has an opponent!", ephemeral=True)
            return
            
        # Check if user has a complete combiner team
        user_team = await self.cog.find_user_combiner_team(interaction.user.id)
        if not user_team:
            await interaction.response.send_message("❌ You need to be part of a complete combiner team to join mega-fights!", ephemeral=True)
            return
            
        # Only the head can join mega-fights
        if not user_team['is_head']:
            await interaction.response.send_message(f"❌ Only the head member (<@{user_team['head_id']}>) can join mega-fights for your combiner team!", ephemeral=True)
            return
            
        # Can't fight yourself
        if user_team['team_id'] == self.challenger_team_info['team_id']:
            await interaction.response.send_message("❌ You can't fight your own team!", ephemeral=True)
            return
            
        self.opponent_team_info = user_team
        
        # Enable roll buttons and disable join button
        button.disabled = True
        self.roll_challenger.disabled = False
        self.roll_opponent.disabled = False
        
        embed = self.update_embed(interaction, "ready")
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label='Roll (Challenger)', style=discord.ButtonStyle.primary, emoji='🎲', disabled=True)
    async def roll_challenger(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.challenger_team_info['head_id']:
            await interaction.response.send_message("❌ Only the challenger team's head can roll!", ephemeral=True)
            return
            
        if not self.opponent_team_info:
            await interaction.response.send_message("❌ Waiting for an opponent team!", ephemeral=True)
            return
            
        await self.execute_round(interaction, "challenger")
    
    @discord.ui.button(label='Roll (Opponent)', style=discord.ButtonStyle.secondary, emoji='🎲', disabled=True)
    async def roll_opponent(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.opponent_team_info['head_id']:
            await interaction.response.send_message("❌ Only the opponent team's head can roll!", ephemeral=True)
            return
            
        await self.execute_round(interaction, "opponent")
    
    async def execute_round(self, interaction, roller):
        """Execute a round of the mega-fight."""
        challenger_roll = random.randint(1, 100)
        opponent_roll = random.randint(1, 100)
        
        challenger_name = self.get_team_display_name(self.challenger_team_info)
        opponent_name = self.get_team_display_name(self.opponent_team_info)
        
        round_result = f"🎲 **{challenger_name}** rolled: **{challenger_roll}**\n🎲 **{opponent_name}** rolled: **{opponent_roll}**\n\n"
        
        if challenger_roll > opponent_roll:
            self.challenger_wins += 1
            round_result += f"🏆 **{challenger_name}** wins this round!"
        elif opponent_roll > challenger_roll:
            self.opponent_wins += 1
            round_result += f"🏆 **{opponent_name}** wins this round!"
        else:
            round_result += "🤝 **TIE!** No points awarded."
        
        self.current_round += 1
        
        # Check if fight is over
        if self.current_round > self.max_rounds or self.challenger_wins >= 2 or self.opponent_wins >= 2:
            await self.complete_mega_fight(interaction, round_result)
        else:
            embed = self.update_embed(interaction, "round_result", round_result)
            await interaction.response.edit_message(embed=embed, view=self)
    
    async def complete_mega_fight(self, interaction, final_round_result):
        """Complete the mega-fight and distribute rewards/penalties."""
        challenger_name = self.get_team_display_name(self.challenger_team_info)
        opponent_name = self.get_team_display_name(self.opponent_team_info)
        
        # Determine winner
        if self.challenger_wins > self.opponent_wins:
            winning_team = self.challenger_team_info
            losing_team = self.opponent_team_info
            winner_name = challenger_name
        else:
            winning_team = self.opponent_team_info
            losing_team = self.challenger_team_info
            winner_name = opponent_name
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        # Apply rewards and penalties
        energon_reward = random.randint(100, 300)
        energon_penalty = 50
        
        reward_messages = []
        penalty_messages = []
        
        # Process winning team
        for member_id in winning_team['all_members']:
            # Update stats
            await self.cog.update_player_stats(member_id, "mega_fights_won", 1)
            await self.cog.update_player_stats(member_id, "total_energon_won", energon_reward)
            await self.cog.update_player_stats(member_id, "total_fights", 1)
            
            # Award energon using UserDataManager for proper tracking
            await self.cog.bot.user_data_manager.add_energon(str(member_id), energon_reward, "mega_fight_win")
            reward_messages.append(f"<@{member_id}> gained {energon_reward} energon")
            
            # Pet XP reward
            pet_data = await self.cog.bot.user_data_manager.get_pet_data(str(member_id))
            if pet_data:
                from .pet_levels import add_experience
                xp_gain = random.randint(25, 50)
                level_up_result = await add_experience(self.cog.bot, str(member_id), xp_gain, "mega_fight")
                reward_messages.append(f"<@{member_id}>'s pet gained {xp_gain} XP")
                
                if level_up_result and level_up_result.get('leveled_up'):
                    # Send level-up embed
                    try:
                        await interaction.followup.send(embed=level_up_result['embed'])
                    except:
                        reward_messages.append(f"<@{member_id}>'s pet leveled up!")
        
        # Process losing team
        for member_id in losing_team['all_members']:
            # Update stats
            await self.cog.update_player_stats(member_id, "mega_fights_lost", 1)
            await self.cog.update_player_stats(member_id, "total_energon_lost", energon_penalty)
            await self.cog.update_player_stats(member_id, "total_fights", 1)
            
            # Deduct energon using proper energon tracking
            await self.cog.bot.user_data_manager.subtract_energon(str(member_id), energon_penalty, "mega_fight_loss")
            penalty_messages.append(f"<@{member_id}> lost {energon_penalty} energon")
            
            # Pet health penalty - distribute across energy, maintenance, and happiness
            pet_data = await self.cog.bot.user_data_manager.get_pet_data(str(member_id))
            if pet_data:
                health_loss = random.randint(15, 30)
                
                # Distribute health loss evenly across energy, maintenance, and happiness
                loss_per_stat = health_loss // 3
                remaining_loss = health_loss % 3
                
                # Apply damage to each stat
                pet_data['energy'] = max(0, pet_data['energy'] - loss_per_stat - (1 if remaining_loss > 0 else 0))
                pet_data['maintenance'] = max(0, pet_data['maintenance'] - loss_per_stat - (1 if remaining_loss > 1 else 0))
                pet_data['happiness'] = max(0, pet_data['happiness'] - loss_per_stat)
                
                # Save the updated pet data
                await self.cog.bot.user_data_manager.save_pet_data(str(member_id), str(member_id), pet_data)
                
                penalty_messages.append(f"<@{member_id}>'s pet lost {health_loss} total stats (Energy: {loss_per_stat + (1 if remaining_loss > 0 else 0)}, Maintenance: {loss_per_stat + (1 if remaining_loss > 1 else 0)}, Happiness: {loss_per_stat})")
        
        # Data is automatically saved by UserDataManager - no manual saving needed
        
        # Create final embed
        embed = discord.Embed(
            title="🏆 MEGA-FIGHT COMPLETE!",
            description=f"{final_round_result}\n\n**🎉 WINNER: {winner_name}!**",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="📊 Final Score",
            value=f"{challenger_name}: {self.challenger_wins}\n{opponent_name}: {self.opponent_wins}",
            inline=True
        )
        
        if reward_messages:
            embed.add_field(
                name="🎁 Rewards (Winners)",
                value="\n".join(reward_messages[:10]),  # Limit to prevent embed overflow
                inline=False
            )
        
        if penalty_messages:
            embed.add_field(
                name="💸 Penalties (Losers)",
                value="\n".join(penalty_messages[:10]),  # Limit to prevent embed overflow
                inline=False
            )
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_timeout(self):
        """Handle timeout."""
        for item in self.children:
            item.disabled = True
        
        embed = discord.Embed(
            title="⏰ Mega-Fight Expired",
            description="No opponent joined in time. The mega-fight has been cancelled.",
            color=discord.Color.red()
        )
        
        try:
            await self.ctx.edit(embed=embed, view=self)
        except:
            pass

class PetsMegaCog(commands.Cog):
    """Mega-Fight functionality for combiner teams."""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def find_user_combiner_team(self, user_id):
        """Find the combiner team that a user belongs to."""
        if not hasattr(self.bot, 'user_data_manager'):
            return None
        
        # Check if user is in any combiner team
        in_combiner, message_id = await self.bot.user_data_manager.is_user_in_any_combiner(str(user_id))
        if not in_combiner or not message_id:
            return None
        
        # Get the team data from the theme system
        team_data = await self.bot.user_data_manager.get_user_theme_data_section(message_id, "combiner_teams", {})
        if not team_data:
            return None
        
        # Get the combiner name data
        combiner_name_data = await self.bot.user_data_manager.get_user_theme_data_section(message_id, "combiner_name", {})
        
        # Collect all members from team data
        all_members = []
        for part_members in team_data.values():
            all_members.extend(part_members)
        
        # Check if user is actually in this team and team is complete (4 members)
        if str(user_id) not in all_members or len(all_members) != 4:
            return None
        
        # Create team info structure
        team_info = {
            'all_members': all_members,
            'name': combiner_name_data.get('name', 'Unknown Combiner'),
            'message_id': message_id,
            'is_head': str(user_id) == str(all_members[0]) if all_members else False,  # First member is head
            'team_id': message_id
        }
        
        return team_info
    
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

    async def calculate_combiner_stats(self, team_info: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate combined stats from all 4 pets in the combiner team."""
        combined_stats = {
            'attack': 0,
            'defense': 0,
            'max_health': 0,
            'current_health': 0,
            'speed': 0,
            'level': 0,
            'experience': 0,
            'pet_names': [],
            'member_ids': [],
            'pet_data': []  # Store individual pet data for health updates
        }
        
        try:
            # Get all team members
            all_members = team_info.get('all_members', [])
            
            for member_id in all_members:
                # Get pet data for each member
                pet_data = await self.bot.user_data_manager.get_pet_data(str(member_id))
                if pet_data:
                    # Store pet data for health updates
                    combined_stats['pet_data'].append({
                        'member_id': str(member_id),
                        'data': pet_data
                    })
                    
                    # Calculate base stats
                    base_attack = pet_data.get('attack', 10)
                    base_defense = pet_data.get('defense', 5)
                    base_energy = pet_data.get('energy', 100)
                    base_maintenance = pet_data.get('maintenance', 100)
                    base_happiness = pet_data.get('happiness', 100)
                    base_max_energy = pet_data.get('max_energy', 100)
                    base_max_maintenance = pet_data.get('max_maintenance', 100)
                    base_max_happiness = pet_data.get('max_happiness', 100)
                    
                    # Calculate equipment bonuses
                    equipment_stats = self.calculate_equipment_stats(pet_data.get('equipment', {}))
                    
                    # Calculate total stats (base + equipment)
                    total_attack = base_attack + equipment_stats['attack']
                    total_defense = base_defense + equipment_stats['defense']
                    total_max_energy = base_max_energy + equipment_stats['energy']
                    total_max_maintenance = base_max_maintenance + equipment_stats['maintenance']
                    total_max_happiness = base_max_happiness + equipment_stats['happiness']
                    
                    # Sum up attack and defense stats for battle (with equipment)
                    combined_stats['attack'] += total_attack
                    combined_stats['defense'] += total_defense
                    combined_stats['speed'] += pet_data.get('speed', 10)
                    combined_stats['level'] += pet_data.get('level', 1)
                    combined_stats['experience'] += pet_data.get('experience', 0)
                    combined_stats['pet_names'].append(pet_data.get('name', f'Pet {member_id}'))
                    combined_stats['member_ids'].append(str(member_id))
                    
                    # Calculate health from energy, maintenance, and happiness (current stats for current health)
                    pet_battle_health = base_energy + base_maintenance + base_happiness
                    combined_stats['current_health'] += pet_battle_health
                    
                    # Max health uses max stats + equipment bonuses
                    pet_max_health = total_max_energy + total_max_maintenance + total_max_happiness
                    combined_stats['max_health'] += pet_max_health
            
            # Calculate average level for the combiner
            if combined_stats['pet_names']:
                combined_stats['level'] = combined_stats['level'] // len(combined_stats['pet_names'])
            
            # Set minimum values to ensure the combiner is viable
            combined_stats['attack'] = max(1, combined_stats['attack'])
            combined_stats['defense'] = max(1, combined_stats['defense'])
            combined_stats['max_health'] = max(10, combined_stats['max_health'])
            combined_stats['current_health'] = max(1, combined_stats['current_health'])
            combined_stats['speed'] = max(1, combined_stats['speed'])
            
            logger.info(f"Combiner stats calculated for team {team_info.get('name', 'Unknown')}: ATK={combined_stats['attack']}, DEF={combined_stats['defense']}, HP={combined_stats['current_health']}/{combined_stats['max_health']}, SPD={combined_stats['speed']}")
            return combined_stats
            
        except Exception as e:
            logger.error(f"Error calculating combiner stats: {e}")
            # Return default stats if calculation fails
            return {
                'attack': 10,
                'defense': 5,
                'max_health': 400,  # 4 pets * 100 each
                'current_health': 400,
                'speed': 10,
                'level': 1,
                'experience': 0,
                'pet_names': ['Default Combiner'],
                'member_ids': [],
                'pet_data': []
            }
    
    async def update_player_stats(self, user_id, stat_name, value):
        """Update player statistics."""
        try:
            user_data = await self.bot.user_data_manager.get_user_data(str(user_id), str(user_id))
            if not user_data:
                return
                
            if 'mega_fights' not in user_data:
                user_data['mega_fights'] = {
                    "mega_fights_won": 0,
                    "mega_fights_lost": 0,
                    "total_energon_won": 0,
                    "total_energon_lost": 0,
                    "total_fights": 0
                }
                
            if stat_name not in user_data['mega_fights']:
                user_data['mega_fights'][stat_name] = 0
                
            user_data['mega_fights'][stat_name] += value
            
            # Save the updated data
            self.bot.user_data_manager.save_user_data(str(user_id), user_data)
            
        except Exception as e:
            logger.error(f"Error updating player stats for {user_id}: {e}")
    
    def has_cybertronian_role(self, member):
        """Check if member has Cybertronian role."""
        return any(role.name.lower() in ['cybertronian', 'cybertronian citizen'] for role in member.roles)
    
    @commands.hybrid_command(name='mega_fight', description="Challenge another combiner team to a Mega-Fight!")
    async def mega_fight(self, ctx):
        """Start a mega-fight between combiner teams."""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can start mega-fights! Please get a Cybertronian role first.")
            return
        
        # Check if user has a complete combiner team
        user_team = await self.find_user_combiner_team(ctx.author.id)
        if not user_team:
            await ctx.send("❌ You need to be part of a complete combiner team to start mega-fights! Use `/combiner` to form a team.")
            return
        
        # Only the head can start mega-fights
        if not user_team['is_head']:
            await ctx.send(f"❌ Only the head member (<@{user_team['head_id']}>) can start mega-fights for your combiner team!")
            return
        
        # Calculate combiner stats for display
        combiner_stats = await self.calculate_combiner_stats(user_team)
        
        # Create mode selection view
        view = MegaFightModeView(self, user_team, ctx, combiner_stats)
        embed = view.create_mode_selection_embed()
        
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    """Setup function to add the PetsMegaCog."""
    await bot.add_cog(PetsMegaCog(bot))