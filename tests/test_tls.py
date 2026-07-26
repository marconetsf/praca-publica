"""TDD: bundle de CAs por fonte.

O download.inep.gov.br envia só o certificado folha, sem o intermediário. O
navegador busca o intermediário sozinho (AIA fetching); o Python não faz isso
e recusa a conexão. A saída correta é completar a cadeia — nunca `verify=False`,
que abriria o espelho a interceptação: o sha256 que gravamos é do que baixamos,
então ele não denunciaria conteúdo trocado no caminho.
"""

from pathlib import Path

import certifi
import pytest

from pipelines.common import tls


def test_sem_ca_extra_usa_o_certifi():
    assert tls.bundle(None) == certifi.where()


def test_bundle_contem_certifi_e_o_certificado_extra(tmp_path, monkeypatch):
    extra = tmp_path / "extra.pem"
    extra.write_text("-----BEGIN CERTIFICATE-----\nFALSO\n-----END CERTIFICATE-----\n")
    monkeypatch.setattr(tls, "RAIZ", tmp_path)

    caminho = tls.bundle("extra.pem")

    conteudo = Path(caminho).read_text(encoding="ascii")
    assert "FALSO" in conteudo
    assert len(conteudo) > len(extra.read_text())  # o certifi veio junto


def test_bundle_e_reaproveitado_entre_chamadas(tmp_path, monkeypatch):
    """Recriar o bundle a cada request desperdiçaria I/O em download de GBs."""
    extra = tmp_path / "extra.pem"
    extra.write_text("-----BEGIN CERTIFICATE-----\nX\n-----END CERTIFICATE-----\n")
    monkeypatch.setattr(tls, "RAIZ", tmp_path)
    tls.bundle.cache_clear()

    assert tls.bundle("extra.pem") == tls.bundle("extra.pem")


def test_ca_inexistente_falha_com_mensagem_clara(tmp_path, monkeypatch):
    monkeypatch.setattr(tls, "RAIZ", tmp_path)
    tls.bundle.cache_clear()

    with pytest.raises(FileNotFoundError, match="nao_existe.pem"):
        tls.bundle("nao_existe.pem")


def test_certificado_do_inep_esta_versionado():
    """Sem o PEM no repo o Actions não consegue espelhar o INEP."""
    from pipelines.common.config import RAIZ

    pem = RAIZ / "config" / "ca" / "inep.pem"
    assert pem.exists()
    conteudo = pem.read_text(encoding="ascii")
    assert conteudo.startswith("-----BEGIN CERTIFICATE-----")
    assert conteudo.strip().endswith("-----END CERTIFICATE-----")
