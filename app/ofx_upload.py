# -*- coding: utf-8 -*-
"""Upload de extratos OFX → PostgreSQL.

Suporta o formato SGML (OFX 1.x) usado por Bradesco, Santander e BB.
"""
import re
import datetime
import pandas as pd
import streamlit as st


# ─── Parser OFX ──────────────────────────────────────────────────────────────

def _tag(text: str, name: str) -> str:
    """Extrai o valor de uma tag OFX (SGML ou XML), sem fechar tag obrigatória."""
    m = re.search(rf'<{name}>(.*?)(?:\n|</{name}>|<[A-Z/])', text, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""


def parse_ofx(raw: bytes) -> tuple:
    """Parseia bytes de um arquivo OFX.
    Retorna (banco: str, conta: str, txs: list[dict]).
    """
    try:
        text = raw.decode("latin-1")
    except Exception:
        text = raw.decode("utf-8", errors="replace")

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Banco: tenta <ORG> direto ou dentro de <FI>
    banco = ""
    for pat in [r'<FI>.*?<ORG>(.*?)[\n<]', r'<ORG>(.*?)[\n<]']:
        m = re.search(pat, text, re.DOTALL | re.IGNORECASE)
        if m:
            banco = m.group(1).strip()
            break

    # Conta
    conta = ""
    m = re.search(r'<ACCTID>(.*?)[\n<]', text, re.IGNORECASE)
    if m:
        conta = m.group(1).strip()

    txs = []
    for bloco in re.finditer(r'<STMTTRN>(.*?)</STMTTRN>', text, re.DOTALL | re.IGNORECASE):
        b = bloco.group(1)
        fitid    = _tag(b, "FITID")
        dtposted = _tag(b, "DTPOSTED")
        trnamt   = _tag(b, "TRNAMT")
        memo     = _tag(b, "MEMO") or _tag(b, "NAME")

        if not fitid or not dtposted or not trnamt:
            continue

        # Data: YYYYMMDD[HH...] [timezone]
        try:
            data = datetime.date(int(dtposted[:4]), int(dtposted[4:6]), int(dtposted[6:8]))
        except Exception:
            continue

        try:
            valor = float(trnamt.replace(",", "."))
        except Exception:
            continue

        txs.append({
            "banco":       banco,
            "conta":       conta,
            "data_tx":     data,
            "valor":       valor,
            "descricao":   memo[:500] if memo else "",
            "fitid":       fitid,
            "periodo":     f"{data.year}-{data.month:02d}",
            "categoria":   "",
            "classificado": "pendente",
        })

    # Saldo de fechamento (LEDGERBAL) — presente na maioria dos OFX
    saldo_fim = None
    dtasof    = None
    m = re.search(r'<LEDGERBAL>(.*?)(?:</LEDGERBAL>|<[A-Z])', text, re.DOTALL | re.IGNORECASE)
    if m:
        bloco_bal = m.group(1)
        amt = _tag(bloco_bal, "BALAMT")
        dta = _tag(bloco_bal, "DTASOF")
        try:
            saldo_fim = float(amt.replace(",", "."))
        except Exception:
            pass
        try:
            dtasof = datetime.date(int(dta[:4]), int(dta[4:6]), int(dta[6:8]))
        except Exception:
            pass

    return banco, conta, txs, saldo_fim, dtasof


# ─── UI Streamlit ─────────────────────────────────────────────────────────────

def render():
    st.subheader("📤 Upload de Extratos OFX")
    st.caption(
        "Importe extratos bancários no formato OFX (Bradesco, Santander, BB). "
        "Os dados são salvos no PostgreSQL e ficam disponíveis na aba 🧾 Extrato/Reconciliação. "
        "Duplicatas são ignoradas automaticamente pelo FITID."
    )

    try:
        import db_pg as PG
        if not PG.is_available():
            st.error("⚠️ PostgreSQL indisponível. Verifique a conexão para usar o upload OFX.")
            return
    except ImportError:
        st.error("Módulo db_pg não disponível.")
        return

    # ── Resumo do que já está no PG ──────────────────────────────────────────
    try:
        resumo = PG.fetchall(
            "SELECT banco, conta, COUNT(*) as n, MIN(data_tx) as de, MAX(data_tx) as ate "
            "FROM extrato_txs GROUP BY banco, conta ORDER BY banco, conta"
        )
        if resumo:
            st.markdown("#### Extratos já importados")
            df_res = pd.DataFrame(resumo)
            df_res.columns = ["Banco", "Conta", "Transações", "De", "Até"]
            st.dataframe(df_res, hide_index=True, use_container_width=True)
            st.divider()
    except Exception as e:
        st.caption(f"(não foi possível consultar extratos existentes: {e})")

    # ── Upload ───────────────────────────────────────────────────────────────
    uploaded = st.file_uploader(
        "Selecione um ou mais arquivos OFX",
        accept_multiple_files=True,
        type=["ofx", "OFX"],
        help=(
            "Arquivos exportados pelo internet banking do banco. "
            "Bradesco: Extrato → Exportar → OFX. "
            "Santander: Extrato de conta → Exportar → Microsoft Money (OFX). "
            "BB: Extrato → Exportar OFX."
        ),
    )

    if not uploaded:
        st.info("☝️ Selecione um ou mais arquivos OFX acima para importar.")
        return

    all_txs    = []
    saldos_ofx = []   # (banco, conta, periodo, saldo_fim, dtasof)
    for f in uploaded:
        banco, conta, txs, saldo_fim, dtasof = parse_ofx(f.read())
        if not txs:
            st.warning(f"⚠️ **{f.name}**: nenhuma transação encontrada. Verifique se é um OFX válido.")
            continue
        for t in txs:
            t["_arquivo"] = f.name
        all_txs.extend(txs)
        if saldo_fim is not None and dtasof is not None:
            periodo_saldo = f"{dtasof.year}-{dtasof.month:02d}"
            saldos_ofx.append((banco, conta, periodo_saldo, saldo_fim, dtasof))
        st.success(f"✅ **{f.name}** — {len(txs)} transações · Banco: **{banco or '(não identificado)'}** · Conta: **{conta or '(não identificada)'}**"
                   + (f" · Saldo: **R$ {saldo_fim:,.2f}**".replace(",","X").replace(".",",").replace("X",".") if saldo_fim is not None else ""))

    if not all_txs:
        return

    # ── Preview ──────────────────────────────────────────────────────────────
    df_prev = pd.DataFrame(all_txs)
    df_show = df_prev[["banco", "conta", "data_tx", "valor", "descricao", "fitid", "_arquivo"]].copy()
    df_show["data_tx"] = df_show["data_tx"].astype(str)
    df_show["valor"]   = df_show["valor"].map(lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    df_show.columns    = ["Banco", "Conta", "Data", "Valor", "Histórico", "FITID", "Arquivo"]

    pos = df_prev[df_prev["valor"] > 0]["valor"].sum()
    neg = df_prev[df_prev["valor"] < 0]["valor"].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("Transações", len(all_txs))
    c2.metric("Entradas",   f"R$ {pos:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c3.metric("Saídas",     f"R$ {abs(neg):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    st.markdown(f"#### Preview — {len(all_txs)} transação(ões)")
    st.dataframe(df_show, hide_index=True, use_container_width=True, height=350)

    # ── Salvar ───────────────────────────────────────────────────────────────
    if st.button("💾 Salvar no banco de dados", type="primary", use_container_width=True):
        rows_pg = [{k: v for k, v in t.items() if k != "_arquivo"} for t in all_txs]
        inseridas, ignoradas = PG.insert_extrato_batch(rows_pg)
        for banco, conta, periodo, saldo_fim, dtasof in saldos_ofx:
            PG.upsert_extrato_saldo(banco, conta, periodo, saldo_fim, dtasof)
        msg = f"✅ {inseridas} transação(ões) salvas"
        if ignoradas:
            msg += f" · {ignoradas} já existiam (FITID duplicado)"
        if saldos_ofx:
            msg += f" · {len(saldos_ofx)} saldo(s) de fechamento registrado(s)"
        st.success(msg + ".")
        st.cache_data.clear()
        st.rerun()
