import sys, json, docx
from docx.shared import Pt, RGBColor
sys.path.insert(0,'.')
from script import STOPS
marks={m['n']:m for m in json.load(open('marks.json'))}
d=docx.Document('/mnt/user-data/uploads/ECO COMS/Presentations/ECO-COMS-Live-Demo-Script-2026-11-03-v2.docx')
body=d.element.body
for el in list(body):
    if not el.tag.endswith('sectPr'): body.remove(el)
def para(text, size=None, color=None, bold=None):
    p=d.add_paragraph(); r=p.add_run(text)
    if size: r.font.size=Pt(size)
    if color: r.font.color.rgb=RGBColor.from_string(color)
    if bold: r.bold=True
fmt=lambda s: f"{int(s//60)}:{int(s%60):02d}"
para("ECO-COMS live demo · 5 November 2026", 20, None, True)
para("Narration file: ECO-COMS-Live-Demo-Narration-2026-11-05.mp3 (8:54). Times below are where each stop starts in the audio. Nothing here submits except the optional Apply in stop 8; OK is pressed only where it is refused.", 11, '5E6878')
for st in STOPS:
    m=marks[st['n']]
    para(f"Stop {st['n']} · {st['title']}", 17, None, True)
    para(f"{fmt(m['start'])} – {fmt(m['start']+m['dur'])} · Open: {st['open']}", 11, '5E6878')
    for kind, text in st['items']:
        if kind=='say': para(text)
        elif kind=='do': para('▶ '+text, 10.5, '2F6FDB')
        else: para('▶ Safety: '+text, 10.5, 'B45309')
d.core_properties.title='ECO-COMS live demo script, 2026-11-05'
d.save('ECO-COMS-Live-Demo-Script-2026-11-05.docx'); print('ok')
