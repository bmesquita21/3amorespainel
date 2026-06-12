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

    CREATE TABLE IF NOT EXISTS config_geral (
        chave      TEXT PRIMARY KEY,
        valor      TEXT NOT NULL DEFAULT '',
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


def is_available() -> bool:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True
    except Exception:
        return False
