"""TDD: cliente do catálogo federal dados.gov.br.

Serve para descobrir onde um dado está quando o portal do próprio órgão fica
inacessível — caso do SNIS, cuja série histórica ficou atrás de um WAF depois
da extinção do MDR.

Contrato da API (extraído de https://dados.gov.br/v3/api-docs em 27/07/2026):
header `chave-api-dados-abertos`, base `/dados/api/publico`, recursos com os
campos `link`, `formato`, `titulo`, `nomeArquivo`, `tamanho`.
"""

import pytest

from pipelines.espelho import dadosgov

CONJUNTO = {
    "id": "abc-123",
    "titulo": "SNIS - Série Histórica",
    "nome": "snis-serie-historica",
    "descontinuado": False,
    "recursos": [
        {
            "titulo": "Água e Esgoto 1995-2023",
            "link": "https://exemplo.gov.br/agua_esgoto.csv",
            "formato": "CSV",
            "nomeArquivo": "agua_esgoto.csv",
            "tamanho": 12345,
        },
        {
            "titulo": "Aplicativo Série Histórica",
            "link": "https://app4.cidades.gov.br/serieHistorica/",
            "formato": "HTML",
            "nomeArquivo": None,
            "tamanho": None,
        },
        {
            "titulo": "Resíduos Sólidos",
            "link": "https://exemplo.gov.br/residuos.zip",
            "formato": "ZIP",
            "nomeArquivo": "residuos.zip",
            "tamanho": 999,
        },
        {"titulo": "Recurso sem link", "link": None, "formato": "CSV"},
    ],
}


@pytest.fixture(autouse=True)
def _chave(monkeypatch):
    monkeypatch.setenv("DADOS_GOV_API_KEY", "chave-de-teste")


# ---------------------------------------------------------------- normalização


def test_recursos_normaliza_os_campos_da_api():
    recursos = dadosgov.recursos(CONJUNTO)
    primeiro = recursos[0]
    assert primeiro["url"] == "https://exemplo.gov.br/agua_esgoto.csv"
    assert primeiro["formato"] == "csv"
    assert primeiro["titulo"] == "Água e Esgoto 1995-2023"


def test_recursos_descarta_entrada_sem_link():
    """Recurso sem link não é espelhável — deixá-lo passar quebraria o download."""
    assert all(recurso["url"] for recurso in dadosgov.recursos(CONJUNTO))
    assert len(dadosgov.recursos(CONJUNTO)) == 3


def test_urls_para_espelho_filtra_por_formato():
    """HTML é página de aplicativo, não dado: espelhar isso guardaria um menu."""
    urls = dadosgov.urls_para_espelho(CONJUNTO, formatos=("csv", "zip"))
    assert urls == [
        "https://exemplo.gov.br/agua_esgoto.csv",
        "https://exemplo.gov.br/residuos.zip",
    ]


def test_urls_para_espelho_sem_filtro_traz_tudo_com_link():
    assert len(dadosgov.urls_para_espelho(CONJUNTO)) == 3


# ---------------------------------------------------------------- chamadas


def test_busca_envia_chave_no_header_correto(monkeypatch):
    capturado = {}

    def buscar(url, *, headers=None, params=None):
        capturado["url"] = url
        capturado["headers"] = headers
        capturado["params"] = params
        return {"status": 200, "json": []}

    dadosgov.buscar_conjuntos("SNIS", buscar=buscar)

    assert capturado["headers"]["chave-api-dados-abertos"] == "chave-de-teste"
    assert capturado["params"]["nomeConjuntoDados"] == "SNIS"
    assert capturado["params"]["pagina"] == 1
    assert capturado["url"].endswith("/conjuntos-dados")


def test_detalhe_usa_o_id_no_caminho():
    capturado = {}

    def buscar(url, *, headers=None, params=None):
        capturado["url"] = url
        return {"status": 200, "json": CONJUNTO}

    assert dadosgov.conjunto("abc-123", buscar=buscar)["titulo"] == "SNIS - Série Histórica"
    assert capturado["url"].endswith("/conjuntos-dados/abc-123")


def test_sem_chave_no_ambiente_falha_com_instrucao(monkeypatch):
    monkeypatch.delenv("DADOS_GOV_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="DADOS_GOV_API_KEY"):
        dadosgov.buscar_conjuntos("SNIS", buscar=lambda *a, **k: {"status": 200, "json": []})


def test_401_explica_que_a_chave_e_invalida():
    def buscar(url, *, headers=None, params=None):
        return {"status": 401, "json": None}

    with pytest.raises(RuntimeError, match="chave"):
        dadosgov.buscar_conjuntos("SNIS", buscar=buscar)


def test_erro_de_servidor_e_repassado_com_status():
    def buscar(url, *, headers=None, params=None):
        return {"status": 503, "json": None}

    with pytest.raises(RuntimeError, match="503"):
        dadosgov.buscar_conjuntos("SNIS", buscar=buscar)


def test_conjunto_descontinuado_e_sinalizado():
    """Conjunto marcado como descontinuado é exatamente o que corre risco de sumir."""
    assert dadosgov.descontinuado({**CONJUNTO, "descontinuado": True}) is True
    assert dadosgov.descontinuado(CONJUNTO) is False
