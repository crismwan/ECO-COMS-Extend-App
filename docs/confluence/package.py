"""Turn filled HTML into: .docx (Word / Confluence 'Import Word document') and .doc (Confluence MHTML export format)."""
import base64, email.mime.multipart, email.mime.text, email.mime.image, os, re, subprocess, sys, shutil
from bs4 import BeautifulSoup
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
SRC, NAME = sys.argv[1], sys.argv[2]
OUT = 'out'
os.makedirs(OUT, exist_ok=True)
s = BeautifulSoup(open(SRC, encoding='utf-8').read(), 'html.parser')

# Word-friendly table borders (Confluence keeps its own styling on import)
for cg in s.find_all('colgroup'):
    cg.decompose()
for t in s.find_all('table'):
    t['border'] = '1'; t['cellpadding'] = '4'; t['cellspacing'] = '0'
    t['style'] = 'border-collapse:collapse;border:1px solid #A1AAB3;width:100%'
for c in s.find_all(['td', 'th']):
    c['style'] = (c.get('style', '') + ';border:1px solid #A1AAB3;padding:4px;vertical-align:top').lstrip(';')
# Image size: fit a 6.5 in text width
for im in s.find_all('img'):
    src = im['src']
    if src.startswith('img/'):
        w, h = Image.open(src).size
        want = min(int(im.get('width', 900)) * 96 // 100, 864)
        im['width'] = str(want); im['height'] = str(round(h * want / w))
        im['style'] = f'width:{want}px;height:{round(h * want / w)}px'

html = str(s)

# 1) .docx through LibreOffice with images embedded as data URIs
emb = re.sub(r'src="(img/[^"]+)"', lambda m: 'src="data:image/png;base64,' + base64.b64encode(open(m.group(1), 'rb').read()).decode() + '"', html)
tmp = os.path.join(OUT, NAME + '.html')
open(tmp, 'w', encoding='utf-8').write(emb)
subprocess.run(['soffice', '--headless', '--infilter=HTML (StarWriter)', '--convert-to', 'docx:MS Word 2007 XML', '--outdir', OUT, tmp],
               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
os.remove(tmp)
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.shared import Inches
dp = os.path.join(OUT, NAME + '.docx')
d = Document(dp)
for sec in d.sections:
    sec.orientation = WD_ORIENT.LANDSCAPE
    sec.page_width, sec.page_height = Inches(11), Inches(8.5)
    for m in ('left_margin', 'right_margin'): setattr(sec, m, Inches(0.75))
    for m in ('top_margin', 'bottom_margin'): setattr(sec, m, Inches(0.7))
from docx.oxml.ns import qn
FULL = 13680  # 9.5 in of text width, in twips
for tbl in d.element.body.iter(qn('w:tbl')):
    tw = tbl.find(qn('w:tblPr')).find(qn('w:tblW'))
    if tw is None or tw.get(qn('w:type')) != 'dxa':
        continue
    cur = int(tw.get(qn('w:w')))
    if cur < 5000:  # small tables (e.g. progress box) keep their size
        continue
    f = FULL / cur
    tw.set(qn('w:w'), str(FULL))
    for el in list(tbl.iter(qn('w:gridCol'))) + list(tbl.iter(qn('w:tcW'))):
        if el.get(qn('w:w')) and el.get(qn('w:type'), 'dxa') == 'dxa':
            el.set(qn('w:w'), str(int(int(el.get(qn('w:w'))) * f)))
d.save(dp)

# 2) .doc in the same MHTML form Confluence exports (images as related parts)
msg = email.mime.multipart.MIMEMultipart('related')
msg['Subject'] = 'Exported From Confluence'
mh = re.sub(r'src="img/([^"]+)"', r'src="file:///C:/\1"', html)
part = email.mime.text.MIMEText(mh, 'html', 'utf-8')
part.add_header('Content-Location', 'file:///C:/exported.html')
msg.attach(part)
for f in sorted(set(re.findall(r'src="img/([^"]+)"', html))):
    ip = email.mime.image.MIMEImage(open('img/' + f, 'rb').read(), 'png')
    ip.add_header('Content-Location', 'file:///C:/' + f)
    msg.attach(ip)
open(os.path.join(OUT, NAME + '.doc'), 'w').write(msg.as_string())
print('packaged', NAME)
