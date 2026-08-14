---
name: webgpu-browser-graphics
description: "Use when writing raw WebGPU or WGSL shaders. Includes render verification."
---

# WebGPU Tarayıcı Grafiği (ham WGSL, bağımlılıksız)

Landing page hero'su, marka animasyonu, parçacık sistemi, raymarching sahnesi gibi
tarayıcıda çalışan GPU grafiği üretmek için. Three.js/Babylon **olmadan**, tek dosya
ham WebGPU + WGSL. Headless Chrome ile render alıp görsel doğrulama döngüsü içerir.

Şu durumlarda yükle: "hero animasyonu", "WebGPU ile şunu yap", "siteye canlı görsel",
"shader yaz", "logo animasyonu", tarayıcıda parçacık/bloom/raymarching istendiğinde.

## Neden bağımlılıksız

Landing sayfasında bundle boyutu kritik. Bir hero efekti için three.js eklemek
gereksiz; ham WebGPU tek dosyada durur, ~10-60 KB. React tarafına taşınırken de
sadece `@webgpu/types` dev bağımlılığı gerekir (`tsconfig` → `"types": ["@webgpu/types"]`).

## Doğrulama döngüsü (bu skill'in kalbi)

Shader'ı yazıp "oldu" deme. Her turda render al, **gözünle bak**, düzelt. Bu iş
3-4 tur sürer ve normalidir.

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --enable-unsafe-webgpu \
  --enable-features=Vulkan,WebGPU --use-angle=metal \
  --screenshot=/tmp/kare.png --window-size=1280,720 \
  --virtual-time-budget=9000 "file:///tmp/sahne.html?t=5.0&k=1.0&m=9,9"
```

Sonra `vision_analyze` ile karaya bak: kompozisyon merkezde mi, renk dengesi nasıl,
metinle çakışma var mı. Bu döngüde yakalanan gerçek kusurlar: plastik görünen metal,
ekranın yarısını yiyen arka plan lekesi, sola kaymış kütle, spiral çıkan dağılım,
lime renginin mor/pembeyi yutması.

### Deterministik durum için URL parametresi

Shader'a zamanı ve durum değişkenlerini URL'den geçirilebilir yap
(`?t=` zaman, `?k=` animasyon evresi, `?m=x,y` imleç). Üç fayda:
tam istediğin anı yakalarsın, MP4 için kare dizisi üretirsin, ara evreleri
tek tek denetlersin.

```js
const qs = new URLSearchParams(location.search);
const FT = qs.get("t"), FK = qs.get("k"), FM = qs.get("m");
const t = FT !== null ? parseFloat(FT) : (performance.now() - t0) / 1000;
```

### ⚠ En kritik tuzak: `?t=` ile yaptığın hareket testi GEÇERSİZDİR

Sayfanın animasyon döngüsü tamamen donmuş olsa bile, `?t=2` ve `?t=5` iki farklı
görüntü verir — çünkü zamanı dışarıdan sen veriyorsun. Bu testle "hareket var"
sonucuna varmak yanlış pozitiftir; bu oturumda tam olarak bu hataya düştüm ve
kullanıcı hâlâ donuk sayfa görüyordu.

**Gerçek test: hiç parametre verme, aynı sayfayı iki farklı
`--virtual-time-budget` ile yakala, piksel farkını ölç.**
Detaylı script: `references/render-verification.md`.

## prefers-reduced-motion: durdurma, YAVAŞLAT

Erişilebilirlik adına "hareket azaltma açıksa animasyonu hiç başlatma" mantıklı
görünür ama Windows'ta bu ayar çok yaygın açıktır ve kullanıcı **sayfayı bozuk
sanır**. Bu oturumda kullanıcı "html dosyası statik açıldı, animasyon yok" dedi.

Doğru davranış:
- Animasyon her koşulda başlar.
- `prefers-reduced-motion` varsa döngü ~2 kat yavaşlatılır (sakin tempo).
- Kullanıcıya görünür bir **duraklat düğmesi** verilir, tercih onda kalır.
- Döngü `requestAnimationFrame`'den asla erken `return` etmez.

## file:// teslimi (kullanıcı kendi makinesinde denesin)

Kullanıcı Windows'ta çift tıklayıp açacaksa **fetch() çalışmaz** (CORS). Harici
JSON/veri dosyasını HTML'in içine göm. Koordinatları 3 basamağa yuvarlamak dosya
boyutunu yarıya indirir.

Teslim paketine şunları koy: gerçek hero yerleşimi (başlık/buton), sol altta
FPS + parçacık sayısı gösteren durum satırı, WebGPU yoksa ne yapılacağını anlatan
açıklamalı uyarı ekranı (`chrome://flags/#enable-unsafe-webgpu`).

## Teknik tarifler

### Çok geçişli bloom (gerçek ışıma)
HDR ara doku (`rgba16float`) → parlaklık ayıkla (yarı çözünürlük) → iki geçişli
Gauss (yatay, dikey) → birleştir + ACES ton eşleme + vinyet + film greni.
Tam pipeline ve bind group kurulumu: `references/bloom-pipeline.md`.

### Logo → nokta bulutu
PNG'yi PIL ile oku, hedef renkteki pikselleri topla, merkez motifi izole etmek için
yarıçapla kırp (dış halka/çerçeve genelde istenmez), rastgele örnekle, `[-1,1]`
aralığına normalize et, merkeze uzaklığa göre sırala (içten dışa oluşum için).
Script: `scripts/logo_to_points.py`.

### Dağılım: açı ve yarıçap BAĞIMSIZ olmalı
Altın açıyı ve yarıçapı aynı diziden türetirsen **spiral** çıkar (bu oturumda çıktı).
Ayrı hash'ler kullan, yarıçapa `sqrt` uygula (alan-eşit dolu bulut):
```js
const r1 = Math.abs(Math.sin(i * 12.9898) * 43758.5453) % 1;
const r2 = Math.abs(Math.sin(i * 78.2330) * 12345.6789) % 1;
const aci = r1 * Math.PI * 2;
const yari = 1.68 * Math.sqrt(r2);
```

### Metal görünümü
Düşük difüz + baskın yansıma. Işıkları doğrudan uygulamak "plastik" verir; bunun
yerine renkli bir `env(rd)` ışık kubbesi kur ve `reflect(rd,n)` ile örnekle.
İkinci sıçrama (metalin metali görmesi) cıva hissini verir. Schlick Fresnel ile
kenarlar tam ayna olur.

### Hareket izi
Parçacığın bir önceki karedeki konumunu da hesapla, hız yönünde quad'ı uzat.
Akışkanlık hissini veren şey budur.

## Kompozisyon (Kasparov'un anında yakaladığı şeyler)

- **Merkez-eksen dengesi.** Köşeye/kenara yaslamak kolaycılık sayılır.
- Hero'da metin solda, görsel sağda; **çakışma olmayacak**. Geniş ekranda motifi
  `select(0.0, 0.42, en > 1.15)` ile sağa kaydır, dar ekranda ortala + metne gölge.
- Tek renk baskın olmasın. Bloom parlak rengi (lime gibi) diğerlerini yutar;
  mor/pembe paylarını artır ve parlaklıklarını telafi et.
- Arka plan lekesiz olmalı: yansıma için kullanılan renkli ışıkları arka plana
  bulaştırma, zemini ayrı nötr degrade olarak çiz.

## Anlam kontrolü (teknik doğrulama YETMEZ)

Bu oturumun en değerli dersi. Teknik olarak kusursuz, görsel olarak etkileyici bir
sıvı metal hero yaptım; kullanıcının cevabı: *"Bu sadece güzel bir 3d animasyon,
herhangi bir anlamı ve bağlamı yok."*

Teslim etmeden önce sor: **bu görsel neyi anlatıyor, bu markaya mı ait?**
Aynı çıktı başka bir sitede de durabiliyorsa yanlıştır. Çözüm sitenin kendi
malzemesinden gelir: hero başlığı ("Maarifle Her Yerde, Hep Birlikte") → dünyaya
dağılmış parçacıklar kurumun armasındaki motifte birleşiyor. Şekil logodan
çıkarıldı, rastgele seçilmedi.

Ayrıca **veri yokken veri görselleştirmesi yapma.** Boş bir mezun sitesine "mezun
haritası" önerdim; kullanıcı haklı olarak reddetti (kayıtlı kimse yok). Veri
gerektirmeyen görsel seç.

## Performans

- Tam ekran raymarching maliyeti piksel sayısıyla artar → mobilde riskli.
  Instanced parçacık quad'ları çok daha ucuz.
- `devicePixelRatio` 2 ile sınırla.
- `document.hidden` ise render etme.
- Yük düşürme sırası: ana raymarch döngüsü 128→64, ikinci sıçramayı kapat,
  gölge döngüsü 28→12, bloom'u yarı yerine çeyrek çözünürlük.
- Pencere yeniden boyutlanınca HDR dokuları yeniden oluştur (`destroy()` + create).

## Kare dizisinden MP4

Headless Chrome her kare için ayrı süreç açar; 240 kare ~10 dakika sürer,
`background=true` ile çalıştır. Sonra:
```bash
ffmpeg -framerate 24 -pattern_type glob -i 'frames/*.png' \
  -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p out.mp4
```
Telegram için CRF 24 + 1280x720'ye küçült (20 MB → 3 MB).
