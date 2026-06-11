# -*- coding: utf-8 -*-
"""Carrega CADA brutils.pyc do projeto e mostra o que o brl_compact compilado produz."""
import glob, importlib.util, os, time, sys
sys.stdout.reconfigure(encoding="utf-8")

pycs = glob.glob("**/brutils*.pyc", recursive=True)
print("brutils*.pyc encontrados:", len(pycs))
for p in pycs:
    mt = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(p)))
    try:
        spec = importlib.util.spec_from_file_location("t_pyc", p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        print(f"\n  {p}")
        print(f"     mtime {mt}")
        print(f"     brl_compact(477002.88) = {m.brl_compact(477002.88)}")
    except Exception as e:
        print(f"\n  {p}  ERRO: {e}")

# e o .py fonte, pra comparar
sys.path.insert(0, "app")
import brutils as B
print(f"\n  FONTE app/brutils.py -> brl_compact(477002.88) = {B.brl_compact(477002.88)}")
