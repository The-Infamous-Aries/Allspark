import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import psutil
import asyncio
from datetime import datetime, timezone
from config import ADMIN_USER_ID

class BotLogger:
    """Logging system for bot activities"""
    def __init__(self, log_file=None):
        if log_file is None:
            # Use absolute path for Json directory
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.log_file = os.path.join(base_dir, "Json", "bot_logs.json")
        else:
            self.log_file = log_file
        self.ensure_log_file()
    
    def ensure_log_file(self):
        """Ensure log file exists"""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w') as f:
                json.dump({"logs": []}, f)
    
    def add_log(self, user_id, username, command, details=""):
        """Add a log entry"""
        try:
            with open(self.log_file, 'r') as f:
                data = json.load(f)
        except:
            data = {"logs": []}
        
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "username": username,
            "command": command,
            "details": details
        }
        
        data["logs"].append(log_entry)
        
        with open(self.log_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_logs(self, user_id=None, limit=50):
        """Get logs with optional user filter"""
        try:
            with open(self.log_file, 'r') as f:
                data = json.load(f)
        except:
            return [], 0
        
        logs = data.get("logs", [])
        
        if user_id:
            logs = [log for log in logs if log.get("user_id") == user_id]
        
        total_count = len(logs)
        recent_logs = logs[-limit:] if logs else []
        
        return recent_logs, total_count
    
    def clear_logs(self, count=None):
        """Clear logs with optional count limit"""
        try:
            with open(self.log_file, 'r') as f:
                data = json.load(f)
        except:
            return 0
        
        logs = data.get("logs", [])
        original_count = len(logs)
        
        if count is None:
            # Clear all logs
            data["logs"] = []
            cleared = original_count
        else:
            # Clear specified number of logs from the beginning
            count = min(count, original_count)
            data["logs"] = logs[count:]
            cleared = count
        
        with open(self.log_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        return cleared

class SystemMonitorView(discord.ui.View):
    """System monitoring view for bot resources"""
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

class ConfirmClearView(discord.ui.View):
    """Confirmation view for clearing all logs"""
    def __init__(self, cog, user_id):
        super().__init__(timeout=30)
        self.cog = cog
        self.user_id = user_id
    
    @discord.ui.button(label="Clear All Logs", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This confirmation is not for you.", ephemeral=True)
            return
        
        try:
            cleared = self.cog.logger.clear_logs()
            embed = discord.Embed(
                title="✅ Logs Cleared",
                description=f"Successfully cleared all {cleared} log entries.",
                color=0x00ff00,
                timestamp=discord.utils.utcnow()
            )
            await interaction.response.edit_message(embed=embed, view=None)
            self.cog.logger.add_log(self.user_id, str(interaction.user), "logs_clear", f"Cleared all {cleared} logs")
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to clear logs: {str(e)}",
                color=0xff0000
            )
            await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This confirmation is not for you.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="❌ Cancelled",
            description="Log clearing cancelled.",
            color=0x808080,
            timestamp=discord.utils.utcnow()
        )
        await interaction.response.edit_message(embed=embed, view=None)

class SystemMonitorView(discord.ui.View):
    """System monitoring view for bot resources"""
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog
    
    def get_system_info(self):
        """Get current system resource information"""
        current_process = psutil.Process()
        
        # Get bot's memory usage
        bot_memory = current_process.memory_info()
        bot_memory_mb = bot_memory.rss / (1024**2)
        bot_memory_gb = bot_memory_mb / 1024
        
        # Get system memory for comparison
        system_memory = psutil.virtual_memory()
        system_memory_gb = system_memory.total / (1024**3)
        
        # Calculate percentage based on 1GB max for RAM
        max_memory_gb = 1.0
        bot_memory_percent = (bot_memory_gb / max_memory_gb) * 100
        
        # Get bot directory size
        bot_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        bot_storage_bytes = 0
        
        try:
            for root, dirs, files in os.walk(bot_directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        bot_storage_bytes += os.path.getsize(file_path)
                    except (OSError, IOError):
                        continue
        except:
            bot_storage_bytes = 0
        
        bot_storage_mb = bot_storage_bytes / (1024**2)
        bot_storage_gb = bot_storage_mb / 1024
        
        # Calculate percentage based on 15GB max
        max_storage_gb = 15.0
        bot_storage_percent = (bot_storage_gb / max_storage_gb) * 100
        
        # Get bot's CPU usage
        bot_cpu_percent = current_process.cpu_percent(interval=1)
        
        # Calculate CPU percentage based on 10% max
        max_cpu_percent = 10.0
        bot_cpu_display_percent = (bot_cpu_percent / max_cpu_percent) * 100
        
        # Get bot's thread count and file handles
        bot_threads = current_process.num_threads()
        try:
            bot_handles = len(current_process.open_files())
        except:
            bot_handles = 0
        
        return {
            'bot_memory_mb': bot_memory_mb,
            'bot_memory_gb': bot_memory_gb,
            'bot_memory_percent': bot_memory_percent,
            'max_memory_gb': max_memory_gb,
            'system_memory_gb': system_memory_gb,
            'bot_storage_mb': bot_storage_mb,
            'bot_storage_gb': bot_storage_gb,
            'bot_storage_percent': bot_storage_percent,
            'max_storage_gb': max_storage_gb,
            'bot_cpu_percent': bot_cpu_percent,
            'bot_cpu_display_percent': bot_cpu_display_percent,
            'max_cpu_percent': max_cpu_percent,
            'bot_threads': bot_threads,
            'bot_handles': bot_handles
        }
    
    def create_progress_bar(self, percentage, length=20, max_val=100):
        """Create a visual progress bar"""
        normalized = min(percentage / max_val * 100, 100)
        filled = int(length * normalized / 100)
        empty = length - filled
        
        if normalized >= 90:
            bar_char = "🟥"
        elif normalized >= 75:
            bar_char = "🟧"
        elif normalized >= 50:
            bar_char = "🟨"
        else:
            bar_char = "🟩"
        
        return bar_char * filled + "⬜" * empty
    
    def create_embed(self):
        """Create system monitoring embed"""
        info = self.get_system_info()
        
        # Color based on bot's resource usage
        max_usage = max(info['bot_memory_percent'], info['bot_cpu_display_percent'], info['bot_storage_percent'])
        if max_usage >= 80:
            color = 0xff0000  # Red - High usage
        elif max_usage >= 60:
            color = 0xff8800  # Orange - Moderate-high
        elif max_usage >= 40:
            color = 0xffff00  # Yellow - Moderate
        else:
            color = 0x00ff00  # Green - Normal
        
        embed = discord.Embed(
            title="🤖 Bot Resource Monitor",
            description="Real-time bot-specific resource usage",
            color=color,
            timestamp=discord.utils.utcnow()
        )
        
        # Bot Memory field
        memory_bar = self.create_progress_bar(info['bot_memory_percent'])
        embed.add_field(
            name="💾 Bot RAM Usage",
            value=f"{memory_bar}\n{info['bot_memory_mb']:.1f}MB / {info['max_memory_gb']:.1f}GB max ({info['bot_memory_percent']:.1f}%)",
            inline=False
        )
        
        # Bot Storage field
        storage_bar = self.create_progress_bar(info['bot_storage_percent'])
        embed.add_field(
            name="💿 Bot Storage Usage",
            value=f"{storage_bar}\n{info['bot_storage_mb']:.1f}MB / {info['max_storage_gb']:.1f}GB max ({info['bot_storage_percent']:.1f}%)",
            inline=False
        )
        
        # Bot CPU field
        cpu_bar = self.create_progress_bar(info['bot_cpu_display_percent'])
        embed.add_field(
            name="⚡ Bot CPU Usage",
            value=f"{cpu_bar}\n{info['bot_cpu_percent']:.2f}% / {info['max_cpu_percent']:.0f}% max ({info['bot_cpu_display_percent']:.1f}%)",
            inline=False
        )
        
        # Additional bot info
        embed.add_field(
            name="🔧 Bot Details",
            value=f"**Threads:** {info['bot_threads']}\n**File Handles:** {info['bot_handles']}",
            inline=True
        )
        
        embed.set_footer(text="Click refresh to update • Bot-specific monitoring active")
        
        return embed
    
    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.primary)
    async def refresh_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=self.create_embed(), view=self)
    
    @discord.ui.button(label="❌ Dismiss", style=discord.ButtonStyle.secondary)
    async def dismiss_monitor(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="System monitor dismissed.", embed=None, view=None)

class DataClearView(discord.ui.View):
    """Data clearing interface for admin - now supports user file deletion"""
    def __init__(self, cog):
        super().__init__(timeout=300)
        self.cog = cog
        self.selected_users = []
        self.clear_mode = "user_files"  # New mode for user file deletion
        
        # Get user data directory from user_data_manager
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.users_dir = os.path.join(base_dir, "Systems", "Users")

    @discord.ui.select(
        placeholder="Select users to delete their data files...",
        min_values=1,
        max_values=5,
        options=[]  # Will be populated dynamically
    )
    async def select_users(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected_users = [int(user_id) for user_id in select.values]
        
        if self.selected_users:
            user_mentions = []
            for user_id in self.selected_users:
                try:
                    user = await interaction.guild.fetch_member(user_id)
                    user_mentions.append(f"• {user.mention} ({user.display_name})")
                except:
                    user_mentions.append(f"• <@{user_id}> (User not found)")
            
            description = f"**Selected users to delete data files:**\n{'\n'.join(user_mentions)}\n\n⚠️ **Warning:** This will permanently delete ALL user data files!"
        else:
            description = "No users selected. Choose users from the dropdown above.\n\n⚠️ **Warning:** This will permanently delete ALL user data files!"
        
        embed = discord.Embed(
            title="🗑️ Admin User Data Clear",
            description=description,
            color=0xff0000
        )
        
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🗑️ Delete User Data Files", style=discord.ButtonStyle.danger)
    async def delete_user_data(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_users:
            await interaction.response.send_message("❌ No users selected to delete!", ephemeral=True)
            return
        
        try:
            deleted_files = []
            failed_deletions = []
            
            for user_id in self.selected_users:
                try:
                    # Construct file path using user_id only (matches user_data_manager.py)
                    file_path = os.path.join(self.users_dir, f"{user_id}.json")
                    
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        
                        # Get user info for logging
                        try:
                            user = await interaction.guild.fetch_member(user_id)
                            user_info = f"{user.mention} ({user.display_name})"
                        except:
                            user_info = f"<@{user_id}> (User not found)"
                        
                        deleted_files.append(user_info)
                        self.cog.logger.add_log(
                            interaction.user.id, 
                            str(interaction.user), 
                            "admin_clear", 
                            f"Deleted user data file for {user_id}"
                        )
                    else:
                        failed_deletions.append(f"<@{user_id}> (No data file)")
                
                except Exception as e:
                    failed_deletions.append(f"<@{user_id}> (Error: {str(e)})")
            
            # Create response embed
            embed = discord.Embed(
                title="✅ User Data Deletion Complete",
                color=0x00ff00 if deleted_files else 0xff0000,
                timestamp=discord.utils.utcnow()
            )
            
            if deleted_files:
                embed.add_field(
                    name="✅ Successfully Deleted",
                    value="\n".join(deleted_files),
                    inline=False
                )
            
            if failed_deletions:
                embed.add_field(
                    name="❌ Failed/Skipped",
                    value="\n".join(failed_deletions),
                    inline=False
                )
            
            await interaction.response.edit_message(embed=embed, view=None)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error Deleting User Data",
                description=f"An error occurred: {str(e)}",
                color=0xff0000
            )
            await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="❌ Operation Cancelled",
            description="User data deletion has been cancelled.",
            color=0x808080
        )
        await interaction.response.edit_message(embed=embed, view=None)

class AdminSystem(commands.Cog):
    """Admin system cog for bot management and monitoring"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = BotLogger()
    
    @commands.hybrid_command(name='monitor', description="[ADMIN ONLY] Display system resource usage monitor")
    async def monitor(self, ctx):
        """Display real-time system resource monitoring"""
        if ctx.author.id != ADMIN_USER_ID:
            await ctx.send("❌ This command is restricted to the bot administrator.", ephemeral=True)
            return
        
        self.logger.add_log(ctx.author.id, str(ctx.author), "monitor", "System monitor accessed")
        
        view = SystemMonitorView(self)
        embed = view.create_embed()
        
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name='admin_clear', description="[ADMIN ONLY] Clear user data files")
    async def admin_clear(self, ctx):
        """Clear user data files for selected users"""
        if ctx.author.id != ADMIN_USER_ID:
            await ctx.send("❌ This command is restricted to the bot administrator.", ephemeral=True)
            return
        
        self.logger.add_log(ctx.author.id, str(ctx.author), "admin_clear", "Data clear interface accessed")
        
        embed = discord.Embed(
            title="🗑️ Admin User Data Clear",
            description="Select users to delete their data files from the dropdown below.\n\n⚠️ **Warning:** This will permanently delete ALL user data files!",
            color=0x0099ff
        )
        
        view = DataClearView(self)
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name='logs', description="[ADMIN ONLY] View bot logs")
    async def logs(self, ctx, user: discord.Member = None):
        """View bot activity logs"""
        if ctx.author.id != ADMIN_USER_ID:
            await ctx.send("❌ This command is restricted to the bot administrator.", ephemeral=True)
            return
        
        user_id = user.id if user else None
        logs, total_count = self.logger.get_logs(user_id=user_id, limit=50)
        
        if not logs:
            if user:
                await ctx.send(f"📝 No logs found for {user.mention}.")
            else:
                await ctx.send("📝 No logs found.")
            return
        
        # Create embed
        if user:
            title = f"📝 Recent Logs for {user.display_name}"
            description = f"Showing last {len(logs)} of {total_count} total logs for this user"
        else:
            title = "📝 Recent Bot Logs"
            description = f"Showing last {len(logs)} of {total_count} total logs"
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=0x0099ff,
            timestamp=discord.utils.utcnow()
        )
        
        # Add log entries
        log_text = ""
        for log in logs[-10:]:  # Show only last 10 in embed to avoid length limits
            timestamp = datetime.fromisoformat(log['timestamp']).strftime('%m/%d %H:%M')
            log_text += f"`{timestamp}` **{log['username']}** used `{log['command']}`\n"
            if log.get('details'):
                log_text += f"  └ {log['details']}\n"
        
        if log_text:
            embed.add_field(name="Recent Activity", value=log_text, inline=False)
        
        if len(logs) > 10:
            embed.add_field(
                name="Note", 
                value=f"Only showing last 10 entries in embed. Total retrieved: {len(logs)}", 
                inline=False
            )
        
        embed.set_footer(text=f"Total logs in system: {total_count}")
        
        await ctx.send(embed=embed)
        
        self.logger.add_log(ctx.author.id, str(ctx.author), "logs", f"Viewed logs for {'user: ' + str(user) if user else 'all users'}")

    @commands.hybrid_command(name='logs_clear', description="[ADMIN ONLY] Clear bot logs")
    async def logs_clear(self, ctx, count: int = None):
        """Clear bot activity logs"""
        if ctx.author.id != ADMIN_USER_ID:
            await ctx.send("❌ This command is restricted to the bot administrator.", ephemeral=True)
            return
        
        if count is not None and count <= 0:
            await ctx.send("❌ Count must be a positive number or omitted to clear all logs.")
            return
        
        # Check if clearing all logs and ask for confirmation
        if count is None:
            view = ConfirmClearView(self, ctx.author.id)
            embed = discord.Embed(
                title="⚠️ Confirm Log Clear",
                description="Are you sure you want to clear **ALL** bot activity logs? This action cannot be undone.",
                color=0xff8800,
                timestamp=discord.utils.utcnow()
            )
            await ctx.send(embed=embed, view=view)
            return
        
        cleared = self.logger.clear_logs(count)
        
        await ctx.send(f"🗑️ Cleared {cleared} log entries.")
        self.logger.add_log(ctx.author.id, str(ctx.author), "logs_clear", f"Cleared {cleared} logs")

    @commands.hybrid_command(name='uptime', description="[ADMIN ONLY] Check bot uptime and performance")
    async def uptime(self, ctx):
        """Check bot uptime and system performance"""
        if ctx.author.id != ADMIN_USER_ID:
            await ctx.send("❌ This command is restricted to the bot administrator.", ephemeral=True)
            return
        
        # Get bot uptime
        uptime_seconds = (discord.utils.utcnow() - self.bot.user.created_at).total_seconds()
        
        # Convert to readable format
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        
        # Get system info
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        embed = discord.Embed(
            title="⏱️ Bot Uptime & Performance",
            color=0x00ff00,
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(
            name="🕐 Uptime",
            value=f"{days}d {hours}h {minutes}m",
            inline=True
        )
        
        embed.add_field(
            name="💾 Memory Usage",
            value=f"{memory.percent:.1f}%",
            inline=True
        )
        
        embed.add_field(
            name="⚡ CPU Usage",
            value=f"{cpu_percent:.1f}%",
            inline=True
        )
        
        embed.set_footer(text="Bot performance metrics")
        
        await ctx.send(embed=embed)
        
        self.logger.add_log(ctx.author.id, str(ctx.author), "uptime", "Uptime check performed")

    @commands.hybrid_command(name='clear_debug_log', description="[ADMIN ONLY] Clear the bot debug log file")
    async def clear_debug_log(self, ctx):
        """Clear the bot_debug.log file while the bot is running"""
        if ctx.author.id != ADMIN_USER_ID:
            await ctx.send("❌ This command is restricted to the bot administrator.", ephemeral=True)
            return
        
        try:
            log_path = "bot_debug.log"
            if os.path.exists(log_path):
                # Clear the log file
                with open(log_path, 'w') as f:
                    f.write("")
                
                embed = discord.Embed(
                    title="✅ Debug Log Cleared",
                    description="Successfully cleared bot_debug.log file",
                    color=0x00ff00,
                    timestamp=discord.utils.utcnow()
                )
                embed.add_field(
                    name="📁 File",
                    value=f"`{log_path}`",
                    inline=True
                )
                embed.add_field(
                    name="👤 Cleared by",
                    value=ctx.author.mention,
                    inline=True
                )
                
                await ctx.send(embed=embed)
                self.logger.add_log(ctx.author.id, str(ctx.author), "clear_debug_log", f"Cleared debug log file")
            else:
                await ctx.send("❌ Debug log file not found.")
                
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error Clearing Debug Log",
                description=f"Failed to clear debug log: {str(e)}",
                color=0xff0000,
                timestamp=discord.utils.utcnow()
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(name='sync_commands', description="[ADMIN ONLY] Force sync all slash commands")
    async def sync_commands(self, ctx):
        """Force sync all slash commands to Discord"""
        if ctx.author.id != ADMIN_USER_ID:
            await ctx.send("❌ This command is restricted to the bot administrator.", ephemeral=True)
            return
        
        try:
            embed = discord.Embed(
                title="🔄 Syncing Commands",
                description="Syncing all slash commands to Discord...",
                color=0x0099ff,
                timestamp=discord.utils.utcnow()
            )
            await ctx.send(embed=embed)
            
            # Force sync the command tree
            synced = await self.bot.tree.sync()
            
            # Log the synced commands
            command_list = [f"`/{cmd.name}`" for cmd in synced]
            commands_text = "\n".join(command_list) if command_list else "No commands synced"
            
            success_embed = discord.Embed(
                title="✅ Commands Synced Successfully",
                description=f"Successfully synced **{len(synced)}** slash commands.",
                color=0x00ff00,
                timestamp=discord.utils.utcnow()
            )
            
            if command_list:
                success_embed.add_field(
                    name="📋 Synced Commands",
                    value=commands_text[:1024],  # Discord field limit
                    inline=False
                )
            
            await ctx.send(embed=success_embed)
            self.logger.add_log(ctx.author.id, str(ctx.author), "sync_commands", f"Synced {len(synced)} commands")
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Sync Failed",
                description=f"Failed to sync commands: {str(e)}",
                color=0xff0000,
                timestamp=discord.utils.utcnow()
            )
            await ctx.send(embed=error_embed)
            self.logger.add_log(ctx.author.id, str(ctx.author), "sync_commands_error", str(e))

async def setup(bot):
    """Setup function to add the AdminSystem cog"""
    await bot.add_cog(AdminSystem(bot))
    print("Admin system loaded successfully")

def setup_legacy(bot):
    """Legacy setup function for backward compatibility"""
    bot.add_cog(AdminSystem(bot))
    print("Admin system loaded (legacy)")

__all__ = ['setup', 'setup_legacy', 'AdminSystem']