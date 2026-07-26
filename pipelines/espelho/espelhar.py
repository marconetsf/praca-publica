"""Espelhamento defensivo: URL pública → cópia imutável na raw, com sha256.

Por que existe (ESCOPO M0.5, FONTES §7): o INEP apagou séries em 2022 e nunca
republicou completas; a série do SNIS saiu do ar. Dado público some — e 2026 é
ano eleitoral. O espelho é a única garantia de reprodutibilidade.

Premissas do desenho, todas vindas de como esses servidores realmente falham:
- o download cai no meio de arquivos de 1 GB → retomada por Range, o parcial
  sobrevive à falha e a próxima execução continua de onde parou;
- o servidor pode ignorar o Range → detectamos pelo status e recomeçamos, em vez
  de concatenar bytes errados e gerar um espelho corrompido;
- o servidor pode truncar a resposta → conferimos contra o Content-Length
  declarado e falhamos ruidosamente (regra 4: dado suspeito não é promovido).

Uso:
    python -m pipelines.espelho.espelhar --fonte inep --url https://.../censo.zip
    python -m pipelines.espelho.espelhar --fonte inep       # usa `espelho:` do YAML
    python -m pipelines.espelho.espelhar --todas
"""

import argparse
import tempfile
import time
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

from pipelines.common import alertas, manifest, storage, tls
from pipelines.common.config import fonte as carregar_fonte
from pipelines.common.config import fontes as carregar_fontes
from pipelines.common.http import UA

TAMANHO_BLOCO = 1 << 20  # 1 MiB
TIMEOUT = (30, 300)  # (conexão, leitura): arquivo grande demora entre blocos
TENTATIVAS = 5
ESPERA_INICIAL = 3.0  # segundos, dobrando a cada tentativa


def nome_do_arquivo(url: str) -> str:
    nome = unquote(Path(urlparse(url).path).name)
    if not nome:
        raise ValueError(f"não dá para deduzir o nome do arquivo em {url} — informe --nome")
    return nome


def caminho_parcial(destino: Path) -> Path:
    return destino.with_suffix(destino.suffix + ".parcial")


def requisitador(ca_extra: str | None = None):
    """Downloader real; `ca_extra` completa a cadeia TLS de servidores mal configurados."""
    verificacao = tls.bundle(ca_extra)

    def requisitar(url: str, *, headers: dict | None = None):
        return requests.get(
            url,
            headers={"User-Agent": UA, **(headers or {})},
            stream=True,
            timeout=TIMEOUT,
            verify=verificacao,
        )

    return requisitar


def baixar(
    url: str,
    destino: Path,
    *,
    requisitar=None,
    tamanho_bloco: int = TAMANHO_BLOCO,
    tentativas: int = TENTATIVAS,
    espera: float = ESPERA_INICIAL,
) -> Path:
    """Baixa `url` para `destino`, com retomada e novas tentativas em queda de rede.

    Resume e retry se completam: cada tentativa retoma do `.parcial`, então uma
    conexão que cai no byte 900 MB não joga fora o que já veio.
    """
    ultima: Exception | None = None
    for tentativa in range(tentativas):
        try:
            return _baixar_uma_vez(url, destino, requisitar=requisitar, tamanho_bloco=tamanho_bloco)
        except (OSError, ConnectionError) as exc:
            # falha de transporte: o parcial sobreviveu, a próxima tentativa continua
            ultima = exc
            if espera:
                time.sleep(espera * (2**tentativa))
    raise ultima  # type: ignore[misc]


def _baixar_uma_vez(
    url: str, destino: Path, *, requisitar=None, tamanho_bloco: int = TAMANHO_BLOCO
) -> Path:
    requisitar = requisitar or requisitador()
    parcial = caminho_parcial(destino)
    parcial.parent.mkdir(parents=True, exist_ok=True)

    ja_tenho = parcial.stat().st_size if parcial.exists() else 0
    cabecalhos = {"Range": f"bytes={ja_tenho}-"} if ja_tenho else None

    with requisitar(url, headers=cabecalhos) as resposta:
        retomando = resposta.status_code == 206
        if ja_tenho and not retomando:
            # servidor ignorou o Range: concatenar corromperia o arquivo
            ja_tenho = 0
        declarado = resposta.headers.get("Content-Length")
        modo = "ab" if retomando and ja_tenho else "wb"

        with open(parcial, modo) as arquivo:
            for bloco in resposta.iter_content(chunk_size=tamanho_bloco):
                arquivo.write(bloco)

    baixado = parcial.stat().st_size
    esperado = int(declarado) + ja_tenho if declarado is not None else None
    if esperado is not None and baixado != esperado:
        raise RuntimeError(
            f"download incompleto de {url}: {baixado} bytes, esperados {esperado} "
            "— o parcial foi preservado para a próxima tentativa"
        )

    parcial.replace(destino)  # só vira arquivo final quando está íntegro
    return destino


def espelhar(
    fonte: str,
    url: str,
    *,
    nome: str | None = None,
    coleta: date | None = None,
    requisitar=None,
    tentativas: int = TENTATIVAS,
    espera: float = ESPERA_INICIAL,
) -> dict:
    """Copia a URL para a raw da fonte e registra hash e tamanho no manifesto."""
    nome = nome or nome_do_arquivo(url)
    chave = f"espelho/{fonte}/{nome}"
    if manifest.ja_processado(chave):
        return {"pulado": True, "chave": chave}

    with tempfile.TemporaryDirectory(prefix="praca-espelho-") as temporario:
        local = baixar(
            url,
            Path(temporario) / nome,
            requisitar=requisitar,
            tentativas=tentativas,
            espera=espera,
        )
        # hash e subida por streaming: o alvo do espelho são arquivos de GBs
        sha256 = manifest.sha256_arquivo(local)
        tamanho = local.stat().st_size
        destino = storage.caminho_raw(fonte, nome, coleta=coleta)
        storage.enviar_arquivo(local, destino)

    manifest.registrar(chave, url=url, destino=destino, sha256=sha256, bytes=tamanho)
    return {
        "pulado": False,
        "chave": chave,
        "destino": destino,
        "sha256": sha256,
        "bytes": tamanho,
    }


def alvos_do_catalogo(fontes: dict) -> list[tuple[str, str]]:
    """Pares (fonte, url) declarados em `espelho:` no fontes.yaml."""
    alvos = []
    for fonte, config in fontes.items():
        if not isinstance(config, dict):
            continue
        for url in config.get("espelho") or []:
            alvos.append((fonte, url))
    return alvos


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fonte", help="Nome da fonte no fontes.yaml (ex.: inep)")
    parser.add_argument("--url", help="URL única; sem ela, usa a lista `espelho:` da fonte")
    parser.add_argument("--nome", help="Nome do arquivo na raw (padrão: o nome da URL)")
    parser.add_argument("--todas", action="store_true", help="Espelha todas as fontes do YAML")
    args = parser.parse_args()

    if args.url:
        if not args.fonte:
            raise SystemExit("--url exige --fonte")
        alvos = [(args.fonte, args.url)]
    else:
        catalogo = alvos_do_catalogo(carregar_fontes())
        alvos = catalogo if args.todas else [a for a in catalogo if a[0] == args.fonte]
        if not alvos:
            raise SystemExit(
                f"nada a espelhar: declare `espelho:` em config/fontes.yaml para '{args.fonte}' "
                "ou use --todas"
            )

    with alertas.falhas_alertadas(f"espelho/{args.fonte or 'todas'}"):
        for fonte, url in alvos:
            # servidor com cadeia TLS incompleta declara o intermediário no YAML
            ca_extra = carregar_fonte(fonte).get("tls_ca")
            resultado = espelhar(
                fonte,
                url,
                nome=args.nome if args.url else None,
                requisitar=requisitador(ca_extra),
            )
            if resultado["pulado"]:
                print(f"já espelhado: {resultado['chave']}")
            else:
                mb = resultado["bytes"] / 1e6
                print(f"{resultado['chave']}: {mb:.1f} MB -> {resultado['destino']}")


if __name__ == "__main__":
    main()
