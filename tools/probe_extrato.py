# -*- coding: utf-8 -*-
"""Sonda de layout dos extratos (PDF). Dumpa texto das 1as paginas de jan/2025
(Bradesco + Santander) para entender o formato antes de escrever o parser."""
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
import pdfplumber

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JAN = os.path.join(ROOT, "1.3 EXTRATO", "2025", "1 JANEIRO 2025")

def dump(fp, max_lines=70):
    print("\n" + "=" * 90)
    print("ARQ:", os.path.basename(fp))
    print("=" * 90)
    try:
        with pdfplumber.open(fp) as pdf:
            print(f"[{len(pdf.pages)} paginas]")
            for pi, page in enumerate(pdf.pages):
                txt = page.extract_text() or ""
                lines = txt.split("\n")
                print(f"\n--- pagina {pi+1} ({len(lines)} linhas) ---")
                for i, ln in enumerate(lines[:max_lines]):
                    print(f"{i:3d}| {ln}")
                if len(lines) > max_lines:
                    print(f"... (+{len(lines)-max_lines} linhas)")
                if pi >= 1:  # so as 2 primeiras paginas por arquivo
                    if len(pdf.pages) > 2: print(f"... (+{len(pdf.pages)-2} paginas)")
                    break
    except Exception as e:
        print("ERRO:", repr(e))

for fn in sorted(os.listdir(JAN)):
    dump(os.path.join(JAN, fn))
