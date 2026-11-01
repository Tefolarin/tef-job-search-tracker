"""Rebuild the H-1B company ranking from Department of Labor LCA disclosure files in this folder.

Method (from NOTES.md and the workbook's Read me sheet):
- Files named LCA_Disclosure_Data_*.xlsx. Rows with a blank case number are skipped.
- A case that appears in more than one file keeps the record with the later decision date.
- Window: the 12 months ending with the latest decision date found.
- Only visa class H-1B with case status Certified.
- Roles matched on JOB_TITLE text. New hire = NEW_EMPLOYMENT or CHANGE_EMPLOYER above zero.
- Score: 1 per new-hire filing in product manager, product ops, product marketing or strategy; 0.5 for TPM only.
- Companies: the checked list of names in h1b_names.json (tax ID -> company), then grouping by tax ID.
- Staffing and IT outsourcing names are left out and listed on the Excluded sheet.

Reading a big file takes a few minutes, so each file is cached in data/lca_cache as a slim, compressed copy.
"""
import os
import re
import csv
import glob
import gzip
import json
import statistics
import datetime as dt
from collections import Counter, defaultdict

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(HERE, "data", "lca_cache")
NAMES_FILE = os.path.join(HERE, "h1b_names.json")
TOP_N = 300
TIER_CUTS = (75, 150)  # ranks 1-75 Tier 1, 76-150 Tier 2, rest Tier 3

COLS = ["CASE_NUMBER", "CASE_STATUS", "DECISION_DATE", "VISA_CLASS", "JOB_TITLE", "NEW_EMPLOYMENT", "CHANGE_EMPLOYER",
        "EMPLOYER_NAME", "EMPLOYER_FEIN", "WORKSITE_CITY", "WORKSITE_STATE", "WAGE_RATE_OF_PAY_FROM",
        "WAGE_UNIT_OF_PAY", "PW_WAGE_LEVEL", "H_1B_DEPENDENT"]
I = {c: i for i, c in enumerate(COLS)}

# ---------- role titles ----------
TPM = re.compile(r"\btechnical program manag", re.I)
PMM = re.compile(r"\bproduct marketing\b", re.I)
POPS = re.compile(r"\bproduct (operations|ops)\b", re.I)
PM = re.compile(r"\bproduct (manager|owner|lead|leader|director|management)\b|\b(apm|gpm)\b|"
                r"\bgroup product manager\b|\bassociate product manager\b", re.I)
STRAT = re.compile(r"\bcorporate strategy\b|\bbusiness strategy\b|"
                   r"\bstrategy\s*(and|&|,)\s*(operations|ops|planning|analytics|analysis|transformation|execution)\b|"
                   r"\bstrat ?ops\b|\bstrategic (planning|initiatives|programs?)\b|"
                   r"\bstrategy (senior |sr\.? )?(manager|lead|associate|analyst|director)\b|"
                   r"\b(director|head|vp|vice president),?( of)? strategy\b|\bbiz ?ops\b", re.I)
STRAT_NOT_WORDS = re.compile(r"\b(engineer|engineering|developer|scientist)\b", re.I)
STRAT_NOT_QUAL = re.compile(r"\b(sales|marketing|content|brand|pricing|investment|credit|risk|data|seo|tax|legal|trading|"
                            r"media|creative|search|quantitative)\s+(strategy|strategist|strategic)", re.I)
SENIOR = re.compile(r"\b(senior|sr|staff|principal|lead|director|head|vp|vice president|group)\b", re.I)
ENTRY = re.compile(r"(?<!senior )(?<!sr )(?<!sr\. )\bassociate\b(?!,? director)|\b(apm|junior|jr|entry|new grad|rotational)\b",
                   re.I)


def role(title):
    t = title or ""
    if PMM.search(t):
        return "pmm"
    if POPS.search(t):
        return "pops"
    if PM.search(t):
        return "pm"
    if TPM.search(t):
        return "tpm"
    if STRAT.search(t) and not STRAT_NOT_WORDS.search(t) and not STRAT_NOT_QUAL.search(t):
        return "strat"
    return None


# ---------- names, exclusions, flags ----------
STAFFING = ["populus", "compunnel", "infotech", "insight global", "hcl", "mphasis", "infinite computer solutions",
            "intraedge", "randstad", "xoriant", "brillio", "globallogic", "beacon hill", "nagarro", "pyramid consulting",
            "altimetrik", "artech", "collabera", "infosystems", "consultancy", "wipro", "ust global", "staffing",
            "hexaware", "trantor"]
CONSULTING = re.compile(r"\b(consulting|consultants|deloitte|alixpartners|sapient|mckinsey|kearney|accenture|"
                        r"pricewaterhouse|pwc|kpmg|ernst & young|oliver wyman|booz allen|boston consulting)\b", re.I)
UNIVERSITY = re.compile(r"\b(university|college|institute of technology)\b", re.I)
F_CONSULT = "Consulting firm: confirm roles are in-house"
F_UNI = "University: may be exempt from the H-1B lottery"
F_DEP = "Files as H-1B dependent (heavy H-1B workforce): check it is a direct employer"
F_SMALL = "Small filer (under 15 filings in total): check it is a real employer"
RULE_FLAGS = (F_CONSULT, F_UNI, F_DEP, F_SMALL)

UNIT = {"year": 1, "hour": 2080, "month": 12, "week": 52, "bi-weekly": 26}


def fein(v):
    return re.sub(r"\D", "", str(v or "")).zfill(9)


def staffing_match(name):
    low = (name or "").lower()
    for k in STAFFING:
        if re.search(r"\b" + re.escape(k) + r"\b", low):
            return k
    return None


# ---------- reading files ----------
def list_files():
    return sorted(glob.glob(os.path.join(HERE, "LCA_Disclosure_Data_*.xlsx")))


def cache_path(path):
    base = os.path.basename(path)
    return os.path.join(CACHE_DIR, f"{base}.{int(os.path.getmtime(path))}.csv.gz")


def _date(v):
    if isinstance(v, dt.datetime):
        return v.date().isoformat()
    if isinstance(v, dt.date):
        return v.isoformat()
    return str(v or "")[:10]


def extract(path, progress=None):
    """Make the slim cached copy of one file if it isn't there yet. Returns the cache path."""
    out = cache_path(path)
    if os.path.exists(out):
        return out
    os.makedirs(CACHE_DIR, exist_ok=True)
    wb = openpyxl.load_workbook(path, read_only=True)
    try:
        ws = wb[wb.sheetnames[0]]
        rows = ws.iter_rows(values_only=True)
        head = [str(h or "").strip().upper() for h in next(rows)]
        missing = [c for c in COLS if c not in head]
        if missing:
            raise ValueError(f"{os.path.basename(path)} is missing columns: {', '.join(missing)}")
        idx = [head.index(c) for c in COLS]
        tmp = out + ".tmp"
        n = 0
        with gzip.open(tmp, "wt", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(COLS)
            for r in rows:
                if not r or r[idx[0]] in (None, ""):
                    continue
                vals = [r[i] if i < len(r) else None for i in idx]
                vals[I["DECISION_DATE"]] = _date(vals[I["DECISION_DATE"]])
                w.writerow(["" if v is None else v for v in vals])
                n += 1
                if progress and n % 50000 == 0:
                    progress(f"Reading {os.path.basename(path)}: {n:,} cases so far")
        os.replace(tmp, out)
    finally:
        wb.close()
    # remove older caches of the same file (they're our own scratch copies)
    for old in glob.glob(os.path.join(CACHE_DIR, os.path.basename(path) + ".*.csv.gz")):
        if old != out:
            try:
                os.remove(old)
            except OSError:
                pass
    return out


def iter_cache(cpath):
    with gzip.open(cpath, "rt", newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        for row in r:
            yield row


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


# ---------- the build ----------
def build(names_map, carry_flags=None, progress=None):
    """Returns a dict with companies (ranked), excluded, entities and stats."""
    progress = progress or (lambda m: None)
    files = list_files()
    if not files:
        raise ValueError("No LCA_Disclosure_Data_*.xlsx files in the folder.")
    caches = []
    for p in files:
        progress(f"Preparing {os.path.basename(p)}")
        caches.append((os.path.basename(p), extract(p, progress)))

    # pass 1: which record wins for each case, and each file's date range
    progress("Removing cases that appear in more than one file")
    best = {}
    ranges = {}
    total_rows = 0
    for fi, (name, cp) in enumerate(caches):
        lo, hi, n = "9999", "0000", 0
        for row in iter_cache(cp):
            n += 1
            case, dd = row[0], row[I["DECISION_DATE"]]
            if dd:
                lo, hi = min(lo, dd), max(hi, dd)
            prev = best.get(case)
            if prev is None or (dd, fi) >= prev:
                best[case] = (dd, fi)
        ranges[name] = (lo if n else "", hi if n else "", n)
        total_rows += n
    dupes = total_rows - len(best)
    latest = max((v[0] for v in best.values() if v[0]), default="")
    if not latest:
        raise ValueError("No decision dates found in the files.")
    ld = dt.date.fromisoformat(latest)
    y, m = ld.year, ld.month - 11
    while m <= 0:
        m += 12
        y -= 1
    start = dt.date(y, m, 1).isoformat()

    # pass 2: aggregate certified H-1B cases in the window
    progress("Counting filings")
    by_fein = defaultdict(lambda: {"all": 0, "dep": 0, "names": Counter()})
    roles = []
    n_cases = n_cert = 0
    for fi, (name, cp) in enumerate(caches):
        for row in iter_cache(cp):
            case, dd = row[0], row[I["DECISION_DATE"]]
            if best.get(case) != (dd, fi):
                continue
            best[case] = None  # a case is counted once even if repeated inside one file
            if not (start <= dd <= latest):
                continue
            n_cases += 1
            if row[I["VISA_CLASS"]].strip() != "H-1B" or row[I["CASE_STATUS"]].strip() != "Certified":
                continue
            n_cert += 1
            fe = fein(row[I["EMPLOYER_FEIN"]])
            agg = by_fein[fe]
            agg["all"] += 1
            agg["dep"] += row[I["H_1B_DEPENDENT"]].strip().lower() == "yes"
            agg["names"][row[I["EMPLOYER_NAME"]].strip()] += 1
            cat = role(row[I["JOB_TITLE"]])
            if cat:
                unit = UNIT.get(row[I["WAGE_UNIT_OF_PAY"]].strip().lower())
                pay = num(row[I["WAGE_RATE_OF_PAY_FROM"]]) * unit if unit else 0
                roles.append({
                    "fe": fe, "cat": cat, "title": row[I["JOB_TITLE"]],
                    "nh": num(row[I["NEW_EMPLOYMENT"]]) > 0 or num(row[I["CHANGE_EMPLOYER"]]) > 0,
                    "state": row[I["WORKSITE_STATE"]].strip().upper(),
                    "city": row[I["WORKSITE_CITY"]].strip().title(), "level": row[I["PW_WAGE_LEVEL"]].strip(),
                    "pay": pay})
    del best

    # group into companies
    progress("Grouping into companies")
    def key_for(fe):
        return names_map.get(fe) or ("FEIN:" + fe)

    groups = defaultdict(lambda: {"feins": set(), "all": 0, "dep": 0, "roles": []})
    for fe, agg in by_fein.items():
        g = groups[key_for(fe)]
        g["feins"].add(fe)
        g["all"] += agg["all"]
        g["dep"] += agg["dep"]
    for r in roles:
        groups[key_for(r["fe"])]["roles"].append(r)

    def legal(fe):
        return by_fein[fe]["names"].most_common(1)[0][0] if by_fein[fe]["names"] else fe

    rows = []
    for key, g in groups.items():
        rs = g["roles"]
        if not rs:
            continue
        nh = [r for r in rs if r["nh"]]
        cnt = Counter(r["cat"] for r in nh)
        score = cnt["pm"] + cnt["strat"] + cnt["pmm"] + cnt["pops"] + 0.5 * cnt["tpm"]
        if score <= 0:
            continue
        if key.startswith("FEIN:"):
            fe = next(iter(g["feins"]))
            name = legal(fe)
        else:
            name = key
        prod = cnt["pm"] + cnt["pmm"] + cnt["pops"] + cnt["tpm"]
        focus = "Product" if cnt["strat"] == 0 else ("Strategy" if prod == 0 else "Product and strategy")
        levelled = [r for r in rs if r["level"]]
        pays = [r["pay"] for r in rs if r["pay"] > 0]
        states = Counter(r["state"] for r in rs if r["state"])
        cities = Counter(f"{r['city']}, {r['state']}" for r in rs if r["city"])
        rows.append({
            "name": name, "key": key, "score": score, "focus": focus,
            "pm": cnt["pm"], "tpm": cnt["tpm"], "strat": cnt["strat"], "pmm": cnt["pmm"], "pops": cnt["pops"],
            "nh": len(nh), "all_roles": len(rs), "all": g["all"],
            "wage34": (sum(1 for r in levelled if r["level"] in ("III", "IV")) / len(levelled)) if levelled else None,
            "median": round(statistics.median(pays)) if pays else None,
            "entry": sum(1 for r in rs if ENTRY.search(r["title"])),
            "senior": sum(1 for r in rs if SENIOR.search(r["title"])),
            "states": ", ".join(s for s, _ in states.most_common(2)),
            "cities": ", ".join(c for c, _ in cities.most_common(2)),
            "entities": len(g["feins"]), "dep_share": g["dep"] / g["all"] if g["all"] else 0,
            "entity_rows": [(legal(fe), fe, by_fein[fe]["all"],
                             sum(1 for r in rs if r["fe"] == fe), sum(1 for r in nh if r["fe"] == fe))
                            for fe in sorted(g["feins"], key=lambda f: -by_fein[f]["all"])],
        })

    rows.sort(key=lambda r: (-r["score"], -r["all_roles"], r["name"].lower()))
    excluded, kept = [], []
    for r in rows:
        k = staffing_match(r["name"]) or next((staffing_match(e[0]) for e in r["entity_rows"] if staffing_match(e[0])), None)
        if k and r["key"].startswith("FEIN:"):
            r["why"] = f"IT outsourcing / staffing name match: {k}"
            excluded.append(r)
        else:
            kept.append(r)
    top = kept[:TOP_N]
    cut = top[-1]["score"] if top else 0
    excluded = [r for r in excluded if r["score"] >= cut]
    carry_flags = carry_flags or {}
    for i, r in enumerate(top, 1):
        r["rank"] = i
        r["tier"] = 1 if i <= TIER_CUTS[0] else (2 if i <= TIER_CUTS[1] else 3)
        flags = []
        names_all = [r["name"]] + [e[0] for e in r["entity_rows"]]
        if any(CONSULTING.search(n) for n in names_all):
            flags.append(F_CONSULT)
        if any(UNIVERSITY.search(n) for n in names_all):
            flags.append(F_UNI)
        if r["dep_share"] > 0.5:
            flags.append(F_DEP)
        if r["all"] < 15:
            flags.append(F_SMALL)
        flags += [f for f in carry_flags.get(r["name"].lower(), []) if f not in flags]
        r["flags"] = "; ".join(flags)

    stats = {
        "window": (start, latest), "files": ranges, "dupes": dupes, "cases": n_cases, "certified": n_cert,
        "role_cases": len(roles), "role_newhire": sum(1 for r in roles if r["nh"]),
        "focus": Counter(r["focus"] for r in top),
        "score_at": {k: top[k - 1]["score"] for k in (50, 100, 200, 300) if len(top) >= k},
        "score5": sum(1 for r in top if r["score"] >= 5),
        "tier_scores": (top[TIER_CUTS[0] - 1]["score"] if len(top) >= TIER_CUTS[0] else None,
                        top[TIER_CUTS[1] - 1]["score"] if len(top) >= TIER_CUTS[1] else None),
    }
    # every ranked company (not excluded), so a company that falls out of the top 300 can still be updated
    positions = {}
    for i, r in enumerate(kept, 1):
        r.setdefault("rank", i)
        positions[r["name"].lower()] = r
    return {"companies": top, "excluded": excluded, "stats": stats, "all": positions}


def load_names():
    try:
        with open(NAMES_FILE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


# ---------- writing the result into tracker.xlsx ----------
USER_COLS = ["Tier", "E-Verify (STEM OPT needs it)", "Sponsorship answer from a person", "Last checked",
             "Career page", "Notes"]
OWN_COLS = USER_COLS[1:]  # columns that are only ever typed by the user
F_DROPPED = "Below the top 300 in the latest data: kept because you have notes, contacts or applications here"


def implied_tier(rank):
    try:
        rank = int(rank)
    except (TypeError, ValueError):
        return None
    return 1 if rank <= TIER_CUTS[0] else (2 if rank <= TIER_CUTS[1] else 3)


def read_existing(ws):
    head = [str(c.value or "").strip() for c in ws[1]]
    out = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        rec = {h: v for h, v in zip(head, row) if h}
        name = str(rec.get("Company") or "").strip()
        if name:
            out[name.lower()] = rec
    return head, out


def plan(result, existing, busy_names):
    """Work out what changes. busy_names: companies with People or Applications rows (lower case)."""
    new_names = {r["name"].lower() for r in result["companies"]}
    old_ranked = {k for k, v in existing.items() if v.get("Rank") not in (None, "")}
    joining = [r for r in result["companies"] if r["name"].lower() not in existing]
    keep_dropped, remove = [], []
    for k, rec in existing.items():
        if k in new_names:
            continue
        has_own = any(str(rec.get(c) or "").strip() for c in OWN_COLS)
        override = rec.get("Tier") not in (None, "") and implied_tier(rec.get("Rank")) not in (None, rec.get("Tier"))
        if has_own or override or k in busy_names:
            keep_dropped.append(rec)
        else:
            remove.append(rec)
    moves = []
    for r in result["companies"]:
        old = existing.get(r["name"].lower())
        if old and old.get("Rank") not in (None, ""):
            moves.append((r["name"], int(old["Rank"]), r["rank"]))
    tier_changes = []
    for r in result["companies"]:
        old = existing.get(r["name"].lower())
        if not old:
            continue
        t = final_tier(r, old)
        if old.get("Tier") not in (None, "") and t != old.get("Tier"):
            tier_changes.append((r["name"], old.get("Tier"), t))
    return {"joining": joining, "keep_dropped": keep_dropped, "remove": remove,
            "moves": sorted(moves, key=lambda m: -abs(m[1] - m[2]))[:25], "tier_changes": tier_changes,
            "old_ranked": len(old_ranked)}


def final_tier(r, old):
    """Keep a tier the user changed by hand; otherwise use the new tier."""
    if old:
        t = old.get("Tier")
        if t not in (None, "") and implied_tier(old.get("Rank")) not in (None, t):
            return t
    return r["tier"]


def _style(cell):
    from copy import copy
    return (copy(cell.font), copy(cell.fill), cell.number_format, copy(cell.alignment), copy(cell.border))


def _apply_style(cell, st):
    cell.font, cell.fill, cell.number_format, cell.alignment, cell.border = st


def write_companies(wb, result, existing, keep_dropped, data_through):
    ws = wb["Companies"]
    head = [str(c.value or "").strip() for c in ws[1]]
    col = {h: i + 1 for i, h in enumerate(head) if h}
    styles = {i: _style(ws.cell(2, i)) for i in range(1, len(head) + 1)} if ws.max_row >= 2 else {}
    if ws.max_row >= 2:
        ws.delete_rows(2, ws.max_row - 1)

    def put(rownum, r, old, dropped=False):
        vals = {
            "Rank": None if dropped else r["rank"], "Company": r["name"],
            "Tier": (old or {}).get("Tier") if dropped else final_tier(r, old),
            "Role focus": r["focus"], "Score": r["score"],
            "Product manager (new hire)": r["pm"], "Technical program manager (new hire)": r["tpm"],
            "Strategy (new hire)": r["strat"], "Product marketing (new hire)": r["pmm"],
            "Product ops (new hire)": r["pops"], "Role filings, new hire": r["nh"],
            "Role filings, all types": r["all_roles"], "New-hire share": f"=IFERROR(K{rownum}/L{rownum},0)",
            "All filings, all roles": r["all"], "Wage level III or IV share": r["wage34"],
            "Median offered salary (USD)": r["median"], "Entry-level titles": r["entry"],
            "Senior-level titles": r["senior"], "Top states": r["states"], "Top cities": r["cities"],
            "Legal entities merged": r["entities"],
            "Flags": "; ".join(x for x in [r.get("flags", ""), F_DROPPED if dropped else ""] if x),
        }
        for c in OWN_COLS:
            vals[c] = (old or {}).get(c)
        for h, v in vals.items():
            if h in col:
                cell = ws.cell(rownum, col[h], v)
                if col[h] in styles:
                    _apply_style(cell, styles[col[h]])

    rownum = 2
    for r in result["companies"]:
        put(rownum, r, existing.get(r["name"].lower()))
        rownum += 1
    for old in keep_dropped:
        name = str(old.get("Company")).strip()
        r = result["all"].get(name.lower())
        if r is None:  # no role filings at all in the new window
            r = {"name": name, "focus": old.get("Role focus"), "score": 0, "pm": 0, "tpm": 0, "strat": 0, "pmm": 0,
                 "pops": 0, "nh": 0, "all_roles": 0, "all": None, "wage34": None, "median": None, "entry": 0,
                 "senior": 0, "states": "", "cities": "", "entities": old.get("Legal entities merged"), "flags": ""}
        put(rownum, r, old, dropped=True)
        rownum += 1
    return rownum - 2


def write_excluded(wb, result):
    if "Excluded" not in wb.sheetnames:
        return
    ws = wb["Excluded"]
    if ws.max_row >= 2:
        ws.delete_rows(2, ws.max_row - 1)
    for r in result["excluded"]:
        ws.append([r["name"], r["why"], r["score"], r["nh"], r["all_roles"], r["all"], r["states"]])


def write_entities(wb, result):
    if "Entity groups" not in wb.sheetnames:
        return
    ws = wb["Entity groups"]
    if ws.max_row >= 2:
        ws.delete_rows(2, ws.max_row - 1)
    for r in result["companies"]:
        if r["entities"] > 1:
            for name, fe, alln, roles_all, roles_nh in r["entity_rows"]:
                ws.append([r["rank"], r["name"], name, fe, alln, roles_all, roles_nh])


def update_readme(wb, result):
    if "Read me" not in wb.sheetnames:
        return
    ws = wb["Read me"]
    st = result["stats"]
    start, end = st["window"]
    f = st["focus"]
    files = "; ".join(f"{n}: {lo} to {hi}" for n, (lo, hi, _) in st["files"].items())
    sa = st["score_at"]
    t1, t2 = st["tier_scores"]
    texts = {
        "Built": dt.date.today().strftime("%d %B %Y").lstrip("0") + " (refreshed from the site)",
        "Source": "US Department of Labor, Office of Foreign Labor Certification, LCA public disclosure files: "
                  + ", ".join(st["files"]) + " (dol.gov/agencies/eta/foreign-labor/performance).",
        "Data window": f"Decisions from {start} to {end}, the 12 months up to the latest decision in the files. {files}.",
        "Cases used": f"{st['cases']:,} cases in the window after removing {st['dupes']:,} that appear in more than one "
                      f"file (the later record is kept). {st['certified']:,} are certified H-1B. {st['role_cases']:,} "
                      f"match your role titles, of which {st['role_newhire']:,} are for new hires. Only status "
                      "'Certified' on visa class H-1B is counted. Withdrawn and denied cases, E-3 and H-1B1 are out.",
        "Role focus": f"Product, Strategy, or Product and strategy, from where the company's new-hire filings fall. "
                      f"In this list: {f.get('Product', 0)} Product, {f.get('Product and strategy', 0)} Product and "
                      f"strategy, {f.get('Strategy', 0)} Strategy. Filter on it to see one side only.",
        "Rule": f"Set by filing volume. Tier 1 is ranks 1 to 75 (score {t1} or more). Tier 2 is ranks 76 to 150 "
                f"(score {t2} or more). Tier 3 is the rest, ranks 151 to 300. Ties are ordered by role filings of any "
                "type, then by name. There is no Skip. A tier you changed by hand is kept when the numbers refresh.",
        "Thin tail": "Scores fall quickly. " + ", ".join(f"rank {k} has a score of {v:g}" for k, v in sa.items())
                     + f". Only {st['score5']} companies score 5 or more.",
        "Age": f"The data stops at {end}. The Department of Labor publishes about six weeks after each quarter ends. "
               "Add the new file to the folder and press Refresh on the H-1B page of the site.",
    }
    for row in ws.iter_rows(min_row=1, max_col=2):
        label = str(row[0].value or "").strip()
        if label in texts:
            row[1].value = texts[label]
