# -*- coding: utf-8 -*-
"""Parseia a composição (embalagem/caixa) e cruza com Produtos Produzidos p/ achar o CMV embalagem por consumo."""
import os, sys, re, unicodedata
import pandas as pd, pdfplumber
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
def norm(s):
    s=unicodedata.normalize("NFKD", str(s)).encode("ascii","ignore").decode().upper()
    return re.sub(r"[^A-Z0-9]+"," ", s).strip()

# ---- parse composição ----
def parse_comp():
    comp={}
    with pdfplumber.open(path("0 COMPOSIÇÕES DOS PRODUTOS/Composição Produto Acabado.pdf")) as pdf:
        full="\n".join((p.extract_text() or "") for p in pdf.pages)
    blocks=full.split("Identificação:")
    for b in blocks[1:]:
        lines=[l.strip() for l in b.splitlines() if l.strip()]
        if not lines: continue
        nome=lines[0]
        sec=None; emb=None; total=None
        for l in lines:
            if l=="Embalagem": sec="EMB"
            elif l=="Material": sec="MAT"
            elif l.startswith("Total Geral"):
                m=re.search(r"R\$\s*([\d.,]+)", l); total=pv(m.group(1)) if m else None
            elif re.fullmatch(r"R\$\s*[\d.,]+", l):   # subtotal isolado
                if sec=="EMB": emb=pv(l)
        if emb is not None:
            comp[norm(nome)]=dict(nome=nome, emb=emb, total=total)
    return comp

comp=parse_comp()
print(f"Composição: {len(comp)} produtos com custo de embalagem")
for k in list(comp)[:3]:
    print(f"   emb={brl(comp[k]['emb']):>10} total={brl(comp[k]['total'] or 0):>10}  {comp[k]['nome'][:55]}")

# ---- produtos produzidos: caixas de ovos produzidas ----
pr=pd.read_excel(path("4 PRODUTOS PRODUZIDOS - MOVIMENTAÇÃO DE ESTOQUE/Relatório de Produtos Produzidos 2025 a 04.2026.XLS"), header=0, dtype=object, engine="xlrd")
def parse_date(v):
    import datetime
    if isinstance(v,(pd.Timestamp,)): return (v.year,v.month)
    s=str(v); m=re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})",s)
    return (int(m.group(3)),int(m.group(2))) if m else None
def cor(desc):
    d=norm(desc)
    if "CAIPIRA" in d: return "Caipira","Fazenda"
    if "VERMELHO" in d: return "Vermelho","Silveira"
    if "BRANCO" in d: return "Branco","Silveira"
    return "?","?"

consumo=defaultdict(float); matched=defaultdict(float); nomatch=defaultdict(lambda:[0,0.0])
boxes=0; boxes_total=0; emb_unit=[]
for _,r in pr.iterrows():
    desc=str(r.iloc[2])
    if "OVOS" not in desc.upper(): continue   # só caixas de ovos (produto acabado)
    ym=parse_date(r.iloc[7])
    if not ym or not (2020<=ym[0]<=2035): continue
    qtd=pv(r.iloc[5]); boxes_total+=qtd
    info=comp.get(norm(desc))
    yr=str(ym[0])
    if info:
        v=qtd*info["emb"]; consumo[(yr,cor(desc)[1])]+=v; matched[yr]+=v; boxes+=qtd; emb_unit.append(info["emb"])
    else:
        nomatch[norm(desc)][0]+=1; nomatch[norm(desc)][1]+=qtd

cov = 100*boxes/boxes_total if boxes_total else 0
print(f"\nCaixas: total produzidas={boxes_total:,.0f} | com composição={boxes:,.0f} ({cov:.1f}%) | sem={boxes_total-boxes:,.0f}")
print(f"Custo embalagem/caixa nas 8 receitas: min={brl(min(set(emb_unit)))} max={brl(max(set(emb_unit)))}")
print("\nCMV EMBALAGEM por CONSUMO (composição x caixas produzidas):")
for yr in ["2025","2026"]:
    sil=consumo.get((yr,"Silveira"),0); faz=consumo.get((yr,"Fazenda"),0)
    print(f"   {yr}: Silveira={brl(sil)} | Fazenda={brl(faz)} | TOTAL={brl(sil+faz)}")

if nomatch:
    print(f"\nProdutos produzidos SEM composição ({len(nomatch)}):")
    for k,(c,q) in sorted(nomatch.items(), key=lambda x:-x[1][1])[:15]:
        print(f"   x{c:<4} qtd={q:>10,.0f}  {k[:60]}")
