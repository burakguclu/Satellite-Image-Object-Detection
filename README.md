# Uydu Görüntüsü ile CBS Haritalama

Google Maps uydu görüntülerini indirip birleştiren ve üzerine OpenStreetMap verilerini (binalar, yollar, havuzlar, parklar) işleyerek zengin bir CBS haritası üreten Python projesi.

## Örnek Bölgeler
- **Ankara Çankaya** (Zoom 17)
- **İstanbul Boğaz** (Zoom 18)

## Kurulum

### 1. Bağımlılıkları yükleyin
```bash
pip install requests Pillow
```

### 2. API anahtarını ayarlayın
`ayarlar_ornek.json` dosyasını `ayarlar.json` olarak kopyalayıp Google Maps Static API anahtarınızı yazın:

```bash
copy ayarlar_ornek.json ayarlar.json
```

Veya çevresel değişken olarak ayarlayın:
```bash
set GOOGLE_MAPS_API_KEY=sizin_api_anahtariniz
```

## Kullanım

Sırasıyla çalıştırın:

```bash
python 1_indir.py       # Uydu görüntü parçalarını indirir
python 2_birlestir.py   # Parçaları tek bir büyük haritaya birleştirir
python 3_osm_ciz.py     # OSM verileriyle zenginleştirilmiş CBS haritası üretir
```

## Dosya Yapısı

| Dosya | Açıklama |
|-------|----------|
| `1_indir.py` | Google Maps Static API ile uydu karelerini indirir |
| `2_birlestir.py` | İndirilen kareleri büyük bir haritaya birleştirir |
| `3_osm_ciz.py` | Overpass API ile OSM verilerini çekip haritaya işler |
| `ayarlar.json` | Bölge koordinatları ve API anahtarı (git'e dahil değil) |
| `ayarlar_ornek.json` | Ayar dosyası şablonu |

## Çıktı Renk Kodları (Lejant)

- 🔴 **Kızıl-Turuncu** → Ana yollar
- 🔵 **Elektrik Mavisi** → Ara sokaklar
- 🟣 **Neon Mor** → Standart binalar
- 🟡 **Altın Sarısı** → Eğitim (okul/üniversite)
- 🔴 **Neon Kırmızı** → Sağlık (hastane/eczane)
- 🔵 **Neon Mavi** → Ticari (ofis/banka)
- 🟦 **Turkuaz** → Havuzlar
- 🟢 **Koyu Yeşil** → Park/Orman
