"""Infraestrutura compartilhada dos pipelines.

O `.env` é carregado aqui, no import do pacote, e não dentro de um módulo
específico: assim qualquer `python -m pipelines.*` enxerga as credenciais.
Quando isso morava só em config.py, um módulo que não importasse config rodava
sem credencial nenhuma e acusava chave ausente com a chave no lugar.
"""

from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[2]

load_dotenv(RAIZ / ".env")  # credenciais locais (gitignored); no CI vêm de Secrets
