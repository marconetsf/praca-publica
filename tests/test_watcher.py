"""TDD: watcher v1 — disponibilidade e mudança de conteúdo das fontes.

Regras da OPERACAO §1: HEAD (GET Range onde HEAD é bloqueado), ≠2xx/3xx por
2 dias = alerta, ETag/Last-Modified/Content-Length contra o estado anterior.

A sonda é declarada por fonte no fontes.yaml: sondar `api_base` cru gera falso
positivo em massa (401 de quem exige token, 404 de quem é só prefixo de URL) —
e watcher que grita alarme falso todo dia faz o operador desligar o canal.
"""

import json

import pytest

from pipelines.common import storage
from pipelines.watcher import sonda


class RespostaFake:
    def __init__(self, status_code=200, headers=None):
        self.status_code = status_code
        self.headers = headers or {}


def _ok(etag="abc", tamanho="100"):
    return {
        "status": 200,
        "ok": True,
        "etag": etag,
        "last_modified": None,
        "content_length": tamanho,
        "erro": None,
    }


def _falha(status=503):
    return {
        "status": status,
        "ok": False,
        "etag": None,
        "last_modified": None,
        "content_length": None,
        "erro": None,
    }


# ---------------------------------------------------------------- alvos


def test_alvo_vem_da_chave_sonda_da_fonte():
    fontes = {"siconfi": {"api_base": "https://x", "sonda": {"url": "https://x/entes?a=1"}}}
    assert sonda.alvos_de_sonda(fontes)["siconfi"]["url"] == "https://x/entes?a=1"


def test_fonte_sem_sonda_nao_e_vigiada():
    """DataSUS e RAIS só existem por FTP: sondá-los por HTTP daria alarme falso diário."""
    fontes = {"datasus": {"ftp": "ftp://ftp.datasus.gov.br/"}, "x": {"sonda": {"url": "https://x"}}}
    assert list(sonda.alvos_de_sonda(fontes)) == ["x"]


def test_status_ok_padrao_e_2xx_3xx():
    fontes = {"x": {"sonda": {"url": "https://x"}}}
    assert sonda.alvos_de_sonda(fontes)["x"]["status_ok"] == []


def test_deteccao_de_mudanca_ligada_por_padrao():
    fontes = {"x": {"sonda": {"url": "https://x"}}}
    assert sonda.alvos_de_sonda(fontes)["x"]["detectar_mudanca"] is True


def test_fonte_pode_desligar_deteccao_de_mudanca():
    """Nextcloud da Receita e CKAN do TSE mudam de tamanho a cada request."""
    fontes = {"x": {"sonda": {"url": "https://x", "detectar_mudanca": False}}}
    assert sonda.alvos_de_sonda(fontes)["x"]["detectar_mudanca"] is False


def test_sem_deteccao_de_mudanca_a_assinatura_nova_nao_alerta():
    eventos = sonda.comparar("x", _ok(etag="v1"), _ok(etag="v2"), detectar_mudanca=False)
    assert eventos == []


def test_sem_deteccao_de_mudanca_a_indisponibilidade_ainda_alerta():
    """Desligar a detecção de conteúdo não pode cegar o watcher para queda."""
    anterior = {**_falha(), "falhas_consecutivas": 1}
    eventos = sonda.comparar("x", anterior, _falha(), detectar_mudanca=False)
    assert [severidade for severidade, _ in eventos] == ["AVISO"]


def test_fontes_instaveis_do_catalogo_estao_marcadas():
    from pipelines.common.config import fontes

    alvos = sonda.alvos_de_sonda(fontes())
    assert alvos["cnpj_rfb"]["detectar_mudanca"] is False
    assert alvos["tse"]["detectar_mudanca"] is False
    assert alvos["siconfi"]["detectar_mudanca"] is True


def test_alvo_herda_o_tls_ca_da_fonte():
    """Sem isso o watcher acusaria o INEP de caído por causa da cadeia TLS incompleta."""
    fontes = {"inep": {"tls_ca": "config/ca/inep.pem", "sonda": {"url": "https://inep/a.zip"}}}
    assert sonda.alvos_de_sonda(fontes)["inep"]["ca"] == "config/ca/inep.pem"


def test_alvo_sem_tls_ca_fica_com_none():
    fontes = {"x": {"sonda": {"url": "https://x"}}}
    assert sonda.alvos_de_sonda(fontes)["x"]["ca"] is None


def test_status_ok_declarado_e_preservado():
    """401 no Portal da Transparência significa 'de pé, exigindo token'."""
    fontes = {"pt": {"sonda": {"url": "https://x", "status_ok": [200, 401]}}}
    assert sonda.alvos_de_sonda(fontes)["pt"]["status_ok"] == [200, 401]


def test_catalogo_real_tem_sondas_para_as_fontes_http():
    from pipelines.common.config import fontes

    alvos = sonda.alvos_de_sonda(fontes())
    assert {"siconfi", "ibge", "pncp", "tse", "bcb"} <= set(alvos)
    assert all(alvo["url"].startswith("https://") for alvo in alvos.values())


# ---------------------------------------------------------------- sondar


def test_sondar_usa_head_e_extrai_os_cabecalhos():
    chamadas = []

    def requisitar(metodo, url, **kwargs):
        chamadas.append(metodo)
        return RespostaFake(200, {"ETag": 'W/"xyz"', "Content-Length": "42"})

    resultado = sonda.sondar("https://exemplo", requisitar=requisitar)

    assert chamadas == ["HEAD"]
    assert resultado["ok"] is True
    assert resultado["etag"] == 'W/"xyz"'
    assert resultado["content_length"] == "42"


def test_sondar_cai_para_get_quando_head_e_bloqueado():
    """Vários servidores respondem 403/405 a HEAD mas aceitam GET com Range."""
    chamadas = []

    def requisitar(metodo, url, **kwargs):
        chamadas.append((metodo, kwargs.get("headers", {}).get("Range")))
        if metodo == "HEAD":
            return RespostaFake(405)
        return RespostaFake(206, {"ETag": "zzz"})

    resultado = sonda.sondar("https://exemplo", requisitar=requisitar)

    assert chamadas == [("HEAD", None), ("GET", "bytes=0-0")]
    assert resultado["ok"] is True


def test_sondar_respeita_status_ok_declarado():
    resultado = sonda.sondar(
        "https://x", status_ok=[200, 401], requisitar=lambda *a, **k: RespostaFake(401)
    )
    assert resultado["status"] == 401
    assert resultado["ok"] is True


def test_status_fora_da_lista_declarada_e_indisponivel():
    resultado = sonda.sondar(
        "https://x", status_ok=[200, 401], requisitar=lambda *a, **k: RespostaFake(500)
    )
    assert resultado["ok"] is False


def test_sondar_registra_erro_de_rede_sem_estourar():
    def requisitar(metodo, url, **kwargs):
        raise TimeoutError("servidor não respondeu")

    resultado = sonda.sondar("https://exemplo", requisitar=requisitar)

    assert resultado["ok"] is False
    assert "TimeoutError" in resultado["erro"]


# ---------------------------------------------------------------- comparar


def test_primeira_sondagem_nao_alerta():
    assert sonda.comparar("siconfi", None, _ok()) == []


def test_etag_igual_nao_alerta():
    assert sonda.comparar("x", _ok(etag="abc"), _ok(etag="abc")) == []


def test_etag_diferente_avisa_dado_novo():
    eventos = sonda.comparar("siconfi", _ok(etag="abc"), _ok(etag="def"))
    assert len(eventos) == 1
    severidade, mensagem = eventos[0]
    assert severidade == "AVISO"
    assert "siconfi" in mensagem


def test_content_length_diferente_avisa_mesmo_sem_etag():
    anterior = {**_ok(etag=None, tamanho="10")}
    atual = {**_ok(etag=None, tamanho="20")}
    assert sonda.comparar("x", anterior, atual) != []


def test_uma_falha_isolada_nao_alerta():
    """Instabilidade de minuto em servidor público é rotina; alertar seria ruído."""
    anterior = {**_ok(), "falhas_consecutivas": 0}
    assert sonda.comparar("x", anterior, _falha()) == []


def test_segunda_falha_consecutiva_alerta():
    anterior = {**_falha(), "falhas_consecutivas": 1}
    eventos = sonda.comparar("ibge", anterior, _falha())
    assert [severidade for severidade, _ in eventos] == ["AVISO"]
    assert "ibge" in eventos[0][1]


def test_recuperacao_apos_alerta_avisa_que_voltou():
    anterior = {**_falha(), "falhas_consecutivas": 3}
    assert [sev for sev, _ in sonda.comparar("x", anterior, _ok())] == ["INFO"]


def test_recuperacao_sem_alerta_previo_nao_gera_evento():
    anterior = {**_falha(), "falhas_consecutivas": 1}
    assert sonda.comparar("x", anterior, _ok()) == []


# ---------------------------------------------------------------- estado


def test_estado_conta_falhas_consecutivas():
    anterior = {**_falha(), "falhas_consecutivas": 1}
    assert sonda.proximo_estado(anterior, _falha())["falhas_consecutivas"] == 2


def test_estado_zera_contador_quando_volta():
    anterior = {**_falha(), "falhas_consecutivas": 4}
    assert sonda.proximo_estado(anterior, _ok())["falhas_consecutivas"] == 0


def test_estado_guarda_a_assinatura_e_o_horario():
    novo = sonda.proximo_estado(None, _ok(etag="abc"))
    assert novo["etag"] == "abc"
    assert novo["visto_em"]


# ---------------------------------------------------------------- execução


@pytest.fixture
def storage_local(monkeypatch, tmp_path):
    monkeypatch.setenv("PRACA_DATA_ROOT", str(tmp_path))
    return tmp_path


def test_executar_persiste_estado_no_storage(storage_local, monkeypatch):
    monkeypatch.setattr(sonda, "alertar", lambda *a, **k: True)
    fontes = {"siconfi": {"sonda": {"url": "https://exemplo"}}}

    sonda.executar(fontes=fontes, requisitar=lambda *a, **k: RespostaFake(200, {"ETag": "v1"}))

    estado = json.loads(storage.ler_bytes(sonda.caminho_estado()).decode("utf-8"))
    assert estado["siconfi"]["etag"] == "v1"


def test_executar_alerta_so_na_segunda_rodada_com_mudanca(storage_local, monkeypatch):
    enviados = []
    monkeypatch.setattr(
        sonda, "alertar", lambda msg, severidade="INFO": enviados.append((severidade, msg))
    )
    fontes = {"siconfi": {"sonda": {"url": "https://exemplo"}}}

    sonda.executar(fontes=fontes, requisitar=lambda *a, **k: RespostaFake(200, {"ETag": "v1"}))
    assert enviados == []  # primeira rodada só cria a linha de base

    sonda.executar(fontes=fontes, requisitar=lambda *a, **k: RespostaFake(200, {"ETag": "v2"}))
    assert [severidade for severidade, _ in enviados] == ["AVISO"]


def test_executar_devolve_resumo_com_contagens(storage_local, monkeypatch):
    monkeypatch.setattr(sonda, "alertar", lambda *a, **k: True)
    fontes = {"a": {"sonda": {"url": "https://um"}}, "b": {"sonda": {"url": "https://dois"}}}

    resumo = sonda.executar(
        fontes=fontes,
        requisitar=lambda metodo, url, **k: RespostaFake(200 if "um" in url else 500),
    )

    assert resumo["sondadas"] == 2
    assert resumo["indisponiveis"] == 1


def test_executar_nao_deixa_uma_fonte_derrubar_as_outras(storage_local, monkeypatch):
    """Watcher que morre na primeira fonte quebrada não vigia nada."""
    monkeypatch.setattr(sonda, "alertar", lambda *a, **k: True)
    fontes = {"a": {"sonda": {"url": "https://explode"}}, "b": {"sonda": {"url": "https://ok"}}}

    def requisitar(metodo, url, **kwargs):
        if "explode" in url:
            raise ConnectionError("dns falhou")
        return RespostaFake(200, {"ETag": "v1"})

    resumo = sonda.executar(fontes=fontes, requisitar=requisitar)

    assert resumo["sondadas"] == 2
    estado = json.loads(storage.ler_bytes(sonda.caminho_estado()).decode("utf-8"))
    assert estado["b"]["etag"] == "v1"
