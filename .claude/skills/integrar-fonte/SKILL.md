---
name: integrar-fonte
description: Integra uma base de dados nova ao projeto, do reconhecimento à publicação. Use quando alguém quiser adicionar uma fonte ao catálogo, avaliar se vale a pena coletar algo, ou decidir se um dado precisa ser espelhado. Também serve para reavaliar fonte já catalogada quando o volume ou o risco mudam.
---

# Integrar uma base de dados nova

O procedimento completo está em `docs/arquitetura/INTEGRAR-FONTE.md` — **leia antes**. Esta skill é
o roteiro de execução: o que rodar, em que ordem, e onde não avançar.

A regra que orienta tudo: **computar não exige cópia, publicar exige**. O que se guarda é o insumo
do número publicado, nunca "a fonte inteira".

## Etapa 1 — Reconhecer (nunca pule)

```bash
python -m pipelines.reconhecer --url <um alvo representativo> \
    --unidades <quantos alvos como esse> \
    --requisicoes <quantas chamadas para cobrir o país> \
    --throttle <segundos entre chamadas> \
    --risco <alto|medio|baixo> [--filtro]
```

`--risco alto` significa **a fonte já apagou série alguma vez** — histórico, não previsão. O INEP é
alto porque o Ideb de 2019 e 2021 já responde 404.

Se a fonte publica parquet, dá para inspecionar sem baixar:

```sql
INSTALL httpfs; LOAD httpfs;
SELECT count(*) FROM read_parquet('https://.../base.parquet');
```

A saída inclui o bloco `guarda:` pronto. **Não escreva esse bloco à mão** — o comando aplica os
limiares (6 h de runner, 10 GB de plano, 2/20 GB de guarda) e escreve o motivo com os números.

## Etapa 2 — Declarar no catálogo

Cole o bloco em `config/fontes.yaml`, junto de `sonda:` e `ficha:`. As três declarações são
obrigatórias e cada uma tem seu teste:

| Bloco | Para que serve | Teste que cobra |
|---|---|---|
| `sonda:` | o watcher vigiar a fonte | `tests/test_watcher.py` |
| `ficha:` | o cidadão ler em `/fontes` | `tests/test_fontes_publicas.py` |
| `guarda:` | decidir o que se guarda | `tests/test_guarda.py` |

Rode `pytest -q tests/test_guarda.py tests/test_fontes_publicas.py` antes de seguir.

## Etapa 3 — Pactuar o indicador (portão)

`recorte.pactuado_em: null` faz o pipeline **se recusar a colher**. Para destravar, o indicador
precisa existir: nome, direção (subir é melhor ou pior?), esfera responsável e ressalva escrita.
Consulte `docs/ciencia-politica/INDICADORES.md` — e o agente `ciencia-politica` se a relevância
estiver em dúvida.

Não colete "para ter". Bytes sem finalidade contam no plano e ninguém revisa.

## Etapa 4 — Adquirir

- `colheita`: pipeline em `pipelines/<fonte>/`, respeitando o throttle do YAML, registrando `url` e
  `sha256` no manifesto.
- `integral`: `python -m pipelines.espelho.espelhar --fonte <nome>` (a lista vem de `espelho:`).
- **INEP**: só de rede residencial. O bloqueio é por ASN de datacenter, não geográfico — VPS
  brasileiro não resolve. Rode da máquina local.

Depois de adquirir, confira o que entrou:

```bash
python -m pipelines.espelho.inventario --fonte <nome>
```

## Etapa 5 — Staging e publicação

Encoding declarado no YAML (nunca auto-detect), `codigo_municipio_ibge` VARCHAR(7), dado suspeito
não sobe. Indicador novo entra em `pipelines/marts/fato_indicador.py` com contrato completo, e o
gate de sanidade roda antes de virar página.

## Onde parar e perguntar

- A fonte exige **credencial nova** → é o usuário quem provisiona.
- A aquisição **não cabe no runner** e exigiria VPS → custo recorrente, decisão do usuário.
- O volume passa de **20 GB** → não entra enquanto o espelho B2 não existir.
- A fonte **bloqueia acesso automatizado** → não se contorna. Documente e siga.

## Armadilha frequente

Começar pela coleta porque a fonte "parece útil". O reconhecimento custa minutos e evita descobrir
depois de 4 h de download que o grão não serve — ou que o dado que interessava está em outra
publicação do mesmo órgão. Foi o que aconteceu com o abandono escolar: cinco anos de microdados do
Censo espelhados, e a taxa de abandono estava nas *Taxas de Rendimento*, que é outro arquivo.
