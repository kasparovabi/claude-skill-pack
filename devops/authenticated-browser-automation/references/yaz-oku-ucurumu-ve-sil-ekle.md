# Yaz-oku uçurumu: form doluyor ama kayıt kabul edilmiyor

Bir web uygulamasında formu programatik doldurdun, Kaydet'e bastın, kutu kapandı,
hata çıkmadı — ama değişiklik görünmüyor. Bu belge o durumun teşhis ağacını ve
doğrulanmış çözümünü verir.

Kaynak vaka: 2026-08-09, LinkedIn profil "Projeler" bölümü, 7 kaydın Türkçe'den
İngilizce'ye çevrilmesi. İki ayrı oturuma yayıldı, ilkinde yanlış teşhis konuldu.

## Belirti

- Form alanları doluyor (`inp.value.length` doğru, karakter sayacı güncelleniyor).
- Kaydet düğmesi mavi/etkin, tıklanıyor, diyalog kapanıyor.
- Hata mesajı yok, konsol temiz.
- Sayfa tazelendiğinde **eski değer** duruyor.
- **Düzenleme formunu tekrar açtığında YENİ değeri gösteriyor** ← en yanıltıcı kısım.

## Neden yanlış teşhis konulur

Düzenleme formunun yeni metni göstermesi "veri sunucuda" sanılır. Değildir:
istemci durumu (React state / bileşen önbelleği) sayfa yenilense bile o oturum
boyunca yaşayabiliyor. Aynı vakada silme onay diyaloğu bile yeni İngilizce başlığı
okudu — yine de sunucuda Türkçe duruyordu.

İlk oturumda bu yüzden "yedisi de çevrildi, doğrulandı" denildi. Kullanıcı ertesi
gün "hâlâ Türkçe" diye döndü. **Doğrulamanın kendisi yanlış yerden yapılmıştı.**

## Ayırıcı test: sahte kayıt ekle (en değerli adım)

Şu soruyu ayırmak gerekiyor: **bayat önbellek mi, reddedilen yazma mı?**

Tek adımda ayrılıyor — listeye **yeni bir kayıt EKLE**:

```javascript
// ekleme formunu aç, doldur, kaydet
setVal(inp, 'ZZTEST Visibility Probe');
setVal(ta,  'Temporary test entry. Will be deleted immediately.');
```

Sonra listeyi tazele:

- **ZZTEST listede GÖRÜNÜYORSA** → önbellek suçlu değil, liste taze veri
  gösteriyor. Demek ki senin düzenleme yazman **sunucu tarafında reddediliyor**.
  → Sil-ekle döngüsüne geç (aşağıda).
- **ZZTEST GÖRÜNMÜYORSA** → sorun okuma yolunda, önbellek/dil sürümü araştır.

Testten sonra ZZTEST'i **hemen sil**. Ekleme ve silme akışları farklı uç noktalar
kullandığı için bu test ucuzdur ve kalıcı hasar bırakmaz.

> Bu test, "8 yöntem denedim hiçbiri olmadı" çıkmazını 3 çağrıda çözdü. Yeni bir
> yazma yöntemi denemeden ÖNCE yap — deneme sayısını değil, teşhisi artır.

## Çözüm: sil + yeniden ekle döngüsü

Düzenleme uç noktası reddediyorsa ekleme uç noktası genelde çalışır (farklı kod
yolu, farklı doğrulama). Döngü:

1. Liste sayfasını aç.
2. Hedef kaydın kalem düğmesini `aria-label` ile bul, tıkla.
3. Formdaki **"Sil"** düğmesine bas → onay diyaloğu açılır.
4. Onay diyaloğundaki **"Sil"**e bas.
5. Liste sayfasına dön, **"Yeni ... ekle"** düğmesine bas.
6. Formu native setter ile doldur, tarih/`<select>` alanlarını ayarla, Kaydet.

Her adım arasında `sleep 5-7`. Tek proje için ~6 `osascript` çağrısı.

### Bash harness (doğrulanmış)

```bash
#!/bin/bash
# tek_proje.sh <index> — sil-ekle döngüsü, her adımı kontrol eder
i="$1"; W=<applescript_window_id>; T=<tab_index>; E=/tmp/lk_exec.scpt

osascript /tmp/liste_ac.scpt >/dev/null 2>&1; sleep 5
AC=$(osascript "$E" $W $T /tmp/lk2/ac_$i.js 2>&1)
[ "$AC" != "ACILDI" ] && { echo "[$i] DURDU: $AC"; exit 1; }
sleep 5
SIL=$(osascript "$E" $W $T /tmp/lk2/sil.js 2>&1)
[ "$SIL" != "SIL" ] && { echo "[$i] DURDU: $SIL"; exit 1; }
sleep 3
ONAY=$(osascript "$E" $W $T /tmp/lk2/onay.js 2>&1)
[ "$ONAY" != "ONAYLANDI" ] && { echo "[$i] DURDU: $ONAY"; exit 1; }
sleep 7
osascript /tmp/liste_ac.scpt >/dev/null 2>&1; sleep 5
YENI=$(osascript "$E" $W $T /tmp/lk2/yeni.js 2>&1)
[ "$YENI" != "EKLEME ACILDI" ] && { echo "[$i] DURDU: $YENI"; exit 1; }
sleep 5
osascript "$E" $W $T /tmp/lk2/dol_$i.js 2>&1
sleep 8
```

Her adım beklenen dizgeyi döndürmezse **durur**. Yarım silinmiş kayıt bırakmamak
için bu şart: kayıt silinip yeniden eklenemezse veri kaybolur.

### Önce TEK kayıtta test et

Toplu koşmadan önce döngüyü **bir** kayıtta çalıştır ve listeden doğrula. Tuttuğunu
gördükten sonra kalanları döngüye al. Kaynak vakada Zoku ile test edildi, sonra
kalan 6 tek komutla geçirildi.

## Silme öncesi zorunlu hazırlık

Silme geri alınamaz. Döngüye girmeden önce:

1. **Mevcut tüm içeriği diske yaz** — başlık, açıklama, tarih. Liste sayfasının
   `innerText`'ini ham olarak da sakla.
2. **Tarihleri ayrıca çıkar.** Yeniden eklerken `<select>` alanlarını doldurman
   gerekir, yoksa tarih bilgisi kaybolur.
   ```python
   import re
   AY = {"Oca":"Ocak","Şub":"Şubat","Mar":"Mart","Nis":"Nisan","May":"Mayıs",
         "Haz":"Haziran","Tem":"Temmuz","Ağu":"Ağustos","Eyl":"Eylül",
         "Eki":"Ekim","Kas":"Kasım","Ara":"Aralık"}
   t = re.findall(r"(\w+)\s+(\d{4})\s*[–-]\s*(\w+)\s+(\d{4})", ham)
   ```
   Listede kısa ay adı (`Şub`) görünür ama `<option>` metni uzun (`Şubat`) —
   eşleştirirken çevir.
3. **Silme onay diyaloğunu her seferinde GÖZLE doğrula** (`mode="vision"`).
   Diyalog silinecek kaydın adını yazar. Yanlış kaydı silmek geri alınamaz.

## `<select>` alanlarını doldurma

Tarih açılır menüleri native setter ile ayarlanır, metin eşleşmesiyle:

```javascript
var ss = function(el, v){
  var s = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set;
  s.call(el, v);
  el.dispatchEvent(new Event('change', {bubbles:true}));
};
var hedef = ["Şubat","2026","Ağustos","2026"];   // baş ay, baş yıl, bitiş ay, bitiş yıl
var sel = [].slice.call(d.querySelectorAll('select'));
var bulundu = 0;
for (var i = 0; i < sel.length && i < 4; i++){
  var m = [].slice.call(sel[i].options).filter(function(o){
    return o.text.trim() === hedef[i];
  });
  if (m.length){ ss(sel[i], m[0].value); bulundu++; }
}
// dönüşte 'tarih:'+bulundu+'/4' raporla — 4/4 değilse tarih eksik kaydedilmiştir
```

Doldurma fonksiyonu **kaç alanın oturduğunu döndürsün**. `4/4` görmeden geçme.

## Doğrulama sırası (bu vaka için kesinleşmiş)

1. `inp.value.length` / karakter sayacı → alan doldu mu. **Kabul testi DEĞİL.**
2. Düzenleme formunu tekrar açmak → **kabul testi DEĞİL**, istemci durumu olabilir.
3. **Liste sayfasını tam sayfa yeniden yükleyip (`set URL` + `delay 12`) oradan
   okumak** → kabul testi budur.

Sayfa içi `fetch(..., {cache:'no-store'})` ile HTML çekmek bu vakada işe yaramadı:
866 KB HTML döndü ama metin ne İngilizce ne Türkçe eşleşti (sunucu tarafı farklı
kodluyor). Voyager API'si (`/voyager/api/identity/profiles/.../profileProjects`)
**HTTP 404** verdi. Gizli pencere **giriş duvarına** takıldı, `curl` **HTTP 999**
(bot engeli) aldı. Yani: karmaşık doğrulama yolları denenmeden önce **en basit
olanı** dene — sekmeyi gerçekten yeniden yükle.

## Genellenebilir kural

> Bir yazma yöntemi "çalışmadı" demeden önce, aynı verinin **başka bir yazma
> yolundan** (ekleme/silme/farklı form) geçip geçmediğini test et. Sorun
> yöntemde değil, o uç noktanın kabul edip etmemesinde olabilir. Sekiz kez aynı
> kapıyı çalmak yerine ikinci kapıyı dene.
