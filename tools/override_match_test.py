# -*- coding: utf-8 -*-
"""Confere que a planilha ANTIGA (sem coluna id) casa os rótulos pelo recalculo do tid."""
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
sys.path.insert(0, APP)
import pandas as pd
import configs as C, ingest as I, extrato as E, brutils as B

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = C.load(os.path.join(ROOT, "config"))
dfs = I.load_all(ROOT, cfg)
tx, rs = E.load_transacoes(ROOT)
fim = sorted(dfs["periodos"])[-1]

outros = E.creditos_outros(tx)
top = outros.iloc[0]
print(f"maior 'Outros': tid={top.tid}  {B.brl(top.valor)}  {str(top.desc)[:35]}")

# simula planilha ANTIGA (sem coluna tid/id), com 2 maiores rotulados
old = outros.head(2)[["periodo", "data", "banco", "titular", "conta", "valor", "desc"]].copy()
old["natureza (preencher)"] = ["aporte", "mutuo"]
tmp = os.path.join(ROOT, "creditos_TESTE_classificado.xlsx")
old.to_excel(tmp, index=False)
print(f"  planilha-teste SEM coluna id, colunas: {list(old.columns)}")

ov = E.carregar_overrides(ROOT)
print(f"  carregar_overrides leu {len(ov)} rótulo(s); top casou? -> {ov.get(top.tid)!r}")
b1 = E.buckets_balanco(tx, fim, ov)
print(f"  buckets c/ rótulos da planilha antiga: aporte={B.brl(b1['aporte'])}  emprestimos={B.brl(b1['emprestimos'])}")
os.remove(tmp)
print("  (planilha-teste removida)")
