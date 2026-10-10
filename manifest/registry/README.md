# Registro de itens e elementos

Cópia de 2026-10-04 do que o runtime de desenvolvimento do GTIACore registra: `items.txt` (todos os ids de item) e
`elements.tsv` (os elementos do GTCEu com o item de lingote, pó, gema e balde de cada um). É gerado pelo GameTest
`RegistryDumpGameTests` do core (`runGameTestServer`, saída em `core/build/reports/registry/`).

Serve para `tools/questgen.py` conferir ids de item e montar o capítulo da Tabela Periódica a partir de fatos. **Cobre só os mods do
runtime do core** (GTCEu, GTNA, GTIACore, AE2 e o que eles trazem): itens de outros mods (Sophisticated, Construction Wand etc.) não
estão aqui e não são conferidos. Depois de mudar versões de GTCEu, GTNA ou GTIACore, gere de novo e copie para esta pasta.
