"""Declaração de Contas Anuais (DCA) dos municípios de uma UF, por exercício.

A DCA é a base do painel municipal: despesas e receitas por função (saúde,
educação...), cruzáveis com população para gasto per capita.

Pré-requisito: rodar ingest_entes antes (usa entes.parquet para listar municípios).

Uso: python -m pipelines.siconfi.ingest_dca --exercicio 2024 --uf PE
"""

import argparse
import json

from pipelines.common import manifest
from pipelines.common.config import RAW, STAGING
from pipelines.common.parquet import json_para_parquet
from pipelines.siconfi.api import paginar
from pipelines.siconfi.transform import municipios_da_uf


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exercicio", type=int, required=True)
    parser.add_argument("--uf", required=True, help="Sigla da UF, ex.: PE")
    args = parser.parse_args()

    uf = args.uf.upper()
    raw_dir = RAW / "siconfi" / f"dca_{args.exercicio}_{uf}"
    raw_dir.mkdir(parents=True, exist_ok=True)

    entes_parquet = STAGING / "siconfi" / "entes.parquet"
    if not entes_parquet.exists():
        raise SystemExit("Rode antes: python -m pipelines.siconfi.ingest_entes")

    municipios = municipios_da_uf(entes_parquet, uf)
    sem_declaracao = 0
    for i, cod_ibge in enumerate(municipios, 1):
        chave = f"siconfi/dca/{args.exercicio}/{cod_ibge}"
        if manifest.ja_processado(chave):
            continue
        itens = paginar("dca", {"an_exercicio": args.exercicio, "id_ente": cod_ibge})
        if not itens:
            # municípios pequenos atrasam ou não entregam a DCA — lacuna esperada
            sem_declaracao += 1
        else:
            destino = raw_dir / f"{cod_ibge}.json"
            destino.write_text(json.dumps(itens, ensure_ascii=False), encoding="utf-8")
        manifest.registrar(chave, registros=len(itens))
        if i % 25 == 0:
            print(f"{i}/{len(municipios)} municípios de {uf}...")

    arquivos = list(raw_dir.glob("*.json"))
    if not arquivos:
        raise SystemExit(f"Nenhuma DCA encontrada para {uf}/{args.exercicio}")

    parquet = STAGING / "siconfi" / f"dca/an_exercicio={args.exercicio}/uf={uf}" / "dca.parquet"
    json_para_parquet(raw_dir / "*.json", parquet)
    print(
        f"{len(arquivos)} municípios gravados em {parquet} "
        f"({sem_declaracao} sem declaração — lacuna conhecida do SICONFI)"
    )


if __name__ == "__main__":
    main()
