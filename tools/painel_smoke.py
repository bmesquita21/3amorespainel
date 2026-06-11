# -*- coding: utf-8 -*-
"""Smoke test do painel: injeta um Streamlit FALSO e roda painel.py top-to-bottom com dados reais.
Pega erros de runtime (colunas, índices de aba, etc.) sem precisar abrir o navegador."""
import os, sys, types, traceback
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app")
sys.path.insert(0, APP)

class Dummy:
    def __getattr__(self, n): return Dummy()
    def __call__(self, *a, **k): return Dummy()
    def __enter__(self): return self
    def __exit__(self, *a): return False

class Sidebar:
    def title(self, *a, **k): pass
    def text_input(self, label, value=None, **k): return value
    def button(self, *a, **k): return False
    def selectbox(self, label, options, **k): return options[0]
    def checkbox(self, label, value=False, **k): return bool(value)
    def __getattr__(self, n): return lambda *a, **k: None

class St(types.ModuleType):
    def __init__(self):
        super().__init__("streamlit"); self.sidebar = Sidebar()
    def set_page_config(self, *a, **k): pass
    def cache_data(self, *a, **k):
        def deco(fn): return fn
        return deco
    def selectbox(self, label, options, index=0, **k):
        options = list(options); return options[index] if options else None
    def radio(self, label, options, index=0, **k):
        options = list(options); return options[index] if options else None
    def multiselect(self, label, options, default=None, **k): return list(default) if default else []
    def text_input(self, label, value="", **k): return value
    def number_input(self, label, value=0, **k): return value
    def slider(self, label, *a, **k): return a[0] if a else 0
    def tabs(self, items): return [Dummy() for _ in items]
    def columns(self, spec, **k):
        n = spec if isinstance(spec, int) else len(spec)
        return [Dummy() for _ in range(n)]
    def stop(self): raise SystemExit("st.stop chamado (dados faltando?)")
    def rerun(self): pass
    def __getattr__(self, n): return lambda *a, **k: Dummy()

sys.modules["streamlit"] = St()
try:
    import painel  # noqa  (roda o painel inteiro)
    print("\n>>> PAINEL SMOKE OK — script rodou top-to-bottom (todas as 9 abas) sem erro.")
except SystemExit as e:
    print("\n>>> st.stop:", e)
except Exception:
    traceback.print_exc(); print("\n>>> ERRO no painel (corrigir)")
