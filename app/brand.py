# -*- coding: utf-8 -*-
"""Identidade visual Três Amores — injeta CSS + componentes de marca no Streamlit."""
import streamlit as st

# ── Paleta oficial (Key Visual V3) ───────────────────────────────────────────
LARANJA  = "#ef7736"   # cor primária
AMARELO  = "#fdc438"   # secundária
VERDE    = "#5ab046"   # campo / positivo
CREME    = "#e5dfcc"   # fundo suave
MARROM   = "#5c3d1e"   # texto escuro / contraste
BRANCO   = "#ffffff"
CINZA_BG = "#f7f4ef"   # fundo geral (derivado do creme)

CSS = f"""
<style>
/* ── Fundo geral ─────────────────────────────────────────────────── */
.stApp {{
    background-color: {CINZA_BG};
}}

/* ── Barra lateral ───────────────────────────────────────────────── */
[data-testid="stSidebar"] {{
    background: linear-gradient(160deg, {MARROM} 0%, #3a2510 100%);
}}
[data-testid="stSidebar"] * {{
    color: {CREME} !important;
}}
[data-testid="stSidebar"] .stButton > button {{
    background-color: {LARANJA} !important;
    color: {BRANCO} !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
    background-color: {AMARELO} !important;
    color: {MARROM} !important;
}}
[data-testid="stSidebar"] .stCheckbox label {{
    color: {CREME} !important;
}}

/* ── Abas (tabs) ─────────────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {{
    background-color: {BRANCO};
    border-bottom: 3px solid {LARANJA};
    border-radius: 8px 8px 0 0;
    gap: 2px;
}}
[data-testid="stTabs"] [data-baseweb="tab"] {{
    color: {MARROM} !important;
    font-weight: 500;
    border-radius: 6px 6px 0 0;
    padding: 8px 16px;
}}
[data-testid="stTabs"] [aria-selected="true"] {{
    background-color: {LARANJA} !important;
    color: {BRANCO} !important;
    font-weight: 700 !important;
}}

/* ── Botões primários ────────────────────────────────────────────── */
.stButton > button[kind="primary"],
.stButton > button {{
    background-color: {LARANJA} !important;
    color: {BRANCO} !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: background 0.2s;
}}
.stButton > button:hover {{
    background-color: {AMARELO} !important;
    color: {MARROM} !important;
}}

/* ── Métricas ────────────────────────────────────────────────────── */
[data-testid="metric-container"] {{
    background: {BRANCO};
    border: 1px solid #e0d8cc;
    border-left: 5px solid {LARANJA};
    border-radius: 10px;
    padding: 14px 18px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.07);
}}
[data-testid="metric-container"] [data-testid="stMetricLabel"] {{
    color: {MARROM} !important;
    font-weight: 600;
    font-size: 0.82rem;
}}
[data-testid="metric-container"] [data-testid="stMetricValue"] {{
    color: {LARANJA} !important;
    font-weight: 700;
}}

/* ── Cabeçalhos ──────────────────────────────────────────────────── */
h1, h2, h3 {{
    color: {MARROM} !important;
}}
h2 {{
    border-bottom: 3px solid {LARANJA};
    padding-bottom: 6px;
}}

/* ── Filtro de período (radio) ────────────────────────────────────── */
[data-testid="stRadio"] label {{
    font-weight: 500;
    color: {MARROM};
}}

/* ── Inputs de texto ─────────────────────────────────────────────── */
input[type="text"], input[type="password"] {{
    border: 1.5px solid {LARANJA} !important;
    border-radius: 8px !important;
}}

/* ── Scrollbar ───────────────────────────────────────────────────── */
::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: {CREME}; }}
::-webkit-scrollbar-thumb {{ background: {LARANJA}; border-radius: 3px; }}
</style>
"""

LOGIN_CSS = f"""
<style>
/* Fundo creme claro */
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
    background: #fdf6ee !important;
}}
[data-testid="stHeader"] {{ display: none; }}
/* Centraliza verticalmente */
[data-testid="stAppViewContainer"] {{
    display: flex; align-items: center; justify-content: center;
    min-height: 100vh;
}}
/* Rótulos */
label, p, .stMarkdown p {{
    color: {MARROM} !important;
    font-weight: 600;
}}
/* Inputs */
input[type="text"], input[type="password"] {{
    border: 1.5px solid #d4a87a !important;
    border-radius: 8px !important;
    background: {BRANCO} !important;
    font-size: 1rem !important;
}}
input:focus {{
    border-color: {LARANJA} !important;
    box-shadow: 0 0 0 3px rgba(239,119,54,0.18) !important;
    outline: none !important;
}}
/* Botão Entrar */
.stButton > button {{
    background: {LARANJA} !important;
    color: {BRANCO} !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 1.05rem !important;
    letter-spacing: 0.5px;
    transition: background 0.2s;
}}
.stButton > button:hover {{
    background: {AMARELO} !important;
    color: {MARROM} !important;
}}
/* Alerta de erro */
[data-testid="stAlert"] {{
    border-radius: 10px !important;
}}
</style>
"""

LOGO_HTML = f"""
<div style="text-align:center; margin-bottom:8px;">
  <div style="display:inline-block; background:{LARANJA}; border-radius:50%;
              width:64px; height:64px; line-height:64px; font-size:36px;
              box-shadow:0 4px 12px rgba(239,119,54,0.4);">🥚</div>
  <div style="font-size:1.5rem; font-weight:800; color:{MARROM}; margin-top:6px;
              letter-spacing:0.5px;">TRES AMORES AGRONEGÓCIO</div>
  <div style="font-size:0.78rem; color:#888; letter-spacing:2px; text-transform:uppercase;">
    Painel Financeiro</div>
</div>
"""

def aplicar(login=False):
    """Injeta o CSS de marca. Chamar logo após set_page_config."""
    st.markdown(LOGIN_CSS if login else CSS, unsafe_allow_html=True)

def logo():
    """Renderiza o logo/título da marca."""
    st.markdown(LOGO_HTML, unsafe_allow_html=True)
