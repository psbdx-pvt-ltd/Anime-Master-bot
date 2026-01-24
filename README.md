# Anime Master Bot

![Version](https://img.shields.io/badge/Version-9.3-blue?style=for-the-badge&logo=python)
![License](https://img.shields.io/badge/License-PSBDx_Open_Source-red?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Online-success?style=for-the-badge)
[![Documentation](https://img.shields.io/badge/Documentation-Check_For_More-blueviolet?style=for-the-badge)](https://documentations.psbdx.rf.gd/v9_3)

**Anime Master** is a comprehensive, open-source Discord bot designed for media aggregation. It retrieves detailed data from multiple authoritative sources to provide accurate ratings, streaming availability, and studio information.

**Version 9.3 Update:** This release introduces **Dynamic Storage**! The bot can now automatically switch between Local Storage (File) and Cloud Storage (Discord Channel) based on your environment variables.

---

## ✨ Key Features

| Feature | Description |
| :--- | :--- |
| **🔎 Smart Search** | Retrieves data from **MyAnimeList** via the Jikan API. |
| **🍂 Seasonal Logic** | Supports specific season queries (e.g., "Season 2") for precise results. |
| **💾 Dynamic Storage** | **New:** Automatically switches between Discord DB and Local File storage. |
| **📊 Multi-Source Ratings** | Aggregates and compares scores from **MAL**, **AniList**, **Kitsu**, and **IMDb**. |
| **🌐 Configurable Translation** | Translates synopses into a target language configured in the source code (Default: Bangla). |
| **📺 Streaming Availability** | Detects and provides legal streaming links for Netflix and Crunchyroll. |
| **🔒 Administration** | Includes channel locking mechanisms to manage bot activity. |
| **📖 Transparent Core** | Fully open-source codebase with transparent attribution logic. |

---

## 🛠️ Installation & Configuration

Follow these steps to deploy the bot on a local machine or server.

### 1. Environment Variables

Set these in your `.env` file or your host's environment configuration.

| Variable | Required? | Description |
| :--- | :--- | :--- |
| `BOT_TOKEN` | **Yes** | Your Discord Bot Token. |
| `ADMN_ID` | **Yes** | Your Discord User ID (allows access to admin commands). |
| `DSCRD_DB` | **Optional** | A Discord Channel ID. **If set, the bot enables Discord DB mode.** |

### 2. Dynamic Storage Guide (New in v9.3)

The bot now features a smart switch for storage.

**Option A: Cloud Mode (Recommended for Heroku/Render)**
If you are hosting on a platform that wipes files when the bot restarts, use this mode.
1. Create a private channel in your server (e.g., `#bot-database`).
2. Copy the Channel ID.
3. Add `DSCRD_DB` to your environment variables and paste the ID.
4. **Result:** The bot will automatically check this channel for `backup_xxxx.json` files on restart and load your settings.

**Option B: Local Mode (Default)**
If you are hosting on a VPS or your own PC.
1. Do **NOT** add the `DSCRD_DB` variable.
2. **Result:** The bot will save data to a local `data.json` file in the bot's folder.

### 3. Admin Commands

| Command | Description |
| :--- | :--- |
| `/set_channel` | Locks the bot to the current channel. |
| `/unlock_all` | Allows the bot to reply in all channels. |
| `/upload` or `/backup` | **(New)** Manually saves current data to the storage (DB or Local). |
| `!check sys` | Displays system status, including the current Storage Mode. |

### 4. Clone the Repository
```bash
git clone [https://github.com/psbdx-pvt-ltd/Anime-Master-bot.git](https://github.com/psbdx-pvt-ltd/Anime-Master-bot.git)
cd Anime-Master-bot
pip install -r requirements.txt
python bot.py
