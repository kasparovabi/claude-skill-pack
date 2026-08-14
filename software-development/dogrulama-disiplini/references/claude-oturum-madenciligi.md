# Claude Code oturum kayıtlarından problem-çözüm madenciliği

Gerçek yaşanmış teknik problemleri ve nasıl çözüldüklerini çıkarmak için.
İçerik üretiminde (blog, LinkedIn, eğitim notu) haber taramasından çok daha
değerli: veri yalnızca kullanıcıda vardır, kimse kopyalayamaz.

## Veri kaynağı

```
~/.claude/projects/**/*.jsonl
```

Her satır bir JSON kaydı. Ölçülen bir kurulumda 6.400+ oturum dosyası vardı.

Satır türleri: `user`, `assistant`, `attachment`.

İçerik `message.content` altındadır ve iki biçimde gelir:
- `str` — düz metin
- `list[dict]` — parçalar; `{"type": "text", "text": ...}` ve
  `{"type": "tool_result", "content": ...}` işe yarar olanlar

## Kritik tuzak: aracın kendi telemetrisi

İlk saf tarama (sadece `error|failed|traceback` araması) **135 sonuç
döndürdü ve hepsi çöptü.** Claude Code'un kendi iç mesajlarında da bu
kelimeler geçiyor.

Elenmesi gereken desenler:

```
<observed_from_primary_session>   <observation>   <summary>
<what_happened>   <investigation>   <request>
MODE SWITCH   CRITICAL TAG REQUIREMENT
occurred_at   working_directory   system-reminder
<command-name>   tool_use_id
```

Ayrıca kod içi yanlış eşleşmeler: `error_handling`, `errors.log`,
`on_error`, `catch`, `except`, `.error(`, `error: None`, `no error`.

## İki kapılı tespit

Gerçek bir problem şu iki kaynaktan birinden gelmeli:

1. **Kullanıcı şikâyeti** (`type == "user"` + şikâyet kalıbı):
   `çalışmıyor, olmuyor, hata veriyor, patladı, bozuldu, yapamıyor,
   yanlış, eksik, kayboldu, gelmiyor, görünmüyor`
2. **Araç çıktısı hatası** — hata deseni var ve metin kısa (<2000 karakter;
   uzun bloklar genelde döküman/kod, gerçek hata değil)

Ek şart: **çözüm sinyali sonradan gelmeli.** Çözülmemiş problemin öğretici
değeri yoktur. Kayan pencere (son ~6 mesaj) içinde ara:
`fixed, resolved, works now, çalıştı, düzeldi, çözüldü, geçti, OK:`

Bu iki kapı devreye girince 135 → 72 sonuç, içlerinde gerçek olanlar:
commit'siz PR açma hatası (`Head sha can't be blank`), izin
sınıflandırıcısı bloğu, geçersiz koordinat hatası.

## Yapı

```python
def _metin(d):          # JSONL satırından düz metin
def oturum_tara(yol):   # tek dosyada problem-çözüm çifti
def mac_tara(gun):      # tarihe göre yerel tarama
def windows_tara(gun):  # Tailscale üzerinden uzak tarama
```

Aynı belirtinin tekrarı ilk 90 karaktere göre elenir.

## Çok makineli tarama

Tailscale üzerinden ikinci makine (`tailscale status` ile IP bulunur):

```bash
ssh -o BatchMode=yes ahmet@<tailscale-ip> 'powershell -NoProfile -Command "..."'
```

**Fail-closed kuralı:** uzak makineye erişilemiyorsa sessizce boş dönme.
Çıktıda açıkça `"bağlanamadı"` yaz. Yoksa eksik veriyle içerik üretilir ve
kimse fark etmez.

PowerShell tırnak cehennemine girmemek için: komutu `.ps1` dosyasına yazıp
`scp` ile gönder, sonra çalıştır.

## İlgili

Ana ilke için `SKILL.md` → "Gürültüyü saymak" ve "Filtre boş/aşırı sonuç
döndürdüğünde önce GİRDİYİ doğrula".
