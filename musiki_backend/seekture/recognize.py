"""
Şarkı tanıma test script — seek-tune/server/shazam/shazam.go FindMatches portuna karşılık gelir.

Kullanım:
    cd musiki_backend
    python -m seekture.recognize --file kayit.wav
    python -m seekture.recognize --file kayit.mp3 --db seekture.db

Kayıt dosyası herhangi bir formatta olabilir (ffmpeg dönüştürür).
"""
import argparse
import os
import subprocess
import tempfile
import time

from .fingerprint import fingerprint_audio
from .matcher import find_matches_fgp
from .db_client import SQLiteClient


def convert_to_wav(input_path):
    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    tmp.close()
    cmd = [
        'ffmpeg', '-y', '-i', input_path,
        '-ac', '1', '-ar', '44100', '-c:a', 'pcm_s16le',
        tmp.name,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return tmp.name


def main():
    parser = argparse.ArgumentParser(description='Seekture - Recognize')
    parser.add_argument('--file', required=True, help='Ses kaydi dosyasi')
    parser.add_argument('--db', default='seekture.db', help='SQLite DB yolu')
    args = parser.parse_args()

    db = SQLiteClient(args.db)
    print(f"DB'de {db.get_total_songs()} sarki, "
          f"{db.get_total_fingerprints()} fingerprint var.\n")

    # WAV'a dönüştür (gerekirse)
    need_cleanup = False
    if not args.file.lower().endswith('.wav'):
        print("Dosya WAV'a donusturuluyor...")
        wav_path = convert_to_wav(args.file)
        need_cleanup = True
    else:
        wav_path = args.file

    try:
        # Fingerprint çıkart (dummy song_id=0)
        print("Fingerprint cikariliyor...")
        t0 = time.time()
        fps = fingerprint_audio(wav_path, 0)
        fp_time = time.time() - t0
        print(f"  {len(fps)} fingerprint ({fp_time:.1f}s)\n")

        # address -> anchor_time_ms
        sample_map = {addr: c.anchor_time_ms for addr, c in fps.items()}

        # Eşleşme ara
        print("Eslestirme yapiliyor...")
        t0 = time.time()
        matches = find_matches_fgp(sample_map, db)
        match_time = time.time() - t0

        if matches:
            print(f"\n{'=' * 55}")
            print(f"  SONUCLAR ({match_time:.2f}s)")
            print(f"{'=' * 55}")
            for i, m in enumerate(matches[:10]):
                print(f"  {i + 1}. {m['title']:30s} - {m['artist']:15s}  "
                      f"(skor: {m['score']:.0f})")
            print(f"{'=' * 55}")
        else:
            print("\n  Eslestirme bulunamadi.")

    finally:
        if need_cleanup:
            os.unlink(wav_path)

    db.close()


if __name__ == '__main__':
    main()
