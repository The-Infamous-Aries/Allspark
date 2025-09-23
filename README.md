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

A complete virtual pet and battle system with RPG elements, economy management, and competitive gameplay.

#### ⚔️ Battle System (`Systems/EnergonPets/PetBattles/`)
- **PvP Combat**: Real-time player vs player battles with strategic elements
- **Tournament System**: Organized competitive events with brackets and rewards
- **Enemy Selection**: AI-powered opponent matching and selection
- **Damage Calculator**: Complex damage calculation system with type advantages
- **Battle Lobby**: Interactive waiting rooms and matchmaking

#### 🐾 Pet Management & Progression
- **Pet Leveling**: Experience-based progression system with stat growth
- **Equipment System**: Gear and items that enhance pet abilities
- **Mega Evolution**: Special transformation mechanics for advanced pets
- **Pet Commands**: Comprehensive pet interaction and management

#### 💠 Energon Economy & Games
- **Energon Currency**: Primary in-game currency system
- **Slots Minigame**: Casino-style gambling with Transformers themes
- **CyberCoin Market**: Secondary currency and trading system
- **Economic Balance**: Carefully tuned reward and cost systems

#### 🎮 RPG System (`Systems/EnergonPets/RPG/`)
- **Character Progression**: RPG-style character development
- **Quest System**: Missions and objectives for players
- **Skill Trees**: Branching advancement paths

### 🤖 Random System (`Systems/Random/`)

Entertainment and interactive content system with AI-powered features.

#### 🎯 Core Features
- **Fun Commands**: Variety of entertainment and utility commands
- **Hunger Games Simulator**: AI-powered battle royale simulation
- **Interactive Adventures**: Choose-your-own-adventure style games
- **Theme System**: Customizable user profiles and appearances

#### 💬 Talk System (`Systems/Random/Talk/`)
- **Conversational AI**: Natural language interaction capabilities
- **Blessing System**: Positive affirmations and encouragement
- **Joke Database**: Curated humor content
- **User Lore**: Personalized story and character development
- **Template System**: Structured conversation frameworks

#### 🚶 Walk-Through Adventures (`Systems/Random/Walk Tru/`)
- **Multiple Scenarios**: Gangster, Horror, Knight, Robot, Western, Wizard themes
- **Interactive Storytelling**: Branching narrative paths
- **Character Development**: Role-playing elements within adventures

### 🏛️ PnW Recruitment System (`Systems/PnW/`)

Automated recruitment system for Politics and War game integration.

#### 🌐 Core Functionality
- **Automated Messaging**: Smart recruitment message delivery
- **Cooldown Management**: Rule-compliant messaging intervals (60-day same message, 60-hour any message)
- **Target Filtering**: Intelligent selection of recruitment candidates
- **Message Tracking**: Comprehensive logging and history management

#### 🛠️ Key Components
- **Recruitment Tracker**: Message history and cooldown enforcement
- **Interactive Views**: Discord UI components for recruitment management
- **Cache Management**: Efficient data handling and cleanup systems
- **Rule Compliance**: Built-in safeguards to prevent policy violations

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

The bot maintains comprehensive data persistence through JSON files:

- **Pet System Data**: `pets_level.json`, `pets_mission.json`, `pet_equipment.json`, `pet_xp.json`
- **Battle Data**: `bosses.json`, `monsters.json`, `titans.json`
- **Recruitment Data**: `recruit.json`, `recruit_backup.json`, `recruitment_history.json`
- **Entertainment Data**: `roasts.json`
- **System Logs**: `bot_logs.json`
- **Backup Systems**: Compressed backups (`.gz` files) for data recovery

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
- **Pet Management**: `/pet`, `/feed`, `/train`, `/evolve`
- **Battle System**: `/battle`, `/tournament`, `/challenge`
- **Economy**: `/energon`, `/shop`, `/inventory`, `/trade`
- **Equipment**: `/equip`, `/upgrade`, `/forge`
- **Slots**: `/slots`, `/jackpot`, `/leaderboard`

### 🤖 Random & Entertainment
- **Fun Commands**: `/joke`, `/roast`, `/blessing`, `/theme`
- **Games**: `/hungergames`, `/walktru`, `/adventure`
- **Social**: `/talk`, `/lore`, `/profile`
- **Interactive**: `/choose`, `/decide`, `/random`

### 🏛️ Recruitment Commands
- **Management**: `/recruit start`, `/recruit stop`, `/recruit status`
- **Configuration**: `/recruit config`, `/recruit messages`
- **Monitoring**: `/recruit history`, `/recruit stats`

### 👑 Admin Commands
- **Server Management**: `/admin config`, `/admin roles`, `/admin channels`
- **User Management**: `/admin user`, `/admin data`, `/admin backup`
- **System**: `/admin status`, `/admin logs`, `/admin restart`

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
