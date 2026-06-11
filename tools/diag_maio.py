# -*- coding: utf-8 -*-
"""Diagnóstico do extrato de maio/2026: leitura + classificação das entradas."""
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
import extrato as E

tx, rs = E.load_transacoes(ROOT)
maio = rs[rs.periodo == "2026-05"] if len(rs) else rs
print(f"=== EXTRATOS maio/2026: {len(maio)} conta(s) ===")
for _, r in maio.iterrows():
    print(f"  {r['chave']:42s} n_tx={r['n_tx']:>3} entradas={r['entradas']:>14,.2f} saidas={r['saidas']:>14,.2f}")

ov = E.carregar_overrides(ROOT)
cl = E.entradas_classificadas(tx, ["2026-05"], ov)
print(f"\n=== CLASSIFICAÇÃO das entradas de maio (colunas: {list(cl.columns)}) ===")
if "classe" in cl.columns:
    g = cl.groupby("classe").valor.agg(["sum", "count"]).sort_values("sum", ascending=False)
    for classe, row in g.iterrows():
        print(f"  {str(classe):42s} R$ {row['sum']:>14,.2f}  ({int(row['count'])} lançs)")
    # top pagadores entre os NÃO identificados (Outros)
    out = cl[cl.classe.astype(str).str.contains("Outro", case=False, na=False)]
    print(f"\n=== TOP pagadores NÃO identificados em maio ({len(out)} lançs, R$ {out.valor.sum():,.2f}) ===")
    if len(out) and "desc" in out.columns:
        top = (out.assign(p=out.desc.astype(str).str.replace(r"^\d+\s*\|?\s*", "", regex=True).str[:48])
                  .groupby("p").valor.agg(["sum", "count"]).sort_values("sum", ascending=False).head(12))
        for d, row in top.iterrows():
            print(f"  R$ {row['sum']:>13,.2f} ({int(row['count'])}x)  {d}")
