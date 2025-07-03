import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import lyricsgenius

# Konfigurasi logging untuk melihat aktivitas bot di konsol
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- PENTING: GANTI DENGAN TOKEN KAMU YANG SEBENARNYA ---

# Token Bot Telegram dari @BotFather
TELEGRAM_BOT_TOKEN = "7905915168:AAEe9IaFRjkAAjra1BXKwSe37dxrFVqbboo" 

# Access Token Genius dari genius.com/developers (yang baru saja kamu dapatkan: FvVYV3R8o6ckf2rzrUA-2otYWteaU6IBTLw2twgF-WPWGF2i3rfXZzu3CE3OpFNB)
GENIUS_ACCESS_TOKEN = "FvVYV3R8o6ckf2rzrUA-2otYWteaU6IBTLw2twgF-WPWGF2i3rfXZzu3CE3OpFNB" 

# --- AKHIR BAGIAN PENTING ---

# Inisialisasi Genius API
# Pastikan GENIUS_ACCESS_TOKEN sudah diisi dengan benar
genius = lyricsgenius.Genius(GENIUS_ACCESS_TOKEN)
genius.verbose = False  # Menonaktifkan pesan status dari lyricsgenius agar konsol lebih bersih
genius.remove_section_headers = True # Menghapus bagian seperti [Chorus], [Verse 1] dari lirik

# Fungsi handler untuk perintah /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengirim pesan sambutan saat perintah /start diterima."""
    await update.message.reply_text(
        'Halo! Aku adalah Bot Pencari Lirik. \n\n'
        'Kirimkan judul lagu dan artisnya dalam format:\n'
        '  *Judul Lagu - Nama Artis*\n'
        '  atau\n'
        '  *Judul Lagu by Nama Artis*\n\n'
        'Contoh: Bohemian Rhapsody - Queen\n'
        'Contoh: Hampa by Ari Lasso'
    )

# Fungsi handler untuk mencari lirik
async def search_lyrics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mencari lirik dari Genius berdasarkan input pengguna dan mengirimkannya."""
    user_input = update.message.text
    logging.info(f"Menerima pencarian dari {update.effective_user.full_name}: {user_input}")

    title = None
    artist = None

    # Mencoba parsing input untuk mendapatkan judul dan artis
    if " - " in user_input:
        parts = user_input.split(" - ", 1)
        title = parts[0].strip()
        if len(parts) > 1:
            artist = parts[1].strip()
    elif " by " in user_input:
        parts = user_input.split(" by ", 1)
        title = parts[0].strip()
        if len(parts) > 1:
            artist = parts[1].strip()
    else:
        await update.message.reply_text(
            'Format tidak dikenal. Harap gunakan "Judul Lagu - Artis" atau "Judul Lagu by Artis".\n'
            'Contoh: Bohemian Rhapsody - Queen'
        )
        return

    if not title:
        await update.message.reply_text('Mohon berikan judul lagu.')
        return

    # Memberi tahu pengguna bahwa bot sedang mencari
    if artist:
        await update.message.reply_text(f'Mencari lirik untuk "{title}" oleh "{artist}"...')
    else:
        await update.message.reply_text(f'Mencari lirik untuk "{title}"...')

    try:
        # Memanggil Genius API
        song = genius.search_song(title, artist)

        if song:
            lyrics = song.lyrics

            # Telegram memiliki batasan panjang pesan (sekitar 4096 karakter)
            # Jika liriknya sangat panjang, kita perlu membaginya menjadi beberapa pesan
            if len(lyrics) > 4000: # Menggunakan 4000 sebagai batas aman
                await update.message.reply_text(f"Lirik untuk *{song.title}* oleh *{song.artist}*:\n\n{lyrics[:2000]}...", parse_mode='Markdown')
                # Kirim sisa lirik dalam pesan terpisah
                # Anda bisa membagi lagi jika sisa lirik masih sangat panjang
                await update.message.reply_text(f"...{lyrics[2000:]}", parse_mode='Markdown')
            else:
                await update.message.reply_text(f"Lirik untuk *{song.title}* oleh *{song.artist}*:\n\n{lyrics}", parse_mode='Markdown')

            logging.info(f"Lirik ditemukan untuk: {song.title} oleh {song.artist}")
        else:
            await update.message.reply_text(f'Maaf, lirik untuk "{title}"' + (f' oleh "{artist}"' if artist else '') + ' tidak ditemukan.')
            logging.info(f"Lirik tidak ditemukan untuk: {user_input}")
    except Exception as e:
        logging.error(f"Terjadi kesalahan saat mencari lirik: {e}", exc_info=True)
        await update.message.reply_text(
            'Terjadi kesalahan saat mencari lirik. Mohon coba lagi nanti atau pastikan formatnya benar.'
        )

def main() -> None:
    """Fungsi utama untuk menjalankan bot."""
    # Membuat objek ApplicationBuilder dan menghubungkannya dengan token bot
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Menambahkan handler untuk perintah /start
    application.add_handler(CommandHandler("start", start))

    # Menambahkan handler untuk pesan teks (selain perintah)
    # Filter 'filters.TEXT & ~filters.COMMAND' memastikan hanya pesan teks biasa (bukan perintah seperti /start) yang diproses oleh search_lyrics
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_lyrics))

    logging.info("Bot sedang berjalan...")
    # Memulai polling untuk menerima update dari Telegram
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()