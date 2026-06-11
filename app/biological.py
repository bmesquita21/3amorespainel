# -*- coding: utf-8 -*-
"""Ativo Biológico (poedeiras): custo de formação (recria) e amortização na postura (§3.4)."""

def _ord(p): return int(p[:4]) * 12 + int(p[5:]) - 1

def chicks_cost(dfs):
    im = dfs.get("imob")
    if im is None or len(im) == 0: return 0.0
    return float(im[im.is_bio].valor_aquisicao.sum())

def feed_cost(dfs, periodos=None):
    rac = dfs.get("racao")
    if rac is None or len(rac) == 0: return 0.0
    d = rac[rac.fase == "RECRIA"]
    if periodos is not None: d = d[d.periodo.isin(set(periodos))]
    return float(d.custo.sum()) if len(d) else 0.0

def shed_cost(dfs, periodos=None):
    desp = dfs.get("despesa")
    if desp is None or len(desp) == 0: return 0.0
    d = desp[desp.cc.str.upper().str.contains("GALPAO RECRIA", na=False)]
    if periodos is not None: d = d[d.periodo.isin(set(periodos))]
    return float(d.valor.sum()) if len(d) else 0.0

def total_recria(dfs, periodos=None):
    return chicks_cost(dfs) + feed_cost(dfs, periodos) + shed_cost(dfs, periodos)

def componentes(dfs):
    return {"pintainhas": chicks_cost(dfs), "racao_recria": feed_cost(dfs), "galpao_recria": shed_cost(dfs)}

def amort_schedule(total, cfg):
    lote = getattr(cfg, "lote", {}) or {}
    if not lote or total <= 0: return {}
    try: n = int(float(lote.get("ciclo_postura_meses", 13) or 13))
    except Exception: n = 13
    start = str(lote.get("data_inicio_postura", "2026-01"))
    so = _ord(start); monthly = total / n if n else 0.0
    return {f"{(so+i)//12}-{((so+i)%12)+1:02d}": monthly for i in range(n)}

def amort_periodos(dfs, cfg, periodos):
    sched = amort_schedule(total_recria(dfs), cfg)
    return sum(sched.get(p, 0.0) for p in periodos)

def asset_value(dfs, cfg, periodos):
    """Valor do ativo biológico no fim do período = custo total − amortização acumulada."""
    end = _ord(max(periodos))
    total = total_recria(dfs)
    sched = amort_schedule(total, cfg)
    amort_acum = sum(v for p, v in sched.items() if _ord(p) <= end)
    return max(0.0, total - amort_acum), total, amort_acum
