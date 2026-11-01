"""Your rewritten bullets, one set per role type, read from "Bullet rewrites.docx" in the PM Tracker folder.

The file has one Heading 1 per role type (the names in ROLE_TYPES, exactly) and under each a table with the columns
ID | Employer | Fit | Rewritten bullet. Fit is Core, Strong or Reserve. The CV generator uses the section for the
job's role type; bullets left out of a section aren't used for that role type. If the file is missing, or a role type
has no section, the generator uses the wording from your CVs as before. A bullet with a [ or ] in it (a placeholder
not filled in) is never used.
"""
import os
import re

import cvlib

HERE = os.path.dirname(os.path.abspath(__file__))
FILE = os.path.join(HERE, "Bullet rewrites.docx")
FALLBACK = os.path.join(HERE, "CV", "Bullet rewrites.docx")  # used only if the main-folder copy is missing


def path():
    """Where the rewrites are read from: the PM Tracker folder, or the CV folder if it's only there."""
    return FILE if os.path.exists(FILE) or not os.path.exists(FALLBACK) else FALLBACK

ROLE_TYPES = [
    "Product management",
    "Product marketing",
    "Strategy & operations / BizOps",
    "Corporate strategy / internal consulting",
    "MBA leadership & rotational programmes",
    "Commercial, partnerships & solution sales",
    "Pricing, revenue management & analytics",
]

# Which role type a job is, from its title. First match wins, so the order matters (an "MBA Product Marketing
# Leadership Program" is an MBA programme; a "Pricing Product Manager" is pricing).
BY_TITLE = [
    ("MBA leadership & rotational programmes",
     r"\bmba\b|leadership (development )?program|rotational|development program|graduate (hire|program)|"
     r"associate program|university graduate|accelerated leadership|general management associate|pathway"),
    ("Product marketing", r"product marketing|\bpmm\b"),
    ("Pricing, revenue management & analytics", r"pricing|revenue (management|science|strategy)|monetization strategy"),
    ("Commercial, partnerships & solution sales",
     r"solution sales|partnership|business development|business manager|commercial (lead|manager|strategy)|"
     r"account (manager|executive)|sales strategy|alliances"),
    ("Strategy & operations / BizOps",
     r"strategy (&|and) operations|strategy operations|bizops|business operations|strategy (&|and) planning|"
     r"planning manager|chief of staff|operations (strategy|lead)"),
    ("Corporate strategy / internal consulting",
     r"corporate strategy|business strategy|internal consulting|strategic (initiatives|projects|planning)|"
     r"strategy (manager|lead|associate|director|principal)|transformation|corporate development"),
    ("Product management", r"product (manager|owner|lead|management|director)|\bapm\b|\bgpm\b|product ops|product operations"),
]
_BY_TITLE = [(n, re.compile(rx, re.I)) for n, rx in BY_TITLE]
BY_LABEL = {"Product marketing": "Product marketing", "Strategy": "Strategy & operations / BizOps",
            "MBA programme": "MBA leadership & rotational programmes"}

FIT_BONUS = {"core": 1.6, "strong": 0.8, "reserve": 0.0}
# Different IDs that tell the same story; never two of a pair on one CV (the rewrites don't always name the project,
# so the wording alone can't catch these).
SAME_STORY = [{"PWC-03", "PWC-13"},   # Aerotropolis demand model / Aerotropolis viability assessments
              {"ACC-07", "ACC-13"},   # campaigns with Group Marketing / campaigns with Marketing and branch teams
              {"ACC-03", "ACC-10"},   # requirements from research and data with engineering, twice
              {"ACC-09", "ACC-11"},   # performance reporting, twice
              {"ISW-03", "ISW-08"}]   # executive dashboards, twice


def same_story(a, b):
    return bool(a and b) and any({a, b} == pair for pair in SAME_STORY)
_EMP_KEY = {n.lower(): k for k, n, _ in cvlib.EMPLOYERS}
_ID_PREFIX = {"tts": "tts", "mc": "mastercard", "isw": "interswitch", "pwc": "pwc", "acc": "access"}
_norm = lambda s: re.sub(r"\s+", " ", (s or "").replace("’", "'")).strip()


def role_type(title, label=""):
    """The role type for a job title; falls back to the watcher's label (Product marketing, Strategy, Product)."""
    for name, rx in _BY_TITLE:
        if rx.search(title or ""):
            return name
    return BY_LABEL.get(label, "Product management")


_cache = {}


def load():
    """{role type: {employer key: [ {id, fit, text}, ... ]}}. Empty if the file isn't there. Re-read when it changes."""
    src = path()
    try:
        mtime = (src, os.path.getmtime(src))
    except OSError:
        return {}
    if _cache.get("mtime") == mtime:
        return _cache["data"]
    import docx
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    d = docx.Document(src)
    names = {n.lower(): n for n in ROLE_TYPES}
    data, current, skipped = {}, None, []
    for el in d.element.body.iterchildren():
        if el.tag == qn("w:p"):
            p = Paragraph(el, d)
            text = _norm(p.text)
            if text.lower() in names:
                current = names[text.lower()]
                data.setdefault(current, {})
            elif p.style is not None and p.style.name.lower().startswith("heading") and text:
                current = None  # a heading that isn't a role type: ignore the table under it
        elif el.tag == qn("w:tbl") and current:
            t = Table(el, d)
            head = [_norm(c.text).lower() for c in t.rows[0].cells]
            col = lambda *keys: next((i for i, h in enumerate(head) if any(k in h for k in keys)), None)
            i_id, i_emp, i_fit = col("id"), col("employer"), col("fit")
            i_txt = col("bullet", "rewrit", "wording")
            if i_id is None or i_txt is None:
                continue
            for row in t.rows[1:]:
                cells = [_norm(c.text) for c in row.cells]
                bid, text = cells[i_id].upper(), cells[i_txt]
                if not bid or not text:
                    continue
                if "[" in text or "]" in text:
                    skipped.append(f"{current}: {bid}")
                    continue
                emp = _EMP_KEY.get(cells[i_emp].lower()) if i_emp is not None else None
                emp = emp or _ID_PREFIX.get(bid.split("-")[0].lower())
                if not emp or emp in cvlib.NEVER_USE:
                    continue
                fit = cells[i_fit].lower() if i_fit is not None else ""
                bucket = data[current].setdefault(emp, [])
                if not any(b["id"] == bid for b in bucket):
                    bucket.append({"id": bid, "fit": fit if fit in FIT_BONUS else "", "text": text})
    data = {k: v for k, v in data.items() if v}
    _cache.update(mtime=mtime, data=data, skipped=skipped)
    return data


def for_job(title, label=""):
    """(role type, {employer key: [rewrites]}). The dict is empty when there's no section for that role type."""
    rt = role_type(title, label)
    return rt, load().get(rt, {})


def skipped():
    load()
    return list(_cache.get("skipped", []))
