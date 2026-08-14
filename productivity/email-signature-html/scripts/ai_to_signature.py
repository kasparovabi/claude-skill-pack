#!/usr/bin/env python3
"""
AI/PDF imza tasarımından parça (logo, sosyal şerit) kesme + email-optimize.
Kullanım: incele→bbox/renk çıkar→kes→trim→optimize. Adımları görevine göre uyarla.
Gerektirir: PyMuPDF (fitz), Pillow.  pip install pymupdf pillow

Notlar:
- .ai / .ps dosyaları genelde PDF-1.x; doğrudan fitz.open ile açılır (önce .pdf kopyala).
- Türkçe-güvenli HTML için ent() fonksiyonunu kullan (tüm non-ASCII → numeric entity).
- Logoyu hosted HTTPS URL'e yükle (base64 KULLANMA). Test için tmpfiles.org örneği altta.
"""
import sys, os
import fitz                      # PyMuPDF
from PIL import Image, ImageOps


def inspect(pdf_path):
    """Metin span'leri (bbox/font/size/#hex), dolgu renkleri, dikey ayraç çizgisi."""
    d = fitz.open(pdf_path); p = d[0]
    print("sayfa:", d.page_count, "| pt:", p.rect,
          "| cm:", round(p.rect.width/28.346,1), "x", round(p.rect.height/28.346,1))
    print("--- TEXT SPANS ---")
    for b in p.get_text("dict")["blocks"]:
        if b.get("type") != 0: continue
        for l in b["lines"]:
            for s in l["spans"]:
                x0,y0,x1,y1 = s["bbox"]
                print(f"[{x0:6.1f},{y0:6.1f},{x1:6.1f},{y1:6.1f}] {s['font']:24s} "
                      f"{s['size']:5.1f} #{s['color']:06x} {s['text']!r}")
    fills = set()
    for dr in p.get_drawings():
        if dr.get("fill"): fills.add(tuple(round(c,3) for c in dr["fill"]))
        r = dr["rect"]
        if r.height > 80 and r.width < 12:           # dikey ayraç çizgisi adayı
            print("AYRAC cizgi x:", round(r.x0,1), "y:", round(r.y0,1), round(r.y1,1))
    print("dolgu renkleri (RGB 0-1):", fills)


def cut(pdf_path, clip, out_png, scale=8, pad=12):
    """Belirtilen clip bölgesini yüksek çözünürlükte, şeffaf, otomatik-trim'li kes."""
    d = fitz.open(pdf_path); p = d[0]
    raw = out_png + ".raw.png"
    pix = p.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=fitz.Rect(*clip), alpha=True)
    pix.save(raw)
    im = Image.open(raw).convert("RGBA")
    bb = im.split()[3].getbbox()                     # alfa kanalına göre içerik sınırı
    im = im.crop(bb)
    im = ImageOps.expand(im, border=(pad,pad,pad,pad), fill=(0,0,0,0))
    im.save(out_png)
    os.remove(raw)
    print("kesildi:", out_png, im.size)
    return im.size


def webify(src_png, out_png, target_w):
    """Email için optimize: gösterim genişliğinin ~2 katı yeterli (retina)."""
    im = Image.open(src_png).convert("RGBA")
    w, h = im.size
    im.resize((target_w, round(h*target_w/w)), Image.LANCZOS).save(out_png, optimize=True)
    print("webify:", out_png, Image.open(out_png).size, os.path.getsize(out_png), "B")


def ent(s):
    """Türkçe-güvenli: tüm non-ASCII'yi numeric HTML entity'e çevir (mojibake-proof)."""
    s = s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    return s.encode("ascii", "xmlcharrefreplace").decode("ascii")


# tmpfiles.org'a yükleme (geçici! birkaç gün sonra silinir, kalıcıda kurum sunucusu):
#   curl -sS -F "file=@logo_web.png" https://tmpfiles.org/api/v1/upload
#   dönen url'deki /<id>/ kısmını /dl/<id>/ yap → direkt img src linki
#   curl ile 200 + image/png doğrula.

if __name__ == "__main__":
    if len(sys.argv) > 1:
        inspect(sys.argv[1])
    else:
        print(__doc__)
