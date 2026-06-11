# -*- coding: utf-8 -*-
"""Varre todos os PDFs Bradesco e lista as linhas onde valor != diff de saldo (fantasmas)."""
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
import extrato as E

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT = os.path.join(ROOT, "1.3 EXTRATO")
for ano in sorted(os.listdir(EXT)):
    yp = os.path.join(EXT, ano)
    if not (os.path.isdir(yp) and ano.isdigit()): continue
    for mof in sorted(os.listdir(yp), key=lambda x: int(x.split()[0]) if x.split()[0].isdigit() else 99):
        mp = os.path.join(yp, mof)
        if not os.path.isdir(mp): continue
        for fn in sorted(os.listdir(mp)):
            if not fn.lower().endswith(".pdf") or "BRADESCO" not in fn.upper(): continue
            txt = E._read_pdf_text(os.path.join(mp, fn))
            R = E._parse_tx(txt, "Bradesco")
            if not R["tx"]: continue
            prev = R["abertura"]; mism = []
            for t in R["tx"]:
                if t["saldo"] is not None and prev is not None:
                    diff = t["saldo"] - prev
                    if abs(diff - t["valor"]) > 0.01:
                        mism.append((t["valor"], t["saldo"], diff, t["desc"][:45]))
                    prev = t["saldo"]
            sv = sum(t["valor"] for t in R["tx"])
            net_calc = (R["abertura"] or 0) + sv
            err = net_calc - (R["fechamento"] or 0)
            if mism or abs(err) > 1:
                print(f"\n=== {ano}/{mof} :: {fn}  (abert={R['abertura']}, fech={R['fechamento']}, erro={err:.2f}, fantasmas={len(mism)})")
                for v, s, d, ds in mism[:8]:
                    print(f"    valor={v:>13.2f}  saldo={s:>13.2f}  diff={d:>13.2f} | {ds}")
