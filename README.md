🌟 AllSpark Discord Bot
> The ultimate Transformers-themed Discord bot featuring advanced pet systems, RPG mechanics, interactive storytelling, and comprehensive entertainment features.
> 
</div>
📋 Table of Contents
 * 🚀 Overview
 * ✨ Features
 * 🎯 System Components
   * 🐾 EnergonPets System
   * 🤖 Random System
   * ⚔️ RPG System
   * 🏛️ PnW Recruitment
 * 🎮 Getting Started
 * 📊 Commands Reference
 * 🏗️ System Architecture
 * 🔧 Configuration
 * 📁 File Structure
 * 🛠️ Development
 * 🤝 Contributing
 * 📄 License
🚀 Overview
AllSpark is a feature-rich Discord bot that brings the Transformers universe to life through interactive systems, pet management, storytelling, and community engagement. Built with Discord.py and designed for scalability, it offers multiple interconnected systems that create a comprehensive user experience.
Key Highlights
 * 🐾 EnergonPets: Advanced pet management with 100-level progression.
 * 🤖 Random System: Interactive storytelling, AI conversations, and theme customization.
 * ⚔️ RPG System: Character creation and progression mechanics.
 * 🏛️ PnW Integration: Politics & War alliance recruitment automation.
 * 🎭 Theme System: Transformer identity creation and combiner teams.
✨ Features
🐾 EnergonPets System
 * 100-Level Progression: Evolve your pet from "Nano Core" to "Nano Supreme" with XP scaling from 50 to 6.32 billion.
 * Faction-Based: Choose Autobot or Decepticon for unique bonuses and themed UI.
 * Multi-Battle System: Engage in Solo, Group (4v1), PvP, and 4-way FFA battles.
 * Resource Management: Manage your pet's Energy, Maintenance, and Happiness through missions and activities.
 * Equipment & Loot: Earn and equip items in 3 slots (Chassis, Core, Utility) across 6 rarity tiers.
🤖 Random System
 * Interactive Stories: Play through 6 genres (Horror, Western, etc.) with unique mechanics and branching narratives.
 * Conversational AI: An advanced dialogue system with user analysis and a Transformers-themed joke API.
 * Mini-Games: Compete in a reaction-based Shooting Range, a Hunger Games sorter, and 6v6 Mega-Fights.
 * Personal Profiles: Track comprehensive user statistics and achievements.
⚔️ RPG System
 * Character Classes: Choose from 8 specialized classes per faction.
 * Stat System: Track ATT, DEF, DEX, INT, CHA, and HP attributes.
 * Cross-System Integration: Links directly with the EnergonPets and Theme systems for unified progression.
🏛️ PnW Recruitment
 * Real-Time Discovery: Automatically finds and targets unallied nations using the P&W API.
 * Intelligent Filtering: Excludes inactive, admin, and vacation-mode nations.
 * Personalized Messaging: Uses dynamic templates for customized recruitment messages.
 * API Safeguards: Built-in rate limit protection to prevent API abuse.
🎯 System Components
🐾 EnergonPets System (Systems/EnergonPets/)
A comprehensive robotic pet management platform with deep progression and customization.
Core Pet Features
 * Faction Selection: Choose between Autobot and Decepticon factions with distinct visual themes.
 * 100-Level Progression: Exponential XP requirements (50 → 6.32B XP) with automatic level-up notifications.
 * Progression Indicators: Stage emojis (🔩⚙️🔧🤖⚡💎🔱🌌✨👑) and faction-specific colors show progress.
 * Interactive UI: Button-based navigation with real-time updates, breakdown views, and faction-colored embeds.
 * Role-Based Access: Requires a "Cybertronian" role (Autobot, Decepticon, etc.) to participate.
 * Data Persistence: Automatic saving and migration system with JSON-based configuration.
Pet Activities & Training
 * 150+ Missions: 50 easy, 50 average, and 50 hard robotic missions with unique descriptions.
 * Resource Management: Manage Energy, Maintenance, and Happiness, which affect performance.
 * Training Programs: Three difficulty levels (average, intense, godmode) for progressive stat improvements.
 * Cooldown System: Duration-based activities (15min/30min/1hour options) for charging, playing, and repairing.
<details>
<summary><strong>Click to see a deep dive into the Energon Game Engine & Economy</strong></summary>
🚀 Energon Game System & Engine (energon_system.py, energon_commands.py)
A sophisticated 1286-line Energon mining and economy game featuring cross-channel multiplayer gameplay, real-time updates, comprehensive statistics tracking, and advanced market mechanics.
Core Game Features:
 * Transformers: Energon Rush: A global, cross-channel mining competition where the first to 10,000 Energon wins.
 * Persistent Banking: An Energon banking system for long-term progression outside of active games.
 * Pet Integration: Pets provide a 2% bonus per level during searches and gain XP from successful operations.
 * Probability System: A 5-tier outcome system for searches (disaster, loss, nothing, small find, major find).
Market & Economy Features:
 * Dynamic Events: Weighted random market events like surges, crashes, and chaos.
 * Holiday Events: Over 15 Transformers-themed holidays (e.g., Cybertron Day) with market multipliers (0.1x to 6.0x).
 * Slot Machine: A 3-difficulty slot machine with progressive rewards and emoji-based themes.
 * Banking System: A dual-account system for current game Energon and persistent banked Energon.
Technical Features:
 * Async Processing: Non-blocking game operations with robust error handling and fallback systems.
 * State Management: Channel-based game instances with lazy loading to ensure memory efficiency.
 * Cross-Server Support: Games and leaderboards function across multiple Discord servers.
</details>
⚔️ Advanced Battle System (battle_system.py)
A 1624-line turn-based battle engine with d20 roll mechanics, supporting multiple combat scenarios.
 * Multi-Battle Architecture: A unified system handling various combat types:
   * Solo Battles: Individual pet vs. monster encounters.
   * Group Battles: Cooperative 4v1 boss battles.
   * PvP Challenges: Direct pet vs. pet battles with other users.
   * Open FFA: Create 4-way Free-for-All battles that others can join.
 * Interactive UI: Advanced Discord Views for real-time battle management, enemy selection, and status updates.
 * Monster Database: 6 rarity tiers (Common to Mythic) across 3 enemy types (Monsters, Bosses, Titans).
 * Group Defense: Coordinated protection mechanics for team-based battles.
 * Energon Betting: Wager Energon in challenge-based battles with an automated prize pool.
 * Equipment Integration: Pet equipment stats directly impact attack, defense, and other battle attributes.
 * Loot System: Victories reward Energon, XP, and equipment drops based on rarity.
⚙️ Equipment & Inventory System
 * 3 Equipment Slots: Chassis Plating (defense), Energy Cores (energy), Utility Modules (happiness/maintenance).
 * 6 Rarity Tiers: Common, Uncommon, Rare, Epic, Legendary, and Mythic.
 * Stat Bonuses: Equipment provides direct improvements to pet stats.
 * Inventory Management: View and equip items via commands like /pet_equipment and /pet_equip.
🤖 Random System (Systems/Random/)
A 900-line entertainment suite featuring interactive games and immersive storytelling.
🎯 Shooting Range System
 * Reaction-Based Gameplay: A timed, button-clicking mini-game to test accuracy.
 * Multi-Round Sessions: Choose from 5, 15, 25, 50, or 100 round sessions.
 * Advanced Statistics: Tracks personal bests, overall accuracy, and session history.
 * 8-Tier Ranking System: Progress from a Recruit to a Matrix Bearer based on performance.
🏹 Hunger Games District Sorter
 * Intelligent Member Selection: Randomly sorts up to 24 server members into districts for a custom game.
 * Advanced Filtering: Can exclude bots, filter by role, or select from citizens only.
 * Automated Setup: Generates the necessary /hungergames add commands for easy game setup.
🤖 Mega-Fight System
 * 6v6 Team Combat: Form 6-member "Combiner" teams to battle other teams.
 * RNG-Based Combat: A best-of-3 battle system based on pure 1-100 dice rolls.
 * Reward & Penalty System: Winners gain Energon and Pet XP; losers face penalties.
🎭 WalkThru Interactive Stories
 * 6 Story Genres: Horror, Gangster, Knight, Robot, Western, and Wizard.
 * Unique Mechanics: Each genre has a unique stat system (e.g., Fear, Honor, Mana).
 * Branching Narratives: Your choices drive the story toward multiple possible endings.
💬 Talk System (talk_system.py)
 * Conversational AI: Features NLP-powered keyword extraction and analysis from user messages.
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
# Edit the .env file with your tokens and keys

 * Run the bot:
   python allspark.py

📊 Commands Reference
A full command reference can be found in COMMANDS.md. Here are some key commands:
| Category | Command | Description |
|---|---|---|
| EnergonPets | /get_pet | Create a new robotic pet. |
|  | /pet | View your interactive pet dashboard. |
|  | /mission | Send your pet on a mission for rewards. |
| Battle | /battle | Start a solo battle against a monster. |
|  | /pvp | Challenge another player to a pet battle. |
|  | /group_battle | Start a cooperative boss battle. |
| Economy | /search | Search for Energon in an active game. |
|  | /slots | Play the Energon slot machine. |
| Fun | /range | Start a session at the shooting range. |
|  | /walktru | Begin an interactive story. |
🏗️ System Architecture
AllSpark uses a modular architecture where each major feature (EnergonPets, Random, PnW) is a self-contained system.
 * Data Management: User data is stored in individual JSON files managed by a central user_data_manager, allowing for cross-system integration of stats like XP and achievements.
 * Performance: The bot uses asynchronous operations, lazy loading of data, and caching strategies to ensure efficiency and prevent memory bloat.
🔧 Configuration
All critical configurations are managed via environment variables in a .env file.
# .env.example
DISCORD_TOKEN=your_bot_token_here
GUILD_ID=your_server_id_here
PNW_API_KEY=your_pnw_api_key_here
OWNER_ID=your_discord_user_id

System-specific configurations (like story maps, monster data, and market events) are stored in JSON files within their respective system directories.
📁 File Structure
AllSpark/
├── 📄 allspark.py             # Main bot entry point
├── 📄 README.md
├── 📄 requirements.txt
├── 📄 .env.example
└── 📁 Systems/
    ├── 📁 EnergonPets/         # Pet management system
    │   ├── 📄 pets_system.py
    │   ├── 📄 battle_system.py
    │   └── 📄 energon_system.py
    ├── 📁 Random/              # Entertainment suite
    │   ├── 📄 fun_system.py
    │   ├── 📄 talk_system.py
    │   └── 📄 walktru.py
    ├── 📁 PnW/                 # Politics & War integration
    │   └── 📄 recruit.py
    └── 📁 Global Saves/        # User data storage

🛠️ Development
 * Setup: Follow the Installation steps.
 * Enable Debug Mode: Run the bot with the --debug flag for verbose logging.
   python allspark.py --debug

 * Reporting Issues:
   * Bugs: Use GitHub Issues with the provided template.
   * Features: Use GitHub Discussions to propose new ideas.
   * Security: Please email the maintainers directly.
🤝 Contributing
 * Fork the repository.
 * Create a new feature branch (git checkout -b feature/AmazingFeature).
 * Commit your changes (git commit -m 'Add some AmazingFeature').
 * Push to the branch (git push origin feature/AmazingFeature).
 * Open a Pull Request for review.
📄 License
This project is licensed under the MIT License - see the LICENSE file for details.

