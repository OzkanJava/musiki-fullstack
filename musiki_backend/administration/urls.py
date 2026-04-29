from django.urls import path
from .views import (
    PendingArtistsView, ApproveArtistView, RejectArtistView,
    DeletedSongsView, RestoreSongView,
)

urlpatterns = [
    path('artists/pending/', PendingArtistsView.as_view(), name='admin-pending-artists'),
    path('artists/<int:pk>/approve/', ApproveArtistView.as_view(), name='admin-approve-artist'),
    path('artists/<int:pk>/reject/', RejectArtistView.as_view(), name='admin-reject-artist'),
    path('songs/deleted/', DeletedSongsView.as_view(), name='admin-deleted-songs'),
    path('songs/<int:pk>/restore/', RestoreSongView.as_view(), name='admin-restore-song'),
]
