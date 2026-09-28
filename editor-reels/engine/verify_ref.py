"""Confere o video final: toda palavra falada (inclusive as escondidas da legenda) tem voz no audio de saida;
gera folha com quadros nos b-rolls e nos textos."""
import subprocess
import sys
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine_ref import (OUT, ROOT, FPS, Timeline, load_spec, load_words_all, safe_segments, voice_env)  # noqa: E402

v = sys.argv[1]
spec = load_spec(Path(__file__).resolve().parent / "specs_ref" / f"{v}.py")
w = load_words_all(spec)
env_src = voice_env(ROOT / "raw" / f"{spec['source']}.mp4")
tl = Timeline(safe_segments(w, spec["keep"], env_src, 0.28, 0.10, 0.12))
final = OUT / (spec["name"] + "_ref") / f"{spec['name']}_nomusic.mp4"
env_out = voice_env(final)

missing = []
for x in w:
    mid = (x["start"] + x["end"]) / 2
    if not any(a <= mid < b for a, b in spec["keep"]):
        continue  # trecho descartado de proposito (tentativas)
    inside = any(sg["s"] <= mid < sg["e"] for sg in tl.segs)
    if not inside:
        missing.append(f"FORA DO CORTE: {x['text']} @{x['start']:.2f}")
        continue
    o = tl.to_out(x["start"])
    seg = env_out[int(o * 100):int((o + max(0.12, x["end"] - x["start"])) * 100)]
    if len(seg) and seg.max() < -35:
        missing.append(f"SEM VOZ: {x['text']} @{x['start']:.2f} (saida {o:.2f})")
hidden = [x for x in w if x.get("hide")]
print(f"{v}: {len(w)} palavras, {len(hidden)} escondidas da legenda ({' '.join(h['text'] for h in hidden)}), problemas: {len(missing)}")
for m in missing:
    print("   ", m)

tiles = []
ts = [tl.to_out(b["at"]) + b["dur"] / 2 for b in spec.get("broll", [])]
ts += [tl.to_out(e["until"]) - 0.2 for e in spec["type"]][:8]
for t in ts[:12]:
    png = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(OUT / (spec["name"] + "_ref") / f"{spec['name']}_REF.mp4"),
                          "-frames:v", "1", "-vf", "scale=220:-2", "-f", "image2pipe", "-vcodec", "png", "-"],
                         capture_output=True).stdout
    tiles.append(Image.open(BytesIO(png)).convert("RGB"))
S = Image.new("RGB", (220 * 6, 391 * 2))
for i, t in enumerate(tiles):
    S.paste(t, ((i % 6) * 220, (i // 6) * 391))
S.save(ROOT / "look" / f"verify_{v}.jpg")
