# Praça Pública

Dados públicos brasileiros → parquet → cruzamentos → site que o cidadão comum entende e compartilha.
Fase atual: especificação concluída (26/07/2026); execução começa no marco M0 do roadmap.

## Mapa dos documentos (ler antes de propor qualquer mudança)

| Arquivo | O que contém | Consultar quando... |
|---|---|---|
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
- Falhas de pipeline avisam o canal de operações: envolver o `main()` em
  `alertas.falhas_alertadas(contexto)`. Só falha alerta — sucesso de rotina viraria ruído.
- Estado: sem remoto GitHub ainda (branch protection pendente disso).

## Próximo trabalho

Roadmap ESCOPO.md §3: **M0.4 e M0.5 concluídos e validados contra R2 e Telegram reais**.
Pendências que dependem do usuário: espelho **Backblaze B2** com Object Lock (é ele que
garante a imutabilidade da raw — o R2 não tem versionamento) e conta **healthchecks.io**.
Próximo: M0.6 (workflow agendado no Actions — precisa dos secrets do R2 no repositório) →
M0.7 (watcher). Prazo externo mais urgente:
**M0.5 onda 1 do espelhamento (INEP e SNIS) até 30/09/2026**.
