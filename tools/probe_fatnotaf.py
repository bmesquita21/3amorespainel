# -*- coding: utf-8 -*-
"""Diagnóstico da tabela FATNOTAF no Firebird.

    docker exec painel-3amores python tools/probe_fatnotaf.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from db import get_conn

def probe():
    conn = get_conn()
    cur  = conn.cursor()

    print("=" * 60)
    print("COLUNAS de FATNOTAF")
    print("=" * 60)
    cur.execute("SELECT FIRST 1 * FROM FATNOTAF")
    cols = [d[0] for d in cur.description]
    for c in cols:
        print(f"  {c}")

    # Campos que provavelmente indicam situação / natureza / tipo
    candidates = [c for c in cols if any(k in c.upper() for k in
        ("SITUA", "STATUS", "TIPO", "NATUR", "CANCEL", "CODOP", "OPERAC", "MODAL", "MOVIM"))]

    print()
    print("=" * 60)
    print("VALORES DISTINTOS — campos de status/situação/tipo/natureza")
    print("=" * 60)
    for col in candidates:
        try:
            cur.execute(f"SELECT {col}, COUNT(*) FROM FATNOTAF GROUP BY {col} ORDER BY COUNT(*) DESC")
            rows = cur.fetchall()
            print(f"\n  {col}:")
            for v, n in rows:
                print(f"    {repr(v)} → {n} registros")
        except Exception as e:
            print(f"  {col}: erro ({e})")

    print()
    print("=" * 60)
    print("RELACIONAMENTO com VS_VENDAS — amostra do JOIN via CONT_NOTA")
    print("=" * 60)
    # Mostra quais colunas relevantes de FATNOTAF aparecem junto com cont_nota
    join_cols = ["f.CONT_NOTA"] + [f"f.{c}" for c in candidates[:8]]
    try:
        cur.execute(f"""
            SELECT FIRST 10 {', '.join(join_cols)}
            FROM FATNOTAF f
            JOIN VS_VENDAS v ON v.CONT_NOTA = f.CONT_NOTA
            ORDER BY f.CONT_NOTA DESC
        """)
        join_desc = [d[0] for d in cur.description]
        print("  " + " | ".join(join_desc))
        print("  " + "-" * 80)
        for row in cur.fetchall():
            print("  " + " | ".join(str(v) for v in row))
    except Exception as e:
        print(f"  Erro no JOIN: {e}")
        # Tenta sem o join p/ confirmar que a coluna existe
        print("\n  Tentando sem JOIN...")
        cur.execute(f"SELECT FIRST 5 CONT_NOTA, {', '.join(c for c in candidates[:6])} FROM FATNOTAF ORDER BY CONT_NOTA DESC")
        for row in cur.fetchall():
            print(f"  {row}")

    print()
    print("=" * 60)
    print("VOLUME — quantas notas por situação (campo mais provável)")
    print("=" * 60)
    # Tenta achar o campo de situação mais relevante e cruzar com VS_VENDAS
    for col in candidates:
        try:
            cur.execute(f"""
                SELECT f.{col}, COUNT(*), SUM(i.SUBTOTAL)
                FROM FATNOTAF f
                JOIN VS_VENDAS v  ON v.CONT_NOTA = f.CONT_NOTA
                JOIN VS_ITENS_VENDA i ON i.CONT_NOTA = f.CONT_NOTA
                WHERE v.DATAEMISSAO IS NOT NULL AND i.SUBTOTAL > 0
                GROUP BY f.{col}
                ORDER BY COUNT(*) DESC
            """)
            rows = cur.fetchall()
            if rows:
                print(f"\n  Por {col}:")
                for sit, n, total in rows:
                    print(f"    {repr(sit)} → {n} itens · R$ {float(total or 0):,.2f}")
                break
        except Exception:
            continue

    cur.close()
    conn.close()

if __name__ == "__main__":
    probe()
