from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Album, Song, ListenHistory,
    SongLike, AlbumLike, ArtistFollow,
    Playlist, PlaylistItem,
)

User = get_user_model()


def _current_user(context):
    request = context.get('request') if context else None
    if request and request.user and request.user.is_authenticated:
        return request.user
    return None


class ArtistBriefSerializer(serializers.ModelSerializer):
    is_followed = serializers.SerializerMethodField()
    followers_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'is_followed', 'followers_count')

    def get_is_followed(self, obj):
        user = _current_user(self.context)
        if not user:
            return False
        return ArtistFollow.objects.filter(user=user, artist=obj).exists()

    def get_followers_count(self, obj):
        return ArtistFollow.objects.filter(artist=obj).count()


class AlbumBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Album
        fields = ('id', 'title')


class ArtistListSerializer(ArtistBriefSerializer):
    songs_count = serializers.SerializerMethodField()

    class Meta(ArtistBriefSerializer.Meta):
        fields = ArtistBriefSerializer.Meta.fields + ('songs_count',)

    def get_songs_count(self, obj):
        return Song.objects.filter(artist=obj).count()


class ArtistDetailSerializer(ArtistBriefSerializer):
    songs = serializers.SerializerMethodField()
    albums = serializers.SerializerMethodField()
    songs_count = serializers.SerializerMethodField()

    class Meta(ArtistBriefSerializer.Meta):
        fields = ArtistBriefSerializer.Meta.fields + ('songs_count', 'songs', 'albums')

    def get_songs(self, obj):
        qs = Song.objects.filter(artist=obj).select_related('artist', 'album').order_by('-play_count')
        return SongListSerializer(qs, many=True, context=self.context).data

    def get_albums(self, obj):
        qs = Album.objects.filter(artist=obj).select_related('artist').order_by('-created_at')
        return AlbumSerializer(qs, many=True, context=self.context).data

    def get_songs_count(self, obj):
        return Song.objects.filter(artist=obj).count()


# ──────────────────────────── ALBUM ────────────────────────────

class AlbumSerializer(serializers.ModelSerializer):
    artist = ArtistBriefSerializer(read_only=True)
    song_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Album
        fields = ('id', 'title', 'artist', 'cover_image', 'release_date',
                  'description', 'song_count', 'is_liked', 'created_at')
        read_only_fields = ('id', 'artist', 'created_at')

    def get_song_count(self, obj):
        return obj.songs.count()

    def get_is_liked(self, obj):
        user = _current_user(self.context)
        if not user:
            return False
        return AlbumLike.objects.filter(user=user, album=obj).exists()


class AlbumDetailSerializer(AlbumSerializer):
    songs = serializers.SerializerMethodField()

    class Meta(AlbumSerializer.Meta):
        fields = AlbumSerializer.Meta.fields + ('songs',)

    def get_songs(self, obj):
        return SongListSerializer(obj.songs.all(), many=True, context=self.context).data


# ──────────────────────────── SONG ────────────────────────────

class SongListSerializer(serializers.ModelSerializer):
    artist = ArtistBriefSerializer(read_only=True)
    album = AlbumBriefSerializer(read_only=True)
    is_liked = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = Song
        fields = ('id', 'title', 'artist', 'album', 'genre',
                  'duration', 'play_count', 'is_fingerprinted', 'cover_image',
                  'is_liked', 'created_at')

    def get_is_liked(self, obj):
        user = _current_user(self.context)
        if not user:
            return False
        liked_ids = self.context.get('liked_song_ids')
        if liked_ids is not None:
            return obj.id in liked_ids
        return SongLike.objects.filter(user=user, song=obj).exists()

    def get_cover_image(self, obj):
        cover = obj.effective_cover
        if not cover:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(cover.url)
        return cover.url


class SongDetailSerializer(serializers.ModelSerializer):
    artist = ArtistBriefSerializer(read_only=True)
    album = AlbumSerializer(read_only=True)
    fingerprint_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = Song
        fields = ('id', 'title', 'artist', 'album', 'genre', 'audio_file',
                  'cover_image', 'duration', 'play_count', 'is_fingerprinted',
                  'fingerprint_count', 'is_liked', 'created_at', 'updated_at')
        read_only_fields = ('id', 'artist', 'duration', 'is_fingerprinted', 'play_count', 'created_at')

    def get_fingerprint_count(self, obj):
        return obj.fingerprints.count()

    def get_is_liked(self, obj):
        user = _current_user(self.context)
        if not user:
            return False
        return SongLike.objects.filter(user=user, song=obj).exists()

    def get_cover_image(self, obj):
        cover = obj.effective_cover
        if not cover:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(cover.url)
        return cover.url


class SongUploadSerializer(serializers.ModelSerializer):
    album = serializers.PrimaryKeyRelatedField(
        queryset=Album.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Song
        fields = ('id', 'title', 'genre', 'album', 'audio_file',
                  'cover_image', 'duration', 'is_fingerprinted')
        read_only_fields = ('id', 'duration', 'is_fingerprinted')

    def validate_album(self, album):
        request = self.context.get('request')
        if album and request and album.artist != request.user:
            raise serializers.ValidationError("Bu albüm size ait değil.")
        return album

    def validate_audio_file(self, value):
        allowed = ('.mp3', '.wav', '.flac', '.ogg', '.m4a')
        if not any(value.name.lower().endswith(ext) for ext in allowed):
            raise serializers.ValidationError(
                f"Desteklenen formatlar: {', '.join(allowed)}"
            )
        return value


class SongUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Song
        fields = ('title', 'genre', 'album', 'cover_image')

    def validate_album(self, album):
        request = self.context.get('request')
        if album and request and album.artist != request.user:
            raise serializers.ValidationError("Bu albüm size ait değil.")
        return album


# ──────────────────────────── LISTEN HISTORY ────────────────────────────

class ListenHistorySerializer(serializers.ModelSerializer):
    song = SongListSerializer(read_only=True)

    class Meta:
        model = ListenHistory
        fields = ('id', 'song', 'duration_ms', 'listened_at')


class RecordListenSerializer(serializers.Serializer):
    song_id = serializers.IntegerField()
    duration_ms = serializers.IntegerField(min_value=0)


# ──────────────────────────── PLAYLIST ────────────────────────────

class PlaylistSerializer(serializers.ModelSerializer):
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Playlist
        fields = ('id', 'title', 'description', 'cover_image',
                  'item_count', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_item_count(self, obj):
        return obj.items.count()


class PlaylistItemSerializer(serializers.ModelSerializer):
    song = SongListSerializer(read_only=True)

    class Meta:
        model = PlaylistItem
        fields = ('id', 'position', 'song', 'added_at')


class PlaylistDetailSerializer(PlaylistSerializer):
    items = PlaylistItemSerializer(many=True, read_only=True)

    class Meta(PlaylistSerializer.Meta):
        fields = PlaylistSerializer.Meta.fields + ('items',)


class PlaylistAddItemSerializer(serializers.Serializer):
    song_id = serializers.IntegerField()


class PlaylistReorderSerializer(serializers.Serializer):
    item_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
