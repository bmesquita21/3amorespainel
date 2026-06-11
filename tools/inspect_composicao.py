# -*- coding: utf-8 -*-
"""Inspeciona os PDFs de composição (produto acabado e ração) via pdfplumber."""
import os, sys
import pdfplumber
sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def path(rel): return os.path.join(BASE, rel.replace("/", os.sep))

for rel in ["0 COMPOSIÇÕES DOS PRODUTOS/Composição Produto Acabado.pdf",
            "0 COMPOSIÇÕES DOS PRODUTOS/Composição Ração.pdf"]:
    print("\n" + "#"*80); print("###", rel)
    with pdfplumber.open(path(rel)) as pdf:
        print(f"páginas: {len(pdf.pages)}")
        for pi, page in enumerate(pdf.pages[:3]):
            print(f"\n----- página {pi+1} -----")
            txt = (page.extract_text() or "")[:1800]
            print("TEXTO:"); print(txt)
            tables = page.extract_tables()
            print(f"\nTABELAS detectadas: {len(tables)}")
            for ti, t in enumerate(tables[:2]):
                print(f"  tabela {ti}: {len(t)} linhas")
                for row in t[:8]:
                    print("   ", [ (c or "").replace("\n"," ")[:22] for c in row ])
