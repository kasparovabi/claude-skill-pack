# Vaka: talep-motoru radar denetimi (2 Ağustos 2026)

SKILL.md'deki dokuz kalıbın çıktığı gerçek oturum. Sayılar ölçülmüştür, hiçbiri
tahmin değil.

## Sistem

`~/Developer/talep-motoru` — günlük cron (`daily_radar.sh`, 09:30) ve haftalık
kurul (`weekly_board.sh`, Pazar 21:30). Kadro: 4 scout → editör → rakip ölçümü →
doğrulayıcı → Telegram özeti. Anayasa `CLAUDE.md`, rol sözleşmeleri `prompts/`.

## Tetikleyen şikâyet

Kullanıcı günlük radar özetini alıntılayıp sordu: **"neredeyse her fikirde bir
düzeltme var, neden böyle"**.

## Ölçüm (Adım 0)

| Ölçüt | Sonuç |
|---|---|
| İki günde özete giren aday | 6 |
| Düzeltme alan | 6 (%100) |
| Düzeltmesiz geçen | 0 |
| Dayanak denetiminden çıkan hata | 0 |
| Rekabet ölçümünden çıkan bulgu | 5 |
| Kararı değiştiren düzeltme | 0 |

`ideas.db` durumu: 19 fikir, 16'sı `aday`, 2 `reddedildi`, 1 `izleniyor`.
`idea_events`: 19 `olusturuldu`, 5 `skorlandi`, 2 `durum:reddedildi`. Hiçbir
kayıt bir sonuca ulaşmamış.

## Teşhis

Scout yalnız `signals/` altındaki JSON'ları okuyor (ilk 50 listeleri + Reddit
RSS). Doğrulayıcı `lib/appstore.py` ile canlı App Store sorguluyor. Rakip sayısı,
fiyat çıpası, doygunluk hiçbir sinyal dosyasında yok. Yani scout'un gerekçesinin
her koşuda revize edilmesi **tasarımın zorunlu sonucu**, arıza değil.

Sorun şuydu: ACFT tipi gerçek hatalar (dayanak kalkmış) ile rutin rekabet ölçümü
aynı "Düzeltme" satırında sunuluyordu. İki gündür dayanak hatası hiç çıkmamıştı
ama sayaç her gün alarm veriyordu.

### Saman adam kanıtı

Doğrulayıcı, ekran görüntüsü karartıcı adayı için `"Kimse yapmamış" iddiası
düştü` yazmıştı. `reports/2026-08-02_scout_raw.json` açıldığında scout'un
`why_now` alanı:

> "Bugünün ABD ücretli listesinde üç gizlilik aracı var, biri 5. sırada ve
> yayıncısı tek kişi..."

Böyle bir iddia yok. Zaten `prompts/scout_ortak.md` 31 Temmuz'dan beri rakip
iddiasını yasaklıyor. Doğrulayıcı olmayan bir iddiayı çürütüp kendi katkısını
büyütmüştü.

## Bulunan iki sessiz arıza

### 1. Oyun listesi iki gündür yanlış veri

`collect_signals.py` şunu çağırıyordu:

```
https://rss.marketingtools.apple.com/api/v2/us/apps/top-free/50/apps.json?genre=6014
```

Uç `genre` parametresini **sessizce yok sayıyor**. Kanıt:

```
A: ?genre=6014 → ['Netflix Game Controller', 'TikTok Pro', 'ChatGPT', 'Capital One', 'Threads']
B: itunes.apple.com/us/rss/topfreeapplications/limit=50/genre=6014/json
   → ['Block Out!', 'Smash Fest!', 'Meowdoku!', 'Bus Traffic Fever!', 'Magic Sort!', 'Roblox']
```

1 ve 2 Ağustos'ta oyun masası uygulama listesini oyun sanıp yarım çalıştı. İstek
200 dönüyordu, log temizdi. Sadece 2 Ağustos özetinde bir insan "md5 eşit" diye
not düşmüştü.

Denenip elenen alternatifler (ikisi de 404):
```
.../us/apps/top-free-games/50/apps.json
.../us/games/top-free/50/games.json
```

Çözüm: `ITUNES_LEGACY_FEEDS` sözlüğü + ayrı ayrıştırıcı + oyun oranı nöbetçisi.

Legacy şema tuzağı: `entry.link` bazen dict, bazen liste geliyor (ek bağlantısı
olan uygulamalarda). Kontrol gerekli:

```python
link = entry.get("link")
if isinstance(link, list):
    link = link[0] if link else {}
```

Doğrulama sonrası: 50 kayıt, 50'si Games, md5'ler farklı.

### 2. Ölçüm tavanı bir adayı haksız yere elemişti

`lib/keywords.py` iTunes'a `limit=50` ile soruyordu ve uç `resultCount`'ı limite
kırpıyor:

```
limit=50  → resultCount 48
limit=200 → resultCount 178
```

Ekran görüntüsü karartıcı adayı 2 Ağustos'ta şu gerekçeyle reddedilmişti:

> "Anayasa: iOS adayi keyword-once secilir, olculemiyorsa aday degildir.
> lib/keywords.py iOS kanalinda olcum yapamiyor (limit=50 tavani)."

Yani araç bozuk olduğu için fikir öldü. `ITUNES_LIMIT = 200` + tavan bayrağı
eklendikten sonra aynı sorgu 178 gerçek sonuç veriyor.

## Uygulanan değişiklikler

**Sözleşmeler**
- `prompts/dogrulayici.md` — yeniden yazıldı. `duzeltme` yalnız dayanak
  değişince dolar, rekabet ayrı `rekabet` nesnesine gider, `silinen_iddialar`
  birebir alıntı ister. Rekabet ölçülemedi tek başına adayı düşürmez.
- `prompts/editor.md` — özet formatına `Rekabet:` ve koşullu `Düzeltme:`
  satırları, kapanışta iki ayrı sayaç.
- `prompts/kasap.md` — YENİ. Üç karar (yaşat/beklet/öldür), beş kanıta bağlı
  öldürme gerekçesi, tarihsiz bekletme yasağı, sıfır karar da raporlanır.

**Kod**
- `lib/etsy_rivals.py` — YENİ. `reports/_etsy_rakip.py` tek kullanımlıktı,
  kalıcılaştırıldı. İlan sayısı + favori dağılımı + fiyat çıpası ölçer.
- `tools/kasap_liste.py` — YENİ. LLM'siz, karar bekleyeni yaşıyla listeler,
  21 gün eşiğini işaretler, hiçbir şey öldürmez.
- `collect_signals.py` — legacy uç + oyun oranı nöbetçisi.
- `lib/keywords.py` — tavan 200 + `tavanda` bayrağı.

**Betikler**
- `daily_radar.sh`, `weekly_board.sh` — `MODEL="claude-opus-5"`, `--model`
  bayrağı, prompt gövdesinde açık model kuralı, kanal→ölçüm aracı eşlemesi,
  Kasap adımı.

**Anayasa** — kapı 4 model kimliği, 6b/6c/6d yeni kapılar, kadro tablosu tümü
opus-5, karar mercileri tablosu eklendi.

## Yapılan hatalar

1. `patch` ile fonksiyon eklerken `def hacker_news():` başlığını yanlışlıkla
   sildim. LSP `"hacker_news" is not defined` diye yakaladı. Ders: `patch`
   old_string'i seçerken sonraki fonksiyonun imzasını sınır olarak alma.
2. Heredoc'ta `$SIGNAL_DIR`'i gereksiz yere `\$` ile kaçırdım. `bash -n` temiz
   geçti ama render edilen gövdede ham `$SIGNAL_DIR` metni vardı, ajan sinyal
   dizinini bulamayacaktı. Ancak gövdeyi `eval "cat <<EOF"` ile render edip
   okuyunca görüldü.

## Doğrulama çıktısı

```
collect_signals.py  → EXIT 0, 510 sinyal, 11 kaynak, hepsi OK
md5 games vs apps   → farklı (önce eşitti)
oyun listesi        → 50 kayıttan 50'si Games
magaza.json         → 31 kayıt (1 Ağu'da boş dönüyordu)
etsy_rivals.py      → "funny bathroom wall art": 142.273 ilan, lider 7.127 fav,
                      ilk sayfa %40 dijital, medyan 15.0
keywords.py ios     → "redact screenshot": competition 178 (önce 50)
kasap_liste.py      → 17 aday listelendi, 21 günü aşan 0
bash -n             → her iki betik temiz
render testi        → SIGNAL_DIR mutlak yola genişliyor, MODEL 6 satırda
```

## Kullanıcıya bırakılan açık karar → nasıl kapandı

Karartıcı fikri bozuk ölçüm aracı yüzünden reddedilmişti ve red gerekçesinde
"ölçüm aracı düzeltilirse yeniden bakılabilir" yazıyordu. Ama anayasa
reddedileni geri getirmiyor. Diriltip diriltmeme kararı kullanıcıya soruldu,
kendi başına yapılmadı.

Kullanıcı "yeniden değerlendirsin" dedi. Kapanış şöyle oldu:

**Önce ölçüldü, sonra ledger'a dokunuldu.** Eski gerekçeyi tekrar etmek yerine
düzeltilmiş araçla dört terim koşturuldu:

```
redact screenshot        → birebir rakipler var ama HEPSI OLU:
                           Redact Screenshot-Blur Text 1 oy, Screenshot
                           Editor-Text Blur 3 oy, Redacter 2 oy, Redactly 0 oy
                           Ayni sorgudaki yuksek oylular FARKLI is yapiyor:
                           Picsew 3069, Stitch It 2654 (ekran gor. BIRLESTIRME)
blur personal info photo → Blur Photo 31.454 oy, Blur Photo Effect 26.984,
                           Blur Photo Background 18.726 — genel bulaniklastirma,
                           otomatik tespit yok
```

Yorum: arama niyeti `blur` tarafında, `redact` tarafı boş **ve** ölü. Ölü
rakipler yanlış kelimeyle konumlanmışsa o başarısızlık fikrin değil
isimlendirmenin başarısızlığı olabilir. Ayrışma noktası net: rakipler elle
seçtiriyor, otomatik tespit boşta.

**Eski gerekçedeki iki iddia ayrı ayrı işaretlendi.** "Ölçülemiyor" çürüdü
(178 gerçek sonuç). "Altı kişi denemiş, tutturamamış" doğrulandı, hatta rakamlar
daha kötü çıktı. İkisi aynı gerekçede yan yanaydı; biri düştü diye diğeri
düşmüyor.

**Ledger yazımı** (`lib/ledger.py`, iki olay + statü):

```python
ledger.log_event(conn, 16, "olcum_araci_duzeltildi",
    "lib/keywords.py limit=50 -> 200. Eski olcum 'tam 50 rakip' diyordu (tavan), "
    "gercek sonuc 178. Red gerekcesinin olcum ayagi gecersiz.")
ledger.log_event(conn, 16, "rekabet_olculdu", "<yukaridaki olcumun ozeti>")
conn.execute("UPDATE ideas SET reject_reason = NULL WHERE id = ?", (16,))
ledger.set_status(conn, 16, "aday",
    "Kullanici karari 2026-08-02: red gerekcesi fikrin kendisi degil OLCUM "
    "ARACIYDI. Arac duzeltildi, olcum kosturuldu. Onceki red gerekcesi: " + eski[:200])
```

Eski gerekçe silinmedi, yeni notun içine gömüldü — geçmiş okunabilir kalsın.

**Anayasaya istisna yazıldı** (kapı 3), kapıyı sonuna kadar açmadan: üç koşul
birlikte (araç kanıtlanıp düzeltildi + ölçüm fiilen koşturuldu + iki olay
ledger'a yazıldı), karar kullanıcının. `prompts/kasap.md`'ye de karşılık kural
eklendi — Kasap diriltemez, sadece "gerekçesi bozuk ölçüme dayanıyordu" diye not
düşer.

**Skora dokunulmadı.** 25 puan bozuk ölçümle hesaplanmıştı ama yeniden skorlama
haftalık kurulun işi. Karar merci tablosu varken onu delmek anlamsız olurdu.

Doğrulama: `tools/kasap_liste.py` → 18 aday (önce 17), kayıt `aday` statüsünde,
son olayı diriltme notu.

