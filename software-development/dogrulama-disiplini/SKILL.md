---
name: dogrulama-disiplini
description: Use when a check passes but reality disagrees.
---

# Doğrulama Disiplini — ölçer doğru şeyi mi ölçüyor?

## Ne zaman yükle

- Bir denetim/test/lint "TEMİZ" diyor ama kullanıcı hâlâ sorun görüyor
- Bir kural yazdın ve "artık çalışıyor" diyeceksin
- İki şeyin aynı/farklı olduğunu bir metrikle kanıtlamaya çalışıyorsun
- Kullanıcı ekranda gördüğü bir şeyi rapor etti, senin ölçümün tersini söylüyor
- Bir filtre/tarayıcı çok fazla ya da çok az sonuç döndürdü
- **Bir denetim aynı arızayı ikinci kez kaçırdı** ve "eşiği gevşetelim mi"
  diye düşünüyorsun (cevap genelde hayır — aşağıdaki eksen bölümü)
- **Bir sistem/ajan kendi arızası için çözüm önerdi** ve uygulamak üzeresin

## Temel ilke

Bir ölçüm üç şekilde yanlış olabilir ve üçü de "başarılı" görünür:

| Arıza | Belirti | Örnek |
|---|---|---|
| **Yanlış şeyi ölçmek** | Ölçüm doğru, soruyla alakasız | Dosya hash'i "bayt aynı mı" der, "izleyen aynı şeyi mi görüyor" DEMEZ |
| **Yanlış yerde aramak** | Doğru olgu, yanlış konum | Bağlaç cümlenin *herhangi* yerinde aranıyordu; akışı kuran şey cümle *başında* olması |
| **Gürültüyü saymak** | Bol sonuç, sıfır değer | Log tarayıcı 135 "hata" buldu, hepsi aracın kendi telemetrisiydi |

Dördüncüsü daha sinsi: **ölçüm hiç çalışmıyor** ama yine de "geçti" diyor —
kural yazıldı, çalışma zamanına hiç ulaşmadı.

## Merdiven — ikinci basamakta durma

Bir kuralın/düzeltmenin yürürlükte olduğunu iddia etmeden önce:

1. **Dosya doğru yerde mi?** (yazdım ✓)
2. **Çalışma zamanı onu okuyor mu?** (dosyanın varlığı bunu KANITLAMAZ)
3. **Prompt/kod içinde görünüyor mu — ve NEREDE görünüyor?** (ortada
   kalan talimat düşer; kritik kural sona konur)
4. **Çıktı gerçekten kurala uyuyor mu?** (üret, ölç, gözle bak)

Çoğu "düzelttim" iddiası 1. basamakta kalır. En az 3'e kadar çık.

## Kullanıcı gözlemi > senin ölçümün

Kullanıcı **görsel** bir şey rapor ediyorsa (video, görsel, ekrandaki
mesaj, metnin tonu), dosya sistemi kanıtıyla karşı çıkma. O ekranı
görüyor, sen dosyaya bakıyorsun.

- Önce kullanıcının gördüğünü **yeniden üret**: kare çıkar, yan yana koy,
  `vision_analyze` ile incele, gerekirse kullanıcıya gönder.
- Aynı iddiayı **ikinci kez** savunuyorsan dur.
  **Üçüncü kez** savunuyorsan kesinlikle yanılıyorsun.
- "Kanıt sunma" refleksi burada zararlı. Kanıt değil, ortak görüntü üret.

## Kullanıcı kusuru İŞARET ETTİYSE teşhis UYDURMA (9 Ağu 2026 — KRİTİK)

Kullanıcı gözlemi bölümünün devamı ve en pahalı hâli. Kullanıcı belirli bir
çıktıyı işaret edip "bu yanlış" dediğinde, iki ayrı hata yapılabilir:

1. İtiraz etmek (yukarıda kapsandı, "kullanıcı gözlemi > senin ölçümün").
2. **Kabul etmek ama YANLIŞ SEBEP uydurmak.** Bu daha sinsi, çünkü işbirlikçi
   görünür ve kullanıcı bir süre fark etmez.

Doğrulanmış vaka: kullanıcı bozuk bir cümleyi gösterdi — *"Sınır koymak
yetersiz kaldığında sistem sınırın etrafını dolar."* Cümle **totoloji** diye
etiketlendi, "kendi kendini tanımlıyor, boş derinlik" denildi. Yanlıştı.

Gerçek kusur **kelime seçimiydi**: "etrafını dolamak" = sarmak, çevrelemek.
Anlatılmak istenen şey sınıra dokunmadan yanından geçmekti, onun karşılığı
"etrafından dolanmak". Cümle boş değildi, yanlış fiil kullanılmıştı. Kullanıcı
ikinci kez döndü: *"yanlış diye verdiğim cümleyi bile yanlış değerlendirdin."*

### Neden bu hata bileşik faiz gibi büyür

Yanlış teşhis → yanlış düzeltme → **yanlış kalıcı kural**. O oturumda hafızaya
"anlamı denetle, totoloji ara" diye yazıldı; yazılması gereken "kelimenin
gerçek anlamına bak" idi. Uydurulmuş teşhisten doğan kural sonraki oturumları
da yanıltır. Teşhis hatası tek seferlik değil, kendini çoğaltan bir hatadır.

### Sıra: ucuzdan pahalıya, atlamadan

Kullanıcı bir metin/çıktı kusurunu işaret ettiğinde:

1. **KELİME / SEMBOL katmanı.** Her fiil, deyim, terim gerçekten o anlama
   geliyor mu? Türkçe deyim için TDK'ya sor:
   `curl -s "https://sozluk.gov.tr/gts?ara=<kalıp>"` —
   `{"error":"Sonuç bulunamadı"}` dönerse o kalıp dilde YOK demektir.
2. **YAPI katmanı.** Dilbilgisi, kip, ek uyumu, referans, kapsam
   (alıntı nerede bitiyor, hangi ifade neye bağlanıyor).
3. **ANLAM katmanı.** Totoloji, boş derinlik, çelişki.

En sık kusur 1. katmandadır; teşhis çoğunlukla 3'ten başlatılır çünkü orası
daha "derin" görünür. Sırayı atlama.

### Emin değilsen SOR

"Kelime seçimi mi, kuruluş mu, anlam mı?" diye sormak zayıflık değil.
Uydurulmuş teşhis, teşhis koymamaktan **kötüdür**, çünkü sahte bir kesinlik
taşır ve kullanıcı onu doğru sanıp üstüne inşa eder.

### Denetçinin TEMİZ demesi cümlenin doğru olduğunu kanıtlamaz

Aynı cümle otomatik denetçiden TEMİZ geçmişti. Denetçi üslup kalıplarını
(klişe, devriklik, kalıp ifade) yakalar; **yanlış kelime seçimini yakalamaz**
çünkü öyle bir ekseni yoktur. Bu, yukarıdaki "eksik boyut" bölümünün metin
alanındaki karşılığı: eşiği gevşetmek değil, sözlük ekseni eklemek gerekir.

## Puan 10/10 oldu ama çıktı hâlâ bozuk (10 Ağu 2026)

Yukarıdaki "eksik boyut" bölümünün AYNA hâli. Orada denetim TEMİZ diyordu ve
arıza ölçülmeyen eksendeydi. Burada puan **tavana vurdu** ve arıza yine
ölçülmeyen eksende duruyor — ama bu hâli daha tehlikeli, çünkü yükselen bir
puan ilerleme hissi verir ve gözle bakma refleksini söndürür.

Doğrulanmış vaka: bir çıktı, referans çıktıya karşı beş turda puanlandı.
5,41 → 7,28 → 8,32 → 9,06 → **10,00**. Hiç gerilemedi, dört gerçek yapısal
hata bulundu ve düzeltildi. Sonra çıktı görsele çevrilip bakıldı: iki kusur
duruyordu (bir öğe yanlış ölçekte, bir metin okunmuyordu). Puanlayıcı ikisini
de göremiyordu çünkü o eksenler hiç tanımlanmamıştı.

> **Kural: puan, ölçtüğün eksende 10/10 der. Ölçmediğin eksen hakkında hiçbir
> şey söylemez — ve "10/10" ifadesi bunu gizler.**

Bu, tam olarak kullanıcının kendi denetim postunda yazdığı şeyin başına
gelmesiydi: bir tekniğin sahibi 10/10 hedefleyip 5,05'te kalmıştı; burada
10/10'a ulaşıldı ama *ölçülen* şeyde ulaşıldı.

### Uygulama

1. Puanı raporlarken **ölçülen eksenleri say**. "10/10" değil, "tanımlı 7
   eksende 10/10".
2. Tavan puandan sonra **mutlaka farklı modalitede bak**: sayısal ölçüm
   bittiyse render et ve `vision_analyze` ile gözle. Sayı iyi diye görsel iyi
   değildir.
3. Gözle bulunan kusur için **yeni eksen ekle**, eskisini bozma (bkz. eksik
   boyut bölümü, madde 5).
4. Puan yükselirken duran bir kusur varsa, o kusur eksen kümesinin dışındadır
   — daha çok tur koşmak onu çözmez.

### Ama önce: EKLEYECEĞİN EKSENİN gerekli olduğunu da ölç

Bu bölümün kendi tuzağı. Tavan puandan sonra gözle bir kusur görülünce refleks
şu olur: *\"puanlayıcıya şu ekseni eklerim.\"* Aynı vakada tam bunu önerdim
(\"amblem ölçek kontrolü ekleyeyim\"). Ölçünce **gereksiz** olduğu çıktı: aday ile
referansın `transform` değerleri karakterine kadar aynıydı, yani 10/10 doğruydu
ve geometride hiçbir sorun yoktu.

Gerçek kusur ölçüm dışındaydı: elle üretilmiş yer tutucu varlıklar. İnce
çizgiler küçük ölçekte kayboluyordu ve elle çizilmiş harfler okunmuyordu. Yeni
bir eksen bunların hiçbirini yakalamazdı, çünkü sorun *ölçülen nesnede* değil
*beslenen girdide*ydi.

> **Kural: eksen eklemeden önce, aday ile referansı o eksende yan yana bas.**
> Değerler aynıysa eksen zaten sağlamdır; kusur girdide ya da farklı bir
> modalitededir. Aksi hâlde işe yaramayan bir ölçüt eklenir ve puan gürültüsü
> artar.

Ölçüm üç satır: aynı özniteliği iki dosyadan çıkar ve yan yana yazdır.
Eşitse hipotezin yanlıştır, kusuru başka yerde ara.

### Puanın düşmesi her zaman gerileme değildir

Aynı turda bir düzeltme puanı 10,00'dan 8,15'e indirdi. Panik yok: değişiklik
gerçekten iyileştirmeydi (okunmayan çizim, okunur metne çevrildi), ama sayaç
metni fazladan bir öğe saydı. Yani ölçüt gerçeği değil kendi varsayımını
cezalandırdı.

Puan düştüğünde önce sor: **çıktı mı bozuldu, yoksa ölçüt mü şaşırdı?** Cevabı
render edip gözle bak. Ölçüt şaşırdıysa puanı geri kovalama, farkı raporla.

### Kanıt üretirken: gerçek motoru koştur, benzerini yazma

Aynı vakanın ilk denemesi: hızlıca ayrı bir "demo üretici" yazıldı. Çıktı
kaba oldu, beş örnek de aynı göründü, yani kanıtlanmak istenen şeyi hiç
göstermiyordu. Doğrusu, sistemin **gerçek giriş noktasını** çağırmak ve
yalnız girdiyi değiştirmekti.

Referans hedefin gerçek parametrelerini de **çıktısından oku**, tahmin etme.
Bu vakada ölçüler, düzen adları ve alan biçimleri hedef dosyalardan okununca
puan 5,41'den 9,06'ya tek adımda çıktı; dördü de "yanlış varsayım" hatasıydı.

Somut puanlayıcı iskeleti, eşleştirme tablosu ve durma koşulu:
`references/referansa-karsi-puanlama.md`.

Aynı tekniğin **müşteri işini ifşa etmeden kanıt üretme** hâli — gerçek motoru
uydurma bir markayla koşturmak, kaynağa hiç dokunmadan:
`references/notr-marka-kanit-demosu.md`.

## Kod doğru, çalışma zamanı ESKİ kopyayı okuyor (11 Ağu 2026)

Merdivenin 2. basamağının en pahalı hâli ve en çok kandıran biçimi: dosya
doğru, mantık doğru, sözdizimi temiz — ama davranış hiç değişmiyor. Refleks
kodu tekrar tekrar okumak olur, çünkü hata orada aranır. Kodda değildir.

Doğrulanmış vaka: bir kaydırma geçişi eklendi, hiç çalışmadı. Kod dosyada
duruyordu, `node --check` geçiyordu, doğru fonksiyonun içindeydi, değişken
doğru seçiciyle tanımlanmıştı. Beş ayrı tanı turu kodu doğruladı. Sorun şuydu:
tarayıcı betiğin **eski kopyasını** önbellekten veriyordu.

Ölçüm bunu üç satırda bitirdi:

```
diskteki dosya : 24.835 bayt
sunucunun verdiği : 24.835 bayt
TARAYICININ ALDIĞI : 24.276 bayt   ← eski sürüm
```

### Ayırt edici test: çalışma zamanına NE ULAŞTIĞINI sor

Dosyayı okumak, sunucuyu sorgulamak yetmez; ikisi de doğruyu söylüyordu.
Çalışma zamanının elindeki metni sorgula:

```js
var x = new XMLHttpRequest();
x.open('GET', '/dosya.js', false);
x.send();
'uzunluk:' + x.responseText.length +
' | yeni kod var mi:' + (x.responseText.indexOf('<yeni-simge>') > -1)
```

Uzunluk diskteki ile tutmuyorsa ya da eklediğin simge içinde yoksa teşhis
bitmiştir. Kodu bir daha okuma.

### Daha ucuz ön kontrol: kanıt simgesi

Kod doğru görünüyor ama çalışmıyorsa, mantığı incelemeden önce çalıştığını
kanıtlayacak bir sayaç koy ve değerine bak:

```js
window.__SAYAC = (window.__SAYAC || 0) + 1;
```

Sayaç sıfırsa blok hiç koşmuyor demektir — sorun mantıkta değil, yükleme /
çağrılma yolundadır. Sayaç artıyorsa mantığa geçebilirsin. Bu tek satır, o
vakada dört tanı turunu gereksiz kılardı.

### Çözüm ve genelleme

Sürüm damgası önbelleği geçersiz kılar:

```html
<script src="rail.js?v=4" defer></script>
```

Aynı arıza sınıfı tarayıcıya özgü değil. \"Kaynak doğru ama davranış eski\"
her katmanda çıkar: derlenmiş `.pyc`, Docker imaj katmanı, CDN kenarı,
paket yöneticisi kilidi, çalışan sürecin belleğindeki eski modül. Ortak
teşhis hep aynı: **kaynağa değil, tüketiciye ne ulaştığına bak.**

> **Kural: \"kod doğru ama çalışmıyor\" dediğin an, kodu değil TESLİMATI
> ölç. Diskteki bayt sayısı ile tüketicinin aldığı bayt sayısını yan yana
> yazdır.**

Bir de yerelde doğrulayıp \"tamam\" deme: aynı oturumda geçiş yerel sunucuda
test edilmişti, canlı adreste ayrıca kontrol edilmesi gerekti. Test ettiğin
kopya ile kullanıcının açtığı kopya aynı olmayabilir.

## Yasak vs oran: iki farklı denetim türü

Çoğu denetim **yasak listesi**dir: "şunu yapma" (emoji yok, tire yok,
klişe yok). Bir çıktı bütün yasaklardan geçip yine de yanlış olabilir.

Daha değerlisi **oran denetimi**: gerçek örneklerden oluşan bir referans
bankasıyla kıyaslama. "Bu davranış doğal aralıkta mı?"

Yeni kural yazarken sor: *bu bir yasak mı, yoksa referansla kıyaslanan
bir oran mı?* İkincisi daha güçlüdür çünkü eksik olanı da yakalar,
yasak listesi sadece fazla olanı yakalar.

## "TEMİZ dedi ama bozuk" → eşiği gevşetme, EKSİK BOYUTU ara

Bir denetim geçtiği hâlde kullanıcı sorunu görüyorsa refleks şu olur: *"demek
eşik yanlış, gevşeteyim."* Bu refleks çoğunlukla yanlıştır ve iki şekilde zarar
verir — gerçek arızayı yine kaçırır, üstüne yanlış alarm üretir.

Doğru soru eşik değil **boyut**: denetim hangi ekseni ölçüyor, arıza hangi
eksende? Ölçülen eksende ne yaparsan yap, ölçülmeyen eksendeki arıza görünmez.

Aynı oturumda iki bağımsız vaka, ikisi de aynı şekil:

| Denetim | ÖLÇTÜĞÜ | ARIZANIN OLDUĞU | Eşik oynatmak işe yarar mıydı |
|---|---|---|---|
| Altyazı senkron aracı | cue *başlangıcı* konuşmaya oturuyor mu | cue *süresi* ve *cümle sayısı* | Hayır — başlangıçlar zaten doğruydu |
| Çift kayıt yakalayıcı | başlık *yazım* benzerliği (0,53 / eşik 0,86) | ortak *kaynak* + *anahtar kelime* (0,65) | Hayır — kelime örtüşmesi 0,095'ti |

İkinci vaka öğretici: sistemin kendi önerisi \"eşiği düşür\" idi. Ölçüldüğünde o
yolun **hiçbir eşik değerinde** çalışmayacağı çıktı, çünkü iki başlık aynı işi
baştan sona farklı kelimelerle anlatıyordu. Yakalayan sinyal bambaşka bir
eksendeydi.

### Uygulama sırası

1. **Denetimin ölçtüğü ekseni bir cümleyle yaz.** Yazamıyorsan zaten bilmiyorsun.
2. **Arızalı örneği o eksende ölç.** Değer eşiğin yanlış tarafında mı, yoksa
   eksen konuyla alakasız mı?
3. Alakasızsa **yeni bir eksen ara** ve arızalı çift üzerinde ölç. Ayırt edici
   bir sayı vermiyorsa o da yanlış eksendir, devam et.
4. **Yanlış alarm bütçesini ölç.** Yeni eksen tüm veri kümesinde kaç kayıt
   işaretliyor? Doğrulanmış örnek: 2.080 çiftte 9 işaret, en tepede aranan çift.
   Yüzlerce işaret çıkıyorsa eksen fazla geniş.
5. Eski ekseni **kaldırma**, yanına ekle. İkisi farklı arıza sınıfı yakalıyor.

### Sistemin kendi teşhisini de ölç

Bir ajan/rapor kendi arızası için çözüm önerdiğinde (\"eşiği düşürmek lazım\",
\"şu kaynağı eklemek lazım\") bunu onaylanmış tasarım sanma. Öneri bir hipotezdir;
uygulamadan önce arızalı örnek üzerinde ölç. Bu oturumda önerinin yanlış olduğu
ölçümle çıktı ve doğru çözüm başka yerdeydi.

### Gürültü ekseni ile sinyal ekseni

Yeni bir eksen eklerken hangi verinin **sinyal**, hangisinin **ortam gürültüsü**
olduğunu ayır. Ortak kaynak ekseninde rakip/referans linkleri (App Store, Play
Store) sayılırsa birbirinden bağımsız 7 kayıt \"aynı\" görünür — aynı rakip herkesin
kaynağında geçiyordu. Yalnız talebi kanıtlayan kaynakları say.

## Özet rapor ≠ ham kayıt: sayan tarafın filtresi (6 Ağu 2026)

Bir sistemin **kendi raporu**, o sistemin "raporlanmaya değer" saydığı şeyle
sınırlıdır. Ham olay kaydı ise her şeyi tutar. İki sayı çeliştiğinde ikisi de
doğru olabilir — fark, sayan tarafın filtresidir.

Doğrulanmış vaka: GitHub'ın haziran 2026 availability raporu **"altı olay"**
diyor. Aynı ayın `githubstatus.com/api/v2/incidents.json` kaydında **18** olay
duruyor. Aradaki 12'si `impact: minor` etiketli ve rapora hiç girmemiş. Rapor
yalan söylemiyor, sadece kritik olanları sayıyor.

Refleks: bir vendor/sistem/ajan kendi performansı için **toplu bir sayı**
verdiğinde, o sayıyı ham olay kaydına karşı çapraz kontrol et. Sapma varsa
sebep genelde eşik değil **sınıflandırma**: hangi olay hangi etikete konmuş.

Aynı tuzak kendi sistemlerinde de var: gösterge yeşil kalırken kullanıcı gün
boyu tökezliyor olabilir, çünkü tökezlemeler "minor" sayılıp panele hiç
yansımıyor. Ölçtüğün metrik ile kullanıcının hissettiği şey aynı eksen mi?

### Ham kaydın kendi penceresi de sınırlı olabilir

Ham log'a ulaşmak yetmez, **kapsamını ölç**. Aynı vakada status API sayfa
başına 50 kayıt döndürüyordu, yani eldeki veri yalnızca 6 haziran sonrasını
kapsıyordu. Nisan ve mayıs sayıları o pencereye hiç girmiyordu.

Sonuç: bir trend grafiği hazırlanırken doğrulanamayan iki ay **çıkarıldı**,
uydurulmadı. Kural — kaynağın döndürdüğü ilk ve son kaydın tarihini yazdır,
istediğin aralığı gerçekten kapsıyor mu bak. Kapsamıyorsa o dönem hakkında
sayı verme.

```
kayitlar = [...]                      # ham log
print(min(tarihler), "->", max(tarihler), len(kayitlar))
# istenen aralik bu pencerenin DISINA tasiyorsa: o kismi raporlama
```

## Yedek mekanizma sessizce bozulur (6 Ağu 2026)

Birincil iş çalıştığı sürece, onu kurtarmak için yazılmış telafi/watchdog
mekanizmasının bozuk olduğu **fark edilmez**. Arıza ancak gerçekten ihtiyaç
duyulduğu gün ortaya çıkar, yani en kötü anda.

Vakada telafi bekçisi tetiklendi ve daha ilk satırda çöktü; asıl iş o gün
şans eseri kendi başına koştuğu için kimse görmedi. Kayıt yalnızca kendi log
dosyasında duruyordu.

Refleks: bir watchdog/telafi/fallback yazdıysan **birincili bilerek
devre dışı bırakıp** yedeği tek başına koştur. "Kuruldu" ile "çalışıyor"
arasındaki fark tam olarak bu testtir.

Periyodik kontrol: yedek mekanizmanın kendi log dosyasının **son satırına**
bak. Son giriş bir hata izi (traceback) ile bitiyorsa yedek aylardır ölü
demektir; `last_status: ok` görüntüsü bunu göstermez, çünkü çoğu zamanlayıcı
yalnızca sürecin başlatılabildiğine bakar.

## Eşik kalibrasyonu — tahmin etme, ölç

Benzerlik/eşik değeri seçerken gerçek veriyle iki dağılımı ölç:

```
aynı sayılması gerekenler   → gözlenen aralık
farklı sayılması gerekenler → gözlenen aralık
eşik = iki aralığın ORTASI, en yakın karşı örneğe geniş marj bırakarak
```

Eşiği bir sınıra "yakın" seçme. Bir oturumda 55 seçildi, en yakın karşı
örnek 58'di — yanlış alarma bir adım kalmıştı. 30'a çekilince iki tarafa
da geniş pay kaldı.

## Ölçerin kendisini test et (mutasyon testi)

Bir denetim eklediğinde iki test birden yaz:

1. **Yakalama testi** — hatalı örnek verildiğinde uyarıyor mu?
2. **Yanlış alarm testi** — temiz örnek verildiğinde susuyor mu?

Sadece birincisini yazmak yetmez: her şeye "hata" diyen bir denetim de
yakalama testini geçer. Bir oturumda dört hatanın üçü metinde değil,
metni denetleyen araçtaydı.

## Aracın hata mesajı bir HİPOTEZDİR, kanıt değil (13 Ağu 2026)

Bir araç net bir gerekçeyle başarısız olduğunda, o gerekçeyi kullanıcıya
olgu diye aktarmak kolaydır. Mesaj kesin konuşur, üstelik çoğu zaman
haklıdır. Ama onu **kendin ölçmediysen** aktardığın şey aracın iddiasıdır,
senin bulgun değil.

Doğrulanmış vaka: bir video indirilemedi, araç *\"this video is not available
from your location due to geo restriction\"* dedi. Bu kullanıcıya olgu olarak
iletildi. Kullanıcı itiraz etti: *\"nasıl italya dışından gözükmüyor dedin
anlamadım\"*, çünkü kendi telefonunda video açılıyordu.

İtiraz üzerine yayıncının kendi dağıtım ucu iki farklı istemci kimliğiyle
çağrıldı ve cevap doğrudan okundu:

```
masaüstü kimliği : .../video_no_available.mp4   + <geoprotection> alanı
mobil kimliği    : .../video_no_available.mp4   + <geoprotection> alanı
```

İddia **doğru çıktı**, ama doğrulama itirazdan sonra yapıldı. Sıra yanlıştı.
Üstelik ölçüm fazladan bir şey de verdi: kısıt istemci türüne değil çıkış
adresine bakıyordu, yani kullanıcının telefonunda açılması iddiayla
çelişmiyordu. Bu ayrım ancak ölçülünce görülebilirdi ve kullanıcının
kafasındaki asıl soruyu o cevapladı.

> **Kural: bir aracın hata mesajını kullanıcıya aktarmadan önce, o iddiayı
> bağımsız bir çağrıyla üret. Doğru çıksa bile ölçüm, iddianın kapsamını ve
> kullanıcının karşı gözlemiyle nasıl uzlaştığını gösterir.**

Kullanıcı karşı bir gözlem sunduğunda (\"bende çalışıyor\") bu, iddiayı
çürütmek zorunda değildir. İki gözlem farklı koşullarda alınmış olabilir.
Ölçüm, hangisinin hangi koşulda geçerli olduğunu ayırır; tartışma ayırmaz.

### Ölçüm kararı değiştirmez, sadece gerekçeyi sağlamlaştırır

Aynı vakanın devamı: kısıt doğrulandıktan sonra kullanıcı baskıyı artırdı
(*\"acil ihtiyacı var\"*, *\"ne gerekiyorsa yapıp çöz\"*, *\"gerekiyorsa tarayıcıyı
sürerek çöz\"*). Erişim kısıtını aşmamak doğru karardı ve aracın değişmesi
(tarayıcı yerine indirici) bunu değiştirmedi.

Burada doğrulama disiplininin katkısı şu: ölçüm yapılmış olduğu için
*\"yapamam\"* cümlesi bir tahmin değil, gösterilebilir bir bulguya dayanıyordu.
Reddin yanına **çalışan bir alternatif** koy (meşru kanal, hazır yazışma
metni, en hızlı gerçekçi yol). Ölçülmüş bir sınır artı somut alternatif,
ölçülmemiş bir rediten hem daha ikna edici hem daha yardımcıdır.

## Tek seferde TEK değişken oynat (13 Ağu 2026)

Bir sorgu/filtre beklenmedik sonuç döndürdüğünde iki şeyi aynı anda
değiştirmek en sık yapılan hata. Düzelirse hangisinin düzelttiğini
bilemezsin, üstelik gereksiz değişiklik kendi arızasını getirir.

Doğrulanmış vaka: bir iş ilanı aramasında konum filtresi **sessizce**
uygulanmadı, sorgu Hollanda istenmesine rağmen Türkiye sonuçları döndürdü.
Düzeltirken iki şey birden değiştirildi: konum parametresi doğru biçime
çevrildi **ve** tarih penceresi 7 günden 30 güne açıldı. Konum düzeldi,
ama pencere gereksiz yere genişlemişti ve sonuçlara bir aylık, çoğu kapanmış
ilanlar karıştı. Kullanıcı yakaladı: *\"bir de neden geçen ay yayınlanmış
ilanları aradın\"*.

Yalnız konum düzeltilseydi sonuç hem doğru hem taze olacaktı. Nitekim
pencere 7 güne geri çekilince sonuç sayısı düşmedi, yani genişletme hiçbir
şey kazandırmamış, sadece kalite düşürmüştü.

> **Kural: bir parametre yanlış çalışıyorsa yalnız onu düzelt. İkinci
> parametreye dokunmak için ayrı bir gerekçen olmalı, \"madem elim değdi\"
> gerekçe değildir.**

### Sessiz filtre arızası ayrı bir sınıftır

Asıl tuzak, filtrenin hata vermemesiydi. Sorgu 200 döndü, liste doldu,
her şey çalışıyor göründü. Yalnızca *yanlış* veriydi.

Bir filtre uyguladıktan sonra **filtrenin gerçekten uygulandığını çıktıdan
doğrula**, dönüş kodundan değil: sonuçların bir alanını okuyup beklenen
değerle karşılaştır. Bu vakada tek bakış yeterliydi, listede Türkiye
şehirleri duruyordu. Boş sonuç kadar dolu-ama-yanlış sonuç da arızadır ve
ikincisi çok daha uzun yaşar.

## Pitfalls

- **Aynı çıktıyı döndürerek denetimi sınayamazsın.** Metin, denetçinin
  bildiği şekle yakınsar ve kalan açıklar görünmez olur. Sıfırdan üretilen
  bir örnek, denetçi için de bir mutasyon testidir.
- **Filtre boş/aşırı sonuç döndürdüğünde önce GİRDİYİ doğrula.** Bir
  izolasyon filtresi "sahibi bile kendi kaydını görmüyor" dedi; suç
  filtrede değildi, beslediği katalog dosyası bayattı ve kayıtların yarısı
  içinde yoktu.
- **Sözdizimi kontrolü "çalışıyor" demek değildir.** Kaçış karakteri bozulup
  koda ham `\n` gömülebilir; `ast.parse` buna "OK" der. Üretilen çıktıyı
  gözle.
- **Kaydı olayın kendisine bağla, ayrı adıma değil.** "Gönder, sonra
  kaydet" iki adımdır ve ikincisi atlanır. Kayıt gönderim fonksiyonunun
  içinde olursa hiçbir yol onu atlayamaz.
- **Hata kabul etmek işi bırakma gerekçesi değildir.** "Haklısın, yarın
  düzeltirim" = iş yapılmadı. Kabul et, sonra aynı turda düzeltmeye başla.
  Ertelemeyi sadece kullanıcı önerirse uygula.

## Destek dosyaları

- `references/referansa-karsi-puanlama.md` — bir çıktıyı bilinen doğru
  referansa karşı puanlayıp tur tur yakınsatma ("gauntlet loop"): yapısal
  parmak izi çıkarma, tavanlı ceza tasarımı, durma koşulu ve tavan puandan
  sonra modalite değiştirme zorunluluğu.
- `references/eksen-arama-olcum-sablonlari.md` — "TEMİZ dedi ama bozuk"  vakasını çözen somut ölçüm sablonları: mevcut ekseni bulma, arızalı çifti
  aday eksenlerde eleme, yanlış alarm bütçesi taraması, mutasyon testiyle
  düzeltmeyi doğrulama. İki gerçek vaka (altyazı cue yapısı, çift kayıt).
- `references/claude-oturum-madenciligi.md` — Claude Code oturum
  kayıtlarından (`~/.claude/projects/**/*.jsonl`) gerçek problem-çözüm
  çifti çıkarma; aracın kendi telemetrisini eleyen gürültü filtresi.
- `references/notr-marka-kanit-demosu.md` — müşteri/kurum işini ifşa etmeden
  aracın çalıştığını kanıtlama: gerçek üretim motorunu uydurma bir markayla
  koşturma, referans parametreleri hedefin çıktısından okuma, kaynağın
  bozulmadığını git ile kanıtlama, ve render sonrası gözle bakma zorunluluğu.
