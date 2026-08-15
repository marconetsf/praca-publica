---
name: rodar-local
description: Como levantar o ambiente do Praça Pública na máquina — venv, testes, pipelines contra dados locais ou R2, e o servidor do site. Use quando pedirem para rodar, subir, servir, testar localmente, ver o site no navegador, ou quando aparecer erro de ambiente (venv, variável não encontrada, caminho, encoding). Cobre Windows (máquina atual) e Linux/macOS lado a lado.
---

# Rodar o Praça Pública localmente

> **A máquina de desenvolvimento atual é Windows 11 com PowerShell.** Todo comando aparece
> em duas versões. O CI roda `ubuntu-latest`, então o código é exercitado em Linux a cada PR —
> mas os comandos de terminal deste documento diferem, e é aí que se perde tempo.

## 1. Ambiente Python

Python **3.14**. No Windows a instalação é `pythoncore-3.14-64` em
`C:\Users\<você>\AppData\Local\Python\`.

**Windows (PowerShell)**
```powershell
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

**Linux / macOS**
```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Se `Activate.ps1` for bloqueado por política de execução:
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.

## 2. Testes e lint

Iguais nos dois sistemas — rodam sem rede.

```bash
pytest -q                 # suíte padrão
pytest -q -m live         # smoke tests contra APIs reais (fora do CI)
ruff check . ; ruff format .
```

`pytest` sozinho não toca a rede nem o R2: o `tests/conftest.py` neutraliza
`PRACA_DATA_ROOT` e `PRACA_RAW_ROOT` justamente para que um `.env` apontando para produção
não faça a suíte escrever nos buckets.

## 3. Onde os dados vão parar

Sem variável de ambiente, tudo cai em `data/` local. Com as variáveis, vai para o R2.

**Windows (PowerShell)** — a variável vale só na sessão atual:
```powershell
$env:PRACA_RAW_ROOT  = "s3://praca-raw"
$env:PRACA_DATA_ROOT = "s3://praca-dados"
Remove-Item Env:\PRACA_RAW_ROOT        # para voltar ao local
```

**Linux / macOS**
```bash
export PRACA_RAW_ROOT=s3://praca-raw
export PRACA_DATA_ROOT=s3://praca-dados
unset PRACA_RAW_ROOT
```

Prefixar a variável na mesma linha (`VAR=x comando`) **funciona em bash e não existe em
PowerShell** — no Windows é sempre atribuir antes, em comando separado.

As credenciais vêm do `.env` na raiz (gitignored), carregado por `pipelines/common/__init__.py`.
Qualquer `python -m pipelines.*` já enxerga.

## 4. Rodar os pipelines

```bash
python -m pipelines.siconfi.ingest_entes                      # dimensão de entes (5.598)
python -m pipelines.siconfi.ingest_dca --exercicio 2024 --uf RR
python -m pipelines.watcher.sonda                             # sonda as fontes
python -m pipelines.espelho.espelhar --fonte inep             # espelho defensivo
python -m pipelines.marts.dim_municipio                       # dimensão do mart
python -m pipelines.marts.fato_indicador --ano 2024           # fato + comparação
```

Ordem importa: `ingest_entes` antes de `ingest_dca`; `dim_municipio` antes de `fato_indicador`.

**Rodar de rede brasileira quando envolver o INEP.** `download.inep.gov.br` recusa conexão de
datacenter — o espelho e a ingestão do INEP falham no GitHub Actions e funcionam daqui. Ver
`docs/ESTADO.md` §5.

## 5. Servir o site

O site é **Astro SSG**: o build lê os JSONs de `site/public/dados/` e embute o conteúdo no
HTML. Nada é buscado em runtime para ler a página.

**Pré-requisito: os dados precisam existir.** O build falha com mensagem explícita se
`busca.json` não estiver lá.

```bash
# 1. gerar os dados (Python, a partir dos marts)
python -m pipelines.marts.dim_municipio
python -m pipelines.marts.fato_indicador --ano 2024
python -m pipelines.marts.serving --ano 2024      # → site/public/dados/

# 2. instalar e servir (Node 22+)
cd site
npm install
npm run dev            # desenvolvimento, recarrega ao salvar → localhost:4321
npm run build          # gera dist/
npm run preview        # serve o dist/ como em produção
```

### Acessar de outra máquina (Meshnet, rede local)

`dev` e `preview` escutam só em localhost por padrão. Os alvos `:rede` acrescentam `--host`:

```bash
npm run dev:rede
npm run preview:rede
```

O Astro imprime todos os endereços. Numa máquina com NordVPN Meshnet ativo, o IP da faixa
**`10.5.0.x`** é o que responde de fora:

```
┃ Local    http://localhost:4321/
┃ Network  http://10.5.0.2:4321/      ← Meshnet
┃          http://192.168.0.20:4321/  ← rede local
```

**Windows**: a primeira execução com `--host` costuma abrir o alerta do Firewall — é preciso
autorizar, senão só o `localhost` responde. Para checar sem interface gráfica:

```powershell
Get-NetFirewallRule -DisplayName "*Node*" | Select-Object DisplayName, Enabled, Direction
Test-NetConnection -ComputerName 10.5.0.2 -Port 4321
```

**Linux/macOS**: normalmente não há firewall bloqueando porta alta local. Se houver:
`sudo ufw allow 4321/tcp`.

### Rotas do MVP

| Rota | O que é |
|---|---|
| `/` | busca — lista os municípios com dado, filtro client-side |
| `/municipio/{uf}/{slug}` | página do município (ex.: `/municipio/rr/boa-vista`) |
| `/dados/municipio/{codigo}.json` | o JSON bruto, servido direto de `public/` |

### Servidor que precisa sobreviver à sessão do agente

Se um agente subir o servidor como tarefa em background, ele **é encerrado a cada ciclo do
harness** — a pessoa fica testando no celular e a página morre no meio. Para servidor que
precisa durar, subir destacado:

```powershell
$p = Start-Process npm.cmd -ArgumentList "run","preview:rede" `
     -WorkingDirectory "C:\...\praca_publica\site" -WindowStyle Minimized -PassThru
"PID: $($p.Id)"     # guarde para encerrar depois
```

**Linux/macOS**: `nohup npm run preview:rede > /tmp/praca-site.log 2>&1 &`

### Encerrar o servidor

**Windows**: `Ctrl+C` no terminal; se ficou órfão em background,
`Get-Process node | Stop-Process`.
**Linux/macOS**: `Ctrl+C` ou `pkill -f "astro preview"`.

### Limite conhecido do acesso por Meshnet

Serve para você e para quem está na sua rede mesh. **Não serve para validar o preview de link
no WhatsApp** — o crawler do WhatsApp não alcança IP privado, e o preview é a hipótese central
do produto (PRODUTO §1). Para isso é preciso URL pública: Cloudflare Pages (a decisão do
ESCOPO), ou um túnel temporário (Cloudflare Tunnel, Tailscale Funnel, ngrok).

## 6. Armadilhas específicas de Windows

| Sintoma | Causa | Saída |
|---|---|---|
| `s3:/praca-raw/...` com uma barra só | `Path()` colapsa `//` no Windows | nunca passar URI `s3://` por `Path`; usar `parquet._posix()` |
| Acentos saem quebrados no terminal | console em CP-1252 | `chcp 65001` ou usar Windows Terminal |
| `&&` dá erro de parser | PowerShell 5.1 não tem pipeline chain | usar `;` ou `if ($?) { ... }` |
| Comando parece falhar com saída normal | PowerShell trata `stderr` de exe como erro | conferir o exit code, não a presença de stderr |
| Heredoc não funciona | sintaxe bash | usar here-string `@'...'@` com `'@` na coluna 0 |
| `git commit -m` com múltiplas linhas | quoting | usar here-string ou `-F -` via Bash |

## 7. Verificação rápida (o "está tudo de pé?")

```bash
pytest -q                                  # 222 testes, sem rede
python -m pipelines.watcher.sonda          # sonda as fontes reais
```

O watcher é o melhor teste de fumaça: bate em 10 fontes reais e não escreve nada de
irreversível. Se ele passa, rede, `.env`, storage e parquet estão funcionando.
