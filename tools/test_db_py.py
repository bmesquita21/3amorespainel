#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Testa conexão com Firebird e verifica mapeamentos das contas/CC.
Executar: py tools/test_db_py.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))

print("1. Testando conexão...")
from db import test_conn
ver = test_conn()
print(f"   OK — Firebird {ver}\n")

print("2. Carregando configs...")
import configs as C
cfg = C.load("config")
print(f"   Contas mapeadas: {len(cfg.conta2linha)}")
print(f"   CCs mapeados:    {len(cfg.cc2info)}")
print(f"   Produtos:        {len(cfg.prod2)}\n")

print("3. Carregando despesas do banco...")
import ingest_db as IDB
from db import get_conn
conn = get_conn()

desp = IDB.ingest_despesa_db(cfg, conn)
print(f"   Total registros: {len(desp)}")
if len(desp):
    print(f"   Destinos: {desp.destino.value_counts().to_dict()}")
    print(f"   Período: {desp.periodo.min()} → {desp.periodo.max()}")
    reapr = desp[desp.destino == "REAPROPRIAR"]
    print(f"   Sem mapeamento: {len(reapr)} ({100*len(reapr)/len(desp):.1f}%)")
    if len(reapr):
        top = reapr.conta.value_counts().head(10)
        print("   Contas sem mapeamento (top 10):")
        for k, v in top.items():
            print(f"     {v:4d}x  {k}")

print("\n4. Carregando receitas do banco...")
rec = IDB.ingest_receita_db(cfg, conn)
print(f"   Total registros: {len(rec)}")
if len(rec):
    print(f"   Destinos: {rec.destino.value_counts().to_dict()}")
    print(f"   Período: {rec.periodo.min()} → {rec.periodo.max()}")
    nclass = rec[rec.destino == "NAOCLASS"]
    if len(nclass):
        print("   Produtos sem mapeamento (top 10):")
        for k, v in nclass.produto.value_counts().head(10).items():
            print(f"     {v:4d}x  {k}")

print("\n5. Carregando FC saídas...")
fc_s = IDB.ingest_fc_saidas_db(cfg, conn)
print(f"   FC saídas: {len(fc_s)} registros  |  Total: R$ {fc_s.valor.sum():,.2f}")

print("\n6. Carregando FC entradas...")
fc_e = IDB.ingest_fc_entradas_db(conn)
print(f"   FC entradas: {len(fc_e)} registros  |  Total: R$ {fc_e.valor.sum():,.2f}")

conn.close()
print("\nTeste concluído com sucesso!")
