
# 🌟 AllSpark Discord Bot

> **The ultimate Transformers-themed Discord bot featuring advanced pet systems, RPG mechanics, interactive storytelling, and comprehensive entertainment features.**

[![Discord.py](https://img.shields.io/badge/Discord.py-2.3+-blue.svg)](https://discordpy.readthedocs.io/)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📋 Table of Contents

- [🚀 Overview](#-overview)
- [✨ Features](#-features)
- [🎯 System Components](#-system-components)
- [🎮 Getting Started](#-getting-started)
- [📊 Commands Reference](#-commands-reference)
- [🏗️ System Architecture](#-system-architecture)
- [🔧 Configuration](#-configuration)
- [📁 File Structure](#-file-structure)
- [🛠️ Development](#-development)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

## 🚀 Overview

**AllSpark** is a feature-rich Discord bot that brings the Transformers universe to life through interactive systems, pet management, storytelling, and community engagement. Built with Discord.py and designed for scalability, it offers multiple interconnected systems that create a comprehensive user experience.

### Key Highlights
- **🐾 EnergonPets**: Advanced pet management with 100-level progression
- **🤖 Random System**: Interactive storytelling, AI conversations, and theme customization
- **⚔️ RPG System**: Character creation and progression mechanics
- **🏛️ PnW Integration**: Politics & War alliance recruitment automation
- **🎭 Theme System**: Transformer identity creation and combiner teams

## ✨ Features

### 🐾 **EnergonPets System**
- **100-Level Progression**: Massive XP scaling from 50 to 6.32 billion XP
- **100 Unique Stages**: From "Nano Core" to "Nano Supreme"
- **Faction-Based**: Autobot vs Decepticon with unique bonuses
- **150+ Missions**: 50 easy, 50 average, 50 hard robotic missions
- **Multi-Battle Types**: Solo, group, PvP, open challenges, 4v1 boss battles, 4-way FFA
- **Comprehensive Stats**: Energy, maintenance, happiness, attack, defense with faction-specific maximums
- **Interactive UI**: Button-based navigation with real-time updates, faction-colored embeds, detailed breakdown views
- **Role-Based Access**: Cybertronian citizenship requirement (Autobot, Decepticon, Maverick, or Cybertronian_Citizen roles)
- **Data Persistence**: Automatic saving and migration system with JSON-based configuration
- **Progression Tracking**: Automatic stat increases, level-up celebrations, achievement milestones
- **Resource Management**: Energy consumption/recharge, maintenance repair, happiness mechanics
- **Cooldown System**: Duration-based activities (15min/30min/1hour options)
- **Loot System**: Energon rewards, transformation items, class-based equipment

### 🤖 **Random System**
- **Interactive Stories**: 6 genres with unique mechanics (Horror, Gangster, Knight, Robot, Western, Wizard)
- **Conversational AI**: Advanced dialogue generation and user analysis
- **Lore Management**: Server history and user-generated content
- **Joke System**: Transformers-themed humor with API integration
- **Personal Profiles**: Comprehensive user statistics and achievements
- **Theme Customization**: Transformer identity creation and combiner teams

### ⚔️ **RPG System**
- **Character Classes**: 8 specialized classes per faction
- **Stat System**: ATT, DEF, DEX, INT, CHA, HP attributes
- **Battle Mechanics**: Turn-based combat with progression
- **Cross-System Integration**: Links with EnergonPets and Theme System

### 🏛️ **PnW Recruitment**
- **Real-Time Discovery**: Automated nation targeting via P&W API
- **Intelligent Filtering**: Activity-based sorting and comprehensive filtering
- **Personalized Messaging**: Dynamic recruitment messages
- **Rate Limit Protection**: Built-in safeguards against API abuse

## 🎯 System Components

### 🐾 **EnergonPets System** (`Systems/EnergonPets/`)

The EnergonPets system is a comprehensive robotic pet management platform featuring deep progression mechanics and extensive customization options.

#### 🚀 **Energon Game System** (`energon_commands.py` & `energon_system.py`)

A sophisticated 1286-line Energon mining and economy game featuring cross-channel multiplayer gameplay with real-time updates, comprehensive statistics tracking, and advanced market mechanics.

**🎯 Core Game Features:**
- **Transformers: Energon Rush**: Global cross-channel mining competition
- **Win Condition**: First to reach 10,000 Energon wins the game
- **Real-time Processing**: Live game state updates across all channels
- **Persistent Banking**: Energon banking system for long-term progression
- **Multi-Channel Support**: Games span across Discord channels and servers
- **Role-Based Access**: Cybertronian citizenship requirement
- **Comprehensive Statistics**: Track wins, losses, total Energon gained/lost

**🎮 Advanced Mechanics:**
- **Pet Integration**: Pets provide 2% bonus per level during searches
- **Probability System**: 5-tier outcome system (disaster, loss, nothing, small find, major find)
- **Pet Damage**: Pets can be damaged during failed searches
- **XP Rewards**: Pets gain experience from successful mining operations
- **Game State Management**: Automatic game creation and cleanup
- **Win Detection**: Real-time win condition checking and celebration

**📊 Statistics Tracking:**
- **Personal Stats**: Total Energon gained, lost, games won/lost
- **Global Leaderboards**: Cross-server ranking system with daily/weekly/all-time rankings
- **Pet Contributions**: Track pet bonuses and search assistance
- **Bank Balances**: Persistent Energon storage between games
- **Win/Loss Records**: Comprehensive battle history

**🔧 Technical Features:**
- **Async Processing**: Non-blocking game operations with proper async/await patterns
- **Error Handling**: Robust exception management with fallback systems
- **Data Persistence**: JSON-based game state storage with user_data_manager integration
- **Cross-Server Support**: Games work across Discord servers
- **Real-time Updates**: Instant status notifications
- **State Management**: Lazy loading and automatic state saving

#### ⚡ **Energon Game Engine** (`energon_system.py`)

**🏗️ System Architecture:**
- **EnergonGameManager**: Central 1286-line game management class handling all Energon operations
- **State Persistence**: Advanced JSON-based state management with user_data_manager integration
- **Global Leaderboards**: Cross-server ranking system with multiple time periods
- **Banking System**: Persistent Energon storage with dual-account management
- **Challenge System**: Real-time PvP challenges with timeout handling
- **Cooldown Management**: Intelligent cooldown tracking per channel

**💰 Market System Features:**
- **Slot Machine Integration**: 3 difficulty levels (easy/medium/hard) with emoji-based themes
- **Holiday Events**: 15+ Transformers-themed holidays with market multipliers
- **Catastrophic Events**: Weighted random events (surges/crashes/chaos)
- **Event Probability System**: 25% base event chance with holiday-specific probabilities
- **Multiplier Ranges**: Dynamic price adjustments from 0.1x to 6.0x
- **Transformers Holidays**: Cybertron Day, Energon Discovery Day, Decepticon Uprising

**🎰 Slot Machine Configuration:**
- **Theme Variety**: 5 emoji themes for easy, 8 for medium, 12 for hard difficulty
- **Difficulty Multipliers**: 80x (easy), 512x (medium), 1728x (hard) reward scaling
- **Emoji Collections**: Weapon themes, superhero themes, animal themes
- **Progressive Rewards**: Scaled based on difficulty and theme complexity

**📈 Market Events & Holidays:**
- **Surge Holidays**: Christmas (1.5-3.0x), New Year (1.3-2.5x), Independence Day (1.2-2.0x)
- **Crash Events**: Halloween (0.3-0.8x), April Fools chaos (0.2-4.0x), Remembrance Day (0.5-0.9x)
- **Transformers Events**: Cybertron Day (2.0-5.0x), Energon Discovery Day (1.8-3.5x)
- **Catastrophic Events**: UNICRON awakening, Cybertron core meltdown, energon plague
- **Massive Surges**: Allspark returns, energon moon discovery, ancient vaults

**🔐 Banking & Economy:**
- **Dual Account System**: Current game energon + persistent bank storage
- **Challenge Integration**: Use banked energon for PvP challenges when not in active game
- **Win Banking**: Automatic transfer of winnings to persistent bank
- **Global Leaderboard**: Cross-server rankings with username tracking
- **Transaction Safety**: Atomic operations with rollback on failure

**🎮 Game State Management:**
- **Channel-Based Games**: Separate game instances per Discord channel
- **Player Initialization**: Automatic setup with 0 energon starting balance
- **Cross-Server Support**: Games function across multiple Discord servers
- **State Loading**: Lazy loading with fallback to empty state
- **Data Validation**: Comprehensive error handling and data integrity checks

**⚙️ Technical Implementation:**
- **Async State Management**: Non-blocking save/load operations
- **Error Recovery**: Graceful handling of missing files or corrupted data
- **Memory Efficiency**: Lazy loading prevents memory bloat
- **Cross-System Integration**: Seamless integration with user_data_manager
- **Logging System**: Comprehensive debug logging for all operations

#### Core Features

**🎯 Core Features**

**🎯 Pet Creation & Management**
- **Faction Selection**: Choose between Autobot and Decepticon factions with distinct visual themes
- **100-Level Progression**: Exponential XP requirements (50 → 6.32B XP) with automatic level-up notifications
- **100 Unique Stages**: Complete evolution from Nano Core to Nano Supreme with emoji progression indicators
- **Visual Indicators**: Stage emojis (🔩⚙️🔧🤖⚡💎🔱🌌✨👑) show progression and faction-specific colors
- **Comprehensive Stats**: Energy, maintenance, happiness, attack, defense attributes with real-time updates
- **Interactive Status**: Real-time stats with breakdown buttons, refresh functionality, and detailed pet profiles
- **Role-Based Access**: Cybertronian citizenship requirement (Autobot, Decepticon, Maverick, or Cybertronian_Citizen roles)
- **Name Customization**: Rename pets with 20-character limit and validation
- **Data Migration**: Automatic old data migration and persistent storage
- **Legacy Data Support**: Automatic migration from old pet data format with equipment and inventory integration

**⚔️ Advanced Battle System**
- **Comprehensive Combat Engine**: Turn-based battle system with d20 roll mechanics (1624 lines of battle logic)
- **Multi-Battle Architecture**: Unified system handling solo, group, PvP, and energon challenges
- **Interactive UI Components**: Advanced Discord UI views for battle management
- **Real-time Battle Processing**: Live battle updates with action buttons
- **Group Battle Management**: Dynamic participant joining/leaving with 4-player maximum
- **Energon Betting System**: Wagering mechanics with prize pool calculations
- **Battle Statistics**: Comprehensive tracking of wins, losses, and performance metrics
- **Defense Mechanics**: Group defense system with coordinated protection strategies
- **Turn-based Processing**: Sophisticated action queue and round resolution
- **Battle Logging**: Detailed combat logs and outcome tracking
- **Monster Database**: 6 rarity tiers (common to mythic) across 3 enemy types (monsters, bosses, titans)
- **Dynamic Enemy Generation**: Real-time monster loading with fallback systems
- **Advanced Battle Views**: 5 specialized UI classes for different battle scenarios
- **Group Defense Coordination**: Multi-player defense mechanics with shared protection
- **PvP Turn Management**: Simultaneous action collection and resolution system
- **Equipment Integration**: Equipment stats directly affect battle performance (attack, defense, energy bonuses)
- **Loot System**: Victory rewards include equipment drops with rarity-based generation
- **Equipment-Based Scaling**: Battle stats dynamically calculated including equipment bonuses

**⚔️ Battle System**
- **Multi-Battle Types**: Solo battles, group battles (up to 4 players), PvP challenges, group PvP, energon challenges
- **Interactive Enemy Selection**: Button-based UI for choosing opponents by type and rarity
- **Energon Betting**: Challenge-based battles with energon wagering system
- **Battle Statistics**: Comprehensive tracking of wins, losses, and win rates
- **Real-time Updates**: Live battle status and outcome displays
- **Challenge System**: Direct player-to-player PvP battles with confirmation
- **Group Management**: Dynamic participant joining with interactive controls
- **Turn-Based Mechanics**: Sophisticated d20 roll system with damage multipliers
- **Monster Encyclopedia**: 3 enemy types (🤖 Monsters, 👹 Bosses, 👑 Titans) with 6 rarity tiers
- **Battle Views Architecture**: 5 specialized UI classes for different battle scenarios
- **Group Defense System**: Coordinated protection mechanics for team battles
- **Action Queue Management**: Simultaneous turn processing for PvP battles
- **Reward Distribution**: Automated loot and energon prize allocation

**⚔️ Battle Systems**
- **Solo Battles**: Individual pet vs monster encounters with 5 difficulty levels
- **Group Battles**: Multi-pet cooperative combat (4v1 boss battles)
- **PvP Challenges**: Direct pet vs pet battles with other users
- **Open Challenges**: Create battles others can join (4-way FFA)
- **Monster Battles**: 5 difficulty levels (common to legendary) with unique rewards
- **Loot Rewards**: Earn energon, items, and XP from victories with detailed battle summaries
- **Battle Statistics**: Track wins, losses, and performance metrics
- **Interactive Battle UI**: Real-time battle status and outcome displays

**🎮 Pet Activities & Training**
- **150+ Missions**: 50 easy, 50 average, 50 hard robotic missions with unique descriptions
- **Energy System**: Pets consume energy during activities with automatic recharge options
- **Maintenance System**: Wear and tear affects performance with repair mechanics
- **Happiness Mechanics**: Mood affects battle performance and training efficiency
- **Training Programs**: Three difficulty levels (average, intense, godmode) with progressive stat improvements
- **Duration-Based Activities**: 15min, 30min, and 1-hour options for charging, playing, and repairing
- **Real-Time Progress**: Activity completion notifications and level-up celebrations
- **Achievement Tracking**: Missions completed, battles won/lost, and progression milestones

**⚙️ Equipment & Inventory System**
- **3 Equipment Slots**: Chassis Plating (defense), Energy Cores (energy), Utility Modules (happiness/maintenance)
- **Rarity Tiers**: Common, Uncommon, Rare, Epic, Legendary, Mythic equipment
- **Stat Bonuses**: Direct stat improvements for attack, defense, energy, maintenance, and happiness
- **Inventory Management**: Comprehensive item storage with pagination display
- **Equipment Commands**: `/pet_equip` for equipping items, `/pet_equipment` for inventory viewing
- **Loot Integration**: Equipment drops from battle victories with rarity-based generation
- **Legacy Migration**: Automatic conversion of old inventory data to new equipment system
- **Visual Equipment Display**: Real-time equipment stats in pet status views

**🗑️ Pet Management**
- **Permanent Deletion**: Safe deletion with confirmation dialog and irreversible consequences
- **Deletion Preview**: Shows current stats, achievements, and warning messages before deletion
- **Recovery System**: Immediate new pet creation after deletion
- **Confirmation UI**: Interactive confirmation buttons with 30-second timeout
- **Deletion Logging**: Track deletion history and user statistics


### 🤖 **Random System** (`Systems/Random/`)

**900-line comprehensive entertainment suite** featuring interactive games, competitive systems, and immersive storytelling experiences with advanced user tracking and persistent statistics.

#### 🎯 **Shooting Range System** (`fun_system.py`)

**🔫 Interactive Target Practice**
- **Multi-Round Sessions**: Configurable 5, 15, 25, 50, or 100 round sessions
- **Reaction-Based Gameplay**: 1-second timed button clicks with 🎯 target identification
- **Real-Time Scoring**: Live accuracy tracking and hit/miss calculation
- **Visual Feedback**: Color-coded results with immediate embed updates
- **Cybertronian Access**: Role-gated training system for faction members

**📊 Advanced Statistics Engine**
- **Persistent User Tracking**: Individual performance metrics stored via UserDataManager
- **Multi-Tier Rankings**: 8-tier achievement system (Recruit → Matrix Bearer)
- **Personal Best Records**: Round-specific accuracy tracking and improvement metrics
- **Session Analytics**: Total hits, overall accuracy, and session counts
- **Progress Visualization**: ASCII progress bars and emoji-based rankings

**🏆 Competitive Features**
- **Achievement System**: Dynamic rank assignment based on performance thresholds
- **Leaderboard Integration**: Round-specific best records and global rankings
- **Performance History**: Complete session tracking with detailed statistics
- **Motivational Messaging**: Context-aware feedback based on performance levels

#### 🏹 **Hunger Games District Sorter** (`fun_system.py`)

**🎲 Intelligent Member Selection**
- **Multi-Filter System**: Bot exclusion, role-based filtering, and citizen-only modes
- **Dynamic Sampling**: Random selection from up to 24 qualifying members
- **District Organization**: Automatic pairing into numbered districts (2 members each)
- **Flexible Configuration**: Include/exclude bots and Cybertron citizens
- **Real-Time Validation**: Ensures minimum member requirements (2+ members)

**📋 Automated Setup Commands**
- **Command Generation**: Automatic `/hungergames add` command creation for each tribute
- **Visual Organization**: Discord embed with district assignments and member lists
- **Filter Transparency**: Clear indication of applied filters and selection criteria
- **Audit Logging**: Comprehensive operation logging with user attribution

#### 🤖 **Mega-Fight System** (`fun_system.py`)

**⚔️ Combiner Team Battles**
- **Team-Based Combat**: 6-member combiner teams (2 legs, 2 arms, 1 head, 1 body)
- **Head-Controlled Fights**: Only team heads can initiate and control battles
- **Pure RNG Combat**: 1-100 dice rolls with no external modifiers
- **Multi-Round Format**: Best-of-3 rounds with 2-win victory condition
- **Interactive UI**: Real-time battle interface with roll buttons

**💰 Reward & Penalty System**
- **Winner Rewards**: 100-300 energon + 25-50 pet XP for all team members
- **Loser Penalties**: -50 energon + 15-30 pet health loss for all team members
- **Cross-System Integration**: Automatic energon and pet system updates
- **Stat Tracking**: Individual mega-fight win/loss records
- **Level-Up Automation**: Automatic pet level progression notifications

#### 🎭 **WalkThru Interactive Stories** (`walktru.py`)

**📖 Multi-Genre Adventure System**
- **6 Story Genres**: Horror, Gangster, Knight, Robot, Western, Wizard
- **Unique Mechanics**: Fear, heat, honor, power, health, mana systems per genre
- **Branching Narratives**: Choice-driven progression with multiple endings
- **Stat-Based Outcomes**: Probability calculations based on accumulated stats
- **Visual Progress**: Progress bars and stat displays during gameplay

**🎮 Interactive Features**
- **Dropdown Selection**: Genre-based story selection interface
- **Real-Time Updates**: Dynamic story progression with immediate feedback
- **Persistent Progress**: Story state management across sessions
- **Success/Failure System**: Stat-dependent outcome calculations
- **Atmospheric Design**: Genre-appropriate embed colors and descriptions

#### 💬 **Talk System** (`talk_system.py`)

**🤖 Conversational AI**
- **NLP-Powered Analysis**: Advanced keyword extraction from user messages
- **Dynamic Responses**: Personalized Transformers-themed dialogue generation
- **Template System**: JSON-based customizable response templates
- **Multi-User Support**: Individual conversation tracking per user
- **Context Awareness**: Maintains conversation history and continuity

**📚 Comprehensive Knowledge Base**
- **Transformers Lore**: Extensive character, faction, and technology database
- **Blessing System**: Random Allspark blessings with categorized themes
- **Server History**: Persistent lore storage with user contributions
- **Search Functionality**: Topic-based information retrieval
- **Joke Integration**: Multi-source humor with Transformers focus

#### 👤 **Personal Profile System** (`me.py`)

**🎮 Comprehensive User Dashboard**
- **Transformer Identity**: Faction, class, and RPG stats integration
- **Game Statistics**: Win rates, performance metrics, and progression tracking
- **Pet Integration**: Detailed pet information with level and health displays
- **Combiner Teams**: Team formation status and member composition
- **CyberCoin Portfolio**: Holdings, investments, and profit analysis

**📊 Interactive Interface**
- **Tabbed Navigation**: Multiple profile sections with smooth transitions
- **Real-Time Updates**: Dynamic content refresh without page reload
- **Faction-Based Design**: Color schemes and emoji indicators per faction
- **Cross-System Data**: Integration with all bot systems for complete profiles

#### 🎨 **Theme System** (`themer.py`)

**🤖 Transformer Creation**
- **Faction Selection**: Autobot/Decepticon affiliation with role assignment
- **Class System**: 8 specialized classes per faction with unique attributes
- **AI Name Generation**: Context-aware name creation based on faction/class
- **RPG Integration**: Automatic character creation with ATT, DEF, DEX, INT, CHA, HP stats
- **Visual Identity**: Discord role and color scheme assignment

**🤝 Combiner Team Management**
- **6-Member Structure**: Complete team formation (legs, arms, head, body)
- **Role Assignment**: Emoji-based position selection with real-time updates
- **Dynamic Management**: Add/remove members with automatic team naming
- **Unique Identities**: Team names generated from member composition
- **Cross-System Sync**: Automatic integration with RPG and combat systems

### 🏛️ **PnW Recruitment System** (`Systems/PnW/`)

**887-line automated recruitment system** for the Cybertr0n alliance in Politics & War, featuring real-time nation discovery, intelligent filtering, and comprehensive API integration.

#### 🎯 **Core System Architecture**

**🔄 Real-Time Nation Discovery**
- **15,000 Nation Processing**: Sequential pagination handling 30 pages × 500 nations each
- **Activity-Based Prioritization**: Nations sorted by most recent activity (newest first)
- **API Rate Limit Protection**: 1-second delays between API calls to prevent abuse
- **Comprehensive Error Handling**: Fallback mechanisms for API failures and timeouts

**🔍 Advanced Filtering Engine**
- **Alliance Status**: Only nations with `alliance_id: 0` (unallied)
- **Activity Threshold**: Excludes nations inactive for 7+ days
- **Admin Exclusion**: Automatically skips nation ID=1 (game admin)
- **Vacation Mode**: Filters out nations in vacation mode
- **Data Validation**: Robust parsing with fallback values for missing data

**📊 Intelligent Data Processing**
- **Score Analysis**: Tracks nation power levels and city counts
- **Activity Indicators**: Color-coded activity status (🟢 Just now → 🔴 7+ days)
- **Statistical Summary**: Total nations, average scores, activity distribution
- **Progress Tracking**: Real-time processing status updates

#### 📬 **Messaging System**

**🎯 Dynamic Recruitment Messages**
- **Template System**: JSON-based message templates with dynamic placeholders
- **Personalization**: Customized messages using leader names and nation details
- **Multi-Template Support**: Random selection from multiple recruitment messages
- **Link Integration**: Automatic Discord and Alliance page inclusion
- **HTML Formatting**: Properly formatted links for P&W message system

**📤 Multi-Tier Messaging**
- **Individual Targeting**: Send messages to specific nations
- **Page-Based Recruitment**: Recruit all nations on current page (5 nations)
- **Mass Recruitment**: Send to all discovered nations with progress tracking
- **Rate Limiting**: Built-in 1-second delays between messages to prevent API abuse

#### 🎮 **Interactive UI System**

**📱 RecruitPaginatorView**
- **Real-Time Navigation**: Previous/Next buttons for nation browsing
- **Dynamic Updates**: Live refresh of nation data from P&W API
- **Progress Indicators**: Current page position and total nation count
- **Activity Visualization**: Color-coded activity status for each nation
- **Direct Actions**: Send page, mass recruit, and refresh functionality

**🔘 Action Buttons**
- **Previous/Next**: Navigate through paginated nation lists
- **🔄 Refresh**: Reload latest nation data from P&W API
- **📋 Send Page**: Recruit all 5 nations on current page
- **🎯 Mass Recruit**: Send messages to all discovered nations
- **❌ Close**: Clean shutdown of interactive interface

#### ⚙️ **Technical Implementation**

**🔗 API Integration**
- **pnwkit-py Library**: Modern GraphQL API wrapper for Politics & War
- **REST API Support**: Direct message sending via P&W REST API
- **Error Recovery**: Graceful handling of API timeouts and connection failures
- **Rate Limit Protection**: Comprehensive safeguards against API abuse
- **Data Validation**: Extensive error checking and data sanitization

**📊 Data Management**
- **JSON Configuration**: External message templates in `Data/recruit.json`
- **Fallback Systems**: Default recruitment message if JSON fails to load
- **Memory Efficiency**: Lazy loading and cleanup of nation data
- **Cross-Platform**: Works across Discord servers and channels

**🛡️ Security & Access Control**
- **Role-Based Access**: Restricted to Aries user ID (configurable)
- **Permission Validation**: Ephemeral responses for unauthorized users
- **Audit Logging**: Comprehensive logging of all recruitment activities
- **Timeout Handling**: 30-second API timeouts with proper error messages

#### 📈 **Performance Features**

**⚡ Processing Optimization**
- **Sequential Loading**: Prevents API overload with controlled request pacing
- **Memory Management**: Efficient handling of large nation datasets
- **Progress Tracking**: Real-time status updates during mass operations
- **Error Isolation**: Individual nation failures don't stop entire process

**📊 Analytics & Reporting**
- **Success Tracking**: Detailed counts of sent vs failed messages
- **Activity Analysis**: Comprehensive nation activity patterns
- **Performance Metrics**: Processing times and success rates
- **Error Logging**: Detailed failure analysis for debugging

## 🎮 Getting Started

### Prerequisites

- **Python 3.8+**
- **Discord Bot Token**
- **Politics & War API Key** (for recruitment features)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/AllSpark.git
   cd AllSpark
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your tokens and keys
   ```

4. **Run the bot**
   ```bash
   python allspark.py
   ```

### Quick Setup

1. **Create Discord Application**: Visit [Discord Developer Portal](https://discord.com/developers/applications)
2. **Enable Privileged Intents**: Server Members Intent and Message Content Intent
3. **Invite Bot**: Generate OAuth2 URL with appropriate permissions
4. **Configure Systems**: Set up individual system configurations as needed

## 📊 Commands Reference

### 🐾 EnergonPets Commands

#### Pet Management Commands
| Command | Description | Parameters | Example |
|---------|-------------|------------|---------|
| `/get_pet` | Create a new pet (Autobot/Decepticon) with faction-specific starting stats | `[autobot/decepticon]` | `/get_pet autobot` |
| `/pet` | View interactive pet dashboard with main stats and detailed breakdown | None | `/pet` |
| `/rename_pet` | Change pet name with instant update | `[new_name]` | `/rename_pet Optimus` |
| `/kill` | Permanently delete pet with confirmation UI and deletion logging | None | `/kill` |
| `/charge_pet` | Restore pet energy with scaled XP rewards | `[15min/30min/1hour]` | `/charge_pet 30min` |
| `/repair_pet` | Restore pet maintenance with scaled XP rewards | `[15min/30min/1hour]` | `/repair_pet 1hour` |
| `/play` | Increase pet happiness with scaled XP rewards | `[15min/30min/1hour]` | `/play 15min` |
| `/train` | Train pet stats with energy/happiness costs and stat improvements | `[average/intense/godmode]` | `/train intense` |
| `/mission` | Send pet on missions for XP and energon rewards | `[easy/average/hard]` | `/mission hard` |

#### Equipment & Inventory Commands
| Command | Description | Parameters | Example |
|---------|-------------|------------|---------|
| `/pet_equipment` | View all your pet items with pagination | None | `/pet_equipment` |
| `/pet_equip` | Equip items or view equipment slots | `[slot] [item_name]` | `/pet_equip chassis_plating armor` |

#### 🚀 Energon Game Commands
| Command | Description | Parameters | Example |
|---------|-------------|------------|---------|
| `/rush_info` | Display comprehensive Energon Rush game rules and features | None | `/rush_info` |
| `/scout` | Perform low-risk Energon search (50-200 Energon guaranteed) | None | `/scout` |
| `/search` | Embark on high-risk, high-reward Energon mining with 5 possible outcomes | None | `/search` |
| `/slots` | Play slot machine mini-game with configurable payouts | `[bet]` | `/slots 100` |
| `/cybercoin_market` | View current energon market events and prices | None | `/market` |
| `/challenge` | Challenge another player to direct PvP Energon battle | `<amount>` | `/challenge 500` |
| `/energon_stats` | View comprehensive Energon statistics and leaderboards | `[@member]` | `/energon_stats @OptimusPrime` |

#### ⚔️ Battle Commands
| Command | Description | Parameters | Example |
|---------|-------------|------------|---------|
| `/battle` | Start solo battle with interactive enemy selection | None | `/battle` |
| `/group_battle` | Start group battle (up to 4 players) | None | `/group_battle` |
| `/pvp` | Challenge specific player to PvP battle | `@player` | `/pvp @OptimusPrime` |
| `/group_pvp` | Start group PvP battle (up to 4 players) | None | `/group_pvp` |
| `/energon_challenge` | Start energon betting battle | `[amount]` | `/energon_challenge 1000` |
| `/battle_info` | Show comprehensive battle rules and information | None | `/battle_info` |
| `/battle_stats` | View battle statistics for any user | `[@member]` | `/battle_stats @Megatron` |

#### Access Requirements
- **Role**: Must have one of: Autobot, Decepticon, Maverick, or Cybertronian_Citizen roles
- **Permissions**: Basic Discord permissions (Send Messages, Embed Links)
- **Guild**: Must be in a server with appropriate role structure
- **One Pet Per User**: Each user can only have one active pet at a time
- **Faction Lock**: Once chosen, faction cannot be changed without deleting pet

#### Command Features
- **Interactive UI**: Button-based navigation with faction-colored embeds
- **Real-time Updates**: Live stat changes with refresh buttons
- **Progress Notifications**: Automatic level-up messages and achievement alerts
- **Confirmation Dialogs**: Safety prompts for destructive actions (/kill command)
- **Cooldown System**: Duration-based activity restrictions with remaining time display
- **Validation**: Input validation for names (20 char limit) and parameters
- **Error Handling**: Comprehensive error messages for invalid inputs or conditions
- **Progress Tracking**: Detailed XP breakdowns by activity type
- **Achievement Display**: Comprehensive battle statistics and resource tracking
- **Level-up Celebrations**: Automatic notifications with stat improvements
- **Data Migration**: Automatic handling of legacy pet data format updates

### 🤖 Random System Commands

| Command | Description | Parameters | Example |
|---------|-------------|------------|---------|
| `/hello` | AI conversation with escalating responses | None | `/hello` |
| `/ping` | Test responsiveness with escalating threats | None | `/ping` |
| `/whatis` | Query Transformers lore database | `<topic>` | `/whatis Optimus Prime` |
| `/blessing` | Get blessing from the Allspark | `[category]` | `/blessing wisdom` |
| `/joke` | Get random jokes with categories | `[category]` | `/joke coding` |
| `/roast` | Get roasted by the bot | `[target]` | `/roast @user` |
| `/compliment` | Get a nice compliment | `[target]` | `/compliment @user` |
| `/user_says` | Analyze user message patterns | `[members...]` | `/user_says @user1 @user2` |
| `/grump` | Sweet ping revenge on Grump | None | `/grump` |
| `/lore add` | Add lore | `<title>` | `/lore add Server History` |
| `/lore list` | Browse lore | None | `/lore list` |
| `/walktru` | Start story | None | `/walktru` |
| `/me` | View profile | None | `/me` |
| `/spark` | Create transformer | `[autobot/decepticon]` | `/spark autobot` |
| `/combiner` | Form team | None | `/combiner` |
| `/analysis` | Personality test | None | `/analysis` |
| `/range` | Shooting range training | None | `/range` |
| `/rangestats` | View shooting stats | None | `/rangestats` |
| `/hg_sorter` | Sort members into Hunger Games districts | `[filter]` | `/hg_sorter` |
| `/mega_fight` | Start mega-fight challenge | `[team1] [team2]` | `/mega_fight @user1 @user2 @user3 @user4` |

### 🏛️ PnW Commands

| Command | Description | Parameters | Access | Example |
|---------|-------------|------------|--------|---------|
| `/recruit` | Display unallied nations with interactive recruitment UI | None | Aries only | `/recruit` |

**🎯 Interactive Features:**
- **Real-Time Nation Discovery**: Automatically finds unallied nations via P&W API
- **Activity-Based Sorting**: Nations sorted by most recent activity (newest first)
- **Comprehensive Filtering**: Excludes inactive, vacation mode, and admin nations
- **Interactive Navigation**: Previous/Next buttons for browsing nation lists
- **Multi-Tier Messaging**: Individual, page-based, and mass recruitment options
- **Progress Tracking**: Real-time status updates during mass operations

**📊 Data Display:**
- **Nation Details**: Leader name, nation name, cities, score, last activity
- **Activity Indicators**: Color-coded status (🟢 Just now → 🔴 7+ days)
- **Statistics**: Total nations, average scores, activity distribution
- **Processing Status**: Live updates during recruitment operations

**🔘 Action Buttons:**
- **Previous/Next**: Navigate through paginated nation lists (5 nations per page)
- **🔄 Refresh**: Reload latest nation data from P&W API
- **📋 Send Page**: Recruit all 5 nations on current page
- **🎯 Mass Recruit**: Send messages to all discovered nations
- **❌ Close**: Clean shutdown of recruitment interface

## 🏗️ System Architecture

### ⚔️ Battle System Architecture

The battle system is built on a sophisticated 1624-line framework featuring:

**Core Battle Classes:**
- **UnifiedBattleView**: Main battle orchestrator handling all battle types
- **GroupBattleJoinView**: Dynamic participant management for group battles
- **EnergonChallengeJoinView**: Specialized betting battle coordination
- **BattleInfoView**: Comprehensive battle rules and mechanics display
- **UnifiedBattleActionView**: Real-time battle action interface

**Battle Mechanics Engine:**
- **d20 Roll System**: Sophisticated damage calculation with 6-tier multiplier system
- **Monster Database**: 3 enemy types (🤖 Monsters, 👹 Bosses, 👑 Titans) × 6 rarity tiers
- **Turn Management**: Simultaneous action collection for PvP, sequential for PvE
- **Group Coordination**: 4-player maximum with defense sharing mechanics
- **Reward Distribution**: Automated loot allocation based on battle performance

**Real-time Processing:**
- **Live Updates**: Discord embed updates every action
- **Timeout Management**: 5-minute battle timeouts with graceful cleanup
- **Error Recovery**: Fallback monster generation and error handling
- **State Persistence**: Battle state maintained across Discord interactions

### Core Components

```
AllSpark/
├── allspark.py              # Main bot entry point
├── Systems/
│   ├── EnergonPets/         # Pet management system
│   ├── Random/              # Entertainment suite
│   ├── PnW/                 # Politics & War integration
│   ├── RPG/                 # Role-playing system
│   └── Global Saves/        # User data storage
└── requirements.txt         # Python dependencies
```

### Data Management

**Storage Structure**
- **JSON Configuration**: System settings and templates
- **Individual User Files**: Personalized data per user
- **Global Statistics**: System-wide tracking
- **Cache Systems**: Efficient data loading and retrieval

**Cross-System Integration**
- **Shared User Data**: Unified user profiles across systems
- **Progress Sync**: XP and achievements shared between systems
- **Role Management**: Discord role integration
- **Permission System**: Role-based access control

### Performance Features

- **Asynchronous Operations**: Non-blocking API calls
- **Memory Management**: Efficient large dataset handling
- **Caching Strategies**: Minimize redundant operations
- **Error Recovery**: Graceful failure handling
- **Rate Limiting**: API abuse protection

## 🔧 Configuration

### Environment Variables (.env)

```bash
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
```

### System Configuration Files

**Systems/Random/Talk/**:
- `talk_templates.json`: AI response templates
- `blessings.json`: Blessing messages
- `jokes.json`: Joke database
- `user_lore.json`: Server lore storage

**Systems/Random/Walk Tru/**:
- `*.json`: Story maps for each genre

**Systems/EnergonPets/**:
- `pets_system.py`: Core pet logic and progression system (1313 lines, main PetSystem class with all functionality)
- `pets_commands.py`: Discord command handlers and UI with hybrid commands
- `battle_system.py`: Comprehensive battle engine (1624 lines) featuring turn-based combat, d20 roll mechanics, multi-battle types, group coordination, and interactive UI components
- `battle_commands.py`: Battle-specific command handlers (204 lines, 7 battle commands with interactive UI)
- `enemy_selection_view.py`: Interactive enemy selection UI with button-based navigation
- `energon_system.py`: Energon currency and betting system integration
- `energon_commands.py`: Energon management commands and utilities
- `slots.py`: Slot machine mini-game for energon rewards
- **Data Files:**
    - `pets_level.json`: 100-level progression data and thresholds
    - `monsters.json`: Monster definitions and battle configurations with rarity scaling
    - `transformation_items.json`: Evolution items and special equipment by class
    - `bosses.json`: Boss battle configurations for group battles
    - `titans.json`: Titan battle specifications

## 📁 File Structure

```
AllSpark/
├── 📄 allspark.py                 # Main bot entry point
├── 📄 README.md                   # This documentation
├── 📄 requirements.txt             # Python dependencies
├── 📄 .env.example                # Environment template
├── 📁 Systems/
│   ├── EnergonPets/            # Pet management system
│   │   ├── 📄 pets_system.py     # Core pet logic (1313 lines)
│   │   ├── 📄 battle_system.py   # Combat mechanics (PvP/PvE) (1624 lines, comprehensive battle engine with d20 mechanics)
│   │   ├── 📄 energon_system.py  # 1286-line Energon Game Engine with market events, slot machines, banking, and game state management
│   │   ├── 📄 battle_commands.py      # Battle-specific commands (204 lines, 7 battle commands with interactive UI)
│   │   ├── 📄 enemy_selection_view.py # 221-line interactive enemy selection UI with dropdown menus and battle type support
│   │   ├── 📄 energon_commands.py  # 723-line Energon mining game system with Transformers: Energon Rush
│   │   ├── 📄 slots.py                # Slot machine mini-game for energon rewards
│   ├── 📁 Random/                # Entertainment suite
│   │   ├── 📄 fun_system.py      # 900-line interactive games (shooting range, Hunger Games sorter, Mega-Fights)
│   │   ├── 📄 talk_system.py     # 1965-line conversational AI suite with lore, jokes, roasts, compliments, user analysis, and interactive features
│   │   ├── 📄 walktru.py         # Interactive stories
│   │   ├── 📄 themer.py          # Theme customization
│   │   ├── 📄 me.py              # User profiles
│   │   ├── 📁 Talk/              # Talk system data
│   │   ├── 📁 Walk Tru/          # Story maps
│   │   └── 📁 Talk/              # Configuration files
│   ├── 📁 PnW/                   # Politics & War system
│   │   └── 📄 recruit.py         # 887-line P&W recruitment system with real-time nation discovery, filtering, and messaging
│   ├── 📁 RPG/                   # Role-playing system
│   │   ├── 📄 rpg_system.py      # Core RPG logic
│   │   └── 📄 rpg_battle_system.py
│   ├── 📁 Data/                  # Shared game data
│   │   ├── 📄 monsters.json      # Monster definitions
│   │   ├── 📄 bosses.json        # Boss configurations
│   │   ├── 📄 pets_level.json    # Pet progression data
│   │   └── 📄 transformation_items.json
│   ├── 📁 Global Saves/          # User data storage
│   ├── 📄 user_data_manager.py   # Data management
│   └── 📄 admin_system.py        # Admin controls
├── 📄 cyberchronicles.py         # Legacy features
└── 📄 requirements.txt          # Dependencies
```

## 🛠️ Development

### Prerequisites

```bash
# System requirements
Python 3.8+
discord.py 2.3+
aiohttp 3.8+
pnwkit-py 1.0+
python-dotenv 1.0+
```

### Local Development Setup

1. **Clone and setup**
   ```bash
   git clone https://github.com/yourusername/AllSpark.git
   cd AllSpark
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Testing**
   ```bash
   python -m pytest tests/  # If tests exist
   python allspark.py --debug
   ```

### Adding New Features

1. **System Integration**: Add new systems in `Systems/[SystemName]/`
2. **Command Registration**: Use Discord.py slash command decorators
3. **Data Management**: Follow existing JSON storage patterns
4. **Cross-System**: Implement shared user data interfaces

### Code Style

- **PEP 8**: Follow Python style guidelines
- **Type Hints**: Use type annotations
- **Docstrings**: Document all functions and classes
- **Async/Await**: All Discord operations are async

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Contribution Process

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit changes**: `git commit -m 'Add amazing feature'`
4. **Push to branch**: `git push origin feature/amazing-feature`
5. **Open Pull Request**

### Reporting Issues

- **Bug Reports**: Use GitHub Issues with template
- **Feature Requests**: Use GitHub Discussions
- **Security Issues**: Email maintainers directly

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Discord.py Community**: For the excellent Discord API wrapper
- **Transformers Universe**: Inspiration for the theme and content
- **Politics & War**: For the recruitment system integration
- **Contributors**: All the amazing people who contributed to this project

## 📞 Support

- **Discord Server**: [Join our support server](https://discord.gg/pDTKNQJXdh)

---

<div align="center">
  <p><strong>AllSpark Bot</strong> - Bringing the Transformers universe to Discord</p>
  <p>Built with ❤️ by the AllSpark Development Team</p>
</div>
