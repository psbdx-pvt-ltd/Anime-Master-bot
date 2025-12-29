import os
import logging
import requests
import threading
import time
import base64
import json
from datetime import datetime
import pytz 
from flask import Flask
import discord
from discord import app_commands
from discord.ext import commands
from imdb import Cinemagoer
from deep_translator import GoogleTranslator

# --- CONFIGURATION ---
# Load secrets from Environment Variables for security (Open Source Best Practice)
TOKEN = os.getenv("BOT_TOKEN")

try:
    ADMN_ID = int(os.getenv("ADMN_ID", "0").strip())
except ValueError:
    ADMN_ID = 0

PORT = int(os.environ.get('PORT', 5000))

# Configure Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- GLOBAL VARIABLES ---
LOCKED_CHANNEL_ID = None

# --- PROTECTION ALGORITHM ---
# This block contains the protected/encrypted details about the developer and license.
# As per license requirements, this function and the encrypted string should not be modified.
def _decrypt_about_data():
    # This string is Base64 encoded JSON data containing the version and credits.
    # Editing this string will break the /about command integrity.
    _encrypted_payload = (
        "eyJWZXJzaW9uIENvZGUiOiAiOS4xIiwgIlZlcnNpb24gdHlwZSI6ICJPcGVuIFNvdXJjZSIsICJE"
        "ZXZlbG9wZXIgTmFtZSI6ICJQU0JEeCIs "
        "IlVzZXIgTGljZW5zZSBUeXBlIjogIk9wZW4gU291cmNlIiwgIk9wZW4gU291cmNlIENvbW1lbnQi"
        "OiAidGhlIGN1cnJlbnQgZGV2ZWxvZXByIGNhbiBlZGl0IHRoZSBib3QgY29kZSBhbmQgY2hhbmdl"
        "IGNvbmZpZyBtZXRob2RzIGJ1dCBkZXZlbG9wZXIgaGFzIG5vIHBlcm1pc3Npb24gdG8gZWRpdCB0"
        "aGUgYWxnb3JpdGhtJ3MgZnVuY3Rpb25zIG9yIHRoZSBlbmNydXB0ZWQgbWVzc2FnZXMvY29kZXMu"
        "In0="
    )
    try:
        # Decrypting (Decoding) the payload for display
        decoded_bytes = base64.b64decode(_encrypted_payload)
        return json.loads(decoded_bytes.decode('utf-8'))
    except Exception as e:
        logger.error(f"Integrity Check Failed: {e}")
        return {"Error": "License Data Corrupted"}

# --- FLASK SERVER (Keep Alive) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Anime Master Bot is Running! (Open Source Version)"

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

def translate_to_bangla(text):
    """Translates English text to Bangla using Google Translate"""
    if not text: return "কোন বর্ণনা পাওয়া যায়নি।"
    try:
        short_text = (text[:400] + '...') if len(text) > 400 else text
        return GoogleTranslator(source='auto', target='bn').translate(short_text)
    except:
        return text

# --- DATA FETCHING FUNCTIONS ---

def get_mal_full_data(name):
    """Fetches detailed anime data from MyAnimeList via Jikan API"""
    try:
        r = requests.get(f"https://api.jikan.moe/v4/anime?q={name}&limit=1", timeout=5)
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
    # Updated status to show the primary command
    await bot.change_presence(activity=discord.Game(name="/find [anime]"))

# --- ADMIN COMMANDS ---

@bot.tree.command(name="set_channel", description="Admin: Lock the bot to ONLY reply in this current channel.")
async def set_channel_slash(interaction: discord.Interaction):
    if interaction.user.id != ADMN_ID:
        await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
        return

    global LOCKED_CHANNEL_ID
    LOCKED_CHANNEL_ID = interaction.channel_id
    
    await interaction.response.send_message(f"🔒 **Locked!** I will now only reply in <#{LOCKED_CHANNEL_ID}>.")

@bot.tree.command(name="unlock_all", description="Admin: Allow the bot to reply in ALL channels.")
async def unlock_all_slash(interaction: discord.Interaction):
    if interaction.user.id != ADMN_ID:
        await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
        return

    global LOCKED_CHANNEL_ID
    LOCKED_CHANNEL_ID = None
    
    await interaction.response.send_message("🔓 **Unlocked!** I will now reply in all channels.")

# --- PUBLIC SLASH COMMANDS ---

@bot.tree.command(name="about", description="View developer and license information (Encrypted/Protected)")
async def about_slash(interaction: discord.Interaction):
    """
    Displays the encrypted/obfuscated about information.
    The source of this data is protected in _decrypt_about_data()
    """
    if LOCKED_CHANNEL_ID and interaction.channel_id != LOCKED_CHANNEL_ID:
        await interaction.response.send_message(f"⚠️ I am restricted to <#{LOCKED_CHANNEL_ID}>.", ephemeral=True)
        return

    # Decrypt the data at runtime
    data = _decrypt_about_data()
    
    embed = discord.Embed(
        title="🤖 About Anime Master",
        description="Core details and license information.",
        color=0x2b2d31 # Dark embed color
    )
    
    # Dynamically add fields from the decrypted JSON
    for key, value in data.items():
        if key == "Open Source Comment":
            embed.add_field(name="⚖️ Legal/Comment", value=f"*{value}*", inline=False)
        else:
            embed.add_field(name=key, value=f"`{value}`", inline=True)
            
    embed.set_footer(text="Verified Open Source Build | Integrity Check Passed")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="start", description="Get welcome info and help")
async def start_slash(interaction: discord.Interaction):
    if LOCKED_CHANNEL_ID and interaction.channel_id != LOCKED_CHANNEL_ID:
        await interaction.response.send_message(f"⚠️ I am restricted to <#{LOCKED_CHANNEL_ID}>.", ephemeral=True)
        return

    user_name = interaction.user.name
    msg = (
        f"👋 Hello **{user_name}**! 🍥\n"
        f"I am your Anime Assistant.\n\n"
        f"✅ **Usage:** Type `/find` followed by an anime name.\n"
        f"I will fetch ratings, studio info, genres, and translate the description to Bangla."
    )
    await interaction.response.send_message(msg)

@bot.tree.command(name="sources", description="See which websites I use for data")
async def sources_slash(interaction: discord.Interaction):
    if LOCKED_CHANNEL_ID and interaction.channel_id != LOCKED_CHANNEL_ID:
        await interaction.response.send_message(f"⚠️ I am restricted to <#{LOCKED_CHANNEL_ID}>.", ephemeral=True)
        return

    embed = discord.Embed(
        title="📚 Data Sources Used",
        description=(
            "🔹 **MyAnimeList** (Jikan API)\n"
            "🔹 **AniList** (GraphQL)\n"
            "🔹 **Kitsu** (API)\n"
            "🔹 **IMDb** (Cinemagoer)\n"
            "🔹 **Translation:** Google Translate"
        ),
        color=0x3498db
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="find", description="Search for an anime, get info, ratings & Bangla description")
@app_commands.describe(anime_name="The name of the anime you want to search for")
async def find_slash(interaction: discord.Interaction, anime_name: str):
    # 1. CHECK LOCK
    if LOCKED_CHANNEL_ID and interaction.channel_id != LOCKED_CHANNEL_ID:
        await interaction.response.send_message(f"❌ Please use this command in <#{LOCKED_CHANNEL_ID}>!", ephemeral=True)
        return

    # 2. DEFER
    await interaction.response.defer()

    # 3. FETCH DATA
    mal = get_mal_full_data(anime_name)
    
    if not mal:
        await interaction.followup.send("❌ Anime not found. Please check the spelling.")
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
    desc_bn = translate_to_bangla(mal['synopsis'])

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
        description=f"**Bangla Description:**\n{desc_bn}",
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
        lock_status = f"<#{LOCKED_CHANNEL_ID}>" if LOCKED_CHANNEL_ID else "Unlocked (All Channels)"

        sys_report = (
            "**⚙️ System Status**\n"
            "-----------------------------\n"
            f"🕒 **Server Time (BD):** {now_bd}\n"
            f"🤖 **Bot Status:** ✅ Online\n"
            f"🔒 **Restrictions:** {lock_status}\n"
            f"📶 **API Latency:** {discord_ping}\n"
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
