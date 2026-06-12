# -*- coding: utf-8 -*-
"""Login gate simples (usuário + senha) para o Painel 3 Amores.

- Senhas guardadas como PBKDF2-HMAC-SHA256 (hashlib, SEM dependência externa) em config/usuarios.yaml.
- SEM config/usuarios.yaml  -> libera o painel (modo local, sem senha).
- COM config/usuarios.yaml   -> exige login (modo servidor/produção).
- Gerar/trocar senha:  py tools/gerar_senha.py <senha> <usuario> "<Nome>"
"""
import os, hashlib, hmac, binascii
import streamlit as st

try:
    import yaml
except Exception:
    yaml = None

ITER = 200_000  # iterações do PBKDF2 (custo p/ dificultar força-bruta)


def hash_senha(senha, salt_hex=None):
    """Devolve (salt_hex, hash_hex). Sem salt -> gera um novo (uso no cadastro)."""
    salt = binascii.unhexlify(salt_hex) if salt_hex else os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", str(senha).encode("utf-8"), salt, ITER)
    return binascii.hexlify(salt).decode(), binascii.hexlify(dk).decode()


def _confere(senha, salt_hex, hash_hex):
    if not salt_hex or not hash_hex:
        return False
    try:
        _, calc = hash_senha(senha, salt_hex)
    except Exception:
        return False
    return hmac.compare_digest(calc, hash_hex)


def _carregar_usuarios(base):
    # Tenta PG primeiro
    try:
        import db_pg as _pg
        if _pg.is_available():
            rows = _pg.fetch_usuarios()
            if rows:
                return {r["login"]: {"nome": r["nome"], "salt": r["salt"], "hash": r["hash"]} for r in rows}
    except Exception:
        pass
    # Fallback YAML
    if yaml is None:
        return {}
    fp = os.path.join(base, "config", "usuarios.yaml")
    if not os.path.exists(fp):
        return {}
    try:
        with open(fp, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data.get("usuarios", {}) or {}
    except Exception:
        return {}


def login_gate(base):
    """Mostra a tela de login. Retorna o nome do usuário logado.
    Retorna None se NÃO houver usuarios.yaml (modo local). PARA a execução
    (st.stop) enquanto não autenticado."""
    usuarios = _carregar_usuarios(base)
    if not usuarios:
        return None  # sem config de usuários -> uso local, sem senha
    try:
        if st.session_state.get("auth_ok"):
            return st.session_state.get("auth_nome")
    except Exception:
        return None  # ambiente de teste/sem session_state -> libera

    try:
        import brand as _brand
        _brand.aplicar(login=True)
    except Exception:
        pass

    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown("""
        <div style='text-align:center;margin-bottom:28px;'>
          <div style='font-size:3.8rem;margin-bottom:8px;'>🥚</div>
          <div style='font-size:1.7rem;font-weight:900;color:#5c3d1e;letter-spacing:2px;
                      text-transform:uppercase;'>Tres Amores Agronegócio</div>
          <div style='width:48px;height:3px;background:#ef7736;margin:8px auto 6px auto;
                      border-radius:2px;'></div>
          <div style='font-size:0.78rem;color:#a07850;letter-spacing:3px;
                      text-transform:uppercase;'>Painel Financeiro</div>
        </div>
        """, unsafe_allow_html=True)
        u = (st.text_input("Usuário", placeholder="seu.usuario") or "").strip().lower()
        p = st.text_input("Senha", type="password", placeholder="••••••••") or ""
        if st.button("Entrar", type="primary", use_container_width=True):
            info = usuarios.get(u)
            if info and _confere(p, info.get("salt", ""), info.get("hash", "")):
                st.session_state["auth_ok"] = True
                st.session_state["auth_nome"] = info.get("nome", u)
                st.session_state["auth_login"] = u
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")
        st.markdown("<div style='text-align:center;margin-top:12px;font-size:0.78rem;color:#aaa;'>Esqueceu a senha? Fale com a Sabrina ou o TI.</div>",
                    unsafe_allow_html=True)
    st.stop()


def logout_button():
    """Mostra 'logado como X' + botão Sair na barra lateral (chamar já dentro do app)."""
    try:
        nome = st.session_state.get("auth_nome")
    except Exception:
        return
    if nome:
        st.sidebar.caption(f"👤 {nome}")
        if st.sidebar.button("🚪 Sair", use_container_width=True):
            for k in ("auth_ok", "auth_nome"):
                st.session_state.pop(k, None)
            st.rerun()


def is_admin():
    """Retorna True se o usuário logado é admin (login = sabrina) ou modo local (sem senha)."""
    try:
        auth_ok = st.session_state.get("auth_ok")
        login   = st.session_state.get("auth_login", "")
        # modo local (sem yaml) -> libera; modo servidor -> só sabrina
        return (not auth_ok) or (login == "sabrina")
    except Exception:
        return True


def _salvar_yaml(base, data):
    if yaml is None:
        raise RuntimeError("pyyaml não instalado")
    fp = os.path.join(base, "config", "usuarios.yaml")
    with open(fp, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)


def listar_usuarios(base):
    """Retorna lista de dicts com login, nome."""
    usuarios = _carregar_usuarios(base)
    return [{"login": k, "nome": v.get("nome", k)} for k, v in sorted(usuarios.items())]


def adicionar_usuario(base, login, nome, senha):
    """Cria ou atualiza usuário. Retorna mensagem de erro ou None (sucesso)."""
    if not login or not nome or not senha:
        return "Preencha login, nome e senha."
    login = login.strip().lower()
    if not login.replace("_", "").replace(".", "").isalnum():
        return "Login deve conter apenas letras, números, ponto ou underline."
    if len(senha) < 6:
        return "Senha deve ter pelo menos 6 caracteres."
    salt, hsh = hash_senha(senha)
    # Tenta PG primeiro
    try:
        import db_pg as _pg
        if _pg.is_available():
            _pg.upsert_usuario(login, nome.strip(), salt, hsh)
            return None
    except Exception as e:
        return f"Erro ao salvar no banco: {e}"
    # Fallback YAML
    if yaml is None:
        return "pyyaml não disponível."
    fp = os.path.join(base, "config", "usuarios.yaml")
    try:
        if os.path.exists(fp):
            with open(fp, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {}
        if "usuarios" not in data:
            data["usuarios"] = {}
        data["usuarios"][login] = {"nome": nome.strip(), "salt": salt, "hash": hsh}
        _salvar_yaml(base, data)
        return None
    except Exception as e:
        return f"Erro ao salvar: {e}"


def remover_usuario(base, login):
    """Remove usuário pelo login. Retorna mensagem de erro ou None."""
    try:
        import db_pg as _pg
        if _pg.is_available():
            _pg.execute("UPDATE usuarios SET ativo = FALSE WHERE login = %s", (login,))
            return None
    except Exception as e:
        return f"Erro ao remover no banco: {e}"
    if yaml is None:
        return "pyyaml não disponível."
    fp = os.path.join(base, "config", "usuarios.yaml")
    try:
        with open(fp, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        usuarios = data.get("usuarios", {})
        if login not in usuarios:
            return f"Usuário '{login}' não encontrado."
        del usuarios[login]
        data["usuarios"] = usuarios
        _salvar_yaml(base, data)
        return None
    except Exception as e:
        return f"Erro ao remover: {e}"


def alterar_senha(base, login, senha_nova):
    """Altera a senha de um usuário existente. Retorna mensagem de erro ou None."""
    if len(senha_nova) < 6:
        return "Senha deve ter pelo menos 6 caracteres."
    salt, hsh = hash_senha(senha_nova)
    try:
        import db_pg as _pg
        if _pg.is_available():
            _pg.execute("UPDATE usuarios SET salt=%s, hash=%s WHERE login=%s AND ativo=TRUE", (salt, hsh, login))
            return None
    except Exception as e:
        return f"Erro ao alterar no banco: {e}"
    if yaml is None:
        return "pyyaml não disponível."
    fp = os.path.join(base, "config", "usuarios.yaml")
    try:
        with open(fp, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if login not in data.get("usuarios", {}):
            return f"Usuário '{login}' não encontrado."
        data["usuarios"][login]["salt"] = salt
        data["usuarios"][login]["hash"] = hsh
        _salvar_yaml(base, data)
        return None
    except Exception as e:
        return f"Erro ao alterar senha: {e}"
