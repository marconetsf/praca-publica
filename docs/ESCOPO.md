# Escopo de Desenvolvimento — Praça Pública

> Documento-mestre da fase de especificação, fechado em 26/07/2026.
> Detalhes por área: [ARQUITETURA.md](ARQUITETURA.md) · [PRODUTO.md](PRODUTO.md) ·
> [CRESCIMENTO.md](CRESCIMENTO.md) · [SEGURANCA.md](SEGURANCA.md) · [OPERACAO.md](OPERACAO.md) ·
> catálogo de fontes em [../FONTES.md](../FONTES.md).

## 1. Visão

Transformar dados públicos brasileiros em informação que o cidadão comum entende e compartilha.
Produto central: **a página do município** — "o raio-X da sua cidade" — distribuída principalmente
via WhatsApp, onde **o preview do link é a mensagem** (número + comparação + fonte, sem exigir clique).

**Princípios inegociáveis:**
1. Todo número tem fonte + data de referência + data de coleta.
2. Nenhum número sem comparação ("cidades parecidas": mesmo porte + mesma região, mediana).
3. Dado ausente ≠ zero; ausência é informação e aparece como tal.
4. Descritivo, nunca prescritivo — sem juízo de valor sobre gestões; sem nomes de políticos na v1.
5. Nenhum dado individual de pessoa física; agregados com n ≥ 5; CPF jamais.
6. Erro publicado gera errata pública — nunca correção silenciosa.

## 2. Decisões de arquitetura consolidadas

| Área | Decisão | Doc |
|---|---|---|
| Armazenamento | Parquet (zstd) hive-partitioned + manifesto; sem Iceberg/DuckLake | ARQUITETURA §1 |
| Chave canônica | `codigo_municipio_ibge` VARCHAR(7) em todas as tabelas | ARQUITETURA §1 |
| Cloud | **Cloudflare R2** (egress $0) + GitHub Actions (repo público, grátis); VPS Hetzner `heavy` só na Fase 2 (CNPJ) | ARQUITETURA §2 |
| Serving | JSONs estáticos pré-computados atrás do CDN; **sem API com servidor**; DuckDB-WASM só como "explorador" cortável | ARQUITETURA §3 |
| Marts | Fato longo município×ano×indicador; metodologia versionada em `dim_indicador` | ARQUITETURA §4 |
| Frontend | **Astro SSG + Cloudflare Pages** (zero JS para ler; banda ilimitada) | PRODUTO §6 |
| OG images | Sob demanda: Satori em Cloudflare Workers + cache CDN + versão do dado na URL (`?v=2026-06`) | CRESCIMENTO §2 |
| Analytics | **Umami self-hosted desde o lançamento público** (cloud free só no soft launch — 100k eventos/mês não sobrevive a pico viral); script proxiado pelo próprio domínio (CSP estrita) | CRESCIMENTO §6 |
| Orquestração | GitHub Actions até a Fase 2; Dagster OSS no VPS quando ≥ 2 gatilhos objetivos dispararem | OPERACAO §1 |
| Qualidade | Contratos de schema YAML (gate raw→staging) + sanidade estatística (gate staging→marts), caseiros em DuckDB | OPERACAO §3 |
| Alertas | Telegram (3 severidades) + healthchecks.io (dead-man switch) | OPERACAO §1 |
| Repo | Monorepo `pipelines/` + `site/` + `contracts/` | OPERACAO §2 |
| Custo | ~US$ 5–21/mês em qualquer cenário, inclusive pico viral (Workers Paid US$ 5 entra no M3 para as OG images) | ARQUITETURA §5 |

Divergências entre frentes, resolvidas assim:
- *OG no build vs sob demanda*: sob demanda (130 mil imagens/ciclo no build seria desperdício; cache por URL versionada resolve o cache sem purge do WhatsApp).
- *Analytics Cloudflare vs Umami*: Umami — eventos custom de share são a métrica-mãe do produto e o Cloudflare Web Analytics não os cobre.
- *CNPJ no Actions vs VPS*: VPS self-hosted runner (o processamento arquivo-a-arquivo até caberia, mas viraria 37 jobs frágeis contra servidor instável).

**Revisão adversarial aplicada em 26/07/2026** — correções relevantes já incorporadas aos docs: R2 não tem versionamento de objetos nem OIDC do GitHub (imutabilidade garantida pelo espelho B2; tokens R2 escopados por bucket); páginas de comparação não são pré-renderizadas (limite de 20k arquivos do Pages); mart ganhou `mediana_grupo`/`slug`/`faixa_porte` (o schema não cobria a feature central); Workers Paid (US$ 5) entra no custo a partir do M3; denominador do limite de pessoal é a RCL; "mediana/típico" padronizado no texto público; régua de comparação unificada em PRODUTO §2 regra 3.

## 3. Roadmap (1 dev + IA, ~10 h/semana ≈ 1,25 dia-pessoa/semana)

| Marco | Épico | Esforço | Calendário |
|---|---|---|---|
| **M0** | Fundações: cloud-ready + CI | 7 dp | ago → meados set/2026 |
| **M0.5** | **Espelhamento defensivo pré-eleição** ⚠️ prazo duro | 3 dp | até 30/11/2026 |
| **M1** | Dados da Fase 1 completos (6 fontes, nacional) | 15 dp | set → dez/2026 |
| **M2** | Marts + ~12–15 indicadores | 8 dp | dez/2026 → fev/2027 |
| **M3** | Site MVP (5.570 páginas) | 12 dp | fev → abr/2027 |
| **M4** | Lançamento (soft → público) | 5 dp | abr → mai/2027 |
| **M5** | Fase 2: CNPJ × contratos | 22 dp | mai → out/2027 |
| | **Total (Fases 1–2)** | **72 dp** | **lançamento ~mai/2027** |
| **M6** | Fase 3: eixo parlamentar (§7) | ~20 dp | pós-M5, nunca antes |

### M0 — Fundações (7 dp)
0.1 `pyproject.toml` + ruff + pytest; extrair transformações dos `main()` para funções puras (1 dp)
0.2 Primeiros testes: manifest, config, transformação DCA com fixture (1 dp)
0.3 `ci.yml` + branch protection + Conventional Commits (0,5 dp)
0.4 `storage.py` (local ↔ R2 via fsspec, env `PRACA_DATA_ROOT`); buckets R2 + espelho B2 (versioning/Object Lock — o R2 não tem versionamento); retrofit da raw datada `raw/{fonte}/{AAAA-MM-DD}/` e da chave de manifesto com **janela de captura** (hoje um município sem DCA é pulado para sempre — entregas atrasadas nunca entrariam) (1,5 dp)
0.5 Bot Telegram + `alertas.py` + healthchecks.io (0,5 dp)
0.6 Primeiro workflow agendado: SICONFI no Actions → R2, ponta a ponta (1,5 dp)
0.7 Watcher v1: status + ETag para todas as fontes do YAML (1 dp)
**Pronto quando**: push roda lint+testes; SICONFI executa agendado sem tocar a máquina local; falha simulada chega no Telegram; watcher rodou 3 dias seguidos.

### M0.5 — Espelhamento defensivo (3 dp, em duas ondas)
0.5.1 Script genérico de espelhamento (URL → raw R2, resume, sha256) (1 dp)
0.5.2 **Onda 1 — até 30/09/2026** (antes das eleições de outubro, que é o risco que justifica o marco): INEP e histórico SNIS/SINISA — as fontes com precedente real de apagão (2 dp)
0.5.3 **Onda 2 — até 30/11/2026** (antes da troca de gestão de jan/2027): DataSUS alvo, CAGED/RAIS recentes, séries SICONFI
**Pronto quando**: todo dataset marcado "instável" no FONTES.md tem cópia raw no R2 com hash, nos prazos das ondas.

### M1 — Dados Fase 1 (15 dp)
1.1 `checks.py` + contratos YAML + gate raw→staging, retrofit no SICONFI (2 dp)
1.2 SICONFI nacional: DCA todas as UFs 2020–2025 + RREO corrente (2 dp)
1.3 IBGE: dim municípios, população, PIB municipal (2 dp)
1.4 INEP: Censo Escolar + IDEB (2,5 dp — trabalhar sobre o espelho de M0.5)
1.5 DataSUS agregado: CNES, SIM/SINASC via pysus (3 dp — maior folga: FTP instável)
1.6 ANEEL: DEC/FEC por município (1 dp)
1.7 Novo CAGED mensal (2 dp)
1.8 Watcher v2: fingerprint de schema + hash de listagens (0,5 dp)
**Pronto quando**: cada fonte tem staging nacional no R2, contrato versionado, workflow na cadência certa, cobertura ≥ limiar, 2 execuções sem intervenção.

### M2 — Marts (8 dp)
2.1 `dim_municipio` (1 dp) · 2.2 definição editorial dos indicadores com memória de cálculo (1,5 dp) · 2.3 `fato_indicador_municipio` + séries (2,5 dp) · 2.4 Gate 2 de sanidade (1,5 dp) · 2.5 freshness + SLAs (0,5 dp) · 2.6 dicionário público + snapshots versionados (1 dp)
**Pronto quando**: painel completo de qualquer município em 1 SELECT; **5 municípios conferidos manualmente contra as fontes**; falha de sanidade bloqueia publicação.

### M3 — Site MVP (12 dp)
3.1 Esqueleto Astro + Pages com preview por PR (1,5 dp) · 3.2 página municipal ×5.570 (4 dp) · 3.3 busca/home/hubs UF (1,5 dp) · 3.4 DuckDB-WASM comparador — *cortável* (2 dp) · 3.5 metodologia + limitações + LGPD (1,5 dp) · 3.6 deploy automático + acessibilidade mínima (1,5 dp)
**Pronto quando**: URL pública não divulgada com 5.570 páginas; Lighthouse ≥ 90 (performance e acessibilidade); mart atualizado reflete sem ação manual; toda cifra com fonte e data.

### M4 — Lançamento (5 dp)
4.1 Hardening: UptimeRobot, domínio, analytics, robots/sitemap (1 dp) · 4.2 soft launch com 10–20 pessoas, 2–3 semanas (1 dp) · 4.3 correções — números confusos antes de bugs de UI (2 dp) · 4.4 lançamento público + monitorar primeira onda (1 dp)
**Pronto quando**: ≥ 5 devolutivas tratadas; **zero erro conhecido de dado** (inegociável); uptime > 99% no soft launch; checklist de conformidade (SEGURANCA §6) 100%.

### M5 — Fase 2 (22 dp)
5.1 VPS + runner `heavy` + hardening (1,5 dp) · 5.2 pipeline dump CNPJ com resume/fallback espelho (5 dp) · 5.3 snapshot+diff mensal (3 dp) · 5.4 PNCP (3 dp) · 5.5 Portal da Transparência com token (2,5 dp) · 5.6 marts de cruzamento com LIA documentado (3,5 dp) · 5.7 "quem vende para a prefeitura" no site (2,5 dp) · 5.8 avaliar gatilhos Dagster (1 dp)
**Pronto quando**: ciclo CNPJ roda 2 meses sem intervenção; top fornecedores conferidos em 3 municípios; nenhum dado pessoal não-agregado publicado; RIPD e LIAs escritos ANTES da publicação.

## 4. Riscos de cronograma

| Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|
| Ano eleitoral: fontes fora do ar/apagadas perto de out/2026; troca de gestão muda URLs em 01/2027 | Alta | Alto | M0.5 com prazo duro; raw imutável; watcher; URLs centralizadas |
| Fonte instável estoura estimativa (DataSUS, PDET, Receita) | Alta | Médio | ordem do M1 dá folga às instáveis; espelhos; timebox 1,5× → corta para Should |
| 10 h/semana é otimista | Média | Alto | marcos incrementais, cada um termina utilizável; MoSCoW abaixo |
| Dump CNPJ com lote defeituoso (precedente real) | Média | Médio | sanidade entre meses; snapshot anterior para rollback |
| Mudança de layout (RAIS `.comt` etc.) | Média | Baixo | contrato falha ruidosamente; de-para versionado |
| Escopo do site cresce | Alta | Médio | MVP fechado em 3.1–3.6; resto vai para backlog pós-M4 |

## 5. MoSCoW — o que cortar se apertar

- **Must** (sem isso não há lançamento): M0, M0.5, SICONFI + IBGE nacionais, contratos de schema, mart com ~8 indicadores financeiros+demografia, página municipal + busca + metodologia, soft launch. ≈ **38 dp → lançamento reduzido possível em fev–mar/2027**.
- **Should** (corta primeiro, volta pós-launch): INEP e DataSUS (estreia só com finanças+demografia), freshness no site, DuckDB-WASM.
- **Could**: ANEEL e CAGED, comparador, snapshots públicos versionados.
- **Won't (até pós-M5)**: TSE/Querido Diário/CNEFE, **eixo parlamentar (§7)**, Dagster antecipado, mapas/geo, API pública própria.

## 6. Decisões pendentes (donas do usuário)

1. **Nome/domínio** ⚠️ bloqueante para marca: `pracapublica.com.br` registrado por terceiro em 11/06/2026. Opções: negociar; `pracapublica.org.br` (verificar disponibilidade; combina com projeto cívico); renomear. Busca INPI antes do lançamento. (CRESCIMENTO §7)
2. **Associação sem fins lucrativos antes da Fase 2** — separa patrimônio pessoal do risco cível de publicar empresa×contrato. Decisão de maior alavancagem jurídica do projeto. (SEGURANCA §2)
3. **Token da CGU** — cadastrar (conta gov.br Prata/Ouro) já; destrava a Fase 2 quando chegar.
4. **BD Pro (R$ 47/mês)** — só se a defasagem de 6 meses do free tier da Base dos Dados incomodar em alguma dimensão; não é necessário para o plano atual.

## 7. Fase 3 — eixo parlamentar (M6, ~20 dp)

> Registrado em 27/07/2026 a pedido da idealização do projeto. **Não é backlog imediato**: é a
> definição do que o eixo será *quando* for, para que a decisão não seja improvisada sob pressão
> e para que ninguém precise redesenhar a modelagem depois.

### 7.1 O que responde e por que é outro produto

O produto atual responde **"como está a minha cidade?"**. Este responde **"o que este parlamentar
fez com dinheiro e mandato?"**. Muda a unidade de análise, o público, o risco jurídico e a régua
de comparação — por isso é marco próprio, não uma aba a mais na página do município.

### 7.2 Grão e modelagem (a decisão técnica que evita retrabalho)

**A chave canônica do projeto não serve aqui.** Todo o mart da Fase 1 é ancorado em
`codigo_municipio_ibge`; parlamentar não tem município — tem UF, mandato que atravessa
legislaturas e partido que muda no meio do caminho. Consequência: **fato separado**, nunca uma
coluna a mais no fato municipal.

```sql
-- dim_parlamentar (SCD tipo 2: partido e situação mudam durante o mandato)
parlamentar_id VARCHAR PK,        -- id nativo da Câmara/Senado, nunca CPF
nome_parlamentar, nome_civil, casa VARCHAR,   -- 'camara' | 'senado'
uf, partido_sigla, legislatura INT,
vigencia_inicio DATE, vigencia_fim DATE,      -- troca de partido gera nova linha
codigo_candidato_tse VARCHAR                  -- de-para por id do TSE; JAMAIS por CPF

-- fato_indicador_parlamentar (compartilha dim_indicador com o eixo municipal)
parlamentar_id, periodo VARCHAR, indicador_id, versao_metodologia,
valor DOUBLE, valor_formatado VARCHAR,
mediana_grupo DOUBLE, n_grupo INT,            -- régua obrigatória, como no municipal
data_calculo TIMESTAMP, run_id VARCHAR

-- fato_emenda — A PONTE ENTRE OS DOIS EIXOS
parlamentar_id, codigo_municipio_ibge VARCHAR(7), ano SMALLINT,
funcao, valor_indicado, valor_empenhado, valor_pago
```

**`fato_emenda` é o ativo mais valioso deste marco**, e a razão de ele fazer sentido dentro deste
projeto e não em outro: emenda tem município de destino, então liga o eixo novo ao produto que já
existe — *"quem mandou dinheiro para a sua cidade, quanto foi indicado e quanto foi efetivamente
pago"*. Indicado ≠ empenhado ≠ pago é, por si só, informação que quase ninguém vê.

**Régua de comparação**: o grupo é `mesma casa + mesma UF + mesma legislatura` (análogo às
"cidades parecidas"), com mediana. Sem grupo definido, não publica — mesma regra do card municipal.

### 7.3 Fontes (todas já catalogadas ou de acesso conhecido)

| Fonte | O que traz | Estado |
|---|---|---|
| Câmara — `dadosabertos.camara.leg.br` | proposições, votações nominais, presença, cota parlamentar (CEAP) | catalogada, estável, sem token |
| Senado — `legis.senado.leg.br` | idem para senadores | catalogada, sem token |
| Portal da Transparência / SIOP | execução de emendas (indicado → empenhado → pago) | API já catalogada; **exige token CGU** |
| TSE | candidaturas anteriores, bens declarados, prestação de contas | **espelhar 2026 antes de dezembro** (ARQUITETURA §6) |

### 7.4 O que se publica — e o que não

**Publica-se fato com fonte e data**: presença em votações nominais, proposições apresentadas e
aprovadas, gasto da cota parlamentar por categoria, emendas indicadas × pagas por município,
evolução do patrimônio declarado entre eleições.

**Não se publica nota, score, ranking de mérito ou classificação "econômica/social".** A razão não
é timidez: uma nota é juízo de valor, colide com o princípio inegociável 4, atrai representação
eleitoral e — o efeito mais caro — faz o leitor desconfiar da metodologia de *todo* o site,
inclusive dos indicadores municipais que não têm nada a ver com política partidária. Ranking de
posição segue a regra 6 do PRODUTO §2: sempre com denominador e grupo, nunca "melhor/pior".

### 7.5 Portões de entrada (todos obrigatórios, sem exceção)

1. **M4 lançado e estável** — credibilidade é pré-requisito, não consequência.
2. **Associação sem fins lucrativos constituída** (§6 item 2) — publicar dado individual de pessoa
   pública com patrimônio pessoal exposto é risco cível desnecessário.
3. **RIPD + LIA escritos e revisados por advogado**, antes de uma linha de código de publicação.
   Dado de político é dado pessoal: a expectativa de privacidade é reduzida, não nula.
4. **Fora do período eleitoral** — de agosto à diplomação vale o congelamento do SEGURANCA §6.3.
5. **Anti-CPF ativo no CI** — a proibição de join QSA × TSE (regra 3) vale integralmente aqui, e é
   exatamente neste marco que ela fica tentadora de burlar.

### 7.6 Esforço e critério de pronto

~20 dp, estimativa grossa: dim + coleta Câmara (3) · Senado (2) · emendas com execução (4) ·
CEAP (2) · TSE bens e candidaturas (3) · marts e régua (3) · páginas e OG (3).

**Pronto quando**: um parlamentar tem página com no mínimo 5 indicadores, cada um com fonte, data
de referência e comparação de grupo; `fato_emenda` reconcilia com o Portal da Transparência em 3
municípios conferidos manualmente; nenhuma nota ou classificação de mérito publicada; RIPD e LIA
publicados junto com a estreia do marco.
