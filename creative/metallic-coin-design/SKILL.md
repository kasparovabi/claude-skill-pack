---
name: metallic-coin-design
description: "Use when designing a metallic coin or medal. Python PIL, 2D relief."
platforms: [macos, linux]
metadata:
  hermes:
    tags: [pil, pillow, coin, medal, commemorative, maarif, silver, bronze, metallic, map]
    category: creative
---

# Metalik Madeni Para / Madalya Tasarımı

AI görsel üreteci madeni para için güvenilmez — gerçek kurum logosu bozulur, dünya haritası
orantısız çıkar, metalik doku plastik görünür. Çözüm: PIL ile deterministik render.

## Kanvas Yapısı (RGBA, 900×900)

```python
SIZE = 900
CX, CY = 450, 450
R = 420  # dış yarıçap (kenar dahil)

# Katman sırası (alt → üst):
# 1. Metalik radyal gradyan dolgu
# 2. Dış koyu halka rim (~5px, metal kenar)
# 3. Tırtık çizgisi (tick_r = R-28, her 5°'de 3° çizgi, 2° boş)
# 4. İç ince kenar çizgisi (R-42)
# 5. Logo veya dünya haritası
# 6. Yay üzeri metin (arced text)
# 7. Düz metin (letter_spacing manuel)
# 8. Üst-sol parlaklık elipsi (beyaz, opacity ~0.15)
```

## Metalik Gradyan Formülleri

### Gümüş (silver)
```python
for i in range(R, 0, -1):
    t = i / R
    angle_factor = 0.5 + 0.5 * math.sin(math.pi * (1 - t))
    base = int(100 + 140 * t * angle_factor)
    r_c, g_c, b_c = base, base, base + 5
    alpha = 255 if i <= R - 5 else int(255 * (R - i) / 5)
    draw.ellipse([CX-i, CY-i, CX+i, CY+i], fill=(r_c, g_c, b_c, alpha))
```

### Bronz (bronze)
```python
    base = int(80 + 120 * t)
    r_c = min(255, int(base * 1.3))
    g_c = min(255, int(base * 0.85))
    b_c = min(255, int(base * 0.4))
```

## Logo Kaynağı — a client organisation

Önce yerel asset'e bak:
`~/.hermes/imported-from-pyto/workspaces/workspace-kasparov/assets/maarif-logo/logo_1_beyaz.png`

Yoksa web'den indir:
```bash
curl -sL "https://logowik.com/content/uploads/images/turkiye-maarif-vakfi5683.jpg" \
  -H "Referer: https://logowik.com/" -o /tmp/maarif_logo.jpg
```

Beyaz arka planı şeffaf yap (r>220 & g>220 & b>220 → alpha=0), sonra para yüzeyiyle uyumlu
renk tonu (gümüş için gray=80) uygula. Coin yüzeyine göm.

## Dünya Haritası — 6 Kıta (Antarktika Hariç)

Koordinat dönüşümü:
```python
def ll2px(lon, lat, cx, cy, r):
    x = cx + int((lon / 180) * (r - 15))
    y = cy - int((lat / 90) * (r - 15))
    return x, y
```

Kıta poligon listeleri (`references/continent-polygons.md`'de tam liste):
- **Kuzey Amerika**: [(-170,70), (-75,65), (-80,25), (-65,22), ..., (-130,70)]
- **Güney Amerika**: [(-80,10), (-35,-10), (-68,-45), (-40,-35), ..., (-80,10)]
- **Avrupa**: [(0,70), (-10,58), (5,54), (30,68), ...] + İberya/İtalya alt poligon
- **Afrika**: [(-18,15), (0,37), (44,5), (26,-34), (-18,0), ...]
- **Asya**: [(30,70), (145,60), (100,5), (30,20), ...]  + Japonya küçük elips
- **Okyanusya**: [(114,-22), (152,-35), (113,-28), ...] + Yeni Zelanda küçük elips

Kıta fill rengi gümüş için `(72,72,78,240)`, bronz için `(65,38,15,240)`.

Harita üzeri paralel ve meridyen çizgileri (opacity ~0.4–0.6):
- Yatay: ekvatörde `draw.line`, ±30°, ±60° için `path d="M95,Y Q160,Y2 225,Y"`
- Dikey: `draw.arc` eliptik meridyen (rx değişken, ry=r-15)

## Yay Üzeri Metin (Arced Text)

```python
def add_text_arc(img, text, radius, start_angle=0,
                 color=(70,70,75,230), font_size=30):
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Georgia.ttf", font_size)
    chars = list(text)
    char_angle = 2.8 / font_size * 20   # derece/karakter (yaklaşık)
    total_angle = (len(chars) - 1) * char_angle
    angle_start = start_angle - total_angle / 2
    for i, ch in enumerate(chars):
        angle_deg = angle_start + i * char_angle
        angle_rad = math.radians(angle_deg - 90)
        x = CX + radius * math.cos(angle_rad)
        y = CY + radius * math.sin(angle_rad)
        # 2x font_size'lık ch_img üret, rotate et, paste
        ch_img = Image.new('RGBA', (font_size*2, font_size*2), (0,0,0,0))
        ImageDraw.Draw(ch_img).text((font_size//2, font_size//2), ch, font=font, fill=color)
        ch_img = ch_img.rotate(-angle_deg, expand=False, center=(font_size, font_size))
        img.paste(ch_img, (int(x)-font_size, int(y)-font_size), ch_img)
```

## Düz Metin (Letter Spacing Manuel)

```python
def add_straight_text(img, text, y, color, font_size=28, letter_spacing=6):
    draw = ImageDraw.Draw(overlay)
    total_w = sum(font.getlength(c) for c in text) + letter_spacing*(len(text)-1)
    x = CX - total_w / 2
    for ch in text:
        cw = font.getlength(ch)
        draw.text((x, y), ch, font=font, fill=color)
        x += cw + letter_spacing
```

## Birleşik Kapak Görseli

```python
COIN_W = 600
PADDING = 40
LABEL_H = 60
total_w = COIN_W * 3 + PADDING * 4
total_h = COIN_W + LABEL_H + PADDING * 2 + 80

canvas = Image.new('RGB', (total_w, total_h), (15, 15, 22))  # koyu lacivert
```

Her `900×900` RGBA coin'i `(600,600)`'e resize et, LANCZOS, paste et, etiket yaz.

## Kritik Tuzaklar

**svglib renderPM macOS'ta çalışmaz.**
`renderPM.drawToFile()` → `cannot import desired renderPM backend rlPyCairo`. KULLANMA.
SVG'den para üretmek istersen: `renderPDF.draw(drawing, canvas, x, y)` ile PDF'e göm
ya da sıfırdan PIL ile çiz (daha güvenilir).

**SVG radialGradient svglib tarafından işlenmiyor.**
`Can't handle color: url(#s1)` uyarısı → gradient görmezden gelinir, para düz renk çıkar.
SVG içinde gradient KULLANMA; ya PIL ile çiz ya flat solid renkle SVG yaz.

**Logo boyutlandırma:** Logo JPG'si 866×650 (yatay). Coin'e yerleştirirken
yükseklik-bazlı boyutla (`scale * SIZE`), merkez-eksen dengeli yerleştir,
alt yazıya yer bırakmak için `y_offset = -40` gibi hafif yukarı al.

**Font yolu macOS:** Georgia için `/System/Library/Fonts/Supplemental/Georgia.ttf`.
Linux fallback: `/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf`.

**Çıktı gönderimi:** `sendPhoto` JPG için yeterli. Transparan PNG gerekirse `sendDocument`.

## Üretim Sırası

1. Logo indir/bul → vision ile teyit et
2. `write_file` ile render script'i `/tmp/coin_metallic.py`'ya yaz
3. `terminal` ile çalıştır
4. `vision_analyze` → logo net mi, harita orantılı mı, metin okunaklı mı?
5. Sorun varsa (harita çok küçük, logo taşıyor) → koordinatları/parametreleri düzelt, tekrar üret
6. Teyit sonrası `sendPhoto` ile Telegram'a gönder

Görsel üreteci KULLANMA — deterministik PIL render her zaman daha güvenilir ve hızlı.

## İlk Çıktı Kalitesi — Kullanıcı Geri Bildirimi

İlk SVG-tabanlı taslak şiddetli ret aldı: "Allah aşkına bu tasarım tam bir hayal kırıklığı — ne logo the client logosu, ne harita dünya haritası, tipografi desen gözlerim kanadı." Bunun nedeni SVG'de radialGradient + svglib uyumsuzluğuydu.

**İlk denemede doğru başlamak için kontrol listesi:**
- [ ] Gerçek logo kullandın mı? (PIL ile çizilmiş sahte logo değil)
- [ ] Kıta koordinatları doğru lon/lat → piksel dönüşümüyle mi? (kutuplar sıkışmasın)
- [ ] Gradyan PIL döngüsüyle mi üretildi? (SVG radialGradient değil)
- [ ] vision_analyze yaptın mı GÖNDERMEDEN ÖNCE?

## 3D Alternatif — Three.js + Browser Render

PIL 2D sunum için yeterliyken, "3 boyutlu görünsün" denilirse Three.js dene:

### Pipeline
1. Three.js'i CDN'den local'e indir:
   `curl -sL "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js" -o /tmp/three.min.js`
2. HTML'e INLINE göm (Python `str.replace` ile — sed/heredoc değil):
   Browser tool CDN erişemi yoktur, mutlaka inline!
3. `browser_navigate` ile `file:///tmp/dosya.html` aç.
4. `browser_vision` ile screenshot al → `~/.hermes/cache/screenshots/browser_screenshot_*.png` → `ls -t` ile en son bul → Telegram'a gönder.

### Three.js r128 Tuzakları
- `THREE.RoomEnvironment` r128'de YOK (r150+ gerektirir) → hata: "not a constructor". Bunun yerine `new THREE.PMREMGenerator(renderer).fromScene(new THREE.Scene()).texture` veya sadece DirectionalLight kullan.
- `renderer.domElement.toDataURL()` canvas'tan PNG base64 alır ama dosyaya doğrudan yazılamaz — browser_vision screenshot yolu daha kolay.
- `MeshStandardMaterial({ metalness: 0.92~0.98, roughness: 0.08~0.18 })` gerçekçi metal efekti verir.
- `envMapIntensity` 0.5–1.0 tut; yüksek değer her şeyi beyazlatır.
- Işıklama: `AmbientLight(0.3–0.5)` + `DirectionalLight(1.8–2.5)` + `toneMappingExposure(1.0)` dengeli çıkar.
