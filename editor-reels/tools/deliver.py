"""Versao de entrega (<= N MB, 2 passes, 1080x1920) a partir do master. Funciona no Windows, Mac e Linux.

Uso:  python tools/deliver.py out/v1_..._clip/v1_..._CLIP.mp4 entregas/v1_final.mp4 [28]
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
target_mb = float(sys.argv[3]) if len(sys.argv) > 3 else 28
dst.parent.mkdir(parents=True, exist_ok=True)
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)],
                           capture_output=True, text=True, check=True).stdout)
vb = int((target_mb * 8 * 1024 * 1024 / dur - 160000) * 0.97)
with tempfile.TemporaryDirectory() as td:
    log = os.path.join(td, "pass")
    base = ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-c:v", "libx264", "-preset", "slow", "-b:v", str(vb),
            "-passlogfile", log]
    subprocess.run(base + ["-pass", "1", "-an", "-f", "mp4", os.devnull], check=True)
    subprocess.run(base + ["-pass", "2", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                           "-movflags", "+faststart", str(dst)], check=True)
print(f"{dst}  {dst.stat().st_size / 1024 / 1024:.1f} MB")
