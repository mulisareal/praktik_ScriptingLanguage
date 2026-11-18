"""
scraper.py — Mengambil (scraping) data kutipan dari https://quotes.toscrape.com

Situs quotes.toscrape.com memang disediakan khusus untuk latihan web scraping,
jadi aman dipakai untuk tugas kuliah.

Alur:
1. Ambil HTML halaman 1 dengan requests.
2. Baca HTML dengan BeautifulSoup, ambil setiap kutipan (teks, tokoh, tema).
3. Cari tombol "Next" -> pindah ke halaman berikutnya, ulangi sampai habis.
4. Simpan hasilnya ke data/quotes.json (cache) supaya tidak scraping terus-menerus.

Bisa dijalankan sendiri untuk mencoba:  python scraper.py
"""

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://quotes.toscrape.com/"
FILE_DATA = Path(__file__).parent / "data" / "quotes.json"
MASA_BERLAKU = timedelta(hours=24)   # cache dianggap basi setelah 24 jam
JEDA_DETIK = 1                       # jeda antar-halaman, supaya sopan ke server
MAKS_HALAMAN = 20                    # pengaman agar perulangan tidak tak berujung
HEADERS = {"User-Agent": "BotPenyemangatMahasiswa/1.0 (tugas kuliah scripting language)"}

log = logging.getLogger(__name__)


def parse_halaman(html):
    """Ambil semua kutipan dari SATU halaman HTML.

    Mengembalikan (daftar_kutipan, link_halaman_berikutnya).
    link_halaman_berikutnya bernilai None kalau sudah halaman terakhir.
    """
    soup = BeautifulSoup(html, "html.parser")
    hasil = []

    # Setiap kutipan dibungkus <div class="quote">
    for kotak in soup.select("div.quote"):
        teks = kotak.select_one("span.text")
        tokoh = kotak.select_one("small.author")
        if not teks or not tokoh:
            continue  # lewati kotak yang strukturnya tidak lengkap

        hasil.append({
            "teks": teks.get_text(strip=True).strip("“”\""),
            "tokoh": tokoh.get_text(strip=True),
            "tema": [a.get_text(strip=True) for a in kotak.select("div.tags a.tag")],
        })

    # Tombol "Next" ada di <li class="next"><a href="/page/2/">
    tombol_next = soup.select_one("li.next a")
    link_next = tombol_next.get("href") if tombol_next else None
    return hasil, link_next


def scrape_semua():
    """Scraping semua halaman, mengikuti tombol Next sampai habis."""
    semua = []
    url = BASE_URL
    nomor = 0

    while url and nomor < MAKS_HALAMAN:
        nomor += 1
        log.info("Mengambil halaman %d: %s", nomor, url)

        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()          # error kalau status bukan 200
        resp.encoding = "utf-8"

        kutipan, link_next = parse_halaman(resp.text)
        semua.extend(kutipan)

        url = urljoin(BASE_URL, link_next) if link_next else None
        if url:
            time.sleep(JEDA_DETIK)

    # Pembersihan sederhana: buang kutipan ganda (teks + tokoh yang sama)
    unik, sudah_ada = [], set()
    for k in semua:
        kunci = (k["teks"].lower(), k["tokoh"].lower())
        if kunci not in sudah_ada:
            sudah_ada.add(kunci)
            unik.append(k)

    log.info("Selesai: %d kutipan unik dari %d halaman", len(unik), nomor)
    return unik


def simpan(daftar_kutipan):
    """Simpan hasil scraping ke file JSON beserta waktu pengambilannya."""
    FILE_DATA.parent.mkdir(parents=True, exist_ok=True)
    paket = {
        "sumber": BASE_URL,
        "diambil_pada": datetime.now().isoformat(timespec="seconds"),
        "jumlah": len(daftar_kutipan),
        "kutipan": daftar_kutipan,
    }
    FILE_DATA.write_text(json.dumps(paket, ensure_ascii=False, indent=2), encoding="utf-8")
    return paket


def baca_cache():
    """Baca file cache. Mengembalikan None kalau file belum ada atau rusak."""
    if not FILE_DATA.exists():
        return None
    try:
        return json.loads(FILE_DATA.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        log.warning("File cache tidak bisa dibaca: %s", e)
        return None


def muat_data(paksa_perbarui=False):
    """Ambil data kutipan.

    - Kalau cache masih baru (< 24 jam) -> pakai cache.
    - Kalau cache basi / belum ada / dipaksa -> scraping ulang.
    - Kalau scraping gagal (misalnya internet putus) -> pakai cache lama kalau ada.
    """
    cache = baca_cache()

    if cache and not paksa_perbarui:
        umur = datetime.now() - datetime.fromisoformat(cache["diambil_pada"])
        if umur < MASA_BERLAKU:
            log.info("Memakai cache (%d kutipan, umur %s)", cache["jumlah"], str(umur).split(".")[0])
            return cache

    try:
        return simpan(scrape_semua())
    except requests.RequestException as e:
        log.error("Scraping gagal: %s", e)
        if cache:
            log.warning("Memakai cache lama sebagai cadangan.")
            return cache
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    paket = muat_data(paksa_perbarui=True)
    print(f"\nBerhasil mengambil {paket['jumlah']} kutipan. Contoh:")
    for k in paket["kutipan"][:3]:
        print(f"- “{k['teks']}” — {k['tokoh']}  {k['tema']}")
    print(f"\nData tersimpan di: {FILE_DATA}")
