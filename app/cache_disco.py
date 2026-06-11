"""Cache persistente em disco para o load_all.
Salva em <DADOS>/.cache/ (na pasta de dados, NAS/SMB) para sobreviver a
restartes do Docker. Fallback p/ /tmp/ se a pasta não tiver permissão de escrita.
Invalida se qualquer arquivo relevante mudar.
"""
import os, pickle, hashlib, time

def _resolve_cache_path(base: str, filename: str) -> str:
    """Prefere <base>/.cache/<filename> (persiste no NAS entre deploys).
    Cai para /tmp/<filename> se não puder escrever lá."""
    nas_dir = os.path.join(base, ".cache")
    try:
        os.makedirs(nas_dir, exist_ok=True)
        test = os.path.join(nas_dir, ".write_test")
        with open(test, "w") as f: f.write("ok")
        os.remove(test)
        return os.path.join(nas_dir, filename)
    except Exception:
        return os.path.join("/tmp", filename)

# Paths resolvidos na primeira chamada (lazy)
_CACHE_PATH_RESOLVED: dict = {}

def _cache_path(base: str, key: str) -> str:
    k = (base, key)
    if k not in _CACHE_PATH_RESOLVED:
        _CACHE_PATH_RESOLVED[k] = _resolve_cache_path(base, key)
    return _CACHE_PATH_RESOLVED[k]

# Compat: constantes legadas usadas em limpar_cache
CACHE_PATH          = "/tmp/painel_cache.pkl"

_SKIP_DIRS = {"NFSE", "DANF", "RELATORIOS DEP", "LANCAMENTOS", "__PYCACHE__"}
_DATA_EXTS = {".xlsx", ".xls", ".pdf", ".csv", ".yaml"}

def _fingerprint(base: str) -> str:
    """Varredura rápida: só entra em subpastas de 1º e 2º nível (não percorre PDFs recursivamente)."""
    entries = []
    try:
        top_items = os.listdir(base)
    except OSError:
        return "error"
    for item in sorted(top_items):
        item_path = os.path.join(base, item)
        uitem = item.upper()
        if any(s in uitem for s in _SKIP_DIRS):
            continue
        if os.path.isfile(item_path):
            ext = os.path.splitext(item)[1].lower()
            if ext in _DATA_EXTS:
                try:
                    st = os.stat(item_path)
                    entries.append(f"{item_path}:{st.st_mtime}:{st.st_size}")
                except OSError:
                    pass
        elif os.path.isdir(item_path):
            # Nível 2 — apenas conta arquivos e pega mtime do diretório
            try:
                sub_stat = os.stat(item_path)
                entries.append(f"{item_path}:dir:{sub_stat.st_mtime}")
                # Para pastas de extrato (PDFs) só usa mtime do diretório
                if "EXTRATO" in uitem:
                    continue
                for sub in sorted(os.listdir(item_path)):
                    sub_path = os.path.join(item_path, sub)
                    usub = sub.upper()
                    if any(s in usub for s in _SKIP_DIRS):
                        continue
                    if os.path.isfile(sub_path):
                        ext = os.path.splitext(sub)[1].lower()
                        if ext in _DATA_EXTS:
                            try:
                                st = os.stat(sub_path)
                                entries.append(f"{sub_path}:{st.st_mtime}:{st.st_size}")
                            except OSError:
                                pass
            except OSError:
                pass
    return hashlib.md5("\n".join(entries).encode()).hexdigest()

CACHE_EXTRATOS_PATH = "/tmp/painel_cache_extratos.pkl"  # compat

def limpar_cache(base: str = ""):
    """Apaga o cache de disco (equivalente ao Atualizar do painel).
    Remove tanto os caches no NAS quanto os fallbacks em /tmp."""
    for fname in ("painel_cache.pkl", "painel_cache_extratos.pkl"):
        # cache no NAS (se base fornecida)
        if base:
            p = os.path.join(base, ".cache", fname)
            try:
                if os.path.exists(p): os.remove(p)
            except Exception: pass
        # fallback /tmp
        p2 = os.path.join("/tmp", fname)
        try:
            if os.path.exists(p2): os.remove(p2)
        except Exception: pass
    # limpa dict de paths resolvidos p/ forçar reavaliação
    _CACHE_PATH_RESOLVED.clear()

def carregar_com_cache(base: str, load_fn):
    path = _cache_path(base, "painel_cache.pkl")
    fp   = _fingerprint(base)
    if os.path.exists(path):
        try:
            with open(path, "rb") as f:
                cached = pickle.load(f)
            if cached.get("fingerprint") == fp:
                print(f"[cache] HIT ({path})")
                return cached["dfs"]
        except Exception:
            pass
    print(f"[cache] MISS - relendo arquivos... (cache em {path})")
    t0 = time.time()
    dfs = load_fn()
    print(f"[cache] load_all: {time.time()-t0:.1f}s - salvando")
    try:
        with open(path, "wb") as f:
            pickle.dump({"fingerprint": fp, "dfs": dfs}, f)
    except Exception as e:
        print(f"[cache] aviso: nao salvou: {e}")
    return dfs

def carregar_extratos_com_cache(base: str, load_fn):
    path = _cache_path(base, "painel_cache_extratos.pkl")
    fp   = _fingerprint(base)
    if os.path.exists(path):
        try:
            with open(path, "rb") as f:
                cached = pickle.load(f)
            if cached.get("fingerprint") == fp:
                return cached["dfs"]
        except Exception:
            pass
    dfs = load_fn()
    try:
        with open(path, "wb") as f:
            pickle.dump({"fingerprint": fp, "dfs": dfs}, f)
    except Exception:
        pass
    return dfs
