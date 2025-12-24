import re
from rapidfuzz import fuzz
from typing import List, Tuple

VENDOR_SYNONYMS = {
    "microsoft": ["ms", "microsoft_corporation", "microsoft_inc"],
    "google": ["google_inc", "google_llc"],
    "adobe": ["adobe_inc", "adobe_systems"],
    "cisco": ["cisco_systems", "cisco_inc"]
}

PRODUCT_SYNONYMS = {
    "chrome": ["google_chrome", "chrome-browser", "chromium_browser"],
    "edge": ["microsoft_edge", "edge_browser"],
    "excel": ["microsoft_excel", "office_excel"],
    "office": ["microsoft_office"],
    "windows": ["windows_10", "windows_11", "win10", "win11"]
}


def normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "_", (s or "").lower().strip())


def parse_cpe(cpe: str):
    parts = cpe.split(":")
    if len(parts) < 6:
        return None, None, None
    return normalize(parts[3]), normalize(parts[4]), normalize(parts[5])


def vendor_match(v1: str, v2: str) -> bool:
    if v1 == v2:
        return True
    for root, syns in VENDOR_SYNONYMS.items():
        if v1 == root and v2 in syns:
            return True
        if v2 == root and v1 in syns:
            return True
    return False


def product_match(p1: str, p2: str) -> bool:
    if p1 == p2:
        return True
    for root, syns in PRODUCT_SYNONYMS.items():
        if p1 == root and p2 in syns:
            return True
        if p2 == root and p1 in syns:
            return True
    sim = fuzz.partial_ratio(p1, p2)
    return sim >= 72


def version_match(v1: str, v2: str) -> bool:
    if v1 == v2:
        return True
    if v2 in ["*", "-", "na", ""]:
        return True
    try:
        v1_major = v1.split(".")[0]
        v2_major = v2.split(".")[0]
        if v1_major == v2_major:
            return True
    except Exception:
        pass
    return False


# Public fuzzy find: accept a sqlite cursor and cpe_input string
def fuzzy_find_related_cpe(cursor, cpe_input: str) -> List[str]:
    vin, pin, verin = parse_cpe(cpe_input)
    if not vin or not pin:
        return []

    # Optimized: Instead of loading ALL cve_cpe rows (323k!), 
    # use SQL LIKE to pre-filter by product name
    # This is much faster than loading everything into memory
    product_pattern = f'%{pin}%'
    vendor_pattern = f'%{vin}%'
    
    # Query only rows that likely contain this vendor/product
    cursor.execute(
        "SELECT DISTINCT cve_cpe FROM cve WHERE cve_cpe LIKE ? OR cve_cpe LIKE ? LIMIT 1000", 
        (product_pattern, vendor_pattern)
    )
    db_cpes = [row[0] for row in cursor.fetchall()]

    matched = []
    for cpe_blob in db_cpes:
        try:
            # cve_cpe stored as JSON array; simple string search
            if not cpe_blob:
                continue
            # parse blob into individual cpes by looking for '"cpe:2.3:' occurrences
            cand_list = []
            if cpe_blob.startswith('['):
                # crude: split on '"' and filter
                parts = [p for p in cpe_blob.split('"') if p.startswith('cpe:2.3:')]
                cand_list = parts
            else:
                cand_list = [cpe_blob]

            for cpe in cand_list:
                v, p, ver = parse_cpe(cpe)
                if not v:
                    continue
                if not vendor_match(vin, v):
                    continue
                if not product_match(pin, p):
                    continue
                if not version_match(verin, ver):
                    continue
                matched.append(cpe)
        except Exception:
            continue

    return list(set(matched))


# Return rows (id, description, score, published) for matched cpes
def fuzzy_match_cpe_to_cve(cursor, cpe_input: str):
    related = fuzzy_find_related_cpe(cursor, cpe_input)
    if not related:
        return []

    # Determine which columns are available in the 'cve' table
    cols = [r[1] for r in cursor.execute("PRAGMA table_info(cve)").fetchall()]

    sel_cols = ["id", "description", "cvss_base_score"]
    if "published" in cols:
        sel_cols.append("published")
    elif "last_modified" in cols:
        sel_cols.append("last_modified")
    else:
        # we'll add a NULL placeholder later
        pass

    # cve_cpe may be stored as JSON array string; use LIKE to match entries
    conditions = " OR ".join(["cve_cpe LIKE ?"] * len(related))
    params = [f'%"{r}"%' for r in related]
    sql = f"SELECT {', '.join(sel_cols)} FROM cve WHERE ({conditions})"
    cursor.execute(sql, params)
    rows = cursor.fetchall()

    # Normalize rows to always have 4 columns: (id, description, cvss, published)
    normalized = []
    for r in rows:
        r = list(r)
        if len(r) == 3:
            r.append(None)
        normalized.append(tuple(r))

    return normalized
