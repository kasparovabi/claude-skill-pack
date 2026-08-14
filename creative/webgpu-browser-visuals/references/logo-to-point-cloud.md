# Logo → Point Cloud

Turn a brand emblem PNG into particle targets so a converging-particle animation
resolves into the organisation's *actual* mark rather than an invented shape.
This is what makes the visual mean something (see Rule 0 in SKILL.md).

## Recipe

```python
from PIL import Image
import json, math, random

im = Image.open(KAYNAK).convert("RGBA")
W, H = im.size
cx, cy = W / 2.0, H / 2.0

# Mask to the emblem's INNER motif. Tune this multiplier by preview.
ic_yaricap = min(W, H) * 0.268

px = im.load()
adaylar = []
for y in range(0, H, 2):                 # stride 2 — plenty dense, 4x faster
    for x in range(0, W, 2):
        dx, dy = x - cx, y - cy
        if dx*dx + dy*dy > ic_yaricap*ic_yaricap:
            continue                     # outside the motif
        r, g, b, a = px[x, y]
        if a < 200:
            continue                     # transparent
        if r > 205 and g > 205 and b > 205:
            adaylar.append((x, y))       # motif is white on coloured ground

random.seed(42)                          # reproducible cloud
secilen = random.sample(adaylar, ISTENEN)

noktalar = []
for x, y in secilen:
    nx = (x - cx) / ic_yaricap
    ny = -(y - cy) / ic_yaricap          # flip: screen Y down → GL Y up
    noktalar.append([round(nx, 4), round(ny, 4)])

# inside-out convergence reads better than random
noktalar.sort(key=lambda p: math.hypot(p[0], p[1]))

json.dump({"points": noktalar}, open(HEDEF, "w"))
```

## The radius multiplier is the whole job

Most emblems are motif + surrounding ring + wordmark. Only the motif makes a
good particle target; rings render as a lifeless circle and text turns to mush.

Iterate: start near `0.335`, preview, tighten until the ring is gone. `0.268`
was the value that isolated the Seljuk motif in the the client arma (1185×1185 PNG).

## Always preview before wiring the shader

```python
from PIL import Image, ImageDraw
d = json.load(open('motif_noktalar.json'))['points']
S = 600
im = Image.new('RGB', (S, S), (10, 12, 18))
dr = ImageDraw.Draw(im)
for x, y in d:
    px_ = int((x*0.85 + 1) / 2 * S)
    py_ = int((-y*0.85 + 1) / 2 * S)
    dr.ellipse([px_-1, py_-1, px_+1, py_+1], fill=(108, 242, 13))
im.save('nokta_onizleme.png')
```

Then `vision_analyze` it: *"is the motif recognisable, is the outer ring gone?"*
Catching a bad radius here costs one minute. Catching it after the shader,
the React component, and a 6-minute video render costs an hour.

## Threshold variants

The sampling test above assumes **light motif on a dark/coloured ground**. Invert
for the opposite (`r < 60 and g < 60 and b < 60`). For multi-colour emblems,
select by distance to a target colour instead:

```python
if (r-tr)**2 + (g-tg)**2 + (b-tb)**2 < 60**2:
    adaylar.append((x, y))
```

## Density

2500–3000 points reads as a solid shape at 1280×720 while staying cheap.
Drop to ~1500 if a low-end mobile target needs headroom. Regenerate the JSON
rather than dropping points at runtime — the inside-out sort should be
recomputed for the new count.

## Ship shape

- JSON → `public/brand/motif_noktalar.json` (~50 KB at 2800 points)
- extraction script kept beside it so the cloud can be rebuilt when the logo
  changes; note the radius multiplier in a comment, it is not re-derivable by
  eye
- component fetches the JSON, so it needs an HTTP origin — `file://` will fail
