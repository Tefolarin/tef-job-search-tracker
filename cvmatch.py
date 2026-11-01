"""Compare job descriptions with your CVs, on this laptop only. Word matching (plus meaning, see meaning.py), no AI service.

For each role:
- the CV for that role type (PM, PMM or Strategy) and your long CV are checked against the role's key terms;
- tier: Strong match, Small tweaks (the long CV has what the role CV lacks), Major tweaks, Weak match;
- "Add from your long CV": key terms the long CV has and the role CV doesn't;
- "Not in either CV": key terms neither has.
CVs live in the CV folder. Names just need to contain PM, PMM, Strategy or Long.
"""
import os
import re
import glob
from functools import lru_cache

HERE = os.path.dirname(os.path.abspath(__file__))
CV_DIR = os.path.join(HERE, "CV")

# Key terms: what product, marketing and strategy job descriptions ask for. Each has the ways it's usually written.
TERMS = {
    "roadmap": r"roadmap\w*",
    "product requirements (PRDs)": r"\bprds?\b|product requirements?|requirements documents?|user stories|specs\b|specifications",
    "experimentation / A-B testing": r"a/b test\w*|ab test\w*|a\|b (test\w*|experiment\w*)|experimentation|experiments\b|test.and.learn",
    "SQL": r"\bsql\b",
    "Python": r"\bpython\b",
    "dashboards / BI tools": r"tableau|power bi|looker|dashboards?|business intelligence",
    "data analysis and metrics": r"data analysis|analytics|data.driven|\bmetrics\b|\bkpis?\b",
    "user / customer research": r"user research|customer research|customer discovery|customer interviews|discovery interviews|"
                                r"customer insights?|voice of (the )?customer|usability",
    "go-to-market and launch": r"go.to.market|\bgtm\b|route.to.market|product launch\w*|launch(es|ed|ing)? (new )?products?",
    "positioning and messaging": r"positioning|messaging|value propositions?|narratives?",
    "pricing and monetization": r"pricing|monetization|monetisation|revenue strateg\w+",
    "segmentation and personas": r"segmentation|personas?|customer segments?",
    "competitive analysis": r"competitive (analysis|intelligence|landscape|insights?)|competitors?|benchmark\w*",
    "market sizing": r"market sizing|\btam\b|sizing|market opportunit\w+",
    "business cases": r"business cases?|investment cases?",
    "financial modelling": r"financial model\w*|valuation|\bdcf\b|unit economics|forecast\w*",
    "P&L ownership": r"p&l|p & l|profit and loss|profitability",
    "strategic planning": r"strategic plan\w*|long.range plan\w*|annual planning|planning cycles?|\bokrs?\b|operating plans?",
    "executive communication": r"executives?|c.suite|senior leadership|leadership teams?|board of directors",
    "cross-functional leadership": r"cross.functional\w*",
    "agile delivery": r"\bagile\b|scrum|sprints?",
    "APIs and platforms": r"\bapis?\b|platform products?|developer platforms?",
    "B2B / enterprise": r"\bb2b\b|enterprise customers|enterprise software|\bsaas\b",
    "consumer products": r"\bconsumer products?|\bb2c\b|consumer.facing",
    "growth and funnel": r"growth|acquisition|activation|retention|conversion|funnels?",
    "partnerships": r"partnerships?|channel partners?|strategic partners?",
    "sales enablement": r"sales enablement|enablement|pitch decks?|sales teams?",
    "campaigns and demand generation": r"demand gen\w*|campaigns?|lead gen\w*",
    "M&A and corporate development": r"\bm&a\b|mergers|corporate development|due diligence",
    "operations and process improvement": r"process improvement|operating models?|operational efficiency|lean|six sigma",
    "management consulting": r"management consult\w*|consulting (firm|background|experience)|strategy consult\w*",
    "international markets": r"international|emerging markets|multiple markets|global markets|cross.border",
    "mobile apps": r"\bmobile\b|\bios\b|android",
    "AI and machine learning": r"machine learning|\bai\b|artificial intelligence|\bllms?\b|generative",
    "payments and cards": r"payments?|\bcards?\b|fintech|issuing|acquiring",
    "regulation and compliance": r"regulat\w+|compliance",
    "e-commerce and marketplaces": r"(?<!cloud )marketplaces?|e-?commerce|merchants?|checkout",
    "advertising": r"advertising|advertisers?|\bads\b|ad tech",
    "technical degree / background": r"technical background|computer science|engineering degree|technical degree|"
                                     r"\bb\.?s\.? in (computer|engineering)|bachelor of engineering|degree in engineering",
    "MBA": r"\bmba\b|master of business",
}
_RX = {k: re.compile(r"\b(?:" + v + r")", re.I) for k, v in TERMS.items()}

# Industry words on the CV side (same groups as the job watcher, a little stricter so "payments infrastructure"
# doesn't count as cloud experience and FMCG counts as commerce).
CV_INDUSTRY = {
    "Financial services": r"payments?|fintech|banking|\bbanks?\b|lending|credit cards?|financial services|card issuing",
    "Commerce and retail": r"e-?commerce|marketplaces?|\bretail|merchants?|checkout|\bfmcg\b|\bcpg\b|consumer goods",
    "Advertising": r"advertis\w*|\bad ?tech\b",
    "Healthcare": r"healthcare|health care|clinical|medical|patients?|pharma\w*",
    "Enterprise SaaS": r"\bb2b\b|\bsaas\b|enterprise software",
    "AI and machine learning": r"machine learning|artificial intelligence|generative ai|\bai\b",
    "Cloud and infrastructure": r"\bcloud\b|data cent(er|re)s?|kubernetes|devops|azure",
    "Security": r"cyber ?security|zero trust",
    "Mobility and automotive": r"automotive|vehicles?|mobility|transport",
    "Media and entertainment": r"streaming|entertainment|music|media",
    "Gaming": r"gaming|video games?",
    "Travel and hospitality": r"\btravel|hospitality|airlines?|hotels?|airport|aerotropolis",
    "Logistics": r"logistics|supply chain|fulfil?lment|warehous\w+",
    "Hardware and semiconductors": r"semiconductors?|hardware|silicon|firmware",
    "Telecom": r"telecom\w*|wireless",
    "Public sector": r"public sector|government|public asset",
    "Education": r"education|edtech|training program",
}
_CV_IND = {k: re.compile(r"\b(?:" + v + r")", re.I) for k, v in CV_INDUSTRY.items()}

TIERS = ["Strong match", "Small tweaks", "Major tweaks", "Weak match"]
STRONG, SMALL, MAJOR = 0.70, 0.70, 0.45
MY_YEARS = 8


# ---------- reading the CVs ----------
_cache = {}


def _read(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(path).pages)
    if ext == ".docx":
        import docx
        d = docx.Document(path)
        parts = [p.text for p in d.paragraphs]
        for t in d.tables:
            for r in t.rows:
                parts += [c.text for c in r.cells]
        return "\n".join(parts)
    if ext in (".txt", ".md"):
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    return ""


def _kind(name):
    n = os.path.splitext(os.path.basename(name))[0].lower()
    if re.search(r"long|master|full", n):
        return "long"
    if re.search(r"pmm|marketing", n):
        return "pmm"
    if re.search(r"strat", n):
        return "strategy"
    if re.search(r"\bpm\b|_pm|pm\b|product", n):
        return "pm"
    return None


def load_cvs():
    """Returns ({kind: text}, problems). Re-reads a file only when it changes."""
    cvs, problems = {}, []
    for path in sorted(glob.glob(os.path.join(CV_DIR, "*"))):
        kind = _kind(path)
        if not kind or os.path.basename(path).startswith("~$"):
            continue
        key = (path, os.path.getmtime(path))
        if key not in _cache:
            try:
                _cache[key] = _read(path)
            except Exception as e:
                _cache[key] = ""
                problems.append(f"Couldn't read {os.path.basename(path)} ({type(e).__name__}).")
        text = _cache[key]
        if len(text.split()) < 50:
            problems.append(f"{os.path.basename(path)} has almost no readable text. If it's a scanned PDF, save it "
                            "from Word as a PDF instead.")
            continue
        cvs[kind] = text
    return cvs, problems


# ---------- scoring ----------
@lru_cache(maxsize=4096)
def _weights_cached(desc):
    return _weights(desc)


REQ_BOOST, PREF_DAMP = 1.6, 0.7


@lru_cache(maxsize=4096)
def weights_for(desc):
    """Key terms weighted by where they appear: a term in the requirements counts 1.6 times, a term only in the
    preferred section 0.7 times. Returns (weights, required terms)."""
    import jdtext
    w = dict(_weights(desc))
    req, pref = jdtext.split(desc)
    req_terms = set()
    if req or pref:
        for t in list(w):
            if req and _RX[t].search(req):
                w[t] = round(w[t] * REQ_BOOST, 2)
                req_terms.add(t)
            elif pref and _RX[t].search(pref):
                w[t] = round(w[t] * PREF_DAMP, 2)
    return w, frozenset(req_terms)


def _weights(desc):
    """Key terms in this description, weighted by how often they come up (1 to 2). Company blurbs, benefits, pay and
    legal text are left out first (jdtext.clean), so "we experiment" or "this posting is to advertise" don't count."""
    import jdtext
    desc = jdtext.clean(desc)
    w = {}
    for term, rx in _RX.items():
        n = len(rx.findall(desc))
        if n:
            w[term] = 1.0 + min(n - 1, 2) * 0.5
    return w


@lru_cache(maxsize=32)
def _covered(cv_text):
    return {term for term, rx in _RX.items() if rx.search(cv_text)}


@lru_cache(maxsize=32)
def _cv_industries(cv_text):
    return {k for k, rx in _CV_IND.items() if len(rx.findall(cv_text)) >= 2}


def cv_for(label):
    return {"Product marketing": "pmm", "Strategy": "strategy", "MBA programme": "strategy"}.get(label, "pm")


def score(label, desc, cvs, industries=(), years=None, clearance=False, weights=None, req_terms=(),
          cs_degree=False, meaning=None):
    """Returns a dict, or None if the description or CVs are missing.
    weights: the role's key terms if already worked out (the job watcher stores them), so the description isn't re-read.
    meaning: {"score": 0-1} from meaning.py when it has read this role. The match level then blends keywords and
    meaning half and half for all your CVs together, and shifts the role CV's figure by the same amount. The
    percentages shown stay the keyword ones, with the meaning figure shown alongside."""
    kind = cv_for(label)
    role_cv = cvs.get(kind) or cvs.get("long")
    long_cv = cvs.get("long") or role_cv
    if not role_cv or (not desc and not weights):
        return None
    if weights:
        w = weights
    else:
        w, req_terms = weights_for(desc)
    req_terms = set(req_terms or ())
    if not w:
        return None
    total = sum(w.values())
    have_role, have_long = _covered(role_cv), _covered(long_cv) | _covered(role_cv)
    role_cov = sum(v for t, v in w.items() if t in have_role) / total
    long_cov = sum(v for t, v in w.items() if t in have_long) / total
    by_weight = sorted(w, key=lambda t: -w[t])
    add = [t for t in by_weight if t in have_long and t not in have_role]
    gaps = [t for t in by_weight if t not in have_long]
    req_gaps = [t for t in gaps if t in req_terms]
    gaps = [t for t in gaps if t not in req_terms]
    req_total = sum(w[t] for t in req_terms if t in w)
    req_cov = (sum(w[t] for t in req_terms if t in w and t in have_long) / req_total) if req_total else None

    r_cov, l_cov = role_cov, long_cov
    if meaning:
        import meaning as _m
        l_cov = (1 - _m.BLEND) * long_cov + _m.BLEND * meaning["score"]
        r_cov = max(0.0, min(1.0, role_cov + (l_cov - long_cov)))
    if r_cov >= STRONG:
        tier = 0
    elif l_cov >= SMALL or (l_cov - r_cov >= 0.2 and l_cov >= 0.6):
        tier = 1
    elif l_cov >= MAJOR:
        tier = 2
    else:
        tier = 3
    reasons = []
    cv_inds = _cv_industries(long_cv)
    missing_ind = [n for n, k in industries if k == "asks" and n not in cv_inds]
    if missing_ind:
        tier = max(tier, 2)
        reasons.append("asks for " + " and ".join(missing_ind) + " experience, which your CVs don't show")
    if req_cov is not None and req_cov < 0.6 and len(req_gaps) >= 2:
        tier = max(tier, 2)
        reasons.append("misses " + str(len(req_gaps)) + " of the stated requirements")
    if cs_degree:
        tier = max(tier, 2)
        reasons.append("asks for a computer science degree")
    if years and years > MY_YEARS + 2:
        tier = min(tier + 1, 3)
        reasons.append(f"asks for {years}+ years")
    if clearance:
        tier = 3
        reasons.append("needs a security clearance")
    # one plain list of what's missing: required skills first, then the knockouts, then other skills
    missing = [f"{t} (required)" for t in req_gaps]
    if years and years > MY_YEARS + 2:
        missing.append(f"{years}+ years of experience")
    missing += [f"{n[0].lower() + n[1:]} experience" for n in missing_ind]
    if cs_degree:
        missing.append("a computer science degree")
    if clearance:
        missing.append("a security clearance")
    missing += gaps
    req_in = [t for t in req_terms if t in w]
    return {"tier": tier, "tier_name": TIERS[tier], "cv": {"pm": "PM CV", "pmm": "PMM CV", "strategy": "Strategy CV"}.get(
            kind if cvs.get(kind) else "long", "long CV"), "role_cov": round(role_cov * 100), "long_cov": round(long_cov * 100),
            "add": add[:8], "gaps": gaps[:8], "req_gaps": req_gaps[:8], "reasons": reasons, "terms": len(w),
            "req_cov": round(req_cov * 100) if req_cov is not None else None,
            "req_n": len(req_in), "req_have": sum(1 for t in req_in if t in have_long), "missing": missing[:10],
            "meaning": round(meaning["score"] * 100) if meaning else None}
