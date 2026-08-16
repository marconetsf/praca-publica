# Segurança, LGPD e Integridade Editorial

> Especificado em 26/07/2026. Complementa a seção de riscos do FONTES.md.

## 1. LGPD operacional

### Papel e enquadramento
- O projeto é **controlador** (art. 5º, VI); provedores de cloud/CDN são operadores (constam no registro de operações). Finalidade pública → LGPD aplica integralmente mesmo a pessoa física.
- **Invocar explicitamente o enquadramento de agente de pequeno porte** (Res. CD/ANPD nº 2/2022 — flexibiliza registro e comunicação de incidentes). Encarregado (DPO) = o mantenedor, com contato público no site.

### Base legal por categoria publicada

| Categoria | Dado pessoal? | Base legal |
|---|---|---|
| Agregados municipais (SICONFI, IBGE, DataSUS agregado) | Não | Fora do escopo — manter supressão n<5 |
| CNPJ: razão social, CNAE, situação | Não para PJ; **sim para MEI** (nome civil no nome da empresa) | Legítimo interesse + dado público (art. 7º, IX e §3º) |
| QSA (sócios) | **Sim** | Legítimo interesse **com LIA documentado**; nunca desmascar CPF; não exibir CPF nem mascarado |
| Contratos × CNPJ (PNCP/CGU) | Sim quando PF/MEI | Legítimo interesse + publicidade legal original (LAI, Lei 14.133 art. 94) |
| Sanções (CEIS/CNEP) | Sim | Legítimo interesse; **exibir sempre vigência** — sanção expirada exibida como vigente é o maior risco cível |
| Doações eleitorais (TSE) | Sim, CPF completo na fonte | **Não publicar microdado de doador PF na v1** — só agregados por candidato/partido |

### LIA (teste de legítimo interesse) — um por cruzamento, antes da Fase 2
`docs/lgpd/lia-{cruzamento}.md` com 4 blocos: finalidade (controle social do gasto público, art. 10, I), necessidade (minimização — nome e qualificação do sócio; **não** endereço, **não** CPF mascarado), balanceamento (expectativa: QSA é registro público por lei; mitigação de homônimos: nome sempre com CNPJ + UF), salvaguardas (canal de titular, atribuição, sem enriquecimento com dado não público).

### RIPD
Não obrigatório para agregados. **Fazer antes da Fase 2** (larga escala + legítimo interesse — art. 10, §3º permite à ANPD exigir; ter pronto é a defesa). 5–10 páginas, template ANPD para pequenos agentes. Incluir: por que o cruzamento QSA×TSE é proibido no pipeline, com verificação técnica (checklist item 3).

### Regras mecânicas no pipeline
- **Supressão de células pequenas: n < 5 como asserção no job de publicação** (DataSUS por causa × município pequeno reidentifica um óbito), não como convenção.
- **Verificação anti-CPF no CI**: teste que falha se coluna publicada casar regex de CPF completo ou se houver join QSA × bases com CPF completo (TSE).
- Registro de operações (art. 37): `docs/lgpd/registro-operacoes.md`, uma linha por operação (categorias, titulares, finalidade, base legal, origem, compartilhamento, retenção, segurança).

### Site (visitantes)
- **Analytics sem cookie/fingerprinting (Umami)** → sem banner de consentimento. Nunca GA4.
- Política de privacidade: o que coletamos (analytics agregado; logs CDN com IP ≤ 30 dias, legítimo interesse), o que NÃO coletamos (sem cadastro, sem tracking, sem venda), operadores, contato do encarregado.

### Canal de titular e takedown
E-mail `privacidade@` + formulário. Confirmação em 72 h, resposta em **15 dias** (art. 19, §1º). Fluxo para "sócio pede remoção":
1. Verificar identidade (takedown fraudulento é vetor de censura).
2. Classificar: **dado incorreto** → corrigir + errata (obrigação, art. 18, III); **correto e vigente** → a lei não obriga remoção; responder citando o LIA e oferecer nota de contexto (cortesia); **defasado** (saiu da sociedade, sanção expirou) → atualizar, antecipar manualmente se dano plausível; **risco concreto à pessoa** (medida protetiva) → remover/desindexar mantendo o CNPJ — cortesia adotada por padrão.
3. Registrar todo pedido e desfecho (accountability, art. 6º, X).
4. **`noindex` por padrão em páginas cujo título é nome de PF** — acessível, não googlável.

## 2. Fase 2 (empresas × contratos) — regras editoriais de risco

O risco real (aprendizado Serenata/Fiquem Sabendo): processos por difamação de citados, mesmo com dado público correto — **o custo é a defesa, não a condenação**. Cada página deve ser defensável em juízo por si só.

**Pode** (fato verificável com fonte primária linkada): "Empresa X firmou contrato Y de R$ Z com o município W em DD/MM (PNCP, id)"; "X consta no CEIS com sanção vigente de DD/MM a DD/MM"; "A sócia A da empresa X também é sócia da Y (QSA, competência AAAA-MM)".

**Não pode** (juízo de valor como dado): "suspeito", "fachada", "indício de fraude", "esquema", "laranja"; rankings valorativos ("os piores"); **correlação como causa** ("doou e ganhou contrato" como manchete — exibir os dois fatos lado a lado, datados, sem conector causal).

**Flags estatísticas**: nomear de forma neutra ("atípico") + disclaimer literal: *"Indicador estatístico, não acusação. Pode ter explicações legítimas. Verifique a fonte primária."*

Regras mecânicas (no template, geradas pelo pipeline):
1. Toda afirmação com link para fonte primária + data de extração.
2. Toda página de empresa exibe a defasagem ("Receita: competência AAAA-MM").
3. Sanção expirada sai da vitrine (fica no histórico marcado).
4. Homônimo: nome de sócio sempre com CNPJs — nunca página "Fulano" agregando pessoas distintas.
5. **Direito de resposta**: nota do citado publicada na íntegra (até 1.500 chars) em 5 dias úteis — desarma a maioria das notificações extrajudiciais.
6. Zero texto opinativo na plataforma de dados (análise, se houver, em rota separada com autoria).
7. Feature de "destaque" só após revisão com a pergunta: "um advogado do citado leria isso como acusação?"

**Blindagem**: snapshot raw imutável sustenta cada publicação (prova de boa-fé na data X); texto padrão de resposta a notificação extrajudicial; **avaliar constituir associação sem fins lucrativos antes da Fase 2** — separa o patrimônio pessoal do mantenedor do risco cível. É a decisão de maior alavancagem desta seção.

## 3. Segurança da infraestrutura

- **Segredos**: `.env` fora do git + `gitleaks` no pre-commit e CI (histórico completo, não só diff). Token CGU em GitHub Secrets, rotação semestral. **A Cloudflare não suporta OIDC federado do GitHub para R2** — usar **tokens de API do R2 escopados por bucket** (um por job: ingestão→`praca-raw`, transformação/publicação→`praca-dados`), guardados em GitHub **Environments** com rotação semestral documentada. `permissions:` mínimo em todo workflow; actions de terceiros pinnadas por SHA.
- **Buckets** (topologia única em ARQUITETURA.md §2): leitura pública só em `marts/latest/` e `serving/` de `praca-dados`, via CDN; `praca-raw` privado. **O R2 não tem versionamento de objetos nem token "sem delete"** — a proteção contra deleção/ransomware vem do espelho **B2 com versioning/Object Lock**; no R2 vale a convenção de prefixos datados nunca sobrescritos, verificada por teste no CI (tentar sobrescrever um objeto raw existente deve falhar no código do pipeline).
- **Integridade**: `SHA256SUMS` por release + manifesto (versão, extração por fonte, hash por arquivo, commit do pipeline) **assinados com minisign** (chave pública no site e no repo). GPG é overkill.
- **Backup 3-2-1** da raw: R2 (IA) + B2 (`rclone sync` mensal) + disco local como cópia de trabalho. Testar restauração 2×/ano (restaurar 1 mês de CNPJ e reprocessar). Prioridade 2026: INEP, SNIS histórico, dumps Receita, RAIS — antes de dezembro.
- **Dependências**: lockfile com `--frozen` no CI; Dependabot (auto-merge só patch de dev); `pip-audit`/`osv-scanner` no CI. Um token R2 por papel (ingestão / transformação / publicação), cada um restrito ao seu bucket. Nunca `pull_request_target` com checkout de fork.

## 4. Segurança do site

Headers (meta Mozilla Observatory ≥ A):
```
Content-Security-Policy: default-src 'self'; script-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
```
- Sem scripts de terceiros: o script e o endpoint de coleta do Umami são **servidos pelo próprio domínio via proxy** (rewrite no Pages/Worker) — mantém a CSP `script-src 'self'` estrita mesmo antes do self-host. A melhor decisão de segurança: **site estático, sem backend onde possível**.
- Cloudflare free: DDoS ilimitado, WAF básico, **1 regra de rate limit** → usá-la no único endpoint caro (busca, se sair do client-side na Fase 2: 30 req/10 s → challenge). Cache Everything + purge por deploy. Cuidado com Bot Fight Mode: pode bloquear reutilizadores legítimos dos dados.
- **Scraping do nosso site — postura: dados são abertos; scraping é desnecessário, não proibido.** Desincentivo: `/dados` com bulk download + checksums, linkado em todo rodapé; licença explícita (CC-BY; ODbL onde derivado de BCB/ANEEL) — clareza de licença transforma scraper em reutilizador.
- Pico viral: estático em CDN aguenta por construção. Runbook: (1) Under Attack Mode se L7 anormal; (2) desligar busca por feature flag; (3) bulk já está no R2, não no origin. Nunca expor IP de origin.

## 5. Integridade editorial como superfície de ataque

### Dado errado com a nossa marca
Cenário: número errado (a Receita já distribuiu lote defeituoso sem errata; ou nosso pipeline erra), print viraliza, correção não alcança o print.
- **Versionamento do dado exibido**: toda página mostra `release AAAA.MM.N` + data de extração; manifesto reconstitui o que estava no ar em qualquer data.
- **Pipeline de errata**: corrigir + registro público em `/erratas` (valor anterior → corrigido, causa, data) + banner "Corrigido em DD/MM" por 30 dias + **RSS de erratas** (jornalistas assinam). **Nunca corrigir silenciosamente.**
- Validação pré-publicação: variação > X% vs release anterior trava para revisão humana.
- Prints são incontroláveis; o que se controla é a **URL permanente e datada** para apontar como resposta.

### Captura política em 2026
1. **Mesma régua, mecanicamente**: todo ranking cobre todos os entes do recorte por critério declarado — nunca lista curada à mão (é onde a parcialidade entra).
2. Metodologia pública; mudanças só entre releases, datadas; **nunca no ciclo eleitoral**.
3. **Congelamento eleitoral**: de agosto à diplomação, nenhuma feature nova de destaque/ranking — só atualização de dados e correções. Mudança de vitrine em setembro será lida como ato político.
4. Sem nomes de políticos como eixo de navegação na v1; TSE só agregado.
5. **Financiamento transparente** ("quem paga a infra") — antecipa o ataque padrão "financiado por X".
6. Pedidos de destaque/remoção de campanhas: recusar por regra escrita e registrar.
7. Contas oficiais não endossam candidatos; separar voz pessoal do mantenedor da voz do projeto.

## 6. Checklist de conformidade pré-lançamento

1. [ ] `docs/lgpd/`: registro de operações, política de privacidade publicada, LIA por cruzamento (Fase 2: + RIPD).
2. [ ] Encarregado nomeado com contato público; `privacidade@` testado (pedido fake cronometrado).
3. [ ] Verificação anti-CPF automatizada no CI (regex em colunas publicadas + proibição de join QSA×TSE).
4. [ ] Supressão n<5 como asserção com teste.
5. [ ] Fonte + data de extração geradas pelo pipeline em toda página (inspecionar 5 aleatórias).
6. [ ] Analytics sem cookie confirmado (aba Network limpa).
7. [ ] `gitleaks detect` no histórico completo passa.
8. [ ] Tokens R2 escopados por bucket em GitHub Environments (rotação agendada); `permissions:` mínimo; actions pinnadas por SHA.
9. [ ] PUT anônimo e PUT com credencial de leitura falham no bucket público; espelho B2 com versioning/Object Lock ativo; pipeline recusa sobrescrever objeto raw existente (teste no CI).
10. [ ] `SHA256SUMS` + manifesto assinados (minisign) no último release.
11. [ ] Backup 3-2-1 ativo + **uma restauração testada**.
12. [ ] Mozilla Observatory ≥ A; HSTS; CSP sem `unsafe-inline` em script.
13. [ ] Rate limit da busca testado (estourar de propósito); origin não exposto.
14. [ ] `/dados` no ar com licença explícita e link em todas as páginas.
15. [ ] Publicados: metodologia, `/erratas` (com RSS, mesmo vazia), texto de direito de resposta, "quem financia".
16. [ ] Lockfile + Dependabot + zero vulnerabilidades high/critical no CI.
