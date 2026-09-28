"""Motor de edicao do Lote 3 (v2) - Senhor Tanquinho.

Compositor quadro a quadro (OpenCV) -> ffmpeg. Principais recursos:
  - cortes secos automaticos nas pausas (a partir das palavras do transcript)
  - punch-in alternado nos cortes (1.00 / 1.10) ancorado no rosto
  - DESTAQUE DE OBJETO: rastreia o objeto que ele mostra, da zoom suave nele,
    desenha anel animado + etiqueta com seta
  - cards/etiquetas animadas (numeros, emojis) com "pop"
  - b-roll em tela cheia com entrada em zoom + flash
  - titulo-gancho animado, barra de progresso, tremida em palavras de impacto
  - legenda animada (.ass / libass) palavra a palavra
  - audio: cortes com micro-fade, EQ, compressor, loudnorm -14 LUFS + SFX sintetizados
Uso: python engine.py specs/v1.py [--preview] [--no-endcard]
"""

from __future__ import annotations

import importlib.util
import json
import math
import re
import subprocess
import sys
import unicodedata
import wave
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
EDIT = ROOT / "edit"
OUT = ROOT / "out"
W, H, FPS = 1080, 1920, 30
FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"  # fontes vao junto no repo (roda em qualquer PC)
FONT_BLACK = str(FONTS / "Montserrat-Black.otf")
FONT_EXTRA = str(FONTS / "Montserrat-ExtraBold.otf")
FONT_EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"

AMARELO = (255, 212, 0)
LARANJA = (255, 140, 20)
VERDE = (40, 205, 95)
VERMELHO = (235, 50, 50)
BRANCO = (255, 255, 255)
PRETO = (0, 0, 0)


# ----------------------------------------------------------------------------- util
def ease(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def back_out(x: float, s: float = 1.9) -> float:
    """overshoot (pop)"""
    x = min(1.0, max(0.0, x)) - 1
    return x * x * ((s + 1) * x + s) + 1


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s)


def load_spec(path: Path) -> dict:
    sp = importlib.util.spec_from_file_location("spec", path)
    mod = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(mod)
    return mod.SPEC


# ----------------------------------------------------------------------------- timeline
def load_words(spec: dict) -> list[dict]:
    data = json.loads((EDIT / "transcripts" / f"{spec['source']}.json").read_text(encoding="utf-8"))
    ws = [w for w in data["words"] if w.get("type", "word") == "word"]
    fx = spec.get("fixes", {})
    rep = {int(k): v for k, v in fx.get("replace", {}).items()}
    drop = set(fx.get("drop", []))
    out = []
    for i, w in enumerate(ws):
        if i in drop:
            continue
        s, e = float(w["start"]), float(w["end"])
        e = min(e, s + 1.0)  # palavra "esticada" por cima de pausa
        out.append({"i": i, "text": rep.get(i, w["text"]).strip(), "start": s, "end": e})
    for inj in fx.get("inject", []):
        out.append({"i": -1, "text": inj["text"], "start": inj["start"], "end": inj["end"]})
    out = [w for w in out if w["text"]]
    out.sort(key=lambda w: w["start"])
    return out


def build_segments(words: list[dict], keep: list, gap: float, pad_in: float, pad_out: float) -> list[dict]:
    segs: list[list[float]] = []
    for a, b in keep:
        ws = [w for w in words if a <= (w["start"] + w["end"]) / 2 < b]
        if not ws:
            continue
        groups, cur = [], [ws[0]]
        for w in ws[1:]:
            if w["start"] - cur[-1]["end"] > gap:
                groups.append(cur)
                cur = [w]
            else:
                cur.append(w)
        groups.append(cur)
        for g in groups:
            s = max(a, g[0]["start"] - pad_in)
            e = min(b, g[-1]["end"] + pad_out)
            if segs and s <= segs[-1][1] + 0.04:
                segs[-1][1] = max(segs[-1][1], e)
            else:
                segs.append([s, e])
    out, t = [], 0.0
    for s, e in segs:
        s = round(s * FPS) / FPS
        n = max(1, round((e - s) * FPS))
        e = s + n / FPS
        out.append({"s": s, "e": e, "o": t, "n": n})
        t += n / FPS
    return out


class Timeline:
    def __init__(self, segs: list[dict]):
        self.segs = segs
        self.dur = segs[-1]["o"] + segs[-1]["n"] / FPS

    def to_out(self, raw: float) -> float:
        for sg in self.segs:
            if raw < sg["s"]:
                return sg["o"]
            if raw < sg["e"]:
                return sg["o"] + raw - sg["s"]
        return self.dur

    def seg_at_out(self, t: float) -> tuple[int, dict]:
        for k, sg in enumerate(self.segs):
            if t < sg["o"] + sg["n"] / FPS - 1e-9:
                return k, sg
        return len(self.segs) - 1, self.segs[-1]

    def to_raw(self, t: float) -> float:
        _, sg = self.seg_at_out(t)
        return sg["s"] + (t - sg["o"])


# ----------------------------------------------------------------------------- tracking
def track_object(src: Path, t0: float, t1: float, init_t: float, box: list[int], cache: Path) -> dict:
    """Template matching (escala 1/2). Retorna {frame_idx: (cx, cy, w, h)} no quadro-fonte."""
    if cache.exists():
        d = json.loads(cache.read_text())
        return {int(k): tuple(v) for k, v in d.items()}
    f0, f1, fi = int(t0 * FPS), int(t1 * FPS) + 1, int(init_t * FPS)
    sc = 0.5
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{f0 / FPS:.3f}", "-i", str(src), "-frames:v", str(f1 - f0),
           "-vf", f"scale={int(W * sc)}:{int(H * sc)}", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    fw, fh = int(W * sc), int(H * sc)
    frames = np.frombuffer(raw, np.uint8).reshape(-1, fh, fw)
    x, y, w, h = [int(v * sc) for v in box]
    k0 = min(max(fi - f0, 0), len(frames) - 1)
    tpl0 = frames[k0][y:y + h, x:x + w].astype(np.float32)
    res: dict[int, tuple] = {}

    def run(order):
        cx, cy = x + w / 2, y + h / 2
        tpl = tpl0.copy()
        for k in order:
            fr = frames[k].astype(np.float32)
            m = 60
            sx0 = int(max(0, cx - w / 2 - m)); sy0 = int(max(0, cy - h / 2 - m))
            sx1 = int(min(fw, cx + w / 2 + m)); sy1 = int(min(fh, cy + h / 2 + m))
            reg = fr[sy0:sy1, sx0:sx1]
            if reg.shape[0] < h or reg.shape[1] < w:
                res[k] = (cx, cy)
                continue
            r = cv2.matchTemplate(reg, tpl, cv2.TM_CCOEFF_NORMED)
            _, mv, _, ml = cv2.minMaxLoc(r)
            if mv > 0.35:
                cx, cy = sx0 + ml[0] + w / 2, sy0 + ml[1] + h / 2
                patch = fr[int(cy - h / 2):int(cy - h / 2) + h, int(cx - w / 2):int(cx - w / 2) + w]
                if patch.shape == tpl.shape:
                    tpl = 0.85 * tpl + 0.15 * (0.5 * patch + 0.5 * tpl0)
            res[k] = (cx, cy)

    run(range(k0, len(frames)))
    run(range(k0, -1, -1))
    ks = sorted(res)
    xs = np.array([res[k][0] for k in ks]); ys = np.array([res[k][1] for k in ks])
    ker = np.ones(7) / 7
    xs = np.convolve(np.pad(xs, 3, mode="edge"), ker, "valid")
    ys = np.convolve(np.pad(ys, 3, mode="edge"), ker, "valid")
    out = {f0 + k: (float(xs[j] / sc), float(ys[j] / sc), float(w / sc), float(h / sc)) for j, k in enumerate(ks)}
    cache.write_text(json.dumps(out))
    return out


def track_white(src: Path, t0: float, t1: float, init_t: float, box: list[int], cache: Path) -> dict:
    """Objeto branco (ovo): maior mancha clara e pouco saturada perto da posicao anterior."""
    if cache.exists():
        return {int(k): tuple(v) for k, v in json.loads(cache.read_text()).items()}
    f0, f1, fi = int(t0 * FPS), int(t1 * FPS) + 1, int(init_t * FPS)
    sc = 0.5
    fw, fh = int(W * sc), int(H * sc)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{f0 / FPS:.3f}", "-i", str(src), "-frames:v", str(f1 - f0),
                          "-vf", f"scale={fw}:{fh}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    frames = np.frombuffer(raw, np.uint8).reshape(-1, fh, fw, 3)
    w, h = box[2] * sc, box[3] * sc
    k0 = min(max(fi - f0, 0), len(frames) - 1)
    res = {}

    def run(order):
        cx, cy = (box[0] + box[2] / 2) * sc, (box[1] + box[3] / 2) * sc
        for k in order:
            hsv = cv2.cvtColor(frames[k], cv2.COLOR_RGB2HSV)
            m = ((hsv[..., 2] > 200) & (hsv[..., 1] < 45)).astype(np.uint8)
            R = 90
            x0, y0 = int(max(0, cx - R)), int(max(0, cy - R))
            x1, y1 = int(min(fw, cx + R)), int(min(fh, cy + R))
            sub = cv2.morphologyEx(m[y0:y1, x0:x1], cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
            n, lab, st, cen = cv2.connectedComponentsWithStats(sub)
            best, bd = None, 1e9
            for j in range(1, n):
                a = st[j, cv2.CC_STAT_AREA]
                if 600 < a < 9000:
                    d = (cen[j][0] + x0 - cx) ** 2 + (cen[j][1] + y0 - cy) ** 2
                    if d < bd:
                        best, bd = j, d
            if best is not None:
                cx, cy = cen[best][0] + x0, cen[best][1] + y0
            res[k] = (cx, cy)

    run(range(k0, len(frames)))
    run(range(k0, -1, -1))
    ks = sorted(res)
    xs = np.array([res[k][0] for k in ks]); ys = np.array([res[k][1] for k in ks])
    ker = np.ones(5) / 5
    xs = np.convolve(np.pad(xs, 2, mode="edge"), ker, "valid")
    ys = np.convolve(np.pad(ys, 2, mode="edge"), ker, "valid")
    out = {f0 + k: (float(xs[j] / sc), float(ys[j] / sc), float(w / sc), float(h / sc)) for j, k in enumerate(ks)}
    cache.write_text(json.dumps(out))
    return out


# ----------------------------------------------------------------------------- sprites
_font_cache: dict = {}


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    k = (path, size)
    if k not in _font_cache:
        _font_cache[k] = ImageFont.truetype(path, size)
    return _font_cache[k]


def emoji_img(ch: str, size: int) -> Image.Image:
    f = font(FONT_EMOJI, 109)
    im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10, 10), ch, font=f, embedded_color=True)
    bb = im.getbbox() or (0, 0, 1, 1)
    im = im.crop(bb)
    r = size / max(im.size)
    return im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)


def pill(text: str, size: int = 64, bg=AMARELO, fg=PRETO, emoji: str | None = None, pad=(34, 18),
         radius: int | None = None, outline=PRETO, rot: float = 0.0, font_path: str = FONT_BLACK) -> np.ndarray:
    """Etiqueta arredondada com sombra. Retorna RGBA premultiplicavel (np.uint8)."""
    f = font(font_path, size)
    tb = f.getbbox(text)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    em = emoji_img(emoji, int(size * 1.15)) if emoji else None
    gap = int(size * 0.28) if em else 0
    iw = tw + (em.width + gap if em else 0)
    ih = max(th, em.height if em else 0)
    bw, bh = iw + 2 * pad[0], ih + 2 * pad[1]
    r = radius if radius is not None else bh // 2
    sh = 14
    im = Image.new("RGBA", (bw + 2 * sh, bh + 2 * sh), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((sh + 6, sh + 10, sh + bw + 6, sh + bh + 10), r, fill=(0, 0, 0, 110))
    d.rounded_rectangle((sh, sh, sh + bw, sh + bh), r, fill=bg + (255,), outline=outline + (255,) if outline else None,
                        width=5 if outline else 0)
    x = sh + pad[0]
    if em:
        im.alpha_composite(em, (x, sh + (bh - em.height) // 2))
        x += em.width + gap
    d.text((x - tb[0], sh + (bh - th) // 2 - tb[1]), text, font=f, fill=fg + (255,))
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    return np.array(im)


ACCENT = {AMARELO: AMARELO, LARANJA: LARANJA, VERDE: (70, 215, 120), VERMELHO: (255, 85, 70),
          BRANCO: BRANCO, PRETO: BRANCO}


def panel(lines: list[dict], accent=LARANJA, width: int | None = None) -> np.ndarray:
    """Card sobrio: fundo preto 80%, cantos 16px, barra de acento a esquerda, linhas de texto empilhadas.
    line = {text, size, color}"""
    rend = []
    for ln in lines:
        f = font(ln.get("font", FONT_EXTRA), ln["size"])
        bb = f.getbbox(ln["text"])
        rend.append((ln, f, bb, bb[2] - bb[0], bb[3] - bb[1]))
    padx, pady, gap, bar = 34, 22, 12, 8
    tw = max(r[3] for r in rend)
    th = sum(r[4] for r in rend) + gap * (len(rend) - 1)
    bw = width or (tw + 2 * padx + bar)
    bh = th + 2 * pady
    sh = 18
    im = Image.new("RGBA", (bw + 2 * sh, bh + 2 * sh), (0, 0, 0, 0))
    sd = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sd).rounded_rectangle((sh, sh + 6, sh + bw, sh + bh + 6), 16, fill=(0, 0, 0, 120))
    from PIL import ImageFilter
    im.alpha_composite(sd.filter(ImageFilter.GaussianBlur(10)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((sh, sh, sh + bw, sh + bh), 16, fill=(14, 14, 14, 205))
    d.rounded_rectangle((sh, sh, sh + bar + 8, sh + bh), 16, fill=accent + (255,))
    d.rectangle((sh + bar, sh, sh + bar + 10, sh + bh), fill=(14, 14, 14, 205))
    y = sh + pady
    for ln, f, bb, w_, h_ in rend:
        x = sh + bar + (bw - bar - w_) // 2
        d.text((x - bb[0], y - bb[1]), ln["text"], font=f, fill=tuple(ln.get("color", BRANCO)) + (255,))
        y += h_ + gap
    return np.array(im)


def card_from_pills(pills: list[dict], scale: float = 1.0) -> np.ndarray:
    """Converte a ficha antiga (pills coloridas) no card sobrio."""
    lines, accent = [], LARANJA
    for p in pills:
        bg = tuple(p.get("bg", AMARELO))
        big = p.get("size", 64) >= 70
        col = BRANCO if bg in (BRANCO, PRETO) else ACCENT.get(bg, AMARELO)
        if bg not in (BRANCO, PRETO):
            accent = ACCENT.get(bg, LARANJA)
        size = int(min(p.get("size", 64), 110) * (0.95 if big else 0.82) * scale)
        lines.append({"text": p["text"], "size": size, "color": col,
                      "font": FONT_BLACK if big else FONT_EXTRA})
    return panel(lines, accent)


def slide_curve(t: float, t_in: float, t_out: float, d_in: float = 0.28, d_out: float = 0.22) -> tuple[float, float]:
    """(deslocamento_y, alpha): entra subindo 28px com fade, sai com fade."""
    if t < t_in or t > t_out:
        return 0.0, 0.0
    if t < t_in + d_in:
        x = ease((t - t_in) / d_in)
        return 28 * (1 - x), x
    if t > t_out - d_out:
        return 0.0, ease((t_out - t) / d_out)
    return 0.0, 1.0


def brackets(img: np.ndarray, X: float, Y: float, hw: float, hh: float, alpha: float, grow: float) -> None:
    """Cantoneiras de foco (4 'L') brancas com sombra."""
    if alpha <= 0.01:
        return
    hw, hh = hw * grow, hh * grow
    L = int(min(hw, hh) * 0.45)
    over = img.copy()
    pts = [((X - hw, Y - hh), (1, 1)), ((X + hw, Y - hh), (-1, 1)), ((X - hw, Y + hh), (1, -1)), ((X + hw, Y + hh), (-1, -1))]
    for col, th in (((0, 0, 0), 12), ((255, 255, 255), 6)):
        for (cx, cy), (sx, sy) in pts:
            c = (int(cx), int(cy))
            cv2.line(over, c, (int(cx + sx * L), int(cy)), col, th, cv2.LINE_AA)
            cv2.line(over, c, (int(cx), int(cy + sy * L)), col, th, cv2.LINE_AA)
    cv2.addWeighted(over, alpha, img, 1 - alpha, 0, dst=img)


def stack(sprites: list[np.ndarray], gap: int = 10) -> np.ndarray:
    w = max(s.shape[1] for s in sprites)
    h = sum(s.shape[0] for s in sprites) + gap * (len(sprites) - 1)
    out = np.zeros((h, w, 4), np.uint8)
    y = 0
    for s in sprites:
        x = (w - s.shape[1]) // 2
        out[y:y + s.shape[0], x:x + s.shape[1]] = s
        y += s.shape[0] + gap
    return out


def blit(frame: np.ndarray, spr: np.ndarray, cx: float, cy: float, scale: float = 1.0, alpha: float = 1.0) -> None:
    """Cola sprite RGBA centralizado em (cx, cy) com escala e opacidade."""
    if scale <= 0.01 or alpha <= 0.01:
        return
    s = spr
    if abs(scale - 1) > 1e-3:
        s = cv2.resize(spr, (max(1, int(spr.shape[1] * scale)), max(1, int(spr.shape[0] * scale))),
                       interpolation=cv2.INTER_LINEAR)
    h, w = s.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    fx0, fy0, fx1, fy1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if fx1 <= fx0 or fy1 <= fy0:
        return
    sub = s[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0].astype(np.float32)
    a = sub[..., 3:4] / 255.0 * alpha
    roi = frame[fy0:fy1, fx0:fx1].astype(np.float32)
    frame[fy0:fy1, fx0:fx1] = (roi * (1 - a) + sub[..., :3] * a).astype(np.uint8)


def pop_curve(t: float, t_in: float, t_out: float, dur_in: float = 0.28, dur_out: float = 0.18) -> tuple[float, float]:
    """(escala, alpha) de um elemento que entra com pop e sai encolhendo."""
    if t < t_in or t > t_out:
        return 0.0, 0.0
    if t < t_in + dur_in:
        x = (t - t_in) / dur_in
        return back_out(x), min(1.0, x * 3)
    if t > t_out - dur_out:
        x = (t_out - t) / dur_out
        return 0.6 + 0.4 * ease(x), ease(x)
    return 1.0, 1.0


# ----------------------------------------------------------------------------- captions (.ass)
def ass_ts(t: float) -> str:
    cs = int(round(max(0.0, t) * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def build_captions(words_out: list[dict], keywords: list[str], path: Path, y, size: int,
                   hide: list[tuple[float, float]]) -> None:
    y_at = y if callable(y) else (lambda t, _y=y: _y)
    kw = {norm(k) for k in keywords}
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Montserrat ExtraBold,{size},&H00FFFFFF,&H00FFFFFF,&H00101010,&H78000000,0,0,0,0,100,100,0.5,0,1,4.5,2.5,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # blocos de ate 3 palavras / 16 caracteres, quebrando em pontuacao e pausas
    chunks, cur = [], []
    for i, w in enumerate(words_out):
        cur.append(w)
        nx = words_out[i + 1] if i + 1 < len(words_out) else None
        chars = sum(len(x["text"]) + 1 for x in cur)
        if (len(cur) >= 3 or w["text"][-1:] in ".,?!:;" or nx is None or nx["start"] - w["end"] > 0.30
                or chars + (len(nx["text"]) if nx else 0) > 16):
            chunks.append(cur)
            cur = []
    ev = []
    for ci, ch in enumerate(chunks):
        c0 = ch[0]["start"]
        nxt = chunks[ci + 1][0]["start"] if ci + 1 < len(chunks) else ch[-1]["end"] + 0.4
        c1 = min(max(ch[-1]["end"] + 0.12, c0 + 0.3), nxt) if nxt - ch[-1]["end"] > 0.5 else nxt
        if any(a <= c0 < b for a, b in hide):
            continue
        texts = [re.sub(r"[.,;:]+$", "", w["text"].upper()) for w in ch]
        iskw = [norm(w["text"]) in kw for w in ch]
        # um evento por palavra falada (a palavra ativa acende)
        bounds = [max(c0, w["start"]) for w in ch] + [c1]
        bounds[0] = c0
        for k in range(len(ch)):
            a, b = bounds[k], bounds[k + 1]
            if b - a < 0.01:
                continue
            parts = []
            for j, tx in enumerate(texts):
                if j == k:
                    parts.append(r"{\c&H00D4FF&}" + tx + r"{\c&HFFFFFF&}")
                else:
                    parts.append(tx)
            anim = r"{\fad(90,0)\blur0.8}" if k == 0 else r"{\blur0.8}"
            ev.append(f"Dialogue: 0,{ass_ts(a)},{ass_ts(b)},Cap,,0,0,0,,{{\\an5\\pos({W // 2},{int(y_at(c0))})}}{anim}" + " ".join(parts))
    path.write_text(head + "\n".join(ev) + "\n", encoding="utf-8")


# ----------------------------------------------------------------------------- sfx
def synth_sfx(dirp: Path) -> dict:
    dirp.mkdir(parents=True, exist_ok=True)
    sr = 48000

    def save(name, y):
        y = np.clip(y, -1, 1)
        p = dirp / f"{name}.wav"
        with wave.open(str(p), "wb") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
            wf.writeframes((y * 32767).astype(np.int16).tobytes())
        return p

    t = np.arange(int(0.09 * sr)) / sr
    f = 950 * np.exp(-t * 18) + 380
    pop = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t * 45) * 0.9
    t2 = np.arange(int(0.7 * sr)) / sr
    ding = (np.sin(2 * np.pi * 1318 * t2) * 0.55 + np.sin(2 * np.pi * 2637 * t2) * 0.25
            + np.sin(2 * np.pi * 1975 * t2) * 0.15) * np.exp(-t2 * 6) * np.minimum(1, t2 * 400)
    t3 = np.arange(int(0.05 * sr)) / sr
    tick = np.sin(2 * np.pi * 2200 * t3) * np.exp(-t3 * 90) * 0.7
    t4 = np.arange(int(0.35 * sr)) / sr
    buzz = (np.sign(np.sin(2 * np.pi * 150 * t4)) * 0.25 + np.sin(2 * np.pi * 300 * t4) * 0.3) * np.exp(-t4 * 7) \
        * np.minimum(1, t4 * 300)
    rng = np.random.default_rng(3)
    t5 = np.arange(int(0.25 * sr)) / sr
    thump = np.sin(2 * np.pi * (60 + 90 * np.exp(-t5 * 25)) * t5) * np.exp(-t5 * 12) + rng.normal(0, 0.05, t5.size) * np.exp(-t5 * 40)
    return {"pop": save("pop", pop), "ding": save("ding", ding), "tick": save("tick", tick),
            "buzz": save("buzz", buzz), "thump": save("thump", thump * 0.9)}


# ----------------------------------------------------------------------------- render
class Reader:
    def __init__(self, path: Path, start: float = 0.0, size=(W, H)):
        self.w, self.h = size
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-i", str(path), "-f", "rawvideo",
                                   "-pix_fmt", "rgb24", "-vf", f"scale={self.w}:{self.h}", "-"], stdout=subprocess.PIPE)
        self.idx = -1
        self.last = None

    eof = False

    def read(self):
        if self.eof:
            return self.last
        buf = self.p.stdout.read(self.w * self.h * 3)
        if len(buf) < self.w * self.h * 3:
            self.eof = True
            return self.last
        self.idx += 1
        self.last = np.frombuffer(buf, np.uint8).reshape(self.h, self.w, 3)
        return self.last

    def seek_to(self, k: int):
        while self.idx < k and not self.eof:
            self.read()
        return self.last

    def close(self):
        self.p.stdout.close()
        self.p.kill()


def render(spec_path: Path, preview: bool = False, endcard: bool = True) -> Path:
    spec = load_spec(spec_path)
    name = spec["name"]
    job = OUT / name
    job.mkdir(parents=True, exist_ok=True)
    src = ROOT / "raw" / f"{spec['source']}.mp4"

    words = load_words(spec)
    tl = Timeline(build_segments(words, spec["keep"], spec.get("gap", 0.30), spec.get("pad_in", 0.07),
                                 spec.get("pad_out", 0.13)))
    dur = tl.dur
    nfr = round(dur * FPS)
    print(f"[{name}] {len(tl.segs)} trechos, {dur:.2f}s (bruto {spec['keep'][-1][1] - spec['keep'][0][0]:.2f}s)")

    # palavras no timeline de saida
    words_out = []
    for w in words:
        mid = (w["start"] + w["end"]) / 2
        if any(sg["s"] <= mid < sg["e"] for sg in tl.segs):
            words_out.append({"text": w["text"], "start": tl.to_out(max(w["start"], mid - 0.6)),
                              "end": tl.to_out(min(w["end"], mid + 0.6))})

    # ---- zoom por trecho (jump-cut)
    face = spec.get("face", (540, 620))
    zooms = []
    for k, sg in enumerate(tl.segs):
        if k == 0:
            zooms.append(1.0)
        else:
            gap_cut = sg["s"] - tl.segs[k - 1]["e"]
            zooms.append((1.10 if zooms[-1] == 1.0 else 1.0) if gap_cut > 0.12 else zooms[-1])

    # ---- objetos
    props = []
    for pi, pr in enumerate(spec.get("props", [])):
        if pr.get("static"):
            bx = pr["box"]
            c = (bx[0] + bx[2] / 2, bx[1] + bx[3] / 2, bx[2], bx[3])
            tr = {k: c for k in range(int((pr["t0"] - 0.6) * FPS), int((pr["t1"] + 0.6) * FPS) + 1)}
        elif pr.get("white"):
            tr = track_white(src, pr["t0"] - 0.5, pr["t1"] + 0.5, pr["init_t"], pr["box"], job / f"track_{pi}.json")
        else:
            tr = track_object(src, pr["t0"] - 0.5, pr["t1"] + 0.5, pr["init_t"], pr["box"], job / f"track_{pi}.json")
        props.append({**pr, "track": tr, "o0": tl.to_out(pr["t0"]), "o1": tl.to_out(pr["t1"])})

    def prop_state(t: float, raw: float):
        best = None
        for pr in props:
            ramp = 0.35
            if pr["o0"] - ramp <= t <= pr["o1"] + ramp:
                w = ease((t - (pr["o0"] - ramp)) / ramp) * ease(((pr["o1"] + ramp) - t) / ramp)
                k = int(round(raw * FPS))
                ks = pr["track"]
                if k not in ks:
                    k = min(ks, key=lambda q: abs(q - k))
                best = (pr, w, ks[k])
        return best

    # ---- b-roll / cards / efeitos em tempo de saida
    brolls = []
    for b in spec.get("broll", []):
        o = tl.to_out(b["at"])
        brolls.append({**b, "o0": o, "o1": o + b["dur"]})
    for b in brolls:
        for pr in props:
            if b["o0"] < pr["o1"] and pr["o0"] < b["o1"]:
                print(f"  AVISO: b-roll {b['clip']} cobre destaque de objeto '{pr['label']}'")

    cards = []
    for c in spec.get("cards", []):
        spr = c.get("sprite")
        if spr is None:
            spr = card_from_pills(c["pills"], spec.get("card_scale", 1.3))
        o0 = tl.to_out(c["at"])
        o1 = tl.to_out(c["until"]) if "until" in c else o0 + c.get("dur", 1.6)
        cards.append({**c, "spr": spr, "o0": o0, "o1": o1})

    shakes = []  # estilo adulto: sem tremida
    top_max = spec.get("head_top", 640) - 40
    punches = [tl.to_out(t) for t in spec.get("punch", [])]

    # headline
    hl = spec.get("headline")
    hl_sprites = []
    if hl:
        for li, ln in enumerate(hl["lines"]):
            pass
        hl_sprites.append(panel([{"text": ln["text"], "size": int(ln.get("size", 80) * 0.86), "font": FONT_BLACK,
                                  "color": BRANCO if li == 0 else AMARELO} for li, ln in enumerate(hl["lines"])],
                                LARANJA))

    # ---- legenda
    hide = [(b["o0"] - 0.01, b["o0"] + 0.01) for b in []]
    cap_path = job / "captions.ass"
    cy0 = spec.get("cap_y", 1290)
    moves = [(tl.to_out(a), tl.to_out(b), yy) for a, b, yy in spec.get("cap_moves", [])]
    cap_y = lambda t: next((yy for a, b, yy in moves if a - 0.2 <= t < b), cy0)
    build_captions(words_out, spec.get("keywords", []), cap_path, cap_y,
                   spec.get("cap_size", 76), hide)

    # ---- audio
    sfx = synth_sfx(OUT / "_sfx")
    sfx_events = []
    for pr in props:
        sfx_events.append(("tick", pr["o0"], 0.10))
    for c in cards:
        sfx_events.append(("tick", c["o0"], 0.09))
    wav = job / "audio.wav"
    build_audio(src, tl, sfx, sfx_events, wav, dur)

    # ---- video
    out_body = job / f"{name}_body.mp4"
    enc = subprocess.Popen([
        "ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "-", "-i", str(wav),
        "-vf", f"eq=contrast=1.05:saturation=1.10:gamma=1.02,ass={cap_path}",
        "-c:v", "libx264", "-preset", "veryfast" if preview else "medium", "-crf", "24" if preview else "18",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out_body)],
        stdin=subprocess.PIPE)
    rd = Reader(src)
    br_reader, br_cur = None, None
    ring_col = spec.get("ring_color", AMARELO)

    for fi in range(nfr):
        t = fi / FPS
        k, sg = tl.seg_at_out(t)
        raw = sg["s"] + (t - sg["o"])
        frame = rd.seek_to(int(round(raw * FPS)))
        if frame is None:
            break

        # ---------- enquadramento
        z, ax, ay = zooms[k], face[0], face[1]
        ps = prop_state(t, raw)
        if ps:
            pr, wgt, (ocx, ocy, ow, oh) = ps
            pz = pr.get("zoom", 1.28)
            z = z + (pz - z) * wgt
            ax = ax + (ocx - ax) * wgt
            ay = ay + (ocy - ay) * wgt
        for pt in punches:
            if pt <= t < pt + 0.5:
                z *= 1 + 0.035 * math.sin(math.pi * min(1, (t - pt) / 0.5))
        dx = dy = 0.0
        for st in shakes:
            if st <= t < st + 0.28:
                amp = 16 * (1 - (t - st) / 0.28)
                dx += amp * math.sin(t * 95)
                dy += amp * math.cos(t * 77)
        M = np.float32([[z, 0, (1 - z) * ax + dx], [0, z, (1 - z) * ay + dy]])
        if abs(z - 1) > 1e-4 or dx or dy:
            if dx or dy:
                M[0, 0] = M[1, 1] = max(z, 1.04)
                zz = M[0, 0]
                M[0, 2] = (1 - zz) * ax + dx
                M[1, 2] = (1 - zz) * ay + dy
            img = cv2.warpAffine(frame, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        else:
            img = frame.copy()

        # ---------- destaque do objeto (cantoneiras de foco + etiqueta compacta)
        if ps and not any(b["o0"] <= t < b["o1"] for b in brolls):
            pr, wgt, (ocx, ocy, ow, oh) = ps
            zz = M[0, 0]
            X = zz * ocx + M[0, 2]
            Y = zz * ocy + M[1, 2]
            bs = pr.get("bracket", 0.55)
            hw, hh = ow * zz * bs, oh * zz * bs
            if pr["o0"] <= t <= pr["o1"] + 0.15:
                a_in = ease((t - pr["o0"]) / 0.3)
                a_out = ease((pr["o1"] + 0.15 - t) / 0.2)
                brackets(img, X, Y, hw, hh, min(a_in, a_out), 1.0 + 0.25 * (1 - a_in))
                lab = pr.get("_spr")
                if lab is None:
                    bg = tuple(pr.get("label_bg", AMARELO))
                    col = ACCENT.get(bg, AMARELO) if bg not in (BRANCO, PRETO) else AMARELO
                    lab = pr["_spr"] = panel([{"text": pr["label"], "size": pr.get("label_size", 44), "color": col,
                                               "font": FONT_EXTRA}], ACCENT.get(bg, LARANJA))
                dy, a = slide_curve(t, pr["o0"] + 0.2, pr["o1"] + 0.15)
                side = pr.get("label_side", "up")
                lw, lh = lab.shape[1] / 2, lab.shape[0] / 2
                if side == "down":
                    lx, ly = X, Y + hh + lh + 4
                elif side == "right":
                    lx, ly = X + hw + lw - 30, Y - hh
                elif side == "left":
                    lx, ly = X - hw - lw + 30, Y - hh
                else:
                    lx, ly = X, Y - hh - lh + 4
                lx = min(max(lx, lw + 10), W - lw - 10)
                blit(img, lab, lx, ly + dy, 1.0, a)

        # ---------- b-roll
        base_img = img
        cur = next((b for b in brolls if b["o0"] <= t < b["o1"]), None)
        if cur is not br_cur:
            if br_reader:
                br_reader.close()
            br_reader = Reader(EDIT / "broll" / "clips" / f"{cur['clip']}.mp4", cur.get("src_start", 0.0)) if cur else None
            br_cur = cur
        if cur:
            bf = br_reader.read()
            if bf is not None:
                e = t - cur["o0"]
                zb = 1.06 - 0.06 * ease(e / 0.45) + 0.03 * (e / cur["dur"])
                Mb = np.float32([[zb, 0, (1 - zb) * W / 2], [0, zb, (1 - zb) * H / 2]])
                img = cv2.warpAffine(bf, Mb, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
                if e < 0.13 and base_img is not None:
                    fl = ease(e / 0.13)
                    img = cv2.addWeighted(img, fl, base_img, 1 - fl, 0)

        # ---------- cards
        for c in cards:
            dy, a = slide_curve(t, c["o0"], c["o1"])
            if a > 0:
                hw = c["spr"].shape[1] / 2 + 10
                hh = c["spr"].shape[0] / 2
                cy = min(c["y"], top_max - hh)  # nunca invade a cabeca
                cy = max(cy, 40 + hh)
                blit(img, c["spr"], min(max(c["x"], hw), W - hw), cy + dy, 1.0, a)

        # ---------- headline
        if hl and t < hl["dur"]:
            spr = hl_sprites[0]
            dy, a = slide_curve(t, 0.0, hl["dur"], 0.35, 0.3)
            cy = min(hl.get("top", 180) + spr.shape[0] / 2, top_max - spr.shape[0] / 2)
            blit(img, spr, W / 2, cy + dy, 1.0, a)

        # ---------- barra de progresso
        pw = int(W * (t / dur))
        img[0:6, :pw] = LARANJA

        enc.stdin.write(np.ascontiguousarray(img).tobytes())
        if fi % 300 == 0:
            print(f"  quadro {fi}/{nfr}", flush=True)

    rd.close()
    if br_reader:
        br_reader.close()
    enc.stdin.close()
    enc.wait()

    final = job / f"{name}_FINAL.mp4"
    card = EDIT / "endcard" / "endcard.mp4"
    if endcard and card.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out_body), "-i", str(card), "-filter_complex",
                        "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]", "-map", "[v]", "-map", "[a]",
                        "-c:v", "libx264", "-preset", "veryfast" if preview else "medium",
                        "-crf", "24" if preview else "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                        "-movflags", "+faststart", str(final)], check=True)
    else:
        out_body.replace(final)
    print(f"[{name}] PRONTO -> {final}")
    return final


def build_audio(src: Path, tl: Timeline, sfx: dict, events: list, wav: Path, dur: float) -> None:
    parts, labels = [], []
    for k, sg in enumerate(tl.segs):
        d = sg["n"] / FPS
        f = min(0.008, d / 4)
        parts.append(f"[0:a]atrim={sg['s']:.4f}:{sg['s'] + d:.4f},asetpts=PTS-STARTPTS,"
                     f"afade=t=in:d={f:.4f},afade=t=out:st={d - f:.4f}:d={f:.4f}[s{k}]")
        labels.append(f"[s{k}]")
    fc = ";".join(parts) + ";" + "".join(labels) + f"concat=n={len(labels)}:v=0:a=1,aresample=48000,"
    fc += "highpass=f=75,equalizer=f=3200:t=q:w=1.2:g=2.5,acompressor=threshold=-20dB:ratio=3:attack=8:release=120," \
          "loudnorm=I=-14:TP=-1.5:LRA=9[voice]"
    inputs = ["-i", str(src)]
    mix = ["[voice]"]
    for j, (kind, t, vol) in enumerate(events):
        inputs += ["-i", str(sfx[kind])]
        ms = int(max(0, t) * 1000)
        fc += f";[{j + 1}:a]aresample=48000,volume={vol},adelay={ms}|{ms}[x{j}]"
        mix.append(f"[x{j}]")
    fc += f";{''.join(mix)}amix=inputs={len(mix)}:normalize=0:duration=first,atrim=0:{dur:.3f},alimiter=limit=0.95[a]"
    script = wav.with_suffix(".fc.txt")
    script.write_text(fc)
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex_script", str(script), "-map", "[a]",
                    "-ac", "2", "-ar", "48000", str(wav)], check=True)


if __name__ == "__main__":
    render(Path(sys.argv[1]), preview="--preview" in sys.argv, endcard="--no-endcard" not in sys.argv)
