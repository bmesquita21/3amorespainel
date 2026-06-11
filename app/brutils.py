# -*- coding: utf-8 -*-
"""Utilidades de domínio reaproveitadas do protótipo: parse BR, datas, períodos."""
import re, datetime, unicodedata
import pandas as pd

def parse_valor_br(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return 0.0
    if isinstance(v, (int, float)): return float(v)
    s = str(v).replace("R$", "").replace("\xa0", "").replace(" ", "").strip()
    if not s: return 0.0
    s = s.replace(".", "").replace(",", ".")
    try: return float(s)
    except: return 0.0

def parse_date(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return None
    if isinstance(v, pd.Timestamp):
        try: return datetime.date(v.year, v.month, v.day)
        except: return None
    if isinstance(v, (datetime.datetime, datetime.date)): return datetime.date(v.year, v.month, v.day)
    if isinstance(v, (int, float)):
        try: return datetime.date(1899, 12, 30) + datetime.timedelta(days=int(v))
        except: return None
    s = str(v).strip()
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        try: return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except: return None
    try: return datetime.date.fromisoformat(s[:10])
    except: return None

def valid(d): return (d is not None) and (2020 <= d.year <= 2035)
def period(d): return f"{d.year}-{d.month:02d}"
def ymv(d): return d.year * 12 + (d.month - 1)

def brl(x):
    try: return "R$ " + f"{float(x):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except: return str(x)

def norm_prod(s):
    """Normaliza nome de produto p/ casar entre fontes (sem acento, maiúsculo, só alfanumérico)."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z0-9]+", " ", s).strip()

def eggs_per_box(desc):
    """Estima ovos por caixa a partir do nome (para estimar embalagem de produtos sem receita)."""
    d = norm_prod(desc)
    m = re.search(r"(\d+)\s+CRIVOS?\s+(?:DE\s+)?(\d+)", d)      # 12 CRIVO DE 20 / 12 CRIVOS 30
    if m: return int(m.group(1)) * int(m.group(2))
    m = re.search(r"CRIVO\s+(\d+)\s*UN", d)                      # CRIVO 30UN
    if m: return int(m.group(1))
    m = re.search(r"(\d+)\s+1\s+2\s+D[UÚ]ZIA", d)                # 30 1/2 DUZIAS
    if m: return int(m.group(1)) * 6
    m = re.search(r"(\d+)\s+D[UÚ]ZIA", d)                        # 20 DUZIA
    if m: return int(m.group(1)) * 12
    m = re.search(r"(\d+)\s+DEZENA", d)                          # 20 DEZENAS
    if m: return int(m.group(1)) * 10
    if "DUZIA" in d: return 12
    if "DEZENA" in d: return 10
    return 277  # média de ovos/caixa (fallback)

def brl_compact(x):
    """Formato curto p/ KPIs. Regra: <1.000.000 -> 'mil'; >=1.000.000 -> 'mi' (milhões)."""
    try: x = float(x)
    except: return str(x)
    s = "-" if x < 0 else ""
    a = abs(x)
    if a >= 1e6: num, suf = f"{a/1e6:,.2f}", " mi"
    elif a >= 1e3: num, suf = f"{min(round(a/1e3), 999):,.0f}", " mil"   # 999.999 nunca vira '1.000 mil'
    else: num, suf = f"{a:,.0f}", ""
    num = num.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}{num}{suf}"
