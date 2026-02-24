import json
import requests
import os
from PIL import Image, ImageDraw, ImageFont

# ==============================================================================
# YÜKSEK KONTRASTLI RENK PALETİ (Neon GIS Teması)
# ==============================================================================
RENK_DOGA_FILL = (0, 80, 0, 90)          # Koyu Derin Yeşil
RENK_ANAYOL = (255, 69, 0, 255)          # Kızıl-Turuncu
RENK_ARAYOL = (0, 191, 255, 220)         # Elektrik Mavisi
RENK_BINA_STD_FILL = (160, 32, 240, 110) # Neon Mor/Eflatun (Evler/Standart)
RENK_BINA_STD_OUT = (200, 50, 255, 230)  
RENK_OKUL_FILL = (255, 215, 0, 160)      # Altın Sarısı (Okul/Üniversite)
RENK_HASTANE_FILL = (255, 20, 20, 160)   # Neon Kırmızı (Hastane/Eczane)
RENK_TICARI_FILL = (0, 150, 255, 160)    # Neon Mavi (Ticari/Banka/Ofis)
RENK_TICARI_OUT = (0, 200, 255, 255)
RENK_HAVUZ_FILL = (0, 220, 255, 190)     # Parlak Turkuaz (Havuz)
RENK_HAVUZ_OUT = (150, 255, 255, 255)    
# ==============================================================================

with open("ayarlar.json", "r", encoding="utf-8") as f:
    ayarlar = json.load(f)

def piksel_alani_hesapla(noktalar):
    n = len(noktalar)
    alan = 0.0
    for i in range(n):
        j = (i + 1) % n
        alan += noktalar[i][0] * noktalar[j][1]
        alan -= noktalar[j][0] * noktalar[i][1]
    return abs(alan) / 2.0

for bolge in ayarlar["bolgeler"]:
    zemin_dosyasi = f"{bolge['isim']}_ham_harita.png"
    cikti_dosyasi = f"{bolge['isim']}_FINAL_CBS_NEON.png"

    if not os.path.exists(zemin_dosyasi):
        print(f"Hata: {zemin_dosyasi} bulunamadı, önce birleştirme kodunu çalıştırın.")
        continue

    print(f"\n---> {bolge['isim']} için OSM verileri çekiliyor...")
    
    tolerans = 0.0020 
    sorgu_kuzey = bolge['kuzey'] + tolerans
    sorgu_guney = bolge['guney'] - tolerans
    sorgu_bati = bolge['bati'] - tolerans
    sorgu_dogu = bolge['dogu'] + tolerans
    
    overpass_sorgusu = f"""
    [out:json][timeout:180];
    (
      way["building"]({sorgu_guney},{sorgu_bati},{sorgu_kuzey},{sorgu_dogu});
      way["highway"]({sorgu_guney},{sorgu_bati},{sorgu_kuzey},{sorgu_dogu});
      way["leisure"="swimming_pool"]({sorgu_guney},{sorgu_bati},{sorgu_kuzey},{sorgu_dogu});
      way["leisure"="park"]({sorgu_guney},{sorgu_bati},{sorgu_kuzey},{sorgu_dogu});
      way["natural"="wood"]({sorgu_guney},{sorgu_bati},{sorgu_kuzey},{sorgu_dogu});
    );
    out tags geom;
    """
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    cevap = requests.post("http://overpass-api.de/api/interpreter", data={'data': overpass_sorgusu}, headers=headers)
    
    if cevap.status_code == 200:
        try:
            elemanlar = cevap.json().get('elements', [])
            print(f"Başarılı! {len(elemanlar)} adet OSM verisi alındı. Haritaya işleniyor...")
        except ValueError:
            print("HATA: Sunucu yanıt verdi ancak veri formatı bozuk (JSON değil).")
            continue
    else:
        print(f"HATA: Overpass API isteği reddetti! Durum Kodu: {cevap.status_code}")
        print(f"Sunucu Mesajı: {cevap.text[:300]}...")
        continue
        
    harita = Image.open(zemin_dosyasi).convert("RGBA")
    cizim_katmani = Image.new("RGBA", harita.size, (255, 255, 255, 0))
    cizici = ImageDraw.Draw(cizim_katmani)

    def piksele_cevir(enlem, boylam):
        dx = boylam - bolge['bati']
        dy = bolge['kuzey'] - enlem
        x = (dx / bolge['boylam_adimi']) * bolge['x_piksel'] + (bolge['x_piksel'] / 2) + bolge.get('x_kayma', 0)
        y = (dy / bolge['enlem_adimi']) * bolge['y_piksel'] + (bolge['y_piksel'] / 2) + bolge.get('y_kayma', 0)
        return (x, y)

    try: font = ImageFont.truetype("arial.ttf", 14)
    except IOError: font = ImageFont.load_default()

    # 1. Parklar ve Ormanlar
    for e in elemanlar:
        if e.get('tags', {}).get('leisure') == 'park' or e.get('tags', {}).get('natural') == 'wood':
            noktalar = [piksele_cevir(n['lat'], n['lon']) for n in e.get('geometry', [])]
            if len(noktalar) > 2: cizici.polygon(noktalar, fill=RENK_DOGA_FILL)

    # 2. Yollar
    for e in elemanlar:
        yol_turu = e.get('tags', {}).get('highway')
        if yol_turu:
            noktalar = [piksele_cevir(n['lat'], n['lon']) for n in e.get('geometry', [])]
            if yol_turu in ['primary', 'secondary', 'trunk']: cizici.line(noktalar, fill=RENK_ANAYOL, width=10)
            elif yol_turu in ['residential', 'tertiary']: cizici.line(noktalar, fill=RENK_ARAYOL, width=5)
            else: cizici.line(noktalar, fill=(200, 200, 200, 150), width=2)

    # 3. BİNALAR (Zenginleştirilmiş Kategori Mantığı)
    for e in elemanlar:
        if 'building' in e.get('tags', {}):
            noktalar = [piksele_cevir(n['lat'], n['lon']) for n in e.get('geometry', [])]
            if len(noktalar) > 2:
                tags = e.get('tags', {})
                bina_turu = tags.get('building', '')
                amenity = tags.get('amenity', '')
                
                # Varsayılan Renk (Mor)
                renk, cerceve = RENK_BINA_STD_FILL, RENK_BINA_STD_OUT
                
                # Zenginleştirilmiş Kategori Filtreleri
                if amenity in ['school', 'university', 'college'] or bina_turu == 'school':
                    renk, cerceve = RENK_OKUL_FILL, (255, 255, 0, 255)
                elif amenity in ['hospital', 'clinic', 'pharmacy']:
                    renk, cerceve = RENK_HASTANE_FILL, (255, 0, 0, 255)
                elif bina_turu in ['commercial', 'retail', 'office'] or amenity in ['bank', 'marketplace']:
                    renk, cerceve = RENK_TICARI_FILL, RENK_TICARI_OUT
                
                cizici.polygon(noktalar, fill=renk, outline=cerceve)
                
                piksel_alani = piksel_alani_hesapla(noktalar)
                metrekare = int(piksel_alani * bolge['m2_carpani'])
                
                if metrekare > 30:
                    merkez_x = sum(p[0] for p in noktalar) / len(noktalar)
                    merkez_y = sum(p[1] for p in noktalar) / len(noktalar)
                    metin = f"{metrekare}m2"
                    cizici.text((merkez_x-10, merkez_y-5), metin, fill=(0,0,0,255), font=font)
                    cizici.text((merkez_x-11, merkez_y-6), metin, fill=(255,255,255,255), font=font)

    # 4. Havuzlar
    for e in elemanlar:
        if e.get('tags', {}).get('leisure') == 'swimming_pool':
            noktalar = [piksele_cevir(n['lat'], n['lon']) for n in e.get('geometry', [])]
            if len(noktalar) > 2: cizici.polygon(noktalar, fill=RENK_HAVUZ_FILL, outline=RENK_HAVUZ_OUT)

    son_harita = Image.alpha_composite(harita, cizim_katmani)
    
    # 5. Lejant Ekleme
    cizici_son = ImageDraw.Draw(son_harita)
    try: font_lejant = ImageFont.truetype("arial.ttf", 36)
    except IOError: font_lejant = ImageFont.load_default()

    genislik, yukseklik = son_harita.size
    kutu_x1, kutu_y1 = genislik - 480, 50
    kutu_x2, kutu_y2 = genislik - 50, 440
    
    cizici_son.rectangle([kutu_x1, kutu_y1, kutu_x2, kutu_y2], fill=(0, 0, 0, 220), outline=(255, 255, 255, 255), width=3)
    cizici_son.text((kutu_x1 + 140, kutu_y1 + 15), "LEJANT", fill=(255, 255, 255, 255), font=font_lejant)

    maddeler = [
        (RENK_ANAYOL, "Ana Yollar (Kizil)"),
        (RENK_ARAYOL, "Ara Sokaklar (Mavi)"),
        (RENK_BINA_STD_OUT, "Standart Binalar (Mor)"),
        (RENK_TICARI_FILL, "Ticari/Ofis (Mavi)"), 
        (RENK_HASTANE_FILL, "Saglik/Eczane (Kirmizi)"),
        (RENK_OKUL_FILL, "Egitim/Okul (Sari)"),
        (RENK_HAVUZ_FILL, "Havuzlar (Turkuaz)"),
        (RENK_DOGA_FILL, "Park/Orman (Koyu Yesil)")
    ]

    y_offset = kutu_y1 + 80
    for renk, metin in maddeler:
        cizici_son.rectangle([kutu_x1 + 30, y_offset, kutu_x1 + 70, y_offset + 30], fill=renk)
        cizici_son.text((kutu_x1 + 90, y_offset - 5), metin, fill=(255, 255, 255, 255), font=font_lejant)
        y_offset += 40

    son_harita.convert("RGB").save(cikti_dosyasi)
    print(f"MÜKEMMEL! Zengin etiketli yeni neon harita kaydedildi: {cikti_dosyasi}")