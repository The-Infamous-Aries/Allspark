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
        
        # Initialize bot data storage
        self.user_data = {}
        self.walktru_states = {}
        self.energon_game_data = {}
        self.energon_cooldowns = {}
        self.energon_challenges = {}
        self.player_stats = {}
        self.ping_cooldowns = {}
        self.hello_cooldowns = {}
        self.pet_data = {}
        self.pet_cooldowns = {}
        
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
            # Ensure all slash commands are synced after loading modules
            try:
                synced = await self.tree.sync()
                logger.info(f"✅ Final sync: {len(synced)} slash commands registered")
                # Log RPG-specific commands
                rpg_commands = [cmd for cmd in synced if cmd.name in [
                    'character_new', 'character_view', 'equip', 'start_cyberchronicles', 
                    'stop_cyberchronicles', 'kill_character'
                ]]
                if rpg_commands:
                    logger.info(f"🎮 RPG Commands synced: {[cmd.name for cmd in rpg_commands]}")
            except Exception as e:
                logger.error(f"❌ Final sync failed: {e}")
        except Exception as e:
            logger.critical(f"💥 Critical error during setup: {e}")
            logger.critical(traceback.format_exc())
            raise
        
    async def load_all_modules(self):
        """Load all bot modules and extensions with simplified error handling"""
        # Import systems from Systems directory
        import sys
        import os
        
        # Add current directory to path for relative imports
        sys.path.insert(0, str(Path(__file__).parent))
        
        modules = [
            # Core systems from Systems directory
            ('admin_system', 'Systems.admin_system'),
            ('energon_system', 'Systems.Energon.energon_system'),
            ('energon_commands', 'Systems.Energon.energon_commands'),
            ('fun_system', 'Systems.fun_system'),
            ('pets_system', 'Systems.Pets.pets_system'),
            ('pets_commands', 'Systems.Pets.pets_commands'),
            ('rpg_system', 'Systems.RPG.rpg_system'),
            ('rpg_commands', 'Systems.RPG.rpg_commands'),
            ('talk_system', 'Systems.talk_system'),
            ('theme_system', 'Systems.theme_system'),
            ('pnw_recruit', 'Systems.PnW.recruit'),
            ('user_data_manager', 'Systems.user_data_manager'),
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
        self.pages = [
            {
                "title": "🔓 Commands for Everyone (15 commands)",
                "description": """🤹 **Base & Fun Commands**
`/features` - Display this command list
`/random_lore` - Display a random lore entry
`/view_lore` - Browse all lore entries with pagination
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

🎯 **Utility Commands**
`/whois [member]` - View detailed user information
`/server_info` - Display server statistics and information""",
                "color": 0x00ff00
            },
            {
                "title": "🔒 Commands Requiring Cybertronian Roles (11 commands)",
                "description": """📚 **Lore System**
`/add_lore <title> <description>` - Add a new lore entry to the server's history
`/lore_stats` - View statistics about the server's lore collection

🤖 **Transformer Identity**
`/analysis` - 5-question faction survey (Autobot/Decepticon/Maverick)
`/spark` - Become a Transformer! Pick your class and faction
`/combiner` - Start forming a Combiner team!

🎯 **Shooting Range**
`/range [rounds]` - Start a shooting range session
`/rangestats [@user]` - View shooting range statistics

⚔️ **PvP Battle**
`/challenge <amount>` - Create an open Energon challenge
`/mega_fight` - Challenge another combiner team to a Mega-Fight!

🧌 **Special Features**
`/grump` - Get sweet ping revenge on Grump! 😉
`/theme` - Change your personal bot theme""",
                "color": 0xff6600
            },
            {
                "title": "⚡ Energon Rush & Digital Pets (19 commands)",
                "description": """📊 **Stat Viewers**
`/me [@user]` - View comprehensive profile with interactive navigation
`/pet` - View your digital pet's status
`/rush_info` - Display information about Transformers: Energon Rush
`/energon_level` - Check your current Energon level
`/leaderboard` - View Energon Rush leaderboards
`/cybercoin_market` - View the CyberCoin market dashboard
`/cybercoin_profile` - View your CyberCoin market portfolio

⛏️ **Energon Rush Game**
`/start_energon_rush` - Start a new round of Transformers: Energon Rush
`/scout` - Perform a low-risk scout for Energon
`/search` - Embark on a dangerous search for Energon
`/slots` - Play Emoji Slots for Fun or Energon
`/challenge <amount> [type]` - Create an open Energon challenge

🐾 **Digital Pets Management**
`/get_pet <faction>` - Get your first digital pet (autobot/decepticon)
`/rename_pet <new_name>` - Rename your digital pet
`/kill` - Permanently delete your digital pet
`/charge_pet` - Fully charge your pet's energy
`/repair_pet` - Fully repair your pet's maintenance

🎮 **Pet Activities**
`/play` - Play with your pet to increase happiness
`/train` - Train your pet to increase attack and defense
`/battle [difficulty]` - Battle monsters, bosses, or titans
`/mission <difficulty>` - Send your pet on a mission
`/group_battle` - Start a group battle with up to 4 players
`/open_challenge` - Start an open PvP challenge (up to 4 players)
`/pet_battle_info` - Learn everything about pet battles""",
                "color": 0x00ccff
            },
            {
                "title": "🎮 CyberChronicles RPG (12 commands)",
                "description": """🧞 **Character Management**
`/character_new <name> <faction> <class>` - Create a new Transformers character
`/character_view [name]` - View your characters with detailed stats
`/equip <char> <type> <item>` - Equip items to your character
`/kill_character` - Delete one of your characters permanently

🏰 **CyberChronicles Adventures**
`/start_cyberchronicles <char>` - Begin an AI-generated CyberChronicles adventure
`/stop_cyberchronicles` - Stop the current adventure session
`/cyber_random` - Trigger a Random Event
`/cyber_battle` - Trigger a Monster, Boss, or Titan Battle
`/cyber_event` - Trigger Events with Skill Challenges
`/cyber_story` - Trigger Story Segments
`/cyber_info` - View CyberChronicles info

🎲 **RPG Features**
Story Segments, Skill Challenges, Battles vs Monsters/Bosses/Titans
AI-generated stories, multiplayer support, progression system, voting combat""",
                "color": 0x9966ff
            },
            {
                "title": "♈ Aries ONLY Commands (12 commands)",
                "description": """🛠️ **Bot Management**
`/admin_clear` - Clear selected save data
`/monitor` - Display system resource usage monitor
`/uptime` - Check bot uptime and performance
`/logs` - View bot logs
`/logs_clear` - Clear bot logs
`/clear_debug_log` - Clear the bot debug log file
`/sync_commands` - Force sync all slash commands
`/system_status` - View comprehensive system status
`/module_reload <module>` - Reload specific bot modules
`/config_view` - View current configuration settings
`/backup_data` - Create manual backup of all user data

🤝 **Recruitment System**
`/recruit` - Shows unallied nations for recruitment""",
                "color": 0x9932cc
            }
        ]
    
    def get_embed(self):
        page = self.pages[self.current_page]
        embed = discord.Embed(
            title=page["title"],
            description=page["description"],
            color=page["color"]
        )
        
        total_commands = 60
        footer_text = f"Page {self.current_page + 1}/6 | Total Commands: {total_commands} | Bot Credit - The Infamous Aries"
        embed.set_footer(text=footer_text)
        return embed

    @discord.ui.button(label="🔓 Everyone", style=discord.ButtonStyle.secondary)
    async def everyone_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        await self.update_button_styles(button)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="🔒 Cybertronian", style=discord.ButtonStyle.secondary)
    async def cybertronian_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 1
        await self.update_button_styles(button)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)
    
    @discord.ui.button(label="⚡ Energon & Pets", style=discord.ButtonStyle.secondary)
    async def energon_pets_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 2
        await self.update_button_styles(button)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)
    
    @discord.ui.button(label="🎮 CyberChronicles", style=discord.ButtonStyle.secondary)
    async def cyberchronicles_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 3
        await self.update_button_styles(button)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)
    
    @discord.ui.button(label="♈ Aries ONLY", style=discord.ButtonStyle.secondary)
    async def aries_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 4  # Changed from 5 to 4 (last page)
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