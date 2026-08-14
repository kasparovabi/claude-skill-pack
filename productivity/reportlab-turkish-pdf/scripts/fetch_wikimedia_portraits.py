#!/usr/bin/env python3
# Wikimedia Commons portrelerini indir + 240px kare portreye kırp.
# Thumb URL'leri 400 verir; ORİJİNAL dosya URL'i kullanılır. 429'a karşı sleep+retry.
# Kullanım: PORTRAITS sözlüğünü doldur (no -> "proj/d1/d2/Dosya.jpg"), çalıştır.
# Çıktı: /tmp/portraits/<no>.jpg (240px kare). Sonra 4x3 kontak sayfası ile vision doğrula.
import os, urllib.request, time
try:
    from PIL import Image
except Exception as e:
    raise SystemExit("Pillow gerekli: pip3 install pillow")

OUT_DIR="/tmp/portraits"
os.makedirs(OUT_DIR, exist_ok=True)
SIZE=240
H={"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15"}

# no -> commons/wikipedia yolu. Örn: "commons/a/a8/Ataturk1930s.jpg" veya "tr/a/a1/File.jpg"
# Yolları hedef Wikipedia sayfasının HTML'inden upload.wikimedia.org linklerini grepleyerek bul.
PORTRAITS = {
 # 1: "commons/a/a8/Ataturk1930s.jpg",
}

def orig_url(path):
    proj,d1,d2,fn=path.split("/",3)
    return f"https://upload.wikimedia.org/wikipedia/{proj}/{d1}/{d2}/{fn}"

# 1) İndir (429 backoff)
for no,path in PORTRAITS.items():
    raw=f"{OUT_DIR}/{no}_raw"
    if os.path.exists(raw): continue
    url=orig_url(path)
    for attempt in range(4):
        try:
            data=urllib.request.urlopen(urllib.request.Request(url,headers=H),timeout=30).read()
            if len(data)>3000:
                open(raw,"wb").write(data); print(no,"DL",len(data)); break
        except Exception as e:
            print(no,"retry",attempt,str(e)[:50]); time.sleep(6)
    time.sleep(4)  # 429 önleme: istekler arası bekle

# 2) Kare kırp (üstten %18 offset, yüz ortaya gelsin)
for no in PORTRAITS:
    raw=f"{OUT_DIR}/{no}_raw"
    if not os.path.exists(raw): continue
    im=Image.open(raw).convert("RGB")
    w,h=im.size; side=min(w,h)
    left=(w-side)//2; top=int((h-side)*0.18)
    if top+side>h: top=h-side
    if top<0: top=0
    im=im.crop((left,top,left+side,top+side)).resize((SIZE,SIZE),Image.LANCZOS)
    im.save(f"{OUT_DIR}/{no}.jpg","JPEG",quality=88)
    print(no,"kırpıldı")
print("hazır — şimdi kontak sayfası + vision doğrula")
