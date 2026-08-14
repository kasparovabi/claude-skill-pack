---
name: multi-agent-pipeline-audit
description: "Use when an agent crew ships a broken report. Diagnose the pipeline."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Multi-Agent, Pipeline, Audit, Cron, Diagnosis, Data-Quality, Decision-Design]
    related_skills: [ralph-loop, claude-code, dynamic-workflow, systematic-debugging, upstream-pr-review-response]
---

# Tekrarlayan ajan ekibi denetimi

Zamanlanmış bir ajan ekibi (cron + scout'lar + editör + doğrulayıcı gibi) her gün
rapor üretiyor ve kullanıcı **çıktının şeklinden** şikâyet ediyor: "neredeyse her
maddede bir uyarı var, neden böyle", "bu rapor artık bir şey söylemiyor", "hep
aynı şeyi yazıyor".

Bu skill o şikâyeti teşhise çevirir. Ana kural: **şikâyet çıktı hakkındadır ama
sebep neredeyse hiç çıktıda değildir.** Prompt'u güzelleştirmek yerine boru
hattının hangi adımının hangi veriyi göremediğini bul.

## Ne zaman kullan

- Kullanıcı yinelenen otomatik bir raporun kalitesini/tonunu sorguladı
- Beklenen rapor hiç gelmedi ("bu sabah rapor gelmedi", "cron çalışmamış") —
  özellikle makine uyuduysa ya da ağ kesildiyse
- Bir cron ekibinin çıktısında aynı uyarı/etiket her koşuda tekrarlıyor
- Ekibe yeni rol, yeni karar mekanizması ya da model değişikliği eklenecek
- "Bu ekip neden hiç X yapmıyor" ya da "neden hep Y diyor" sorusu geldi

Tek seferlik bir prompt düzeltmesi için kullanma. Bu skill kadrosu ve sözleşmesi
olan, tekrar tekrar koşan sistemler içindir.

## Adım 0 — Açıklamadan önce SAY

Teori üretme. Önce son koşuların çıktısını say ve oranı gör.

```
kaç aday özete girdi | kaçı etiket aldı | etiket kararı değiştirdi mi
```

Sayı, hikâyeyi tek başına kurar. Bir örnekte iki günde özete giren 6 adayın
6'sı da "Düzeltme" almıştı; %100 oran tesadüf değil, tasarımın zorunlu
sonucudur. Ayrıca 6 düzeltmenin **hiçbiri** kararı değiştirmemişti, yani
uyarıların tamamı dipnottu.

Ledger/DB varsa doğrudan oradan say, rapor metninden değil:

```sql
SELECT status, COUNT(*) FROM ideas GROUP BY status;
SELECT action, COUNT(*) FROM idea_events GROUP BY action ORDER BY 2 DESC;
```

## Teşhis kalıpları

Aşağıdakiler bu sınıfta tekrar tekrar çıkar. Sırayla kontrol et.

### 1. Girdi asimetrisi — üreten göremez, denetleyen görür

Üretici ajan yalnız dosyadan okuyor (`signals/` gibi), denetleyici ajan canlı
API çağırıyor. Bu kurulumda üreticinin gerekçesinin her koşuda revize edilmesi
**beklenen çıktıdır**, arıza sinyali değil. Kullanıcı bunu "üretici sürekli hata
yapıyor" diye okur.

Çözüm etiketi değiştirmek değil, iki bulguyu ayırmaktır (bkz. kalıp 2).

### 2. Tek alanda toplanmış iki farklı sinyal sınıfı → alarm yorgunluğu

İki ayrı denetim (ör. "dayanak hâlâ yürürlükte mi" ve "rekabet ne durumda") tek
bir çıktı alanına yazılıyorsa, sık olan seyrek olanı boğar.

**Her koşuda çalan alarm alarm değildir.** Ayır:

- Kararı değiştirebilen bulgu → kendi alanı, kendi sayacı, seyrek dolar
- Her koşuda üretilen ölçüm → ayrı alan, her maddede yazılır, alarm değil

Sayaç da ayrılır. `"3 aday düzeltildi"` yerine:

```
Dayanak: <n> yürürlükte, <n> değişti, <n> doğrulanamadı.
Rekabet: <n> adayda ölçüldü, <n> adayda ölçülemedi.
```

### 3. Saman adam — denetleyici, söylenmemiş iddiayı çürütüyor

Denetleyici ajan "X iddiası düştü" yazıyor ama üretici X'i hiç yazmamış (hatta
yazması yasaklanmış). Ajan kendi katkısını büyük göstermek için olmayan bir
iddiayı çürütür, kullanıcı da üreticinin hata yaptığını sanır.

Sözleşmeye **alıntı zorunluluğu** koy: bir iddiayı sildiğini yazacaksa
üreticinin çıktısındaki cümleyi birebir alıntılamak zorunda. Alıntılayamıyorsa
o satır düzeltme değil, ölçüm bulgusudur.

```json
"silinen_iddialar": [
  {"kaynak_cumlesi": "<birebir alinti>", "neden": "<olculen gercek>"}
]
```

### 4. Sessiz veri arızası — HTTP 200, yanlış gövde

En sinsi hata. Endpoint 200 dönüyor, alan adları doğru, **içerik yanlış**.
Tipik sebep: uç bir query parametresini sessizce yok sayıyor.

Teşhis: aynı olmaması gereken iki kaynağın md5'ini karşılaştır.

```bash
md5 signals/<tarih>/apple_us_free_games.json signals/<tarih>/apple_us_free_apps.json
```

Eşitse filtre uygulanmamış demektir. Bir örnekte `?genre=6014` iki gün boyunca
yok sayıldı, oyun masası uygulama listesini oyun sanıp yarım çalıştı ve hiçbir
log satırı hata göstermedi.

Onarım iki parçalıdır:
1. Çalışan uca geç (eski/legacy uç genelde filtreyi hâlâ uygular)
2. **Mekanik nöbetçi koy** — beklenen içerik oranı tutmuyorsa hata işaretle

```python
oyun_sayisi = sum(1 for i in items if "Games" in (i["genres"] or [""])[0])
if items and oyun_sayisi < len(items) // 2:
    return SourceResult(name, items, f"genre filtresi tutmadi: {oyun_sayisi}/{len(items)}")
```

Sözleşmeye kural yazmak yetmez; çıkışta mekanik olarak zorla.

### 5. Ölçüm tavanı → sahte "ölçülemedi" → haksız eleme

API `limit` parametresi sonuç sayısını kırpıyorsa, eşiği aşan her niş **tam
limit kadar** görünür. Bu, "ölçüm yapılamadı" sanılıp adayın elenmesine yol
açar.

```bash
for L in 50 200; do curl -s ".../search?term=X&limit=$L" | jq .resultCount; done
# 50  -> 48   (gercek)
# 200 -> 178  (gercek)   ← 50 tavani sahte "tam 50" uretiyordu
```

Tavanı yükselt **ve** tavana dayanıldığını çıktıda söyle:

```python
tavanda = sayi >= LIMIT
reason = "sonuc tavana dayandi, gercek rekabet daha yuksek" if tavanda else None
```

Bu kalıbı bulduğunda, tavan yüzünden geçmişte elenmiş kayıtları da tara —
haksız eleme sessizce ledger'da durur.

#### 5b. Bozuk ölçümle elenmiş kaydı geri getirme protokolü

Ölçüm aracını onardıysan, o araç yüzünden elenmiş kayıtlar için "reddedilen geri
gelmez" kuralını **delmeden** bir istisna tanımla. Ayrım şu: red gerekçesi
kaydın kendisine mi dayanıyordu, yoksa o gün bozuk olan teraziye mi.

Üç koşul **birlikte** sağlanmadan diriltme yok:

1. Aracın bozuk olduğu kanıtlanmış ve düzeltilmiş
2. Düzeltilmiş araçla ölçüm **fiilen koşturulmuş** (eski gerekçeyi tekrar etme,
   yeniden ölç)
3. Ledger'a hem düzeltme hem yeni ölçüm ayrı olay olarak yazılmış

```python
ledger.log_event(conn, idea_id, "olcum_araci_duzeltildi", "limit=50 -> 200, gercek sonuc 178")
ledger.log_event(conn, idea_id, "rekabet_olculdu", "<yeni olcumun ozeti>")
conn.execute("UPDATE ideas SET reject_reason = NULL WHERE id = ?", (idea_id,))
ledger.set_status(conn, idea_id, "aday", "Kullanici karari <tarih>: gerekce OLCUM ARACIYDI. "
                                         "Onceki red gerekcesi: " + eski[:200])
```

Kararın sahibi **kullanıcıdır**. Reaper (Kasap) kendi başına diriltemez; sadece
"bu kaydın gerekçesi bozuk ölçüme dayanıyordu" diye not düşer ve önüne koyar.
Bunu reaper sözleşmesine açıkça yaz, yoksa istisna bir süre sonra kuralı yer.

Yeni ölçüm kaydı yine düşürüyorsa kayıt ölür — ama bu kez gerekçesi ölçülmüş
olur. Eski gerekçedeki iddiaları tek tek işaretle: hangisi çürüdü, hangisi
sağlamlaştı. Bir örnekte "ölçülemiyor" iddiası çürüdü, "N rakip denemiş ve
tutturamamış" iddiası doğrulandı; ikisi aynı gerekçede yan yanaydı.

Skoru kendi başına değiştirme. Bozuk ölçümle hesaplanmış skor yanlıştır ama
yeniden skorlama karar merciinin (haftalık kurul) işidir — sen sadece kaydı
masaya geri koyarsın.

### 6. Biriktiren ama temizlemeyen ekip — reaper yok

Üreten rol var, öldüren rol yok. Ledger şişer, her hafta aynı yığın karar
merciinin önüne çıkar, seçim ağırlaşır.

Belirti: `SELECT status, COUNT(*)` çıktısında ezici çoğunluk tek bir bekleme
statüsünde ve hiçbiri sonlanmamış.

Çözüm: **Kasap** rolü. Günlük koşar, her bekleyen kayda üç karardan birini
verir ve kararı ledger'a yazar:

- **yaşat** — gerekçe zorunlu, "henüz bakılmadı" gerekçe değil
- **beklet** — somut tetikleyici + **yeniden bakış tarihi** zorunlu. Tarihsiz
  bekletme erteleme değil, sessiz ölümdür
- **öldür** — gerekçe kanıta bağlı listeden seçilir, "içime sinmedi" yasak

Öldürme gerekçelerini önceden say ve sözleşmeye yaz (dayanak çöktü / doygunluk /
fiyat çıpası kırık / yaş aşıldı ve tekrar görülmedi / kural ihlali). Serbest
metin gerekçe, kararı denetlenemez yapar.

Ayrıca "sıfır karar" meşru ama sessiz geçilemez: `"bugün 0 karar, sebep: X"`
satırı zorunlu olsun.

### 7. Karar sahipsizliği

Kim neye karar veriyor yazılı değilse iki rol aynı kararı verir ya da hiçbiri
vermez. Anayasaya **karar mercileri tablosu** ekle: her karar, tek sahip, kadans.

| Karar | Merci | Kadans |
|---|---|---|
| Şemadan geçti mi | Editör | günlük |
| Dayanak yürürlükte mi | Doğrulayıcı | günlük |
| Yaşar / bekler / ölür | Kasap | günlük |
| Build'e girer mi | Haftalık kurul | haftalık |
| Sözleşme değişikliği | Kullanıcı | retro önerir |

### 8. Model takma adı → denetlenemez koşu

`--model opus` gibi takma adlar CLI'nin o günkü varsayılanına çözülür ve
log'dan hangi sürümün koştuğu okunamaz. Tam sürüm kimliği kullan
(`claude-opus-5`), hem bayrakta hem prompt gövdesinde.

Güncel kimliği **doğrula, hatırlama** — training verisi eskir:

```bash
curl -sL https://platform.claude.com/docs/en/docs/about-claude/models/overview.md | grep -i -A2 "Claude API ID"
```

CLI'nin gerçekten tanıdığı kimlikleri ikiliden de teyit edebilirsin:

```bash
strings ~/.local/share/claude/versions/<surum> | grep -oE "claude-(opus|sonnet|fable)-[0-9-]*" | sort -u
```

### 9. Tek kullanımlık script → tekrarlanamayan ölçüm

Bir ajan `reports/` altına geçici bir ölçüm script'i yazıp bırakmışsa, ertesi
gün o ölçüm hiçbir sözleşmede yazmaz ve yeniden icat edilir. Bir yüzeyde kalıcı
araç varken (`lib/appstore.py`) diğer yüzeyde her gün yeniden yazılıyorsa bu
kalıptır.

`lib/` altına taşı, sözleşmeye kanal→araç eşlemesi olarak yaz:

```
ios  -> python lib/appstore.py "<terimler>"
etsy -> python lib/etsy_rivals.py "<terimler>"
web  -> uygun arac yoksa "kontrol edilemedi" yaz, uydurma
```

**Yanlış yüzeyde ölçüm, ölçüm yapmamaktan daha kötüdür** — Etsy adayını App
Store'da ölçmek anlamsız bir sayı üretir ve o sayı doğru sanılır.

### 10. Uyuyan makinede fail-open → geçici ağ kesintisi kalıcı veri kaybına döner

Belirti: kullanıcı **\"bu sabah rapor gelmedi\"** diyor. Cron kayıtlarında iş
`error` görünüyor ama iş aslında **koştu**.

Kök neden zinciri (dizüstünde koşan her ajan ekibi için geçerli):

1. Makine gece uyudu, cron kaçırdığı işi yakalama (catch-up) moduyla tetikledi
2. Uyanma `DarkWake` tipiydi — işlemci uyandı, **WiFi henüz bağlanmamıştı**
3. DNS çözülmedi, bütün kaynaklar `ENOTFOUND` döndü
4. Toplayıcı fail-open davrandı ve **hata dönen kaynağın boş çıktısını diske
   yazdı**; bir önceki günün dolu dosyası boş `[]` ile **EZİLDİ**
5. \"Dizin boş mu\" kontrolü geçti, çünkü dosyalar vardı — sadece 2 baytlıklardı
6. LLM CLI de aynı hataya çarpıp düştü, rapor hiç üretilmedi

Arıza **gürültülü** (her satırda ENOTFOUND) ama hasar **sessiz**: dün çalışan
veri yok oldu ve kimse fark etmedi.

Zaman çizelgesini önce kanıtla, tahmin etme:

```bash
pmset -g log | grep -E \"Sleep  |Wake   |DarkWake\" | tail -25
```

**Aynı pencerede birden çok cron işi düştüyse bu tek tek iş hatası değil, ortam
hatasıdır.** Üç iş 09:16-10:34 arasında düştüyse tek tek prompt'larını inceleme,
ortama bak.

Üç katmanlı onarım — üçü de gerekli:

**(a) Betiğe ağ ön kontrolü, fail-closed.** Ağ yoksa koşuya hiç başlama:

```bash
ag_var_mi() {
  for host in api.anthropic.com <veri-kaynagi-host>; do
    ping -c1 -t3 \"$host\" >/dev/null 2>&1 || nc -z -G3 \"$host\" 443 >/dev/null 2>&1 && return 0
  done
  return 1
}
AG_DENEME=0
until ag_var_mi; do
  AG_DENEME=$((AG_DENEME + 1))
  if [[ $AG_DENEME -ge 10 ]]; then
    log \"HATA: 5 dakikadir ag yok. Kosu YAPILMADI, cikiliyor.\"
    exit 0        # 0 dondur: bu bir kod hatasi degil, ortam hali
  fi
  sleep 30
done
```

**(b) Toplayıcı, hatalı kaynağın boş çıktısını YAZMASIN.** Asıl zehir burada:

```python
if result.error and not result.items:
    durum = \"korundu\" if path.exists() else \"yazilmadi\"
    ledger.record_source_stat(conn, result.source, today, 0, result.error)
    print(f\"  {result.source:26s} 0 sinyal  HATA ({durum}): {result.error}\")
    continue          # eski dosya oldugu gibi kalir
```

Ayrıca **kısmi kayıp ile toplu kaybı ayır** — fail-open yalnız kısmi kayıpta
anlamlıdır:

```python
if totals and not any(totals.values()):
    print(\"HATA: butun kaynaklar bos dondu, ag arizasi olabilir\")
    sys.exit(2)       # cagiran betik ayirt edebilsin
```

**(c) Varlık kontrolü değil, İÇERİK kontrolü.** `ls -A` dosya sayar, veri
saymaz:

```bash
DOLU=$(find \"$SIGNAL_DIR\" -name '*.json' -size +10c | wc -l | tr -d ' ')
TOPLAM=$(find \"$SIGNAL_DIR\" -name '*.json' | wc -l | tr -d ' ')
if [[ \"$DOLU\" -lt 3 ]]; then
  log \"HATA: $TOPLAM dosyadan yalniz $DOLU tanesi dolu. Kosu YAPILMADI.\"
  exit 1
fi
```

Onarımdan sonra **zehirli boş dosyaları sil** — onlar veri değil arıza artığıdır
ve ertesi gün \"dün de boştu\" diye yanlış okunur.

Hermes cron'un kendisinde ağ farkındalığı yoktur; kaçırılan işi ağ hazır mı diye
bakmadan tetikler. Bu yüzden koruma **her betiğin kendi içinde** olmalı. Çekirdeğe
genel bir bekleme adımı eklemek kullanıcı kararıdır, kendi başına yapma.

## Onarım sırası

1. Say, oranı göster, kullanıcıya sebebi tek paragrafta anlat
2. Sözleşme (`prompts/*.md`) — alanları ayır, alıntı zorunluluğu, sayaç ayrımı
3. Kod — sessiz arıza nöbetçisi, tavan bayrağı, kalıcı ölçüm aracı
4. Yeni rol + karar mercileri tablosu
5. Anayasa/`CLAUDE.md` — kapılar ve kadro tablosu güncellenir, **gerekçesiyle**
   (hangi tarihte hangi ölçüm bu kuralı doğurdu)
6. Kuru koşu ile doğrula

Anayasaya kural yazarken gerekçe ve tarih koy. Gerekçesiz kural birkaç ay sonra
"neden böyleydi" diye sorulup kaldırılır.

## Doğrulama — betik üretiyorsa `bash -n` YETMEZ

Cron betikleri prompt gövdesini heredoc ile üretir. `bash -n` sadece sözdizimi
bakar; değişkenin gerçekten genişleyip genişlemediğini görmez. Heredoc içinde
`\$VAR` kaçışı yaparsan ajana ham `$SIGNAL_DIR` metni gider ve dizin yolu
kaybolur — betik hatasız koşar, ajan yolu bulamaz.

Gövdeyi **render edip oku**:

```bash
ROOT=/path/proje; TODAY=$(date +%F); SIGNAL_DIR="$ROOT/signals/$TODAY"; MODEL="claude-opus-5"
sed -n '/^cat >/,/^EOF$/p' daily_radar.sh | sed '1d;$d' > /tmp/govde.txt
eval "cat <<EOF
$(cat /tmp/govde.txt)
EOF"
```

Sonra gözle doğrula: yol mutlak mı, model kimliği kaç yerde geçiyor.

### Fail-closed korumasını VARSAYMA, ağsızlığı simüle et

Ağ koruması yazdıysan onu gerçekten ağsız koştur. Kabloyu çekmeye gerek yok:
kapalı bir porta proxy vererek her giden isteği düşür.

```python
env = dict(os.environ)
env["HTTPS_PROXY"] = "http://127.0.0.1:9"   # kapali port
env["HTTP_PROXY"]  = "http://127.0.0.1:9"
```

İki şeyi ayrı ayrı kanıtla:

1. **Hiç boş dosya yazılmadı** — geçici bir `SIGNAL_DIR` ver, sonra
   `len(list(dir.glob("*.json"))) == 0` bekle
2. **Eski dosya EZİLMEDİ** — dizine sahte bir \"önceki gün verisi\" koy, boyutunu
   ölç, ağsız koşuyu çalıştır, boyutun aynı kaldığını doğrula

```python
sahte.write_text(json.dumps([{"rank": 1, "name": "ONCEKI GUNUN VERISI"}]))
once = sahte.stat().st_size
# ... agsiz kosu ...
assert sahte.stat().st_size == once, "EZILDI"
```

Sonra ağ **açıkken** de bir kez koştur — fail-closed eklerken ağlı yolu bozmak
kolaydır. Uzun toplayıcılar (~4-5 dk) ön planda araç zaman aşımına takılır;
`background=true` ile başlat, dosyalar dolarken yoklayarak izle.

Kalan doğrulama listesi:

- [ ] Yeni/onarılmış toplayıcı koşturuldu, kaynak sayıları gerçek
- [ ] Daha önce kopya dönen dosyaların md5'i artık farklı
- [ ] Yeni ölçüm aracı gerçek sorguyla test edildi, çıktı mantıklı
- [ ] Reaper aracı koştu ve bekleyenleri listeledi (öldürmeden)
- [ ] Prompt gövdesi render edildi, yollar mutlak
- [ ] `bash -n` her iki betikte temiz
- [ ] Ağsız simülasyon koştu: sıfır boş dosya + eski dosya korundu
- [ ] Ağlı koşu da bir kez doğrulandı (fail-closed ağlı yolu bozmamış)

## Tuzaklar

- **Sebebi çıktıda aramak.** Rapor formatını güzelleştirmek şikâyeti susturur,
  arızayı kapatmaz. Girdi asimetrisine bak.
- **Ajanın kendi raporuna güvenmek.** Ajanın "3 aday düzeltildi" demesi
  düzeltmelerin gerçek olduğunu göstermez. Ham çıktıyı (`scout_raw.json`) aç ve
  denetleyicinin iddiasını üreticinin metniyle karşılaştır.
- **200 = sağlıklı sanmak.** Sessiz filtre düşmeleri her zaman 200 döner.
- **Sadece prompt'a kural yazmak.** Kural mekanik olarak zorlanmıyorsa bir
  sonraki koşuda yine ihlal edilir.
- **Reaper'ı aynı gün doğan kayda saldırtmak.** Kayıt en az bir tam koşu
  yaşasın, yoksa üretim ile temizlik birbirini yer.
- **Model yükseltmesini çözüm sanmak.** Model bilgisi de eskir; asıl çözüm
  doğrulama ve karar adımlarıdır. Model pahalılaştırması sadece tabandır.
- **Heredoc içinde gereksiz `\$` kaçışı.** Betik çalışır, ajan yolsuz kalır.
- **Ölçüm aracını değiştirip geçmişi taramamak.** Bozuk araçla elenmiş kayıtlar
  ledger'da haksız yere ölü durur; kullanıcıya sor, kendi başına diriltme.
- **Fail-open'ı her yerde iyi sanmak.** Kısmi kaynak kaybında doğrudur; ağ
  tamamen yokken **veri imha eder** — hatalı boş çıktı dünün dolu dosyasını ezer.
  Hata varsa yazma, eskiyi koru.
- **Dosya varlığını veri varlığı sanmak.** `ls -A` doluyken içerik 2 baytlık
  `[]` olabilir. Boyut/kayıt say, dosya sayma.
- **Rapor gelmedi şikâyetini prompt sorunu sanmak.** Önce işin gerçekten koşup
  koşmadığına ve ortam durumuna (uyku/ağ) bak; aynı pencerede birden çok iş
  düştüyse sebep ortamdadır, sözleşmede değil.

## Kullanıcıya sunum

Kasparov için: markdown başlık yok, numaralı liste yok, doğal paragraf. Önce
sayı ve sebep, sonra ne yapıldığı, sonunda **tek** karar sorusu. Teknik rapor
(commit, diff, dosya yolu) istenmedikçe paylaşılmaz. Kural değişikliği önerisi
uygulanmadan önce onaya sunulur; onay gelince kod da yazılır, sadece sözleşme
değil.

## Destek dosyaları

- `references/talep-motoru-2026-08.md` — bu kalıpların ilk çıktığı gerçek vaka:
  ölçülen sayılar, bulunan iki sessiz arıza, uygulanan değişiklikler
- `references/uyku-ag-kesintisi-vakasi.md` — kalıp 10'un vakası: uyuyan Mac,
  DarkWake'te WiFi yokken koşan cron, ezilen sinyal dosyaları, üç katmanlı
  onarım ve ağsız simülasyonla doğrulama
