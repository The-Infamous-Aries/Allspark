import discord
import random
import asyncio
from typing import List

# Import constants from energon_system
from Systems.EnergonPets.energon_system import SLOT_THEMES, DIFFICULTY_MULTIPLIERS

class SlotMachineView(discord.ui.View):
    """Interactive slot machine view with spinning animation."""
    
    def __init__(self, bot, user: discord.Member, mode: str, difficulty: str, bet: int, 
                 current_energon: int, slot_emojis: List[str], multiplier: int):
        super().__init__(timeout=300)  # 5 minute timeout
        self.bot = bot
        self.user = user
        self.mode = mode
        self.difficulty = difficulty
        self.bet = bet
        self.current_energon = current_energon
        self.slot_emojis = slot_emojis
        self.multiplier = multiplier
        self.message = None
        self.game_finished = False
    
    async def on_timeout(self):
        """Handle view timeout."""
        for item in self.children:
            item.disabled = True
        if self.message and not self.game_finished:
            try:
                timeout_embed = discord.Embed(
                    title="⏰ Slot Machine Timed Out",
                    description="The slot machine has been reset due to inactivity.",
                    color=discord.Color.orange()
                )
                await self.message.edit(embed=timeout_embed, view=self)
            except:
                pass
    
    @discord.ui.button(label="🎰 SPIN", style=discord.ButtonStyle.success, emoji="🎰")
    async def spin_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle spin button click."""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ This isn't your slot machine!", ephemeral=True)
            return
        
        button.disabled = True
        await interaction.response.edit_message(view=self)
        await self.perform_spin(interaction)
    
    async def perform_spin(self, interaction: discord.Interaction):
        """Perform the slot machine spin animation with 6 random reels."""
        # Ensure message reference is properly set
        if not self.message:
            self.message = await interaction.original_response()
            
        embed = discord.Embed(
            title=f"🎰 SLOT MACHINE - {self.difficulty.upper()} 🎰",
            color=discord.Color.gold() if self.mode == "bet" else discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        embed.set_author(
            name=f"{self.user.display_name} is spinning!",
            icon_url=self.user.display_avatar.url
        )
        
        # 6-stage spinning animation with 1.5-second intervals
        animation_stages = [
            "**🎰 STAGE 1: Spinning... 🎰**",
            "**⚡ STAGE 2: Reels turning! ⚡**",
            "**🎯 STAGE 3: Building momentum... 🎯**",
            "**🐢 STAGE 4: Slowing down... 🐢**",
            "**🔮 STAGE 5: Finalizing... 🔮**",
            "**🌟 STAGE 6: Revealing result! 🌟**"
        ]
        
        for stage_num, status in enumerate(animation_stages):
            try:
                # Generate random reel for this stage
                current_slots = [random.choice(self.slot_emojis) for _ in range(3)]
                
                # Make emojis appear much bigger using large text and spacing
                slots_display = f"🎰  {current_slots[0]}  {current_slots[1]}  {current_slots[2]}  🎰"
                
                embed.clear_fields()
                
                if self.mode == "bet":
                    embed.add_field(name="💰 Bet", value=f"**{self.bet}** Energon", inline=True)
                    embed.add_field(name="⚡ Your Energon", value=f"**{self.current_energon}** Energon", inline=True)
                else:
                    embed.add_field(name="🎮 Mode", value="**Just for Fun**", inline=True)
                    embed.add_field(name="🎯 Stakes", value="**No Risk**", inline=True)
                
                # Add stage counter
                embed.add_field(name="🎲 Animation", value=f"**Stage {stage_num + 1}/6**", inline=True)
                
                # Display reels as large, prominent text
                embed.add_field(name="🎰 SLOT REELS", value=slots_display, inline=False)
                embed.add_field(name="🎰 Status", value=status, inline=False)
                
                # Add visual progress bar
                progress_bar = "🟩" * (stage_num + 1) + "⬜" * (6 - stage_num - 1)
                elapsed_time = (stage_num + 1) * 1.5
                embed.set_footer(text=f"{progress_bar} Stage {stage_num + 1}/6 • {elapsed_time:.1f}s", icon_url=self.bot.user.display_avatar.url)
                
                # Force update the embed with new content
                await self.message.edit(embed=embed, view=self)
                
                await asyncio.sleep(1.5)  # 1.5 seconds per stage
                
            except discord.HTTPException as e:
                if e.status == 429:
                    await asyncio.sleep(0.1)
                    continue
                else:
                    break
            except Exception:
                break
        
        # Brief pause before final result
        await asyncio.sleep(0.5)
        
        # Show final result
        await self.show_results(self.slot_emojis)
    
    async def show_results(self, slot_emojis: List[str]):
        """Show the final results of the slot machine spin with bigger emojis."""
        final_slots = [random.choice(slot_emojis) for _ in range(3)]
        
        # Make final reels appear much bigger
        slots_display = f"🎰  {final_slots[0]}  {final_slots[1]}  {final_slots[2]}  🎰"
        
        # Check win conditions
        all_match = len(set(final_slots)) == 1
        two_match = len(set(final_slots)) == 2
        
        # Calculate winnings
        winnings = 0
        if all_match:
            winnings = self.bet * (self.multiplier * 3)
        elif two_match:
            winnings = self.bet * self.multiplier
        
        # Create result embed with bigger emoji presentation
        embed = discord.Embed(
            title=f"🎰 SLOT MACHINE - {self.difficulty.upper()} 🎰",
            color=discord.Color.gold() if self.mode == "bet" else discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        embed.set_author(
            name=f"{self.user.display_name}'s Results",
            icon_url=self.user.display_avatar.url
        )
        
        if self.mode == "bet":
            embed.add_field(name="💰 Bet", value=f"**{self.bet}** Energon", inline=True)
            
            if winnings > 0:
                embed.add_field(name="🏆 Winnings", value=f"**{winnings}** Energon", inline=True)
                embed.add_field(name="⚡ New Balance", value=f"**{self.current_energon + winnings}** Energon", inline=True)
                # Display final reels as large, prominent text
                embed.add_field(name="🎯 FINAL REELS", value=slots_display, inline=False)
                embed.add_field(name="✨ Result", value=f"**JACKPOT!** {'🌟 ' * 3 if all_match else '⭐ ' * 2}", inline=False)
            else:
                embed.add_field(name="💸 Lost", value=f"**{self.bet}** Energon", inline=True)
                embed.add_field(name="⚡ New Balance", value=f"**{self.current_energon}** Energon", inline=True)
                # Display final reels as large, prominent text
                embed.add_field(name="🎯 FINAL REELS", value=slots_display, inline=False)
                embed.add_field(name="😢 Result", value="**Better luck next time!**", inline=False)
        else:
            embed.add_field(name="🎮 Mode", value="**Just for Fun**", inline=True)
            # Display final reels as large, prominent text
            embed.add_field(name="🎯 FINAL REELS", value=slots_display, inline=False)
            if all_match or two_match:
                embed.add_field(name="✨ Result", value=f"**WINNER!** {'🌟 ' * 3 if all_match else '⭐ ' * 2}", inline=False)
            else:
                embed.add_field(name="😢 Result", value="**Better luck next time!**", inline=False)
        
        # Update game state
        self.game_finished = True
        
        # Update slot machine statistics in user data
        if self.mode == "bet":
            try:
                from Systems.user_data_manager import user_data_manager
                
                # Get current slot machine data
                slot_data = await user_data_manager.get_slot_machine_data(str(self.user.id), self.user.display_name)
                
                # Update statistics
                slot_data["total_games_played"] += 1
                slot_data["games_by_difficulty"][self.difficulty] += 1
                
                if winnings > 0:
                    slot_data["total_winnings"] += winnings
                    slot_data["winnings_by_difficulty"][self.difficulty] += winnings
                    
                    if all_match:
                        slot_data["jackpots_won"] += 1
                    elif two_match:
                        slot_data["two_matches_won"] += 1
                    
                    if winnings > slot_data["highest_win"]:
                        slot_data["highest_win"] = winnings
                else:
                    slot_data["total_losses"] += self.bet
                
                if self.bet > slot_data["highest_bet"]:
                    slot_data["highest_bet"] = self.bet
                
                # Update main energon balance in user data
                energon_data = await user_data_manager.get_energon_data(str(self.user.id))
                new_energon = energon_data.get('energon', 0) + (winnings if winnings > 0 else 0)
                energon_data['energon'] = new_energon
                await user_data_manager.save_energon_data(str(self.user.id), energon_data)
                
                # Save updated slot machine data
                await user_data_manager.save_slot_machine_data(str(self.user.id), self.user.display_name, slot_data)
                
            except Exception as e:
                print(f"Error updating slot machine statistics: {e}")
        
        # Show play again button
        play_again_view = PlayAgainView(self.bot, self.user, self.mode, self.difficulty, 
                                      self.current_energon + (winnings if winnings > 0 else 0))
        await self.message.edit(embed=embed, view=play_again_view)

class PlayAgainView(discord.ui.View):
    """View for playing slots again with difficulty selection."""
    
    def __init__(self, bot, user: discord.Member, mode: str, difficulty: str, current_energon: int):
        super().__init__(timeout=180)  # 3 minute timeout
        self.bot = bot
        self.user = user
        self.mode = mode
        self.difficulty = difficulty
        self.current_energon = current_energon
        self.message = None
    
    @discord.ui.button(label="🎮 Play Again", style=discord.ButtonStyle.success)
    async def play_again(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle play again button."""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        # Create difficulty select menu
        difficulty_select = discord.ui.Select(
            placeholder="Choose Difficulty",
            options=[
                discord.SelectOption(label="Easy", description="Skills Theme - Lower Risk, Lower Reward", emoji="🟢"),
                discord.SelectOption(label="Medium", description="Characters Theme - Balanced Risk/Reward", emoji="🟡"),
                discord.SelectOption(label="Hard", description="Zodiac Theme - Higher Risk, Higher Reward", emoji="🔴")
            ]
        )
        
        async def difficulty_callback(interaction: discord.Interaction):
            difficulty = difficulty_select.values[0].lower()
            
            # Defer the interaction to prevent timeout
            await interaction.response.defer()
            
            if self.mode == "bet":
                # Create bet amount modal for betting mode
                modal = discord.ui.Modal(title="Place Your Bet")
                bet_input = discord.ui.TextInput(
                    label="Bet Amount",
                    placeholder="Enter bet (10-1000)",
                    min_length=1,
                    max_length=4
                )
                modal.add_item(bet_input)
                
                async def modal_callback(interaction: discord.Interaction):
                    try:
                        bet = int(bet_input.value)
                        if 10 <= bet <= 1000:
                            # Get latest energon balance from user data
                            from Systems.user_data_manager import UserDataManager
                            user_data_manager = UserDataManager()
                            energon_data = await user_data_manager.get_energon_data(str(self.user.id))
                            current_energon = energon_data.get('energon', 0)
                            await EnergonCommands.start_slot_game(interaction, self.mode, difficulty, bet, self.user, current_energon)
                        else:
                            await interaction.response.send_message("❌ Bet must be between 10-1000 Energon!", ephemeral=True)
                    except ValueError:
                        await interaction.response.send_message("❌ Please enter a valid number!", ephemeral=True)
                
                modal.on_submit = modal_callback
                await interaction.followup.send_modal(modal)
            else:
                # Access the slot game through the bot's cog system
                energon_cog = interaction.client.get_cog('EnergonCommands')
                if energon_cog and hasattr(energon_cog, 'start_slot_game'):
                    await energon_cog.start_slot_game(interaction, self.mode, difficulty, 0, self.user, 0)
                else:
                    await interaction.response.send_message("Slot game system is currently unavailable.", ephemeral=True)
        
        difficulty_select.callback = difficulty_callback
        view = discord.ui.View()
        view.add_item(difficulty_select)
        
        await interaction.response.send_message("Choose your difficulty:", view=view, ephemeral=True)