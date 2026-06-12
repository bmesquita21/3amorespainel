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

    sub = st.tabs(["📋 Contas", "🏢 Centros de Custo", "🏭 Fornecedores", "📦 Produtos", "🥚 Composição", "🐔 Lotes"])

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


    # ── Composição ───────────────────────────────────────────────────────────
    with sub[4]:
        st.caption("Custo de embalagem e quantidade de ovos por caixa — usado no cálculo do CMV embalagem.")
        df = _df("SELECT id,produto_norm,produto_original,ovos_por_caixa,emb_por_caixa,total_por_caixa,unidade,ativo FROM config_composicao ORDER BY produto_norm")
        if df.empty:
            st.info("Nenhuma composição cadastrada.")
        else:
            orig = df.copy()
            edited = st.data_editor(
                df, hide_index=True, use_container_width=True, height=380,
                disabled=["id", "produto_norm"],
                column_config={
                    "id":               st.column_config.NumberColumn("ID", width="small"),
                    "produto_norm":     st.column_config.TextColumn("Produto (chave)", width="large"),
                    "produto_original": st.column_config.TextColumn("Descrição original", width="large"),
                    "ovos_por_caixa":   st.column_config.NumberColumn("Ovos/caixa", min_value=0, format="%.0f"),
                    "emb_por_caixa":    st.column_config.NumberColumn("Emb. R$/caixa", min_value=0, format="%.4f"),
                    "total_por_caixa":  st.column_config.NumberColumn("Total R$/caixa", min_value=0, format="%.4f"),
                    "unidade":          st.column_config.TextColumn("Unidade", width="medium"),
                    "ativo":            st.column_config.CheckboxColumn("Ativo", width="small"),
                },
            )
            if st.button("💾 Salvar composição", type="primary"):
                changed = edited[edited.ne(orig).any(axis=1)]
                if changed.empty:
                    st.info("Nenhuma alteração detectada.")
                else:
                    for _, r in changed.iterrows():
                        PG.execute(
                            "UPDATE config_composicao SET produto_original=%s,ovos_por_caixa=%s,emb_por_caixa=%s,"
                            "total_por_caixa=%s,unidade=%s,ativo=%s,updated_at=NOW() WHERE id=%s",
                            (r["produto_original"], float(r["ovos_por_caixa"]), float(r["emb_por_caixa"]),
                             float(r["total_por_caixa"]), r["unidade"], bool(r["ativo"]), int(r["id"]))
                        )
                    st.success(f"{len(changed)} linha(s) atualizada(s).")
                    st.cache_data.clear()
        st.divider()
        st.markdown("#### ➕ Nova composição")
        with st.form("form_nova_comp", clear_on_submit=True):
            c1, c2 = st.columns(2)
            pnorm = c1.text_input("Produto (chave normalizada)", placeholder="EX: CX OVOS CAIPIRA TIPO GRANDE 12 CRIVO DE 20 TRES AMORES")
            porig = c2.text_input("Descrição original")
            c3, c4, c5, c6 = st.columns(4)
            ovos  = c3.number_input("Ovos/caixa", min_value=0, value=240, step=1)
            emb   = c4.number_input("Emb. R$/caixa", min_value=0.0, value=0.0, format="%.4f")
            tot   = c5.number_input("Total R$/caixa", min_value=0.0, value=0.0, format="%.4f")
            uni   = c6.selectbox("Unidade", ["Fazenda", "Silveira", ""])
            if st.form_submit_button("Adicionar", type="primary"):
                if pnorm.strip():
                    try:
                        PG.execute(
                            "INSERT INTO config_composicao(produto_norm,produto_original,ovos_por_caixa,emb_por_caixa,total_por_caixa,unidade) "
                            "VALUES(%s,%s,%s,%s,%s,%s)",
                            (pnorm.strip().upper(), porig.strip(), ovos, emb, tot, uni)
                        )
                        st.success(f"Composição '{pnorm.upper()}' adicionada!")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
                else:
                    st.warning("Preencha a chave do produto.")

    # ── Lotes ─────────────────────────────────────────────────────────────────
    with sub[5]:
        st.caption("Lotes do plantel de poedeiras — controla a amortização do ativo biológico.")
        df = _df("SELECT id,lote_id,fonte_recria,data_entrada_recria,data_inicio_postura,galpao_postura,grupo_galpao,n_aves,ciclo_postura_meses,metodo_amortizacao,ativo FROM config_lotes ORDER BY lote_id")
        if df.empty:
            st.info("Nenhum lote cadastrado.")
        else:
            orig = df.copy()
            edited = st.data_editor(
                df, hide_index=True, use_container_width=True, height=200,
                disabled=["id", "lote_id"],
                column_config={
                    "id":                   st.column_config.NumberColumn("ID", width="small"),
                    "lote_id":              st.column_config.TextColumn("Lote ID", width="small"),
                    "fonte_recria":         st.column_config.TextColumn("Fonte recria", width="medium"),
                    "data_entrada_recria":  st.column_config.TextColumn("Entrada recria (AAAA-MM)", width="medium"),
                    "data_inicio_postura":  st.column_config.TextColumn("Início postura (AAAA-MM)", width="medium"),
                    "galpao_postura":       st.column_config.TextColumn("Galpão postura", width="small"),
                    "grupo_galpao":         st.column_config.TextColumn("Grupo galpão", width="medium"),
                    "n_aves":               st.column_config.NumberColumn("Nº aves", min_value=0),
                    "ciclo_postura_meses":  st.column_config.NumberColumn("Ciclo (meses)", min_value=1, max_value=36),
                    "metodo_amortizacao":   st.column_config.SelectboxColumn("Método", options=["LINEAR"], width="small"),
                    "ativo":                st.column_config.CheckboxColumn("Ativo", width="small"),
                },
            )
            if st.button("💾 Salvar lotes", type="primary"):
                changed = edited[edited.ne(orig).any(axis=1)]
                if changed.empty:
                    st.info("Nenhuma alteração detectada.")
                else:
                    for _, r in changed.iterrows():
                        PG.execute(
                            "UPDATE config_lotes SET fonte_recria=%s,data_entrada_recria=%s,data_inicio_postura=%s,"
                            "galpao_postura=%s,grupo_galpao=%s,n_aves=%s,ciclo_postura_meses=%s,"
                            "metodo_amortizacao=%s,ativo=%s,updated_at=NOW() WHERE id=%s",
                            (r["fonte_recria"], r["data_entrada_recria"], r["data_inicio_postura"],
                             r["galpao_postura"], r["grupo_galpao"], int(r["n_aves"]),
                             int(r["ciclo_postura_meses"]), r["metodo_amortizacao"],
                             bool(r["ativo"]), int(r["id"]))
                        )
                    st.success(f"{len(changed)} lote(s) atualizado(s).")
                    st.cache_data.clear()


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
