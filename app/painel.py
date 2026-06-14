# -*- coding: utf-8 -*-
"""Painel Financeiro 3 Amores — Streamlit. Apontar pasta -> Atualizar -> filtrar período -> DRE."""
import os
import pandas as pd
import streamlit as st
import brutils as B, configs as C, dre as D, fc as FC, bp as BP, biological as BIO, extrato as EX
import brand as _brand

# --- Suporte a modo banco de dados (Firebird) ---
try:
    import ingest_db as _IDB
    _DB_DISPONIVEL = True
except ImportError:
    _DB_DISPONIVEL = False

try:
    import ofx_upload as _OFX
    _OFX_DISPONIVEL = True
except ImportError:
    _OFX_DISPONIVEL = False

try:
    import imob_upload as _IMOB
    _IMOB_DISPONIVEL = True
except ImportError:
    _IMOB_DISPONIVEL = False

try:
    import pdf_upload as _PDF
    _PDF_DISPONIVEL = True
except ImportError:
    _PDF_DISPONIVEL = False

# --- PostgreSQL auxiliar (parametrizações, extratos, usuários) ---
try:
    import db_pg as _PG
    import pg_migrate as _PGM
    import config_pg as _CFG_PG
    _PG_DISPONIVEL = True
except ImportError:
    _PG_DISPONIVEL = False
    _CFG_PG = None

st.set_page_config(page_title="Painel Financeiro 3 Amores", page_icon="🥚", layout="wide")
_brand.aplicar()
# CSS: sidebar hamburger e tema geral
st.markdown("""<style>
/* Botão RECOLHER/EXPANDIR sidebar — transparente */
[data-testid="stSidebarCollapseButton"] button,
button[data-testid="collapsedControl"] {
    background:transparent!important;border:none!important;box-shadow:none!important;
}
[data-testid="stSidebarCollapseButton"] button:hover,
button[data-testid="collapsedControl"]:hover {
    background:rgba(255,255,255,.12)!important;border-radius:6px!important;
}
section[data-testid="stSidebar"]{transition:all .25s ease;}
/* Botões de módulo — sombra de escurecimento no hover/focus */
section[data-testid="stSidebar"] .stButton > button:hover,
section[data-testid="stSidebar"] .stButton > button:focus {
    filter:brightness(.88)!important;
    box-shadow:inset 0 0 0 100px rgba(0,0,0,.12)!important;
}
/* Botões de export na sidebar — 1º download=Excel(verde), 2º download=PDF(vermelho) */
section[data-testid="stSidebar"] div[data-testid="stDownloadButton"]:nth-of-type(1) button {
    background:#1D6F42!important;color:white!important;font-weight:700!important;border:none!important;
}
section[data-testid="stSidebar"] div[data-testid="stDownloadButton"]:nth-of-type(1) button:hover {
    background:#175a35!important;color:white!important;
}
section[data-testid="stSidebar"] div[data-testid="stDownloadButton"]:nth-of-type(2) button {
    background:#c0392b!important;color:white!important;font-weight:700!important;border:none!important;
}
section[data-testid="stSidebar"] div[data-testid="stDownloadButton"]:nth-of-type(2) button:hover {
    background:#a93226!important;color:white!important;
}
/* Spinner — esconde só o texto, mantém o ícone */
div[data-testid="stSpinner"] > div > p { display:none!important; }
</style>""", unsafe_allow_html=True)
# Marca a página como pt-BR e "não traduzir": senão a tradução automática do navegador
# troca "mil" por "milhões" nos KPIs (é bug do TRADUTOR, não do cálculo). Best-effort.
try:
    import streamlit.components.v1 as _comp
    _comp.html("<script>try{var d=window.parent.document;d.documentElement.lang='pt-BR';d.documentElement.setAttribute('translate','no');d.documentElement.classList.add('notranslate');var m=d.createElement('meta');m.name='google';m.content='notranslate';d.head.appendChild(m);}catch(e){}</script>", height=0)
except Exception:
    pass
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Pasta de DADOS (planilhas/extratos/correções/usuarios): no VPS aponta p/ a pasta SMB via variável
# de ambiente PAINEL_DADOS; no uso local é a própria pasta do projeto. Mantém o CÓDIGO (git) separado
# dos DADOS (SMB) — o `git pull` atualiza o código sem tocar nos dados.
DADOS = os.environ.get("PAINEL_DADOS", ROOT)

# --- PostgreSQL: inicializa schema e migra CSVs na primeira execução ---
if _PG_DISPONIVEL and _PG.is_available():
    try:
        _PGM.migrate_all(os.path.join(DADOS, "config"))
    except Exception as _e:
        pass  # não impede o painel de abrir

# --- Login: exige senha se existir <DADOS>/config/usuarios.yaml (servidor); senão libera (uso local) ---
import auth as _auth
_USUARIO = _auth.login_gate(DADOS)

@st.cache_data(show_spinner="Conectando ao banco de dados (Firebird)...", ttl=1800)
def carregar_do_banco(base):
    cfg = C.load(os.path.join(base, "config"))
    return _IDB.load_all_db(cfg)

@st.cache_data(show_spinner="Carregando extratos bancários...", ttl=1800)
def carregar_extratos():
    try: return EX.load_transacoes()
    except Exception:
        import pandas as _pd
        return _pd.DataFrame(), _pd.DataFrame()

@st.cache_data(show_spinner="Calculando DRE...")
def _calc_dre(_dfs, per_tuple, _cfg_obj, biologico):
    return D.compute(_dfs, list(per_tuple), _cfg_obj, biologico)

@st.cache_data(show_spinner="Calculando DRE mensal...")
def _calc_dre_mensal(_dfs, periodos_tuple, _cfg_obj, biologico):
    return {p: D.compute(_dfs, [p], _cfg_obj, biologico) for p in periodos_tuple}

def _mes_lbl(p):
    ms = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]
    return f"{ms[int(p[5:])-1]}/{p[2:4]}"

@st.cache_data(show_spinner="Calculando Balanço...")
def _calc_bp(_dfs, per_tuple, _cfg_obj, biologico, caixa_real, adiant_clientes, aporte_socio, emprestimos):
    return BP.compute(_dfs, list(per_tuple), _cfg_obj, biologico,
                      caixa_real=caixa_real, adiant_clientes=adiant_clientes,
                      aporte_socio=aporte_socio, emprestimos=emprestimos)

@st.cache_data(show_spinner="Classificando extratos...")
def _calc_buckets(_tx_ex, periodo_fim, overrides_ex):
    if _tx_ex is None or not len(_tx_ex):
        return {"adiant": 0.0, "aporte": 0.0, "emprestimos": 0.0}
    return EX.buckets_balanco(_tx_ex, periodo_fim, overrides_ex)

@st.cache_data(show_spinner="Calculando Fluxo de Caixa...")
def _calc_fc(_dfs, per_tuple):
    return FC.compute(_dfs, list(per_tuple))

@st.cache_data(show_spinner="Calculando FC mensal...")
def _calc_fc_mensal(_dfs, periodos_tuple):
    return {p: FC.compute(_dfs, [p]) for p in periodos_tuple}

@st.cache_data(show_spinner="Calculando Indicadores...")
def _calc_indicadores(_dfs, per_tuple, _cfg_obj, biologico, caixa_real, adiant_clientes, aporte_socio, emprestimos):
    return BP.indicadores(_dfs, list(per_tuple), _cfg_obj, biologico,
                          caixa_real=caixa_real, adiant_clientes=adiant_clientes,
                          aporte_socio=aporte_socio, emprestimos=emprestimos)

def money_col(df, col="valor"):
    df = df.copy(); df[col] = df[col].map(B.brl); return df

# Paleta de destaque para linhas da DRE
_DRE_STYLE = {
    "section":  "background-color:#FEF3E2;font-weight:700;color:#7B4F2E",
    "total":    "background-color:#FFF0E0;font-weight:700;border-top:2px solid #ef7736",
    "subtotal": "background-color:#EEF2F7;font-weight:700",
    "profit":   "background-color:#E8EFF7;font-weight:700",
}

def _dre_styler(df, tipo_map, highlight_cols=None):
    """Aplica cores de linha ao dataframe DRE baseado no tipo (section/total/subtotal/profit).
    highlight_cols: lista de nomes de colunas que recebem destaque adicional (ex: TOTAL, Média/mês)."""
    def _row(row):
        t = tipo_map[row.name] if row.name < len(tipo_map) else "det"
        css = _DRE_STYLE.get(t, "")
        return [css] * len(row)
    s = df.style.apply(_row, axis=1)
    if highlight_cols:
        for _hc in highlight_cols:
            if _hc in df.columns:
                s = s.set_properties(
                    subset=[_hc],
                    **{"background-color": "#FEF3E2", "font-weight": "bold",
                       "border-left": "2px solid #ef7736"}
                )
    return s

def tabela_drill(df, grupo, valor="valor", *, key, det_cols=None, col_label=None, fmt=B.brl, topn=None, height_det=300):
    """RASTREÁVEL: tabela <grupo → Total, nº> CLICÁVEL. Clicar numa linha abre, embaixo, os
    lançamentos individuais que somam aquele valor (rastreabilidade). grupo: str ou lista."""
    if df is None or not len(df):
        st.caption("(sem dados no período)"); return
    gcols = grupo if isinstance(grupo, list) else [grupo]
    g = (df.groupby(gcols)[valor].agg(["sum", "count"]).reset_index()
           .sort_values("sum", ascending=False).reset_index(drop=True))
    if topn: g = g.head(topn).reset_index(drop=True)
    g["Total (R$)"] = g["sum"].map(fmt)
    show = g[gcols + ["Total (R$)", "count"]].rename(columns={"count": "nº", **(col_label or {})})
    sel = st.dataframe(show, hide_index=True, use_container_width=True,
                       on_select="rerun", selection_mode="single-row", key=key)
    rows = []
    try:
        s = sel.selection.rows
        if isinstance(s, (list, tuple)): rows = list(s)
    except Exception:
        rows = []
    if rows and rows[0] < len(g):
        sub = df
        for gc in gcols:
            sub = sub[sub[gc] == g.iloc[rows[0]][gc]]
        rot = " · ".join(str(g.iloc[rows[0]][gc]) for gc in gcols)
        st.markdown(f"###### 🔎 {rot} — {len(sub)} lançamento(s) · {fmt(float(sub[valor].sum()))}")
        cols = [c for c in (det_cols or list(df.columns)) if c in sub.columns]
        d = sub[cols].copy()
        if valor in d.columns: d[valor] = d[valor].map(fmt)
        st.dataframe(d, hide_index=True, use_container_width=True, height=height_det)
    else:
        st.caption("👆 Clique numa linha para rastrear os lançamentos que somam o valor.")

# ---------------- Sidebar ----------------
pasta = DADOS

try:
    dfs = carregar_do_banco(pasta)
except Exception as e:
    st.error(f"Erro ao carregar banco de dados:\n\n{e}"); st.stop()

cfg_obj = C.load(os.path.join(pasta, "config"))
periodos = dfs["periodos"]
if not periodos:
    st.warning("Nenhum dado encontrado. Clique em Atualizar dados."); st.stop()
periodos = sorted(periodos)
anos = sorted({p[:4] for p in periodos})

# Identidade do usuário logado
_nome_usuario = str(_USUARIO) if _USUARIO else "Usuário"

st.sidebar.markdown(f"""
<div style='text-align:center;padding:12px 0 8px 0'>
  <div style='font-size:2.2rem;'>🥚</div>
  <div style='font-size:1rem;font-weight:800;color:#e5dfcc;letter-spacing:1px;margin-top:4px;'>TRES AMORES AGRONEGÓCIO</div>
  <div style='font-size:.65rem;color:#c4b49a;letter-spacing:2px;text-transform:uppercase;margin-top:2px;'>Painel Financeiro</div>
  <div style='font-size:.72rem;color:#c4a87a;margin-top:6px;'>👤 {_nome_usuario}</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")

# Navegação por módulo
st.sidebar.markdown("<div style='font-size:.68rem;color:#a08060;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:4px;padding-left:4px;'>Módulos</div>", unsafe_allow_html=True)
_MODULOS = [
    ("🏠", "Início"),
    ("📊", "DRE"),
    ("🔧", "Reapropriar/Verificar"),
    ("💰", "Receita"),
    ("📦", "Estoque"),
    ("🏦", "Fluxo de Caixa"),
    ("🧾", "Extrato/Reconciliação"),
    ("🏛️", "Balanço"),
    ("📈", "Indicadores"),
    ("⚙️", "Config"),
    ("📤", "Importar Dados"),
]
if _auth.is_admin():
    _MODULOS.append(("👥", "Usuários"))

if "modulo_ativo" not in st.session_state:
    st.session_state["modulo_ativo"] = "Início"

for _ico, _mod in _MODULOS:
    _ativo = st.session_state["modulo_ativo"] == _mod
    _estilo = ("background:#ef7736;color:white;font-weight:700;" if _ativo
               else "background:rgba(255,255,255,.06);color:#e5dfcc;")
    if st.sidebar.button(f"{_ico}  {_mod}", key=f"nav_{_mod}", use_container_width=True):
        st.session_state["modulo_ativo"] = _mod
        st.rerun()

st.sidebar.markdown("---")

if st.sidebar.button("🔄 Atualizar dados", use_container_width=True, type="primary"):
    st.cache_data.clear(); st.rerun()
_auth.logout_button()

def _get_bloco(row):
    g, s = str(row.get("grupo", "")), str(row.get("subgrupo", ""))
    if g == "OVOS_3AMORES": return "OVOS 3 AMORES MATRIZ" if s == "MATRIZ" else "OVOS 3 AMORES SILVEIRA"
    if g == "COMPOSTAGEM":  return "COMPOSTAGEM 3 AMORES"
    if g == "PLANTACAO":    return "Plantação"
    if g == "PARTICULAR":   return "Particular"
    return g.title() if g else "Outros"

_modulo_pre = st.session_state.get("modulo_ativo", "Início")

# -------- Cabeçalho compacto (oculto na tela Início) --------
_desp_g = dfs["despesa"]
_rec_g  = dfs["receita"]
if len(_desp_g):
    _desp_g = _desp_g.copy()
    _desp_g["bloco"] = _desp_g.apply(_get_bloco, axis=1)

if _modulo_pre != "Início":
    _hp, _hs, _hb, _hc = st.columns([1.8, 3.0, 2.2, 2.2])

    with _hp:
        modo = st.radio("📅 Período", ["Acumulado", "Ano", "Mês", "Meses", "Intervalo"],
                        horizontal=True, key="modo_per", label_visibility="collapsed")

    with _hs:
        if modo == "Ano":
            a = st.selectbox("Ano", anos, index=len(anos) - 1, key="ano_per", label_visibility="collapsed")
            per = [p for p in periodos if p[:4] == a]; sel = f"Ano {a}"
        elif modo == "Mês":
            m = st.selectbox("Mês", periodos, index=len(periodos) - 1, key="mes_per", label_visibility="collapsed")
            per = [m]; sel = m
        elif modo == "Meses":
            _ms = st.multiselect(
                "Meses", periodos,
                default=periodos[-min(3, len(periodos)):],
                format_func=_mes_lbl, key="meses_per",
                label_visibility="collapsed",
                placeholder="Selecione meses (não sequenciais)...",
            )
            per = sorted(_ms) if _ms else periodos
            sel = "Meses: " + ", ".join(_mes_lbl(p) for p in per) if per != periodos else "Todos os meses"
        elif modo == "Intervalo":
            _si1, _si2 = st.columns(2)
            with _si1: ini = st.selectbox("De", periodos, index=0, key="ini_per", label_visibility="collapsed")
            with _si2: fim = st.selectbox("Até", periodos, index=len(periodos) - 1, key="fim_per", label_visibility="collapsed")
            if ini > fim: ini, fim = fim, ini
            per = [p for p in periodos if ini <= p <= fim]; sel = f"{ini} a {fim}"
        else:
            per = periodos; sel = "Acumulado (tudo)"
            st.markdown("<div style='font-size:.78rem;color:#888;padding-top:6px;'>todos os meses</div>",
                        unsafe_allow_html=True)

    _blocos_all_g = sorted(_desp_g["bloco"].dropna().unique()) if len(_desp_g) else []
    with _hb:
        _sel_blocos_g = st.multiselect("🏗️ Bloco", _blocos_all_g, default=[],
                                       key="g_blocos", placeholder="Todos os blocos",
                                       label_visibility="collapsed")
    _sel_blocos_g = _sel_blocos_g or _blocos_all_g
    _desp_g_b   = _desp_g[_desp_g["bloco"].isin(_sel_blocos_g)] if len(_desp_g) else _desp_g
    _desp_ccs_g = sorted(_desp_g_b["cc"].dropna().unique()) if len(_desp_g_b) else []
    _rec_ccs_g  = sorted({c for c in (_rec_g["cc"].dropna() if "cc" in _rec_g.columns and len(_rec_g) else []) if c})
    _ccs_all_g  = sorted(set(_desp_ccs_g) | set(_rec_ccs_g))
    with _hc:
        _sel_ccs_g_raw = st.multiselect("🏷️ CC", _ccs_all_g, default=[],
                                        key="g_ccs", placeholder="Todos os CCs",
                                        label_visibility="collapsed")
    _sel_ccs_g  = _sel_ccs_g_raw or _ccs_all_g
    _desp_fil_g = _desp_g_b[_desp_g_b["cc"].isin(_sel_ccs_g)] if len(_desp_g_b) else _desp_g_b
    _rec_fil_g  = (_rec_g[_rec_g["cc"].isin(_sel_ccs_g)]
                   if _sel_ccs_g_raw and "cc" in _rec_g.columns and len(_rec_g) else None)
    _filtrou_g  = bool(_sel_ccs_g_raw) or len(_desp_fil_g) < len(_desp_g)

    st.markdown("<hr style='margin:4px 0 2px 0;border:none;border-top:2px solid #ef7736;opacity:.35;'>",
                unsafe_allow_html=True)
else:
    # Tela Início: sem filtros — usa período completo como padrão
    modo            = "Acumulado"
    per             = periodos
    sel             = "Acumulado (tudo)"
    _blocos_all_g   = []
    _sel_blocos_g   = []
    _desp_g_b       = _desp_g
    _ccs_all_g      = []
    _sel_ccs_g_raw  = []
    _sel_ccs_g      = []
    _desp_fil_g     = _desp_g
    _rec_fil_g      = None
    _filtrou_g      = False

if dfs["dropped"]:
    st.sidebar.warning("Duplicados ignorados:\n" + "\n".join("• " + d for d in dfs["dropped"]))

biologico = cfg_obj.biologico_default  # ativo biológico sempre ligado (padrão do config)

_per_tuple = tuple(per)   # tuple é hasheável → permite cache por período

V = _calc_dre(dfs, _per_tuple, cfg_obj, biologico)
desp, rec = dfs["despesa"], dfs["receita"]
P = set(per)
bal = lambda dest: float(desp[(desp.destino == dest) & (desp.periodo.isin(P))].valor.sum()) if len(desp) else 0.0

tx_ex, rs_ex = carregar_extratos()
caixa_real_v, caixa_brk = (EX.caixa_real_fim(rs_ex, per[-1]) if len(rs_ex) else (None, None))
overrides_ex = EX.carregar_overrides(pasta) if len(tx_ex) else {}
_bk = _calc_buckets(tx_ex if len(tx_ex) else None, per[-1], overrides_ex)
adiant_v, emprest_v = _bk["adiant"], _bk["emprestimos"]
# aporte = residual pela identidade contábil (BP sem aporte → DIFERENCA vira o aporte líquido)
aporte_v = max(0.0, _calc_bp(dfs, _per_tuple, cfg_obj, biologico,
                              caixa_real_v, adiant_v, 0.0, emprest_v).get("DIFERENCA", 0.0))
_bruto_aporte = _bk.get("aporte", 0.0)

st.sidebar.divider()
try:
    import export as EXP
    _nome = "Painel_3Amores_" + "".join(c if c.isalnum() else "_" for c in sel) + ".xlsx"
    with st.sidebar:
        st.markdown('<div class="btn-excel">', unsafe_allow_html=True)
        st.download_button("📗 Exportar em Excel",
            EXP.build_excel(dfs, per, cfg_obj, biologico, caixa_real_v, adiant_v, aporte_v, tx_ex, emprest_v, overrides_ex),
            file_name=_nome, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True, help="DRE, Fluxo de Caixa, Balanço, Indicadores, Receita, Reconciliação e Reapropriar — 1 aba cada.")
        st.markdown('</div>', unsafe_allow_html=True)
except Exception as _e:
    st.sidebar.caption(f"(Excel indisponível: {_e})")
try:
    import report as RPT
    _pnome = "Relatorio_3Amores_" + "".join(c if c.isalnum() else "_" for c in sel) + ".pdf"
    with st.sidebar:
        st.markdown('<div class="btn-pdf">', unsafe_allow_html=True)
        st.download_button("📕 Exportar em PDF",
            RPT.build_pdf(dfs, per, cfg_obj, biologico, caixa_real_v, adiant_v, aporte_v, emprest_v, tx_ex, overrides_ex, sel),
            file_name=_pnome, mime="application/pdf", use_container_width=True,
            help="3 páginas para o sócio: veredito + DRE + Fluxo de Caixa + Balanço + Indicadores + Reconciliação.")
        st.markdown('</div>', unsafe_allow_html=True)
except Exception as _e:
    st.sidebar.caption(f"(PDF indisponível: {_e})")

_modulo = _modulo_pre

# helper bloco (usado no DRE e no FC)
def _filtro_bloco_cc(df_src, key_prefix):
    df = df_src.copy()
    if len(df):
        df["bloco"] = df.apply(_get_bloco, axis=1)
    else:
        df["bloco"] = ""
    blocos_all = sorted(df["bloco"].dropna().unique()) if len(df) else []
    _c1, _c2 = st.columns(2)
    with _c1:
        sel_b = st.multiselect("🏗️ Bloco", blocos_all, default=[],
                               key=f"{key_prefix}_blocos", placeholder="Todos os blocos")
    sel_b = sel_b or blocos_all
    df_b = df[df["bloco"].isin(sel_b)]
    ccs_all = sorted(df_b["cc"].dropna().unique()) if len(df_b) else []
    with _c2:
        sel_c = st.multiselect("🏷️ Centro de Custo", ccs_all, default=[],
                               key=f"{key_prefix}_ccs", placeholder="Todos os CCs do bloco")
    sel_c = sel_c or ccs_all
    return df_b[df_b["cc"].isin(sel_c)]

# ---------------- INÍCIO ----------------
if _modulo == "Início":
    _primer = _nome_usuario.split()[0] if _nome_usuario else "Usuário"
    st.markdown(f"""
    <div style="padding:40px 8px 16px 8px;">
      <div style="font-size:2.6rem;font-weight:800;color:#3d2008;line-height:1.2;">
        👋 Seja Bem Vindo(a), {_primer}!
      </div>
      <div style="font-size:1.15rem;color:#888;margin-top:10px;">
        Painel Financeiro Gerencial · Tres Amores Agronegócio
      </div>
    </div>
    """, unsafe_allow_html=True)

# ---------------- DRE ----------------
elif _modulo == "DRE":
    # Monta dfs filtrados para o cálculo do DRE (usa filtro global do cabeçalho)
    _dfs_dre = dict(dfs)
    if _filtrou_g:
        _dfs_dre["despesa"] = _desp_fil_g
        if _rec_fil_g is not None:
            _dfs_dre["receita"] = _rec_fil_g

    V_dre = D.compute(_dfs_dre, per, cfg_obj, biologico)

    # Título com linha descritiva do filtro/período ativo
    _desc_partes = [f"Período: {sel}"]
    if _sel_ccs_g_raw:
        _desc_partes.append(f"CC: {', '.join(_sel_ccs_g_raw)}")
    if _sel_blocos_g != _blocos_all_g:
        _desc_partes.append(f"Bloco: {', '.join(_sel_blocos_g)}")
    _desc_filtro = " · ".join(_desc_partes)
    st.markdown(f"""<div style="margin-bottom:14px;">
      <div style="font-size:1.35rem;font-weight:800;color:#3d2008;letter-spacing:.3px;">
        DRE GERENCIAL (Por Competência)</div>
      <div style="font-size:.78rem;color:#999;margin-top:3px;">{_desc_filtro}</div>
    </div>""", unsafe_allow_html=True)

    # Período anterior para comparação nos cards
    _periodos_set = set(periodos)
    def _get_per_prev():
        if not per: return [], ""
        if modo == "Mês":
            y, m_ = int(per[0][:4]), int(per[0][5:])
            m_ -= 1
            if m_ == 0: m_, y = 12, y - 1
            p = f"{y}-{m_:02d}"
            lbl = f"Mês Ant. ({_mes_lbl(p)})" if p in _periodos_set else ""
            return ([p] if p in _periodos_set else []), lbl
        elif modo == "Ano":
            py = str(int(per[0][:4]) - 1)
            pp = [p for p in periodos if p[:4] == py]
            return pp, (f"Ano Ant. ({py})" if pp else "")
        else:
            n = len(per)
            y, m_ = int(per[0][:4]), int(per[0][5:])
            pp = []
            for _ in range(n):
                m_ -= 1
                if m_ == 0: m_, y = 12, y - 1
                pp.insert(0, f"{y}-{m_:02d}")
            pp = [p for p in pp if p in _periodos_set]
            lbl = f"{n} Meses Ant." if n > 1 else "Mês Ant."
            return pp, (lbl if pp else "")
    _per_prev, _lbl_prev = _get_per_prev()
    V_prev = D.compute(_dfs_dre, _per_prev, cfg_obj, biologico) if _per_prev else None

    def _kpi_card(titulo, valor, vp, lbl_prev, icone=""):
        cor = "#1a7f3c" if valor >= 0 else "#c0392b"
        borda = "#ef7736" if titulo == "Faturamento Bruto" else cor
        if vp is not None:
            delta = valor - vp
            pct = (delta / abs(vp) * 100) if vp != 0 else 0
            d_cor = "#1a7f3c" if delta >= 0 else "#c0392b"
            d_sig = "▲" if delta > 0 else ("▼" if delta < 0 else "—")
            sub = (f'<span style="color:{d_cor};font-weight:700;">{d_sig} {B.brl_compact(abs(delta))}'
                   f' ({pct:+.1f}%)</span>'
                   f' <span style="color:#bbb;font-size:.68rem;">{lbl_prev}</span>')
        else:
            sub = f'<span style="color:#ccc;">{lbl_prev or "—"}</span>'
        return f"""<div style="background:linear-gradient(135deg,#fffcf9 0%,#fff 100%);
            border:1.5px solid {borda};border-radius:14px;padding:16px 20px;
            box-shadow:0 2px 10px rgba(0,0,0,.07);height:100%;">
          <div style="font-size:.7rem;font-weight:700;color:#a07850;letter-spacing:.8px;
               text-transform:uppercase;margin-bottom:6px;">{icone} {titulo}</div>
          <div style="font-size:1.6rem;font-weight:800;color:#2d1a0e;line-height:1.1;">
            {B.brl_compact(valor)}</div>
          <div style="font-size:.75rem;margin-top:5px;">{sub}</div>
        </div>"""

    def _vp(key): return V_prev[key] if V_prev else None
    _kc = st.columns(4)
    _kc[0].markdown(_kpi_card("Faturamento Bruto", V_dre["FAT_BRUTO"],   _vp("FAT_BRUTO"),   _lbl_prev, "💰"), unsafe_allow_html=True)
    _kc[1].markdown(_kpi_card("Lucro Bruto",       V_dre["LUCRO_BRUTO"], _vp("LUCRO_BRUTO"), _lbl_prev, "📦"), unsafe_allow_html=True)
    _kc[2].markdown(_kpi_card("EBITDA",            V_dre["EBITDA"],      _vp("EBITDA"),      _lbl_prev, "📊"), unsafe_allow_html=True)
    _kc[3].markdown(_kpi_card("Lucro Líquido",     V_dre["LUCRO_LIQ"],   _vp("LUCRO_LIQ"),   _lbl_prev, "🏆"), unsafe_allow_html=True)
    st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)

    fat = V_dre["FAT_BRUTO"] or 1

    # _dre_det e _idk_map disponíveis em ambas as vistas (matriz e coluna única)
    _idk_map = [idk or "" for _, _, idk in D.LAYOUT]
    _tipo_map = [tipo for tipo, _, _ in D.LAYOUT]

    def _dre_det(idk):
        _COR_MAP = {"BRA": "Branco", "VER": "Vermelho", "CAI": "Caipira", "PLT": "Plantação"}
        rec_per = rec[(rec.destino == "RECEITA") & (rec.periodo.isin(P))] if len(rec) else rec
        dre_rows_f = desp[(desp.destino == "DRE") & (desp.periodo.isin(P))] if len(desp) else desp
        if idk in _COR_MAP:
            cor = _COR_MAP[idk]
            sub = rec_per[rec_per.cor == cor] if "cor" in rec_per.columns else rec_per.iloc[0:0]
            cols = [c for c in ["periodo", "data", "produto", "cliente", "nota", "valor"] if c in sub.columns]
        elif idk and len(dre_rows_f) and "linha_dre" in dre_rows_f.columns:
            sub = dre_rows_f[dre_rows_f.linha_dre == idk]
            cols = [c for c in ["periodo", "data", "credor", "conta", "cc", "valor"] if c in sub.columns]
        else:
            return pd.DataFrame(), []
        det = sub[cols].copy() if cols else sub.copy()
        if "valor" in det.columns: det["valor"] = det["valor"].map(B.brl)
        return det, cols

    def _dre_render_det(rows_list, idk_map_list, val_col, state_key, close_prefix):
        """Renderiza as expansões de drill-down para a lista de índices abertos."""
        ROW_PX = 35; HDR_PX = 40
        for _ri in sorted(st.session_state.get(state_key, set())):
            if _ri >= len(rows_list): continue
            _idk       = idk_map_list[_ri] if _ri < len(idk_map_list) else ""
            _label_mae = str(rows_list[_ri].get("Descrição", rows_list[_ri].get("Linha", ""))).strip()
            _val_mae   = rows_list[_ri].get(val_col, "")
            _det, _    = _dre_det(_idk)
            _hcol1, _hcol2 = st.columns([0.96, 0.04])
            with _hcol1:
                st.markdown(
                    f"""<div style="background:#FFF3E0;border-left:5px solid #FF9800;
                        padding:7px 14px;font-weight:700;font-size:14px;
                        display:flex;justify-content:space-between;align-items:center;
                        border-radius:2px;margin-top:4px;">
                        <span>▶ {_label_mae}</span>
                        <span style="color:#E65100;">{_val_mae}</span>
                    </div>""", unsafe_allow_html=True)
            with _hcol2:
                if st.button("✕", key=f"{close_prefix}_{_ri}", help="Fechar detalhe"):
                    st.session_state[state_key].discard(_ri); st.rerun()
            if len(_det):
                _det_h = min(HDR_PX + ROW_PX * len(_det), 380)
                st.dataframe(_det.style.set_properties(**{"background-color": "#FFF8F0"}),
                             hide_index=True, use_container_width=True, height=_det_h)
            else:
                st.markdown(
                    f'<div style="background:#FFF8F0;border-left:5px solid #FFCC80;'
                    f'padding:6px 14px;font-size:13px;color:#888;border-radius:2px;">'
                    f'Sem lançamentos individuais para <b>{_label_mae}</b> (linha calculada ou sem dados).</div>',
                    unsafe_allow_html=True)

    _HCOLS = ["TOTAL", "Média/mês", "Melhor mês", "Pior mês"]

    if len(per) > 1:
        # ── Vista matricial: uma coluna por mês + Total + Média + drill-down ─
        _use_cache_m = not _filtrou_g
        if _use_cache_m:
            _vper = _calc_dre_mensal(dfs, _per_tuple, cfg_obj, biologico)
        else:
            _vper = {p: D.compute(_dfs_dre, [p], cfg_obj, biologico) for p in per}
        _rows_m = []
        for tipo, label, idk in D.LAYOUT:
            ind = "    " if tipo in ("sub", "det") else ""
            row = {"Descrição": ind + label}
            vals_n = []
            for p in per:
                v = _vper[p].get(idk) if idk else None
                row[_mes_lbl(p)] = B.brl(v) if v is not None else ""
                if v is not None: vals_n.append(v)
            if idk and vals_n:
                _tot = sum(vals_n)
                row["TOTAL"] = B.brl(_tot)
                row["Média/mês"] = B.brl(_tot / len(vals_n))
                row["Melhor mês"] = B.brl(max(vals_n))
                row["Pior mês"]   = B.brl(min(vals_n))
            else:
                row["TOTAL"] = row["Média/mês"] = row["Melhor mês"] = row["Pior mês"] = ""
            _rows_m.append(row)
        df_dre = pd.DataFrame(_rows_m)
        _h_dre = min(44 + 35 * len(_rows_m), 950)
        _dre_sel_m = st.dataframe(
            _dre_styler(df_dre, _tipo_map, highlight_cols=_HCOLS),
            hide_index=True, use_container_width=True, height=_h_dre,
            on_select="rerun", selection_mode="single-row", key="dre_table_m",
        )
        st.caption("👆 Clique em qualquer linha para ver **todos os lançamentos do período** que somam aquela linha. Clique novamente para fechar.")

        if "dre_open_m" not in st.session_state:
            st.session_state["dre_open_m"] = set()
        try:
            _clicked_m = _dre_sel_m.selection.rows
            if isinstance(_clicked_m, (list, tuple)) and _clicked_m:
                _ci_m = _clicked_m[0]
                if _ci_m in st.session_state["dre_open_m"]: st.session_state["dre_open_m"].discard(_ci_m)
                else: st.session_state["dre_open_m"].add(_ci_m)
            # sem st.rerun() extra — o on_select já dispara o rerun necessário
        except Exception: pass

        _dre_render_det(_rows_m, _idk_map, "TOTAL", "dre_open_m", "dre_close_m")

    else:
        # ── Vista detalhada: coluna única + drill-down (período único) ───────
        _HCOLS = ["Valor (R$)", "% Fat."]
        linhas = []
        for tipo, label, idk in D.LAYOUT:
            ind = "    " if tipo in ("sub", "det") else ""
            val = V_dre.get(idk) if idk else None
            linhas.append({
                "Linha": ind + label,
                "Valor (R$)": B.brl(val) if val is not None else "",
                "% Fat.": (f"{100*val/fat:.1f}%" if (val is not None and tipo != 'section') else ""),
                "Descrição": ind + label,  # alias p/ _dre_render_det
            })
        df_dre = pd.DataFrame([{k: v for k, v in r.items() if k != "Descrição"} for r in linhas])

        _dre_sel = st.dataframe(
            _dre_styler(df_dre, _tipo_map),
            hide_index=True, use_container_width=True, height=880,
            on_select="rerun", selection_mode="single-row", key="dre_table",
        )
        st.caption("👆 Clique em qualquer linha para ver os lançamentos. Clique novamente para fechar.")

        if "dre_open" not in st.session_state:
            st.session_state["dre_open"] = set()
        try:
            _clicked = _dre_sel.selection.rows
            if isinstance(_clicked, (list, tuple)) and _clicked:
                _ci = _clicked[0]
                if _ci in st.session_state["dre_open"]: st.session_state["dre_open"].discard(_ci)
                else: st.session_state["dre_open"].add(_ci)
        except Exception: pass

        _dre_render_det(linhas, _idk_map, "Valor (R$)", "dre_open", "dre_close")

    st.markdown("**Fora da DRE (transparente — nada some):**")
    b = st.columns(4)
    b[0].metric("CAPEX (investimento)", B.brl_compact(bal("CAPEX")), help=B.brl(bal("CAPEX")))
    b[1].metric("A Reapropriar", B.brl_compact(bal("REAPROPRIAR")), help=B.brl(bal("REAPROPRIAR")))
    b[2].metric("Ignorado (adiant./migração)", B.brl_compact(bal("IGNORADO")), help=B.brl(bal("IGNORADO")))
    est = desp[(desp.destino == "ESTOQUE") & (desp.periodo.isin(P))] if len(desp) else desp
    _estv = float(est.valor.sum()) if len(est) else 0
    b[3].metric("Estoque (compras MP)", B.brl_compact(_estv), help=B.brl(_estv))
    st.caption("PIS/COFINS sem lançamento → não calculados por alíquota. Embalagem por **consumo** (composição × caixas produzidas; ver cobertura na aba Estoque). Salários sem CC caem em Reapropriar.")

# ---------------- Reapropriar ----------------
elif _modulo == "Reapropriar/Verificar":
    st.subheader("Reapropriar / Verificar — lançamentos sem CC ou sem conta (fora da DRE)")
    rea = desp[(desp.destino == "REAPROPRIAR") & (desp.periodo.isin(P))] if len(desp) else desp
    st.metric("Total a reapropriar", B.brl(float(rea.valor.sum()) if len(rea) else 0))
    if len(rea):
        c1, c2 = st.columns(2)
        with c1:
            st.write("Por motivo (clique p/ rastrear):")
            tabela_drill(rea, "motivo", key="rea_motivo", col_label={"motivo": "Motivo"},
                         det_cols=["periodo", "data", "credor", "conta", "cc", "valor"])
        with c2:
            st.write("Por credor — top 30 (clique p/ rastrear):")
            tabela_drill(rea, "credor", key="rea_credor", topn=30, col_label={"credor": "Credor"},
                         det_cols=["periodo", "data", "credor", "conta", "cc", "valor"])
        st.write("Lançamentos:")
        st.dataframe(money_col(rea[["periodo", "credor", "conta", "cc", "valor"]]), hide_index=True, use_container_width=True, height=380)
        st.info("Corrija o Centro de Custo / Conta na fonte e clique Atualizar — o lançamento flui sozinho para o lugar certo.")

# ---------------- Receita ----------------
elif _modulo == "Receita":
    st.subheader("Receita (emissão / competência)")
    rok = rec[(rec.destino == "RECEITA") & (rec.periodo.isin(P))] if len(rec) else rec
    if len(rok):
        c1, c2 = st.columns(2)
        with c1:
            st.write("Por unidade / cor (clique p/ rastrear):")
            tabela_drill(rok, ["unidade", "cor"], key="rec_unicor",
                         col_label={"unidade": "Unidade", "cor": "Cor"},
                         det_cols=["periodo", "data", "produto", "cliente", "valor"])
        with c2:
            st.write("Por produto — top 30 (clique p/ rastrear):")
            tabela_drill(rok, "produto", key="rec_prod", topn=30, col_label={"produto": "Produto"},
                         det_cols=["periodo", "data", "produto", "unidade", "cor", "cliente", "valor"])
    desc = rec[(rec.destino == "DESCARTE") & (rec.periodo.isin(P))] if len(rec) else rec
    if len(desc):
        st.caption(f"Descarte de aves (não é receita; Fase 6): {B.brl(float(desc.valor.sum()))}")

# ---------------- Estoque ----------------
elif _modulo == "Estoque":
    st.subheader("Estoque / CMV por consumo")
    prod = dfs.get("producao")
    if prod is not None and len(prod):
        pp = prod[prod.periodo.isin(P)]
        emb_tot = float(pp.emb_total.sum()); emb_exact = float(pp[pp.matched].emb_total.sum())
        qx = float(pp[pp.matched].qtd.sum()); qt = float(pp.qtd.sum()); cov = 100 * qx / qt if qt else 0
        c = st.columns(3)
        c[0].metric("Embalagem (consumo)", B.brl_compact(emb_tot), help=B.brl(emb_tot))
        c[1].metric("Cobertura da composição", f"{cov:.0f}% das caixas", help=f"{qx:,.0f} de {qt:,.0f} caixas têm receita")
        c[2].metric("Parte estimada", B.brl_compact(emb_tot - emb_exact), help="produtos sem receita → estimados por ovo")
        st.caption("Produto **com** receita → custo exato. **Sem** receita → estimativa por ovo (R$/ovo médio das receitas). Complete o `config_composicao.csv` (ou reexporte a composição cheia) para ficar 100% exato — o painel se ajusta no Atualizar.")
        st.write("Embalagem consumida por unidade:")
        tabela_drill(pp, "unidade", valor="emb_total", key="est_emb", col_label={"unidade": "Unidade"},
                     det_cols=["periodo", "galpao", "descricao", "qtd", "emb_total"])
        falt = pp[~pp.matched].groupby("descricao").agg(caixas=("qtd", "sum"), emb_estimada=("emb_total", "sum")).reset_index().sort_values("emb_estimada", ascending=False)
        if len(falt):
            st.warning(f"⚠️ {len(falt)} produtos produzidos SEM receita de composição (embalagem estimada). Adicione-os ao config_composicao.csv:")
            falt["emb_estimada"] = falt["emb_estimada"].map(B.brl); falt["caixas"] = falt["caixas"].map(lambda x: f"{x:,.0f}")
            st.dataframe(falt, hide_index=True, use_container_width=True, height=280)
    st.divider()
    rac = dfs["racao"]
    if len(rac):
        st.write("Ração produzida por fase e galpão — **POSTURA** = CMV ração · **RECRIA** = ativo biológico:")
        racp = rac[rac.periodo.isin(P)]
        tabela_drill(racp, ["fase", "galpao"], valor="custo", key="est_racao",
                     col_label={"fase": "Fase", "galpao": "Galpão"},
                     det_cols=["periodo", "galpao", "descricao", "qtd", "custo"])
    st.divider()
    st.markdown(f"### 🐔 Ativo Biológico — lote {cfg_obj.lote.get('lote_id','GR01')} → {cfg_obj.lote.get('galpao_postura','GS02')}")
    comp = BIO.componentes(dfs); total_bio = sum(comp.values())
    cc = st.columns(4)
    cc[0].metric("Pintainhas", B.brl_compact(comp["pintainhas"]), help=B.brl(comp["pintainhas"]))
    cc[1].metric("Ração de recria", B.brl_compact(comp["racao_recria"]), help=B.brl(comp["racao_recria"]))
    cc[2].metric("Galpão recria", B.brl_compact(comp["galpao_recria"]), help=B.brl(comp["galpao_recria"]))
    cc[3].metric("Custo total de formação", B.brl_compact(total_bio), help=B.brl(total_bio))
    av, tot, amort = BIO.asset_value(dfs, cfg_obj, per)
    st.caption(f"Amortização **linear em {cfg_obj.lote.get('ciclo_postura_meses','13')} meses** desde {cfg_obj.lote.get('data_inicio_postura','—')}, lançada contra **{cfg_obj.lote.get('galpao_postura','GS02')}** (FILIAL). "
               f"Valor do ativo no fim do período: **{B.brl(av)}** (custo {B.brl(tot)} − amort. acumulada {B.brl(amort)}). "
               f"{'✅ Tratamento LIGADO' if biologico else '⚠️ Tratamento DESLIGADO (recria vira despesa)'} — alterne na barra lateral.")

# ---------------- Fluxo de Caixa ----------------
elif _modulo == "Fluxo de Caixa":
    st.subheader(f"Fluxo de Caixa — Sistema (regime de caixa) — {sel}")
    Fv = _calc_fc(dfs, _per_tuple)
    k = st.columns(4)
    k[0].metric("Entradas (recebido)", B.brl_compact(Fv["ENT_OPER"]), help=B.brl(Fv["ENT_OPER"]))
    k[1].metric("Saídas (pago)", B.brl_compact(Fv["SAI_TOTAL"]), help=B.brl(Fv["SAI_TOTAL"]))
    k[2].metric("Fluxo operacional", B.brl_compact(Fv["FLUXO_OPER"]), help=B.brl(Fv["FLUXO_OPER"]))
    k[3].metric("Fluxo líquido", B.brl_compact(Fv["FLUXO_LIQ"]), help=B.brl(Fv["FLUXO_LIQ"]))

    # helper drill-down FC (saídas ou entradas do período selecionado)
    _fc_idk_map  = [idk or "" for _, _, idk in FC.LAYOUT]
    _fc_tipo_map = [t for t, _, _ in FC.LAYOUT]
    _fc_lab_map  = [lab for _, lab, _ in FC.LAYOUT]

    def _fc_det(idx):
        t_type = _fc_tipo_map[idx] if idx < len(_fc_tipo_map) else ""
        idk_k  = _fc_idk_map[idx]  if idx < len(_fc_idk_map)  else ""
        sai = dfs.get("fc_saidas"); ent = dfs.get("fc_entradas")
        if "ENT" in idk_k or t_type in ("ent",):
            if ent is not None and len(ent):
                sub = ent[ent.periodo.isin(P)].copy()
                cols = [c for c in ["periodo", "data", "credor", "conta", "valor"] if c in sub.columns]
                sub = sub[cols]
                if "valor" in sub.columns: sub = sub.copy(); sub["valor"] = sub["valor"].map(B.brl)
                return sub
        if sai is not None and len(sai):
            sub = sai[sai.periodo.isin(P)].copy()
            cols = [c for c in ["periodo", "data", "credor", "conta", "categoria", "valor"] if c in sub.columns]
            sub = sub[cols]
            if "valor" in sub.columns: sub = sub.copy(); sub["valor"] = sub["valor"].map(B.brl)
            return sub
        return pd.DataFrame()

    if len(per) > 1:
        # ── Vista matricial FC ───────────────────────────────────────────────
        _fper = _calc_fc_mensal(dfs, _per_tuple)
        _rows_fc = []
        for t, lab, idk in FC.LAYOUT:
            ind = "    " if t == "sai" else ""
            row = {"Descrição": ind + lab}
            vals_n = []
            for p in per:
                v = _fper[p].get(idk)
                row[_mes_lbl(p)] = B.brl(v) if v is not None else ""
                if v is not None: vals_n.append(v)
            if vals_n:
                _tot = sum(vals_n)
                row["TOTAL"] = B.brl(_tot)
                row["Média/mês"] = B.brl(_tot / len(vals_n))
            else:
                row["TOTAL"] = row["Média/mês"] = ""
            _rows_fc.append(row)
        _df_fc_m = pd.DataFrame(_rows_fc)
        _h_fc = min(44 + 35 * len(_rows_fc), 600)
        _fc_sel_m = st.dataframe(_df_fc_m, hide_index=True, use_container_width=True, height=_h_fc,
                                 on_select="rerun", selection_mode="single-row", key="fc_table_m")
        st.caption("👆 Clique em qualquer linha para ver os lançamentos do período completo.")

        if "fc_open_m" not in st.session_state:
            st.session_state["fc_open_m"] = set()
        try:
            _fc_clicked_m = _fc_sel_m.selection.rows
            if isinstance(_fc_clicked_m, (list, tuple)) and _fc_clicked_m:
                _fci_m = _fc_clicked_m[0]
                if _fci_m in st.session_state["fc_open_m"]: st.session_state["fc_open_m"].discard(_fci_m)
                else: st.session_state["fc_open_m"].add(_fci_m)
        except Exception: pass

        ROW_PX = 35; HDR_PX = 40
        for _frim in sorted(st.session_state.get("fc_open_m", set())):
            if _frim >= len(_rows_fc): continue
            _flab  = _fc_lab_map[_frim] if _frim < len(_fc_lab_map) else ""
            _fval  = _rows_fc[_frim].get("TOTAL", "")
            _fdet  = _fc_det(_frim)
            _fhc1, _fhc2 = st.columns([0.96, 0.04])
            with _fhc1:
                st.markdown(f"""<div style="background:#E8F5E9;border-left:5px solid #43A047;
                    padding:7px 14px;font-weight:700;font-size:14px;
                    display:flex;justify-content:space-between;align-items:center;
                    border-radius:2px;margin-top:4px;">
                    <span>▶ {_flab}</span><span style="color:#1B5E20;">{_fval}</span>
                </div>""", unsafe_allow_html=True)
            with _fhc2:
                if st.button("✕", key=f"fc_close_m_{_frim}", help="Fechar detalhe"):
                    st.session_state["fc_open_m"].discard(_frim); st.rerun()
            if len(_fdet):
                _fdh = min(HDR_PX + ROW_PX * len(_fdet), 380)
                st.dataframe(_fdet.style.set_properties(**{"background-color": "#F1F8E9"}),
                             hide_index=True, use_container_width=True, height=_fdh)
            else:
                st.markdown("<div style='padding:8px 12px;color:#999;font-size:13px;'>Sem lançamentos disponíveis para esta linha.</div>", unsafe_allow_html=True)
    else:
        st.dataframe(pd.DataFrame([{"Linha": ("    " if t == "sai" else "") + lab, "Valor (R$)": B.brl(Fv[idk])}
                                   for t, lab, idk in FC.LAYOUT]), hide_index=True, use_container_width=True)
    st.caption("FC-**Sistema** (relatórios da empresa). FC-**Extrato** (extratos bancários) + reconciliação → aba 🧾.")
    sai = dfs.get("fc_saidas")
    if sai is not None and len(sai):
        sp = sai[sai.periodo.isin(P)].copy()
        # Aplica filtro global de Bloco/CC do cabeçalho
        if _filtrou_g:
            sp["grupo"]    = sp["cc"].str.upper().map(lambda x: cfg_obj.cc2info.get(x, {}).get("grupo", "")).fillna("")
            sp["subgrupo"] = sp["cc"].str.upper().map(lambda x: cfg_obj.cc2info.get(x, {}).get("subgrupo", "")).fillna("")
            sp["bloco"] = sp.apply(_get_bloco, axis=1)
            sp = sp[sp["cc"].isin(_sel_ccs_g)]
            st.caption(f"🔍 Filtro ativo: {len(_sel_blocos_g)} bloco(s) · {len(_sel_ccs_g)} CC(s) — altere no cabeçalho.")
        c1, c2 = st.columns(2)
        with c1:
            st.write("Saídas por categoria:")
            tabela_drill(sp, "categoria", key="fc_cat", col_label={"categoria": "Categoria"},
                         det_cols=["periodo", "data", "credor", "conta", "categoria", "valor"])
        with c2:
            st.write("Saídas por credor — top 20:")
            tabela_drill(sp, "credor", key="fc_credor", topn=20, col_label={"credor": "Credor"},
                         det_cols=["periodo", "data", "credor", "conta", "categoria", "valor"])
    if dfs.get("fc_dropped"):
        st.caption("Duplicados ignorados (saídas): " + ", ".join(dfs["fc_dropped"]))

# ---------------- Extrato / Reconciliação ----------------
elif _modulo == "Extrato/Reconciliação":
    st.subheader(f"Extrato bancário × Sistema — caixa real e reconciliação — {sel}")
    if not len(rs_ex):
        st.warning("Nenhum extrato bancário encontrado. Importe arquivos OFX ou PDF na aba **📤 Importar Dados**.")
    else:
        op = cfg_obj.saldo_caixa_inicial
        fc_month = _calc_fc_mensal(dfs, tuple(periodos))
        cx_fim = caixa_real_v if caixa_real_v is not None else 0.0
        fc_acum = sum(fc_month[p]["FLUXO_LIQ"] for p in periodos if p <= per[-1])
        gap = cx_fim - (op + fc_acum)
        k = st.columns(4)
        k[0].metric("💵 Caixa real (fim do período)", B.brl_compact(cx_fim), help=B.brl(cx_fim))
        k[1].metric("Caixa de abertura 01/01/25", B.brl_compact(op), help=B.brl(op))
        k[2].metric("FC-Sistema acumulado", B.brl_compact(fc_acum), help=B.brl(fc_acum))
        k[3].metric("GAP (entradas fora do sistema)", B.brl_compact(gap), help=B.brl(gap))
        st.caption("O **GAP** = dinheiro que entrou no banco mas o sistema de faturamento/desembolso **não enxerga**: "
                   "**aportes de capital, empréstimos e transferências entre as contas próprias**. É o que explica a *Diferença a investigar* do Balanço.")
        st.markdown("#### Saldo real por conta (último saldo conhecido até o período)")
        b = caixa_brk.copy()
        b["Saldo (R$)"] = b.saldo_fim.map(B.brl)
        b["Fonte"] = b.aprox.map(lambda a: "≈ aprox. (CONTAMAX)" if a else "exato (cadeia)")
        st.dataframe(b[["chave", "periodo", "Saldo (R$)", "Fonte"]].rename(columns={"chave": "Conta", "periodo": "Mês"}),
                     hide_index=True, use_container_width=True)
        st.markdown("#### Trajetória: caixa real × Sistema (mês a mês)")
        rec, acum = [], op
        for p in periodos:
            cxp = EX.caixa_real_fim(rs_ex, p)[0]; acum += fc_month[p]["FLUXO_LIQ"]
            rec.append({"Mês": p, "Caixa real (fim)": B.brl(cxp), "FC-Sistema líq. (mês)": B.brl(fc_month[p]["FLUXO_LIQ"]),
                        "Caixa se só sistema": B.brl(acum), "GAP acumulado": B.brl(cxp - acum)})
        st.dataframe(pd.DataFrame(rec), hide_index=True, use_container_width=True, height=400)
        st.markdown("#### Reconciliação das entradas por classe de pagador")
        if len(tx_ex):
            cl = EX.entradas_classificadas(tx_ex, per, overrides_ex)
            if len(cl):
                rcl = (cl.groupby("classe").valor.agg(["sum", "count"]).reset_index()
                         .sort_values("sum", ascending=False).reset_index(drop=True))
                rcl["Total (R$)"] = rcl["sum"].map(B.brl)
                c1, c2 = st.columns([3, 2])
                with c1:
                    _selcl = st.dataframe(
                        rcl[["classe", "Total (R$)", "count"]].rename(columns={"classe": "Classe", "count": "nº"}),
                        hide_index=True, use_container_width=True,
                        on_select="rerun", selection_mode="single-row", key="recl_drill")
                    st.caption("👆 **Clique numa classe** para abrir os lançamentos abaixo. AgroMais → **Passivo** · Aporte Álvaro → **PL** · Intercompany → **neta** · Outros = PIX sem pagador.")
                with c2:
                    fc_ent_tot = sum(fc_month[p]["ENT_OPER"] for p in per)
                    fat_tot = D.compute(dfs, per, cfg_obj, biologico)["FAT_BRUTO"]
                    st.metric("Operacional — FC-Sistema (recebido)", B.brl_compact(fc_ent_tot), help=B.brl(fc_ent_tot))
                    st.metric("Operacional — DRE faturamento", B.brl_compact(fat_tot), help=B.brl(fat_tot))
                    st.caption("Os dois batem → sistema de receita **consistente**. O excedente no banco é financiamento/intercompany.")
                # ---- drill-down: lançamentos da classe clicada ----
                _rows = []
                try:
                    _s = _selcl.selection.rows
                    if isinstance(_s, (list, tuple)): _rows = list(_s)
                except Exception:
                    _rows = []
                if _rows and _rows[0] < len(rcl):
                    _classe = rcl.iloc[_rows[0]]["classe"]
                    _det = cl[cl.classe == _classe].sort_values("valor", ascending=False)
                    st.markdown(f"##### 🔎 Lançamentos de **{_classe}** — {len(_det)} entradas · {B.brl(float(_det.valor.sum()))}")
                    st.caption("✏️ Classificado errado? Escolha a natureza certa na coluna **Corrigir p/** e clique **💾 Salvar**. "
                               "Vocabulário: **cliente · aporte · mutuo · emprestimo · intercompany · adiantamento**. (Em branco = mantém como está.)")
                    _ed = _det[["tid", "periodo", "data", "chave", "valor", "desc"]].reset_index(drop=True).copy()
                    _view = pd.DataFrame({
                        "Mês": _ed["periodo"], "Data": _ed["data"].astype(str), "Conta": _ed["chave"],
                        "Valor (R$)": _ed["valor"].map(B.brl), "Histórico / Pagador": _ed["desc"], "Corrigir p/": ""})
                    _opts = ["", "cliente", "aporte", "mutuo", "emprestimo", "intercompany", "adiantamento"]
                    _edited = st.data_editor(
                        _view, hide_index=True, use_container_width=True, height=380, key=f"edt_{_rows[0]}",
                        column_config={"Corrigir p/": st.column_config.SelectboxColumn("Corrigir p/ (natureza)", options=_opts, width="medium")},
                        disabled=["Mês", "Data", "Conta", "Valor (R$)", "Histórico / Pagador"])
                    if st.button("💾 Salvar correções", key=f"save_{_rows[0]}", type="primary"):
                        _mapa = {}
                        for _i, _nat in enumerate(list(_edited["Corrigir p/"])):
                            _nat = (str(_nat) if _nat is not None else "").strip()
                            if _nat and _i < len(_ed):
                                _r = _ed.iloc[_i]
                                _mapa[str(_r["tid"])] = {"natureza": _nat, "banco": str(_r["chave"]),
                                                         "data": str(_r["data"]), "valor": str(_r["valor"]), "desc": str(_r["desc"])}
                        if _mapa:
                            _n = EX.salvar_correcoes(pasta, _mapa)
                            st.cache_data.clear()
                            st.success(f"✅ {_n} correção(ões) salva(s)! Reclassificando…")
                            st.rerun()
                        else:
                            st.warning("Preencha a coluna **Corrigir p/** em pelo menos uma linha antes de salvar.")
                else:
                    st.caption("ℹ️ Clique numa linha da tabela de classes acima para abrir aqui os lançamentos que compõem o valor.")
            outros = EX.creditos_outros(tx_ex, per, overrides_ex)
            if len(outros):
                st.markdown(f"#### 'Outros recebimentos' a classificar — {len(outros)} lançs · {B.brl(outros.valor.sum())}")
                show = outros.head(50).copy(); show["valor"] = show["valor"].map(B.brl)
                st.dataframe(show.rename(columns={"periodo": "Mês", "data": "Data", "banco": "Banco", "titular": "Titular", "valor": "Valor (R$)", "desc": "Histórico/Doc"}),
                             hide_index=True, use_container_width=True, height=320)
                try:
                    import io
                    buf = io.BytesIO(); outros.to_excel(buf, index=False, sheet_name="Outros a classificar")
                    st.download_button("⬇️ Baixar Excel dos 'Outros' para rotular a natureza", buf.getvalue(),
                        file_name="creditos_outros_para_classificar.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                except Exception as _e:
                    st.caption(f"(Excel indisponível: {_e})")
        st.info("✅ **Bradesco + BB exatos** (cadeia de saldos validada: abertura[M+1] = fechamento[M]). "
                "⚠️ **Santander aproximado** (c/c varre p/ CONTAMAX; saldo real só na data de emissão do PDF). "
                "Netagem das transferências intercompany + refino do Santander = Fase 7.")

# ---------------- Balanço ----------------
elif _modulo == "Balanço":
    st.subheader(f"Balanço Patrimonial (gerencial) — posição em {per[-1]}")
    Bv = _calc_bp(dfs, _per_tuple, cfg_obj, biologico, caixa_real_v, adiant_v, aporte_v, emprest_v)
    k = st.columns(4)
    k[0].metric("Ativo total", B.brl_compact(Bv["ATIVO_TOTAL"]), help=B.brl(Bv["ATIVO_TOTAL"]))
    k[1].metric("Passivo total", B.brl_compact(Bv["PASSIVO_TOTAL"]), help=B.brl(Bv["PASSIVO_TOTAL"]))
    k[2].metric("Patrimônio Líquido", B.brl_compact(Bv["PL"]), help=B.brl(Bv["PL"]))
    k[3].metric("Diferença a investigar", B.brl_compact(Bv["DIFERENCA"]), help=B.brl(Bv["DIFERENCA"]))
    _bp_rows, _bp_idk_map = [], []
    for t, lab, idk in BP.LAYOUT:
        val = Bv.get(idk) if idk else None
        ind = "" if t in ("h", "t", "dif") else ("  " if t in ("h2", "st") else "    ")
        _bp_rows.append({"Conta": ind + lab, "Valor (R$)": (B.brl(val) if val is not None else "")})
        _bp_idk_map.append(idk or "")
    _df_bp = pd.DataFrame(_bp_rows)
    _bp_sel = st.dataframe(_df_bp, hide_index=True, use_container_width=True, height=720,
                           on_select="rerun", selection_mode="single-row", key="bp_table")
    st.caption("👆 Clique em qualquer linha para ver a origem dos valores.")

    if "bp_open" not in st.session_state:
        st.session_state["bp_open"] = set()
    try:
        _bp_clicked = _bp_sel.selection.rows
        if isinstance(_bp_clicked, (list, tuple)) and _bp_clicked:
            _bci = _bp_clicked[0]
            if _bci in st.session_state["bp_open"]:
                st.session_state["bp_open"].discard(_bci)
            else:
                st.session_state["bp_open"].add(_bci)
        # sem st.rerun() extra — o on_select já dispara o rerun necessário
    except Exception: pass

    # ---- Drill-down helper: retorna (df_detalhe, mensagem_str) ----
    def _bp_det(idk_k):
        P_set = set(per)
        A_set = set(BP._acum(dfs, per))
        empty = pd.DataFrame()
        desp_a = dfs["despesa"]
        imob_a = dfs.get("imob", pd.DataFrame())

        if idk_k == "CAIXA":
            fonte = Bv.get("CAIXA_FONTE", "estimado")
            if "real" in fonte and len(rs_ex):
                rows_c = []
                for _, s in rs_ex[rs_ex.periodo.isin(P_set)].iterrows():
                    rows_c.append({"Banco/Conta": s.get("conta", ""), "Período": s.get("periodo", ""),
                                   "Saldo final (R$)": B.brl(s.get("saldo_fim", 0))})
                return pd.DataFrame(rows_c) if rows_c else empty, "Saldos reais dos extratos bancários."
            return empty, f"Caixa estimado: Saldo inicial R$ 17.431,11 + Δsistema {B.brl(Bv.get('DCAIXA_SIST',0))}. Para saldo real, use a aba 🧾 Extrato."

        if idk_k == "CR":
            rok = dfs["receita"]
            rok_p = rok[(rok.destino == "RECEITA") & (rok.periodo.isin(P_set))] if len(rok) else rok
            ent_p = dfs["fc_entradas"]
            ent_p = ent_p[ent_p.periodo.isin(P_set)] if len(ent_p) else ent_p
            fat = float(rok_p.valor.sum()) if len(rok_p) else 0.0
            rec = float(ent_p.valor.sum()) if len(ent_p) else 0.0
            return empty, f"Faturado no período: {B.brl(fat)} − Recebido pelo FC: {B.brl(rec)} = CR estimado {B.brl(max(0.0, fat-rec))}. (Aproximação — reconciliação exata na aba 🧾 Extrato.)"

        if idk_k == "ESTOQUE":
            est = desp_a[(desp_a.destino == "ESTOQUE") & (desp_a.periodo.isin(A_set))] if len(desp_a) else empty
            if not len(est): return empty, "Nenhuma compra de inventariável encontrada no período acumulado."
            g = (est.groupby(["conta", "credor"], dropna=False)["valor"].sum()
                   .reset_index().sort_values("valor", ascending=False))
            g.columns = ["Conta", "Fornecedor/Credor", "Compras (R$)"]
            g["Compras (R$)"] = g["Compras (R$)"].map(B.brl)
            consumo = float(dfs["racao"][dfs["racao"].periodo.isin(A_set)].custo.sum()) if len(dfs["racao"]) else 0.0
            return g, f"Estoque = Compras inventariáveis {B.brl(float(est.valor.sum()))} − Consumo ração/emb {B.brl(consumo)} ≈ {B.brl(max(0.0, float(est.valor.sum())-consumo))}."

        if idk_k in ("IMOB_BRUTO", "IMOB_LIQ", "DEPREC_ACUM"):
            if imob_a is None or not len(imob_a): return empty, "Sem dados de imobilizado."
            nbio = imob_a[~imob_a.is_bio].copy()
            if not len(nbio): return empty, "Nenhum item de imobilizado não-biológico."
            nbio["Aq. (R$)"]     = nbio.valor_aquisicao.map(B.brl)
            nbio["Saldo pagar"]  = nbio.saldo_a_pagar.map(B.brl)
            nbio["Deprec/mês"]   = nbio.deprec_mensal.map(B.brl)
            return nbio[["item", "classe", "Aq. (R$)", "Saldo pagar", "Deprec/mês", "em_uso"]].rename(
                columns={"item": "Item", "classe": "Classe", "em_uso": "Em uso"}), ""

        if idk_k == "ATIVO_BIO":
            if imob_a is None or not len(imob_a): return empty, "Sem dados de ativo biológico."
            bio = imob_a[imob_a.is_bio].copy()
            if not len(bio): return empty, "Nenhum item biológico registrado."
            bio["Aq. (R$)"]   = bio.valor_aquisicao.map(B.brl)
            bio["Saldo pagar"] = bio.saldo_a_pagar.map(B.brl)
            return bio[["item", "classe", "Aq. (R$)", "Saldo pagar"]].rename(
                columns={"item": "Item", "classe": "Classe"}), "Custo de recria capitalizado (pintainhas + ração recria + galpão recria) − amortização acumulada."

        if idk_k == "APORTES_PAGAR":
            if imob_a is None or not len(imob_a): return empty, "Sem dados de imobilizado."
            pag = imob_a[imob_a.saldo_a_pagar > 0].copy()
            if not len(pag): return empty, "Nenhuma parcela de CAPEX a pagar."
            pag["Aq. (R$)"]    = pag.valor_aquisicao.map(B.brl)
            pag["A pagar (R$)"] = pag.saldo_a_pagar.map(B.brl)
            return pag[["item", "classe", "Aq. (R$)", "A pagar (R$)"]].rename(
                columns={"item": "Item", "classe": "Classe"}), ""

        if idk_k in ("ADIANT_CLI", "EMPRESTIMOS", "AFAC_SOCIO") and len(tx_ex):
            cl = EX.entradas_classificadas(tx_ex, overrides=overrides_ex)
            if not len(cl): return empty, "Sem transações classificadas nos extratos."
            A_ord = int(per[-1][:4]) * 12 + int(per[-1][5:])
            cl = cl[(cl.ano * 12 + cl.mes) <= A_ord].copy()
            cls_map = {"ADIANT_CLI": ["adiantamento"], "EMPRESTIMOS": ["mutuo", "emprestimo"],
                       "AFAC_SOCIO": ["aporte"]}
            classes = cls_map.get(idk_k, [])
            dest_map = {"adiantamento": "PASS_ADI", "mutuo": "PASS_EMP", "emprestimo": "PASS_EMP", "aporte": "PL"}
            dests = {dest_map[c] for c in classes if c in dest_map}
            cl["dest"] = cl.classe.map(EX.destino_natureza)
            sub = cl[cl.dest.isin(dests)].copy()
            if not len(sub): return empty, f"Nenhuma transação classificada como {'/'.join(classes)} nos extratos."
            sub = sub.sort_values("valor", ascending=False).head(100)
            sub["Data"] = sub["data"] if "data" in sub.columns else sub.get("periodo", "")
            sub["Valor (R$)"] = sub.valor.map(B.brl)
            cols = [c for c in ["conta", "Data", "periodo", "desc", "Valor (R$)"] if c in sub.columns]
            return sub[cols].rename(columns={"conta": "Conta", "periodo": "Período", "desc": "Descrição"}), ""

        if idk_k == "PREJ_ACUM":
            dre_v = D.compute(dfs, list(BP._acum(dfs, per)), cfg_obj, biologico)
            linhas_dre = [
                ("Faturamento bruto", dre_v.get("FAT_BRUTO")),
                ("(−) Deduções", -dre_v.get("DED_TOTAL", 0)),
                ("Receita líquida", dre_v.get("REC_LIQ")),
                ("(−) CMV total", -dre_v.get("CMV_TOTAL", 0)),
                ("Lucro bruto", dre_v.get("LUCRO_BRUTO")),
                ("(−) Despesas operacionais", -dre_v.get("OPER_TOTAL", 0)),
                ("EBITDA", dre_v.get("EBITDA")),
                ("(−) Depreciação", -dre_v.get("DEPREC", 0)),
                ("EBIT", dre_v.get("EBIT")),
                ("(±) Resultado financeiro", dre_v.get("RESULT_FIN")),
                ("(−) Impostos", -dre_v.get("IMP_TOTAL", 0)),
                ("Lucro líquido acumulado", dre_v.get("LUCRO_LIQ")),
            ]
            df_dre2 = pd.DataFrame(linhas_dre, columns=["Linha DRE", "Valor (R$)"])
            df_dre2["Valor (R$)"] = df_dre2["Valor (R$)"].map(lambda v: B.brl(v) if v is not None else "—")
            return df_dre2, "DRE acumulada até o fim do período selecionado (mesma base do Balanço)."

        if idk_k == "CAPITAL":
            return empty, f"Capital Social informado na configuração: {B.brl(Bv.get('CAPITAL', 0))} (config_geral.yaml)."

        return empty, ""

    # ---- Renderiza expansões ----
    _ROW_PX = 35; _HDR_PX = 40
    for _bri in sorted(st.session_state["bp_open"]):
        if _bri >= len(_bp_rows): continue
        _bidk  = _bp_idk_map[_bri]
        _blab  = _bp_rows[_bri]["Conta"].strip()
        _bval  = _bp_rows[_bri]["Valor (R$)"]
        if not _bidk: continue   # cabeçalho/subtotal sem dado
        _bdet, _bmsg = _bp_det(_bidk)
        _bhcol1, _bhcol2 = st.columns([0.96, 0.04])
        with _bhcol1:
            st.markdown(
                f"""<div style="background:#FFF3E0;border-left:5px solid #FF9800;
                    padding:7px 14px;font-weight:700;font-size:14px;
                    display:flex;justify-content:space-between;align-items:center;
                    border-radius:2px;margin-top:4px;">
                    <span>▶ {_blab}</span><span style="color:#E65100;">{_bval}</span>
                </div>""", unsafe_allow_html=True)
        with _bhcol2:
            if st.button("✕", key=f"bp_close_{_bri}", help="Fechar detalhe"):
                st.session_state["bp_open"].discard(_bri)
                st.rerun()
        if _bmsg:
            st.info(_bmsg)
        if len(_bdet):
            _bh = min(_HDR_PX + _ROW_PX * len(_bdet), 380)
            st.dataframe(_bdet.style.set_properties(**{"background-color": "#FFF8F0"}),
                         hide_index=True, use_container_width=True, height=_bh)
        elif not _bmsg:
            st.markdown("<div style='padding:8px 12px;color:#999;font-size:13px;'>Sem detalhe disponível para esta linha.</div>",
                        unsafe_allow_html=True)
    _fonte = Bv.get("CAIXA_FONTE", "")
    if "real" in _fonte:
        st.success(f"💵 **Caixa agora vem dos EXTRATOS reais** ({B.brl(Bv['CAIXA'])}) — Bradesco+BB exatos (cadeia de saldos) + Santander aproximado. Veja a aba 🧾 Extrato/Reconciliação.")
    if Bv.get("ADIANT_CLI", 0) or Bv.get("AFAC_SOCIO", 0) or Bv.get("EMPRESTIMOS", 0):
        st.success(f"🔎 **Fase 7 — fechamento gerencial:** Aporte do sócio/grupo (**líquido**) **{B.brl(Bv['AFAC_SOCIO'])}** no PL · "
                   f"Adiant. AgroMais **{B.brl(Bv['ADIANT_CLI'])}** + Mútuos **{B.brl(Bv['EMPRESTIMOS'])}** no Passivo · "
                   f"Diferença a investigar → **{B.brl(Bv['DIFERENCA'])}**.")
        st.caption(f"O aporte é o **líquido**, medido pela identidade contábil (Ativo + Prejuízos − Capital) e confirmado pelos extratos como dinheiro do grupo. "
                   f"A soma BRUTA dos rótulos é **{B.brl(_bruto_aporte)}** — bem maior porque o mesmo dinheiro **circula entre as contas** (cada volta conta de novo). "
                   f"`cliente` = venda realizada (já está na Receita; não vira passivo). Gerencial (§3): fecha porque o funding está **medido e evidenciado**, não chutado.")
    else:
        st.caption("*Aproximações: **Contas a Receber/Estoque**. A **Diferença a investigar** ≈ aportes/empréstimos do grupo ainda não rotulados — aba 🧾 Extrato, baixe o Excel e preencha *natureza*.")

# ---------------- Indicadores ----------------
elif _modulo == "Indicadores":
    st.subheader(f"Indicadores (DRE × Balanço) — {sel}")
    ind, Bv = _calc_indicadores(dfs, _per_tuple, cfg_obj, biologico, caixa_real_v, adiant_v, aporte_v, emprest_v)
    def _pct(x): return f"{100*x:.1f}%" if x is not None else "—"
    def _num(x): return f"{x:.2f}" if x is not None else "—"
    k = st.columns(4)
    k[0].metric("ROE (LL/PL)", _pct(ind["ROE"]))
    k[1].metric("Liquidez Corrente (AC/PC)", _num(ind["LIQ_CORR"]))
    k[2].metric("Endividamento (Passivo/PL)", _num(ind["ENDIV"]))
    k[3].metric("ROCE (EBIT/(Ativo−PC))", _pct(ind["ROCE"]))
    ll, ebitda = ind["_LL"], ind["_EBITDA"]
    if ebitda < 0: vered = "🔴 DEFICITÁRIO — opera no vermelho (EBITDA acumulado negativo)"
    elif ll < 0: vered = "🟡 NO LIMITE — gera caixa operacional, mas o resultado final ainda é negativo"
    else: vered = "🟢 RENTÁVEL"
    st.markdown(f"### Veredito: {vered}")
    st.caption(f"EBITDA acumulado {B.brl(ebitda)} · Lucro líquido acumulado {B.brl(ll)}. PL negativo (prejuízos > capital) distorce ROE/Endividamento — informe o Capital Social e o caixa (extrato) para indicadores confiáveis.")
    st.info("A normalização do **Ativo Biológico (Fase 6)** vai realocar o custo da recria e melhorar a leitura de 2025 (hoje 2025 'parece desastre' pela formação do plantel).")

# ---------------- Config ----------------
elif _modulo == "Config":  # noqa: E305
    _cfg_abas = ["⚙️ Parâmetros", "📊 Status", "🔬 Diagnóstico BD"] if _auth.is_admin() else ["⚙️ Parâmetros", "📊 Status"]
    _cfg_tabs = st.tabs(_cfg_abas)

    with _cfg_tabs[0]:
        st.subheader("⚙️ Configurações")
        if _CFG_PG is not None:
            _CFG_PG.render(pasta)
        else:
            st.warning("Módulo config_pg não disponível.")
            cfgdir = os.path.join(pasta, "config")
            for fn in ["config_contas.csv", "config_centros_custo.csv", "config_produtos.csv"]:
                fp = os.path.join(cfgdir, fn)
                if os.path.exists(fp):
                    with st.expander(fn):
                        try: st.dataframe(pd.read_csv(fp, sep=";", encoding="utf-8-sig"), hide_index=True, height=280, use_container_width=True)
                        except Exception as e: st.write(f"(erro: {e})")

    with _cfg_tabs[1]:
        st.subheader("📊 Status dos dados carregados")
        _rac = dfs.get("racao"); _prod = dfs.get("producao"); _desp = dfs.get("despesa"); _rec = dfs.get("receita")
        _col1, _col2 = st.columns(2)
        with _col1:
            st.metric("Ração (linhas)", len(_rac) if _rac is not None else 0,
                      help="POSTURA + RECRIA de '4 PRODUTOS PRODUZIDOS'")
            if _rac is not None and len(_rac):
                st.caption(f"POSTURA: {len(_rac[_rac.fase=='POSTURA'])} · RECRIA: {len(_rac[_rac.fase=='RECRIA'])}")
            else:
                st.error("⚠️ Nenhum dado de produção/ração retornado pelo banco.")
            st.metric("Produção/Ovos (linhas)", len(_prod) if _prod is not None else 0,
                      help="Fase OVOS de '4 PRODUTOS PRODUZIDOS'")
        with _col2:
            st.metric("Despesas (linhas)", len(_desp) if _desp is not None else 0)
            st.metric("Receita (linhas)", len(_rec) if _rec is not None else 0)
        st.caption(f"Pasta de dados: `{pasta}`")

    if _auth.is_admin():
        with _cfg_tabs[2]:
            st.subheader("🔬 Explorador do Banco Firebird")
            st.caption(
                "Consulta direta às tabelas de sistema do Firebird (RDB$) — "
                "mostra estrutura, tipos, relacionamentos e dados reais sem precisar de terminal."
            )
            from db import get_conn as _get_fb

            _diag_sub = st.tabs(["📋 Listar tabelas", "🏛️ Estrutura da tabela", "🔗 Relacionamentos", "🔍 Dados / status"])

            # ── 1. Listar tabelas ────────────────────────────────────────────
            with _diag_sub[0]:
                _prefixo = st.text_input("Filtrar pelo início do nome (deixe vazio para listar tudo)",
                                         value="FATNOTAF", key="diag_prefix")
                if st.button("🔍 Buscar tabelas", key="btn_list"):
                    try:
                        _conn = _get_fb(); _cur = _conn.cursor()
                        _like = f"{_prefixo.strip().upper()}%" if _prefixo.strip() else "%"
                        _cur.execute("""
                            SELECT TRIM(r.RDB$RELATION_NAME)   AS tabela,
                                   TRIM(r.RDB$DESCRIPTION)     AS descricao,
                                   COUNT(f.RDB$FIELD_NAME)     AS colunas,
                                   CASE WHEN r.RDB$VIEW_BLR IS NULL THEN 'Tabela' ELSE 'View' END AS tipo
                            FROM RDB$RELATIONS r
                            LEFT JOIN RDB$RELATION_FIELDS f ON f.RDB$RELATION_NAME = r.RDB$RELATION_NAME
                            WHERE r.RDB$SYSTEM_FLAG = 0
                              AND r.RDB$RELATION_NAME LIKE ?
                            GROUP BY r.RDB$RELATION_NAME, r.RDB$DESCRIPTION, r.RDB$VIEW_BLR
                            ORDER BY r.RDB$RELATION_NAME
                        """, (_like,))
                        _rows = _cur.fetchall()
                        _cur.close(); _conn.close()
                        if _rows:
                            _df_l = pd.DataFrame(_rows, columns=["Tabela", "Descrição", "Colunas", "Tipo"])
                            st.success(f"{len(_rows)} tabela(s)/view(s) encontrada(s)")
                            st.dataframe(_df_l, hide_index=True, use_container_width=True, height=400)
                        else:
                            st.warning("Nenhuma tabela encontrada com esse prefixo.")
                    except Exception as _e:
                        st.error(f"Erro: {_e}")

            # ── 2. Estrutura de uma tabela ───────────────────────────────────
            with _diag_sub[1]:
                _tbl = st.text_input("Nome exato da tabela", value="FATNOTAF01001", key="diag_tbl_struct")
                if st.button("📐 Ver estrutura", key="btn_struct"):
                    try:
                        _conn = _get_fb(); _cur = _conn.cursor()
                        _cur.execute("""
                            SELECT
                                TRIM(rf.RDB$FIELD_NAME)                        AS coluna,
                                CASE ft.RDB$FIELD_TYPE
                                    WHEN 7  THEN 'SMALLINT'
                                    WHEN 8  THEN 'INTEGER'
                                    WHEN 10 THEN 'FLOAT'
                                    WHEN 12 THEN 'DATE'
                                    WHEN 13 THEN 'TIME'
                                    WHEN 14 THEN 'CHAR(' || ft.RDB$FIELD_LENGTH || ')'
                                    WHEN 16 THEN CASE WHEN ft.RDB$FIELD_SUB_TYPE = 1 THEN 'NUMERIC(' || ft.RDB$FIELD_PRECISION || ',' || (-ft.RDB$FIELD_SCALE) || ')' ELSE 'BIGINT' END
                                    WHEN 27 THEN 'DOUBLE'
                                    WHEN 35 THEN 'TIMESTAMP'
                                    WHEN 37 THEN 'VARCHAR(' || ft.RDB$FIELD_LENGTH || ')'
                                    WHEN 261 THEN 'BLOB'
                                    ELSE 'TIPO_' || ft.RDB$FIELD_TYPE
                                END                                            AS tipo,
                                CASE rf.RDB$NULL_FLAG WHEN 1 THEN 'NÃO' ELSE 'SIM' END AS aceita_null,
                                TRIM(rf.RDB$DEFAULT_SOURCE)                    AS default_val,
                                TRIM(rf.RDB$DESCRIPTION)                       AS descricao
                            FROM RDB$RELATION_FIELDS rf
                            JOIN RDB$FIELDS ft ON ft.RDB$FIELD_NAME = rf.RDB$FIELD_SOURCE
                            WHERE rf.RDB$RELATION_NAME = ?
                            ORDER BY rf.RDB$FIELD_POSITION
                        """, (_tbl.strip().upper(),))
                        _rows = _cur.fetchall()
                        _cur.close(); _conn.close()
                        if _rows:
                            _df_st = pd.DataFrame(_rows, columns=["Coluna", "Tipo", "Aceita NULL", "Default", "Descrição"])
                            st.success(f"{len(_rows)} coluna(s) em `{_tbl.strip().upper()}`")
                            st.dataframe(_df_st, hide_index=True, use_container_width=True, height=500)
                        else:
                            st.warning("Tabela não encontrada ou sem colunas.")
                    except Exception as _e:
                        st.error(f"Erro: {_e}")

            # ── 3. Relacionamentos (FK) ──────────────────────────────────────
            with _diag_sub[2]:
                _tbl_fk = st.text_input("Nome da tabela", value="FATNOTAF01001", key="diag_tbl_fk")
                if st.button("🔗 Ver relacionamentos", key="btn_fk"):
                    try:
                        _conn = _get_fb(); _cur = _conn.cursor()
                        # FKs que SAEM desta tabela
                        _cur.execute("""
                            SELECT
                                TRIM(rc.RDB$CONSTRAINT_NAME)                  AS fk_nome,
                                TRIM(idx_seg.RDB$FIELD_NAME)                  AS coluna_origem,
                                TRIM(rc2.RDB$RELATION_NAME)                   AS tabela_destino,
                                TRIM(idx_seg2.RDB$FIELD_NAME)                 AS coluna_destino
                            FROM RDB$REF_CONSTRAINTS ref
                            JOIN RDB$RELATION_CONSTRAINTS rc  ON rc.RDB$CONSTRAINT_NAME  = ref.RDB$CONSTRAINT_NAME
                            JOIN RDB$RELATION_CONSTRAINTS rc2 ON rc2.RDB$CONSTRAINT_NAME = ref.RDB$CONST_NAME_UQ
                            JOIN RDB$INDEX_SEGMENTS idx_seg  ON idx_seg.RDB$INDEX_NAME  = rc.RDB$INDEX_NAME
                            JOIN RDB$INDEX_SEGMENTS idx_seg2 ON idx_seg2.RDB$INDEX_NAME = rc2.RDB$INDEX_NAME
                            WHERE rc.RDB$RELATION_NAME = ?
                            ORDER BY fk_nome
                        """, (_tbl_fk.strip().upper(),))
                        _fk_out = _cur.fetchall()

                        # FKs que CHEGAM nesta tabela
                        _cur.execute("""
                            SELECT
                                TRIM(rc.RDB$RELATION_NAME)                    AS tabela_origem,
                                TRIM(idx_seg.RDB$FIELD_NAME)                  AS coluna_origem,
                                TRIM(idx_seg2.RDB$FIELD_NAME)                 AS coluna_destino
                            FROM RDB$REF_CONSTRAINTS ref
                            JOIN RDB$RELATION_CONSTRAINTS rc  ON rc.RDB$CONSTRAINT_NAME  = ref.RDB$CONSTRAINT_NAME
                            JOIN RDB$RELATION_CONSTRAINTS rc2 ON rc2.RDB$CONSTRAINT_NAME = ref.RDB$CONST_NAME_UQ
                            JOIN RDB$INDEX_SEGMENTS idx_seg  ON idx_seg.RDB$INDEX_NAME  = rc.RDB$INDEX_NAME
                            JOIN RDB$INDEX_SEGMENTS idx_seg2 ON idx_seg2.RDB$INDEX_NAME = rc2.RDB$INDEX_NAME
                            WHERE rc2.RDB$RELATION_NAME = ?
                            ORDER BY tabela_origem
                        """, (_tbl_fk.strip().upper(),))
                        _fk_in = _cur.fetchall()
                        _cur.close(); _conn.close()

                        if _fk_out:
                            st.markdown(f"**Chaves estrangeiras que saem de `{_tbl_fk.strip().upper()}`:**")
                            _df_fo = pd.DataFrame(_fk_out, columns=["FK Nome", "Coluna aqui", "Tabela destino", "Coluna destino"])
                            st.dataframe(_df_fo, hide_index=True, use_container_width=True)
                        else:
                            st.info("Nenhuma FK saindo desta tabela.")

                        if _fk_in:
                            st.markdown(f"**Tabelas que referenciam `{_tbl_fk.strip().upper()}`:**")
                            _df_fi = pd.DataFrame(_fk_in, columns=["Tabela origem", "Coluna lá", "Coluna aqui"])
                            st.dataframe(_df_fi, hide_index=True, use_container_width=True)
                        else:
                            st.info("Nenhuma tabela referencia esta tabela.")
                    except Exception as _e:
                        st.error(f"Erro: {_e}")

            # ── 4. Dados / valores distintos ────────────────────────────────
            with _diag_sub[3]:
                _tbl_d = st.text_input("Nome da tabela", value="FATNOTAF01001", key="diag_tbl_data")
                _col_d = st.text_input("Coluna para ver valores distintos (ex: TIPONF, SITUACAO)",
                                       key="diag_col_data", placeholder="deixe vazio para ver amostra")
                if st.button("🔍 Consultar", key="btn_data"):
                    try:
                        _conn = _get_fb(); _cur = _conn.cursor()
                        _t = _tbl_d.strip().upper()
                        _c = _col_d.strip().upper()
                        if _c:
                            # Valores distintos + contagem
                            _cur.execute(f"SELECT {_c}, COUNT(*) FROM {_t} GROUP BY {_c} ORDER BY COUNT(*) DESC")
                            _rows = _cur.fetchall()
                            st.markdown(f"**Valores distintos de `{_c}` em `{_t}`:**")
                            _df_d = pd.DataFrame(_rows, columns=["Valor", "Registros"])
                            st.dataframe(_df_d, hide_index=True, use_container_width=True)
                        else:
                            # Amostra das primeiras 20 linhas
                            _cur.execute(f"SELECT FIRST 20 * FROM {_t}")
                            _cols_s = [d[0] for d in _cur.description]
                            _rows_s = _cur.fetchall()
                            st.markdown(f"**20 primeiros registros de `{_t}`:**")
                            st.dataframe(pd.DataFrame(_rows_s, columns=_cols_s),
                                         hide_index=True, use_container_width=True)
                        _cur.close(); _conn.close()
                    except Exception as _e:
                        st.error(f"Erro: {_e}")

# ---------------- Importar Dados ----------------
elif _modulo == "Importar Dados":
    _sub_imp = st.tabs(["🏦 Extratos OFX", "📄 Extratos PDF (histórico)", "🏗️ Imobilizado"])
    with _sub_imp[0]:
        if _OFX_DISPONIVEL:
            _OFX.render()
        else:
            st.warning("Módulo ofx_upload não disponível.")
    with _sub_imp[1]:
        if _PDF_DISPONIVEL:
            _PDF.render()
        else:
            st.warning("Módulo pdf_upload não disponível.")
    with _sub_imp[2]:
        if _IMOB_DISPONIVEL:
            _IMOB.render()
        else:
            st.warning("Módulo imob_upload não disponível.")

# ---------------- Usuários (só admin) ----------------
elif _modulo == "Usuários" and _auth.is_admin():
        st.subheader("👥 Gerenciar Usuários")
        st.caption("Somente a administradora (Sabrina) vê esta aba.")

        _usuarios = _auth.listar_usuarios(pasta)

        # --- Tabela de usuários existentes ---
        if _usuarios:
            st.markdown("#### Usuários cadastrados")
            _df_u = pd.DataFrame(_usuarios)
            _df_u.columns = ["Login", "Nome"]
            st.dataframe(_df_u, hide_index=True, use_container_width=True)
        else:
            st.info("Nenhum usuário cadastrado ainda (modo local sem senha).")

        st.divider()

        # --- Adicionar / Editar usuário ---
        st.markdown("#### ➕ Adicionar ou editar usuário")
        with st.form("form_add_user", clear_on_submit=True):
            _c1, _c2 = st.columns(2)
            _novo_login = _c1.text_input("Login (sem espaços)", placeholder="ex: joao.silva")
            _novo_nome  = _c2.text_input("Nome completo", placeholder="ex: João Silva")
            _c3, _c4 = st.columns(2)
            _nova_senha = _c3.text_input("Senha (mín. 6 caracteres)", type="password")
            _conf_senha = _c4.text_input("Confirmar senha", type="password")
            _submit_add = st.form_submit_button("💾 Salvar usuário", type="primary", use_container_width=True)

        if _submit_add:
            if _nova_senha != _conf_senha:
                st.error("As senhas não coincidem.")
            else:
                _err = _auth.adicionar_usuario(pasta, _novo_login, _novo_nome, _nova_senha)
                if _err:
                    st.error(_err)
                else:
                    _ja_existia = any(u["login"] == _novo_login.strip().lower() for u in _usuarios)
                    st.success(f"✅ Usuário **{_novo_login}** {'atualizado' if _ja_existia else 'cadastrado'} com sucesso!")
                    st.rerun()

        st.divider()

        # --- Remover usuário ---
        st.markdown("#### 🗑️ Remover usuário")
        _logins = [u["login"] for u in _usuarios if u["login"] != "sabrina"]
        if _logins:
            with st.form("form_del_user", clear_on_submit=True):
                _del_login = st.selectbox("Selecione o usuário para remover", _logins)
                _submit_del = st.form_submit_button("🗑️ Remover", type="secondary", use_container_width=True)
            if _submit_del:
                _err = _auth.remover_usuario(pasta, _del_login)
                if _err:
                    st.error(_err)
                else:
                    st.success(f"✅ Usuário **{_del_login}** removido.")
                    st.rerun()
        else:
            st.caption("Nenhum outro usuário para remover.")

        st.divider()

        # --- Alterar senha de qualquer usuário ---
        st.markdown("#### 🔑 Alterar senha")
        _todos_logins = [u["login"] for u in _usuarios]
        if _todos_logins:
            with st.form("form_senha_user", clear_on_submit=True):
                _s_login = st.selectbox("Usuário", _todos_logins, key="sel_troca_senha")
                _s1, _s2 = st.columns(2)
                _s_nova = _s1.text_input("Nova senha", type="password")
                _s_conf = _s2.text_input("Confirmar", type="password")
                _submit_senha = st.form_submit_button("🔑 Alterar senha", use_container_width=True)
            if _submit_senha:
                if _s_nova != _s_conf:
                    st.error("As senhas não coincidem.")
                else:
                    _err = _auth.alterar_senha(pasta, _s_login, _s_nova)
                    if _err:
                        st.error(_err)
                    else:
                        st.success(f"✅ Senha de **{_s_login}** alterada com sucesso!")
