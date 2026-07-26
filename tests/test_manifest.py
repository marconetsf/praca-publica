"""Caracterização do manifesto de idempotência antes da refatoração."""

from pathlib import Path

from pipelines.common import manifest


def _isolar_manifesto(monkeypatch, tmp_path: Path) -> Path:
    caminho = tmp_path / "manifest.json"
    monkeypatch.setattr(manifest, "CAMINHO", caminho)
    return caminho


def test_chave_nova_nao_esta_processada(monkeypatch, tmp_path):
    _isolar_manifesto(monkeypatch, tmp_path)
    assert not manifest.ja_processado("siconfi/dca/2024/2611101")


def test_registrar_torna_chave_processada(monkeypatch, tmp_path):
    _isolar_manifesto(monkeypatch, tmp_path)
    manifest.registrar("siconfi/dca/2024/2611101", registros=42)
    assert manifest.ja_processado("siconfi/dca/2024/2611101")


def test_registrar_preserva_chaves_anteriores(monkeypatch, tmp_path):
    _isolar_manifesto(monkeypatch, tmp_path)
    manifest.registrar("a", registros=1)
    manifest.registrar("b", registros=2)
    assert manifest.ja_processado("a")
    assert manifest.ja_processado("b")


def test_registrar_grava_metadados_e_timestamp(monkeypatch, tmp_path):
    caminho = _isolar_manifesto(monkeypatch, tmp_path)
    manifest.registrar("chave", url="http://exemplo", registros=7)
    import json

    conteudo = json.loads(caminho.read_text(encoding="utf-8"))
    assert conteudo["chave"]["url"] == "http://exemplo"
    assert conteudo["chave"]["registros"] == 7
    assert "registrado_em" in conteudo["chave"]


def test_sha256_arquivo_valor_conhecido(tmp_path):
    arquivo = tmp_path / "abc.txt"
    arquivo.write_bytes(b"abc")
    esperado = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert manifest.sha256_arquivo(arquivo) == esperado
