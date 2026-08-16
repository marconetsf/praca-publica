# Praça Pública

Acessibilização de dados públicos brasileiros: scanning periódico de bases abertas, tabulação em
parquet e cruzamento para gerar informação compreensível para a população geral.

## Arquitetura

```
config/fontes.yaml     fonte da verdade de URLs e parâmetros de cada base (nunca hardcode)
data/
├── raw/               arquivos originais imutáveis, como baixados (espelho defensivo)
├── staging/           parquet 1:1 com a fonte (zstd), tipos corrigidos, UTF-8
└── marts/             tabelas cruzadas e agregados prontos para publicação
pipelines/
├── common/            manifesto de downloads (idempotência) + HTTP com retry
└── siconfi/           primeiro pipeline: finanças municipais (Tesouro Nacional)
```

- **Engine analítica**: DuckDB sobre parquet — sem banco de dados para gerenciar.
- **Chave de cruzamento primária**: código IBGE de município (7 dígitos); secundária: CNPJ básico (8 dígitos).
- **Idempotência**: todo download é registrado em `data/manifest.json` (URL, sha256, data); re-execuções pulam o que já foi processado.
- **Regra de ouro**: falhar ruidosamente — dado suspeito (schema diferente, variação anômala de linhas) não é promovido a staging.

Catálogo completo de fontes, riscos e decisões: [FONTES.md](FONTES.md).

## Especificação completa

O escopo de desenvolvimento (visão → lançamento) está em [docs/ESCOPO.md](docs/ESCOPO.md), com detalhes por área:
[arquitetura/cloud](docs/arquitetura/ARQUITETURA.md) · [produto/design](docs/produto/PRODUTO.md) · [insights/viralização](docs/engajamento/CRESCIMENTO.md) · [segurança/LGPD](docs/infra/SEGURANCA.md) · [operação/CI-CD](docs/infra/OPERACAO.md).

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Desenvolvimento é **TDD sempre**: teste primeiro (vermelho), implementação (verde), refatoração.

```powershell
pytest -q            # suíte padrão (sem rede)
pytest -q -m live    # smoke tests contra as APIs reais
ruff check .; ruff format .
```

## Uso

```powershell
# cadastro de todos os entes federativos (União, estados, 5.570 municípios)
python -m pipelines.siconfi.ingest_entes

# declarações anuais de contas (DCA) dos municípios de uma UF
python -m pipelines.siconfi.ingest_dca --exercicio 2024 --uf PE
```

Os resultados ficam em `data/staging/siconfi/*.parquet`, consultáveis direto:

```python
import duckdb

duckdb.sql("SELECT * FROM 'data/staging/siconfi/entes.parquet' WHERE uf = 'PE' LIMIT 5").show()
```

## Fases

1. **Painel municipal** — IBGE + SICONFI + DataSUS (agregado) + INEP + ANEEL + CAGED, cruzados por código IBGE. Risco LGPD zero.
2. **Quem vende para o governo** — dump mensal do CNPJ (snapshot + diff) × PNCP × Portal da Transparência (requer token da CGU).
3. **Camada política e espacial** — TSE, Querido Diário, setor censitário (CNEFE).
