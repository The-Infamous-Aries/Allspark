# 🌟 The AllSpark

> **The most advanced and complete Transformers-themed Discord bot.**  
> 🚨 **For help, bug reports, or feature requests: [Join the Support Discord Server!](https://discord.gg/pDTKNQJXdh)**

---

## 📋 Table of Contents

- [🚀 Overview](#-overview)
- [✨ Major Features](#-major-features)
  - [🐾 EnergonPets System](#-energonpets-system)
  - [🤖 Random System](#-random-system)
  - [🏛️ PnW Recruitment System](#-pnw-recruitment-system)
  - [👑 Admin System](#-admin-system)
  - [🗂️ User Data Manager](#️-user-data-manager)
- [🗂️ System Components & Architecture](#️-system-components--architecture)
- [📜 Complete Commands List](#-complete-commands-list)
- [🏗️ Project Structure](#-project-structure)
- [🔧 Configuration & Setup](#-configuration--setup)
- [🛠️ Development & Support](#️-development--support)

---

## 🚀 Overview

The AllSpark is a comprehensive Discord bot built with a modular architecture, featuring multiple interconnected systems for gaming, recruitment, administration, and entertainment. Built with Python and discord.py, it provides a rich set of features centered around the Transformers universe.

### 🎯 Core Philosophy
- **Modular Design**: Each system operates independently while sharing data through unified managers
- **Scalability**: Built to handle multiple servers with different configurations
- **User Experience**: Rich interactive interfaces with Discord UI components
- **Data Persistence**: Comprehensive data storage and backup systems

---

## ✨ Major Features

### 🐾 EnergonPets System

A comprehensive virtual pet ecosystem featuring battle mechanics, RPG elements, economic systems, and competitive gameplay with Transformers-themed content.

#### 🤖 Core Pet System (`Systems/EnergonPets/`)
- **Pet Creation & Management**: Autobot and Decepticon faction pets with unique names and characteristics
- **Level Progression**: Multi-stage evolution system with experience thresholds and stat growth
- **Pet Stages**: Progressive evolution from basic forms to advanced mega-evolved states
- **Mission System**: Various mission types with different difficulty levels and rewards
- **Pet Statistics**: Comprehensive tracking of pet health, energy, happiness, and maintenance

#### ⚔️ Advanced Battle System (`Systems/EnergonPets/PetBattles/`)
- **Unified Battle Engine**: Sophisticated combat system supporting multiple battle modes
- **PvP Combat**: Real-time player vs player battles with strategic team composition
- **Group Battles**: Multi-participant battles with join/leave mechanics and team coordination
- **Tournament System**: Organized competitive events with bracket management and rewards
- **Damage Calculator**: Complex damage calculation with type advantages, critical hits, and modifiers
- **Enemy Selection**: Smart opponent matching based on pet levels and battle history
- **PvP Lobby**: Interactive waiting rooms with matchmaking and battle preparation

#### 🎰 Energon Economy & Gaming (`Systems/EnergonPets/`)
- **Energon Currency**: Primary economic system with earning, spending, and balance management
- **Slot Machine**: Multi-difficulty casino games with themed emoji sets and progressive jackpots
  - **Easy Mode**: 5-emoji themes with 80x multiplier potential
  - **Medium Mode**: 8-emoji themes with 512x multiplier potential  
  - **Hard Mode**: 12-emoji themes with 1728x multiplier potential
- **Interactive Slots**: Animated spinning mechanics with Discord UI integration
- **Economic Balance**: Carefully calibrated reward systems and betting limits
- **Challenge System**: Player-to-player wagering and competitive gaming

#### 🎮 RPG Adventure System (`Systems/EnergonPets/RPG/`)
- **AI-Powered Events**: Google Gemini AI integration for dynamic storytelling
- **Resource Management**: Energy, maintenance, and happiness resource systems
- **Event System**: Randomized RPG events with success/failure mechanics
- **Character Development**: Progressive character growth through adventures
- **Risk/Reward Mechanics**: Strategic decision-making with meaningful consequences
- **Narrative Integration**: Immersive storytelling with Transformers universe themes

#### 📊 Battle Statistics & Analytics
- **Comprehensive Stats**: Win/loss ratios, battle history, and performance metrics
- **Team Management**: Squad formation and tactical team composition
- **Battle Logs**: Detailed combat records and replay functionality
- **Leaderboards**: Competitive rankings and achievement tracking
- **Performance Analysis**: Statistical breakdowns of battle effectiveness

### 🤖 Random System (`Systems/Random/`)

Comprehensive entertainment and interactive content system featuring AI-powered games, immersive adventures, social features, and Transformers-themed activities.

#### 🎯 Shooting Range Training (`Systems/Random/fun_system.py`)
- **Interactive Shooting Range**: Multi-round training sessions (5, 15, 25, 50, 100 rounds) with real-time target practice
- **Cybertronian Access Control**: Restricted to users with Autobot, Decepticon, Maverick, or Cybertronian Citizen roles
- **Performance Tracking**: Comprehensive statistics including accuracy, hits, total shots, and leaderboard rankings
- **Dynamic UI**: Interactive Discord buttons for target selection with immediate feedback and scoring
- **User Statistics**: Persistent stat tracking with UserDataManager integration for progress monitoring

#### 🎮 Cybertron Games (`Systems/Random/hunger_games.py`)
- **AI-Powered Battle Royale**: Groq AI integration for dynamic Transformers-themed deathmatch narratives
- **Faction Assignment**: Automatic assignment to 40+ different Cybertronian factions (Autobots, Decepticons, Maximals, etc.)
- **Advanced Participant Management**: Support for bot inclusion, specific user selection, and Cybertronian-only filtering
- **Real-time Game Control**: Interactive Discord UI with start, next round, and end game controls
- **Intelligent Storytelling**: AI-generated narratives with fallback Cybertronian story templates
- **Flexible Game Setup**: Customizable warrior count (2-50), faction count (2-5), and participant filtering

#### 🗺️ Interactive Adventures (`Systems/Random/walktru.py`)
- **Six Themed Adventures**: Horror Sanitarium, Gangster's Rise, Knight's Quest, Robot Uprising, Western Frontier, Wizard's Apprentice
- **Dynamic Stat Systems**: Unique mechanics per adventure (Fear, Heat, Honor, Power, Health, Mana) with visual progress bars
- **Branching Narratives**: Complex choice-driven storylines with multiple endings and consequences
- **State Persistence**: User adventure progress saved across sessions with UserDataManager integration
- **Interactive UI**: Discord select menus and buttons for seamless story navigation
- **Stat Visualization**: Color-coded progress bars and warning thresholds for immersive gameplay

#### 💬 Advanced Talk System (`Systems/Random/talk_system.py`)
- **Server Lore Management**: Comprehensive lore creation, viewing, and statistics with paginated navigation
- **Transformers Knowledge Base**: Extensive lore lookup system with character information and universe details
- **AI Message Analysis**: Pattern recognition and prediction of user communication styles
- **Entertainment Suite**: Jokes, roasts, compliments, and blessings with curated content databases
- **Social Features**: User interaction tracking and personalized content delivery
- **Template System**: Sophisticated dialogue templates with dynamic content insertion

#### 🔮 Theme & Combiner System (`Systems/Random/themer.py`)
- **Pet Combiner Teams**: Interactive team formation with role assignment (Left/Right Arms/Legs, Torso)
- **Dynamic Name Generation**: AI-powered combiner name creation using extensive prefix/suffix databases
- **Allspark Analysis**: Personality assessment system with multi-question interactive surveys
- **Role Management**: Integration with server role systems for Cybertronian faction verification
- **Team Coordination**: Real-time team status tracking and member management
- **Advanced UI**: Multi-view Discord interfaces with pagination and role selection systems

#### 🎨 Data & Content Management
- **Rich Content Libraries**: Extensive JSON databases for jokes, blessings, roasts, and dialogue templates
- **User Data Integration**: Seamless integration with centralized UserDataManager for persistent storage
- **Template Systems**: Sophisticated content generation with dynamic variable insertion
- **Performance Optimization**: Lazy loading and caching systems for efficient data access

### 🏛️ PnW Recruitment System (`Systems/PnW/`)

Advanced automated recruitment system for Politics and War game integration with comprehensive rule compliance and task management.

#### 🌐 Core Functionality
- **Automated Nation Discovery**: Fetches up to 15,000 unallied nations from PnW API with activity filtering
- **Smart Message Delivery**: Automated recruitment message sending with randomized content selection
- **Advanced Cooldown Management**: Strict rule compliance (60-day same message, 60-hour any message cooldowns)
- **Real-time Task Tracking**: Background task management with progress monitoring and cancellation support
- **Interactive Nation Browser**: Paginated Discord UI for reviewing and selecting recruitment targets

#### 🛠️ Key Components
- **Recruitment Tracker** (`recruitment_tracker.py`): Comprehensive message history and cooldown enforcement system
- **Interactive Views** (`recruit_views.py`): Discord UI components with pagination and nation activity indicators
- **API Integration**: PnWKit integration with fallback to local packages and comprehensive error handling
- **Task Management**: Asynchronous recruitment campaigns with real-time status monitoring and performance metrics
- **Rule Compliance Engine**: Built-in safeguards to prevent policy violations and maintain game rule adherence

#### 📊 Advanced Features
- **Nation Activity Analysis**: Real-time activity indicators showing last login times with color-coded status
- **Performance Metrics**: Success rates, nations per minute, and comprehensive campaign statistics
- **Flexible Message System**: Multiple recruitment templates with leader name personalization and link integration
- **Comprehensive Logging**: Detailed tracking of all recruitment activities with backup and recovery systems
- **Multi-page Nation Display**: Efficient browsing of large nation datasets with detailed nation information

### 👑 Admin System (`Systems/admin_system.py`)

Comprehensive server administration and moderation tools.

#### 🛠️ Administrative Features
- **Server Management**: Multi-server configuration support
- **User Management**: Advanced user data handling and moderation
- **System Monitoring**: Bot health and performance tracking
- **Configuration Management**: Dynamic settings and role management

### 🗂️ User Data Manager (`Systems/user_data_manager.py`)

Centralized data management system providing unified storage and retrieval.

#### 🚀 Key Features
- **Unified Storage**: Single point of access for all user data
- **Data Persistence**: Reliable JSON-based storage with backup systems
- **Cross-System Integration**: Shared data access across all bot systems
- **Performance Optimization**: Efficient data caching and retrieval

---

## 🗂️ System Components & Architecture

### 📁 Core Structure

```
AllSpark/
├── allspark.py                 # Main bot entry point with enhanced logging
├── config_example.py           # Multi-server configuration system
├── bundle_pnwkit.py           # Dependency bundling for deployment
├── Systems/                    # Modular system architecture
│   ├── admin_system.py        # Administrative functions
│   ├── user_data_manager.py   # Centralized data management
│   ├── Data/                  # Persistent storage
│   ├── EnergonPets/           # Complete pet and battle system
│   ├── PnW/                   # Politics and War integration
│   ├── Random/                # Entertainment and interactive content
│   ├── Users/                 # User-specific data (empty - managed by data manager)
│   └── Global Saves/          # Global state storage (empty - managed by data manager)
└── local_packages/            # Bundled dependencies for deployment
```

### 🗄️ Data Storage (`Systems/Data/`)

The bot maintains comprehensive data persistence through specialized JSON files:

#### 🐾 Pet System Data
- **`pets_level.json`**: Pet progression system with 480 levels across multiple stages (Spark Initiate to advanced tiers), each with unique names and emojis
- **`pet_equipment.json`**: Equipment database with rarity-based chassis plating (Basic to Mythic), stat bonuses, and unlock requirements
- **`pets_mission.json`**: Mission templates categorized by difficulty levels with varied task descriptions for pet training
- **`pet_xp.json`**: Experience point thresholds defining XP requirements for each level (100 XP for level 1, scaling to 50,000+ for higher levels)

#### ⚔️ Battle System Data
- **`bosses.json`**: Boss entity database with rarity classifications (Common to Mythic), combat stats (HP, Attack, Defense), and reward systems
- **`monsters.json`**: Monster catalog featuring various enemy types with balanced combat statistics and energy/XP rewards
- **`titans.json`**: Titan collection including iconic Transformers characters with detailed descriptions, combat attributes, and rarity tiers

#### 🎯 Recruitment System Data
- **`recruit.json`**: Recruitment message templates featuring themed invitations from Transformers characters (Optimus Prime, Bumblebee, Megatron, etc.) with personalized content
- **`recruit_backup.json`**: Backup copy of recruitment templates for data recovery and system reliability
- **`recruitment_history.json`**: Historical tracking of recruitment campaigns with nation IDs, leader names, message numbers, and timestamps

#### 🎭 Entertainment & System Data
- **`roasts.json`**: Comprehensive collection of categorized roasts and humorous insults for entertainment commands
- **`bot_logs.json`**: System activity logs tracking user interactions, command usage, timestamps, and administrative actions

#### 🛡️ Backup & Recovery Systems
- **Compressed Backups**: `.gz` files providing automated data recovery capabilities for critical system data

### 🔧 Local Packages (`local_packages/`)

Self-contained dependency management for deployment compatibility:
- **Web Libraries**: aiohttp, requests, urllib3 for HTTP operations
- **Data Processing**: beautifulsoup4, charset_normalizer for web scraping
- **Game Integration**: pnwkit for Politics and War API integration
- **Utility Libraries**: typing_extensions, certifi, idna for enhanced functionality
- **Performance**: multidict, frozenlist, propcache for optimized operations

This bundled approach ensures consistent deployment across different hosting environments.

---

## 📜 Complete Commands List

### 🐾 EnergonPets & Economy

#### Pet Management
- `/get_pet` - Acquire your first Energon pet
- `/pet` - View pet status and information
- `/charge_pet` - Restore pet energy levels
- `/play` - Interactive play sessions with your pet
- `/repair_pet` - Fix damaged pet components

#### Pet Training & Equipment
- `/train` - Train your pet to improve stats
- `/mission` - Send pets on training missions
- `/pet_equipment` - Manage pet gear and upgrades

#### Battle System
- `/battle` - Engage in pet combat
- `/group_battle` - Team-based battle scenarios
- `/battle_stats` - View combat statistics
- `/tournament` - Participate in competitive events

#### Economy & Gaming
- `/scout` - Search for resources and opportunities
- `/search` - Explore for hidden items
- `/energon_stats` - View economy statistics
- `/rush_info` - Check rush event information
- `/slots` - Slot machine gaming (Easy/Medium/Hard difficulties, Fun/Bet modes)
- `/cybercoin_market` - Access the digital currency market
- `/cybercoin_profile` - View your CyberCoin portfolio
- **RPG Adventures** - AI-powered storytelling with resource management

---

### 🤖 Random & Entertainment

#### Interactive Gaming
- `/range` - Interactive target practice with multiple round options
- `/rangestats` - View shooting statistics and leaderboards
- `/walktru` - Choose-your-own-adventure with 6 themed storylines:
  - 🎃 Horror • 🕴️ Gangster • ⚔️ Knight • 🤖 Robot • 🤠 Western • 🧙 Wizard
- `/cybertron_games` - AI-powered Transformers battle royale with faction assignment

#### Lore & Knowledge Management
- `/add_lore` - Create and store server lore
- `/add_message_to_lore` - Archive important messages
- `/view_lore` - Browse lore entries
- `/random_lore` - Get a random lore entry
- `/lore_stats` - View lore collection statistics
- `/what_is` - Transformers universe information and character details

#### Social & Entertainment
- `/joke` - Categorized humor and jokes
- `/roast` - Playful insults and roasts
- `/compliment` - Positive affirmations
- `/blessing` - Receive Allspark blessings
- `/user_says` - AI-powered message pattern analysis and prediction

#### Theme & Analysis
- `/combiner` - Form pet combiner teams
- `/analysis` - Allspark personality assessment

#### Utility
- `/ping` - Check bot latency
- `/hello` - Friendly greeting
- `/grump` - Ping revenge system

---

### 🏛️ PnW Recruitment Commands

#### Campaign Management
- `/recruit` - Start recruitment campaigns with nation browser
- `/recruit_cancel` - Cancel active recruitment tasks

#### Monitoring & Analytics
- `/recruit_status` - View task progress and metrics
- `/recruitment_stats` - Historical recruitment statistics
- `/pnwkit_status` - API integration health check

---

### 👑 Admin Commands

#### Server Management
- `/admin config` - Configure server settings
- `/admin roles` - Manage user roles
- `/admin channels` - Channel configuration

#### User & Data Management
- `/admin user` - User administration tools
- `/admin data` - Data management utilities
- `/admin backup` - Backup system controls

#### System Operations
- `/admin status` - System status overview
- `/admin logs` - View system logs
- `/admin restart` - Restart bot services

---

## 🏗️ Project Structure

### 🎯 Design Principles

1. **Modular Architecture**: Each system (`EnergonPets`, `PnW`, `Random`) operates independently
2. **Centralized Data Management**: `UserDataManager` provides unified data access
3. **Scalable Configuration**: Multi-server support with per-server settings
4. **Robust Error Handling**: Comprehensive logging and error recovery
5. **Deployment Ready**: Self-contained dependencies and environment setup

### 🔄 Data Flow

```
User Command → System Module → UserDataManager → JSON Storage
                    ↓
            Discord UI Response ← Processed Data ← Data Retrieval
```

### 🛡️ Security & Compliance

- **Rate Limiting**: Built-in cooldown systems prevent abuse
- **Rule Compliance**: Automated enforcement of platform policies
- **Data Privacy**: Secure handling of user information
- **Backup Systems**: Multiple layers of data protection

---

## 🔧 Configuration & Setup

### 📋 Prerequisites
- Python 3.8+
- Discord.py library
- Valid Discord bot token
- Politics and War API key (for recruitment features)

### ⚙️ Configuration Files
- **`.env.example`**: Environment variable template
- **`config_example.py`**: Multi-server configuration template
- **`LICENSE.txt`**: Project licensing information

### 🚀 Deployment
The bot includes deployment optimization:
- **Bundled Dependencies**: `local_packages/` for hosting compatibility
- **Environment Setup**: Automatic path and directory configuration
- **SparkedHost Ready**: Optimized for popular Discord bot hosting platforms

---

## 🛠️ Development & Support

### 🔧 Development Environment
- **IDE Support**: Visual Studio integration (`.vs/` folder)
- **Git Integration**: Comprehensive `.gitignore` for clean repositories
- **Modular Testing**: Each system can be tested independently

### 📞 Support Channels
- **Discord Server**: [Join for support](https://discord.gg/pDTKNQJXdh)
- **Bug Reports**: Use GitHub issues or Discord support
- **Feature Requests**: Community-driven development

### 🤝 Contributing
1. Fork the repository
2. Create feature branches for new systems
3. Follow the modular architecture patterns
4. Test thoroughly with multiple server configurations
5. Submit pull requests with detailed descriptions

### 📊 Performance Monitoring
- **Colored Logging**: Enhanced console output with color-coded log levels
- **Error Tracking**: Comprehensive error logging and traceback
- **System Health**: Built-in monitoring and diagnostic tools

---

## 📄 License

This project is licensed under the terms specified in `LICENSE.txt`.

## 🔗 Support

For technical support, feature requests, or community discussion:
**[Join the Support Discord Server!](https://discord.gg/pDTKNQJXdh)**

---

*The AllSpark - Transforming Discord servers one command at a time.* ⚡
