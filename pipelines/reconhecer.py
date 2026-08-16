"""Reconhecimento de fonte nova: medir antes de decidir se ela entra.

É a etapa 1 de toda integração (ver `docs/arquitetura/INTEGRAR-FONTE.md`). Ela
existe porque a pergunta cara — *"vale a pena, e o que vamos guardar?"* — tem
resposta barata: um HEAD, uma consulta de amostra, e três limiares.

Os limiares não são gosto. Saem de restrições que já morderam este projeto:

- **6 h** é o teto de um job do Actions. O PNCP nacional são 66.840 requisições:
  a 1 req/s, 18,6 h. Não cabe, e descobrir isso depois custa um job cancelado no
  meio com o manifesto pela metade.
- **10 GB** é o plano atual do R2, com ~2 GB usados. Uma fonte de 66 GB não é
  "pesada", é 6,6× tudo que temos.
- **Cópia única**: enquanto o espelho B2 não existir, guardar acervo grande
  aumenta o que se perde de uma vez.

Uso:
    python -m pipelines.reconhecer --url https://exemplo.gov.br/base.zip
    python -m pipelines.reconhecer --url ... --unidades 5570 --requisicoes 5570
"""

import argparse
from dataclasses import dataclass

TETO_RUNNER_H = 6.0  # job do Actions morre em 6 h
TETO_PLANO_GB = 10.0  # R2 no plano atual
GB = 1024**3
MB = 1024**2

# Acima disso, guardar tudo comprometeria o plano inteiro por uma fonte só.
LIMITE_INTEGRAL_GB = 2.0
# Acima disso, nem com risco alto: enquanto houver cópia única, não se triplica
# o acervo de uma vez.
LIMITE_ABSOLUTO_GB = 20.0
# Payload por unidade acima disso torna varredura nacional inviável por volume.
PAYLOAD_PESADO_BYTES = 500 * 1024

MODOS_COM_COPIA = ("integral", "recorte", "colheita")


@dataclass(frozen=True)
class Medida:
    """O que se mede de uma fonte antes de decidir. Tudo observável, nada opinado."""

    bytes_por_unidade: int
    # "unidade" é o que se pede de uma vez: um arquivo, um município, um mês
    unidades_para_cobrir_o_pais: int = 1
    requisicoes: int = 1
    throttle_s: float = 1.0
    # a única entrada de julgamento — e ela é histórica, não previsão: a fonte
    # JÁ apagou série alguma vez?
    risco_sumico: str = "baixo"
    tem_filtro: bool = False

    @property
    def total_bytes(self) -> int:
        return self.bytes_por_unidade * self.unidades_para_cobrir_o_pais

    @property
    def total_gb(self) -> float:
        return self.total_bytes / GB


def horas(medida: Medida) -> float:
    """Quanto tempo levaria cobrir o país, respeitando o throttle da fonte."""
    return medida.requisicoes * medida.throttle_s / 3600


def cabe_no_runner(medida: Medida) -> bool:
    return horas(medida) <= TETO_RUNNER_H


def _tamanho_legivel(total: int) -> str:
    for limite, unidade, divisor in ((GB, "GB", GB), (MB, "MB", MB), (1024, "KB", 1024)):
        if total >= limite:
            return f"{total / divisor:.1f} {unidade}"
    return f"{total} bytes"


def sugerir(medida: Medida) -> tuple[str, str]:
    """O modo de guarda e o motivo, na ordem em que as perguntas eliminam.

    A primeira pergunta que responde decide — e a ordem importa: risco de sumiço
    ganha de volume, porque bytes se compram e série apagada não volta.
    """
    tamanho = _tamanho_legivel(medida.total_bytes)

    # Q1 — a fonte já provou que some?
    if medida.risco_sumico == "alto":
        if medida.total_gb > LIMITE_ABSOLUTO_GB:
            return "recorte", (
                f"Fonte com risco de sumiço, mas {tamanho} é grande demais para guardar "
                f"inteira antes de existir uma segunda cópia do acervo. Recortar o que "
                f"sustenta indicador publicado e reavaliar quando o espelho existir."
            )
        return "integral", (
            f"Fonte com precedente de sumiço: {tamanho} guardados inteiros, mesmo sem "
            f"indicador publicado ainda. Bytes se compram; série apagada não volta."
        )

    # Q2 — cobrir o país cabe numa execução?
    if not cabe_no_runner(medida):
        return "recorte", (
            f"Cobrir o país levaria {horas(medida):.1f} h contra {TETO_RUNNER_H:.0f} h de "
            f"teto do runner ({medida.requisicoes} requisições). Só o recorte pactuado "
            f"é executável — e ele precisa de indicador definido antes."
        )

    # Q3 — cabe no orçamento de bytes?
    if medida.total_gb > LIMITE_ABSOLUTO_GB:
        return "recorte", (
            f"{tamanho} são {medida.total_gb / TETO_PLANO_GB:.1f}× o plano de storage "
            f"inteiro, para uma fonte que não corre risco de sumir. Guardar só a fatia "
            f"que alimenta indicador publicado."
        )

    if medida.tem_filtro and medida.bytes_por_unidade <= PAYLOAD_PESADO_BYTES:
        return "colheita", (
            f"API com filtro e resposta de {_tamanho_legivel(medida.bytes_por_unidade)} por "
            f"consulta: cobrir o país custa {tamanho}. Guardamos as respostas de cada "
            f"execução, com os parâmetros usados."
        )

    if medida.total_gb > LIMITE_INTEGRAL_GB:
        return "recorte", (
            f"{tamanho} passam do limite de {LIMITE_INTEGRAL_GB:.0f} GB para guarda "
            f"integral de fonte sem risco de sumiço. Recortar o que sustenta indicador."
        )

    return "integral", (
        f"{tamanho} cabem no plano com folga e a aquisição é uma execução só. "
        f"Guardar inteiro é mais simples e mais barato do que decidir o que descartar."
    )


def bloco_yaml(medida: Medida, *, medido_em: str, onde: str = "actions") -> str:
    """O bloco pronto para colar no `fontes.yaml`.

    A etapa termina num artefato, não numa conclusão: quem reconhece a fonte
    entrega o texto que o catálogo vai receber, já com o motivo escrito.
    """
    modo, motivo = sugerir(medida)
    linhas = [
        "guarda:",
        f"  modo: {modo}",
        f"  medido_em: {medido_em}",
        f"  volume_gb: {medida.total_gb:.3f}",
        f"  risco_sumico: {medida.risco_sumico}",
        f"  onde: {onde}",
        "  motivo: >-",
    ]
    linhas += [f"    {trecho}" for trecho in _quebrar(motivo, 84)]
    if modo == "recorte":
        linhas += [
            "  recorte:",
            "    pactuado_em: null   # sem indicador pactuado, o pipeline não colhe",
            "    municipios: []",
            "    periodo: []",
        ]
    return "\n".join(linhas) + "\n"


def _quebrar(texto: str, largura: int) -> list[str]:
    linhas, atual = [], ""
    for palavra in texto.split():
        if len(atual) + len(palavra) + 1 > largura:
            linhas.append(atual)
            atual = palavra
        else:
            atual = f"{atual} {palavra}".strip()
    if atual:
        linhas.append(atual)
    return linhas


def dica_de_falha(erro: Exception) -> str:
    """O que fazer quando a medição não passa — em uma frase, sem traceback.

    A primeira tentativa real desta ferramenta morreu em cem linhas de urllib3
    por não usar a cadeia TLS que o catálogo já declarava. Ferramenta que
    responde com stack trace é ferramenta que ninguém usa na segunda vez.
    """
    nome = type(erro).__name__
    if "SSL" in nome or "Certificate" in nome:
        return (
            "A cadeia TLS da origem não fecha. Se a fonte já está no catálogo, rode com "
            "--fonte <nome>: o `tls_ca` declarado no fontes.yaml é usado automaticamente."
        )
    if "Timeout" in nome or "ConnectionReset" in nome or "ConnectionError" in nome:
        return (
            "A conexão nem chegou a abrir. Três causas prováveis, nesta ordem: a origem "
            "recusa acesso automatizado de datacenter (rode de rede residencial), a cadeia "
            "TLS está incompleta (use --fonte <nome> para carregar o `tls_ca` do catálogo), "
            "ou a fonte está fora do ar."
        )
    return f"Falha inesperada ao medir ({nome}). Confira a URL antes de insistir."


def medir_url(url: str, *, ca: str | None = None, **campos) -> Medida:
    """Mede o que dá para medir sem baixar: um HEAD e o Content-Length.

    `ca` é o bundle da cadeia TLS quando a origem manda o certificado incompleto
    — vem do `tls_ca` da fonte no catálogo, nunca de `verify=False`.
    """
    import requests

    from pipelines.common import tls
    from pipelines.common.http import UA

    verificar = tls.bundle(ca)
    resposta = requests.head(
        url, headers={"User-Agent": UA}, timeout=30, allow_redirects=True, verify=verificar
    )
    tamanho = int(resposta.headers.get("Content-Length") or 0)
    if not tamanho:
        # servidor que não declara tamanho: pede só o primeiro pedaço para estimar
        parcial = requests.get(
            url,
            headers={"User-Agent": UA, "Range": "bytes=0-1048575"},
            timeout=60,
            stream=True,
            verify=verificar,
        )
        tamanho = int(parcial.headers.get("Content-Range", "/0").split("/")[-1]) or 0
    return Medida(bytes_por_unidade=tamanho, **campos)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="um alvo representativo da fonte")
    parser.add_argument(
        "--fonte", help="nome no fontes.yaml: carrega o `tls_ca` e o throttle já declarados"
    )
    parser.add_argument("--unidades", type=int, default=1, help="quantos alvos como esse")
    parser.add_argument("--requisicoes", type=int, default=1)
    parser.add_argument("--throttle", type=float, default=1.0)
    parser.add_argument("--risco", choices=["alto", "medio", "baixo"], default="baixo")
    parser.add_argument("--filtro", action="store_true", help="a fonte aceita filtro por município")
    parser.add_argument("--onde", choices=list(("actions", "brasil", "vps")), default="actions")
    parser.add_argument("--medido-em", default=None)
    args = parser.parse_args()

    from datetime import date

    # fonte já catalogada traz a cadeia TLS e o throttle prontos: as duas coisas
    # que fizeram esta ferramenta falhar no primeiro uso real
    ca, throttle = None, args.throttle
    if args.fonte:
        from pipelines.common.config import fonte as carregar_fonte

        config = carregar_fonte(args.fonte)
        ca = config.get("tls_ca")
        throttle = config.get("throttle_s", throttle)

    try:
        medida = medir_url(
            args.url,
            ca=ca,
            unidades_para_cobrir_o_pais=args.unidades,
            requisicoes=args.requisicoes,
            throttle_s=throttle,
            risco_sumico=args.risco,
            tem_filtro=args.filtro,
        )
    except Exception as erro:  # noqa: BLE001 — a dica é a resposta útil, não o traceback
        raise SystemExit(f"não deu para medir {args.url}\n\n{dica_de_falha(erro)}") from None

    print(f"unidade:  {_tamanho_legivel(medida.bytes_por_unidade)}")
    print(f"país:     {_tamanho_legivel(medida.total_bytes)} em {medida.requisicoes} requisições")
    print(f"execução: {horas(medida):.1f} h ({'cabe' if cabe_no_runner(medida) else 'NÃO cabe'})\n")
    print(bloco_yaml(medida, medido_em=args.medido_em or date.today().isoformat(), onde=args.onde))


if __name__ == "__main__":
    main()
