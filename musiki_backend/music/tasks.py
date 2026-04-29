import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def fingerprint_song_task(self, song_id: int):
    from music.models import Song
    from music.services.ingest import ingest_song

    try:
        song = Song.objects.get(id=song_id)
        count = ingest_song(song)
        return {'status': 'ok', 'song_id': song_id, 'hashes': count}
    except Song.DoesNotExist:
        logger.error(f"Song {song_id} bulunamadı")
        return {'status': 'error', 'detail': 'not found'}
    except Exception as exc:
        logger.error(f"Fingerprint task hatası song_id={song_id}: {exc}")
        raise self.retry(exc=exc, countdown=30)
