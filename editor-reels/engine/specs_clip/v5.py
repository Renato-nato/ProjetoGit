# v5 "Vou falar sobre a caneta" — bruto corrigido: raw/v5_caneta_fix.mp4
# (o "nunca" do original virou "não", colado da fala dele em 2:37.95-2:38.20; 1.45-1.63 e silencio e fica fora do keep)
SPEC = {
    "name": "v5_caneta_inicio",
    "source": "v5_caneta_fix",
    # "Eu não" | "falei da caneta aqui, em 10 anos," | (sai "nenhuma vez") pausa + "Não dessa caneta ... que emagrece."
    "keep": [[0.50, 1.45], [1.63, 4.66], [5.60, 13.20]],
    "lead": [5.60],                      # pausa de ~1 s depois de "em 10 anos" (pedido do Renato)
    "fixes": {"replace": {"14": "essa"}, "drop": [], "inject": []},
    "music": "282.mp3",
    "highpass": 70,
    "split_style": "fade",
    "face": (470, 960),
    "head_top": 670,
    "cap_y": 1320, "cap_size": 64,
    "keywords": ["caneta", "10", "anos", "sempre", "outra", "emagrece"],
    "giants": [
        {"type": "giant", "at": 3.40, "until": 4.58, "text": "10 ANOS", "size": 380},
        {"type": "giant", "at": 12.00, "until": 12.90, "text": "EMAGRECE", "size": 330},
    ],
    "close": [],
    # caneta comum que ele mostra em "Não dessa caneta, essa aqui a gente pode até falar sempre"
    "props": [
        {"t0": 6.60, "t1": 9.30, "init_t": 7.0, "box": [720, 890, 110, 290], "zoom": 1.2},
    ],
    # b-roll da caneta emagrecedora em "Eu não falei da caneta aqui", ele embaixo em preto e branco
    "panels": [
        {"at": 0.82, "until": 3.02, "file": "broll_new/caneta_kb.mp4", "src_start": 0.0, "bw": True},
    ],
}
