"""TDD: espelhamento defensivo (M0.5.1) — URL → raw no R2, com resume e sha256.

O marco existe por precedente concreto (FONTES.md §7): o INEP apagou séries em
2022 e nunca republicou completas; a série do SNIS saiu do ar. O espelho é a
única garantia de que o dado sobrevive ao apagão — então tudo aqui é pensado
para download que falha no meio, servidor que mente e execução que repete.
"""

import hashlib

import pytest

from pipelines.common import manifest, storage
from pipelines.espelho import espelhar


class RespostaFalsa:
    def __init__(self, corpo: bytes, status: int = 200, headers: dict | None = None):
        self.corpo = corpo
        self.status_code = status
        self.headers = headers or {"Content-Length": str(len(corpo))}

    def iter_content(self, chunk_size: int = 8192):
        for i in range(0, len(self.corpo), chunk_size):
            yield self.corpo[i : i + chunk_size]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def servidor(corpo: bytes, *, aceita_range: bool = True):
    """Servidor falso que honra Range como um servidor HTTP real."""
    chamadas = []

    def requisitar(url, *, headers=None):
        headers = headers or {}
        chamadas.append(headers.get("Range"))
        faixa = headers.get("Range")
        if faixa and aceita_range:
            inicio = int(faixa.removeprefix("bytes=").split("-")[0])
            parcial = corpo[inicio:]
            return RespostaFalsa(
                parcial,
                status=206,
                headers={
                    "Content-Length": str(len(parcial)),
                    "Content-Range": f"bytes {inicio}-{len(corpo) - 1}/{len(corpo)}",
                },
            )
        return RespostaFalsa(corpo)

    requisitar.chamadas = chamadas
    return requisitar


@pytest.fixture
def storage_local(monkeypatch, tmp_path):
    monkeypatch.setenv("PRACA_DATA_ROOT", str(tmp_path / "dados"))
    monkeypatch.setenv("PRACA_RAW_ROOT", str(tmp_path / "bruto"))
    return tmp_path


CORPO = b"microdados do censo escolar" * 500


# ---------------------------------------------------------------- download


def test_baixa_arquivo_inteiro(tmp_path):
    destino = tmp_path / "arquivo.zip"

    espelhar.baixar("https://inep/censo.zip", destino, requisitar=servidor(CORPO), tamanho_bloco=64)

    assert destino.read_bytes() == CORPO


def test_primeira_tentativa_nao_pede_range(tmp_path):
    requisitar = servidor(CORPO)
    espelhar.baixar("https://x/a.zip", tmp_path / "a.zip", requisitar=requisitar)
    assert requisitar.chamadas == [None]


def test_retoma_de_onde_parou(tmp_path):
    """Servidor governamental cai no meio de arquivo de 1 GB — recomeçar do zero é inviável."""
    destino = tmp_path / "a.zip"
    parcial = espelhar.caminho_parcial(destino)
    parcial.write_bytes(CORPO[:1000])
    requisitar = servidor(CORPO)

    espelhar.baixar("https://x/a.zip", destino, requisitar=requisitar, tamanho_bloco=64)

    assert requisitar.chamadas == ["bytes=1000-"]
    assert destino.read_bytes() == CORPO


def test_servidor_que_ignora_range_recomeca_sem_corromper(tmp_path):
    """Se o servidor devolve 200 ao pedido de Range, o parcial não pode ser concatenado."""
    destino = tmp_path / "a.zip"
    espelhar.caminho_parcial(destino).write_bytes(CORPO[:1000])

    espelhar.baixar(
        "https://x/a.zip",
        destino,
        requisitar=servidor(CORPO, aceita_range=False),
        tamanho_bloco=64,
    )

    assert destino.read_bytes() == CORPO


def test_tamanho_divergente_do_declarado_falha(tmp_path):
    """Download truncado silenciosamente viraria espelho corrompido (regra 4)."""

    def requisitar(url, *, headers=None):
        return RespostaFalsa(b"curto demais", headers={"Content-Length": "999999"})

    with pytest.raises(RuntimeError, match="incompleto"):
        espelhar.baixar("https://x/a.zip", tmp_path / "a.zip", requisitar=requisitar)


def test_download_interrompido_preserva_o_parcial(tmp_path):
    """O que já veio precisa sobreviver para a próxima tentativa retomar."""
    destino = tmp_path / "a.zip"

    def requisitar(url, *, headers=None):
        class Explosiva(RespostaFalsa):
            def iter_content(self, chunk_size=8192):
                yield CORPO[:500]
                raise ConnectionError("conexão caiu")

        return Explosiva(CORPO)

    with pytest.raises(ConnectionError):
        espelhar.baixar("https://x/a.zip", destino, requisitar=requisitar, tentativas=1, espera=0)

    assert espelhar.caminho_parcial(destino).read_bytes() == CORPO[:500]
    assert not destino.exists()


def test_queda_de_conexao_e_retomada_automaticamente(tmp_path):
    """O download.inep.gov.br reseta conexões no meio do handshake, sem padrão."""
    tentativas = []

    def requisitar(url, *, headers=None):
        tentativas.append(headers.get("Range") if headers else None)
        if len(tentativas) == 1:

            class Explosiva(RespostaFalsa):
                def iter_content(self, chunk_size=8192):
                    yield CORPO[:1000]
                    raise ConnectionError("conexão resetada pelo host remoto")

            return Explosiva(CORPO)
        return servidor(CORPO)(url, headers=headers)

    destino = tmp_path / "a.zip"
    espelhar.baixar(url="https://inep/a.zip", destino=destino, requisitar=requisitar, espera=0)

    assert tentativas == [None, "bytes=1000-"]  # retomou de onde parou
    assert destino.read_bytes() == CORPO


def test_desiste_depois_das_tentativas(tmp_path):
    def requisitar(url, *, headers=None):
        raise ConnectionError("servidor fora do ar")

    with pytest.raises(ConnectionError):
        espelhar.baixar(
            "https://x/a.zip", tmp_path / "a.zip", requisitar=requisitar, tentativas=3, espera=0
        )


def test_erro_de_integridade_nao_e_retentado(tmp_path):
    """Content-Length divergente é defeito do arquivo, não da rede: insistir não resolve."""
    chamadas = []

    def requisitar(url, *, headers=None):
        chamadas.append(1)
        return RespostaFalsa(b"curto", headers={"Content-Length": "999"})

    with pytest.raises(RuntimeError, match="incompleto"):
        espelhar.baixar("https://x/a.zip", tmp_path / "a.zip", requisitar=requisitar, espera=0)

    assert len(chamadas) == 1


# ---------------------------------------------------------------- espelhar


def test_espelhar_grava_na_raw_datada_com_hash(storage_local):
    from datetime import date

    resultado = espelhar.espelhar(
        "inep", "https://inep/censo_2024.zip", requisitar=servidor(CORPO), coleta=date(2026, 7, 26)
    )

    destino = storage.caminho_raw("inep", "censo_2024.zip", coleta=date(2026, 7, 26))
    assert storage.existe(destino)
    assert storage.ler_bytes(destino) == CORPO
    assert resultado["sha256"] == hashlib.sha256(CORPO).hexdigest()
    assert resultado["bytes"] == len(CORPO)


def test_espelhar_registra_no_manifesto(storage_local):
    espelhar.espelhar("inep", "https://inep/censo_2024.zip", requisitar=servidor(CORPO))

    registro = manifest._carregar()["espelho/inep/censo_2024.zip"]
    assert registro["completo"] is True
    assert registro["url"] == "https://inep/censo_2024.zip"
    assert registro["sha256"] == hashlib.sha256(CORPO).hexdigest()


def test_espelhar_e_idempotente(storage_local):
    requisitar = servidor(CORPO)
    espelhar.espelhar("inep", "https://inep/a.zip", requisitar=requisitar)
    chamadas_primeira = len(requisitar.chamadas)

    resultado = espelhar.espelhar("inep", "https://inep/a.zip", requisitar=requisitar)

    assert len(requisitar.chamadas) == chamadas_primeira  # não baixou de novo
    assert resultado["pulado"] is True


def test_falha_no_download_nao_registra_no_manifesto(storage_local):
    """Meio arquivo registrado como espelhado seria pior que nenhum."""

    def requisitar(url, *, headers=None):
        raise ConnectionError("servidor fora do ar")

    with pytest.raises(ConnectionError):
        espelhar.espelhar(
            "inep", "https://inep/a.zip", requisitar=requisitar, tentativas=1, espera=0
        )

    assert not manifest.ja_processado("espelho/inep/a.zip")


def test_nome_do_arquivo_vem_da_url_sem_querystring(storage_local):
    assert espelhar.nome_do_arquivo("https://x/dados/censo_2024.zip?token=abc") == "censo_2024.zip"


def test_url_sem_nome_util_falha_cedo(storage_local):
    with pytest.raises(ValueError, match="nome"):
        espelhar.nome_do_arquivo("https://exemplo.gov.br/")


def test_espelhar_url_ftp_usa_o_cliente_ftp(storage_local, monkeypatch):
    """DataSUS e PDET só existem por FTP — o espelho precisa falar os dois protocolos."""
    chamadas = {}

    def baixar_ftp_falso(url, destino, *, encoding="utf-8", **kwargs):
        chamadas["url"] = url
        chamadas["encoding"] = encoding
        destino.write_bytes(CORPO)
        return destino

    monkeypatch.setattr(espelhar.ftp, "baixar", baixar_ftp_falso)

    resultado = espelhar.espelhar(
        "rais_caged",
        "ftp://ftp.mtps.gov.br/pdet/microdados/NOVO%20CAGED/2026/202605/CAGEDMOV202605.7z",
        ftp_encoding="latin-1",
    )

    assert chamadas["encoding"] == "latin-1"
    assert resultado["bytes"] == len(CORPO)
    assert storage.existe(storage.caminho_raw("rais_caged", "CAGEDMOV202605.7z"))


def test_nome_do_arquivo_decodifica_espaco_em_url_ftp():
    nome = espelhar.nome_do_arquivo("ftp://host/NOVO%20CAGED/2026/CAGEDMOV202605.7z")
    assert nome == "CAGEDMOV202605.7z"


# ---------------------------------------------------------------- catálogo


# Toda fonte do catálogo declara o que se guarda dela (ver test_guarda.py); os
# alvos do espelho passam por essa declaração antes de virar download.
GUARDA_INTEGRAL = {
    "modo": "integral",
    "medido_em": "2026-08-16",
    "motivo": "fonte com precedente de apagão",
}


def test_alvos_do_yaml_le_a_lista_espelho_da_fonte():
    fontes = {
        "inep": {"espelho": ["https://inep/a.zip", "https://inep/b.zip"], "guarda": GUARDA_INTEGRAL}
    }
    assert espelhar.alvos_do_catalogo(fontes) == [
        ("inep", "https://inep/a.zip"),
        ("inep", "https://inep/b.zip"),
    ]


def test_fonte_sem_espelho_nao_entra():
    fontes = {
        "siconfi": {
            "api_base": "https://x",
            "guarda": {
                "modo": "colheita",
                "medido_em": "2026-08-16",
                "motivo": "API com filtro; guardamos as respostas de cada execução",
            },
        },
        "inep": {"espelho": ["https://inep/a.zip"], "guarda": GUARDA_INTEGRAL},
    }
    assert espelhar.alvos_do_catalogo(fontes) == [("inep", "https://inep/a.zip")]
