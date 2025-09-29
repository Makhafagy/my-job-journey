# pull_apply_links.py
import csv
import re
import sys
import urllib.parse
from typing import Dict, List, Optional, Set, Tuple
import os  # Added for file existence check

import requests
from bs4 import BeautifulSoup

# ---------- Config ----------
RAW_MD = "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/README.md"

ATS_WHITELIST = (
    "myworkdayjobs.com", "workday",
    "greenhouse.io", "boards.greenhouse.io",
    "lever.co", "jobs.lever.co",
    "icims.com", "taleo.net", "ashbyhq.com",
    "smartrecruiters.com", "eightfold.ai",
    "myhirecloud.com", "successfactors", "dayforcehcm",
    "brassring", "workforcenow", "workable.com",
    "careers.", "jobs.",
)
EXCLUDE_DOMAINS = ("simplify.jobs", "imgur.com", "github.com",
                   "swelist.com", "raw.githubusercontent.com")

FLAG_EMOJIS = {
    "🛂": "no_sponsorship",
    "🇺🇸": "requires_us_citizenship",
    "🔥": "faang_plus",
    "🔒": "closed",
    "🎓": "advanced_degree",
}
ARROW_GLYPHS = ("↳", "↠", "➜", "→", "⤷", "⮑", "›", "»")

CSV_FIELDS = [
    "flags", "company", "title", "location", "apply_url",
    "age",  # numeric (days)
    "no_sponsorship", "requires_us_citizenship", "faang_plus",
    "closed", "advanced_degree",
]

# ---------- NEW: US Location Filtering Config ----------
US_STATE_CODES = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID',
    'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS',
    'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK',
    'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV',
    'WI', 'WY', 'DC'
}
US_KEYWORDS = {'USA', 'U.S.', 'US', 'United States'}
NON_US_KEYWORDS = {'Canada', 'UK', 'United Kingdom'}

# ---------- HTTP ----------
def fetch(url: str) -> str:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.text

# ---------- URL helpers ----------
def strip_tracking(u: str) -> str:
    try:
        p = urllib.parse.urlparse(u)
    except Exception:
        return u
    if not p.query:
        return u
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
        out = f"{p.scheme}://{p.netloc}{p.path}"
    return out

def is_direct_ats(u: str) -> bool:
    low = (u or "").lower()
    if any(bad in low for bad in EXCLUDE_DOMAINS):
        return False
    return any(dom in low for dom in ATS_WHITELIST)

def norm_url_for_dedupe(u: str) -> str:
    try:
        p = urllib.parse.urlparse(u)
        return urllib.parse.urlunparse((
            p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"),
            "", p.query, ""
        ))
    except Exception:
        return (u or "").rstrip("/").lower()

# ---------- Text helpers ----------
def is_arrow_cell(s: str) -> bool:
    s = (s or "").strip()
    if s in ARROW_GLYPHS:
        return True
    return bool(re.fullmatch(r"(?:-&gt;|->|→|↳)\s*", s))

def clean_md_text(md: str) -> str:
    md = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", md or "")
    return re.sub(r"\s+", " ", md).strip()

def strip_flag_emojis(s: str) -> str:
    for e in FLAG_EMOJIS.keys():
        s = s.replace(e, "")
    return re.sub(r"\s+", " ", s).strip()

def age_to_days(s: str) -> Optional[int]:
    s = (s or "").strip().lower()
    if not s:
        return None
    s = (s.replace("mth", "mo")
           .replace("year", "yr").replace("years", "yr")
           .replace("month", "mo").replace("months", "mo")
           .replace("week", "w").replace("weeks", "w")
           .replace("day", "d").replace("days", "d")
           .replace("hour", "h").replace("hours", "h"))
    m = re.search(r"\b(\d+)\s*(h|d|w|mo|yr|y)\b", s) or re.search(r"\b(\d+)(h|d|w|mo|yr|y)\b", s)
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2)
    if unit == "y": unit = "yr"
    return { "h": 0, "d": n, "w": n*7, "mo": n*30, "yr": n*365 }.get(unit, None)

def detect_flags(text: str) -> Dict[str, bool]:
    out = {k: False for k in FLAG_EMOJIS.values()}
    for e, k in FLAG_EMOJIS.items():
        if e in text:
            out[k] = True
    low = (text or "").lower()
    if any(t in low for t in ["no sponsorship", "does not offer sponsorship", "sponsorship not available", "no visa"]):
        out["no_sponsorship"] = True
    if any(t in low for t in ["requires u.s. citizenship", "us citizenship required", "citizens only", "u.s. citizens only"]):
        out["requires_us_citizenship"] = True
    if "faang" in low: out["faang_plus"] = True
    if any(t in low for t in ["application is closed", "posting closed", "closed", "inactive", "not accepting", "no longer accepting", "apply disabled", "unavailable", "archived", "lock"]):
        out["closed"] = True
    if any(t in low for t in ["advanced degree", "master", "master’s", "masters", "phd", "mba"]):
        out["advanced_degree"] = True
    return out

def flags_emoji_row(row: Dict) -> str:
    buf = []
    if row.get("no_sponsorship"): buf.append("🛂")
    if row.get("requires_us_citizenship"): buf.append("🇺🇸")
    if row.get("faang_plus"): buf.append("🔥")
    return "".join(buf)

# ---------- README slicing ----------
def extract_active_swe(md: str) -> str:
    start_m = re.search(r"^##\s*Software Engineering New Grad Roles.*?$", md, re.I | re.M)
    if not start_m:
        return md
    start = start_m.start()
    inactive_m = re.search(r"^###\s*Inactive roles.*?$", md[start_m.end():], re.I | re.M)
    next_h2_m = re.search(r"^##\s+", md[start_m.end():], re.M)
    if inactive_m:
        end = start_m.end() + inactive_m.start()
    elif next_h2_m:
        end = start_m.end() + next_h2_m.start()
    else:
        end = len(md)
    return md[start:end]

# ---------- Table parsing ----------
def extract_first_ats_url_from_cell(cell_md: str) -> Optional[str]:
    urls = re.findall(r"\((https?://[^)]+)\)", cell_md or "")
    urls += [u.rstrip(")|,") for u in re.findall(r"https?://\S+", cell_md or "")]
    for u in urls:
        if is_direct_ats(u):
            return u
    return None

def parse_markdown_table(fragment: str) -> List[Dict]:
    rows: List[Dict] = []
    seen = set()
    last_company: Optional[str] = None
    lines = [ln.strip() for ln in fragment.splitlines() if ln.strip().startswith("|") and ln.count("|") >= 5]
    if not lines:
        return parse_html_table(fragment)
    body = []
    for ln in lines:
        if re.match(r"^\|\s*-+\s*\|", ln): continue
        if re.search(r"\|\s*Company\s*\|\s*Role\s*\|\s*Location\s*\|\s*Application\s*\|\s*Age\s*\|", ln, re.I): continue
        body.append(ln)
    for ln in body:
        cols = [c.strip() for c in ln.strip("|").split("|")]
        if len(cols) < 5: continue
        comp_cell, role_cell, loc_cell, app_cell, age_cell = cols[0], cols[1], cols[2], cols[3], cols[4]
        app_soup = BeautifulSoup(app_cell, "html.parser")
        app_alts = " ".join(img.get("alt", "") for img in app_soup.find_all("img"))
        flags = detect_flags(" ".join([comp_cell, role_cell, app_soup.get_text(" ", strip=True), app_alts, age_cell]))
        raw_company = clean_md_text(comp_cell)
        company = strip_flag_emojis(raw_company)
        if is_arrow_cell(company):
            company = last_company or ""
        else:
            if company: last_company = company
        title = strip_flag_emojis(clean_md_text(role_cell))
        location = clean_md_text(loc_cell)
        age_days = age_to_days(clean_md_text(age_cell))
        apply_url = extract_first_ats_url_from_cell(app_cell)
        if not apply_url: continue
        cleaned = strip_tracking(apply_url)
        if not is_direct_ats(cleaned): continue
        key = norm_url_for_dedupe(cleaned)
        if key in seen: continue
        seen.add(key)
        rows.append({"company": company, "title": title, "location": location, "apply_url": cleaned, "age": age_days, **flags})
    return rows

def parse_html_table(fragment: str) -> List[Dict]:
    soup = BeautifulSoup(fragment, "html.parser")
    rows: List[Dict] = []
    seen = set()
    last_company: Optional[str] = None
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 5: continue
        comp_td, role_td, loc_td, app_td, age_td = tds[0], tds[1], tds[2], tds[3], tds[4]
        comp_text, role_text, loc_text, app_text, age_text = comp_td.get_text(" ", strip=True), role_td.get_text(" ", strip=True), loc_td.get_text(" ", strip=True), app_td.get_text(" ", strip=True), age_td.get_text(" ", strip=True)
        alts = " ".join(img.get("alt", "") for img in (comp_td.find_all("img") + role_td.find_all("img") + app_td.find_all("img")))
        flags = detect_flags(f"{comp_text} {role_text} {app_text} {alts} {age_text}")
        company = strip_flag_emojis(comp_text)
        if is_arrow_cell(company):
            company = last_company or ""
        else:
            if company: last_company = company
        title = strip_flag_emojis(role_text)
        age_days = age_to_days(age_text)
        apply_url = None
        for a in app_td.find_all("a", href=True):
            if is_direct_ats(a["href"]):
                apply_url = a["href"].strip()
                break
        if not apply_url: continue
        cleaned = strip_tracking(apply_url)
        if not is_direct_ats(cleaned): continue
        key = norm_url_for_dedupe(cleaned)
        if key in seen: continue
        seen.add(key)
        rows.append({"company": company, "title": title, "location": loc_text, "apply_url": cleaned, "age": age_days, **flags})
    return rows

# ---------- Pipeline ----------
def load_active_swe_rows() -> List[Dict]:
    md = fetch(RAW_MD)
    section = extract_active_swe(md)
    rows = parse_markdown_table(section)
    return rows

def dedupe(rows: List[Dict]) -> List[Dict]:
    out, seen = [], set()
    for r in rows:
        key = norm_url_for_dedupe(r["apply_url"])
        if key in seen: continue
        seen.add(key)
        out.append(r)
    return out

# ---------- NEW: Function to read previously applied jobs ----------
def load_applied_urls(applied_csv_path: str) -> Set[str]:
    """Reads the CSV with application tracking and returns a set of normalized URLs for jobs already applied to."""
    applied_urls = set()
    if not os.path.exists(applied_csv_path):
        print(f"Info: Applied jobs file not found at '{applied_csv_path}'. Skipping.")
        return applied_urls
    
    try:
        with open(applied_csv_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            # Normalize field names by lowercasing and stripping whitespace
            reader.fieldnames = [name.lower().strip() for name in reader.fieldnames]
            for row in reader:
                # Check for 'applied' column, case-insensitive
                if row.get("applied", "").strip().upper() == "TRUE":
                    url = row.get("apply_url")
                    if url:
                        applied_urls.add(norm_url_for_dedupe(url))
    except Exception as e:
        print(f"Warning: Could not read applied jobs file '{applied_csv_path}'. Error: {e}")
        
    print(f"Found {len(applied_urls)} previously applied jobs.")
    return applied_urls

# ---------- NEW: Enhanced filtering function ----------
def is_us_location(location: str) -> bool:
    """Checks if a location string corresponds to a US location."""
    loc_upper = (location or "").upper()

    # Exclude if a non-US keyword is present
    if any(keyword.upper() in loc_upper for keyword in NON_US_KEYWORDS):
        return False
    
    # Include if a US keyword is present
    if any(keyword.upper() in loc_upper for keyword in US_KEYWORDS):
        return True
    
    # Check for state codes using regex to match whole words
    # This avoids matching "CA" in "Canada"
    if any(re.search(r'\b' + code + r'\b', loc_upper) for code in US_STATE_CODES):
        return True
    
    # Heuristic for "Remote" - include if it doesn't mention a non-US country
    if "REMOTE" in loc_upper:
        return True

    # Default to excluding if no positive US indicators are found
    return False

def filter_rows(rows: List[Dict], applied_urls: Set[str]) -> List[Dict]:
    """Applies all filtering logic: age, location, applied status, and flags."""
    out = []
    for r in rows:
        # 1. Filter out closed or advanced degree roles
        if r.get("closed") or r.get("advanced_degree"):
            continue
        
        # 2. Filter out jobs already applied to
        normalized_url = norm_url_for_dedupe(r["apply_url"])
        if normalized_url in applied_urls:
            continue

        # 3. Filter jobs older than 7 days
        age = r.get("age")
        if age is None or age > 7:
            continue
            
        # 4. Filter for US-only locations
        if not is_us_location(r.get("location", "")):
            continue

        out.append(r)
    return out

def sort_rows(rows: List[Dict]) -> List[Dict]:
    def k(r: Dict) -> Tuple:
        return (
            0 if r.get("no_sponsorship") else 1,
            0 if r.get("requires_us_citizenship") else 1,
            0 if r.get("faang_plus") else 1,
            (r.get("company") or "zzz").lower(),
            (r.get("title") or "zzz").lower(),
            (r.get("location") or "zzz").lower(),
        )
    return sorted(rows, key=k)

# ---------- Main ----------
def main():
    # Define input (your sheet) and output (new filtered list) filenames
    applied_csv = "new_grad_swe_apply_links_applying.csv"
    out_csv = sys.argv[1] if len(sys.argv) > 1 else "new_grad_swe_apply_links.csv"

    # --- Pipeline updated ---
    applied_urls = load_applied_urls(applied_csv) # Load applied jobs
    rows = load_active_swe_rows()                 # Scrape all active SWE jobs
    rows = dedupe(rows)
    rows = filter_rows(rows, applied_urls)         # Apply the new, combined filters
    rows = sort_rows(rows)

    # Defaults & cleanup
    for r in rows:
        for k in ["no_sponsorship", "requires_us_citizenship", "faang_plus", "closed", "advanced_degree"]:
            r.setdefault(k, False)
        r["company"] = strip_flag_emojis(r.get("company", ""))
        r["title"]   = strip_flag_emojis(r.get("title", ""))
        if r.get("age") is None:
            r["age"] = ""

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for r in rows:
            out = {k: r.get(k, "") for k in CSV_FIELDS}
            out["flags"] = flags_emoji_row(r)
            w.writerow(out)

    print(f"✅ Wrote {len(rows)} new, filtered, direct ATS links to {out_csv}")
    print(f"   - Ignored {len(applied_urls)} jobs you already applied to.")
    print("   - Kept only jobs in the US posted in the last 7 days.")

if __name__ == "__main__":
    main()