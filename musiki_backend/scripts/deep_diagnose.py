"""
Derin teshis — bir kaydi DB'ye karsi cok farkli aci altinda test eder.

1) Normal match (mevcut algoritma)
2) Coarse-bucketed match (100ms, 200ms, 500ms bucket) — tempo drift'e dayanikli
3) Tum sarkilarin skor dagilimi — bir "gercek" sinyal var mi kontrol
4) Score / fps (relative match) ve offset histogram analizi

FILE_PATH'i degistir, calistir.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from seekture.fingerprint import fingerprint_audio
from seekture.db_client import SQLiteClient


FILE_PATH = r"C:\Users\ozkan\Documents\Ses Kayıtları\Kayıt (13).wav"
DB_PATH = "seekture.db"
START_SEC: float | None = None
DUR_SEC: float | None = None


def to_wav(path: str, start: float | None, dur: float | None) -> str:
    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False); tmp.close()
    cmd = ['ffmpeg', '-y']
    if start is not None: cmd += ['-ss', str(start)]
    cmd += ['-i', path]
    if dur is not None: cmd += ['-t', str(dur)]
    cmd += ['-ac', '1', '-ar', '44100', '-c:a', 'pcm_s16le', tmp.name]
    subprocess.run(cmd, capture_output=True, check=True)
    return tmp.name


def compute_offsets(sample_fingerprint: dict, db: SQLiteClient) -> dict:
    """Her sarki icin butun (sample_time, db_time) ciftlerini topla."""
    addresses = list(sample_fingerprint.keys())
    couples_map = db.get_couples(addresses)

    song_offsets: dict[int, list[int]] = {}
    for address, couples in couples_map.items():
        for couple in couples:
            sid = couple['song_id']
            offset = couple['anchor_time_ms'] - sample_fingerprint[address]
            song_offsets.setdefault(sid, []).append(offset)
    return song_offsets


def score_with_bucket(offsets: list[int], bucket_ms: int) -> int:
    """Bucket boyutunu degistirerek skor hesapla (orijinal 50ms)."""
    counts: dict[int, int] = {}
    for off in offsets:
        b = off // bucket_ms
        counts[b] = counts.get(b, 0) + 1
    return max(counts.values()) if counts else 0


def main() -> None:
    print(f"Dosya: {FILE_PATH}")
    print(f"DB: {DB_PATH}")
    print()

    # 1. Fingerprint
    wav = to_wav(FILE_PATH, START_SEC, DUR_SEC)
    try:
        fps = fingerprint_audio(wav, 0)
    finally:
        os.unlink(wav)

    if not fps:
        print("[!] Hic fingerprint uretilmedi.")
        return

    sample_map = {a: c.anchor_time_ms for a, c in fps.items()}
    print(f"Query fingerprint: {len(fps)}")
    print()

    db = SQLiteClient(DB_PATH)

    # 2. Tum song offset'lerini topla
    song_offsets = compute_offsets(sample_map, db)
    print(f"Aday sarki sayisi (en az 1 hash match): {len(song_offsets)}")
    print()

    # 3. Her sarki icin farkli bucket'larla skor hesapla
    print("Her sarki icin farkli offset bucket'larla skor dagilimi:")
    print("(Gercek eslesmede bucket buyudukce skor agresif sekilde cogalmaz)")
    print()

    rows = []
    for sid, offsets in song_offsets.items():
        s = db.get_song_by_id(sid)
        if not s:
            continue
        s50  = score_with_bucket(offsets, 50)
        s100 = score_with_bucket(offsets, 100)
        s200 = score_with_bucket(offsets, 200)
        s500 = score_with_bucket(offsets, 500)
        s1000 = score_with_bucket(offsets, 1000)
        total_hits = len(offsets)
        # Coverage: query hash'lerin yuzde kaci bu sarkidan match buldu
        unique_sample_times = len(set(o for o in offsets))  # sample_time unique sayisi
        rows.append({
            'sid': sid, 'title': s['title'], 'artist': s['artist'],
            's50': s50, 's100': s100, 's200': s200, 's500': s500, 's1000': s1000,
            'total_hits': total_hits,
        })

    # En iyi skor (s50'ye gore) sirala
    rows.sort(key=lambda r: r['s50'], reverse=True)

    print(f"  {'#':>2}  {'tot':>5}  {'50ms':>4}  {'100':>4}  {'200':>4}  "
          f"{'500':>4}  {'1s':>4}  SARKI")
    print(f"  {'-'*2}  {'-'*5}  {'-'*4}  {'-'*4}  {'-'*4}  {'-'*4}  "
          f"{'-'*4}  {'-'*40}")
    for i, r in enumerate(rows[:20], 1):
        print(f"  {i:>2}  {r['total_hits']:>5}  {r['s50']:>4}  {r['s100']:>4}  "
              f"{r['s200']:>4}  {r['s500']:>4}  {r['s1000']:>4}  "
              f"{r['artist']} - {r['title'][:40]}")

    print()
    print("Yorum:")
    top = rows[0] if rows else None
    if top:
        print(f"  En iyi aday: {top['artist']} - {top['title']}")
        print(f"  Bucket ilerledikce skor artiyorsa = tempo drift var, ama gercek eslesme")
        print(f"  Skor 50ms ve 1000ms'de benzerse = rastgele eslesme (gercek degil)")
        print()
        ratio_50_to_1000 = top['s1000'] / top['s50'] if top['s50'] > 0 else 0
        print(f"  1000ms/50ms skor orani: {ratio_50_to_1000:.2f}")
        if ratio_50_to_1000 > 3:
            print(f"    [!] COK fark — muhtemelen zaman kaymasi var (tempo/delay)")
        elif ratio_50_to_1000 > 1.5:
            print(f"    [~] Orta fark — kucuk bir kayma olabilir")
        else:
            print(f"    [!] Fark yok — rastgele hit dagilimi, muhtemelen sarki DB'de yok")

    # 4. En iyi adayin offset histogramini cizdir
    if top:
        sid = top['sid']
        offsets = sorted(song_offsets[sid])
        print()
        print(f"En iyi adayin offset dagilimi (ms):")
        print(f"  Min: {offsets[0]}  Max: {offsets[-1]}  "
              f"Median: {offsets[len(offsets)//2]}")
        # 100ms bucket histogram (-10000 to 400000, coarse)
        if offsets:
            bucket_hist: dict[int, int] = {}
            for o in offsets:
                b = o // 500  # 500ms bucket
                bucket_hist[b] = bucket_hist.get(b, 0) + 1
            # En kalabalik 20 bucket
            top_buckets = sorted(bucket_hist.items(), key=lambda x: x[1], reverse=True)[:15]
            print(f"  En kalabalik 15 bucket (500ms):")
            for b, c in sorted(top_buckets, key=lambda x: x[0]):
                bar = '#' * min(60, c)
                print(f"    {b*500:>8}ms +500ms: {c:>3}  {bar}")

    db.close()


if __name__ == '__main__':
    main()
