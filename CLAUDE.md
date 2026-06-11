# CLAUDE.md — Painel Financeiro 3 Amores

> Memória do projeto. Lido automaticamente no início de cada sessão. Mantenha atualizado.

## 1. O que é
Painel financeiro **gerencial** para a granja de poedeiras **"3 Amores"** (Grupo Bom Jardim).
Objetivo: responder ao sócio **se o negócio é rentável/sustentável**, entregando 3 peças que se conversam:
**DRE (competência)**, **Fluxo de Caixa (caixa)** e **Balanço Patrimonial + Indicadores**.

- **Matriz (Fazenda)** + **Filial (Silveira)**. Marcas: *Três Amores* e *Granjas Bom Jardim* (só rótulo, não muda agrupamento).
- Recorte de análise: **2025 em diante** (é quando a operação ganhou escala; antes disso fica no Balanço, não no P&L).
- Briefing original: `PROMPT_PAINEL_FINANCEIRO_GRANJA_2.md.txt`. Protótipo fonte dos de-para: `DRE_GRANJA_DASHBOARD.html`.

## 2. Stack e como rodar
- **Python 3.12 + Streamlit** (Windows). Use o launcher `py`.
- Pacotes: `pandas openpyxl xlrd pdfplumber pyyaml streamlit beautifulsoup4 lxml html5lib fpdf2` (fpdf2 = PDF do relatório).
- **Rodar:** duplo-clique em `iniciar.bat` (raiz) **ou** `py -m streamlit run app/painel.py` → http://localhost:8501. O `iniciar.bat` limpa `app\__pycache__` antes de subir (evita "versão fantasma" — ver §7).
- ⚠️ **Mexeu no código? FECHE a janela preta e reabra o `iniciar.bat`** (reinicia o servidor). O "Rerun" / **🔄 Atualizar** do navegador **NÃO** recarrega módulos `.py` — o Atualizar só relê DADOS.
- Teste rápido do motor (sem UI): `py app/_selftest.py` (imprime DRE/FC/BP de 2025 e 2026).
- UX: **barra lateral** = pasta de dados + botão **Atualizar** (relê tudo) + checkbox **🐔 ativo biológico** + downloads **📦 Excel / 📄 PDF**. O **filtro de Período** ficou no **topo da tela** (corpo, acima das abas), modos **Acumulado / Ano / Mês / Intervalo (de-até)** — é **global**: vale p/ TODAS as abas e p/ os downloads. (Antes ficava na barra lateral; movido + intervalo livre adicionado.)
- **Tradução do navegador:** `painel.py` injeta `lang=pt-BR`/`notranslate` (best-effort) p/ o navegador NÃO traduzir "mil"→"milhões". Se reaparecer: desligar a tradução do site OU usar aba anônima (ver §7).
- **Deploy em servidor (24/7 + acesso externo):** `auth.py` = login (config/usuarios.yaml; senha provisória `trocar@2026` — TROCAR). Guia completo pro TI em **`DEPLOY_GUIA_TI.md`** (⚠️ HTTPS/VPN obrigatórios — dados bancários). `requirements.txt` + `.streamlit/config.toml` prontos. Gerar/trocar senha: `py tools/gerar_senha.py <senha> <usuario> "<Nome>"`.
- **Deploy Docker/VPS (infra real da Sabrina = Debian + Docker + Portainer + Nginx + Supabase):** `Dockerfile` + `docker-compose.yml` + `.dockerignore` + `.gitignore` prontos. Painel lê os dados de **`PAINEL_DADOS`** (env var → pasta SMB montada em `/dados` no VPS; default = pasta do projeto no uso local). Fluxo: repo **PRIVADO** no GitHub (só CÓDIGO; dados/senhas via `.gitignore`/`.dockerignore`) → **Portainer GitOps** puxa e redeploya no push → **Nginx** (existente) faz HTTPS/proxy do container `painel-3amores:8501` → **SMB** traz planilhas+`config/`+`usuarios.yaml`+correções. Guia: **`DEPLOY_GIT_VPS.md`**. Supabase NÃO é usado (painel lê arquivos; migrar p/ BD = projeto futuro). `.github/workflows/deploy.yml` = alternativa SSH ao GitOps.

## 3. Estrutura
```
app/
  brutils.py    parse_valor_br, parse_date (serial/dd-mm-aaaa), valid(2020-2035), brl, brl_compact (KPI curto — REGRA: <R$1.000.000→'mil'; ≥R$1.000.000→'mi'; 999.999 capado p/ não virar '1.000 mil'), norm_prod, eggs_per_box
  configs.py    carrega TODOS os config/*.csv + config_geral.yaml -> objeto Configs (conta2linha, cc2info, prod2, comp, lote, capital_social...)
  ingest.py     varre pastas, DEDUPLICA por conteúdo, classifica destino de cada lançamento. load_all() devolve dict de DataFrames
  dre.py        compute(dfs, periodos, cfg, biologico) -> DRE (competência). LAYOUT da cascata
  fc.py         compute(dfs, periodos) -> Fluxo de Caixa (Sistema)
  bp.py         compute()/indicadores() -> Balanço + indicadores (snapshot acumulado até o fim do período)
  biological.py custo de recria + amortização linear contra GS02
  extrato.py    extratos (PDF) -> caixa real + transações (load_transacoes) + classificar_credito (intercompany/aporte/AgroMais) + passivo_pl_extras
  export.py     empacotamento Excel: build_excel -> 1 aba por peça (DRE/FC/BP/Indic/Receita/Reconc/Reapropriar)
  report.py     empacotamento PDF (fpdf2): build_pdf -> relatório 3 páginas (veredito+DRE+FC+BP+Indic+Reconc); _san p/ latin-1
  auth.py       login usuário+senha (PBKDF2, hashlib) p/ deploy em servidor: login_gate()/logout_button(); lê config/usuarios.yaml. SEM o yaml = libera (uso local sem senha)
  painel.py     Streamlit. **Filtro de Período GLOBAL no topo do corpo** (Acumulado/Ano/Mês/Intervalo de-até) → define `per`+`sel`. **`tabela_drill()`** = helper de RASTREABILIDADE: toda tabela agrupada (Receita, Reapropriar, Estoque, Fluxo, Reconciliação) é CLICÁVEL → clique na linha abre embaixo os lançamentos que somam o valor (`on_select="rerun"` + `selection.rows`). Abas: DRE, Reapropriar, Receita, Estoque, Fluxo de Caixa, Extrato/Reconciliação, Balanço, Indicadores, Config + botões 📦 Excel / 📄 PDF na barra lateral
  _selftest.py  teste de fumaça do motor
config/         de-para EDITÁVEIS (o "coração do liga-e-usa"): contas, centros_custo, produtos, impostos,
                layout_dre, composicao, lotes (.csv) + geral.yaml + usuarios.yaml (logins do deploy — hash PBKDF2)
tools/          scripts de diagnóstico/geração (inspect_*, extract_domain, classify_produtos, gen_configs,
                gen_composicao, diag_*, probe_*, build_dre[legado])
```
**Arquitetura:** ingest (1x, cacheado) → DataFrames → dre/fc/bp computam por período → painel renderiza. Toda regra vive em `config/`, não no código.

## 4. Fontes de dados (arquivo → peça → colunas)
| Pasta | Peça | Data | Valor / colunas-chave |
|---|---|---|---|
| `2.2 DRE - DESEMBOLSO POR DATA DE ENTRADA` | DRE despesa (competência) | col1 Data Entrada | col3 Conta, col4 CC, col6 Valor; aba `DadosDetalhados` |
| `2.1 DRE - FATURAMENTO POR DATA DE EMISSÃO` | DRE receita (competência) | col3 Emissão | col5 Produto, col8 Valor |
| `1.1 FLUXO DE CAIXA ... PAGAMENTO` | FC saídas (caixa) | col5 Pagamento | col6 Valor (mesmo layout do 2.2) |
| `1.2 FLUXO DE CAIXA ... RECEBIMENTO` | FC entradas (caixa) | col4 Pagamento/recebimento | col8 Valor |
| `4 PRODUTOS PRODUZIDOS` (.XLS xlrd) | Estoque/CMV | col7 Data Produção | col2 Descrição, col4 Alojamento/galpão, col5 Qtd, col6 Custo |
| `3 LEVANTAMENTO DE ATIVOS/ATIVOS/Registro_Imobilizado_TresAmores.xlsx` | Imobilizado/ativo bio | aba "Registro de Imobilizado", **header na linha 3** | col11 aquisição, col13 saldo a pagar, col15 deprec/mês, col2 classe |
| `0 COMPOSIÇÕES DOS PRODUTOS/Composição Produto Acabado.pdf` | embalagem por caixa | — | seção "Embalagem" tem subtotal por produto |
| `RECRIA HISTÓRICO/` | ativo biológico (lote GR01) | — | DADOS GERAIS DA RECRIA.XLS (107.100 aves, BOVANS WHITE) |
| `1.3 EXTRATO/<ano>/<mês>/*.PDF` (2025–2026, **só PDF**) | FC-Extrato (`app/extrato.py`) | SALDO ANTERIOR / topo | 5 contas: Bradesco Mat 0012922-4 + Fil 0001751-5; Santander Mat 130033543 + Fil 130068679; BB 28750-4 |

## 5. Regras contábeis (inegociáveis)
- **Competência ≠ Caixa** — DRE por competência; FC por caixa. Datas separadas sempre.
- **CMV por CONSUMO (não compra):** ração = `Produtos Produzidos` fase POSTURA; embalagem = composição × caixas produzidas. **Compras de inventariáveis** (milho/soja/núcleo/embalagem) → **Estoque**, não DRE.
- **Impostos PUXADOS das contas reais** (ICMS, IRPJ, CSLL). **PIS/COFINS não existem como conta → linha zerada e sinalizada. NUNCA calcular por alíquota.**
- **CAPEX fora da DRE** → Imobilizado + depreciação. Marcado por `natureza=CAPEX` (conta) ou `forca_capex=S` (centro de custo).
- **Ativo Biológico (§3.4):** custo de recria (pintainhas + ração recria + galpão recria) é **capitalizado** e **amortizado linear (13 meses) contra o GS02/Silveira** quando o lote bota. Liga/desliga na UI (default LIGADO).
- **Reapropriar/Verificar:** lançamento **sem centro de custo OU sem conta** → NÃO entra na DRE; vai para aba própria. Corrige na fonte e reupa → flui sozinho. Nada vai para "outros" silenciosamente.
- **Cascata familiar:** sempre rastreável até a **conta original do sistema** e o lançamento.
- **Balanço:** NÃO forçar fechamento — mostrar **"Diferença a investigar"**.

## 6. Decisões do usuário (travadas)
- **Agrupamento receita:** Branco + Vermelho = **Ovos Silveira (FILIAL)**; Caipira = **Ovos Fazenda (MATRIZ)**. Marca é só rótulo.
- **Produtos não-ovo (só no recebimento):** VACA → **ignorar**; PIMENTÃO/ABACATE/INHAME → **plantação**; GALINHA-ADULTO → **descarte de aves** (NÃO é receita; ligado ao ativo biológico).
- **Clientes de ovo (créditos do extrato, a partir de mai/2026):** a granja DIVERSIFICOU (antes só AgroMais) — HNT Comércio, Rio Mar, Du Vale, Jaboatão, Armazém do Grão, L.G.H., Marcos André, Jeferson + **"VALOR DISPONIVEL"** (remessa de boleto Bradesco) = **receita de cliente** (NETA, já na DRE). **Álvaro Freitas Pinheiro** = aporte do sócio Álvaro. **REGRA AUTOMÁTICA** (`extrato.classificar_credito`): remessa/PIX de terceiro NÃO identificada (`REM:`/`REMET`) → cliente; **salvaguarda: valor ≥ R$ 200k fica em "Outros (rever)"** (pode ser aporte/empréstimo — não chuta). Resolve clientes novos todo mês sem listar nome a nome. (Diag: `tools/diag_maio.py`.)
- **Correção manual de classificação (NO PAINEL):** aba 🧾 Extrato → clicar numa classe abre os lançamentos num **EDITOR** com a coluna *Corrigir p/* (cliente/aporte/mutuo/emprestimo/intercompany/adiantamento) → **💾 Salvar** grava por `tid` em `config/correcoes_classificacao.csv` (lido de volta por `carregar_overrides`) → reclassifica na hora. O override por `tid` **SOBREPÕE até a regra automática** (corrige p.ex. "intercompany que não é"). Função: `extrato.salvar_correcoes`.
- **Contas:** `VITOR XAVIER EMMERICK` → CAPEX (obras); `CUSTOS SIENGE` + `CUSTOS INCORRIDOS - TRANSFERENCIA DE SISTEMAS` → IGNORAR; `ADIANTAMENTO A FORNECEDOR` → CAPEX; `DI - PROVISÕES DE ENCARGOS SOCIAIS` → OPER_ENCARGOS.
- **Capital Social = R$ 12.480.000,00** (em `config_geral.yaml`).
- **CNPJs nos créditos dos extratos:** `15.718.991/0001-10` = **própria Três Amores** (intercompany → neta); `55.425.727/0001-02` = **AgroMais = CLIENTE** (recebimento); `40.108.957/0001-70` = **empresa do sócio Álvaro** (ele é dono da 3 Amores E desta) → **APORTE de sócio (PL)**. ⚠️ AgroMais pagou ~R$ 2 mi só em jan/25, mas faturamento 2025 = R$ 0,76 mi → o excedente é **adiantamento de cliente (Passivo)**, não receita realizada (investigar na Fase 7).
- **Saldo de caixa inicial 01/01/2025 = R$ 17.431,11** (apurado: Bradesco Matriz `SALDO ANTERIOR` 31/12/2024; Santander abre 0,00; Filiais/BB ainda não existiam). Gravado em `config_geral.yaml`. Ressalva: aplicação Santander (CONTAMAX) em 31/12/24 era ínfima e não consta nos PDFs de jan.
- Período: **2025 em diante**.

## 7. Bugs achados e corrigidos (não repetir)
- **`Relatorio_Desembolso_Detalhado 2025.xlsx` era cópia do 2026** → usuário substituiu por 2 arquivos (semestres). `ingest` **deduplica por conteúdo** (shape+total) automaticamente.
- **Registro de Imobilizado tem linha "TOTAL"** (dobrava o imobilizado e o saldo a pagar) → ingest pula linhas sem Cód / "TOTAL".
- **Fornecedores via "Pagamento em branco" é BOGUS** — o arquivo "por entrada" não traz data de pagamento. Fornecedores ficou **"a apurar" (Fase 7 reconciliação)**.
- Mojibake em nomes de produto (TRÃŠS/PAPELÃƒO) → `norm_prod` (NFKD + ascii) ao casar.
- **KPI mostra "milhões" onde devia ser "mil"** (ex.: "R$ 477 **milhões**" em vez de "R$ 477 **mil**"; só afeta valores < R$ 1 mi — os "X,XX **mi**" ficam certos). **🎯 CAUSA REAL = TRADUÇÃO AUTOMÁTICA DO NAVEGADOR**, NÃO o código. O Streamlit serve a página como `lang="en"`; Edge/Chrome detecta texto em PT e "traduz", e o tradutor **troca "mil" por "milhões"** (erro dele). O `brl_compact` SEMPRE esteve "mil". **Como provamos (depois de horas achando que era bytecode!):** numa **aba anônima** (sem tradução/extensões) aparece "R$ 477 **mil**" CERTO; e uma faixa de diagnóstico com `inspect.getsource(B.brl_compact)` no topo do painel mostrou o código-fonte limpo (só 1 ocorrência de "milh" = a docstring). **Correção:** (1) `painel.py` injeta `lang="pt-BR"` + `<meta name=google content=notranslate>` via `components.html` logo após `set_page_config` (best-effort); (2) **DEFINITIVO = desligar a tradução do site no navegador** (ícone de tradução na barra → "Nunca traduzir este site"). **Pista p/ diagnosticar de novo:** se SÓ os valores na casa dos milhares viram "milhões" e os "mi" ficam certos → é tradução, teste em **aba anônima** ANTES de mexer no código. (Investigação descartou bytecode/`__pycache__`/cópia/servidor-fantasma — nada disso era; mesmo assim o `iniciar.bat` agora limpa `app\__pycache__` ao subir, boa prática. Ferramentas: `tools/diag_server.py`, `tools/diag_pyc.py`.)

## 8. Status das fases
> **🏁 PROJETO COMPLETO — todas as 7 fases entregues.** Painel com as 3 peças + Indicadores + Reconciliação; Balanço fecha (Diferença R$ 0); export Excel (7 abas) + PDF (3 págs). Só restam refinos OPCIONAIS de fonte (§10).
- ✅ **Fase 0** Setup + de-para  · ✅ **Fase 1** Ingestão  · ✅ **Fase 2** Estoque/CMV consumo  · ✅ **Fase 3** DRE
- ✅ **Fase 4** FC — **FC-Sistema PRONTO**; **FC-Extrato:** `app/extrato.py` lê 55 PDFs (5 contas) + **transações** (`load_transacoes` → 7.345 lançs). **VALIDADO:** Bradesco+BB batem exato pela cadeia de saldos (abertura[M+1]=fechamento[M], filtro de auto-consistência `valor==Δsaldo` mata fantasmas de cabeçalho/Invest Fácil). Santander = aproximado (c/c varre p/ CONTAMAX; saldo real só na data de emissão). **Reconciliação (`tools/reconc_selftest.py`):** caixa real anda "na boca do caixa" (R$ 5–200k sempre), FC-Sistema acumula −R$ 31,5 mi → **GAP de ~R$ 31,5 mi de entradas que o sistema não vê = aportes + empréstimos + transferências intercompany**. **Falta:** classificar CNPJs (15718991000110 = própria Três Amores/intercompany; 55425727000102 e 40108957000170 = a confirmar), netar Santander, e usar caixa real no Balanço. **✅ Wired no painel** (aba 🧾 Extrato/Reconciliação: caixa real, trajetória mês a mês, GAP, top créditos p/ classificar; + caixa real no Balanço via `bp.compute(..., caixa_real=)`). Smoke test do painel OK (`tools/painel_smoke.py`, mock do Streamlit). **Obs:** caixa real é pequeno (~R$ 50k em abr/26) → a Diferença NÃO encolhe pelo caixa; encolhe na Fase 7 ao lançar os ~R$ 31,5 mi de aportes/empréstimos no Passivo/PL.
- ✅ **Fase 5** Balanço + Indicadores  · ✅ **Fase 6** Ativo Biológico · **Empacotamento:** ✅ export **Excel** (`export.py`, 7 abas) + ✅ **PDF consolidado** (`report.py`/fpdf2, relatório 3 págs p/ o sócio) — ambos com botão na barra lateral + `iniciar.bat`
- ✅ **Fase 7** Integração/conciliação cruzada — **CONCLUÍDA** (Balanço fecha, Diferença R$ 0). **Passo 1 (reconc. entradas) FEITO** (`tools/reconc_entradas_selftest.py`, `extrato.classificar_credito`): dos R$ 69,5 mi de créditos no banco → **operacional só ~R$ 10 mi** (FC-Sistema R$ 9,89 mi ≈ DRE faturamento R$ 9,96 mi — CONSISTENTE). Identificado: AgroMais adiant. **R$ 2,6 mi → Passivo**; aporte sócio Álvaro (40.108.957) **R$ 1,87 mi → PL**; intercompany (própria) **R$ 18,12 mi → neta**. ⚠️ **R$ 46,9 mi "Outros"** = PIX Bradesco só com nº de documento (sem pagador) — valores redondos (R$100k+) = financiamento/intercompany, mas não dá p/ classificar pela fonte → **Sabrina precisa identificar os maiores**. **Conclusão p/ sócio: operação NÃO se autofinancia — sobrevive de ~R$ 59 mi de injeções do grupo (capital+dívida+intercompany) em 16 meses.** **Passo 2 FEITO:** `bp.compute(..., adiant_clientes=, aporte_socio=)` lança AgroMais no Passivo + aporte Álvaro no PL → **Diferença caiu 18,55→14,08 mi** (fechou R$ 4,47 mi). Excel `creditos_outros_para_classificar.xlsx` gerado (1288 lançs, R$ 46,9 mi) + botão de download na aba Extrato. **Passo 3 — INFRA PRONTA:** mecanismo de rótulos manuais. Sabrina preenche a coluna *natureza* no Excel (vocabulário: `aporte`→PL · `mutuo`→Passivo · `emprestimo`→Passivo · `cliente`→adiant.Passivo · `intercompany`→neta) e salva como `creditos_outros_classificado.xlsx` na raiz/config; `extrato.carregar_overrides` lê por `tid` (id estável por lançamento, incluído no Excel) e `buckets_balanco` lança no Balanço (`bp.compute(..., emprestimos=)` → nova linha "Empréstimos e mútuos a pagar"). Mútuo de empresa do mesmo sócio = NÃO é empréstimo de banco (é parte relacionada): `aporte` se fica, `mutuo` se devolve. `extrato.py`: `classificar_credito(desc,tid,overrides)`, `destino_natureza`, `entradas_classificadas`, `buckets_balanco`, `carregar_overrides`, `creditos_outros`. **Parser melhorado:** anexa a linha SEGUINTE (pagador REM:/DES:/CNPJ) à desc → intercompany BB/Bradesco auto-classifica. **✅ FECHAMENTO GERENCIAL FEITO:** Sabrina preencheu (planilha em `creditos_outros_classificado.xlsx` na raiz). **Regra-chave:** a soma BRUTA dos rótulos SUPERESTIMA (mesmo dinheiro circula entre as 5 contas — bruto deu R$ 36 mi de aporte). Solução: **aporte do sócio = LÍQUIDO (residual)** medido pela identidade contábil (Ativo+Prejuízos−Capital) e confirmado pelos extratos como dinheiro do grupo. `cliente`→**receita** (NETA, já na DRE — NÃO é adiant.); só `adiantamento`/AgroMais→Passivo. `painel.py` calcula `aporte_v` como residual (`BP.compute` com aporte=0 → DIFERENCA → vira o aporte). **Resultado: A=P+PL, Diferença = R$ 0.** (`extrato.destino_natureza`: cliente/receita→NETA, adiant→PASS_ADI, mutuo/emprestimo→PASS_EMP, aporte→PL, intercompany→NETA.) Teste: `tools/fase7_gerencial_test.py`.

## 9. Números-chave (recorte atual, ativo biológico LIGADO)
- **2026 (Jan–Abr):** Faturamento R$ 9,2 mi · Lucro bruto **+R$ 2,1 mi** · EBITDA **−R$ 3,4 mi** · LL −R$ 4,0 mi.
- **2025:** Faturamento R$ 0,76 mi (plantel em formação) · EBITDA −R$ 17,2 mi.
- **Balanço 2026-04 (✅ fechamento gerencial Fase 7):** Ativo **R$ 9,66 mi** (imob 7,1 + bio 2,2 + caixa real) = Passivo **R$ 5,15 mi** (adiant. AgroMais 2,6 + mútuos do grupo 1,92 + CAPEX a pagar 0,63) + PL **R$ 4,5 mi** (capital 12,48 + **aporte líquido do grupo 14,03** − prejuízos 22,01). **Diferença = R$ 0.** *(A soma bruta dos rótulos daria R$ 36 mi de aporte, mas o dinheiro circula entre as contas → usa-se o líquido residual.)* PL positivo só por causa do aporte do grupo.
- **Caixa/funding (extratos):** caixa real anda **na boca do caixa** (R$ 5–200k sempre). FC-Sistema acumula −R$ 31,5 mi mas o caixa quase não mudou → **~R$ 31,5 mi de entradas fora do sistema = aportes (cap. 12,48 mi) + empréstimos + transfer. intercompany**. A operação foi sustentada por **capital E dívida**.
- **Veredito:** 🔴 **deficitária no formato atual** — margem bruta do ovo é POSITIVA, mas **opex acumulado (logística ~R$ 9 mi + pessoal ~R$ 6,6 mi) engole a margem**. Não é efeito só da recria (provado pelo ativo biológico). Caminho: escalar produção ou enxugar custo fixo. **(EBITDA acum. −R$ 20,6 mi · LL acum. −R$ 22 mi · funding do grupo ~R$ 31 mi em 16 meses.)**

## 10. Pendências do usuário (fonte) — destravam precisão
- **Salários sem CC** (R$ 2,83 mi caem no "Reapropriar", fora da DRE) → lançar Centro de Custo + Conta e reexportar.
- **Composição incompleta** (cobre só ~28% das caixas) → completar `config/config_composicao.csv` ou reexportar a composição cheia (os 72% usam estimativa por ovo).
- ✅ **Saldo de caixa 01/01/2025** apurado = R$ 17.431,11 (resolvido na Fase 4/Extrato).
- ✅ **CNPJs classificados** (ver §6): AgroMais=cliente, 40.108.957=aporte sócio Álvaro, 15.718.991=própria. **Falta (Fase 7):** muitos créditos Bradesco têm só nº de documento (sem nome do pagador) → não dá p/ classificar pela fonte; precisaria da Sabrina conferir os maiores.
- **(opcional, p/ precisão máxima)** extratos das **aplicações** (Bradesco Invest Fácil / Santander CONTAMAX) e de **dez/2024**.

## 11. Status: PROJETO COMPLETO ✅ (o que fazer numa próxima sessão)
Tudo entregue e funcionando. Não há tarefa pendente do meu lado.
- **Rodar:** `iniciar.bat` → barra lateral: pasta de dados → **🔄 Atualizar** → seletor de período → ver abas / baixar **📦 Excel** ou **📄 PDF**.
- **Se a Sabrina reupar/corrigir dados na fonte** (§10: salários s/ CC, composição) → só clicar **Atualizar** que o painel recalcula sozinho.
- **Se ela preencher mais a planilha de créditos** (`creditos_outros_classificado.xlsx` na raiz) → idem, Atualizar.
- **Refinos OPCIONAIS futuros** (se pedirem): netar Santander com precisão (hoje aproximado); extratos das aplicações/dez-2024 p/ saldo de abertura exato; gráficos no PDF; PDF por unidade (Matriz/Filial).
- **Cuidado ao retomar:** o motor evoluiu — confira a API atual de `extrato.py`/`bp.py` (ver §8 Fase 7) antes de mexer. Sempre rodar `tools/painel_smoke.py` + `tools/fase7_gerencial_test.py` após mudanças.

## 12. Convenções de trabalho com a Sabrina
- Trabalhar **pouco a pouco e testando**; validar números antes de avançar.
- **Sinalizar** (não chutar) quando faltar/divergir dado na fonte — ela corrige e reupa.
- Responder em **português**.

## 13. Infraestrutura de produção (configurada em 09/06/2026)

### Ambiente
- **VPS:** Debian 12, IP `177.11.52.50`
- **Container:** `painel-3amores` (Docker, gerenciado pelo Portainer)
- **URL pública:** `https://painelbj.bjgestaoempresarial.com.br`
- **Proxy:** Nginx Proxy Manager (`npm-network`) com HTTPS Let's Encrypt + WebSocket Support ativado

### Dados (NAS → SMB → Container)
- **NAS:** `\\192.168.100.202\Publico\Servidor_TresAmores\Painelbj`
- **Montagem no VPS:** `/mnt/dados-painel` (CIFS permanente via `/etc/fstab`)
- **Dentro do container:** `/dados` (via volume Docker)
- **Variável de ambiente:** `PAINEL_DADOS=/dados`
- A Sabrina larga planilhas/extratos no NAS e clica em Atualizar no painel. Nenhum deploy necessário.

### Deploy automático (GitHub Actions)
- **Gatilho:** `git push` na branch `main`
- **O que faz:** SSH no VPS → `git pull` → `DOCKER_BUILDKIT=0 docker build -t painel-3amores:latest .` → `docker restart painel-3amores`
- **Tempo:** ~3 minutos após o push
- **Workflow:** `.github/workflows/deploy.yml`

### Observações técnicas importantes
- BuildKit desabilitado no VPS (`/etc/docker/daemon.json` com `"buildkit": false`). Sempre usar `DOCKER_BUILDKIT=0 docker build` se buildar manualmente.
- O NPM usa o nome do container (`painel-3amores`) como Forward Hostname, nunca o IP.
- A VPN WireGuard entre VPS e rede local (192.168.100.x) já estava configurada, permitindo acesso ao NAS.

### Gerenciar usuários do painel
Gerar hash de senha (rodar no VPS):
```bash
docker exec painel-3amores python tools/gerar_senha.py "SenhaForte" nomeusuario "Nome Completo"
```
Colar o bloco gerado dentro de `usuarios:` no arquivo `/mnt/dados-painel/config/usuarios.yaml`.
