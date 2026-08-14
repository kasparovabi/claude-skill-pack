# Tembel yüklenen listeyi sonuna kadar kaydırmak

2026-08-14'te çözüldü. Belirti: arama sonucu "1.441 sonuç" diyor ama DOM'dan
yalnızca 9 kayıt okunuyor. Kaydırma komutları `ok` dönüyor, hiçbir şey olmuyor,
liste büyümüyor.

Yanlış teşhis: "LinkedIn'de kaydırma çalışmıyor". Doğru teşhis: **yanlış kutuyu
kaydırıyorsun.**

## Kök sebep

Sayfanın kendisi kaydırılabilir değil (`document.documentElement`:
`scrollHeight=812, clientHeight=812`, yani fark yok). Asıl kaydırılabilir kutu,
ilan bağlantısının **dokuz seviye yukarısında** duran bir `div`:

```
0:A            oy=visible  sh=24    ch=24
...
8:UL           oy=visible  sh=3156  ch=3156
9:DIV          oy=auto     sh=3407  ch=626   <-- BU
10:DIV.scaffold-layout__list  oy=visible
```

`window.scrollBy()` ve `document.body` kaydırma bu kutuya hiç dokunmaz. Sınıf
adları rastgele üretilmiş (`VAnvNymswPClnUgkWpEuWevPqq`), yani seçici yazılamaz
— **hesaplanmış stilden bulmak gerekir.**

## Kutuyu bulan ve kaydıran kod

Ölçütler birlikte olmalı: `overflow-y` `auto`/`scroll` VE `scrollHeight`
`clientHeight`'tan belirgin büyük. Yalnız birine bakmak yanlış kutu seçtirir.

```js
(function(){
  var link = document.querySelector('a[href*="/jobs/view/"]');
  if (!link) return 'ILAN YOK';

  var kutu = null;
  var e = link.parentElement;
  for (var i = 0; i < 14 && e; i++) {
    var s = window.getComputedStyle(e);
    if ((s.overflowY === 'auto' || s.overflowY === 'scroll') &&
        e.scrollHeight > e.clientHeight + 100) { kutu = e; break; }
    e = e.parentElement;
  }
  if (!kutu) return 'KUTU YOK';

  var once = kutu.scrollTop;
  kutu.scrollTop = kutu.scrollTop + Math.round(kutu.clientHeight * 0.85);
  kutu.dispatchEvent(new Event('scroll', { bubbles: true }));

  return 'kaydi ' + once + ' -> ' + kutu.scrollTop + ' / ' + kutu.scrollHeight +
         ' | ilan=' + document.querySelectorAll('a[href*="/jobs/view/"]').length;
})()
```

Ölçülen sonuç, üç turda:

```
kaydi 0    -> 532  / 3407 | ilan=9
kaydi 532  -> 1064 / 3417 | ilan=12
kaydi 1064 -> 1596 / 3323 | ilan=17
```

`clientHeight * 0.85` bilinçli: tam ekran boyu kaydırmak aradaki kayıtları
atlatabiliyor, %85 örtüşme bırakıyor.

## Döngü: ilerlemeyi ölç, sabit tur sayısı kullanma

`scrollHeight` her yüklemede değişir (3407 → 3417 → 3323), bu yüzden "sona
geldim" testi yükseklikle yapılamaz. `scrollTop` **artmıyorsa** dur:

```python
onceki = -1
for tur in range(22):
    topla()                      # once oku, sonra kaydir
    durum = js("kaydir.js")
    if "KUTU YOK" in durum or "ZAMAN" in durum:
        break
    konum = int(durum.split("-> ")[1].split(" ")[0])
    if konum == onceki:
        break
    onceki = konum
    time.sleep(2.2)
```

Her turda **önce topla sonra kaydır**. Tersi olursa ilk ekrandaki kayıtlar
hiç okunmaz.

## Tuzaklar

- **Sona kadar kaydırmak listeyi sıfırlayabilir.** Sonuna varıldığında DOM'un
  boşaldığı ve sonraki okumanın `0 aday` döndürdüğü görüldü. Birikimi her turda
  Python tarafında sözlükte topla; DOM'a "en sonda hepsi durur" diye güvenme.
- **Kaydırma çalıştı ama filtre boş dönüyorsa** sorun kaydırmada değil, aday
  süzgecindedir. Ham `a[href*="/jobs/view/"]` sayısını da bas, ayrımı görürsün.
- **Arka planda tarama dönerken aynı sekmeye dokunma.** İki iş aynı sekmeyi
  paylaşırsa tarama sessizce durur (3/10 terimde kaldı) ve ön plandaki sayfa
  boş görünür. Tarama betiğine kendi sekmesini aç, numarasını parametre geç.
- **Sekme NUMARASI tur içinde kayar — kullanmadan önce URL ile doğrula.**
  "Her iş için yeni sekme aç" kuralının bedeli: her açılan sekme sonraki
  numaraları kaydırır, kullanıcı da kendi sekmesini kapatıp açar. Saklanan
  numara birkaç tur sonra **başka bir sayfayı** gösterir ve okuma/yazma
  sessizce yanlış yere gider.

  2026-08-14 vaka: başvuru formu 19. sekmedeydi, birkaç tur sonra 19 LinkedIn
  aramasına dönmüş, form 20'ye kaymıştı. Alan tarayıcı LinkedIn'in arama
  kutularını döndürdü (`Ünvan, yetenek veya şirket ile arayın`) ve "bu formda
  maaş alanı yok" sonucuna varıldı. Kullanıcı düzeltti: *"Hayır alan var"*.
  Hata sekmedeydi, formda değil.

  Her yazma öbeğinden önce hedefi kimliğinden bul:

  ```applescript
  tell application "Google Chrome"
    set w to (first window whose id is <WID>)
    repeat with i from 1 to count of tabs of w
      if (URL of tab i of w) contains "<ayirt-edici-parca>" then return i
    end repeat
    return "sekme yok"
  end tell
  ```

  Belirti: okunan alanlar hedef sayfaya hiç benzemiyorsa (site menüsü, arama
  kutusu, gezinme) önce sekmeyi doğrula, seçiciyi düzeltmeye kalkma.

## Sabit `sleep` ile okumak sessizce ÇÖP veri üretir

Kaydırma çözüldükten sonra sıradaki tuzak, ve bu daha sinsi: sayfa geç
yüklenince `innerText` **boş dönmez**, gezinme menüsünü döner.

2026-08-14 vaka: altı ilan sırayla açıldı, her biri ~1600 karakter
döndürdü, altısı da "başarılı okundu" göründü. Arkasındaki puanlayıcı
altısına birden `kod:0 dil:0 diploma:0` verip hepsini "sınırda" ilan
etti. Ham metnin ilk satırlarına bakınca gerçek çıktı:

```
=== Ilan A ===
0 bildirim
Aramaya geç
Ana içeriğe geç
Ana Sayfa
Ağım
İş İlanları
```

İlan gövdesi hiç gelmemişti. Elle açılınca eleme sebebi olan şart
görüldü: *"at least three years of experience building and shipping
production software"*.

Süre değil **içerik** bekle, ve her kaydı damgala:

```python
def oku(kimlik):
    goto(kimlik)
    for deneme in range(9):
        time.sleep(3)
        genislet()                    # "daha fazla" / "see more"
        metin = govde_oku()
        if len(metin) > 400 and "Ana Sayfa" not in metin[:200]:
            return metin, "OK"
    return metin, "BOS"
```

Menü çapası (`Ana Sayfa`, `Skip to main content`, `Aramaya geç`) ilk 200
karakterde görünüyorsa gövde gelmemiştir. `BOS` işaretli kayıtları elle
aç, tarama sonucuna karıştırma.

Gövde çıkarıcı da esnek olmalı: aradığın başlık (`Requirements`,
`Qualifications`) her sitede yok. Önce dil-bağımsız kapsayıcı çapayı
dene (`İş ilanı hakkında`, `About the job`), sonra bölüm başlıklarını,
en son ham metnin başını al.

> **Bütün kayıtlar aynı puanı aldıysa önce OKUMADAN şüphelen.** Tekdüze
> sonuç bir bulgu değil, boru hattının kırıldığının işaretidir. Ham
> metnin ilk üç satırını gözle oku; menü görüyorsan o tarama çöptür.

## Her turu ANINDA diske yaz

İlk sürüm bütün terimleri bellekte tutup en sonda yazıyordu; betik
onuncu terimde takılınca biriken her şey uçtu ve günlükte `toplam: 0`
kaldı. Toplama döngüsü dosyaya `append` etmeli, tekilleştirme de
dosyadan okunmalı. Böylece tarama kesilse bile o ana kadarki iş durur ve
yeniden çalıştırmak kaldığı yerden devam eder.

## Genelleme

Bu kalıp LinkedIn'e özgü değil. Sanal listeleme kullanan her arayüzde
(sonsuz kaydırma, sanal tablo, sohbet geçmişi) aynı şey geçerli: **kaydırılacak
öğe, içeriğin kendisi değil onu saran ve `overflow` taşıyan atadır.** Önce
zinciri yazdır, sonra kaydır.
