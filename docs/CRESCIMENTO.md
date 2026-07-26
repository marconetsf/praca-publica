# Insights e Viralização

> Regra transversal: toda comparação segue a régua única do projeto (PRODUTO.md §2, regra 3 —
> mesma faixa de porte na mesma Grande Região, mediana; no texto público, "o típico das parecidas",
> nunca "média"); exceções por indicador só se documentadas na metodologia. Todo card exibe
> fonte + período de referência + data de extração. Especificado em 26/07/2026.

## 1. Top 12 insights recorrentes da Fase 1

Priorização = potencial de compartilhamento (identidade local + emoção comparativa) × viabilidade.

| # | Insight (título popular) | Fonte | Atualização | O que a manchete NÃO pode afirmar |
|---|---|---|---|---|
| 1 | "{Município} gastou R$ X por habitante em saúde — Y% acima/abaixo das cidades do mesmo tamanho" | SICONFI (RREO função 10) + população IBGE | bimestral | "gasta mal/bem" — despesa ≠ qualidade; excluir não-declarantes com aviso |
| 2 | "Sua cidade criou/perdeu N empregos com carteira em {mês}" + setor destaque | Novo CAGED | mensal (~1 mês defasagem) | causa ("graças a..."); saldo formal ≠ desemprego; nunca citar empresa |
| 3 | "N bebês nasceram em {Município} em {ano} — o menor número em X anos" | SINASC (pysus) | anual (1–2 anos defasagem) | "cidade está morrendo"; deixar claro o ano de referência |
| 4 | "Quantas horas sua cidade ficou sem luz em {ano}? Xh — a Nª pior da região" (DEC/FEC) | ANEEL | mensal/anual | grão real é conjunto elétrico, não município — dizer "área atendida" |
| 5 | "A nota das escolas de {Município}: X — acima/abaixo do típico do estado" | INEP (IDEB/Censo Escolar) | anual (IDEB bienal) | ranking de escola individual; nota reflete contexto socioeconômico. Exceção de régua (mediana estadual) documentada na metodologia |
| 6 | "{Município} arrecadou R$ X de IPTU por morador" / "Y% do dinheiro vem de Brasília" | SICONFI (receitas próprias vs FPM) | bimestral | "prefeitura preguiçosa"; FPM é direito constitucional, não "esmola" |
| 7 | "Sua prefeitura gasta X% da **receita corrente líquida** com pessoal — o limite da lei é 54%" | SICONFI (RGF — usar o % **já apurado** no demonstrativo, nunca recalcular pessoal/receita total: o denominador legal é a RCL, LRF art. 20, III) | quadrimestral | "ilegal" — há prazos de reenquadramento na LRF; dizer "acima do limite da LRF" |
| 8 | "Quantos médicos por 10 mil habitantes tem {Município}?" | CNES + população | mensal | CNES conta vínculos, não pessoas — dizer "vínculos médicos"; não nomear profissionais |
| 9 | "Internações evitáveis: N moradores internaram por diabetes/hipertensão" (ICSAP) | SIH (por residência) | mensal (~3 meses) | culpar unidade específica; **suprimir células < 5** (reidentificação) |
| 10 | "O salário de quem foi contratado em {Município} em {mês}: R$ X" | Novo CAGED (mediana de admissão) | mensal | usar média (outliers); é salário de admitidos, não de todos |
| 11 | "{Município} tem X% de crianças fora da creche" | Censo Escolar + população 0–3 (Censo 2022) | anual | denominador é fotografia 2022 — declarar; "negligência dos pais" |
| 12 | "De cada R$ 100 da prefeitura, só R$ X viraram obra" (investimento vs custeio) | SICONFI (GND 4) | bimestral | ciclo de obra é plurianual — comparar média de 3–4 anos |

**Fábrica de manchetes**: 3 templates por insight (acima / abaixo / "na média — sua cidade é a mais típica do Brasil em X"). Superlativos regionais ("a que mais criou empregos no interior de {UF}") têm o maior share — gerar 1º/último por UF e porte a cada ciclo.

## 2. Share card

**Formatos**: 1200×630 (OG — WhatsApp/X) + 1080×1920 ("baixar para o Status/Story" — Instagram não puxa OG).

**Layout (1200×630)**:
1. Topo: município + UF + marca (cores neutras — nunca vermelho/azul partidários).
2. Centro: **número gigante** (≥ 120 px) + unidade ("R$ 812 por habitante").
3. Faixa de comparação: barra/seta vs "o típico das cidades de porte semelhante" (mediana — régua única) com delta.
4. **Rodapé obrigatório DENTRO da imagem**: `Fonte: Tesouro Nacional · dados de mar/2026 · {url}` — a imagem circula descolada do link; a fonte viaja junto.
5. Contraste alto, rodapé ≥ 28 px (tela pequena + compressão do WhatsApp).

**Botão**: Web Share API com `files` (anexa a imagem — Android/iOS). Fallback em cascata: `wa.me/?text=`, copiar link, download. Texto pré-preenchido curto, com número, sem opinião, terminando em `(fonte: Tesouro Nacional)`.

**Geração em escala — decisão: sob demanda com Satori em Cloudflare Workers (`workers-og`/resvg-wasm) + cache CDN.** Pré-renderizar seria 5.570 × 12 insights × 2 formatos ≈ 130 mil imagens/ciclo, com cauda longa jamais acessada. **Versão do dado na URL** (`/og/{ibge}/saude?v=2026-06`): invalidação por URL, nunca por purge — essencial porque o cache do WhatsApp não tem endpoint de purge. Persistir o PNG no R2 na 1ª requisição. Atenção Satori: só flexbox, fontes embutidas — card visualmente simples joga a favor. **Custo: exige Workers Paid (US$ 5/mês)** — renderizar imagem consome dezenas/centenas de ms de CPU e o free tier dá 10 ms/requisição; já incluído na tabela de custos (ARQUITETURA.md §5) a partir do M3.

## 3. Open Graph / WhatsApp — requisitos exatos

- `og:image`: **1200×630, uma única tag**, HTTPS, JPG/PNG; **peso < 600 KB (teto Meta), mirar 200–300 KB** (JPEG ~80).
- Tags **no HTML inicial** (SSG) — o crawler do WhatsApp não executa JS.
- Cache do WhatsApp é por URL e sem purge → URL nova = preview novo (daí o `?v={mês}`).
- `og:title` ≤ 65 chars **com o número dentro**: "Ipatinga: R$ 812/habitante em saúde (−14% vs média)".
- **Tese de distribuição: o preview É a mensagem.** A maioria dos destinatários no grupo nunca clica — o card entrega insight completo (número + comparação + fonte) sozinho; o clique é bônus. Isso também é defesa editorial.

## 4. Loops de retenção

1. **"Compare com o vizinho"** — 3 chips ao fim de cada card: limítrofes (geobr), capital da UF, "mais parecida" (porte+renda). O loop interno mais barato que existe.
2. **Alerta mensal por município** — e-mail opt-in (double opt-in; Listmonk self-hosted), gatilhado pelo ciclo CAGED/SICONFI. Complemento: **RSS por município** (`/m/{ibge}/feed.xml`) — jornalistas assinam.
3. **Embed para portais locais — o multiplicador nº 1**:
   - Imagem hotlinkável + HTML de crédito pronto (rádio/blog de cidade pequena cola imagem, não iframe);
   - iframe responsivo `/embed/{ibge}` com o loop de comparação dentro, rodapé com marca;
   - **Press kit por UF a cada ciclo CAGED** (`/imprensa`): 10 destaques do estado em imagem + texto factual pronto. Prospecção via Atlas da Notícia (mapeia quem cobre cada município).

## 5. Calendário editorial 2026–2027

| Cadência | Âncora | Peça |
|---|---|---|
| Mensal (fim do mês) | Novo CAGED | saldo de empregos por município; ranking estadual; salário mediano |
| Mensal | Dump CNPJ | "N empresas abertas/fechadas em {Município}" (ponte p/ Fase 2) |
| Bimestral | RREO/SICONFI | despesa por função |
| Quadrimestral | RGF | pessoal vs limite LRF |
| Anual (1º sem.) | IDEB/Censo Escolar, DCA, RAIS | "o ano da sua cidade em dados" |

**O calendário editorial vale a partir do soft launch (abr/2027)** — antes disso não há canal de publicação (o site é M3). Em 2026 o esforço "editorial" é interno: espelhamento defensivo (M0.5) e construção da fábrica de manchetes. Marcos pós-launch: mai/2027 — lançamento com "a herança recebida em dados" (posses de jan/2027 + 1º RREO dos novos governos, abr/2027); ciclos mensais CAGED/CNPJ desde o primeiro mês; retrospectivas anuais no 1º semestre. Se surgir canal interino pré-launch (newsletter/rede social), tratar como projeto à parte com esforço próprio — não está no roadmap.

### Período eleitoral (Lei 9.504/97) — o que pode

- Conteúdo **informativo factual com fonte oficial, sem pedido de voto e sem exaltar/depreciar candidato, não é propaganda** — protegido o ano todo.
- **Riscos a evitar**: (a) PJ não pode fazer propaganda eleitoral nem de graça — nunca associar dado a candidato/partido/número; (b) **impulsionamento pago de conteúdo eleitoral é exclusivo de candidatos** — não pagar mídia para peças citando gestões de candidatos à reeleição; (c) nada que pareça pesquisa eleitoral (exige registro); (d) sem juízo de valor sobre governadores/presidente candidatos entre 15/08 e o 2º turno.
- **Vantagem estrutural**: o painel é municipal e prefeitos NÃO concorrem em 2026 — o grosso do conteúdo fica fora da zona de risco. Cuidado residual: prefeito licenciado candidato. Regra: "dados descrevem o município, nunca o gestor nomeado" de julho a outubro.
- **Congelar comparações estaduais/federais nominais de 15/08 a 25/10.**

## 6. Métricas desde o dia 1

**Ferramenta: Umami self-hosted desde o lançamento público** (sem cookie, sem fingerprinting → sem banner; < 1 KB; eventos custom). O Umami Cloud free (100 mil eventos/mês) serve só para o soft launch — um dia de pico viral o estoura, matando a métrica-mãe no momento decisivo. Self-host num VPS mínimo (~€4/mês, pode ser o mesmo da Fase 2 antecipado) com script e endpoint **proxiados pelo próprio domínio** (mantém a CSP estrita — ver SEGURANCA.md §4). Não usar GA4 (peso, consentimento, transferência internacional).

1. **Shares por página** — evento `share {municipio, insight, metodo}`. Métrica-mãe: shares/visita por insight orienta o backlog editorial.
2. **% tráfego WhatsApp** — via parâmetro próprio `?s=w` no texto pré-preenchido (referrer do WhatsApp é vazio). Meta de saúde: > 40%.
3. **Cobertura municipal** — municípios com ≥ 1 visita/semana e ≥ 1 share/mês (denominador: 5.570). Métrica de missão.
4. **Loop interno** — cliques em "compare com o vizinho".
5. **Fetches de og:image pelo crawler do WhatsApp** — registrados **no próprio Worker de OG** (o UA `WhatsApp/x.y` é gravado via Workers Analytics Engine; logs brutos do CDN são Enterprise, não existem no nosso plano). Mede compartilhamento *sem clique*, o "impressions" real que analytics de página não vê.
6. **Multiplicadores** — hotlinks por domínio referenciador, medidos pelo header `Referer` no mesmo Worker de OG/embeds (quais portais republicam); inscritos no alerta por município.
7. **Busca** — termos sem resultado = backlog de dados.

## 7. Nome e domínio — ⚠️ decisão pendente (bloqueante para marca)

- "Praça Pública" comunica bem (metáfora exata, português popular, funciona em rádio), mas: SEO genérico (encontrável só como marca composta), leitura hostil possível ("esculachado em praça pública"), e **`pracapublica.com.br` foi registrado por terceiro em 11/06/2026** (RDAP Registro.br, verificado 26/07/2026; status inativo).
- **Opções**: negociar o `.com.br`; usar `pracapublica.org.br` (verificar disponibilidade — `.org.br` até combina com projeto cívico); ou renomear antes de investir em marca.
- Fazer busca INPI (classes 35/38/41/42) antes do lançamento. Tagline que ancore o sentido positivo: "os dados da sua cidade, na sua mão".
