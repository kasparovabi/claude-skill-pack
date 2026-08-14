# Remotion + @remotion/three: gerçek dünya küresi — çalışan kod ve tuzaklar

Bu dosya, sıfırdan denerken kaybedilen saatleri önler. Sırayla 4 hata yaşandı ve
çözüldü; sırayı koru.

## Hata sırası (gerçek seans)
1. İlk render: küre SİYAH. Sebep: `loader.load()` senkron çağrıldı, texture
   gelmeden render bitti. → delayRender çözümü.
2. İkinci render: TÜM EKRAN düz turkuaz. Sebep: `<Atmosphere>` fresnel mesh
   AdditiveBlending+BackSide, kamera 6 birimde çok yakın → halo ekranı boğdu.
   → atmosferi geçici kaldır, kamerayı 8.5'e çek.
3. Üçüncü render: arka plan gradyan+yıldız GÜZEL ama küre yok, sadece bir marker
   noktası görünüyor. Sebep: ShaderMaterial veya texture decode şüphesi.
   → MeshBasicMaterial/MeshStandardMaterial ile izole et, texture boyutunu düşür.
4. (Devam) 8K texture (6.5MB) decode ağır olabilir → 4K'ya geç. earth-nasa-4k.jpg
   beklenenden büyük çıkabilir (27MB = bozuk), dosya boyutunu `ls -la` ile DOĞRULA.
   Sağlam `earth-4k.jpg` (~1.4MB) ile çalıştı. Texture decode olmazsa ÖNCE dosya
   boyutuna bak, makul (<5MB) sağlam bir alternatif dene.
5. (ASIL KÖK SEBEP) Küre HÂLÂ yok, sadece bir marker görünüyor. Gerçek sebep:
   texture `useState`+`useEffect` ThreeCanvas'ın İÇİNDEKİ `EarthMesh`'te
   yükleniyordu. Remotion her kareyi izole (fresh) render ettiği için ThreeCanvas
   içindeki setState→re-render o kare için güvenilmez. → texture yüklemeyi
   ThreeCanvas DIŞINA, parent `Globe` component'ine taşı; hazır olunca texture'ı
   PROP olarak `EarthMesh`'e geçir. "Doğru desen" bölümü bu düzeltilmiş haldir.

## Texture yükleme — DOĞRU desen (ThreeCanvas DIŞINDA, parent'ta)
KRİTİK: texture'ı ThreeCanvas içindeki mesh'te DEĞİL, Canvas'ı saran PARENT
component'te yükle. Canvas içinde useState frame-izole render'da güvenilmez
(Hata 5). Parent hazır olunca Canvas'ı render et, texture'ı prop geç.
```tsx
import { delayRender, continueRender, staticFile } from 'remotion';
import { useState, useEffect, useMemo } from 'react';
import * as THREE from 'three';

// İÇERİDE: texture PROP olarak gelir, yükleme YOK.
function EarthMesh({ rotation, dayTex }: { rotation: number; dayTex: THREE.Texture }) {
  const mat = useMemo(() => new THREE.MeshBasicMaterial({ map: dayTex }), [dayTex]);
  return (
    <mesh rotation={[0, rotation, 0]} material={mat}>
      <sphereGeometry args={[2, 96, 96]} />
    </mesh>
  );
}

// DIŞARIDA (parent): texture'ı delayRender ile yükle, hazır olunca Canvas'ı bas.
export const Globe = ({ width, height, markers, revealCount, rotation }) => {
  const [dayTex, setDayTex] = useState<THREE.Texture | null>(null);
  const [handle] = useState(() => delayRender('earth-texture'));
  useEffect(() => {
    new THREE.TextureLoader().load(staticFile('earth.jpg'), (tex) => {
      tex.colorSpace = THREE.SRGBColorSpace;
      setDayTex(tex);
      continueRender(handle);   // ← çağrılmazsa render asılır
    });
  }, []);
  if (!dayTex) return null;     // texture gelmeden Canvas YOK
  return (
    <ThreeCanvas /* ...transparent ayarları aşağıda... */>
      <EarthMesh rotation={rotation} dayTex={dayTex} />
      {/* markerlar */}
    </ThreeCanvas>
  );
};
```
MeshStandardMaterial + emissiveMap (gece ışıkları, emissiveIntensity~0.35) de
kullanılabilir; ama ÖNCE MeshBasicMaterial ile küre GELDİĞİNİ doğrula, sonra
ışıklı materyale geç (izolasyon prensibi).

## NİHAİ KALİTE: ışıklı küre (MeshPhong + gece/bulut/bump)
MeshBasicMaterial DÜZ ve ucuz durur ("sosyal medya için yeterli kalitede değil"
şikayeti tam buradan gelir — gerçek seansta yaşandı). Gerçekçi NASA dünyası için
debug bittikten sonra MeshPhongMaterial'a geç ve gece ışıkları + bulut katmanı
ekle. Tüm texture'ları (gündüz, gece, bump, bulut) PARENT'ta tek `Promise.all`
ile delayRender altında yükle, prop geç.
```tsx
type Tex = { day: THREE.Texture; night: THREE.Texture; bump: THREE.Texture; clouds: THREE.Texture };

function EarthMesh({ rotation, tex }: { rotation: number; tex: Tex }) {
  const mat = useMemo(() => new THREE.MeshPhongMaterial({
    map: tex.day,
    bumpMap: tex.bump, bumpScale: 0.04,
    emissiveMap: tex.night, emissive: new THREE.Color(0xffe6b0), emissiveIntensity: 0.55, // gece şehir ışıkları
    specular: new THREE.Color(0x335566), shininess: 9,                                     // okyanus parlaması
  }), [tex]);
  return <mesh rotation={[0, rotation, 0]} material={mat}><sphereGeometry args={[2, 128, 128]} /></mesh>;
}

// Bulut: ayrı küre, kürenin biraz farklı hızında döner, alphaMap=bulut texture
function Clouds({ rotation, tex }: { rotation: number; tex: THREE.Texture }) {
  const mat = useMemo(() => new THREE.MeshPhongMaterial({
    map: tex, alphaMap: tex, transparent: true, opacity: 0.42, depthWrite: false,
  }), [tex]);
  return <mesh rotation={[0, rotation, 0]} material={mat}><sphereGeometry args={[2.03, 96, 96]} /></mesh>;
}

// Işıklandırma: DÜŞÜK ambient + GÜÇLÜ yandan directional = doğal terminatör
// + çok hafif ters dolgu (gece tarafı tam siyah olmasın)
<ambientLight intensity={0.28} />
<directionalLight position={[6, 2.5, 5]} intensity={1.55} color={0xfff4e0} />
<directionalLight position={[-5, -1, -3]} intensity={0.18} color={0x2a6b8a} />
<EarthMesh rotation={rotation} tex={tex} />
<Clouds rotation={(frame/fps)*0.16 + 3.55} tex={tex.clouds} />  {/* bulut biraz daha hızlı */}
```
Parent texture yükleme (4 texture, hepsi hazır olunca tek continueRender):
```tsx
const [tex, setTex] = useState<Tex | null>(null);
const [handle] = useState(() => delayRender('earth-textures'));
useEffect(() => {
  const loader = new THREE.TextureLoader();
  const load = (f: string) => new Promise<THREE.Texture>((res) => loader.load(staticFile(f), res));
  Promise.all([load('earth.jpg'), load('earth-night.jpg'), load('earth-bump.jpg'), load('earth-clouds.jpg')])
    .then(([day, night, bump, clouds]) => {
      [day, night, clouds].forEach(t => (t.colorSpace = THREE.SRGBColorSpace));
      setTex({ day, night, bump, clouds }); continueRender(handle);
    });
}, []);
if (!tex) return null;
```
the client dashboard'da bu texture'lar zaten var (earth-night.jpg, earth-clouds.jpg,
earth-bump.jpg) — kopyalaman yeter, üretmen gerekmez.

## ThreeCanvas — arka planı örtmesin
```tsx
<ThreeCanvas
  width={width} height={height}
  style={{ background: 'transparent' }}
  camera={{ position: [0, 0.2, 11], fov: 30 }}   // bkz. kamera/rotasyon kalibrasyonu
  gl={{ antialias: true, alpha: true, premultipliedAlpha: false }}
  onCreated={({ gl }) => { gl.setClearColor(0x000000, 0); }}
>
  <ambientLight intensity={0.8} />
  <directionalLight position={[5, 2, 4]} intensity={0.9} />
  <EarthMesh rotation={rotation} dayTex={dayTex} />
  <Markers markers={markers} rotation={rotation} revealCount={revealCount} />
</ThreeCanvas>
```
Arka plan (gradyan + sabit-seed yıldız) ThreeCanvas'ın ALTINDA ayrı bir
`<AbsoluteFill>` CSS katmanı olarak durur. Canvas şeffaf olunca görünür.

## Kamera ve rotasyon kalibrasyonu (deneyerek bulundu — başlangıç değerleri)
Küre boyutu ve hangi kıtanın merkeze geleceği el yordamıyla kalibre edilir;
tek-kare render ile birkaç turda oturur. Bu oturumda işe yarayan değerler:
- **Kamera mesafesi**: `position:[0,0.2,11], fov:30`. 8.5'te küre ekrandan
  TAŞIYORDU; 11'e çekince çevresinde dengeli boşluk kaldı, hem 9:16 hem 1:1'de
  düzgün. Küre `sphereGeometry args={[2,...]}` (yarıçap 2).
- **Rotasyon offset**: `rotation = (frame/fps)*0.13 + 3.55`. Bu offset Afrika +
  Avrupa + Ortadoğu + Asya'yı (the client'in faaliyet yoğunluğu, markerların çoğu)
  ekran merkezine getirir. Kalibrasyon mantığı: `-1.15` → Afrika sağ kenarda,
  `+1.7` → Asya-Pasifik önde (boş okyanus, marker yok), `+3.55` → Afrika tam
  merkez. Yeni bir bölge istenirse offset'i tek-kare render ile ayarla.
- Hız `0.13` yavaş/zarif. Çok hızlı dönüş kurumsal videoda ucuz durur.

## lat/lng → 3D küre yüzeyi (Globe.tsx ile birebir formül)
```tsx
function latLngToVec3(lat: number, lng: number, r: number) {
  const phi = (90 - lat) * (Math.PI/180);
  const theta = (lng + 180) * (Math.PI/180);
  return new THREE.Vector3(
    -(r*Math.sin(phi)*Math.cos(theta)),
    r*Math.cos(phi),
    r*Math.sin(phi)*Math.sin(theta),
  );
}
```
Marker'ı küreden hafif dışta konumla (r=2.02, küre r=2). Ön/arka yüz testi:
rotasyon matrisi uygula, dünya-uzayı normalinin `.z > -0.1` ise göster.

## Atmosfer halosu (en sonda, kontrollü ekle)
BackSide + AdditiveBlending fresnel mesh, küre r'sinden ~%9 büyük (r=2.18).
Fresnel: `pow(1.0 - max(dot(normal,viewDir),0.0), 2.6)` — üs ≥2.6 tut, opacity
≤0.9 ve kenar dışında hızla sönsün. Düşük üs = tüm ekran boyanır.

## Marker kademeli belirme — sayaçla BİREBİR senkron (düzeltilmiş)
DİKKAT — eski yanlış kalıp: pin reveal'ı `interpolate(frame,[30,175],...)` LİNEER,
sayaç ise `spring` idi. İkisi aynı frame'de başlayıp bitse de ORTADA ayrışır
(sayaç 40 derken ekranda 50 pin). Kullanıcı "aynı anda gelmiyor/bitmiyor" der.
Bu gerçek bir bug olarak yaşandı ve düzeltildi.

DOĞRU: pin reveal'ı sayacın TIPATIP aynı spring'iyle hesapla. Counter
`{startFrame:30, durationInFrames:145, damping:20, stiffness:70, mass:1}`
kullanıyorsa:
```tsx
const countSpr = spring({
  frame: frame - 30,
  fps,
  config: { damping: 20, stiffness: 70, mass: 1 },
  durationInFrames: 145,
});
const reveal = Math.round(
  interpolate(countSpr, [0, 1], [0, 64], { extrapolateRight: 'clamp' })
);
// Markers içinde: if (i >= revealCount) return null;
```
Sayaç (Counter) ve pin reveal artık aynı eğride → tam senkron başlar/biter.
Doğrulama: gerçek videodan 2 kare (orta+son) çıkar, vision ile "sayaç kaç + kaç
görünür pin" sor; eşleşmeli (küre arkasındaki pinler gizliyse ekran < sayaç olur,
o normal — kriter reveal sayısı = sayaç değeri).

## Hızlı doğrulama döngüsü
Tam video render etmeden önce `npx remotion still ... --frame=N` ile o sahnenin
ortasından tek kare çıkar (küre sahnesi ~frame 180), vision ile bak. Tam render
dakikalar sürer; tek kare saniyeler.
