# İnteraktif Değer Sunumu: Web Sitesi + Canlı İnfografik PDF

Kullanıcı değer/teklif belgesini "daha interaktif, izlemesi sıkmayan" ve "daha canlı bir PDF" isterse, İKİ çıktı üret. İkisi de AYNI görsel dilde (koyu kurumsal tema + kanon renkler) olmalı ki tutarlı dursun.

## Görsel kimlik (the client örneği — kanon)
- Koyu lacivert zemin (`--bg:#0f1923`, kart `#1b2c39`), kurumsal mavi `#3479A3`, altın `#886848`/`#b08d5e`.
- Başlıklarda altın→beyaz gradyan (`-webkit-background-clip:text`).
- Durum noktaları: yeşil (yapılıyor) / amber (kısmen) / gri (yok).
- Kart üst şeridi: mavi→altın gradyan 3px.

## Çıktı 1 — İnteraktif tek-dosya web sitesi
Bağımlılıksız tek `index.html`. Anahtar etkileşimler:
- **Scroll-reveal:** `.reveal` sınıfı opacity:0+translateY; `IntersectionObserver` (threshold .12) ile görünürken `.in` ekle, `unobserve` et.
- **Sayaç animasyonu:** `data-count` li sayıları ayrı bir IntersectionObserver (threshold .4) ile setInterval ile artır. `data-suffix=" ₺"` gibi son ek desteği; 0 ise direkt yaz.
- **Nav küçülmesi:** scroll>40 olunca padding daralt.
- Bölümler: hero (gradyan başlık + rozet) → istatistik şeridi → 3 sütun (TASARRUF/HIZ/PRESTİJ) → envanter kart grid (badge'li) → 14 alan durum (renkli nokta) → gerekçe → yol haritası timeline → kadro → kapanış CTA + footer.
- Logoları `img/` ile koyup GitHub Pages'e deploy et. Tarayıcıda `browser_navigate` + aşağı kaydırıp `browser_vision` ile reveal'ın gerçekten tetiklendiğini DOĞRULA (ilk snapshot'ta alt bölümler opacity:0 olduğu için boş görünür — bu normal, kaydırınca açılmalı).

## Çıktı 2 — Koyu temalı infografik PDF (headless Chrome)
reportlab koyu tema + CSS gradyan/gölge için zayıf. Bunun yerine print-uyarlı bir HTML yaz, headless Chrome ile PDF bas — gradyanlar/gölgeler/emoji tam render olur.

### Adımlar
1. Print HTML: her sayfa `.page{ width:210mm; height:296mm; padding:16mm 15mm 14mm; page-break-after:always; overflow:hidden }`. **`min-height:297mm` KULLANMA** — içerik 297'yi taşırsa her A4'ten sonra fazladan boş/yarım sayfa üretir (3 sayfa→5 sayfa olur). Sabit `height:296mm` + `overflow:hidden` taşmayı keser. `@page{size:A4;margin:0}` ve her elemana `print-color-adjust:exact` (koyu zemin basılsın).
2. Bas: `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu --no-pdf-header-footer --print-to-pdf=/tmp/out.pdf "file:///tmp/print.html"`. (GCM/PHONE_REGISTRATION_ERROR uyarıları zararsız — Chrome arka plan servisi.)
3. Sayfa sayısını ve düzeni `fitz` ile PNG'e render edip `vision_analyze` ile kontrol et (taşma, footer çakışması, Türkçe karakter). Taşarsa: bölüm `margin-top`'larını ve son-bölüm boşluklarını sıkıştır; alt imza bloğu footer şeridiyle çakışıyorsa kompakt tek-satır imzaya indir.
4. **Her cihazda birebir için rasterize et** (reportlab-turkish-pdf'teki kalıp): `fitz` ile dpi=180 pixmap → JPEG q88 → yeni PDF'e `insert_image`. `get_fonts()` 0 dönmeli (salt resim). 3 sayfa ~1MB, Telegram limiti içinde.
5. Telegram'a `sendDocument` ile gönder (token'ı inline al — SKILL.md pitfall'ına bak).

## Sıra/paralellik
Web deploy build'i olurken (gh-pages "building") PDF'i rasterize edip gönder — paralel ilerle. En son web'in canlıya geçtiğini `curl ".../?v=$(date +%s)"` ile doğrula.
