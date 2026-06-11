# -*- coding: utf-8 -*-
"""Fase 0 — gera config_contas.csv e config_centros_custo.csv a partir do HTML + decisões,
e VALIDA cobertura contra os dados reais de despesa (2.2)."""
import os, sys, re, csv
import pandas as pd
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(BASE, "DRE_GRANJA_DASHBOARD.html")
CFG = os.path.join(BASE, "config"); os.makedirs(CFG, exist_ok=True)
def path(rel): return os.path.join(BASE, rel.replace("/", os.sep))
def pv(v):
    if v is None or (isinstance(v,float) and pd.isna(v)): return 0.0
    if isinstance(v,(int,float)): return float(v)
    s=str(v).replace("R$","").replace("\xa0","").replace(" ","").strip().replace(".","").replace(",",".")
    try: return float(s)
    except: return 0.0
def brl(x): return f"R$ {x:,.2f}".replace(",","X").replace(".",",").replace("X",".")
def wcsv(name, header, rows):
    p = os.path.join(CFG, name)
    with open(p,"w",encoding="utf-8-sig",newline="") as f:
        w = csv.writer(f, delimiter=";"); w.writerow(header); w.writerows(rows)
    return p

# ---------- de-para do HTML ----------
def block(text, name):
    i = text.find("const " + name); m = re.search(r"\n\s*[}\]];", text[i:])
    return text[i:i + (m.end() if m else 5000)]
html = open(HTML, encoding="utf-8").read()
MAPA_CONTA = {k.strip(): v.strip() for k,v in re.findall(r"'([^']*)'\s*:\s*'([^']*)'", block(html,"MAPA_CONTA"))}
NOVO_MAPA_CC = {}
for k, arr in re.findall(r"'([^']*)'\s*:\s*\[([^\]]*)\]", block(html,"NOVO_MAPA_CC")):
    vals = [x.strip().strip("'") for x in arr.split(",")]
    NOVO_MAPA_CC[k.strip()] = (vals+["—","—","—"])[:3]

# ---------- decisões / overrides ----------
OVERRIDE_CONTA = {
    "DI - PROVISÕES DE ENCARGOS SOCIAIS": "OPER_ENCARGOS",
    "CUSTOS INCORRIDOS - TRANSFERENCIA DE SISTEMAS": "IGNORAR",
    "CUSTOS SIENGE": "IGNORAR",
}
MAPA_CONTA.update(OVERRIDE_CONTA)

def natureza(linha):
    if linha in ("CMV_MILHO","CMV_SOJA","CMV_NUCLEO"): return "INVENTARIAVEL","RACAO"
    if linha == "CMV_EMBAL": return "INVENTARIAVEL","EMBALAGEM"
    if linha.startswith("CMV_"): return "DESPESA_DIRETA",""
    if linha.startswith("OPER_"): return "DESPESA_DIRETA",""
    if linha.startswith("DED_"): return "DEDUCAO",""
    if linha.startswith("IMP_"): return "IMPOSTO",""
    if linha.startswith("CAPEX"): return "CAPEX",""
    if linha == "IGNORAR": return "IGNORAR",""
    return "DESPESA_DIRETA",""

# ---------- centro de custo CAPEX (forçado) por palavra-chave ----------
def capex_cc(cc):
    u = cc.upper()
    if "OVOS SILVEIRA" in u: return ("OVOS_3AMORES","FILIAL","Reformas Ovos Silveira")
    if "OVOS FAZENDA" in u:  return ("OVOS_3AMORES","MATRIZ","Reformas Ovos Fazenda")
    if "RAÇÃO" in u or "RACAO" in u: return ("OVOS_3AMORES","MATRIZ","Reformas Ração")
    if "CONDICIONADOR" in u: return ("COMPOSTAGEM","—","Reformas Compostagem")
    if "RECRIA" in u:        return ("OVOS_3AMORES","MATRIZ","Reformas Recria")
    if "LEGUMES" in u:       return ("PLANTACAO","—","Reformas Galpão Legumes")
    if "DURVAL" in u:        return ("PLANTACAO","—","Reformas Plantação Durval")
    if "ROMENIQUE" in u:     return ("PLANTACAO","—","Reformas Plantação Romenique")
    if "GELSON" in u:        return ("PLANTACAO","—","Reformas Plantação Gelson")
    if "ESCRITÓRIO" in u or "ESCRITORIO" in u: return ("OUTROS","—","Reformas Escritório")
    if "PARTICULAR" in u:    return ("PARTICULAR","—","Reformas Particular")
    if "GADO" in u:          return ("OUTROS","—","Reformas Gado")
    if "PATRIMÔNIO" in u or "PATRIMONIO" in u: return ("OVOS_3AMORES","—","Patrimônio/Imobilizado")
    if "ADIANTAMENTO" in u:  return ("OUTROS","—","Adiantamento a Fornecedor")
    return ("OUTROS","—",cc.title())

# ---------- lê dados reais p/ validar ----------
d = pd.concat([
    pd.read_excel(path("2.2 DRE - DESEMBOLSO POR DATA DE ENTRADA/Relatorio_Desembolso_Detalhado 2025.xlsx"), header=0, dtype=object),
    pd.read_excel(path("2.2 DRE - DESEMBOLSO POR DATA DE ENTRADA/Relatorio_Desembolso_Detalhado 01 a 04.2026.xlsx"), header=0, dtype=object),
], ignore_index=True)
contas_reais, cc_reais = defaultdict(float), defaultdict(float)
for _, r in d.iterrows():
    c = r.iloc[3]; cc = r.iloc[4]; val = pv(r.iloc[6])
    c = "" if (c is None or (isinstance(c,float) and pd.isna(c))) else str(c).strip()
    cc = "" if (cc is None or (isinstance(cc,float) and pd.isna(cc))) else str(cc).strip()
    contas_reais[c]+=val; cc_reais[cc]+=val

# ===== config_contas.csv =====
rows=[]
for nome in sorted(MAPA_CONTA):
    if nome=="": continue
    linha = MAPA_CONTA[nome]; nat, est = natureza(linha)
    rows.append([nome, linha, nat, est])
wcsv("config_contas.csv", ["nome_conta","linha_dre","natureza","tipo_estoque"], rows)
faltam_conta = [c for c in contas_reais if c!="" and c not in MAPA_CONTA]
print("="*70); print(f"config_contas.csv: {len(rows)} contas")
inv = [r for r in rows if r[2]=="INVENTARIAVEL"]
print(f"   INVENTARIÁVEIS: {len(inv)} -> {[r[0] for r in inv]}")
print(f"   cobertura dados reais: {len(contas_reais)-len(faltam_conta)-(1 if '' in contas_reais else 0)} de {len([c for c in contas_reais if c!=''])} contas | FALTAM: {faltam_conta or 'nenhuma ✅'}")
if "" in contas_reais:
    print(f"   (linhas com conta vazia: {brl(contas_reais[''])} -> regra credor-fallback na Fase 1)")

# ===== config_centros_custo.csv =====
INV_CC = {"ALMOXARIFADO":("S","ALMOXARIFADO"), "RAÇÕES":("S","RACAO"), "RAÇÃO":("S","RACAO")}
def inv_flag(cc):
    u=cc.upper()
    for key,(s,t) in INV_CC.items():
        if key in u: return s,t
    return "N",""
rows=[]
# base (mapeados)
for cc in sorted(NOVO_MAPA_CC):
    g,sub,det = NOVO_MAPA_CC[cc]; s,t = inv_flag(cc)
    rows.append([cc, g, sub, det, s, t, "N"])
# CAPEX (reais não mapeados)
capex_add=[]
for cc in sorted(cc_reais):
    if cc=="" or cc in NOVO_MAPA_CC: continue
    g,sub,det = capex_cc(cc)
    rows.append([cc, g, sub, det, "N", "", "S"]); capex_add.append((cc,g,det,cc_reais[cc]))
rows.append(["", "SEMCC","—","Sem Centro de Custo","N","","N"])
wcsv("config_centros_custo.csv", ["centro_custo","grupo","subgrupo","detalhe","inventariavel","tipo_estoque","forca_capex"], rows)
faltam_cc = [c for c in cc_reais if c!="" and c not in NOVO_MAPA_CC and c not in [x[0] for x in capex_add]]
print("\n"+"="*70); print(f"config_centros_custo.csv: {len(rows)} centros ({len(NOVO_MAPA_CC)} base + {len(capex_add)} CAPEX + SEMCC)")
print(f"   cobertura dados reais: 100% | FALTAM: {faltam_cc or 'nenhum ✅'}")
print("   CAPEX adicionados (forca_capex=S) — REVISAR:")
for cc,g,det,val in sorted(capex_add, key=lambda x:-x[3]):
    print(f"      {brl(val):>16}  [{g:<12}] {cc}")
print("\n-> gerados: config/config_contas.csv, config/config_centros_custo.csv")
