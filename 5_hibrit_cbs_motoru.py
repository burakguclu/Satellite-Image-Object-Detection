import json
import requests
import os
import overturemaps
import pandas as pd
from shapely import wkb
from PIL import Image, ImageDraw, ImageFont

# ==============================================================================
# YÜKSEK KONTRASTLI RENK PALETİ
# ==============================================================================
RENK_DOGA_FILL = (0, 80, 0, 90)          
RENK_ANAYOL = (255, 69, 0, 255)          
RENK_ARAYOL = (0, 191, 255, 220)         
RENK_BINA_STD_FILL = (160, 32, 240, 110) 
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

# RAPORLARI TUTACAĞIMIZ ANA LİSTE
tum_raporlar = []

for bolge in ayarlar["bolgeler"]:
    zemin_dosyasi = f"{bolge['isim']}_ham_harita.png"
    cikti_dosyasi = f"{bolge['isim']}_ULTIMATE_HIBRIT.png"

    if not os.path.exists(zemin_dosyasi):
        print(f"Atlanıyor: {zemin_dosyasi} bulunamadı.")
        continue
        
    # --- BU BÖLGE İÇİN İSTATİSTİK SAYAÇLARI ---
    istatistik = {
        "Bölge Adı": bolge['isim'],
        "Havuz Sayısı": 0,
        "Yapay Zeka (AI) Bina Sayısı": 0,
        "Ticari Bina Sayısı": 0,
        "Eğitim Binası Sayısı": 0,
        "Sağlık Binası Sayısı": 0,
        "Toplam Yeşil Alan (m2)": 0,
        "Toplam İnşaat Alanı (m2)": 0
    }

    print(f"\n{'='*50}\n---> {bolge['isim']} İÇİN HİBRİT MOTOR VE RAPORLAMA BAŞLADI\n{'='*50}")
    
    tolerans = 0.0020 
    sorgu_kuzey, sorgu_guney = bolge['kuzey'] + tolerans, bolge['guney'] - tolerans
    sorgu_bati, sorgu_dogu = bolge['bati'] - tolerans, bolge['dogu'] + tolerans

    bbox = (sorgu_bati, sorgu_guney, sorgu_dogu, sorgu_kuzey)
    try:
        tablo = overturemaps.record_batch_reader("building", bbox).read_all()
        df_overture = tablo.to_pandas()
    except Exception:
        df_overture = pd.DataFrame() 

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
    
    cevap = requests.post("http://overpass-api.de/api/interpreter", data={'data': overpass_sorgusu}, headers={'User-Agent': 'Mozilla/5.0'})
    elemanlar = cevap.json().get('elements', []) if cevap.status_code == 200 else []

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

    # KATMAN 1: OSM Doğal Alanlar (Yeşil Alan İstatistiği)
    for e in elemanlar:
        if e.get('tags', {}).get('leisure') == 'park' or e.get('tags', {}).get('natural') == 'wood':
            noktalar = [piksele_cevir(n['lat'], n['lon']) for n in e.get('geometry', [])]
            if len(noktalar) > 2: 
                cizici.polygon(noktalar, fill=RENK_DOGA_FILL)
                # Yeşil alan hesapla ve rapora ekle
                m2 = int(piksel_alani_hesapla(noktalar) * bolge['m2_carpani'])
                istatistik["Toplam Yeşil Alan (m2)"] += m2

    # KATMAN 2: OSM Yollar
    for e in elemanlar:
        yol_turu = e.get('tags', {}).get('highway')
        if yol_turu:
            noktalar = [piksele_cevir(n['lat'], n['lon']) for n in e.get('geometry', [])]
            if yol_turu in ['primary', 'secondary', 'trunk']: cizici.line(noktalar, fill=RENK_ANAYOL, width=10)
            elif yol_turu in ['residential', 'tertiary']: cizici.line(noktalar, fill=RENK_ARAYOL, width=5)
            else: cizici.line(noktalar, fill=(200, 200, 200, 150), width=2)

    # KATMAN 3: OVERTURE Binaları (AI Bina İstatistiği)
    if not df_overture.empty:
        for index, row in df_overture.iterrows():
            try:
                geom = wkb.loads(row['geometry'])
                def ciz_overture_poligon(polygon):
                    noktalar = [piksele_cevir(lat, lon) for lon, lat in polygon.exterior.coords]
                    if len(noktalar) > 2:
                        metrekare = int(piksel_alani_hesapla(noktalar) * bolge['m2_carpani'])
                        if metrekare > 10000: return 
                            
                        cizici.polygon(noktalar, fill=RENK_BINA_STD_FILL, outline=RENK_BINA_STD_OUT)
                        
                        # AI Bina İstatistiklerini Güncelle
                        istatistik["Yapay Zeka (AI) Bina Sayısı"] += 1
                        istatistik["Toplam İnşaat Alanı (m2)"] += metrekare
                        
                        if metrekare > 30:
                            merkez_x = sum(p[0] for p in noktalar) / len(noktalar)
                            merkez_y = sum(p[1] for p in noktalar) / len(noktalar)
                            cizici.text((merkez_x-10, merkez_y-5), f"{metrekare}m2", fill=(0,0,0,255), font=font)
                            cizici.text((merkez_x-11, merkez_y-6), f"{metrekare}m2", fill=(255,255,255,255), font=font)

                if geom.geom_type == 'Polygon': ciz_overture_poligon(geom)
                elif geom.geom_type == 'MultiPolygon':
                    for poly in geom.geoms: ciz_overture_poligon(poly)
            except Exception: pass

    # KATMAN 4: OSM Akıllı Binalar (Özel Bina İstatistiği)
    for e in elemanlar:
        if 'building' in e.get('tags', {}):
            tags = e.get('tags', {})
            bina_turu = tags.get('building', '')
            amenity = tags.get('amenity', '')
            
            # Kategori belirleme
            if amenity in ['school', 'university', 'college'] or bina_turu == 'school':
                renk, cerceve = RENK_OKUL_FILL, (255, 255, 0, 255)
                istatistik["Eğitim Binası Sayısı"] += 1
            elif amenity in ['hospital', 'clinic', 'pharmacy']:
                renk, cerceve = RENK_HASTANE_FILL, (255, 0, 0, 255)
                istatistik["Sağlık Binası Sayısı"] += 1
            elif bina_turu in ['commercial', 'retail', 'office'] or amenity in ['bank', 'marketplace']:
                renk, cerceve = RENK_TICARI_FILL, RENK_TICARI_OUT
                istatistik["Ticari Bina Sayısı"] += 1
            else:
                continue 
                
            noktalar = [piksele_cevir(n['lat'], n['lon']) for n in e.get('geometry', [])]
            if len(noktalar) > 2:
                cizici.polygon(noktalar, fill=renk, outline=cerceve)
                metrekare = int(piksel_alani_hesapla(noktalar) * bolge['m2_carpani'])
                istatistik["Toplam İnşaat Alanı (m2)"] += metrekare # Özel binaları da inşaat alanına ekle
                
                if metrekare > 30:
                    merkez_x = sum(p[0] for p in noktalar) / len(noktalar)
                    merkez_y = sum(p[1] for p in noktalar) / len(noktalar)
                    cizici.text((merkez_x-10, merkez_y-5), f"{metrekare}m2", fill=(0,0,0,255), font=font)
                    cizici.text((merkez_x-11, merkez_y-6), f"{metrekare}m2", fill=(255,255,255,255), font=font)

    # KATMAN 5: Havuzlar (Havuz İstatistiği)
    for e in elemanlar:
        if e.get('tags', {}).get('leisure') == 'swimming_pool':
            noktalar = [piksele_cevir(n['lat'], n['lon']) for n in e.get('geometry', [])]
            if len(noktalar) > 2: 
                cizici.polygon(noktalar, fill=RENK_HAVUZ_FILL, outline=RENK_HAVUZ_OUT)
                istatistik["Havuz Sayısı"] += 1

    # Lejant ve Çizim Kayıtları (Aynı kalıyor...)
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
    print(f"HARİTA TAMAMLANDI: {cikti_dosyasi}")
    
    # İstatistiği ana listeye ekle
    tum_raporlar.append(istatistik)

# ==============================================================================
# TÜM İŞLEMLER BİTİNCE EXCEL/CSV RAPORUNU ÇIKAR
# ==============================================================================
if tum_raporlar:
    df_rapor = pd.DataFrame(tum_raporlar)
    rapor_dosyasi = "SEHIR_RAPORLARI.csv"
    
    # Türkçe karakter bozulmaması için utf-8-sig kullanıyoruz (Excel dostu)
    df_rapor.to_csv(rapor_dosyasi, index=False, encoding='utf-8-sig')
    
    print(f"\n{'*'*50}")
    print(f"MÜKEMMEL! Tüm analizler tamamlandı.")
    print(f"Veri raporunuz '{rapor_dosyasi}' dosyasına kaydedildi.")
    print(df_rapor.to_string(index=False)) # Konsola da havalı bir şekilde yazdıralım
    print(f"{'*'*50}")