"""Senha de acesso, bloqueio após tentativas erradas e sessões de login."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from . import config, db

SENHA_PADRAO = "9993"
MAX_TENTATIVAS = 3
BLOQUEIO = timedelta(hours=1)
COOKIE = "zinc_sessao"

_ph = PasswordHasher()


def garantir_senha() -> None:
    if not config.get("senha_hash"):
        config.set("senha_hash", _ph.hash(SENHA_PADRAO))


def bloqueado_ate(ip: str = "") -> datetime | None:
    """Bloqueio por endereço de acesso: 3 falhas seguidas daquele endereço bloqueiam ele por 1 h.
    Assim, alguém tentando senhas pela internet não tranca os seus aparelhos."""
    ult = db.rows(
        "SELECT quando, sucesso FROM login_tentativa WHERE ip = ? ORDER BY id DESC LIMIT ?",
        (ip, MAX_TENTATIVAS),
    )
    if len(ult) < MAX_TENTATIVAS or any(t["sucesso"] for t in ult):
        return None
    fim = datetime.fromisoformat(ult[0]["quando"]) + BLOQUEIO
    return fim if fim > datetime.now() else None


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def login(senha: str, ip: str = "") -> str | None:
    """Retorna o token de sessão, ou None se a senha estiver errada."""
    ok = False
    try:
        ok = _ph.verify(config.get("senha_hash"), senha)
    except (VerifyMismatchError, InvalidHashError):
        ok = False
    conn = db.get_conn()
    conn.execute(
        "INSERT INTO login_tentativa(quando, sucesso, ip) VALUES(?, ?, ?)", (db.agora(), int(ok), ip)
    )
    if not ok:
        return None
    token = secrets.token_urlsafe(32)
    conn.execute(
        "INSERT INTO login_sessao(token_hash, criado_em) VALUES(?, ?)",
        (_hash_token(token), db.agora()),
    )
    return token


def valido(token: str | None) -> bool:
    if not token:
        return False
    return db.row("SELECT 1 FROM login_sessao WHERE token_hash = ?", (_hash_token(token),)) is not None


def logout(token: str | None) -> None:
    if token:
        db.get_conn().execute("DELETE FROM login_sessao WHERE token_hash = ?", (_hash_token(token),))


def trocar_senha(atual: str, nova: str) -> bool:
    try:
        _ph.verify(config.get("senha_hash"), atual)
    except (VerifyMismatchError, InvalidHashError):
        return False
    config.set("senha_hash", _ph.hash(nova))
    db.get_conn().execute("DELETE FROM login_sessao")  # desloga todos os dispositivos
    return True
