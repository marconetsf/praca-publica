"""fontes.json — a ficha pública de cada fonte de dados (rota `/fontes`).

Cobramos transparência dos municípios; a contrapartida é dizer, com a mesma
clareza, o que **nós** conseguimos obter de cada órgão. Cada ficha responde
quatro perguntas do leitor:

- o que este órgão publica, em português;
- de quanto em quanto tempo, e com que atraso;
- o que já está no site, o que está guardado e o que ainda não;
- se algo está bloqueado, por quê.

**A situação é derivada de fatos, nunca declarada.** "Está no site" sai da lista
de indicadores publicados; "guardado" sai do manifesto do espelho; a vigilância
sai do estado do watcher. Um campo `situacao: em_uso` escrito à mão no YAML
envelheceria mentindo — e a página que existe para ser honesta seria a primeira
a mentir.

O que o YAML declara é só o que nenhum fato revela: o nome do órgão, a frase que
explica o que ele publica, o endereço oficial e o motivo de um bloqueio.

Uso: python -m pipelines.marts.fontes
"""

import argparse
import json
from datetime import date
from pathlib import Path

from pipelines.common import storage
from pipelines.common.config import fontes as carregar_fontes

# Sem estes campos a ficha não informa nada ao leitor — cobrado em teste sobre o
# arquivo real, para que fonte nova não entre muda no catálogo.
CAMPOS_OBRIGATORIOS = ("orgao", "publica", "atualizacao", "pagina_oficial")

# Ordem de exibição. O leitor procura primeiro o que ele consegue ver hoje; o
# que está bloqueado fica no fim, mas fica — some da página seria esconder.
ORDEM_SITUACAO = ("no_site", "guardado", "planejado", "bloqueado")

PREFIXO_ESPELHO = "espelho/"


def _dia(carimbo: str | None) -> str | None:
    """Corta o carimbo ISO no dia: hora e fuso não interessam ao leitor."""
    return carimbo.split("T")[0] if carimbo else None


def _espelho(nome: str, config: dict, manifesto: dict) -> dict | None:
    """Quanto do acervo desta fonte já está guardado conosco.

    `declarados` são os alvos listados no YAML; `guardados` são os que o
    manifesto confirma ter baixado, com hash. A diferença entre os dois é
    justamente o que ainda não foi resgatado — e é ela que impede a página de
    dizer "guardado" para uma lista de intenções.
    """
    # `espelho:` string é outra coisa: o fallback de terceiros da Receita. Contar
    # o len() dela devolveria "50 arquivos declarados" — o tamanho da URL.
    alvos = config.get("espelho")
    declarados = len(alvos) if isinstance(alvos, list) else 0
    prefixo = f"{PREFIXO_ESPELHO}{nome}/"
    registros = [
        registro
        for chave, registro in manifesto.items()
        if chave.startswith(prefixo) and registro.get("completo", True)
    ]
    if not declarados and not registros:
        return None
    return {
        "declarados": declarados,
        "guardados": len(registros),
        "bytes": sum(r.get("bytes") or 0 for r in registros),
        "ultimo_em": _dia(max((r.get("registrado_em") or "" for r in registros), default="")),
    }


# Falha em que a conexão nem chegou a abrir. Não diz nada sobre o site do órgão:
# quatro fontes que dão timeout na nossa sonda respondem normalmente de rede
# brasileira. O rastro da exceção do Python jamais vai para a página.
ERROS_DE_CONEXAO = ("ConnectTimeout", "ConnectionError", "SSLError", "ReadTimeout", "Timeout")

FALHA_DE_CONEXAO = (
    "A conexão nem chegou a abrir. Pode ser bloqueio ao nosso acesso automático, "
    "e não queda do site do órgão."
)

NAO_VERIFICAVEL = (
    "O servidor recusa conexão vinda das máquinas onde a checagem roda. "
    "A fonte pode estar no ar normalmente."
)


def _motivo_da_falha(registro: dict) -> str | None:
    """Por que a sonda não passou, em português e sem acusar o órgão."""
    erro = registro.get("erro") or ""
    if any(erro.startswith(tipo) for tipo in ERROS_DE_CONEXAO):
        return FALHA_DE_CONEXAO
    status = registro.get("status")
    if status:
        return f"O endereço respondeu com erro {status}."
    return FALHA_DE_CONEXAO if erro else None


def _vigilancia(nome: str, config: dict, ficha: dict, estado: dict) -> dict:
    """O que o watcher sabe sobre esta fonte, traduzido para o leitor.

    Três estados diferentes que costumam ser confundidos: a fonte respondeu, a
    fonte não respondeu, e *nós* não conseguimos verificar daqui. O terceiro é
    limitação nossa (o INEP recusa conexão de datacenter) e apresentá-lo como
    queda da fonte seria acusar o órgão de algo que ele não fez.
    """
    vazio = {"situacao": None, "visto_em": None, "observacao": None, "falhas_seguidas": 0}

    if not (config.get("sonda") or {}).get("url"):
        return {**vazio, "vigiada": False, "observacao": ficha.get("nao_vigiada")}

    registro = estado.get(nome) or {}
    if not registro:
        return {**vazio, "vigiada": True}

    if registro.get("nao_verificavel"):
        # o motivo do watcher é interno ("recusa conexão de datacenter; sondar de
        # rede brasileira") — a página recebe a versão que o leitor entende
        situacao, observacao = "nao_verificavel", NAO_VERIFICAVEL
    elif registro.get("ok"):
        situacao, observacao = "responde", None
    else:
        situacao, observacao = "sem_resposta", _motivo_da_falha(registro)

    return {
        "vigiada": True,
        "situacao": situacao,
        "visto_em": _dia(registro.get("visto_em")),
        "observacao": observacao,
        # uma queda isolada é rotina em servidor público; a página só deve soar
        # o alarme quando a fonte não responde há várias checagens seguidas
        "falhas_seguidas": registro.get("falhas_consecutivas", 0),
    }


def _situacao(indicadores: list[str], espelho: dict | None, ficha: dict) -> str:
    if indicadores:
        return "no_site"
    if espelho and espelho["guardados"]:
        return "guardado"
    if ficha.get("bloqueio"):
        return "bloqueado"
    return "planejado"


def montar(
    *,
    fontes: dict | None = None,
    estado: dict | None = None,
    manifesto: dict | None = None,
    indicadores=None,
) -> list[dict]:
    """Uma ficha por fonte do catálogo, na ordem em que a página as mostra."""
    fontes = carregar_fontes() if fontes is None else fontes
    estado = estado or {}
    manifesto = manifesto or {}
    if indicadores is None:
        from pipelines.marts.fato_indicador import INDICADORES

        indicadores = INDICADORES

    publicados: dict[str, list[str]] = {}
    for indicador in indicadores:
        publicados.setdefault(indicador.fonte_id, []).append(indicador.nome_exibicao)

    fichas = []
    for nome, config in sorted(fontes.items()):
        config = config or {}
        ficha = config.get("ficha") or {}
        no_site = publicados.get(nome, [])
        espelho = _espelho(nome, config, manifesto)
        fichas.append(
            {
                "id": nome,
                "orgao": ficha.get("orgao"),
                "publica": ficha.get("publica"),
                "atualizacao": ficha.get("atualizacao"),
                "pagina_oficial": ficha.get("pagina_oficial"),
                "situacao": _situacao(no_site, espelho, ficha),
                "indicadores": no_site,
                "espelho": espelho,
                "vigilancia": _vigilancia(nome, config, ficha, estado),
                "bloqueio": ficha.get("bloqueio"),
            }
        )

    fichas.sort(key=lambda f: (ORDEM_SITUACAO.index(f["situacao"]), f["orgao"] or f["id"]))
    return fichas


def _ler_json(caminho: str) -> dict:
    """Lê um JSON do catálogo; ausente vira vazio — a página degrada, não quebra."""
    if not storage.existe(caminho):
        return {}
    return json.loads(storage.ler_bytes(caminho).decode("utf-8"))


def gerar(
    destino,
    *,
    fontes: dict | None = None,
    estado: dict | None = None,
    manifesto: dict | None = None,
    indicadores=None,
    coletado_em: str | None = None,
) -> int:
    """Escreve `fontes.json` no destino e devolve quantas fichas."""
    fichas = montar(fontes=fontes, estado=estado, manifesto=manifesto, indicadores=indicadores)
    resumo = {situacao: 0 for situacao in ORDEM_SITUACAO}
    for ficha in fichas:
        resumo[ficha["situacao"]] += 1

    pasta = Path(destino)
    pasta.mkdir(parents=True, exist_ok=True)
    conteudo = {
        "gerado_em": coletado_em or date.today().isoformat(),
        "resumo": resumo,
        "fontes": fichas,
    }
    (pasta / "fontes.json").write_text(
        json.dumps(conteudo, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return len(fichas)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destino", default="site/public/dados")
    args = parser.parse_args()

    total = gerar(
        args.destino,
        estado=_ler_json(storage.uri("catalog", "watcher_state.json")),
        manifesto=_ler_json(storage.uri("catalog", "manifest.json")),
    )
    print(f"{total} fontes em {args.destino}/fontes.json")


if __name__ == "__main__":
    main()
