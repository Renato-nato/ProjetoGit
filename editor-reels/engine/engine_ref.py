"""Motor v3 - estilo da referencia (@giubeckers): tipografia como protagonista.

- tipografia condensada (Anton) amarelo-lima com brilho, palavra aparece quando e falada
  layouts: "spread" (palavras espalhadas na largura), "stack" (bloco alinhado a esquerda),
           "giant" (palavra gigante), "cta" (linha pequena branca + palavra gigante)
- TODO texto grande passa ATRAS da pessoa (mascara MediaPipe por quadro) -> nunca cobre o rosto
- momentos em preto e branco, enquadramento alternado (aberto / fechado), grade quente
- legenda minima: uma palavra por vez, pequena, entre queixo e prato
- zoom suave nos objetos que ele mostra (rastreados)
- audio: noisereduce (perfil de ruido do proprio video) + loudnorm linear + musica com ducking
Rodar (dentro de editor-reels/engine, com o venv ativo):  python engine_ref.py specs_ref/v1.py
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import (EDIT, FPS, H, OUT, ROOT, W, Reader, Timeline, ass_ts, build_segments, ease, load_spec,  # noqa: E402
                    load_words, norm, track_object, track_white)

ASSETS = ROOT / "assets"
FONT_COND = str(ASSETS / "Anton.ttf")
FONT_CAP = str(ASSETS / "fonts" / "Montserrat-SemiBold.otf")
LIME = (254, 122, 0)  # laranja do card final (era amarelo-lima)
WHITE = (255, 255, 255)


# ----------------------------------------------------------------------------- tipografia
_fc: dict = {}
_sc: dict = {}


def fnt(path: str, size: int) -> ImageFont.FreeTypeFont:
    k = (path, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(path, size)
    return _fc[k]


def word_sprite(text: str, size: int, color=LIME, font_path: str = FONT_COND, glow: float = 0.40,
                stroke: float = 0.0) -> np.ndarray:
    """Palavra com brilho suave da propria cor. RGBA float32 0..1 (premultiplicado).
    stroke = contorno preto em volta da letra (fracao do tamanho; 0 = sem contorno)."""
    k = (text, size, color, font_path, glow, stroke)
    if k in _sc:
        return _sc[k]
    f = fnt(font_path, size)
    bb = f.getbbox(text)
    pad = int(size * 0.35)
    w, h = bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad
    base = Image.new("L", (w, h), 0)
    ImageDraw.Draw(base).text((pad - bb[0], pad - bb[1]), text, font=f, fill=255)
    a_txt = np.asarray(base, np.float32) / 255
    a_ol = a_txt
    if stroke > 0:  # letra + contorno (a parte do contorno fica preta: entra no alfa, nao na cor)
        ol = Image.new("L", (w, h), 0)
        ImageDraw.Draw(ol).text((pad - bb[0], pad - bb[1]), text, font=f, fill=255,
                                stroke_width=max(1, round(size * stroke)), stroke_fill=255)
        a_ol = np.maximum(np.asarray(ol, np.float32) / 255, a_txt)
    a_glow = np.asarray(base.filter(ImageFilter.GaussianBlur(size * 0.09)), np.float32) / 255 * glow
    a_sh = np.asarray(base.filter(ImageFilter.GaussianBlur(size * 0.06)), np.float32) / 255 * 0.62
    col = np.array(color, np.float32) / 255
    # sombra escura por baixo, brilho colorido, contorno preto, texto por cima
    A = np.clip(a_ol + a_glow * (1 - a_ol) + a_sh * (1 - a_ol) * (1 - a_glow), 0, 1)
    rgb = (col * (a_txt + a_glow * (1 - a_ol))[..., None])
    out = np.dstack([rgb, A]).astype(np.float32)
    _sc[k] = out
    _base[k] = pad - bb[1] + f.getmetrics()[0]
    return out


_base: dict = {}


def baseline_of(text: str, size: int, color=LIME, font_path: str = FONT_COND, stroke: float = 0.0) -> float:
    word_sprite(text, size, color, font_path, stroke=stroke)
    return _base[(text, size, color, font_path, 0.40, stroke)]


def cap_h(size: int, font_path: str = FONT_COND) -> float:
    bb = fnt(font_path, size).getbbox("H")
    return bb[3] - bb[1]


def text_width(text: str, size: int, font_path: str = FONT_COND) -> int:
    bb = fnt(font_path, size).getbbox(text)
    return bb[2] - bb[0]


def layout_event(ev: dict) -> list[dict]:
    """Converte um evento em itens {word, size, color, x (centro), y (centro)} em ordem de fala."""
    items = []
    kind = ev["type"]
    if kind == "spread":
        # linha longa demais: quebra em duas em vez de encolher a letra
        min_size = ev.get("min_size", 118)
        lines, ys = [], []
        for li, line in enumerate(ev["lines"]):
            words = line.split()
            size = ev.get("size", 150)
            if len(words) > 1 and sum(text_width(w, min_size) for w in words) + 30 * (len(words) - 1) > W - 2 * ev.get("margin", 48):
                cut = (len(words) + 1) // 2
                lines += [" ".join(words[:cut]), " ".join(words[cut:])]
                ys += [ev["y"][li], ev["y"][li] + cap_h(size) + 40]
            else:
                lines.append(line)
                ys.append(ev["y"][li])
        if len(lines) > len(ev["lines"]):  # houve quebra: reempilha a partir da 1a linha
            step = cap_h(ev.get("size", 150)) + 48
            ys = [ev["y"][0] + i * step for i in range(len(lines))]
        ev = {**ev, "lines": lines, "y": ys}
        for li, line in enumerate(ev["lines"]):
            words = line.split()
            size = ev.get("size", 150)
            margin = ev.get("margin", 48)
            while sum(text_width(w, size) for w in words) + 30 * (len(words) - 1) > W - 2 * margin and size > 40:
                size -= 4
            ws = [text_width(w, size) for w in words]
            if len(words) >= 3:  # espalha na largura (como na referencia)
                gap = (W - 2 * margin - sum(ws)) / (len(words) - 1)
                x = margin
            else:  # 1-2 palavras: centraliza com espaco normal (espalhar le errado)
                gap = text_width(" ", size) * 0.9
                x = (W - sum(ws) - gap * (len(words) - 1)) / 2
            for w, wd in zip(words, ws):
                items.append({"word": w, "size": size, "color": LIME, "x": x + wd / 2, "by": ev["y"][li] + cap_h(size) / 2})
                x += wd + gap
    elif kind == "stack":
        size = ev.get("size", 150)
        x0, y = ev.get("x", 56), ev.get("y", 170)
        maxw = ev.get("maxw", W - 2 * x0)
        for line in ev["lines"]:
            words = line.split()
            s = size
            while text_width(line, s) > maxw and s > 40:
                s -= 4
            y += cap_h(s)
            x = x0
            sp = text_width(" ", s) * 0.6
            for w in words:
                wd = text_width(w, s)
                items.append({"word": w, "size": s, "color": LIME, "x": x + wd / 2, "by": y})
                x += wd + sp
            y += cap_h(s) * ev.get("leading", 0.2) + 14
    elif kind == "giant":
        size = ev.get("size", 420)
        while text_width(ev["text"], size) > W - 60 and size > 60:
            size -= 8
        items.append({"word": ev["text"], "size": size, "color": LIME, "x": ev.get("x", W / 2),
                      "by": ev["y"] + cap_h(size) / 2, "whole": True})
    elif kind == "cta":
        y = ev.get("y", 260)
        for ln in ev["lines"]:
            size = ln["size"]
            fp = FONT_CAP if ln.get("small") else FONT_COND
            while text_width(ln["text"], size, fp) > W - 60 and size > 40:
                size -= 6
            y += cap_h(size, fp)
            items.append({"word": ln["text"], "size": size, "color": WHITE if ln.get("small") else LIME,
                          "font": fp, "x": W / 2, "by": y, "whole": True})
            y += 26
    return items


def match_times(items: list[dict], words: list[dict], at: float, until: float) -> None:
    """Hora (bruta) em que cada palavra do evento aparece = quando ela e falada."""
    cand = [w for w in words if at - 0.35 <= w["start"] < until + 0.2]
    j, last = 0, at
    for it in items:
        if it.get("whole") or it.get("t") is not None:
            it["t"] = it.get("t") if it.get("t") is not None else at
            continue
        key = norm(it["word"])
        found = None
        for k in range(j, min(len(cand), j + 6)):
            cw = norm(cand[k]["text"])
            if key and (cw == key or cw.startswith(key) or key.startswith(cw) and len(cw) >= 2):
                found = k
                break
        if found is not None:
            last = cand[found]["start"]
            j = found + 1
        else:
            last = last + 0.16
        it["t"] = max(at, last)


# ----------------------------------------------------------------------------- linha do tempo segura
def load_words_all(spec: dict) -> list[dict]:
    """Palavras 'drop' so somem da LEGENDA; continuam contando como fala (nao podem ser cortadas)."""
    fx = dict(spec.get("fixes", {}))
    drop = set(fx.get("drop", []))
    ws = load_words({**spec, "fixes": {**fx, "drop": []}})
    for w in ws:
        w["hide"] = w["i"] in drop
    return ws


def voice_env(src: Path) -> np.ndarray:
    a = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                                     capture_output=True, check=True).stdout, np.int16).astype(np.float32) / 32768
    f = a[: len(a) // 160 * 160].reshape(-1, 160)  # 10 ms
    return 20 * np.log10(np.sqrt((f ** 2).mean(1)) + 1e-9)


def safe_segments(words, keep, env, gap, pad_in, pad_out) -> list[dict]:
    """Cortes nas pausas, mas NUNCA corta trecho com voz sustentada (mesmo que o transcript nao tenha a palavra)."""
    segs = build_segments(words, keep, gap, pad_in, pad_out)
    raw = [[sg["s"], sg["e"]] for sg in segs]

    def keep_of(t):
        return next((i for i, (a, b) in enumerate(keep) if a - 0.05 <= t <= b + 0.05), -1)

    merged = [raw[0]]
    for s, e in raw[1:]:
        ps, pe = merged[-1]
        same = keep_of(pe) == keep_of(s)
        seg_env = env[int(pe * 100):int(s * 100)]
        loud = seg_env > -24
        run = best = 0
        for x in loud:
            run = run + 1 if x else 0
            best = max(best, run)
        if same and (best >= 6 or s - pe < 0.15):  # voz no "buraco" (>=60 ms) ou buraco minusculo: nao corta
            merged[-1][1] = e
        else:
            merged.append([s, e])
    # segue a voz ate ela realmente acabar (cauda de palavra, entonacao de pergunta) e desde onde ela comeca
    for k in range(len(merged)):
        s, e = merged[k]
        lim_e = merged[k + 1][0] - 0.02 if k + 1 < len(merged) else e + 0.35
        i = int(e * 100)
        while i < len(env) and i / 100 < min(e + 0.35, lim_e) and env[i:i + 20].max() > -34:
            i += 1
        e2 = max(e, i / 100 + 0.04)
        lim_s = merged[k - 1][1] + 0.02 if k > 0 else s - 0.2
        j = int(s * 100)
        while j > 0 and j / 100 > max(s - 0.2, lim_s) and env[max(0, j - 20):j].max() > -34:
            j -= 1
        kr = keep[keep_of(s)] if keep_of(s) >= 0 else (s, e)
        merged[k] = [max(kr[0], min(s, j / 100)), min(kr[1], min(e2, lim_e))]  # nunca passa dos limites do trecho escolhido
    # buraco que sobrou minusculo (< 0,15 s) vira "pulo" de 1-2 quadros = video parece travar: junta os trechos
    joined = [merged[0][:]]
    for s, e in merged[1:]:
        if s - joined[-1][1] < 0.15 and keep_of(s) == keep_of(joined[-1][1]):
            joined[-1][1] = max(joined[-1][1], e)
        else:
            joined.append([s, e])
    merged = joined
    out, t = [], 0.0
    for s, e in merged:
        # inicio no quadro inteiro: s "no meio" de 2 quadros (ex. 13,25 s = quadro 397,5) fazia o arredondamento
        # repetir quadro sim, quadro nao -> video "travando" (metade dos quadros) no trecho inteiro
        s = round(s * FPS) / FPS
        n = max(1, round((e - s) * FPS))
        out.append({"s": s, "e": s + n / FPS, "o": t, "n": n})
        t += n / FPS
    return out


def apply_lead(segs: list[dict], leads: list) -> list[dict]:
    """'lead' do spec: tempos brutos onde o trecho comeca EXATAMENTE (mantem a pausa antes da fala, sem encurtar)."""
    for t0 in leads:
        for sg in segs:
            if t0 <= sg["s"] < t0 + 1.5:
                s0 = round(t0 * FPS) / FPS
                sg["n"] = round((sg["e"] - s0) * FPS)
                sg["s"] = s0
    t = 0.0
    for sg in segs:
        sg["e"], sg["o"] = sg["s"] + sg["n"] / FPS, t
        t += sg["n"] / FPS
    return segs


class ClipReader(Reader):
    """B-roll com enquadramento correto (nao deforma clipe horizontal).
    mode: 'fill' = preenche 9:16 cortando (x_off -1..1 desloca o corte) | 'blurfit' = clipe inteiro no centro
    sobre um fundo desfocado dele mesmo."""

    def __init__(self, path: Path, start: float = 0.0, mode: str = "fill", x_off: float = 0.0, zoom: float = 1.0):
        self.w, self.h = W, H
        if mode == "blurfit":
            fc = (f"[0:v]split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=28:2,"
                  f"eq=brightness=-0.12:saturation=0.8[bg];[b]scale={int(W * zoom)}:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,fps={FPS}")
            args = ["-filter_complex", fc]
        else:
            vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                  f"crop={W}:{H}:(iw-{W})/2*(1+{x_off}):(ih-{H})/2,fps={FPS}")
            args = ["-vf", vf]
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-i", str(path), *args,
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.idx = -1
        self.last = None


TOP_H, TOP_0, TOP_TY = 1080, 720, 300  # b-roll "top": area de cima, inicio do degrade, quanto ele desce


class TopReader(Reader):
    """B-roll da tela dividida (mode "top"): clipe inteiro sobre um fundo desfocado dele mesmo, na area de cima.
    lift = sobe o clipe N px (pessoa na parte de baixo do clipe sumiria no degrade)."""

    def __init__(self, path: Path, start: float = 0.0, lift: int = 0):
        self.w, self.h = W, TOP_H
        fc = (f"[0:v]split[a][b];[a]scale={W}:{TOP_H}:force_original_aspect_ratio=increase,crop={W}:{TOP_H},"
              f"boxblur=24:2,eq=brightness=-0.10:saturation=0.85[bg];[b]scale={W}:{TOP_H}:force_original_aspect_ratio=decrease[fg];"
              f"[bg][fg]overlay=(W-w)/2:(H-h)/2-{lift},fps={FPS}")
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-i", str(path), "-filter_complex", fc,
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.idx = -1
        self.last = None


# ----------------------------------------------------------------------------- mascara da pessoa
class Segmenter:
    def __init__(self):
        import mediapipe as mp
        from mediapipe.tasks import python as mpt
        from mediapipe.tasks.python import vision
        self.mp = mp
        opts = vision.ImageSegmenterOptions(
            base_options=mpt.BaseOptions(model_asset_path=str(ASSETS / "selfie_segmenter.tflite")),
            output_confidence_masks=True)
        self.seg = vision.ImageSegmenter.create_from_options(opts)
        self.prev = None

    def __call__(self, rgb: np.ndarray) -> np.ndarray:
        small = cv2.resize(rgb, (360, 640))
        r = self.seg.segment(self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=np.ascontiguousarray(small)))
        m = np.squeeze(r.confidence_masks[0].numpy_view()).astype(np.float32)
        m = np.clip((m - 0.35) / 0.3, 0, 1)
        if self.prev is not None:  # estabiliza bordas entre quadros
            m = 0.6 * m + 0.4 * self.prev
        self.prev = m
        m = cv2.GaussianBlur(cv2.resize(m, (W, H)), (0, 0), 3)
        return m


# ----------------------------------------------------------------------------- grade
def make_lut():
    x = np.arange(256, dtype=np.float32) / 255
    s = x + 0.06 * np.sin(2 * np.pi * x) * -0.5  # leve curva em S
    s = np.clip(0.02 + s * 0.97, 0, 1)
    r = np.clip(s * 1.03 + 0.01, 0, 1)
    g = s
    b = np.clip(s * 0.94 + 0.015, 0, 1)
    return [(c * 255).astype(np.uint8) for c in (r, g, b)]


LUT = make_lut()


def grade(img: np.ndarray, bw: float = 0.0) -> np.ndarray:
    out = np.dstack([cv2.LUT(img[..., i], LUT[i]) for i in range(3)])
    if bw > 0:
        g = cv2.cvtColor(out, cv2.COLOR_RGB2GRAY)
        g = cv2.convertScaleAbs(g, alpha=1.08, beta=-6)
        g3 = np.dstack([g, g, g])
        out = cv2.addWeighted(g3, bw, out, 1 - bw, 0)
    return out


# ----------------------------------------------------------------------------- legenda minima (.ass)
def build_tiny_captions(words_out: list[dict], path: Path, y_at, size: int = 50) -> None:
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Montserrat SemiBold,{size},&H00FFFFFF,&H00FFFFFF,&H40000000,&H90000000,0,0,0,0,100,100,0.5,0,1,1.2,2.2,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    for i, w in enumerate(words_out):
        a = w["start"]
        nxt = words_out[i + 1]["start"] if i + 1 < len(words_out) else w["end"] + 0.3
        b = min(nxt, max(w["end"] + 0.25, a + 0.18))
        if b - a < 0.05:
            continue
        txt = w["text"].strip().rstrip(".,;:").lower()
        ev.append(f"Dialogue: 0,{ass_ts(a)},{ass_ts(b)},Cap,,0,0,0,,{{\\an5\\pos({W // 2},{int(y_at(a))})\\blur0.6}}{txt}")
    path.write_text(head + "\n".join(ev) + "\n", encoding="utf-8")


# ----------------------------------------------------------------------------- audio
def clean_voice(src: Path, out: Path) -> Path:
    if out.exists():
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    import noisereduce as nr
    import soundfile as sf
    sr = 48000
    a = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                                     capture_output=True, check=True).stdout, np.int16).astype(np.float32) / 32768
    win = sr // 20
    frames = a[: len(a) // win * win].reshape(-1, win)
    rms = np.sqrt((frames ** 2).mean(1))
    quiet = frames[rms <= np.percentile(rms, 6)].ravel()
    clean = nr.reduce_noise(y=a, sr=sr, y_noise=quiet, stationary=True, prop_decrease=0.9, n_fft=2048)
    sf.write(str(out), clean, sr)
    return out


def fix_noises(src_wav: Path, spec: dict, out: Path) -> Path:
    """Barulhos que o noisereduce nao pega (tempos brutos, na voz limpa):
    "mute": [[t0, t1], ...]       abafa um barulho FORA da fala (estalo, batida), com fade de 12 ms
    "hp_zones": [[t0, t1, hz]]    filtro de graves forte (6a ordem) so no trecho (pancada/ronco no microfone)
    "nr_zones": [[t0, t1]]        limpeza extra com o perfil de ruido DO PROPRIO trecho (ruido de fundo que so
                                  existe ali, ex. elastico esfregando; o perfil geral do video e mais baixo e nao pega)"""
    mutes, zones, nrz = spec.get("mute", []), spec.get("hp_zones", []), spec.get("nr_zones", [])
    if not mutes and not zones and not nrz:
        return src_wav
    import soundfile as sf
    from scipy.signal import butter, sosfiltfilt
    a, sr = sf.read(str(src_wav))
    f = int(0.012 * sr)
    for t0, t1 in nrz:
        import noisereduce as nr
        i0, i1 = int(t0 * sr), int(t1 * sr)
        seg = a[i0:i1]
        win = sr // 20
        fr = seg[: len(seg) // win * win].reshape(-1, win)
        rms = np.sqrt((fr ** 2).mean(1))
        noise = fr[rms <= np.percentile(rms, 15)].ravel()  # as pausas do proprio trecho
        cl = nr.reduce_noise(y=seg, sr=sr, y_noise=noise, stationary=True, prop_decrease=0.95, n_fft=2048)
        fl = int(0.05 * sr)
        w = np.ones(len(seg))
        w[:fl], w[-fl:] = np.linspace(0, 1, fl), np.linspace(1, 0, fl)  # entra e sai suave
        a[i0:i1] = seg * (1 - w) + cl * w
    for t0, t1, hz in zones:
        i0, i1 = int(t0 * sr), int(t1 * sr)
        seg = sosfiltfilt(butter(6, hz, "highpass", fs=sr, output="sos"), a[max(0, i0 - f):i1 + f])
        w = np.ones(len(seg))
        w[:f], w[-f:] = np.linspace(0, 1, f), np.linspace(1, 0, f)  # entra e sai sem clique
        a[max(0, i0 - f):i1 + f] = a[max(0, i0 - f):i1 + f] * (1 - w) + seg * w
    for t0, t1 in mutes:
        i0, i1 = int(t0 * sr), int(t1 * sr)
        g = np.ones(i1 - i0 + 2 * f)
        g[f:-f] = 0
        g[:f], g[-f:] = np.linspace(1, 0, f), np.linspace(0, 1, f)
        a[i0 - f:i1 + f] *= g
    sf.write(str(out), a, sr)
    return out


def build_voice(src_wav: Path, tl: Timeline, out: Path, highpass: int = 70) -> None:
    parts, labels = [], []
    for k, sg in enumerate(tl.segs):
        d = sg["n"] / FPS
        f = min(0.010, d / 4)
        parts.append(f"[0:a]atrim={sg['s']:.4f}:{sg['s'] + d:.4f},asetpts=PTS-STARTPTS,"
                     f"afade=t=in:d={f:.4f},afade=t=out:st={d - f:.4f}:d={f:.4f}[s{k}]")
        labels.append(f"[s{k}]")
    fc = ";".join(parts) + ";" + "".join(labels) + f"concat=n={len(labels)}:v=0:a=1,highpass=f={highpass}:poles=2," \
        "acompressor=threshold=-22dB:ratio=2:attack=15:release=200:makeup=1[v]"
    tmp = out.with_suffix(".pre.wav")
    script = out.with_suffix(".fc.txt")
    script.write_text(fc)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src_wav), "-filter_complex_script", str(script),
                    "-map", "[v]", "-ar", "48000", str(tmp)], check=True)
    m = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(tmp), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    j = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
    ln = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
          f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-af", ln, "-ar", "48000", "-ac", "2", str(out)], check=True)


def add_music(video: Path, music: Path, out: Path, level_db: float = -21.0, start: float = 0.0) -> None:
    """Musica por baixo, abaixando sozinha quando ele fala (sidechain)."""
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                             capture_output=True, text=True).stdout)
    fc = (f"[1:a]atrim={start}:{start + d},asetpts=PTS-STARTPTS,aresample=48000,volume={level_db}dB,"
          f"afade=t=in:d=0.6,afade=t=out:st={d - 1.6}:d=1.6[m];"
          f"[0:a]asplit=2[vo][key];"
          f"[m][key]sidechaincompress=threshold=0.035:ratio=5:attack=25:release=350[md];"
          f"[vo][md]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95[a]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-i", str(music), "-filter_complex", fc,
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", str(out)], check=True)


# ----------------------------------------------------------------------------- render
def render(spec_path: Path, preview: bool = False, until: float | None = None) -> Path:
    spec = load_spec(spec_path)
    name = spec["name"]
    job = OUT / (name + "_ref")
    job.mkdir(parents=True, exist_ok=True)
    src = ROOT / "raw" / f"{spec['source']}.mp4"

    words = load_words_all(spec)
    env = voice_env(src)
    tl = Timeline(safe_segments(words, spec["keep"], env, spec.get("gap", 0.28), spec.get("pad_in", 0.10),
                                spec.get("pad_out", 0.12)))
    dur = tl.dur if until is None else min(tl.dur, until)
    nfr = round(dur * FPS)
    print(f"[{name}] {len(tl.segs)} trechos, {tl.dur:.2f}s")

    words_out = []
    for w in words:
        mid = (w["start"] + w["end"]) / 2
        if not w.get("hide") and any(sg["s"] <= mid < sg["e"] for sg in tl.segs):
            words_out.append({"text": w["text"], "start": tl.to_out(w["start"]), "end": tl.to_out(w["end"])})

    # eventos de tipografia
    events = []
    for ev in spec.get("type", []):
        items = layout_event(ev)
        until_raw = ev["until"]
        match_times(items, words, ev["at"], until_raw)
        for it in items:
            it["o"] = tl.to_out(it["t"])
        events.append({**ev, "items": items, "o0": tl.to_out(ev["at"]), "o1": tl.to_out(until_raw)})

    brolls, pips, tops = [], [], []
    for b in spec.get("broll", []):
        o = tl.to_out(b["at"])
        {"pip": pips, "top": tops}.get(b.get("mode"), brolls).append({**b, "o0": o, "o1": o + b["dur"]})
    # tela dividida: b-roll em cima, ele desce; clipes seguidos (< 1,4 s) viram um grupo so (sem sobe-e-desce)
    top_groups = []
    for b in sorted(tops, key=lambda x: x["o0"]):
        if top_groups and b["o0"] - top_groups[-1][1] < 1.4:
            top_groups[-1][1] = max(top_groups[-1][1], b["o1"])
        else:
            top_groups.append([b["o0"], b["o1"]])

    def split_p(t):
        for a, b in top_groups:
            if a - 0.35 <= t <= b + 0.35:
                return ease((t - a + 0.35) / 0.35) * ease((b + 0.35 - t) / 0.35)
        return 0.0
    top_grad = np.clip((TOP_H - np.arange(TOP_H, dtype=np.float32)) / (TOP_H - TOP_0), 0, 1)
    top_grad = (top_grad * top_grad * (3 - 2 * top_grad))[:, None, None]
    top_readers: dict = {}
    PW, PH, PX, PY, PR = 840, 472, (W - 840) // 2, 48, 30  # janela acima da cabeca
    pip_mask = np.zeros((PH, PW), np.uint8)
    cv2.rectangle(pip_mask, (PR, 0), (PW - PR, PH), 255, -1)
    cv2.rectangle(pip_mask, (0, PR), (PW, PH - PR), 255, -1)
    for cx_, cy_ in ((PR, PR), (PW - PR, PR), (PR, PH - PR), (PW - PR, PH - PR)):
        cv2.circle(pip_mask, (cx_, cy_), PR, 255, -1, cv2.LINE_AA)
    pip_mask = cv2.GaussianBlur(pip_mask, (3, 3), 0).astype(np.float32)[..., None] / 255
    bw_win = [(tl.to_out(a), tl.to_out(b)) for a, b in spec.get("bw", [])]
    close_win = [(tl.to_out(a), tl.to_out(b), z) for a, b, z in spec.get("close", [])]
    face = spec.get("face", (540, 880))

    zooms = []
    for k, sg in enumerate(tl.segs):
        if k == 0:
            zooms.append(1.0)
        else:
            gap_cut = sg["s"] - tl.segs[k - 1]["e"]
            zooms.append((1.12 if zooms[-1] == 1.0 else 1.0) if gap_cut > 0.12 else zooms[-1])

    props = []
    for pi, pr in enumerate(spec.get("props", [])):
        cache = job / f"track_{pi}.json"
        if pr.get("static"):
            bx = pr["box"]
            c = (bx[0] + bx[2] / 2, bx[1] + bx[3] / 2, bx[2], bx[3])
            tr = {k: c for k in range(int((pr["t0"] - 0.6) * FPS), int((pr["t1"] + 0.6) * FPS) + 1)}
        elif pr.get("white"):
            tr = track_white(src, pr["t0"] - 0.5, pr["t1"] + 0.5, pr["init_t"], pr["box"], cache)
        else:
            tr = track_object(src, pr["t0"] - 0.5, pr["t1"] + 0.5, pr["init_t"], pr["box"], cache)
        props.append({**pr, "track": tr, "o0": tl.to_out(pr["t0"]), "o1": tl.to_out(pr["t1"])})

    # legenda minima
    cy0 = spec.get("cap_y", 1250)
    moves = [(tl.to_out(a), tl.to_out(b), yy) for a, b, yy in spec.get("cap_moves", [])]
    cap_y = lambda t: (next((yy for a, b, yy in moves if a - 0.2 <= t < b), cy0)  # noqa: E731
                       + (TOP_TY if any(a - 0.35 <= t <= b + 0.35 for a, b in top_groups) else 0))  # desce com ele
    cap_path = job / "captions.ass"
    build_tiny_captions(words_out, cap_path, cap_y, spec.get("cap_size", 50))

    # audio (voz limpa)
    clean = fix_noises(clean_voice(src, OUT / name / "voice_clean.wav"), spec, job / "voice_fixed.wav")
    voice = job / "voice.wav"
    build_voice(clean, tl, voice, spec.get("highpass", 70))

    body = job / f"{name}_body.mp4"
    enc = subprocess.Popen([
        "ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
        # caminhos relativos (cwd = pasta do job): evita o problema do "C:" no filtro ass do Windows
        "-i", "-", "-i", str(voice), "-vf",
        f"ass={cap_path.name}:fontsdir={os.path.relpath(ASSETS / 'fonts', job).replace(os.sep, '/')}",
        "-c:v", "libx264", "-preset", "veryfast" if preview else "medium", "-crf", "23" if preview else "17",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(body)],
        stdin=subprocess.PIPE, cwd=str(job))
    rd = Reader(src)
    segm = Segmenter()
    br_reader, br_cur = None, None
    pip_reader, pip_cur = None, None

    for fi in range(nfr):
        t = fi / FPS
        k, sg = tl.seg_at_out(t)
        raw = sg["s"] + (t - sg["o"])
        frame = rd.seek_to(int(round(raw * FPS)))
        if frame is None:
            break

        # enquadramento: jump-cut, janelas fechadas, zoom no objeto
        z, ax, ay = zooms[k], face[0], face[1]
        for a, b, zz in close_win:
            if a <= t < b:
                z = zz
        for pr in props:
            ramp = 0.3
            if pr["o0"] - ramp <= t <= pr["o1"] + ramp:
                wgt = ease((t - (pr["o0"] - ramp)) / ramp) * ease(((pr["o1"] + ramp) - t) / ramp)
                kk = int(round(raw * FPS))
                ks = pr["track"]
                if kk not in ks:
                    kk = min(ks, key=lambda q: abs(q - kk))
                ocx, ocy = ks[kk][0], ks[kk][1]
                pz = pr.get("zoom", 1.25)
                z = z + (pz - z) * wgt
                ax = ax + (ocx - ax) * wgt
                ay = ay + (ocy - ay) * wgt
        if abs(z - 1) > 1e-4:
            M = np.float32([[z, 0, (1 - z) * ax], [0, z, (1 - z) * ay]])
            img = cv2.warpAffine(frame, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        else:
            img = frame.copy()

        # b-roll em destaque (tela cheia, entra com zoom suave e fusao curta)
        cur = next((b for b in brolls if b["o0"] <= t < b["o1"]), None)
        if cur is not br_cur:
            if br_reader:
                br_reader.close()
            if cur and cur.get("file"):
                br_reader = ClipReader(ROOT / cur["file"], cur.get("src_start", 0.0), cur.get("mode", "fill"),
                                       cur.get("x_off", 0.0), cur.get("fg_zoom", 1.0))
            else:
                br_reader = Reader(EDIT / "broll" / "clips" / f"{cur['clip']}.mp4", cur.get("src_start", 0.0)) if cur else None
            br_cur = cur
        on_broll = False
        if cur:
            bf = br_reader.read()
            if bf is not None:
                e_ = t - cur["o0"]
                zb = 1.07 - 0.07 * ease(e_ / 0.5)
                Mb = np.float32([[zb, 0, (1 - zb) * W / 2], [0, zb, (1 - zb) * H / 2]])
                bimg = cv2.warpAffine(bf, Mb, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
                fin = ease(e_ / 0.12)
                fout = ease((cur["o1"] - t) / 0.10)
                mix = min(fin, fout)
                img = cv2.addWeighted(bimg, mix, img, 1 - mix, 0)
                on_broll = mix > 0.5

        # tela dividida (mode "top"): ele desce, b-roll em cima sumindo em degrade ate ele
        p = split_p(t)
        if p > 1e-3:
            img = cv2.warpAffine(img, np.float32([[1, 0, 0], [0, 1, TOP_TY * p]]), (W, H),
                                 flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            for ti, tb in enumerate(tops):
                if not (tb["o0"] - 0.01 <= t <= tb["o1"] + 0.25):
                    if ti in top_readers:
                        top_readers.pop(ti).close()
                    continue
                if ti not in top_readers:
                    top_readers[ti] = TopReader(ROOT / tb["file"], tb.get("src_start", 0.0), tb.get("lift", 0))
                content = top_readers[ti].read()
                if content is None:
                    continue
                a_ = min(ease((t - tb["o0"]) / 0.2), ease((tb["o1"] + 0.25 - t) / 0.25)) * ease(p / 0.6)
                mA = top_grad * a_
                img[:TOP_H] = (img[:TOP_H].astype(np.float32) * (1 - mA) + content.astype(np.float32) * mA).astype(np.uint8)
            on_broll = on_broll or p > 0.5  # texto nao passa "atras" de gente do b-roll

        # preto e branco
        bw = 0.0
        for a, b in bw_win:
            if a <= t < b:
                bw = 1.0
        img = grade(img, bw)

        # tipografia (atras da pessoa)
        active = [e for e in events if e["o0"] - 0.05 <= t <= e["o1"] + 0.25]
        if active:
            layer = np.zeros((H, W, 4), np.float32)
            for e in active:
                fade = ease((e["o1"] + 0.25 - t) / 0.25)
                for it in e["items"]:
                    if t < it["o"]:
                        continue
                    e_in = ease((t - it["o"]) / 0.12)
                    a = e_in * fade
                    if a <= 0.01:
                        continue
                    fp = it.get("font", FONT_COND)
                    stroke = spec.get("giant_stroke", 0.0)  # contorno preto nas palavras grandes
                    spr = word_sprite(it["word"], it["size"], it["color"], fp, stroke=stroke)
                    base = baseline_of(it["word"], it["size"], it["color"], fp, stroke=stroke)
                    cy_spr = it["by"] - base + spr.shape[0] / 2
                    sc = 1.0 + (0.08 if it.get("whole") else 0.05) * (1 - ease((t - it["o"]) / 0.22))
                    if abs(sc - 1) > 1e-3:
                        spr = cv2.resize(spr, (int(spr.shape[1] * sc), int(spr.shape[0] * sc)), interpolation=cv2.INTER_LINEAR)
                    h_, w_ = spr.shape[:2]
                    x0, y0 = int(it["x"] - w_ / 2), int(cy_spr - h_ / 2)
                    fx0, fy0, fx1, fy1 = max(0, x0), max(0, y0), min(W, x0 + w_), min(H, y0 + h_)
                    if fx1 <= fx0 or fy1 <= fy0:
                        continue
                    s = spr[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0] * a
                    L = layer[fy0:fy1, fx0:fx1]
                    L[..., :3] = s[..., :3] + L[..., :3] * (1 - s[..., 3:4])
                    L[..., 3:4] = s[..., 3:4] + L[..., 3:4] * (1 - s[..., 3:4])
            behind = any(e.get("behind", True) for e in active) and not on_broll
            A = layer[..., 3:4]
            if behind:
                person = segm(img)[..., None]
                A = A * (1 - person)
                col = layer[..., :3] * (1 - person)
            else:
                col = layer[..., :3]
            img = (img.astype(np.float32) * (1 - A) + col * 255).clip(0, 255).astype(np.uint8)

        # b-roll em janela (pip) acima da cabeca
        pc = next((b for b in pips if b["o0"] <= t < b["o1"]), None)
        if pc is not pip_cur:
            if pip_reader:
                pip_reader.close()
            pip_reader = Reader(ROOT / pc["file"], pc.get("src_start", 0.0), size=(PW, PH)) if pc else None
            pip_cur = pc
        if pc:
            pf = pip_reader.read()
            if pf is not None:
                e_ = t - pc["o0"]
                a = min(ease(e_ / 0.22), ease((pc["o1"] - t) / 0.18))
                sc = 0.92 + 0.08 * ease(e_ / 0.3)
                cw, ch = int(PW * sc), int(PH * sc)
                win = cv2.resize(pf, (cw, ch), interpolation=cv2.INTER_AREA).astype(np.float32)
                m = cv2.resize(pip_mask, (cw, ch))[..., None] * a
                x0, y0 = W // 2 - cw // 2, PY + (PH - ch) // 2
                base = img.astype(np.float32)
                # sombra
                sh = np.zeros((H, W), np.float32)
                sh[y0 + 12:y0 + ch + 12, x0:x0 + cw] = m[..., 0]
                sh = cv2.GaussianBlur(sh, (0, 0), 14)[..., None] * 0.55
                base = base * (1 - sh)
                # borda laranja (6px) + conteudo
                # monta a janela inteira (borda + imagem) opaca e so depois aplica o fade (sem "vazar" laranja)
                bm = cv2.resize(pip_mask, (cw + 12, ch + 12))[..., None]
                m1 = cv2.resize(pip_mask, (cw, ch))[..., None]
                card = np.empty((ch + 12, cw + 12, 3), np.float32)
                card[:] = np.array(LIME, np.float32)
                inner = card[6:6 + ch, 6:6 + cw]
                inner[:] = inner * (1 - m1) + grade(win.astype(np.uint8)).astype(np.float32) * m1
                roi = base[y0 - 6:y0 + ch + 6, x0 - 6:x0 + cw + 6]
                roi[:] = roi * (1 - bm * a) + card * (bm * a)
                img = base.clip(0, 255).astype(np.uint8)

        enc.stdin.write(np.ascontiguousarray(img).tobytes())
        if fi % 300 == 0:
            print(f"  quadro {fi}/{nfr}", flush=True)

    rd.close()
    if br_reader:
        br_reader.close()
    if pip_reader:
        pip_reader.close()
    enc.stdin.close()
    enc.wait()

    final_nomusic = job / f"{name}_nomusic.mp4"
    card = EDIT / "endcard" / "endcard.mp4"
    if until is None and spec.get("endcard", True) and card.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(body), "-i", str(card), "-filter_complex",
                        "[1:a]volume=0.6[ca];[0:v][0:a][1:v][ca]concat=n=2:v=1:a=1[v][a]", "-map", "[v]", "-map", "[a]",
                        "-c:v", "libx264", "-preset", "veryfast" if preview else "medium", "-crf", "23" if preview else "17",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", str(final_nomusic)], check=True)
    else:
        body.replace(final_nomusic)
    final = job / f"{name}_REF.mp4"
    music = spec.get("music")
    if music:
        add_music(final_nomusic, ASSETS / "music" / music, final, spec.get("music_db", -21.0), spec.get("music_start", 0.0))
    else:
        final_nomusic.replace(final)
    print(f"[{name}] PRONTO -> {final}")
    return final


if __name__ == "__main__":
    u = None
    for a in sys.argv:
        if a.startswith("--until="):
            u = float(a.split("=")[1])
    render(Path(sys.argv[1]), preview="--preview" in sys.argv, until=u)
