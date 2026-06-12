# -*- coding: utf-8 -*-
"""Ingestão direta do banco Firebird (Auditor ERP).

Substitui ingest.py para lançamentos financeiros, produzindo os mesmos
DataFrames com as mesmas colunas esperadas pelos módulos dre/fc/bp.

Views utilizadas:
  VS_CONTASAPAGAR   — despesas (competência + caixa)
  VS_CONTASARECEBER — receitas/recebimentos
  VS_VENDAS         — cabeçalho de vendas (NF)
  VS_ITENS_VENDA    — itens de vendas (produto, qtd, valor)
  VS_ENTRADASAIDA   — movimentos de estoque (ração, embalagens…)
  FINVSIPG          — tipos de pagamento (fallback para conta sem título)
  CONCECUS01        — cadastro de centros de custo
  FINVSPLC01        — plano de contas (código → título)

Situações (campo SITUACAO):
  1 = Em aberto   2 = Pago/Recebido   3 = Cancelado   8 = Renegociado
"""
import datetime
import decimal
import pandas as pd
import brutils as B
from concurrent.futures import ThreadPoolExecutor, as_completed
from db import get_conn

_QUITADO = {2}


# ─── Utilitários ─────────────────────────────────────────────────────────────

def _query(conn, sql: str) -> pd.DataFrame:
    """Executa SQL e retorna DataFrame, tratando tipos Firebird nativos."""
    cur = conn.cursor()
    cur.execute(sql)
    cols = [d[0] for d in cur.description]
    rows = []
    for row in cur.fetchall():
        clean = []
        for v in row:
            if isinstance(v, decimal.Decimal):
                clean.append(float(v))
            elif isinstance(v, (bytes, bytearray)):
                clean.append(v.decode("latin-1").strip())
            elif isinstance(v, str):
                clean.append(v.strip())
            else:
                clean.append(v)
        rows.append(clean)
    cur.close()
    return pd.DataFrame(rows, columns=cols)


def _str(val) -> str:
    """Converte valor do DB para str, tratando None e NaN do pandas."""
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except (TypeError, ValueError):
        pass
    return str(val).strip()


def _to_date(val):
    if val is None:
        return None
    if isinstance(val, datetime.date):
        return val
    try:
        return pd.to_datetime(val).date()
    except Exception:
        return None


def _fc_categoria(titulo: str, cc: str) -> str:
    t = (titulo or "").upper()
    c = (cc or "").upper()
    if any(k in t for k in ("EMPRESTIMO", "EMPRÉSTIMO", "FINANCIAMENTO", "JUROS", "CONSIGNADO",
                             "MUTU", "MÚTUO", "RESGATE", "RENDIMENTO", "APLICAÇ")):
        return "Financiamento"
    if any(k in t for k in ("ADIANTAMENTO", "CAPEX", "IMOBILIZADO", "BENFEITORIA",
                             "OBRA", "FERRAMENTAL", "EQUIPAMENTO", "MAQUINA", "MÁQUINA")):
        return "Investimento"
    if any(k in c for k in ("REFORMA", "BENFEITORIAS", "ADIANTAMENTO A FORNECEDOR")):
        return "Investimento"
    return "Operacional"


# ─── Despesas ────────────────────────────────────────────────────────────────

def ingest_despesa_db(cfg, conn=None) -> pd.DataFrame:
    """Despesas por DATA DE COMPETÊNCIA — equivalente a ingest_despesa()."""
    sql = """
        SELECT
            p.DATACOMPETENCIA   AS DATA_COMP,
            p.DTPAGAMENTO       AS DATA_PAGO,
            p.CREDOR            AS CREDOR,
            p.TITULO            AS CONTA,
            p.IDPAGAMENTO       AS TIPO_PGTO,
            p.CENTROCUSTO       AS CC,
            p.VALOR_FINAL       AS VALOR,
            p.VALORPAGO         AS VALOR_PAGO,
            p.SITUACAO          AS SITUACAO
        FROM VS_CONTASAPAGAR p
        WHERE p.DATACOMPETENCIA IS NOT NULL
          AND p.VALOR_FINAL > 0
          AND p.SITUACAO <> 3
        ORDER BY p.DATACOMPETENCIA
    """
    close = conn is None
    if conn is None:
        conn = get_conn()
    try:
        df = _query(conn, sql)
    finally:
        if close:
            conn.close()

    rows = []
    for _, r in df.iterrows():
        d = _to_date(r["DATA_COMP"])
        if d is None:
            continue
        val   = float(r["VALOR"] or 0)
        if val == 0:
            continue

        # Conta: usa TITULO; fallback: TIPO_PGTO (ex: "13SL - DÉCIMO TERCEIRO SALÁRIO")
        conta_raw = _str(r["CONTA"])
        if not conta_raw:
            tipo_pgto = _str(r["TIPO_PGTO"])
            if " - " in tipo_pgto:
                conta_raw = tipo_pgto.split(" - ", 1)[1].strip()
            else:
                conta_raw = tipo_pgto

        cc   = _str(r["CC"])
        cred = _str(r["CREDOR"])
        pago = int(r["SITUACAO"]) in _QUITADO

        cu, ccu = conta_raw.upper(), cc.upper()
        linha = cfg.conta2linha.get(cu)
        info  = cfg.cc2info.get(ccu)

        # Fallback por fornecedor (quando NF não tem conta contábil no Auditor)
        if linha is None and cred:
            linha_forn = cfg.forn2linha.get(cred.upper())
            if linha_forn:
                linha = linha_forn
                nat_forn, tipo_forn = cfg.forn2nat.get(cred.upper(), ("DESPESA_DIRETA", ""))

        destino, motivo, nat, tipo, grupo, sub, det = "DRE", "", "", "", "", "", ""
        if conta_raw == "" or cc == "" or linha is None or info is None:
            destino = "REAPROPRIAR"
            mm = []
            if conta_raw == "":  mm.append("sem conta")
            elif linha is None:  mm.append("conta não mapeada")
            if cc == "":         mm.append("sem CC")
            elif info is None:   mm.append("CC não mapeado")
            motivo = " + ".join([m for m in mm if m])
        else:
            nat, tipo = cfg.conta2nat.get(cu, ("DESPESA_DIRETA", ""))
            # se veio do fallback por fornecedor, usa natureza do fornecedor
            if not cfg.conta2nat.get(cu) and cred and cfg.forn2nat.get(cred.upper()):
                nat, tipo = cfg.forn2nat[cred.upper()]
            grupo = info.get("grupo", "")
            sub   = info.get("subgrupo", "")
            det   = info.get("detalhe", "")
            forca = info.get("forca_capex", "N") == "S"
            if linha == "IGNORAR" or nat == "IGNORAR":
                destino = "IGNORADO"
            elif forca or nat == "CAPEX":
                destino = "CAPEX"
            elif nat == "INVENTARIAVEL":
                destino = "ESTOQUE"
            else:
                destino = "DRE"

        rows.append(dict(
            periodo=B.period(d), ano=d.year, mes=d.month, data=d,
            conta=conta_raw or "(sem conta)", cc=cc or "(sem CC)", credor=cred, valor=val,
            linha_dre=linha or "", natureza=nat, tipo_estoque=tipo,
            grupo=grupo, subgrupo=sub, detalhe=det,
            destino=destino, motivo=motivo, pago=pago,
        ))
    return pd.DataFrame(rows)


# ─── Receitas ────────────────────────────────────────────────────────────────

def ingest_receita_db(cfg, conn=None) -> pd.DataFrame:
    """Receitas por DATA DE EMISSÃO da NF — equivalente a ingest_receita()."""
    sql = """
        SELECT
            v.CONT_NOTA         AS CONT_NOTA,
            v.DATAEMISSAO       AS DATA_EMISSAO,
            v.CLIENTE           AS CLIENTE,
            i.DESCRICAO         AS PRODUTO,
            i.SUBTOTAL          AS VALOR
        FROM VS_VENDAS v
        JOIN VS_ITENS_VENDA i ON i.CONT_NOTA = v.CONT_NOTA
        WHERE v.DATAEMISSAO IS NOT NULL
          AND i.SUBTOTAL > 0
        ORDER BY v.DATAEMISSAO
    """
    close = conn is None
    if conn is None:
        conn = get_conn()
    try:
        df = _query(conn, sql)
    finally:
        if close:
            conn.close()

    rows = []
    for _, r in df.iterrows():
        d = _to_date(r["DATA_EMISSAO"])
        if d is None:
            continue
        val  = float(r["VALOR"] or 0)
        prod = _str(r["PRODUTO"])
        cli  = _str(r["CLIENTE"])

        info = cfg.prod2.get(prod)
        if not info:
            norm = B.norm_prod(prod)
            info = next((v for k, v in cfg.prod2.items() if B.norm_prod(k) == norm), None)

        lid   = info["linha_id"] if info else ""
        grupo = info["grupo"]    if info else ""
        uni   = info["unidade"]  if info else ""
        cor   = info["cor"]      if info else ""

        if not info:         destino = "NAOCLASS"
        elif lid == "IGNORAR":      destino = "IGNORADO"
        elif lid == "DESCARTE_AVES": destino = "DESCARTE"
        else:                destino = "RECEITA"

        rows.append(dict(
            periodo=B.period(d), ano=d.year, mes=d.month, data=d,
            produto=prod, linha_id=lid, grupo=grupo, unidade=uni, cor=cor,
            valor=val, destino=destino, cliente=cli,
        ))
    return pd.DataFrame(rows)


# ─── Fluxo de Caixa ──────────────────────────────────────────────────────────

def ingest_fc_saidas_db(cfg, conn=None) -> pd.DataFrame:
    """Saídas de caixa por DATA DE PAGAMENTO."""
    sql = """
        SELECT
            p.DTPAGAMENTO   AS DATA_PAGO,
            p.CREDOR        AS CREDOR,
            p.TITULO        AS CONTA,
            p.IDPAGAMENTO   AS TIPO_PGTO,
            p.CENTROCUSTO   AS CC,
            p.VALORPAGO     AS VALOR
        FROM VS_CONTASAPAGAR p
        WHERE p.DTPAGAMENTO IS NOT NULL
          AND p.SITUACAO = 2
          AND p.VALORPAGO > 0
        ORDER BY p.DTPAGAMENTO
    """
    close = conn is None
    if conn is None:
        conn = get_conn()
    try:
        df = _query(conn, sql)
    finally:
        if close:
            conn.close()

    rows = []
    for _, r in df.iterrows():
        d = _to_date(r["DATA_PAGO"])
        if d is None:
            continue
        val   = float(r["VALOR"] or 0)
        conta = _str(r["CONTA"])
        if not conta:
            tipo_pgto = _str(r["TIPO_PGTO"])
            conta = tipo_pgto.split(" - ", 1)[-1].strip() if " - " in tipo_pgto else tipo_pgto
        cc   = _str(r["CC"])
        cred = _str(r["CREDOR"])
        rows.append(dict(
            periodo=B.period(d), ano=d.year, mes=d.month, data=d,
            conta=conta or "(sem conta)", cc=cc or "(sem CC)", credor=cred, valor=val,
            categoria=_fc_categoria(conta, cc),
        ))
    return pd.DataFrame(rows)


def ingest_fc_entradas_db(conn=None) -> pd.DataFrame:
    """Entradas de caixa por DATA DE RECEBIMENTO."""
    sql = """
        SELECT
            r.DATARECEBIMENTO   AS DATA_REC,
            r.CLIENTE           AS CLIENTE,
            r.VALORRECEBIDO     AS VALOR
        FROM VS_CONTASARECEBER r
        WHERE r.DATARECEBIMENTO IS NOT NULL
          AND r.SITUACAO = 2
          AND r.VALORRECEBIDO > 0
        ORDER BY r.DATARECEBIMENTO
    """
    close = conn is None
    if conn is None:
        conn = get_conn()
    try:
        df = _query(conn, sql)
    finally:
        if close:
            conn.close()

    rows = []
    for _, r in df.iterrows():
        d = _to_date(r["DATA_REC"])
        if d is None:
            continue
        val = float(r["VALOR"] or 0)
        rows.append(dict(
            periodo=B.period(d), ano=d.year, mes=d.month, data=d,
            produto="", cliente=_str(r["CLIENTE"]),
            valor=val, categoria="Operacional",
        ))
    return pd.DataFrame(rows)


# ─── Estoque / Ração ─────────────────────────────────────────────────────────

def ingest_racao_db(conn=None) -> pd.DataFrame:
    """Entradas/saídas de insumos do almoxarifado."""
    sql = """
        SELECT
            e.DATAMOVIMENTO AS DATA_MOV,
            e.DESCRICAO     AS DESCRICAO,
            e.QTD_ENTRADA   AS QTD_ENTRADA,
            e.QTD_SAIDA     AS QTD_SAIDA,
            e.NOME          AS ALMOXARIFADO
        FROM VS_ENTRADASAIDA e
        WHERE e.DATAMOVIMENTO IS NOT NULL
          AND (e.QTD_ENTRADA > 0 OR e.QTD_SAIDA > 0)
        ORDER BY e.DATAMOVIMENTO
    """
    close = conn is None
    if conn is None:
        conn = get_conn()
    try:
        df = _query(conn, sql)
    finally:
        if close:
            conn.close()

    rows = []
    for _, r in df.iterrows():
        d = _to_date(r["DATA_MOV"])
        if d is None:
            continue
        desc = _str(r["DESCRICAO"])
        du = desc.upper()
        if "OVOS" in du:
            fase = "OVOS"
        elif "PRE POSTURA" in du or "PRE-POSTURA" in du:
            fase = "RECRIA"
        elif "POSTURA" in du:
            fase = "POSTURA"
        elif any(k in du for k in ("RAÇÃO", "RACAO", "NUCLEO", "FARELO", "MILHO",
                                    "SOJA", "PREMIX", "CONCENTRADO")):
            fase = "POSTURA"
        else:
            fase = "OUTRO"

        rows.append(dict(
            periodo=B.period(d), ano=d.year, mes=d.month, data=d,
            descricao=desc,
            galpao=_str(r["ALMOXARIFADO"]),
            fase=fase,
            qtd=float(r["QTD_ENTRADA"] or 0),
            custo=0.0,
        ))
    return pd.DataFrame(rows)


# ─── Imobilizado (lê do PostgreSQL) ─────────────────────────────────────────

def ingest_imob_db() -> pd.DataFrame:
    """Lê imobilizado salvo no PostgreSQL (via tela de upload)."""
    try:
        import db_pg as _PG
        if not _PG.is_available():
            return pd.DataFrame()
        rows = _PG.fetch_imobilizado()
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        df = df.rename(columns={"data_aquisicao": "acq"})
        # garante tipos numéricos (psycopg2 pode retornar Decimal)
        for col in ("valor_aquisicao", "valor_pago", "saldo_a_pagar", "deprec_mensal", "valor_liquido"):
            if col in df.columns:
                df[col] = df[col].astype(float)
        return df
    except Exception:
        return pd.DataFrame()


# ─── Ponto de entrada ────────────────────────────────────────────────────────

def load_all_db(cfg, conn=None) -> dict:
    """Carrega todos os dados do BD em paralelo (5 conexões independentes)."""

    def _run(fn, *args):
        c = get_conn()
        try:
            return fn(*args, conn=c)
        finally:
            c.close()

    tasks = {
        "despesa":     (ingest_despesa_db,    cfg),
        "receita":     (ingest_receita_db,    cfg),
        "racao":       (ingest_racao_db,       ),
        "fc_saidas":   (ingest_fc_saidas_db,  cfg),
        "fc_entradas": (ingest_fc_entradas_db, ),
    }

    results = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(_run, fn, *args): key for key, (fn, *args) in tasks.items()}
        for future in as_completed(futures):
            results[futures[future]] = future.result()

    desp   = results["despesa"]
    rec    = results["receita"]
    est    = results["racao"]
    fc_sai = results["fc_saidas"]
    fc_ent = results["fc_entradas"]

    rac  = est[est.fase.isin(["POSTURA", "RECRIA"])].copy() if len(est) else est
    prod = est[est.fase == "OVOS"].copy() if len(est) else est

    if len(prod):
        prod["unidade"] = prod.descricao.map(
            lambda d: "Fazenda (MATRIZ)" if "CAIPIRA" in d.upper()
            else ("Silveira (FILIAL)" if ("VERMELHO" in d.upper() or "BRANCO" in d.upper()) else "—")
        )
        prod["matched"]   = False
        prod["emb_unit"]  = 0.0
        prod["emb_total"] = 0.0

    pers = set()
    for df in [desp, rec, fc_sai, fc_ent]:
        if len(df):
            pers |= set(df["periodo"])

    return dict(
        despesa=desp, receita=rec, racao=rac, producao=prod,
        imob=ingest_imob_db(),
        fc_saidas=fc_sai, fc_entradas=fc_ent,
        fc_dropped=[], dropped=[],
        periodos=sorted(pers),
        fonte="banco",
    )
