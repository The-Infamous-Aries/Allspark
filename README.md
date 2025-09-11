🌟 AllSpark Discord Bot
> The ultimate Transformers-themed Discord bot featuring advanced pet systems, RPG mechanics, interactive storytelling, and comprehensive entertainment features.
> 
📋 Table of Contents
 * 🚀 Overview
 * ✨ Features
 * 🎯 System Components
 * 🎮 Getting Started
 * 📊 Commands Reference
 * 🏗️ System Architecture
 * 🔧 Configuration
 * 📁 File Structure
 * 🛠️ Development
 * 🤝 Contributing
 * 📄 License
 * 🙏 Acknowledgments
 * 📞 Support
🚀 Overview
AllSpark is a feature-rich Discord bot that brings the Transformers universe to life through interactive systems, pet management, storytelling, and community engagement. Built with Discord.py and designed for scalability, it offers multiple interconnected systems that create a comprehensive user experience.
Key Highlights
 * 🐾 EnergonPets: An advanced pet management system with 100 levels of progression.
 * 🤖 Random System: Interactive storytelling, AI conversations, and theme customization.
 * ⚔️ RPG System: Mechanics for character creation and progression.
 * 🏛️ PnW Integration: Automated alliance recruitment for Politics & War.
 * 🎭 Theme System: Create a unique Transformer identity and form combiner teams.
✨ Features
🐾 EnergonPets System
This is a comprehensive robotic pet management platform with deep progression mechanics and extensive customization.
 * 100-Level Progression: Pets evolve through 100 unique stages, from "Nano Core" to "Nano Supreme", with massive XP scaling from 50 to 6.32 billion XP.
 * Faction-Based: Choose between Autobot and Decepticon factions, each with unique bonuses and themed progression indicators (e.g., 🔩⚙️🔧🤖⚡💎🔱🌌✨👑).
 * Activities & Resources: Manage your pet's Energy, Maintenance, and Happiness through over 150 robotic missions (50 easy, 50 average, 50 hard). Use the cooldown system for duration-based activities like charging and repairing.
 * Loot System: Earn Energon, transformation items, and class-based equipment from missions and battles.
🤖 Random System
A comprehensive entertainment suite featuring interactive games, competitive systems, and immersive storytelling.
 * Interactive Stories: Choose from 6 genres (Horror, Gangster, Knight, Robot, Western, Wizard), each with unique mechanics and branching narratives.
 * Conversational AI: An NLP-powered talk system provides personalized, Transformers-themed dialogue, jokes, and lore.
 * Personal Profiles: A comprehensive user dashboard that displays Transformer identity, game statistics, pet info, and combiner teams.
⚔️ RPG System
 * Character Classes: Choose from 8 specialized classes per faction.
 * Stat System: Track attributes like ATT, DEF, DEX, INT, CHA, and HP.
 * Battle Mechanics: Engage in turn-based combat that integrates with both the EnergonPets and Theme Systems.
🏛️ PnW Recruitment
An automated, 887-line recruitment system for the Cybertr0n alliance in Politics & War.
 * Real-Time Discovery: Automatically finds unallied nations via the P&W API, with built-in safeguards against API abuse.
 * Intelligent Filtering: Excludes inactive nations (7+ days), admin nations, and those in vacation mode.
 * Personalized Messaging: Sends customized recruitment messages using JSON-based templates and dynamic placeholders.
🎯 System Components
🐾 EnergonPets System (Systems/EnergonPets/)
The core pet management platform.
 * Energon Game System: A sophisticated 1286-line Energon mining and economy game with a global Transformers: Energon Rush competition. It features a persistent banking system, a 5-tier probability system for searches, and cross-server leaderboards.
 * Energon Game Engine: A central EnergonGameManager class that handles all operations, including a dynamic Market System with over 15 Transformers-themed holidays, catastrophic events, and a 3-difficulty-level slot machine with progressive rewards.
 * Advanced Battle System: A 1624-line, turn-based combat engine with d20 roll mechanics. It supports multiple battle types (solo, group, PvP, energon challenges) and features a Monster Database with 6 rarity tiers and 3 enemy types.
 * Equipment & Inventory: Pets have 3 equipment slots (Chassis Plating, Energy Cores, Utility Modules) with 6 rarity tiers, providing stat bonuses.
🤖 Random System (Systems/Random/)
A 900-line comprehensive entertainment suite.
 * Shooting Range System: An interactive, reaction-based mini-game with configurable rounds, real-time scoring, and an 8-tier achievement system.
 * Hunger Games District Sorter: An intelligent member selection system that sorts up to 24 qualifying members into districts for a custom game.
 * Mega-Fight System: Team-based combat for 6-member combiner teams with pure RNG mechanics and automatic rewards/penalties.
 * Talk System: A 1965-line conversational AI suite with an extensive Transformers Lore knowledge base, a blessing system, and joke integration.
 * Theme System: A tool for creating a Transformer identity with a faction and one of 8 specialized classes, linking to the RPG and combat systems.
🏛️ PnW Recruitment System (Systems/PnW/)
 * Core Architecture: Handles 15,000 nation processing with sequential pagination and includes a dynamic messaging system with multi-tier options (individual, page-based, mass recruitment).
 * Interactive UI: The RecruitPaginatorView provides real-time navigation and action buttons for a smooth user experience.
🎮 Getting Started
Prerequisites
 * Python 3.8+
 * Discord Bot Token
 * Politics & War API Key (for recruitment features)
Installation
 * Clone the repository:
   git clone https://github.com/yourusername/AllSpark.git
cd AllSpark

 * Install dependencies:
   pip install -r requirements.txt

 * Configure environment variables:
   cp .env.example .env
# Edit .env with your tokens and keys

 * Run the bot:
   python allspark.py

📊 Commands Reference
🐾 EnergonPets & Energon Game
| Command | Description | Example |
|---|---|---|
| /get_pet | Create a new pet. | /get_pet autobot |
| /pet | View your interactive pet dashboard. | /pet |
| /rename_pet | Change your pet's name. | /rename_pet Optimus |
| /kill | Permanently delete your pet. | /kill |
| /charge_pet, /repair_pet, /play | Restore your pet's resources. | /charge_pet 30min |
| /train | Improve your pet's stats. | /train intense |
| /mission | Send your pet on a mission. | /mission hard |
| /pet_equipment | View your pet's inventory. | /pet_equipment |
| /pet_equip | Equip items to your pet. | /pet_equip chassis_plating armor |
| /rush_info | Display rules for the Energon Rush game. | /rush_info |
| /scout, /search | Perform an Energon search. | /search |
| /slots | Play the slot machine mini-game. | /slots 100 |
| /cybercoin_market | View current market events. | /cybercoin_market |
| /energon_stats | View Energon stats and leaderboards. | /energon_stats |
| /challenge | Challenge a player to an Energon PvP battle. | /challenge 500 |
⚔️ Battle Commands
| Command | Description | Example |
|---|---|---|
| /battle | Start a solo battle. | /battle |
| /group_battle | Start a group battle (up to 4 players). | /group_battle |
| /pvp | Challenge a player to a PvP battle. | /pvp @OptimusPrime |
| /group_pvp | Start a group PvP battle. | /group_pvp |
| /energon_challenge | Start a battle with an Energon wager. | /energon_challenge 1000 |
| /battle_info | Show battle rules. | /battle_info |
| /battle_stats | View battle statistics. | /battle_stats @Megatron |
🤖 Random System Commands
| Command | Description | Example |
|---|---|---|
| /hello, /ping | AI conversation commands. | /ping |
| /whatis | Query the Transformers lore database. | /whatis Optimus Prime |
| /blessing | Get a blessing from the Allspark. | /blessing wisdom |
| /joke, /roast, /compliment | Get jokes, roasts, or compliments. | /roast @user |
| /user_says | Analyze a user's message patterns. | /user_says @user1 |
| /walktru | Start an interactive story. | /walktru |
| /me | View your profile. | /me |
| /spark | Create a Transformer identity. | /spark autobot |
| /combiner | Form a combiner team. | /combiner |
| /analysis | Take a personality test. | /analysis |
| /range | Practice at the shooting range. | /range |
| /rangestats | View your shooting stats. | /rangestats |
| /hg_sorter | Sort members into Hunger Games districts. | /hg_sorter |
| /mega_fight | Start a team-based mega-fight. | /mega_fight |
🏛️ PnW Commands
| Command | Description | Access | Example |
|---|---|---|---|
| /recruit | Display unallied nations with an interactive UI. | Aries only | /recruit |
🏗️ System Architecture
AllSpark is built with a modular architecture to ensure scalability and maintainability.
Core Components
AllSpark/
├── allspark.py              # Main bot entry point
├── Systems/                 # Root directory for all bot systems
│   ├── EnergonPets/         # Pet management system
│   ├── Random/              # Entertainment suite
│   ├── PnW/                 # Politics & War integration
│   ├── RPG/                 # Role-playing system
│   └── Global Saves/        # User data storage
└── requirements.txt         # Python dependencies

Data Management
 * Storage Structure: Uses a combination of JSON files for configuration, individual user files for personalized data, and global statistics files for system-wide tracking.
 * Cross-System Integration: A central user_data_manager provides unified user profiles, allowing XP and achievements to be shared between systems.
 * Performance: Asynchronous operations, lazy loading, and caching strategies ensure efficient data handling and prevent memory bloat.
🔧 Configuration
Environment Variables (.env)
# Discord Configuration
DISCORD_TOKEN=your_bot_token_here
GUILD_ID=your_server_id_here

# Politics & War API
PNW_API_KEY=your_pnw_api_key_here
PNW_API_URL=https://api.politicsandwar.com/

# Bot Settings
OWNER_ID=your_discord_user_id
PREFIX=!
DEBUG=False

# System Paths
DATA_PATH=./Systems/Global Saves/
CONFIG_PATH=./Systems/Config/

System Configuration Files
 * Systems/Random/Talk/: Includes talk_templates.json, blessings.json, jokes.json, and user_lore.json.
 * Systems/Random/Walk Tru/: Contains story maps for each genre.
 * Systems/EnergonPets/: Stores pets_level.json, monsters.json, transformation_items.json, and other data files.
📁 File Structure
AllSpark/
├── 📄 allspark.py                 # Main bot entry point
├── 📄 README.md                   # This documentation
├── 📄 requirements.txt             # Python dependencies
├── 📄 .env.example                # Environment template
├── 📁 Systems/
│   ├── EnergonPets/            # Pet management system
│   │   ├── 📄 pets_system.py     # Core pet logic (1313 lines)
│   │   ├── 📄 battle_system.py   # Combat mechanics (1624 lines)
│   │   ├── 📄 energon_system.py  # Energon Game Engine (1286 lines)
│   │   ├── 📄 energon_commands.py  # Energon mining game (723 lines)
│   │   └── ... (other EnergonPets files)
│   ├── Random/                # Entertainment suite
│   │   ├── 📄 fun_system.py      # Interactive games (900 lines)
│   │   ├── 📄 talk_system.py     # Conversational AI (1965 lines)
│   │   └── ... (other Random files)
│   ├── PnW/                   # Politics & War system
│   │   └── 📄 recruit.py         # P&W recruitment (887 lines)
│   └── ... (other systems and data directories)
└── 📄 cyberchronicles.py         # Legacy features

🛠️ Development
Local Development Setup
 * Clone and setup: git clone and pip install -r requirements.txt.
 * Configuration: Copy .env.example to .env and fill in your credentials.
 * Testing: Run python allspark.py --debug to test locally.
Contribution Process
 * Fork the repository.
 * Create a feature branch.
 * Commit your changes.
 * Push to the branch.
 * Open a Pull Request.
Reporting Issues
 * Bug Reports: Use GitHub Issues with the provided template.
 * Feature Requests: Use GitHub Discussions.
 * Security Issues: Email the maintainers directly.
🙏 Acknowledgments
 * Discord.py Community: For the excellent Discord API wrapper.
 * Transformers Universe: For the inspiration for the theme and content.
 * Politics & War: For the recruitment system integration.
 * Contributors: All the amazing people who contributed to this project.
📞 Support
 * Discord Server: Join our support server
<div align="center">
<p><strong>AllSpark Bot</strong> - Bringing the Transformers universe to Discord</p>
<p>Built with ❤️ by the AllSpark Development Team</p>
</div>
