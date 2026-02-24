import json
import requests
import os
import time

# Ayarları JSON dosyasından oku
with open("ayarlar.json", "r", encoding="utf-8") as f:
    ayarlar = json.load(f)

# API anahtarını önce çevresel değişkenden, yoksa ayarlar.json'dan al
api_key = os.environ.get("GOOGLE_MAPS_API_KEY") or ayarlar.get("api_key")
if not api_key or api_key == "BURAYA_GOOGLE_MAPS_API_ANAHTARINIZI_YAZIN":
    raise ValueError("API anahtarı bulunamadı! GOOGLE_MAPS_API_KEY çevresel değişkenini ayarlayın veya ayarlar.json'a yazın.")

for bolge in ayarlar["bolgeler"]:
    klasor = f"{bolge['isim']}_parcalar"
    
    # --- EKLENEN KONTROL: KLASÖR VARSA BÖLGEYİ TAMAMEN ATLA ---
    if os.path.exists(klasor):
        print(f"\n---> {bolge['isim']} için '{klasor}' zaten mevcut. İndirme pas geçiliyor...")
        continue
    # ----------------------------------------------------------
    
    # Klasör yoksa oluştur ve indirmeye başla
    os.makedirs(klasor)

    print(f"\n---> {bolge['isim']} İndirmesi Başlıyor (Zoom: {bolge['zoom']})")
    satir, mevcut_enlem = 0, bolge['kuzey']
    
    while mevcut_enlem > bolge['guney']:
        sutun, mevcut_boylam = 0, bolge['bati']
        while mevcut_boylam < bolge['dogu']:
            dosya_adi = f"{klasor}/kare_satir{satir}_sutun{sutun}.png"
            
            if not os.path.exists(dosya_adi):
                url = "https://maps.googleapis.com/maps/api/staticmap"
                parametreler = {
                    "center": f"{mevcut_enlem},{mevcut_boylam}", "zoom": bolge['zoom'],
                    "size": "640x640", "scale": 2, "maptype": "satellite", "key": api_key
                }
                cevap = requests.get(url, params=parametreler)
                if cevap.status_code == 200:
                    with open(dosya_adi, 'wb') as resim_dosyasi:
                        resim_dosyasi.write(cevap.content)
                    print(f"İndirildi: {dosya_adi}")
                else:
                    print(f"Hata! {dosya_adi} alınamadı.")
                time.sleep(0.2) # Ban yememek için bekle
            sutun += 1
            mevcut_boylam += bolge['boylam_adimi']
        satir += 1
        mevcut_enlem -= bolge['enlem_adimi']

print("\nTüm indirme işlemleri tamamlandı!")