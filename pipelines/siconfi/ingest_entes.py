"""Cadastro de entes federativos do SICONFI (União, 27 UFs, 5.570 municípios).

É a tabela-dimensão do projeto: traz cod_ibge (chave de cruzamento primária),
nome, UF, esfera, população e capital.

Uso: python -m pipelines.siconfi.ingest_entes
"""

import json
from datetime import date

from pipelines.common import alertas, manifest, storage
from pipelines.common.config import fonte
from pipelines.common.parquet import json_para_parquet
from pipelines.siconfi.api import Buscador, paginar
from pipelines.siconfi.transform import validar_minimo

MINIMO_ENTES = 5000  # ~5.598 esperados; menos que isso = resposta truncada/suspeita


def executar(*, buscar: Buscador | None = None, coleta: date | None = None) -> str:
    """Coleta os entes, guarda a raw do dia e promove ao staging. Devolve o parquet."""
    coleta = coleta or date.today()

    itens = validar_minimo(paginar("entes", buscar=buscar), minimo=MINIMO_ENTES, contexto="entes")
    dados = json.dumps(itens, ensure_ascii=False).encode("utf-8")

    raw = storage.caminho_raw("siconfi", "entes.json", coleta=coleta)
    storage.escrever_bytes(raw, dados)

    destino = storage.uri("staging", "siconfi", "entes.parquet")
    linhas = json_para_parquet(raw, destino)

    manifest.registrar(
        f"siconfi/entes/{coleta.isoformat()}",
        url=f"{fonte('siconfi')['api_base']}/entes",
        registros=linhas,
        sha256=manifest.sha256_bytes(dados),
    )
    return destino


def main() -> None:
    with alertas.falhas_alertadas("siconfi/entes"):
        print(f"entes gravados em {executar()}")


if __name__ == "__main__":
    main()
