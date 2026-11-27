# kev-report：CISA KEV 漏洞處理報告

把 CISA「已知遭利用漏洞（KEV）」清單中，指定月份或日期區間新增的 CVE，整理成繁體中文 PDF 報告（A4 橫式）。每筆列出：KEV 公告日、CVE、產品、漏洞類型、**怎麼確認**、**怎麼修正**，並依「一般企業設備／網站與伺服器元件／AI、VoIP、OT」分類，標出勒索軟體利用與已停止維護的項目。

## 怎麼用

安裝後在 Claude Code 直接用中文問即可，例如：

- 「10月的KEV報告」
- 「KEV 11/1-11/15 有哪些」
- 「整理成 pdf 報告，要有怎麼確認、怎麼修正」
- 「幫報告加上 "XX部門" 浮水印」

Claude 會：抓 CISA KEV 與 CVE.org 資料 → 查原廠公告補修補版本（查不到會寫「以原廠公告為準」，不會猜）→ 產生 `CISA_KEV_<區間>_漏洞處理報告.pdf` → 截圖檢查排版。

## 需求

- Python 3.10 以上，且能連到 cisa.gov、cveawg.mitre.org 與各原廠網站。
- 第一次使用時會自動建立 `~/.cache/kev-report-venv`，並安裝 `reportlab`、`pypdfium2`、`pypdf`。
- 中文字型：優先使用 Windows 微軟正黑體（WSL 可自動讀到），其次 Noto Sans CJK；都沒有時改用內建字型。純 Linux 建議安裝 `fonts-noto-cjk`。

## 內容

- `skills/kev-report/SKILL.md`：工作流程與撰寫規則
- `scripts/fetch_kev.py`：抓取 KEV 與 CVE 記錄
- `scripts/render_pdf.py`：產生 PDF
- `scripts/watermark.py`：為任何 PDF 加斜向浮水印
- `examples/2026-11.json`：完整範例（39 筆）

## 注意

「KEV 公告日」是 CISA 加入目錄的日期，不是原廠發布日期。報告中的截止日（dueDate）是美國聯邦機關的期限，僅供急迫性參考。執行修補前請以原廠最新公告為準。

## 授權

Apache License 2.0，詳見 `LICENSE`。Copyright 2026 bellehsu。
