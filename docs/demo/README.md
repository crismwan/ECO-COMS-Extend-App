# Live demo narration (2026-11-05)

`script.py` holds the nine demo stops (click path, narration, safety notes). `tts.py` turns the narration into
`narration.wav` plus `marks.json` (where each stop starts). The voice is Kokoro, an offline model, so it works
without internet access to a voice service:

```
pip install kokoro-onnx soundfile
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
python3 tts.py am_michael
ffmpeg -i narration.wav -af loudnorm=I=-16:TP=-1.5:LRA=11 -ar 24000 -ac 1 -b:a 96k narration.mp3
```

Codes such as X:BPMS(COMS) are given spoken forms in `tts.py` (SAY list), so the voice doesn't read punctuation.
Delivered files: ECO-COMS-Live-Demo-Narration-2026-11-05.mp3 (9:03; stop 4 redone for the Shell Org Manager application bar) and ECO-COMS-Live-Demo-Script-2026-11-05.docx/.pdf.
