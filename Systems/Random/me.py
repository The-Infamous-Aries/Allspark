import discord
from discord.ext import commands
from datetime import datetime
import asyncio
from typing import Optional, Dict, Any
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)

class ProfileView(discord.ui.View):
    """Discord UI view for comprehensive user profiles."""
    
    def __init__(self, target_member, interaction):
        super().__init__(timeout=300)
        self.target_member = target_member
        self.interaction = interaction
        self.current_view = "me"
        
        # Use UserDataManager exclusively
        self.data_manager = interaction.client.user_data_manager
            
        # Lazy loading cache
        self._cached_data = {}
        self._data_loaded = False
    
    def get_rank_emojis(self, count):
        """Get rank emojis for leaderboards"""
        if count <= 5:
            return ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        else:
            return ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    async def _get_user_data(self):
        """Get user theme data with caching"""
        if not self._data_loaded:
            try:
                self._cached_data = await self.data_manager.get_user_theme_data(str(self.target_member.id))
                self._data_loaded = True
            except Exception as e:
                logger.error(f"Error loading user data for {self.target_member.id}: {e}")
                self._cached_data = {}
        return self._cached_data
    
    async def _get_player_stats(self, player_id):
        """Get or create player statistics from UserDataManager."""
        try:
            energon_data = await self.interaction.client.user_data_manager.get_energon_stats(player_id)
            # Map energon data fields to expected format for backward compatibility
            return {
                "games_won": energon_data.get('games_won', 0),
                "games_lost": energon_data.get('games_lost', 0),
                "challenges_won": energon_data.get('challenge_energon_earned', 0),  # Approximate
                "challenges_lost": 0,  # Not directly tracked, use 0 as fallback
                "total_energon_gained": energon_data.get('total_earned', 0),
                "total_energon_lost": energon_data.get('total_spent', 0),
                "energon_bank": energon_data.get('energon_bank', 0),
                "challenge_energon_won": energon_data.get('challenge_energon_earned', 0),
                "challenge_energon_lost": energon_data.get('total_spent', 0),  # Approximate
                "current_energon": energon_data.get('energon', 0),
                "lifetime_energon": energon_data.get('total_earned', 0)
            }
        except Exception as e:
            logger.error(f"Error getting player stats for {player_id}: {e}")
            return {
                "games_won": 0,
                "games_lost": 0,
                "challenges_won": 0,
                "challenges_lost": 0,
                "total_energon_gained": 0,
                "total_energon_lost": 0,
                "energon_bank": 0,
                "challenge_energon_won": 0,
                "challenge_energon_lost": 0,
                "current_energon": 0,
                "lifetime_energon": 0
            }
    
    async def create_me_embed(self):
        """Create the personal stats embed"""
        player_id = str(self.target_member.id)
        stats = await self._get_player_stats(player_id)
        
        # Get transformer data from cache
        theme_data = await self._get_user_data()
        transformer_name = theme_data.get("transformer_name", "Not assigned")
        faction = theme_data.get("transformer_faction", "Unknown").capitalize()
        transformer_class = theme_data.get("transformer_class", "Unknown").capitalize()
        
        # Set color based on faction
        color = discord.Color.dark_gold()
        if faction.lower() == "decepticon":
            color = discord.Color.purple()
        elif faction.lower() == "autobot":
            color = discord.Color.red()
        
        embed = discord.Embed(
            title=f"📊 {self.target_member.display_name}'s Profile",
            description="Personal statistics and Transformer identity",
            color=color
        )
        
        # Add Transformer identity
        if transformer_name != "Not assigned":
            if transformer_class != "Unknown":
                embed.add_field(
                    name="🤖 Transformer Identity", 
                    value=f"**{transformer_name}**\n{faction} {transformer_class}", 
                    inline=False
                )
            else:
                embed.add_field(
                    name="🤖 Transformer Identity", 
                    value=f"**{transformer_name}** ({faction})", 
                    inline=False
                )
        else:
            embed.add_field(
                name="🤖 Transformer Identity", 
                value="*Use `/spark` to get your Transformer identity!*", 
                inline=False
            )
        
        # Add game statistics
        embed.add_field(name="🏆 Games Won", value=stats.get('games_won', 0), inline=True)
        embed.add_field(name="💀 Games Lost", value=stats.get('games_lost', 0), inline=True)
        embed.add_field(name="🏦 Banked Energon", value=stats.get('energon_bank', 0), inline=True)
        embed.add_field(name="⚔️ Challenges Won", value=stats.get('challenges_won', 0), inline=True)
        embed.add_field(name="💰 Challenge Winnings", value=stats.get('challenge_energon_won', 0), inline=True)
        embed.add_field(name="💎 Total Energon Gained", value=stats.get('total_energon_gained', 0), inline=True)
        embed.add_field(name="💔 Challenges Lost", value=stats.get('challenges_lost', 0), inline=True)
        embed.add_field(name="💸 Challenge Losses", value=stats.get('challenge_energon_lost', 0), inline=True)
        embed.add_field(name="💸 Total Energon Lost", value=stats.get('total_energon_lost', 0), inline=True)

        # Calculate win rates
        total_games = stats.get('games_won', 0) + stats.get('games_lost', 0)
        total_challenges = stats.get('challenges_won', 0) + stats.get('challenges_lost', 0)
        
        if total_games > 0:
            game_win_rate = (stats.get('games_won', 0) / total_games) * 100
            embed.add_field(name="📈 Game Win Rate", value=f"{game_win_rate:.1f}%", inline=True)
        
        if total_challenges > 0:
            challenge_win_rate = (stats.get('challenges_won', 0) / total_challenges) * 100
            embed.add_field(name="⚔️ Challenge Win Rate", value=f"{challenge_win_rate:.1f}%", inline=True)
        
        # Add current energon if available
        current_energon = stats.get('current_energon', 0)
        if current_energon > 0:
            embed.add_field(name="⚡ Current Game Energon", value=current_energon, inline=True)
        
        return embed
    
    async def create_pet_embed(self):
        """Create the pet stats embed"""
        player_id = str(self.target_member.id)
        pet = getattr(self.interaction.client, 'pet_system', None)
        
        if not pet:
            embed = discord.Embed(
                title="🤖 Pet System Unavailable",
                description="Pet system is not loaded.",
                color=discord.Color.red()
            )
            return embed
        
        pet_data = pet.get_user_pet(self.target_member.id)
        
        if not pet_data:
            embed = discord.Embed(
                title=f"🤖 {self.target_member.display_name}'s Pet",
                description="No pet found! Use `/get_pet autobot` or `/get_pet decepticon` to get one.",
                color=discord.Color.orange()
            )
            return embed
        
        # Import required modules from pets_system
        try:
            from Systems.EnergonPets.pets_system import PET_STAGES, LEVEL_THRESHOLDS, get_stage_emoji
            stage = PET_STAGES[pet_data["level"]]
            
            # Set faction-based color
            faction = pet_data.get('faction', 'Unknown').lower()
            if faction == 'autobot':
                embed_color = 0xCC0000  # Red for Autobots
            elif faction == 'decepticon':
                embed_color = 0x800080  # Purple for Decepticons
            else:
                embed_color = 0x808080  # Gray for Unknown
                
            # Get faction-based emoji
            faction_emoji = "🔴" if faction == 'autobot' else "🟣" if faction == 'decepticon' else "⚡"
            
            # Get stage emoji
            try:
                stage_emoji = get_stage_emoji(pet_data['level'])
            except:
                stage_emoji = "🥚"
                
            embed = discord.Embed(
                title=f"{stage_emoji} {pet_data['name']} - {pet_data.get('faction', 'Unknown')}",
                color=embed_color
            )
            
            # Always show full date and time
            created = datetime.fromisoformat(pet_data["created_at"])
            age_text = created.strftime("%B %d, %Y at %I:%M %p")
            
            embed.add_field(name="🧬 Stage", value=f"{stage_emoji} {pet_data['level']} - {stage['name']}", inline=True)
            embed.add_field(name="🗓️ Created", value=age_text, inline=True)
            
            max_level = max(LEVEL_THRESHOLDS.keys())
            if pet_data['level'] < max_level:
                threshold = LEVEL_THRESHOLDS[pet_data['level']]
                progress = min(pet_data['experience'] / threshold, 1.0)
                bar_length = 10
                filled_length = int(bar_length * progress)
                
                # Determine faction color for progress bar
                filled_char = "🟥" if faction == 'autobot' else "🟪" if faction == 'decepticon' else "🟨"
                empty_char = "⬛"
                bar = filled_char * filled_length + empty_char * (bar_length - filled_length)
                embed.add_field(name="📊 Level Progress", value=f"{bar} {pet_data['experience']}/{threshold} XP", inline=False)
            
            # Get detailed stats like PetStatusView
            detailed_stats = self.get_pet_detailed_stats(player_id)
            
            embed.add_field(name="🔋 **Energy**", value=f"{pet_data['energy']:.0f}/{pet_data['max_energy']:.0f}", inline=True)
            embed.add_field(name="🔧 **Maintenance**", value=f"{pet_data['maintenance']:.0f}/{pet_data['max_maintenance']:.0f}", inline=True)
            embed.add_field(name="😊 **Happiness**", value=f"{pet_data['happiness']:.0f}/{pet_data['max_happiness']:.0f}", inline=True)
            embed.add_field(name="⚡ **Power**", value=f"⚔️ Attack: {pet_data['attack']} | 🛡️ Defense: {pet_data['defense']}", inline=False)
            
            embed.add_field(
                name="🏆 **Achievements**", 
                value=f"⚔️ **__Total Battle Wins__**: {detailed_stats['battles']['total']['wins']}\n"
                      f"💀 **__Total Battle Losses__**: {detailed_stats['battles']['total']['losses']}\n"
                      f"📋 **__Missions Completed__**: {pet_data.get('missions_completed', 0)}\n"
                      f"💰 **__Total Energon__**: {detailed_stats['energon']['total']:,}\n"
                      f"⭐ **__Total Experience__**: {detailed_stats['experience']['total']:,}", 
                inline=False
            )
            
            embed.set_footer(text="Use the buttons below for detailed stats or refresh")
            
        except (ImportError, KeyError):
            # Fallback if pets_system modules are not available
            embed = discord.Embed(
                title=f"🤖 {pet_data['name']} - {pet_data.get('faction', 'Unknown')}",
                description=f"**{self.target_member.display_name}'s Digital Pet**",
                color=discord.Color.blue() if pet_data.get('faction') == 'Autobot' else discord.Color.red()
            )
            
            # Always show full date and time
            created = datetime.fromisoformat(pet_data["created_at"])
            age_text = created.strftime("%B %d, %Y at %I:%M %p")
            
            embed.add_field(name="🧬 Stage", value=f"Level {pet_data['level']}", inline=True)
            embed.add_field(name="🗓️ Obtained", value=age_text, inline=True)
            
            embed.add_field(name="⚡ Energy", value=f"{pet_data['energy']}/100", inline=True)
            embed.add_field(name="😊 Happiness", value=f"{pet_data['happiness']}/100", inline=True)
            
        return embed
    
    def get_pet_detailed_stats(self, user_id: str) -> dict:
        """Get detailed pet statistics like PetStatusView does"""
        try:
            # Use bot's UserDataManager for consistent data access
            # Return placeholder since this is called from sync context
            return {
                'pet': {},
                'battles': {'total': {'wins': 0, 'losses': 0}},
                'energon': {'total': 0},
                'experience': {'total': 0, 'mission': 0, 'battle': 0, 'challenge': 0, 'search': 0, 'training': 0, 'charge': 0, 'play': 0, 'repair': 0}
            }
        except Exception as e:
            logger.error(f"Error getting pet detailed stats: {e}")
            return {
                'pet': {},
                'battles': {'total': {'wins': 0, 'losses': 0}},
                'energon': {'total': 0},
                'experience': {'total': 0, 'mission': 0, 'battle': 0, 'challenge': 0, 'search': 0, 'training': 0, 'charge': 0, 'play': 0, 'repair': 0}
            }
    
    async def create_combiner_embed(self):
        """Create the detailed combiner embed"""
        player_id = str(self.target_member.id)
        
        # Use cached data
        theme_data = await self._get_user_data()
        combiner_teams = theme_data.get("combiner_teams", {})
        
        user_team_data = None
        user_part = None
        team_message_id = None
        
        # Find user's team in cached data
        for message_id, team_data in combiner_teams.items():
            for part, members in team_data.items():
                if player_id in members:
                    user_team_data = team_data
                    user_part = part
                    team_message_id = message_id
                    break
            if user_team_data:
                break
        
        if not user_team_data:
            embed = discord.Embed(
                title=f"🔗 {self.target_member.display_name}'s Combiner Status",
                description="Not currently part of any combiner team.\n\nUse `/combiner` to start or join a combiner team!",
                color=discord.Color.orange()
            )
            return embed
        
        part_names = {"🦿": "Leg", "🦾": "Arm", "🧠": "Head", "🫀": "Body"}
        part_name = part_names.get(user_part, "Unknown")
        
        # Get combiner name and formation date
        theme_data = await self.data_manager.get_theme_system_data(str(self.target_member.id))
        combiner_names = theme_data.get("combiner_names", {})
        combiner_data = combiner_names.get(str(team_message_id), {})
        if isinstance(combiner_data, dict):
            combiner_name = combiner_data.get('name', 'Unnamed Combiner')
            formation_timestamp = combiner_data.get('timestamp')
        else:
            combiner_name = combiner_data or 'Unnamed Combiner'
            formation_timestamp = None
        
        # Check if team is complete
        total_slots = sum(2 if part in ["🦿", "🦾"] else 1 for part in part_names.keys())
        filled_slots = sum(len(members) for members in user_team_data.values())
        is_complete = filled_slots == total_slots
        
        embed = discord.Embed(
            title=f"🔗 Combiner Team: {combiner_name}",
            description=f"**{self.target_member.display_name}'s Role:** {part_name}\n**Team Status:** {'✅ Complete' if is_complete else f'🔄 In Progress ({filled_slots}/{total_slots} slots filled)'}",
            color=discord.Color.green() if is_complete else discord.Color.yellow()
        )
        
        # Add detailed team composition
        for part_emoji, part_display in part_names.items():
            members_in_part = user_team_data.get(part_emoji, [])
            max_slots = 2 if part_emoji in ["🦿", "🦾"] else 1

            if members_in_part:
                member_list = []
                for i, m_id in enumerate(members_in_part):
                    try:
                        member_obj = self.ctx.guild.get_member(int(m_id))
                        if member_obj:
                            t_data = await self.data_manager.get_theme_system_data(str(m_id))
                            t_name = t_data.get("transformer_name", member_obj.display_name)
                            faction = t_data.get("transformer_faction", "Unknown")
                            t_class = t_data.get("transformer_class", "Unknown")
                                # Add position indicator for parts with multiple slots
                            if max_slots > 1:
                                if part_emoji == "🦾":  # Arms
                                    position = f" (Left)" if i == 0 else f" (Right)"
                                elif part_emoji == "🦿":  # Legs
                                    position = f" (Left)" if i == 0 else f" (Right)"
                                else:
                                    position = f" ({part_display} {i+1})"
                            else:
                                position = ""
                            member_list.append(f"**{t_name}**{position}\n{faction} {t_class}")

                            if max_slots > 1:
                                if part_emoji == "🦾":  # Arms
                                    position = f" (Left)" if i == 0 else f" (Right)"
                                elif part_emoji == "🦿":  # Legs
                                    position = f" (Left)" if i == 0 else f" (Right)"
                                else:
                                    position = f" ({part_display} {i+1})"
                            else:
                                position = ""
                            member_list.append(f"**{t_name}**{position}")
                    except Exception as e:
                        logger.error(f"Error processing member {m_id}: {e}")
                        continue
                
                value = "\n\n".join(member_list) if member_list else "*No members*"
                if len(members_in_part) < max_slots:
                    value += f"\n\n*{max_slots - len(members_in_part)} slot(s) available*"
            else:
                value = f"*{max_slots} slot(s) available*"
            
            embed.add_field(
                name=f"{part_emoji} {part_display} ({len(members_in_part)}/{max_slots})",
                value=value,
                inline=True
            )
        
        # Add team formation date if available
        if formation_timestamp and is_complete:
            formation_date = datetime.fromtimestamp(formation_timestamp)
            embed.add_field(
                name="📅 Team Formation",
                value=formation_date.strftime("%B %d, %Y at %I:%M %p"),
                inline=False
            )
        
        # Add instructions
        embed.add_field(
            name="ℹ️ How Combiners Work",
            value="• Teams need 6 members: 2 legs, 2 arms, 1 head, 1 body\n• Heads control the Combiner in Mega-Fights\n• Use `/combiner` to start a new team\n• Use `/mega_fight` to start Combiner Battle",
            inline=False
        )
        
        return embed
    
    async def create_coin_embed(self):
        """Create the CyberCoin portfolio embed"""
        player_id = str(self.target_member.id)
        
        # Try to get CyberCoin data from cached theme data
        try:
            theme_data = await self._get_user_data()
            coin_summary = theme_data.get("cybercoin", {})
            
            # Check if market system is available for fallback
            if not coin_summary and hasattr(self.interaction.client, 'market_manager') and self.interaction.client.market_manager:
                from Systems.EnergonPets.energon_system import MarketManager
                market_manager = self.interaction.client.market_manager
                coin_summary = market_manager.get_user_cybercoin_summary(player_id)
                
                embed = discord.Embed(
                    title=f"💰 {self.target_member.display_name}'s CyberCoin Portfolio",
                    description="Detailed CyberCoin investment and trading history",
                    color=discord.Color.gold()
                )
                
                # Current holdings
                current_coins = coin_summary.get('total_coins', 0)
                total_invested = coin_summary.get('total_invested', 0)
                total_sold = coin_summary.get('total_sold', 0)
                total_made = coin_summary.get('total_made', 0)
                unrealized_pnl = coin_summary.get('unrealized_pnl', 0)
                realized_profit = coin_summary.get('realized_profit', 0)
                most_coins_ever = coin_summary.get('most_coins_ever', 0)
                
                # Calculate total profit
                total_profit = realized_profit + unrealized_pnl
                
                # Add main portfolio fields
                embed.add_field(
                    name="🏦 Current Holdings",
                    value=f"**Current Coins:** {current_coins:,}\n**Most Coins Ever:** {most_coins_ever:,}",
                    inline=True
                )
                
                embed.add_field(
                    name="💵 Investment Summary",
                    value=f"**Amount Invested:** {total_invested:,} Energon\n**Amount Made:** {total_made:,} Energon",
                    inline=True
                )
                
                embed.add_field(
                    name="📊 Profit Analysis",
                    value=f"**Realized Profit:** {realized_profit:,}\n**Unrealized P&L:** {unrealized_pnl:,}\n**Total Profit:** {total_profit:,}",
                    inline=True
                )
                
                # Add transaction history if available
                recent_transactions = coin_summary.get('recent_transactions', [])
                if recent_transactions:
                    recent_text = ""
                    for tx in recent_transactions[:5]:  # Show last 5 transactions
                        tx_type = "📈 Buy" if tx['type'] == 'buy' else "📉 Sell"
                        recent_text += f"{tx_type}: {tx['coins']} coins @ {tx['price']} Energon\n"
                    
                    embed.add_field(
                        name="🔄 Recent Transactions",
                        value=recent_text,
                        inline=False
                    )
                
                # Add ROI calculation
                if total_invested > 0:
                    roi = (total_profit / total_invested) * 100
                    roi_emoji = "📈" if roi > 0 else "📉" if roi < 0 else "➡️"
                    embed.add_field(
                        name="🎯 Overall ROI",
                        value=f"{roi_emoji} {roi:.2f}%",
                        inline=True
                    )
                
                embed.set_footer(text="Use /market to access the CyberCoin trading platform")
                
            else:
                # Fallback if market system is not available
                embed = discord.Embed(
                    title=f"💰 {self.target_member.display_name}'s CyberCoin Portfolio",
                    description="CyberCoin system is not available.",
                    color=discord.Color.red()
                )
                
        except Exception as e:
            logger.error(f"Error creating coin embed: {e}")
            embed = discord.Embed(
                title=f"💰 {self.target_member.display_name}'s CyberCoin Portfolio",
                description="Error loading CyberCoin data",
                color=discord.Color.red()
            )
            return embed

    @discord.ui.button(label="Me", style=discord.ButtonStyle.primary, emoji="📊", disabled=True)
    async def me_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show personal stats"""
        if interaction.user.id != self.target_member.id:
            await interaction.response.send_message("You can only use your own profile buttons!", ephemeral=True)
            return
            
        self.current_view = "me"
        await self._update_buttons()
        embed = await self.create_me_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Pet", style=discord.ButtonStyle.secondary, emoji="🤖")
    async def pet_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show pet stats"""
        if interaction.user.id != self.target_member.id:
            await interaction.response.send_message("You can only use your own profile buttons!", ephemeral=True)
            return
            
        self.current_view = "pet"
        await self._update_buttons()
        embed = await self.create_pet_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Combiner", style=discord.ButtonStyle.secondary, emoji="🔗")
    async def combiner_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show combiner team status"""
        if interaction.user.id != self.target_member.id:
            await interaction.response.send_message("You can only use your own profile buttons!", ephemeral=True)
            return
            
        self.current_view = "combiner"
        await self._update_buttons()
        embed = await self.create_combiner_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="CyberCoin", style=discord.ButtonStyle.secondary, emoji="💰")
    async def coin_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show CyberCoin portfolio"""
        if interaction.user.id != self.target_member.id:
            await interaction.response.send_message("You can only use your own profile buttons!", ephemeral=True)
            return
            
        self.current_view = "coin"
        await self._update_buttons()
        embed = await self.create_coin_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.success, emoji="🔄")
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Refresh current view"""
        if interaction.user.id != self.target_member.id:
            await interaction.response.send_message("You can only use your own profile buttons!", ephemeral=True)
            return
            
        # Clear cache and reload
        self._cached_data = {}
        self._data_loaded = False
        
        if self.current_view == "me":
            embed = await self.create_me_embed()
        elif self.current_view == "pet":
            embed = await self.create_pet_embed()
        elif self.current_view == "combiner":
            embed = await self.create_combiner_embed()
        elif self.current_view == "coin":
            embed = await self.create_coin_embed()
        else:
            embed = await self.create_me_embed()
            
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def _update_buttons(self):
        """Update button states based on current view"""
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.label == "Me":
                    child.disabled = (self.current_view == "me")
                elif child.label == "Pet":
                    child.disabled = (self.current_view == "pet")
                elif child.label == "Combiner":
                    child.disabled = (self.current_view == "combiner")
                elif child.label == "CyberCoin":
                    child.disabled = (self.current_view == "coin")
                elif child.label == "Refresh":
                    child.disabled = False


class ProfileCog(commands.Cog):
    """Cog for user profile management"""
    
    def __init__(self, bot):
        self.bot = bot
        logger.info("ProfileCog initialized")
    
    @discord.app_commands.command(name="profile", description="View your comprehensive transformer profile")
    @discord.app_commands.guild_only()
    async def profile(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        """Display a comprehensive transformer profile with interactive navigation."""
        try:
            target_member = member or interaction.user
            
            # Check if target has transformer identity
            user_id = str(target_member.id)
            theme_data = await self.bot.user_data_manager.get_user_theme_data(user_id, target_member.display_name)
            transformer_name = theme_data.get("transformer_name")
            transformer_data = {"name": transformer_name} if transformer_name else {}
            
            if not transformer_data and target_member == interaction.user:
                await interaction.response.send_message("❌ You haven't been assigned a transformer identity yet! Use `/spark` to get started.", ephemeral=True)
                return
            elif not transformer_data:
                await interaction.response.send_message(f"❌ {target_member.display_name} hasn't been assigned a transformer identity yet.", ephemeral=True)
                return
            
            # Create and send the interactive profile view
            view = ProfileView(target_member, interaction)
            embed = await view.create_me_embed()
            await interaction.response.send_message(embed=embed, view=view)
            
        except Exception as e:
            logger.exception(f"Error displaying profile: {e}")
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info("ProfileCog is ready")


async def setup(bot):
    """Setup function for loading the cog"""
    await bot.add_cog(ProfileCog(bot))
    logger.info("ProfileCog loaded successfully")


# For backward compatibility - direct access to ProfileView
__all__ = ['ProfileCog', 'ProfileView', 'setup']