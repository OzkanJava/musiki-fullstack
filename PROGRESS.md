# Musiki Projesi — İlerleme Durumu

Son güncelleme: 2026-04-05

---

## Tamamlanan Fazlar

### Faz 1 — Django İskeleti, Docker, JWT Auth ✅
- Django projesi `config/` pattern ile kuruldu (settings: base/dev/prod)
- Custom User modeli: `AbstractUser` + `role` (listener/artist/admin) + soft delete
- `SoftDeleteModel` abstract base + custom manager (`.alive()`, `.dead()`, `.hard_delete()`)
- Docker Compose: postgres:16, redis:7, backend, celery, nginx
- JWT endpoints: `/api/auth/register/`, `/api/auth/token/`, `/api/auth/token/refresh/`, `/api/auth/me/`
- Role-based permission: `IsListener`, `IsArtist`, `IsAdmin`

### Faz 2 — Müzik Modelleri ve Song CRUD API ✅
- `Album`, `Song` (soft delete), `Fingerprint` (B-Tree index on hash_code), `ListenHistory` modelleri
- `SongViewSet`: list/detail/stream/play + sanatçı upload
- `AlbumViewSet`: CRUD
- `ArtistProfile`: `is_approved_artist` flag
- Django Filter + search_fields entegrasyonu
- `POST /api/music/recognize/` endpoint

### Faz 3 — Fingerprint Logic Django'ya Port ✅
- `logicofsongrecognition/` → `music/services/fingerprint.py` (birebir port, logging eklendi)
- `music/services/ingest.py`: bulk_create (batch_size=5000), `is_fingerprinted` flag
- `music/services/recognize.py`: Counter alignment, `MIN_MATCH_THRESHOLD=5`
- Celery task: `fingerprint_song_task(song_id)` (prod) / sync (dev, `FINGERPRINT_SYNC=True`)
- `python manage.py ingest_songs` yönetim komutu
- 15 Duman şarkısı → ~2.1M fingerprint hash üretildi

### Faz 4 — Nginx X-Accel-Redirect ile Güvenli Streaming ✅
- `nginx/nginx.conf`: `/internal-media/` internal directive, sendfile, tcp_nopush
- `GET /api/music/songs/{id}/stream/`: JWT doğrular → X-Accel-Redirect (prod) / Range-aware FileResponse (dev)
- `USE_NGINX_ACCEL` toggle: dev=False (206 Partial Content), prod=True
- ListenHistory kaydı stream isteğinde oluşturuluyor

### Faz 5 — Android Navigasyon, Auth ve Tema ✅
- Bağımlılıklar: Retrofit, OkHttp, Hilt, Navigation Compose, DataStore, Coil, Moshi, KSP
- `TokenManager`: DataStore Preferences ile JWT kalıcı saklama
- `AuthInterceptor`: tüm isteklere Bearer header otomatik ekleniyor
- `AuthViewModel`: login, register, logout
- `LoginScreen`, `RegisterScreen`: dark-mode UI
- `MusikiTheme`: dark-first, Musiki brand palette (violet primary, cyan accent)
- `NavGraph`: Auth graph + Main graph, token kontrolüne göre start destination
- `BottomNavBar`: 4 tab (Ana Sayfa, Ara, Tanı, Profil)
- `MusikiApp` (@HiltAndroidApp), `MainActivity` (@AndroidEntryPoint)

### Faz 6 — Müzik Listeleme, Streaming ve Player UI ✅
- `MusicRepository`: `getSongs()`, `searchSongs()`
- `PlayerViewModel`: ExoPlayer (Media3) + OkHttpDataSource (auth interceptor otomatik), position polling
- `HomeScreen`: LazyColumn şarkı listesi, SongRow, SongCover (Coil + placeholder)
- `SearchScreen`: 300ms debounce arama
- `MiniPlayerBar`: progress bar + tap → FullPlayer
- `FullPlayerScreen`: seek bar (Slider), büyük cover, play/pause/rewind kontrolleri
- Activity-scoped PlayerViewModel (navigation boyunca persist ediyor)

### Faz 7 — Mobilde Ses Tanıma ✅

### Faz 7.5 — Seekture: Ses Parmak İzi Algoritması ✅

### Faz 7.9 — Altyapı Sabitleme, Streaming Fix & Auth Güvenliği ✅
- **`setup_music` management command** (`music/management/commands/setup_music.py`):
  - Tüm DB kaydını sıfırlar (schema korunur, superuser korunur)
  - `seekture.db` songs + fingerprints tablolarını temizler
  - Multi-artist desteği: dosya adından sanatçı parse ederek her şarkıyı doğru kullanıcıya atar
  - `duman` ve `manga` sanatçı hesapları (şifre: `Artist123!`, `is_approved_artist=True`)
  - 79 şarkı + 79/79 fingerprint başarıyla ingest edildi (Duman + maNga)
- **ExoPlayer streaming fix**:
  - `USE_NGINX_ACCEL=false` (dev mod): Django `FileResponse` + `206 Partial Content` seek desteği
  - `MimeTypes.AUDIO_MPEG` explicit MIME type → format sniff atlandı, doğrudan `c2.android.mp3.decoder`
  - `HttpLoggingInterceptor.Level.BODY` → `HEADERS`: büyük binary body'nin belleğe tamponlanması engellendi
- **Android build variant'ları** (`build.gradle.kts`):
  - `emulatorDebug`: `http://10.0.2.2/` (host loopback → nginx port 80)
  - `deviceDebug`: `http://192.168.1.107/` (LAN IP → nginx port 80)
  - Port 8000 (direct Django) yerine port 80 (nginx) kullanımına geçildi
- **`SessionViewModel`** — startup'ta her zaman sunucu doğrulaması:
  - `DataStore`'daki token boş değilse → `/api/auth/me/` çağrılır
  - 401 dönerse token temizlenir, Login ekranına yönlendirilir
  - Farklı cihazdan oluşturulan hesapla giriş yapılabilmesi garanti altına alındı
  - `tokenManager` parametresi `NavGraph` / `MainActivity`'den kaldırıldı (DI üzerinden)
seek-tune Go projesinin birebir Python portu. Tüm algoritmik dosyalar Go kaynağıyla 1:1 eşleşmektedir.

**Algoritma (seek-tune/server/shazam/*.go portları):**
- `wav_reader.py`: 44-byte PCM header parse, 16-bit → float64 [-1,1] normaliz., `data` chunk dinamik bulma (ffmpeg LIST chunk uyumluluğu)
- `spectrogram.py`: IIR low-pass filtre (5kHz), 4x downsample (44100→11025 Hz), Hanning pencere, STFT (1024 window / 512 hop), magnitude spectrum
- `fingerprint.py`: 6 log frekans bandı peak extraction, 32-bit adres hash: `(anchorFreq/10 << 23) | (targetFreq/10 << 14) | deltaMs`, TARGET_ZONE_SIZE=5
- `matcher.py`: offset bucket analizi (100ms buckets), max count = skor
- `db_client.py`: SQLite (songs + fingerprints), WAL mode, composite PK (address, anchor_time_ms, song_id)

**Kritik Bug Fix (frame_duration):**
Go kodu `frame_duration = audio_duration / num_frames` kullanıyor. Bu değer ses uzunluğuna göre değiştiğinden (full song ≠ 8s clip), `deltaMs` 1-2ms farklı üretilip adres hash'leri eşleşmiyordu.
**Fix:** `frame_duration = HOP_SIZE / effective_sample_rate` (sabit, uzunluğa bağımsız)

**Test Sonuçları (15 Duman şarkısı, `seekture.db`):**
| Pozisyon | Doğruluk |
|----------|----------|
| 10s mark | 13/15 (%87) |
| 30s mark | 15/15 (%100) |
| 60s mark | 15/15 (%100) |
| 90s mark | 15/15 (%100) |
| **Genel** | **58/60 (%96.7)** |

Test araçları:
```bash
cd musiki_backend
python -m seekture.ingest --dir media/songs          # İngest
python -m seekture.clip_test --src "media/songs/Duman - Ah.mp3" --start 30 --dur 8  # Test
python -m seekture.recognize --file sample.wav        # Tanıma
```

**Django Entegrasyonu:**
- `music/services/ingest.py`: Seekture ile yeniden yazıldı. `song.id` → seekture `song_id` (doğrudan eşleşme)
- `music/services/recognize.py`: Seekture tanıma + Django `Song.objects.get(id=song_id)`
- `seekture/db_client.py`: `store_song_with_id()`, `delete_song()` eklendi
- `config/settings/base.py`: `SEEKTURE_DB_PATH = BASE_DIR / 'seekture.db'` (env override destekli)
- Eski `music/services/fingerprint.py` (librosa tabanlı) artık kullanılmıyor
- `RecognizeViewModel`: state machine (Idle → Recording → Recorded → Uploading → Matched/NoMatch/Error)
- `AudioRecord`: 44100 Hz, mono, 16-bit PCM, 8 saniye
- WAV encoder: 44-byte header + PCM data (ByteBuffer little-endian)
- Kayıt sonrası **playback**: MediaPlayer ile kaydedilen ses dinlenilebiliyor
- `@Multipart POST /api/music/recognize/` ile backend'e gönderme
- `RECORD_AUDIO` runtime permission handling
- `RecognizeScreen`: pulsing animasyon (InfiniteTransition), tüm state'ler için UI

---

## Altyapı Notları

### Docker
- `docker-compose.yml` servisleri: db, redis, backend, celery, nginx
- Postgres healthcheck: `pg_isready`, backend/celery `condition: service_healthy` bekliyor
- Media dosyaları: `./musiki_backend` bind mount → `/app` (media/ alt klasörü dahil, named volume yok)
- Nginx media: `./musiki_backend/media:/media` bind mount
- `USE_NGINX_ACCEL=false` (dev) — Django Range-aware FileResponse
- Veri sıfırlama + yeniden yükleme: `docker-compose exec backend python manage.py setup_music`

### Backend URL — Build Variant ile Yönetilir
`musiki_frontend/app/build.gradle.kts` product flavor'ları:
```kotlin
// Emülatör (Android Studio'da "emulatorDebug" seç):
create("emulator") → BASE_URL = "http://10.0.2.2/"   // nginx port 80

// Fiziksel cihaz ("deviceDebug" seç):
create("device")   → BASE_URL = "http://192.168.1.107/"  // nginx port 80
```
LAN IP değişirse `device` flavor'ındaki IP'yi güncelle.  
Windows Firewall'da port 80 açık olmalı: `New-NetFirewallRule -DisplayName "Musiki Nginx 80" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow`

### Test Kullanıcıları (Docker DB)
- Admin: `admin` / `admin1234` (superuser, role=admin)
- Duman sanatçı: `duman` / `Artist123!` (role=artist, is_approved_artist=True)
- maNga sanatçı: `manga` / `Artist123!` (role=artist, is_approved_artist=True)

---

## Bilinen Sorunlar ve Yapılacaklar

### 🔴 Kritik
*Tümü çözüldü.*

### 🟡 Orta

| # | Sorun | Detay |
|---|-------|-------|
| 5 | **Emülatörde ses kaydı çalışmıyor** | Android Emulator host mikrofonunu AudioRecord API'ye düzgün iletmiyor. Fiziksel cihazda test edilmeli. |
| 6 | **Register sonrası otomatik login yok** | Kayıt sonrası kullanıcı Login ekranına yönlendiriliyor, token otomatik alınmıyor. UX iyileştirmesi gerekiyor. |

### 🟢 İyileştirme

| # | Konu | Detay |
|---|------|-------|
| 7 | **Fingerprint eşik değeri** | `MIN_MATCH_THRESHOLD` ayarlanabilir hale getirilmeli, güven skoru UI'da gösterilmeli |
| 8 | **Şarkı listesi sayfalama** | Şu an tüm şarkılar tek seferde çekiliyor, büyük kütüphane için paging gerekli |
| 9 | **ExoPlayer arka planda çalma** | MediaSession servisi yok, uygulama arka plana geçince müzik duruyor |
| 10 | **Cover image yok** | İngest edilen şarkılarda kapak resmi yok, placeholder icon gösteriliyor |
| 11 | **Arama debounce** | 300ms, minimum karakter kontrolü eklenebilir |

---

## Sonraki Fazlar (Planlanmış)

- **Faz 8** — Sanatçı Upload, Profil ve İstatistik
  - Upload ekranı: dosya seçici, metadata girişi (başlık, tür, albüm), progress göstergesi
  - Profil ekranı: dinleme geçmişi, toplam dinlenme, favori tür
  - `/api/music/songs/mine/` endpoint (sanatçının kendi şarkıları)
  - Listener → artist başvuru akışı (`POST /api/auth/request-artist/`)
  - Register sonrası otomatik login (token alıp direkt Home'a geç)

- **Faz 9** — Admin, Optimizasyon ve Production
  - Django admin panel özelleştirme
  - Gunicorn + production settings
  - DB index doğrulama, connection pooling
  - ExoPlayer MediaSession servisi (arka planda çalma, bildirim kontrolü)
  - Frontend: proper error handling, offline cache
  - Test suite: backend pytest + Compose UI testleri
