---
name: public-release-sanitization
description: "Use before publishing a private workdir publicly."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [security, git, publishing, privacy, open-source]
    category: devops
---

# Özel çalışma dizinini herkese açık yayınlamak

Bir dizini GitHub'a, npm'e, gist'e veya herhangi bir herkese açık yere açmadan
önceki temizlik. Sıradan "kod yazdım, push ettim" işi değil bu: burada
**çalışırken dolmuş** bir dizin var. Skill klasörü, script klasörü, not ağacı,
şablon deposu.

Yükle: "şunu depoya atalım", "bunu yayınlayalım", "public yap", "paylaşılabilir
hale getir", "npm'e koyalım", "gist yapalım" türü istekler geldiğinde. Ayrıca
kendi ürettiğin bir klasörü kullanıcı adına yayınlarken, sormasını beklemeden.

## Neden ayrı bir iş

Risk gömülü token değil. Sır tarayıcıları onu yakalar, GitHub push sırasında
uyarır. Asıl risk **birikmiş bağlam**:

- Müşteri ve kurum adları, iç proje kod adları
- Sohbet kimlikleri, kullanıcı kimlikleri, grup numaraları
- Mutlak ev dizini yolları (`/Users/<ad>/`, `C:\Users\<ad>\`)
- İç hostname'ler, VPN adresleri, özel ağ IP'leri
- Kişisel telefon ve e-posta
- Eski yedek arşivleri (içinde temizlenmemiş sürümler)

Bunların hiçbiri "sır" değil, o yüzden hiçbir otomatik koruma durdurmaz. Ama
hepsi kalıcı olarak yayınlanır ve git geçmişinden temizlemek ikinci, daha kötü
bir iştir.

Ölçülmüş vaka (13 Ağu 2026, 145 dosyalık 23 MB skill klasörü yayınlanacaktı):
ham ağaçta **646 müşteri referansı, 72 sohbet kimliği, 96 mutlak ev dizini
yolu** ve eski yedek arşivleri vardı. Doğrudan push edilseydi hepsi çıkardı.

## Sızıntıdan ÖNCE gelen iki eleme

Sızıntı taraması üçüncü sıradadır. Ondan önce iki soru var ve ikisi de
"gizli veri var mı" sorusundan bağımsız.

### Eleme A — bu dosya SENİN mi

14 Ağu 2026 vakası: kullanıcı "kendi ürettiğim skiller olsun" dedi, ben
klasördeki her şeyi yayınladım. 115 dosyanın **81'i başkasının işiydi**:
ajanla kurulu gelen skiller ve satıcı dokümantasyonunun kopyaları
(Cloudflare, Wrangler, Workers, SDK belgeleri). Kullanıcının tepkisi:
*"ben bu repoda kendi ürettiğim skilleri barındırayım istiyordum ama sen
var olan tüm skilleri yükledin oraya"*.

İki zarar birden: yayınlama hakkın olmayan içerik çıkıyor, ve kendi işin
o yığının içinde görünmez oluyor.

Sahiplik testi, mekanik yapılabilir:

```python
# upstream = kurulum + eklenti agaclarindaki tum dosya adlari
upstream = {p.parent.name for p in Path(KURULUM).rglob("SKILL.md")}
upstream |= {p.parent.name for p in Path(EKLENTILER).rglob("SKILL.md")}
# ayni ad upstream'de varsa -> kurulu gelmis, senin degil
```

İkinci süzgeç elle: bir dosya bir **ürünün belgesini** taşıyorsa
(satıcı API'si, framework rehberi) o senin öğrendiğin şey değil, kopya.

Sonuç: 115 → 34.

### Eleme B — bu dosya HERKESE mi ait

Sızıntısı olmayan ama yine de yayınlanmaması gereken dosyalar var:
başkası yüklediğinde ona **senin gibi davranmasını** söyleyenler.

Kullanıcının ifadesi: *"yazı stili skillim bana ait ve bana özel bir
skill, bu herkese uygun olmaz"*.

Aynı taramada dördü çıktı ve deseni ortaktı:

| Dosya | Neden kişiye özel |
|---|---|
| yazım tarzı profili | kullanıcının ölçülmüş üslubunu dayatıyor |
| zamanlanmış iş güvenilirliği | kendi cron kurulumunu varsayıyor |
| model iskelesi | kendi model tercihlerine ayarlı |
| tetikleyici eşlemesi | kendi tetikleyici kelimelerine bağlı |

Tarama deseni: `yazım protokol|writing voice|median message|üslup|
kendi cron|benim kurulum|bu makinede` artı kullanıcının kendi adı.

Ayrım: **isim geçiyorsa temizle, davranışı dayatıyorsa çıkar.** Aynı
oturumda 14 dosyada sadece isim geçiyordu, temizlenip alındı; 4 tanesi
davranış dayatıyordu, çıkarıldı.

## Dört adım, sırası önemli

### 1. Tara ve say

Hafızadan karar veremezsin. Ne olduğunu ölç:

```
python3 scripts/dizin_sizinti_tara.py <dizin>
```

Çıktı türe göre gruplu gelir: kaç bulgu, kaç dosya, hangi dosyalar. Bu sayı
kararı belirler; 600 bulgu ile 6 bulgu farklı stratejiler ister.

### 2. Konuya özel olanı TAMAMEN dışarıda bırak

Bir dosyanın öğrettiği şey tek bir müşteriye, tek bir iç sisteme bağlıysa
genelleştirilemez. Listeye koy, atla. Örnek eleme sebepleri:

- Sadece o kurumun iş akışını anlatan dosyalar
- İç panel adresine, özel makineye bağlı yordamlar
- Kullanıcının kişisel iş arama, sağlık, finans dosyaları

### 3. Sadece TESADÜFİ geçenleri genelleştir

Öğrettiği şey genel ama örneğinde müşteri adı geçiyorsa değiştir:

| Bulunan | Yerine |
|---|---|
| `AcmeCorp`, `Acme Vakfı` | `the client`, `a client organisation` |
| `~/` | `~/` |
| `+90 5xx ...` | kaldır |
| `-100123...` (sohbet kimliği) | kaldır |

**Test: değişimden sonra cümle hâlâ anlamlı olmalı.** "the client'in the
client platformunda" gibi bir şey çıkıyorsa dönüşüm yanlış, dosyayı at.

### 4. Kopyada yeniden doğrula, kaynakta değil

Genelleştirme kaçırır. Değiştirdikten sonra çıkış kopyasını baştan tara.
Ölçülmüş oranlar: 19 dosyadan **9'u temizlendi ve alındı, 10'u hâlâ kirli
çıktı ve atıldı**. Yani doğrulama adımı olmasaydı 10 sızıntı yayınlanacaktı.

## Yayın sonrası: CANLI adresten teyit

Temiz çalışma kopyası, push edilenin temiz olduğunu **kanıtlamaz**. Yanlış
branch, eksik `git add`, `.gitignore` sürprizi araya girebilir. Yayınlanan
dosyaları geri çek:

```bash
for f in README.md tools/script.py docs/notes.md; do
  echo -n "$f: "
  curl -s "https://raw.githubusercontent.com/OWNER/REPO/main/$f" \
    | grep -ciE "musterikadi|/Users/|ic-hostname" || echo "0 (temiz)"
done
```

## Yayınlandıktan SONRA sızıntı fark edersen

Dosyayı silip yeni commit atmak yetmez, eski commit içerikte durur.
`git rebase` ya da `--force` ile geçmişi yeniden yazmak da **yetmez**:
GitHub kopan commit'leri hemen toplamaz, doğrudan SHA ile istenirse
verir.

14 Ağu 2026'da ölçüldü. Force push sonrası depo tek commit gösteriyordu
ama eski üç SHA hâlâ `200` dönüyordu:

```bash
for sha in <eski1> <eski2> <eski3>; do
  curl -s -o /dev/null -w "$sha: %{http_code}\n" \
    "https://api.github.com/repos/OWNER/REPO/commits/$sha"
done
# force push sonrasi:  200 200 200   <- hala okunabilir
# depo silinip yeniden kurulduktan sonra:  422 422 422
```

Kesin çözüm depoyu **silip yeniden oluşturmak**:

```bash
gh repo delete OWNER/REPO --yes
# temiz kopyada gecmisi sifirla
rm -rf .git && git init -q && git add -A && git commit -q -m "..."
gh repo create REPO --public --description "..."
git remote add origin "https://$(gh auth token)@github.com/OWNER/REPO.git"
git push -q -u origin main
git remote set-url origin https://github.com/OWNER/REPO.git   # token'i URL'de birakma
```

Yeni depoda çatal veya yıldız yoksa maliyet sıfır. Varsa GitHub desteğine
çöp toplama isteği açmak gerekir; o yüzden **ilk push'tan önce temizlemek**
her zaman ucuzdur.

İki pratik not:
- `gh repo create --source=. --push` uzak adı ekler ama sonraki
  `git push --force` ayrı bir onay kapısına takılabilir. Depoyu silip
  yeniden kurmak bu kapıyı da atlar.
- HTTPS push kimlik doğrulaması düşerse uzak adrese `gh auth token`
  gömüp push et, **hemen ardından token'sız hâline geri al**.

## Her zaman dışarıda kalanlar

- **Yedek dizinleri** (`.curator_backups/`, `*-backup/`, `*.bak`). İçlerinde
  eski ve temizlenmemiş sürümler var. Ayrıca `.tar.gz` arşivlerinin içini
  metin tarayıcısı hiç açmaz, yani sessizce sızarlar.
- **Türetilmiş önbellekler** (`index-cache/`, `__pycache__/`, `node_modules/`).
- **İçe aktarılmış kişisel workspace klasörleri.**
- **Oturum kayıtları ve loglar.** Her şey oradadır.

## Altın kural

**Şüpheli olan dışarıda kalır.** Eksik dosya, sızmış veriden iyidir.
"Herhalde temizdir" diye geçme, ölç. Bir dosyayı yayınlamamanın maliyeti
sıfır; yayınladıktan sonra geri almanın maliyeti geri alınamaz.

## Yayınlama

Temizlik bittikten sonra depo açmak sıradan iş:

```bash
cd <temiz-kopya>
git init -q && git add -A && git commit -q -m "..."
gh repo create <ad> --public --source=. --description "..." --push
```

Lisans dosyasını ve `.gitignore`'u temizlik sırasında ekle, sonradan değil.
README'ye **ne çıkarıldığını** bir cümleyle yaz: "müşteri tanımlayıcıları ve
kişisel iletişim bilgileri kaldırıldı, temiz genelleştirilemeyen dosyalar
yarım temizlenmiş hâlde yayınlanmak yerine dışarıda bırakıldı" gibi. Bu hem
dürüst hem de eksikliği açıklıyor.

## Pitfalls

- **Sır tarayıcısı geçti diye temiz sanma.** Token yok demek müşteri adı yok
  demek değil. İki ayrı tarama.
- **İkili dosyaları atla ama unutma.** PNG, PDF, `.tar.gz` metin taramasından
  geçer; içlerinde ekran görüntüsü, iç belge, eski kopya olabilir. Şüphedeysen
  aç ve bak, ya da dışarıda bırak.
- **Küçük harf/büyük harf varyantlarını kaçırma.** `Acme`, `ACME`, `acme`
  ayrı ayrı eşleşir; desenleri `re.I` ile yaz ama yerine koyarken büyük harf
  sürümüne ayrı kural ver, yoksa cümleyi bozarsın.
- **Türkçe ek almış hâlleri unutma.** `Acme'nin`, `Acme'ye`, `Acme'de` ayrı
  desenlerdir; sadece kök eşleşmesi yaparsan ekler ortada kalır.
- **Yedeklerdeki arşivleri açma zahmetine girme, sil.** Taramaya değmez.
- **Yanlış alarmı gerçek sızıntı sanma.** 14 Ağu'da derin tarama 92 bulgu
  verdi, gerçek olan **3**'tü. Gürültü kaynakları: satıcı belgelerindeki
  örnek e-postalar (`inbox@corp.com`), maskelenmiş telefon örnekleri
  (`+141****1212`), `.claude/settings.local.json` gibi dosya yolları,
  `command.local.Command` gibi API adları. Beyaz listeyi eşleşen parçaya
  **ve çevresindeki ~45 karaktere** birden uygula, yoksa her belge dosyası
  alarm üretir. Lisanstaki kendi adın da kasıtlıdır, telif için gerekli.
- **Bulguyu satır numarası ve çevresiyle bas.** Sadece "3 bulgu" demek
  hangisinin gerçek olduğunu göstermez, karar veremezsin.
- **Kaynağı değil YAYINDAKİ hâli tara.** Yerel kopya temiz olabilir ama
  push edilen farklı olabilir. Derin taramayı `git clone --depth 1` ile
  çekilen canlı depo üzerinde çalıştır.

## Destek dosyaları

- `scripts/dizin_sizinti_tara.py` — dizini tarar, bulguları türe göre sayar,
  dosya yollarıyla listeler. Yayın kararından önce çalıştır.
