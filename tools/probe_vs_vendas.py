# -*- coding: utf-8 -*-
"""Diagnóstico da view VS_VENDAS e VS_ITENS_VENDA no Firebird.

Roda no VPS (dentro do container) ou localmente com acesso ao Firebird:
    docker exec painel-3amores python tools/probe_vs_vendas.py

Mostra:
  1. Colunas disponíveis em VS_VENDAS
  2. Valores distintos de cada campo de status/situação/tipo
  3. Amostra de notas por situação (quantas, soma do valor)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from db import get_conn

def probe():
    conn = get_conn()
    cur  = conn.cursor()

    print("=" * 60)
    print("COLUNAS de VS_VENDAS")
    print("=" * 60)
    cur.execute("SELECT FIRST 1 * FROM VS_VENDAS")
    cols = [d[0] for d in cur.description]
    for c in cols:
        print(f"  {c}")

    print()
    print("=" * 60)
    print("COLUNAS de VS_ITENS_VENDA")
    print("=" * 60)
    cur.execute("SELECT FIRST 1 * FROM VS_ITENS_VENDA")
    cols_itens = [d[0] for d in cur.description]
    for c in cols_itens:
        print(f"  {c}")

    # Campos de status que provavelmente existem
    status_candidates = ["SITUACAO", "STATUS", "TIPO_NF", "TIPONOTA",
                         "CANCELADA", "CODSTATUS", "SITUACAONF", "TIPOMOVIMENTO"]

    print()
    print("=" * 60)
    print("VALORES DISTINTOS — campos de status/situação/tipo")
    print("=" * 60)
    for col in status_candidates:
        if col in cols:
            try:
                cur.execute(f"SELECT {col}, COUNT(*) FROM VS_VENDAS GROUP BY {col} ORDER BY COUNT(*) DESC")
                rows = cur.fetchall()
                print(f"\n  {col}:")
                for v, n in rows:
                    print(f"    '{v}' → {n} notas")
            except Exception as e:
                print(f"  {col}: erro ({e})")

    print()
    print("=" * 60)
    print("VOLUME TOTAL — notas × valor (sem filtro)")
    print("=" * 60)
    cur.execute("""
        SELECT COUNT(DISTINCT v.CONT_NOTA), SUM(i.SUBTOTAL)
        FROM VS_VENDAS v
        JOIN VS_ITENS_VENDA i ON i.CONT_NOTA = v.CONT_NOTA
        WHERE v.DATAEMISSAO IS NOT NULL AND i.SUBTOTAL > 0
    """)
    n, s = cur.fetchone()
    print(f"  {n} notas · R$ {float(s or 0):,.2f}")

    print()
    print("=" * 60)
    print("AMOSTRA — 5 notas mais recentes (todos os campos)")
    print("=" * 60)
    cur.execute("""
        SELECT FIRST 5 * FROM VS_VENDAS
        WHERE DATAEMISSAO IS NOT NULL
        ORDER BY DATAEMISSAO DESC
    """)
    sample_cols = [d[0] for d in cur.description]
    for row in cur.fetchall():
        print()
        for col, val in zip(sample_cols, row):
            if val not in (None, "", b""):
                print(f"  {col}: {val}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    probe()
