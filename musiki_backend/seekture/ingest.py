"""
Şarkı ingest script — seek-tune/server/cmdHandlers.go save() portuna karşılık gelir.

Kullanım:
    cd musiki_backend
    python -m seekture.ingest --dir media/songs
    python -m seekture.ingest --file "media/songs/Duman - Ah.mp3"
    python -m seekture.ingest --dir media/songs --db test.db

Şarkı dosyaları "Artist - Title.ext" formatında olmalı.
WAV olmayan dosyalar ffmpeg ile 44100 Hz mono PCM'e dönüştürülür.
"""
import argparse
import os
import re
import subprocess
import tempfile
import time

from .fingerprint import fingerprint_audio_full
from .db_client import SQLiteClient


def convert_to_wav(input_path):
    """ffmpeg ile mono 44100 Hz 16-bit PCM WAV'a dönüştür."""
    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    tmp.close()
    cmd = [
        'ffmpeg', '-y', '-i', input_path,
        '-ac', '1', '-ar', '44100', '-c:a', 'pcm_s16le',
        tmp.name,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return tmp.name


def parse_filename(filename):
    """'Artist - Title.ext' -> (artist, title)"""
    name = os.path.splitext(filename)[0]
    m = re.match(r'^(.+?)\s*-\s*(.+)$', name)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return "Unknown", name.strip()


def ingest_file(db, file_path):
    filename = os.path.basename(file_path)
    artist, title = parse_filename(filename)

    song_id = db.store_song(title, artist)
    print(f"  [{song_id}] {artist} - {title}")

    # WAV'a dönüştür (gerekirse)
    need_cleanup = False
    if not file_path.lower().endswith('.wav'):
        wav_path = convert_to_wav(file_path)
        need_cleanup = True
    else:
        wav_path = file_path

    try:
        t0 = time.time()
        fps = fingerprint_audio_full(wav_path, song_id)
        elapsed = time.time() - t0

        db.store_fingerprints(fps)
        print(f"    {len(fps)} fingerprint, {elapsed:.1f}s")
    finally:
        if need_cleanup:
            os.unlink(wav_path)


AUDIO_EXTENSIONS = ('.wav', '.mp3', '.flac', '.m4a', '.ogg', '.opus')


def main():
    parser = argparse.ArgumentParser(description='Seekture - Ingest')
    parser.add_argument('--dir', help='Sarki klasoru')
    parser.add_argument('--file', help='Tek sarki dosyasi')
    parser.add_argument('--db', default='seekture.db', help='SQLite DB yolu')
    args = parser.parse_args()

    db = SQLiteClient(args.db)

    if args.file:
        ingest_file(db, args.file)
    elif args.dir:
        files = sorted([
            os.path.join(args.dir, f)
            for f in os.listdir(args.dir)
            if f.lower().endswith(AUDIO_EXTENSIONS)
        ])
        print(f"{len(files)} dosya bulundu.\n")
        for f in files:
            ingest_file(db, f)
        print(f"\nToplam: {db.get_total_songs()} sarki, "
              f"{db.get_total_fingerprints()} fingerprint DB'de.")
    else:
        parser.print_help()

    db.close()


if __name__ == '__main__':
    main()
