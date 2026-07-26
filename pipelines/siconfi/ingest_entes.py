"""Cadastro de entes federativos do SICONFI (União, 27 UFs, 5.570 municípios).

É a tabela-dimensão do projeto: traz cod_ibge (chave de cruzamento primária),
nome, UF, esfera, população e capital.

Uso: python -m pipelines.siconfi.ingest_entes
"""

import json

from pipelines.common import manifest
from pipelines.common.config import RAW, STAGING, fonte
from pipelines.common.parquet import json_para_parquet
from pipelines.siconfi.api import paginar
from pipelines.siconfi.transform import validar_minimo

MINIMO_ENTES = 5000  # ~5.598 esperados; menos que isso = resposta truncada/suspeita


def main() -> None:
    raw_dir = RAW / "siconfi"
    raw_dir.mkdir(parents=True, exist_ok=True)

    itens = validar_minimo(paginar("entes"), minimo=MINIMO_ENTES, contexto="entes")

    raw_path = raw_dir / "entes.json"
    raw_path.write_text(json.dumps(itens, ensure_ascii=False), encoding="utf-8")

    parquet = STAGING / "siconfi" / "entes.parquet"
    linhas = json_para_parquet(raw_path, parquet)

    manifest.registrar(
        "siconfi/entes",
        url=f"{fonte('siconfi')['api_base']}/entes",
        registros=linhas,
        sha256=manifest.sha256_arquivo(raw_path),
    )
    print(f"{linhas} entes gravados em {parquet}")


if __name__ == "__main__":
    main()
