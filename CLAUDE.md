# Praça Pública

Dados públicos brasileiros → parquet → cruzamentos → site que o cidadão comum entende e compartilha.

> ## ▶ Comece por [docs/ESTADO.md](docs/ESTADO.md)
> Onde o projeto parou, a fila de tarefas em ordem, as pendências que dependem do usuário,
> as decisões já tomadas e as armadilhas já encontradas. **Ler antes de qualquer trabalho.**

## Mapa dos documentos (ler antes de propor qualquer mudança)

| Arquivo | O que contém | Consultar quando... |
|---|---|---|
| **[docs/ESTADO.md](docs/ESTADO.md)** | **Estado atual + fila de trabalho + pendências + armadilhas** | **sempre, antes de tudo** |
| [docs/ESCOPO.md](docs/ESCOPO.md) | **Documento-mestre**: visão, princípios inegociáveis, decisões consolidadas, roadmap M0→M5 com critérios de pronto, riscos, MoSCoW, pendências do usuário | for começar qualquer tarefa — é o índice de tudo |
| [FONTES.md](FONTES.md) | Catálogo das fontes de dados (URLs verificadas, formatos, volumes, riscos por fonte, chaves de cruzamento) | for mexer em ingestão ou adicionar fonte |
| [docs/ARQUITETURA.md](docs/ARQUITETURA.md) | Storage (parquet+manifesto), R2/Actions/VPS, topologia de buckets, serving, schema dos marts, custos, backup | for decidir onde/como guardar ou servir dado |
| [docs/OPERACAO.md](docs/OPERACAO.md) | Workflows, gatilhos para Dagster, watcher, CI/CD, gates de qualidade (contratos YAML), observabilidade, SLAs | for criar pipeline, workflow ou check |
| [docs/PRODUTO.md](docs/PRODUTO.md) | Rotas, página de município, **régua única de comparação (§2 regra 3)**, design system, acessibilidade, stack Astro+Pages | for trabalhar no site |
| [docs/CRESCIMENTO.md](docs/CRESCIMENTO.md) | 12 insights com cuidados editoriais, share cards/OG, calendário, Lei 9.504, métricas | for criar insight, card ou texto público |
| [docs/SEGURANCA.md](docs/SEGURANCA.md) | LGPD (LIA/RIPD/n<5/anti-CPF), regras editoriais da Fase 2, segredos/buckets, checklist pré-lançamento | for publicar dado ou tocar em infra/segredos |
| [config/fontes.yaml](config/fontes.yaml) | **Fonte da verdade de URLs** — pipelines nunca hardcodam endereço | sempre que uma URL de fonte mudar |

## Regras que nenhuma mudança pode violar (detalhes em ESCOPO.md §1)

1. Todo número publicado tem fonte + data de referência + data de coleta.
2. Chave canônica: `codigo_municipio_ibge` VARCHAR(7). **Nunca INT** (zeros à esquerda).
3. **CPF jamais** — nem reconstituir (join QSA×TSE proibido), nem exibir mascarado. Agregados com n ≥ 5.
4. Dado ausente ≠ zero; dado suspeito não é promovido a staging (falhar ruidosamente).
5. Comparações usam mediana ("o típico das parecidas"), nunca "média" no texto público.
6. Raw é imutável: `raw/{fonte}/{AAAA-MM-DD}/`, nunca sobrescrever.
7. Erro publicado gera errata pública — nunca correção silenciosa.

## Código e comandos

```powershell
.venv\Scripts\Activate.ps1                          # venv Python 3.14
pip install -e ".[dev]"                             # deps via pyproject.toml
pytest -q                                           # suíte padrão (sem rede)
pytest -q -m live                                   # smoke tests contra APIs reais
ruff check .; ruff format .
python -m pipelines.siconfi.ingest_entes            # dimensão de entes (5.598)
python -m pipelines.siconfi.ingest_dca --exercicio 2024 --uf PE
```

- **TDD é obrigatório em todo desenvolvimento**: escrever o teste antes (vermelho), implementar
  (verde), refatorar. Nenhum módulo novo sem teste que falhou primeiro. Testes que tocam rede
  levam `@pytest.mark.live` (excluídos por padrão e no CI).
- Camadas: `raw/{fonte}/{AAAA-MM-DD}/` (originais imutáveis, uma pasta por coleta) →
  `staging/` (parquet zstd) → `marts/`. Nenhum módulo monta caminho na mão: tudo por
  `storage.uri()` / `storage.caminho_raw()`. Na cloud são **dois buckets**: `PRACA_RAW_ROOT`
  (`praca-raw`, só a raw) e `PRACA_DATA_ROOT` (`praca-dados`, o resto) — tokens R2 escopados
  por bucket; local, sem `PRACA_RAW_ROOT`, tudo cai na mesma pasta.
- `pipelines/common/`: `config.py` (fontes.yaml), `storage.py` (local ↔ R2 + raw datada),
  `http.py` (retry+throttle), `manifest.py` (idempotência + janela de captura),
  `parquet.py` (JSON→parquet; `pragmas_s3` ensina o duckdb a ler/gravar no R2).
- Ausência de dado é lacuna provisória: `manifest.registrar(..., completo=False)` faz a chave
  ser reconsultada após `JANELA_PADRAO_DIAS` (entrega atrasada precisa entrar depois).
- `pipelines/siconfi/`: `api.py` (paginação, buscador injetável), `transform.py` (funções puras),
  `ingest_*.py` (orquestração fina — main() não contém lógica).
- Encoding declarado por fonte no YAML (SICONFI utf-8; Receita/TSE/CVM latin-1) — nunca auto-detect.
- Throttle SICONFI: 1 req/s (bloqueiam acima disso).
- CI: `.github/workflows/ci.yml` (lint + formato + pytest; actions pinnadas por SHA — cobrado
  por `tests/test_workflows.py`, que também exige concurrency e alerta de falha nos agendados).
- Ingestão agendada: `.github/workflows/ingest-mensal.yml` (dia 5, 03:00 BRT) escreve direto
  nos buckets; DCA sai só por `workflow_dispatch` com exercício e UF.
- Watcher: `pipelines/watcher/sonda.py` + `watcher-fontes.yml` (diário, 06:00 BRT); estado em
  `catalog/watcher_state.json`. **Nunca acoplar ao ingest** — ele precisa rodar justamente
  quando um pipeline quebrou.
- **Ao adicionar fonte no `fontes.yaml`, declare `sonda:`** com um endpoint real (não o
  `api_base`, que costuma ser prefixo e dar 404), `status_ok` quando 401/403 for resposta
  saudável, e `detectar_mudanca: false` se a assinatura oscilar entre requests. Fonte sem
  `sonda:` não é vigiada — deixe comentado o porquê.
- Falhas de pipeline avisam o canal de operações: envolver o `main()` em
  `alertas.falhas_alertadas(contexto)`. Só falha alerta — sucesso de rotina viraria ruído.
- Repo: `marconetsf/praca-publica` (público). **Main protegida: PR obrigatório** (0 aprovações,
  CI verde, sem force-push) — não commitar direto na main, sempre branch + PR.
- Secrets do R2 e do Telegram já cadastrados; faltam `HEALTHCHECK_URL` e
  `HEALTHCHECK_WATCHER_URL` (os workflows já os consomem de forma condicional).

## Próximo trabalho

**→ [docs/ESTADO.md](docs/ESTADO.md)** tem o estado atual, a fila em ordem, as pendências do
usuário, as decisões já tomadas e as armadilhas já encontradas. É lá que se atualiza o
andamento — não aqui, para não haver duas versões da verdade.

Resumo de uma linha (27/07/2026): código do M0 completo e validado; falta o watcher acumular
3 dias agendados. Onda 2 do M0.5 em curso. Prazo duro do projeto: **30/11/2026**.
