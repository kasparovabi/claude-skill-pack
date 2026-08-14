# Türkiye mevzuatını terminalden çekmek (mevzuat.gov.tr)

Türkçe hukuki bir soruya cevap verirken (harcırah, iş kazası, meslek kanunu,
vakıf mevzuatı) kanun metnini **birincil kaynaktan** okumak şart. İkincil
yorum siteleri (hukuk blogları, muhasebe forumları) sık sık mülga maddeyi
yürürlükteymiş gibi aktarıyor.

## Çalışan yol: doğrudan PDF endpoint'i

HTML arayüzü JS ile render oluyor ve `body { display: none }` ile geliyor —
tag striptorsan sadece Google Analytics kodu çıkar. **HTML'i hiç deneme.**

```bash
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"
curl -sL --max-time 40 -c ck.txt -b ck.txt \
  "https://www.mevzuat.gov.tr/MevzuatMetin/1.5.3568.pdf" \
  -A "$UA" -H "Accept-Language: tr-TR,tr;q=0.9" -o kanun.pdf
file kanun.pdf          # "PDF document, N pages" gormelisin
pdftotext kanun.pdf - > kanun.txt
```

Cookie kavanozu (`-c/-b`) şart, yoksa yönlendirme döngüsüne girebiliyor.

### URL şeması

`https://www.mevzuat.gov.tr/MevzuatMetin/<TERTIP>.<TUR>.<NO>.pdf`

| Örnek | Kanun |
|---|---|
| `1.5.3568.pdf` | SMMM ve YMM Kanunu |
| `1.5.5510.pdf` | Sosyal Sigortalar ve GSS Kanunu (248 sayfa) |
| `1.5.4857.pdf` | İş Kanunu |
| `1.5.6721.pdf` | a client organisation Kanunu |
| `1.3.6245.pdf` | Harcırah Kanunu (tertip 3'e dikkat) |

Tertip numarası her zaman `1.5` değil; eski kanunlarda `1.3` olabiliyor.
Yanlış tertiple 404 yerine HTML dönebilir, o yüzden `file` ile doğrula.

## Okuma: `grep -n -A/-B` ile madde avla

`pdftotext` çıktısı satır numaralı olduğu için ilgili maddeyi bağlamıyla al:

```bash
grep -n -A 25 'İş kazasının tanımı' sgk.txt | head -40
grep -n -B2 -A 12 'Harcırahın unsurları\|Yevmiye' harcirah.txt | head -55
sed -n '30,82p' harcirah.txt      # tanımlar bölümü genelde başlarda
```

Kanunlarda tanımlar maddesi (genelde Madde 3-4) belirleyicidir; asıl hüküm
oradaki tanıma dayanır. Hükmü okuyup tanımı atlarsan yanlış sonuca varırsın.

## Doğrulanmış bulgular (6 Ağu 2026 oturumu)

Bunlar tekrar araştırılmasın diye:

- **5510/13** iş kazasını sayarken iki bendi kritik: görevli olarak işyeri
  dışına gönderilen sigortalının *asıl işini yapmaksızın geçen zamanları*, ve
  *işverence sağlanan taşıtla gidiş gelişi*. Yani görev yolculuğu iş kazası
  kapsamında.
- **6245/39** yemek gideri değil **gündelik** düzenliyor: memuriyet mahalli
  *içinde* göreve gündelik verilmez; *dışına* çıkıp öğle veya akşam yemeği
  saatlerinden birini geçirene 1/3, ikisini geçirene 2/3, geceyi de geçirene
  tam gündelik.
- **6245/3-g** "memuriyet mahalli" tanımı: büyükşehirlerde il mülki sınırı
  içinde kalan ilçe belediye sınırları, **artı kurumun sağladığı taşıtla
  gidilip gelinebilen yerler**. Araç tahsisi yeri mahalli *içine* sokabiliyor.
- **3568/8A** SMMM, düzenlediği iade raporu yanlışsa ziyaa uğratılan vergi ve
  cezalardan mükellefle **müşterek ve müteselsil sorumlu**. Bu, muhasebecinin
  neden belirsizlikte "hayır" dediğini açıklıyor.
- **6721/4** TMV harcırah ve yolluklarını **Mütevelli Heyeti belirler**, yani
  vakıf 6245'e doğrudan tabi değil, kıyasen uyguluyor. Bağlayıcı metin
  Mütevelli Heyeti kararıdır.
- **6721/5** brüt gelirin **en fazla 1/3'ü** yönetim/idame giderine, 2/3'ü
  amaca. Kurumlar vergisi muafiyeti var ama *iktisadi işletmeler ve iştirakler
  hariç*.

## Tuzak: sorumluluk rejimi ile ödeme yükümlülüğü ayrı kanunlarda

En sık yapılan hata bu. "Kişi o esnada kurumun sorumluluğunda" (5510) ile
"o harcamayı kurum öder" (6245 / iç yönerge) **birbirinden çıkmaz**. Biri
sigorta, öbürü mali hak. Kullanıcı ikisini birleştirip argüman kuruyorsa
ayrımı nazikçe göster, ama hangi tarafta haklı olduğunu da söyle.

## Kapsam uyarısı

Kanun metni **asgari zemini** verir. Vakıf, belediye, üniversite gibi kendi
mevzuatı olan kurumlarda bağlayıcı olan iç yönergedir ve kanundan daha cömert
olabilir. Somut bir vakayı savunacaksan iç yönergeyi görmeden kesin konuşma —
"kanun şunu diyor, kurumun kendi kararı farklı olabilir" de.
