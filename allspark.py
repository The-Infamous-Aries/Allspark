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

# Import configuration
try:
    from config import TOKEN, PREFIX, ADMIN_USER_ID, RESULTS_CHANNEL_ID, GRUMP_USER_ID, ARIES_USER_ID, ROLE_IDS
    logger.info("✅ Configuration loaded successfully")
except ImportError as e:
    logger.error(f"❌ Failed to load configuration: {e}")
    raise

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
        """Sync commands globally with exponential backoff and batching"""
        # Get all commands before syncing to count them
        commands_list = list(self.tree.walk_commands())
        total_commands = len(commands_list)
        
        if total_commands == 0:
            logger.warning("⚠️ No commands found to sync")
            return
            
        logger.info(f"🔄 Preparing to sync {total_commands} commands globally")
        
        # Discord's global rate limit is ~200 commands per day
        # We'll use conservative timing: 1 command per second max
        max_retries = 10
        base_delay = 30  # Start with 30 seconds for global sync
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 Attempt {attempt + 1}/{max_retries} to sync commands...")
                
                # Add pre-sync delay for rate limit reset
                if attempt > 0:
                    delay = base_delay * (2 ** (attempt - 1))  # Exponential backoff
                    logger.info(f"⏳ Waiting {delay}s before retry...")
                    await asyncio.sleep(delay)
                
                # Perform the sync
                synced = await self.tree.sync()
                
                logger.info(f"✅ Successfully synced {len(synced)} slash commands globally")
                
                # Log command breakdown by category
                categories = {}
                for cmd in synced:
                    category = 'General'
                    if any(name in cmd.name for name in ['character', 'cyber', 'rpg']):
                        category = 'RPG'
                    elif any(name in cmd.name for name in ['pet', 'battle', 'energon']):
                        category = 'Pets/Energon'
                    elif any(name in cmd.name for name in ['fun', 'me', 'talk']):
                        category = 'Fun'
                    
                    categories[category] = categories.get(category, 0) + 1
                
                for category, count in categories.items():
                    logger.info(f"📊 {category}: {count} commands")
                
                break
                
            except discord.HTTPException as e:
                if e.status == 429:
                    retry_after = getattr(e, 'retry_after', base_delay * (2 ** attempt))
                    retry_after = min(retry_after, 300)  # Cap at 5 minutes
                    
                    if attempt < max_retries - 1:
                        logger.warning(f"⚠️ Rate limited by Discord. Retry after {retry_after}s...")
                        await asyncio.sleep(retry_after)
                    else:
                        logger.error(f"❌ Max retries reached. Failed to sync commands.")
                        raise
                else:
                    logger.error(f"❌ HTTP error during sync: {e.status} - {e}")
                    raise
            except Exception as e:
                logger.error(f"❌ Unexpected error during sync: {type(e).__name__}: {e}")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.info(f"⏳ Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    raise

    def get_user_data_manager(self):
        """Provide access to the UserDataManager instance for all systems"""
        return self.user_data_manager
        
    async def load_all_modules(self):
        """Load all bot modules and extensions with simplified error handling"""
        # Import systems from Systems directory
        import sys
        import os
        
        # Add current directory to path for relative imports
        sys.path.insert(0, str(Path(__file__).parent))
        
        modules = [
            # Core systems from Systems directory (ordered by dependency)
            ('admin_system', 'Systems.admin_system'),
            ('energon_system', 'Systems.EnergonPets.energon_system'),
            ('energon_commands', 'Systems.EnergonPets.energon_commands'),
            ('pets_system', 'Systems.EnergonPets.pets_system'),
            ('pets_commands', 'Systems.EnergonPets.pets_commands'),
            ('battle_commands', 'Systems.EnergonPets.battle_commands'),
            ('fun_system', 'Systems.Random.fun_system'),
            ('talk_system', 'Systems.Random.talk_system'),
            ('me', 'Systems.Random.me'),
            ('themer', 'Systems.Random.themer'),
            ('rpg_system', 'Systems.RPG.rpg_system'),
            ('rpg_commands', 'Systems.RPG.rpg_commands'),
            ('pnw_recruit', 'Systems.PnW.recruit'),
        ]

        logger.info(f"📦 Loading {len(modules)} modules...")
        
        for module_name, import_path in modules:
            start_time = datetime.now()
            try:
                logger.debug(f"🔄 Attempting to load {module_name} from {import_path}")
                
                # Import the module
                module = __import__(import_path, fromlist=['setup'])
                
                # Look for setup function
                if hasattr(module, 'setup'):
                    setup_func = module.setup
                elif hasattr(module, f'setup_{module_name}'):
                    setup_func = getattr(module, f'setup_{module_name}')
                else:
                    logger.warning(f"⚠️ No setup function found for {module_name}")
                    continue
                
                # Execute setup function
                if asyncio.iscoroutinefunction(setup_func):
                    await setup_func(self)
                else:
                    setup_func(self)
                
                load_time = (datetime.now() - start_time).total_seconds()
                self.loaded_modules.append(module_name)
                logger.info(f"✅ Loaded {module_name} in {load_time:.2f}s")
                
            except ImportError as e:
                error_msg = f"ImportError: {e}"
                logger.error(f"❌ Failed to load {module_name}: {error_msg}")
                self.failed_modules.append((module_name, error_msg))
                
            except Exception as e:
                error_msg = f"{type(e).__name__}: {e}"
                logger.error(f"❌ Failed to load {module_name}: {error_msg}")
                self.failed_modules.append((module_name, error_msg))

    def log_startup_summary(self):
        """Log simplified startup summary"""
        total_time = (datetime.now() - self.startup_time).total_seconds()
        
        logger.info("=" * 60)
        logger.info("🎯 STARTUP SUMMARY")
        logger.info("=" * 60)
        logger.info(f"⏱️  Total startup time: {total_time:.2f}s")
        logger.info(f"✅ Successfully loaded: {len(self.loaded_modules)} modules")
        
        if self.loaded_modules:
            for module in self.loaded_modules:
                logger.info(f"   ✓ {module}")
        
        if self.failed_modules:
            logger.error(f"❌ Failed to load: {len(self.failed_modules)} modules")
            for module, error in self.failed_modules:
                logger.error(f"   ✗ {module}: {error}")
        
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
            synced = await self.tree.sync()
            logger.info(f"✅ Synced {len(synced)} slash commands")
            
        except Exception as e:
            logger.error(f"❌ Failed to sync commands: {e}")
            logger.error(traceback.format_exc())

    async def on_member_join(self, member):
        """Welcome new members"""
        embed = discord.Embed(
            title=f"Welcome {member.name} to {member.guild.name}!",
            description="Don't Break Anything You Can't Pay For!",
            color=discord.Color.green()
        )
        embed.add_field(name="Server Rules", value="Please read #rules", inline=False)
        embed.add_field(name="Here to Apply?", value="Create a ticket in #tickets", inline=False)
        embed.add_field(name="Here To Game?", value="Grab roles in #roles", inline=False)
        embed.add_field(name="Everyone Else", value="Bow Before Cybertr0n's Might!", inline=False)
        
        if member.guild.system_channel:
            await member.guild.system_channel.send(embed=embed)
        else:
            for channel in member.guild.text_channels:
                if channel.permissions_for(member.guild.me).send_messages:
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
        self.commands = 12  # Default to Everyone commands count
        self.pages = [
            {
                "title": "🔓 Commands for Everyone (12 commands)",
                "description": """🤹 **Base & Fun Commands**
`/features` - Display this command list
`/walktru` - Start an interactive walktru adventure
`/hg_sorter [include_bots] [cybertron_citizens_only]` - Sort 24 users into districts

🤖 **Allspark Conversations**
`/joke` - Get a random joke to brighten your day!
`/ping` - Check bot latency
`/roast [member]` - Get roasted by the bot! (Use at your own risk)
`/compliment [member]` - Get a nice compliment to brighten your day!
`/what_is <topic>` - Learn about Transformers lore
`/hello` - Say hello to the bot
`/blessing [category]` - Receive a blessing from the Allspark
`/user_says [member]` - Analyze user message patterns and predict what they might say

📚 **Lore System**
`/random_lore` - Display a random lore entry
`/view_lore` - Browse all lore entries with pagination""",
                "color": 0x00ff00
            },
            {
                "title": "🔒 Commands Requiring Cybertronian Roles (12 commands)",
                "description": """🤖 **Transformer Identity**
`/analysis` - 5-question faction survey (Autobot/Decepticon/Maverick)
`/spark` - Become a Transformer! Pick your class and faction
`/combiner` - Start forming a Combiner team!
`/mega_fight` - Challenge another combiner team to a Mega-Fight!

📚 **Fun Stuff**
`/add_lore <title> <description>` - Add a new lore entry to the server's history
`/lore_stats` - View statistics about the server's lore collection
`/range [rounds]` - Start a shooting range session
`/rangestats [@user]` - View shooting range statistics
`/grump` - Get sweet ping revenge on Grump! 😉""",
                "color": 0xff6600
            },
            {
                "title": "⛏️ Energon Rush Game (8 commands)",
                "description": """📊 **Stat Viewers**
`/profile [@user]` - View comprehensive profile with interactive navigation
`/rush_info` - Display information about Transformers: Energon Rush
`/energon_stats` - Check your Energon game statistics and global leaderboards
`/cybercoin_market` - View the CyberCoin market dashboard with live updates
`/cybercoin_profile` - View your personal CyberCoin portfolio and transaction history

⛏️ **Energon Rush Game**
`/scout` - Perform a low-risk scout for Energon
`/search` - Embark on a dangerous search for Energon
`/slots` - Play Emoji Slots for Fun or Energon""",
                "color": 0x00ccff
            },
            {
                "title": "🐾 Digital Pets & Equipment (16 commands)",
                "description": """📊 **Stat Viewers**
`/pet` - View your digital pet's comprehensive status
`/pet_equipment` - View all your pet items with pagination
`/battle_info` - Show comprehensive battle information and rules
`/battle_stats [member]` - Show battle statistics for a user

🐾 **Digital Pets Management**
`/get_pet <faction>` - Get your first digital pet (autobot/decepticon)
`/pet` - View your digital pet's comprehensive status
`/rename_pet <new_name>` - Rename your digital pet
`/kill` - Permanently delete your digital pet
`/charge_pet [duration]` - Charge your pet's energy (15min/30min/1hour)
`/repair_pet [duration]` - Repair your pet's maintenance (15min/30min/1hour)
`/play [duration]` - Play with your pet to increase happiness (15min/30min/1hour)
`/train <difficulty>` - Train your pet (average/intense/godmode)
`/mission <difficulty>` - Send your pet on missions (easy/average/hard)
`/pet_equip [slot] [item_name]` - Equip items or view equipment slots

⚔️ **Pet Battle System**
`/battle [enemy_type] [rarity]` - Start a solo battle against a monster
`/group_battle [enemy_type] [rarity]` - Start a group battle for up to 4 players
`/pvp <target>` - Challenge another player to PvP battle
`/group_pvp` - Start a group PvP battle for up to 4 players
`/energon_challenge <amount>` - Start an energon challenge with a bet""",
                "color": 0x00ccff
            },
            {
                "title": "🎮 CyberChronicles RPG (11 commands)",
                "description": """🧞 **Character Management**
`/character_new <name> <faction> <class>` - Create a new Transformers character
`/character_view [name]` - View your characters with detailed stats
`/equip <char> <type> <item>` - Equip items to your character
`/kill_character` - Delete one of your characters permanently

🏰 **CyberChronicles Adventures**
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
        
        total_commands = 59
        footer_text = f"| Page {self.current_page + 1} of 5 | Showing {self.commands} of {total_commands} commands |\n| Bow before the might of Cybertr0n! | Bot Credit - The Infamous Aries"
        embed.set_footer(text=footer_text)
        return embed

    @discord.ui.button(label="🔓 Everyone", style=discord.ButtonStyle.secondary)
    async def everyone_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        self.commands = 12
        await self.update_button_styles(button)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="🔒 Cybertronian", style=discord.ButtonStyle.secondary)
    async def cybertronian_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 1
        self.commands = 12
        await self.update_button_styles(button)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)
    
    @discord.ui.button(label="⛏️ Energon Rush", style=discord.ButtonStyle.secondary)
    async def energon_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 2
        self.commands = 8
        await self.update_button_styles(button)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)
    
    @discord.ui.button(label="🐾 Digital Pets", style=discord.ButtonStyle.secondary)
    async def pets_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 3
        self.commands = 16
        await self.update_button_styles(button)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)
    
    @discord.ui.button(label="🎮 CyberChronicles", style=discord.ButtonStyle.secondary)
    async def cyberchronicles_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 4
        self.commands = 11
        await self.update_button_styles(button)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def update_button_styles(self, active_button):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.style = discord.ButtonStyle.secondary
                if child == active_button:
                    child.style = discord.ButtonStyle.primary

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
        logger.info("🚀 Starting AllsparkBot...")
        bot.log_system_info()
        bot.run(TOKEN)
    except KeyboardInterrupt:
        logger.info("🛑 Bot shutdown requested by user")
    except discord.LoginFailure as e:
        logger.critical("❌ Invalid Discord token provided")
        logger.critical(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.critical("💥 Critical error during bot startup")
        logger.critical(f"Error: {type(e).__name__}: {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1)