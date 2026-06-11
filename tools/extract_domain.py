# -*- coding: utf-8 -*-
"""Fase 0 — extrai valores DISTINTOS reais e checa cobertura vs de-para do HTML."""
import os, re, sys
import pandas as pd
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(BASE, "DRE_GRANJA_DASHBOARD.html")

F = {
    "desp_comp_2025": "2.2 DRE - DESEMBOLSO POR DATA DE ENTRADA/Relatorio_Desembolso_Detalhado 2025.xlsx",
    "desp_comp_2026": "2.2 DRE - DESEMBOLSO POR DATA DE ENTRADA/Relatorio_Desembolso_Detalhado 01 a 04.2026.xlsx",
    "fat_emissao":    "2.1 DRE - FATURAMENTO POR DATA DE EMISSÃO/notas_fiscais emissão 2025 a 04.2026.xlsx",
    "fat_receb":      "1.2 FLUXO DE CAIXA - FATURAMENTO POR DATA DE RECEBIMENTO/notas_fiscais 2025 a 04.2026 - recebidas.xlsx",
    "prod":           "4 PRODUTOS PRODUZIDOS - MOVIMENTAÇÃO DE ESTOQUE/Relatório de Produtos Produzidos 2025 a 04.2026.XLS",
}

def path(rel): return os.path.join(BASE, rel.replace("/", os.sep))

def parse_valor_br(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return 0.0
    if isinstance(v, (int, float)): return float(v)
    s = str(v).replace("R$", "").replace("\xa0", "").replace(" ", "").strip()
    if not s: return 0.0
    s = s.replace(".", "").replace(",", ".")
    try: return float(s)
    except: return 0.0

# ---- de-para do HTML ----
def block(text, name):
    i = text.find("const " + name)
    if i < 0: return ""
    m = re.search(r"\n\s*[}\]];", text[i:])
    return text[i:i + (m.end() if m else 4000)]

html = open(HTML, encoding="utf-8").read()
CONTA_KEYS = set(k.strip().upper() for k, _ in re.findall(r"'([^']*)'\s*:\s*'([^']*)'", block(html, "MAPA_CONTA")))
CC_KEYS    = set(k.strip().upper() for k in re.findall(r"'([^']*)'\s*:\s*\[", block(html, "NOVO_MAPA_CC")))
print(f"de-para HTML: MAPA_CONTA={len(CONTA_KEYS)} contas | NOVO_MAPA_CC={len(CC_KEYS)} centros de custo\n")

def read(rel, engine):
    return pd.read_excel(path(rel), header=0, dtype=object, engine=engine)

def agg(df, key_idx, val_idx, val_is_br=True):
    cnt, tot = defaultdict(int), defaultdict(float)
    for _, r in df.iterrows():
        k = r.iloc[key_idx]
        if k is None or (isinstance(k, float) and pd.isna(k)): k = "(vazio)"
        k = str(k).strip()
        v = parse_valor_br(r.iloc[val_idx]) if val_is_br else (float(r.iloc[val_idx]) if pd.notna(r.iloc[val_idx]) else 0.0)
        cnt[k] += 1; tot[k] += v
    return cnt, tot

def brl(x): return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ===== CONTAS CONTÁBEIS (despesa competência) =====
print("=" * 70); print("CONTAS CONTÁBEIS — despesa competência (2.2, 2025+2026)")
d = pd.concat([read(F["desp_comp_2025"], "openpyxl"), read(F["desp_comp_2026"], "openpyxl")], ignore_index=True)
cnt, tot = agg(d, 3, 6)
mapped = [k for k in cnt if k.upper() in CONTA_KEYS]
unmapped = [k for k in cnt if k.upper() not in CONTA_KEYS]
print(f"linhas={len(d)} | contas distintas={len(cnt)} | MAPEADAS={len(mapped)} | NÃO MAPEADAS={len(unmapped)}")
print("\n-- NÃO MAPEADAS (precisam de decisão) — por valor --")
for k in sorted(unmapped, key=lambda x: -tot[x]):
    print(f"   {brl(tot[k]):>18}  x{cnt[k]:<4}  {k!r}")

# ===== CENTROS DE CUSTO =====
print("\n" + "=" * 70); print("CENTROS DE CUSTO — despesa competência")
cnt, tot = agg(d, 4, 6)
unmapped_cc = [k for k in cnt if k.upper() not in CC_KEYS]
print(f"CCs distintos={len(cnt)} | MAPEADOS={len(cnt)-len(unmapped_cc)} | NÃO MAPEADOS={len(unmapped_cc)}")
print("\n-- NÃO MAPEADOS (precisam de decisão) — por valor --")
for k in sorted(unmapped_cc, key=lambda x: -tot[x]):
    print(f"   {brl(tot[k]):>18}  x{cnt[k]:<4}  {k!r}")

# ===== PRODUTOS (faturamento emissão = DRE) =====
print("\n" + "=" * 70); print("PRODUTOS — faturamento EMISSÃO (2.1 = receita da DRE)")
fe = read(F["fat_emissao"], "openpyxl")
cnt, tot = agg(fe, 5, 8)
print(f"linhas={len(fe)} | produtos distintos={len(cnt)}  (de-para a CONSTRUIR do zero)\n")
for k in sorted(cnt, key=lambda x: -tot[x]):
    print(f"   {brl(tot[k]):>18}  x{cnt[k]:<4}  {k!r}")

# ===== DESCRIÇÕES (produtos produzidos = ração p/ CMV) =====
print("\n" + "=" * 70); print("PRODUTOS PRODUZIDOS — descrição (4 = ração p/ CMV)")
pr = read(F["prod"], "xlrd")
cnt, tot = agg(pr, 2, 6, val_is_br=False)
print(f"linhas={len(pr)} | descrições distintas={len(cnt)}\n")
for k in sorted(cnt, key=lambda x: -tot[x]):
    print(f"   {brl(tot[k]):>18}  x{cnt[k]:<4}  {k!r}")
