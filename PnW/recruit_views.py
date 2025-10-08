import discord
from discord.ext import commands
from discord.ui import View, Button
from typing import List, Dict, Any
import asyncio
from datetime import datetime, timezone, timedelta

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
    
    def filter_nations_by_activity(self, nations: List[Dict[str, Any]], filter_type: str) -> List[Dict[str, Any]]:
        """Filter nations by activity based on specific ranges"""
        if not nations:
            return []
            
        now = datetime.now(timezone.utc)
        filtered = []
        
        for nation in nations:
            if not nation.get('last_active_dt'):
                continue  # Skip nations with unknown activity
                
            time_diff = now - nation['last_active_dt']
            hours_ago = time_diff.total_seconds() / 3600
            
            if filter_type == "today":
                # Today only: last 24 hours
                if hours_ago <= 24:
                    filtered.append(nation)
            elif filter_type == "week":
                # Last week excluding today: 24-168 hours ago (days 2-7)
                if 24 < hours_ago <= 168:
                    filtered.append(nation)
            elif filter_type == "two_weeks":
                # Last 14 days excluding first week: 168-336 hours ago (days 8-14)
                if 168 < hours_ago <= 336:
                    filtered.append(nation)
                
        return filtered
    
    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.gray)
    async def previous_page(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ You can't use these buttons!", 
                
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
                
            )
            return
            
        await interaction.response.defer()
        
        # Fetch all new nations (up to 15000) - filter out those on cooldown
        new_nations = await self.recruit_cog.get_unallied_nations(15000, filter_cooldown=True)
        
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
    
    @discord.ui.button(label="🟢 Today", style=discord.ButtonStyle.green)
    async def recruit_today(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ You can't use these buttons!", 
                ephemeral=True
            )
            return
        
        # Filter nations active today (last 24 hours)
        today_nations = self.filter_nations_by_activity(self.nations, "today")
        
        if not today_nations:
            await interaction.response.send_message(
                "❌ No nations found that were active today!", 
                ephemeral=True
            )
            return
        
        # Send messages directly with delays
        try:
            # Create initial "starting recruitment" embed
            embed = discord.Embed(
                title="🔄 Starting Recruitment...",
                description=f"**Filter:** Active today (last 24 hours)\n**Nations:** {len(today_nations)}",
                color=0xff9800
            )
            embed.add_field(
                name="📊 Status", 
                value="Sending recruitment messages with 1.5s delays...", 
                inline=False
            )
            embed.add_field(
                name="⚡ Estimated Time",
                value=f"Approximately {len(today_nations) * 1.5 / 60:.1f} minutes\n"
                      f"(1.5 seconds per nation to prevent API spam)",
                inline=False
            )
            
            # Edit the original message to close the nation browser
            await interaction.response.edit_message(embed=embed, view=None)
            
            # Send messages directly with delays
            results = await self.recruit_cog.send_messages_directly(
                today_nations, 
                interaction.user.id,
                interaction.edit_original_response
            )
            
            # Show final results
            await self._show_final_results(interaction, results, "Active today (last 24 hours)")
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Failed to Start Recruitment",
                description=f"Error: {str(e)}",
                color=0xff6b6b
            )
            await interaction.edit_original_response(embed=embed, view=None)
    
    async def _show_final_results(self, interaction: discord.Interaction, results: dict, filter_description: str):
        """Show the final results embed after recruitment completion"""
        total_tried = results.get('total_tried', 0)
        total_sent = results.get('total_sent', 0)
        total_failed = results.get('total_failed', 0)
        success_rate = (total_sent / total_tried * 100) if total_tried > 0 else 0
        
        embed = discord.Embed(
            title="✅ Recruitment Complete",
            description=f"**Filter:** {filter_description}\n**Status:** Completed successfully",
            color=0x4CAF50
        )
        
        # Final statistics
        embed.add_field(
            name="📊 Final Results",
            value=f"**Total Tried:** {total_tried}\n"
                  f"**Total Sent:** {total_sent}\n"
                  f"**Total Failed:** {total_failed}\n"
                  f"**Success Rate:** {success_rate:.1f}%",
            inline=True
        )
        
        # Additional info
        if results.get('duration'):
            embed.add_field(
                name="⏱️ Duration",
                value=f"**Total Time:** {results['duration']}",
                inline=True
            )
        
        embed.set_footer(text="Recruitment completed - Cache has been cleaned and saved")
        embed.timestamp = datetime.now()
        
        await interaction.edit_original_response(embed=embed, view=None)
    
    @discord.ui.button(label="🟡 Last 6 Days", style=discord.ButtonStyle.secondary)
    async def recruit_last_week(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ You can't use these buttons!", 
                ephemeral=True
            )
            return
        
        # Filter nations active in last week excluding today (24-168 hours ago)
        week_nations = self.filter_nations_by_activity(self.nations, "week")
        
        if not week_nations:
            await interaction.response.send_message(
                "❌ No nations found active in the last 6 days (excluding today)!", 
                ephemeral=True
            )
            return
        
        # Send messages directly with delays
        try:
            # Create initial "starting recruitment" embed
            embed = discord.Embed(
                title="🔄 Starting Recruitment...",
                description=f"**Filter:** Last 6 days (excluding today)\n**Nations:** {len(week_nations)}",
                color=0xff9800
            )
            embed.add_field(
                name="📊 Status", 
                value="Sending recruitment messages with 1.5s delays...", 
                inline=False
            )
            embed.add_field(
                name="⚡ Estimated Time",
                value=f"Approximately {len(week_nations) * 1.5 / 60:.1f} minutes\n"
                      f"(1.5 seconds per nation to prevent API spam)",
                inline=False
            )
            
            # Edit the original message to close the nation browser
            await interaction.response.edit_message(embed=embed, view=None)
            
            # Send messages directly with delays
            results = await self.recruit_cog.send_messages_directly(
                week_nations, 
                interaction.user.id,
                interaction.edit_original_response
            )
            
            # Show final results
            await self._show_final_results(interaction, results, "Last 6 days (excluding today)")
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Failed to Start Recruitment",
                description=f"Error: {str(e)}",
                color=0xff6b6b
            )
            await interaction.edit_original_response(embed=embed, view=None)
    
    @discord.ui.button(label="🟠 Last 14 Days", style=discord.ButtonStyle.secondary)
    async def recruit_two_weeks(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ You can't use these buttons!", 
                ephemeral=True
            )
            return
        
        # Filter nations active in last 14 days excluding first week (168-336 hours ago)
        two_weeks_nations = self.filter_nations_by_activity(self.nations, "two_weeks")
        
        if not two_weeks_nations:
            await interaction.response.send_message(
                "❌ No nations found active 8-14 days ago!", 
                ephemeral=True
            )
            return
        
        # Send messages directly with delays
        try:
            # Create initial "starting recruitment" embed
            embed = discord.Embed(
                title="🔄 Starting Recruitment...",
                description=f"**Filter:** Last 14 days (8-14 days ago)\n**Nations:** {len(two_weeks_nations)}",
                color=0xff9800
            )
            embed.add_field(
                name="📊 Status", 
                value="Sending recruitment messages with 1.5s delays...", 
                inline=False
            )
            embed.add_field(
                name="⚡ Estimated Time",
                value=f"Approximately {len(two_weeks_nations) * 1.5 / 60:.1f} minutes\n"
                      f"(1.5 seconds per nation to prevent API spam)",
                inline=False
            )
            
            # Edit the original message to close the nation browser
            await interaction.response.edit_message(embed=embed, view=None)
            
            # Send messages directly with delays
            results = await self.recruit_cog.send_messages_directly(
                two_weeks_nations, 
                interaction.user.id,
                interaction.edit_original_response
            )
            
            # Show final results
            await self._show_final_results(interaction, results, "Last 14 days (8-14 days ago)")
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Failed to Start Recruitment",
                description=f"Error: {str(e)}",
                color=0xff6b6b
            )
            await interaction.edit_original_response(embed=embed, view=None)
    
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


class ActivityFilterView(View):
    """View for filtering nations by activity periods"""
    
    def __init__(self, recruit_cog, author_id: int):
        super().__init__(timeout=300)  # 5 minute timeout
        self.recruit_cog = recruit_cog
        self.author_id = author_id
        self.message = None
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the command author can use the buttons"""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Only the command author can use these buttons.")
            return False
        return True
    
    def filter_nations_by_activity(self, nations: List[Dict[str, Any]], days: int) -> List[Dict[str, Any]]:
        """Filter nations by activity within the specified number of days"""
        if not nations:
            return []
            
        now = datetime.now(timezone.utc)
        cutoff_date = now - timedelta(days=days)
        
        filtered = []
        for nation in nations:
            if nation.get('last_active_dt'):
                if nation['last_active_dt'] >= cutoff_date:
                    filtered.append(nation)
            # If no last_active_dt, include it (unknown activity)
            elif days >= 14:  # Only include unknowns in longer periods
                filtered.append(nation)
                
        return filtered
    
    def create_filter_embed(self) -> discord.Embed:
        """Create the initial filter selection embed"""
        embed = discord.Embed(
            title="🎯 Nation Activity Filter",
            description="Choose which nations to display based on their last activity:",
            color=0x4CAF50
        )
        
        embed.add_field(
            name="📊 Filter Options:",
            value=(
                "🟢 **Active Today** - Nations active in the last 24 hours\n"
                "🟡 **Last 7 Days** - Nations active within the past week\n"
                "🟠 **Last 14 Days** - Nations active within 2 weeks\n\n"
                "Nations inactive for 14+ days are automatically excluded."
            ),
            inline=False
        )
        
        embed.set_footer(text="Select a filter option below to view nations")
        return embed
    
    @discord.ui.button(label="🟢 Active Today", style=discord.ButtonStyle.green)
    async def filter_today(self, interaction: discord.Interaction, button: Button):
        """Show nations active today (last 24 hours)"""
        await interaction.response.defer()
        
        try:
            # Fetch all nations - filter out those on cooldown
            all_nations = await self.recruit_cog.get_unallied_nations(15000, filter_cooldown=True)
            
            # Filter for today (1 day)
            filtered_nations = self.filter_nations_by_activity(all_nations, 1)
            
            if not filtered_nations:
                embed = discord.Embed(
                    title="🟢 Active Today",
                    description="No nations found that were active in the last 24 hours.",
                    color=0xff6b6b
                )
                await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self)
                return
            
            # Create paginated view
            paginated_view = PaginatedRecruitmentView(filtered_nations, self.recruit_cog, self.author_id)
            
            embed = discord.Embed(
                title="🟢 Nations Active Today",
                description=f"Found **{len(filtered_nations)}** nations active in the last 24 hours",
                color=0x4CAF50
            )
            
            await interaction.followup.edit_message(interaction.message.id, embed=embed, view=paginated_view)
            paginated_view.message = await interaction.original_response()
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error filtering nations: {str(e)}")
    
    @discord.ui.button(label="🟡 Last 7 Days", style=discord.ButtonStyle.secondary)
    async def filter_week(self, interaction: discord.Interaction, button: Button):
        """Show nations active in the last 7 days"""
        await interaction.response.defer()
        
        try:
            # Fetch all nations - filter out those on cooldown
            all_nations = await self.recruit_cog.get_unallied_nations(15000, filter_cooldown=True)
            
            # Filter for last 7 days
            filtered_nations = self.filter_nations_by_activity(all_nations, 7)
            
            if not filtered_nations:
                embed = discord.Embed(
                    title="🟡 Active Last 7 Days",
                    description="No nations found that were active in the last 7 days.",
                    color=0xff6b6b
                )
                await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self)
                return
            
            # Create paginated view
            paginated_view = PaginatedRecruitmentView(filtered_nations, self.recruit_cog, self.author_id)
            
            embed = discord.Embed(
                title="🟡 Nations Active Last 7 Days",
                description=f"Found **{len(filtered_nations)}** nations active in the last 7 days",
                color=0xFFC107
            )
            
            await interaction.followup.edit_message(interaction.message.id, embed=embed, view=paginated_view)
            paginated_view.message = await interaction.original_response()
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error filtering nations: {str(e)}")
    
    @discord.ui.button(label="🟠 Last 14 Days", style=discord.ButtonStyle.secondary)
    async def filter_two_weeks(self, interaction: discord.Interaction, button: Button):
        """Show nations active in the last 14 days"""
        await interaction.response.defer()
        
        try:
            # Fetch all nations - filter out those on cooldown
            all_nations = await self.recruit_cog.get_unallied_nations(15000, filter_cooldown=True)
            
            # Filter for last 14 days
            filtered_nations = self.filter_nations_by_activity(all_nations, 14)
            
            if not filtered_nations:
                embed = discord.Embed(
                    title="🟠 Active Last 14 Days",
                    description="No nations found that were active in the last 14 days.",
                    color=0xff6b6b
                )
                await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self)
                return
            
            # Create paginated view
            paginated_view = PaginatedRecruitmentView(filtered_nations, self.recruit_cog, self.author_id)
            
            embed = discord.Embed(
                title="🟠 Nations Active Last 14 Days",
                description=f"Found **{len(filtered_nations)}** nations active in the last 14 days",
                color=0xFF9800
            )
            
            await interaction.followup.edit_message(interaction.message.id, embed=embed, view=paginated_view)
            paginated_view.message = await interaction.original_response()
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error filtering nations: {str(e)}")
    
    @discord.ui.button(label="❌ Close", style=discord.ButtonStyle.red)
    async def close_filter(self, interaction: discord.Interaction, button: Button):
        """Close the filter view"""
        await interaction.response.defer()
        
        embed = discord.Embed(
            title="✅ Filter Closed",
            description="Activity filter has been closed.",
            color=0x6c757d
        )
        
        await interaction.followup.edit_message(interaction.message.id, embed=embed, view=None)
    
    async def on_timeout(self):
        """Called when view times out"""
        if self.message:
            try:
                embed = discord.Embed(
                    title="⏰ Filter Timeout",
                    description="Activity filter has timed out.",
                    color=0x6c757d
                )
                await self.message.edit(embed=embed, view=None)
            except:
                pass
