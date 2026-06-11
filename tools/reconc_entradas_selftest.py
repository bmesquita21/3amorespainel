# -*- coding: utf-8 -*-
"""Fase 7 - Reconciliacao das ENTRADAS: creditos no banco (por classe de pagador)
x FC-Sistema (recebido) x DRE faturamento (competencia)."""
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
sys.path.insert(0, APP)
import configs as C, ingest as I, dre as D, fc as FC, extrato as E, brutils as B

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = C.load(os.path.join(ROOT, "config"))
dfs = I.load_all(ROOT, cfg)
tx, rs = E.load_transacoes(ROOT)
periodos = sorted(dfs["periodos"])

cl = E.entradas_classificadas(tx)
print(f"creditos (nao internos): {len(cl)}  total {B.brl(cl.valor.sum())}\n")

# total por classe
print("=" * 70)
print("CREDITOS NO BANCO POR CLASSE (jan/25 -> abr/26)")
print("=" * 70)
g = cl.groupby("classe").valor.agg(["sum", "count"]).sort_values("sum", ascending=False)
for classe, r in g.iterrows():
    print(f"  {classe:30s} {B.brl(r['sum']):>18s}  ({int(r['count'])} lanç.)")
print(f"  {'TOTAL':30s} {B.brl(cl.valor.sum()):>18s}")

# por mes: banco operacional (outros) x FC-sistema x DRE faturamento
print("\n" + "=" * 104)
print("ENTRADAS OPERACIONAIS: Banco 'Outros recebimentos' x FC-Sistema (recebido) x DRE faturamento")
print("=" * 104)
print(f"{'mes':8s} {'Banco Outros':>15s} {'Banco AgroMais':>15s} {'Banco Aporte':>14s} {'FC-Sist ENT':>14s} {'DRE faturam.':>14s}")
acc = {}
for p in periodos:
    sub = cl[cl.periodo == p]
    outros = sub[sub.classe == "Outros recebimentos"].valor.sum()
    agro = sub[sub.classe == "Adiant. cliente (AgroMais)"].valor.sum()
    aporte = sub[sub.classe == "Aporte sócio (Álvaro)"].valor.sum()
    fcent = FC.compute(dfs, [p])["ENT_OPER"]
    fat = D.compute(dfs, [p], cfg, True)["FAT_BRUTO"]
    for k, v in [("outros", outros), ("agro", agro), ("aporte", aporte), ("fc", fcent), ("fat", fat)]:
        acc[k] = acc.get(k, 0) + v
    print(f"{p:8s} {B.brl(outros):>15s} {B.brl(agro):>15s} {B.brl(aporte):>14s} {B.brl(fcent):>14s} {B.brl(fat):>14s}")
print("-" * 104)
print(f"{'TOTAL':8s} {B.brl(acc['outros']):>15s} {B.brl(acc['agro']):>15s} {B.brl(acc['aporte']):>14s} {B.brl(acc['fc']):>14s} {B.brl(acc['fat']):>14s}")

print("\n>> LEITURA:")
print(f"   AgroMais (adiantamento de cliente -> PASSIVO): {B.brl(acc['agro'])}")
print(f"   Aporte do sócio Álvaro (40.108.957 -> PL):     {B.brl(acc['aporte'])}")
print(f"   Intercompany (própria, neta):                  {B.brl(g['sum'].get('Intercompany (própria)', 0))}")
print(f"   Outros recebimentos (operacional?):            {B.brl(acc['outros'])}")
print(f"   vs DRE faturamento competência:                {B.brl(acc['fat'])}")
