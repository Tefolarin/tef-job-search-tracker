"""Matching by meaning, on this laptop. Free, no AI service, nothing about you leaves the computer.

Two small models (downloaded once, about 1.5 GB in all, kept in %LOCALAPPDATA%\\TEF so OneDrive doesn't sync them):
- bge-base turns each sentence into a "meaning fingerprint", so "drive alignment across teams" and "aligned bank
  partners across 5 markets" count as close even though the words differ. Used for every role's match level.
- bge-reranker reads one job and one of your bullets side by side and judges the fit. Slower, so it runs only when
  you press Generate CV, to help choose your 12 bullets.

The first run reads every saved job description once (in the background; the site works as normal and uses keyword
scores until it's done). Results are saved, so later starts only read new roles. If the package or models aren't
there, everything falls back to keyword matching exactly as before.
"""
import os
import re
import time
import pickle
import hashlib
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
EMBED_MODEL = "BAAI/bge-base-en-v1.5"
RERANK_MODEL = "BAAI/bge-reranker-base"
LO, HI = 0.66, 0.80     # below LO a requirement counts as not covered, from HI fully covered (calibrated on 1,639 real job sentences)
BLEND = 0.5             # share of the match level that comes from meaning; the rest stays keyword matching
MAX_SENTENCES = 60      # per job description, requirements first
CHUNK = 5               # jobs read per turn, so a CV request never waits long for the model


def _home():
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".cache")
    path = os.path.join(base, "TEF")
    os.makedirs(path, exist_ok=True)
    return path


MODELS_DIR = os.path.join(_home(), "models")
JOBS_FILE = os.path.join(_home(), "meaning_jobs.pkl")
TEXT_FILE = os.path.join(_home(), "meaning_text.pkl")

status = {"state": "off", "done": 0, "total": 0, "note": ""}   # off, loading, working, ready, unavailable
_model_lock = threading.Lock()
_data_lock = threading.Lock()
_load_lock = threading.Lock()
_models = {}
_jobs = {}        # uid: (hash of description, [sentences], weights array, vectors array)
_texts = {}       # hash of a sentence: vector (your bullets and anything else embedded on demand)
_evidence = {}    # "all", "pm", "pmm", "strategy", "long": vectors of your bullets for that CV
_evidence_key = None
_thread = None
version = 0       # goes up whenever saved results or your bullets change, so the site knows to refresh its lists
_scores = {}      # uid: (description hash, evidence version, result), so a role is scored once, not on every click
_ev_version = 0
THREADS = max(1, (os.cpu_count() or 2) // 2)  # half the processor, so the site stays quick while this works


def available():
    try:
        import numpy  # noqa: F401
        import fastembed  # noqa: F401
        return True
    except Exception:
        return False


def ready():
    return status["state"] == "ready" or (status["state"] == "working" and bool(_evidence))


# ---------- models ----------
def _embedder():
    with _load_lock:
        if "embed" not in _models:
            from fastembed import TextEmbedding
            _models["embed"] = TextEmbedding(EMBED_MODEL, cache_dir=MODELS_DIR, threads=THREADS)
    return _models["embed"]


def _reranker():
    with _load_lock:
        if "rerank" not in _models:
            from fastembed.rerank.cross_encoder import TextCrossEncoder
            _models["rerank"] = TextCrossEncoder(RERANK_MODEL, cache_dir=MODELS_DIR, threads=THREADS)
    return _models["rerank"]


def _h(text):
    return hashlib.sha1(text.encode("utf-8", "ignore")).hexdigest()[:16]


def embed(texts):
    """Unit-length vectors for these sentences (one row each). Your bullets are remembered between runs."""
    import numpy as np
    keys = [_h(t) for t in texts]
    missing = [(k, t) for k, t in zip(keys, texts) if k not in _texts]
    if missing:
        uniq = dict(missing)
        with _model_lock:
            vecs = list(_embedder().embed(list(uniq.values()), batch_size=32))
        for k, v in zip(uniq, vecs):
            v = np.asarray(v, dtype=np.float32)
            _texts[k] = (v / (np.linalg.norm(v) or 1.0)).astype(np.float16)
    if not texts:
        return np.zeros((0, 768), dtype=np.float32)
    return np.stack([_texts[k] for k in keys]).astype(np.float32)


def rerank(query, docs):
    """How well each doc answers the query (the re-ranker's raw score; higher is better)."""
    if not docs:
        return []
    with _model_lock:
        raw = list(_reranker().rerank(query, docs, batch_size=16))
    return [float(x) for x in raw]


# ---------- job descriptions into sentences ----------
_SPLIT = re.compile(r"(?<=[.!?;])\s+|\n+|\s+[•·▪◦]\s+|\s{2,}")


def job_sentences(desc):
    """[(weight, sentence)]: what the job asks for and does. Requirements count 1.6, nice-to-haves 0.7, the rest 1.
    Company blurbs, benefits, pay and legal text are left out first."""
    import jdtext
    req, pref = jdtext.split(desc or "")
    text = jdtext.clean(desc or "")
    req_n, pref_n = " ".join(req.split()).lower(), " ".join(pref.split()).lower()
    out, seen = [], set()
    for s in _SPLIT.split(text):
        s = s.strip(" -*•·:\t")
        words = s.split()
        if len(words) < 5 or len(words) > 70:
            continue
        key = " ".join(words).lower()
        if key in seen:
            continue
        seen.add(key)
        w = 1.6 if key[:60] in req_n else 0.7 if key[:60] in pref_n else 1.0
        out.append((w, " ".join(words)))
    out.sort(key=lambda x: -x[0])  # requirements first, original order kept within each group (sort is stable)
    return out[:MAX_SENTENCES]


# ---------- saving ----------
def _load():
    for path, target in ((JOBS_FILE, _jobs), (TEXT_FILE, _texts)):
        try:
            with open(path, "rb") as f:
                target.update(pickle.load(f))
        except Exception:
            pass


def _save():
    global version
    version += 1
    with _data_lock:
        for path, data in ((JOBS_FILE, dict(_jobs)), (TEXT_FILE, dict(_texts))):
            tmp = path + ".tmp"
            with open(tmp, "wb") as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            os.replace(tmp, path)


# ---------- your side ----------
def _your_bullets():
    """{"all": [...], "pm": [...], ...}: every bullet on your CVs and in Bullet rewrites.docx, and per CV."""
    import cvlib
    import rewrites
    per = {"all": set()}
    for groups in cvlib.library().values():
        for g in groups:
            for v in g:
                per["all"].add(v["text"])
                for src in [v["source"]] + v.get("also_in", []):
                    per.setdefault(src, set()).add(v["text"])
    for es in rewrites.load().values():
        for rows in es.values():
            for r in rows:
                per["all"].add(r["text"])
    per["long"] = per["all"]
    return {k: sorted(v) for k, v in per.items()}


def _refresh_evidence():
    global _evidence_key
    import cvlib
    import rewrites
    files = [os.path.join(cvlib.CV_DIR, n) for n in sorted(os.listdir(cvlib.CV_DIR))] + [rewrites.path()]
    key = tuple((p, os.path.getmtime(p)) for p in files if os.path.exists(p))
    if key == _evidence_key and _evidence:
        return
    global _ev_version, version
    bullets = _your_bullets()
    _evidence.update({k: embed(v) for k, v in bullets.items() if v})
    _evidence_key = key
    _ev_version += 1
    version += 1


# ---------- scoring ----------
def _soft(sims):
    import numpy as np
    return np.clip((sims - LO) / (HI - LO), 0.0, 1.0)


# How a role's average closeness maps onto the keyword scale. Calibrated on 30 real roles (31 October 2026): the
# 10th and 90th percentile of average closeness (0.562, 0.626) line up with the 10th and 90th percentile of keyword
# coverage across all your CVs (78%, 100%). Meaning then moves a role up or down only where it disagrees with keywords.
ALIGN = (0.562, 0.626, 0.78, 1.00)


def job_score(uid, kind=None):
    """{"score": 0-1 on the keyword scale, "raw": average closeness}: how well everything you've done fits what the
    job asks for, by meaning. None until this role has been read."""
    item = _jobs.get(uid)
    ev = _evidence.get("all")
    if not item or ev is None:
        return None
    hit = _scores.get(uid)
    if hit and hit[0] == item[0] and hit[1] == _ev_version:
        return hit[2]
    _, _sents, w, vecs = item
    if not len(w):
        return None
    best = (vecs.astype("float32") @ ev.T).max(axis=1)
    raw = float((best * w).sum() / w.sum())
    r0, r1, k0, k1 = ALIGN
    score = min(1.0, max(0.0, k0 + (raw - r0) * (k1 - k0) / (r1 - r0)))
    out = {"score": score, "raw": raw}
    _scores[uid] = (item[0], _ev_version, out)
    return out


# Not skills: degrees, licences, office days, travel, pay. Bullets can't speak to these, so they're never "least covered".
NOT_SKILL = re.compile(r"\b(degree|bachelor|master'?s|mba|graduat\w*|education|studies|gpa|licen[cs]e|series \d+|"
                       r"office|on.?site|hybrid|remote|relocat\w*|travel|days per week|hours|salary|pay|visa|"
                       r"sponsor\w*|authori[sz]\w*|citizen\w*|set you apart|currently (has|have|enrolled)|final year|"
                       r"\d+\+? years|benefits)\b", re.I)

ASKS = re.compile(r"\b(experience (in|with|of|leading|building|working|driving|managing|owning|defining)|skills?|ability|"
                  r"proficien\w*|knowledge|track record|background in|familiar\w*|understanding of|demonstrated|"
                  r"expertise|comfort\w* with|fluency)\b", re.I)


CLOSE = 0.62  # a bullet at least this close to a stated requirement counts as speaking to it (calibrated on 45 real requirements: median best 0.63; pairs above 0.62 read as genuine matches)


def is_requirement(w, s):
    """A stated requirement that's about skills or experience (not degrees, years, office days, pay)."""
    return w >= 1.6 and len(s.split()) >= 7 and not NOT_SKILL.search(s) and bool(ASKS.search(s))


def least_covered(uid, cands=None, n=3):
    """The skills the job lists as requirements that your bullets speak to least, each with your closest bullet.
    cands: [(label, text)] to compare with, e.g. the rewrites for this role type with their IDs; default all bullets.
    Returns [{"req", "label", "text", "sim", "close"}]. Descriptions without a requirements section give []."""
    item = _jobs.get(uid)
    if not item or "all" not in _evidence:
        return []
    _, sents, w, vecs = item
    cands = [c for c in (cands or []) if _h(c[1]) in _texts]  # only bullets already read, so a page never waits
    if cands:
        labels, texts = [c[0] for c in cands], [c[1] for c in cands]
        ev = embed(texts)
    else:
        labels, texts, ev = None, None, _evidence["all"]
    sims = vecs.astype("float32") @ ev.T
    best, arg = sims.max(axis=1), sims.argmax(axis=1)
    keep = [i for i in range(len(sents)) if is_requirement(w[i], sents[i]) and best[i] < HI]
    keep.sort(key=lambda i: best[i])
    return [{"req": sents[i], "label": labels[arg[i]] if labels else "", "text": texts[arg[i]] if texts else "",
             "sim": float(best[i]), "close": bool(best[i] >= CLOSE)} for i in keep[:n]]


class ForCV:
    """Meaning scores for one job's description against candidate bullets, for the CV generator."""

    def __init__(self, desc, texts, use_reranker=True):
        import numpy as np
        js = job_sentences(desc)
        self.ok = bool(js and texts)
        if not self.ok:
            return
        self.w = np.array([w for w, _ in js], dtype=np.float32)
        self.sents = [s for _, s in js]
        self.req = [i for i, (w, s) in enumerate(js) if is_requirement(w, s)]  # stated requirements, in order
        jv = embed(self.sents)
        self.index = {t: i for i, t in enumerate(texts)}
        self.raw = embed(texts) @ jv.T                  # bullets x job sentences, closeness
        self.soft = _soft(self.raw)                     # the same, 0 to 1
        self.cur = np.zeros(len(js), dtype=np.float32)  # how well the chosen bullets cover each sentence so far
        self.rr = {}
        if use_reranker:
            top = [s for w, s in js if w >= 1.6][:8] or [s for _, s in js][:8]
            query = " ".join(top)[:1200]
            raw = rerank(query, list(texts))
            # the re-ranker's raw scores for CV bullets sit close together, so use each bullet's rank among the
            # candidates instead: the best fit gets 1, the weakest 0
            order = sorted(range(len(raw)), key=lambda i: raw[i])
            n = max(len(raw) - 1, 1)
            self.rr = {texts[i]: r / n for r, i in enumerate(order)}

    def gain(self, text):
        """Share of the job's asks this bullet would newly cover, given the bullets already chosen."""
        import numpy as np
        i = self.index.get(text)
        if i is None:
            return 0.0
        return float(((np.maximum(self.cur, self.soft[i]) - self.cur) * self.w).sum() / self.w.sum())

    def take(self, text):
        import numpy as np
        i = self.index.get(text)
        if i is not None:
            self.cur = np.maximum(self.cur, self.soft[i])

    def fit(self, text):
        return self.rr.get(text, 0.0)

    def sim(self, text, j):
        i = self.index.get(text)
        return float(self.raw[i, j]) if i is not None else 0.0

    def covered(self, j, texts):
        return any(self.sim(t, j) >= CLOSE for t in texts)

    def checklist(self, chosen):
        """For each stated requirement: the chosen bullet closest to it and whether it's close enough.
        chosen: [(label, text)]."""
        out = []
        for j in self.req:
            lab, txt, s = max(((lab, t, self.sim(t, j)) for lab, t in chosen), key=lambda x: x[2],
                              default=("", "", 0.0))
            out.append({"req": self.sents[j], "label": lab, "text": txt, "covered": s >= CLOSE})
        return out


def for_cv(desc, texts):
    """ForCV, or None when meaning matching isn't available yet."""
    if not available() or status["state"] not in ("ready", "working"):
        return None  # still loading, or not installed: the CV is chosen on keywords as before
    try:
        f = ForCV(desc, texts)
        return f if f.ok else None
    except Exception:
        return None


# ---------- the background reader ----------
def _run(get_descriptions):
    import numpy as np
    status.update(state="loading", note="Loading the meaning model (the first time, it downloads about 1.5 GB).")
    try:
        _load()
        _embedder()
        _refresh_evidence()
    except Exception as e:
        status.update(state="unavailable", note=f"Meaning matching is off ({type(e).__name__}: {str(e)[:120]}). "
                                                "Matching uses keywords only.")
        return
    try:
        _reranker()  # download now, so the first Generate CV isn't the one that waits
    except Exception:
        pass
    while True:
        try:
            _refresh_evidence()
            descs = get_descriptions() or {}
            todo = [u for u, d in descs.items() if d and len(d) > 200 and (_jobs.get(u) or ("",))[0] != _h(d)]
            if todo:
                status.update(state="working", done=0, total=len(todo), note="")
                for start in range(0, len(todo), CHUNK):
                    for uid in todo[start:start + CHUNK]:
                        js = job_sentences(descs[uid])
                        vecs = embed([s for _, s in js]) if js else np.zeros((0, 768), dtype=np.float32)
                        for _, s in js:  # job sentences live with their job, not in the bullet store
                            _texts.pop(_h(s), None)
                        _jobs[uid] = (_h(descs[uid]), [s for _, s in js],
                                      np.array([w for w, _ in js], dtype=np.float32), vecs.astype(np.float16))
                    status["done"] = min(start + CHUNK, len(todo))
                    if (start // CHUNK) % 20 == 19:
                        _save()
                    time.sleep(0.05)
                _save()
            status.update(state="ready", done=0, total=0, note="")
        except Exception as e:
            status.update(state="ready" if _jobs else "unavailable", note=f"Last update failed ({type(e).__name__}).")
        time.sleep(60)  # new roles from Check now or Paste a job are picked up within a minute


def start(get_descriptions):
    """Start the background reader once. get_descriptions: returns {role id: description}."""
    global _thread
    if _thread or not available():
        if not available():
            status.update(state="unavailable", note="Meaning matching isn't installed. Matching uses keywords only.")
        return
    _thread = threading.Thread(target=_run, args=(get_descriptions,), daemon=True, name="meaning")
    _thread.start()
