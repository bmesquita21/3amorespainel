# -*- coding: utf-8 -*-
import os, sys, re, datetime
import pandas as pd
from collections import Counter, defaultdict
sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def path(rel): return os.path.join(BASE, rel.replace("/", os.sep))
def pv(v):
    if v is None or (isinstance(v,float) and pd.isna(v)): return 0.0
    if isinstance(v,(int,float)): return float(v)
    s=str(v).replace("R$","").replace("\xa0","").replace(" ","").strip().replace(".","").replace(",",".")
    try: return float(s)
    except: return 0.0
def parse_date(v):
    if v is None or (isinstance(v,float) and pd.isna(v)): return None
    if isinstance(v, pd.Timestamp):
        try: return datetime.date(v.year,v.month,v.day)
        except: return None
    if isinstance(v,(datetime.datetime,datetime.date)): return datetime.date(v.year,v.month,v.day)
    if isinstance(v,(int,float)):
        try: return datetime.date(1899,12,30)+datetime.timedelta(days=int(v))
        except: return None
    s=str(v).strip()
    m=re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        try: return datetime.date(int(m.group(3)),int(m.group(2)),int(m.group(1)))
        except: return None
    try: return datetime.date.fromisoformat(s[:10])
    except: return None

def diag(label, rel, date_col, val_col):
    print("\n"+"#"*70); print(f"### {label}\n### {rel}")
    df=pd.read_excel(path(rel), header=0, dtype=object)
    print("HEADER:", [f"{i}={c}" for i,c in enumerate(df.columns)])
    print("amostra coluna data (idx %d):"%date_col, [repr(df.iloc[i,date_col]) for i in range(min(3,len(df)))])
    yr=Counter(); valyr=defaultdict(float); none=0
    for _,r in df.iterrows():
        d=parse_date(r.iloc[date_col])
        if d is None: none+=1; continue
        yr[d.year]+=1; valyr[d.year]+=pv(r.iloc[val_col])
    print("linhas=%d | None=%d" % (len(df), none))
    for y in sorted(yr): print(f"   {y}: {yr[y]:>5} linhas | R$ {valyr[y]:,.2f}")

diag("DESEMBOLSO 2025 (col1=DataEntrada,col6=Valor)","2.2 DRE - DESEMBOLSO POR DATA DE ENTRADA/Relatorio_Desembolso_Detalhado 2025.xlsx",1,6)
diag("DESEMBOLSO 2026 (col1,col6)","2.2 DRE - DESEMBOLSO POR DATA DE ENTRADA/Relatorio_Desembolso_Detalhado 01 a 04.2026.xlsx",1,6)
diag("EMISSÃO (col3=Emissão,col8=Valor)","2.1 DRE - FATURAMENTO POR DATA DE EMISSÃO/notas_fiscais emissão 2025 a 04.2026.xlsx",3,8)
