"""Gera os JSONs que o site consome (ARQUITETURA §3).

Um JSON por município, contendo **tudo** que a página precisa: um fetch resolve a
página inteira, sem join no navegador. Por isso a proveniência (fonte, ano de
referência, data de coleta) e a comparação de grupo viajam dentro de cada
indicador, em vez de serem montadas no frontend.

Dois cuidados que vêm direto das regras do produto:

- `comparacao` é `null` — nunca ausente — quando o grupo é pequeno demais. O site
  precisa distinguir "não é comparável" de "faltou gerar".
- o texto da posição já vem pronto com denominador ("4º entre os 7 parecidos"),
  para que nenhuma camada adiante seja tentada a escrever "melhor" ou "pior".

Uso: python -m pipelines.marts.serving --ano 2024
"""

import argparse
import json
from datetime import date
from pathlib import Path

from pipelines.common import parquet, storage


def url_dado_bruto(indicador_id: str, codigo_ibge: str, ano: int) -> str:
    """Link para o dado bruto deste município, na API pública do órgão de origem.

    Vem da definição do indicador, para que a URL nunca divirja da conta que foi
    de fato usada. Indicador de outra fonte traz sua própria regra de link.
    """
    from pipelines.marts.fato_indicador import INDICADORES

    definicao = next(i for i in INDICADORES if i.indicador_id == indicador_id)
    return definicao.url_dado_bruto(codigo_ibge=codigo_ibge, ano=ano)


def texto_posicao(posicao: int | None, n_grupo: int | None) -> str | None:
    """Regra 6 do PRODUTO §2: posição sempre com denominador e grupo."""
    if not posicao or not n_grupo:
        return None
    return f"{posicao}º entre os {n_grupo} parecidos"


def _montar(linhas, indicadores: dict, ano: int, coletado_em: str) -> dict:
    """Uma linha por indicador do mesmo município → o dicionário da página."""
    primeira = linhas[0]
    municipio = {
        "codigo_ibge": primeira["codigo_municipio_ibge"],
        "nome": primeira["nome"],
        "slug": primeira["slug"],
        "uf": primeira["uf"],
        "regiao": primeira["regiao"],
        "populacao": primeira["populacao_referencia"],
        "faixa_porte": primeira["faixa_porte"],
        "eh_capital": primeira["eh_capital"],
        "ano_referencia": ano,
        "coletado_em": coletado_em,
        # município que não entregou nada tem página e diz isso; sumir do site
        # seria apagar justamente o ente sobre o qual há algo a informar
        "sem_nenhum_dado": not primeira.get("indicador_id"),
        "indicadores": [],
    }
    if municipio["sem_nenhum_dado"]:
        return municipio

    for linha in linhas:
        meta = indicadores[linha["indicador_id"]]
        comparacao = None
        if linha["mediana_grupo"] is not None:
            comparacao = {
                "mediana_parecidos": linha["mediana_grupo"],
                "n_parecidos": linha["n_grupo"],
                "posicao": linha["posicao_grupo"],
                "grupo": linha["grupo_comparacao"],
                "texto": texto_posicao(linha["posicao_grupo"], linha["n_grupo"]),
            }
        municipio["indicadores"].append(
            {
                "id": linha["indicador_id"],
                "nome": meta["nome_exibicao"],
                "descricao": meta["descricao_publica"],
                "valor": linha["valor"],
                "unidade": meta["unidade"],
                "direcao_melhor": meta["direcao_melhor"],
                "fonte": meta["fonte"],
                "ano_referencia": ano,
                "coletado_em": coletado_em,
                "versao_metodologia": linha["versao_metodologia"],
                "comparacao": comparacao,
                # "Como esse cálculo foi feito?" — obrigatório em todo número
                # publicado. O link leva ao dado bruto DESTE município na API do
                # órgão de origem: o leitor confere na fonte, não numa cópia nossa.
                "procedencia": {
                    "orgao": meta["orgao"],
                    "fonte": meta["fonte"],
                    "formula_legivel": meta["formula_legivel"],
                    "formula_sql": meta["formula_sql"],
                    "ressalvas": meta["ressalvas"],
                    "versao_metodologia": linha["versao_metodologia"],
                    "ano_referencia": ano,
                    "coletado_em": coletado_em,
                    "url_dado_bruto": url_dado_bruto(
                        linha["indicador_id"], municipio["codigo_ibge"], ano
                    ),
                },
            }
        )
    return municipio


def gerar(
    dim_parquet,
    fato_parquet,
    dim_indicador_parquet,
    destino,
    *,
    ano: int,
    coletado_em: str | None = None,
    universo: list[str] | None = None,
) -> int:
    """Escreve `municipio/{codigo}.json` + `busca.json`. Devolve quantos municípios.

    `universo` é a lista de municípios que **deveriam** ter página — tipicamente
    todos os das UFs já coletadas. Quem está no universo e não tem nenhuma linha
    no fato ganha página de ausência, em vez de sumir do site: era o caso de 7
    municípios do Norte, 112 mil habitantes, invisíveis porque não declararam.
    """
    coletado_em = coletado_em or date.today().isoformat()
    dim = parquet._posix(dim_parquet)
    fato = parquet._posix(fato_parquet)
    dim_ind = parquet._posix(dim_indicador_parquet)
    con = parquet.conectar(dim, fato, dim_ind)

    campos_indicador = (
        "indicador_id",
        "nome_exibicao",
        "descricao_publica",
        "fonte",
        "orgao",
        "unidade",
        "direcao_melhor",
        "formula_sql",
        "formula_legivel",
        "ressalvas",
    )
    indicadores = {
        linha[0]: dict(zip(campos_indicador, linha, strict=True))
        for linha in con.sql(f"SELECT {', '.join(campos_indicador)} FROM '{dim_ind}'").fetchall()
    }

    colunas = [
        "codigo_municipio_ibge",
        "nome",
        "slug",
        "uf",
        "regiao",
        "populacao_referencia",
        "faixa_porte",
        "eh_capital",
        "indicador_id",
        "versao_metodologia",
        "valor",
        "mediana_grupo",
        "n_grupo",
        "posicao_grupo",
        "grupo_comparacao",
    ]
    resultado = con.sql(f"""
        SELECT
            f.codigo_municipio_ibge,
            m.nome, m.slug, m.uf, m.regiao, m.populacao_referencia,
            m.faixa_porte, m.eh_capital,
            f.indicador_id, f.versao_metodologia, f.valor,
            f.mediana_grupo, f.n_grupo, f.posicao_grupo,
            m.grupo_comparacao          -- nasce na dimensão; o fato só o replica
        FROM '{fato}' f
        JOIN '{dim}' m USING (codigo_municipio_ibge)
        WHERE f.ano = {ano}
        ORDER BY f.codigo_municipio_ibge, f.indicador_id
    """).fetchall()

    por_municipio: dict[str, list[dict]] = {}
    for linha in resultado:
        registro = dict(zip(colunas, linha, strict=True))
        por_municipio.setdefault(registro["codigo_municipio_ibge"], []).append(registro)

    if universo:
        faltantes = [codigo for codigo in universo if codigo not in por_municipio]
        if faltantes:
            lista = ", ".join(f"'{c}'" for c in faltantes)
            identificacao = con.sql(f"""
                SELECT codigo_municipio_ibge, nome, slug, uf, regiao,
                       populacao_referencia, faixa_porte, eh_capital
                FROM '{dim}' WHERE codigo_municipio_ibge IN ({lista})
            """).fetchall()
            campos = (
                "codigo_municipio_ibge",
                "nome",
                "slug",
                "uf",
                "regiao",
                "populacao_referencia",
                "faixa_porte",
                "eh_capital",
            )
            for linha in identificacao:
                registro = dict(zip(campos, linha, strict=True))
                por_municipio[registro["codigo_municipio_ibge"]] = [registro]

    pasta = Path(destino)
    (pasta / "municipio").mkdir(parents=True, exist_ok=True)

    indice = []
    for codigo, linhas in por_municipio.items():
        dados = _montar(linhas, indicadores, ano, coletado_em)
        (pasta / "municipio" / f"{codigo}.json").write_text(
            json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        indice.append(
            {
                "codigo_ibge": codigo,
                "nome": dados["nome"],
                "slug": dados["slug"],
                "uf": dados["uf"],
            }
        )

    indice.sort(key=lambda m: (m["uf"], m["nome"]))
    (pasta / "busca.json").write_text(json.dumps(indice, ensure_ascii=False), encoding="utf-8")
    return len(indice)


def universo_coletado(dim_parquet, ano: int) -> list[str]:
    """Municípios que já deveriam ter página: todos das UFs com staging do ano.

    Deriva das UFs presentes no staging — a fonte da verdade sobre o que foi
    coletado. Município que não declarou não aparece no staging, mas a UF dele
    sim, e é assim que ele volta para a lista.
    """
    prefixo = storage.uri("staging", "siconfi", "dca", f"an_exercicio={ano}", "*")
    ufs = sorted(
        {
            caminho.rstrip("/").split("uf=")[-1]
            for caminho in storage.listar(prefixo)
            if "uf=" in caminho
        }
    )
    if not ufs:
        return []

    lista = ", ".join(f"'{uf}'" for uf in ufs)
    con = parquet.conectar(parquet._posix(dim_parquet))
    return [
        linha[0]
        for linha in con.sql(f"""
            SELECT codigo_municipio_ibge FROM '{parquet._posix(dim_parquet)}'
            WHERE uf IN ({lista}) ORDER BY 1
        """).fetchall()
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ano", type=int, default=2024)
    parser.add_argument("--destino", default="site/public/dados")
    args = parser.parse_args()

    dim = storage.uri("marts", "dim_municipio.parquet")
    total = gerar(
        dim,
        storage.uri("marts", f"fato_indicador_municipio/ano={args.ano}", "fato.parquet"),
        storage.uri("marts", "dim_indicador.parquet"),
        args.destino,
        ano=args.ano,
        universo=universo_coletado(dim, args.ano),
    )
    print(f"{total} municípios em {args.destino}/municipio/")


if __name__ == "__main__":
    main()
