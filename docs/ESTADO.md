# Estado atual e fila de trabalho

> **Comece por aqui.** Este arquivo diz onde o projeto parou e o que fazer em seguida.
> Última atualização: **27/07/2026**. Se a data estiver velha, confirme os fatos abaixo
> antes de confiar neles (`gh run list`, `git log`, e o manifesto no R2).

## 1. Onde paramos

Repositório: **[marconetsf/praca-publica](https://github.com/marconetsf/praca-publica)** (público).
Main protegida: **PR obrigatório** (0 aprovações, CI verde, sem force-push). Nunca commitar direto.

| Marco | Estado |
|---|---|
| **M0.1–M0.7** | ✅ código completo e validado contra os serviços reais |
| **M0 "pronto"** | ⏳ falta o watcher acumular **3 dias seguidos de execução agendada** |
| **M0.5 onda 1** (prazo 30/09) | 🟡 INEP espelhado; **SNIS abandonado** com justificativa (ver §4) |
| **M0.5 onda 2** (prazo 30/11) | 🟡 DataSUS espelhado; falta CAGED/RAIS e séries SICONFI |
| **M1 em diante** | ❌ não começou |

### O que roda sozinho hoje

| Workflow | Gatilho | O que faz |
|---|---|---|
| `ci.yml` | PR + push na main | ruff + pytest (~20 s) |
| `ingest-mensal.yml` | dia 5, 03:00 BRT | SICONFI entes → R2; DCA por `workflow_dispatch` |
| `watcher-fontes.yml` | diário, 06:00 BRT | sonda 9 fontes, alerta mudança/queda |
| `espelho-defensivo.yml` | só `workflow_dispatch` | espelha o que está em `espelho:` no YAML |

### O que já está no R2 (verificado em 27/07/2026)

- `praca-raw`: **2,07 GB** — INEP (7 arquivos, 190 MB), DataSUS (14, 1.883 MB), 1 arquivo de teste do CAGED
- `praca-dados`: staging do SICONFI (entes nacional; DCA de RR e AP), `catalog/manifest.json`, `catalog/watcher_state.json`
- Free tier do R2: 10 GB — há folga, mas ver §3

## 2. Fila de trabalho, em ordem

### 1. Confirmar o M0 como pronto — sem código, só verificação
O watcher rodou **uma vez, por disparo manual** (26/07). **Nenhuma execução agendada até 27/07.**
A contagem começa na primeira execução do cron. Verificar com:

```bash
gh run list --workflow="Watcher de fontes" --event schedule
```

Três execuções agendadas consecutivas e bem-sucedidas fecham o critério do ESCOPO §3.
Se o cron não disparar (o Actions pula execuções silenciosamente), é sintoma — e é exatamente
o que o healthchecks.io existe para detectar (§3).

### 2. Terminar a onda 2 do M0.5 — prazo 30/11/2026
1. **CAGED 2026** já está declarado no `fontes.yaml`, ~280 MB, é só rodar:
   ```bash
   gh workflow run "Espelho defensivo" --ref main -f fonte=rais_caged
   ```
2. **RAIS 2024** ainda **não** está declarada: 3,7 GB em 9 arquivos, um deles de 1 GB
   (`RAIS_VINC_PUB_SP.7z`). Declarar em `rais_caged.espelho` e rodar em execução dedicada.
   Caminho: `ftp://ftp.mtps.gov.br/pdet/microdados/RAIS/2024/`
3. **Séries SICONFI** — terceiro item da onda 2, ainda não desenhado. Diferente dos outros:
   é API JSON, não arquivo, então não passa pelo espelhador atual. Decidir se vira ingestão
   histórica (M1.2) em vez de espelho.

### 3. M1.1 — contratos e a dívida do `cod_ibge`
Antes de qualquer ingestão nova. Inclui a **violação da regra 2** que está aberta: o
`cod_ibge` é gravado como **BIGINT** no staging do SICONFI, e a regra exige `VARCHAR(7)`
(zeros à esquerda). Corrigir junto com os contratos YAML e o gate raw→staging.

### 4. M1.2 em diante
SICONFI nacional → IBGE → INEP (sobre o espelho já feito) → DataSUS (idem) → ANEEL → CAGED.
Ver ESCOPO §3.

## 3. Pendências que dependem do usuário

| O quê | Por que importa |
|---|---|
| **Espelho Backblaze B2** com Object Lock | O R2 **não tem versionamento**. Os 2 GB de acervo de resgate têm **uma única cópia**: token vazado ou comando errado apaga sem recuperação. O SNIS provou nesta sessão que a origem some. |
| **healthchecks.io** (2 checks) | Secrets `HEALTHCHECK_URL` (ingest) e `HEALTHCHECK_WATCHER_URL` (watcher) — os workflows já os consomem condicionalmente. O Telegram cobre job que *falhou*, não job que *nem rodou*. |

## 4. Decisões tomadas (não reabrir sem motivo novo)

- **SNIS fora da onda 1.** Série histórica inacessível por todos os caminhos: DNS morto,
  403 de appliance nos domínios `cidades.gov.br`, e o catálogo federal (consultado **com
  chave de API**) tem só um recurso HTML apontando para o host morto. Detalhes em
  `FONTES.md` §7 e `config/fontes.yaml → snis`. Sobrariam download manual ou Base dos Dados.
- **Nunca `verify=False`.** O TLS do INEP foi resolvido com o intermediário versionado em
  `config/ca/inep.pem`. O sha256 que gravamos é do que baixamos — não detectaria conteúdo
  trocado no caminho.
- **Não contornar WAF.** O 403 do `cidades.gov.br` não é User-Agent; driblar por fingerprint
  ou proxy seria evasão, e não entra neste projeto.
- **Espelho não é agendado.** É ato pontual de resgate; a lista de alvos vive no YAML.
- **Sonda declarada por fonte.** Sondar `api_base` cru acusou 9 de 15 fontes como caídas sem
  nenhuma estar fora do ar. Ver a convenção no `CLAUDE.md`.

## 5. Armadilhas já encontradas (não repetir)

- O `LIST` do FTP do DataSUS e do PDET vem em **formato MS-DOS**, não Unix.
- O FTP do MTPS devolve **nomes de arquivo em latin-1** (`ftp_encoding` no YAML).
- `Path("s3://…")` no Windows vira `s3:/…` — nunca passar URI s3 por `Path`.
- `load_dotenv` mora no `__init__` de `pipelines/common` — não recolocar em módulo solto.
- A API do `dados.gov.br` usa header `chave-api-dados-abertos`; o Portal da Transparência usa
  `chave-api-dados`, sem o sufixo.
- Testes que esperam falha de rede precisam de `tentativas=1, espera=0`, senão a suíte dorme.
