"""fato_indicador_municipio — o mart que a página do município consome (M2.3).

Fato longo (`município × ano × indicador`): indicador novo é INSERT, nunca
ALTER TABLE. A comparação vem junto no fato — `mediana_grupo` e `n_grupo` são
colunas, não cálculo de frontend, porque a régua do PRODUTO §2 regra 3 diz que
nenhum card existe sem valor de referência.

Três decisões que os dados reais impuseram:

1. **Anexo I-E, não I-G.** Os dois trazem "10 - Saúde", mas só o I-E tem a
   coluna "Despesas Pagas". Usar o outro publicaria número errado.
2. **Ausência não é zero** (regra 4). Município que não declarou não vira linha
   com valor 0 — não vira linha, e não entra na mediana dos outros.
3. **Grupo com menos de 5 municípios não publica mediana.** O menor grupo do
   país tem 4 (Norte acima de 500 mil); mediana de 4 não é "o típico das
   parecidas", é ruído com aparência de referência.

Uso: python -m pipelines.marts.fato_indicador --ano 2024
"""

import argparse
from dataclasses import dataclass

from pipelines.common import parquet, storage

# abaixo disso a mediana do grupo é instável demais para virar referência pública
MINIMO_GRUPO = 5


@dataclass(frozen=True)
class Indicador:
    """Definição de um indicador — inclui a procedência, que é obrigatória.

    "Como esse cálculo foi feito?" é feature de todo número publicado, não de
    alguns. Por isso os campos de procedência moram aqui, ao lado da regra de
    cálculo: indicador novo sem eles quebra o teste antes de virar página.
    """

    indicador_id: str
    nome_exibicao: str
    descricao_publica: str
    unidade: str
    direcao_melhor: str  # 'maior' | 'menor' | 'neutro'
    anexo: str
    coluna: str
    conta: str
    formula_legivel: str  # em português, para o leitor — sem jargão de banco
    ressalvas: str  # o que o leitor precisa saber antes de tirar conclusão
    fonte: str = "SICONFI/DCA"
    orgao: str = "Tesouro Nacional"
    versao_metodologia: int = 1

    @property
    def formula_sql(self) -> str:
        """A fórmula técnica, para quem quiser auditar ou reproduzir."""
        return (
            f"valor de '{self.conta}' no {self.anexo} (coluna '{self.coluna}') "
            "dividido pela população do município no ano de referência"
        )

    def url_dado_bruto(self, *, codigo_ibge: str, ano: int) -> str:
        """Link para o dado deste município na API pública do Tesouro.

        Abre no navegador e devolve o JSON da declaração — o leitor confere na
        origem, não numa cópia nossa. É a diferença entre "confie em nós" e
        "veja você mesmo".
        """
        return (
            "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/dca"
            f"?an_exercicio={ano}&id_ente={codigo_ibge}"
        )


INDICADORES: tuple[Indicador, ...] = (
    Indicador(
        indicador_id="siconfi_despesa_saude_pc",
        nome_exibicao="Gasto com saúde por morador",
        descricao_publica="Hospitais, postos e agentes de saúde.",
        unidade="R$/morador/ano",
        # gastar mais não é melhor nem pior por si só — composição não tem valência
        direcao_melhor="neutro",
        anexo="DCA-Anexo I-E",
        coluna="Despesas Pagas",
        conta="10 - Saúde",
        formula_legivel=(
            "O que a prefeitura pagou em saúde no ano, dividido pelos moradores. "
            "Usamos o valor pago, não o empenhado: empenhado é promessa de gasto."
        ),
        ressalvas=(
            "Quem declara é a prefeitura, e o Tesouro publica sem auditar. "
            "Cidade pequena tende a gastar mais por morador — custo fixo dividido "
            "entre menos gente. Por isso a comparação é só com cidades de porte parecido."
        ),
    ),
    Indicador(
        indicador_id="siconfi_despesa_educacao_pc",
        nome_exibicao="Gasto com educação por morador",
        descricao_publica="Escolas, merenda e transporte escolar.",
        unidade="R$/morador/ano",
        direcao_melhor="neutro",
        anexo="DCA-Anexo I-E",
        coluna="Despesas Pagas",
        conta="12 - Educação",
        formula_legivel=(
            "O que a prefeitura pagou em educação no ano, dividido pelos moradores "
            "da cidade — **não** pelo número de alunos."
        ),
        # A ressalva mais importante do MVP: o leitor lê "educação por morador" e
        # entende "investimento por aluno", que é outra conta. Enquanto o Censo
        # Escolar (M1.4) não entra, o texto precisa dizer isso de frente.
        ressalvas=(
            "Atenção: este número mede o esforço do orçamento, não o investimento por "
            "aluno. Saúde atende todo mundo; escola atende quem estuda. Cidade com mais "
            "crianças aparece gastando mais por morador sem gastar mais por aluno. "
            "O gasto por aluno depende do número de matrículas, que entra em versão futura."
        ),
    ),
    Indicador(
        indicador_id="siconfi_receita_impostos_pc",
        nome_exibicao="Impostos arrecadados por morador",
        descricao_publica="IPTU, ISS e outros impostos da própria cidade.",
        unidade="R$/morador/ano",
        direcao_melhor="neutro",
        anexo="DCA-Anexo I-C",
        coluna="Receitas Brutas Realizadas",
        conta="1.1.1.0.00.0.0 - Impostos",
        formula_legivel=(
            "Os impostos que a própria prefeitura arrecadou no ano, divididos pelos "
            "moradores. Repasses da União e do estado ficam de fora."
        ),
        ressalvas=(
            "Arrecadar pouco não significa má gestão: depende da economia local e do "
            "valor dos imóveis. Na maioria das cidades brasileiras, o dinheiro vem "
            "principalmente de repasses, não de impostos próprios."
        ),
    ),
)


def _sql_indicador(ind: Indicador, dca: str) -> str:
    conta = ind.conta.replace("'", "''")
    return f"""
        SELECT
            lpad(CAST(cod_ibge AS VARCHAR), 7, '0') AS codigo_municipio_ibge,
            '{ind.indicador_id}' AS indicador_id,
            {ind.versao_metodologia} AS versao_metodologia,
            valor AS valor_bruto
        FROM '{dca}'
        WHERE anexo = '{ind.anexo}' AND coluna = '{ind.coluna}' AND conta = '{conta}'
          AND valor IS NOT NULL
          -- receita bruta ou despesa paga negativa é impossível; 31 municípios do
          -- TO declararam assim em 2024. Regra 4: dado suspeito não é promovido —
          -- melhor o card faltar do que exibir "-R$ 3.827 por morador"
          AND valor >= 0
    """


def construir(dca_parquet, dim_parquet, destino, *, ano: int) -> int:
    """Monta o fato para um exercício e devolve o nº de linhas."""
    dca = parquet._posix(dca_parquet)
    dim = parquet._posix(dim_parquet)
    saida = parquet._posix(destino)
    con = parquet.conectar(dca, dim, saida)

    bruto = "\n            UNION ALL\n".join(_sql_indicador(i, dca) for i in INDICADORES)

    con.execute(f"""
        CREATE TABLE base AS
        WITH bruto AS ({bruto})
        SELECT
            b.codigo_municipio_ibge,
            {ano} AS ano,
            b.indicador_id,
            b.versao_metodologia,
            b.valor_bruto / m.populacao_referencia AS valor,
            m.grupo_comparacao
        FROM bruto b
        -- INNER JOIN: município fora da dimensão não entra; município da dimensão
        -- que não declarou simplesmente não tem linha (regra 4: ausência ≠ zero)
        JOIN '{dim}' m USING (codigo_municipio_ibge)
        WHERE m.populacao_referencia > 0
    """)

    con.execute(f"""
        COPY (
            SELECT
                codigo_municipio_ibge, ano, indicador_id, versao_metodologia, valor,
                CASE WHEN n_grupo >= {MINIMO_GRUPO} THEN mediana END AS mediana_grupo,
                n_grupo,
                CASE WHEN n_grupo >= {MINIMO_GRUPO} THEN posicao END AS posicao_grupo,
                grupo_comparacao
            FROM (
                SELECT *,
                    median(valor) OVER (PARTITION BY indicador_id, grupo_comparacao) AS mediana,
                    count(*)     OVER (PARTITION BY indicador_id, grupo_comparacao) AS n_grupo,
                    rank() OVER (
                        PARTITION BY indicador_id, grupo_comparacao ORDER BY valor DESC
                    ) AS posicao
                FROM base
            )
            ORDER BY codigo_municipio_ibge, indicador_id
        ) TO '{saida}' (FORMAT parquet, COMPRESSION zstd)
    """)

    (total,) = con.sql(f"SELECT count(*) FROM '{saida}'").fetchone()
    return total


def construir_dim_indicador(destino) -> int:
    """A metodologia é dado público (ARQUITETURA §4): vira parquet junto do fato."""
    saida = parquet._posix(destino)
    con = parquet.conectar(saida)
    con.execute(
        "CREATE TABLE d (indicador_id VARCHAR, nome_exibicao VARCHAR, "
        "descricao_publica VARCHAR, fonte VARCHAR, orgao VARCHAR, unidade VARCHAR, "
        "direcao_melhor VARCHAR, versao_metodologia INT, formula_sql VARCHAR, "
        "formula_legivel VARCHAR, ressalvas VARCHAR)"
    )
    con.executemany(
        "INSERT INTO d VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                i.indicador_id,
                i.nome_exibicao,
                i.descricao_publica,
                i.fonte,
                i.orgao,
                i.unidade,
                i.direcao_melhor,
                i.versao_metodologia,
                i.formula_sql,
                i.formula_legivel,
                i.ressalvas,
            )
            for i in INDICADORES
        ],
    )
    con.execute(f"COPY d TO '{saida}' (FORMAT parquet, COMPRESSION zstd)")
    return len(INDICADORES)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ano", type=int, default=2024)
    args = parser.parse_args()

    dca = storage.uri(
        "staging", "siconfi", "dca", f"an_exercicio={args.ano}", "uf=*", "dca.parquet"
    )
    dim = storage.uri("marts", "dim_municipio.parquet")
    destino = storage.uri("marts", f"fato_indicador_municipio/ano={args.ano}", "fato.parquet")

    linhas = construir(dca, dim, destino, ano=args.ano)
    construir_dim_indicador(storage.uri("marts", "dim_indicador.parquet"))
    print(f"{linhas} linhas em {destino}")


if __name__ == "__main__":
    main()
