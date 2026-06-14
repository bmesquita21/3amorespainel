# -*- coding: utf-8 -*-
"""Probe das tabelas de produção do Auditor para substituição do Excel.

Rodar no VPS:
    docker exec painel-db python tools/probe_producao.py

Tabelas investigadas:
  PROPRODU  — ordens/registros de produção
  PROSTPRO  — situação da produção
  PROPSCMP  — composições da produção (ração consumida por ordem)
  ESPRODU   — cadastro de produtos
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from db import get_conn

TABELAS = ["PROPRODU", "PROSTPRO", "PROPSCMP", "ESPRODU"]

def sep(titulo=""):
    print("\n" + "=" * 70)
    if titulo:
        print(f"  {titulo}")
        print("=" * 70)

def probe_tabela(cur, tabela, limit=5):
    sep(f"COLUNAS — {tabela}")
    try:
        cur.execute(f"SELECT FIRST 1 * FROM {tabela}")
        cols = [d[0] for d in cur.description]
        for c in cols:
            print(f"  {c}")
    except Exception as e:
        print(f"  ERRO ao abrir {tabela}: {e}")
        return []

    sep(f"AMOSTRA ({limit} linhas) — {tabela}")
    try:
        cur.execute(f"SELECT FIRST {limit} * FROM {tabela}")
        rows = cur.fetchall()
        hdr = " | ".join(f"{c[:18]:18s}" for c in cols)
        print("  " + hdr)
        print("  " + "-" * len(hdr))
        for row in rows:
            print("  " + " | ".join(f"{str(v)[:18]:18s}" for v in row))
    except Exception as e:
        print(f"  ERRO: {e}")

    return cols

def distintos(cur, tabela, col, top=20):
    try:
        cur.execute(f"""
            SELECT TRIM({col}), COUNT(*)
            FROM {tabela}
            GROUP BY {col}
            ORDER BY COUNT(*) DESC
            ROWS {top}
        """)
        rows = cur.fetchall()
        print(f"\n  {col} (top {top}):")
        for v, n in rows:
            print(f"    {repr(v):35s} → {n:>6} linhas")
    except Exception as e:
        print(f"  {col}: erro ({e})")

def probe():
    conn = get_conn()
    cur  = conn.cursor()

    # ── 1. Estrutura de cada tabela ──────────────────────────────────────────
    cols_map = {}
    for t in TABELAS:
        cols_map[t] = probe_tabela(cur, t)

    # ── 2. Campos candidatos por tabela ─────────────────────────────────────
    sep("CAMPOS CANDIDATOS — datas, quantidades, custos, situação")
    for t, cols in cols_map.items():
        cands = [c for c in cols if any(k in c.upper() for k in
                 ("DATA", "DT", "QTD", "QUANT", "CUSTO", "VALOR", "SITU",
                  "FASE", "GALPAO", "LOTE", "DESCRI", "NOME", "COD", "FASE",
                  "PROD", "TOTAL", "UNIT"))]
        if cands:
            print(f"\n  {t}:")
            for c in cands:
                distintos(cur, t, c, top=10)

    # ── 3. Contagem geral ────────────────────────────────────────────────────
    sep("CONTAGEM DE REGISTROS")
    for t in TABELAS:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            n = cur.fetchone()[0]
            print(f"  {t}: {n:,} registros")
        except Exception as e:
            print(f"  {t}: erro ({e})")

    # ── 4. JOIN exploratório PROPRODU × PROPSCMP × ESPRODU ──────────────────
    sep("JOIN PROPRODU × PROPSCMP × ESPRODU — 10 linhas recentes")
    join_sql = """
        SELECT FIRST 10
            p.CODPRODUCAO,
            p.DATAPRODUCAO,
            p.CODIGOPRODUTO,
            e.NOME          AS PRODUTO_NOME,
            p.QUANTIDADEPRODUCAO,
            p.CUSTOPRODUCAO,
            p.SITUACAO,
            c.CODIGOINSUMO,
            c.DESCRICAOINSUMO,
            c.QUANTIDADEINSUMO,
            c.CUSTOINSUMO
        FROM PROPRODU p
        LEFT JOIN ESPRODU e  ON e.CODIGO  = p.CODIGOPRODUTO
        LEFT JOIN PROPSCMP c ON c.CODPRODUCAO = p.CODPRODUCAO
        ORDER BY p.DATAPRODUCAO DESC
    """
    try:
        cur.execute(join_sql)
        cols = [d[0] for d in cur.description]
        print("  " + " | ".join(f"{c[:16]:16s}" for c in cols))
        print("  " + "-" * 100)
        for row in cur.fetchall():
            print("  " + " | ".join(f"{str(v)[:16]:16s}" for v in row))
    except Exception as e:
        print(f"  JOIN falhou: {e}")
        # Tenta variações de nome de coluna
        sep("Tentando colunas alternativas…")
        for tentativa in [
            "SELECT FIRST 5 * FROM PROPRODU ORDER BY 1 DESC",
            "SELECT FIRST 5 * FROM PROPSCMP ORDER BY 1 DESC",
        ]:
            try:
                cur.execute(tentativa)
                cols2 = [d[0] for d in cur.description]
                print(f"\n  {tentativa[:40]}:")
                print("  " + " | ".join(f"{c[:18]:18s}" for c in cols2))
                for r in cur.fetchall():
                    print("  " + " | ".join(f"{str(v)[:18]:18s}" for v in r))
            except Exception as e2:
                print(f"  Erro: {e2}")

    # ── 5. PROSTPRO — situações disponíveis ─────────────────────────────────
    sep("PROSTPRO — situações disponíveis")
    try:
        cur.execute("SELECT FIRST 1 * FROM PROSTPRO")
        pcols = [d[0] for d in cur.description]
        print(f"  Colunas: {pcols}")
        cur.execute("SELECT FIRST 10 * FROM PROSTPRO")
        for r in cur.fetchall():
            print("  " + str(r))
    except Exception as e:
        print(f"  PROSTPRO: {e}")

    cur.close()
    conn.close()
    sep("FIM DO PROBE")

if __name__ == "__main__":
    probe()
