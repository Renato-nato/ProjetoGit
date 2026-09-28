SPEC = {
    "name": "v1_quanta_proteina_bife",
    "source": "v1_quanta_proteina_bife",
    "keep": [[3.28, 71.0]],
    "fixes": {
        "replace": {"86": "bem", "87": "feito,", "191": "caneta"},
        "drop": [0, 1, 2, 190],
        "inject": [{"text": "Quantos", "start": 3.30, "end": 3.62}, {"text": "gramas", "start": 3.62, "end": 3.90},
                   {"text": "de", "start": 3.90, "end": 4.14}],
    },
    "face": (540, 880), "music": "282.mp3", "split_style": "fade", "head_top": 650,
    "cap_y": 1195, "giant_y": 1190, "cap_size": 64,
    # palavras-chave = peso forte laranja na legenda
    "keywords": ["proteína", "100", "26", "bife", "carne", "gramas", "água", "gordura", "liga", "prato", "bonito",
                 "resolveu", "errado", "cabeça", "caneta", "menos", "fora", "conta", "peso", "sozinha", "certa",
                 "comeu", "precisava", "perceber", "guia"],
    # palavra gigante com brilho (tempos do video bruto)
    "giants": [  # destaque bem grande ACIMA da cabeca (y automatico pelo head_top)
        {"type": "giant", "at": 3.28, "until": 3.62, "text": "QUANTOS", "size": 420},
        {"type": "giant", "at": 3.62, "until": 4.12, "text": "GRAMAS", "size": 420},
        {"type": "giant", "at": 6.35, "until": 7.35, "text": "100G?", "size": 330, "y": 205},
        {"type": "giant", "at": 16.50, "until": 17.95, "text": "26G", "size": 470},
        {"type": "giant", "at": 50.72, "until": 51.95, "text": "2X", "size": 520},
        {"type": "giant", "at": 63.95, "until": 64.90, "text": "GRÁTIS", "size": 400},
        {"type": "cta", "at": 67.15, "until": 71.0, "y": 170,
         "lines": [{"text": "Comenta", "size": 110, "small": True}, {"text": "CANETA", "size": 330}]},
    ],
    "close": [[25.80, 28.20, 1.22], [41.30, 42.40, 1.24]],
    "props": [
        {"t0": 5.55, "t1": 7.30, "init_t": 5.9, "box": [570, 1490, 280, 190], "zoom": 1.2},
        {"t0": 18.05, "t1": 21.60, "init_t": 19.0, "box": [510, 1530, 290, 170], "zoom": 1.22},
        {"t0": 29.00, "t1": 31.90, "init_t": 31.1, "box": [440, 1530, 280, 185], "zoom": 1.22},
        {"t0": 36.30, "t1": 38.30, "init_t": 36.9, "box": [320, 1490, 300, 170], "zoom": 1.2},
    ],
    # tela dividida: painel em cima, Guilherme embaixo
    "panels": [
        {"at": 22.00, "until": 25.30, "card": "comp",
         "beats": {"start": 22.00, "resto": 22.12, "agua": 22.52, "gordura": 23.10, "liga": 24.28}},
        {"at": 36.28, "until": 40.70, "card": "meta", "beats": {"comeu": 36.78, "meta": 39.32}},
        {"at": 43.40, "until": 47.10, "file": "broll_new/px_7247817.mp4", "src_start": 1.0, "yc": 0.36},
        {"at": 48.40, "until": 49.95, "file": "broll_new/caneta_kb.mp4", "src_start": 0.0},
        {"at": 52.24, "until": 58.45, "file": "broll_new/px_6054023.mp4", "src_start": 2.0, "yc": 0.70},
        {"at": 59.30, "until": 62.60, "file": "broll_new/px_7710747.mp4", "src_start": 2.0, "yc": 0.72},
    ],
}
