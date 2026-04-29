# Musiki

Müzik akış uygulaması + Shazam tarzı şarkı tanıma.

- **Backend:** Django + DRF, Postgres, Redis, Celery, Nginx, [Seekture](https://github.com/) fingerprint motoru
- **Frontend:** Android (Kotlin + Jetpack Compose, Hilt, Retrofit, ExoPlayer)

---

## Gereksinimler

- Docker + Docker Compose
- Python 3.11+ (yerel `manage.py` komutları için)
- Android Studio (Hedgehog veya üstü)
- Telefon veya emülatör

---

## 1. Repo'yu klonla

```bash
git clone https://github.com/<KULLANICI_ADIN>/musiki-fullstack.git
cd musiki-fullstack
```

## 2. Backend'i ayağa kaldır

```bash
cp musiki_backend/.env.example musiki_backend/.env
docker compose up -d
```

Bu komut Postgres, Redis, Django (8000), Celery worker ve Nginx'i (80) başlatır. Migration'lar ve `collectstatic` otomatik çalışır.

Sağlık kontrolü:
```bash
curl http://localhost:8000/api/auth/me/      # 401 dönmeli — backend ayakta
curl http://localhost/                        # nginx ayakta
```

## 3. Müzik dosyalarını ekle

Repo'da telif sebebiyle audio dosyaları yok. Kendi mp3'lerini `musiki_backend/media/songs/` altına `Artist - Title.mp3` formatında at:

```
musiki_backend/media/songs/
├── Duman - Bal.mp3
├── Manifest - Sınırsız.mp3
└── Sezen Aksu - Tükeniyorum.mp3
```

Desteklenen sanatçılar (seed map'inde): **Manifest, Ati242, Duman, maNga, Sezen Aksu, Sagopa Kajmer**. Başka sanatçı eklemek için `musiki_backend/music/management/commands/seed_demo.py` içindeki `ARTIST_MAP`'e ekle.

## 4. Demo veriyi yükle (seed)

```bash
docker compose exec backend python manage.py seed_demo
```

Bu komut:
- DB'yi sıfırlar (superuser hariç)
- 6 sanatçı + 3 dinleyici hesabı açar
- `media/songs/` altındaki mp3'leri ilgili sanatçıya bağlar
- iTunes API'den her şarkı için kapak indirir
- Fingerprint çıkarır (Seekture)

**Hızlı seçenekler:**
```bash
# Fingerprint'i atla (sonra tek tek)
docker compose exec backend python manage.py seed_demo --no-fingerprint

# iTunes'a hiç gitme (test)
docker compose exec backend python manage.py seed_demo --skip-covers
```

## 5. Admin kullanıcısı oluştur

```bash
docker compose exec backend python manage.py createsuperuser
```

Sonra: http://localhost:8000/admin/

## 6. Frontend'i hazırla

`musiki_frontend/app/build.gradle.kts` dosyasında **device** flavor'ının `BASE_URL`'ini kendi LAN IP'ne göre ayarla (telefon ile aynı WiFi'da):

```kotlin
create("device") {
    dimension = "target"
    buildConfigField("String", "BASE_URL", "\"http://192.168.X.Y/\"")
}
```

LAN IP'ni bulmak için (Windows): `ipconfig` → IPv4 Address. Backend container'ın 80 portu (nginx) üzerinden istek alır.

Android Studio'da:
1. Sol altta **Build Variants** panelini aç
2. `deviceDebug` (gerçek telefon için) veya `emulatorDebug` (Android emülatör için) seç
3. **Run ▶**

> Emülatör kullanıyorsan IP değiştirmen gerekmez, `emulatorDebug` doğrudan `10.0.2.2` (host loopback) kullanır.

---

## Demo hesaplar

| Rol | Kullanıcı adı | Şifre |
|---|---|---|
| Sanatçı | `manifest`, `ati242`, `duman`, `manga`, `sezen_aksu`, `sagopa_kajmer` | `Artist123!` |
| Dinleyici | `ali`, `ayse`, `mehmet` | `Demo123!` |

---

## Servisler ve portlar

| Servis | Port | URL |
|---|---|---|
| Django | 8000 | http://localhost:8000/ |
| Nginx (mobil burayı çağırır) | 80 | http://localhost/ |
| Postgres | 5433 | host'ta |
| Redis | 6379 | host'ta |

---

## Sık komutlar

```bash
# Logları izle
docker compose logs -f backend

# Backend'e shell
docker compose exec backend python manage.py shell

# Migration sıfırla ve baştan al
docker compose exec backend python manage.py migrate

# Stop
docker compose down

# Volume'ları da sil (DB sıfırlanır)
docker compose down -v
```

## Tek bir şarkıyı yeniden fingerprint'le

```bash
docker compose exec backend python manage.py shell
```
```python
from music.models import Song
from music.services.ingest import ingest_song
ingest_song(Song.objects.get(id=1))
```

Veya tüm şarkıları yeniden işle:
```bash
docker compose exec backend python scripts/reingest_all.py
```

---

## Klasör yapısı

```
musiki-fullstack/
├── musiki_backend/          Django projesi
│   ├── config/              settings, urls, asgi
│   ├── music/               şarkı/albüm/playlist/recognize
│   ├── users/               kullanıcı modeli (listener/artist/admin)
│   ├── scripts/             organize_library.py, reingest_all.py
│   └── media/               (gitignore'da) mp3'ler ve kapaklar
├── musiki_frontend/         Android uygulaması
├── nginx/                   nginx.conf
└── docker-compose.yml
```

## Sorun giderme

- **Mobil uygulama 404 / connection refused:** Telefon ve PC aynı WiFi'da mı? `BASE_URL`'deki IP doğru mu? Modem 80 portunu engelliyor mu?
- **`seed_demo` "media/songs/ boş" hatası:** mp3'leri doğru klasöre, doğru formatta (`Artist - Title.mp3`) koydun mu?
- **Recognize "no_match" döndürüyor:** Şarkı fingerprint'lendi mi? Admin → Songs'da `is_fingerprinted=True` olmalı.
- **Build variant yanlış:** Android Studio'da Build Variants paneli yoksa `View → Tool Windows → Build Variants`. `deviceDebug`/`emulatorDebug` doğru seçili mi?
