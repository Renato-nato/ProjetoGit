"""Motor v4 - estilo 'clip' (referencia @iassminmoraes).

- legenda por frase, palavra aparece quando e falada, dois pesos:
  palavra-chave = Montserrat ExtraBold laranja com brilho leve | resto = Montserrat Medium branco translucido
  letras juntas (tracking negativo), minusculas, no peito (abaixo do queixo, acima do prato)
- palavra gigante com brilho so no gancho, nos numeros-chave e no CTA
- tela dividida: fundo escuro, Guilherme num cartao arredondado embaixo, painel em cima
  (clipe real ou cartao de dados animado); transicao suave, sem pulo/tremida
- mantem: corte seguro da fala, zoom nos objetos que ele mostra, jump-cut alternado, grade, audio limpo
Rodar (dentro de editor-reels/engine, com o venv ativo):  python engine_clip.py specs_clip/v1.py [--preview] [--until=SEG]
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import EDIT, FPS, H, OUT, ROOT, W, Reader, Timeline, ease, load_spec, norm, track_object, track_white  # noqa: E402
from engine_ref import (ASSETS, FONT_COND, LIME, WHITE, Segmenter, add_music, baseline_of, build_voice, cap_h, layout_event, text_width, clean_voice, fnt,  # noqa: E402
                        grade, load_words_all, safe_segments, voice_env, word_sprite)

MS = str(ASSETS / "fonts") + "/"
FONT_XB = MS + "Montserrat-ExtraBold.otf"
FONT_MED = MS + "Montserrat-Medium.otf"
FONT_SB = MS + "Montserrat-SemiBold.otf"
BG = np.array((20, 20, 22), np.float32)
CARD = (34, 34, 39)

# tela dividida: cartao do Guilherme (embaixo) e painel (em cima)
S_SPLIT = 900 / W                      # escala do video dele no cartao
TX, TY = 90.0, 730 - 540 * S_SPLIT     # origem: fonte y=540 fica no topo do cartao
CARD_R = (90, 730, 990, 1872)          # retangulo final do cartao dele
PAN = (90, 96, 990, 676)               # painel de cima (900 x 580)
PW, PH = PAN[2] - PAN[0], PAN[3] - PAN[1]
CW, CH = 900, 580                      # tamanho de desenho dos cartoes de dados
# estilo "fade" (sem bordas): b-roll em cima na largura toda, sumindo em degrade ate ele, que desce um pouco
FADE_H, FADE_0, FADE_TY = 1080, 720, 300


# ----------------------------------------------------------------------------- sprites
_cs: dict = {}


def cap_sprite(text: str, size: int, key: bool):
    """Palavra da legenda. Retorna (RGBA premult float32, baseline_y, largura_tinta)."""
    k = (text, size, key)
    if k in _cs:
        return _cs[k]
    f = fnt(FONT_XB if key else FONT_MED, size)
    track = -0.035 * size
    ws = [f.getlength(c) for c in text]
    tw = sum(ws) + track * max(0, len(text) - 1)
    asc, desc = f.getmetrics()
    pad = int(size * 0.45)
    im = Image.new("L", (int(tw + 2 * pad) + 2, asc + desc + 2 * pad), 0)
    d = ImageDraw.Draw(im)
    x = pad
    for c, cw in zip(text, ws):
        d.text((x, pad), c, font=f, fill=255)
        x += cw + track
    a = np.asarray(im, np.float32) / 255
    sh = np.asarray(im.filter(ImageFilter.GaussianBlur(size * 0.14)), np.float32) / 255 * 0.55
    at = a * (1.0 if key else 0.80)
    col = np.array(LIME if key else WHITE, np.float32) / 255
    if key:
        gl = np.asarray(im.filter(ImageFilter.GaussianBlur(size * 0.22)), np.float32) / 255 * 0.30
        cov = at + gl * (1 - at)
        rgb = col * cov[..., None]
        A = cov + sh * (1 - cov)
    else:
        rgb = col * at[..., None]
        A = at + sh * (1 - at)
    out = (np.dstack([rgb, A]).astype(np.float32), pad + asc, tw, pad)
    _cs[k] = out
    return out


def paste(dst: np.ndarray, spr: np.ndarray, cx: float, cy: float, a: float, sc: float = 1.0) -> None:
    """Compoe sprite RGBA premultiplicado (0..1) em dst float32 0..255, centrado em (cx, cy)."""
    if a <= 0.01:
        return
    if abs(sc - 1) > 1e-3:
        spr = cv2.resize(spr, (max(1, int(spr.shape[1] * sc)), max(1, int(spr.shape[0] * sc))), interpolation=cv2.INTER_AREA)
    h, w = spr.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    fx0, fy0, fx1, fy1 = max(0, x0), max(0, y0), min(dst.shape[1], x0 + w), min(dst.shape[0], y0 + h)
    if fx1 <= fx0 or fy1 <= fy0:
        return
    s = spr[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0] * a
    R = dst[fy0:fy1, fx0:fx1]
    R[:] = R * (1 - s[..., 3:4]) + s[..., :3] * 255


def paste_rgba(dst: np.ndarray, spr: np.ndarray, cx: float, cy: float, a: float, sc: float = 1.0) -> None:
    """Como paste, mas numa camada RGBA premultiplicada (0..1)."""
    if a <= 0.01:
        return
    if abs(sc - 1) > 1e-3:
        spr = cv2.resize(spr, (max(1, int(spr.shape[1] * sc)), max(1, int(spr.shape[0] * sc))), interpolation=cv2.INTER_LINEAR)
    h, w = spr.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    fx0, fy0, fx1, fy1 = max(0, x0), max(0, y0), min(dst.shape[1], x0 + w), min(dst.shape[0], y0 + h)
    if fx1 <= fx0 or fy1 <= fy0:
        return
    s = spr[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0] * a
    L = dst[fy0:fy1, fx0:fx1]
    L[:] = s + L * (1 - s[..., 3:4])


def rrect_mask(h: int, w: int, box, r: float) -> np.ndarray:
    m = np.zeros((h, w), np.uint8)
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    r = int(max(0, min(r, (x1 - x0) / 2, (y1 - y0) / 2)))
    if r == 0:
        m[max(0, y0):y1, max(0, x0):x1] = 255
    else:
        cv2.rectangle(m, (x0 + r, y0), (x1 - r, y1 - 1), 255, -1)
        cv2.rectangle(m, (x0, y0 + r), (x1 - 1, y1 - r), 255, -1)
        for cx, cy in ((x0 + r, y0 + r), (x1 - r - 1, y0 + r), (x0 + r, y1 - r - 1), (x1 - r - 1, y1 - r - 1)):
            cv2.circle(m, (cx, cy), r, 255, -1, cv2.LINE_AA)
    return m.astype(np.float32) / 255


# ----------------------------------------------------------------------------- legenda por frase
def build_phrases(words_out: list[dict], keys: set, max_words: int = 5, max_chars: int = 24) -> list[dict]:
    phrases, cur = [], []
    for w in words_out:
        txt = w["text"].strip().lower().strip(".,;:!?")
        if not txt:
            continue
        if cur and (w["start"] - cur[-1]["end"] > 0.45 or len(cur) >= max_words
                    or sum(len(x["t"]) + 1 for x in cur) + len(txt) > max_chars):
            phrases.append(cur)
            cur = []
        cur.append({"t": txt, "start": w["start"], "end": w["end"], "key": norm(txt) in keys})
        if w["text"].rstrip()[-1:] in ".?!" and len(cur) >= 2:
            phrases.append(cur)
            cur = []
    if cur:
        phrases.append(cur)
    out = []
    for i, ph in enumerate(phrases):
        a = ph[0]["start"]
        nxt = phrases[i + 1][0]["start"] if i + 1 < len(phrases) else ph[-1]["end"] + 0.5
        b = min(nxt, ph[-1]["end"] + 0.7)
        out.append({"words": ph, "a": a, "b": b})
    return out


def layout_phrase(ph: dict, size: int, maxw: float = 830) -> None:
    """Posicoes relativas ao centro do bloco (1 ou 2 linhas, quebra equilibrada)."""
    ws = ph["words"]
    for w in ws:
        s = int(size * (1.12 if w["key"] else 1.0))
        spr, base, tw, pad = cap_sprite(w["t"], s, w["key"])
        w.update(spr=spr, base=base, tw=tw, pad=pad, size=s)
    gap = size * 0.24
    tot = sum(w["tw"] for w in ws) + gap * (len(ws) - 1)
    lines = [ws]
    if tot > maxw and len(ws) > 1:
        best, cut = 1e9, 1
        for c in range(1, len(ws)):
            l1 = sum(w["tw"] for w in ws[:c]) + gap * (c - 1)
            l2 = sum(w["tw"] for w in ws[c:]) + gap * (len(ws) - c - 1)
            if max(l1, l2) < best:
                best, cut = max(l1, l2), c
        lines = [ws[:cut], ws[cut:]]
    lh = size * 1.12
    y_base0 = -(len(lines) - 1) * lh / 2 + size * 0.36
    for li, ln in enumerate(lines):
        lw = sum(w["tw"] for w in ln) + gap * (len(ln) - 1)
        x = -lw / 2
        for w in ln:
            w["dx"] = x + w["tw"] / 2
            w["dy_base"] = y_base0 + li * lh
            x += w["tw"] + gap


# ----------------------------------------------------------------------------- painel: clipe real
class PanelReader(Reader):
    def __init__(self, path: Path, start: float = 0.0, yc: float = 0.5, xc: float = 0.5, size=(PW, PH)):
        PW, PH = size  # noqa: N806
        self.w, self.h = PW, PH
        # imagem inteira (sem cortar a pessoa) centrada sobre um fundo desfocado dela mesma
        vf = (f"split[a][b];[a]scale={PW}:{PH}:force_original_aspect_ratio=increase,crop={PW}:{PH},"
              f"boxblur=24:2,eq=brightness=-0.10:saturation=0.85[bg];"
              f"[b]scale={PW}:{PH}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,fps={FPS}")
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-i", str(path), "-filter_complex", vf,
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.idx = -1
        self.last = None
        self.eof = False


# ----------------------------------------------------------------------------- painel: cartoes de dados
def _txt(d: ImageDraw.ImageDraw, xy, text, font, fill, anchor="la"):
    d.text(xy, text, font=font, fill=fill, anchor=anchor)


def card_frame(kind: str, lt: float, beats: dict) -> np.ndarray:
    """Cartao de dados animado (900x580). lt = tempo desde que o painel entrou; beats = {nome: tempo local}."""
    S = 2  # desenha em 2x e reduz (bordas limpas)
    PW, PH = CW, CH  # noqa: N806
    im = Image.new("RGBA", (PW * S, PH * S), (tuple(int(v) for v in BG) if FADE else CARD) + (255,))
    d = ImageDraw.Draw(im)
    orange = LIME + (255,)
    grey = (58, 58, 64, 255)
    soft = (255, 255, 255, 150)

    def ap(name, dur=0.25):
        return ease((lt - beats.get(name, 0)) / dur) if lt >= beats.get(name, 0) else 0.0

    X0, X1 = 60 * S, (PW - 60) * S
    if kind == "comp":
        _txt(d, (X0, 58 * S), "100 g de carne", fnt(FONT_SB, 46 * S), soft)
        by0, by1 = 280 * S, 372 * S
        d.rounded_rectangle((X0, by0, X1, by1), radius=22 * S, fill=grey)
        f = 0.26 * ease(lt / 0.6)
        xe = X0 + (X1 - X0) * f
        if xe - X0 > 44 * S:
            d.rounded_rectangle((X0, by0, xe, by1), radius=22 * S, fill=orange)
        a = ap("start", 0.4)
        _txt(d, (X0, by0 - 22 * S), "26 g", fnt(FONT_COND, 150 * S), LIME + (int(255 * a),), "ls")
        _txt(d, (X0, by1 + 18 * S), "proteína", fnt(FONT_SB, 40 * S), (255, 255, 255, int(230 * a)), "la")
        # o resto: chips aparecem quando ele fala
        x = max(X0 + (X1 - X0) * 0.26 + 36 * S, X0 + fnt(FONT_COND, 150 * S).getlength("26 g") + 44 * S)
        _txt(d, (x, by0 - 24 * S), "o resto", fnt(FONT_MED, 44 * S), (255, 255, 255, int(170 * ap("resto"))), "ls")
        cx, cy = X0, 500 * S
        for name, label in (("agua", "água"), ("gordura", "gordura"), ("liga", "o que dá liga")):
            a = ap(name, 0.2)
            if a <= 0:
                continue
            fo = fnt(FONT_SB, 42 * S)
            tw = fo.getlength(label)
            yy = cy + (1 - a) * 14 * S
            d.rounded_rectangle((cx, yy - 38 * S, cx + tw + 56 * S, yy + 38 * S), radius=38 * S,
                                outline=(255, 255, 255, int(120 * a)), width=2 * S, fill=(52, 52, 58, int(255 * a)))
            _txt(d, (cx + 28 * S, yy), label, fo, (255, 255, 255, int(240 * a)), "lm")
            cx += tw + 56 * S + 22 * S
    elif kind == "meta":
        _txt(d, (X0, 58 * S), "proteína do dia", fnt(FONT_SB, 46 * S), soft)
        by0, by1 = 300 * S, 392 * S
        d.rounded_rectangle((X0, by0, X1, by1), radius=36 * S, fill=grey)
        f = 0.26 * ease((lt - beats.get("comeu", 0)) / 0.7) if lt >= beats.get("comeu", 0) else 0
        xe = X0 + (X1 - X0) * f
        if xe - X0 > 72 * S:
            d.rounded_rectangle((X0, by0, xe, by1), radius=36 * S, fill=orange)
        a = ap("comeu", 0.35)
        _txt(d, (X0, by0 - 24 * S), "26 g", fnt(FONT_COND, 150 * S), LIME + (int(255 * a),), "ls")
        _txt(d, (X0, by1 + 22 * S), "comeu", fnt(FONT_SB, 40 * S), (255, 255, 255, int(220 * a)), "la")
        a = ap("meta", 0.35)
        if a > 0:
            d.rounded_rectangle((X0 - 4 * S, by0 - 4 * S, X1 + 4 * S, by1 + 4 * S), radius=40 * S,
                                outline=(255, 255, 255, int(200 * a)), width=3 * S)
            _txt(d, (X1, by0 - 24 * S), "~100 g", fnt(FONT_COND, 150 * S), (255, 255, 255, int(255 * a)), "rs")
            _txt(d, (X1, by1 + 22 * S), "precisava", fnt(FONT_SB, 40 * S), (255, 255, 255, int(220 * a)), "ra")
    arr = np.asarray(im.resize((PW, PH), Image.LANCZOS).convert("RGB"))
    return arr


# ----------------------------------------------------------------------------- render
FADE = False


def render(spec_path: Path, preview: bool = False, until: float | None = None) -> Path:
    global FADE
    spec = load_spec(spec_path)
    FADE = spec.get("split_style") == "fade"
    fade_grad = np.clip((FADE_H - np.arange(FADE_H, dtype=np.float32)) / (FADE_H - FADE_0), 0, 1)
    fade_grad = (fade_grad * fade_grad * (3 - 2 * fade_grad))[:, None, None]  # suave
    name = spec["name"]
    job = OUT / (name + "_clip")
    job.mkdir(parents=True, exist_ok=True)
    src = ROOT / "raw" / f"{spec['source']}.mp4"

    words = load_words_all(spec)
    env = voice_env(src)
    tl = Timeline(safe_segments(words, spec["keep"], env, spec.get("gap", 0.28), spec.get("pad_in", 0.10),
                                spec.get("pad_out", 0.12)))
    dur = tl.dur if until is None else min(tl.dur, until)
    nfr = round(dur * FPS)
    print(f"[{name}] {len(tl.segs)} trechos, {tl.dur:.2f}s")

    # gigantes / CTA (tempos brutos -> saida)
    giants = []
    head_top = spec.get("head_top", 650)  # topo da cabeca (ja contando o jump-cut de 1,10x)
    for g in spec.get("giants", []):
        if g.get("type") == "giant" and g.get("y", "above") == "above":
            # destaque ACIMA da cabeca: a base da palavra fica ~35 px acima do topo da cabeca
            size = g.get("size", 420)
            while text_width(g["text"], size) > W - 60 and size > 60:
                size -= 8
            # (no layout "giant" o y e o centro da letra)
            g = {**g, "size": size, "y": max(30 + cap_h(size) / 2, head_top - 35 - cap_h(size) / 2)}
        items = layout_event(g)
        for it in items:
            it["o"] = tl.to_out(g["at"])
        giants.append({**g, "items": items, "o0": tl.to_out(g["at"]), "o1": tl.to_out(g["until"])})

    def in_giant(t):
        return False  # legenda continua durante o destaque (ele fica em cima, a legenda no peito)

    words_out = []
    for w in words:
        mid = (w["start"] + w["end"]) / 2
        if not w.get("hide") and any(sg["s"] <= mid < sg["e"] for sg in tl.segs):
            o = tl.to_out(w["start"])
            if not in_giant(o):
                words_out.append({"text": w["text"], "start": o, "end": tl.to_out(w["end"])})
    keys = {norm(k) for k in spec.get("keywords", [])}
    cap_size = spec.get("cap_size", 60)
    phrases = build_phrases(words_out, keys)
    for ph in phrases:
        layout_phrase(ph, cap_size)
        ph["b"] = min(ph["b"], next((g["o0"] for g in giants if ph["a"] < g["o0"] < ph["b"]), ph["b"]))

    # paineis (tela dividida) e grupos continuos
    panels = []
    for p in spec.get("panels", []):
        o0, o1 = tl.to_out(p["at"]), tl.to_out(p["until"])
        beats = {k: tl.to_out(v) - o0 for k, v in p.get("beats", {}).items()}
        panels.append({**p, "o0": o0, "o1": o1, "beats": beats})
    groups = []
    for p in panels:
        if groups and p["o0"] - groups[-1][1] < 1.4 and not any(groups[-1][1] <= g["o0"] <= p["o0"] for g in giants):
            groups[-1][1] = p["o1"]
        else:
            groups.append([p["o0"], p["o1"]])
    for i, p in enumerate(panels):  # painel anterior fica ate o proximo terminar de entrar
        if i + 1 < len(panels) and any(a <= p["o1"] and panels[i + 1]["o0"] <= b for a, b in groups):
            p["hold"] = max(p["o1"], panels[i + 1]["o0"] + 0.35)
        else:  # ultimo do grupo: some junto com a saida da tela dividida (sem painel vazio)
            p["hold"] = p["o1"] + 0.35

    def split_p(t):
        for a, b in groups:
            if a - 0.01 <= t <= b + 0.75:
                return ease((t - a) / 0.4) * ease((b + 0.75 - t) / 0.4)
        return 0.0

    close_win = [(tl.to_out(a), tl.to_out(b), z) for a, b, z in spec.get("close", [])]
    face = spec.get("face", (540, 880))
    zooms = []
    for k, sg in enumerate(tl.segs):
        if k == 0:
            zooms.append(1.0)
        else:
            gap_cut = sg["s"] - tl.segs[k - 1]["e"]
            zooms.append((1.10 if zooms[-1] == 1.0 else 1.0) if gap_cut > 0.12 else zooms[-1])

    props = []
    for pi, pr in enumerate(spec.get("props", [])):
        cache = job / f"track_{pi}.json"
        if pr.get("white"):
            tr = track_white(src, pr["t0"] - 0.5, pr["t1"] + 0.5, pr["init_t"], pr["box"], cache)
        else:
            tr = track_object(src, pr["t0"] - 0.5, pr["t1"] + 0.5, pr["init_t"], pr["box"], cache)
        props.append({**pr, "track": tr, "o0": tl.to_out(pr["t0"]), "o1": tl.to_out(pr["t1"])})

    clean = clean_voice(src, OUT / name / "voice_clean.wav")
    voice = job / "voice.wav"
    build_voice(clean, tl, voice, spec.get("highpass", 70))

    body = job / f"{name}_body.mp4"
    enc = subprocess.Popen([
        "ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "-", "-i", str(voice),
        "-c:v", "libx264", "-preset", "veryfast" if preview else "medium", "-crf", "23" if preview else "17",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(body)],
        stdin=subprocess.PIPE)
    rd = Reader(src)
    readers: dict = {}
    pan_mask = rrect_mask(PH + 2, PW + 2, (1, 1, PW + 1, PH + 1), 34)[..., None]
    cap_y = spec.get("cap_y", 1160)
    segm = Segmenter()

    for fi in range(nfr):
        t = fi / FPS
        k, sg = tl.seg_at_out(t)
        raw = sg["s"] + (t - sg["o"])
        frame = rd.seek_to(int(round(raw * FPS)))
        if frame is None:
            break

        # enquadramento (jump-cut, janelas fechadas, zoom no objeto que ele mostra)
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
                z = z + (pr.get("zoom", 1.22) - z) * wgt
                ax = ax + (ks[kk][0] - ax) * wgt
                ay = ay + (ks[kk][1] - ay) * wgt

        p = split_p(t)
        if FADE:
            s, tx, ty = 1.0, 0.0, FADE_TY * p
        else:
            s = 1 + (S_SPLIT - 1) * p
            tx, ty = TX * p, TY * p
        # matriz final = split o zoom
        M = np.float32([[s * z, 0, s * (1 - z) * ax + tx], [0, s * z, s * (1 - z) * ay + ty]])
        if p <= 1e-3 and abs(z - 1) < 1e-4:
            guy = frame
        else:
            guy = cv2.warpAffine(frame, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        guy = grade(guy)
        if FADE:
            img = guy.astype(np.float32)
        elif p > 1e-3:
            box = (CARD_R[0] * p, CARD_R[1] * p, W - (W - CARD_R[2]) * p, H - (H - CARD_R[3]) * p)
            m = rrect_mask(H, W, box, 40 * p)[..., None]
            img = BG * (1 - m) + guy.astype(np.float32) * m
        else:
            img = guy.astype(np.float32)

        # painel de cima
        for pi, pn in enumerate(panels):
            if not (pn["o0"] - 0.01 <= t <= pn["hold"] + 0.35):
                if pi in readers:
                    readers.pop(pi).close()
                continue
            lt = t - pn["o0"]
            if FADE:
                if pn.get("card"):
                    content = np.empty((FADE_H, W, 3), np.float32)
                    content[:] = BG
                    cy0, chh = pn.get("card_y", 110), int(CH * W / CW)
                    content[cy0:cy0 + chh] = cv2.resize(card_frame(pn["card"], lt, pn["beats"]), (W, chh),
                                                        interpolation=cv2.INTER_CUBIC)
                else:
                    if pi not in readers:
                        readers[pi] = PanelReader(ROOT / pn["file"], pn.get("src_start", 0.0), size=(W, FADE_H))
                    content = readers[pi].read()
                    if content is None:
                        continue
                    content = grade(content).astype(np.float32)
                a = ease(lt / 0.35) * ease((pn["hold"] + 0.35 - t) / 0.35) * ease(p / 0.6)
                if a <= 0.01:
                    continue
                sc = 1.04 - 0.04 * ease(lt / 0.6)  # leve aproximacao ao entrar
                if sc > 1.001:
                    Mc = np.float32([[sc, 0, (1 - sc) * W / 2], [0, sc, (1 - sc) * FADE_H / 2]])
                    content = cv2.warpAffine(content, Mc, (W, FADE_H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
                mA = fade_grad * a
                img[:FADE_H] = img[:FADE_H] * (1 - mA) + content * mA
                continue
            if pn.get("card"):
                content = card_frame(pn["card"], lt, pn["beats"])
            else:
                if pi not in readers:
                    readers[pi] = PanelReader(ROOT / pn["file"], pn.get("src_start", 0.0), pn.get("yc", 0.5), pn.get("xc", 0.5))
                content = readers[pi].read()
                if content is None:
                    continue
                content = grade(content)
            a = ease(lt / 0.35) * ease((pn["hold"] + 0.35 - t) / 0.35) * ease((p - 0.5) / 0.5)
            if a <= 0.01:
                continue
            dy = int(round((1 - ease(lt / 0.45)) * -46))
            sc = 0.96 + 0.04 * ease(lt / 0.45)
            cw, ch = int(PW * sc), int(PH * sc)
            cont = cv2.resize(content, (cw, ch), interpolation=cv2.INTER_AREA).astype(np.float32)
            mm = cv2.resize(pan_mask, (cw, ch))[..., None] * a
            x0 = PAN[0] + (PW - cw) // 2
            y0 = PAN[1] + (PH - ch) // 2 + dy
            # sombra suave
            sh = np.zeros((H, W), np.float32)
            y0c, y1c = max(0, y0 + 14), min(H, y0 + 14 + ch)
            sh[y0c:y1c, x0:x0 + cw] = mm[: y1c - y0c, :, 0]
            sh = cv2.GaussianBlur(sh, (0, 0), 18)[..., None] * 0.5
            img *= (1 - sh)
            ys0, ys1 = max(0, y0), min(H, y0 + ch)
            R = img[ys0:ys1, x0:x0 + cw]
            mc = mm[ys0 - y0:ys1 - y0]
            R[:] = R * (1 - mc) + cont[ys0 - y0:ys1 - y0] * mc

        # destaque gigante: em cima, bem grande, passando ATRAS dele (como antes)
        act = [g for g in giants if g["o0"] - 0.01 <= t < g["o1"] + 0.25]
        if act:
            layer = np.zeros((H, W, 4), np.float32)
            for g in act:
                fade = ease((g["o1"] + 0.25 - t) / 0.25)
                for it in g["items"]:
                    a = ease((t - it["o"]) / 0.12) * fade
                    if a <= 0.01:
                        continue
                    fp = it.get("font", FONT_COND)
                    spr = word_sprite(it["word"], it["size"], it["color"], fp)
                    base = baseline_of(it["word"], it["size"], it["color"], fp)
                    sc = 1.0 + 0.08 * (1 - ease((t - it["o"]) / 0.22))
                    cy_spr = ty + s * (it["by"] - base + spr.shape[0] / 2)
                    paste_rgba(layer, spr, TX * p + s * it["x"], cy_spr, a, sc * s)
            A = layer[..., 3:4]
            col = layer[..., :3]
            if p < 0.05:
                person = segm(img.clip(0, 255).astype(np.uint8))[..., None]
                A = A * (1 - person)
                col = col * (1 - person)
            img = img * (1 - A) + col * 255

        # legenda por frase (no peito dele, acompanha o cartao)
        cx, cy = TX * p + s * W / 2, ty + s * cap_y
        csc = s
        for ph in phrases:
            if not (ph["a"] - 0.01 <= t < ph["b"] + 0.15):
                continue
            fade = ease((ph["b"] + 0.15 - t) / 0.15)
            for w in ph["words"]:
                if t < w["start"] - 0.03:
                    continue
                e = ease((t - w["start"] + 0.03) / 0.12)
                wy = cy + csc * (w["dy_base"] - w["base"] + w["spr"].shape[0] / 2) + (1 - e) * 10
                paste(img, w["spr"], cx + csc * w["dx"], wy, e * fade, csc)


        enc.stdin.write(np.ascontiguousarray(img.clip(0, 255).astype(np.uint8)).tobytes())
        if fi % 300 == 0:
            print(f"  quadro {fi}/{nfr}", flush=True)

    rd.close()
    segm.seg.close()  # fecha o mediapipe antes do python sair (evita aviso feio no final)
    for r in readers.values():
        r.close()
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
    final = job / f"{name}_CLIP.mp4"
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
