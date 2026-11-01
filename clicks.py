"""Roles you opened from the tracker, waiting for you to say whether you applied.

Kept in data/clicks.json, never in tracker.xlsx: the workbook changes only when you press "Yes, applied".
Each entry: company, role, url, where it was opened from, when, and its state:
  waiting  opened, not asked yet (the "Did you apply?" bar shows these)
  not_yet  you said "Not yet"; stays on the Applications page list, the bar doesn't ask again
Entries go when you answer Yes or Not for me, after KEEP_DAYS, or when the watcher sees the posting has closed.
"""
import os
import json
import threading
import datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
FILE = os.path.join(HERE, "data", "clicks.json")
KEEP_DAYS = 14
_lock = threading.Lock()


def key_for(url):
    return (url or "").strip().rstrip("/").lower()


def _load():
    try:
        with open(FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(data):
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    tmp = FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    os.replace(tmp, FILE)


def _fresh(data, closed=()):
    cut = (dt.datetime.now() - dt.timedelta(days=KEEP_DAYS)).isoformat(timespec="seconds")
    return {k: v for k, v in data.items() if v.get("at", "") >= cut and not (v.get("uid") and v["uid"] in closed)}


def record(company, role, url, source, uid="", row=None):
    """Note that a posting was opened. Opening it again puts it back to waiting, so you're asked again."""
    k = key_for(url)
    if not k:
        return
    with _lock:
        data = _fresh(_load())
        data[k] = {"company": (company or "").strip(), "role": " ".join((role or "").split()), "url": url, "source": source, "uid": uid, "row": row,
                   "at": dt.datetime.now().isoformat(timespec="seconds"), "state": "waiting"}
        _save(data)


def pending(closed=()):
    """Every open question, newest first. closed: watcher role ids whose postings have closed."""
    with _lock:
        raw = _load()
        data = _fresh(raw, closed)
        if len(data) != len(raw):
            _save(data)
    out = [dict(v, key=k) for k, v in data.items()]
    return sorted(out, key=lambda x: x["at"], reverse=True)


def get(k):
    return _load().get(k)


def set_state(k, state):
    with _lock:
        data = _load()
        if k in data:
            data[k]["state"] = state
            _save(data)


def remove(k):
    with _lock:
        data = _load()
        if data.pop(k, None) is not None:
            _save(data)


def ago(at):
    """'just now', '25 minutes ago', '3 hours ago', 'yesterday', '4 days ago'."""
    try:
        secs = (dt.datetime.now() - dt.datetime.fromisoformat(at)).total_seconds()
    except (TypeError, ValueError):
        return ""
    if secs < 90:
        return "just now"
    if secs < 3600:
        return f"{int(secs // 60)} minutes ago"
    if secs < 86400:
        h = int(secs // 3600)
        return f"{h} hour{'s' if h != 1 else ''} ago"
    d = int(secs // 86400)
    return "yesterday" if d == 1 else f"{d} days ago"
