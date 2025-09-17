# 🌟 The AllSpark

> **The most advanced and complete Transformers-themed Discord bot.**  
> 🚨 **For help, bug reports, or feature requests: [Join the Support Discord Server!](https://discord.gg/pDTKNQJXdh)**

---

## 📋 Table of Contents

- [🚀 Overview](#-overview)
- [✨ Major Features](#-major-features)
  - [🐾 EnergonPets System](#-energonpets-system)
    - [⚔️ Battle System](#️-battle-system)
    - [🐾 Pet Leveling & Progression System](#-pet-leveling--progression-system)
    - [💠 Energon Economy & Game](#-energon-economy--game)
    - [🎰 Slots Minigame](#-slots-minigame)
    - [🪙 CyberCoin Market](#-cybercoin-market)
  - [🛡️ Transformers RPG System](#️-transformers-rpg-system)
    - [🎮 Character Creation & Progression](#-character-creation--progression)
    - [⚔️ RPG Battle System](#️-rpg-battle-system)
    - [🧭 Story, Events, & Loot](#-story-events--loot)
  - [🤖 Random System](#-random-system)
    - [🕹️ Main Features](#-main-features)
      - [🎯 Shooting Range](#-shooting-range)
      - [🏹 Hunger Games Sorter](#-hunger-games-sorter)
      - [👾 Walktru Interactive Adventures](#-walktru-interactive-adventures)
      - [💬 Conversational AI & Lore](#-conversational-ai--lore)
      - [📚 Server Lore System](#-server-lore-system)
      - [🤖 Profile & Theme System](#-profile--theme-system)
      - [🔗 Combiner Teams & Mega-Fight](#-combiner-teams--mega-fight)
    - [🗂️ Key Random System Modules](#️-key-random-system-modules)
  - [🏛️ PnW Recruitment System](#-pnw-recruitment-system)
    - [🌐 What It Does](#-what-it-does)
    - [🛠️ Major Features](#️-major-features-1)
  - [👑 Admin System](#-admin-system)
    - [🛠️ Major Features](#️-major-features-2)
  - [🗂️ User Data Manager](#️-user-data-manager)
    - [🚀 Key Features](#-key-features)
    - [📦 What Does It Store?](#-what-does-it-store)
    - [🛠️ Key API Methods (examples)](#️-key-api-methods-examples)
- [🗂️ System Components & Cogs](#️-system-components--cogs)
- [📜 Complete Commands List (62+)](#-complete-commands-list-62)
  - [🐾 EnergonPets & Economy](#-energonpets--economy)
  - [📜 RPG Commands](#-rpg-commands)
  - [📜 Core Random & Fun Commands List](#-core-random--fun-commands-list)
  - [📜 Recruitment Commands](#-recruitment-commands)
  - [📜 Admin Commands](#-admin-commands)
- [🏗️ Architecture & Data](#-architecture--data)
- [🔧 Configuration](#-configuration)
- [📁 File Structure](#-file-structure)
- [🛠️ Development & Support](#️-development--support)
- [🤝 Contributing](#-contributing)
- [📄 License](LICENSE.txt)
- [🔗 Support](#-support)

---

## 🚀 Overview

AllSpark is a modular, feature-rich Discord bot that brings the Transformers universe to life through interactive digital pets, RPG battles, interactive stories, games, recruiting, a full cyber-economy, and much more.  
**Every system, view, and cog is documented here.**

---

# ✨ Major Features

## 🐾 EnergonPets System

- **Adopt and raise a digital Transformer pet** (Autobot or Decepticon) with unique attributes, evolution stages, and persistent stats.
- **Pet management** includes Energy, Happiness, Maintenance, Equipment, and a massive progression ladder up to level 500.
- **Actions:** Charge, Play, Repair, Train, Rename, and send on Missions. Each action affects stats and unlocks new rewards.
- **Loot & Equipment:** Earn, equip, and collect 100+ unique items (Chassis Plating, Energy Cores, Utility Modules) across 6 rarity tiers.
- **Persistent growth:** All progress, stats, and inventory are saved across servers.
- **Battle Integration:** Pets are fully integrated into the battle system, with equipment affecting combat performance and battle rewards improving pet stats.
- **PvP Integration:** Use your pets in competitive PvP battles, with special PvP-only equipment and rewards.
- **Cross-system Synergy:** Pet stats directly influence battle effectiveness, creating a unified progression system.

### ⚔️ Battle System

#### Core Features
- **Turn-based d20 Combat**: Classic RPG-style battles with rich mechanics including:
  - Critical hits and special moves
  - Group defense and parry systems
  - Charge mechanics for powerful attacks
  - Guard/Protect mechanics for team play

#### Battle Types
- **Solo Battles**: Face off against AI-controlled monsters
- **Group Battles**: Team up with friends (up to 4 players) to take on powerful bosses and titans
- **PvP Modes**:
  - 1v1 Duel: Classic head-to-head combat
  - Team Battles: 2v2, 3v3, and 4v4 team-based combat
  - Free-For-All: Every pet for themselves in chaotic battles
  - Energon Challenges: High-stakes battles with Energon wagers

#### Battle Mechanics
- **Interactive UI**: Full Discord UI with buttons, select menus, and real-time updates
- **Action System**: Players choose from Attack, Defend, Charge, and Special moves
- **Status Effects**: Various buffs and debuffs that affect combat
- **Dynamic Scaling**: Enemy difficulty scales based on player levels and party size
- **Spectator Mode**: Watch ongoing battles with live updates

#### Enemy System
- **100+ Unique Enemies**: Across multiple types and rarities with unique abilities and loot tables
- **Interactive Enemy Selection**: Advanced UI for choosing enemies by type and rarity
- **Enemy Types**:
  - 🏃 Monsters: Standard enemies with balanced stats and basic loot drops
  - 👹 Bosses: Powerful foes with special abilities and rare equipment drops
  - 👑 Titans: Legendary challenges requiring coordinated teams with mythic rewards
- **Rarity Tiers**: Common, Uncommon, Rare, Epic, Legendary, and Mythic variants
- **Dynamic Scaling**: Enemy stats automatically scale based on player level and party size

#### Enemy Selection System (`enemy_selection_view.py`)
- **Rich Interactive UI**: Discord embeds with enemy previews and stat comparisons
- **Type Filtering**: Select specific enemy types (Monsters, Bosses, Titans) for targeted battles
- **Rarity Selection**: Choose desired loot rarity to influence battle difficulty and rewards
- **Real-time Stats**: Display enemy health, attack power, and special abilities before battle
- **Recommended Level**: Shows suggested pet level for each enemy to help players choose appropriate challenges
- **Team Compatibility**: Validates party composition against selected enemy difficulty

#### Rewards & Progression
- **Experience & Leveling**: Gain XP to level up your pet
- **Loot Drops**: Random equipment drops based on enemy difficulty
- **Achievements**: Unlock special rewards and titles
- **Leaderboards**: Compete for top spots in various categories

#### Technical Implementation
- **BattleSystem Class**: Central manager for all active battles across servers
- **UnifiedBattleView**: Core battle interface handling all battle types with real-time Discord UI
- **EnemySelectionView**: Interactive enemy type and rarity selection with rich embeds
- **PvP Lobby System**: Advanced matchmaking and team management for all PvP modes
- **Efficient State Management**: Handles thousands of concurrent battles with async processing
- **Persistent Data**: All battle progress, rewards, and statistics automatically saved

#### PetBattles Module Architecture
- **`battle_system.py`**: Core battle engine with UnifiedBattleView and battle state management
- **`enemy_selection_view.py`**: Interactive enemy selection with type/rarity filtering
- **`pvp_system.py`**: Complete PvP battle system with matchmaking and team coordination
- **`pvp_lobby.py`**: Advanced lobby system for organizing PvP battles and tournaments

#### PvP Lobby System (`pvp_lobby.py`)
- **Multi-mode Support**: Organize 1v1 duels, team battles (2v2, 3v3, 4v4), and free-for-all matches
- **Interactive Lobby Creation**: Rich Discord embeds for creating and managing battle lobbies
- **Team Formation**: Dynamic team assignment with automatic balancing based on pet levels
- **Ready System**: Players can mark themselves ready/unready with real-time status updates
- **Spectator Mode**: Allow non-participants to watch ongoing battles with live updates
- **Tournament Mode**: Support for bracket-style tournaments with elimination tracking
- **Cross-server Battles**: Enable battles between players from different Discord servers
- **Battle History**: Track PvP match results with detailed statistics and leaderboards

#### Advanced Features
- **Smart AI**: Adaptive enemy behavior based on party composition and battle conditions
- **Equipment Integration**: Battle performance directly affected by equipped pet items
- **Multi-phase Battles**: Bosses with multiple forms, escalating attack patterns, and special phases
- **Cross-server Compatibility**: Battle with players across different Discord servers
- **Combat Analytics**: Detailed battle history, win rates, damage statistics, and performance tracking
- **Real-time Spectator Mode**: Watch live battles with health bars and action updates
- **Battle Replay System**: Review completed battles with full turn-by-turn breakdowns

#### PvP Battle System (`pvp_system.py`)
- **Comprehensive PvP Engine**: Complete battle system for player vs player combat
- **Multi-format Support**: Handles 1v1, 2v2, 3v3, and 4v4 team battles seamlessly
- **Real-time Turn Management**: Synchronized turn processing across all participants
- **Elo Rating System**: Skill-based matchmaking with rating adjustments after battles
- **Battle Validation**: Pre-battle checks for pet eligibility, equipment, and level requirements
- **Spectator Integration**: Built-in spectator mode with live battle updates
- **Battle Recording**: Complete battle logs with damage calculations and turn summaries
- **Anti-cheat Protection**: Validates battle actions and prevents exploitation
- **Cross-server Support**: Enables battles between players from different Discord servers
- **Tournament Integration**: Direct integration with PvP lobby system for organized events

#### Pet System Integration (`pets_system.py`)
- **Battle-ready Pet Management**: Core pet system that feeds directly into battle calculations
- **Stat-to-Battle Conversion**: Pet attributes (Attack, Defense, Speed, Special) translate directly into battle effectiveness
- **Equipment Impact**: All equipped items provide immediate combat bonuses and special abilities
- **Level Scaling**: Pet levels provide exponential stat growth, making higher-level pets significantly stronger
- **Battle Experience**: Pets gain experience from both PvE and PvP battles, accelerating their progression
- **Cross-server Pet Storage**: Pets persist across all Discord servers, enabling universal battle participation
- **Pet Commands Integration**: Direct integration with battle commands for seamless pet selection and management
- **PvP Pet Validation**: Automatic checking of pet eligibility for different PvP formats based on level and equipment

#### Battle Commands Interface (`battle_commands.py`)
- **Comprehensive Command Suite**: Complete set of Discord slash commands for all battle interactions
- **Smart Pet Selection**: Automatic detection and selection of your active pet for battles
- **Interactive Enemy Selection**: Rich Discord UI for browsing and selecting enemies by type and rarity
- **PvP Matchmaking Commands**: Quick matchmaking for 1v1, team battles, and custom PvP formats
- **Battle Management**: Real-time battle status, turn notifications, and action prompts
- **Spectator Commands**: Join ongoing battles as a spectator with live updates and battle replays
- **Team Formation**: Easy team creation and management for group battles and PvP modes
- **Battle History**: Access detailed battle logs, statistics, and performance analytics
- **Cross-server Compatibility**: Commands work seamlessly across all Discord servers with unified pet data
- **Error Handling**: Comprehensive validation and user-friendly error messages for all battle scenarios

**Key Commands:**
- `/battle` - Start a solo battle with enemy selection
- `/battle_group` - Create or join group battles with friends
- `/pvp_duel` - Challenge another player to 1v1 PvP combat
- `/pvp_team` - Organize team battles (2v2, 3v3, 4v4)
- `/pvp_lobby` - Create custom PvP lobbies with specific rules
- `/battle_spectate` - Watch ongoing battles as a spectator
- `/battle_history` - View your battle statistics and replays
- `/pet_select` - Choose your active pet for battles
- `/team_form` - Create and manage battle teams

### 🐾 Pet Leveling & Progression System

The new **Pet Leveling System** transforms your digital pets into powerful warriors with an extensive progression path from Level 1 to **Level 500**, featuring 50 unique stages of evolution and balanced stat progression.

#### 🎯 Leveling Mechanics

**Experience System:**
- **Level 1-50**: Basic progression covering Stages 1-5 (Spark Initiate to Cyber Warrior)
- **Level 51-100**: Advanced progression covering Stages 6-10 (Matrix Guardian to Allspark Warden)
- **Level 101-150**: Elite progression covering Stages 11-15 (Titan Initiate to Matrix Sage)
- **Level 151-200**: Master progression covering Stages 16-20 (Vector Prophet to Reality Weaver)
- **Level 201-250**: Legendary progression covering Stages 21-25 (Primus Voice to Cybertron Hope)
- **Level 251-300**: Mythic progression covering Stages 26-30 (Titan Lord to Matrix Oracle)
- **Level 301-350**: Omega progression covering Stages 31-35 (Vector Master to Reality Master)
- **Level 351-400**: Supreme progression covering Stages 36-40 (Primus Herald to Cybertron Genesis)
- **Level 401-450**: Titan progression covering Stages 41-45 (Titan Genesis to Matrix Genesis)
- **Level 451-500**: Genesis progression covering Stages 46-50 (Vector Genesis to Genesis Supreme)

**XP Sources:**
- **Battles**: Primary XP source, scaled by enemy difficulty and battle outcome
- **Missions**: Variable XP rewards based on mission difficulty and duration
- **Training**: Daily training sessions provide steady XP gains
- **Special Events**: Bonus XP during server events and achievements

#### 🏆 Evolution Stages (50 Tiers)

**Stage Progression by Level:**

| Stage | Name | Level Range | Emoji | Power Tier |
|-------|------|-------------|--------|------------|
| 1 | Spark Initiate | 1-10 | ✨ | Basic |
| 2 | Protoform Cadet | 11-20 | 🤖 | Basic |
| 3 | Data Scout | 21-30 | 📊 | Basic |
| 4 | Energon Trooper | 31-40 | ⚡ | Basic |
| 5 | Cyber Warrior | 41-50 | 🛡️ | Basic |
| 6 | Matrix Guardian | 51-60 | 💎 | Advanced |
| 7 | Prime Aspirant | 61-70 | ⭐ | Advanced |
| 8 | Spark Champion | 71-80 | 🔥 | Advanced |
| 9 | Vector Seer | 81-90 | 🔮 | Advanced |
| 10 | Allspark Warden | 91-100 | 🌟 | Advanced |
| 11 | Titan Initiate | 101-110 | 🏗️ | Elite |
| 12 | City Speaker | 111-120 | 🏙️ | Elite |
| 13 | Combiner Core | 121-130 | 🔗 | Elite |
| 14 | Omega Sentinel | 131-140 | 🔱 | Elite |
| 15 | Matrix Sage | 141-150 | 📜 | Elite |
| 16 | Vector Prophet | 151-160 | ✨ | Master |
| 17 | Chronos Knight | 161-170 | ⏰ | Master |
| 18 | Quantum Master | 171-180 | ⚛️ | Master |
| 19 | Void Walker | 181-190 | 🌌 | Master |
| 20 | Reality Weaver | 191-200 | 🕸️ | Master |
| 21 | Primus Voice | 201-210 | 🎵 | Legendary |
| 22 | Unicron Bane | 211-220 | 🌑 | Legendary |
| 23 | Spark Eternal | 221-230 | ♾️ | Legendary |
| 24 | Matrix Avatar | 231-240 | 👑 | Legendary |
| 25 | Cybertron Hope | 241-250 | 🌅 | Legendary |
| 26 | Titan Lord | 251-260 | 👑 | Mythic |
| 27 | City Commander | 261-270 | 🏰 | Mythic |
| 28 | Combiner Supreme | 271-280 | 💪 | Mythic |
| 29 | Omega Force | 281-290 | 💥 | Mythic |
| 30 | Matrix Oracle | 291-300 | 🔮 | Mythic |
| 31 | Vector Master | 301-310 | 🧭 | Omega |
| 32 | Chronos Lord | 311-320 | ⏳ | Omega |
| 33 | Quantum Lord | 321-330 | 🔬 | Omega |
| 34 | Void Sovereign | 331-340 | 🌀 | Omega |
| 35 | Reality Master | 341-350 | 🎭 | Omega |
| 36 | Primus Herald | 351-360 | 📯 | Supreme |
| 37 | Unicron Scourge | 361-370 | ☄️ | Supreme |
| 38 | Spark Genesis | 371-380 | 🌌 | Supreme |
| 39 | Matrix Genesis | 381-390 | 💫 | Supreme |
| 40 | Cybertron Genesis | 391-400 | 🌍 | Supreme |
| 41 | Titan Genesis | 401-410 | 🌋 | Titan |
| 42 | City Genesis | 411-420 | 🏛️ | Titan |
| 43 | Combiner Genesis | 421-430 | ⚡ | Titan |
| 44 | Omega Genesis | 431-440 | 🔱 | Titan |
| 45 | Matrix Genesis | 441-450 | 💠 | Titan |
| 46 | Vector Genesis | 451-460 | 🌠 | Genesis |
| 47 | Chronos Genesis | 461-470 | 🕰️ | Genesis |
| 48 | Quantum Genesis | 471-480 | 🎯 | Genesis |
| 49 | Void Genesis | 481-490 | 🌌 | Genesis |
| 50 | Genesis Supreme | 491-500 | 👑 | Genesis |

#### ⚖️ Balanced Stat Progression

**Faction-Based Scaling:**
- **Autobots**: +10% Defense, -10% Attack bonus progression
- **Decepticons**: +10% Attack, -10% Defense bonus progression
- **Neutral**: Balanced progression with no bonuses or penalties

**Stage-Based Stat Targets:**

**Stages 1-5 (Levels 1-50) - Basic Tier:**
- Target Resources: 900 total (Energy/Maintenance/Happiness)
- Target Attack: 100 base (110 Decepticon / 90 Autobot)
- Target Defense: 100 base (90 Decepticon / 110 Autobot)

**Stages 6-10 (Levels 51-100) - Advanced Tier:**
- Target Resources: 2,500 total
- Target Attack: 200 base (220 Decepticon / 180 Autobot)
- Target Defense: 200 base (180 Decepticon / 220 Autobot)

**Stages 11-15 (Levels 101-150) - Elite Tier:**
- Target Resources: 7,000 total
- Target Attack: 400 base (440 Decepticon / 360 Autobot)
- Target Defense: 400 base (360 Decepticon / 440 Autobot)

**Stages 16-20 (Levels 151-200) - Master Tier:**
- Target Resources: 15,000 total
- Target Attack: 800 base (880 Decepticon / 720 Autobot)
- Target Defense: 800 base (720 Decepticon / 880 Autobot)

**Stages 21-25 (Levels 201-250) - Legendary Tier:**
- Target Resources: 25,000 total
- Target Attack: 1,600 base (1,750 Decepticon / 1,450 Autobot)
- Target Defense: 1,600 base (1,450 Decepticon / 1,750 Autobot)

**Stages 26-30 (Levels 251-300) - Mythic Tier:**
- Target Resources: 50,000 total
- Target Attack: 3,200 base (3,500 Decepticon / 2,900 Autobot)
- Target Defense: 3,200 base (2,900 Decepticon / 3,500 Autobot)

**Stages 31-35 (Levels 301-350) - Omega Tier:**
- Target Resources: 100,000 total
- Target Attack: 6,400 base (7,000 Decepticon / 5,800 Autobot)
- Target Defense: 6,400 base (5,800 Decepticon / 7,000 Autobot)

**Stages 36-40 (Levels 351-400) - Supreme Tier:**
- Target Resources: 250,000 total
- Target Attack: 12,800 base (14,000 Decepticon / 11,600 Autobot)
- Target Defense: 12,800 base (11,600 Decepticon / 14,000 Autobot)

**Stages 41-45 (Levels 401-450) - Titan Tier:**
- Target Resources: 500,000 total
- Target Attack: 25,600 base (28,000 Decepticon / 23,200 Autobot)
- Target Defense: 25,600 base (23,200 Decepticon / 28,000 Autobot)

**Stages 46-50 (Levels 451-500) - Genesis Tier:**
- Target Resources: 1,000,000+ total
- Target Attack: 51,200+ base (56,000+ Decepticon / 46,400+ Autobot)
- Target Defense: 51,200+ base (46,400+ Decepticon / 56,000+ Autobot)
- Cross-server competitive viability
- Ultimate power ceiling for dedicated players

#### 🎮 Leveling Features

**Automatic Progression:**
- **Smart XP Distribution**: Experience automatically applied with level-up notifications
- **Stat Auto-Scaling**: Stats increase automatically based on faction and progression stage
- **Random Bonus Rolls**: Small random stat bonuses (1-5 points) on each level up
- **Stage Notifications**: Rich embed notifications when reaching new evolution stages

**Cross-Server Persistence:**
- **Universal Progress**: Pet levels and stats persist across all Discord servers
- **Equipment Compatibility**: All equipment scales with pet level progression
- **Battle Integration**: Higher level pets unlock advanced battle features and enemy types

**Progression Milestones:**
- **Stage 5 (Level 50)**: Unlock advanced equipment slots and basic battle features
- **Stage 10 (Level 100)**: Access to boss-tier enemies and rare missions
- **Stage 15 (Level 150)**: Elite content unlock and enhanced equipment options
- **Stage 20 (Level 200)**: Master-tier content and advanced PvP features
- **Stage 25 (Level 250)**: Legendary status with exclusive battle modes
- **Stage 30 (Level 300)**: Mythic-tier challenges and unique cosmetic rewards
- **Stage 35 (Level 350)**: Omega-level content and cross-server competitive features
- **Stage 40 (Level 400)**: Supreme-tier status with genesis-level equipment
- **Stage 45 (Level 450)**: Titan-tier advancement with server-wide recognition
- **Stage 50 (Level 500)**: Genesis Supreme status with exclusive titles and rewards

#### 📊 Technical Implementation

**Data Files:**
- `pet_levels.py` - Core leveling logic and stat calculation engine
- `pets_level.json` - 50 evolution stages with level ranges and emojis
- `pet_xp.json` - Complete XP threshold table for all 500 levels
- `pets_level.json` - Faction-specific pet name pools (Autobot/Decepticon)

**Key Functions:**
- `get_stage_for_level(level)` - Returns evolution stage for any given level
- `get_level_experience(level)` - Returns XP required for next level
- `get_total_experience_for_level(target_level)` - Calculates total XP needed from level 1
- `add_experience()` - Handles XP gains with automatic level-ups and stat increases
- `get_stage_name(level)` - Returns the display name for pet's current stage
- `get_stage_emoji(level)` - Returns the emoji for current evolution stage

#### 🎨 Pet Naming System

**Autobot Names (100+ options):**
- Guardian-themed names: "Guardian Spark", "Shield Circuit", "Protector Protocol"
- Peacekeeper names: "Peace Maker", "Harmony Bot", "Serenity Core"
- Elemental names: "Sunshine Guard", "Moonlight Keeper", "Starlight Protector"

**Decepticon Names (100+ options):**
- Warrior names: "Annihilator Core", "Destructor Prime", "Oblivion Engine"
- Dark-themed: "Shadow Slayer", "Darkness Destroyer", "Void Vanguard"
- Power names: "War Machine", "Battle Bot", "Combat Core"

**Team Names (50+ options):**
- Tech-themed: "The Rusty Bolts", "Overclocked Outlaws", "404 Team Not Found"
- Gaming references: "The Binary Brawlers", "Syntax Error Squad", "The Glitch Mob"

### 💠 Energon Economy & Game

- **Energon:** The core currency, earned from battles, missions, events, and games.
- **Energon Rush:** A cross-server competitive game where players race from 0 to 10,000 Energon—progress resets each game, but leaderboard and stats persist.
- **Banking:** Bank your Energon for safekeeping or risk it in games and challenges.
- **Leaderboards:** Track global, daily, weekly, and all-time rankings.

### 🎰 Slots Minigame

- **Energon Slot Machine:** Play for fun or bet Energon in a flashy, interactive slot machine with 3-reel and 6-stage spinning animations.
- **Difficulties:** Easy (skills), Medium (characters), Hard (zodiac)—each with unique emoji themes and payout multipliers.
- **Win tracking:** Full stats, including jackpots, winnings, losses, and highest bets.

### 🪙 CyberCoin Market

- **Simulated cryptocurrency:** Buy, sell, and trade CyberCoin, with a real-time updating market and price chart.
- **Market events:** Dynamic world/holiday events, random surges and crashes, and a complete market history.
- **Portfolio tracking:** Persistent user holdings, profit/loss, and transaction history.
- **Interactive UI:** Buy/sell through Discord modals, see live market stats and trends.
- **Leaderboard:** Track your position among the richest CyberCoin traders.

## 🛡️ Transformers RPG System

The RPG system in AllSpark lets you create your own original Cybertronian character, join group adventures, and participate in classic turn-based battles—fully themed for Transformers and deeply integrated with the rest of the bot.

### 🎮 Character Creation & Progression

- **Create up to three custom characters** per user, each with their own name, faction (Autobot or Decepticon), and class (e.g., Scientist, Warrior, Engineer, Mariner, Scout, Seeker, Commander, Medic).
- **Classes have unique stat templates** (Attack, Defense, Dexterity, Intelligence, Charisma, HP), and your main stat determines your health scaling and battle focus.
- **Persistent leveling:** Gain experience from battles, missions, and events. Stat increases and unique bonuses as you level up.
- **Full inventory system:** Collect, equip, and manage beast modes, transformations, weapons, and armor—each with their own rarity and effects.

### ⚔️ RPG Battle System

- **Classic turn-based d20 combat:** Solo, group (up to 4 players), and PvP battles. Group up against monsters, bosses, or legendary titans.
- **Dynamic enemies:** 100+ monsters, bosses, and titans, each with distinct stats and rarities.
- **Interactive UI:** Battle views, action buttons, health bars, and real-time updates.
- **Skill checks, parries, and criticals:** Use your character’s main stats in and out of combat.
- **Party mechanics:** Group skill checks and “first to react” events, where the fastest player in your party makes key choices for the group.

### 🧭 Story, Events, & Loot

- **AI-powered story engine:** Adventures, group events, and exploration segments are generated dynamically, blending Transformers lore with your party’s actions and choices.
- **Skill-based random events:** Parties face events where Attack, Defense, Dexterity, Intelligence, or Charisma may be tested, with outcomes and rewards based on rolls and stats.
- **Loot & rewards:** Battles and events can grant powerful new items, rare transformations, XP, and energon. All loot is persistent and equippable.
- **Full integration:** RPG inventory items can cross over with the EnergonPets and global economy systems for a unified experience.

## 🤖 Random System

The Random System in AllSpark brings a huge variety of games, minigames, lore, fun utilities, and interactive experiences to your server. It's loaded with entertainment, social, and creative features.

### 🕹️ Main Features

#### 🎯 Shooting Range

- **/range** — Fast-paced reaction game: race to click the 🎯 target before time runs out!
- Tracks hits, accuracy, and new personal bests, with full stat history and ranks (Matrix Bearer, Spark Guardian, etc).
- Leaderboard and performance stats for all users.

#### 🏹 Cybertron Games (AI-Powered Hunger Games)

- **/cybertron_games** — Launch the ultimate Transformers-themed deathmatch experience with AI-generated cybertronian narratives.
- **Dynamic Configuration:** Configure up to 12 districts and 10 factions with custom naming, supporting up to 50 participants.
- **Role-Based Filtering:** Automatically filter participants using Cybertronian Citizen role IDs from server configuration.
- **Smart Participant Selection:** Choose specific users, include/exclude bots, and verify Cybertronian citizenship status.
- **AI Story Generation:** Powered by Gemini-1.5-pro for epic cybertronian narratives featuring energon combat, spark core battles, and ancient Prime technology.
- **District & Faction System:** Warriors assigned to dynamic districts (Energon Elite, Plasma Core, Spark Extractors, etc.) and factions (Autobot, Decepticon, Maximal, Predacon, etc.) with loyalty conflicts.
- **Alliance Tracking:** Real-time alliance formation, betrayal mechanics, and faction shift dynamics.
- **Pure Cybertronian Lore:** 100% Transformers-themed with energon weapons, spark extractors, ancient relics, and orbital arena combat.
- **Interactive Progress:** Rich embeds with district assignments, faction allegiances, and elimination summaries.
- **Legacy Support:** **/hg_sorter** still available for basic district sorting with bot/citizen filtering.

#### 👾 Walktru Interactive Adventures

- **/walktru** — Choose a story genre (Horror, Gangster, Knight, Robot, Western, Wizard) and play a branching, fully interactive adventure.
- 20+ event stages per story, different mechanics (fear, heat, honor, power, health, mana), progress bars, and dozens of outcomes.
- Every choice impacts your character and the narrative.
- Visual progress bars, event warnings, endings, and full journey summaries.

#### 💬 Conversational AI & Lore

- **/user_says** — Analyze the top 3 words used by you or any user in the server and generate a funny "What would you say?" line.
- **/what_is** — Explore Transformers lore on any topic, with rich embeds from a curated database.
- **/blessing** — Receive a random or themed "blessing" from the Allspark.
- **/joke** and **/roast** — Get a joke (Transformers, coding, puns, seasonal, etc) or a savage roast (or compliment!) with themed responses.

#### 📚 Server Lore System

- **/add_lore** — Save any message or story as part of your server's permanent lore archive.
- **/view_lore**, **/random_lore**, **/lore_stats** — Browse lore entries, pick random stories, and see stats for top contributors.

#### 🤖 Profile & Theme System

- **/profile** — Interactive, multi-tab profile: see your stats, assigned Transformer identity, digital pet, combiner team, and CyberCoin market standing.
- **/spark** — Assign yourself a unique Transformer name, faction, and class, fully integrated with the RPG system.
- **/analysis** — Take a "faction quiz" that assigns you to Autobot, Decepticon, or Maverick based on your answers.

#### 🔗 Combiner Teams & Mega-Fight

- **/combiner** — Form a team of 6 (legs, arms, head, body) to unlock special mega-battles.
- **/mega_fight** — Challenge other teams to multi-round, head-controlled battles with energon rewards.

### 🗂️ Key Random System Modules

- **fun_system.py** — All games, minigames, shooting range, and Hunger Games logic.
- **walktru.py** — Interactive adventure engine, story map manager, progress bars, and adventure logic.
- **themer.py** — Transformer identity assignment, combiner teams, name generation, theme data, and profile utilities.
- **me.py** — Multi-tab interactive profile system (personal stats, pet, combiner, CyberCoin).
- **talk_system.py** — Lore, jokes, blessings, conversational analysis, roasts, and more.

## 🏛️ PnW Recruitment System

The PnW Recruitment System automates and streamlines the process of finding and messaging unallied nations in Politics & War, making mass recruitment and alliance growth efficient, safe, and fully compliant with game rules.

### 🌐 What It Does

- **Fetches up to 15,000 unallied nations** directly from the Politics & War API, sorted by most recent activity
- **Advanced filtering:** Excludes game admin nations (ID=1), nations inactive for 7+ days, vacation mode nations, and those on recruitment cooldown
- **Real-time cooldown tracking:** Prevents messaging nations that have been contacted within 60 hours (PnW rules)
- **Message variety system:** Rotates through 50+ unique recruitment messages to avoid spam detection
- **Comprehensive nation stats:** Nation name, leader, score, cities count, last active date, and recruitment eligibility status

### 🚀 Enhanced Features

#### 📊 Advanced Recruitment Engine
- **Massive scale processing:** Handles up to 15,000 nations per fetch with intelligent pagination
- **Smart cooldown management:** Built-in tracking system prevents rule violations with 60-hour and 60-day cooldowns
- **Dynamic message selection:** Automatically selects appropriate messages based on nation history and availability
- **Rate limit handling:** Respects PnW API limits with intelligent retry logic and user feedback

#### 🎯 Interactive Recruitment Views
- **Paginated nation browser:** View 100 nations across 10 pages (10 nations per page)
- **Rich nation cards:** Each nation displayed with clickable links, activity indicators, and recruitment status
- **Multi-action buttons:**
  - **🎯 Recruit This Page:** Target specific nations on current page
  - **🚀 Mass Recruit All Shown:** Send to all 100 displayed nations with progress tracking
  - **🔄 Refresh:** Re-fetch latest nation data from API
  - **📊 Real-time progress:** Live updates during mass recruitment with success/failure counts

#### 📈 Recruitment Tracking & Analytics
- **Complete message history:** Tracks every recruitment message sent with timestamps and message numbers
- **Nation-based cooldown system:** Uses nation ID as primary identifier for accurate tracking
- **Smart availability detection:** Shows which messages can be sent to each nation based on cooldown status
- **Comprehensive statistics:**
  - Total messages sent and unique nations contacted
  - Nations currently on cooldown
  - Next available recruitment time
  - Recent activity log with leader names and timestamps

#### 🔧 Technical Improvements
- **Asynchronous processing:** Non-blocking API calls prevent bot freezing during large operations
- **Robust error handling:** Handles API timeouts, connection failures, and rate limits gracefully
- **Detailed logging:** Full audit trail of all recruitment activities for compliance and debugging
- **GDPR compliance:** Built-in data cleanup tools for managing user data retention

#### 📋 Usage Commands
- **`/recruit`** - Launch interactive recruitment interface (Aries-only)
- **`/recruitment_stats`** - View detailed recruitment analytics and cooldown information
- **Automatic cooldown enforcement** - Prevents rule violations without user intervention

#### 🛡️ Safety & Compliance Features
- **PnW rules compliance:** Automatically enforces 60-hour cooldown between messages
- **Message uniqueness:** Prevents sending same message to same nation within 60 days
- **API rate limiting:** Respects PnW API limits to prevent bans
- **Error recovery:** Continues processing remaining nations if individual failures occur

## 👑 Admin System

The Admin System is a comprehensive set of tools for bot administrators and owners to manage, monitor, debug, and maintain the AllSpark bot ecosystem. It provides real-time monitoring, activity logging, stress testing, and advanced data/file management tools.

### 🛠️ Major Features

- **System Resource Monitor:**  
  Live dashboard showing bot CPU, RAM, storage, thread/file handles, Discord server/user counts, uptime, and module status. Includes colored progress bars, refresh, stress test, and dismiss buttons.
- **Bot Activity Logging:**  
  Every major admin, mod, or sensitive action is logged (with username, command, and details), viewable as an embed or filtered by user. Logs are stored via the unified UserDataManager.
- **Log Management:**  
  View all recent logs, filter by user, see how many entries in total, and clear logs (with confirmation dialogs). Supports partial and full clears.
- **Stress Testing:**  
  Launch simulated stress tests, spawning fake users and commands to measure bot performance under load. Live stats and progress updates are shown.
- **User Data File Management:**  
  Admins can select and permanently delete user data files—useful for GDPR compliance or purging abandoned/test accounts. Multi-user selection, safety checks, and feedback included.
- **Debug Log Control:**  
  Instantly clear the `bot_debug.log` file from Discord.
- **Slash Command Sync:**  
  Force-resync all bot slash commands with Discord, with instant feedback and a list of synced commands.
- **Uptime and Performance:**  
  Check bot uptime, system RAM/CPU, and storage stats at any time.
- **Error Handling:**  
  All admin commands feature robust error handling, rate limiting, and detailed feedback.

## 🗂️ User Data Manager

The User Data Manager is the core engine for persistent, high-performance, and scalable data storage in AllSpark. It provides a unified interface for saving, loading, updating, and migrating all user, game, and system data.

### 🚀 Key Features

- **Optimized Async I/O:**  
  All read and write operations are asynchronous, non-blocking, and use file-level locks to ensure stability and performance even under heavy loads.
- **Smart Caching & LRU Eviction:**  
  Hot data is kept in memory, with configurable TTL and automatic least-recently-used (LRU) eviction to balance speed and memory efficiency.
- **Automatic Directory & File Management:**  
  Ensures all required directories and JSON files exist, handling upgrades, migrations, and new installs seamlessly.
- **Unified User Data Schema:**  
  Every user has a single data file (`Systems/Users/{user_id}.json`) containing all RPG characters, pet info, minigame stats, economy, slots, cybercoin, achievements, theme/identity, and more.
- **Batch Operations & Migration:**  
  Tools to migrate legacy data, update all pet records, or clean up inactive data in bulk.
- **Advanced Game & Economy Support:**  
  Persistent storage for Energon balances, CyberCoin portfolios, slot/jackpot records, RPG and pet progression, battle logs, event history, achievements, and more.
- **Global & System Data:**  
  Efficient storage and retrieval for global game state, market data, logs, lore, jokes, blessings, templates, and system-wide settings.
- **Validation & Integrity Checks:**  
  Built-in tools to validate file/data integrity, check for negative values, consistency, and auto-heal missing fields.
- **Admin, Logging, & Debug Tools:**  
  Backed by a real-time logging system, performance metrics, and support for admin operations like log viewing, clearing, and user file deletion.

### 📦 What Does It Store?

- **User Profiles:** Discord/user IDs, names, creation/update times.
- **RPG Characters:** Full stats, history, combat, inventory, equipment, and more.
- **Pets:** Pet data (with auto-migration for legacy formats), equipment, inventory, stats.
- **Mini-Game Stats:** Shooting range, slots, missions, mega-fights, leaderboards, achievements.
- **Economy & Currency:** Energon (banked, earned, spent, in-game), CyberCoin market, transactions.
- **Themes & Identities:** Transformer name, faction, class, combiner teams, roles, history.
- **Lore & Social:** Server lore, jokes, blessings, user sayings, and custom templates.
- **Logs:** All admin/mod actions, system events, and user activity.
- **Global Saves:** Game state, global leaderboards, CyberCoin market, admin data.

### 🛠️ Key API Methods (examples)

- `get_user_data(user_id, username)` — Load or create a user's data file.
- `save_user_data(user_id, username, data)` — Save all data for a user.
- `get_rpg_character(user_id, username, name)` — Retrieve a specific RPG character.
- `save_rpg_character(user_id, username, character)` — Save RPG character info.
- `get_pet_data(user_id)` / `save_pet_data(user_id, username, pet_data)` — Manage digital pet storage.
- `get_energon_data(player_id)` / `save_energon_data(player_id, energon_data)` — Game currency management.
- `add_energon(player_id, amount, source)` / `subtract_energon(player_id, amount, source)` — Add or remove currency.
- `get_monsters_and_bosses()` — Load monster/boss/titan data for RPG.
- `get_slot_machine_data(player_id, username)` — Minigame stats.
- `get_theme_system_data(user_id, username)` — Get/set theme, combiner, and identity info.
- `add_bot_log(log_entry)` / `get_bot_logs()` — Logging system.
- `cleanup_inactive_data(days_inactive)` — Batch cleanup for stale users.
- `migrate_all_pet_data()` — Batch migration for legacy pet data.
- ...and many more for leaderboard, validation, admin tools, and system data.

---

## 🗂️ System Components & Cogs

**Every major system and cog is included with full views/UI:**

### `/Systems/EnergonPets/`
- `pets_system.py`, `battle_system.py`, `battle_commands.py`, `pets_commands.py`, `energon_system.py`, `energon_commands.py`, `slots.py`, `enemy_selection_view.py`:  
  *Pet logic, missions, battles, economy, slot machine, equipment, and all battle-related views, joiners, and embeds.*

### `/Systems/RPG/`
- `rpg_system.py`, `rpg_commands.py`, `rpg_battle_system.py`:  
  *RPG character classes, stats, loot, unified battle system, XP, inventory, and all RPG battle-related views.*

### `/Systems/Random/`
- `fun_system.py`, `walktru.py`, `talk_system.py`, `themer.py`, `me.py`:  
  *Mini-games, Hunger Games, shooting range, walk-thru stories, combiner teams, AI dialogue, transformer class assignment, and user profiles.*

### `/Systems/PnW/`
- `recruit.py`:  
  *PnW recruiting, nation lists, views, and paginators.*

### `/Systems/admin_system.py`  
  *Admin and moderation controls, logging, error handling, system monitor, stress tests, and all admin views.*

### `/Systems/user_data_manager.py`  
  *Core user data, XP, loot management, and async file operations.*

### `/Systems/Data/`  
  *JSON data for missions, enemies, loot, classes, story maps, etc.*

### `/Systems/Users/` and `/Systems/Global Saves/`  
  *User profiles, inventories, persistent data.*

---

## 📜 Complete Commands List (70+)

> For the absolute latest, use `/features` or `/help` in your server, or see the code: [GitHub Code Search](https://github.com/The-Infamous-Aries/Allspark/search?q=commands.hybrid_command).

### 🐾 EnergonPets & Economy

#### Pet Management Commands
- `/get_pet` — Adopt your digital pet (choose faction)
- `/pet` — View/manage your pet (interactive dashboard)
- `/rename_pet` — Rename your pet
- `/kill_pet` — Delete your pet forever (confirmation required)
- `/pet_level` — View pet level, experience, and evolution stage
- `/pet_stats` — Detailed pet statistics and progression overview
- `/pet_progression` — View complete leveling roadmap and milestones

#### Pet Care & Actions
- `/charge_pet` — Recharge pet's energy (3 durations)
- `/repair_pet` — Repair pet's maintenance (3 durations)
- `/play` — Play with your pet (3 durations)
- `/train` — Train your pet (3 intensities) [+XP gains]
- `/mission` — Send pet on a mission (choose difficulty) [+XP rewards]
- `/pet_equip` — Equip/view pet items (per slot)
- `/pet_equipment` — Show all pet items (paginated)

#### Battle & PvP Commands
- `/battle` — Start a solo pet battle vs. monster (enemy selection UI) [+XP rewards]
- `/pvp_duel` — Challenge another user to 1v1 PvP pet battle [+XP rewards]
- `/pvp_team` — Organize team battles (2v2, 3v3, 4v4) [+XP rewards]
- `/pvp_lobby` — Create custom PvP lobbies with specific rules [+XP rewards]
- `/group_battle` — Start a group boss battle (4 players) [+XP rewards]
- `/battle_stats` — View detailed battle stats (your pet or others)
- `/battle_history` — Access battle replays and performance analytics

#### Energon Economy Commands
- `/energon_challenge` — Start an energon challenge with a bet
- `/search` — Search for Energon (risk/reward, pet bonuses)
- `/scout` — Low-risk scout for Energon
- `/slots` — Play the Energon slot machine (bet/fun modes)
- `/rush_info` — Info about Energon Rush game
- `/energon_stats` — View Energon economy stats and leaderboards
- `/cybercoin_market` — Trade CyberCoin (interactive market)
- `/cybercoin_profile` — View your CyberCoin portfolio

### 📜 RPG Commands

- `/character_new` — Create a new character (choose name, faction, class)
- `/character_view` — View all your characters and their stats
- `/equip` — Equip or unequip items (weapons, armor, beast modes, etc.)
- `/kill_character` — Delete a character forever (confirmation required)
- `/cyber_info` — Show RPG system help and overview
- `/cyber_random` — Start a group adventure with random events
- `/cyber_battle` — Start a group combat scenario
- `/cyber_event` — Start a group event challenge
- `/cyber_story` — Start a group story-driven session
- `/start_cyberchronicles` — Begin an AI-generated long-form RPG adventure

### 📜 Core Random & Fun Commands List

- `/range` — Shooting range minigame (test your reaction speed)
- `/rangestats` — View your training stats
- `/cybertron_games` — AI-powered Transformers deathmatch with districts & factions
- `/walktru` — Start an interactive adventure (choose genre)
- `/user_says` — Analyze most-used words and "what you'd say"
- `/what_is` — Look up Transformers lore topics
- `/blessing` — Get a blessing from the Allspark
- `/joke` — Get a random joke (multiple categories)
- `/roast` — Get roasted, or roast someone else
- `/compliment` — Get a compliment, or compliment someone else
- `/add_lore` — Add a new lore entry to the server's archive
- `/add_message_to_lore` — Add an existing message to lore
- `/view_lore` — Paginated lore browser
- `/random_lore` — Show a random lore entry
- `/lore_stats` — Lore collection statistics
- `/profile` — Interactive personal profile (stats, pet, combiner, coin)
- `/spark` — Assign a transformer identity to yourself
- `/analysis` — Take the Allspark faction quiz
- `/combiner` — Form or join a combiner team
- `/mega_fight` — Start a mega-battle between combiner teams
- `/hello` — Say hello to the bot (with escalating responses)
- `/ping` — Bot latency (with escalating threats)
- `/grump` — Have fun pinging the "Grump" user

### 📜 Recruitment Commands

- **`/recruit`** — Launch interactive recruitment interface showing up to 100 unallied nations in paginated view (Aries-only)
  - **Advanced pagination:** 10 pages × 10 nations each = 100 nations maximum display
  - **Rich nation cards:** Clickable nation links, activity timestamps, cities count, nation score
  - **Smart filtering:** Only shows nations eligible for recruitment (not on cooldown)
- **`/recruitment_stats`** — View comprehensive recruitment analytics and cooldown information
  - **Message statistics:** Total sent, unique nations contacted, nations on cooldown
  - **Cooldown tracking:** Next available recruitment time, oldest active cooldown
  - **Recent activity log:** Last 10 recruitment attempts with leader names and timestamps

#### 🎯 Interactive Recruitment View Features
- **🎯 Recruit This Page** — Send recruitment messages to all 10 nations on current page
- **🚀 Mass Recruit All Shown** — Send to all 100 displayed nations with live progress updates
- **🔄 Refresh Nations** — Re-fetch latest unallied nations from Politics & War API
- **Real-time progress tracking:** Success/failure counts during mass operations
- **Automatic cooldown enforcement:** Prevents rule violations with built-in tracking

#### 📊 Advanced Features
- **PnW rules compliance:** 60-hour cooldown between messages to same nation
- **Message variety system:** 50+ unique recruitment messages prevent spam detection
- **Rate limit handling:** Respects API limits with intelligent retry logic
- **Comprehensive error handling:** Detailed feedback for API failures and network issues

### 📜 Admin Commands

- `/monitor` — Real-time, paginated dashboard for system resources (RAM, CPU, storage, threads, uptime, Discord stats, and more).
- `/admin_clear` — Select users and delete their data files (supports multi-select and per-user feedback).
- `/logs` — View bot logs (all or filtered by user), see the last 10 entries, and get total log count.
- `/logs_clear` — Clear logs (partial or all, with confirmation dialog).
- `/uptime` — Show bot uptime, RAM/CPU percentage, and more.
- `/clear_debug_log` — Instantly clear the bot’s debug log file.
- `/sync_commands` — Force-sync all slash commands with Discord and see the results.

---

## 🏗️ Architecture & Data

- **Modular:** Every feature is in `/Systems/` as a separate cog/module.
- **All Views Included:** Every interactive battle, pet, RPG, story, market, admin, and combiner view is present and documented.
- **Persistent Data:** User stats, pets, RPG, loot always saved and shared.
- **Async:** Non-blocking for smooth operation.
- **Cross-Server:** Stats and pets travel with users.
- **JSON-based Data:** Easy to back up, migrate, or expand.
- **Admin Logging & Error Handling:** Robust monitoring, error tracking, and log management.

---

## 🔧 Configuration

- Edit `.env` for Discord tokens, API keys, and owner ID.
- System settings, missions, loot, and enemies are all JSON and can be edited/expanded easily.

---

## 📁 File Structure

```
AllSpark/
├── allspark.py
├── README.md
├── requirements.txt
├── .env.example
└── Systems/
    ├── EnergonPets/
    │   ├── pets_system.py
    │   ├── battle_commands.py
    │   ├── pets_commands.py
    │   ├── energon_system.py
    │   ├── energon_commands.py
    │   ├── slots.py
    │   └── PetBattles/
    │       ├── battle_system.py
    │       ├── enemy_selection_view.py
    │       ├── pvp_system.py
    │       ├── pvp_lobby.py
    ├── RPG/
    │   ├── rpg_system.py
    │   ├── rpg_commands.py
    │   ├── rpg_battle_system.py
    ├── Random/
    │   ├── fun_system.py
    │   ├── walktru.py
    │   ├── talk_system.py
    │   ├── themer.py
    │   ├── me.py
    ├── PnW/
    ├── recruit.py
    ├── recruit_views.py
    └── recruitment_tracker.py
    ├── Users/
    ├── Data/
    ├── Global Saves/
    ├── admin_system.py
    ├── user_data_manager.py
```

---

## 🛠️ Development & Support

- **Run:** `python allspark.py`
- **Debug:** `python allspark.py --debug`
- **Issues/Support:** [Join the Support Discord Server](https://discord.gg/pDTKNQJXdh)

---

## 🤝 Contributing

1. Fork and branch
2. Commit & push
3. Open a Pull Request

---

## 📄 License

Distributed under the MIT License.

---

## 🔗 Support

> **Need help, bug reporting, or want to suggest features? [Join the Support Discord Server!](https://discord.gg/pDTKNQJXdh)**
