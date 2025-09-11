# 🌟 The AllSpark

> **The most advanced and complete Transformers-themed Discord bot.**  
> 🚨 **For help, bug reports, or feature requests: [Join the Support Discord Server!](https://discord.gg/pDTKNQJXdh)**

---

## 📋 Table of Contents

- [🚀 Overview](#-overview)
- [✨ Major Features](#-major-features)
  - [🐾 EnergonPets System](#-energonpets-system)
    - [⚔️ Battle System](#️-battle-system)
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
- [📜 Complete Commands List (70+)](#-complete-commands-list-70)
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
- [📄 License](#-license)
- [🔗 Support](#-support)

---

## 🚀 Overview

AllSpark is a modular, feature-rich Discord bot that brings the Transformers universe to life through interactive digital pets, RPG battles, interactive stories, games, recruiting, a full cyber-economy, and much more.  
**Every system, view, and cog is documented here.**

---

# ✨ Major Features

## 🐾 EnergonPets System

- **Adopt and raise a digital Transformer pet** (Autobot or Decepticon) with unique attributes, evolution stages, and persistent stats.
- **Pet management** includes Energy, Happiness, Maintenance, Equipment, and a massive progression ladder up to level 100.
- **Actions:** Charge, Play, Repair, Train, Rename, and send on Missions. Each action affects stats and unlocks new rewards.
- **Loot & Equipment:** Earn, equip, and collect 100+ unique items (Chassis Plating, Energy Cores, Utility Modules) across 6 rarity tiers.
- **Persistent growth:** All progress, stats, and inventory are saved across servers.

### ⚔️ Battle System

- **Turn-based d20 combat**: Classic RPG-style battles with rich mechanics, critical hits, group defense, and parry systems.
- **Battle types:** Solo (vs monsters), Group (up to 4 vs bosses/titans), PvP, Group PvP, Free-For-All, and Energon Challenges (betting battles).
- **Dynamic enemies:** 100+ monsters, bosses, and titans, each with unique stats, types, and rarities.
- **Rewards:** Earn Energon, XP, loot, and leaderboard glory from battles.
- **Full UI:** Interactive Discord views for joining, action selection, and real-time combat updates.

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

#### 🏹 Hunger Games Sorter

- **/hg_sorter** — Randomly sorts users into Hunger Games districts for custom games.
- Filter by bots, Cybertron citizens, or everyone. Output includes `/hungergames add` commands for each tribute.

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

The PnW Recruitment System automates and streamlines the process of finding and messaging unallied nations in Politics & War, making mass recruitment and alliance growth efficient and safe.

### 🌐 What It Does

- **Fetches all unallied nations** (up to 15,000 at a time) directly from the Politics & War API, sorted by most recent activity.
- **Filters out** game admin nations, nations inactive for 7+ days, and those in vacation mode.
- **Displays comprehensive stats:** nation name, leader, score, activity, cities, and more.
- **Supports mass or targeted messaging** with customizable recruitment messages, including links to Discord and alliance application.

### 🛠️ Major Features

- **Paged, interactive navigation:** Browse unallied nations 5 at a time, with "Previous" and "Next" buttons.
- **Recruitment buttons:**
  - **Refresh:** Instantly re-fetches the latest nation data.
  - **Recruit All Shown:** Sends recruitment messages to all nations on the current page.
  - **Mass Recruit ALL:** Sends to every nation in the list (rate-limited, with progress updates).
  - **Close:** Ends the session and cleans up the UI.
- **Smart error handling:** Handles API errors, rate limits, and provides user feedback at every step.
- **Activity indicators:** Color-coded icons (🟢 just now, 🟡 recent, 🟠 older, 🔴 inactive) and "time ago" for each nation.
- **Recruitment messages:** Professionally formatted, themed, and customizable; always includes your Discord and alliance links.

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

- `/get_pet` — Adopt your digital pet (choose faction)
- `/pet` — View/manage your pet (interactive dashboard)
- `/rename_pet` — Rename your pet
- `/kill` — Delete your pet forever (confirmation required)
- `/charge_pet` — Recharge pet's energy (3 durations)
- `/repair_pet` — Repair pet's maintenance (3 durations)
- `/play` — Play with your pet (3 durations)
- `/train` — Train your pet (3 intensities)
- `/mission` — Send pet on a mission (choose difficulty)
- `/pet_equip` — Equip/view pet items (per slot)
- `/pet_equipment` — Show all pet items (paginated)
- `/battle` — Start a solo pet battle vs. monster (enemy selection UI)
- `/battle_info` — Show comprehensive battle rules & info
- `/group_battle` — Start a group boss battle (4 players)
- `/group_pvp` — Start a group PvP battle (4 players)
- `/pvp` — Challenge another user to PvP pet battle
- `/ffa_battle` — Four-way free-for-all battle
- `/battle_stats` — View detailed battle stats (your pet or others)
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
- `/hg_sorter` — Randomly assign users to Hunger Games districts
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

- `/recruit` — Shows the full, paginated list of unallied nations, sorted by most recent activity (restricted to Aries only).
- **Recruit View Buttons** (within the embed):
  - **Previous/Next** — Navigate through the nation list, 5 at a time.
  - **🔄 Refresh** — Reload nation data from the API.
  - **Recruit All Shown** — Send the recruitment message to every nation on the current page.
  - **🎯 Mass Recruit ALL** — Send to every nation; includes live progress and rate limiting.
  - **Close** — Exit and clean up the view.

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
    │   ├── battle_system.py
    │   ├── battle_commands.py
    │   ├── pets_commands.py
    │   ├── energon_system.py
    │   ├── energon_commands.py
    │   ├── slots.py
    │   └── enemy_selection_view.py
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
    │   └── recruit.py
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
