"""Bundles de CA por fonte, para servidores que não mandam a cadeia completa.

Caso real: `download.inep.gov.br` envia só o certificado folha, sem o
intermediário. Navegador busca o intermediário sozinho (AIA fetching); Python
não faz isso e recusa a conexão.

A saída é completar a cadeia com o intermediário versionado em `config/ca/`,
**nunca** `verify=False`. O sha256 que gravamos é calculado do que baixamos:
ele detecta corrupção de transporte, mas não denunciaria conteúdo trocado por
um intermediário malicioso. Desligar a verificação transformaria o espelho —
cuja razão de existir é ser cópia fiel — em cópia de procedência incerta.

Para renovar um certificado vencido: a URI de CA Issuers está na extensão AIA
do certificado do servidor (`openssl s_client -connect host:443 | openssl x509
-text | grep -A2 'Authority Information Access'`).
"""

import tempfile
from functools import lru_cache
from pathlib import Path

import certifi

from pipelines.common.config import RAIZ


@lru_cache(maxsize=8)
def bundle(ca_extra: str | None = None) -> str:
    """Caminho de um bundle com o certifi + o PEM extra da fonte (se houver)."""
    if not ca_extra:
        return certifi.where()

    caminho = Path(RAIZ) / ca_extra
    if not caminho.exists():
        raise FileNotFoundError(
            f"certificado declarado em fontes.yaml não existe: {ca_extra} (procurei em {caminho})"
        )

    with tempfile.NamedTemporaryFile(
        "w", suffix=".pem", delete=False, encoding="ascii", prefix="praca-ca-"
    ) as combinado:
        combinado.write(Path(certifi.where()).read_text(encoding="ascii"))
        combinado.write("\n")
        combinado.write(caminho.read_text(encoding="ascii"))
        return combinado.name
