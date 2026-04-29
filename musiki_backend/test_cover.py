import os, django
from django.core.files.uploadedfile import SimpleUploadedFile
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()
from music.serializers import SongUploadSerializer
from music.models import Song
from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.first()

import io
from PIL import Image
img = Image.new('RGB', (100, 100), color='red')
img_byte_arr = io.BytesIO()
img.save(img_byte_arr, format='JPEG')
img_byte_arr = img_byte_arr.getvalue()

f_audio = SimpleUploadedFile('test.mp3', b'file_content', content_type='audio/mpeg')
f_img = SimpleUploadedFile('cover.jpg', img_byte_arr, content_type='image/jpeg')

s = SongUploadSerializer(data={'title': 'test3', 'genre': 'rock'})
s.initial_data['audio_file'] = f_audio
s.initial_data['cover_image'] = f_img
print(s.is_valid(), s.errors)
if s.is_valid():
    song = s.save(artist=user)
    print("Song ID:", song.id, "Cover:", bool(song.cover_image))
