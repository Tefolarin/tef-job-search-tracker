"""Split a job description into what it requires and what it only prefers.

Headings are recognised only when they look like headings (start of a line or sentence, followed by a colon, full stop
or line break), so prose like "that means you have an opportunity" isn't mistaken for a "You have" section.
Inside a requirements section, a sentence that says "is a plus", "preferred", "nice to have" or "ideally" counts as
preferred.
"""
import re

REQ = (r"basic qualifications|minimum qualifications|required qualifications|qualifications|requirements|"
       r"what you(?:'|’)?ll need|what you need|what you bring|what you(?:'|’)?ll bring|you(?:'|’)?ll have|you have|"
       r"who you are|about you|must haves?|what we(?:'|’)?re looking for|we(?:'|’)?re looking for|skills (?:and|&) experience|"
       r"your experience|experience you(?:'|’)?ll bring")
PREF = (r"preferred qualifications|preferred skills|preferred experience|preferred|nice to haves?|bonus points|bonus|"
        r"ideally|desired qualifications|desired|pluses|even better|it(?:'|’)?s a plus if|extra credit")
STOP = (r"responsibilities|what you(?:'|’)?ll do|what you will do|the role|about the role|about the team|about us|"
        r"about [a-z]+|benefits|perks|compensation|pay range|salary|our commitment|equal (?:employment )?opportunity|"
        r"why join|life at|how we work|what we offer|additional information|location")
_HEAD = re.compile(r"(?:^|[\n.!?•]\s*|\s{2,})(" + "|".join([REQ, PREF, STOP]) + r")\s*(?::|\.(?=\s)|\n|\s-\s|\s•)",
                   re.I)
_REQ_RX = re.compile(r"^(?:" + REQ + r")$", re.I)
_PREF_RX = re.compile(r"^(?:" + PREF + r")$", re.I)
PLUS = re.compile(r"\b(is a plus|a plus\b|are a plus|preferred|nice to have|bonus|ideally|desirable|"
                  r"is helpful|would be great|is an advantage|considered a plus)\b", re.I)


def split(text):
    """Returns (required_text, preferred_text). Both are empty if the description has no such headings."""
    text = text or ""
    marks = []
    for m in _HEAD.finditer(text):
        h = m.group(1).strip().lower()
        kind = "req" if _REQ_RX.match(h) else "pref" if _PREF_RX.match(h) else "stop"
        marks.append((m.start(1), m.end(), kind))
    if not any(k in ("req", "pref") for _, _, k in marks):
        return "", ""
    req, pref = [], []
    for i, (start, body_start, kind) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        body = text[body_start:end]
        if kind == "pref":
            pref.append(body)
        elif kind == "req":
            for s in re.split(r"(?<=[.!?;])\s+|\s+[•·▪]\s+|\s+-\s+", body):
                (pref if PLUS.search(s) else req).append(s)
    return " ".join(req).strip(), " ".join(pref).strip()


# ---------- leaving out what isn't about the job ----------
# Company blurbs, benefits, pay and legal text mention words like "experiment", "advertise" or "regulations" that
# have nothing to do with the skills a role needs. clean() drops them before skills are counted.
COMPANY_HEAD = re.compile(
    r"(?:^|\n|[.!?]\s+|\s{2,})((?:why (?:join|work at|work for)?\s*[a-z]*|who we are|about us|about the company|"
    r"about (?!the role|the team|this role|the job|the position|the opportunity|you\b|your\b|the work)[a-z][a-z&.\- ]{1,30}|"
    r"our commitment[a-z ]*|equal (?:employment )?opportunit\w*[a-z ]*|benefits[a-z &]*|perks[a-z &]*|what we offer|"
    r"compensation[a-z &]*|pay (?:range|transparency)[a-z ]*|salary[a-z ]*|message to (?:all )?applicants[a-z .]*|"
    r"life at [a-z]+|our culture|our values|our mission|disclaimer|privacy notice|accommodations?))\s*[?:]?\s*(?=\n|:)",
    re.I)
_NEXT = re.compile(r"(?:^|[\n.!?•]\s*|\s{2,})(" + "|".join([REQ, PREF, r"responsibilities|what you(?:'|’)?ll do|what you will do|"
                   r"the role|about the role|about (?:your|this) role|your role|about the (?:team|job|position|opportunity|work)|"
                   r"the opportunity|key job responsibilities|a day in the life"]) +
                   r")\s*(?::|\.(?=\s)|\n|\s-\s|\s•)", re.I)
BOILER_SENTENCE = re.compile(
    r"\b(401\(?k|dental|paid time off|\bpto\b|vacation|sick (time|leave)|parental leave|health insurance|"
    r"equal (employment )?opportunit\w+|affirmative action|disabilit\w+|veterans?|reasonable accommodations?|"
    r"protected (veteran|class|characteristic)|regardless of|race, |sexual orientation|gender identity|"
    r"pay range|base (pay|salary)|salary range|compensation (range|package)|incentive (pay|compensation|target)|"
    r"background checks?|e-verify|fair chance|arrest (and|or) conviction|privacy (notice|policy)|"
    r"applicable (federal|state|local|law|laws)|laws and regulations|this posting|job posting|apply(ing)? (now|today)|"
    r"we experiment|fueled by|join us|our (culture|mission|values|people) (is|are)|benefits (package|include|program)|"
    r"comprehensive benefits|world.class benefits|is an equal|employer of choice)\b", re.I)


def clean(text):
    """The description without company blurbs, benefits, pay or legal text."""
    text = text or ""
    cut = []
    for m in COMPANY_HEAD.finditer(text):
        nxt = _NEXT.search(text, m.end())
        cut.append((m.start(1), nxt.start(1) if nxt else len(text)))
    if cut:
        keep, pos = [], 0
        for a, b in sorted(cut):
            if a >= pos:
                keep.append(text[pos:a])
                pos = b
            else:
                pos = max(pos, b)
        keep.append(text[pos:])
        text = " ".join(keep)
    parts = re.split(r"(?<=[.!?;])\s+|\n+", text)
    return "\n".join(s for s in parts if s.strip() and not BOILER_SENTENCE.search(s))
