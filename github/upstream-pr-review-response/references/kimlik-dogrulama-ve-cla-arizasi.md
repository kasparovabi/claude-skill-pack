# Maintainer talebini kanıtla kapatmak + CLA arızası teşhisi

Aynı model-kimliği kampanyasının devamı, 6 Ağu 2026. Önceki tur PR'ları açtı;
bu tur maintainer taleplerini kapattı. İki kalıcı ders çıktı.

## 1. "Bu değerleri doğrula" talebi: doküman değil, API

`enuno/unifi-mcp-server#111` maintainer'ı `CHANGES_REQUESTED` verip şunu istedi:

> please verify the replacement Claude model identifiers against the current
> support matrix

Bu talebi "doğrudur herhalde" diye geçiştirmek PR'ı kapatmaz. Ölçüm gerekiyordu.

### Doküman sayfaları bot korumasına takılıyor

Önce resmî doküman denendi, üçü de **boş** döndü:

```bash
curl -s 'https://docs.anthropic.com/en/docs/about-claude/models/overview'   | grep -oE 'claude-[a-z]+-[0-9]-[0-9]+'   # bos
curl -s 'https://docs.claude.com/.../model-deprecations'                    | grep ...  # bos
```

Sayfa HTML dönüyor ama içerik istemci tarafında geliyor ve/veya bot filtresi var.
**Doküman sayfasından grep'lemek güvenilir bir doğrulama yöntemi değil.**

### Doğru kaynak: `GET /v1/models`

```bash
source ~/.hermes/secrets/env.sh
curl -s "https://api.anthropic.com/v1/models?limit=100" \
  -H "Authorization: Bearer $ANTHROPIC_AUTH_TOKEN" \
  -H 'anthropic-version: 2023-06-01' -o /tmp/models.json -w "HTTP=%{http_code}\n"
```

Sonra kesişim al — göz kararı değil:

```python
ids = [m["id"] for m in json.load(open("/tmp/models.json"))["data"]]
for kid in ["claude-sonnet-4-6", "claude-opus-4-8"]:
    print(kid, "GECERLI" if kid in ids else "LISTEDE YOK")
```

**Kimlik doğrulama tuzağı:** bu ortamda değişken `ANTHROPIC_API_KEY` değil
`ANTHROPIC_AUTH_TOKEN` ve başlık `x-api-key` değil `Authorization: Bearer`.
`x-api-key` ile denemek `401 authentication_error` döndürür. 401 alırsan
anahtarın geçersiz olduğunu varsayma, önce başlık biçimini ve değişken adını
kontrol et.

### Cevapta ne yazılır

Ham liste + hangi kimliğin nerede kullanıldığı + kaldırılanların artık listede
olmadığı. Üstüne maintainer'ın asıl derdine cevap ver ("bir daha çürümesin"):

> I used unversioned aliases (`claude-sonnet-4-6`) rather than dated snapshots.
> Aliases track the current snapshot, so this rot does not recur on the next release.

Bu, talebi teknik olarak kapatan cümledir. Ayrıca dört temas noktasının
(imza varsayılanı, argparse varsayılanı, `--help`, doküman örneği) birlikte
güncellendiğini belirt — yalnız imzayı güncellemek bu dosyada **no-op** olurdu,
çünkü `args.model` her zaman açıkça geçiliyor. (Ayrıntı: `model-id-migration-campaign.md`, Bulgu 3.)

### Kırmızı CI atfı: dosya listesiyle konuş

Aynı PR'da `Mermaid Diagram Sync Assistant` kırmızıydı. Atıf kanıtı:

```bash
gh pr view 111 --repo enuno/unifi-mcp-server --json files --jq '.files[].path'
# 4 dosya: 2 workflow + 2 mcp-builder dosyasi, hicbirinde mermaid diyagrami yok
```

Diff 8+/8−, tamamı model kimliği stringi. Diğer iki check (Socket Security) geçiyor.
Cevapta **kesin dille suçlama**, gözlemi ver ve kapıyı açık bırak:

> I could not find a way for a string swap in these files to affect diagram sync,
> so I believe this check is failing independently of the change. Happy to rebase
> if you see a connection I am missing.

## 2. CLA yeşile dönmüyor: imza metni değil, depolama arızası

`wildcard/caro#1390`. Bot istenen metni söylüyordu:

```
I have read the CLA Document and I hereby sign the CLA
```

Yorum yazıldı. Check **hâlâ kırmızı**. Buradaki refleks "metni yanlış yazdım,
tekrar deneyeyim" olmamalı — önce koşuları oku.

### Teşhis zinciri

```bash
# 1) Ilgili workflow kosulari
gh api "repos/wildcard/caro/actions/runs?per_page=15" \
  --jq '.workflow_runs[] | select(.name|test("cla";"i")) | "\(.created_at) \(.status)/\(.conclusion) event=\(.event)"'
# 08:37:48Z completed/success  event=issue_comment   <- imza yorumu
# 08:39:06Z completed/failure  event=issue_comment   <- recheck yorumu

# 2) Basarisiz kosunun log'u
gh api "repos/<owner>/<repo>/actions/jobs/<JOB_ID>/logs" | grep -iE "error|sign"
# ##[error]Committers of Pull Request number 1390 have to sign the CLA

# 3) Imza DEPOSU — kritik adim
gh api repos/wildcard/caro/contents/.github/cla-signatures.json?ref=cla-signatures \
  --jq .content | base64 -d
# {"signedContributors": []}
```

**İmzayı işleyen koşu `success` verdi, ama depo boş.** Dalın son commit'i
2025-12-31 tarihli, yani aylardır hiçbir imza yazılmamış. Liste boş kaldığı için
sonraki her kontrol katkıcıyı imzasız sayıyor. Bu bir **yazma izni arızası**,
imza metni sorunu değil.

### Yanlış hipotezi de eleyip yaz

Commit'in author/committer kimliğini kontrol et; ikinci bir kimlik varsa o da
imzalamalıdır ve arıza sende olabilir:

```bash
gh api repos/<owner>/<repo>/pulls/<N>/commits \
  --jq '.[] | {sha:.sha[0:8], author:.author.login, committer:.committer.login,
               a_mail:.commit.author.email, c_mail:.commit.committer.email}'
```

Bu vakada ikisi de `kasparovabi` + GitHub noreply adresiydi, yani ikinci kimlik
yoktu. Raporda bunu göstermek "sorun bende değil" iddiasını kanıta çeviriyor.

### Maintainer'a ne yazılır

Koşu zaman damgaları, boş depo çıktısı, dalın tarihi, commit kimliği. Sonunda
**iki somut seçenek** sun ve kararı ona bırak: imzayı tekrar yorumlamak, ya da
DCO'ya geçip `git commit -s` ile imzalı commit atmak.

`recheck` yorumu botu yeniden tetikler ama depo yazılamıyorsa sonucu değiştirmez.
İki denemeden fazla tekrarlama; üçüncü denemede teşhise geç.

## Genel ders: yeşile dönmeyen check'te üç katman

1. **Check ne diyor** — job log'undaki hata satırı
2. **Koşu gerçekten çalıştı mı** — `actions/runs`, conclusion + event
3. **Yan etkisi diske yazıldı mı** — imza dosyası, cache, artifact

Çoğu \"neden hâlâ kırmızı\" vakası 3. katmanda çözülüyor. 1. katmanda kalıp aynı
eylemi tekrarlamak tur yakar ve kullanıcıya \"denedim olmadı\" demekle biter.
