"""
Orijinal port: seek-tune/server/shazam/shazam.go → FindMatchesFGP +
               analyzeRelativeTiming

IYILESTIRME (Musiki v2):
1) Offset bucket 100ms -> 50ms (daha sıkı zaman hizalaması)
2) Her match icin ratio (top/second) hesaplanir
3) match_quality siniflandirmasi: HIGH / MEDIUM / LOW / REJECTED
4) REJECTED sonuclar dondurulur ama caller'a flag'lenir — API seviyesinde
   gercek cevap verilir mi belirlenir.

Parametreler env vars ile ayarlanabilir.
"""
from __future__ import annotations
import os

# Zaman hizalamasi hassasiyeti.
# 100ms = 50ms (studio robust) + 200ms (mic robust) arasi tatli nokta.
# Deney: 100ms clean=77/88 (regressionsuz), mic kaydinda Parti score 19 > esik.
OFFSET_BUCKET_MS = int(os.environ.get('MATCHER_OFFSET_BUCKET_MS', '100'))

# Minimum mutlak skor.
# 15 = gercek dunya mic kayitlarindaki zayif ama gercek eslesmeleri yakalar.
# FP testinde her senaryoda skor+ratio birlikte basarisiz olur.
MIN_SCORE_ABSOLUTE = int(os.environ.get('MATCHER_MIN_SCORE', '15'))

# Minimum top/second ratio.
# Gercek eslesme (studio): ~10x. Gercek eslesme (mic kaydi): ~1.58-1.61x. FP: 1.0-1.3x.
# 1.5 = FP'nin uzerinde guvenli marj, mic kayitlarini kabul eder.
MIN_SCORE_RATIO = float(os.environ.get('MATCHER_MIN_RATIO', '1.5'))

# HIGH guven: kesin match (studio / yakin kayit).
HIGH_SCORE_ABSOLUTE = int(os.environ.get('MATCHER_HIGH_SCORE', '100'))
HIGH_SCORE_RATIO = float(os.environ.get('MATCHER_HIGH_RATIO', '4.0'))

# MEDIUM guven.
MEDIUM_SCORE_ABSOLUTE = int(os.environ.get('MATCHER_MEDIUM_SCORE', '50'))
MEDIUM_SCORE_RATIO = float(os.environ.get('MATCHER_MEDIUM_RATIO', '2.5'))


def analyze_relative_timing(matches, bucket_ms: int | None = None):
    """
    Her sarki icin sample_time ve db_time arasindaki offset'leri bucket'lara
    boler. En kalabalik bucket'in sayisi = score.
    """
    if bucket_ms is None:
        bucket_ms = OFFSET_BUCKET_MS

    scores = {}

    for song_id, times in matches.items():
        offset_counts = {}

        for sample_time, db_time in times:
            offset = int(db_time) - int(sample_time)
            offset_bucket = offset // bucket_ms
            offset_counts[offset_bucket] = offset_counts.get(offset_bucket, 0) + 1

        # IYILESTIRME: Sınır parcalanmasini (bucket tearing) onlemek icin
        # yan yana olan 3 bucket'in toplamini al.
        max_count = 0
        if offset_counts:
            for b in offset_counts:
                cluster_sum = (
                    offset_counts.get(b - 1, 0) + 
                    offset_counts.get(b, 0) + 
                    offset_counts.get(b + 1, 0)
                )
                if cluster_sum > max_count:
                    max_count = cluster_sum

        scores[song_id] = float(max_count)

    return scores


def _dual_bucket_score(matches):
    """
    Dual-bucket teknik: hem sıkı (50ms) hem gevsek (200ms) bucket'ta skor hesapla.
    Her iki bucketta da TOP olan sarkiya guvenilir eslesme say.

    - Studio quality: sıkı bucket'ta zaten dogru top, skor yuksek.
    - Gercek mic kaydi: sıkı bucket'ta top olsa bile skor dusuk olabilir;
                        gevsek bucket'ta skor buyur.
    - Sahte eslesme: bucket genislediginde random hitler kumelenip baska
                    bir sarki top olabilir — bu disagreement'ta GUVENILMEZ
                    sinyal olarak isaretlenir.

    Returns: (final_scores, secondary_scores, agreement_map)
        final_scores     : her sarki icin kullanilacak skor (max of iki bucket)
        secondary_scores : ikinci en yuksek skoru hesaplamak icin
        agreement_map    : her sarki icin her iki bucketta top olup olmadigi
    """
    scores_tight = analyze_relative_timing(matches, bucket_ms=50)
    scores_loose = analyze_relative_timing(matches, bucket_ms=200)

    if not scores_tight and not scores_loose:
        return {}, {}, {}

    tight_top = max(scores_tight, key=scores_tight.get) if scores_tight else None
    loose_top = max(scores_loose, key=scores_loose.get) if scores_loose else None

    final_scores = {}
    for sid in set(scores_tight) | set(scores_loose):
        t = scores_tight.get(sid, 0)
        l = scores_loose.get(sid, 0)
        # Iki bucketta da uyum varsa gevsek bucket'in (daha yuksek) skoru
        # Aksi halde sıkı bucket'in skoru (daha guvenilir)
        if sid == tight_top == loose_top:
            final_scores[sid] = l  # agreement — guvenli
        elif sid == tight_top:
            final_scores[sid] = t  # tight onayladi
        elif sid == loose_top:
            # Sadece loose'da top — daha riskli. Skoru penalize et.
            final_scores[sid] = l * 0.7
        else:
            final_scores[sid] = max(t, l)

    return final_scores, scores_tight, scores_loose


def classify_quality(top_score: float, second_score: float) -> str:
    """
    Match kalitesi: HIGH / MEDIUM / LOW / REJECTED
    HIGH     → Response doner, UI "Eslesti" (yesil) gosterir.
    MEDIUM   → Response doner, UI "Muhtemel eslesme" gosterir.
    LOW      → Response doner ama UI "Dusuk guven" uyarisi gosterir.
    REJECTED → Response 'song: null' doner — false-positive tuzaklarini engeller.
    """
    if top_score < MIN_SCORE_ABSOLUTE:
        return 'REJECTED'

    ratio = (top_score / second_score) if second_score > 0 else float('inf')
    if ratio < MIN_SCORE_RATIO:
        return 'REJECTED'

    if top_score >= HIGH_SCORE_ABSOLUTE and ratio >= HIGH_SCORE_RATIO:
        return 'HIGH'
    if top_score >= MEDIUM_SCORE_ABSOLUTE and ratio >= MEDIUM_SCORE_RATIO:
        return 'MEDIUM'
    return 'LOW'


def find_matches_fgp(sample_fingerprint, db_client):
    """
    sample_fingerprint: dict[address] -> anchor_time_ms
    db_client: SQLiteClient (get_couples, get_song_by_id)

    Her match'e su alanlar eklenir:
      - score:          kalabalik bucket count (en iyi zaman hizalamasi)
      - second_score:   ikinci en iyi sarkinin skoru (ratio hesabi icin)
      - ratio:          top_score / second_score
      - match_quality:  HIGH / MEDIUM / LOW / REJECTED
    """
    addresses = list(sample_fingerprint.keys())
    if not addresses:
        return []

    couples_map = db_client.get_couples(addresses)

    matches = {}
    timestamps = {}

    for address, couples in couples_map.items():
        for couple in couples:
            sid = couple['song_id']
            atm = couple['anchor_time_ms']

            if sid not in matches:
                matches[sid] = []
            matches[sid].append((sample_fingerprint[address], atm))

            if sid not in timestamps or atm < timestamps[sid]:
                timestamps[sid] = atm

    # Tek-bucket scoring (dual-bucket denendi ama 74/88, 100ms direkt daha iyi)
    scores = analyze_relative_timing(matches)

    # Siralama oncesi ikinci en iyi skoru da hesaplayabilmek icin liste olustur.
    score_list = sorted(scores.values(), reverse=True) if scores else [0.0]
    second_score_global = score_list[1] if len(score_list) > 1 else 0.0

    match_list = []
    for song_id, points in scores.items():
        song = db_client.get_song_by_id(song_id)
        if song is None:
            continue

        # Bu sarkinin skoru top ise second=2. sira; degilse top ile kiyasla.
        if points == score_list[0]:
            second = second_score_global
        else:
            second = score_list[0]

        ratio = (points / second) if second > 0 else float('inf')
        quality = classify_quality(points, second)

        match_list.append({
            'song_id': song_id,
            'title': song['title'],
            'artist': song['artist'],
            'timestamp': timestamps.get(song_id, 0),
            'score': points,
            'total_collisions': len(matches[song_id]),
            'second_score': second,
            'ratio': ratio,
            'match_quality': quality,
        })

    match_list.sort(key=lambda m: m['score'], reverse=True)
    return match_list
