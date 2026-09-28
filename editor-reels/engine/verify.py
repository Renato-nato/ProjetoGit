"""Confere se TODA palavra falada continua com voz no video final (nada de fala cortada).

Uso (na pasta engine):  python verify.py specs_clip/v1.py        (ou specs_ref/v2.py)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine_ref import OUT, ROOT, Timeline, load_spec, load_words_all, safe_segments, voice_env  # noqa: E402

sp = Path(sys.argv[1])
spec = load_spec(sp)
suffix = "_clip" if "clip" in sp.parent.name else "_ref"
w = load_words_all(spec)
tl = Timeline(safe_segments(w, spec["keep"], voice_env(ROOT / "raw" / f"{spec['source']}.mp4"),
                            spec.get("gap", 0.28), spec.get("pad_in", 0.10), spec.get("pad_out", 0.12)))
env_out = voice_env(OUT / (spec["name"] + suffix) / f"{spec['name']}_nomusic.mp4")
bad = []
for x in w:
    mid = (x["start"] + x["end"]) / 2
    if not any(a <= mid < b for a, b in spec["keep"]):
        continue
    if not any(sg["s"] <= mid < sg["e"] for sg in tl.segs):
        bad.append(f"FORA DO CORTE: {x['text']} @{x['start']:.2f}")
        continue
    o = tl.to_out(x["start"])
    seg = env_out[int(o * 100):int((o + max(0.12, x["end"] - x["start"])) * 100)]
    if len(seg) and seg.max() < -35:
        bad.append(f"SEM VOZ: {x['text']} @{x['start']:.2f} (saida {o:.2f})")
print(f"{spec['name']}: {len(w)} palavras, problemas: {len(bad)}")
for b in bad:
    print("   ", b)
