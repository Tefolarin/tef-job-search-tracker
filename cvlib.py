"""Your bullet library: every bullet from your CVs, grouped by employer, with versions of the same achievement
grouped together. The tailored-CV builder picks from this. Nothing here is written or reworded; it's your text.
"""
import os
import re
import glob

HERE = os.path.dirname(os.path.abspath(__file__))
CV_DIR = os.path.join(HERE, "CV")

# Employers as they appear on the Strategy CV (the template). PwC is one employer, Associate and Senior Associate together.
EMPLOYERS = [
    ("tts", "Training The Street", r"training the street"),
    ("mastercard", "Mastercard", r"mastercard"),
    ("interswitch", "Interswitch", r"interswitch"),
    ("pwc", "PwC", r"pricewaterhouse|\bpwc\b"),
    ("access", "Access Bank", r"access bank"),
    # Tanit Medical is still recognised so its bullet isn't mistaken for Interswitch's, but it is never used
    ("tanit", "Tanit Medical", r"tanit medical"),
]
NEVER_USE = {"tanit"}  # the user's instruction, 17 October 2026
_EMP_RX = [(k, re.compile(rx, re.I)) for k, _, rx in EMPLOYERS]
EMP_NAME = {k: n for k, n, _ in EMPLOYERS}
SECTION = re.compile(r"^(education|experience|professional experience|skills|additional information|publications|"
                     r"certifications|profile|activities)", re.I)
DATE_HINT = re.compile(r"(19|20)\d\d")


def employer_of(line):
    """The employer key if this line is an employer heading (name, place and dates), else None."""
    if not DATE_HINT.search(line) or ("–" not in line and " - " not in line):
        return None
    for k, rx in _EMP_RX:
        if rx.search(line[:80]):
            return k
    return None


def _clean(t):
    t = t.replace(" ", " ").replace("’", "'").strip()
    t = re.sub(r"\s+", " ", t)
    return t.strip(" •▪·-")


# ---------- reading each CV into {employer: [bullets]} ----------
def from_docx(path):
    import docx
    d = docx.Document(path)
    out, emp = {}, None
    for p in d.paragraphs:
        text = p.text.strip()
        if not text:
            continue
        k = employer_of(text)
        if k:
            emp = k
            continue
        if SECTION.match(text) and len(text) < 40:
            emp = None
            continue
        pPr = p._p.pPr
        is_bullet = (pPr is not None and pPr.numPr is not None) or text[:1] in "•▪·"
        if emp and is_bullet:
            out.setdefault(emp, []).append(_clean(text))
    return out


def from_pdf(path):
    from pypdf import PdfReader
    lines = []
    for page in PdfReader(path).pages:
        lines += (page.extract_text() or "").splitlines()
    out, emp, cur = {}, None, None

    def flush():
        nonlocal cur
        if emp and cur:
            out.setdefault(emp, []).append(_clean(cur))
        cur = None

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        k = employer_of(line)
        if k:
            flush()
            emp = k
            continue
        if SECTION.match(line) and len(line) < 40:
            flush()
            emp = None
            continue
        if line[:1] in "•▪·":
            flush()
            cur = line[1:].strip()
        elif cur is not None:
            # a wrapped line of the current bullet; keep hyphenated words whole ("AI-" + "driven")
            cur = cur + line if cur.endswith("-") else cur + " " + line
    flush()
    return out


def read_cv(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        return from_docx(path)
    if ext == ".pdf":
        return from_pdf(path)
    return {}


# ---------- grouping versions of the same achievement ----------
_STOP = set("a an and the of to in for by on with across from into at as that this their its our is was were be "
            "which who while over under through".split())


def _words(t):
    return {w for w in re.findall(r"[a-z]+", t.lower()) if w not in _STOP and len(w) > 2}


def _metrics(t):
    """Distinctive figures: percentages, money, multipliers ("23%", "$17M", "3x", "tripled")."""
    out = set()
    for m in re.findall(r"\$\s?\d+(?:\.\d+)?\s*[mbk]?|\d+(?:\.\d+)?\s*%|\b\d+x\b|tripled|doubled", t, re.I):
        out.add(re.sub(r"\s", "", m.lower()))
    if out & {"tripled", "3x"}:
        out |= {"tripled", "3x"}
    return out


def _lead(t):
    return [w for w in re.findall(r"[a-z]+", t.lower()) if w not in _STOP][:3]


def _compounds(t):
    """Hyphenated words and capitalised pairs, e.g. "AI-integrated", "Group Marketing"."""
    out = {w.lower() for w in re.findall(r"\b\w+-\w+(?:-\w+)*\b", t)}
    out |= {m.lower() for m in re.findall(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", t)}
    return out


def same_achievement(a, b):
    """Two bullets describe the same achievement (same employer is assumed)."""
    wa, wb = _words(a), _words(b)
    if not wa or not wb:
        return False
    j = len(wa & wb) / len(wa | wb)
    if j >= 0.5:
        return True
    if _metrics(a) & _metrics(b):  # the same figure under the same employer
        return True
    if _lead(a) == _lead(b) and len(_lead(a)) == 3:  # "Mentored junior staff ..."
        return True
    return j >= 0.15 and bool(_compounds(a) & _compounds(b))


# which CV a bullet came from, for the "about this CV" note; the long CV first so its wording is the default
SOURCE_ORDER = ["strategy", "long", "pm", "pmm"]


def _kind(path):
    n = os.path.splitext(os.path.basename(path))[0].lower()
    if re.search(r"long|master|full", n):
        return "long"
    if re.search(r"pmm|marketing", n):
        return "pmm"
    if re.search(r"strat", n):
        return "strategy"
    if re.search(r"\bpm\b|pm\b|product", n):
        return "pm"
    return None


_cache = {}


def library():
    """{employer: [ [ {text, source}, ... versions ], ... achievements ]}, re-read only when a CV file changes."""
    files = sorted(p for p in glob.glob(os.path.join(CV_DIR, "*")) if _kind(p) and not os.path.basename(p).startswith("~$"))
    key = tuple((p, os.path.getmtime(p)) for p in files)
    if key in _cache:
        return _cache[key]
    per_source = {}
    for p in files:
        try:
            per_source[_kind(p)] = read_cv(p)
        except Exception:
            per_source[_kind(p)] = {}
    lib = {}
    for src in SOURCE_ORDER:
        for emp, bullets in (per_source.get(src) or {}).items():
            if emp in NEVER_USE:
                continue
            groups = lib.setdefault(emp, [])
            for b in bullets:
                if len(b) < 25:
                    continue
                for g in groups:
                    if any(v["text"] == b for v in g):
                        if not any(v["source"] == src for v in g):
                            g[0].setdefault("also_in", []).append(src)
                        break
                    if any(same_achievement(v["text"], b) for v in g):
                        g.append({"text": b, "source": src})
                        break
                else:
                    groups.append([{"text": b, "source": src}])
    _cache.clear()
    _cache[key] = lib
    return lib


# ---------- skills ----------
def _skills_from_text(text):
    """Skill names from "Skills:" lines and the long CV's "Business & Analytics:" / "Strategy & Product:" lines."""
    out = []
    flat = re.sub(r"\s*\n\s*", " ", text)
    for label in ("Skills", "Business & Analytics", "Strategy & Product"):
        for m in re.finditer(re.escape(label) + r"\s*:\s*(.+?)(?=(Activities|Hobbies|Review Interests|Business & Analytics|"
                             r"Strategy & Product|Work Authorization|$))", flat):
            for s in re.split(r",(?![^()]*\))", m.group(1)):
                s = s.strip(" .;")
                if 2 < len(s) < 50:
                    out.append(s)
    return out


def skills_pool():
    """Every skill named on your CVs, Strategy CV first, without duplicates."""
    files = sorted(p for p in glob.glob(os.path.join(CV_DIR, "*")) if _kind(p) and not os.path.basename(p).startswith("~$"))
    by_kind = {}
    for p in files:
        try:
            if p.lower().endswith(".docx"):
                import docx
                text = "\n".join(par.text for par in docx.Document(p).paragraphs)
            else:
                from pypdf import PdfReader
                text = "\n".join((pg.extract_text() or "") for pg in PdfReader(p).pages)
            by_kind[_kind(p)] = _skills_from_text(text)
        except Exception:
            pass
    seen, out = set(), []
    for k in SOURCE_ORDER:
        for s in by_kind.get(k, []):
            key = re.sub(r"[^a-z]", "", s.lower().replace("go-to-market", "gotomarket"))
            if key not in seen:
                seen.add(key)
                out.append(s)
    return out
