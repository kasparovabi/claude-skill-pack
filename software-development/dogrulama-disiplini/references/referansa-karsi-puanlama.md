# Bir çıktıyı referans çıktıya karşı puanlayıp yakınsatmak

Elinde **hedef** (bilinen doğru çıktı) ve **aday** (yeni üretilen çıktı) varsa,
farkı sayıya çevirip tur tur kapatabilirsin. Kullanıcının deyimiyle "gauntlet
loop": puanla → en düşük boyutu bildir → düzelt → tekrar puanla.

Ne zaman işe yarar: bir motoru farklı girdiyle koşturup orijinaline benzetmek,
bir yeniden yazımın eskisiyle aynı davrandığını göstermek, bir dönüştürücünün
çıktısını referans dosyaya yaklaştırmak.

## 1. Piksel/bayt farkı ölçme — YAPISAL parmak izi çıkar

Doğrulanmış vakada aday bilerek farklı içerik taşıyordu (başka marka, başka
renk, başka metin). Piksel farkı ölçmek anlamsız olurdu: zaten farklı olmasını
istiyorduk. Ölçülen şey **yapısal sadakat**ti — öğeler aynı yerlerde mi, aynı
oranda mı, aynı hizada mı.

Parmak izi, içerikten bağımsız ve **orana normalize** alanlardan kurulur:

```python
@dataclass
class Profil:
    en_boy: float                              # w / h
    metin_sayisi: int
    metinler: list[tuple[float, float, float]] # (cx/w, y/h, boy/h)
    amblem_var: bool
    amblem_cy: float                           # merkez y / h
    amblem_h: float                            # yükseklik / h
    zemin_var: bool
    ortalama_sapma: float                      # yatay merkezden sapma
```

Mutlak koordinat değil **orana bölünmüş** değer sakla; hedef ile aday farklı
ölçüde olsa bile karşılaştırılabilir kalır.

## 2. Puanlayıcı: 10 üzerinden, her eksene tavanlı ceza

```python
def puanla(hedef, aday):
    notlar, puan = [], 10.0

    fark = abs(aday.en_boy - hedef.en_boy) / hedef.en_boy
    if fark > 0.02:
        ceza = min(2.0, fark * 4)          # TAVAN şart
        puan -= ceza
        notlar.append(f"en/boy: hedef {hedef.en_boy:.2f} aday {aday.en_boy:.2f} (-{ceza:.2f})")

    d = abs(aday.metin_sayisi - hedef.metin_sayisi)
    if d:
        ceza = min(2.5, d * 1.25)
        puan -= ceza
        notlar.append(f"metin satiri: {hedef.metin_sayisi} vs {aday.metin_sayisi} (-{ceza:.2f})")

    # metin dikey konumlari: ikisini de SIRALA, karsilikli olc
    n = min(len(hedef.metinler), len(aday.metinler))
    if n:
        hm = sorted(hedef.metinler, key=lambda m: m[1])
        am = sorted(aday.metinler, key=lambda m: m[1])
        ort = sum(abs(am[i][1] - hm[i][1]) for i in range(n)) / n
        if ort > 0.02:
            ceza = min(2.0, ort * 12)
            puan -= ceza
            notlar.append(f"dikey konum ortalama {ort:.3f} sapiyor (-{ceza:.2f})")

    return max(0.0, puan), notlar
```

Tasarım kuralları:

- **Her cezaya tavan koy.** Tavansız tek eksen puanı sıfırlar ve kalan
  eksenlerin bilgisi kaybolur. Vakada kampüs bandı 0,10 aldı, altı ayrı sorun
  vardı ama hangisinin baskın olduğu görünmüyordu.
- **Küçük sapmaya tolerans bırak** (`> 0.02`), yoksa gürültü ceza üretir.
- **Ceza gerekçesini metin olarak döndür.** "5,30/10" bir sonraki adımı
  söylemez; "metin satırı: 10 vs 6" söyler.

## 3. Tur döngüsü ve durma koşulu

Her turdan sonra puanı bir dosyaya ekle, önceki turla farkı bas:

```
tur 1: 5.41
tur 2: 7.28   (+1.87)
tur 3: 8.32   (+1.04)
tur 4: 9.06   (+0.74)
tur 5: 10.00  (+0.94)
```

Dur:
- puan **düştüyse** (son değişiklik zararlı, geri al),
- 3 tur üst üste **ilerlemediyse** (kalan kusur eksen kümesinin dışında),
- ya da tavana ulaştıysa → **modalite değiştir** (aşağıdaki 5. adım).

## 4. Bulunan hataların hepsi "yanlış varsayım" çıktı

Beş turda kapanan dört sorunun ortak kökü aynıydı: hedefin gerçek
parametrelerine bakmadan tahmin yürütmek.

| Bulgu | Gerçek | Kazanç |
|---|---|---|
| Ölçüler uydurulmuştu (40x60) | Hedef 126x65 | en büyük sıçrama |
| Yanlış düzen adı (`interior`) | `nameplate` | 6,28 → 10,00 |
| Yanlış düzen adı (`band`) | `campus` | 0,10 → 5,30 |
| Alan biçimi yanlış (ham dizi) | `{primary, secondary}` nesnesi | 5,30 → 10,00 |

**Önce hedefin çıktısını oku, sonra aday üret.** Ölçüler, düzen adları, alan
biçimleri referans dosyalardan çekilir:

```python
r = ET.parse(hedef).getroot()
print(r.get("viewBox"), r.get("width"), r.get("height"))
for t in r.iter():
    if t.tag.split("}")[-1] == "text":
        print(t.get("y"), t.get("font-size"), t.get("text-anchor"), (t.text or "")[:24])
```

Aynı disiplin motorun kendisi için de geçerli: benzerini yazma, **gerçek giriş
noktasını** çağır. Hangi alanları beklediğini kaynaktan oku
(`grep -n 'spec\.' render.js`), dokümana ya da hafızaya güvenme.

## 5. Tavan puandan sonra ZORUNLU adım: farklı modalitede bak

Bu tarifin en önemli maddesi. 10/10 alındıktan sonra çıktı render edilip gözle
bakıldı ve **iki kusur duruyordu**: bir öğe yanlış ölçekteydi, elle çizilmiş
bir metin okunmuyordu. Puanlayıcı ikisini de göremiyordu, çünkü o eksenler
tanımlanmamıştı.

```bash
rsvg-convert -w 1000 --background-color=white cikti.svg -o cikti.png
```
sonra `vision_analyze` ile sor: *"çakışma, taşma, yanlış ölçek var mı?"*

Raporlarken **"10/10" deme, "tanımlı 7 eksende 10/10" de** ve gözle bulunan
kusuru ayrıca söyle. Tavan puanı sonuç diye sunmak, ölçünün kapsamadığı yerde
kaliteyi garanti ediyormuş izlenimi verir.
