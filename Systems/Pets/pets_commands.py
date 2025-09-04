import discord
from discord.ext import commands
from discord import app_commands
import json
import sys
import os
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

from config import ROLE_IDS
from .pets_system import PetSystem, PET_STAGES, LEVEL_THRESHOLDS, UnifiedBattleView, UnifiedBattleActionView
from ..user_data_manager import user_data_manager

class PetCommands:
    """Discord command handlers for the pet system"""
    
    def __init__(self, bot, pet_system: PetSystem):
        self.bot = bot
        self.pet_system = pet_system
    
    def has_cybertronian_role(self, member: discord.Member) -> bool:
        """Check if a member has any Cybertronian role"""
        cybertronian_roles = [ROLE_IDS.get(role) for role in ['Autobot', 'Decepticon', 'Maverick', 'Cybertronian_Citizen']]
        return any(role.id in cybertronian_roles for role in member.roles)
    
    async def get_pet_command(self, ctx: commands.Context, faction: str) -> None:
        """Handle /get_pet command"""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can get pets! Please get a Cybertronian role first.")
            return
        
        if await self.pet_system.get_user_pet(ctx.author.id):
            await ctx.send("🤖 You already have a digital pet! Use `/pet` to check on them.")
            return
        
        if faction.lower() not in ['autobot', 'decepticon']:
            await ctx.send("❌ Please choose either 'autobot' or 'decepticon' as your faction!")
            return
        
        pet_data = await self.pet_system.create_pet(ctx.author.id, faction)
        stage = PET_STAGES[pet_data["level"]]
        
        # Get stage emoji for new pet
        try:
            stage_emoji = self.pet_system.get_stage_emoji(pet_data['level'])
        except:
            stage_emoji = "🥚"
        
        color = discord.Color.blue() if pet_data['faction'] == 'Autobot' else discord.Color.red()
        
        embed = discord.Embed(
            title=f"{stage_emoji} Welcome to the Digital Pet System!",
            description=f"You've received **{pet_data['name']}**, a {pet_data['faction']} {stage_emoji} {stage['name']}!",
            color=color
        )
        
        embed.add_field(name="⚡ Energy", value=f"{pet_data['energy']}/{pet_data['max_energy']}", inline=True)
        embed.add_field(name="😊 Happiness", value=f"{pet_data['happiness']}/{pet_data['max_happiness']}", inline=True)
        embed.add_field(name="🛠️ Maintenance", value=f"{pet_data['maintenance']}/{pet_data['max_maintenance']}", inline=True)
        embed.add_field(name="⚔️ Attack", value=f"{pet_data['attack']}", inline=True)
        embed.add_field(name="🛡️ Defense", value=f"{pet_data['defense']}", inline=True)
        embed.add_field(name="🧬 Stage", value=f"{stage_emoji} {stage['name']}", inline=True)
        embed.add_field(name="📖 Description", value=stage['description'], inline=False)
        embed.add_field(name="🎮 Commands", value="Use `/charge_pet`, `/play` & `/repair_pet` to raise pet levels.\n `/train` & `/mission` to gain Energon & XP.\n Use `/battle` (1v1) & `/group_battle` (4v1) to fight NPC enemies.\n Use `/challenge` (1v1) & `/open_challenge` (4way FFA) to fight other pets.\n Use `/pet` to see, `/rename_pet` to rename and `/kill` to kill pet!", inline=False)
        
        await ctx.send(embed=embed)
    
    async def pet_status_command(self, ctx: commands.Context) -> None:
        """Handle /pet command"""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can access the pet system! Please get a Cybertronian role first.")
            return
        
        pet = await self.pet_system.get_user_pet(ctx.author.id)
        if not pet:
            await ctx.send("🤖 You don't have a pet yet! Use `/get_pet autobot` or `/get_pet decepticon` to get one.")
            return

        # Migrate old pet data
        await self.pet_system.migrate_pet_data(pet)
        await user_data_manager.save_pet_data(str(ctx.author.id), str(ctx.author), pet)
        
        # Import PetStatusView from pets_system
        from .pets_system import PetStatusView
        
        # Create interactive view with buttons
        view = PetStatusView(ctx.author.id, self.pet_system, self)
        embed = await view.create_main_embed()
        
        message = await ctx.send(embed=embed, view=view)
        view.message = message
    
    async def charge_pet_command(self, ctx: commands.Context, duration: str = "15min") -> None:
        """Handle /charge_pet command with duration selection"""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can use pet commands!")
            return
        
        success, message, level_gains = await self.pet_system.charge_pet(ctx.author.id, duration)
        if success:
            await ctx.send(f"✅ {message}")
            if level_gains:
                asyncio.create_task(self.pet_system.send_level_up_embed(ctx.author.id, level_gains, ctx.channel))
        else:
            await ctx.send(f"❌ {message}")
    
    async def play_command(self, ctx: commands.Context, duration: str = "15min") -> None:
        """Handle /play command with duration selection"""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can use pet commands!")
            return
        
        success, message, level_gains = await self.pet_system.play_with_pet(ctx.author.id, duration)
        if success:
            await ctx.send(f"✅ {message}")
            if level_gains:
                asyncio.create_task(self.pet_system.send_level_up_embed(ctx.author.id, level_gains, ctx.channel))
        else:
            await ctx.send(f"❌ {message}")
    
    async def train_command(self, ctx: commands.Context, difficulty: str) -> None:
        """Handle /train command with difficulty selection"""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can use pet commands!")
            return
        
        success, message, level_gains = await self.pet_system.train_pet(ctx.author.id, difficulty)
        if success:
            await ctx.send(message)
            if level_gains:
                asyncio.create_task(self.pet_system.send_level_up_embed(ctx.author.id, level_gains, ctx.channel))
        else:
            await ctx.send(f"❌ {message}")
    
    async def repair_pet_command(self, ctx: commands.Context, duration: str = "15min") -> None:
        """Handle /repair_pet command with duration selection"""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can use pet commands!")
            return
        
        success, message, level_gains = await self.pet_system.repair_pet(ctx.author.id, duration)
        if success:
            await ctx.send(f"✅ {message}")
            if level_gains:
                asyncio.create_task(self.pet_system.send_level_up_embed(ctx.author.id, level_gains, ctx.channel))
        else:
            await ctx.send(f"❌ {message}")
    
    async def rename_pet_command(self, ctx: commands.Context, new_name: str) -> None:
        """Handle /rename_pet command"""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can rename pets!")
            return
        
        pet = await self.pet_system.get_user_pet(ctx.author.id)
        if not pet:
            await ctx.send("🤖 You don't have a pet yet! Use `/get_pet autobot` or `/get_pet decepticon` to get one.")
            return
        
        if len(new_name) > 20:
            await ctx.send("❌ Pet name must be 20 characters or less!")
            return
        
        if len(new_name.strip()) == 0:
            await ctx.send("❌ Pet name cannot be empty!")
            return
        
        old_name = pet["name"]
        pet["name"] = new_name.strip()
        await user_data_manager.save_pet_data(str(ctx.author.id), str(ctx.author), pet)
        
        stage = PET_STAGES[pet["level"]]
        await ctx.send(f"✅ Your {stage['name']} has been renamed from **{old_name}** to **{new_name}**!")
    
    async def kill_pet_command(self, ctx: commands.Context) -> None:
        """Handle /kill command with confirmation"""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can access the pet system!")
            return
        
        pet = await self.pet_system.get_user_pet(ctx.author.id)
        if not pet:
            await ctx.send("🤖 You don't have a pet to delete!")
            return
        
        # Create confirmation view
        class KillConfirmView(discord.ui.View):
            def __init__(self, pet_system_instance, ctx_instance):
                super().__init__(timeout=30.0)
                self.pet_system = pet_system_instance
                self.ctx = ctx_instance
                self.confirmed = False
            
            @discord.ui.button(label='❌ Cancel', style=discord.ButtonStyle.secondary)
            async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id != self.ctx.author.id:
                    await interaction.response.send_message("❌ Only the pet owner can use this button!", ephemeral=True)
                    return
                
                embed = discord.Embed(
                    title="✅ Pet Deletion Cancelled",
                    description=f"Your pet **{pet['name']}** is safe! {PET_STAGES[pet['level']]['emoji']}",
                    color=discord.Color.green()
                )
                await interaction.response.edit_message(embed=embed, view=None)
                self.stop()
            
            @discord.ui.button(label='💀 DELETE FOREVER', style=discord.ButtonStyle.danger)
            async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id != self.ctx.author.id:
                    await interaction.response.send_message("❌ Only the pet owner can use this button!", ephemeral=True)
                    return
                
                deleted_pet = await self.pet_system.delete_pet(self.ctx.author.id)
                
                if deleted_pet:
                    embed = discord.Embed(
                        title="💀 Pet Deleted Forever",
                        description=f"**{deleted_pet['name']}** has been permanently deleted from the digital realm.\n\nYou can get a new pet anytime with `/get_pet autobot` or `/get_pet decepticon`.",
                        color=discord.Color.dark_red()
                    )
                    await interaction.response.edit_message(embed=embed, view=None)
                else:
                    await interaction.response.send_message("❌ Error deleting pet. Please try again.", ephemeral=True)
                
                self.confirmed = True
                self.stop()
        
        # Create confirmation embed
        stage = PET_STAGES[pet["level"]]
        color = discord.Color.blue() if pet['faction'] == 'Autobot' else discord.Color.red()
        
        embed = discord.Embed(
            title="⚠️ PERMANENT PET DELETION WARNING",
            description=f"Are you sure you want to **permanently delete** your pet?\n\n**{pet['name']}** - {pet['faction']} {stage['name']}\nLevel {pet['level']} | ATT: {pet['attack']} | DEF: {pet['defense']}",
            color=discord.Color.red()
        )
        
        embed.add_field(name="⚠️ WARNING", value="This action is **IRREVERSIBLE**!\nAll progress, stats, and memories will be lost forever.", inline=False)
        embed.add_field(name="📊 Current Stats", value=f"Energy: {pet['energy']:.0f}/{pet['max_energy']:.0f}\nMaintenance: {pet['maintenance']:.0f}/{pet['max_maintenance']:.0f}\nHappiness: {pet['happiness']:.0f}/{pet['max_happiness']:.0f}", inline=True)
        embed.add_field(name="🏆 Achievements", value=f"Missions: {pet.get('missions_completed', 0)}\nBattles Won: {pet.get('battles_won', 0)}\nBattles Lost: {pet.get('battles_lost', 0)}", inline=True)
        
        view = KillConfirmView(self.pet_system, ctx)
        await ctx.send(embed=embed, view=view)

    async def mission_command(self, ctx: commands.Context, difficulty: str) -> None:
        """Handle /mission command"""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can use pet commands!")
            return
        
        success, message = await self.pet_system.send_mission(ctx.author.id, difficulty)
        if success:
            await ctx.send(message)
        else:
            await ctx.send(f"❌ {message}")

class PetCommandsCog(commands.Cog):
    """Cog for pet-related commands"""
    
    def __init__(self, bot: commands.Bot, pet_system: PetSystem, pet_commands: PetCommands):
        self.bot = bot
        self.pet_system = pet_system
        self.pet_commands = pet_commands
    
    @commands.hybrid_command(name='get_pet', description='Get your first digital pet')
    @app_commands.describe(faction="Choose your pet's faction")
    @app_commands.choices(faction=[
        app_commands.Choice(name="🔵 Autobot", value="autobot"),
        app_commands.Choice(name="🔴 Decepticon", value="decepticon")
    ])
    @app_commands.checks.has_role(ROLE_IDS.get('Cybertronian_Citizen'))
    async def get_pet(self, ctx: commands.Context, faction: str):
        await self.pet_commands.get_pet_command(ctx, faction)
    
    @commands.hybrid_command(name='pet', description='View your digital pet\'s status')
    async def pet_status(self, ctx: commands.Context):
        await self.pet_commands.pet_status_command(ctx)
    
    @commands.hybrid_command(name='charge_pet', description='Charge your pet\'s energy with duration options')
    @app_commands.describe(duration="How long to charge your pet")
    @app_commands.choices(duration=[
        app_commands.Choice(name="🪫 15 minutes", value="15min"),
        app_commands.Choice(name="🔋 30 minutes", value="30min"),
        app_commands.Choice(name="🏭 1 hour", value="1hour")
    ])
    async def charge_pet(self, ctx: commands.Context, duration: str):
        await self.pet_commands.charge_pet_command(ctx, duration)
    
    @commands.hybrid_command(name='play', description='Play with your pet to increase happiness with duration options')
    @app_commands.describe(duration="How long to play with your pet")
    @app_commands.choices(duration=[
        app_commands.Choice(name="🎮 15 minutes", value="15min"),
        app_commands.Choice(name="🃏 30 minutes", value="30min"),
        app_commands.Choice(name="🎳 1 hour", value="1hour")
    ])
    async def play(self, ctx: commands.Context, duration: str):
        await self.pet_commands.play_command(ctx, duration)
    
    @commands.hybrid_command(name='train', description='Train your pet with different intensity levels')
    @app_commands.describe(difficulty="Choose training intensity")
    @app_commands.choices(difficulty=[
        app_commands.Choice(name="⚡ Average", value="average"),
        app_commands.Choice(name="🔥 Intense", value="intense"),
        app_commands.Choice(name="💀 Godmode", value="godmode")
    ])
    async def train(self, ctx: commands.Context, difficulty: str):
        await self.pet_commands.train_command(ctx, difficulty)
    
    @commands.hybrid_command(name='repair_pet', description='Repair your pet\'s maintenance with duration options')
    @app_commands.describe(duration="How long to repair your pet")
    @app_commands.choices(duration=[
        app_commands.Choice(name="⚙️ 15 minutes", value="15min"),
        app_commands.Choice(name="🔨 30 minutes", value="30min"),
        app_commands.Choice(name="🛠️ 1 hour", value="1hour")
    ])
    async def repair_pet(self, ctx: commands.Context, duration: str):
        await self.pet_commands.repair_pet_command(ctx, duration)
    
    @commands.hybrid_command(name='rename_pet', description='Rename your digital pet')
    async def rename_pet(self, ctx: commands.Context, *, new_name: str):
        await self.pet_commands.rename_pet_command(ctx, new_name)
    
    @commands.hybrid_command(name='kill', description='Permanently delete your digital pet')
    async def kill_pet(self, ctx: commands.Context):
        await self.pet_commands.kill_pet_command(ctx)
    
    @commands.hybrid_command(name='mission', description='Send your pet on a mission to earn experience and energon')
    @app_commands.describe(difficulty="Choose mission difficulty")
    @app_commands.choices(difficulty=[
        app_commands.Choice(name="🟢 Easy", value="easy"),
        app_commands.Choice(name="🟡 Average", value="average"),
        app_commands.Choice(name="🔴 Hard", value="hard")
    ])
    async def mission(self, ctx: commands.Context, difficulty: str):
        await self.pet_commands.mission_command(ctx, difficulty)

class BattleCommandsCog(commands.Cog):
    """Cog for battle-related commands"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    def load_challenges_from_game_state(self, channel_id=None):
        """Load challenge data from game_state.json"""
        try:
            from Systems.Energon.energon_system import EnergonGameManager
            game_manager = EnergonGameManager()
            game_manager.load_game_state()
            
            if channel_id:
                return game_manager.challenges.get(str(channel_id), [])
            else:
                # Return all challenges across all channels
                all_challenges = []
                for channel_challenges in game_manager.challenges.values():
                    all_challenges.extend(channel_challenges)
                return all_challenges
                
        except Exception as e:
            print(f"Error loading challenges from game state: {e}")
            return []
    
    @commands.hybrid_command(name='battle', description='Start a battle with a random enemy')
    @app_commands.describe(enemy_type="Choose the type of enemy to battle", enemy_rarity="Choose the rarity of the enemy")
    @app_commands.choices(enemy_type=[
        app_commands.Choice(name="🤖 Monster", value="monster"),
        app_commands.Choice(name="👹 Boss", value="boss"),
        app_commands.Choice(name="👑 Titan", value="titan")
    ])
    @app_commands.choices(enemy_rarity=[
        app_commands.Choice(name="⚪ Common", value="common"),
        app_commands.Choice(name="🟢 Uncommon", value="uncommon"),
        app_commands.Choice(name="🔵 Rare", value="rare"),
        app_commands.Choice(name="🟣 Epic", value="epic"),
        app_commands.Choice(name="🟠 Legendary", value="legendary"),
        app_commands.Choice(name="🔴 Mythic", value="mythic")
    ])
    async def battle(self, ctx: commands.Context, enemy_type: str, enemy_rarity: str):
        """Start a battle with a random enemy"""
        if not has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can battle! Please get the 'Cybertronian Citizen' role first.")
            return
            
        # Get user's pet
        user_pet = await user_data_manager.get_pet_data(str(ctx.author.id), ctx.author.display_name)
        if not user_pet or not user_pet.get('name'):
            await ctx.send("❌ You don't have a pet! Use `/get_pet` to get one.")
            return
            
        # Check energy
        if user_pet.get('energy', 0) < 10:
            await ctx.send(f"❌ Your pet doesn't have enough energy! (Needs 10, has {user_pet.get('energy', 0)})")
            return
            
        # Create battle with selected parameters
        participants = [(ctx.author, user_pet)]
        
        # Create monster based on selections
        monster = None
        try:
            if not self.bot.pet_system.monsters_data:
                self.bot.pet_system.load_cyberchronicles_monsters()
            
            # Get appropriate enemy collection
            if enemy_type == "monster":
                enemies = self.bot.pet_system.monsters_data
            elif enemy_type == "boss":
                enemies = self.bot.pet_system.bosses_data
            elif enemy_type == "titan":
                enemies = self.bot.pet_system.titans_data
            else:
                enemies = self.bot.pet_system.monsters_data
            
            # Get monsters by rarity
            matching_enemies = enemies.get(enemy_rarity, [])
            
            if matching_enemies:
                monster = random.choice(matching_enemies)
                if "attack" in monster:
                    attack_value = monster["attack"]
                    monster["attack_min"] = attack_value
                    monster["attack_max"] = int(attack_value * 1.2)
                else:
                    monster["attack_min"] = monster.get("attack_min", 10)
                    monster["attack_max"] = monster.get("attack_max", 15)
                
                monster["health"] = monster.get("health", 50)
                monster["type"] = enemy_type
                monster["rarity"] = enemy_rarity
            else:
                # Fallback monster
                monster = {
                    "name": f"{enemy_rarity.title()} {enemy_type.title()}",
                    "health": 50,
                    "attack_min": 10,
                    "attack_max": 15,
                    "type": enemy_type,
                    "rarity": enemy_rarity
                }
                
        except Exception as e:
            print(f"Error loading monsters: {e}")
            # Create fallback monster
            monster = {
                "name": f"{enemy_rarity.title()} {enemy_type.title()}",
                "health": 50,
                "attack_min": 10,
                "attack_max": 15,
                "type": enemy_type,
                "rarity": enemy_rarity
            }
        
        # Start the battle
        view = await UnifiedBattleView.create_async(ctx, self.bot.pet_system, "solo", participants, monster, enemy_rarity)
        view.battle_started = True
        action_view = UnifiedBattleActionView(view)
        embed = view.build_battle_embed()
        
        message = await ctx.send(embed=embed, view=action_view)
        view.message = message
    
    @commands.hybrid_command(name='pet_battle_info', description='Show battle information and stats')
    async def pet_battle_info(self, ctx: commands.Context):
        """Show battle information and stats"""
        if not has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can battle! Please get the 'Cybertronian Citizen' role first.")
            return
            
        user_pet = await user_data_manager.get_pet_data(str(ctx.author.id), ctx.author.display_name)
        if not user_pet or not user_pet.get('name'):
            await ctx.send("❌ You don't have a pet! Use `/get_pet` to get one.")
            return
            
        embed = discord.Embed(
            title="⚔️ Battle Information",
            description=f"Battle stats for **{user_pet['name']}**",
            color=0x0099ff
        )
        
        # Battle stats
        battles_won = user_pet.get('battles_won', 0)
        battles_lost = user_pet.get('battles_lost', 0)
        total_battles = battles_won + battles_lost
        win_rate = (battles_won / total_battles * 100) if total_battles > 0 else 0
        
        embed.add_field(
            name="📊 Battle Stats",
            value=f"Total Battles: {total_battles}\n"
                  f"Won: {battles_won}\n"
                  f"Lost: {battles_lost}\n"
                  f"Win Rate: {win_rate:.1f}%",
            inline=True
        )
        
        embed.add_field(
            name="💪 Combat Stats",
            value=f"Attack: {user_pet.get('attack', 0)}\n"
                  f"Defense: {user_pet.get('defense', 0)}\n"
                  f"Energy: {user_pet.get('energy', 0)}/{user_pet.get('max_energy', 100)}",
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='challenge', description='Challenge another player to a battle')
    @app_commands.describe(opponent="The player you want to challenge")
    async def challenge(self, ctx: commands.Context, opponent: discord.Member):
        """Challenge another player to a battle"""
        if not has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can battle! Please get the 'Cybertronian Citizen' role first.")
            return
            
        if not has_cybertronian_role(opponent):
            await ctx.send("❌ Your opponent must be a Cybertronian Citizen to battle!")
            return
            
        # Check challenger pet
        challenger_pet = await user_data_manager.get_pet_data(str(ctx.author.id), ctx.author.display_name)
        if not challenger_pet or not challenger_pet.get('name'):
            await ctx.send("❌ You don't have a pet! Use `/get_pet` to get one.")
            return
            
        # Check opponent pet
        opponent_pet = await user_data_manager.get_pet_data(str(opponent.id), opponent.display_name)
        if not opponent_pet or not opponent_pet.get('name'):
            await ctx.send(f"❌ {opponent.display_name} doesn't have a pet!")
            return
            
        # Check energy
        if challenger_pet.get('energy', 0) < 10:
            await ctx.send(f"❌ Your pet doesn't have enough energy! (Needs 10, has {challenger_pet.get('energy', 0)})")
            return
            
        if opponent_pet.get('energy', 0) < 10:
            await ctx.send(f"❌ {opponent.display_name}'s pet doesn't have enough energy!")
            return
            
        # Create PvP battle
        try:
            battle_view = await UnifiedBattleView.create_async(
                ctx, 
                self.bot.pet_system, 
                "pvp", 
                participants=[(ctx.author, challenger_pet), (opponent, opponent_pet)],
                target_user=opponent
            )
            battle_view.battle_started = True
            action_view = UnifiedBattleActionView(battle_view)
            
            embed = battle_view.build_battle_embed()
            await ctx.send(embed=embed, view=action_view)
        except Exception as e:
            print(f"Error creating PvP battle: {e}")
            await ctx.send("❌ Battle system is not available right now.")
    
    @commands.hybrid_command(name='open_challenge', description='Create an open challenge for anyone to accept')
    async def open_challenge(self, ctx: commands.Context):
        """Create an open challenge for anyone to accept"""
        if not has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can battle! Please get the 'Cybertronian Citizen' role first.")
            return
            
        user_pet = await user_data_manager.get_pet_data(str(ctx.author.id), ctx.author.display_name)
        if not user_pet or not user_pet.get('name'):
            await ctx.send("❌ You don't have a pet! Use `/get_pet` to get one.")
            return
            
        if user_pet.get('energy', 0) < 10:
            await ctx.send(f"❌ Your pet doesn't have enough energy! (Needs 10, has {user_pet.get('energy', 0)})")
            return
            
        # Create open challenge
        try:
            from Systems.Energon.energon_system import EnergonGameManager
            game_manager = EnergonGameManager()
            success = game_manager.create_open_challenge(ctx.channel.id, str(ctx.author.id))
            if success:
                embed = discord.Embed(
                    title="⚔️ Open Challenge",
                    description=f"{ctx.author.mention} has created an open challenge!",
                    color=0x0099ff
                )
                embed.add_field(name="🐾 Challenger", value=f"**{user_pet['name']}** - {ctx.author.display_name}", inline=False)
                embed.set_footer(text="Anyone can accept this challenge with /accept_open_challenge")
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Failed to create open challenge. Please try again.")
        except Exception as e:
            print(f"Error creating open challenge: {e}")
            await ctx.send("❌ Battle system is not available right now.")
    
    @commands.hybrid_command(name='group_battle', description='Start a group battle with up to 4 players')
    @app_commands.describe(enemy_type="Choose the type of enemy to battle", enemy_rarity="Choose the rarity of the enemy")
    @app_commands.choices(enemy_type=[
        app_commands.Choice(name="🤖 Monster", value="monster"),
        app_commands.Choice(name="👹 Boss", value="boss"),
        app_commands.Choice(name="👑 Titan", value="titan")
    ])
    @app_commands.choices(enemy_rarity=[
        app_commands.Choice(name="⚪ Common", value="common"),
        app_commands.Choice(name="🟢 Uncommon", value="uncommon"),
        app_commands.Choice(name="🔵 Rare", value="rare"),
        app_commands.Choice(name="🟣 Epic", value="epic"),
        app_commands.Choice(name="🟠 Legendary", value="legendary"),
        app_commands.Choice(name="🔴 Mythic", value="mythic")
    ])
    async def group_battle(self, ctx: commands.Context, enemy_type: str, enemy_rarity: str):
        """Start a group battle with up to 4 players"""
        if not has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can battle! Please get the 'Cybertronian Citizen' role first.")
            return
            
        # Get initiator's pet
        initiator_pet = await user_data_manager.get_pet_data(str(ctx.author.id), ctx.author.display_name)
        if not initiator_pet or not initiator_pet.get('name'):
            await ctx.send("❌ You don't have a pet! Use `/get_pet` to get one.")
            return
            
        # Check energy
        if initiator_pet.get('energy', 0) < 10:
            await ctx.send(f"❌ Your pet doesn't have enough energy! (Needs 10, has {initiator_pet.get('energy', 0)})")
            return
            
        # Create group battle directly with provided enemy type and rarity
        participants = [(ctx.author, initiator_pet)]
        
        # Create monster based on provided type and rarity
        monster = self.bot.pet_system.create_enemy_monster(enemy_type, enemy_rarity)
        
        # Start battle directly without voting
        battle_view = await UnifiedBattleView.create_async(
            ctx, 
            self.bot.pet_system, 
            "group", 
            participants, 
            monster, 
            enemy_rarity
        )
        embed = battle_view.build_join_embed()
        await ctx.send(embed=embed, view=battle_view)

# Helper function for role checking
def has_cybertronian_role(member):
    """Check if member has Cybertronian role"""
    cybertronian_roles = [discord.utils.get(member.roles, name=role) for role in ['Autobot', 'Decepticon', 'Maverick', 'Cybertronian_Citizen']]
    return any(role in member.roles for role in cybertronian_roles if role)

# Setup functions for the commands
async def setup_pet_commands(bot: commands.Bot) -> None:
    """
    Setup all pet-related commands for the bot
    
    This function:
    1. Creates PetCommands instance
    2. Registers all hybrid commands via cog
    """
    pet_commands = PetCommands(bot, bot.pet_system)
    
    # Add pet commands cog
    await bot.add_cog(PetCommandsCog(bot, bot.pet_system, pet_commands))
    
    # Store instance for external access
    bot.pet_commands = pet_commands

async def setup_battle_commands(bot: commands.Bot) -> None:
    """Setup function to initialize battle commands"""
    await bot.add_cog(BattleCommandsCog(bot))

# Enhanced setup function for complete pet commands
async def setup(bot_instance):
    """Async setup function for complete pet system commands"""
    # Use the existing pet system from pets_system.py - don't create a new one
    if not hasattr(bot_instance, 'pet_system'):
        logger.error("Pet system not found! Make sure pets_system.py is loaded first.")
        return
    
    await setup_pet_commands(bot_instance)
    await setup_battle_commands(bot_instance)
    print("Pet system commands loaded successfully")