"""
Toplu sarki indirme scripti.

songs.txt formati (her satir):
    Artist - Title
    Artist - Title | https://www.youtube.com/watch?v=VIDEO_ID   <- URL verirsen direkt onu indirir
    PLAYLIST | https://www.youtube.com/playlist?list=PLxxxx      <- tum playlist'i indirir

Ornek:
    Duman - Kolay Degildir
    Duman - Yürek | https://www.youtube.com/watch?v=abc123
    Ati242 - Leke
    PLAYLIST | https://www.youtube.com/playlist?list=PLxxxx

Kullanim:
    cd musiki_backend
    python download_songs.py                                         # songs.txt
    python download_songs.py --file liste.txt                        # baska dosya
    python download_songs.py --check                                 # hangi dosyalar eksik, URL olmayan
    python download_songs.py --playlist https://youtube.com/...      # tek playlist indir
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time


DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), 'media', 'songs')
FAILURE_LOG = os.path.join(os.path.dirname(__file__), 'download_failures.log')
SLEEP_BETWEEN = 5

# YouTube bot-detection icin cookie kullanimi.
# Oncelik: 1) cookies.txt dosyasi (Netscape format)  2) tarayici cookie'leri.
# YT_BROWSER_COOKIES env: 'chrome', 'edge', 'firefox', 'brave', vs. (bos = kullanma)
COOKIES_FILE = os.path.join(os.path.dirname(__file__), 'www.youtube.com_cookies.txt')
YT_BROWSER_COOKIES = os.environ.get('YT_BROWSER_COOKIES', '').strip()


def _cookie_args():
    """yt-dlp'ye eklenecek cookie argumanlari."""
    if os.path.isfile(COOKIES_FILE):
        return ['--cookies', COOKIES_FILE]
    if YT_BROWSER_COOKIES:
        return ['--cookies-from-browser', YT_BROWSER_COOKIES]
    return []


def _yt_dlp():
    """
    yt-dlp binary'sini bul: once ayni venv/Scripts, sonra PATH.
    Bulamazsa hata ver.
    """
    # Script ile ayni venv icinde ara (en guvenilir)
    scripts_dir = os.path.join(os.path.dirname(sys.executable), '')
    candidates = [
        os.path.join(scripts_dir, 'yt-dlp.exe'),   # Windows venv
        os.path.join(scripts_dir, 'yt-dlp'),        # Unix venv
        'yt-dlp',                                    # PATH fallback
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return 'yt-dlp'  # PATH'e birak, hata verirse kullanici gorecek


def sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def _try_download(source, output_path, retries=3, retry_sleep=8):
    """
    source: YouTube URL (https://...) veya ytsearch1:... sorgusu
    SSL: INVALID_SESSION_ID gibi gecici hatalar icin otomatik retry yapar.
    Dondurur: (basarili: bool, hata_mesaji: str)
    """
    import uuid
    temp_id = str(uuid.uuid4())
    temp_output_path = os.path.join(os.path.dirname(output_path), temp_id + ".%(ext)s")
    
    cmd = [
        _yt_dlp(),
        '-x', '--audio-format', 'mp3',
        '--audio-quality', '0',
        '-o', temp_output_path,
        '--no-playlist',
        '--no-warnings',
        '--force-ipv4',
        '--legacy-server-connect',
        '--downloader', 'curl',
        '--downloader-args', 'curl:--silent --show-error --retry 3',
        '--extractor-args', 'youtube:player_client=tv,web',
        '--js-runtimes', 'node',
        *_cookie_args(),
        source,
    ]
    last_err = 'bilinmeyen hata'
    for attempt in range(1, retries + 1):
        # capture_output kaldirildi, kullanici OAuth2 prompt'larini ve canli durumu gorebilsin
        result = subprocess.run(cmd, text=True)
        if result.returncode == 0:
            temp_mp3 = os.path.join(os.path.dirname(output_path), temp_id + ".mp3")
            if os.path.exists(temp_mp3):
                if os.path.exists(output_path):
                    os.remove(output_path)
                os.rename(temp_mp3, output_path)
            return True, ''
        print(f"    [İndirme Başarısız] Deneme {attempt}/{retries}. Çıkış kodu: {result.returncode}")
        time.sleep(retry_sleep)
    return False, "İndirme başarısız oldu (Detaylar terminalde)."


def _find_downloaded(output_dir, safe_name, output_path):
    """Dosya farkli adla kaydedilmis olabilir, kontrol et."""
    if os.path.exists(output_path):
        return output_path
    for f in os.listdir(output_dir):
        if f.startswith(safe_name) and f.endswith('.mp3'):
            final_path = os.path.join(output_dir, f)
            if final_path != output_path:
                os.rename(final_path, output_path)
            return output_path
    return None


def download_song(artist, title, url, output_dir):
    safe_name = sanitize_filename(f"{artist} - {title}")
    output_path = os.path.join(output_dir, f"{safe_name}.mp3")

    if os.path.exists(output_path):
        print(f"  [MEVCUT] {safe_name}")
        return True

    try:
        if url:
            # Dogrudan URL ile indir — kesin dogru video
            success, err_msg = _try_download(url, output_path)
            if _find_downloaded(output_dir, safe_name, output_path):
                size_mb = os.path.getsize(output_path) / (1024 * 1024)
                print(f"  [OK]     {safe_name} ({size_mb:.1f} MB)  [URL]")
                return True
            if not success:
                print(f"  [HATA]   {safe_name}: URL indirilemedi — {err_msg}")
                return False
        else:
            # URL yok — arama ile bul (ilk sonuc, hataya duyarli)
            queries = [
                f"ytsearch1:{artist} {title} official audio",
                f"ytsearch1:{artist} {title} lyrics",
                f"ytsearch1:{artist} {title}",
            ]
            last_err = ''
            for qi, query in enumerate(queries):
                success, last_err = _try_download(query, output_path)
                found = _find_downloaded(output_dir, safe_name, output_path)
                if found:
                    size_mb = os.path.getsize(output_path) / (1024 * 1024)
                    warn = "  [!arama]" if qi > 0 else ""
                    print(f"  [OK]     {safe_name} ({size_mb:.1f} MB){warn}")
                    return True
                if qi < len(queries) - 1:
                    time.sleep(3)

            print(f"  [HATA]   {safe_name}: tum sorgular basarisiz — {last_err}")
            return False

    except subprocess.TimeoutExpired:
        print(f"  [TIMEOUT] {safe_name}")
        return False
    except Exception as e:
        print(f"  [HATA]   {safe_name}: {e}")
        return False


# YouTube basliklarindaki yaygin parantez/koseli suffix'ler.
# Anahtar kelimelerin BIR YA DA DAHA FAZLASI parantez icinde, bosluklarla ayrilmis olabilir:
#   (Official Audio) (Lyric Video) (HD 4K) (Live 2020) (2023) (Akustik) ...
_YT_KW = (
    r'(?:official|lyric(?:s)?|audio|video|music|hd|4k|fhd|remastered|remaster'
    r'|live|akustik|acoustic|klip|cover|reaction|full\s+album|album\s+version'
    r'|\d{4})'
)
_YT_SUFFIX_RE = re.compile(
    rf'[\(\[]\s*{_YT_KW}(?:\s+{_YT_KW})*\s*[\)\]]',
    re.IGNORECASE,
)


def _clean_title(title):
    """YouTube basligindan parantez/koseli suffix'leri temizle."""
    cleaned = _YT_SUFFIX_RE.sub('', title)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip(' -')
    return cleaned


def normalize_title(yt_title, artist):
    """
    YouTube video basligini '{Artist} - {Sarki}' formatina hazirlamak icin temizle.
    Sanatci adi basta veya sonda tekrar ediyorsa cikar; suffix'leri ('Official Audio',
    '[HD]', '(Live)' vs.) at; pipe/tire/em-dash ayiricilarini handle et.
    """
    cleaned = _YT_SUFFIX_RE.sub('', yt_title)
    parts = re.split(r'\s*[-–|]\s*', cleaned, maxsplit=1)
    if len(parts) == 2:
        a, b = parts[0].strip(), parts[1].strip()
        a_low, b_low, art_low = a.lower(), b.lower(), artist.lower()
        if a_low == art_low or art_low in a_low:
            cleaned = b
        elif b_low == art_low or art_low in b_low:
            cleaned = a
    cleaned = re.sub(r'\s+', ' ', cleaned).strip(' -–|')
    return cleaned or yt_title


def _log_failure(artist, title, url, err):
    """Eksik kalan sarki kaydi: timestamp | artist | title | url | err."""
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f"{ts} | {artist or '-'} | {title} | {url or '-'} | {err}\n"
    try:
        with open(FAILURE_LOG, 'a', encoding='utf-8') as f:
            f.write(line)
    except Exception:
        pass


def _title_exists(raw_title, output_dir):
    """
    Verilen YouTube basligina ait MP3 dosyasi output_dir'de var mi?
    1. Tam eslesmeli kontrol (ayni isimle indirilmisse)
    2. Suffix temizlenince eslesmeli kontrol (Official Audio vs. vs.)
    """
    safe_exact = sanitize_filename(raw_title)
    if os.path.exists(os.path.join(output_dir, f"{safe_exact}.mp3")):
        return safe_exact

    safe_clean = sanitize_filename(_clean_title(raw_title))
    if safe_clean and os.path.exists(os.path.join(output_dir, f"{safe_clean}.mp3")):
        return safe_clean

    return None


def download_playlist(url, output_dir, artist=None):
    """
    YouTube playlist URL'sindeki tum sarkilari MP3 olarak indirir.
    Zaten var olan dosyalari atlar.

    artist verilirse: her dosya '{Artist} - {NormTitle}.mp3' formatinda kaydedilir.
                     Bu sayede setup_music.py / seed_demo.py regex parse'i kesin uyar.
    artist None ise eski davranis: dosya YouTube basligi ile kaydedilir.

    Dondurur: (ok_count, fail_count)
    """
    if artist:
        print(f"\nPlaylist [ARTIST={artist}] bilgisi aliniyor: {url}")
    else:
        print(f"\nPlaylist bilgisi aliniyor: {url}")

    # Once playlist metadata'sini al (baslik listesi)
    meta_cmd = [
        _yt_dlp(),
        '--flat-playlist',
        '--print', '%(title)s\t%(id)s',
        '--no-warnings',
        '--legacy-server-connect',
        *_cookie_args(),
        url,
    ]
    result = subprocess.run(meta_cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        print(f"  [HATA] Playlist bilgisi alinamadi: {result.stderr.strip()}")
        return 0, 0

    entries = []
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.rsplit('\t', 1)
        if len(parts) == 2:
            title, vid_id = parts
        else:
            title, vid_id = parts[0], None
        entries.append((title.strip(), vid_id))

    if not entries:
        print("  [HATA] Playlist bos veya erisilemiyor.")
        return 0, 0

    print(f"  {len(entries)} sarki bulundu.\n")

    ok = fail = 0
    for i, (title, vid_id) in enumerate(entries, 1):
        video_url = f"https://www.youtube.com/watch?v={vid_id}" if vid_id else title

        if artist:
            # Artist mode: hedef dosya adi sabit '{Artist} - {NormTitle}.mp3'
            norm_title = normalize_title(title, artist)
            canonical_safe = sanitize_filename(f"{artist} - {norm_title}")
            canonical_path = os.path.join(output_dir, f"{canonical_safe}.mp3")

            if os.path.exists(canonical_path):
                print(f"  [{i}/{len(entries)}] [MEVCUT] {canonical_safe}")
                ok += 1
                continue

            # Once YouTube basligi ile indir, sonra canonical'a yeniden adlandir
            yt_safe = sanitize_filename(title)
            yt_path = os.path.join(output_dir, f"{yt_safe}.mp3")
            print(f"  [{i}/{len(entries)}] {canonical_safe}")

            try:
                success, err_msg = _try_download(video_url, yt_path)
                found = _find_downloaded(output_dir, yt_safe, yt_path)
                if found:
                    if found != canonical_path and not os.path.exists(canonical_path):
                        os.rename(found, canonical_path)
                    elif os.path.exists(canonical_path) and found != canonical_path:
                        os.remove(found)
                    if os.path.exists(canonical_path):
                        size_mb = os.path.getsize(canonical_path) / (1024 * 1024)
                        print(f"    [OK] {size_mb:.1f} MB")
                        ok += 1
                    else:
                        print(f"    [HATA] Indirildi gosterildi ama dosya bulunamadi: {canonical_path}")
                        fail += 1
                else:
                    print(f"    [HATA] {err_msg or 'indirilemedi'}")
                    _log_failure(artist, title, video_url, err_msg or 'indirilemedi')
                    fail += 1
            except subprocess.TimeoutExpired:
                print(f"    [TIMEOUT]")
                _log_failure(artist, title, video_url, 'timeout')
                fail += 1
            except Exception as e:
                print(f"    [HATA] {e}")
                _log_failure(artist, title, video_url, str(e))
                fail += 1
        else:
            # Eski davranis: dosya YouTube basligi ile kaydedilir
            safe_name = sanitize_filename(title)
            output_path = os.path.join(output_dir, f"{safe_name}.mp3")

            existing = _title_exists(title, output_dir)
            if existing:
                print(f"  [{i}/{len(entries)}] [MEVCUT] {existing}")
                ok += 1
                continue

            print(f"  [{i}/{len(entries)}] {safe_name}")
            try:
                success, err_msg = _try_download(video_url, output_path)
                found = _find_downloaded(output_dir, safe_name, output_path)
                if found:
                    size_mb = os.path.getsize(output_path) / (1024 * 1024)
                    print(f"    [OK] {size_mb:.1f} MB")
                    ok += 1
                else:
                    print(f"    [HATA] {err_msg or 'indirilemedi'}")
                    _log_failure(None, title, video_url, err_msg or 'indirilemedi')
                    fail += 1
            except subprocess.TimeoutExpired:
                print(f"    [TIMEOUT]")
                _log_failure(None, title, video_url, 'timeout')
                fail += 1
            except Exception as e:
                print(f"    [HATA] {e}")
                _log_failure(None, title, video_url, str(e))
                fail += 1

        if i < len(entries):
            time.sleep(SLEEP_BETWEEN)

    return ok, fail


def parse_song_list(file_path):
    """
    Her satir:
      Artist - Title
      Artist - Title | https://youtube.com/...
      PLAYLIST | https://www.youtube.com/playlist?list=...
      ARTIST=Sanatci | https://www.youtube.com/playlist?list=...

    ARTIST=X playlist'i: tum video'lar bu sanatciya ait sayilir, dosya
    '{Sanatci} - {NormTitle}.mp3' formatina yeniden adlandirilir.
    Bos URL'li satirlar atlanir (uyari ile).

    Dondurur: [(artist, title, url_or_None), ...]
    """
    songs = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            url = None
            if '|' in line:
                parts = line.split('|', 1)
                head = parts[0].strip()
                url = parts[1].strip() or None

                # ARTIST=Sanatci | https://playlist
                if head.upper().startswith('ARTIST='):
                    artist = head.split('=', 1)[1].strip()
                    if not url:
                        print(f"  [ATLA] ARTIST={artist} satiri URL icermiyor.")
                        continue
                    songs.append(('__artist_playlist__', artist, url))
                    continue

                tag = head.upper()
                # PLAYLIST satiri: PLAYLIST | https://...
                if tag == 'PLAYLIST':
                    if url:
                        songs.append(('__playlist__', url, url))
                    else:
                        print("  [ATLA] PLAYLIST satiri URL icermiyor.")
                    continue

                line = head

            m = re.match(r'^(.+?)\s*-\s*(.+)$', line)
            if m:
                songs.append((m.group(1).strip(), m.group(2).strip(), url))
            else:
                print(f"  [ATLA] Format hatasi: '{line}'")
    return songs


def check_mode(songs, output_dir):
    """Hangi dosyalar eksik, URL'si olmayan hangisi — rapor yaz."""
    print(f"\n{'DURUM':<8} {'URL':>3}  SARKI")
    print('-' * 60)
    missing_no_url = []
    for artist, title, url in songs:
        safe_name = sanitize_filename(f"{artist} - {title}")
        path = os.path.join(output_dir, f"{safe_name}.mp3")
        exists = os.path.exists(path)
        has_url = 'V' if url else '-'
        status = 'OK' if exists else 'EKSIK'
        print(f"  {status:<6} [{has_url}]  {artist} - {title}")
        if not exists and not url:
            missing_no_url.append((artist, title))

    print('-' * 60)
    missing_total = sum(1 for a, t, u in songs if not os.path.exists(
        os.path.join(output_dir, f"{sanitize_filename(f'{a} - {t}')}.mp3")))
    print(f"Eksik: {missing_total}/{len(songs)}")
    if missing_no_url:
        print(f"\nURL olmayan eksik sarkiler ({len(missing_no_url)}) — yanlis video gelebilir:")
        for a, t in missing_no_url:
            print(f"  {a} - {t} | https://www.youtube.com/watch?v=???")


def main():
    parser = argparse.ArgumentParser(description='Musiki - Toplu Sarki Indirme')
    parser.add_argument('--file', default='songs.txt')
    parser.add_argument('--output', default=DOWNLOAD_DIR)
    parser.add_argument('--sleep', type=int, default=SLEEP_BETWEEN)
    parser.add_argument('--check', action='store_true',
                        help="Sadece hangi dosyalar eksik/URL'siz goster, indirme yapma")
    parser.add_argument('--playlist', metavar='URL',
                        help='YouTube playlist URL\'i — tum sarkilari indir')
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    # Sadece --playlist verildiyse songs.txt'e gerek yok
    if args.playlist:
        ok, fail = download_playlist(args.playlist, args.output)
        print(f"\n{'=' * 50}")
        print(f"Playlist sonuc: {ok} basarili, {fail} hatali")
        if ok > 0:
            print(f"\nIngest:")
            print(f'  python -m seekture.ingest --dir "{args.output}"')
        return

    if not os.path.exists(args.file):
        print(f"HATA: '{args.file}' bulunamadi!")
        sys.exit(1)

    songs = parse_song_list(args.file)

    if not songs:
        print("Listede sarki yok!")
        sys.exit(1)

    if args.check:
        check_mode([s for s in songs if s[0] != '__playlist__'], args.output)
        return

    # Playlist satirlarini ayir, normal sarkilari ayir
    artist_playlists = [(title_or_url, url) for tag, title_or_url, url in songs if tag == '__artist_playlist__']
    playlists = [(title_or_url, url) for tag, title_or_url, url in songs if tag == '__playlist__']
    normal = [(artist, title, url) for artist, title, url in songs
              if artist not in ('__playlist__', '__artist_playlist__')]

    total_ok = total_fail = 0

    # Once ARTIST=X playlist'leri (sanatci-baglamali, canonical rename)
    for artist, pl_url in artist_playlists:
        ok, fail = download_playlist(pl_url, args.output, artist=artist)
        total_ok += ok
        total_fail += fail

    # Sonra eski tarz playlist'ler (sanatcisiz)
    for _, pl_url in playlists:
        ok, fail = download_playlist(pl_url, args.output)
        total_ok += ok
        total_fail += fail

    # Sonra normal sarkilari indir
    if normal:
        url_count = sum(1 for _, _, u in normal if u)
        search_count = len(normal) - url_count
        print(f"\n{len(normal)} sarki: {url_count} URL'li (kesin), {search_count} arama ile -> {args.output}\n")

        for i, (artist, title, url) in enumerate(normal, 1):
            print(f"[{i}/{len(normal)}] {artist} - {title}")
            if download_song(artist, title, url, args.output):
                total_ok += 1
            else:
                _log_failure(artist, title, url, 'download_song fail')
                total_fail += 1
            if i < len(normal):
                time.sleep(args.sleep)

    print(f"\n{'=' * 50}")
    print(f"Sonuc: {total_ok} basarili, {total_fail} hatali")
    if total_fail:
        print(f"\nEksik kalan {total_fail} sarki -> {FAILURE_LOG}")
        print(f"Tamamlamak icin songs.txt'e tek satir ekle:")
        print(f"  ARTIST=Sanatci | https://www.youtube.com/watch?v=XXXXX")
        print(f"Sonra: python download_songs.py")


if __name__ == '__main__':
    main()
