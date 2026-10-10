# KubeJS do GTIA

**Fora da primeira fatia.** O mod KubeJS não está em `manifest/first-slice.lock.json`, então `tools/pack.py instance` não
copia esta pasta. Ela guarda material que só vale com KubeJS instalado:

- `data/gtia/gtceu/fluid_veins/mars_radon.json`: depósito de Radon marciano do perfil de fluidos EV. Usa a dimensão
  `ad_astra:mars`, então também precisa do Ad Astra. Não afeta Start → Steam → LV.

Quando o KubeJS entrar no conjunto de mods (acrescente `kubejs` ao `manifest/first-slice.seeds` e rode
`python3 tools/pack.py lock`), a ferramenta passa a copiar esta pasta para a instância. Scripts de receita só devem entrar aqui
depois de verificados em jogo; a progressão atual é controlada pelos nós de pesquisa do GTIACore e pelo motor do GTNA.
