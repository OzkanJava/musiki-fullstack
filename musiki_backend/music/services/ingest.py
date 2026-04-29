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
    """ffmpeg ile mono 44100 Hz 16-bit PCM WAV'a donustur."""
    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    tmp.close()
    cmd = [
        'ffmpeg', '-y', '-i', input_path,
        '-ac', '1', '-ar', '44100', '-c:a', 'pcm_s16le',
        tmp.name,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return tmp.name


def ingest_song(song) -> int:
    """
    Şarkının parmak izini seekture algoritmasıyla çıkarır ve SQLite DB'ye kaydeder.
    Django Song.id, seekture song_id olarak kullanılır — doğrudan eşleşme sağlar.
    Returns: oluşturulan fingerprint sayısı
    """
    from seekture.fingerprint import fingerprint_audio_full

    logger.info(f"Seekture ingest başlatılıyor: '{song.title}' [{song.audio_file.path}]")

    wav_path = None
    need_cleanup = False
    try:
        src_path = song.audio_file.path
        if not src_path.lower().endswith('.wav'):
            wav_path = _convert_to_wav(src_path)
            need_cleanup = True
        else:
            wav_path = src_path

        from seekture.wav_reader import read_wav_info
        wav_info = read_wav_info(wav_path)
        fps = fingerprint_audio_full(wav_path, song.id)
        duration = round(wav_info['duration'], 2)
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg dönüşüm hatası '{song.title}': {e}")
        return 0
    except Exception as e:
        logger.error(f"Fingerprint hatası '{song.title}': {e}")
        return 0
    finally:
        if need_cleanup and wav_path and os.path.exists(wav_path):
            os.unlink(wav_path)

    if not fps:
        logger.warning(f"'{song.title}' için fingerprint üretilemedi.")
        return 0

    db = _get_seekture_db()
    try:
        db.store_song_with_id(song.id, song.title, song.artist.username)
        db.store_fingerprints(fps)
    finally:
        db.close()

    song.is_fingerprinted = True
    song.duration = duration
    song.save(update_fields=['is_fingerprinted', 'duration'])

    logger.info(f"'{song.title}': {len(fps)} fingerprint kaydedildi (song_id={song.id})")
    return len(fps)
