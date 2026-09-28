# MODELO de spec para um video novo (copie para specs_clip/v5.py e preencha).
# Todos os tempos sao do VIDEO BRUTO (os da transcricao), nao do video final.
SPEC = {
    "name": "v5_nome_do_video",          # nome do arquivo de saida
    "source": "v5_nome_do_video",        # raw/<source>.mp4 e edit/transcripts/<source>.json
    # trechos que ficam (tira tentativas repetidas e CTAs repetidos do fim)
    "keep": [[0.50, 60.0]],
    # correcoes da transcricao: indice da palavra -> texto; "drop" some SO da legenda (a fala continua)
    "fixes": {"replace": {}, "drop": [], "inject": []},
    "music": "282.mp3",                  # assets/music (282, 479, 485, 666)
    "highpass": 70,                      # 100 se tiver barulho grave/ruido no comeco
    "split_style": "fade",               # tela dividida SEM bordas: b-roll em cima sumindo em degrade ate ele
    "face": (540, 880),                  # centro do rosto no quadro 1080x1920 (medir numa folha de quadros)
    "head_top": 650,                     # topo da cabeca (com o jump-cut 1,10x); palavras grandes ficam ACIMA disso
    "cap_y": 1195, "cap_size": 64,       # legenda no peito: abaixo do queixo e acima do prato
    # palavras-chave = peso forte laranja na legenda (o resto fica branco fino translucido)
    "keywords": ["proteína", "caneta"],
    # destaques GIGANTES com brilho, ACIMA da cabeca (y automatico). So gancho, numeros-chave e CTA.
    "giants": [
        {"type": "giant", "at": 1.00, "until": 1.60, "text": "PALAVRA", "size": 420},
        {"type": "cta", "at": 55.0, "until": 59.0, "y": 170,
         "lines": [{"text": "Comenta", "size": 110, "small": True}, {"text": "CANETA", "size": 330}]},
    ],
    # aproximacao em momentos de enfase: [inicio, fim, zoom]
    "close": [],
    # objetos que ele MOSTRA/APONTA: zoom rastreado (box = x, y, largura, altura do objeto no init_t)
    "props": [
        # {"t0": 5.55, "t1": 7.30, "init_t": 5.9, "box": [570, 1490, 280, 190], "zoom": 1.2},
    ],
    # tela dividida: card = cartao de dados animado ("comp" / "meta"); file = b-roll REAL (mostrar opcoes antes!)
    # nunca durante um "giant" (o motor fecha a tela dividida antes do destaque)
    "panels": [
        # {"at": 43.40, "until": 47.10, "file": "broll_new/px_7247817.mp4", "src_start": 1.0},
    ],
}
