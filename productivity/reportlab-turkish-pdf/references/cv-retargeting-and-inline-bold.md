# CV'yi yeniden hedefleme + `<b>` markup tuzağı

11 Ağu 2026 oturumundan. İki ayrı ders: biri reportlab'ın sessiz bir davranışı,
diğeri ilana-özel bir CV'yi genel hedefe çevirme akışı.

---

## 1. `<b>` etiketi SESSİZCE hiçbir şey yapmaz — `registerFontFamily` şart

Gömülü TTF kullanırken `Paragraph` içindeki `<b>`, `<i>`, `<strong>` markup'ı
**hata vermeden yok sayılır**. Metin çıkar, düzen bozulmaz, sadece kalın olması
gereken yer düz kalır. Bu yüzden font sorunu değil, stil sorunu sanılıp yanlış
yerde aranır. Bu oturumda iki tur kaybettirdi.

Sebep: `registerFont` reportlab'a fontun kendisini tanıtır ama "bu fontun kalın
kardeşi hangisi" bilgisini vermez. Markup çözümleyici kalın varyantı bulamayınca
sessizce normal yüzü kullanır.

```python
pdfmetrics.registerFont(TTFont("Body",  ".../Arial.ttf"))
pdfmetrics.registerFont(TTFont("BodyB", ".../Arial Bold.ttf"))

# BU SATIR OLMADAN <b> CALISMAZ
pdfmetrics.registerFontFamily("Body", normal="Body", bold="BodyB",
                              italic="Body", boldItalic="BodyB")
```

Aile adı, stilde kullandığın `fontName` ile **birebir aynı** olmalı
(`ParagraphStyle(fontName="Body")` → `registerFontFamily("Body", ...)`).

Nerede ısırır: paragraf başında kalın bir alt başlık isteyip gövdeyi aynı
`Paragraph` içinde sürdürdüğünde:

```python
ad = next(a for a in ALT_BASLIKLAR if s.startswith(a))
ogeler.append(Paragraph("<b>%s</b>%s" % (ad, s[len(ad):]), st_p))
```

Ayrı satırlık başlıklar `fontName=KALIN` olan kendi stiliyle çizildiği için
çalışır. Sonuç kafa karıştırıcı: "bazı başlıklar kalın, bazıları değil".

Doğrulama gözle olmalı. `get_text()` kalın/düz ayrımını göstermez; sayfayı PNG'e
çevirip `vision_analyze`'a **"alt başlıklar kalın mı"** diye açıkça sor.

### Yan tuzak: bölüm adları iki yerde yaşar

Betik `BOLUMLER` / `ALT_BASLIKLAR` kümeleriyle hangi satırın başlık olduğuna
karar veriyorsa, kaynak metindeki bölüm adını değiştirmek **sessizce** o başlığı
düz paragrafa çevirir. Uyarı yok, sadece hiyerarşi kaybolur. Kaynak metni
yeniden çerçevelerken iki dosyayı birlikte güncelle ve render edip bak.

---

## 2. İlana-özel CV'yi genel hedefe çevirmek

### Belirti: site ile indirilen dosya farklı şey iddia ediyor

Kullanıcının sorusu şuydu: *"sitedeki indirilebilir cv'ler de güncel mi, yani
onlar bir projeye özel yazılmıştı ama şimdi herkese hitap ediyoruz"*. Haklıydı.

- Sayfa başlığı: `AI Automation Engineer · LLM agent systems`
- İndirilen PDF: `AI PLATFORM ENGINEER · AGENT INFRASTRUCTURE, EVALUATION AND GOVERNANCE`

Bir işveren siteyi okuyup CV'yi indirdiğinde **iki farklı konumlandırma**
görüyor. Bu yetkinlik sorunu değil, tutarlılık sorunu, ve güveni doğrudan kırar.

**Kural: portfolyo sitesi ile indirilebilir CV aynı unvanı ve aynı özeti
taşımalı.** Site başlığını değiştirdiğin her seferde CV'yi de kontrol et; bunlar
ayrı dosyalar olduğu için birlikte güncellenmezler.

### Ölçerek teşhis et, okuyarak değil

İlana-özel dil ile genel dilin ağırlığını sayarak göster:

```python
ilan_ozel = ["platform layer", "governance", "evaluation harness",
             "permission boundaries", "run logging", "the pager"]
genel     = ["automation", "workflow", "agent", "Python", "API",
             "integration", "pipeline", "orchestration", "Docker", "AWS"]
for k in ilan_ozel + genel:
    print(k, len(re.findall(re.escape(k), metin, re.I)))
```

Bu oturumda: `governance` 3, `evaluation harness` 3 iken `automation` 1,
`Python` 1, `Docker` 1. Tablo tek bakışta yanlış hedefi gösterdi.

### Genel bir referans ilan yaz, sonra denetle

`ats_denetci.py` bir CV **ve bir ilan** ister. Genel hedef için gerçek bir ilan
yoksa, hedeflenen rolün tipik gereksinimlerinden bir referans ilan yaz
(`/tmp/work/ilan_genel.txt`) ve ona karşı denetle. Yapay değil, temsili olmalı:
sorumluluklar, zorunlu nitelikler, artı nitelikler.

```bash
python3 ~/.hermes/scripts/ats_denetci.py CV.pdf ilan_genel.txt
```

### Eksik terimi UYDURARAK değil, yapılmış işi yazarak kapat

Üç turda %75 → %93 → %100. Kritik nokta: eksik çıkan terimler
(`pipelines`, `automated`, `integration`, `tests`) zaten yapılmış işlerdi,
sadece CV'de yazılmamıştı. Kapatma şekli, o işi anlatan cümleyi genişletmek:

> "...and each runs as a scheduled pipeline with automated checks rather than as
> a script someone remembers to run."

> "Two marketplace API integrations, automated listing state reconciliation, and
> integration tests against recorded responses."

Terimi boşluğa serpiştirmek `[D] DOLDURMA RISKI` kapısına takılır ve kara liste
riski doğurur. Denetçinin dört çıktısını birlikte oku: kapsam yükselirken
doldurma riski temiz kalmalı.

### Kanıt yoğunluğu ayrı bir eksen

`[C] KANIT YOGUNLUGU` "kelimenin arkasında somut sonuç var mı" diye sorar,
yani cümlelerin kaçında sayı geçiyor. Yükseltmenin yolu sıfat değil ölçüm:

- zayıf: "güvenlik araştırması yaptım"
- güçlü: "iki bildirim gönderdim, satıcının düzeltme commit'i raporu adıyla anıyor"

### İki formatı birlikte yenile

PDF ve `.docx` ayrı üretim yollarıdır. Birini güncelleyip diğerini unutmak, iki
farklı CV'nin dolaşıma girmesi demektir. `.docx` tarafında `len(d.tables) == 0`
doğrula (ATS tablo okuyamaz) ve aynı anahtar dizeleri ara.

```python
from docx import Document
d = Document("CV.docx")
t = "\n".join(p.text for p in d.paragraphs)
assert len(d.tables) == 0
for k in ["AI AUTOMATION ENGINEER", "platform layer"]:
    print(k, k in t)      # ikincisi False olmali
```
