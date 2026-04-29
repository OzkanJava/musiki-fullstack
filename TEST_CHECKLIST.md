# Musiki — Uçtan Uca Test Checklist

Aşağıdaki her maddeyi sırayla yap; ✅/❌ notu al. Riskli/yeni düzelttiğimiz alanları ⚠️ ile işaretledim.

## 0. Ön Hazırlık
- [ ] Backend `docker-compose up` ile ayakta mı? (`/api/me/` 200 dönüyor mu)
- [ ] Cihazda mikrofon + storage izinleri **reddedilmiş** başla (izin akışları test edilsin)
- [ ] En az 2 test hesabı: (a) **approved artist**, (b) **listener**
- [ ] Cihazın `Music/` veya `Download/` klasörüne en az 3 dosya koy: 1 × mp3, 1 × flac, 1 × m4a

---

## 1. Auth (`ui/auth`)
### Login
- [ ] Boş alanlarla "Giriş Yap" → buton disabled/hata
- [ ] Yanlış şifre → kırmızı hata mesajı görünüyor
- [ ] Göz ikonu ile şifre görünür/gizli toggle
- [ ] Doğru bilgi → Home'a geçiş, token kaydediliyor
- [ ] "Hesabın yok mu? Kayıt ol" → Register'a gidiyor

### Register
- [ ] Password ≠ confirm → hata
- [ ] Zaten kayıtlı username → backend hatası kullanıcıya gösteriliyor
- [ ] Başarılı kayıt → direkt Home'a düşüyor (login gerekmiyor)

### Oturum Kalıcılığı
- [ ] Uygulamayı kapat + aç → Login yerine Home açılıyor
- [ ] ⚠️ Backend'i kapat, uygulamayı aç → 5 sn timeout sonrası Login'e düşüyor (beyaz ekran yok)

---

## 2. Home (`ui/home`)
- [ ] 3 shelf görünüyor: **Son çalınanlar / Senin için / Tüm şarkılar**
- [ ] Shelf kartına tıklayınca çalıyor; mini player çıkıyor
- [ ] Aşağıdaki tam listeden çal → aynı çalma akışı
- [ ] Şarkı satırında kalp / ⋮ menü çalışıyor
- [ ] Çalan şarkı primary renkte vurgulanıyor
- [ ] Hata durumu (backend kapat) → "Tekrar Dene" butonu yeniden yüklüyor

---

## 3. Search (`ui/search`)
- [ ] Boş iken "Aramak istediğin şarkıyı yaz" mesajı
- [ ] Yazı yazdıkça canlı sonuç geliyor
- [ ] Olmayan kelime → "Sonuç bulunamadı"
- [ ] Sonuçtan şarkı oynat → çalıyor
- [ ] Sonuçtaki artist adına tıkla → ArtistDetail açılıyor

---

## 4. Recognize (`ui/recognize`) — Fingerprint
- [ ] İlk kullanımda RECORD_AUDIO izni isteniyor
- [ ] İzin reddedilirse uyarı + tekrar iste butonu
- [ ] "Dinlemeye Başla" → countdown animasyonu (0→13 sn)
- [ ] Bittikten sonra "Kaydı Dinle" çalışıyor (sessiz değil)
- [ ] Gerçek bir şarkı çalarken kaydet → "Bulundu!" + confidence
- [ ] Sessiz ortam → "silence" mesajı (kırmızı RMS uyarısı)
- [ ] Veritabanında olmayan müzik → "Eşleşme Bulunamadı" + debug card
- [ ] Backend kapat → error state + "Tekrar Dene"

---

## 5. Upload (`ui/upload`) ⚠️ **Yeni düzeltildi**
**Approved artist hesabıyla:**
- [ ] Profile → "Şarkı Yükle" → UploadScreen açılıyor (**Home'a atmıyor**)
- [ ] Kapak resmi seçici çalışıyor (galeri açılıyor)
- [ ] Audio seçici MP3/WAV/FLAC alıyor; dosya adı gösteriliyor
- [ ] Tür chips'i seçiliyor; "Diğer" → custom genre input çıkıyor
- [ ] Boş title → buton disabled veya hata
- [ ] "Yükle" → progress + başarılı → "Şarkı Yüklendi!"
- [ ] "Başka Şarkı Yükle" → form temizleniyor
- [ ] Yüklenen şarkı Home "Tüm şarkılar" listesinde görünüyor (fingerprint pipeline tetiklendi)

**Listener hesabıyla:**
- [ ] Profile'da "Şarkı Yükle" butonu **görünmüyor**

---

## 6. Profile (`ui/profile`)
- [ ] Avatar, username, rol badge (Yönetici/Sanatçı/Dinleyici) doğru
- [ ] Email görünüyor; bio (varsa) görünüyor
- [ ] "Sanatçı Ol" → dialog → bio gir → "Başvur" → success state
- [ ] Başvuru sonrası role hâlâ `listener`, admin onayına kadar değişmiyor
- [ ] Tema seçici: Koyu/Açık/Cihaz → anında UI renk değişiyor
- [ ] Tema seçimi uygulama yeniden açılınca kalıcı
- [ ] "Son Dinlenenler" son 20 girdiyi gösteriyor (çalıp dönünce doluyor)
- [ ] "Çıkış Yap" → Login'e düşüyor, token temizleniyor

---

## 7. Library Hub (`ui/library`)
- [ ] 3 kart: Beğenilen Şarkılar / Playlistlerim / Cihazımdaki Müzikler
- [ ] Her biri doğru ekrana gidiyor

### 7a. Liked Songs
- [ ] Beğendiğim şarkılar listeleniyor
- [ ] Satırdaki kalp → unlike → satır listeden düşüyor (veya state güncelleniyor)
- [ ] Boş durumda "Henüz beğendiğin şarkı yok"
- [ ] ⋮ menü → AddToPlaylistSheet açılıyor

### 7b. Local Music (`ui/library/LocalMusicScreen`) ⚠️ **Yeni düzeltildi**
- [ ] İlk açılış → izin diyaloğu çıkıyor (Android 13+ READ_MEDIA_AUDIO)
- [ ] İzin reddedilirse "İzin Ver" butonu tekrar açıyor
- [ ] İzin verildikten sonra dosyalar listeleniyor
- [ ] **MP3 şarkıya bas → çalıyor** (bug fix doğrulaması)
- [ ] **FLAC şarkıya bas → çalıyor**
- [ ] **M4A şarkıya bas → çalıyor**
- [ ] Mini player görünüyor, position ilerliyor
- [ ] Çalan şarkı ▶ ve primary renkle işaretleniyor
- [ ] Local çalarken Home'dan streaming bir şarkı başlat → streaming de çalışıyor (regression)

---

## 8. Playlists (`ui/playlist`)
### Liste
- [ ] Boşsa "Henüz playlist yok" + "+" FAB
- [ ] FAB → CreatePlaylistScreen
- [ ] Playlist row'daki çöp ikonu → anında siliyor (onay yoksa not et)

### Create
- [ ] Title boş → "Oluştur" disabled/hata
- [ ] Başarı → listeye dönüyor, yeni playlist başta

### Detail
- [ ] Header: kapak + "Çal" butonu → 0'dan oynatıyor
- [ ] Satıra bas → o index'ten oynatıyor
- [ ] Satır çöp → şarkı playlist'ten çıkıyor
- [ ] Boş playlist → boş state görünüyor

### AddToPlaylistSheet
- [ ] Bir şarkının ⋮ menüsünden aç
- [ ] Mevcut playlist'e ekle → ✓ + "Playlist'e eklendi" toast
- [ ] Aynı playlist'e tekrar ekleme denemesi → tekrar eklemiyor veya hata
- [ ] "Yeni Playlist" inline form → oluştur + ekle

---

## 9. Detail Ekranları (`ui/detail`)
### Album
- [ ] Kapak + başlık + artist (clickable) + açıklama + şarkı sayısı
- [ ] "Çal" → tüm albüm sıraya giriyor, 0'dan başlıyor
- [ ] Artist adına bas → ArtistDetail
- [ ] Şarkı satırından kalp/⋮ çalışıyor

### Artist
- [ ] Header: avatar + isim + şarkı sayısı
- [ ] "Albümler" yatay shelf (varsa); karta bas → AlbumDetail
- [ ] "Popüler Şarkılar" listesi çalıyor

---

## 10. Player (`ui/player`)
### Mini Player
- [ ] Şarkı başlayınca alt bara yapışıyor (auth/player dışı ekranlarda)
- [ ] Satıra bas (play butonu hariç) → Full Player açılıyor
- [ ] Play/pause butonu anında çalışıyor
- [ ] Üstteki progress bar akıyor
- [ ] Auth ekranında (Login/Register) **görünmüyor**

### Full Player
- [ ] Kapak + title + artist doğru
- [ ] Kalp → like/unlike toggle, kuyruk ve currentSong tutarlı
- [ ] Seek slider'ı sürükle → o konuma atlıyor
- [ ] Zaman göstergesi MM:SS formatında
- [ ] Previous:
  - [ ] 3 sn'den sonraysa → başa sarıyor
  - [ ] 3 sn öncesiyse → önceki şarkıya geçiyor
- [ ] Next → bir sonraki
- [ ] Shuffle → ikon rengi değişiyor; kuyruk karışıyor
- [ ] Repeat OFF → ALL → ONE → OFF döngüsü; son şarkı sonunda davranış doğru
- [ ] Queue butonu → bottom sheet açılıyor

### Queue Sheet
- [ ] Sıradaki şarkılar listeleniyor; çalan highlight + ♪
- [ ] Satıra bas → o şarkıya atlıyor, çalıyor
- [ ] Boş durumda "Sıra boş"

### Background/Lifecycle
- [ ] Şarkı çalarken Home'a bas (ev butonu) → müzik devam ediyor
- [ ] Uygulamaya dön → state korunmuş (position, queue)
- [ ] Uygulamayı force-kill → müzik duruyor (MediaSession yoksa normal)
- [ ] Cihazı döndür → player state kaybolmuyor

---

## 11. Cross-Cutting / Kenar Durumlar

### Ağ
- [ ] Uçak modu → streaming şarkı → hata mesajı, crash yok
- [ ] Uçak modunda **local şarkı çalıyor** (offline)
- [ ] Token süresi dolmuş → TokenAuthenticator logout yapıyor, Login'e düşüyor

### Durum Tutarlılığı ⚠️
- [ ] Bir şarkıyı Home'dan like'la → Liked Songs'ta anında görünüyor
- [ ] Full Player'dan like → Home satırındaki kalp güncel
- [ ] Playlist'e ekledikten sonra PlaylistDetail'de görünüyor

### Listen History
- [ ] Bir şarkıyı en az 10 sn dinle → Profile → "Son Dinlenenler"de ilk sırada
- [ ] Auto-advance ile geçen şarkı da history'e yazılıyor

### Performans / UI
- [ ] Uzun şarkı adları ellipsis ile kesiliyor (overflow yok)
- [ ] Küçük ekranda formlar scroll oluyor, klavye alanı örtmüyor
- [ ] 100+ şarkılı listede scroll akıcı (dropped frames?)

---

## 12. ⚠️ Bilinen Şüpheli Alanlar (özellikle dikkat)

Kodu incelerken not aldığım, kırılabilecek yerler:

1. **Double `getMe()` çağrısı** — `SessionViewModel` ve `ProfileViewModel` bağımsız `getMe()` çağırıyor. `isApprovedArtist` değişirse (artist onayı mid-session), `SessionViewModel` stale kalır. Upload gate'i kaldırdığımız için şu an sorun yok, ama başka bir yerde `sessionViewModel.currentUser` kullanılırsa patlar.

2. **Streaming MIME hardcoded** (`AUDIO_MPEG`) — backend MP3 dışında format serve etmeye başlarsa patlar. Şu an pipeline MP3 transcode ediyor mu kontrol et.

3. **MediaSessionService yok** — arkaplanda bildirim/kilit ekranı kontrolü test et; kullanıcı beklentisi olabilir.

4. **Local track ID çarpışması** — `LocalTrack.id` `Long`, `SongDto.id` `Int`'e cast ediliyor. MediaStore ID 2³¹'i aşarsa overflow. Nadir ama not.

5. **Playlist silme onayı yok** — kazara silme riski. UX iyileştirmesi gerekebilir.

6. **Artist follow / yorum / paylaşım** — kodda yok; roadmap'te varsa eklenecek.

---

**Kullanım:** Her bölümü tek oturumda yap. ❌ çıkan maddeyi ekran görüntüsü + `adb logcat` çıktısıyla not al; tek tek bug olarak çözeriz.
