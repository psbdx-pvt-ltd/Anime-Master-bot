import os
import logging
import requests
import threading
import time
import base64
import json
import io 
from datetime import datetime
import pytz 
from flask import Flask
import discord
from discord import app_commands
from discord.ext import commands
from imdb import Cinemagoer
from deep_translator import GoogleTranslator

# --- CONFIGURATION ---
# Load secrets from Environment Variables
TOKEN = os.getenv("BOT_TOKEN")

try:
    ADMN_ID = int(os.getenv("ADMN_ID", "0").strip())
except ValueError:
    ADMN_ID = 0

PORT = int(os.environ.get('PORT', 5000))

# --- LANGUAGE SETTINGS ---
# Change this code to set the bot's translation language.
# Examples: 'bn' (Bangla), 'en' (English), 'es' (Spanish), 'ja' (Japanese)
CURRENT_LANGUAGE = "bn" 

# --- DYNAMIC STORAGE CONFIGURATION ---
# This is the "switch". If DSCRD_DB env var exists, use Discord DB. If not, use Local.
DSCRD_DB_ID = os.getenv("DSCRD_DB")
USE_DISCORD_DB = True if DSCRD_DB_ID else False

# Configure Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- GLOBAL STATE ---
# We store state here now instead of just loose variables
BOT_DATA = {
    "locked_channel_id": None
}

# --- PROTECTION ALGORITHM (MODIFIED) ---
def _get_about_data():
    """
    Returns the developer and version info.
    Now un-encrypted for Version 9.3.
    """
    return {
        "Version Code": "9.3",
        "Version type": "Open Source (Custom)",
        "Developer Name": "PSBDx",
        "User License Type": "Open Source",
        "Open Source Comment": "Dynamic Storage Enabled."
    }

# --- FLASK SERVER (Keep Alive) ---
app = Flask(__name__)

@app.route('/')
def home():
    storage_mode = "Discord Cloud DB" if USE_DISCORD_DB else "Local Server Storage"
    return f"Anime Master Bot v9.3 is Running! ({CURRENT_LANGUAGE.upper()} Mode) | Storage: {storage_mode}"

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

# --- HELPER FUNCTIONS ---

def get_ping(url):
    """Checks connection speed to external APIs"""
    start_time = time.time()
    try:
        requests.get(url, timeout=5)
        latency = (time.time() - start_time) * 1000 
        return f"{int(latency)}ms", True, "OK"
    except Exception as e:
        return "N/A", False, str(e)

def translate_text(text):
    """Translates text to the configured CURRENT_LANGUAGE"""
    if not text: return "No description available."
    
    # If target is English and text is already likely English, skip (simple check)
    if CURRENT_LANGUAGE == 'en':
        return text

    try:
        short_text = (text[:400] + '...') if len(text) > 400 else text
        return GoogleTranslator(source='auto', target=CURRENT_LANGUAGE).translate(short_text)
    except:
        return text

# --- DATA FETCHING FUNCTIONS ---

def get_mal_full_data(name, season=None):
    """
    Fetches detailed anime data from MyAnimeList via Jikan API.
    Now supports an optional 'season' parameter.
    """
    search_query = f"{name} {season}" if season else name
    try:
        r = requests.get(f"https://api.jikan.moe/v4/anime?q={search_query}&limit=1", timeout=5)
        if r.status_code == 200 and r.json()['data']:
            item = r.json()['data'][0]
            
            # Extract Genres
            genres_list = [g['name'] for g in item.get('genres', [])]
            genres_str = ", ".join(genres_list) if genres_list else "N/A"

            # Extract Studios
            studios_list = [s['name'] for s in item.get('studios', [])]
            studios_str = ", ".join(studios_list) if studios_list else "N/A"

            return {
                'mal_id': item.get('mal_id'),
                'title': item.get('title_english') or item.get('title'),
                'score': item.get('score'),
                'episodes': item.get('episodes'),
                'synopsis': item.get('synopsis'),
                'image_url': item['images']['jpg']['large_image_url'],
                'url': item.get('url'),
                'type': item.get('type', 'TV'),
                'status': item.get('status', 'Finished'),
                'genres': genres_str,
                'studios': studios_str
            }
    except: pass
    return None

def get_streaming_links(mal_id):
    """Fetches streaming links (Netflix/Crunchyroll)"""
    if not mal_id: return "N/A", "N/A"
    n, c = "N/A", "N/A"
    try:
        r = requests.get(f"https://api.jikan.moe/v4/anime/{mal_id}/streaming", timeout=5)
        if r.status_code == 200:
            for site in r.json().get('data', []):
                name = site.get('name', '').lower()
                if 'netflix' in name: n = site.get('url')
                elif 'crunchyroll' in name: c = site.get('url')
    except: pass
    return n, c

def get_score_generic(url, json_data, key_path):
    """Helper to fetch scores from AniList and Kitsu"""
    try:
        if json_data:
            r = requests.post(url, json=json_data, timeout=5)
        else:
            r = requests.get(url, timeout=5)
        
        if r.status_code == 200:
            data = r.json()
            for k in key_path:
                data = data[k]
            return data
    except: pass
    return None

# --- STORAGE LOGIC (NEW) ---

async def load_data(bot_instance):
    """
    Loads data from Discord Channel or Local File based on USE_DISCORD_DB flag.
    """
    global BOT_DATA
    
    # 1. DISCORD DB MODE
    if USE_DISCORD_DB:
        try:
            channel = bot_instance.get_channel(int(DSCRD_DB_ID))
            if not channel:
                logger.error(f"❌ Error: DSCRD_DB channel ID {DSCRD_DB_ID} not found or bot lacks access.")
                return

            # Check history for latest file
            found_data = False
            async for message in channel.history(limit=1):
                if message.attachments:
                    for att in message.attachments:
                        if att.filename.endswith('.json'):
                            file_data = await att.read()
                            BOT_DATA = json.loads(file_data.decode('utf-8'))
                            logger.info("✅ successfully connected with discord db")
                            found_data = True
                            break
                if found_data: break
            
            if not found_data:
                logger.info("ℹ️ Connected to Discord DB (No previous JSON file found, starting fresh).")
        except Exception as e:
            logger.error(f"❌ Failed to load from Discord DB: {str(e)}")

    # 2. LOCAL FILE MODE
    else:
        try:
            if os.path.exists("data.json"):
                with open("data.json", "r") as f:
                    BOT_DATA = json.load(f)
                logger.info("✅ Loaded data from local server file.")
            else:
                logger.info("ℹ️ No local data file found. Starting fresh.")
        except Exception as e:
            logger.error(f"❌ Failed to load local data: {str(e)}")

async def save_data(interaction=None):
    """
    Saves data to Discord Channel or Local File based on USE_DISCORD_DB flag.
    """
    global BOT_DATA
    
    # Prepare JSON
    json_str = json.dumps(BOT_DATA, indent=4)
    
    # 1. DISCORD DB MODE
    if USE_DISCORD_DB:
        try:
            channel = bot.get_channel(int(DSCRD_DB_ID))
            if channel:
                # Create in-memory file
                file_obj = io.BytesIO(json_str.encode('utf-8'))
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                file_name = f"backup_{int(time.time())}.json"
                
                await channel.send(
                    content=f"💾 **Auto-Backup** | {timestamp}",
                    file=discord.File(file_obj, filename=file_name)
                )
                if interaction:
                    await interaction.response.send_message(f"✅ **Success!** Data uploaded to Discord DB <#{DSCRD_DB_ID}>.")
                logger.info("✅ Data saved to Discord DB.")
            else:
                if interaction:
                     await interaction.response.send_message("❌ Error: Could not find DB Channel.")
        except Exception as e:
            logger.error(f"❌ Error saving to Discord DB: {e}")
            if interaction:
                await interaction.response.send_message(f"❌ Save Failed: {e}")

    # 2. LOCAL FILE MODE
    else:
        try:
            with open("data.json", "w") as f:
                f.write(json_str)
            logger.info("✅ Data saved locally.")
            if interaction:
                await interaction.response.send_message("✅ **Success!** Data saved to local server file.")
        except Exception as e:
            logger.error(f"❌ Error saving locally: {e}")
            if interaction:
                await interaction.response.send_message(f"❌ Local Save Failed: {e}")

# --- BOT CLASS & SETUP ---

class AnimeMasterBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Slash commands synced!")

bot = AnimeMasterBot()

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
    
    # --- LOAD DATA ON RESTART ---
    await load_data(bot)
    
    # Updated status to show the language in the status
    await bot.change_presence(activity=discord.Game(name=f"/find [anime] | {CURRENT_LANGUAGE.upper()}"))

# --- ADMIN COMMANDS ---

@bot.tree.command(name="backup", description="Admin: Upload/Save current bot data manually")
async def backup_slash(interaction: discord.Interaction):
    if interaction.user.id != ADMN_ID:
        await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
        return

    # Trigger save
    await save_data(interaction)

@bot.tree.command(name="set_channel", description="Admin: Lock the bot to ONLY reply in this current channel.")
async def set_channel_slash(interaction: discord.Interaction):
    if interaction.user.id != ADMN_ID:
        await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
        return

    global BOT_DATA
    BOT_DATA["locked_channel_id"] = interaction.channel_id
    
    await interaction.response.send_message(f"🔒 **Locked!** I will now only reply in <#{BOT_DATA['locked_channel_id']}>.")

@bot.tree.command(name="unlock_all", description="Admin: Allow the bot to reply in ALL channels.")
async def unlock_all_slash(interaction: discord.Interaction):
    if interaction.user.id != ADMN_ID:
        await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
        return

    global BOT_DATA
    BOT_DATA["locked_channel_id"] = None
    
    await interaction.response.send_message("🔓 **Unlocked!** I will now reply in all channels.")

# --- PUBLIC SLASH COMMANDS ---

@bot.tree.command(name="about", description="View developer and license information")
async def about_slash(interaction: discord.Interaction):
    cid = BOT_DATA.get("locked_channel_id")
    if cid and interaction.channel_id != cid:
        await interaction.response.send_message(f"⚠️ I am restricted to <#{cid}>.", ephemeral=True)
        return

    # Get plain data
    data = _get_about_data()
    
    embed = discord.Embed(
        title="🤖 About Anime Master",
        description="Core details and license information.",
        color=0x2b2d31 # Dark embed color
    )
    
    # Dynamically add fields
    for key, value in data.items():
        if key == "Open Source Comment":
            embed.add_field(name="⚖️ Note", value=f"*{value}*", inline=False)
        else:
            embed.add_field(name=key, value=f"`{value}`", inline=True)
            
    embed.set_footer(text="Verified Open Source Build | Version 9.3")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="start", description="Get welcome info and help")
async def start_slash(interaction: discord.Interaction):
    cid = BOT_DATA.get("locked_channel_id")
    if cid and interaction.channel_id != cid:
        await interaction.response.send_message(f"⚠️ I am restricted to <#{cid}>.", ephemeral=True)
        return

    user_name = interaction.user.name
    
    # Show user which storage is active
    storage_status = "☁️ Discord DB" if USE_DISCORD_DB else "📁 Local File"

    msg = (
        f"👋 Hello **{user_name}**! 🍥\n"
        f"I am your Anime Assistant.\n\n"
        f"✅ **Usage:** Type `/find` followed by an anime name.\n"
        f"✨ **Season:** You can add a specific season in the search (e.g., 'Season 2')!\n"
        f"🌐 **Language:** Currently set to **{CURRENT_LANGUAGE.upper()}**.\n"
        f"💾 **Storage:** {storage_status}\n"
        f"I will fetch ratings, studio info, genres, and translate the description."
    )
    await interaction.response.send_message(msg)

@bot.tree.command(name="sources", description="See which websites I use for data")
async def sources_slash(interaction: discord.Interaction):
    cid = BOT_DATA.get("locked_channel_id")
    if cid and interaction.channel_id != cid:
        await interaction.response.send_message(f"⚠️ I am restricted to <#{cid}>.", ephemeral=True)
        return

    embed = discord.Embed(
        title="📚 Data Sources Used",
        description=(
            "🔹 **MyAnimeList** (Jikan API)\n"
            "🔹 **AniList** (GraphQL)\n"
            "🔹 **Kitsu** (API)\n"
            "🔹 **IMDb** (Cinemagoer)\n"
            f"🔹 **Translation:** Google Translate ({CURRENT_LANGUAGE})"
        ),
        color=0x3498db
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="find", description="Search for an anime, get info, ratings & translated description")
@app_commands.describe(anime_name="The name of the anime", season="Optional: The specific season (e.g., 'Season 2')")
async def find_slash(interaction: discord.Interaction, anime_name: str, season: str = None):
    # 1. CHECK LOCK
    cid = BOT_DATA.get("locked_channel_id")
    if cid and interaction.channel_id != cid:
        await interaction.response.send_message(f"❌ Please use this command in <#{cid}>!", ephemeral=True)
        return

    # 2. DEFER
    await interaction.response.defer()

    # 3. FETCH DATA
    mal = get_mal_full_data(anime_name, season)
    
    if not mal:
        await interaction.followup.send("❌ Anime not found. Please check the spelling or season.")
        return

    # Fetch extra data
    search_title = mal['title']
    
    # AniList
    ani_q = 'query ($s: String) { Media (search: $s, type: ANIME) { averageScore } }'
    ani_score = get_score_generic('https://graphql.anilist.co', {'query': ani_q, 'variables': {'s': search_title}}, ['data', 'Media', 'averageScore'])
    
    # Kitsu
    kitsu_score = get_score_generic(f"https://kitsu.io/api/edge/anime?filter[text]={search_title}&page[limit]=1", None, ['data', 0, 'attributes', 'averageRating'])
    
    # IMDb
    imdb_score = None
    try:
        ia = Cinemagoer()
        res = ia.search_movie(search_title)
        if res: imdb_score = ia.get_movie(res[0].movieID).get('rating')
    except: pass

    # Streaming & Translate
    net, cru = get_streaming_links(mal['mal_id'])
    desc_translated = translate_text(mal['synopsis'])

    # 4. CALCULATE SCORES
    scores = []
    if mal['score']: scores.append(mal['score'])
    if ani_score: scores.append(ani_score/10)
    if kitsu_score: scores.append(float(kitsu_score)/10)
    if imdb_score: scores.append(float(imdb_score))
    
    avg_score = round(sum(scores)/len(scores), 1) if scores else 'N/A'

    # 5. BUILD EMBED
    embed = discord.Embed(
        title=f"🎬 {mal['title']}",
        description=f"**Description ({CURRENT_LANGUAGE.upper()}):**\n{desc_translated}",
        color=0xe67e22
    )
    
    embed.set_thumbnail(url=mal['image_url'])

    # -- Row 1: Basic Stats --
    embed.add_field(name="📌 Type", value=mal.get('type', 'N/A'), inline=True)
    embed.add_field(name="📺 Episodes", value=str(mal.get('episodes', 'N/A')), inline=True)
    embed.add_field(name="📡 Status", value=mal.get('status', 'N/A'), inline=True)

    # -- Row 2: Info --
    embed.add_field(name="🎭 Genres", value=mal.get('genres', 'N/A'), inline=False)
    embed.add_field(name="🏢 Studios", value=mal.get('studios', 'N/A'), inline=True)
    embed.add_field(name="🏆 Overall Rating", value=f"**{avg_score}⭐**", inline=True)
    
    # -- Row 3: Detailed Ratings --
    def sc(val): return f"{val}⭐" if val else "N/A"
    
    ratings_text = (
        f"**AniList:** {sc(ani_score/10 if ani_score else None)} | "
        f"**MAL:** {sc(mal['score'])}\n"
        f"**Kitsu:** {sc(float(kitsu_score)/10 if kitsu_score else None)} | "
        f"**IMDb:** {sc(imdb_score)}"
    )
    embed.add_field(name="📊 Detailed Ratings", value=ratings_text, inline=False)

    # -- Row 4: Links --
    def lnk(u, t): return f"[{t}]({u})" if u != "N/A" else "N/A"
    links_text = f"🔴 **Netflix:** {lnk(net, 'Watch')} | 🟠 **Crunchyroll:** {lnk(cru, 'Watch')}"
    embed.add_field(name="🔗 Streaming Links", value=links_text, inline=False)

    # 6. SEND RESULT
    await interaction.followup.send(embed=embed)

# --- SYSTEM COMMANDS ---

@bot.command(name='check')
async def check_command(ctx, cmd: str = None):
    if ctx.author.id != ADMN_ID: return 

    if not cmd:
        await ctx.send("⚠️ Use: `!check sys` or `!check sources`")
        return

    cmd = cmd.lower()

    if cmd in ['sources', 'source']:
        msg = await ctx.send("🕵️ **Checking Sources...**")
        targets = [
            ("MyAnimeList (Jikan)", "https://api.jikan.moe/v4"),
            ("AniList API", "https://graphql.anilist.co"),
            ("Kitsu API", "https://kitsu.io/api/edge"),
            ("Google Translate", "https://translate.google.com")
        ]
        report = "**📡 Source Connection Report**\n\n"
        for name, url in targets:
            ping, status, err = get_ping(url)
            icon = "✅" if status else "❌"
            status_text = "OK" if status else f"Error: {err}"
            report += f"{icon} **{name}**\n   └ Ping: {ping} | Status: {status_text}\n"
        await msg.edit(content=report)

    elif cmd in ['sys', 'system']:
        msg = await ctx.send("🖥️ **Checking System...**")
        try:
            bd_tz = pytz.timezone('Asia/Dhaka')
            now_bd = datetime.now(bd_tz).strftime("%I:%M %p")
        except:
            now_bd = "Timezone Error"
        
        discord_ping = f"{int(bot.latency * 1000)}ms"
        
        cid = BOT_DATA.get("locked_channel_id")
        lock_status = f"<#{cid}>" if cid else "Unlocked (All Channels)"
        
        # New Storage Status
        storage_status = f"☁️ Discord DB <#{DSCRD_DB_ID}>" if USE_DISCORD_DB else "📁 Local File"

        sys_report = (
            "**⚙️ System Status**\n"
            "-----------------------------\n"
            f"🕒 **Server Time (BD):** {now_bd}\n"
            f"🤖 **Bot Status:** ✅ Online\n"
            f"🔒 **Restrictions:** {lock_status}\n"
            f"💾 **Storage:** {storage_status}\n"
            f"📶 **API Latency:** {discord_ping}\n"
            f"🌐 **Language:** {CURRENT_LANGUAGE.upper()}\n"
            "-----------------------------\n"
            "✅ **All Systems Operational**"
        )
        await msg.edit(content=sys_report)

# --- RUNNER ---

if __name__ == '__main__':
    if not TOKEN:
        print("Error: BOT_TOKEN missing. Please set it in your environment variables.")
        exit(1)

    # Start Flask in a background thread for keeping the bot alive (e.g., on Render/UptimeRobot)
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    print("Bot is connecting to Discord...")
    bot.run(TOKEN)
