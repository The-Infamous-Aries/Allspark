import discord
from discord.ext import commands
from discord import app_commands
import sys
import os
import logging
import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

from config import ROLE_IDS
from .pets_system import PetSystem, PET_STAGES, LEVEL_THRESHOLDS
from ..user_data_manager import user_data_manager

# Configure logging
logger = logging.getLogger(__name__)

class PetCommands:
    """Discord command handlers for the pet system"""
    
    def __init__(self, bot, pet_system: PetSystem):
        self.bot = bot
        self.pet_system = pet_system
    
    def has_cybertronian_role(self, member: discord.Member) -> bool:
        """Check if a member has any Cybertronian role"""
        if not member or not member.roles:
            return False
            
        cybertronian_role_ids = [ROLE_IDS.get(role) for role in ['Autobot', 'Decepticon', 'Maverick', 'Cybertronian_Citizen']]
        return any(role.id in cybertronian_role_ids for role in member.roles if role.id in cybertronian_role_ids)
    
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
        
        # Create interactive view with buttons - pass the already-loaded pet data
        view = PetStatusView(ctx.author.id, self.pet_system, self, pet_data=pet)
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
        # Get total max stats including equipment bonuses
        equipment_stats = await self.pet_system.get_equipment_stats(ctx.author.id)
        total_max_energy = pet['max_energy'] + equipment_stats.get('energy', 0)
        total_max_maintenance = pet['max_maintenance'] + equipment_stats.get('maintenance', 0)
        total_max_happiness = pet['max_happiness'] + equipment_stats.get('happiness', 0)
        
        embed.add_field(name="📊 Current Stats", value=f"Energy: {pet['energy']:.0f}/{total_max_energy:.0f}\nMaintenance: {pet['maintenance']:.0f}/{total_max_maintenance:.0f}\nHappiness: {pet['happiness']:.0f}/{total_max_happiness:.0f}", inline=True)
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

    async def pet_equip_command(self, ctx: commands.Context, slot: str = None, item_name: str = None) -> None:
        """Handle /pet_equip command"""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can use pet commands!")
            return
        
        pet = await self.pet_system.get_user_pet(ctx.author.id)
        if not pet:
            await ctx.send("🤖 You don't have a pet yet! Use `/get_pet autobot` or `/get_pet decepticon` to get one.")
            return

        # If no slot provided, show current equipment
        if not slot:
            details = await self.pet_system.get_equipment_details(ctx.author.id)
            if not details:
                await ctx.send("❌ Error retrieving equipment details!")
                return

            embed = discord.Embed(
                title=f"🛡️ {pet['name']}'s Equipment",
                description="Manage your pet's equipment and view current loadout",
                color=discord.Color.blue() if pet['faction'] == 'Autobot' else discord.Color.red()
            )

            # Show equipped items
            equipment = details["equipment"]
            for slot_name, item in equipment.items():
                slot_display = slot_name.replace('_', ' ').title()
                if item:
                    stat_bonus = item.get("stat_bonus", {})
                    stats_text = ""
                    for stat, value in stat_bonus.items():
                        stats_text += f" +{value} {stat}"
                    embed.add_field(
                        name=f"🎯 {slot_display}",
                        value=f"**{item['name']}**{stats_text}",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name=f"🎯 {slot_display}",
                        value="*Empty*",
                        inline=False
                    )

            # Show total bonus stats
            total_stats = details["total_stats"]
            embed.add_field(
                name="📊 Total Equipment Bonus",
                value=f"⚔️ Attack: +{total_stats['attack']}\n🛡️ Defense: +{total_stats['defense']}",
                inline=False
            )

            # Show available items in inventory
            inventory = details["inventory"]
            if inventory:
                item_list = []
                for item in inventory:
                    item_list.append(f"• **{item['name']}** ({item['type'].replace('_', ' ').title()})")
                embed.add_field(
                    name="🎒 Inventory",
                    value="\n".join(item_list[:5]) + ("\n..." if len(item_list) > 5 else ""),
                    inline=False
                )
            else:
                embed.add_field(name="🎒 Inventory", value="*No items in inventory*", inline=False)

            embed.set_footer(text="Use /pet_equip <slot> <item> to equip items")
            await ctx.send(embed=embed)
            return

        # Validate slot
        valid_slots = ["chassis_plating", "energy_cores", "utility_modules"]
        if slot not in valid_slots:
            await ctx.send(f"❌ Invalid slot! Valid slots: {', '.join(valid_slots)}")
            return

        # If no item provided, show available items for this slot
        if not item_name:
            equippable = await self.pet_system.get_equippable_items(ctx.author.id, slot)
            if not equippable:
                await ctx.send(f"❌ No items available for {slot.replace('_', ' ').title()} in your inventory!")
                return

            embed = discord.Embed(
                title=f"🎒 Available {slot.replace('_', ' ').title()} Items",
                description=f"Choose an item to equip in the {slot.replace('_', ' ').title()} slot:",
                color=discord.Color.blue() if pet['faction'] == 'Autobot' else discord.Color.red()
            )

            for item in equippable:
                stat_bonus = item.get("stat_bonus", {})
                stats_text = ""
                for stat, value in stat_bonus.items():
                    stats_text += f" +{value} {stat}"
                embed.add_field(
                    name=f"**{item['name']}**",
                    value=f"Rarity: {item.get('rarity', 'Unknown')}{stats_text}",
                    inline=False
                )

            embed.set_footer(text=f"Use /pet_equip {slot} <item_name> to equip an item")
            await ctx.send(embed=embed)
            return

        # Try to equip the specified item
        success, message = await self.pet_system.equip_item(ctx.author.id, item_name)
        if success:
            await ctx.send(f"✅ {message}")
        else:
            await ctx.send(f"❌ {message}")

    async def pet_equipment_command(self, ctx: commands.Context) -> None:
        """Handle /pet_equipment command to display all pet items with pagination"""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can use pet commands!")
            return
        
        pet = await self.pet_system.get_user_pet(ctx.author.id)
        if not pet:
            await ctx.send("🤖 You don't have a pet yet! Use `/get_pet autobot` or `/get_pet decepticon` to get one.")
            return

        # Get all pet items from inventory
        items = await self.pet_system.get_all_pet_items(ctx.author.id)
        if not items:
            await ctx.send("📦 You don't have any pet items yet! Complete missions to earn equipment.")
            return

        # Create and send the pagination view
        view = PetEquipmentView(ctx.author.id, self.pet_system, items)
        embed = await view.create_embed(0)
        await ctx.send(embed=embed, view=view if len(items) > 10 else None)

class PetCommandsCog(commands.Cog):
    """Cog for pet-related commands"""
    
    def __init__(self, bot: commands.Bot, pet_system: PetSystem, pet_commands: PetCommands):
        self.bot = bot
        self.pet_system = pet_system
        self.pet_commands = pet_commands
    
    @commands.hybrid_command(name='get_pet', description='Get your first digital pet')
    @app_commands.describe(faction="Choose your pet's faction")
    @app_commands.choices(faction=[
        app_commands.Choice(name="🔴 Autobot (Happy Defender)", value="autobot"),
        app_commands.Choice(name="🟣 Decepticon (Energetic Attacker)", value="decepticon")
    ])
    async def get_pet(self, ctx: commands.Context, faction: str):
        if not has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can use pet commands!")
            return
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

    @commands.hybrid_command(name='pet_equip', description='Equip items to your pet or view equipment')
    @app_commands.describe(
        slot="Equipment slot to manage",
        item_name="Name of item to equip (optional)"
    )
    @app_commands.choices(slot=[
        app_commands.Choice(name="🛡️ Chassis Plating", value="chassis_plating"),
        app_commands.Choice(name="⚡ Energy Cores", value="energy_cores"),
        app_commands.Choice(name="🔧 Utility Modules", value="utility_modules")
    ])
    async def pet_equip(self, ctx: commands.Context, slot: str = None, item_name: str = None):
        await self.pet_commands.pet_equip_command(ctx, slot, item_name)

    @commands.hybrid_command(name='pet_equipment', description='View all your pet items with pagination')
    async def pet_equipment(self, ctx: commands.Context):
        await self.pet_commands.pet_equipment_command(ctx)

# Helper function for role checking
def has_cybertronian_role(member: discord.Member) -> bool:
    """Check if member has Cybertronian role"""
    if not member or not member.roles:
        return False
    
    cybertronian_role_ids = [ROLE_IDS.get(role) for role in ['Autobot', 'Decepticon', 'Maverick', 'Cybertronian_Citizen']]
    return any(role.id in cybertronian_role_ids for role in member.roles if role.id in cybertronian_role_ids)

# Setup functions for the commands
async def setup_pet_commands(bot: commands.Bot) -> None:
    """
    Setup all pet-related commands for the bot
    
    This function:
    1. Creates PetCommands instance
    2. Registers all hybrid commands via cog
    """
    try:
        if not hasattr(bot, 'pet_system'):
            logger.error("Pet system not found on bot instance")
            raise ValueError("Bot instance missing pet_system")
            
        pet_commands = PetCommands(bot, bot.pet_system)
        
        # Add pet commands cog
        await bot.add_cog(PetCommandsCog(bot, bot.pet_system, pet_commands))
        
        # Store instance for external access
        bot.pet_commands = pet_commands
        logger.info("Pet commands cog loaded successfully")
        
    except Exception as e:
        logger.error(f"Failed to setup pet commands: {e}")
        raise

# Enhanced setup function for pet commands only
async def setup(bot_instance: commands.Bot):
    """Async setup function for pet system commands only (no battle commands)"""
    try:
        # Validate bot instance
        if not bot_instance:
            raise ValueError("Bot instance is None")
            
        # Use the existing pet system from pets_system.py - don't create a new one
        if not hasattr(bot_instance, 'pet_system'):
            logger.error("Pet system not found! Make sure pets_system.py is loaded first.")
            return False
        
        # Setup pet commands only
        await setup_pet_commands(bot_instance)
        
        logger.info("Pet system commands loaded successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to load pet system commands: {e}")
        raise

# Export the setup function for the cog
__all__ = ['setup', 'setup_pet_commands', 'PetCommands', 'PetCommandsCog']