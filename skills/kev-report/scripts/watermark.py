#!/usr/bin/env python3
"""Add a diagonal, semi-transparent text watermark to every page of a PDF.

Usage: watermark.py <input.pdf> <output.pdf> "<watermark text>"
Needs: pypdf, reportlab (same venv as render_pdf.py).
Landscape pages get 3 lines, portrait pages 2; font size shrinks so text stays on the page.
"""
import glob
import io
import os
import sys

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


def register_font():
    """Prefer Microsoft JhengHei Bold (WSL/Windows), then Noto CJK, else built-in CID font."""
    cands = ["/mnt/c/Windows/Fonts/msjhbd.ttc", "C:/Windows/Fonts/msjhbd.ttc",
             "/mnt/c/Windows/Fonts/msjh.ttc", "C:/Windows/Fonts/msjh.ttc",
             "/System/Library/Fonts/PingFang.ttc"]
    for pat in ["/usr/share/fonts/**/NotoSansCJK-Bold.ttc", "/usr/share/fonts/**/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/**/NotoSansCJKtc-Bold.otf", "/usr/share/fonts/**/NotoSansCJKtc-Regular.otf"]:
        cands += glob.glob(pat, recursive=True)
    for f in cands:
        if os.path.exists(f):
            try:
                pdfmetrics.registerFont(TTFont("WM", f, subfontIndex=0))
                return "WM"
            except Exception:
                continue
    pdfmetrics.registerFont(UnicodeCIDFont("MSung-Light"))
    return "MSung-Light"


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    src, dst, text = sys.argv[1], sys.argv[2], sys.argv[3]
    font = register_font()
    w = PdfWriter(clone_from=src)
    for page in w.pages:
        W, H = float(page.mediabox.width), float(page.mediabox.height)
        n = 3 if W >= H else 2
        base = pdfmetrics.stringWidth(text, font, 56)
        fs = min(56, min(0.62 * (W * W + H * H) ** 0.5, 0.85 * W / 0.866, 0.95 * H / n) * 56 / base)
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(W, H))
        c.setFillColor(Color(0.5, 0.5, 0.5, alpha=0.13))
        c.setFont(font, fs)
        for k in range(n):
            c.saveState()
            c.translate(W / 2, H * (k + 0.5) / n)
            c.rotate(30)
            c.drawCentredString(0, 0, text)
            c.restoreState()
        c.save()
        buf.seek(0)
        page.merge_page(PdfReader(buf).pages[0])
    w.write(dst)
    print(f"written {dst} ({len(w.pages)} pages)")


if __name__ == "__main__":
    main()
