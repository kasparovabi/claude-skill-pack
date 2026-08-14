# -*- coding: utf-8 -*-
"""
docx tablo KAYMASINI önleyen yardımcılar (python-docx).

Word, python-docx'in verdiği hücre genişliklerini yok sayar; sütunlar kayar.
lock_table() üç ayarı BİRLİKTE uygular (fixed layout + tblW + tblGrid/tcW) ki
Word tam olarak verdiğin ölçülere uysun.

Kullanım:
    from docx import Document
    from docx.shared import Mm
    doc = Document()
    USABLE = 184.0  # A4 210 - sol(13) - sağ(13)
    t = doc.add_table(rows=3, cols=2); t.style = "Table Grid"
    # ...hücreleri doldur...
    lock_table(t, [USABLE*0.25, USABLE*0.75])

Doğrulama (göndermeden önce):
    soffice --headless --convert-to pdf --outdir /tmp /tmp/belge.docx
    # sonra fitz ile PNG'e çevir + vision_analyze ile kayma/taşma kontrol et
"""
from docx.shared import Mm
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.enum.table import WD_TABLE_ALIGNMENT

MM_TO_TWIP = 56.6929  # 1mm = 56.6929 dxa(twip)


def _shade(cell, hexcolor):
    """Hücreye zemin rengi ver (başlık/zebra için). hexcolor: 'EEF2F6' gibi."""
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:fill"), hexcolor)
    tcPr.append(sh)


def lock_table(t, widths_mm):
    """Word'de kaymayı önleyen tam fix: fixed layout + tblW(toplam) + gridCol + tcW."""
    total = sum(widths_mm)
    tblPr = t._tbl.tblPr

    # 1) fixed layout — Word'ün otomatik genişlik hesabını kapat
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)

    # 2) toplam tablo genişliği
    tblW = OxmlElement("w:tblW")
    tblW.set(qn("w:w"), str(int(total * MM_TO_TWIP)))
    tblW.set(qn("w:type"), "dxa")
    tblPr.append(tblW)

    # 3a) tblGrid sütun genişlikleri
    grid = t._tbl.find(qn("w:tblGrid"))
    if grid is not None:
        for i, gc in enumerate(grid.findall(qn("w:gridCol"))):
            if i < len(widths_mm):
                gc.set(qn("w:w"), str(int(widths_mm[i] * MM_TO_TWIP)))

    # 3b) her hücreye tcW (Word bunu da ister; cell.width tek başına yetmez)
    for row in t.rows:
        for i, c in enumerate(row.cells):
            if i < len(widths_mm):
                c.width = Mm(widths_mm[i])
                tcPr = c._tc.get_or_add_tcPr()
                tcW = tcPr.find(qn("w:tcW"))
                if tcW is None:
                    tcW = OxmlElement("w:tcW")
                    tcPr.append(tcW)
                tcW.set(qn("w:w"), str(int(widths_mm[i] * MM_TO_TWIP)))
                tcW.set(qn("w:type"), "dxa")

    t.alignment = WD_TABLE_ALIGNMENT.CENTER
