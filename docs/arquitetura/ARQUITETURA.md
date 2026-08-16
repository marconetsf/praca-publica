# Arquitetura de Dados e Cloud

> Decisões fechadas em 26/07/2026. Preços e limites verificados nessa data.

## 1. Formato de armazenamento: parquet puro + manifesto

**Decisão: parquet (zstd) com hive-partitioning + manifesto JSON. Sem DuckLake, sem Iceberg.**

| Opção | Veredito neste porte (≤300 GB, escritor único, DuckDB) |
|---|---|
| Parquet + manifesto | **Escolhido.** Zero dependência nova; arquivos diretamente baixáveis pelo público (transparência é objetivo); legível por DuckDB-WASM, httpfs, pandas, R |
| DuckLake | Production-ready desde 04/2026, mas exige catálogo vivo e renomeia data files (perde navegabilidade pública). Ponto de migração futuro se surgirem escritores concorrentes |
| Iceberg | Superdimensionado — valor está em multi-engine + Spark, que não existem aqui |

### Convenções (fixar agora, mudar depois custa caro)

- **Partições hive-style** só onde há poda real: `staging/{fonte}/{tabela}/ano=YYYY/uf=XX/`. Tabelas pequenas = arquivo único. Regra: não particionar se gerar arquivos < 50 MB; alvo 100–500 MB por arquivo.
- **Nomes**: `snake_case` em português sem acentos; prefixos de camada `stg_`, `mart_`, `dim_`, `fato_`.
- **Chave canônica**: `codigo_municipio_ibge` — **VARCHAR(7), nunca INT** (preserva zeros à esquerda), nome idêntico em todas as tabelas.
- **Snapshots CNPJ**: partição `snapshot=YYYY-MM` em staging; mart de "estado atual" derivado do último snapshot + `fato_cnpj_mudancas` gerada por diff entre snapshots (histórico sem duplicar 30 GB/mês).
- **Catálogo**: evoluir `data/manifest.json` para:
  - `contracts/{fonte}/{tabela}.yaml` — schema contract validado na promoção raw→staging (falha ruidosa);
  - `catalog/manifest.json` — por artefato: URL, sha256, bytes, data de extração, run_id, contagem de linhas. **Vai junto para o bucket** (metadado público).

## 2. Cloud: Cloudflare R2 + GitHub Actions (+ VPS na Fase 2)

### Object storage: **Cloudflare R2** — decisão clara

| | R2 | S3 Standard | GCS |
|---|---|---|---|
| Storage/GB-mês | **$0,015** (IA: $0,01) | $0,023 | $0,020 |
| **Egress internet** | **$0** | ~$0,09/GB | $0,12/GB |
| Free tier | 10 GB + 1M writes + 10M reads/mês | 100 GB egress/mês | 1 GB egress |

Para um projeto que **serve dados públicos**, egress é o custo dominante: 1 TB/mês de saída ≈ $90 no S3, **$0 no R2**. R2 fala protocolo S3 (DuckDB httpfs e fsspec funcionam com `endpoint_url`) e integra com o CDN da Cloudflare. Limitação aceita: sem tier de arquivamento profundo (mitigada no §6 com B2).

### Compute dos pipelines

- **GitHub Actions** (repo público): minutos ilimitados grátis, runner 4 vCPU/16 GB RAM/~14 GB disco livre, 6 h/job. **Cobre toda a Fase 1.** O workflow vira documentação executável.

### Topologia de buckets (referência única)

| Bucket | Prefixos | Acesso de leitura | Quem escreve |
|---|---|---|---|
| `praca-raw` (R2, classe IA) | `raw/{fonte}/{AAAA-MM-DD}/` | privado | job de ingestão (token R2 do bucket) |
| `praca-dados` (R2) | `staging/`, `marts/v=.../`, `marts/latest/`, `serving/` | `marts/latest/` e `serving/` públicos via CDN; resto privado | jobs de transformação/publicação |
| `praca-espelho` (Backblaze B2, **versioning/Object Lock ligado**) | espelho de `raw/` | privado | `rclone sync` mensal |
| prefixo `dev/` em `praca-dados` | testes manuais | privado | qualquer dev; apagável |
- **Dump CNPJ (Fase 2) não cabe** no runner gratuito (8 GB zip + 30 GB extraído > 14 GB; download instável ameaça as 6 h). Solução: **VPS Hetzner (~€8/mês) como self-hosted runner** com label `heavy` — mesmos workflows, logs e secrets; só o job CNPJ declara `runs-on: [self-hosted, heavy]`. O mesmo VPS recebe o Dagster se/quando os gatilhos dispararem (ver OPERACAO.md §1).
- Segredos em GitHub Secrets; **tokens de API do R2 escopados por bucket** (a Cloudflare não suporta OIDC federado do GitHub para R2 — ver SEGURANCA.md §3).

### Código cloud-ready desde já (mudanças no repo atual)

1. Env var única `PRACA_DATA_ROOT` (`data/` local, `s3://praca` na cloud); helper `pipelines/common/paths.py` resolve camada/fonte/tabela/partição — nenhum pipeline monta caminho na mão.
2. I/O via fsspec (`s3fs` com endpoint R2) para raw; DuckDB httpfs + `CREATE SECRET (TYPE s3, ENDPOINT ...)` para parquet — o SQL não muda.
3. Manifesto no bucket com escrita atômica (`.tmp` + rename).
4. Idempotência por partição: sobrescrever a partição inteira (`OVERWRITE_OR_IGNORE`), nunca append.

**Estágios**: E0 (hoje) local com código abstraído → E1 espelhar raw+staging+marts no R2 → E2 pipelines no Actions → E3 VPS para CNPJ.

## 3. Serving do site: JSONs estáticos atrás de CDN — sem API com servidor

- **`serving/municipio/{codigo_ibge}.json`** — 1 JSON por município com todos os indicadores (~5.570 arquivos de 20–150 KB); um fetch resolve a página. Complementos: `serving/indicador/{id}/ranking.json`, `serving/uf/{uf}.json`, `serving/busca.json` (índice nome→código, ~300 KB gzip).
- Gerados por job DuckDB no fim do pipeline de marts; site estático no Cloudflare Pages consome o bucket via CDN (`cache-control: max-age=86400` + purge no deploy).
- **Quem consome `serving/`**: (a) o **build do Astro** — roda no Pages via git-integration (preview por PR nativo) com token de leitura R2 em variável de ambiente do build, baixa os JSONs e embute os dados nas páginas estáticas (por isso "0 JS para ler"); (b) as **ilhas interativas** (comparador, busca) e os **embeds**, que fazem fetch dos mesmos JSONs via CDN em runtime.
- **Pico viral (100k visitas/dia)**: ~500k req/dia com cache hit >95% → R2 vê <1M ops/mês → **dentro do free tier, custo ~R$ 0**. É o cenário que mataria uma API com servidor.
- **DuckDB-WASM** lendo parquet do R2 (range requests, egress zero): só para a página "explore os dados" (usuários avançados) — ~35 MB de runtime é hostil ao mobile 3G, que é a audiência-alvo. Cortável.
- **Fronteira formal**: o site só conhece `serving/`; `marts/` é contrato interno; raw/staging expostos apenas como bulk download documentado em `/dados`.

## 4. Modelagem dos marts (Fase 1)

**Fato longo (município × ano × indicador) como canônico** — indicador novo = inserir linhas, não `ALTER TABLE`. O formato wide é artefato de serving gerado por pivot.

```sql
-- dim_municipio (~5.570 linhas; inclui de-para TSE)
codigo_municipio_ibge VARCHAR(7) PK, nome, uf, codigo_uf, regiao,
codigo_municipio_tse, populacao_referencia BIGINT, ano_populacao,
latitude, longitude, eh_capital BOOLEAN,
slug VARCHAR,          -- minúsculas, sem acento, hífens; unicidade por UF garantida por asserção
faixa_porte VARCHAR    -- 7 faixas IBGE (ver PRODUTO.md §2 regra 3), fixada pelo ano de referência da população

-- dim_indicador (metodologia versionada)
indicador_id VARCHAR PK,          -- 'siconfi_despesa_saude_pc'
nome_exibicao, descricao_publica, -- linguagem para leigos
fonte, tabela_origem, unidade, formato_exibicao,
versao_metodologia INT,           -- incrementa quando a fórmula muda
formula_sql TEXT,                 -- a fórmula é dado público (auditabilidade)
direcao_melhor VARCHAR,           -- 'maior' | 'menor' | 'neutro'
valido_desde DATE, valido_ate DATE

-- fato_indicador_municipio (partição ano=YYYY)
codigo_municipio_ibge, ano SMALLINT, indicador_id, versao_metodologia,
valor DOUBLE, valor_formatado VARCHAR,
mediana_grupo DOUBLE, n_grupo INT,    -- referência do grupo de comparação (obrigatória em todo card)
posicao_grupo INT, posicao_uf INT, posicao_brasil INT,  -- rankings pré-computados
data_calculo TIMESTAMP, run_id VARCHAR
```

**Versionamento de metodologia**: fórmula mudou ⇒ nova `versao_metodologia`, série inteira recalculada sob a versão nova, versão antiga preservada no fato. O serving publica só a corrente; o parquet mantém todas ("recalculamos X, veja por quê").

Auxiliares: `mart_ranking_indicador_ano`; Fase 2: `fato_contrato` (grão contrato, chaves `cnpj_basico` + `codigo_municipio_ibge`).

## 5. Custo mensal estimado (USD, 300 GB maduro)

| Item | A: pipelines locais + storage cloud | B: tudo cloud, tráfego baixo | C: pico viral 100k visitas/dia |
|---|---|---|---|
| R2 storage 300 GB | $4,35 | $4,35 | $4,35 |
| R2 ops | ~$0,50 | ~$1 | ~$1–3 (CDN absorve) |
| Egress | $0 | $0 | **$0** |
| Compute (Actions, repo público) | $0 | $0 | $0 |
| VPS CNPJ (Fase 2) | — | ~€8 | ~€8 |
| Workers Paid (OG images dinâmicas, a partir do M3) | — | $5 | $5 |
| Site (Pages) + domínio | — | ~$1 | ~$1 |
| **Total** | **~$5** | **~$11–19** | **~$12–21** |

Comparativo: o cenário C em S3 custaria ~$180 só de egress. **A escolha do R2 é o que torna "viral" um não-evento financeiro.**

## 6. Backup e reprodutibilidade da raw

A raw é acervo, não cache (INEP apagou séries em 2022; SNIS saiu do ar):

1. **3-2-1**: (a) R2 `praca-raw` privado, classe Infrequent Access; (b) segunda cópia em **Backblaze B2** ($6/TB-mês, S3-compatible, mesmo código fsspec) — provedor distinto; (c) disco local vira cópia de trabalho.
2. **Imutabilidade**: no R2, é **convenção** — prefixos datados `raw/{fonte}/{AAAA-MM-DD}/{arquivo_original}`, nunca sobrescrever (o R2 **não implementa** versionamento de objetos nem Object Lock, e seus tokens não distinguem write de delete). A **garantia técnica** vem do espelho B2, que tem versioning/Object Lock ligados.
3. **Manifesto como prova**: sha256 + URL + timestamp publicados junto ao dado — qualquer pessoa verifica que o espelho corresponde ao que o governo publicou naquela data.
4. **Retenção CNPJ**: todos os zips do ano corrente + eleitoral; após 24 meses, reter jan/abr/jul/out (~91 GB/ano em IA ≈ $0,91/mês).
5. **Prioridade 2026 (ano eleitoral)**: espelhar antes de dezembro — INEP, SINISA/histórico SNIS, TSE 2026, DataSUS (ordem de risco de desaparecimento). Ver marco M0.5 no ESCOPO.md.
6. **Reprodutibilidade**: cada mart carrega `run_id` → commit + manifesto; raw imutável + git reconstrói qualquer publicação.
