import os
import re
import mimetypes
import tempfile
import logging

from django.conf import settings
from django.http import HttpResponse, FileResponse, StreamingHttpResponse
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser

from common.permissions import IsArtist, IsAdmin, IsOwnerOrAdmin
from .models import (
    Album, Song, ListenHistory,
    SongLike, AlbumLike, ArtistFollow,
    Playlist, PlaylistItem,
)
from django.contrib.auth import get_user_model
from django.db.models import F, Max, Subquery, OuterRef
from django.shortcuts import get_object_or_404
from .serializers import (
    AlbumSerializer, AlbumDetailSerializer,
    SongListSerializer, SongDetailSerializer,
    SongUploadSerializer, SongUpdateSerializer,
    ListenHistorySerializer, RecordListenSerializer,
    ArtistBriefSerializer, ArtistListSerializer, ArtistDetailSerializer,
    PlaylistSerializer, PlaylistDetailSerializer,
    PlaylistItemSerializer, PlaylistAddItemSerializer,
    PlaylistReorderSerializer,
)

User = get_user_model()
from .filters import SongFilter, AlbumFilter
from .services.ingest import ingest_song
from .services.recognize import recognize_audio

logger = logging.getLogger(__name__)

FINGERPRINT_SYNC = getattr(settings, 'FINGERPRINT_SYNC', False)

AUDIO_MIME = {
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.flac': 'audio/flac',
    '.ogg': 'audio/ogg',
    '.m4a': 'audio/mp4',
}


def _audio_content_type(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return AUDIO_MIME.get(ext, 'audio/mpeg')


def _range_response(request, file_path: str, content_type: str) -> HttpResponse:
    """
    Range-aware dosya sunumu — dev modda seek desteği için.
    206 Partial Content döner; Range header yoksa 200 ile tam dosya.
    """
    file_size = os.path.getsize(file_path)
    range_header = request.META.get('HTTP_RANGE', '').strip()

    if range_header:
        m = re.match(r'bytes=(\d+)-(\d*)', range_header)
        if m:
            start = int(m.group(1))
            end = int(m.group(2)) if m.group(2) else file_size - 1
            end = min(end, file_size - 1)
            length = end - start + 1

            with open(file_path, 'rb') as f:
                f.seek(start)
                data = f.read(length)

            resp = HttpResponse(data, status=206, content_type=content_type)
            resp['Content-Range'] = f'bytes {start}-{end}/{file_size}'
            resp['Accept-Ranges'] = 'bytes'
            resp['Content-Length'] = str(length)
            return resp

    resp = FileResponse(open(file_path, 'rb'), content_type=content_type)
    resp['Accept-Ranges'] = 'bytes'
    resp['Content-Length'] = str(file_size)
    return resp


def _trigger_fingerprint(song):
    if FINGERPRINT_SYNC:
        ingest_song(song)
    else:
        from .tasks import fingerprint_song_task
        fingerprint_song_task.delay(song.id)


# ──────────────────────────── ALBUM ────────────────────────────

class AlbumViewSet(viewsets.ModelViewSet):
    queryset = Album.objects.select_related('artist').all()
    filterset_class = AlbumFilter
    search_fields = ('title', 'artist__username')
    ordering_fields = ('title', 'created_at')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AlbumDetailSerializer
        return AlbumSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'liked', 'like'):
            return [IsAuthenticated()]
        if self.action in ('update', 'partial_update', 'destroy'):
            return [IsArtist(), IsOwnerOrAdmin()]
        # create
        return [IsArtist()]

    def perform_create(self, serializer):
        serializer.save(artist=self.request.user)

    def perform_destroy(self, instance):
        instance.delete()  # Soft delete

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='liked')
    def liked(self, request):
        likes = AlbumLike.objects.filter(user=request.user).select_related(
            'album', 'album__artist'
        ).order_by('-created_at')
        albums = [like.album for like in likes]
        serializer = AlbumSerializer(albums, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated], url_path='like')
    def like(self, request, pk=None):
        album = self.get_object()
        if request.method == 'POST':
            _obj, created = AlbumLike.objects.get_or_create(user=request.user, album=album)
            return Response(
                {'liked': True},
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            )
        AlbumLike.objects.filter(user=request.user, album=album).delete()
        return Response({'liked': False}, status=status.HTTP_204_NO_CONTENT)


# ──────────────────────────── SONG ────────────────────────────

class SongViewSet(viewsets.ModelViewSet):
    queryset = Song.objects.select_related('artist', 'album').all()
    filterset_class = SongFilter
    search_fields = ('title', 'artist__username', 'album__title')
    ordering_fields = ('title', 'play_count', 'created_at')
    parser_classes = (MultiPartParser, FormParser)

    def get_serializer_class(self):
        if self.action == 'create':
            return SongUploadSerializer
        if self.action in ('update', 'partial_update'):
            return SongUpdateSerializer
        if self.action == 'retrieve':
            return SongDetailSerializer
        return SongListSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'stream', 'play', 'mine', 'liked', 'like'):
            return [IsAuthenticated()]
        if self.action in ('update', 'partial_update', 'destroy'):
            return [IsArtist(), IsOwnerOrAdmin()]
        # create
        return [IsArtist()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Frontend SongDto (Moshi) requires 'artist' and other fields.
        # Since SongUploadSerializer lacks them, we use SongListSerializer for the response.
        song = serializer.instance
        read_serializer = SongListSerializer(song, context=self.get_serializer_context())
        headers = self.get_success_headers(serializer.data)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        song = serializer.save(artist=self.request.user)
        _trigger_fingerprint(song)

    def perform_destroy(self, instance):
        instance.delete()  # Soft delete

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        user = self.request.user if self.request else None
        if user and user.is_authenticated and self.action in ('list', 'mine', 'liked'):
            ctx['liked_song_ids'] = set(
                SongLike.objects.filter(user=user).values_list('song_id', flat=True)
            )
        return ctx

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def mine(self, request):
        """Giriş yapan sanatçının kendi şarkılarını listeler."""
        songs = Song.objects.filter(artist=request.user).select_related('artist', 'album')
        serializer = SongListSerializer(songs, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='liked')
    def liked(self, request):
        """Kullanıcının beğendiği şarkılar (yeniden eskiye)."""
        likes = SongLike.objects.filter(user=request.user).select_related(
            'song', 'song__artist', 'song__album'
        ).order_by('-created_at')
        songs = [like.song for like in likes]
        serializer = SongListSerializer(songs, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated], url_path='like')
    def like(self, request, pk=None):
        """POST: beğen (idempotent), DELETE: beğeniyi kaldır."""
        song = self.get_object()
        if request.method == 'POST':
            _obj, created = SongLike.objects.get_or_create(user=request.user, song=song)
            return Response(
                {'liked': True},
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            )
        # DELETE
        SongLike.objects.filter(user=request.user, song=song).delete()
        return Response({'liked': False}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def play(self, request, pk=None):
        """Play count artır (atomic). Dinleme geçmişi RecordListenView'dan kaydedilir."""
        song = self.get_object()
        Song.objects.filter(pk=song.pk).update(play_count=F('play_count') + 1)
        song.refresh_from_db(fields=['play_count'])
        return Response({'status': 'ok', 'play_count': song.play_count})

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def stream(self, request, pk=None):
        """
        Güvenli müzik streaming.

        Production (USE_NGINX_ACCEL=True):
            Django JWT'yi doğrular → boş response + X-Accel-Redirect header →
            Nginx /internal-media/'den dosyayı doğrudan serve eder (zero-copy).

        Development (USE_NGINX_ACCEL=False):
            Django Range-aware FileResponse ile dosyayı serve eder.
            Seek (scrubbing) desteği: 206 Partial Content.
        """
        song = self.get_object()
        content_type = _audio_content_type(song.audio_file.name)
        filename = os.path.basename(song.audio_file.name)

        use_nginx = getattr(settings, 'USE_NGINX_ACCEL', False)

        if use_nginx:
            # ── Production: Nginx X-Accel-Redirect ──────────────────────
            resp = HttpResponse(content_type=content_type)
            resp['X-Accel-Redirect'] = f'/internal-media/{song.audio_file.name}'
            resp['Content-Disposition'] = f'inline; filename="{filename}"'
            return resp
        else:
            # ── Development: Range-aware Django FileResponse ─────────────
            resp = _range_response(request, song.audio_file.path, content_type)
            resp['Content-Disposition'] = f'inline; filename="{filename}"'
            return resp


# ──────────────────────────── RECOGNIZE ────────────────────────────

class RecognizeView(APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        audio_file = request.FILES.get('audio')
        if not audio_file:
            return Response(
                {'detail': 'audio alanı zorunludur.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        suffix = os.path.splitext(audio_file.name)[1] or '.wav'
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            for chunk in audio_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            result = recognize_audio(tmp_path, request=request)
        finally:
            os.unlink(tmp_path)

        return Response(result)


# ──────────────────────────── LISTEN HISTORY ────────────────────────────

class RecordListenView(APIView):
    """
    Dinleme oturumu kaydı.
    Frontend şarkı değiştiğinde/durduğunda çağırır.
    - ListenHistory kaydı oluşturur (duration_ms dahil)
    - play_count'u atomic artırır
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = RecordListenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        song_id = serializer.validated_data['song_id']
        duration_ms = serializer.validated_data['duration_ms']

        try:
            song = Song.objects.get(pk=song_id)
        except Song.DoesNotExist:
            return Response(
                {'detail': 'Şarkı bulunamadı.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Atomic play_count artışı
        Song.objects.filter(pk=song.pk).update(play_count=F('play_count') + 1)

        # Dinleme geçmişi kaydı (süre dahil)
        ListenHistory.objects.create(
            user=request.user,
            song=song,
            duration_ms=duration_ms,
        )

        return Response({'status': 'ok'})


class ListenHistoryView(generics.ListAPIView):
    serializer_class = ListenHistorySerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return ListenHistory.objects.filter(
            user=self.request.user
        ).select_related('song', 'song__artist', 'song__album')


# ──────────────────────────── PLAYLIST ────────────────────────────

class PlaylistViewSet(viewsets.ModelViewSet):
    """
    Kullanıcının kendi playlistleri — her zaman owner filter.
    Private-only: başka kullanıcıların playlistlerine erişim yok (404).
    """
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Playlist.objects.filter(owner=self.request.user).order_by('-updated_at')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PlaylistDetailSerializer
        return PlaylistSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def perform_destroy(self, instance):
        instance.delete()  # soft delete

    @action(detail=True, methods=['post'], url_path='items')
    def add_item(self, request, pk=None):
        """Playlist'e şarkı ekler. Aynı şarkı iki kez eklenmez."""
        playlist = self.get_object()
        serializer = PlaylistAddItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        song_id = serializer.validated_data['song_id']
        song = get_object_or_404(Song, pk=song_id)

        existing = PlaylistItem.objects.filter(playlist=playlist, song=song).first()
        if existing:
            return Response(
                PlaylistItemSerializer(existing).data,
                status=status.HTTP_200_OK,
            )

        max_pos = PlaylistItem.objects.filter(playlist=playlist).aggregate(m=Max('position'))['m']
        next_pos = 0 if max_pos is None else max_pos + 1
        item = PlaylistItem.objects.create(playlist=playlist, song=song, position=next_pos)
        playlist.save(update_fields=['updated_at'])
        return Response(
            PlaylistItemSerializer(item, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['delete'], url_path=r'items/(?P<item_id>\d+)')
    def remove_item(self, request, pk=None, item_id=None):
        playlist = self.get_object()
        deleted, _ = PlaylistItem.objects.filter(playlist=playlist, pk=item_id).delete()
        if deleted == 0:
            return Response({'detail': 'Item bulunamadı.'}, status=status.HTTP_404_NOT_FOUND)
        playlist.save(update_fields=['updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='reorder')
    def reorder(self, request, pk=None):
        """item_ids sırasına göre position'ları yeniden ata."""
        playlist = self.get_object()
        serializer = PlaylistReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item_ids = serializer.validated_data['item_ids']

        existing_ids = set(
            PlaylistItem.objects.filter(playlist=playlist).values_list('id', flat=True)
        )
        if set(item_ids) != existing_ids:
            return Response(
                {'detail': 'item_ids playlistteki item\'larla eşleşmiyor.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for idx, item_id in enumerate(item_ids):
            PlaylistItem.objects.filter(pk=item_id).update(position=idx)
        playlist.save(update_fields=['updated_at'])
        return Response({'status': 'ok'})


# ──────────────────────────── ARTIST FOLLOW ────────────────────────────

class ArtistFollowView(APIView):
    """POST/DELETE /api/music/artists/{id}/follow/"""
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        artist = get_object_or_404(User, pk=pk)
        if artist == request.user:
            return Response(
                {'detail': 'Kendini takip edemezsin.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        _obj, created = ArtistFollow.objects.get_or_create(user=request.user, artist=artist)
        return Response(
            {'followed': True},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request, pk):
        ArtistFollow.objects.filter(user=request.user, artist_id=pk).delete()
        return Response({'followed': False}, status=status.HTTP_204_NO_CONTENT)


class ArtistListView(generics.ListAPIView):
    """GET /api/music/artists/?search=... — sanatçı listesi (search destekli)."""
    permission_classes = (IsAuthenticated,)
    serializer_class = ArtistListSerializer
    pagination_class = None

    def get_queryset(self):
        qs = User.objects.filter(role='artist').order_by('username')
        q = self.request.query_params.get('search', '').strip()
        if q:
            qs = qs.filter(username__icontains=q)
        return qs


class ArtistDetailView(generics.RetrieveAPIView):
    """GET /api/music/artists/{id}/ — sanatçı profili + şarkılar + albümler."""
    permission_classes = (IsAuthenticated,)
    serializer_class = ArtistDetailSerializer

    def get_queryset(self):
        return User.objects.filter(role='artist')


class FollowedArtistsView(generics.ListAPIView):
    serializer_class = ArtistBriefSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        followed_ids = ArtistFollow.objects.filter(
            user=self.request.user
        ).order_by('-created_at').values_list('artist_id', flat=True)
        # Preserve order with Case/When would be ideal; for simplicity:
        return User.objects.filter(pk__in=list(followed_ids))


# ──────────────────────────── HOME FEED ────────────────────────────

class HomeRecentlyPlayedView(APIView):
    """Son dinlenen unique şarkılar (son 10)."""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        latest_per_song = ListenHistory.objects.filter(
            user=request.user
        ).values('song').annotate(last=Max('listened_at')).order_by('-last')[:10]
        song_ids = [row['song'] for row in latest_per_song]
        if not song_ids:
            return Response([])
        songs_map = {
            s.id: s for s in Song.objects.filter(pk__in=song_ids).select_related('artist', 'album')
        }
        ordered = [songs_map[sid] for sid in song_ids if sid in songs_map]
        context = {
            'request': request,
            'liked_song_ids': set(
                SongLike.objects.filter(user=request.user, song_id__in=song_ids)
                .values_list('song_id', flat=True)
            ),
        }
        return Response(SongListSerializer(ordered, many=True, context=context).data)


class HomeForYouView(APIView):
    """Rastgele seçilmiş 10 şarkı — basit 'Senin İçin' shelfi."""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        songs = Song.objects.select_related('artist', 'album').order_by('?')[:10]
        context = {
            'request': request,
            'liked_song_ids': set(
                SongLike.objects.filter(user=request.user).values_list('song_id', flat=True)
            ),
        }
        return Response(SongListSerializer(songs, many=True, context=context).data)


# ──────────────────────────── SOCIAL (Faz D) ────────────────────────────

class UserFollowView(APIView):
    """POST/DELETE /api/music/users/{id}/follow/ — herhangi bir kullanıcıyı takip et."""
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        if target == request.user:
            return Response(
                {'detail': 'Kendini takip edemezsin.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        _obj, created = ArtistFollow.objects.get_or_create(user=request.user, artist=target)
        return Response(
            {'followed': True},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request, pk):
        ArtistFollow.objects.filter(user=request.user, artist_id=pk).delete()
        return Response({'followed': False}, status=status.HTTP_204_NO_CONTENT)


class UserProfileView(APIView):
    """GET /api/music/users/{id}/ — başka kullanıcının public profili."""
    permission_classes = (IsAuthenticated,)

    def get(self, request, pk):
        target = get_object_or_404(User, pk=pk)

        is_followed = ArtistFollow.objects.filter(
            user=request.user, artist=target
        ).exists()
        followers_count = ArtistFollow.objects.filter(artist=target).count()
        following_count = ArtistFollow.objects.filter(user=target).count()

        # Son dinlediği unique şarkılar (kendi profili için kendi geçmişi, başkaları için de aynı)
        latest = (
            ListenHistory.objects.filter(user=target)
            .values('song')
            .annotate(last=Max('listened_at'))
            .order_by('-last')[:10]
        )
        song_ids = [r['song'] for r in latest]
        songs_map = {
            s.id: s for s in Song.objects.filter(pk__in=song_ids).select_related('artist', 'album')
        }
        recent_songs = [songs_map[i] for i in song_ids if i in songs_map]

        context = {
            'request': request,
            'liked_song_ids': set(
                SongLike.objects.filter(user=request.user, song_id__in=song_ids)
                .values_list('song_id', flat=True)
            ),
        }

        return Response({
            'id': target.id,
            'username': target.username,
            'bio': target.bio,
            'role': target.role,
            'is_approved_artist': target.is_approved_artist,
            'is_followed': is_followed,
            'followers_count': followers_count,
            'following_count': following_count,
            'recent_songs': SongListSerializer(recent_songs, many=True, context=context).data,
        })


class MyFollowingView(generics.ListAPIView):
    """GET /api/music/users/me/following/"""
    serializer_class = ArtistBriefSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        ids = list(
            ArtistFollow.objects.filter(user=self.request.user)
            .order_by('-created_at')
            .values_list('artist_id', flat=True)
        )
        return User.objects.filter(pk__in=ids)


class MyFollowersView(generics.ListAPIView):
    """GET /api/music/users/me/followers/"""
    serializer_class = ArtistBriefSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        ids = list(
            ArtistFollow.objects.filter(artist=self.request.user)
            .order_by('-created_at')
            .values_list('user_id', flat=True)
        )
        return User.objects.filter(pk__in=ids)


class UserSearchView(APIView):
    """GET /api/music/users/search/?q=xxx — kullanıcı arama."""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        q = request.query_params.get('q', '').strip()
        if not q:
            return Response([])
        users = User.objects.filter(username__icontains=q).exclude(pk=request.user.pk)[:20]
        data = ArtistBriefSerializer(users, many=True, context={'request': request}).data
        return Response(data)


class ActivityFeedView(APIView):
    """
    GET /api/music/social/feed/

    Takip edilen kullanıcıların son dinlediği şarkılar — en yeni önce.
    Her (user, song) çifti tek kayıt olarak döner.
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        followed_ids = list(
            ArtistFollow.objects.filter(user=request.user)
            .values_list('artist_id', flat=True)
        )
        if not followed_ids:
            return Response([])

        latest = (
            ListenHistory.objects.filter(user_id__in=followed_ids)
            .values('user', 'song')
            .annotate(last=Max('listened_at'))
            .order_by('-last')[:50]
        )

        pairs = [(r['user'], r['song'], r['last']) for r in latest]
        user_ids = {p[0] for p in pairs}
        song_ids = {p[1] for p in pairs}

        users_map = {u.id: u for u in User.objects.filter(pk__in=user_ids)}
        songs_map = {
            s.id: s for s in Song.objects.filter(pk__in=song_ids).select_related('artist', 'album')
        }

        context = {
            'request': request,
            'liked_song_ids': set(
                SongLike.objects.filter(user=request.user, song_id__in=song_ids)
                .values_list('song_id', flat=True)
            ),
        }

        feed = []
        for uid, sid, last in pairs:
            u = users_map.get(uid)
            s = songs_map.get(sid)
            if not u or not s:
                continue
            feed.append({
                'user': {'id': u.id, 'username': u.username},
                'song': SongListSerializer(s, context=context).data,
                'listened_at': last,
            })
        return Response(feed)
