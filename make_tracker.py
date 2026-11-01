import sys, openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

src, out = sys.argv[1], sys.argv[2]
wb = openpyxl.load_workbook(src)
HEAD = PatternFill("solid", fgColor="FFF2CC")
BOLD = Font(bold=True)

def sheet(name, headers, widths, tab):
    ws = wb.create_sheet(name)
    ws.append(headers)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
        c = ws.cell(1, i); c.font = BOLD; c.fill = HEAD
        c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"
    ws.sheet_properties.tabColor = tab
    return ws

def dv(ws, formula, col, warn=False):
    d = DataValidation(type="list", formula1=formula, allow_blank=True)
    if warn:
        d.errorStyle = "warning"
    d.showErrorMessage = True
    ws.add_data_validation(d)
    d.add(f"{col}2:{col}500")

def datefmt(ws, cols):
    for col in cols:
        for r in range(2, 501):
            ws[f"{col}{r}"].number_format = "yyyy-mm-dd"

ppl = sheet("People",
    ["Company", "Person", "Role", "How found", "LinkedIn link", "Stage", "Stage date", "Last contact",
     "Sponsorship answer", "Referral offered", "Chat date", "Notes"],
    [26, 22, 24, 22, 32, 16, 12, 12, 40, 14, 12, 40], "4472C4")
dv(ppl, '"found,request sent,accepted,message sent,replied,chat booked,chat done,thank-you sent,follow-up sent,dead"', "F")
dv(ppl, '"Yes,No"', "J")
dv(ppl, "=Companies!$B$2:$B$301", "A", warn=True)
datefmt(ppl, "GHK")

apps = sheet("Applications",
    ["Company", "Role", "Link", "Focus", "Deadline", "Date applied", "Status", "Referred by",
     "Next step date", "Next step", "Notes"],
    [26, 30, 32, 12, 12, 12, 14, 20, 14, 30, 40], "70AD47")
dv(apps, '"Product,Strategy"', "D")
dv(apps, '"not applied,applied,interview,offer,rejected,withdrawn"', "G")
dv(apps, "=Companies!$B$2:$B$301", "A", warn=True)
datefmt(apps, "EFI")

st = sheet("Settings", ["Rule", "Value", "Key (do not edit)"], [64, 14, 28], "A5A5A5")
rows = [
 ("Days before an unanswered connection request needs a nudge", 7, "request_nudge_days"),
 ("Days after a request is accepted before you should have sent a message", 2, "accepted_message_days"),
 ("Days after a first message with no reply before a polite follow-up", 5, "message_followup_days"),
 ("Days after a follow-up with no reply before marking the person dead", 5, "second_silence_days"),
 ("Days after a chat before the thank-you counts as overdue", 1, "thankyou_due_days"),
 ("Days after a thank-you before you check back", 14, "checkback_days"),
 ("Flag an application when the deadline is within this many days", 7, "deadline_warning_days"),
 ("Filing data runs up to (shown on company pages)", "2026-06-30", "data_through"),
]
for r in rows:
    st.append(r)
    st.cell(st.max_row, 2).fill = HEAD
    st.cell(st.max_row, 3).font = Font(color="808080")

order = ["Companies", "People", "Applications", "Settings", "Read me", "Excluded", "Entity groups"]
wb._sheets = [wb[n] for n in order]
wb.active = 0
wb.save(out)
