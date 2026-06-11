# -*- coding: utf-8 -*-
"""Valida o fechamento GERENCIAL: aporte = líquido (residual), cliente -> receita (neutro)."""
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
sys.path.insert(0, APP)
import configs as C, ingest as I, bp as BP, extrato as E, brutils as B

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = C.load(os.path.join(ROOT, "config"))
dfs = I.load_all(ROOT, cfg)
tx, rs = E.load_transacoes(ROOT)
per = sorted(dfs["periodos"]); fim = per[-1]
ov = E.carregar_overrides(ROOT)

# classes (com cliente -> receita)
cl = E.entradas_classificadas(tx, per, ov)
print("CRÉDITOS POR CLASSE (após correção cliente->receita):")
for classe, v in cl.groupby("classe").valor.sum().sort_values(ascending=False).items():
    print(f"  {classe:34s} {B.brl(v)}")

bk = E.buckets_balanco(tx, fim, ov)
print(f"\nBUCKETS (face value): adiant(AgroMais)={B.brl(bk['adiant'])}  mútuos/emp={B.brl(bk['emprestimos'])}  aporte_bruto(memo)={B.brl(bk['aporte'])}")

# fechamento gerencial
cx, _ = E.caixa_real_fim(rs, fim)
B0 = BP.compute(dfs, per, cfg, True, caixa_real=cx, adiant_clientes=bk["adiant"], aporte_socio=0.0, emprestimos=bk["emprestimos"])
aporte_liq = max(0.0, B0["DIFERENCA"])
Bf = BP.compute(dfs, per, cfg, True, caixa_real=cx, adiant_clientes=bk["adiant"], aporte_socio=aporte_liq, emprestimos=bk["emprestimos"])
print(f"\n=== BALANÇO GERENCIAL — posição {fim} ===")
print(f"  Aporte do sócio/grupo (LÍQUIDO, residual): {B.brl(aporte_liq)}   [bruto seria {B.brl(bk['aporte'])}]")
print(f"  ATIVO TOTAL: {B.brl(Bf['ATIVO_TOTAL'])}")
print(f"  PASSIVO:     {B.brl(Bf['PASSIVO_TOTAL'])}  (adiant {B.brl(Bf['ADIANT_CLI'])} + mútuos {B.brl(Bf['EMPRESTIMOS'])} + aportes a pagar {B.brl(Bf['APORTES_PAGAR'])})")
print(f"  PL:          {B.brl(Bf['PL'])}  (capital {B.brl(Bf['CAPITAL'])} + aporte {B.brl(Bf['AFAC_SOCIO'])} − prejuízos {B.brl(Bf['PREJ_ACUM'])})")
print(f"  DIFERENÇA:   {B.brl(Bf['DIFERENCA'])}  <-- deve ser ~0")
