# -*- coding: utf-8 -*-
"""1ª DRE (competência) — motor protótipo.
Lê configs + dados reais. CMV ração por CONSUMO (produtos produzidos POSTURA),
impostos das contas reais, depreciação do imobilizado, e baldes CAPEX / Reapropriar / Estoque / Ignorado."""
import os, sys, csv, re, glob, datetime
import pandas as pd
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(BASE, "config")
def path(rel): return os.path.join(BASE, rel.replace("/", os.sep))
def pv(v):
    if v is None or (isinstance(v,float) and pd.isna(v)): return 0.0
    if isinstance(v,(int,float)): return float(v)
    s=str(v).replace("R$","").replace("\xa0","").replace(" ","").strip().replace(".","").replace(",",".")
    try: return float(s)
    except: return 0.0
def brl(x): return f"R$ {x:,.2f}".replace(",","X").replace(".",",").replace("X",".")
def parse_date(v):
    if v is None or (isinstance(v,float) and pd.isna(v)): return None
    if isinstance(v, pd.Timestamp):
        try: return datetime.date(v.year, v.month, v.day)
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
def valid(d): return (d is not None) and (2020 <= d.year <= 2035)
def ymv(d): return d.year*12 + (d.month-1)
def load_csv(name):
    with open(os.path.join(CFG,name), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))

conta_rows=load_csv("config_contas.csv")
conta2linha={r["nome_conta"].strip().upper(): r["linha_dre"] for r in conta_rows}
conta2nat ={r["nome_conta"].strip().upper(): (r["natureza"], r.get("tipo_estoque","")) for r in conta_rows}
cc2info={r["centro_custo"].strip().upper(): r for r in load_csv("config_centros_custo.csv")}
prod2 ={r["produto_original"].strip(): r for r in load_csv("config_produtos.csv")}

desp=defaultdict(lambda: defaultdict(float)); capex=defaultdict(float)
reaprop=defaultdict(float); reaprop_det=defaultdict(float)
estoque=defaultdict(lambda: defaultdict(float)); ignorado=defaultdict(float)
seen_sig=set()
for fp in sorted(glob.glob(os.path.join(path("2.2 DRE - DESEMBOLSO POR DATA DE ENTRADA"), "*.xlsx"))):
    df=pd.read_excel(fp, header=0, dtype=object)
    sig=(df.shape, round(df.iloc[:,6].map(pv).sum(),2))
    if sig in seen_sig:
        print(f"[dedupe] desembolso duplicado IGNORADO: {os.path.basename(fp)}"); continue
    seen_sig.add(sig)
    for _,r in df.iterrows():
        d=parse_date(r.iloc[1]);  val=pv(r.iloc[6])
        if not valid(d) or val==0: continue
        p=f"{d.year}-{d.month:02d}"
        conta="" if pd.isna(r.iloc[3]) else str(r.iloc[3]).strip()
        cc   ="" if pd.isna(r.iloc[4]) else str(r.iloc[4]).strip()
        cu, ccu = conta.upper(), cc.upper()
        if conta=="" or cc=="" or cu not in conta2linha or ccu not in cc2info:
            mot=[]
            mot.append("sem conta" if conta=="" else ("conta não mapeada" if cu not in conta2linha else None))
            mot.append("sem CC" if cc=="" else ("CC não mapeado" if ccu not in cc2info else None))
            reaprop[p]+=val; reaprop_det[" + ".join([m for m in mot if m])]+=val; continue
        linha=conta2linha[cu]; nat=conta2nat[cu][0]; forca=cc2info[ccu].get("forca_capex","N")=="S"
        if linha=="IGNORAR" or nat=="IGNORAR": ignorado[p]+=val; continue
        if forca or nat=="CAPEX": capex[p]+=val; continue
        if nat=="INVENTARIAVEL": estoque[p][conta2nat[cu][1] or "OUTROS"]+=val; continue
        desp[p][linha]+=val

rec=defaultdict(lambda: defaultdict(float)); descarte=defaultdict(float); naoclass=defaultdict(float)
df=pd.read_excel(path("2.1 DRE - FATURAMENTO POR DATA DE EMISSÃO/notas_fiscais emissão 2025 a 04.2026.xlsx"), header=0, dtype=object)
for _,r in df.iterrows():
    d=parse_date(r.iloc[3]); val=pv(r.iloc[8])
    if not valid(d) or val==0: continue
    p=f"{d.year}-{d.month:02d}"
    prod="" if pd.isna(r.iloc[5]) else str(r.iloc[5]).strip()
    info=prod2.get(prod)
    if not info: naoclass[p]+=val; continue
    lid=info["linha_id"]
    if lid=="IGNORAR": continue
    if lid=="DESCARTE_AVES": descarte[p]+=val; continue
    rec[p][lid]+=val

racao=defaultdict(float)
prdf=pd.read_excel(path("4 PRODUTOS PRODUZIDOS - MOVIMENTAÇÃO DE ESTOQUE/Relatório de Produtos Produzidos 2025 a 04.2026.XLS"), header=0, dtype=object, engine="xlrd")
def feed_kind(desc):
    x=str(desc).upper()
    if "OVOS" in x: return "OVOS"
    if "PRE POSTURA" in x or "PRE-POSTURA" in x: return "RECRIA"
    if "POSTURA" in x: return "POSTURA"
    if any(k in x for k in ("INICIAL","CRESCIMENTO","MATURIDADE")): return "RECRIA"
    return "OUTRO"
for _,r in prdf.iterrows():
    if feed_kind(r.iloc[2])!="POSTURA": continue
    d=parse_date(r.iloc[7])
    if valid(d): racao[f"{d.year}-{d.month:02d}"]+=pv(r.iloc[6])

im=pd.read_excel(path("3 LEVANTAMENTO DE ATIVOS/ATIVOS/Registro_Imobilizado_TresAmores.xlsx"), sheet_name="Registro de Imobilizado", header=3, dtype=object)
assets=[]
for i in range(len(im)):
    dep=pv(im.iloc[i,15]); st=str(im.iloc[i,10]).strip().upper(); acq=parse_date(im.iloc[i,8])
    if dep>0 and "USO" in st and acq: assets.append((ymv(acq),dep))
def deprec_period(ps,pe):
    return sum(dep*max(0, pe-max(a,ps)+1) for a,dep in assets)

def vals(periodos):
    g=lambda L: sum(desp[p].get(L,0) for p in periodos)
    r=lambda L: sum(rec[p].get(L,0) for p in periodos)
    V={}
    V["BRA"]=sum(r("BRA_"+t) for t in ["GR","MED","TA","T1"])
    V["VER"]=sum(r("VER_"+t) for t in ["GR","EXT","TA","JUM","T1","MED","T2"])
    V["CAI"]=sum(r("CAI_"+t) for t in ["GR","EXT","TA","JUM","PEQ"])
    V["PLT"]=sum(r("PLT_"+t) for t in ["BNP","ABO","CHU","BNV","BDA","JILO","PIM","ABA","INH"])
    V["FAT_BRUTO"]=V["BRA"]+V["VER"]+V["CAI"]+V["PLT"]
    V["DED_ICMS"]=g("DED_ICMS"); V["DED_PIS"]=g("DED_PIS"); V["DED_COFINS"]=g("DED_COFINS")
    V["DED_TOTAL"]=V["DED_ICMS"]+V["DED_PIS"]+V["DED_COFINS"]; V["REC_LIQ"]=V["FAT_BRUTO"]-V["DED_TOTAL"]
    V["CMV_RACAO"]=sum(racao[p] for p in periodos); V["CMV_EMBAL"]=sum(estoque[p].get("EMBALAGEM",0) for p in periodos)
    V["CMV_SAUDE"]=g("CMV_SAUDE"); V["CMV_ENERGIA"]=g("CMV_ENERGIA")+g("OPER_GAS")
    V["CMV_MOTER"]=g("CMV_MOTER"); V["CMV_EPI"]=g("CMV_EPI"); V["CMV_MANUT"]=g("CMV_MANUT"); V["CMV_OUTROS"]=g("CMV_OUTROS")
    V["CMV_TOTAL"]=sum(V[k] for k in ["CMV_RACAO","CMV_EMBAL","CMV_SAUDE","CMV_ENERGIA","CMV_MOTER","CMV_EPI","CMV_MANUT","CMV_OUTROS"])
    V["LUCRO_BRUTO"]=V["REC_LIQ"]-V["CMV_TOTAL"]
    grp={"OPER_LOG":["OPER_DIESEL","OPER_FRETE","OPER_PEDAGIO","OPER_COMISSAO","OPER_COMBVEIC","OPER_LOCEQ","OPER_TRASLADO"],
         "OPER_PES":["OPER_FOLHA","OPER_ENCARGOS","OPER_PROLAB","OPER_SEGVIDA","OPER_VALEREF","OPER_SST"],
         "OPER_GES":["OPER_GESTAO","OPER_CONTADOR"],"OPER_TI":["OPER_INTERNET","OPER_ERP","OPER_CERTDIG"],
         "OPER_MKT":["OPER_MKT","OPER_PATROC"],"OPER_ALI":["OPER_REFEI","OPER_REFCARNE","OPER_REFALIM","OPER_LIMP"],
         "OPER_INS":["OPER_LAVOURA","OPER_CONFRAT","OPER_TAXAS","OPER_OUTRASFIX","OPER_RESID"]}
    for k,ls in grp.items(): V[k]=sum(g(x) for x in ls)
    V["OPER_TOTAL"]=sum(V[k] for k in grp); V["EBITDA"]=V["LUCRO_BRUTO"]-V["OPER_TOTAL"]
    ps=[int(p[:4])*12+int(p[5:])-1 for p in periodos]; V["DEPREC"]=deprec_period(min(ps),max(ps))
    V["EBIT"]=V["EBITDA"]-V["DEPREC"]; V["RESULT_FIN"]=0.0; V["LAIR"]=V["EBIT"]+V["RESULT_FIN"]
    V["IMP_IRPJ"]=g("IMP_IRPJ"); V["IMP_CSLL"]=g("IMP_CSLL"); V["IMP_TOTAL"]=V["IMP_IRPJ"]+V["IMP_CSLL"]
    V["LUCRO_LIQ"]=V["LAIR"]-V["IMP_TOTAL"]
    V["CAPEX"]=sum(capex[p] for p in periodos); V["REAPROP"]=sum(reaprop[p] for p in periodos)
    V["ESTOQUE_RACAO"]=sum(estoque[p].get("RACAO",0) for p in periodos); V["ESTOQUE_EMBAL"]=sum(estoque[p].get("EMBALAGEM",0) for p in periodos)
    V["IGNORADO"]=sum(ignorado[p] for p in periodos); V["DESCARTE"]=sum(descarte[p] for p in periodos)
    V["NAOCLASS"]=sum(naoclass[p] for p in periodos)
    return V

A=vals([f"2025-{m:02d}" for m in range(1,13)]); B=vals([f"2026-{m:02d}" for m in range(1,5)])
def L(label,key,ind=0):
    a,b=A.get(key,0),B.get(key,0)
    print(f"{'  '*ind}{label:<40} {brl(a):>17}   {brl(b):>17}")
print("="*86); print(f"{'DRE GERENCIAL (competência)':<44}{'2025 (12m)':>17}   {'2026 (Jan-Abr)':>17}"); print("="*86)
L("( + ) FATURAMENTO BRUTO","FAT_BRUTO")
L("Ovos Branco (Silveira)","BRA",1); L("Ovos Vermelho (Silveira)","VER",1); L("Ovos Caipira (Fazenda)","CAI",1); L("Plantação","PLT",1)
L("( - ) Deduções (ICMS real; PIS/COFINS=0*)","DED_TOTAL")
L("( = ) RECEITA LÍQUIDA","REC_LIQ")
L("( - ) CMV TOTAL","CMV_TOTAL")
L("Ração (CONSUMO postura)","CMV_RACAO",1); L("Embalagens (compras prov.*)","CMV_EMBAL",1); L("Saúde animal","CMV_SAUDE",1)
L("Energia + Gás","CMV_ENERGIA",1); L("Mão de obra direta","CMV_MOTER",1); L("EPI/uniformes","CMV_EPI",1)
L("Manutenção","CMV_MANUT",1); L("Outros diretos","CMV_OUTROS",1)
L("( = ) LUCRO BRUTO","LUCRO_BRUTO")
L("( - ) DESPESAS OPERACIONAIS","OPER_TOTAL")
L("Logística/distribuição","OPER_LOG",1); L("Pessoal administrativo","OPER_PES",1); L("Gestão/serviços ext.","OPER_GES",1)
L("Infra/TI","OPER_TI",1); L("Marketing","OPER_MKT",1); L("Alimentação/higiene","OPER_ALI",1); L("Instalações/outros","OPER_INS",1)
L("( = ) EBITDA","EBITDA")
L("( - ) Depreciação","DEPREC"); L("( = ) EBIT","EBIT")
L("( ± ) Resultado financeiro*","RESULT_FIN"); L("( = ) LAIR","LAIR")
L("( - ) IRPJ","IMP_IRPJ",1); L("( - ) CSLL","IMP_CSLL",1)
L("( = ) LUCRO LÍQUIDO","LUCRO_LIQ")
print("-"*86)
L("» CAPEX (fora da DRE)","CAPEX"); L("» A REAPROPRIAR/VERIFICAR","REAPROP")
L("» Estoque ração (compras MP)","ESTOQUE_RACAO"); L("» Estoque embalagem (compras)","ESTOQUE_EMBAL")
L("» Ignorado (adiant./migração)","IGNORADO"); L("» Descarte de aves (Fase 6)","DESCARTE")
print("\nReapropriar — abertura por motivo (2025+2026):")
for m,v in sorted(reaprop_det.items(), key=lambda x:-x[1]): print(f"   {brl(v):>16}  {m}")
print("\n* PIS/COFINS: sem conta lançada -> não calculado por alíquota. Embalagem: provisório (compras); Fase 2 = consumo. Result. financeiro: sem conta relevante no desembolso.")

# dump config_layout_dre.csv (deliverable, editável)
LAYOUT=[("section","( + ) FATURAMENTO BRUTO","",""),
 ("subtotal","Ovos Branco","BRA","BRA_GR,BRA_MED,BRA_TA,BRA_T1"),("subtotal","Ovos Vermelho","VER","VER_GR,VER_EXT,VER_TA,VER_JUM,VER_T1,VER_MED,VER_T2"),
 ("subtotal","Ovos Caipira","CAI","CAI_GR,CAI_EXT,CAI_TA,CAI_JUM,CAI_PEQ"),("subtotal","Plantação","PLT","PLT_BNP,PLT_ABO,PLT_CHU,PLT_BNV,PLT_BDA,PLT_JILO,PLT_PIM,PLT_ABA,PLT_INH"),
 ("total","( = ) FATURAMENTO BRUTO","FAT_BRUTO",""),("section","( - ) DEDUÇÕES","",""),
 ("detail","ICMS (real)","DED_ICMS",""),("detail","PIS (das contas reais)","DED_PIS",""),("detail","COFINS (das contas reais)","DED_COFINS",""),
 ("subtotal","( = ) RECEITA LÍQUIDA","REC_LIQ",""),("section","( - ) CMV","",""),
 ("detail","Ração (consumo postura)","CMV_RACAO",""),("detail","Embalagens","CMV_EMBAL",""),("detail","Saúde animal","CMV_SAUDE",""),
 ("detail","Energia+Gás","CMV_ENERGIA",""),("detail","Mão de obra direta","CMV_MOTER",""),("detail","EPI","CMV_EPI",""),
 ("detail","Manutenção","CMV_MANUT",""),("detail","Outros diretos","CMV_OUTROS",""),("sectiontotal","( = ) TOTAL CMV","CMV_TOTAL",""),
 ("profit","( = ) LUCRO BRUTO","LUCRO_BRUTO",""),("section","( - ) DESPESAS OPERACIONAIS","",""),
 ("subtotal","Logística","OPER_LOG",""),("subtotal","Pessoal admin","OPER_PES",""),("subtotal","Gestão/serviços","OPER_GES",""),
 ("subtotal","Infra/TI","OPER_TI",""),("subtotal","Marketing","OPER_MKT",""),("subtotal","Alimentação/higiene","OPER_ALI",""),("subtotal","Instalações/outros","OPER_INS",""),
 ("sectiontotal","( = ) TOTAL DESP. OPERACIONAIS","OPER_TOTAL",""),("profit","( = ) EBITDA","EBITDA",""),
 ("detail","( - ) Depreciação","DEPREC",""),("profit","( = ) EBIT","EBIT",""),
 ("detail","( ± ) Resultado financeiro","RESULT_FIN",""),("profit","( = ) LAIR","LAIR",""),
 ("detail","IRPJ (real)","IMP_IRPJ",""),("detail","CSLL (real)","IMP_CSLL",""),("sectiontotal","( = ) TOTAL IMPOSTOS LUCRO","IMP_TOTAL",""),
 ("profit","( = ) LUCRO LÍQUIDO","LUCRO_LIQ",""),
 ("capex","CAPEX (fora da DRE)","CAPEX",""),("nota","A Reapropriar/Verificar","REAPROP",""),("nota","Descarte de aves (Fase 6)","DESCARTE","")]
with open(os.path.join(CFG,"config_layout_dre.csv"),"w",encoding="utf-8-sig",newline="") as f:
    w=csv.writer(f,delimiter=";"); w.writerow(["tipo","label","id","calc"]); w.writerows(LAYOUT)
print("\n-> config/config_layout_dre.csv gerado")
