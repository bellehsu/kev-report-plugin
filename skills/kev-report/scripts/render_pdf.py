#!/usr/bin/env python3
"""Render a KEV report JSON (see SKILL.md for schema) to a landscape A4 PDF.

Usage: python render_pdf.py report.json output.pdf     (needs reportlab)
"""
import glob, json, os, subprocess, sys
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont


def register_fonts():
    """Prefer Microsoft JhengHei (WSL/Windows), then any Noto CJK TC .ttc, else built-in CID font."""
    cands = [("/mnt/c/Windows/Fonts/msjh.ttc", "/mnt/c/Windows/Fonts/msjhbd.ttc"),
             ("C:/Windows/Fonts/msjh.ttc", "C:/Windows/Fonts/msjhbd.ttc")]
    for pat in ["/usr/share/fonts/**/NotoSansCJK-Regular.ttc", "/usr/share/fonts/**/NotoSansCJKtc-Regular.otf"]:
        for f in glob.glob(pat, recursive=True):
            cands.append((f, f.replace("Regular", "Bold")))
    for reg, bold in cands:
        if os.path.exists(reg):
            try:
                pdfmetrics.registerFont(TTFont("CJK", reg, subfontIndex=0))
                pdfmetrics.registerFont(TTFont("CJKB", bold if os.path.exists(bold) else reg, subfontIndex=0))
                return
            except Exception:
                continue
    pdfmetrics.registerFont(UnicodeCIDFont("MSung-Light"))
    pdfmetrics._fonts["CJK"] = pdfmetrics.getFont("MSung-Light")
    pdfmetrics._fonts["CJKB"] = pdfmetrics.getFont("MSung-Light")


register_fonts()
pdfmetrics.registerFontFamily("CJK", normal="CJK", bold="CJKB", italic="CJK", boldItalic="CJKB")

NAVY, GREY, LINE = colors.HexColor("#1F3A5F"), colors.HexColor("#F2F4F7"), colors.HexColor("#D0D5DD")
sTitle = ParagraphStyle("t", fontName="CJKB", fontSize=22, leading=30, textColor=NAVY)
sSub = ParagraphStyle("s", fontName="CJK", fontSize=11, leading=17, textColor=colors.HexColor("#475467"))
sH1 = ParagraphStyle("h1", fontName="CJKB", fontSize=14, leading=20, textColor=NAVY, spaceBefore=6, spaceAfter=6)
sBody = ParagraphStyle("b", fontName="CJK", fontSize=10, leading=16)
sCell = ParagraphStyle("c", fontName="CJK", fontSize=8, leading=11.5, wordWrap="CJK")
sCellB = ParagraphStyle("cb", parent=sCell, fontName="CJKB")
sHead = ParagraphStyle("hd", parent=sCell, fontName="CJKB", textColor=colors.white)
COLW = [20*mm, 29*mm, 39*mm, 43*mm, 72*mm, 66*mm]

# Glyphs missing from JhengHei / CJK fonts -> render as tofu boxes. Normalise them.
REPL = {"≤": "<=", "≥": ">=", "⚠": "", "✓": "V", "✗": "X", "–": "-", "—": "-"}


def clean(t):
    for k, v in REPL.items():
        t = t.replace(k, v)
    return t


def e(t):  # plain text cell -> escaped Paragraph markup
    return escape(clean(t)).replace("\n", "<br/>")


def P(t, st=sCell):
    return Paragraph(t, st)


def table(rows):
    data = [[P(h, sHead) for h in ["KEV 公告日", "CVE", "產品", "漏洞類型", "怎麼確認", "怎麼修正"]]]
    st = []
    for i, r in enumerate(rows, 1):
        prod = e(r["product"]) + ('<br/><font color="#B42318"><b>【已被勒索軟體利用】</b></font>' if r.get("ransomware") else "")
        data.append([P(e(r["date"])), P("<br/>".join(map(e, r["cves"])), sCellB), P(prod, sCellB),
                     P(e(r["vuln_type"])), P(e(r["check"])), P(e(r["fix"]))])
        if i % 2 == 0:
            st.append(("BACKGROUND", (0, i), (-1, i), GREY))
    t = Table(data, colWidths=COLW, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("GRID", (0, 0), (-1, -1), 0.4, LINE)] +
                          [(k, (0, 0), (-1, -1), 4) for k in ("TOPPADDING", "BOTTOMPADDING", "LEFTPADDING", "RIGHTPADDING")] + st))
    return t


def main(src, out):
    R = json.load(open(src, encoding="utf-8"))
    rng = f"{R['range_start'].replace('-', '/')} - {R['range_end'].replace('-', '/')}"
    title = R.get("title") or f"CISA KEV 新增漏洞處理報告（{rng}）"
    n = sum(len(r["cves"]) for s in R["sections"] for r in s["rows"])

    def footer(c, doc):
        c.saveState(); c.setFont("CJK", 8); c.setFillColor(colors.HexColor("#667085"))
        c.drawString(14*mm, 8*mm, clean(title)); c.drawRightString(landscape(A4)[0] - 14*mm, 8*mm, f"第 {doc.page} 頁")
        c.restoreState()

    story = [P(e(title), sTitle),
             P(e(f"資料範圍：{rng}（KEV 目錄版本 {R.get('catalog_version', '')}）　｜　共 {n} 筆 CVE　｜　報告日期：{R.get('report_date', '')}"), sSub),
             Spacer(1, 8), P("重點摘要", sH1)]
    story += [P("• " + clean(s), sBody) for s in R.get("summary", [])]  # summary may contain <b>
    story += [Spacer(1, 6), P("資料來源與說明", sH1)]
    notes = ["漏洞清單：CISA KEV 官方 JSON feed（https://www.cisa.gov/known-exploited-vulnerabilities-catalog）。「KEV 公告日」是 CISA 加入目錄的日期，不是原廠發布公告的日期。",
             "受影響和修補版本：CVE.org 官方記錄與各原廠安全公告。執行修補前請以原廠最新公告為準。",
             "每筆在 NVD 的詳細資料：https://nvd.nist.gov/vuln/detail/<CVE 編號>"] + R.get("notes", [])
    story += [P("• " + e(x), sBody) for x in notes] + [PageBreak()]
    for s in R["sections"]:
        if not s["rows"]:
            continue
        story += [P(e(f"{s['title']}（{sum(len(r['cves']) for r in s['rows'])} 筆）"), sH1), table(s["rows"]), Spacer(1, 10)]

    SimpleDocTemplate(out, pagesize=landscape(A4), leftMargin=14*mm, rightMargin=14*mm, topMargin=12*mm,
                      bottomMargin=14*mm, title=clean(title), author="MIS").build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"written {out} ({n} CVEs)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
