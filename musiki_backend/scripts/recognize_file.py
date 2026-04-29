"""
Tek dosya taninma test scripti.

KULLANIM:
    1) Asagidaki KONFIG bolumunde FILE_PATH'i test edecegin dosyaya yonlendir.
    2) Istersen START / DUR ile kesit al (None = tum dosya).
    3) Calistir:
          cd musiki_backend
          python -m scripts.recognize_file
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seekture.fingerprint import fingerprint_audio
from seekture.matcher import (
    find_matches_fgp,
    OFFSET_BUCKET_MS,
    MIN_SCORE_ABSOLUTE,
    MIN_SCORE_RATIO,
    MEDIUM_SCORE_ABSOLUTE,
    MEDIUM_SCORE_RATIO,
    HIGH_SCORE_ABSOLUTE,
    HIGH_SCORE_RATIO,
)
from seekture.db_client import SQLiteClient


# ═════════════════════════ KONFIG — BURAYI DEGISTIR ═════════════════════════

# Test edilecek dosyanin yolu (mp3 / wav / m4a / flac / ogg)
FILE_PATH = r"C:\Users\ozkan\Documents\Ses Kayıtları\Kayıt (13).wav"

# Kesit ayari (None = dosyanin tamami)
START_SEC: float | None = 0   # kacinci saniyeden baslasin; None = 0
DUR_SEC:   float | None = None   # kac saniye alsin;            None = sonuna kadar

# Gosterilecek top eslesme sayisi
TOP_N = 10

# Fingerprint veritabani
DB_PATH = "seekture.db"

# Terminalin ANSI renklerini destekliyorsa True yap (Windows cmd genellikle desteklemez)
USE_COLOR = False

# ════════════════════════════════════════════════════════════════════════════


def to_wav(input_path: str, start: float | None, dur: float | None) -> str:
    """ffmpeg ile mono 44100Hz 16-bit PCM WAV'a donustur. Opsiyonel kesit."""
    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    tmp.close()
    cmd = ['ffmpeg', '-y']
    if start is not None:
        cmd += ['-ss', str(start)]
    cmd += ['-i', input_path]
    if dur is not None:
        cmd += ['-t', str(dur)]
    cmd += ['-ac', '1', '-ar', '44100', '-c:a', 'pcm_s16le', tmp.name]
    subprocess.run(cmd, capture_output=True, check=True)
    return tmp.name


def quality_color(q: str) -> str:
    if not USE_COLOR:
        return ''
    return {
        'HIGH':     '\033[92m',  # parlak yesil
        'MEDIUM':   '\033[93m',  # parlak sari
        'LOW':      '\033[33m',  # sari
        'REJECTED': '\033[91m',  # parlak kirmizi
    }.get(q, '')


RESET = '\033[0m' if USE_COLOR else ''


def hr(char: str = '-', width: int = 82) -> str:
    return char * width


def banner(title: str, char: str = '=', width: int = 82) -> str:
    pad = max(0, (width - len(title) - 2) // 2)
    return char * pad + ' ' + title + ' ' + char * (width - pad - len(title) - 2)


def classify_explain(quality: str) -> str:
    return {
        'HIGH':     'Kesin eslesme — UI yesil/Check gosterir.',
        'MEDIUM':   'Muhtemel eslesme — UI sari/Uyari gosterir.',
        'LOW':      'Zayif eslesme — UI dusuk guven uyarisi gosterir.',
        'REJECTED': 'API null doner — kullaniciya "eslesme yok" mesaji gider.',
    }.get(quality, '(bilinmeyen)')


def main() -> None:
    # ── 0. Dogrulamalar ─────────────────────────────────────────────
    if not os.path.isfile(FILE_PATH):
        print(f"[HATA] Dosya bulunamadi: {FILE_PATH}")
        print(f"       CWD: {os.getcwd()}")
        print(f"       Script icindeki FILE_PATH'i kontrol et.")
        sys.exit(1)

    if not os.path.isfile(DB_PATH):
        print(f"[HATA] Fingerprint DB bulunamadi: {DB_PATH}")
        sys.exit(1)

    file_size_mb = os.path.getsize(FILE_PATH) / (1024 * 1024)

    print()
    print(banner("MUSIKI TANIMA TESTI"))
    print()
    print(f"  Dosya    : {FILE_PATH}")
    print(f"  Boyut    : {file_size_mb:.2f} MB")
    if START_SEC is not None or DUR_SEC is not None:
        s = f"{START_SEC:.1f}s" if START_SEC is not None else "0.0s"
        d = f"{DUR_SEC:.1f}s" if DUR_SEC is not None else "sonuna kadar"
        print(f"  Kesit    : {s} itibaren, {d}")
    else:
        print(f"  Kesit    : tam dosya")
    print(f"  Veritabani: {DB_PATH}")
    print(hr())

    # ── 1. WAV'a donustur ───────────────────────────────────────────
    print("  [1/3] ffmpeg ile WAV'a donusturuluyor...")
    t0 = time.time()
    try:
        wav_path = to_wav(FILE_PATH, START_SEC, DUR_SEC)
    except subprocess.CalledProcessError as e:
        print(f"[HATA] ffmpeg basarisiz:")
        print(e.stderr.decode(errors='ignore')[:500])
        sys.exit(2)
    t_ffmpeg = time.time() - t0
    wav_size_kb = os.path.getsize(wav_path) / 1024
    print(f"        OK — {wav_size_kb:.1f} KB, {t_ffmpeg:.2f}s")

    # ── 2. Fingerprint ──────────────────────────────────────────────
    print("  [2/3] Fingerprint uretiliyor (spectrogram + peak + hash)...")
    t0 = time.time()
    try:
        fps = fingerprint_audio(wav_path, 0)
    finally:
        if os.path.exists(wav_path):
            os.unlink(wav_path)
    t_fingerprint = time.time() - t0

    if not fps:
        print()
        print(hr('!'))
        print("  SONUC: HIC FINGERPRINT URETILMEDI")
        print("  Sebep: Ses cok sessiz (silence gate tetiklendi) veya dosya bozuk.")
        print("         Algoritma bu girdiyi muzik olarak kabul etmiyor.")
        print(hr('!'))
        return

    print(f"        OK — {len(fps)} benzersiz hash, {t_fingerprint:.2f}s")

    # ── 3. Match ────────────────────────────────────────────────────
    print("  [3/3] Veritabaninda aranıyor...")
    t0 = time.time()
    db = SQLiteClient(DB_PATH)
    total_songs = db.get_total_songs()
    total_fps_in_db = db.get_total_fingerprints()
    sample_map = {a: c.anchor_time_ms for a, c in fps.items()}
    matches = find_matches_fgp(sample_map, db)
    t_match = time.time() - t0
    db.close()
    print(f"        OK — {len(matches)} aday sarki, {t_match:.2f}s")

    # ── SONUC BASLIGI ───────────────────────────────────────────────
    print()
    print(banner("SONUC"))
    print()

    if not matches:
        print("  ESLESME YOK")
        print("  Fingerprint uretildi ama DB'deki hicbir sarki ile ortusmedi.")
        print()
        print(f"  DB'de {total_songs} sarki, {total_fps_in_db:,} fingerprint var.")
        return

    best = matches[0]
    quality = best.get('match_quality', 'UNKNOWN')
    score = int(best['score'])
    ratio = best.get('ratio', 0.0)
    ratio_str = f"{ratio:.2f}x" if ratio != float('inf') else "sonsuz"
    relative = score / len(fps) if len(fps) > 0 else 0.0

    color = quality_color(quality)

    if quality == 'REJECTED':
        print(f"  >> {color}REDDEDILDI{RESET} — Guvenilir eslesme bulunamadi.")
        print()
        print(f"  En yakin aday    : {best['artist']} - {best['title']}")
        print(f"  Aday skoru       : {score}")
        print(f"  Ratio (top/2nd)  : {ratio_str}")
        print(f"  Neden reddedildi : skor < {MIN_SCORE_ABSOLUTE} veya ratio < {MIN_SCORE_RATIO}")
        print()
        print(f"  (API seviyesinde song: null doner — FP korumasi devrede)")
    else:
        print(f"  {color}>> {quality} GUVEN{RESET}")
        print()
        print(f"     {best['artist']} - {best['title']}")
        print()
        print(f"  Skor                 : {score}  ({score} hash dogru hizalama buldu)")
        print(f"  Relative confidence  : {relative:.1%}  (skor / toplam query hash)")
        print(f"  Ratio (top/2.)       : {ratio_str}  (gercek eslesmede >5x bekleriz)")
        print(f"  DB song_id           : {best['song_id']}")
        print(f"  DB timestamp         : {best.get('timestamp', 0)} ms")
        print(f"  Anlami               : {classify_explain(quality)}")

    # ── TUM TOP N ────────────────────────────────────────────────
    print()
    print(hr())
    n = min(TOP_N, len(matches))
    print(f"  Ust {n} eslesme (skora gore azalan):")
    print()
    print(f"  {'#':>2}  {'SKOR':>5}  {'2.SKOR':>6}  {'RATIO':>7}  {'KALITE':>9}  ESLESME")
    print(f"  {'-'*2}  {'-'*5}  {'-'*6}  {'-'*7}  {'-'*9}  {'-'*50}")
    for i, m in enumerate(matches[:n], 1):
        q = m.get('match_quality', '?')
        c = quality_color(q)
        r = m.get('ratio', 0.0)
        r_str = f"{r:.2f}x" if r != float('inf') else "inf"
        s2 = int(m.get('second_score', 0))
        title = m['title']
        if len(title) > 48:
            title = title[:45] + '...'
        print(f"  {i:>2}  {int(m['score']):>5}  {s2:>6}  {r_str:>7}  "
              f"{c}{q:>9}{RESET}  {m['artist']} - {title}")

    # ── METRIK OZETI ────────────────────────────────────────────────
    print()
    print(hr())
    print(f"  Zamanlamalar  : ffmpeg {t_ffmpeg:.2f}s  "
          f"fingerprint {t_fingerprint:.2f}s  "
          f"match {t_match:.2f}s  "
          f"(toplam {t_ffmpeg + t_fingerprint + t_match:.2f}s)")
    print(f"  Query hash    : {len(fps)}  (sessizlik gate'i gecti)")
    print(f"  DB istatistik : {total_songs} sarki, {total_fps_in_db:,} fingerprint")
    print(f"  Kalite esigi  : MIN_SCORE={MIN_SCORE_ABSOLUTE}  "
          f"MIN_RATIO={MIN_SCORE_RATIO}  BUCKET={OFFSET_BUCKET_MS}ms  "
          f"(REJECTED = bunlarin altinda)")

    # ── EGITIM BILGISI ──────────────────────────────────────────────
    print()
    print(hr())
    print("  KALITE SINIFLARI:")
    print(f"    HIGH      : skor >= {HIGH_SCORE_ABSOLUTE} VE ratio >= {HIGH_SCORE_RATIO}  (studio eslesme)")
    print(f"    MEDIUM    : skor >= {MEDIUM_SCORE_ABSOLUTE}  VE ratio >= {MEDIUM_SCORE_RATIO}  (guvenli eslesme)")
    print(f"    LOW       : skor >= {MIN_SCORE_ABSOLUTE}  VE ratio >= {MIN_SCORE_RATIO}  (gercek dunya mic kaydi)")
    print(f"    REJECTED  : yukaridakilerden biri saglanmazsa  (sahte eslesme riski)")
    print()


if __name__ == '__main__':
    main()
