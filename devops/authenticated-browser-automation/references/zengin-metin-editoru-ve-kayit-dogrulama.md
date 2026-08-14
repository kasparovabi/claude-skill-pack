# Zengin metin editörüne yazma ve kaydı gerçekten doğrulama

Doğrulandığı oturum: 2026-08-08, Chrome + LinkedIn profil düzenleme kutuları.
Sonuç: **iki ayrı çalışan yol bulundu ve uçtan uca kaydedildi** (düz alanlarda AX
`set_value`, zengin metin kutusunda pano + `cmd+a`/`cmd+v`). Aşağısı hem kazanan
reçeteler hem de önce denenip tutmayan yolların ölçülmüş kaydı.

**Kısa yol:** alanın türünü belirle → "Alanın türü yolu belirler" tablosuna bak →
o bölümün reçetesini uygula → "Kaydettim mi?" testiyle doğrula.

## Belirti

Metin ekranda görünüyor, Kaydet'e basılıyor, diyalog kapanıyor, doğrulama "VAR"
diyor. Sayfa yenilenince metin yok.

## Yalancı pozitifin kaynağı

Kaydet sonrası sayfadan metin okumak kaydın tuttuğunu **kanıtlamaz.** Diyalog
kapandıktan sonra metin hâlâ DOM'da duruyor:

| An | `document.body.innerText` uzunluğu | Arama sonucu |
|---|---|---|
| Kaydet'ten hemen sonra | 40.710 | `TR:VAR \| EN:VAR` |
| Sayfa yenilendikten sonra | 37.336 | `TR:YOK \| EN:YOK` |

Aradaki fark tam olarak eklenen metin kadar. Yani ilk ölçüm, kaydı değil ekranda
kalan artığı ölçüyor.

### Ters yöndeki tuzak da var

Yenileme sonrası `YOK` görmek de tek başına kanıt değil: profil sayfası uzun metni
kırpıp "…daha fazla göster" arkasına gizliyor, `body.innerText` kırpılmış hâli
veriyor. Yani aynı belirsizliğin iki yüzü var ve ikisi de yanıltıyor.

## Geçerli kabul testi (üç adım, üçü de zorunlu)

1. Sayfayı yeniden yükle
2. Düzenleme kutusunu **yeniden aç**
3. Metnin kutunun içinde olduğunu doğrula

Yalnız düzenleme kutusunun içeriği gerçeği söyler.

Sonda — paragraf listesini basar, hem varlığı hem **sırayı** gösterir:

```javascript
(function(){var ce=document.querySelector('[contenteditable="true"]');
if(!ce)return 'KUTU YOK';var p=ce.children;var o=[];
for(var i=0;i<p.length;i++)o.push(i+':'+(p[i].innerText||'').substring(0,40));
return 'COCUK:'+p.length+' || '+o.join(' | ');})()
```

## Tutmayan yollar (hepsi denendi)

| Yöntem | Görünen sonuç | Gerçek sonuç |
|---|---|---|
| `execCommand('insertText', ...)` | `true`, metin ekranda | kayıt eski değeri gönderdi |
| `insertBefore` ile yeni `<p>` | dönüş `missing value` | düğüm hiç eklenmedi |
| `dispatchEvent(new Event('input'))` | hata yok | React state güncellenmedi |
| Kaydet'e `.click()` (JS) | diyalog kapandı | kaydedilmedi |
| Kaydet'e gerçek fare tıklaması | diyalog kapandı | yine kaydedilmedi |

Son satır kritik: gerçek tıklama bile kurtarmadı. Demek ki sorun tıklamada değil,
metnin React'in state'ine hiç ulaşmamasında. Tıklama yolunu değiştirerek uğraşmak
boşa tur harcatır.

## Alanın türü yolu belirler — önce bunu ayır

İki ayrı sınıf var ve **aynı yol ikisinde de çalışmıyor.** Yazmaya başlamadan önce
alanın hangisi olduğunu tespit et:

| Alan türü | AX'te görünümü | Çalışan yol |
|---|---|---|
| Düz alan (ad, başlık, `<input>`) | `AXTextField` / `AXTextArea`, `set_value` kabul eder | **AX `set_value`** (aşağıdaki bölüm) |
| Zengin metin (`[contenteditable=true]`) | genelde `AXTextArea` ama `set_value` içeriği değiştirmez | **Pano + gerçek klavye** (aşağıdaki bölüm) |
| `<select>` | `set_value` "has no AX children" ile reddeder | native setter + `change` olayı |

Ayırt etmenin en hızlı yolu, sayfaya tek satır sorup bakmak:
`document.querySelector('[contenteditable="true"]')` sonuç dönüyorsa zengin metin
kutusundasın ve AX `set_value` ile uğraşma.

## Düz alanlar — AX `set_value` (2026-08-08 doğrulandı)

LinkedIn'in "Profilinizi farklı bir dilde oluşturun" formu (Ad, Soyadı, Başlık) bu
yolla uçtan uca kaydedildi, başarı diyaloğu ekranda teyit edildi.

```
# 1) Alanları AX ağacından bul (DOM sorgusu bu formlarda 0 sonuç döndürebiliyor)
computer_use(action="capture", mode="ax", pid=<pid>, window_id=<wid>, max_elements=1000)
#    -> çıktı dosyaya düşerse execute_code ile filtrele:
#       role in ("AXTextField","AXTextArea") ve bounds[1] > 400

# 2) Her alana set_value
computer_use(action="set_value", element=44, value="Ahmet", pid=..., window_id=...)

# 3) Kaydet'e AXPress
computer_use(action="click", element=58, pid=..., window_id=...)
```

`set_value` **`effect: unverifiable` + "Read-back did not confirm"** dönse bile
başarılıdır — `mode="som"` capture ile gözle doğrula, tekrar gönderme. Üç alan da
bu uyarıyı verdi, üçü de ekranda doğru göründü ve kayıt tuttu.

## Zengin metin kutusu — pano + gerçek klavye (2026-08-08 doğrulandı)

LinkedIn "Hakkında" kutusu `[contenteditable=true]`. Burada AX `set_value` ve tüm
DOM yolları başarısız; kazanan sıra şu ve **sırası önemli**:

```bash
printf '%s' "$METIN" | pbcopy          # 1) metni panoya al, uzunluğu doğrula
```
```
# 2) kutuya GERÇEK tıklama ile odaklan (JS focus() yetmiyor)
computer_use(action="click", coordinate=[<kutu içi>], delivery_mode="foreground",
             pid=..., window_id=...)

# 3) cmd+a  -> 4) cmd+v   (ikisi de delivery_mode="foreground")
computer_use(action="key", keys="cmd+a", delivery_mode="foreground", pid=..., window_id=...)
computer_use(action="key", keys="cmd+v", delivery_mode="foreground", pid=..., window_id=...)
```

### `cmd+a` atlanırsa metin DEĞİŞMEZ, EKLENİR

JS ile `Range`/`Selection` kurup metni seçmek işe yaramıyor — yapıştırma o seçimi
görmüyor ve imlecin bulunduğu yere ekliyor. Ölçülmüş kayıt:

| Adım | Kutu uzunluğu |
|---|---|
| başlangıç (Türkçe metin) | 2405 |
| JS ile seç + `cmd+v` | **3774** ← değişmedi, sona eklendi |
| `cmd+a` + `cmd+v` | **1369** ← doğru, tamamen değişti |

Kural: seçimi **klavyeden** yap. Yapıştırdıktan sonra uzunluğu beklenen değere karşı
kontrol et; sayı tutmuyorsa ekleme olmuştur, `cmd+a` ile tekrarla.

### Yapıştırma sonrası içerik sondası

Uzunluk tek başına yetmez, yanlış dil/artık metin kalmış olabilir. Dil izini de sor:

```javascript
(function(){var ce=document.querySelector('[contenteditable="true"]');
if(!ce)return 'YOK';var m=ce.innerText||'';
var tr=/ş|ğ|ı|Şirketlerde/.test(m);
return 'uzunluk:'+m.length+' | TURKCE-IZ:'+(tr?'VAR':'YOK')
  +' | ilk90:'+m.substring(0,90)+' || son90:'+m.substring(m.length-90);})()
```

`TURKCE-IZ:YOK` + doğru uzunluk = metin gerçekten değişmiş demektir.

### Yapıştırma boş satırları yutar — uzunluk sondası bunu YAKALAMAZ

2026-08-09'da doğrulandı. Paragraf araları olan bir metni panodan yapıştırdığında
LinkedIn **boş paragrafları siliyor.** Metnin kendisi doğru, uzunluk beklenen değere
yakın, dil izi temiz — ama ekranda paragraflar birbirine yapışık duruyor ve okunmaz
hâle geliyor.

Bu, bu dosyadaki sondaların **kör noktası**: uzunluk ve dil izi \"tamam\" derken biçim
bozuk. Kullanıcı bunu gözüyle görüp söyledi (*\"hiç satır aralığı bırakmadın, bilerek
mi\"*), sonda söylemedi. Böyle bir uyarı geldiğinde itiraz etme, `mode=\"vision\"`
capture al ve bak.

**Çözüm — boş satırlara kırılmayan boşluk koy.** LinkedIn içi boş olmayan paragrafı
korur:

```python
NB = \"\\u00a0\"  # kirilmayan bosluk
def bosluklu(metin):
    p = [x.strip() for x in metin.strip().split(\"\\n\\n\") if x.strip()]
    return (\"\\n\" + NB + \"\\n\").join(p) + \"\\n\"
```

Bu hâli panoya alıp `cmd+a` + `cmd+v` ile yapıştır. Sonuç: paragraflar ayrı duruyor
ve ekranda `&nbsp;` gibi ham kod **görünmüyor** (kontrol ettim, `body.innerText`
içinde `&nbsp;` aranınca `yok` döndü).

Kaydettikten sonra zorunlu adım: `mode=\"vision\"` capture alıp **paragraf aralarına
gözle bak**. Metin doğruluğu ile biçim doğruluğu ayrı iki şeydir; ikincisini yalnız
görüntü kanıtlar.


### Neden DOM yolu tutmuyor

DOM'a JS ile yazmak React'in state'ini güncellemiyor, form eski değeri gönderiyor.
AX `set_value` ve pano yapıştırma ise tarayıcının kendi girdi katmanından geçiyor,
React olayı gerçek kullanıcı girdisi olarak görüyor. Bu yüzden
`execCommand`/`insertBefore`/`dispatchEvent` üçlüsüyle uğraşma; **alanın türüne
bakıp yukarıdaki iki yoldan doğru olanına geç.**

JS'in hâlâ meşru olduğu tek yer, yazmak değil **okumak**: paragraf listesi basmak,
uzunluk ölçmek, dil izi aramak, koordinat hesaplamak. Sonda olarak kullan, kalem
olarak değil.

Tek istisna: `<select>` elemanları. Onlarda AX `set_value` "has no AX children"
diye reddedebiliyor; native setter + `change` olayı çalışıyor ve kaydediliyor:

```javascript
var setter=Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype,'value').set;
setter.call(s,'en_US');
s.dispatchEvent(new Event('change',{bubbles:true}));
```

### Görünmeyen düğmeye basmak için kaydırmaya çalışma

Kaydet düğmesi AX ağacında `bounds: [0,0,0,0]` ile, yani görünür alanın dışında
gelebiliyor. **`element=N` ile AXPress yine de çalışıyor** — kaydırmaya, zoom
küçültmeye, pencere büyütmeye gerek yok. Bu, SKILL.md'deki "sayfa kaydırma hiç
çalışmayabilir" tuzağının pratik çözümü.

## Çok pencereli Chrome: `type` ve `scroll` arka planda reddedilir

Chrome birden fazla üst düzey pencere sahibiyse arka plan klavye/tekerlek girdisi
yapısal olarak reddediliyor:

```
Background input refused (same_pid_keyboard_ambiguity):
pid X owns 2 other eligible top-level window(s)
```

Bu bir arıza değil, koruma — kardeş pencereye yazmayı engelliyor. **İki geçerli
çıkış var, hangisini seçeceğini alanın türü belirler:**

- **Düz alan / düğme ise** element index'e geç: `type` yerine `set_value`, `scroll`
  yerine hedefe doğrudan AXPress. İkisi de element hedeflediği için `same_pid`
  belirsizliğine düşmez ve kullanıcının odağını hiç bozmaz. Önce bunu dene.
- **Zengin metin kutusu ise** (`contenteditable`) element yolu içeriği
  değiştiremiyor; `delivery_mode="foreground"` **doğru ve gerekli** cevaptır.
  Driver'ın kendi tavsiyesi de budur (`escalation.recommended`). Kısa süreliğine
  pencereyi öne alır, işi yapar, geri bırakır.

Yani "foreground'a hiç çıkma" diye bir kural yok; kör kör tekrar denemek yanlış,
**dönen yapısal reddi okuyup uygun basamağa çıkmak** doğru.


## Sekmeli (çok dilli) düzenleme kutusu: hangi sekmedeyim?

Profil birden çok dilde tutuluyorsa düzenleme kutusu üstte sekme taşır
(`English (Birincil profil)` / `Turkish`). İki tuzak birden var:

- **URL parametresi sekmeyi seçmez.** `?locale=en_US` eklemek çalışmıyor, kutu yine
  varsayılan sekmeyle açılıyor ve URL `language=und&locale=und` gösteriyor. Yani
  URL'e bakarak hangi dili düzenlediğini **anlayamazsın**.
- **Yeni dil sürümü, eski dilin metniyle dolu açılır.** İçeriğin Türkçe olması
  yanlış sekmede olduğun anlamına gelmez; doğru sekmede ama henüz çevrilmemiş
  olabilir. Bu ikisi karıştırılınca doğru yerde yapılan iş "yanlış sekme" sanılıp
  geri alınır.

Tek güvenilir yol: `mode="vision"` capture alıp **hangi sekmenin altı çizili
olduğuna gözle bak**, sonra sekmeye gerçek tıklama yap ve öyle yaz.

## Kaydettim mi? — kabul testi bu formlarda da geçerli

Kaydet sonrası profil sayfasından okumak yanıltıcı: sayfa metni kırpıp
"…daha fazla göster" arkasına gizliyor, ayrıca tarayıcı arayüz dili Türkçeyse
İngilizce sürümü göremezsin. `TR:YOK | EN:YOK` çıktısı **kaydın tutmadığını
kanıtlamaz.**

Geçerli test değişmedi: sayfayı yenile → düzenleme kutusunu yeniden aç → içeriği
kutunun içinden oku. Bir de en ucuz kanıt: kaydetme sonrası ekranda beliren
**"Kaydetme işleminiz başarılı oldu"** bildirimini `mode="vision"` ile yakala.

## Yerleştirme: sona eklemek çoğu zaman yanlış yer

Bu bölüm yalnız **ekleme** yapıyorsan geçerli; metnin tamamını değiştiriyorsan
`cmd+a` + yapıştır zaten her şeyi siler ve yerleştirme sorunu doğmaz.

Tek dilde tutulan iki dilli metinlerin yapısı tipik olarak şu: Türkçe blok →
İngilizce blok → iletişim satırı. Kutunun sonuna eklemek, Türkçe cümleyi İngilizce
bloğun ve e-postanın **altına** düşürür.

Doğru sıra: paragraf listesini bas → hedef paragrafı metniyle bul → imleci onun
sonuna koy → ekle. Yanlış yere düştüyse önce o düğümü ve arkasında bıraktığı boş
paragrafı kaldır, sonra yeniden ekle.

**Daha iyisi:** profil çok dilli sürüme geçirilebiliyorsa bu iş tamamen ortadan
kalkar — her dil kendi sürümünde tek dilde durur. Bkz.
`linkedin-profile-optimization/references/cok-dilli-profil.md`.

## LinkedIn proje formu: URL doğrudan açılmıyor

`/in/.../edit/forms/projects/<ID>/` adresini doğrudan `set URL of tab` ile yüklemeye
çalışırsan LinkedIn "Böyle bir sayfa yok" döndürüyor ve form alanları asla belirecek.
**Tek çalışan yol:**

1. `/in/.../details/projects/` sayfasını aç (normal liste)
2. Hedef projenin `aria-label="<proje adı> projesini düzenleyin"` etiketli düğmesini
   JS ile bul ve tıkla:
   ```javascript
   var btn = Array.from(document.querySelectorAll('button,a'))
     .find(b => /d.zenleyin/.test(b.getAttribute('aria-label')||'')
              && /audit/i.test(b.getAttribute('aria-label')||''));
   btn && btn.click();
   ```
3. Form açıldıktan sonra `lk_exec.scpt <wid> <tab_idx> <js_dosyasi>` yaklaşımı çalışır.

Marker testi bittiğinde geri alma da aynı akışı izler — kalem düğmesini JS ile bul,
formu aç, orijinal değerleri (`/tmp/orig_fields.json`) yerleştir, kaydet.

## Pencere hedefleme yan notu

`computer_use capture app="Google Chrome"` bozuk/küçük bir çerçeve döndürebiliyor
(466x44 gibi) çünkü Chrome'un başlıksız yardımcı pencereleri de listede. `list_windows`
ile **başlıklı** pencereyi bul, `pid` + `window_id` ikisini birden ver. Bozuk capture'ı
"ekran alınamıyor" diye yorumlama, yanlış pencereyi hedeflemiş olabilirsin.

Sayfa içi koordinatı ekran koordinatına çevirirken krom yüksekliğini ekle:
`window.outerHeight - window.innerHeight` (bu oturumda 121 px) + pencere `position.y`.

### `window_id` bayatlar — uzun oturumda yeniden türet

Oturum bir kesintiyi aşıyorsa (ağ kopması, tarayıcı yeniden başlaması, kullanıcı
pencereyi kapatıp açması) elindeki `window_id` geçersizleşir:

```
capture failed: window_id 46822 is not a live window (closed, or the id is stale).
```

Bu bir arıza değil, kimlik değişmiştir. `list_windows` ile **başlıklı** pencereyi
yeniden bul, `pid` de değişmiş olabilir — ikisini birden tazele. Aynı `window_id`'yi
tekrar denemek tur harcatır.

Kesinti sonrası ikinci kontrol: `/tmp` altındaki çalışma dosyaların (metinler,
yardımcı `.scpt` dosyaları) silinmiş olabilir. Devam etmeden önce varlıklarını
doğrula, yoksa yeniden üret.
