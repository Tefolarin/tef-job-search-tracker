"""PM job search tracker. Reads tracker.xlsx fresh on every page load and stores nothing."""
import os
import sys
import json
import shutil
import secrets
import datetime as dt
import threading
import webbrowser
import re
from urllib.parse import quote, quote_plus, urlencode

import openpyxl
from flask import Flask, render_template, abort, request, redirect, jsonify
from jinja2 import DictLoader

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "tracker.xlsx")
PORT = 5000

app = Flask(__name__)
sys.modules.setdefault("app", sys.modules[__name__])  # so digest.py reuses this copy when the site imports it

DEFAULTS = {
    "request_nudge_days": 7, "accepted_message_days": 2, "message_followup_days": 5,
    "second_silence_days": 5, "thankyou_due_days": 1, "checkback_days": 14,
    "deadline_warning_days": 7, "data_through": "2026-06-30",
    "school_name": "", "school_linkedin_url": "",
    "email_from": "", "email_to": "", "digest_time": "07:30",
    "jobs_max_age_days": 30,
}
TEXT_SETTINGS = {"data_through", "school_name", "school_linkedin_url", "email_from", "email_to", "digest_time"}
SETTING_LABELS = {
    "request_nudge_days": "Days before an unanswered connection request needs a nudge",
    "accepted_message_days": "Days after a request is accepted before you should have sent a message",
    "message_followup_days": "Days after a first message with no reply before a polite follow-up",
    "second_silence_days": "Days after a follow-up with no reply before marking the person dead",
    "thankyou_due_days": "Days after a chat before the thank-you counts as overdue",
    "checkback_days": "Days after a thank-you before you check back",
    "deadline_warning_days": "Flag an application when the deadline is within this many days",
    "data_through": "Filing data runs up to (shown on company pages)",
    "school_name": "Your school, as it is written on LinkedIn",
    "school_linkedin_url": "Your school's LinkedIn page address",
    "email_from": "Gmail address that sends the daily email",
    "email_to": "Send the daily email to (blank means the same Gmail address)",
    "digest_time": "Time to send the daily email (24-hour, e.g. 07:30)",
    "jobs_max_age_days": "Jobs page: only show roles posted within this many days",
}
SPOKEN = {"replied", "chat booked", "chat done", "thank-you sent"}
STATUSES = ["interested", "applied", "screening", "interviewing", "offer", "rejected", "withdrawn"]
STATUS_ALIASES = {"": "interested", "not applied": "interested", "interview": "interviewing"}
OPEN_APP = {"interested", "applied", "screening", "interviewing", "offer"}
RESPONDED = {"screening", "interviewing", "offer", "rejected"}
STAGES = ["found", "request sent", "accepted", "message sent", "replied", "chat booked", "chat done",
          "thank-you sent", "follow-up sent", "dead"]


# ---------- reading the workbook ----------
def s(v):
    return "" if v is None else str(v).strip()


def d(v):
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    t = s(v)
    for f in ("%Y-%m-%d", "%d/%m/%Y", "%d %b %Y", "%d %B %Y"):
        try:
            return dt.datetime.strptime(t, f).date()
        except ValueError:
            pass
    return None


def n_days(n):
    return f"{n} day" if n == 1 else f"{n} days"


def fmt(v):
    if isinstance(v, str):  # an ISO date such as 2026-10-18
        try:
            v = dt.date.fromisoformat(v[:10])
        except ValueError:
            return v
    return v.strftime("%d %b %Y").lstrip("0") if v else ""


def read_sheet(wb, name):
    if name not in wb.sheetnames:
        return []
    rows = wb[name].iter_rows(values_only=True)
    head = [s(h) for h in next(rows, [])]
    out = []
    for i, r in enumerate(rows, start=2):
        if all(c is None or s(c) == "" for c in r):
            continue
        rec = {h: v for h, v in zip(head, r) if h}
        rec["_row"] = i
        out.append(rec)
    return out


def load():
    wb = openpyxl.load_workbook(PATH, data_only=True)
    try:
        settings = dict(DEFAULTS)
        for r in read_sheet(wb, "Settings"):
            k, v = s(r.get("Key (do not edit)")), r.get("Value")
            if k in DEFAULTS and v is not None:
                if k == "data_through":
                    settings[k] = s(v)[:10] if not isinstance(v, (dt.date, dt.datetime)) else v.strftime("%Y-%m-%d")
                elif k in TEXT_SETTINGS:
                    settings[k] = s(v)
                else:
                    try:
                        settings[k] = int(v)
                    except (TypeError, ValueError):
                        pass
        return (read_sheet(wb, "Companies"), read_sheet(wb, "People"),
                read_sheet(wb, "Applications"), settings)
    finally:
        wb.close()


# ---------- the follow-up rules ----------
def person_status(p, S):
    """Returns (state, action, reason, priority, due_date). state: act, soon, wait, done."""
    st, days, name = p["stage"], p["days"], p["name"]
    if st == "dead":
        return "done", "", "", 99, None
    if st == "found":
        return "act", "Send connection request", "Found, not contacted yet.", 6, None
    if st == "replied":
        ago = (f"{days} day{'s' if days != 1 else ''} ago") if days is not None else "recently"
        return "act", "Reply and ask for a chat", f"They replied {ago}.", 2, None
    if st == "chat booked":
        cd = p["chat_date"]
        if cd is None:
            return "soon", "Add the chat date", "Chat booked but no date on the row.", 5, None
        if cd <= p["today"]:
            return "act", "Log how the chat went", f"Chat was set for {fmt(cd)}.", 2, None
        return "soon", f"Chat on {fmt(cd)}", f"{n_days((cd - p['today']).days)} away.", 5, cd
    if st == "chat done":
        if days is None:
            return "act", "Send thank-you", "Chat done, no date on the row.", 1, None
        late = " Overdue." if days > S["thankyou_due_days"] else ""
        return "act", "Send thank-you", f"Chat done {n_days(days)} ago.{late}", 1, None
    if days is None:
        return "act", "Add a stage date", "No date on this row, so I can't time the follow-up.", 8, None

    def timed(limit, action, reason, prio, waiting_label):
        due = p["since"] + dt.timedelta(days=limit)
        if days >= limit:
            return "act", action, reason, prio, None
        return "wait", waiting_label, f"{n_days(limit - days)} until it's time to act.", prio, due

    if st == "request sent":
        return timed(S["request_nudge_days"], "Nudge, or move on",
                     f"Request sent {n_days(days)} ago, not accepted.", 4, "Request not accepted yet")
    if st == "accepted":
        r = timed(S["accepted_message_days"], "Send your first message",
                  f"Accepted {n_days(days)} ago, no message sent.", 3, "")
        return ("soon",) + r[1:] if r[0] == "wait" else r
    if st == "message sent":
        return timed(S["message_followup_days"], "Send one polite follow-up",
                     f"Message sent {n_days(days)} ago, no reply.", 4, "Message sent, no reply yet")
    if st == "follow-up sent":
        return timed(S["second_silence_days"], "Mark dead (second silence)",
                     f"Follow-up sent {n_days(days)} ago, still no reply.", 7, "Follow-up sent, no reply yet")
    if st == "thank-you sent":
        return timed(S["checkback_days"], "Check back in",
                     f"Thank-you sent {n_days(days)} ago.", 6, "Thank-you sent")
    return "act", "Fix the stage", f"Stage '{st}' isn't one of the options.", 8, None


def norm_status(v):
    t = s(v).lower()
    return STATUS_ALIASES.get(t, t)


_build_cache = {"key": None, "value": None}
_build_lock = threading.Lock()


def build():
    """Everything the pages need from tracker.xlsx. Re-read only when the file changes (or the day changes)."""
    try:
        st = os.stat(PATH)
        key = (st.st_mtime_ns, st.st_size, dt.date.today())
    except OSError:
        key = None
    with _build_lock:
        if key is not None and _build_cache["key"] == key:
            return _build_cache["value"]
        value = _build()
        _build_cache.update(key=key, value=value)
        return value


def _build():
    today = dt.date.today()
    companies, people_raw, apps_raw, S = load()

    people = []
    for r in people_raw:
        p = {
            "row": r["_row"], "company": s(r.get("Company")), "name": s(r.get("Person")) or "(no name)",
            "role": s(r.get("Role")), "found": s(r.get("How found")), "link": s(r.get("LinkedIn link")),
            "stage": s(r.get("Stage")).lower(), "stage_date": d(r.get("Stage date")),
            "last_contact": d(r.get("Last contact")), "answer": s(r.get("Sponsorship answer")),
            "referral": s(r.get("Referral offered")), "chat_date": d(r.get("Chat date")),
            "notes": s(r.get("Notes")), "today": today,
        }
        p["since"] = p["stage_date"] or p["last_contact"]
        p["days"] = (today - p["since"]).days if p["since"] else None
        p["state"], p["action"], p["reason"], p["prio"], p["due"] = person_status(p, S)
        p["key"] = p["company"].lower()
        people.append(p)

    apps = []
    for r in apps_raw:
        a = {
            "row": r["_row"], "company": s(r.get("Company")), "role": s(r.get("Role")),
            "link": s(r.get("Link")), "focus": s(r.get("Focus")), "deadline": d(r.get("Deadline")),
            "applied": d(r.get("Date applied")), "status": norm_status(r.get("Status")),
            "referred": s(r.get("Referred by")), "next_date": d(r.get("Next step date")),
            "next": s(r.get("Next step")), "notes": s(r.get("Notes")),
            "cv_used": s(r.get("CV used")), "match_level": s(r.get("Match level")),
        }
        a["key"] = a["company"].lower()
        apps.append(a)

    by_p, by_a = {}, {}
    for p in people:
        by_p.setdefault(p["key"], []).append(p)
    for a in apps:
        by_a.setdefault(a["key"], []).append(a)

    def company_stage(key):
        ps, as_ = by_p.get(key, []), by_a.get(key, [])
        sts = {a["status"] for a in as_}
        if "offer" in sts:
            return "Offer"
        if "interviewing" in sts:
            return "Interviewing"
        if "screening" in sts:
            return "Screening"
        if "applied" in sts:
            return "Applied"
        if "interested" in sts:
            return "Interested"
        if any(p["stage"] in SPOKEN for p in ps):
            return "In conversation"
        if any(p["stage"] != "dead" for p in ps):
            return "Reaching out"
        if ps or as_:
            return "Went quiet"
        return "Not started"

    cos, seen = [], set()
    for r in companies:
        name = s(r.get("Company"))
        if not name:
            continue
        seen.add(name.lower())
        cos.append({"data": r, "name": name, "key": name.lower(), "rank": r.get("Rank"),
                    "tier": r.get("Tier"), "other": False})
    for key in sorted(set(by_p) | set(by_a)):
        if key and key not in seen:
            nm = (by_p.get(key) or by_a.get(key))[0]["company"]
            cos.append({"data": {}, "name": nm, "key": key, "rank": None, "tier": None, "other": True})
    for c in cos:
        c["stage"] = company_stage(c["key"])
        c["people"] = by_p.get(c["key"], [])
        c["apps"] = by_a.get(c["key"], [])
        c["answer"] = s(c["data"].get("Sponsorship answer from a person"))
        c["people_answers"] = [p for p in c["people"] if p["answer"]]
        c["has_answer"] = bool(c["answer"] or c["people_answers"])
        c["everify"] = s(c["data"].get("E-Verify (STEM OPT needs it)"))
        c["url"] = "/company/" + quote(c["name"], safe="")
    cmap = {c["key"]: c for c in cos}

    spoken = {k for k, v in by_p.items() if any(p["stage"] in SPOKEN for p in v)}

    # Today
    todo, soon = [], []
    for p in people:
        item = {"prio": p["prio"], "who": p["name"], "company": p["company"], "role": p["role"],
                "action": p["action"], "reason": p["reason"], "url": f"/person/{p['row']}",
                "curl": cmap.get(p["key"], {}).get("url", "")}
        if p["state"] == "act":
            todo.append(item)
        elif p["state"] == "soon":
            soon.append(item)
    warn = S["deadline_warning_days"]
    for a in apps:
        if a["status"] not in OPEN_APP:
            continue
        who = a["role"] or "(no role)"
        base = {"who": who, "company": a["company"], "role": "Application",
                "url": f"/application/{a['row']}/edit", "row": a["row"], "link": a["link"],
                "curl": cmap.get(a["key"], {}).get("url", "")}
        no_contact = a["key"] not in spoken
        if a["status"] == "interested":
            extra = " You've spoken to no one there." if no_contact else ""
            if a["deadline"]:
                left = (a["deadline"] - today).days
                if left < 0:
                    todo.append({**base, "prio": 1, "action": "Deadline passed: apply or close it",
                                 "reason": f"Deadline was {fmt(a['deadline'])}.{extra}"})
                    continue
                elif left <= warn:
                    todo.append({**base, "prio": 1 if left <= 2 else 2, "action": "Apply",
                                 "reason": f"Deadline {fmt(a['deadline'])}, {n_days(left)} left.{extra}"})
                    continue
            if no_contact:
                todo.append({**base, "prio": 5, "action": "Find a contact before applying",
                             "reason": "You've spoken to no one at this company."})
        if a["next_date"] and a["next_date"] <= today:
            todo.append({**base, "prio": 3, "action": a["next"] or "Next step due",
                         "reason": f"Next step date was {fmt(a['next_date'])}."})
    todo.sort(key=lambda x: (x["prio"], x["company"].lower()))
    soon.sort(key=lambda x: x["company"].lower())

    # Waiting on
    waiting = [{"p": p, "label": p["action"]} for p in people if p["state"] == "wait"]
    waiting.sort(key=lambda w: (w["p"]["due"] or today, w["p"]["company"].lower()))
    waiting_apps = [a for a in apps if a["status"] in ("applied", "screening", "interviewing")]
    waiting_apps.sort(key=lambda a: a["applied"] or today)

    # Applications page: flags and urgency
    far = dt.date.max
    for a in apps:
        a["no_contact"] = a["status"] in OPEN_APP and a["key"] not in spoken
        a["days_left"] = (a["deadline"] - today).days if a["deadline"] else None
        a["deadline_flag"] = (a["status"] == "interested" and a["days_left"] is not None
                              and a["days_left"] <= warn)
        a["next_due"] = bool(a["next_date"] and a["next_date"] <= today and a["status"] in OPEN_APP)
        a["curl"] = cmap.get(a["key"], {}).get("url", "")
        if a["status"] not in OPEN_APP:
            bucket = 9
        elif a["deadline_flag"] and a["days_left"] < 0:
            bucket = 0
        elif a["deadline_flag"]:
            bucket = 1
        elif a["next_due"]:
            bucket = 2
        elif a["next_date"] and (a["next_date"] - today).days <= 7:
            bucket = 3
        elif a["no_contact"]:
            bucket = 4
        else:
            bucket = 5
        soonest = min(x for x in (a["deadline"] if a["status"] == "interested" else None,
                                  a["next_date"], far) if x)
        a["sort"] = (bucket, soonest, a["company"].lower(), a["role"].lower())
    apps_sorted = sorted(apps, key=lambda a: a["sort"])
    counts = {st: sum(1 for a in apps if a["status"] == st) for st in STATUSES}
    other = [a for a in apps if a["status"] not in STATUSES]
    submitted = [a for a in apps if a["status"] in {"applied"} | RESPONDED
                 or (a["status"] == "withdrawn" and a["applied"])]
    responded = [a for a in apps if a["status"] in RESPONDED]

    def rate(group):
        sub = [a for a in group if a in submitted]
        return {"submitted": len(sub), "responded": sum(1 for a in sub if a["status"] in RESPONDED)}
    cv_stats = {"Tailored CV": rate([a for a in apps if a["cv_used"]]),
                "Standard CV": rate([a for a in apps if not a["cv_used"]])}
    level_stats = {lv: rate([a for a in apps if a["match_level"] == lv])
                   for lv in MATCH_LEVELS}

    names = sorted({c["name"] for c in cos}, key=str.lower)
    return {"today": today, "S": S, "cos": cos, "cmap": cmap, "people": people, "apps": apps,
            "todo": todo, "soon": soon, "waiting": waiting, "waiting_apps": waiting_apps,
            "apps_sorted": apps_sorted, "counts": counts, "other_status": other,
            "n_submitted": len(submitted), "n_responded": len(responded), "company_names": names,
            "cv_stats": cv_stats, "level_stats": level_stats}


# ---------- pages ----------

@app.route("/waiting")
def waiting_page():
    return render_template("waiting.html", **build(), active="waiting")


@app.route("/companies")
def companies_page():
    return render_template("companies.html", **build(), active="companies")


@app.route("/company/<path:name>")
def company_page(name):
    m = build()
    c = m["cmap"].get(name.lower())
    if not c:
        abort(404)
    links, has_slug, has_school = find_links(m["S"])
    search_as = search_name(c["name"])
    links = [(label, tpl, fill(tpl, search_as), hint) for label, tpl, hint in links]
    return render_template("company.html", c=c, links=links, has_slug=has_slug, has_school=has_school,
                           search_as=search_as, **m, active="companies")


@app.route("/settings", methods=["GET", "POST"])
def settings_page():
    m = build()
    errors, vals = [], dict(m["S"])
    if request.method == "POST":
        check_token()
        changes = {}
        for k in DEFAULTS:
            if k in ("data_through", "email_from", "email_to", "digest_time") or k not in request.form:
                continue
            v = request.form.get(k, "").strip()
            if k in TEXT_SETTINGS:
                if k == "school_linkedin_url" and v and "linkedin.com/school/" not in v:
                    errors.append("The school page address should look like "
                                  "https://www.linkedin.com/school/your-school/. Open your school on LinkedIn "
                                  "and copy the address from the browser.")
                vals[k] = v
            else:
                try:
                    n = int(v)
                    if n < 0:
                        raise ValueError
                    v = n
                    vals[k] = n
                except ValueError:
                    errors.append(f"'{SETTING_LABELS[k]}' needs a whole number.")
                    vals[k] = v
                    continue
            if v != m["S"].get(k):
                changes[k] = v
        if not errors:
            if changes:
                try:
                    write_settings(changes)
                    return redirect("/settings?msg=Saved")
                except SaveError as e:
                    errors.append(str(e))
            else:
                return redirect("/settings?msg=Nothing changed")
    return render_template("settings.html", vals=vals, labels=SETTING_LABELS, text_keys=TEXT_SETTINGS,
                           errors=errors, email=email_status(m["S"]), **m, active="settings")


# ---------- daily email ----------
import digest  # noqa: E402

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TIME_RE = re.compile(r"^([01]?\d|2[0-3]):[0-5]\d$")


def email_status(S):
    log = digest.read_log()
    return {"has_password": bool(digest.get_password(S.get("email_from", ""))),
            "has_keyring": digest._keyring() is not None,
            "schedule": digest.schedule_status(), "last_result": log.get("last_result", ""),
            "last_try": (log.get("last_try") or "").replace("T", " at ")[:19]}


@app.route("/settings/email", methods=["POST"])
def settings_email():
    check_token()
    S = build()["S"]
    sender = request.form.get("email_from", "").strip()
    to = request.form.get("email_to", "").strip()
    hhmm = request.form.get("digest_time", "").strip() or "07:30"
    password = request.form.get("app_password", "").strip()
    problems = []
    if not EMAIL_RE.match(sender):
        problems.append("Add the Gmail address that will send the email.")
    elif not sender.lower().endswith(("@gmail.com", "@googlemail.com")):
        problems.append("The sending address needs to be a Gmail address. This setup only knows Gmail.")
    if to and not EMAIL_RE.match(to):
        problems.append("The 'send to' address doesn't look like an email address.")
    if not TIME_RE.match(hhmm):
        problems.append("Write the time as hours and minutes, like 07:30.")
    if password and len(password.replace(" ", "")) != 16:
        problems.append("A Google app password is 16 letters. Copy it again from Google.")
    if problems:
        return redirect("/settings?msg=" + quote(" ".join(problems)) + "#email")
    hhmm = "%02d:%s" % (int(hhmm.split(":")[0]), hhmm.split(":")[1])
    try:
        changes = {k: v for k, v in (("email_from", sender), ("email_to", to), ("digest_time", hhmm))
                   if v != S.get(k, "")}
        if changes:
            write_settings(changes)
        if password:
            digest.set_password(sender, password)
        if "digest_time" in changes and digest.schedule_status() == "on":
            digest.schedule_on(hhmm)
    except (SaveError, RuntimeError) as e:
        return redirect("/settings?msg=" + quote(str(e)) + "#email")
    return redirect("/settings?msg=" + quote("Email settings saved.") + "#email")


@app.route("/settings/email/test", methods=["POST"])
def settings_email_test():
    check_token()
    ok, message = digest.run(test=True)
    return redirect("/settings?msg=" + quote(message if ok else "Not sent. " + message) + "#email")


@app.route("/settings/email/schedule", methods=["POST"])
def settings_email_schedule():
    check_token()
    S = build()["S"]
    try:
        if request.form.get("on") == "1":
            if not digest.get_password(S.get("email_from", "")):
                return redirect("/settings?msg=" + quote("Save the Gmail address and app password first, "
                                                         "then send a test.") + "#email")
            digest.schedule_on(S.get("digest_time") or "07:30")
            msg = f"Daily email is on. It goes at {S.get('digest_time') or '07:30'} each day, or as soon as the laptop wakes after that."
        else:
            digest.schedule_off()
            msg = "Daily email is off."
    except (RuntimeError, OSError) as e:
        msg = f"Windows Task Scheduler said: {e}"
    return redirect("/settings?msg=" + quote(msg) + "#email")


@app.route("/person/<int:row>")
def person_page(row):
    m = build()
    p = next((x for x in m["people"] if x["row"] == row), None)
    if not p:
        abort(404)
    return render_template("person.html", p=p, co=m["cmap"].get(p["key"]), **m, active="")


@app.errorhandler(Exception)
def oops(e):
    code = getattr(e, "code", 500)
    if code == 400:
        return render_template("error.html", title="Form expired",
                               msg="The site was restarted since this form opened. Go back, refresh, and try again.",
                               active=""), 400
    if code == 404:
        return render_template("error.html", title="Not found",
                               msg="That company or person isn't in tracker.xlsx.", active=""), 404
    if isinstance(e, (PermissionError, FileNotFoundError, OSError)) or "zip" in type(e).__name__.lower():
        msg = ("I couldn't read tracker.xlsx. If Excel or OneDrive is saving it, wait a few seconds and refresh. "
               f"The file should be at: {PATH}")
    else:
        msg = (f"Something went wrong ({type(e).__name__}: {e}). If you just edited tracker.xlsx in Excel, "
               "check the last row you changed. Otherwise, tell Claude what you clicked.")
    return render_template("error.html", title="Couldn't load the tracker", msg=msg, active=""), 500


# ---------- writing to the workbook ----------
from openpyxl.worksheet.datavalidation import DataValidation  # noqa: E402

BACKUPS = os.path.join(HERE, "backups")
EXCEL_LOCK = os.path.join(HERE, "~$tracker.xlsx")
TOKEN = secrets.token_hex(16)  # stops other websites posting to this local site

PEOPLE_FIELDS = ["Company", "Person", "Role", "How found", "LinkedIn link", "Stage", "Stage date",
                 "Last contact", "Sponsorship answer", "Referral offered", "Chat date", "Notes"]
APP_FIELDS = ["Company", "Role", "Link", "Focus", "Deadline", "Date applied", "Status", "Referred by",
              "Next step date", "Next step", "Notes", "CV used", "Match level"]
MATCH_LEVELS = ("Strong match", "Small tweaks", "Major tweaks", "Weak match")
NEW_COLUMNS = {"Applications": ["CV used", "Match level"]}  # added to the sheet the first time they're needed
DATE_FIELDS = {"Stage date", "Last contact", "Chat date", "Deadline", "Date applied", "Next step date"}


class SaveError(Exception):
    pass


def backup_once_a_day():
    """Copy tracker.xlsx into backups/ before the first site save of each day. Never deletes backups."""
    os.makedirs(BACKUPS, exist_ok=True)
    stamp = dt.date.today().isoformat()
    if any(f.startswith(f"tracker_{stamp}") for f in os.listdir(BACKUPS)):
        return None
    dst = os.path.join(BACKUPS, f"tracker_{stamp}_{dt.datetime.now():%H%M%S}.xlsx")
    shutil.copy2(PATH, dst)
    return dst


def ensure_validations(wb):
    """Put the dropdowns back. Excel stores the company dropdown in a form openpyxl drops on save."""
    lists = {
        "People": [("F", '"' + ",".join(STAGES) + '"', False), ("J", '"Yes,No"', False),
                   ("A", "=Companies!$B$2:$B$400", True)],
        "Applications": [("D", '"Product,Strategy"', False), ("G", '"' + ",".join(STATUSES) + '"', False),
                         ("A", "=Companies!$B$2:$B$400", True)],
    }
    if "Applications" in wb.sheetnames:
        for c in wb["Applications"][1]:
            if s(c.value) == "Match level":
                lists["Applications"].append((c.column_letter, '"' + ",".join(MATCH_LEVELS) + '"', False))
    for sheet, rules in lists.items():
        if sheet not in wb.sheetnames:
            continue
        ws = wb[sheet]
        ws.data_validations.dataValidation = []
        for col, formula, warn_only in rules:
            dv = DataValidation(type="list", formula1=formula, allow_blank=True)
            dv.errorStyle = "warning" if warn_only else "stop"
            dv.showErrorMessage = True
            ws.add_data_validation(dv)
            dv.add(f"{col}2:{col}1000")


def next_empty_row(ws, ncols):
    last = 1
    for row in ws.iter_rows(min_row=2, max_col=ncols):
        if any(c.value not in (None, "") for c in row):
            last = row[0].row
    return last + 1


def write_row(sheet, row, values, expect=None):
    """Write one row. row=None adds a new row. expect guards against the row having moved in Excel."""
    if os.path.exists(EXCEL_LOCK):
        raise SaveError("tracker.xlsx is open in Excel. Save and close it there, then press Save again. "
                        "Nothing was changed.")
    backup_once_a_day()
    wb = openpyxl.load_workbook(PATH)
    ws = wb[sheet]
    head = {s(c.value): c.column for c in ws[1] if s(c.value)}
    values = {k: v for k, v in values.items() if k in head or k not in NEW_COLUMNS.get(sheet, []) or v not in ("", None)}
    for k in values:
        if k not in head and k in NEW_COLUMNS.get(sheet, []):
            col = max(head.values()) + 1
            from copy import copy as _copy
            src = ws.cell(1, col - 1)
            cell = ws.cell(1, col, k)
            cell.font, cell.fill, cell.alignment = _copy(src.font), _copy(src.fill), _copy(src.alignment)
            ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 34 if k == "CV used" else 14
            head[k] = col
    for k in values:
        if k not in head:
            raise SaveError(f"The {sheet} sheet has no '{k}' column. Was a heading renamed?")
    if row is None:
        row = next_empty_row(ws, max(head.values()))
    elif expect:
        for k, v in expect.items():
            if s(ws.cell(row, head[k]).value).lower() != s(v).lower():
                raise SaveError(f"Row {row} of {sheet} has changed since you opened this form (maybe in Excel). "
                                "Nothing was changed. Go back, refresh, and try again.")
    for k, v in values.items():
        c = ws.cell(row, head[k])
        c.value = v if v not in ("",) else None
        if isinstance(v, dt.date):
            c.number_format = "yyyy-mm-dd"
    save_workbook(wb)
    return row


def save_workbook(wb):
    ensure_validations(wb)
    wb.calculation.fullCalcOnLoad = True
    tmp = os.path.join(HERE, "tracker.saving.xlsx")
    wb.save(tmp)
    try:
        os.replace(tmp, PATH)
    except PermissionError:
        os.remove(tmp)
        raise SaveError("Windows wouldn't let me replace tracker.xlsx. It may be open in Excel, or OneDrive "
                        "may be syncing it. Wait a moment and try again. Nothing was changed.")


def write_settings(changes):
    """Update Settings rows by key. Adds a row for a key that isn't there yet."""
    if os.path.exists(EXCEL_LOCK):
        raise SaveError("tracker.xlsx is open in Excel. Save and close it there, then press Save again. "
                        "Nothing was changed.")
    backup_once_a_day()
    wb = openpyxl.load_workbook(PATH)
    ws = wb["Settings"]
    rows = {s(ws.cell(r, 3).value): r for r in range(2, ws.max_row + 1) if s(ws.cell(r, 3).value)}
    for k, v in changes.items():
        r = rows.get(k)
        if r is None:
            r = next_empty_row(ws, 3)
            ws.cell(r, 1, SETTING_LABELS.get(k, k))
            ws.cell(r, 3, k)
            rows[k] = r
        ws.cell(r, 2, v if v != "" else None)
    save_workbook(wb)


# ---------- find-people links (open LinkedIn in the browser; nothing is fetched) ----------
SUFFIXES = re.compile(r"[,\s]+(inc|incorporated|llc|l\.l\.c|corp|corporation|co|ltd|limited|lp|l\.p|llp|plc|"
                      r"pllc|n\.a)\.?$", re.I)
PLACE = re.compile(r"(?<!\bof)\s+(usa|us|americas|america|north america)$", re.I)


def search_name(name):
    """Drop legal endings (Inc, LLC, Co.) so LinkedIn searches match how people write the company."""
    n = name.strip()
    for _ in range(3):
        n2 = PLACE.sub("", SUFFIXES.sub("", n).strip(" ,.&")).strip(" ,.&")
        if n2 == n or not n2:
            break
        n = n2
    return n


def li_people(keywords):
    return "https://www.linkedin.com/search/results/people/?" + urlencode({"keywords": keywords})


CO = "__CO__"  # placeholder; the company page swaps in the name from its "Search as" box


def find_links(S):
    """Link templates. CO is replaced by the company name, on the server and again in the page as you type."""
    q = f'"{CO}"'
    links = []
    school, url = S.get("school_name", ""), S.get("school_linkedin_url", "")
    m = re.search(r"linkedin\.com/school/([^/?#]+)", url or "")
    if m:
        base = f"https://www.linkedin.com/school/{m.group(1)}/people/?"
        links.append(("Alumni here", base + urlencode({"keywords": CO}),
                      "Your school's alumni page, filtered to this company."))
        links.append(("Alumni in product or strategy", base + urlencode({"keywords": f"{CO} product"}),
                      "Alumni page, this company plus the word product. Change it to strategy in LinkedIn if you like."))
    if school:
        links.append(("Alumni (people search)", li_people(f'{q} "{school}"'),
                      "People search for this company and your school."))
    links.append(("Product people", li_people(
        f'{q} AND ("product manager" OR "product lead" OR "group product manager" OR "director of product" '
        f'OR "product marketing")'), "Product managers, leads and product marketers."))
    links.append(("Strategy people", li_people(
        f'{q} AND ("corporate strategy" OR "business strategy" OR "strategy and operations" OR "bizops" '
        f'OR "strategy manager")'), "Corporate strategy, strategy and operations, BizOps."))
    links.append(("Recruiters", li_people(f'{q} AND ("university recruiter" OR "MBA recruiter" OR "campus recruiter" '
                                          f'OR "technical recruiter" OR "talent acquisition")'),
                  "Useful for the sponsorship question."))
    return links, bool(m), bool(school)


def fill(tpl, name):
    return tpl.replace(CO, quote_plus(name))


def form_values(fields):
    out = {}
    for f in fields:
        v = request.form.get(f, "").strip()
        out[f] = (d(v) if v else None) if f in DATE_FIELDS else v
    return out


def check_token():
    if request.form.get("_token") != TOKEN:
        abort(400)


@app.context_processor
def _globals():
    return {"TOKEN": TOKEN, "STAGES": STAGES, "STATUSES": STATUSES, "msg": request.args.get("msg", "")}


def iso(v):
    return v.isoformat() if isinstance(v, dt.date) else ""


# ---------- people forms ----------
def person_form_values(p):
    return {"Company": p["company"], "Person": "" if p["name"] == "(no name)" else p["name"],
            "Role": p["role"], "How found": p["found"], "LinkedIn link": p["link"], "Stage": p["stage"],
            "Stage date": iso(p["stage_date"]), "Last contact": iso(p["last_contact"]),
            "Sponsorship answer": p["answer"], "Referral offered": p["referral"],
            "Chat date": iso(p["chat_date"]), "Notes": p["notes"]}


@app.route("/people")
def people_page():
    return render_template("people.html", **build(), active="people")


@app.route("/people/new")
def person_new():
    m = build()
    v = {f: "" for f in PEOPLE_FIELDS}
    v.update({"Company": request.args.get("company", ""), "Stage": "found", "Stage date": iso(m["today"])})
    return render_template("person_form.html", v=v, row=None, orig={}, errors=[], **m, active="people")


@app.route("/person/<int:row>/edit")
def person_edit(row):
    m = build()
    p = next((x for x in m["people"] if x["row"] == row), None)
    if not p:
        abort(404)
    v = person_form_values(p)
    return render_template("person_form.html", v=v, row=row, orig={"Company": v["Company"], "Person": v["Person"]},
                           errors=[], **m, active="people")


@app.route("/people/save", methods=["POST"])
def person_save():
    check_token()
    v = form_values(PEOPLE_FIELDS)
    row = request.form.get("_row", type=int)
    orig = {"Company": request.form.get("_orig_company", ""), "Person": request.form.get("_orig_person", "")}
    errors = []
    if not v["Company"]:
        errors.append("Add a company.")
    if not v["Person"]:
        errors.append("Add the person's name.")
    v["Stage"] = v["Stage"].lower()
    if v["Stage"] and v["Stage"] not in STAGES:
        errors.append("Pick a stage from the list.")
    if v["Stage"] and not v["Stage date"]:
        v["Stage date"] = dt.date.today()
    if not errors:
        try:
            row = write_row("People", row, v, expect=orig if row else None)
            return redirect("/people?msg=" + quote(f"Saved {v['Person']} ({v['Company']})."))
        except SaveError as e:
            errors.append(str(e))
    shown = {k: (iso(x) if isinstance(x, dt.date) else (x or "")) for k, x in v.items()}
    return render_template("person_form.html", v=shown, row=row, orig=orig, errors=errors,
                           **build(), active="people")


# ---------- application forms ----------
@app.route("/applications")
def applications_page():
    asks = [dict(c, ago=clicks.ago(c["at"])) for c in clicks.pending(closed_uids())]
    m = build()
    role_by_row = {}
    for uid, j in jobwatch.load_store()["jobs"].items():
        a = app_for_job(m, dict(j, uid=uid))
        if a:
            role_by_row[a["row"]] = uid
    return render_template("applications.html", **m, asks=asks, role_by_row=role_by_row, active="applications")


@app.route("/applications/new")
def application_new():
    m = build()
    v = {f: "" for f in APP_FIELDS}
    v.update({"Company": request.args.get("company", ""), "Status": "interested",
              "Role": request.args.get("role", ""), "Link": request.args.get("link", "")})
    return render_template("application_form.html", v=v, row=None, orig={}, errors=[], **m,
                           active="applications")


@app.route("/application/<int:row>/edit")
def application_edit(row):
    m = build()
    a = next((x for x in m["apps"] if x["row"] == row), None)
    if not a:
        abort(404)
    v = {"Company": a["company"], "Role": a["role"], "Link": a["link"], "Focus": a["focus"],
         "Deadline": iso(a["deadline"]), "Date applied": iso(a["applied"]), "Status": a["status"],
         "Referred by": a["referred"], "Next step date": iso(a["next_date"]), "Next step": a["next"],
         "Notes": a["notes"], "CV used": a["cv_used"], "Match level": a["match_level"]}
    return render_template("application_form.html", v=v, row=row,
                           orig={"Company": a["company"], "Role": a["role"]}, errors=[], **m,
                           active="applications")


@app.route("/applications/save", methods=["POST"])
def application_save():
    check_token()
    v = form_values(APP_FIELDS)
    row = request.form.get("_row", type=int)
    orig = {"Company": request.form.get("_orig_company", ""), "Role": request.form.get("_orig_role", "")}
    errors = []
    if not v["Company"]:
        errors.append("Add a company.")
    if not v["Role"]:
        errors.append("Add the role.")
    v["Status"] = v["Status"].lower() or "interested"
    if v["Status"] not in STATUSES:
        errors.append("Pick a status from the list.")
    if v["Match level"] and v["Match level"] not in MATCH_LEVELS:
        errors.append("Pick a match level from the list, or leave it blank.")
    if v["Status"] != "interested" and v["Status"] != "withdrawn" and not v["Date applied"]:
        v["Date applied"] = dt.date.today()
    if not errors:
        try:
            write_row("Applications", row, v, expect=orig if row else None)
            return redirect("/applications?msg=" + quote(f"Saved {v['Role']} at {v['Company']}."))
        except SaveError as e:
            errors.append(str(e))
    shown = {k: (iso(x) if isinstance(x, dt.date) else (x or "")) for k, x in v.items()}
    return render_template("application_form.html", v=shown, row=row, orig=orig, errors=errors,
                           **build(), active="applications")


# ---------- job watcher pages ----------
import jobwatch  # noqa: E402
import cvmatch  # noqa: E402
import cvbuild  # noqa: E402
import meaning  # noqa: E402
import rewrites  # noqa: E402

NEW_DAYS = 14


def watched_companies(m):
    """Tier 1 companies from the Companies sheet, the extra companies in jobwatch.EXTRA_WATCH, and any company you
    gave a board by hand."""
    names = [c["name"] for c in m["cos"] if s(c["tier"]) in ("1", "1.0")]
    have = {n.lower() for n in names}
    names += [n for n in jobwatch.EXTRA_WATCH if n.lower() not in have]
    store = jobwatch.load_store()
    for key, b in store["boards"].items():
        if b.get("source") == "manual" and b.get("company") and b["company"] not in names:
            names.append(b["company"])
    return names


def load_descriptions():
    try:
        with open(jobwatch.DESC_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


_desc_cache = {"key": None, "value": {}}


def descriptions_cached():
    try:
        st = os.stat(jobwatch.DESC_FILE)
        key = (st.st_mtime_ns, st.st_size)
    except OSError:
        return {}
    if _desc_cache["key"] != key:
        _desc_cache.update(key=key, value=load_descriptions())
    return _desc_cache["value"]


_jobs_cache = {}


def _stamp(path):
    try:
        st = os.stat(path)
        return (st.st_mtime_ns, st.st_size)
    except OSError:
        return None


def jobs_view(m, score=True):
    """The jobs list, remembered between clicks (31 Oct 2026): rebuilt only when the watcher's data, the tracker, the
    CVs, the rewrites, the CVs made, meaning matching's results or the date change. Callers get their own copies."""
    cv_dir = cvmatch.CV_DIR
    try:
        cv_files = tuple(sorted((n, _stamp(os.path.join(cv_dir, n))) for n in os.listdir(cv_dir)))
    except OSError:
        cv_files = ()
    key = (score, _stamp(jobwatch.STORE), _stamp(jobwatch.DESC_FILE), _build_cache.get("key"), _stamp(PATH),
           _stamp(cvbuild.INFO_FILE), cv_files, _stamp(rewrites.path()), meaning.version, dt.date.today())
    hit = _jobs_cache.get(score)
    if not hit or hit[0] != key:
        store, jobs = _jobs_view(m, score)
        # the list may have written back saved analyses, which changes the watcher's file: stamp it as it is now
        key = key[:1] + (_stamp(jobwatch.STORE),) + key[2:]
        hit = (key, store, jobs)
        _jobs_cache[score] = hit
    _, store, jobs = hit
    return dict(store), [dict(j) for j in jobs]


def _jobs_view(m, score=True):
    store = jobwatch.load_store()
    made = cvbuild.made_for() if score else {}
    cvs, cv_problems = {}, []
    if score:
        try:
            cvs, cv_problems = cvmatch.load_cvs()
        except Exception as e:
            cvs, cv_problems = {}, [f"Couldn't read the CV folder ({type(e).__name__})."]
    backfill = {}
    links = {a["link"].strip() for a in m["apps"] if a["link"]}
    today = m["today"]
    max_age = m["S"].get("jobs_max_age_days", 30)
    jobs = []
    for uid, j in store["jobs"].items():
        if not j.get("pasted") and not jobwatch.classify(j.get("title", ""))[0]:
            continue  # stored before a rule change (for example TPM roles, dropped 13 October 2026)
        j = dict(j, uid=uid)
        j["in_apps"] = j.get("added") or (j.get("url", "").strip() in links)
        fs = d(j.get("first_seen"))
        j["is_new"] = (j.get("open") and not j.get("baseline") and not j.get("dismissed") and not j["in_apps"]
                       and fs is not None and (today - fs).days <= NEW_DAYS)
        j["posted_d"] = d(j.get("posted"))
        # how old the role is: the posting date from the job board, or when the watcher first saw it
        # no posting date: a "newest first" source (Google) counts from first seen; a full list (Workday sitemap)
        # only counts roles that appeared after its first check, because the others could be months old
        when = j["posted_d"] or (fs if ((j.get("nodate") and not j.get("inventory")) or not j.get("baseline")) else None)
        j["too_old"] = when is None or (today - when).days > max_age
        if j.get("pasted"):  # you chose this one: it stays until you hide it
            j["too_old"], j["is_new"] = False, False
        if j["too_old"]:
            j["is_new"] = False
        j["curl"] = m["cmap"].get(j.get("company", "").lower(), {}).get("url", "")
        if j.get("desc_done") and j.get("av") != jobwatch.AV and j.get("open"):
            desc = descriptions_cached().get(uid, "")
            if desc:  # saved under an older version of the analysis: read it again once and save
                a_ = jobwatch.analyse(desc)
                w_, rq_ = cvmatch.weights_for(desc)
                a_["terms"], a_["req_terms"] = w_, sorted(rq_)
                a_["av"] = jobwatch.AV
                # Amazon roles saved before their sections were labelled: re-read from Amazon at the next check
                a_["relabel"] = uid.startswith("az:") and not a_.get("has_req")
                j.update(a_)
                backfill[uid] = a_
        j["industries"] = [tuple(x) for x in j.get("industries") or []]
        j["ind_names"] = [x[0] for x in j["industries"]]
        j["no_sponsor"] = j.get("sponsor") == "no" and j.get("company", "").lower() not in jobwatch.SELECTIVE_SPONSORS
        if j["no_sponsor"]:
            j["is_new"] = False  # keep it off Today and the daily email
            if not j.get("pasted") and not j["in_apps"]:
                continue  # the user's choice (31 Oct 2026): roles that say they won't sponsor are removed from view
        j["match"] = None
        if cvs and j.get("open") and not j["too_old"] and j.get("desc_done"):
            terms = j.get("terms")
            if not terms:  # analysed before key terms were stored: work them out once and save them
                desc = descriptions_cached().get(uid, "")
                terms = cvmatch._weights_cached(desc) if desc else {}
                if terms:
                    backfill.setdefault(uid, {})["terms"] = terms
            if terms:
                j["match"] = cvmatch.score(j.get("label", ""), "", cvs, j["industries"], j.get("years"),
                                           j.get("clearance"), weights=terms, req_terms=j.get("req_terms") or (),
                                           cs_degree=j.get("cs_degree"),
                                           meaning=meaning.job_score(uid, cvmatch.cv_for(j.get("label", ""))))
        j["tier"] = j["match"]["tier"] if j["match"] else 9
        j["cv_made"] = len(made.get(uid, []))
        jobs.append(j)
    if backfill:
        def save_terms(data):
            for uid, fields in backfill.items():
                if uid in data["jobs"]:
                    data["jobs"][uid].update(fields)
        try:
            jobwatch.update(save_terms)
        except Exception:
            pass
    jobs.sort(key=lambda j: (j["posted_d"] or d(j.get("first_seen")) or dt.date.min), reverse=True)
    jobs.sort(key=lambda j: j["tier"])  # best matches first, newest first within each tier
    store["cv_kinds"] = sorted(cvs)
    store["cv_problems"] = cv_problems
    return store, jobs


@app.route("/")
def today_page():
    m = build()
    try:
        _, jobs = jobs_view(m, score=False)
        new_jobs = sum(1 for j in jobs if j["is_new"])
    except Exception:
        new_jobs = 0
    return render_template("today.html", **m, new_jobs=new_jobs, active="today")


def safe_back(url, default="/jobs"):
    """Only ever return to a page on this site."""
    return url if url and url.startswith("/") and not url.startswith("//") else default


def with_msg(url, msg):
    return url + ("&" if "?" in url else "?") + "msg=" + quote(msg)


TIER_NAMES = ["Strong match", "Small tweaks", "Major tweaks", "Weak match"]


def job_tabs(jobs):
    """Which roles go in which Jobs tab. Roles in Applications, closed roles and old roles are in none."""
    live = [j for j in jobs if j.get("open") and not j["too_old"]]
    review = [j for j in live if not j.get("pasted") and not j.get("dismissed") and not j["in_apps"]]
    pasted = [j for j in jobs if j.get("pasted") and not j.get("dismissed") and not j["in_apps"]]
    pasted.sort(key=lambda j: j.get("first_seen", ""), reverse=True)
    hidden = [j for j in live if j.get("dismissed") and not j["in_apps"]]
    return {"review": review, "pasted": pasted, "hidden": hidden,
            "in_apps": sum(1 for j in live if j["in_apps"]),
            "old": sum(1 for j in jobs if j.get("open") and j["too_old"] and not j.get("pasted"))}


@app.route("/jobs")
@app.route("/jobs/<any(pasted, hidden):tab>")
def jobs_page(tab="review"):
    m = build()
    store, jobs = jobs_view(m)
    tabs = job_tabs(jobs)
    rows = tabs[tab]
    groups = []
    if tab == "review":
        for t, name in enumerate(TIER_NAMES + ["Not scored yet"]):
            g = [j for j in rows if j["tier"] == (t if t < 4 else 9)]
            if g:
                groups.append({"name": name, "rows": g, "open": t < 2})
    industry_names = sorted({n for j in rows for n in j["ind_names"]})
    n_no_sponsor = 0  # roles that say no sponsorship are no longer listed
    return render_template("jobs.html", tab=tab, tabs=tabs, rows=rows, groups=groups, store=store,
                           run=jobwatch.state, industry_names=industry_names, n_no_sponsor=n_no_sponsor,
                           back=request.path, mstat=meaning.status, **m, active="jobs")


@app.route("/jobs/role/<path:uid>")
def job_role(uid):
    m = build()
    store, jobs = jobs_view(m)
    j = next((x for x in jobs if x["uid"] == uid), None)
    if not j:
        abort(404)
    a = app_for_job(m, j)
    back = safe_back(request.args.get("back", ""))
    here = request.path + "?" + urlencode({"back": back})
    return render_template("job_role.html", j=j, app_row=a, desc=descriptions_cached().get(uid, ""),
                           versions=cvbuild.made_for().get(uid, []), tabs=job_tabs(jobs), back=back, here=here,
                           weakest=meaning.least_covered(uid, role_cands(j)), **m, active="jobs")


def role_cands(j):
    """Your rewritten bullets for this job's role type, with their IDs, for the role page's closest-bullet notes."""
    _, rw = rewrites.for_job(j.get("title", ""), j.get("label", ""))
    return [(r["id"], r["text"]) for rows in rw.values() for r in rows] or None


@app.route("/jobs/check", methods=["POST"])
def jobs_check():
    check_token()
    m = build()
    started = jobwatch.start_check(watched_companies(m), search_name)
    return redirect("/jobs?msg=" + ("Checking now. This page refreshes until it's done." if started
                                    else "A check is already running."))


@app.route("/jobs/add", methods=["POST"])
def jobs_add():
    check_token()
    uid = request.form.get("uid", "")
    store = jobwatch.load_store()
    j = store["jobs"].get(uid)
    if not j:
        abort(404)
    back = safe_back(request.form.get("back", ""))
    m = build()
    if app_for_job(m, j):
        return redirect(with_msg(back, "That role is already in Applications."))
    try:
        write_row("Applications", None, new_app_row(j, m, uid, "interested"))
    except SaveError as e:
        return redirect(with_msg(back, str(e)))
    mark_added(uid)
    return redirect(with_msg(back, f"Added to Applications as interested: {j['title']}, {j['company']}. "
                                   "It's on the Applications page now."))


def new_app_row(j, m, uid, status):
    """An Applications row for a watcher role, with the notes, CV used and match level filled in."""
    how = "Pasted in" if j.get("pasted") else "Found by the job watcher"
    note = f"{how} on {fmt(dt.date.today())}. {j.get('label', '')}. Location: {j.get('location', '') or 'not given'}."
    inds = j.get("industries") or []
    if inds:
        note += " Industry: " + ", ".join(f"{n} ({'asks for' if k == 'asks' else 'mentions'})" for n, k in inds) + "."
    if j.get("sponsor") == "no":
        note += " The description says no visa sponsorship."
    row = {"Company": j["company"], "Role": " ".join(j["title"].split()), "Link": j["url"],
           "Focus": j.get("focus", ""), "Status": status, "Notes": note}
    if status != "interested":
        row["Date applied"] = dt.date.today()
    cv_name, level = latest_cv_name(uid), match_level_of(m, uid)
    if cv_name:
        row["CV used"] = cv_name
    if level:
        row["Match level"] = level
    return row


def mark_added(uid):
    def mark(data):
        if uid in data["jobs"]:
            data["jobs"][uid]["added"] = True
    jobwatch.update(mark)


# ---------- "Did you apply?": postings opened from the tracker ----------
import clicks  # noqa: E402


def closed_uids():
    try:
        return {u for u, j in jobwatch.load_store()["jobs"].items() if j.get("open") is False}
    except Exception:
        return set()


def app_for_job(m, j):
    """The application for a Jobs-page role: same posting link, or for a pasted role with no link, same company and role."""
    if j.get("url"):
        return app_for_link(m, j["url"])
    co, role = j["company"].strip().lower(), " ".join(j["title"].split()).lower()
    return next((a for a in m["apps"] if a["company"].strip().lower() == co
                 and " ".join(a["role"].split()).lower() == role), None)


def app_for_link(m, url):
    k = clicks.key_for(url)
    return next((a for a in m["apps"] if a["link"] and clicks.key_for(a["link"]) == k), None)


@app.route("/go/job/<path:uid>")
def go_job(uid):
    """Opens a watcher role's posting, noting the click so the site can ask whether you applied."""
    j = jobwatch.load_store()["jobs"].get(uid)
    if not j or not str(j.get("url", "")).startswith("http"):
        return redirect(with_msg(f"/jobs/role/{quote(uid, safe='')}", "This role has no link. Add one with Edit."))
    a = app_for_link(build(), j["url"])
    if not a or a["status"] == "interested":  # already applied: you're only re-reading it, so don't ask
        clicks.record(j["company"], j["title"], j["url"], "Jobs", uid=uid, row=a["row"] if a else None)
    return redirect(j["url"])


@app.route("/go/app/<int:row>")
def go_app(row):
    """Opens an application's posting; asks later only if the application is still 'interested'."""
    a = next((x for x in build()["apps"] if x["row"] == row), None)
    if not a or not a["link"].startswith("http"):
        abort(404)
    if a["status"] == "interested":
        uid = next((u for u, j in jobwatch.load_store()["jobs"].items()
                    if clicks.key_for(j.get("url")) == clicks.key_for(a["link"])), "")
        clicks.record(a["company"], a["role"], a["link"], "Applications", uid=uid, row=row)
    return redirect(a["link"])


@app.route("/clicks/pending")
def clicks_pending():
    waiting = [{"key": c["key"], "company": c["company"], "role": c["role"], "ago": clicks.ago(c["at"])}
               for c in clicks.pending(closed_uids()) if c["state"] == "waiting"]
    return jsonify({"waiting": waiting})


@app.route("/clicks/answer", methods=["POST"])
def clicks_answer():
    check_token()
    key, answer = request.form.get("key", ""), request.form.get("answer", "")
    back = request.form.get("back", "")
    back = back if back.startswith("/") and not back.startswith("//") else "/applications"
    c = clicks.get(key)
    if not c:
        msg = "Already answered."
    elif answer == "not_yet":
        clicks.set_state(key, "not_yet")
        msg = f"Kept {c['role']} at {c['company']} on the Applications page list for later."
    elif answer == "no":
        clicks.remove(key)
        msg = f"Cleared {c['role']} at {c['company']}."
    elif answer == "yes":
        try:
            msg = mark_applied(c)
            clicks.remove(key)
        except SaveError as e:
            msg = str(e)
    else:
        abort(400)
    if request.form.get("ajax"):
        return jsonify({"msg": msg})
    sep = "&" if "?" in back else "?"
    return redirect(back + sep + "msg=" + quote(msg))


def mark_applied(c):
    """Set the application to applied (adding it if it isn't in Applications yet). Returns the message."""
    m = build()
    a = app_for_link(m, c["url"])
    uid = c.get("uid") or ""
    if a:
        vals = {}
        if a["status"] == "interested":
            vals["Status"] = "applied"
        if not a["applied"]:
            vals["Date applied"] = dt.date.today()
        if not a["cv_used"] and uid:
            name = latest_cv_name(uid)
            if name:
                vals["CV used"] = name
        if vals:
            write_row("Applications", a["row"], vals, expect={"Company": a["company"], "Role": a["role"]})
        return f"Marked as applied: {a['role']} at {a['company']}."
    j = jobwatch.load_store()["jobs"].get(uid) if uid else None
    if j:
        write_row("Applications", None, new_app_row(j, m, uid, "applied"))
        mark_added(uid)
    else:
        write_row("Applications", None, {"Company": c["company"], "Role": c["role"], "Link": c["url"],
                                          "Status": "applied", "Date applied": dt.date.today()})
    return f"Added to Applications as applied: {c['role']} at {c['company']}."


# ---------- jobs you paste in (roles the watcher doesn't capture) ----------
PASTE_KINDS = ["Product", "Product marketing", "Product ops", "Strategy", "MBA programme"]
PASTE_MIN = 300  # characters; less than this is probably a title or a link, not a description


@app.route("/jobs/paste")
def paste_new():
    v = {"company": request.args.get("company", ""), "title": "", "url": "", "location": "", "kind": "", "desc": ""}
    return render_template("paste.html", v=v, uid="", errors=[], kinds=PASTE_KINDS, **build(), active="jobs")


@app.route("/jobs/paste/<path:uid>/edit")
def paste_edit(uid):
    j = jobwatch.load_store()["jobs"].get(uid)
    if not j or not j.get("pasted"):
        abort(404)
    v = {"company": j["company"], "title": j["title"], "url": j.get("url", ""), "location": j.get("location", ""),
         "kind": j.get("label", ""), "desc": descriptions_cached().get(uid, "")}
    return render_template("paste.html", v=v, uid=uid, errors=[], kinds=PASTE_KINDS, **build(), active="jobs")


@app.route("/jobs/paste", methods=["POST"])
def paste_save():
    check_token()
    f = request.form
    uid = f.get("uid", "")
    v = {"company": f.get("company", "").strip(), "title": " ".join(f.get("title", "").split()),
         "url": f.get("url", "").strip(), "location": f.get("location", "").strip(), "kind": f.get("kind", ""),
         "desc": f.get("desc", "").replace("\r\n", "\n").strip()}
    store = jobwatch.load_store()
    errors = []
    if not v["company"]:
        errors.append("Add the company.")
    if not v["title"]:
        errors.append("Add the role title.")
    if len(v["desc"]) < PASTE_MIN:
        errors.append("Paste the whole job description. What's there is too short to match against your CVs.")
    if v["url"] and not v["url"].startswith(("http://", "https://")):
        errors.append("The link should start with http:// or https://, or leave it blank.")
    if v["kind"] and v["kind"] not in PASTE_KINDS:
        errors.append("Pick a kind of role from the list.")
    if v["url"] and not errors:
        k = clicks.key_for(v["url"])
        same = next(((u, j) for u, j in store["jobs"].items() if u != uid and clicks.key_for(j.get("url")) == k), None)
        if same:
            u, j = same
            where = "you pasted it" if j.get("pasted") else "the job watcher found it"
            errors.append(f"This role is already on the Jobs page ({where}: {j['title']}, {j['company']}).")
    if errors:
        return render_template("paste.html", v=v, uid=uid, errors=errors, kinds=PASTE_KINDS, **build(), active="jobs")
    label = v["kind"] or jobwatch.classify(v["title"])[1] or "Product"
    a_ = jobwatch.analyse(v["desc"])
    w_, rq_ = cvmatch.weights_for(v["desc"])
    today = dt.date.today().isoformat()
    new = not uid
    if new:
        import secrets
        uid = "pa:" + secrets.token_hex(4)
    rec = {"company": v["company"], "title": v["title"], "url": v["url"], "location": v["location"],
           "where": jobwatch.us_status(v["location"]) if v["location"] else "Unclear",
           "focus": "Strategy" if label in ("Strategy", "MBA programme") else "Product", "label": label,
           "open": True, "desc_done": True, "pasted": True, "nodate": False, "inventory": False,
           "industries": a_["industries"], "sponsor": a_["sponsor"], "clearance": a_["clearance"],
           "years": a_["years"], "cs_degree": a_["cs_degree"], "onsite": a_["onsite"], "has_req": a_["has_req"],
           "terms": w_, "req_terms": sorted(rq_), "av": jobwatch.AV, "relabel": False}

    def put(data):
        old = data["jobs"].get(uid) or {"first_seen": today, "posted": today, "baseline": True,
                                        "dismissed": False, "added": False}
        old.update(rec)
        data["jobs"][uid] = old
    jobwatch.update(put)
    jobwatch.save_descriptions({uid: v["desc"][:20000]})
    word = "Added" if new else "Saved"
    return redirect(with_msg(f"/jobs/role/{quote(uid, safe='')}?back=/jobs/pasted",
                             f"{word} {v['title']}, {v['company']}. It's in the Pasted tab too."))


@app.route("/jobs/hide", methods=["POST"])
def jobs_hide():
    check_token()
    uid, hide = request.form.get("uid", ""), request.form.get("hide") == "1"

    def mark(data):
        if uid in data["jobs"]:
            data["jobs"][uid]["dismissed"] = hide
    jobwatch.update(mark)
    back = safe_back(request.form.get("back", ""))
    return redirect(with_msg(back, "Hidden. It's in the Hidden tab." if hide else "Shown again."))


@app.route("/jobs/coverage")
def jobs_coverage():
    m = build()
    store = jobwatch.load_store()
    rows = []
    for name in watched_companies(m):
        b = store["boards"].get(name.lower(), {})
        c = m["cmap"].get(name.lower(), {})
        career = s((c.get("data") or {}).get("Career page")) or b.get("hand_link", "")
        rows.append({"name": name, "b": b, "rank": c.get("rank"), "curl": c.get("url", ""),
                     "ok": b.get("status") == "ok", "unofficial": b.get("ats") in jobwatch.UNOFFICIAL, "board_url": jobwatch.board_url(b["ats"], b["token"])
                     if b.get("ats") and b.get("token") else "",
                     "career": career, "google": "https://www.google.com/search?" + urlencode(
                         {"q": f"{search_name(name)} careers product manager"})})
    rows.sort(key=lambda r: (not r["ok"], r["rank"] or 999))
    _, jobs = jobs_view(m, score=False)
    return render_template("coverage.html", rows=rows, store=store, run=jobwatch.state, tab="coverage",
                           tabs=job_tabs(jobs), ats_names=jobwatch.ATS_NAMES, **m, active="jobs")


@app.route("/jobs/board", methods=["POST"])
def jobs_board():
    check_token()
    company = request.form.get("company", "").strip()
    action = request.form.get("action", "")
    link = request.form.get("link", "")
    if not company:
        abort(400)
    if action == "set":
        ats, token = jobwatch.parse_board_url(link)
        if not ats:
            return redirect("/jobs/coverage?msg=" + quote(
                "That link isn't a Greenhouse, Lever or Ashby board. Open the company's careers page, click a job, "
                "and copy the address if it contains greenhouse.io, lever.co or ashbyhq.com."))
        entry = {"company": company, "ats": ats, "token": token, "source": "manual", "status": "Set by you, not checked yet"}
        msg = f"Saved. {company} will be checked on {jobwatch.ATS_NAMES[ats]} next time."
    elif action == "none":
        entry = {"company": company, "source": "none", "status": "You marked it as not on these boards"}
        msg = f"{company} won't be looked up again."
    else:  # look again
        entry = {"company": company}
        msg = f"{company} will be looked up again on the next check."

    def put(data):
        data["boards"][company.lower()] = entry
    jobwatch.update(put)
    return redirect("/jobs/coverage?msg=" + quote(msg))


@app.route("/jobs/look-again", methods=["POST"])
def jobs_look_again():
    check_token()

    def clear(data):
        for b in data["boards"].values():
            if b.get("detected_none"):
                b.pop("detected_none", None)
                b["status"] = "Will be looked up again"
    jobwatch.update(clear)
    return redirect("/jobs/coverage?msg=" + quote("The uncovered companies will be looked up again on the next check."))


def auto_check_on_start():
    try:
        h = jobwatch.hours_since_last_run()
        if h is None or h > 20:
            jobwatch.start_check(watched_companies(build()), search_name)
            print("Job watcher: checking Tier 1 career feeds in the background.")
    except Exception as e:
        print(f"Job watcher didn't start: {e}")


# ---------- H-1B numbers refresh ----------
import pickle  # noqa: E402
import h1b  # noqa: E402

H1B_PREVIEW = os.path.join(HERE, "data", "h1b_preview.pkl")
h1b_state = {"running": False, "message": "", "error": "", "started": ""}


def existing_companies():
    wb = openpyxl.load_workbook(PATH, data_only=True, read_only=True)
    try:
        return h1b.read_existing(wb["Companies"])[1]
    finally:
        wb.close()


def manual_flags(existing):
    out = {}
    for k, rec in existing.items():
        fl = [f.strip() for f in str(rec.get("Flags") or "").split(";") if f.strip()]
        keep = [f for f in fl if f not in h1b.RULE_FLAGS and f != h1b.F_DROPPED]
        if keep:
            out[k] = keep
    return out


def load_preview():
    try:
        with open(H1B_PREVIEW, "rb") as f:
            return pickle.load(f)
    except (FileNotFoundError, EOFError, pickle.UnpicklingError):
        return None


def run_h1b_refresh():
    h1b_state.update({"running": True, "error": "", "message": "Starting",
                      "started": dt.datetime.now().isoformat(timespec="seconds")})
    try:
        existing = existing_companies()
        result = h1b.build(h1b.load_names(), carry_flags=manual_flags(existing),
                           progress=lambda m: h1b_state.update(message=m))
        os.makedirs(os.path.dirname(H1B_PREVIEW), exist_ok=True)
        with open(H1B_PREVIEW, "wb") as f:
            pickle.dump(result, f)
        h1b_state["message"] = "Done. Check the changes below, then apply them."
    except Exception as e:
        h1b_state.update(error=f"{type(e).__name__}: {e}", message="")
    finally:
        h1b_state["running"] = False


@app.route("/h1b")
def h1b_page():
    m = build()
    files = [{"name": os.path.basename(p), "size": os.path.getsize(p) / 1e6,
              "cached": os.path.exists(h1b.cache_path(p))} for p in h1b.list_files()]
    result, change = load_preview(), None
    if result and not h1b_state["running"]:
        existing = existing_companies()
        busy = {p["key"] for p in m["people"]} | {a["key"] for a in m["apps"]}
        change = h1b.plan(result, existing, busy)
    return render_template("h1b.html", files=files, state=h1b_state, result=result, change=change,
                           **m, active="companies")


@app.route("/h1b/refresh", methods=["POST"])
def h1b_refresh():
    check_token()
    if not h1b_state["running"]:
        threading.Thread(target=run_h1b_refresh, daemon=True).start()
    return redirect("/h1b")


@app.route("/h1b/discard", methods=["POST"])
def h1b_discard():
    check_token()
    try:
        os.remove(H1B_PREVIEW)  # our own preview file, not the user's data
    except FileNotFoundError:
        pass
    return redirect("/h1b?msg=" + quote("Preview thrown away. Nothing in tracker.xlsx changed."))


@app.route("/h1b/apply", methods=["POST"])
def h1b_apply():
    check_token()
    result = load_preview()
    if not result:
        return redirect("/h1b?msg=" + quote("There's no refreshed data to apply. Press Refresh first."))
    if os.path.exists(EXCEL_LOCK):
        return redirect("/h1b?msg=" + quote("tracker.xlsx is open in Excel. Save and close it, then press Apply again."))
    m = build()
    busy = {p["key"] for p in m["people"]} | {a["key"] for a in m["apps"]}
    try:
        backup_once_a_day()
        wb = openpyxl.load_workbook(PATH)
        _, existing = h1b.read_existing(wb["Companies"])
        change = h1b.plan(result, existing, busy)
        end = result["stats"]["window"][1]
        n = h1b.write_companies(wb, result, existing, change["keep_dropped"], end)
        h1b.write_excluded(wb, result)
        h1b.write_entities(wb, result)
        h1b.update_readme(wb, result)
        ws = wb["Settings"]
        for r in range(2, ws.max_row + 1):
            if s(ws.cell(r, 3).value) == "data_through":
                ws.cell(r, 2, end)
        save_workbook(wb)
    except SaveError as e:
        return redirect("/h1b?msg=" + quote(str(e)))
    # pin the names of companies new to the list, so they keep the same name next time
    names = h1b.load_names()
    for r in result["companies"]:
        for _, fe, *_ in r["entity_rows"]:
            names.setdefault(fe, r["name"])
    with open(h1b.NAMES_FILE + ".tmp", "w", encoding="utf-8") as f:
        json.dump(dict(sorted(names.items())), f, indent=0)
    os.replace(h1b.NAMES_FILE + ".tmp", h1b.NAMES_FILE)
    try:
        os.remove(H1B_PREVIEW)
    except FileNotFoundError:
        pass
    return redirect("/h1b?msg=" + quote(f"Applied. The Companies sheet now has {n} rows, with data up to {end}. "
                                        "A backup of the old file is in the backups folder."))



# ---------- tailored CVs (made only when you press the button, one job at a time) ----------
@app.route("/jobs/cv", methods=["POST"])
def jobs_cv():
    check_token()
    uid = request.form.get("uid", "")
    store = jobwatch.load_store()
    j = store["jobs"].get(uid)
    if not j:
        abort(404)
    desc = descriptions_cached().get(uid, "")
    back = safe_back(request.form.get("back", ""))
    if not desc:
        return redirect(with_msg(back, "This role's description hasn't been read yet, so there's nothing to tailor "
                                       "to. Press Check now on the Jobs page, then try again."))
    try:
        cvs, _ = cvmatch.load_cvs()
        job = dict(j, uid=uid, label=jobwatch.classify(j.get("title", ""))[1] or j.get("label", ""))
        info = cvbuild.build(job, desc, cvs)
    except FileNotFoundError as e:
        return redirect(with_msg(back, str(e)))
    except PermissionError:
        return redirect(with_msg(back, "Couldn't save the CV. If a version of it is open in Word, close it and try again."))
    note = applied_with_cv(uid, info["path"])
    return redirect(f"/cv/{quote(uid, safe='')}?v={info['version']}&msg=" +
                    quote(f"CV made: {os.path.basename(info['path'])}. {note}"))


@app.route("/cv/<path:uid>")
def cv_page(uid):
    versions = cvbuild.made_for().get(uid, [])
    if not versions:
        abort(404)
    v = request.args.get("v", type=int)
    info = next((x for x in versions if x.get("version") == v), versions[-1])
    return render_template("cv.html", info=info, versions=versions, uid=uid, active="jobs",
                           can_open=hasattr(os, "startfile"))



def latest_cv_name(uid):
    versions = cvbuild.made_for().get(uid, [])
    return cv_label(versions[-1]["path"]) if versions else ""


def cv_label(path):
    """Folder and file name inside Tailored CVs, so two CVs for the same company can't be confused."""
    try:
        return os.path.relpath(path, cvbuild.OUT_DIR).replace(os.sep, " / ")
    except ValueError:
        return os.path.basename(path)


def match_level_of(m, uid):
    try:
        _, jobs = jobs_view(m)
        j = next((x for x in jobs if x["uid"] == uid), None)
        return j["match"]["tier_name"] if j and j.get("match") else ""
    except Exception:
        return ""


@app.route("/cv/record", methods=["POST"])
def cv_record():
    """Put this CV's file name (and the match level) on the application for this role, adding it if needed."""
    check_token()
    uid = request.form.get("uid", "")
    v = request.form.get("v", type=int)
    versions = cvbuild.made_for().get(uid, [])
    info = next((x for x in versions if x.get("version") == v), versions[-1] if versions else None)
    j = jobwatch.load_store()["jobs"].get(uid)
    if not info or not j:
        abort(404)
    back = f"/cv/{quote(uid, safe='')}?v={info['version']}"
    m = build()
    cv_name, level = cv_label(info["path"]), match_level_of(m, uid)
    app_row = app_for_job(m, j)
    try:
        if app_row:
            vals = {"CV used": cv_name}
            if level and not app_row["match_level"]:
                vals["Match level"] = level
            write_row("Applications", app_row["row"], vals,
                      expect={"Company": app_row["company"], "Role": app_row["role"]})
            msg = f"Recorded {cv_name} on your application."
        else:
            vals = {"Company": j["company"], "Role": j["title"], "Link": j["url"], "Focus": j.get("focus", ""),
                    "Status": "interested", "CV used": cv_name,
                    "Notes": f"CV made by the site on {fmt(dt.date.today())}."}
            if level:
                vals["Match level"] = level
            write_row("Applications", None, vals)

            def mark(data):
                if uid in data["jobs"]:
                    data["jobs"][uid]["added"] = True
            jobwatch.update(mark)
            msg = f"Added to Applications as interested, with {cv_name}."
    except SaveError as e:
        msg = str(e)
    return redirect(back + "&msg=" + quote(msg))


@app.route("/cv/open", methods=["POST"])
def cv_open():
    check_token()
    target = os.path.abspath(request.form.get("path", ""))
    back = safe_back(request.form.get("back", ""))
    root = os.path.abspath(cvbuild.OUT_DIR)
    if not target.startswith(root + os.sep) or not os.path.exists(target):
        abort(400)
    note = ""
    if target.lower().endswith(".docx"):  # opening the CV itself (not the folder) counts as applying with it
        uid = next((u for u, vs in cvbuild.made_for().items()
                    for x in vs if os.path.abspath(x.get("path", "")) == target), "")
        if uid:
            note = applied_with_cv(uid, target)
    if hasattr(os, "startfile"):
        os.startfile(target)  # opens in Word, or the folder in File Explorer
        return redirect(with_msg(back, note) if note else back)
    return redirect(with_msg(back, (note + " " if note else "") + f"The file is at {target}"))


def applied_with_cv(uid, path):
    """You generate or open a CV when you apply: put the role in Applications as applied, today, with this CV.
    A role already there keeps a later status (screening, interviewing...) and its date; only an "interested" one
    moves to applied. Returns a short message for the page."""
    j = jobwatch.load_store()["jobs"].get(uid)
    if not j:
        return ""
    m = build()
    label = cv_label(path)
    a = app_for_job(m, dict(j, uid=uid))
    try:
        if a:
            vals = {"CV used": label}
            if a["status"] == "interested":
                vals["Status"] = "applied"
            if not a["applied"]:
                vals["Date applied"] = dt.date.today()
            if not a["match_level"]:
                level = match_level_of(m, uid)
                if level:
                    vals["Match level"] = level
            write_row("Applications", a["row"], vals, expect={"Company": a["company"], "Role": a["role"]})
            status = "applied" if a["status"] == "interested" else a["status"]
            msg = f"Applications updated: {status}, with this CV."
        else:
            row = new_app_row(j, m, uid, "applied")
            row["CV used"] = label
            write_row("Applications", None, row)
            mark_added(uid)
            msg = "Added to Applications as applied, dated today."
    except SaveError as e:
        if os.path.exists(EXCEL_LOCK):
            return ("Not added to Applications, because tracker.xlsx is open in Excel. Close it, then press "
                    "Record this CV on my application.")
        return f"Not added to Applications: {e}"
    if j.get("url"):
        clicks.remove(clicks.key_for(j["url"]))  # no need to ask "Did you apply?" about it any more
    return msg


@app.template_filter("fmt")
def _fmt(v):
    return fmt(v) if isinstance(v, (dt.date, dt.datetime, str)) and v else ""


@app.template_filter("num")
def _num(v, places=0):
    try:
        return f"{float(v):,.{places}f}"
    except (TypeError, ValueError):
        return ""


@app.template_filter("pct")
def _pct(v):
    try:
        return f"{float(v) * 100:.0f}%"
    except (TypeError, ValueError):
        return ""


from templates_html import TEMPLATES  # noqa: E402

app.jinja_env.loader = DictLoader(TEMPLATES)

if __name__ == "__main__":
    threading.Timer(1.2, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}")).start()
    print(f"Tracker running at http://127.0.0.1:{PORT}  (close this window to stop it)")
    threading.Timer(3, auto_check_on_start).start()
    meaning.start(descriptions_cached)  # reads job descriptions by meaning in the background
    app.run(host="127.0.0.1", port=PORT, debug=False)
