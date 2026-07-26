"""Transformações puras do SICONFI — testáveis sem rede."""

from pathlib import Path

import duckdb


def validar_minimo(itens: list[dict], *, minimo: int, contexto: str) -> list[dict]:
    """Guarda de qualidade: menos itens que o esperado = dado suspeito, não promover."""
    if len(itens) < minimo:
        raise RuntimeError(
            f"Apenas {len(itens)} itens em '{contexto}' (mínimo {minimo}) — não promovendo"
        )
    return itens


def municipios_da_uf(entes_parquet: Path, uf: str) -> list[int]:
    """Códigos IBGE dos municípios de uma UF, a partir do parquet de entes."""
    linhas = duckdb.sql(
        f"""
        SELECT cod_ibge FROM '{entes_parquet.as_posix()}'
        WHERE esfera = 'M' AND uf = '{uf.upper()}'
        ORDER BY cod_ibge
        """
    ).fetchall()
    return [linha[0] for linha in linhas]
