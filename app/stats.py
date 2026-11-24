"""Estatísticas no estilo do TecConcursos: desempenho geral, por matéria e assunto, evolução diária."""
from __future__ import annotations

import re
from datetime import date, timedelta

from . import db

STOP = {"de", "da", "do", "das", "dos", "e", "a", "o", "em", "para"}


def sigla_materia(nome: str) -> str:
    """"Direito Processual Civil" -> "DPC"; "Língua Portuguesa" -> "LP"."""
    base = re.sub(r"\(.*?\)", "", nome)
    palavras = [p for p in re.split(r"[\s\-–/]+", base) if p and p.lower() not in STOP]
    if not palavras:
        return nome[:4].upper()
    if len(palavras) == 1:
        return palavras[0][:4].upper()
    return "".join(p[0] for p in palavras).upper()[:5]


def _respostas(inicio: str, fim: str, fonte: str, origem: str, materias: list[int]) -> list[dict]:
    filtro_mat = ""
    params_mat: tuple = ()
    if materias:
        filtro_mat = f" AND m.id IN ({','.join('?' * len(materias))})"
        params_mat = tuple(materias)
    filtro_origem = "" if origem not in ("real", "gerada") else " AND q.origem = ?"
    params_origem: tuple = () if not filtro_origem else (origem,)
    out: list[dict] = []
    if fonte in ("app", "ambos"):
        out += db.rows(
            f"""SELECT substr(si.respondida_em, 1, 10) AS dia, si.correta AS correta,
                       m.id AS materia_id, m.nome AS materia, t.id AS topico_id, t.nome AS topico,
                       COALESCE(NULLIF(q.assunto, ''), NULLIF(t.assunto, ''), t.nome) AS assunto
                FROM sessao_item si
                JOIN questao q ON q.id = si.questao_id
                JOIN topico t ON t.id = si.topico_id
                JOIN materia m ON m.id = t.materia_id
                WHERE si.resposta IS NOT NULL AND si.invalidada = 0 AND q.status = 'ativa'
                  AND substr(si.respondida_em, 1, 10) BETWEEN ? AND ?{filtro_mat}{filtro_origem}""",
            (inicio, fim, *params_mat, *params_origem),
        )
    if fonte in ("tec", "ambos") and origem != "gerada":
        out += db.rows(
            f"""SELECT substr(q.criado_em, 1, 10) AS dia,
                       CASE q.resultado_no_tec WHEN 'acertou' THEN 1 ELSE 0 END AS correta,
                       m.id AS materia_id, m.nome AS materia, t.id AS topico_id, t.nome AS topico,
                       COALESCE(NULLIF(q.assunto, ''), NULLIF(t.assunto, ''), t.nome) AS assunto
                FROM questao q
                JOIN topico t ON t.id = q.topico_id
                JOIN materia m ON m.id = t.materia_id
                WHERE q.origem = 'real' AND q.resultado_no_tec IN ('acertou', 'errou')
                  AND substr(q.criado_em, 1, 10) BETWEEN ? AND ?{filtro_mat}""",
            (inicio, fim, *params_mat),
        )
    return out


def _agg(lista: list[dict]) -> dict:
    total = len(lista)
    acertos = sum(1 for r in lista if r["correta"])
    return {"resolvidas": total, "acertos": acertos, "erros": total - acertos,
            "pct": round(100 * acertos / total, 2) if total else 0.0}


def estatisticas(inicio: str | None, fim: str | None, fonte: str = "app", origem: str = "todas",
                 materias: list[int] | None = None) -> dict:
    hoje = db.hoje()
    fim = fim or hoje.isoformat()
    inicio = inicio or (hoje - timedelta(days=30)).isoformat()
    resp = _respostas(inicio, fim, fonte, origem, materias or [])

    por_mat: dict[int, dict] = {}
    for r in resp:
        m = por_mat.setdefault(r["materia_id"], {"id": r["materia_id"], "nome": r["materia"], "linhas": [], "topicos": {}})
        m["linhas"].append(r)
        m["topicos"].setdefault(r["assunto"], {"id": r["topico_id"], "nome": r["assunto"], "linhas": []})["linhas"].append(r)

    materias_out = []
    for m in sorted(por_mat.values(), key=lambda x: x["nome"]):
        topicos = [{"id": t["id"], "nome": t["nome"], **_agg(t["linhas"])}
                   for t in sorted(m["topicos"].values(), key=lambda x: _ordem_natural(x["nome"]))]
        materias_out.append({"id": m["id"], "nome": m["nome"], "sigla": sigla_materia(m["nome"]),
                             **_agg(m["linhas"]), "topicos": topicos})

    # evolução diária
    dias = []
    d0, d1 = date.fromisoformat(inicio), date.fromisoformat(fim)
    por_dia: dict[str, list] = {}
    for r in resp:
        por_dia.setdefault(r["dia"], []).append(r)
    d = d0
    while d <= d1 and len(dias) < 400:
        dias.append({"dia": d.isoformat(), **_agg(por_dia.get(d.isoformat(), []))})
        d += timedelta(days=1)

    return {
        "periodo": {"inicio": inicio, "fim": fim},
        "geral": {**_agg(resp), "total_materias": len(materias_out)},
        "materias": materias_out,
        "dias": dias,
        "revisao": situacao_revisao(),
    }


def situacao_revisao() -> dict:
    hoje = db.hoje().isoformat()
    etapas = db.rows("SELECT etapa, COUNT(*) AS n FROM topico GROUP BY etapa ORDER BY etapa")
    tot = db.row("SELECT COUNT(*) AS n, SUM(CASE WHEN proxima_revisao <= ? THEN 1 ELSE 0 END) AS vencidos FROM topico",
                 (hoje,))
    return {"etapas": etapas, "topicos": tot["n"] or 0, "vencidos": tot["vencidos"] or 0}


def _ordem_natural(s: str):
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", s)]


def lista_materias() -> list[dict]:
    return [{"id": m["id"], "nome": m["nome"], "sigla": sigla_materia(m["nome"])}
            for m in db.rows("SELECT id, nome FROM materia ORDER BY nome")]
