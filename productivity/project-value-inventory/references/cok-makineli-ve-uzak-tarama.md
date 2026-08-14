# Çok makineli ve uzak tarama: yerel disk yetmez

Doğrulandığı oturum: 2026-08-05 (LinkedIn projeler bölümünü doldurmak için aday
çıkarma). Kullanıcının iki makinesi vardı ve hangisinde ne olduğu bilinmiyordu.

## Neden gerekli

`scripts/scan_projects.py` yalnızca çalıştığı makinenin disklerine bakar. Kullanıcı
birden fazla makine kullanıyorsa (ev/iş, mac/windows) tek makineyi tarayıp
"envanter çıkardım" demek yanıltıcıdır. Ayrıca bazı işler yalnızca uzak sunucuda
veya yalnızca GitHub'da durur, hiçbir diskte kopyası yoktur.

## Makineleri keşfet

Tailscale kullanılıyorsa ağdaki tüm cihazlar tek komutta görünür ve hangisinin ayakta
olduğu da yazar:

```bash
tailscale status
```

Çıktı `IP  cihaz-adı  hesap  os  durum` biçiminde. `offline, last seen 163d ago`
diyen makineye bağlanmaya çalışıp zaman harcama.

Kullanıcı adını **tahmin etme**. Geçmiş oturum kayıtlarından çıkar:

```bash
grep -rhoE '(ssh )?[a-z]+@[0-9.]+' ~/.claude/projects 2>/dev/null \
  | sort | uniq -c | sort -rn | head
```

En çok geçen kombinasyon doğru olandır.

---

# ⚠ EN KRİTİK DERS: `.git` aramak eksik envanter üretir

Bu bölüm, aynı oturumda **önce yanlış yapılıp sonra kullanıcı tarafından
düzeltilen** bir hatadan yazıldı. Aynı hataya düşme.

## Ne oldu

Windows makinesi şu yöntemle tarandı: `Get-ChildItem -Filter '.git' -Recurse
-Depth 4`, yalnızca `$env:USERPROFILE` + `C:\` + `D:\Users` köklerinden.

Sonuç: 24 git deposu bulundu, hepsi üçüncü parti klondu. Kullanıcıya
**"Windows'ta kendi işin yok, hepsi klon"** diye raporlandı.

Kullanıcının cevabı: *"Bir kere windows tarafı dediğin gibi değil, onlarca proje
var çalışan çalışmayan, yanlış şeylere bakmışsın, o kısımlara tekrar bak."*

Doğru tarama yapılınca aynı makinede **25 gerçek proje** çıktı. En büyüğü 3668 kod
dosyalı bir video render sistemi, bir diğeri 1546 dosyalık mobil uygulama. Hiçbiri
git altında değildi, o yüzden ilk tarama hiçbirini görmedi.

## Kök sebep

Gerçek projelerin çoğu versiyon kontrolü altında değil: tek seferlik otomasyon
işçileri, render hatları, script kovaları, denemeler, GPU işleri. `.git` aramak
bunların hepsini görünmez kılar.

Ayrıca projeler ev dizininde değil, **sürücü kökünde** duruyordu (`C:\pozla_worker`,
`C:\sceneshift`, `C:\sentinel`, `C:\upscale`, `C:\mockup`). Yalnızca
`$env:USERPROFILE` taramak bunları tamamen kaçırır.

## Doğru yöntem: işaret dosyası taraması

Bir klasörde şunlardan **herhangi biri** varsa o klasör projedir:

```
package.json  requirements.txt  pyproject.toml  main.py  app.py  index.js
server.js  Cargo.toml  go.mod  pom.xml  Dockerfile  docker-compose.yml
README.md  .git
```

Git yoksa olgunluk sinyali olarak **kod dosyası sayısı + son değişiklik tarihi**
kullan (`.py .js .ts .tsx .jsx .go .rs .java .cs .swift .rb .php .sh .ps1`).
Git'i olmayan 3000 dosyalık bir sistem, 5 commit'lik denemeden ciddi bir iştir.

## Sıra: önce kökleri GÖR, sonra derine in

Kör derin tarama hem yavaş hem yanıltıcı. Üç adım:

```powershell
# 1) Her sürücünün kökü — projeler sık sık burada
foreach($d in @('C:\','D:\')){
  Write-Output ('===== ' + $d)
  Get-ChildItem $d -Directory -Force -EA SilentlyContinue | Select-Object -Expand Name
}
# 2) Kullanıcı profilinin birinci seviyesi (gizliler dahil)
Get-ChildItem $env:USERPROFILE -Directory -Force -EA SilentlyContinue | Select-Object -Expand Name
```

Bu iki listeyi GÖRDÜKTEN sonra ilginç görünen kökleri hedefli tara. Sürücü kökünde
`pozla_worker`, `sceneshift`, `upscale` gibi isimler duruyorsa bunlar projedir;
`Program Files`, `Windows`, `ESD`, `$Recycle.Bin` sistemdir.

## Hazır script

`scripts/win_project_scan.ps1` — işaret dosyası taraması, kod sayımı, git bilgisi,
README ilk satırı, JSON çıktı. Kökleri düzenleyip kullan:

```bash
scp -o BatchMode=yes /tmp/win_scan.ps1 KULLANICI@IP:win_scan.ps1
ssh -o BatchMode=yes KULLANICI@IP "powershell -NoProfile -ExecutionPolicy Bypass -File win_scan.ps1" \
  2>&1 | grep -v "WARNING\|vulnerable\|upgraded\|openssh.com" > /tmp/win.json
```

`scp` hedefinde `C:/Temp/x.ps1` gibi mutlak yol **exit 1** verebiliyor; çıplak
`KULLANICI@IP:win_scan.ps1` (ev dizinine) sorunsuz gidiyor.

### JSON bozulması: README metni çıktıyı patlatır

`ConvertTo-Json` içine giren README satırlarındaki tırnak, backtick ve kontrol
karakterleri JSON'u geçersiz kılar (`Invalid control character`, `Expecting ','`).
README'yi **kaynakta temizle**, sonra JSON'a koy:

```powershell
$clean = $line.Trim().TrimStart('#').Trim() -replace '[^\w\s\.\,\-\(\)/]', ' '
$o.readme = ($clean -replace '\s+', ' ')
```

## Klon ayıklama

Uzak makinede çıkanın bir kısmı gerçekten üçüncü parti olur. Ayıklama kuralları:

- `remote` adresi başkasının hesabını gösteriyorsa klondur.
- `.claude/plugins`, `vendor_imports`, `marketplaces`, `cookiecutters`,
  `node_modules`, `site-packages`, `venv` altındakiler paket yöneticisinindir.
- `Program Files`, `AppData`, `Windows`, `tools` altı sistem kurulumudur.
- **Ama klon filtresini fazla geniş tutma.** Bir klasör üçüncü parti bir aracın
  *yanında* duruyor diye kullanıcının işi olmadığı anlamına gelmez.

Klon oranı yüksek çıkarsa bu bir "orada iş yok" kanıtı **değildir** — büyük
ihtimalle yanlış ölçütle tarıyorsundur. Önce işaret dosyası taramasını çalıştır.

## Negatif bulguyu nasıl raporlamalı

"Orada senin projen yok" **deme**. Doğru cümle: **"şu kökleri, şu ölçütle taradım,
çıkmadı."** Kullanıcı kendi diskini senden iyi bilir ve yanlış negatifi anında
yakalar. Ölçütü açıkça söylemek, kullanıcının "yanlış yere bakmışsın" diyebilmesini
sağlar; bu düzeltme senin lehinedir.

---

## GitHub: kendi işi ile fork'u ayır

Depo sayısı yanıltıcıdır; fork'lar listeyi şişirir. Doğrulanmış oran: 81 depodan 24'ü
kendi işi, 57'si fork.

```bash
gh repo list KULLANICI --limit 100 \
  --json name,description,pushedAt,visibility,isFork,homepageUrl > /tmp/gh_repos.json
```

Sonra `isFork` false olanları süz ve `pushedAt` ile sırala. Pipe-to-interpreter
taramaya takıldığı için önce dosyaya yaz, sonra ayrı adımda oku.

### Sıralamayı belirleyen alanlar

Depo adı ve commit sayısı bir projenin **dışarıdan görünen** değerini vermez. Şu
metadatayı çek, aday sıralaması buradan çıkar:

```bash
gh api repos/KULLANICI/DEPO \
  --jq '{n:.name,s:.stargazers_count,f:.forks_count,d:.description,t:.topics,pub:(.private|not),lang:.language,url:.homepage}'
```

- `stargazers_count` / `forks_count` > 0 → başkaları bulmuş ve kullanmış.
- `topics` → projenin hangi alana ait olduğunu kullanıcının kendi etiketiyle söyler.
- `pub: false` → recruiter/dış gözlemci içine bakamaz; anlatıda bunu belirtmek gerekir.

### README ilk 40 satırını oku, tahmin etme

Bir projenin gerçekte ne olduğu ve neden değerli olduğu README'nin ilk paragrafında
yazar. Açıklama alanı çoğu zaman yetersiz kalır.

```bash
gh api repos/KULLANICI/DEPO/readme --jq .content | base64 -d | head -40
```

Doğrulanmış vaka: `security-research` deposunun açıklaması yalnızca "Security research
and coordinated disclosures" diyordu. README açılınca içinde CVSS 10.0 seviyesinde,
bir üründe 17 açık bulan ve koordineli açıklama takvimiyle yürütülmüş bir bildirim
tablosu çıktı. Envanterdeki en güçlü tek kalem oydu ve depo adından anlaşılmıyordu.

Aynı şekilde bir başka depo, sahibi tarafından gerekçesi yazılarak emekliye
ayrılmıştı; bu da olgunluk sinyalidir, ölü proje değil.

### Uzak makinedeki repo kullanıcının OLMAYABİLİR

Disk üzerinde çok gelişmiş görünen bir proje (Rust crate'leri, firmware, ADR
belgeleri, mobil arayüz) üst projesi başkasına ait bir klon olabilir. README'deki
issue/repo linkine bak. Kullanıcıya "bu senin mi, katkı mı verdin?" diye **sor**;
envantere "onun projesi" diye koymadan önce netleştir. Yanlış sahiplenme, tek bir
mülakat sorusuyla tüm listenin güvenilirliğini götürür.

## Sıra

1. `tailscale status` → hangi makineler var, hangisi ayakta.
2. Yerel: `scan_projects.py` (kökleri ortama göre düzenle, harici diskleri ekle).
3. Uzak makineler: **önce sürücü kökü + profil listesi**, sonra işaret dosyası
   taraması (`.git` aramakla yetinme), sonra klon ayıklama.
4. GitHub: fork'suz liste + kilit depolar için metadata ve README.
5. Bulguları üç kovaya ayır; negatif bulguyu **kullanılan ölçütle birlikte** raporla.
