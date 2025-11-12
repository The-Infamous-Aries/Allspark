# 🌟 The AllSpark

> **The most advanced and complete Transformers-themed Discord bot.**  
> 🚨 **For help, bug reports, or feature requests: [Join the Support Discord Server!](https://discord.gg/pDTKNQJXdh)**

---

## 📋 Table of Contents

- [🚀 Overview](#-overview)
- [✨ Major Features](#-major-features)
  - [🐾 EnergonPets System](#-energonpets-system)
  - [🤖 Random System](#-random-system)
  - [🧠 Trivia System](#-trivia-system)
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
- **AI-Powered Battle Royale**: Groq AI integration for dynamic Transformers-themed deathmatch narratives with structured JSON output
- **40+ Cybertronian Factions**: Comprehensive faction system including Autobots, Decepticons, Maximals, Predacons, Seekers, Wreckers, Dinobots, Technobots, and many more
- **Advanced Participant Management**: Support for bot inclusion, specific user selection, Cybertronian-only filtering, and automatic role-based participant detection
- **Real-time Game Control**: Interactive Discord UI with start, next round, and end game controls with dynamic button states
- **Intelligent Storytelling**: AI-generated narratives with comprehensive error handling, fallback systems, and structured data processing
- **Flexible Game Setup**: Customizable warrior count (2-50), faction count (2-5), with comprehensive participant filtering options
- **Structured Round Processing**: Advanced JSON parsing with faction tracking, elimination management, and survivor statistics
- **Comprehensive Game State Management**: Persistent game tracking, round history, and detailed elimination records
- **Rich Discord Integration**: Embeds for game results, faction summaries, elimination notifications, and champion announcements
- **Robust Error Handling**: Fallback narrative generation, AI failure recovery, and data validation systems

#### 🗺️ Interactive Adventures (`Systems/Random/walktru.py`)
- **Six Themed Adventures**: Horror Sanitarium, Gangster's Rise, Knight's Quest, Robot Uprising, Western Frontier, Wizard's Apprentice
- **Dynamic Stat Systems**: Unique mechanics per adventure (Fear, Heat, Honor, Power, Health, Mana) with visual progress bars
- **Branching Narratives**: Complex choice-driven storylines with multiple endings and consequences
- **State Persistence**: User adventure progress saved across sessions with UserDataManager integration
- **Interactive UI**: Discord select menus and buttons for seamless story navigation
- **Stat Visualization**: Color-coded progress bars and warning thresholds for immersive gameplay

#### 💬 Advanced Talk System (`Systems/Random/talk_system.py` & `Systems/Data/Talk/`)
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

### 🧠 Trivia System (`Systems/trivia.py`)

Interactive knowledge testing system featuring comprehensive Transformers-themed trivia with real-time multiplayer gameplay and detailed performance tracking.

#### 🎯 Core Trivia Features
- **Multi-Category Support**: Five specialized trivia categories covering the entire Transformers universe
  - **Culture**: Cybertronian society, traditions, and lore
  - **Characters**: Iconic Autobots, Decepticons, and other faction members
  - **Factions**: Organizations, groups, and allegiances across the franchise
  - **Movies**: Live-action and animated film content and storylines
  - **Shows**: TV series, episodes, and animated content knowledge
- **Random Mix Mode**: Dynamic question selection from all categories for varied gameplay
- **Flexible Question Count**: Customizable sessions from 1-100 questions per game

#### 🎮 Interactive Gameplay
- **Real-time Multiplayer**: Multiple users can participate simultaneously in the same channel
- **Interactive UI**: Discord button interface with A, B, C, D answer choices
- **Smart Answer Tracking**: Each user can answer once per question with immediate feedback
- **Automatic Progression**: Questions advance after correct answers or 2-minute timeouts
- **Session Management**: One active trivia session per channel with proper cleanup

#### 📊 Performance Analytics
- **Individual Statistics**: Personal accuracy tracking and question attempt counts
- **Leaderboard System**: Real-time ranking based on correct answers and performance
- **Session Results**: Comprehensive end-game statistics showing all participant performance
- **Progress Tracking**: Visual progress indicators showing current question and category
- **Duration Monitoring**: Session timing and completion statistics

#### 🗄️ Data Integration
- **Extensive Question Database**: 3,900+ carefully curated trivia questions across all categories
- **UserDataManager Integration**: Seamless data loading with optimized performance
- **Question Randomization**: Smart selection algorithms ensuring varied gameplay experiences
- **Category Balance**: Well-distributed question counts across all trivia categories

### 🏛️ PnW Recruitment & War Analysis System (`Systems/PnW/`)

Comprehensive Politics and War integration featuring advanced recruitment automation, target analysis, and blitz party recommendation systems with full rule compliance and strategic warfare tools.

#### 🎯 Target Analysis & Blitz Party System (`destroy.py`)
- **Advanced Target Analysis**: Multi-format target identification (nation name, leader name, nation ID, or nation link)
- **Blitz Party Recommendations**: Intelligent analysis of optimal attack parties against specific targets
- **Combat Effectiveness Scoring**: Sophisticated military strength calculations with weighted unit values
- **Attack Range Validation**: Automatic verification of score-based attack eligibility (75%-250% range)
- **Strategic Asset Analysis**: Comprehensive evaluation of missiles, nukes, and defensive projects (Iron Dome, VDS)
- **Risk Assessment Engine**: Multi-factor risk analysis with Low/Medium/High classifications
- **Military Advantage Calculations**: Ground, air, naval, and overall military ratio analysis
- **Interactive Target Display**: Rich Discord embeds showing detailed target information and military assets
- **Multi-Party Comparison**: Top 3 attack option recommendations with detailed advantage/warning breakdowns

#### 🤖 Blitz Party Generation System (`blitz.py`)
- **Intelligent Party Creation**: Advanced algorithms for creating balanced 3-member attack parties with optimal military distribution
- **Strategic Composition Analysis**: Automated evaluation of ground, air, and naval advantages across party members
- **Score Range Optimization**: Ensures coordinated attack capability with compatible score ranges for same-target strikes
- **Military Capability Assessment**: Comprehensive analysis of current military units vs maximum capacity with daily production limits
- **Strategic Asset Prioritization**: Preference for nations with missiles, nukes, and defensive projects (Iron Dome, VDS)
- **Interactive Party Browser**: Paginated Discord UI for viewing detailed party compositions and member statistics
- **Real-time Military Intelligence**: Live military unit counts, production capabilities, and strategic project status
- **Team Name Assignment**: Randomized creative team names for enhanced coordination and identification
- **Persistent Data Storage**: Comprehensive party data saving with member details, statistics, and attack range calculations
- **Dynamic Party Management**: Real-time party resorting and optimization with updated alliance data
- **Nation Activity Filtering**: Automatic exclusion of vacation mode and applicant nations for active party composition
- **MMR Scoring System**: Advanced Military Might Rating calculations combining cities and combat effectiveness
- **Attack Range Calculations**: Precise target range analysis for coordinated party attacks (75%-250% score ratios)
- **Military Production Analysis**: Daily unit production limits and maximum capacity calculations for strategic planning

#### 🌐 Advanced Recruitment System (`recruit.py`)
- **Automated Nation Discovery**: Fetches up to 15,000 unallied nations from PnW API with comprehensive activity filtering
- **Enhanced Message Delivery**: Improved recruitment message sending with consistent 2-second delays to prevent API overload
- **Smart Message Selection**: Randomized recruitment templates featuring Transformers characters (Optimus Prime, Bumblebee, Megatron, etc.)
- **Advanced Cooldown Management**: Strict rule compliance (60-day same message, 60-hour any message cooldowns)
- **Real-time Task Tracking**: Background task management with detailed progress monitoring and cancellation support
- **Interactive Nation Browser**: Paginated Discord UI for reviewing and selecting recruitment targets
- **API Key Validation**: Built-in verification of P&W API key configuration before message sending
- **Comprehensive Statistics**: Detailed tracking of attempted, sent, and failed messages with success rate calculations
- **Enhanced Progress Tracking**: Real-time Discord embed updates showing campaign progress and performance metrics

### ⚔️ Military Alliance (MA) System (`Systems/PnW/MA/`)

Comprehensive military alliance management system providing advanced alliance statistics, blitz party generation, target analysis, and strategic warfare planning tools with sophisticated calculation engines and interactive Discord interfaces.

#### 🎯 Main Alliance Manager (`ma.py`)
- **Centralized Command Hub**: Primary interface for all MA system commands with intelligent module loading and error handling
- **Advanced Target Input System**: Multi-format target identification supporting nation names, leader names, nation IDs, and direct P&W links
- **Interactive UI Framework**: Dynamic Discord select menus and button interfaces for target type selection and command execution
- **Comprehensive Error Handling**: Robust fallback systems for missing dependencies and API failures with detailed error logging
- **Modular Architecture**: Intelligent import system with automatic fallback to local packages and graceful degradation
- **Real-time Status Monitoring**: Live command execution tracking with timeout management and user feedback systems

#### 🏭 Alliance Statistics & Full Mill Analysis (`alliance.py`)
- **Comprehensive Alliance Analytics**: Advanced statistical analysis of alliance nations with active member filtering (excludes applicants and vacation mode)
- **Full Mill Calculations**: Detailed military capacity analysis including current units, maximum capacity, daily production rates, and time-to-max calculations
- **Infrastructure & Improvements Tracking**: Complete breakdown of power plants, resource extraction, manufacturing facilities, and military improvements across all cities
- **Strategic Asset Evaluation**: Missile launch pads, nuclear research facilities, Iron Dome, and Vital Defense System project tracking
- **Interactive Data Visualization**: Rich Discord embeds with paginated displays, color-coded statistics, and real-time data refresh capabilities
- **Performance Metrics**: Alliance-wide scoring, city counts, military unit gaps, and production efficiency analysis
- **War Range Calculations**: Automated attack range analysis with 75%-250% score ratio validation for strategic planning

#### ⚡ Advanced Blitz Party System (`blitz.py`)
- **Intelligent Party Generation**: Sophisticated algorithms creating balanced 3-member attack parties with optimal military distribution and score compatibility
- **Strategic Composition Analysis**: Automated evaluation of ground, air, and naval advantages across party members with specialty balancing
- **Score Range Optimization**: Ensures coordinated attack capability with compatible score ranges for same-target strikes (75%-250% ratio compliance)
- **Military Capability Assessment**: Real-time analysis of current military units vs maximum capacity with daily production limits and strategic project evaluation
- **MMR Scoring System**: Advanced Military Might Rating calculations combining city counts, combat effectiveness, and infrastructure tiers
- **Interactive Party Browser**: Paginated Discord UI with detailed member statistics, war range displays, and strategic capability indicators
- **Dynamic Team Naming**: Creative randomized team names for enhanced coordination and alliance identification
- **Persistent Data Storage**: Comprehensive party data management with member details, statistics, and attack range calculations
- **Real-time Military Intelligence**: Live military unit counts, production capabilities, and strategic project status updates

#### 🧮 Advanced Calculation Engine (`calc.py`)
- **Comprehensive Statistical Analysis**: Centralized calculator for alliance statistics, military calculations, and performance metrics with robust error handling
- **Military Purchase Limits**: Advanced calculations for daily production rates, maximum unit capacities, and infrastructure-based limitations
- **Combat Score Calculations**: Sophisticated military effectiveness scoring combining soldiers, tanks, aircraft, and ships with weighted unit values
- **Infrastructure Tier System**: Multi-tier infrastructure classification (Destitute to Megalopolis) with corresponding statistical analysis
- **Nation Specialty Determination**: Intelligent classification of nations into Ground, Air, Naval, or Generalist specialties based on military composition
- **Project Detection System**: Comprehensive detection of strategic projects including Missile Launch Pads, Nuclear Research Facilities, Iron Dome, and VDS
- **Active Nation Filtering**: Advanced filtering systems excluding applicants, vacation mode nations, and inactive members from calculations
- **War Range Validation**: Precise attack range calculations ensuring compliance with P&W game mechanics (75%-250% score ratios)
- **Infrastructure Statistics**: Detailed infrastructure analysis including averages, totals, and improvement distribution across alliance cities

#### 🎯 Target Analysis & Destruction Planning (`destroy.py`)
- **Multi-Format Target Identification**: Advanced parsing supporting nation names, leader names, nation IDs, and direct Politics & War links
- **Comprehensive Target Profiling**: Detailed enemy analysis including military assets, strategic projects, city infrastructure, and economic indicators
- **Blitz Party Recommendations**: Intelligent analysis of optimal attack parties against specific targets with detailed advantage calculations
- **Combat Effectiveness Scoring**: Sophisticated military strength calculations with weighted unit values and strategic asset evaluation
- **Risk Assessment Engine**: Multi-factor risk analysis with Low/Medium/High classifications based on military ratios and defensive capabilities
- **Strategic Asset Analysis**: Comprehensive evaluation of missiles, nukes, and defensive projects (Iron Dome, VDS) with threat level assessment
- **Military Advantage Calculations**: Ground, air, naval, and overall military ratio analysis with detailed breakdowns and recommendations
- **Interactive Target Display**: Rich Discord embeds showing detailed target information, military assets, and attack recommendations
- **Multi-Party Comparison**: Top 3 attack option recommendations with detailed advantage/warning breakdowns and strategic considerations

#### 📋 Nation Management & Display (`nations.py`)
- **Alliance Nation Browser**: Interactive paginated display of alliance members with comprehensive military and economic statistics
- **Detailed Nation Profiles**: Individual nation cards showing leader information, Discord integration, city counts, scores, and policy data
- **Military Status Display**: Real-time military unit counts, daily production rates, maximum capacities, and current stockpiles
- **Strategic Capability Indicators**: Visual display of missile/nuclear capabilities, defensive projects, and military specialties
- **MMR Score Integration**: Military Might Rating calculations with specialty classification (Ground, Air, Naval, Generalist)
- **War Range Calculations**: Automated party war range analysis with average scoring and attack eligibility verification
- **Interactive Navigation**: Discord button controls for browsing nation lists with real-time data updates and pagination
- **Discord Integration**: Automatic Discord username and display name retrieval for enhanced member identification

#### 🎉 Party Management System (`parties.py`)
- **Saved Party Browser**: Interactive interface for viewing and managing previously generated blitz parties with comprehensive member statistics
- **Historical Party Tracking**: Persistent storage and retrieval of party compositions with detailed member information and attack statistics
- **Party Performance Analysis**: Detailed breakdowns of party military capabilities, score ranges, and strategic asset distribution
- **Interactive Party Navigation**: Paginated Discord UI for browsing saved parties with real-time data refresh and member detail displays
- **Party Data Management**: Advanced data conversion systems handling multiple storage formats with error recovery and validation
- **Real-time Party Updates**: Live data synchronization with alliance information ensuring current military status and availability
- **Enhanced Error Handling**: Comprehensive error recovery systems for data corruption, missing members, and API failures

#### 🔍 Centralized Query System (`query.py`)
- **GraphQL API Integration**: Advanced Politics & War API query system with optimized caching and comprehensive error handling
- **Alliance Data Management**: Intelligent caching of alliance nation data with 1-hour TTL and automatic refresh capabilities
- **Discord Username Enrichment**: Automatic retrieval and integration of Discord usernames and display names for alliance members
- **Comprehensive Nation Queries**: Detailed nation data retrieval including military units, cities, projects, alliances, and economic indicators
- **Cache Optimization**: Advanced caching systems with UserDataManager integration, TTL management, and forced refresh capabilities
- **Error Recovery Systems**: Robust fallback mechanisms for API failures, network issues, and data corruption scenarios
- **Real-time Data Synchronization**: Live data updates with activity filtering, vacation mode detection, and applicant exclusion
- **Performance Monitoring**: Comprehensive logging and performance tracking for all API interactions and cache operations

#### 🎯 Intelligent Party Sorting (`sorter.py`)
- **Advanced Sorting Algorithms**: Sophisticated party creation logic balancing military specialties, strategic capabilities, and score compatibility
- **Strategic Asset Prioritization**: Preference-based selection ensuring missile/nuclear capabilities within generated parties
- **Specialty Balance Optimization**: Intelligent distribution of Ground, Air, Naval, and Generalist specialties across party members
- **Infrastructure Tier Analysis**: Multi-tier infrastructure classification system ensuring compatible development levels within parties
- **Strength Window Grouping**: 500-point score range grouping system for optimal party composition and attack coordination
- **Fallback Party Generation**: Robust fallback systems creating viable parties when optimal conditions are not met
- **Active Nation Filtering**: Advanced filtering ensuring only active, non-vacation mode nations are included in party generation
- **Performance Optimization**: Efficient algorithms handling large alliance datasets with comprehensive error handling and validation

#### 🛠️ Key System Components
- **Recruitment Tracker** (`recruitment_tracker.py`): Comprehensive message history and cooldown enforcement system with UserDataManager integration
- **Interactive Views** (`recruit_views.py`): Advanced Discord UI components with pagination, nation activity indicators, and recruitment controls
- **Target Analysis Engine** (`destroy.py`): Sophisticated combat analysis system for strategic warfare planning
- **API Integration**: Robust PnWKit integration with fallback to local packages and comprehensive error handling
- **Task Management**: Asynchronous recruitment campaigns with real-time status monitoring and performance metrics
- **Rule Compliance Engine**: Built-in safeguards to prevent policy violations and maintain game rule adherence

#### 📊 Advanced Analytics & Features
- **Nation Activity Analysis**: Real-time activity indicators showing last login times with color-coded status (Active, Inactive, Very Inactive)
- **Performance Metrics**: Success rates, nations per minute, and comprehensive campaign statistics with detailed breakdowns
- **Flexible Message System**: Multiple recruitment templates with leader name personalization, Discord links, and alliance integration
- **Comprehensive Logging**: Detailed tracking of all recruitment activities with backup and recovery systems
- **Multi-page Nation Display**: Efficient browsing of large nation datasets with detailed nation information and filtering
- **Strategic Warfare Tools**: Complete target analysis with military comparisons, strategic asset evaluation, and attack recommendations
- **Combat Intelligence**: Advanced algorithms for analyzing party vs target matchups with recommendation scoring
- **Alliance Integration**: Built-in Cybertr0n Alliance ID integration for alliance-specific functionality

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
│   ├── trivia.py              # Interactive trivia game system
│   ├── Data/                  # Persistent storage
│   ├── EnergonPets/           # Complete pet and battle system
│   ├── PnW/                   # Politics and War integration
│   ├── Random/                # Entertainment and interactive content
│   └── Data/                  # Centralized data storage (Talk, Walk Tru, Users, Global Saves, Trivia)
└── local_packages/            # Bundled dependencies for deployment
```

### 🗄️ Data Storage (`Systems/Data/`)

The bot maintains comprehensive data persistence through specialized JSON files:

#### 🐾 Pet System Data (`Systems/Data/PetsInfo/`)
- **`pets_level.json`**: Pet progression system with 480 levels across multiple stages (Spark Initiate to advanced tiers), each with unique names and emojis
- **`pet_equipment.json`**: Equipment database with rarity-based chassis plating (Basic to Mythic), stat bonuses, and unlock requirements
- **`pets_mission.json`**: Mission templates categorized by difficulty levels with varied task descriptions for pet training
- **`pet_xp.json`**: Experience point thresholds defining XP requirements for each level (100 XP for level 1, scaling to 50,000+ for higher levels)

#### ⚔️ Battle System Data (`Systems/Data/PetsInfo/`)
- **`bosses.json`**: Boss entity database with rarity classifications (Common to Mythic), combat stats (HP, Attack, Defense), and reward systems
- **`monsters.json`**: Monster catalog featuring various enemy types with balanced combat statistics and energy/XP rewards
- **`titans.json`**: Titan collection including iconic Transformers characters with detailed descriptions, combat attributes, and rarity tiers

#### 🎯 Recruitment & War Analysis System Data
- **`recruit.json`**: Recruitment message templates featuring themed invitations from Transformers characters (Optimus Prime, Bumblebee, Megatron, etc.) with personalized content
- **`recruit_backup.json`**: Backup copy of recruitment templates for data recovery and system reliability
- **`recruitment_history.json`**: Historical tracking of recruitment campaigns with nation IDs, leader names, message numbers, and timestamps
- **`blitz_parties.json`**: Comprehensive blitz party data storage with detailed party compositions, member military intelligence, strategic capabilities, attack ranges, and team assignments

#### 🧠 Trivia System Data (`Systems/Data/Trivia/`)
- **`transformers_culture.json`**: Cybertronian culture, society, and lore questions (780+ questions)
- **`transformers_characters.json`**: Character knowledge covering Autobots, Decepticons, and other factions (780+ questions)
- **`transformers_factions.json`**: Organizations, groups, and allegiances across the franchise (780+ questions)
- **`transformers_movies.json`**: Live-action and animated film content and storylines (780+ questions)
- **`transformers_shows.json`**: TV series, episodes, and animated content knowledge (780+ questions)

#### 🎭 Entertainment & System Data
- **`roasts.json`**: Comprehensive collection of categorized roasts and humorous insults for entertainment commands (Systems/Data/Talk/)
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

### 🧠 Trivia & Knowledge

#### Interactive Trivia Gaming
- `/trivia` - Start interactive trivia sessions with category and question count selection:
  - **Categories**: Culture, Characters, Factions, Movies, Shows, Random Mix
  - **Question Count**: 1-100 questions per session
  - **Multiplayer Support**: Multiple users can participate simultaneously
  - **Real-time Scoring**: Live leaderboards and performance tracking
  - **Interactive UI**: A, B, C, D button interface with immediate feedback

---

### 🏛️ PnW Recruitment & War Analysis Commands

#### Target Analysis & Strategic Warfare
- `/destroy` - Advanced target analysis and blitz party recommendations
  - **Multi-format Target Input**: Nation name, leader name, nation ID, or nation link support
  - **Combat Analysis**: Comprehensive military strength comparison and strategic asset evaluation
  - **Attack Recommendations**: Top 3 optimal blitz party suggestions with risk assessment
  - **Military Ratios**: Ground, air, naval, and overall advantage calculations
  - **Strategic Intelligence**: Missile/nuke analysis vs defensive projects (Iron Dome, VDS)

#### Blitz Party Management
- `/blitz_parties` (aliases: `/blitz`, `/parties`) - Generate and manage strategic attack parties
  - **Intelligent Party Creation**: Automated generation of balanced 3-member attack teams
  - **Interactive Mode Selection**: Choose between "Sort into Parties" or "View Nations" modes
  - **Strategic Composition**: Optimal distribution of ground, air, and naval military advantages
  - **Real-time Military Analysis**: Live unit counts, production limits, and strategic capabilities
  - **MMR Scoring**: Advanced Military Might Rating calculations for party optimization
  - **Attack Range Coordination**: Ensures party members can attack the same targets (score compatibility)
  - **Strategic Asset Prioritization**: Preference for nations with missiles, nukes, and defensive projects
  - **Interactive Party Browser**: Paginated Discord UI with detailed party statistics and member information
  - **Dynamic Party Management**: Real-time party resorting and optimization capabilities
  - **Persistent Data Storage**: Comprehensive party data saving with full military intelligence
  - **Team Name Assignment**: Creative team names for enhanced coordination and identification
  - **Nation Activity Filtering**: Automatic exclusion of vacation mode and applicant nations

#### Campaign Management
- `/recruit` - Enhanced recruitment campaigns with improved nation browser
  - **Activity Filtering**: Real-time nation activity indicators with color-coded status
  - **Interactive UI**: Paginated nation display with recruitment controls
  - **Smart Targeting**: Comprehensive nation information and selection tools
- `/recruit_cancel` - Cancel active recruitment tasks with immediate cleanup

#### Monitoring & Analytics
- `/recruit_status` - Detailed task progress with enhanced metrics and performance tracking
- `/recruitment_stats` - Comprehensive historical recruitment statistics with success rate analysis
- `/pnwkit_status` - API integration health check with version and source information

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