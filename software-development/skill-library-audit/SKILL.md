---
name: skill-library-audit
description: "Use when skills don't trigger or the index needs audit."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [skills, audit, discoverability, linting, skill-md]
    related_skills: [hermes-agent-skill-authoring]
---

# Skill kütüphanesini denetlemek

## Overview

Tek bir skill yazmak değil, **var olan kütüphanenin tamamını** keşfedilebilirlik
açısından ölçmek ve düzeltmek. Tetikleyici durumlar:

- Kullanıcı *"skiller tetiklenmiyor"*, *"açıklamalar kesiliyor"* diyor
- *"Skilleri tek seferde yüklemek yerine linklerini tutsak"* türü mimari öneri
- Yeni skill eklendi ve indeksin şiştiği hissediliyor

Tek bir SKILL.md yazımı/frontmatter kuralları için `hermes-agent-skill-authoring`
skill'ine bak; bu skill onun **toplu denetim** tarafıdır.

## When to Use

- 50+ skill'lik bir kütüphanede kalite taraması
- Bir skill'in "neden hiç yüklenmiyor" teşhisi
- Kullanıcı indeks/bağlam maliyetini sorguluyor

**Kullanma:** tek bir skill yazarken ya da tek bir açıklamayı düzeltirken.

## Kendi denetçini yazma — bunlar var

Bu problem çözülmüş. Üçü de `SKILL.md` doğrulayıp **açıklama
keşfedilebilirliğini puanlıyor** (9 Ağu 2026 itibarıyla):

| Repo | Yıldız | Dil | Not |
|---|---|---|---|
| `agent-sh/agnix` | 377 | Rust | En aktif. CLAUDE.md / AGENTS.md / SKILL.md / hooks / MCP doğrular, IDE eklentisi var |
| `moonrunnerkc/skillcheck` | 22 | Python | agentskills.io şartnamesine göre kapı. Açıklamayı 0-100 puanlar |
| `ryanda9910/friskeval` | 3 | JS | Sıfır bağımlılık; açıklama çakışması ve kapsam şişirmesi arar |

agnix'in tanıtımındaki gerekçe sorunun sektörel olduğunu gösteriyor:
*"Your skills don't trigger."* — Vercel'in araştırmasına atıf veriyor.

```bash
git clone --depth 1 https://github.com/moonrunnerkc/skillcheck.git
cd skillcheck && pip install -q -e .
cd ~/.hermes/skills && skillcheck . --min-desc-score 60
```

**Üçüncü taraf kodu kurmadan önce tara** (bu vakada temiz çıktı: tek bağımlılık
`pyyaml`, ağ çağrısı yok, subprocess yok):

```bash
grep -rnE "subprocess|os\.system|eval\(|exec\(|requests\.|urllib|socket" --include=*.py .
grep -A5 "^dependencies" pyproject.toml
```

## Ölçülmüş temel durum (bu kütüphane, 9 Ağu 2026)

```
130 dosya: 33 geçti, 97 kaldı, 573 uyarı
```

Tekrarlayan bulgular: açıklamada eylem fiili yok · tetikleyici bağlam yok ·
açıklama 200+ karakter · kırık `references/` bağlantısı · gövde 500 satır
sınırını aşıyor · frontmatter ~100 token bütçesini aşıyor.

Somut: `motion-tetikleyici` 43/100 — açıklama 810 karakter, eylem fiili yok,
tetikleyici ifade yok.

## Gerçek hata: `description: >` Cursor'da BOŞ görünüyor

skillcheck'in yakaladığı, gözle görülmeyen kusur:

> description uses block scalar `>` which Cursor's skills UI renders as empty.
> Use `>-` (folded strip) instead.

Çok satırlı açıklamada `>-` ya da `|-` kullan. Bu kütüphanede etkilenenler:
`macos-computer-use`, `computer-use` (`|`) · `windows-remote-over-tailscale`,
`ponytail`, `motion-tetikleyici`, `skill-pack-install`, `mythos-scaffold` (`>`).

## Aşamalı açığa çıkarma zaten çalışıyor — önce ÖLÇ

Kullanıcı *"skilleri tek seferde yüklemek yerine linklerini tutup ihtiyaç
anında okusak"* diye önerdiğinde: bu zaten mevcut mimari. Ölçüm:

| | Karakter |
|---|---|
| 131 skill gövdesi toplamı | 1.844.241 |
| Konuşmaya yüklenen indeks (ad + kırpılmış açıklama) | ~9.800 |
| Oran | **188 kat** |

Gövdeler yüklenmiyor, `skill_view` ile ihtiyaç anında okunuyor. Mimari doğru;
sorun **indeksin kalitesinde**: 131 açıklamanın yalnızca 21'i 57 karakterlik
pencerede tetikleyici taşıyor, 30'u 200 karakteri aşıyor.

**Kullanıcı var olan bir mimariyi öneriyorsa önce ölç ve durumu göster**,
sıfırdan kurmaya girişme. Aynı refleks GitHub paylaşımı için de geçerli: yeni
repo açmadan önce `gh api search/repositories` ile ara — bu vakada üç olgun
proje çıktı ve yeni repo gereksizdi.

## Ölçüm tuzağı: kendi tarayıcım yanlış rapor üretti

Denetimden önce kendi regex'imle taradım ve kullanıcıya **"7 skill'in açıklaması
bozuk"** dedim. Yanlıştı.

```python
# HATALI — sadece ilk satırı okur
m = re.search(r"^description:\s*(.+)$", t, re.M)
# 'description: |' satırında yakaladığı şey: '|'
```

O skiller YAML'ın çok satırlı blok yazımını kullanıyordu; açıklamaları sağlamdı.
**Araç bozuk değildi, ölçüm aracım bozuktu.** Frontmatter okuyacaksan satır
regex'i değil `yaml.safe_load` kullan:

```python
import yaml, re
gövde = open(yol, encoding="utf-8").read()
m = re.search(r"\n---\s*\n", gövde[3:])
fm = yaml.safe_load(gövde[3:m.start() + 3])
ac = (fm.get("description") or "").strip()
```

Bir ölçüm şaşırtıcı sonuç veriyorsa **bulguyu duyurmadan önce ölçeni doğrula.**

## Düzeltme kalıbı

Açıklamayı `Use when <tetikleyici>. <tek satır davranış>.` biçimine sok; uzun
anlatımı gövdeye taşı. Sistem promptu 57 karakterde kestiği için tetikleyici o
pencerede tamamlanmalı.

| Kötü | İyi |
|---|---|
| `Bu skill ... için ayrıntılı rehber içerir` | `Use when skills don't trigger.` |
| 810 karakterlik tetikleyici ifade listesi | Tek satır tetikleyici + gövdede liste |

**Yeni skill oluştururken sınır 60 karakter, 57 değil.** `skill_manage` 60'ı
aşan açıklamayı doğrudan reddeder (bu skill ilk denemede 64 karakterle
reddedildi). Kayıtlı skilleri düzeltirken hedef yine 57 karakterlik görünür
pencere.

Öncelik sırası: (1) hiç tetikleyicisi olmayan 110 skill, (2) 200+ karakterlik
30 açıklama, (3) blok skalar `>` kullanan 7 skill, (4) kırık referans bağlantısı.

## Toplu onarım — yedekle, kuru koş, uygula, yeniden ölç

Teşhis yarısı yukarıda. Bu bölüm **fiilen düzeltme** tarafı; 68 dosyada
doğrulandı (9 Ağu 2026).

Onarım tablosunu koda göm (`{yol parçası: yeni açıklama}`) ve yalnız
frontmatter'daki `description` alanını değiştir — gövdeye dokunma:

```python
def aciklama_degistir(metin, yeni):
    if not metin.startswith("---"):
        return None, "frontmatter yok"
    son = metin.find("\n---", 3)
    if son == -1:
        return None, "frontmatter kapanmamis"
    bas, bit = 3, son + 1
    fm = metin[bas:bit]
    # blok skalari da kapsayan devam satiri deseni
    m = re.search(r"^description:.*(?:\n(?:[ \t]+\S.*|[ \t]*))*", fm, re.M)
    if not m:
        return None, "description yok"
    kacisli = yeni.replace('"', "'")
    yeni_fm = fm[:m.start()] + f'description: "{kacisli}"\n' + fm[m.end():].lstrip("\n")
    return metin[:bas] + yeni_fm + metin[bit:], None
```

Betiği **kuru koşum varsayılan** yaz, `--uygula` ile yazsın. Kuru koşumda her
satırın ilk 57 karakterini bas ki tetikleyicinin pencerede bittiği gözle görülsün.

Hazır ve çalıştırılabilir hâli pakette: `scripts/skill_aciklama_duzelt.py`
— gövde değişirse yazmayı iptal eder, tetikleyicisiz satırları `ZAYIF` işaretler.

```bash
# 1. Yedek — cp -r kirik sembolik baglarda patlar, tar kullan
cd ~/.hermes && tar czf /tmp/skills_yedek.tgz --exclude='*/node_modules' skills/
tar tzf /tmp/skills_yedek.tgz | grep -c "SKILL.md"     # sayiyi dogrula

# 2. Kuru kosum → 3. Uygula → 4. Yeniden olc
SC=~/.hermes/skills/software-development/skill-library-audit/scripts/skill_aciklama_duzelt.py
python3 "$SC" --tablo /tmp/tablo.json
python3 "$SC" --tablo /tmp/tablo.json --uygula
cd ~/.hermes/skills && skillcheck . --format json > /tmp/sonra.json
```

### Raporlanacak üç sayı

"Açıklamaları iyileştirdim" sonuç değildir. Ölçülmüş geçiş (131 skill, 68 düzeltildi):

| Ölçüt | Önce | Sonra |
|---|---|---|
| Tetikleyicisi yok | 94 | 31 |
| 60 puan altı | 48 | 2 |
| Ortalama puan | 64,3 | 75,6 |

Puanı JSON'dan çek (`breakdown.trigger` alanı tetikleyici puanını verir):

```python
for r in json.load(open(y))["results"]:
    for f in r["diagnostics"]:
        if f["rule"] == "description.quality-score":
            puan = int(re.search(r"score:\s*(\d+)/100", f["message"]).group(1))
            tetik = f.get("breakdown", {}).get("trigger", 0)
            break
```

### Metrik artefaktını kovalama

`skillcheck` tetikleyici olarak yalnız **`Use when`** kalıbını sayıyor.
`Use whenever` ve `Use for` geçerli olmalarına rağmen sıfır puan alıyor — geçiş
sonrası kalan 31'in belirgin kısmı aslında düzgündü.

Doğru olan, açıklamayı linteri memnun etmek için bozmak değil, farkı kullanıcıya
söylemektir: *"gerçek durum ölçünün gösterdiğinden iyi, araç tek kalıbı tanıyor."*
Aynısı `references.broken-link` için de geçerli: `@babel/preset-env` gibi paket
adlarını araç kırık dosya bağlantısı sanıyor. Uyarıyı sıfırlamak hedef değil.

## SIKIŞTIRMA ÖNERİLERİ: dördü de ölçüldü, dördü de elendi

Kullanıcı er ya da geç soruyor: *"açıklamaları ikili kodla / başka dille / mağara
mantığıyla yazsak karakter tasarrufu olur mu?"* Cevap ölçüldü (10 Ağu 2026).
**Tahmin etme, bu tabloyu göster.**

| Fikir | Sonuç |
|---|---|
| İkili kod | **9 KAT kötü** — 85 karakter → 764. İkili sıkıştırma değil *açma*dır; her harfi 8 basamağa yayar. İndeks 2.273 → 20.457 token |
| Çince / CJK | Karakterde kazanır (85→42), **tokende %32 kaybeder** |
| Mağara üslubu | %22 tasarruf ama **7 skill çifti karışır** |
| Dolgu temizliği | Kabul edildi, ama **token kazancı SIFIR** (aşağıda) |

Token/karakter oranı, tasarruf sezgisini tersine çeviren asıl veri:

| Dil | Karakter | Token | Karakter/token |
|---|---|---|---|
| İngilizce | 85 | 19 | 4,47 |
| Türkçe | 81 | 25 | 3,24 |
| Çince | 42 | **25** | 1,68 |

CJK ekranda yarı yarıya kısa görünür, faturada pahalıdır — tokenizer onu verimli
paketleyemez. Ayrıca kullanıcı Türkçe istek yazdığında Çince açıklamayla eşleşme
belirsizleşir; yani çözmeye çalıştığın keşfedilebilirlik sorununu geri getirir.

### Mağara üslubunun kırılma noktası

"email terminal read send himalaya imap smtp" biçimi %22 tasarruf ediyor (2.273 →
1.762 token) ama ayrımı öldürüyor: 7 çift birbirine yaklaşıyor (claude-code↔codex,
webgpu'nun iki sürümü, powerpoint↔docx).

Somut kırılma: *"Şu PDF'teki tabloyu çıkar"* dendiğinde mağara üslubunda **üç skill
birden** aday olur, çünkü hepsinde "pdf" geçer. Tam cümlede ayrım net:

```
"extracting tables FROM a pdf"    -> PDF'ten OKUYOR
"producing a turkish pdf report"  -> PDF ÜRETİYOR
```

Silinen küçük kelimeler (`from`, `producing`) **yönü** taşıyor. Üstelik mağara
üslubu `Use when` kalıbını da siler, yani yeni kazanılan puanı geri verir.

### ÖLÇÜLMÜŞ NULL SONUÇ — dolgu temizliği token kazandırmaz

Kabul edilen orta yol ("tetikleyici ve yön kalsın, dolgu gitsin") 68 açıklamada
uygulandı, metinler toplam **819 karakter** kısaldı:

```
indeks token: 2.273  ->  2.277     (KAZANÇ YOK, +4)
puan        : 75,6   ->  75,4      (bozulma da yok)
```

**Sebep: alan zaten 57 karakterde kırpılıyor.** Cümlenin tamamı kısaltıldı ama
kesilen kısım nasılsa hiç yüklenmiyordu — var olmayan bir yük azaltıldı.

> **Kural: kırpılmış bir alanı kısaltarak token kazanamazsın.**
> Kazanç ancak *pencere içindeki bilgi yoğunluğunu* artırırsan gelir.

Sadeleştirmenin gerçek faydası buydu: `"Use when a Turkish PDF report, table or
list is needed"` penceresi `is needed`e varmadan doluyordu; `"Use when producing a
Turkish PDF report or table"` üretmek mi çıkarmak mı olduğunu pencere *içinde*
söylüyor. Çakışan çift de 7'den 6'ya indi.

Bir sıkıştırma önerisi geldiğinde ilk soru: **bu alan zaten kırpılıyor mu?**
Kırpılıyorsa hedef kısaltmak değil, pencereyi daha iyi doldurmaktır.

### Genelleme: kırpılan her alan için aynı hesap

Bu ders skill açıklamalarına özel değil. Sistem promptuna, indekse, özet
alanlarına giren **her kırpılmış metin** için geçerli:

```
tasarruf = f(pencere), gövde uzunluğu DEĞİL
```

Kısaltmadan önce ölç: alan kırpılıyor mu, kırpma sınırı kaç? Sınırın ötesindeki
her karakter zaten bedava. "Uzun görünüyor, kısaltayım" refleksi kırpılmış
alanlarda sıfır kazanç, pozitif risk (yön/tetikleyici kaybı) taşır.

Kullanıcı sıkıştırma önerdiğinde tahmin yerine üç sayıyı bas: mevcut token,
önerilen biçimde token, ayırt edicilik kaybı (çakışan çift sayısı). Bu tablo
tartışmayı bitirir.

## Common Pitfalls

1. **Kendi denetçini yazmak.** Önce `gh api search/repositories` ile ara.
2. **Frontmatter'ı satır regex'iyle okumak.** Blok skalar (`|`, `>`) yanlış
   okunur ve sağlam skilleri "bozuk" gösterir.
3. **Kırpılan açıklamayı gözle kontrol etmek.** 57 karakter penceresini
   programla kes ve tetikleyici var mı diye bak.
4. **Denetim çıktısını düzeltme sanmak.** 97 kalan dosya raporlandı ≠ düzeltildi.
   Neyin fiilen düzeltildiğini ayrı say.
5. **Bundled / user-owned skilleri yamamaya çalışmak.** Yazma reddedilir;
   `hermes curator adopt <name>` gerekir. Denetim raporunda bunları ayrı işaretle.
6. **`cp -r` ile yedek almak.** Skill dizinlerinde kırık sembolik bağlar oluyor;
   `cp` her birinde hata basıp yedeği yarım bırakıyor ve bunu fark etmezsin.
   `tar czf` kullan, sonra `tar tzf | grep -c SKILL.md` ile içeriği doğrula.
7. **Yedeksiz toplu yazma.** Tek koşuda 68 dosyaya dokunuluyor.
8. **Gövdeye dokunmak.** Onarım yalnız `description` alanını değiştirmeli.
   Gövde tek satır bile değişiyorsa fonksiyonun bozuktur — örnek bir dosyada
   `git diff` ya da uzunluk karşılaştırmasıyla doğrula.
9. **Uzun açıklamayı korumaya çalışmak.** 846 karakterlik açıklamanın 789
   karakteri hiçbir zaman görünmüyor; anlatım gövdeye ya da `references/` altına
   taşınır, açıklama kısalır.
10. **Yeni skill oluştururken 60 karakter sınırını unutmak.**
   `skill_manage(action='create')` 60 karakteri aşan açıklamayı **reddeder** —
   bu skill'i yazarken tam bu hataya düşüldü (67 karakter). Hata mesajı nettir:
   *"new skills must fit the 60-char system-prompt budget."* Mevcut skilleri
   düzeltirken hedef 57 karakterlik görünür pencere, yeni oluştururken 60
   karakterlik sert sınır. Oluşturmadan önce `len(aciklama)` bas.
11. **`create` hata döndürdü diye tekrar denemek.** Bu oturumda `create` önce
   açıklama hatası verdi, düzeltilmiş sürüm ise *"already exists"* dedi — ilk
   çağrı aslında yazmıştı. Aynı adı ikinci kez oluşturmaya çalışmadan önce
   `skill_view(name=...)` ile **gerçekten var mı** diye bak; varsa `create`
   değil `patch` kullan.

## Verification Checklist

- [ ] Harici araç kuruldu ve güvenlik taramasından geçti
- [ ] Taban durum sayıyla kaydedildi (geçen/kalan/uyarı) — onarımdan ÖNCE
- [ ] Frontmatter `yaml.safe_load` ile okundu, satır regex'iyle değil
- [ ] 57 karakterlik pencere programla ölçüldü
- [ ] Yedek `tar` ile alındı ve içindeki SKILL.md sayısı doğrulandı
- [ ] Kuru koşum çıktısında her satırın ilk 57 karakteri gözle görüldü
- [ ] Blok skalar `>` kullananlar `>-` ile düzeltildi
- [ ] Düzeltme sonrası araç yeniden koşturuldu ve üç sayı karşılaştırıldı
- [ ] Gövdelerin değişmediği doğrulandı
- [ ] Kalan uyarılardan metrik artefaktı olanlar ayrıştırılarak raporlandı
