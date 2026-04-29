import argparse
import os
import random
import subprocess
import tempfile
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from seekture.db_client import SQLiteClient
from test_recognition import recognize_file

EFFECTS = {
    "CLEAN": "clean",
    "HIGH-PASS (Telefon Mic. Sim.)": "highpass",
    "LOW-PASS (Boğuk Kulüp Sim.)": "lowpass",
    "PINK-NOISE (Rüzgarlı Ortam)": "pink_noise"
}

def apply_effect(input_path, output_path, effect):
    if effect == 'clean':
        import shutil
        shutil.copy2(input_path, output_path)
    elif effect == 'highpass':
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', input_path, '-af', 'highpass=f=600', output_path], check=True)
    elif effect == 'lowpass':
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', input_path, '-af', 'lowpass=f=1000', output_path], check=True)
    elif effect == 'pink_noise':
        subprocess.run([
            'ffmpeg', '-y', '-v', 'error', '-i', input_path,
            '-filter_complex', 'anoisesrc=c=pink:r=44100:a=0.15[noise];[0:a][noise]amix=inputs=2:duration=first',
            output_path
        ], check=True)

def main():
    songs_dir = 'media/songs'
    if not os.path.exists(songs_dir):
        print(f"HATA: {songs_dir} bulunamadi.")
        return

    mp3s = [f for f in os.listdir(songs_dir) if f.endswith('.mp3')]
    random.shuffle(mp3s)
    test_files = mp3s[:5]  # Rastgele 5 sarki

    db = SQLiteClient('seekture.db')

    print("=" * 80)
    print("STRESS TEST BASLATILIYOR... (Rastgele 5 Sarki)")
    print("=" * 80)

    for i, fname in enumerate(test_files, 1):
        full_path = os.path.join(songs_dir, fname)
        print(f"\n[{i}/5] DOSYA: {fname}")
        
        expected_title = fname.split(' - ')[1].replace('.mp3', '').strip()
        expected_artist = fname.split(' - ')[0].strip()

        # 1. Slice 8s chunk (from 30s to 38s) into a clean WAV
        tmp_clean = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
        # use ffmpeg to cut
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', '30', '-t', '8', '-i', full_path, '-ac', '1', '-ar', '44100', '-c:a', 'pcm_s16le', tmp_clean], check=True)

        for eff_name, eff_code in EFFECTS.items():
            tmp_test = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
            apply_effect(tmp_clean, tmp_test, eff_code)

            # test
            try:
                matches, fp_count, fp_time, match_time = recognize_file(tmp_test, db)
            except Exception as e:
                print(f"  [{eff_name}] HATA: {e}")
                os.unlink(tmp_test)
                continue
            
            if not matches:
                print(f"  [{eff_name}]: X HIC SONUC BULUNAMADI! (Fingerprints: {fp_count})")
                os.unlink(tmp_test)
                continue

            top_match = matches[0]
            top_title = top_match['title']
            top_artist = top_match['artist']
            top_score = top_match['score']

            if top_title.lower() == expected_title.lower() or expected_title.lower() in top_title.lower():
                print(f"  [{eff_name}]: [BASARILI] (Skor: {top_score}, FPs: {fp_count})")
            else:
                print(f"  [{eff_name}]: X HATALI ESLESME! (Fingerprints: {fp_count})")
                print(f"     Beklenen: {expected_artist} - {expected_title}")
                print(f"     Bulunan:  {top_artist} - {top_title} (Skor: {top_score}, TotColl: {top_match['tot_coll']})")
                if len(matches) > 1:
                    print(f"     2. Siradaki Parca: {matches[1]['artist']} - {matches[1]['title']} (Skor: {matches[1]['score']})")
                
                # Nerede kalmis bulun diye listeye bakalim, hic var miymis?
                found_rank = -1
                for rank, m in enumerate(matches, 1):
                    if expected_title.lower() in m['title'].lower():
                        found_rank = rank
                        break
                if found_rank != -1:
                    print(f"     Gercek sarki {found_rank}. siradaydi (Skor: {matches[found_rank-1]['score']}).")
                else:
                    print(f"     Gercek sarki ilk 10'da BİLE YOK!")

            os.unlink(tmp_test)
        os.unlink(tmp_clean)

if __name__ == '__main__':
    main()
