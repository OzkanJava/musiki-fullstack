"""
Bir kayit dosyasinin ne durumda oldugunu analiz eder.
FILE_PATH'i degistirip calistir — detayli teshis raporu verir.

    cd musiki_backend
    python -m scripts.diagnose_recording
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np


if len(sys.argv) > 1:
    FILE_PATH = sys.argv[1]
else:
    FILE_PATH = r"C:\Users\ozkan\Documents\Ses Kayıtları\oje.wav"


def ffprobe_info(path: str) -> dict:
    """ffprobe ile dosya metadatasini al."""
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_format', '-show_streams',
         '-of', 'json', path],
        capture_output=True, text=True, check=True,
    )
    import json
    return json.loads(result.stdout)


def to_mono44k(path: str) -> str:
    """Mono 44100Hz WAV'a donustur."""
    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    tmp.close()
    subprocess.run(
        ['ffmpeg', '-y', '-i', path, '-ac', '1', '-ar', '44100',
         '-c:a', 'pcm_s16le', tmp.name],
        capture_output=True, check=True,
    )
    return tmp.name


def read_samples(wav_path: str) -> tuple[np.ndarray, int]:
    from seekture.wav_reader import read_wav_info
    info = read_wav_info(wav_path)
    return np.array(info['left_samples'], dtype=np.float64), info['sample_rate']


def analyze(path: str) -> None:
    print("=" * 80)
    print(f"  DOSYA: {path}")
    print("=" * 80)

    # ── 1. Metadata ─────────────────────────────────────────────
    print("\n[1] Metadata (ffprobe)")
    try:
        info = ffprobe_info(path)
        stream = info['streams'][0]
        fmt = info['format']
        print(f"    Codec          : {stream.get('codec_name', '?')}")
        print(f"    Sample rate    : {stream.get('sample_rate', '?')} Hz")
        print(f"    Channels       : {stream.get('channels', '?')}")
        print(f"    Bits per sample: {stream.get('bits_per_sample', '?')}")
        print(f"    Duration       : {float(fmt.get('duration', 0)):.2f} s")
        print(f"    Bitrate        : {int(fmt.get('bit_rate', 0))//1000} kbps")
        print(f"    Size           : {int(fmt.get('size', 0))/1024/1024:.2f} MB")
    except Exception as e:
        print(f"    ffprobe hata: {e}")
        return

    # ── 2. Sample analizi ──────────────────────────────────────
    print("\n[2] Sinyal istatistikleri (mono 44100Hz'e normalize edildi)")
    wav = to_mono44k(path)
    try:
        samples, sr = read_samples(wav)
    finally:
        os.unlink(wav)

    n = len(samples)
    duration = n / sr
    peak = float(np.max(np.abs(samples)))
    rms = float(np.sqrt(np.mean(samples ** 2)))
    peak_db = 20 * np.log10(peak) if peak > 0 else -120
    rms_db = 20 * np.log10(rms) if rms > 0 else -120
    crest = peak / rms if rms > 0 else 0

    print(f"    Duration       : {duration:.2f}s ({n} sample)")
    print(f"    Peak           : {peak:.4f}  ({peak_db:.1f} dBFS)")
    print(f"    RMS            : {rms:.4f}  ({rms_db:.1f} dBFS)")
    print(f"    Crest factor   : {crest:.1f}  (muzik tipik 10-20, konusma 15-25)")

    # DC offset
    dc = float(np.mean(samples))
    print(f"    DC offset      : {dc:.5f}  (ideal 0, >0.01 problem)")

    # Clipping kontrol
    clip_ratio = float(np.sum(np.abs(samples) >= 0.99)) / n
    print(f"    Clipping       : {clip_ratio*100:.2f}%  (>1% klip olmus demek)")

    # Ses yuksekligi yorumu
    print(f"\n    Yorum:")
    if rms_db < -50:
        print(f"      [!] COK SESSIZ ({rms_db:.1f}dB) — mikrofon cok uzakta veya volume cok dusuk")
    elif rms_db < -35:
        print(f"      [~] Dusuk seviyeli ({rms_db:.1f}dB) — muzik ama uzaktan/alcak sesli")
    elif rms_db < -20:
        print(f"      [OK] Normal muzik seviyesi ({rms_db:.1f}dB)")
    else:
        print(f"      [!] COK YUKSEK ({rms_db:.1f}dB) — clipping olabilir")

    if clip_ratio > 0.01:
        print(f"      [!] Clipping var — peak limiter devrede olabilir, kalite bozulmus")

    # ── 3. Frekans analizi ──────────────────────────────────────
    print("\n[3] Spektral dagilim (FFT uzerinden, bant enerjileri)")
    # Tum sinyalin FFT'si
    fft = np.abs(np.fft.rfft(samples))
    freqs = np.fft.rfftfreq(n, 1 / sr)

    # dB olarak
    fft_db = 20 * np.log10(fft + 1e-10)
    fft_db -= np.max(fft_db)  # peak-normalize

    bands = [
        ('Sub (0-50 Hz)',       0,     50),
        ('Bass (50-250 Hz)',    50,    250),
        ('Lo-mid (250-500 Hz)', 250,   500),
        ('Mid (500-2000 Hz)',   500,   2000),
        ('Hi-mid (2-4 kHz)',    2000,  4000),
        ('Presence (4-6 kHz)',  4000,  6000),
        ('Brilliance (6-20k)',  6000,  20000),
    ]

    print(f"    {'Band':<22} {'Max dB':>8}  Gorsel")
    for name, lo, hi in bands:
        mask = (freqs >= lo) & (freqs < hi)
        if not mask.any():
            continue
        max_db = float(np.max(fft_db[mask]))
        bar = '#' * max(0, int(60 + max_db))  # -60..0 -> 0..60
        print(f"    {name:<22} {max_db:>7.1f}  {bar}")

    # Muzik mi konusma mi ipuclari
    print(f"\n    Yorum:")
    mid_energy = float(np.max(fft_db[(freqs >= 500) & (freqs < 4000)]))
    high_energy = float(np.max(fft_db[(freqs >= 4000) & (freqs < 8000)]))
    low_energy = float(np.max(fft_db[(freqs >= 50) & (freqs < 500)]))

    if high_energy < -20:
        print(f"      [!] 4kHz+ enerjisi cok dusuk ({high_energy:.1f}dB). Muhtemel sebepler:")
        print(f"          - Hoparlor kotu (tiz yok)")
        print(f"          - Mikrofon kotu (hi-freq rolloff)")
        print(f"          - Uzaktan kayit (yuksek frekanslar once kaybolur)")
    if low_energy < -20:
        print(f"      [!] Bass ({low_energy:.1f}dB) zayif")

    # ── 4. Geçici (temporal) kontrol ─────────────────────────────
    print("\n[4] Zaman bolgesi kontrol (RMS window = 500ms)")
    win_size = int(sr * 0.5)
    hops = n // win_size
    rms_per_window = []
    for i in range(hops):
        seg = samples[i*win_size:(i+1)*win_size]
        w_rms = np.sqrt(np.mean(seg ** 2))
        w_db = 20 * np.log10(w_rms) if w_rms > 0 else -120
        rms_per_window.append(w_db)

    if rms_per_window:
        rms_arr = np.array(rms_per_window)
        print(f"    Min window RMS : {float(rms_arr.min()):.1f} dBFS")
        print(f"    Max window RMS : {float(rms_arr.max()):.1f} dBFS")
        print(f"    Std dev        : {float(rms_arr.std()):.1f} dB")
        silent_windows = int(np.sum(rms_arr < -50))
        print(f"    Sessiz pencere : {silent_windows}/{len(rms_arr)}  (>%30 ise sorun)")

        # Profile plot
        print(f"\n    Zaman profili (her karakter ~0.5s):")
        for db in rms_arr:
            # -60 -> 0, 0 -> 30
            bar = '#' * max(1, int((db + 60) / 2))
            print(f"    {db:>6.1f}dB  {bar}")


if __name__ == '__main__':
    analyze(FILE_PATH)
