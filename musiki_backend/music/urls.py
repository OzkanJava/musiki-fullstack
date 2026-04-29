from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AlbumViewSet, SongViewSet, RecognizeView,
    RecordListenView, ListenHistoryView,
    PlaylistViewSet,
    ArtistFollowView, FollowedArtistsView,
    ArtistListView, ArtistDetailView,
    HomeRecentlyPlayedView, HomeForYouView,
    UserFollowView, UserProfileView,
    MyFollowingView, MyFollowersView, UserSearchView,
    ActivityFeedView,
)

router = DefaultRouter()
router.register('albums', AlbumViewSet, basename='album')
router.register('songs', SongViewSet, basename='song')
router.register('playlists', PlaylistViewSet, basename='playlist')

urlpatterns = [
    path('', include(router.urls)),
    path('recognize/', RecognizeView.as_view(), name='music-recognize'),
    path('history/', ListenHistoryView.as_view(), name='music-history'),
    path('history/record/', RecordListenView.as_view(), name='music-record-listen'),

    # Artist list / follow / detail
    path('artists/', ArtistListView.as_view(), name='artist-list'),
    path('artists/followed/', FollowedArtistsView.as_view(), name='artists-followed'),
    path('artists/<int:pk>/follow/', ArtistFollowView.as_view(), name='artist-follow'),
    path('artists/<int:pk>/', ArtistDetailView.as_view(), name='artist-detail'),

    # Home feed shelves
    path('home/recently-played/', HomeRecentlyPlayedView.as_view(), name='home-recently-played'),
    path('home/for-you/', HomeForYouView.as_view(), name='home-for-you'),

    # Social (Faz D)
    path('users/search/', UserSearchView.as_view(), name='user-search'),
    path('users/me/following/', MyFollowingView.as_view(), name='my-following'),
    path('users/me/followers/', MyFollowersView.as_view(), name='my-followers'),
    path('users/<int:pk>/follow/', UserFollowView.as_view(), name='user-follow'),
    path('users/<int:pk>/', UserProfileView.as_view(), name='user-profile'),
    path('social/feed/', ActivityFeedView.as_view(), name='activity-feed'),
]
