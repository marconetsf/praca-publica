"""dim_municipio — a dimensão que ancora todo o mart (ESCOPO M2.1).

É aqui que a **regra 2** do projeto é cumprida: `codigo_municipio_ibge` é
VARCHAR(7), nunca INT. O SICONFI entrega o código como número; esta é a
fronteira onde ele vira texto e passa a ser tratado como identificador, não
como quantidade. Depois deste ponto, nenhum join precisa lembrar de zero à
esquerda.

Fonte no MVP: `staging/siconfi/entes.parquet`, que já traz população, UF e
Grande Região dos 5.570 municípios. O IBGE entra no M1.3 para substituir a
população por estimativa oficial datada — por ora a do SICONFI serve, e o
campo `fonte_populacao` registra isso para não se perder a proveniência.

Uso: python -m pipelines.marts.dim_municipio
"""

import unicodedata

from pipelines.common import parquet, storage

# 7 faixas do PRODUTO §2 regra 3 — o limite superior é exclusivo
FAIXAS = (
    (5_000, "ate_5k"),
    (10_000, "5k_10k"),
    (20_000, "10k_20k"),
    (50_000, "20k_50k"),
    (100_000, "50k_100k"),
    (500_000, "100k_500k"),
)
FAIXA_MAIOR = "acima_500k"


def faixa_porte(populacao: int | None) -> str | None:
    """Faixa de porte pela população. Sem população não há faixa (regra 4)."""
    if not populacao or populacao <= 0:
        return None
    for limite, nome in FAIXAS:
        if populacao < limite:
            return nome
    return FAIXA_MAIOR


def slug(nome: str) -> str:
    """`Alta Floresta D'Oeste` → `alta-floresta-doeste`. Único dentro da UF."""
    sem_acento = "".join(
        letra for letra in unicodedata.normalize("NFD", nome) if unicodedata.category(letra) != "Mn"
    )
    limpo = "".join(
        letra if letra.isalnum() else " " if letra in " -" else "" for letra in sem_acento
    )
    return "-".join(limpo.lower().split())


def _sql_faixa(coluna: str) -> str:
    """A mesma escada de FAIXAS, em SQL — mantida ao lado da versão Python."""
    casos = " ".join(f"WHEN {coluna} < {limite} THEN '{nome}'" for limite, nome in FAIXAS)
    return f"CASE WHEN {coluna} IS NULL OR {coluna} <= 0 THEN NULL {casos} ELSE '{FAIXA_MAIOR}' END"


def construir(entes_parquet, destino) -> int:
    """Monta a dimensão a partir do parquet de entes e devolve o nº de linhas."""
    origem = parquet._posix(entes_parquet)
    saida = parquet._posix(destino)
    con = parquet.conectar(origem, saida)

    # o slug é gerado em Python (unicodedata) e trazido por join, para que a
    # regra de normalização exista em um lugar só
    linhas = con.sql(f"SELECT cod_ibge, ente FROM '{origem}' WHERE esfera = 'M'").fetchall()
    slugs = [(str(cod).zfill(7), slug(nome)) for cod, nome in linhas]
    con.execute("CREATE TABLE slugs (codigo_municipio_ibge VARCHAR, slug VARCHAR)")
    con.executemany("INSERT INTO slugs VALUES (?, ?)", slugs)

    con.execute(f"""
        COPY (
            SELECT
                lpad(CAST(e.cod_ibge AS VARCHAR), 7, '0') AS codigo_municipio_ibge,
                e.ente        AS nome,
                s.slug        AS slug,
                e.uf          AS uf,
                e.regiao      AS regiao,
                e.populacao   AS populacao_referencia,
                'siconfi/entes' AS fonte_populacao,
                {_sql_faixa("e.populacao")} AS faixa_porte,
                e.regiao || '|' || {_sql_faixa("e.populacao")} AS grupo_comparacao,
                e.capital = '1' AS eh_capital
            FROM '{origem}' e
            JOIN slugs s ON s.codigo_municipio_ibge = lpad(CAST(e.cod_ibge AS VARCHAR), 7, '0')
            WHERE e.esfera = 'M'
            ORDER BY 1
        ) TO '{saida}' (FORMAT parquet, COMPRESSION zstd)
    """)

    (total,) = con.sql(f"SELECT count(*) FROM '{saida}'").fetchone()
    _validar(con, saida)
    return total


def _validar(con, saida: str) -> None:
    """Asserções que o ESCOPO exige: slug único por UF e código com 7 dígitos."""
    duplicados = con.sql(f"""
        SELECT uf, slug, count(*) AS n FROM '{saida}' GROUP BY 1,2 HAVING n > 1
    """).fetchall()
    if duplicados:
        raise RuntimeError(f"slug duplicado dentro da UF: {duplicados[:5]}")

    (tortos,) = con.sql(
        f"SELECT count(*) FROM '{saida}' WHERE length(codigo_municipio_ibge) <> 7"
    ).fetchone()
    if tortos:
        raise RuntimeError(f"{tortos} códigos IBGE fora do formato VARCHAR(7)")


def main() -> None:
    entes = storage.uri("staging", "siconfi", "entes.parquet")
    destino = storage.uri("marts", "dim_municipio.parquet")
    total = construir(entes, destino)
    print(f"{total} municípios em {destino}")


if __name__ == "__main__":
    main()
