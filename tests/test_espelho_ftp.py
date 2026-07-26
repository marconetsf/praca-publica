"""TDD: espelhamento por FTP (onda 2 do M0.5).

DataSUS e PDET/RAIS-CAGED só existem por FTP anônimo — o portal do PDET está
com certificado TLS inválido e o host do DataSUS não atende na 443. Verificado
em 27/07/2026: ambos os FTPs respondem, com SIZE e REST funcionando.

Detalhe que quebra na prática: o FTP do MTPS devolve nomes de arquivo em
latin-1 ("NOVO CAGED" tem PDF com ç e õ), e o ftplib assume utf-8 — listar o
diretório estoura UnicodeDecodeError antes de qualquer download.
"""

import pytest

from pipelines.espelho import ftp as espelho_ftp


class FtpFalso:
    """Servidor FTP de mentira que se comporta como o ftplib espera."""

    def __init__(self, arquivos: dict[str, bytes], *, suporta_rest: bool = True):
        self.arquivos = arquivos
        self.suporta_rest = suporta_rest
        self.encoding = "utf-8"
        self.diretorio = "/"
        self.comandos: list[str] = []
        self.fechado = False

    def login(self, *args, **kwargs):
        self.comandos.append("LOGIN")

    def cwd(self, caminho):
        self.comandos.append(f"CWD {caminho}")
        self.diretorio = caminho

    def voidcmd(self, comando):
        self.comandos.append(comando)

    def size(self, nome):
        return len(self.arquivos[nome])

    def retrbinary(self, comando, callback, blocksize=8192, rest=None):
        self.comandos.append(f"{comando} rest={rest}")
        nome = comando.removeprefix("RETR ")
        dados = self.arquivos[nome]
        if rest:
            if not self.suporta_rest:
                raise RuntimeError("servidor não deveria receber REST neste teste")
            dados = dados[rest:]
        for i in range(0, len(dados), blocksize):
            callback(dados[i : i + blocksize])

    def nlst(self):
        return list(self.arquivos)

    def retrlines(self, comando, callback):
        self.comandos.append(comando)
        for nome, dados in self.arquivos.items():
            callback(f"-rw-r--r-- 1 ftp ftp {len(dados)} Jul 27 10:00 {nome}")

    def quit(self):
        self.fechado = True

    def close(self):
        self.fechado = True


CONTEUDO = b"microdados do caged" * 300


def conector(ftp_falso):
    def conectar(host, *, encoding="utf-8", timeout=None):
        ftp_falso.host = host
        ftp_falso.encoding = encoding
        return ftp_falso

    return conectar


# ---------------------------------------------------------------- URL


def test_partes_da_url_separa_host_diretorio_e_arquivo():
    host, diretorio, arquivo = espelho_ftp.partes_da_url(
        "ftp://ftp.mtps.gov.br/pdet/microdados/CAGED/CAGEDEST_012020.7z"
    )
    assert host == "ftp.mtps.gov.br"
    assert diretorio == "/pdet/microdados/CAGED"
    assert arquivo == "CAGEDEST_012020.7z"


def test_partes_da_url_aceita_espaco_codificado():
    """`NOVO CAGED` tem espaço no nome do diretório — vem como %20 na URL."""
    _, diretorio, arquivo = espelho_ftp.partes_da_url(
        "ftp://ftp.mtps.gov.br/pdet/microdados/NOVO%20CAGED/2026/202605/CAGEDMOV202605.7z"
    )
    assert diretorio == "/pdet/microdados/NOVO CAGED/2026/202605"
    assert arquivo == "CAGEDMOV202605.7z"


def test_url_sem_arquivo_falha_cedo():
    with pytest.raises(ValueError, match="arquivo"):
        espelho_ftp.partes_da_url("ftp://ftp.datasus.gov.br/dissemin/publicos/")


# ---------------------------------------------------------------- download


def test_baixa_arquivo_inteiro(tmp_path):
    falso = FtpFalso({"a.7z": CONTEUDO})
    destino = tmp_path / "a.7z"

    espelho_ftp.baixar("ftp://host/dir/a.7z", destino, conectar=conector(falso))

    assert destino.read_bytes() == CONTEUDO
    assert "RETR a.7z rest=None" in falso.comandos


def test_aplica_o_encoding_declarado(tmp_path):
    """Sem latin-1, listar o diretório do MTPS estoura UnicodeDecodeError."""
    falso = FtpFalso({"a.7z": CONTEUDO})

    espelho_ftp.baixar(
        "ftp://host/dir/a.7z", tmp_path / "a.7z", conectar=conector(falso), encoding="latin-1"
    )

    assert falso.encoding == "latin-1"


def test_retoma_de_onde_parou(tmp_path):
    falso = FtpFalso({"a.7z": CONTEUDO})
    destino = tmp_path / "a.7z"
    espelho_ftp.caminho_parcial(destino).write_bytes(CONTEUDO[:500])

    espelho_ftp.baixar("ftp://host/dir/a.7z", destino, conectar=conector(falso))

    assert "RETR a.7z rest=500" in falso.comandos
    assert destino.read_bytes() == CONTEUDO


def test_tamanho_divergente_do_size_falha(tmp_path):
    """SIZE é a única conferência que o FTP oferece — ignorá-la deixaria passar truncado."""

    class Truncado(FtpFalso):
        def retrbinary(self, comando, callback, blocksize=8192, rest=None):
            callback(CONTEUDO[:10])

    falso = Truncado({"a.7z": CONTEUDO})

    with pytest.raises(RuntimeError, match="incompleto"):
        espelho_ftp.baixar("ftp://host/dir/a.7z", tmp_path / "a.7z", conectar=conector(falso))


def test_parcial_sobrevive_a_falha(tmp_path):
    class Explosivo(FtpFalso):
        def retrbinary(self, comando, callback, blocksize=8192, rest=None):
            callback(CONTEUDO[:400])
            raise ConnectionError("conexão caiu")

    falso = Explosivo({"a.7z": CONTEUDO})
    destino = tmp_path / "a.7z"

    with pytest.raises(ConnectionError):
        espelho_ftp.baixar("ftp://host/dir/a.7z", destino, conectar=conector(falso))

    assert espelho_ftp.caminho_parcial(destino).read_bytes() == CONTEUDO[:400]
    assert not destino.exists()


def test_conexao_e_encerrada_mesmo_em_falha(tmp_path):
    class Explosivo(FtpFalso):
        def retrbinary(self, *a, **k):
            raise ConnectionError("caiu")

    falso = Explosivo({"a.7z": CONTEUDO})

    with pytest.raises(ConnectionError):
        espelho_ftp.baixar("ftp://host/dir/a.7z", tmp_path / "a.7z", conectar=conector(falso))

    assert falso.fechado, "conexão FTP vazada deixaria sessão pendurada no servidor"


# ---------------------------------------------------------------- listagem


# Linhas capturadas dos servidores reais em 27/07/2026 — os dois usam o formato
# MS-DOS, não o Unix que se assume por padrão.
LIST_DATASUS = "01-31-20  02:48PM                76107 DOAC1996.dbc"
LIST_DATASUS_DIR = "07-07-14  10:51AM       <DIR>          CNES"
LIST_MTPS_ESPACO = (
    "06-05-20  05:49PM               345046 Comunicado - Grupamento de Atividades Econômicas.pdf"
)
LIST_UNIX = "-rw-r--r--    1 ftp      ftp        123456 Jul 27 10:00 arquivo.zip"


def test_parseia_formato_ms_dos_do_datasus():
    item = espelho_ftp.parsear_linha(LIST_DATASUS)
    assert item == {"nome": "DOAC1996.dbc", "tamanho": 76107}


def test_parseia_nome_com_espacos_e_acentos():
    """O PDF do PDET tem espaços e acentos no nome — cortar no espaço perderia o arquivo."""
    item = espelho_ftp.parsear_linha(LIST_MTPS_ESPACO)
    assert item["nome"] == "Comunicado - Grupamento de Atividades Econômicas.pdf"
    assert item["tamanho"] == 345046


def test_diretorio_ms_dos_e_ignorado():
    assert espelho_ftp.parsear_linha(LIST_DATASUS_DIR) is None


def test_ainda_entende_o_formato_unix():
    item = espelho_ftp.parsear_linha(LIST_UNIX)
    assert item == {"nome": "arquivo.zip", "tamanho": 123456}


def test_linha_ininteligivel_nao_derruba():
    assert espelho_ftp.parsear_linha("total 42") is None
    assert espelho_ftp.parsear_linha("") is None


def test_listar_devolve_nomes_e_tamanhos():
    falso = FtpFalso({"a.7z": b"12345", "b.7z": b"123"})

    itens = espelho_ftp.listar("ftp://host/dir/", conectar=conector(falso))

    assert {item["nome"] for item in itens} == {"a.7z", "b.7z"}
    assert {item["tamanho"] for item in itens} == {5, 3}


def test_listar_ignora_diretorios():
    falso = FtpFalso({"a.7z": b"12345"})
    original = falso.retrlines

    def com_diretorio(comando, callback):
        callback("drwxr-xr-x 2 ftp ftp 4096 Jul 27 10:00 SUBPASTA")
        original(comando, callback)

    falso.retrlines = com_diretorio

    itens = espelho_ftp.listar("ftp://host/dir/", conectar=conector(falso))

    assert [item["nome"] for item in itens] == ["a.7z"]
