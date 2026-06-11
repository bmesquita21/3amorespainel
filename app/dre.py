# -*- coding: utf-8 -*-
"""Monta a DRE (competência) para um conjunto de períodos a partir dos DataFrames ingeridos."""

def _deprec(imob, periodos):
    if imob is None or len(imob) == 0: return 0.0
    ms = [int(p[:4]) * 12 + int(p[5:]) - 1 for p in periodos]
    ps, pe = min(ms), max(ms)
    tot = 0.0
    for _, a in imob.iterrows():
        if not a["em_uso"] or a["acq"] is None: continue
        am = a["acq"].year * 12 + (a["acq"].month - 1)
        m = pe - max(am, ps) + 1
        if m > 0: tot += a["deprec_mensal"] * m
    return tot

GRUPOS_OPER = {
    "OPER_LOG": ["OPER_DIESEL", "OPER_FRETE", "OPER_PEDAGIO", "OPER_COMISSAO", "OPER_COMBVEIC", "OPER_LOCEQ", "OPER_TRASLADO"],
    "OPER_PES": ["OPER_FOLHA", "OPER_ENCARGOS", "OPER_PROLAB", "OPER_SEGVIDA", "OPER_VALEREF", "OPER_SST"],
    "OPER_GES": ["OPER_GESTAO", "OPER_CONTADOR"], "OPER_TI": ["OPER_INTERNET", "OPER_ERP", "OPER_CERTDIG"],
    "OPER_MKT": ["OPER_MKT", "OPER_PATROC"], "OPER_ALI": ["OPER_REFEI", "OPER_REFCARNE", "OPER_REFALIM", "OPER_LIMP"],
    "OPER_INS": ["OPER_LAVOURA", "OPER_CONFRAT", "OPER_TAXAS", "OPER_OUTRASFIX", "OPER_RESID"],
}
# id da cascata -> linhas_dre que o compõem (para rastrear até a conta original)
COMPOE = dict(GRUPOS_OPER)
COMPOE.update({"CMV_ENERGIA": ["CMV_ENERGIA", "OPER_GAS"], "CMV_SAUDE": ["CMV_SAUDE"], "CMV_MOTER": ["CMV_MOTER"],
    "CMV_EPI": ["CMV_EPI"], "CMV_MANUT": ["CMV_MANUT"], "CMV_OUTROS": ["CMV_OUTROS"],
    "DED_ICMS": ["DED_ICMS"], "IMP_IRPJ": ["IMP_IRPJ"], "IMP_CSLL": ["IMP_CSLL"]})

def compute(dfs, periodos, cfg=None, biologico=True):
    import biological as BIO
    desp, rec, rac = dfs["despesa"], dfs["receita"], dfs["racao"]
    P = set(periodos)
    dre = desp[(desp.destino == "DRE") & (desp.periodo.isin(P))] if len(desp) else desp
    if biologico and len(dre):
        dre = dre[~dre.cc.str.upper().str.contains("GALPAO RECRIA", na=False)]  # recria capitalizada no ativo biológico
    g = lambda L: float(dre[dre.linha_dre == L].valor.sum()) if len(dre) else 0.0
    rok = rec[(rec.destino == "RECEITA") & (rec.periodo.isin(P))] if len(rec) else rec
    rcor = lambda c: float(rok[rok.cor == c].valor.sum()) if len(rok) else 0.0
    V = {}
    V["BRA"], V["VER"], V["CAI"], V["PLT"] = rcor("Branco"), rcor("Vermelho"), rcor("Caipira"), rcor("Plantação")
    V["FAT_BRUTO"] = V["BRA"] + V["VER"] + V["CAI"] + V["PLT"]
    V["DED_ICMS"], V["DED_PIS"], V["DED_COFINS"] = g("DED_ICMS"), g("DED_PIS"), g("DED_COFINS")
    V["DED_TOTAL"] = V["DED_ICMS"] + V["DED_PIS"] + V["DED_COFINS"]
    V["REC_LIQ"] = V["FAT_BRUTO"] - V["DED_TOTAL"]
    rp = rac[(rac.fase == "POSTURA") & (rac.periodo.isin(P))] if len(rac) else rac
    V["CMV_RACAO"] = float(rp.custo.sum()) if len(rp) else 0.0
    if not biologico and len(rac):   # sem tratamento: ração de recria vira despesa
        rr = rac[(rac.fase == "RECRIA") & (rac.periodo.isin(P))]
        V["CMV_RACAO"] += float(rr.custo.sum()) if len(rr) else 0.0
    prod = dfs.get("producao")
    if prod is not None and len(prod):
        V["CMV_EMBAL"] = float(prod[prod.periodo.isin(P)].emb_total.sum())  # consumo (composição x caixas)
    else:
        V["CMV_EMBAL"] = 0.0
    V["CMV_SAUDE"] = g("CMV_SAUDE"); V["CMV_ENERGIA"] = g("CMV_ENERGIA") + g("OPER_GAS")
    V["CMV_MOTER"] = g("CMV_MOTER"); V["CMV_EPI"] = g("CMV_EPI"); V["CMV_MANUT"] = g("CMV_MANUT"); V["CMV_OUTROS"] = g("CMV_OUTROS")
    V["AMORT_BIO"] = BIO.amort_periodos(dfs, cfg, periodos) if (biologico and cfg is not None) else 0.0
    V["CMV_TOTAL"] = sum(V[k] for k in ["CMV_RACAO", "CMV_EMBAL", "CMV_SAUDE", "CMV_ENERGIA", "CMV_MOTER", "CMV_EPI", "CMV_MANUT", "CMV_OUTROS", "AMORT_BIO"])
    V["LUCRO_BRUTO"] = V["REC_LIQ"] - V["CMV_TOTAL"]
    for k, ls in GRUPOS_OPER.items(): V[k] = sum(g(x) for x in ls)
    V["OPER_TOTAL"] = sum(V[k] for k in GRUPOS_OPER)
    V["EBITDA"] = V["LUCRO_BRUTO"] - V["OPER_TOTAL"]
    V["DEPREC"] = _deprec(dfs["imob"], periodos); V["EBIT"] = V["EBITDA"] - V["DEPREC"]
    V["RESULT_FIN"] = 0.0; V["LAIR"] = V["EBIT"] + V["RESULT_FIN"]
    V["IMP_IRPJ"] = g("IMP_IRPJ"); V["IMP_CSLL"] = g("IMP_CSLL"); V["IMP_TOTAL"] = V["IMP_IRPJ"] + V["IMP_CSLL"]
    V["LUCRO_LIQ"] = V["LAIR"] - V["IMP_TOTAL"]
    return V

LAYOUT = [
    ("section", "( + ) FATURAMENTO BRUTO", ""),
    ("sub", "Ovos Branco (Silveira)", "BRA"), ("sub", "Ovos Vermelho (Silveira)", "VER"),
    ("sub", "Ovos Caipira (Fazenda)", "CAI"), ("sub", "Plantação", "PLT"),
    ("total", "( = ) FATURAMENTO BRUTO", "FAT_BRUTO"),
    ("section", "( - ) Deduções (impostos s/ venda)", ""),
    ("det", "ICMS (real)", "DED_ICMS"), ("det", "PIS (contas reais)", "DED_PIS"), ("det", "COFINS (contas reais)", "DED_COFINS"),
    ("subtotal", "( = ) RECEITA LÍQUIDA", "REC_LIQ"),
    ("section", "( - ) CMV", ""),
    ("det", "Ração (consumo postura)", "CMV_RACAO"), ("det", "Embalagens", "CMV_EMBAL"), ("det", "Saúde animal", "CMV_SAUDE"),
    ("det", "Energia + Gás", "CMV_ENERGIA"), ("det", "Mão de obra direta", "CMV_MOTER"), ("det", "EPI/uniformes", "CMV_EPI"),
    ("det", "Manutenção", "CMV_MANUT"), ("det", "Outros diretos", "CMV_OUTROS"),
    ("det", "Amortização ativo biológico (recria→GS02)", "AMORT_BIO"),
    ("subtotal", "( = ) TOTAL CMV", "CMV_TOTAL"), ("profit", "( = ) LUCRO BRUTO", "LUCRO_BRUTO"),
    ("section", "( - ) Despesas operacionais", ""),
    ("sub", "Logística/distribuição", "OPER_LOG"), ("sub", "Pessoal administrativo", "OPER_PES"),
    ("sub", "Gestão/serviços", "OPER_GES"), ("sub", "Infra/TI", "OPER_TI"), ("sub", "Marketing", "OPER_MKT"),
    ("sub", "Alimentação/higiene", "OPER_ALI"), ("sub", "Instalações/outros", "OPER_INS"),
    ("subtotal", "( = ) TOTAL DESP. OPERACIONAIS", "OPER_TOTAL"), ("profit", "( = ) EBITDA", "EBITDA"),
    ("det", "( - ) Depreciação", "DEPREC"), ("profit", "( = ) EBIT", "EBIT"),
    ("det", "( ± ) Resultado financeiro", "RESULT_FIN"), ("profit", "( = ) LAIR", "LAIR"),
    ("det", "IRPJ (real)", "IMP_IRPJ"), ("det", "CSLL (real)", "IMP_CSLL"),
    ("profit", "( = ) LUCRO LÍQUIDO", "LUCRO_LIQ"),
]
