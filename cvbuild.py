"""Make a one-page CV tailored to one job, from your Strategy CV's Word file and your bullets.

Runs only when you press Generate CV on a job. It never rewrites a sentence: it chooses which of your bullets to use,
which wording of each, how many per employer, and their order; and it reorders your skills line.
- Bullets come from "Bullet rewrites.docx", the section for the job's role type (see rewrites.py), with Core bullets
  preferred, then Strong, then Reserve. An employer with nothing in that section, or a role type with no section,
  uses the wording from your CVs instead.
- Requirements first: for each requirement the job states, your closest bullet goes on if it's a close match and
  its employer has room; the rest of the places are filled by the usual scoring.
- Never two bullets claiming the same result under one employer (e.g. two different adoption figures at Mastercard).
- Employers stay in date order, as on your Strategy CV. The best-fitting employer gets more bullets, the others fewer.
- Same number of bullets as your Strategy CV (12), and about the same length, so it stays on one page.
- Saved in Tailored CVs/<Company - Role>/, never overwriting an earlier version.
"""
import os
import re
import copy
import json
import datetime as dt

import cvlib
import cvmatch
import rewrites
import meaning

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "Tailored CVs")
INFO_FILE = os.path.join(HERE, "data", "tailored.json")

MIN_PER_EMPLOYER = {"tts": 1, "mastercard": 1, "interswitch": 1, "pwc": 1, "access": 1}
MAX_PER_EMPLOYER = {"tts": 2, "mastercard": 3, "interswitch": 3, "pwc": 3, "access": 3}
MEANING_W, RERANK_W = 12.0, 2.5  # weight of meaning coverage and the re-ranker against keyword scores (calibrated)
LENGTH_SLACK = 1.05  # at most 5% more characters in the bullets than your Strategy CV has

# What kind of job is it? Each signal nudges the employers that show that kind of work.
SIGNALS = {
    "pwc": r"\bclients?\b|consult\w*|advisory|engagements?|transformation|due diligence|feasibility",
    "interswitch": r"strategic planning|operating (plan|rhythm|cadence|model)|business reviews?|\bokrs?\b|planning cycles?|"
                   r"executive team|leadership team|internal strategy|strategy (and|&) operations|bizops|cross.functional",
    "access": r"roadmap|product launch|launch(ed|ing)? (new )?products?|product requirements|\bprds?\b|\bship\w*|"
              r"user research|discovery|agile|sprints?|0 to 1|zero to one",
    "mastercard": r"p&l|profit and loss|portfolio|card (products?|issuing|programs?)|issuers?|premium|monetization",
    "tts": r"financial model\w*|valuation|\bdcf\b|\blbo\b|investment banking|training|enablement|\bai\b|analytics dashboards?",
}
_SIG = {k: re.compile(v, re.I) for k, v in SIGNALS.items()}
_STOP = set("a an and the of to in for by on with across from into at as that this their its our is was were be which "
            "who while over under through you your we will are have has can more most all any not but or".split())


# ---------- the template ----------
def template_path():
    for name in os.listdir(cvlib.CV_DIR):
        if name.lower().endswith(".docx") and cvlib._kind(name) == "strategy" and not name.startswith("~$"):
            return os.path.join(cvlib.CV_DIR, name)
    raise FileNotFoundError("The Strategy CV in Word format wasn't found in the CV folder.")


def _is_bullet(p):
    pPr = p._p.pPr
    return pPr is not None and pPr.numPr is not None


def template_layout(doc):
    """{employer: [bullet paragraphs]} in page order, the skills paragraph, and the name on the CV."""
    blocks, order, emp, skills = {}, [], None, None
    for p in doc.paragraphs:
        text = p.text.strip()
        k = cvlib.employer_of(text) if text else None
        if k:
            emp = k
            order.append(k)
            blocks[k] = []
            continue
        if text and cvlib.SECTION.match(text) and len(text) < 40:
            emp = None
        if text.lower().startswith("skills:"):
            skills = p
        if emp and _is_bullet(p):
            blocks[emp].append(p)
    name = doc.paragraphs[0].text.strip() if doc.paragraphs else "CV"
    return order, blocks, skills, name


# ---------- choosing bullets ----------
def _jd_words(desc):
    words = [w for w in re.findall(r"[a-z][a-z\-]+", desc.lower()) if w not in _STOP and len(w) > 3]
    counts = {}
    for w in words:
        counts[w] = counts.get(w, 0) + 1
    return {w for w, n in counts.items() if n >= 2}


WEAK_START = re.compile(r"^(supported|contributed|facilitated|prepared|assisted|helped|participated|acted as|"
                        r"established cross-functional)", re.I)
# The user's choice (27 October 2026): generated CVs say nothing about work authorization or visas.
WORK_AUTH = re.compile(r"^\s*(work authori[sz]ation|work permit|visa( status)?|sponsorship|immigration status|"
                       r"authori[sz]ed to work)\b", re.I)


def drop_work_authorization(doc):
    """Take the work authorization line (e.g. "Work Authorization: 3-year OPT...") out of the CV being made."""
    for p in list(doc.paragraphs):
        if WORK_AUTH.match(p.text):
            p._p.getparent().remove(p._p)


HAS_FIGURE = re.compile(r"\d+(\.\d+)?\s*(%|x\b|\+)|\$\s?\d|tripled|doubled|from (zero|0)|\b\d+ (markets|states|countries)\b", re.I)


def bullet_terms(text, weights):
    return {t for t in weights if cvmatch._RX[t].search(text)}


def bullet_score(text, weights, jd_words, covered=frozenset(), from_template=False):
    """Key terms of the job this bullet shows (terms already shown by chosen bullets count a quarter), words it shares
    with the job, plus a nudge for bullets with a result and against weak openings."""
    s = 0.0
    for term in bullet_terms(text, weights):
        s += weights[term] * (0.25 if term in covered else 1.0)
    words = {w for w in re.findall(r"[a-z][a-z\-]+", text.lower()) if len(w) > 3}
    s += 0.15 * len(words & jd_words)
    if HAS_FIGURE.search(text):
        s += 0.6
    if WEAK_START.search(text):
        s -= 0.8
    if from_template:
        s += 0.3  # small preference for bullets you chose for your Strategy CV
    return s


def _similar(a, b):
    wa, wb = cvlib._words(a), cvlib._words(b)
    if not wa or not wb:
        return False
    if len(wa & wb) / len(wa | wb) >= 0.25:
        return True
    caps = lambda t: {w for w in re.findall(r"\b[A-Z][a-z]{4,}\b", t[1:])}  # e.g. "Aerotropolis", "Verve"
    return bool(caps(a) & caps(b))


# ---------- the same result claimed twice ----------
FIGURE = re.compile(r"\d+(?:\.\d+)?\s*%|\b\d+(?:\.\d+)?x\b|\$\s?\d|\btripled\b|\bdoubled\b|\bhalved\b", re.I)
OUTCOME = re.compile(r"adoption|revenue|profit\w*|transaction volume|transactions|engagement|conversion|acquisition|"
                     r"lending|usage|issuance|sales performance|processing time|reporting (cycle )?time", re.I)


def results(text):
    """What a bullet claims as a measured result: its figures, and the outcomes named next to a figure."""
    out = cvlib._metrics(text)
    for m in FIGURE.finditer(text):
        window = text[max(0, m.start() - 60):m.end() + 60]
        out |= {o.group(0).lower().split()[0].rstrip("s") for o in OUTCOME.finditer(window)}
    return out


def same_result(a, b):
    """Both bullets claim the same result: the same figure, or a figure for the same outcome (adoption, revenue...)."""
    return bool(results(a) & results(b))


def _version_from(e, rw):
    return [{"text": rw["text"], "source": "rewrite", "id": rw["id"], "fit": rw["fit"]}]


def plan(desc, template_counts, template_chars, order, template_bullets=frozenset(), rewritten=None):
    """Decide the bullets for each employer. Returns {employer: [chosen dicts]}, employer fit scores, key-term weights.
    rewritten: {employer: [rewrites]} for the job's role type; employers not in it use the library."""
    lib = cvlib.library()
    weights, _req = cvmatch.weights_for(desc)  # requirements count more than nice-to-haves
    jd_words = _jd_words(desc)
    rewritten = rewritten or {}
    groups = {e: ([_version_from(e, r) for r in rewritten[e]] if rewritten.get(e) else lib.get(e, [])) for e in order}

    # meaning: how much of the job's asks a bullet newly covers, and the re-ranker's view of its fit with the job
    mc = meaning.for_cv(desc, sorted({v["text"] for e in order for g in groups[e] for v in g}))

    def vscore(v, covered):
        s = bullet_score(v["text"], weights, jd_words, covered, v["text"] in template_bullets)
        s += rewrites.FIT_BONUS.get(v.get("fit", ""), 0.0)  # Core first, then Strong, then Reserve
        if mc:
            s += MEANING_W * mc.gain(v["text"]) + RERANK_W * mc.fit(v["text"])
        return s

    def best_version(g, covered):
        return max(g, key=lambda v: (vscore(v, covered), -cvlib.SOURCE_ORDER.index(v["source"])
                                     if v["source"] in cvlib.SOURCE_ORDER else 0, -len(v["text"])))

    # how well each employer fits: the average of its two best bullets, plus what kind of job this is
    fit = {}
    for e in order:
        scores = sorted((vscore(best_version(g, frozenset()), frozenset()) for g in groups[e]), reverse=True)[:2]
        signal = len(_SIG[e].findall(desc)) if e in _SIG else 0
        fit[e] = (sum(scores) / max(len(scores), 1)) + 0.35 * min(signal, 6)
    # share out the bullets (12 on your Strategy CV): everyone gets their minimum, the rest go to the best fits
    total = sum(template_counts.values())
    alloc = {e: min(MIN_PER_EMPLOYER.get(e, 1), len(groups[e])) for e in order}
    caps = dict(MAX_PER_EMPLOYER)
    if "tts" in _SIG and len(_SIG["tts"].findall(desc)) < 2:
        caps["tts"] = 1  # Training The Street gets a second bullet only when the job asks for modelling, training or AI
    while sum(alloc.values()) < total:
        cands = [e for e in order if alloc[e] < min(caps.get(e, 3), len(groups[e]))]
        if not cands:
            break
        e = max(cands, key=lambda e: max(fit[e], 0.1) / (alloc[e] + 1))
        alloc[e] += 1
    chosen, covered = {e: [] for e in order}, set()
    left = {e: list(groups[e]) for e in order}

    def blocked(v, e):
        return any(_similar(v["text"], p["text"]) or same_result(v["text"], p["text"])
                   or rewrites.same_story(v.get("id"), p.get("id")) for p in chosen[e])

    def add(e, v, g, sc, req=False):
        chosen[e].append({"text": v["text"], "source": v["source"], "score": sc,
                          "id": v.get("id", ""), "fit": v.get("fit", ""), "req": req})
        if mc:
            mc.take(v["text"])
        covered.update(bullet_terms(v["text"], weights))
        left[e].remove(g)

    # requirements first: for each requirement the job states, in order, put your closest bullet on the CV if it's
    # a close match and its employer still has room (and it doesn't repeat a story or result already chosen)
    if mc:
        for j in mc.req:
            if mc.covered(j, [p["text"] for ps in chosen.values() for p in ps]):
                continue
            best = None
            for e in order:
                if len(chosen[e]) >= alloc[e]:
                    continue
                for g in left[e]:
                    v = max(g, key=lambda v: mc.sim(v["text"], j))
                    s = mc.sim(v["text"], j)
                    if s >= meaning.CLOSE and (best is None or s > best[0]) and not blocked(v, e):
                        best = (s, e, v, g)
            if best:
                _, e, v, g = best
                add(e, v, g, vscore(v, covered), req=True)
    # then the remaining places, best-fitting employers first, so each new bullet adds what isn't shown yet
    for e in sorted(order, key=lambda e: -fit[e]):
        while len(chosen[e]) < alloc[e] and left[e]:
            options = [(vscore(v, covered), v, g) for g in left[e] for v in [best_version(g, covered)]
                       if not blocked(v, e)]
            if not options:
                break
            sc, v, g = max(options, key=lambda o: o[0])
            add(e, v, g, sc)
    for e in order:
        chosen[e].sort(key=lambda c: -c["score"])  # within each employer, best fit first

    def chars():
        return sum(len(p["text"]) for ps in chosen.values() for p in ps)
    # keep the length close to your Strategy CV: drop the weakest extra bullet until it fits
    while chars() > template_chars * LENGTH_SLACK:
        cands = [(p.get("req", False), p["score"], e, i) for e, ps in chosen.items() for i, p in enumerate(ps)
                 if len(ps) > MIN_PER_EMPLOYER.get(e, 1)]  # bullets that answer a requirement go last
        if not cands:
            break
        _, _, e, i = min(cands)
        chosen[e].pop(i)
    return chosen, fit, weights, mc


# ---------- skills line ----------
def _skill_key(s):
    return re.sub(r"[^a-z]", "", s.lower())


def pick_skills(template_skills, desc, weights):
    pool = cvlib.skills_pool()
    budget = len(", ".join(template_skills)) * 1.1
    jd = desc.lower()

    def relevance(s):
        r = sum(weights[t] for t in bullet_terms(s, weights))  # the job's key terms this skill shows
        core = re.sub(r"\(.*?\)|&.*$| and .*$", "", s.lower()).strip()
        if len(core) > 3 and core in jd:
            r += 1.5  # the job names this skill
        if s in template_skills:
            r += 0.3  # small preference for what's on your Strategy CV now
        return r

    ranked = sorted(pool, key=lambda s: -relevance(s))
    out, used = [], []
    for s in ranked:
        k = _skill_key(s)
        if any(k in u or u in k for u in used):  # "Go-To-Market" vs "Go-To-Market Strategy"
            continue
        if len(", ".join(out + [s])) > budget:
            continue
        out.append(s)
        used.append(k)
    return out


# ---------- writing the file ----------
def _set_text(p, text):
    runs = p.runs
    if not runs:
        p.add_run(text)
        return
    runs[0].text = text
    for r in runs[1:]:
        r._r.getparent().remove(r._r)


def _safe(s, n=70):
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", s)
    s = re.sub(r"\s+", " ", s).strip(" .")
    if len(s) > n:  # cut at a word, not in the middle of one
        s = s[:n].rsplit(" ", 1)[0]
    return s.strip(" .,&-") or "Job"


def short_name(full):
    parts = full.split()
    return f"{parts[0]} {parts[-1]}" if len(parts) >= 2 else full


def _covered_pct(text, weights):
    if not weights:
        return 0
    total = sum(weights.values())
    return round(100 * sum(w for t, w in weights.items() if cvmatch._RX[t].search(text)) / total)


def build(job, desc, cvs):
    """Make the tailored CV for one job. Returns a dict describing what was done."""
    import docx
    tpath = template_path()
    doc = docx.Document(tpath)
    drop_work_authorization(doc)
    order, blocks, skills_p, full_name = template_layout(doc)
    template_counts = {e: len(blocks[e]) for e in order}
    template_text = {e: [p.text.strip() for p in blocks[e]] for e in order}
    template_chars = sum(len(t) for ts in template_text.values() for t in ts)
    template_bullets = frozenset(t for ts in template_text.values() for t in ts)
    role_type, rewritten = rewrites.for_job(job.get("title", ""), job.get("label", ""))
    chosen, fit, weights, mc = plan(desc, template_counts, template_chars, order, template_bullets, rewritten)
    meaning_used = bool(mc)
    # which of the job's stated requirements this CV speaks to, and with which bullet
    checklist = mc.checklist([(c.get("id") or "", c["text"]) for e in order for c in chosen.get(e, [])]) if mc else []

    # bullets: reuse each employer's own bullet paragraphs so fonts, spacing and numbering stay the same
    for emp in order:
        paras = blocks[emp]
        want = [c["text"] for c in chosen.get(emp, [])]
        while len(paras) < len(want):
            new = copy.deepcopy(paras[-1]._p)
            paras[-1]._p.addnext(new)
            from docx.text.paragraph import Paragraph
            paras.append(Paragraph(new, paras[-1]._parent))
        while len(paras) > len(want):
            gone = paras.pop()
            gone._p.getparent().remove(gone._p)
        for p, t in zip(paras, want):
            _set_text(p, t if t.endswith((".", "!", "?")) else t + ".")  # punctuation only, for consistency

    # skills line: keep the bold "Skills: " label, replace the list
    template_skills, new_skills = [], []
    if skills_p is not None:
        raw = skills_p.text.split(":", 1)[1] if ":" in skills_p.text else ""
        template_skills = [s.strip(" .") for s in re.split(r",(?![^()]*\))", raw) if s.strip(" .")]
        new_skills = pick_skills(template_skills, desc, weights)
        runs = skills_p.runs
        if len(runs) >= 2:
            runs[1].text = ", ".join(new_skills)
            for r in runs[2:]:
                r._r.getparent().remove(r._r)

    # where it goes
    company, role = job.get("company", "Company"), job.get("title", "Role")
    folder = os.path.join(OUT_DIR, _safe(f"{cvlib_short(company)} - {role}"))
    os.makedirs(folder, exist_ok=True)
    base = f"{short_name(full_name)} - CV - {_safe(cvlib_short(company), 40)}"
    path, v = os.path.join(folder, base + ".docx"), 1
    while os.path.exists(path):
        v += 1
        path = os.path.join(folder, f"{base} (v{v}).docx")
    doc.save(path)

    readable = readability(path, order, chosen, full_name, new_skills)

    # before and after, each measured on the whole CV
    tailored_text = "\n".join(p.text for p in docx.Document(path).paragraphs)
    role_kind = cvmatch.cv_for(job.get("label", ""))
    before_text = cvs.get(role_kind) or cvs.get("strategy") or ""
    strategy_text = cvs.get("strategy") or "\n".join(p.text for p in docx.Document(tpath).paragraphs)
    new_chars = sum(len(c["text"]) for cs in chosen.values() for c in cs)
    kept = {t for ts in template_text.values() for t in ts}
    info = {
        "uid": job.get("uid"), "company": company, "role": role, "url": job.get("url", ""), "version": v,
        "path": path, "folder": folder, "made": dt.datetime.now().isoformat(timespec="seconds"),
        "before_cv": {"pm": "PM CV", "pmm": "PMM CV", "strategy": "Strategy CV"}.get(role_kind, "CV"),
        "before_pct": _covered_pct(before_text, weights), "strategy_pct": _covered_pct(strategy_text, weights),
        "after_pct": _covered_pct(tailored_text, weights), "long_pct": _covered_pct(cvs.get("long", "") + "\n" + before_text, weights),
        "length_pct": round(100 * new_chars / template_chars) if template_chars else 100,
        "role_type": role_type, "rewrites_used": bool(rewritten), "meaning_used": meaning_used,
        "requirements": checklist,
        "bullets": {cvlib.EMP_NAME[e]: [{"text": c["text"], "source": c["source"], "id": c.get("id", ""),
                                        "fit": c.get("fit", ""),
                                        "new": c["source"] != "rewrite" and c["text"] not in kept}
                                       for c in chosen.get(e, [])] for e in order},
        # with rewrites every Strategy CV line is replaced, so listing them all as "taken out" says nothing
        "dropped": [] if rewritten else [t for t in kept if t not in {c["text"] for cs in chosen.values() for c in cs}],
        "fit": {cvlib.EMP_NAME[e]: round(fit[e], 1) for e in order},
        "skills_before": template_skills, "skills_after": new_skills, "readability": readable,
    }
    _write_notes(folder, path, info, job, desc)
    _remember(info)
    return info


def cvlib_short(company):
    """Company name without legal endings, for folder and file names."""
    s = re.sub(r"[,\s]+(inc|incorporated|llc|corp|corporation|co|ltd|lp|l\.p|llp|plc)\.?$", "", company.strip(), flags=re.I)
    return s.strip(" ,.") or company


SRC = {"strategy": "Strategy CV", "long": "long CV", "pm": "PM CV", "pmm": "PMM CV", "rewrite": "your rewrite"}


def readability(path, order, chosen, full_name, skills):
    """Read the saved file back in plain reading order, the way a simple CV parser does, and check that the name,
    the section headings, every employer with its dates, every bullet under the right employer and the skills come
    out where they should. Returns a list of problems (empty if it reads cleanly)."""
    import docx
    paras = docx.Document(path).paragraphs
    lines = [(p.text.strip(), p) for p in paras if p.text.strip()]
    texts = [t for t, _ in lines]
    problems = []
    if not texts or texts[0] != full_name:
        problems.append("The name isn't the first line.")
    for head in ("Education", "Experience", "Additional Information"):
        if head not in texts:
            problems.append(f"The '{head}' heading is missing.")
    # employers in date order, each with dates on its line
    pos = {}
    for i, t in enumerate(texts):
        k = cvlib.employer_of(t)
        if k and k not in pos:
            pos[k] = i
            if not re.search(r"(19|20)\d\d", t):
                problems.append(f"{cvlib.EMP_NAME[k]} has no dates on its line.")
    seen = [k for k in order if k in pos]
    if seen != order:
        problems.append("Not every employer was found: " + ", ".join(cvlib.EMP_NAME[k] for k in order if k not in pos) + ".")
    if [pos[k] for k in seen] != sorted(pos[k] for k in seen):
        problems.append("Employers are out of order.")
    # every chosen bullet under its own employer, in the chosen order
    bounds = sorted(pos.values()) + [len(texts)]
    for k in seen:
        start = pos[k]
        end = min(b_ for b_ in bounds if b_ > start)
        block = texts[start + 1:end]
        idx = []
        for c in chosen.get(k, []):
            want = c["text"].rstrip(".!?")
            hit = next((i for i, t in enumerate(block) if t.rstrip(".!?") == want), None)
            if hit is None:
                problems.append(f"A {cvlib.EMP_NAME[k]} bullet didn't come out under {cvlib.EMP_NAME[k]}.")
            else:
                idx.append(hit)
        if idx != sorted(idx):
            problems.append(f"{cvlib.EMP_NAME[k]} bullets are out of order.")
    # bullets are real list items, none empty
    for p in paras:
        if _is_bullet(p) and not p.text.strip():
            problems.append("There's an empty bullet.")
            break
    skills_line = next((t for t in texts if t.lower().startswith("skills:")), "")
    missing = [s for s in skills if s not in skills_line]
    if missing:
        problems.append("Some skills didn't come out on the skills line.")
    return problems


def _write_notes(folder, path, info, job, desc):
    name = os.path.splitext(os.path.basename(path))[0]
    lines = [f"{info['role']} at {info['company']}", f"Made {info['made'].replace('T', ' at ')} as {os.path.basename(path)}",
             f"Posting: {info['url']}", "",
             f"Skills this job asks for, covered by: your {info['before_cv']} {info['before_pct']}%, "
             + (f"your Strategy CV {info['strategy_pct']}%, " if info['before_cv'] != "Strategy CV" else "")
             + f"this tailored CV {info['after_pct']}%. "
             f"All your CVs together: {info['long_pct']}%.",
             f"Bullet length: {info['length_pct']}% of your Strategy CV's.",
             f"Role type: {info['role_type']}. " + ("Bullets from your Bullet rewrites for this role type."
                                                    if info["rewrites_used"] else
                                                    "No section for it in Bullet rewrites.docx, so bullets use the wording from your CVs."),
             "Chosen with: keywords" + (", meaning matching and the re-ranker." if info.get("meaning_used") else
                                        " only (meaning matching wasn't ready)."),
             "Readability check: " + ("reads cleanly (name, headings, employers with dates, every bullet in place, skills)."
                                      if not info["readability"] else "PROBLEMS: " + " ".join(info["readability"])),
             "", "Bullets used, by employer (date order kept):"]
    for emp, bs in info["bullets"].items():
        lines.append(f"  {emp}")
        for b in bs:
            where = f"{b['id']}, {(b['fit'] or 'no fit').capitalize()}" if b.get("id") else SRC.get(b["source"], b["source"])
            lines.append(f"    {'NEW ' if b['new'] else '    '}{b['text']}  [{where}]")
    if info.get("requirements"):
        lines += ["", "Requirements the job states, and the bullet on this CV that speaks to each:"]
        for r in info["requirements"]:
            who = r["label"] or (r["text"][:60] + "...")
            lines.append(f"    {'YES' if r['covered'] else 'NO '} {r['req']}" + (f"  [{who}]" if r["covered"] else
                                                                            "  [no close match on this CV]"))
    if info["dropped"]:
        lines += ["", "Taken out from your Strategy CV:"] + [f"    {t}" for t in info["dropped"]]
    lines += ["", "Skills before: " + ", ".join(info["skills_before"]), "Skills after:  " + ", ".join(info["skills_after"]),
              "", "Every bullet is your own wording, from Bullet rewrites.docx or your CVs. "
                  "Open the Word file and check it fits on one page."]
    suffix = "" if info["version"] == 1 else f" (v{info['version']})"
    with open(os.path.join(folder, f"about this CV{suffix}.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    jd_path = os.path.join(folder, "job description.txt")
    if not os.path.exists(jd_path):
        with open(jd_path, "w", encoding="utf-8") as f:
            f.write(f"{info['role']} at {info['company']}\n{info['url']}\nSaved {info['made'][:10]}\n\n{desc}")


def _remember(info):
    os.makedirs(os.path.dirname(INFO_FILE), exist_ok=True)
    try:
        with open(INFO_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    data.setdefault(info["uid"], []).append(info)
    with open(INFO_FILE + ".tmp", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(INFO_FILE + ".tmp", INFO_FILE)


def made_for():
    """{uid: [versions]} of CVs made so far."""
    try:
        with open(INFO_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
