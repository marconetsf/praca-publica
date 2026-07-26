"""TDD: abstração de storage local ↔ R2 via PRACA_DATA_ROOT."""

from datetime import date
from pathlib import Path

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


def test_raw_vai_para_o_bucket_proprio(monkeypatch):
    """Topologia da ARQUITETURA §2: raw mora em praca-raw, o resto em praca-dados."""
    monkeypatch.setenv("PRACA_DATA_ROOT", "s3://praca-dados")
    monkeypatch.setenv("PRACA_RAW_ROOT", "s3://praca-raw")
    destino = storage.caminho_raw("siconfi", "entes.json", coleta=date(2026, 7, 26))
    assert destino == "s3://praca-raw/raw/siconfi/2026-07-26/entes.json"


def test_staging_e_marts_ficam_no_bucket_de_dados(monkeypatch):
    monkeypatch.setenv("PRACA_DATA_ROOT", "s3://praca-dados")
    monkeypatch.setenv("PRACA_RAW_ROOT", "s3://praca-raw")
    assert storage.uri("staging", "siconfi", "entes.parquet").startswith("s3://praca-dados/")
    assert storage.uri("marts", "fato.parquet").startswith("s3://praca-dados/")


def test_sem_raw_root_tudo_compartilha_a_mesma_raiz(monkeypatch, tmp_path):
    """Desenvolvimento local continua com uma pasta só."""
    monkeypatch.delenv("PRACA_RAW_ROOT", raising=False)
    monkeypatch.setenv("PRACA_DATA_ROOT", str(tmp_path))
    raiz = str(tmp_path).replace("\\", "/")
    assert storage.caminho_raw("siconfi", "e.json").replace("\\", "/").startswith(raiz)
    assert storage.uri("staging", "e.parquet").replace("\\", "/").startswith(raiz)


def test_coletas_mais_recentes_com_raw_em_bucket_separado(monkeypatch, tmp_path):
    monkeypatch.setenv("PRACA_DATA_ROOT", str(tmp_path / "dados"))
    monkeypatch.setenv("PRACA_RAW_ROOT", str(tmp_path / "bruto"))
    storage.escrever_bytes(
        storage.caminho_raw("siconfi", "1.json", coleta=date(2026, 7, 25)), b"antigo"
    )
    storage.escrever_bytes(
        storage.caminho_raw("siconfi", "1.json", coleta=date(2026, 7, 26)), b"novo"
    )

    achados = storage.coletas_mais_recentes("siconfi", "*.json")

    assert len(achados) == 1
    assert storage.ler_bytes(achados[0]) == b"novo"


def test_caminho_raw_inclui_a_data_de_coleta(monkeypatch):
    monkeypatch.setenv("PRACA_DATA_ROOT", "s3://praca-raw")
    destino = storage.caminho_raw("siconfi", "entes.json", coleta=date(2026, 7, 26))
    assert destino == "s3://praca-raw/raw/siconfi/2026-07-26/entes.json"


def test_caminho_raw_usa_hoje_por_padrao(monkeypatch):
    monkeypatch.setenv("PRACA_DATA_ROOT", "s3://praca-raw")
    destino = storage.caminho_raw("siconfi", "entes.json")
    assert f"/raw/siconfi/{date.today().isoformat()}/entes.json" in destino


def test_caminho_raw_aceita_subpastas(monkeypatch):
    monkeypatch.setenv("PRACA_DATA_ROOT", "s3://praca-raw")
    destino = storage.caminho_raw(
        "siconfi", "dca_2024_PE", "2611101.json", coleta=date(2026, 7, 26)
    )
    assert destino == "s3://praca-raw/raw/siconfi/2026-07-26/dca_2024_PE/2611101.json"


def test_coletas_em_dias_diferentes_nao_se_sobrescrevem(monkeypatch, tmp_path):
    """Regra 6: raw é imutável — coleta nova nunca sobrescreve a anterior."""
    monkeypatch.setenv("PRACA_DATA_ROOT", str(tmp_path))
    ontem = storage.caminho_raw("siconfi", "entes.json", coleta=date(2026, 7, 25))
    hoje = storage.caminho_raw("siconfi", "entes.json", coleta=date(2026, 7, 26))
    storage.escrever_bytes(ontem, b"versao antiga")
    storage.escrever_bytes(hoje, b"versao nova")
    assert storage.ler_bytes(ontem) == b"versao antiga"
    assert storage.ler_bytes(hoje) == b"versao nova"


def test_listar_devolve_os_arquivos_do_glob(monkeypatch, tmp_path):
    monkeypatch.setenv("PRACA_DATA_ROOT", str(tmp_path))
    for nome in ("a.json", "b.json", "c.txt"):
        storage.escrever_bytes(storage.uri("raw", "fonte", nome), b"x")
    achados = storage.listar(storage.uri("raw", "fonte", "*.json"))
    assert sorted(Path(a).name for a in achados) == ["a.json", "b.json"]


def test_listar_vazio_quando_nada_corresponde(monkeypatch, tmp_path):
    monkeypatch.setenv("PRACA_DATA_ROOT", str(tmp_path))
    assert storage.listar(storage.uri("raw", "nada", "*.json")) == []


def test_coletas_mais_recentes_prefere_a_data_maior(monkeypatch, tmp_path):
    monkeypatch.setenv("PRACA_DATA_ROOT", str(tmp_path))
    storage.escrever_bytes(
        storage.caminho_raw("siconfi", "2611101.json", coleta=date(2026, 7, 25)), b"antigo"
    )
    storage.escrever_bytes(
        storage.caminho_raw("siconfi", "2611101.json", coleta=date(2026, 7, 26)), b"novo"
    )

    achados = storage.coletas_mais_recentes("siconfi", "*.json")

    assert len(achados) == 1
    assert storage.ler_bytes(achados[0]) == b"novo"


def test_coletas_mais_recentes_preserva_arquivo_ausente_na_coleta_nova(monkeypatch, tmp_path):
    """Município que entregou em julho e não aparece em agosto não pode sumir do staging."""
    monkeypatch.setenv("PRACA_DATA_ROOT", str(tmp_path))
    storage.escrever_bytes(
        storage.caminho_raw("siconfi", "2611101.json", coleta=date(2026, 7, 25)), b"so em julho"
    )
    storage.escrever_bytes(
        storage.caminho_raw("siconfi", "2607901.json", coleta=date(2026, 8, 1)), b"so em agosto"
    )

    achados = storage.coletas_mais_recentes("siconfi", "*.json")

    assert sorted(Path(a).name for a in achados) == ["2607901.json", "2611101.json"]


def test_coletas_mais_recentes_respeita_subpasta(monkeypatch, tmp_path):
    monkeypatch.setenv("PRACA_DATA_ROOT", str(tmp_path))
    storage.escrever_bytes(
        storage.caminho_raw("siconfi", "dca_2024_PE", "1.json", coleta=date(2026, 7, 26)), b"pe"
    )
    storage.escrever_bytes(
        storage.caminho_raw("siconfi", "dca_2024_RR", "2.json", coleta=date(2026, 7, 26)), b"rr"
    )

    achados = storage.coletas_mais_recentes("siconfi", "dca_2024_PE", "*.json")

    assert len(achados) == 1
    assert storage.ler_bytes(achados[0]) == b"pe"


def test_coletas_mais_recentes_vazio_sem_raw(monkeypatch, tmp_path):
    monkeypatch.setenv("PRACA_DATA_ROOT", str(tmp_path))
    assert storage.coletas_mais_recentes("siconfi", "*.json") == []


def test_enviar_arquivo_copia_sem_passar_pela_memoria(monkeypatch, tmp_path):
    """Espelho de 1 GB não cabe em read_bytes() — a subida precisa ser por arquivo."""
    monkeypatch.setenv("PRACA_DATA_ROOT", str(tmp_path / "dados"))
    origem = tmp_path / "grande.zip"
    origem.write_bytes(b"conteudo binario" * 1000)

    destino = storage.uri("raw", "fonte", "grande.zip")
    storage.enviar_arquivo(origem, destino)

    assert storage.ler_bytes(destino) == origem.read_bytes()


def test_enviar_arquivo_cria_diretorios_intermediarios(monkeypatch, tmp_path):
    monkeypatch.setenv("PRACA_DATA_ROOT", str(tmp_path / "dados"))
    origem = tmp_path / "a.txt"
    origem.write_bytes(b"x")

    destino = storage.uri("raw", "fonte", "2026-07-26", "sub", "a.txt")
    storage.enviar_arquivo(origem, destino)

    assert storage.existe(destino)


def test_opcoes_fs_r2_sem_credenciais_falha_claro(monkeypatch):
    monkeypatch.delenv("R2_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("R2_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("R2_SECRET_ACCESS_KEY", raising=False)
    import pytest

    with pytest.raises(RuntimeError, match="R2_"):
        storage.opcoes_fs("s3://praca-dados/x")
