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
            return loop.run_until_complete(self.get_logs_async(user_id, limit))
        except:
            return [], 0
    
    async def clear_logs_async(self, count=None):
        """Clear logs with optional count limit using UserDataManager"""
        return await user_data_manager.clear_bot_logs(count)
    
    def clear_logs(self, count=None):
        """Synchronous wrapper for clear_logs_async"""
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.clear_logs_async(count))
        except:
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

class SystemMonitorView(discord.ui.View):
    """System monitoring view for bot resources with caching"""
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog
        self._cache = {}
        self._cache_duration = 3  # Cache for 3 seconds
        self._last_update = 0
    
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
        
        # Calculate realistic storage percentage (assuming 5GB max for bot)
        max_storage_gb = 5.0
        bot_storage_percent = (bot_storage_mb / (max_storage_gb * 1024)) * 100
        
        # Calculate realistic memory percentage (assuming 2GB max for bot)
        max_memory_gb = 2.0
        bot_memory_display_percent = min((bot_memory_gb / max_memory_gb) * 100, 100)
        
        # Calculate realistic CPU percentage (assuming 100% max)
        max_cpu_percent = 100.0
        bot_cpu_display_percent = min(bot_cpu_percent, 100)
        
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
            'total_system_gb': round(total_system_gb, 2)
        }
        self._last_update = current_time
        
        return self._cache
    
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
        """Create comprehensive system monitoring embed"""
        info = self.get_system_info()
        
        # Color based on bot's resource usage
        max_usage = max(info['bot_memory_display_percent'], info['bot_cpu_display_percent'], info['bot_storage_percent'])
        if max_usage >= 80:
            color = 0xff0000  # Red - High usage
        elif max_usage >= 60:
            color = 0xff8800  # Orange - Moderate-high
        elif max_usage >= 40:
            color = 0xffff00  # Yellow - Moderate
        else:
            color = 0x00ff00  # Green - Normal
        
        embed = discord.Embed(
            title="🤖 Allspark Bot Monitor",
            description="Comprehensive real-time monitoring of entire bot ecosystem",
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
        
        # Bot Process Details
        uptime_str = self.format_uptime(info['bot_uptime_seconds'])
        embed.add_field(
            name="🔧 Bot Process Details",
            value=f"**PID:** {info['process_id']}\n**Threads:** {info['bot_threads']}\n**Handles:** {info['bot_handles']}\n**Child Processes:** {info['child_processes']}",
            inline=True
        )
        
        # Discord Bot Metrics
        embed.add_field(
            name="🌐 Discord Metrics",
            value=f"**Guilds:** {info['guild_count']:,}\n**Users:** {info['user_count']:,}\n**Uptime:** {uptime_str}",
            inline=True
        )
        
        # Module System Status
        total_modules = info['loaded_modules'] + info['failed_modules']
        embed.add_field(
            name="📦 Module System",
            value=f"**Loaded:** {info['loaded_modules']}\n**Failed:** {info['failed_modules']}\n**Total:** {total_modules}",
            inline=True
        )
        
        # File Statistics
        file_stats = info['file_counts']
        embed.add_field(
            name="📁 Bot Files",
            value=f"**Python:** {file_stats['py']}\n**JSON:** {file_stats['json']}\n**Total:** {file_stats['total']}",
            inline=True
        )
        
        embed.set_footer(text="Click refresh to update • Comprehensive bot monitoring active")
        
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
            await interaction.response.send_message("❌ Test already running!", ephemeral=True)
            return
            
        self.is_running = True
        button.label = "⏹️ Stop Test"
        button.style = discord.ButtonStyle.secondary
        
        await interaction.response.edit_message(embed=self.create_stress_embed("Starting..."), view=self)
        
        # Start the stress test
        self.current_test = asyncio.create_task(self.run_stress_test(interaction))
    
    async def run_stress_test(self, interaction: discord.Interaction):
        """Run the actual stress test"""
        try:
            monitor = SystemMonitorView(self.cog)
            start_time = time.time()
            commands_executed = 0
            
            # Simulate users
            fake_users = [f"TestUser_{i}" for i in range(self.test_users)]
            test_commands = [
                "ping", "features", "joke", "hello", "user_says",
                "energon_stats", "battle_info", "cybercoin_market"
            ]
            
            # Create progress message
            progress_msg = await interaction.channel.send("🔄 Stress test starting...")
            
            while self.is_running and (time.time() - start_time) < self.test_duration:
                # Execute commands for each user
                for user in fake_users:
                    if not self.is_running:
                        break
                        
                    for _ in range(self.commands_per_user):
                        if not self.is_running:
                            break
                            
                        # Simulate command execution
                        command = test_commands[commands_executed % len(test_commands)]
                        
                        # Get current stats
                        stats = monitor.get_system_info()
                        commands_per_sec = commands_executed / max(1, time.time() - start_time)
                        
                        # Update progress
                        elapsed = int(time.time() - start_time)
                        progress_bar = "🟩" * min(20, int((elapsed / self.test_duration) * 20))
                        progress_bar += "⬜" * (20 - len(progress_bar))
                        
                        await progress_msg.edit(
                            content=f"🔥 Stress Test Running...\n"
                                   f"{progress_bar} {elapsed}s/{self.test_duration}s\n"
                                   f"📊 Commands: {commands_executed} | Memory: {stats['bot_memory_mb']:.1f}MB | CPU: {stats['bot_cpu_percent']:.1f}%"
                        )
                        
                        commands_executed += 1
                        await asyncio.sleep(0.1)  # Small delay between commands
            
            # Test complete
            self.is_running = False
            stats = monitor.get_system_info()
            
            # Update button back to start
            for child in self.children:
                if child.label.startswith("⏹️"):
                    child.label = "🚀 Start Stress Test"
                    child.style = discord.ButtonStyle.danger
            
            final_embed = self.create_stress_embed("Complete", {
                'bot_memory_mb': stats['bot_memory_mb'],
                'bot_cpu_percent': stats['bot_cpu_percent'],
                'commands_per_second': commands_executed / max(1, time.time() - start_time)
            })
            
            await progress_msg.edit(
                content=f"✅ Stress test completed!\n"
                       f"📊 **Final Results:**\n"
                       f"- Commands executed: {commands_executed}\n"
                       f"- Peak memory: {stats['bot_memory_mb']:.1f}MB\n"
                       f"- Final CPU: {stats['bot_cpu_percent']:.1f}%\n"
                       f"- Average commands/sec: {commands_executed/self.test_duration:.1f}",
                embed=None
            )
            
            await interaction.edit_original_response(embed=final_embed, view=self)
            
        except Exception as e:
            self.is_running = False
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

async def setup(bot):
    """Setup function to add the AdminSystem cog"""
    await bot.add_cog(AdminSystem(bot))
    print("Admin system loaded successfully")

def setup_legacy(bot):
    """Legacy setup function for backward compatibility"""
    bot.add_cog(AdminSystem(bot))
    print("Admin system loaded (legacy)")

__all__ = ['setup', 'setup_legacy', 'AdminSystem']