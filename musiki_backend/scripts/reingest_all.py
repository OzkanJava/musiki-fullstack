"""
Tum sarkilarin fingerprint'lerini yeniden olustur.

Varsayilan: Django ORM modu — Song tablosunu dolasir, ingest_song servisi
ile her sarkinin fingerprint'ini cikarir, seekture.db'ye yazar.

Kullanim (host'ta venv ile):
    cd musiki_backend
    .venv/Scripts/python.exe scripts/reingest_all.py
        # POSTGRES_HOST=localhost, POSTGRES_PORT=5433,
        # DJANGO_SETTINGS_MODULE=config.settings.dev otomatik set edilir.

Bayraklar:
    --standalone        : Django'suz, "Artist - Title.mp3" patternli klasor tarar
    --songs-dir DIR     : standalone modda klasor (default: media/songs)
    --db PATH           : seekture sqlite (default: settings.SEEKTURE_DB_PATH)
    --no-backup         : seekture.db yedegini atla
    --only-missing      : Sadece is_fingerprinted=False olan sarkilari isle
    --limit N           : Ilk N sarki (test icin)
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import time

# Windows konsol UTF-8 (Türkçe karakterler için)
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# scripts/ alt klasöründen çalıştırıldığında config/ modülünün bulunabilmesi için.
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

# Host'tan çalıştırıldığında postgres docker'a (5433) ve dev settings'e otomatik bağlan.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5433")


def _convert_to_wav(input_path: str) -> str:
    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    tmp.close()
    subprocess.run(
        ['ffmpeg', '-y', '-i', input_path,
         '-ac', '1', '-ar', '44100', '-c:a', 'pcm_s16le', tmp.name],
        capture_output=True, check=True,
    )
    return tmp.name


def reingest_standalone(songs_dir: str, db_path: str, backup: bool = True) -> None:
    """
    Django'suz reingest. media/songs/*.mp3 dosyalarindan 'Artist - Title.mp3'
    paternini kullanarak seekture DB'yi yeniden olusturur.

    DB'deki mevcut song ID'leri korunmaya calisilir (title+artist eslesmesi).
    """
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from seekture.fingerprint import fingerprint_audio_full
    from seekture.db_client import SQLiteClient

    if backup and os.path.exists(db_path):
        backup_path = db_path + '.bak_' + time.strftime('%Y%m%d_%H%M%S')
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"[OK] DB yedek: {backup_path}")

    db = SQLiteClient(db_path)

    # Mevcut song (title, artist) -> id haritasini koru
    existing = {
        (r[1], r[2].lower()): r[0]
        for r in db.conn.execute('SELECT id, title, artist FROM songs').fetchall()
    }
    print(f"[INFO] Mevcut DB: {len(existing)} song kaydi var")

    # Tum fingerprint'leri sil
    db.conn.execute('DELETE FROM fingerprints')
    db.conn.commit()
    print(f"[INFO] Eski fingerprint'ler temizlendi")

    files = sorted([
        f for f in os.listdir(songs_dir)
        if f.lower().endswith(('.mp3', '.wav', '.flac', '.ogg', '.m4a'))
    ])

    print(f"[INFO] {len(files)} dosya islenecek")
    print("=" * 80)

    success = 0
    skipped = 0
    failed = 0
    total_fps = 0
    t_start = time.time()

    for i, fname in enumerate(files, 1):
        stem = fname.rsplit('.', 1)[0]
        if ' - ' not in stem:
            print(f"[{i}/{len(files)}] SKIP (pattern): {fname}")
            skipped += 1
            continue

        artist, title = stem.split(' - ', 1)
        key = (title, artist.lower())

        if key not in existing:
            # Yeni sarki — insert et
            sid = db.store_song(title, artist.lower())
            existing[key] = sid
            print(f"[{i}/{len(files)}] NEW song_id={sid}: {fname}")
        else:
            sid = existing[key]

        # Fingerprint uret
        path = os.path.join(songs_dir, fname)
        t0 = time.time()
        wav_path = None
        try:
            if not path.lower().endswith('.wav'):
                wav_path = _convert_to_wav(path)
            else:
                wav_path = path

            fps = fingerprint_audio_full(wav_path, sid)

            if wav_path != path and os.path.exists(wav_path):
                os.unlink(wav_path)

            if not fps:
                print(f"[{i}/{len(files)}] FAIL (no fps): {fname}")
                failed += 1
                continue

            db.store_fingerprints(fps)
            elapsed = time.time() - t0
            total_fps += len(fps)
            success += 1
            print(f"[{i}/{len(files)}] OK id={sid} fps={len(fps):>5} "
                  f"t={elapsed:.1f}s  {fname}")
        except Exception as e:
            if wav_path and wav_path != path and os.path.exists(wav_path):
                os.unlink(wav_path)
            print(f"[{i}/{len(files)}] ERR: {fname}  {type(e).__name__}: {e}")
            failed += 1

    total_time = time.time() - t_start
    db.close()

    print("=" * 80)
    print(f"TAMAMLANDI: success={success}  skipped={skipped}  failed={failed}")
    print(f"Toplam fingerprint: {total_fps}")
    print(f"Toplam sure: {total_time:.1f}s ({total_time/60:.1f} dk)")


def reingest_django(only_missing: bool = False, limit: int | None = None,
                    backup: bool = True) -> None:
    """Django ORM ile reingest — Song.objects üzerinde döner."""
    import django
    django.setup()

    from django.conf import settings as dj_settings
    from music.models import Song
    from music.services.ingest import ingest_song
    from seekture.db_client import SQLiteClient

    db_path = getattr(dj_settings, 'SEEKTURE_DB_PATH', 'seekture.db')
    if backup and os.path.exists(db_path):
        import shutil
        backup_path = db_path + '.bak_' + time.strftime('%Y%m%d_%H%M%S')
        shutil.copy2(db_path, backup_path)
        print(f"[OK] DB yedek: {backup_path}")

    # Tüm fingerprint'leri sil. only-missing modunda da, çünkü kısmi durum tutarsız olabilir.
    # only-missing: sadece yeni Song'lar için ingest çalıştır — eski FP'ler korunur.
    db = SQLiteClient(db_path)
    if not only_missing:
        db.conn.execute('DELETE FROM fingerprints')
        db.conn.commit()
        print('[INFO] Eski fingerprintler temizlendi')
    db.close()

    qs = Song.objects.select_related('artist').order_by('id')
    if only_missing:
        qs = qs.filter(is_fingerprinted=False)
    if limit:
        qs = qs[:limit]

    songs = list(qs)
    total = len(songs)
    if total == 0:
        print('[INFO] İşlenecek şarkı yok.')
        return

    print(f'[INFO] {total} şarkı işlenecek (only_missing={only_missing}, limit={limit or "yok"})')
    print('=' * 80)

    ok = 0
    failed = 0
    total_fps = 0
    t_start = time.time()

    for i, song in enumerate(songs, 1):
        t0 = time.time()
        try:
            count = ingest_song(song)
            elapsed = time.time() - t0
            if count > 0:
                ok += 1
                total_fps += count
                # Kalan süre tahmini
                avg = (time.time() - t_start) / i
                eta = avg * (total - i)
                print(f'[{i}/{total}] OK id={song.id} fps={count:>5} '
                      f't={elapsed:>4.1f}s eta={eta/60:>4.1f}dk  {song.title}')
            else:
                failed += 1
                print(f'[{i}/{total}] FAIL (no fps) id={song.id}: {song.title}')
        except Exception as e:
            failed += 1
            print(f'[{i}/{total}] ERR id={song.id} {song.title}: {type(e).__name__}: {e}')

    total_time = time.time() - t_start
    print('=' * 80)
    print(f'TAMAMLANDI: ok={ok}  failed={failed}  fingerprint={total_fps}')
    print(f'Süre: {total_time:.1f}s ({total_time/60:.1f} dk)')


def main() -> None:
    parser = argparse.ArgumentParser(description='Seekture Full Reingest (default: Django modu)')
    parser.add_argument('--standalone', action='store_true',
                        help='Django\'suz, klasör tarama modu')
    parser.add_argument('--songs-dir', default='media/songs',
                        help='Standalone modda şarkı klasörü')
    parser.add_argument('--db', default='seekture.db',
                        help='SQLite DB yolu (sadece standalone modda)')
    parser.add_argument('--no-backup', action='store_true',
                        help='seekture.db yedeklemesini atla')
    parser.add_argument('--only-missing', action='store_true',
                        help='Sadece is_fingerprinted=False olanları işle (Django mod)')
    parser.add_argument('--limit', type=int, default=None,
                        help='İlk N şarkı (test için, Django mod)')
    args = parser.parse_args()

    if args.standalone:
        reingest_standalone(args.songs_dir, args.db, backup=not args.no_backup)
    else:
        reingest_django(
            only_missing=args.only_missing,
            limit=args.limit,
            backup=not args.no_backup,
        )


if __name__ == '__main__':
    main()
