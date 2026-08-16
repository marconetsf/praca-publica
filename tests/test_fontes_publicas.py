"""A ficha pública de cada fonte — o que o órgão publica e o que conseguimos dele.

A página `/fontes` é a contrapartida honesta de cobrar transparência dos
municípios: se medimos quanto cada ente informou, precisamos dizer com a mesma
clareza o que **nós** conseguimos obter, o que está guardado e o que está
bloqueado — e por quê.

Por isso os testes daqui cobram três coisas do arquivo real de configuração:

1. **Nenhuma fonte fica de fora.** Fonte no `fontes.yaml` sem `ficha:` sumiria da
   página pública sem ninguém perceber — exatamente o erro dos 7 municípios
   órfãos, agora na camada do catálogo.
2. **A situação é derivada, não declarada.** "Está no site", "guardado",
   "bloqueado" saem dos fatos (indicador publicado, manifesto do espelho, motivo
   registrado), para que a ficha não envelheça mentindo.
3. **O texto é legível.** A ficha é para o cidadão, não para quem já conhece a
   sigla do órgão.
"""

import json

import pytest

from pipelines.common.config import fontes as fontes_reais
from pipelines.marts import fontes as mart_fontes
from pipelines.marts import legibilidade

PISO_FACIL = 50  # mesmo piso do resto do texto público (ver test_legibilidade)

FONTES_FALSAS = {
    "tesouro": {
        "api_base": "https://exemplo.gov.br/api",
        "sonda": {"url": "https://exemplo.gov.br/api/entes"},
        "ficha": {
            "orgao": "Tesouro Nacional",
            "publica": "As contas que cada prefeitura declara ao governo federal.",
            "atualizacao": "uma vez por ano",
            "pagina_oficial": "https://exemplo.gov.br",
        },
    },
    "escolas": {
        "espelho": ["https://exemplo.gov.br/censo_2024.zip"],
        "ficha": {
            "orgao": "Instituto de Educação",
            "publica": "Os dados de todas as escolas do país.",
            "atualizacao": "uma vez por ano",
            "pagina_oficial": "https://exemplo.gov.br/escolas",
            "nao_vigiada": "o servidor recusa conexão de fora do Brasil",
        },
    },
    "saneamento": {
        "ficha": {
            "orgao": "Ministério das Cidades",
            "publica": "Quanta gente tem água tratada e esgoto em cada cidade.",
            "atualizacao": "encerrada em 2023",
            "pagina_oficial": "https://exemplo.gov.br/saneamento",
            "nao_vigiada": "não há endereço que responda",
            "bloqueio": "O endereço do arquivo saiu do ar e não foi republicado.",
        },
    },
}


class IndicadorFalso:
    def __init__(self, fonte_id, nome):
        self.fonte_id = fonte_id
        self.nome_exibicao = nome


INDICADORES_FALSOS = (IndicadorFalso("tesouro", "Gasto com saúde por morador"),)


def montar(**kwargs):
    kwargs.setdefault("fontes", FONTES_FALSAS)
    kwargs.setdefault("indicadores", INDICADORES_FALSOS)
    return {f["id"]: f for f in mart_fontes.montar(**kwargs)}


# ----------------------------------------------------- situação derivada


def test_fonte_que_alimenta_indicador_esta_no_site():
    assert montar()["tesouro"]["situacao"] == "no_site"
    assert montar()["tesouro"]["indicadores"] == ["Gasto com saúde por morador"]


def test_fonte_so_espelhada_aparece_como_guardada():
    manifesto = {
        "espelho/escolas/censo_2024.zip": {
            "registrado_em": "2026-07-26T10:00:00+00:00",
            "completo": True,
            "bytes": 1000,
        }
    }
    ficha = montar(manifesto=manifesto)["escolas"]
    assert ficha["situacao"] == "guardado"
    assert ficha["espelho"]["guardados"] == 1
    assert ficha["espelho"]["bytes"] == 1000
    assert ficha["espelho"]["ultimo_em"] == "2026-07-26"


def test_espelho_declarado_sem_arquivo_guardado_ainda_e_planejado():
    """Declarar alvo não é ter o acervo. A página não pode prometer o que não guardou."""
    ficha = montar()["escolas"]
    assert ficha["situacao"] == "planejado"
    assert ficha["espelho"]["declarados"] == 1
    assert ficha["espelho"]["guardados"] == 0


def test_espelho_de_terceiro_nao_conta_como_alvo_declarado():
    """`espelho:` string é fallback de terceiros (a Receita tem um), não lista de alvos.

    Contar `len()` de string devolveu 50 "arquivos declarados" para o CNPJ — o
    número de caracteres da URL. Só lista é alvo de resgate.
    """
    fontes = {
        "receita": {
            "espelho": "https://espelho-de-terceiro.example.com/",
            "sonda": {"url": "https://exemplo.gov.br/cnpj"},
            "ficha": {
                "orgao": "Receita Federal",
                "publica": "O cadastro das empresas do país.",
                "atualizacao": "Uma vez por mês.",
                "pagina_oficial": "https://exemplo.gov.br",
            },
        }
    }
    ficha = mart_fontes.montar(fontes=fontes, indicadores=())[0]
    assert ficha["espelho"] is None
    assert ficha["situacao"] == "planejado"


def test_fonte_com_bloqueio_declarado_aparece_como_bloqueada():
    ficha = montar()["saneamento"]
    assert ficha["situacao"] == "bloqueado"
    assert ficha["bloqueio"].startswith("O endereço")


def test_ordem_poe_o_que_esta_no_site_primeiro():
    ordem = [
        f["id"] for f in mart_fontes.montar(fontes=FONTES_FALSAS, indicadores=INDICADORES_FALSOS)
    ]
    assert ordem[0] == "tesouro"
    assert ordem[-1] == "saneamento"  # bloqueado por último


# ----------------------------------------------------- vigilância


def test_vigilancia_sai_do_estado_do_watcher():
    estado = {"tesouro": {"ok": True, "visto_em": "2026-08-15T06:00:00+00:00"}}
    vigilancia = montar(estado=estado)["tesouro"]["vigilancia"]
    assert vigilancia["vigiada"] is True
    assert vigilancia["situacao"] == "responde"
    assert vigilancia["visto_em"] == "2026-08-15"


def test_fonte_que_parou_de_responder_diz_isso():
    estado = {"tesouro": {"ok": False, "visto_em": "2026-08-15T06:00:00+00:00"}}
    assert montar(estado=estado)["tesouro"]["vigilancia"]["situacao"] == "sem_resposta"


def test_nao_verificavel_daqui_nao_vira_fonte_caida():
    """Bloqueio de datacenter é limitação nossa, não queda da fonte."""
    estado = {
        "tesouro": {
            "nao_verificavel": True,
            "motivo": "fonte recusa conexão de datacenter",
            "visto_em": "2026-08-15T06:00:00+00:00",
        }
    }
    vigilancia = montar(estado=estado)["tesouro"]["vigilancia"]
    assert vigilancia["situacao"] == "nao_verificavel"
    # o motivo interno do watcher é jargão; a página recebe a versão do leitor
    assert "datacenter" not in vigilancia["observacao"]
    assert "pode estar no ar" in vigilancia["observacao"]


def test_falha_de_rede_nao_vira_acusacao_ao_orgao():
    """Timeout na nossa sonda não prova que o site do órgão caiu.

    Quatro fontes (IBGE, PNCP, CNJ, Receita) dão ConnectTimeout no runner e
    respondem normalmente de rede brasileira. Publicar "não respondeu" sem essa
    ressalva seria acusar o órgão de algo que o dado não sustenta — e o rastro
    da exceção do Python não é texto para o cidadão.
    """
    estado = {
        "tesouro": {
            "ok": False,
            "erro": "ConnectTimeout: HTTPSConnectionPool(host='x.gov.br', port=443)",
            "visto_em": "2026-08-15T06:00:00+00:00",
        }
    }
    observacao = montar(estado=estado)["tesouro"]["vigilancia"]["observacao"]
    assert "HTTPSConnectionPool" not in observacao
    assert "bloqueio" in observacao.lower()


def test_ficha_diz_ha_quantas_checagens_a_fonte_nao_responde():
    """Uma falha isolada é rotina em servidor público; cinco seguidas são sinal.

    Em 15/08/2026 quatro fontes falharam **na mesma** execução e responderam
    normalmente de outra rede — foi a saída do runner, não elas. Sem o número de
    falhas seguidas, a página trataria esse episódio como fonte fora do ar.
    """
    estado = {
        "tesouro": {"ok": False, "falhas_consecutivas": 4, "visto_em": "2026-08-15T06:00:00Z"}
    }
    assert montar(estado=estado)["tesouro"]["vigilancia"]["falhas_seguidas"] == 4


def test_erro_http_diz_o_codigo_sem_jargao():
    estado = {"tesouro": {"ok": False, "status": 500, "visto_em": "2026-08-15T06:00:00+00:00"}}
    assert "500" in montar(estado=estado)["tesouro"]["vigilancia"]["observacao"]


def test_fonte_sem_sonda_explica_por_que_nao_e_vigiada():
    vigilancia = montar()["escolas"]["vigilancia"]
    assert vigilancia["vigiada"] is False
    assert vigilancia["observacao"] == "o servidor recusa conexão de fora do Brasil"


# ----------------------------------------------------- geração do JSON


def test_gerar_escreve_o_json_que_o_site_consome(tmp_path):
    total = mart_fontes.gerar(
        tmp_path, fontes=FONTES_FALSAS, indicadores=INDICADORES_FALSOS, coletado_em="2026-08-16"
    )
    assert total == 3
    dados = json.loads((tmp_path / "fontes.json").read_text(encoding="utf-8"))
    assert dados["gerado_em"] == "2026-08-16"
    assert [f["id"] for f in dados["fontes"]][0] == "tesouro"
    assert dados["resumo"]["no_site"] == 1


# ----------------------------------------------------- o catálogo real


@pytest.mark.parametrize("nome", sorted(fontes_reais()))
def test_toda_fonte_do_catalogo_tem_ficha_publica(nome):
    """Fonte sem ficha some da página — e some sem ninguém perceber."""
    ficha = (fontes_reais()[nome] or {}).get("ficha")
    assert ficha, f"'{nome}' não tem ficha: ela nunca apareceria em /fontes"
    for campo in mart_fontes.CAMPOS_OBRIGATORIOS:
        assert ficha.get(campo), f"'{nome}' não declara '{campo}' na ficha"


@pytest.mark.parametrize("nome", sorted(fontes_reais()))
def test_fonte_sem_sonda_declara_por_que_nao_e_vigiada(nome):
    config = fontes_reais()[nome] or {}
    if config.get("sonda", {}).get("url"):
        return
    assert (config.get("ficha") or {}).get("nao_vigiada"), (
        f"'{nome}' não é vigiada pelo watcher e não diz o motivo ao leitor"
    )


@pytest.mark.parametrize("nome", sorted(fontes_reais()))
def test_texto_da_ficha_e_facil_de_ler(nome):
    ficha = (fontes_reais()[nome] or {}).get("ficha") or {}
    for campo in ("publica", "bloqueio"):
        texto = ficha.get(campo)
        if not texto or not legibilidade.mensuravel(texto):
            continue
        nota = legibilidade.indice(texto)
        assert nota >= PISO_FACIL, (
            f"{nome}.{campo}: nota {nota:.0f} — {legibilidade.diagnosticar(texto)}"
        )


def test_pagina_oficial_e_endereco_publico():
    for nome, config in fontes_reais().items():
        url = (config or {}).get("ficha", {}).get("pagina_oficial", "")
        assert url.startswith("https://"), f"'{nome}': página oficial precisa ser https"
