---
name: kev-report
description: Use when the user asks for a CISA KEV (Known Exploited Vulnerabilities) report, list or PDF for a month or date range, e.g. "10月的KEV報告", "KEV 11/1-11/15 有哪些", "整理成pdf報告 怎麼確認 怎麼修正", or wants to know which actively exploited CVEs were added recently and how to check/fix them.
---

# CISA KEV 漏洞處理報告

Produces a Traditional Chinese PDF (landscape A4) listing every CVE that CISA added to KEV in a date range. Each row has these columns: KEV 公告日 | CVE | 產品 | 漏洞類型 | 怎麼確認 | 怎麼修正.

Scripts do the deterministic parts (fetching, rendering). You do the research and the writing.

## Workflow

Let `SK=<this skill's base directory>` (the "Base directory for this skill" path shown when the skill loads; never assume `~/.claude/skills/...`, because a plugin install lives elsewhere) and `W=<scratchpad>/kev-<range>`.

1. **Parse the range.** "10月" means `--month 2026-10`; "11/1-11/15" means `--start 2026-11-01 --end 2026-11-15`. Use the current year unless the user names one.
2. **Fetch.** Run `python3 $SK/scripts/fetch_kev.py --month YYYY-MM --out $W`. It writes `$W/raw.json` and prints a digest for each CVE: KEV description, affected versions from CVE.org, fixes, workarounds, vendor advisory links, and the flags `RANSOMWARE` and `NEEDS_VENDOR_LOOKUP`.
   - If the digest says the range end is after the catalog release, tell the user that later additions are not included yet.
3. **Fill gaps.** For each `NEEDS_VENDOR_LOOKUP` entry, and any entry whose fixed version is unclear, read the vendor advisory link. Use the web-fetch agent or `curl`. Cisco advisories have readable HTML. These pages can't be fetched automatically: SonicWall PSIRT, Ivanti hub (both JS shells), nvd.nist.gov (shell), and BeyondTrust (403). For these, first check the CVE record's `unaffected` version list. If it has nothing useful, write "以原廠公告為準" instead of guessing. Hand all lookups to a single web-fetch agent so they run in parallel.
   - Never invent version numbers. If you can't find one, write `修補版本請以原廠 <advisory id> 為準` and add a line to `notes`.
4. **Write `$W/report.json`** using the schema below. `examples/2026-11.json` is a complete real example (39 CVEs). Match its tone and level of detail.
5. **Render.** Run `~/.cache/kev-report-venv/bin/python $SK/scripts/render_pdf.py $W/report.json <output.pdf>`.
   - The renderer needs reportlab. If no venv exists yet, create one: `python3 -m venv ~/.cache/kev-report-venv && ~/.cache/kev-report-venv/bin/pip install -q reportlab pypdfium2 pypdf`.
   - Save the PDF in the user's working directory as `CISA_KEV_<range>_漏洞處理報告.pdf`.
6. **Verify visually.** Render 2 or more pages to PNG with pypdfium2 and Read them. Check for tofu boxes (□), broken tables, and that the CVE count matches `raw.json`.
7. **Watermark (only when the user asks).** Run `~/.cache/kev-report-venv/bin/python $SK/scripts/watermark.py <in.pdf> <out.pdf> "<text>"`. Write to a new file named `<name>_浮水印.pdf` and keep the original. It works on any PDF, landscape or portrait. If `pypdf` is missing, `pip install pypdf` into the same venv. Render one page to PNG and check that the text stays on the page.
   - To merge several reports, use pypdf `PdfWriter.append()` and add one bookmark per file with `add_outline_item(title=..., page_number=...)`.

## report.json schema

```json
{
  "range_start": "2026-10-01", "range_end": "2026-10-31",
  "catalog_version": "<from raw.json meta>", "report_date": "<today>",
  "title": "(optional; default: CISA KEV 新增漏洞處理報告（range）)",
  "summary": ["3-5 bullets; <b>bold</b> allowed: ransomware items, edge devices, EoL/no-patch items, suggested order"],
  "notes": ["range-specific caveats, e.g. advisories that could not be read"],
  "sections": [
    {"title": "一、一般企業常見設備與軟體（建議優先處理）", "rows": [
      {"date": "2026/11/18", "cves": ["CVE-2024-10441"], "product": "Synology DSM / BeeStation (BSM)",
       "vuln_type": "輸出編碼不當，可遠端執行程式碼",
       "check": "where to see the version (UI path or command) + affected version ranges + preconditions (e.g. only if clustered / SAML enabled)",
       "fix": "exact fixed versions + workaround if no patch yet + hardening tip",
       "ransomware": true}
    ]}
  ]
}
```

Fields are plain text, and `\n` makes a line break. Only `summary` accepts markup.

## Writing rules

- **Sections, in this order:** 一、一般企業常見設備與軟體（建議優先處理）, which covers NAS, virtualization, Office/browsers, VPN/firewall/mail gateways, OS. 二、網站、伺服器與開發元件. 三、AI、VoIP、OT 與特定產業. Skip a section if it has no rows.
- **Merging rows:** put CVEs for the same product from the same advisory in one row (`cves` list), e.g. 5 Mitel CVEs → 1 row.
- **怎麼確認:** give the concrete place to read the version (a UI path, or a command such as `ssh -V`, `pip show x`, `cpinfo -y all`, `wp core version`), the affected range, and any precondition that narrows exposure.
- **怎麼修正:** give the fixed version(s). Add the workaround if one exists. Mark EoL products 沒有修補 → 移除/替換.
- **Old CVEs:** for entries from 2023 or 2024, say most devices are already past the affected versions.
- **Language:** Traditional Chinese with Taiwan IT terms (修補, 韌體, 弱點/漏洞, 設定).
- **Glyphs:** avoid ≤ ≥ ⚠, because Windows CJK fonts lack them. The renderer replaces them, but write `<=` yourself.

## Common mistakes

| Mistake | Fix |
|---|---|
| Reporting vendor advisory date as 公告日 | Column is KEV dateAdded; note says so |
| Guessing a fixed version from the "affected <= X" range | Only state versions you read in the CVE record or advisory |
| Dropping CVEs when merging rows | Total `cves` count must equal `raw.json` meta.count |
| Treating the deadline (dueDate) as binding | It is the US federal deadline; mention only as an urgency hint |
