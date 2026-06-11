# -*- coding: utf-8 -*-
"""Gera config_composicao.csv (de-para editável: produto -> custo de embalagem por caixa) a partir do PDF."""
import os, sys, re, csv, unicodedata
import pandas as pd, pdfplumber
sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(BASE, "config"); os.makedirs(CFG, exist_ok=True)
def path(rel): return os.path.join(BASE, rel.replace("/", os.sep))
def pv(s):
    s=str(s).replace("R$","").replace(" ","").strip().replace(".","").replace(",",".")
    try: return float(s)
    except: return 0.0
def norm(s):
    s=unicodedata.normalize("NFKD", str(s)).encode("ascii","ignore").decode().upper()
    return re.sub(r"[^A-Z0-9]+"," ", s).strip()
def unidade(desc):
    d=norm(desc)
    if "CAIPIRA" in d: return "Fazenda"
    if "VERMELHO" in d or "BRANCO" in d: return "Silveira"
    return "—"

with pdfplumber.open(path("0 COMPOSIÇÕES DOS PRODUTOS/Composição Produto Acabado.pdf")) as pdf:
    full="\n".join((p.extract_text() or "") for p in pdf.pages)

rows=[]
for b in full.split("Identificação:")[1:]:
    lines=[l.strip() for l in b.splitlines() if l.strip()]
    if not lines: continue
    nome=lines[0].strip()
    sec=None; emb=None; total=None; ovos=None
    for l in lines:
        if l=="Embalagem": sec="EMB"
        elif l=="Material": sec="MAT"
        elif l.startswith("Total Geral"):
            m=re.search(r"R\$\s*([\d.,]+)", l); total=pv(m.group(1)) if m else None
        elif re.fullmatch(r"R\$\s*[\d.,]+", l) and sec=="EMB": emb=pv(l)
        mo=re.search(r"OVO IN NATURA\s+([\d.,]+)", l)
        if mo: ovos=pv(mo.group(1))
    if emb is not None:
        rows.append([norm(nome), nome, int(ovos or 0), round(emb,2), round(total or 0,2), unidade(nome)])

with open(os.path.join(CFG,"config_composicao.csv"),"w",encoding="utf-8-sig",newline="") as f:
    w=csv.writer(f, delimiter=";")
    w.writerow(["produto_norm","produto_original","ovos_por_caixa","emb_por_caixa","total_por_caixa","unidade"])
    w.writerows(rows)

print(f"config_composicao.csv gerado com {len(rows)} produtos:")
for r in rows: print(f"   emb/caixa=R$ {r[3]:>6.2f} | {r[2]:>3} ovos | {r[1][:55]}")
embs=[r[3] for r in rows]
print(f"\nmédia emb/caixa = R$ {sum(embs)/len(embs):.2f} (usada como estimativa p/ produtos sem receita, até você completar a composição)")
