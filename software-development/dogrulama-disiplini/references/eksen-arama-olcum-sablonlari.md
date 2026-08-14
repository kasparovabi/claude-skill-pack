# Eksen arama: "TEMIZ dedi ama bozuk" vakasini cozme sablonu

Bir denetim geciyor ama kullanici arizayi goruyor. SKILL.md'deki merdiveni
uygularken kullanilan somut olcum sablonlari. Iki gercek vakadan cikti
(6 Agu 2026): altyazi cue yapisi ve cift kayit yakalayici.

## Adim 1 — Denetimin ekseni ne?

Kaynagi ac ve **neyi karsilastirdigini** bul. Cogu zaman docstring bile soyler.

Vaka 1, `srt_senkron.py`: cue basi ile kelime `start` degerini karsilastiriyor.
Yani ekseni **zaman hizasi**. Cue'nun ne kadar surdugu ya da kac cumle tasidigi
kodun hicbir yerinde gecmiyor.

Vaka 2, `find_duplicate()`: `SequenceMatcher(slug_a, slug_b)`. Ekseni **yazim
benzerligi**. Kaynak ve anahtar kelime alanlarina hic bakmiyor.

Bunu yazamiyorsan devam etme; hangi eksende korlestigin bilinmeden dogru eksen
aranamaz.

## Adim 2 — Arizali ornegi mevcut eksende olc

Amac: deger esigin yanlis tarafinda mi (esik sorunu), yoksa eksen konuyla
alakasiz mi (boyut sorunu)?

```python
import sys
sys.path.insert(0, "/proje/yolu")
from lib.ledger import _similarity, NEAR_DUPLICATE_RATIO

a, b = "kucuk-atolyede-siparis-durumu-tahtasi", "kucuk-atolye-acik-is-panosu"
print(f"esik={NEAR_DUPLICATE_RATIO}  olculen={_similarity(a, b):.3f}")
# esik=0.86  olculen=0.529
```

0,53 ile 0,86 arasi kapatilabilir gorunuyor. **Burada durma** — esigi
dusurmeden once bir sonraki adima gec.

## Adim 3 — Aday eksenleri arizali cift uzerinde ele

Esik dusurmenin ise yarayip yaramayacagini, ayni cifti **baska eksenlerde**
olcerek anlarsin. Ayirt edici sayi vermeyen eksen yanlis eksendir.

```python
def tokens(slug):
    return set(slug.split("-"))

ja, jb = tokens(a), tokens(b)
jac = len(ja & jb) / len(ja | jb)
print(f"kelime ortusmesi = {jac:.3f}")   # 0.095
```

Kritik bulgu: 0,095. Yani kelime ekseninde bu cift **hicbir esikte** yakalanmaz
ve esigi oraya cekmek yalniz yanlis alarm uretir. Iki eksen de olu cikinca
uydurma degil, olculmus bir gerekcen olur: "esik dusurmek cozum degil."

Sonra gercek sinyali ara. Alan alan dene:

```python
def demand_sources(row):
    """Rakip/referans linkleri ELE — onlar ortam gurultusu."""
    out = set()
    for s in json.loads(row["sources"] or "[]"):
        u = (s.get("url") if isinstance(s, dict) else s) or ""
        if u and "apps.apple.com" not in u and "play.google.com" not in u:
            out.add(u.rstrip("/"))
    return out

def kw_words(row):
    return {w for p in json.loads(row["keywords"] or "[]") for w in p.lower().split()}

ortak = demand_sources(x) & demand_sources(y)
kw = len(kw_words(x) & kw_words(y)) / len(kw_words(x) | kw_words(y))
print(f"ortak kaynak={len(ortak)}  kelime ortusmesi={kw:.2f}")
# ortak kaynak=2  kelime ortusmesi=0.65
```

0,65 ayirt edici. Eksen bulundu.

## Adim 4 — Yanlis alarm butcesi (ATLAMA)

Yeni eksen arizali cifti yakaliyor diye dogru degildir; tum veri kumesinde kac
kayit isaretledigini olc. Bu adim atlanirsa denetim her seye "cift" der ve
okunmaz hale gelir.

```python
bulunan = []
for i in range(len(rows)):
    for j in range(i + 1, len(rows)):
        x, y = rows[i], rows[j]
        if not (demand_sources(x) & demand_sources(y)):
            continue
        kw = kw_benzer(kw_words(x), kw_words(y))
        if kw >= 0.30:                      # once GENIS tara, sonra daralt
            bulunan.append((kw, x, y))

for kw, x, y in sorted(bulunan, key=lambda t: -t[0]):
    print(f"kw={kw:.2f}  #{x['id']} <-> #{y['id']}")
print(f"toplam: {len(bulunan)} / {len(rows)*(len(rows)-1)//2}")
# 9 / 2080  — aranan cift en tepede (0.65)
```

Saglikli isaret: aranan cift **en tepede**, toplam isaret sayisi veri kumesinin
yuzdesi degil binde biri mertebesinde. Yuzlerce isaret cikiyorsa eksen fazla
geniş, esigi yukari cek ya da ikinci bir kosul ekle.

Esigi 0,30'da tarayip 0,55'te sabitlemek: en yakin karsi ornek 0,63'tu, yani
sinira yapismamak icin iki taraftan da pay birakildi.

## Adim 5 — Regresyon + mutasyon testi

Yakalama testi tek basina yetmez; her seye "cift" diyen bir denetim de onu gecer.
Dort test yaz:

```python
def test_arizali_cift_yakalanir(tmp_path):      # yakalama
def test_gurultu_ekseni_cift_saymaz(tmp_path):  # rakip linki ortak ama ayri fikir
def test_ortak_kaynak_tek_basina_yetmez(tmp_path):
def test_veri_eksikse_eski_davranis(tmp_path):  # anahtar kelime yoksa
```

Sonra duzeltmeyi **gecici olarak geri al** ve testin gercekten kirmizi yandigini
gor:

```bash
cp lib/ledger.py /tmp/iyi.py
python3 - <<'PY'
from pathlib import Path
p = Path("lib/ledger.py"); s = p.read_text()
p.write_text(s.replace("SHARED_SOURCE_KEYWORD_RATIO = 0.55",
                       "SHARED_SOURCE_KEYWORD_RATIO = 9.99"))
PY
python3 -m pytest tests/test_cift_kayit.py -q     # 1 failed bekleniyor
cp /tmp/iyi.py lib/ledger.py
python3 -m pytest tests/ -q                       # hepsi yesil
```

Kirmizi yanmiyorsa test duzeltmeyi degil baska bir seyi olcuyor.

## Vaka 1'in karsiligi: cue yapisi

Ayni merdiven, metin tarafinda. Denetim cue *baslangicini* olcuyordu; eksik eksen
**sure ve cumle sayisi**. Gommeden once kosulacak kontrol:

```python
import re
def sn(x):
    h, m, kalan = x.split(":"); s, ms = kalan.split(",")
    return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000

for blok in open("/tmp/altyazi.srt", encoding="utf-8").read().strip().split("\n\n"):
    sat = blok.strip().split("\n")
    if len(sat) < 3:
        continue
    a, b = sat[1].split(" --> ")
    sure = sn(b) - sn(a)
    metin = " ".join(sat[2:])
    cumle = len([c for c in re.split(r"[.!?]+", metin) if c.strip()])
    if sure > 2.5 or cumle > 1:
        print(f"cue {sat[0]}: {sure:.1f}sn, {cumle} cumle -> BOL")
```

Cikti bossa yapi dogru. Olculen fark: 6 cue / 67 sn (bir cue 6 saniye boyunca uc
cumle gosteriyordu) -> 18 cue, her biri tek cumle ve 2,5 saniye alti.
