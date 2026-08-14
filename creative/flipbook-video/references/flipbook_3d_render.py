# Flipbook 3B render — gerçek pinhole kamera + global TILT + Lambert ışık + çoklu yaprak
# Bu, kullanıcının 9 iterasyonda onayladığı NİHAİ yaklaşımdır. Basit trapez warp REDDEDİLDİ.
# Kullanım:
#   1. PDF sayfalarını fitz ile /tmp/flip/pages/p00.png... olarak render et (zoom~2).
#      Kitap PDF'leri "spread" (çift sayfa) yapıdadır: ilk/son tek (kapak), aradakiler 2:1.
#      Bu kod half_pages() ile spread'leri otomatik L|R yarıma böler.
#   2. SRC yolunu ayarla, sonra build() çağır.
#   3. ffmpeg ile MP4'e çevir (SKILL.md'deki komut).
#
# AYAR NOKTALARI (kullanıcı tercihleri — SKILL.md'ye bak):
#   TILT  = kitabı stand gibi öne eğme. İçerik okunmuyorsa BUNU artır (THETA'yı değil). ~30° tatlı nokta.
#   THETA = sayfaların omurgadan açılma açısı. Düşük tut (~15°) ki içerik düz/okunur olsun.
#   GROUP = aynı anda dönen yaprak sayısı (kullanıcı 3 istedi). FAN = aralarındaki sabit açı farkı
#           (yelpaze yayılması). STAGGER/faz-gecikmesi yöntemi BAŞARISIZ — build() içindeki uyarıya bak.
#   HOLD/TURN = hız. Düşür = daha hızlı.

import os, sys, math
from PIL import Image, ImageDraw
import numpy as np

SRC = "/tmp/flip/pages"          # fitz render çıktısı (p00.png...)
OUT = "/tmp/flip3/frames"

# --- yarim sayfalar ---
files = sorted(os.listdir(SRC))
raw = [Image.open(os.path.join(SRC, f)).convert("RGB") for f in files]
spread_w = max(im.width for im in raw)
PW = 760
def half_pages(im):
    if im.width < spread_w * 0.75:               # kapak (tek)
        return [im.resize((PW, int(PW * im.height / im.width)))]
    L = im.crop((0, 0, im.width // 2, im.height))
    R = im.crop((im.width // 2, 0, im.width, im.height))
    return [L.resize((PW, int(PW * L.height / L.width))),
            R.resize((PW, int(PW * R.height / R.width)))]
seq = []
for im in raw:
    seq.extend(half_pages(im))
PH = seq[0].height
N = len(seq)

# --- dunya boyutlari ---
W = 1.0
D = (PH / PW) * W
THETA = math.radians(15)         # sayfa egimi: DUSUK tut (icerik okunur)
CURL = 0.05
K = 14
TILT = math.radians(30)          # KITABI ONE EGME: icerik okunmuyorsa BUNU artir
_ct, _st = math.cos(TILT), math.sin(TILT)
RT = np.array([[1, 0, 0], [0, _ct, -_st], [0, _st, _ct]])
def rot(P):  return RT @ np.asarray(P, float)
def rotn(n): return RT @ np.asarray(n, float)

# --- kamera (tam karsidan, ust-on) ---
EYE = np.array([0.0, -2.05, 1.05])
TARGET = np.array([0.0, 0.05, 0.10])
UP = np.array([0.0, 0.0, 1.0])
FOC = 1150.0
def _n(v): return v / np.linalg.norm(v)
FWD = _n(TARGET - EYE); RIGHT = _n(np.cross(FWD, UP)); CUP = np.cross(RIGHT, FWD)

# --- isik (yonlu Lambert + ambient + AO) ---
LIGHT = _n(np.array([0.35, -0.55, 1.0])); AMBIENT = 0.46; DIFFUSE = 0.62
def shade(normal, u, ce=0.0):
    nl = max(0.0, float(np.dot(_n(normal), LIGHT)))
    val = AMBIENT + DIFFUSE * nl
    ao = 0.78 + 0.22 * min(1.0, u * 2.2)         # omurga (u kucuk) civari kapanma
    return max(0.0, min(1.18, val * ao + ce))
def rest_normal(side):
    t = np.array([side * math.cos(THETA), 0.0, math.sin(THETA)])
    n = np.cross(t, np.array([0.0, 1.0, 0.0]));  n = n if n[2] >= 0 else -n
    return rotn(n)
def leaf_normal(beta):
    t = np.array([math.cos(beta), 0.0, math.sin(beta)])
    n = np.cross(t, np.array([0.0, 1.0, 0.0]));  n = n if n[2] >= 0 else -n
    return rotn(n)

def project(P):
    d = rot(P) - EYE
    cz = d @ FWD
    if cz < 0.02: cz = 0.02
    return np.array([FOC * (d @ RIGHT) / cz, -FOC * (d @ CUP) / cz])

def restX(side, u): return side * u * W * math.cos(THETA)
def restZ(u):       return u * W * math.sin(THETA) + CURL * math.sin(math.pi * u)

# bbox -> canvas
_pts = []
for side in (-1, 1):
    for u in (0.0, 1.0):
        for v in (0.0, 1.0):
            _pts.append(project((restX(side, u), v * D, restZ(u))))
_pts.append(project((0, 0, W))); _pts.append(project((0, D, W)))
_pts = np.array(_pts); _min = _pts.min(0); _max = _pts.max(0); PAD = 64
CX = -_min[0] + PAD; CY = -_min[1] + PAD
WC = int(_max[0] - _min[0] + 2 * PAD); HC = int(_max[1] - _min[1] + 2 * PAD)
if WC % 2: WC += 1
if HC % 2: HC += 1
def scr(P):
    p = project(P); return (p[0] + CX, p[1] + CY)

BG_TOP = (16, 18, 23); BG_BOT = (30, 33, 41); COVER = (38, 30, 26)
def base_canvas():
    arr = np.zeros((HC, WC, 3), np.float32)
    for c in range(3):
        arr[:, :, c] = np.linspace(BG_TOP[c], BG_BOT[c], HC)[:, None]
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8))

def find_coeffs(dst, src):
    M = []
    for (dx, dy), (sx, sy) in zip(dst, src):
        M.append([dx, dy, 1, 0, 0, 0, -sx * dx, -sx * dy])
        M.append([0, 0, 0, dx, dy, 1, -sy * dx, -sy * dy])
    return np.linalg.solve(np.array(M, float), np.array(src, float).reshape(8))

def imgx_for(is_left, u):
    return (1 - u) * PW if is_left else u * PW

def warp_strip(face_img, is_left, u0, u1, X, Z, light):
    xa = imgx_for(is_left, u0); xb = imgx_for(is_left, u1)
    lo, hi = (xa, xb) if xa <= xb else (xb, xa)
    loi, hii = int(round(lo)), int(round(hi))
    if hii - loi < 1: hii = loi + 1
    strip = face_img.crop((loi, 0, hii, PH)); sw, sh = strip.size
    far0 = scr((X(u0), D, Z(u0))); near0 = scr((X(u0), 0, Z(u0)))
    far1 = scr((X(u1), D, Z(u1))); near1 = scr((X(u1), 0, Z(u1)))
    u_lo = u0 if xa <= xb else u1; u_hi = u1 if xa <= xb else u0
    def far(u):  return far0 if u == u0 else far1
    def near(u): return near0 if u == u0 else near1
    dst = [far(u_lo), near(u_lo), near(u_hi), far(u_hi)]
    src = [(0, 0), (0, sh), (sw, sh), (sw, 0)]
    try:
        co = find_coeffs(dst, src)
    except Exception:
        return None
    a = np.asarray(strip.convert("RGBA")).astype(np.float32); a[..., :3] *= light(u0)
    st = Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA")
    return st.transform((WC, HC), Image.PERSPECTIVE, co, resample=Image.BICUBIC, fillcolor=(0, 0, 0, 0))

def draw_book_base(fr):
    d = ImageDraw.Draw(fr, "RGBA"); THK = 0.045
    def outline(z):
        return [scr((restX(-1, 1), D, restZ(1) + z)), scr((restX(-1, 1), 0, restZ(1) + z)),
                scr((0, 0, z)), scr((restX(1, 1), 0, restZ(1) + z)),
                scr((restX(1, 1), D, restZ(1) + z)), scr((0, D, z))]
    top = outline(0); bot = outline(-THK)
    for i in range(len(top)):
        j = (i + 1) % len(top)
        d.polygon([top[i], top[j], bot[j], bot[i]], fill=(225, 220, 205, 255))
    d.polygon(bot, fill=COVER + (255,))

def gutter_shadow(fr):
    d = ImageDraw.Draw(fr, "RGBA")
    t = scr((0, D, restZ(0))); b = scr((0, 0, restZ(0)))
    for i in range(16):
        a = int(120 * (1 - i / 16))
        d.line([(t[0] - i, t[1]), (b[0] - i, b[1])], fill=(0, 0, 0, a))
        d.line([(t[0] + i, t[1]), (b[0] + i, b[1])], fill=(0, 0, 0, a))

def render_static(left, right, path):
    fr = base_canvas().convert("RGBA"); draw_book_base(fr)
    nL = rest_normal(-1); nR = rest_normal(1)
    for k in range(K):
        u0, u1 = k / K, (k + 1) / K
        if left is not None:
            w = warp_strip(seq[left], True, u0, u1, lambda u: restX(-1, u), restZ, lambda u: shade(nL, u))
            if w: fr = Image.alpha_composite(fr, w)
        if right is not None:
            w = warp_strip(seq[right], False, u0, u1, lambda u: restX(1, u), restZ, lambda u: shade(nR, u))
            if w: fr = Image.alpha_composite(fr, w)
    fr = fr.convert("RGB"); gutter_shadow(fr); fr.save(path)

def _draw_leaf(fr, front, back, beta, lift=0.0):
    # lift: ekstra kabarma -> coklu yaprak yelpazesinde yapraklari birbirinden ayirir
    front_face = beta <= math.pi / 2; is_left = not front_face
    img = front if front_face else back
    def LX(u): return u * W * math.cos(beta)
    def LZ(u): return u * W * math.sin(beta) + (CURL + lift) * math.sin(math.pi * u)
    nLeaf = leaf_normal(beta)
    if not front_face: nLeaf = nLeaf * np.array([-1.0, 1.0, 1.0])
    sLeaf = lambda u: shade(nLeaf, max(u, 0.35))
    leaf = Image.new("RGBA", (WC, HC), (0, 0, 0, 0))
    for k in range(K):
        u0, u1 = k / K, (k + 1) / K
        w = warp_strip(img, is_left, u0, u1, LX, LZ, sLeaf)
        if w: leaf = Image.alpha_composite(leaf, w)
    return Image.alpha_composite(fr, leaf)

def render_turn_multi(left_static, right_static, leaves, path):
    # leaves: [(front_img, back_img, beta) ya da (front,back,beta,lift), ...] ayni anda donen yapraklar
    fr = base_canvas().convert("RGBA"); draw_book_base(fr)
    nL = rest_normal(-1); nR = rest_normal(1)
    for k in range(K):
        u0, u1 = k / K, (k + 1) / K
        if left_static is not None:
            w = warp_strip(seq[left_static], True, u0, u1, lambda u: restX(-1, u), restZ, lambda u: shade(nL, u))
            if w: fr = Image.alpha_composite(fr, w)
        if right_static is not None:
            w = warp_strip(seq[right_static], False, u0, u1, lambda u: restX(1, u), restZ, lambda u: shade(nR, u))
            if w: fr = Image.alpha_composite(fr, w)
    # painter: en yatik once, en dik en ustte
    norm = [(L[0], L[1], L[2], (L[3] if len(L) > 3 else 0.0)) for L in leaves]
    for (front, back, beta, lift) in sorted(norm, key=lambda L: abs(L[2] - math.pi / 2), reverse=True):
        fr = _draw_leaf(fr, front, back, beta, lift)
    fr = fr.convert("RGB"); gutter_shadow(fr); fr.save(path)

# --- video kareleri: 3'erli YELPAZE acilis (DOGRU yontem) ---
# DIKKAT: Eski STAGGER (faz gecikmesi) yontemi BASARISIZ oldu — yapraklar farkli zamanlarda
# doner, cogu anda TEK yaprak havada kalir, sonuc bir oncekiyle ayni gorunur. DOGRU yontem:
# yapraklari SABIT ACI FARKIYLA (FAN) BIRLIKTE dondur -> hepsi ayni anda farkli acida = surekli yelpaze.
def build():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT): os.remove(os.path.join(OUT, f))
    PI = math.pi; HOLD = 5; TURN = 26; GROUP = 3
    FAN = 0.42         # yapraklar arasi sabit aci farki (rad) -> surekli yelpaze
    LIFT_STEP = 0.10   # her ust yaprak biraz daha kabarik (ayrim icin)
    def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)  # smoothstep
    spreads = [(None, 0)]; i = 1
    while i < N:
        spreads.append((i, i + 1 if i + 1 < N else None)); i += 2
    Sn = len(spreads); fi = 0
    def save_static(l, r, n=1):
        nonlocal fi
        for _ in range(n): render_static(l, r, f"{OUT}/f{fi:04d}.png"); fi += 1
    save_static(spreads[0][0], spreads[0][1], HOLD)
    g = 0
    while g < Sn - 1:
        grp = min(GROUP, (Sn - 1) - g); target = spreads[g + grp]
        left_static = spreads[g][0]; right_static = target[1]
        leaf_defs = []
        for l in range(grp):
            rg = spreads[g + l][1]; nl = spreads[g + l + 1][0]
            front = seq[rg] if rg is not None else seq[nl]
            back = seq[nl] if nl is not None else seq[rg]
            leaf_defs.append((front, back))
        for fnum in range(1, TURN + 1):
            t = fnum / TURN
            bc = THETA + (PI - 2 * THETA) * ease(t)   # grup merkez acisi
            spread_amt = math.sin(PI * t)             # yelpaze yalniz havadayken acilir
            specs = []
            for l in range(grp):
                off = (l - (grp - 1) / 2.0) * FAN * spread_amt
                beta = max(0.12, min(PI - 0.12, bc + off))
                lift = LIFT_STEP * l * spread_amt
                specs.append((leaf_defs[l][0], leaf_defs[l][1], beta, lift))
            render_turn_multi(left_static, right_static, specs, f"{OUT}/f{fi:04d}.png"); fi += 1
        g += grp
        save_static(spreads[g][0], spreads[g][1], HOLD)
    print("toplam frame:", fi)

if __name__ == "__main__":
    build()
