# -*- coding: utf-8 -*-
"""Dump dos formatos ainda nao mapeados: BB e Santander novo (Santander Empresas)."""
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
import pdfplumber

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALVOS = [
    os.path.join(ROOT, "1.3 EXTRATO", "2026", "3 MARÇO 2026", "MARÇO 2026Tres Amores - BB .pdf"),
    os.path.join(ROOT, "1.3 EXTRATO", "2026", "4 ABRIL 2026", "ABRIL 2026 Tres Amores Matriz  - Santander .pdf"),
]

for fp in ALVOS:
    print("\n" + "=" * 95)
    print("ARQ:", os.path.basename(fp), "| existe:", os.path.exists(fp))
    print("=" * 95)
    if not os.path.exists(fp):
        # tenta achar por prefixo
        d = os.path.dirname(fp)
        if os.path.isdir(d):
            print("  arquivos na pasta:")
            for f in sorted(os.listdir(d)): print("   -", repr(f))
        continue
    with pdfplumber.open(fp) as pdf:
        for pi, page in enumerate(pdf.pages):
            txt = page.extract_text() or ""
            print(f"\n--- pagina {pi+1}/{len(pdf.pages)} ---")
            for i, ln in enumerate(txt.split("\n")):
                print(f"{i:3d}| {ln}")
