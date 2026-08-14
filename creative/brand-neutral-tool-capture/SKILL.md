---
name: brand-neutral-tool-capture
description: "Use when showing a client tool as proof. Strips branding."
version: 1.0.0
platforms: [macos]
metadata:
  hermes:
    tags: [screenshot, screen-recording, branding, proof-of-work, ffmpeg]
    category: creative
---

# Çalışan bir aracı marka sızdırmadan kanıt olarak göstermek

Bir otomasyonu/aracı dışarıya anlatırken (LinkedIn postu, portfolyo, sunum) elde
iki seçenek var: aracın **çıktısını** göstermek ya da **kendi ekranını**. İkincisi
daha güçlü, ama müşteri/kurum markası ekranda duruyor.

Bu skill o dengeyi kuruyor: aracın gerçek arayüzünü kaydet, marka izlerini kaldır.

## Ne zaman

- Danışmanlık verilen kurum için yapılmış bir aracı kamuya gösterme
- "Parametrik kurdum", "şu akışı otomatikleştirdim" iddiasını kanıtlama
- Portfolyo/CV için ekran görüntüsü veya kısa demo videosu

**Kullanma:** araç zaten senin markansa (nötrlemeye gerek yok), ya da anlatılan
şey görsel değilse (cron, API, veri işleme).

## 1. Çıktı değil ARACIN EKRANI

Kullanıcının doğrudan talimatı (2026-08-10):

> *"bu tarz işlerde işin kendisine ait video veya görsel paylaşsak daha iyi olur"*

Fark ölçülebilir. Tasarım çıktısı "güzel bir tabela" gösterir; araç ekranı
**çalışan bir sistem** gösterir. Tek karede tip seçici, ölçü alanları, dil
seçimi ve canlı önizleme aynı anda görünür — yani metindeki "parametrik kurdum"
iddiası anlatılmadan kanıtlanır.

Aynı oturumda önce çıktı görselleri üretildi (5 SVG → PNG kolaj), kullanıcı
kabul etmedi. Araç ekranı ilk denemede kabul gördü.

## 2. Nötrleme merdiveni — dördü de gerekli

Bir katmanı atlarsan kullanıcı yakalar. Sırayla:

| Katman | Ne yapılır |
|---|---|
| 1. Metinler | Kurum adı → uydurma ad (MAARİF → ORION). DOM text node'larını gez |
| 2. Form değerleri | `input` alanlarındaki kurum adları da değişmeli, ayrı geçiş ister |
| 3. Gerçek yer adları | Ülke/şehir/semt adları müşteriyi ele verir (Kamerun, Yaoundé → uydurma) |
| 4. **Amblem ŞEKLİ** | Renk değil, geometrinin kendisi |
| 5. Arayüz renkleri | Marka rengi düğmelerde/kenarlıklarda kalır, hesaplanmış stili tara |

### En kritik: amblemin ŞEKLİ de markadır

İlk denemede sadece renk ve metin değiştirildi. Kullanıcı:

> *"ama logo hala maarif logosu"*

Haklı. **Amblemin geometrik deseni markanın en ayırt edici parçası**, belki
adından bile fazla. Rengini değiştirip şeklini bırakmak, adı silip logoyu
bırakmakla aynı şey.

Çözüm: amblem path'lerini gizle, yerine aynı kutuda/ölçekte nötr bir geometri
koy (sekizgen, daire). Kutu ve ölçek korunmalı ki aracın yerleşimi bozulmasın.

Amblemi ayırt etme sinyali — marka amblemleri çok kırıklı uzun path taşır:

```js
var amblemMi = pathlar.some(function(p){
  var d = p.getAttribute('d') || '';
  return d.length > 400 && (d.match(/L/g) || []).length > 30;
});
```

Hazır ve çalıştırılmış JS'in tamamı (metin, form, amblem, renk):
`references/notrleme-js-tarifi.md`

### Logotype: harf harf çizme, gerçek metin koy

Elle path'lerle "ORION" çizmek denendi, ekranda **"IVTIC"** gibi okundu. Gizlenen
grubun yerine `<text>` koymak hem okunur hem dürüst — amaç markanın YERİNİ
tutmak, taklidini yapmak değil.

**Koordinat uzayı tuzağı:** `<text>` öğesini SVG kökünün `viewBox` birimlerine
göre konumlandırma. Gizlediğin grup kendi `transform` (translate+scale) değerini
taşır; metni **o grubun içine** koy, ölçüyü `getBBox()` ile grubun iç
koordinatından al. Dışarıda kurulan metin 126x65'lik bir viewBox'ta 308 birim
genişliğe çıkıp ekrandan taştı.

## 3. Ekran görüntüsü

```bash
screencapture -x /tmp/ham.png          # -x = deklanşör sesi yok
```

Sonra tarayıcı çerçevesini kırp. Oranı gözle ölç (`vision_analyze` ile "araç
ekranın hangi bölgesinde" diye sor), sabit piksel varsayma:

```python
from PIL import Image
im = Image.open('ham.png'); w, h = im.size
im.crop((0, int(h * 0.122), w, h - 6)).save('ekran.png')
```

Sekme çubuğu **ve yer imi çubuğu** ayrı ayrı kesilmeli; ilk kırpma sekmeleri
alıp yer imlerini bıraktı, ikinci turda fark edildi.

## 4. Video turu

Aracın farklı modlarını gezdirmek tek karenin anlatamadığını anlatır.

### Sıra kritik: önce nötrle, sonra kaydet

İlk denemede kayıt önce başlatıldı → **ilk karede MAARİF logosu** duruyordu.
Turu başlat, ilk mod nötrlensin, **sonra** `screencapture` çağır.

### `screencapture -v` ile `-R` birlikte ÇALIŞMIYOR

Doğrulandı: bölge parametresiyle video kaydı **boş dosya** üretip `exit 1`
döner, hata mesajı basmaz. Tam ekran kaydet, ffmpeg ile kırp:

```bash
screencapture -v -V 18 /tmp/ham.mov     # -V = saniye, kendi kapanır
ffmpeg -v error -i /tmp/ham.mov \
  -vf "crop=2290:1270:0:295,scale=1280:-2" \
  -c:v libx264 -crf 22 -pix_fmt yuv420p -an /tmp/video.mp4 -y
```

`-V` ile sabit süre ver; arka planda çalıştırıp `kill -INT` göndermek kırılgan.

### Nötrlemeyi tekrar tekrar çağır, MutationObserver KURMA

Her mod değişiminde önizleme yeniden çizilir ve marka geri gelir. Refleks
`MutationObserver` kurmak oluyor — **iki denemede de sayfayı kilitledi**
(`AppleEvent zaman aşımına uğradı -1712`), çünkü nötrleme kendi değişikliğini
tetikleyip sonsuz döngüye giriyor. `attributes:false` ve yeniden-giriş kilidi
de kurtarmadı.

Çalışan yol basit: her mod değişiminde nötrlemeyi birkaç gecikmeyle çağır.

```js
guvenliNotrle();
setTimeout(guvenliNotrle, 150);
setTimeout(guvenliNotrle, 400);
setTimeout(guvenliNotrle, 800);
```

**Sekme kilitlendiyse kurtarma:** `set URL of tab N to "about:blank"`, 6 saniye
bekle, sonra aracı yeniden yükle. Chrome'u kapatmaya gerek yok.

## 5. Doğrulama — her turda gözle bak

Kare örnekle, kolaj yap, `vision_analyze` ile sor. Sayı değil göz karar verir.

```bash
for t in 1 4 7 10 13 16; do
  ffmpeg -v error -ss $t -i video.mp4 -vframes 1 kare_$t.png -y
done
ffmpeg -v error -i kare_1.png -i kare_4.png -i kare_7.png \
       -i kare_10.png -i kare_13.png -i kare_16.png \
  -filter_complex "[0:v][1:v][2:v]hstack=3[a];[3:v][4:v][5:v]hstack=3[b];[a][b]vstack=2,scale=1500:-1" \
  -frames:v 1 kontrol.png -y
```

**Kare çıkarırken `.png` kullan, `.jpg` değil.** `screencapture` çıktısında
`.jpg` hedefi mjpeg kodlayıcısını *"Non full-range YUV is non-standard"* hatasıyla
düşürüyor ve **hiç dosya yazılmıyor**; hata ffmpeg gürültüsü içinde kaybolabilir.

Sorulacak soru sabit: *"Marka izi (amblem, kurum adı, kurumsal renk, gerçek yer
adı) kaldı mı? Tarayıcı çubuğu kırpıldı mı?"*

Bu oturumda gözle bakmak dört ayrı kaçağı yakaladı: ilk karede logo, "BEYAZ"
düğmesinde marka turkuazı, "Kamerun" yer adı, kırpılmamış yer imi çubuğu.
Hiçbiri programatik kontrole takılmazdı.

## Pitfalls

1. **Sadece rengi değiştirip amblemi bırakmak.** Şekil de markadır — en sık
   yapılan ve kullanıcının hemen yakaladığı hata.
2. **Gerçek yer adlarını unutmak.** Kurum adını temizleyip "Yaoundé, Kamerun"
   bırakmak müşteriyi aynı ölçüde ele verir.
3. **Kayıt başladıktan sonra nötrlemek.** İlk kareler markayı gösterir.
4. **`screencapture -v -R` kombinasyonuna güvenmek.** Sessizce boş dosya.
5. **MutationObserver ile sürekli nötrleme.** Sayfayı kilitler; tekrar çağrı yeterli.
6. **Kare çıkarırken `.jpg` kullanmak.** mjpeg renk aralığı hatası, dosya oluşmaz.
7. **`<text>` öğesini yanlış koordinat uzayında kurmak.** Gizlenen grubun içine
   koy, `getBBox()` ile ölç.
8. **Tek kırpma oranıyla yetinmek.** Sekme çubuğu ve yer imi çubuğu ayrı katman.
9. **Aracın kaynak dosyalarını değiştirmek.** Nötrleme çalışma kopyasında
   (`/tmp`'ye kopyalanan HTML + DOM üzerinde) yapılır; depoya dokunma.

## Verification Checklist

- [ ] Kaynak dosyalar değişmedi (`git diff --stat` boş)
- [ ] Metin, form değeri, yer adı, amblem şekli, arayüz rengi — beşi de nötr
- [ ] Nötrleme kayıttan ÖNCE tamamlandı
- [ ] Kare kolajı üretilip `vision_analyze` ile bakıldı
- [ ] Tarayıcı sekmeleri VE yer imi çubuğu kırpıldı
- [ ] Videonun ilk ve son karesi ayrıca kontrol edildi
