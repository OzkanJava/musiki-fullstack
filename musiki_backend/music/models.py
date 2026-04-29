from django.db import models
from django.conf import settings
from common.models import SoftDeleteModel


class Album(SoftDeleteModel):
    title = models.CharField(max_length=200)
    artist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='albums',
    )
    cover_image = models.ImageField(upload_to='covers/albums/', null=True, blank=True)
    release_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'albums'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} ({self.artist.username})'


class Song(SoftDeleteModel):
    class Genre(models.TextChoices):
        POP = 'pop', 'Pop'
        ROCK = 'rock', 'Rock'
        HIP_HOP = 'hip_hop', 'Hip Hop'
        ELECTRONIC = 'electronic', 'Electronic'
        CLASSICAL = 'classical', 'Klasik'
        JAZZ = 'jazz', 'Jazz'
        FOLK = 'folk', 'Folk'
        OTHER = 'other', 'Diğer'

    title = models.CharField(max_length=200)
    artist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='songs',
    )
    album = models.ForeignKey(
        Album,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='songs',
    )
    # Kullanıcı "Diğer" seçerse serbest metin gönderebilir — choices kısıtı yok.
    # ŞEMA DEĞİŞİKLİĞİ: `python manage.py makemigrations music && python manage.py migrate` çalıştırılmalı.
    genre = models.CharField(max_length=50, default=Genre.OTHER)
    audio_file = models.FileField(upload_to='songs/')
    cover_image = models.ImageField(upload_to='covers/songs/', null=True, blank=True)
    duration = models.FloatField(default=0.0, help_text='Saniye cinsinden süre')
    play_count = models.PositiveIntegerField(default=0)
    is_fingerprinted = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'songs'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} - {self.artist.username}'

    @property
    def effective_cover(self):
        """Şarkının kapağı yoksa albüm kapağını döner."""
        if self.cover_image:
            return self.cover_image
        if self.album and self.album.cover_image:
            return self.album.cover_image
        return None


class Fingerprint(models.Model):
    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE,
        related_name='fingerprints',
    )
    hash_code = models.CharField(max_length=20)
    offset_time = models.IntegerField()

    class Meta:
        db_table = 'fingerprints'
        indexes = [
            models.Index(fields=['hash_code'], name='idx_hash_code'),
        ]


class ListenHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='listen_history',
    )
    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE,
        related_name='listen_history',
    )
    duration_ms = models.PositiveIntegerField(
        default=0,
        help_text='Kullanıcının bu oturumda dinlediği süre (milisaniye)',
    )
    listened_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'listen_history'
        ordering = ['-listened_at']
        indexes = [
            models.Index(fields=['user', 'listened_at'], name='idx_user_listened'),
        ]


# ──────────────────────────── LIKES / FOLLOWS ────────────────────────────

class SongLike(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='song_likes',
    )
    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE,
        related_name='likes',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'song_likes'
        unique_together = ('user', 'song')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at'], name='idx_songlike_user_time'),
        ]


class AlbumLike(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='album_likes',
    )
    album = models.ForeignKey(
        Album,
        on_delete=models.CASCADE,
        related_name='likes',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'album_likes'
        unique_together = ('user', 'album')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at'], name='idx_albumlike_user_time'),
        ]


class ArtistFollow(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='artist_follows',
    )
    artist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='followers',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'artist_follows'
        unique_together = ('user', 'artist')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at'], name='idx_follow_user_time'),
            models.Index(fields=['artist'], name='idx_follow_artist'),
        ]


# ──────────────────────────── PLAYLIST ────────────────────────────

class Playlist(SoftDeleteModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='playlists',
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    cover_image = models.ImageField(upload_to='covers/playlists/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'playlists'
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.title} ({self.owner.username})'


class PlaylistItem(models.Model):
    playlist = models.ForeignKey(
        Playlist,
        on_delete=models.CASCADE,
        related_name='items',
    )
    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE,
        related_name='+',
    )
    position = models.PositiveIntegerField()
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'playlist_items'
        ordering = ['position']
        unique_together = ('playlist', 'song')
        indexes = [
            models.Index(fields=['playlist', 'position'], name='idx_playlistitem_pos'),
        ]
