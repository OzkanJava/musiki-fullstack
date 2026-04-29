"""
False-positive testi — asil teshis araci.

"Rock-solid Shazam" icin: muzik olmayan girdilere karsilik HIC eslestirme
dondurulmemeli (veya cok dusuk skorla). Mevcut algoritmada bunun duzgun
calismadigi raporlandi.

Kullanim:
    cd musiki_backend
    python -m scripts.false_positive_test --db seekture.db --dur 8
"""
from __future__ import annotations

import argparse
import os
import random
import struct
import sys
import tempfile

import numpy as np

# module-as-script kullanilabilmesi icin:
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seekture.fingerprint import fingerprint_audio
from seekture.matcher import find_matches_fgp
from seekture.db_client import SQLiteClient


SAMPLE_RATE = 44100


def write_wav(samples: np.ndarray, sample_rate: int, path: str) -> None:
    samples = np.clip(samples, -1.0, 1.0)
    int16 = (samples * 32767).astype(np.int16)
    raw = int16.tobytes()
    with open(path, 'wb') as f:
        f.write(b'RIFF')
        f.write(struct.pack('<I', 36 + len(raw)))
        f.write(b'WAVE')
        f.write(b'fmt ')
        f.write(struct.pack('<I', 16))
        f.write(struct.pack('<H', 1))
        f.write(struct.pack('<H', 1))
        f.write(struct.pack('<I', sample_rate))
        f.write(struct.pack('<I', sample_rate * 2))
        f.write(struct.pack('<H', 2))
        f.write(struct.pack('<H', 16))
        f.write(b'data')
        f.write(struct.pack('<I', len(raw)))
        f.write(raw)


# ── Negative-sample uretici fonksiyonlar ────────────────────────────

def gen_digital_silence(dur_s: float) -> np.ndarray:
    return np.zeros(int(SAMPLE_RATE * dur_s), dtype=np.float64)


def gen_quiet_noise(dur_s: float, amp_db: float = -60.0) -> np.ndarray:
    """Cok dusuk gurultu (mikrofon bias/elektronik gurultu seviyesinde)."""
    amp = 10 ** (amp_db / 20)
    return np.random.normal(0, amp, int(SAMPLE_RATE * dur_s))


def gen_white_noise(dur_s: float, amp_db: float = -20.0) -> np.ndarray:
    """Normal seviyeli beyaz gurultu (buzdolabi, klima, kafe gurultusu)."""
    amp = 10 ** (amp_db / 20)
    return np.random.normal(0, amp, int(SAMPLE_RATE * dur_s))


def gen_pink_noise(dur_s: float, amp_db: float = -20.0) -> np.ndarray:
    """Pembe gurultu (1/f spektrumu — muzik benzeri dagilim)."""
    n = int(SAMPLE_RATE * dur_s)
    white = np.random.normal(0, 1, n)
    fft = np.fft.rfft(white)
    freqs = np.fft.rfftfreq(n, 1 / SAMPLE_RATE)
    scale = np.ones_like(freqs)
    scale[1:] = 1.0 / np.sqrt(freqs[1:])
    pink = np.fft.irfft(fft * scale, n=n)
    pink = pink / np.max(np.abs(pink)) * (10 ** (amp_db / 20))
    return pink


def gen_speech_sim(dur_s: float, amp_db: float = -15.0) -> np.ndarray:
    """Konusma benzeri AM/FM sinyal (formant-like carrier)."""
    t = np.linspace(0, dur_s, int(SAMPLE_RATE * dur_s), endpoint=False)
    carrier = (
        0.5 * np.sin(2 * np.pi * 220 * t) +
        0.3 * np.sin(2 * np.pi * 880 * t) +
        0.2 * np.sin(2 * np.pi * 1760 * t)
    )
    envelope = 0.5 + 0.5 * np.sin(2 * np.pi * 4 * t)  # 4 Hz heceleme
    signal = carrier * envelope
    signal = signal / np.max(np.abs(signal)) * (10 ** (amp_db / 20))
    return signal


def gen_sine_tone(dur_s: float, freq: float = 440.0, amp_db: float = -15.0) -> np.ndarray:
    """Saf sinus dalgasi (telefon zili, uyari sesi)."""
    t = np.linspace(0, dur_s, int(SAMPLE_RATE * dur_s), endpoint=False)
    amp = 10 ** (amp_db / 20)
    return amp * np.sin(2 * np.pi * freq * t)


def gen_random_music_like(dur_s: float, seed: int = None) -> np.ndarray:
    """
    Gercek muzige benzer ama kutuphanede olmayan bir sinyal: rastgele
    akor progresyonu + arpeggio. Eger algoritma bunu bir sarkiya baglarsa
    bu kesin false-positive demektir.
    """
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)
    t = np.linspace(0, dur_s, int(SAMPLE_RATE * dur_s), endpoint=False)
    out = np.zeros_like(t)
    # Rastgele 4-5 nota, her biri 1-2 saniye
    cur = 0.0
    while cur < dur_s:
        seg_len = random.uniform(0.5, 1.5)
        freq = random.choice([220, 247, 262, 294, 330, 349, 392, 440, 494])
        idx_start = int(cur * SAMPLE_RATE)
        idx_end = min(int((cur + seg_len) * SAMPLE_RATE), len(out))
        tt = t[idx_start:idx_end]
        envelope = np.exp(-3.0 * (tt - tt[0]))  # sonme
        note = 0.3 * np.sin(2 * np.pi * freq * tt) * envelope
        note += 0.15 * np.sin(2 * np.pi * freq * 2 * tt) * envelope  # oktav
        out[idx_start:idx_end] += note
        cur += seg_len * 0.6  # overlap
    if np.max(np.abs(out)) > 0:
        out = out / np.max(np.abs(out)) * 0.3
    return out


# ── Test runner ────────────────────────────────────────────

SCENARIOS = {
    'digital_silence': ('Tam dijital sessizlik (0.0 sample)', gen_digital_silence),
    'quiet_noise':     ('Cok dusuk gurultu (-60dB, mikrofon bias)', gen_quiet_noise),
    'white_noise_20':  ('Beyaz gurultu -20dB (kafe/buzdolabi)', gen_white_noise),
    'pink_noise':      ('Pembe gurultu -20dB (muzik spektrumuna benzer)', gen_pink_noise),
    'speech_sim':      ('Konusma benzeri AM/FM sinyal', gen_speech_sim),
    'sine_440':        ('Saf sinus 440Hz (telefon zili)', gen_sine_tone),
    'random_music_1':  ('Kutuphanede olmayan rastgele muzik (seed=1)',
                        lambda d: gen_random_music_like(d, seed=1)),
    'random_music_2':  ('Kutuphanede olmayan rastgele muzik (seed=2)',
                        lambda d: gen_random_music_like(d, seed=2)),
    'random_music_3':  ('Kutuphanede olmayan rastgele muzik (seed=3)',
                        lambda d: gen_random_music_like(d, seed=3)),
}


def run_scenario(name: str, label: str, gen_fn, db: SQLiteClient, dur_s: float) -> dict:
    """Bir negatif senaryo icin test calistir."""
    samples = gen_fn(dur_s)

    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    tmp.close()
    write_wav(samples, SAMPLE_RATE, tmp.name)

    try:
        fps = fingerprint_audio(tmp.name, 0)
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    fp_count = len(fps) if fps else 0

    if not fps:
        return {
            'name': name, 'label': label,
            'fp_count': 0, 'match': None,
            'top_score': 0, 'second_score': 0,
            'ratio': 0.0,
        }

    sample_map = {addr: c.anchor_time_ms for addr, c in fps.items()}
    matches = find_matches_fgp(sample_map, db)

    if not matches:
        return {
            'name': name, 'label': label,
            'fp_count': fp_count, 'match': None,
            'top_score': 0, 'second_score': 0,
            'ratio': 0.0, 'quality': 'NONE',
        }

    top = matches[0]
    second_score = top.get('second_score', 0)
    quality = top.get('match_quality', 'UNKNOWN')
    # REJECTED = API null doner, FP degil
    is_fp = quality != 'REJECTED'

    return {
        'name': name, 'label': label,
        'fp_count': fp_count,
        'match': f"{top['artist']} - {top['title']}" if is_fp else None,
        'top_score': int(top['score']),
        'second_score': int(second_score),
        'ratio': top.get('ratio', 0.0),
        'quality': quality,
        'raw_match': f"{top['artist']} - {top['title']}",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Seekture False-Positive Testi')
    parser.add_argument('--db', default='seekture.db')
    parser.add_argument('--dur', type=float, default=8.0, help='Kesit uzunlugu (saniye)')
    parser.add_argument('--repeats', type=int, default=1,
                        help='Rastgele senaryolari kac kez tekrarla')
    args = parser.parse_args()

    db = SQLiteClient(args.db)
    total_songs = db.get_total_songs()

    print(f"Veritabani: {args.db} ({total_songs} sarki)")
    print(f"Test suresi: {args.dur:.0f}s, tekrar: {args.repeats}")
    print("=" * 100)
    print(f"{'SENARYO':<18} {'FP':>6}  {'SKOR':>6}  {'2.':>6}  {'RATIO':>6}  {'KALITE':>9}  ESLESME")
    print("-" * 100)

    false_positives = 0
    total_tests = 0

    for name, (label, gen_fn) in SCENARIOS.items():
        for rep in range(args.repeats):
            total_tests += 1
            result = run_scenario(name, label, gen_fn, db, args.dur)
            suffix = f"_#{rep+1}" if args.repeats > 1 else ""

            fp_count = result['fp_count']
            top_score = result['top_score']
            second = result['second_score']
            ratio = result['ratio']
            quality = result.get('quality', 'NONE')
            raw_match = result.get('raw_match', '(hic match yok)')

            if result['match'] is not None:
                false_positives += 1
                flag = "[FP]"
                disp = raw_match
            elif quality == 'REJECTED':
                flag = "[OK]"
                disp = f"REJECTED -> {raw_match}"
            else:
                flag = "[OK]"
                disp = "(eslesme yok)"

            ratio_str = f"{ratio:>6.2f}" if ratio != float('inf') else "   inf"
            print(f"{name+suffix:<18} {fp_count:>6}  {top_score:>6}  "
                  f"{second:>6}  {ratio_str}  {quality:>9}  {flag}  {disp}")

    print("-" * 90)
    fp_rate = 100.0 * false_positives / total_tests if total_tests else 0
    print(f"TOPLAM: {false_positives}/{total_tests} FALSE-POSITIVE "
          f"({fp_rate:.1f}%)")
    print(f"HEDEF: 0 FP — herhangi bir eslesme, algoritmanin FP sorunu var demek")

    db.close()


if __name__ == '__main__':
    main()
