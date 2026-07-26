"""TDD: manifesto de idempotência com janela de captura, persistido no storage.

A janela existe por um bug real: hoje um município sem DCA é registrado como
processado e nunca mais é consultado — a entrega atrasada jamais entraria.
"""

import json
from datetime import UTC, datetime, timedelta

from pipelines.common import manifest, storage


def _isolar(monkeypatch, tmp_path):
    monkeypatch.setenv("PRACA_DATA_ROOT", str(tmp_path))


def test_chave_nova_nao_esta_processada(monkeypatch, tmp_path):
    _isolar(monkeypatch, tmp_path)
    assert not manifest.ja_processado("siconfi/dca/2024/2611101")


def test_registrar_torna_chave_processada(monkeypatch, tmp_path):
    _isolar(monkeypatch, tmp_path)
    manifest.registrar("siconfi/dca/2024/2611101", registros=42)
    assert manifest.ja_processado("siconfi/dca/2024/2611101")


def test_registrar_preserva_chaves_anteriores(monkeypatch, tmp_path):
    _isolar(monkeypatch, tmp_path)
    manifest.registrar("a", registros=1)
    manifest.registrar("b", registros=2)
    assert manifest.ja_processado("a")
    assert manifest.ja_processado("b")


def test_registrar_grava_metadados_e_timestamp(monkeypatch, tmp_path):
    _isolar(monkeypatch, tmp_path)
    manifest.registrar("chave", url="http://exemplo", registros=7)
    conteudo = json.loads(storage.ler_bytes(manifest.caminho()).decode("utf-8"))
    assert conteudo["chave"]["url"] == "http://exemplo"
    assert conteudo["chave"]["registros"] == 7
    assert "registrado_em" in conteudo["chave"]


def test_manifesto_mora_em_catalog_no_storage(monkeypatch, tmp_path):
    """ARQUITETURA §1: o catálogo vai junto para o bucket, em catalog/."""
    _isolar(monkeypatch, tmp_path)
    manifest.registrar("a", registros=1)
    assert (tmp_path / "catalog" / "manifest.json").exists()


def test_manifesto_acompanha_o_bucket_de_dados_e_nao_o_de_raw(monkeypatch, tmp_path):
    monkeypatch.setenv("PRACA_DATA_ROOT", str(tmp_path / "dados"))
    monkeypatch.setenv("PRACA_RAW_ROOT", str(tmp_path / "bruto"))
    manifest.registrar("a", registros=1)
    assert (tmp_path / "dados" / "catalog" / "manifest.json").exists()
    assert not (tmp_path / "bruto" / "catalog").exists()


def test_registro_completo_nunca_expira(monkeypatch, tmp_path):
    _isolar(monkeypatch, tmp_path)
    manifest.registrar("siconfi/dca/2024/2611101", registros=42, completo=True)
    daqui_a_anos = datetime.now(UTC) + timedelta(days=3650)
    assert manifest.ja_processado("siconfi/dca/2024/2611101", agora=daqui_a_anos)


def test_registro_incompleto_vale_dentro_da_janela(monkeypatch, tmp_path):
    """Sem isso, cada execução consultaria de novo os ~1.500 municípios sem DCA."""
    _isolar(monkeypatch, tmp_path)
    manifest.registrar("siconfi/dca/2024/2611101", registros=0, completo=False)
    daqui_a_pouco = datetime.now(UTC) + timedelta(days=5)
    assert manifest.ja_processado("siconfi/dca/2024/2611101", janela_dias=30, agora=daqui_a_pouco)


def test_registro_incompleto_expira_depois_da_janela(monkeypatch, tmp_path):
    """O município que entregou a DCA com atraso precisa voltar a ser consultado."""
    _isolar(monkeypatch, tmp_path)
    manifest.registrar("siconfi/dca/2024/2611101", registros=0, completo=False)
    depois = datetime.now(UTC) + timedelta(days=31)
    assert not manifest.ja_processado("siconfi/dca/2024/2611101", janela_dias=30, agora=depois)


def test_registro_legado_sem_campo_completo_conta_como_completo(monkeypatch, tmp_path):
    _isolar(monkeypatch, tmp_path)
    antigo = {"legado": {"registrado_em": "2020-01-01T00:00:00+00:00", "registros": 3}}
    storage.escrever_bytes(manifest.caminho(), json.dumps(antigo).encode("utf-8"))
    assert manifest.ja_processado("legado")


def test_reregistrar_completo_apaga_o_incompleto_anterior(monkeypatch, tmp_path):
    _isolar(monkeypatch, tmp_path)
    manifest.registrar("chave", registros=0, completo=False)
    manifest.registrar("chave", registros=9, completo=True)
    depois = datetime.now(UTC) + timedelta(days=365)
    assert manifest.ja_processado("chave", agora=depois)


def test_sha256_arquivo_valor_conhecido(tmp_path):
    arquivo = tmp_path / "abc.txt"
    arquivo.write_bytes(b"abc")
    esperado = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert manifest.sha256_arquivo(arquivo) == esperado


def test_sha256_bytes_valor_conhecido():
    esperado = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert manifest.sha256_bytes(b"abc") == esperado
