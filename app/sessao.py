"""Sessão diária: montagem, respostas e fechamento com a regra adaptativa."""
from __future__ import annotations

import json
import math
import random
from datetime import date, timedelta

from . import db, srs
from .questoes import ids_vistos_recentes, questao_publica, srs_cfg


def sessao_aberta() -> dict | None:
    return db.row("SELECT * FROM sessao WHERE status = 'aberta' ORDER BY id LIMIT 1")


def topicos_vencidos(hoje: date | None = None) -> list[dict]:
    hoje = hoje or db.hoje()
    desde = (hoje - timedelta(days=30)).isoformat()
    return db.rows(
        """SELECT t.*, m.nome AS materia,
                  (julianday(?) - julianday(t.proxima_revisao)) AS atraso,
                  (SELECT COUNT(*) FROM sessao_item si JOIN sessao s ON s.id = si.sessao_id
                     WHERE si.topico_id = t.id AND si.correta = 0 AND si.invalidada = 0 AND s.data >= ?)
                + (SELECT COUNT(*) FROM questao q
                     WHERE q.topico_id = t.id AND q.resultado_no_tec = 'errou' AND q.criado_em >= ?) AS erros_recentes
           FROM topico t JOIN materia m ON m.id = t.materia_id
           WHERE t.proxima_revisao <= ?
           ORDER BY atraso DESC, erros_recentes DESC, t.id""",
        (hoje.isoformat(), desde, desde, hoje.isoformat()),
    )


def escolher_questoes(topico_id: int, n: int, proporcao_reais: int, rng: random.Random) -> list[int]:
    """Mira metade reais/metade geradas; reais erradas no Tec e menos vistas primeiro;
    evita as vistas nas últimas 2 revisões quando há alternativa."""
    qs = db.rows(
        "SELECT id, origem, resultado_no_tec, vezes_vista FROM questao WHERE topico_id = ? AND status = 'ativa'",
        (topico_id,),
    )
    if not qs:
        return []
    vistos = ids_vistos_recentes(topico_id)

    def ordenar(lista, reais: bool):
        rng.shuffle(lista)
        if reais:
            lista.sort(key=lambda q: (q["resultado_no_tec"] != "errou", q["vezes_vista"]))
        else:
            lista.sort(key=lambda q: q["vezes_vista"])
        frescas = [q for q in lista if q["id"] not in vistos]
        repetidas = [q for q in lista if q["id"] in vistos]
        return frescas + repetidas

    reais = ordenar([q for q in qs if q["origem"] == "real"], True)
    geradas = ordenar([q for q in qs if q["origem"] == "gerada"], False)
    alvo_reais = math.ceil(n * proporcao_reais / 100)
    alvo_geradas = n - alvo_reais

    def frescas(lista):
        return [q for q in lista if q["id"] not in vistos]

    # primeiro só questões frescas, respeitando a proporção; depois completa com o que houver
    escolhidas: list[dict] = []
    fr, fg = frescas(reais), frescas(geradas)
    escolhidas += fr[:alvo_reais]
    escolhidas += fg[:alvo_geradas]
    for lista in (fr, fg, reais, geradas):
        for q in lista:
            if len(escolhidas) >= n:
                break
            if q not in escolhidas:
                escolhidas.append(q)
    return [q["id"] for q in escolhidas[:n]]


def montar_sessao(rng: random.Random | None = None) -> dict:
    """Abre a sessão do dia com todos os tópicos vencidos. Se já houver uma aberta, devolve ela."""
    aberta = sessao_aberta()
    if aberta:
        return estado(aberta["id"])
    rng = rng or random.Random()
    cfg = srs_cfg()
    vencidos = topicos_vencidos()
    limite = int(cfg["limite_diario"] or 0)
    itens: list[tuple[int, int]] = []
    sem_questoes = []
    usados = 0
    for t in vencidos:
        if limite and usados >= limite:
            break
        n = srs.questoes_por_revisao(t["etapa"], cfg)
        ids = escolher_questoes(t["id"], n, int(cfg["proporcao_reais"]), rng)
        if not ids:
            sem_questoes.append(t["id"])
            continue
        itens += [(t["id"], qid) for qid in ids]
        usados += 1
    if not itens:
        return {"sessao": None, "sem_questoes": sem_questoes}
    rng.shuffle(itens)
    with db.tx() as conn:
        sid = conn.execute(
            "INSERT INTO sessao(data, iniciada_em) VALUES(?, ?)", (db.hoje().isoformat(), db.agora())
        ).lastrowid
        conn.executemany(
            "INSERT INTO sessao_item(sessao_id, topico_id, questao_id, ordem) VALUES(?, ?, ?, ?)",
            [(sid, tid, qid, i) for i, (tid, qid) in enumerate(itens)],
        )
    return estado(sid)


def estado(sessao_id: int) -> dict:
    s = db.row("SELECT * FROM sessao WHERE id = ?", (sessao_id,))
    if not s:
        return {"sessao": None}
    itens = db.rows(
        """SELECT si.*, t.nome AS topico, t.assunto AS topico_assunto, m.nome AS materia, q.*,
                  si.id AS item_id, q.id AS questao_id
           FROM sessao_item si
           JOIN questao q ON q.id = si.questao_id
           JOIN topico t ON t.id = si.topico_id
           JOIN materia m ON m.id = t.materia_id
           WHERE si.sessao_id = ? ORDER BY si.ordem""",
        (sessao_id,),
    )
    out = []
    for it in itens:
        respondida = it["resposta"] is not None
        q = questao_publica({**it, "id": it["questao_id"]}, com_gabarito=respondida or bool(it["invalidada"]))
        out.append({
            "item_id": it["item_id"], "topico_id": it["topico_id"], "topico": it["topico"], "materia": it["materia"],
            "assunto": it["assunto"] or it["topico_assunto"] or "",
            "resposta": it["resposta"], "correta": None if it["correta"] is None else bool(it["correta"]),
            "invalidada": bool(it["invalidada"]), "questao": q,
        })
    resumo = resumo_sessao(sessao_id) if s["status"] == "concluida" else None
    return {"sessao": s, "itens": out, "resumo": resumo}


def responder(item_id: int, resposta: str) -> dict:
    it = db.row(
        """SELECT si.*, s.status AS sessao_status FROM sessao_item si JOIN sessao s ON s.id = si.sessao_id
           WHERE si.id = ?""", (item_id,))
    if not it:
        raise ValueError("Item não encontrado.")
    if it["sessao_status"] != "aberta":
        raise ValueError("A sessão já foi concluída.")
    if it["resposta"] is not None:
        raise ValueError("Questão já respondida.")
    q = db.row("SELECT * FROM questao WHERE id = ?", (it["questao_id"],))
    resposta = resposta.strip().upper()[:1]
    correta = int(resposta == q["gabarito"])
    db.get_conn().execute(
        "UPDATE sessao_item SET resposta = ?, correta = ?, respondida_em = ? WHERE id = ?",
        (resposta, correta, db.agora(), item_id),
    )
    return {"correta": bool(correta), "questao": questao_publica(q)}


def pendentes(sessao_id: int) -> int:
    return db.row(
        "SELECT COUNT(*) AS n FROM sessao_item WHERE sessao_id = ? AND resposta IS NULL AND invalidada = 0",
        (sessao_id,),
    )["n"]


def concluir(sessao_id: int) -> dict:
    """Aplica a regra adaptativa a cada tópico da sessão e fecha a sessão."""
    s = db.row("SELECT * FROM sessao WHERE id = ?", (sessao_id,))
    if not s or s["status"] != "aberta":
        raise ValueError("Sessão não está aberta.")
    if pendentes(sessao_id):
        raise ValueError("Ainda há questões sem resposta.")
    cfg = srs_cfg()
    hoje = db.hoje()
    por_topico = db.rows(
        """SELECT si.topico_id, SUM(CASE WHEN si.invalidada = 0 THEN 1 ELSE 0 END) AS total,
                  SUM(CASE WHEN si.invalidada = 0 AND si.correta = 1 THEN 1 ELSE 0 END) AS acertos
           FROM sessao_item si WHERE si.sessao_id = ? GROUP BY si.topico_id""",
        (sessao_id,),
    )
    with db.tx() as conn:
        for p in por_topico:
            t = db.row("SELECT etapa, proxima_revisao FROM topico WHERE id = ?", (p["topico_id"],))
            if not p["total"]:
                continue  # todas invalidadas: o tópico continua vencido para a próxima sessão
            nova, proxima = srs.agendar(hoje, t["etapa"], p["acertos"], p["total"], cfg)
            conn.execute(
                "UPDATE topico SET etapa = ?, proxima_revisao = ?, ultima_revisao = ? WHERE id = ?",
                (nova, proxima.isoformat(), hoje.isoformat(), p["topico_id"]),
            )
            conn.execute(
                """INSERT INTO revisao(topico_id, sessao_id, data, etapa_antes, etapa_depois, acertos, total, proxima)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (p["topico_id"], sessao_id, hoje.isoformat(), t["etapa"], nova, p["acertos"], p["total"],
                 proxima.isoformat()),
            )
        conn.execute(
            """UPDATE questao SET vezes_vista = vezes_vista + 1
               WHERE id IN (SELECT questao_id FROM sessao_item WHERE sessao_id = ? AND invalidada = 0)""",
            (sessao_id,),
        )
        conn.execute("UPDATE sessao SET status = 'concluida', concluida_em = ? WHERE id = ?", (db.agora(), sessao_id))
    return estado(sessao_id)


def resumo_sessao(sessao_id: int) -> dict:
    revs = db.rows(
        """SELECT r.*, t.nome AS topico, m.nome AS materia FROM revisao r
           JOIN topico t ON t.id = r.topico_id JOIN materia m ON m.id = t.materia_id
           WHERE r.sessao_id = ? ORDER BY m.nome, t.nome""",
        (sessao_id,),
    )
    acertos = sum(r["acertos"] for r in revs)
    total = sum(r["total"] for r in revs)
    erradas = db.rows(
        """SELECT si.id AS item_id, si.resposta, q.id FROM sessao_item si JOIN questao q ON q.id = si.questao_id
           WHERE si.sessao_id = ? AND si.correta = 0 AND si.invalidada = 0 ORDER BY si.ordem""",
        (sessao_id,),
    )
    return {
        "topicos": revs, "acertos": acertos, "total": total,
        "pct": round(100 * acertos / total, 1) if total else 0,
        "erradas": [{"item_id": e["item_id"], "resposta": e["resposta"], "questao_id": e["id"]} for e in erradas],
    }


def proximos_dias(dias: int = 14) -> list[dict]:
    hoje = db.hoje()
    fim = (hoje + timedelta(days=dias)).isoformat()
    cont = {r["d"]: r["n"] for r in db.rows(
        "SELECT proxima_revisao AS d, COUNT(*) AS n FROM topico WHERE proxima_revisao > ? AND proxima_revisao <= ? "
        "GROUP BY proxima_revisao", (hoje.isoformat(), fim))}
    return [{"data": (hoje + timedelta(days=i)).isoformat(), "topicos": cont.get((hoje + timedelta(days=i)).isoformat(), 0)}
            for i in range(1, dias + 1)]


def _json(x):
    return json.dumps(x, ensure_ascii=False)
