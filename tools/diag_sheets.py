# -*- coding: utf-8 -*-
import os, sys, re, datetime
import pandas as pd
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def path(rel): return os.path.join(BASE, rel.replace("/", os.sep))
def yr_of(v):
    if isinstance(v,(pd.Timestamp,datetime.datetime,datetime.date)): return v.year
    s=str(v); m=re.search(r"/(\d{4})", s) or re.match(r"(\d{4})-", s)
    return int(m.group(1)) if m else None

for rel in ["2.2 DRE - DESEMBOLSO POR DATA DE ENTRADA/Relatorio_Desembolso_Detalhado 2025.xlsx",
            "2.2 DRE - DESEMBOLSO POR DATA DE ENTRADA/Relatorio_Desembolso_Detalhado 01 a 04.2026.xlsx"]:
    print("\n"+"#"*70); print("###", rel)
    xl = pd.ExcelFile(path(rel), engine="openpyxl")
    print("ABAS:", xl.sheet_names)
    for sh in xl.sheet_names:
        df = xl.parse(sh, header=0, dtype=object)
        yrs = Counter(y for y in (yr_of(df.iloc[i,1]) for i in range(len(df))) if y)
        print(f"   aba '{sh}': {df.shape[0]} linhas x {df.shape[1]} cols | anos(col1)={dict(sorted(yrs.items()))}")
