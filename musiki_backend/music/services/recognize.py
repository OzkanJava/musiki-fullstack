import logging
import os
import subprocess
import tempfile

from django.conf import settings

logger = logging.getLogger(__name__)


def _get_seekture_db():
    from seekture.db_client import SQLiteClient
    db_path = getattr(settings, 'SEEKTURE_DB_PATH', 'seekture.db')
    return SQLiteClient(db_path)


def _convert_to_wav(input_path):
    """ffmpeg ile mono 44100 Hz 16-bit PCM WAV'a dönüştür."""
    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    tmp.close()
    cmd = [
        'ffmpeg', '-y', '-i', input_path,
        '-ac', '1', '-ar', '44100', '-c:a', 'pcm_s16le',
        tmp.name,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return tmp.name


def recognize_audio(file_path: str) -> dict | None:
    """
    Verilen ses dosyasını seekture algoritmasıyla veritabanındaki şarkılarla eşleştirir.
    Returns: {"song_id", "title", "artist", "album", "confidence"} veya None
    """
    from seekture.fingerprint import fingerprint_audio
    from seekture.matcher import find_matches_fgp

    wav_path = None
    need_cleanup = False
    try:
        if not file_path.lower().endswith('.wav'):
            wav_path = _convert_to_wav(file_path)
            need_cleanup = True
        else:
            wav_path = file_path

        fps = fingerprint_audio(wav_path, 0)
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg dönüşüm hatası (recognize): {e}")
        return None
    except Exception as e:
        logger.error(f"Fingerprint hatası (recognize): {e}")
        return None
    finally:
        if need_cleanup and wav_path and os.path.exists(wav_path):
            os.unlink(wav_path)

    if not fps:
        logger.warning("Tanıma için fingerprint üretilemedi.")
        return {'accepted': False, 'song': None, 'candidate': None,
                'reason': 'silence', 'total_hashes': 0}

    # address -> anchor_time_ms haritası (matcher için)
    sample_map = {addr: c.anchor_time_ms for addr, c in fps.items()}

    db = _get_seekture_db()
    try:
        matches = find_matches_fgp(sample_map, db)
    finally:
        db.close()

    if not matches:
        return {'accepted': False, 'song': None, 'candidate': None,
                'reason': 'no_match', 'total_hashes': len(fps)}

    best = matches[0]
    quality = best.get('match_quality', 'LOW')
    song_id = best['song_id']
    score = best['score']
    ratio = best.get('ratio', 0.0)
    total_hashes = len(fps)
    relative = score / total_hashes if total_hashes > 0 else 0.0

    # Django'dan sarki bilgisini al (REJECTED icin bile, debug amacli)
    from music.models import Song
    try:
        song_obj = Song.objects.select_related('artist', 'album').get(id=song_id)
        candidate = {
            'song_id': song_obj.id,
            'title': song_obj.title,
            'artist': song_obj.artist.username,
            'album': song_obj.album.title if song_obj.album else None,
            'confidence': int(score),
            'relative_confidence': round(relative, 3),
            'ratio': round(ratio, 2) if ratio != float('inf') else 999.0,
            'match_quality': quality,
        }
    except Song.DoesNotExist:
        logger.warning(f"Seekture song_id={song_id} Django DB'de bulunamadı.")
        candidate = None

    logger.info(
        f"Eslesme: song_id={song_id}, skor={score}, "
        f"ratio={ratio:.2f}, kalite={quality}"
    )

    # REJECTED -> song: null ama candidate bilgisi UI'da gosterilir
    if quality == 'REJECTED':
        return {'accepted': False, 'song': None, 'candidate': candidate,
                'reason': 'low_confidence', 'total_hashes': total_hashes}

    return {'accepted': True, 'song': candidate, 'candidate': candidate,
            'reason': 'ok', 'total_hashes': total_hashes}
