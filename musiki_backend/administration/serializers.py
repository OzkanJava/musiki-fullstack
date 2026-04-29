from rest_framework import serializers
from django.contrib.auth import get_user_model
from music.models import Song

User = get_user_model()


class PendingArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'bio', 'date_joined')


class DeletedSongSerializer(serializers.ModelSerializer):
    artist_name = serializers.CharField(source='artist.username', read_only=True)

    class Meta:
        model = Song
        fields = ('id', 'title', 'artist_name', 'genre', 'deleted_at')
