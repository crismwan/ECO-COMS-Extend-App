import re, sys, json, numpy as np, soundfile as sf
sys.path.insert(0, '.')
from script import STOPS
from kokoro_onnx import Kokoro
K = Kokoro('kokoro-v1.0.onnx', 'voices-v1.0.bin')
VOICE = sys.argv[1] if len(sys.argv) > 1 else 'am_michael'
SAY = [  # spoken forms, longest first
 (r'X:BPMS\(COMS\)', 'X B P M S, Coms in brackets'), (r'X:BPMS\(TST\)', 'X B P M S, T S T in brackets'),
 (r'X:NEWAPP', 'X New App'), (r'X:META', 'X Meta'), (r'X:SHELL', 'X Shell'), (r'X:BPMS', 'X B P M S'),
 (r'\bRBAC\b', 'R back'), (r'\bISC\b', 'I S C'), (r'\bEIB\b', 'E I B'), (r'\bAAA\b', 'triple A'), (r'\bCSV\b', 'C S V'),
 (r'\bADVISORS\b', 'Advisors'), (r'\bSTAFF\b', 'Staff'), (r'\bCOMS\b', 'Coms'), (r'\bOK\b', 'O K'), (r'\bID\b', 'I D'),
 (r'\bIDs\b', 'I Ds'), (r'\bX:', 'X '), (r'Appian', 'Appian')]
def speak(t):
    for a, b in SAY: t = re.sub(a, b, t)
    return t
SR = 24000
def sil(s): return np.zeros(int(SR * s), dtype=np.float32)
out = []; marks = []; t = 0.0
for st in STOPS:
    seg = [sil(0.6)]
    prev = None
    for kind, text in st['items']:
        if kind == 'do': prev = 'do'; continue
        if kind != 'say': continue
        if prev == 'do' and len(seg) > 1: seg.append(sil(2.2))   # time for the click
        elif len(seg) > 1: seg.append(sil(0.55))
        a, _ = K.create(speak(text), voice=VOICE, speed=1.0, lang='en-us'); seg.append(a.astype(np.float32)); prev = 'say'
    seg.append(sil(1.2))
    a = np.concatenate(seg); sf.write(f"stop{st['n']}.wav", a, SR)
    marks.append({'n': st['n'], 'title': st['title'], 'start': round(t, 1), 'dur': round(len(a) / SR, 1)}); t += len(a) / SR
    out.append(a)
sf.write('narration.wav', np.concatenate(out), SR)
json.dump(marks, open('marks.json', 'w'), indent=1)
for m in marks: print(f"{m['n']} {int(m['start']//60)}:{int(m['start']%60):02d} ({m['dur']}s) {m['title']}")
print('total', round(t/60, 2), 'min')
