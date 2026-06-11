# -*- coding: utf-8 -*-
"""Fase 0 — inspeciona o layout REAL das fontes de dados (sem assumir nada)."""
import sys, os, io
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Arquivos-chave (1 exemplo de cada fonte). Usa os 2026 (menores) quando há opção.
TARGETS = [
    ("DESPESA / competencia (entrada)", "2.2 DRE - DESEMBOLSO POR DATA DE ENTRADA/Relatorio_Desembolso_Detalhado 01 a 04.2026.xlsx"),
    ("DESPESA / caixa (pagamento)",      "1.1 FLUXO DE CAIXA - DESEMBOLSO POR DATA DE PAGAMENTO/Relatorio_Contas_Pagas_Detalhado 01 a 04.2026.xlsx"),
    ("RECEITA / competencia (emissao)",  "2.1 DRE - FATURAMENTO POR DATA DE EMISSÃO/notas_fiscais emissão 2025 a 04.2026.xlsx"),
    ("RECEITA / caixa (recebimento)",    "1.2 FLUXO DE CAIXA - FATURAMENTO POR DATA DE RECEBIMENTO/notas_fiscais 2025 a 04.2026 - recebidas.xlsx"),
    ("ESTOQUE / produtos produzidos",    "4 PRODUTOS PRODUZIDOS - MOVIMENTAÇÃO DE ESTOQUE/Relatório de Produtos Produzidos 2025 a 04.2026.XLS"),
    ("ATIVOS / imobilizado",             "3 LEVANTAMENTO DE ATIVOS/ATIVOS/Registro_Imobilizado_TresAmores.xlsx"),
    ("ATIVOS / omega consolidado",       "3 LEVANTAMENTO DE ATIVOS/SERVIÇOS OMEGA/CONSOLIDADO TRES AMORES (com notas marcadas).xlsx"),
    ("RECRIA / dados gerais",            "RECRIA HISTÓRICO/DADOS GERAIS DA RECRIA.XLS"),
]

def cell(v, width=26):
    s = "" if v is None else str(v)
    s = s.replace("\n", " ").replace("\r", " ").strip()
    if len(s) > width:
        s = s[:width-1] + "…"
    return s

def dump_df(df, max_rows=6):
    ncols = df.shape[1]
    print(f"    shape = {df.shape[0]} linhas x {ncols} colunas")
    for r in range(min(max_rows, len(df))):
        parts = []
        for c in range(ncols):
            parts.append(f"{c}={cell(df.iat[r, c])}")
        print(f"    R{r}: " + " | ".join(parts))

def sniff_html(path):
    with open(path, "rb") as f:
        head = f.read(2048).lower()
    return (b"<html" in head) or (b"<table" in head) or head.lstrip().startswith(b"<")

def inspect(path):
    ext = os.path.splitext(path)[1].lower()
    # .XLS/.xls que na verdade é HTML (ERP brasileiro)
    if ext in (".xls",) and sniff_html(path):
        return ("HTML(read_html)", read_html_tables(path))
    if ext == ".xls" and sniff_html(path):
        return ("HTML(read_html)", read_html_tables(path))
    try:
        engine = "openpyxl" if ext == ".xlsx" else "xlrd"
        xl = pd.ExcelFile(path, engine=engine)
        out = {}
        for sh in xl.sheet_names[:10]:
            out[sh] = xl.parse(sh, header=None, dtype=object)
        return (f"excel({engine})", out)
    except Exception as e:
        # fallback: pode ser HTML disfarçado
        if sniff_html(path):
            return ("HTML(read_html)", read_html_tables(path))
        raise

def read_html_tables(path):
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            with open(path, "r", encoding=enc) as f:
                txt = f.read()
            tables = pd.read_html(io.StringIO(txt), header=None)
            return {f"tabela_{i}": t for i, t in enumerate(tables[:5])}
        except Exception:
            continue
    raise RuntimeError("não consegui ler como HTML")

def main():
    print("pandas", pd.__version__)
    for label, rel in TARGETS:
        path = os.path.join(BASE, rel.replace("/", os.sep))
        print("\n" + "#" * 78)
        print(f"### {label}")
        print(f"### {rel}")
        if not os.path.exists(path):
            print("    [!!] ARQUIVO NÃO ENCONTRADO")
            continue
        try:
            kind, sheets = inspect(path)
            print(f"    leitor: {kind}  |  abas/tabelas: {list(sheets.keys())}")
            for name, df in sheets.items():
                print(f"  --- '{name}' ---")
                dump_df(df)
        except Exception as e:
            print(f"    [ERRO] {type(e).__name__}: {e}")

if __name__ == "__main__":
    main()
