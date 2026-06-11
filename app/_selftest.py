# -*- coding: utf-8 -*-
"""Teste de fumaça do motor (sem Streamlit): confere se os módulos batem com o build_dre."""
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
import configs as C, ingest as I, dre as D, fc as FC, bp as BP, brutils as B
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = C.load(os.path.join(ROOT, "config"))
dfs = I.load_all(ROOT, cfg)
print("periodos:", dfs["periodos"][0], "→", dfs["periodos"][-1], "| dropped:", dfs["dropped"])
print("linhas: despesa=%d receita=%d racao=%d producao=%d imob=%d fc_sai=%d fc_ent=%d" % (
    len(dfs["despesa"]), len(dfs["receita"]), len(dfs["racao"]), len(dfs["producao"]),
    len(dfs["imob"]), len(dfs["fc_saidas"]), len(dfs["fc_entradas"])))
for yr in ["2025", "2026"]:
    per = [p for p in dfs["periodos"] if p[:4] == yr]
    if not per: continue
    Von = D.compute(dfs, per, cfg, True); Voff = D.compute(dfs, per, cfg, False); Fv = FC.compute(dfs, per)
    print(f"\n{yr} DRE ON : LB={B.brl(Von['LUCRO_BRUTO'])} EBITDA={B.brl(Von['EBITDA'])} LL={B.brl(Von['LUCRO_LIQ'])} amortBio={B.brl(Von['AMORT_BIO'])}")
    print(f"{yr} DRE OFF: LB={B.brl(Voff['LUCRO_BRUTO'])} EBITDA={B.brl(Voff['EBITDA'])} LL={B.brl(Voff['LUCRO_LIQ'])}")
    print(f"{yr} FC : ENT={B.brl(Fv['ENT_OPER'])} SAI={B.brl(Fv['SAI_TOTAL'])} Fluxo={B.brl(Fv['FLUXO_LIQ'])}")
    Bv = BP.compute(dfs, per, cfg, True)
    print(f"{yr} BP : Ativo={B.brl(Bv['ATIVO_TOTAL'])} (bio={B.brl(Bv['ATIVO_BIO'])}) Passivo={B.brl(Bv['PASSIVO_TOTAL'])} PL={B.brl(Bv['PL'])} Dif={B.brl(Bv['DIFERENCA'])}")
