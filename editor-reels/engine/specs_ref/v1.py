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
    "face": (540, 880), "cap_y": 1290, "music": "282.mp3",
    # tipografia (tempos = video bruto; cada palavra aparece quando e falada)
    "type": [
        {"type": "stack", "at": 3.28, "until": 6.25, "y": 150, "size": 150,
         "lines": ["QUANTOS GRAMAS DE", "PROTEÍNA TEM", "NUM BIFE?"]},
        {"type": "giant", "at": 6.35, "until": 7.35, "text": "100G", "y": 560, "size": 420},
        {"type": "spread", "at": 7.44, "until": 9.45, "y": [215, 370], "size": 140,
         "lines": ["SE VOCÊ RESPONDEU", "100 GRAMAS"]},
        {"type": "spread", "at": 14.40, "until": 16.45, "y": [230], "size": 130, "lines": ["A RESPOSTA CERTA"]},
        {"type": "giant", "at": 16.50, "until": 17.95, "text": "26G", "y": 560, "size": 470},
        {"type": "spread", "at": 18.10, "until": 21.40, "y": [215, 370], "size": 130,
         "lines": ["100G DE CARNE", "26G DE PROTEÍNA"]},
        {"type": "stack", "at": 22.30, "until": 25.10, "y": 160, "size": 140, "lines": ["ÁGUA", "GORDURA", "E O QUE DÁ LIGA"]},
        {"type": "spread", "at": 30.75, "until": 31.95, "y": [240], "size": 140, "lines": ["UM BIFE BONITO"]},
        {"type": "giant", "at": 34.25, "until": 35.70, "text": "RESOLVEU?", "y": 560, "size": 330},
        {"type": "stack", "at": 36.40, "until": 40.50, "y": 170, "size": 170, "lines": ["COMEU 26G", "PRECISAVA 100"]},
        {"type": "spread", "at": 41.35, "until": 42.40, "y": [230], "size": 120, "lines": ["NÃO ESTÁ COMENDO ERRADO"]},
        {"type": "stack", "at": 46.30, "until": 47.60, "y": 150, "size": 250, "lines": ["NÚMERO", "ERRADO"]},
        {"type": "spread", "at": 48.40, "until": 50.70, "y": [215, 370], "size": 130,
         "lines": ["SE VOCÊ ESTÁ", "USANDO A CANETA"]},
        {"type": "giant", "at": 50.75, "until": 52.10, "text": "2X", "y": 560, "size": 520},
        {"type": "spread", "at": 56.10, "until": 58.40, "y": [230], "size": 120, "lines": ["A PROTEÍNA FICA DE FORA"]},
        {"type": "stack", "at": 59.60, "until": 61.40, "y": 170, "size": 160, "lines": ["UMA CONTA", "PARA O SEU PESO"]},
        {"type": "giant", "at": 63.95, "until": 66.30, "text": "GRÁTIS", "y": 560, "size": 400},
        {"type": "cta", "at": 67.15, "until": 71.0, "y": 170,
         "lines": [{"text": "Comenta", "size": 110, "small": True}, {"text": "CANETA", "size": 330}]},
    ],
    "bw": [[12.00, 13.50], [33.80, 35.70], [45.30, 47.60]],
    "close": [[25.80, 28.20, 1.28], [41.30, 42.40, 1.30], [52.20, 54.70, 1.22]],
    "props": [
        {"t0": 5.55, "t1": 7.30, "init_t": 5.9, "box": [570, 1490, 280, 190], "zoom": 1.2},
        {"t0": 18.05, "t1": 21.60, "init_t": 19.0, "box": [510, 1530, 290, 170], "zoom": 1.22},
        {"t0": 29.00, "t1": 31.90, "init_t": 31.1, "box": [440, 1530, 280, 185], "zoom": 1.22},
        {"t0": 36.30, "t1": 38.30, "init_t": 36.9, "box": [320, 1490, 300, 170], "zoom": 1.2},
    ],
    "broll": [
        {"clip": "v1_quanta_proteina_bife_04_7247817", "at": 43.42, "dur": 1.9},  # "A conta que ela faz de cabeca"
        {"clip": "v1_quanta_proteina_bife_06_6054023", "at": 52.6, "dur": 1.9},  # "comendo menos no geral"
        {"clip": "v1_quanta_proteina_bife_07_7710747", "at": 59.34, "dur": 1.8},  # "Eu fiz uma conta simples"
    ],
}
