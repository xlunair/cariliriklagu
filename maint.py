import requests
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
import logging
import time
import random
import urllib.parse

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Konfigurasi
BOT_TOKEN = "7905915168:AAEe9IaFRjkAAjra1BXKwSe37dxrFVqbboo"
GENIUS_ACCESS_TOKEN = "L6IK-TI3-N-wdGhldZDySNnEwwrx2a5s2ZjyolDMXSJ7-Ox5c9Pb2rFi22Md-ufd"

class MultiSourceLyricsBot:
    def __init__(self, genius_token):
        self.genius_token = genius_token
        self.base_url = "https://api.genius.com"
        self.headers = {
            'Authorization': f'Bearer {genius_token}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.last_request_time = 0
        self.min_request_interval = 2  # 2 detik antar request

        # User agents untuk rotasi
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
        ]

    def _rate_limit(self):
        """Rate limiting dengan jitter"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            # Tambahkan random jitter
            sleep_time += random.uniform(0.5, 1.5)
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def search_song(self, query):
        """Mencari lagu di Genius API"""
        try:
            self._rate_limit()
            search_url = f"{self.base_url}/search"
            params = {'q': query}

            response = requests.get(search_url, params=params, headers=self.headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                hits = data['response']['hits']

                if hits:
                    songs = []
                    for hit in hits[:5]:
                        song_info = {
                            'title': hit['result']['title'],
                            'artist': hit['result']['primary_artist']['name'],
                            'url': hit['result']['url'],
                            'id': hit['result']['id'],
                            'release_date': hit['result'].get('release_date_for_display', 'N/A')
                        }
                        songs.append(song_info)
                    return songs
                else:
                    return []
            else:
                logger.error(f"Error searching song: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Exception in search_song: {str(e)}")
            return []

    def get_lyrics_from_lyrics_ovh(self, artist, title):
        """Coba ambil lirik dari lyrics.ovh API (gratis)"""
        try:
            self._rate_limit()

            # Clean artist and title
            artist = artist.replace(' ', '%20')
            title = title.replace(' ', '%20')

            url = f"https://api.lyrics.ovh/v1/{artist}/{title}"

            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                lyrics = data.get('lyrics', '')

                if lyrics and len(lyrics.strip()) > 20:
                    # Batasi preview lirik untuk menghindari masalah hak cipta
                    lines = lyrics.split('\n')
                    preview = '\n'.join(lines[:4])  # Hanya 4 baris pertama

                    return f"🎵 Preview lirik (4 baris pertama):\n\n{preview}\n\n[Lirik lengkap tersedia di sumber asli]"

            return None
        except Exception as e:
            logger.error(f"Error getting lyrics from lyrics.ovh: {str(e)}")
            return None

    def get_song_info_alternative(self, song_data):
        """Dapatkan informasi lagu tanpa scraping"""
        try:
            info_parts = []

            # Informasi dari API Genius
            info_parts.append(f"📝 Judul: {song_data['title']}")
            info_parts.append(f"🎤 Artis: {song_data['artist']}")

            if song_data.get('release_date') and song_data['release_date'] != 'N/A':
                info_parts.append(f"📅 Rilis: {song_data['release_date']}")

            # Coba dapatkan preview lirik dari sumber alternatif
            lyrics_preview = self.get_lyrics_from_lyrics_ovh(song_data['artist'], song_data['title'])

            result = "ℹ️ Informasi lagu:\n\n" + "\n".join(info_parts)

            if lyrics_preview:
                result += f"\n\n{lyrics_preview}"
            else:
                result += "\n\n💡 Untuk membaca lirik lengkap, klik link di bawah ini."

            return result

        except Exception as e:
            logger.error(f"Error in get_song_info_alternative: {str(e)}")
            return "ℹ️ Informasi lagu ditemukan.\n\n💡 Untuk membaca lirik lengkap, klik link di bawah ini."

    def search_youtube_music(self, query):
        """Buat link pencarian YouTube Music"""
        encoded_query = urllib.parse.quote(query)
        return f"https://music.youtube.com/search?q={encoded_query}"

    def search_spotify(self, query):
        """Buat link pencarian Spotify"""
        encoded_query = urllib.parse.quote(query)
        return f"https://open.spotify.com/search/{encoded_query}"

    def search_apple_music(self, query):
        """Buat link pencarian Apple Music"""
        encoded_query = urllib.parse.quote(query)
        return f"https://music.apple.com/search?term={encoded_query}"

# Inisialisasi bot
lyrics_bot = MultiSourceLyricsBot(GENIUS_ACCESS_TOKEN)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /start"""
    welcome_message = """
🎵 *Selamat datang di Multi-Source Lyrics Bot!* 🎵

Saya dapat membantu Anda mencari informasi lagu dari berbagai sumber.

*Fitur:*
• 🔍 Pencarian lagu di Genius
• 📝 Preview lirik (jika tersedia)
• 🎵 Link ke platform musik populer
• 📱 Informasi lagu lengkap

*Cara penggunaan:*
Ketik nama lagu dan artis, lalu pilih dari hasil pencarian.

*Contoh:*
`Bohemian Rhapsody Queen`
`Imagine Dragons Believer`
`The Weeknd Blinding Lights`

Mulai mencari lagu favorit Anda! 🎶
    """
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /help"""
    help_text = """
🎵 *Bantuan Multi-Source Lyrics Bot* 🎵

*Perintah:*
• `/start` - Memulai bot
• `/help` - Menampilkan bantuan

*Cara mencari:*
1. Ketik nama lagu + artis
2. Pilih dari hasil pencarian
3. Dapatkan informasi lengkap

*Sumber informasi:*
• 🎯 Genius (metadata lagu)
• 🎵 Lyrics.ovh (preview lirik)
• 🎵 YouTube Music
• 🎵 Spotify
• 🎵 Apple Music

*Tips:*
• Gunakan nama yang tepat
• Coba variasi nama artis
• Gunakan bahasa Inggris untuk hasil terbaik

Bot ini menghormati hak cipta dengan memberikan preview terbatas dan mengarahkan ke sumber asli.
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def search_lyrics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk pencarian lagu"""
    query = update.message.text

    loading_message = await update.message.reply_text("🔍 Mencari lagu dari berbagai sumber...")

    # Cari di Genius
    songs = lyrics_bot.search_song(query)

    if songs:
        keyboard = []
        for i, song in enumerate(songs):
            button_text = f"{song['title']} - {song['artist']}"
            if len(button_text) > 60:
                button_text = button_text[:57] + "..."
            callback_data = f"song_{i}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

        # Tambahkan tombol untuk pencarian di platform lain
        keyboard.append([
            InlineKeyboardButton("🎵 YouTube Music", url=lyrics_bot.search_youtube_music(query)),
            InlineKeyboardButton("🎵 Spotify", url=lyrics_bot.search_spotify(query))
        ])

        context.user_data['search_results'] = songs
        reply_markup = InlineKeyboardMarkup(keyboard)

        await loading_message.edit_text(
            f"🎵 Ditemukan {len(songs)} lagu untuk '{query}':\n\nPilih lagu atau cari di platform musik:",
            reply_markup=reply_markup
        )
    else:
        # Jika tidak ada hasil, berikan alternatif
        keyboard = [
            [InlineKeyboardButton("🎵 Cari di YouTube Music", url=lyrics_bot.search_youtube_music(query))],
            [InlineKeyboardButton("🎵 Cari di Spotify", url=lyrics_bot.search_spotify(query))],
            [InlineKeyboardButton("🎵 Cari di Apple Music", url=lyrics_bot.search_apple_music(query))]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await loading_message.edit_text(
            f"❌ Tidak ditemukan hasil untuk '{query}' di database.\n\nCoba cari di platform musik:",
            reply_markup=reply_markup
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk callback button"""
    query = update.callback_query
    await query.answer()

    if query.data.startswith('song_'):
        song_index = int(query.data.split('_')[1])
        search_results = context.user_data.get('search_results', [])

        if song_index < len(search_results):
            song = search_results[song_index]

            await query.edit_message_text("📥 Mengumpulkan informasi lagu...")

            # Dapatkan informasi lagu
            song_info = lyrics_bot.get_song_info_alternative(song)

            # Buat keyboard dengan link ke berbagai platform
            keyboard = [
                [InlineKeyboardButton("🔗 Lihat di Genius", url=song['url'])],
                [
                    InlineKeyboardButton("🎵 YouTube Music", url=lyrics_bot.search_youtube_music(f"{song['title']} {song['artist']}")),
                    InlineKeyboardButton("🎵 Spotify", url=lyrics_bot.search_spotify(f"{song['title']} {song['artist']}"))
                ],
                [InlineKeyboardButton("🎵 Apple Music", url=lyrics_bot.search_apple_music(f"{song['title']} {song['artist']}"))]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            message = f"🎵 *{song['title']}*\n👤 *{song['artist']}*\n\n{song_info}"

            try:
                await query.edit_message_text(
                    message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup,
                    disable_web_page_preview=True
                )
            except Exception as e:
                # Fallback jika ada masalah formatting
                simple_message = f"🎵 *{song['title']}* - *{song['artist']}*\n\n✅ Informasi lagu ditemukan!"

                await query.edit_message_text(
                    simple_message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup,
                    disable_web_page_preview=True
                )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk error"""
    logger.error(f"Update {update} caused error {context.error}")

    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ Terjadi kesalahan. Silakan coba lagi nanti."
            )
        except:
            pass

def main():
    """Fungsi utama untuk menjalankan bot"""
    if BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        print("❌ Error: Silakan isi BOT_TOKEN dengan token bot Telegram Anda")
        return

    if GENIUS_ACCESS_TOKEN == "YOUR_GENIUS_ACCESS_TOKEN":
        print("❌ Error: Silakan isi GENIUS_ACCESS_TOKEN dengan token Genius API Anda")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_lyrics))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_error_handler(error_handler)

    print("🤖 Multi-Source Lyrics Bot dimulai...")
    print("✅ Bot siap dengan multiple fallback sources!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
