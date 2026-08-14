---
name: authenticated-browser-automation
description: "Drive the user's own logged-in browser to edit web accounts."
version: 1.0.0
platforms: [macos]
metadata:
  hermes:
    tags: [computer-use, browser, chrome, applescript, gui-automation]
    category: devops
---

# Kullanıcının oturumu açık tarayıcısında iş yapmak

Kullanıcı "kendi tarayıcımdan bağlan ve şunu yap" dediğinde. Tipik: LinkedIn profili
düzenlemek, bir panele giriş yapıp ayar değiştirmek, oturum gerektiren bir formu
doldurmak.

Headless tarayıcıda çözülmez, çünkü işin tamamı kullanıcının **mevcut oturum
çerezlerine** dayanıyor. `computer_use` ile kullanıcının gerçek Chrome'unu arka planda
sürmek gerekir. `macos-computer-use` skill'i temel akışı anlatır; bu skill oturumlu
web uygulamalarına özgü tuzakları ekler.

## 0. Sınır: neyi yapıp neyi yapmayacağın

İşi ikiye ayır ve kullanıcıya da böyle sun:
- **Mekanik olan** (sıralama değiştirme, madde silme, kutu işaretleme): karar zaten
  verilmiş, git yap.
- **Kullanıcının sesi olan** (profil metni, bio, açıklama, gönderilecek mesaj): önce
  taslağı göster, onay al. Kullanıcı hakkında **doğrulanmamış olgu yazma** — kullandığı
  araçlar, sertifikaları, süreler. İlk görüşmede aleyhine döner.

Kullanıcı açıkça "hepsini sen yap, sonra bakarım" derse mekanik kısımda serbestsin ama
metin taslağını yine de ölçümle birlikte raporla.

Asla dokunma: şifre alanları, ödeme ekranları, 2FA, izin diyalogları, silme onayları.

## 1. Chrome'a bağlan — pencere kimliği iki farklı sistemde

Bu iki numara **aynı değil** ve karıştırmak saatler yakar:

| Kaynak | Örnek | Nerede kullanılır |
|---|---|---|
| `computer_use action=list_windows` | `window_id: 31602` | `computer_use` çağrılarında (`pid` ile birlikte) |
| AppleScript `id of window` | `444136678` | `osascript` içinde |

`computer_use` ile capture alırken **`pid` ve `window_id` İKİSİNİ birden** ver.
Sadece `app="Google Chrome"` vermek boş sonuç döndürebilir (0x0, 0 element) çünkü
birden fazla pencere var ve hangisi olduğu belirsiz.

```
computer_use(action="list_windows", app="Google Chrome")
# başlıktan doğru pencereyi seç, sonra:
computer_use(action="capture", mode="ax", pid=67022, window_id=31602, max_elements=90)
```

### Hangi sekmede olduğunu AppleScript ile bul
Sekme listesini taramak `computer_use`'dan hızlı ve güvenilir. Script'i **dosyaya yaz**,
`osascript /tmp/x.scpt` ile çalıştır — inline heredoc `&` yüzünden terminal aracına
takılıyor.

```applescript
tell application "Google Chrome"
  set out to ""
  set wi to 0
  repeat with w in windows
    set wi to wi + 1
    set out to out & "win " & wi & " id=" & (id of w) & " title=" & (title of w) & linefeed
  end repeat
  return out
end tell
```
Sonra hedef sekmeye geç: `set active tab index of w to N`.

## 2. Etkileşim: element index tek güvenilir yol

- **Piksel koordinatı doğrudan kullanma — capture ile AX uzayı farklı ölçekte.**
  Capture 1455x795 raporlarken AX sınırları 1920x1049 uzayında ve negatif y taşıyor.
  Ekran görüntüsünden okuduğun koordinat hedefi ıskalar. Öncelik `element=N`.
  Element index alınamıyorsa koordinatı **çevir**, elle tahmin etme:
  ```python
  # AX pencere bounds: [ax_x, ax_y, ax_w, ax_h], capture: img_w x img_h
  sx, sy = ax_w / img_w, ax_h / img_h
  gercek_x, gercek_y = ax_x + goruntu_x * sx, ax_y + goruntu_y * sy
  ```
  Bu dönüşümle piksel tıklama güvenilir çalışıyor; tekrarlayan döngülerde (aynı
  konumdan liste boşaltma) index yenilemekten daha ucuz.
- **Her state değişiminden sonra yeniden capture al.** Index'ler snapshot'a bağlı; bir
  madde silindiğinde sonraki maddeler yukarı kayar. Aynı index'e ikinci kez basmak
  farklı bir şeyi siler — bu aslında işe yarar (listeyi hep aynı index'ten
  boşaltabilirsin) ama bilerek yap.
- `element` verirken driver **snapshot_id / element_token** isteyebiliyor
  (`bare element_index is not accepted`). Çözüm: hemen öncesinde taze capture al.

### AX çıktısı devasa olabilir
Tam liste 200 KB'ı geçip context'i doldurur. `max_elements` ile kıs. Belirli bir
butonu arıyorsan çıktı dosyaya kaydedildiğinde `execute_code` ile filtrele:

```python
import json
d = json.load(open(PERSISTED_PATH, encoding="utf-8"))
for e in d["elements"]:
    if "Kaydet" in (e.get("label") or ""):
        print(e["index"], e["role"], e["bounds"])
```

## 3. Metin yazma: `set_value` > `type`

> React/SPA formlarında (LinkedIn, Notion, modern paneller) **zengin metin kutusuna
> DOM'dan JS ile yazma.** Doğrulanmış kural: `execCommand`/`insertBefore`/`dispatchEvent`
> ekranda çalışıyor görünür ama kayıt eski değeri gönderir. AX katmanından `set_value`
> kullan. Tam reçete, `<select>` istisnası ve `same_pid_keyboard_ambiguity` reddinin
> çözümü: `references/zengin-metin-editoru-ve-kayit-dogrulama.md`
>
> **İSTİSNA — düz `input`/`textarea` alanlarda native setter genelde çalışır.**
> Yukarıdaki yasak `contenteditable` zengin metin kutuları içindir. Düz alanlarda
> `HTMLInputElement.prototype.value` setter + `input`/`change` olayları React 19 /
> RSC formlarında da alanı doldurur. **Önce alanın türünü ayır, sonra yol seç.**
>
> **AMA alanı doldurmak kaydın kabul edileceğini GARANTİ ETMEZ.** Aynı setter,
> aynı sitede bir formda kaydı geçirir, başka bir formda geçirmez — çünkü
> darboğaz istemci tarafı değil, **sunucunun o uç noktayı kabul edip etmemesi**.
> 2026-08-09 doğrulanmış vaka: LinkedIn Hakkında formunda geçti, Projeler
> **düzenleme** formunda 8 yöntemin hiçbiri geçmedi, aynı sitenin Projeler
> **ekleme** formunda ilk denemede geçti. Alanın dolması ara sonuç, kabul testi
> değil — aşağıdaki "yaz-oku uçurumu" bölümünü oku.
>
> **Kaydın tuttuğunu YANLIŞ yerden doğrulamak, çalışan yöntemi \"başarısız\" gösterir.**
> Aynı oturumda 7 yöntem \"tutmadı\" sanıldı; gerçekte kayıt geçmişti, liste sayfası
> bayattı. Ağdan doğrulama, `fetch` monkeypatch hook'unun yalancı negatifi ve React 19
> tespiti: `references/sdui-rsc-form-kaydi-dogrulama.md`

- **`set_value` tercih et.** Uzun metni tek seferde yerleştirir, Türkçe karakterleri
  bozmaz. `effect: unverifiable` dönse bile genelde başarılıdır — `mode="vision"`
  capture ile GÖZLE doğrula, tekrar gönderme.
- **`type` tuzağı: metin iki-üç kez yazılıyor.** Arka planda `delivered 0 of N` deyip
  başarısız görünüyor, foreground'a çıkınca gönderiyor ama önceki denemeler de
  birikmiş oluyor. Sonuç: `AI AgentsAI AgentsAI Agents`.
  - Sonuç ne olursa olsun **önce capture al ve alanın gerçek içeriğini oku**.
  - Yeniden yazmadan önce `cmd+a` ile alanı temizle.
  - Otomatik tamamlamalı alanlarda (yetenek, etiket, konum) `type` özellikle sorunlu;
    liste açılıp seçim beklediği için tekrar denemeler üst üste biniyor.

### Panodan yapıştırırken BOŞ SATIRLAR yutuluyor

Çok paragraflı metni `pbcopy` + `cmd+v` ile yapıştırdığında editör boş paragrafları
siliyor; metin doğru ama tek blok hâlinde, paragraf araları yok. Kullanıcı bunu
"hiç satır aralığı bırakmamışsın" diye fark eder ve haklıdır.

Çözüm: boş satırlara **kırılmayan boşluk** (`\u00a0`) koy. Editör onu "içi olan
paragraf" sayıp korur, ekranda normal boşluk gibi görünür ve ham `&nbsp;` kodu
sızmaz (2026-08-09'da LinkedIn Hakkında bölümünde iki dilde de gözle doğrulandı).

```python
NB = "\u00a0"
def bosluklu(metin):
    p = [x.strip() for x in metin.strip().split("\n\n") if x.strip()]
    return ("\n" + NB + "\n").join(p) + "\n"
```

Yapıştırdıktan sonra `mode="vision"` capture al ve paragrafların gerçekten ayrı
göründüğünü **gözle** kontrol et. Karakter sayısının doğru olması biçimin doğru
olduğunu göstermez.

## 4. Onay ver ve doğrula

Kaydet'e bastıktan sonra `mode="vision"` capture al ve **sayfada canlı görünen değeri**
oku. `effect: unverifiable` bir başarısızlık kanıtı değil, sadece driver'ın
doğrulayamadığı anlamına geliyor — kör tekrar tıklama yapma, önce bak.

### Doğrulamayı YANLIŞ yerden yapmak en pahalı hata

Bir yöntemi "tutmadı" diye elemeden önce **doğru yerden baktığından emin ol.**
2026-08-09'da 7 farklı yöntem başarısız sanıldı; hepsi liste sayfasından
doğrulanmıştı ve liste bayattı. 8. yöntem aslında 2. yöntemin aynısıydı — sadece
doğru yerden doğrulandı.

Doğrulama sırası (ucuzdan pahalıya):
1. **Karakter sayacı** (`37/255` gibi) — React state güncellendi mi, bedava kanıt.
2. **Resource Timing** — kayıt isteği gerçekten gitti mi ve `transferSize` dolu mu.
3. **Düzenleme formunu sunucudan taze çek** (`cache:'no-store'`) — asıl kabul testi.

Liste/özet sayfasında eski metin görmek **kaydın tutmadığını kanıtlamaz.**
Ayrıntı: `references/sdui-rsc-form-kaydi-dogrulama.md`

### Tersi de doğru: düzenleme formunda yeni metin görmek kaydı KANITLAMAZ

Düzenleme formunu tekrar açtığında yeni değeri görmen, verinin sunucuya geçtiği
anlamına gelmez — istemci durumu sayfa yenilense bile yaşayabiliyor. 2026-08-09'da
silme onay diyaloğu bile yeni İngilizce başlığı okudu, buna rağmen sunucuda eski
Türkçe metin duruyordu ve kullanıcı ertesi gün "hâlâ Türkçe" diye döndü.

**Tek geçerli kabul testi:** sekmeyi `set URL` ile tam yeniden yükle (`delay 12`)
ve liste/profil sayfasından oku.

### Tıkandığında: yeni yöntem deneme, AYIRICI TEST yap

Aynı yazma yöntemini varyasyonlarla tekrar denemek (setter → pano → AXPress →
piksel → JS click) teşhis üretmez, sadece tur yakar. Bunun yerine **sahte bir
kayıt EKLE** ve listede görünüyor mu bak:

- Görünüyorsa → liste taze, sorun **düzenleme uç noktasının reddi** → sil+ekle.
- Görünmüyorsa → sorun okuma tarafında, önbellek/dil sürümü araştır.

Sonra sahte kaydı hemen sil. Bu üç çağrı, 8 başarısız yazma denemesinden daha
çok bilgi verir. Tam reçete: `references/yaz-oku-ucurumu-ve-sil-ekle.md`

### "Aynı yöntemi tekrar deneme" kuralının sınırı

`Pitfalls` altındaki "aynı çağrıyı üçüncü kez deneme" kuralı **çağrı tekrarı** içindir.
Doğrulama yöntemini değiştirmek tekrar sayılmaz — tersine, tıkandığında yapılacak
ilk iş budur. Yöntemi değiştirmeden önce **ölçüm noktasını** değiştir.

### Alan DOLU ama form "boş" diyor: `customError` takılı kalması

Yukarıdaki "yaz-oku uçurumu" alanın **dolmasıyla** ilgiliydi. Bu tuzak bir adım
sonrası: alan gerçekten dolu, gözle görüyorsun, ama Gönder düğmesi çalışmıyor ve
tarayıcı **"Please fill out the details"** diyor.

Refleks yanlış olur: metni tekrar yapıştırmak, farklı setter denemek, alanı
temizleyip yeniden yazmak. Hiçbiri işe yaramaz çünkü sorun metinde değil.

**Önce hangi doğrulama kuralının patladığını ÖLÇ** — üç satır, bedava:

```js
d.value.length           // 3317  -> alan gerçekten dolu
d.validity.valueMissing  // false -> "boş" değil
d.validity.customError   // true  -> İŞTE SORUN BU
d.validationMessage      // "Please fill out the details"
```

`customError: true`, sitenin **kendi** doğrulama kodunun alana bir hata bayrağı
bıraktığı ve metin dolduktan sonra temizlemediği anlamına gelir. Kullanıcı o
sırada tarayıcıya dokunduysa (sekme değiştirdi, tıkladı, pencereyi öne aldı) bu
kolayca oluşur — yani senin yazma yöntemin doğruydu, araya insan girdi.

Çözüm tek satır:

```js
if (d.validity.customError) d.setCustomValidity('');
// sonra d.checkValidity() anında true döner
```

2026-08-10 doğrulanmış vaka: 3.317 karakterlik rapor alanı defalarca yeniden
yapıştırıldı, her seferinde form reddetti. Bayrak düşürülünce ilk denemede geçti.
Kaybedilen tur sayısı: metni yeniden doldurma denemeleri + boş satır silme +
foreground tıklama denemeleri.

> **Kural: "alan boş" hatası aldığında alanın içeriğine değil,
> `validity` nesnesine bak.** Hangi bayrağın kalktığını bilmeden yaptığın her
> düzeltme kör atıştır.

Sıra: `valueMissing` → gerçekten boşsa doldur. `customError` → bayrağı düşür.
`tooShort`/`patternMismatch` → içeriği düzelt. Bunlara bakmadan yöntem değiştirme.

Hazır teşhis betiği (elle yazma): `scripts/form_dogrulama_teshis.js` — formdaki
tüm alanları tarar, gönderimi hangisinin bloke ettiğini ve sebebini basar, takılı
`customError` bayraklarını düşürür.

### Gönderimin tuttuğunu URL + API ile doğrula

"Düğmeye tıklandı" bir sonuç değildir. JS `click()` çağrısı `TIKLANDI` dönse bile
form doğrulamada takılıp aynı sayfada kalabilir. İki bağımsız kanıt iste:

1. **URL değişti mi?** `.../new` gibi bir oluşturma adresinde kaldıysa gönderim
   TUTMADI, kayıt hâlâ taslak.
2. **Kaynağın kendi API'sinden oku.** Oluşan kaydın kimliğiyle sorgula ve
   durumunu gör. Bu, istemci tarafındaki her yanılsamayı eler.

### Var olan kaydı DÜZELTMEK: yenisini ekleme, düzenle

Gönderdiğin bir yorumun/kaydın içeriği yanlışsa altına ikinci bir tane ekleme.
Okuyucu ikisini birden görür ve hangisinin geçerli olduğu belirsiz kalır.

Düzenleme akışı: kaydın sağ üstündeki **üç nokta menüsü** → `Edit` → aynı native
setter yöntemiyle metni değiştir → `Update comment` / `Save`.

Üç nokta menüsünü ararken kaydın **kendi** DOM alt ağacında arama, orada
bulunmayabilir; menü genelde kardeş bir başlık öğesindedir. Alt ağaçta düğme
çıkmazsa `mode="vision"` capture al ve menüyü gözle bul, sonra koordinatla tıkla.

Doğrulama: yeni metne özgü bir dizeyi (ör. bir sayı) sayfada ara.

```js
var y = [].slice.call(document.querySelectorAll('[id^=comment-]'))
          .filter(function(x){ return (x.innerText||'').indexOf('<ayirt-edici>')>-1; });
y.length ? (y[0].innerText.indexOf('14,139')>-1 ? 'YENI' : 'ESKI') : 'yok';
```

**Aynı içerik iki yerde yayınlandıysa ikisini de güncelle.** 2026-08-10'da bir
takip özeti hem GitHub yorumunda hem kendi depomdaki yazıda duruyordu; yalnız
depo yazısını düzelttim, kullanıcı eski metni gördü ve "hâlâ eski yazı
görünüyor" diye döndü. Bir metni düzelttiğinde nerelerde kopyası olduğunu
listele ve hepsini aynı turda kapat.

## Yazma işlemi API'den kapalı olabilir — okuma açıkken

Bir platformda `gh`/REST ile onlarca işi arka planda yapabiliyor olman, **her**
işi yapabileceğin anlamına gelmez. Bazı yazma uçları bilinçli olarak insan
onayına bağlanmıştır ve tarayıcı şarttır.

Doğrulanmış vaka (2026-08-10, GitHub güvenlik danışmanlığı): PR açmak, yorum
yazmak, fork'lamak API'den sorunsuz. Güvenlik raporu göndermek ve gelen krediyi
kabul etmek **403**. Kendi deposunda, özel bildirimi kendi açmış olmasına rağmen
403. Sebep yetki eksikliği değil, kasıtlı kısıt (bot üretimi sahte rapor akınına
karşı). Token'a yetki eklemek çözmez.

**Ayrım genelde şu şekilde:** okuma tarafı API'den çalışır (listeleme, tam metin
okuma, durum sorgulama — ön kontrolleri bununla yap), yazma tarafı tarayıcı ister.

Refleks: bir yazma ucu 403/500 döndüğünde önce **kendi kaynağında test et**. Orada
da reddediyorsa bu bir yetki sorunu değil, ürün kararıdır — tarayıcı yoluna geç,
token yetkisiyle uğraşma.

## LinkedIn'e özgü tuzaklar

- **Çok dilli profil: her bölüm dil sürümü tutmuyor.** Hakkında/başlık bölümü
  ayrı ayrı `English` / `Turkish` sürümü saklar (düzenleme kutusunda sekme olarak
  görünür, `?locale=en_US` parametresi bunu DEĞİŞTİRMEZ — sekmeye tıklamak gerekir).
  **Projeler bölümünde düzenleme kutusunda dil sekmesi ÇIKMIYOR** (Hakkında'da
  çıkıyor). Hedef kitle yurt dışıysa İngilizce yaz. Birincil dili İngilizce
  yapmak, dili eşleşmeyen her ziyaretçiye İngilizce sürümü gösterir.

  > **ÇÖZÜLDÜ (2026-08-09) — projelerde DÜZENLEME kaydı sessizce reddediliyor,
  > EKLEME çalışıyor.** Sekiz farklı yazma yöntemi (native setter, pano+gerçek
  > klavye, AXPress, piksel tıklama, alanı kirletme, JS `.click()`) denendi;
  > hepsinde form doluyor, kutu kapanıyor, hata çıkmıyor ve **profil sayfası
  > değişmiyordu**. Düzenleme formu kendi içinde yeni metni gösterdiği için
  > "kaydedildi" sanıldı — form içeriği yalnızca istemci durumuydu.
  >
  > Doğru teşhis ve çalışan çözüm: `references/yaz-oku-ucurumu-ve-sil-ekle.md`
  > Özet: **sahte bir kayıt EKLE** (`ZZTEST`), listede görünürse önbellek suçlu
  > değildir → düzenleme uç noktası reddediyordur → **sil + yeniden ekle**
  > döngüsüne geç. Bu döngüyle 7 proje tek turda çevrildi, tarih `<select>`
  > alanları dahil 4/4 oturdu, tazelenmiş listeden doğrulandı.
- **Toplu bölüm çevirisi / düzenlemesi yapacaksan** doğrulanmış üç adımlı döngü
  (liste → kalem `aria-label` → native setter + Kaydet) ve **liste sayfasının
  bayat olduğu** tuzağı: `references/toplu-duzenleme-js-koprusu.md` →
  "Doğrulanmış toplu düzenleme döngüsü".
- **Form URL'ine doğrudan gitmek çalışmıyor.** `/edit/forms/projects/<id>/`
  adresine `set URL` ile gitmek "Böyle bir sayfa yok" döndürüyor. Form yalnızca
  liste sayfasındaki kalem düğmesiyle açılır.

- **Öne çıkan 5 yetenek ayrı bir ekranda değil**, "Hakkında kısmını düzenle" kutusunun
  içinde, metin alanının altında. Hakkında metnini yazdığın kutuda hem metin hem
  yetenekler var; ikisi tek Kaydet ile geçiyor.
- Yetenek kaldırma butonlarının erişilebilirlik etiketi
  `"<Yetenek adı> yeteneğini listeden kaldır"` biçiminde — arama yaparken bunu kullan.
- Başlık alanı `AXTextArea`, Hakkında alanı `AXTextField` olarak görünebiliyor; role'e
  göre değil label içeriğine göre bul.
- Sayfa kendi kendine odak değiştirebiliyor (bir tıklama sonrası "Action caused a
  different app to become frontmost"). Devam etmeden önce AppleScript ile doğru sekmeye
  geri dön.
- Chrome'un "Apple Events'ten JavaScript'e izin ver" ayarı varsayılan olarak KAPALI.
  **Birkaç alan düzenleyeceksen** doğrudan AX ağacıyla çalış, ayarı kurcalama.
  **Ama 20+ maddelik toplu işlem yapacaksan durum tersine döner** — aşağıdaki
  "Araç çağrısı bütçesi" bölümünü oku.

## Araç çağrısı bütçesi: asıl darboğaz bu

Doğrulanmış maliyet: tek bir liste maddesini silmek **4 çağrı** eder (kalem ikonu →
sil → onay diyaloğu → doğrulama capture'ı). Kaydırma çalışmıyorsa her adıma bir
capture daha binir. 7 madde sildiğinde 28+ çağrı harcanmış olur; iterasyon limitine
iş bitmeden çarparsın ve kullanıcıya yarım rapor vermek zorunda kalırsın.

**Önden kestir.** İşe başlamadan madde sayısını say ve 4 ile çarp. 20'yi geçiyorsa AX
tıklama yolu yanlış araçtır. Sırayla dene:

1. **Chrome JS köprüsü.** Kullanıcıdan Görünüm → Geliştirici → "Apple Events'ten
   JavaScript'e izin ver" kutusunu **bir kez** işaretlemesini iste. Tek tıklık iş,
   tarayıcı kapanmıyor, sonrası tek `osascript` ile hallolur. Bunu istemek sürtünme
   değil, 20 tur pinpon oynamak sürtünmedir.
   - Menüyü programatik tıklamayı deneme, tutmuyor (Chrome bilinçli koruyor).
2. **Uzaktan hata ayıklama portu.** Chrome'u `--remote-debugging-port` ile yeniden
   başlatmak. Oturum korunur ama tarayıcıyı kapatıp açmak gerekir — kullanıcı
   çalışıyorsa rahatsız edici.
3. Hiçbiri olmuyorsa AX ile devam et ama **kullanıcıya baştan söyle** bunun turlara
   yayılacağını; iş bitmeden limit yiyip sessizce kesilmekten iyidir.

### "Claude for Chrome eklentisini kullansana"
Kullanılamaz. O uzantı kullanıcının kendi Claude hesabıyla, tarayıcının içinde çalışır
ve dışarıya programatik bir uç açmaz. Ona yazmak araya ikinci bir ajan katmanı sokar:
yavaşlar, kontrol kaybolur, kullanıcının kotasından düşer. Net şekilde "bağlanamam,
sebebi şu" de ve JS köprüsüne yönlendir.

### JS'i AppleScript string'ine gömme — DOSYADAN okut

Kesme işareti / tırnak yüzünden çağrının sessizce `missing value` dönmesi sorunu
(bkz. `references/toplu-duzenleme-js-koprusu.md`) **tamamen ortadan kalkıyor** eğer
JS'i dosyaya yazıp AppleScript'e okutursan. Kaçış katmanı hiç oluşmaz; Türkçe metin
ve kesme işareti serbestçe kullanılabilir.

```applescript
on run argv
	set wid to (item 1 of argv) as integer
	set tidx to (item 2 of argv) as integer
	set jsf to item 3 of argv
	set jsCode to (read POSIX file jsf as «class utf8»)
	tell application "Google Chrome"
		set w to (first window whose id is wid)
		return (execute (tab tidx of w) javascript jsCode)
	end tell
end run
```
`osascript /tmp/lk_exec.scpt 444142723 9 /tmp/probe.js`

`as «class utf8»` şart — onsuz Türkçe karakterler bozulur. Sondaları küçük ayrı `.js`
dosyaları hâlinde tut, tek harness ile hepsini çalıştır.

## Sayfayı KİLİTLEYEN kod: MutationObserver kendi kendini tetikler

Sayfa içeriği sürekli yeniden çiziliyorsa (canlı önizleme, SPA yeniden render)
refleks olarak `MutationObserver` kurup "her değişimde düzeltirim" demek cazip.
**Bu tuzak, sayfayı tamamen dondurur.**

Sebep: gözlemcinin çağırdığı fonksiyon DOM'a dokunuyorsa o dokunuş yeni bir
mutasyon üretir, o da gözlemciyi tetikler, sonsuz döngü. Sayfa yanıt vermez ve
`osascript` şu hatayı döndürür:

```
execution error: Google Chrome bir hatayla karşılaştı:
AppleEvent zaman aşımına uğradı. (-1712)
```

Bu hata mesajı yanıltıcı: AppleScript'te ya da izinlerde sorun yok, **sayfanın
JS iş parçacığı meşgul**, cevap veremiyor.

### Donmuş sekmeyi kurtarma

Yeniden yükleme yetmez, yükleme de aynı koda düşer. Sekmeyi boş sayfaya sürüp
JS bağlamını öldür:

```bash
osascript -e 'tell application "Google Chrome"
  set URL of tab N of (first window whose id is <WID>) to "about:blank"
end tell'
sleep 6
# canlılık testi: cevap geliyorsa sekme kurtuldu
osascript -e 'with timeout of 12 seconds
tell application "Google Chrome" to execute tab N of (first window whose id is <WID>) javascript "String(2+2)"
end timeout'
```

`with timeout of N seconds` sarmalayıcısını kullan; yoksa `osascript` varsayılan
timeout'a kadar asılı kalır ve turu yakar. (`timeout` komutu macOS'ta yok,
GNU coreutils gerektirir — AppleScript'in kendi timeout'unu kullan.)

### Deneme koruması yeterli DEĞİL

İkinci denemede "yeniden giriş bayrağı + `disconnect()`/`observe()` sarmalama +
`attributes:false`" ekledim. **Yine kilitlendi.** Gözlemci yaklaşımı bu iş için
yanlış araçtı; korumayı iyileştirmek yanlış aracı doğru yapmıyor.

### Doğru yol: kesikli tekrar

Yeniden çizim süresi ölçülebilir bir aralıksa (genelde 200-800 ms), tepkisel
gözlemci yerine **birkaç kez çağır**:

```js
duzelt();                          // hemen
setTimeout(duzelt, 150);
setTimeout(duzelt, 400);
setTimeout(duzelt, 800);           // yeniden çizim penceresini kapsa
```

Basit, öngörülebilir, kilitlenmiyor. Kayıp: teorik olarak arada bir kare
yakalanmayabilir. Kazanç: iş bitiyor.

> **Kural: reaktif/sürekli bir mekanizma (observer, interval, hook) iki denemede
> de patladıysa mekanizmayı iyileştirme, kesikli tekrara geç.** Aynı kalıp
> `setInterval` ile DOM yamalamada ve `fetch` monkeypatch'te de görülüyor.

## Dosya yükleme: gerçek tıklama + otomasyon izni

Form alanlarını JS ile doldurabilirsin ama `input[type=file]` alanını
**doldurtamazsın** — tarayıcı bunu kasıtlı engeller, Chrome 136+ varsayılan
profilde CDP de kapalıdır. Tek yol native dosya seçici sheet'ini sürmek.

İki ön koşul, ikisi de atlanırsa iş sessizce başarısız olur:

1. **macOS otomasyon izni.** İlk çalıştırmada ekranda "Terminal, System Events
   uygulamasını kontrol etsin mi?" penceresi çıkar ve kullanıcı **İzin Ver**
   demeden hiçbir tuş gitmez. Kullanıcı makine başında değilse önceden haber ver.
2. **Sheet'i açan tıklama gerçek fare olayı olmalı.** JS `.click()` `'ok'` döner
   ama sheet açılmaz (8 saniye boyunca ölçüldü, sıfır sheet). Gerçek tıklama
   **ekran koordinatına** gittiği için alan viewport içinde olmalı: önce
   `scrollIntoView({block:'center'})`, sonra koordinatı **yeniden oku**, sonra
   tıkla. Uzun formlarda alan `y=13202` gibi bir konumda olabilir.

Tam reçete, sheet'in hangi pencerede açıldığını bulma ve `Cmd+Shift+G` tuzağı:
`references/native-dosya-secici-ve-medya.md`

## Sabit `sleep` ile okumak sessizce ÇÖP veri üretir

Bir sayfayı açıp `sleep 12` bekleyip metnini okumak çoğu zaman çalışır. Sorun
**çalışmadığı zamanda hata vermemesidir**: sayfa henüz yüklenmemişse
`document.body.innerText` boş dönmez, gezinme menüsünü döner. Okuma başarılı
görünür, dosyaya yazılır, sonraki adım onu gerçek içerik sanıp işler.

2026-08-14 doğrulanmış vaka: altı iş ilanı toplu okundu, her biri ~1600 karakter
döndü, hepsi \"başarılı\" göründü. Kaydedilen metin şuydu:

```
=== Vectrix FDE Logistics (4454505803) ===
0 bildirim
Aramaya geç
Ana Sayfa
Ağım
İş İlanları
...
```

İlan gövdesi değil, LinkedIn menüsü. Arkasından çalışan puanlayıcı her ilana
`kod:0 dil:0 diploma:0` verdi ve **altı ilanın altısı da \"sınırda\"** çıktı.
Karakter sayısı doluydu, çıktı makul görünüyordu, sonuç tamamen uydurmaydı.
Elle tek tek açılınca gerçek şart ortaya çıktı: en az üç yıl üretim yazılımı.

**Çözüm: süre değil İÇERİK bekle.** Beklemeyi uzatmak (`sleep 20`) yavaş ağda
yine patlar; doğru olan okunanın gerçekten hedef içerik olduğunu sınamaktır.

```python
def oku_dogrulayarak(js_dosya, gecersiz_izi, en_az=400, deneme=9):
    for _ in range(deneme):
        time.sleep(3)
        metin = js(js_dosya)
        if len(metin) > en_az and gecersiz_izi not in metin[:200]:
            return metin
    return metin          # son deneme, cagiran taraf BOS diye isaretler
```

`gecersiz_izi` sayfanın kabuğunda olup içeriğinde olmayan bir dize olmalı —
LinkedIn için `\"Ana Sayfa\"`, çoğu panelde site adı ya da giriş menüsü.

Toplu okumada her kaydı `OK` / `BOS` diye **işaretle ve say**. Bu iki satır,
sessiz çöpün istatistiğe karışmasını engeller:

```python
iyi = \"OK\" if len(metin) > 400 and gecersiz_izi not in metin[:200] else \"BOS\"
print(\"%-36s %s (%d karakter)\" % (ad[:36], iyi, len(metin)))
```

> **Kural: bir tarama sonucunda ölçülen bütün kayıtlar aynı değeri veriyorsa
> (hepsi sıfır, hepsi \"sınırda\", hepsi aynı uzunlukta) önce ölçümden şüphelen,
> veriden değil.** Tekdüze sonuç genelde bulgu değil, boru hattının kırıldığının
> işaretidir. Ham kaydın ilk satırlarını gözle oku.

## Görünen değer ile GÖNDERİLECEK değer aynı olmayabilir

Form ekranda doğru görünür, hata çıkmaz, ama gönderilecek veri yanlıştır.
**Ekran görüntüsü bu sınıfı yakalamaz**, çünkü ekranda her şey doğrudur.

2026-08-14 ölçümü: `input[type=range]` alanına native setter ile `6` yazıldı,
kaydırıcı 6 gösterdi, formun kendi verisinde `0` duruyordu. Site kaydırıcının
yanında **ayrı bir gizli alan** tutuyordu (`range-custom_number`) ve görünen
öğeye yazmak onu güncellemiyordu. Gönderilseydi sıfır gidecekti.

Tersi de olur: dosya alanı `files` boş gösterir ama dosya sunucuya yüklenmiştir
(adres `*_remote_url` alanında durur). "Boş" sanıp tekrar yüklersen ikinci kopya
eklersin.

> **Kural: bitirmeden önce alanların `value` değerlerini tek tek OKU.** Aynı
> soruya hizmet eden bütün alanlar (görünen + gizli eş) aynı değeri göstermeli.
> Dosya doğrulaması `files` VEYA `*_remote_url` ile yapılır.

Ölçümler ve hazır doğrulama kodu: `references/native-dosya-secici-ve-medya.md`.

## Açılır menü `<select>` olmayabilir — tıkla, ok tuşuyla aç

Modern form altyapıları (Greenhouse, Teamtailor, Ashby) açılır menüleri özel
bileşenle çizer. `document.querySelectorAll('select')` **sıfır** döner ve
`SELECT YOK` sonucunu \"bu formda menü yok\" diye okursan zorunlu alanı boş
bırakırsın.

2026-08-14 doğrulanmış sıra:

1. Alanın **kendisine** gerçek fare tıklaması (menü hemen açılmayabilir).
2. `key: down` — özel bileşenler klavye ile açılır, tıklamayla açılmayanlar bile.
3. Açılan listedeki seçeneğe koordinatla tıkla.
4. Yeni capture al ve alanın **görünen değerini** oku.

Menü seçeneklerini önden görmek için DOM'dan değil ekrandan bak; seçenek düğümleri
menü kapalıyken DOM'da olmayabilir.

### Chrome'un kendi öneri katmanı tıklamayı yutar

Aynı oturumda üç kez oldu: adres/otomatik doldurma önerisi form öğesinin üstüne
biniyor, tıklama menüye değil öneriye gidiyor. Belirti: tıkladın, ekran görüntüsünde
koyu bir liste var ve içinde site seçenekleri değil **kayıtlı adresler** duruyor.

Refleks `Escape`, sonra **koordinatı yeniden oku** (öneri kapanınca düzen kayar) ve
tekrar tıkla. Öneriyi kapatmadan yapılan her tıklama boşa gider.

## Native izin penceresi girdiyi YUTAR, sayfa capture'ı onu göstermez

2026-08-15'te bir başvuru formu iki kez bu yüzden durdu. Belirti hep aynı:

```
type_text incomplete: delivered 0 of 8 character(s)
```

Tıklamalar da `unverifiable` dönüyor ve hiçbir şey değişmiyor. Refleks yanlış
olur: farklı yazma yöntemi denemek, koordinatı yeniden okumak, `Escape` atmak.
Hiçbiri işe yaramaz çünkü klavye ve fare **sayfaya değil, önündeki modal izin
penceresine** gidiyor.

İki kaynak görüldü:

| Pencere | Ne tetikledi | Nereye çıktı |
|---|---|---|
| \"Uzaktan hata ayıklamaya izin verilsin mi?\" | `browser_exec` çağrısı | Chrome kabuğu, sayfanın dışında |
| \"<site> konumunuzu öğrenmek istiyor\" | Formdaki konum alanı | Adres çubuğunun altında, sayfanın dışında |

**Kritik ayrıntı: ikisi de sayfa içeriğinde değil.** `app`/`window_id` ile
alınan capture bunları bazen gösterir, bazen pencere başlığına düşer:

```
title='... - İzin istendi, yanıtlamak için ⌘ + Option + Yukarı ok tuşlarına basın'
```

Başlıkta \"İzin istendi\" görüyorsan girdinin neden kaybolduğunu bulmuşsundur.

### Ne YAPMA

Bu pencereler kullanıcının rızası içindir (bkz. bölüm 0 — izin diyaloglarına
dokunma). Konum izni özellikle kişisel veridir. Tıklamayı deneme, tıklasan bile
tıklaman genelde geçmez ve geçerse kullanıcı adına rıza vermiş olursun.

### Ne YAP

1. Girdi \"delivered 0 of N\" veriyorsa **önce izin penceresi ara** — pencere
   başlığına bak, sonra `app=\"screen\"` ile capture al (sayfa capture'ı yetmez).
2. Kullanıcıya söyle ve **kapatmasını iste.** Hangi pencere olduğunu ve neyi
   seçmesi gerektiğini yaz (\"Hiçbir zaman izin verme\" gibi).
3. Kapatılana kadar aynı forma yazmayı tekrar deneme, her deneme boşa gider.

> **Kural: `delivered 0 of N` bir yazma yöntemi hatası değil, ODAK hatasıdır.**
> Yöntem değiştirmeden önce girdinin nereye gittiğini sor.

## Gezinme ve yenileme, DOLU alanları siler

Yukarıdaki izin penceresini atlatmak için sekmeyi yeniden yüklemek cazip gelir.
Bedeli var: 2026-08-15'te yarım dolu bir başvuru formunda telefon ve konum
alanları yenileme sonrası **boşaldı**, ad ve e-posta kaldı. Site bazı alanları
oturumda tutuyor, bazılarını tutmuyor ve hangisinin hangisi olduğu önceden
bilinemez.

Aynısı otomatik olarak da olur: dosya seçici açılıp kapanırken, çok adımlı
formda geri/ileri gidildiğinde, SPA yönlendirmesinde.

> **Kural: her gezinme, yenileme veya modal açılıp kapanmasından sonra formun
> TAMAMINI yeniden oku.** \"Bu alanı zaten doldurmuştum\" varsayımı, doldurulmamış
> bir alanla gönderim yapmanın en yaygın yolu.

```js
[].slice.call(document.querySelectorAll('input,textarea'))
  .filter(function(e){ return e.type !== 'hidden' && e.type !== 'file'; })
  .map(function(e){ return (e.name||e.id||e.type) + '=' + (e.value ? e.value.slice(0,20) : 'BOS'); })
```

Doldurma betiğini **idempotent** yaz (dolu alana dokunma, boş alanı doldur);
böylece yenileme sonrası aynı betiği tekrar çalıştırmak yeterli olur ve dolu
alanları bozmaz.

## Sekme numarası TUR İÇİNDE kayar, adresten yeniden bul

`make new tab` ile aldığın numarayı sabit sanma. Kullanıcı sekme kapattığında ya da
başka bir iş sekme açtığında numaralar kayar ve elindeki numara **başka bir sayfayı**
gösterir. Kötü hâli sessiz değildir, ama mesajı yanıltıcıdır:

```
execution error: Google Chrome bir hatayla karşılaştı:
tab 21 of window 1 whose id = 444142723 alınamıyor.
```

2026-08-14'te yarım dolu bir başvuru formu 21'den 15'e kaydı. Numaraya güvenip
devam etseydim başka bir sayfada iş yapıyor olacaktım.

**Kural: uzun süren bir işte sekmeyi numarayla değil ADRESLE bul.** Her önemli
adımdan önce doğrula:

```applescript
tell application "Google Chrome"
  set o to ""
  repeat with i from 1 to count of tabs of (first window whose id is <WID>)
    set u to URL of tab i of (first window whose id is <WID>)
    if u contains "<ayirt-edici-parca>" then set o to o & i
  end repeat
  if o is "" then return "SEKME YOK"
  return o
end tell
```

Dönen numarayı o adımda kullan, sonraki adımda yeniden sor. Bu üç saniyelik kontrol,
yanlış sayfaya veri yazmaktan ucuzdur.

## Çapraz kaynak iframe: JS erişimi TAMAMEN kapalıdır

Gömülü form (Greenhouse, Typeform, ödeme alanları) `<iframe>` içindeyse ve
iframe farklı kaynaktan geliyorsa `contentDocument` okumak tarayıcı
güvenliğine takılır. `try/catch` sessizce boş döner, ortada hata görünmez.

Belirti: sayfada form GÖRÜNÜYOR ama `querySelectorAll('input')` yalnızca
çerez kutusu ve arama kutusu döndürüyor.

```js
var erisim = [].slice.call(document.querySelectorAll('iframe')).some(function(f){
  try { return !!(f.contentDocument && f.contentDocument.querySelector('input')); }
  catch (e) { return false; }
});
erisim ? 'ERISILEBILIR' : 'CAPRAZ KAYNAK, JS YOK';
```

`CAPRAZ KAYNAK` çıkarsa yukarıdaki native setter reçetesi geçersizdir, JS
köprüsü de kurtarmaz. Tek yol gerçek klavye: her alana `computer_use` ile
tıkla, `type` ile yaz. Koordinatı her adımda ekran görüntüsünden **yeniden
oku**, iframe içeriği kaydıkça konumlar değişir.

> **Kural: \"bu formda alan yok\" demeden önce iframe erişimini sına.**
> Alanların olmaması ile alanlara erişememek ayrı teşhislerdir ve ikincisi
> tamamen farklı bir yol gerektirir.

## Otomatik tamamlama listesi YANLIŞ kaydı seçer

Şehir/adres alanlarında açılan öneriden ilk kaydı seçmek riskli. 2026-08-14
ölçümü: `Istanbul` yazıldı, ilk öneri seçildi, alana `Istanbulbogazi, Ordu,
Türkiye` yerleşti. Alan dolu olduğu için **ekran görüntüsü bu hatayı
yakalamaz**.

Aramayı daralt (`Istanbul, Turkey`) ve seçimden sonra alanın son değerini
oku. Listeye tıklamış olmak doğru kaydın geldiğini göstermez.

## Gevşek etiket eşleşmesi AYNI değeri iki alana yazar

Yukarıdaki \"ata düğümleri tara\" reçetesinin bedeli var: kalıp fazla genişse
tek bir değer birden çok alana düşer. 2026-08-14 ölçümü — `/\bname\b/` kalıbı
hem `Name` hem `Location` sarmalayıcısında eşleşti ve konum alanına
`Ahmet Kazankaya` yazıldı. Alan doluydu, hata çıkmadı, ekran görüntüsünde
normal görünüyordu.

Sıra önemli, önce dar eşleşme:

```js
function etiketMetni(e){
  if (e.id) {
    var l = document.querySelector('label[for=\"' + e.id + '\"]');
    if (l) return (l.innerText || '').trim().toLowerCase();   // TAM eslesme
  }
  var p = e.closest('div');                                    // ancak simdi ata
  for (var i = 0; i < 4 && p; i++) {
    var m = (p.innerText || '').replace(/\s+/g, ' ');
    if (m.length > 8) return m.slice(0, 130).toLowerCase();
    p = p.parentElement;
  }
  return '';
}
```

Ata metnine düşerken kalıbı **çapala**: `/^name$/` veya `/first name/`, çıplak
`/name/` değil. `location`, `company`, `title` gibi kelimeler başka etiketlerin
içinde geçer.

Doldurma sonrası çapraz kontrol iki satır ve bu sınıfı tamamen kapatır:

```js
var d = {};
[].slice.call(document.querySelectorAll('input,textarea')).forEach(function(e){
  if (!e.value || e.type === 'hidden' || e.type === 'file') return;
  (d[e.value] = d[e.value] || []).push(e.name || e.id || e.type);
});
Object.keys(d).filter(function(v){ return d[v].length > 1; })
  .map(function(v){ return v.slice(0,24) + ' -> ' + d[v].join(', '); });
```

Boş dönmüyorsa aynı değer birden çok alanda demektir. E-posta gibi kasıtlı
tekrarları ayıkla, kalanı düzelt.

> **Düzeltmeyi JS ile değil GERÇEK KLAVYEYLE yap.** Yanlış yazan setter aynı
> alana doğru değeri de yazamıyor olabilir; tıkla, `cmd+a`, `type`. 2026-08-14'te
> JS düzeltmesi değeri bu kez isim alanına taşıdı ve hata yer değiştirdi.

## Pitfalls

- **Tarayıcıyı sürmek her zaman doğru araç değil — önce maliyeti kıyasla.**
  Tek bir metin alanını güncellemek için uzaktan tarayıcı sürmek 20+ tur
  yakabiliyor. Metni kullanıcıya verip elle yapıştırmasını istemek iki dakikalık
  iştir. Kullanıcı "sen yap" demiş olsa bile, iş tek bir alansa ve tur bütçesi
  darsa bu seçeneği söyle. Doğrulanmış vaka (2026-08-08): tek bir Hakkında
  cümlesi eklemek, kaydetmenin sessiz reddi yüzünden bir turu tamamen yedi ve
  kullanıcının sesli mesajındaki diğer iki iş hiç başlayamadı.
- **Çok işli istekte tarayıcı işine dalıp diğerlerini düşürme.** Sesli mesaj ya
  da uzun istek birkaç iş içeriyorsa önce hepsini listele, sonra en riskli olanı
  (genelde tarayıcı otomasyonu) **en sona** al. Tarayıcı işi turu yediğinde
  diğerleri hiç başlamamış olur ve kullanıcı haklı olarak "neden tam
  işleyemedin" der. Tur biterken yarım kaldıysa, kalan işleri ve elle yapılacak
  metni açıkça yaz.
- **Yarım kalan işi "tamamlandı" diye raporlama.** Bir alan bozuk kaldıysa kaydetme,
  kullanıcıya durumu ve elle ne yapması gerektiğini net söyle.
- **Canlı profilde marker ile test ediyorsan geri almayı ÖNCE bütçele.** Başlığa
  `[T9Z]` gibi bir işaret koyup kaydın tuttuğunu doğrulamak meşru ve güçlü bir
  teknik — ama kullanıcının gerçek profilini bozar. 2026-08-09'da tur limiti geri
  alma adımından önce doldu ve profil test marker'ıyla, Türkçe karakterleri ASCII'ye
  düşmüş bir başlıkla kaldı. Kural:
  1. Değiştirmeden önce orijinal değerleri JSON olarak diske yaz (yolu rapora ekle).
  2. Marker testini **tek bir alanda** yap, tüm bölüme yayma.
  3. Geri alma çağrısını bütçenin sonuna değil, doğrulamadan **hemen sonrasına** koy.
  4. Tur biterken profil bozuk kaldıysa raporun **en üstüne** yaz — sonuca gömme.
  Mümkünse marker'ı görünür başlık yerine açıklamanın sonuna koy; profil daha az
  bozulur.
- Aynı çağrıyı değiştirmeden üçüncü kez deneme. `unverifiable` görünce taze durum al,
  `suspected_noop` veya yapısal ret görünce escalate et.
- Uzun listeleri tek tek silerken her silme sonrası capture almayı atlama.
- **Sayfa kaydırma hiç çalışmayabilir.** `action=scroll` (fare tekerleği) ve `pagedown`
  ikisi de `unverifiable` dönüp hiçbir şey yapmayabiliyor; iç panele tıklayıp odak
  vermek de çözmüyor. AX ağacı yalnızca görünür alanı verdiği için liste kesik gelir.

  > **Önce sebebi ayır: kaydırma bozuk değil, YANLIŞ KUTUYU kaydırıyor olabilirsin.**
  > Tembel yüklenen listelerde (arama sonuçları, sonsuz kaydırma) kaydırılacak öğe
  > sayfanın kendisi değil, içeriği saran ve `overflow-y:auto` taşıyan atadır —
  > LinkedIn'de ilan bağlantısının 9 seviye yukarısında. `window.scrollBy` ona hiç
  > dokunmaz. Hesaplanmış stilden kutuyu bulan çalışan reçete, ilerleme ölçen döngü
  > ve "sona varınca liste sıfırlanıyor" tuzağı:
  > `references/tembel-liste-kaydirma.md` (2026-08-14'te 9 → 17 kayıtla doğrulandı).

  Kutu bulma da işe yaramıyorsa **en ucuz çare kaydırmamak:** hedef eleman AX
  ağacında `bounds: [0,0,0,0]` ile, yani ekran dışında görünse bile `element=N` ile
  AXPress çalışıyor (2026-08-08'de görünmeyen Kaydet düğmesinde doğrulandı).
  Kaydırma gerçekten şartsa, sırayla:
  1. `osascript` ile `keystroke "-" using command down` × 4 → zoom'u küçült, daha çok
     satır tek ekrana sığar. (`cmd+minus` computer_use'da geçersiz tuş adı, AppleScript
     kullan.)
  2. Pencereyi büyüt: AppleScript `set bounds of w to {0, 0, 1512, 940}`.
  3. Kaydırmaya hiç ihtiyaç duymayan döngü kur: her silmede liste yukarı kaydığı için
     **hep aynı ekran konumundan** çalış, sonraki madde o koordinata gelir.
- `pagedown` geçerli tuş adı, `page_down` değil. Tuş adı hatası alırsan alt çizgiyi at.
- **Her yeni iş için YENİ SEKME aç, açık sekmenin adresini EZME.** Bu kural
  2026-08-14'te kullanıcı düzeltmesiyle tersine çevrildi. Önceki hâli "iş hangi
  sekmedeyse orada kal" diyordu ve tam da bu yüzden siteler kayboldu:

  > *"edflex sekmesi açık değil, sen bu tarz şeylerde genelde yeni sekme açmayıp
  > açık olan sekmeden devam ettiğin için kayboluyor siteler"*

  `set URL of tab N` mevcut sayfayı yok eder. Yarım kalmış bir form, okunmuş bir
  ilan ya da kullanıcının kendi açtığı bir sayfa oradaysa geri getirilemez.
  Doğrusu:

  ```applescript
  tell application "Google Chrome"
    set w to (first window whose id is <WID>)
    make new tab at end of tabs of w with properties {URL:"<adres>"}
    set active tab index of w to (count of tabs of w)
    return (count of tabs of w)   -- yeni sekme numarasi, bunu sakla
  end tell
  ```

  `set URL` yalnızca **kendi açtığın** sekmede, aynı iş devam ederken meşrudur
  (form → doğrulama → sonraki adım). Kullanıcının sekmesine ya da başka bir işin
  sekmesine asla yazma.
- **Arka plan işi ile ön plan işi AYNI sekmeyi paylaşamaz.** Uzun bir tarama
  arka planda dönerken aynı sekmede iş yapmaya kalkarsan ikisi birbirini ezer;
  tarama üçüncü adımda sessizce durur, ön plandaki sayfa boş kalır. Arka plan
  betiğine kendi sekmesini aç ve numarasını parametre olarak geç.
