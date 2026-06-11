# -*- coding: utf-8 -*-
"""Reconciliacao Extrato x Sistema: caixa real (Bradesco+BB via cadeia de aberturas) vs
opening + fluxo do FC-Sistema. Revela os aportes/financiamentos que o sistema nao captura."""
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
sys.path.insert(0, APP)
import configs as C, ingest as I, fc as FC, extrato as E, brutils as B

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = C.load(os.path.join(ROOT, "config"))
dfs = I.load_all(ROOT, cfg)
tx, rs = E.load_transacoes(ROOT)

# saldo de fechamento por conta-mes:
rs = rs.sort_values(["chave", "ano", "mes"]).reset_index(drop=True)
rs["ord"] = rs.ano * 12 + rs.mes
rs["bal_chain"] = rs.groupby("chave")["abertura"].shift(-1)   # abertura[M+1] = fechamento[M]
def bal(r):
    if r.banco in ("Bradesco", "BB"):
        return r.bal_chain if r.bal_chain == r.bal_chain else r.fech_detectado  # last month fallback
    return None
rs["saldo_fim"] = rs.apply(bal, axis=1)

periodos = sorted(set(dfs["periodos"]))
print("=" * 104)
print("CAIXA REAL (Bradesco+BB) x SISTEMA por mes")
print(f"{'mes':8s} {'caixa real fim':>16s} | {'FC ENT':>13s} {'FC SAI':>14s} {'FC liq':>14s} | {'cx ini+ΣFCliq':>15s} {'GAP(real-sist)':>15s}")
print("=" * 104)
op = cfg.saldo_caixa_inicial
acum = op
for p in periodos:
    sub = rs[(rs.periodo == p) & rs.banco.isin(["Bradesco", "BB"])]
    real = sub.saldo_fim.dropna().sum()
    f = FC.compute(dfs, [p])
    acum += f["FLUXO_LIQ"]
    gap = real - acum
    print(f"{p:8s} {B.brl(real):>16s} | {B.brl(f['ENT_OPER']):>13s} {B.brl(f['SAI_TOTAL']):>14s} {B.brl(f['FLUXO_LIQ']):>14s} | {B.brl(acum):>15s} {B.brl(gap):>15s}")

# total
print("\n--- TOTAIS (jan/2025 a fim) ---")
ent_tot = sum(FC.compute(dfs, [p])["ENT_OPER"] for p in periodos)
sai_tot = sum(FC.compute(dfs, [p])["SAI_TOTAL"] for p in periodos)
print(f"FC-Sistema entradas: {B.brl(ent_tot)}  saidas: {B.brl(sai_tot)}  liquido: {B.brl(ent_tot-sai_tot)}")
ult = periodos[-1]
real_fim = rs[(rs.periodo == ult) & rs.banco.isin(["Bradesco", "BB"])].saldo_fim.dropna().sum()
print(f"Caixa real (Brad+BB) fim {ult}: {B.brl(real_fim)}  | abertura: {B.brl(op)}")
print(f"=> Entradas NAO capturadas pelo sistema (aportes+financ.): {B.brl(real_fim - op - (ent_tot - sai_tot))}")

# maiores creditos (candidatos a aporte)
print("\n" + "=" * 104)
print("TOP 25 MAIORES CREDITOS NOS EXTRATOS (candidatos a aporte/financiamento)")
print("=" * 104)
cred = tx[(tx.valor > 0) & (~tx.interno)].copy()
top = cred.sort_values("valor", ascending=False).head(25)
for _, r in top.iterrows():
    print(f"  {str(r.data):11s} {r.banco:9s}/{r.titular:6s} {B.brl(r.valor):>16s}  {str(r.desc)[:46]}")
print(f"\nTotal creditos (nao internos): {B.brl(cred.valor.sum())}  em {len(cred)} lancamentos")
