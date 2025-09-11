# 🌟 AllSpark Discord Bot

> **The most advanced and complete Transformers-themed Discord bot.**  
> 🚨 **For help, bug reports, or feature requests: [Join the Support Discord Server!](https://discord.gg/pDTKNQJXdh)**

---

## 📋 Table of Contents

- [🚀 Overview](#🚀-overview)
- [✨ Major Features](#✨-major-features)
- [🗂️ System Components & Cogs](#🗂️-system-components--cogs)
- [📜 Complete Commands List (70+)](#📜-complete-commands-list-70)
- [🏗️ Architecture & Data](#🏗️-architecture--data)
- [🔧 Configuration](#🔧-configuration)
- [📁 File Structure](#📁-file-structure)
- [🛠️ Development & Support](#🛠️-development--support)
- [🤝 Contributing](#🤝-contributing)
- [📄 License](#📄-license)

---

## 🚀 Overview

AllSpark is a modular, feature-rich Discord bot that brings the Transformers universe to life through interactive digital pets, RPG battles, interactive stories, games, recruiting, a full cyber-economy, and advanced admin tools. All systems are interconnected, use persistent user data, and support cross-server play.  
**Every system, view, and cog is documented here.**

---

## ✨ Major Features

### 🐾 EnergonPets System

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

### 🤖 Random System

- **Mini-Games:** Shooting Range, Hunger Games Sorter, Mega-Fight (6v6).
- **RPG Stories:** 6 genres (Horror, Western, Gangster, Knight, Robot, Wizard).
- **Conversational AI:** Keyword-extraction, jokes, and dialogue.
- **Combiner Teams:** Become part of a combiner team for mega-battles.

### 🏛️ PnW Recruitment

- **API Integration:** Recruits from Politics & War.
- **Auto-Filtering:** Excludes ineligible nations, customizes messages, prevents API abuse.

### 👑 Admin System

- **Admin Controls:** Permissions, roles, configuration, moderation, event automation.
- **Debug/Logging:** Enable for troubleshooting.
- **Custom Settings:** Change limits/rules/features live.

### 🛡️ User Data

- **Persistent Profiles:** Stats, inventories, and achievements across all systems.
- **Data Manager:** JSON-based, robust, and easily backed up.

---

## 🗂️ System Components & Cogs

**Every major system and cog is included with full views/UI:**

### `/Systems/EnergonPets/`
- `pets_system.py`, `battle_system.py`, `battle_commands.py`, `pets_commands.py`, `energon_system.py`, `energon_commands.py`, `slots.py`, and more:  
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

### 🤖 Random & Fun

- `/walktru` — Start an interactive adventure (pick genre)
- `/hg_sorter` — Hunger Games team sorter (choose filters)
- `/range` — Shooting range mini-game (reaction-based)
- `/mega_fight` — Start/join a 6v6 mega battle (UI)
- `/random_lore` — Get a random lore entry
- `/lore_stats` — View lore collection stats

### 🏛️ PnW & Recruitment

- `/recruit` — View unallied nations for recruitment (admin only)

### 👑 Admin & Utility

- `/admin` — Admin/moderator dashboard (UI & commands)
- `/monitor` — View system monitor (CPU/mem stats)
- `/logs` — View admin logs
- `/logs_clear` — Clear admin logs (with confirmation)
- `/uptime` — View bot uptime and system info
- `/clear_debug_log` — Clear debug log (admin only)
- `/sync_commands` — Sync all slash commands (admin only)
- `/features` — List all bot commands and features
- `/debug` — Show debug info (owner only)
- `/test_error` — (Owner only, test error handling)

> ℹ️ *There are more context, sub, and modal commands (e.g., `/equip`, `/item`, `/equipment_type`, `/character_autocomplete`, etc.).  
For the full list, use `/features`, `/help`, or the GitHub code search.*

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

MIT License. See LICENSE for details.

---

> 🔗 **Need help, bug reporting, or want to suggest features? [Join the Support Discord Server!](https://discord.gg/pDTKNQJXdh)**
