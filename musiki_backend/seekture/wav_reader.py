"""
Birebir port: seek-tune/server/wav/wav.go → ReadWavInfo
16-bit PCM WAV okuyucu. Mono ve stereo destekler.
"""
import struct


def read_wav_info(filename):
    """
    Go karşılığı: wav.ReadWavInfo(filename)
    Returns dict with keys: channels, sample_rate, duration,
                             data, left_samples, right_samples
    """
    with open(filename, 'rb') as f:
        data = f.read()

    if len(data) < 44:
        raise ValueError("Invalid WAV file size (too small)")

    # ── Header parse (binary.LittleEndian) ────────────────────────────
    chunk_id = data[0:4]
    format_tag = data[8:12]
    audio_format = struct.unpack_from('<H', data, 20)[0]
    num_channels = struct.unpack_from('<H', data, 22)[0]
    sample_rate = struct.unpack_from('<I', data, 24)[0]
    bits_per_sample = struct.unpack_from('<H', data, 34)[0]

    if chunk_id != b'RIFF' or format_tag != b'WAVE' or audio_format != 1:
        raise ValueError("Invalid WAV header format")
    if bits_per_sample != 16:
        raise ValueError("Unsupported bits-per-sample (expect 16-bit PCM)")

    # ── 'data' chunk'ını bul (ffmpeg LIST gibi ekstra chunk ekleyebilir) ──
    data_offset = data.find(b'data', 36)
    if data_offset == -1:
        raise ValueError("Could not find 'data' chunk in WAV file")
    audio_data = data[data_offset + 8:]  # 4 byte 'data' + 4 byte size
    sample_count = len(audio_data) // 2
    int16_samples = struct.unpack_from(f'<{sample_count}h', audio_data)

    SCALE = 1.0 / 32768.0  # 16-bit normalisation

    info = {
        'channels': num_channels,
        'sample_rate': sample_rate,
        'data': audio_data,
        'left_samples': None,
        'right_samples': None,
        'duration': 0.0,
    }

    if num_channels == 1:
        info['left_samples'] = [s * SCALE for s in int16_samples]
        info['right_samples'] = None
        info['duration'] = sample_count / sample_rate

    elif num_channels == 2:
        frame_count = sample_count // 2
        info['left_samples'] = [int16_samples[2 * i] * SCALE for i in range(frame_count)]
        info['right_samples'] = [int16_samples[2 * i + 1] * SCALE for i in range(frame_count)]
        # Go: float64(sampleCount) / (float64(header.NumChannels) * float64(header.SampleRate))
        info['duration'] = sample_count / (num_channels * sample_rate)

    else:
        raise ValueError("Unsupported channel count (only mono/stereo)")

    return info
