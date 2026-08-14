---
name: hands-on-tool-evaluation
description: Use when presenting a public repo you haven't run.
---

# Hands-on tool evaluation

Use when the task is **"find something useful in public repos and present it"** —
tool roundups, "bu hafta denediğim araç" posts, build-vs-buy checks, or any time
you're about to recommend a library you haven't run.

The deliverable is never "here's a repo with a lot of stars." It is **which of
its claims held on my machine, and which didn't.** That distinction is the entire
value; without it you're reposting a README.

## Why this class exists

READMEs quote best-case numbers from the author's benchmark. Some hold, some
don't, and the ones that don't are usually the ones a reader would hit first.
A post that says "claimed 60-90%, I measured 91% on code and 0% on shell output"
is trusted; "claims 60-90% savings" is marketing laundering.

## Step 1 — Find candidates with real filters

Star count alone selects for old, famous, or promoted repos. Filter on recency
and activity together:

```bash
gh api 'search/repositories?q=<terms>+in:name,description,readme+stars:>200+pushed:>2026-07-01&sort=updated&per_page=8' \
  --jq '.items[] | "\(.stargazers_count)\t\(.full_name)\t\(.pushed_at[0:10])\t\(.description[0:80] // "")"'
```

Then pull the health signals before investing time:

```bash
gh api repos/<owner>/<repo> --jq '{yildiz:.stargazers_count, fork:.forks_count,
  lisans:(.license.spdx_id//"YOK"), guncelleme:.pushed_at[0:10],
  acik_issue:.open_issues_count, arsiv:.archived, olusturma:.created_at[0:10]}'
```

Reject early: archived, no license, last push months old. A very high
fork-to-star ratio or a wall of content-free issues (`omg`, single first names)
suggests inflated stars — mention the number cautiously or not at all.

## Step 2 — Extract the falsifiable claims

Grep the README for numbers, not adjectives. "Blazing fast" is unfalsifiable;
"60-90% fewer tokens" and "~13 tokens on cached re-reads" are testable.

```bash
gh api repos/<owner>/<repo>/readme --jq .content | base64 -d > /tmp/readme.md
grep -nE '[0-9]+%|[0-9]+x|tokens|install|brew|npm|cargo|curl' /tmp/readme.md | head -25
```

Write the claims down before installing. You are testing *these*, not forming an
impression.

## Step 3 — Install it for real

Use the documented path (npm/brew/cargo/curl). Confirm the binary exists and
reports a version before measuring anything.

## Step 4 — Measure, and LOOK AT THE OUTPUT

**The trap that ruins this whole class of work:** measuring only the *size* of
the output and never reading it.

A file compressed 5179 → 521 bytes looked like a 90% win. The 521 bytes were an
error message:

```
path: path escapes project root: /private/tmp/... (root: /usr/.../node_modules/lean-ctx-bin)
```

The tool had pinned its root to its own install directory and refused to read
the file at all. Reported as-is, that would have been a fabricated benchmark in
a public post.

Rule: **every measurement gets `wc -c` AND `head -15`.** If you cannot see the
expected content in the output, the number is meaningless.

```bash
echo "=== ham ==="; wc -c target.py
echo "=== isle ==="; <tool> read target.py 2>&1 | wc -c
echo "=== icerik ==="; <tool> read target.py 2>&1 | head -15   # ZORUNLU
```

Measure across **input types**, not one flattering case. Code, plain prose, and
command output behave very differently. In one evaluation: source file 5179→452
(91%), markdown 8408→7140 (15%), `git status` 958→958 (0%). Only the first
matched the README.

Also test the second-call path if caching is claimed — repeat the identical
call and measure again.

## Step 5 — Report both columns

Lead with what held, state plainly what didn't, and name the gotcha you hit
during setup. The setup gotcha is often the most useful paragraph for the
reader, because they will hit it too.

Structure that works:
- what it is, in one mechanical sentence (not the tagline)
- the claim, and that you distrusted it enough to measure
- the measurement that held, with both raw and processed numbers
- the measurement that did **not** hold
- the install trap
- license, stars, source-open status

Never state a number you did not personally produce.

## Kuramadığın şeyi denetlemek

Değerlendireceğin şey bir araç değil de **bir teknik / yöntem / \"şunu yaptım\"
iddiası** ise kendi makinende ölçemezsin. O zaman ölçümün yerine geçen tek şey
iddia sahibinin **kendi yayımladığı ham veridir** — ve sınırları çoğu zaman
yazarın kendisi yazmıştır, sadece kimse okumamıştır.

Doğrulanmış vaka: X'te 3,8 milyon izlenme alan bir prompting tekniğinin yazarı,
kendi deposundaki `Honest assessment` bölümüne \"hedefe ulaşmadı\" yazmış, ham skor
tablosunda gerileme turu görünüyor ve kendi \"Process note\"u tekniğin ana iddiasını
(paralel fan-out) çürütüyordu. HN'de 4 puan almıştı — yani hiçbir mühendis
bakmamıştı.

Yöntem, aranacak depo bölümleri, ikincil anlatının verdiği kaynağı doğrulama ve
\"bulamadım\"ı bulgu olarak raporlama: `references/iddia-denetimi-kaynak-madenciligi.md`

## Konu seçimi: BAŞKASININ aracı, kendi deponuz değil

Bu skill'in tetiklendiği yer genelde \"bu haftaki içerik ne olsun\" sorusudur ve
orada tekrar eden bir sapma var: gün içinde kendi deponu yayınladıysan veya kendi
aracını düzelttiysen, o iş günün hikâyesi gibi hissettirir ve konu olur.
Değildir. Kullanıcının düzeltmesi (14 Ağu 2026):

> *\"Kendi repomuzu değil başka bu aralar trend olan bir repoyu bulalım ve
> paylaşalım\"*

Okuyucunun kazancı ölçülmüş bir dış araçtır. Kendi deponu tanıtmak duyurudur,
değerlendirme değil, ve bu skill'in bütün ölçüm yordamı orada boşa düşer, çünkü
kendi aracını \"denemiş\" olmazsın, zaten yazmışsındır.

Taze aday bulma (yıldız + tazelik birlikte, 30-60 günlük pencere):

```bash
curl -s \"https://api.github.com/search/repositories?q=created:>2026-06-01+stars:>800&sort=stars&order=desc&per_page=25\" \\
  | python3 -c \"import json,sys;[print('%6d  %-34s %s' % (r['stargazers_count'], r['full_name'][:34], (r.get('description') or '')[:64])) for r in json.load(sys.stdin)['items']]\"
```

Sonra Adım 1'deki sağlık kontrolüne düş: lisans, son itme, arşiv bayrağı.

## Aracın REDDİ de bir bulgudur, hatta en iyisi

Adım 4 \"çıktıya bak\" diyor. Bunun güçlü hâli: araç bir girdiyi işleyemediğini
**açıkça söylüyorsa** bu kusur değil, raporun en değerli satırıdır.

Ölçülmüş vaka (14 Ağu 2026, belge → markdown dönüştürücü): dört kendi dosyam
verildi, üçü dönüştü, dördüncüsü dönüşmedi ve şunu bastı:

```
anydoc: unsupported input: PDF has no extractable text (Scanned, 8 pages): OCR is required
```

Bağımsız doğrulama, sekiz sayfada metin katmanı gerçekten sıfırdı:

```python
import fitz
d = fitz.open(\"slaytlar.pdf\")
print(d.page_count, len(\"\".join(p.get_text() for p in d)))   # 8 0
```

Yani araç doğru davrandı. Bu sınıftaki çoğu kütüphane aynı girdide **boş dize**
döndürür ve kullanıcı dosyanın çevrildiğini sanır — Adım 4'teki \"sadece boyuta
bakma\" tuzağının tam olarak sessiz hâli. Sınırını söyleyen araç, sınırı yokmuş
gibi davranandan üstündür ve rapor bunu böyle yazmalıdır.

Bu yüzden ölçüm setine **kasten zor bir girdi koy**: taranmış PDF, boş dosya,
yanlış uzantı, çok büyük dosya. Hepsi başarılı olan bir ölçüm seti aracın
sınırlarını hiç göstermez.

## Rakamı KENDİ dosyalarınla üret

\"Never state a number you did not personally produce\" kuralının pratik hâli:
ölçümü kendi iş dosyalarınla yap, örnek dosyayla değil. Aynı vakada CV 673 ms,
iki sayfalık PDF tablo 39 ms, RTF 37 ms sürdü; bunlar kullanıcının gerçekten
ürettiği dosyalardı, dolayısıyla sayılar hem savunulabilir hem ilgili.

İlk çalıştırmayı ölçme, indirme süresi karışır (`npx` ilk çağrıda ikiliyi
indirir: 4,2 sn). Aracı kalıcı kur, sonra ölç.

## Pitfalls

- **Size-only measurement.** See Step 4. Read the bytes.
- **Single-input benchmarking.** One file type produces a number that doesn't
  generalise; the reader's first try will disagree with you.
- **Repeating README figures as findings.** If you couldn't reproduce it, say
  you couldn't reproduce it.
- **Config-scoped tools silently refusing.** Tools that sandbox to a project
  root (`extra_roots`, `allow_paths`, workspace config) fail *quietly* outside
  it. Configure the root first, then measure.
- **Treating star count as quality.** Check license, last push, archived flag,
  and issue quality.
- **Skipping the health check and burning an hour on an archived repo.**
- **Kendi deponu/aracını konu yapmak.** Değerlendirme dış araç içindir; kendi
  işini tanıtmak duyurudur ve bu skill'in ölçüm yordamı orada anlamsızdır.
- **Hepsi başarılı olan ölçüm seti.** Aracın nerede durduğunu göstermez. Sete
  kasten zor bir girdi koy (taranmış PDF, boş dosya, yanlış format).
- **İkincil anlatının verdiği kaynağa körlemesine güvenmek.** Video/thread/haber
  özetleri kaynak, isim ve rakamda yanılıyor. Bir oturumda üçü birden yanlış
  çıktı: yazarın soyadı, kaynak makale, izlenme sayısı. Kaynağı indirip içinde
  konunun geçtiğini `grep` ile doğrula; geçmiyorsa yanlış kaynaktır.

## Kullanıcıya sunum (Kasparov)

Kitle vibecoder: derin kod okuma, dil-içi detay ve Swift/AST seviyesi anlatım
İLGİ ÇEKMİYOR. Aracın ne yaptığı, ne kadar kazandırdığı ve nerede tökezlediği
ilgi çekiyor.

### Metni DOSYA olarak gönderme, KOD BLOĞU içinde yaz

14 Ağu 2026'da aynı turda dört kez ihlal edildi (RTF → sadece dosya, metin
yok → PDF → düzeltme) ve kullanıcı sert çıktı:

> *"ya olum telegramda mesaj atacaksın ya mesaj, zengin metin olarak mesaj
> atacaksın. sikicem dosya yollayıp durma ya"*

Kök hata bir yorum hatası: **"zengin metin" isteği RTF/HTML/PDF diye okundu.**
Zengin metin, Telegram'ın kendi biçimlendirmesi demek. Bir biçim
reddedildiğinde başka bir DOSYA biçimi denemek aynı hatayı tekrar etmektir.

| İstenen | Teslim |
|---|---|
| Post metni, mesaj, taslak (kopyalanacak) | Telegram mesajı, kod bloğu içinde |
| Yüklenecek belge (CV, PDF rapor) | Dosya |
| Çok satırlı karşılaştırma tablosu | PDF |

Kod bloğunun içine tarih, başlık veya açıklama koyma; blok içindeki her şey
kopyalanan metne sızar. Metni özetleyip "hazır" deme, tam hâlini yaz.

### Ders cümlesi ÖLÇÜMDEN çıksın, edebiyattan değil

Kapanış cümlesi postun en çok okunan yeri ve en kolay bozulan yeri. Aynı
oturumda ilk deneme yarım bir Türkçe cümleyle bitti (*"asıl bilgi nerede
durduğunda"*) ve kullanıcı takıldı: *"Bu kısım neden postun içinde?"*

Doğrusu ölçülen şeyin kendisini söyler: *"Bir aracın nerede durduğunu görmek,
ne yaptığını okumaktan daha çok şey anlatıyor."* Yazdıktan sonra tek başına
oku; bağlamsız anlamlı değilse yeniden yaz.

Post akışı `linkedin-ai-post-pipeline` skill'ine tabidir (post_lint.py zorunlu,
video ZORUNLU ve sitcom parodi klibi olmalı — veri/grafik animasyonu değil).
Bu skill sadece **ölçüm** tarafını tanımlar; yazım ve teslim o skill'de.
