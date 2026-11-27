#!/usr/bin/env python3
"""Fetch CISA KEV entries added in a date range, plus each CVE's official record.

Usage:
  python3 fetch_kev.py --month 2026-10 --out WORKDIR
  python3 fetch_kev.py --start 2026-10-01 --end 2026-10-15 --out WORKDIR

Writes WORKDIR/raw.json (one object per CVE, sorted by dateAdded) and prints a
compact digest to stdout. Standard library only.
"""
import argparse, calendar, json, os, sys, urllib.request, concurrent.futures as cf

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
CVE_API = "https://cveawg.mitre.org/api/cve/{}"
UA = {"User-Agent": "kev-report/1.0"}


def get(url, timeout=30):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()


def versions(aff):
    out = []
    for v in aff.get("versions", []):
        s = v.get("version", "")
        if v.get("lessThan"):
            s += " <" + v["lessThan"]
        if v.get("lessThanOrEqual"):
            s += " <=" + v["lessThanOrEqual"]
        out.append(f"{s} ({v.get('status', '')})")
    return out


def cve_record(cve_id):
    try:
        r = json.loads(get(CVE_API.format(cve_id)))
    except Exception as e:  # network / 404: keep going, flag it
        return {"error": str(e)}
    cna = r.get("containers", {}).get("cna", {})
    return {
        "description": next((d["value"] for d in cna.get("descriptions", []) if d.get("lang", "en").startswith("en")), ""),
        "affected": [{"vendor": a.get("vendor"), "product": a.get("product"), "versions": versions(a)}
                     for a in cna.get("affected", [])],
        "solutions": [x["value"] for x in cna.get("solutions", [])],
        "workarounds": [x["value"] for x in cna.get("workarounds", [])],
        "references": [x["url"] for x in cna.get("references", [])][:8],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", help="YYYY-MM")
    ap.add_argument("--start", help="YYYY-MM-DD (inclusive)")
    ap.add_argument("--end", help="YYYY-MM-DD (inclusive)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.month:
        y, m = map(int, a.month.split("-"))
        start, end = f"{y:04d}-{m:02d}-01", f"{y:04d}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}"
    elif a.start and a.end:
        start, end = a.start, a.end
    else:
        sys.exit("give --month or --start/--end")
    os.makedirs(a.out, exist_ok=True)

    kev = json.loads(get(KEV_URL, 60))
    rows = [v for v in kev["vulnerabilities"] if start <= v["dateAdded"][:10] <= end]
    rows.sort(key=lambda v: (v["dateAdded"], v["cveID"]))
    with cf.ThreadPoolExecutor(8) as ex:
        recs = list(ex.map(lambda v: cve_record(v["cveID"]), rows))

    out = []
    for v, rec in zip(rows, recs):
        notes = [n.strip() for n in v.get("notes", "").split(";")]
        vendor_links = [n for n in notes if n.startswith("http") and "cisa.gov" not in n and "nvd.nist.gov" not in n]
        out.append({
            "dateAdded": v["dateAdded"][:10], "cveID": v["cveID"], "vendor": v["vendorProject"],
            "product": v["product"], "name": v["vulnerabilityName"], "kev_description": v["shortDescription"],
            "dueDate": v["dueDate"], "ransomware": v.get("knownRansomwareCampaignUse") == "Known",
            "cwes": v.get("cwes", []), "vendor_advisories": vendor_links, "cve_record": rec,
            "needs_vendor_lookup": not rec.get("solutions") and not any(
                "<" in s for af in rec.get("affected", []) for s in af["versions"]),
        })
    meta = {"range_start": start, "range_end": end, "catalog_version": kev.get("catalogVersion"),
            "catalog_released": kev.get("dateReleased"), "count": len(out)}
    json.dump({"meta": meta, "items": out}, open(os.path.join(a.out, "raw.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print(json.dumps(meta, ensure_ascii=False))
    if end > (kev.get("dateReleased") or "")[:10]:
        print(f"NOTE: range end {end} is after catalog release {kev.get('dateReleased')}; later additions not included")
    for it in out:
        r = it["cve_record"]
        print(f"=== {it['dateAdded']} {it['cveID']} | {it['vendor']} {it['product']}"
              f"{' | RANSOMWARE' if it['ransomware'] else ''}{' | NEEDS_VENDOR_LOOKUP' if it['needs_vendor_lookup'] else ''}")
        print("  KEV:", it["kev_description"][:400])
        for af in r.get("affected", []):
            print(f"  AFF: {af['vendor']} / {af['product']}: {', '.join(af['versions'])[:400]}")
        for s in r.get("solutions", [])[:1]:
            print("  FIX:", s[:400].replace("\n", " "))
        for w in r.get("workarounds", [])[:1]:
            print("  WORKAROUND:", w[:300].replace("\n", " "))
        if r.get("error"):
            print("  CVE RECORD ERROR:", r["error"])
        print("  ADVISORY:", " ; ".join(it["vendor_advisories"][:3]))


if __name__ == "__main__":
    main()
