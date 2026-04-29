import os
from pathlib import Path

# BURAYA PROJENİZİN TAM DOSYA YOLUNU YAZIN
KAYNAK_KLASOR_YOLU = r"musiki_frontend"

# OLUŞTURULACAK METİN BELGESİNİN ADI
CIKTI_DOSYASI_ADI = "proje_kodlarfrontend.txt"

def projeyi_metne_aktar(hedef_klasor_yolu, cikti_dosyasi):
    hedef_klasor = Path(hedef_klasor_yolu)
    
    # Klasörün var olup olmadığını kontrol et
    if not hedef_klasor.exists() or not hedef_klasor.is_dir():
        print(f"Hata: '{hedef_klasor_yolu}' adında bir klasör bulunamadı!")
        return

    aranan_uzantilar = ['.py', '.kt']
    
    # İÇİNE GİRİLMEYECEK KLASÖRLER (Sanal ortamlar, git vb.)
    yoksayilacak_klasorler = ['.venv', 'venv', 'env', '.git', '__pycache__', '.idea']
    
    bulunan_dosya_sayisi = 0

    # Çıktı dosyasını yazma modunda açıyoruz
    with open(cikti_dosyasi, 'w', encoding='utf-8') as cikti:
        
        # os.walk ile klasörleri geziyoruz
        for root, dirs, files in os.walk(hedef_klasor):
            
            # Yoksayılacak klasörleri listeden çıkarıyoruz ki os.walk bu klasörlerin içine HİÇ GİRMESİN
            # Bu işlem performansı inanılmaz derecede artırır.
            dirs[:] = [d for d in dirs if d not in yoksayilacak_klasorler]
            
            for file in files:
                dosya_yolu = Path(root) / file
                
                # Uzantı kontrolü (.py veya .kt)
                if dosya_yolu.suffix in aranan_uzantilar:
                    
                    # Tam yoldan, sadece proje klasöründen sonraki kısmı alıyoruz
                    goreceli_yol = dosya_yolu.relative_to(hedef_klasor)
                    
                    # Dosya içeriğini okuma
                    try:
                        with open(dosya_yolu, 'r', encoding='utf-8') as okunan_dosya:
                            icerik = okunan_dosya.read()
                    except Exception as e:
                        icerik = f"[DOSYA OKUNAMADI: {e}]"

                    # 1. Satır: Göreceli Dosya Yolu
                    # 2. Satır: Boşluk (\n)
                    # 3. Satır ve sonrası: Dosya İçeriği
                    cikti.write(f"{goreceli_yol}\n\n")
                    cikti.write(f"{icerik}\n")
                    
                    # Dosyalar birbirine karışmasın diye aralarına ayıraç ekliyoruz
                    cikti.write("\n" + "="*50 + "\n\n")
                    
                    bulunan_dosya_sayisi += 1

    print(f"İşlem tamamlandı! Toplam {bulunan_dosya_sayisi} adet dosya '{cikti_dosyasi}' içine aktarıldı.")

if __name__ == "__main__":
    projeyi_metne_aktar(KAYNAK_KLASOR_YOLU, CIKTI_DOSYASI_ADI)