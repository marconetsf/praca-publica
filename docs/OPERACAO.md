# Operação: Orquestração, CI/CD, Qualidade e Observabilidade

> Especificado em 26/07/2026, a partir do estado real do repositório (2 pipelines SICONFI,
> common/ com http+manifest, fontes.yaml, sem testes, sem CI).

## 1. Orquestração

**Decisão: GitHub Actions scheduled workflows até a Fase 2. Dagster só quando gatilhos objetivos dispararem.**

O DAG real é raso (`ingest_* → staging → build_marts → site`) e a idempotência já vive no manifesto. Estrutura:

| Workflow | Cron (UTC) | Conteúdo |
|---|---|---|
| `ingest-mensal.yml` | dia 5, 03:00 | SICONFI (RREO/MSC), CAGED, ANEEL — matrix por fonte |
| `ingest-anual.yml` | manual + trimestral | DCA todas as UFs (matrix), INEP, DataSUS |
| `build-marts.yml` | `workflow_run` pós-ingest + cron diário de segurança | recalcula marts do staging no R2 |
| `watcher-fontes.yml` | diário 06:00 | sonda de fontes (abaixo) |
| `deploy-site.yml` | `repository_dispatch` quando mart mudou | build + deploy Pages |

Regra: todo workflow agendado termina com **ping no healthchecks.io** (dead-man switch) e `if: failure()` → Telegram.

**Gatilhos objetivos para migrar a Dagster (migrar quando ≥ 2 forem verdade):**
1. Backfill particionado vira rotina (> ~1×/mês) — o manifesto cobre "pular o que já foi", não "reprocessar a partição X e seus dependentes". Gatilho mais provável; chega com a Fase 2 (CNPJ).
2. > 10–12 assets com dependências cruzadas entre fontes.
3. Job > 6 h ou que não cabe no runner.
4. Necessidade de lineage/freshness por asset além dos checks caseiros.

Preparação sem custo: manter cada pipeline como **função pura `ingest(particao) -> Path`** chamada pelo `__main__` — Dagster entra depois como camada fina de `@asset` sobre as mesmas funções, OSS, no VPS da Fase 2. Não usar Dagster+ (pago) nem antecipar a adoção.

### Watcher de fontes (`pipelines/watcher/sonda.py`, workflow próprio, nunca acoplado aos ingests)

Para cada entrada de `config/fontes.yaml`:
- **Disponibilidade**: HEAD (ou GET `Range: bytes=0-0` onde HEAD é bloqueado — INEP exige UA; ComexStat tem TLS quebrado) → ≠ 2xx/3xx por 2 dias = alerta.
- **Mudança de conteúdo**: ETag/Last-Modified/Content-Length vs `watcher_state.json`; para índices de diretório (Nextcloud Receita, FTP IBGE, CKAN): hash da listagem → arquivo novo = "dado disponível", arquivo sumido = alerta.
- **Fingerprint de schema**: 1 página das APIs baratas (SICONFI, PNCP, IBGE) → hash dos nomes de campos vs contrato → divergência = CRÍTICO.

**Alertas — decisão: Telegram + healthchecks.io** (e-mail só como fallback nativo do GitHub). Canal único com severidade no prefixo: `CRITICO` (schema mudou/pipeline falhou), `AVISO` (URL instável, dado novo), `INFO` (resumo diário). healthchecks.io free (20 checks) detecta o pior caso: o job que **nem rodou** (cron do Actions pula silenciosamente com frequência documentada).

## 2. CI/CD

**Decisão: monorepo** (`pipelines/` + `site/` + `contracts/` + `tests/`). 1 dev, contratos compartilhados (schema dos marts é a API do site), atomicidade entre mudança de mart e de página. CI com `paths:` filters.

- **`ci.yml`** (PR + main): `ruff check` + `ruff format --check` + `pytest` (< 3 min; sem rede — testes live atrás de `@pytest.mark.live`). Runner `ubuntu-latest` (alvo de produção é Linux; dev local Windows, `pathlib` cobre).
- **Pipelines agendados**: Fase 1 cabe folgada no runner gratuito (centenas de MB/execução); runner é descartável — baixa manifesto do R2, processa, sobe, ping.
- **Dump CNPJ não cabe** (8 GB zip + 30 GB > 14 GB de disco; download instável ameaça 6 h) → **VPS Hetzner ~€8/mês como self-hosted runner `heavy`**; só o job CNPJ usa `runs-on: [self-hosted, heavy]`. Mesmos logs/secrets. Custo cloud até a Fase 2: **R$ 0**; na Fase 2: ~R$ 50–60/mês.
- **Deploy do site**: marts vivem no R2, não no git → `build-marts` compara sha256 com o publicado; mudou → sobe `marts/latest/` + `serving/` e dispara o build. **Mecanismo**: Pages via git-integration (preview por PR nativo); o build do Astro lê `serving/` do R2 com token de leitura em variável de ambiente do build; dado novo sem mudança de código é disparado por deploy hook do Pages chamado pelo `build-marts`.

## 3. Qualidade de dados como teste

**Decisão de ferramenta: checks caseiros em DuckDB SQL (~200 linhas). Nem Frictionless, nem dbt** (custo de adoção desproporcional para ~15 tabelas majoritariamente de ingestão; reavaliar se marts passarem de ~30 modelos encadeados).

**Gate 1 — raw→staging: contrato de schema (falha dura).** `contracts/{fonte}/{tabela}.yaml`.
Regra de nomes: **staging preserva o nome e o tipo da fonte** (`cod_ibge` BIGINT, como o SICONFI
entrega); a normalização para a chave canônica (`codigo_municipio_ibge` VARCHAR(7), ARQUITETURA §1)
acontece **no gate staging→marts** — validações de formato sobre inteiros usam cast explícito:
```yaml
colunas:
  cod_ibge:     {tipo: BIGINT, nao_nulo: true, valida: "length(CAST(cod_ibge AS VARCHAR)) = 7"}
  an_exercicio: {tipo: BIGINT, nao_nulo: true}
  valor:        {tipo: DOUBLE}
linhas_min: 1000
chave_unica: [cod_ibge, an_exercicio, conta]
# coluna extra na fonte = AVISO; faltante ou tipo trocado = FALHA
```
Falhou → parquet não entra no staging, raw preservado, CRÍTICO no Telegram, exit ≠ 0.

**Gate 2 — staging→marts: sanidade estatística.**
- Variação de linhas vs execução anterior fora de ±20% (configurável por tabela) = FALHA.
- Cobertura de municípios < limiar da fonte (DCA ≥ 85% — lacuna conhecida ~25%) = AVISO; queda > 10 p.p. = FALHA.
- Domínio: financeiro negativo onde não cabe; soma por função ≈ total (tolerância 1%); população ∈ [700, 13 mi].
- Baseline persistido em `marts/_quality_baseline.json` no R2.

**Testes de código (pytest, camada separada):** fixtures parquet minúsculas commitadas (10 municípios, < 100 KB); transformações testadas entrada→saída exata incluindo bordas (município sem declaração, IBGE de 6 dígitos sujo); manifest (idempotência), checks (contrato violado levanta erro), parsing com JSONs gravados. **Pré-requisito: extrair transformações dos `main()` para funções puras** (hoje `ingest_dca.py` mistura download/transformação/I/O).

## 4. Observabilidade mínima viável (tudo gratuito)

| Saber que... | Como | Ferramenta |
|---|---|---|
| pipeline falhou | `if: failure()` → Telegram | bot Telegram |
| pipeline **nem rodou** | ausência de ping | healthchecks.io |
| fonte mudou | watcher diário | job próprio |
| site caiu | HTTP 5 min na home + 1 página municipal (valida dado, não só CDN) | UptimeRobot free |
| dado ficou velho | `_meta_freshness.parquet` + SLA por fonte | DuckDB no watcher |

**SLAs de staleness** (`contracts/slas.yaml`): SICONFI RREO 75 dias; DCA 400; CAGED 60; IBGE população 400; INEP 430; DataSUS consolidado 730; ANEEL 60. Estouro = AVISO diário até resolver. **O mesmo arquivo alimenta o site** ("dados de MM/AAAA, extraídos em DD/MM") — observabilidade vira transparência editorial de graça.

Fora do escopo (overkill): Grafana/Prometheus, Sentry, OpenTelemetry, data catalogs.

## 5. Ambientes e fluxo de trabalho

- **Dev/prod como convenção, não infra**: local escreve em `data/` local; **só a main (via Actions) escreve no R2 de produção**. Prefixo `r2://praca/dev/` para testes manuais, apagável. Preview de site por PR já vem do Pages.
- **Branch protection na main** (mesmo com 1 dev — protege do próprio descuido e de agente de IA commitando direto): PR obrigatório, CI verde, auto-merge liberado. Exceção documentada: hotfix de URL em `fontes.yaml` tem workflow manual de bypass — fonte fora do ar não espera CI de site.
- **Conventional Commits** com escopo: `feat(siconfi):`, `fix(fontes):`, `data(contracts):`.
- **Versionamento**: código em tags `vX.Y.Z`, carimbado nos marts (`gerado_por: vX.Y.Z + sha`); dados em `marts/v=AAAA-MM-DD/` (imutável) + `latest/`; reter 6 snapshots + 1/semestre. Raw imutável é o backup real. **Não usar** DVC/lakeFS/git-lfs — manifesto + prefixos datados resolvem sem mais uma ferramenta.
