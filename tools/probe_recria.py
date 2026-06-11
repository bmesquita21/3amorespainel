# -*- coding: utf-8 -*-
"""Levanta os componentes do custo de recria do lote (ativo biológico) + parâmetros do lote."""
import os, sys, re
import pandas as pd
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def path(rel): return os.path.join(BASE, rel.replace("/", os.sep))
def pv(v):
    if v is None or (isinstance(v,float) and pd.isna(v)): return 0.0
    if isinstance(v,(int,float)): return float(v)
    s=str(v).replace("R$","").replace("\xa0","").replace(" ","").strip().replace(".","").replace(",",".")
    try: return float(s)
    except: return 0.0
def brl(x): return f"R$ {x:,.2f}".replace(",","X").replace(".",",").replace("X",".")
def pdt(v):
    if isinstance(v,(pd.Timestamp,)): return (v.year,v.month)
    s=str(v); m=re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})",s)
    return (int(m.group(3)),int(m.group(2))) if m else None

# 1) Despesas do GALPÃO RECRIA (custos correntes de formação) — no desembolso competência
print("="*70); print("1) DESPESAS com 'RECRIA' no centro de custo (desembolso competência)")
desp = pd.concat([pd.read_excel(path(f), header=0, dtype=object) for f in [
    "2.2 DRE - DESEMBOLSO POR DATA DE ENTRADA/Relatorio_Desembolso_Detalhado 2025 01-01 a 01-06.xlsx",
    "2.2 DRE - DESEMBOLSO POR DATA DE ENTRADA/Relatorio_Desembolso_Detalhado 2025 02-06 a 31-12.xlsx",
    "2.2 DRE - DESEMBOLSO POR DATA DE ENTRADA/Relatorio_Desembolso_Detalhado 01 a 04.2026.xlsx"]], ignore_index=True)
cc_tot=defaultdict(float)
for _,r in desp.iterrows():
    cc=str(r.iloc[4]).strip()
    if "RECRIA" in cc.upper(): cc_tot[cc]+=pv(r.iloc[6])
for cc,v in sorted(cc_tot.items(), key=lambda x:-x[1]): print(f"   {brl(v):>16}  {cc}")
galpao_recria = sum(v for cc,v in cc_tot.items() if "GALPAO RECRIA" in cc.upper() or "GALPÃO RECRIA" in cc.upper())
print(f"   -> GALPÃO RECRIA (custo corrente de formação) = {brl(galpao_recria)}")

# 2) Ração de recria (produtos produzidos) por período
print("\n"+"="*70); print("2) RAÇÃO DE RECRIA por mês (produtos produzidos)")
pr=pd.read_excel(path("4 PRODUTOS PRODUZIDOS - MOVIMENTAÇÃO DE ESTOQUE/Relatório de Produtos Produzidos 2025 a 04.2026.XLS"), header=0, dtype=object, engine="xlrd")
rec_feed=defaultdict(float)
for _,r in pr.iterrows():
    d=str(r.iloc[2]).upper()
    if "OVOS" in d: continue
    if "PRE POSTURA" in d or any(k in d for k in ("INICIAL","CRESCIMENTO","MATURIDADE")):
        ym=pdt(r.iloc[7])
        if ym: rec_feed[ym]+=pv(r.iloc[6])
for ym in sorted(rec_feed): print(f"   {ym[0]}-{ym[1]:02d}: {brl(rec_feed[ym])}")
print(f"   -> Ração recria TOTAL = {brl(sum(rec_feed.values()))}")

# 3) Parâmetros do lote (DADOS GERAIS DA RECRIA.XLS)
print("\n"+"="*70); print("3) DADOS GERAIS DA RECRIA (parâmetros do lote)")
dg=pd.read_excel(path("RECRIA HISTÓRICO/DADOS GERAIS DA RECRIA.XLS"), header=None, dtype=object, engine="xlrd")
for i in range(min(12, len(dg))):
    vals=[str(dg.iloc[i,j]) for j in range(dg.shape[1]) if pd.notna(dg.iloc[i,j])]
    if vals: print("   ", " | ".join(vals)[:110])

print("\n"+"="*70); print("4) RESUMO custo de formação do lote (ativo biológico)")
print(f"   Pintainhas (registro imobilizado)      = {brl(510459.93)}")
print(f"   Ração de recria (produtos produzidos)  = {brl(sum(rec_feed.values()))}")
print(f"   Galpão Recria (despesas correntes)     = {brl(galpao_recria)}")
print(f"   ----------------------------------------------------")
print(f"   TOTAL custo de recria (estimado)       = {brl(510459.93 + sum(rec_feed.values()) + galpao_recria)}")
