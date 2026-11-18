"""
test_bot.py — Pengujian otomatis (unittest), tanpa internet dan tanpa Telegram.

Jalankan:  python -m unittest -v
"""

import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import logika
import scraper

# Contoh HTML yang strukturnya sama dengan quotes.toscrape.com
CONTOH_HTML = """
<div class="quote">
  <span class="text">“The world as we have created it is a process of our thinking.”</span>
  <span>by <small class="author">Albert Einstein</small></span>
  <div class="tags">Tags:
    <a class="tag" href="/tag/change/page/1/">change</a>
    <a class="tag" href="/tag/thinking/page/1/">thinking</a>
  </div>
</div>
<div class="quote">
  <span class="text">“A day without sunshine is like, you know, night.”</span>
  <span>by <small class="author">Steve Martin</small></span>
  <div class="tags">Tags: <a class="tag" href="/tag/humor/page/1/">humor</a></div>
</div>
<nav><ul class="pager"><li class="next"><a href="/page/2/">Next →</a></li></ul></nav>
"""

DATA = [
    {"teks": "The world as we have created it is a process of our thinking.", "tokoh": "Albert Einstein", "tema": ["change", "thinking"]},
    {"teks": "A day without sunshine is like, you know, night.", "tokoh": "Steve Martin", "tema": ["humor"]},
    {"teks": "It is our choices that show what we truly are.", "tokoh": "J.K. Rowling", "tema": ["abilities", "choices"]},
]


class TestScraper(unittest.TestCase):
    def test_parse_halaman_mengambil_semua_kutipan(self):
        hasil, link_next = scraper.parse_halaman(CONTOH_HTML)
        self.assertEqual(len(hasil), 2)
        self.assertEqual(hasil[0]["tokoh"], "Albert Einstein")
        self.assertEqual(hasil[0]["tema"], ["change", "thinking"])
        self.assertFalse(hasil[0]["teks"].startswith("“"))  # tanda kutip dibuang
        self.assertEqual(link_next, "/page/2/")

    def test_halaman_terakhir_tidak_punya_next(self):
        _, link_next = scraper.parse_halaman("<div class='quote'></div>")
        self.assertIsNone(link_next)

    def test_cache_dipakai_kalau_scraping_gagal(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(scraper, "FILE_DATA", Path(tmp) / "quotes.json"):
                scraper.simpan(DATA)
                gagal = mock.Mock(side_effect=scraper.requests.ConnectionError("internet putus"))
                with mock.patch.object(scraper, "scrape_semua", gagal):
                    paket = scraper.muat_data(paksa_perbarui=True)
                self.assertEqual(paket["jumlah"], 3)


class TestLogika(unittest.TestCase):
    def test_deteksi_mood(self):
        self.assertEqual(logika.deteksi_mood("aku lagi capek banget"), "capek")
        self.assertEqual(logika.deteksi_mood("Lagi GABUT nih"), "bosan")
        self.assertEqual(logika.deteksi_mood("skripsiku buntu"), "bingung")
        self.assertIsNone(logika.deteksi_mood("halo apa kabar"))

    def test_mood_yang_muncul_duluan_menang(self):
        self.assertEqual(logika.deteksi_mood("males banget, jadi sedih"), "malas")

    def test_tidak_salah_cocok_di_tengah_kata(self):
        self.assertIsNone(logika.deteksi_mood("nonton capella"))  # 'cape' ada di dalam kata lain

    def test_pilih_kutipan_sesuai_tema_mood(self):
        k = logika.pilih_kutipan(DATA, "bingung", rng=random.Random(1))
        self.assertTrue({"thinking", "choices", "truth", "life"} & set(k["tema"]))

    def test_cari_tokoh_tidak_peduli_huruf_besar(self):
        self.assertEqual(len(logika.cari_tokoh(DATA, "EINSTEIN")), 1)

    def test_statistik(self):
        s = logika.statistik(DATA)
        self.assertEqual(s["jumlah_kutipan"], 3)
        self.assertEqual(s["jumlah_tokoh"], 3)

    def test_format_kutipan_aman_untuk_html(self):
        teks = logika.format_kutipan({"teks": "a < b & c", "tokoh": "X", "tema": ["deep-thoughts"]})
        self.assertIn("a &lt; b &amp; c", teks)
        self.assertIn("#deep_thoughts", teks)


if __name__ == "__main__":
    unittest.main(verbosity=2)
