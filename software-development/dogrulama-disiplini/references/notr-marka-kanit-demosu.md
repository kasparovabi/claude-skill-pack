# Nötr marka demosu — müşteri işini ifşa etmeden kanıtlamak

## Ne zaman

Bir müşteri/kurum için kurulmuş bir aracın çalıştığını **dışarıya göstermek**
gerekiyor ama kurumun adı, logosu, renk kodları ve iç materyali görünmemeli.
Tipik tetikleyici: *"işin kendisine ait görsel paylaşsak daha iyi olur ama
kurumun ismi ve logosu gözükme sıkıntısı var."*

Aynı desen imza üreteci, tabela üreteci, rapor şablonu, editöryel PDF, sunum
üreteci gibi her parametrik araç için geçerli.

## Temel fikir

Araç gerçekten parametrikse (renk, oran, metin, varlıklar ayrı tanımlıysa)
markayı değiştirmek motoru değiştirmeyi gerektirmez. O yüzden:

> **Gerçek üretim motorunu çağır, yalnız içeriği nötrle.**

Bu aynı zamanda iddianın kanıtıdır. "Parametrik kurdum" demek ile "bak, aynı
motor başka bir markayla elini sürmeden çalışıyor" demek farklı ağırlıkta
şeylerdir.

## Adımlar

### 1. Demo çizici YAZMA — gerçek giriş noktasını çağır

İlk refleks hızlıca ayrı bir "demo üretici" yazmak oluyor. Bu vakada yazıldı ve
sonuç kanıtı **zayıflattı**: beş çıktı da neredeyse aynı düzende geldi, bir öğe
diğerinin üstüne bindi, aracın en iyi yaptığı şey (tipe göre farklı düzen) hiç
görünmedi.

Doğrusu üretim giriş noktasını aynen çağırmak (`renderSign`, `generate`, hangi
fonksiyonsa). Web arayüzü ve toplu üretim de onu çağırıyorsa sıfır sapma olur.

```bash
grep -n "^export function\|^export const\|^def " engine/render.js | head
```

### 2. Referans parametreleri hedefin ÇIKTISINDAN oku

Ölçüleri, düzen adlarını ve alan biçimlerini tahmin etme; gerçek çıktı
dosyalarından çıkar. Bu vakada dört ayrı "yanlış varsayım" hatası vardı
(yanlış ölçü, yanlış düzen adı, yanlış alan biçimi, yanlış veri şekli) ve
hedefin kendi çıktısı okununca puan tek adımda 5,41 → 9,06 çıktı.

```python
import xml.etree.ElementTree as ET
r = ET.parse(hedef).getroot()
print(r.get("viewBox"), r.get("width"), r.get("height"))
for t in (e for e in r.iter() if e.tag.split('}')[-1] == 'text'):
    print(t.get('y'), t.get('font-size'), t.get('text-anchor'), (t.text or '')[:30])
```

Alan adlarını da kaynaktan oku, İngilizce/Türkçe karışabiliyor:

```bash
grep -n "spec\." engine/render.js | head -30
```

### 3. Marka öğelerini ÇALIŞMA KOPYASINDA değiştir, kaynağa dokunma

Kaynağı okuyup `/tmp` altına nötrlenmiş kopya yaz, import'u oradan yap:

```
canon.js  -> renk kodları + kurum adları değiştirilmiş kopya
assets.js -> gerçek amblem/logotype vektörü basit geometrik eşdeğerle değiştirilmiş
```

Uydurma marka gerçek isme benzemesin (Orion, Atlantis gibi tarafsız adlar).

**Kaynağın bozulmadığını kanıtla, tahmin etme:**

```bash
git diff --stat                      # bos olmali
grep -c "<orijinal renk kodu>" engine/canon.js   # >=1 olmali
```

### 4. Birden fazla tip üret ve GÖZLE BAK

Tek örnek "parametrik" iddiasını taşımaz. Farklı düzenler yan yana gelince araç
kendini anlatır.

Render sonrası mutlaka görsel incele. Bu turda iki gerçek hata **yalnız bakınca**
çıktı, ikisi de kod hatasız çalışırken üretilmişti:

- geçersiz bir kademe anahtarı etikete `NDEFİNE` diye basılmıştı
- ters zeminli bantta amblem yanlış ölçekte küçücük bir nokta olmuştu

Bu, `dogrulama-disiplini` ana dosyasındaki "puan 10/10 oldu ama çıktı hâlâ
bozuk" bölümünün somut hâli: sayısal ölçüm bittiğinde modalite değiştir.

### 5. SVG → PNG (bu makinede çalışan yol)

`cairosvg` burada libcairo eksikliğinden patlıyor. Çalışan:

```bash
rsvg-convert -w 1000 --background-color=white girdi.svg -o cikti.png
```

Birleştirme (PIL):

```python
from PIL import Image
ims = [Image.open(f).convert('RGB') for f in dosyalar]
G = 1000
olcekli = [im.resize((G, int(im.height * G / im.width)), Image.LANCZOS) for im in ims]
H = sum(i.height for i in olcekli) + 24 * (len(olcekli) - 1)
tuval = Image.new('RGB', (G + 40, H + 40), '#EFEFEF')
y = 20
for i in olcekli:
    tuval.paste(i, (20, y)); y += i.height + 24
tuval.save('demo_hepsi.png')
```

## Paylaşırken

Görselin altına "gerçek marka öğesi kullanılmadı" notunu düşür. Demo işin
*kendisini* göstermiş olur; kurum, müşteri materyali ve iç süreç görünmez kalır.

## Sınır

Araç parametrik değilse nötr demo mümkün değildir — ama o durumda zaten
"parametrik kurdum" diye bir iddian olamaz. Nötr demo üretilemiyorsa iddiayı
gözden geçir.
