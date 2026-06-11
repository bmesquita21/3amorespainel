# -*- coding: utf-8 -*-
"""Fase 0 / ponto 1 — classifica os produtos do faturamento NOVO pela lógica do modelo DRE.
Cor -> Tipo -> Unidade (Branco/Vermelho=Silveira, Caipira=Fazenda). Sinaliza o que não fechar."""
import os, sys, re, csv
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

FILES = {
    "EMISSAO (DRE)":      "2.1 DRE - FATURAMENTO POR DATA DE EMISSÃO/notas_fiscais emissão 2025 a 04.2026.xlsx",
    "RECEBIMENTO (FC)":   "1.2 FLUXO DE CAIXA - FATURAMENTO POR DATA DE RECEBIMENTO/notas_fiscais 2025 a 04.2026 - recebidas.xlsx",
}

def norm(s):
    s = str(s).upper()
    # conserta mojibake comum (UTF-8 lido como latin-1)
    for a,b in [("TRÃŠS","TRÊS"),("Ãƒ","Ã"),("PAPELÃƒO","PAPELÃO"),("Ã‡","Ç"),("Ã•","Õ"),("Ã‰","É")]:
        s = s.replace(a,b)
    return s

def classifica(nome):
    n = norm(nome)
    # --- plantação (não tem 'OVOS') ---
    if "OVOS" not in n:
        if "BANANA" in n and "VITORIA" in n: return ("PLANTACAO","Plantação","Banana Prata Vitória","PLT_BNV","—")
        if "BANANA" in n and ("D AGUA" in n or "D'AGUA" in n or "DAGUA" in n): return ("PLANTACAO","Plantação","Banana D'Água","PLT_BDA","—")
        if "BANANA" in n: return ("PLANTACAO","Plantação","Banana Prata","PLT_BNP","—")
        if "ABOBORA" in n or "ABÓBORA" in n: return ("PLANTACAO","Plantação","Abóbora","PLT_ABO","—")
        if "CHUCHU" in n: return ("PLANTACAO","Plantação","Chuchu","PLT_CHU","—")
        if "JILO" in n or "JILÓ" in n: return ("PLANTACAO","Plantação","Jiló","PLT_JILO","—")
        if "PIMENTAO" in n or "PIMENTÃO" in n: return ("PLANTACAO","Plantação","Pimentão","PLT_PIM","—")
        if "ABACATE" in n: return ("PLANTACAO","Plantação","Abacate","PLT_ABA","—")
        if "INHAME" in n: return ("PLANTACAO","Plantação","Inhame","PLT_INH","—")
        if "VACA" in n or "GADO" in n: return ("IGNORAR","—","Gado (desconsiderado)","IGNORAR","—")
        if "GALINHA" in n: return ("DESCARTE_AVES","Ativo Biológico","Descarte de poedeiras (Fazenda)","DESCARTE_AVES","Fazenda (MATRIZ)")
        return (None,None,None,None,None)  # GAP
    # --- ovos: cor ---
    if "CAIPIRA" in n: cor, cc, uni = "CAI","Caipira","Fazenda (MATRIZ)"
    elif "VERMELHO" in n: cor, cc, uni = "VER","Vermelho","Silveira (FILIAL)"
    elif "BRANCO" in n or "BRANCOS" in n: cor, cc, uni = "BRA","Branco","Silveira (FILIAL)"
    else: return (None,None,None,None,None)  # GAP cor
    # --- tipo / tamanho ---
    tipo = None
    if "EXTRA" in n: tipo="EXT"
    elif "JUMBO" in n: tipo="JUM"
    elif "MEDIO" in n or "MÉDIO" in n: tipo="MED"
    elif "PEQUENO" in n: tipo="PEQ"
    elif re.search(r"\bTIPO A\b", n): tipo="TA"
    elif re.search(r"\bTIPO 1\b", n): tipo="T1"
    elif re.search(r"\bTIPO 2\b", n): tipo="T2"
    elif "GRANDE" in n: tipo="GR"
    if tipo is None: return (None,None,None,None,None)  # GAP tipo
    lid = f"{cor}_{tipo}"
    nome_tipo = {"GR":"Grande","EXT":"Extra","MED":"Médio","TA":"Tipo A","T1":"Tipo 1","T2":"Tipo 2","JUM":"Jumbo","PEQ":"Pequeno"}[tipo]
    return ("OVOS_3AMORES", cc, nome_tipo, lid, uni)

def marca(nome):
    n = norm(nome)
    if "BOM JARDIM" in n or n.rstrip().endswith(" BJ") or "PAPELAO BJ" in n: return "BOM_JARDIM"
    if "AMORES" in n: return "TRES_AMORES"
    return "—"

# coleta produtos distintos (união dos 2 arquivos) com total por arquivo
prod_tot = {k: defaultdict(float) for k in FILES}
all_prods = {}
for label, rel in FILES.items():
    df = pd.read_excel(path(rel), header=0, dtype=object)
    for _, r in df.iterrows():
        p = r.iloc[5]
        if p is None or (isinstance(p,float) and pd.isna(p)): continue
        p = str(p).strip()
        prod_tot[label][p] += pv(r.iloc[8])
        all_prods[p] = True

rows, gaps = [], []
for p in sorted(all_prods):
    grupo, cor, tnome, lid, uni = classifica(p)
    mk = marca(p)
    rows.append((p, grupo, cor, tnome, lid, uni, mk))
    if lid is None: gaps.append(p)

# escreve config_produtos.csv (editável)
os.makedirs(os.path.join(BASE,"config"), exist_ok=True)
out = os.path.join(BASE,"config","config_produtos.csv")
with open(out,"w",encoding="utf-8-sig",newline="") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["produto_original","grupo","cor","tipo","linha_id","unidade","marca"])
    for row in rows: w.writerow([x if x is not None else "" for x in row])

# ===== relatório =====
emi = prod_tot["EMISSAO (DRE)"]
tot_emi = sum(emi.values())
class_emi = sum(v for p,v in emi.items() if classifica(p)[3] is not None)
print(f"PRODUTOS distintos (união): {len(all_prods)} | GAPs (não classificados): {len(gaps)}")
print(f"FATURAMENTO EMISSÃO (DRE): total={brl(tot_emi)} | classificado={brl(class_emi)} ({100*class_emi/tot_emi:.2f}%)\n")

print("="*92)
print(f"{'PRODUTO':<60} {'LINHA':<8} {'UNIDADE':<18} MARCA")
print("="*92)
for p,grupo,cor,tnome,lid,uni,mk in rows:
    flag = "  <<< GAP" if lid is None else ""
    print(f"{norm(p)[:58]:<60} {str(lid or '—'):<8} {str(uni or '—'):<18} {mk}{flag}")

# pivôs
print("\n--- EMISSÃO por UNIDADE ---")
piv = defaultdict(float)
for p,v in emi.items():
    _,_,_,lid,uni = classifica(p); piv[uni or "GAP"] += v
for k in sorted(piv, key=lambda x:-piv[x]): print(f"   {brl(piv[k]):>18}  {k}")
print("\n--- EMISSÃO por COR/LINHA ---")
piv2 = defaultdict(float)
for p,v in emi.items():
    g,cor,t,lid,uni = classifica(p); piv2[lid or "GAP"] += v
for k in sorted(piv2, key=lambda x:-piv2[x]): print(f"   {brl(piv2[k]):>18}  {k}")
print("\n--- RECEBIMENTO (FC) — destino de cada R$ ---")
rec = prod_tot["RECEBIMENTO (FC)"]
def destino(p):
    lid = classifica(p)[3]
    if lid is None: return "GAP (sem classificação)"
    if lid == "IGNORAR": return "IGNORADO (gado/vaca)"
    if lid == "DESCARTE_AVES": return "DESCARTE DE AVES (Fase 6, não é receita)"
    return "RECEITA (ovos + plantação)"
agg = defaultdict(float)
for p,v in rec.items(): agg[destino(p)] += v
tot_rec = sum(rec.values())
for k in sorted(agg, key=lambda x:-agg[x]):
    print(f"   {brl(agg[k]):>16}  ({100*agg[k]/tot_rec:5.2f}%)  {k}")
gaps2 = [p for p in rec if classifica(p)[3] is None]
print("   GAPs restantes:", [norm(g) for g in gaps2] or "NENHUM ✅")
print(f"\n-> atualizado: config/config_produtos.csv")
