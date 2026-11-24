"""Banco SQLite: conexão, schema e utilidades."""
from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("ZINC_DATA_DIR", BASE_DIR / "data"))

_local = threading.local()

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS materia (
    id        INTEGER PRIMARY KEY,
    nome      TEXT NOT NULL UNIQUE,
    sigla     TEXT,
    lei_seca  INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS lei (
    id          INTEGER PRIMARY KEY,
    nome        TEXT NOT NULL,
    sigla       TEXT NOT NULL UNIQUE,
    pdf_path    TEXT,
    versao      INTEGER NOT NULL DEFAULT 1,
    enviado_em  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dispositivo (
    id          INTEGER PRIMARY KEY,
    lei_id      INTEGER NOT NULL REFERENCES lei(id) ON DELETE CASCADE,
    referencia  TEXT NOT NULL,      -- forma legível: "art. 5º, XI"
    chave       TEXT NOT NULL,      -- forma normalizada: "5|XI"
    nivel       TEXT NOT NULL,      -- artigo | paragrafo | inciso | alinea
    artigo      TEXT NOT NULL,      -- chave do artigo: "5"
    texto       TEXT NOT NULL,
    ordem       INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_disp_lei_chave ON dispositivo(lei_id, chave);
CREATE INDEX IF NOT EXISTS ix_disp_lei_artigo ON dispositivo(lei_id, artigo);

CREATE TABLE IF NOT EXISTS topico (
    id               INTEGER PRIMARY KEY,
    materia_id       INTEGER NOT NULL REFERENCES materia(id),
    nome             TEXT NOT NULL,
    dispositivo_ref  TEXT NOT NULL DEFAULT '',   -- "CF/88, art. 5º, XI"
    lei_id           INTEGER REFERENCES lei(id) ON DELETE SET NULL,
    dispositivo_chave TEXT NOT NULL DEFAULT '',
    etapa            INTEGER NOT NULL DEFAULT 0,
    proxima_revisao  TEXT NOT NULL,
    ultima_revisao   TEXT,
    ultima_geracao   TEXT,
    criado_em        TEXT NOT NULL,
    UNIQUE (materia_id, nome)
);

CREATE TABLE IF NOT EXISTS material_apoio (
    id          INTEGER PRIMARY KEY,
    topico_id   INTEGER NOT NULL REFERENCES topico(id) ON DELETE CASCADE,
    nome        TEXT NOT NULL,
    pdf_path    TEXT,
    texto       TEXT NOT NULL,
    enviado_em  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS questao (
    id                  INTEGER PRIMARY KEY,
    topico_id           INTEGER NOT NULL REFERENCES topico(id) ON DELETE CASCADE,
    origem              TEXT NOT NULL,            -- real | gerada
    enunciado           TEXT NOT NULL,
    alternativas_json   TEXT NOT NULL,            -- [{"letra":"A","texto":"..."}]
    gabarito            TEXT NOT NULL DEFAULT '',
    gabarito_origem     TEXT NOT NULL DEFAULT '', -- print | claude_provisorio | claude_conferido | usuario | claude
    justificativa       TEXT NOT NULL DEFAULT '',
    explicacoes_json    TEXT NOT NULL DEFAULT '[]', -- [{"letra":"B","motivo":"..."}]
    dispositivo_ref     TEXT NOT NULL DEFAULT '',
    trecho_base         TEXT NOT NULL DEFAULT '',
    fonte_externa       INTEGER NOT NULL DEFAULT 0,
    fontes              TEXT NOT NULL DEFAULT '',
    explicacao_detalhada TEXT NOT NULL DEFAULT '',
    no_banco            INTEGER NOT NULL DEFAULT 0,
    status              TEXT NOT NULL DEFAULT 'ativa',  -- ativa | invalidada
    motivo_invalidacao  TEXT NOT NULL DEFAULT '',
    marcada_no_tec      TEXT NOT NULL DEFAULT '',
    resultado_no_tec    TEXT NOT NULL DEFAULT '',  -- acertou | errou | nao_respondeu
    imagem_path         TEXT NOT NULL DEFAULT '',
    vezes_vista         INTEGER NOT NULL DEFAULT 0,
    criado_em           TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_questao_topico ON questao(topico_id, status);

CREATE TABLE IF NOT EXISTS sessao (
    id            INTEGER PRIMARY KEY,
    data          TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'aberta',   -- aberta | concluida
    iniciada_em   TEXT NOT NULL,
    concluida_em  TEXT
);

CREATE TABLE IF NOT EXISTS sessao_item (
    id            INTEGER PRIMARY KEY,
    sessao_id     INTEGER NOT NULL REFERENCES sessao(id) ON DELETE CASCADE,
    topico_id     INTEGER NOT NULL REFERENCES topico(id) ON DELETE CASCADE,
    questao_id    INTEGER NOT NULL REFERENCES questao(id) ON DELETE CASCADE,
    ordem         INTEGER NOT NULL,
    resposta      TEXT,
    correta       INTEGER,
    invalidada    INTEGER NOT NULL DEFAULT 0,
    respondida_em TEXT
);
CREATE INDEX IF NOT EXISTS ix_item_sessao ON sessao_item(sessao_id, ordem);

CREATE TABLE IF NOT EXISTS revisao (
    id           INTEGER PRIMARY KEY,
    topico_id    INTEGER NOT NULL REFERENCES topico(id) ON DELETE CASCADE,
    sessao_id    INTEGER NOT NULL REFERENCES sessao(id) ON DELETE CASCADE,
    data         TEXT NOT NULL,
    etapa_antes  INTEGER NOT NULL,
    etapa_depois INTEGER NOT NULL,
    acertos      INTEGER NOT NULL,
    total        INTEGER NOT NULL,
    proxima      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS job (
    id            INTEGER PRIMARY KEY,
    tipo          TEXT NOT NULL,
    topico_id     INTEGER,
    payload_json  TEXT NOT NULL DEFAULT '{}',
    status        TEXT NOT NULL DEFAULT 'pendente',  -- pendente | rodando | ok | erro
    tentativas    INTEGER NOT NULL DEFAULT 0,
    erro          TEXT NOT NULL DEFAULT '',
    criado_em     TEXT NOT NULL,
    atualizado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS config (
    chave  TEXT PRIMARY KEY,
    valor  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS login_tentativa (
    id       INTEGER PRIMARY KEY,
    quando   TEXT NOT NULL,
    sucesso  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS login_sessao (
    token_hash  TEXT PRIMARY KEY,
    criado_em   TEXT NOT NULL
);
"""


def db_path() -> Path:
    return DATA_DIR / "zincrevise.db"


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # isolation_level=None: autocommit; transações só quando abertas com tx()
    conn = sqlite3.connect(db_path(), timeout=30, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def get_conn() -> sqlite3.Connection:
    """Uma conexão por thread."""
    conn = getattr(_local, "conn", None)
    if conn is None or getattr(_local, "path", None) != db_path():
        conn = connect()
        _local.conn = conn
        _local.path = db_path()
    return conn


def reset_thread_conn() -> None:
    conn = getattr(_local, "conn", None)
    if conn is not None:
        conn.close()
    _local.conn = None


@contextmanager
def tx():
    conn = get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


MIGRACOES = {
    "topico": {"assunto": "TEXT NOT NULL DEFAULT ''"},
    "materia": {"tema": "TEXT NOT NULL DEFAULT ''"},
    "sessao": {"teste": "INTEGER NOT NULL DEFAULT 0"},
    "login_tentativa": {"ip": "TEXT NOT NULL DEFAULT ''"},
    "questao": {"assunto": "TEXT NOT NULL DEFAULT ''", "tec_codigo": "TEXT NOT NULL DEFAULT ''",
                "tec_prova": "TEXT NOT NULL DEFAULT ''"},
}


def init_db() -> None:
    conn = get_conn()
    conn.executescript(SCHEMA)
    for tabela, colunas in MIGRACOES.items():
        existentes = {r["name"] for r in conn.execute(f"PRAGMA table_info({tabela})")}
        for nome, tipo in colunas.items():
            if nome not in existentes:
                conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {nome} {tipo}")
    for sub in ("imagens", "leis", "materiais", "tmp", "claude_work"):
        (DATA_DIR / sub).mkdir(parents=True, exist_ok=True)


def rows(sql: str, params=()) -> list[dict]:
    return [dict(r) for r in get_conn().execute(sql, params).fetchall()]


def row(sql: str, params=()) -> dict | None:
    r = get_conn().execute(sql, params).fetchone()
    return dict(r) if r else None


def hoje() -> date:
    override = os.environ.get("ZINC_HOJE")
    if override:
        return date.fromisoformat(override)
    return date.today()


def agora() -> str:
    return datetime.now().isoformat(timespec="seconds")
