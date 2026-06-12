# -*- coding: utf-8 -*-
"""Carrega os de-para editáveis. Tenta PostgreSQL primeiro; cai em CSV como fallback."""
import os, csv
try: import yaml
except Exception: yaml = None

def _load(cfg_dir, name):
    with open(os.path.join(cfg_dir, name), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


class Configs:
    def __init__(self, cfg_dir):
        self.dir = cfg_dir
        _pg_ok = False
        try:
            import db_pg as _pg
            if _pg.is_available():
                self._init_from_pg(_pg, cfg_dir)
                _pg_ok = True
        except Exception:
            pass
        if not _pg_ok:
            self._init_from_csv(cfg_dir)

    # ── PG-first ────────────────────────────────────────────────────────────

    def _init_from_pg(self, pg, cfg_dir):
        contas = pg.fetch_contas()
        self.conta2linha = {r["nome_conta"].strip().upper(): r["linha_dre"] for r in contas}
        self.conta2nat   = {r["nome_conta"].strip().upper(): (r["natureza"], r.get("tipo_estoque", "")) for r in contas}
        self.cc2info = {r["centro_custo"].strip().upper(): r for r in pg.fetch_centros_custo()}
        self.prod2   = {r["produto_original"].strip(): r for r in pg.fetch_produtos()}
        self.forn2linha, self.forn2nat = {}, {}
        for r in pg.fetch_fornecedores():
            k = r["credor"].strip().upper()
            self.forn2linha[k] = r["linha_dre"]
            self.forn2nat[k]   = (r["natureza"], r.get("tipo_estoque", ""))
        try: self.layout = _load(cfg_dir, "config_layout_dre.csv")
        except Exception: self.layout = []
        self._init_composicao(pg, cfg_dir)
        self._init_lotes(pg, cfg_dir)
        self._load_config_geral(pg, cfg_dir)

    # ── CSV fallback ─────────────────────────────────────────────────────────

    def _init_from_csv(self, cfg_dir):
        cr = _load(cfg_dir, "config_contas.csv")
        self.conta2linha = {r["nome_conta"].strip().upper(): r["linha_dre"] for r in cr}
        self.conta2nat   = {r["nome_conta"].strip().upper(): (r["natureza"], r.get("tipo_estoque", "")) for r in cr}
        self.cc2info = {r["centro_custo"].strip().upper(): r for r in _load(cfg_dir, "config_centros_custo.csv")}
        self.prod2   = {r["produto_original"].strip(): r for r in _load(cfg_dir, "config_produtos.csv")}
        self.forn2linha, self.forn2nat = {}, {}
        try:
            for r in _load(cfg_dir, "config_fornecedores.csv"):
                k = r["credor"].strip().upper()
                self.forn2linha[k] = r["linha_dre"]
                self.forn2nat[k]   = (r["natureza"], r.get("tipo_estoque", ""))
        except Exception:
            pass
        try: self.layout = _load(cfg_dir, "config_layout_dre.csv")
        except Exception: self.layout = []
        self._init_composicao(None, cfg_dir)
        self._init_lotes(None, cfg_dir)
        self._load_config_geral(None, cfg_dir)

    # ── Composição ──────────────────────────────────────────────────────────

    def _init_composicao(self, pg, cfg_dir):
        self.comp, embs, eggs = {}, [], []
        if pg is not None:
            try:
                for r in pg.fetch_composicao():
                    nk = r["produto_norm"].strip()
                    e  = float(r.get("emb_por_caixa") or 0)
                    o  = float(r.get("ovos_por_caixa") or 0)
                    self.comp[nk] = e
                    if o > 0: embs.append(e); eggs.append(o)
                self.comp_emb_per_egg = (sum(embs) / sum(eggs)) if eggs else 0.058
                return
            except Exception:
                self.comp, embs, eggs = {}, [], []
        # CSV fallback
        try:
            for r in _load(cfg_dir, "config_composicao.csv"):
                nk = r["produto_norm"].strip()
                e  = float(str(r["emb_por_caixa"]).replace(",", "."))
                o  = float(str(r.get("ovos_por_caixa", "0")).replace(",", ".") or 0)
                self.comp[nk] = e
                if o > 0: embs.append(e); eggs.append(o)
        except Exception: pass
        self.comp_emb_per_egg = (sum(embs) / sum(eggs)) if eggs else 0.058

    # ── Lotes ────────────────────────────────────────────────────────────────

    def _init_lotes(self, pg, cfg_dir):
        self.lote = {}
        if pg is not None:
            try:
                rows = pg.fetch_lotes()
                if rows:
                    # converte Decimal/int para str para compatibilidade com biological.py
                    self.lote = {k: str(v) for k, v in rows[0].items()}
                    return
            except Exception:
                pass
        try:
            lr = _load(cfg_dir, "config_lotes.csv")
            if lr: self.lote = lr[0]
        except Exception: pass

    # ── Config geral ─────────────────────────────────────────────────────────

    def _load_config_geral(self, pg, cfg_dir):
        self.capital_social = 0.0
        self.saldo_caixa_inicial = 0.0
        self.biologico_default = True
        if pg is not None:
            try:
                geral = pg.fetch_config_geral()
                if geral:
                    self.capital_social      = float(geral.get("capital_social", 0) or 0)
                    self.saldo_caixa_inicial = float(geral.get("saldo_caixa_inicial", 0) or 0)
                    self.biologico_default   = geral.get("biologico_default", "true").lower() != "false"
                    return
            except Exception:
                pass
        if yaml is not None:
            try:
                with open(os.path.join(cfg_dir, "config_geral.yaml"), encoding="utf-8") as f:
                    g = yaml.safe_load(f) or {}
                bp = (g.get("balanco") or {}) if isinstance(g, dict) else {}
                self.capital_social      = float(bp.get("capital_social", 0) or 0)
                self.saldo_caixa_inicial = float(bp.get("saldo_caixa_inicial", 0) or 0)
                ab = (g.get("ativo_biologico") or {}) if isinstance(g, dict) else {}
                self.biologico_default   = bool(ab.get("tratar_recria_como_ativo", True))
            except Exception: pass


def load(cfg_dir): return Configs(cfg_dir)
