# -*- coding: utf-8 -*-
"""Balanço Patrimonial (gerencial, snapshot no fim do período) + Indicadores.
Não força o fechamento: mostra 'Diferença a investigar' (§3 do briefing)."""
import dre as D

def _ord(p): return int(p[:4]) * 12 + int(p[5:]) - 1

def _acum(dfs, periodos):
    """Todos os períodos disponíveis até o FIM do período selecionado (snapshot acumulado)."""
    end = _ord(max(periodos))
    return sorted(p for p in dfs["periodos"] if _ord(p) <= end)

def compute(dfs, periodos, cfg, biologico=True, caixa_real=None, adiant_clientes=0.0, aporte_socio=0.0, emprestimos=0.0):
    if not periodos: return {}
    A = _acum(dfs, periodos); As = set(A); end_o = _ord(max(periodos))
    desp, rec, rac, prod = dfs["despesa"], dfs["receita"], dfs["racao"], dfs.get("producao")
    imob, ent, sai = dfs["imob"], dfs["fc_entradas"], dfs["fc_saidas"]
    def S(df, col="valor", mask=None):
        if df is None or len(df) == 0: return 0.0
        d = df[df.periodo.isin(As)]
        if mask is not None: d = d[mask(d)]
        return float(d[col].sum()) if len(d) else 0.0
    V = {}
    # ---------- ATIVO ----------
    ent_a, sai_a = S(ent), S(sai)
    V["DCAIXA_SIST"] = ent_a - sai_a                                           # variação de caixa pelo sistema (memo)
    if caixa_real is not None:
        V["CAIXA"] = float(caixa_real); V["CAIXA_FONTE"] = "extrato (real)"     # saldo real dos extratos bancários
    else:
        V["CAIXA"] = max(0.0, cfg.saldo_caixa_inicial + V["DCAIXA_SIST"])      # fallback: saldo inicial + Δsistema
        V["CAIXA_FONTE"] = "estimado (saldo inicial + Δsistema)"
    V["CR"] = max(0.0, S(rec, mask=lambda d: d.destino == "RECEITA") - ent_a)  # emitido - recebido
    compras = S(desp, mask=lambda d: d.destino == "ESTOQUE")
    consumo = S(rac, "custo") + S(prod, "emb_total")
    V["ESTOQUE"] = max(0.0, compras - consumo)
    if imob is not None and len(imob):
        im = imob[imob.acq.map(lambda a: (a is None) or (a.year * 12 + (a.month - 1) <= end_o))]
        nbio, bio = im[~im.is_bio], im[im.is_bio]
        V["IMOB_BRUTO"] = float(nbio.valor_aquisicao.sum())
        V["DEPREC_ACUM"] = D._deprec(im, A)
        V["IMOB_LIQ"] = V["IMOB_BRUTO"] - V["DEPREC_ACUM"]
        if biologico:
            import biological as BIO
            V["ATIVO_BIO"], _, _ = BIO.asset_value(dfs, cfg, periodos)   # pintainhas+ração recria+galpão − amortização
        else:
            V["ATIVO_BIO"] = float(bio.valor_aquisicao.sum())            # só pintainhas (registro)
        V["CONTAS_PAGAR"] = float(im.saldo_a_pagar.sum())
    else:
        V["IMOB_BRUTO"] = V["DEPREC_ACUM"] = V["IMOB_LIQ"] = V["ATIVO_BIO"] = V["CONTAS_PAGAR"] = 0.0
    V["AC"] = V["CAIXA"] + V["CR"] + V["ESTOQUE"]
    V["ANC"] = V["IMOB_LIQ"] + V["ATIVO_BIO"]
    V["ATIVO_TOTAL"] = V["AC"] + V["ANC"]
    # ---------- PASSIVO ----------
    V["FORNECEDORES"] = 0.0   # a apurar na Fase 7 (reconciliação competência × pago; dados desalinhados p/ estimar agora)
    V["ADIANT_CLI"] = float(adiant_clientes or 0.0)   # adiantamento de clientes (AgroMais) — extratos, Fase 7
    V["EMPRESTIMOS"] = float(emprestimos or 0.0)      # empréstimos bancários + mútuos de partes relacionadas — extratos, Fase 7
    V["APORTES_PAGAR"] = V["CONTAS_PAGAR"]                                                     # CAPEX/aportes não pagos (registro)
    V["PC"] = V["FORNECEDORES"] + V["ADIANT_CLI"] + V["EMPRESTIMOS"] + V["APORTES_PAGAR"]
    V["PNC"] = 0.0
    V["PASSIVO_TOTAL"] = V["PC"] + V["PNC"]
    # ---------- PL ----------
    V["CAPITAL"] = cfg.capital_social
    V["AFAC_SOCIO"] = float(aporte_socio or 0.0)   # aporte do sócio Álvaro (40.108.957) — extratos, Fase 7
    V["PREJ_ACUM"] = D.compute(dfs, A, cfg, biologico)["LUCRO_LIQ"]   # soma dos LL da DRE (mesmo tratamento)
    V["PL"] = V["CAPITAL"] + V["AFAC_SOCIO"] + V["PREJ_ACUM"]
    # ---------- fechamento (NÃO força) ----------
    V["PASS_PL"] = V["PASSIVO_TOTAL"] + V["PL"]
    V["DIFERENCA"] = V["ATIVO_TOTAL"] - V["PASS_PL"]
    return V

def indicadores(dfs, periodos, cfg, biologico=True, caixa_real=None, adiant_clientes=0.0, aporte_socio=0.0, emprestimos=0.0):
    V = compute(dfs, periodos, cfg, biologico, caixa_real, adiant_clientes, aporte_socio, emprestimos)
    A = _acum(dfs, periodos)
    Vd = D.compute(dfs, A, cfg, biologico)
    pl, pc, at = V["PL"], V["PC"], V["ATIVO_TOTAL"]
    def div(a, b): return (a / b) if b else None
    return {
        "ROE": div(V["PREJ_ACUM"], pl),
        "LIQ_CORR": div(V["AC"], pc),
        "ENDIV": div(V["PASSIVO_TOTAL"], pl),
        "ROCE": div(Vd["EBIT"], (at - pc)),
        "_LL": V["PREJ_ACUM"], "_EBITDA": Vd["EBITDA"], "_EBIT": Vd["EBIT"],
    }, V

LAYOUT = [
    ("h", "ATIVO", None), ("h2", "Ativo Circulante", None),
    ("d", "Caixa e equivalentes (Δ sistema)*", "CAIXA"), ("d", "Contas a Receber (emitido − recebido)*", "CR"),
    ("d", "Estoques (compras − consumo)*", "ESTOQUE"), ("st", "Total Ativo Circulante", "AC"),
    ("h2", "Ativo Não Circulante", None),
    ("d", "Imobilizado bruto", "IMOB_BRUTO"), ("d", "(−) Depreciação acumulada", "DEPREC_ACUM"),
    ("d", "Imobilizado líquido", "IMOB_LIQ"), ("d", "Ativo Biológico (plantel)", "ATIVO_BIO"),
    ("st", "Total Ativo Não Circulante", "ANC"), ("t", "= ATIVO TOTAL", "ATIVO_TOTAL"),
    ("h", "PASSIVO + PL", None), ("h2", "Passivo Circulante", None),
    ("d", "Fornecedores a pagar — a apurar (Fase 7)*", "FORNECEDORES"),
    ("d", "Adiantamento de clientes (AgroMais — extrato)", "ADIANT_CLI"),
    ("d", "Empréstimos e mútuos a pagar (extrato)", "EMPRESTIMOS"),
    ("d", "Aportes/CAPEX a pagar (Omega/parceiros)", "APORTES_PAGAR"), ("st", "Total Passivo Circulante", "PC"),
    ("h2", "Patrimônio Líquido", None),
    ("d", "Capital Social (informar)*", "CAPITAL"),
    ("d", "Aporte do sócio/grupo (líquido — via extratos)", "AFAC_SOCIO"),
    ("d", "Prejuízos Acumulados (Σ LL da DRE)", "PREJ_ACUM"),
    ("st", "Total Patrimônio Líquido", "PL"), ("t", "= PASSIVO + PL", "PASS_PL"),
    ("dif", "⚠️ Diferença a investigar (Ativo − Passivo−PL)", "DIFERENCA"),
    ("memo", "memo: Δ Caixa pelo sistema no período (precisa do extrato p/ saldo real)", "DCAIXA_SIST"),
]
