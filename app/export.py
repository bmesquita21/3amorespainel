# -*- coding: utf-8 -*-
"""Empacotamento: exporta as peças (DRE, Fluxo de Caixa, Balanço, Indicadores, Reconciliação)
para um único arquivo Excel (1 aba por peça). Usado pelo botão 'Exportar tudo' no painel."""
import io
import pandas as pd
import dre as D, fc as FC, bp as BP, extrato as EX


def _layout_df(layout, V):
    rows = []
    for t, lab, idk in layout:
        val = V.get(idk) if idk else None
        rows.append({"Linha": lab, "Valor (R$)": (round(float(val), 2) if isinstance(val, (int, float)) else "")})
    return pd.DataFrame(rows)


def _indic_df(ind):
    def v(x): return round(float(x), 4) if isinstance(x, (int, float)) else ""
    return pd.DataFrame([
        {"Indicador": "ROE (LL/PL)", "Valor": v(ind.get("ROE"))},
        {"Indicador": "Liquidez Corrente (AC/PC)", "Valor": v(ind.get("LIQ_CORR"))},
        {"Indicador": "Endividamento (Passivo/PL)", "Valor": v(ind.get("ENDIV"))},
        {"Indicador": "ROCE (EBIT/(Ativo-PC))", "Valor": v(ind.get("ROCE"))},
        {"Indicador": "EBITDA acumulado", "Valor": v(ind.get("_EBITDA"))},
        {"Indicador": "EBIT acumulado", "Valor": v(ind.get("_EBIT"))},
        {"Indicador": "Lucro Líquido acumulado", "Valor": v(ind.get("_LL"))},
    ])


def build_excel(dfs, periodos, cfg, biologico=True, caixa_real=None, adiant=0.0, aporte=0.0, tx_ex=None, emprestimos=0.0, overrides=None):
    """Monta o workbook (bytes) com 1 aba por peça, para o período selecionado."""
    Vd = D.compute(dfs, periodos, cfg, biologico)
    Fv = FC.compute(dfs, periodos)
    Bv = BP.compute(dfs, periodos, cfg, biologico, caixa_real=caixa_real, adiant_clientes=adiant, aporte_socio=aporte, emprestimos=emprestimos)
    ind, _ = BP.indicadores(dfs, periodos, cfg, biologico, caixa_real=caixa_real, adiant_clientes=adiant, aporte_socio=aporte, emprestimos=emprestimos)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xl:
        _layout_df(D.LAYOUT, Vd).to_excel(xl, sheet_name="DRE", index=False)
        _layout_df(FC.LAYOUT, Fv).to_excel(xl, sheet_name="Fluxo de Caixa", index=False)
        _layout_df(BP.LAYOUT, Bv).to_excel(xl, sheet_name="Balanço", index=False)
        _indic_df(ind).to_excel(xl, sheet_name="Indicadores", index=False)
        # Receita por produto/unidade
        rec = dfs.get("receita")
        if rec is not None and len(rec):
            rok = rec[(rec.destino == "RECEITA") & (rec.periodo.isin(set(periodos)))]
            if len(rok):
                rr = rok.groupby(["unidade", "cor"]).valor.sum().reset_index().sort_values("valor", ascending=False)
                rr["valor"] = rr["valor"].round(2)
                rr.to_excel(xl, sheet_name="Receita", index=False)
        # Reconciliação das entradas (extratos) por classe
        if tx_ex is not None and len(tx_ex):
            cl = EX.entradas_classificadas(tx_ex, periodos, overrides)
            if len(cl):
                rc = cl.groupby("classe").valor.agg(["sum", "count"]).reset_index()
                rc.columns = ["Classe de pagador", "Total (R$)", "Lançamentos"]
                rc["Total (R$)"] = rc["Total (R$)"].round(2)
                rc.to_excel(xl, sheet_name="Reconc. entradas", index=False)
        # Reapropriar (pendências fora da DRE)
        desp = dfs.get("despesa")
        if desp is not None and len(desp):
            rea = desp[(desp.destino == "REAPROPRIAR") & (desp.periodo.isin(set(periodos)))]
            if len(rea):
                ra = rea.groupby(["motivo", "cc"]).valor.sum().reset_index().sort_values("valor", ascending=False)
                ra["valor"] = ra["valor"].round(2)
                ra.to_excel(xl, sheet_name="Reapropriar", index=False)
    return buf.getvalue()
