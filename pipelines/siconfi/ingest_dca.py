"""Declaração de Contas Anuais (DCA) dos municípios de uma UF, por exercício.

A DCA é a base do painel municipal: despesas e receitas por função (saúde,
educação...), cruzáveis com população para gasto per capita.

Município sem DCA não é lacuna definitiva — muitos entregam com meses de atraso.
Por isso a ausência é registrada como incompleta e reconsultada depois da janela
de captura (ver pipelines/common/manifest.py).

Pré-requisito: rodar ingest_entes antes (usa entes.parquet para listar municípios).

Uso: python -m pipelines.siconfi.ingest_dca --exercicio 2024 --uf PE
"""

import argparse
import json
from datetime import date

from pipelines.common import alertas, manifest, storage
from pipelines.common.parquet import json_para_parquet
from pipelines.siconfi.api import Buscador, paginar
from pipelines.siconfi.transform import municipios_da_uf


def executar(
    exercicio: int,
    uf: str,
    *,
    buscar: Buscador | None = None,
    coleta: date | None = None,
    janela_dias: int = manifest.JANELA_PADRAO_DIAS,
) -> str:
    """Coleta a DCA de todos os municípios da UF e promove ao staging."""
    coleta = coleta or date.today()
    uf = uf.upper()
    pasta = f"dca_{exercicio}_{uf}"

    entes_parquet = storage.uri("staging", "siconfi", "entes.parquet")
    if not storage.existe(entes_parquet):
        raise SystemExit("Rode antes: python -m pipelines.siconfi.ingest_entes")

    municipios = municipios_da_uf(entes_parquet, uf)
    sem_declaracao = 0
    try:
        for i, cod_ibge in enumerate(municipios, 1):
            chave = f"siconfi/dca/{exercicio}/{cod_ibge}"
            if manifest.ja_processado(chave, janela_dias=janela_dias):
                continue

            itens = paginar("dca", {"an_exercicio": exercicio, "id_ente": cod_ibge}, buscar=buscar)
            if itens:
                storage.escrever_bytes(
                    storage.caminho_raw("siconfi", pasta, f"{cod_ibge}.json", coleta=coleta),
                    json.dumps(itens, ensure_ascii=False).encode("utf-8"),
                )
            else:
                sem_declaracao += 1

            # salvar_agora=False: um PUT por município seria 5.570 escritas no R2
            manifest.registrar(
                chave, registros=len(itens), completo=bool(itens), salvar_agora=False
            )
            if i % 25 == 0:
                print(f"{i}/{len(municipios)} municípios de {uf}...")
    finally:
        manifest.salvar()  # interrupção no meio não pode perder o que já foi coletado

    arquivos = storage.coletas_mais_recentes("siconfi", pasta, "*.json")
    if not arquivos:
        raise SystemExit(f"Nenhuma DCA encontrada para {uf}/{exercicio}")

    destino = storage.uri(
        "staging", "siconfi", "dca", f"an_exercicio={exercicio}", f"uf={uf}", "dca.parquet"
    )
    json_para_parquet(arquivos, destino)
    print(
        f"{len(arquivos)} municípios gravados em {destino} "
        f"({sem_declaracao} sem declaração nesta coleta — reconsultados em {janela_dias} dias)"
    )
    return destino


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exercicio", type=int, required=True)
    parser.add_argument("--uf", required=True, help="Sigla da UF, ex.: PE")
    args = parser.parse_args()
    with alertas.falhas_alertadas(f"siconfi/dca {args.exercicio}/{args.uf.upper()}"):
        executar(args.exercicio, args.uf)


if __name__ == "__main__":
    main()
