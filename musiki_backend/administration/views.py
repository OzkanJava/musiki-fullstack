from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsAdmin
from django.contrib.auth import get_user_model
from music.models import Song
from .serializers import PendingArtistSerializer, DeletedSongSerializer

User = get_user_model()


class PendingArtistsView(generics.ListAPIView):
    """Admin: onay bekleyen sanatçıları listele."""
    serializer_class = PendingArtistSerializer
    permission_classes = (IsAdmin,)

    def get_queryset(self):
        return User.objects.filter(role='artist', is_approved_artist=False)


class ApproveArtistView(APIView):
    """Admin: sanatçıyı onayla."""
    permission_classes = (IsAdmin,)

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk, role='artist')
        except User.DoesNotExist:
            return Response({'detail': 'Sanatçı bulunamadı.'}, status=status.HTTP_404_NOT_FOUND)

        user.is_approved_artist = True
        user.approved_at = timezone.now()
        user.save(update_fields=['is_approved_artist', 'approved_at'])
        return Response({'detail': f'{user.username} onaylandı.'})


class RejectArtistView(APIView):
    """Admin: sanatçı başvurusunu reddet (listener'a düşür)."""
    permission_classes = (IsAdmin,)

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk, role='artist', is_approved_artist=False)
        except User.DoesNotExist:
            return Response({'detail': 'Bekleyen sanatçı bulunamadı.'}, status=status.HTTP_404_NOT_FOUND)

        user.role = 'listener'
        user.save(update_fields=['role'])
        return Response({'detail': f'{user.username} başvurusu reddedildi.'})


class DeletedSongsView(generics.ListAPIView):
    """Admin: silinmiş şarkıları listele."""
    serializer_class = DeletedSongSerializer
    permission_classes = (IsAdmin,)

    def get_queryset(self):
        return Song.objects.deleted_only()


class RestoreSongView(APIView):
    """Admin: silinmiş şarkıyı geri yükle."""
    permission_classes = (IsAdmin,)

    def post(self, request, pk):
        try:
            song = Song.objects.deleted_only().get(pk=pk)
        except Song.DoesNotExist:
            return Response({'detail': 'Silinmiş şarkı bulunamadı.'}, status=status.HTTP_404_NOT_FOUND)

        song.restore()
        return Response({'detail': f"'{song.title}' geri yüklendi."})
