# v5 "Vou falar sobre a caneta" — video COMPLETO. Bruto corrigido: raw/v5_caneta_fix.mp4
# (o "nunca" do original virou "não", colado da fala dele em 2:37.95-2:38.20; 1.45-1.63 e silencio e fica fora do keep)
SPEC = {
    "name": "v5_caneta",
    "source": "v5_caneta_fix",
    "keep": [
        [0.50, 1.45],      # "Eu não"
        [1.63, 4.66],      # "falei da caneta aqui, em 10 anos," (sai "nenhuma vez")
        [5.60, 81.20],     # pausa + "Não dessa caneta ..." ate "... treinar força e dormir bem."
        # sai 81.46-92.30: "Só que pensa comigo ... falar de novo. Agora pensa comigo, só um instante." (tentativa errada)
        [92.30, 115.70],   # "Agora repara comigo ..." ate "... ter começado por aí."
        # sai 115.84-133.80: primeira versao de "se ela está tomando para sempre ... De novo." (ele regravou)
        [133.75, 176.20],  # "Agora, se ela for tomar pra sempre ..." ate o CTA (sai "Boa! Tá gravando?")
    ],
    "lead": [5.60],        # pausa de ~1 s depois de "em 10 anos" (pedido do Renato)
    "fixes": {"replace": {"14": "essa", "159": "25%", "162": "45%"}, "drop": [160, 163], "inject": []},
    "music": "282.mp3",
    "highpass": 70,
    "split_style": "fade",
    "face": (470, 960),
    "head_top": 670,
    "cap_y": 1320, "cap_size": 64,
    "giant_stroke": 0.035,  # contorno preto nas palavras gigantes (pedido do Renato)
    "keywords": ["caneta", "10", "anos", "sempre", "outra", "emagrece", "opinião", "real", "médico", "músculo",
                 "25%", "45%", "estudos", "proteína", "força", "dormir", "novo", "30", "grátis", "trabalho",
                 "guia", "gratuita", "Comenta"],
    "giants": [
        {"type": "giant", "at": 3.40, "until": 4.58, "text": "10 ANOS", "size": 380},
        {"type": "giant", "at": 12.00, "until": 12.90, "text": "EMAGRECE", "size": 330},
        {"type": "giant", "at": 24.48, "until": 25.95, "text": "OBESIDADE GRAVE", "size": 330},
        {"type": "giant", "at": 26.04, "until": 26.90, "text": "DIABETES", "size": 360},
        {"type": "giant", "at": 40.34, "until": 42.22, "text": "1ª OPÇÃO", "size": 380},  # "a primeira coisa que a pessoa tenta"
        {"type": "giant", "at": 56.76, "until": 57.90, "text": "MÚSCULO", "size": 360},
        {"type": "giant", "at": 60.72, "until": 63.60, "text": "25% A 45%", "size": 300},
        # 1:33 do video: "comendo bem, dormindo bem e treinando bem"
        {"type": "giant", "at": 110.06, "until": 110.82, "text": "COMENDO BEM", "size": 330},
        {"type": "giant", "at": 110.88, "until": 111.62, "text": "DORMINDO BEM", "size": 330},
        {"type": "giant", "at": 111.68, "until": 112.60, "text": "TREINANDO BEM", "size": 330},
        {"type": "giant", "at": 140.56, "until": 141.50, "text": "30 ANOS", "size": 380},
        {"type": "cta", "at": 172.96, "until": 176.20, "y": 170,
         "lines": [{"text": "Comenta", "size": 110, "small": True}, {"text": "CANETA", "size": 330}]},
    ],
    "close": [],
    # caneta comum que ele mostra em "Não dessa caneta, essa aqui a gente pode até falar sempre"
    "props": [
        {"t0": 6.60, "t1": 9.30, "init_t": 7.0, "box": [720, 890, 110, 290], "zoom": 1.2},
    ],
    # tela dividida com b-roll REAL (cada um aprovado pelo Renato antes de entrar)
    "panels": [
        {"at": 0.82, "until": 3.02, "file": "broll_new/caneta_kb.mp4", "src_start": 0.0, "bw": True},
        {"at": 30.90, "until": 33.98, "file": "broll_new/px_7579595.mp4", "src_start": 1.0},   # medica + paciente
        {"at": 75.70, "until": 78.95, "file": "broll_new/px_28315647.mp4", "src_start": 1.0},  # carne no prato
        {"at": 79.00, "until": 80.20, "file": "broll_new/px_6892536.mp4", "src_start": 2.0, "lift": 330},  # agachamento (ela fica embaixo no clipe)
        {"at": 80.20, "until": 81.10, "file": "broll_new/px_9035661.mp4", "src_start": 1.0},   # dormindo
    ],
}
