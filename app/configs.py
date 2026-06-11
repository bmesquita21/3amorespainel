# -*- coding: utf-8 -*-
"""Carrega os de-para editáveis de /config (toda a lógica de classificação vive aqui)."""
import os, csv
try: import yaml
except Exception: yaml = None

def _load(cfg_dir, name):
    with open(os.path.join(cfg_dir, name), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))

class Configs:
    def __init__(self, cfg_dir):
        self.dir = cfg_dir
        cr = _load(cfg_dir, "config_contas.csv")
        self.conta2linha = {r["nome_conta"].strip().upper(): r["linha_dre"] for r in cr}
        self.conta2nat  = {r["nome_conta"].strip().upper(): (r["natureza"], r.get("tipo_estoque", "")) for r in cr}
        self.cc2info = {r["centro_custo"].strip().upper(): r for r in _load(cfg_dir, "config_centros_custo.csv")}
        self.prod2   = {r["produto_original"].strip(): r for r in _load(cfg_dir, "config_produtos.csv")}
        # mapeamento fornecedor → DRE (fallback para NFs sem conta contábil no ERP)
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
        # composição: produto -> custo de embalagem por caixa (+ taxa média por ovo p/ estimar faltantes)
        self.comp, embs, eggs = {}, [], []
        try:
            for r in _load(cfg_dir, "config_composicao.csv"):
                nk = r["produto_norm"].strip()
                e = float(str(r["emb_por_caixa"]).replace(",", "."))
                o = float(str(r.get("ovos_por_caixa", "0")).replace(",", ".") or 0)
                self.comp[nk] = e
                if o > 0: embs.append(e); eggs.append(o)
        except Exception: pass
        self.comp_emb_per_egg = (sum(embs) / sum(eggs)) if eggs else 0.058
        # parâmetros gerais (capital social, saldo inicial) do config_geral.yaml
        self.capital_social, self.saldo_caixa_inicial, self.biologico_default = 0.0, 0.0, True
        if yaml is not None:
            try:
                with open(os.path.join(cfg_dir, "config_geral.yaml"), encoding="utf-8") as f:
                    g = yaml.safe_load(f) or {}
                bp = (g.get("balanco") or {}) if isinstance(g, dict) else {}
                self.capital_social = float(bp.get("capital_social", 0) or 0)
                self.saldo_caixa_inicial = float(bp.get("saldo_caixa_inicial", 0) or 0)
                ab = (g.get("ativo_biologico") or {}) if isinstance(g, dict) else {}
                self.biologico_default = bool(ab.get("tratar_recria_como_ativo", True))
            except Exception: pass
        # lote(s) do plantel (ativo biológico)
        self.lote = {}
        try:
            lr = _load(cfg_dir, "config_lotes.csv")
            if lr: self.lote = lr[0]
        except Exception: pass

def load(cfg_dir): return Configs(cfg_dir)
