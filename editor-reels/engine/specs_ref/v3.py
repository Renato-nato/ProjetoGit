SPEC = {
    "name": "v3_musculo_apos_40",
    "source": "v3_musculo_apos_40",
    "keep": [[0.55, 38.3], [40.0, 51.05], [73.5, 97.9]],
    "fixes": {"replace": {"29": "8%", "219": "caneta", "227": "quanta", "243": "perdê-la"}, "drop": [30, 218, 244]},
    "face": (540, 900), "cap_y": 1200, "music": "479.mp3",
    "type": [
        {"type": "stack", "at": 0.60, "until": 4.80, "y": 140, "size": 150,
         "lines": ["QUANTO MÚSCULO", "VOCÊ PERDE", "DEPOIS DOS 40?"]},
        {"type": "spread", "at": 5.30, "until": 7.00, "y": [240], "size": 150, "lines": ["A CONTA ASSUSTA"]},
        {"type": "giant", "at": 10.55, "until": 12.40, "text": "3 A 8%", "y": 560, "size": 380},
        {"type": "spread", "at": 12.45, "until": 13.90, "y": [215, 370], "size": 140, "lines": ["DE MASSA MAGRA", "POR DÉCADA"]},
        {"type": "spread", "at": 14.20, "until": 16.60, "y": [215, 370], "size": 150, "lines": ["NA MENOPAUSA", "ACELERA"]},
        {"type": "spread", "at": 17.30, "until": 18.80, "y": [250], "size": 150, "lines": ["NINGUÉM SENTE"]},
        {"type": "stack", "at": 19.60, "until": 22.00, "y": 150, "size": 170, "lines": ["NÃO DÓI", "NÃO APARECE", "NA BALANÇA"]},
        {"type": "spread", "at": 22.30, "until": 25.70, "y": [215, 370], "size": 140, "lines": ["O MÚSCULO SAI", "ENTRA A GORDURA"]},
        {"type": "stack", "at": 30.15, "until": 32.40, "y": 110, "size": 140, "lines": ["A TAMPA DO", "VIDRO QUE", "NÃO ABRE"]},
        {"type": "spread", "at": 32.70, "until": 34.20, "y": [240], "size": 150, "lines": ["A ESCADA CANSA"]},
        {"type": "spread", "at": 34.60, "until": 38.20, "y": [215, 370], "size": 150, "lines": ["A ROUPA FICA", "DIFERENTE"]},
        {"type": "spread", "at": 40.60, "until": 41.90, "y": [215, 370], "size": 140, "lines": ["JUNTA ISSO COM", "A CANETA"]},
        {"type": "spread", "at": 43.30, "until": 44.70, "y": [250], "size": 200, "lines": ["DEVAGAR"]},
        {"type": "giant", "at": 45.70, "until": 46.75, "text": "RÁPIDO", "y": 560, "size": 400},
        {"type": "stack", "at": 47.10, "until": 50.80, "y": 150, "size": 170, "lines": ["GORDURA", "E MÚSCULO", "AO MESMO TEMPO"]},
        {"type": "spread", "at": 74.40, "until": 76.10, "y": [250], "size": 170, "lines": ["BOA NOTÍCIA"]},
        {"type": "spread", "at": 80.95, "until": 82.80, "y": [250], "size": 200, "lines": ["SÃO DOIS"]},
        {"type": "stack", "at": 82.85, "until": 85.00, "y": 150, "size": 180, "lines": ["TREINAMENTO", "E COMIDA"]},
        {"type": "spread", "at": 86.70, "until": 88.40, "y": [240], "size": 130, "lines": ["A PARTE MAIS FÁCIL"]},
        {"type": "cta", "at": 88.85, "until": 97.9, "y": 170,
         "lines": [{"text": "Comenta", "size": 110, "small": True}, {"text": "CANETA", "size": 330}]},
    ],
    "bw": [[5.30, 7.00], [44.80, 46.75]],
    "close": [[25.70, 27.60, 1.25], [28.30, 29.50, 1.30], [73.60, 74.40, 1.20]],
    "props": [
        {"t0": 0.60, "t1": 2.25, "static": True, "box": [40, 730, 420, 420], "zoom": 1.12},
        {"t0": 30.30, "t1": 33.70, "init_t": 30.5, "box": [450, 1320, 450, 350], "zoom": 1.2},
    ],
    "broll": [
        {"clip": "v3_musculo_apos_40_01_7802051", "at": 20.8, "dur": 1.35},  # "nao aparece na balanca"
        {"clip": "v3_musculo_apos_40_05_8836867", "at": 82.88, "dur": 1.35},  # "O treinamento adequado"
        {"clip": "v3_musculo_apos_40_06_9484988", "at": 84.26, "dur": 1.5},  # "e a comida"
    ],
}
