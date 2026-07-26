"""TDD: ingest da DCA — raw datada, idempotência e janela de captura.

O caso que motiva a janela: município sem DCA hoje entrega com atraso amanhã.
Antes deste retrofit ele era registrado como processado e nunca mais consultado.
"""

import json
from datetime import UTC, date, datetime, timedelta

import pytest

from pipelines.common import manifest, parquet, storage
from pipelines.siconfi import ingest_dca

COLETA = date(2026, 7, 26)
COM_DCA = 2611101  # Petrolina
SEM_DCA = 2607901  # Jaboatão — nesta simulação, ainda não entregou


@pytest.fixture
def entes(monkeypatch, tmp_path):
    monkeypatch.setenv("PRACA_DATA_ROOT", str(tmp_path))
    origem = storage.uri("raw", "siconfi", "entes.json")
    storage.escrever_bytes(
        origem,
        json.dumps(
            [
                {"cod_ibge": COM_DCA, "ente": "Petrolina", "uf": "PE", "esfera": "M"},
                {"cod_ibge": SEM_DCA, "ente": "Jaboatão", "uf": "PE", "esfera": "M"},
                {"cod_ibge": 26, "ente": "Pernambuco", "uf": "PE", "esfera": "E"},
            ]
        ).encode("utf-8"),
    )
    parquet.json_para_parquet(origem, storage.uri("staging", "siconfi", "entes.parquet"))


class BuscadorFalso:
    """Devolve DCA só para COM_DCA e conta quem foi consultado."""

    def __init__(self):
        self.consultados: list[int] = []

    def __call__(self, endpoint: str, params: dict) -> dict:
        ente = params["id_ente"]
        self.consultados.append(ente)
        itens = [{"id_ente": ente, "conta": "Saúde", "valor": 1000.0}] if ente == COM_DCA else []
        return {"items": itens, "hasMore": False}


def test_grava_raw_datada_por_municipio(entes):
    ingest_dca.executar(2024, "PE", buscar=BuscadorFalso(), coleta=COLETA)

    raw = storage.caminho_raw("siconfi", "dca_2024_PE", f"{COM_DCA}.json", coleta=COLETA)
    assert storage.existe(raw)
    assert not storage.existe(
        storage.caminho_raw("siconfi", "dca_2024_PE", f"{SEM_DCA}.json", coleta=COLETA)
    )


def test_promove_staging_particionado(entes):
    destino = ingest_dca.executar(2024, "PE", buscar=BuscadorFalso(), coleta=COLETA)

    assert destino == storage.uri(
        "staging", "siconfi", "dca", "an_exercicio=2024", "uf=PE", "dca.parquet"
    )
    assert storage.existe(destino)


def test_municipio_com_dca_e_registrado_como_completo(entes):
    ingest_dca.executar(2024, "PE", buscar=BuscadorFalso(), coleta=COLETA)

    registros = json.loads(storage.ler_bytes(manifest.caminho()).decode("utf-8"))
    assert registros[f"siconfi/dca/2024/{COM_DCA}"]["completo"] is True


def test_municipio_sem_dca_e_registrado_como_incompleto(entes):
    """A lacuna é provisória, não definitiva — regra 4: ausente ≠ zero."""
    ingest_dca.executar(2024, "PE", buscar=BuscadorFalso(), coleta=COLETA)

    registros = json.loads(storage.ler_bytes(manifest.caminho()).decode("utf-8"))
    assert registros[f"siconfi/dca/2024/{SEM_DCA}"]["completo"] is False


def test_reexecucao_imediata_nao_reconsulta_ninguem(entes):
    ingest_dca.executar(2024, "PE", buscar=BuscadorFalso(), coleta=COLETA)

    segunda = BuscadorFalso()
    ingest_dca.executar(2024, "PE", buscar=segunda, coleta=date(2026, 7, 27))

    assert segunda.consultados == []


def test_apos_a_janela_so_o_incompleto_volta_a_ser_consultado(entes):
    ingest_dca.executar(2024, "PE", buscar=BuscadorFalso(), coleta=COLETA)
    _envelhecer_manifesto(dias=60)

    segunda = BuscadorFalso()
    ingest_dca.executar(2024, "PE", buscar=segunda, coleta=date(2026, 9, 24))

    assert segunda.consultados == [SEM_DCA]


def test_dca_entregue_com_atraso_entra_no_staging(entes):
    """O bug que a janela corrige: a entrega atrasada precisa chegar ao staging."""
    ingest_dca.executar(2024, "PE", buscar=BuscadorFalso(), coleta=COLETA)
    _envelhecer_manifesto(dias=60)

    class AgoraTodosEntregaram(BuscadorFalso):
        def __call__(self, endpoint: str, params: dict) -> dict:
            self.consultados.append(params["id_ente"])
            return {"items": [{"id_ente": params["id_ente"], "valor": 5.0}], "hasMore": False}

    destino = ingest_dca.executar(
        2024, "PE", buscar=AgoraTodosEntregaram(), coleta=date(2026, 9, 24)
    )

    entes_no_staging = _ler_coluna(destino, "id_ente")
    assert sorted(entes_no_staging) == sorted([COM_DCA, SEM_DCA])


def test_staging_mantem_coleta_antiga_de_quem_nao_foi_reconsultado(entes):
    """Raw datada não pode fazer o staging perder o que já tinha."""
    ingest_dca.executar(2024, "PE", buscar=BuscadorFalso(), coleta=COLETA)
    _envelhecer_manifesto(dias=60)

    destino = ingest_dca.executar(2024, "PE", buscar=BuscadorFalso(), coleta=date(2026, 9, 24))

    assert _ler_coluna(destino, "id_ente") == [COM_DCA]


def test_sem_entes_no_staging_falha_com_instrucao(monkeypatch, tmp_path):
    monkeypatch.setenv("PRACA_DATA_ROOT", str(tmp_path))
    with pytest.raises(SystemExit, match="ingest_entes"):
        ingest_dca.executar(2024, "PE", buscar=BuscadorFalso(), coleta=COLETA)


def test_nenhuma_dca_na_uf_nao_cria_staging(entes):
    class NinguemEntregou(BuscadorFalso):
        def __call__(self, endpoint: str, params: dict) -> dict:
            self.consultados.append(params["id_ente"])
            return {"items": [], "hasMore": False}

    with pytest.raises(SystemExit, match="Nenhuma DCA"):
        ingest_dca.executar(2024, "PE", buscar=NinguemEntregou(), coleta=COLETA)


def _envelhecer_manifesto(*, dias: int) -> None:
    """Recua os timestamps do manifesto para simular a passagem do tempo."""
    caminho = manifest.caminho()
    registros = json.loads(storage.ler_bytes(caminho).decode("utf-8"))
    passado = (datetime.now(UTC) - timedelta(days=dias)).isoformat()
    for registro in registros.values():
        registro["registrado_em"] = passado
    storage.escrever_bytes(caminho, json.dumps(registros).encode("utf-8"))
    manifest.recarregar()  # o manifesto foi alterado por fora do módulo


def _ler_coluna(destino: str, coluna: str) -> list:
    import duckdb

    linhas = duckdb.sql(f"SELECT {coluna} FROM '{destino}' ORDER BY 1").fetchall()
    return [linha[0] for linha in linhas]
