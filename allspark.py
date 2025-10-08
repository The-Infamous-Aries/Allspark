import discord
from discord.ext import commands
import os
import asyncio
import json
import logging
import traceback
import sys
from datetime import datetime
from pathlib import Path
import inspect

def setup_environment():
    """Setup the environment for SparkedHost compatibility"""
    # Ensure we're in the correct directory
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    
    # Set environment variables to prevent automatic package installation
    os.environ['PIP_DISABLE_PIP_VERSION_CHECK'] = '1'
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    os.environ['PYTHONPATH'] = str(script_dir) + os.pathsep + os.environ.get('PYTHONPATH', '')
    
    # Add the current directory to Python path
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    
    # Prioritize local packages directory for SparkedHost
    local_packages_dir = script_dir / "local_packages"
    if local_packages_dir.exists():
        local_packages_str = str(local_packages_dir)
        if local_packages_str not in sys.path:
            sys.path.insert(0, local_packages_str)
        print(f"✅ Local packages directory prioritized: {local_packages_dir}")
        
        # Log available local packages for debugging
        try:
            packages = [d.name for d in local_packages_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
            print(f"📦 Available local packages: {', '.join(packages)}")
        except Exception as e:
            print(f"⚠️ Could not list local packages: {e}")
    else:
        print(f"⚠️ Local packages directory not found: {local_packages_dir}")
    
    print(f"✅ Working directory: {script_dir}")
    print(f"✅ Python path updated with {len(sys.path)} entries")
    print(f"🔍 Python path priority order:")
    for i, path in enumerate(sys.path[:5]):  # Show first 5 entries
        print(f"   {i+1}. {path}")

# Setup environment before imports
setup_environment()



# Import UserDataManager for unified data storage
from Systems.user_data_manager import UserDataManager

# Enhanced error handling and logging setup
class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for terminal output"""
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)

# Configure logging to avoid duplicates
# Ensure UTF-8 encoding for console output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
elif hasattr(sys.stdout, 'buffer'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Create file handler
file_handler = logging.FileHandler('bot_debug.log', mode='a', encoding='utf-8')
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s'
))

# Create colored console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(ColoredFormatter(
    '%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s'
))

# Configure root logger to avoid basicConfig
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

# Clear any existing handlers to prevent duplicates
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# Add our handlers
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# Get our specific logger
logger = logging.getLogger('AllsparkBot')
logger.setLevel(logging.DEBUG)

# Suppress discord.py debug logs
logging.getLogger('discord').setLevel(logging.INFO)
logging.getLogger('discord.http').setLevel(logging.WARNING)
logging.getLogger('discord.gateway').setLevel(logging.INFO)

# Import configuration with enhanced validation
def validate_configuration():
    """Validate configuration for SparkedHost deployment"""
    try:
        from config import TOKEN, PREFIX, ADMIN_USER_ID, RESULTS_CHANNEL_ID, GRUMP_USER_ID, ARIES_USER_ID, ROLE_IDS
        
        if not TOKEN:
            raise ValueError("DISCORD_TOKEN not set in configuration")
        
        logger.info("✅ Configuration loaded and validated successfully")
        return TOKEN, PREFIX, ADMIN_USER_ID, RESULTS_CHANNEL_ID, GRUMP_USER_ID, ARIES_USER_ID, ROLE_IDS
        
    except ImportError as e:
        logger.error(f"❌ Failed to load configuration: {e}")
        logger.error("Make sure config.py exists and contains all required variables")
        raise
    except ValueError as e:
        logger.error(f"❌ Configuration validation failed: {e}")
        raise

# Load and validate configuration
TOKEN, PREFIX, ADMIN_USER_ID, RESULTS_CHANNEL_ID, GRUMP_USER_ID, ARIES_USER_ID, ROLE_IDS = validate_configuration()

# Bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.guilds = True

class AllsparkBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=PREFIX,
            intents=intents,
            description="Allspark - Transformers Discord Bot with RPG, Pets, and More!",
            case_insensitive=True
        )
        
        # Development mode toggle - set to True during development
        self.development_mode = os.getenv('DEV_MODE', 'false').lower() == 'true'
        self.dev_guild_id = int(os.getenv('DEV_GUILD_ID', 0)) if os.getenv('DEV_GUILD_ID') else None
        
        # Initialize unified data storage with UserDataManager
        self.user_data_manager = UserDataManager()
        
        # Legacy data storage (to be migrated)
        self.user_data = {}  # Will be deprecated
        self.walktru_states = {}  # Will be deprecated
        self.energon_game_data = {}  # Will be deprecated
        self.energon_cooldowns = {}  # Will be deprecated
        self.energon_challenges = {}  # Will be deprecated
        self.player_stats = {}  # Will be deprecated
        self.ping_cooldowns = {}
        self.hello_cooldowns = {}
        self.pet_data = {}  # Will be deprecated
        self.pet_cooldowns = {}  # Will be deprecated
        
        # Sync configuration
        self.sync_strategy = "staged"  # "staged", "batch", or "single"
        self.batch_size = 25  # Discord recommended batch size
        self.stagger_delay = 2  # Base delay between batches in seconds
        
        # Track loaded modules
        self.loaded_modules = []
        self.failed_modules = []
        
        # Error tracking
        self.error_log = []
        self.startup_time = datetime.now()
        
    async def setup_hook(self):
        """Called when the bot is starting up"""
        logger.info("🤖 Setting up AllsparkBot...")
        logger.info(f"📅 Startup time: {self.startup_time}")
        logger.info(f"🎯 Python version: {sys.version}")
        logger.info(f"🔧 Discord.py version: {discord.__version__}")
        
        try:
            await self.load_all_modules()
            self.log_startup_summary()
            await self.sync_commands_safely()
        except Exception as e:
            logger.critical(f"💥 Critical error during setup: {e}")
            logger.critical(traceback.format_exc())
            raise

    async def sync_commands_safely(self):
        """Sync commands with comprehensive rate limiting protection"""
        try:
            if self.development_mode and self.dev_guild_id:
                # Development mode: sync to specific guild only (faster, no rate limits)
                guild = discord.Object(id=self.dev_guild_id)
                synced = await self.tree.sync(guild=guild)
                logger.info(f"✅ Dev mode: synced {len(synced)} commands to guild {self.dev_guild_id}")
            else:
                # Production mode: global sync with advanced rate limit handling
                await self.sync_commands_with_backoff()
        except Exception as e:
            logger.error(f"❌ Command sync failed: {e}")

    async def sync_commands_with_backoff(self):
        """Sync commands globally with intelligent rate limiting"""
        commands_list = list(self.tree.walk_commands())
        total_commands = len(commands_list)
        
        if total_commands == 0:
            logger.warning("⚠️ No commands found to sync")
            return
            
        logger.info(f"🔄 Syncing {total_commands} commands globally")
        
        # Implement exponential backoff for rate limiting
        max_retries = 5
        base_delay = 2.0
        max_delay = 60.0
        
        for attempt in range(max_retries):
            try:
                synced_commands = await self.tree.sync()
                logger.info(f"✅ Sync complete: {len(synced_commands)} commands")
                return
                
            except discord.HTTPException as e:
                if e.status == 429:
                    # Calculate exponential backoff with jitter
                    retry_after = getattr(e, 'retry_after', base_delay * (2 ** attempt))
                    delay = min(retry_after * (1 + 0.1 * attempt), max_delay)
                    
                    logger.warning(f"⚠️ Rate limited (attempt {attempt + 1}/{max_retries}), retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                    
                    if attempt == max_retries - 1:
                        logger.error(f"❌ Max retries reached. Consider using development mode or reducing command count.")
                        logger.error(f"💡 Tip: Use dev_guild_id in config for faster development testing")
                        return
                else:
                    logger.error(f"❌ HTTP error during sync: {e}")
                    return
                    
            except Exception as e:
                logger.error(f"❌ Unexpected error during sync: {e}")
                return
        
        logger.error(f"❌ Command sync failed after {max_retries} attempts")

    def get_user_data_manager(self):
        """Provide access to the UserDataManager instance for all systems"""
        return self.user_data_manager
        
    async def load_all_modules(self):
        """Load all bot modules efficiently without Discord timeout"""
        import sys
        import os
        
        # Add current directory to path for relative imports
        sys.path.insert(0, str(Path(__file__).parent))
        
        primary_modules = [
            ('admin_system', 'Systems.admin_system'),
            ('energon_system', 'Systems.EnergonPets.energon_system'),
            ('pets_system', 'Systems.EnergonPets.pets_system'),
        ]
        
        secondary_modules = [
        ('energon_commands', 'Systems.EnergonPets.energon_commands'),
        ('pets_commands', 'Systems.EnergonPets.pets_commands'),
        ('pets_mega', 'Systems.EnergonPets.pets_mega'),
        ('battle_commands', 'Systems.EnergonPets.battle_commands'),
        ('cybercoin_test', 'Systems.EnergonPets.cybercoin_test'),
        ('rpg_commands', 'Systems.EnergonPets.RPG.rpg_commands'),
        ('trivia', 'Systems.trivia'),
        ('fun_system', 'Systems.Random.fun_system'),
        ('talk_system', 'Systems.Random.talk_system'),
        ('themer', 'Systems.Random.themer'),
        ('hunger_games', 'Systems.Random.hunger_games'),
        ('pnw_recruit', 'Systems.PnW.recruit'),
        ('military_affairs', 'Systems.PnW.ma')
    ]
        
        all_modules = primary_modules + secondary_modules

        logger.info(f"🚀 Loading {len(all_modules)} modules...")
        
        # Load all modules efficiently
        await self._load_all_modules_parallel(primary_modules)
        await self._load_all_modules_parallel(secondary_modules)

    async def _load_all_modules_parallel(self, modules):
        """Load all modules in parallel with timeout protection"""
        
        async def _load_single_module(module_name, import_path):
            """Load a single module with timeout"""
            start_time = datetime.now()
            try:
                # Import with timeout protection
                module = __import__(import_path, fromlist=['setup'])
                
                # Look for setup function
                if hasattr(module, 'setup'):
                    setup_func = module.setup
                elif hasattr(module, f'setup_{module_name}'):
                    setup_func = getattr(module, f'setup_{module_name}')
                else:
                    logger.warning(f"⚠️ No setup function found for {module_name}")
                    return None
                
                # Execute setup with timeout
                if asyncio.iscoroutinefunction(setup_func):
                    await asyncio.wait_for(setup_func(self), timeout=10.0)
                else:
                    setup_func(self)
                
                load_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"✅ Loaded {module_name} in {load_time:.2f}s")
                return module_name
                
            except asyncio.TimeoutError:
                logger.error(f"⏰ Timeout loading {module_name}")
                self.failed_modules.append((module_name, "Timeout"))
                return None
            except Exception as e:
                error_msg = f"{type(e).__name__}: {e}"
                logger.error(f"❌ Failed to load {module_name}: {error_msg}")
                self.failed_modules.append((module_name, error_msg))
                return None

        # Create tasks for parallel loading
        tasks = []
        for module_name, import_path in modules:
            task = asyncio.create_task(_load_single_module(module_name, import_path))
            tasks.append(task)
        
        # Wait for all tasks to complete with timeout
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect successful loads
        for result in results:
            if result and isinstance(result, str):
                self.loaded_modules.append(result)
        
        total_time = (datetime.now() - self.startup_time).total_seconds()
        logger.info(f"🎯 All modules loaded in {total_time:.2f}s total")

    def log_startup_summary(self):
        """Log optimized startup summary with loading phases"""
        total_time = (datetime.now() - self.startup_time).total_seconds()
        
        # Categorize loaded modules for better reporting
        essential_loaded = [m for m in self.loaded_modules if m in ['admin_system']]
        secondary_loaded = [m for m in self.loaded_modules if m in [
            'rpg_system', 'rpg_commands', 'energon_system', 'energon_commands', 
            'pets_system', 'pets_commands', 'battle_commands', 'cybercoin_test'
        ]]
        optional_loaded = [m for m in self.loaded_modules if m in [
            'fun_system', 'talk_system', 'me', 'themer', 'hunger_games', 'pnw_recruit', 'military_affairs'
        ]]
        
        logger.info("=" * 60)
        logger.info("🎯 OPTIMIZED STARTUP SUMMARY")
        logger.info("=" * 60)
        logger.info(f"⏱️  Total startup time: {total_time:.2f}s")
        logger.info(f"✅ Successfully loaded: {len(self.loaded_modules)} modules")
        
        if essential_loaded:
            logger.info(f"🎯 Essential ({len(essential_loaded)}):")
            for module in essential_loaded:
                logger.info(f"   ✓ {module}")
        
        if secondary_loaded:
            logger.info(f"🔄 Secondary ({len(secondary_loaded)}):")
            for module in secondary_loaded:
                logger.info(f"   ✓ {module}")
        
        if optional_loaded:
            logger.info(f"⚡ Optional ({len(optional_loaded)}):")
            for module in optional_loaded:
                logger.info(f"   ✓ {module}")
        
        if self.failed_modules:
            critical_failed = [m for m, err in self.failed_modules if any(crit in m for crit in ['admin_system', 'user_data_manager'])]
            non_critical_failed = [m for m, err in self.failed_modules if m not in critical_failed]
            
            if critical_failed:
                logger.error(f"❌ Critical failures ({len(critical_failed)}):")
                for module, error in [(m, e) for m, e in self.failed_modules if m in critical_failed]:
                    logger.error(f"   ✗ {module}: {error}")
            
            if non_critical_failed:
                logger.warning(f"⚠️ Non-critical failures ({len(non_critical_failed)}):")
                for module, error in [(m, e) for m, e in self.failed_modules if m in non_critical_failed]:
                    logger.warning(f"   ✗ {module}: {error}")
        
        logger.info("=" * 60)

    async def on_ready(self):
        """Called when the bot is ready"""
        ready_time = datetime.now()
        startup_duration = (ready_time - self.startup_time).total_seconds()
        
        logger.info("=" * 60)
        logger.info(f"🚀 {self.user} has landed!")
        logger.info(f"🆔 Bot ID: {self.user.id}")
        logger.info(f"📊 Connected to {len(self.guilds)} guilds")
        logger.info(f"⏱️  Startup duration: {startup_duration:.2f}s")
        logger.info("=" * 60)
        
        # Log guild information
        if self.guilds:
            logger.info("📋 Connected Guilds:")
            for guild in self.guilds:
                logger.info(f"   🏰 {guild.name} ({guild.id}) - {guild.member_count} members")
        
        try:
            # Wait for Discord to stabilize connection
            logger.info("⏳ Waiting for Discord connection to stabilize...")
            await asyncio.sleep(5)
            
            # Sync commands with staged approach
            logger.info("🔄 Beginning staged command sync...")
            synced = await self.tree.sync()
            logger.info(f"✅ Synced {len(synced)} slash commands")
            
        except Exception as e:
            logger.error(f"❌ Failed to sync commands: {e}")
            logger.error(traceback.format_exc())

    async def on_member_join(self, member):
        """Welcome new members"""
        logger.info(f"👋 Member joined: {member.name} in guild {member.guild.name} (ID: {member.guild.id})")
        
        # Only send welcome message for the specific server
        if member.guild.id != 1294360926224519198:
            logger.info(f"❌ Wrong server - welcome message not sent (expected: 1294360926224519198, got: {member.guild.id})")
            return
            
        logger.info(f"✅ Correct server - sending welcome message for {member.name}")
            
        embed = discord.Embed(
            title="Welcome to Cybertron!",
            description=f"{member.mention} Cybertron is not only a home. It is a forge. Be sharpened or you will be scrapped!",
            color=discord.Color.green()
        )
        embed.add_field(name="📋 Server Rules", value="Read & Obey - <#1299147811161505803>", inline=False)
        embed.add_field(name="🎫 Here to Apply?", value="Create a ticket in - <#1294362865435807764>", inline=False)
        embed.add_field(name="📰 Prime News", value="News and Entertainment [HERE](https://discord.gg/EBwtQsw2Vy)", inline=False)
        embed.add_field(name="🏛️ FA Matters?", value="Want an embassy? Getting tossed & want it to stop? Join our - [FA Server](https://discord.gg/7YVJmtMZKN)", inline=False)
        embed.add_field(name="♾️ Prime Industries", value="Financial Advice, Nation Counsel, Alliance Page Setup & Exclusive Shows all right [HERE](https://discord.gg/uUrwR8A2Zm)", inline=False)
        embed.add_field(name="👑 Everyone Else", value="Bow before the might of Cybertr0n!", inline=False)
        embed.set_footer(text="Fornication with the perimeter may result in unsolicited educational encounters!")
        
        # Send to specific welcome channel
        welcome_channel = member.guild.get_channel(1377518499299332168)
        if welcome_channel and welcome_channel.permissions_for(member.guild.me).send_messages:
            logger.info(f"📤 Sending welcome message to {welcome_channel.name} (ID: {welcome_channel.id})")
            await welcome_channel.send(embed=embed)
            logger.info(f"✅ Welcome message sent successfully!")
        else:
            if not welcome_channel:
                logger.warning(f"❌ Welcome channel 1377518499299332168 not found!")
            else:
                logger.warning(f"❌ No permission to send messages in {welcome_channel.name}")
            
            # Fallback to system channel or first available channel
            if member.guild.system_channel:
                logger.info(f"📤 Fallback: Sending to system channel {member.guild.system_channel.name}")
                await member.guild.system_channel.send(embed=embed)
            else:
                logger.info("📤 Fallback: Searching for available text channel...")
                for channel in member.guild.text_channels:
                    if channel.permissions_for(member.guild.me).send_messages:
                        logger.info(f"📤 Fallback: Sending to {channel.name}")
                        await channel.send(embed=embed)
                        break

    async def on_command_error(self, ctx, error):
        """Handle command errors with detailed logging"""
        error_time = datetime.now()
        
        # Create detailed error context
        error_context = {
            'time': error_time.isoformat(),
            'guild': str(ctx.guild) if ctx.guild else 'DM',
            'channel': str(ctx.channel),
            'user': str(ctx.author),
            'user_id': ctx.author.id,
            'command': str(ctx.command),
            'message_content': ctx.message.content[:200] + '...' if len(ctx.message.content) > 200 else ctx.message.content,
            'error_type': type(error).__name__,
            'error_message': str(error)
        }
        
        # Log detailed error information
        logger.error("=" * 60)
        logger.error("🚨 COMMAND ERROR DETECTED")
        logger.error("=" * 60)
        logger.error(f"📅 Time: {error_context['time']}")
        logger.error(f"🏰 Guild: {error_context['guild']}")
        logger.error(f"💬 Channel: {error_context['channel']}")
        logger.error(f"👤 User: {error_context['user']} ({error_context['user_id']})")
        logger.error(f"📝 Command: {error_context['command']}")
        logger.error(f"📨 Message: {error_context['message_content']}")
        logger.error(f"❌ Error Type: {error_context['error_type']}")
        logger.error(f"💬 Error Message: {error_context['error_message']}")
        logger.error("📍 Stack Trace:")
        logger.error(traceback.format_exc())
        logger.error("=" * 60)
        
        # User-friendly error responses
        try:
            if isinstance(error, commands.CommandNotFound):
                await ctx.send(f"❌ Command not found: `{ctx.invoked_with}`")
            elif isinstance(error, commands.MissingRequiredArgument):
                await ctx.send(f"❌ Missing required argument: `{error.param}`")
            elif isinstance(error, commands.BadArgument):
                await ctx.send(f"❌ Bad argument: {error}")
            elif isinstance(error, commands.CheckFailure):
                await ctx.send("❌ You don't have permission to use this command.")
            elif isinstance(error, commands.CommandOnCooldown):
                await ctx.send(f"⏳ Command on cooldown. Try again in {error.retry_after:.1f} seconds.")
            elif isinstance(error, commands.MissingPermissions):
                missing_perms = ', '.join(error.missing_permissions)
                await ctx.send(f"❌ Missing permissions: {missing_perms}")
            elif isinstance(error, commands.BotMissingPermissions):
                missing_perms = ', '.join(error.missing_permissions)
                await ctx.send(f"❌ Bot missing permissions: {missing_perms}")
            else:
                # Unknown error - log and notify
                error_id = hash(str(error_context)) % 10000
                await ctx.send(
                    f"❌ An unexpected error occurred (Error #{error_id}).\n"
                    f"This has been logged and will be investigated."
                )
                
        except Exception as send_error:
            logger.error(f"Failed to send error message to user: {send_error}")
    
    async def on_error(self, event_method, *args, **kwargs):
        """Handle general bot errors"""
        error_time = datetime.now()
        logger.error("=" * 60)
        logger.error("🚨 GENERAL BOT ERROR")
        logger.error("=" * 60)
        logger.error(f"📅 Time: {error_time.isoformat()}")
        logger.error(f"🎯 Event: {event_method}")
        logger.error(f"📥 Args: {args}")
        logger.error(f"⚙️  Kwargs: {kwargs}")
        logger.error("📍 Stack Trace:")
        logger.error(traceback.format_exc())
        logger.error("=" * 60)
    
    def log_system_info(self):
        """Log detailed system information for debugging"""
        logger.info("=" * 60)
        logger.info("🔍 SYSTEM DIAGNOSTICS")
        logger.info("=" * 60)
        logger.info(f"🐍 Python version: {sys.version}")
        logger.info(f"🔧 Discord.py version: {discord.__version__}")
        logger.info(f"📁 Working directory: {os.getcwd()}")
        logger.info(f"📊 Loaded modules: {len(self.loaded_modules)}")
        logger.info(f"❌ Failed modules: {len(self.failed_modules)}")
        logger.info(f"📋 Error log entries: {len(self.error_log)}")
        logger.info("=" * 60)

class FeaturesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.current_page = 0
        self.commands = 8  # Default to Everyone commands count
        self.pages = [
            {
                "title": "🔓 Commands for Everyone (8 commands)",
                "description": """🤹 **Base & Fun Commands**
`/features` - Display this command list
`/hello` - Say hello to the bot
`/ping` - Check bot latency
`/what_is <topic>` - Learn about Transformers lore
`/trivia [category] [amount]` - Start a Transformers Trivia Session

📚 **Lore System**
`/random_lore` - Display a random lore entry
`/view_lore` - Browse all lore entries with pagination
`/lore_stats` - View statistics about the server's lore collection""",
                "color": 0x00ff00
            },
            {
                "title": "🔒 Commands Requiring Cybertronian Roles (13 commands)",
                "description": """🤖 **Transformer Identity**
`/analysis` - 5-question faction survey (Autobot/Decepticon/Maverick)
`/range [rounds]` - Start a shooting range session
`/rangestats [@user]` - View shooting range statistics
`/grump` - Get sweet ping revenge on Grump! 😉

🎮 **Interactive Features**
`/walktru` - Start an interactive walktru adventure
`/user_says [member]` - Analyze user message patterns and predict what they might say
`/joke` - Get a random joke to brighten your day!
`/roast [member]` - Get roasted by the bot! (Use at your own risk)
`/compliment [member]` - Get a nice compliment to brighten your day!
`/blessing [category]` - Receive a blessing from the Allspark
`/add_lore <title> <description>` - Add a new lore entry to the server's history
`/add_message_to_lore` - Add an existing message to the lore system
`/cybertron_games` - Initiate the ultimate Transformers deathmatch - The Cybertron Games""",
                "color": 0xff6600
            },
            {
                "title": "⛏️ Energon Rush Game (7 commands)",
                "description": """📊 **Stat Viewers**
`/rush_info` - Display information about Transformers: Energon Rush
`/energon_stats` - Check your Energon game statistics and global leaderboards
`/cybercoin_market` - View the CyberCoin market dashboard with live updates
`/cybercoin_profile` - View your personal CyberCoin portfolio and transaction history

⛏️ **Energon Rush Game**
`/scout` - Perform a low-risk scout for Energon
`/search` - Embark on a dangerous search for Energon
`/slots` - Play the Energon slot machine""",
                "color": 0x00ccff
            },
            {
                "title": "🐾 Digital Pets & Equipment (20 commands)",
                "description": """📊 **Stat Viewers**
`/pet` - View your digital pet's comprehensive status
`/pet_equipment` - View all your pet items with pagination
`/pet_info` - Comprehensive guide to all pet systems with 5 detailed pages
`/battle_stats [member]` - Show battle statistics for a user

🐾 **Digital Pets Management**
`/get_pet <faction>` - Get your first digital pet (autobot/decepticon)
`/combiner` - Start forming a Pet Combiner team!
`/rename_pet <new_name>` - Rename your digital pet
`/kill` - Permanently delete your digital pet
`/charge_pet [duration]` - Charge your pet's energy (15min/30min/1hour)
`/repair_pet [duration]` - Repair your pet's maintenance (15min/30min/1hour)
`/play [duration]` - Play with your pet to increase happiness (15min/30min/1hour)
`/train <difficulty>` - Train your pet (average/intense/godmode)
`/mission <difficulty>` - Send your pet on missions (easy/average/hard)
`/pet_equip [slot] [item_name]` - Equip items or view equipment slots
`/pet_unequip [slot]` - Unequip items from your pet

⚔️ **Pet Battle System**
`/battle` - Start a solo battle against a monster
`/group_battle` - Start a group battle for up to 4 players
`/pvp` - Start a PvP battle lobby with multiple modes (1v1, 2v2, 3v3, 4v4, FFA)
`/tournament` - Start a tournament with multiple rounds
`/mega_fight` - Challenge another combiner team to a Mega-Fight!""",
                "color": 0x00ccff
            },
            {
                "title": "🎮 CyberChronicles RPG (7 commands)",
                "description": """🏰 **CyberChronicles Adventures**
`/start_cyberchronicles <char>` - Begin an AI-generated CyberChronicles adventure
`/stop_cyberchronicles` - Stop the current CyberChronicles adventure session

⚔️ **Group Adventures**
`/cyber_random` - Start a random group adventure
`/cyber_battle` - Start a group battle adventure
`/cyber_event` - Start a group event adventure
`/cyber_story` - Start a group story adventure
`/cyber_info` - Show information about the Cybertronian RPG system

🎲 **RPG Features**
AI-generated stories, multiplayer support, progression system, character customization, group battles, interactive events""",
                "color": 0x9966ff
            }
        ]
    
    def get_embed(self):
        page = self.pages[self.current_page]
        embed = discord.Embed(
            title=page["title"],
            description=page["description"],
            color=page["color"]
        )
        
        total_commands = 54
        footer_text = f"| Page {self.current_page + 1} of 5 | Showing {self.commands} of {total_commands} commands |\n| Bow before the might of Cybertr0n! | Bot Credit - The Infamous Aries"
        embed.set_footer(text=footer_text)
        return embed

    @discord.ui.button(label="🔓 Everyone", style=discord.ButtonStyle.secondary)
    async def everyone_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        self.commands = 8
        await self.update_button_styles(button)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="🔒 Cybertronian", style=discord.ButtonStyle.secondary)
    async def cybertronian_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 1
        self.commands = 13
        await self.update_button_styles(button)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)
    
    @discord.ui.button(label="⛏️ Energon Rush", style=discord.ButtonStyle.secondary)
    async def energon_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 2
        self.commands = 7
        await self.update_button_styles(button)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)
    
    @discord.ui.button(label="🐾 Digital Pets", style=discord.ButtonStyle.secondary)
    async def pets_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 3
        self.commands = 20
        await self.update_button_styles(button)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)
    
    @discord.ui.button(label="🎮 CyberChronicles", style=discord.ButtonStyle.secondary)
    async def cyberchronicles_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 4
        self.commands = 7
        await self.update_button_styles(button)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def update_button_styles(self, active_button):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.style = discord.ButtonStyle.secondary
                if child == active_button:
                    child.style = discord.ButtonStyle.primary
    
    async def on_timeout(self):
        """Handle timeout by disabling all buttons"""
        try:
            for item in self.children:
                item.disabled = True
            # Note: We can't edit the message here since we don't have a reference to it
        except Exception:
            pass

# Commands
@commands.hybrid_command(name='features', description="Display all available bot commands")
async def features(ctx):
    """Show all bot features and commands"""
    view = FeaturesView()
    embed = view.get_embed()
    await ctx.send(embed=embed, view=view)

# Create bot instance
bot = AllsparkBot()

# Add commands to bot
bot.add_command(features)

# Debug command for testing error handling
@bot.command(name='debug', hidden=True)
@commands.is_owner()
async def debug_info(ctx):
    """Display detailed debug information"""
    embed = discord.Embed(
        title="🔍 Allspark Debug Information",
        description="Detailed system and error information",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="📊 Module Status",
        value=f"✅ Loaded: {len(bot.loaded_modules)}\n"
              f"❌ Failed: {len(bot.failed_modules)}\n"
              f"📋 Errors: {len(bot.error_log)}",
        inline=True
    )
    
    embed.add_field(
        name="🐍 System Info",
        value=f"Python: {sys.version.split()[0]}\n"
              f"Discord.py: {discord.__version__}\n"
              f"Uptime: {datetime.now() - bot.startup_time}",
        inline=True
    )
    
    if bot.failed_modules:
        failed_list = "\n".join([f"• {mod}: {err[:50]}..." for mod, err in bot.failed_modules[:5]])
        embed.add_field(
            name="❌ Failed Modules",
            value=failed_list or "None",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='test_error', hidden=True)
@commands.is_owner()
async def test_error(ctx):
    """Test error handling system"""
    try:
        # Intentionally cause an error
        result = 1 / 0
    except Exception as e:
        logger.error("Test error triggered by owner")
        await ctx.send(f"✅ Error handling system working! Check logs for details.")

# Run the bot
if __name__ == "__main__":
    try:
        logger.info("🚀 Starting AllsparkBot for SparkedHost deployment...")
        logger.info("=" * 60)
        logger.info("🔧 SPARKEDHOST STARTUP SEQUENCE")
        logger.info("=" * 60)
        
        # Log system information for debugging
        bot.log_system_info()
        
        # Start the bot
        logger.info("🎯 Connecting to Discord...")
        bot.run(TOKEN)
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot shutdown requested by user")
        sys.exit(0)
    except discord.LoginFailure as e:
        logger.critical("❌ Discord authentication failed")
        logger.critical(f"Token error: {e}")
        logger.critical("Check your DISCORD_TOKEN in config.py")
        sys.exit(1)
    except discord.HTTPException as e:
        logger.critical("❌ Discord HTTP error")
        logger.critical(f"HTTP error: {e}")
        logger.critical("This may be a temporary Discord API issue")
        sys.exit(1)
    except ConnectionError as e:
        logger.critical("❌ Network connection error")
        logger.critical(f"Connection error: {e}")
        logger.critical("Check your internet connection and SparkedHost network status")
        sys.exit(1)
    except Exception as e:
        logger.critical("💥 Critical error during bot startup")
        logger.critical(f"Error type: {type(e).__name__}")
        logger.critical(f"Error message: {e}")
        logger.critical("Full traceback:")
        logger.critical(traceback.format_exc())
        sys.exit(1)