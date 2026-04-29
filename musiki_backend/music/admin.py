from django.contrib import admin
from .models import (
    Album, Song, Fingerprint, ListenHistory,
    SongLike, AlbumLike, ArtistFollow,
    Playlist, PlaylistItem,
)


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ('title', 'artist', 'release_date', 'is_deleted', 'created_at')
    list_filter = ('is_deleted',)
    search_fields = ('title', 'artist__username')


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ('title', 'artist', 'album', 'genre', 'duration',
                    'play_count', 'is_fingerprinted', 'is_deleted', 'created_at')
    list_filter = ('genre', 'is_fingerprinted', 'is_deleted')
    search_fields = ('title', 'artist__username')
    readonly_fields = ('is_fingerprinted', 'duration', 'play_count')

    actions = ['re_fingerprint']

    @admin.action(description='Seçili şarkıları yeniden fingerprint et')
    def re_fingerprint(self, request, queryset):
        from music.services.ingest import ingest_song
        count = 0
        for song in queryset:
            ingest_song(song)
            count += 1
        self.message_user(request, f'{count} şarkı yeniden fingerprint edildi.')


@admin.register(Fingerprint)
class FingerprintAdmin(admin.ModelAdmin):
    list_display = ('song', 'hash_code', 'offset_time')
    search_fields = ('song__title', 'hash_code')
    raw_id_fields = ('song',)


@admin.register(ListenHistory)
class ListenHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'song', 'listened_at')
    list_filter = ('listened_at',)


@admin.register(SongLike)
class SongLikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'song', 'created_at')
    raw_id_fields = ('user', 'song')


@admin.register(AlbumLike)
class AlbumLikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'album', 'created_at')
    raw_id_fields = ('user', 'album')


@admin.register(ArtistFollow)
class ArtistFollowAdmin(admin.ModelAdmin):
    list_display = ('user', 'artist', 'created_at')
    raw_id_fields = ('user', 'artist')


class PlaylistItemInline(admin.TabularInline):
    model = PlaylistItem
    extra = 0
    raw_id_fields = ('song',)


@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'is_deleted', 'created_at', 'updated_at')
    list_filter = ('is_deleted',)
    search_fields = ('title', 'owner__username')
    inlines = [PlaylistItemInline]


@admin.register(PlaylistItem)
class PlaylistItemAdmin(admin.ModelAdmin):
    list_display = ('playlist', 'song', 'position', 'added_at')
    raw_id_fields = ('playlist', 'song')
