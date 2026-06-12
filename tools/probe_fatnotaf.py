# -*- coding: utf-8 -*-
"""Diagnóstico da tabela FATNOTAF01001 no Firebird.

Roda no VPS dentro do container:
    docker exec painel-db python tools/probe_fatnotaf.py

Mostra colunas, valores distintos de SITUACAO/NATUREZA e
o impacto do filtro recomendado no faturamento bruto do DRE.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from db import get_conn

TABLE = "FATNOTAF01001"


def probe():
    conn = get_conn()
    cur  = conn.cursor()

    # ── 1. Colunas ────────────────────────────────────────────────────────────
    print("=" * 60)
    print(f"COLUNAS de {TABLE}")
    print("=" * 60)
    try:
        cur.execute(f"SELECT FIRST 1 * FROM {TABLE}")
        cols = [d[0] for d in cur.description]
        for c in cols:
            print(f"  {c}")
    except Exception as e:
        print(f"  ERRO: {e}")
        conn.close()
        return

    # Candidatos de status / natureza / tipo
    candidates = [c for c in cols if any(k in c.upper() for k in
        ("SITUA", "STATUS", "TIPO", "NATUR", "CANCEL", "CODOP", "OPERAC", "MODAL", "MOVIM", "CFOP"))]

    # ── 2. Valores distintos ──────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("VALORES DISTINTOS — campos de situação / natureza / tipo")
    print("=" * 60)
    for col in candidates:
        try:
            cur.execute(f"SELECT TRIM({col}), COUNT(*) FROM {TABLE} GROUP BY {col} ORDER BY COUNT(*) DESC")
            rows = cur.fetchall()
            print(f"\n  {col}:")
            for v, n in rows:
                print(f"    {repr(v):30s} → {n:>6} registros")
        except Exception as e:
            print(f"  {col}: erro ({e})")

    # ── 3. JOIN com VS_VENDAS ─────────────────────────────────────────────────
    print()
    print("=" * 60)
    print(f"JOIN {TABLE} × VS_VENDAS — amostra de 10 notas recentes")
    print("=" * 60)
    join_cols = ["f.CONT_NOTA"] + [f"f.{c}" for c in candidates[:8]]
    try:
        cur.execute(f"""
            SELECT FIRST 10 {', '.join(join_cols)}
            FROM {TABLE} f
            JOIN VS_VENDAS v ON v.CONT_NOTA = f.CONT_NOTA
            ORDER BY f.CONT_NOTA DESC
        """)
        hdr = [d[0] for d in cur.description]
        print("  " + " | ".join(f"{h:20s}" for h in hdr))
        print("  " + "-" * 80)
        for row in cur.fetchall():
            print("  " + " | ".join(f"{str(v):20s}" for v in row))
    except Exception as e:
        print(f"  Erro no JOIN: {e}")

    # ── 4. Impacto do filtro SITUACAO = 'IMPRESSA' ───────────────────────────
    print()
    print("=" * 60)
    print("IMPACTO DO FILTRO — SITUACAO por volume e valor (via JOIN)")
    print("=" * 60)
    situa_col = next((c for c in candidates if "SITUA" in c), None)
    if situa_col:
        try:
            cur.execute(f"""
                SELECT TRIM(f.{situa_col}), COUNT(DISTINCT f.CONT_NOTA), SUM(i.SUBTOTAL)
                FROM {TABLE} f
                JOIN VS_VENDAS v       ON v.CONT_NOTA = f.CONT_NOTA
                JOIN VS_ITENS_VENDA i  ON i.CONT_NOTA = f.CONT_NOTA
                WHERE v.DATAEMISSAO IS NOT NULL AND i.SUBTOTAL > 0
                GROUP BY f.{situa_col}
                ORDER BY COUNT(DISTINCT f.CONT_NOTA) DESC
            """)
            rows = cur.fetchall()
            print(f"\n  Por {situa_col}:")
            for sit, n_nf, total in rows:
                print(f"    {repr(sit):20s} → {n_nf:>5} NFs · R$ {float(total or 0):>15,.2f}")
        except Exception as e:
            print(f"  Erro: {e}")

    # ── 5. Impacto do filtro NATUREZA ─────────────────────────────────────────
    print()
    print("=" * 60)
    print("IMPACTO DO FILTRO — NATUREZA por volume e valor (via JOIN)")
    print("=" * 60)
    natur_col = next((c for c in candidates if "NATUR" in c), None)
    if natur_col:
        try:
            cur.execute(f"""
                SELECT TRIM(f.{natur_col}), COUNT(DISTINCT f.CONT_NOTA), SUM(i.SUBTOTAL)
                FROM {TABLE} f
                JOIN VS_VENDAS v       ON v.CONT_NOTA = f.CONT_NOTA
                JOIN VS_ITENS_VENDA i  ON i.CONT_NOTA = f.CONT_NOTA
                WHERE v.DATAEMISSAO IS NOT NULL AND i.SUBTOTAL > 0
                GROUP BY f.{natur_col}
                ORDER BY SUM(i.SUBTOTAL) DESC
            """)
            rows = cur.fetchall()
            print(f"\n  Por {natur_col}:")
            for nat, n_nf, total in rows:
                print(f"    {repr(nat):30s} → {n_nf:>5} NFs · R$ {float(total or 0):>15,.2f}")
        except Exception as e:
            print(f"  Erro: {e}")
    else:
        print("  Coluna NATUREZA não encontrada nos candidatos.")
        print(f"  Colunas disponíveis: {cols}")

    cur.close()
    conn.close()
    print()
    print("=" * 60)
    print("FIM DO PROBE")
    print("=" * 60)


if __name__ == "__main__":
    probe()
