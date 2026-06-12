# -*- coding: utf-8 -*-
"""Conexão e schema do PostgreSQL auxiliar (parametrizações, extratos, usuários).

Tabelas:
  contas          — mapeamento conta contábil → linha DRE
  centros_custo   — mapeamento CC → grupo/subgrupo/detalhe
  fornecedores    — fallback fornecedor → linha DRE
  produtos        — mapeamento produto → linha receita
  usuarios        — autenticação (migra de usuarios.yaml)
  extrato_txs     — transações OFX importadas
  extrato_regras  — regras de classificação automática
"""
import os
import psycopg2
import psycopg2.extras
from contextlib import contextmanager

_DSN = None


def _get_dsn() -> str:
    global _DSN
    if _DSN is None:
        _DSN = (
            f"host={os.environ.get('PG_HOST','localhost')} "
            f"port={os.environ.get('PG_PORT','5432')} "
            f"dbname={os.environ.get('PG_DB','painel3amores')} "
            f"user={os.environ.get('PG_USER','painel')} "
            f"password={os.environ.get('PG_PASSWORD','')}"
        )
    return _DSN


@contextmanager
def get_conn():
    conn = psycopg2.connect(_get_dsn())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema():
    """Cria as tabelas se não existirem."""
    sql = """
    CREATE TABLE IF NOT EXISTS contas (
        id          SERIAL PRIMARY KEY,
        nome_conta  TEXT NOT NULL UNIQUE,
        linha_dre   TEXT NOT NULL,
        natureza    TEXT NOT NULL DEFAULT 'DESPESA_DIRETA',
        tipo_estoque TEXT NOT NULL DEFAULT '',
        ativo       BOOLEAN NOT NULL DEFAULT TRUE,
        updated_at  TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS centros_custo (
        id           SERIAL PRIMARY KEY,
        centro_custo TEXT NOT NULL UNIQUE,
        grupo        TEXT NOT NULL DEFAULT '',
        subgrupo     TEXT NOT NULL DEFAULT '',
        detalhe      TEXT NOT NULL DEFAULT '',
        inventariavel TEXT NOT NULL DEFAULT 'N',
        tipo_estoque TEXT NOT NULL DEFAULT '',
        forca_capex  TEXT NOT NULL DEFAULT 'N',
        ativo        BOOLEAN NOT NULL DEFAULT TRUE,
        updated_at   TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS fornecedores (
        id          SERIAL PRIMARY KEY,
        credor      TEXT NOT NULL UNIQUE,
        linha_dre   TEXT NOT NULL,
        natureza    TEXT NOT NULL DEFAULT 'DESPESA_DIRETA',
        tipo_estoque TEXT NOT NULL DEFAULT '',
        observacao  TEXT NOT NULL DEFAULT '',
        ativo       BOOLEAN NOT NULL DEFAULT TRUE,
        updated_at  TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS produtos (
        id               SERIAL PRIMARY KEY,
        produto_original TEXT NOT NULL UNIQUE,
        grupo            TEXT NOT NULL DEFAULT '',
        cor              TEXT NOT NULL DEFAULT '',
        tipo             TEXT NOT NULL DEFAULT '',
        linha_id         TEXT NOT NULL DEFAULT '',
        unidade          TEXT NOT NULL DEFAULT '',
        marca            TEXT NOT NULL DEFAULT '',
        ativo            BOOLEAN NOT NULL DEFAULT TRUE,
        updated_at       TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS usuarios (
        id         SERIAL PRIMARY KEY,
        login      TEXT NOT NULL UNIQUE,
        nome       TEXT NOT NULL,
        salt       TEXT NOT NULL,
        hash       TEXT NOT NULL,
        ativo      BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS extrato_txs (
        id          SERIAL PRIMARY KEY,
        banco       TEXT NOT NULL,
        conta       TEXT NOT NULL DEFAULT '',
        data_tx     DATE NOT NULL,
        valor       NUMERIC(15,2) NOT NULL,
        descricao   TEXT NOT NULL DEFAULT '',
        fitid       TEXT NOT NULL,
        categoria   TEXT NOT NULL DEFAULT '',
        classificado TEXT NOT NULL DEFAULT 'pendente',
        periodo     TEXT NOT NULL DEFAULT '',
        created_at  TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(banco, fitid)
    );

    CREATE TABLE IF NOT EXISTS extrato_regras (
        id         SERIAL PRIMARY KEY,
        padrao     TEXT NOT NULL,
        categoria  TEXT NOT NULL,
        prioridade INT NOT NULL DEFAULT 0,
        ativo      BOOLEAN NOT NULL DEFAULT TRUE
    );

    CREATE INDEX IF NOT EXISTS idx_extrato_txs_periodo ON extrato_txs(periodo);
    CREATE INDEX IF NOT EXISTS idx_extrato_txs_data    ON extrato_txs(data_tx);

    CREATE TABLE IF NOT EXISTS extrato_saldos (
        id         SERIAL PRIMARY KEY,
        banco      TEXT NOT NULL,
        conta      TEXT NOT NULL,
        periodo    TEXT NOT NULL,
        dtasof     DATE,
        saldo_fim  NUMERIC(15,2) NOT NULL DEFAULT 0,
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(banco, conta, periodo)
    );
    CREATE INDEX IF NOT EXISTS idx_extrato_saldos_periodo ON extrato_saldos(periodo);

    CREATE TABLE IF NOT EXISTS config_geral (
        chave      TEXT PRIMARY KEY,
        valor      TEXT NOT NULL DEFAULT '',
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS config_composicao (
        id              SERIAL PRIMARY KEY,
        produto_norm    TEXT NOT NULL UNIQUE,
        produto_original TEXT NOT NULL DEFAULT '',
        ovos_por_caixa  NUMERIC(10,2) NOT NULL DEFAULT 0,
        emb_por_caixa   NUMERIC(10,4) NOT NULL DEFAULT 0,
        total_por_caixa NUMERIC(10,4) NOT NULL DEFAULT 0,
        unidade         TEXT NOT NULL DEFAULT '',
        ativo           BOOLEAN NOT NULL DEFAULT TRUE,
        updated_at      TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS config_lotes (
        id                  SERIAL PRIMARY KEY,
        lote_id             TEXT NOT NULL UNIQUE,
        fonte_recria        TEXT NOT NULL DEFAULT '',
        data_entrada_recria TEXT NOT NULL DEFAULT '',
        data_inicio_postura TEXT NOT NULL DEFAULT '',
        galpao_postura      TEXT NOT NULL DEFAULT '',
        grupo_galpao        TEXT NOT NULL DEFAULT '',
        n_aves              INT  NOT NULL DEFAULT 0,
        ciclo_postura_meses INT  NOT NULL DEFAULT 13,
        metodo_amortizacao  TEXT NOT NULL DEFAULT 'LINEAR',
        ativo               BOOLEAN NOT NULL DEFAULT TRUE,
        updated_at          TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS imobilizado (
        id              SERIAL PRIMARY KEY,
        item            TEXT NOT NULL,
        classe          TEXT NOT NULL DEFAULT '',
        bloco           TEXT NOT NULL DEFAULT '',
        data_aquisicao  DATE,
        valor_aquisicao NUMERIC(15,2) NOT NULL DEFAULT 0,
        valor_pago      NUMERIC(15,2) NOT NULL DEFAULT 0,
        saldo_a_pagar   NUMERIC(15,2) NOT NULL DEFAULT 0,
        deprec_mensal   NUMERIC(15,2) NOT NULL DEFAULT 0,
        valor_liquido   NUMERIC(15,2) NOT NULL DEFAULT 0,
        status          TEXT NOT NULL DEFAULT '',
        em_uso          BOOLEAN NOT NULL DEFAULT TRUE,
        is_bio          BOOLEAN NOT NULL DEFAULT FALSE,
        ativo           BOOLEAN NOT NULL DEFAULT TRUE,
        updated_at      TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS extrato_correcoes (
        id         SERIAL PRIMARY KEY,
        tid        TEXT NOT NULL UNIQUE,
        natureza   TEXT NOT NULL,
        banco      TEXT NOT NULL DEFAULT '',
        data_tx    TEXT NOT NULL DEFAULT '',
        valor      TEXT NOT NULL DEFAULT '',
        descricao  TEXT NOT NULL DEFAULT '',
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)


# ─── Helpers genéricos ───────────────────────────────────────────────────────

def fetchall(sql: str, params=None) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]


def execute(sql: str, params=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)


def executemany(sql: str, seq):
    with get_conn() as conn:
        with conn.cursor() as cur:
            psycopg2.extras.execute_batch(cur, sql, seq)


# ─── Fetch helpers para configs ──────────────────────────────────────────────

def fetch_contas() -> list:
    return fetchall("SELECT nome_conta, linha_dre, natureza, tipo_estoque FROM contas WHERE ativo = TRUE ORDER BY nome_conta")

def fetch_centros_custo() -> list:
    return fetchall("SELECT centro_custo, grupo, subgrupo, detalhe, inventariavel, tipo_estoque, forca_capex FROM centros_custo WHERE ativo = TRUE ORDER BY centro_custo")

def fetch_fornecedores() -> list:
    return fetchall("SELECT credor, linha_dre, natureza, tipo_estoque, observacao FROM fornecedores WHERE ativo = TRUE ORDER BY credor")

def fetch_produtos() -> list:
    return fetchall("SELECT produto_original, grupo, cor, tipo, linha_id, unidade, marca FROM produtos WHERE ativo = TRUE ORDER BY produto_original")

def fetch_config_geral() -> dict:
    rows = fetchall("SELECT chave, valor FROM config_geral")
    return {r["chave"]: r["valor"] for r in rows}

def upsert_config_geral(chave: str, valor: str):
    execute("INSERT INTO config_geral(chave, valor) VALUES(%s,%s) ON CONFLICT(chave) DO UPDATE SET valor=%s, updated_at=NOW()", (chave, valor, valor))


# ─── Fetch/write helpers para usuários ────────────────────────────────────────

def fetch_usuarios() -> list:
    return fetchall("SELECT login, nome, salt, hash FROM usuarios WHERE ativo = TRUE ORDER BY login")

def upsert_usuario(login: str, nome: str, salt: str, hash_: str):
    execute(
        "INSERT INTO usuarios(login, nome, salt, hash) VALUES(%s,%s,%s,%s) "
        "ON CONFLICT(login) DO UPDATE SET nome=EXCLUDED.nome, salt=EXCLUDED.salt, hash=EXCLUDED.hash",
        (login, nome, salt, hash_)
    )


# ─── Helper bulk para extratos OFX ────────────────────────────────────────────

def fetch_composicao() -> list:
    return fetchall("SELECT produto_norm, produto_original, ovos_por_caixa, emb_por_caixa, total_por_caixa, unidade FROM config_composicao WHERE ativo = TRUE ORDER BY produto_norm")

def fetch_lotes() -> list:
    return fetchall("SELECT lote_id, fonte_recria, data_entrada_recria, data_inicio_postura, galpao_postura, grupo_galpao, n_aves, ciclo_postura_meses, metodo_amortizacao FROM config_lotes WHERE ativo = TRUE ORDER BY lote_id")

def fetch_imobilizado() -> list:
    return fetchall("SELECT item, classe, bloco, data_aquisicao, valor_aquisicao, valor_pago, saldo_a_pagar, deprec_mensal, valor_liquido, status, em_uso, is_bio FROM imobilizado WHERE ativo = TRUE ORDER BY id")

def replace_imobilizado(rows: list):
    """Substitui todo o imobilizado (desativa antigos e insere novos)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE imobilizado SET ativo = FALSE")
            for r in rows:
                cur.execute("""
                    INSERT INTO imobilizado(item,classe,bloco,data_aquisicao,valor_aquisicao,valor_pago,saldo_a_pagar,deprec_mensal,valor_liquido,status,em_uso,is_bio)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (r["item"], r["classe"], r.get("bloco",""), r.get("acq"),
                      r["valor_aquisicao"], r["valor_pago"], r["saldo_a_pagar"],
                      r["deprec_mensal"], r["valor_liquido"], r["status"],
                      bool(r["em_uso"]), bool(r["is_bio"])))

def fetch_correcoes() -> dict:
    rows = fetchall("SELECT tid, natureza FROM extrato_correcoes")
    return {r["tid"]: r["natureza"] for r in rows}

def upsert_correcao(tid: str, natureza: str, banco: str = "", data_tx: str = "", valor: str = "", descricao: str = ""):
    execute("""
        INSERT INTO extrato_correcoes(tid, natureza, banco, data_tx, valor, descricao)
        VALUES(%s,%s,%s,%s,%s,%s)
        ON CONFLICT(tid) DO UPDATE SET natureza=%s, banco=%s, data_tx=%s, valor=%s, descricao=%s, updated_at=NOW()
    """, (tid, natureza, banco, data_tx, valor, descricao,
          natureza, banco, data_tx, valor, descricao))


def insert_extrato_batch(txs: list) -> tuple:
    """Insere transações, ignora duplicatas. Retorna (inseridas, ignoradas)."""
    if not txs:
        return 0, 0
    sql = """
        INSERT INTO extrato_txs(banco, conta, data_tx, valor, descricao, fitid, periodo, categoria, classificado)
        VALUES(%(banco)s, %(conta)s, %(data_tx)s, %(valor)s, %(descricao)s, %(fitid)s, %(periodo)s, %(categoria)s, %(classificado)s)
        ON CONFLICT(banco, fitid) DO NOTHING
    """
    inserted = 0
    skipped = 0
    with get_conn() as conn:
        with conn.cursor() as cur:
            for tx in txs:
                cur.execute(sql, tx)
                if cur.rowcount > 0:
                    inserted += 1
                else:
                    skipped += 1
    return inserted, skipped


def fetch_extrato_txs() -> list:
    """Retorna todas as transações de extrato salvas no PG."""
    return fetchall(
        "SELECT banco, conta, data_tx, valor, descricao, fitid, periodo "
        "FROM extrato_txs ORDER BY data_tx, id"
    )


def fetch_extrato_saldos() -> list:
    """Retorna os saldos de fechamento por conta/período."""
    return fetchall(
        "SELECT banco, conta, periodo, dtasof, saldo_fim "
        "FROM extrato_saldos ORDER BY periodo, banco, conta"
    )


def upsert_extrato_saldo(banco: str, conta: str, periodo: str, saldo_fim: float, dtasof=None):
    execute("""
        INSERT INTO extrato_saldos(banco, conta, periodo, dtasof, saldo_fim)
        VALUES(%s,%s,%s,%s,%s)
        ON CONFLICT(banco, conta, periodo) DO UPDATE
          SET saldo_fim=%s, dtasof=%s, updated_at=NOW()
    """, (banco, conta, periodo, dtasof, saldo_fim, saldo_fim, dtasof))


def is_available() -> bool:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True
    except Exception:
        return False
