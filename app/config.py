"""Configurações do usuário, guardadas na tabela config."""
from __future__ import annotations

import json
from typing import Any

from . import db

ESTILO_VUNESP = """Banca: Vunesp (TJSP – Escrevente Técnico Judiciário).
- 5 alternativas (A a E), exatamente uma correta.
- Redação próxima da literalidade da lei.
- Pegadinhas típicas: troca de verbo modal ("poderá" ↔ "deverá"); "permitido" ↔ "vedado", "salvo" ↔ "inclusive"; prazos, quóruns e números trocados; competência atribuída ao órgão errado; exceção apresentada como regra.
- Enunciados curtos e diretos, no padrão "Assinale a alternativa correta" ou "De acordo com ..., é correto afirmar que"."""

DEFAULTS: dict[str, Any] = {
    "modo_ia": "assinatura",          # assinatura | api
    "api_key": "",
    "claude_bin": "",
    "modelos": {
        "ler": {"modelo": "claude-haiku-5-5", "esforco": "low"},
        "reler": {"modelo": "claude-sonnet-5-5", "esforco": "low"},
        "gerar": {"modelo": "claude-opus-5-5", "esforco": "medium"},
        "explicar": {"modelo": "claude-sonnet-5-5", "esforco": "high"},
    },
    "intervalos": [1, 3, 7, 15, 30, 60],
    "intervalo_manutencao": 30,
    "limiar_avancar": 80,
    "limiar_repetir": 50,
    "questoes_primeira": 3,
    "questoes_demais": 5,
    "proporcao_reais": 50,
    "minimo_geradas": 5,
    "limiar_banco_baixo": 6,
    "limite_diario": 0,               # 0 = sem limite
    "modo_teste_sessao": False,       # sessão com todas as questões, sem mexer na revisão
    "estilo_banca": ESTILO_VUNESP,
}

SECRET_KEYS = {"api_key", "senha_hash"}


def get(chave: str) -> Any:
    r = db.row("SELECT valor FROM config WHERE chave = ?", (chave,))
    if r is None:
        return DEFAULTS.get(chave)
    return json.loads(r["valor"])


def set(chave: str, valor: Any) -> None:  # noqa: A001
    db.get_conn().execute(
        "INSERT INTO config(chave, valor) VALUES(?, ?) "
        "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
        (chave, json.dumps(valor, ensure_ascii=False)),
    )


def todas_publicas() -> dict:
    out = {k: get(k) for k in DEFAULTS}
    key = out.pop("api_key") or ""
    out["api_key_mascarada"] = mascarar(key)
    out["api_key_configurada"] = bool(key)
    return out


def mascarar(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 12:
        return "…" + key[-2:]
    return f"{key[:7]}…{key[-4:]}"


def modelo_da_tarefa(tarefa: str) -> tuple[str, str]:
    modelos = get("modelos") or {}
    m = modelos.get(tarefa) or DEFAULTS["modelos"][tarefa]
    return m["modelo"], m["esforco"]
