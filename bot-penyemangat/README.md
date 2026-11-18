# Bot Penyemangat Mahasiswa 🤖💪

Bot Telegram yang mengirim **kutipan motivasi sesuai suasana hati**.
Kamu cukup bercerita dengan bahasa sehari-hari, misalnya *"aku lagi capek banget"*,
lalu bot menebak mood-mu dan memilih kutipan yang temanya cocok.

Data kutipan diambil dengan **web scraping** dari [quotes.toscrape.com](https://quotes.toscrape.com),
situs yang memang disediakan untuk latihan scraping.

## Fitur

| Perintah | Fungsi |
|---|---|
| `/start` atau `/help` | Sambutan, daftar perintah, tombol mood |
| `/semangat` | Kutipan acak |
| `/mood` | Pilih suasana hati lewat tombol (atau `/mood capek`) |
| `/tokoh <nama>` | Kutipan dari tokoh tertentu, misalnya `/tokoh einstein` |
| `/cari <kata>` | Cari kutipan yang mengandung kata tertentu |
| `/statistik` | Ringkasan data hasil scraping (tokoh & tema terbanyak) |
| `/langganan` / `/berhenti` | Kutipan otomatis setiap pagi |
| `/perbarui` | Scraping ulang (khusus admin bila `ADMIN_ID` diisi) |
| *(teks bebas)* | Bot menebak mood dari kalimatmu |

Mood yang dikenali: capek, sedih, malas, bingung, cemas, bosan, senang.

## Struktur file

```
bot-penyemangat/
├── scraper.py      # mengambil data dari website (requests + BeautifulSoup)
├── logika.py       # mengolah data: deteksi mood (regex), pencarian, statistik
├── bot.py          # bot Telegram (pyTelegramBotAPI)
├── test_bot.py     # pengujian otomatis (unittest)
├── requirements.txt
├── .env.contoh     # contoh konfigurasi
└── data/           # dibuat otomatis: quotes.json (cache), pelanggan.json
```

## Cara menjalankan

1. **Buat bot di Telegram**: chat [@BotFather](https://t.me/BotFather), kirim `/newbot`, ikuti langkahnya, lalu salin token yang diberikan.
2. **Install library**:
   ```
   pip install -r requirements.txt
   ```
3. **Isi konfigurasi**: salin `.env.contoh` menjadi `.env`, lalu isi `BOT_TOKEN`.
4. **(Opsional) Coba scraper saja**:
   ```
   python scraper.py
   ```
5. **Jalankan bot**:
   ```
   python bot.py
   ```
6. Buka bot-mu di Telegram, lalu ketik `/start`.

Menjalankan pengujian: `python -m unittest -v`

## Cara kerja singkat

1. `scraper.py` mengambil HTML halaman 1, membaca setiap `<div class="quote">`
   (teks, tokoh, tema), lalu mengikuti tombol **Next** sampai halaman terakhir.
2. Hasilnya dibersihkan (duplikat dibuang) dan disimpan ke `data/quotes.json`.
   Cache ini dipakai selama 24 jam supaya tidak scraping terus-menerus.
   Kalau scraping gagal, bot tetap jalan memakai cache lama.
3. Saat pengguna mengirim pesan, `logika.py` menebak mood dengan regex,
   lalu memilih kutipan yang temanya cocok.
4. `bot.py` mengirim balasan, dan sebuah thread kecil mengirim kutipan harian ke pelanggan.

## Etika scraping

- Sumber data adalah situs latihan scraping.
- Ada jeda 1 detik antar-halaman dan identitas `User-Agent` yang jelas.
- Data disimpan di cache sehingga server tidak diakses berulang-ulang.
