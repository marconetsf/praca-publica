"""Cliente do catálogo federal dados.gov.br.

Serve para descobrir onde um dado está quando o portal do próprio órgão fica
inacessível. Caso concreto: a série histórica do SNIS: `app4.mdr.gov.br` morreu
com a extinção do MDR e os domínios `cidades.gov.br` respondem 403 de appliance
(ver config/fontes.yaml → snis). O catálogo federal é a via institucional que
sobra — e, ao contrário do WAF, ela tem contrato documentado.

Contrato (de https://dados.gov.br/v3/api-docs, lido em 27/07/2026):
- autenticação por header `chave-api-dados-abertos` (chave gratuita, criada em
  "Minha Conta" no portal); guardar em DADOS_GOV_API_KEY, nunca no YAML
- `GET /dados/api/publico/conjuntos-dados?nomeConjuntoDados=&pagina=`
- `GET /dados/api/publico/conjuntos-dados/{id}` devolve `recursos[]` com
  `link`, `formato`, `titulo`, `nomeArquivo`, `tamanho`

Uso:
    python -m pipelines.espelho.dadosgov --buscar SNIS
    python -m pipelines.espelho.dadosgov --conjunto <id>
"""

import argparse
import os

import requests

from pipelines.common.http import UA

BASE = "https://dados.gov.br/dados/api/publico"
CABECALHO_CHAVE = "chave-api-dados-abertos"
TIMEOUT = 60


def _chave() -> str:
    chave = os.environ.get("DADOS_GOV_API_KEY")
    if not chave:
        raise RuntimeError(
            "DADOS_GOV_API_KEY não está no ambiente. Crie a chave gratuita em "
            "dados.gov.br (Minha Conta → chave de API) e coloque no .env"
        )
    return chave


def _buscar_real(url: str, *, headers: dict | None = None, params: dict | None = None) -> dict:
    resposta = requests.get(url, headers=headers, params=params, timeout=TIMEOUT)
    corpo = None
    if resposta.status_code == 200:
        corpo = resposta.json()
    return {"status": resposta.status_code, "json": corpo}


def _pedir(caminho: str, *, params: dict | None = None, buscar=None):
    buscar = buscar or _buscar_real
    cabecalhos = {"User-Agent": UA, "Accept": "application/json", CABECALHO_CHAVE: _chave()}
    resposta = buscar(f"{BASE}{caminho}", headers=cabecalhos, params=params)

    status = resposta["status"]
    if status == 401 or status == 403:
        raise RuntimeError(
            f"dados.gov.br recusou a chave (HTTP {status}) — confira DADOS_GOV_API_KEY"
        )
    if status != 200:
        raise RuntimeError(f"dados.gov.br respondeu HTTP {status} em {caminho}")
    return resposta["json"]


def buscar_conjuntos(nome: str, *, pagina: int = 1, buscar=None) -> list[dict]:
    return _pedir(
        "/conjuntos-dados", params={"nomeConjuntoDados": nome, "pagina": pagina}, buscar=buscar
    )


def conjunto(id_conjunto: str, *, buscar=None) -> dict:
    return _pedir(f"/conjuntos-dados/{id_conjunto}", buscar=buscar)


def recursos(conjunto_dados: dict) -> list[dict]:
    """Normaliza os recursos, descartando os que não têm link para baixar."""
    normalizados = []
    for recurso in conjunto_dados.get("recursos") or []:
        link = recurso.get("link")
        if not link:
            continue
        normalizados.append(
            {
                "url": link,
                "formato": (recurso.get("formato") or "").lower(),
                "titulo": recurso.get("titulo"),
                "nome_arquivo": recurso.get("nomeArquivo"),
                "tamanho": recurso.get("tamanho"),
            }
        )
    return normalizados


def urls_para_espelho(conjunto_dados: dict, formatos: tuple[str, ...] | None = None) -> list[str]:
    """URLs espelháveis; `formatos` filtra o que é dado do que é página."""
    return [
        recurso["url"]
        for recurso in recursos(conjunto_dados)
        if formatos is None or recurso["formato"] in formatos
    ]


def descontinuado(conjunto_dados: dict) -> bool:
    return bool(conjunto_dados.get("descontinuado"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--buscar", help="Procura conjuntos pelo nome (ex.: SNIS)")
    grupo.add_argument("--conjunto", help="Detalha um conjunto pelo id e lista os recursos")
    args = parser.parse_args()

    if args.buscar:
        achados = buscar_conjuntos(args.buscar)
        print(f"{len(achados)} conjunto(s) para '{args.buscar}':\n")
        for item in achados:
            print(f"  {item.get('id')}  {item.get('title') or item.get('nome')}")
            print(f"    organização: {item.get('nomeOrganizacao')}")
            print(f"    dados atualizados em: {item.get('ultimaAtualizacaoDados')}")
        return

    dados = conjunto(args.conjunto)
    aviso = "  [DESCONTINUADO]" if descontinuado(dados) else ""
    print(f"{dados.get('titulo')}{aviso}")
    print(f"organização: {dados.get('organizacao')}")
    print(
        f"cobertura: {dados.get('coberturaTemporalInicio')} a {dados.get('coberturaTemporalFim')}"
    )
    lista = recursos(dados)
    print(f"\n{len(lista)} recurso(s) com link:")
    for recurso in lista:
        tamanho = f"{recurso['tamanho']} B" if recurso["tamanho"] else "tamanho não informado"
        print(f"  [{recurso['formato'] or '?'}] {recurso['titulo']} ({tamanho})")
        print(f"      {recurso['url']}")


if __name__ == "__main__":
    main()
