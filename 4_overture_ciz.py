import json
import os
import overturemaps
import pandas as pd
from shapely import wkb
from PIL import Image, ImageDraw

# Sadece binaların Overture'dan gelip gelmediğini test edeceğimiz Neon Mor renk
RENK_BINA_FILL = (160, 32, 240, 150) 
RENK_BINA_OUT = (200, 50, 255, 255)

with open("ayarlar.json", "r", encoding="utf-8") as f:
    ayarlar = json.load(f)

# Koordinatı piksele çeviren klasik matematik fonksiyonumuz
def piksele_cevir(enlem, boylam, bolge):
    dx = boylam - bolge['bati']
    dy = bolge['kuzey'] - enlem
    x = (dx / bolge['boylam_adimi']) * bolge['x_piksel'] + (bolge['x_piksel'] / 2) + bolge.get('x_kayma', 0)
    y = (dy / bolge['enlem_adimi']) * bolge['y_piksel'] + (bolge['y_piksel'] / 2) + bolge.get('y_kayma', 0)
    return (x, y)

for bolge in ayarlar["bolgeler"]:
    zemin_dosyasi = f"{bolge['isim']}_ham_harita.png"
    cikti_dosyasi = f"{bolge['isim']}_OVERTURE_TEST.png"

    if not os.path.exists(zemin_dosyasi):
        print(f"Atlanıyor: {zemin_dosyasi} bulunamadı.")
        continue

    print(f"\n---> {bolge['isim']} için OVERTURE MAPS yapay zeka binaları çekiliyor...")
    
    # Overture BBox formatı OSM'den farklıdır: (Batı, Güney, Doğu, Kuzey)
    # Tolerans payı ekliyoruz ki sınırdaki evler yarım çıkmasın
    tol = 0.0020
    bbox = (bolge['bati'] - tol, bolge['guney'] - tol, bolge['dogu'] + tol, bolge['kuzey'] + tol)
    
    try:
        # SİHİRLİ SATIR: Overture'un devasa veri tabanından 'building' (binaları) çekiyoruz
        tablo = overturemaps.record_batch_reader("building", bbox).read_all()
        df = tablo.to_pandas()
        print(f"BÜYÜK BAŞARI! Overture'dan tam {len(df)} adet bina verisi çekildi.")
    except Exception as e:
        print(f"Veri çekilemedi: {e}")
        continue

    harita = Image.open(zemin_dosyasi).convert("RGBA")
    cizim_katmani = Image.new("RGBA", harita.size, (255, 255, 255, 0))
    cizici = ImageDraw.Draw(cizim_katmani)

    # Gelen verideki her bir binayı haritaya işliyoruz
    for index, row in df.iterrows():
        try:
            # Overture verisi 'WKB' (Well-Known Binary) formatında gelir. Bunu Shapely ile çözüyoruz.
            geom = wkb.loads(row['geometry'])
            
            # Geometriyi çizim noktalarına çeviren yardımcı fonksiyon
            def ciz_poligon(polygon):
                noktalar = []
                # Shapely, koordinatları (Boylam, Enlem) sırasıyla verir
                for lon, lat in polygon.exterior.coords:
                    x, y = piksele_cevir(lat, lon, bolge)
                    noktalar.append((x, y))
                if len(noktalar) > 2:
                    cizici.polygon(noktalar, fill=RENK_BINA_FILL, outline=RENK_BINA_OUT)

            # Bazı binalar tek parça (Polygon), bazıları kompleks çok parçalıdır (MultiPolygon)
            if geom.geom_type == 'Polygon':
                ciz_poligon(geom)
            elif geom.geom_type == 'MultiPolygon':
                for poly in geom.geoms:
                    ciz_poligon(poly)
                    
        except Exception as e:
            continue

    son_harita = Image.alpha_composite(harita, cizim_katmani)
    son_harita.convert("RGB").save(cikti_dosyasi)
    print(f"MÜKEMMEL! Acarkent test haritanız '{cikti_dosyasi}' olarak kaydedildi.")