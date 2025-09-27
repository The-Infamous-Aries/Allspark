import discord
from discord.ext import commands
import asyncio
import random
import math
import logging
import json
from typing import List, Dict, Optional, Tuple, Union, Set, Any
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict

from Systems.user_data_manager import user_data_manager
from .pvp_system import PvPBattleView, BattleMode
from ..pet_levels import calculate_xp_gain, create_level_up_embed
from .damage_calculator import DamageCalculator

logger = logging.getLogger('tournament')

class TournamentStatus(Enum):
    REGISTRATION = "registration"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TournamentSize(Enum):
    SMALL = 4
    MEDIUM = 8
    LARGE = 16

class TournamentBattleView(discord.ui.View):
    """Tournament-specific battle view that uses PvP logic but with tournament modifications"""
    
    def __init__(self, bot, player1: discord.Member, player2: discord.Member, tournament_match, tournament_instance):
        super().__init__(timeout=300)
        self.bot = bot
        self.player1 = player1
        self.player2 = player2
        self.tournament_match = tournament_match
        self.tournament = tournament_instance
        self.message = None
        self.battle_over = False
        self.turn_count = 0
        self.battle_log = []
        self.defending_players = set()
        self.guard_relationships = {}
        self.player_actions = {}
        self.waiting_for_actions = False
        self.death_log = []
        self.action_messages = {}
        
        # Initialize players with same structure as PvPBattleView
        self.players = {
            str(player1.id): {
                'user': player1,
                'team_id': 'a',
                'hp': 100, 'max_hp': 100,
                'attack': 10, 'defense': 5,
                'charge': 1.0, 'charging': False,
                'pet': None, 'alive': True,
                'xp_earned': 0, 'damage_dealt': 0,
                'damage_taken': 0, 'kills': 0, 'assists': 0
            },
            str(player2.id): {
                'user': player2,
                'team_id': 'b',
                'hp': 100, 'max_hp': 100,
                'attack': 10, 'defense': 5,
                'charge': 1.0, 'charging': False,
                'pet': None, 'alive': True,
                'xp_earned': 0, 'damage_dealt': 0,
                'damage_taken': 0, 'kills': 0, 'assists': 0
            }
        }
        
        self.teams = {'a': [player1], 'b': [player2]}
        self.team_assignments = {str(player1.id): 'a', str(player2.id): 'b'}
        self.team_names = {'a': f"{player1.display_name}'s Team", 'b': f"{player2.display_name}'s Team"}
        
        # Team colors and emojis
        self.team_colors = {'a': discord.Color.blue(), 'b': discord.Color.red()}
        self.team_emojis = {'a': '🔵', 'b': '🔴'}
        
        # Start battle initialization
        asyncio.create_task(self.initialize_battle_data())
    
    async def initialize_battle_data(self):
        """Initialize pet data for both participants"""
        try:
            # Load pet data for both players
            await self._load_pet_data(str(self.player1.id), self.players[str(self.player1.id)])
            await self._load_pet_data(str(self.player2.id), self.players[str(self.player2.id)])
            
            await self.start_battle()
        except Exception as e:
            logger.error(f"Tournament battle init error: {e}", exc_info=True)
            if self.message:
                await self.message.edit(content=f"❌ Error: {str(e)}", view=None)
    
    async def _load_pet_data(self, player_id: str, player: dict):
        """Load pet data for a player (copied from PvPBattleView)"""
        try:
            pet_data = await user_data_manager.get_pet_data(player_id)
            if not pet_data:
                raise ValueError(f"No pet data found for player {player['user'].display_name}")
            
            player['pet'] = pet_data
            
            # Calculate base stats
            level = pet_data.get('level', 1)
            base_attack = 10 + (level * 2)
            base_defense = 5 + level
            base_hp = 100 + (level * 10)
            
            # Apply equipment bonuses
            equipment = pet_data.get('equipment', {})
            equipment_stats = self.calculate_equipment_stats(equipment)
            
            # Set final stats
            player['attack'] = base_attack + equipment_stats.get('attack', 0)
            player['defense'] = base_defense + equipment_stats.get('defense', 0)
            player['max_hp'] = base_hp + equipment_stats.get('energy', 0)
            player['hp'] = player['max_hp']
            
        except Exception as e:
            logger.error(f"Error loading pet data for {player_id}: {e}")
            raise
    
    def calculate_equipment_stats(self, equipment):
        """Calculate total stats from equipped items (copied from PvPBattleView)"""
        total_stats = {'attack': 0, 'defense': 0, 'energy': 0, 'maintenance': 0, 'happiness': 0}
        
        if not equipment:
            return total_stats
            
        for slot, item in equipment.items():
            if item and isinstance(item, dict):
                stat_bonus = item.get('stat_bonus', {})
                for stat, value in stat_bonus.items():
                    if stat in total_stats:
                        total_stats[stat] += value
                    elif stat == 'max_energy':
                        total_stats['energy'] += value
        
        return total_stats
    
    async def start_battle(self):
        """Start the tournament battle"""
        try:
            embed = self.build_battle_embed()
            embed.title = f"🏆 Tournament Battle - {self.tournament_match.match_id}"
            embed.description = f"**{self.player1.display_name}** vs **{self.player2.display_name}**\n\n{embed.description}"
            
            self.message = await self.tournament.channel.send(
                content=f"{self.player1.mention} vs {self.player2.mention} - Tournament battle begins!",
                embed=embed,
                view=self
            )
            
            await self.process_turn()
            
        except Exception as e:
            logger.error(f"Error starting tournament battle: {e}")
            await self.tournament.channel.send(f"❌ Error starting tournament battle: {str(e)}")
    
    def build_battle_embed(self) -> discord.Embed:
        """Build the battle status embed (adapted from PvPBattleView)"""
        embed = discord.Embed(
            title="⚔️ Tournament Battle",
            color=discord.Color.gold()
        )
        
        # Build team status
        team_status = ""
        for team_id in ['a', 'b']:
            team_members = [p for p in self.players.values() if p['team_id'] == team_id]
            if team_members:
                emoji = self.team_emojis.get(team_id, '⚔️')
                team_name = self.team_names.get(team_id, f"Team {team_id.upper()}")
                team_status += f"{emoji} **{team_name}**\n"
                
                for player in team_members:
                    if player['alive']:
                        hp_bar = self.create_hp_bar(player['hp'], player['max_hp'])
                        charge_bar = self.create_charge_bar(player['charge'])
                        status_icon = "🛡️" if str(player['user'].id) in self.defending_players else "⚔️"
                        team_status += f"  {status_icon} {player['user'].display_name}: {hp_bar} {charge_bar}\n"
                    else:
                        team_status += f"  💀 {player['user'].display_name}: **DEFEATED**\n"
                team_status += "\n"
        
        embed.description = team_status
        
        # Add battle log if exists
        if self.battle_log:
            recent_log = self.battle_log[-5:]  # Show last 5 actions
            log_text = "\n".join(recent_log)
            embed.add_field(name="📜 Recent Actions", value=log_text, inline=False)
        
        embed.set_footer(text=f"Turn {self.turn_count} | Tournament Match")
        return embed
    
    def create_hp_bar(self, current_hp: int, max_hp: int) -> str:
        """Create HP bar visualization"""
        if max_hp <= 0:
            return "❤️ 0/0"
        
        percentage = current_hp / max_hp
        bar_length = 10
        filled_length = int(bar_length * percentage)
        
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        return f"❤️ {current_hp}/{max_hp} [{bar}]"
    
    def create_charge_bar(self, charge: float) -> str:
        """Create charge bar visualization"""
        percentage = min(charge, 3.0) / 3.0
        bar_length = 5
        filled_length = int(bar_length * percentage)
        
        bar = "⚡" * filled_length + "○" * (bar_length - filled_length)
        return f"[{bar}] {charge:.1f}"
    
    async def process_turn(self):
        """Process a battle turn (adapted from PvPBattleView)"""
        if self.battle_over:
            return
        
        self.turn_count += 1
        
        # Check if battle should end
        if await self.check_battle_end():
            return
        
        # Process charging for all players
        await self.process_charge()
        
        # Clear previous actions
        self.player_actions.clear()
        self.defending_players.clear()
        
        # Set up action collection
        self.waiting_for_actions = True
        
        # Update battle display
        embed = self.build_battle_embed()
        await self.message.edit(embed=embed, view=self)
        
        # Wait for actions or timeout
        await asyncio.sleep(30)  # 30 second turn timer
        
        # Process collected actions
        await self.process_combat_interactions()
        
        # Continue to next turn
        await self.process_turn()
    
    async def process_charge(self):
        """Process charging phase for all players"""
        for player in self.players.values():
            if player['alive'] and player['charging']:
                player['charge'] = min(player['charge'] + 0.5, 3.0)
                if player['charge'] >= 3.0:
                    player['charging'] = False
                    self.battle_log.append(f"⚡ {player['user'].display_name} is fully charged!")
    
    async def process_combat_interactions(self):
        """Process all combat interactions for the turn"""
        if not self.player_actions:
            self.battle_log.append("⏰ No actions taken this turn.")
            return
        
        # Process attacks
        for attacker_id, action_data in self.player_actions.items():
            if action_data['action'] == 'attack':
                await self.process_attack(attacker_id, action_data['target_id'])
        
        # Check for battle end after attacks
        await self.check_battle_end()
    
    async def process_attack(self, attacker_id: str, target_id: str):
        """Process an attack between two players"""
        attacker = self.players.get(attacker_id)
        target = self.players.get(target_id)
        
        if not attacker or not target or not attacker['alive'] or not target['alive']:
            return
        
        # Calculate damage using DamageCalculator
        damage_calc = DamageCalculator()
        base_damage = damage_calc.calculate_damage(
            attacker['attack'], 
            target['defense'], 
            attacker['charge']
        )
        
        # Apply charge multiplier
        charge_multiplier = min(attacker['charge'], 3.0)
        final_damage = int(base_damage * charge_multiplier)
        
        # Apply damage
        target['hp'] = max(0, target['hp'] - final_damage)
        target['damage_taken'] += final_damage
        attacker['damage_dealt'] += final_damage
        
        # Reset attacker's charge
        attacker['charge'] = 1.0
        attacker['charging'] = False
        
        # Log the attack
        self.battle_log.append(
            f"⚔️ {attacker['user'].display_name} attacks {target['user'].display_name} for {final_damage} damage!"
        )
        
        # Check if target is defeated
        if target['hp'] <= 0:
            target['alive'] = False
            attacker['kills'] += 1
            self.battle_log.append(f"💀 {target['user'].display_name} has been defeated!")
    
    async def check_battle_end(self) -> bool:
        """Check if the battle should end"""
        alive_teams = set()
        for player in self.players.values():
            if player['alive']:
                alive_teams.add(player['team_id'])
        
        if len(alive_teams) <= 1:
            await self.end_battle()
            return True
        
        return False
    
    async def end_battle(self):
        """End the tournament battle with tournament-specific logic"""
        if self.battle_over:
            return
        
        self.battle_over = True
        
        # Determine winner
        winner_team = None
        winner_player = None
        loser_player = None
        
        for player in self.players.values():
            if player['alive']:
                winner_team = player['team_id']
                winner_player = player
            else:
                loser_player = player
        
        if not winner_player:
            # Draw - shouldn't happen in 1v1
            await self.message.edit(content="⚖️ Tournament battle ended in a draw!", view=None)
            return
        
        # Tournament-specific: Only give massive XP to winner, no stat deductions
        # Give 500 XP for winning each round (progressing to next round)
        winner_xp = 500  # 500 XP for progressing to next round
        winner_player['xp_earned'] = winner_xp
        
        # Apply XP to winner's pet
        try:
            current_pet_data = await user_data_manager.get_pet_data(str(winner_player['user'].id))
            if current_pet_data:
                old_level = current_pet_data.get('level', 1)
                new_xp = current_pet_data.get('xp', 0) + winner_xp
                current_pet_data['xp'] = new_xp
                
                # Check for level up
                level_up_embed = None
                if calculate_xp_gain(old_level, new_xp) > old_level:
                    new_level = calculate_xp_gain(old_level, new_xp)
                    current_pet_data['level'] = new_level
                    level_up_embed = create_level_up_embed(current_pet_data, old_level, new_level)
                
                await user_data_manager.save_pet_data(str(winner_player['user'].id), current_pet_data)
                
                # Send level up notification if applicable
                if level_up_embed:
                    await self.tournament.channel.send(embed=level_up_embed)
        
        except Exception as e:
            logger.error(f"Error applying tournament XP: {e}")
        
        # Create battle result embed
        embed = discord.Embed(
            title="🏆 Tournament Battle Complete!",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="🥇 Winner",
            value=f"{winner_player['user'].display_name}\n+{winner_xp} XP",
            inline=True
        )
        
        embed.add_field(
            name="Battle Stats",
            value=f"Turns: {self.turn_count}\nDamage Dealt: {winner_player['damage_dealt']}\nDamage Taken: {winner_player['damage_taken']}",
            inline=True
        )
        
        # Update the message with final results
        await self.message.edit(embed=embed, view=None)
        
        # Set tournament match winner
        if winner_team == 'a':
            self.tournament_match.set_winner(self.player1)
        else:
            self.tournament_match.set_winner(self.player2)
        
        # Schedule message deletion and tournament progression
        asyncio.create_task(self.cleanup_and_progress())
    
    async def cleanup_and_progress(self):
        """Clean up battle message and progress tournament after delay"""
        # Wait 10 seconds before cleanup
        await asyncio.sleep(10)
        
        # Delete the battle message
        try:
            await self.message.delete()
        except:
            pass  # Message might already be deleted
        
        # Progress the tournament
        await self.tournament.handle_match_completion(self.tournament_match)
    
    @discord.ui.button(label="⚔️ Attack", style=discord.ButtonStyle.danger)
    async def attack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle attack button press"""
        if not self.waiting_for_actions or self.battle_over:
            await interaction.response.send_message("❌ Not accepting actions right now.", ephemeral=True)
            return
        
        player_id = str(interaction.user.id)
        if player_id not in self.players or not self.players[player_id]['alive']:
            await interaction.response.send_message("❌ You're not in this battle or are defeated.", ephemeral=True)
            return
        
        if player_id in self.player_actions:
            await interaction.response.send_message("❌ You've already chosen an action this turn.", ephemeral=True)
            return
        
        # Find target (the other player)
        target_id = None
        for pid, player in self.players.items():
            if pid != player_id and player['alive']:
                target_id = pid
                break
        
        if not target_id:
            await interaction.response.send_message("❌ No valid target found.", ephemeral=True)
            return
        
        # Record action
        self.player_actions[player_id] = {
            'action': 'attack',
            'target_id': target_id
        }
        
        target_name = self.players[target_id]['user'].display_name
        await interaction.response.send_message(f"⚔️ You will attack {target_name}!", ephemeral=True)
    
    @discord.ui.button(label="⚡ Charge", style=discord.ButtonStyle.primary)
    async def charge_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle charge button press"""
        if not self.waiting_for_actions or self.battle_over:
            await interaction.response.send_message("❌ Not accepting actions right now.", ephemeral=True)
            return
        
        player_id = str(interaction.user.id)
        if player_id not in self.players or not self.players[player_id]['alive']:
            await interaction.response.send_message("❌ You're not in this battle or are defeated.", ephemeral=True)
            return
        
        if player_id in self.player_actions:
            await interaction.response.send_message("❌ You've already chosen an action this turn.", ephemeral=True)
            return
        
        # Set charging
        self.players[player_id]['charging'] = True
        self.player_actions[player_id] = {'action': 'charge'}
        
        await interaction.response.send_message("⚡ You will charge up this turn!", ephemeral=True)
    
    @discord.ui.button(label="🛡️ Defend", style=discord.ButtonStyle.secondary)
    async def defend_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle defend button press"""
        if not self.waiting_for_actions or self.battle_over:
            await interaction.response.send_message("❌ Not accepting actions right now.", ephemeral=True)
            return
        
        player_id = str(interaction.user.id)
        if player_id not in self.players or not self.players[player_id]['alive']:
            await interaction.response.send_message("❌ You're not in this battle or are defeated.", ephemeral=True)
            return
        
        if player_id in self.player_actions:
            await interaction.response.send_message("❌ You've already chosen an action this turn.", ephemeral=True)
            return
        
        # Set defending
        self.defending_players.add(player_id)
        self.player_actions[player_id] = {'action': 'defend'}
        
        await interaction.response.send_message("🛡️ You will defend this turn!", ephemeral=True)

class TournamentMatch:
    """Represents a single match in the tournament bracket"""
    
    def __init__(self, match_id: str, round_num: int, player1: discord.Member = None, player2: discord.Member = None):
        self.match_id = match_id
        self.round_num = round_num
        self.player1 = player1
        self.player2 = player2
        self.winner = None
        self.completed = False
        self.battle_view = None
    
    def is_ready(self) -> bool:
        """Check if both players are assigned and match can start"""
        return self.player1 is not None and self.player2 is not None and not self.completed
    
    def set_winner(self, winner: discord.Member):
        """Set the winner of this match"""
        if winner in [self.player1, self.player2]:
            self.winner = winner
            self.completed = True
        else:
            raise ValueError("Winner must be one of the match participants")

class Tournament:
    """Main tournament class handling bracket generation and match management"""
    
    def __init__(self, bot, organizer: discord.Member, size: TournamentSize, channel: discord.TextChannel):
        self.bot = bot
        self.organizer = organizer
        self.size = size
        self.channel = channel
        self.status = TournamentStatus.REGISTRATION
        self.participants: List[discord.Member] = []
        self.matches: Dict[str, TournamentMatch] = {}
        self.current_round = 1
        self.max_rounds = int(math.log2(size.value))
        self.registration_deadline = datetime.now() + timedelta(minutes=10)  # 10 minute registration
        self.bracket_message = None
        
    def has_cybertronian_role(self, member: discord.Member) -> bool:
        """Check if a member has any Cybertronian role"""
        if not member or not member.roles:
            return False
        
        from config import get_role_ids
        
        guild_id = member.guild.id if member.guild else None
        role_ids_config = get_role_ids(guild_id)
        
        cybertronian_roles = []
        for role_name in ['Autobot', 'Decepticon', 'Maverick', 'Cybertronian_Citizen']:
            role_ids = role_ids_config.get(role_name, [])
            if isinstance(role_ids, list):
                cybertronian_roles.extend(role_ids)
            elif role_ids:
                cybertronian_roles.append(role_ids)
        
        return any(role.id in cybertronian_roles for role in member.roles)
    
    async def get_eligible_users(self, guild: discord.Guild) -> List[discord.Member]:
        """Get all guild members with Cybertronian roles and pets"""
        eligible_users = []
        
        for member in guild.members:
            if member.bot:
                continue
                
            # Check if they have Cybertronian role
            if not self.has_cybertronian_role(member):
                continue
                
            # Check if they have a pet
            try:
                pet_data = await user_data_manager.get_pet_data(str(member.id))
                if pet_data and pet_data.get('name'):
                    eligible_users.append(member)
            except Exception as e:
                logger.warning(f"Error checking pet data for {member.id}: {e}")
                continue
        
        return eligible_users
    
    def add_participant(self, member: discord.Member) -> bool:
        """Add a participant to the tournament"""
        if self.status != TournamentStatus.REGISTRATION:
            return False
            
        if len(self.participants) >= self.size.value:
            return False
            
        if member not in self.participants:
            self.participants.append(member)
            return True
        return False
    
    def remove_participant(self, member: discord.Member) -> bool:
        """Remove a participant from the tournament"""
        if self.status != TournamentStatus.REGISTRATION:
            return False
            
        if member in self.participants:
            self.participants.remove(member)
            return True
        return False
    
    def can_start(self) -> bool:
        """Check if tournament can start"""
        return (len(self.participants) == self.size.value and 
                self.status == TournamentStatus.REGISTRATION)
    
    def generate_bracket(self):
        """Generate the tournament bracket"""
        if not self.can_start():
            raise ValueError("Cannot generate bracket - tournament not ready")
        
        # Shuffle participants for random seeding
        participants = self.participants.copy()
        random.shuffle(participants)
        
        # Generate first round matches
        self.matches.clear()
        match_count = 0
        
        for i in range(0, len(participants), 2):
            match_id = f"R{self.current_round}M{match_count + 1}"
            match = TournamentMatch(
                match_id=match_id,
                round_num=self.current_round,
                player1=participants[i],
                player2=participants[i + 1] if i + 1 < len(participants) else None
            )
            self.matches[match_id] = match
            match_count += 1
        
        self.status = TournamentStatus.IN_PROGRESS
    
    def advance_round(self):
        """Advance to the next round of the tournament"""
        if self.current_round >= self.max_rounds:
            self.status = TournamentStatus.COMPLETED
            return
        
        # Get winners from current round
        current_round_matches = [m for m in self.matches.values() if m.round_num == self.current_round]
        winners = []
        
        for match in current_round_matches:
            if match.completed and match.winner:
                winners.append(match.winner)
        
        if len(winners) < len(current_round_matches):
            raise ValueError("Not all matches in current round are completed")
        
        # Create next round matches
        self.current_round += 1
        match_count = 0
        
        for i in range(0, len(winners), 2):
            match_id = f"R{self.current_round}M{match_count + 1}"
            match = TournamentMatch(
                match_id=match_id,
                round_num=self.current_round,
                player1=winners[i],
                player2=winners[i + 1] if i + 1 < len(winners) else None
            )
            self.matches[match_id] = match
            match_count += 1
        
        # Check if tournament is complete
        if self.current_round > self.max_rounds:
            self.status = TournamentStatus.COMPLETED
    
    def get_current_matches(self) -> List[TournamentMatch]:
        """Get matches for the current round"""
        return [m for m in self.matches.values() if m.round_num == self.current_round and not m.completed]
    
    def get_champion(self) -> Optional[discord.Member]:
        """Get the tournament champion"""
        if self.status != TournamentStatus.COMPLETED:
            return None
        
        final_matches = [m for m in self.matches.values() if m.round_num == self.max_rounds]
        if final_matches and final_matches[0].completed:
            return final_matches[0].winner
        return None
    
    def get_bracket_display(self) -> str:
        """Generate a compact text representation of the tournament bracket"""
        if not self.matches:
            return "No bracket generated yet."
        
        bracket_text = f"🏆 **{self.size.value}P Tournament** | Round {self.current_round}/{self.max_rounds}\n\n"
        
        # Only show current round and completed rounds to save space
        for round_num in range(1, self.current_round + 1):
            round_matches = [m for m in self.matches.values() if m.round_num == round_num]
            if not round_matches:
                continue
                
            # Compact round headers
            if round_num == self.max_rounds:
                bracket_text += f"🏆 **FINAL**\n"
            elif round_num == self.max_rounds - 1:
                bracket_text += f"🥉 **SEMIS**\n"
            else:
                bracket_text += f"⚔️ **R{round_num}**\n"
            
            for match in round_matches:
                if match.player1 and match.player2:
                    if match.completed:
                        # Compact completed match display
                        winner = match.winner.display_name[:12]  # Truncate long names
                        loser = (match.player1 if match.winner == match.player2 else match.player2).display_name[:12]
                        bracket_text += f"✅ **{winner}** def. ~~{loser}~~\n"
                    else:
                        # Current round matches
                        p1 = match.player1.display_name[:12]
                        p2 = match.player2.display_name[:12]
                        bracket_text += f"🔴 {p1} vs {p2}\n"
                elif match.player1:
                    bracket_text += f"🎯 {match.player1.display_name[:12]} (Bye)\n"
        
        # Show next round preview if not final
        if self.current_round < self.max_rounds:
            next_round_matches = [m for m in self.matches.values() if m.round_num == self.current_round + 1]
            if next_round_matches:
                bracket_text += f"\n⏳ **Next: R{self.current_round + 1}**\n"
                for match in next_round_matches[:3]:  # Show max 3 upcoming matches
                    if match.player1 and match.player2:
                        p1 = match.player1.display_name[:12]
                        p2 = match.player2.display_name[:12]
                        bracket_text += f"⏳ {p1} vs {p2}\n"
                if len(next_round_matches) > 3:
                    bracket_text += f"... +{len(next_round_matches) - 3} more\n"
        
        if self.status == TournamentStatus.COMPLETED:
            champion = self.get_champion()
            if champion:
                bracket_text += f"\n🎉 **CHAMPION: {champion.display_name}** 🎉"
        
        return bracket_text
    
    async def handle_match_completion(self, completed_match: TournamentMatch):
        """Handle completion of a tournament match with bracket refresh and progression"""
        try:
            # Check if all matches in current round are complete
            current_round_matches = [m for m in self.matches.values() if m.round_num == self.current_round]
            all_complete = all(m.completed for m in current_round_matches)
            
            # Send updated bracket
            embed = discord.Embed(
                title="🏆 Tournament Bracket Updated",
                description=self.get_bracket_display(),
                color=discord.Color.gold()
            )
            await self.channel.send(embed=embed)
            
            if all_complete:
                if self.current_round >= self.max_rounds:
                    # Tournament is complete
                    self.status = TournamentStatus.COMPLETED
                    champion = self.get_champion()
                    
                    # Give massive XP to tournament winner
                    if champion:
                        try:
                            current_pet_data = await user_data_manager.get_pet_data(str(champion.id))
                            if current_pet_data:
                                tournament_bonus_xp = 2000  # Massive tournament completion bonus
                                old_level = current_pet_data.get('level', 1)
                                new_xp = current_pet_data.get('xp', 0) + tournament_bonus_xp
                                current_pet_data['xp'] = new_xp
                                
                                # Check for level up
                                if calculate_xp_gain(old_level, new_xp) > old_level:
                                    new_level = calculate_xp_gain(old_level, new_xp)
                                    current_pet_data['level'] = new_level
                                    level_up_embed = create_level_up_embed(current_pet_data, old_level, new_level)
                                    await self.channel.send(embed=level_up_embed)
                                
                                await user_data_manager.save_pet_data(str(champion.id), current_pet_data)
                        except Exception as e:
                            logger.error(f"Error applying tournament champion XP: {e}")
                    
                    embed = discord.Embed(
                        title="🎉 TOURNAMENT COMPLETE! 🎉",
                        description=f"**🏆 CHAMPION: {champion.display_name}** 🏆\n\n{self.get_bracket_display()}",
                        color=discord.Color.gold()
                    )
                    embed.add_field(
                        name="🎁 Champion Rewards",
                        value="• 2000 Bonus XP\n• Tournament Glory\n• Bragging Rights",
                        inline=False
                    )
                    await self.channel.send(embed=embed)
                else:
                    # Advance to next round
                    self.advance_round()
                    
                    embed = discord.Embed(
                        title=f"⚔️ Round {self.current_round} Starting Soon!",
                        description=f"Next battles begin in 10 seconds...\n\n{self.get_bracket_display()}",
                        color=discord.Color.blue()
                    )
                    await self.channel.send(embed=embed)
                    
                    # Wait 10 seconds then start next round matches
                    await asyncio.sleep(10)
                    
                    # Start next round matches
                    next_matches = self.get_current_matches()
                    for match in next_matches:
                        if match.is_ready():
                            await self.start_match(match)
            
        except Exception as e:
            logger.error(f"Error handling match completion: {e}")
            await self.channel.send("❌ Error processing tournament match completion.")

class TournamentView(discord.ui.View):
    """Discord UI View for tournament registration and management"""
    
    def __init__(self, tournament: Tournament):
        super().__init__(timeout=600)  # 10 minute timeout
        self.tournament = tournament
    
    @discord.ui.button(label="Join Tournament", style=discord.ButtonStyle.green, emoji="⚔️")
    async def join_tournament(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle tournament join requests"""
        if self.tournament.status != TournamentStatus.REGISTRATION:
            await interaction.response.send_message("❌ Tournament registration is closed!", ephemeral=True)
            return
        
        # Check if user has Cybertronian role
        if not self.tournament.has_cybertronian_role(interaction.user):
            await interaction.response.send_message(
                "❌ Only Cybertronian Citizens can join tournaments! Please get a Cybertronian role first.",
                ephemeral=True
            )
            return
        
        # Check if user has a pet
        try:
            pet_data = await user_data_manager.get_pet_data(str(interaction.user.id))
            if not pet_data or not pet_data.get('name'):
                await interaction.response.send_message(
                    "❌ You need a pet to join the tournament! Use `/pet_create` to get started.",
                    ephemeral=True
                )
                return
        except Exception:
            await interaction.response.send_message(
                "❌ Error checking your pet data. Please try again.",
                ephemeral=True
            )
            return
        
        # Try to add participant
        if self.tournament.add_participant(interaction.user):
            await interaction.response.send_message(
                f"✅ You've joined the tournament! ({len(self.tournament.participants)}/{self.tournament.size.value})",
                ephemeral=True
            )
            await self.update_tournament_message(interaction)
        else:
            await interaction.response.send_message("❌ Could not join tournament (full or already joined).", ephemeral=True)
    
    @discord.ui.button(label="Leave Tournament", style=discord.ButtonStyle.red, emoji="🚪")
    async def leave_tournament(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle tournament leave requests"""
        if self.tournament.status != TournamentStatus.REGISTRATION:
            await interaction.response.send_message("❌ Cannot leave tournament after registration closes!", ephemeral=True)
            return
        
        if self.tournament.remove_participant(interaction.user):
            await interaction.response.send_message("✅ You've left the tournament.", ephemeral=True)
            await self.update_tournament_message(interaction)
        else:
            await interaction.response.send_message("❌ You're not in this tournament.", ephemeral=True)
    
    @discord.ui.button(label="Start Tournament", style=discord.ButtonStyle.primary, emoji="🏁")
    async def start_tournament(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Start the tournament (organizer only)"""
        if interaction.user != self.tournament.organizer:
            await interaction.response.send_message("❌ Only the tournament organizer can start the tournament!", ephemeral=True)
            return
        
        if not self.tournament.can_start():
            await interaction.response.send_message(
                f"❌ Tournament needs exactly {self.tournament.size.value} participants to start! "
                f"Currently have {len(self.tournament.participants)}.",
                ephemeral=True
            )
            return
        
        try:
            self.tournament.generate_bracket()
            await interaction.response.send_message("🏁 Tournament started! Generating bracket...", ephemeral=True)
            await self.start_tournament_battles(interaction)
        except Exception as e:
            logger.error(f"Error starting tournament: {e}")
            await interaction.response.send_message("❌ Error starting tournament. Please try again.", ephemeral=True)
    
    @discord.ui.button(label="Auto-Fill", style=discord.ButtonStyle.secondary, emoji="🤖")
    async def auto_fill(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Auto-fill tournament with eligible users (organizer only)"""
        if interaction.user != self.tournament.organizer:
            await interaction.response.send_message("❌ Only the tournament organizer can auto-fill!", ephemeral=True)
            return
        
        if self.tournament.status != TournamentStatus.REGISTRATION:
            await interaction.response.send_message("❌ Tournament registration is closed!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            eligible_users = await self.tournament.get_eligible_users(interaction.guild)
            # Remove already registered participants
            available_users = [u for u in eligible_users if u not in self.tournament.participants]
            
            if not available_users:
                await interaction.followup.send("❌ No eligible users found to auto-fill tournament.", ephemeral=True)
                return
            
            # Randomly select users to fill remaining spots
            spots_needed = self.tournament.size.value - len(self.tournament.participants)
            if spots_needed <= 0:
                await interaction.followup.send("❌ Tournament is already full!", ephemeral=True)
                return
            
            selected_users = random.sample(available_users, min(spots_needed, len(available_users)))
            added_count = 0
            
            for user in selected_users:
                if self.tournament.add_participant(user):
                    added_count += 1
            
            await interaction.followup.send(
                f"✅ Auto-filled {added_count} participants! "
                f"Tournament now has {len(self.tournament.participants)}/{self.tournament.size.value} players.",
                ephemeral=True
            )
            await self.update_tournament_message(interaction)
            
        except Exception as e:
            logger.error(f"Error auto-filling tournament: {e}")
            await interaction.followup.send("❌ Error auto-filling tournament. Please try again.", ephemeral=True)
    
    async def update_tournament_message(self, interaction: discord.Interaction):
        """Update the tournament message with current status"""
        embed = self.create_tournament_embed()
        try:
            await interaction.edit_original_response(embed=embed, view=self)
        except:
            # If we can't edit, send a new message
            await interaction.followup.send(embed=embed, view=self)
    
    async def start_tournament_battles(self, interaction: discord.Interaction):
        """Start the first round of tournament battles"""
        current_matches = self.tournament.get_current_matches()
        
        if not current_matches:
            await interaction.followup.send("❌ No matches to start!", ephemeral=True)
            return
        
        # Update the tournament display
        embed = self.create_tournament_embed()
        await interaction.edit_original_response(embed=embed, view=None)
        
        # Start all matches in the current round
        for match in current_matches:
            if match.is_ready():
                await self.start_match(match)
    
    async def start_match(self, match: TournamentMatch):
        """Start a single tournament match"""
        try:
            # Create tournament battle with mentions
            await self.tournament.channel.send(
                f"🏆 **{match.match_id}** starting now!\n{match.player1.mention} vs {match.player2.mention}"
            )
            
            # Create tournament-specific battle view
            battle_view = TournamentBattleView(
                self.tournament.bot, 
                match.player1, 
                match.player2, 
                match, 
                self.tournament
            )
            
            # Store reference to battle view
            match.battle_view = battle_view
            
        except Exception as e:
            logger.error(f"Error starting tournament match {match.match_id}: {e}")
            await self.tournament.channel.send(f"❌ Error starting match {match.match_id}. Please contact an admin.")
    

    
    def create_tournament_embed(self) -> discord.Embed:
        """Create the tournament status embed"""
        embed = discord.Embed(
            title=f"🏆 Pet Tournament ({self.tournament.size.value} Players)",
            color=0x0099ff
        )
        
        if self.tournament.status == TournamentStatus.REGISTRATION:
            embed.description = f"**Registration Open!**\n\nParticipants: {len(self.tournament.participants)}/{self.tournament.size.value}"
            
            if self.tournament.participants:
                participant_list = "\n".join([f"⚔️ {p.display_name}" for p in self.tournament.participants])
                embed.add_field(name="Registered Players", value=participant_list, inline=False)
            
            embed.add_field(
                name="Requirements",
                value="• Must have a Cybertronian role\n• Must have a pet\n• Tournament starts when full",
                inline=False
            )
            
            time_left = self.tournament.registration_deadline - datetime.now()
            if time_left.total_seconds() > 0:
                embed.add_field(
                    name="Registration Deadline",
                    value=f"<t:{int(self.tournament.registration_deadline.timestamp())}:R>",
                    inline=False
                )
        
        elif self.tournament.status == TournamentStatus.IN_PROGRESS:
            embed.description = f"**Tournament In Progress!**\n\n{self.tournament.get_bracket_display()}"
        
        elif self.tournament.status == TournamentStatus.COMPLETED:
            champion = self.tournament.get_champion()
            embed.description = f"**Tournament Complete!**\n\n🏆 **Champion: {champion.display_name if champion else 'Unknown'}**"
            embed.add_field(name="Final Bracket", value=self.tournament.get_bracket_display(), inline=False)
        
        embed.set_footer(text=f"Organized by {self.tournament.organizer.display_name}")
        return embed