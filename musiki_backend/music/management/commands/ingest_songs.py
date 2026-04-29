"""
Toplu şarkı yükleme komutu.
Kullanım:
    python manage.py ingest_songs --dir PATH [--album "Albüm Adı"] [--genre rock]

Dosya ismi formatı: "Sanatçı - Şarkı Adı.mp3" veya "Şarkı Adı.mp3"
"""
import os
import re
import shutil
import logging
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File

from music.models import Song, Album
from music.services.ingest import ingest_song

User = get_user_model()
logger = logging.getLogger(__name__)

SUPPORTED_EXTS = ('.mp3', '.wav', '.flac', '.ogg', '.m4a')
FILENAME_PATTERN = re.compile(r'^(.+?)\s+-\s+(.+?)(\.\w+)$')


class Command(BaseCommand):
    help = 'MP3 dosyalarını toplu olarak sisteme yükler ve fingerprint oluşturur.'

    def add_arguments(self, parser):
        parser.add_argument('--dir', required=True, help='MP3 dosyalarının bulunduğu klasör')
        parser.add_argument('--album', default=None, help='Albüm adı (opsiyonel)')
        parser.add_argument('--genre', default='other', help='Tür (varsayılan: other)')
        parser.add_argument('--no-fingerprint', action='store_true',
                            help='Fingerprint oluşturmayı atla')

    def handle(self, *args, **options):
        src_dir = Path(options['dir'])
        if not src_dir.exists():
            self.stderr.write(self.style.ERROR(f"Klasör bulunamadı: {src_dir}"))
            return

        audio_files = [
            f for f in src_dir.iterdir()
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS
        ]

        if not audio_files:
            self.stderr.write(self.style.WARNING("Ses dosyası bulunamadı."))
            return

        self.stdout.write(f"{len(audio_files)} dosya bulundu.\n")

        # Dosya isimlerinden sanatçı tespiti (ilk dosyadan)
        artist_user = self._get_or_create_artist(audio_files)
        album = self._get_or_create_album(options['album'], artist_user) if options['album'] else None

        dest_dir = Path(settings.MEDIA_ROOT) / 'songs'
        dest_dir.mkdir(parents=True, exist_ok=True)

        success, skipped = 0, 0

        for audio_path in sorted(audio_files):
            artist_name, title = self._parse_filename(audio_path)

            # Aynı sanatçı + başlık varsa atla
            if Song.objects.filter(title=title, artist=artist_user).exists():
                self.stdout.write(f"  [ATLA] '{title}' zaten mevcut.")
                skipped += 1
                continue

            # Dosyayı media/songs/ altına kopyala
            dest_path = dest_dir / audio_path.name
            if not dest_path.exists():
                shutil.copy2(str(audio_path), str(dest_path))

            # Song kaydı oluştur
            relative_path = f"songs/{audio_path.name}"
            song = Song.objects.create(
                title=title,
                artist=artist_user,
                album=album,
                genre=options['genre'],
                audio_file=relative_path,
            )

            self.stdout.write(f"  [+] '{title}' kaydedildi (id={song.id})", ending='')

            # Fingerprint
            if not options['no_fingerprint']:
                self.stdout.write(' -> fingerprint...', ending='')
                try:
                    count = ingest_song(song)
                    self.stdout.write(self.style.SUCCESS(f' {count} hash OK'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f' HATA: {e}'))
            else:
                self.stdout.write('')

            success += 1

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f"Tamamlandı: {success} yüklendi, {skipped} atlandı."
        ))

    def _parse_filename(self, path: Path) -> tuple[str, str]:
        """'Duman - Ah.mp3' → ('Duman', 'Ah')"""
        m = FILENAME_PATTERN.match(path.name)
        if m:
            return m.group(1).strip(), m.group(2).strip()
        return 'Bilinmeyen', path.stem

    def _get_or_create_artist(self, audio_files: list) -> User:
        """İlk dosyanın adından sanatçıyı tespit et, yoksa oluştur."""
        artist_name = 'Bilinmeyen'
        for f in audio_files:
            m = FILENAME_PATTERN.match(f.name)
            if m:
                artist_name = m.group(1).strip()
                break

        username = artist_name.lower().replace(' ', '_')
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'role': 'artist',
                'is_approved_artist': True,
                'bio': f'{artist_name} - Musiki sanatçısı',
            }
        )
        if created:
            user.set_password('Artist123!')
            user.save()
            self.stdout.write(self.style.SUCCESS(
                f"Sanatçı hesabı oluşturuldu: {username} (şifre: Artist123!)"
            ))
        else:
            # Mevcut kullanıcıyı sanatçı yap
            if user.role != 'artist':
                user.role = 'artist'
                user.is_approved_artist = True
                user.save(update_fields=['role', 'is_approved_artist'])
            self.stdout.write(f"Sanatçı mevcut: {username}")

        return user

    def _get_or_create_album(self, album_title: str, artist: User) -> Album:
        album, created = Album.objects.get_or_create(
            title=album_title,
            artist=artist,
        )
        if created:
            self.stdout.write(f"Albüm oluşturuldu: '{album_title}'")
        else:
            self.stdout.write(f"Albüm mevcut: '{album_title}'")
        return album
