"""Fila de jobs em SQLite + worker em thread para o botão "Gerar questões".

Modo assinatura: um tópico por vez, via `claude -p`.
Modo API: os tópicos pendentes vão juntos num lote da Batch API (50% de desconto).
"""
from __future__ import annotations

import json
import logging
import threading
import time
import traceback

from . import config, db, ia, leis
from .questoes import situacao_banco

log = logging.getLogger("zinc.jobs")

_acordar = threading.Event()
_parar = threading.Event()
_thread: threading.Thread | None = None

POLL_LOTE_SEG = 30


# ---------------------------------------------------------------------------
# Enfileirar
# ---------------------------------------------------------------------------

def topicos_com_novas() -> list[int]:
    return [r["topico_id"] for r in db.rows(
        "SELECT DISTINCT topico_id FROM questao WHERE origem = 'real' AND no_banco = 0 AND status = 'ativa'")]


def enfileirar_geracao(topico_id: int | None = None, modo: str | None = None,
                       quantidade: int | None = None) -> list[int]:
    alvos = [topico_id] if topico_id else topicos_com_novas()
    criados = []
    with db.tx() as conn:
        for tid in alvos:
            ja = db.row("SELECT id FROM job WHERE tipo = 'gerar_banco' AND topico_id = ? AND status IN ('pendente','rodando')",
                        (tid,))
            if ja:
                continue
            payload = {"modo": modo} if modo else {}
            if quantidade:
                payload["quantidade"] = max(1, min(int(quantidade), 50))
            criados.append(conn.execute(
                "INSERT INTO job(tipo, topico_id, payload_json, criado_em, atualizado_em) VALUES('gerar_banco', ?, ?, ?, ?)",
                (tid, json.dumps(payload), db.agora(), db.agora()),
            ).lastrowid)
    _acordar.set()
    return criados


def listar(ativos: bool = False) -> list[dict]:
    from datetime import datetime, timedelta

    corte = "9999" if ativos else (datetime.now() - timedelta(days=1)).isoformat(timespec="seconds")
    out = db.rows(
        """SELECT j.id, j.tipo, j.topico_id, j.status, j.erro, j.criado_em, j.atualizado_em, j.payload_json,
                  t.nome AS topico, m.nome AS materia
           FROM job j LEFT JOIN topico t ON t.id = j.topico_id LEFT JOIN materia m ON m.id = t.materia_id
           WHERE j.status IN ('pendente','rodando') OR j.atualizado_em >= ?
           ORDER BY j.id DESC LIMIT 50""", (corte,))
    for j in out:
        p = json.loads(j.pop("payload_json") or "{}")
        j["pode_tentar_api"] = bool(p.get("pode_tentar_api"))
        j["geradas"] = p.get("geradas")
    return out


# ---------------------------------------------------------------------------
# Contexto e aplicação do resultado
# ---------------------------------------------------------------------------

def montar_contexto(topico_id: int, quantidade: int | None = None) -> dict:
    t = db.row(
        """SELECT t.*, m.nome AS materia, m.lei_seca FROM topico t JOIN materia m ON m.id = t.materia_id
           WHERE t.id = ?""", (topico_id,))
    if not t:
        raise ValueError("Tópico não existe mais.")
    reais = db.rows(
        "SELECT * FROM questao WHERE topico_id = ? AND origem = 'real' AND status = 'ativa' ORDER BY id", (topico_id,))
    banco = situacao_banco(topico_id)
    minimo = int(config.get("minimo_geradas"))
    prop = int(config.get("proporcao_reais")) or 50
    # alvo de geradas para ficar perto da proporção (padrão 50/50), com um mínimo
    alvo_geradas = max(minimo, round(len(reais) * (100 - prop) / prop))
    n_gerar = max(0, alvo_geradas - banco["geradas"])
    if n_gerar == 0 and banco["banco_baixo"]:
        n_gerar = minimo
    n_gerar = min(n_gerar, 15)
    if quantidade:
        # quantidade escolhida no botão = total de questões que entram no banco nesta geração,
        # contando as reais novas (copiadas). Só a diferença é gerada pelo Claude.
        # Ex.: 5 reais novas e quantidade 15 -> copia as 5 e gera 10.
        n_gerar = max(0, min(int(quantidade), 50) - banco["novas"])
    conferir = [q["id"] for q in reais if q["gabarito_origem"] == "claude_provisorio"]
    material = db.row("SELECT texto FROM material_apoio WHERE topico_id = ? ORDER BY id DESC LIMIT 1", (topico_id,))
    return {
        "topico_id": topico_id,
        "materia": t["materia"],
        "topico": t["nome"],
        "lei_seca": bool(t["lei_seca"]),
        "dispositivo_ref": t["dispositivo_ref"],
        "texto_base": leis.texto_base_topico(topico_id),
        "material_apoio": (material["texto"][:30000] if material else ""),
        "estilo": config.get("estilo_banca"),
        "reais": [{"id": q["id"], "enunciado": q["enunciado"], "alternativas": json.loads(q["alternativas_json"]),
                   "gabarito": q["gabarito"]} for q in reais],
        "reais_ids": [q["id"] for q in reais],
        "conferir": conferir,
        "n_gerar": n_gerar,
    }


def aplicar_resultado(ctx: dict, res: dict | None) -> int:
    """Grava gabaritos conferidos e questões geradas; marca as reais como copiadas para o banco."""
    geradas = 0
    with db.tx() as conn:
        if res:
            conferiveis = set(ctx["conferir"])
            for g in res.get("gabaritos", []):
                if g.get("questao_id") in conferiveis and g.get("gabarito"):
                    conn.execute(
                        "UPDATE questao SET gabarito = ?, gabarito_origem = 'claude_conferido', justificativa = ? WHERE id = ?",
                        (str(g["gabarito"]).strip().upper()[:1], g.get("justificativa", ""), g["questao_id"]),
                    )
            fonte_ext = int(bool(res.get("fonte_externa")))
            for q in res.get("questoes", []):
                alts = [{"letra": str(a["letra"]).strip().upper()[:1], "texto": a["texto"].strip()}
                        for a in q.get("alternativas", []) if a.get("texto")]
                gab = str(q.get("gabarito", "")).strip().upper()[:1]
                if len(alts) < 2 or gab not in {a["letra"] for a in alts}:
                    continue
                conn.execute(
                    """INSERT INTO questao(topico_id, origem, enunciado, alternativas_json, gabarito, gabarito_origem,
                           justificativa, explicacoes_json, dispositivo_ref, trecho_base, fonte_externa, fontes,
                           no_banco, criado_em)
                       VALUES(?, 'gerada', ?, ?, ?, 'claude', ?, ?, ?, ?, ?, ?, 1, ?)""",
                    (ctx["topico_id"], q["enunciado"].strip(), json.dumps(alts, ensure_ascii=False), gab,
                     q.get("justificativa", ""), json.dumps(q.get("explicacoes_erradas", []), ensure_ascii=False),
                     q.get("dispositivo_ref", ""), q.get("trecho_base", ""), fonte_ext, res.get("fontes", ""),
                     db.agora()),
                )
                geradas += 1
        if ctx["reais_ids"]:
            marks = ",".join("?" * len(ctx["reais_ids"]))
            conn.execute(f"UPDATE questao SET no_banco = 1 WHERE id IN ({marks})", ctx["reais_ids"])
        conn.execute("UPDATE topico SET ultima_geracao = ? WHERE id = ?", (db.agora(), ctx["topico_id"]))
    return geradas


def _marcar(job_id: int, status: str, erro: str = "", extra: dict | None = None) -> None:
    j = db.row("SELECT payload_json FROM job WHERE id = ?", (job_id,))
    payload = json.loads(j["payload_json"] or "{}") if j else {}
    payload.update(extra or {})
    db.get_conn().execute(
        "UPDATE job SET status = ?, erro = ?, payload_json = ?, atualizado_em = ?, "
        "tentativas = tentativas + CASE WHEN ? = 'rodando' THEN 1 ELSE 0 END WHERE id = ?",
        (status, erro, json.dumps(payload), db.agora(), status, job_id),
    )


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------

def _precisa_ia(ctx: dict) -> bool:
    return ctx["n_gerar"] > 0 or bool(ctx["conferir"])


def processar_um(job: dict) -> None:
    payload = json.loads(job["payload_json"] or "{}")
    _marcar(job["id"], "rodando")
    try:
        ctx = montar_contexto(job["topico_id"], payload.get("quantidade"))
        res = ia.gerar_banco(ctx, modo=payload.get("modo")) if _precisa_ia(ctx) else None
        n = aplicar_resultado(ctx, res)
        _marcar(job["id"], "ok", extra={"geradas": n})
    except ia.ErroIA as e:
        _marcar(job["id"], "erro", str(e), {"pode_tentar_api": e.pode_tentar_api})
    except Exception as e:  # noqa: BLE001
        log.error("job %s falhou: %s", job["id"], traceback.format_exc())
        _marcar(job["id"], "erro", f"Erro interno: {e}")


def processar_lote_api(jobs: list[dict]) -> None:
    """Envia vários tópicos num lote da Batch API e espera o resultado."""
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    ctxs: dict[int, dict] = {}
    requisicoes = []
    for j in jobs:
        _marcar(j["id"], "rodando")
        try:
            ctx = montar_contexto(j["topico_id"], json.loads(j["payload_json"] or "{}").get("quantidade"))
        except Exception as e:  # noqa: BLE001
            _marcar(j["id"], "erro", str(e))
            continue
        if not _precisa_ia(ctx):
            n = aplicar_resultado(ctx, None)
            _marcar(j["id"], "ok", extra={"geradas": n})
            continue
        ctxs[j["id"]] = ctx
        requisicoes.append(Request(custom_id=f"job-{j['id']}",
                                   params=MessageCreateParamsNonStreaming(**ia.params_lote_gerar(ctx))))
    if not requisicoes:
        return
    try:
        client = ia._cliente_api()
        lote = client.messages.batches.create(requests=requisicoes)
        for jid in ctxs:
            _marcar(jid, "rodando", extra={"lote": lote.id})
        while not _parar.is_set():
            b = client.messages.batches.retrieve(lote.id)
            if b.processing_status == "ended":
                break
            _parar.wait(POLL_LOTE_SEG)
        if _parar.is_set():
            return
        for r in client.messages.batches.results(lote.id):
            jid = int(r.custom_id.split("-")[1])
            ctx = ctxs.get(jid)
            if ctx is None:
                continue
            if r.result.type == "succeeded":
                try:
                    res = ia.ler_resultado_lote(r.result.message)
                    n = aplicar_resultado(ctx, res)
                    _marcar(jid, "ok", extra={"geradas": n})
                except ia.ErroIA as e:
                    _marcar(jid, "erro", str(e))
            else:
                _marcar(jid, "erro", f"Lote: {r.result.type}")
    except ia.ErroIA as e:
        for jid in ctxs:
            _marcar(jid, "erro", str(e))
    except Exception as e:  # noqa: BLE001
        log.error("lote falhou: %s", traceback.format_exc())
        for jid in ctxs:
            _marcar(jid, "erro", f"Erro no lote: {e}")


def ciclo() -> bool:
    """Processa o que houver pendente. Retorna True se fez algo."""
    pend = db.rows("SELECT * FROM job WHERE status = 'pendente' AND tipo = 'gerar_banco' ORDER BY id")
    if not pend:
        return False
    modo_padrao = ia.modo_atual()
    via_api = [j for j in pend if (json.loads(j["payload_json"] or "{}").get("modo") or modo_padrao) == "api"]
    via_assinatura = [j for j in pend if j not in via_api]
    if len(via_api) > 1:
        processar_lote_api(via_api)
    else:
        via_assinatura = via_api + via_assinatura
    for j in via_assinatura:
        if _parar.is_set():
            break
        processar_um(j)
    return True


def _loop() -> None:
    db.get_conn()
    # jobs interrompidos por reinício voltam para a fila
    db.get_conn().execute("UPDATE job SET status = 'pendente' WHERE status = 'rodando'")
    while not _parar.is_set():
        try:
            fez = ciclo()
        except Exception:  # noqa: BLE001
            log.error("worker: %s", traceback.format_exc())
            fez = False
        if not fez:
            _acordar.wait(5)
            _acordar.clear()


def iniciar_worker() -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    _parar.clear()
    _thread = threading.Thread(target=_loop, name="zinc-worker", daemon=True)
    _thread.start()


def parar_worker() -> None:
    _parar.set()
    _acordar.set()
