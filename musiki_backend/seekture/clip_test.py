"""
Test script — bilinen bir şarkıdan kısa bir kesit alıp tanıma testi yapar.

Kullanım:
    cd musiki_backend
    python -m seekture.clip_test --src "media/songs/Duman - Ah.mp3" --start 30 --dur 8
    python -m seekture.clip_test --src "media/songs/Duman - Ah.mp3" --start 60 --dur 10 --db seekture.db

Önce ingest yapılmış olmalı:
    python -m seekture.ingest --dir media/songs
"""
import argparse
import os
import subprocess
import tempfile
import time

from .fingerprint import fingerprint_audio
from .matcher import find_matches_fgp
from .db_client import SQLiteClient


def clip_audio(src_path, start_sec, duration_sec):
    """ffmpeg ile şarkıdan kesit al, mono 44100 Hz WAV olarak döndür."""
    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    tmp.close()
    cmd = [
        'ffmpeg', '-y',
        '-ss', str(start_sec),
        '-t', str(duration_sec),
        '-i', src_path,
        '-ac', '1', '-ar', '44100', '-c:a', 'pcm_s16le',
        tmp.name,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return tmp.name


def main():
    parser = argparse.ArgumentParser(description='Seekture - Clip Test')
    parser.add_argument('--src', required=True, help='Kaynak sarki dosyasi')
    parser.add_argument('--start', type=float, default=30, help='Baslangic saniyesi (default: 30)')
    parser.add_argument('--dur', type=float, default=8, help='Kesit suresi saniye (default: 8)')
    parser.add_argument('--db', default='seekture.db', help='SQLite DB yolu')
    args = parser.parse_args()

    db = SQLiteClient(args.db)
    total_songs = db.get_total_songs()
    total_fp = db.get_total_fingerprints()
    print(f"DB: {total_songs} sarki, {total_fp} fingerprint\n")

    if total_songs == 0:
        print("HATA: DB bos! Once ingest yapin:")
        print("  python -m seekture.ingest --dir media/songs")
        db.close()
        return

    # Kesit al
    basename = os.path.basename(args.src)
    print(f"Kaynak: {basename}")
    print(f"Kesit:  {args.start}s - {args.start + args.dur}s ({args.dur}s)\n")

    clip_path = clip_audio(args.src, args.start, args.dur)

    try:
        # Fingerprint
        print("Fingerprint cikariliyor...")
        t0 = time.time()
        fps = fingerprint_audio(clip_path, 0)
        fp_time = time.time() - t0
        print(f"  {len(fps)} fingerprint ({fp_time:.2f}s)\n")

        if len(fps) == 0:
            print("HATA: Hic fingerprint cikarilmadi! Kesit cok kisa olabilir.")
            return

        # address -> anchor_time_ms
        sample_map = {addr: c.anchor_time_ms for addr, c in fps.items()}

        # Eslestirme
        print("Eslestirme yapiliyor...")
        t0 = time.time()
        matches = find_matches_fgp(sample_map, db)
        match_time = time.time() - t0

        print(f"\n{'=' * 60}")
        print(f"  SONUCLAR ({match_time:.2f}s)")
        print(f"{'=' * 60}")

        if matches:
            expected = basename.rsplit('.', 1)[0]  # "Duman - Ah"
            top = matches[0]
            top_name = f"{top['artist']} - {top['title']}"

            for i, m in enumerate(matches[:10]):
                marker = " <-- BEKLENEN" if f"{m['artist']} - {m['title']}" == expected else ""
                print(f"  {i + 1}. {m['artist']:15s} - {m['title']:25s}  "
                      f"skor: {m['score']:.0f}{marker}")

            print(f"{'=' * 60}")

            if top_name == expected:
                print(f"\n  BASARILI! Dogru sarki bulundu: {top_name}")
            else:
                print(f"\n  HATALI! Beklenen: {expected}")
                print(f"          Bulunan:  {top_name}")
        else:
            print("  Eslestirme bulunamadi!")
            print(f"{'=' * 60}")

    finally:
        os.unlink(clip_path)

    db.close()


if __name__ == '__main__':
    main()
