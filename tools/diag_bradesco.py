# -*- coding: utf-8 -*-
"""Diagnostico: compara valor parseado vs diferenca de saldos corridos (Bradesco Jan/Matriz)."""
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
import extrato as E

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fp = os.path.join(ROOT, "1.3 EXTRATO", "2025", "1 JANEIRO 2025", "Tres Amores 01.2025 - Bradesco.PDF")
txt = E._read_pdf_text(fp)
R = E._parse_tx(txt, "Bradesco")
print("abertura:", R["abertura"], "| fechamento:", R["fechamento"], "| n_tx:", len(R["tx"]))
prev = R["abertura"]
bad = 0
print(">>> DESCASAMENTOS (valor != diff de saldo) em TODAS as transacoes:")
for i, t in enumerate(R["tx"]):
    diff = t["saldo"] - prev if (t["saldo"] is not None and prev is not None) else None
    if diff is not None and abs(diff - t["valor"]) > 0.01:
        print(f"{i:3d} {str(t['data']):10s} v={t['valor']:>13.2f} saldo={t['saldo']:>13.2f} diff={diff:>13.2f} | {t['desc'][:50]}")
        bad += 1
    prev = t["saldo"]
print(f"\ntotal descasamentos: {bad}")

print("\n>>> ULTIMAS 22 LINHAS BRUTAS (seção Invest Fácil):")
ne = [l for l in txt.split("\n") if l.strip()]
for l in ne[-22:]:
    print("   |", l)
# soma total
sv = sum(t["valor"] for t in R["tx"])
print(f"Soma valores={sv:.2f}  | abertura+soma={R['abertura']+sv:.2f}  | fechamento={R['fechamento']:.2f}")
