"""Gate 2 de sanidade: confere os números antes de virarem página (ESCOPO M2.4).

Existe porque "olhar e ver se faz sentido" não escala e não é reproduzível.
Ninguém precisa saber de cor quanto um município gasta por morador — o gate
usa âncoras que não dependem de julgamento:

1. **Aritmética**: a soma das funções não pode exceder a despesa total declarada,
   e valor negativo em despesa ou receita não existe.
2. **Pisos constitucionais**: educação tem piso de 25% (CF art. 212) e saúde de
   15% (LC 141/2012). Um município aparecendo com 4% em educação denuncia erro
   de dado muito antes de denunciar má gestão.

⚠️ **O percentual daqui é indicador de sanidade, não aferição legal.** A base de
cálculo do piso real exclui transferências que somamos (SUS, FNDE, convênios),
então nosso denominador é maior e o percentual sai menor que o oficial. Serve
para achar erro nosso; **nunca** para afirmar que um município descumpriu a
Constituição — isso seria acusação com conta aproximada, e o projeto é
descritivo, não prescritivo.

Uso: python -m pipelines.marts.sanidade --ano 2024
"""

import argparse

from pipelines.common import parquet, storage

SEVERIDADES = ("CRITICO", "AVISO")

ANEXO_DESPESA = "DCA-Anexo I-E"
COLUNA_DESPESA = "Despesas Pagas"
ANEXO_RECEITA = "DCA-Anexo I-C"
COLUNA_RECEITA = "Receitas Brutas Realizadas"
CONTA_TOTAL = "Despesas Exceto Intraorçamentárias"
CONTA_SAUDE = "10 - Saúde"
CONTA_EDUCACAO = "12 - Educação"
CONTA_IMPOSTOS = "1.1.0.0.00.0.0 - Impostos, Taxas e Contribuições de Melhoria"
CONTA_TRANSFERENCIAS = "1.7.0.0.00.0.0 - Transferências Correntes"

PISO_EDUCACAO = 0.25
PISO_SAUDE = 0.15
# folga sobre o piso: a base aproximada é maior que a legal, então o percentual
# calculado sai menor. Só alerta quem está MUITO abaixo — evita acusar quem
# cumpre a lei e só parece não cumprir por causa do nosso denominador inflado.
FOLGA = 0.6

# Qual indicador depende de cada conta. Serve para saber se um achado chegou à
# página: valor negativo na conta de impostos só bloqueia se o indicador de
# impostos daquele município tiver sido publicado.
#
# A conta de receita do gate é a agregada (1.1.0.0) e a do indicador é a de
# nível abaixo (1.1.1.0). Quando a agregada vem negativa, a filha também vem —
# foi o que aconteceu nos 31 municípios do TO. Tratar as duas como o mesmo
# indicador é aproximação, e ela é conservadora: erra para o lado de bloquear.
CONTA_PARA_INDICADOR = {
    CONTA_SAUDE: "siconfi_despesa_saude_pc",
    CONTA_EDUCACAO: "siconfi_despesa_educacao_pc",
    CONTA_IMPOSTOS: "siconfi_receita_impostos_pc",
}

NAO_E_AFERICAO = (
    "percentual aproximado (a base legal exclui transferências que somamos) — "
    "serve para achar erro de dado, não para afirmar descumprimento de piso"
)


def _valores(con, dca: str) -> dict:
    """`{codigo: {conta: valor}}` com as contas que interessam ao gate."""
    contas = (CONTA_TOTAL, CONTA_SAUDE, CONTA_EDUCACAO, CONTA_IMPOSTOS, CONTA_TRANSFERENCIAS)
    lista = ", ".join(f"'{c}'" for c in contas)
    linhas = con.sql(f"""
        SELECT lpad(CAST(cod_ibge AS VARCHAR), 7, '0') AS codigo, conta, valor
        FROM '{dca}'
        WHERE conta IN ({lista})
          AND ((anexo = '{ANEXO_DESPESA}' AND coluna = '{COLUNA_DESPESA}')
            OR (anexo = '{ANEXO_RECEITA}' AND coluna = '{COLUNA_RECEITA}'))
    """).fetchall()

    por_municipio: dict[str, dict[str, float]] = {}
    for codigo, conta, valor in linhas:
        por_municipio.setdefault(codigo, {})[conta] = valor
    return por_municipio


def _somas_de_funcao(con, dca: str) -> dict:
    """Soma das funções de primeiro nível (`NN - Nome`), sem subfunções."""
    linhas = con.sql(f"""
        SELECT lpad(CAST(cod_ibge AS VARCHAR), 7, '0') AS codigo, sum(valor) AS soma
        FROM '{dca}'
        WHERE anexo = '{ANEXO_DESPESA}' AND coluna = '{COLUNA_DESPESA}'
          AND regexp_matches(conta, '^[0-9]{{2}} - ')
        GROUP BY 1
    """).fetchall()
    return dict(linhas)


def verificar(dca_parquet, *, publicados: dict[str, set[str]] | None = None) -> list[dict]:
    """Roda todos os checks e devolve os achados, do mais grave para o menos.

    `publicados` mapeia município → indicadores que chegaram ao mart. Serve para
    separar **achado real** de **achado que ainda bloqueia**: os 31 municípios do
    TO com receita negativa são problema verdadeiro no dado bruto, e o
    `fato_indicador` já os descarta. Bloquear a publicação por eles pararia o
    pipeline para sempre por algo que está resolvido.

    Sem esse mapa, nada é considerado mitigado — o lado seguro.
    """
    dca = parquet._posix(dca_parquet)
    con = parquet.conectar(dca)
    valores = _valores(con, dca)
    somas = _somas_de_funcao(con, dca)

    achados: list[dict] = []
    for codigo, contas in sorted(valores.items()):
        achados.extend(_checar_municipio(codigo, contas, somas.get(codigo)))

    for achado in achados:
        achado["mitigado"] = _foi_mitigado(achado, publicados)

    ordem = {s: i for i, s in enumerate(SEVERIDADES)}
    achados.sort(key=lambda a: (a["mitigado"], ordem[a["severidade"]], a["codigo_municipio_ibge"]))
    return achados


def _foi_mitigado(achado: dict, publicados: dict[str, set[str]] | None) -> bool:
    """O problema chegou à página, ou foi barrado antes?"""
    if publicados is None:
        return False

    do_municipio = publicados.get(achado["codigo_municipio_ibge"])
    if not do_municipio:
        # município sem nada publicado: nenhum achado dele chegou ao leitor
        return True

    indicador = achado.get("indicador_afetado")
    if indicador is None:
        # achado que não aponta para um indicador específico (soma das funções,
        # por exemplo) afeta a declaração inteira: só é mitigado se nada saiu
        return False
    return indicador not in do_municipio


def _checar_municipio(codigo: str, contas: dict, soma_funcoes: float | None) -> list[dict]:
    achados = []

    def registrar(check, severidade, detalhe, indicador=None):
        achados.append(
            {
                "codigo_municipio_ibge": codigo,
                "check": check,
                "severidade": severidade,
                "detalhe": detalhe,
                # qual indicador este achado afeta; None = afeta a declaração toda
                "indicador_afetado": indicador,
            }
        )

    for conta, valor in contas.items():
        if valor is not None and valor < 0:
            registrar(
                "valor_negativo",
                "CRITICO",
                f"'{conta}' vale {valor:.2f}",
                CONTA_PARA_INDICADOR.get(conta),
            )

    total = contas.get(CONTA_TOTAL)
    if total and soma_funcoes and soma_funcoes > total * 1.01:  # 1% de folga p/ arredondamento
        registrar(
            "soma_funcoes_excede_total",
            "CRITICO",
            f"funções somam {soma_funcoes:.2f}, total declarado é {total:.2f}",
        )

    base = (contas.get(CONTA_IMPOSTOS) or 0) + (contas.get(CONTA_TRANSFERENCIAS) or 0)
    if base <= 0:
        return achados  # sem base declarada não se avalia piso (regra 4)

    for conta, piso, nome in (
        (CONTA_EDUCACAO, PISO_EDUCACAO, "educacao"),
        (CONTA_SAUDE, PISO_SAUDE, "saude"),
    ):
        aplicado = contas.get(conta)
        if aplicado is None:
            continue
        proporcao = aplicado / base
        if proporcao < piso * FOLGA:
            registrar(
                f"{nome}_abaixo_do_piso",
                "AVISO",
                f"{proporcao:.1%} da base (piso legal {piso:.0%}) — {NAO_E_AFERICAO}",
            )

    return achados


def resumir(achados: list[dict]) -> dict:
    resumo = {severidade: 0 for severidade in SEVERIDADES}
    for achado in achados:
        resumo[achado["severidade"]] += 1
    resumo["total"] = len(achados)
    resumo["municipios"] = len({a["codigo_municipio_ibge"] for a in achados})
    # o que impede publicar: crítico que chegou à página
    resumo["bloqueiam"] = sum(
        1 for a in achados if a["severidade"] == "CRITICO" and not a.get("mitigado")
    )
    resumo["mitigados"] = sum(1 for a in achados if a.get("mitigado"))
    return resumo


def publicados_no_mart(fato_parquet) -> dict[str, set[str]]:
    """Quais indicadores de cada município chegaram ao mart, com valor."""
    fato = parquet._posix(fato_parquet)
    con = parquet.conectar(fato)
    linhas = con.sql(f"""
        SELECT codigo_municipio_ibge, indicador_id
        FROM '{fato}' WHERE valor IS NOT NULL
    """).fetchall()

    publicados: dict[str, set[str]] = {}
    for codigo, indicador in linhas:
        publicados.setdefault(codigo, set()).add(indicador)
    return publicados


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ano", type=int, default=2024)
    parser.add_argument("--listar", type=int, default=15, help="quantos achados exibir")
    args = parser.parse_args()

    dca = storage.uri(
        "staging", "siconfi", "dca", f"an_exercicio={args.ano}", "uf=*", "dca.parquet"
    )
    fato = storage.uri("marts", f"fato_indicador_municipio/ano={args.ano}", "fato.parquet")

    # o gate lê o staging, mas o que importa é o que chegou à página: achado já
    # barrado pelo fato é problema real do dado bruto, não motivo para travar
    publicados = publicados_no_mart(fato) if storage.existe(fato) else None
    achados = verificar(dca, publicados=publicados)
    resumo = resumir(achados)

    print(f"{resumo['total']} achados em {resumo['municipios']} municípios")
    for severidade in SEVERIDADES:
        print(f"  {severidade}: {resumo[severidade]}")
    print(f"  já barrados antes da publicação: {resumo['mitigados']}")
    print(f"  bloqueiam a publicação: {resumo['bloqueiam']}")

    for achado in achados[: args.listar]:
        marca = " [mitigado]" if achado.get("mitigado") else ""
        print(
            f"\n  [{achado['severidade']}]{marca} {achado['codigo_municipio_ibge']} "
            f"{achado['check']}\n    {achado['detalhe']}"
        )

    if resumo["bloqueiam"]:
        raise SystemExit(
            f"{resumo['bloqueiam']} achados CRÍTICOS chegaram à página — não publicar assim"
        )


if __name__ == "__main__":
    main()
