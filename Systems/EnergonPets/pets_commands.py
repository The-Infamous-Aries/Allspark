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
        embed.add_field(name="🎮 Commands", value="Use `/charge_pet`, `/play` & `/repair_pet` to raise pet levels.\n `/train` & `/mission` to gain Energon & XP.\n Use `/battle` (1v1) & `/group_battle` (4v1) to fight NPC enemies.\n Use `/pet` to see, `/rename_pet` to rename and `/kill` to kill pet!", inline=False)
        
        await ctx.send(embed=embed)
    
    async def pet_status_command(self, ctx: commands.Context) -> None:
        """Handle /pet command"""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can access the pet system! Please get a Cybertronian role first.")
            return
        
        # Send immediate response to prevent timeout - use ephemeral thinking message
        await ctx.defer(ephemeral=False)
        
        try:
            # Get pet data with minimal delay - use direct fetch
            pet = await self.pet_system.get_user_pet(ctx.author.id)
            if not pet:
                await ctx.send("🤖 You don't have a pet yet! Use `/get_pet autobot` or `/get_pet decepticon` to get one.")
                return

            # Quick migration check - only if absolutely necessary
            needs_migration = (
                'total_wins' not in pet or 
                'total_losses' not in pet or
                'total_mission_energon' not in pet
            )
            
            if needs_migration:
                # Quick migration - don't wait for save
                await self.pet_system.migrate_pet_data(pet)
                asyncio.create_task(user_data_manager.save_pet_data(str(ctx.author.id), str(ctx.author), pet))
            
            # Import PetStatusView from pets_system
            from .pets_system import PetStatusView
            
            # Create interactive view with buttons - optimized for speed
            view = PetStatusView(ctx.author.id, self.pet_system, self, pet_data=pet)
            embed = await view.create_main_embed()
            
            # Send response immediately
            message = await ctx.send(embed=embed, view=view)
            view.message = message
            
        except Exception as e:
            logger.error(f"Error in pet_status_command: {e}")
            try:
                await ctx.send("❌ An error occurred while loading your pet. Please try again in a moment.")
            except:
                # Fallback if interaction already failed
                pass
    
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

    async def pet_unequip_command(self, ctx: commands.Context, slot: str) -> None:
        """Handle /pet_unequip command to remove items from equipment slots"""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can use pet commands!")
            return
            
        pet = await self.pet_system.get_user_pet(ctx.author.id)
        if not pet:
            await ctx.send("🤖 You don't have a pet yet! Use `/get_pet autobot` or `/get_pet decepticon` to get one.")
            return

        success, message = await self.pet_system.unequip_item(ctx.author.id, slot)
        if success:
            await ctx.send(f"✅ {message}")
        else:
            await ctx.send(f"❌ {message}")

    @commands.command(name='pet_equip')
    async def pet_equip_command(self, ctx: commands.Context) -> None:
        """Show 3 dropdown menus for pet equipment selection in a dismissible message"""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can use pet commands!")
            return
            
        pet = await self.pet_system.get_user_pet(ctx.author.id)
        if not pet:
            await ctx.send("🤖 You don't have a pet yet! Use `/get_pet autobot` or `/get_pet decepticon` to get one.")
            return

        # Show 3 dropdown menus in a dismissible ephemeral message
        view = PetEquipmentSelectionView(ctx.author.id, self.pet_system)
        embed = discord.Embed(
            title="🛡️ Pet Equipment Selection",
            description="Select equipment for your pet from the dropdown menus below.\n\nThis message will disappear when you're done.",
            color=discord.Color.blue()
        )
        await ctx.reply(embed=embed, view=view, ephemeral=True)

class PetEquipmentSelectionView(discord.ui.View):
    """View with 3 dropdown menus for pet equipment selection"""
    
    def __init__(self, user_id: int, pet_system):
        super().__init__()
        self.user_id = user_id
        self.pet_system = pet_system
        self.selected_equipment = {
            'chassis_plating': None,
            'energy_cores': None,
            'utility_modules': None
        }
        
        # Create dropdowns for each equipment type
        self._create_dropdowns()
    
    async def _get_user_equipment(self, slot: str) -> list:
        """Get user's obtained equipment for a specific slot"""
        try:
            pet = await self.pet_system.get_user_pet(self.user_id)
            if not pet:
                return []
            
            inventory = pet.get('inventory', [])
            equipment_data = await self.pet_system.get_pet_equipment_data()
            
            available = []
            for item in inventory:
                if isinstance(item, dict) and item.get('type') == slot:
                    item_id = item.get('id')
                    if item_id and item_id in equipment_data:
                        equipment = equipment_data[item_id]
                        available.append({
                            'id': item_id,
                            'name': equipment.get('name', item_id),
                            'rarity': equipment.get('rarity', 'common'),
                            'stats': equipment.get('stat_bonus', {})
                        })
            
            # Sort by rarity
            rarity_order = {'common': 1, 'uncommon': 2, 'rare': 3, 'epic': 4, 'legendary': 5, 'mythic': 6}
            return sorted(available, key=lambda x: rarity_order.get(x['rarity'], 0), reverse=True)
        except Exception:
            return []
    
    def _create_dropdowns(self):
        """Create dropdown menus for each equipment slot"""
        slots = [
            ('chassis_plating', '🛡️ Chassis Plating'),
            ('energy_cores', '⚡ Energy Cores'),
            ('utility_modules', '🔧 Utility Modules')
        ]
        
        for slot, display_name in slots:
            dropdown = PetEquipmentDropdown(slot, display_name, self)
            self.add_item(dropdown)
    
    @discord.ui.button(label="Equip Selected Items", style=discord.ButtonStyle.green, row=4)
    async def equip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Equip all selected items"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This selection is for someone else!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        equipped_count = 0
        messages = []
        
        for slot, item_id in self.selected_equipment.items():
            if item_id:
                success, message = await self.pet_system.equip_item(self.user_id, item_id)
                if success:
                    equipped_count += 1
                    messages.append(message)
        
        if equipped_count > 0:
            final_message = f"✅ Successfully equipped {equipped_count} item(s)!\n" + "\n".join(messages)
            await interaction.followup.send(final_message, ephemeral=True)
        else:
            await interaction.followup.send("❌ No items selected to equip.", ephemeral=True)
        
        self.stop()
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, row=4)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel equipment selection"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This selection is for someone else!", ephemeral=True)
            return
        
        await interaction.response.send_message("❌ Equipment selection cancelled.", ephemeral=True)
        self.stop()

class PetEquipmentTypeView(discord.ui.View):
    """Interactive view for displaying items of a specific type with equipment selection"""
    
    def __init__(self, user_id: int, pet_system, items: List[Dict[str, Any]], equipment_type: str):
        super().__init__(timeout=300)  # 5 minute timeout
        self.user_id = user_id
        self.pet_system = pet_system
        self.items = items
        self.equipment_type = equipment_type
        
        # Add type-specific dropdown
        dropdown = EquipmentTypeDropdown(user_id, pet_system, items, equipment_type)
        self.add_item(dropdown)
    
    def get_rarity_emoji(self, rarity: str) -> str:
        """Get emoji for item rarity"""
        rarity_emojis = {
            "common": "⚪",
            "uncommon": "🟢", 
            "rare": "🔵",
            "epic": "🟣", 
            "legendary": "🟡",
            "mythic": "🟠"
        }
        return rarity_emojis.get(rarity.lower(), "⚪")
    
    def get_type_emoji(self, item_type: str) -> str:
        """Get emoji for item type"""
        type_emojis = {
            "chassis_plating": "🛡️",
            "energy_cores": "⚡",
            "utility_modules": "🔧"
        }
        return type_emojis.get(item_type.lower(), "📦")
    
    def format_stat_bonus(self, stat_bonus: Dict[str, int]) -> str:
        """Format stat bonus text"""
        if not stat_bonus:
            return ""
        
        stat_emojis = {
            "attack": "⚔️",
            "defense": "🛡️",
            "energy": "⚡",
            "maintenance": "🔧",
            "happiness": "😊"
        }
        
        parts = []
        for stat, value in stat_bonus.items():
            if value != 0:
                emoji = stat_emojis.get(stat, "📊")
                parts.append(f"{emoji} +{value}")
        return " | ".join(parts)
    
    async def create_type_embed(self) -> discord.Embed:
        """Create embed for type-specific equipment selection"""
        type_emoji = self.get_type_emoji(self.equipment_type)
        type_name = self.equipment_type.replace('_', ' ').title()
        
        embed = discord.Embed(
            title=f"{type_emoji} Equip {type_name}",
            description=f"Select a {type_name} item to equip to your pet from the dropdown below.",
            color=discord.Color.blue()
        )
        
        # Add pet info
        pet = await self.pet_system.get_user_pet(self.user_id)
        if pet:
            embed.set_author(name=f"{pet['name']}'s Equipment", icon_url=pet.get('image_url'))
            
            # Show currently equipped item of this type
            equipped = pet.get('equipment', {})
            current_item = equipped.get(self.equipment_type)
            if current_item:
                embed.add_field(
                    name="Currently Equipped",
                    value=f"**{current_item['name']}** {self.get_rarity_emoji(current_item.get('rarity', 'common'))}",
                    inline=False
                )
            else:
                embed.add_field(
                    name="Currently Equipped",
                    value="None",
                    inline=False
                )
        
        # List available items
        if self.items:
            item_list = []
            for item in self.items[:5]:  # Show first 5 items
                rarity_emoji = self.get_rarity_emoji(item.get('rarity', 'common'))
                stats = self.format_stat_bonus(item.get('stat_bonus', {}))
                item_list.append(f"{rarity_emoji} **{item['name']}** - {stats}")
            
            embed.add_field(
                name="Available Items",
                value="\n".join(item_list) if item_list else "No items available",
                inline=False
            )
        
        return embed

class EquipmentTypeDropdown(discord.ui.Select):
    """Dropdown for selecting specific equipment item by type"""
    
    def __init__(self, user_id: int, pet_system, items: List[Dict[str, Any]], equipment_type: str):
        self.user_id = user_id
        self.pet_system = pet_system
        self.items = items
        self.equipment_type = equipment_type
        
        # Create options for items of this type
        options = []
        
        # Add "None" option to unequip this slot
        type_emoji = {
            'chassis_plating': '🛡️',
            'energy_cores': '⚡',
            'utility_modules': '🔧'
        }.get(equipment_type, '📦')
        type_name = equipment_type.replace('_', ' ').title()
        
        options.append(discord.SelectOption(
            label=f"Remove {type_name}",
            value="none",
            description=f"Unequip current {type_name}",
            emoji="❌"
        ))
        
        # Add items of the specified type
        for item in items:
            rarity_emoji = self._get_rarity_emoji(item.get('rarity', 'common'))
            name = item.get('name', 'Unknown')
            
            # Format stat bonus
            stat_bonus = item.get('stat_bonus', {})
            stat_desc = []
            for stat, value in stat_bonus.items():
                if value > 0:
                    stat_desc.append(f"+{value} {stat}")
            description = ", ".join(stat_desc)[:100]
            
            label = f"{rarity_emoji} {name}"
            if len(label) > 100:
                label = label[:97] + "..."
            
            options.append(discord.SelectOption(
                label=label,
                value=item['id'],
                description=description,
                emoji=type_emoji
            ))
        
        super().__init__(
            placeholder=f"Select {type_name}...",
            options=options[:25],  # Discord limit
            min_values=1,
            max_values=1
        )
    
    def _get_rarity_emoji(self, rarity: str) -> str:
        """Get emoji for rarity"""
        emoji_map = {
            'common': '⚪',
            'uncommon': '🟢',
            'rare': '🔵',
            'epic': '🟣',
            'legendary': '🟡',
            'mythic': '🟠'
        }
        return emoji_map.get(rarity.lower(), '⚪')
    
    async def callback(self, interaction: discord.Interaction):
        """Handle equipment selection"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This selection is for someone else!", ephemeral=True)
            return
        
        selected_value = self.values[0]
        
        try:
            if selected_value == "none":
                # Unequip item from this slot
                success, message = await self.pet_system.unequip_item(self.user_id, self.equipment_type)
                await interaction.response.send_message(message, ephemeral=True)
            else:
                # Equip the selected item
                success, message = await self.pet_system.equip_item(self.user_id, selected_value)
                await interaction.response.send_message(message, ephemeral=True)
        
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class PetEquipmentDropdown(discord.ui.Select):
    """Dropdown for selecting pet equipment"""
    
    def __init__(self, slot: str, display_name: str, parent_view: PetEquipmentSelectionView):
        self.slot = slot
        self.parent_view = parent_view
        
        # Create placeholder options initially
        options = [discord.SelectOption(label=f"No {display_name}", value=f"none_{slot}")]
        
        super().__init__(
            placeholder=f"Select {display_name}",
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle dropdown selection"""
        if interaction.user.id != self.parent_view.user_id:
            await interaction.response.send_message("❌ This selection is for someone else!", ephemeral=True)
            return
        
        selected_value = self.values[0]
        
        if selected_value.startswith("none_"):
            self.parent_view.selected_equipment[self.slot] = None
        else:
            self.parent_view.selected_equipment[self.slot] = selected_value
        
        await interaction.response.defer()
    
    async def populate_options(self):
        """Populate dropdown with user's obtained equipment"""
        equipment = await self.parent_view._get_user_equipment(self.slot)
        
        options = []
        
        # Add "None" option
        options.append(discord.SelectOption(
            label=f"No {self.slot.replace('_', ' ').title()}",
            value=f"none_{self.slot}",
            description="Don't equip any item for this slot"
        ))
        
        # Add available equipment
        for item in equipment:
            rarity_emoji = self._get_rarity_emoji(item['rarity'])
            label = f"{rarity_emoji} {item['name']}"
            
            # Create stats description
            stats = item['stats']
            stats_desc = []
            for stat, value in stats.items():
                if value > 0:
                    stats_desc.append(f"+{value} {stat}")
            description = ", ".join(stats_desc)[:100]
            
            options.append(discord.SelectOption(
                label=label[:100],
                value=item['id'],
                description=description
            ))
        
        self.options = options[:25]  # Discord limit
    
    def _get_rarity_emoji(self, rarity: str) -> str:
        """Get emoji for rarity"""
        emoji_map = {
            'common': '⚪',
            'uncommon': '🟢',
            'rare': '🔵',
            'epic': '🟣',
            'legendary': '🟡',
            'mythic': '🟠'
        }
        return emoji_map.get(rarity.lower(), '⚪')

    async def pet_equip_command(self, ctx: commands.Context, equipment_type: str = None) -> None:
        """Handle /pet_equip command to equip items to your pet"""
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

        if equipment_type:
            # Filter items by selected type
            filtered_items = [item for item in items if item.get('type') == equipment_type]
            if not filtered_items:
                type_emoji = {
                    'chassis_plating': '🛡️',
                    'energy_cores': '⚡',
                    'utility_modules': '🔧'
                }.get(equipment_type, '📦')
                type_name = equipment_type.replace('_', ' ').title()
                await ctx.send(f"{type_emoji} You don't have any {type_name} items to equip!")
                return
            
            # Create type-specific equipment view
            view = PetEquipmentTypeView(ctx.author.id, self.pet_system, filtered_items, equipment_type)
            embed = await view.create_type_embed()
            await ctx.send(embed=embed, view=view)
        else:
            # Show all items with equipment selection
            view = PetEquipmentView(ctx.author.id, self.pet_system, items)
            embed = await view.create_equipment_embed()
            await ctx.send(embed=embed, view=view)

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

    @commands.hybrid_command(name='pet_equip', description='Equip items to your pet by type')
    @app_commands.describe(
        equipment_type="Type of equipment to equip"
    )
    @app_commands.choices(equipment_type=[
        app_commands.Choice(name="🛡️ Chassis Plating", value="chassis_plating"),
        app_commands.Choice(name="⚡ Energy Cores", value="energy_cores"),
        app_commands.Choice(name="🔧 Utility Modules", value="utility_modules")
    ])
    async def pet_equip(self, ctx: commands.Context, equipment_type: str = None):
        await self.pet_commands.pet_equip_command(ctx, equipment_type)

    @commands.hybrid_command(name='pet_equipment', description='View all your pet items with pagination')
    async def pet_equipment(self, ctx: commands.Context):
        await self.pet_commands.pet_equipment_command(ctx)

    @commands.hybrid_command(name='pet_unequip', description='Unequip items from your pet')
    @app_commands.describe(
        slot="Equipment slot to unequip from"
    )
    @app_commands.choices(slot=[
        app_commands.Choice(name="🛡️ Chassis Plating", value="chassis_plating"),
        app_commands.Choice(name="⚡ Energy Cores", value="energy_cores"),
        app_commands.Choice(name="🔧 Utility Modules", value="utility_modules")
    ])
    async def pet_unequip(self, ctx: commands.Context, slot: str):
        await self.pet_commands.pet_unequip_command(ctx, slot)

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
