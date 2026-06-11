# -*- coding: utf-8 -*-
import os, sys
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fp = os.path.join(BASE, "3 LEVANTAMENTO DE ATIVOS", "ATIVOS", "Registro_Imobilizado_TresAmores.xlsx")
def pv(v):
    try:
        if v is None or (isinstance(v,float) and pd.isna(v)): return 0.0
        if isinstance(v,(int,float)): return float(v)
        s=str(v).replace("R$","").replace("\xa0","").replace(" ","").strip().replace(".","").replace(",",".")
        return float(s)
    except: return 0.0
def brl(x): return f"R$ {x:,.2f}".replace(",","X").replace(".",",").replace("X",".")

df = pd.read_excel(fp, sheet_name="Registro de Imobilizado", header=3, dtype=object)
print("REGISTRO DE IMOBILIZADO — itens (col11=aquisição, col13=saldo a pagar):")
tot=0; totsaldo=0
for i in range(len(df)):
    aq=pv(df.iloc[i,11])
    if aq<=0: continue
    cod=str(df.iloc[i,0]); desc=str(df.iloc[i,1])[:30]; classe=str(df.iloc[i,2])[:22]; saldo=pv(df.iloc[i,13])
    tot+=aq; totsaldo+=saldo
    print(f"   {cod:<8} {brl(aq):>16} saldo={brl(saldo):>14} | {classe:<22} | {desc}")
print(f"\n   SOMA aquisição = {brl(tot)} | SOMA saldo a pagar = {brl(totsaldo)} | nº itens = {sum(1 for i in range(len(df)) if pv(df.iloc[i,11])>0)}")

for sh in ["Resumo por Classe", "Conciliação Contábil"]:
    try:
        d = pd.read_excel(fp, sheet_name=sh, header=None, dtype=object)
        print(f"\n--- {sh} ---")
        for i in range(len(d)):
            vals=[str(d.iloc[i,j]) for j in range(d.shape[1]) if pd.notna(d.iloc[i,j])]
            if vals: print("   ", " | ".join(vals))
    except Exception as e: print(sh, "erro", e)
