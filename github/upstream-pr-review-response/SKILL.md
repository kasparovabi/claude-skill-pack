---
name: upstream-pr-review-response
description: "Use when a bot review lands on your upstream PR. Verify, then answer with evidence."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [GitHub, Pull-Requests, Code-Review, Open-Source, CI, Upstream]
    related_skills: [github-pr-workflow, github-code-review, github-auth]
---

# Upstream PR takibi ve review cevabı

Sahibi olmadığın repolara açtığın PR'lar için. Kampanya tipi katkıda (aynı
düzeltmeyi 5-10 repoya birden açmak) bu iş sürekli tekrarlar: PR'lar açık kalır,
AI reviewer'lar (cubic, CodeRabbit, Greptile, CodeAnt) bulgu yazar, CI kırmızı
yanar ve birinin bunları ayıklaması gerekir.

`github-pr-workflow` PR **açmayı** anlatır. Bu skill PR açıldıktan **sonrasını**
anlatır: durum taraması, bulgu ayıklama, takip commit'i.

## Ne zaman kullan

- "PR'ların durumuna bak", "son commitlerin ne durumda", "repoları kontrol et"
- Bir bot review'u bulgu yazmış, hangisi gerçek karar verilecek
- CI kırmızı ve senin diff'inle ilgili olup olmadığı belirsiz
- Aynı düzeltmeyi birden çok upstream repoya açtın, hepsini topluca izliyorsun

## Adım -1 — Katkı verilecek mi? Bu kararı CV mantığıyla verme

PR açmadan önceki karar. Yabancı bir repo katkı adayı olarak geldiğinde
*"bu CV'de iyi görünür mü"* diye tartmak yanlış filtredir. Kullanıcının
düzeltmesi net (11 Ağu 2026):

> *"Mesele sadece cv değil ya. Eforu direkt ben harcamadığım ve işi sen
> arkaplanda yaptığın için boşa vakit harcamış olmayız. Ve bir repoda adam akıllı
> görünmüş oluruz ki kişinin linkedin profiline bakmadım ama entrepenuar diyor
> belki sever ve iş bağlarız belli mi olur. Sadece issue değil direkt pr yapalım."*

Üç düzeltme:

- **Efor hesabı senin değil.** İşi arka planda ajan yapıyorsa "düşük getirili,
  geçelim" kararı yanlış bütçeye karşı verilmiş olur. Düşük yıldız sayısı ve
  küçük depo, göründüğünden çok daha az engeldir.
- **Portfolyo değeri tek değer değil.** İyi bir yama profesyonel bir temas
  demektir ve bakımcı tanışmaya değer biri olabilir. Bu getiri CV satırı
  hesabında hiç görünmez.
- **Issue yerine PR.** Teşhisi yazıp düzeltmeyi bakımcıya bırakmak aynı işin
  küçük hâlidir. Tarif edecek kadar sağlam bir teşhisin varsa yamayacak kadar da
  sağlamdır.

Gerçek gerekçelerle reddet: lisans yok, katkı kuralları düşmanca, depo terk
edilmiş, ya da düzeltme hiçbir şekilde doğrulanamıyor.

### Depoyu bulamadan hüküm verme

Kısaltılmış bağlantı (`lnkd.in/...`) `curl -L` ile çözülmeyebilir ve kullanıcı
adı tahmini boşa çıkar. Tarayıcı sekmesinde açıp gerçek URL'i oku. Bu oturumda
`gh api /users/<tahmin>` üç kez 404/boş döndü; doğru depo yalnızca tarayıcıdan
çıktı ve tahminlere dayalı ilk değerlendirme yanlıştı.

### İddia etmeden önce derle ve koştur, doğrulayamadığını da YAZ

Açmadan önce gerçek sayılar üret, "çalışması lazım" deme. Sonra PR gövdesinde
sınırı açıkça belirt. Bedeli yok, güvenilir yamayı makul yamadan ayıran şey bu:

> Build succeeds and the full suite passes: 135 tests, 0 failures.
>
> I could not validate on-device that the hide now lands every time, since that
> depends on the real menu bar and Accessibility permissions on your machine.
> If it still misses under load, `dropSettleDelay` is the one to raise first.

### Yorum yasağı SENİN yazdığın satırlar için, bakımcının dosyası için değil

"Kod yorumu yazma" tercihi yazdığın koda uygulanır. Bakımcının dosyasını yeniden
biçimlendirme yetkisi vermez; onun doküman yorumlarını silmek dar bir düzeltmeyi
gürültülü bir diff'e çevirir ve reddi davet eder.

Temizlemeden önce diff'in gerçekte ne eklediğine bak:

```bash
git diff HEAD~1 -- path/to/file | grep "^+" | grep -c "//"
```

Bu oturumda eklenen 26 satırın 16'sı benim yorumumdu. Yalnız onları çıkarmak
değişikliği 26 satırdan 10'a indirdi (dört sabit, dört çağrı) ve bakımcının
kendi yorumları yerinde kaldı. Sonra derleme ve testleri **yeniden koştur**:
bir bloğu kapatan satırı silmek bu işin tek ısıran yanıdır ve gürültülü patlar.

## Adım 0 — Bağlamı doğru oku

**Tuzak:** Kullanıcı "son commitlerin durumuna bak" dediğinde bu yerel git
deposu değil, **açık upstream PR'lar** olabilir. Kanal/konu bağlamı belirleyici:
GitHub PR raporlarına ayrılmış bir Telegram konusunda sorulan "commit durumu"
sorusu PR'ları kastediyordur ve kullanıcı senin bunu bildiğini varsayar.

Şüphedeysen önce ucuz olanı koştur, tek komut:

```bash
gh search prs --author=@me --limit 20 \
  --json number,title,state,repository,url,updatedAt
```

Yerel depo durumu ayrı bir sorudur; ikisini karıştırma. Yanlış tarafa uzun bir
rapor yazmak kullanıcının vaktini yakar.

## Adım 1 — Toplu durum taraması

Her PR için tek çağrıda karar verecek kadar veri çek:

```bash
gh pr view <N> --repo <owner/repo> --json \
  number,title,state,mergeable,mergeStateStatus,reviewDecision,\
comments,reviews,statusCheckRollup,additions,deletions,changedFiles
```

Çok PR varsa döngüye al ve tek satır özet bas. Sınıflandır:

| Sınıf | Belirti | Aksiyon |
|---|---|---|
| Merge oldu | `state=MERGED` | iş bitti, sadece raporla |
| Temiz bekliyor | `CLEAN`, bulgu yok | aksiyon yok, maintainer bekliyor |
| Bulgu var | review'da issue sayısı | Adım 3'e git |
| CI kırmızı | check `FAILURE` | Adım 2'ye git (önce atfet) |
| İnsan engeli | CLA, imza, hesap onayı | **kullanıcıya devret** |

## Adım 2 — Kırmızı CI senin mi? (düzeltmeden ÖNCE atfet)

Bu adımı atlamak en pahalı hatadır. Sahibi olmadığın bir repoda kırmızı check
çoğu zaman **önceden kırık** olan bir şeydir ve senin diff'inle ilgisi yoktur.
Onu "düzeltmek" PR'ı incelenemez hale şişirir ve asıl değişikliğini gömer.

Job log'unu çek, hata satırlarını süz:

```bash
gh pr checks <N> --repo <owner/repo>
gh api repos/<owner/repo>/actions/jobs/<JOB_ID>/logs \
  | grep -iE "error|fail|✖|✗|violation" | head -20
```

Kendi diff'inle kesişiyor mu:

```bash
gh pr view <N> --repo <owner/repo> --json files --jq '.files[].path'
```

**Senin olmadığının gerçek işaretleri:**

- Düşen kalemler PR'ının hiç dokunmadığı dosyalar (repo geneli lint/audit 100+
  eski dosyada patlıyor)
- Hata içerik değil altyapı: SARIF yükleme reddi, `Resource not accessible by
  integration`, bot adımında eksik izin/token
- Check yalnız PR'larda koşuyor; `main` yeşil çünkü orada **hiç koşmuyor**.
  Yeşil taban olmaması, hatanın sana ait olduğunun kanıtı **değildir**

Sessizce geçme de. Atfı kanıtıyla kullanıcıya söyle ki maintainer sorduğunda
cevabı hazır olsun. Gerçekten ayırt edemiyorsan tahmin etme, "ayırt edemedim" de.

## Adım 3 — Bot bulgularını ayıkla

Özet satırına değil, **gövdeye** bak. "9 issue found" tek başına eyleme
dönüşmez; `--json reviews` her bulgunun dosyasını, satırını ve ciddiyetini
(P1/P2/P3) verir.

```bash
gh pr view <N> --repo <owner/repo> --json reviews \
  --jq '.reviews[] | select(.author.login=="cubic-dev-ai") | .body'
```

**Her bulguyu koda karşı doğrula.** Botlar bayat satır numarası verir ve bazen
artık o dosyada olmayan bir şeyi işaretler. Değiştirmeden önce grep'le.
Üretemediğin bir bulguyu "düzeltme" — hangi bulguları reddettiğini ve nedenini
açıkça söyle.

### En sık geçerli bulgu: yarım kalmış göç

Sweep tipi PR'larda baskın sınıf budur. Örneği değiştirmişsindir ama aynı
dosyadaki referans listesi, alan açıklaması ya da CLI varsayılanı eski değerde
kalmıştır. Aynı belgede iki çelişen bilgi durur.

Çözüm satır yamamak değil, **eski deseni repo genelinde yeniden taramak**:

```bash
grep -rn -E '<eski-desen-1>|<eski-desen-2>' <PR kapsamindaki dizinler>
```

PR'ın kapsamındaki her geçişi kapat, yoksa bir sonraki reviewer aynı bulguyu
yeniden yazar.

### Değişikliğin gerçekten etkili mi

Fonksiyon imzasındaki varsayılanı güncellemek, CLI arg parser açık bir bayat
varsayılan geçiriyorsa **hiçbir işe yaramaz** — CLI değeri fonksiyon
varsayılanını ezer. İkisinin uyuştuğunu iddia etme, ölç:

```bash
grep -n 'add_argument("-m", "--model"' script.py
grep -n 'model: str = ' script.py
```

### Üretilmiş/aynalanmış dosyayı elle düzenleme

Kaynaktan **yeniden türet**, yoksa kopya tekrar kayar:

```python
wrapper = json.loads(dst.read_text())
wrapper["content"] = src.read_text()      # yeniden turet, elle yazma
dst.write_text(json.dumps(wrapper, ensure_ascii=False))
```

Sonra eşitliği doğrula: `json.loads(dst.read_text())["content"] == src.read_text()`

## Adım 4 — Push öncesi diff hijyeni

Dar bir değişiklik dar görünmeli. 12 satırlık düzeltme 1000 satır olarak
görünüyorsa PR anında reddedilir.

```bash
git diff --stat
for f in $(git diff --name-only); do
  printf '%-60s ' "$f"; grep -qU $'\r' "$f" && echo CRLF || echo LF
done
```

Satır sonlarını yamalama sırasında bozma. Dosyayı Python'la işliyorsan yazmadan
önce kontrol et:

```python
raw = p.read_bytes()
assert b"\r\n" not in raw, f"CRLF! {p}"
```

JSON/YAML dokunduysan hâlâ geçerli mi doğrula (`json.loads`), Python dokunduysan
`python3 -m py_compile`.

## Adım 5 — Takip commit'i

Mesaj, reviewer'ın bulgusunu **açıklasın**: ilk commit neyi kaçırdı, neden
önemliydi. "Fix review comments" hiçbir şey anlatmaz.

```
Fix CLI default and sync generated dashboard copies

Two gaps from the first commit:

1. Only the function signature default was updated. The argparse default
   still pointed at the retired value, and since args.model is always
   passed explicitly, the CLI value overrode it — so the change had no
   practical effect.

2. Components under cli-tool/ were updated but their generated copies
   under dashboard/public/ were not. Copies are now regenerated from
   source rather than hand-edited.
```

Push'tan ~45 sn sonra CI'ın yeniden koştuğunu ve commit sayısı/diff boyutunun
beklendiği gibi olduğunu teyit et.

## Adım 3.5 — Maintainer "şu değerleri doğrula" dediyse ÖLÇ

Sweep PR'larında en sık gelen insan talebi bu: "yeni değerlerin geçerli olduğunu
doğrula." Cevap yazmadan önce gerçekten ölç; "doğrudur herhalde" demek talebi
kapatmaz ve maintainer ikinci kez sorar.

**Canlı API > doküman sayfası.** Doküman sayfalarını grep'lemek güvenilmez;
içerik istemci tarafında gelebiliyor ya da bot filtresine takılıyor ve **boş**
dönüyor. Boş çıktıyı "değer bulunamadı" diye okuma, kaynağı değiştir. Model
kimlikleri için doğru kaynak `GET /v1/models`.

Ölçüm elde varsa cevaba ham listeyi koy, kullanılan değerleri işaretle,
kaldırılanların artık listede olmadığını göster. Üstüne maintainer'ın asıl
derdine ("bir daha çürümesin") cevap ver: sürümsüz takma ad kullanmak, tarihli
anlık görüntüye göre bu çürümeyi tekrarlatmaz.

Ölçemediysen **iddia etme**. "Teyit edemedim, sebebi şu" demek, doğrulanmamış bir
onayı maintainer'a sunmaktan iyidir.

Yöntem, kimlik doğrulama tuzağı (`ANTHROPIC_AUTH_TOKEN` + `Authorization: Bearer`)
ve gerçek cevap metni: `references/kimlik-dogrulama-ve-cla-arizasi.md`

### Maintainer "bir daha çürümesin" diyorsa ölçüm YETMEZ, kontrol gönder

Talep iki katmanlı gelir: (a) bu değerler doğru mu, (b) bir daha eskimeyeceğinden
nasıl emin olacağız. Sadece (a)'yı cevaplarsan PR ikinci turda yine takılır.

(b)'nin cevabı takip commit'idir: değeri tarayıp canlı kaynağa soran, eskimiş
olanı bulunca **sıfırdan farklı kodla çıkan** küçük bir betik. Sıfırdan farklı
çıkış kritik, çünkü betiği zamanlanmış bir CI işine bağlanabilir yapan tek şey o.

Kanıtlanmış şekil (`scripts/check_model_ids.py`, unifi-mcp-server #111):

- repoyu tarar, kullanılan kimlikleri **dosya yollarıyla** listeler
- her birini canlı API'ye sorar
- `0` hepsi geçerli / `1` en az biri emekli / `2` kaynağa ulaşılamadı
- `--offline` bayrağı: kimlik bilgisi olmadan sadece ne kullanıldığını basar
- ürün adlarını eler (`claude-code-action`, `claude-desktop` model kimliği değil)

**Betiği göndermeden önce mutasyon testiyle kanıtla.** Emekli bir değeri repoya
geri koy, betiğin `1` ile çıkıp dosyayı adıyla gösterdiğini gör, geri al, `0`'a
döndüğünü doğrula. Yorumda bu testi de anlat — "yazdım" ile "yakaladığını
gördüm" arasındaki farkı maintainer okur.

İki ortam değişkenini birden destekle: `ANTHROPIC_API_KEY` yoksa
`ANTHROPIC_AUTH_TOKEN`'a düş. İkincisi OAuth token'ıdır ve `x-api-key` başlığıyla
**401 verir**, `Authorization: Bearer` ister. Bunu bilmezsen kendi doğrulama
betiğin çalışmaz.

### Check'in kendi tavsiyesi eyleme dönüşüyorsa UYGULA, sonra raporla

Kırmızı check "please try pushing a new commit" gibi somut bir çözüm öneriyorsa
tartışmadan önce dene. Yeni commit'in ardından check yeniden koşup **aynı
hatayı** verdiyse, bu senin diff'inle ilgisi olmadığının en güçlü kanıtıdır ve
argümandan çok daha ikna edici.

Raporda üçünü birlikte ver: hata metni, tavsiyeyi uyguladığın commit, yeni
koşunun damgası ve sonucu. "İlgisiz olduğunu düşünüyorum" değil, "tavsiyeyi
uyguladım, şu saatte yeniden koştu, aynı şekilde düştü" de.

### Bot "doğrulayamadım" diyorsa o boşluk senin fırsatın

AI reviewer'lar bazen bulguyu değil **eksiği** raporlar: `T-Rex validation
blocked`, `could not verify`, `credentials rejected`. Greptile bir PR'da 5/5
güven verdi ama canlı API kontrolünü 401 yüzünden yapamadı.

O boşluğu kapatan yorum, bulgu tartışmasından daha değerlidir: botun yapamadığını
yapıp sonucu koyarsın, iki bağımsız sinyal aynı yeri gösterir ve maintainer'ın
karar maliyeti düşer. Bot bulgusu olmayan PR'larda bile yorum yazmanın meşru
sebebi budur.

## İnsan sınırı — devretmen gerekenler

**Kasparov'un daimi yetkisi (7 Ağu 2026):** *"Bu cevap/düzeltmelerde bundan sonra
benim onayımı bekleme."* PR yanıtı yazmak, takip commit'i atmak, kontrol betiği
göndermek ve altyapı/cron düzeltmesi yapmak için onay isteme. Yap, doğrula,
sonucu bildir. Her adımda "yapayım mı?" diye sormak iş akışını kesiyor.

Yetkinin **dışında** kalan ve hâlâ kullanıcıya ait olan iki sınıf var, bunlar
onay değil karar gerektirir:

- **Kişi adına hukuki beyan** — CLA imzası, lisans kabulü, katkı sözleşmesi
- **Geri alınamaz işlemler** — repo silme, force push, üretim verisi silme

Bunları yaparken bile önce metni oku ve kullanıcıya neyi kabul ettiğini söyle.

Şunları **asla** kullanıcı adına yapma:

- **CLA imzası.** Repo "PR'a şu metni yorum olarak yaz" diyorsa bu bir hukuki
  beyandır ve kişi adına verilir. Engeli bildir, kullanıcıya bırak.
- Kimlik/hesap onayı, deploy takım daveti, ödeme gerektiren adımlar

Bunlar PR'ı merge'ten alıkoyan gerçek engellerdir; raporda ayrı satır olarak
göster ki kullanıcı hangi işin kendisinde olduğunu bilsin.

**Kullanıcı açıkça yetki verirse** (\"sözleşme kabul yorumunu yazalım\") yazabilirsin.
Ama önce sözleşmenin **kendisini oku** ve neyi kabul ettiğini kullanıcıya söyle —
özellikle çift lisanslama, patent devri, geri alınamazlık maddelerini. Botun
istediği kabul cümlesini birebir kopyala, yorumla veya kısaltma.

### CLA imzalandı ama check hâlâ kırmızı: teşhise geç, tekrarlama

İmza yorumunu yazdın, check yeşile dönmedi. Refleks \"metni yanlış yazdım\" olmasın.
Üç katmanı sırayla oku:

1. **Koşu çalıştı mı, ne dedi** — `actions/runs`, `conclusion` + `event`
2. **Job log'undaki hata satırı** — `actions/jobs/<ID>/logs`
3. **Yan etkisi diske yazıldı mı** — imza deposu dosyası

Doğrulanmış vaka: imzayı işleyen koşu `success` verdi, ama imza deposu
(`.github/cla-signatures.json`, `cla-signatures` dalı) `{\"signedContributors\": []}`
idi ve dalın son commit'i aylar öncesine aitti. Bot imzayı işliyor ama **dala
yazamıyor**; liste boş kaldığı için her kontrol katkıcıyı imzasız sayıyor. Bu bir
yazma izni arızası, imza metni sorunu değil ve **çözümü depo sahibinde**.

Yanlış hipotezi de ele: commit'in author ve committer kimliği farklıysa ikincisinin
de imzalaması gerekir, o zaman arıza sende olur. Kontrol et ve raporda göster.

`recheck` botu yeniden tetikler ama depo yazılamıyorsa sonucu değiştirmez. İki
denemeden fazla tekrarlama. Maintainer'a kanıtları (koşu damgaları, boş depo
çıktısı, dal tarihi, commit kimliği) ver ve iki somut seçenek sun: imzayı tekrar
yorumlamak, ya da DCO'ya geçip `git commit -s` ile imzalı commit atmak.

Ayrıntılı teşhis komutları: `references/kimlik-dogrulama-ve-cla-arizasi.md`

## Tuzaklar

- **Yerel depoya bakıp PR sanmak.** Bağlamı okumadan uzun bir yerel git raporu
  yazmak; kullanıcı upstream PR'ları soruyordu.
- **Özet sayısına bakıp gövdeyi okumamak.** "2 issue" ile "9 issue" arasındaki
  fark, hangi dosyada ne olduğu okunmadan yönetilemez.
- **Bot bulgusunu doğrulamadan uygulamak.** Bayat satır numarası yüzünden var
  olmayan bir şeyi "düzeltirsin".
- **Kırmızı CI'ı otomatik üstlenmek.** Repo geneli audit'ler önceden kırıktır;
  düzeltmeye kalkışmak PR'ı boğar.
- **Bulgunun gösterdiği satırı yamalamak.** Kök neden genelde yarım kalmış göç;
  desenin tamamını tara.
- **Üretilmiş dosyayı elle düzeltmek.** Kaynaktan türet.
- **CRLF şişmesini fark etmemek.** Push'tan önce `git diff --stat` bak.
- **Fonksiyon varsayılanını güncelleyip CLI varsayılanını unutmak.** Değişiklik
  sessizce etkisiz kalır.
- **Kampanyada bir PR'ın değerlerini diğerine taşımak.** Aynı düzeltme 5-10
  repoya açıldığında diff'ler BENZER ama AYNI DEĞİL. Bir repoda kaldırılan
  kimlik `claude-3-5-sonnet-20241022` iken diğerinde
  `claude-sonnet-4-20250514` çıktı; ilk yazılan yorum yanlış değeri
  taşıyordu. Yorumu göndermeden önce **o PR'ın kendi diff'ini** oku:
  `gh pr diff <N> --repo <owner/repo> | grep -E '^[+-].*<desen>'`.
  Maintainer'a onun repoda hiç görmediği bir değeri göstermek, cevabın
  tamamının güvenilirliğini yakar.

## Kullanıcıya sunum

Kasparov için: markdown başlık yok, numaralı liste yok, doğal paragraf. Önce
sınıflandırılmış durum (merge olan / temiz bekleyen / bulgu var / engelli),
sonra hangi bulgunun gerçek olduğu ve neden, sonunda kullanıcıda kalan tek iş.
Reddettiğin bulguları da söyle — sessizce atlamak güveni yer. Teknik rapor
(diff, commit hash, dosya yolu) istenmedikçe uzatma.

## Destek dosyaları

- `references/model-id-migration-campaign.md` — bu kalıpların çıktığı gerçek
  vaka: 7 repoya açılan emekli-model-kimliği PR'ları, cubic'in 11 bulgusu,
  hangileri gerçekti, iki repoda uygulanan onarım
- `references/kimlik-dogrulama-ve-cla-arizasi.md` — maintainer'ın "değerleri
  doğrula" talebini canlı API ölçümüyle kapatmak; CLA imzalandığı hâlde check'in
  kırmızı kalması (imza deposu yazılamıyor) ve üç katmanlı teşhis zinciri
- `references/cururme-kontrolu-ve-cla-kok-neden.md` — "bir daha çürümesin"
  talebine kontrol betiğiyle cevap (mutasyon testi dahil); check'in kendi
  tavsiyesini uygulayıp atfetme; CLA arızasının kesin kök nedeni (imza
  dosyasının commit geçmişi tek insan commit'i) ve elenen hipotezler
- `scripts/check_model_ids.py` — repodaki model kimliklerini canlı API'ye karşı
  doğrulayan, emekli kimlik bulunca 1 ile çıkan kontrol betiği. Takip commit'i
  olarak upstream'e gönderilebilir; göndermeden önce mutasyon testiyle sına.
