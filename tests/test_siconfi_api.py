"""TDD: paginação da API do SICONFI como função pura (injetando o buscador)."""

from pipelines.siconfi.api import paginar


def _buscador_fake(paginas):
    """Simula a API: devolve páginas na ordem, registrando os offsets pedidos."""
    offsets = []

    def buscar(endpoint, params):
        offsets.append(params.get("offset", 0))
        return paginas[len(offsets) - 1]

    return buscar, offsets


def test_pagina_unica():
    buscar, offsets = _buscador_fake(
        [{"items": [{"a": 1}, {"a": 2}], "hasMore": False, "limit": 100}]
    )
    itens = paginar("entes", buscar=buscar)
    assert itens == [{"a": 1}, {"a": 2}]
    assert offsets == [0]


def test_multiplas_paginas_avancando_offset_pelo_limit():
    buscar, offsets = _buscador_fake(
        [
            {"items": [{"a": 1}, {"a": 2}], "hasMore": True, "limit": 2},
            {"items": [{"a": 3}, {"a": 4}], "hasMore": True, "limit": 2},
            {"items": [{"a": 5}], "hasMore": False, "limit": 2},
        ]
    )
    itens = paginar("dca", {"an_exercicio": 2024}, buscar=buscar)
    assert [i["a"] for i in itens] == [1, 2, 3, 4, 5]
    assert offsets == [0, 2, 4]


def test_parametros_originais_sao_preservados():
    capturados = []

    def buscar(endpoint, params):
        capturados.append(dict(params))
        return {"items": [], "hasMore": False, "limit": 100}

    paginar("dca", {"an_exercicio": 2024, "id_ente": 2611101}, buscar=buscar)
    assert capturados[0]["an_exercicio"] == 2024
    assert capturados[0]["id_ente"] == 2611101


def test_resposta_vazia_devolve_lista_vazia():
    buscar, _ = _buscador_fake([{"items": [], "hasMore": False, "limit": 100}])
    assert paginar("dca", buscar=buscar) == []
