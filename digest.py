"""Daily email digest of the Today page.

Windows Task Scheduler runs this file once a day (turned on from the Settings page). It can also be run by hand:
    py digest.py          send today's digest, unless it was already sent today
    py digest.py --test   send one now, whatever happened earlier
The Gmail app password is kept in Windows Credential Manager, never in tracker.xlsx or this folder.
"""
import os
import sys
import json
import time
import smtplib
import socket
import subprocess
import datetime as dt
from email.message import EmailMessage
from xml.sax.saxutils import escape

from jinja2 import Template

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
LOG = os.path.join(DATA_DIR, "digest.json")
TASK_NAME = "PM Tracker daily email"
KEYRING_SERVICE = "PM Tracker email"
SMTP_HOST, SMTP_PORT = "smtp.gmail.com", 465
SITE = "http://127.0.0.1:5000"


# ---------- password (Windows Credential Manager through keyring) ----------
def _keyring():
    try:
        import keyring
        return keyring
    except ImportError:
        return None


def get_password(address):
    kr = _keyring()
    if not kr or not address:
        return None
    try:
        return kr.get_password(KEYRING_SERVICE, address.lower())
    except Exception:
        return None


def set_password(address, password):
    kr = _keyring()
    if not kr:
        raise RuntimeError("The keyring package isn't installed. Close the site and double-click start.bat again.")
    kr.set_password(KEYRING_SERVICE, address.lower(), password.replace(" ", ""))


# ---------- log ----------
def read_log():
    try:
        with open(LOG, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def write_log(**kw):
    os.makedirs(DATA_DIR, exist_ok=True)
    data = read_log()
    data.update(kw)
    tmp = LOG + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, LOG)


# ---------- the email ----------
HTML = Template("""<div style="font-family:Segoe UI,Arial,sans-serif;font-size:15px;color:#1f2328;max-width:680px">
<h2 style="margin:0 0 4px">Today, {{ today }}</h2>
<p style="color:#6b7280;margin:0 0 16px">From your PM Tracker. {{ todo|length }} to do{% if new_jobs %}, {{ new_jobs|length }} new role{{ 's' if new_jobs|length != 1 }}{% endif %}.</p>
{% if todo %}<table cellpadding="6" style="border-collapse:collapse;width:100%">
{% for t in todo %}<tr style="border-top:1px solid #e5e2d9"><td style="vertical-align:top"><b>{{ t.action }}</b></td>
<td style="vertical-align:top">{{ t.who }}{% if t.role and t.role != 'Application' %}, {{ t.role }}{% endif %}{% if t.role == 'Application' %} (application){% endif %}<br><span style="color:#6b7280">{{ t.company }}</span></td>
<td style="vertical-align:top;color:#6b7280">{{ t.reason }}</td></tr>{% endfor %}</table>
{% else %}<p>Nothing to chase today.</p>{% endif %}
{% if soon %}<h3 style="margin:20px 0 6px">Coming up</h3><ul style="padding-left:18px;margin:0">
{% for t in soon %}<li>{{ t.action }}: {{ t.who }}, {{ t.company }} <span style="color:#6b7280">({{ t.reason }})</span></li>{% endfor %}</ul>{% endif %}
{% if new_jobs %}<h3 style="margin:20px 0 6px">New roles from the job watcher</h3><ul style="padding-left:18px;margin:0">
{% for j in new_jobs %}<li>{% if j.match %}<b>{{ j.match.tier_name }}:</b> {% endif %}<a href="{{ j.url }}">{{ j.title }}</a>, {{ j.company }} <span style="color:#6b7280">({{ j.location }})</span></li>{% endfor %}</ul>{% endif %}
<p style="color:#6b7280;margin-top:20px">Waiting on {{ waiting }} {{ 'person' if waiting == 1 else 'people' }}. {{ applied }} application{{ 's' if applied != 1 }} in progress.<br>
Open the tracker: <a href="{{ site }}">{{ site }}</a> (works while the site is running on your laptop).</p></div>""")

TEXT = Template("""Today, {{ today }}
{{ todo|length }} to do{% if new_jobs %}, {{ new_jobs|length }} new roles{% endif %}.

{% for t in todo %}- {{ t.action }}: {{ t.who }}, {{ t.company }}. {{ t.reason }}
{% else %}Nothing to chase today.
{% endfor %}{% if soon %}
Coming up
{% for t in soon %}- {{ t.action }}: {{ t.who }}, {{ t.company }} ({{ t.reason }})
{% endfor %}{% endif %}{% if new_jobs %}
New roles
{% for j in new_jobs %}- {{ j.title }}, {{ j.company }}: {{ j.url }}
{% endfor %}{% endif %}
Waiting on {{ waiting }} {{ 'person' if waiting == 1 else 'people' }}. {{ applied }} application{{ 's' if applied != 1 }} in progress.
Open the tracker: {{ site }} (works while the site is running).
""")


def compose(refresh_jobs=True):
    """Build the subject, plain text and HTML from the same data as the Today page."""
    import app  # the site's own logic, so the email always matches the Today page
    import jobwatch
    m = app.build()
    if refresh_jobs:
        try:
            h = jobwatch.hours_since_last_run()
            if h is None or h > 20:
                jobwatch.run_check(app.watched_companies(m), app.search_name)
        except Exception:
            pass  # the email still goes without fresh jobs
    try:
        _, jobs = app.jobs_view(m)
        new_jobs = [j for j in jobs if j["is_new"] and j.get("where") != "Not US"]
    except Exception:
        new_jobs = []
    ctx = {"today": app.fmt(m["today"]), "todo": m["todo"], "soon": m["soon"], "new_jobs": new_jobs,
           "waiting": len(m["waiting"]), "applied": len(m["waiting_apps"]), "site": SITE}
    n = len(m["todo"])
    bits = [f"{n} to do" if n else "nothing due"]
    if new_jobs:
        bits.append(f"{len(new_jobs)} new role{'s' if len(new_jobs) != 1 else ''}")
    subject = f"PM Tracker, {app.fmt(m['today'])}: " + ", ".join(bits)
    return subject, TEXT.render(**ctx), HTML.render(**ctx), m["S"]


def send(subject, text, html, sender, to, password):
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, sender, to
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as s:
        s.login(sender, password)
        s.send_message(msg)


def friendly(e):
    if isinstance(e, smtplib.SMTPAuthenticationError):
        return ("Gmail refused the login. Check the Gmail address, and that the password is a 16-letter app password, "
                "not your normal Gmail password.")
    if isinstance(e, (socket.gaierror, OSError, smtplib.SMTPServerDisconnected)):
        return f"Couldn't reach Gmail ({type(e).__name__}). Check the internet connection."
    return f"{type(e).__name__}: {e}"


def run(test=False, tries=4, wait=60):
    """Send the digest. Returns (ok, message). Daily runs send at most once per day."""
    today = dt.date.today().isoformat()
    if not test and read_log().get("last_sent") == today:
        return True, "Already sent today."
    subject, text, html, S = compose(refresh_jobs=not test)
    sender, to = S.get("email_from", ""), S.get("email_to", "") or S.get("email_from", "")
    password = get_password(sender)
    if not sender or not password:
        msg = "Email isn't set up yet. Add the Gmail address and app password on the Settings page."
        write_log(last_result=msg, last_try=dt.datetime.now().isoformat(timespec="seconds"))
        return False, msg
    err = None
    for i in range(1 if test else tries):
        try:
            send(subject, text, html, sender, to, password)
            now = dt.datetime.now().isoformat(timespec="seconds")
            if test:
                write_log(last_result=f"Test email sent to {to}.", last_try=now)
            else:
                write_log(last_sent=today, last_result=f"Sent to {to}.", last_try=now)
            return True, f"Sent to {to}: {subject}"
        except smtplib.SMTPAuthenticationError as e:
            err = e
            break  # retrying a wrong password won't help
        except Exception as e:
            err = e
            if i < tries - 1:
                time.sleep(wait)  # the laptop may have just woken up
    msg = friendly(err)
    write_log(last_result="Not sent. " + msg, last_try=dt.datetime.now().isoformat(timespec="seconds"))
    return False, msg


# ---------- Windows Task Scheduler ----------
def pythonw():
    exe = sys.executable
    w = os.path.join(os.path.dirname(exe), "pythonw.exe")
    return w if os.path.exists(w) else exe


def task_xml(hhmm):
    start = (dt.date.today() + dt.timedelta(days=1)).isoformat() + f"T{hhmm}:00"
    script = os.path.join(HERE, "digest.py")
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>Sends the PM Tracker Today list by email. Turn off from the tracker's Settings page.</Description></RegistrationInfo>
  <Triggers><CalendarTrigger><StartBoundary>{start}</StartBoundary><Enabled>true</Enabled>
    <ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay></CalendarTrigger></Triggers>
  <Principals><Principal id="Author"><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <ExecutionTimeLimit>PT30M</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author"><Exec>
    <Command>{escape(pythonw())}</Command>
    <Arguments>"{escape(script)}"</Arguments>
    <WorkingDirectory>{escape(HERE)}</WorkingDirectory>
  </Exec></Actions>
</Task>
"""


def _schtasks(args):
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(["schtasks"] + args, capture_output=True, text=True, creationflags=flags)


def schedule_on(hhmm):
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, "digest_task.xml")
    with open(path, "w", encoding="utf-16") as f:
        f.write(task_xml(hhmm))
    r = _schtasks(["/Create", "/TN", TASK_NAME, "/XML", path, "/F"])
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "Task Scheduler refused.").strip())


def schedule_off():
    r = _schtasks(["/Delete", "/TN", TASK_NAME, "/F"])
    if r.returncode != 0 and "cannot find" not in (r.stderr or "").lower():
        raise RuntimeError((r.stderr or r.stdout or "Task Scheduler refused.").strip())


def schedule_status():
    """Returns 'on', 'off' or 'unknown' (not Windows)."""
    if os.name != "nt":
        return "unknown"
    try:
        r = _schtasks(["/Query", "/TN", TASK_NAME])
    except Exception:
        return "unknown"
    return "on" if r.returncode == 0 else "off"


if __name__ == "__main__":
    ok, message = run(test="--test" in sys.argv)
    print(message)
    sys.exit(0 if ok else 1)
