---
name: <pack>-tetikleyici
description: >
  Türkçe doğal-dil yönlendirici (router) — kullanıcı slash komut yazmadan,
  normal Türkçe mesajıyla <konu> işi istediğinde hangi skill'in yükleneceğini
  belirler. Şu ifadelerden biri geçtiğinde devreye girer: "<örnek ifade 1>",
  "<örnek ifade 2>", "<örnek ifade 3>" ... (kullanıcının gerçekte yazacağı
  Türkçe cümleleri buraya BOL BOL koy — router'ın tetiklenmesi bu açıklamadaki
  kelime eşleşmesine bağlı).
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [router, turkce, tetikleyici, <konu>]
    related_skills: [<asıl skill 1>, <asıl skill 2>]
---

# <Pack> Tetikleyici — Türkçe Doğal-Dil Yönlendirici

Kullanıcı slash komut yazmaz; normal Türkçe mesajıyla iş ister. Bu skill o
ifadeleri doğru uzman skill'e bağlar. ÖNCE bu tabloyu uygula, sonra eşleşen
asıl skill'i skillread ile yükle ve onun talimatlarını izle.

## ZORUNLU ÖN OKUMA
Herhangi bir işe başlamadan ÖNCE `YEREL_UYARLAMA.md` oku — tech/etik kısıtlar
(Vercel/Next YASAK, alternatif yığın, görsel kimlik, kota/maliyet kuralları)
orada ve pack'in önerilerini EZER.

## Türkçe ifade → yüklenecek skill
| Kullanıcı şunu derse | Yükle |
| --- | --- |
| "<ifade>" | `<skill-adı>` |
| ... | ... |

## Kombinasyon kuralları
- Karmaşık iş birden çok sistem gerektiriyorsa önce pack'in kendi router'ını
  (varsa) yükle, o en küçük gerekli seti seçsin; gereksiz tüm skill'leri yükleme.
- the client işi her zaman: YEREL_UYARLAMA'daki görsel kimlik + render→vision doğrula.

## Tetiklenmeyecek durumlar
Sadece <konu> bağlamında çalışır. Alakasız (metin/çeviri/araştırma) işlerde
devreye GİRMEZ.
