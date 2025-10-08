"""
Configuration template for AllSpark Discord Bot.

Copy this file to config.py and update with your actual values.
This file contains configuration for Discord bot tokens, API keys, and server settings.

IMPORTANT: Never commit the actual config.py file to version control!
"""

import os
from dotenv import load_dotenv
from typing import Dict, List, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    import discord
    from discord.ext import commands

# Load environment variables from .env file
load_dotenv()

# =============================================================================
# REQUIRED DISCORD CONFIGURATION
# =============================================================================

# Your Discord bot token (get from Discord Developer Portal)
TOKEN = os.getenv('DISCORD_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# Command prefix for text commands (can be changed per server)
PREFIX = os.getenv('COMMAND_PREFIX', '!')

# =============================================================================
# API KEYS (OPTIONAL - SET IF USING FEATURES)
# =============================================================================

# Gemini API key for AI features (optional)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

# Groq API key for AI features (optional) 
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')

# Politics and War API key (required for PnW recruitment features)
PANDW_API_KEY = os.getenv('PANDW_API_KEY', '')

# Politics and War bot key (required for some PnW features)
PANDW_BOT_KEY = os.getenv('PANDW_BOT_KEY', '')

# =============================================================================
# SERVER CONFIGURATION
# =============================================================================

# Default Cybertron Alliance ID (for PnW features)
CYBERTRON_ALLIANCE_ID = os.getenv('CYBERTRON_ALLIANCE_ID', '9999')

# User IDs for bot administrators (set to 0 to disable)
GRUMP_USER_ID = int(os.getenv('GRUMP_USER_ID', '0'))
ARIES_USER_ID = int(os.getenv('ARIES_USER_ID', '0'))
PRIMAL_USER_ID = int(os.getenv('PRIMAL_USER_ID', '0'))
CARNAGE_USER_ID = int(os.getenv('CARNAGE_USER_ID', '0'))
BENEVOLENT_USER_ID = int(os.getenv('BENEVOLENT_USER_ID', '0'))
TECH_USER_ID = int(os.getenv('TECH_USER_ID', '0'))

def _get_admin_user_id() -> int:
    """Get the primary admin user ID."""
    admin_from_env = os.getenv('ADMIN_USER_ID')
    if admin_from_env and admin_from_env != '0':
        return int(admin_from_env)
    
    # Fallback to first available admin
    authorized_users = [ARIES_USER_ID, PRIMAL_USER_ID, CARNAGE_USER_ID, BENEVOLENT_USER_ID]
    for user_id in authorized_users:
        if user_id != 0:
            return user_id
    return 0

ADMIN_USER_ID = _get_admin_user_id()

# Default channel IDs
DEFAULT_RESULTS_CHANNEL_ID = int(os.getenv('RESULTS_CHANNEL_ID', '0'))

# Default role IDs for different factions
DEFAULT_ROLE_IDS = {
    'Autobot': [int(role_id.strip()) for role_id in os.getenv('ROLE_AUTOBOT', '0').split(',') if role_id.strip() != '0'],
    'Maverick': [int(role_id.strip()) for role_id in os.getenv('ROLE_MAVERICK', '0').split(',') if role_id.strip() != '0'],
    'Decepticon': [int(role_id.strip()) for role_id in os.getenv('ROLE_DECEPTICON', '0').split(',') if role_id.strip() != '0'],
    'Cybertronian_Citizen': [int(role_id.strip()) for role_id in os.getenv('ROLE_CYBERTRONIAN_CITIZEN', '0').split(',') if role_id.strip() != '0'],
    'Predaking': [int(role_id.strip()) for role_id in os.getenv('ROLE_PREDAKING', '0').split(',') if role_id.strip() != '0'],
    'IA': [int(role_id.strip()) for role_id in os.getenv('IA_ROLE_ID', '0').split(',') if role_id.strip() != '0'],
    'MG': [int(role_id.strip()) for role_id in os.getenv('MG_ROLE_ID', '0').split(',') if role_id.strip() != '0'],
    'HG': [int(role_id.strip()) for role_id in os.getenv('HG_ROLE_ID', '0').split(',') if role_id.strip() != '0']
}

# =============================================================================
# SERVER-SPECIFIC CONFIGURATION PARSING
# =============================================================================

def _parse_server_config() -> Dict[int, Dict[str, Union[int, List[int]]]]:
    """Parse server-specific configuration from environment variables."""
    server_configs = {}
    
    for key, value in os.environ.items():
        if key.startswith('SERVER_') and '_' in key[7:]:
            try:
                parts = key[7:].split('_', 1) 
                guild_id = int(parts[0])
                setting_name = parts[1]      
                
                if guild_id not in server_configs:
                    server_configs[guild_id] = {}
                
                if setting_name == 'RESULTS_CHANNEL_ID':
                    server_configs[guild_id]['RESULTS_CHANNEL_ID'] = int(value)
                elif setting_name.startswith('ROLE_') or setting_name.endswith('_ROLE_ID'):
                    # Handle both ROLE_ prefix and _ROLE_ID suffix patterns
                    if setting_name.startswith('ROLE_'):
                        role_env_name = setting_name[5:]
                    elif setting_name.endswith('_ROLE_ID'):
                        role_env_name = setting_name[:-8]  # Remove '_ROLE_ID' suffix
                    else:
                        role_env_name = setting_name
                    
                    role_name_map = {
                        'AUTOBOT': 'Autobot',
                        'MAVERICK': 'Maverick', 
                        'DECEPTICON': 'Decepticon',
                        'CYBERTRONIAN_CITIZEN': 'Cybertronian_Citizen',
                        'PREDAKING': 'Predaking',
                        'IA': 'IA',
                        'MG': 'MG',
                        'HG': 'HG'
                    }
                    role_name = role_name_map.get(role_env_name, role_env_name)            
                    
                    if 'ROLE_IDS' not in server_configs[guild_id]:
                        server_configs[guild_id]['ROLE_IDS'] = {}
                    
                    server_configs[guild_id]['ROLE_IDS'][role_name] = [
                        int(role_id.strip()) for role_id in value.split(',') 
                        if role_id.strip() != '0' and role_id.strip()
                    ]
            except (ValueError, IndexError):
                continue   
    
    return server_configs

SERVER_CONFIGS = _parse_server_config()

# =============================================================================
# CONFIGURATION ACCESS FUNCTIONS
# =============================================================================

def get_server_config(guild_id: Optional[int], refresh: bool = False) -> Dict[str, Union[int, Dict[str, List[int]]]]:
    """
    Get configuration for a specific server.
    
    Args:
        guild_id: The Discord guild (server) ID
        refresh: Whether to refresh the configuration from environment variables
        
    Returns:
        Dictionary containing server-specific configuration
    """
    global SERVER_CONFIGS
    
    if refresh:
        SERVER_CONFIGS = _parse_server_config()
    
    if guild_id and guild_id in SERVER_CONFIGS:
        config = SERVER_CONFIGS[guild_id].copy()
        
        # Ensure all required keys exist with defaults
        if 'RESULTS_CHANNEL_ID' not in config:
            config['RESULTS_CHANNEL_ID'] = DEFAULT_RESULTS_CHANNEL_ID
        
        if 'ROLE_IDS' not in config:
            config['ROLE_IDS'] = DEFAULT_ROLE_IDS.copy()
        else:
            # Merge with defaults for missing roles
            merged_roles = DEFAULT_ROLE_IDS.copy()
            merged_roles.update(config['ROLE_IDS'])
            config['ROLE_IDS'] = merged_roles
        
        return config
    
    # Return default configuration
    return {
        'RESULTS_CHANNEL_ID': DEFAULT_RESULTS_CHANNEL_ID,
        'ROLE_IDS': DEFAULT_ROLE_IDS.copy()
    }

def get_results_channel_id(guild_id: Optional[int] = None) -> int:
    """Get the results channel ID for a specific server."""
    return get_server_config(guild_id)['RESULTS_CHANNEL_ID']

def get_role_ids(guild_id: Optional[int] = None) -> Dict[str, List[int]]:
    """Get the role IDs for a specific server."""
    return get_server_config(guild_id)['ROLE_IDS']

def get_guild_id_from_context(ctx_or_interaction: Union["commands.Context", "discord.Interaction", "discord.Guild", int, None]) -> Optional[int]:
    """
    Extract guild ID from various Discord context objects.
    Args:
        ctx_or_interaction: Context, Interaction, Guild object, guild ID, or None   
    Returns:
        Guild ID or None if not available
    """
    if ctx_or_interaction is None:
        return None  
    if isinstance(ctx_or_interaction, int):
        return ctx_or_interaction 
    if hasattr(ctx_or_interaction, 'id') and hasattr(ctx_or_interaction, 'name'):
        return ctx_or_interaction.id  
    if hasattr(ctx_or_interaction, 'guild') and ctx_or_interaction.guild:
        return ctx_or_interaction.guild.id   
    return None

def get_channel_ids(guild_id: Optional[int] = None) -> Dict[str, int]:
    """
    Get channel IDs for a specific server, including cybercoin market channel.
    
    Args:
        guild_id: The Discord guild (server) ID
        
    Returns:
        Dictionary containing channel IDs with cybercoin_market key
    """
    # Get server config to check for server-specific channel IDs
    server_config = get_server_config(guild_id)
    
    # Default channel IDs - can be overridden by environment variables
    default_channel_ids = {
        'cybercoin_market': int(os.getenv('CYBERCOIN_MARKET_CHANNEL_ID', '0')),
        'results': server_config.get('RESULTS_CHANNEL_ID', DEFAULT_RESULTS_CHANNEL_ID),
        'general': int(os.getenv('GENERAL_CHANNEL_ID', '0')),
        'bot_commands': int(os.getenv('BOT_COMMANDS_CHANNEL_ID', '0'))
    }
    
    # Check for server-specific channel IDs in environment variables
    if guild_id:
        server_channels = {}
        for key, value in os.environ.items():
            if key.startswith(f'SERVER_{guild_id}_') and key.endswith('_CHANNEL_ID'):
                try:
                    # Extract channel name from SERVER_GUILID_NAME_CHANNEL_ID format
                    # For example: SERVER_1294360926224519198_CYBERCOIN_MARKET_CHANNEL_ID
                    prefix = f'SERVER_{guild_id}_'
                    channel_part = key[len(prefix):-len('_CHANNEL_ID')]  # Remove prefix and suffix
                    
                    # Convert to simple format, but preserve underscores for known channel names
                    if 'CYBERCOIN_MARKET' in channel_part:
                        channel_name = 'cybercoin_market'
                    else:
                        channel_name = channel_part.lower().replace('_', '')
                    
                    server_channels[channel_name] = int(value)
                except (ValueError, AttributeError):
                    continue
            elif key.startswith(f'SERVER_{guild_id}_CHANNEL_'):
                try:
                    # Handle older format: SERVER_GUILID_CHANNEL_NAME
                    channel_name = key.replace(f'SERVER_{guild_id}_CHANNEL_', '').lower()
                    server_channels[channel_name] = int(value)
                except (ValueError, AttributeError):
                    continue
        
        # Merge server-specific channels with defaults
        if server_channels:
            default_channel_ids.update(server_channels)
    
    return default_channel_ids

# =============================================================================
# LEGACY COMPATIBILITY
# =============================================================================

RESULTS_CHANNEL_ID = DEFAULT_RESULTS_CHANNEL_ID