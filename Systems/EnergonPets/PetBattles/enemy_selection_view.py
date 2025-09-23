import discord
import asyncio
from typing import Optional

# Import emoji mappings from battle_system
from .battle_system import MONSTER_EMOJIS, RARITY_EMOJIS

class EnemySelectionView(discord.ui.View):
    """Interactive view for selecting enemy type and rarity in battles"""
    
    def __init__(self, ctx, battle_type="solo"):
        super().__init__(timeout=600)
        self.ctx = ctx
        self.battle_type = battle_type
        self.selected_enemy_type = None
        self.selected_rarity = None
        self.message = None

    def create_selection_embed(self):
        """Create embed showing current selections"""
        embed = discord.Embed(
            title=f"⚔️ {self.battle_type.title()} Battle Setup",
            description="Choose your opponent:",
            color=0x0099ff
        )
        
        # Show current selections with emojis
        type_emoji = MONSTER_EMOJIS.get(self.selected_enemy_type, "❓") if self.selected_enemy_type else "❓"
        rarity_emoji = RARITY_EMOJIS.get(self.selected_rarity, "❓") if self.selected_rarity else "❓"
        
        embed.add_field(
            name="🎯 Enemy Type",
            value=f"{type_emoji} {self.selected_enemy_type.title() if self.selected_enemy_type else 'Not selected'}",
            inline=True
        )
        embed.add_field(
            name="💎 Rarity",
            value=f"{rarity_emoji} {self.selected_rarity.title() if self.selected_rarity else 'Not selected'}",
            inline=True
        )
        
        if self.selected_enemy_type and self.selected_rarity:
            embed.set_footer(text="Click 'Start Battle' to begin! 🚀")
        else:
            embed.set_footer(text="Select both type and rarity to continue...")
            
        return embed

    @discord.ui.select(
        placeholder="🎯 Select enemy type...",
        options=[
            discord.SelectOption(
                label="Monster",
                value="monster",
                emoji=MONSTER_EMOJIS["monster"],
                description="Standard enemies with balanced stats"
            ),
            discord.SelectOption(
                label="Boss",
                value="boss",
                emoji=MONSTER_EMOJIS["boss"],
                description="Powerful single enemies"
            ),
            discord.SelectOption(
                label="Titan",
                value="titan",
                emoji=MONSTER_EMOJIS["titan"],
                description="Real Transformers - ultimate challenges"
            )
        ],
        row=0
    )
    async def select_enemy_type(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle enemy type selection"""
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Only the command user can select!", ephemeral=True)
            return
            
        self.selected_enemy_type = select.values[0]
        
        # Enable rarity select if enemy type is selected
        for child in self.children:
            if isinstance(child, discord.ui.Select) and child.placeholder.startswith("💎"):
                child.disabled = False
                
        try:
            await interaction.response.edit_message(embed=self.create_selection_embed(), view=self)
        except discord.errors.NotFound:
            # Interaction expired, try to edit the message directly
            if self.message:
                await self.message.edit(embed=self.create_selection_embed(), view=self)

    @discord.ui.select(
        placeholder="💎 Select rarity...",
        options=[
            discord.SelectOption(
                label="Common",
                value="common",
                emoji=RARITY_EMOJIS["common"],
                description="Basic enemies - easiest difficulty"
            ),
            discord.SelectOption(
                label="Uncommon",
                value="uncommon",
                emoji=RARITY_EMOJIS["uncommon"],
                description="Stronger foes - moderate difficulty"
            ),
            discord.SelectOption(
                label="Rare",
                value="rare",
                emoji=RARITY_EMOJIS["rare"],
                description="Challenging battles"
            ),
            discord.SelectOption(
                label="Epic",
                value="epic",
                emoji=RARITY_EMOJIS["epic"],
                description="Difficult encounters"
            ),
            discord.SelectOption(
                label="Legendary",
                value="legendary",
                emoji=RARITY_EMOJIS["legendary"],
                description="Powerful adversaries"
            ),
            discord.SelectOption(
                label="Mythic",
                value="mythic",
                emoji=RARITY_EMOJIS["mythic"],
                description="Ultimate challenges - hardest difficulty"
            )
        ],
        row=1,
        disabled=True
    )
    async def select_rarity(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle rarity selection"""
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Only the command user can select!", ephemeral=True)
            return
            
        self.selected_rarity = select.values[0]
        
        # Update embed and enable start button if both selections are made
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.label == "Start Battle":
                child.disabled = not (self.selected_enemy_type and self.selected_rarity)
                
        try:
            await interaction.response.edit_message(embed=self.create_selection_embed(), view=self)
        except discord.errors.NotFound:
            # Interaction expired, try to edit the message directly
            if self.message:
                await self.message.edit(embed=self.create_selection_embed(), view=self)

    @discord.ui.button(label="Start Battle", style=discord.ButtonStyle.green, emoji="⚔️", disabled=True, row=2)
    async def start_battle(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Start the battle with selected options"""
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Only the command user can start the battle!", ephemeral=True)
            return
            
        if not self.selected_enemy_type or not self.selected_rarity:
            await interaction.response.send_message("❌ Please select both enemy type and rarity!", ephemeral=True)
            return
            
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            # Interaction already expired, just continue
            pass
        
        try:
            from Systems.EnergonPets.PetBattles.battle_system import UnifiedBattleView
            
            # Create battle view with selected options
            battle_view = await UnifiedBattleView.create_async(
                self.ctx,
                battle_type=self.battle_type,
                selected_enemy_type=self.selected_enemy_type,
                selected_rarity=self.selected_rarity,
                interaction=interaction
            )
            
            if self.battle_type == "group":
                # Use GroupBattleJoinView for group battles
                from Systems.EnergonPets.PetBattles.battle_system import GroupBattleJoinView
                join_view = GroupBattleJoinView(self.ctx, battle_view)
                embed = battle_view.build_join_embed()
                embed.description = "🎯 Battle setup complete! Waiting for other players to join..."
                await self.message.edit(embed=embed, view=join_view)
                join_view.message = self.message
            else:
                # For solo battles, start immediately
                battle_view.battle_started = True
                battle_view.message = self.message  # Assign the message to battle view
                
                # Ensure monster is displayed in the battle embed
                if battle_view.monster:
                    # COMPLETELY replace the selection view with battle embed (no buttons)
                    embed = battle_view.build_battle_embed("⚔️ Battle Started! Check the channel for actions!")
                    await self.message.edit(embed=embed, view=None)
                    
                    # Start action collection in channel
                    await battle_view.start_action_collection()
                else:
                    # Fallback if monster is missing
                    embed = discord.Embed(
                        title="❌ Battle Error",
                        description="Failed to initialize monster. Please try again.",
                        color=0xff0000
                    )
                    await self.message.edit(embed=embed, view=None)
            
        except Exception as e:
            await self.message.edit(
                content=f"❌ Error starting battle: {str(e)}",
                embed=None,
                view=None
            )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌", row=2)
    async def cancel_battle(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the battle setup"""
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Only the command user can cancel!", ephemeral=True)
            return
            
        try:
            await interaction.response.edit_message(
                content="❌ Battle cancelled.",
                embed=None,
                view=None
            )
        except discord.errors.NotFound:
            # Interaction expired, try to edit message directly
            if self.message:
                await self.message.edit(
                    content="❌ Battle cancelled.",
                    embed=None,
                    view=None
                )

    async def on_timeout(self):
        """Handle timeout"""
        try:
            if self.message:
                await self.message.edit(
                    content="⏰ Battle setup timed out.",
                    embed=None,
                    view=None
                )
        except:
            pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if interaction is valid"""
        return interaction.user.id == self.ctx.author.id