import logging
import os
import subprocess
import tempfile

from django.conf import settings

logger = logging.getLogger(__name__)

TOP_N = 3


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


def _serialize_song(song_obj, request=None):
    """Tek şarkıyı UI'in beklediği sade yapıyla serialize et."""
    cover = song_obj.effective_cover
    cover_url = None
    if cover:
        cover_url = request.build_absolute_uri(cover.url) if request else cover.url

    album = None
    if song_obj.album:
        album = {'id': song_obj.album.id, 'title': song_obj.album.title}

    return {
        'song_id': song_obj.id,
        'title': song_obj.title,
        'artist': {'id': song_obj.artist.id, 'username': song_obj.artist.username},
        'album': album,
        'cover_image': cover_url,
    }


def recognize_audio(file_path: str, request=None) -> dict:
    """
    Ses dosyasını seekture algoritmasıyla DB'deki şarkılarla eşleştirir.

    Returns:
        {
            'accepted': bool,                 # top match güvenilir mi
            'candidates': [...],              # 0-3 eleman; tıklanabilir kartlar
            'reason': 'ok'|'silence'|'no_match'|'low_confidence',
            'detail': str | None,
        }
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
        return {'accepted': False, 'candidates': [],
                'reason': 'silence', 'detail': 'Ses dosyası işlenemedi.'}
    except Exception as e:
        logger.error(f"Fingerprint hatası (recognize): {e}")
        return {'accepted': False, 'candidates': [],
                'reason': 'silence', 'detail': 'Fingerprint üretilemedi.'}
    finally:
        if need_cleanup and wav_path and os.path.exists(wav_path):
            os.unlink(wav_path)

    if not fps:
        return {'accepted': False, 'candidates': [],
                'reason': 'silence',
                'detail': 'Kayıttan fingerprint üretilemedi (çok sessiz/gürültülü).'}

    sample_map = {addr: c.anchor_time_ms for addr, c in fps.items()}

    db = _get_seekture_db()
    try:
        matches = find_matches_fgp(sample_map, db)
    finally:
        db.close()

    if not matches:
        return {'accepted': False, 'candidates': [],
                'reason': 'no_match',
                'detail': 'Veritabanında eşleşen şarkı yok.'}

    top = matches[0]
    quality = top.get('match_quality', 'LOW')
    accepted = quality != 'REJECTED'

    from music.models import Song
    candidates = []
    for m in matches[:TOP_N]:
        try:
            song_obj = Song.objects.select_related('artist', 'album').get(id=m['song_id'])
        except Song.DoesNotExist:
            logger.warning(f"Seekture song_id={m['song_id']} Django DB'de yok.")
            continue
        candidates.append(_serialize_song(song_obj, request=request))

    if accepted:
        reason = 'ok'
        detail = None
    else:
        reason = 'low_confidence'
        detail = 'Tam emin değilim, en yakın tahminler:'

    logger.info(
        f"Recognize: accepted={accepted}, top_score={top['score']}, "
        f"quality={quality}, candidates={len(candidates)}"
    )

    return {
        'accepted': accepted,
        'candidates': candidates,
        'reason': reason,
        'detail': detail,
    }
