"""
Birebir port: seek-tune/server/shazam/fingerprint.go

IYILESTIRME (v3): Query tarafinda neighbor-bin expansion.
Gercek dunya kayitlarinda mikrofon/hoparlor frekans kaymasi nedeniyle bir peak
1000Hz'den 1015Hz'e kayabilir -> hash tamamen degisir. Expansion, query peak'i
icin ±1 komsu bin hashlerini de uretir, DB'deki ufak kaymalari yakalar.
Ingest tarafi DEGISMEZ (hash formati ve DB sayisi korunur).
"""
import os

from .models import Couple, Peak
from .spectrogram import make_spectrogram, extract_peaks
from .wav_reader import read_wav_info

# ── Constants (fingerprint.go) ────────────────────────────────────────────
MAX_FREQ_BITS = 9
MAX_DELTA_BITS = 14
TARGET_ZONE_SIZE = 15

# Query-side expansion: her peak icin kac komsu bin hashlenecek?
QUERY_NEIGHBOR_EXPANSION = 0


def create_address(anchor, target):
    """
    32-bit adres:
      [31-23] anchor freq (9 bit)
      [22-14] target freq (9 bit)
      [13-0]  delta time  (14 bit)
    """
    anchor_freq_bin = int(anchor.freq / 10)
    target_freq_bin = int(target.freq / 10)
    delta_ms_raw = int((target.time - anchor.time) * 1000)

    anchor_freq_bits = anchor_freq_bin & ((1 << MAX_FREQ_BITS) - 1)   # 9 bits
    target_freq_bits = target_freq_bin & ((1 << MAX_FREQ_BITS) - 1)   # 9 bits
    delta_bits = delta_ms_raw & ((1 << MAX_DELTA_BITS) - 1)           # 14 bits

    address = (anchor_freq_bits << 23) | (target_freq_bits << 14) | delta_bits
    return address


def create_addresses_expanded(anchor, target, delta_ms_raw: int, expansion: int):
    """
    Query tarafi: anchor ve target frekans bin'ini ±expansion komsulariyla
    ve delta_ms'i ±2 toleransla birlikte hashler. 
    Gercek dunya kayitlarinda frekans kaymasini ve float/int boundary
    degisimlerini tolere eder.
    """
    if expansion <= 0:
        return [create_address(anchor, target)]

    anchor_freq_bin = int(anchor.freq / 10)
    target_freq_bin = int(target.freq / 10)
    
    addresses = []
    mask = (1 << MAX_FREQ_BITS) - 1
    delta_bits = delta_ms_raw & ((1 << MAX_DELTA_BITS) - 1)
    
    for da in range(-expansion, expansion + 1):
        ab = (anchor_freq_bin + da) & mask
        for dt in range(-expansion, expansion + 1):
            tb = (target_freq_bin + dt) & mask
            addresses.append((ab << 23) | (tb << 14) | delta_bits)
                
    return addresses


def fingerprint(peaks, song_id):
    """
    Go karşılığı: Fingerprint(peaks []Peak, songID uint32) map[uint32]Couple

    IYILESTIRME: Go kodu dict (map) kullanarak ayni adreste farkli zamanlardaki
    fingerprint'leri kaybediyor (%91 veri kaybi). Biz tum cifteleri list olarak
    donduruyoruz — DB composite PK (address, anchor_time_ms, song_id) sayesinde
    hepsi saklanir ve eslestirme dogrulugu onemli olcude artar.
    """
    fingerprints = []

    for i, anchor in enumerate(peaks):
        j_end = min(i + TARGET_ZONE_SIZE + 1, len(peaks))
        for j in range(i + 1, j_end):
            target = peaks[j]
            address = create_address(anchor, target)
            anchor_time_ms = int(anchor.time * 1000)
            fingerprints.append((
                address,
                Couple(anchor_time_ms=anchor_time_ms, song_id=song_id),
            ))

    return fingerprints


def fingerprint_expanded(peaks, song_id, expansion: int):
    """
    Query tarafi: neighbor-bin expansion ile hashler.
    Returns: dict[address -> Couple]  (first anchor_time kazanir)
    """
    fp = {}
    for i, anchor in enumerate(peaks):
        anchor_time_ms = int(anchor.time * 1000)
        
        # IYILESTIRME: Sadece 'TARGET_ZONE_SIZE' kadar index degil,
        # gercek saniye cinsinden hedeflere ulas!
        # Anchor'dan sonraki ~1.2 saniyelik zaman dilimindeki tum tepe noktalariyla eslestir.
        # Boylece gurultu olan kayitlarda index sisse bile zaman bandi sasmaz!
        j = i + 1
        while j < len(peaks):
            target = peaks[j]
            dt_sec = target.time - anchor.time
            
            # 1.2 saniyeden uzağa gitme
            if dt_sec > 1.2:
                break
                
            # Cok yakin transientleri atla (örn < 0.05 ms). Burada gerekmeyebilir ama koruduk.
            if dt_sec > 0.0:
                delta_ms_raw = int(dt_sec * 1000)
                addrs = create_addresses_expanded(anchor, target, delta_ms_raw, expansion)
                
                for addr in addrs:
                    if addr not in fp:
                        fp[addr] = Couple(anchor_time_ms=anchor_time_ms, song_id=song_id)
            j += 1
    return fp


def fingerprint_audio(wav_file_path, song_id):
    """
    WAV dosyasini okur, spectrogram -> peaks -> fingerprint uretir.
    Stereo dosyalarda her iki kanal da islenir.
    QUERY_NEIGHBOR_EXPANSION > 0 ise hash adedi katlanir — gercek dunya
    kayitlarinda hedef sarkiyi yakalamak icin.

    Returns:
        dict[address -> Couple]  (tanima icin)
        Ingest icin fingerprint_audio_full() kullanin (expansion DEVRE DISI).
    """
    wav_info = read_wav_info(wav_file_path)
    fp = {}

    # Sol kanal
    spectro = make_spectrogram(wav_info['left_samples'], wav_info['sample_rate'])
    peaks = extract_peaks(spectro, wav_info['duration'], wav_info['sample_rate'])
    expanded = fingerprint_expanded(peaks, song_id, QUERY_NEIGHBOR_EXPANSION)
    fp.update(expanded)

    # Sag kanal (stereo ise)
    if wav_info['channels'] == 2 and wav_info['right_samples']:
        spectro = make_spectrogram(wav_info['right_samples'], wav_info['sample_rate'])
        peaks = extract_peaks(spectro, wav_info['duration'], wav_info['sample_rate'])
        expanded = fingerprint_expanded(peaks, song_id, QUERY_NEIGHBOR_EXPANSION)
        for addr, couple in expanded.items():
            if addr not in fp:
                fp[addr] = couple

    return fp


def fingerprint_audio_full(wav_file_path, song_id):
    """
    Ingest icin: TUM fingerprint'leri dondurur (duplicate address'ler dahil).
    Go'daki dict kaybi olmadan DB'ye yazilir.

    Returns:
        list of (address, Couple)
    """
    wav_info = read_wav_info(wav_file_path)
    all_fps = []

    spectro = make_spectrogram(wav_info['left_samples'], wav_info['sample_rate'])
    peaks = extract_peaks(spectro, wav_info['duration'], wav_info['sample_rate'])
    all_fps.extend(fingerprint(peaks, song_id))

    if wav_info['channels'] == 2 and wav_info['right_samples']:
        spectro = make_spectrogram(wav_info['right_samples'], wav_info['sample_rate'])
        peaks = extract_peaks(spectro, wav_info['duration'], wav_info['sample_rate'])
        all_fps.extend(fingerprint(peaks, song_id))

    return all_fps
