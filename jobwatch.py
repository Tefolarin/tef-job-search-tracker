"""Job watcher. Reads the official public job feeds of Greenhouse, Lever and Ashby. No scraping, no logins.

Everything it remembers lives in data/jobwatch.json next to this file. tracker.xlsx is only written when you
press "Add to Applications".
"""
import os
import re
import json
import time
import threading
import datetime as dt
import urllib.request
import urllib.error
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
STORE = os.path.join(DATA_DIR, "jobwatch.json")
UA = "PM-Tracker personal job watcher (one request per company per check)"
TIMEOUT = 15

# Checked by hand on 12 October 2026. The watcher still confirms each one live before trusting it.
SEED = {
    "stripe": ("greenhouse", "stripe"),
    "robinhood markets, inc.": ("greenhouse", "robinhood"),
    "doordash": ("greenhouse", "doordashusa"),
    "datadog, inc.": ("greenhouse", "datadog"),
    "databricks, inc.": ("greenhouse", "databricks"),
    "scale ai": ("greenhouse", "scaleai"),
    "twilio, inc.": ("greenhouse", "twilio"),
    "waymo llc": ("greenhouse", "waymo"),
    "maplebear inc.": ("greenhouse", "instacart"),
    "zscaler, inc.": ("greenhouse", "zscaler"),
    "everpure, inc.": ("greenhouse", "purestorage"),
    "lucid usa, inc.": ("greenhouse", "lucidmotors"),
    "zoox inc.": ("lever", "zoox"),
    "snowflake inc.": ("ashby", "snowflake"),
    "juniper square inc.": ("ashby", "junipersquare"),
    "amazon": ("amazon", "amazon"),
    "google": ("google", "google"),
    # added 31 October 2026 from roles the user pasted (boards checked by hand)
    "openai opco, llc": ("ashby", "openai"),
    "riot games": ("greenhouse", "riotgames"),
    "hunter douglas": ("greenhouse", "hunterdouglas"),
    "momentum": ("greenhouse", "momentumcompany3"),
    "forcefactor": ("greenhouse", "forcefactor"),
    # consulting firms funnel, step 4 (31 October 2026): sponsoring firms whose boards the watcher can read
    "keystone strategy": ("greenhouse", "keystonestrategy"),
    "cra international": ("greenhouse", "charlesriverassociates"),
    "the brattle group": ("greenhouse", "thebrattlegroup"),
    "clearview healthcare partners": ("greenhouse", "clearviewhealthcarepartners"),
    "alixpartners": ("greenhouse", "alixpartners"),
    "capco": ("greenhouse", "capco"),
    "gallup": ("greenhouse", "gallup"),
}

# Workday career sites (checked 13 October 2026: each tenant's robots.txt allows the site and lists its sitemap).
# token = "<root>|<tenant>|<site>|<path prefix>"; the prefix is "" for myworkdayjobs.com hosts.
WORKDAY = {
    "adobe": ("https://adobe.wd5.myworkdayjobs.com", "adobe", "external_experienced", ""),
    "salesforce": ("https://salesforce.wd12.myworkdayjobs.com", "salesforce", "External_Career_Site", ""),
    "nvidia": ("https://nvidia.wd5.myworkdayjobs.com", "nvidia", "NVIDIAExternalCareerSite", ""),
    "cisco": ("https://cisco.wd5.myworkdayjobs.com", "cisco", "Cisco_Careers", ""),
    "dell": ("https://dell.wd1.myworkdayjobs.com", "dell", "External", ""),
    "hewlett packard enterprise company": ("https://hpe.wd5.myworkdayjobs.com", "hpe", "Jobsathpe", ""),
    "fidelity investments": ("https://wd1.myworkdaysite.com", "fmr", "FidelityCareers", "/recruiting/fmr"),
    "expedia, inc.": ("https://expedia.wd108.myworkdayjobs.com", "expedia", "search", ""),
    "visa": ("https://visa.wd5.myworkdayjobs.com", "visa", "Visa", ""),
    "capital one": ("https://capitalone.wd12.myworkdayjobs.com", "capitalone", "Capital_One", ""),
    "autodesk, inc.": ("https://autodesk.wd1.myworkdayjobs.com", "autodesk", "Ext", ""),
    "applied materials, inc": ("https://amat.wd1.myworkdayjobs.com", "amat", "External", ""),
    "humana inc.": ("https://humana.wd5.myworkdayjobs.com", "humana", "Humana_External_Career_Site", ""),
    "mastercard": ("https://mastercard.wd1.myworkdayjobs.com", "mastercard", "CorporateCareers", ""),
    "f5, inc.": ("https://ffive.wd5.myworkdayjobs.com", "ffive", "f5jobs", ""),
    "state street bank and trust company": ("https://statestreet.wd1.myworkdayjobs.com", "statestreet", "Global", ""),
    "kla corporation": ("https://kla.wd1.myworkdayjobs.com", "kla", "Search", ""),
    "hp inc.": ("https://hp.wd5.myworkdayjobs.com", "hp", "ExternalCareerSite", ""),
    "lexisnexis": ("https://relx.wd3.myworkdayjobs.com", "relx", "LexisNexisLegal", ""),
    # consulting firms funnel, step 4 (31 October 2026)
    "accenture": ("https://accenture.wd103.myworkdayjobs.com", "accenture", "AccentureCareers", ""),
    "pwc": ("https://pwc.wd3.myworkdayjobs.com", "pwc", "US_Experienced_Careers", ""),
    "guidehouse": ("https://guidehouse.wd1.myworkdayjobs.com", "guidehouse", "External", ""),
    "huron": ("https://huron.wd1.myworkdayjobs.com", "huron", "huroncareers", ""),
    "cornerstone research": ("https://cornerstone.wd501.myworkdayjobs.com", "cornerstone", "CornerstoneResearch_Careers", ""),
    "brg": ("https://thinkbrg.wd5.myworkdayjobs.com", "thinkbrg", "BRG_External_Career_Site", ""),
    "compass lexecon": ("https://fticonsulting.wd108.myworkdayjobs.com", "fticonsulting", "CompassLexeconCareers", ""),
    "fti consulting": ("https://fticonsulting.wd108.myworkdayjobs.com", "fticonsulting", "FTIConsultingCareers", ""),
    "iqvia": ("https://iqvia.wd1.myworkdayjobs.com", "iqvia", "IQVIA", ""),
    "trinity life sciences": ("https://trinitylifesciences.wd108.myworkdayjobs.com", "trinitylifesciences", "Trinity", ""),
    # its "alvarezandmarsal" site lists no jobs; the live careers site is "alvarezandmarsalp" (checked 31 Oct 2026)
    "alvarez & marsal": ("https://alvarezandmarsal.wd1.myworkdayjobs.com", "alvarezandmarsal", "alvarezandmarsalp", ""),
    "public consulting group": ("https://pcg.wd1.myworkdayjobs.com", "pcg", "PCG_External_Careers", ""),
    "icf": ("https://icf.wd5.myworkdayjobs.com", "icf", "ICFExternal_Career_Site", ""),
    "protiviti": ("https://roberthalf.wd1.myworkdayjobs.com", "roberthalf", "ProtivitiExperiencedCareers", ""),
    "premier": ("https://premierinc.wd1.myworkdayjobs.com", "premierinc", "External_Professional", ""),
    "syneos health": ("https://syneoshealth.wd12.myworkdayjobs.com", "syneoshealth", "Syneos_Health_External_Site", ""),
    "ankura": ("https://ankura.wd5.myworkdayjobs.com", "ankura", "Ankura", ""),
    "kantar": ("https://kantar.wd3.myworkdayjobs.com", "kantar", "KANTAR", ""),
    "gartner": ("https://gartner.wd5.myworkdayjobs.com", "gartner", "EXT", ""),
}
for _k, _v in WORKDAY.items():
    SEED[_k] = ("workday", "|".join(_v))
# a checked seed replaces a board the watcher guessed by itself (HP's 7-role Greenhouse board)
SEED_REPLACES_AUTO = {"hp inc."}
# Watched even though they aren't Tier 1 on the Companies sheet (the user's pasted roles came from them)
EXTRA_WATCH = ["OpenAI OpCo, LLC", "LexisNexis", "Riot Games", "Hunter Douglas", "Momentum", "ForceFactor",
               # consulting firms funnel, step 4 (31 October 2026): sponsor H-1Bs and have a readable board
               "Accenture", "PwC", "Guidehouse", "Huron", "Keystone Strategy", "Cornerstone Research", "CRA International",
               "BRG", "Compass Lexecon", "The Brattle Group", "ClearView Healthcare Partners", "IQVIA",
               "Trinity Life Sciences", "Alvarez & Marsal", "AlixPartners", "Capco", "Public Consulting Group", "ICF",
               "Protiviti", "Premier", "Syneos Health", "Ankura", "FTI Consulting", "Kantar", "Gartner", "Gallup"]

# Sites whose rules don't allow automated reading. The watcher leaves them alone and says why.
BLOCKED = {
    "microsoft": ("Microsoft's job search blocks automated tools in its robots.txt. Check it by hand, or set up "
                  "job alerts on Microsoft's careers site.", "https://careers.microsoft.com/v2/global/en/home.html"),
    "meta": ("Meta's robots.txt says automated collection needs Meta's written permission. Check it by hand, or set "
             "up job alerts on Meta's careers site.", "https://www.metacareers.com/jobsearch/"),
    "linkedin corporation": ("The Lever board named 'linkedin' holds test postings, not LinkedIn's jobs. LinkedIn's own "
                             "jobs are on linkedin.com, which blocks automated tools. Check by hand.",
                             "https://www.linkedin.com/company/linkedin/jobs/"),
}

ATS_NAMES = {"greenhouse": "Greenhouse", "lever": "Lever", "ashby": "Ashby", "amazon": "Amazon Jobs search (unofficial)",
             "google": "Google Careers results (first page only)", "workday": "Workday"}
UNOFFICIAL = {"amazon", "google"}

# Google: robots.txt allows the first results page but not ?page=, so the watcher reads only page one of each
# search, sorted newest first (20 roles each). The page shows no posting date, so age counts from first seen.
GOOGLE_RESULTS = "https://www.google.com/about/careers/applications/jobs/results"
GOOGLE_QUERIES = ['"product manager"', '"product marketing"', "strategy", "MBA", '"leadership development program"']

# Amazon has no public job feed. Its own careers site loads search results as data from search.json, and the
# watcher reads that, a few searches per check, newest first, US only. Not an official feed: it may change.
AMAZON_SEARCH = "https://www.amazon.jobs/en/search.json"
AMAZON_QUERIES = ["product manager", "product marketing", "strategy", "MBA", "leadership development program"]
AMAZON_PAGE = 100
AMAZON_MAX_PAGES = 30      # per search, a ceiling; paging normally stops on the date rule after 1 to 3 pages
AMAZON_STOP_DAYS = 45      # stop paging once results are older than this

# ---------- title matching (same role definitions as the H-1B ranking) ----------
PRODUCT = [
    (r"\bproduct marketing\b|\bpmm\b", "Product marketing"),
    (r"\bproduct operations?\b|\bproduct ops\b", "Product ops"),
    (r"\bproduct (manager|owner|lead|director|management|leader)\b|\b(director|head|vp|vice president),? (of )?product\b"
     r"|\bgroup product manager\b|\bassociate product manager\b|\b(apm|gpm)\b|\bprincipal product\b"
     r"|\bproduct manager\b", "Product"),
]
STRATEGY = (r"\bcorporate strategy\b|\bbusiness strategy\b|\bstrategy\s*(and|&)\s*(operations|ops|planning|analytics)\b"
            r"|\bstrategic (planning|initiatives)\b|\bstrategy (manager|lead|associate|analyst|director|principal)\b"
            r"|\b(director|head|vp|vice president|manager|lead),? (of )?(corporate )?strategy\b|\bbiz ?ops\b"
            r"|\bbusiness operations (and|&) strategy\b")  # chief of staff is out of scope, as in the ranking
STRATEGY_EXCLUDE = r"\b(sales|marketing|content|brand|pricing|investment|credit|risk|data|channel|seo|tax|legal)\b"
# MBA leadership and rotational programmes (added 31 October 2026): checked before product and strategy, so an "MBA
# Product Leadership Program" counts as a programme. Undergraduate, PhD, internship and clinical programmes are left out.
MBA = (r"\bmba\b|\bleadership (development )?program(me)?s?\b|\bleadership development\b|\brotational\b|"
       r"\brotation(al)? program|\bdevelopment program(me)?\b|\baccelerated leadership\b|"
       r"\bgeneral management (associate|program)|\bgraduate (hire|program|programme|scheme)\b|\bassociate program\b|"
       r"\buniversity graduate\b|\bexecutive development\b|\bmanagement associate\b|\bfuture leaders?\b|"
       r"\bemerging leaders?\b|\bleadership associate\b")
MBA_EXCLUDE = (r"\b(phd|ph\.d|undergrad\w*|bachelor'?s?|high school|apprentice\w*|summer associate|summer intern\w*|"
               r"nurs(e|ing)|clinical|pharmac\w*|residency|teacher|software development program)\b")
EXCLUDE = r"\btechnical program manag|\btpm\b|\bengineer\b|\bdeveloper\b|\bscientist\b|\bintern(ship)?\b|\bdesigner\b|\brecruiter\b"


def classify(title):
    """Returns (focus, label) or (None, None). focus is Product or Strategy, the Applications values (MBA
    programmes count as Strategy there, with the label "MBA programme")."""
    t = title.lower()
    if re.search(EXCLUDE, t):
        return None, None
    if re.search(MBA, t) and not re.search(MBA_EXCLUDE, t):
        return "Strategy", "MBA programme"
    for pat, label in PRODUCT:
        if re.search(pat, t):
            return "Product", label
    if re.search(STRATEGY, t) and not re.search(STRATEGY_EXCLUDE, t):
        return "Strategy", "Strategy"
    return None, None


# ---------- US or not ----------
NON_US = (r"\b(canada|toronto|vancouver|montreal|ottawa|mexico|brazil|s[aã]o paulo|argentina|buenos aires|uk|u\.k\.|"
          r"united kingdom|london|england|scotland|edinburgh|manchester|ireland|dublin|france|paris|germany|berlin|munich|"
          r"hamburg|netherlands|amsterdam|spain|madrid|barcelona|portugal|lisbon|italy|milan|switzerland|zurich|sweden|"
          r"stockholm|poland|warsaw|krakow|india|bangalore|bengaluru|hyderabad|pune|mumbai|delhi|gurgaon|gurugram|chennai|"
          r"noida|singapore|japan|tokyo|china|beijing|shanghai|shenzhen|hong kong|taiwan|taipei|korea|seoul|australia|"
          r"sydney|melbourne|new zealand|auckland|israel|tel aviv|uae|dubai|abu dhabi|emea|apac|latam|europe|philippines|"
          r"manila|vietnam|indonesia|jakarta|malaysia|kuala lumpur|thailand|bangkok|nigeria|lagos|kenya|nairobi|"
          r"south africa|cape town|egypt|cairo|turkey|istanbul|czech|prague|romania|bucharest|hungary|budapest|denmark|"
          r"copenhagen|norway|oslo|finland|helsinki|belgium|brussels|austria|vienna|colombia|bogot[aá]|chile|santiago|"
          r"costa rica|peru|lima|serbia|belgrade|ukraine|greece|athens|saudi|riyadh|qatar|doha|pakistan|bulgaria|sofia|"
          r"lithuania|estonia|tallinn|luxembourg|latin america)\b")
US = (r"\b(united states|usa|u\.s\.a?\.?|us|new york|nyc|san francisco|bay area|seattle|bellevue|redmond|"
      r"mountain view|sunnyvale|palo alto|menlo park|san jose|santa clara|los angeles|austin|dallas|houston|chicago|"
      r"boston|atlanta|denver|boulder|miami|washington,? d\.?c|philadelphia|pittsburgh|phoenix|salt lake city|"
      r"detroit|minneapolis|nashville|raleigh|charlotte|san diego|irvine|oakland|south san francisco|foster city|"
      r"redwood city|cupertino|plano|kirkland|jersey city|brooklyn|manhattan)\b")
STATES = (r",\s*(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|"
          r"ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC)\b")


def us_status(location, country=""):
    loc = f"{location} {country}".strip()
    low = loc.lower()
    if re.search(r"\b(united states|usa|us)\b", (country or "").lower()):
        return "US"
    has_us = bool(re.search(US, low)) or bool(re.search(STATES, loc))
    if has_us:
        return "US"
    if re.search(NON_US, low):
        return "Not US"
    return "Unclear"


# ---------- feeds ----------
def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def board_url(ats, token):
    return {"greenhouse": f"https://job-boards.greenhouse.io/{token}",
            "lever": f"https://jobs.lever.co/{token}",
            "ashby": f"https://jobs.ashbyhq.com/{token}",
            "amazon": "https://www.amazon.jobs/en/search?base_query=product+manager&country=USA&sort=recent",
            "google": GOOGLE_RESULTS + "?q=%22product+manager%22&location=United+States&sort_by=date",
            "workday": _workday_site(token) if ats == "workday" else ""}[ats]


def _workday_parts(token):
    root, tenant, site, prefix = (token.split("|") + ["", "", "", ""])[:4]
    return root, tenant, site, prefix


def _workday_site(token):
    root, tenant, site, prefix = _workday_parts(token)
    return f"{root}{prefix}/{site}"


US_STATE_CODES = set("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC "
                     "ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC".split())
_known = {}  # uid -> posting date already looked up, filled from the store at the start of each check
_seen_before = set()  # roles already in the store: their date is never looked up again
WORKDAY_DETAIL_CAP = 400  # most posting-date and description lookups per company per check (150 until 31 Oct 2026)


def _workday_location(locpart):
    parts = [p for p in locpart.split("-") if p]
    if parts and parts[-1].upper() in US_STATE_CODES and len(parts) > 1:
        return " ".join(parts[:-1]) + ", " + parts[-1].upper()
    return " ".join(parts)


def _workday_title(slug):
    t = slug.replace("---", " - ").replace("--", " - ").replace("-", " ")
    return re.sub(r"\s+", " ", t).strip()


def _posted_from_text(text):
    """Workday says "Posted Today", "Posted Yesterday", "Posted 5 Days Ago" or "Posted 30+ Days Ago"."""
    t = (text or "").lower()
    today = dt.date.today()
    if "today" in t:
        return today
    if "yesterday" in t:
        return today - dt.timedelta(days=1)
    m = re.search(r"(\d+)\+?\s*days?", t)
    if m:
        return today - dt.timedelta(days=int(m.group(1)) + (1 if "+" in t else 0))
    return None


def workday_jobs(token):
    """Read the site's sitemap (listed in its robots.txt), keep titles that match your roles, then look up each
    match's posting date once from the job's Workday record."""
    root, tenant, site, prefix = _workday_parts(token)
    xml = fetch_text(f"{root}{prefix}/{site}/siteMap.xml")
    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)
    if "<sitemapindex" in xml:  # a big site splits its sitemap into parts
        locs = []
        for part in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)[:10]:
            locs += re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", fetch_text(part))
    if not locs:
        raise ValueError("Read the Workday sitemap but found no jobs in it. The site may have changed.")
    out, seen, lookups = [], set(), 0
    pat = re.compile(r"/" + re.escape(site) + r"/job/([^/]+)/([^/?#]+)_([A-Za-z0-9-]+)$", re.I)  # sitemaps vary the case
    for url in locs:
        m = pat.search(url)
        if not m:
            continue
        locpart, slug, req = m.groups()
        uid = f"wd:{tenant}:{req}"
        if uid in seen:
            continue
        seen.add(uid)
        title = _workday_title(slug)
        location = _workday_location(locpart)
        rec = {"uid": uid, "title": title, "url": url, "location": location, "country": "", "posted": "",
               "nodate": True, "inventory": True}
        focus, _ = classify(title)
        if focus and us_status(location) != "Not US":
            if uid in _known and _known[uid]:
                rec.update(posted=_known[uid], nodate=False)
            need_date = rec["nodate"] and uid not in _seen_before
            need_desc = uid not in _desc_done and uid not in _stored_desc()
            if (need_date or need_desc) and lookups < WORKDAY_DETAIL_CAP:
                lookups += 1
                try:
                    info = fetch_json(f"{root}/wday/cxs/{tenant}/{site}/job/{locpart}/{slug}_{req}").get(
                        "jobPostingInfo") or {}
                    if info.get("jobDescription"):
                        rec["desc"] = html_text(info["jobDescription"])
                    posted = info.get("startDate") or "" if need_date else ""
                    if not posted:
                        p = _posted_from_text(info.get("postedOn"))
                        posted = p.isoformat() if p else ""
                    if info.get("title"):
                        rec["title"] = info["title"]
                    if info.get("location"):
                        rec["location"] = info["location"]
                    if posted and rec["nodate"]:
                        rec.update(posted=posted[:10], nodate=False)
                except Exception:
                    pass  # no date: the role only shows if it appears after the first check
                time.sleep(0.2)
        out.append(rec)
    return out


def fetch_text(url):
    # Accept XML too: Workday answers 406 to a sitemap request that only accepts text/html (found 31 October 2026)
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "text/html,application/xml,text/xml;q=0.9,*/*;q=0.8",
                                               "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode("utf-8", "replace")


def parse_google(page):
    """Pull roles out of one Google results page. Defensive, because the page's markup isn't a published format.
    Each role is read from its own link tag (title in aria-label) and the stretch of page since the previous link."""
    import html as htmlmod
    link = re.compile(r'<a\b[^>]*?href="(?:\./|/about/careers/applications/)?jobs/results/(\d{6,})-([a-z0-9-]+)[^"]*"[^>]*>')
    matches = list(link.finditer(page))
    out, seen, prev_end = [], {}, 0
    for i, m in enumerate(matches):
        jid, slug, tag = m.group(1), m.group(2), m.group(0)
        before = page[prev_end:m.start()]
        nxt = matches[i + 1].start() if i + 1 < len(matches) else min(len(page), m.end() + 3000)
        after = page[m.end():nxt]
        prev_end = m.end()
        title = ""
        al = re.search(r'aria-label="(?:Learn more about )?([^"]+)"', tag)
        if al:
            title = al.group(1)
        else:
            h3 = re.findall(r"<h3[^>]*>(.*?)</h3>", before, re.S) or re.findall(r"<h3[^>]*>(.*?)</h3>", after, re.S)[:1]
            if h3:
                title = re.sub(r"<[^>]+>", "", h3[-1])
        title = htmlmod.unescape(title).strip()
        locs = [htmlmod.unescape(x).strip(" ;") for x in re.findall(r'class="r0wTof[^"]*"[^>]*>([^<]+)<', before)]
        if jid in seen:  # a second link to the same role: fill in anything missing
            rec = seen[jid]
            if title and rec["title_from_slug"]:
                rec.update(title=title, title_from_slug=False)
            if locs and not rec["location"]:
                rec["location"] = "; ".join(locs)
            continue
        rec = {"uid": f"go:{jid}", "title": title or slug.replace("-", " ").title(), "title_from_slug": not title,
               "url": f"{GOOGLE_RESULTS}/{jid}-{slug}", "location": "; ".join(x for x in locs if x),
               "country": "United States", "posted": "", "nodate": True}
        seen[jid] = rec
        out.append(rec)
    return out


def google_jobs():
    from urllib.parse import urlencode
    out, seen = [], set()
    for q in GOOGLE_QUERIES:
        page = fetch_text(GOOGLE_RESULTS + "?" + urlencode({"q": q, "location": "United States", "sort_by": "date"}))
        for j in parse_google(page):
            if j["uid"] not in seen:
                seen.add(j["uid"])
                out.append(j)
    if not out:
        raise ValueError("Read Google's results page but found no roles in it. Google may have changed the page.")
    return out


def amazon_jobs():
    from urllib.parse import urlencode
    out, seen = [], set()
    cutoff = dt.date.today() - dt.timedelta(days=AMAZON_STOP_DAYS)
    for q in AMAZON_QUERIES:
        offset = 0
        for _ in range(AMAZON_MAX_PAGES):
            url = AMAZON_SEARCH + "?" + urlencode({"base_query": q, "country": "USA", "result_limit": AMAZON_PAGE,
                                                   "offset": offset, "sort": "recent"})
            data = fetch_json(url)
            page = data.get("jobs") or []
            if not page:
                break
            oldest = None
            for j in page:
                try:
                    posted = dt.datetime.strptime(str(j.get("posted_date", "")).strip(), "%B %d, %Y").date()
                except ValueError:
                    posted = None
                if posted:
                    oldest = posted if oldest is None else min(oldest, posted)
                uid = f"az:{j.get('id_icims') or j.get('id')}"
                if uid in seen:
                    continue
                seen.add(uid)
                path = j.get("job_path") or ""
                out.append({"uid": uid, "title": j.get("title", ""),
                            "url": ("https://www.amazon.jobs" + path) if path.startswith("/") else path,
                            "location": j.get("location") or j.get("normalized_location") or "",
                            "country": "United States" if j.get("country_code") == "USA" else (j.get("country_code") or ""),
                            "posted": posted.isoformat() if posted else "",
                            "desc": "\n".join(x for x in (
                                html_text(j.get("description") or ""),
                                ("Basic qualifications:\n" + html_text(j.get("basic_qualifications") or ""))
                                if j.get("basic_qualifications") else "",
                                ("Preferred qualifications:\n" + html_text(j.get("preferred_qualifications") or ""))
                                if j.get("preferred_qualifications") else "") if x)})
            offset += len(page)
            if oldest is None or oldest < cutoff:
                break  # no readable dates (stop rather than page blindly), or we've reached old roles
            if offset >= int(data.get("hits") or 0):
                break
    return out


def parse_board_url(text):
    """Turn a pasted board link into (ats, token)."""
    t = (text or "").strip()
    pats = [(r"greenhouse\.io/(?:embed/job_board\?for=)?([A-Za-z0-9_-]+)", "greenhouse"),
            (r"lever\.co/([A-Za-z0-9_.-]+)", "lever"),
            (r"ashbyhq\.com/([A-Za-z0-9_.%-]+)", "ashby")]
    for p, ats in pats:
        m = re.search(p, t)
        if m and m.group(1).lower() not in ("v1", "boards", "v0", "postings", "posting-api", "embed"):
            return ats, m.group(1)
    return None, None


# ---------- job descriptions: industry and other signals ----------
DESC_FILE = os.path.join(DATA_DIR, "descriptions.json")
DESC_CAP = 300  # most description fetches per company per check (120 until 31 Oct 2026) (Greenhouse and Google need one request each)
_desc_done = set()  # roles already analysed


def html_text(s):
    import html as htmlmod
    s = htmlmod.unescape(str(s or ""))
    s = re.sub(r"(?i)<\s*(br|/p|/li|/h\d|/div)[^>]*>", ". ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = htmlmod.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


INDUSTRIES = {
    "Financial services": r"payments?|fintech|banking|\bbanks?\b|lending|loans?|credit cards?|financial services|"
                          r"wealth management|asset management|insurtech|brokerage|capital markets|underwriting|"
                          r"treasury|money movement|card issuing|mortgages?|\bkyc\b|\baml\b|financial institutions?",
    "Commerce and retail": r"e-?commerce|marketplaces?|\bretail|merchants?|checkout|shopping|grocery|\bcpg\b|"
                           r"consumer packaged goods|omnichannel|sellers?|storefronts?|\bd2c\b|direct.to.consumer",
    "Advertising": r"advertis\w*|\bad ?tech\b|\bads\b|programmatic|media buying|martech",
    "Healthcare": r"healthcare|health care|clinical|\bpayers?\b|patients?|medicare|medicaid|pharmac\w+|"
                  r"life sciences|\bhipaa\b|\behr\b|health plans?",
    "Enterprise SaaS": r"\bb2b\b|\bsaas\b|enterprise software|enterprise customers|\bcrm\b|\berp\b",
    "AI and machine learning": r"machine learning|artificial intelligence|generative ai|\bgen ?ai\b|\bllms?\b|"
                               r"large language models?|\bai\b",
    "Cloud and infrastructure": r"cloud (computing|infrastructure|platforms?|services|native|providers?)|"
                                r"data cent(er|re)s?|kubernetes|devops|developer platforms?|developer tools|\baws\b|"
                                r"\bgcp\b|azure|infrastructure as a service|\biaas\b|\bpaas\b",
    "Security": r"cyber ?security|\bsecurity products?|identity|zero trust|threat",
    "Mobility and automotive": r"automotive|autonomous|vehicles?|\bevs?\b|electric vehicles?|mobility|rideshare",
    "Media and entertainment": r"streaming|entertainment|music|creators?|publishers?|video",
    "Gaming": r"gaming|video games?",
    "Travel and hospitality": r"\btravel|hospitality|airlines?|hotels?|lodging",
    "Logistics": r"logistics|supply chain|fulfil?lment|warehouses?|last.mile|freight",
    "Hardware and semiconductors": r"semiconductors?|hardware|silicon|\bchips?\b|firmware|consumer electronics",
    "Telecom": r"telecom\w*|wireless|\b5g\b|carriers?",
    "Public sector": r"public sector|government|federal agenc\w+",
    "Education": r"education|edtech|students?|learning platforms?",
}
_IND_RX = {k: re.compile(r"\b(?:" + v + r")", re.I) for k, v in INDUSTRIES.items()}
ASK_CUE = re.compile(r"\b(experience|background|expertise|knowledge|familiarity|domain|industry|years|worked in|"
                     r"track record|understanding of)\b", re.I)
BOILER = re.compile(r"\b(benefits?|401\(?k|dental|vision|medical|paid time off|\bpto\b|equal (employment )?opportunity|"
                    r"disabilit\w+|veterans?|accommodations?|pay range|salary|compensation|insurance plans?|"
                    r"health insurance|wellness|parental leave|background check)\b", re.I)
NO_SPONSOR = re.compile(r"(not|unable to|cannot|can't|will not|won't|does not|doesn't|do not|don't|no longer)\s+"
                        r"(be able to\s+)?(offer|provide|sponsor|support|consider)\w*[^.]{0,60}?(sponsor\w*|visas?)|"
                        r"without (the )?(need for )?(current or future )?(employer |visa |company )?sponsorship|"
                        # added 31 Oct 2026: Capital One ("will not sponsor a new applicant ..."), PCG ("does not sponsor
                        # newly hired ..."), and "no immigration related support"
                        r"\b(will not|won't|does not|doesn't|do not|don't|cannot|can't|unable to|not able to|no longer)\s+"
                        r"(be able to\s+)?sponsor\b|not (offer|provide) any immigration[- ]related support|"
                        r"\bno (visa |immigration )?sponsorship|sponsorship (is |will )?not (be )?(available|offered|provided|possible)|"
                        r"(not|in)eligible for[^.]{0,30}sponsorship|not (be )?eligible for[^.]{0,30}sponsorship|"
                        r"sponsorship[^.]{0,40}(is|are) not (available|offered|provided|possible)|"
                        r"(must|will need to) be (legally )?authori[sz]ed to work[^.]{0,80}without[^.]{0,40}sponsor|"
                        r"(u\.?s\.? )?citizenship (is )?required|must be a u\.?s\.? citizen", re.I)
ASK_STRONG = re.compile(r"\b(experience (in|with|across|within)|background in|industry experience|domain (experience|"
                        r"expertise|knowledge)|expertise in|worked in|years (of experience )?in|deep knowledge of|"
                        r"familiarity with the)\b", re.I)
AV = 5  # version of the description analysis; saved roles are re-read once when it changes (4: boilerplate left out of skills, 19 Oct 2026; 5: more no-sponsorship and will-consider wording, 31 Oct 2026)
CS_DEGREE = re.compile(r"(bachelor\w*|\bb\.?s\.?\b|\bb\.?a\.?\b|degree)[^.]{0,80}computer science", re.I)
CS_ALT = re.compile(r"engineering|technical (field|discipline)|related (technical )?field|equivalent|quantitative", re.I)
ONSITE = re.compile(r"fully on-?site|on-?site (5|five) days|(5|five) days (a|per) week in (the |our )?office|"
                    r"in.office (5|five) days|this (role|position) is (fully )?on-?site|on-?site only|"
                    r"not eligible for remote|no remote", re.I)
YES_SPONSOR = re.compile(r"(visa |immigration )?sponsorship (is |may be )?available|we (will|can|do) sponsor|"
                         r"open to sponsor|will consider sponsor\w*|may (consider|offer|provide) (visa |immigration )?"
                         r"sponsor\w*|eligible for (visa |immigration )?sponsorship", re.I)
# Firms the user knows sponsor selectively: a firm-wide "we don't sponsor" line in their postings is not acted on
SELECTIVE_SPONSORS = {"pwc"}
CLEARANCE = re.compile(r"security clearance|\bts/sci\b|top secret|clearance (is )?required|active clearance", re.I)
YEARS = re.compile(r"(\d{1,2})\s*\+?\s*(?:-|to|–)?\s*(?:\d{1,2}\s*\+?\s*)?years?(?:\'|’)?\s+(?:of|in|experience|working|"
                   r"managing|leading|as|building|doing)", re.I)


def analyse(text):
    """Read a job description for industry signals, sponsorship wording, clearance and years asked for."""
    text = text or ""
    sentences = [s for s in re.split(r"(?<=[.!?;])\s+|\s+[•·▪]\s+", text) if s.strip()]
    asks, mentions = Counter(), Counter()
    for s in sentences:
        if BOILER.search(s):
            continue
        cue = bool(ASK_CUE.search(s))
        strong = bool(ASK_STRONG.search(s))
        for name, rx in _IND_RX.items():
            n = len(rx.findall(s))
            if n:
                mentions[name] += n
                if cue:
                    asks[name] += n * (2 if strong else 1)
    # "asks for" needs a clear request ("experience in payments") or the industry asked about more than once
    ind = [(k, "asks") for k, v in asks.most_common() if v >= 2][:2]
    for k, n in mentions.most_common():
        if len(ind) >= 2:
            break
        if n >= 3 and k not in dict(ind):
            ind.append((k, "mentions"))
    years = None
    for s in sentences:
        if not BOILER.search(s):
            for m in YEARS.finditer(s):
                y = int(m.group(1))
                if 1 <= y <= 25:
                    years = max(years or 0, y)
    sponsor = None
    if NO_SPONSOR.search(text):
        sponsor = "no"
    elif YES_SPONSOR.search(text):
        sponsor = "yes"
    import jdtext
    req, _pref = jdtext.split(text)
    scope = req or text  # the degree rule only counts as a knockout when it's a requirement
    cs = any(CS_DEGREE.search(s) and not CS_ALT.search(s) for s in re.split(r"(?<=[.!?;])\s+", scope))
    return {"industries": ind, "sponsor": sponsor, "clearance": bool(CLEARANCE.search(text)), "years": years,
            "cs_degree": cs, "onsite": bool(ONSITE.search(text)), "has_req": bool(req)}


def fetch_description(ats, token, job):
    if ats == "greenhouse":
        jid = job["uid"].split(":")[-1]
        data = fetch_json(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{jid}")
        return html_text(data.get("content", ""))
    if ats == "google":
        page = fetch_text(job["url"])
        text = html_text(re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", page))
        i = text.find(job["title"])
        return text[i:i + 15000] if i >= 0 else text[:15000]
    return ""


_desc_text = {"key": None, "value": {}}


def _stored_desc():
    """Descriptions saved earlier, so a re-read after an analysis change needs no new request."""
    try:
        st = os.stat(DESC_FILE)
        key = (st.st_mtime_ns, st.st_size)
    except OSError:
        return {}
    if _desc_text["key"] != key:
        try:
            with open(DESC_FILE, encoding="utf-8") as f:
                _desc_text.update(key=key, value=json.load(f))
        except (OSError, json.JSONDecodeError):
            _desc_text.update(key=key, value={})
    return _desc_text["value"]


def enrich(ats, token, jobs):
    """Attach an analysis to each matching US role not analysed before."""
    fetched = 0
    for j in jobs:
        if j["uid"] in _desc_done or not classify(j["title"])[0]:
            continue
        if us_status(j.get("location", ""), j.get("country", "")) == "Not US":
            continue
        desc = j.get("desc") or _stored_desc().get(j["uid"], "")
        if not desc and ats in ("greenhouse", "google") and fetched < DESC_CAP:
            fetched += 1
            try:
                desc = fetch_description(ats, token, j)
            except Exception:
                desc = ""
            time.sleep(0.2)
        if desc:
            j["desc"] = desc[:12000]
            j["ana"] = analyse(desc)
            try:
                import cvmatch
                w, req_terms = cvmatch.weights_for(j["desc"])
                j["ana"]["terms"], j["ana"]["req_terms"] = w, sorted(req_terms)
            except Exception:
                pass
    return jobs


def get_jobs(ats, token):
    """Returns a list of dicts: uid, title, url, location, country, posted (date or None)."""
    out = []
    if ats == "amazon":
        return amazon_jobs()
    if ats == "google":
        return google_jobs()
    if ats == "workday":
        return workday_jobs(token)
    if ats == "greenhouse":
        data = fetch_json(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs")
        for j in data.get("jobs", []):
            posted = (j.get("first_published") or j.get("updated_at") or "")[:10]
            out.append({"uid": f"gh:{token}:{j.get('id')}", "title": j.get("title", ""),
                        "url": j.get("absolute_url", ""), "location": (j.get("location") or {}).get("name", ""),
                        "country": "", "posted": posted})
    elif ats == "lever":
        data = fetch_json(f"https://api.lever.co/v0/postings/{token}?mode=json")
        for j in data if isinstance(data, list) else []:
            cat = j.get("categories") or {}
            locs = cat.get("allLocations") or ([cat.get("location")] if cat.get("location") else [])
            ms = j.get("createdAt")
            posted = (dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).date().isoformat()
                      if isinstance(ms, (int, float)) else "")
            desc = " ".join([j.get("descriptionPlain") or ""] +
                            [f"{x.get('text', '')}: {html_text(x.get('content', ''))}" for x in j.get("lists") or []] +
                            [j.get("additionalPlain") or ""])
            out.append({"uid": f"lv:{token}:{j.get('id')}", "title": j.get("text", ""), "url": j.get("hostedUrl", ""),
                        "location": "; ".join(x for x in locs if x), "country": j.get("country", "") or "",
                        "posted": posted, "desc": desc})
    elif ats == "ashby":
        data = fetch_json(f"https://api.ashbyhq.com/posting-api/job-board/{token}")
        for j in data.get("jobs", []):
            if j.get("isListed") is False:
                continue
            locs = [j.get("location") or ""] + [x.get("location", "") for x in j.get("secondaryLocations") or []]
            country = (((j.get("address") or {}).get("postalAddress") or {}).get("addressCountry") or "")
            out.append({"uid": f"ab:{token}:{j.get('id')}", "title": j.get("title", ""),
                        "url": j.get("jobUrl") or j.get("applyUrl") or "", "location": "; ".join(x for x in locs if x),
                        "country": country, "posted": (j.get("publishedAt") or "")[:10],
                        "desc": j.get("descriptionPlain") or html_text(j.get("descriptionHtml") or "")})
    return out


def squash(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


GENERIC = {"american", "global", "united", "general", "national", "international", "first", "technology",
           "technologies", "services", "health", "digital", "advanced", "systems", "capital", "financial"}
ALL = ("greenhouse", "lever", "ashby")


def candidates(search_name):
    """Likely board names, each with the boards it may be tried on. A first-word guess is only tried on
    Greenhouse, because Greenhouse reports the board's company name and the watcher can check it matches."""
    base = re.sub(r"^the\s+", "", search_name.strip(), flags=re.I)
    out = [(squash(base), ALL), (re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-"), ALL)]
    words = base.split()
    if len(words) > 1 and len(squash(words[0])) >= 6 and squash(words[0]) not in GENERIC:
        out.append((squash(words[0]), ("greenhouse",)))
    seen, res = set(), []
    for tok, ats in out:
        if tok and tok not in seen:
            seen.add(tok)
            res.append((tok, ats))
    return res


def same_company(board_name, search_name):
    a, b = squash(board_name), squash(search_name)
    n = min(len(a), len(b), 8)
    return n >= 2 and a[:n] == b[:n]


def detect(search_name):
    """Try the company's likely board names on all three.
    Returns (ats, token, board_name), (None, None, None) if there is no board, or ("error", ...) if the
    network failed so the answer is unknown."""
    network_trouble = False
    for token, boards in candidates(search_name):
        for ats in boards:
            try:
                jobs = get_jobs(ats, token)
            except urllib.error.HTTPError:
                continue
            except Exception:
                network_trouble = True
                continue
            if not jobs:
                continue
            name = ""
            if ats == "greenhouse":
                try:
                    name = fetch_json(f"https://boards-api.greenhouse.io/v1/boards/{token}").get("name", "")
                except Exception:
                    name = ""
                if not name or not same_company(name, search_name):
                    continue
            return ats, token, name
    if network_trouble:
        return "error", None, None
    return None, None, None


# ---------- the store ----------
_lock = threading.Lock()
state = {"running": False, "done": 0, "total": 0, "current": ""}


def load_store():
    try:
        with open(STORE, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    data.setdefault("boards", {})
    data.setdefault("jobs", {})
    data.setdefault("last_run", {})
    return data


def save_descriptions(new):
    """Keep the description text for later CV matching (data/descriptions.json)."""
    with _lock:
        try:
            with open(DESC_FILE, encoding="utf-8") as f:
                allp = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            allp = {}
        allp.update(new)
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(DESC_FILE + ".tmp", "w", encoding="utf-8") as f:
            json.dump(allp, f, ensure_ascii=False)
        os.replace(DESC_FILE + ".tmp", DESC_FILE)


def save_store(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = STORE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    os.replace(tmp, STORE)


def update(fn):
    """Load, change and save the store under a lock."""
    with _lock:
        data = load_store()
        result = fn(data)
        save_store(data)
        return result


def check_company(company, search_name, entry):
    """Work out the board (if needed) and fetch it. Returns (board_entry, jobs or None)."""
    key = company.lower()
    now = dt.datetime.now().isoformat(timespec="seconds")
    entry = dict(entry or {})
    entry["company"] = company
    if entry.get("source") == "none":
        return entry, None
    if key in BLOCKED:
        entry.update({"status": BLOCKED[key][0], "blocked": True, "hand_link": BLOCKED[key][1], "checked": now,
                      "ats": None, "token": None})
        return entry, None
    seed = SEED.get(key)
    if seed and (not entry.get("ats") or (key in SEED_REPLACES_AUTO and entry.get("source") == "auto")):
        entry.update({"ats": seed[0], "token": seed[1], "source": "seed", "board_name": ""})
    if seed and entry.get("source") == "seed" and entry.get("token") != seed[1]:
        entry.update({"ats": seed[0], "token": seed[1]})  # the checked list was updated
    tried_detect = False
    if not entry.get("ats") and not entry.get("detected_none"):
        ats, token, name = detect(search_name)
        tried_detect = True
        if ats == "error":
            entry.update({"status": "Couldn't reach the job boards to look. Will try again next check.", "checked": now})
            return entry, None
        if ats:
            entry.update({"ats": ats, "token": token, "board_name": name, "source": "auto"})
        else:
            entry.update({"detected_none": now, "status": "No Greenhouse, Lever or Ashby board found", "checked": now})
            return entry, None
    if not entry.get("ats"):
        return entry, None
    try:
        jobs = enrich(entry["ats"], entry["token"], get_jobs(entry["ats"], entry["token"]))
        entry.update({"status": "ok", "checked": now, "jobs_total": len(jobs)})
        return entry, jobs
    except urllib.error.HTTPError as e:
        msg = f"Board not found ({e.code})" if e.code == 404 else f"Feed error ({e.code})"
    except ValueError as e:  # a page or feed we could read but not understand
        msg = str(e)
    except Exception as e:  # network trouble, timeouts
        msg = f"Couldn't reach the feed ({type(e).__name__})"
    entry.update({"status": msg, "checked": now})
    if entry.get("source") in ("seed", "auto") and not tried_detect and "not found" in msg:
        entry.update({"ats": None, "token": None, "source": None})  # look again next time
    return entry, None


def run_check(companies, search_name):
    """companies: list of company names to watch. Runs in a background thread."""
    if state["running"]:
        return
    state.update({"running": True, "done": 0, "total": len(companies), "current": ""})
    started = dt.datetime.now().isoformat(timespec="seconds")
    try:
        store = load_store()
        boards = store["boards"]
        _known.clear()
        _known.update({uid: j.get("posted", "") for uid, j in store["jobs"].items() if j.get("posted")})
        _seen_before.clear()
        _seen_before.update(store["jobs"].keys())
        _desc_done.clear()
        _desc_done.update(uid for uid, j in store["jobs"].items()
                          if j.get("desc_done") and j.get("av") == AV and not j.get("relabel"))

        def one(company):
            state["current"] = company
            res = check_company(company, search_name(company), boards.get(company.lower()))
            state["done"] += 1
            return company, res

        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(one, companies))

        descs = {}

        def apply(data):
            today = dt.date.today().isoformat()
            for company, (entry, jobs) in results:
                key = company.lower()
                first_time = not data["boards"].get(key, {}).get("baseline_done")
                if jobs is None and entry.get("blocked"):
                    for rec in data["jobs"].values():
                        if rec.get("company", "").lower() == key and not rec.get("pasted"):
                            rec["open"] = False
                if jobs is not None:
                    entry["baseline_done"] = True
                    seen_now = set()
                    matches = 0
                    for j in jobs:
                        focus, label = classify(j["title"])
                        if not focus:
                            continue
                        matches += 1
                        seen_now.add(j["uid"])
                        old = data["jobs"].get(j["uid"])
                        rec = old or {"first_seen": today, "baseline": first_time, "dismissed": False, "added": False}
                        rec.update({"company": company, "title": j["title"], "url": j["url"],
                                    "location": j["location"], "where": us_status(j["location"], j["country"]),
                                    "posted": j["posted"], "nodate": j.get("nodate", False),
                                    "inventory": j.get("inventory", False),
                                    "focus": focus, "label": label, "last_seen": today,
                                    "open": True})
                        if j.get("ana"):
                            a_ = j["ana"]
                            rec.update(industries=a_["industries"], sponsor=a_["sponsor"],
                                       clearance=a_["clearance"], years=a_["years"], desc_done=True,
                                       terms=a_.get("terms", {}), req_terms=a_.get("req_terms", []), av=AV,
                                       cs_degree=a_.get("cs_degree"), onsite=a_.get("onsite"),
                                       has_req=a_.get("has_req"), relabel=False)
                            descs[j["uid"]] = j["desc"]
                        data["jobs"][j["uid"]] = rec
                    entry["matches"] = matches
                    for uid, rec in data["jobs"].items():
                        if rec.get("company", "").lower() == key and uid not in seen_now and not rec.get("pasted"):
                            rec["open"] = False  # roles you pasted in are never closed by a check
                data["boards"][key] = entry
            data["last_run"] = {"started": started, "finished": dt.datetime.now().isoformat(timespec="seconds"),
                                "companies": len(companies)}
        update(apply)
        if descs:
            save_descriptions(descs)
    finally:
        state.update({"running": False, "current": ""})


def start_check(companies, search_name):
    if state["running"]:
        return False
    threading.Thread(target=run_check, args=(companies, search_name), daemon=True).start()
    return True


def hours_since_last_run():
    fin = load_store().get("last_run", {}).get("finished")
    if not fin:
        return None
    return (dt.datetime.now() - dt.datetime.fromisoformat(fin)).total_seconds() / 3600
