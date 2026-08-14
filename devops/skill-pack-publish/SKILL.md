---
name: skill-pack-publish
description: "Use when publishing own skills publicly. Scrub leaks first."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [skills, publishing, github, leak-scan, privacy]
    category: devops
    related_skills: [skill-pack-install, hermes-guvenlik-sertlestirme]
---

# Kendi skill kütüphaneni herkese açık yayınlamak

`skill-pack-install` **gelen** yönü anlatır (dışarıdan pack kurmak). Bu skill
**giden** yönü anlatır: kendi `~/.hermes/skills/` klasörünü herkese açık bir
depoya çıkarmak.

Kritik fark: kurulumda risk kod çalıştırmak, yayınlamada risk **veri sızdırmak**.
Skill'ler çalışırken yazıldığı için içlerinde gerçek müşteri adı, gerçek dosya
yolu, gerçek sohbet kimliği ve bazen gerçek anahtar bulunur.

## When to Use

- "skilleri github'a at", "skill pack repom olsun", "bunları yayınla"
- "kendi skill paketimi paylaşalım", "publish my skills"
- Kişisel bir betiği veya aracı herkese açık depoya çıkarmadan önce
- Herhangi bir yerel klasörü (not, yapılandırma, arşiv) halka açmadan önce

Yalnızca **kendi** üretimini yayınlarken. Dışarıdan pack kurmak için
`skill-pack-install` kullan.

## İKİ AYRI SORU var, sırayla sor

Yayınlamadan önce her skill iki elemeden geçer ve bunlar bağımsızdır:

1. **Kime ait?** Bu skill'i kullanıcı mı yazdı, yoksa kurulumla mı geldi?
2. **Ne sızdırıyor?** İçinde müşteri adı, kimlik, yol, anahtar var mı?

Bu skill'in ilk sürümü yalnızca 2. soruyu soruyordu ve o yüzden yanlış bir
depo yayınlandı. 2026-08-14'te kullanıcının düzeltmesi:

> *"ben bu repoda kendi ürettiğim skilleri barındırayım istiyordum ama sen
> dün var olan tüm skilleri yükledin oraya"*

Haklıydı. 115 dosya yayınlanmıştı, **81'i başkasının işiydi.** Sızıntı
taramasından temiz geçmişlerdi, çünkü sızıntı yoktu; sorun sahiplikti.

### Sahiplik elemesi nasıl yapılır

Üç grup dışarıda kalır:

**Kurulumla gelenler.** Hermes ve eklentileriyle hazır gelen skiller. Mekanik
olarak tespit edilir, upstream ağaçlarındaki `SKILL.md` adlarını topla ve
depodakilerle kesiştir:

```bash
find ~/.hermes/hermes-agent/skills ~/.hermes/hermes-agent/optional-skills \
     ~/.hermes/plugins -name SKILL.md \
  | sed 's|.*/\([^/]*\)/SKILL.md|\1|' | sort -u > /tmp/upstream.txt
```

Depodaki bir skill adı bu listede varsa kullanıcının değildir.

**Satıcı belge paketleri.** Bir ürünün dokümantasyonunu taşıyan skiller
(bulut sağlayıcı belgeleri, CLI kılavuzları, SDK referansları). Ad listesi
değil, ölçüt şu: skill kullanıcının **öğrendiği** bir şeyi mi anlatıyor,
yoksa satıcının kendi belgesinin özeti mi. İkincisiyse dışarıda kalır.

**Kişiye özel olanlar.** Aşağıdaki ayrı bölüm.

Kalanlar gerçekten bu makinede iş yapılırken yazılmış olanlardır. Ölçüm:
115 → 34. Sonra kişiye özel eleme ile 34 → 30.

> **Neden önemli:** başkasının 81 dosyası, kullanıcının 30 dosyasını
> gömüyordu. Depo hem yanıltıcı hem değersiz görünüyordu. Az ve kendine ait
> olan, çok ve karışık olandan iyidir.

## Kişiye özel skill: sızıntı DEĞİL ama yayınlanamaz

Ayrı bir eleme, çünkü aradığın şey gizli veri değil. Soru şu: **başkası bunu
kurarsa ne olur?**

Kullanıcının ifadesi:

> *"yazı stili skillim bana ait ve bana özel bir skill, bu herkese uygun olmaz"*

Doğru. O skill kullanıcının ölçülmüş yazım profilini taşıyor. Başkası
yüklediğinde ajanına **kullanıcı gibi yazmasını** söyler. Sızıntı yok ama
zarar var.

İki iz aranır:

```python
SES_IZI = re.compile(
    r"yazım protokol|writing voice|voice calibration|kullanıcının sesi|"
    r"ortanca mesaj|median message|tone profile|üslup", re.I)

AKIS_IZI = re.compile(
    r"<kullanıcı adı>|benim kurulum|my setup|bu makinede|kendi cron", re.I)
```

Ölçüm: 34 skill'in 14'ü işaretlendi, **4'ü kaldırıldı**, 14 dosya temizlendi.

Ayrım şöyle yapılır:

- **KALDIR** — skill'in *kendisi* kişiye özel: yazım profili, kullanıcının
  cron kurulumuna bağlı iş, kendi model tercihleri, kendi tetikleyici
  kelimeleri. Temizlemek işe yaramaz, geriye bir şey kalmaz.
- **TEMİZLE** — skill genel, sadece içinde ad geçiyor. Ad çıkınca aynen
  çalışır (`Kasparov` → `the user`, `pyto-bot` → `the messaging bridge`).

Betik: `scripts/kisisel_eleme.py`.

## Kural: ham klasör ASLA doğrudan gitmez

Ölçüm, 145 skill'lik gerçek bir kütüphanede (2026-08-13):

| Bulgu | Adet | Dosya |
|---|---|---|
| Müşteri/kurum adı | 646 | 82 |
| Sohbet ve kullanıcı kimliği | 72 | 19 |
| Mutlak ev dizini yolu | 96 | 24 |
| Telefon numarası | 3 | 2 |
| Özel ağ IP'si | 1 | 1 |

`git init && git add -A` deseydim bunların hepsi yayına çıkardı ve git
geçmişinden temizlemek çok daha zor olurdu.

## Akış

### 1. Önce TARA, sonra karar ver

Tarama betiği: `scripts/sizinti_tara.py`. Ham klasörü okur, hiçbir şey
değiştirmez, sadece ne bulduğunu basar. Çıktıyı kullanıcıya göster.

```bash
python3 scripts/sizinti_tara.py ~/.hermes/skills
```

Aranan desenler: API anahtarları (`sk-`, `ghp_`, `xox`, `AIza`, bot token
biçimi), e-posta, telefon, mutlak ev dizini, özel ağ IP'si, müşteri/kurum
adları, sohbet ve kullanıcı kimlikleri.

**Beyaz liste şart.** `example.com`, `your-`, `<your`, `placeholder`,
`000 0000` gibi örnek değerler bulgu sayılmamalı, yoksa gürültüden gerçek
bulguyu göremezsin.

### 2. Üç kova ayır

Taramadan sonra her skill üç kovadan birine düşer:

**Kova A, doğrudan gider.** Hiç bulgu yok.

**Kova B, temizlenip gider.** Öğrettiği şey genel ama örnek metninde müşteri
adı ya da mutlak yol geçiyor. Bunlar değerlidir, atma; genelleştir:

```
"Türkiye <Kurum> Vakfı"  -> "a client organisation"
"<Kurum>'in"             -> "the client's"
"<KURUM>"                -> "CLIENT"
"/Users/<kullanici>/"    -> "~/"
```

Cümle çevirdikten sonra hâlâ anlamlı kalmalı. "the client için tabela üretir"
okunabilir; "CLIENT için CLIENT" okunamaz.

**Kova C, hiç gitmez.** Skill'in kendisi müşteriye özel (kurumun sosyal medya
akışı, kurum içi araştırma hattı, kişisel otomasyon, iş arama hattı, uzak
makine erişimi). Bunlar temizlenince geriye bir şey kalmıyor zaten.

Ayrıca klasör olarak tamamen dışarıda tut: `.curator_backups/`, `index-cache/`,
`__pycache__/`. Yedek arşivleri sıkıştırılmış hâlde eski sürümleri taşır ve
tarayıcı içlerini okuyamaz.

### 3. Temizlikten SONRA yeniden doğrula

En önemli adım ve atlanması kolay. Temizleyip pakete aldığın her skill'i
**tekrar tara**; hâlâ kirliyse pakete alma, at.

Ölçüm: 19 skill temizlik için işaretlendi, 9'u temiz geçti, **10'u ikinci
taramada hâlâ kirli çıktı** (bir referans dosyasının adında kurum adı, bir
başkasında kişi adı, birinde ham sohbet kimliği). Sadece ilk taramaya
güvenseydim onlar yayına çıkardı.

Hazır betik: `scripts/skill_pack_hazirla.py` — üç kovayı uygular, temizler ve
temizlik sonrası doğrulamayı kendisi yapar.

### 4. Depoyu kur ve CANLI adresten doğrula

```bash
cd <paket-dizini>
git init -q && git add -A && git commit -q -m "..."
gh repo create <ad> --public --source=. --push
```

Push'tan sonra **ham dosya adresinden** kontrol et, yerel dosyadan değil:

```bash
for f in README.md tools/x.py devops/y/SKILL.md; do
  curl -s "https://raw.githubusercontent.com/<kullanici>/<depo>/main/$f" \
    | grep -ciE "<kurum>|/Users/|<kimlik>"
done
```

Sıfır dönmeliler. Yerelde temiz olması push'un temiz olduğunu kanıtlamaz.

## Yanlış yayınladıysan: force push YETMEZ

2026-08-14'te ölçüldü ve şaşırtıcı. Sızıntıyı fark edip düzelttikten sonra
geçmişi tek commit'e indirdim ve force push ettim. Depo temiz görünüyordu.
Ama eski commit'ler **hâlâ erişilebilirdi**:

```bash
for sha in e39b2b8 159bbb4 669de0f; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    "https://api.github.com/repos/<kullanici>/<depo>/commits/$sha"
done
# 200, 200, 200  <- ucu ucuna duruyorlar
```

GitHub force push sonrası eski nesneleri hemen toplamıyor. Depo listesinde
görünmüyorlar ama **SHA'yı bilen okuyabiliyor**. SHA'lar da gizli değil,
önceki push'ların çıktısında, forklarda, olay akışında duruyor.

Kesin çözüm depoyu silip yeniden oluşturmak:

```bash
gh repo delete <kullanici>/<depo> --yes
# temiz dizinde tek commit
gh repo create <depo> --public --source=. --push
```

Doğrulama, eski SHA'lar artık `422` dönmeli (depoya ait değil):

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  "https://api.github.com/repos/<kullanici>/<depo>/commits/<eski_sha>"
```

**Ne zaman silmeye değer:** depo yeniyse ve henüz yıldız/fork/issue yoksa
maliyeti sıfırdır, tereddüt etme. Depo yaşlıysa silmek geri alınamaz kayıp
demektir; o durumda GitHub Support'tan çöp toplama talep edilir ve sızan
sırlar **iptal edilmiş** sayılır.

> **Kural: bir sırrı yanlışlıkla yayınladıysan, silmek onu geri getirmez.
> Anahtarsa iptal et. Kişisel veriyse depoyu sıfırla.**

## Depoyu bir ürün gibi kur

Kütüphaneyi atmakla yayınlamak arasındaki fark burada.

**README dürüst olsun.** Neyin dışarıda bırakıldığını yaz: *"Client
identifiers and personal contact details have been removed. Skills that could
not be cleanly generalised were left out rather than published half-scrubbed."*
Bu cümle hem güven verir hem eksikliği açıklar.

**Araçları ve gerekçelerini birlikte koy.** Bir betik tek başına yarım
değerdedir; arkasındaki araştırma notu onu kullanılabilir yapar. Bu oturumda
ATS denetçisi `tools/` altına, dayandığı bulgular `tools/ATS-NOTES.md` olarak
yanına kondu.

**Lisans ekle.** MIT yeterli. Lisanssız depo teknik olarak kullanılamaz.

**Kategori tablosu koy.** 116 skill düz liste hâlinde okunmaz; hangi klasörde
ne olduğunu tabloya dök.

## Pitfalls

- **`git add -A` demeden önce tara.** Bir kez commit edilen sır, dosyayı
  silsen bile geçmişte kalır. Sıra: tara → temizle → yeniden tara → init.
- **Temizlik sonrası doğrulamayı atlama.** Ölçülen kaçak oranı 10/19.
- **Regex "air" tuzağı.** `artificial` ararken `\bA\.?I\b` gibi dar desen
  kullan; geniş desen `airline`, `aircraft`, `airport` yakalar. Bu oturumda
  ilk filtre 161 sonuç verdi, çoğu havayolu şirketiydi; daralttıktan sonra 65
  gerçek sonuç kaldı.
- **Kişiye özel skill'i "temizleyip" yayınlamaya çalışma.** İş arama hattı,
  kurum içi içerik akışı, kişisel makine erişimi gibi skill'lerde geriye
  öğretecek bir şey kalmaz. Kova C'ye koy ve kullanıcıya sebebini söyle.
- **Şüphede dışarıda bırak.** Eksik skill, sızmış veriden iyidir. Bu kuralı
  kullanıcıya da söyle, çünkü "neden 145 değil 116" sorusunun cevabı budur.
- **Sızıntı taraması sahiplik sorusunu CEVAPLAMAZ.** Kurulumla gelen 81 skill
  taramadan tertemiz geçti, çünkü içlerinde sızıntı yoktu. "Temiz" ile
  "yayınlanmalı" ayrı şeyler.
- **Force push geçmişi temizlemez.** Eski commit'ler SHA ile erişilebilir
  kalır. Yukarıdaki bölümü oku.
- **Derin tarama YANLIŞ ALARM üretir, bulguları körlemesine temizleme.**
  20+ desenli tarama 92 bulgu verdi, gerçek olan 3'tü. Gerisi satıcı
  belgelerindeki örnek e-postalar (`inbox@corp.com`), maskeli örnek telefon
  (`+141****1212`), ve `.claude/settings.local.json` gibi dosya yolları
  (`IC_ALAN` desenine takılıyor). Her bulguyu **çevresiyle birlikte** bas ve
  gözle ayır; temizleme kararını sayıya değil içeriğe göre ver.
- **LICENSE'taki gerçek ad bulgu değildir.** Telif için gereklidir, dokunma.
  Tarayıcı onu her seferinde işaretleyecek, bunu bilerek geç.
- **Yayınlanan depoyu KULLANICI adına konuşarak tanıtma.** README ve commit
  mesajı deponun sahibinin ağzından yazılır. \"Bugün şunu düzelttim\" gibi ajan
  günlüğü cümleleri depoya girmez; ne yaptığın değil, dosyanın ne öğrettiği
  yazılır.

## Destek dosyaları

- `scripts/sizinti_tara.py` — salt okunur tarayıcı, hiçbir şeyi değiştirmez.
- `scripts/kisisel_eleme.py` — SAHİPLİK elemesi: kurulumla gelenleri ve
  kişiye özel olanları ayırır. Sızıntı taramasından ayrı çalıştır, çünkü
  farklı soru sorar. Varsayılan rapor modu, `--uygula` ile siler.
- `scripts/skill_pack_hazirla.py` — üç kovayı uygular, genelleştirir ve
  temizlik sonrası doğrulamayı yapar.

## Sıra (hepsi gerekli, atlama)

1. `kisisel_eleme.py` → kime ait, kim kalmalı
2. `sizinti_tara.py` → ne sızdırıyor
3. `skill_pack_hazirla.py` → temizle
4. `sizinti_tara.py` tekrar → temizlik tuttu mu (kaçak oranı 10/19 ölçüldü)
5. `git init` → tek commit
6. `gh repo create --push`
7. Canlı ham adresten doğrula
8. Yanlış bir şey çıktıysa depoyu **sil ve yeniden kur**, force push yetmez
