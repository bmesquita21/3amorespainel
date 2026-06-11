# -*- coding: utf-8 -*-
"""Smoke limpo: mock do Streamlit que IMPRIME st.error/st.warning para revelar o motivo de st.stop."""
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
    def selectbox(self, label, options, **k): return list(options)[0]
    def checkbox(self, label, value=False, **k): return bool(value)
    def download_button(self, *a, **k): return False
    def __getattr__(self, n): return lambda *a, **k: None

class St(types.ModuleType):
    def __init__(self): super().__init__("streamlit"); self.sidebar = Sidebar()
    def set_page_config(self, *a, **k): pass
    def cache_data(self, *a, **k):
        def deco(fn): return fn
        return deco
    def tabs(self, items): return [Dummy() for _ in items]
    def selectbox(self, label, options, index=0, **k):
        opts = list(options); return opts[index] if opts else None
    def radio(self, label, options, index=0, **k):
        opts = list(options); return opts[index] if opts else None
    def multiselect(self, label, options, default=None, **k): return list(default) if default else []
    def number_input(self, label, value=0, **k): return value
    def slider(self, label, *a, **k): return a[0] if a else 0
    def columns(self, spec, **k):
        n = spec if isinstance(spec, int) else len(spec)
        return [Dummy() for _ in range(n)]
    def error(self, msg, *a, **k): print(">>> st.error:", str(msg)[:500])
    def warning(self, msg, *a, **k): print(">>> st.warning:", str(msg)[:200])
    def stop(self): raise SystemExit("st.stop")
    def rerun(self): pass
    def __getattr__(self, n): return lambda *a, **k: Dummy()

sys.modules["streamlit"] = St()
try:
    import painel
    print(">>> PAINEL SMOKE2 OK")
except SystemExit as e:
    print(">>> st.stop:", e)
except Exception:
    traceback.print_exc()
