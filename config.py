import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Discord Bot Configuration
TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = os.getenv('COMMAND_PREFIX', '!')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
PANDW_API_KEY = os.getenv('PANDW_API_KEY')
PANDW_BOT_KEY = os.getenv('PANDW_BOT_KEY')
RESULTS_CHANNEL_ID = int(os.getenv('RESULTS_CHANNEL_ID', '0'))
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '0'))
GRUMP_USER_ID = int(os.getenv('GRUMP_USER_ID', '0'))
ARIES_USER_ID = int(os.getenv('ARIES_USER_ID', '0'))

ROLE_IDS = {
    'Autobot': int(os.getenv('ROLE_AUTOBOT', '0')),
    'Maverick': int(os.getenv('ROLE_MAVERICK', '0')),
    'Decepticon': int(os.getenv('ROLE_DECEPTICON', '0')),
    'Cybertronian_Citizen': [int(role_id.strip()) for role_id in os.getenv('ROLE_CYBERTRONIAN_CITIZEN', '0').split(',')]
}