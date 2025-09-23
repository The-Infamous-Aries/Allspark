import discord
from discord.ext import commands
from discord.ui import View, Button
from typing import List, Dict, Any
import asyncio

class PaginatedRecruitmentView(View):
    def __init__(self, nations: List[Dict[str, Any]], recruit_cog, author_id: int):
        super().__init__(timeout=300)  # 5 minute timeout
        self.nations = nations
        self.recruit_cog = recruit_cog
        self.author_id = author_id
        self.current_page = 0
        self.total_pages = (len(nations) + 4) // 5  # Show all nations, 5 nations per page
        self.message = None
        
        # Calculate page ranges - 5 nations per page for all available nations
        self.pages = []
        for i in range(self.total_pages):
            start_idx = i * 5
            end_idx = min(start_idx + 5, len(nations))
            self.pages.append(nations[start_idx:end_idx])
    
    def get_activity_indicator(self, last_active_str: str) -> str:
        """Convert last active datetime string to emoji indicator showing recency"""
        if not last_active_str or last_active_str == "None":
            return "❓ Unknown"
        
        try:
            from datetime import datetime, timezone
            
            # Parse the datetime string
            last_active_str = last_active_str.replace('Z', '+00:00')
            last_active_dt = datetime.fromisoformat(last_active_str)
            now = datetime.now(timezone.utc)
            
            # Calculate time difference
            time_diff = now - last_active_dt
            hours_ago = time_diff.total_seconds() / 3600
            
            # Return appropriate emoji based on recency
            if hours_ago < 1:
                return "🟢 Online now"
            elif hours_ago < 6:
                return f"🟢 {int(hours_ago)}h ago"
            elif hours_ago < 24:
                return f"🟡 {int(hours_ago)}h ago"
            elif hours_ago < 48:
                return f"🟠 {int(hours_ago // 24)}d {int(hours_ago % 24)}h ago"
            elif hours_ago < 168:  # 1 week
                days_ago = int(hours_ago // 24)
                return f"🟠 {days_ago}d ago"
            else:
                weeks_ago = int(hours_ago // 168)
                return f"🔴 {weeks_ago}w+ ago"
                
        except Exception:
            return "❓ Unknown"

    def create_embed(self) -> discord.Embed:
        """Create embed for current page"""
        if not self.pages:
            embed = discord.Embed(
                title="📋 No Nations Available",
                description="No unallied nations are currently available for recruitment.",
                color=0xff6b6b
            )
            return embed
        
        current_nations = self.pages[self.current_page]
        
        embed = discord.Embed(
            title=f"🌍 Unallied Nations - Page {self.current_page + 1}/{self.total_pages}",
            description=f"Showing {len(current_nations)} of {len(self.nations)} nations ready for recruitment",
            color=0x4CAF50
        )
        
        # Build the nations field
        nations_text = ""
        for i, nation in enumerate(current_nations, 1):
            nation_id = nation['nation_id']
            nation_name = nation['nation_name']
            leader_name = nation['leader_name']
            score = nation['score']
            cities = nation['cities_count']
            activity_indicator = self.get_activity_indicator(nation.get('last_active'))
            
            nations_text += (
                f"**{i}.** [{nation_name}](https://politicsandwar.com/nation/id={nation_id})\n"
                f"   👑 Leader: {leader_name}\n"
                f"   📊 Score: {score:,.0f} | 🏙️ Cities: {cities}\n"
                f"   {activity_indicator}\n\n"
            )
        
        if nations_text:
            embed.add_field(
                name="Nations on this page:",
                value=nations_text,
                inline=False
            )
        
        embed.set_footer(
            text=f"Use buttons to navigate | Mass recruit sends to all {len(self.nations)} shown nations"
        )
        
        return embed
    
    def update_buttons(self):
        """Update button states based on current page"""
        # Previous button
        prev_button = self.children[0]
        prev_button.disabled = self.current_page == 0
        
        # Next button
        next_button = self.children[1]
        next_button.disabled = self.current_page >= self.total_pages - 1
        
        # Page indicator (now at index 2)
        page_button = self.children[2]
        page_button.label = f"Page {self.current_page + 1}/{self.total_pages}"
    
    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.gray)
    async def previous_page(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ You can't use these buttons!", 
                ephemeral=True
            )
            return
            
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.gray)
    async def next_page(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ You can't use these buttons!", 
                ephemeral=True
            )
            return
            
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="Page 1/1", style=discord.ButtonStyle.secondary, disabled=True)
    async def page_indicator(self, interaction: discord.Interaction, button: Button):
        # This button is just for display, no action needed
        await interaction.response.defer()
     
    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.secondary)
    async def refresh_nations(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ You can't use these buttons!", 
                ephemeral=True
            )
            return
            
        await interaction.response.defer()
        
        # Fetch all new nations (up to 15000)
        new_nations = await self.recruit_cog.get_unallied_nations(15000)
        
        if not new_nations:
            embed = discord.Embed(
                title="❌ No Nations Available",
                description="No new unallied nations found. Try again later.",
                color=0xff6b6b
            )
            try:
                await interaction.message.edit(embed=embed, view=None)
            except discord.errors.Forbidden:
                # If we can't edit the original message, send a new one
                await interaction.followup.send(embed=embed)
            self.stop()
            return
        
        # Create new view with fresh nations
        new_view = PaginatedRecruitmentView(new_nations, self.recruit_cog, self.author_id)
        new_embed = new_view.create_embed()
        
        try:
            await interaction.message.edit(embed=new_embed, view=new_view)
        except discord.errors.Forbidden:
            # If we can't edit the original message, send a new one
            await interaction.followup.send(embed=new_embed)
        self.stop()
    
    @discord.ui.button(label="🎯 Recruit This Page", style=discord.ButtonStyle.green)
    async def recruit_page(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ You can't use these buttons!", 
                ephemeral=True
            )
            return
            
        if not self.pages or self.current_page >= len(self.pages):
            await interaction.response.send_message(
                "❌ No nations on this page!", 
                ephemeral=True
            )
            return
        
        current_nations = self.pages[self.current_page]
        if not current_nations:
            await interaction.response.send_message(
                "❌ No nations on this page!", 
                ephemeral=True
            )
            return
        
        # Start background recruitment task
        try:
            task_id = await self.recruit_cog.start_background_recruitment(
                current_nations, 
                interaction.user.id
            )
            
            embed = discord.Embed(
                title=f"🚀 Background Recruitment Started",
                description=f"Recruitment task started for page {self.current_page + 1}",
                color=0x4CAF50
            )
            
            embed.add_field(
                name="Task Details",
                value=f"**Task ID:** `{task_id}`\n"
                      f"**Nations:** {len(current_nations)}\n"
                      f"**Status:** Running in background",
                inline=False
            )
            
            embed.add_field(
                name="📊 Track Progress",
                value=f"Use `/recruit_status {task_id}` to check progress\n"
                      f"Use `/recruit_status` to see all active tasks\n"
                      f"Use `/recruit_cancel {task_id}` to cancel if needed",
                inline=False
            )
            
            embed.add_field(
                name="✅ Bot Availability",
                value="The bot remains fully functional while recruitment runs in the background!",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Failed to Start Background Task",
                description=f"Error: {str(e)}",
                color=0xff6b6b
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🚀 Mass Recruit All Shown", style=discord.ButtonStyle.red)
    async def mass_recruit_all(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ You can't use these buttons!", 
                ephemeral=True
            )
            return
            
        if not self.nations:
            await interaction.response.send_message(
                "❌ No nations available for recruitment!", 
                ephemeral=True
            )
            return
        
        # Start background recruitment task for all nations
        try:
            task_id = await self.recruit_cog.start_background_recruitment(
                self.nations, 
                interaction.user.id
            )
            
            embed = discord.Embed(
                title="🚀 Mass Background Recruitment Started",
                description="Large-scale recruitment task started for all displayed nations",
                color=0x4CAF50
            )
            
            embed.add_field(
                name="Task Details",
                value=f"**Task ID:** `{task_id}`\n"
                      f"**Total Nations:** {len(self.nations)}\n"
                      f"**Pages:** {len(self.pages)}\n"
                      f"**Status:** Running in background",
                inline=False
            )
            
            embed.add_field(
                name="📊 Track Progress",
                value=f"Use `/recruit_status {task_id}` to check progress\n"
                      f"Use `/recruit_status` to see all active tasks\n"
                      f"Use `/recruit_cancel {task_id}` to cancel if needed",
                inline=False
            )
            
            embed.add_field(
                name="⚡ Estimated Time",
                value=f"Approximately {len(self.nations) * 2.5 / 60:.1f} minutes\n"
                      f"(2-3 seconds per nation to prevent API spam)",
                inline=False
            )
            
            embed.add_field(
                name="✅ Bot Availability",
                value="The bot remains fully functional while mass recruitment runs in the background!\n"
                      f"You can continue using all other commands and features.",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Failed to Start Mass Recruitment",
                description=f"Error: {str(e)}",
                color=0xff6b6b
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="❌ Close", style=discord.ButtonStyle.secondary)
    async def close_view(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ You can't use these buttons!", 
                ephemeral=True
            )
            return
            
        # Perform cache cleanup
        cleanup_count = await self._cleanup_view_cache()
        
        embed = discord.Embed(
            title="✅ Recruitment View Closed",
            description=f"The recruitment interface has been closed.\n{cleanup_count} cache entries cleaned up.",
            color=0x95a5a6
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()
    
    async def _cleanup_view_cache(self) -> int:
        """Clean up view-specific cache and return count of cleaned items"""
        cleanup_count = 0
        
        try:
            # Clear view-specific data
            if hasattr(self, 'nations'):
                self.nations.clear()
                cleanup_count += 1
            
            if hasattr(self, 'pages'):
                self.pages.clear()
                cleanup_count += 1
            
            # Clear any cached recruitment data for this user
            if hasattr(self.recruit_cog, 'active_tasks'):
                user_tasks = [task_id for task_id, task in self.recruit_cog.active_tasks.items() 
                             if task.user_id == self.author_id]
                
                for task_id in user_tasks:
                    # Cancel the task if it's still running
                    task = self.recruit_cog.active_tasks[task_id]
                    if task.task_handle and not task.task_handle.done():
                        task.task_handle.cancel()
                        task.status = "cancelled"
                    
                    # Remove from active tasks
                    del self.recruit_cog.active_tasks[task_id]
                    cleanup_count += 1
            
            # Force garbage collection of view data
            self.current_page = 0
            self.total_pages = 0
            
        except Exception as e:
            print(f"⚠️ Error during cache cleanup: {e}")
        
        return cleanup_count
    
    async def on_timeout(self):
        """Called when view times out"""
        if self.message:
            try:
                await self.message.edit(view=None)
            except discord.errors.Forbidden:
                # If we can't edit due to permissions, just ignore
                pass
            except Exception:
                # Ignore any other errors during cleanup
                pass