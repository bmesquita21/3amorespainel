# -*- coding: utf-8 -*-
"""Upload de extratos bancários em PDF → PostgreSQL.

Usa o parser já existente em extrato.py para extrair transações e saldo
de fechamento, depois salva nas mesmas tabelas usadas pelo fluxo OFX
(extrato_txs e extrato_saldos).
"""
import io
import pandas as pd
import streamlit as st


def _parse_pdf_bytes(raw: bytes, filename: str) -> tuple:
    """Parseia bytes de um PDF de extrato.
    Retorna (banco, conta, titular, txs: list[dict], saldo_fim, dtasof).
    """
    import pdfplumber
    from extrato import _banco, _parse, _parse_tx, CONTA2TIT, _tid

    try:
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            txt = "\n".join((p.extract_text() or "") for p in pdf.pages)
    except Exception as e:
        raise ValueError(f"Erro ao abrir PDF: {e}")

    banco  = _banco(filename, txt)
    parsed = _parse(txt, banco)
    conta  = parsed["conta"]

    bt = CONTA2TIT.get(conta)
    if bt:
        banco, titular = bt
    else:
        import re
        titular = "Filial" if re.search(r"\bF(ILIAL)?\b", filename.upper()) else "Matriz"

    R = _parse_tx(txt, banco)

    txs = []
    for t in R["tx"]:
        data_str = t["data"]          # "DD/MM/YYYY"
        valor    = float(t["valor"])
        fitid    = _tid(banco, conta, data_str, valor)

        # converte data para datetime.date
        try:
            d, m, a = data_str.split("/")
            import datetime
            data_date = datetime.date(int(a), int(m), int(d))
        except Exception:
            continue

        periodo = f"{data_date.year}-{data_date.month:02d}"
        txs.append({
            "banco":        banco,
            "conta":        conta,
            "data_tx":      data_date,
            "valor":        valor,
            "descricao":    t["desc"][:500] if t["desc"] else "",
            "fitid":        fitid,
            "periodo":      periodo,
            "categoria":    "",
            "classificado": "pendente",
        })

    # saldo de fechamento: usa fech_detectado (cadeia) se disponível
    saldo_fim = R.get("fechamento")
    dtasof    = None
    if saldo_fim is not None and txs:
        # data do último lançamento como referência do saldo
        dtasof = max(t["data_tx"] for t in txs)

    return banco, conta, titular, txs, saldo_fim, dtasof


def render():
    st.subheader("📄 Upload de Extratos em PDF")
    st.caption(
        "Importe extratos bancários em PDF (Bradesco, Santander, BB). "
        "As transações são extraídas e salvas no PostgreSQL na mesma tabela dos OFX. "
        "Use esta opção para importar extratos históricos. "
        "Para novos extratos, prefira o formato **OFX** (mais preciso)."
    )

    try:
        import db_pg as PG
        if not PG.is_available():
            st.error("⚠️ PostgreSQL indisponível.")
            return
    except ImportError:
        st.error("Módulo db_pg não disponível.")
        return

    # ── Resumo atual ─────────────────────────────────────────────────────────
    try:
        resumo = PG.fetchall(
            "SELECT banco, conta, COUNT(*) as n, MIN(data_tx) as de, MAX(data_tx) as ate "
            "FROM extrato_txs GROUP BY banco, conta ORDER BY banco, conta"
        )
        if resumo:
            st.markdown("#### Extratos já no banco")
            df_res = pd.DataFrame(resumo)
            df_res.columns = ["Banco", "Conta", "Transações", "De", "Até"]
            st.dataframe(df_res, hide_index=True, use_container_width=True)
            st.divider()
    except Exception:
        pass

    # ── Upload ───────────────────────────────────────────────────────────────
    uploaded = st.file_uploader(
        "Selecione um ou mais PDFs de extrato",
        accept_multiple_files=True,
        type=["pdf"],
        help="Extratos em PDF exportados pelo internet banking (Bradesco, Santander, BB).",
    )

    if not uploaded:
        st.info("☝️ Selecione os arquivos PDF acima.")
        return

    all_txs    = []
    saldos_pdf = []
    erros      = []

    for f in uploaded:
        try:
            banco, conta, titular, txs, saldo_fim, dtasof = _parse_pdf_bytes(f.read(), f.name)
        except Exception as e:
            erros.append(f"**{f.name}**: {e}")
            continue

        if not txs:
            erros.append(f"**{f.name}**: nenhuma transação extraída — verifique se é um extrato válido.")
            continue

        for t in txs:
            t["_arquivo"] = f.name
        all_txs.extend(txs)

        if saldo_fim is not None and dtasof is not None:
            periodo_s = f"{dtasof.year}-{dtasof.month:02d}"
            saldos_pdf.append((banco, conta, periodo_s, saldo_fim, dtasof))

        st.success(
            f"✅ **{f.name}** — {len(txs)} transações · "
            f"**{banco}** / {titular} ({conta})"
            + (f" · Saldo fechamento: **R$ {saldo_fim:,.2f}**"
               .replace(",","X").replace(".",",").replace("X",".") if saldo_fim is not None else "")
        )

    for msg in erros:
        st.error(msg)

    if not all_txs:
        return

    # ── Preview ──────────────────────────────────────────────────────────────
    df_prev = pd.DataFrame(all_txs)
    pos = df_prev[df_prev.valor > 0].valor.sum()
    neg = df_prev[df_prev.valor < 0].valor.sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("Transações",  len(all_txs))
    c2.metric("Entradas",    f"R$ {pos:,.2f}".replace(",","X").replace(".",",").replace("X","."))
    c3.metric("Saídas",      f"R$ {abs(neg):,.2f}".replace(",","X").replace(".",",").replace("X","."))

    df_show = df_prev[["banco","conta","data_tx","valor","descricao","_arquivo"]].copy()
    df_show["data_tx"] = df_show["data_tx"].astype(str)
    df_show["valor"]   = df_show["valor"].map(
        lambda v: f"R$ {v:,.2f}".replace(",","X").replace(".",",").replace("X",".")
    )
    df_show.columns = ["Banco","Conta","Data","Valor","Histórico","Arquivo"]
    st.markdown(f"#### Preview — {len(all_txs)} transação(ões)")
    st.dataframe(df_show, hide_index=True, use_container_width=True, height=350)

    # ── Salvar ───────────────────────────────────────────────────────────────
    st.warning(
        "ℹ️ Transações duplicadas (mesmo banco + mesmo hash data/valor) são ignoradas automaticamente."
    )
    if st.button("💾 Salvar no banco de dados", type="primary", use_container_width=True):
        rows_pg = [{k: v for k, v in t.items() if k != "_arquivo"} for t in all_txs]
        inseridas, ignoradas = PG.insert_extrato_batch(rows_pg)
        for banco, conta, periodo, saldo_fim, dtasof in saldos_pdf:
            PG.upsert_extrato_saldo(banco, conta, periodo, saldo_fim, dtasof)
        msg = f"✅ {inseridas} transação(ões) salvas"
        if ignoradas:
            msg += f" · {ignoradas} já existiam"
        if saldos_pdf:
            msg += f" · {len(saldos_pdf)} saldo(s) de fechamento registrado(s)"
        st.success(msg + ".")
        st.cache_data.clear()
        st.rerun()
