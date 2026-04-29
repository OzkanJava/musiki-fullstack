import django_filters
from .models import Song, Album


class SongFilter(django_filters.FilterSet):
    artist = django_filters.NumberFilter(field_name='artist__id')
    album = django_filters.NumberFilter(field_name='album__id')
    genre = django_filters.CharFilter(field_name='genre', lookup_expr='exact')
    is_fingerprinted = django_filters.BooleanFilter()

    class Meta:
        model = Song
        fields = ('artist', 'album', 'genre', 'is_fingerprinted')


class AlbumFilter(django_filters.FilterSet):
    artist = django_filters.NumberFilter(field_name='artist__id')

    class Meta:
        model = Album
        fields = ('artist',)
