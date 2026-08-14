# -*- coding: utf-8 -*-
# Fotoğraflı kişi/veri listesi tablosu (tek sayfa). Solda portre, renk şeridi, zebra satır.
# Portreler /tmp/portraits/<no>.jpg (240px kare, önceden indirilip kırpılmış olmalı).
# Sütun X konumlarını ve genişlikleri taşma olmayacak şekilde ayarla (bkz SKILL.md taşma notu).
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

pdfmetrics.registerFont(TTFont("Arial","/System/Library/Fonts/Supplemental/Arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold","/System/Library/Fonts/Supplemental/Arial Bold.ttf"))

W,H=A4
OUT=os.path.expanduser("~/Downloads/Liste.pdf")
c=canvas.Canvas(OUT,pagesize=A4)

LACI=colors.HexColor("#1F3A5F"); GRI=colors.HexColor("#444444")
ACIKGRI=colors.HexColor("#777777"); ZEBRA=colors.HexColor("#F4F6F9")
CIZGI=colors.HexColor("#DCE2EA")
RENK1=colors.HexColor("#C0392B"); RENK2=colors.HexColor("#8E9BA8")

# (no, ad, alt_satir, sutun3, sutun4, sutun5, kategori_renk, son_sutun)
data=[
 ("1","Ad Soyad","1881–1938 • Etiket","29 Ekim 1923","10 Kasım 1938","15 yıl",RENK1,"Önceki görev kısa"),
 ("2","İkinci Kişi","1884–1973 • Etiket","11 Kasım 1938","22 Mayıs 1950","11 yıl",RENK2,"Genelkurmay Başkanı"),
]

y=H-16*mm
c.setFillColor(LACI); c.setFont("Arial-Bold",19); c.drawString(16*mm,y,"Liste Başlığı")
y-=6.5*mm
c.setFillColor(ACIKGRI); c.setFont("Arial",9.5); c.drawString(16*mm,y,"Alt başlık / kapsam.")
y-=3.5*mm
c.setStrokeColor(LACI); c.setLineWidth(1.2); c.line(16*mm,y,W-16*mm,y)
y-=7*mm

# Sütun X (taşma yok: aralar ~22mm, sağ sınır W-11mm)
X_BAR=14*mm; X_FOTO=17*mm; FOTO=15.5*mm
X_NO=35*mm; X_AD=41*mm; X_C3=95*mm; X_C4=119*mm; X_C5=143*mm; X_SON=164*mm
TBL_L=13*mm; TBL_R=W-11*mm

c.setFillColor(LACI); c.setFont("Arial-Bold",8)
c.drawString(X_AD,y,"İsim"); c.drawString(X_C3,y,"Başlangıç")
c.drawString(X_C4,y,"Bitiş"); c.drawString(X_C5,y,"Süre"); c.drawString(X_SON,y,"Önceki Görev")
y-=2*mm
c.setStrokeColor(CIZGI); c.setLineWidth(0.6); c.line(TBL_L,y,TBL_R,y)

rowh=18.6*mm
for idx,(no,ad,alt,c3,c4,c5,prenk,son) in enumerate(data):
    top=y
    if idx%2==1:
        c.setFillColor(ZEBRA); c.rect(TBL_L,top-rowh,TBL_R-TBL_L,rowh,fill=1,stroke=0)
    c.setFillColor(prenk); c.rect(X_BAR,top-rowh+2*mm,2*mm,rowh-4*mm,fill=1,stroke=0)
    fp=f"/tmp/portraits/{no}.jpg"
    fy=top-rowh+(rowh-FOTO)/2
    if os.path.exists(fp):
        c.drawImage(fp,X_FOTO,fy,FOTO,FOTO)
        c.setStrokeColor(colors.HexColor("#C0C8D2")); c.setLineWidth(0.5)
        c.rect(X_FOTO,fy,FOTO,FOTO,fill=0,stroke=1)
    yc=top-7*mm
    c.setFillColor(prenk); c.setFont("Arial-Bold",11); c.drawString(X_NO,yc,no)
    c.setFillColor(LACI); c.setFont("Arial-Bold",10.5); c.drawString(X_AD,yc,ad)
    c.setFillColor(ACIKGRI); c.setFont("Arial",7.5); c.drawString(X_AD,yc-4.2*mm,alt)
    c.setFillColor(GRI); c.setFont("Arial",7.8)
    c.drawString(X_C3,yc,c3); c.drawString(X_C4,yc,c4); c.drawString(X_C5,yc,c5)
    c.setFont("Arial",7.2); c.drawString(X_SON,yc,son)
    c.setStrokeColor(CIZGI); c.setLineWidth(0.5); c.line(TBL_L,top-rowh,TBL_R,top-rowh)
    y=top-rowh

y-=6*mm
c.setFillColor(ACIKGRI); c.setFont("Arial",7.3)
c.drawString(16*mm,y,"Kaynak: ... Portreler Wikimedia Commons. Tarihler 2026 itibarıyladır.")
c.showPage(); c.save()
print("PDF:",OUT)
