"""
media/library/ altındaki seed kütüphanesini Django'ya yükler:
  - 6 sanatçı için User (role=ARTIST, is_approved_artist=True) hesabı oluşturur.
  - Her ses dosyasını ffmpeg ile MP3 192k stereo 44.1kHz'e normalize eder
    (mp3/m4a/opus karışımı tek formata gelsin, frontend ExoPlayer hep çalsın).
  - duration ffprobe ile çıkarılır.
  - Song kaydı oluşturulur (audio_file + cover_image + genre).
  - is_fingerprinted=False bırakılır; fingerprint reingest_all.py --django ile sonra.

Kullanım (host'tan):
    cd musiki_backend
    POSTGRES_HOST=localhost POSTGRES_PORT=5433 \
    DJANGO_SETTINGS_MODULE=config.settings.dev \
    .venv/Scripts/python.exe scripts/ingest_seed.py --dry-run

Kullanım (gerçek):
    .venv/Scripts/python.exe scripts/ingest_seed.py
    .venv/Scripts/python.exe scripts/ingest_seed.py --limit 3        # ilk 3 şarkı (test)
    .venv/Scripts/python.exe scripts/ingest_seed.py --reset          # mevcut Song/User'ı sil

Notlar:
  - Script Django'yu kendisi setup eder.
  - Dry-run'da bir örnek dosyayı gerçekten ffmpeg'le çevirir, çıktı kontrol edilir.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Windows konsol UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
LIB_DIR = BASE_DIR / "media" / "library"

AUDIO_EXTS = {".mp3", ".m4a", ".opus", ".ogg", ".flac", ".wav"}

# Sanatçı meta: (username, display_name, bio, genre)
ARTISTS = [
    {
        "username": "ati242",
        "display": "Ati242",
        "first_name": "Ati242",
        "bio": "İstanbul rap sahnesinin yükselen sesi.",
        "genre": "hip_hop",
        "folder": "Ati242",
    },
    {
        "username": "duman",
        "display": "Duman",
        "first_name": "Duman",
        "bio": "Türk rock'ının ikonik gruplarından.",
        "genre": "rock",
        "folder": "Duman",
    },
    {
        "username": "manga",
        "display": "maNga",
        "first_name": "maNga",
        "bio": "Eurovision 2010 ikincisi, alternatif rock grubu.",
        "genre": "rock",
        "folder": "maNga",
    },
    {
        "username": "manifest",
        "display": "Manifest",
        "first_name": "Manifest",
        "bio": "Türkçe pop sahnesinde yeni nesil.",
        "genre": "pop",
        "folder": "Manifest",
    },
    {
        "username": "sagopa_kajmer",
        "display": "Sagopa Kajmer",
        "first_name": "Sagopa Kajmer",
        "bio": "Türk hip-hop'unun yaşayan efsanesi.",
        "genre": "hip_hop",
        "folder": "Sagopa Kajmer",
    },
    {
        "username": "sezen_aksu",
        "display": "Sezen Aksu",
        "first_name": "Sezen Aksu",
        "bio": "Türk pop müziğinin minik serçesi.",
        "genre": "pop",
        "folder": "Sezen Aksu",
    },
]

DEFAULT_PASSWORD = "musiki123"

# ──────────────────────────── Django bootstrap ────────────────────────────

def _setup_django() -> None:
    sys.path.insert(0, str(BASE_DIR))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    os.environ.setdefault("POSTGRES_HOST", "localhost")
    os.environ.setdefault("POSTGRES_PORT", "5433")
    import django
    django.setup()


# ──────────────────────────── ffmpeg/ffprobe ────────────────────────────

def _ffprobe_duration(path: Path) -> float:
    """Saniye cinsinden süre."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json", str(path),
    ]
    out = subprocess.check_output(cmd, stderr=subprocess.PIPE)
    return float(json.loads(out)["format"]["duration"])


def _normalize_to_mp3(src: Path, dst: Path) -> None:
    """src -> mp3 192kbps stereo 44.1kHz. dst .mp3 ile bitmeli."""
    cmd = [
        "ffmpeg", "-y", "-i", str(src),
        "-vn",                       # eğer kapağı embed ettiyse (m4a) at
        "-c:a", "libmp3lame",
        "-b:a", "192k",
        "-ar", "44100",
        "-ac", "2",
        str(dst),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


# ──────────────────────────── Yardımcı ────────────────────────────

def _slug(s: str) -> str:
    """ASCII slug (Django default storage çakışmaları azalsın)."""
    from django.utils.text import slugify
    out = slugify(s, allow_unicode=False)
    return out or "untitled"


def _collect_songs(folder: Path) -> list[Path]:
    return sorted(
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in AUDIO_EXTS
    )


# ──────────────────────────── Ana akış ────────────────────────────

def ensure_artist(meta: dict, dry_run: bool):
    """User (artist) bul/oluştur. Dry-run'da nesneyi yaratmaz, dict döner."""
    from users.models import User
    from django.utils import timezone

    if dry_run:
        return {
            "username": meta["username"],
            "display": meta["display"],
            "exists": User.objects.filter(username=meta["username"]).exists(),
        }

    user, created = User.objects.get_or_create(
        username=meta["username"],
        defaults={
            "first_name": meta["first_name"],
            "email": f'{meta["username"]}@musiki.local',
            "role": User.Role.ARTIST,
            "is_approved_artist": True,
            "approved_at": timezone.now(),
            "bio": meta["bio"],
        },
    )
    if created:
        user.set_password(DEFAULT_PASSWORD)
        user.save()
    return user


def ingest_artist(meta: dict, dry_run: bool, limit: int | None) -> tuple[int, int, int]:
    """Bir sanatçı için tüm şarkıları yükler. (success, skipped, failed) döner."""
    from django.core.files import File
    from music.models import Song

    folder = LIB_DIR / meta["folder"]
    if not folder.is_dir():
        print(f"[YOK] klasör: {folder}")
        return 0, 0, 0

    songs = _collect_songs(folder)
    if limit:
        songs = songs[:limit]

    artist = ensure_artist(meta, dry_run)
    label = meta["display"] if dry_run else artist.username
    print(f"\n=== {meta['display']} ({len(songs)} şarkı) — user: {label} ===")

    success = skipped = failed = 0
    for i, src in enumerate(songs, 1):
        title = src.stem
        cover = src.with_suffix(".jpg")
        has_cover = cover.exists()

        # Hedef dosya adı (Django storage çakışmasını minimize eden slug)
        slug = f"{meta['username']}__{_slug(title)}.mp3"
        cover_name = f"{meta['username']}__{_slug(title)}.jpg" if has_cover else None

        # Dry-run: sadece ne olacağını yazdır + ilk şarkı için ffmpeg sanity check
        if dry_run:
            tag = "✓cover" if has_cover else "      "
            print(f"  [{i:>3}/{len(songs)}] {tag}  {src.name}  →  songs/{slug}")
            if i == 1:
                # Pipeline test: ffprobe + ffmpeg gerçekten çalışıyor mu?
                try:
                    dur = _ffprobe_duration(src)
                    print(f"             ffprobe duration: {dur:.2f}s")
                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                        tmp_path = Path(tmp.name)
                    try:
                        _normalize_to_mp3(src, tmp_path)
                        size_kb = tmp_path.stat().st_size / 1024
                        print(f"             ffmpeg → mp3: {size_kb:.0f} KB ✓")
                    finally:
                        tmp_path.unlink(missing_ok=True)
                except Exception as e:
                    print(f"             [HATA] ffmpeg/ffprobe: {e}")
                    failed += 1
                    continue
            success += 1
            continue

        # Mevcut Song atla (idempotent)
        if Song.objects.filter(artist=artist, title=title).exists():
            print(f"  [{i:>3}/{len(songs)}] [VAR] {title}")
            skipped += 1
            continue

        t0 = time.time()
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_mp3 = Path(tmp.name)
        try:
            _normalize_to_mp3(src, tmp_mp3)
            duration = _ffprobe_duration(tmp_mp3)

            song = Song(
                title=title,
                artist=artist,
                genre=meta["genre"],
                duration=round(duration, 2),
                is_fingerprinted=False,
            )
            with open(tmp_mp3, "rb") as fh:
                song.audio_file.save(slug, File(fh), save=False)
            if has_cover:
                with open(cover, "rb") as fh:
                    song.cover_image.save(cover_name, File(fh), save=False)
            song.save()

            elapsed = time.time() - t0
            print(f"  [{i:>3}/{len(songs)}] OK id={song.id} {duration:>5.1f}s {elapsed:>4.1f}s {title}")
            success += 1
        except subprocess.CalledProcessError as e:
            print(f"  [{i:>3}/{len(songs)}] FFMPEG-ERR {title}: {e.stderr.decode('utf-8', 'ignore')[:200]}")
            failed += 1
        except Exception as e:
            print(f"  [{i:>3}/{len(songs)}] ERR {title}: {type(e).__name__}: {e}")
            failed += 1
        finally:
            tmp_mp3.unlink(missing_ok=True)

    return success, skipped, failed


def reset_existing() -> None:
    """Önceki seed run'lardan kalmış User+Song'ları sil."""
    from users.models import User
    from music.models import Song
    usernames = [m["username"] for m in ARTISTS]
    deleted_songs = Song.objects.filter(artist__username__in=usernames).delete()
    deleted_users = User.objects.filter(username__in=usernames).delete()
    print(f"[RESET] silinen: {deleted_songs} song, {deleted_users} user")


def main() -> int:
    ap = argparse.ArgumentParser(description="Seed kütüphanesini Django'ya ingest eder.")
    ap.add_argument("--dry-run", action="store_true", help="Sadece göster + bir örnek dosyayla ffmpeg pipeline'ı test et")
    ap.add_argument("--limit", type=int, default=None, help="Sanatçı başına en fazla N şarkı (test için)")
    ap.add_argument("--reset", action="store_true", help="Mevcut seed user/song'ları sil, sonra ingest et")
    ap.add_argument("--only", default=None, help="Sadece bu sanatçı (folder adı): 'Ati242' vb.")
    args = ap.parse_args()

    _setup_django()

    if args.reset and not args.dry_run:
        reset_existing()

    artists = ARTISTS
    if args.only:
        artists = [m for m in ARTISTS if m["folder"] == args.only or m["username"] == args.only]
        if not artists:
            print(f"[HATA] --only eşleşmedi: {args.only}")
            return 2

    print(f"Mod: {'DRY-RUN' if args.dry_run else 'LIVE'}    Sanatçı: {len(artists)}    Limit: {args.limit or 'yok'}")

    t_total = time.time()
    sums = [0, 0, 0]
    for meta in artists:
        s, sk, f = ingest_artist(meta, args.dry_run, args.limit)
        sums[0] += s; sums[1] += sk; sums[2] += f

    print("\n" + "=" * 60)
    print(f"TOPLAM: success={sums[0]}  skipped={sums[1]}  failed={sums[2]}")
    print(f"Süre: {time.time() - t_total:.1f}s")
    if not args.dry_run:
        print("\nSıradaki adım — fingerprint:")
        print("  python scripts/reingest_all.py --django")
    return 0


if __name__ == "__main__":
    sys.exit(main())
