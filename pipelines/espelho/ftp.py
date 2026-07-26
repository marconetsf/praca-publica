"""Espelhamento por FTP anônimo — DataSUS e PDET (RAIS/CAGED).

Essas duas fontes não têm alternativa HTTP utilizável: o host do DataSUS não
atende na 443 e o portal do PDET está com certificado TLS inválido. O FTP, ao
contrário, responde bem e ainda oferece SIZE e REST (verificado em 27/07/2026).

Armadilha específica: o FTP do MTPS devolve nomes de arquivo em latin-1
(o diretório "NOVO CAGED" tem PDF com ç e õ) e o ftplib assume utf-8 — listar
estoura UnicodeDecodeError antes de qualquer download. Por isso o encoding é
declarado por fonte no YAML, como manda a convenção do projeto.
"""

import re
from ftplib import FTP
from pathlib import Path
from urllib.parse import unquote, urlparse

TAMANHO_BLOCO = 1 << 20  # 1 MiB
TIMEOUT = 120  # servidores do governo demoram a responder LIST em pasta grande
DATA_MS_DOS = re.compile(r"^\d{2}-\d{2}-\d{2}$")


def partes_da_url(url: str) -> tuple[str, str, str]:
    """`ftp://host/dir/sub/arquivo.7z` → (host, "/dir/sub", "arquivo.7z")."""
    partes = urlparse(url)
    caminho = unquote(partes.path)  # "NOVO CAGED" chega como NOVO%20CAGED
    diretorio, _, arquivo = caminho.rpartition("/")
    if not arquivo:
        raise ValueError(f"a URL não aponta para um arquivo: {url}")
    return partes.hostname, diretorio or "/", arquivo


def caminho_parcial(destino: Path) -> Path:
    return destino.with_suffix(destino.suffix + ".parcial")


def _conectar_real(host: str, *, encoding: str = "utf-8", timeout: int = TIMEOUT) -> FTP:
    ftp = FTP(host, timeout=timeout)
    ftp.encoding = encoding
    ftp.login()  # anônimo
    return ftp


def baixar(
    url: str,
    destino: Path,
    *,
    encoding: str = "utf-8",
    conectar=None,
    tamanho_bloco: int = TAMANHO_BLOCO,
) -> Path:
    """Baixa um arquivo por FTP, retomando o `.parcial` anterior se houver."""
    conectar = conectar or _conectar_real
    host, diretorio, arquivo = partes_da_url(url)

    parcial = caminho_parcial(destino)
    parcial.parent.mkdir(parents=True, exist_ok=True)
    ja_tenho = parcial.stat().st_size if parcial.exists() else 0

    ftp = conectar(host, encoding=encoding, timeout=TIMEOUT)
    try:
        ftp.cwd(diretorio)
        ftp.voidcmd("TYPE I")  # SIZE só é confiável em modo binário
        esperado = ftp.size(arquivo)

        with open(parcial, "ab" if ja_tenho else "wb") as saida:
            ftp.retrbinary(
                f"RETR {arquivo}",
                saida.write,
                blocksize=tamanho_bloco,
                rest=ja_tenho or None,
            )
    finally:
        # sessão FTP vazada fica pendurada no servidor e consome slot anônimo
        try:
            ftp.quit()
        except Exception:  # noqa: BLE001 — encerrar é melhor esforço
            ftp.close()

    baixado = parcial.stat().st_size
    if esperado is not None and baixado != esperado:
        raise RuntimeError(
            f"download incompleto de {url}: {baixado} bytes, esperados {esperado} "
            "— o parcial foi preservado para a próxima tentativa"
        )

    parcial.replace(destino)
    return destino


def parsear_linha(linha: str) -> dict | None:
    """Uma linha de `LIST` → `{nome, tamanho}`; None para diretório ou lixo.

    DataSUS e PDET respondem no formato MS-DOS (`MM-DD-AA HH:MMAM  tamanho  nome`),
    não no Unix que se costuma assumir. O nome pode ter espaços e acentos — o PDF
    "Comunicado - Grupamento de Atividades Econômicas.pdf" tem os dois —, então o
    corte é por número de campos, nunca por espaço solto.
    """
    if not linha or not linha.strip():
        return None

    if linha[0] in "-dbclps" and len(linha.split()) >= 9:  # formato Unix
        campos = linha.split(maxsplit=8)
        if linha[0] == "d":
            return None
        try:
            return {"nome": campos[8], "tamanho": int(campos[4])}
        except ValueError:
            return None

    campos = linha.split(maxsplit=3)  # formato MS-DOS
    if len(campos) < 4 or not DATA_MS_DOS.match(campos[0]):
        return None
    if campos[2] == "<DIR>":
        return None
    try:
        return {"nome": campos[3].strip(), "tamanho": int(campos[2])}
    except ValueError:
        return None


def listar(url_diretorio: str, *, encoding: str = "utf-8", conectar=None) -> list[dict]:
    """Arquivos de um diretório FTP: `[{nome, tamanho}]`. Diretórios ficam de fora."""
    conectar = conectar or _conectar_real
    partes = urlparse(url_diretorio)
    caminho = unquote(partes.path) or "/"

    ftp = conectar(partes.hostname, encoding=encoding, timeout=TIMEOUT)
    linhas: list[str] = []
    try:
        ftp.cwd(caminho)
        ftp.retrlines("LIST", linhas.append)
    finally:
        try:
            ftp.quit()
        except Exception:  # noqa: BLE001
            ftp.close()

    itens = [parsear_linha(linha) for linha in linhas]
    return [item for item in itens if item]
