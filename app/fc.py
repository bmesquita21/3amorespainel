# -*- coding: utf-8 -*-
"""Fluxo de Caixa (Sistema) — entradas por recebimento, saídas por pagamento, em O/I/F."""

def compute(dfs, periodos):
    P = set(periodos)
    sai = dfs.get("fc_saidas"); ent = dfs.get("fc_entradas")
    o = {}
    o["ENT_OPER"] = float(ent[ent.periodo.isin(P)].valor.sum()) if (ent is not None and len(ent)) else 0.0
    sp = sai[sai.periodo.isin(P)] if (sai is not None and len(sai)) else None
    for cat, key in [("Operacional", "SAI_OPER"), ("Investimento", "SAI_INV"), ("Financiamento", "SAI_FIN")]:
        o[key] = float(sp[sp.categoria == cat].valor.sum()) if (sp is not None and len(sp)) else 0.0
    o["SAI_TOTAL"] = o["SAI_OPER"] + o["SAI_INV"] + o["SAI_FIN"]
    o["FLUXO_OPER"] = o["ENT_OPER"] - o["SAI_OPER"]
    o["FLUXO_LIQ"] = o["ENT_OPER"] - o["SAI_TOTAL"]
    return o

LAYOUT = [
    ("ent", "( + ) Entradas operacionais (recebimentos)", "ENT_OPER"),
    ("sai", "( - ) Saídas operacionais", "SAI_OPER"),
    ("flux", "( = ) Fluxo de Caixa OPERACIONAL", "FLUXO_OPER"),
    ("sai", "( - ) Saídas de investimento (CAPEX/adiantamentos)", "SAI_INV"),
    ("sai", "( - ) Saídas de financiamento", "SAI_FIN"),
    ("flux", "( = ) Fluxo de Caixa LÍQUIDO do período", "FLUXO_LIQ"),
]
