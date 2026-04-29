"""
Gercekci ortam simulasyonu ile taninma testi.

Kullanim:
    cd musiki_backend
    python -m seekture.noise_test                         # tum testler
    python -m seekture.noise_test --pos 30 --dur 8        # belirli pozisyon
    python -m seekture.noise_test --only clean,snr20      # belirli senaryolar

Senaryolar:
    clean      : Orijinal kesit (referans)
    snr20      : Beyaz gurultu SNR=20dB (sessiz oda)
    snr10      : Beyaz gurultu SNR=10dB (kafe ortami)
    snr5       : Beyaz gurultu SNR=5dB (gurultulu sokak)
    lowpass    : Alcak geciren filtre 3kHz (hoparlorden dinleme)
    volume     : %30 ses seviyesi (uzaktan duyma)
    reverb     : Basit oda yankisi simulasyonu
    combined   : SNR=15dB + lowpass 4kHz + reverb (gercekci senaryo)
"""
import argparse
import os
import subprocess
import sys
import tempfile
import time

import numpy as np

from .fingerprint import fingerprint_audio
from .matcher import find_matches_fgp
from .db_client import SQLiteClient
from .wav_reader import read_wav_info


def clip_to_wav(src_path, start, dur):
    """MP3'ten kesit al, mono 44100Hz WAV olarak dondur."""
    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    tmp.close()
    subprocess.run(
        ['ffmpeg', '-y', '-ss', str(start), '-t', str(dur),
         '-i', src_path, '-ac', '1', '-ar', '44100', '-c:a', 'pcm_s16le', tmp.name],
        capture_output=True, check=True,
    )
    return tmp.name


def read_samples(wav_path):
    """WAV dosyasindan float64 sample dizisi oku."""
    info = read_wav_info(wav_path)
    return np.array(info['left_samples'], dtype=np.float64), info['sample_rate']


def write_wav(samples, sample_rate, path):
    """float64 sample dizisini 16-bit PCM WAV olarak yaz."""
    import struct
    samples = np.clip(samples, -1.0, 1.0)
    int16 = (samples * 32767).astype(np.int16)
    raw = int16.tobytes()

    with open(path, 'wb') as f:
        # WAV header (44 bytes)
        num_channels = 1
        bits_per_sample = 16
        byte_rate = sample_rate * num_channels * bits_per_sample // 8
        block_align = num_channels * bits_per_sample // 8
        data_size = len(raw)

        f.write(b'RIFF')
        f.write(struct.pack('<I', 36 + data_size))
        f.write(b'WAVE')
        f.write(b'fmt ')
        f.write(struct.pack('<I', 16))  # subchunk1 size
        f.write(struct.pack('<H', 1))   # PCM
        f.write(struct.pack('<H', num_channels))
        f.write(struct.pack('<I', sample_rate))
        f.write(struct.pack('<I', byte_rate))
        f.write(struct.pack('<H', block_align))
        f.write(struct.pack('<H', bits_per_sample))
        f.write(b'data')
        f.write(struct.pack('<I', data_size))
        f.write(raw)


# ── Gurultu fonksiyonlari ────────────────────────────────────────────

def add_white_noise(samples, snr_db):
    """Beyaz gurultu ekle. SNR=20 sessiz oda, SNR=10 kafe, SNR=5 sokak."""
    signal_power = np.mean(samples ** 2)
    noise_power = signal_power / (10 ** (snr_db / 10))
    noise = np.random.normal(0, np.sqrt(noise_power), len(samples))
    return samples + noise


def apply_lowpass(samples, cutoff_hz, sample_rate):
    """Basit IIR alcak geciren filtre (hoparlor/duvar simulasyonu)."""
    import math
    rc = 1.0 / (2.0 * math.pi * cutoff_hz)
    dt = 1.0 / sample_rate
    alpha = dt / (rc + dt)

    out = np.empty_like(samples)
    out[0] = samples[0] * alpha
    for i in range(1, len(samples)):
        out[i] = alpha * samples[i] + (1 - alpha) * out[i - 1]
    return out


def reduce_volume(samples, factor):
    """Ses seviyesini dusur (0.3 = %30 volume, uzaktan duyma)."""
    return samples * factor


def add_reverb(samples, sample_rate, delay_ms=50, decay=0.3):
    """Basit oda yankisi — tek yansima."""
    delay_samples = int(sample_rate * delay_ms / 1000)
    out = samples.copy()
    if delay_samples < len(samples):
        out[delay_samples:] += samples[:-delay_samples] * decay
    return np.clip(out, -1.0, 1.0)


# ── Senaryo tanimlari ────────────────────────────────────────────────

SCENARIOS = {
    'clean': {
        'label': 'Temiz kesit (referans)',
        'fn': lambda s, sr: s,
    },
    'snr20': {
        'label': 'Beyaz gurultu SNR=20dB (sessiz oda)',
        'fn': lambda s, sr: add_white_noise(s, 20),
    },
    'snr10': {
        'label': 'Beyaz gurultu SNR=10dB (kafe)',
        'fn': lambda s, sr: add_white_noise(s, 10),
    },
    'snr5': {
        'label': 'Beyaz gurultu SNR=5dB (sokak)',
        'fn': lambda s, sr: add_white_noise(s, 5),
    },
    'lowpass': {
        'label': 'Lowpass 3kHz (hoparlorden)',
        'fn': lambda s, sr: apply_lowpass(s, 3000, sr),
    },
    'volume': {
        'label': '%30 volume (uzaktan)',
        'fn': lambda s, sr: reduce_volume(s, 0.3),
    },
    'reverb': {
        'label': 'Oda yankisi (50ms, 0.3 decay)',
        'fn': lambda s, sr: add_reverb(s, sr, 50, 0.3),
    },
    'combined': {
        'label': 'Gercekci: SNR15 + lowpass4k + reverb',
        'fn': lambda s, sr: add_reverb(
            apply_lowpass(add_white_noise(s, 15), 4000, sr),
            sr, 40, 0.25
        ),
    },
}


def test_scenario(scenario_key, songs, songs_dir, db, start, dur):
    """Bir senaryo icin tum sarkilari test et."""
    scenario = SCENARIOS[scenario_key]
    passed = 0
    failed = []

    for fname in songs:
        path = os.path.join(songs_dir, fname)
        expected = fname.rsplit('.', 1)[0]

        # 1. Kesit al
        wav_path = clip_to_wav(path, start, dur)
        try:
            # 2. Sample'lari oku
            samples, sr = read_samples(wav_path)
            os.unlink(wav_path)

            # 3. Gurultu/efekt uygula
            modified = scenario['fn'](samples, sr)

            # 4. Gecici WAV yaz
            tmp_path = wav_path + '_mod.wav'
            write_wav(modified, sr, tmp_path)

            # 5. Fingerprint + match
            fps = fingerprint_audio(tmp_path, 0)
            os.unlink(tmp_path)

            if not fps:
                failed.append((expected.split(' - ', 1)[-1][:18], 0, 0))
                continue

            sample_map = {addr: c.anchor_time_ms for addr, c in fps.items()}
            matches = find_matches_fgp(sample_map, db)

            if matches:
                top = matches[0]['artist'] + ' - ' + matches[0]['title']
                score = matches[0]['score']
                second = matches[1]['score'] if len(matches) > 1 else 0
                # Case-insensitive karsilastirma (DB'de artist username lowercase olabilir)
                if top.lower() == expected.lower():
                    passed += 1
                else:
                    failed.append((expected.split(' - ', 1)[-1][:18], int(score), int(second)))
            else:
                failed.append((expected.split(' - ', 1)[-1][:18], 0, 0))
        except Exception as e:
            if os.path.exists(wav_path):
                os.unlink(wav_path)
            failed.append((expected.split(' - ', 1)[-1][:18], 0, 0))

    return passed, len(songs), failed


def main():
    parser = argparse.ArgumentParser(description='Seekture - Gurultu Testi')
    parser.add_argument('--dir', default='media/songs', help='Sarki klasoru')
    parser.add_argument('--db', default='seekture.db', help='SQLite DB')
    parser.add_argument('--pos', type=float, default=30, help='Kesit baslangici (saniye)')
    parser.add_argument('--dur', type=float, default=8, help='Kesit suresi (saniye)')
    parser.add_argument('--only', default=None, help='Sadece belirli senaryolar (virgul ile)')
    args = parser.parse_args()

    db = SQLiteClient(args.db)
    songs = sorted([f for f in os.listdir(args.dir) if f.lower().endswith(('.mp3', '.wav', '.flac'))])
    total_songs = len(songs)

    if args.only:
        keys = [k.strip() for k in args.only.split(',')]
    else:
        keys = list(SCENARIOS.keys())

    print(f"{total_songs} sarki, {args.dur:.0f}s kesit @ {args.pos:.0f}s")
    print(f"{'=' * 70}\n")

    header = f"{'SENARYO':<12} {'ACIKLAMA':<38} {'SONUC':>8}  HATALAR"
    print(header)
    print('-' * 70)

    for key in keys:
        scenario = SCENARIOS[key]
        t0 = time.time()
        passed, total, failed = test_scenario(key, songs, args.dir, db, args.pos, args.dur)
        elapsed = time.time() - t0

        pct = f"{passed}/{total}"
        fail_str = ', '.join([f'{n}' for n, s, s2 in failed[:5]]) if failed else '-'
        if len(failed) > 5:
            fail_str += f' +{len(failed)-5}'
        print(f"{key:<12} {scenario['label']:<38} {pct:>8}  {fail_str}")

    print('-' * 70)
    db.close()


if __name__ == '__main__':
    main()
