# -*- coding: utf-8 -*-
"""Conexão com o banco Firebird (Auditor ERP).

Carrega credenciais de .env (desenvolvimento) ou variáveis de ambiente (Docker/VPS).

Uso:
    from db import get_conn
    with get_conn() as con:
        df = pd.read_sql("SELECT ...", con)
"""
import os
import sys

def _load_env():
    """Lê .env da raiz do projeto (sobe 1 nível a partir de app/)."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.isfile(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

_load_env()

# Configura o caminho da biblioteca Firebird no nível do módulo,
# antes de qualquer import de firebird.driver (evita _client=None).
def _configure_firebird_client():
    lib = os.environ.get("FB_CLIENT_LIBRARY", "")
    if not lib:
        if sys.platform == "win32":
            for p in [
                r"C:\Program Files (x86)\HK-Software\IBExpert\firebird4\fbclient.dll",
                r"C:\Program Files\Firebird\Firebird_4_0\fbclient.dll",
                r"C:\Program Files\Firebird\Firebird_3_0\fbclient.dll",
            ]:
                if os.path.isfile(p):
                    lib = p
                    break
        else:
            for p in [
                "/usr/lib/x86_64-linux-gnu/libfbclient.so.2",
                "libfbclient.so.2",
                "libfbclient.so",
            ]:
                if p.startswith("/"):
                    if os.path.isfile(p):
                        lib = p
                        break
                else:
                    lib = p
                    break
    if lib:
        try:
            from firebird.driver import driver_config
            driver_config.fb_client_library.value = lib
        except Exception:
            pass

_configure_firebird_client()

def _resolve_client_lib() -> str:
    """Resolve o caminho da biblioteca cliente Firebird por plataforma."""
    # Variável de ambiente tem prioridade (Docker injeta FB_CLIENT_LIBRARY)
    explicit = os.environ.get("FB_CLIENT_LIBRARY", "")
    if explicit:
        return explicit

    if sys.platform == "win32":
        # IBExpert instala o Firebird 4 client em:
        candidates = [
            r"C:\Program Files (x86)\HK-Software\IBExpert\firebird4\fbclient.dll",
            r"C:\Program Files\Firebird\Firebird_4_0\fbclient.dll",
            r"C:\Program Files\Firebird\Firebird_3_0\fbclient.dll",
        ]
        for path in candidates:
            if os.path.isfile(path):
                return path
        return ""  # deixa o driver tentar o PATH

    # Linux/Mac — nomes padrão do apt (libfbclient2)
    linux_candidates = [
        "libfbclient.so.2",   # Debian/Ubuntu: pacote libfbclient2
        "libfbclient.so",
        "/usr/lib/x86_64-linux-gnu/libfbclient.so.2",
    ]
    for lib in linux_candidates:
        if lib.startswith("/"):
            if os.path.isfile(lib):
                return lib
        else:
            return lib  # nome sem caminho; o loader do SO vai procurar

    return ""

def get_conn():
    """Retorna conexão DBAPI2 com o Firebird.
    Use como context manager ou chame .close() ao terminar.
    """
    from firebird.driver import connect

    host = os.environ.get("FB_HOST", "192.168.100.201")
    port = os.environ.get("FB_PORT", "3050")
    db   = os.environ.get("FB_DATABASE", "/opt/Auditor/Dados/AUDITOR.FDB")
    user = os.environ.get("FB_USER", "RO_AUDITOR")
    pwd  = os.environ.get("FB_PASSWORD", "")

    return connect(
        f"inet://{host}:{port}/{db}",
        user=user,
        password=pwd,
        charset=os.environ.get("FB_CHARSET", "WIN1252"),
    )

def db_disponivel() -> bool:
    """Retorna True se conseguir conectar ao banco (para testes de saúde)."""
    try:
        with get_conn() as con:
            cur = con.cursor()
            cur.execute("SELECT 1 FROM rdb$database")
            cur.fetchone()
        return True
    except Exception:
        return False

def versao_servidor() -> str:
    """Retorna string de versão do servidor Firebird."""
    with get_conn() as con:
        cur = con.cursor()
        cur.execute("SELECT rdb$get_context('SYSTEM','ENGINE_VERSION') FROM rdb$database")
        return cur.fetchone()[0]
