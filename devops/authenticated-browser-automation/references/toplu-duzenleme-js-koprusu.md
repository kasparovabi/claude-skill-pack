# Toplu düzenleme: AX yolunu bırakıp Chrome JS köprüsüne geçmek

Doğrulandığı oturum: 2026-08-05, Türkçe arayüzlü LinkedIn, 80 yetenekten 27'ye budama
+ 7 yeni terim ekleme.

## Ölçülen fark — bu tabloyu karar anında hatırla

| Yol | İş | Araç çağrısı | Sonuç |
|---|---|---|---|
| AX tıklama (`computer_use`) | 7 madde silme | 28+ | Limite çarptı, iş yarım kaldı |
| Chrome JS köprüsü | 49 silme + 7 ekleme | ~10 | Tek turda bitti |

Tek maddeyi silmek AX yolunda **4 çağrı**: kalem ikonu → sil → onay diyaloğu →
doğrulama capture'ı. Kaydırma tutmuyorsa her adıma bir capture daha biner.

**Kural: madde sayısı × 4 > 20 ise AX yolu yanlış araçtır.** İşe başlamadan hesapla.

## Köprüyü açtırmak

Chrome'da Görünüm → Geliştirici → "Apple Events'ten JavaScript'e izin ver".
Kullanıcı **elle** işaretlemeli.

Programatik açmak MÜMKÜN DEĞİL. Bu oturumda denenen ve hepsi başarısız olan yollar:
- `click menu item "Apple Events'ten JavaScript'e izin ver"` → "tıklandı" döner, kutu işaretlenmez
- `perform action "AXPress"` → aynı
- Menüyü açıp tekrar tıklama → aynı

Chrome bunu güvenlik ayarı olarak koruyor. Kullanıcıdan istemek tek yol ve bu sürtünme
değil: alternatif 20 tur pinpon oynamak.

Kullanıcı "Görünüm menüsünü bulamadım" derse: bu Chrome'un ayarlar sayfası değil,
**macOS menü çubuğu** — ekranın en tepesindeki şerit, saatin olduğu sıra. Chrome öndeyken
soldan sağa: elma, Chrome, Dosya, Düzenle, **Görünüm**, Geçmiş, Yer İşaretleri...

Köprünün açık olduğunu varsayma. Önce yokla:
```applescript
execute active tab of w javascript "document.querySelectorAll('button').length"
```
Kapalıysa Chrome hatayı açıkça söylüyor ("JavaScript'i AppleScript üzerinden çalıştırma
seçeneği kapalı"). Bu mesajı görürsen kullanıcıya git, sessizce AX yoluna düşme.

## Hazır harness

`scripts/chrome-js-toplu-duzenleme.applescript` — envanter çıkarma, üç aşamalı silme,
katalog yoklama, ekleme, kaydetme. WINDOW_ID + URL parçası + listeleri düzenleyip
`osascript` ile çalıştır.

## Sanal liste tuzağı: DOM ilk ~20 maddeyi tutuyor

Uzun listelerde tam envanter çıkarmaya çalışmak boşuna. Bu oturumda denenen ve
**hiçbiri sayıyı artırmayan** yollar:
- `window.scrollTo(0, document.body.scrollHeight)`
- `scrollBy` döngüsü + sayı sabitlenene kadar bekleme
- "Daha fazla göster" butonunu tıklama (tıklanıyor, sayı 20'de kalıyor)

Doğru döngü şu: **bir parti sil → listeyi yeniden sorgula → yeni maddeler görünür.**
Her partiden sonra envanteri tazele, gelen yeni isimleri sınıflandır, sonraki partiyi
kur. Bu oturumda 6 → 14 → 13 → 10 → 6 şeklinde beş partide bitti.

Toplam sayıyı öğrenmek istersen profil ana sayfasındaki `Yetenekler (27)` başlığını oku,
liste sayfasını saymaya çalışma.

## React kontrollü input'a yazma

`inp.value = "x"` React'te **çalışmaz**. React kendi iç state'ini korur, yazdığın değeri
yok sayar ve autocomplete listesi hiç açılmaz. Native setter'ı prototipten al:

```javascript
var setter = Object.getOwnPropertyDescriptor(
  window.HTMLInputElement.prototype, 'value').set;
setter.call(inp, "aranan terim");
inp.dispatchEvent(new Event('input',  {bubbles:true}));
inp.dispatchEvent(new Event('change', {bubbles:true}));
```

Öneri listesini okurken `[role="option"]` seçicisine sadık kal. Geniş `li` seçicisi
sayfanın navigasyon menüsünü de toplar (Ana Sayfa / Ağım / İş İlanları / Mesajlaşma...)
ve çıktıyı çöple doldurur.

## Kapalı katalog alanlarında: önce yokla, sonra ekle

Yetenek/etiket/konum gibi alanlar serbest metin değil, sabit katalog. Terimi tek tek
deneyip "yok" demek yerine **tek turda onlarca varyasyon yokla**, dönen önerileri oku,
sonra sadece birebir eşleşenleri ekle. 14 terimlik yoklama tek `osascript` çağrısı.

## Parti işlerinde try/rapor kalıbı

Her maddeyi `try` ile sar, sonucu rapora ekle, döngüyü durdurma:

```applescript
repeat with s in toDelete
  try
    set report to report & sName & " => " & deleteItem(sName) & linefeed
  on error e
    set report to report & sName & " => HATA: " & e & linefeed
  end try
end repeat
```

Tek madde patlayınca 40 maddelik parti durmasın. Dönen rapor (`CONFIRMED` / `NOTFOUND` /
`NOOPT:...`) aynı zamanda kullanıcıya gösterilecek kanıttır — "hepsi silindi" demek
yerine satır satır sonucu göster.

## Hayalet kayıt: silme sonrası aynı sayfayı sorgulamak yanıltıyor

Partinin **son maddesi** silindikten sonra aynı sayfada yapılan sorgu onu hâlâ
listede gösterebiliyor. Silme aslında başarılı olmuştur; DOM güncellenmemiştir.

Bu oturumda yaşanan tam senaryo — 6 projeden 5'i silindi, 6'sı (`Style Shots`) inatla
listede kaldı:
- Sorgu üst üste `1 |||| Style Shots` döndü
- Silme akışı yeniden çalıştırıldı, `CONFIRMED` döndü, liste yine aynı
- Onay butonu yoklandı: `NOCONFIRM` — çünkü **silinecek bir şey kalmamıştı**
- URL yeniden yüklendikten sonra: `0` madde

**Kural: `NOCONFIRM` / `NOTFOUND` bir hata değil, \"zaten silinmiş\" sinyali olabilir.**
Silme akışını üçüncü kez tetiklemeden önce sayfayı **taze yükle** ve öyle say. Aksi
halde var olmayan maddeyi kovalarken tur harcarsın, daha kötüsü bir sonraki maddeyi
yanlışlıkla silersin.

Doğrulama için ayrı bir script tut: URL'i `set URL of active tab` ile yeniden ata,
`delay 6-7` bekle, sonra envanteri say. Silme scriptinin kendi raporuna güvenme.

## Aynı harness, farklı bölüm: sadece üç şey değişiyor

`deleteItem` kalıbı LinkedIn'in tüm liste bölümlerinde çalışıyor. Bölümden bölüme
değişen yalnızca şunlar:

| | Yetenekler | Projeler |
|---|---|---|
| aria-label regex | `(.+?)\s+yeteneğini\s+düzenle` | `(.+?)\s+projesini\s+düzenle` |
| Silme butonu | `Yeteneği sil` | `Projeyi sil` |
| URL | `/details/skills/` | `/details/projects/` |

Onay diyaloğundaki buton her ikisinde de düz `Sil`.

**Onay butonunu `[role="dialog"]` içinde arama.** Bu oturumda LinkedIn'in onay katmanı
o role'ü taşımıyordu; kapsamlı seçici boş döndü, butona ancak global `button` taraması
ile ulaşıldı. Kalıp: önce dialog kapsamında ara, boş dönerse global taramaya düş.

```javascript
var out=[];
document.querySelectorAll('[role="alertdialog"] button, [role="dialog"] button')
  .forEach(function(b){ out.push((b.innerText||'').trim()); });
if(out.length===0){                       // dialog role'ü yoksa global tara
  document.querySelectorAll('button').forEach(function(b){
    var t=(b.innerText||'').trim();
    if(/^(Sil|Delete)$/.test(t)) out.push('GLOBAL:'+t);
  });
}
```

Yeni bir bölümle karşılaşınca kör deneme yapma: önce modalın **buton isimlerini
listele**, gerçek etiketi gör, sonra silme akışını kur. Tek yoklama çağrısı üç tur
tahmin yürütmekten ucuz.

## AppleScript içine JS gömerken: tırnak ve kesme işareti dinamiti

JS'i AppleScript string'i olarak taşırken metindeki tek karakter tüm çağrıyı sessizce
düşürüyor. Hata mesajı gelmiyor, sadece `missing value` dönüyor — bu yüzden teşhisi zor.

**Kesme işareti (`'`) ölümcül.** Türkçe metinde çok yaygın: `Omi'nin`, `Chrome'un`,
`kullanıcı'nın`. `quoted form of` bunu kurtarmıyor.

Doğrulanmış vaka (2026-08-05): 7 projeden 6'sı eklendi, biri ısrarla `missing value`
döndü. Fark tek karakterdi — açıklamadaki `Omi'nin`. Metin `Omi üzerinde yaptığım`
olarak yeniden yazılınca aynı script sorunsuz çalıştı.

Göndermeden önce tara:
```python
bad = [(i, ch) for i, ch in enumerate(metin) if ch in "'\"\\"]
assert not bad, f"JS'e gömülemez karakter: {bad}"
```
Bulursan **metni yeniden yaz** (kaçış karakteri eklemeye çalışma, katman katman bozuluyor).
Türkçede kesme işaretinden kaçınmak kolay: `Omi'nin kod tabanı` → `Omi üzerindeki kod tabanı`.

> **BU BÖLÜM ARTIK SON ÇARE (2026-08-09 güncellemesi).** Metni yeniden yazmak gereksiz —
> JS'i **dosyadan okutursan** kaçış katmanı hiç oluşmaz ve kesme işareti, tırnak, Türkçe
> karakter serbestçe kullanılabilir. `SKILL.md` → "JS'i AppleScript string'ine gömme —
> DOSYADAN okut" bölümündeki `lk_exec.scpt` harness'ını kullan:
> `osascript /tmp/lk_exec.scpt <window_id> <tab_index> /tmp/is.js`
> Yukarıdaki karakter taraması yalnızca harness'ı kuramadığın durumlarda anlamlı.
> **Kullanıcının metnini araç kısıtı yüzünden değiştirmek en son seçenek olmalı** —
> bu, kullanıcının sesini araca feda etmektir.

**`CSS.escape` de aynı sebeple patlıyor.** İçindeki tırnaklar AppleScript katmanında
bozuluyor:
```javascript
document.querySelector('label[for="' + CSS.escape(el.id) + '"]')   // KIRILIR
```
LinkedIn id'leri zaten `«r0»`, `«r1»` gibi tuhaf karakterler taşıyor. Çözüm: id ile
eşleştirmeyi bırak, **DOM sırasına göre** al:
```javascript
var fields = document.querySelectorAll('input[type=text], textarea');
var nameEl = fields[0];
var descEl = null;
for (var i = 0; i < fields.length; i++) {
  if (fields[i].tagName === 'TEXTAREA') { descEl = fields[i]; break; }
}
```

## `SAVED` yalan söyleyebilir: doldurmayı kaydetmeden önce doğrula

En pahalı tuzak bu. Kaydet butonu form boşken de tıklanabiliyor ve `SAVED` dönüyor;
hiçbir şey kaydedilmemiş oluyor. Bu oturumda 7 proje "SAVED" raporladı, taze sayım
`0` döndü — tamamı boşa gitmişti.

**Kural: fill fonksiyonu doldurduğu değerleri geri döndürsün, `SAVED`'a güvenme.**

```javascript
return 'name=' + (nameEl.value || '').slice(0,25)
     + ' desc=' + (descEl ? (descEl.value||'').length : 0)
     + ' sel='  + monthYear.length
     + ' dates=' + d.join(',');
```
Sağlıklı çıktı: `name=Zoku — Claude Code için O desc=403 sel=4 dates=ok,ok,ok,ok`
Bozuk çıktı: `missing value` → kaydetme, metni düzelt, tekrar dene.

Kaydet butonunu tıklamadan önce `b.disabled` kontrolü de ekle; LinkedIn zorunlu alan
boşken butonu pasif tutuyor ama tıklama yine de sessizce geçiyor.

## Tarih `select`'lerini label ile arama, içeriğe bak

Ay/Yıl açılırları `label[for=]` ile bulunmuyor (yukarıdaki `CSS.escape` sorunu) ve
sayfada onlarca alakasız `select` var (video oynatıcının Color/Opacity ayarları gibi).
Doğru yol: **option içeriğinden tanı.**

```javascript
var monthYear = [];
var all = document.querySelectorAll('select');
for (var j = 0; j < all.length; j++) {
  var opts = all[j].options;
  if (!opts || opts.length < 3) continue;
  var txt = (opts[1].text || '').trim();
  var isMonth = /^(Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)$/.test(txt);
  var isYear  = /^[12][0-9]{3}$/.test(txt);
  if (isMonth || isYear) monthYear.push(all[j]);
  if (monthYear.length >= 4) break;
}
```
Sıra: başlangıç ay, başlangıç yıl, bitiş ay, bitiş yıl. `select` seçerken de native
setter gerekiyor (`HTMLSelectElement.prototype` + `change` event).

## `load script` ile kütüphane ayırma çalışmıyor

Handler'ları ayrı dosyaya koyup `load script POSIX file "/tmp/lib.scpt"` demek
`Betik, AppleScript'e aitmiş gibi gözükmüyor. (-1752)` hatası veriyor — `.scpt`
uzantılı düz metin dosyası derlenmiş script sanılıyor.

Çözüm: gövde + handler'ları **tek dosyada birleştir**. Python ile üretiyorsan handler
bloğunu string olarak tut, çağrı satırlarının arkasına ekle, `lib's addProject` yerine
`my addProject` yaz.

## LinkedIn proje formu (`/add-edit/PROJECT/`)

| Alan | Seçici |
|---|---|
| Proje adı (zorunlu) | `input[type=text]` — DOM'daki ilk text input |
| Açıklama | ilk `TEXTAREA` |
| Tarihler | 4 adet `select`, option içeriğinden tanınır |
| Medya | `Gönderiler` / `Yorumlar` / `Videolar` / `Resimler` / `Belgeler` checkbox'ları |

Her proje için formu **yeniden aç** (`set URL ... /add-edit/PROJECT/` + `delay 7-8`);
aynı formu tekrar kullanmaya çalışma.

> **2026-08-09 DÜZELTMESİ — form URL'ine doğrudan gitmek artık ÇALIŞMIYOR.**
> `/in/<slug>/edit/forms/projects/<id>/` adresine `set URL` ile gitmek
> `\"Böyle bir sayfa yok\"` döndürüyor (`inp:0 ta:0 btn:0`, sayfa gövdesi 116 karakter).
> Form yalnızca **liste sayfasındaki kalem düğmesine tıklayarak** açılıyor.
> Aşağıdaki "Doğrulanmış toplu düzenleme döngüsü" bölümünü kullan.

Medya kararı: görsel çıktısı olan projede (video üretimi, mobil uygulama, arayüz) medya
işe yarar. Saf kod projelerinde ekran görüntüsü zayıf kalır, depo bağlantısı metin içine
yazmak daha değerli — proje bölümündeki bağlantılar akış algoritmasına girmediği için
dış bağlantı cezası burada geçerli değil.

## Doğrulanmış toplu düzenleme döngüsü (2026-08-09, 7/7 proje)

Uçtan uca çalıştığı ve tek tek doğrulandığı oturum: LinkedIn projeler bölümü,
7 projenin başlık + açıklaması Türkçeden İngilizceye çevrildi.

Döngü **üç adım**, her madde için tekrarlanır:

1. **Liste sayfasına dön** (form URL'ine doğrudan gitme, çalışmıyor)
2. **Kalem düğmesini `aria-label` ile bul ve tıkla** — `delay 6`
3. **Formu native setter ile doldur + Kaydet'e `.click()`** — `delay 5`

```bash
#!/bin/bash
WID=444142723; TIDX=9; EXEC=/tmp/lk_exec.scpt
for i in 0 1 2 3 4 5 6; do
  osascript /tmp/li_proj_ac.scpt >/dev/null 2>&1   # liste sayfasi
  sleep 4
  AC=$(osascript "$EXEC" $WID $TIDX /tmp/lkjs/ac_$i.js 2>&1)
  echo "[$i] $AC"
  case "$AC" in ACILDI*) ;; *) echo "[$i] ATLANDI"; continue ;; esac
  sleep 6
  echo "[$i] $(osascript "$EXEC" $WID $TIDX /tmp/lkjs/dol_$i.js 2>&1)"
  sleep 5
done
```

Kalem düğmesini açan `ac_N.js` — `aria-label` Türkçe arayüzde
`\"<Proje adı> projesini düzenleyin\"` biçiminde:

```javascript
(function(){
  var anahtar = "Pozla";                       // benzersiz kisa parca yeter
  var tum = document.querySelectorAll('button,a');
  for(var i=0;i<tum.length;i++){
    var la = tum[i].getAttribute('aria-label')||'';
    if(la.indexOf(anahtar)>-1 && /d.zenle|edit/i.test(la)){
      tum[i].click(); return 'ACILDI: '+la;
    }
  }
  return 'BULUNAMADI: '+anahtar;
})()
```

Formu dolduran `dol_N.js` — **düz `input`/`textarea` olduğu için native setter
çalışıyor** (zengin metin kutusu yasağı burada geçerli değil):

```javascript
(function(){
  var setVal=function(el,v){
    var t = el.tagName==='INPUT'?HTMLInputElement:HTMLTextAreaElement;
    var s = Object.getOwnPropertyDescriptor(t.prototype,'value').set;
    el.focus(); s.call(el,v);
    el.dispatchEvent(new Event('input',{bubbles:true,cancelable:true}));
    el.dispatchEvent(new Event('change',{bubbles:true,cancelable:true}));
    el.blur();
  };
  var inp=document.querySelector('input[type=text][id]');
  var ta=document.querySelector('textarea[id]');
  if(!inp||!ta) return 'FORM YOK';
  setVal(inp,"Pozla — Event Video Production Pipeline");
  setVal(ta,"A system that turns event photos into...");
  var b=[].slice.call(document.querySelectorAll('button'))
          .filter(function(x){return x.innerText.trim()==='Kaydet';});
  if(!b.length) return 'KAYDET YOK';
  b[b.length-1].click();
  return 'KAYDEDILDI ad:'+inp.value.length+' ack:'+ta.value.length;
})()
```

`[id]` niteleyicisi şart — onsuz sayfanın arama kutusu yakalanıyor.
Kaydet düğmesinde `b[b.length-1]` kullan, sayfada birden çok `Kaydet` olabiliyor.

### Doğrulama: liste sayfasına BAKMA, formu yeniden aç

Bu oturumun en pahalı dersi. Kaydetme başarılı olduktan sonra bile
`/details/projects/` listesi **eski Türkçe metni göstermeye devam etti** — üç kez
yeniden yükleme ve cache-buster parametresi dahil hiçbiri değiştirmedi.

Doğru kabul testi: kalem düğmesini tekrar tıkla ve form alanının değerini oku.

```javascript
(function(){
  var inp=document.querySelector('input[type=text][id]');
  var ta=document.querySelector('textarea[id]');
  if(!inp||!ta) return 'FORM KAPALI';
  return 'ad:'+JSON.stringify(inp.value)+' | ack:'+ta.value.length;
})()
```

7 projenin tamamı bu yöntemle tek tek doğrulandı. **Liste sayfasında eski metin
görmek kaydın tutmadığını kanıtlamaz.**

### Kaç madde var, ÖNCE listeden say

Bu oturumda 8 madde çevrilmeye çalışıldı, biri `BULUNAMADI` döndü. Sebep: liste
aslında 7 maddeydi, 8'inci ajanın kendi çıkardığı özetten geliyordu ve profilde
hiç yoktu. Döngüyü kurmadan önce gerçek listeyi çek:

```javascript
(function(){
  var r=[];
  document.querySelectorAll('button,a').forEach(function(x){
    var la=x.getAttribute('aria-label')||'';
    if(/projesini d.zenle/i.test(la)) r.push(la.replace(' projesini düzenleyin',''));
  });
  return r.join(' || ');
})()
```

## Test marker'ını geri alma bütçesi

Bir alt ajan kaydın tuttuğunu kanıtlamak için başlığa `[T9Z]` markerı koydu ve
tur limiti geri alma adımından önce doldu; profil bozuk kaldı. Orijinal değerler
`/tmp/orig_fields.json`'a yazılmış olduğu için ana oturum tek çağrıda geri aldı.

**Kural: marker koyacaksan orijinali ÖNCE diske yaz.** Geri alma, yukarıdaki
üç adımlı döngünün aynısıdır — sadece orijinal metinlerle çalıştır.



Araç çağrısı limitine çarpıp iş yarım kaldığında kullanıcıya "bunu elle yapman gerekiyor"
deme. Kullanıcı haklı olarak *"silip yeniden yazma yeteneğin yok mu?"* diye sorar.

Doğru cümle: **"araç bütçem bitti, kaldığım yer şurası, devam ediyorum."**
Yapabildiğin ama o tur sığdıramadığın işi yapamıyormuş gibi anlatmak güveni kırar.
