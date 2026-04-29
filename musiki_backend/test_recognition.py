"""
Lokal sarki tanima testi — sunucu gerektirmez.

Kullanim:
    cd musiki_backend

    # Tam dosya ile test (ornegin telefondan kaydedilmis bir parca):
    python test_recognition.py "C:/Users/ozkan/Music/kayit.wav"

    # Bir sarkidan kesit alarak test (--start ve --dur ile):
    python test_recognition.py "media/songs/duman - Ah.mp3" --clip --start 30 --dur 8

    # Farkli DB yolu:
    python test_recognition.py kayit.wav --db seekture.db

    # Tum sarkiler icin toplu test (her birinden 8s kesit):
    python test_recognition.py --batch --start 30 --dur 8
"""
import argparse
import os
import subprocess
import sys
import tempfile
import time

# seekture modulu ayni dizinde
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from seekture.fingerprint import fingerprint_audio
from seekture.matcher import find_matches_fgp
from seekture.db_client import SQLiteClient


def convert_to_wav(input_path):
    """Herhangi bir ses dosyasini mono 44100 Hz WAV'a donusturur."""
    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    tmp.close()
    cmd = [
        'ffmpeg', '-y', '-i', input_path,
        '-ac', '1', '-ar', '44100', '-c:a', 'pcm_s16le',
        tmp.name,
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        os.unlink(tmp.name)
        stderr = result.stderr.decode('utf-8', errors='replace')
        raise RuntimeError(f"ffmpeg donusturme hatasi:\n{stderr}")
    return tmp.name


def clip_audio(src_path, start_sec, duration_sec):
    """ffmpeg ile sarkidan kesit al, mono 44100 Hz WAV olarak dondur."""
    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    tmp.close()
    cmd = [
        'ffmpeg', '-y',
        '-ss', str(start_sec),
        '-t', str(duration_sec),
        '-i', src_path,
        '-ac', '1', '-ar', '44100', '-c:a', 'pcm_s16le',
        tmp.name,
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        os.unlink(tmp.name)
        stderr = result.stderr.decode('utf-8', errors='replace')
        raise RuntimeError(f"ffmpeg kesit alma hatasi:\n{stderr}")
    return tmp.name


def recognize_file(file_path, db, clip=False, start=30, dur=8):
    """
    Dosya yolunu alir, fingerprint cikarir, DB'de eslestirir.
    Returns: (matches_list, fp_count, fp_time, match_time)
    """
    need_cleanup = False
    wav_path = None

    try:
        if clip:
            wav_path = clip_audio(file_path, start, dur)
            need_cleanup = True
        else:
            # Her zaman ffmpeg ile donustur — kaynak WAV olsa bile
            # format uyumsuzlugu olabilir (32-bit float, farkli codec vb.)
            wav_path = convert_to_wav(file_path)
            need_cleanup = True

        # Fingerprint cikar
        t0 = time.time()
        fps = fingerprint_audio(wav_path, 0)
        fp_time = time.time() - t0

        if not fps:
            return [], 0, fp_time, 0

        # address -> anchor_time_ms
        sample_map = {addr: c.anchor_time_ms for addr, c in fps.items()}

        # Eslestirme
        t0 = time.time()
        matches = find_matches_fgp(sample_map, db)
        match_time = time.time() - t0

        return matches, len(fps), fp_time, match_time

    finally:
        if need_cleanup and wav_path and os.path.exists(wav_path):
            os.unlink(wav_path)


def print_results(matches, fp_count, fp_time, match_time, expected=None):
    """Sonuclari formatli yazdir."""
    print(f"  Fingerprint: {fp_count} adet ({fp_time:.2f}s)")
    print(f"  Eslestirme suresi: {match_time:.2f}s")

    if not matches:
        print("\n  SONUC: Eslestirme bulunamadi!")
        return False

    top = matches[0]
    second = matches[1]['score'] if len(matches) > 1 else 0
    ratio = top['score'] / second if second > 0 else float('inf')

    print(f"\n  {'Sira':<5} {'Artist':<20} {'Sarki':<35} {'Skor':<8} {'TotColl'}")
    print(f"  {'-'*78}")

    for i, m in enumerate(matches[:10]):
        marker = ""
        if expected and f"{m['artist']} - {m['title']}".lower() == expected.lower():
            marker = " << DOGRU"
        print(f"  {i+1:<5} {m['artist']:<20} {m['title']:<35} {m['score']:<8.0f} {m.get('total_collisions', 0):<8} {marker}")

    # Guven analizi
    if ratio >= 3:
        confidence = "YUKSEK"
    elif ratio >= 1.5:
        confidence = "ORTA"
    else:
        confidence = "DUSUK"

    print(f"\n  BULUNAN: {top['artist']} - {top['title']} (skor: {top['score']:.0f})")
    print(f"  GUVEN:   {confidence} (1. skor / 2. skor = {ratio:.1f}x)")

    if expected:
        top_name = f"{top['artist']} - {top['title']}"
        if top_name.lower() == expected.lower():
            print("  DURUM: BASARILI!")
            return True
        else:
            print(f"  DURUM: HATALI! Beklenen: {expected}")
            return False
    return True


def run_single(args, db):
    """Tek dosya testi."""
    file_path = args.file
    if not os.path.exists(file_path):
        print(f"HATA: Dosya bulunamadi: {file_path}")
        return

    basename = os.path.basename(file_path)
    print(f"\n{'='*70}")
    print(f"  DOSYA: {basename}")
    if args.clip:
        print(f"  KESIT: {args.start}s - {args.start + args.dur}s ({args.dur}s)")
    print(f"{'='*70}\n")

    matches, fp_count, fp_time, match_time = recognize_file(
        file_path, db, clip=args.clip, start=args.start, dur=args.dur
    )

    # Beklenen sarkiyi dosya adindan cikar (opsiyonel)
    expected = None
    if args.clip:
        expected = basename.rsplit('.', 1)[0]  # "duman - Ah"

    print_results(matches, fp_count, fp_time, match_time, expected)
    print()


def run_batch(args, db):
    """DB'deki tum sarkilar icin toplu test."""
    rows = db.conn.execute('SELECT id, title, artist FROM songs ORDER BY id').fetchall()

    if not rows:
        print("HATA: DB'de sarki yok!")
        return

    # media/songs klasorundeki dosyalari bul
    songs_dir = os.path.join(os.path.dirname(__file__), 'media', 'songs')
    if not os.path.isdir(songs_dir):
        print(f"HATA: Sarki klasoru bulunamadi: {songs_dir}")
        return

    song_files = {}
    for f in os.listdir(songs_dir):
        name_no_ext = f.rsplit('.', 1)[0]
        song_files[name_no_ext.lower()] = os.path.join(songs_dir, f)

    total = 0
    success = 0
    fail = 0
    not_found = 0
    results = []

    print(f"\n{'='*70}")
    print(f"  TOPLU TEST — {len(rows)} sarki, kesit: {args.start}s-{args.start+args.dur}s")
    print(f"{'='*70}\n")

    for song_id, title, artist in rows:
        expected_key = f"{artist} - {title}"
        file_key = expected_key.lower()

        if file_key not in song_files:
            not_found += 1
            continue

        file_path = song_files[file_key]
        total += 1

        try:
            matches, fp_count, fp_time, match_time = recognize_file(
                file_path, db, clip=True, start=args.start, dur=args.dur
            )

            if matches and f"{matches[0]['artist']} - {matches[0]['title']}".lower() == expected_key.lower():
                status = "OK"
                success += 1
            else:
                status = "FAIL"
                fail += 1
                top_name = f"{matches[0]['artist']} - {matches[0]['title']}" if matches else "YOK"
                results.append((expected_key, top_name, matches[0]['score'] if matches else 0))

            score = matches[0]['score'] if matches else 0
            print(f"  [{status:4s}] {expected_key:<45} skor: {score:.0f}")

        except Exception as e:
            fail += 1
            print(f"  [ERR ] {expected_key:<45} {e}")

    print(f"\n{'='*70}")
    print(f"  OZET: {success}/{total} basarili ({success/total*100:.0f}%)" if total else "  Hic sarki test edilemedi")
    if fail:
        print(f"  Basarisiz: {fail}")
        for exp, found, score in results:
            print(f"    Beklenen: {exp}")
            print(f"    Bulunan:  {found} (skor: {score:.0f})")
    if not_found:
        print(f"  Dosya bulunamayan: {not_found}")
    print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(description='Musiki Recognition Test')
    parser.add_argument('file', nargs='?', help='File path', default=r"C:\Users\ozkan\Documents\Ses Kayıtları\vals.wav")
    parser.add_argument('--clip', action='store_true')
    parser.add_argument('--start', type=float, default=30)
    parser.add_argument('--dur', type=float, default=13)
    parser.add_argument('--db', default='seekture.db')
    parser.add_argument('--batch', action='store_true')
    args = parser.parse_args()

    if not args.batch and not args.file:
        print("HATA: Dosya yolu veya batch secenegi gerekli")
        return

    # DB baglan
    if not os.path.exists(args.db):
        print(f"HATA: DB bulunamadi: {args.db}")
        print("Once ingest yapin: python -m seekture.ingest --dir media/songs")
        return

    db = SQLiteClient(args.db)
    total_songs = db.get_total_songs()
    total_fp = db.get_total_fingerprints()
    print(f"\nDB: {total_songs} sarki, {total_fp:,} fingerprint")

    if total_songs == 0:
        print("HATA: DB bos! Once ingest yapin.")
        db.close()
        return

    try:
        if args.batch:
            run_batch(args, db)
        else:
            run_single(args, db)
    finally:
        db.close()


if __name__ == '__main__':
    main()
