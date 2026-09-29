SPEC = {
    "name": "v2_peso_volta_elastico",
    "source": "v2_peso_volta_elastico",
    "keep": [[1.57, 63.75], [68.9, 86.9]], "highpass": 100,
    "fixes": {"replace": {"82": "o", "122": "14%", "129": "82,5%", "137": "25%", "214": "caneta"},
              "drop": [123, 130, 131, 138, 213]},
    "face": (540, 910), "cap_y": 1200, "music": "485.mp3",
    "giant_stroke": 0.035,  # contorno preto nas palavras grandes (pedido do Renato, 29/09)
    # ruido (29/09): pancadas graves no microfone no comeco (ele mexe no elastico)
    # (NAO abafar 28.8-29.2: o pico ali e o "-de" de "quantidade" falado forte, nao estalo; abafar cortou a fala)
    "hp_zones": [[1.5, 9.6, 110]],
    # ruido de fundo ~11 dB acima do resto do video so no comeco (elastico esfregando perto do microfone)
    "nr_zones": [[0.8, 10.2]],
    "type": [
        {"type": "stack", "at": 1.0, "until": 5.40, "y": 140, "size": 150,
         "lines": ["POR QUE O PESO", "VOLTA QUANDO", "PARA A CANETA?"]},
        {"type": "spread", "at": 7.20, "until": 8.60, "y": [215, 370], "size": 140, "lines": ["FALTOU FORÇA", "DE VONTADE"]},
        {"type": "giant", "at": 9.80, "until": 11.80, "text": "ERRADA", "y": 560, "size": 400},
        {"type": "spread", "at": 12.80, "until": 15.60, "y": [215, 370], "size": 140,
         "lines": ["A CANETA TE EMPRESTA", "A SACIEDADE"]},
        {"type": "spread", "at": 21.45, "until": 23.00, "y": [240], "size": 130, "lines": ["A FOME NÃO APARECE"]},
        {"type": "stack", "at": 24.85, "until": 26.80, "y": 150, "size": 170, "lines": ["O CARDÁPIO", "CONTINUOU", "O MESMO"]},
        {"type": "spread", "at": 34.30, "until": 35.60, "y": [240], "size": 150, "lines": ["A FOME VOLTA"]},
        {"type": "stack", "at": 37.35, "until": 40.60, "y": 150, "size": 160,
         "lines": ["O MESMO CARDÁPIO", "QUE FEZ VOCÊ", "ENGORDAR"]},
        {"type": "giant", "at": 47.15, "until": 50.20, "text": "14%", "y": 560, "size": 480},
        {"type": "giant", "at": 50.35, "until": 52.60, "text": "82,5%", "y": 560, "size": 420},
        {"type": "spread", "at": 52.70, "until": 56.60, "y": [215, 370], "size": 140, "lines": ["REGANHAM", "25% OU MAIS"]},
        {"type": "spread", "at": 56.85, "until": 58.40, "y": [260], "size": 160, "lines": ["NINGUÉM RECAIU"]},
        {"type": "spread", "at": 59.20, "until": 61.20, "y": [240], "size": 140, "lines": ["A CONTA FECHOU"]},
        {"type": "stack", "at": 72.80, "until": 74.60, "y": 150, "size": 190, "lines": ["O TEMPO MAIS", "VALIOSO"]},
        {"type": "spread", "at": 74.65, "until": 76.20, "y": [240], "size": 130, "lines": ["CONSERTAR O SEU PRATO"]},
        {"type": "stack", "at": 78.30, "until": 81.50, "y": 150, "size": 160, "lines": ["NOVO HÁBITO", "NOVA ROTINA", "SEM PASSAR FOME"]},
        {"type": "cta", "at": 81.80, "until": 86.9, "y": 170,
         "lines": [{"text": "Comenta", "size": 110, "small": True}, {"text": "CANETA", "size": 330}]},
    ],
    # (29/09: saiu o P&B de 32.50-35.30 "a fome volta" -- piscava P&B/cor/P&B com o b-roll da geladeira)
    "bw": [[9.70, 11.80]],
    "close": [[27.00, 31.70, 1.25], [56.80, 58.20, 1.30], [69.00, 71.20, 1.22]],
    "props": [{"t0": 1.45, "t1": 3.25, "static": True, "box": [230, 1290, 740, 130], "zoom": 1.18}],
    # b-roll na tela dividida (regra do projeto): em cima, sumindo em degrade ate ele, que desce (29/09)
    "broll": [
        # "a fome volta / ao normal": geladeira aberta no escuro e o bolo saindo (Pexels 7331512)
        {"file": "broll_new/px_7331512.mp4", "mode": "top", "src_start": 2.3, "at": 34.40, "dur": 0.95},
        {"file": "broll_new/px_7331512.mp4", "mode": "top", "src_start": 9.6, "at": 35.35, "dur": 1.0},
        # (29/09: saiu o b-roll da balanca em "recupera", 46.06 -- Renato quer so as palavras ali)
    ],
}
