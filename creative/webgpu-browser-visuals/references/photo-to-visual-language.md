# Redrawing a photograph in the page's visual language

Use when a portrait or product photo has to sit inside a scene that already has
a strong visual vocabulary (a trace, a field, a diagram system). Dropping the
raw photo in reads as a photo pasted onto a design. Redrawing it in the same
language makes it part of the argument.

Worked case: a CV site whose whole vocabulary is oscilloscope / voltage
measurement. The brief was *"direkt görsel olarak değil de point cloud gibi ama
point cloud da değil başka nasıl gösterebiliriz beni"* — abstraction wanted,
point cloud explicitly ruled out.

## Step 1 — cut the subject out

Background removal without the heavy dependency chain. `onnxruntime` + `pillow`
+ `numpy` only, no matting library, so nothing pulls in a pinned numba:

```python
MODEL = "/tmp/u2net_human_seg.onnx"
URL = ("https://github.com/danielgatis/rembg/releases/download/"
       "v0.0.0/u2net_human_seg.onnx")
if not os.path.exists(MODEL):
    urllib.request.urlretrieve(URL, MODEL)          # ~168 MB, cache it

im = Image.open(src).convert("RGB"); W, H = im.size
g = im.resize((320, 320), Image.LANCZOS)
a = np.array(g).astype(np.float32) / 255.0
a = (a - np.array([0.485, 0.456, 0.406])) / np.array([0.229, 0.224, 0.225])
a = a.transpose(2, 0, 1)[None].astype(np.float32)

s = ort.InferenceSession(MODEL, providers=["CPUExecutionProvider"])
m = s.run(None, {s.get_inputs()[0].name: a})[0][0, 0]
m = (m - m.min()) / (m.max() - m.min() + 1e-8)

res = im.convert("RGBA")
res.putalpha(Image.fromarray((m * 255).astype(np.uint8)).resize((W, H), Image.LANCZOS))
```

Run it under `uv run --isolated --with onnxruntime --with pillow --with numpy`
so it cannot collide with whatever the ambient interpreter has installed.

**Verify the cut before building on it.** Composite onto the site's own dark
background and look at it — hair, shoulders, bag straps are where these models
fail. Alpha histogram is a cheap sanity check: a clean human-segmentation cut
lands near 60% fully transparent / 38% fully opaque, with a thin soft edge. If
the opaque share is far higher, the model kept background.

## Step 2 — mask out the background from the luminance too

Every treatment below reads `gri`. If the background is still in it, the
treatment renders the background as well:

```python
gri = np.array(im.convert("L"), dtype=np.float32) / 255.0
alfa = np.array(im.split()[3], dtype=np.float32) / 255.0
gri = gri * alfa            # <- do not skip
```

## Step 3 — render candidates, all of them, into one sheet

Four treatments were tried. Only the last two were viable, but generating all
four cost one script and produced a decision in one message.

### 1. Oscilloscope scan lines — weakest

Each image row becomes a measurement trace; luminance deflects the line.

```python
for y in range(0, H, 5):
    pts = [(x, y - (gri[y, x] - 0.5) * 5 * 2.6)
           for x in range(0, W, 2) if gri[y, x] >= 0.04]
    d.line(pts, fill=renk, width=1)
```

Verdict: figure survives but detail washes out. Conceptually on-theme, visually
too faint to carry a hero.

### 2. Character matrix

Terminal aesthetic, `" .:-=+*#%@"` ramp over 6x9 cells. Recognisable, but the
face fragments. Good for a small inline figure, not for a hero.

### 3. Contour lines — best legibility

Threshold the luminance at N levels and draw the boundary of each region by
XOR-ing the mask against itself shifted by one pixel:

```python
for i, s in enumerate([0.12, 0.22, 0.33, 0.45, 0.58, 0.72, 0.86]):
    mask = (gri > s).astype(np.uint8)
    kenar = np.zeros_like(mask)
    kenar[1:, :] |= mask[1:, :] ^ mask[:-1, :]
    kenar[:, 1:] |= mask[:, 1:] ^ mask[:, :-1]
    ys, xs = np.nonzero(kenar)
```

Verdict: glasses, tie, jacket all read clearly. Topographic, abstract, precise.
This was my recommendation.

### 4. Vertical current lines — what shipped

Columns of varying thickness, thickness tracking luminance. Reads as conductors
carrying current, which is exactly the page's subject.

```python
ADIM = 15                      # scale with output resolution, not fixed px
for x in range(0, W, ADIM):
    col = gri[:, x]
    var = np.nonzero(col > 0.05)[0]
    if len(var) < 2: continue
    for y in range(int(var[0]), int(var[-1]) + 1):
        v = float(col[y])
        if v < 0.05: continue
        kal = 2 + int(v * 5.0)
        d.rectangle([x - kal // 2, y, x + kal // 2, y], fill=renk_for(v))
```

Chosen by the user over the contour version I preferred. **Ask, do not decide.**

## Step 4 — the refinement that lost

The shipped version's weakness is the face: at fixed spacing, the most detailed
region of the image is the one that loses most. The obvious fix is to vary
spacing by local detail, tightening lines where an edge-detect pass finds
structure:

```python
kenar = np.array(gri_im.filter(ImageFilter.FIND_EDGES), dtype=np.float32) / 255.0
sutun_detay = (kenar * alfa).mean(axis=0)
sutun_detay /= sutun_detay.max()
# ...
det = float(sutun_detay[x])
adim = int(adim_max - (adim_max - adim_min) * min(1.0, det * 2.6))
```

It worked: glasses, facial features, tie pattern and hands all resolved. It was
**rejected** — *"önceki hali iyi ya"*.

The irregular spacing bought fidelity and spent the calm regularity that made
the effect read as *current* rather than as a rendering technique. The lesson is
not "do not refine". It is: when a refinement changes the *character* of an
effect rather than just its quality, present it as a before/after comparison and
let the user pick. Assuming more detail wins is how you lose the thing that made
the first version work.

## Step 5 — output at 2x and ship WebP with alpha

Generate at twice the maximum on-screen height (here 880px display, so 1760px
render), keeping the same frame as any layer it will crossfade with.

| Format | Size |
|---|---|
| transparent PNG | 691 KB |
| WebP q=86 at 2x the height | 147 KB |
| current-lines WebP (sparse) | 72 KB |

```python
img.save(path, "WEBP", quality=86, method=6)
```

Line-art treatments compress far better than photographs because most of the
frame is transparent, which is a real argument for them on a page that also
carries several canvases.

## Placement pitfalls

- **Check the far edge.** At `right:1vw` with a wide source, an arm hung off the
  viewport. `right:3vw` plus a slightly smaller height fixed it. Look at the
  render; the CSS reads fine either way.
- **Cap the copy column** on wide screens (`max-width:min(58%,680px)`) so text
  never runs under the figure.
- **Do not hard-mask a line treatment.** Lines already fall off into the dark;
  an aggressive gradient mask on top eats the torso. The mask here only needed
  to start at 72%, versus 46% for the photographic layer.
