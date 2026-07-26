# Catálogo de Fontes de Dados Públicos

> URLs verificadas por acesso real em **26/07/2026**. URLs governamentais mudam sem aviso —
> em caso de 404, consultar `config/fontes.yaml` (fonte da verdade do projeto) e atualizar lá,
> nunca hardcoded nos pipelines.

## Chaves de cruzamento

| Chave | Confiabilidade | Uso |
|---|---|---|
| **Código IBGE de município** (7 dígitos) | Alta — presente em quase toda fonte | Chave primária do projeto. Atenção: o código de município do TSE **não** é o do IBGE (usar diretório de-para da Base dos Dados) |
| **CNPJ** (8 dígitos básicos) | Alta — determinística | Receita × PNCP × Portal da Transparência × sanções × Querido Diário |
| **CPF** | — | **Proibida no projeto.** O QSA do CNPJ traz CPF mascarado; reconstituí-lo cruzando com bases de CPF completo (TSE) cria dado pessoal novo e risco LGPD sério |

---

## Camada 1 — Núcleo

### CNPJ — Receita Federal
- **URL**: https://arquivos.receitafederal.gov.br/index.php/s/YggdBLfdninEJX9 (Nextcloud; download programático via WebDAV: `https://arquivos.receitafederal.gov.br/public.php/webdav/<AAAA-MM>/<arquivo>`, usuário `YggdBLfdninEJX9`, senha vazia)
- **Espelho (fallback)**: https://dados-abertos-rf-cnpj.casadosdados.com.br/
- **Formato**: ZIP de CSV sem cabeçalho, separador `;`, **ISO-8859-1**. 37 arquivos/mês (Empresas0–9, Estabelecimentos0–9, Socios0–9, Simples + tabelas de domínio). Layout: https://www.gov.br/receitafederal/dados/cnpj-metadados.pdf
- **Atualização**: mensal | **Volume**: ~7,6 GB zip/mês, ~25–30 GB descomprimido, ~60 mi estabelecimentos
- **Auth**: nenhuma
- **⚠️**: URL mudou 3× desde 2021. Servidor lento/instável para arquivos >1 GB — usar retry + resume (range requests). Já houve lote com dados errados sem errata. CNAE e endereço são autodeclarados e frequentemente desatualizados.

### Portal da Transparência — CGU
- **API**: https://api.portaldatransparencia.gov.br/ (Swagger em `/swagger-ui/index.html`) — 106 endpoints
- **Bulk**: https://portaldatransparencia.gov.br/download-de-dados (CSVs — preferir para volume)
- **Formato**: REST/JSON paginado (até 500/página)
- **Atualização**: diária/mensal por base
- **Auth**: **token obrigatório** (conta gov.br Prata/Ouro → https://portaldatransparencia.gov.br/api-de-dados/cadastrar-email); header `chave-api-dados`
- **Limites**: 90 req/min (6h–23h59), 300 req/min (0h–5h59); exceder pode suspender o token

### PNCP — Portal Nacional de Contratações Públicas
- **API**: `https://pncp.gov.br/api/consulta` (OpenAPI: https://pncp.gov.br/api/consulta/v3/api-docs)
- **Endpoints**: `/v1/contratacoes/publicacao|proposta|atualizacao`, `/v1/contratos`, `/v1/atas`, `/v1/pca/`
- **Formato**: REST/JSON | **Atualização**: quase tempo real (publicação obrigatória, Lei 14.133)
- **Auth**: nenhuma para consulta
- **Limites**: paginação `pagina`/`tamanhoPagina` — máx. 500 (contratos), **50 (contratações)**; `dataInicial`/`dataFinal` (AAAAMMDD) obrigatórios na maioria
- **Pré-2021 (Lei 8.666)**: módulo Legado em https://dadosabertos.compras.gov.br (sem token; a API antiga `compras.dados.gov.br` está descontinuada)

### IBGE
- **APIs**: https://servicodados.ibge.gov.br/api/docs (19 APIs: Agregados v3, Localidades, Malhas v4, Nomes...)
- **SIDRA**: https://apisidra.ibge.gov.br/
- **Censo 2022**: https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/ (usar HTTPS, não ftp://)
- **CNEFE** (endereços): https://ftp.ibge.gov.br/Cadastro_Nacional_de_Enderecos_para_Fins_Estatisticos/Censo_Demografico_2022/Arquivos_CNEFE/ — ~3,7 GB zip, ~111 mi endereços com CEP, coordenadas e setor censitário
- **Malhas**: via API v4 (GeoJSON) ou pacote `geobr` (GeoParquet, integra DuckDB)
- **Auth**: nenhuma | **Estabilidade**: a melhor do ecossistema
- **⚠️**: SIDRA rejeita consultas muito grandes — paginar por período/localidade

### TSE — Dados Abertos
- **URL**: https://dadosabertos.tse.jus.br/ (CKAN funcional, 172 datasets; candidatos 2026 já publicados)
- **Formato**: ZIP de CSV, `;`, ISO-8859-1 | **Atualização**: diária no ciclo eleitoral; histórico 1933–2024 estático
- **Auth**: nenhuma | **Licença**: CC-BY (atribuição obrigatória)
- **⚠️**: CPF completo de doadores PF fica exposto — não usar para reconstituir identidades (ver LGPD abaixo)

### SICONFI — Tesouro Nacional
- **API**: `https://apidatalake.tesouro.gov.br/ords/siconfi/tt/` (Swagger: https://apidatalake.tesouro.gov.br/docs/siconfi/)
- **Endpoints**: `entes`, `rreo` (bimestral), `rgf` (quadrimestral), `dca` (anual), `msc_*` (mensal)
- **Formato**: REST/JSON, até 5.000 itens/página | **Auth**: nenhuma
- **Limites**: ~1 req/s é o consenso seguro da comunidade (bloqueio por "má prática" documentado)
- **⚠️ Qualidade**: ~25% das declarações municipais têm inconsistências (o Tesouro publica ranking de qualidade); municípios pequenos atrasam/faltam

### Banco Central
- **SGS**: `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json` — janela máx. de 10 anos/consulta
- **Olinda/OData**: `https://olinda.bcb.gov.br/olinda/servico/{Servico}/versao/{vN}/odata/` (PTAX, Focus)
- **Pix**: `https://olinda.bcb.gov.br/olinda/servico/Pix_DadosAbertos/versao/v1/odata/` (mensal)
- **Auth**: nenhuma | **Licença**: ODbL (atribuição + share-alike em derivados)

---

## Camada 2 — Setoriais

### DataSUS (SIM, SINASC, SIH, CNES, SINAN)
- **FTP**: `ftp://ftp.datasus.gov.br/dissemin/publicos/` | **Web**: https://datasus.saude.gov.br/transferencia-de-arquivos/
- **Formato**: **.DBC** (DBF comprimido proprietário) — converter 1× para parquet via `pysus` (Python) ou `datasus-dbc`; nunca reprocessar DBC
- **Atualização**: SIH/CNES mensais; SIM/SINASC consolidados com 1–2 anos de defasagem
- **⚠️**: FTP notoriamente instável (TabNet em 503 na verificação). Totais do TabNet divergem dos microdados (filtros/datas de processamento diferentes) — padronizar nos microdados. Subnotificação regional no SIM/SINAN.

### INEP (ENEM, Censo Escolar, Educação Superior)
- **URL**: https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados (downloads em download.inep.gov.br)
- **Formato**: ZIP de CSV `;` | **Atualização**: anual
- **⚠️ LGPD**: microdados **seguem reduzidos pós-2022** (sem raça/renda/vínculo aluno-escola; Ed. Superior sem microdados de alunos). Versão completa só via SEDAP (sala segura, projeto aprovado). Servidor rejeita requisições sem header `User-Agent`.

### ANS (saúde suplementar)
- **URL**: https://dadosabertos.ans.gov.br/FTP/PDA/ (~60 conjuntos; índice HTTP raspável)
- **Formato**: CSV em ZIP; microdados históricos em DBC | **Atualização**: beneficiários mensal
- **⚠️**: diretórios mudam de nome com frequência; downloads de GB caem — usar `wget -c`

### ANEEL (energia)
- **URL**: https://dadosabertos.aneel.gov.br/ (CKAN, 71 datasets) + https://dadosabertos-aneel.opendata.arcgis.com/ (geo)
- **Formato**: CSV, **Parquet** (17 datasets), JSON | **Atualização**: interrupções mensal; tarifas ~semanal
- **Licença**: ODbL | **⚠️**: `datastore_search` tem limite de página baixo — baixar CSV/Parquet completo para tabelas grandes

### RAIS / Novo CAGED (trabalho)
- **FTP**: `ftp://ftp.mtps.gov.br/pdet/microdados/` (página oficial: https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/estatisticas-trabalho/microdados-rais-e-caged)
- **Formato**: **.7z** com TXT `;`. Novo CAGED: UTF-8. RAIS antiga: latin-1. **RAIS 2024+: extensão `.comt` e novos nomes de variáveis** (de-para oficial de 06/2026)
- **Atualização**: CAGED mensal (~1 mês); RAIS anual (~12–18 meses)
- **⚠️**: navegadores não abrem `ftp://` — usar curl/ftplib. Fonte instável. Quebras metodológicas pós-eSocial.

### DataJud — CNJ
- **API**: `https://api-publica.datajud.cnj.jus.br/{alias}/_search` (Elasticsearch DSL; wiki: https://datajud-wiki.cnj.jus.br/api-publica/)
- **Conteúdo**: só metadados de capa e movimentações (~352,7 mi documentos, 91 tribunais, sem STF)
- **Auth**: APIKey pública única publicada na wiki | **Limite**: 120 req/min; `from+size` ≤ 10.000 (usar `search_after`)
- **⚠️**: termo de uso proíbe exploração comercial sem autorização

### CVM
- **URL**: https://dados.cvm.gov.br/dados/ (listagem HTTP direta, aceita download resumível)
- **Formato**: CSV `;` ISO-8859-1 | **Atualização**: informes de fundos diários
- **⚠️**: Resolução CVM 175 mudou o layout — identificador deixou de ser `CNPJ_FUNDO` (agora `CNPJ_FUNDO_CLASSE` + `ID_SUBCLASSE`)

### SINISA (ex-SNIS, saneamento)
- **URL**: https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/saneamento/sinisa
- **Formato**: XLSX por módulo, sem API | **Atualização**: anual (ano-base t-1, publicação até dezembro)
- **⚠️ Quebra de série**: SNIS extinto em 2023; série histórica (`app4.mdr.gov.br`) fora do DNS; portal de dados do MCID bloqueia bots (403). Recuperar histórico SNIS via Base dos Dados.

### ComexStat — MDIC
- **CSVs**: https://balanca.economia.gov.br/balanca/bd/comexstat-bd/ (`/ncm/`, `/mun/`, `/tabelas/`)
- **Formato**: CSV `;` | **Atualização**: mensal, série 1989–2026
- **⚠️**: site principal devolve 403 a clientes automatizados; host dos CSVs com cadeia TLS incompleta

### Câmara e Senado
- **Câmara**: https://dadosabertos.camara.leg.br/ (REST + CSVs bulk em `/arquivos/`; cota parlamentar, votações) — diária, sem token, estável
- **Senado**: https://legis.senado.leg.br/dadosabertos/ — contínua, sem token

### IPEA Data / Atlas Brasil
- **IPEA**: OData `http://www.ipeadata.gov.br/api/odata4/` (~11 mil séries; sempre filtrar por `SERCODIGO`)
- **Atlas** (IDHM): https://www.atlasbrasil.org.br/ — XLSX, sem API, SPA difícil de raspar

### Outras
- **INMET** (clima): https://portal.inmet.gov.br/dadoshistoricos — ZIPs anuais de estações automáticas
- **ANP** (combustíveis): https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos — CSV, preços semanais
- **ANTT**: https://dados.antt.gov.br/ — ⚠️ WAF bloqueia acesso automatizado
- **MapBiomas** (uso do solo): https://brasil.mapbiomas.org/ — GeoTIFF 30 m, anual (Coleção 11 em 08/2026)

---

## Camada 3 — Agregadores (não reinventar a roda)

| Agregador | Oferece | Restrição |
|---|---|---|
| **Base dos Dados** — basedosdados.org | 1.194 datasets tratados no BigQuery, IDs harmonizados (`id_municipio`), diretórios de-para IBGE/TSE/BCB/RF | Alta frequência (CNPJ, CAGED, DataSUS) com **~6 meses de defasagem no free tier**; corrente = BD Pro (R$ 47+/mês). 1 TB query/mês grátis |
| **Querido Diário** — api.queridodiario.ok.org.br | Diários oficiais de 510 municípios; busca textual; endpoint `/company/info/{cnpj}` | 60 req/min; Cloudflare exige User-Agent de navegador |
| **minha-receita** | Pipeline Go + API self-hosted de CNPJ | Ativo no **Codeberg** (codeberg.org/cuducos/minha-receita); GitHub arquivado em 01/2026 |
| **Brasil.IO** | Dumps tratados (CNPJ/sócios, gastos de deputados) | API exige token gratuito; vários datasets congelados |
| **geobr / censobr** (Ipea) | Malhas em GeoParquet; microdados dos Censos em parquet/Arrow | — |
| **BrasilAPI / ViaCEP / OpenCEP** | Lookup pontual de CNPJ/CEP | **Proibido uso em massa** (bloqueio); só enriquecimento pontual |

### CEP — situação especial
A base oficial (DNE dos Correios) é **proprietária e paga** (~R$ 1.400–3.200/ano), protegida por direito autoral — única base "pública" nessa situação. ViaCEP e similares operam em zona cinzenta e bloqueiam varredura. **Rota do projeto: CNEFE/IBGE** para geocodificação e cruzamento em lote (fotografia de 2022; 22,8% dos endereços sem número), APIs só para lookup em interfaces.

---

## Riscos transversais

1. **LGPD**: dado público ≠ dado livre (art. 7º, §3º — compatibilidade de finalidade). Precedentes: multa Telekall (2023, reuso de dados "da internet"), casos Serasa. Cruzamentos que permitem reidentificação criam dado pessoal novo sob nossa responsabilidade — **nunca reconstituir CPFs** (QSA mascarado × TSE completo). Publicar preferencialmente agregados; documentar teste de legítimo interesse por cruzamento; atribuir fonte + data de extração sempre.
2. **Instabilidade**: instáveis — DataSUS FTP, PDET/RAIS, INEP, dumps da Receita; estáveis — IBGE, BCB, TSE, SICONFI, CVM, Câmara. O INEP apagou séries em 2022 e nunca republicou completas; a série do SNIS saiu do ar. **A camada `raw/` imutável é a garantia de reprodutibilidade. 2026 é ano eleitoral: espelhar o que importa antes de dezembro.**
3. **Licenças**: nenhuma fonte gov. veda uso comercial expressamente, exceto DNE (pago) e DataJud (termo restritivo). BCB/ANEEL: ODbL. TSE: atribuição. Demais: omissas — citar fonte e data.
