# -*- coding: utf-8 -*-
"""Valida o parser de extratos: inventario de contas, saldo de abertura 01/01/2025,
e a CADEIA de saldos (saldo_anterior[M] deve ~ saldo_disp do mes anterior)."""
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
import extrato as E

def brl(v):
    if v is None: return "      —      "
    return f"R$ {v:>14,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
df = E.load_extratos(ROOT)
print(f"PDFs lidos: {len(df)}\n")

# erros de leitura
err = df[df.fonte_disp.astype(str).str.startswith("ERRO")]
if len(err):
    print("!! ERROS DE LEITURA:")
    for _, r in err.iterrows(): print("  ", r.arquivo, r.fonte_disp)
    print()

# 1) inventario de contas
print("=" * 96)
print("INVENTARIO DE CONTAS")
print("=" * 96)
inv = df.groupby(["banco", "titular", "conta"]).agg(
    meses=("periodo", "count"), de=("periodo", "min"), ate=("periodo", "max")).reset_index()
for _, r in inv.iterrows():
    print(f"  {r.banco:10s} {r.titular:7s} conta {r.conta:12s} | {r.meses:2d} meses | {r.de} a {r.ate}")

# 2) saldo de abertura 01/01/2025
print("\n" + "=" * 96)
print("SALDO DE CAIXA EM 01/01/2025 (SALDO ANTERIOR do 1o extrato de cada conta em jan/2025)")
print("=" * 96)
tot, ini = E.saldo_abertura(df, "2025-01")
for _, r in ini.iterrows():
    print(f"  {r.chave:34s}  {brl(r.saldo_abertura)}")
print(f"  {'TOTAL ABERTURA 01/01/2025':34s}  {brl(tot)}")

# 3) cadeia de saldos por conta (anterior[M] vs disp[M-1])
print("\n" + "=" * 96)
print("CADEIA DE SALDOS POR CONTA  (col: SALDO ANTERIOR no inicio do mes | saldo disp. topo)")
print("=" * 96)
fm = E.fechamento_mensal(df)
for chave, g in fm.groupby("chave"):
    print(f"\n  >> {chave}")
    g = g.sort_values("ord")
    prev_disp = None
    for _, r in g.iterrows():
        ant = r.saldo_anterior
        flag = ""
        if prev_disp is not None and ant is not None:
            d = abs(ant - prev_disp)
            flag = " OK" if d < max(50.0, abs(prev_disp) * 0.02) else f"  <> dif {brl(ant-prev_disp)} (anterior vs disp mes passado)"
        print(f"     {r.periodo}  ant={brl(ant)}  disp={brl(r.saldo_disp)} [{r.fonte_disp}]{flag}")
        prev_disp = r.saldo_disp
