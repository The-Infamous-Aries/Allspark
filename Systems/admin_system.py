import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import psutil
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from functools import lru_cache
import time
import aiofiles
from config import (
    ADMIN_USER_ID,
    CYBERTRON_ALLIANCE_ID,
    PRIME_BANK_ALLIANCE_ID,
    NORTHERN_CONCORD_ALLIANCE_ID,
    UNION_OF_NATIONS_ALLIANCE_ID,
    TRIUMVIRATE_ALLIANCE_ID,
    RECLAIMED_FLAME_ALLIANCE_ID,
    TCO_ALLIANCE_ID,
)

# Import UserDataManager for unified data storage
from Systems.user_data_manager import user_data_manager

class BotLogger:
    """Logging system for bot activities"""
    def __init__(self, log_file=None):
        # No longer need file paths - using UserDataManager
        pass
    
    def add_log(self, user_id, username, command, details=""):
        """Add a log entry using UserDataManager"""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "username": username,
            "command": command,
            "details": details
        }
        
        # Use UserDataManager to add log
        asyncio.create_task(user_data_manager.add_bot_log(log_entry))
    
    async def get_logs_async(self, user_id=None, limit=50):
        """Get logs with optional user filter using UserDataManager"""
        logs = await user_data_manager.get_bot_logs(user_id, limit)
        total_count = await user_data_manager.get_bot_log_count(user_id)
        return logs, total_count
    
    def get_logs(self, user_id=None, limit=50):
        """Synchronous wrapper for get_logs_async"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, we can't use run_until_complete
                # Return empty logs instead of causing issues
                return [], 0
            return loop.run_until_complete(self.get_logs_async(user_id, limit))
        except Exception as e:
            # Log the specific error for debugging
            print(f"Error in get_logs: {e}")
            return [], 0
    
    async def clear_logs_async(self, count=None):
        """Clear logs with optional count limit using UserDataManager"""
        return await user_data_manager.clear_bot_logs(count)
    
    def clear_logs(self, count=None):
        """Synchronous wrapper for clear_logs_async"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, we can't use run_until_complete
                # Return 0 instead of causing issues
                return 0
            return loop.run_until_complete(self.clear_logs_async(count))
        except Exception as e:
            # Log the specific error for debugging
            print(f"Error in clear_logs: {e}")
            return 0

class AsyncFileHandler:
    """Async file handler for efficient log operations"""
    
    def __init__(self, max_buffer_size: int = 100):
        self.log_buffer = []
        self.max_buffer_size = max_buffer_size
        self._lock = asyncio.Lock()
    
    async def write_log_async(self, log_path: str, content: str) -> None:
        """Write logs asynchronously with buffering"""
        async with self._lock:
            self.log_buffer.append((log_path, content))
            
            if len(self.log_buffer) >= self.max_buffer_size:
                await self._flush_buffer()
    
    async def _flush_buffer(self) -> None:
        """Flush buffered logs to files"""
        if not self.log_buffer:
            return
            
        # Group logs by file path for batch processing
        log_groups = {}
        for log_path, content in self.log_buffer:
            if log_path not in log_groups:
                log_groups[log_path] = []
            log_groups[log_path].append(content)
        
        # Write all logs for each file
        for log_path, contents in log_groups.items():
            try:
                async with aiofiles.open(log_path, 'a', encoding='utf-8') as f:
                    await f.write('\n'.join(contents) + '\n')
            except Exception as e:
                print(f"Error writing to log {log_path}: {e}")
        
        self.log_buffer.clear()
    
    async def read_logs_async(self, log_path: str, lines: int = 50) -> List[str]:
        """Read logs asynchronously with line limiting"""
        try:
            async with aiofiles.open(log_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                lines_list = content.splitlines()
                return lines_list[-lines:] if len(lines_list) > lines else lines_list
        except FileNotFoundError:
            return []
        except Exception as e:
            print(f"Error reading log {log_path}: {e}")
            return []

class MemoryOptimizedLogger:
    """Memory-efficient logger with automatic cleanup"""
    
    def __init__(self, max_log_size_mb: int = 10, max_log_age_days: int = 7):
        self.max_log_size = max_log_size_mb * 1024 * 1024  # Convert to bytes
        self.max_log_age = max_log_age_days * 24 * 3600  # Convert to seconds
        self._cleanup_lock = asyncio.Lock()
    
    async def cleanup_old_logs(self, log_dir: str = "logs") -> None:
        """Remove old log files to save disk space"""
        async with self._cleanup_lock:
            try:
                if not os.path.exists(log_dir):
                    return
                
                current_time = time.time()
                for filename in os.listdir(log_dir):
                    if filename.endswith('.log'):
                        file_path = os.path.join(log_dir, filename)
                        
                        # Check file age
                        try:
                            stat = os.stat(file_path)
                            if current_time - stat.st_mtime > self.max_log_age:
                                os.remove(file_path)
                                continue
                            
                            # Check file size and rotate if too large
                            if stat.st_size > self.max_log_size:
                                # Rotate log by renaming and creating new one
                                new_name = f"{file_path}.{int(current_time)}.old"
                                os.rename(file_path, new_name)
                                
                        except OSError:
                            continue
                            
            except Exception as e:
                print(f"Error during log cleanup: {e}")
    
    def get_memory_usage(self) -> Dict[str, int]:
        """Get current memory usage statistics"""
        import gc
        gc.collect()  # Force garbage collection
        
        return {
            'objects': len(gc.get_objects()),
            'garbage': len(gc.garbage),
            'current_memory_mb': psutil.Process().memory_info().rss // (1024 * 1024)
        }

class ErrorHandler:
    """Centralized error handling with graceful degradation"""
    
    def __init__(self):
        self.error_counts = {}
        self.last_error_time = {}
        self.max_errors_per_minute = 5
    
    async def handle_error(self, error: Exception, context: str = "unknown") -> bool:
        """Handle errors gracefully and return whether to continue execution"""
        current_time = time.time()
        
        # Initialize error tracking
        if context not in self.error_counts:
            self.error_counts[context] = 0
            self.last_error_time[context] = current_time
        
        # Reset counter if minute has passed
        if current_time - self.last_error_time[context] > 60:
            self.error_counts[context] = 0
            self.last_error_time[context] = current_time
        
        # Increment error count
        self.error_counts[context] += 1
        
        # Check if we should suppress errors (rate limiting)
        if self.error_counts[context] > self.max_errors_per_minute:
            return False
        
        # Log error appropriately
        print(f"Error in {context}: {str(error)}")
        return True
    
    def get_error_stats(self) -> Dict[str, int]:
        """Get current error statistics"""
        return self.error_counts.copy()

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
    
    async def on_timeout(self):
        """Handle timeout by disabling the view"""
        try:
            for item in self.children:
                item.disabled = True
            # Note: We can't edit the message here since we don't have a reference to it
        except Exception:
            pass

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
            
            user_list = '\n'.join(user_mentions)
            description = f"**Selected users to delete data files:**\n{user_list}\n\n⚠️ **Warning:** This will permanently delete ALL user data files!"
        else:
            description = "No users selected. Choose users from the dropdown above.\n\n⚠️ **Warning:** This will permanently delete ALL user data files!"
        
        embed = discord.Embed(
            title="🗑️ Admin User Data Clear",
            description=description,
            color=0xff0000
        )
        await interaction.response.edit_message(embed=embed, view=self)

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
            
            user_list = '\n'.join(user_mentions)
            description = f"**Selected users to delete data files:**\n{user_list}\n\n⚠️ **Warning:** This will permanently delete ALL user data files!"
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
    def __init__(self, bot):
        self.bot = bot
        self._last_monitor_update = 0
        self._cached_stats = {}
        self._cache_duration = 5  # Cache for 5 seconds
        self.file_handler = AsyncFileHandler()
        self.memory_logger = MemoryOptimizedLogger()
        self.error_handler = ErrorHandler()
        self.logger = BotLogger()
        
        # Command tracking system
        self.command_stats = {}
        self.active_users = set()
        self.error_count = 0
        self.start_time = time.time()
        self.command_usage_history = []  # Store recent command usage for analysis
    
    async def cog_check(self, ctx):
        """Global check for all commands in this cog"""
        return await self.bot.is_owner(ctx.author)
    
    async def cog_command_error(self, ctx, error):
        """Global error handler for this cog"""
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ This command is restricted to the bot owner.")
        else:
            should_continue = await self.error_handler.handle_error(error, ctx.command.name)
            if should_continue:
                await ctx.send(f"❌ An error occurred: {str(error)}")
            else:
                await ctx.send("❌ Command temporarily disabled due to excessive errors.")

    @commands.hybrid_command(name='alliance_clear', description='[ADMIN ONLY] Clear Bloc data except current alliances and treaties_9445.json')
    async def alliance_clear(self, ctx):
        """Delete files in Systems/Data/Bloc except active alliance files and treaties_9445.json."""
        if ctx.author.id != ADMIN_USER_ID:
            await ctx.send("❌ This command is restricted to the bot administrator.", ephemeral=True)
            return

        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            bloc_dir = os.path.join(base_dir, "Systems", "Data", "Bloc")

            keep_ids = {
                str(CYBERTRON_ALLIANCE_ID),
                str(PRIME_BANK_ALLIANCE_ID),
                str(NORTHERN_CONCORD_ALLIANCE_ID),
                str(UNION_OF_NATIONS_ALLIANCE_ID),
                str(TRIUMVIRATE_ALLIANCE_ID),
                str(RECLAIMED_FLAME_ALLIANCE_ID),
                str(TCO_ALLIANCE_ID),
            }

            keep_files = {f"alliance_{aid}.json" for aid in keep_ids}
            keep_files.add("treaties_9445.json")

            deleted = []
            kept = []

            if not os.path.isdir(bloc_dir):
                await ctx.send(f"❌ Bloc directory not found: `{bloc_dir}`")
                return

            for name in os.listdir(bloc_dir):
                full_path = os.path.join(bloc_dir, name)
                if os.path.isfile(full_path):
                    if name in keep_files:
                        kept.append(name)
                    else:
                        try:
                            os.remove(full_path)
                            deleted.append(name)
                        except Exception as e:
                            deleted.append(f"{name} (error: {e})")
                else:
                    kept.append(name)

            self.logger.add_log(ctx.author.id, str(ctx.author), "alliance_clear", f"Deleted {len(deleted)} files in Bloc directory")

            embed = discord.Embed(
                title="🧹 Alliance Bloc Cleanup",
                description=f"Kept alliance files linked to current bloc alliances and `treaties_9445.json`.\nDirectory: `{bloc_dir}`",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )

            if kept:
                kept_display = ", ".join(sorted(k for k in kept if k in keep_files))
                embed.add_field(name="✅ Kept", value=kept_display or "(none)", inline=False)

            if deleted:
                deleted_display = ", ".join(sorted(deleted))
                if len(deleted_display) > 900:
                    deleted_display = deleted_display[:897] + "..."
                embed.add_field(name="🗑️ Deleted", value=deleted_display or "(none)", inline=False)

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error during alliance_clear: {str(e)}")

        
    @lru_cache(maxsize=128)
    def _get_cached_system_stats(self) -> Dict[str, Any]:
        """Cache system stats to reduce CPU usage"""
        current_time = time.time()
        if current_time - self._last_monitor_update > self._cache_duration:
            self._cached_stats = {
                'cpu': psutil.cpu_percent(interval=0.1),
                'memory': psutil.virtual_memory()._asdict(),
                'disk': psutil.disk_usage('/')._asdict(),
                'boot_time': psutil.boot_time(),
                'processes': len(psutil.pids())
            }
            self._last_monitor_update = current_time
        return self._cached_stats



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

    @commands.hybrid_command(name='analytics', description="[ADMIN ONLY] Display comprehensive command usage analytics")
    async def analytics(self, ctx):
        """Display detailed command usage analytics and statistics"""
        if ctx.author.id != ADMIN_USER_ID:
            await ctx.send("❌ This command is restricted to the bot administrator.", ephemeral=True)
            return
        
        self.logger.add_log(ctx.author.id, str(ctx.author), "analytics", "Command analytics accessed")
        
        # Get analytics data
        analytics = self.get_command_analytics()
        
        # Create comprehensive analytics embed
        embed = discord.Embed(
            title="📊 Bot Command Analytics Dashboard",
            description="Comprehensive command usage statistics and performance metrics",
            color=0x00ff99,
            timestamp=discord.utils.utcnow()
        )
        
        # Overall statistics
        embed.add_field(
            name="📈 Overall Statistics",
            value=f"• **Total Commands:** {analytics['total_commands']:,}\n"
                  f"• **Unique Commands:** {analytics['unique_commands']}\n"
                  f"• **Bot Uptime:** {analytics['uptime_hours']:.1f} hours\n"
                  f"• **Total Errors:** {analytics['total_errors']:,}",
            inline=True
        )
        
        # Recent activity
        embed.add_field(
            name="⏰ Recent Activity",
            value=f"• **Last Hour:** {analytics['recent_activity']} commands\n"
                  f"• **Last 24h:** {analytics['daily_activity']} commands\n"
                  f"• **Error Rate:** {analytics['error_rate']:.1f}%\n"
                  f"• **Active Users (1h):** {analytics['recent_users']}",
            inline=True
        )
        
        # Performance metrics
        avg_commands_per_hour = analytics['daily_activity'] / 24 if analytics['daily_activity'] > 0 else 0
        embed.add_field(
            name="⚡ Performance Metrics",
            value=f"• **Avg Commands/Hour:** {avg_commands_per_hour:.1f}\n"
                  f"• **Daily Users:** {analytics['daily_users']}\n"
                  f"• **Commands/User:** {analytics['daily_activity'] / max(1, analytics['daily_users']):.1f}\n"
                  f"• **Success Rate:** {100 - analytics['error_rate']:.1f}%",
            inline=True
        )
        
        # Top commands
        if analytics['top_commands']:
            top_commands_text = ""
            for i, (cmd, count) in enumerate(analytics['top_commands'][:8], 1):
                percentage = (count / max(1, analytics['total_commands'])) * 100
                top_commands_text += f"{i}. **{cmd}**: {count:,} ({percentage:.1f}%)\n"
            
            embed.add_field(
                name="🏆 Most Used Commands",
                value=top_commands_text,
                inline=False
            )
        
        # Add footer with refresh info
        embed.set_footer(text="Analytics update in real-time • Use /monitor for system resources")
        
        await ctx.send(embed=embed)

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
            else:
                await ctx.send("❌ Debug log file not found.")
                
        except Exception as e:
            await ctx.send(f"❌ Error clearing debug log: {str(e)}")

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

    @commands.Cog.listener()
    async def on_command(self, ctx):
        """Track command usage when commands are invoked"""
        try:
            command_name = ctx.command.name if ctx.command else "unknown"
            user_id = ctx.author.id
            
            # Update command statistics
            if command_name not in self.command_stats:
                self.command_stats[command_name] = 0
            self.command_stats[command_name] += 1
            
            # Track active users
            self.active_users.add(user_id)
            
            # Add to usage history (keep last 1000 entries)
            self.command_usage_history.append({
                'command': command_name,
                'user_id': user_id,
                'timestamp': time.time(),
                'guild_id': ctx.guild.id if ctx.guild else None
            })
            
            # Keep history manageable
            if len(self.command_usage_history) > 1000:
                self.command_usage_history = self.command_usage_history[-500:]
                
        except Exception as e:
            # Don't let tracking errors break command execution
            pass

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Track command errors for monitoring"""
        try:
            self.error_count += 1
            command_name = ctx.command.name if ctx.command else "unknown"
            
            # Log error for analysis
            self.command_usage_history.append({
                'command': command_name,
                'user_id': ctx.author.id,
                'timestamp': time.time(),
                'guild_id': ctx.guild.id if ctx.guild else None,
                'error': True,
                'error_type': type(error).__name__
            })
            
        except Exception as e:
            # Don't let error tracking break error handling
            pass

    @commands.Cog.listener()
    async def on_application_command(self, interaction):
        """Track slash command usage"""
        try:
            command_name = interaction.command.name if interaction.command else "unknown"
            user_id = interaction.user.id
            
            # Update command statistics
            if command_name not in self.command_stats:
                self.command_stats[command_name] = 0
            self.command_stats[command_name] += 1
            
            # Track active users
            self.active_users.add(user_id)
            
            # Add to usage history
            self.command_usage_history.append({
                'command': command_name,
                'user_id': user_id,
                'timestamp': time.time(),
                'guild_id': interaction.guild.id if interaction.guild else None,
                'slash_command': True
            })
            
            # Keep history manageable
            if len(self.command_usage_history) > 1000:
                self.command_usage_history = self.command_usage_history[-500:]
                
        except Exception as e:
            # Don't let tracking errors break command execution
            pass

    def get_command_analytics(self):
        """Get comprehensive command usage analytics"""
        try:
            current_time = time.time()
            
            # Calculate time-based metrics
            hour_ago = current_time - 3600
            day_ago = current_time - 86400
            
            recent_commands = [cmd for cmd in self.command_usage_history if cmd['timestamp'] > hour_ago]
            daily_commands = [cmd for cmd in self.command_usage_history if cmd['timestamp'] > day_ago]
            
            # Most used commands (all time)
            top_commands = sorted(self.command_stats.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # Recent activity
            recent_activity = len(recent_commands)
            daily_activity = len(daily_commands)
            
            # Error rate calculation
            recent_errors = len([cmd for cmd in recent_commands if cmd.get('error', False)])
            error_rate = (recent_errors / max(1, recent_activity)) * 100
            
            # Unique users
            recent_users = len(set(cmd['user_id'] for cmd in recent_commands))
            daily_users = len(set(cmd['user_id'] for cmd in daily_commands))
            
            return {
                'total_commands': sum(self.command_stats.values()),
                'unique_commands': len(self.command_stats),
                'top_commands': top_commands,
                'recent_activity': recent_activity,
                'daily_activity': daily_activity,
                'error_rate': error_rate,
                'recent_users': recent_users,
                'daily_users': daily_users,
                'total_errors': self.error_count,
                'uptime_hours': (current_time - self.start_time) / 3600
            }
        except Exception as e:
            return {
                'total_commands': 0,
                'unique_commands': 0,
                'top_commands': [],
                'recent_activity': 0,
                'daily_activity': 0,
                'error_rate': 0,
                'recent_users': 0,
                'daily_users': 0,
                'total_errors': 0,
                'uptime_hours': 0
            }

async def setup(bot):
    """Setup function to add the AdminSystem cog"""
    await bot.add_cog(AdminSystem(bot))
    print("Admin system loaded successfully")

def setup_legacy(bot):
    """Legacy setup function for backward compatibility"""
    bot.add_cog(AdminSystem(bot))
    print("Admin system loaded (legacy)")

__all__ = ['setup', 'setup_legacy', 'AdminSystem']