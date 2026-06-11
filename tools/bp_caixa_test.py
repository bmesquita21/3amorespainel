# -*- coding: utf-8 -*-
"""Confere o Balanço com CAIXA real do extrato (caminho do painel)."""
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
sys.path.insert(0, APP)
import configs as C, ingest as I, bp as BP, extrato as E, brutils as B

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = C.load(os.path.join(ROOT, "config"))
dfs = I.load_all(ROOT, cfg)
tx, rs = E.load_transacoes(ROOT)

for per in (["2025-%02d" % m for m in range(1, 13)], ["2026-%02d" % m for m in range(1, 5)]):
    fim = per[-1]
    cx, brk = E.caixa_real_fim(rs, fim)
    Bsem = BP.compute(dfs, per, cfg, True)
    Bcom = BP.compute(dfs, per, cfg, True, caixa_real=cx)
    print(f"\n=== posição {fim} ===")
    print(f"  Caixa real (extrato): {B.brl(cx)}  [{Bcom['CAIXA_FONTE']}]")
    print(f"  por conta:")
    for _, r in brk.iterrows():
        print(f"     {r.chave:30s} {B.brl(r.saldo_fim):>16s} {'(aprox)' if r.aprox else '(exato)'}")
    print(f"  Diferença a investigar:  SEM caixa real {B.brl(Bsem['DIFERENCA'])}  ->  COM {B.brl(Bcom['DIFERENCA'])}")
