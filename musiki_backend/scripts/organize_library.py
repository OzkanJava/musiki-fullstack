"""
Seed kütüphanesini düzenler:
  - musiki_backend/media/jdown/<playlist>/  ve  musiki_backend/media/songs/  altındaki
    karışık dosyaları okur.
  - 6 sanatçı için temiz klasör yapısı kurar:  media/library/<Sanatçı>/<Başlık>.<ext>
  - iTunes Search API üzerinden her şarkı için 600x600 kapak indirir:
        media/library/<Sanatçı>/<Başlık>.jpg
  - Aynı (sanatçı, başlık) çifti için tek dosya bırakır (öncelik: songs/ -> jdown/).

Kullanım:
    python scripts/organize_library.py            # her şeyi yap (kopyala + kapakları çek)
    python scripts/organize_library.py --no-cover # sadece dosyaları düzenle
    python scripts/organize_library.py --dry-run  # sadece ne yapılacağını göster

Notlar:
  - Orijinaller silinmez (kopyalanır).  --move bayrağı ile taşıma yapılabilir.
  - Mevcut hedef dosya varsa atlanır (tekrar çalıştırmak güvenli).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

# Windows konsolunda Türkçe + box-drawing karakterleri için UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# ──────────────────────────── KONFİGÜRASYON ────────────────────────────

BASE_DIR   = Path(__file__).resolve().parent.parent
MEDIA_DIR  = BASE_DIR / "media"
JDOWN_DIR  = MEDIA_DIR / "jdown"
SONGS_DIR  = MEDIA_DIR / "songs"
LIB_DIR    = MEDIA_DIR / "library"

AUDIO_EXTS = {".mp3", ".m4a", ".opus", ".webm", ".ogg", ".flac", ".wav"}

# jdown alt klasör adı -> kanonik sanatçı adı
JDOWN_ARTIST_MAP = {
    "- Presenting Sezen Aksu": "Sezen Aksu",
    "1,950,710,452 görüntüleme - En İyi Şarkılar (en çok dinlenen SAGOPA KAJMER şarkıları)": "Sagopa Kajmer",
    "Kulak Playlists - Duman ¦ En İyi Şarkıları ¦ Duman'ın En İyi Şarkıları Tek Listede!": "Duman",
    "Z - Ati242 Playlist Tüm Şarkılar": "Ati242",
    "maNga Delisi - maNga Tüm Şarkılar": "maNga",
    "manifest - Official Music Videos": "Manifest",
}

# songs/ klasöründeki dosyalar "Artist - Title.mp3" formatında: bilinen sanatçılar
KNOWN_ARTISTS = ["Sezen Aksu", "Sagopa Kajmer", "Duman", "Ati242", "maNga", "Manifest"]

# Başlıktan silinecek gürültü kalıpları (büyük/küçük harf duyarsız).
NOISE_PATTERNS = [
    r"\(\s*\d+\s*kbit[_ ]\w+\s*\)",
    r"\(\s*official\s+(video|audio|lyric\s+video|music\s+video|dance\s+video)\s*\)",
    r"\s+official\s+(lyric\s+video|music\s+video|dance\s+video|video|audio)\s*$",
    r"\[\s*official\s+video\s*\]",
    r"\(\s*lyrics?[^\)]*\)",
    r"\(\s*lyric\s+video\s*\)",
    r"\(\s*şarkı\s+sözleri\s*\)",
    r"\(\s*hd[^\)]*\)",
    r"\[\s*hd[^\]]*\]",
    r"\(\s*\d{3,4}p\s*\)",
    r"\[\s*\d{3,4}p[^\]]*\]",
    r"\(\s*joyt[uü]rk\s+akustik\s*\)",
    r"\(\s*powert[uü]rk\s+akustik\s*\)",
    r"\|\s*official\s+(video|audio|lyric\s+video|music\s+video|dance\s+video)\s*$",
    r"¦\s*official\s+(video|audio|lyric\s+video|music\s+video|dance\s+video)[^¦]*$",
    r"¦\s*en\s+i?yi\s+şarkıları[^¦]*",
    r"www\.\S+",
]

ITUNES_URL = "https://itunes.apple.com/search"
ITUNES_TIMEOUT = 10
COVER_RES = "600x600bb"

# ──────────────────────────── YARDIMCI ────────────────────────────

INVALID_FS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_filename(name: str) -> str:
    """Windows + Unix güvenli dosya/klasör adı."""
    name = INVALID_FS_CHARS.sub("", name)
    name = name.strip(" .")
    return name or "untitled"


def clean_title(raw: str, artist: str, strip_artist_prefix: bool = True) -> str:
    """Dosya adından başlığı çıkarır.

    strip_artist_prefix=False: songs/ kanalından gelenlerde artist zaten ayrıştırıldı,
    tekrar silmeye çalışma (yoksa "Manifest - Manifest XYZ" -> "XYZ" olur).
    """
    name = raw

    # Uzantıyı düş
    for ext in AUDIO_EXTS:
        if name.lower().endswith(ext):
            name = name[: -len(ext)]
            break

    if strip_artist_prefix:
        artist_variants = {artist, artist.lower(), artist.upper(),
                           "sagopa kajmer", "manga", "manifest"}
        # Tek-kelimeli sanatçılarda sade boşluk silmek tehlikeli
        # ("Manifest Manifest (Arem...)" gibi başlıkları bozar).
        for variant in artist_variants:
            seps = [" - ", " – ", " — "]
            if " " in variant.strip():
                seps += ["-", " "]
            for sep in seps:
                prefix = f"{variant}{sep}"
                if name.lower().startswith(prefix.lower()):
                    name = name[len(prefix):]
                    break

    # Gürültü kalıplarını sil
    for pat in NOISE_PATTERNS:
        name = re.sub(pat, "", name, flags=re.IGNORECASE)

    # Özel karakterler
    name = name.replace("¦", " ")
    name = name.replace("|", " ")
    name = name.replace("¿", "?")
    name = name.replace("⁄", "/")
    name = name.replace("/", " ")
    name = name.replace("[", "(").replace("]", ")")

    # Birden fazla boşluk + artakalan tırnaklar/ayraçlar
    name = re.sub(r"\s+", " ", name).strip(" -–—,.'\"")

    return name or raw


def normalize_key(s: str) -> str:
    """Dedup karşılaştırması için: küçük harf, aksanları kaldır, alfanümerik."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", "", s.lower())
    return s


def parse_songs_folder(filename: str) -> tuple[str, str] | None:
    """songs/ altındaki "Artist - Title.ext" formatını çözer."""
    stem = filename
    for ext in AUDIO_EXTS:
        if stem.lower().endswith(ext):
            stem = stem[: -len(ext)]
            break

    # "Artist - Title"
    parts = stem.split(" - ", 1)
    if len(parts) != 2:
        return None

    artist_raw, title_raw = parts
    # Bilinen sanatçıyla eşleştir (büyük/küçük harf duyarsız)
    for known in KNOWN_ARTISTS:
        if normalize_key(artist_raw) == normalize_key(known):
            return known, title_raw.strip()
    return None


def get_extension(path: Path) -> str:
    """`.webm.part` gibi durumları normalleştir."""
    name = path.name.lower()
    if name.endswith(".webm.part"):
        return ".part"
    return path.suffix.lower()


# ──────────────────────────── KAPAK İNDİRME ────────────────────────────

class CoverFetcher:
    def __init__(self, country: str = "TR"):
        self.country = country
        self.session_ua = "Mozilla/5.0 (compatible; MusikiSeed/1.0)"
        self._artwork_cache: dict[str, str] = {}

    def search_artwork_url(self, artist: str, title: str) -> str | None:
        # Birinci deneme: tam başlık. İkinci: parantez içleri silinmiş.
        # Üçüncü: " - " sonrası kısım (collab/feat formatları için).
        candidates = [f"{artist} {title}"]
        stripped = re.sub(r"\s*\([^)]*\)\s*", " ", title).strip()
        if stripped and stripped != title:
            candidates.append(f"{artist} {stripped}")
        # "Title - Subtitle" yapısında ana başlığı dene
        if " - " in stripped:
            main = stripped.split(" - ", 1)[0].strip()
            if main:
                candidates.append(f"{artist} {main}")

        for term in candidates:
            url = self._do_search(term)
            if url:
                return url
        return None

    def _do_search(self, term: str) -> str | None:
        params = {
            "term": term,
            "entity": "song",
            "limit": "1",
            "country": self.country,
        }
        url = f"{ITUNES_URL}?{urllib.parse.urlencode(params)}"
        cache_key = f"{self.country}|{term}"
        if cache_key in self._artwork_cache:
            return self._artwork_cache[cache_key]

        # 429'a karşı basit exponential backoff
        delay = 1.0
        for attempt in range(4):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": self.session_ua})
                with urllib.request.urlopen(req, timeout=ITUNES_TIMEOUT) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < 3:
                    print(f"   [429 backoff {delay:.1f}s] {term}")
                    time.sleep(delay)
                    delay *= 2
                    continue
                print(f"   [iTunes hata] {term}: {e}")
                return None
            except Exception as e:
                print(f"   [iTunes hata] {term}: {e}")
                return None
        else:
            return None

        if data.get("resultCount", 0) == 0 or not data.get("results"):
            # Sadece sanatçı adıyla yeniden dene (en azından artist artwork)
            return None

        art = data["results"][0].get("artworkUrl100", "")
        if not art:
            return None

        # 100x100bb -> 600x600bb
        hi = art.replace("100x100bb", COVER_RES)
        self._artwork_cache[cache_key] = hi
        return hi

    def download(self, url: str, dest: Path) -> bool:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": self.session_ua})
            with urllib.request.urlopen(req, timeout=ITUNES_TIMEOUT) as resp:
                dest.write_bytes(resp.read())
            return True
        except Exception as e:
            print(f"   [indirme hata] {dest.name}: {e}")
            return False


# ──────────────────────────── ANA AKIŞ ────────────────────────────

def collect_sources() -> list[tuple[str, str, Path]]:
    """(artist, title, source_path) listesi döner. Dedup'siz."""
    items: list[tuple[str, str, Path]] = []

    # 1) songs/ — "Artist - Title.ext"
    if SONGS_DIR.is_dir():
        for f in sorted(SONGS_DIR.iterdir()):
            if not f.is_file():
                continue
            ext = get_extension(f)
            if ext == ".part" or ext not in AUDIO_EXTS:
                continue
            parsed = parse_songs_folder(f.name)
            if parsed is None:
                print(f"[atlandı / songs] sanatçı çözülemedi: {f.name}")
                continue
            artist, title_raw = parsed
            title = clean_title(title_raw, artist, strip_artist_prefix=False)
            items.append((artist, title, f))

    # 2) jdown/<playlist>/<title>.ext
    if JDOWN_DIR.is_dir():
        for sub in sorted(JDOWN_DIR.iterdir()):
            if not sub.is_dir():
                continue
            artist = JDOWN_ARTIST_MAP.get(sub.name)
            if artist is None:
                print(f"[atlandı / jdown] bilinmeyen klasör: {sub.name}")
                continue
            for f in sorted(sub.iterdir()):
                if not f.is_file():
                    continue
                ext = get_extension(f)
                if ext == ".part" or ext not in AUDIO_EXTS:
                    continue
                title = clean_title(f.name, artist)
                items.append((artist, title, f))

    return items


def dedupe(items: list[tuple[str, str, Path]]) -> list[tuple[str, str, Path]]:
    seen: dict[tuple[str, str], Path] = {}
    out: list[tuple[str, str, Path]] = []
    for artist, title, src in items:
        key = (normalize_key(artist), normalize_key(title))
        if key in seen:
            continue
        seen[key] = src
        out.append((artist, title, src))
    return out


def organize(items: list[tuple[str, str, Path]], move: bool, dry_run: bool) -> list[tuple[str, str, Path]]:
    """Dosyaları library/<Artist>/<Title>.<ext> hedefine taşır/kopyalar.
    Hedef yollarıyla birlikte güncel listeyi döner."""
    out: list[tuple[str, str, Path]] = []
    for artist, title, src in items:
        artist_dir = LIB_DIR / safe_filename(artist)
        ext = src.suffix.lower()
        dest = artist_dir / f"{safe_filename(title)}{ext}"

        if dry_run:
            print(f"  [DRY] {src.name}\n        -> {dest.relative_to(MEDIA_DIR)}")
            out.append((artist, title, dest))
            continue

        artist_dir.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            print(f"  [var] {dest.relative_to(MEDIA_DIR)}")
        else:
            if move:
                shutil.move(str(src), str(dest))
                print(f"  [tşn] {dest.relative_to(MEDIA_DIR)}")
            else:
                shutil.copy2(str(src), str(dest))
                print(f"  [kpy] {dest.relative_to(MEDIA_DIR)}")
        out.append((artist, title, dest))
    return out


def fetch_covers(items: list[tuple[str, str, Path]], dry_run: bool) -> None:
    fetcher = CoverFetcher()
    missing: list[tuple[str, str]] = []
    fetched = 0
    skipped = 0

    for i, (artist, title, audio_dest) in enumerate(items, 1):
        cover_path = audio_dest.with_suffix(".jpg")
        if cover_path.exists():
            skipped += 1
            continue
        if dry_run:
            print(f"  [DRY-COVER] {artist} - {title}")
            continue

        url = fetcher.search_artwork_url(artist, title)
        if not url:
            missing.append((artist, title))
            print(f"  [yok] {artist} - {title}")
            time.sleep(0.4)
            continue

        if fetcher.download(url, cover_path):
            fetched += 1
            print(f"  [✓]   ({i}/{len(items)}) {artist} - {title}")
        else:
            missing.append((artist, title))

        # iTunes: yumuşak rate limit. 0.8sn aralık.
        time.sleep(0.8)

    print(f"\nKapaklar: yeni={fetched}, mevcut={skipped}, bulunamadı={len(missing)}")
    if missing:
        log = LIB_DIR / "_missing_covers.txt"
        if not dry_run:
            log.write_text(
                "\n".join(f"{a}\t{t}" for a, t in missing),
                encoding="utf-8",
            )
            print(f"Eksik liste: {log.relative_to(MEDIA_DIR)}")


# ──────────────────────────── CLI ────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="Seed kütüphanesini düzenler ve kapakları çeker.")
    ap.add_argument("--no-cover", action="store_true", help="Kapakları indirme")
    ap.add_argument("--cover-only", action="store_true", help="Sadece kapakları çek (dosya taşıma yok)")
    ap.add_argument("--move", action="store_true", help="Kopyalamak yerine taşı")
    ap.add_argument("--dry-run", action="store_true", help="Sadece göster, dosyaya dokunma")
    args = ap.parse_args()

    print(f"Kütüphane kökü: {LIB_DIR}\n")

    items = collect_sources()
    print(f"Tespit edilen ham dosya: {len(items)}")
    items = dedupe(items)
    print(f"Tekrar temizliği sonrası: {len(items)}\n")

    # Sanatçı bazlı özet
    counts: dict[str, int] = {}
    for a, _, _ in items:
        counts[a] = counts.get(a, 0) + 1
    for a in sorted(counts):
        print(f"  {a}: {counts[a]}")
    print()

    if args.cover_only:
        # Hedef yollarını yeniden hesapla
        items = [(a, t, LIB_DIR / safe_filename(a) / f"{safe_filename(t)}{src.suffix.lower()}") for a, t, src in items]
        items = [(a, t, p) for a, t, p in items if p.exists()]
        print(f"Library'de bulunan dosya: {len(items)}")
        fetch_covers(items, args.dry_run)
        return 0

    print("── Dosyalar düzenleniyor ──")
    items = organize(items, move=args.move, dry_run=args.dry_run)

    if not args.no_cover:
        print("\n── Kapaklar indiriliyor (iTunes) ──")
        fetch_covers(items, args.dry_run)

    print("\nBitti.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
