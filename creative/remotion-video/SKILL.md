---
name: remotion-video
description: "Use when rendering a programmatic MP4. Remotion with React, deterministic output."
---

# Remotion Programatik Video

React/TypeScript ile kare-kare deterministik video. After Effects'in kod karşılığı. Headless Chrome her kareyi render eder, FFmpeg birleştirir. Aynı koddan farklı en-boy oranları (9:16, 1:1, 16:9) tek `Composition` listesiyle çıkar — sosyal medya çoklu format için ideal.

## Ne zaman Remotion, ne zaman başka araç
- **Remotion**: React bilgisi, data-driven (JSON'dan sayı/marker), 3D (@remotion/three), çok format, deterministik tekrar üretilebilirlik. Mevcut bir kurumsal videoyu yeni verilerle klonlamak.
- **flipbook-video**: PDF→sayfa çevirme efekti (ayrı skill).
- **manim-video**: matematik/algoritma animasyonu (ayrı skill).
- **hyperframes (HeyGen, açık kaynak)**: saf HTML/CSS→video, React istemiyorsan veya ajan HTML yazacaksa alternatif. `npm i hyperframes` + `hyperframes render index.html --output v.mp4`. Node 22+ ve FFmpeg gerekir.

## Kurulum (macOS, doğrulandı)
```bash
mkdir proje && cd proje && npm init -y
npm install remotion @remotion/cli @remotion/three \
  @react-three/fiber @react-three/drei @react-three/postprocessing three react react-dom
```
tsconfig.json'a `"resolveJsonModule": true` ekle (marker/veri JSON import için).
İlk `npx remotion still ...` çağrısı headless Chrome shell'ini indirir (~93MB) — normal, bir kez olur.

## Proje iskeleti
- `src/index.ts` → `registerRoot(RemotionRoot)`
- `src/Root.tsx` → her format için bir `<Composition>` (id, width, height, durationInFrames, fps, defaultProps). Aynı component'i 1080×1920 ve 1080×1080 ile iki kez kaydet.
- `src/design.ts` → **TEK KAYNAK tasarım sistemi**: COLORS, FONT (aile+ağırlık), SPRING configleri, SCENES (frame süreleri), STATS, hedef sayılar. AI-slop'tan kaçınmanın temeli budur.
- `src/MaarifVideo.tsx` → sahneler `<Sequence from=... durationInFrames=...>` ile zincirlenir. Her sahne `{width,height,portrait}` alır; `portrait = height>=width` ile responsive boyut.
- `src/ui.tsx` → paylaşılan Counter, Background.
- `src/Globe.tsx` → 3D küre (varsa).

## Determinizm (KRİTİK)
- `Math.random()` ve `Date.now()` YASAK — her render farklı çıkar. Yıldız/parçacık konumu için sabit-seed LCG kullan (`s=(s*1103515245+12345)&0x7fffffff`).
- Animasyon `useFrame` DEĞİL `useCurrentFrame()` ile. Rotasyon = `(frame/fps)*hız`.
- Sayaç: `spring({frame,fps,config})` → `interpolate(spr,[0,1],[0,hedef],{extrapolateRight:'clamp'})` → `Math.round`. `fontVariantNumeric:'tabular-nums'` ile rakamlar zıplamaz. Binlik ayraç `toLocaleString('tr-TR')`.

### Paralel animasyonlarda SENKRON (KRİTİK tuzak)
Aynı kavramı temsil eden iki eleman (ör. "64 ülke" sayacı + haritadaki 64 pin) AYNI easing eğrisini paylaşmalı. Klasik bug: sayaç `spring` (yumuşak ivmeli) ile sayarken pin reveal'ı düz `interpolate(frame,[start,end],...)` (lineer) ile gidiyor. İkisi aynı frame'de başlayıp bitse de **ORTADA ayrışırlar** — sayaç "40" derken ekranda 50 pin olur. Kullanıcı "aynı anda gelmiyor/bitmiyor" der.
- **Çözüm:** ikinci elemanın reveal'ını da sayacın bire bir aynı spring'iyle hesapla. Sayaç `spring({frame:frame-S, fps, config, durationInFrames:D})` kullanıyorsa, pin reveal de TIPATIP aynı `spring(...)` + aynı `interpolate(spr,[0,1],[0,hedef])` + aynı `Math.round` kullanmalı. Birebir kopyala veya ortak fonksiyon yap.
- **Doğrulama:** gerçek videodan iki farklı frame çıkar (orta + son), vision ile "sayaç kaç + kaç görünür pin" sor; eşleşmeli. Küre arkasındaki pinler gizliyse ekran sayısı < sayaç olabilir — bu normal, asıl kriter reveal sayısı = sayaç değeri.

## 3D küre (@remotion/three) — pitfall'lar
Detaylı çalışan kod ve tuzaklar: `references/remotion-three-globe.md`.
Özet kritik noktalar:
1. **Texture delayRender ile beklenmeli VE ThreeCanvas DIŞINDA (parent'ta) yüklenmeli.** `TextureLoader.load()` asenkron; beklenmezse küre SİYAH render olur. Texture'ı Canvas İÇİNDEKİ mesh'te useState ile yüklersen Remotion frame-izole render'da yakalamaz (küre hiç gelmez) — yüklemeyi Canvas'ı saran parent component'e taşı: `delayRender()` al, `loader.load(url, resolve)` bekle, `continueRender(handle)` çağır, hazır olana dek Canvas'ı `return null` ile beklet, texture'ı PROP olarak mesh'e geçir.
2. **ThreeCanvas arka planı örter.** Arkadaki CSS gradyan/yıldız görünsün diye: `gl={{alpha:true, premultipliedAlpha:false}}` + `onCreated={({gl})=>gl.setClearColor(0x000000,0)}` + `style={{background:'transparent'}}`.
3. **Fresnel atmosfer halosu tüm ekranı boyayabilir.** `AdditiveBlending` + `BackSide` halo mesh, kamera çok yakınsa veya fresnel üssü düşükse ekranı düz renge boğar. Önce küreyi atmosfersiz doğrula, sonra kontrollü ekle (üs ≥2.6, opacity düşük).
4. **lat/lng→3D**: `phi=(90-lat)*π/180; theta=(lng+180)*π/180; x=-(r·sinφ·cosθ); z=r·sinφ·sinθ; y=r·cosφ`.
5. Marker görünürlüğü: rotasyon sonrası normalin kameraya (+z) bakıp bakmadığını test et (`nW.z > -0.1`), arka yüz markerlarını gizle.
6. Sorun ayıklarken **MeshBasicMaterial ile izole et** (ışık bağımsız) — küre hiç mi gelmiyor yoksa aydınlatma mı yok ayırt edilir. AMA bu sadece DEBUG içindir; nihai üründe kalır KALMAMALI (bkz. madde 8).
8. **NİHAİ KALİTE: MeshBasicMaterial DÜZ/ucuz durur — sosyal medya için MeshPhongMaterial kullan.** `MeshBasicMaterial` ışık almaz, gece tarafı/terminatör/okyanus parlaması olmaz, küre tek-düz fotoğraf gibi görünür ("yeterli kalitede değil" şikayeti buradan gelir). Gerçekçi NASA dünyası için: `MeshPhongMaterial({ map:gündüz, bumpMap:bump, bumpScale:0.04, emissiveMap:gece, emissive:#ffe6b0, emissiveIntensity:0.55, specular:#335566, shininess:9 })` + düşük `ambientLight(0.28)` + güçlü yandan `directionalLight(1.55, #fff4e0)` (gündüz/gece terminatörü) + çok hafif ters dolgu ışığı (gece tarafı tam siyah olmasın). Üstüne ayrı bir bulut küresi (r=2.03, `alphaMap`=bulut texture, opacity 0.42, kürenin biraz farklı hızında dönen) ekle. the client dashboard'da bu texture'lar zaten var (earth-night/clouds/bump). Çalışan tam kod: `references/remotion-three-globe.md`.
7. **Kamera/rotasyon el yordamıyla kalibre edilir** (tek-kare render ile). Küre yarıçapı 2 ise kamera `[0,0.2,11] fov:30` taşmadan oturur (8.5 taşıyordu). Rotasyon offset ile hangi kıtanın merkeze geleceği seçilir (Afrika/the client yoğunluğu için `+3.55`). Detay: `references/remotion-three-globe.md`.

## Render
```bash
npx remotion still src/index.ts <KompozisyonID> out.png --frame=180   # tek kare doğrulama (HIZLI)
npx remotion render src/index.ts <KompozisyonID> out.mp4               # tam video
```
remotion.config.ts: `Config.setChromiumOpenGlRenderer('angle')` WebGL için. macOS'ta `timeout` komutu YOK — doğrudan çalıştır, gerekirse background+notify.

## "Ucuz duruyor" → DOLU kompozisyon (KRİTİK kalite)
Tek bir merkez öğe + boş zemin = ucuz/amatör his ("videonun tamamı ucuz duruyor" şikayeti). Sahneleri KATMANLA — her sahnede 4-6 anlam taşıyan eleman olsun:
- **Zemin asla düz olmasın:** radyal gradyan + ince kurumsal grid (SVG `<pattern>` strokeOpacity ~0.06) + soldan sağa süzülen diyagonal ışık huzmesi (`(frame*0.6)%140` ile hareket) + sabit-seed yıldız/parçacık (twinkle `sin(frame*hız+i)`) + yukarı süzülen büyük motes + vinyet (radyal `<radialGradient>` siyah dış). Hepsi tek `Background` component'inde.
- **Her sahnede sabit marka varlığı:** üst köşede küçük "TÜRKİYE MAARİF VAKFI" + renk noktası (BrandTag). Sürekli kurumsal aidiyet.
- **Boş alanı VERİYLE doldur:** küre/ana sahnede sol üst büyük sayaç, sağda mini istatistik çipleri (`6 KITA`, `496 KURUM`...), altta SÜREKLİ KAYAN ülke isimleri şeridi (NameTicker: `[...names,...names,...names]` + `translateX(-(frame*hız)%width)`). Kayan şerit "dolu/canlı" hissin en güçlü kaynağı.
- **İstatistik kartlarına ikon + üst renk şeridi + her rakam kendi renginde** ekle; düz metin liste değil grid (portre 2×2, kare/yatay 1×4). Üstte alt-başlık ("2024 VERİLERİYLE"), altta açıklama cümlesi.
- **Açılış/kapanışa hareket kat:** dönen kesik halka (`strokeDasharray` + `rotate(frame*hız)`), çift halka, glow + inset shadow. Statik logo ≠ canlı açılış.

### Kare (1:1) format öğe ÇAKIŞMASI (pitfall)
9:16'da rahat oturan yatay-yan-yana öğeler (sol sayaç + sağ çipler) **karede dar yatay alanda üst üste biner** (ör. "ÜLKEDE EĞİTİM" rozeti sağdaki "496 KURUM" çipini ezer). Çözüm: format-koşullu render — `portrait && height/width > 1.2` ile yalnız 9:16'da göster, karede gizle (o veri zaten istatistik sahnesinde tam haliyle var). HER FORMATTAN ayrı kare çıkarıp vision ile çakışma kontrol et; tek format doğrulaması yetmez.

### Instagram/sosyal medya GÜVENLİ ALAN (safe zone) — KRİTİK konumlandırma
Reels/Story (9:16, 1080×1920) yüklendiğinde Instagram UI öğeleri görselin ÜZERİNE biner: üstte kullanıcı adı/profil, altta açıklama + beğeni/yorum/paylaş, sağda dikey aksiyon-buton kolonu. Bu bantlara giren metin/sayaç/rozet kapanır. Kullanıcı "postların altını/üstünü profil adı ve açıklama kapatır" der.
- **Ölçüler (web araştırması, Verve/Meta/Minta/FizzyPop kılavuzları — tahmin değil):** 9:16'da üst ~220px (kullanıcı adı), alt ~320px (açıklama+butonlar), sağ ~120px (aksiyon kolonu), sol ~60px. Merkezi güvenli alan ≈ 1010×1440px. Kaynaklar farklı sayı verir; en geniş/güvenli olanı al (yüzde olarak üst 0.12·h, alt 0.18·h, sağ 0.11·w, sol 0.06·w).
- **1:1 feed (ve 4:5):** UI görselin DIŞINDA (üstte ad, altta açıklama ayrı satırda) → sadece hafif kenar boşluğu (~0.05-0.07) yeterli, agresif inset GEREKMEZ.
- **Uygulama:** design.ts'e `safeInsets(w,h)` fonksiyonu koy (`reels = portrait && h/w>1.4` testiyle 9:16'yı ayır), tüm sahneleri saran bir `<SafeArea>` wrapper'ı (AbsoluteFill'in top/bottom/left/right'ını insets'e eşitle) kullan. Dekoratif Background TAM EKRAN kalır (gradyan/küre kenara taşsın güzel durur), sadece KRİTİK öğeler banda girmez. **Kopyalanabilir kod + drawbox doğrulama komutu: `templates/safeArea.tsx`.**
- **Küreyi güvenli banda ortala:** dikeyde `translateY((top-bottom)/2)` ile kaydır, yoksa küre üst banda yakın kalır.
- **Doğrulama (zorunlu):** asıl videodan kare çıkar, ffmpeg `drawbox` ile üst/alt kırmızı + sağ turuncu bantları görsel olarak çiz, vision'a "bu bantlara giren öğe var mı" diye sor. Gözle tahmin etme — işaretleyip bak.

### Güvenli alan = sola yığma DEĞİL; MERKEZ-EKSEN denge (KRİTİK kompozisyon dersi)
Güvenli alana sığdırmanın TEMBEL/yanlış yolu: tüm öğeleri sol üst köşeye yığıp sağ kolonu bomboş bırakmak. Kullanıcı bunu \"kolaya kaçıp her şeyi sağa/bir tarafa yaslamışsın\" diye reddeder — dengesiz, amatör durur. Doğru yol DİKEY MERKEZ-EKSEN ritmidir, özellikle 9:16'da:\n- **Üst güvenli bant** → ORTALANMIŞ başlık bloğu (büyük sayaç + yanında etiket + altında rozet), `width:100% + alignItems:center` ile yatay merkezde.\n- **Orta** → küre/ana görsel KAHRAMAN öğe, tam merkezde (`translateY((top-bottom)/2)` ile iki bant arasına ortalanmış).\n- **Alt güvenli bant** → YATAY ortalanmış istatistik şeridi (`justifyContent:center` ile 3 çip yan yana eşit dağılmış), üstünde ortalanmış rozet.\nBöylece ağırlık ekranın orta dikey ekseninde toplanır, hiçbir yan boş kalmaz, simetrik durur. Sayaç+çipleri sol sütuna dikey dizmek (önceki \"çözüm\") YANLIŞTI — sağ taraf çöl gibi kalıyor.\n\n### Alt bölge üç-öğe çakışması (pitfall)\nMerkez-eksen düzeninde alt bantta birden çok öğe (kayan isim şeridi + rozet + çip satırı) varsa kolayca üst üste biner — kayan NameTicker tam çiplerin üstünden geçip etiketleri okunmaz yapar. Çözüm: alt bölgeyi sadeleştir. NameTicker DEKORATİF; çipler daha bilgilendirici. Çakışma çıkarsa NameTicker'ı KALDIR, alt bölge nefes alsın. Bir bantta en fazla 2 yatay-ortalı katman (rozet + çip satırı) tut.\nKarede (1:1) dikey alan dar → rozet ile çip satırı bile çakışabilir: rozeti `s.reels &&` ile sadece 9:16'da göster, karede çipler tek başına yeterli. HER format için ayrı kare + vision doğrula.\n\n### Güvenli alana sığdırırken iteratif daraltma (pitfall)
Öğeleri güvenli banda sığdırmak tek hamlede olmaz, 2-3 tur sürer — HER turda render + drawbox + vision döngüsü yap:
1. Yan-yana çipleri sağ aksiyon-buton kolonundan al, sol sütuna (sayacın altına dikey) taşı — sağ kolon TAMAMEN boş kalsın.
2. Tek satıra sığmayan başlık banda/ekran dışına taşar → `<br/>` ile iki satıra böl ("RAKAMLARLA / MAARİF").
3. Uzun kart etiketi karta sığmayıp sağ banda değer → grid'i daralt (width %86) + font küçült YETMEZSE **etiketi kısalt** ("EĞİTİM KURUMU"→"KURUM"). En kesin çözüm metni kısaltmaktır; daraltma/küçültme bir yere kadar. ICONS eşlemesi label'ı anahtar kullanıyorsa onu da güncelle.
Kart KENARI (zemin) banda 1-2px değmesi tolere edilebilir — kritik olan OKUNABİLİR İÇERİĞİN (sayı+etiket) banttan tamamen çıkması; IG ikonları kart kenarını anlamlı kapatmaz.

### Overpass fontu yükleme
`npm i @remotion/google-fonts@<remotion-sürümü>` → `import {loadFont} from '@remotion/google-fonts/Overpass'; export const {fontFamily:OVERPASS}=loadFont();` → design.ts'de `FONT.family = \`${OVERPASS}, system-ui, sans-serif\``. Versiyon remotion ile aynı olmalı (4.0.471 vs).

## AI-slop'tan kaçınma (NotebookLM araştırma özeti)
- Renk/tipografi/spacing'i design.ts'de kısıt olarak baştan sabitle, AI'ya bırakma.
- Jenerik mor gradyan, gereksiz parlak bloom, çok-font karmaşası YOK. Tek font ailesi + net ağırlık hiyerarşisi.
- Hareket fizik temelli (spring), lineer değil. Sahne geçişleri yumuşak fade (frame aralığında interpolate).
- Postprocessing: kurumsal videoda "yumuşak parıltı" — Bloom `luminanceThreshold` yüksek + düşük intensity, Vignette hafif. Glitch/aşırı bloom kaçar.

## Mustafa Bey / the client kuralları
- Görsel zekâ/illüzyon/metafor sever; şablon-figür sevmez. Klişeyi anında reddeder.
- Format: 3:2 yatay sosyal medyaya UYGUN DEĞİL → kare 1:1 / dikey 9:16-4:5 üret.
- **the client RESMİ kurumsal kimlik (turkiyemaarif.org CSS değişkenlerinden çekildi, tahmin DEĞİL):** Font = **Overpass** (Google Fonts açık kaynak; `@remotion/google-fonts/Overpass` ile `loadFont()` → `fontFamily`). Renkler: turkuaz **#04adbc** (--theme-3, ana marka), lacivert **#0d131b** (--theme-1), yeşil **#00c047**, amber **#ffca3b**, mercan **#fd5f61**, gri **#535a63**, açık zemin **#f7f7f7**. (Eski #08A8B8/#1e3f67 yaklaşıktı — bunlar gerçeği.) Zemin lacivert (#0d131b) tonlarına derinleştirilir. **Kurumsal kimliği yeniden teyit etmek gerekirse**: siteyi browser'da aç, console'da `getComputedStyle(document.documentElement)` ile `--theme-*` ve `--ol-*` CSS değişkenlerini + `getComputedStyle(document.body).fontFamily` oku, en sık geçen renkleri elemanları tarayarak frekans sırala. Bu yöntem her kurum için geçerli — markanın gerçek paletini varsaymadan çıkarmanın en hızlı yolu.
- **Olgu/sayı uydurma YOK**: istatistikleri kullanıcının kendi veri kaynağından (ör. maarif-dashboard countryData.ts) hesapla. computeInstitutionsTotal/computeStudentsTotal mantığı = blok başına `total:` toplamı.
- Video göndermeden ÖNCE asıl çıktıdan kare çıkar + vision ile doğrula (test karesinden değil).

## GÖRSEL-TABANLI sinematik mod (hazır kampanya görsellerini canlandırma)
Kullanıcı bazen sahneleri koddan kurmak yerine ELDE HAZIR (ör. ChatGPT/Midjourney ile üretilmiş, onaylı) tam kampanya görselleri verir ve "eski videoyu unut, sadece sıralamayı tut, bu görsellerle video yap; küre/pin/metin/atmosfer GÖRSELLERDEKİ gibi olsun" der. Burada 3D küre/metin/pin SIFIRDAN üretilmez — görsellerin kendi içeriği (küre, gece atmosferi, bağlı pinler, başlıklar, rakamlar) zaten basılıdır. İş = bu statik görselleri SİNEMATİK harekete dönüştürmek:
- **Ken Burns (yavaş zoom/pan):** her görsele `interpolate(frame,[0,dur],[0,1],{easing:Easing.bezier(0.33,0,0.25,1)})` ile yumuşak ölçek (ör. 1.06→1.18) + hafif translate. İçe zoom (genel→detay), dışa zoom (detay→bütün), ya da yüze doğru yaklaşım (kapanış). `<Img objectFit:cover>` üstüne `transform:scale()+translate()`, `willChange:transform`.
- **Crossfade geçiş:** sahneleri `XFADE` (~22 frame) kadar üst üste bindir. `<Sequence from={t===0?0:t-XFADE}>` ve her katmanın opacity'sini giriş/çıkışta interpolate et (`opIn=interp(frame,[0,XFADE],[0,1])`, `opOut=interp(frame,[dur-XFADE,dur],[1,0])`, `opacity=min(opIn,opOut)`). İlk sahnede fadeIn kapalı, son sahnede fadeOut kapalı.
- **Hafif atmosfer:** üzerlerine ÇOK hafif vinyet (radyal gradyan dış karartma) + nefes alan ışık parlaması (`sin(frame*0.06)` ile değişen düşük-opacity radyal). Görselin metnini/kalitesini bozma.
- **Görseli ÖNCE upscale et:** kaynak 941×1672 gibi hedeften (1080×1920) küçükse zoom'da bulanıklaşır. `sips --resampleHeight 2304 in.png --out out_hd.png` ile ~1296×2304'e çıkar, Ken Burns'e bol headroom kalsın. PIL `python3 -c` güvenlik taramasına takılır → `sips`/`ffmpeg`/dosyaya yazılı script kullan.
- **Sıralama "timeline'ı tut":** kullanıcı "sadece sırayı koru" derse eski sahne akışını (intro→büyüme→rakamlar→kapanış) aynen uygula; "X sahnesi son olsun" gibi yeniden sıralama isteklerine uy.
- **Ayrı Composition + dosya:** eski üretken videoyu SİLME, yeni `MaarifTenth.tsx` + Root.tsx'e yeni `<Composition id>` ekle. Eski referans korunur.
- **Doğrulama:** her sahne ortasından + bir crossfade anından kare çıkar; vision ile (1) doğru görsel/sıra mı, (2) keskin mi (upscale yeterli mi), (3) geçişte çift-görüntü/sert kesme yok mu sor.
- **Font uyarısı:** hazır görsellerin tipografisi kurumsal Overpass değil (ChatGPT serif font üretir) — kullanıcı "görselleri olduğu gibi kullan" dediyse dokunma ama font tutarsızlığını NOT ET, kurumsal kullanımda gündeme getir.

## the client dashboard kaynakları (referans video klonlama)
- Proje: `/Volumes/YEDEK-AHMET/Antigravity/maarif-dashboard` (React Three Fiber, gerçek 3D küre zaten var).
- Earth texture'lar: `public/earth-nasa-4k.jpg`, `earth-nasa-8k.jpg`, `earth-night.jpg`, `earth-bump.jpg`, `earth-clouds.jpg`, galaksi arkaplanları.
- Logo: `public/maarif-text-logo.png` (amblem + yazı, turkuaz, şeffaf). Amblemi PIL ile kırp+beyaza/turkuaza çevir (amblem-yazı arası boşluktan kes).
- Ülke verisi/koordinat: `src/data/countryData.ts` — 64 ülke (+ Türkiye HQ). nameTr/lat/lng regex ile çekilebilir.
