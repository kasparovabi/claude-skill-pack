---
name: pdf-columnar-extraction
description: "Use when extracting tables from a PDF. fitz bbox parsing by x coordinate."
version: 1.0.0
author: Hermes Agent
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [PDF, Tables, fitz, pymupdf, Extraction, Columnar, Government, YKS, ÖSYM]
    related_skills: [ocr-and-documents, pdf, xlsx]
---

# PDF Columnar / Positional Table Extraction

Use when a PDF contains tabular data (government kılavuzları, financial tables, exam score sheets, regulations) and `page.get_text()` returns garbled output because text is positionally encoded, not semantically tagged.

**Trigger conditions:**
- Government/official document with fixed-width columns (YKS, KPSS, vergi, trafik tabloları)
- `get_text()` merges columns or drops values
- Columns must be identified by X-coordinate range, not reading order
- You need to filter rows by column value (e.g. only EA puan type, only rows with quota > 0)

**Required:** `pip install pymupdf`

**Ready-to-run:** `scripts/yks_kilavuz_parse.py` is the verified ÖSYM YKS parser
(detects page ranges, guards column magnitude, clears the institution buffer, and
`--verify` prints the QA checks). Start there for any YKS kılavuzu instead of
rebuilding the parser; adapt its `COORD` dict for other columnar documents.

**Copy the PDF out of `/tmp` first.** Files delivered into `/tmp` by a chat
integration get cleaned up mid-session — a 793-page PDF vanished three times here,
each time after a parser script had already been written against its path. First
command after receiving the file:

```bash
cp /tmp/<incoming>.pdf ~/<meaningful_name>.pdf
```

Then point every script at the stable copy. A parse script that silently produces
an empty log is usually this, not a code bug — stat the input before debugging logic.

---

## Core Pattern

### Step 0 — Detect real table page ranges (NEVER guess)

Guessing "table 1 is pages 22-180, table 2 is 181-end" is the single most expensive
mistake in this workflow. It silently parses appendices, condition lists and fee
tables as if they were data rows, and the row count balloons with plausible-looking
garbage that survives every sanity check you'd think to run.

```python
import fitz
doc = fitz.open(path)

t3, t4 = [], []
for i in range(doc.page_count):
    head = doc[i].get_text()[:300]          # header band only, not whole page
    if "TABLO-3" in head: t3.append(i + 1)
    if "TABLO-4" in head: t4.append(i + 1)

print("TABLO-3:", t3[0], "-", t3[-1])
print("TABLO-4:", t4[0], "-", t4[-1])
```

Then spot-check what lies past the last data page, so you know where the tables
genuinely end:

```python
for i in [t4[-1], t4[-1] + 20, t4[-1] + 100, doc.page_count - 5]:
    print(f"s{i+1}:", doc[i].get_text()[:160].replace("\n", " | "))
```

Only feed the confirmed ranges into the parser. Use `range(first-1, last)`.

### Step 0b — Verify columns visually before trusting any X range

Header text alone is ambiguous: adjacent columns overlap in X, and a "34 yaş" label
can sit above a different column than the one its values occupy. Crop the header
strip and one known data row to PNG, then read them with vision.

```python
p = doc[23]                                     # a data page
p.get_pixmap(matrix=fitz.Matrix(6, 6),
             clip=fitz.Rect(180, 25, 545, 70)).save("/tmp/hdr.png")   # header band
p.get_pixmap(matrix=fitz.Matrix(6, 6),
             clip=fitz.Rect(0, 705, 545, 730)).save("/tmp/row.png")   # data rows
```

Then `vision_analyze` each: ask for the column headers left-to-right *with their
parenthesised numbers*, and separately ask which cell each value in the data row
falls under. This is what catches an off-by-one-column read — the failure mode that
looks completely correct in text output.

### Step 1 — Discover column X positions from header page

```python
import fitz, re

doc = fitz.open("document.pdf")
page = doc[0]   # page that has column headers

blocks = page.get_text("dict")["blocks"]
rows_by_y = {}
for block in blocks:
    if block.get("type") == 0:
        for line in block["lines"]:
            for span in line["spans"]:
                text = span["text"].strip()
                if text:
                    y_key = round(span["bbox"][1])     # top-Y → row bucket
                    x     = round(span["bbox"][0], 1)  # left-X → column id
                    rows_by_y.setdefault(y_key, []).append((x, text))

# Print header rows (first ~80 pts of page height)
for y, items in sorted(rows_by_y.items()):
    if y < 80:
        print(f"y={y}: {sorted(items)}")
```

This tells you which X range maps to which column. X ranges are stable across all pages in the same table.

### Step 2 — Scan all pages, extract by X range

```python
results = []
current_section = ""
current_table   = ""

for page_num in range(doc.page_count):
    page     = doc[page_num]
    text_raw = page.get_text()

    # Detect table type
    if "TABLO-3." in text_raw and "Ön Lisans" in text_raw:
        current_table = "TABLO-3"
    elif "TABLO-4." in text_raw and "Lisans Programları" in text_raw:
        current_table = "TABLO-4"

    # Stop at end-of-table sentinel
    if "1. KISIM KOŞULLAR" in text_raw:
        break

    # Build rows_by_y for this page
    blocks    = page.get_text("dict")["blocks"]
    rows_by_y = {}
    for block in blocks:
        if block.get("type") == 0:
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if text:
                        y_key = round(span["bbox"][1])
                        x     = round(span["bbox"][0], 1)
                        rows_by_y.setdefault(y_key, []).append((x, text))

    for y, items in sorted(rows_by_y.items()):
        items_sorted = sorted(items, key=lambda i: i[0])

        # Track section header — reprinted on every page in YKS-style docs
        for x, t in items:
            if 45 <= x <= 65 and "ÜNİVERSİTESİ" in t:
                current_section = t

        # Row anchor: 9-digit code at x~14
        row_code = next(
            (t for x, t in items if 13 <= x <= 22 and re.match(r"^\d{9}$", t)),
            None
        )
        if not row_code:
            continue

        # Extract columns by X range (adjust ranges per document from Step 1)
        name    = next((t for x, t in items_sorted
                        if 45 <= x <= 75 and len(t) > 2
                        and not re.match(r"^[\d,\s.]+$", t)), "")
        puan    = next((t for x, t in items
                        if 210 <= x <= 250
                        and t in ["EA", "TYT", "SAY", "SÖZ", "DİL"]), "")
        quota   = next((t for x, t in items
                        if 228 <= x <= 270 and re.match(r"^\d+$", t)), "")
        special = next((t for x, t in items
                        if 310 <= x <= 355 and re.match(r"^\d+$", t)), "")
        # Condition codes — exclude adjacent stat numbers (large int or decimal)
        conds   = [t for x, t in items
                   if 348 <= x <= 396
                   and not re.match(r"^\d{6,}$", t)
                   and not re.match(r"^\d+\.\d+$", t)]
        min_p   = next((t for x, t in items
                        if 428 <= x <= 448 and re.match(r"^\d+\.\d+$", t)), "")

        if not special:
            continue   # skip rows without the special quota column

        results.append(dict(
            table=current_table, uni=current_section,
            code=row_code, name=name, puan=puan,
            genel_kont=quota, spec_col=special,
            conditions=", ".join(conds), min_puan=min_p
        ))

print(f"Extracted {len(results)} rows")
```

### Step 3 — Filter by eligibility

```python
eligible_certain = [r for r in results
                    if r["min_puan"] and float(r["min_puan"]) <= 226.0]
eligible_new     = [r for r in results if not r["min_puan"]]  # new/unfilled

# IMPORTANT: Special kontenjanlar (34 yas ustu kadin, sehit/gazi) often have
# LOWER thresholds than the genel kontenjan printed in the table.
# Always include new/unfilled programs as a separate "potential" tier.
```

---

## Pitfalls

| Pitfall | Fix |
|---------|-----|
| Spans on same visual row differ by ±2–3 pt in Y | `round(bbox[1])` collapses them. Still splitting? Use `round(bbox[1] / 2) * 2`. |
| Section header only captured once; later pages lose it | Never reset `current_section` at top of page loop — persists intentionally. |
| Stat columns pollute condition-code column | Exclude `re.match(r"^\d{6,}$")` and `re.match(r"^\d+\.\d+$")`. |
| KKTC / foreign rows omit special quota column | `next(..., "")` → `""` → `if not special: continue`. |
| End-of-table sentinel on page that still mentions "TABLO-4" in header | Check sentinel first (before table-type detector). |
| Filtering by 2025 taban underestimates eligibility for special kontenjanlar | Special kontenjanlar use separate (often lower) thresholds. Include `min_puan == ""` as tier 2. |
| **Guessed page ranges parsed appendices as data** — row count balloons (7,000+ rows) with values that look plausible | Do Step 0. Detect ranges from `TABLO-n` in the header band, then verify what sits past the last page. |
| **Reading the wrong column but getting numbers anyway** — özel koşul codes (x≈448 in Tablo-3) sit near the başarı sırası column, so a slightly-off range returns real integers and nothing looks broken | Do Step 0b: crop header + data row to PNG and confirm with vision. Two adjacent candidate columns both ~47-49% populated across the document is the tell that you're guessing. |
| Same visual row split across buckets when spans differ in Y | `round(y0 / 1.4) * 1.4` grouped YKS rows correctly; `round(y0)` and `/2*2` both split some rows. Tune the divisor and re-check row counts. |
| Multi-word program names truncated to first token | Join every word in the name X range: `" ".join(t for x, t in row if AD_MIN <= x <= AD_MAX)`. Taking `next(...)` gives you "Deniz" instead of "Deniz Ulaştırma ve İşletme". |
| **Institution name bleeds across rows** — a program gets attributed to the previous or next university (e.g. Elazığ OSB's programs labelled Galatasaray) | Institution names span 2+ lines and reprint per page. Buffer uppercase left-column lines, flush the buffer into `uni` only when the line carries `(Devlet` / `(Vakıf` / `(KKTC`, and **clear the buffer the moment a program row is seen**. Without that clear, leftovers concatenate into the next name. |
| Attribution silently wrong even after the buffer fix | Verify: pick 2–3 extracted codes, `grep` them back to their page, print the ~14 lines above each, and confirm the nearest preceding institution line matches what you assigned. Row-level column values being right does not mean the row is attached to the right parent. |
| A sub-campus in another city inherits the parent's city | Program names carry the city in parentheses (e.g. `Anestezi (Ankara)` under an İstanbul-headquartered university). When filtering by city, split these out and label them, don't drop them silently. |
| **Keyword filter returns 0 rows on data you can see in the raw dump** | `.upper()` mangles Turkish `i`/`İ` — see "Türkçe metinde eşleme" below. Match against the raw string, never a case-folded one. Burned three scan runs this session before it was spotted. |
| **Long program names overflow the name X range**, so a filter reading only that range misses the row | Match the keyword against the **whole row text**, then recover the name with a regex anchored on the bracketing columns: `re.match(r"^\d{9}\s+(.+?)\s+2\s+TYT\b", full)`. `(Açıköğretim)` / `(Uzaktan Öğretim)` suffixes routinely push a name past `admax`. |

---

## Alan/meslek adı bazlı filtreleme — geniş tara, dağılımı gör, SONRA daralt

\"Şu alanla ilgili tüm programları çıkar\" istendiğinde anahtar kelime listesini
baştan doğru kurmaya çalışmak boşa efor. Program adları kılavuzda beklenmedik
şekilde çeşitlenir (aynı alan \"Kuyumculuk ve Takı Tasarımı\", \"Kuyumculuk ve
Mücevher Tasarımı\", \"Takı Tasarımı ve İmalatı\" olarak geçer) ve geniş bir anahtar
alakasız kütle çeker.

Doğru sıra:

```python
# 1) GENİŞ tara — komşu/olası tüm terimleri koy
KEY = (\"KUYUMCULUK\", \"TAKI TASARIM\", \"MÜCEVHER\", \"DEĞERLİ TAŞ\",
       \"METAL İŞLERİ\", \"EL SANATLARI\")

# 2) Program adı dağılımını YAZDIR — kararı buradan ver
import collections
for ad, n in collections.Counter(r[\"ad\"] for r in allr).most_common():
    print(f\"{n:3d}  {ad}\")
```

Çıktı bu oturumda şöyleydi: 32 satır \"Geleneksel El Sanatları\", 16 \"Kuyumculuk ve
Takı Tasarımı\", 3 \"Kuyumculuk ve Mücevher Tasarımı\", 1 \"Takı Tasarımı ve İmalatı\".
\"El Sanatları\" alanla ilgisizdi ve sonucun yarısından fazlasını oluşturuyordu.

```python
# 3) DARALT ve nedenini belgede belirt
KEEP = ("KUYUMCULUK", "TAKI TASARIM", "MÜCEVHER")
sel = [r for r in allr if any(k in r["ad"].upper() for k in KEEP)]
```

Bu `.upper()` yalnızca ASCII anahtar sözcüklerde güvenli. Anahtarda `i`/`İ` geçiyorsa
bir sonraki bölümü oku — sessizce 0 satır döner.

Teslim ederken hangi yakın programların **neden** dışarıda bırakıldığını yaz
(\"Geleneksel El Sanatları gibi doğrudan ilgisi olmayan programlar alınmadı\").
Kullanıcı kapsamı sorgulayacağı için kararı görünür kıl.

**Aynı program adı birden çok satırda** çıkabilir: `(Burslu)`, `(%50 İndirimli)`,
`(KKTC Uyruklu)`, `(Uzaktan Öğretim)`, `(M.T.O.K.)` varyantları ayrı kayıtlardır.
Bunları silme — vakıf üniversitesinde burslu/ücretli ayrımı kullanıcı için asıl
karar bilgisidir. Tabloda ayrı bir \"öğrenim türü\" kolonuna çıkar, program adından
parantezi temizle.

## Türkçe metinde eşleme — `.upper()` filtreyi SESSİZCE sıfırlar

Bu oturumda en pahalı hata buydu. Ham dökümde gözle görülen satırlar, filtre
"0 program" dedi ve hata hiçbir yerde patlamadı:

```python
full = "101490817 Bilgisayar Programcılığı (Açıköğretim) 2 TYT 3500 88 ..."
"AÇIKÖĞRETİM" in full.upper()   # False  ← sessiz kayıp
"Açıköğretim" in full           # True   ← doğru
```

Sebep: Python `"Açıköğretim".upper()` çağrısını `"AÇIKÖĞRETIM"` yapar — sondaki
harf noktalı `İ` değil, noktasız `I` olur. Aynı tuzak `ı`/`I` çiftinde de var.
`.lower()` ters yönde aynı hasarı verir.

Kural: **eşleme her zaman ham metin üzerinde yapılır.**

```python
# YANLIŞ — Türkçe anahtar + case-fold
if "AÇIKÖĞRETİM" in full.upper(): ...

# DOĞRU — ham metinde, kılavuzdaki yazımıyla
if "Açıköğretim" in full:        mod = "Açıköğretim"
elif "Uzaktan Öğretim" in full:  mod = "Uzaktan Öğretim"
```

Büyük/küçük harf duyarsızlığı gerçekten şartsa Türkçe-farkında ön değişim yap
(`İ→i`, `I→ı`) ya da her iki yazımı da listeye koy. Görüntüleme tarafındaki
`.title()` bozulması için `reportlab-turkish-pdf` skill'ine bak — aynı kök neden.

**Teşhis refleksi:** bir filtre 0 satır döndüğünde önce anahtar sözcüğü tek satırda
`repr()` ile bas ve `in` testini hem ham hem case-fold halinde çalıştır. Parser
mantığını debug etmeden önce bunu ele.

## Öğretim türü (açıköğretim / uzaktan) kontenjan dağılımı ayrıdır

Aynı "34 yaş" sütunu, öğretim türüne göre tamamen farklı davranır — birinde boş
çıkması bug değil, bulgudur:

- **Açıköğretim:** 34 yaş kontenjanı açan tek kurum **Anadolu Üniversitesi** (29
  program). İstanbul Üniversitesi Açık ve Uzaktan Eğitim Fakültesi ile Atatürk
  Üniversitesi Açıköğretim Fakültesi programları kılavuzda var ama sütun her
  satırda boş.
- **Uzaktan öğretim:** 24 program, **hepsi devlet üniversitesi**. Vakıf
  üniversitelerinin uzaktan programlarında bu kontenjan hiç açılmamış.

Açıköğretim satırlarında x≈448'de görülen `13` değeri 34 yaş kontenjanı DEĞİL,
özel koşul kodudur — Tablo-3'ün klasik tuzağı (bkz. Step 0b).

Kurum adı çıkarımı bu formatta en kırılgan parçadır (çok satırlı adlar, sayfa başı
tekrarları, tampon sızması). Sonuç kümesi küçükse (≲50 satır) parser'ı daha fazla
uğraştırmak yerine kod→bilgi sözlüğü yaz:

```python
INFO = {   # kod: (üniversite, şehir, birim, öğrenim türü)
    \"100490225\": (\"Afyon Kocatepe Ü.\", \"Afyonkarahisar\", \"İscehisar MYO\", \"Devlet\"),
    \"103150468\": (\"Dokuz Eylül Ü.\", \"İzmir\", \"İzmir MYO\", \"Devlet\"),
    \"202450546\": (\"İstanbul Aydın Ü.\", \"İstanbul\", \"Anadolu BİL MYO\", \"Burslu\"),
}
```

Üç kazanç: (a) parser'ın yanlış kuruma bağladığı satırlar elde düzeltilir,
(b) **şehir** gibi PDF'te hiç yer almayan alan eklenir — kullanıcı \"Türkiye geneli\"
liste isteyince şehir kolonu listeyi kullanılabilir kılar, (c) `.title()` gibi
Türkçe-bozan dönüşümlere hiç gerek kalmaz (bkz. `reportlab-turkish-pdf`).

Sözlüğü doldurmadan önce her kodu kılavuza geri izle (kodun sayfasını bul, üstündeki
~14 satırı yazdır, en yakın kurum satırını gör). Bu oturumda bu kontrol Mersin
Üniversitesi'ne ait bir lisans programının yanlış kuruma bağlandığını yakaladı.
Büyük kümelerde (binlerce satır) bu yol ölçeklenmez — orada parser'ı düzelt ve
örneklem doğrulaması yap.

---

A positional parser fails *quietly*. Wrong X range still returns integers; wrong page
range still returns rows; wrong parent attribution still returns a plausible
university name. Row counts and clean output prove nothing. In this session a
7,000-row spreadsheet was delivered and only a user asking "is this 100% correct?"
surfaced two real bugs. Run these checks yourself, before you hand anything over:

1. **Page ranges detected, not assumed** — Step 0 ran, and you looked at what sits
   past the last data page.
2. **Columns confirmed visually** — Step 0b ran; header band and one data row were
   read with vision, not just inferred from text X positions.
3. **Value sanity per column** — a quota column should hold small integers (1–100).
   Seeing 320, 1286405 or a decimal there means you're reading özel koşul codes,
   başarı sırası, or taban puan. Assert the expected magnitude explicitly.
4. **Two candidate columns both plausible = unresolved** — if two X ranges are each
   populated on roughly half the rows, you have not identified the column yet.
5. **Parent attribution spot-checked** — trace 2–3 extracted codes back to their page
   and confirm the preceding institution line. Prefer codes from *different* pages,
   including one right after a page break.
6. **Zero rows for a whole institution is a finding, not a bug** — check whether the
   column is genuinely empty there before rewriting the parser.

When something turns out wrong, say plainly what was wrong and what the corrected
figure is. Don't restate a number as verified when only its formatting was checked.

## Adayın puan türünü BELGEDEN doğrula — hangi tabloya bakacağını o belirler

Kullanıcı "226 puan" dediğinde hangi puan türü olduğunu varsayma. Bu oturumda
226 sayısı Y-EA sanıldı ve buna göre lisans (Tablo-4) programları listelendi;
sonuç belgesi gelince puanın **Y-TYT** olduğu ve adayın AYT'ye hiç girmediği
görüldü — yani lisans programlarına başvuru hakkı yoktu, üretilen listenin
lisans yarısı baştan geçersizdi.

Sonuç belgesinde okunacak yer: **"Yerleştirme Puanları ve Başarı Sıraları"**
tablosu. Y-TYT / Y-SAY / Y-SÖZ / Y-EA / Y-DİL satırlarından hangileri dolu?

- Yalnızca **Y-TYT** doluysa → aday AYT'ye girmemiştir. Sadece **2 yıllık
  önlisans** (Tablo-3) tercih edebilir. Lisans programı önerme.
- SAY/SÖZ/EA/DİL satırları da doluysa → Tablo-4 de devrededir.

Ayrıca ham TYT puanı ile Y-TYT farklıdır (OBP katkısı): belgede TYT 185,50 iken
Y-TYT 226,38 çıkabilir. **Karşılaştırmayı her zaman Y- ile başlayan yerleştirme
puanı üzerinden yap**, ham sınav puanı üzerinden değil.

Belge gelmeden bu bilgi netleşmiyorsa listeyi üretmeden önce sor. Yanlış puan
türü, tüm çıktıyı sessizce geçersiz kılar.

## Reporting derived eligibility honestly

Special-quota pools (34 yaş üstü kadın, şehit/gazi) do **not** publish their own taban
puan — the printed taban belongs to the genel kontenjan. So a candidate's score cannot
be compared against it directly.

State the limit rather than implying a threshold: the printed taban is genel-kontenjan
data, the special pool's threshold is typically lower because far fewer candidates
compete in it, and the exact figure isn't derivable from the kılavuz. Then give the
actionable signal instead — rows with an **empty** 2025 taban/sıra didn't fill last
year, and those are where a low score realistically places. Surface those first.

When the local file path doesn't exist (Pyto-initiated sessions):

1. Browse `https://www.osym.gov.tr`
2. Navigate to "Yakındakiler → YKS → Kılavuz" and click the PDF link
3. `browser_console(expression="document.URL")` captures the actual PDF URL from the iframe
4. `curl -L -o /tmp/kilavuz.pdf "<url>"` downloads it

ÖSYM pattern: `https://dokuman.osym.gov.tr/web//<YEAR>/<MONTH>/<slug>.pdf`

**2026 YKS kılavuzu (775 pages, ~10 MB):**
`https://dokuman.osym.gov.tr/web//2026/7/2026-yuksekogretim-kurumlari-sinavi-yks-yuksekogretim-programlari-ve-kontenjanlari-kilavuzu-2996nz6m.pdf`

---

## 2026 YKS Kılavuzu — VERIFIED Column X Ranges

Values below were confirmed by cropping the header strip AND a data row out of the
PDF and reading them with vision (see "Verify columns visually"). Earlier guessed
ranges in this skill were wrong and produced a 7,000-row garbage list — trust these.

**Page ranges — do NOT guess these, detect them (see Step 0):**
- Tablo-3 (Ön Lisans): pages **23–147**
- Tablo-4 (Lisans): pages **151–549**
- Pages **550+ are NOT program tables** — koşul açıklamaları, Tablo-5 meslek lisesi
  listesi, ücret tabloları, üniversite web adresleri. Parsing them inflates results.

**Tablo-3 (Ön Lisans, pages 23–147)** — header numbering: (5) genel, (6) ok.bir,
(7) şehit/gazi, (8) 34 yaş, (9) özel koşul, (10) başarı sırası, (11) en küçük puan:
- Program kodu: x < 30 (values land x≈15)
- Program adı: x 40–205 — **multi-word, must be joined, see pitfalls**
- Öğr. süre: x≈216
- Puan türü: x 228–252 (values x≈237)
- Genel kontenjan: x 253–280 (values x≈264)
- Ok.bir. kont.: x≈292
- **34 Yaş Üstü Kadın kont. (col 8): x 332–366 — values land x≈350**
- Özel koşul (col 9): x 407–451 — **values land x≈444–451, this is the trap**
- 2025 başarı sırası: x 455–492 (values x≈470–473)
- 2025 en küçük puan: x 493–532 (values x≈503)

**Tablo-4 (Lisans, pages 151–549)** — note the column numbering SHIFTS by one:
(7) meb, (8) şehit/gazi, (9) 34 yaş:
- Program kodu: x < 45 (values x≈15)
- Program adı: x 48–192 — multi-word, join
- Öğr. süre: x≈197
- Puan türü: x 204–226 (values x≈211–213)
- Genel kontenjan: x 227–250 (values x≈234)
- Ok.bir. kont.: x≈257
- Şehit/gazi kont. (col 8): x 287–304
- **34 Yaş Üstü Kadın kont. (col 9): x 316–346 — values land x≈329**
- Özel koşul codes: x 350–385
- 2025 başarı sırası: x 392–424 (values x≈399–403)
- 2025 en küçük puan: x 426–462 (values x≈432)

**Domain fact worth keeping:** the 34 yaş üstü kadın kontenjanı exists **only at
state universities**. Every İstanbul vakıf üniversitesi (Beykoz 78 programs,
İstanbul Aydın 80, Gelişim 81, Maltepe 80, Üsküdar 83) has that column empty on
every row. Don't report "parser failed" when a vakıf page yields zero rows.

Also: not every state university opts in. İstanbul Üniversitesi (19 önlisans
programs), Cerrahpaşa (50), Marmara (28) and İTÜ (1) all reserved zero.
