"""
Müzik verilerini sıfırla ve yeniden yükle.

Kullanım:
    python manage.py setup_music
    python manage.py setup_music --no-fingerprint   # Fingerprint oluşturmayı atla (hızlı test)

Yapılanlar:
  1. Tüm DB verisi silinir (tablo şemaları korunur, superuser'lar korunur)
  2. seekture.db fingerprint/song kayıtları temizlenir
  3. 'duman' ve 'manga' sanatçı hesapları oluşturulur
  4. media/songs/ altındaki tüm MP3'ler dosya adından sanatçı tespit edilerek
     doğru kullanıcıya atanır ve fingerprint'lenir
"""
import os
import re
import sqlite3
import logging
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from music.models import Song, Album, Fingerprint, ListenHistory
from music.services.ingest import ingest_song

User = get_user_model()
logger = logging.getLogger(__name__)

SUPPORTED_EXTS = ('.mp3', '.wav', '.flac', '.ogg', '.m4a')
FILENAME_PATTERN = re.compile(r'^(.+?)\s+-\s+(.+?)(\.\w+)$')

# Dosya adı prefix → kullanıcı adı eşleşmesi
ARTIST_MAP = [
    {"filename_prefix": "Duman",  "username": "duman",  "display_name": "Duman"},
    {"filename_prefix": "maNga",  "username": "manga",  "display_name": "maNga"},
]


class Command(BaseCommand):
    help = 'Tüm veriyi temizler, sanatçı hesapları açar ve şarkıları yeniden yükler.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-fingerprint',
            action='store_true',
            help='Fingerprint oluşturmayı atla (hızlı test modu)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('=== Musiki Veri Sıfırlama ===\n'))

        self._clear_db()
        self._clear_seekture()
        artist_users = self._create_artists()
        self._ingest_songs(artist_users, skip_fingerprint=options['no_fingerprint'])

        self.stdout.write(self.style.SUCCESS('\n=== Tamamlandı ==='))

    # ── 1. DB Temizleme ────────────────────────────────────────────────────

    def _clear_db(self):
        self.stdout.write('1) PostgreSQL verisi temizleniyor...')

        lh_count, _ = ListenHistory.objects.all().delete()
        fp_count, _ = Fingerprint.objects.all().delete()

        # Soft-delete modellerini hard-delete ile sil (şema korunsun)
        song_count, _ = Song.all_objects.all().hard_delete()
        album_count, _ = Album.all_objects.all().hard_delete()
        user_count, _ = User.all_objects.filter(is_superuser=False).hard_delete()

        self.stdout.write(
            f'   Silindi → {user_count} kullanıcı, {album_count} albüm, '
            f'{song_count} şarkı, {fp_count} fingerprint (DB), '
            f'{lh_count} dinleme geçmişi'
        )

    # ── 2. seekture.db Temizleme ───────────────────────────────────────────

    def _clear_seekture(self):
        self.stdout.write('2) seekture.db temizleniyor...')
        db_path = settings.SEEKTURE_DB_PATH

        if not os.path.exists(db_path):
            self.stdout.write('   seekture.db bulunamadı, atlanıyor.')
            return

        conn = sqlite3.connect(db_path)
        try:
            fp_deleted = conn.execute('DELETE FROM fingerprints').rowcount
            song_deleted = conn.execute('DELETE FROM songs').rowcount
            conn.commit()
            self.stdout.write(
                f'   Silindi → {fp_deleted} fingerprint, {song_deleted} seekture şarkı kaydı'
            )
        finally:
            conn.close()

    # ── 3. Sanatçı Hesapları ───────────────────────────────────────────────

    def _create_artists(self) -> dict:
        """
        ARTIST_MAP'e göre sanatçı kullanıcıları oluştur.
        Returns: {filename_prefix: User} dict
        """
        self.stdout.write('3) Sanatçı hesapları oluşturuluyor...')
        artist_users = {}

        for a in ARTIST_MAP:
            user, created = User.objects.get_or_create(
                username=a['username'],
                defaults={
                    'first_name': a['display_name'],
                    'role': 'artist',
                    'is_approved_artist': True,
                    'bio': f"{a['display_name']} - Musiki sanatçısı",
                },
            )
            if created:
                user.set_password('Artist123!')
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f"   [+] Oluşturuldu: {a['username']} (şifre: Artist123!)")
                )
            else:
                # Mevcut kullanıcıyı sanatçı yap
                updated_fields = []
                if user.role != 'artist':
                    user.role = 'artist'
                    updated_fields.append('role')
                if not user.is_approved_artist:
                    user.is_approved_artist = True
                    updated_fields.append('is_approved_artist')
                if updated_fields:
                    user.save(update_fields=updated_fields)
                self.stdout.write(f"   [~] Mevcut: {a['username']}")

            artist_users[a['filename_prefix']] = user

        return artist_users

    # ── 4. Şarkı Yükleme ──────────────────────────────────────────────────

    def _ingest_songs(self, artist_users: dict, skip_fingerprint: bool):
        self.stdout.write(
            f"4) Şarkılar yükleniyor ({'fingerprint YOK' if skip_fingerprint else 'fingerprint VAR'})..."
        )

        songs_dir = Path(settings.MEDIA_ROOT) / 'songs'
        if not songs_dir.exists():
            self.stderr.write(self.style.ERROR(f'   media/songs/ klasörü bulunamadı: {songs_dir}'))
            return

        audio_files = [
            f for f in sorted(songs_dir.iterdir())
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS
        ]

        if not audio_files:
            self.stdout.write(self.style.WARNING('   Ses dosyası bulunamadı.'))
            return

        self.stdout.write(f'   {len(audio_files)} dosya bulundu.\n')

        success, skipped, error = 0, 0, 0

        for audio_path in audio_files:
            m = FILENAME_PATTERN.match(audio_path.name)
            if not m:
                self.stdout.write(f'   [?] Parse edilemedi: {audio_path.name}')
                skipped += 1
                continue

            filename_prefix = m.group(1).strip()
            title = m.group(2).strip()

            # Sanatçı eşleşmesi: önce tam eşleşme, yoksa kullanıcı adına düşür
            artist_user = artist_users.get(filename_prefix)
            if artist_user is None:
                username = filename_prefix.lower().replace(' ', '_')
                artist_user = artist_users.get(username)

            if artist_user is None:
                self.stdout.write(
                    self.style.WARNING(f'   [!] Sanatçı eşleşmedi: "{filename_prefix}" → atlandı')
                )
                skipped += 1
                continue

            # Dosya media/songs/ altında zaten var — sadece DB kaydı oluştur
            relative_path = f'songs/{audio_path.name}'
            song = Song.objects.create(
                title=title,
                artist=artist_user,
                genre='rock',
                audio_file=relative_path,
            )

            self.stdout.write(
                f'   [+] {filename_prefix} - {title} (id={song.id})',
                ending='',
            )

            if not skip_fingerprint:
                self.stdout.write(' → fingerprint...', ending='')
                try:
                    count = ingest_song(song)
                    self.stdout.write(self.style.SUCCESS(f' {count} hash OK'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f' HATA: {e}'))
                    error += 1
            else:
                self.stdout.write('')

            success += 1

        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(f'   Sonuç: {success} yüklendi, {skipped} atlandı, {error} fingerprint hatası')
        )
