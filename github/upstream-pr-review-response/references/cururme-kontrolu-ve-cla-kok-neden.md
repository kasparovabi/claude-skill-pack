# Çürüme kontrolü ve CLA arızasının kök nedeni

7 Ağustos 2026 oturumu. İki maintainer talebi kapatıldı, biri çözüldü, biri
depo sahibine devredildi. Buradaki her komut ve çıktı gerçekten koşturuldu.

## 1. "Bir daha çürümesin" talebine kontrol betiğiyle cevap

### Talep

`enuno/unifi-mcp-server#111` — emekli model kimliklerini güncelleyen PR.
Maintainer `CHANGES_REQUESTED` verdi, iki şey istedi: kırmızı check yeşile
dönsün, ve yeni kimliklerin emeklilik listesiyle senkron kaldığı teyit edilsin.

İkinci istek tek seferlik bir ölçümle kapanmıyor. "Bugün geçerli" demek
maintainer'ın sorduğu şey değil; sorduğu şey **bir daha aynı PR'ı açmak
zorunda kalmayacağı**.

### Çözüm şekli

`scripts/check_model_ids.py` — repoyu tarar, bulduğu her model kimliğini canlı
API'ye sorar, emekli olan varsa sıfırdan farklı çıkar.

Tasarım kararları ve gerekçeleri:

| Karar | Gerekçe |
|---|---|
| Çıkış kodu 1 = emekli kimlik var | CI işi olarak bağlanabilmesi için tek yol |
| `--offline` bayrağı | kimlik bilgisi olmayan geliştirici de ne kullanıldığını görebilsin |
| Dosya yollarını da bas | "nerede" bilgisi olmadan bulgu eyleme dönmüyor |
| Ürün adlarını ele | `claude-code-action`, `claude-desktop` model kimliği değil, regex bunları yakalarsa rapor gürültüye boğulur |
| Kendi dosyasını atla | betiğin içindeki regex örnekleri bulgu sanılmasın |

Regex'in ayırt edici kısmı — hem yeni takma adları hem eski tarihli anlık
görüntüleri yakalar, ürün adlarını yakalamaz:

```python
MODEL_RE = re.compile(
    r"claude-(?:opus|sonnet|haiku)-[0-9][a-z0-9-]*"
    r"|claude-[0-9][a-z0-9-]*-(?:opus|sonnet|haiku)[a-z0-9-]*"
)
```

### Kimlik doğrulama tuzağı

Betik ilk sürümde sadece `ANTHROPIC_API_KEY` + `x-api-key` başlığını
destekliyordu ve canlı testte **çıkış 2** verdi:

```
Could not reach the Anthropic API: HTTP Error 401: Unauthorized
```

Sebep: makinede duran değişken `ANTHROPIC_AUTH_TOKEN` (108 karakter,
`sk-ant-o...` öneki) yani OAuth token'ı. `x-api-key` bunu reddediyor,
`Authorization: Bearer` istiyor. İkisini birden destekle:

```python
credential = os.environ.get("ANTHROPIC_API_KEY")
header = "x-api-key"
if not credential:
    credential = os.environ.get("ANTHROPIC_AUTH_TOKEN")
    header = "authorization"
```

Bu tuzak kendi doğrulama aracını çalıştıramamana yol açar; "API'ye ulaşılamıyor"
sanıp kaynağı suçlarsın, oysa sorun başlıktadır.

### Mutasyon testi — betiğin işe yaradığının kanıtı

Betiği yazmak yetmez, yakaladığını görmen gerekir:

```bash
# emekli kimligi geri koy
sed -i '' 's/claude-opus-4-8/claude-3-7-sonnet-20250219/' .github/workflows/claude.yml
python3 scripts/check_model_ids.py; echo "cikis: $?"   # -> 1
# RETIRED — these ids are referenced but no longer served:
#   claude-3-7-sonnet-20250219
#       .github/workflows/claude.yml

# geri al
cp /tmp/claude.yml.yedek .github/workflows/claude.yml
python3 scripts/check_model_ids.py; echo "cikis: $?"   # -> 0
git diff --stat                                        # bos, calisma alani temiz
```

Yorumda bu testi anlat. "Betik ekledim" ile "betiğin regresyonu yakaladığını
doğruladım" arasındaki farkı maintainer okur.

### Kapsam taraması: PR eksik mi kalmış?

Cevap yazmadan önce repoda kalan başka eski kimlik var mı bak. Varsa PR yarım
demektir ve maintainer bunu fark eder:

```bash
grep -rn --include='*.py' --include='*.yml' --include='*.md' --include='*.json' \
  -oE 'claude-[a-z0-9.-]+' . | grep -v '\.git/' \
  | sed 's/.*:\(claude-[a-z0-9.-]*\)/\1/' | sort | uniq -c | sort -rn
```

Bu oturumda çıktı temizdi: sadece `claude-sonnet-4-6` ve `claude-opus-4-8`,
kalanlar ürün adları. Yani PR tam kapsamlıydı ve bunu yorumda söyleyebildim.

## 2. Kırmızı check: tavsiyeyi uygula, sonra atfet

`Mermaid Diagram Sync Assistant` çıktısı:

> **Webhook Processing Failed** — An unexpected error occurred while processing
> the webhook. Please try pushing a new commit or check your repository
> configuration.

Check'in kendisi somut bir eylem öneriyor. Tartışmadan önce uygula:

```bash
git push origin <dal>          # yeni commit -> webhook yeniden tetiklenir
sleep 75
gh api repos/<owner/repo>/commits/$(gh pr view <N> --repo <owner/repo> \
  --json headRefOid --jq .headRefOid)/check-runs \
  --jq '.check_runs[] | {ad:.name, sonuc:.conclusion, baslangic:.started_at}'
```

Sonuç: check yeni commit'e karşı `15:34 UTC`'de yeniden koştu ve **aynı şekilde**
düştü. Bu artık bayat koşu değil, tekrarlanabilir bir arıza.

Atıf üçlüsünü rapora koy: hata metni, tavsiyeyi uyguladığın commit, yeni koşunun
damgası. Üstüne diff'in o alana dokunmadığını göster (dört dosya: iki workflow
YAML, iki skill dosyası, hiçbirinde mermaid diyagramı yok) ve diğer check'lerin
geçtiğini ekle.

## 3. CLA arızası: üç katmanlı teşhis, kesin kök neden

İmza yorumu yazıldı, `cla-check` kırmızı kaldı. Sıradaki refleks "metni yanlış
yazdım" olmamalı. Katman katman in.

### Katman 1 — koşular ne dedi

```bash
gh api 'repos/<owner/repo>/actions/runs?per_page=20' \
  --jq '.workflow_runs[] | select(.name|test("CLA";"i")) |
        "\(.created_at[0:16]) \(.status)/\(.conclusion) event=\(.event) id=\(.id)"'
```

```
2026-08-06T08:42 completed/success  event=issue_comment   # recheck
2026-08-06T08:39 completed/failure  event=issue_comment
2026-08-06T08:37 completed/success  event=issue_comment   # imza yorumu
```

İmzayı işleyen koşu **başarılı**. Yani metin doğru, tetikleme doğru.

### Katman 2 — job log'undaki gerçek hata

```bash
JID=$(gh api repos/<owner/repo>/actions/runs/<RUN_ID>/jobs --jq '.jobs[0].id')
gh api repos/<owner/repo>/actions/jobs/$JID/logs \
  | grep -iE 'error|fail|denied|403|refus|protected' | head -12
```

```
##[error]Committers of Pull Request number 1390 have to sign the CLA 📝
```

"Committers" çoğul — ikinci bir imzacı gerekiyor olabilir. Bu hipotezi ele:

```bash
gh api repos/<owner/repo>/pulls/<N>/commits \
  --jq '.[] | {sha:.sha[0:8], author_login:.author.login,
               committer_login:.committer.login}'
```

Author ve committer aynı kişi, imzayı atan da o. Hipotez elendi.

### Katman 3 — yan etki diske yazıldı mı (KÖK NEDEN BURADA)

```bash
gh api 'repos/<owner/repo>/contents/.github/cla-signatures.json?ref=cla-signatures' \
  --jq .content | base64 -d
```

```json
{ "signedContributors": [] }
```

Koşu başarılı ama liste boş. Kesin kanıt için dosyanın **commit geçmişine** bak:

```bash
gh api 'repos/<owner/repo>/commits?sha=cla-signatures&path=.github/cla-signatures.json&per_page=10' \
  --jq '.[] | "\(.commit.committer.date[0:16]) \(.commit.author.name): \(.commit.message|split("\n")[0])"'
```

```
2025-12-31T08:30 Kobi Kadosh: Research and align CLA for AGPL projects (#45)
```

**Tek commit, insan eliyle, aylar önce.** Bot bugüne kadar hiçbir imzayı
yazamamış. Bu bir kişi sorunu değil, deponun tamamını etkileyen yapısal arıza.

### Kalan hipotezleri ele

```bash
# yol dogru mu? (workflow .github/ altini ariyor)
gh api 'repos/<owner/repo>/contents/.github?ref=cla-signatures' --jq '.[].name'
# -> cla-signatures.json  VAR, yol dogru

# dal korumasi engelliyor mu?
gh api repos/<owner/repo>/branches/cla-signatures/protection
# -> 404 Not Found, koruma yok
```

Geriye token kalıyor. Workflow `contributor-assistant/github-action` çağrısını
`GITHUB_TOKEN` ile yapıyor ve hemen altındaki `PERSONAL_ACCESS_TOKEN` satırı
yoruma alınmış. Varsayılan Actions token'ı imza dalına push edemiyorsa eylem
imzayı kaydedemez ama yine de `0` ile çıkar — log'ların gösterdiği tam olarak bu.

### Maintainer'a sunum

Kanıtları sırayla ver (koşu damgaları, boş depo çıktısı, tek commitlik geçmiş,
eşleşen commit kimliği, 404 koruma) ve elediğin hipotezleri de yaz — neyi
kontrol ettiğini görmek maintainer'ın işini kısaltır. Sonunda iki somut seçenek
sun:

1. PAT etkinleştirilsin (ya da varsayılan token'a `cla-signatures` push izni
   verilsin), imza yorumu tekrarlansın
2. DCO'ya geçilsin — `use-dco-flag` şu an `false`, dal `git commit -s` ile
   yeniden imzalanıp force-push edilir

Bu bir yazma izni arızası ve **çözümü depo sahibinde**. `recheck` botu yeniden
tetikler ama depo yazılamadığı sürece sonucu değiştirmez; iki denemeden fazla
tekrarlama.
