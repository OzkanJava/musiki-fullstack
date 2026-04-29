
# MUSİKİ PROJESİ: İSTERLER ANALİZİ VE GELİŞTİRME REHBERİ

## 1. Proje Özeti ve Vizyonu
Musiki, piyasadaki devleşmiş ancak kapalı kutu ve yüksek maliyetli (Shazam, Spotify vb.) sistemlere bağımlılığı ortadan kaldıran; müzik dinleme (streaming) ve ses tanıma (audio fingerprinting) özelliklerini tek bir çatı altında, tamamen **on-premise (kurum içi)** sunucularda birleştiren otonom bir ekosistemdir. Projenin temel amacı, yüksek performanslı bir dijital sinyal işleme (DSP) laboratuvarı işlevi gören bir mobil uygulama sunmaktır.

---

## 2. Paydaş ve Kullanıcı Analizi
Sistemin üç temel kullanıcı tipi ve bu tiplerin farklı isterleri bulunmaktadır:

*   **Son Kullanıcı (Dinleyici):** Çevrimiçi/yerel müzik dinleme, ortamdaki sesi 8 saniye içinde tanımlama, kişiselleştirilmiş profil ve istatistik takibi.
*   **Sanatçı:** Kendi eserlerini sisteme yükleme, içerik yönetimi ve dinlenme istatistiklerini görüntüleme.
*   **Sistem Yöneticisi (Admin):** Sanatçı başvurularını onaylama/reddetme, içerik denetimi (Soft Delete yönetimi) ve sistem sağlığını izleme.

---

## 3. Fonksiyonel Gereksinimler (Functional Requirements)

### 3.1. Ses Tanıma ve Parmak İzi (Audio Fingerprinting)
*   **Ortam Dinleme:** Mobil uygulama üzerinden en az 8 saniye boyunca ortam sesini kaydedebilmelidir.
*   **Algoritmik İşleme:** Sistem; ham sesi mono kanala indirmeliz, FFT (Hızlı Fourier Dönüşümü) ile spektrogram oluşturmalı ve "Combinatorial Hashing" yöntemiyle benzersiz parmak izleri üretmelidir.
*   **Eşleştirme:** Veritabanındaki milyonlarca hash arasından en az %70 doğrulukla eşleşme sağlamalıdır.
Ses tanıma için çalışan versiyonun dosya yolu musiki-fullstack/logicofsongrecognition/ klasöürndeki logic kullanılcaktır .

### 3.2. Medya Akış ve Oynatma (Streaming)
*   **Kesintisiz Akış:** Sunucu üzerindeki müzikler, düşük gecikme ile istemciye aktarılmalıdır.
*   **Kontrol Mekanizması:** İleri-geri sarma, duraklatma ve ses seviyesi kontrolü standart olarak sunulmalıdır.
*   **Hibrit Yapı:** Hem yerel (cihazdaki MP3) hem de sunucudaki (streaming) dosyalar aynı arayüzden yönetilmelidir.

### 3.3. Üyelik ve Güvenlik
*   **Kimlik Doğrulama:** JWT (JSON Web Token) tabanlı güvenli giriş sistemi.
*   **İçerik Güvenliği:** Medya dosyalarına doğrudan URL (Hotlink) ile erişim engellenmeli, sadece yetkili oturumlar akış alabilmelidir.

---

## 4. Fonksiyonel Olmayan Gereksinimler (Non-Functional Requirements)


*   **Ölçeklenebilirlik:** Veritabanı (PostgreSQL), B-Tree indexing sayesinde milyonlarca parmak izi kaydı içinde milisaniyeler bazında arama yapabilmelidir. musiki-fullstack/logicofsongrecognition/ buradaki mantık seçilmeli 
*   **Erişilebilirlik:** Android 10 ve üzeri sürümlerle tam uyum, Dark Mode desteği ve minimalist UI/UX tasarımı.
*   **Veri Bütünlüğü:** "Soft Delete" stratejisi ile silinen veriler fiziksel olarak yok edilmemeli, istatistiksel tutarlılık korunmalıdır.

---

## 5. Teknik Mimari ve Teknoloji Yığını

Geliştirme süreci **3-Katmanlı Mimari (3-Tier Architecture)** üzerine inşa edilmelidir:

1.  **Sunucu Tarafı (Backend):**
    *   **Framework:** Python Django (REST Framework).
    *   **Asenkron İşlemler:** Celery & Redis (Ses işleme süreçlerinin arka planda yapılması için). Gerekliyse yapılsın gerekli değilse implementasyonuna gerek yok 
    *   **Ses İşleme:** Librosa & NumPy (Spektrogram ve Peak Finding analizleri için).
2.  **Veri Katmanı (Database & Storage):**
    *   **RDBMS:** PostgreSQL (İlişkisel veriler ve Hash kayıtları).
    *   **File Server:** Nginx (X-Accel-Redirect mekanizması ile güvenli dosya sunumu). File server mantıklı olan buysa devam edilebilir 
3.  **İstemci Tarafı (Mobile):**
    *   **Dil:** Kotlin (Native Android).
    *   **Medya Motoru:** ExoPlayer (Yüksek performanslı akış yönetimi). Exo şart değil Başka sağlıklı çalışan da olabilir ilk tercihimiz exo 

---

## 6. Geliştirme Yol Haritası 

### Faz 1: Altyapı ve Hazırlık 
*   Docker konteyner yapısının kurulması.
*   PostgreSQL şemasının ve ilişkisel modelin (User-Artist-Song-Fingerprint) tasarımı.
*   Django REST API iskeletinin oluşturulması ve JWT entegrasyonu.

### Faz 2: Çekirdek Algoritma Geliştirme 
*   **DSP Motoru:** Librosa kullanılarak ses dosyalarından spektrogram üretimi.
*   **Hashing:** Shazam benzeri "Constellation Map" algoritmasının Python ile kodlanması.
*   **Asenkron Kuyruk:** Yüklenen şarkıların arka planda parmak izlerinin çıkarılması için Celery görevlerinin yazılması.

### Faz 3: Mobil Uygulama ve Entegrasyon 
*   Kotlin ile minimalist UI (Ana ekran, Oynatıcı, Arama) tasarımı.
*   ExoPlayer entegrasyonu ile streaming servisinin bağlanması.
*   Mobil cihazın mikrofonundan ses örneği alıp API'ye gönderen "Tanıma Modülü"nün geliştirilmesi.

### Faz 4: Optimizasyon ve Canlıya Geçiş 
*   **Nginx Yapılandırması:** X-Accel-Redirect ile Django'yu yormadan dosya sunumu.
*   **Veritabanı Tuning:** Hash tabloları üzerinde B-Tree ve Hash Index optimizasyonları.
*   **Testler:** Birim (Unit), Entegrasyon ve Kullanıcı Kabul Testleri (UAT).

---

## 7. Kritik Geliştirme Notları ve Stratejiler

### 7.1. Ses İşleme Darboğazının Aşılması
Python, C++ kadar hızlı değildir. Bu nedenle, ses işleme süreçlerinde (FFT, Hashing) mutlaka **NumPy** gibi vektörize edilmiş kütüphaneler kullanılmalı ve bu işlemler ana istek (request) döngüsünün dışında, **Celery** işçileri (workers) tarafından asenkron olarak yürütülmelidir.

### 7.2. Güvenli Medya Akışı (The Handshake)
Dosya güvenliği için istemci doğrudan dosya yolunu bilmemelidir. İstemci API'den istek yapar, Django yetkiyi kontrol eder ve Nginx'e `"Bu kullanıcıya şu dosyayı gönder"` komutunu (X-Accel-Redirect) verir. Böylece dosya sunucu performansı Nginx'e, yetki kontrolü Django'ya bırakılarak hibrit bir verimlilik sağlanır.


---

**Sonuç:** Musiki projesi, sadece bir yazılım değil, aynı zamanda bir mühendislik çözümüdür. Bu isterler analizi doğrultusunda yapılacak bir geliştirme, ticari rakiplerine karşı maliyet ve güvenlik avantajı sağlayan, ölçeklenebilir bir platform ortaya çıkaracaktır.

