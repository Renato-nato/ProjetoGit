"""Transcreve um video bruto com tempo de cada palavra (roda local, sem nuvem).

Uso (na pasta editor-reels, venv ativo):
    python tools/transcribe.py raw/v5_nome_do_video.mp4            # modelo "medium" (bom em portugues)
    python tools/transcribe.py raw/v5_nome_do_video.mp4 --model small   # mais rapido, menos preciso
Gera edit/transcripts/<nome>.json no formato que o motor le.
"""
import json
import sys
from pathlib import Path

from faster_whisper import WhisperModel

ROOT = Path(__file__).resolve().parent.parent

src = Path(sys.argv[1])
model_name = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else "medium"
model = WhisperModel(model_name, device="auto", compute_type="int8")
segments, _ = model.transcribe(str(src), language="pt", word_timestamps=True, vad_filter=False,
                               condition_on_previous_text=False)
words = []
for seg in segments:
    for w in seg.words or []:
        words.append({"type": "word", "text": w.word.strip(), "start": round(w.start, 2), "end": round(w.end, 2),
                      "speaker_id": None})
out = ROOT / "edit" / "transcripts" / f"{src.stem}.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"words": words}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"{len(words)} palavras -> {out}")
# texto com tempos, para montar o spec
line, t0 = [], None
for w in words:
    t0 = w["start"] if t0 is None else t0
    line.append(w["text"])
    if w["text"][-1:] in ".?!" or len(line) > 12:
        print(f"{t0:6.2f}  " + " ".join(line))
        line, t0 = [], None
if line:
    print(f"{t0:6.2f}  " + " ".join(line))
