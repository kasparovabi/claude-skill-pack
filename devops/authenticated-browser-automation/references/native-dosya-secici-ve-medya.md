# Native dosya seçici: medya yüklemenin tek çalışan yolu

Doğrulandığı oturum: 2026-08-05, LinkedIn proje bölümüne görsel/video ekleme.
Genişletildi: 2026-08-13, Personio başvuru formunda iki dosya alanı yüklendi.

Web formunun geri kalanını JS köprüsüyle sürebilirsin ama **dosya yükleme adımı
tarayıcının dışına çıkar**. macOS'un native dosya seçici sheet'i açılır ve o katmanda
hem JS hem `computer_use` işe yaramaz. Bu dosya o duvarın nasıl aşıldığını anlatır.

## Ön koşul: macOS otomasyon izni (ilk çalıştırmada kullanıcı onaylamalı)

**Bu adım atlanırsa aşağıdaki hiçbir reçete çalışmaz** ve hata mesajı sebebi
söylemez — betik sessizce `DOSYA PENCERESI GELMEDI` ya da boş sonuç döndürür.

İlk kez `System Events` üzerinden tuş gönderdiğinde macOS ekranda bir izin
penceresi açar:

> "Terminal" uygulamasının "System Events" uygulamasını kontrol etmesine izin
> verilsin mi?

Kullanıcı **İzin Ver** demeden tuşlar hiçbir yere gitmez. 2026-08-13 oturumunda
bu pencere kullanıcının ekranında açıldı ve o onayladıktan sonra yükleme geçti.

Bunun sonuçları:

- **Kullanıcı makine başında değilse bu iş bitmez.** Uzaktan çalışıyorsan ve
  ilk kez otomasyon izni gerekiyorsa, kullanıcıya "ekranda bir izin penceresi
  çıkacak, onaylaman gerekiyor" diye **önceden** söyle. Sessizce denemek turu yakar.
- İzin uygulama bazlı: Terminal ayrı, iTerm ayrı, Python'u çağıran süreç ayrı.
  Bir kez verilince kalıcıdır.
- Aynı şekilde `tell application "Google Chrome"` ilk çağrıda ayrı bir izin
  ister. İkisi farklı pencerelerdir, ikisi de gerekli.

Verilmiş izinleri görmek/sıfırlamak:
`Sistem Ayarları → Gizlilik ve Güvenlik → Otomasyon`

Programatik kontrol yok; TCC veritabanı korumalı, betikle izin veremezsin.
Tek yol kullanıcının tıklaması.

### İzin penceresini GÖREBİLİRSİN — `app="screen"` ile yakala

2026-08-13'te bu pencereyi "göremiyorum" varsayıp kullanıcıdan haber bekledim.
Yanlıştı. `computer_use(action="capture", app="screen")` masaüstü yüzeyini
yakalar ve **başka uygulamalara ait pencereleri de gösterir** (o an Finder
penceresi geldi). İzin penceresi de oradadır.

Ayrım şu:
- `capture(pid=..., window_id=...)` → yalnızca o Chrome penceresi. İzin
  penceresi burada **görünmez**, çünkü sahibi başka bir süreçtir.
- `capture(app="screen")` → masaüstü yüzeyi, sistem pencereleri dahil.

Doğru refleks: `System Events` çağrısı beklenmedik şekilde sessiz kaldıysa
körlemesine tekrar deneme, **`app="screen"` ile bak**. Ekranda bekleyen bir
onay penceresi varsa anında görürsün ve kullanıcıya tam olarak neyi
onaylayacağını söylersin.

Not: izin penceresine sen tıklama. Görmek teşhis içindir, onay kullanıcının.

## Çalışan reçete (önce bunu oku, denemeye buradan başla)

İki adım, ikisi de zorunlu ve **sırası önemli**:

1. **Sheet'i GERÇEK fare tıklamasıyla aç.** JS `.click()` sheet açmaz (aşağıda ölçüm
   var). `computer_use(action="click", coordinate=[x,y], delivery_mode="foreground",
   pid=..., window_id=...)` kullan.
2. **Sheet açıkken yolu klavyeden yaz.** `scripts/dosya_yukle.py <pencere_id>
   <sekme_no> <dosya_yolu>` — sheet'i taşıyan pencereyi bulur, `Cmd+Shift+G` ile tam
   yolu yazar, iki Enter ile onaylar, sonra alanın gerçekten dolduğunu döndürür.

Birden fazla alan varsa her alan için 1 ve 2'yi tekrarla.

### Adım 1'in ön koşulu: alan EKRANDA GÖRÜNÜR olmalı

2026-08-14'te tur yakan eksik. Gerçek fare tıklaması **ekran koordinatına**
gider, DOM konumuna değil. Alan viewport dışındaysa tıklama başka bir şeye
düşer, sheet açılmaz ve betik doğru şekilde `SHEET YOK` der. Uzun başvuru
formlarında alan `y=13202` gibi bir konumda olabiliyor.

Üç adım, ikincisi atlanamaz:

```js
// 1. gorunur konuma getir
document.querySelectorAll('input[type=file]')[0]
  .closest('div').scrollIntoView({ block: 'center', behavior: 'instant' });
```

```js
// 2. koordinati YENIDEN oku, kaydirma oncesi deger artik gecersiz
var r = document.querySelectorAll('input[type=file]')[0]
          .closest('div').getBoundingClientRect();
JSON.stringify({ x: Math.round(r.left + r.width/2),
                 y: Math.round(r.top  + r.height/2) });
```

3. `computer_use` ile o koordinata `delivery_mode="foreground"` tıklama.

**Üstü kapalı alan tuzağı:** adres alanının otomatik tamamlama açılır listesi
dosya alanının üzerine binmişti ve tıklama listeye gitti. Tıklamadan önce
`Escape` ile açık listeleri kapat, sonra ekran görüntüsüyle alanın gerçekten
göründüğünü doğrula.

**Tıklama noktası kutunun ortası değil, "upload" bağlantısı olabilir.**
Sürükle-bırak kutularında (`Drop your file or upload`) kutunun ortası
tıklanabilir olmayabilir; ekran görüntüsünden altı çizili bağlantı metnini
hedefle.

### Yükleme sonrası: `files` boş görünebilir ama dosya YÜKLENMİŞTİR

Bazı ATS'ler (Teamtailor doğrulandı) seçilen dosyayı anında kendi nesne
deposuna gönderip `input.files` listesini temizliyor ve adresi ayrı bir
alana yazıyor:

```
DOSYA: BOS
candidate[resume_remote_url] = https://...s3.eu-west-1...
```

`files` boş diye tekrar yüklersen ikinci kopya eklersin. Doğrulama iki
kaynaklı olmalı:

```js
var dosyaVar = [].slice.call(document.querySelectorAll('input[type=file]'))
  .some(function(e){ return e.files && e.files.length; });
var uzaktaVar = [].slice.call(document.querySelectorAll('input'))
  .some(function(e){ return /remote_url/i.test(e.name || '') && e.value; });
(dosyaVar || uzaktaVar) ? 'YUKLENDI' : 'BOS';
```

Görsel doğrulama da geçerli: yüklenen dosyanın adı alanın altında listelenir.

## İki kritik tuzak (2026-08-13'te ölçüldü)

### Tuzak 1: JS `.click()` sheet'i AÇMAZ, sessizce hiçbir şey yapmaz

Alan DOM'da mevcut olsa bile `f[0].click()` çağrısı `'ok'` döner ve **hiçbir sheet
açılmaz**. Chrome dosya seçiciyi yalnızca güvenilir kullanıcı hareketiyle açar.

Ölçüm — tıklamadan sonra sheet sayısı altı ayrı anda yoklandı:

```
tik: ok
t=0.5s -> 1=0 2=0 3=0
t=1.0s -> 1=0 2=0 3=0
t=2.0s -> 1=0 2=0 3=0
t=3.0s -> 1=0 2=0 3=0
t=5.0s -> 1=0 2=0 3=0
t=8.0s -> 1=0 2=0 3=0
```

Aynı alana `computer_use` ile gerçek fare tıklaması gönderilince sheet **anında**
açıldı. Yani gecikme veya zamanlama sorunu değil, yetki sorunu.

> **Kural: dosya seçiciyi açan tıklama gerçek fare olayı olmalı.** JS tıklamayla
> uğraşma, tur yakar.

### Tuzak 2: sheet her zaman `window 1`'de değil

İlk denemelerim `DOSYA PENCERESI GELMEDI` ile düştü çünkü yalnızca 1. pencereye
bakıyordum. Sheet 2. penceredeydi. 1. pencere ise açık kalmış bir "sayfada bul"
çubuğuydu:

```
sheet dagilimi: 1=0 2=1 3=0 4=0
pencere adlari: 1:Şu sayfada bul: ... | 2:AI Solution Builder | Jobs bei Hypatos ...
```

**Bütün Chrome pencerelerini tara, sheet'i taşıyanı bul.** Betik bunu yapıyor.

### Not: `Cmd+Shift+G` sheet odakta değilken Chrome'un arama çubuğuna gider

Kısayolu sheet açılmadan önce göndermek işe yaramaz, tuşlar sayfaya düşer ve
adres/arama çubuğu açılır. Önce sheet'in gerçekten var olduğunu doğrula, sonra yaz.

## Chrome 136+ : CDP yolunu deneme, kapalı

`DevToolsActivePort` dosyası varsayılan profilde **duruyor** ve `9222` yazıyor,
port da gerçekten dinleniyor:

```
Google 9130 kasparov 286u IPv4 TCP 127.0.0.1:9222 (LISTEN)
```

Buna rağmen HTTP ucu `404` döner ve WebSocket el sıkışması zaman aşımına uğrar.
`suppress_origin`, `Host` başlığı, `localhost` / `127.0.0.1` varyasyonları denendi,
hiçbiri geçmedi. Varsayılan profilde bu uç kasıtlı kapalı.

`DOM.setFileInputFiles` bu iş için doğru araç olurdu ama ulaşılamıyor. **Buraya
yatırım yapma**, yukarıdaki gerçek-tıklama + `Cmd+Shift+G` yoluna geç. `computer_use`
typed-browser rung'ı da kendi tarayıcısını kurmak ister (`browser_requires_setup`);
kullanıcının dolu formunu kaybettireceği için oturum ortasında uygun değil.

## Katman katman ne çalışmıyor

### 1. JS ile file input'a ulaşmak — imkânsız
```javascript
document.querySelector('input[type=file]')   // → null
```
Buton tıklanmadan file input DOM'da yok. Tıkladıktan sonra da yok: LinkedIn önce bir
**menü** açıyor (`Bağlantı ekleyin` / `Resim ekleyin` / `Belge ekleyin`), file input
ancak o menüden seçim yapılınca oluşuyor ve anında native sheet'e devrediyor.

`b.click()` sonrası ölçüm: `fileinputs=0`, `dialogs=0`. **Ama menü gerçekten açılmıştı** —
JS tıklama çalıştı, sadece DOM'a yansımadı. Bunu ancak `mode="vision"` capture ile
gördüm. Ders: JS sorgusu boş dönünce "tıklama tutmadı" diye karar verme, GÖZLE bak.

File input'u zorla görünür yapıp tıklatma numarası da (`style.display='block'` + sentetik
click) burada işe yaramıyor; input hiç var olmuyor ki.

### 2. `computer_use` ile sheet'i sürmek — ulaşmıyor
Native sheet açıldıktan sonra `computer_use` girdileri o pencereye **hiç geçmiyor**.
Denenen ve hepsi sessizce başarısız olan:

| Eylem | Sonuç |
|---|---|
| `click` (klasör ikonuna) | ekran değişmedi |
| `double_click` (klasör ikonuna) | ekran değişmedi |
| `type` (arama kutusuna) | hiçbir karakter girmedi |

Hepsi `effect: unverifiable` döndü — yani driver "gönderdim ama doğrulayamıyorum" dedi
ve gerçekten hiçbir şey olmadı.

### 3. AX ağacı da kapalı
```
WIN:... sheets=1
SHEET VAR
  buttons=0
  textfields=0
```
Sheet **var** ama içi erişilebilirlik ağacına açılmıyor. Yani `element=N` ile hedefleme
yolu da yok. Bu yüzden bu skill'in "element index tek güvenilir yol" kuralı native
sheet'te GEÇERSİZ.

## Çalışan yol: düz `System Events` keystroke

Anahtar fark: `tell process "Google Chrome"` ile sarmalamak yerine **uygulamayı
`activate` edip düz `System Events`'e yazmak**.

```applescript
on run argv
  set filePath to item 1 of argv
  tell application "Google Chrome" to activate
  delay 1.2
  tell application "System Events"
    keystroke "G" using {command down, shift down}   -- "Klasöre Git"
    delay 2
    repeat with c in characters of filePath           -- KARAKTER KARAKTER
      keystroke (c as string)
      delay 0.012
    end repeat
    delay 1.2
    keystroke return                                  -- yolu onayla
    delay 2.5
    keystroke return                                  -- dosyayı aç
    delay 5
  end tell
  return "ok"
end run
```

Çalıştır: `osascript /tmp/pick.scpt "/Users/<kullanici>/Downloads/klasor/dosya.png"`

Aynı işi yapmaya çalışıp **başarısız olan** ilk sürümle farkları — hangisinin tek başına
belirleyici olduğunu izole etmedim, dördünü birden uygula:

1. `tell application "Google Chrome" to activate` + `delay` ile **önce odağı ver**
   (başarısız sürümde bu yoktu, `tell process ... click at {x,y}` vardı)
2. `keystroke filePath` yerine **karakter karakter** yaz (toplu keystroke uzun yolda
   karakter düşürüyor)
3. `key code 36` yerine `keystroke return`
4. Adımlar arasında cömert `delay` — sheet ağır açılıyor, 2 sn altına inme

## Yol yazmak > klasörde gezinmek

`Cmd+Shift+G` ("Klasöre Git") kutusuna tam yolu yazmak, seçicide tıklaya tıklaya
ilerlemekten kat kat güvenilir. Zaten tıklama ulaşmıyor (yukarı bak), dolayısıyla
**tek gerçekçi seçenek bu**.

`/tmp` altındaki dosyalar için de çalışıyor; dosyaları `~/Downloads` altına kopyalamak
şart değil. (Bu oturumda kopyaladım ama gerekliliği kanıtlanmadı — gereksiz adım.)

## Yükleme sonrası: meta veri formu web katmanına geri döner

Dosya seçildikten sonra LinkedIn "Medya ekleyin" başlıklı **web modalı** açıyor:
`Başlık*` (zorunlu, 200 karakter) + `Açıklama` + önizleme + `Kaydet`.

Burası artık normal DOM, JS köprüsüyle doldurulur:

```javascript
var ti = document.querySelector('input[type=text]');   // Başlık
var ta = document.querySelector('textarea');           // Açıklama
```
Native setter kalıbını kullan (bkz. `toplu-duzenleme-js-koprusu.md`) ve `Kaydet`
öncesi `b.disabled` kontrol et — başlık boşsa buton pasif.

## Medya varlığının KENDİSİNİ doğrula: mockup ≠ kanıt

Diskte bulduğun bir görseli portföye koymadan önce **aç ve bak**. Bu oturumda
`sceneshift/design-mockup.png` dosyası ilk bakışta ideal aday görünüyordu; açınca
AI ile üretilmiş bir mockup olduğu ve metinlerinin uydurma karakterler taşıdığı
görüldü: `"Write your tesforipril og"`, `"entornarit gnasecoloes"`.

Böyle bir görseli profile koymak doğrudan zarar verir — bakan ilk kişi fark eder.

**Doğrusu: uygulamayı çalıştır, gerçek arayüzü çek.**
```bash
# uzak makinede uygulamayı ayağa kaldır, sonra:
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --disable-gpu --window-size=1600,1000 \
  --virtual-time-budget=9000 \
  --screenshot=/tmp/gercek_arayuz.png "http://<host>:<port>/"
```
Gerçek arayüz mockup'tan iyi çıktı: metinler doğru Türkçe (`Kaynak Görsel`,
`Hedef Arkaplan`, `Dönüştür`), düzen tutarlı.

Bu ayrıca beklenmedik kazanç sağladı: the client platformunun ekran görüntüsünü alınca
dairenin **14 dijital uygulamasını** tek dizinde topladığı ve 12'sinin aktif olduğu
görüldü. Bu bilgi proje açıklamasını yeniden yazdırdı. Ekran görüntüsü sadece görsel
değil, **olgu kaynağı**.

`--headless` çağrısını `terminal` içine gömerken uzun tırnaklı komut "embedded null
byte" hatası verebiliyor; komutu bir `.py` dosyasına yazıp `subprocess.run` ile
çalıştırmak temiz çözüm.

## Animasyonlu SVG'yi PNG'ye çevirirken: ilk kare boş çıkar

Depo içindeki demo görselleri sık sık CSS animasyonlu SVG oluyor. `rsvg-convert` ile
düz çevirince **boş/şeffaf** PNG üretiliyor, çünkü kareler `opacity: 0` ile başlayıp
animasyonla görünür hale geliyor.

Çözüm — istediğin kareyi zorla görünür yap:
```python
s = open("demo.svg", encoding="utf-8").read()
s = s.replace(".frame { opacity: 0; }",
              ".frame { opacity: 0; } .f4 { opacity: 1 !important; animation: none !important; }")
```
Sonra `rsvg-convert -w 1400 -h 840 out.svg -o out.png`.

Dosya boyutu doğrulama aracın: boş PNG ~10 KB, dolu olan ~100 KB çıktı.

**Hangi kareyi seçeceğine içeriğe bakarak karar ver.** İlk kare genelde kurulum/başlangıç
ekranı olur ve aracın ne işe yaradığını anlatmaz; asıl değerli kare çıktının göründüğü
son karelerdir. Bu oturumda 1. kare kurulum, 4. kare aracın keşfettiği iş akışı
örüntüleriydi — 4'ü seçildi.

## Video: LinkedIn'e göndermeden önce küçült

Kaynak 60 MB / 1080x1920 idi. Limit içindeydi ama gereksiz büyüktü:
```bash
ffmpeg -i kaynak.mp4 -vf "scale=720:-2" -c:v libx264 -crf 26 -preset fast \
  -c:a aac -b:a 96k cikti.mp4
```
60 MB → 11 MB, görünür kalite kaybı yok.
