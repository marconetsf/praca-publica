"""TDD: abstração de storage local ↔ R2 via PRACA_DATA_ROOT."""

from pipelines.common import storage


def test_raiz_padrao_e_data_local(monkeypatch):
    monkeypatch.delenv("PRACA_DATA_ROOT", raising=False)
    assert storage.raiz().replace("\\", "/").endswith("/data")


def test_raiz_respeita_env(monkeypatch):
    monkeypatch.setenv("PRACA_DATA_ROOT", "s3://praca-dados")
    assert storage.raiz() == "s3://praca-dados"


def test_uri_junta_camada_e_partes(monkeypatch):
    monkeypatch.setenv("PRACA_DATA_ROOT", "s3://praca-dados")
    esperado = "s3://praca-dados/raw/siconfi/2026-07-26/entes.json"
    assert storage.uri("raw", "siconfi", "2026-07-26", "entes.json") == esperado


def test_roundtrip_local(monkeypatch, tmp_path):
    monkeypatch.setenv("PRACA_DATA_ROOT", str(tmp_path))
    destino = storage.uri("raw", "teste", "arq.txt")
    storage.escrever_bytes(destino, b"ola")
    assert storage.ler_bytes(destino) == b"ola"
    assert storage.existe(destino)


def test_escrever_cria_diretorios_intermediarios(monkeypatch, tmp_path):
    monkeypatch.setenv("PRACA_DATA_ROOT", str(tmp_path))
    destino = storage.uri("raw", "a", "b", "c", "fundo.txt")
    storage.escrever_bytes(destino, b"x")
    assert storage.existe(destino)


def test_existe_falso_para_inexistente(monkeypatch, tmp_path):
    monkeypatch.setenv("PRACA_DATA_ROOT", str(tmp_path))
    assert not storage.existe(storage.uri("raw", "nao", "ha.txt"))


def test_opcoes_fs_para_r2(monkeypatch):
    monkeypatch.setenv("R2_ACCOUNT_ID", "abc123")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "chave")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "segredo")
    opts = storage.opcoes_fs("s3://praca-dados/x")
    assert opts["client_kwargs"]["endpoint_url"] == "https://abc123.r2.cloudflarestorage.com"
    assert opts["key"] == "chave"
    assert opts["secret"] == "segredo"


def test_opcoes_fs_local_e_vazio(tmp_path):
    assert storage.opcoes_fs(str(tmp_path / "x")) == {}


def test_opcoes_fs_r2_sem_credenciais_falha_claro(monkeypatch):
    monkeypatch.delenv("R2_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("R2_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("R2_SECRET_ACCESS_KEY", raising=False)
    import pytest

    with pytest.raises(RuntimeError, match="R2_"):
        storage.opcoes_fs("s3://praca-dados/x")
