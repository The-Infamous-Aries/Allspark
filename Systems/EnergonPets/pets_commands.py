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
from .pets_system import PetEquipmentView, PetSystem, PET_STAGES, LEVEL_THRESHOLDS
from .pet_levels import get_stage_name
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
            
        cybertronian_role_ids = []
        for role_name in ['Autobot', 'Decepticon', 'Maverick', 'Cybertronian_Citizen']:
            role_ids = ROLE_IDS.get(role_name, [])
            if isinstance(role_ids, list):
                cybertronian_role_ids.extend(role_ids)
            else:
                cybertronian_role_ids.append(role_ids)
        
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
        # Get stage emoji and name for new pet
        try:
            stage_emoji = self.pet_system.get_stage_emoji(pet_data['level'])
            stage_name = get_stage_name(pet_data['level'])
        except:
            stage_emoji = "🥚"
            stage_name = "Spark Initiate"
        
        color = discord.Color.blue() if pet_data['faction'] == 'Autobot' else discord.Color.red()
        
        embed = discord.Embed(
            title=f"{stage_emoji} Welcome to the Digital Pet System!",
            description=f"You've received **{pet_data['name']}**, a {pet_data['faction']} {stage_emoji} {stage_name}!",
            color=color
        )
        
        embed.add_field(name="⚡ Energy", value=f"{pet_data['energy']}/{pet_data['max_energy']}", inline=True)
        embed.add_field(name="😊 Happiness", value=f"{pet_data['happiness']}/{pet_data['max_happiness']}", inline=True)
        embed.add_field(name="🛠️ Maintenance", value=f"{pet_data['maintenance']}/{pet_data['max_maintenance']}", inline=True)
        embed.add_field(name="⚔️ Attack", value=f"{pet_data['attack']}", inline=True)
        embed.add_field(name="🛡️ Defense", value=f"{pet_data['defense']}", inline=True)
        embed.add_field(name="🧬 Stage", value=f"{stage_emoji} {stage_name}", inline=True)
        embed.add_field(name="🎮 Commands", value="Use `/charge_pet`, `/play` & `/repair_pet` to raise pet levels.\n `/train` & `/mission` to gain Energon & XP.\n Use `/battle` (1v1) & `/group_battle` for PvE fun!\n ", inline=False)
        
        await ctx.send(embed=embed)
    
    async def pet_status_command(self, ctx: commands.Context) -> None:
        """Handle /pet command"""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can access the pet system! Please get a Cybertronian role first.")
            return
        
        await ctx.defer(ephemeral=False)
        
        try:
            pet = await self.pet_system.get_user_pet(ctx.author.id)
            if not pet:
                await ctx.send("🤖 You don't have a pet yet! Use `/get_pet autobot` or `/get_pet decepticon` to get one.")
                return

            needs_migration = (
                'total_wins' not in pet or 
                'total_losses' not in pet or
                'total_mission_energon' not in pet
            )
            
            if needs_migration:
                await self.pet_system.migrate_pet_data(pet)
                asyncio.create_task(user_data_manager.save_pet_data(str(ctx.author.id), str(ctx.author), pet))
            
            from .pets_system import PetStatusView
            view = PetStatusView(ctx.author.id, self.pet_system, self, pet_data=pet)
            embed = await view.create_main_embed()
            message = await ctx.send(embed=embed, view=view)
            view.message = message
            
        except Exception as e:
            logger.error(f"Error in pet_status_command: {e}")
            try:
                await ctx.send("❌ An error occurred while loading your pet. Please try again in a moment.")
            except:
                pass
    
    async def charge_pet_command(self, ctx: commands.Context, percentage: str = "50") -> None:
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can use pet commands!")
            return
        
        success, message, level_gains = await self.pet_system.charge_pet(ctx.author.id, percentage)
        if success:
            await ctx.send(f"✅ {message}")
            if level_gains:
                from .pet_levels import send_level_up_embed
                asyncio.create_task(send_level_up_embed(ctx.author.id, level_gains, ctx.channel))
        else:
            await ctx.send(f"❌ {message}")
    
    async def play_command(self, ctx: commands.Context, percentage: str = "50") -> None:
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can use pet commands!")
            return
        
        success, message, level_gains = await self.pet_system.play_with_pet(ctx.author.id, percentage)
        if success:
            await ctx.send(f"✅ {message}")
            if level_gains:
                from .pet_levels import send_level_up_embed
                asyncio.create_task(send_level_up_embed(ctx.author.id, level_gains, ctx.channel))
        else:
            await ctx.send(f"❌ {message}")
    
    async def train_command(self, ctx: commands.Context, difficulty: str) -> None:
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can use pet commands!")
            return
        
        success, message, level_gains = await self.pet_system.train_pet(ctx.author.id, difficulty)
        if success:
            await ctx.send(message)
            if level_gains:
                from .pet_levels import send_level_up_embed
                asyncio.create_task(send_level_up_embed(ctx.author.id, level_gains, ctx.channel))
        else:
            await ctx.send(f"❌ {message}")
    
    async def repair_pet_command(self, ctx: commands.Context, percentage: str = "50%") -> None:
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can use pet commands!")
            return
        
        success, message, level_gains = await self.pet_system.repair_pet(ctx.author.id, percentage)
        if success:
            await ctx.send(f"✅ {message}")
            if level_gains:
                from .pet_levels import send_level_up_embed
                asyncio.create_task(send_level_up_embed(ctx.author.id, level_gains, ctx.channel))
        else:
            await ctx.send(f"❌ {message}")
    
    async def rename_pet_command(self, ctx: commands.Context, new_name: str) -> None:
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
        
        stage_name = get_stage_name(pet["level"])
        await ctx.send(f"✅ Your {stage_name} has been renamed from **{old_name}** to **{new_name}**!")
    
    async def kill_pet_command(self, ctx: commands.Context) -> None:
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can access the pet system!")
            return
        
        pet = await self.pet_system.get_user_pet(ctx.author.id)
        if not pet:
            await ctx.send("🤖 You don't have a pet to delete!")
            return
        
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
                    description=f"Your pet **{pet['name']}** is safe! {self.pet_system.get_stage_emoji(pet['level'])}",
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
                        stage_name = get_stage_name(deleted_pet["level"])
                        stage_emoji = self.pet_system.get_stage_emoji(deleted_pet["level"])
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
        
        stage_name = get_stage_name(pet["level"])
        color = discord.Color.blue() if pet['faction'] == 'Autobot' else discord.Color.red()
        
        embed = discord.Embed(
            title="⚠️ PERMANENT PET DELETION WARNING",
            description=f"Are you sure you want to **permanently delete** your pet?\n\n**{pet['name']}** - {pet['faction']} {stage_name}\nLevel {pet['level']} | ATT: {pet['attack']} | DEF: {pet['defense']}",
            color=discord.Color.red()
        )
        
        embed.add_field(name="⚠️ WARNING", value="This action is **IRREVERSIBLE**!\nAll progress, stats, and memories will be lost forever.", inline=False)
        equipment_stats = await self.pet_system.get_equipment_stats(ctx.author.id)
        total_max_energy = pet['max_energy'] + equipment_stats.get('energy', 0)
        total_max_maintenance = pet['max_maintenance'] + equipment_stats.get('maintenance', 0)
        total_max_happiness = pet['max_happiness'] + equipment_stats.get('happiness', 0)
        
        embed.add_field(name="📊 Current Stats", value=f"Energy: {pet['energy']:.0f}/{total_max_energy:.0f}\nMaintenance: {pet['maintenance']:.0f}/{total_max_maintenance:.0f}\nHappiness: {pet['happiness']:.0f}/{total_max_happiness:.0f}", inline=False)
        embed.add_field(name="🏆 Achievements", value=f"Missions: {pet.get('missions_completed', 0)}\nBattles Won: {pet.get('battles_won', 0)}\nBattles Lost: {pet.get('battles_lost', 0)}", inline=True)
        
        view = KillConfirmView(self.pet_system, ctx)
        await ctx.send(embed=embed, view=view)

    async def mission_command(self, ctx: commands.Context, difficulty: str) -> None:
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can use pet commands!")
            return
        
        success, message = await self.pet_system.send_mission(ctx.author.id, difficulty)
        if success:
            await ctx.send(message)
        else:
            await ctx.send(f"❌ {message}")

    async def pet_unequip_command(self, ctx: commands.Context, slot: str) -> None:
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
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can use pet commands!")
            return
            
        pet = await self.pet_system.get_user_pet(ctx.author.id)
        if not pet:
            await ctx.send("🤖 You don't have a pet yet! Use `/get_pet autobot` or `/get_pet decepticon` to get one.")
            return

        view = PetEquipmentSelectionView(ctx.author.id, self.pet_system)
        await view.async_init()
        embed = discord.Embed(
            title="🛡️ Pet Equipment Selection",
            description="Select equipment for your pet from the dropdown menus below.\n\nThis message will disappear when you're done.",
            color=discord.Color.blue()
        )
        await ctx.reply(embed=embed, view=view, ephemeral=True)

class PetEquipmentSelectionView(discord.ui.View):
    """Main view for pet equipment selection with type-based organization"""
    
    def __init__(self, user_id: int, pet_system):
        super().__init__(timeout=300)  # 5 minute timeout
        self.user_id = user_id
        self.pet_system = pet_system
        self.message = None
        
    async def async_init(self):
        """Initialize the view with current equipment data"""
        self.pet = await self.pet_system.get_user_pet(self.user_id)
        self.items = await self.pet_system.get_all_pet_items(self.user_id)
        
        # Add equipment type selection buttons
        self.add_item(EquipmentTypeButton("chassis_plating", "🛡️ Chassis Plating", self))
        self.add_item(EquipmentTypeButton("energy_cores", "⚡ Energy Cores", self))
        self.add_item(EquipmentTypeButton("utility_modules", "🔧 Utility Modules", self))
        self.add_item(CloseButton())

    def get_rarity_emoji(self, rarity: str) -> str:
        """Get emoji for item rarity"""
        rarity_emojis = {
            "common": "⚪",
            "uncommon": "🟢", 
            "rare": "🔵",
            "epic": "🟣", 
            "legendary": "🟠",
            "mythic": "🔴"
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

    async def create_main_embed(self) -> discord.Embed:
        """Create the main equipment selection embed"""
        pet = self.pet
        if not pet:
            return discord.Embed(
                title="❌ No Pet Found",
                description="You don't have a pet yet!",
                color=discord.Color.red()
            )

        color = discord.Color.blue() if pet['faction'] == 'Autobot' else discord.Color.red()
        embed = discord.Embed(
            title="🛡️ Pet Equipment Management",
            description=f"Manage equipment for **{pet['name']}**",
            color=color
        )

        # Show current equipment
        equipment = pet.get('equipment', {})
        for slot in ['chassis_plating', 'energy_cores', 'utility_modules']:
            type_emoji = self.get_type_emoji(slot)
            current_item = equipment.get(slot)
            if current_item:
                rarity_emoji = self.get_rarity_emoji(current_item.get('rarity', 'common'))
                stats = self.format_stat_bonus(current_item.get('stat_bonus', {}))
                embed.add_field(
                    name=f"{type_emoji} {slot.replace('_', ' ').title()}",
                    value=f"{rarity_emoji} **{current_item['name']}**\n{stats}",
                    inline=True
                )
            else:
                embed.add_field(
                    name=f"{type_emoji} {slot.replace('_', ' ').title()}",
                    value="*Empty*",
                    inline=True
                )

        # Show item counts
        if self.items:
            type_counts = {}
            for item in self.items:
                item_type = item.get('type', 'unknown')
                type_counts[item_type] = type_counts.get(item_type, 0) + 1
            
            count_text = []
            for item_type in ['chassis_plating', 'energy_cores', 'utility_modules']:
                count = type_counts.get(item_type, 0)
                emoji = self.get_type_emoji(item_type)
                count_text.append(f"{emoji} {count}")
            
            embed.add_field(
                name="📦 Available Items",
                value=" ".join(count_text),
                inline=False
            )

        return embed


class EquipmentTypeButton(discord.ui.Button):
    """Button for selecting equipment type"""
    
    def __init__(self, equipment_type: str, label: str, parent_view: PetEquipmentSelectionView):
        super().__init__(label=label, style=discord.ButtonStyle.primary, emoji=parent_view.get_type_emoji(equipment_type))
        self.equipment_type = equipment_type
        self.parent_view = parent_view
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_view.user_id:
            await interaction.response.send_message("❌ Only the pet owner can use this!", ephemeral=True)
            return
        
        # Get items of this type
        items = [item for item in self.parent_view.items if item.get('type') == self.equipment_type]
        
        if not items:
            embed = discord.Embed(
                title=f"{self.parent_view.get_type_emoji(self.equipment_type)} No {self.equipment_type.replace('_', ' ').title()}",
                description="You don't have any items of this type! Complete missions to earn equipment.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Create type-specific view
        view = PetEquipmentTypeView(
            self.parent_view.user_id, 
            self.parent_view.pet_system, 
            items, 
            self.equipment_type
        )
        embed = await view.create_type_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class CloseButton(discord.ui.Button):
    """Button to close the equipment selection"""
    
    def __init__(self):
        super().__init__(label="Close", style=discord.ButtonStyle.secondary, emoji="❌")
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.message.delete()


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
            "legendary": "🟠",
            "mythic": "🔴"
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

    async def pet_equip_command(self, ctx: commands.Context, chassis_plating: str = None, energy_cores: str = None, utility_modules: str = None) -> None:
        """Handle /pet_equip command to equip items to your pet"""
        if not self.has_cybertronian_role(ctx.author):
            await ctx.send("❌ Only Cybertronian Citizens can use pet commands!")
            return
        
        pet = await self.pet_system.get_user_pet(ctx.author.id)
        if not pet:
            await ctx.send("🤖 You don't have a pet yet! Use `/get_pet autobot` or `/get_pet decepticon` to get one.")
            return

        # Track items to equip
        items_to_equip = {
            'chassis_plating': chassis_plating,
            'energy_cores': energy_cores,
            'utility_modules': utility_modules
        }

        # Filter out "none" values and None
        valid_items = {slot: item_id for slot, item_id in items_to_equip.items() 
                      if item_id and item_id != "none"}

        if not valid_items:
            # If no items specified, show the old selection view
            items = await self.pet_system.get_all_pet_items(ctx.author.id)
            if not items:
                await ctx.send("📦 You don't have any pet items yet! Complete missions to earn equipment.")
                return
            
            view = PetEquipmentSelectionView(ctx.author.id, self.pet_system)
            await view.async_init()
            embed = discord.Embed(
                title="🛡️ Pet Equipment Selection",
                description="Select equipment for your pet from the dropdown menus below.",
                color=discord.Color.blue()
            )
            await ctx.reply(embed=embed, view=view, ephemeral=True)
            return

        # Process the specified items
        equipped_count = 0
        messages = []
        
        for slot, item_id in valid_items.items():
            # Verify the item exists and is of correct type
            items = await self.pet_system.get_all_pet_items(ctx.author.id)
            item_exists = any(item.get('id') == item_id and item.get('type') == slot for item in items)
            
            if item_exists:
                success, message = await self.pet_system.equip_item(ctx.author.id, item_id)
                if success:
                    equipped_count += 1
                    messages.append(message)
                else:
                    messages.append(f"❌ Failed to equip {item_id}: {message}")
            else:
                messages.append(f"❌ Item {item_id} not found or wrong type for {slot}")

        # Send summary
        if equipped_count > 0:
            embed = discord.Embed(
                title=f"✅ Equipment Update Complete",
                description=f"Successfully equipped {equipped_count} item(s)!",
                color=discord.Color.green()
            )
            embed.add_field(name="Details", value="\n".join(messages), inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ No items were equipped. Please check your selections.")

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
    @app_commands.describe(percentage="How long to charge your pet")
    @app_commands.choices(percentage=[
        app_commands.Choice(name="🪫 15 minutes", value="50%"),
        app_commands.Choice(name="🔋 30 minutes", value="75%"),
        app_commands.Choice(name="🏭 1 hour", value="100%")
    ])
    async def charge_pet(self, ctx: commands.Context, percentage: str):
        await self.pet_commands.charge_pet_command(ctx, percentage)
    
    @commands.hybrid_command(name='play', description='Play with your pet to increase happiness with duration options')
    @app_commands.describe(percentage="How long to play with your pet")
    @app_commands.choices(percentage=[
        app_commands.Choice(name="🎮 15 minutes", value="50%"),
        app_commands.Choice(name="🃏 30 minutes", value="75%"),
        app_commands.Choice(name="🎳 1 hour", value="100%")
    ])
    async def play(self, ctx: commands.Context, percentage: str):
        await self.pet_commands.play_command(ctx, percentage)
    
    @commands.hybrid_command(name='repair_pet', description='Repair your pet\'s maintenance with duration options')
    @app_commands.describe(percentage="How long to repair your pet")
    @app_commands.choices(percentage=[
        app_commands.Choice(name="⚙️ 15 minutes", value="50%"),
        app_commands.Choice(name="🔨 30 minutes", value="75%"),
        app_commands.Choice(name="🛠️ 1 hour", value="100%")
    ])
    async def repair_pet(self, ctx: commands.Context, percentage: str):
        await self.pet_commands.repair_pet_command(ctx, percentage)
    
    @commands.hybrid_command(name='train', description='Train your pet with different intensity levels')
    @app_commands.describe(difficulty="Choose training intensity")
    @app_commands.choices(difficulty=[
        app_commands.Choice(name="⚡ Average", value="average"),
        app_commands.Choice(name="🔥 Intense", value="intense"),
        app_commands.Choice(name="💀 Godmode", value="godmode")
    ])
    async def train(self, ctx: commands.Context, difficulty: str):
        await self.pet_commands.train_command(ctx, difficulty)

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

    @commands.hybrid_command(name='pet_equip', description='Equip items to your pet')
    @app_commands.describe(
        chassis_plating='Select a chassis plating item to equip',
        energy_cores='Select an energy core item to equip', 
        utility_modules='Select a utility module item to equip'
    )
    async def pet_equip(self, ctx: commands.Context, 
                       chassis_plating: str = None, 
                       energy_cores: str = None, 
                       utility_modules: str = None):
        await self.pet_commands.pet_equip_command(ctx, chassis_plating, energy_cores, utility_modules)

    @pet_equip.autocomplete('chassis_plating')
    async def chassis_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self._equipment_autocomplete(interaction, current, 'chassis_plating')

    @pet_equip.autocomplete('energy_cores')
    async def energy_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self._equipment_autocomplete(interaction, current, 'energy_cores')

    @pet_equip.autocomplete('utility_modules')
    async def utility_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self._equipment_autocomplete(interaction, current, 'utility_modules')

    async def _equipment_autocomplete(self, interaction: discord.Interaction, current: str, equipment_type: str):
        """Generic autocomplete function for pet equipment"""
        try:
            user_id = interaction.user.id
            pet = await self.pet_system.get_user_pet(user_id)
            if not pet:
                return []

            items = await self.pet_system.get_all_pet_items(user_id)
            if not items:
                return []

            # Filter items by type
            filtered_items = [item for item in items if item.get('type') == equipment_type]
            if not filtered_items:
                return [app_commands.Choice(name="No items available", value="none")]

            # Get equipment data for names
            equipment_data = await self.pet_system.get_pet_equipment_data()
            
            choices = []
            for item in filtered_items:
                item_id = item.get('id')
                if item_id and item_id in equipment_data:
                    equipment = equipment_data[item_id]
                    name = equipment.get('name', item_id)
                    rarity = equipment.get('rarity', 'common')
                    rarity_emoji = {'common': '⚪', 'uncommon': '🟢', 'rare': '🔵', 'epic': '🟣', 'legendary': '🟠', 'mythic': '🔴'}.get(rarity, '⚪')
                    
                    # Format display name
                    display_name = f"{rarity_emoji} {name}"
                    if len(display_name) > 100:
                        display_name = display_name[:97] + "..."
                    
                    # Filter by current input
                    if current.lower() in name.lower():
                        choices.append(app_commands.Choice(name=display_name, value=item_id))

            # Add "None" option
            choices.insert(0, app_commands.Choice(name="🚫 None (don't equip)", value="none"))
            
            # Limit to 25 choices (Discord limit)
            return choices[:25]
            
        except Exception:
            return [app_commands.Choice(name="Error loading items", value="error")]

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

    @commands.hybrid_command(name="pet_info", description="Comprehensive guide to all pet systems with 4 detailed pages")
    async def pet_info(self, ctx):
        """Comprehensive 4-page guide covering all pet systems: Stats, Battles, Levels & Equipment, and RPG"""
        try:
            view = PetInfoView(ctx)
            await view.send_initial_message()
            
        except Exception as e:
            logger.error(f"Error in pet_info: {e}")
            await ctx.send("❌ Error displaying pet information.")

class PetInfoView(discord.ui.View):
    """Interactive view for the 4-page pet info system"""
    
    def __init__(self, ctx):
        super().__init__(timeout=300)  # 5 minute timeout
        self.ctx = ctx
        self.current_page = 1
        self.message = None
        
        # Add navigation buttons
        self.add_item(PreviousPageButton())
        self.add_item(NextPageButton())
        self.add_item(PageIndicatorButton())
        self.add_item(CloseButton())
    
    async def send_initial_message(self):
        """Send the initial message with page 1"""
        embed = self.create_page_1_stats()
        self.message = await self.ctx.send(embed=embed, view=self)
    
    def create_page_1_stats(self):
        """Page 1: Pet Stats System - Comprehensive explanation of pet statistics"""
        embed = discord.Embed(
            title="📊 Page 1/4: Pet Stats System",
            description="Complete guide to understanding your pet's core statistics and how they work",
            color=0x0099ff
        )
        
        # Core Stats Explained
        embed.add_field(
            name="⚡ Core Statistics Explained",
            value=(
                "**Attack (⚔️)** - Determines damage dealt in battles\n"
                "• Base damage = Attack stat value\n"
                "• Can be boosted by Energy Cores, Leveling Up & Training *may* increase\n"
                "• Critical hits deal bonus damage based on attack\n\n"
                
                "**Defense (🛡️)** - Reduces incoming damage\n"
                "• Higher defense = less damage taken\n"
                "• Can be boosted by Chassis Plating, Leveling Up & Training *may* increase\n"
                "• High enough defense can *parry* attacks\n\n"
                
                "**HP/Health (❤️)** - Combined resource total\n"
                "• Total HP = Energy + Maintenance + Happiness (current values)\n"
                "• Pets are defeated when total HP reaches 0\n"
                "• Restored by recharging energy, repairs, and playtime\n"
                "• Equipment increases maximum capacity for each resource"
            ),
            inline=False
        )
        
        # Resource Stats
        embed.add_field(
            name="🔋 Resource Management Stats",
            value=(
                "**Energy (⚡)** - Primary resource for actions\n"
                "• Consumed on most commands\n"
                "• Restore with charge command\n"
                "• Leveling Up & Energy Cores increase max Energy\n\n"
                
                "**Maintenance (🔧)** - Pet's physical condition\n"
                "• Decreases with battle damage and wear\n"
                "• Restored through repair command\n"
                "• Leveling Up & Utility Modules increase max Maintenance\n\n"
                
                "**Happiness (😊)** - Pet's morale and efficiency\n"
                "• Affects battle performance and rewards\n"
                "• Decreases with any loss, increases with play command\n"
                "• Leveling Up & Utility Modules increase max Happiness"
            ),
            inline=False
        )
        
        # Stat Calculation & Display
        embed.add_field(
            name="🧮 How Stats Are Calculated",
            value=(
                "**Base Stats** - Determined by pet level and faction\n"
                "• Autobots: +Defense bonus, slight Attack penalty\n"
                "• Decepticons: +Attack bonus, slight Defense penalty\n"
                "• Base values increase with each level up\n\n"
                
                "**Equipment Bonuses** - Added on top of base stats\n"
                "• Chassis Plating: +Defense (5-210 bonus)\n"
                "• Energy Cores: +Attack (3-12 bonus) & Max Energy (50-210 bonus)\n"
                "• Utility Modules: +Max Happiness (50-180 bonus) & Max Maintenance (50-170 bonus)\n\n"
                
                "**Total Stats Display** - Shown in `/pet` command\n"
                "• Combines base stats + equipment bonuses\n"
                "• Real-time calculation includes all modifiers\n"
                "• Used for all battle and mission calculations"
            ),
            inline=False
        )
        
        embed.set_footer(text="Use the buttons below to navigate between pages • Page 1/5: Pet Stats")
        return embed
    
    def create_page_2_battles(self):
        """Page 2: Battle System - Comprehensive battle mechanics"""
        embed = discord.Embed(
            title="⚔️ Page 2/4: Battle System",
            description="Complete guide to all battle types and combat mechanics",
            color=0xff6b6b
        )
        
        # Battle Types
        embed.add_field(
            name="🥊 Battle Types Overview",
            value=(
                "**Solo Battles** - 1v1 combat vs Enemy\n"
                "• Use `/battle` to start\n"
                "• 1 player vs Enemy\n"
                "• Rewards: Experience, Energon, Equipment drops\n"
                "• Best for individual progression and practice\n\n"
                
                "**Group Battles** - 2-4v1 combat vs Enemy\n"
                "• Use `/group_battle` to start\n"
                "• 2-4 players vs Enemy\n"
                "• Rewards: Experience, Energon, Equipment drops"
                "• Better for harder enemies at lower levels\n"
                "• Requires coordination and teamwork\n\n"
                
                "**PvP Battles** - Player vs Player combat\n"
                "• Use `/pvp` to join lobby\n"
                "• Modes: 1v1, 2v2, 3v3, 4v4, Free-for-All\n"
                "• Test your pet's strength against other players\n"
                "• Ranked system with leaderboards\n\n"
                
                "**Mega Fights** - Combiner team battles\n"
                "• Special Pet Combiner Mega-Fights\n"
                "• Totals all 4 pet's stats in Combiner into 1 Mega-Pet\n"
                "• Essentially a 4v4 but operates like a 1v1!"
            ),
            inline=False
        )
        
        # Combat Mechanics
        embed.add_field(
            name="⚡ Combat Mechanics",
            value=(
                "**Turn-Based System**\n"
                "• PvE: Simple turn order, all players act each round\n"
                "• PvP: Pure turn-based, all alive players act simultaneously\n"
                "• Actions: Attack, Defend, Charge, Flee\n"
                "• Each round: All alive players must select actions before processing\n\n"
                
                "**Unified Damage System**\n"
                "• Critical hits: 5% chance for 50% bonus damage\n"
                "• Charge system: Build up multipliers for stronger attacks\n"
                "• Defense mechanics: Defending players get 2x defense effectiveness\n"
                "• Parry system: High defense can reflect damage back to attacker\n"
                "• HP = Energy + Maintenance + Happiness (combined resources)\n\n"
                
                "**Damage Calculation**\n"
                "• Attack damage = Attack stat × charge multiplier\n"
                "• Defending: Defense × 2.0 vs attack (can parry)\n"
                "• Not defending: Defense ÷ 2 vs attack (reduced effectiveness)\n"
                "• Perfect block: Defense = Attack (no damage to either)\n"
                "• Parry: Defense > Attack (reflect excess as damage)\n\n"
                
                "**Battle Flow**\n"
                "• Setup: Load participants and calculate stats\n"
                "• Action phase: All players choose actions simultaneously\n"
                "• Resolution: Process all actions at once using unified system\n"
                "• Victory: Rewards based on performance and difficulty"
            ),
            inline=False
        )
        
        # Rewards & Progression
        embed.add_field(
            name="🏕️ Battle Lobbies",
            value=(
                "**Enemy Selection System**\n"
                "• Choose enemy type: Monster - Boss - Titan\n"
                "• Select rarity: Common - Uncommon - Rare - Epic - Legendary - Mythic\n"
                "• Higher Type & Rarity = Stronger Enemies = Better Rewards\n"
                "• Interactive selection with emoji indicators\n"
                "• Real Transformers™️ appear as Titan enemies\n\n"
                
                "**PvP Lobby System**\n"
                "• Battle modes: 1v1, 2v2, 3v3, 4v4, and FFA (Free-for-All)\n"
                "• Join/Leave system with player limits\n"
                "• Team battles assign random team names\n"
                "• Creator controls when battle starts\n"
                "• Auto-balances teams if uneven\n"
                "• 1-hour timeout for inactive lobbies"
            ),
            inline=False
        )
        
        embed.set_footer(text="Use the buttons below to navigate between pages • Page 2/5: Battle System")
        return embed
    
    def create_page_3_levels_equipment(self):
        """Page 3: Levels & Equipment System"""
        embed = discord.Embed(
            title="📈 Page 3/4: Levels & Equipment System",
            description="Complete guide to pet leveling and equipment mechanics",
            color=0x4ecdc4
        )
        
        # Leveling System
        embed.add_field(
            name="📊 Leveling System (Max Level 500)",
            value=(
                "**Experience Requirements**\n"
                "• XP needed increases with each level\n"
                "• Exponential scaling: 100 XP per level (1-100), then 2000+ XP\n"
                "• Different activities provide varying XP amounts\n"
                "• Daily bonuses help accelerate progression\n\n"
                
                "**Level Stages & Progression**\n"
                "• Stage 1 (Lv.1-100): Foundation building\n"
                "  - Stat gains: +1-3 per level (faction-based)\n"
                "  - Focus: Basic battles and equipment\n"
                "  - Progress factor: 1.0x\n\n"
                
                "• Stage 2 (Lv.101-200): Intermediate growth\n"
                "  - Stat gains: +2-5 per level (faction-based)\n"
                "  - Focus: Group battles and advanced equipment\n"
                "  - Progress factor: 1.2x\n\n"
                
                "• Stage 3 (Lv.201-300): Advanced development\n"
                "  - Stat gains: +3-7 per level (faction-based)\n"
                "  - Focus: Mega fights and PvP competition\n"
                "  - Progress factor: 1.5x\n\n"
                
                "• Stage 4 (Lv.301-400): Expert level\n"
                "  - Stat gains: +4-9 per level (faction-based)\n"
                "  - Focus: High-tier equipment and elite battles\n"
                "  - Progress factor: 2.0x\n\n"
                
                "• Stage 5 (Lv.401-500): Master level\n"
                "  - Stat gains: +5-12 per level (faction-based)\n"
                "  - Focus: Endgame content and leaderboards\n"
                "  - Progress factor: 2.5x\n\n"
                
                "**Faction-Based Stat Growth**\n"
                "• Autobots: Defense & Happiness focus\n"
                "• Decepticons: Attack & Enery focus\n"
                "• Random bonuses applied each level up\n"
                "• Stat gains accumulate progressively"
            ),
            inline=False
        )
        
        # Equipment System
        embed.add_field(
            name="⚙️ Equipment Types & Bonuses",
            value=(
                "**Chassis Plating** - Defense\n"
                "• Common: +5-25 Defense\n"
                "• Uncommon: +35-55 Defense\n"
                "• Rare: +65-85 Defense\n"
                "• Epic: +95-120 Defense\n"
                "• Legendary: +130-150 Defense\n"
                "• Mythic: +180-230 Defense\n\n"
                
                "**Energy Cores** - Energy & Attack\n"
                "• Common: +50-95 Energy, +3-5 Attack\n"
                "• Uncommon: +150-250 Energy, +8-15 Attack\n"
                "• Rare: +350-400 Energy, +25-38 Attack\n"
                "• Epic: +600-720 Energy, +58-78 Attack\n"
                "• Legendary: +1200-1600 Energy, +180-220 Attack\n"
                "• Mythic: +2000-2600 Energy, +300-360 Attack\n\n"
                
                "**Utility Modules** - Happiness & Maintenance\n"
                "• Common: +50-90 Happiness, +50-80 Maintenance\n"
                "• Uncommon: +140-195 Happiness, +120-170 Maintenance\n"
                "• Rare: +320-430 Happiness, +300-380 Maintenance\n"
                "• Epic: +600-850 Happiness, +560-760 Maintenance\n"
                "• Legendary: +1200-1400 Happiness, +1200-1400 Maintenance\n"
                "• Mythic: +1800-2500 Happiness, +1800-2500 Maintenance\n\n"
                
                "**Rarity Progression**: Common → Uncommon → Rare → Epic → Legendary → Mythic\n"
                "Higher rarities provide exponentially better bonuses!"
            ),
            inline=False
        ) 
        
        embed.set_footer(text="Use the buttons below to navigate between pages • Page 3/5: Levels & Equipment")
        return embed
    
    def create_page_4_rpg(self):
        """Page 4: RPG System"""
        embed = discord.Embed(
            title="🎲 Page 4/5: RPG System",
            description="Complete guide to the RPG elements and adventure system",
            color=0x9b59b6
        )
        
        # RPG Overview
        embed.add_field(
            name="🗺️ RPG Adventure System",
            value=(
                "**AI-Powered Adventure Mechanics**\n"
                "• Dynamic events generated by Google Gemini AI\n"
                "• Story continuity tracking across adventures\n"
                "• Resource costs scale with pet level and equipment\n"
                "• Success chances based on stats + equipment bonuses\n\n"
                
                "**Adventure Types**\n"
                "• 🎯 AI Events - Dynamic challenges with resource costs\n"
                "• ⚔️ AI Battles - Combat encounters with story context\n"
                "• 📖 AI Stories - Non-combat narrative progression\n"
                "• 🎲 Random - AI chooses between event/battle/story\n\n"
                
                "**Resource Management**\n"
                "• Energy - Required for physical challenges\n"
                "• Maintenance - Needed for repairs and tech challenges\n"
                "• Happiness - Social and diplomatic encounters\n"
                "• Costs scale with effective level (base level + equipment)"
            ),
            inline=False
        )
        
        embed.set_footer(text="Use the buttons below to navigate between pages • Page 4: RPG System • Next: All Commands")
        return embed

    def create_page_5_all_commands(self):
        """Page 5: All Pet Commands"""
        embed = discord.Embed(
            title="📋 Page 5/5: All Pet Commands",
            description="Complete list of all available pet commands across all systems",
            color=0x1abc9c
        )
        
        # Pet Management Commands
        embed.add_field(
            name="🐾 Pet Management Commands",
            value=(
                "**Core Pet Commands**\n"
                "• `/get_pet <faction>` - Obtain digital pet (Autobot/Decepticon)\n"
                "• `/kill` - Permanently delete your pet (confirmation required)\n"
                "• `/pet` - View your pet's current status and stats\n"
                "• `/rename_pet <new_name>` - Rename your digital pet\n"
                "• `/pet_equip` - Interactive equipment selection and equipping\n"
                "• `/pet_equipment` - View all your pet items with pagination\n"
                "• `/pet_unequip <slot>` - Unequip items (chassis/energy/utility)\n\n"
                
                "**Pet Care Commands**\n"
                "• `/charge_pet [time]` - Charge your pet's energy (50%, 75%, 100%)\n"
                "• `/play [time]` - Play with your pet to increase happiness (50%, 75%, 100%)\n"
                "• `/repair_pet [time]` - Repair your pet's maintenance (50%, 75%, 100%)\n"
                "• Charge, Play & Repair commands have cooldown for time selected"
            ),
            inline=False
        )
        
        # Battle Commands
        embed.add_field(
            name="⚔️ Action Commands",
            value=(
                "**Solo & Group Battles**\n"
                "• `/battle` - Start a solo battle against monsters/bosses/titans\n"
                "• `/group_battle` - Start a group battle for up to 4 players\n"
                "• `/battle_stats [member]` - View comprehensive battle statistics\n"
                "• `/pvp <mode>` - Start a PvP battle lobby (1v1, 2v2, 3v3, 4v4, ffa)\n"
                "• `/mega_fight` - Challenge another combiner team to a Mega-Fight\n"
                "• `/train <difficulty>` - Train your pet"
                "• `/mission <difficulty>` - Send your pet on missions for XP and energon"
            ),
            inline=False
        )

        # RPG System Commands
        embed.add_field(
            name="🎲 RPG Adventure Commands",
            value=(
                "**AI-Powered Adventures**\n"
                "• `/cyber_random` - AI randomly chooses adventure type\n"
                "• `/cyber_battle` - Combat-focused AI encounters\n"
                "• `/cyber_event` - Resource challenge events\n"
                "• `/cyber_story` - Narrative story segments\n"
                "• `/cyber_info` - Information about the Cybertronian RPG system\n\n"
                
                "**Adventure Sessions**\n"
                "• `/start_cyberchronicles` - Begin solo AI adventure session\n"
                "• `/stop_cyberchronicles` - Stop current adventure session\n"
                "• Dynamic events with Google Gemini AI generation"
            ),
            inline=False
        )
        
        embed.set_footer(text="Use the buttons below to navigate • Page 5: All Commands • Complete command reference")
        return embed

# Navigation Button Classes
class PreviousPageButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.primary, emoji="⬅️", label="Previous")
    
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if view.current_page > 1:
            view.current_page -= 1
            await view.update_page(interaction)
        else:
            await interaction.response.defer()

class NextPageButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.primary, emoji="➡️", label="Next")
    
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if view.current_page < 5:
            view.current_page += 1
            await view.update_page(interaction)
        else:
            await interaction.response.defer()

class PageIndicatorButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.secondary, disabled=True, label="Page 1/5")
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

class CloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.danger, emoji="❌", label="Close")
    
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        await interaction.message.delete()
        view.stop()

# Add the update_page method to PetInfoView
async def update_page_method(self, interaction: discord.Interaction):
    """Update the embed to show the current page"""
    if self.current_page == 1:
        embed = self.create_page_1_stats()
    elif self.current_page == 2:
        embed = self.create_page_2_battles()
    elif self.current_page == 3:
        embed = self.create_page_3_levels_equipment()
    elif self.current_page == 4:
        embed = self.create_page_4_rpg()
    elif self.current_page == 5:
        embed = self.create_page_5_all_commands()
    
    # Update the page indicator button
    for item in self.children:
        if isinstance(item, PageIndicatorButton):
            item.label = f"Page {self.current_page}/5"
            break
    
    await interaction.response.edit_message(embed=embed, view=self)

# Add the method to the PetInfoView class
PetInfoView.update_page = update_page_method
 
 # Helper function for role checking
def has_cybertronian_role(member: discord.Member) -> bool:
    """Check if member has Cybertronian role"""
    if not member or not member.roles:
        return False
    
    cybertronian_role_ids = []
    for role in ['Autobot', 'Decepticon', 'Maverick', 'Cybertronian_Citizen']:
        role_id = ROLE_IDS.get(role)
        if isinstance(role_id, list):
            cybertronian_role_ids.extend(role_id)
        elif role_id:
            cybertronian_role_ids.append(role_id)
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
            
        # Wait for pet system to be available (with timeout)
        max_wait = 10  # seconds
        waited = 0
        while not hasattr(bot_instance, 'pet_system') and waited < max_wait:
            await asyncio.sleep(0.5)
            waited += 0.5
            
        if not hasattr(bot_instance, 'pet_system'):
            logger.error("Pet system not found after waiting! Make sure pets_system.py is loaded first.")
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