# -*- coding: utf-8 -*-
"""Gera o PDF consolidado (espelha a lógica do painel)."""
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
sys.path.insert(0, APP)
import configs as C, ingest as I, bp as BP, extrato as E, report as R

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = C.load(os.path.join(ROOT, "config"))
dfs = I.load_all(ROOT, cfg)
tx, rs = E.load_transacoes(ROOT)
per = sorted(dfs["periodos"]); fim = per[-1]
ov = E.carregar_overrides(ROOT)
bk = E.buckets_balanco(tx, fim, ov)
cx, _ = E.caixa_real_fim(rs, fim)
B0 = BP.compute(dfs, per, cfg, True, caixa_real=cx, adiant_clientes=bk["adiant"], aporte_socio=0.0, emprestimos=bk["emprestimos"])
aporte_v = max(0.0, B0["DIFERENCA"])

data = R.build_pdf(dfs, per, cfg, True, cx, bk["adiant"], aporte_v, bk["emprestimos"], tx, ov, "Acumulado (2025-2026)")
out = os.path.join(ROOT, "Relatorio_3Amores.pdf")
with open(out, "wb") as f: f.write(data)
print(f"✓ PDF gerado: {os.path.basename(out)}  ({len(data)//1024} KB)")
