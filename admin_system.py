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
from config import ADMIN_USER_ID

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

class SystemMonitorView(discord.ui.View):
    """Enhanced comprehensive system monitoring with command usage tracking"""
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog
        self._cache = {}
        self._cache_duration = 3  # Cache for 3 seconds
        self._last_update = 0
        self.command_stats = {}  # Track command usage
        self.active_users = set()  # Track active users
        self.error_count = 0  # Track errors
        self.start_time = time.time()  # Track session start
    
    def get_system_info(self):
        """Get comprehensive bot resource usage across entire ecosystem"""
        current_time = time.time()
        
        # Return cached data if within cache duration
        if self._cache and (current_time - self._last_update) < self._cache_duration:
            return self._cache
        
        # Get fresh data from the actual bot process
        current_process = psutil.Process()
        
        # Memory usage - actual bot process memory
        bot_memory = current_process.memory_info()
        bot_memory_mb = bot_memory.rss / (1024**2)
        bot_memory_gb = bot_memory_mb / 1024
        
        # Get system memory to calculate realistic percentage
        system_memory = psutil.virtual_memory()
        total_system_gb = system_memory.total / (1024**3)
        bot_memory_percent = (bot_memory_gb / total_system_gb) * 100
        
        # CPU usage - actual bot process CPU
        bot_cpu_percent = current_process.cpu_percent(interval=0.1)
        
        # Get system CPU count for realistic scaling
        system_cpus = psutil.cpu_count()
        bot_cpu_scaled = min(bot_cpu_percent / system_cpus, 100)
        
        # Bot storage - comprehensive bot directory monitoring
        bot_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        bot_storage_mb = 0
        
        # Cache storage calculation for 60 seconds
        if not hasattr(self, '_storage_cache') or (current_time - getattr(self, '_storage_last_update', 0)) > 60:
            try:
                # Monitor entire bot directory structure
                essential_dirs = [
                    bot_directory,  # Root bot directory
                    os.path.join(bot_directory, 'Systems'),
                    os.path.join(bot_directory, 'cogs'),
                    os.path.join(bot_directory, 'Data'),
                    os.path.join(bot_directory, 'Global Saves'),
                    os.path.join(bot_directory, 'Users'),
                ]
                
                bot_storage_bytes = 0
                file_counts = {'py': 0, 'json': 0, 'txt': 0, 'md': 0, 'log': 0, 'total': 0}
                
                for check_dir in essential_dirs:
                    if os.path.exists(check_dir):
                        for root, dirs, files in os.walk(check_dir):
                            # Skip cache and temp directories
                            if any(skip in root.lower() for skip in ['__pycache__', '.git', '.vs', 'env', 'venv', '.pytest_cache']):
                                continue
                            for file in files:
                                try:
                                    file_path = os.path.join(root, file)
                                    file_size = os.path.getsize(file_path)
                                    bot_storage_bytes += file_size
                                    
                                    # Count file types
                                    file_ext = file.split('.')[-1].lower() if '.' in file else 'other'
                                    if file_ext in file_counts:
                                        file_counts[file_ext] += 1
                                    file_counts['total'] += 1
                                    
                                except (OSError, IOError):
                                    continue
                
                bot_storage_mb = bot_storage_bytes / (1024**2)
                self._storage_cache = bot_storage_mb
                self._storage_last_update = current_time
                self._file_counts = file_counts
            except:
                bot_storage_mb = 0
                self._storage_cache = 0
                self._file_counts = {'py': 0, 'json': 0, 'txt': 0, 'md': 0, 'log': 0, 'total': 0}
        else:
            bot_storage_mb = self._storage_cache
            file_counts = getattr(self, '_file_counts', {'py': 0, 'json': 0, 'txt': 0, 'md': 0, 'log': 0, 'total': 0})
        
        # Bot-specific process metrics
        bot_threads = current_process.num_threads()
        
        # Get bot's actual open file handles (comprehensive)
        try:
            bot_files = [f for f in current_process.open_files() 
                        if bot_directory in f.path and not f.path.lower().endswith(('.pyc', '.tmp', '.pyd'))]
            bot_handles = len(bot_files)
        except:
            bot_handles = 0
        
        # Get child processes (if any)
        try:
            child_processes = len(current_process.children(recursive=True))
        except:
            child_processes = 0
        
        # Discord bot-specific metrics
        guild_count = len(self.cog.bot.guilds) if hasattr(self.cog, 'bot') else 0
        user_count = sum(guild.member_count for guild in self.cog.bot.guilds) if hasattr(self.cog, 'bot') else 0
        
        # Bot uptime calculation
        bot_start_time = getattr(self.cog.bot, 'start_time', datetime.now()) if hasattr(self.cog, 'bot') else datetime.now()
        bot_uptime_seconds = (datetime.now() - bot_start_time).total_seconds()
        
        # Module/system counts
        loaded_modules = len(getattr(self.cog.bot, 'loaded_modules', [])) if hasattr(self.cog, 'bot') else 0
        failed_modules = len(getattr(self.cog.bot, 'failed_modules', [])) if hasattr(self.cog, 'bot') else 0
        
        # Calculate realistic storage percentage (assuming 40GB max for bot)
        max_storage_gb = 40.0
        bot_storage_percent = (bot_storage_mb / (max_storage_gb * 1024)) * 100
        
        # Calculate realistic memory percentage (assuming 3GB max for bot)
        max_memory_gb = 3.0
        bot_memory_display_percent = min((bot_memory_gb / max_memory_gb) * 100, 110)
        
        # Calculate realistic CPU percentage (assuming 110% max)
        max_cpu_percent = 110.0
        bot_cpu_display_percent = min(bot_cpu_percent, 110)
        
        # Enhanced metrics - Get analytics from AdminSystem cog
        analytics = {}
        if hasattr(self.cog, 'get_command_analytics'):
            analytics = self.cog.get_command_analytics()
        
        total_commands_executed = analytics.get('total_commands', 0)
        top_commands = analytics.get('top_commands', [])
        most_used_command = top_commands[0] if top_commands else ("None", 0)
        commands_per_minute = analytics.get('recent_activity', 0) / 60 if analytics.get('recent_activity') else 0
        
        # Active users from analytics
        active_users_count = analytics.get('recent_users', 0)
        
        # Error rate
        error_rate = (self.error_count / max(1, total_commands_executed)) * 100 if total_commands_executed > 0 else 0
        
        # Database/file system health
        users_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Systems", "Users")
        user_files_count = len([f for f in os.listdir(users_dir) if f.endswith('.json')]) if os.path.exists(users_dir) else 0
        
        # Store in cache with comprehensive bot metrics
        self._cache = {
            'bot_memory_mb': round(bot_memory_mb, 2),
            'bot_memory_gb': round(bot_memory_gb, 2),
            'bot_memory_percent': round(bot_memory_percent, 2),
            'bot_memory_display_percent': round(bot_memory_display_percent, 2),
            'max_memory_gb': max_memory_gb,
            'bot_cpu_percent': round(bot_cpu_percent, 2),
            'bot_cpu_scaled': round(bot_cpu_scaled, 2),
            'bot_cpu_display_percent': round(bot_cpu_display_percent, 2),
            'max_cpu_percent': max_cpu_percent,
            'system_cpus': system_cpus,
            'bot_storage_mb': round(bot_storage_mb, 2),
            'bot_storage_gb': round(bot_storage_mb / 1024, 2),
            'bot_storage_percent': round(bot_storage_percent, 2),
            'max_storage_gb': max_storage_gb,
            'bot_threads': bot_threads,
            'bot_handles': bot_handles,
            'child_processes': child_processes,
            'guild_count': guild_count,
            'user_count': user_count,
            'bot_uptime_seconds': int(bot_uptime_seconds),
            'loaded_modules': loaded_modules,
            'failed_modules': failed_modules,
            'process_id': current_process.pid,
            'file_counts': file_counts,
            'total_system_gb': round(total_system_gb, 2),
            # Enhanced metrics
            'total_commands_executed': total_commands_executed,
            'most_used_command': most_used_command,
            'commands_per_minute': round(commands_per_minute, 2),
            'active_users_count': active_users_count,
            'error_rate': round(error_rate, 2),
            'user_files_count': user_files_count,
            'command_stats': dict(sorted(self.command_stats.items(), key=lambda x: x[1], reverse=True)[:5])  # Top 5 commands
        }
        self._last_update = current_time
        
        return self._cache
    
    def track_command(self, command_name, user_id, success=True):
        """Track command usage for monitoring"""
        if command_name not in self.command_stats:
            self.command_stats[command_name] = 0
        self.command_stats[command_name] += 1
        
        # Track active users
        self.active_users.add(user_id)
        
        # Track errors
        if not success:
            self.error_count += 1
    
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
        """Create enhanced comprehensive system monitoring embed"""
        info = self.get_system_info()
        
        # Color based on bot's resource usage and health
        max_usage = max(info['bot_memory_display_percent'], info['bot_cpu_display_percent'], info['bot_storage_percent'])
        error_factor = min(info['error_rate'] / 10, 1.0)  # Scale error rate impact
        
        if max_usage >= 80 or error_factor > 0.5:
            color = 0xff0000  # Red - High usage or errors
        elif max_usage >= 60 or error_factor > 0.2:
            color = 0xff8800  # Orange - Moderate-high
        elif max_usage >= 40:
            color = 0xffff00  # Yellow - Moderate
        else:
            color = 0x00ff00  # Green - Normal
        
        embed = discord.Embed(
            title="🤖 Allspark Bot Monitor - Enhanced",
            description="Comprehensive real-time monitoring of entire bot ecosystem with command tracking",
            color=color,
            timestamp=discord.utils.utcnow()
        )
        
        # Bot Memory field
        memory_bar = self.create_progress_bar(info['bot_memory_display_percent'])
        embed.add_field(
            name="💾 Bot RAM Usage",
            value=f"{memory_bar}\n{info['bot_memory_mb']:.1f}MB / {info['max_memory_gb']:.1f}GB ({info['bot_memory_display_percent']:.1f}%)",
            inline=False
        )
        
        # Bot Storage field
        storage_bar = self.create_progress_bar(info['bot_storage_percent'])
        embed.add_field(
            name="💿 Bot Storage Usage",
            value=f"{storage_bar}\n{info['bot_storage_mb']:.1f}MB / {info['max_storage_gb']:.1f}GB ({info['bot_storage_percent']:.1f}%)",
            inline=False
        )
        
        # Bot CPU field
        cpu_bar = self.create_progress_bar(info['bot_cpu_display_percent'])
        embed.add_field(
            name="⚡ Bot CPU Usage",
            value=f"{cpu_bar}\n{info['bot_cpu_percent']:.2f}% / {info['max_cpu_percent']:.0f}% ({info['bot_cpu_display_percent']:.1f}%)",
            inline=False
        )
        
        # Enhanced Bot Process Details
        uptime_str = self.format_uptime(info['bot_uptime_seconds'])
        embed.add_field(
            name="🔧 Bot Process Details",
            value=f"**PID:** {info['process_id']}\n**Threads:** {info['bot_threads']}\n**Handles:** {info['bot_handles']}\n**Child Processes:** {info['child_processes']}\n**Uptime:** {uptime_str}",
            inline=True
        )
        
        # Enhanced Discord Bot Metrics
        embed.add_field(
            name="🌐 Discord Metrics",
            value=f"**Guilds:** {info['guild_count']:,}\n**Users:** {info['user_count']:,}\n**Active Users:** {info['active_users_count']}\n**User Files:** {info['user_files_count']}",
            inline=True
        )
        
        # Enhanced Module System Status
        total_modules = info['loaded_modules'] + info['failed_modules']
        embed.add_field(
            name="📦 Module System",
            value=f"**Loaded:** {info['loaded_modules']}\n**Failed:** {info['failed_modules']}\n**Total:** {total_modules}\n**Health:** {'🟢 Good' if info['failed_modules'] == 0 else '🟡 Issues'}",
            inline=True
        )
        
        # NEW: Command Usage Statistics
        if info['command_stats']:
            top_commands = []
            for cmd, count in list(info['command_stats'].items())[:3]:
                top_commands.append(f"**{cmd}:** {count}")
            commands_text = "\n".join(top_commands) if top_commands else "No commands tracked"
        else:
            commands_text = "No commands executed yet"
            
        embed.add_field(
            name="📊 Command Usage Stats",
            value=f"**Total Executed:** {info['total_commands_executed']:,}\n**Commands/min:** {info['commands_per_minute']}\n**Most Used:** {info['most_used_command'][0]} ({info['most_used_command'][1]})\n**Error Rate:** {info['error_rate']:.1f}%",
            inline=True
        )
        
        # NEW: Top Commands Field
        embed.add_field(
            name="🏆 Top Commands",
            value=commands_text,
            inline=True
        )
        
        # File Statistics
        file_stats = info['file_counts']
        embed.add_field(
            name="📁 Bot Files",
            value=f"**Python:** {file_stats['py']}\n**JSON:** {file_stats['json']}\n**Total:** {file_stats['total']}\n**Systems:** Active",
            inline=True
        )
        
        # NEW: System Health Indicator
        health_indicators = []
        if info['bot_memory_display_percent'] < 70:
            health_indicators.append("🟢 Memory")
        else:
            health_indicators.append("🟡 Memory")
            
        if info['bot_cpu_display_percent'] < 70:
            health_indicators.append("🟢 CPU")
        else:
            health_indicators.append("🟡 CPU")
            
        if info['error_rate'] < 5:
            health_indicators.append("🟢 Errors")
        else:
            health_indicators.append("🔴 Errors")
            
        embed.add_field(
            name="🏥 System Health",
            value=" | ".join(health_indicators),
            inline=False
        )
        
        embed.set_footer(text="Enhanced monitoring • Click refresh for real-time updates • Stress test available")
        
        return embed
    
    def format_uptime(self, seconds):
        """Format uptime in a human-readable way"""
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.primary)
    async def refresh_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=self.create_embed(), view=self)
    
    @discord.ui.button(label="🔥 Stress Test", style=discord.ButtonStyle.danger, row=1)
    async def stress_test(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Launch stress testing interface"""
        stress_view = StressTestView(self.cog)
        embed = stress_view.create_stress_embed()
        await interaction.response.send_message(embed=embed, view=stress_view, ephemeral=True)

    @discord.ui.button(label="❌ Dismiss", style=discord.ButtonStyle.secondary, row=1)
    async def dismiss_monitor(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="System monitor dismissed.", embed=None, view=None)

class StressTestView(discord.ui.View):
    """Interactive stress testing for bot performance"""
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog
        self.is_running = False
        self.test_users = 10
        self.commands_per_user = 5
        self.test_duration = 30  # seconds
        self.current_test = None
        
    def create_stress_embed(self, status="Ready", stats=None):
        """Create stress test embed"""
        color = 0x00ff00 if status == "Ready" else 0xff6600 if status == "Running" else 0xff0000
        
        embed = discord.Embed(
            title="🔥 Bot Stress Test",
            description=f"Simulate bot load with multiple users executing commands",
            color=color,
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(
            name="⚙️ Test Configuration",
            value=f"**Users:** {self.test_users}\n**Commands/User:** {self.commands_per_user}\n**Duration:** {self.test_duration}s\n**Total Commands:** {self.test_users * self.commands_per_user}",
            inline=True
        )
        
        embed.add_field(
            name="🎯 Status",
            value=f"**State:** {status}\n**Running:** {'Yes' if self.is_running else 'No'}",
            inline=True
        )
        
        if stats:
            embed.add_field(
                name="📊 Live Stats",
                value=f"**Memory:** {stats['bot_memory_mb']:.1f}MB\n**CPU:** {stats['bot_cpu_percent']:.1f}%\n**Commands/sec:** {stats['commands_per_second']:.1f}",
                inline=True
            )
        
        embed.set_footer(text="Configure test parameters below • Monitor performance impact")
        return embed
    
    @discord.ui.button(label="🚀 Start Stress Test", style=discord.ButtonStyle.danger, row=0)
    async def start_stress_test(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.is_running:
            await self.stop_stress_test(interaction)
            return
            
        self.is_running = True
        button.label = "⏹️ Stop Test"
        button.style = discord.ButtonStyle.secondary
        
        await interaction.response.edit_message(embed=self.create_stress_embed("Starting..."), view=self)
        
        # Start the stress test
        self.current_test = asyncio.create_task(self.run_stress_test(interaction))

    async def stop_stress_test(self, interaction: discord.Interaction):
        """Emergency stop the stress test"""
        if not self.is_running:
            await interaction.response.send_message("❌ No test is currently running!", ephemeral=True)
            return
            
        self.is_running = False
        
        # Cancel the running task
        if self.current_test and not self.current_test.done():
            self.current_test.cancel()
            try:
                await self.current_test
            except asyncio.CancelledError:
                pass
        
        # Update button back to start
        for child in self.children:
            if child.label and child.label.startswith("⏹️"):
                child.label = "🚀 Start Stress Test"
                child.style = discord.ButtonStyle.danger
        
        embed = self.create_stress_embed("Stopped")
        await interaction.response.edit_message(embed=embed, view=self)
        
        await interaction.channel.send("🛑 Stress test stopped by user!")
    
    async def run_stress_test(self, interaction: discord.Interaction):
        """Enhanced stress test with realistic command patterns and comprehensive monitoring"""
        try:
            monitor = SystemMonitorView(self.cog)
            start_time = time.time()
            commands_executed = 0
            successful_commands = 0
            failed_commands = 0
            command_timings = {}
            
            # Create test users with realistic Discord user objects
            test_users = []
            
            # Create mock user objects for testing with varied characteristics
            for i in range(self.test_users):
                mock_user = type('MockUser', (), {
                    'id': 100000000000000000 + i,
                    'name': f"TestUser_{i}",
                    'display_name': f"TestUser_{i}",
                    'mention': f"<@100000000000000000{i}>",
                    'bot': False,
                    'guild_permissions': type('MockPermissions', (), {'administrator': False})()
                })()
                test_users.append(mock_user)
            
            # Enhanced command categories with realistic usage patterns
            command_categories = {
                # High frequency commands (70% of usage)
                'common': {
                    'commands': ["ping", "hello", "pet", "energon_stats", "profile"],
                    'weight': 0.7,
                    'delay': 0.1  # Fast execution
                },
                # Medium frequency commands (20% of usage)
                'medium': {
                    'commands': ["battle_info", "cybercoin_market", "range", "joke", "blessing"],
                    'weight': 0.2,
                    'delay': 0.3  # Medium execution
                },
                # Low frequency commands (10% of usage)
                'heavy': {
                    'commands': ["walktru", "combiner", "mega_fight", "character_view", "analysis"],
                    'weight': 0.1,
                    'delay': 0.8  # Slower execution
                }
            }
            
            # Flatten commands with weights for realistic distribution
            weighted_commands = []
            for category, data in command_categories.items():
                count = int(len(data['commands']) * data['weight'] * 100)
                weighted_commands.extend(data['commands'] * max(1, count // len(data['commands'])))
            
            # Ensure we have commands to test
            if not weighted_commands:
                weighted_commands = ["ping", "hello", "pet"]
            
            # Create progress message
            progress_msg = await interaction.channel.send("🔄 Stress test starting...")
            
            # Import necessary modules for real command execution
            from discord.ext import commands
            import random
            
            try:
                while self.is_running and (time.time() - start_time) < self.test_duration:
                    # Simulate realistic user behavior patterns
                    batch_size = min(5, len(test_users))  # Process users in small batches
                    user_batch = random.sample(test_users, batch_size)
                    
                    for user in user_batch:
                        if not self.is_running:
                            break
                        
                        # Realistic command burst pattern (1-3 commands per user per cycle)
                        commands_this_cycle = random.randint(1, min(3, self.commands_per_user))
                        
                        for _ in range(commands_this_cycle):
                            if not self.is_running or (time.time() - start_time) >= self.test_duration:
                                self.is_running = False
                                break
                            
                            # Select command based on realistic usage patterns
                            command_name = random.choice(weighted_commands)
                            command_start_time = time.time()
                            
                            # Track command in monitor
                            monitor.track_command(user.id, command_name, success=True)
                            
                            try:
                                # Find the actual command
                                command = None
                                for cmd in interaction.client.walk_commands():
                                    if cmd.name == command_name:
                                        command = cmd
                                        break
                                
                                # Check cooldowns realistically
                                if command and hasattr(command, 'is_on_cooldown'):
                                    try:
                                        if command.is_on_cooldown(user):
                                            await asyncio.sleep(0.2)  # Brief cooldown wait
                                            continue
                                    except:
                                        pass  # Ignore cooldown check errors
                                
                                # Execute real command with enhanced mock context
                                if command:
                                    # Create comprehensive mock context
                                    mock_ctx = type('MockContext', (), {
                                        'author': user,
                                        'channel': interaction.channel,
                                        'guild': interaction.guild,
                                        'bot': interaction.client,
                                        'message': type('MockMessage', (), {
                                            'author': user,
                                            'channel': interaction.channel,
                                            'guild': interaction.guild,
                                            'content': f"/{command_name}"
                                        })(),
                                        'send': lambda *args, **kwargs: asyncio.sleep(0.01),  # Mock send
                                        'reply': lambda *args, **kwargs: asyncio.sleep(0.01),  # Mock reply
                                        'defer': lambda: asyncio.sleep(0),
                                        'respond': lambda *args, **kwargs: asyncio.sleep(0.01),
                                        'followup': type('MockFollowup', (), {
                                            'send': lambda *args, **kwargs: asyncio.sleep(0.01)
                                        })(),
                                        'interaction': type('MockInteraction', (), {
                                            'user': user,
                                            'guild': interaction.guild,
                                            'channel': interaction.channel,
                                            'response': type('MockResponse', (), {
                                                'send_message': lambda *args, **kwargs: asyncio.sleep(0.01),
                                                'defer': lambda: asyncio.sleep(0)
                                            })()
                                        })()
                                    })()
                                    
                                    # Execute command with timing
                                    try:
                                        if hasattr(command, 'callback'):
                                            await command.callback(mock_ctx)
                                        else:
                                            await command(mock_ctx)
                                        
                                        successful_commands += 1
                                        command_end_time = time.time()
                                        execution_time = command_end_time - command_start_time
                                        
                                        # Track command timing
                                        if command_name not in command_timings:
                                            command_timings[command_name] = []
                                        command_timings[command_name].append(execution_time)
                                        
                                    except Exception as cmd_error:
                                        failed_commands += 1
                                        monitor.track_command(user.id, command_name, success=False)
                                        # Add realistic delay for failed commands
                                        await asyncio.sleep(0.1)
                                else:
                                    # Command not found
                                    failed_commands += 1
                                    monitor.track_command(user.id, command_name, success=False)
                                
                            except Exception as e:
                                failed_commands += 1
                                monitor.track_command(user.id, command_name, success=False)
                            
                            commands_executed += 1
                            
                            # Realistic delay based on command category
                            category_delay = 0.2  # Default delay
                            for cat_name, cat_data in command_categories.items():
                                if command_name in cat_data['commands']:
                                    category_delay = cat_data['delay']
                                    break
                            
                            await asyncio.sleep(category_delay + random.uniform(0, 0.1))
                    
                    # Get enhanced stats
                    stats = monitor.get_system_info()
                    elapsed_time = time.time() - start_time
                    commands_per_sec = commands_executed / max(1, elapsed_time)
                    success_rate = (successful_commands / max(1, commands_executed)) * 100
                    
                    # Update progress with enhanced metrics every few seconds
                    if commands_executed % 10 == 0:  # Update every 10 commands
                        elapsed = int(elapsed_time)
                        progress_bar = "🟩" * min(20, int((elapsed / self.test_duration) * 20))
                        progress_bar += "⬜" * (20 - len(progress_bar))
                        
                        # Calculate average command timing
                        avg_timing = 0
                        if command_timings:
                            all_times = [t for times in command_timings.values() for t in times]
                            avg_timing = sum(all_times) / len(all_times) if all_times else 0
                        
                        await progress_msg.edit(
                            content=f"🔥 **Enhanced Stress Test Running** (Real Commands)\n"
                                   f"{progress_bar} {elapsed}s/{self.test_duration}s\n\n"
                                   f"📊 **Performance Metrics:**\n"
                                   f"• Commands Executed: **{commands_executed}** ({commands_per_sec:.1f}/sec)\n"
                                   f"• Success Rate: **{success_rate:.1f}%** ({successful_commands}✅/{failed_commands}❌)\n"
                                   f"• Avg Command Time: **{avg_timing*1000:.1f}ms**\n"
                                   f"• Active Users: **{len(user_batch)}**\n\n"
                                   f"🖥️ **System Resources:**\n"
                                   f"• Memory: **{stats['bot_memory_mb']:.1f}MB** ({stats['memory_percent']:.1f}%)\n"
                                   f"• CPU: **{stats['bot_cpu_percent']:.1f}%**\n"
                                   f"• Threads: **{stats['bot_threads']}**"
                        )
                    
                    # Brief pause between user batches
                    await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                # Handle cancellation from stop button
                self.is_running = False
            
            # Test complete - generate comprehensive final report
            self.is_running = False
            final_stats = monitor.get_system_info()
            elapsed_time = time.time() - start_time
            
            # Update button back to start
            for child in self.children:
                if child.label and "Stop Test" in child.label:
                    child.label = "🚀 Start Stress Test"
                    child.style = discord.ButtonStyle.danger
            
            # Determine completion status
            if elapsed_time >= self.test_duration:
                status = "Complete"
                completion_message = "✅ **Enhanced Stress Test Completed Successfully!**"
            else:
                status = "Stopped"
                completion_message = "🛑 **Enhanced Stress Test Stopped by User**"
            
            # Calculate comprehensive metrics
            final_commands_per_sec = commands_executed / max(1, elapsed_time)
            final_success_rate = (successful_commands / max(1, commands_executed)) * 100
            
            # Analyze command performance
            slowest_commands = []
            fastest_commands = []
            if command_timings:
                avg_times = {}
                for cmd, times in command_timings.items():
                    avg_times[cmd] = sum(times) / len(times)
                
                # Get top 3 slowest and fastest
                sorted_by_time = sorted(avg_times.items(), key=lambda x: x[1])
                fastest_commands = sorted_by_time[:3]
                slowest_commands = sorted_by_time[-3:]
            
            # Create enhanced final embed
            final_embed = self.create_stress_embed(status, {
                'bot_memory_mb': final_stats['bot_memory_mb'],
                'bot_cpu_percent': final_stats['bot_cpu_percent'],
                'commands_per_second': final_commands_per_sec,
                'success_rate': final_success_rate,
                'total_commands': commands_executed,
                'active_users': len(final_stats.get('active_users', [])),
                'error_rate': final_stats.get('error_rate', 0)
            })
            
            # Generate detailed performance report
            performance_report = f"{completion_message}\n\n"
            performance_report += f"📊 **Comprehensive Test Results:**\n"
            performance_report += f"• **Total Commands:** {commands_executed} real bot commands\n"
            performance_report += f"• **Success Rate:** {final_success_rate:.1f}% ({successful_commands}✅/{failed_commands}❌)\n"
            performance_report += f"• **Performance:** {final_commands_per_sec:.1f} commands/sec\n"
            performance_report += f"• **Test Duration:** {elapsed_time:.1f}s / {self.test_duration}s\n"
            performance_report += f"• **Simulated Users:** {self.test_users} concurrent users\n\n"
            
            performance_report += f"🖥️ **System Impact:**\n"
            performance_report += f"• **Memory Usage:** {final_stats['bot_memory_mb']:.1f}MB ({final_stats['memory_percent']:.1f}%)\n"
            performance_report += f"• **CPU Usage:** {final_stats['bot_cpu_percent']:.1f}%\n"
            performance_report += f"• **Active Threads:** {final_stats['bot_threads']}\n"
            performance_report += f"• **Error Rate:** {final_stats.get('error_rate', 0):.1f}%\n\n"
            
            if fastest_commands:
                performance_report += f"⚡ **Fastest Commands:**\n"
                for cmd, exec_time in fastest_commands:
                    performance_report += f"• `{cmd}`: {exec_time*1000:.1f}ms\n"
                performance_report += "\n"
            
            if slowest_commands:
                performance_report += f"🐌 **Slowest Commands:**\n"
                for cmd, exec_time in slowest_commands:
                    performance_report += f"• `{cmd}`: {exec_time*1000:.1f}ms\n"
            
            await progress_msg.edit(content=performance_report, embed=None)
            
            await interaction.edit_original_response(embed=final_embed, view=self)
            
        except Exception as e:
            self.is_running = False
            # Ensure button resets on error
            for child in self.children:
                if child.label and "Stop Test" in child.label:
                    child.label = "🚀 Start Stress Test"
                    child.style = discord.ButtonStyle.danger
            await interaction.channel.send(f"❌ Stress test error: {str(e)}")
    
    @discord.ui.button(label="⚙️ Configure Test", style=discord.ButtonStyle.primary, row=1)
    async def configure_test(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.is_running:
            await interaction.response.send_message("❌ Cannot configure while test is running!", ephemeral=True)
            return
            
        # Create configuration modal
        modal = StressTestModal(self)
        await interaction.response.send_modal(modal)

class StressTestModal(discord.ui.Modal, title="Configure Stress Test"):
    def __init__(self, stress_view):
        super().__init__()
        self.stress_view = stress_view
        
        self.users = discord.ui.TextInput(
            label="Number of Test Users",
            placeholder="Enter 1-50 users",
            default=str(stress_view.test_users),
            max_length=2,
            min_length=1
        )
        
        self.commands = discord.ui.TextInput(
            label="Commands per User",
            placeholder="Enter 1-20 commands",
            default=str(stress_view.commands_per_user),
            max_length=2,
            min_length=1
        )
        
        self.duration = discord.ui.TextInput(
            label="Test Duration (seconds)",
            placeholder="Enter 10-300 seconds",
            default=str(stress_view.test_duration),
            max_length=3,
            min_length=1
        )
        
        self.add_item(self.users)
        self.add_item(self.commands)
        self.add_item(self.duration)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            users = int(self.users.value)
            commands = int(self.commands.value)
            duration = int(self.duration.value)
            
            # Validate inputs
            users = max(1, min(users, 50))
            commands = max(1, min(commands, 20))
            duration = max(10, min(duration, 300))
            
            self.stress_view.test_users = users
            self.stress_view.commands_per_user = commands
            self.stress_view.test_duration = duration
            
            await interaction.response.edit_message(
                embed=self.stress_view.create_stress_embed("Configured"),
                view=self.stress_view
            )
            
        except ValueError:
            await interaction.response.send_message("❌ Please enter valid numbers!", ephemeral=True)

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