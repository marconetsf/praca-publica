"""Transformações puras do SICONFI — testáveis sem rede."""

from pathlib import Path

from pipelines.common.parquet import conectar


def validar_minimo(itens: list[dict], *, minimo: int, contexto: str) -> list[dict]:
    """Guarda de qualidade: menos itens que o esperado = dado suspeito, não promover."""
    if len(itens) < minimo:
        raise RuntimeError(
            f"Apenas {len(itens)} itens em '{contexto}' (mínimo {minimo}) — não promovendo"
        )
    return itens


def municipios_da_uf(entes_parquet: str | Path, uf: str) -> list[int]:
    """Códigos IBGE dos municípios de uma UF, a partir do parquet de entes."""
    caminho = (
        entes_parquet.as_posix()
        if isinstance(entes_parquet, Path)
        else str(entes_parquet).replace("\\", "/")
    )
    linhas = (
        conectar(caminho)
        .sql(
            f"""
            SELECT cod_ibge FROM '{caminho}'
            WHERE esfera = 'M' AND uf = '{uf.upper()}'
            ORDER BY cod_ibge
            """
        )
        .fetchall()
    )
    return [linha[0] for linha in linhas]
