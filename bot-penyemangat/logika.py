"""
logika.py — Mengolah data hasil scraping.

Isinya fungsi-fungsi biasa (tidak ada hubungannya dengan Telegram),
sehingga mudah diuji dan dipahami:
- deteksi_mood   : menebak suasana hati dari kalimat bahasa Indonesia (regex)
- pilih_kutipan  : memilih kutipan yang temanya cocok dengan mood
- cari_tokoh     : mencari kutipan berdasarkan nama tokoh
- cari_kata      : mencari kutipan yang mengandung kata tertentu
- statistik      : ringkasan data (jumlah, tokoh & tema terbanyak)
- format_kutipan : menyusun kutipan menjadi teks pesan yang rapi
"""

import random
import re
from collections import Counter
from html import escape

# Setiap mood punya: kata pemicu (bahasa Indonesia), tema kutipan yang cocok
# (tag dari situs, bahasa Inggris), emoji tombol, dan kalimat sapaan.
MOOD = {
    "capek": {
        "emoji": "😮‍💨",
        "kata": ["capek", "cape", "lelah", "letih", "penat", "lemes", "lemas"],
        "tema": ["inspirational", "life", "success"],
        "sapaan": "Lagi capek ya? Tarik napas, istirahat sebentar, lalu lanjut lagi. 💪",
    },
    "sedih": {
        "emoji": "😢",
        "kata": ["sedih", "galau", "kecewa", "patah hati", "nangis", "menangis"],
        "tema": ["life", "love", "friendship", "hope"],
        "sapaan": "Peluk dari jauh 🤗 Semoga kutipan ini sedikit menghibur.",
    },
    "malas": {
        "emoji": "🛋️",
        "kata": ["malas", "males", "mager", "gak mood", "nggak mood", "ga mood"],
        "tema": ["inspirational", "success", "change"],
        "sapaan": "Mager itu wajar, tapi yuk mulai dari langkah kecil dulu. 🚶",
    },
    "bingung": {
        "emoji": "🤔",
        "kata": ["bingung", "buntu", "stuck", "pusing", "ragu"],
        "tema": ["truth", "thinking", "choices", "life"],
        "sapaan": "Lagi buntu? Kadang jawabannya datang setelah kita berhenti sejenak.",
    },
    "cemas": {
        "emoji": "😰",
        "kata": ["cemas", "takut", "khawatir", "panik", "deg-degan", "overthinking"],
        "tema": ["courage", "inspirational", "hope", "life"],
        "sapaan": "Tenang, kamu sudah sejauh ini. Hadapi satu per satu ya. 🌱",
    },
    "bosan": {
        "emoji": "🥱",
        "kata": ["bosan", "bosen", "gabut", "jenuh"],
        "tema": ["humor", "books", "reading"],
        "sapaan": "Gabut? Nih, bacaan ringan biar nggak bosan. 📚",
    },
    "senang": {
        "emoji": "😄",
        "kata": ["senang", "seneng", "bahagia", "happy", "gembira"],
        "tema": ["humor", "friendship", "love"],
        "sapaan": "Asyik, lagi happy! Ini bonus biar makin semangat. 🎉",
    },
}

# Pola regex untuk tiap mood, dibuat sekali di awal.
# \b = batas kata, supaya "cape" tidak cocok dengan kata "capella".
_POLA_MOOD = {
    nama: re.compile(r"\b(?:" + "|".join(re.escape(k) for k in info["kata"]) + r")\b")
    for nama, info in MOOD.items()
}


def deteksi_mood(kalimat):
    """Tebak mood dari kalimat. Kalau ada beberapa, ambil yang muncul paling awal.

    >>> deteksi_mood("aku lagi capek banget")
    'capek'
    """
    kalimat = kalimat.lower()
    posisi_terdepan = None
    mood_terpilih = None
    for nama, pola in _POLA_MOOD.items():
        cocok = pola.search(kalimat)
        if cocok and (posisi_terdepan is None or cocok.start() < posisi_terdepan):
            posisi_terdepan = cocok.start()
            mood_terpilih = nama
    return mood_terpilih


def pilih_kutipan(data, mood=None, rng=random):
    """Pilih satu kutipan acak. Kalau mood diberikan, utamakan yang temanya cocok."""
    if not data:
        return None
    kandidat = data
    if mood in MOOD:
        tema_cocok = set(MOOD[mood]["tema"])
        kandidat = [k for k in data if tema_cocok & set(k["tema"])] or data
    return rng.choice(kandidat)


def cari_tokoh(data, nama):
    """Kutipan yang nama tokohnya mengandung `nama` (tidak peduli huruf besar/kecil)."""
    nama = nama.lower().strip()
    return [k for k in data if nama in k["tokoh"].lower()]


def cari_kata(data, kata):
    """Kutipan yang teksnya mengandung `kata`."""
    kata = kata.lower().strip()
    return [k for k in data if kata in k["teks"].lower()]


def statistik(data):
    """Ringkasan data: jumlah kutipan, jumlah tokoh, 5 tokoh & 5 tema terbanyak."""
    hitung_tokoh = Counter(k["tokoh"] for k in data)
    hitung_tema = Counter(t for k in data for t in k["tema"])
    return {
        "jumlah_kutipan": len(data),
        "jumlah_tokoh": len(hitung_tokoh),
        "jumlah_tema": len(hitung_tema),
        "top_tokoh": hitung_tokoh.most_common(5),
        "top_tema": hitung_tema.most_common(5),
    }


def format_kutipan(k):
    """Susun kutipan menjadi teks HTML untuk Telegram."""
    tagar = " ".join("#" + t.replace("-", "_") for t in k["tema"][:4])
    return (
        f"<i>“{escape(k['teks'])}”</i>\n\n"
        f"— <b>{escape(k['tokoh'])}</b>"
        + (f"\n{escape(tagar)}" if tagar else "")
    )
