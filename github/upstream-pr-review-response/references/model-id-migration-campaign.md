# Vaka: emekli model kimliği göç kampanyası (2 Ağu 2026)

Bu skill'deki kalıpların çıktığı gerçek oturum. Sayılar ve bulgular birebir.

## Kampanyanın şekli

Anthropic'in emekli ettiği model kimliklerini (`claude-3-5-sonnet-20241022`,
`claude-opus-4-20250514`, `claude-3-7-sonnet-20250219` vb.) hâlâ kullanan açık
kaynak repolara düzeltme PR'ı açılmıştı. Aynı düzeltme, aynı branch adıyla
(`chore/opus5-compat`) yedi repoya birden gitti.

Bu şekil önemli: **tek tip düzeltme, çok repo**. Her repoda farklı CI, farklı
bot reviewer, farklı katkı kuralı var. Toplu tarama olmadan yönetilemez.

## Durum tablosu (tarama anı)

| Repo | PR | Durum | Not |
|---|---|---|---|
| rmyndharis/antigravity-skills | #10 | MERGED | iş bitti |
| muratcankoylan/Agent-Skills… | #115 | MERGED | iş bitti |
| Cluster444/agentic | #14 | OPEN, CLEAN | hiç CI yok, maintainer bekliyor |
| julianromli/droid-factory-template | #1 | OPEN, CLEAN | CodeRabbit+GitGuardian+cubic temiz |
| wildcard/caro | #1390 | OPEN, UNSTABLE | **CLA imzasız** — insan engeli |
| pr-pm/prpm | #274 | OPEN, UNSTABLE | cubic 9 bulgu |
| davila7/claude-code-templates | #771 | OPEN, UNSTABLE | cubic 2 bulgu + 2 kırmızı CI |

İki merge, iki temiz bekleyen, bir insan engeli, iki gerçek iş. Sınıflandırma
yapılmadan hepsine aynı emek harcanırdı.

## Bulgu 1 — yarım kalmış göç (prpm#274, cubic 9 bulgu)

İlk commit yalnız `model:` **örnek değerlerini** değiştirmişti. Aynı dosyalardaki
referans listeleri ve alan açıklamaları eski kimliklerde kaldı:

- `FRONTMATTER.md` — "Available Models" listesi, güncellenmiş örneklerin **tam
  üstünde** emekli kimlikleri öğretmeye devam ediyordu
- `SKILL.md` — aynısı "When to use different models" listesinde
- `opencode.schema.json`, `opencode-slash-command.schema.json` — `model` alanının
  `description`'ı eski kimliği örnek gösteriyor, `examples` dizisi yeniye çevrilmiş
- `opencode.md`, `kiro-agents.md` — aynı çelişki

Yani emekli kimlikleri temizlemek için açılan PR, kendi içinde emekli kimlik
bırakıyordu. Reviewer'ın deyişiyle: PR'ın desteklediği checker bu dosyaları hâlâ
işaretlerdi.

**Onarım:** PR'ın kullandığı eşlemeyi diff'ten çıkar, sonra tüm kapsamda uygula.

```python
MAP = {
    "anthropic/claude-sonnet-4-20250514": "anthropic/claude-sonnet-4-6",
    "claude-3-5-haiku-20241022": "claude-haiku-4-5-20251001",
    "claude-3-5-sonnet-20241022": "claude-sonnet-4-6",
    "claude-opus-4-20250514": "claude-opus-4-8",
}
ORDER = list(MAP)   # uzun/prefiksli anahtar ONCE islensin
```

Eşlemeyi hafızadan uydurma — PR'ın ilk commit'inden oku:

```bash
git diff HEAD~1 HEAD -- . | grep -E '^[+-].*claude-'
```

Sonuç: 8 dosya, +12/−12. Kapsamda emekli kimlik kalmadı, iki JSON şeması hâlâ
geçerli.

## Bulgu 2 — reddedilen bulgu (aynı PR)

cubic, `EXAMPLES.md` için iki bulgu yazmıştı. Dosya grep'lendiğinde emekli kimlik
**yoktu**; satır numaraları başka dosyaya kaymıştı.

```bash
grep -n 'claude-' .claude/skills/slash-command-builder/EXAMPLES.md
# 68:  model: claude-haiku-4-5-20251001
# 688: model: claude-haiku-4-5-20251001
```

Olmayan şey değiştirilmedi ve bu kullanıcıya açıkça söylendi. Bot bulgusunu
körü körüne uygulamak burada gereksiz diff üretirdi.

## Bulgu 3 — etkisiz değişiklik (cct#771, P1)

En ciddi bulgu. `evaluation.py`'de fonksiyon imzasının varsayılanı güncellenmiş:

```python
model: str = "claude-sonnet-4-6",     # satir 223 — guncellenmis
```

Ama argparse varsayılanı bayat kalmıştı ve `args.model` her zaman açıkça
`run_evaluation`'a geçiyordu:

```python
parser.add_argument("-m", "--model", default="claude-3-7-sonnet-20250219", ...)
```

Yani `-m` vermeden koşan herkes hâlâ emekli modele düşüyordu. **Değişiklik
pratikte hiçbir işe yaramıyordu.** Aynı emekli kimlik kullanım örneğinde ve
`reference/evaluation.md`'de iki yerde daha duruyordu.

Doğrulama, iddia değil ölçüm:

```python
m  = re.search(r'parser\.add_argument\("-m", "--model", default="([^"]+)"', src)
m2 = re.search(r'\n    model: str = "([^"]+)"', src)
assert m.group(1) == m2.group(1)
```

## Bulgu 4 — senkronize edilmemiş türev dosya (cct#771, P2)

`cli-tool/components/settings/` altındaki ayar bileşenleri güncellenmiş, ama
`dashboard/public/component-content/settings/` altındaki **üretilmiş kopyaları**
güncellenmemişti. Panel emekli kimlikleri servis etmeye devam edecekti.

Türev dosyalar `{"content": "<kaynak dosyanin ham metni>"}` sarmalı. Elle
düzenlemek yerine kaynaktan yeniden türetildi:

```python
for src, dst in PAIRS:
    wrapper = json.loads(dst.read_text())
    wrapper["content"] = src.read_text()
    dst.write_text(json.dumps(wrapper, ensure_ascii=False))
# dogrulama
assert json.loads(dst.read_text())["content"] == src.read_text()
```

## Kırmızı CI — atfedildi, düzeltilmedi (cct#771)

İki check kırmızıydı, **ikisi de PR'la ilgisiz**:

- **Security Audit** — 129 dosyada düşüyor: `ai-ethics-advisor.md`,
  `llm-architect.md`, `smart-contract-auditor.md`. PR bunların hiçbirine
  dokunmamıştı.
- **SkillSpector** — `Scanned=8 flagged=4`, üstüne SARIF yükleme ve yorum yazma
  izni patlamış: `Resource not accessible by integration`.

`main` dalındaki son koşulara bakıldığında bu iki iş **hiç görünmüyordu** —
yalnız PR'larda tetikleniyorlar. Yani "main'de de kırık" diye gösterilecek
doğrudan kanıt yoktu ve bu kullanıcıya dürüstçe söylendi: gerekirse başka bir
açık PR'da aynı hatanın düştüğünü göstermek gerekir.

Bu ayrım yapılmasaydı 129 dosyalık bir "düzeltme" PR'ı boğardı.

## CLA — insan sınırı (caro#1390)

cubic 12 dosyada sıfır sorun buldu, kod tarafı temizdi. Tek engel: repo, CLA'nın
PR'a yorum olarak imzalanmasını istiyordu. Bu kişi adına verilen hukuki bir
beyandır; kullanıcıya devredildi, adına yazılmadı.

Yan not: o repo Vercel kullanıyordu — kullanıcının uzak durduğu bir bağımlılık.
Bilgi olarak iletildi, karar kullanıcıya bırakıldı.

## Sonuç

İki PR'a takip commit'i push edildi:

- `prpm#274`: +17/−17 → +29/−29, 10 dosya, 2 commit
- `cct#771`: +23/−23 → +30/−30, 16 dosya, 2 commit

Her iki push öncesi CRLF taraması yapıldı (hepsi LF), diff stat kontrol edildi,
JSON'lar `json.loads` ile ve Python `py_compile` ile doğrulandı. Push'tan ~45 sn
sonra CI'ın yeniden koştuğu ve commit sayılarının beklendiği gibi olduğu teyit
edildi.

CRLF taraması boşuna değil: önceki bir oturumda yamalayıcı satır sonlarını
bozmuş, 2 satırlık değişiklik 1002 satır olarak görünmüştü. Dış bir repoya
gitseydi PR anında reddedilirdi.
