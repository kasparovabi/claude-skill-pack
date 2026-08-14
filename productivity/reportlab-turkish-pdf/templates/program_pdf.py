import os
# -*- coding: utf-8 -*-
# Program / takvim / gün-gün plan PDF'i. Sol renk şeritli, iki satırlı kutular.
# Kopyala ve gunler[] verisini + başlıkları değiştir. python3 ile çalıştır (heredoc DEĞİL).
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont("Arial","/System/Library/Fonts/Supplemental/Arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold","/System/Library/Fonts/Supplemental/Arial Bold.ttf"))

W,H=A4
OUT=os.path.expanduser("~/Downloads/Program.pdf")
c=canvas.Canvas(OUT,pagesize=A4)

TURUNCU=colors.HexColor("#E8821E"); YESIL=colors.HexColor("#2E8B57")
KIRMIZI=colors.HexColor("#C0392B"); LACI=colors.HexColor("#1F3A5F")
GRI=colors.HexColor("#444444")
ML=18*mm; MR=18*mm
def line(y): c.setStrokeColor(colors.HexColor("#DDDDDD")); c.line(ML,y,W-MR,y)

y=H-22*mm
c.setFillColor(LACI); c.setFont("Arial-Bold",19)
c.drawString(ML,y,"Başlık Buraya — Tam Türkçe Yaz (ı ş ç ğ ö ü)")
y-=8*mm
c.setFillColor(GRI); c.setFont("Arial",10.5)
c.drawString(ML,y,"Alt başlık / tarih aralığı / hedef.")
y-=4*mm; line(y); y-=8*mm

# (no, tarih, renk, konu_başlığı, açıklama1, açıklama2)
gunler=[
 ("GÜN 1","12 Haziran Cuma",KIRMIZI,"ÖLÇÜM",
   "Birinci açıklama satırı.","İkinci açıklama satırı."),
 ("GÜN 2","13 Haziran Cumartesi",YESIL,"ÇÖZÜMLEME",
   "Birinci açıklama.","İkinci açıklama."),
]

def gun_kutu(g):
    global y
    no,tar,col,bas,s1,s2=g
    kh=27*mm
    if y-kh < 20*mm:
        c.showPage(); y=H-22*mm
    top=y
    c.setFillColor(col); c.rect(ML,top-kh+4*mm,2.8*mm,kh-4*mm,fill=1,stroke=0)
    c.setFillColor(col); c.setFont("Arial-Bold",10.5)
    c.drawString(ML+6*mm,top-1*mm,no+"   "+tar)
    c.setFillColor(LACI); c.setFont("Arial-Bold",11.5)
    c.drawString(ML+6*mm,top-7.5*mm,bas)
    c.setFillColor(GRI); c.setFont("Arial",9)
    c.drawString(ML+6*mm,top-13.5*mm,s1)
    c.drawString(ML+6*mm,top-18.5*mm,s2)
    y=top-kh
    line(y+3*mm)

for g in gunler:
    gun_kutu(g)

c.showPage(); c.save()
print("PDF:",OUT)
