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

- **100-level pet progression:** Nano Core → Nano Supreme (XP: 50 → 6.32B).
- **Factions:** Autobot or Decepticon, each with unique bonuses and UI.
- **Missions:** Over **150+** unique pet missions (50 easy, 50 average, 50 hard).
- **Battles:** Turn-based d20, supports:
  - Solo, Group (4v1), PvP, FFA, Group PvP, Energon Challenge.
- **Enemies:** 100+ unique monsters, bosses, titans.
- **Loot:** 100+ lootable Chassis Plating, Energy Cores and Utility Modules (6 rarity tiers).
- **Resource Management:** Energy, Maintenance, Happiness, Equipment.
- **Economy:** Energon mining, cross-server games, market events, persistent banking, slots.
- **Pet Boosts:** Up to 200% bonus at max level for Energon searching.

### ⚔️ RPG System

- **8 classes per faction** with unique stats.
- **Stats:** ATT, DEF, DEX, INT, CHA, HP.
- **Loot:** 30+ RPG weapons/artifacts/relics.
- **Progression:** Unified with EnergonPets.
- **Enemies:** 100+ unique monsters, bosses, titans.
- **Loot:** 200+ lootable weapons, armors, transformations, beast modes (6 rarity tiers).

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

### ⚔️ RPG & Theme

- `/me` or `/profile` — View your RPG profile and stats, inventory, combiner status, CyberCoin (full UI)
- `/class` — Choose your RPG class
- `/equip` — Equip RPG loot
- `/character_new` — Create new RPG character
- `/character_view` — View RPG character(s)
- `/cyber_random` — Start random group adventure
- `/cyber_battle` — Start group battle adventure
- `/cyber_event` — Start group event challenge
- `/cyber_story` — Start group story adventure
- `/spark` — Assign yourself a Transformer identity
- `/combiner` — Start/join a Combiner team (UI view)
- `/analysis` — Run advanced analysis to determine your class
- `/what_is` — Look up Transformers lore topic

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
