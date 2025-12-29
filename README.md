# 🍥 Anime Master Bot

![Version](https://img.shields.io/badge/Version-9.1-blue?style=for-the-badge&logo=python)
![License](https://img.shields.io/badge/License-PSBDx_Open_Source-red?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Online-success?style=for-the-badge)

> **"I'm not gonna run away, I never go back on my word! That's my nindō: my ninja way!"** 🍥

**Anime Master** is a powerful, open-source Discord bot built for anime enthusiasts. It aggregates data from multiple sources to provide accurate ratings, streaming info, and studio details. Uniquely, it features **automatic Bangla translation** for anime descriptions, making it perfect for the BD community! 🇧🇩

---

## ✨ Key Features

| Feature | Description |
| :--- | :--- |
| **🔎 Smart Search** | Fetches data from **MyAnimeList** via Jikan API. |
| **📊 Multi-Ratings** | Compares scores from **MAL**, **AniList**, **Kitsu**, and **IMDb**. |
| **🇧🇩 Auto-Translate** | Automatically translates anime synopses into **Bangla**. |
| **📺 Streaming** | Detects legal streaming links (Netflix/Crunchyroll). |
| **🔒 Admin Lock** | Restrict the bot to specific channels to prevent spam. |
| **🛡️ Protected Core** | Includes an encrypted `/about` command to protect developer credits. |

---

## 🛠️ Installation & Setup

Follow these steps to host the bot on your own machine or server.

### 1. Clone the Repository
```bash
git clone [https://github.com/psbdx-pvt-ltd/Anime-Master-bot.git](https://github.com/psbdx-pvt-ltd/Anime-Master-bot.git)
cd Anime-Master-bot
```

### 2. Install Dependencies
Ensure you have Python 3.8+ installed.
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a file named `.env` in the root directory and add the following keys. **Do not share this file!**

```env
# Required
BOT_TOKEN=your_discord_bot_token_here

# Optional (Admin Configuration)
ADMN_ID=your_discord_user_id
PORT=5000
```

### 4. Run the Bot
```bash
python bot.py
```

---

## ☁️ Deployment (Online Hosting)

This bot includes a built-in Flask server (`keep_alive`), making it compatible with cloud platforms.

### ⚡ Option 1: Render / Railway (Recommended)
1.  Fork this repo to your GitHub.
2.  Create a new Web Service on **Render** or **Railway**.
3.  Connect your repository.
4.  In the **Environment Variables** section of the dashboard, add your `BOT_TOKEN` and `ADMN_ID`.
5.  Deploy! The bot will run 24/7.

---

## 🤖 Command List

### Public Commands
* `/find [anime_name]` - Search for an anime (e.g., `/find Naruto`).
* `/start` - Get the welcome message and instructions.
* `/sources` - View the APIs used for data fetching.
* `/about` - View Developer and License info (**Protected**).

### Admin Commands (Owner Only)
* `/set_channel` - Lock the bot to reply *only* in the current channel.
* `/unlock_all` - Allow the bot to reply in all channels.
* `!check sys` - View server time (BD Time) and latency.
* `!check sources` - Test the connection to MAL, AniList, and Google Translate.

---

## ⚖️ License & Rights

**Developer:** PSBDx  
**License Type:** PSBDx Open Source License

This project is Open Source, allowing you to modify functionality, commands, and hosting methods. However, **Strict Restrictions** apply to the core attribution:

> ⚠️ **Warning:** Users are **strictly prohibited** from modifying, decrypting, or bypassing the `_decrypt_about_data` function or the encrypted credit payloads within `bot.py`. The `/about` command must remain intact to preserve developer credit.

---

<p align="center">
  Made with 🦊 by <a href="https://github.com/psbdx-pvt-ltd">PSBDx</a>
</p>
