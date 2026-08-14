# Flipbook RIFFLE render — EN GÜNCEL NİHAİ form (kullanıcı en son bunu onayladı).
#
# flipbook_cinematic_render.py'nin altyapısını (3B pinhole projeksiyon, TILT, Lambert ışık,
# render_frame/render_closed/set_camera) AYNEN kullanır. SADECE iki şey farklı:
#   (A) KAMERA: faz-faz lerp yerine TÜM VİDEO boyunca SÜREKLİ yumuşak yörünge — tek cam_at(p) fonksiyonu.
#       Kullanıcı "kamera daha smooth ve fazla olabilir" dedi.
#   (B) AKIŞ (FAZ 3): 3'erli FAN deste yerine RIFFLE = tüm yaprakların sağdan sola SÜREKLİ DALGASI
#       ("fırr"). Kullanıcı "3lü değil tekte fırr diye tarasın yapraklar" dedi.
#
# KRİTİK KALİBRASYON: SPAN aynı anda kaç yaprağın havada olduğunu belirler.
#   SPAN=0.32 → ~10 yaprak birden = kitap iki yana açılmış gibi dağınık (YANLIŞ).
#   SPAN=0.13 → aynı anda 3-4 yaprak ince dalga = gerçek başparmak taraması (DOĞRU).
#
# Bu dosya kendi başına çalışır: ortak altyapı buraya da kopyalandı. SRC'yi fitz render çıktısına
# ayarla, build() çağır, sonra ffmpeg ile birleştir (komut SKILL.md'de).
#
# DOĞRULAMA DİSİPLİNİ: full video bitince ffmpeg -ss ~2.3 ile asıl videodan kare çıkar,
# 3-4 yaprağın dalga halinde aktığını vision_analyze ile teyit et, SONRA gönder.

import os, math
from PIL import Image, ImageDraw
import numpy as np

SRC = "/tmp/flip/pages"     # fitz render çıktısı (p00.png...; zoom~2)
OUT = "/tmp/flip4/frames"

# --- yarim sayfalar (spread -> L|R) ---
files = sorted(os.listdir(SRC))
raw = [Image.open(os.path.join(SRC, f)).convert("RGB") for f in files]
spread_w = max(im.width for im in raw)
PW = 760
def half_pages(im):
    if im.width < spread_w * 0.75:
        return [im.resize((PW, int(PW * im.height / im.width)))]
    L = im.crop((0, 0, im.width // 2, im.height)); R = im.crop((im.width // 2, 0, im.width, im.height))
    return [L.resize((PW, int(PW * L.height / L.width))), R.resize((PW, int(PW * R.height / R.width)))]
seq = []
for im in raw:
    seq.extend(half_pages(im))
PH = seq[0].height; N = len(seq)

# --- dunya + global TILT (okunabilirlik; ~26-30 deg) ---
W = 1.0; D = (PH / PW) * W
THETA = math.radians(15); CURL = 0.05; K = 14
TILT = math.radians(26)
_ct, _st = math.cos(TILT), math.sin(TILT)
RT = np.array([[1, 0, 0], [0, _ct, -_st], [0, _st, _ct]])
def rot(P):  return RT @ np.asarray(P, float)
def rotn(n): return RT @ np.asarray(n, float)

# --- SABİT portre tuval (dikey; "aşırı yatay" şikayetinin çözümü) ---
OUTW, OUTH = 1180, 1320
CXp, CYp = OUTW / 2.0, OUTH / 2.0 - 60
UP = np.array([0.0, 0.0, 1.0])
BOOK_CENTER = rot((0.0, D * 0.5, 0.10))

AMBIENT = 0.46; DIFFUSE = 0.62
LIGHT = None; EYE = FWD = RIGHT = CUP = None; FOC = 1180.0

def set_camera(az, el, dist, foc=1180.0):
    global EYE, FWD, RIGHT, CUP, FOC, LIGHT
    off = np.array([math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)]) * dist
    EYE = BOOK_CENTER + off
    FWD = BOOK_CENTER - EYE; FWD = FWD / np.linalg.norm(FWD)
    RIGHT = np.cross(FWD, UP); RIGHT = RIGHT / np.linalg.norm(RIGHT)
    CUP = np.cross(RIGHT, FWD); FOC = foc
    L = np.array([0.35, -0.55, 1.0]); LIGHT = L / np.linalg.norm(L)

set_camera(0.0, math.radians(20), 2.2)

def project(P):
    d = rot(P) - EYE; cz = d @ FWD
    if cz < 0.05: cz = 0.05
    return (FOC * (d @ RIGHT) / cz + CXp, -FOC * (d @ CUP) / cz + CYp)

def shade(normal, u):
    nl = max(0.0, float(np.dot(normal / np.linalg.norm(normal), LIGHT)))
    val = AMBIENT + DIFFUSE * nl
    ao = 0.78 + 0.22 * min(1.0, u * 2.2)
    return max(0.0, min(1.18, val * ao))

def rest_normal(side):
    t = np.array([side * math.cos(THETA), 0.0, math.sin(THETA)])
    n = np.cross(t, np.array([0.0, 1.0, 0.0])); n = n if n[2] >= 0 else -n
    return rotn(n)
def leaf_normal(beta):
    t = np.array([math.cos(beta), 0.0, math.sin(beta)])
    n = np.cross(t, np.array([0.0, 1.0, 0.0])); n = n if n[2] >= 0 else -n
    return rotn(n)
def restX(side, u): return side * u * W * math.cos(THETA)
def restZ(u):       return u * W * math.sin(THETA) + CURL * math.sin(math.pi * u)

def find_coeffs(dst, src):
    M = []
    for (dx, dy), (sx, sy) in zip(dst, src):
        M.append([dx, dy, 1, 0, 0, 0, -sx * dx, -sx * dy]); M.append([0, 0, 0, dx, dy, 1, -sy * dx, -sy * dy])
    return np.linalg.solve(np.array(M, float), np.array(src, float).reshape(8))

def base_canvas():
    arr = np.zeros((OUTH, OUTW, 3), np.float32)
    top = np.array([14, 16, 22], np.float32); bot = np.array([32, 35, 44], np.float32)
    for c in range(3):
        arr[:, :, c] = np.linspace(top[c], bot[c], OUTH)[:, None]
    yy, xx = np.mgrid[0:OUTH, 0:OUTW]
    r = ((xx - CXp) ** 2 + (yy - CYp) ** 2) ** 0.5 / (0.5 * (OUTW + OUTH) / 2)
    vig = (1 - 0.35 * np.clip(r - 0.4, 0, 1))[:, :, None]
    arr *= vig
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8))

def imgx_for(is_left, u): return (1 - u) * PW if is_left else u * PW

def warp_strip(face_img, is_left, u0, u1, X, Z, light):
    xa = imgx_for(is_left, u0); xb = imgx_for(is_left, u1)
    lo, hi = (xa, xb) if xa <= xb else (xb, xa)
    loi, hii = int(round(lo)), int(round(hi))
    if hii - loi < 1: hii = loi + 1
    strip = face_img.crop((loi, 0, hii, PH)); sw, sh = strip.size
    u_lo = u0 if xa <= xb else u1; u_hi = u1 if xa <= xb else u0
    def far(u):  return project((X(u), D, Z(u)))
    def near(u): return project((X(u), 0, Z(u)))
    dst = [far(u_lo), near(u_lo), near(u_hi), far(u_hi)]
    try:
        co = find_coeffs(dst, [(0, 0), (0, sh), (sw, sh), (sw, 0)])
    except Exception:
        return None
    a = np.asarray(strip.convert("RGBA")).astype(np.float32); a[..., :3] *= light(u0)
    st = Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA")
    return st.transform((OUTW, OUTH), Image.PERSPECTIVE, co, resample=Image.BILINEAR, fillcolor=(0, 0, 0, 0))

def draw_book_base(fr):
    d = ImageDraw.Draw(fr, "RGBA"); THK = 0.05
    def outline(z):
        return [project((restX(-1, 1), D, restZ(1) + z)), project((restX(-1, 1), 0, restZ(1) + z)),
                project((0, 0, z)), project((restX(1, 1), 0, restZ(1) + z)),
                project((restX(1, 1), D, restZ(1) + z)), project((0, D, z))]
    top = outline(0); bot = outline(-THK)
    for i in range(len(top)):
        j = (i + 1) % len(top)
        d.polygon([top[i], top[j], bot[j], bot[i]], fill=(228, 223, 208, 255))
    d.polygon(bot, fill=(40, 32, 28, 255))

def gutter_shadow(fr):
    d = ImageDraw.Draw(fr, "RGBA")
    t = project((0, D, restZ(0))); b = project((0, 0, restZ(0)))
    for i in range(16):
        a = int(115 * (1 - i / 16))
        d.line([(t[0] - i, t[1]), (b[0] - i, b[1])], fill=(0, 0, 0, a))
        d.line([(t[0] + i, t[1]), (b[0] + i, b[1])], fill=(0, 0, 0, a))

def _draw_leaf(fr, front, back, beta, lift=0.0):
    front_face = beta <= math.pi / 2; is_left = not front_face
    img = front if front_face else back
    def LX(u): return u * W * math.cos(beta)
    def LZ(u): return u * W * math.sin(beta) + (CURL + lift) * math.sin(math.pi * u)
    nL = leaf_normal(beta)
    if not front_face: nL = nL * np.array([-1.0, 1.0, 1.0])
    sL = lambda u: shade(nL, max(u, 0.35))
    leaf = Image.new("RGBA", (OUTW, OUTH), (0, 0, 0, 0))
    for k in range(K):
        u0, u1 = k / K, (k + 1) / K
        w = warp_strip(img, is_left, u0, u1, LX, LZ, sL)
        if w: leaf = Image.alpha_composite(leaf, w)
    return Image.alpha_composite(fr, leaf)

def render_frame(left_static, right_static, leaves, path):
    """leaves: [(front,back,beta,lift), ...]; left/right_static: seq index ya da None."""
    fr = base_canvas().convert("RGBA"); draw_book_base(fr)
    nLs = rest_normal(-1); nRs = rest_normal(1)
    for k in range(K):
        u0, u1 = k / K, (k + 1) / K
        if left_static is not None:
            w = warp_strip(seq[left_static], True, u0, u1, lambda u: restX(-1, u), restZ, lambda u: shade(nLs, u))
            if w: fr = Image.alpha_composite(fr, w)
        if right_static is not None:
            w = warp_strip(seq[right_static], False, u0, u1, lambda u: restX(1, u), restZ, lambda u: shade(nRs, u))
            if w: fr = Image.alpha_composite(fr, w)
    norm = [(L[0], L[1], L[2], (L[3] if len(L) > 3 else 0.0)) for L in leaves]
    # painter: en yatık önce, en dik en üstte
    for (fimg, bimg, beta, lift) in sorted(norm, key=lambda L: abs(L[2] - math.pi / 2), reverse=True):
        fr = _draw_leaf(fr, fimg, bimg, beta, lift)
    fr = fr.convert("RGB"); gutter_shadow(fr); fr.save(path)

def render_closed(cover_img, path, z_lift=0.0):
    fr = base_canvas().convert("RGBA")
    cw = W * 1.06; THK = 0.07
    d = ImageDraw.Draw(fr, "RGBA")
    def corner(x, y, z): return project((x, y, z))
    topf = [corner(-cw/2, D, z_lift), corner(cw/2, D, z_lift), corner(cw/2, 0, z_lift), corner(-cw/2, 0, z_lift)]
    botf = [corner(-cw/2, D, z_lift-THK), corner(cw/2, D, z_lift-THK), corner(cw/2, 0, z_lift-THK), corner(-cw/2, 0, z_lift-THK)]
    for i in range(4):
        j = (i + 1) % 4
        d.polygon([topf[i], topf[j], botf[j], botf[i]], fill=(225, 220, 205, 255))
    dst = [corner(-cw/2, D, z_lift), corner(cw/2, D, z_lift), corner(cw/2, 0, z_lift), corner(-cw/2, 0, z_lift)]
    co = find_coeffs([dst[0], dst[3], dst[2], dst[1]],
                     [(0, 0), (0, cover_img.height), (cover_img.width, cover_img.height), (cover_img.width, 0)])
    sh = shade(rotn(np.array([0.0, 0.0, 1.0])), 0.9)
    a = np.asarray(cover_img.convert("RGBA")).astype(np.float32); a[..., :3] *= sh
    cv = Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA")
    fr = Image.alpha_composite(fr, cv.transform((OUTW, OUTH), Image.PERSPECTIVE, co, resample=Image.BILINEAR, fillcolor=(0, 0, 0, 0)))
    fr.convert("RGB").save(path)

spreads = [(None, 0)]
i = 1
while i < N:
    spreads.append((i, i + 1 if i + 1 < N else None)); i += 2
S = len(spreads)

def build(cover_path="/tmp/flip/pages/p00.png"):
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT): os.remove(os.path.join(OUT, f))
    cover = Image.open(cover_path).convert("RGB")
    PI = math.pi; fi = 0
    def smooth(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
    def smoother(x): x = max(0.0, min(1.0, x)); return x*x*x*(x*(x*6-15)+10)   # quintic, çok yumuşak
    def lerp(a, b, t): return a + (b - a) * t

    # --- SÜREKLİ AKICI kamera: tek fonksiyon, video boyunca yumuşak yörünge ---
    def cam_at(p):
        az = math.radians(14) * math.sin(2*PI*p*0.9 + 0.4) - math.radians(8)*p
        el = math.radians(22) + math.radians(12) * (0.5 - 0.5*math.cos(2*PI*p*0.7))
        dist = lerp(1.95, 2.5, smooth(min(1.0, p*1.4))) - 0.18*math.sin(2*PI*p*0.6)
        foc = lerp(1260, 1150, smooth(min(1.0, p*1.5)))
        return az, el, dist, foc

    F_COVER = 24; F_OPEN = 22; F_RIFFLE = 80; F_END = 22
    TOTAL = F_COVER + F_OPEN + F_RIFFLE + F_END

    # FAZ 1: kapalı kapak (okuma)
    for _ in range(F_COVER):
        set_camera(*cam_at(fi / TOTAL))
        render_closed(cover, f"{OUT}/f{fi:04d}.png"); fi += 1
    # FAZ 2: kapak açılışı
    for k in range(1, F_OPEN + 1):
        set_camera(*cam_at(fi / TOTAL))
        t = k / F_OPEN
        beta = THETA + (PI - 2 * THETA) * smoother(t)
        render_frame(None, spreads[1][1] if S > 1 else None,
                     [(seq[0], seq[1], beta, 0.05 * math.sin(PI*t))], f"{OUT}/f{fi:04d}.png"); fi += 1
    # FAZ 3: RIFFLE — tüm yapraklar tek fırr'da sürekli dalga
    nleaves = S - 1
    SPAN = 0.13   # KRİTİK: ~3-4 yaprak havada (fırr). 0.32 → ~10 yaprak = dağınık.
    for fnum in range(1, F_RIFFLE + 1):
        set_camera(*cam_at(fi / TOTAL))
        gt = fnum / F_RIFFLE
        step = (1.0 - SPAN) / max(1, nleaves - 1)
        specs = []; done = 0; pending_first = None
        for l in range(nleaves):
            lt = (gt - l * step) / SPAN
            if lt >= 1.0:
                done = l + 1; continue
            if lt <= 0.0:
                if pending_first is None: pending_first = l
                continue
            rg = spreads[1 + l][1]
            nl = spreads[2 + l][0] if (2 + l) < S else None
            front = seq[rg] if rg is not None else (seq[nl] if nl is not None else seq[0])
            back = seq[nl] if nl is not None else (seq[rg] if rg is not None else seq[0])
            beta = THETA + (PI - 2 * THETA) * smooth(lt)
            specs.append((front, back, beta, 0.06 * math.sin(PI*lt)))
        left_static = spreads[min(done, S - 1)][0] if done >= 1 else spreads[1][0]
        right_static = spreads[1 + pending_first][1] if pending_first is not None else spreads[S - 1][1]
        render_frame(left_static, right_static, specs, f"{OUT}/f{fi:04d}.png"); fi += 1
    # FAZ 4: bitiş, kamera ortala + yumuşak durul
    last = spreads[S - 1]
    for k in range(1, F_END + 1):
        p = fi / TOTAL
        az = math.radians(14)*math.sin(2*PI*p*0.9+0.4)*(1-smooth(k/F_END)) - math.radians(8)
        dist = lerp(2.4, 2.2, smooth(k/F_END))
        set_camera(az, math.radians(28), dist, 1180)
        render_frame(last[0], last[1], [], f"{OUT}/f{fi:04d}.png"); fi += 1
    print("toplam frame:", fi, "yaprak:", nleaves)

if __name__ == "__main__":
    build()
