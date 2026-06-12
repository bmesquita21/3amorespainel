# -*- coding: utf-8 -*-
"""Migra os CSVs de config para o PostgreSQL (executa apenas uma vez por tabela)."""
import csv, os
import db_pg as PG


def _load_csv(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig") as f:
        lines = [l for l in f if not l.startswith("#")]
    return list(csv.DictReader(lines, delimiter=";"))


def _tabela_vazia(tabela: str) -> bool:
    rows = PG.fetchall(f"SELECT 1 FROM {tabela} LIMIT 1")
    return len(rows) == 0


def migrate_all(cfg_dir: str):
    """Migra CSVs → PG apenas se as tabelas estiverem vazias."""
    PG.init_schema()

    if _tabela_vazia("contas"):
        rows = _load_csv(os.path.join(cfg_dir, "config_contas.csv"))
        if rows:
            PG.executemany(
                "INSERT INTO contas(nome_conta,linha_dre,natureza,tipo_estoque) "
                "VALUES(%(nome_conta)s,%(linha_dre)s,%(natureza)s,%(tipo_estoque)s) "
                "ON CONFLICT(nome_conta) DO NOTHING",
                [{"nome_conta": r["nome_conta"].strip().upper(),
                  "linha_dre":  r.get("linha_dre","").strip(),
                  "natureza":   r.get("natureza","DESPESA_DIRETA").strip() or "DESPESA_DIRETA",
                  "tipo_estoque": r.get("tipo_estoque","").strip()} for r in rows]
            )

    if _tabela_vazia("centros_custo"):
        rows = _load_csv(os.path.join(cfg_dir, "config_centros_custo.csv"))
        if rows:
            PG.executemany(
                "INSERT INTO centros_custo(centro_custo,grupo,subgrupo,detalhe,inventariavel,tipo_estoque,forca_capex) "
                "VALUES(%(centro_custo)s,%(grupo)s,%(subgrupo)s,%(detalhe)s,%(inventariavel)s,%(tipo_estoque)s,%(forca_capex)s) "
                "ON CONFLICT(centro_custo) DO NOTHING",
                [{"centro_custo": r["centro_custo"].strip().upper(),
                  "grupo":        r.get("grupo","").strip(),
                  "subgrupo":     r.get("subgrupo","").strip(),
                  "detalhe":      r.get("detalhe","").strip(),
                  "inventariavel":r.get("inventariavel","N").strip() or "N",
                  "tipo_estoque": r.get("tipo_estoque","").strip(),
                  "forca_capex":  r.get("forca_capex","N").strip() or "N"} for r in rows]
            )

    if _tabela_vazia("fornecedores"):
        rows = _load_csv(os.path.join(cfg_dir, "config_fornecedores.csv"))
        if rows:
            PG.executemany(
                "INSERT INTO fornecedores(credor,linha_dre,natureza,tipo_estoque,observacao) "
                "VALUES(%(credor)s,%(linha_dre)s,%(natureza)s,%(tipo_estoque)s,%(observacao)s) "
                "ON CONFLICT(credor) DO NOTHING",
                [{"credor":      r["credor"].strip().upper(),
                  "linha_dre":   r.get("linha_dre","").strip(),
                  "natureza":    r.get("natureza","DESPESA_DIRETA").strip() or "DESPESA_DIRETA",
                  "tipo_estoque":r.get("tipo_estoque","").strip(),
                  "observacao":  r.get("observacao","").strip()} for r in rows]
            )

    if _tabela_vazia("produtos"):
        rows = _load_csv(os.path.join(cfg_dir, "config_produtos.csv"))
        if rows:
            PG.executemany(
                "INSERT INTO produtos(produto_original,grupo,cor,tipo,linha_id,unidade,marca) "
                "VALUES(%(produto_original)s,%(grupo)s,%(cor)s,%(tipo)s,%(linha_id)s,%(unidade)s,%(marca)s) "
                "ON CONFLICT(produto_original) DO NOTHING",
                [{"produto_original": r["produto_original"].strip(),
                  "grupo":   r.get("grupo","").strip(),
                  "cor":     r.get("cor","").strip(),
                  "tipo":    r.get("tipo","").strip(),
                  "linha_id":r.get("linha_id","").strip(),
                  "unidade": r.get("unidade","").strip(),
                  "marca":   r.get("marca","").strip()} for r in rows]
            )

    if _tabela_vazia("config_composicao"):
        rows = _load_csv(os.path.join(cfg_dir, "config_composicao.csv"))
        if rows:
            PG.executemany(
                "INSERT INTO config_composicao(produto_norm,produto_original,ovos_por_caixa,emb_por_caixa,total_por_caixa,unidade) "
                "VALUES(%(produto_norm)s,%(produto_original)s,%(ovos_por_caixa)s,%(emb_por_caixa)s,%(total_por_caixa)s,%(unidade)s) "
                "ON CONFLICT(produto_norm) DO NOTHING",
                [{"produto_norm":     r.get("produto_norm","").strip().upper(),
                  "produto_original": r.get("produto_original","").strip(),
                  "ovos_por_caixa":   float(str(r.get("ovos_por_caixa","0")).replace(",",".") or 0),
                  "emb_por_caixa":    float(str(r.get("emb_por_caixa","0")).replace(",",".") or 0),
                  "total_por_caixa":  float(str(r.get("total_por_caixa","0")).replace(",",".") or 0),
                  "unidade":          r.get("unidade","").strip()} for r in rows]
            )

    if _tabela_vazia("config_lotes"):
        rows = _load_csv(os.path.join(cfg_dir, "config_lotes.csv"))
        for r in rows:
            PG.execute(
                "INSERT INTO config_lotes(lote_id,fonte_recria,data_entrada_recria,data_inicio_postura,"
                "galpao_postura,grupo_galpao,n_aves,ciclo_postura_meses,metodo_amortizacao) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(lote_id) DO NOTHING",
                (r.get("lote_id","").strip(), r.get("fonte_recria","").strip(),
                 r.get("data_entrada_recria","").strip(), r.get("data_inicio_postura","").strip(),
                 r.get("galpao_postura","").strip(), r.get("grupo_galpao","").strip(),
                 int(float(r.get("n_aves","0") or 0)),
                 int(float(r.get("ciclo_postura_meses","13") or 13)),
                 r.get("metodo_amortizacao","LINEAR").strip())
            )

    if _tabela_vazia("extrato_correcoes"):
        fp_cor = os.path.join(cfg_dir, "correcoes_classificacao.csv")
        if os.path.exists(fp_cor):
            try:
                import pandas as _pd
                df_cor = _pd.read_csv(fp_cor, sep=";", dtype=str)
                for _, r in df_cor.iterrows():
                    tid = str(r.get("tid","")).strip()
                    nat = str(r.get("natureza","")).strip()
                    if tid and tid.lower() != "nan" and nat and nat.lower() != "nan":
                        PG.execute(
                            "INSERT INTO extrato_correcoes(tid,natureza,banco,data_tx,valor,descricao) "
                            "VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(tid) DO NOTHING",
                            (tid, nat, str(r.get("banco","")), str(r.get("data","")),
                             str(r.get("valor","")), str(r.get("desc","")))
                        )
            except Exception:
                pass

    if _tabela_vazia("config_geral"):
        yaml_path = os.path.join(cfg_dir, "config_geral.yaml")
        if os.path.exists(yaml_path):
            try:
                import yaml as _yaml
                with open(yaml_path, encoding="utf-8") as f:
                    g = _yaml.safe_load(f) or {}
                bp = (g.get("balanco") or {}) if isinstance(g, dict) else {}
                ab = (g.get("ativo_biologico") or {}) if isinstance(g, dict) else {}
                for chave, valor in [
                    ("capital_social",      str(bp.get("capital_social", "") or "")),
                    ("saldo_caixa_inicial", str(bp.get("saldo_caixa_inicial", "") or "")),
                    ("biologico_default",   str(ab.get("tratar_recria_como_ativo", True)).lower()),
                ]:
                    PG.execute(
                        "INSERT INTO config_geral(chave, valor) VALUES(%s,%s) ON CONFLICT(chave) DO NOTHING",
                        (chave, valor)
                    )
            except Exception:
                pass

    if _tabela_vazia("usuarios"):
        yaml_path = os.path.join(cfg_dir, "usuarios.yaml")
        if os.path.exists(yaml_path):
            try:
                import yaml as _yaml
                with open(yaml_path, encoding="utf-8") as f:
                    data = _yaml.safe_load(f) or {}
                for login, info in (data.get("usuarios") or {}).items():
                    PG.execute(
                        "INSERT INTO usuarios(login, nome, salt, hash) VALUES(%s,%s,%s,%s) "
                        "ON CONFLICT(login) DO NOTHING",
                        (login.strip().lower(), info.get("nome", login),
                         info.get("salt", ""), info.get("hash", ""))
                    )
            except Exception:
                pass
