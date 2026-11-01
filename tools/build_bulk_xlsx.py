#!/usr/bin/env python3
"""Builds the validated Excel template for Bulk Role Changes: docs/templates/ECO-COMS-Bulk-Role-Template.xlsx.

Ideas taken from the Mass Student Appointment Studio template (2026-11-01): a header block saying what each
column needs (required, format, example), drop-downs, format checks with plain error messages, cross-field
rules (ADD vs REMOVE), duplicate detection, shading for cells not to edit, a version stamp, frozen panes.

The sheet must still save as a CSV the BulkRoleApply orchestration reads:
- columns A-H stay in the order of the Workday template (Action, Role, Role WID, Organization, Organization WID,
  Position, Position ID, Assignee WID); the orchestration reads them by index;
- it acts only on rows whose Action is exactly ADD or REMOVE, so the 6 header rows (column A never holds
  those words) are skipped;
- data rows hold no formulas and no direct formatting (shading is conditional formatting), so Excel's CSV
  has no padding rows. The per-row checks live on the Row Checks sheet, which isn't saved into the CSV
  (Excel saves only the active sheet). The 200 cap counts ADD/REMOVE rows, not lines (BulkRoleApply).

Pre-filled (EIB-style "get"): `--data rows.json` writes every current role assignment from row 7, Action empty,
so users only mark REMOVE or add ADD rows. tools/publish_template.js builds rows.json from Workday and
publishes the result to the app's download link (COMSBulkTemplate). Without --data the template is blank.

  python3 tools/build_bulk_xlsx.py [--data rows.json --asof "2026-11-01 08:00 PST"] [--out file.xlsx]
"""
import json, os, sys
from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

VERSION = 'v2 · 2026-11-01'
opt = lambda n: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else None
OUT = opt('--out') or os.path.join(os.path.dirname(__file__), '..', 'docs', 'templates', 'ECO-COMS-Bulk-Role-Template.xlsx')
ROWS = json.load(open(opt('--data'))) if opt('--data') else []
ASOF = opt('--asof')
MAX_CHANGES = 1000                       # safety limit per file (BulkRoleApply): Workday's 60-minute process limit
FIRST = 7
LAST = FIRST + max(len(ROWS) + 300, 300) - 1   # every current assignment plus room for ADD rows
RC = "'Role Changes'"
F = 'Arial'

fill = lambda c: PatternFill('solid', start_color=c, end_color=c)
NAVY, BLUE, PALE, GREY, YELLOW, RED, GREEN = '1F3864', 'D9E2F3', 'EEF3FA', 'EDEDED', 'FFF2CC', 'F8CBAD', 'E2EFDA'
thin = Side(style='thin', color='BFBFBF')
box = Border(left=thin, right=thin, top=thin, bottom=thin)

COLS = [  # header, used for, required, format, example, width, prompt
    ('Action', 'Every change', 'Required to change the row', 'ADD or REMOVE (drop-down)', 'Example: ADD', 17,
     'ADD gives the position this role. REMOVE takes it off. Leave empty for no change.'),
    ('Role', 'Reference', 'From the template', 'Text', 'X:BPMS(ODMT):ROLE:ADVISORS', 34, 'Role name, for reading only.'),
    ('Role WID', 'Every change', 'Required (don\'t edit)', '32-character WID', '2ea70ec010b41001b75f3d8882270000', 36,
     'Copied from the Workday template. Don\'t edit it.'),
    ('Organization', 'Reference', 'From the template', 'Text', 'X:BPMS(ODMT) Document Access (varies)', 38, 'Organization name, for reading only.'),
    ('Organization WID', 'Every change', 'Required (don\'t edit)', '32-character WID', 'e6ca8683b78d10017d0876c383b70000', 36,
     'Copied from the Workday template. Don\'t edit it.'),
    ('Position', 'Reference', 'Optional', 'Text', '(Workday fills in the name)', 40, 'Position name, for reading only. Workday looks up the real name.'),
    ('Position ID', 'ADD rows', 'Required for ADD', 'P- then digits', 'P-00123', 14,
     'For ADD, type the ID of the position that should get the role, e.g. P-00123.'),
    ('Assignee WID', 'REMOVE rows', 'Required for REMOVE; empty for ADD', '32-character WID', '(empty on ADD rows)', 36,
     'Copied from the Workday template. Needed to REMOVE. Clear it on ADD rows.'),
]
L = 'ABCDEFGH'

wb = Workbook()
ws = wb.active
ws.title = 'Role Changes'

# ── header block ──
ws['A1'] = (f'ECO-COMS Bulk Role Changes · template {VERSION} · current assignments as of {ASOF} (refresh: download again)' if ASOF
            else f'ECO-COMS Bulk Role Changes · template {VERSION} · paste Workday template rows from row {FIRST} with Paste Values')
ws['A1'].font = Font(name=F, bold=True, size=12, color='FFFFFF')
ws.merge_cells('A1:H1')
for col in L:
    ws[f'{col}1'].fill = fill(NAVY)
labels = ['Used for', 'Required', 'Format', 'Example']
for i, (h, used, req, fmt, ex, width, prompt) in enumerate(COLS):
    c = L[i]
    ws.column_dimensions[c].width = width
    for r, v in zip((2, 3, 4, 5), (used, req, fmt, ex)):
        cell = ws[f'{c}{r}']
        cell.value = v
        cell.font = Font(name=F, size=9, italic=(r == 5), color='595959' if r != 3 else '000000', bold=(r == 3 and 'Required' in v))
        cell.fill = fill(PALE)
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        cell.border = box
    hc = ws[f'{c}6']
    hc.value = h
    hc.font = Font(name=F, bold=True, size=10)
    hc.fill = fill(BLUE)
    hc.border = box
    hc.alignment = Alignment(vertical='center')
    hc.comment = Comment(prompt, 'ECO-COMS')
for r, lab in zip((2, 3, 4, 5), labels):  # row labels go in a comment on column A so column A never holds ADD/REMOVE
    ws[f'A{r}'].comment = Comment(f'This row: {lab}', 'ECO-COMS')
ws.row_dimensions[1].height = 22
for r in (2, 3, 4):
    ws.row_dimensions[r].height = 30
ws.freeze_panes = f'B{FIRST}'

# ── summary (columns J-K, header rows only, so the CSV gets no extra lines) ──
ws.column_dimensions['I'].width = 3
ws.column_dimensions['J'].width = 22
ws.column_dimensions['K'].width = 34
A_, C_, E_, G_ = (f"${c}${FIRST}:${c}${LAST}" for c in 'ACEG')
CHK = f"'Row Checks'!$E${FIRST}:$E${LAST}"
summary = [
    ('Positions to add', f'=SUMPRODUCT(--(UPPER(TRIM({A_}))="ADD"))'),
    ('Positions to remove', f'=SUMPRODUCT(--(UPPER(TRIM({A_}))="REMOVE"))'),
    ('Rows with problems', f'=SUMPRODUCT(({CHK}<>"")*({CHK}<>"OK"))'),
    (f'Changes (max {MAX_CHANGES})', '=K2+K3'),
    ('Status', '=IF(K4>0,"Fix the rows marked red (see Row Checks)",IF(K5=0,"No changes yet: type ADD or REMOVE",'
               f'IF(K5>{MAX_CHANGES},"Too many changes: split them over several files","Ready: save this sheet as CSV")))'),
]
for i, (lab, f) in enumerate(summary, start=2):
    ws[f'J{i}'] = lab
    ws[f'J{i}'].font = Font(name=F, size=9, bold=True)
    ws[f'K{i}'] = f
    ws[f'K{i}'].font = Font(name=F, size=10, bold=(lab == 'Status'))
    for c in 'JK':
        ws[f'{c}{i}'].border = box
        ws[f'{c}{i}'].fill = fill(PALE)
ws['J1'] = 'Summary'
ws['J1'].font = Font(name=F, bold=True, color='FFFFFF')
ws['J1'].fill = fill(NAVY)
ws.merge_cells('J1:K1')

# ── pre-filled current assignments (values only: no formatting, so the CSV stays clean) ──
for i, r in enumerate(ROWS):
    for j, key in enumerate(('role', 'roleWid', 'org', 'orgWid', 'position', 'positionId', 'assigneeWid'), start=2):
        ws.cell(FIRST + i, j, r.get(key) or None)

# ── data validation (no cell contents, so the CSV is unaffected) ──
def dv(rng, **kw):
    d = DataValidation(allow_blank=True, showErrorMessage=True, showInputMessage=True, **kw)
    d.add(rng)
    ws.add_data_validation(d)
dv(f'A{FIRST}:A{LAST}', type='list', formula1='"ADD,REMOVE"', errorTitle='Action',
   error='Choose ADD or REMOVE, or leave the cell empty for no change.', promptTitle='Action', prompt=COLS[0][6])
wid_rule = lambda c: f'=OR(TRIM({c}{FIRST})="",AND(LEN(TRIM({c}{FIRST}))=32,ISERROR(SEARCH(" ",TRIM({c}{FIRST})))))'
for c, name in (('C', 'Role WID'), ('E', 'Organization WID'), ('H', 'Assignee WID')):
    dv(f'{c}{FIRST}:{c}{LAST}', type='custom', formula1=wid_rule(c), errorStyle='warning', errorTitle=name,
       error=f'{name} is a 32-character code copied from the Workday template. It looks changed. Copy the row from the template again.',
       promptTitle=name, prompt=COLS['ABCDEFGH'.index(c)][6])
dv(f'G{FIRST}:G{LAST}', type='custom', formula1=f'=OR(TRIM(G{FIRST})="",AND(LEFT(TRIM(G{FIRST}),2)="P-",LEN(TRIM(G{FIRST}))>2,ISNUMBER(--MID(TRIM(G{FIRST}),3,20))))',
   errorTitle='Position ID', error='Type the position ID as P- followed by digits, e.g. P-00123.', promptTitle='Position ID', prompt=COLS[6][6])

# ── conditional formatting: input cells, don't-edit cells, problems ──
data = f'A{FIRST}:H{LAST}'
bad = f"AND(TRIM($A{FIRST})<>\"\",'Row Checks'!$E{FIRST}<>\"OK\")"
ws.conditional_formatting.add(data, FormulaRule(formula=[bad], fill=fill(RED), stopIfTrue=True))
ws.conditional_formatting.add(f'A{FIRST}:A{LAST}', FormulaRule(formula=[f"'Row Checks'!$E{FIRST}=\"OK\""], fill=fill(GREEN), stopIfTrue=True))
ws.conditional_formatting.add(f'A{FIRST}:A{LAST}', FormulaRule(formula=[f'LEN($C{FIRST})>0'], fill=fill(YELLOW)))
ws.conditional_formatting.add(f'G{FIRST}:G{LAST}', FormulaRule(formula=[f'UPPER(TRIM($A{FIRST}))="ADD"'], fill=fill(YELLOW)))
for c in 'CEH':
    ws.conditional_formatting.add(f'{c}{FIRST}:{c}{LAST}', FormulaRule(formula=[f'LEN(${c}{FIRST})>0'], fill=fill(GREY), font=Font(color='7F7F7F')))
ws.conditional_formatting.add('K6', FormulaRule(formula=['LEFT(K6,5)="Ready"'], fill=fill(GREEN)))
ws.conditional_formatting.add('K6', FormulaRule(formula=['LEFT(K6,5)<>"Ready"'], fill=fill(YELLOW)))

# ── Row Checks sheet: one plain-language message per data row ──
ck = wb.create_sheet('Row Checks')
for c, (h, w) in zip('ABCDE', (('Row', 7), ('Action', 10), ('Role', 34), ('Position ID', 13), ('Check', 70))):
    ck[f'{c}{FIRST - 1}'] = h
    ck[f'{c}{FIRST - 1}'].font = Font(name=F, bold=True, color='FFFFFF')
    ck[f'{c}{FIRST - 1}'].fill = fill(NAVY)
    ck.column_dimensions[c].width = w
ck['A1'] = 'Row Checks: one line per row of Role Changes, on the same row number'
ck['A1'].font = Font(name=F, bold=True, size=12)
ck['A2'] = 'Rows with an empty Action are left as they are and show no check. This sheet is not part of the CSV.'
ck['A2'].font = Font(name=F, italic=True, size=9, color='595959')
ck.freeze_panes = f'A{FIRST}'
for i in range(FIRST, LAST + 1):
    r = i
    a, c, e, g, h = (f"{RC}!{x}{i}" for x in 'ACEGH')
    act = f'UPPER(TRIM({a}))'
    other = f'IF({act}="ADD","REMOVE","ADD")'
    same = f'{RC}!{A_},{{}},{RC}!{C_},{c},{RC}!{E_},{e},{RC}!{G_},{g}'
    dup = (f'IF(COUNTIFS({same.format(a)})>1,"Duplicate: the same change appears more than once",'
           f'IF(COUNTIFS({same.format(other)})>0,"This position is both added and removed on this role",'
           f'IF(AND({act}="ADD",SUMPRODUCT((TRIM({RC}!{A_})="")*({RC}!{C_}={c})*({RC}!{E_}={e})*(TRIM({RC}!{G_})=TRIM({g})))>0),"Already holds this role (an unchanged row shows it): nothing to add","OK")))')
    pid_ok = f'AND(LEFT(TRIM({g}),2)="P-",LEN(TRIM({g}))>2,ISNUMBER(--MID(TRIM({g}),3,20)))'
    msg = (f'=IF(TRIM({a})="","",'
           f'IF(AND({act}<>"ADD",{act}<>"REMOVE"),"Action must be ADD, REMOVE or empty",'
           f'IF(LEN(TRIM({c}))<>32,"Role WID is missing or changed: copy the row from the Workday template",'
           f'IF(LEN(TRIM({e}))<>32,"Organization WID is missing or changed: copy the row from the Workday template",'
           f'IF({act}="ADD",'
           f'IF(NOT({pid_ok}),"ADD needs a Position ID like P-00123",'
           f'IF(TRIM({h})<>"","Clear Assignee WID on ADD rows (it belongs to the row you copied)",{dup})),'
           f'IF(LEN(TRIM({h}))<>32,"REMOVE needs the Assignee WID from the template row",{dup}))))))')
    ck[f'A{r}'] = i
    ck[f'B{r}'] = f'=IF(TRIM({a})="","",{act})'
    ck[f'C{r}'] = f'=IF(TRIM({a})="","",{RC}!B{i})'
    ck[f'D{r}'] = f'=IF(TRIM({a})="","",{g})'
    ck[f'E{r}'] = msg
    for col in 'ABCDE':
        ck[f'{col}{r}'].font = Font(name=F, size=9)
ck.conditional_formatting.add(f'E{FIRST}:E{LAST}', FormulaRule(formula=[f'E{FIRST}="OK"'], fill=fill(GREEN)))
ck.conditional_formatting.add(f'E{FIRST}:E{LAST}', FormulaRule(formula=[f'AND(E{FIRST}<>"",E{FIRST}<>"OK")'], fill=fill(RED)))

# ── How to use ──
hw = wb.create_sheet('How to use')
hw.column_dimensions['A'].width = 4
hw.column_dimensions['B'].width = 110
steps = [
    ('ECO-COMS Bulk Role Changes template ' + VERSION, True),
    ('', False),
    ((f'1. Role Changes already lists every current role assignment on shell organizations (as of {ASOF}), one row per position. '
      'Download a fresh copy from Bulk Role Changes → Download Template if that is not recent enough.') if ASOF else
     '1. In ECO-COMS, open Bulk Role Changes → Download Template and export the grid to Excel (the export icon).', False),
    (('2. Filter or search the sheet for the roles you want to change. Rows you leave alone are not changed.') if ASOF else
     (f'2. Copy the data rows from that export (not its header) and paste them on Role Changes at cell A{FIRST} with Paste Values '
      '(Ctrl+Shift+V, or Paste Special → Values). A normal paste would remove the checks.'), False),
    ('3. Type REMOVE in Action on the rows to take a position off a role.', False),
    ('4. To add a position: copy a row of the same role and organization to an empty row at the bottom, type ADD in Action, type the new Position ID (e.g. P-00123) and clear Assignee WID and Position.', False),
    ('5. Leave Action empty on rows you don\'t want to change. Don\'t edit the grey WID columns, and keep the columns in this order.', False),
    ('6. Fix anything marked red. Row Checks says what is wrong with each row; the Summary (top right of Role Changes) must say "Ready".', False),
    ('7. With the Role Changes sheet selected, File → Save As → CSV (Excel saves only the sheet you are on).', False),
    ('8. Upload the CSV on Bulk Role Changes, run Validate only first, check the results, then run it for real.', False),
    ('', False),
    ('What the colours mean', True),
    ('Yellow: cells you fill in (Action, and Position ID on ADD rows). Grey: copied from Workday, don\'t edit. '
     'Green Action: the row passed the checks. Red row: a problem; Row Checks says which.', False),
    ('', False),
    ('What these checks cover', True),
    ('Format only: Action values, WIDs present and unchanged in length, Position ID format, Assignee WID on REMOVE rows and not on ADD rows, '
     'duplicate rows, a position both added and removed, and adding a position that already holds the role. '
     'Whether a position exists, is filled, or may hold the role is checked by Workday in the Validate only run.', False),
    ('', False),
    ('Limits', True),
    (f'At most {MAX_CHANGES} ADD or REMOVE rows per file; unchanged rows don\'t count. Split larger changes into several files.', False),
    ('The 6 header lines are ignored by ECO-COMS: it acts only on rows whose Action is exactly ADD or REMOVE.', False),
]
for i, (t, bold) in enumerate(steps, start=1):
    hw[f'B{i}'] = t
    hw[f'B{i}'].font = Font(name=F, bold=bold, size=12 if i == 1 else 10)
    hw[f'B{i}'].alignment = Alignment(wrap_text=True, vertical='top')

wb.active = 0
os.makedirs(os.path.dirname(OUT), exist_ok=True)
wb.save(OUT)
print('wrote', os.path.relpath(OUT))
