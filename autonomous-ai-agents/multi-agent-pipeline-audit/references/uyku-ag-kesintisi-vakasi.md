# Vaka: uyuyan Mac + DarkWake → üç cron işi birden düştü (3 Ağu 2026)

Kalıp 10'un çıktığı gerçek olay. Şikâyet tek cümleydi: **"bu sabah raporu
gelmedi"**, ve kullanıcı kendisi ekledi: "o sırada Mac uyku modundaydı ve
internete bağlı değildi".

## Yanıltıcı ilk görünüm

Cron kayıtları işi `error` gösteriyordu ama iş **koşmuştu**. Yani "cron
tetiklenmedi" hipotezi yanlıştı; asıl soru "koştu da neden çöktü" idi.

## Kanıt zinciri

`pmset -g log` çıktısı gecenin tamamının uyku/DarkWake döngüsü olduğunu
gösterdi:

```
09:36:12 DarkWake  ... rtc/SleepService Using BATT
09:47:18 DarkWake  ... wifibt SMC.OutboxNotEmpty
10:04:56 DarkWake  ...
11:07:56 Wake      ... lid / HID Activity      ← kullanıcı gerçekten burada açtı
```

Cron catch-up 09:16'da tetikledi. O an makine `DarkWake`teydi: işlemci uyanık,
WiFi henüz bağlanmamış.

Toplayıcı logu, 11 kaynağın 11'inde aynı hatayı verdi:

```
apple_us_free_apps   0 sinyal  HATA: URLError: <urlopen error [Errno 8]
                                nodename nor servname provided, or not known>
...
magaza               0 sinyal  HATA: NameResolutionError ... api.etsy.com
```

LLM CLI de aynı duvara çarptı:

```
connection failed - error; no more retries left
  message: "getaddrinfo ENOTFOUND api.anthropic.com"
API Error: Unable to connect to API (ENOTFOUND)
```

## Asıl hasar: gürültülü arıza, sessiz kayıp

Hata her satırda görünüyordu ama kimse şunu fark etmedi: toplayıcı **hata dönen
kaynağın boş çıktısını diske yazdı**. 11 dosya da 2 bayta (`[]`) düştü ve bir
önceki günün dolu verisi ezildi.

```
apple_tr_free_apps.json      2 byte
apple_us_free_apps.json      2 byte
...                          (11/11)
```

Sonra `[[ -z "$(ls -A "$SIGNAL_DIR")" ]]` kontrolü **geçti**, çünkü dosyalar
vardı. Boru hattı boş girdiyle ilerledi.

## Kapsam işareti

Aynı pencerede **üç ayrı cron işi** düştü (talep motoru, haber özeti, LinkedIn
postu), hepsi 09:16-10:34 arası. Bu, tek tek iş hatası değil ortam hatası
olduğunun en net göstergesiydi — üç prompt'u tek tek incelemek zaman kaybı
olurdu.

## Uygulanan onarım

| Katman | Değişiklik |
|---|---|
| `daily_radar.sh`, `weekly_board.sh` | ağ ön kontrolü, 30sn×10 deneme, sonra `exit 0` |
| `collect_signals.py` | hatalı kaynağın boş çıktısı **yazılmıyor**, eski dosya korunuyor |
| `collect_signals.py` | hepsi boşsa `sys.exit(2)` — kısmi/toplu kayıp ayrımı |
| `daily_radar.sh` | dosya sayısı yerine **dolu dosya** sayısı kontrolü (`-size +10c`, eşik 3) |
| temizlik | 11 zehirli boş dosya silindi (veri değil, arıza artığı) |

Ağ kontrolünün çıkışı `exit 0`: bu bir kod hatası değil ortam hali, cron'a
kırmızı yakmak yanlış sinyal olur.

## Doğrulama (varsayılmadı, ölçüldü)

Kapalı porta proxy vererek ağsızlık simüle edildi:

```
HTTPS_PROXY=http://127.0.0.1:9
```

Sonuçlar:

```
11 kaynak → hepsi HATA (yazilmadi)
YAZILAN DOSYA SAYISI: 0            ← tek boş dosya bile yazılmadı
CLI exit kodu (agsiz): 2           ← beklenen
```

Eski dosya koruma testi: dizine sahte "ONCEKI GUNUN VERISI" (44 bayt) konup
ağsız koşu çalıştırıldı → **44 bayt, korundu**.

Ağlı regresyon testi: gerçek koşu 11/11 dosyayı dolu getirdi (41 KB oyun
listesi, 37 KB HN, vb.), fail-closed eklemesi ağlı yolu bozmamıştı.

## Kapanmayan taraf

Hermes cron'un kendisinde ağ farkındalığı yok — kaçırılan işi ağ hazır mı diye
bakmadan tetikliyor. Koruma şimdilik her betiğin kendi içinde. Çekirdeğe genel
bir bekleme adımı eklemek kullanıcıya sorulup bırakıldı, kendi başına yapılmadı.
