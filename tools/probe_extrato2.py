# -*- coding: utf-8 -*-
"""Recon de TODOS os extratos: extrai por arquivo banco/agencia/conta/periodo,
SALDO ANTERIOR, linhas de 'saldo disponivel/total', e ultimas linhas (fechamento).
Saida compacta para mapear variacoes de formato antes de escrever o parser."""
import os, sys, re
sys.stdout.reconfigure(encoding="utf-8")
import pdfplumber

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT = os.path.join(ROOT, "1.3 EXTRATO")

def bank_of(fn):
    u = fn.upper()
    if "BRADESCO" in u: return "BRADESCO"
    if "SANTANDER" in u: return "SANTANDER"
    if "BB" in u or "BANCO DO BRASIL" in u: return "BB"
    return "?"

def all_pdfs():
    out = []
    for yr in sorted(os.listdir(EXT)):
        yp = os.path.join(EXT, yr)
        if not os.path.isdir(yp): continue
        for mo in sorted(os.listdir(yp)):
            mp = os.path.join(yp, mo)
            if not os.path.isdir(mp): continue
            for fn in sorted(os.listdir(mp)):
                if fn.lower().endswith(".pdf"):
                    out.append((yr, mo, fn, os.path.join(mp, fn)))
    return out

def fulltext(fp):
    try:
        with pdfplumber.open(fp) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages)
    except Exception as e:
        return f"__ERRO__ {e!r}"

pdfs = all_pdfs()
print(f"TOTAL PDFs: {len(pdfs)}\n")
for yr, mo, fn, fp in pdfs:
    txt = fulltext(fp)
    print("=" * 100)
    print(f">> {yr} / {mo} / {fn}   [{bank_of(fn)}]")
    if txt.startswith("__ERRO__"):
        print("   ", txt); continue
    lines = [l.rstrip() for l in txt.split("\n")]
    ne = [l for l in lines if l.strip()]
    # 1as 6 linhas (cabecalho)
    print("   -- topo --")
    for l in ne[:6]: print("     ", l)
    # periodo
    per = re.findall(r"\d{2}/\d{2}/\d{4}\s*a\s*\d{2}/\d{2}/\d{4}|Entre\s*\d{2}/\d{2}/\d{4}\s*e\s*\d{2}/\d{2}/\d{4}", txt)
    if per: print("   periodo:", per[0])
    # saldo anterior
    sa = [l.strip() for l in lines if "SALDO ANTERIOR" in l.upper()]
    for l in sa: print("   SA>", l)
    # saldos disponiveis / total / final
    sd = [l.strip() for l in lines if re.search(r"saldo\s+(dispon|em c|atual|final|anterior|total)|total\s+dispon|saldo\s*\(r\$\)", l, re.I)]
    for l in sd[:4]:
        if "SALDO ANTERIOR" not in l.upper(): print("   SD>", l)
    # ultimas 3 linhas
    print("   -- fim --")
    for l in ne[-3:]: print("     ", l)
