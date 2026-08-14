# Çok geçişli bloom pipeline (ham WebGPU)

Tek geçişli çizim "düz nokta" verir. Gerçek ışıma için beş geçiş gerekir.
Bu dosya çalışan kurulumu belgeler.

## Geçiş sırası

1. **Sahne → HDR doku** (`rgba16float`, tam çözünürlük, additive blend)
2. **Parlaklık ayıkla** → yarı çözünürlük (`smoothstep(0.52, 1.45, luma)`)
3. **Yatay Gauss** texA → texB
4. **Dikey Gauss** texB → texA
5. **Birleştir** sahne + ışıma → ekran (ACES + vinyet + grain)

Eşik önemli: 0.42 çok düşüktü, her şey ışıyordu. 0.52 ile sadece gerçekten
parlak yerler ışıyor.

## Doku kurulumu (yeniden boyutlanmada tekrar oluşur)

```js
const HDR = "rgba16float";
let texSahne, texA, texB;

function dokuOlustur(){
  canvas.width  = Math.max(1,(canvas.clientWidth *dpr)|0);
  canvas.height = Math.max(1,(canvas.clientHeight*dpr)|0);
  const W = canvas.width, H = canvas.height;
  const hw = Math.max(1, W>>1), hh = Math.max(1, H>>1);

  texSahne?.destroy?.(); texA?.destroy?.(); texB?.destroy?.();

  const kul = GPUTextureUsage.RENDER_ATTACHMENT | GPUTextureUsage.TEXTURE_BINDING;
  texSahne = device.createTexture({ size:[W,H],   format:HDR, usage:kul });
  texA     = device.createTexture({ size:[hw,hh], format:HDR, usage:kul });
  texB     = device.createTexture({ size:[hw,hh], format:HDR, usage:kul });

  // bind group'lar dokulara bagli -> onlar da yeniden kurulmali
  // teksel boyutu bulanik shader'ina uniform olarak gider
  device.queue.writeBuffer(bUniY, 0, new Float32Array([1/hw, 1/hh, 1, 0]));
  device.queue.writeBuffer(bUniD, 0, new Float32Array([1/hw, 1/hh, 0, 1]));
}
addEventListener("resize", dokuOlustur);
```

**Tuzak:** dokuları yeniden oluşturursan bind group'ları da yeniden kurmalısın,
yoksa eski (destroy edilmiş) dokuya bağlı kalırlar.

## Tam ekran üçgen (post geçişleri için)

Quad değil üçgen; daha ucuz, kenar dikişi yok.

```wgsl
struct O { @builtin(position) pos:vec4f, @location(0) uv:vec2f };
@vertex fn vs(@builtin(vertex_index) i:u32) -> O {
  var p = array<vec2f,3>(vec2f(-1.,-1.), vec2f(3.,-1.), vec2f(-1.,3.));
  var o:O;
  o.pos = vec4f(p[i], 0., 1.);
  o.uv  = vec2f((p[i].x+1.)*0.5, 1.0-(p[i].y+1.)*0.5);
  return o;
}
```

## Gauss (9 örnek, doğrusal örneklemeyle genişletilmiş)

```wgsl
struct B { teksel:vec2f, yon:vec2f };
@fragment fn fs(@location(0) uv:vec2f) -> @location(0) vec4f {
  let ag = array<f32,5>(0.2270270, 0.1945946, 0.1216216, 0.0540541, 0.0162162);
  let ad = array<f32,5>(0.0, 1.3846154, 3.2307692, 5.1600000, 7.0900000);
  var toplam = textureSample(kaynak, samp, uv).rgb * ag[0];
  for (var i=1; i<5; i=i+1) {
    let o = b.yon * b.teksel * ad[i];
    toplam = toplam + textureSample(kaynak, samp, uv + o).rgb * ag[i];
    toplam = toplam + textureSample(kaynak, samp, uv - o).rgb * ag[i];
  }
  return vec4f(toplam, 1.0);
}
```

`yon` = `(1,0)` yatay, `(0,1)` dikey. Sampler `linear` olmalı, yoksa
doğrusal örnekleme hilesi çalışmaz.

## Birleştirme + renk yönetimi

```wgsl
var c = textureSample(sahne, samp, uv).rgb;
c = c + textureSample(isima, samp, uv).rgb * 1.05;

// zemin: ayri notr degrade (renkli isiklari arka plana bulastirma)
c = c + mix(vec3f(0.016,0.018,0.026), vec3f(0.030,0.033,0.044), 1.0-uv.y);

// vinyet (en-boy duzeltmeli)
let m = uv - vec2f(0.5);
let r = length(vec2f(m.x*en, m.y));
c = c * (1.0 - 0.42*smoothstep(0.34, 1.05, r));

// ACES
c = (c*(2.51*c + 0.03)) / (c*(2.43*c + 0.59) + 0.14);
c = clamp(c, vec3f(0.0), vec3f(1.0));

// film greni — 0.016 fazlaydi, 0.009 dogru
c = c + (hash1(uv.x*1273.1 + uv.y*7919.7 + u.time*0.61) - 0.5)*0.009;

return vec4f(pow(c, vec3f(0.4545)), 1.0);  // gamma
```

## Additive blend (parçacık geçişi)

```js
blend:{
  color:{ srcFactor:"src-alpha", dstFactor:"one", operation:"add" },
  alpha:{ srcFactor:"one",       dstFactor:"one", operation:"add" },
}
```

## Bloom renk dengesini bozar

Parlak bir renk (lime `#6cf20d` gibi) bloom'da diğerlerini yutar. Mor ve pembe
paylarını artır **ve** parlaklıklarını telafi et:

```wgsl
let h = hash1(fi*7.31);
var c = LIME;
if (h > 0.38) { c = mix(LIME, SARI, 0.75); }
if (h > 0.62) { c = MOR; }
if (h > 0.82) { c = PEMBE; }
let sicak = step(0.62, h);
c = c * (1.0 + sicak*0.55);   // mor/pembe bloom'da kaybolmasin
```
