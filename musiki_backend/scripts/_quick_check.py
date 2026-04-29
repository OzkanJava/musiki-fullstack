"""Hizli test scripti — bir sarkinin matching ciktilari."""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seekture.fingerprint import fingerprint_audio
from seekture.matcher import find_matches_fgp
from seekture.db_client import SQLiteClient


def check(song_path: str, start: float = 30, dur: float = 8, db_path: str = 'seekture.db'):
    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    tmp.close()
    subprocess.run(
        ['ffmpeg', '-y', '-ss', str(start), '-t', str(dur),
         '-i', song_path,
         '-ac', '1', '-ar', '44100', '-c:a', 'pcm_s16le', tmp.name],
        capture_output=True, check=True,
    )

    fps = fingerprint_audio(tmp.name, 0)
    os.unlink(tmp.name)

    db = SQLiteClient(db_path)
    sample_map = {a: c.anchor_time_ms for a, c in fps.items()}
    matches = find_matches_fgp(sample_map, db)

    print(f"SONG: {os.path.basename(song_path)}")
    print(f"  query fps: {len(fps)}")
    print(f"  top 5 matches:")
    for m in matches[:5]:
        score = int(m['score'])
        ratio = m['ratio']
        ratio_str = f"{ratio:.2f}" if ratio != float('inf') else "inf"
        q = m['match_quality']
        print(f"    score={score:>4}  ratio={ratio_str:>5}  q={q:<9}  "
              f"{m['artist']} - {m['title']}")
    db.close()


if __name__ == '__main__':
    songs = sys.argv[1:] or ['media/songs/Duman - Aman Aman.mp3']
    for s in songs:
        check(s)
        print()
