# Multi-pass bloom in raw WebGPU

Five-pass chain that turns a flat additive-blended particle scene into one that
actually radiates light. No engine, no post-processing library.

```
1. scene      → texSahne  (rgba16float, full res)   particles, additive blend
2. bright     → texA      (rgba16float, half res)   extract hot pixels
3. blur horiz → texB      (half res)                separable Gaussian
4. blur vert  → texA      (half res)                separable Gaussian
5. composite  → swapchain (bgra8unorm)              scene + bloom, ACES, grain
```

Half resolution for passes 2–4 is free quality: the buffer is blurred anyway, so
the detail loss is invisible while the fill cost drops 4×.

## Why an HDR intermediate

The swapchain format (`bgra8unorm`) clamps at 1.0, so additive particle overlap
saturates to white and the bright-pass has nothing left to threshold on. Render
the scene to `rgba16float` instead and values above 1.0 survive into the extract
pass, which is what makes bloom look like light rather than a blur filter.

```js
const HDR = "rgba16float";
const kul = GPUTextureUsage.RENDER_ATTACHMENT | GPUTextureUsage.TEXTURE_BINDING;
texSahne = device.createTexture({ size:[W,H],   format:HDR, usage:kul });
texA     = device.createTexture({ size:[hw,hh], format:HDR, usage:kul });
texB     = device.createTexture({ size:[hw,hh], format:HDR, usage:kul });
```

Only the final composite pipeline targets the swapchain `format`; passes 1–4 all
target `HDR`. Mismatching a pipeline's target format against its attachment is
the most common hard error here.

## Fullscreen triangle for post passes

One triangle, no vertex buffer, no quad seam.

```wgsl
struct O { @builtin(position) pos:vec4f, @location(0) uv:vec2f };
@vertex fn vs(@builtin(vertex_index) i:u32) -> O {
  var p = array<vec2f,3>(vec2f(-1.,-1.), vec2f(3.,-1.), vec2f(-1.,3.));
  var o:O;
  o.pos = vec4f(p[i], 0., 1.);
  o.uv  = vec2f((p[i].x+1.)*0.5, 1.0-(p[i].y+1.)*0.5);   // note the Y flip
  return o;
}
```

The Y flip in `uv` matters: WebGPU's clip space is Y-up while texture sampling is
Y-down. Miss it and the bloom lands mirrored against the scene — subtle enough to
survive a careless glance, obvious once the composition is asymmetric.

## Pass 2 — bright extract

```wgsl
@group(0) @binding(0) var samp : sampler;
@group(0) @binding(1) var kaynak : texture_2d<f32>;
@fragment fn fs(@location(0) uv:vec2f) -> @location(0) vec4f {
  let c = textureSample(kaynak, samp, uv).rgb;
  let l = dot(c, vec3f(0.2126, 0.7152, 0.0722));   // Rec.709 luma
  let k = smoothstep(0.52, 1.45, l);               // soft knee
  return vec4f(c * k, 1.0);
}
```

Threshold is a tuning knob, not a constant. Too low (0.42) and the whole frame
hazes over; too high and only white cores bloom. Tune it *together* with palette
brightness — see the colour section in SKILL.md.

## Pass 3/4 — separable Gaussian

Two 1-D passes instead of one 2-D kernel: 9 taps each instead of 81. The offsets
below exploit linear filtering to cover a wider kernel per tap.

```wgsl
struct B { teksel:vec2f, yon:vec2f };
@group(0) @binding(2) var<uniform> b : B;

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

Two uniform buffers, one per direction, written once at resize:

```js
device.queue.writeBuffer(bUniY, 0, new Float32Array([1/hw, 1/hh, 1, 0]));
device.queue.writeBuffer(bUniD, 0, new Float32Array([1/hw, 1/hh, 0, 1]));
```

Texel size is that of the **half-res** buffer, not the canvas. Using full-res
texel size here produces a blur so tight it looks like a rendering artefact.

Sampler must be `linear` with `clamp-to-edge`; `repeat` wraps the blur around
frame edges and smears the opposite side into view.

## Pass 5 — composite

```wgsl
var c = textureSample(sahne, samp, uv).rgb;
let b = textureSample(isima, samp, uv).rgb;
c = c + b * 1.05;

c = c + mix(vec3f(0.016,0.018,0.026), vec3f(0.030,0.033,0.044), 1.0-uv.y);

let m = uv - vec2f(0.5, 0.5);
let en = u.res.x / max(u.res.y, 1.0);
let r = length(vec2f(m.x*en, m.y));
c = c * (1.0 - 0.42*smoothstep(0.34, 1.05, r));      // aspect-correct vignette

c = (c*(2.51*c + 0.03)) / (c*(2.43*c + 0.59) + 0.14); // ACES approx
c = clamp(c, vec3f(0.0), vec3f(1.0));

let g = hash1(uv.x*1273.1 + uv.y*7919.7 + u.time*0.61);
c = c + (g - 0.5)*0.009;                              // grain

return vec4f(pow(c, vec3f(0.4545)), 1.0);             // gamma
```

Multiply the vignette's X by aspect ratio or it turns elliptical on wide
viewports.

## Resize: textures AND bind groups

The trap. Bind groups hold texture *views*; recreating a texture without
recreating every bind group that references it leaves stale views bound, and the
frame renders from destroyed resources. Rebuild both together in one function
and call it on `resize`:

```js
function dokuOlustur(){
  canvas.width  = Math.max(1,(canvas.clientWidth *dpr)|0);
  canvas.height = Math.max(1,(canvas.clientHeight*dpr)|0);
  const W = canvas.width, H = canvas.height;
  const hw = Math.max(1, W>>1), hh = Math.max(1, H>>1);

  texSahne?.destroy?.(); texA?.destroy?.(); texB?.destroy?.();
  // ... recreate all three textures ...
  // ... recreate bgParlak, bgBulY, bgBulD, bgBirlestir ...
  // ... rewrite the two blur uniform buffers with new texel sizes ...
}
```

Clamp every dimension with `Math.max(1, …)`. A collapsed or hidden container
yields a zero-size texture and the device throws on creation.

## One command encoder, five render passes

All five passes go in a single encoder and a single `submit` — no per-pass
submit, no fences.

```js
const enc = device.createCommandEncoder();
let p = enc.beginRenderPass({ colorAttachments:[{ view: texSahne.createView(),
  clearValue:{r:0,g:0,b:0,a:1}, loadOp:"clear", storeOp:"store" }]});
p.setPipeline(pParcacik); p.setBindGroup(0,bgParcacik); p.draw(6,N); p.end();
// ... passes 2..5 identically, last one targeting ctx.getCurrentTexture() ...
device.queue.submit([enc.finish()]);
```

## Cost

On an M1 Pro at 1440×810 this runs comfortably at display refresh with 2800
instanced particles. The bloom chain is the dominant cost, not the particles.

Tuning order when it needs to be cheaper, least visual damage first:

1. blur buffers to quarter res (`W>>2`) instead of half
2. drop to a single blur direction (directional glow, still reads as light)
3. clamp `dpr` to 1
4. only then reduce particle count
