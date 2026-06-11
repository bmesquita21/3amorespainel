# -*- coding: utf-8 -*-
"""Investiga linhas de despesa com Conta Contábil vazia (credor) + sinais do faturamento."""
import os, sys
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

d = pd.concat([
    pd.read_excel(path("2.2 DRE - DESEMBOLSO POR DATA DE ENTRADA/Relatorio_Desembolso_Detalhado 2025.xlsx"), header=0, dtype=object),
    pd.read_excel(path("2.2 DRE - DESEMBOLSO POR DATA DE ENTRADA/Relatorio_Desembolso_Detalhado 01 a 04.2026.xlsx"), header=0, dtype=object),
], ignore_index=True)

print("="*70); print("DESPESA com CONTA CONTÁBIL vazia -> distribuição por CREDOR")
cnt, tot = defaultdict(int), defaultdict(float)
for _, r in d.iterrows():
    conta = r.iloc[3]
    if conta is None or (isinstance(conta,float) and pd.isna(conta)) or str(conta).strip()=="":
        cred = str(r.iloc[2]).strip() if pd.notna(r.iloc[2]) else "(credor vazio)"
        cnt[cred]+=1; tot[cred]+=pv(r.iloc[6])
for k in sorted(tot, key=lambda x:-tot[x]):
    print(f"   {brl(tot[k]):>18}  x{cnt[k]:<4}  {k!r}")

print("\n"+"="*70); print("DESPESA com conta vazia -> também o CENTRO DE CUSTO desses casos")
cnt2, tot2 = defaultdict(int), defaultdict(float)
for _, r in d.iterrows():
    conta = r.iloc[3]
    if conta is None or (isinstance(conta,float) and pd.isna(conta)) or str(conta).strip()=="":
        cc = str(r.iloc[4]).strip() if pd.notna(r.iloc[4]) else "(cc vazio)"
        cnt2[cc]+=1; tot2[cc]+=pv(r.iloc[6])
for k in sorted(tot2, key=lambda x:-tot2[x])[:12]:
    print(f"   {brl(tot2[k]):>18}  x{cnt2[k]:<4}  {k!r}")

# ---- Faturamento: sinais ----
print("\n"+"="*70); print("FATURAMENTO emissão -> checagens")
fe = pd.read_excel(path("2.1 DRE - FATURAMENTO POR DATA DE EMISSÃO/notas_fiscais emissão 2025 a 04.2026.xlsx"), header=0, dtype=object)
print("colunas:", list(fe.columns))
vals = fe.iloc[:,8].map(pv)
print(f"linhas={len(fe)} | total={brl(vals.sum())} | negativos={int((vals<0).sum())} | zerados={int((vals==0).sum())}")
# marca embutida no nome do produto
prod = fe.iloc[:,5].astype(str)
for marca in ["TRES AMORES","TRÊS AMORES","TRÃŠS AMORES","GRANJAS BOM JARDIM","BOM JARDIM"]:
    m = prod.str.contains(marca, case=False, na=False)
    print(f"   marca contém {marca!r}: {int(m.sum())} linhas | {brl(vals[m].sum())}")
sem_marca = ~prod.str.contains("AMORES|BOM JARDIM", case=False, na=False)
print(f"   SEM marca reconhecida: {int(sem_marca.sum())} linhas | {brl(vals[sem_marca].sum())}")
print("   exemplos sem marca:", list(prod[sem_marca].unique()[:12]))
