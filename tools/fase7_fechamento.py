# -*- coding: utf-8 -*-
"""Fase 7 - fechamento: move a planilha preenchida p/ o projeto, aplica os rótulos e
mostra o Balanço antes/depois (quanto da Diferença fechou)."""
import os, sys, shutil
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8")
APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
sys.path.insert(0, APP)
import configs as C, ingest as I, bp as BP, extrato as E, brutils as B

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESK = r"C:\Users\Sabrina\OneDrive - Grupo Bom Jardim\Área de Trabalho"

# 1) move a planilha preenchida -> projeto (nome canônico) e remove o template vazio
src = os.path.join(DESK, "CREDITOS_classificar.xlsx")
dest = os.path.join(ROOT, "creditos_outros_classificado.xlsx")
shutil.copy2(src, dest)
print(f"✓ planilha copiada p/ o projeto: {os.path.basename(dest)}")
tpl = os.path.join(ROOT, "creditos_outros_para_classificar.xlsx")
if os.path.exists(tpl): os.remove(tpl); print("  (template vazio antigo removido)")

# 2) carrega tudo e aplica
cfg = C.load(os.path.join(ROOT, "config"))
dfs = I.load_all(ROOT, cfg)
tx, rs = E.load_transacoes(ROOT)
per = sorted(dfs["periodos"]); fim = per[-1]
ov = E.carregar_overrides(ROOT)
print(f"\nrótulos manuais carregados: {len(ov)}")
print("  por natureza:", dict(Counter(E._norm(v).split()[0] if v else "" for v in ov.values())))

bk = E.buckets_balanco(tx, fim, ov)
print(f"\nBUCKETS p/ o Balanço (acumulado até {fim}):")
print(f"  Aporte (sócio/grupo) -> PL:                 {B.brl(bk['aporte'])}")
print(f"  Empréstimos + mútuos -> Passivo:            {B.brl(bk['emprestimos'])}")
print(f"  Adiant. cliente (AgroMais) -> Passivo:      {B.brl(bk['adiant'])}")

# 3) classes (com overrides) e o que sobra em 'Outros'
cl = E.entradas_classificadas(tx, per, ov)
print("\nCRÉDITOS POR CLASSE (após seus rótulos):")
for classe, v in cl.groupby("classe").valor.sum().sort_values(ascending=False).items():
    print(f"  {classe:34s} {B.brl(v)}")

# 4) Balanço antes/depois
cx, _ = E.caixa_real_fim(rs, fim)
Bsem = BP.compute(dfs, per, cfg, True, caixa_real=cx)
Bcom = BP.compute(dfs, per, cfg, True, caixa_real=cx, adiant_clientes=bk["adiant"],
                  aporte_socio=bk["aporte"], emprestimos=bk["emprestimos"])
print(f"\n=== BALANÇO posição {fim} ===")
print(f"  Passivo:  {B.brl(Bsem['PASSIVO_TOTAL'])}  ->  {B.brl(Bcom['PASSIVO_TOTAL'])}")
print(f"  PL:       {B.brl(Bsem['PL'])}  ->  {B.brl(Bcom['PL'])}")
print(f"  DIFERENÇA a investigar:  {B.brl(Bsem['DIFERENCA'])}  ->  {B.brl(Bcom['DIFERENCA'])}")
print(f"  (fechou {B.brl(Bsem['DIFERENCA'] - Bcom['DIFERENCA'])} nesta rodada de rótulos)")
