SPEC = {
    "name": "v4_proteina_barata_mercado",
    "source": "v4_proteina_barata_mercado",
    "keep": [[0.30, 37.25], [40.25, 80.9]],
    "fixes": {"replace": {"25": "custa", "69": "osso", "150": "emagrecedora", "195": "Comer", "203": "bonita?",
                          "210": "caneta"}, "drop": [71, 209]},
    "face": (540, 760), "cap_y": 1310, "cap_moves": [[21.2, 23.5, 1150], [27.8, 31.6, 1150]], "music": "666.mp3",
    "type": [
        {"type": "stack", "at": 0.30, "until": 3.40, "y": 120, "size": 140,
         "lines": ["QUAL A PROTEÍNA", "MAIS BARATA DO", "SUPERMERCADO?"]},
        {"type": "giant", "at": 4.25, "until": 5.60, "text": "OVO", "y": 420, "size": 400},
        {"type": "spread", "at": 7.20, "until": 8.40, "y": [230], "size": 130, "lines": ["E O FRANGO TAMBÉM"]},
        {"type": "spread", "at": 8.60, "until": 9.90, "y": [230], "size": 120, "lines": ["VAMOS FAZER AS CONTAS"]},
        {"type": "spread", "at": 10.15, "until": 13.90, "y": [190, 340], "size": 140, "lines": ["UM OVO", "50 A 60 CENTAVOS"]},
        {"type": "giant", "at": 15.45, "until": 16.70, "text": "6G", "y": 420, "size": 440},
        {"type": "stack", "at": 18.10, "until": 20.40, "y": 120, "size": 150, "lines": ["8 E 10 CENTAVOS", "POR GRAMA"]},
        {"type": "spread", "at": 21.30, "until": 22.60, "y": [230], "size": 130, "lines": ["COXA E SOBRECOXA"]},
        {"type": "giant", "at": 24.50, "until": 25.80, "text": "R$15", "y": 420, "size": 380},
        {"type": "spread", "at": 27.90, "until": 31.50, "y": [190, 340], "size": 140, "lines": ["100G COMPRADOS", "12G DE PROTEÍNA"]},
        {"type": "stack", "at": 32.30, "until": 34.00, "y": 120, "size": 160, "lines": ["12 CENTAVOS", "POR GRAMA"]},
        {"type": "spread", "at": 35.20, "until": 37.20, "y": [190, 340], "size": 150, "lines": ["A BARRINHA", "DE PROTEÍNA"]},
        {"type": "giant", "at": 41.90, "until": 42.95, "text": "R$9", "y": 420, "size": 400},
        {"type": "spread", "at": 43.00, "until": 44.30, "y": [230], "size": 140, "lines": ["15G DE PROTEÍNA"]},
        {"type": "stack", "at": 44.70, "until": 46.30, "y": 120, "size": 160, "lines": ["60 CENTAVOS", "POR GRAMA"]},
        {"type": "giant", "at": 47.00, "until": 49.20, "text": "5X", "y": 420, "size": 520},
        {"type": "giant", "at": 55.60, "until": 56.90, "text": "R$ 1.000", "y": 420, "size": 330},
        {"type": "stack", "at": 58.40, "until": 60.00, "y": 120, "size": 170, "lines": ["POR CAUSA", "DO PREÇO"]},
        {"type": "spread", "at": 60.00, "until": 60.90, "y": [230], "size": 130, "lines": ["NÃO POR ESCOLHA"]},
        {"type": "spread", "at": 67.50, "until": 69.30, "y": [190, 340], "size": 150, "lines": ["SABER MONTAR", "O SEU PRATO"]},
        {"type": "giant", "at": 70.80, "until": 71.60, "text": "BARATO", "y": 420, "size": 380},
        {"type": "spread", "at": 72.40, "until": 73.60, "y": [230], "size": 130, "lines": ["EMBALAGEM BONITA?"]},
        {"type": "giant", "at": 74.30, "until": 75.00, "text": "CARO", "y": 420, "size": 420},
        {"type": "cta", "at": 75.05, "until": 80.9, "y": 140,
         "lines": [{"text": "Comenta", "size": 100, "small": True}, {"text": "CANETA", "size": 300}]},
    ],
    "bw": [[46.50, 49.20], [74.00, 75.00]],
    "close": [[57.50, 60.50, 1.20], [61.40, 63.20, 1.22]],
    "props": [
        {"t0": 10.20, "t1": 14.10, "init_t": 14.3, "box": [80, 1100, 110, 110], "white": True, "zoom": 1.22},
        {"t0": 14.20, "t1": 16.60, "init_t": 15.3, "box": [265, 1005, 140, 150], "white": True, "zoom": 1.22},
        {"t0": 21.40, "t1": 23.20, "init_t": 22.5, "box": [370, 1380, 460, 220], "zoom": 1.15},
        {"t0": 28.00, "t1": 31.40, "init_t": 29.0, "box": [350, 1480, 470, 180], "zoom": 1.15},
        {"t0": 40.40, "t1": 42.90, "init_t": 43.0, "box": [640, 1020, 380, 180], "zoom": 1.2},
        {"t0": 42.95, "t1": 44.35, "init_t": 43.0, "box": [640, 1020, 380, 180], "zoom": 1.2},
    ],
    "broll": [
        # caneta emagrecedora sozinha na mesa, em janela acima da cabeca (Pexels foto 32532049, aproximacao lenta)
        {"file": "broll_new/caneta_kb.mp4", "mode": "pip", "src_start": 0.0, "at": 52.68, "dur": 2.5},  # "A caneta emagrecedora custa ai"
        {"clip": "v4_proteina_barata_mercado_01_6669085", "at": 4.16, "dur": 1.5},  # "O ovo consegue ser extremamente barato"
        {"clip": "v4_proteina_barata_mercado_02_5769417", "at": 7.24, "dur": 1.15},  # "e o frango tambem"
        # prato low-carb sendo montado (frango grelhado sobre salada) - Mixkit 26607
        {"file": "broll_new/mx_26607.mp4", "mode": "blurfit", "fg_zoom": 1.25, "src_start": 10.5, "at": 67.52, "dur": 1.8},  # "saber montar o seu prato"
        # marmitas prontas em bandeja plastica - Pexels 6894108
        {"file": "broll_new/px_6894108.mp4", "mode": "fill", "src_start": 1.0, "at": 71.74, "dur": 0.74},  # "Comprar comida de"
        # caixa bonita de hamburguer congelado - Pexels 4139332
        {"file": "broll_new/px_4139332.mp4", "mode": "fill", "src_start": 2.0, "at": 72.48, "dur": 1.2},  # "embalagem bonita?"
    ],
}
