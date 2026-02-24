import json
import requests
import os
import overturemaps
import pandas as pd
from shapely import wkb
from PIL import Image, ImageDraw, ImageFont

# ==============================================================================
# YÜKSEK KONTRASTLI RENK PALETİ (Neon GIS Teması)
# ==============================================================================
RENK_DOGA_FILL = (0, 80, 0, 90)          
RENK_ANAYOL = (255, 69, 0, 255)          
RENK_ARAYOL = (0, 191, 255, 220)         
RENK_BINA_STD_FILL = (160, 32, 240, 110) # Overture AI Binaları
RENK_BINA_STD_OUT = (200, 50, 255, 230)  
RENK_OKUL_FILL = (255, 215, 0, 160)      
RENK_HASTANE_FILL = (255, 20, 20, 160)   
RENK_TICARI_FILL = (0, 150, 255, 160)    
RENK_TICARI_OUT = (0, 200, 255, 255)
RENK_HAVUZ_FILL = (0, 220, 255, 190)     
RENK_HAVUZ_OUT = (150, 255, 255, 255)    

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
    cikti_dosyasi = f"{bolge['isim']}_ULTIMATE_HIBRIT.png"

    if not os.path.exists(zemin_dosyasi):
        print(f"Atlanıyor: {zemin_dosyasi} bulunamadı.")
        continue

    print(f"\n{'='*50}\n---> {bolge['isim']} İÇİN HİBRİT MOTOR BAŞLATILDI\n{'='*50}")
    
    tolerans = 0.0020 
    sorgu_kuzey, sorgu_guney = bolge['kuzey'] + tolerans, bolge['guney'] - tolerans
    sorgu_bati, sorgu_dogu = bolge['bati'] - tolerans, bolge['dogu'] + tolerans

    # 1. OVERTURE MAPS'TEN YAPAY ZEKA BİNALARINI ÇEKME
    print("1/2: Overture AI binaları (GeoParquet) indiriliyor...")
    bbox = (sorgu_bati, sorgu_guney, sorgu_dogu, sorgu_kuzey)
    try:
        tablo = overturemaps.record_batch_reader("building", bbox).read_all()
        df_overture = tablo.to_pandas()
        print(f"     Başarılı! {len(df_overture)} adet AI binası bulundu.")
    except Exception as e:
        print(f"     Overture Hatası: {e}")
        df_overture = pd.DataFrame() # Hata olursa boş dataframe ile devam et

    # 2. OSM'DEN AKILLI VERİLERİ ÇEKME (Kızılay Metro Filtresi Eklendi!)
    print("2/2: OSM'den yollar, parklar, havuzlar ve etiketli binalar çekiliyor...")
    
    # SİHİRLİ OSM FİLTRESİ: ["location"!="underground"] ve ["layer"!~"^-"] 
    # Bu sayede yer altındaki metrolar ve eksi katlar haritaya çizilmez!
    overpass_sorgusu = f"""
    [out:json][timeout:180];
    (
      way["building"]["location"!="underground"]["layer"!~"^-"]({sorgu_guney},{sorgu_bati},{sorgu_kuzey},{sorgu_dogu});
      way["highway"]({sorgu_guney},{sorgu_bati},{sorgu_kuzey},{sorgu_dogu});
      way["leisure"="swimming_pool"]({sorgu_guney},{sorgu_bati},{sorgu_kuzey},{sorgu_dogu});
      way["leisure"="park"]({sorgu_guney},{sorgu_bati},{sorgu_kuzey},{sorgu_dogu});
      way["natural"="wood"]({sorgu_guney},{sorgu_bati},{sorgu_kuzey},{sorgu_dogu});
    );
    out tags geom;
    """
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    cevap = requests.post("http://overpass-api.de/api/interpreter", data={'data': overpass_sorgusu}, headers=headers)
    elemanlar = cevap.json().get('elements', []) if cevap.status_code == 200 else []
    print(f"     Başarılı! {len(elemanlar)} adet OSM verisi alındı.")

    # ÇİZİM AŞAMASI
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

    # KATMAN 1: OSM Doğal Alanlar
    for e in elemanlar:
        if e.get('tags', {}).get('leisure') == 'park' or e.get('tags', {}).get('natural') == 'wood':
            noktalar = [piksele_cevir(n['lat'], n['lon']) for n in e.get('geometry', [])]
            if len(noktalar) > 2: cizici.polygon(noktalar, fill=RENK_DOGA_FILL)

    # KATMAN 2: OSM Yollar
    for e in elemanlar:
        yol_turu = e.get('tags', {}).get('highway')
        if yol_turu:
            noktalar = [piksele_cevir(n['lat'], n['lon']) for n in e.get('geometry', [])]
            if yol_turu in ['primary', 'secondary', 'trunk']: cizici.line(noktalar, fill=RENK_ANAYOL, width=10)
            elif yol_turu in ['residential', 'tertiary']: cizici.line(noktalar, fill=RENK_ARAYOL, width=5)
            else: cizici.line(noktalar, fill=(200, 200, 200, 150), width=2)

# KATMAN 3: OVERTURE Binaları (Ana Bina Katmanı)
    if not df_overture.empty:
        for index, row in df_overture.iterrows():
            try:
                geom = wkb.loads(row['geometry'])
                def ciz_overture_poligon(polygon):
                    noktalar = [piksele_cevir(lat, lon) for lon, lat in polygon.exterior.coords]
                    if len(noktalar) > 2:
                        piksel_alani = piksel_alani_hesapla(noktalar)
                        metrekare = int(piksel_alani * bolge['m2_carpani'])
                        
                        # --- İŞTE SİHİRLİ FİLTRE BURADA ---
                        # Kızılay metrosu gibi yeraltı hatalarını ve devasa Overture anomalilerini çöpe atıyoruz.
                        # Gerçek büyük binalar (AVM vb.) zaten OSM katmanından Renkli olarak gelecek!
                        if metrekare > 10000:
                            return # Bu çokgeni çizmeden doğrudan atla
                            
                        # Standart evleri Neon Mor ile çiz
                        cizici.polygon(noktalar, fill=RENK_BINA_STD_FILL, outline=RENK_BINA_STD_OUT)
                        
                        if metrekare > 30:
                            merkez_x = sum(p[0] for p in noktalar) / len(noktalar)
                            merkez_y = sum(p[1] for p in noktalar) / len(noktalar)
                            cizici.text((merkez_x-10, merkez_y-5), f"{metrekare}m2", fill=(0,0,0,255), font=font)
                            cizici.text((merkez_x-11, merkez_y-6), f"{metrekare}m2", fill=(255,255,255,255), font=font)

                if geom.geom_type == 'Polygon': ciz_overture_poligon(geom)
                elif geom.geom_type == 'MultiPolygon':
                    for poly in geom.geoms: ciz_overture_poligon(poly)
            except Exception: pass

    # KATMAN 4: OSM Akıllı Binalar (Okul, Hastane, AVM - Overture'un üzerine yapışır)
    for e in elemanlar:
        if 'building' in e.get('tags', {}):
            tags = e.get('tags', {})
            bina_turu = tags.get('building', '')
            amenity = tags.get('amenity', '')
            
            # Sadece "Özel" binaları çiz (Standartları Overture zaten çizdi)
            if amenity in ['school', 'university', 'college'] or bina_turu == 'school':
                renk, cerceve = RENK_OKUL_FILL, (255, 255, 0, 255)
            elif amenity in ['hospital', 'clinic', 'pharmacy']:
                renk, cerceve = RENK_HASTANE_FILL, (255, 0, 0, 255)
            elif bina_turu in ['commercial', 'retail', 'office'] or amenity in ['bank', 'marketplace']:
                renk, cerceve = RENK_TICARI_FILL, RENK_TICARI_OUT
            else:
                continue # Standart binaysa atla, zaten Overture çizdi!
                
            noktalar = [piksele_cevir(n['lat'], n['lon']) for n in e.get('geometry', [])]
            if len(noktalar) > 2:
                cizici.polygon(noktalar, fill=renk, outline=cerceve)
                piksel_alani = piksel_alani_hesapla(noktalar)
                metrekare = int(piksel_alani * bolge['m2_carpani'])
                if metrekare > 30:
                    merkez_x = sum(p[0] for p in noktalar) / len(noktalar)
                    merkez_y = sum(p[1] for p in noktalar) / len(noktalar)
                    cizici.text((merkez_x-10, merkez_y-5), f"{metrekare}m2", fill=(0,0,0,255), font=font)
                    cizici.text((merkez_x-11, merkez_y-6), f"{metrekare}m2", fill=(255,255,255,255), font=font)

    # KATMAN 5: Havuzlar (En üstte parlamaları için)
    for e in elemanlar:
        if e.get('tags', {}).get('leisure') == 'swimming_pool':
            noktalar = [piksele_cevir(n['lat'], n['lon']) for n in e.get('geometry', [])]
            if len(noktalar) > 2: cizici.polygon(noktalar, fill=RENK_HAVUZ_FILL, outline=RENK_HAVUZ_OUT)

    # Lejant ve Kaydetme İşlemleri
    son_harita = Image.alpha_composite(harita, cizim_katmani)
    cizici_son = ImageDraw.Draw(son_harita)
    try: font_lejant = ImageFont.truetype("arial.ttf", 36)
    except IOError: font_lejant = ImageFont.load_default()

    genislik, yukseklik = son_harita.size
    kutu_x1, kutu_y1 = genislik - 480, 50
    kutu_x2, kutu_y2 = genislik - 50, 440
    
    cizici_son.rectangle([kutu_x1, kutu_y1, kutu_x2, kutu_y2], fill=(0, 0, 0, 220), outline=(255, 255, 255, 255), width=3)
    cizici_son.text((kutu_x1 + 140, kutu_y1 + 15), "LEJANT", fill=(255, 255, 255, 255), font=font_lejant)

    maddeler = [
        (RENK_ANAYOL, "Ana Yollar (Kizil)"), (RENK_ARAYOL, "Ara Sokaklar (Mavi)"),
        (RENK_BINA_STD_OUT, "Standart Binalar (AI)"), (RENK_TICARI_FILL, "Ticari/Ofis (Mavi)"), 
        (RENK_HASTANE_FILL, "Saglik/Eczane (Kirmizi)"), (RENK_OKUL_FILL, "Egitim/Okul (Sari)"),
        (RENK_HAVUZ_FILL, "Havuzlar (Turkuaz)"), (RENK_DOGA_FILL, "Park/Orman (Koyu Yesil)")
    ]

    y_offset = kutu_y1 + 80
    for renk, metin in maddeler:
        cizici_son.rectangle([kutu_x1 + 30, y_offset, kutu_x1 + 70, y_offset + 30], fill=renk)
        cizici_son.text((kutu_x1 + 90, y_offset - 5), metin, fill=(255, 255, 255, 255), font=font_lejant)
        y_offset += 40

    son_harita.convert("RGB").save(cikti_dosyasi)
    print(f"MÜKEMMEL! Hibrit motor tamamlandı. Harita: {cikti_dosyasi}")