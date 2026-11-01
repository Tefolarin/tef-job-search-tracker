TEMPLATES = {}

TEMPLATES["base.html"] = """<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TEF</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='16' fill='%230f1c24'/%3E%3Ctext x='32' y='41' font-family='Arial' font-weight='800' font-size='22' fill='white' text-anchor='middle'%3ETEF%3C/text%3E%3Ccircle cx='54' cy='54' r='8' fill='%230f766e' stroke='white' stroke-width='3'/%3E%3C/svg%3E">
<style>
/* TEF, Slate & Teal (chosen 31 October 2026). Manrope is in static/fonts so it works offline. */
@font-face{font-family:Manrope;font-weight:500;font-display:swap;src:url(/static/fonts/manrope-latin-500-normal.woff2) format('woff2')}
@font-face{font-family:Manrope;font-weight:600;font-display:swap;src:url(/static/fonts/manrope-latin-600-normal.woff2) format('woff2')}
@font-face{font-family:Manrope;font-weight:700;font-display:swap;src:url(/static/fonts/manrope-latin-700-normal.woff2) format('woff2')}
@font-face{font-family:Manrope;font-weight:800;font-display:swap;src:url(/static/fonts/manrope-latin-800-normal.woff2) format('woff2')}
:root{--bg:#f3f5f7;--card:#fff;--soft:#f8fafb;--ink:#0f1c24;--mute:#5d6b75;--line:#e3e8ec;--slate:#0f1c24;--slate-ink:#fff;--slate-mute:#9fb0bb;
--accent:#0f766e;--accent-ink:#fff;--accentsoft:#ddf1ee;--warn:#a16207;--warnsoft:#fdf4dc;--bad:#c2410c;--badsoft:#fdeee5;--ok:#15803d;--oksoft:#e3f5e8;
--shadow:0 1px 3px rgba(15,28,36,.12)}
@media (prefers-color-scheme:dark){:root{--bg:#0d151b;--card:#152029;--soft:#1a2731;--ink:#e6edf1;--mute:#93a3ae;--line:#25343f;--slate:#1d4b47;--slate-ink:#e6edf1;--slate-mute:#9fc9c3;
--accent:#3cc4b4;--accent-ink:#06201d;--accentsoft:#123733;--warn:#e7b65a;--warnsoft:#33290f;--bad:#f2875a;--badsoft:#3a1e12;--ok:#6fd08f;--oksoft:#14301d;--shadow:0 1px 3px rgba(0,0,0,.5)}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:500 15px/1.5 Manrope,"Segoe UI",system-ui,sans-serif}
b,strong{font-weight:700}
header{background:var(--card);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:4}
.bar{max-width:1160px;margin:0 auto;padding:10px 16px;display:flex;align-items:center;gap:20px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:11px;text-decoration:none!important;color:var(--ink);margin-right:auto}
.mono{width:36px;height:36px;border-radius:10px;background:var(--slate);color:var(--slate-ink);display:grid;place-items:center;font-weight:800;font-size:13px;letter-spacing:.02em;position:relative;flex:none}
.mono:after{content:"";position:absolute;right:-3px;bottom:-3px;width:11px;height:11px;border-radius:50%;background:var(--accent);border:2px solid var(--card)}
.word{font-weight:800;font-size:18px;letter-spacing:.06em;line-height:1}.tag{font-size:11.5px;color:var(--mute);margin-top:2px}
nav{display:flex;gap:2px;flex-wrap:wrap;background:var(--bg);padding:4px;border-radius:12px}
nav a{color:var(--mute);padding:7px 12px;font-size:14px;border-radius:9px;font-weight:600;text-decoration:none}
nav a:hover{color:var(--ink)}
nav a.on{background:var(--card);color:var(--ink);box-shadow:var(--shadow)}
main{max-width:1160px;margin:0 auto;padding:26px 16px 70px}
h1{font-weight:800;font-size:28px;letter-spacing:-.02em;margin:0 0 4px} h2{font-weight:700;font-size:17px;margin:30px 0 10px}
.sub{color:var(--mute);margin:0 0 16px}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
table{width:100%;border-collapse:separate;border-spacing:0;background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden}
th,td{text-align:left;padding:10px 14px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:12.5px;font-weight:700;color:var(--mute);background:var(--soft)}
tr:last-child td{border-bottom:0}
td a{font-weight:700}
.empty{background:var(--card);border:1px dashed var(--line);border-radius:14px;padding:18px;color:var(--mute)}
.pill{display:inline-block;padding:2px 10px;border-radius:99px;font-size:12px;font-weight:700;background:var(--soft);color:var(--mute);white-space:nowrap}
.pill.t1{background:var(--accentsoft);color:var(--accent)}
.pill.hot{background:var(--oksoft);color:var(--ok)}
.pill.warn{background:var(--warnsoft);color:var(--warn)}
.pill.bad{background:var(--badsoft);color:var(--bad)}
.mute{color:var(--mute)} .warn{color:var(--warn)}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin-bottom:12px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:6px}
.grid .card{margin:0}
.k{font-size:13px;color:var(--mute);font-weight:600}.v{font-size:24px;font-weight:800;letter-spacing:-.02em}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:18px 0 6px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 18px;text-decoration:none!important;color:var(--ink)}
.stat .v{font-size:30px}
.stat:hover{border-color:var(--accent)}
.stat.lead{background:var(--slate);border-color:var(--slate);color:var(--slate-ink)}.stat.lead .k{color:var(--slate-mute)}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 12px}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 10px;align-items:center}
.chip{border:1px solid var(--line);background:var(--card);color:var(--mute);border-radius:99px;padding:5px 12px;font:inherit;font-size:13px;font-weight:700;cursor:pointer}
.chip:hover{border-color:var(--accent);color:var(--ink)}
.chip.on{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}
.chip span{opacity:.75;font-weight:600;margin-left:5px}
.chip.plain{background:transparent;border-color:transparent;text-decoration:underline;padding:5px 6px}
.shown{font-size:13px;margin:0 0 10px}
.filters input,.filters select{padding:8px 12px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--ink);font:inherit}
.note{border-left:3px solid var(--accent);padding:8px 14px;margin:8px 0;background:var(--card);border-radius:0 10px 10px 0}
.btn{display:inline-block;padding:8px 15px;border-radius:10px;border:1px solid var(--accent);background:var(--accent);color:var(--accent-ink);text-decoration:none;font:inherit;font-weight:700;font-size:14px;cursor:pointer}
.btn:hover{filter:brightness(1.08)}
.btn.ghost{background:var(--card);color:var(--ink);border-color:var(--line)}
.btn.ghost:hover{border-color:var(--accent);color:var(--accent)}
.btn.small{padding:4px 11px;font-size:13px;border-radius:8px}
.actions{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 16px}
.back{display:inline-block;margin:0 0 14px;padding:6px 12px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--ink);text-decoration:none;font-size:14px;font-weight:600}
.back:hover{border-color:var(--accent);color:var(--accent)}
.flash{background:var(--accentsoft);color:var(--accent);border-radius:12px;padding:10px 16px;margin-bottom:14px}
.flash a{color:var(--accent);font-weight:800}
.errors{background:var(--badsoft);color:var(--bad);border-radius:12px;padding:10px 16px;margin-bottom:14px}
form.f{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px 16px}
form.f label{display:flex;flex-direction:column;gap:5px;font-size:13px;font-weight:600;color:var(--mute)}
form.f label.wide{grid-column:1/-1}
form.f input,form.f select,form.f textarea{padding:9px 12px;border:1px solid var(--line);border-radius:10px;background:var(--soft);color:var(--ink);font:inherit;font-weight:500;width:100%}
form.f input:focus,form.f select:focus,form.f textarea:focus,.filters input:focus,.filters select:focus{outline:2px solid var(--accent);outline-offset:-1px}
form.f textarea{min-height:70px}
.row{display:flex;gap:6px}.row input{flex:1}
.ask{position:fixed;left:16px;right:16px;bottom:16px;max-width:900px;margin:0 auto;z-index:5;background:var(--card);border:1px solid var(--accent);border-radius:14px;padding:10px 14px;box-shadow:0 8px 28px rgba(15,28,36,.2);display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.ask[hidden]{display:none}
.tabs{display:flex;gap:4px;flex-wrap:wrap;margin:8px 0 16px;border-bottom:1px solid var(--line)}
.tabs a{padding:8px 12px;color:var(--mute);text-decoration:none;border-bottom:2px solid transparent;margin-bottom:-1px;font-weight:600}
.tabs a.on{color:var(--ink);border-color:var(--accent);font-weight:700}
.tabs a span{font-size:12px;color:var(--mute);font-weight:500;margin-left:2px}
details.grp{margin:0 0 12px}details.grp>summary{cursor:pointer;padding:6px 0;font-size:16px;font-weight:700}
details.more{flex-basis:100%}details.more>summary{cursor:pointer;font-size:14px}
details.how{margin-top:24px}details.how>summary{cursor:pointer;font-weight:600}
table.jobs td{padding:9px 14px}
td.act{white-space:nowrap;text-align:right}
@media (max-width:700px){td.act{white-space:normal}td.act form{display:block!important;margin:0 0 4px}}
.desc{white-space:pre-wrap;font-size:14px;line-height:1.6}
.counts{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:10px;margin-bottom:14px}
.counts .card{margin:0;padding:10px 14px}
@media (max-width:700px){.hide-s{display:none}h1{font-size:24px}.tag{display:none}header{position:static}}
</style></head><body>
<header><div class="bar"><a class="brand" href="/"><span class="mono">TEF</span><span><span class="word" style="display:block">TEF</span><span class="tag" style="display:block">Job search command centre</span></span></a>
<nav>
<a href="/" class="{{ 'on' if active=='today' }}">Today</a>
<a href="/waiting" class="{{ 'on' if active=='waiting' }}">Waiting on</a>
<a href="/applications" class="{{ 'on' if active=='applications' }}">Applications</a>
<a href="/people" class="{{ 'on' if active=='people' }}">People</a>
<a href="/jobs" class="{{ 'on' if active=='jobs' }}">Jobs</a>
<a href="/companies" class="{{ 'on' if active=='companies' }}">Companies</a>
<a href="/settings" class="{{ 'on' if active=='settings' }}">Settings</a>
</nav></div></header>
<main>{% if msg %}<div class="flash">{{ msg }}</div>{% endif %}{% block body %}{% endblock %}</main>
<div id="askbar" class="ask" hidden></div>
<script>
/* "Did you apply?": when you come back to this tab after opening a posting, ask about it */
(function () {
  var bar = document.getElementById('askbar'), busy = false;
  if (document.getElementById('ask')) return;  /* the Applications page has its own list */
  function esc(s) { var d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
  function check() {
    if (busy || document.hidden) return;
    busy = true;
    fetch('/clicks/pending', {cache: 'no-store'}).then(function (r) { return r.json(); }).then(function (d) {
      busy = false;
      var w = d.waiting;
      if (!w.length) { bar.hidden = true; return; }
      var c = w[0];
      bar.dataset.key = c.key;
      bar.innerHTML = '<span>You opened <b>' + esc(c.role) + '</b> at ' + esc(c.company) + ' ' + esc(c.ago) + '. Did you apply?</span>' +
        '<button class="btn small" data-a="yes">Yes, applied</button>' +
        '<button class="btn small ghost" data-a="not_yet">Not yet</button>' +
        '<button class="btn small ghost" data-a="no">Not for me</button>' +
        (w.length > 1 ? '<a class="mute" href="/applications">' + (w.length - 1) + ' more waiting</a>' : '');
      bar.hidden = false;
    }).catch(function () { busy = false; });
  }
  bar.addEventListener('click', function (e) {
    var a = e.target.getAttribute('data-a');
    if (!a) return;
    var f = new FormData();
    f.append('_token', '{{ TOKEN }}'); f.append('key', bar.dataset.key); f.append('answer', a); f.append('ajax', '1');
    fetch('/clicks/answer', {method: 'POST', body: f}).then(function (r) { return r.json(); }).then(function (d) {
      bar.innerHTML = '<span>' + esc(d.msg) + '</span>';
      setTimeout(check, 2500);
    });
  });
  document.addEventListener('visibilitychange', check);
  window.addEventListener('focus', check);
  check();
})();
</script>
</body></html>"""

TEMPLATES["error.html"] = """{% extends "base.html" %}{% block body %}
<h1>{{ title }}</h1><div class="card">{{ msg }}</div>{% endblock %}"""

TEMPLATES["today.html"] = """{% extends "base.html" %}{% block body %}
<div style="display:flex;justify-content:space-between;align-items:flex-end;gap:12px;flex-wrap:wrap">
<div><h1>Today</h1><p class="sub" style="margin:0">{{ today|fmt }}. Reads tracker.xlsx fresh on every refresh.</p></div>
<div class="actions" style="margin:0"><a class="btn" href="/people/new">Add person</a><a class="btn ghost" href="/applications/new">Add application</a></div></div>
{% if new_jobs %}<div class="flash" style="margin-top:18px"><a href="/jobs">{{ new_jobs }} new product or strategy role{{ 's' if new_jobs != 1 }}</a> found by the job watcher.</div>{% endif %}
<div class="stats">
<a class="stat lead" href="#todo"><div class="k">Chase today</div><div class="v">{{ todo|length }}</div></a>
<a class="stat" href="/waiting"><div class="k">Waiting on</div><div class="v">{{ waiting|length + waiting_apps|length }}</div></a>
<a class="stat" href="/applications"><div class="k">Applications</div><div class="v">{{ apps|length }}</div></a>
<a class="stat" href="/jobs"><div class="k">New roles</div><div class="v">{{ new_jobs }}</div></a>
</div>
<h2 id="todo">Do this</h2>
{% if todo %}
<table><tr><th class="hide-s"></th><th>Action</th><th>Who</th><th>Why</th></tr>
{% for t in todo %}<tr>
<td class="hide-s">{% if t.prio <= 2 %}<span class="pill bad">Do first</span>{% elif t.prio <= 4 %}<span class="pill warn">Due now</span>{% else %}<span class="pill hot">When you can</span>{% endif %}</td>
<td><b>{{ t.action }}</b></td>
<td>{% if t.role=='Application' %}<a href="{{ t.url }}">{{ t.who }}</a> <span class="mute">(application)</span>{% if t.link and t.link.startswith('http') %} <a href="/go/app/{{ t.row }}" target="_blank" style="font-weight:600">posting</a>{% endif %}
{% else %}<a href="{{ t.url }}">{{ t.who }}</a>{% if t.role %}<br><span class="mute">{{ t.role }}</span>{% endif %}{% endif %}
<br>{% if t.curl %}<a href="{{ t.curl }}" style="font-size:13px">{{ t.company }}</a>{% else %}<span style="font-size:13px">{{ t.company }}</span>{% endif %}</td>
<td class="mute">{{ t.reason }}</td></tr>{% endfor %}</table>
{% else %}
<div class="empty">Nothing to chase today.
{% if not people %}You haven't added anyone yet. <a href="/people/new">Add your first person</a>. Start with Tier 1 companies.{% endif %}</div>
{% endif %}
{% if soon %}<h2>Coming up</h2>
<table><tr><th>What</th><th>Who</th><th>When</th></tr>
{% for t in soon %}<tr><td><b>{{ t.action }}</b></td><td><a href="{{ t.url }}">{{ t.who }}</a>, {{ t.company }}</td><td class="mute">{{ t.reason }}</td></tr>{% endfor %}</table>
{% endif %}
{% endblock %}"""

TEMPLATES["waiting.html"] = """{% extends "base.html" %}{% block body %}
<h1>Waiting on</h1>
<p class="sub">Nothing for you to do yet. The last column says when each one turns into a task.</p>
{% if waiting %}
<table><tr><th>Who</th><th>Where it stands</th><th>Waiting</th><th>Turns into a task</th></tr>
{% for w in waiting %}{% set p=w.p %}<tr>
<td><a href="/person/{{ p.row }}">{{ p.name }}</a><br><span class="mute">{{ p.company }}</span></td>
<td>{{ w.label }}</td><td>{{ p.days }} days</td><td>{{ p.due|fmt }}</td></tr>{% endfor %}</table>
{% else %}<div class="empty">No one is waiting on a reply.</div>{% endif %}
<h2>Applications in progress</h2>
{% if waiting_apps %}
<table><tr><th>Role</th><th>Company</th><th>Status</th><th>Applied</th><th>Referred by</th></tr>
{% for a in waiting_apps %}<tr><td>{{ a.role }}</td><td>{{ a.company }}</td><td>{{ a.status }}</td>
<td>{{ a.applied|fmt }}</td><td>{{ a.referred }}</td></tr>{% endfor %}</table>
{% else %}<div class="empty">No applications submitted yet.</div>{% endif %}
{% endblock %}"""

TEMPLATES["companies.html"] = """{% extends "base.html" %}{% block body %}
<h1>Companies</h1>
<p class="sub">Where each company stands, worked out from the People and Applications sheets. Filing data runs to {{ S.data_through }}. <a href="/h1b">Refresh the H-1B numbers</a>.</p>
<div class="filters">
<input id="q" placeholder="Search company" oninput="f()">
<select id="tier" onchange="f()"><option value="">All tiers</option><option>1</option><option>2</option><option>3</option></select>
<select id="stage" onchange="f()"><option value="">All stages</option>
{% for x in ['Not started','Reaching out','In conversation','Applying','Applied','Interviewing','Offer','Went quiet'] %}<option>{{ x }}</option>{% endfor %}</select>
<label class="mute" style="padding:7px 0"><input type="checkbox" id="active" onchange="f()"> Only ones I'm working</label>
</div>
<table id="t"><tr><th>#</th><th>Company</th><th>Tier</th><th class="hide-s">Focus</th><th>Stage</th><th>People</th><th>Apps</th><th>Someone said</th><th class="hide-s">E-Verify</th></tr>
{% for c in cos %}<tr data-n="{{ c.name|lower }}" data-t="{{ c.tier if c.tier else '' }}" data-s="{{ c.stage }}">
<td class="mute">{{ c.rank if c.rank else '' }}</td>
<td><a href="{{ c.url }}">{{ c.name }}</a>{% if c.other %} <span class="pill">not on list</span>{% endif %}</td>
<td>{% if c.tier %}<span class="pill {{ 't1' if c.tier==1 }}">{{ c.tier }}</span>{% endif %}</td>
<td class="hide-s mute">{{ c.data.get('Role focus') or '' }}</td>
<td>{{ c.stage }}</td><td>{{ c.people|length or '' }}</td><td>{{ c.apps|length or '' }}</td>
<td>{% if c.has_answer %}<span class="pill hot">answer on file</span>{% endif %}</td>
<td class="hide-s">{{ c.everify }}</td></tr>{% endfor %}</table>
<script>
function f(){var q=document.getElementById('q').value.toLowerCase(),t=document.getElementById('tier').value,
s=document.getElementById('stage').value,a=document.getElementById('active').checked;
document.querySelectorAll('#t tr[data-n]').forEach(function(r){
var ok=r.dataset.n.indexOf(q)>-1&&(!t||r.dataset.t===t)&&(!s||r.dataset.s===s)&&(!a||r.dataset.s!=='Not started');
r.style.display=ok?'':'none';});}
</script>
{% endblock %}"""

TEMPLATES["company.html"] = """{% extends "base.html" %}{% block body %}
{% set r=c.data %}
<p class="sub"><a href="/companies">Companies</a></p>
<h1>{{ c.name }}</h1>
<p class="sub">{% if c.tier %}Tier {{ c.tier }}, rank {{ c.rank }}. {% endif %}{{ r.get('Role focus') or '' }} &middot; Stage: <b>{{ c.stage }}</b>
{% if r.get('Career page') %} &middot; <a href="{{ r.get('Career page') }}" target="_blank">Career page</a>{% endif %}</p>
<div class="actions"><a class="btn" href="/people/new?company={{ c.name|urlencode }}">Add person here</a>
<a class="btn ghost" href="/applications/new?company={{ c.name|urlencode }}">Add application here</a></div>

<h2>Find people</h2>
<div class="card">
<div class="filters" style="align-items:center"><label class="mute" for="sa">Search as</label>
<input id="sa" value="{{ search_as }}" oninput="relink()" style="min-width:240px">
<span class="mute">Change it if LinkedIn uses a different name (FedEx, not Federal Express).</span></div>
<div class="actions" style="margin:0 0 8px">{% for label, tpl, url, hint in links %}<a class="btn {{ '' if loop.first else 'ghost' }} find" data-tpl="{{ tpl }}" href="{{ url }}" target="_blank" rel="noopener" title="{{ hint }}">{{ label }}</a>{% endfor %}</div>
<span class="mute">Opens LinkedIn in a new tab. Nothing is read or saved from LinkedIn. Hover over a button to see what it searches for.
{% if not has_slug %}<br>For a proper alumni search, add your school's LinkedIn page on the <a href="/settings">Settings</a> page.{% endif %}
When you find someone, <a href="/people/new?company={{ c.name|urlencode }}">add them here</a>.</span>
</div>
<script>function relink(){var n=encodeURIComponent(document.getElementById('sa').value.trim()).replace(/%20/g,'+');
document.querySelectorAll('a.find').forEach(function(a){a.href=a.dataset.tpl.split('__CO__').join(n);});}</script>

<h2>What people have said about sponsorship</h2>
{% if c.has_answer %}
{% if c.answer %}<div class="note">{{ c.answer }}<br><span class="mute">Company-level note. Last checked {{ r.get('Last checked')|fmt or r.get('Last checked') or 'not recorded' }}.</span></div>{% endif %}
{% for p in c.people_answers %}<div class="note">{{ p.answer }}<br><span class="mute">{{ p.name }}{% if p.role %}, {{ p.role }}{% endif %}{% if p.last_contact %}, {{ p.last_contact|fmt }}{% endif %}</span></div>{% endfor %}
{% else %}<div class="empty">No one has told you yet. Ask in your coffee chats, then record who said it and when.</div>{% endif %}
<p class="mute">E-Verify (needed for the STEM OPT extension): {{ c.everify or 'not checked' }}</p>

<h2>People</h2>
{% if c.people %}<table><tr><th>Person</th><th>Stage</th><th>Next</th></tr>
{% for p in c.people %}<tr><td><a href="/person/{{ p.row }}">{{ p.name }}</a><br><span class="mute">{{ p.role }}</span></td>
<td>{{ p.stage }}</td><td>{% if p.state=='act' %}<b>{{ p.action }}</b>{% elif p.state=='done' %}<span class="mute">closed</span>{% else %}<span class="mute">{{ p.action }}</span>{% endif %}</td></tr>{% endfor %}</table>
{% else %}<div class="empty">No one contacted at {{ c.name }} yet.</div>{% endif %}

<h2>Applications</h2>
{% if c.apps %}<table><tr><th>Role</th><th>Status</th><th>Deadline</th><th>Applied</th><th>Referred by</th></tr>
{% for a in c.apps %}<tr><td><a href="/application/{{ a.row }}/edit">{{ a.role }}</a>{% if a.link.startswith('http') %} <a href="/go/app/{{ a.row }}" target="_blank">link</a>{% endif %}</td>
<td>{{ a.status or 'not applied' }}</td><td>{{ a.deadline|fmt }}</td><td>{{ a.applied|fmt }}</td><td>{{ a.referred }}</td></tr>{% endfor %}</table>
{% else %}<div class="empty">No applications logged.</div>{% endif %}

{% if r %}
<h2>What the filings show</h2>
<p class="sub">A signal of intent, not a promise. Certified H-1B filings for product and strategy roles, new hires only, to {{ S.data_through }}. A person's answer outranks all of this.</p>
<div class="grid">
<div class="card"><div class="k">Score</div><div class="v">{{ r.get('Score')|num(1) }}</div></div>
<div class="card"><div class="k">New-hire filings</div><div class="v">{{ r.get('Role filings, new hire')|num }}</div></div>
<div class="card"><div class="k">All role filings</div><div class="v">{{ r.get('Role filings, all types')|num }}</div></div>
<div class="card"><div class="k">New-hire share</div><div class="v">{{ ((r.get('Role filings, new hire') or 0) / (r.get('Role filings, all types') or 1))|pct }}</div></div>
<div class="card"><div class="k">Wage level III or IV</div><div class="v">{{ r.get('Wage level III or IV share')|pct }}</div></div>
<div class="card"><div class="k">Median salary</div><div class="v">${{ r.get('Median offered salary (USD)')|num }}</div></div>
</div>
<div class="card" style="margin-top:12px">
Product manager {{ r.get('Product manager (new hire)')|num }} &middot; Technical program manager {{ r.get('Technical program manager (new hire)')|num }} &middot;
Strategy {{ r.get('Strategy (new hire)')|num }} &middot; Product marketing {{ r.get('Product marketing (new hire)')|num }} &middot; Product ops {{ r.get('Product ops (new hire)')|num }}
<br><span class="mute">Top states: {{ r.get('Top states') or '' }}. Top cities: {{ r.get('Top cities') or '' }}.
Entry-level titles {{ r.get('Entry-level titles')|num }}, senior-level titles {{ r.get('Senior-level titles')|num }}.</span>
{% if r.get('Flags') %}<br><span class="warn">{{ r.get('Flags') }}</span>{% endif %}</div>
{% endif %}
{% if r.get('Notes') %}<h2>Notes</h2><div class="card">{{ r.get('Notes') }}</div>{% endif %}
{% endblock %}"""

TEMPLATES["person.html"] = """{% extends "base.html" %}{% block body %}
<a class="back" href="/people">&larr; Back to People</a>
<p class="sub">{% if co %}<a href="{{ co.url }}">{{ p.company }}</a>{% else %}{{ p.company }}{% endif %}</p>
<h1>{{ p.name }}</h1>
<p class="sub">{{ p.role }}{% if p.link.startswith('http') %} &middot; <a href="{{ p.link }}" target="_blank">LinkedIn</a>{% endif %}</p>
<div class="actions"><a class="btn" href="/person/{{ p.row }}/edit">Edit</a></div>
<div class="grid">
<div class="card"><div class="k">Stage</div><div class="v">{{ p.stage or 'none' }}</div></div>
<div class="card"><div class="k">Since</div><div class="v">{{ p.since|fmt or 'no date' }}</div></div>
<div class="card"><div class="k">Last contact</div><div class="v">{{ p.last_contact|fmt or 'none' }}</div></div>
<div class="card"><div class="k">Referral offered</div><div class="v">{{ p.referral or 'no' }}</div></div>
</div>
<h2>What to do</h2>
{% if p.state=='done' %}<div class="empty">Closed. Nothing to do.</div>
{% else %}<div class="card"><b>{{ p.action }}</b><br><span class="mute">{{ p.reason }}</span></div>{% endif %}
<h2>Sponsorship</h2>
{% if p.answer %}<div class="note">{{ p.answer }}<br><span class="mute">{{ p.name }}{% if p.last_contact %}, {{ p.last_contact|fmt }}{% endif %}</span></div>
{% else %}<div class="empty">They haven't said anything about sponsorship yet.</div>{% endif %}
{% if p.found %}<p class="mute">Found through: {{ p.found }}</p>{% endif %}
{% if p.notes %}<h2>Notes</h2><div class="card">{{ p.notes }}</div>{% endif %}
<p class="mute">Row {{ p.row }} of the People sheet.</p>
{% endblock %}"""


TEMPLATES["people.html"] = """{% extends "base.html" %}{% block body %}
<h1>People</h1>
<div class="actions"><a class="btn" href="/people/new">Add person</a></div>
{% if people %}
<div class="filters"><input id="q" placeholder="Search name or company" oninput="f()"></div>
{% set extra = people|map(attribute='stage')|reject('in', STAGES)|unique|list %}
<div class="chips" id="chips">{% for s in STAGES + extra %}{% set n = people|selectattr('stage', 'equalto', s)|list|length %}<button type="button" class="chip{{ ' on' if s == 'message sent' }}" data-v="{{ s }}">{{ s or '(no stage)' }}<span>{{ n }}</span></button>{% endfor %}
<button type="button" class="chip plain" data-all="1">All</button><button type="button" class="chip plain" data-clear="1">Clear</button></div>
<p class="mute shown" id="shown"></p>
<table id="t"><tr><th>Person</th><th>Company</th><th>Stage</th><th class="hide-s">Since</th><th>Next</th><th></th></tr>
{% for p in people|sort(attribute='company') %}<tr data-n="{{ (p.name ~ ' ' ~ p.company)|lower }}" data-s="{{ p.stage }}">
<td><a href="/person/{{ p.row }}">{{ p.name }}</a><br><span class="mute">{{ p.role }}</span></td>
<td>{{ p.company }}</td><td>{{ p.stage }}</td><td class="hide-s">{{ p.since|fmt }}</td>
<td>{% if p.state=='act' %}<b>{{ p.action }}</b>{% elif p.state=='done' %}<span class="mute">closed</span>{% else %}<span class="mute">{{ p.action }}</span>{% endif %}</td>
<td><a class="btn small ghost" href="/person/{{ p.row }}/edit">Edit</a></td></tr>{% endfor %}</table>
<script>(function(){var box=document.getElementById('chips'),chips=box.querySelectorAll('.chip[data-v]'),KEY='people';
function f(){var on=[].filter.call(chips,function(c){return c.classList.contains('on');}).map(function(c){return c.dataset.v;}),n=0,tot=0;
document.querySelectorAll('#t tr[data-s]').forEach(function(r){tot++;var ok=on.indexOf(r.dataset.s)>-1&&r.dataset.n.indexOf(document.getElementById('q').value.toLowerCase())>-1;r.style.display=ok?'':'none';if(ok)n++;});
document.getElementById('shown').textContent='Showing '+n+' of '+tot+'.'+(n?'':' Click a button above to show more.');}
box.addEventListener('click',function(e){var b=e.target.closest('.chip');if(!b)return;
if(b.dataset.all)chips.forEach(function(c){c.classList.add('on');});else if(b.dataset.clear)chips.forEach(function(c){c.classList.remove('on');});else b.classList.toggle('on');f();});
window.f=f;f();})();</script>
{% else %}<div class="empty">No one yet.</div>{% endif %}
{% endblock %}"""

TEMPLATES["_company_list.html"] = """<datalist id="companies">{% for n in company_names %}<option value="{{ n }}">{% endfor %}</datalist>"""

TEMPLATES["person_form.html"] = """{% extends "base.html" %}{% block body %}
<a class="back" href="/people">&larr; Back to People</a>
<h1>{{ 'Edit ' ~ v['Person'] if row else 'Add a person' }}</h1>
<p class="sub">Saves straight to the People sheet in tracker.xlsx. Close the file in Excel first.</p>
{% if errors %}<div class="errors">{% for e in errors %}{{ e }}<br>{% endfor %}</div>{% endif %}
<form class="f" method="post" action="/people/save">
<input type="hidden" name="_token" value="{{ TOKEN }}">
{% if row %}<input type="hidden" name="_row" value="{{ row }}">
<input type="hidden" name="_orig_company" value="{{ orig['Company'] }}"><input type="hidden" name="_orig_person" value="{{ orig['Person'] }}">{% endif %}
<label>Company<input name="Company" list="companies" value="{{ v['Company'] }}" required></label>
<label>Person<input name="Person" value="{{ v['Person'] }}" required></label>
<label>Role<input name="Role" value="{{ v['Role'] }}"></label>
<label>How found<input name="How found" value="{{ v['How found'] }}" placeholder="Alumni search, referral, event"></label>
<label class="wide">LinkedIn link<input name="LinkedIn link" value="{{ v['LinkedIn link'] }}" placeholder="https://www.linkedin.com/in/..."></label>
<label>Stage<select name="Stage" id="stage" data-was="{{ v['Stage'] }}">{% for s in STAGES %}<option {{ 'selected' if s==v['Stage'] }}>{{ s }}</option>{% endfor %}</select></label>
<label>Stage date<span class="row"><input type="date" name="Stage date" id="stagedate" value="{{ v['Stage date'] }}"><button type="button" class="btn small ghost" onclick="td('stagedate')">Today</button></span></label>
<label>Last contact<span class="row"><input type="date" name="Last contact" id="lastc" value="{{ v['Last contact'] }}"><button type="button" class="btn small ghost" onclick="td('lastc')">Today</button></span></label>
<label>Chat date<input type="date" name="Chat date" value="{{ v['Chat date'] }}"></label>
<label>Referral offered<select name="Referral offered">{% for o in ['', 'Yes', 'No'] %}<option {{ 'selected' if o==v['Referral offered'] }}>{{ o }}</option>{% endfor %}</select></label>
<label class="wide">Sponsorship answer (what they said, in their words)<textarea name="Sponsorship answer">{{ v['Sponsorship answer'] }}</textarea></label>
<label class="wide">Notes<textarea name="Notes">{{ v['Notes'] }}</textarea></label>
<div><button class="btn" type="submit">Save</button> <a class="btn ghost" href="/people">Cancel</a></div>
</form>
{% include "_company_list.html" %}
<p class="mute">Changing the stage sets the stage date to today. Change it back if the step happened earlier.</p>
<script>
function td(id){document.getElementById(id).value=new Date().toLocaleDateString('en-CA');}
document.getElementById('stage').addEventListener('change',function(){if(this.value!==this.dataset.was){td('stagedate');}});
</script>
{% endblock %}"""

TEMPLATES["applications.html"] = """{% extends "base.html" %}{% block body %}
<h1>Applications</h1>
<div class="actions"><a class="btn" href="/applications/new">Add application</a></div>
<div class="counts">
{% for st in STATUSES %}<div class="card"><div class="k">{{ st }}</div><div class="v">{{ counts[st] }}</div></div>{% endfor %}
</div>
<p class="sub">{{ n_responded }} of {{ n_submitted }} submitted applications got a response{% if n_submitted %} ({{ (100 * n_responded / n_submitted)|round|int }}%){% endif %}.
A response means screening, interviewing, offer or rejected.{% if other_status %} <span class="warn">{{ other_status|length }} row(s) have a status that isn't on the list.</span>{% endif %}</p>
{% if asks %}<div class="card" id="ask" style="border-color:var(--accent)">
<b>Did you apply?</b> <span class="mute">Roles you opened from the tracker. Each one drops off after 14 days, or when the posting closes.</span>
<table style="margin-top:8px;border:0">
{% for c in asks %}<tr><td>{{ c.role }}<br><span class="mute">{{ c.company }}</span></td>
<td class="mute hide-s">Opened {{ c.ago }} from {{ c.source }}{% if c.state == 'not_yet' %}<br>You said not yet{% endif %}</td>
<td style="white-space:nowrap"><form method="post" action="/clicks/answer" style="margin:0;display:flex;gap:6px;flex-wrap:wrap">
<input type="hidden" name="_token" value="{{ TOKEN }}"><input type="hidden" name="key" value="{{ c.key }}"><input type="hidden" name="back" value="/applications">
<button class="btn small" name="answer" value="yes">Yes, applied</button>{% if c.state != 'not_yet' %}<button class="btn small ghost" name="answer" value="not_yet">Not yet</button>{% endif %}<button class="btn small ghost" name="answer" value="no">Not for me</button>
<a class="btn small ghost" href="{{ c.url }}" target="_blank" rel="noopener">Open posting</a></form></td></tr>{% endfor %}
</table></div>{% endif %}
{% if cv_stats['Tailored CV'].submitted or cv_stats['Standard CV'].submitted %}
<div class="grid" style="margin-bottom:12px">
{% for name, st in cv_stats.items() %}<div class="card"><div class="k">{{ name }}</div><div class="v">{{ st.responded }} of {{ st.submitted }}</div><span class="mute">submitted got a response{% if st.submitted %} ({{ (100 * st.responded / st.submitted)|round|int }}%){% endif %}</span></div>{% endfor %}
{% for lv, st in level_stats.items() %}{% if st.submitted %}<div class="card"><div class="k">{{ lv }}</div><div class="v">{{ st.responded }} of {{ st.submitted }}</div><span class="mute">got a response</span></div>{% endif %}{% endfor %}
</div>
<p class="mute">Tailored means the application has a "CV used" file name. The numbers become useful after 15 or 20 applications in each group.</p>{% endif %}
{% if apps_sorted %}
<div class="filters">
<select id="co" onchange="f()"><option value="">All companies</option>{% for n in apps_sorted|map(attribute='company')|unique|sort %}<option>{{ n }}</option>{% endfor %}</select>
</div>
{% set extra = apps_sorted|map(attribute='status')|reject('in', STATUSES)|unique|list %}
<div class="chips" id="chips">{% for s in STATUSES + extra %}{% set n = apps_sorted|selectattr('status', 'equalto', s)|list|length %}<button type="button" class="chip{{ ' on' if s == 'applied' }}" data-v="{{ s }}">{{ s or '(no status)' }}<span>{{ n }}</span></button>{% endfor %}
<button type="button" class="chip plain" data-all="1">All</button><button type="button" class="chip plain" data-clear="1">Clear</button></div>
<p class="mute shown" id="shown"></p>
<table id="t"><tr><th>Company</th><th>Role</th><th>Status</th><th class="hide-s">Applied</th><th>Deadline</th><th>Next step</th><th class="hide-s">Referred by</th><th>Flags</th><th></th></tr>
{% for a in apps_sorted %}<tr data-s="{{ a.status }}" data-c="{{ a.company }}">
<td>{% if a.curl %}<a href="{{ a.curl }}">{{ a.company }}</a>{% else %}{{ a.company }}{% endif %}</td>
<td>{% if role_by_row.get(a.row) %}<a href="/jobs/role/{{ role_by_row[a.row]|urlencode }}?back=/applications" title="Match, CVs and the description">{{ a.role }}</a>{% else %}{{ a.role }}{% endif %}{% if a.link.startswith('http') %} <a href="/go/app/{{ a.row }}" target="_blank">posting</a>{% endif %}
{% if a.cv_used %}<br><span class="pill hot" title="{{ a.cv_used }}">tailored CV</span>{% endif %}{% if a.match_level %} <span class="pill">{{ a.match_level }}</span>{% endif %}</td>
<td>{{ a.status }}</td>
<td class="hide-s">{{ a.applied|fmt }}</td>
<td>{{ a.deadline|fmt }}</td>
<td>{{ a.next_date|fmt }}{% if a.next %}<br><span class="mute">{{ a.next }}</span>{% endif %}</td>
<td class="hide-s">{{ a.referred }}</td>
<td>{% if a.deadline_flag %}<span class="pill warn">{% if a.days_left < 0 %}deadline passed{% else %}deadline in {{ a.days_left }}d{% endif %}</span> {% endif %}
{% if a.next_due %}<span class="pill warn">next step due</span> {% endif %}
{% if a.no_contact %}<span class="pill">spoken to no one</span>{% endif %}</td>
<td><a class="btn small ghost" href="/application/{{ a.row }}/edit">Edit</a></td></tr>{% endfor %}</table>
<script>(function(){var box=document.getElementById('chips'),chips=box.querySelectorAll('.chip[data-v]'),KEY='apps';
function f(){var on=[].filter.call(chips,function(c){return c.classList.contains('on');}).map(function(c){return c.dataset.v;}),n=0,tot=0;
document.querySelectorAll('#t tr[data-s]').forEach(function(r){tot++;var ok=on.indexOf(r.dataset.s)>-1&&(!document.getElementById('co').value||r.dataset.c===document.getElementById('co').value);r.style.display=ok?'':'none';if(ok)n++;});
document.getElementById('shown').textContent='Showing '+n+' of '+tot+'.'+(n?'':' Click a button above to show more.');}
box.addEventListener('click',function(e){var b=e.target.closest('.chip');if(!b)return;
if(b.dataset.all)chips.forEach(function(c){c.classList.add('on');});else if(b.dataset.clear)chips.forEach(function(c){c.classList.remove('on');});else b.classList.toggle('on');f();});
window.f=f;f();})();</script>
<p class="mute">Most urgent first: passed and near deadlines, next steps due, next steps this week, then companies where you've spoken to no one. Rejected and withdrawn sit at the bottom.</p>
{% else %}<div class="empty">No applications yet.</div>{% endif %}
{% endblock %}"""

TEMPLATES["application_form.html"] = """{% extends "base.html" %}{% block body %}
<a class="back" href="/applications">&larr; Back to Applications</a>
<h1>{{ 'Edit application' if row else 'Add an application' }}</h1>
<p class="sub">Saves straight to the Applications sheet in tracker.xlsx. Close the file in Excel first.</p>
{% if errors %}<div class="errors">{% for e in errors %}{{ e }}<br>{% endfor %}</div>{% endif %}
<form class="f" method="post" action="/applications/save">
<input type="hidden" name="_token" value="{{ TOKEN }}">
{% if row %}<input type="hidden" name="_row" value="{{ row }}">
<input type="hidden" name="_orig_company" value="{{ orig['Company'] }}"><input type="hidden" name="_orig_role" value="{{ orig['Role'] }}">{% endif %}
<label>Company<input name="Company" list="companies" value="{{ v['Company'] }}" required></label>
<label>Role<input name="Role" value="{{ v['Role'] }}" required></label>
<label class="wide">Link to the posting<input name="Link" value="{{ v['Link'] }}" placeholder="https://..."></label>
<label>Focus<select name="Focus">{% for o in ['', 'Product', 'Strategy'] %}<option {{ 'selected' if o==v['Focus'] }}>{{ o }}</option>{% endfor %}</select></label>
<label>Status<select name="Status" id="status">{% for s in STATUSES %}<option {{ 'selected' if s==v['Status'] }}>{{ s }}</option>{% endfor %}</select></label>
<label>Deadline<input type="date" name="Deadline" value="{{ v['Deadline'] }}"></label>
<label>Date applied<span class="row"><input type="date" name="Date applied" id="applied" value="{{ v['Date applied'] }}"><button type="button" class="btn small ghost" onclick="td('applied')">Today</button></span></label>
<label>Referred by<input name="Referred by" value="{{ v['Referred by'] }}"></label>
<label>Next step date<input type="date" name="Next step date" value="{{ v['Next step date'] }}"></label>
<label class="wide">Next step<input name="Next step" value="{{ v['Next step'] }}" placeholder="Follow up with recruiter"></label>
<label>CV used<input name="CV used" value="{{ v['CV used'] }}" placeholder="Blank means your standard CV"></label>
<label>Match level<select name="Match level">{% for o in ['', 'Strong match', 'Small tweaks', 'Major tweaks', 'Weak match'] %}<option {{ 'selected' if o==v['Match level'] }}>{{ o }}</option>{% endfor %}</select></label>
<label class="wide">Notes<textarea name="Notes">{{ v['Notes'] }}</textarea></label>
<div><button class="btn" type="submit">Save</button> <a class="btn ghost" href="/applications">Cancel</a></div>
</form>
{% include "_company_list.html" %}
<p class="mute">To take an application off your list, set it to withdrawn. The site never deletes rows.</p>
<script>
function td(id){document.getElementById(id).value=new Date().toLocaleDateString('en-CA');}
document.getElementById('status').addEventListener('change',function(){var a=document.getElementById('applied');if(this.value!=='interested'&&this.value!=='withdrawn'&&!a.value){td('applied');}});
</script>
{% endblock %}"""


TEMPLATES["settings.html"] = """{% extends "base.html" %}{% block body %}
<h1>Settings</h1>
<p class="sub">Saved on the Settings sheet in tracker.xlsx. Close the file in Excel first.</p>
{% if errors %}<div class="errors">{% for e in errors %}{{ e }}<br>{% endfor %}</div>{% endif %}
<form class="f" method="post" action="/settings">
<input type="hidden" name="_token" value="{{ TOKEN }}">
<h2 style="grid-column:1/-1;margin:0">Your school</h2>
<label>{{ labels['school_name'] }}<input name="school_name" value="{{ vals['school_name'] }}" placeholder="e.g. Kellogg School of Management"></label>
<label>{{ labels['school_linkedin_url'] }}<input name="school_linkedin_url" value="{{ vals['school_linkedin_url'] }}" placeholder="https://www.linkedin.com/school/..."></label>
<p class="mute" style="grid-column:1/-1;margin:0">To find the address, search for your school on LinkedIn, open its page, and copy the address from the browser bar. It should contain /school/.</p>
<h2 style="grid-column:1/-1;margin:8px 0 0">Follow-up rules</h2>
{% for k in ['request_nudge_days','accepted_message_days','message_followup_days','second_silence_days','thankyou_due_days','checkback_days','deadline_warning_days','jobs_max_age_days'] %}
<label>{{ labels[k] }}<input type="number" min="0" name="{{ k }}" value="{{ vals[k] }}"></label>{% endfor %}
<div style="grid-column:1/-1"><button class="btn" type="submit">Save</button></div>
</form>
<p class="mute">Filing data runs to {{ vals['data_through'] }}. That date updates when you <a href="/h1b">refresh the H-1B numbers</a>.</p>

<h2 id="email">Daily email</h2>
<div class="card">
<b>Status:</b>
{% if email.schedule == 'on' %}<span class="pill hot">on</span> Goes at {{ vals['digest_time'] }} each day, or when the laptop next wakes after that.
{% elif email.schedule == 'off' %}<span class="pill">off</span>
{% else %}<span class="pill">can't tell</span> (this only works on Windows){% endif %}
{% if email.last_result %}<br><span class="mute">Last attempt {{ email.last_try }}: {{ email.last_result }}</span>{% endif %}
{% if not email.has_keyring %}<br><span class="warn">One helper package is missing. Close this window and double-click start.bat again.</span>{% endif %}
</div>
<form class="f" method="post" action="/settings/email">
<input type="hidden" name="_token" value="{{ TOKEN }}">
<label>{{ labels['email_from'] }}<input name="email_from" value="{{ vals['email_from'] }}" placeholder="you@gmail.com"></label>
<label>{{ labels['email_to'] }}<input name="email_to" value="{{ vals['email_to'] }}"></label>
<label>Google app password {% if email.has_password %}<span class="pill hot">saved</span>{% endif %}
<input name="app_password" type="password" autocomplete="new-password" placeholder="{{ 'Leave blank to keep the saved one' if email.has_password else '16 letters from Google' }}"></label>
<label>{{ labels['digest_time'] }}<input name="digest_time" value="{{ vals['digest_time'] }}" placeholder="07:30"></label>
<p class="mute" style="grid-column:1/-1;margin:0">The app password is stored in Windows Credential Manager on this laptop, not in tracker.xlsx or OneDrive.</p>
<div style="grid-column:1/-1"><button class="btn" type="submit">Save email settings</button></div>
</form>
<div class="actions" style="margin-top:12px">
<form method="post" action="/settings/email/test" style="margin:0"><input type="hidden" name="_token" value="{{ TOKEN }}"><button class="btn ghost">Send a test email now</button></form>
{% if email.schedule == 'on' %}<form method="post" action="/settings/email/schedule" style="margin:0"><input type="hidden" name="_token" value="{{ TOKEN }}"><input type="hidden" name="on" value="0"><button class="btn ghost">Turn daily email off</button></form>
{% else %}<form method="post" action="/settings/email/schedule" style="margin:0"><input type="hidden" name="_token" value="{{ TOKEN }}"><input type="hidden" name="on" value="1"><button class="btn">Turn daily email on</button></form>{% endif %}
</div>
<p class="mute">The daily email doesn't need the site running. Windows starts it by itself. It needs the laptop to be on or wake up, and you to be signed in to Windows. If the laptop was asleep at send time, the email goes when it wakes. It sends once a day at most, and refreshes the job watcher first.</p>
{% endblock %}"""


TEMPLATES["_jobs_tabs.html"] = """<h1>Jobs</h1>
<div class="tabs">
<a href="/jobs" class="{{ 'on' if tab == 'review' }}">To review <span>{{ tabs.review|length }}</span></a>
<a href="/jobs/pasted" class="{{ 'on' if tab == 'pasted' }}">Pasted <span>{{ tabs.pasted|length }}</span></a>
<a href="/jobs/hidden" class="{{ 'on' if tab == 'hidden' }}">Hidden <span>{{ tabs.hidden|length }}</span></a>
<a href="/jobs/coverage" class="{{ 'on' if tab == 'coverage' }}">Coverage</a>
</div>"""

TEMPLATES["jobs.html"] = """{% extends "base.html" %}{% block body %}
{% if run.running %}<meta http-equiv="refresh" content="3">{% endif %}
{% include "_jobs_tabs.html" %}
<div class="actions" style="align-items:center">
{% if tab == 'pasted' %}<a class="btn" href="/jobs/paste">Paste a job</a>{% endif %}
{% if run.running %}<span class="btn ghost">Checking {{ run.done }} of {{ run.total }}{% if run.current %}: {{ run.current }}{% endif %}...</span>
{% else %}<form method="post" action="/jobs/check" style="margin:0"><input type="hidden" name="_token" value="{{ TOKEN }}"><button class="btn {{ 'ghost' if tab == 'pasted' }}">Check now</button></form>{% endif %}
<span class="mute" style="font-size:13px">{% if store.last_run.finished %}Last checked {{ store.last_run.finished[:10]|fmt }}, {{ store.last_run.finished[11:16] }}{% else %}Not checked yet{% endif %}</span>
</div>
{% if mstat.state == 'loading' %}<p class="mute" style="margin:-6px 0 12px;font-size:13px">{{ mstat.note }} Match levels use keywords until it's ready.</p>
{% elif mstat.state == 'working' %}<p class="mute" style="margin:-6px 0 12px;font-size:13px">Meaning matching is reading roles: {{ mstat.done }} of {{ mstat.total }}. Roles not read yet are matched on keywords. Refresh to update.</p>
{% elif mstat.state == 'unavailable' %}<p class="mute" style="margin:-6px 0 12px;font-size:13px">{{ mstat.note }}</p>{% endif %}

{% if tab == 'review' %}
<p class="mute" style="margin:0 0 10px">Roles to decide on: Add sends one to Applications, Hide puts it in the Hidden tab. Either way it leaves this list.
{% if tabs.in_apps %}{{ tabs.in_apps }} role{{ 's' if tabs.in_apps != 1 }} already in <a href="/applications">Applications</a>.{% endif %}</p>
{% elif tab == 'pasted' %}
<p class="mute" style="margin:0 0 10px">Roles you pasted in because the watcher doesn't capture them. They stay until you add or hide them.</p>
{% else %}
<p class="mute" style="margin:0 0 10px">Roles you hid. Unhide sends one back to To review (or Pasted).</p>
{% endif %}
{% for p in store.cv_problems %}<p class="warn">{{ p }}</p>{% endfor %}

{% if rows %}
<div class="filters">
<input id="q" placeholder="Search titles" oninput="f()">
<select id="fo" onchange="f()"><option value="">Product and strategy</option><option>Product</option><option>Strategy</option></select>
<select id="co" onchange="f()"><option value="">All companies</option>{% for n in rows|map(attribute='company')|unique|sort %}<option>{{ n }}</option>{% endfor %}</select>
<details class="more"><summary class="mute">More filters</summary><div class="filters" style="margin:8px 0 0">
<select id="wh" onchange="f()"><option value="usu">US and unclear</option><option value="US">US only</option><option value="">Everywhere</option></select>
<select id="ind" onchange="f()"><option value="">All industries</option>{% for n in industry_names %}<option>{{ n }}</option>{% endfor %}</select>
<input type="checkbox" id="ns" checked hidden><!-- roles that say no sponsorship are left out by the site (31 Oct 2026); only ones you pasted or applied to still show, labelled -->
</div></details>
</div>
{% if tab == 'review' %}
{% for g in groups %}<details class="grp" {{ 'open' if g.open }}><summary><b>{{ g.name }}</b> <span class="mute cnt">{{ g.rows|length }}</span></summary>
{% set rows = g.rows %}{% set pill = False %}{% include "_jobs_table.html" %}</details>{% endfor %}
{% else %}{% set pill = True %}{% include "_jobs_table.html" %}{% endif %}
<p class="mute" id="none" hidden>No roles match these filters.</p>
<script>
var KEYS = ['fo', 'co', 'wh', 'ind', 'ns'];
function el(k) { return document.getElementById(k); }
function f() {
  var fo = el('fo').value, co = el('co').value, wh = el('wh').value, q = el('q').value.toLowerCase(),
      ind = el('ind').value, ns = el('ns').checked, shown = 0;
  document.querySelectorAll('table.filt tr[data-c]').forEach(function (r) {
    var w = r.dataset.w;
    var ok = (!fo || r.dataset.f === fo) && (!co || r.dataset.c === co) && r.dataset.t.indexOf(q) > -1
      && (!ind || r.dataset.i.indexOf('|' + ind + '|') > -1) && (ns || r.dataset.ns !== '1')
      && (wh === '' || (wh === 'US' && w === 'US') || (wh === 'usu' && w !== 'Not US'));
    r.style.display = ok ? '' : 'none';
    if (ok) shown++;
  });
  document.querySelectorAll('details.grp').forEach(function (g) {
    var n = 0;
    g.querySelectorAll('tr[data-c]').forEach(function (r) { if (r.style.display !== 'none') n++; });
    g.querySelector('.cnt').textContent = n;
    g.style.display = n ? '' : 'none';
  });
  el('none').hidden = shown > 0;
  try {
    var s = {};
    KEYS.forEach(function (k) { s[k] = el(k).type === 'checkbox' ? el(k).checked : el(k).value; });
    localStorage.setItem('jobFilters', JSON.stringify(s));
  } catch (e) {}
}
document.addEventListener('DOMContentLoaded', function () {
  try {
    var s = JSON.parse(localStorage.getItem('jobFilters') || '{}');
    KEYS.forEach(function (k) {
      if (!(k in s)) return;
      if (el(k).type === 'checkbox') el(k).checked = s[k];
      else if ([].some.call(el(k).options, function (o) { return o.value === s[k]; })) el(k).value = s[k];
    });
  } catch (e) {}
  f();
});
</script>
{% else %}
<div class="empty">{% if tab == 'review' %}{% if not store.last_run.finished %}Press Check now to start.{% else %}Nothing left to review. New roles appear here after each check.{% endif %}
{% elif tab == 'pasted' %}Nothing pasted yet. Use Paste a job for a role the watcher doesn't capture, such as a referral or a LinkedIn post.
{% else %}Nothing hidden.{% endif %}</div>
{% endif %}
{% if tab == 'review' and tabs.old %}<p class="mute">{{ tabs.old }} open role{{ 's' if tabs.old != 1 }} posted more than {{ S.jobs_max_age_days }} days ago left out. Change the number of days on <a href="/settings">Settings</a>.</p>{% endif %}
<details class="how"><summary class="mute">How matching works</summary><div class="card" style="margin-top:8px;font-size:14px">
<p style="margin-top:0">Roles come from your Tier 1 companies' job feeds: Greenhouse, Lever, Ashby, Amazon's job search, the first page of Google's, and Workday career sites. <a href="/jobs/coverage">Coverage</a> shows which companies it can't read.</p>
<p>It keeps product manager, owner, lead and director, APM, GPM, product operations, product marketing, and corporate or business strategy roles. Technical program manager, engineer, designer, scientist and intern titles are left out, as are sales, marketing and data strategy roles.</p>
<p>Match levels compare the skills each description asks for with your CVs{% if store.cv_kinds %} ({{ store.cv_kinds|join(', ') }}){% endif %}: the CV for that kind of role, and your long CV. Skills the description requires count for more than ones it prefers. It's word matching on your laptop, so treat it as a sorting aid, not a verdict.</p>
<p style="margin-bottom:0">Industry comes from the description: it either asks for that experience or only mentions it often. Roles whose description says no sponsorship, or that a US citizen is required, are left out unless you tick the box under More filters. US status is a guess from the location text.</p></div></details>
{% endblock %}"""

TEMPLATES["_jobs_table.html"] = """<table class="filt jobs"><tr><th>Role</th><th>Company</th><th class="hide-s">Location</th><th class="hide-s">Posted</th><th></th></tr>
{% for j in rows %}<tr data-c="{{ j.company }}" data-f="{{ j.focus }}" data-w="{{ j.where }}" data-t="{{ j.title|lower }}" data-i="|{{ j.ind_names|join('|') }}|" data-ns="{{ '1' if j.no_sponsor else '0' }}">
<td>{% if pill and j.match %}<span class="pill {{ ['hot', 't1', 'warn', ''][j.match.tier] }}">{{ j.match.tier_name }}</span> {% endif %}<a href="/jobs/role/{{ j.uid|urlencode }}?back={{ back|urlencode }}"><b>{{ j.title }}</b></a>
<span class="mute" style="font-size:13px">{{ j.label }}</span>{% if j.is_new %} <span class="pill hot">new</span>{% endif %}{% if j.cv_made %} <span class="pill hot">CV made</span>{% endif %}
{% if j.no_sponsor %} <span class="pill warn">says no sponsorship</span>{% elif j.sponsor == 'yes' %} <span class="pill hot">says it will consider sponsorship</span>{% endif %}{% if j.clearance %} <span class="pill warn">clearance</span>{% endif %}{% if j.cs_degree %} <span class="pill warn">CS degree required</span>{% endif %}{% if j.years and j.years > 8 %} <span class="pill">asks {{ j.years }}+ yrs</span>{% endif %}{% if j.onsite %} <span class="pill">on-site</span>{% endif %}</td>
<td>{{ j.company }}</td>
<td class="hide-s">{{ j.location or '' }}{% if j.where == 'Not US' %} <span class="warn">(not US)</span>{% endif %}</td>
<td class="hide-s" style="white-space:nowrap">{% if j.pasted %}<span class="mute">pasted {{ j.first_seen|fmt }}</span>{% elif j.posted_d %}{{ j.posted_d|fmt }}{% elif j.nodate %}<span class="mute">seen {{ j.first_seen|fmt }}</span>{% endif %}</td>
<td class="act">{% if not j.dismissed %}<form method="post" action="/jobs/add" style="display:inline"><input type="hidden" name="_token" value="{{ TOKEN }}"><input type="hidden" name="uid" value="{{ j.uid }}"><input type="hidden" name="back" value="{{ back }}"><button class="btn small" title="Add to Applications as interested">Add</button></form>{% endif %}
<form method="post" action="/jobs/hide" style="display:inline"><input type="hidden" name="_token" value="{{ TOKEN }}"><input type="hidden" name="uid" value="{{ j.uid }}"><input type="hidden" name="hide" value="{{ '0' if j.dismissed else '1' }}"><input type="hidden" name="back" value="{{ back }}"><button class="btn small ghost">{{ 'Unhide' if j.dismissed else 'Hide' }}</button></form></td></tr>{% endfor %}</table>"""

TEMPLATES["job_role.html"] = """{% extends "base.html" %}{% block body %}
<a class="back" href="{{ back }}">&larr; Back to {{ 'Pasted' if back.startswith('/jobs/pasted') else 'Hidden' if back.startswith('/jobs/hidden') else 'Applications' if back.startswith('/applications') else 'Jobs' }}</a>
<h1>{{ j.title }}</h1>
<p class="sub">{% if j.curl %}<a href="{{ j.curl }}">{{ j.company }}</a>{% else %}{{ j.company }}{% endif %}{% if j.location %} &middot; {{ j.location }}{% endif %}
&middot; {{ j.label }} &middot; {% if j.pasted %}pasted {{ j.first_seen|fmt }}{% elif j.posted_d %}posted {{ j.posted_d|fmt }}{% else %}first seen {{ j.first_seen|fmt }}{% endif %}</p>
<p style="margin:-8px 0 12px">{% if j.match %}<span class="pill {{ ['hot', 't1', 'warn', ''][j.match.tier] }}">{{ j.match.tier_name }}</span>{% endif %}
{% if j.is_new %} <span class="pill hot">new</span>{% endif %}{% if j.pasted %} <span class="pill">pasted</span>{% endif %}{% if j.dismissed %} <span class="pill">hidden</span>{% endif %}{% if not j.open %} <span class="pill warn">the watcher no longer sees this posting</span>{% endif %}
{% if j.no_sponsor %} <span class="pill warn">says no sponsorship</span>{% elif j.sponsor == 'yes' %} <span class="pill hot">says it will consider sponsorship</span>{% endif %}{% if j.clearance %} <span class="pill warn">clearance</span>{% endif %}{% if j.cs_degree %} <span class="pill warn">CS degree required</span>{% endif %}{% if j.years %} <span class="pill">asks {{ j.years }}+ yrs</span>{% endif %}{% if j.onsite %} <span class="pill">on-site</span>{% endif %}</p>

<div class="actions">
{% if j.url %}<a class="btn" href="/go/job/{{ j.uid|urlencode }}" target="_blank" rel="noopener" title="When you come back, the tracker asks whether you applied">Open posting</a>{% endif %}
{% if desc %}<form method="post" action="/jobs/cv" style="margin:0"><input type="hidden" name="_token" value="{{ TOKEN }}"><input type="hidden" name="uid" value="{{ j.uid }}"><input type="hidden" name="back" value="{{ here }}"><button class="btn ghost">{{ 'Generate CV again' if versions else 'Generate CV' }}</button></form>{% endif %}
{% if app_row %}<a class="btn ghost" href="/application/{{ app_row.row }}/edit">In Applications: {{ app_row.status }}</a>
{% else %}<form method="post" action="/jobs/add" style="margin:0"><input type="hidden" name="_token" value="{{ TOKEN }}"><input type="hidden" name="uid" value="{{ j.uid }}"><input type="hidden" name="back" value="{{ here }}"><button class="btn ghost">Add to Applications</button></form>{% endif %}
{% if j.pasted %}<a class="btn ghost" href="/jobs/paste/{{ j.uid|urlencode }}/edit">Edit</a>{% endif %}
{% if not app_row %}<form method="post" action="/jobs/hide" style="margin:0"><input type="hidden" name="_token" value="{{ TOKEN }}"><input type="hidden" name="uid" value="{{ j.uid }}"><input type="hidden" name="hide" value="{{ '0' if j.dismissed else '1' }}"><input type="hidden" name="back" value="{{ back if not j.dismissed else here }}"><button class="btn ghost">{{ 'Unhide' if j.dismissed else 'Hide' }}</button></form>{% endif %}
</div>

{% if versions %}<div class="card"><b>CVs made for this role</b><br>
{% for x in versions|reverse %}<a href="/cv/{{ j.uid|urlencode }}?v={{ x.version }}">Version {{ x.version }}</a> <span class="mute">{{ x.made[:10] }}</span>{{ ' · ' if not loop.last }}{% endfor %}</div>{% endif %}

{% if j.match %}{% set mt = j.match %}<div class="card"><b>How your CVs match</b>
<p style="margin:6px 0 0">{% if mt.cv == 'long CV' %}Your CVs cover {{ mt.long_cov }}% of the skills this job asks for.
{% else %}Your {{ mt.cv }} covers {{ mt.role_cov }}% of the skills this job asks for. {% if mt.long_cov > mt.role_cov %}With your other CVs, you cover {{ mt.long_cov }}%.{% else %}Your other CVs don't add to that.{% endif %}{% endif %}
{% if mt.req_n %}{% if mt.req_have == mt.req_n %}You have all the skills the job lists as requirements.{% else %}You have {{ mt.req_have }} of the {{ mt.req_n }} skills the job lists as requirements.{% endif %}{% endif %}</p>
<p style="margin:6px 0 0">{% if mt.missing %}<b>What's missing:</b> {{ mt.missing|join(', ') }}.{% else %}Nothing obvious is missing.{% endif %}</p>
{% if mt.meaning is not none %}<p style="margin:6px 0 0">By meaning, your experience fits this job at {{ mt.meaning }}% on the same scale as the keyword figure{% if mt.meaning >= mt.long_cov + 5 %}: the description asks for things you've done in words your CVs don't use{% elif mt.meaning <= mt.long_cov - 5 %}: your CVs share its words more than its substance{% endif %}. The match level blends the two.</p>
{% if weakest %}<p style="margin:8px 0 0"><b>Least covered by your bullets</b> <span class="mute" style="font-size:13px">(requirements the job states, with your closest bullet)</span></p><ul style="margin:4px 0 0;padding-left:18px">{% for r in weakest %}<li style="margin:4px 0"><span class="mute">{{ r.req }}</span><br>&rarr; {% if r.close %}<b>{{ r.label or 'a line from your CVs' }}</b> <span class="pill hot">close match</span>{% if r.text %} <span class="mute" style="font-size:12px">{{ r.text[:90] }}...</span>{% endif %}{% else %}<span class="pill warn">no close match</span>{% if r.label %} <span class="mute" style="font-size:12px">nearest: {{ r.label }}</span>{% endif %}{% endif %}</li>{% endfor %}</ul>{% endif %}
{% else %}<p class="mute" style="margin:6px 0 0;font-size:13px">Matched on keywords only (meaning matching hasn't read this role yet).</p>{% endif %}
</div>{% elif not desc %}<div class="card mute">Not scored yet: the description hasn't been read. Press Check now on the Jobs page.</div>{% endif %}

{% if j.industries %}<div class="card"><b>Industry</b><br>{% for name, kind in j.industries %}{{ name }} <span class="mute">({{ 'the description asks for this experience' if kind == 'asks' else 'mentioned often' }})</span>{% if not loop.last %}<br>{% endif %}{% endfor %}</div>{% endif %}

{% if desc %}<h2>Job description</h2><div class="card desc">{{ desc }}</div>{% endif %}
{% endblock %}"""

TEMPLATES["paste.html"] = """{% extends "base.html" %}{% block body %}
<a class="back" href="{{ '/jobs/role/' ~ (uid|urlencode) ~ '?back=/jobs/pasted' if uid else '/jobs/pasted' }}">&larr; Back{{ ' to the role' if uid else ' to Pasted' }}</a>
<h1>{{ 'Edit a pasted job' if uid else 'Paste a job' }}</h1>
<p class="sub">For a role the job watcher doesn't capture. The site keeps it, scores it against your CVs like any other role, and gives it Generate CV and Add to Applications.</p>
{% if errors %}<div class="errors">{% for e in errors %}{{ e }}<br>{% endfor %}</div>{% endif %}
<form class="f" method="post" action="/jobs/paste">
<input type="hidden" name="_token" value="{{ TOKEN }}"><input type="hidden" name="uid" value="{{ uid }}">
<label>Company<input name="company" value="{{ v.company }}" list="cos" required autocomplete="off"></label>
<label>Role title<input name="title" value="{{ v.title }}" required placeholder="Senior Product Manager, Payments"></label>
<label>Link to the posting<input name="url" value="{{ v.url }}" placeholder="https://... (optional)">
<span class="mute" style="font-size:12px">With a link, the site can ask whether you applied.</span></label>
<label>Location<input name="location" value="{{ v.location }}" placeholder="New York, NY (optional)"></label>
<label>Kind of role<select name="kind"><option value="">Work it out from the title</option>{% for k in kinds %}<option {{ 'selected' if k == v.kind }}>{{ k }}</option>{% endfor %}</select>
<span class="mute" style="font-size:12px">Decides which of your CVs it's compared with.</span></label>
<label class="wide">Job description<textarea name="desc" rows="16" required placeholder="Paste the whole description, including the qualifications. Headings such as Basic qualifications and Preferred qualifications help: required skills count for more.">{{ v.desc }}</textarea></label>
<div class="wide actions" style="margin:0"><button class="btn">{{ 'Save changes' if uid else 'Save this job' }}</button><a class="btn ghost" href="/jobs/pasted">Cancel</a></div>
</form>
<datalist id="cos">{% for n in company_names %}<option value="{{ n }}">{% endfor %}</datalist>
{% if uid %}<p class="mute">Saving a new description doesn't change CVs already made for this role. Press Generate CV again for a new version.</p>{% endif %}
{% endblock %}"""

TEMPLATES["coverage.html"] = """{% extends "base.html" %}{% block body %}
{% if run.running %}<meta http-equiv="refresh" content="3">{% endif %}
{% include "_jobs_tabs.html" %}
<h2 style="margin-top:0">Which companies the watcher covers</h2>
<p class="sub">It reads public job feeds from Greenhouse, Lever and Ashby, plus Amazon's job search, the first page of Google's, and Workday career sites. Companies that post jobs anywhere else (their own careers site, Workday and the like) aren't covered. Check those by hand, or set a board below if you find one.</p>
{% set ok = rows|selectattr('ok')|list %}{% set notok = rows|rejectattr('ok')|list %}
<h2>Can't cover ({{ notok|length }})</h2>
{% if notok %}
<div class="actions"><form method="post" action="/jobs/look-again" style="margin:0"><input type="hidden" name="_token" value="{{ TOKEN }}"><button class="btn ghost small">Look these up again on the next check</button></form></div>
<table><tr><th>#</th><th>Company</th><th>Why</th><th>Check by hand</th><th>Found a board?</th></tr>
{% for r in notok %}<tr><td class="mute">{{ r.rank or '' }}</td>
<td>{% if r.curl %}<a href="{{ r.curl }}">{{ r.name }}</a>{% else %}{{ r.name }}{% endif %}</td>
<td class="mute">{{ r.b.status or 'Not checked yet' }}</td>
<td>{% if r.career %}<a href="{{ r.career }}" target="_blank" rel="noopener">{{ 'Open their job search' if r.b.blocked else 'Career page' }}</a>{% else %}<a href="{{ r.google }}" target="_blank" rel="noopener">Search for it</a>{% endif %}</td>
<td><form method="post" action="/jobs/board" class="row" style="margin:0"><input type="hidden" name="_token" value="{{ TOKEN }}"><input type="hidden" name="company" value="{{ r.name }}"><input type="hidden" name="action" value="set">
<input name="link" placeholder="Paste a job link" style="padding:4px 8px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--ink);min-width:150px"><button class="btn small">Save</button></form>
{% if r.b.source != 'none' %}<form method="post" action="/jobs/board" style="margin:4px 0 0"><input type="hidden" name="_token" value="{{ TOKEN }}"><input type="hidden" name="company" value="{{ r.name }}"><input type="hidden" name="action" value="none"><button class="btn small ghost">Stop looking</button></form>{% endif %}</td></tr>{% endfor %}</table>
{% else %}<div class="empty">Every watched company is covered.</div>{% endif %}

<h2>Covered ({{ ok|length }})</h2>
{% if ok %}<table><tr><th>#</th><th>Company</th><th>Board</th><th>How it was found</th><th>Open roles</th><th>Match your roles</th><th>Checked</th><th></th></tr>
{% for r in ok %}<tr><td class="mute">{{ r.rank or '' }}</td>
<td>{% if r.curl %}<a href="{{ r.curl }}">{{ r.name }}</a>{% else %}{{ r.name }}{% endif %}</td>
<td><a href="{{ r.board_url }}" target="_blank" rel="noopener">{{ ats_names[r.b.ats] }}: {{ r.b.token.split('|')[2] if r.b.ats == 'workday' else r.b.token }}</a>{% if r.b.board_name %}<br><span class="mute">Board name: {{ r.b.board_name }}</span>{% endif %}</td>
<td class="mute">{% if r.b.ats == 'amazon' %}Amazon's own job search. Not an official feed, so it may stop working if Amazon changes its site.{% elif r.b.ats == 'workday' %}Workday sitemap (listed in the site's robots.txt). Posting dates looked up once per matching role.{% elif r.b.ats == 'google' %}Google's careers results page, first page of each search only (Google's rules). No posting dates, so age counts from when the watcher first saw a role. May stop working if Google changes the page.{% else %}{{ {'seed': 'Checked list', 'auto': 'Found automatically, worth a glance', 'manual': 'Set by you'}.get(r.b.source, '') }}{% endif %}</td>
<td>{{ r.b.jobs_total }}</td><td>{{ r.b.matches }}</td><td class="mute">{{ (r.b.checked or '')[:10] }}</td>
<td><form method="post" action="/jobs/board" style="margin:0"><input type="hidden" name="_token" value="{{ TOKEN }}"><input type="hidden" name="company" value="{{ r.name }}"><input type="hidden" name="action" value="again"><button class="btn small ghost" title="Forget this board and look it up again">Wrong board?</button></form></td></tr>{% endfor %}</table>
{% else %}<div class="empty">Nothing covered yet. Go to <a href="/jobs">Jobs</a> and press Check now.</div>{% endif %}
<p class="mute">The watcher only follows Tier 1. Change a company's tier in the Companies sheet to add or drop it. A company you set a board for by hand is followed whatever its tier.</p>
{% endblock %}"""


TEMPLATES["h1b.html"] = """{% extends "base.html" %}{% block body %}
{% if state.running %}<meta http-equiv="refresh" content="4">{% endif %}
<p class="sub"><a href="/companies">Companies</a></p>
<h1>Refresh the H-1B numbers</h1>
<p class="sub">When the Department of Labor publishes a new disclosure file, save it in the PM Tracker folder with its usual name (LCA_Disclosure_Data_FY2026_Q4.xlsx, for example) and press Refresh. The site rebuilds the ranking, shows you what would change, and only touches tracker.xlsx when you press Apply.</p>

<h2>Files in the folder</h2>
{% if files %}<table><tr><th>File</th><th>Size</th><th>Read before?</th></tr>
{% for f in files %}<tr><td>{{ f.name }}</td><td>{{ f.size|round|int }} MB</td><td>{{ 'Yes, quick' if f.cached else 'No, takes a few minutes' }}</td></tr>{% endfor %}</table>
{% else %}<div class="empty">No LCA_Disclosure_Data files found in the folder.</div>{% endif %}
<p class="mute">Current data runs to {{ S.data_through }}. Overlapping files are fine: a case found in two files counts once, using the later decision. The window is the 12 months up to the latest decision.</p>

<div class="actions">
{% if state.running %}<span class="btn ghost">Working: {{ state.message }}</span><span class="mute" style="padding:7px 0">A new big file takes about five minutes. You can leave this page.</span>
{% else %}<form method="post" action="/h1b/refresh" style="margin:0"><input type="hidden" name="_token" value="{{ TOKEN }}"><button class="btn {{ 'ghost' if result }}">Refresh the numbers</button></form>{% endif %}
</div>
{% if state.error %}<div class="errors">The refresh stopped: {{ state.error }}</div>{% endif %}

{% if result and change %}
{% set st = result.stats %}
<h2>What would change</h2>
<div class="grid">
<div class="card"><div class="k">New data window</div><div class="v" style="font-size:15px">{{ st.window[0] }} to {{ st.window[1] }}</div></div>
<div class="card"><div class="k">Certified H-1B cases</div><div class="v">{{ '{:,}'.format(st.certified) }}</div></div>
<div class="card"><div class="k">New-hire role filings</div><div class="v">{{ '{:,}'.format(st.role_newhire) }}</div></div>
<div class="card"><div class="k">Join the top 300</div><div class="v">{{ change.joining|length }}</div></div>
<div class="card"><div class="k">Leave the top 300</div><div class="v">{{ change.keep_dropped|length + change.remove|length }}</div></div>
</div>

{% if change.remove %}<div class="card"><b>{{ change.remove|length }} compan{{ 'y' if change.remove|length == 1 else 'ies' }} would be taken off the Companies sheet.</b> They fall out of the top 300 and you have no notes, contacts or applications there:
<span class="mute">{{ change.remove|map(attribute='Company')|join(', ') }}</span>.<br>Pressing Apply removes these rows. A backup is saved first.</div>{% endif %}
{% if change.keep_dropped %}<div class="card"><b>Kept even though they fall out of the top 300</b>, because you have notes, a tier you set, contacts or applications there:
<span class="mute">{{ change.keep_dropped|map(attribute='Company')|join(', ') }}</span>. They move to the bottom with a flag.</div>{% endif %}

{% if change.joining %}<h2>Joining</h2>
<table><tr><th>Rank</th><th>Company</th><th>Tier</th><th>Score</th><th>Focus</th></tr>
{% for r in change.joining[:40] %}<tr><td>{{ r.rank }}</td><td>{{ r.name }}</td><td>{{ r.tier }}</td><td>{{ r.score }}</td><td>{{ r.focus }}</td></tr>{% endfor %}</table>
{% if change.joining|length > 40 %}<p class="mute">And {{ change.joining|length - 40 }} more.</p>{% endif %}{% endif %}

{% if change.tier_changes %}<h2>Tier changes</h2>
<table><tr><th>Company</th><th>Now</th><th>Would be</th></tr>
{% for n, a, b in change.tier_changes %}<tr><td>{{ n }}</td><td>{{ a }}</td><td>{{ b }}</td></tr>{% endfor %}</table>
<p class="mute">Tiers you changed by hand are kept and not listed here. The job watcher follows Tier 1, so this changes what it watches.</p>{% endif %}

{% if change.moves %}<h2>Biggest rank moves</h2>
<table><tr><th>Company</th><th>Rank now</th><th>Would be</th></tr>
{% for n, a, b in change.moves[:15] %}<tr><td>{{ n }}</td><td>{{ a }}</td><td>{{ b }}</td></tr>{% endfor %}</table>{% endif %}

<div class="actions" style="margin-top:16px">
<form method="post" action="/h1b/apply" style="margin:0"><input type="hidden" name="_token" value="{{ TOKEN }}"><button class="btn">Apply to tracker.xlsx</button></form>
<form method="post" action="/h1b/discard" style="margin:0"><input type="hidden" name="_token" value="{{ TOKEN }}"><button class="btn ghost">Throw this away</button></form>
</div>
<p class="mute">Apply keeps everything you typed: tier changes, E-Verify, sponsorship answers, last checked, career page and notes. It rewrites the numbers, the Excluded and Entity groups sheets, the Read me dates and counts, and the data date in Settings. Close tracker.xlsx in Excel first.</p>
{% endif %}
{% endblock %}"""


TEMPLATES["cv.html"] = """{% extends "base.html" %}{% block body %}
<a class="back" href="/jobs/role/{{ uid|urlencode }}">&larr; Back to the role</a>
<h1>Tailored CV: {{ info.role }}</h1>
<p class="sub">{{ info.company }}{% if info.url %} &middot; <a href="/go/job/{{ uid|urlencode }}" target="_blank" rel="noopener">posting</a>{% endif %} &middot; version {{ info.version }}, made {{ info.made.replace('T', ' at ')[:19] }}</p>
<div class="actions">
{% if can_open %}<form method="post" action="/cv/open" style="margin:0"><input type="hidden" name="_token" value="{{ TOKEN }}"><input type="hidden" name="path" value="{{ info.path }}"><input type="hidden" name="back" value="/cv/{{ uid|urlencode }}?v={{ info.version }}"><button class="btn">Open CV in Word</button></form>
<form method="post" action="/cv/open" style="margin:0"><input type="hidden" name="_token" value="{{ TOKEN }}"><input type="hidden" name="path" value="{{ info.folder }}"><input type="hidden" name="back" value="/cv/{{ uid|urlencode }}?v={{ info.version }}"><button class="btn ghost">Open folder</button></form>{% endif %}
<form method="post" action="/cv/record" style="margin:0"><input type="hidden" name="_token" value="{{ TOKEN }}"><input type="hidden" name="uid" value="{{ uid }}"><input type="hidden" name="v" value="{{ info.version }}"><button class="btn ghost" title="Puts this CV's file name on your application for this role (adds the role to Applications if it isn't there)">Record this CV on my application</button></form>
<form method="post" action="/jobs/cv" style="margin:0"><input type="hidden" name="_token" value="{{ TOKEN }}"><input type="hidden" name="uid" value="{{ uid }}"><button class="btn ghost" title="Makes a new version; the old one is kept">Generate again</button></form>
</div>
<div class="grid">
<div class="card"><div class="k">{{ info.before_cv }}</div><div class="v">{{ info.before_pct }}%</div><span class="mute">of the skills this job asks for</span></div>
<div class="card"><div class="k">Strategy CV</div><div class="v">{{ info.strategy_pct }}%</div></div>
<div class="card"><div class="k">This tailored CV</div><div class="v">{{ info.after_pct }}%</div></div>
<div class="card"><div class="k">Length</div><div class="v">{{ info.length_pct }}%</div><span class="mute">of your Strategy CV's bullets</span></div>
</div>
{% if info.length_pct > 103 %}<p class="warn">A little longer than your Strategy CV. Open it and check it still fits on one page.</p>{% endif %}
{% if info.readability is defined %}{% if info.readability %}<div class="errors"><b>Readability check found problems:</b> {{ info.readability|join(' ') }}</div>
{% else %}<p><span class="pill hot">Readability check passed</span> <span class="mute">Read back in plain order: name, headings, every employer with its dates, every bullet under the right employer, and the skills all come out where they should.</span></p>{% endif %}{% endif %}
<h2>Bullets used</h2>
{% if info.role_type %}<p>Role type: <b>{{ info.role_type }}</b>. {% if info.rewrites_used %}Bullets come from that section of your Bullet rewrites (Core first, then Strong, then Reserve).{% else %}Bullet rewrites.docx has no section for it, so the bullets use the wording from your CVs.{% endif %}{% if info.meaning_used %} Chosen with meaning matching and the re-ranker as well as keywords.{% elif info.meaning_used is defined %} Chosen on keywords (meaning matching wasn't ready).{% endif %}</p>{% endif %}
<p class="mute">Employers stay in date order. The best fits for this job get more bullets; within each employer the best fit comes first. Never two bullets claiming the same result under one employer. <span class="pill hot">new</span> marks a line from your CVs that isn't on your Strategy CV. Every line is your own wording.</p>
{% for emp, bs in info.bullets.items() %}<div class="card"><b>{{ emp }}</b> <span class="mute">({{ bs|length }} bullet{{ 's' if bs|length != 1 }})</span>
<ul style="margin:6px 0 0;padding-left:18px">{% for b in bs %}<li>{% if b.new %}<span class="pill hot">new</span> {% endif %}{{ b.text }} <span class="mute" style="font-size:12px">({% if b.id %}{{ b.id }}{{ ', ' ~ b.fit|capitalize if b.fit }}{% else %}{{ {'strategy': 'Strategy CV', 'long': 'long CV', 'pm': 'PM CV', 'pmm': 'PMM CV'}.get(b.source, b.source) }}{% endif %})</span></li>{% endfor %}</ul></div>{% endfor %}
{% if info.requirements %}<h2>Requirements checklist</h2>
<p class="mute">What the job lists as requirements, and the bullet on this CV that speaks to each. Anything not on this CV is worth a swap or an interview story.</p>
<div class="card"><ul style="margin:0;padding-left:18px">{% for r in info.requirements %}<li style="margin:5px 0">{% if r.covered %}<span class="pill hot">covered</span>{% else %}<span class="pill warn">not on this CV</span>{% endif %} {{ r.req }}{% if r.covered %} <span class="mute" style="font-size:12px">({{ r.label or 'a line from your CVs' }})</span>{% endif %}</li>{% endfor %}</ul></div>{% endif %}
{% if info.dropped %}<h2>Taken out from your Strategy CV</h2>
<ul class="mute">{% for t in info.dropped %}<li>{{ t }}</li>{% endfor %}</ul>{% endif %}
<h2>Skills line</h2>
<div class="card"><span class="mute">Before:</span> {{ info.skills_before|join(', ') }}<br><span class="mute">After:</span> {{ info.skills_after|join(', ') }}</div>
<p class="mute">Saved in {{ info.folder }}, with "about this CV" and a copy of the job description.</p>
{% if versions|length > 1 %}<h2>Versions</h2><p>{% for x in versions %}<a href="/cv/{{ uid|urlencode }}?v={{ x.version }}">v{{ x.version }}</a> <span class="mute">{{ x.made[:10] }}</span>{{ ' · ' if not loop.last }}{% endfor %}</p>{% endif %}
{% endblock %}"""
