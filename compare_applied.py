#!/usr/bin/env python3
"""
compare_applied.py

Find all past 'applying' CSVs in past_applied_data/new_grad_swe_apply_links_applying_*.csv,
gather URLs marked as applied, then remove matching rows from
new_grad_swe_apply_links.csv (overwrite in place).

Usage:
    python compare_applied.py         # run normally
    python compare_applied.py --debug # print which rows were removed
"""
import csv
import glob
import os
import argparse
import urllib.parse
from typing import Set, Dict, List, Optional

# configuration
LINKS_FILE = "new_grad_swe_apply_links.csv"
PAST_PATTERN = os.path.join("past_applied_data", "new_grad_swe_apply_links_applying_*.csv")
APPLIED_TRUE = {"TRUE", "YES", "Y", "1"}

# ---------------- URL utilities (compatible with pull_apply_links) ----------------
def strip_tracking(u: str) -> str:
    """Remove common tracking UTM params and 'simplify' keys/values from a URL."""
    if not u:
        return ""
    try:
        p = urllib.parse.urlparse(u)
    except Exception:
        return u.strip()
    if not p.query:
        # return full url (including scheme/netloc/path)
        return urllib.parse.urlunparse(p._replace(query=""))
    keep = []
    for k, v in urllib.parse.parse_qsl(p.query, keep_blank_values=True):
        lk, lv = (k or "").lower(), (v or "").lower()
        if lk.startswith("utm_"):
            continue
        if "simplify" in lk or "simplify" in lv:
            continue
        keep.append((k, v))
    q = urllib.parse.urlencode(keep)
    out = urllib.parse.urlunparse(p._replace(query=q))
    if not q:
        # remove the trailing ? etc
        out = f"{p.scheme}://{p.netloc}{p.path}"
    return out

def norm_url_for_dedupe(u: str) -> str:
    """Normalize URL for stable dedupe/comparison: lower scheme+netloc, strip trailing slash on path, keep query."""
    u = (u or "").strip()
    try:
        p = urllib.parse.urlparse(u)
        scheme = (p.scheme or "https").lower()
        netloc = (p.netloc or "").lower()
        path = (p.path or "").rstrip("/")
        # keep query as-is (sometimes query has identifying token), but strip tracking earlier
        query = p.query or ""
        return urllib.parse.urlunparse((scheme, netloc, path, "", query, ""))
    except Exception:
        return u.rstrip("/").lower()

# ---------------- Applied URLs loader ----------------
def find_header_fieldname_map(fieldnames: List[str]) -> Dict[str, str]:
    """
    Build a map of normalized header -> original header name.
    Normalized header is header.strip().lower()
    """
    return { (h or "").strip().lower(): h for h in (fieldnames or []) }

def detect_url_key(fieldnames: List[str]) -> Optional[str]:
    """Return the header name that's most likely the URL/apply link column."""
    if not fieldnames:
        return None
    for h in fieldnames:
        hn = (h or "").strip().lower()
        if hn == "apply_url" or hn == "apply-url" or hn == "apply url":
            return h
    for h in fieldnames:
        hn = (h or "").strip().lower()
        if "apply" in hn and ("url" in hn or "link" in hn):
            return h
    for h in fieldnames:
        hn = (h or "").strip().lower()
        if "url" in hn or "link" in hn:
            return h
    return None

def detect_applied_key(fieldnames: List[str]) -> Optional[str]:
    """Return the header that looks like an 'Applied' flag column (if any)."""
    if not fieldnames:
        return None
    for h in fieldnames:
        hn = (h or "").strip().lower()
        if hn in ("applied", "applied?"):
            return h
    for h in fieldnames:
        hn = (h or "").strip().lower()
        if "appl" in hn and ("date" not in hn):  # prefer plain Applied over "Date Applied"
            return h
    return None

def detect_date_key(fieldnames: List[str]) -> Optional[str]:
    for h in fieldnames:
        if "date applied" == (h or "").strip().lower() or "date_applied" == (h or "").strip().lower():
            return h
    # fallback to any header containing "date"
    for h in fieldnames:
        if "date" in (h or "").strip().lower():
            return h
    return None

def detect_status_key(fieldnames: List[str]) -> Optional[str]:
    for h in fieldnames:
        if (h or "").strip().lower() == "status":
            return h
    return None

def load_applied_urls_from_archives(pattern: str = PAST_PATTERN) -> Set[str]:
    """Read all CSVs matching pattern and collect normalized applied URLs."""
    applied = set()
    files = sorted(glob.glob(pattern))
    for path in files:
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    continue
                # detect keys
                url_key = detect_url_key(reader.fieldnames)
                applied_key = detect_applied_key(reader.fieldnames)
                date_key = detect_date_key(reader.fieldnames)
                status_key = detect_status_key(reader.fieldnames)

                if not url_key:
                    # skip files with no URL column
                    continue

                for row in reader:
                    # skip entirely-empty rows
                    if not any((v or "").strip() for v in (row.values() if row else [])):
                        continue

                    applied_flag = False

                    # 1) explicit applied flag column (TRUE/Yes/1)
                    if applied_key:
                        val = (row.get(applied_key) or "").strip().upper()
                        if val in APPLIED_TRUE:
                            applied_flag = True

                    # 2) Date Applied non-empty => treat as applied
                    if not applied_flag and date_key:
                        if (row.get(date_key) or "").strip():
                            applied_flag = True

                    # 3) Status contains 'applied'
                    if not applied_flag and status_key:
                        st = (row.get(status_key) or "").strip().lower()
                        if "appl" in st or "submitted" in st or "interview" in st:
                            applied_flag = True

                    # 4) fallback: if there's no applied_key but Date Applied or Status is not present,
                    # treat only rows with explicit truthy values as applied. (we don't mark everything)
                    if applied_flag:
                        raw_url = (row.get(url_key) or "").strip()
                        if raw_url:
                            u = strip_tracking(raw_url)
                            applied.add(norm_url_for_dedupe(u))
        except Exception:
            # skip unreadable files silently (we don't want script to fail because of one corrupt CSV)
            continue
    return applied

# ---------------- Filter current links CSV ----------------
def filter_links_file(links_file: str, applied_urls: Set[str], debug: bool = False) -> int:
    """
    Overwrite links_file with only rows whose apply_url (normalized) is NOT in applied_urls.
    Returns number of removed rows.
    """
    if not os.path.exists(links_file):
        raise FileNotFoundError(links_file)

    removed_rows: List[Dict] = []
    kept_rows: List[Dict] = []
    # read
    with open(links_file, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        if not fieldnames:
            return 0
        url_key = detect_url_key(fieldnames)
        if not url_key:
            # can't find URL column -> nothing to compare, keep all
            return 0
        for row in reader:
            raw_url = (row.get(url_key) or "").strip()
            if not raw_url:
                # if no URL in row, keep it (or optionally drop; we keep)
                kept_rows.append(row)
                continue
            cleaned = strip_tracking(raw_url)
            norm = norm_url_for_dedupe(cleaned)
            if norm in applied_urls:
                removed_rows.append(row)
            else:
                kept_rows.append(row)

    # write back (overwrite)
    with open(links_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in kept_rows:
            writer.writerow(r)

    # debug output
    if debug:
        if removed_rows:
            print(f"\nRemoved {len(removed_rows)} applied rows:")
            for r in removed_rows:
                comp = r.get("company") or r.get("Company") or ""
                title = r.get("title") or r.get("Title") or ""
                url = r.get(url_key) or ""
                print(f"- {comp} | {title} | {url}")
        else:
            print("\nNo applied rows were matched/removed.")

    return len(removed_rows)

# ---------------- Main ----------------
def main():
    parser = argparse.ArgumentParser(description="Remove already-applied jobs from new_grad_swe_apply_links.csv using past_applied_data/* files.")
    parser.add_argument("--past-pattern", default=PAST_PATTERN, help="Glob pattern for past applied CSVs (default: past_applied_data/new_grad_swe_apply_links_applying_*.csv)")
    parser.add_argument("--links-file", default=LINKS_FILE, help="Links CSV to update (default: new_grad_swe_apply_links.csv)")
    parser.add_argument("--debug", action="store_true", help="Print removed rows for verification")
    args = parser.parse_args()

    applied_urls = load_applied_urls_from_archives(args.past_pattern)
    removed_count = filter_links_file(args.links_file, applied_urls, debug=args.debug)

    # final summary
    # Count remaining rows in links_file
    remaining = 0
    try:
        with open(args.links_file, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            remaining = sum(1 for _ in reader)
    except Exception:
        remaining = 0

    print(f"\nFiltered {removed_count} applied jobs. {remaining} fresh jobs remain in {args.links_file}.")
    print(f"Used {len(applied_urls)} unique applied URLs from archive files.")

if __name__ == "__main__":
    main()
