# -*- coding: utf-8 -*-
"""Fase 7 passo 2: gera Excel dos 'Outros' p/ classificar + Balanço com adiant.+aporte."""
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
sys.path.insert(0, APP)
import configs as C, ingest as I, bp as BP, extrato as E, brutils as B

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = C.load(os.path.join(ROOT, "config"))
dfs = I.load_all(ROOT, cfg)
tx, rs = E.load_transacoes(ROOT)

# 1) Excel dos 'Outros'
outros = E.creditos_outros(tx)
out_path = os.path.join(ROOT, "creditos_outros_para_classificar.xlsx")
outros.to_excel(out_path, index=False, sheet_name="Outros a classificar")
print(f"✓ Excel gerado: {os.path.basename(out_path)}  ({len(outros)} lançs, total {B.brl(outros.valor.sum())})")
print("  Top 8 'Outros':")
for _, r in outros.head(8).iterrows():
    print(f"     {r.periodo} {r.banco:9s} {B.brl(r.valor):>16s}  {str(r.desc)[:40]}")

# 2) Balanço com Fase 7
peracc = sorted(dfs["periodos"]); fim = peracc[-1]
cx, _ = E.caixa_real_fim(rs, fim)
adi, apo = E.passivo_pl_extras(tx, fim)
Bsem = BP.compute(dfs, peracc, cfg, True, caixa_real=cx)
Bcom = BP.compute(dfs, peracc, cfg, True, caixa_real=cx, adiant_clientes=adi, aporte_socio=apo)
print(f"\n=== Balanço posição {fim} ===")
print(f"  Adiant. clientes (AgroMais) -> Passivo: {B.brl(adi)}")
print(f"  Aporte sócio Álvaro -> PL:              {B.brl(apo)}")
print(f"  Passivo: {B.brl(Bsem['PASSIVO_TOTAL'])} -> {B.brl(Bcom['PASSIVO_TOTAL'])}")
print(f"  PL:      {B.brl(Bsem['PL'])} -> {B.brl(Bcom['PL'])}")
print(f"  DIFERENÇA a investigar: {B.brl(Bsem['DIFERENCA'])} -> {B.brl(Bcom['DIFERENCA'])}  (fechou {B.brl(Bsem['DIFERENCA']-Bcom['DIFERENCA'])})")
