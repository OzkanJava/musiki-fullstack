"""
Orijinal port: seek-tune/server/shazam/spectrogram.go

IYILESTIRME (Musiki v2):
Peak extraction'a global esik eklendi. Orijinal SeekTune algoritmasi sadece
per-frame ortalamaya bakiyordu: sessiz veya gurultulu framelerde bile 3-4
peak uretip yuzlerce sahte fingerprint yaratiyordu. Bu, sessiz ortamlarda
bile %88+ false-positive oranina sebep oluyordu.

Yeni kosul: peak secilmesi icin hem (a) frame ortalamasini asmali hem de
(b) GLOBAL esigi (spectrogram genel statistiklerine dayali) asmali.

Parametreler env vars ile ayarlanabilir (PEAK_GLOBAL_PERCENTILE,
PEAK_MIN_ABS_RATIO) — varsayilanlar judgement-based seciliyor.
"""
import math
import os
import numpy as np
from .models import Peak

# ── DSP Sabitleri (SeekTune ile ayni — hash formati bozulmasin) ──────────
DSP_RATIO = 4
WINDOW_SIZE = 1024
MAX_FREQ = 5000.0            # 5 kHz
HOP_SIZE = WINDOW_SIZE // 2  # 512 — 50% overlap
WINDOW_TYPE = "hanning"

# ── Frekans bantlari (hash uretimi icin) ─────────────────────────────────
BANDS = [
    (0, 10),
    (10, 20),
    (20, 40),
    (40, 80),
    (80, 160),
    (160, 512),
]

# ── Peak extraction esikleri (IYILESTIRME — env ile ayarlanabilir) ──────
# Global persentil: butun spectrogram magnitudelerinin N'inci persentili.
# Peak bunun uzerinde olmali. Yuksek deger = daha agresif filtre.
PEAK_GLOBAL_PERCENTILE = float(os.environ.get('PEAK_GLOBAL_PERCENTILE', '0.0'))

# Mutlak esik: global_max * oran. Sessizlikte bile bir minimum enerji sarti.
# 0.02 = ~-34dB (global max'in %2'si). Dusuk deger = daha fazla peak.
PEAK_MIN_ABS_RATIO = float(os.environ.get('PEAK_MIN_ABS_RATIO', '0.02'))

# Minimum sessizlik enerji esigi — cok sessiz tum spektrogramlari reddetmek icin.
# Global max bu degerin altindaysa hic peak uretilmez (silence gate).
PEAK_SILENCE_GLOBAL_MAX = float(os.environ.get('PEAK_SILENCE_GLOBAL_MAX', '0.5'))


def low_pass_filter(cutoff_freq, sample_rate, input_signal):
    """
    Go karşılığı: LowPassFilter(cutoffFrequency, sampleRate, input)
    Birinci derece IIR alçak geçiren filtre.
    H(s) = 1 / (1 + sRC)
    """
    rc = 1.0 / (2.0 * math.pi * cutoff_freq)
    dt = 1.0 / sample_rate
    alpha = dt / (rc + dt)
    beta = 1.0 - alpha

    x = np.asarray(input_signal, dtype=np.float64)
    y = np.empty(len(x), dtype=np.float64)

    y[0] = x[0] * alpha
    for i in range(1, len(x)):
        y[i] = alpha * x[i] + beta * y[i - 1]

    return y


def downsample(input_signal, original_sr, target_sr):
    """
    Go karşılığı: Downsample(input, originalSampleRate, targetSampleRate)
    Ardışık örneklerin ortalamasını alarak alt-örnekleme.
    """
    if target_sr <= 0 or original_sr <= 0:
        raise ValueError("Sample rates must be positive")
    if target_sr > original_sr:
        raise ValueError("Target sample rate must be <= original sample rate")

    ratio = original_sr // target_sr
    resampled = []
    n = len(input_signal)

    for i in range(0, n, ratio):
        end = min(i + ratio, n)
        chunk = input_signal[i:end]
        avg = float(np.mean(chunk))
        resampled.append(avg)

    return resampled


def make_spectrogram(sample, sample_rate):
    """
    Go karşılığı: Spectrogram(sample, sampleRate)
    1) Alçak geçiren filtre (5 kHz)
    2) 4x alt-örnekleme
    3) STFT (Hanning pencere, 1024 window, 512 hop)
    4) Magnitude spectrogram
    """
    filtered = low_pass_filter(MAX_FREQ, float(sample_rate), sample)
    downsampled = downsample(filtered, sample_rate, sample_rate // DSP_RATIO)
    ds = np.array(downsampled, dtype=np.float64)

    # ── Pencere fonksiyonu (Go: for i range window { ... }) ───────────
    window = np.empty(WINDOW_SIZE, dtype=np.float64)
    for i in range(WINDOW_SIZE):
        theta = 2.0 * math.pi * float(i) / float(WINDOW_SIZE - 1)
        if WINDOW_TYPE == "hamming":
            window[i] = 0.54 - 0.46 * math.cos(theta)
        else:  # hanning
            window[i] = 0.5 - 0.5 * math.cos(theta)

    # ── STFT ──────────────────────────────────────────────────────────
    spectrogram = []
    start = 0
    while start + WINDOW_SIZE <= len(ds):
        frame = ds[start:start + WINDOW_SIZE].copy()
        frame *= window

        # Go: FFT(frame) → numpy.fft.fft (matematiksel olarak özdeş)
        fft_result = np.fft.fft(frame)

        # Go: magnitude = abs(fftResult[:len/2])
        magnitude = np.abs(fft_result[:len(fft_result) // 2])
        spectrogram.append(magnitude.tolist())

        start += HOP_SIZE

    return spectrogram


def _compute_global_threshold(spectrogram: list) -> tuple[float, float]:
    """
    Tum spectrogram uzerinden global esik hesapla.
    Sadece per-band max degerlerini dikkate alir (her frame'de 6 deger).
    Returns (global_threshold, global_max).
    """
    band_maxes = []
    for frame in spectrogram:
        for band_min, band_max in BANDS:
            upper = min(band_max, len(frame))
            if upper <= band_min:
                continue
            mx = 0.0
            for idx in range(band_min, upper):
                if frame[idx] > mx:
                    mx = frame[idx]
            band_maxes.append(mx)

    if not band_maxes:
        return 0.0, 0.0

    arr = np.asarray(band_maxes, dtype=np.float64)
    global_max = float(np.max(arr))
    global_p = float(np.percentile(arr, PEAK_GLOBAL_PERCENTILE))
    abs_floor = global_max * PEAK_MIN_ABS_RATIO
    threshold = max(global_p, abs_floor)
    return threshold, global_max


def extract_peaks(spectrogram, audio_duration, sample_rate):
    """
    Her zaman diliminde 6 frekans bandinda peak arar.
    IYILESTIRME: Peak sadece (a) frame ortalamasini asarsa VE (b) global
    esigi asarsa kabul edilir. Bu, sessiz/gurultulu framelerde sahte peak
    uretimini engeller.
    """
    if len(spectrogram) < 1:
        return []

    # Global esik hesapla (tum spectrogram uzerinden, bir kez)
    global_threshold, global_max = _compute_global_threshold(spectrogram)

    # Silence gate: cok sessiz spektrogramlari tamamen reddet
    # (dijital sessizlik, cok dusuk gurultu, vs.)
    if global_max < PEAK_SILENCE_GLOBAL_MAX:
        return []

    peaks = []

    effective_sr = float(sample_rate) / float(DSP_RATIO)
    freq_resolution = effective_sr / float(WINDOW_SIZE)
    frame_duration = float(HOP_SIZE) / effective_sr

    for frame_idx, frame in enumerate(spectrogram):
        max_mags = []
        freq_indices = []

        for band_min, band_max in BANDS:
            best_mag = 0.0
            best_freq_idx = band_min
            upper = min(band_max, len(frame))
            for idx in range(band_min, upper):
                if frame[idx] > best_mag:
                    best_mag = frame[idx]
                    best_freq_idx = idx
            max_mags.append(best_mag)
            freq_indices.append(best_freq_idx)

        avg = sum(max_mags) / len(max_mags) if max_mags else 0.0

        # IYILESTIRME: Telefon mikrofonlarindaki asiri Mid/HighEQ yuzunden
        # zayif frekans bantlari (Bass vs) ortalamanin altinda kalip eleniyordu.
        # Bu yuzden capraz bant maskelemesini engellemek icin avg * 0.7 kullandik.
        for i, mag in enumerate(max_mags):
            if mag > (avg * 0.7) and mag > global_threshold:
                peak_time = float(frame_idx) * frame_duration
                peak_freq = float(freq_indices[i]) * freq_resolution
                peaks.append(Peak(freq=peak_freq, time=peak_time))

    return peaks
