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
        self.total_pages = min(20, (len(nations) + 4) // 5)  # Max 20 pages of 5 nations each = 100 nations max for display
        self.message = None
        
        # Calculate page ranges - now 5 nations per page
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
        
        # Page indicator
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
     
    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.secondary)
    async def refresh_nations(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ You can't use these buttons!", 
                ephemeral=True
            )
            return
            
        await interaction.response.defer()
        
        # Fetch new nations
        new_nations = await self.recruit_cog.get_unallied_nations(100)
        
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
        
        # Disable buttons during processing
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        
        # Process recruitment for this page with timeout protection
        results = []
        for nation in current_nations:
            try:
                # Add small delay between requests to prevent overwhelming the API
                await asyncio.sleep(0.5)
                
                success, message = await self.recruit_cog.send_p_and_w_message(
                    nation['nation_id'],
                    nation['leader_name']
                )
                results.append({
                    'nation_name': nation['nation_name'],
                    'success': success,
                    'message': message
                })
            except asyncio.TimeoutError:
                results.append({
                    'nation_name': nation['nation_name'],
                    'success': False,
                    'message': 'Request timeout - Politics & War API is slow'
                })
            except Exception as e:
                results.append({
                    'nation_name': nation['nation_name'],
                    'success': False,
                    'message': str(e)
                })
        
        # Create results embed
        success_count = sum(1 for r in results if r['success'])
        embed = discord.Embed(
            title=f"📊 Recruitment Results - Page {self.current_page + 1}",
            description=f"Processed {len(results)} nations",
            color=0x4CAF50 if success_count == len(results) else 0xff9800
        )
        
        results_text = ""
        for result in results:
            status = "✅" if result['success'] else "❌"
            results_text += f"{status} {result['nation_name']}: {result['message']}\n"
        
        if results_text:
            embed.add_field(name="Results:", value=results_text[:1024], inline=False)
        
        embed.set_footer(text=f"Success: {success_count}/{len(results)}")
        
        # Re-enable buttons
        self.update_buttons()
        try:
            await interaction.message.edit(embed=embed, view=self)
        except discord.errors.Forbidden:
            # If we can't edit the original message, send a new one
            await interaction.followup.send(embed=embed)
    
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
        
        # Disable buttons during processing
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        
        # Process recruitment for all nations in the paginated view (max 100)
        results = []
        for nation in self.nations:
            try:
                # Add small delay between requests to prevent overwhelming the API
                await asyncio.sleep(0.1)
                
                success, message = await self.recruit_cog.send_p_and_w_message(
                    nation['nation_id'],
                    nation['leader_name']
                )
                results.append({
                    'nation_name': nation['nation_name'],
                    'success': success,
                    'message': message
                })
            except asyncio.TimeoutError:
                results.append({
                    'nation_name': nation['nation_name'],
                    'success': False,
                    'message': 'Request timeout - Politics & War API is slow'
                })
            except Exception as e:
                results.append({
                    'nation_name': nation['nation_name'],
                    'success': False,
                    'message': str(e)
                })
        
        # Create results embed
        success_count = sum(1 for r in results if r['success'])
        embed = discord.Embed(
            title="📊 Mass Recruitment Results",
            description=f"Processed {len(results)} nations from the displayed list",
            color=0x4CAF50 if success_count == len(results) else 0xff9800
        )
        
        # Summary by pages
        page_results = []
        current_idx = 0
        for page_num, page_nations in enumerate(self.pages, 1):
            page_success = 0
            for _ in page_nations:
                if current_idx < len(results) and results[current_idx]['success']:
                    page_success += 1
                current_idx += 1
            page_results.append(f"Page {page_num}: {page_success}/{len(page_nations)}")
        
        if page_results:
            embed.add_field(name="Page Results:", value="\n".join(page_results), inline=False)
        
        embed.set_footer(text=f"Total Success: {success_count}/{len(results)}")
        
        # Clear view after completion
        try:
            await interaction.message.edit(embed=embed, view=None)
        except discord.errors.Forbidden:
            # If we can't edit the original message, send a new one
            await interaction.followup.send(embed=embed)
        self.stop()
    
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