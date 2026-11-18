"""
bot.py — Bot Telegram "Penyemangat Mahasiswa"

Ceritakan perasaanmu (misalnya "aku lagi capek"), bot akan menebak mood-mu
dan mengirim kutipan yang cocok dari data hasil scraping quotes.toscrape.com.

Jalankan:  python bot.py
"""

import json
import logging
import os
import threading
import time
from datetime import datetime
from html import escape
from pathlib import Path

import telebot
from telebot import types
from dotenv import load_dotenv

import logika
import scraper

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("bot")

# ---------------------------------------------------------------------------
# Konfigurasi (dibaca dari file .env, bukan ditulis di kode)
# ---------------------------------------------------------------------------
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = os.getenv("ADMIN_ID", "").strip()        # opsional, untuk /perbarui
JAM_KIRIM = os.getenv("JAM_KIRIM", "07:00").strip()  # jam kirim kutipan harian

if not TOKEN:
    raise SystemExit("BOT_TOKEN belum diisi. Salin .env.contoh menjadi .env, lalu isi token dari @BotFather.")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

FILE_PELANGGAN = Path(__file__).parent / "data" / "pelanggan.json"
kunci_file = threading.Lock()

DATA = []   # daftar kutipan hasil scraping
INFO = {}   # info pengambilan data (waktu, jumlah)


# ---------------------------------------------------------------------------
# Fungsi bantu
# ---------------------------------------------------------------------------
def siapkan_data(paksa=False):
    """Muat data kutipan (dari cache atau scraping ulang)."""
    global DATA, INFO
    paket = scraper.muat_data(paksa_perbarui=paksa)
    DATA = paket["kutipan"]
    INFO = {"diambil_pada": paket["diambil_pada"], "jumlah": paket["jumlah"]}
    log.info("%d kutipan siap dipakai (diambil %s)", INFO["jumlah"], INFO["diambil_pada"])


def ambil_argumen(pesan):
    """'/tokoh einstein' -> 'einstein'. Kosong kalau tidak ada argumen."""
    bagian = (pesan.text or "").split(maxsplit=1)
    return bagian[1].strip() if len(bagian) > 1 else ""


def baca_pelanggan():
    with kunci_file:
        if FILE_PELANGGAN.exists():
            return set(json.loads(FILE_PELANGGAN.read_text(encoding="utf-8")))
        return set()


def tulis_pelanggan(daftar):
    with kunci_file:
        FILE_PELANGGAN.parent.mkdir(parents=True, exist_ok=True)
        FILE_PELANGGAN.write_text(json.dumps(sorted(daftar)), encoding="utf-8")


def keyboard_mood():
    """Tombol pilihan mood (inline keyboard)."""
    kb = types.InlineKeyboardMarkup(row_width=3)
    kb.add(*[
        types.InlineKeyboardButton(f"{info['emoji']} {nama.title()}", callback_data=f"mood:{nama}")
        for nama, info in logika.MOOD.items()
    ])
    return kb


def kirim_kutipan_mood(chat_id, mood):
    k = logika.pilih_kutipan(DATA, mood)
    if not k:
        bot.send_message(chat_id, "Maaf, data kutipan belum tersedia. Coba lagi nanti ya.")
        return
    bot.send_message(chat_id, f"{logika.MOOD[mood]['sapaan']}\n\n{logika.format_kutipan(k)}")


# ---------------------------------------------------------------------------
# Perintah
# ---------------------------------------------------------------------------
@bot.message_handler(commands=["start", "help"])
def cmd_start(pesan):
    nama = escape(pesan.from_user.first_name or "kamu")
    bot.send_message(
        pesan.chat.id,
        f"Halo, <b>{nama}</b>! 👋\n"
        "Aku <b>Bot Penyemangat Mahasiswa</b>. Ceritakan perasaanmu, nanti aku kirim kutipan yang cocok.\n\n"
        "<b>Perintah:</b>\n"
        "/semangat – kutipan acak\n"
        "/mood – pilih suasana hati lewat tombol\n"
        "/tokoh &lt;nama&gt; – kutipan dari tokoh tertentu\n"
        "/cari &lt;kata&gt; – cari kutipan berisi kata tertentu\n"
        "/statistik – ringkasan data hasil scraping\n"
        f"/langganan – kutipan otomatis setiap pukul {JAM_KIRIM}\n"
        "/berhenti – berhenti berlangganan\n\n"
        "Atau ketik saja, misalnya: <i>aku lagi capek banget</i>",
        reply_markup=keyboard_mood(),
    )


@bot.message_handler(commands=["semangat"])
def cmd_semangat(pesan):
    k = logika.pilih_kutipan(DATA)
    teks = logika.format_kutipan(k) if k else "Maaf, data kutipan belum tersedia."
    bot.send_message(pesan.chat.id, teks)


@bot.message_handler(commands=["mood"])
def cmd_mood(pesan):
    arg = ambil_argumen(pesan).lower()
    if arg in logika.MOOD:
        kirim_kutipan_mood(pesan.chat.id, arg)
    else:
        bot.send_message(pesan.chat.id, "Lagi merasa apa hari ini?", reply_markup=keyboard_mood())


@bot.callback_query_handler(func=lambda c: c.data.startswith("mood:"))
def klik_tombol_mood(call):
    bot.answer_callback_query(call.id)
    mood = call.data.split(":", 1)[1]
    if mood in logika.MOOD:
        kirim_kutipan_mood(call.message.chat.id, mood)


@bot.message_handler(commands=["tokoh"])
def cmd_tokoh(pesan):
    nama = ambil_argumen(pesan)
    if not nama:
        populer = ", ".join(t for t, _ in logika.statistik(DATA)["top_tokoh"])
        bot.send_message(pesan.chat.id, f"Tulis nama tokohnya, contoh: <code>/tokoh einstein</code>\n\nTokoh populer: {escape(populer)}")
        return

    hasil = logika.cari_tokoh(DATA, nama)
    if not hasil:
        bot.send_message(pesan.chat.id, f"Tidak ada kutipan dari tokoh “{escape(nama)}”. Coba nama lain ya.")
        return

    k = logika.pilih_kutipan(hasil)
    bot.send_message(pesan.chat.id, f"{logika.format_kutipan(k)}\n\n<i>({len(hasil)} kutipan ditemukan untuk “{escape(nama)}”)</i>")


@bot.message_handler(commands=["cari"])
def cmd_cari(pesan):
    kata = ambil_argumen(pesan)
    if not kata:
        bot.send_message(pesan.chat.id, "Tulis kata yang dicari, contoh: <code>/cari dream</code>")
        return

    hasil = logika.cari_kata(DATA, kata)
    if not hasil:
        bot.send_message(pesan.chat.id, f"Tidak ada kutipan yang mengandung “{escape(kata)}”.")
        return

    potongan = "\n\n".join(logika.format_kutipan(k) for k in hasil[:3])
    bot.send_message(pesan.chat.id, f"Ditemukan <b>{len(hasil)}</b> kutipan. Ini {min(3, len(hasil))} di antaranya:\n\n{potongan}")


@bot.message_handler(commands=["statistik"])
def cmd_statistik(pesan):
    s = logika.statistik(DATA)
    top_tokoh = "\n".join(f"  {i}. {escape(t)} ({n})" for i, (t, n) in enumerate(s["top_tokoh"], 1))
    top_tema = "\n".join(f"  {i}. #{escape(t)} ({n})" for i, (t, n) in enumerate(s["top_tema"], 1))
    bot.send_message(
        pesan.chat.id,
        "📊 <b>Statistik data hasil scraping</b>\n"
        f"Sumber: quotes.toscrape.com\n"
        f"Diambil pada: {escape(INFO.get('diambil_pada', '-'))}\n\n"
        f"Jumlah kutipan: <b>{s['jumlah_kutipan']}</b>\n"
        f"Jumlah tokoh: <b>{s['jumlah_tokoh']}</b>\n"
        f"Jumlah tema: <b>{s['jumlah_tema']}</b>\n\n"
        f"<b>Tokoh terbanyak:</b>\n{top_tokoh}\n\n"
        f"<b>Tema terbanyak:</b>\n{top_tema}",
    )


@bot.message_handler(commands=["langganan"])
def cmd_langganan(pesan):
    daftar = baca_pelanggan()
    daftar.add(pesan.chat.id)
    tulis_pelanggan(daftar)
    bot.send_message(pesan.chat.id, f"✅ Siap! Setiap pukul {JAM_KIRIM} aku kirim satu kutipan penyemangat. Ketik /berhenti untuk berhenti.")


@bot.message_handler(commands=["berhenti"])
def cmd_berhenti(pesan):
    daftar = baca_pelanggan()
    daftar.discard(pesan.chat.id)
    tulis_pelanggan(daftar)
    bot.send_message(pesan.chat.id, "Oke, langganan dihentikan. Ketik /langganan kalau mau mulai lagi. 👋")


@bot.message_handler(commands=["perbarui"])
def cmd_perbarui(pesan):
    if ADMIN_ID and str(pesan.from_user.id) != ADMIN_ID:
        bot.send_message(pesan.chat.id, "Perintah ini khusus admin.")
        return

    bot.send_message(pesan.chat.id, "⏳ Sedang scraping ulang, tunggu sebentar...")
    try:
        siapkan_data(paksa=True)
        bot.send_message(pesan.chat.id, f"✅ Data diperbarui: {INFO['jumlah']} kutipan ({escape(INFO['diambil_pada'])}).")
    except Exception as e:  # noqa: BLE001 - laporkan error apa pun ke admin
        log.exception("Gagal memperbarui data")
        bot.send_message(pesan.chat.id, f"❌ Gagal memperbarui data: {escape(str(e))}")


# Handler terakhir: semua teks biasa (bukan perintah) -> tebak mood
@bot.message_handler(content_types=["text"])
def pesan_bebas(pesan):
    if pesan.text.startswith("/"):
        bot.send_message(pesan.chat.id, "Perintah tidak dikenal. Ketik /help untuk melihat daftar perintah.")
        return

    mood = logika.deteksi_mood(pesan.text)
    if mood:
        kirim_kutipan_mood(pesan.chat.id, mood)
    else:
        bot.send_message(
            pesan.chat.id,
            "Hmm, aku belum bisa menebak perasaanmu 😅\nCoba ceritakan dengan kata seperti <i>capek, sedih, bingung, malas</i>, atau pilih di bawah:",
            reply_markup=keyboard_mood(),
        )


# ---------------------------------------------------------------------------
# Pengiriman otomatis harian (berjalan di thread terpisah)
# ---------------------------------------------------------------------------
def kirim_ke_pelanggan():
    daftar = baca_pelanggan()
    tidak_aktif = set()
    for chat_id in daftar:
        k = logika.pilih_kutipan(DATA, "capek")  # tema penyemangat
        if not k:
            return
        try:
            bot.send_message(chat_id, f"🌅 <b>Kutipan pagi ini</b>\n\n{logika.format_kutipan(k)}")
        except telebot.apihelper.ApiTelegramException as e:
            if e.error_code == 403:   # pengguna memblokir bot
                tidak_aktif.add(chat_id)
            log.warning("Gagal kirim ke %s: %s", chat_id, e)
    if tidak_aktif:
        tulis_pelanggan(daftar - tidak_aktif)
    log.info("Kutipan harian terkirim ke %d pelanggan", len(daftar) - len(tidak_aktif))


def pengirim_harian():
    sudah_kirim_tanggal = None
    while True:
        sekarang = datetime.now()
        if sekarang.strftime("%H:%M") == JAM_KIRIM and sudah_kirim_tanggal != sekarang.date():
            sudah_kirim_tanggal = sekarang.date()
            try:
                kirim_ke_pelanggan()
            except Exception:  # noqa: BLE001 - thread tidak boleh mati
                log.exception("Error saat mengirim kutipan harian")
        time.sleep(30)


# ---------------------------------------------------------------------------
# Program utama
# ---------------------------------------------------------------------------
def main():
    siapkan_data()
    try:
        bot.set_my_commands([
            types.BotCommand("semangat", "Kutipan acak"),
            types.BotCommand("mood", "Pilih suasana hati"),
            types.BotCommand("tokoh", "Kutipan dari tokoh tertentu"),
            types.BotCommand("cari", "Cari kutipan berisi kata tertentu"),
            types.BotCommand("statistik", "Ringkasan data hasil scraping"),
            types.BotCommand("langganan", "Kutipan otomatis tiap pagi"),
            types.BotCommand("berhenti", "Berhenti berlangganan"),
        ])
    except Exception as e:  # noqa: BLE001 - menu perintah tidak wajib
        log.warning("Gagal memasang menu perintah: %s", e)

    threading.Thread(target=pengirim_harian, daemon=True).start()
    log.info("Bot berjalan. Tekan Ctrl+C untuk berhenti.")
    bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
    main()
