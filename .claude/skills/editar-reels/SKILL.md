---
name: editar-reels
description: Padrão para QUALQUER pedido de edição de vídeo neste projeto. Edita Reels/vídeos (do Guilherme / Senhor Tanquinho ou outros) no estilo aprovado — legenda de dois pesos, palavras grandes laranja acima da cabeça, tela dividida sem bordas com b-roll real, zoom nos objetos, áudio limpo e música. Use sempre que o usuário falar em "edição de vídeo", "editar vídeo", "edita esse vídeo", "reels", "corte", "legenda no vídeo", "b-roll", "refazer/corrigir vídeo", ou mandar um vídeo para editar, mesmo sem dizer /editar-reels.
---

# Editar Reels — Senhor Tanquinho

Tudo roda LOCAL em `editor-reels/`. Leia antes as regras do cliente em `CLAUDE.md` (raiz do repo). Elas são obrigatórias.

## 0. Preparar o computador (uma vez só)
- Precisa de FFmpeg (o hook de SessionStart instala) e de Python 3.10–3.12.
- Criar o ambiente, dentro de `editor-reels/`:
  - Windows: `py -3.11 -m venv .venv` → `.venv\Scripts\activate` → `pip install -r requirements.txt`
  - Mac/Linux: `python3 -m venv .venv` → `source .venv/bin/activate` → `pip install -r requirements.txt`
  - Linux: se o mediapipe reclamar de libEGL, rode `sudo apt install libegl1 libgles2 libgl1`.
- As fontes (Anton, Montserrat), o modelo de recorte da pessoa, as músicas e o card final já estão em `assets/` e `edit/endcard/`.

## 1. Trazer o vídeo
Copie o bruto para `editor-reels/raw/<nome>.mp4`. O vídeo deve ser vertical, 1080x1920 e 30 fps.
Use um nome curto, como `v5_tema_do_video`.

## 2. Transcrever (local, com tempo de cada palavra)
`python tools/transcribe.py raw/<nome>.mp4`

O script gera `edit/transcripts/<nome>.json` e imprime o texto com os tempos.
- Confira os nomes e números errados e corrija-os no spec, em `fixes.replace`, pelo índice da palavra.
- Marque as tentativas repetidas e os CTAs repetidos do fim. Eles ficam fora do `keep`.

## 3. Olhar o vídeo antes de montar
Gere uma folha de quadros e olhe:
`ffmpeg -i raw/<nome>.mp4 -vf "fps=1/4,scale=216:-2,tile=8x3" -frames:v 1 out/folha_<nome>.jpg`

Anote três coisas:
- `face`, o centro do rosto, e `head_top`, o topo da cabeça, no quadro 1080x1920.
- O queixo e o prato, para definir `cap_y`, que fica no peito.
- Quando ele MOSTRA ou APONTA objetos. Esses momentos viram `props` com zoom rastreado.

## 4. Escrever o spec
Copie `engine/specs_clip/_modelo.py` para `engine/specs_clip/<vN>.py` e preencha:
- `keep`: os trechos que ficam. Nunca corte no meio de uma frase.
- `keywords`: as palavras-chave, que saem em laranja forte na legenda.
- `giants`: de 4 a 7 no máximo, só no gancho, nos números e no CTA. O `y` é automático e fica acima da cabeça.
  Se ele se inclinar e a palavra encostar na cabeça, diminua o `size` e dê um `y` fixo menor, que é o centro da letra.
- `panels`: a tela dividida. Use de 4 a 6 por vídeo, com cartões de dados (`comp`, `meta`) ou b-roll real.
  Não coloque painel durante um giant.

## 5. B-roll (SEMPRE mostrar opções antes)
- Procure em Pexels ou Mixkit clipes REAIS do contexto da fala. Nunca use IA.
- Baixe pelo ID do Pexels com `cd broll_new && bash ../tools/pxget.sh <id>`. No Windows, use o Git Bash ou baixe pelo site.
- Monte uma folha com 1 quadro de cada opção e MOSTRE ao cliente. Só coloque as que ele aprovar.

## 6. Renderizar e conferir
Dentro de `engine/`:
1. Prévia rápida: `python engine_clip.py specs_clip/<vN>.py --preview --until=30`
2. Vídeo inteiro: `python engine_clip.py specs_clip/<vN>.py`
3. Fala: `python verify.py specs_clip/<vN>.py`. Precisa dar **0 problemas**.
4. Olhe uma folha de quadros do resultado e confira quatro pontos: texto fora do rosto, gigantes acima da cabeça, legenda entre o queixo e o prato, e b-roll com a pessoa inteira.

A saída fica em `out/<nome>_clip/<nome>_CLIP.mp4`, que é o master.

## 7. Entregar
Na pasta `editor-reels`, rode `python tools/deliver.py out/<nome>_clip/<nome>_CLIP.mp4 entregas/<nome>.mp4 28`.
O cliente sobe o arquivo para o Drive, na pasta `01_VIDEOS_PRONTOS`.

## Ajustes finos (onde mexer)
- Tamanho e posição da legenda: `cap_size` e `cap_y` no spec.
- Distância entre as palavras gigantes e a cabeça: `head_top` no spec. O motor usa 35 px de folga.
- Degradê da tela dividida: `FADE_H`, `FADE_0` e `FADE_TY` em `engine_clip.py`.
- Volume da música: `music_db` no spec. O padrão é -21.
- Ruído grave no começo: `"highpass": 100` e/ou comece o `keep` depois do barulho.
- Ele em preto e branco embaixo do b-roll: `"bw": True` no painel.
- B-roll com a pessoa na parte de baixo do clipe (some no degradê): `"lift": 330` no painel (sobe o clipe em px).
- Manter uma pausa que o motor cortaria: `"lead": [t]` no spec (o trecho começa exatamente em `t`, tempo bruto).
- Contorno preto nas palavras gigantes: `"giant_stroke": 0.035` no spec (vale nos dois motores).
- Estilo antigo (`engine_ref.py`, specs_ref): b-roll na tela dividida (regra do cliente) = `"mode": "top"` no b-roll.
  Clipes seguidos viram uma tela dividida só, e a legenda desce junto com ele.
- Ruídos que o noisereduce geral não pega (tempos brutos, vale nos dois motores):
  - `"hp_zones": [[t0, t1, 110]]`: pancada ou ronco grave no microfone só naquele trecho.
  - `"nr_zones": [[t0, t1]]`: ruído de fundo que só existe ali (ex. elástico esfregando). Usa o perfil do próprio trecho.
  - `"mute": [[t0, t1]]`: só barulho claramente FORA da fala. A voz do Guilherme bate em 0 dB, então um pico
    colado na palavra quase sempre é sílaba. Abafar cortou a fala no v2. Na dúvida, mande um trecho curto pro cliente ouvir.
- Trocar uma palavra dita (ex. "nunca" → "não"): cole o áudio da mesma palavra dita em outro ponto do vídeo num
  bruto corrigido (`raw/<nome>_fix.mp4`), transcreva de novo e deixe o trecho que sobrou fora do `keep`.
  Confira o resultado com o transcritor. Exemplo: `specs_clip/v5_full.py`.
