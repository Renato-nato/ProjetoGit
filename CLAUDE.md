# ProjetoGit — memória do projeto

## Edição de vídeos = SEMPRE este estilo
Quando o usuário falar em **edição de vídeo** de qualquer forma ("edita esse vídeo", "faz a edição", "editar reels",
"corta esse vídeo", "coloca legenda", "b-roll", "refaz o vídeo"...), **use automaticamente a skill `editar-reels`**
e siga o estilo e as regras abaixo, sem perguntar qual estilo usar. Ninguém precisa digitar `/editar-reels`.

## Edição de Reels "Senhor Tanquinho" (apresentador: Guilherme)

Tudo roda **local**, na pasta `editor-reels/`. O passo a passo completo está na skill
`.claude/skills/editar-reels/SKILL.md` (use `/editar-reels`). Os vídeos brutos ficam em `editor-reels/raw/`
e as saídas em `editor-reels/out/`. Essas pastas não vão para o git.

### Regras do cliente (valem para TODO vídeo)
- **Nunca cortar fala.** Depois de cada render, rode `python verify.py <spec>`. O resultado precisa dar 0 problemas.
- **Nenhum texto cobre o rosto do Guilherme.**
- **Palavras grandes de destaque ficam ACIMA DA CABEÇA**, bem grandes, na fonte Anton, laranja e com brilho.
  Use-as só no gancho, nos números-chave e no CTA final ("Comenta CANETA").
- **Legenda** fica abaixo do queixo e acima do prato, no peito. Tem dois pesos: palavra-chave em Montserrat
  ExtraBold laranja (254,122,0) e o resto em branco fino translúcido. Letras juntas, em minúsculas, e cada
  palavra aparece quando é falada.
- **Cor de destaque:** laranja (254,122,0), a mesma do card final.
- **Nada infantil:** sem emoji, sem "pop" e sem tremida. As transições são suaves.
- **B-roll** precisa ser REAL (Pexels ou Mixkit), do contexto da fala, e usado pouco, só em destaque.
  Nunca imagem de IA. **Sempre mostrar as opções de b-roll ao cliente ANTES de colocar.**
- **B-roll mostra a pessoa inteira.** Nunca cortar a cabeça: o motor mostra o clipe inteiro sobre um fundo
  desfocado dele mesmo.
- **Tela dividida sem bordas:** o b-roll fica em cima, na largura toda, e some em degradê até ele, embaixo.
- **Destaques de objeto:** quando ele mostra ou aponta um objeto (prato, bife, caneta), dá zoom rastreado no objeto.
- **Áudio sem ruído de fundo:** usa noisereduce com o perfil do próprio vídeo e loudnorm linear em -14 LUFS.
  Música por baixo, com ducking.
- **Sem "travadas":** o motor junta buracos menores que 0,15 s.
- **Um vídeo por vez.** Mostrar ao cliente, corrigir e só então passar para o próximo.
- **Entrega:** arquivo de até 28 MB (`tools/deliver.py`). O Drive fica na pasta `01_VIDEOS_PRONTOS`.

### Estilo de referência
- @iassminmoraes (https://www.instagram.com/p/Dcd5ciPRkhZ/): legenda de dois pesos, tela dividida
  e cartões de dados. É o estilo atual (`engine_clip.py`).
- @giubeckers (https://www.instagram.com/p/DdCLQG2x9nO/): tipografia grande atrás da pessoa
  (`engine_ref.py`). Foi usado no v2, v3 e v4 do lote 3.
