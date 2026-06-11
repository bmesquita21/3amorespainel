# -*- coding: utf-8 -*-
"""Testa: rótulo manual 'mutuo' -> Passivo; carregar_overrides; regenera template com 'id' (tid)."""
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
sys.path.insert(0, APP)
import configs as C, ingest as I, bp as BP, extrato as E, brutils as B

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = C.load(os.path.join(ROOT, "config"))
dfs = I.load_all(ROOT, cfg)
tx, rs = E.load_transacoes(ROOT)
fim = sorted(dfs["periodos"])[-1]

outros = E.creditos_outros(tx)
top = outros.iloc[0]
print(f"maior 'Outros': tid={top.tid}  {B.brl(top.valor)}  {str(top.desc)[:40]}")

ov = {top.tid: "mutuo"}
b0 = E.buckets_balanco(tx, fim)
b1 = E.buckets_balanco(tx, fim, ov)
print("buckets SEM rótulo:", {k: round(v) for k, v in b0.items()})
print("buckets COM 1 'mutuo':", {k: round(v) for k, v in b1.items()}, "<- empréstimos sobe pelo valor do lançamento")

# BP com o empréstimo/mútuo
cx, _ = E.caixa_real_fim(rs, fim)
Bv = BP.compute(dfs, sorted(dfs["periodos"]), cfg, True, caixa_real=cx,
                adiant_clientes=b1["adiant"], aporte_socio=b1["aporte"], emprestimos=b1["emprestimos"])
print(f"BP: EMPRESTIMOS={B.brl(Bv['EMPRESTIMOS'])}  Passivo={B.brl(Bv['PASSIVO_TOTAL'])}  Diferença={B.brl(Bv['DIFERENCA'])}")

# carregar_overrides via CSV temporário
tcsv = os.path.join(ROOT, "config", "creditos_natureza.csv")
with open(tcsv, "w", encoding="utf-8") as f:
    f.write("tid;natureza\n%s;mutuo\n" % top.tid)
ov2 = E.carregar_overrides(ROOT)
print(f"carregar_overrides: {len(ov2)} rótulo(s) lidos; '{top.tid}' -> '{ov2.get(top.tid)}'")
os.remove(tcsv)

# regenera template com coluna tid (id)
outpath = os.path.join(ROOT, "creditos_outros_para_classificar.xlsx")
outros.to_excel(outpath, index=False)
print(f"✓ template regenerado c/ coluna 'tid': {os.path.basename(outpath)} ({len(outros)} linhas, cols={list(outros.columns)})")
