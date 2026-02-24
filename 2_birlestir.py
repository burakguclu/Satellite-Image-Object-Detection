import json
import os
import re
from PIL import Image

with open("ayarlar.json", "r", encoding="utf-8") as f:
    ayarlar = json.load(f)

for bolge in ayarlar["bolgeler"]:
    klasor = f"{bolge['isim']}_parcalar"
    cikti_adi = f"{bolge['isim']}_ham_harita.png"
    
    print(f"---> {bolge['isim']} parçaları birleştiriliyor...")
    if not os.path.exists(klasor):
        print(f"Klasör bulunamadı, atlanıyor: {klasor}")
        continue

    dosyalar = [f for f in os.listdir(klasor) if f.endswith('.png')]
    if not dosyalar: continue

    pattern = re.compile(r"kare_satir(\d+)_sutun(\d+)\.png")
    max_satir, max_sutun = 0, 0
    for d in dosyalar:
        match = pattern.match(d)
        if match:
            max_satir, max_sutun = max(max_satir, int(match.group(1))), max(max_sutun, int(match.group(2)))

    toplam_satir, toplam_sutun = max_satir + 1, max_sutun + 1
    x_piksel, y_piksel = bolge['x_piksel'], bolge['y_piksel']
    
    # Kırpma ayarları
    sol = (1280 - x_piksel) // 2
    ust = (1280 - y_piksel) // 2
    
    tuval = Image.new('RGB', (toplam_sutun * x_piksel, toplam_satir * y_piksel), (0,0,0))
    
    for s in range(toplam_satir):
        for c in range(toplam_sutun):
            dosya_yolu = os.path.join(klasor, f"kare_satir{s}_sutun{c}.png")
            if os.path.exists(dosya_yolu):
                img = Image.open(dosya_yolu)
                tuval.paste(img.crop((sol, ust, sol + x_piksel, ust + y_piksel)), (c * x_piksel, s * y_piksel))
                
    tuval.save(cikti_adi)
    print(f"Başarılı: {cikti_adi} oluşturuldu.")