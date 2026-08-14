# Gerçekçi Sayfa-Çevirme Fiziği — NotebookLM Araştırma Özeti

Bu not, "yapraklar düz levha gibi duruyor, gerçek fizik kurallarına uymalı, hafif dalgalı
olmalı" geri bildirimi üzerine NotebookLM research ile toplanan akademik/CG kaynaklarının
sentezidir. Kaynaklar: Interactive Geometry Lab (developable surfaces), Soft Math Lab
(Elastica), Cyanilux shader tutorials, Inria deformable objects, Easing Functions Cheat Sheet.
Aşağıdaki formüller flipbook render motoruna (riffle + açılış fazları) uygulandı ve onaylandı.

## 1. Geometrik model — konik developable surface
Kağıt = uzatılamayan ama bükülebilen developable surface (Gauss eğriliği her yerde 0,
yırtılmadan düzleme açılır). Sayfa bir köşeden tutulup çevrildiğinde **konik model** en
gerçekçi. Parametrizasyon: `r(s,r) = r·u(s)` (r = köşeden uzaklık, u(s) birim küre eğrisi).
Eğrilik dağılımı (omurga az, dış kenar çok) Elastica denklemiyle:
`κ̈ + (a² + ½κ²)κ = 0` — bükülme enerjisini minimize eder.

UYGULAMA: yaprağı tek düz açıyla döndürmek yerine her şeride (u) değişen lokal açı ver.
`local_beta(u) = beta + curl·sin(π·u·0.85)` — omurga (u≈0) sabit, dış kenar (u≈1) curl kadar
geriye yaylanır. Bu S-eğrisini üretir.

## 2. Serbest kenar yolu ve S-kıvrımı (curl)
Serbest kenar yarı dairesel yay izler. Yükselme sin tabanlı:
`y_offset = sin(açı·π)·uzaklık`. S-kıvrımı: omurgaya yakın (UV.x≈0.5) hareketsiz, dış kenar
(UV.x=1) tam yay — inverse-lerp ile kontrol. Dışbükeyden içbükeye geçiş ("popping") elastik
enerjiyle modellenir.

UYGULAMA: `z = u·W·sin(local_beta) + (CURL+lift)·sin(π·u)`. curl dönüş ORTASINDA max:
`curl = 0.55·sin(π·lt)` (lt = yaprağın yerel zamanı 0..1). Başta/sonda curl=0 → yaprak düz
başlar, ortada kıvrılır, düz biter. Gerçek kağıt davranışı.

## 3. Riffle (fırr tarama) — easing ve faz
Gerçek nesneler aniden durmaz → **easeInOutCubic** veya **easeInOutSine** kullan.
easeInOutCubic: `4x³ if x<0.5 else 1-(-2x+2)³/2`. Sayfalar arası faz farkı: her yaprağa
`t - n·Δt` gecikme; yapraklar geçmiş geometriler arası enterpolasyonla akar.

UYGULAMA: build.py'de `beta = THETA + (PI-2·THETA)·ease_cubic(lt)` (eski smooth/smoothstep
yerine). Faz: `start = l·step, step = (1-SPAN)/(nleaves-1), lt = (gt-start)/SPAN`.

## 4. Gutter (omurga çukuru)
Açık kitabın omurga kavisi "binding glue" potansiyeliyle modellenir — omurga normali n ile
sayfa tanjantları arasındaki açıyı minimize eder:
`V_glue = w·[(⟨n,d_sol⟩-1)² + (⟨n,d_sağ⟩-1)²]`. Sayfalar masaya düz yapışmaz, hafif havalanır.

## 5. Kalınlık ve gölge gerçekçiliği
- Sayfa kalınlığı: köşe normalleri doğrultusunda ±t/2 normal-offset (hacim).
- Yarı saydamlık (translucency): Cook-Torrance BRDF'e ek `k_t = (1-F_schlick_arka)·e^(-α·t)`.
- Düşük performansta gölge: koyu doku/düzleştirilmiş üçgenlerle fake'le.

## Render geometri hijyeni (fizik uygularken birlikte çıkan artefaktlar)
Fizik-kıvrımı doğru olsa bile şu iki render hatası gerçekçiliği bozar; kullanıcı bu oturumda
ikisini de ayrı ayrı yakaladı:

**(a) Koyu cilt katmanı zemine taşıyor (\"arkaplanda siyah\")**: draw_book_base'de katmanlı
sayfa yığınını çizip EN SON koyu cilt tabanını boyarsan, koyu poligon krem üst yüzeye taşar ve
sağ tarafta sayfa olmayan karelerde (açılış/bitiş) zemine karşı siyah blok görünür. ÇÖZÜM sırası:
(1) koyu cilt tabanını ÖNCE boya → (2) sayfa katmanlarını ALTTAN ÜSTE çiz
(`for li in reversed(range(LAYERS))`) → (3) en üst krem yüzeyi açıkça boya. Üst yüzey hep krem,
koyu renk yalnız kenar/dip.

**(b) Kapak ile iç sayfa genişlik uyumsuzluğu (\"içerik başta/sonda değişiyor\")**: Kapak landscape
tam-board, iç sayfalar spread→yarım olunca açılışta yaprak aniden yarı genişliğe düşer, kapağın
yarısını iç sayfa gibi gösterir. ÇÖZÜM: kapağı (ve gerekiyorsa arka kapağı) yarıma BÖLME, tam board
tek parça çevir; arka yüzüne sade krem sayfa koy. Riffle/bitişi spread-tuple yerine DOĞRUDAN seq
indeksiyle sür (yaprak l → front=seq[2l], back=seq[2l+1]) ki faz geçişleri hizalı olsun.
seq'te olmayan sentetik görselleri (cover_full, cream_page) leaf yapabilmek için PIL.Image kabul
eden ikiz fonksiyon (render_frame_img) ekle — index-tabanlı render_frame bunu yapamaz.

## NotebookLM nasıl tekrar üretilir
```
~/.local/bin/nlm research start "<fizik sorgusu>" --source web --mode fast \
  --title "Sayfa Cevirme Fizigi"
~/.local/bin/nlm research status <notebook_id>      # tamamlanınca task_id verir
~/.local/bin/nlm research import <notebook_id> <task_id>   # 10 kaynak içeri al
~/.local/bin/nlm notebook query <notebook_id> "<teknik soru>" > ans.json
# ans.json -> json['value']['answer'] sentezlenmiş cevaptır
```
auto-import zaman aşımına uğrarsa research yine tamamlanır; status + import manuel yap.
