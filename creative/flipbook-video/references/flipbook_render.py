"""Flipbook video render — V-sekilli 90 derece acik kitap + serit perspektif yaprak bukulme.

Kullanim:
  1. PDF sayfalarini render et (asagidaki render_pages bolumu).
  2. Bu modulu calistir: build_video() tum kareleri uretip ffmpeg ile MP4 yapar.
  3. SRC, OUT_MP4 yollarini gorevine gore ayarla.

DIKKAT: Bu dosyayi /tmp/inspect.py / /tmp/numpy.py gibi stdlib'i golgeleyen
isimlerle AYNI dizine koyma; ayri bir alt dizinde calistir.

Bu oturumda (Cevre Uygulamalari Kilavuzu PDF -> flipbook) test edilip dogrulandi.
"""
import os, math, subprocess
import fitz
from PIL import Image, ImageDraw
import numpy as np

PDF = "/tmp/cevre.pdf"
WORK = "/tmp/flipwork"        # AYRI dizin — stdlib golgeleme onlemek icin
SRC = f"{WORK}/pages"
FRAMES = f"{WORK}/frames"
OUT_MP4 = f"{WORK}/out.mp4"

# ---------------- 1. PDF render ----------------
def render_pages(zoom=2.0):
    os.makedirs(SRC, exist_ok=True)
    doc = fitz.open(PDF)
    mat = fitz.Matrix(zoom, zoom)
    for i, page in enumerate(doc):
        page.get_pixmap(matrix=mat).save(f"{SRC}/p{i:02d}.png")
    return len(doc)

# ---------------- 2. yarim sayfalar ----------------
PW = 760  # kaynak yarim sayfa genisligi
def load_halves():
    files = sorted(os.listdir(SRC))
    raw = [Image.open(os.path.join(SRC, f)).convert("RGB") for f in files]
    spread_w = max(im.width for im in raw)
    seq = []
    for im in raw:
        if im.width < spread_w * 0.75:           # kapak (tek)
            seq.append(im.resize((PW, int(PW * im.height / im.width))))
        else:                                     # spread -> L|R
            L = im.crop((0, 0, im.width // 2, im.height))
            Rr = im.crop((im.width // 2, 0, im.width, im.height))
            seq.append(L.resize((PW, int(PW * L.height / L.width))))
            seq.append(Rr.resize((PW, int(PW * Rr.height / Rr.width))))
    return seq

# ---------------- 3. layout (90 derece V) ----------------
seq = None; PH = 0; N = 0
MX, MY = 70, 70
RW = 540   # ekran yari genisligi (dar = 90 derece his)
VT = 46    # dikey perspektif daralmasi
LIFT = 60  # yaprak ortasi kalkma
K = 11     # serit sayisi
CX = MX + RW; TOPY = MY; WC = 0; HC = 0; BOTY = 0
BG = (20, 22, 28); PANEL = (8, 9, 12)

def setup():
    global seq, PH, N, BOTY, WC, HC
    seq = load_halves(); PH = seq[0].height; N = len(seq)
    BOTY = MY + PH
    WC = 2 * RW + 2 * MX; HC = PH + 2 * MY + 30
    if WC % 2: WC += 1
    if HC % 2: HC += 1

def stops_list():
    st = [(None, 0)]; i = 1
    while i < N:
        st.append((i, i + 1 if i + 1 < N else None)); i += 2
    return st

def find_coeffs(dst, src):
    M = []
    for (dx, dy), (sx, sy) in zip(dst, src):
        M.append([dx, dy, 1, 0, 0, 0, -sx*dx, -sx*dy])
        M.append([0, 0, 0, dx, dy, 1, -sy*dx, -sy*dy])
    return np.linalg.solve(np.array(M, float), np.array(src, float).reshape(8))

def base_canvas():
    arr = np.zeros((HC, WC, 3), np.float32) + np.array(BG, np.float32)
    arr += np.linspace(0, 14, HC)[:, None, None]
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8))

def page_static(img, side):
    if side == "L":
        dst = [(CX-RW, TOPY+VT), (CX-RW, BOTY-VT), (CX, BOTY), (CX, TOPY)]
    else:
        dst = [(CX, TOPY), (CX, BOTY), (CX+RW, BOTY-VT), (CX+RW, TOPY+VT)]
    co = find_coeffs(dst, [(0,0),(0,img.height),(img.width,img.height),(img.width,0)])
    a = np.asarray(img.convert("RGBA")).astype(np.float32); a[..., :3] *= 0.96
    return Image.fromarray(a.clip(0,255).astype(np.uint8), "RGBA").transform(
        (WC, HC), Image.PERSPECTIVE, co, resample=Image.BICUBIC, fillcolor=(0,0,0,0))

def draw_panel(fr):
    ImageDraw.Draw(fr).polygon(
        [(CX-RW-10, TOPY+VT-10),(CX, TOPY-10),(CX+RW+10, TOPY+VT-10),
         (CX+RW+10, BOTY-VT+10),(CX, BOTY+10),(CX-RW-10, BOTY-VT+10)], fill=PANEL)

def spine_shadow(fr):
    d = ImageDraw.Draw(fr, "RGBA")
    for i in range(20):
        a = int(110*(1-i/20))
        d.line([(CX-i, TOPY),(CX-i, BOTY)], fill=(0,0,0,a))
        d.line([(CX+i, TOPY),(CX+i, BOTY)], fill=(0,0,0,a))

def render_static(left, right, path):
    fr = base_canvas(); draw_panel(fr); fr = fr.convert("RGBA")
    if left is not None: fr = Image.alpha_composite(fr, page_static(seq[left], "L"))
    if right is not None: fr = Image.alpha_composite(fr, page_static(seq[right], "R"))
    fr = fr.convert("RGB"); spine_shadow(fr); fr.save(path)

def render_turn(left_static, right_static, front, back, t, path):
    fr = base_canvas(); draw_panel(fr); fr = fr.convert("RGBA")
    if left_static is not None: fr = Image.alpha_composite(fr, page_static(seq[left_static], "L"))
    if right_static is not None: fr = Image.alpha_composite(fr, page_static(seq[right_static], "R"))
    eps = 0.06; tt = min(max(t, eps), 1-eps)
    ox = RW*math.cos(math.pi*tt)
    if abs(ox) < 8: ox = 8 if ox >= 0 else -8
    facing = abs(math.cos(math.pi*tt)); front_face = tt < 0.5
    img = front if front_face else back.transpose(Image.FLIP_LEFT_RIGHT)
    leaf = Image.new("RGBA", (WC, HC), (0,0,0,0))
    for k in range(K):
        u0, u1 = k/K, (k+1)/K
        def X(u): return CX + ox*u
        def lift(u): return LIFT*math.sin(math.pi*u)*math.sin(math.pi*tt)
        def ytop(u): return TOPY + VT*facing*u - lift(u)
        def ybot(u): return BOTY - VT*facing*u - lift(u)*0.5
        dst = [(X(u0), ytop(u0)),(X(u0), ybot(u0)),(X(u1), ybot(u1)),(X(u1), ytop(u1))]
        x0i, x1i = int(round(u0*PW)), int(round(u1*PW))
        if x1i - x0i < 1: x1i = x0i + 1
        strip = img.crop((x0i, 0, x1i, PH))
        if abs(dst[3][0]-dst[0][0]) < 0.5 and abs(dst[2][0]-dst[1][0]) < 0.5:
            continue
        sh = (0.5+0.5*facing)*(0.9+0.18*math.sin(math.pi*u0)*math.sin(math.pi*tt))
        try:
            co = find_coeffs(dst, [(0,0),(0,strip.height),(strip.width,strip.height),(strip.width,0)])
        except Exception:
            continue
        a = np.asarray(strip.convert("RGBA")).astype(np.float32); a[..., :3] *= sh
        st = Image.fromarray(a.clip(0,255).astype(np.uint8), "RGBA")
        leaf = Image.alpha_composite(leaf, st.transform(
            (WC, HC), Image.PERSPECTIVE, co, resample=Image.BICUBIC, fillcolor=(0,0,0,0)))
    fr = Image.alpha_composite(fr, leaf).convert("RGB"); spine_shadow(fr); fr.save(path)

# ---------------- 4. build ----------------
def ease(x): return 0.5 - 0.5*math.cos(math.pi*x)

def build_frames(HOLD=16, TURN=18):
    os.makedirs(FRAMES, exist_ok=True)
    for f in os.listdir(FRAMES): os.remove(os.path.join(FRAMES, f))
    st = stops_list(); fi = 0
    for s in range(len(st)):
        left, right = st[s]
        for _ in range(HOLD):
            render_static(left, right, f"{FRAMES}/f{fi:04d}.png"); fi += 1
        if s < len(st)-1:
            nl, nr = st[s+1]
            front = seq[right] if right is not None else seq[nl]
            back = seq[nl] if nl is not None else (seq[right] if right is not None else seq[0])
            for k in range(1, TURN):
                render_turn(left, nr, front, back, ease(k/TURN), f"{FRAMES}/f{fi:04d}.png"); fi += 1
    return fi

def to_mp4():
    subprocess.run(["ffmpeg","-y","-framerate","30","-i",f"{FRAMES}/f%04d.png",
        "-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart","-crf","23",
        "-vf","scale=trunc(iw/2)*2:trunc(ih/2)*2", OUT_MP4], check=True)

def build_video():
    render_pages(); setup(); n = build_frames(); to_mp4()
    print(f"frame={n} mp4={OUT_MP4} WxH={WC}x{HC}")

if __name__ == "__main__":
    build_video()
