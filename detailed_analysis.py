#!/usr/bin/env python3
"""
detailed_analysis.py

Loads current applying CSV + all past CSVs, dedupes by normalized apply_url,
detects applied rows and statuses, prints a formatted terminal report and
writes application_analysis.csv.

Run:
    python detailed_analysis.py
"""
import csv
import os
import sys
import urllib.parse
from collections import defaultdict, Counter
from typing import List, Dict, Tuple

CURRENT_APPLICATIONS_FILE = "new_grad_swe_apply_links_applying.csv"
PAST_DATA_FOLDER = "past_applied_data"
OUTPUT_CSV = "application_analysis.csv"
APPLIED_TRUE = {"TRUE", "YES", "Y", "1"}
STATUS_KEYWORDS = ("appl", "submitted", "interview", "offer", "accepted", "hired")

# --- helpers (same as count script, but packaged here) ---
def load_csv_rows(path: str) -> List[Dict[str, str]]:
    rows = []
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append({(k or "").strip(): (v or "").strip() for k, v in r.items()})
    except Exception as e:
        print(f"Warning: could not read {path}: {e}", file=sys.stderr)
    return rows

def gather_files(current_file: str, past_folder: str) -> List[str]:
    files = []
    if os.path.exists(current_file):
        files.append(current_file)
    if os.path.isdir(past_folder):
        for p in sorted(os.listdir(past_folder)):
            if p.lower().endswith(".csv"):
                files.append(os.path.join(past_folder, p))
    return files

def detect_key_by_names(fieldnames: List[str], candidates: Tuple[str, ...]) -> str:
    low_map = { (h or "").strip().lower(): h for h in fieldnames }
    for cand in candidates:
        if cand in low_map:
            return low_map[cand]
    return ""

def detect_url_key(fieldnames: List[str]) -> str:
    # prefer apply_url-like names
    fn = detect_key_by_names(fieldnames, ("apply_url", "apply-url", "apply url"))
    if fn:
        return fn
    # fallback heuristics
    low_map = { (h or "").strip().lower(): h for h in fieldnames }
    for k_low, orig in low_map.items():
        if "apply" in k_low and ("url" in k_low or "link" in k_low):
            return orig
    for k_low, orig in low_map.items():
        if "url" in k_low or "link" in k_low:
            return orig
    return fieldnames[0] if fieldnames else ""

def strip_tracking(u: str) -> str:
    if not u:
        return ""
    try:
        p = urllib.parse.urlparse(u)
    except Exception:
        return u.strip()
    if not p.query:
        return urllib.parse.urlunparse(p._replace(query=""))
    keep = []
    for k, v in urllib.parse.parse_qsl(p.query, keep_blank_values=True):
        lk = (k or "").lower(); lv = (v or "").lower()
        if lk.startswith("utm_") or "simplify" in lk or "simplify" in lv:
            continue
        keep.append((k, v))
    q = urllib.parse.urlencode(keep)
    out = urllib.parse.urlunparse(p._replace(query=q))
    if not q:
        out = f"{p.scheme}://{p.netloc}{p.path}"
    return out

def norm_url(u: str) -> str:
    u = (u or "").strip()
    try:
        p = urllib.parse.urlparse(u)
        scheme = (p.scheme or "https").lower()
        netloc = (p.netloc or "").lower()
        path = (p.path or "").rstrip("/")
        query = p.query or ""
        return urllib.parse.urlunparse((scheme, netloc, path, "", query, ""))
    except Exception:
        return u.rstrip("/").lower()

# --- load and dedupe ---
def load_all_applications(current_file: str, past_folder: str) -> Dict[str, Dict[str, str]]:
    files = gather_files(current_file, past_folder)
    combined: Dict[str, Dict[str, str]] = {}
    for p in files:
        rows = load_csv_rows(p)
        if not rows:
            continue
        url_key = detect_url_key(list(rows[0].keys()))
        if not url_key:
            continue
        for r in rows:
            raw = r.get(url_key, "").strip()
            if not raw:
                continue
            cleaned = strip_tracking(raw)
            n = norm_url(cleaned)
            # prefer first-seen (current_file should be first in gather_files)
            if n not in combined:
                combined[n] = {k.lower().strip(): v for k, v in r.items()}
    return combined

# --- analysis ---
def analyze(combined: Dict[str, Dict[str, str]]) -> Tuple[Dict, List[Dict[str,str]]]:
    total_unique = len(combined)
    applied_rows = []
    status_counts = defaultdict(int)
    company_counts = Counter()

    for norm_u, r in combined.items():
        # r already lowercased keys
        applied_flag = False
        applied_val = (r.get("applied") or "").strip().upper()
        if applied_val in APPLIED_TRUE:
            applied_flag = True
        if not applied_flag:
            # date applied heuristic
            if (r.get("date applied") or r.get("date_applied") or r.get("date") or "").strip():
                applied_flag = True
        if not applied_flag:
            st = (r.get("status") or "").strip().lower()
            if any(k in st for k in STATUS_KEYWORDS):
                applied_flag = True

        if applied_flag:
            applied_rows.append(r)
            status_val = (r.get("status") or "").strip().lower() or "applied"
            status_counts[status_val] += 1
            company = (r.get("company") or "").strip() or "Unknown"
            company_counts[company] += 1

    total_applied = len(applied_rows)
    interviews = sum(v for k, v in status_counts.items() if "interview" in k or "offer" in k or "hired" in k or "accepted" in k)
    offers = sum(v for k, v in status_counts.items() if "offer" in k or "accepted" in k or "hired" in k)
    ghosted = total_applied - interviews

    interview_rate = (interviews / total_applied * 100) if total_applied else 0.0
    offer_rate = (offers / total_applied * 100) if total_applied else 0.0
    ghosted_rate = (ghosted / total_applied * 100) if total_applied else 0.0

    metrics = {
        "total_unique_rows": total_unique,
        "total_applied": total_applied,
        "interviews": interviews,
        "offers": offers,
        "ghosted": ghosted,
        "interview_rate": interview_rate,
        "offer_rate": offer_rate,
        "ghosted_rate": ghosted_rate,
        "status_counts": dict(status_counts),
        "company_counts": dict(company_counts.most_common(30)),
    }

    return metrics, applied_rows

# --- output ---
def write_analysis_csv(metrics: Dict, out_file: str):
    rows = [
        {"Metric":"Total Unique Rows", "Value": metrics["total_unique_rows"]},
        {"Metric":"Total Applied (detected)", "Value": metrics["total_applied"]},
        {"Metric":"Interviews (incl offers)", "Value": metrics["interviews"]},
        {"Metric":"Offers/Hired", "Value": metrics["offers"]},
        {"Metric":"Ghosted / Pending", "Value": metrics["ghosted"]},
        {"Metric":"Interview Rate (%)", "Value": f"{metrics['interview_rate']:.2f}"},
        {"Metric":"Offer Rate (%)", "Value": f"{metrics['offer_rate']:.2f}"},
        {"Metric":"Ghosted Rate (%)", "Value": f"{metrics['ghosted_rate']:.2f}"},
        {"Metric":"--- Status Breakdown ---", "Value": ""},
    ]
    for k, v in sorted(metrics["status_counts"].items()):
        rows.append({"Metric": f"Status: {k}", "Value": v})
    rows.append({"Metric":"--- Top Companies (by applications) ---", "Value": ""})
    for comp, cnt in metrics["company_counts"].items():
        rows.append({"Metric": comp, "Value": cnt})

    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Metric", "Value"])
        writer.writeheader()
        writer.writerows(rows)

def pretty_print(metrics: Dict, sample_applied: List[Dict[str,str]]):
    print("\n" + "="*40)
    print(" APPLICATION ANALYSIS SUMMARY ")
    print("="*40)
    print(f"Unique rows scanned: {metrics['total_unique_rows']}")
    print(f"Detected applied entries: {metrics['total_applied']}")
    print(f"Interviews (incl offers/hired): {metrics['interviews']} ({metrics['interview_rate']:.2f}%)")
    print(f"Offers/Hired: {metrics['offers']} ({metrics['offer_rate']:.2f}%)")
    print(f"Ghosted / pending: {metrics['ghosted']} ({metrics['ghosted_rate']:.2f}%)")
    print("\nTop companies (up to 30):")
    for comp, cnt in metrics["company_counts"].items():
        print(f" - {comp:30} {cnt}")
    if sample_applied:
        print("\nSample applied rows (first 10):")
        for r in sample_applied[:10]:
            company = r.get("company") or ""
            title = r.get("title") or ""
            url = r.get("apply_url") or r.get("apply url") or ""
            print(f"  • {company:25} | {title:30} | {url}")
    print("\nReport saved to", OUTPUT_CSV)
    print("="*40 + "\n")

# --- main ---
def main():
    combined = load_all_applications(CURRENT_APPLICATIONS_FILE, PAST_DATA_FOLDER)
    metrics, applied_rows = analyze(combined)
    write_analysis_csv(metrics, OUTPUT_CSV)
    pretty_print(metrics, applied_rows)

if __name__ == "__main__":
    main()
