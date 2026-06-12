# -*- coding: utf-8 -*-
"""Upload do Registro de Imobilizado (xlsx) → PostgreSQL."""
import io
import pandas as pd
import streamlit as st
import brutils as B


def _parse_imob_xlsx(raw: bytes) -> pd.DataFrame:
    """Lê Registro_Imobilizado.xlsx (aba 'Registro de Imobilizado', header linha 4)."""
    try:
        df = pd.read_excel(io.BytesIO(raw), sheet_name="Registro de Imobilizado", header=3, dtype=object)
    except Exception as e:
        raise ValueError(f"Erro ao abrir o Excel: {e}")

    rows = []
    for i in range(len(df)):
        aq  = B.parse_valor_br(df.iloc[i, 11])
        cod = df.iloc[i, 0]
        if aq <= 0:
            continue
        if pd.isna(cod) or str(cod).strip() == "" or "TOTAL" in str(df.iloc[i, 1]).upper():
            continue
        classe = str(df.iloc[i, 2])
        bloco  = str(df.iloc[i, 3])
        status = str(df.iloc[i, 10]).strip()
        is_bio = any(k in (classe + " " + bloco).upper() for k in ("BIOL", "PLANTEL", "AVES"))
        rows.append(dict(
            item            = str(df.iloc[i, 1]),
            classe          = classe,
            bloco           = bloco,
            acq             = B.parse_date(df.iloc[i, 8]),
            valor_aquisicao = aq,
            valor_pago      = B.parse_valor_br(df.iloc[i, 12]),
            saldo_a_pagar   = B.parse_valor_br(df.iloc[i, 13]),
            deprec_mensal   = B.parse_valor_br(df.iloc[i, 15]),
            valor_liquido   = B.parse_valor_br(df.iloc[i, 18]),
            status          = status,
            em_uso          = "USO" in status.upper(),
            is_bio          = is_bio,
        ))

    if not rows:
        raise ValueError(
            "Nenhum item com valor de aquisição encontrado. "
            "Verifique se a aba é **'Registro de Imobilizado'** e o cabeçalho está na **linha 4**."
        )
    return pd.DataFrame(rows)


def render():
    st.subheader("🏗️ Upload do Registro de Imobilizado")
    st.caption(
        "Faça upload do arquivo `Registro_Imobilizado_TresAmores.xlsx`. "
        "O sistema lerá a aba **Registro de Imobilizado** e substituirá os dados salvos no banco. "
        "A **recria (ativo biológico)** vem diretamente do Firebird — não é necessário fazer upload."
    )

    try:
        import db_pg as PG
        if not PG.is_available():
            st.error("⚠️ PostgreSQL indisponível. Verifique a conexão.")
            return
    except ImportError:
        st.error("Módulo db_pg não disponível.")
        return

    # ── Resumo do que já está no banco ──────────────────────────────────────
    try:
        resumo = PG.fetchall(
            "SELECT classe, COUNT(*) as n, SUM(valor_aquisicao) as total, "
            "SUM(saldo_a_pagar) as a_pagar, SUM(deprec_mensal) as deprec "
            "FROM imobilizado WHERE ativo=TRUE GROUP BY classe ORDER BY total DESC"
        )
        if resumo:
            st.markdown("#### Imobilizado atual no banco")
            df_res = pd.DataFrame(resumo)
            df_res.columns = ["Classe", "Itens", "Valor Aquisição", "A Pagar", "Deprec/mês"]
            for col in ("Valor Aquisição", "A Pagar", "Deprec/mês"):
                df_res[col] = df_res[col].map(lambda v: B.brl(float(v or 0)))
            st.dataframe(df_res, hide_index=True, use_container_width=True)
            st.divider()
    except Exception:
        pass

    # ── Upload ───────────────────────────────────────────────────────────────
    uploaded = st.file_uploader(
        "Selecione o arquivo Excel do imobilizado",
        type=["xlsx"],
        help="Arquivo com aba 'Registro de Imobilizado' e cabeçalho na linha 4 (padrão do ERP Auditor).",
    )

    if not uploaded:
        st.info("☝️ Selecione o arquivo Excel para importar.")
        return

    try:
        df = _parse_imob_xlsx(uploaded.read())
    except ValueError as e:
        st.error(str(e))
        return

    # ── Métricas do preview ──────────────────────────────────────────────────
    bio  = df[df.is_bio]
    oper = df[~df.is_bio]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total de itens", len(df))
    c2.metric("Ativo operacional", B.brl_compact(float(oper.valor_aquisicao.sum())))
    c3.metric("Ativo biológico", B.brl_compact(float(bio.valor_aquisicao.sum())))
    c4.metric("Saldo a pagar", B.brl_compact(float(df.saldo_a_pagar.sum())))

    # ── Preview ──────────────────────────────────────────────────────────────
    df_show = df[["item", "classe", "bloco", "acq", "valor_aquisicao", "saldo_a_pagar", "deprec_mensal", "em_uso", "is_bio"]].copy()
    df_show["valor_aquisicao"] = df_show["valor_aquisicao"].map(B.brl)
    df_show["saldo_a_pagar"]   = df_show["saldo_a_pagar"].map(B.brl)
    df_show["deprec_mensal"]   = df_show["deprec_mensal"].map(B.brl)
    df_show["acq"]             = df_show["acq"].astype(str)
    df_show.columns = ["Item", "Classe", "Bloco", "Aquisição", "Valor Aq.", "Saldo p/", "Deprec/mês", "Em uso", "Biológico"]

    st.markdown(f"#### Preview — {len(df)} item(ns)")
    st.dataframe(df_show, hide_index=True, use_container_width=True, height=360)

    # ── Salvar ───────────────────────────────────────────────────────────────
    st.warning("⚠️ **Salvar substituirá** todo o imobilizado atual no banco com os dados deste arquivo.")
    if st.button("💾 Salvar no banco de dados", type="primary", use_container_width=True):
        try:
            PG.replace_imobilizado(df.to_dict("records"))
            st.success(f"✅ {len(df)} item(ns) salvos. Clique em **🔄 Atualizar dados** para refletir no painel.")
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")
