# -*- coding: utf-8 -*-
"""Ingestão robusta por fonte. Varre a pasta, deduplica por conteúdo, classifica o destino
de cada lançamento (DRE / CAPEX / ESTOQUE / IGNORADO / REAPROPRIAR)."""
import os, glob, unicodedata
import pandas as pd
import brutils as B

DESP_DIR = "2.2 DRE - DESEMBOLSO POR DATA DE ENTRADA"
REC_DIR  = "2.1 DRE - FATURAMENTO POR DATA DE EMISSÃO"
PROD_DIR = "4 PRODUTOS PRODUZIDOS - MOVIMENTAÇÃO DE ESTOQUE"
IMOB_FP  = os.path.join("3 LEVANTAMENTO DE ATIVOS", "ATIVOS", "Registro_Imobilizado_TresAmores.xlsx")

def _norm(s):
    """Remove acentos e converte para maiúsculas — para comparação de nomes de pasta."""
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().upper()

def _find_dir(base, target):
    """Localiza subpasta cujo nome normalizado começa com o prefixo normalizado de `target`."""
    exact = os.path.join(base, target)
    if os.path.isdir(exact):
        return exact
    prefix = _norm(target[:20])  # primeiros 20 chars são suficientes para distinguir
    try:
        for entry in os.scandir(base):
            if entry.is_dir() and _norm(entry.name).startswith(prefix):
                return entry.path
    except OSError:
        pass
    return exact  # retorna o caminho original mesmo que não exista (mensagem de erro clara)

def _read(path):
    ext = os.path.splitext(path)[1].lower()
    eng = "xlrd" if ext == ".xls" else "openpyxl"
    try: return pd.read_excel(path, header=0, dtype=object, engine=eng)
    except Exception: return pd.read_excel(path, header=0, dtype=object)

def _files(folder, exts):
    """Lista arquivos com as extensões dadas — case-insensitive (Linux/Windows)."""
    if not folder or not os.path.isdir(folder):
        return []
    exts_lower = {e.lower() for e in exts}
    out = []
    try:
        for f in os.listdir(folder):
            if os.path.splitext(f)[1].lower() in exts_lower:
                out.append(os.path.join(folder, f))
    except Exception:
        pass
    return sorted(out)

def ingest_despesa(base, cfg):
    folder = _find_dir(base, DESP_DIR)
    rows, seen, dropped = [], set(), []
    for fp in _files(folder, [".xlsx", ".xls"]):
        df = _read(fp)
        if df.shape[1] < 7: continue
        sig = (df.shape, round(df.iloc[:, 6].map(B.parse_valor_br).sum(), 2))
        if sig in seen: dropped.append(os.path.basename(fp)); continue
        seen.add(sig)
        for _, r in df.iterrows():
            d = B.parse_date(r.iloc[1]); val = B.parse_valor_br(r.iloc[6])
            if not B.valid(d) or val == 0: continue
            conta = "" if pd.isna(r.iloc[3]) else str(r.iloc[3]).strip()
            cc    = "" if pd.isna(r.iloc[4]) else str(r.iloc[4]).strip()
            cred  = "" if pd.isna(r.iloc[2]) else str(r.iloc[2]).strip()
            pgto  = r.iloc[5]; pago = not (pd.isna(pgto) or str(pgto).strip() == "")
            cu, ccu = conta.upper(), cc.upper()
            linha = cfg.conta2linha.get(cu); info = cfg.cc2info.get(ccu)
            destino, motivo, nat, tipo, grupo, sub, det = "DRE", "", "", "", "", "", ""
            if conta == "" or cc == "" or linha is None or info is None:
                destino = "REAPROPRIAR"
                mm = []
                mm.append("sem conta" if conta == "" else ("conta não mapeada" if linha is None else ""))
                mm.append("sem CC" if cc == "" else ("CC não mapeado" if info is None else ""))
                motivo = " + ".join([m for m in mm if m])
            else:
                nat, tipo = cfg.conta2nat.get(cu, ("DESPESA_DIRETA", ""))
                grupo, sub, det = info.get("grupo", ""), info.get("subgrupo", ""), info.get("detalhe", "")
                forca = info.get("forca_capex", "N") == "S"
                if linha == "IGNORAR" or nat == "IGNORAR": destino = "IGNORADO"
                elif forca or nat == "CAPEX": destino = "CAPEX"
                elif nat == "INVENTARIAVEL": destino = "ESTOQUE"
                else: destino = "DRE"
            rows.append(dict(periodo=B.period(d), ano=d.year, mes=d.month, data=d,
                conta=conta or "(sem conta)", cc=cc or "(sem CC)", credor=cred, valor=val,
                linha_dre=linha or "", natureza=nat, tipo_estoque=tipo,
                grupo=grupo, subgrupo=sub, detalhe=det, destino=destino, motivo=motivo, pago=pago))
    return pd.DataFrame(rows), dropped

def ingest_receita(base, cfg):
    folder = _find_dir(base, REC_DIR)
    rows, seen = [], set()
    for fp in _files(folder, [".xlsx", ".xls"]):
        df = _read(fp)
        if df.shape[1] < 9: continue
        sig = (df.shape, round(df.iloc[:, 8].map(B.parse_valor_br).sum(), 2))
        if sig in seen: continue
        seen.add(sig)
        for _, r in df.iterrows():
            d = B.parse_date(r.iloc[3]); val = B.parse_valor_br(r.iloc[8])
            if not B.valid(d) or val == 0: continue
            prod = "" if pd.isna(r.iloc[5]) else str(r.iloc[5]).strip()
            info = cfg.prod2.get(prod)
            lid = info["linha_id"] if info else ""
            grupo = info["grupo"] if info else ""
            uni = info["unidade"] if info else ""
            cor = info["cor"] if info else ""
            if not info: destino = "NAOCLASS"
            elif lid == "IGNORAR": destino = "IGNORADO"
            elif lid == "DESCARTE_AVES": destino = "DESCARTE"
            else: destino = "RECEITA"
            rows.append(dict(periodo=B.period(d), ano=d.year, mes=d.month, data=d, produto=prod,
                linha_id=lid, grupo=grupo, unidade=uni, cor=cor, valor=val, destino=destino,
                cliente=("" if pd.isna(r.iloc[1]) else str(r.iloc[1]).strip())))
    return pd.DataFrame(rows)

def ingest_produtos(base):
    """Produtos produzidos: ração (POSTURA/RECRIA) E caixas de ovos (OVOS, produto acabado)."""
    folder = _find_dir(base, PROD_DIR)
    rows = []
    fs = _files(folder, [".xls", ".xlsx"])
    if fs:
        df = _read(fs[0])
        if df.shape[1] >= 8:
            for _, r in df.iterrows():
                desc = str(r.iloc[2]).strip(); u = desc.upper()
                if "OVOS" in u: fase = "OVOS"
                elif "PRE POSTURA" in u or "PRE-POSTURA" in u: fase = "RECRIA"
                elif "POSTURA" in u: fase = "POSTURA"
                elif any(k in u for k in ("INICIAL", "CRESCIMENTO", "MATURIDADE")): fase = "RECRIA"
                else: continue
                d = B.parse_date(r.iloc[7])
                if not B.valid(d): continue
                rows.append(dict(periodo=B.period(d), ano=d.year, mes=d.month,
                    galpao=str(r.iloc[4]).strip(), descricao=desc, fase=fase,
                    qtd=B.parse_valor_br(r.iloc[5]), custo=B.parse_valor_br(r.iloc[6])))
    return pd.DataFrame(rows)

def ingest_imob(base):
    """Registro de Imobilizado: aquisição, pago, saldo a pagar, depreciação, ativo biológico."""
    fp = os.path.join(base, IMOB_FP)
    rows = []
    try:
        df = pd.read_excel(fp, sheet_name="Registro de Imobilizado", header=3, dtype=object)
        for i in range(len(df)):
            aq = B.parse_valor_br(df.iloc[i, 11])
            cod = df.iloc[i, 0]
            if aq <= 0: continue
            if pd.isna(cod) or str(cod).strip() == "" or "TOTAL" in str(df.iloc[i, 1]).upper():
                continue  # pula linhas de total/resumo
            classe = str(df.iloc[i, 2]); bloco = str(df.iloc[i, 3]); st = str(df.iloc[i, 10]).strip()
            is_bio = any(k in (classe + " " + bloco).upper() for k in ("BIOL", "PLANTEL", "AVES"))
            rows.append(dict(item=str(df.iloc[i, 1]), classe=classe, acq=B.parse_date(df.iloc[i, 8]),
                valor_aquisicao=aq, valor_pago=B.parse_valor_br(df.iloc[i, 12]),
                saldo_a_pagar=B.parse_valor_br(df.iloc[i, 13]), deprec_mensal=B.parse_valor_br(df.iloc[i, 15]),
                valor_liquido=B.parse_valor_br(df.iloc[i, 18]), status=st,
                em_uso=("USO" in st.upper()), is_bio=is_bio))
    except Exception: pass
    return pd.DataFrame(rows)

FC_SAI_DIR = "1.1 FLUXO DE CAIXA - DESEMBOLSO POR DATA DE PAGAMENTO"
FC_ENT_DIR = "1.2 FLUXO DE CAIXA - FATURAMENTO POR DATA DE RECEBIMENTO"

def _fc_categoria(conta, cc, cfg):
    cu, ccu = conta.upper(), cc.upper()
    info = cfg.cc2info.get(ccu)
    nat = cfg.conta2nat.get(cu, ("", ""))[0]
    forca = (info.get("forca_capex", "N") == "S") if info else False
    if forca or nat == "CAPEX" or "ADIANTAMENTO" in cu or "ADIANTAMENTO" in ccu: return "Investimento"
    if any(k in cu for k in ("EMPRESTIMO", "EMPRÉSTIMO", "FINANCIAMENTO", "JUROS", "CONSIGNADO")): return "Financiamento"
    return "Operacional"

def ingest_fc_saidas(base, cfg):
    """Saídas de caixa = Contas Pagas, por DATA DE PAGAMENTO (col5)."""
    folder = _find_dir(base, FC_SAI_DIR); rows, seen, dropped = [], set(), []
    for fp in _files(folder, [".xlsx", ".xls"]):
        df = _read(fp)
        if df.shape[1] < 7: continue
        sig = (df.shape, round(df.iloc[:, 6].map(B.parse_valor_br).sum(), 2))
        if sig in seen: dropped.append(os.path.basename(fp)); continue
        seen.add(sig)
        for _, r in df.iterrows():
            d = B.parse_date(r.iloc[5]); val = B.parse_valor_br(r.iloc[6])
            if not B.valid(d) or val == 0: continue
            conta = "" if pd.isna(r.iloc[3]) else str(r.iloc[3]).strip()
            cc = "" if pd.isna(r.iloc[4]) else str(r.iloc[4]).strip()
            cred = "" if pd.isna(r.iloc[2]) else str(r.iloc[2]).strip()
            rows.append(dict(periodo=B.period(d), ano=d.year, mes=d.month, data=d,
                conta=conta or "(sem conta)", cc=cc or "(sem CC)", credor=cred, valor=val,
                categoria=_fc_categoria(conta, cc, cfg)))
    return pd.DataFrame(rows), dropped

def ingest_fc_entradas(base, cfg):
    """Entradas de caixa = Notas recebidas, por DATA DE RECEBIMENTO (col4 = Pagamento)."""
    folder = _find_dir(base, FC_ENT_DIR); rows, seen = [], set()
    for fp in _files(folder, [".xlsx", ".xls"]):
        df = _read(fp)
        if df.shape[1] < 9: continue
        sig = (df.shape, round(df.iloc[:, 8].map(B.parse_valor_br).sum(), 2))
        if sig in seen: continue
        seen.add(sig)
        for _, r in df.iterrows():
            d = B.parse_date(r.iloc[4]); val = B.parse_valor_br(r.iloc[8])
            if not B.valid(d) or val == 0: continue
            prod = "" if pd.isna(r.iloc[5]) else str(r.iloc[5]).strip()
            cli = "" if pd.isna(r.iloc[1]) else str(r.iloc[1]).strip()
            rows.append(dict(periodo=B.period(d), ano=d.year, mes=d.month, data=d,
                produto=prod, cliente=cli, valor=val, categoria="Operacional"))
    return pd.DataFrame(rows)

def _unidade(desc):
    d = B.norm_prod(desc)
    if "CAIPIRA" in d: return "Fazenda (MATRIZ)"
    if "VERMELHO" in d or "BRANCO" in d: return "Silveira (FILIAL)"
    return "—"

def load_all(base, cfg):
    desp, dropped = ingest_despesa(base, cfg)
    rec = ingest_receita(base, cfg)
    pp = ingest_produtos(base)
    imob = ingest_imob(base)
    rac = pp[pp.fase.isin(["POSTURA", "RECRIA"])].copy() if len(pp) else pp
    prod = pp[pp.fase == "OVOS"].copy() if len(pp) else pp
    if len(prod):
        prod["unidade"] = prod.descricao.map(_unidade)
        prod["matched"] = prod.descricao.map(lambda d: B.norm_prod(d) in cfg.comp)
        prod["emb_unit"] = prod.descricao.map(
            lambda d: cfg.comp.get(B.norm_prod(d), B.eggs_per_box(d) * cfg.comp_emb_per_egg))
        prod["emb_total"] = prod.emb_unit * prod.qtd
    fc_sai, fc_drop = ingest_fc_saidas(base, cfg)
    fc_ent = ingest_fc_entradas(base, cfg)
    pers = set()
    if len(desp): pers |= set(desp.periodo)
    if len(rec):  pers |= set(rec.periodo)
    if len(fc_sai): pers |= set(fc_sai.periodo)
    if len(fc_ent): pers |= set(fc_ent.periodo)
    return dict(despesa=desp, receita=rec, racao=rac, producao=prod, imob=imob,
                fc_saidas=fc_sai, fc_entradas=fc_ent, fc_dropped=fc_drop,
                periodos=sorted(pers), dropped=dropped)
