---
name: webgpu-browser-visuals
description: "Use when building WebGPU visuals with headless render QA."
---

# WebGPU Browser Visuals

Build GPU-rendered visuals that ship inside a real website: hero backgrounds,
particle systems, shader demos, interactive canvases. Raw WebGPU + WGSL, no
engine dependency, verified by headless render before delivery.

Load when the ask is a browser visual with real GPU work behind it: "hero
animasyonu", "WebGPU demo", "shader arka plan", "parçacık animasyonu",
"landing page'e görsel bir şey", or when porting a shader demo into a
production React/Next app.

## Rule 0 — the visual must MEAN something

**This is the failure that gets rejected, not the technical one.**

A beautiful abstract render that could sit on any startup's landing page is a
failure even when the shading is flawless. Kasparov's exact verdict on a
polished liquid-metal hero: *"Bu sadece güzel bir 3d animasyon, herhangi bir
anlamı ve bağlamı yok."*

Before writing a line of WGSL, answer: **what does this shape say about THIS
organisation?** Anchor the visual in something already in the repo:

- the site's own hero headline (read `messages/tr.json` → `landing.heroHeadline`)
- the brand mark / logo / emblem in `public/brand/`
- the product's actual thesis

Worked example: headline *"Maarifle Her Yerde, Hep Birlikte"* → particles
scattered across the world (her yerde) converge into the emblem's Seljuk motif
(hep birlikte). The shape is extracted from the real logo PNG, not invented.
Same tech budget as the meaningless version, completely different reception.

Corollary: **do not propose data-driven visuals for a product with no data.**
An alumni-density globe is worthless on a site with zero registered alumni. When
the database is empty, the visual must be self-contained — brand-derived, not
record-derived.

### Read the actual repo before proposing anything

Rule 0 is unsatisfiable without the real codebase, and *"bizim şu proje"* rarely
identifies it. Two rounds of suggestions were wasted on the wrong repo here:
a similarly-named internal AI platform, then a corporate-comms platform whose
own README said in as many words that the alumni portal is a **separate**
product. The real path only arrived because the user supplied it.

So: locate and read first, propose second. What to look at, in order —

- `CLAUDE.md` / `README.md` / `HANDOFF.md` — often state outright what the repo
  is *not*, which is the fastest disambiguator
- route directory listing — reveals which modules actually exist
- `messages/*.json` — the real user-facing copy the visual must serve
- existing component folders — check for what is already built before pitching it

That last one saves the most embarrassment: this site already shipped a full
gamification layer (XP bar, badges, leaderboard, streak counter, confetti).
Proposing "let's add badges" would have been noise. Also note the stack from
`package.json` — Leaflet-based 2-D map, no three.js — because it bounds what
"add a visual" actually costs.

When the repo genuinely cannot be found, ask for the path in one line rather
than guessing at a plausible-looking neighbour.

## Rule 0.5 — "X parçacıklı olsun" has THREE layers, ship all three

The most expensive misread in this skill's history. Kasparov asked for a voltage
trace to be made of particles; it took **three correction rounds** because each
delivery satisfied only one layer.

| Round | Delivered | His correction |
|---|---|---|
| 1 | Particle field rendered *behind* the existing 2-D curve | *"asıl o çizginin parçacıklardan oluşmasını istiyorum"* |
| 2 | Particles settle onto the curve shape, 2-D stroke deleted | *"parçacıklar o çizgiyle interaktif değil"* |
| 3 | Pointer repel added | *"normalde düz aksın, scrolladıkça peak ve diplere göre şekli değişsin"* |

The three layers, in the order they will be demanded anyway:

**1. The thing ITSELF becomes particles — delete the old renderer.** Not a layer
behind it, not a layer near it. If the old 2-D stroke still draws, the request is
unsatisfied no matter how good the field looks. Keep the old path *only* as the
no-WebGPU fallback, gated on a flag set after the first successful GPU frame:

```js
var gpuLive = false;                    // set true right after queue.submit()
if (!gpuLive) { /* 2-D stroke fallback */ }
```

**2. It responds to the pointer.** A shape that merely *is* particles reads as a
picture of a fluid. Push particles out of a radius and let the existing settling
force pull them back — about 10 lines in the compute pass:

```wgsl
if (u.mAct > 0.5) {
  let d = p.pos - u.mouse; let r = length(d); let R = 128.0;
  if (r < R && r > 0.001) {
    let f = 1.0 - r / R;
    p.vel = p.vel + normalize(d) * f * f * 2600.0 * u.dt;
  }
}
```

**3. The shape FORMS progressively — it is not pre-drawn.** The layer missed most
often. If the finished shape exists on frame one and scrolling just walks a
playhead across it, the user is watching a recording. The field must start **flat
and neutral**, and scrolling must *write* the shape. Blend each particle's target
between a flat baseline and its real value, weighted by how far the playhead has
passed **that particle's own x**:

```wgsl
let form   = 1.0 - smoothstep(u.prog, u.prog + 0.085, tx);
let vloc   = mix(vFlat, dataFn(tx), form);
let spread = mix(spreadFlat, spreadFormed, form);
```

Drive speed, chaos, colour *and* brightness off the same `form` term, or the
unformed region just looks like the formed one with the geometry deleted.

#### Get the window's direction right, or layer 3 silently does nothing

The formula above is the *corrected* one. The first attempt here was
`smoothstep(u.prog + 0.02, u.prog - 0.19, tx)`, which starts forming **0.19
before** the playhead. It looked plausible and rendered a convincing progressive
build, so it survived review — until the user pointed at the screen: *"voltaj
baya aşağıdayken partiküller hala yukarıda ve düz akıyor"*. The readout sat on
the real curve while the cloud stayed flat and high.

Correct rule: **everything behind the playhead is fully formed, only ahead of it
is flat.** The transition is a short ramp *forward* from `prog`, not a window
straddling it.

The reason this is worth a named subsection: the bug is invisible when the data
function is near its baseline (the early, healthy part of the trace) and only
shows where the data actually deviates — which is the one region the whole
visual exists to show.

### Debug shader maths in Python, not by tweaking WGSL

Neither layer of the `form` bug was findable by staring at the canvas: the 2-D
readout was right, the particle field was right, and they disagreed. Fiddling
with colours and thresholds would have burned rounds. Porting the same
arithmetic to Python and printing a table found it in one shot:

```python
def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)

prog = 0.50                                        # where the playhead sits
for tx in [0.20, 0.35, 0.42, 0.46, 0.50, 0.55]:
    f = smoothstep(prog + 0.02, prog - 0.19, tx)   # the window under test
    v = 3.3 * (1 - f) + dataFn(tx) * f             # what actually gets drawn
    print(tx, round(f, 3), round(v, 2))
```

Output named the cause immediately: at `tx = prog` the weight was **0.025**, so
the value being drawn there was the flat baseline, not the fault. Every dip was
permanently parked in the not-yet-formed zone.

Generalises to any shader parameter behaving unexpectedly: **run the same
arithmetic in the host language and print a table across the input range before
touching WGSL.** Reversed `smoothstep` edges, normalised coordinates and
off-by-a-window blends are effectively impossible to eyeball on a moving canvas
and trivial to spot in six rows of numbers.

### The enabling move: port the data function into WGSL

Layers 1 and 3 are both unreachable while the shape lives in JS. Move the
function itself into the shader so **every particle evaluates it at its own x**:

```wgsl
fn voltsw(t: f32) -> f32 { /* same piecewise function as the JS version */ }
fn tOfX(x: f32, u: U) -> f32 { return clamp((x - u.padX) / span, 0.0, 1.0); }
fn yOfV(v: f32, u: U) -> f32 { return u.gbot - (v / VMAX) * (u.gbot - u.gtop); }
```

Pass the plot geometry (`padX`, `top`, `bot`) in the uniform in **device pixels**
so the shader rebuilds the same coordinate space the 2-D layer used. Before this,
the uniform carried a single scalar (the value under the playhead) and every
particle collapsed into one flat horizontal band — exactly the round-1 failure.

Diagnostic question that generalises to any chart, waveform or path:
**"can a particle at x compute its own target, or is it being handed one global
value?"** The second answer guarantees a decorative layer.

### Growing the uniform is where this silently corrupts

Each layer added fields (`padX/gtop/gbot`, then `mouse/mAct`), so the uniform
went 8 → 12 → 16 floats. **`createBuffer({size})` must grow with it** (48 → 64 →
80 bytes, 16-byte aligned) and the `Float32Array` must be reallocated. Writing 16
floats into a 48-byte buffer does not throw a friendly error; it corrupts the
tail fields, so the pointer looks dead or the geometry lands in the wrong place
while the shader "works". Update struct, buffer size, and typed array together.

### Stacked dimming factors multiply to near-invisible

Adding depth, reveal and formation terms each introduced a brightness multiplier.
Independently sane (`rev 0.30`, `form 0.55`, `dim 0.44`) they multiplied to
**0.07** and the first render looked like a blank canvas — read as a broken page,
not a subtle one. When several passes each scale alpha or colour, multiply the
floors out on paper before rendering, and raise the floors rather than the peaks.

## Effects must be CONDITIONAL to stay meaningful

Rule 0 says the visual must mean something. The same test applies to every
polish technique you bolt on: an effect that runs constantly is decoration, the
same effect gated on a state change is information.

Worked example, a fault trace. Bloom running always = "pretty glowing page".
Bloom gated on the voltage crossing its brownout threshold = *"this is the
moment the chip died"*. One line of difference, completely different reception:

```wgsl
let glow = smoothstep(0.62, 0.20, hv) * form;   // 0 while healthy
let halo = pow(d, 0.85) * glow * 0.62;          // radiates only at collapse
```

Apply the same gating to threshold lines. A labelled axis line is furniture;
a line that *throws* particles as they cross it makes the number an event:

```wgsl
if (form > 0.35 && ((before - yThr) * (after - yThr)) < 0.0) {
  p.vel.y = p.vel.y + (h11(p.seed * 5.7 + u.time) - 0.5) * 620.0;
}
```

Before adding any effect, ask **"what state change turns this on?"** If the
answer is "nothing, it's always on", it is decoration and Rule 0 will reject it.

### Substituting a cheaper technique is fine — say so out loud

The five-pass bloom chain was overkill for a scene whose particles already draw
additively, and a full HDR chain would also have complicated the 2-D fallback.
A fragment-side expanding halo bought a comparable read at roughly a third of the
cost. That is a legitimate call, but **name the substitution when reporting**:
say "expanding halo instead of the multi-pass chain, and here is why", not
"bloom eklendi". Silently shipping the cheap version as the expensive one is how
a technical claim becomes untrue.

## Rule 1 — deterministic params, or you cannot verify anything

Drive time and every animation parameter from the query string, with live
values as the fallback. This single decision buys reproducible screenshots,
frame-by-frame video export, and A/B comparison for free.

```js
const qs = new URLSearchParams(location.search);
const FT = qs.get("t");            // frozen time
const FK = qs.get("k");            // custom param (e.g. convergence 0..1)
const FM = qs.get("m");            // "x,y" pointer override

const t = FT !== null ? parseFloat(FT) : (performance.now() - t0) / 1000;
```

Park the pointer off-screen for clean captures: `&m=9,9`.

Also set a render sentinel so an automated check can distinguish "rendered" from
"blank canvas":

```js
frames++; if (frames === 3) { window.__R = "RENDER_OK"; }
```

## Rule 2 — the headless verify loop

Never hand a GPU visual over unseen. Render → screenshot → look at it → fix.

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --enable-unsafe-webgpu \
  --enable-features=Vulkan,WebGPU --use-angle=metal \
  --screenshot=/tmp/out.png --window-size=1280,720 \
  --virtual-time-budget=8000 \
  "http://127.0.0.1:8911/v1.html?t=6.0&k=1.0&m=9,9"
```

Then inspect the PNG with `vision_analyze` and ask a *specific* question
("is the mass centred?", "is the background clean?"), not "is it good?".

Prove the pipeline works before debugging your art: render a flat green triangle
first. If that screenshots correctly, WebGPU is fine and every later problem is
in your own shader.

**Anything that `fetch()`es needs a real HTTP origin** — `file://` blocks it.
Serve the folder and hit `127.0.0.1`:

```bash
cd /tmp/scene && python3 -m http.server 8911   # background=true
```

**Composite several states into one sheet** to judge a whole animation in a
single look — e.g. `k=0.0 / 0.5 / 1.0` stacked vertically with PIL. Far more
informative than three separate screenshots.

### Testing "is it actually animating?" — the harness invalidates the test

Rule 1's frozen-time params make every *appearance* check reproducible, and for
exactly that reason they make every *motion* check meaningless. Passing `?t=`
drives time from outside the page, so two captures differ even when the page's
own `requestAnimationFrame` loop is dead. That false pass shipped a frozen hero
here — the diff was a healthy 10.0/255 while the animation was completely stopped.

To test motion, pass **no parameters at all** and vary only Chrome's
`--virtual-time-budget`, so the page's own clock is the sole variable:

```python
kare_al("/tmp/a.png", 2500)          # no ?t=, no ?k=
kare_al("/tmp/b.png", 7000)
# mean abs diff > ~0.6/255 → moving; ~0.2 → static
```

Run it across every branch that can gate the loop, not just the default one —
`--force-prefers-reduced-motion` is the flag that reproduces the Windows case
above, and it was the branch that was broken while the default branch passed.

Test interaction the same way, with the *opposite* setup: freeze time (`?t=`)
and vary **only** the pointer (`?m=9,9` vs `?m=0.42,0.0`) so any diff is
attributable to the cursor field and nothing else.

Generalises past WebGPU: whenever a determinism harness overrides the very
quantity under test, the test measures the harness. Vary the real input.

## Rule 3 — video export is the same loop in a for-loop

Screenshot per frame at a fixed timestep, then encode. Budget ~1.5–2 s per frame
of Chrome startup, so a 9 s clip at 24 fps ≈ 216 launches ≈ 6–8 minutes. Run it
`background=true` and do other work meanwhile.

```python
for i in range(N):
    t = 2.0 + i / FPS
    k = egri(i / N)                      # scripted animation curve
    subprocess.run([CHROME, "--headless=new", ..., f"{URL}?t={t}&k={k}"])
```

```bash
ffmpeg -framerate 24 -pattern_type glob -i 'frames/*.png' \
  -c:v libx264 -preset slow -crf 19 -pix_fmt yuv420p out.mp4 -y
```

Sanity-check the encode by sampling frames back out (`fps=1/1.5`) into a contact
sheet and vision-checking that the motion actually reads.

## Particle systems

Store per-particle data in a `storage` buffer of `vec4f` and draw instanced
quads — 6 vertices, N instances. This is *far* cheaper than fullscreen
raymarching and is the right default for anything shipping to mobile.

```js
pass.draw(6, N);   // 6 verts per quad, N instances
```

Additive blending gives cheap glow with no extra pass — the right default for a
first cut:

```js
blend: {
  color: { srcFactor: "src-alpha", dstFactor: "one", operation: "add" },
  alpha: { srcFactor: "one",       dstFactor: "one", operation: "add" },
}
```

It is *not* the premium look. When the visual is the hero of a landing page,
go straight to the multi-pass pipeline below — see "Premium pass".

Per-particle stagger makes convergence organic instead of mechanical:

```wgsl
let gecikme = hash1(fi*1.7)*0.35;
let kk = clamp((k - gecikme) / (1.0 - gecikme + 0.0001), 0.0, 1.0);
let e  = kk*kk*(3.0 - 2.0*kk);          // smoothstep
```

### Distribution maths — two bugs that look like art bugs

**Independent sequences for angle and radius.** Deriving both from the same
sequence correlates them and renders a *spiral*, which reads as a deliberate
(wrong) design choice rather than a bug:

```js
// WRONG — angle and radius correlated, produces a spiral
const aci  = (i * 2.399963) % (Math.PI * 2);
const yari = 1.62 * Math.sqrt((i * 0.61803) % 1);

// RIGHT — two independent hashes
const r1 = Math.abs(Math.sin(i * 12.9898) * 43758.5453) % 1;
const r2 = Math.abs(Math.sin(i * 78.2330) * 12345.6789) % 1;
const aci  = r1 * Math.PI * 2;
const yari = 1.68 * Math.sqrt(r2);
```

**`sqrt()` for area-uniform discs.** A linear radius crowds the rim and renders
a ring/donut, not a cloud. `Math.sqrt(random)` fixes it.

### Following a steep feature needs a PULL FLOOR, not less scatter

Symptom, reported as *"hala çizginin indiği yere kadar inmiyor parçacıklar"*:
the cloud tracks the shape while it is shallow, then fails to reach the bottom
of a sharp drop. The instinct is to widen the scatter so the cloud "covers" the
dip. That is backwards and makes it worse — a wide scatter turns the feature
into fog and loses the shape entirely.

The real cause is the settling coefficient. If `pull` is driven by the same
health/quality term as everything else, it bottoms out exactly where the feature
is steepest, so particles are swept past horizontally before they can descend:

```wgsl
// WRONG — pull collapses to 0.10 in the region that needs it most
let spread = plot * mix(0.30, 0.020, health);
let pull   = (home - p.pos.y) * mix(0.10, 0.72, health);

// RIGHT — floor the pull, cap the scatter
let spread = mix(sprFlat, plot * mix(0.115, 0.020, health), form);
let pull   = (home - p.pos.y) * mix(0.06, mix(0.42, 0.80, health), form);
```

Rule of thumb: **vertical travel is bought by the pull floor; shape legibility
is bought by the scatter cap.** They are separate knobs and they move in
opposite directions.

### Logo → point cloud

Turn a brand mark into particle targets by sampling its PNG. Mask to the emblem's
inner radius to drop outer rings and wordmarks, sample on a stride, normalise to
`[-1,1]`, then sort by distance from centre so convergence reads inside-out.
Preview the cloud with PIL and vision-check it *before* wiring the shader — a
wrong radius multiplier is trivial to fix at this stage and expensive later.
Ship the result as a small JSON in `public/brand/`; keep the extraction script
alongside so the cloud can be regenerated when the logo changes.

Full extraction recipe: `references/logo-to-point-cloud.md`.

## Premium pass — what separates "fine" from "shipped"

Assume the first cut will be judged as not good enough. On this project the
verdict after a clean single-pass particle render was simply *"bu animasyonu çok
daha kaliteli hale getirebilir misin"*. Everything below is what closed that gap,
and it is cheap enough to build in from the start for a hero-slot visual.

Five techniques, roughly in order of visual payoff per unit of work:

**1. Real bloom via a multi-pass chain.** Additive blending fakes glow; a bright-
pass + separable blur actually radiates. Five passes:

```
scene → HDR texture (rgba16float, full res)
      → bright-pass extract (half res)
      → Gaussian blur horizontal (half res)
      → Gaussian blur vertical   (half res)
      → composite: scene + bloom, ACES, vignette, grain → swapchain
```

Half-res for the blur chain is free quality — nobody sees the resolution loss in
a blurred buffer. Full recipe with WGSL and the resize/rebind dance:
`references/multipass-bloom-webgpu.md`.

**2. Depth.** Scatter particles on Z, rotate the whole cloud slowly on Y, and
divide by distance. A flat emblem becomes an object sitting in space:

```wgsl
let w = max(kamZ - q.z, 0.35);
let olcekP = kamZ / w;                    // perspective divide
```

Tint by depth as well as scale — far particles cooler and dimmer — or the
parallax reads as scaling rather than distance.

**3. Motion stretch.** Evaluate each particle's position at `t` *and* `t - dt`
with the same function, then stretch its quad along the velocity vector. This is
the single change that makes convergence look fluid rather than teleported:

```wgsl
let hiz = ekran - ekrano;
let ger = clamp(length(hiz) * 11.0, 0.0, 2.9);
let ofs = ileri * kv.x * boyut * (1.0 + ger) + yan * kv.y * boyut;
```

Requires passing the *previous* frame's animation parameter in the uniform too
(`oncekiK` alongside `toplanma`), so the frozen-time capture path stays exact.

**4. Curved paths + overshoot.** Straight-line lerp reads mechanical. Route each
particle along a quadratic bezier whose control point is offset perpendicular to
the travel direction (sign from a per-particle hash so they fan both ways), and
land with a back-out ease that slightly overshoots before settling.

**5. Inside-out formation and a post-formation pulse.** Stagger arrival by
distance from centre so the shape writes itself from the middle out — this is why
the point cloud is sorted by radius at extraction time. Once formed, run a light
wave outward (`sin(radius*k - t)` gated by a `smoothstep`) so the static state
still breathes.

Finish with ACES tonemapping, a vignette, and ~0.01 film grain. Grain at 0.016
was visibly noisy on a dark background; 0.009 reads as texture.

## Colour survives bloom differently than you expect

A palette that looks balanced pre-bloom will not be balanced post-bloom. The
brightest hue wins twice — once in the scene, once in the bright-pass — and eats
the others. On a lime/purple/pink/yellow brand palette the lime completely
swamped purple and pink until three things changed together:

- widen the secondary hues' share of the hash buckets (lime 52% → 38%)
- **boost the secondary hues' brightness** so they clear the bright-pass at all:
  `let sicak = step(0.62, h); c = c * (1.0 + sicak*0.55);`
- raise the bright-pass threshold so only genuinely hot pixels bloom
  (`smoothstep(0.42, 1.30, l)` → `smoothstep(0.52, 1.45, l)`)

Vision-check the *composited* frame for hue balance. The pre-bloom render lies.

## Hero composition — the subject must not fight the copy

A centred subject is correct for a standalone demo and wrong for a hero, where
headline and CTA occupy the left. Two coordinated moves:

- offset the subject on wide viewports only, in the shader:
  `let kaydir = select(0.0, 0.42, en > 1.15);` and shrink it slightly
- CSS-side, cap the text column (`max-width: min(52%, 620px)`) and on narrow
  viewports let the subject re-centre while the copy gains a `text-shadow` for
  legibility over it

**Keep the pointer transform in sync with the subject transform.** Applying an
offset/scale to particle positions without applying the inverse to the pointer
coordinate leaves the cursor-repel field sitting somewhere the subject no longer
is — the interaction silently stops working while everything still *looks* fine.

### Scroll-driven fades must never take the name and role with them

A scene that dims its own copy as it advances is a defensible artistic choice
everywhere except a hero, where that copy is the page's primary payload. The
identity block here faded to **0.12 opacity** on scroll — technically visible,
practically gone — across exactly the stretch where a recruiter is still reading
who this person is.

```css
/* the fade marks the transition, it does not hide the payload */
.ident { opacity: calc(1 - var(--scene-prog) * 0.18); }
```

Cap the total travel at roughly 0.15–0.20 and add a `text-shadow` so the copy
survives the bright regions of the field behind it. A particle bed is not a flat
backdrop; legibility varies frame to frame in a way a static mockup never shows.

Two related placement traps from the same scene:

- **Do not fight an animated layer for the same pixels.** A support line (an
  availability note) was placed inside the hero three times and lost to the
  field's own opacity animation each time, because it inherited the animated
  parent. Moving it to the first stable section below the scene fixed in one
  edit what three CSS attempts could not. Ask whether the element must be *in*
  the animated region at all.
- **Verify at the scroll offset where the effect peaks**, not at rest. Screenshot
  at rest showed acceptable contrast; the failure only existed mid-scene. Drive
  the page to the worst-case offset before judging:

```js
var s = document.getElementById('stage');
window.scrollTo(0, s.offsetTop + (s.offsetHeight - innerHeight) * 0.55);
```

## Delivering a demo the user can open themselves

Kasparov reviews visuals on his own machine ("windows tarayıcıda kontrol
edeyim"). A dev-server URL is useless for that; ship **one self-contained HTML
file that works from `file://` on a double-click**.

This inverts the Rule 2 constraint: `file://` blocks `fetch()`, so for a
deliverable the data must be *inlined* rather than served.

- embed the point cloud / config as a literal in the page; round coordinates to
  3 decimals first (halved the payload with no visible change — 2800 points,
  ~40 KB, whole file ~50–60 KB)
- fonts via CDN `<link>` with a system-font fallback, so it still renders offline
- include the real headline, subtitle and CTA so the layout is judged in context
- put a live readout in the corner (particle count, FPS, canvas resolution) — the
  user can measure their own hardware, which is the entire point of sending it
- make the no-WebGPU panel *actionable*: name the minimum Chrome/Edge version and
  the `chrome://flags/#enable-unsafe-webgpu` toggle rather than just failing

Generate the file from a script that reads the source assets and does the
inlining, so it can be regenerated after every tweak instead of hand-edited.

- `"use client"`, everything inside one `useEffect`, guarded by an `iptal` flag
  so an unmount mid-`await` cannot touch a destroyed device.
- Cleanup must `cancelAnimationFrame`, remove listeners, and `device.destroy()`.
- `npm i -D @webgpu/types` + `"types": ["@webgpu/types"]` in tsconfig, otherwise
  `navigator.gpu` will not typecheck.
- Cap `devicePixelRatio` at 2. Retina otherwise renders 3–4× the pixels for no
  visible gain, and this is a fullscreen effect.
- No engine dependency. Raw WebGPU keeps a landing page's bundle honest;
  pulling in three.js for a background effect is not worth the kilobytes.

### The fallback ladder is not optional

Every one of these is a real user segment, not a nicety:

| Condition | Behaviour |
|---|---|
| `!("gpu" in navigator)` or no adapter | static brand image / CSS gradient |
| `prefers-reduced-motion: reduce` | **slow the loop (~2×), never stop it** — see below |
| `document.hidden` | skip drawing, keep the rAF alive |
| shader or fetch throws | `catch` → same static fallback, never a blank canvas |

#### `prefers-reduced-motion` must NOT freeze the visual

This rule previously said "render one frame, then stop the loop". That is the
textbook reading of the media query and it **shipped a dead page to the user**:
Windows has *Settings → Accessibility → Visual effects → Animation effects* off
by default on many machines, Chrome reports `reduce`, and the delivered hero
opened frozen. The verdict was *"html dosyası statik açıldı animasyon
etkileşimi veya hareket yok"* — read as a broken file, not as a considerate
accessibility default.

Because this OS toggle is common and invisible to the user, honour the
*intent* (calmer motion) without producing something indistinguishable from a
bug:

```js
// Animation ALWAYS starts. reduced-motion only slows the cycle.
let hareketAcik = qs.get("motion") === "0" ? false : true;
const yavasKat  = azHareket ? 1.9 : 1.0;
const dongu     = 14.0 * yavasKat;
```

Then hand control back explicitly — a corner pause/play button, highlighted
when paused, plus a `· DURAKLATILDI` marker in the status readout. Agency beats
a guess about what the user wanted.

Keep the toggle overridable from the query string (`?motion=0` / `?motion=1`)
so both branches stay testable without touching OS settings.

WebGPU sits around 83% of global browser usage — high enough to build on, far
too low to skip the fallback. Audiences spread across many countries on
mid-range Android make this non-negotiable. Retrofitting a fallback later costs
roughly double.

## Canvas diagrams on a CV / portfolio page

A hero scene is judged on impact. A diagram on a page whose *job* is to be found
and parsed is judged on something else entirely, and the tradeoffs invert.

### The canvas is invisible to the readers that matter

ATS parsers and screen readers cannot read a single pixel you draw. Replacing a
written list with a diagram trades a real gain for a decorative one on exactly
the page that must survive keyword search.

- Diagram goes **above** the written list. The list **stays**.
- Give the canvas `role="img"` and an `aria-label` that names the content and
  says the same data is written out below it.
- Say this out loud when reporting. "Listeyi silmedim çünkü tuvali ATS okuyamaz"
  is the kind of decision the user should hear, not discover later.

### Every drawn string must be in the page's language

Seventeen Turkish labels shipped inside an all-English site here and the user
caught it: *"bu arada yeni yaptığın şeylerde türkçe terimler var"*. Variable
names in the source can stay in any language — nobody reads those. Only
`fillText` / `etiket()` content is user-facing.

Audit before handing over, and check *drawn* strings specifically:

```python
for line in src.splitlines():
    if "fillText" not in line and "aria-label" not in line: continue
    for s in re.findall(r"'([^']{2,})'|\"([^\"]{2,})\"", line):
        ...  # flag non-target-language words
```

Proper nouns in the HTML body are a legitimate exception; leave them.

### Never `display:none` a diagram on phones

All four visuals were hidden below 700–760px, so a recruiter opening the page on
a phone got plain text where the section's whole argument was visual. **Shorter,
not absent:**

```css
@media (max-width:700px){ #stack-map{ height:190px } }   /* not display:none */
```

Reflow rather than hide. When N stages cannot fit side by side, stack them:

```js
var dikey = W < n * 108;              // ~108px per stage before labels clip
var kw = dikey ? (W - pay * 2) : (W - pay * (n + 1)) / n;
var kh = dikey ? Math.max(20, (H - 46 - pay * (n + 1)) / n) : 46;
```

Recompute **every** derived position under the vertical branch. The flowing
markers kept using the horizontal formula and drew outside their boxes; the
secondary strip had to be dropped entirely at that width.

### Clip labels on a measured word boundary

A fixed threshold (`if (bw > 92)`) let a narrow box print its text across its
neighbour, and trimming two characters at a time left half-words on screen
(`"scoped, one"`, `"human,"`). Measure the real string, cut at spaces, and draw
nothing rather than something broken:

```js
var tw = ctx.measureText(label).width;
if (bw > tw + 16) ctx.fillText(label, bx + 7, y);
while (ctx.measureText(alt).width > kw - 16 && alt.indexOf(' ') > 0) {
  alt = alt.slice(0, alt.lastIndexOf(' '));
}
```

Shortening the caption text itself is usually the better fix over cleverer
clipping.

### Many small scenes: 2D canvas, and pause the off-screen ones

Six per-card scenes plus three diagrams on one page do **not** each need a GPU
context — that is a real cost for no gain, and none of them needs compute. Use
2D canvas and animate only what is visible:

```js
new IntersectionObserver(function (g) {
  kayit.gorunur = g[0].isIntersecting;
}, { rootMargin: '120px' }).observe(box);
// loop: if (!k.gorunur || document.hidden) continue;
```

Reduced-motion still **slows** these loops rather than freezing them, for the
reason in the fallback ladder above.

### Each scene must depict its own section

Same Rule 0 test, applied per card: the task board moves cards across three
columns, the review gate turns one item back, the disclosure timeline runs 103
days of commits past an unanswered report. A generic shimmer on all six would
have been decoration and would have been rejected.

## A stale cached script will burn your session before you suspect it

The single largest time sink in the scroll-transition work, and it looked
exactly like a logic bug. The code was correct, the selector resolved, the
element existed, and the feature did nothing at all.

Cause: the browser served a **cached copy of the script**. On disk 24,835 bytes,
in the page 24,276. Reloading did not fix it. A cache-buster on the *page* URL
did not fix it either, because only the page was re-fetched.

Before debugging any logic, prove the runtime received the bytes you wrote:

```js
var x = new XMLHttpRequest();
x.open('GET', '/rail.js', false); x.send();
'uzunluk:' + x.responseText.length +
' | yeni isaret:' + (x.responseText.indexOf('<a-string-only-in-the-new-code>') > -1)
```

If the marker is absent, the code you are reading is not the code that ran and
every further hypothesis is wasted. The fix is to version the **script src**:

```html
<script src="rail.js?v=3" defer></script>
```

The faster first probe is a throwaway counter inside the function under
suspicion — it answers "is this even running" in a single call:

```js
window.__PAINT_SAYAC = (window.__PAINT_SAYAC || 0) + 1;   // remove before commit
```

Here it returned `0` while a sibling line in the *same function* was visibly
writing inline styles, which is the contradiction that finally pointed at the
cache rather than the code. Two lessons that generalise past WebGPU:

- **A local edit is not a deployed edit.** Serving over `127.0.0.1` does not
  mean the browser re-read the file.
- **When two statements in one function appear to disagree, suspect that you are
  running an older version of that function**, not that the language is broken.

## The abstraction must NOT resolve back into the photograph

Tried and **rejected**. Starting the figure as an abstraction and crossfading it
into the real photograph on scroll sounds like the same idea as a trace that is
flat until scrolled into a fault. It is not, and the verdict was blunt:

> *"Gerçek fotoya hiç dönmeyelim ya o kötü görünüyor, sadece mevcut tasarımı
> interaktif yapsak yeter."*

Why the analogy fails: the flat trace and the fault are **the same object in two
states**, so the transition is information. An abstraction and a photograph are
two different renderings of one subject, so the transition just admits the
abstraction was a costume. It also drags an ordinary photo into a page whose
whole visual argument is that everything is a measurement.

**Default: the abstraction stays.** If it is not interesting enough to hold the
slot on its own, fix the abstraction, do not fall back to the photo. The user
asked for interactivity instead, which is what actually earned the slot.

Corollary for any hero subject: when tempted to add a "reveal", ask whether the
two states are the same thing changing, or two depictions of one thing. Only the
first is worth building.

### If you do crossfade two rendered layers, generate them in one frame

Still correct for genuine two-state transitions. The trap is geometry drift:
rendering the two layers independently gives them different bounding boxes, so
the subject slides during the fade. **Generate both from the same source at the
same target frame** (here 1408x1760), stack them absolutely, and drive only
opacity:

```css
.hero-portre{position:absolute; aspect-ratio:1408/1760}
.hero-portre img{position:absolute; inset:0; width:100%; height:100%;
  object-fit:contain; object-position:bottom}
.hp-foto{opacity:var(--foto,0)}      /* photograph underneath */
.hp-akim{opacity:var(--akim,1)}      /* abstraction on top    */
```

Drive the two custom properties from the same scroll progress the scene already
computes, so there is one source of truth for "where are we":

```js
var kk  = Math.max(0, Math.min(1, (p - 0.10) / 0.34));
var yum = kk * kk * (3 - 2 * kk);
portre.style.setProperty('--foto', yum.toFixed(3));
portre.style.setProperty('--akim', (1 - yum * 0.88).toFixed(3));
```

Under `prefers-reduced-motion`, hold **both** layers at partial opacity rather
than picking one. Choosing a winner is an arbitrary editorial call; showing the
blend preserves the idea without motion.

## Ship the geometry, not the picture, when the visual must react

A rendered abstraction exported as WebP is a picture of an effect. Export the
**line/point dataset** instead and draw it live, and the same visual gains
interactivity for free. It is usually smaller too: 189 KB of JSON against the
467 KB WebP it replaced here.

Extract once, offline, at drawing resolution rather than display resolution:

```python
teller = []
for x in range(0, W, ADIM):
    kolon = gri[:, x]
    var = np.nonzero(kolon > 0.05)[0]
    if len(var) < 3: continue
    ornekler = [[y, int(float(kolon[y]) * 99)]          # y, brightness 0..99
                for y in range(int(var[0]), int(var[-1]) + 1, 2)
                if kolon[y] >= 0.05]
    if len(ornekler) > 2: teller.append({"x": x, "o": ornekler})
json.dumps({"w": W, "h": H, "teller": teller}, separators=(",", ":"))
```

Quantise aggressively (integers, not floats) and use compact separators. Then in
the page, the same per-sample loop that generated the static image runs per
frame, and every constant in it becomes a live input:

- **pointer** pushes samples aside like a probe touching a live circuit
- **scene state** published by the main scene deforms the whole figure, so the
  subject and the data are the same event rather than two things on one page

```js
window.__portreDurum = function (p, saglik) { prog = p; saglik = saglik; };
// in the scene's paint(): window.__portreDurum(p, volts(p) / NOMINAL);
```

That last coupling is the part worth keeping: a figure that merely *moves* is
decoration, a figure that becomes unstable exactly when the measured value
collapses is the argument. Same Rule 0 test, applied to interactivity.

### Swapping a raster for a canvas: the aspect ratio does not come with it

Caught by the user, not by me: *"yanlardan sıkıştırılmış gibi duruyor şuan ve
bozuk duruyor açıkçası"*.

The canvas inherited `aspect-ratio:1408/1760` from the WebP it replaced, but the
extracted dataset was 702x560 — landscape, not portrait. The draw loop scales the
two axes independently:

```js
var sx = W / veri.w, sy = H / veri.h;     // different ratios = shear
```

so the figure was squeezed to 64% of its width while every individual line still
looked correct. Nothing errors, nothing logs, and it reads as "bozuk" rather than
as a specific bug.

**Whenever a canvas replaces an image, set `aspect-ratio` from the data's own
dimensions**, and re-check the size constraint afterwards: a wider frame at the
same height will collide with the copy column, so height usually has to come
down at the same time.

### Degrade by position when part of the subject reads badly

A hand or an artefact that survives the abstraction too legibly looks like a
mistake. Rather than retouching the source, make the breakdown a function of
position so the region dissolves into signal:

```js
var n = sampleY / veri.h;
var boz = Math.max(0, (n - 0.34) / 0.66); boz = boz * boz * 1.55;
if (v < 0.05 + boz * 0.30) continue;                    // threshold rises
if (((sampleY * 13 + tel.x * 5) % 29) < boz * 19) continue;   // dropouts
var kay = Math.sin(sampleY * 0.09 + tel.x * 0.31) * boz * 13; // drift
```

**Use deterministic waves and modulo patterns, never `random()`.** The first
version used random jitter and tripled the exported file size, because nothing
compressed. Visually identical, three times the bytes.

A photograph in a hero is a photograph. Redrawn in the visual vocabulary the
rest of the page already speaks, it becomes part of the argument. Recipe and
the four treatments tried here: `references/photo-to-visual-language.md`.

Two process rules that mattered more than the technique:

**Generate every candidate and show them side by side.** Describing treatments
in prose wastes a round. Rendering four into one contact sheet with PIL got a
decision in one message. The user's reply was two words.

**A refinement that improves fidelity can still lose.** The follow-up variant
resolved the face noticeably better by varying line spacing with local detail —
and was rejected: *"önceki hali iyi ya"*. The irregular spacing bought detail at
the cost of the calm regularity that made it read as *current* rather than as a
rendering. When a refinement changes the character of an effect, ship it as a
comparison and let the user choose; do not assume more detail wins.

## Ship the code without the commentary

Standing user directive, 11 Aug 2026:

> *"bundan sonra yazdığın hiçbir kodda // açıklama satırlarını yazmanı
> istemiyorum, hiçbir gerçek yazılımcı bu kadar uzun açıklama yazmaz"*

The snippets in this skill are **teaching material** and carry comments so the
reasoning survives. Code you write into a real file does not. Strip `//`, `#`
and `/* ... */` prose from the delivered scene scripts; naming carries it.

This class of work invites the violation more than most, because the maths is
non-obvious and narrating it feels like diligence. Six scene files here shipped
67 lines of commentary before the rule was applied. Check the artifact:

```bash
grep -cE "^\s*(//|/\*|\*)" scene.js
```

Strip, then re-run `node --check` and the render QA — deleting a line that
closed a block is the one way this bites, and it fails loudly.

Put the explanation in the commit message and the reply to the user, where it is
read once, rather than in the file, where it is re-read forever.

## Cost model

Fullscreen raymarching is fragment-bound: every pixel runs the full march, so
cost scales with resolution and it is the risky choice on mobile. Instanced
particles are vertex-bound and cheap. When a design can be expressed either way,
particles win on both performance and (usually) meaning.

If a raymarched scene must ship, the tuning order that costs least visual
quality: main march steps 128→64, then disable the second reflection bounce,
then shadow steps 28→12, then clamp dpr to 1.

## Pitfalls

- **Judge the render, not the code.** Three consecutive vision checks caught
  "plastic not metal", "background colour wash eating half the frame", and
  "mass off-centre" — none of which were visible in the source.
- **Separate the reflection environment from the background.** Reusing one
  `env()` for both floods the frame with colour blobs. Keep punchy coloured
  lights for reflections; paint the background as a plain neutral gradient.
- **Off-centre composition gets caught immediately.** Centre the mass, keep the
  camera target at origin, and damp any pointer-follow term that can drag the
  subject off-axis.
- **Tight specular lobes** (`pow(dot, 26..58)`) read as studio lights; wide ones
  (`pow(dot, 9)`) smear into a colour wash.
- **Metal needs reflection, not diffuse.** Schlick Fresnel with a high `F0`,
  a second bounce for the liquid-mercury read, and a small ambient term so
  interiors do not crush to black.
- **Template-literal collisions**: writing JS into a file from Python, a stray
  `${...}` can survive into the output. Grep the written file for `${` before
  running it.
- **Don't run notification-sending scripts to "test" an unrelated edit.** After
  refactoring secrets out of a monitoring script, running it fired a real
  Telegram message to the user. Syntax-check or dry-run instead.

## Support files

- `scripts/verify_motion.py` — run before every handoff. Proves the page really
  animates (no params, vary only `--virtual-time-budget`) across both the default
  and `--force-prefers-reduced-motion` branches, and that the pointer field
  responds (time frozen, only `?m=` varies). Exits non-zero on a dead loop.
  `python3 scripts/verify_motion.py file:///tmp/scene/index.html`
- `references/logo-to-point-cloud.md` — PNG emblem → particle-target JSON, with
  the masking/normalisation recipe and preview-QA step.
- `references/multipass-bloom-webgpu.md` — the five-pass HDR bloom chain:
  bright-pass, separable Gaussian, ACES composite, plus the resize/rebind trap
  and the cost-reduction ladder.
- `references/photo-to-visual-language.md` — cutting a photograph out and
  redrawing it in the page's own vocabulary: ONNX background removal without the
  numba dependency chain, four treatments compared (scan lines, character
  matrix, contours, current lines), WebP sizing, and the refinement that
  improved fidelity but was rejected for changing the effect's character.
