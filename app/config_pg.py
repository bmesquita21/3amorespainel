# -*- coding: utf-8 -*-
"""Aba de configurações editáveis via PostgreSQL."""
import pandas as pd
import streamlit as st
import db_pg as PG


# ─── helpers ─────────────────────────────────────────────────────────────────

def _df(sql, params=None) -> pd.DataFrame:
    rows = PG.fetchall(sql, params)
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _salvar_contas(df_orig: pd.DataFrame, df_edit: pd.DataFrame):
    changed = df_edit[df_edit.ne(df_orig).any(axis=1)]
    if changed.empty:
        return 0
    for _, r in changed.iterrows():
        PG.execute(
            "UPDATE contas SET linha_dre=%s, natureza=%s, tipo_estoque=%s, ativo=%s, updated_at=NOW() WHERE id=%s",
            (r["linha_dre"], r["natureza"], r["tipo_estoque"], bool(r["ativo"]), int(r["id"]))
        )
    return len(changed)


def _salvar_ccs(df_orig: pd.DataFrame, df_edit: pd.DataFrame):
    changed = df_edit[df_edit.ne(df_orig).any(axis=1)]
    if changed.empty:
        return 0
    for _, r in changed.iterrows():
        PG.execute(
            "UPDATE centros_custo SET grupo=%s, subgrupo=%s, detalhe=%s, forca_capex=%s, ativo=%s, updated_at=NOW() WHERE id=%s",
            (r["grupo"], r["subgrupo"], r["detalhe"], r["forca_capex"], bool(r["ativo"]), int(r["id"]))
        )
    return len(changed)


def _salvar_fornecedores(df_orig: pd.DataFrame, df_edit: pd.DataFrame):
    changed = df_edit[df_edit.ne(df_orig).any(axis=1)]
    if changed.empty:
        return 0
    for _, r in changed.iterrows():
        PG.execute(
            "UPDATE fornecedores SET linha_dre=%s, natureza=%s, tipo_estoque=%s, observacao=%s, ativo=%s, updated_at=NOW() WHERE id=%s",
            (r["linha_dre"], r["natureza"], r["tipo_estoque"], r["observacao"], bool(r["ativo"]), int(r["id"]))
        )
    return len(changed)


def _salvar_produtos(df_orig: pd.DataFrame, df_edit: pd.DataFrame):
    changed = df_edit[df_edit.ne(df_orig).any(axis=1)]
    if changed.empty:
        return 0
    for _, r in changed.iterrows():
        PG.execute(
            "UPDATE produtos SET grupo=%s, cor=%s, tipo=%s, linha_id=%s, unidade=%s, marca=%s, ativo=%s, updated_at=NOW() WHERE id=%s",
            (r["grupo"], r["cor"], r["tipo"], r["linha_id"], r["unidade"], r["marca"], bool(r["ativo"]), int(r["id"]))
        )
    return len(changed)


def _add_conta(nome, linha, natureza, tipo):
    try:
        PG.execute(
            "INSERT INTO contas(nome_conta,linha_dre,natureza,tipo_estoque) VALUES(%s,%s,%s,%s)",
            (nome.strip().upper(), linha, natureza, tipo)
        )
        return None
    except Exception as e:
        return str(e)


def _add_fornecedor(credor, linha, natureza, tipo, obs):
    try:
        PG.execute(
            "INSERT INTO fornecedores(credor,linha_dre,natureza,tipo_estoque,observacao) VALUES(%s,%s,%s,%s,%s)",
            (credor.strip().upper(), linha, natureza, tipo, obs)
        )
        return None
    except Exception as e:
        return str(e)


# ─── UI principal ─────────────────────────────────────────────────────────────

_LINHAS_DRE = [
    "IGNORAR","CMV_MILHO","CMV_NUCLEO","CMV_EMBAL","CMV_ENERGIA","CMV_MANUT",
    "CMV_SAUDE","CMV_OUTROS","CMV_RECRIA","OPER_FOLHA","OPER_ENCARGOS",
    "OPER_PROLAB","OPER_GESTAO","OPER_ERP","OPER_FRETE","OPER_DIESEL",
    "OPER_GAS","OPER_LAVOURA","CAPEX_REFBENF","CAPEX_EQUIP","FIN_JUROS",
    "FIN_EMPREST","REAPROPRIAR",
]

_NATUREZAS = ["DESPESA_DIRETA","INVENTARIAVEL","CAPEX","IGNORAR"]
_TIPOS_EST = ["","RACAO","EMBALAGEM","ALMOXARIFADO"]


def render(pasta: str):
    pg_ok = PG.is_available()
    if not pg_ok:
        st.warning("PostgreSQL indisponível — edição de configurações desabilitada.")
        _render_somente_leitura(pasta)
        return

    sub = st.tabs(["📋 Contas", "🏢 Centros de Custo", "🏭 Fornecedores", "📦 Produtos"])

    # ── Contas ──────────────────────────────────────────────────────────────
    with sub[0]:
        st.caption("Mapeamento conta contábil → linha do DRE. Edite e clique **Salvar**.")
        df = _df("SELECT id,nome_conta,linha_dre,natureza,tipo_estoque,ativo FROM contas ORDER BY nome_conta")
        if df.empty:
            st.info("Nenhuma conta cadastrada.")
        else:
            key = "ed_contas"
            orig = df.copy()
            edited = st.data_editor(
                df,
                key=key,
                hide_index=True,
                use_container_width=True,
                height=400,
                disabled=["id","nome_conta"],
                column_config={
                    "id":          st.column_config.NumberColumn("ID", width="small"),
                    "nome_conta":  st.column_config.TextColumn("Conta", width="large"),
                    "linha_dre":   st.column_config.SelectboxColumn("Linha DRE", options=_LINHAS_DRE, width="medium"),
                    "natureza":    st.column_config.SelectboxColumn("Natureza", options=_NATUREZAS, width="medium"),
                    "tipo_estoque":st.column_config.SelectboxColumn("Tipo Estoque", options=_TIPOS_EST, width="medium"),
                    "ativo":       st.column_config.CheckboxColumn("Ativo", width="small"),
                },
            )
            if st.button("💾 Salvar contas", type="primary"):
                n = _salvar_contas(orig, edited)
                if n:
                    st.success(f"{n} linha(s) atualizada(s).")
                    st.cache_data.clear()
                else:
                    st.info("Nenhuma alteração detectada.")

        st.divider()
        st.markdown("#### ➕ Nova conta")
        with st.form("form_nova_conta", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            nome  = c1.text_input("Nome da conta (exato como no ERP)")
            linha = c2.selectbox("Linha DRE", _LINHAS_DRE)
            nat   = c3.selectbox("Natureza", _NATUREZAS)
            tipo  = c4.selectbox("Tipo Estoque", _TIPOS_EST)
            if st.form_submit_button("Adicionar", type="primary"):
                if nome.strip():
                    err = _add_conta(nome, linha, nat, tipo)
                    if err:
                        st.error(err)
                    else:
                        st.success(f"Conta '{nome.upper()}' adicionada!")
                        st.rerun()
                else:
                    st.warning("Digite o nome da conta.")

    # ── Centros de Custo ────────────────────────────────────────────────────
    with sub[1]:
        st.caption("Edite grupo, subgrupo e detalhe dos centros de custo.")
        df = _df("SELECT id,centro_custo,grupo,subgrupo,detalhe,forca_capex,ativo FROM centros_custo ORDER BY centro_custo")
        if df.empty:
            st.info("Nenhum CC cadastrado.")
        else:
            orig = df.copy()
            edited = st.data_editor(
                df,
                hide_index=True,
                use_container_width=True,
                height=400,
                disabled=["id","centro_custo"],
                column_config={
                    "id":           st.column_config.NumberColumn("ID", width="small"),
                    "centro_custo": st.column_config.TextColumn("Centro de Custo", width="large"),
                    "grupo":        st.column_config.TextColumn("Grupo", width="medium"),
                    "subgrupo":     st.column_config.TextColumn("Subgrupo", width="medium"),
                    "detalhe":      st.column_config.TextColumn("Detalhe", width="medium"),
                    "forca_capex":  st.column_config.SelectboxColumn("Força CAPEX", options=["N","S"], width="small"),
                    "ativo":        st.column_config.CheckboxColumn("Ativo", width="small"),
                },
            )
            if st.button("💾 Salvar centros de custo", type="primary"):
                n = _salvar_ccs(orig, edited)
                if n:
                    st.success(f"{n} linha(s) atualizada(s).")
                    st.cache_data.clear()
                else:
                    st.info("Nenhuma alteração detectada.")

    # ── Fornecedores ─────────────────────────────────────────────────────────
    with sub[2]:
        st.caption("Fallback: quando a NF não tem conta contábil no ERP, usa o fornecedor para classificar.")
        df = _df("SELECT id,credor,linha_dre,natureza,tipo_estoque,observacao,ativo FROM fornecedores ORDER BY credor")
        if df.empty:
            st.info("Nenhum fornecedor cadastrado.")
        else:
            orig = df.copy()
            edited = st.data_editor(
                df,
                hide_index=True,
                use_container_width=True,
                height=400,
                disabled=["id","credor"],
                column_config={
                    "id":           st.column_config.NumberColumn("ID", width="small"),
                    "credor":       st.column_config.TextColumn("Fornecedor", width="large"),
                    "linha_dre":    st.column_config.SelectboxColumn("Linha DRE", options=_LINHAS_DRE, width="medium"),
                    "natureza":     st.column_config.SelectboxColumn("Natureza", options=_NATUREZAS, width="medium"),
                    "tipo_estoque": st.column_config.SelectboxColumn("Tipo Estoque", options=_TIPOS_EST, width="medium"),
                    "observacao":   st.column_config.TextColumn("Observação", width="medium"),
                    "ativo":        st.column_config.CheckboxColumn("Ativo", width="small"),
                },
            )
            if st.button("💾 Salvar fornecedores", type="primary"):
                n = _salvar_fornecedores(orig, edited)
                if n:
                    st.success(f"{n} linha(s) atualizada(s).")
                    st.cache_data.clear()
                else:
                    st.info("Nenhuma alteração detectada.")

        st.divider()
        st.markdown("#### ➕ Novo fornecedor")
        with st.form("form_novo_forn", clear_on_submit=True):
            c1, c2 = st.columns(2)
            cred  = c1.text_input("Nome exato do fornecedor (como no ERP)")
            obs   = c2.text_input("Observação")
            c3, c4, c5 = st.columns(3)
            linha = c3.selectbox("Linha DRE", _LINHAS_DRE, key="forn_linha")
            nat   = c4.selectbox("Natureza", _NATUREZAS, key="forn_nat")
            tipo  = c5.selectbox("Tipo Estoque", _TIPOS_EST, key="forn_tipo")
            if st.form_submit_button("Adicionar", type="primary"):
                if cred.strip():
                    err = _add_fornecedor(cred, linha, nat, tipo, obs)
                    if err:
                        st.error(err)
                    else:
                        st.success(f"Fornecedor '{cred.upper()}' adicionado!")
                        st.rerun()
                else:
                    st.warning("Digite o nome do fornecedor.")

    # ── Produtos ─────────────────────────────────────────────────────────────
    with sub[3]:
        st.caption("Mapeamento produto de venda → linha de receita.")
        df = _df("SELECT id,produto_original,grupo,cor,tipo,linha_id,unidade,marca,ativo FROM produtos ORDER BY produto_original")
        if df.empty:
            st.info("Nenhum produto cadastrado.")
        else:
            orig = df.copy()
            edited = st.data_editor(
                df,
                hide_index=True,
                use_container_width=True,
                height=400,
                disabled=["id","produto_original"],
                column_config={
                    "id":               st.column_config.NumberColumn("ID", width="small"),
                    "produto_original": st.column_config.TextColumn("Produto", width="large"),
                    "grupo":            st.column_config.TextColumn("Grupo", width="medium"),
                    "cor":              st.column_config.TextColumn("Cor", width="small"),
                    "tipo":             st.column_config.TextColumn("Tipo", width="small"),
                    "linha_id":         st.column_config.TextColumn("Linha ID", width="medium"),
                    "unidade":          st.column_config.TextColumn("Unidade", width="medium"),
                    "marca":            st.column_config.TextColumn("Marca", width="small"),
                    "ativo":            st.column_config.CheckboxColumn("Ativo", width="small"),
                },
            )
            if st.button("💾 Salvar produtos", type="primary"):
                n = _salvar_produtos(orig, edited)
                if n:
                    st.success(f"{n} linha(s) atualizada(s).")
                    st.cache_data.clear()
                else:
                    st.info("Nenhuma alteração detectada.")


def _render_somente_leitura(pasta: str):
    import os
    cfgdir = os.path.join(pasta, "config")
    for fn in ["config_contas.csv","config_centros_custo.csv","config_fornecedores.csv","config_produtos.csv"]:
        fp = os.path.join(cfgdir, fn)
        if os.path.exists(fp):
            with st.expander(fn):
                try:
                    import pandas as pd
                    st.dataframe(pd.read_csv(fp, sep=";", encoding="utf-8-sig"), hide_index=True, height=280, use_container_width=True)
                except Exception as e:
                    st.write(f"(erro: {e})")
