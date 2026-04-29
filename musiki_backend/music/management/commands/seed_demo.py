"""
Mezuniyet sunumu icin demo veri olusturur.

Yapilanlar:
  1) Tum DB temizlenir (superuser'lar korunur), seekture.db sifirlanir
  2) 6 sanatci hesabi acilir (Manifest, Ati242, Duman, maNga, Sezen Aksu, Sagopa Kajmer)
  3) Sanatci basina 1 'Best of {Sanatci}' albumu olusturulur
  4) media/songs/ altindaki MP3'ler dosya adindan parse edilip uygun sanatciya/albuma baglanir
  5) Her sarki icin iTunes Search API'den cover image cekilir (artist fallback'li)
  6) 3 demo listener (ali, ayse, mehmet) ve sosyal aktivite (like/follow/playlist/history) eklenir
  7) Eksik kalan cover'lar cover_failures.log dosyasina yazilir

Kullanim:
    python manage.py seed_demo
    python manage.py seed_demo --no-fingerprint   # fingerprint atla (hizli)
    python manage.py seed_demo --skip-covers      # iTunes'a hic gitme (test)
"""
import os
import re
import sqlite3
import time
import random
import logging
import unicodedata
from pathlib import Path
from datetime import timedelta

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from music.models import (
    Song, Album, Fingerprint, ListenHistory,
    SongLike, AlbumLike, ArtistFollow,
    Playlist, PlaylistItem,
)
from music.services.ingest import ingest_song

User = get_user_model()
logger = logging.getLogger(__name__)

SUPPORTED_EXTS = ('.mp3', '.wav', '.flac', '.ogg', '.m4a')
FILENAME_PATTERN = re.compile(r'^(.+?)\s+-\s+(.+?)(\.\w+)$')

ARTIST_MAP = [
    {"prefix": "Manifest",      "username": "manifest",      "display": "Manifest",      "genre": "hip_hop"},
    {"prefix": "Ati242",        "username": "ati242",        "display": "Ati242",        "genre": "hip_hop"},
    {"prefix": "Duman",         "username": "duman",         "display": "Duman",         "genre": "rock"},
    {"prefix": "maNga",         "username": "manga",         "display": "maNga",         "genre": "rock"},
    {"prefix": "Sezen Aksu",    "username": "sezen_aksu",    "display": "Sezen Aksu",    "genre": "pop"},
    {"prefix": "Sagopa Kajmer", "username": "sagopa_kajmer", "display": "Sagopa Kajmer", "genre": "hip_hop"},
]

DEMO_USERS = [
    {"username": "ali",     "first_name": "Ali",     "bio": "Rock ve rap dinleyicisi"},
    {"username": "ayse",    "first_name": "Ayşe",    "bio": "Pop ve Türkçe rock"},
    {"username": "mehmet",  "first_name": "Mehmet",  "bio": "Her tür müzik"},
]

ITUNES_SEARCH = "https://itunes.apple.com/search"
ITUNES_TIMEOUT = 10
COVER_FAIL_LOG = Path(settings.BASE_DIR) / 'cover_failures.log'


def _slug(s: str, maxlen: int = 60) -> str:
    """Dosya adi icin guvenli ASCII slug (Turkce karakterler de dahil)."""
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    s = re.sub(r'[^\w\s-]', '', s).strip().lower()
    s = re.sub(r'[\s_]+', '-', s)
    return s[:maxlen] or 'cover'


def _itunes_get(params: dict) -> list:
    """iTunes Search API cagrisi, hatada bos liste doner."""
    try:
        r = requests.get(ITUNES_SEARCH, params=params, timeout=ITUNES_TIMEOUT)
        if r.status_code != 200:
            return []
        return r.json().get('results', [])
    except Exception as e:
        logger.warning(f"iTunes call failed: {e}")
        return []


def _itunes_find_song(artist: str, title: str) -> dict | None:
    """
    Sarki icin iTunes match. Once TR store, sonra global. Sanatci adi fuzzy match.
    """
    norm_artist = artist.lower()
    for country in ('tr', None):
        params = {
            'term': f"{artist} {title}",
            'entity': 'song',
            'limit': 5,
        }
        if country:
            params['country'] = country
        results = _itunes_get(params)
        match = next(
            (r for r in results if norm_artist in r.get('artistName', '').lower()),
            None,
        )
        if match:
            return match
    return None


def _itunes_artist_default_cover_url(artist: str) -> str | None:
    """Sanatcinin en populer sarkisinin cover URL'i (600x600)."""
    for country in ('tr', None):
        params = {'term': artist, 'entity': 'song', 'limit': 1}
        if country:
            params['country'] = country
        results = _itunes_get(params)
        if results and results[0].get('artworkUrl100'):
            return results[0]['artworkUrl100'].replace('100x100', '600x600')
    return None


def _download_bytes(url: str) -> bytes | None:
    try:
        r = requests.get(url, timeout=ITUNES_TIMEOUT)
        if r.status_code == 200:
            return r.content
    except Exception:
        pass
    return None


def _save_cover(img_bytes: bytes, subdir: str, slug: str) -> str:
    """Bytes'i media/covers/{subdir}/{slug}.jpg olarak kaydet, relative path don."""
    rel_dir = Path('covers') / subdir
    abs_dir = Path(settings.MEDIA_ROOT) / rel_dir
    abs_dir.mkdir(parents=True, exist_ok=True)
    rel_path = rel_dir / f"{slug}.jpg"
    abs_path = Path(settings.MEDIA_ROOT) / rel_path
    abs_path.write_bytes(img_bytes)
    return str(rel_path).replace('\\', '/')


def _log_cover_failure(kind: str, artist: str, title: str, note: str = ''):
    try:
        with open(COVER_FAIL_LOG, 'a', encoding='utf-8') as f:
            f.write(f"{kind} | {artist} | {title} | {note}\n")
    except Exception:
        pass


class Command(BaseCommand):
    help = 'Demo verisi olusturur: 6 sanatci, Best Of albumler, iTunes cover, demo kullanicilar.'

    def add_arguments(self, parser):
        parser.add_argument('--no-fingerprint', action='store_true',
                            help='Fingerprint olusturmayi atla (hizli mod)')
        parser.add_argument('--skip-covers', action='store_true',
                            help="iTunes API'ye gitme, cover'siz birak (test)")

    def handle(self, *args, **opts):
        self.skip_covers = opts['skip_covers']
        self.skip_fingerprint = opts['no_fingerprint']

        # Cover fail log'unu sifirla
        if COVER_FAIL_LOG.exists():
            COVER_FAIL_LOG.unlink()

        self.stdout.write(self.style.WARNING('=== Musiki Demo Seed ===\n'))

        self._clear_db()
        self._clear_seekture()
        artists = self._create_artists()
        artist_default_covers = self._fetch_artist_default_covers(artists)
        albums = self._create_albums(artists, artist_default_covers)
        songs_by_artist = self._ingest_songs(artists, albums, artist_default_covers)
        demo_users = self._create_demo_users()
        self._seed_social(demo_users, artists, songs_by_artist)

        self.stdout.write(self.style.SUCCESS('\n=== Tamamlandi ==='))
        self._print_summary()

    # ── 1. DB Temizleme ────────────────────────────────────────────────────

    def _clear_db(self):
        self.stdout.write('1) PostgreSQL verisi temizleniyor...')

        PlaylistItem.objects.all().delete()
        Playlist.all_objects.all().hard_delete()
        SongLike.objects.all().delete()
        AlbumLike.objects.all().delete()
        ArtistFollow.objects.all().delete()
        ListenHistory.objects.all().delete()
        Fingerprint.objects.all().delete()
        Song.all_objects.all().hard_delete()
        Album.all_objects.all().hard_delete()
        deleted_users, _ = User.all_objects.filter(is_superuser=False).hard_delete()

        self.stdout.write(f'   Silindi: {deleted_users} kullanici (superuser korundu) + tum muzik/sosyal veri')

    def _clear_seekture(self):
        self.stdout.write('2) seekture.db temizleniyor...')
        db_path = getattr(settings, 'SEEKTURE_DB_PATH', None)
        if not db_path or not os.path.exists(db_path):
            self.stdout.write('   seekture.db bulunamadi, atlanıyor.')
            return
        conn = sqlite3.connect(db_path)
        try:
            fp = conn.execute('DELETE FROM fingerprints').rowcount
            sg = conn.execute('DELETE FROM songs').rowcount
            conn.commit()
            self.stdout.write(f'   Silindi: {fp} fingerprint, {sg} seekture sarki kaydi')
        finally:
            conn.close()

    # ── 2. Sanatci Hesaplari ───────────────────────────────────────────────

    def _create_artists(self) -> dict:
        self.stdout.write('3) Sanatci hesaplari olusturuluyor...')
        artists = {}
        for a in ARTIST_MAP:
            user = User.objects.create(
                username=a['username'],
                first_name=a['display'],
                role='artist',
                is_approved_artist=True,
                bio=f"{a['display']} - Musiki sanatcisi",
            )
            user.set_password('Artist123!')
            user.save()
            artists[a['prefix']] = {'user': user, 'genre': a['genre'], 'display': a['display']}
            self.stdout.write(f"   [+] {a['username']} (sifre: Artist123!)")
        return artists

    # ── 3. Sanatci Default Cover (iTunes) ──────────────────────────────────

    def _fetch_artist_default_covers(self, artists: dict) -> dict:
        if self.skip_covers:
            self.stdout.write('4) Sanatci default cover ATLA (--skip-covers)')
            return {prefix: None for prefix in artists}

        self.stdout.write('4) Sanatci default cover\'lari iTunes\'tan cekiliyor...')
        result = {}
        for prefix in artists:
            url = _itunes_artist_default_cover_url(prefix)
            if url:
                img = _download_bytes(url)
                result[prefix] = img
                status = 'OK' if img else 'INDIRILEMEDI'
            else:
                result[prefix] = None
                status = 'BULUNAMADI'
                _log_cover_failure('ARTIST_DEFAULT_MISS', prefix, '-', 'iTunes\'ta sanatci yok')
            self.stdout.write(f"   [{status}] {prefix}")
            time.sleep(0.5)  # rate limit
        return result

    # ── 4. Albumler ────────────────────────────────────────────────────────

    def _create_albums(self, artists: dict, default_covers: dict) -> dict:
        self.stdout.write('5) Best Of albumler olusturuluyor...')
        albums = {}
        for prefix, info in artists.items():
            album = Album.objects.create(
                title=f"Best of {info['display']}",
                artist=info['user'],
                description=f"{info['display']} en sevilen sarkilari",
            )
            img = default_covers.get(prefix)
            if img:
                rel_path = _save_cover(img, 'albums', _slug(f"best-of-{prefix}"))
                album.cover_image = rel_path
                album.save(update_fields=['cover_image'])
                self.stdout.write(f"   [+] {album.title} (cover: {rel_path})")
            else:
                self.stdout.write(f"   [+] {album.title} (cover yok)")
            albums[prefix] = album
        return albums

    # ── 5. Sarki Yukleme + Cover ───────────────────────────────────────────

    def _ingest_songs(self, artists: dict, albums: dict, default_covers: dict) -> dict:
        self.stdout.write(
            f"6) Sarkilar yukleniyor ({'fingerprint YOK' if self.skip_fingerprint else 'fingerprint VAR'})..."
        )

        songs_dir = Path(settings.MEDIA_ROOT) / 'songs'
        if not songs_dir.exists():
            self.stderr.write(self.style.ERROR(f'   media/songs/ bulunamadi: {songs_dir}'))
            return {}

        audio_files = sorted([
            f for f in songs_dir.iterdir()
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS
        ])
        if not audio_files:
            self.stdout.write(self.style.WARNING('   Ses dosyasi yok.'))
            return {}

        self.stdout.write(f'   {len(audio_files)} dosya bulundu.\n')

        songs_by_artist = {prefix: [] for prefix in artists}
        stats = {
            'success': 0, 'skipped_no_match': 0, 'fingerprint_err': 0,
            'cover_itunes': 0, 'cover_artist_fallback': 0, 'cover_none': 0,
        }

        for audio_path in audio_files:
            m = FILENAME_PATTERN.match(audio_path.name)
            if not m:
                self.stdout.write(f'   [?] Parse edilemedi: {audio_path.name}')
                stats['skipped_no_match'] += 1
                continue

            file_prefix = m.group(1).strip()
            title = m.group(2).strip()

            # Sanatci eslesmesi (case-insensitive)
            artist_info = None
            matched_prefix = None
            for prefix, info in artists.items():
                if file_prefix.lower() == prefix.lower():
                    artist_info = info
                    matched_prefix = prefix
                    break

            if artist_info is None:
                self.stdout.write(self.style.WARNING(
                    f'   [!] Sanatci eslesmedi: "{file_prefix}" - atlandi'
                ))
                stats['skipped_no_match'] += 1
                continue

            # Song create
            relative_path = f'songs/{audio_path.name}'
            song = Song.objects.create(
                title=title,
                artist=artist_info['user'],
                album=albums[matched_prefix],
                genre=artist_info['genre'],
                audio_file=relative_path,
            )
            songs_by_artist[matched_prefix].append(song)

            # Cover fetch
            cover_status = self._attach_cover(song, matched_prefix, title, default_covers)
            if cover_status == 'itunes':
                stats['cover_itunes'] += 1
            elif cover_status == 'fallback':
                stats['cover_artist_fallback'] += 1
            else:
                stats['cover_none'] += 1

            line = f'   [+] {matched_prefix} - {title[:50]} (id={song.id}, cover={cover_status})'

            if not self.skip_fingerprint:
                try:
                    count = ingest_song(song)
                    line += f' fp={count}'
                except Exception as e:
                    line += f' fp=ERR'
                    stats['fingerprint_err'] += 1
                    logger.warning(f'fingerprint err on {song.id}: {e}')

            self.stdout.write(line)
            stats['success'] += 1

            # Rate limit iTunes
            if not self.skip_covers:
                time.sleep(0.4)

        self.stats = stats  # summary icin sakla
        self.stdout.write('')
        self.stdout.write(
            f"   Sonuc: {stats['success']} yuklendi, {stats['skipped_no_match']} atlandi"
        )
        self.stdout.write(
            f"   Cover: iTunes={stats['cover_itunes']}, "
            f"sanatci-fallback={stats['cover_artist_fallback']}, "
            f"yok={stats['cover_none']}"
        )
        return songs_by_artist

    def _attach_cover(self, song: Song, artist_prefix: str, title: str, default_covers: dict) -> str:
        """
        Sarkiya cover ekle. Donus: 'itunes' / 'fallback' / 'none'
        """
        if self.skip_covers:
            return 'none'

        # 1) iTunes match dene
        match = _itunes_find_song(artist_prefix, title)
        if match and match.get('artworkUrl100'):
            url = match['artworkUrl100'].replace('100x100', '600x600')
            img = _download_bytes(url)
            if img:
                rel = _save_cover(img, 'songs', _slug(f"{artist_prefix}-{title}-{song.id}"))
                song.cover_image = rel
                song.save(update_fields=['cover_image'])
                return 'itunes'

        # 2) Sanatci default cover'a dus
        fallback = default_covers.get(artist_prefix)
        if fallback:
            rel = _save_cover(fallback, 'songs', _slug(f"{artist_prefix}-{title}-{song.id}"))
            song.cover_image = rel
            song.save(update_fields=['cover_image'])
            _log_cover_failure('ARTIST_FALLBACK', artist_prefix, title, 'iTunes match yok')
            return 'fallback'

        # 3) Hicbir sey yok
        _log_cover_failure('NO_COVER', artist_prefix, title, 'iTunes ve fallback ikisi de yok')
        return 'none'

    # ── 6. Demo Kullanicilar ───────────────────────────────────────────────

    def _create_demo_users(self) -> list:
        self.stdout.write('7) Demo kullanicilar olusturuluyor...')
        users = []
        for d in DEMO_USERS:
            u = User.objects.create(
                username=d['username'],
                first_name=d['first_name'],
                role='listener',
                bio=d['bio'],
            )
            u.set_password('Demo123!')
            u.save()
            users.append(u)
            self.stdout.write(f"   [+] {d['username']} (sifre: Demo123!)")
        return users

    # ── 7. Sosyal Aktivite ─────────────────────────────────────────────────

    def _seed_social(self, users: list, artists: dict, songs_by_artist: dict):
        self.stdout.write('8) Sosyal aktivite olusturuluyor (likes/follows/playlists/history)...')

        all_songs = []
        for songs in songs_by_artist.values():
            all_songs.extend(songs)
        if not all_songs:
            self.stdout.write('   Sarki yok, atlanıyor.')
            return

        artist_users = [info['user'] for info in artists.values()]

        rng = random.Random(42)  # deterministik

        for u in users:
            # Likes
            liked = rng.sample(all_songs, min(10, len(all_songs)))
            for s in liked:
                SongLike.objects.get_or_create(user=u, song=s)

            # Follows
            for a in rng.sample(artist_users, min(3, len(artist_users))):
                ArtistFollow.objects.get_or_create(user=u, artist=a)

            # Playlist + 8 sarki
            pl = Playlist.objects.create(
                owner=u,
                title=f"{u.first_name}'in seçimi",
                description='Demo calma listesi',
            )
            for pos, s in enumerate(rng.sample(all_songs, min(8, len(all_songs))), 1):
                PlaylistItem.objects.create(playlist=pl, song=s, position=pos)

            # Listen history (son 7 gunde dagilmis)
            history_songs = rng.sample(all_songs, min(15, len(all_songs)))
            now = timezone.now()
            for i, s in enumerate(history_songs):
                lh = ListenHistory.objects.create(
                    user=u, song=s, duration_ms=rng.randint(30_000, 220_000)
                )
                # listened_at auto_now_add → manuel override
                ListenHistory.objects.filter(id=lh.id).update(
                    listened_at=now - timedelta(hours=rng.randint(1, 168))
                )

            self.stdout.write(f"   [+] {u.username}: 10 like, 3 follow, 1 playlist (8 sarki), 15 history")

    def _print_summary(self):
        s = getattr(self, 'stats', {})
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('--- OZET ---'))
        self.stdout.write(f"  Sarki:        {Song.objects.count()}")
        self.stdout.write(f"  Album:        {Album.objects.count()}")
        self.stdout.write(f"  Sanatci:      {User.objects.filter(role='artist').count()}")
        self.stdout.write(f"  Listener:     {User.objects.filter(role='listener').count()}")
        cover_count = Song.objects.exclude(cover_image='').exclude(cover_image=None).count()
        self.stdout.write(f"  Cover'li:     {cover_count}")
        self.stdout.write(f"  Like:         {SongLike.objects.count()}")
        self.stdout.write(f"  Follow:       {ArtistFollow.objects.count()}")
        self.stdout.write(f"  Playlist:     {Playlist.objects.count()}")
        self.stdout.write(f"  History:      {ListenHistory.objects.count()}")
        if COVER_FAIL_LOG.exists():
            self.stdout.write(f"\n  Eksik cover detayi: {COVER_FAIL_LOG}")
