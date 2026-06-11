# -*- coding: utf-8 -*-
"""Sondagem p/ montar a 1ª DRE: contas de imposto/financeiras, split ração, depreciação."""
import os, sys, csv
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

# mapa conta->linha do config recém gerado
conta2linha={}
with open(os.path.join(BASE,"config","config_contas.csv"),encoding="utf-8-sig") as f:
    for row in csv.DictReader(f, delimiter=";"):
        conta2linha[row["nome_conta"].strip().upper()] = row["linha_dre"]

d = pd.concat([
    pd.read_excel(path("2.2 DRE - DESEMBOLSO POR DATA DE ENTRADA/Relatorio_Desembolso_Detalhado 2025.xlsx"), header=0, dtype=object),
    pd.read_excel(path("2.2 DRE - DESEMBOLSO POR DATA DE ENTRADA/Relatorio_Desembolso_Detalhado 01 a 04.2026.xlsx"), header=0, dtype=object),
], ignore_index=True)

print("="*70); print("1) CONTAS de IMPOSTO / FINANCEIRAS (no desembolso real)")
KW = ["PIS","COFINS","ISS","ICMS","IRPJ","CSLL","TARIFA","JUROS","IOF","BANC","FINANC","MULTA","DIFAL"]
tot=defaultdict(float)
for _,r in d.iterrows():
    c = "" if pd.isna(r.iloc[3]) else str(r.iloc[3]).strip()
    cu=c.upper()
    if any(k in cu for k in KW):
        tot[(c, conta2linha.get(cu,"?"))]+=pv(r.iloc[6])
for (c,l),v in sorted(tot.items(), key=lambda x:-x[1]):
    print(f"   {brl(v):>16}  [{l:<12}] {c}")

print("\n"+"="*70); print("2) PRODUTOS PRODUZIDOS — split POSTURA(CMV) vs RECRIA(ativo bio) vs OVOS")
pr = pd.read_excel(path("4 PRODUTOS PRODUZIDOS - MOVIMENTAÇÃO DE ESTOQUE/Relatório de Produtos Produzidos 2025 a 04.2026.XLS"), header=0, dtype=object, engine="xlrd")
def feed_kind(desc):
    x=str(desc).upper()
    if "OVOS" in x: return "OVOS (produto acabado)"
    if "PRE POSTURA" in x or "PRE-POSTURA" in x or "PREPOSTURA" in x: return "RECRIA pré-postura"
    if "POSTURA" in x: return "POSTURA (CMV ração)"
    if "INICIAL" in x: return "RECRIA inicial"
    if "CRESCIMENTO" in x: return "RECRIA crescimento"
    if "MATURIDADE" in x: return "RECRIA maturidade"
    return "OUTRO"
kind=defaultdict(float); kind_cnt=defaultdict(int)
for _,r in pr.iterrows():
    k=feed_kind(r.iloc[2]); kind[k]+=pv(r.iloc[6]); kind_cnt[k]+=1
for k,v in sorted(kind.items(), key=lambda x:-x[1]):
    print(f"   {brl(v):>16}  x{kind_cnt[k]:<4} {k}")
postura = sum(v for k,v in kind.items() if k.startswith("POSTURA"))
recria  = sum(v for k,v in kind.items() if k.startswith("RECRIA"))
print(f"   --> CMV ração (POSTURA) = {brl(postura)} | Ativo biológico (RECRIA) = {brl(recria)}")
# ração postura por galpão (Alojamento)
print("\n   POSTURA por galpão (Alojamento):")
gal=defaultdict(float)
for _,r in pr.iterrows():
    if feed_kind(r.iloc[2]).startswith("POSTURA"): gal[str(r.iloc[4]).strip()]+=pv(r.iloc[6])
for g,v in sorted(gal.items(), key=lambda x:-x[1]): print(f"      {brl(v):>16}  {g}")

print("\n"+"="*70); print("3) IMOBILIZADO — depreciação mensal")
im = pd.read_excel(path("3 LEVANTAMENTO DE ATIVOS/ATIVOS/Registro_Imobilizado_TresAmores.xlsx"), sheet_name="Registro de Imobilizado", header=3, dtype=object)
dep_col = im.iloc[:,15]; status_col = im.iloc[:,10]
tot_dep=0.0; by_status=defaultdict(float)
for i in range(len(im)):
    dv = pv(im.iloc[i,15]); st=str(im.iloc[i,10]).strip()
    if dv>0: tot_dep+=dv; by_status[st]+=dv
print(f"   depreciação mensal TOTAL = {brl(tot_dep)}  (anual ~ {brl(tot_dep*12)})")
for s,v in sorted(by_status.items(), key=lambda x:-x[1]): print(f"      {brl(v):>14}/mês  status={s}")
