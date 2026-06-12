# -*- coding: utf-8 -*-
"""Extratos bancarios (PDF) -> caixa real por conta/mes.
Bancos: Bradesco (Invest Facil embutido no saldo), Santander (CONTAMAX a parte), BB.
Para cada PDF (1 conta x 1 mes) extrai: saldo_anterior (= fechamento do mes anterior),
saldo_disp (saldo disponivel no topo do extrato; e na DATA DE EMISSAO do PDF, nao no
ultimo dia do mes), agencia, conta, titular. O saldo de FECHAMENTO confiavel de um mes
e o saldo_anterior do mes seguinte (cadeia)."""
import os, re
import pandas as pd

EXT_DIR = "1.3 EXTRATO"
MONEY = re.compile(r"-?\d{1,3}(?:\.\d{3})*,\d{2}")

# conta -> (banco, titular)  [deterministico, melhor que adivinhar pelo nome do arquivo]
CONTA2TIT = {
    "0012922-4": ("Bradesco", "Matriz"), "0001751-5": ("Bradesco", "Filial"),
    "130033543": ("Santander", "Matriz"), "130068679": ("Santander", "Filial"),
    "28750-4":   ("BB", "Matriz"),
}

def _money(tok):
    if tok is None: return None
    m = MONEY.search(tok)
    if not m: return None
    v = float(m.group(0).replace(".", "").replace(",", ".").lstrip("-"))
    s = tok.strip()
    if m.group(0).startswith("-") or s.endswith("D") or s.endswith("D ") or "-" in s[:m.start()+1]:
        v = -abs(v)
    return v

def _last_money(line):
    ms = MONEY.findall(line)
    return _money(line[line.rfind(ms[-1]) - 1:]) if ms else None

def _banco(fn, txt):
    u = (fn + " " + txt[:400]).upper()
    if "BRADESCO" in u: return "Bradesco"
    if "SANTANDER" in u: return "Santander"
    if "BANCO DO BRASIL" in fn.upper() or re.search(r"\bBB\b", fn.upper()): return "BB"
    return "?"

def _parse(txt, banco):
    """Retorna dict(agencia, conta, saldo_anterior, saldo_disp, fonte_disp)."""
    out = dict(agencia="", conta="", saldo_anterior=None, saldo_disp=None, fonte_disp="")
    lines = [l.strip() for l in txt.split("\n")]

    # ---- agencia / conta ----
    if banco == "Bradesco":
        m = re.search(r"Ag:\s*(\d+)\s*\|\s*CC:\s*([\d.\-]+)", txt)
        if m: out["agencia"], out["conta"] = m.group(1), m.group(2)
    elif banco == "Santander":
        m = re.search(r"Ag[eê]ncia:\s*(\d+)\s*Conta:\s*([\d.\-]+)", txt)
        if m: out["agencia"], out["conta"] = m.group(1), m.group(2)
    elif banco == "BB":
        ma = re.search(r"Ag[eê]ncia\s+([\d.\-]+)", txt); mc = re.search(r"Conta corrente\s+([\d.\-]+)", txt)
        if ma: out["agencia"] = ma.group(1)
        if mc: out["conta"] = mc.group(1)

    # ---- saldo anterior (1a ocorrencia) ----
    for l in lines:
        if "SALDO ANTERIOR" in l.upper():
            out["saldo_anterior"] = _last_money(l); break

    # ---- saldo disponivel (topo; data de emissao do extrato) ----
    if banco == "Bradesco":
        for l in lines:                                  # "01332 | 0012922-4 188.326,35 188.326,35"
            m = re.match(r"\d{3,5}\s*\|\s*[\d.\-]+\s+(-?[\d.,]+)\s+(-?[\d.,]+)$", l)
            if m: out["saldo_disp"] = _money(m.group(1)); out["fonte_disp"] = "Total Disponivel"; break
    elif banco == "Santander":
        pats = [(r"saldo dispon[ií]vel para uso[:\s]*r?\$?\s*(-?[\d.,]+)", "Saldo disp. p/ uso"),
                (r"saldo dispon[ií]vel total\s*\(d\s*\+\s*e\)\s*(-?[\d.,]+)", "Saldo disp. Total (D+E)"),
                (r"saldo dispon[ií]vel\s+(-?[\d.,]+)", "Saldo Disponivel")]
        for pat, nome in pats:
            m = re.search(pat, txt, re.I)
            if m: out["saldo_disp"] = _money(m.group(1)); out["fonte_disp"] = nome; break
    elif banco == "BB":
        # BB: procurar "Saldo" final (Saldo Atual / S A L D O)
        for l in lines:
            if re.search(r"saldo\s+(atual|final|do dia)", l, re.I):
                out["saldo_disp"] = _last_money(l); out["fonte_disp"] = "Saldo Atual"; break
    return out

def _read_pdf_text(fp):
    import pdfplumber
    with pdfplumber.open(fp) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages)

# ---------------------------------------------------------------------------
# TRANSACOES (linha a linha) — para reconciliacao Extrato x Sistema
# ---------------------------------------------------------------------------
DATE_RE = re.compile(r"(\d{2}/\d{2}/\d{4})")
INTERNO_RE = re.compile(r"CONTAMAX|APLICA[CÇ]|RESGATE", re.I)  # varreduras c/c<->aplicacao (internas)
BB_PAIR = re.compile(r"(-?\d{1,3}(?:\.\d{3})*,\d{2})\s+([CD])\b")
# linhas de rodapé/cabeçalho a NÃO anexar como contexto de pagador
_FOOTER = re.compile(r"dados acima|transa[çc][aã]o efetuada|central de vendas|central de atendimento|"
                     r"ouvidoria|deficient|extrato antigo|acessar novo|saldo dispon|conta corrente >|"
                     r"posi[çc][aã]o em|entenda a composi|^\d/\d$", re.I)

def _floats(line):
    return [float(m.replace(".", "").replace(",", ".")) for m in MONEY.findall(line)]

def _tid(banco, conta, data, valor):
    """id estável por lançamento (p/ casar rótulos manuais da planilha de volta)."""
    import hashlib
    return hashlib.md5(f"{banco}|{conta}|{data}|{round(float(valor or 0), 2)}".encode()).hexdigest()[:10]

def _parse_tx(txt, banco):
    """Retorna dict(tx=[...], abertura, fechamento, fonte_fech). Cada tx: data,desc,valor,saldo,interno.
    valor>0 credito (entrada), valor<0 debito (saida)."""
    lines = [l.rstrip() for l in txt.split("\n")]
    tx, idxs, abertura, fechamento, fonte = [], [], None, None, ""

    if banco == "Bradesco":
        cur, prev = None, None
        for i, l in enumerate(lines):
            s = l.strip(); U = s.upper()
            md = DATE_RE.match(s)
            if md: cur = md.group(1)
            if "SALDO ANTERIOR" in U:
                if abertura is None: abertura = _last_money(s); prev = abertura
                continue
            # nao-transacoes: cabecalho "AG | CONTA tot tot", coluna, SALDO INVEST/totalizadores
            if "|" in s or "SALDO INVEST" in U or re.search(r"\bTOTAL\b", U) or "TOTAL DISPON" in U:
                continue
            fs = _floats(s)
            if len(fs) < 2: continue            # tx do Bradesco = valor + saldo corrido
            val, sal = fs[0], fs[-1]
            if prev is None: prev = abertura if abertura is not None else (sal - val)
            if abs(val - (sal - prev)) > 0.02:  # fora da cadeia c/c (fantasma/seção Invest Fácil)
                continue
            desc = DATE_RE.sub("", MONEY.sub("", s)).strip(" .|*")
            tx.append(dict(data=cur, desc=desc, valor=val, saldo=sal,
                           interno=bool(INTERNO_RE.search(desc))))
            idxs.append(i); prev = sal
        if prev is not None: fechamento, fonte = prev, "saldo corrido (cadeia c/c)"

    elif banco == "Santander":
        # Layout do Santander: dois formatos convivem no mesmo PDF:
        #   CRÉDITO  → tudo numa linha: "DATA  Descrição  valor  saldo"
        #   DÉBITO   → descrição na linha ANTERIOR (sem data) + "DATA  DocNum  valor  saldo"
        #              + eventual continuação da descrição na linha SEGUINTE
        # O parser varre todas as linhas com data; quando não sobra texto após remover
        # data/valores/doc (apenas número longo), pega a linha anterior como descrição.
        # NÃO usa o "enrich com linha seguinte" genérico (idxs fica vazio para o Santander).
        _DOC = re.compile(r'\b\d{6,10}\b')  # numero de documento (sem pontos/virgulas)
        i = 0
        while i < len(lines):
            s = lines[i].strip(); U = s.upper()
            md = DATE_RE.match(s)
            if not md: i += 1; continue
            if "SALDO ANTERIOR" in U:
                if abertura is None: abertura = _last_money(s)
                i += 1; continue
            if "SALDO DISP" in U or "SALDO BLOQ" in U or "CONTA CORRENTE" in U:
                i += 1; continue
            fs = _floats(s)
            if not fs: i += 1; continue
            val = fs[0]; sal = fs[-1] if len(fs) >= 2 else None
            # Remove data, números monetários e número de doc → o que sobra é a descrição inline
            desc = _DOC.sub("", DATE_RE.sub("", MONEY.sub("", s))).strip(" .|*")
            if not desc:
                # Formato débito: descrição está na linha ANTERIOR não-vazia / não-data
                for k in range(i - 1, max(i - 5, -1), -1):
                    prev = lines[k].strip()
                    if prev and not DATE_RE.match(prev) and not _FOOTER.search(prev):
                        desc = prev
                        # Continuação da descrição pode estar na linha i+1
                        if i + 1 < len(lines):
                            nxt = lines[i + 1].strip()
                            if nxt and not DATE_RE.match(nxt) and not _FOOTER.search(nxt) and not _floats(nxt):
                                desc = desc + " " + nxt
                        break
            tx.append(dict(data=md.group(1), desc=desc, valor=val, saldo=sal,
                           interno=bool(INTERNO_RE.search(desc))))
            # NÃO adiciona a idxs: o passo "enrich com linha seguinte" não se aplica
            # ao Santander (a linha seguinte é descrição do próximo débito, não contexto desta tx)
            i += 1
        fonte = "reconstruido por fluxo"

    elif banco == "BB":
        for i, l in enumerate(lines):
            s = l.strip(); U = s.upper()
            md = DATE_RE.match(s)
            if not md: continue
            pairs = BB_PAIR.findall(s)
            if not pairs: continue
            def sg(p):
                v = float(p[0].replace(".", "").replace(",", "."))
                return -abs(v) if p[1] == "D" else abs(v)
            if "SALDO ANTERIOR" in U:
                if abertura is None: abertura = sg(pairs[0])
                continue
            if "S A L D O" in U or re.search(r"\bSALDO\b(?! ANTERIOR)", U):
                fechamento, fonte = sg(pairs[0]), "S A L D O"; continue
            val = sg(pairs[0]); sal = sg(pairs[1]) if len(pairs) >= 2 else None
            desc = DATE_RE.sub("", BB_PAIR.sub("", s)).strip(" .|*")
            tx.append(dict(data=md.group(1), desc=desc, valor=val, saldo=sal, interno=False))
            idxs.append(i)

    # enriquece a desc com a linha SEGUINTE (pagador: REM:/DES:/CNPJ/nome) p/ classificacao
    used = set(idxs)
    for k, i in enumerate(idxs):
        j = i + 1
        if j < len(lines) and j not in used:
            t = lines[j].strip()
            if t and not DATE_RE.match(t) and not _FOOTER.search(t):
                tx[k]["desc"] = (tx[k]["desc"] + " | " + t).strip(" |")

    return dict(tx=tx, abertura=abertura, fechamento=fechamento, fonte_fech=fonte)

def load_transacoes(base=None):
    """DataFrame de TODAS as transações (1 linha por lançamento) + resumo por conta-mês.
    Lê do PostgreSQL (tabela extrato_txs). `base` mantido por compatibilidade mas não usado."""
    try:
        import db_pg as _pg
        if not _pg.is_available():
            return pd.DataFrame(), pd.DataFrame()
        rows = _pg.fetch_extrato_txs()
    except Exception:
        return pd.DataFrame(), pd.DataFrame()

    if not rows:
        return pd.DataFrame(), pd.DataFrame()

    txrows = []
    for r in rows:
        data_tx = r["data_tx"]
        if hasattr(data_tx, "strftime"):
            data_str = data_tx.strftime("%d/%m/%Y")
            ano, mes  = data_tx.year, data_tx.month
        else:
            data_str = str(data_tx)
            try: ano, mes = int(str(data_tx)[:4]), int(str(data_tx)[5:7])
            except Exception: ano, mes = 0, 0

        banco   = str(r["banco"])
        conta   = str(r["conta"])
        bt      = CONTA2TIT.get(conta)
        titular = bt[1] if bt else "Matriz"
        if bt:
            banco = bt[0]
        chave   = f"{banco}/{titular} ({conta})"
        periodo = r["periodo"] or f"{ano}-{mes:02d}"
        valor   = float(r["valor"])
        desc    = str(r["descricao"])
        fitid   = str(r["fitid"])
        interno = bool(INTERNO_RE.search(desc))

        txrows.append(dict(
            periodo=periodo, ano=ano, mes=mes,
            banco=banco, titular=titular, conta=conta, chave=chave,
            tid=fitid,
            data=data_str, desc=desc, valor=valor,
            saldo=None, interno=interno,
        ))

    tx = pd.DataFrame(txrows)
    if not len(tx):
        return tx, pd.DataFrame()

    # Resumo por conta-mês
    resumo_rows = []
    for keys, grp in tx.groupby(["periodo","ano","mes","banco","titular","conta","chave"]):
        per, ano, mes, banco, titular, conta, chave = keys
        ext = grp[~grp.interno]
        resumo_rows.append(dict(
            periodo=per, ano=int(ano), mes=int(mes),
            banco=banco, titular=titular, conta=conta, chave=chave,
            arquivo="(OFX/PG)", n_tx=len(grp),
            abertura=None,
            entradas=float(ext[ext.valor > 0].valor.sum()),
            saidas=float(ext[ext.valor < 0].valor.sum()),
            fluxo=float(ext.valor.sum()),
            fech_detectado=None, fonte_fech="OFX/PG",
        ))
    rs = pd.DataFrame(resumo_rows).sort_values(["banco","titular","ano","mes"]).reset_index(drop=True)
    return tx, rs

# ---------------------------------------------------------------------------
# SALDOS DE FECHAMENTO / CAIXA REAL  (para Balanço e reconciliação)
# ---------------------------------------------------------------------------
def tabela_saldos(rs):
    """Adiciona saldo_fim por conta-mes.
    Bradesco/BB: fechamento[M] = abertura[M+1] (saldo oficial carregado; exato pela cadeia);
                 ultimo mes da conta -> fech_detectado (saldo corrido).
    Santander:   c/c varre p/ CONTAMAX -> reconstruido = acumulado do fluxo (>=0), APROXIMADO."""
    if not len(rs): return rs
    d = rs.sort_values(["chave", "ano", "mes"]).copy()
    d["ord"] = d.ano * 12 + d.mes
    d["prox_abertura"] = d.groupby("chave")["abertura"].shift(-1)
    d["cum_fluxo"] = d.groupby("chave")["fluxo"].cumsum()
    def sfim(r):
        if r.banco in ("Bradesco", "BB"):
            v = r.prox_abertura
            return r.fech_detectado if (v != v) else v
        return max(0.0, r.cum_fluxo) if (r.cum_fluxo == r.cum_fluxo) else 0.0   # Santander aprox.
    d["saldo_fim"] = d.apply(sfim, axis=1).astype(float)
    d["aprox"] = d.banco == "Santander"
    return d

# classificacao dos CREDITOS por pagador (decisoes da Sabrina — ver CLAUDE.md §6)
CRED_CLASSES = [
    ("Intercompany (própria)",      ["15718991", "TRES AMORES", "TRÊS AMORES"]),
    ("Adiant. cliente (AgroMais)",  ["55425727", "AGROMAIS", "AGRO MAIS"]),
    ("Aporte sócio (Álvaro)",       ["40108957", "ALVARO FREITAS"]),
    # Clientes de ovo confirmados pela Sabrina (+ "VALOR DISPONIVEL" = remessa de boleto de cliente no Bradesco).
    # Venda realizada -> NETA (já está na DRE/FC; neutro p/ Balanço). A ordem importa: intercompany/aporte vêm ANTES.
    ("Cliente (ovo) - receita",     ["HNT COMERCIO", "RIO MAR", "DU VALE", "JABOATAO DA SERRA",
                                     "ARMAZEM DO GRAO", "L. G. H.", "MARCOS ANDRE MOREIRA",
                                     "JEFERSON DE SOUZA", "VALOR DISPONIVEL"]),
]
def _norm(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", str(s or "")) if not unicodedata.combining(c)).upper()

# rótulo manual (planilha) -> rótulo canônico exibido. Sabrina escreve: aporte/mutuo/emprestimo/cliente/adiantamento/intercompany
# NB: 'cliente' = venda realizada (já na DRE/FC, NEUTRO p/ Balanço); 'adiantamento' = cliente pagou a mais (Passivo)
_MANUAL = {"APORTE": "Aporte (sócio/grupo)", "MUTUO": "Mútuo (partes relacionadas)",
           "EMPRESTIMO": "Empréstimo bancário", "INTERCOMPANY": "Intercompany (própria)",
           "ADIANT": "Adiantamento de cliente", "CLIENTE": "Receita (cliente)", "RECEITA": "Receita (cliente)"}

def _classe_manual(nat):
    u = _norm(nat).strip()
    for k, v in _MANUAL.items():
        if u.startswith(k) or k in u: return v
    return None

AUTO_CLIENTE_TETO = 200_000.0   # remessa NÃO identificada acima disso fica p/ rever (pode ser aporte/empréstimo)
_REMESSA_RE = re.compile(r"\bREM[:.\s]|REMET")   # remessa PIX/TED de terceiro (cliente)

def classificar_credito(desc, tid=None, overrides=None, valor=None):
    if overrides and tid in overrides:
        m = _classe_manual(overrides[tid])
        if m: return m
    u = _norm(desc)
    for nome, chaves in CRED_CLASSES:
        if any(_norm(k) in u for k in chaves): return nome
    # Regra automática (decisão Sabrina, mai/2026): remessa de terceiro NÃO identificada = receita de cliente.
    # Salvaguarda: valor alto fica em "Outros (rever)" — pode ser aporte/empréstimo; não chutar.
    if _REMESSA_RE.search(u):
        if valor is not None and abs(valor) >= AUTO_CLIENTE_TETO:
            return "Outros recebimentos (valor alto - rever)"
        return "Cliente (ovo) - receita"
    return "Outros recebimentos"

def destino_natureza(classe):
    """classe -> destino no Balanço: PL | PASS_EMP (empréstimos/mútuos) | PASS_ADI (adiant. cliente) | NETA | OUTROS."""
    n = _norm(classe)
    if "ADIANT" in n or "AGROMAIS" in n: return "PASS_ADI"          # adiantamento de cliente -> Passivo
    if "RECEITA" in n or "CLIENTE" in n: return "NETA"              # venda realizada (já na DRE/FC) -> neutro
    if "MUTUO" in n or "EMPRESTIMO" in n or "FINANC" in n: return "PASS_EMP"
    if "APORTE" in n: return "PL"
    if "INTERCOMPANY" in n: return "NETA"
    return "OUTROS"

def entradas_classificadas(tx, periodos=None, overrides=None):
    """Agrega os CREDITOS (entradas) por classe e periodo, aplicando rótulos manuais (overrides) se houver."""
    if tx is None or not len(tx): return pd.DataFrame()
    c = tx[(tx.valor > 0) & (~tx.interno)].copy()
    if periodos is not None: c = c[c.periodo.isin(set(periodos))]
    if not len(c): return pd.DataFrame()
    has_tid = "tid" in c.columns
    c["classe"] = c.apply(lambda r: classificar_credito(r.desc, (r["tid"] if has_tid else None), overrides, r.valor), axis=1)
    return c

def buckets_balanco(tx, periodo_fim, overrides=None):
    """Acumulados até periodo_fim por destino contábil: dict(adiant, aporte, emprestimos)."""
    cl = entradas_classificadas(tx, overrides=overrides)
    if not len(cl): return dict(adiant=0.0, aporte=0.0, emprestimos=0.0)
    alvo = int(periodo_fim[:4]) * 12 + int(periodo_fim[5:])
    cl = cl[(cl.ano * 12 + cl.mes) <= alvo].copy()
    cl["dest"] = cl.classe.map(destino_natureza)
    g = cl.groupby("dest").valor.sum()
    return dict(adiant=float(g.get("PASS_ADI", 0.0)), aporte=float(g.get("PL", 0.0)),
                emprestimos=float(g.get("PASS_EMP", 0.0)))

def passivo_pl_extras(tx, periodo_fim, overrides=None):
    """Compat: (adiant_clientes, aporte_socio). Use buckets_balanco p/ incluir empréstimos/mútuos."""
    b = buckets_balanco(tx, periodo_fim, overrides)
    return b["adiant"], b["aporte"]

def carregar_overrides(base):
    """Lê rótulos manuais. Tenta PostgreSQL primeiro; fallback para planilha/CSV."""
    # PG-first
    try:
        import db_pg as _pg
        if _pg.is_available():
            ov = _pg.fetch_correcoes()
            if ov:
                return ov
    except Exception:
        pass
    # Fallback: varre arquivos 'credito*/natureza/classific*' na raiz ou config/
    import glob
    files = []
    for d in (base, os.path.join(base, "config")):
        if not os.path.isdir(d): continue
        for ext in ("*.xlsx", "*.csv"):
            for fp in glob.glob(os.path.join(d, ext)):
                nm = os.path.basename(fp).lower()
                if "credito" in nm or "natureza" in nm or "classific" in nm:
                    files.append(fp)
    ov = {}
    for fp in sorted(set(files)):
        try:
            df = pd.read_excel(fp) if fp.lower().endswith(".xlsx") else pd.read_csv(fp, sep=";", dtype=str)
        except Exception:
            continue
        cols = {str(c).strip().lower(): c for c in df.columns}
        ncol = next((cols[k] for k in cols if k.startswith("natureza")), None)
        if not ncol: continue
        kcol = cols.get("tid") or cols.get("id")
        bcol, ccol, dcol, vcol = cols.get("banco"), cols.get("conta"), cols.get("data"), cols.get("valor")
        for _, r in df.iterrows():
            nat = str(r[ncol]).strip()
            if not nat or nat.lower() == "nan": continue
            key = None
            if kcol and str(r[kcol]).strip() and str(r[kcol]).strip().lower() != "nan":
                key = str(r[kcol]).strip()
            elif bcol and ccol and dcol and vcol:
                dv = r[dcol]; ds = dv.strftime("%d/%m/%Y") if hasattr(dv, "strftime") else str(dv).strip()
                try: vv = float(r[vcol])
                except Exception:
                    vv = float(str(r[vcol]).replace("R$", "").replace(".", "").replace(",", ".").strip() or 0)
                key = _tid(str(r[bcol]).strip(), str(r[ccol]).strip(), ds, vv)
            if key: ov[key] = nat
    return ov


def salvar_correcoes(base, mapa):
    """Grava/atualiza correções manuais de classificação. PG-first, fallback CSV."""
    if not mapa: return 0
    # PG-first
    try:
        import db_pg as _pg
        if _pg.is_available():
            for tid, info in mapa.items():
                _pg.upsert_correcao(
                    str(tid), str(info.get("natureza","")).strip(),
                    str(info.get("banco","")), str(info.get("data","")),
                    str(info.get("valor","")), str(info.get("desc",""))
                )
            return len(mapa)
    except Exception:
        pass
    # Fallback CSV
    fp = os.path.join(base, "config", "correcoes_classificacao.csv")
    atual = {}
    if os.path.exists(fp):
        try:
            df = pd.read_csv(fp, sep=";", dtype=str)
            for _, r in df.iterrows():
                t = str(r.get("tid", "")).strip()
                if t and t.lower() != "nan":
                    atual[t] = {c: ("" if pd.isna(r[c]) else str(r[c])) for c in df.columns}
        except Exception:
            pass
    for tid, info in mapa.items():
        atual[str(tid)] = {"tid": str(tid), "natureza": str(info.get("natureza", "")).strip(),
                           "banco": str(info.get("banco", "")), "data": str(info.get("data", "")),
                           "valor": str(info.get("valor", "")), "desc": str(info.get("desc", ""))}
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    cols = ["tid", "natureza", "banco", "data", "valor", "desc"]
    pd.DataFrame([{c: row.get(c, "") for c in cols} for row in atual.values()]).to_csv(
        fp, sep=";", index=False, encoding="utf-8-sig")
    return len(mapa)

def creditos_outros(tx, periodos=None, overrides=None, top=None):
    """Créditos 'Outros recebimentos' (não identificados), p/ a Sabrina rotular. Inclui 'tid' p/ casar de volta."""
    cl = entradas_classificadas(tx, periodos, overrides)
    if not len(cl): return cl
    o = cl[cl.classe == "Outros recebimentos"].sort_values("valor", ascending=False)
    keep = [c for c in ["tid", "periodo", "data", "banco", "titular", "conta", "valor", "desc"] if c in o.columns]
    o = o[keep].copy()
    o.insert(len(o.columns), "natureza (preencher)", "")
    return o.head(top) if top else o

def caixa_real_fim(rs, periodo):
    """Caixa real total no fim de `periodo`.
    Usa saldos de fechamento do PostgreSQL (extrato_saldos, gravados no upload OFX).
    Fallback: soma de fluxo acumulado das transações OFX se não houver saldo cadastrado."""
    alvo = int(periodo[:4]) * 12 + int(periodo[5:])

    # Tenta usar extrato_saldos do PG
    try:
        import db_pg as _pg
        if _pg.is_available():
            srows = _pg.fetch_extrato_saldos()
            if srows:
                df_s = pd.DataFrame(srows)
                df_s["ord"] = df_s["periodo"].map(lambda p: int(p[:4]) * 12 + int(p[5:]))
                df_s["chave"] = df_s.apply(
                    lambda r: f"{CONTA2TIT.get(str(r['conta']), (str(r['banco']), 'Matriz'))[0]}/"
                              f"{CONTA2TIT.get(str(r['conta']), (str(r['banco']), 'Matriz'))[1]} ({r['conta']})", axis=1)
                df_s = df_s[df_s.ord <= alvo]
                if len(df_s):
                    last = df_s.sort_values("ord").groupby("chave", as_index=False).tail(1)
                    last["saldo_fim"] = last["saldo_fim"].astype(float)
                    last["aprox"] = False
                    total = float(last["saldo_fim"].fillna(0).sum())
                    return total, last[["chave", "banco", "conta", "periodo", "saldo_fim", "aprox"]]
    except Exception:
        pass

    # Fallback: usa tabela de resumo por período (baseada nas transações OFX)
    if rs is None or not len(rs):
        return 0.0, pd.DataFrame()
    d = tabela_saldos(rs)
    if not len(d): return 0.0, d
    d = d[d.ord <= alvo]
    if not len(d): return 0.0, d
    last = d.sort_values("ord").groupby("chave", as_index=False).tail(1)
    return float(last.saldo_fim.fillna(0).sum()), last[["chave", "banco", "titular", "periodo", "saldo_fim", "aprox"]]

def load_extratos(base):
    """Varre 1.3 EXTRATO/<ano>/<mes>/<pdf> -> DataFrame (1 linha por conta-mes)."""
    root = os.path.join(base, EXT_DIR)
    rows = []
    if not os.path.isdir(root): return pd.DataFrame(rows)
    for ano in sorted(os.listdir(root)):
        yp = os.path.join(root, ano)
        if not (os.path.isdir(yp) and ano.isdigit()): continue
        for mof in sorted(os.listdir(yp)):
            mp = os.path.join(yp, mof)
            if not os.path.isdir(mp): continue
            try: mes = int(mof.split()[0])
            except Exception: continue
            for fn in sorted(os.listdir(mp)):
                if not fn.lower().endswith(".pdf"): continue
                fp = os.path.join(mp, fn)
                try: txt = _read_pdf_text(fp)
                except Exception as e:
                    rows.append(dict(ano=int(ano), mes=mes, periodo=f"{ano}-{mes:02d}", arquivo=fn,
                        banco="?", titular="?", agencia="", conta="", saldo_anterior=None,
                        saldo_disp=None, fonte_disp=f"ERRO: {e!r}")); continue
                banco = _banco(fn, txt)
                p = _parse(txt, banco)
                conta = p["conta"]
                bt = CONTA2TIT.get(conta)
                if bt: banco, titular = bt
                else: titular = "Filial" if re.search(r"\bF(ILIAL)?\b", fn.upper()) else "Matriz"
                rows.append(dict(ano=int(ano), mes=mes, periodo=f"{ano}-{mes:02d}", arquivo=fn,
                    banco=banco, titular=titular, agencia=p["agencia"], conta=conta,
                    saldo_anterior=p["saldo_anterior"], saldo_disp=p["saldo_disp"],
                    fonte_disp=p["fonte_disp"]))
    df = pd.DataFrame(rows)
    if len(df):
        df["chave"] = df.banco + "/" + df.titular + " (" + df.conta + ")"
        df = df.sort_values(["banco", "titular", "ano", "mes"]).reset_index(drop=True)
    return df

def saldo_abertura(df, periodo_ini="2025-01"):
    """Saldo de caixa no inicio de `periodo_ini` = soma dos SALDO ANTERIOR das contas
    cujo 1o extrato e exatamente esse periodo (= fechamento do mes imediatamente anterior)."""
    if not len(df): return 0.0, pd.DataFrame()
    first = df.sort_values(["ano", "mes"]).groupby("chave", as_index=False).first()
    ini = first[first.periodo == periodo_ini].copy()
    ini["saldo_abertura"] = ini.saldo_anterior.fillna(0.0)
    total = float(ini.saldo_abertura.sum())
    return total, ini[["chave", "banco", "titular", "conta", "saldo_abertura", "fonte_disp"]]

def fechamento_mensal(df):
    """Saldo de FECHAMENTO de cada conta-mes = saldo_anterior do mes SEGUINTE (cadeia).
    Para o ultimo mes de cada conta, usa saldo_disp (aprox., data de emissao)."""
    if not len(df): return pd.DataFrame()
    d = df.sort_values(["chave", "ano", "mes"]).copy()
    d["ord"] = d.ano * 12 + d.mes
    d["fech"] = d.groupby("chave")["saldo_anterior"].shift(-1)
    # ultimo mes da conta: fallback no saldo_disp
    d["fech"] = d["fech"].where(d["fech"].notna(), d["saldo_disp"])
    return d
