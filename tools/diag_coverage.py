# -*- coding: utf-8 -*-
"""Cobertura REAL de datas por arquivo transacional (qual período cada um realmente tem)."""
import os, sys, re, datetime
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
def pd_(v):
    if v is None or (isinstance(v,float) and pd.isna(v)): return None
    if isinstance(v,(pd.Timestamp,datetime.datetime,datetime.date)): return (v.year,v.month)
    s=str(v).strip(); m=re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})",s)
    if m: return (int(m.group(3)),int(m.group(2)))
    m=re.match(r"(\d{4})-(\d{2})",s)
    if m: return (int(m.group(1)),int(m.group(2)))
    return None
def brl(x): return f"R$ {x:,.2f}".replace(",","X").replace(".",",").replace("X",".")

JOBS=[
 ("DESEMBOLSO '2025' (col1 entrada)","2.2 DRE - DESEMBOLSO POR DATA DE ENTRADA/Relatorio_Desembolso_Detalhado 2025.xlsx",1,6),
 ("DESEMBOLSO '2026' (col1 entrada)","2.2 DRE - DESEMBOLSO POR DATA DE ENTRADA/Relatorio_Desembolso_Detalhado 01 a 04.2026.xlsx",1,6),
 ("CONTAS PAGAS '2025' (col5 pgto)","1.1 FLUXO DE CAIXA - DESEMBOLSO POR DATA DE PAGAMENTO/Relatorio_Contas_Pagas_Detalhado 01 a 12.2025.xlsx",5,6),
 ("CONTAS PAGAS '2026' (col5 pgto)","1.1 FLUXO DE CAIXA - DESEMBOLSO POR DATA DE PAGAMENTO/Relatorio_Contas_Pagas_Detalhado 01 a 04.2026.xlsx",5,6),
 ("EMISSÃO (col3)","2.1 DRE - FATURAMENTO POR DATA DE EMISSÃO/notas_fiscais emissão 2025 a 04.2026.xlsx",3,8),
 ("RECEBIDAS (col4 pgto)","1.2 FLUXO DE CAIXA - FATURAMENTO POR DATA DE RECEBIMENTO/notas_fiscais 2025 a 04.2026 - recebidas.xlsx",4,8),
]
for label, rel, dc, vc in JOBS:
    try:
        df=pd.read_excel(path(rel), header=0, dtype=object)
    except Exception as e:
        print(f"{label}: ERRO {e}"); continue
    ym=defaultdict(float); none=0
    for _,r in df.iterrows():
        k=pd_(r.iloc[dc])
        if k is None: none+=1; continue
        ym[k]+=pv(r.iloc[vc])
    anos=defaultdict(lambda:[0.0,set()])
    for (y,m),v in ym.items(): anos[y][0]+=v; anos[y][1].add(m)
    print(f"\n### {label}  ({len(df)} linhas, sem-data={none})")
    for y in sorted(anos):
        meses=sorted(anos[y][1])
        print(f"   {y}: meses {meses}  total {brl(anos[y][0])}")
