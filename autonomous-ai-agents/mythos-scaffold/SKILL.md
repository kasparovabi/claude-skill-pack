---
name: mythos-scaffold
description: >
  Push Opus-class and smaller models toward Mythos/Fable-grade agentic behavior.
  Kernel of Fable-distilled patterns (decomposition, verification, next-action, context economy)
  plus demand-loaded skills, persistent mission files, named sub-agents, enforcement hooks,
  and domain modes (research, migration). Use when starting complex multi-step work,
  long-horizon tasks, or anything needing systematic persistence and verification.
  DO NOT fully load on Fable 5 / Mythos 5; over-scaffolding degrades Mythos-class models.
  Source: https://github.com/kasparovabi/claude-mythos-scaffold (MIT, kasparovabi).
version: 0.3.0
author: kasparovabi
license: MIT
---

# Mythos Scaffold — Kullanım Kılavuzu

Kaynak repo: `~/.claude/skills/mythos-scaffold/`
Hermes skill path: `~/.hermes/skills/mythos-scaffold/SKILL.md` (bu dosya)

## Model gating — ÖNCE OKU

| Model | Ne yükle |
|---|---|
| Opus 4.8 / Opus 4.x / Sonnet / Haiku | Kernel + gerektiğinde tier'lar |
| Fable 5 / Mythos 5 (bu model) | Hiçbir şey, ya da sadece kernel'in bölüm 2'si |

**Bu oturum Fable 5 / Sonnet 4 gibi güçlü bir modelde çalışıyor olabilir. Scaffold'u tam yükleme — sadece verification bölümü yeter. Hedefi ve kısıtları söyle; adımları sayma.**

## Aktivasyon

Her zaman sadece kernel'i yükle:
`~/.claude/skills/mythos-scaffold/core/fable-distilled.md`

Diğer dosyaları yalnızca trigger'ı tetiklendiğinde aç:

| Aç | Ne zaman |
|---|---|
| `core/mode.md` | Framing, dürüst tavan, çalışma şablonu istediğinde |
| `core/tool-stack.md` | Hangi araç, hangi sırada belirsizse |
| `core/context-priming.md` | Yeni domain, "projeyi anla" |
| `core/decomposition.md` | Tek geçişe sığmıyorsa, sub-agent fan-out düşünülüyorsa |
| `core/agent-loop.md` | Uzun horizon, drift riski, çok turlu iterasyon |
| `core/verification.md` | "Bitti" demeden önce, non-trivial işlerde |
| `core/failure-recovery.md` | Hata, takılma, tekrarlayan başarısızlık |
| `core/memory.md` | Cross-session recall önemliyse |
| `core/headless.md` | Gözetimsiz çalışma: cron, loop, eval |
| `domains/research/` | Araştırma sentezi |
| `domains/migration/` | Codebase migration |

## Mission file

Uzun horizon işlerde görev durumu `~/.claude/mythos/missions/<slug>--<stamp>.md` dosyasına yazılır.
Aktif mission pointer: `~/.cache/mythos/active`
Komut: `/mythos-mode <görev>` | `resume` | `status` | `close`

## Kurulu sub-agents

`~/.claude/agents/` altında:
- `mythos-scout.md` — Haiku, mekanik toplu iş
- `mythos-builder.md` — Sonnet, hafif kod
- `mythos-heavy.md` — Opus, zorlu çok-dosyalı iş
- `mythos-verifier.md` — Sonnet, adversarial doğrulama (ASLA düzenleme yapmaz)

## Temel prensipler (kernel özeti)

**Decomposition:** Araçlara dokunmadan önce teslimabeliyi tek cümleyle tanımla. Done-condition yaz. En riskli bilinmeyeni önce çöz. Bağımsız işleri aynı mesajda batch et.

**Verification:** Edit = claim, sonuç değil. Kullanıcının tükettiği seviyede doğrula: UI → UI'ya bak, API → API'ı çağır. "Şimdi çalışmalı" yazma — çalıştır, çıktıyı yapıştır.

**Next action:** Done-condition'a karşı state'i karşılaştır, plana değil. 3 tur ilerlemesiz = pattern değiştir, retry etme. Fix-stack'i durdur, son known-good'a dön, yeniden diagnose et.

**Context economy:** Priming'i window'un %10-15'iyle sınırla. İhtiyaç duyduğun aralığı oku, dosyanın tamamını değil.
