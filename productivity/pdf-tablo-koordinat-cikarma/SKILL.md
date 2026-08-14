---
name: pdf-tablo-koordinat-cikarma
description: Use when extracting tables from big PDFs by x-coordinate.
---

# PDF'ten Koordinat Bazlı Tablo Çıkarma

Büyük resmi PDF'lerden (ÖSYM kılavuzu, kurum tabloları, istatistik yayınları) satır/sütun verisi çıkarmak için. Metin akışına güvenmek yerine x-koordinatıyla sütun okur, sonucu bağımsız olarak doğrular.

## Ne zaman kullanılır

- 100+ sayfalık PDF'te tablo var, tüm satırlar lazım
- Sütunların bir kısmı boş (opsiyonel kontenjan, dipnot vb.) ve satır metni bu yüzden kayıyor
- "Şu koşulu sağlayan tüm kayıtlar" tipi tam kapsam isteniyor, örnekleme kabul edilmiyor

## Adımlar

### 1. Dosyayı kalıcı konuma kopyala
`/tmp` altındaki yüklenen dosyalar sistem tarafından silinebiliyor, iş yarıda kalıyor.
```bash
cp /tmp/yuklenen.pdf ~/calisma.pdf
```
Aynı dosyanın tekrar gönderilip gönderilmediğini hash ile teyit et: `shasum -a 256 dosya1 dosya2`

### 2. Tablo sayfa aralığını BAŞLIKTAN tespit et — asla tahmin etme
```python
import fitz
doc = fitz.open("~/calisma.pdf")
t3 = [i+1 for i in range(doc.page_count) if 'TABLO-3' in doc[i].get_text()[:300]]
print("Tablo-3:", t3[0], "-", t3[-1])
```
Sayfa aralığını yanlış varsaymak en pahalı hata: tablo olmayan bölümler (koşul açıklamaları, ücret listeleri) de parse edilir ve sonuç şişer.

### 3. Sütun x-koordinatlarını başlık satırından oku
```python
page = doc[BASLIK_SAYFASI]
for w in page.get_text("words"):
    x0, y0, x1, y1, t = w[:5]
    if y0 < 100:                      # başlık bölgesi
        print(f"x={x0:6.1f} y={y0:6.1f} '{t}'")
```
Sütun numaraları `(7)`, `(8)`, `(9)` şeklinde ayrı satırda olur; hangi başlığın hangi x'te olduğunu buradan eşle. **Tablodan tabloya koordinatlar değişir** — her tablo için ayrı koordinat seti çıkar.

### 4. Satırları y-koordinatına göre grupla, sütunu x aralığıyla oku
```python
rows = {}
for x0, y0, x1, y1, t, *_ in page.get_text("words"):
    rows.setdefault(round(y0 / 1.4) * 1.4, []).append((x0, t))

for k in sorted(rows):
    row = sorted(rows[k], key=lambda p: p[0])
    kod = [t for x, t in row if t.isdigit() and len(t) == 9 and x < 30]
    hedef = [t for x, t in row if 332 <= x <= 366]   # aranan sütun
```
y toleransı 1.4-2.0 arası iyi çalışır; çok küçük olursa satır bölünür, çok büyük olursa iki satır birleşir.

### 5. SÜTUNU BAĞIMSIZ OLARAK DOĞRULA (atlanmamalı)
Doğru sütunu okuduğunu, o sütunun **boş olması gereken bir alt kümede gerçekten boş olduğunu** göstererek kanıtla.

Örnek: 34 yaş kontenjanı sadece devlet üniversitelerinde olur → vakıf üniversitesi sayfalarında o sütun tamamen boş çıkmalı.
```python
hist = collections.Counter()
for pno in VAKIF_SAYFALARI:
    ...
    for x, t in row:
        if t.isdigit() and len(t) <= 3 and 295 < x < 380:
            hist[round(x)] += 1
# beklenen: hedef x'te 0 kayıt
```
Bu test tutmuyorsa yanlış sütunu okuyorsun demektir.

### 6. Spot-check: rastgele kayıtları ham satırla karşılaştır
```python
import random; random.seed(7)
for r in random.sample(kayitlar, 6):
    # PDF'te kodu bul, ham satır metnini bas, JSON değerleriyle kıyasla
```
6/6 tutmuyorsa parse hatalıdır.

### 7. Kuralın tam metnini oku, listeyi ona karşı süz
Kılavuzun açıklama bölümünde çoğu zaman **kapsam dışı bırakılan kalemler** vardır (ÖSYM'de Pilotaj, Uçak Bakım, Sivil Savunma vb.). Tabloda kontenjan görünse bile bunlar tercih edilemez. Kural metnini bulup listeden çıkar.

## Tuzaklar

**Türkçe `.upper()` sessizce bozar.** Python'da `"Açıköğretim".upper()` → `"AÇIKÖĞRETIM"` (İ değil I). `if "AÇIKÖĞRETİM" in metin.upper()` **hiçbir zaman eşleşmez** ve sıfır sonuç döner, hata da vermez. Türkçe kelime aramasını **ham metinde** yap:
```python
if "Açıköğretim" in full:            # DOĞRU
if "AÇIKÖĞRETİM" in full.upper():    # YANLIŞ — hep False
```
Aynı sorun `.title()` için de geçerli: `"BİLİMLER".title()` bozuk çıktı üretir. TR-güvenli başlık fonksiyonu yaz:
```python
TRMAP = str.maketrans("ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ", "abcçdefgğhıijklmnoöprsştuüvyz")
def tr_title(s):
    return " ".join(w[0] + w[1:].translate(TRMAP) if len(w) > 1 else w for w in s.split())
```

**Kurum adı satırlar arasına dağılır.** Üniversite adı iki satıra bölünebilir ("... ÜNİVERSİTESİ" / "(Devlet Üniversitesi)"). Tampon tut, `(Devlet` / `(Vakıf` gördüğünde birleştir, **program satırı gördüğünde tamponu temizle** — yoksa bir önceki kurumun adı sonrakine sızar.

**Ad alanı taşar.** Uzun program adları sütun sınırını aşar. Ad çıkarırken x aralığı yerine regex kullan: `re.match(r"^\d{9}\s+(.+?)\s+2\s+TYT\b", full)`

**Aynı sayıyı iki sütunda arama.** Özel koşul kodu ile kontenjan sayısı benzer büyüklükte olabilir (17, 31, 320). Değere göre değil, **yalnızca x-koordinatına göre** ayır.

**reportlab renk hatası.** `<font color="...">` içine `HexColor` nesnesi değil `"#rrggbb"` string'i ver.

## Çıktı

Rapor/liste isteniyorsa PDF üret (landscape A4, reportlab). Türkçe font olarak `/System/Library/Fonts/Supplemental/Arial.ttf` ve `Arial Bold.ttf` kaydet. Üretilen PDF'i sayfa sayfa PNG'ye çevirip `vision_analyze` ile kontrol et: taşma, kesilen başlık, bozuk Türkçe karakter arıyorsun.

```python
d = fitz.open("cikti.pdf")
for i in range(d.page_count):
    d[i].get_pixmap(matrix=fitz.Matrix(2, 2)).save(f"/tmp/p{i}.png")
```
