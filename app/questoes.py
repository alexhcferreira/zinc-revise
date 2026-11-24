"""Cadastro de questões reais, tópicos e situação do banco."""
from __future__ import annotations

import json
import re
import shutil
from datetime import timedelta
from pathlib import Path

from . import config, db, leis


def srs_cfg() -> dict:
    return {k: config.get(k) for k in (
        "intervalos", "intervalo_manutencao", "limiar_avancar", "limiar_repetir",
        "questoes_primeira", "questoes_demais", "proporcao_reais", "minimo_geradas",
        "limiar_banco_baixo", "limite_diario",
    )}


def migrar_assuntos() -> None:
    """Uma vez só: o tópico de revisão passa a ser o Assunto do Tec, e cada matéria ganha um Tema."""
    if config.get("migr_assunto_v1"):
        return
    with db.tx() as conn:
        for m in db.rows("SELECT id, nome FROM materia WHERE tema = ''"):
            conn.execute("UPDATE materia SET tema = ? WHERE id = ?", (tema_padrao(m["nome"]), m["id"]))
        for t in db.rows("SELECT id, materia_id, nome, assunto FROM topico WHERE assunto != '' AND nome != assunto"):
            alvo = db.row("SELECT id FROM topico WHERE materia_id = ? AND lower(nome) = lower(?) AND id != ?",
                          (t["materia_id"], t["assunto"], t["id"]))
            if alvo:
                for tabela in ("questao", "sessao_item", "revisao", "material_apoio"):
                    conn.execute(f"UPDATE {tabela} SET topico_id = ? WHERE topico_id = ?", (alvo["id"], t["id"]))
                conn.execute("DELETE FROM topico WHERE id = ?", (t["id"],))
            else:
                conn.execute("UPDATE topico SET nome = assunto WHERE id = ?", (t["id"],))
    config.set("migr_assunto_v1", True)


def contexto_leitura() -> dict:
    return {
        "materias": [m["nome"] for m in db.rows("SELECT nome FROM materia ORDER BY nome")],
        "topicos": [f"{t['tema'] or '—'} › {t['materia']} › {t['nome']}" for t in db.rows(
            "SELECT m.tema, m.nome AS materia, t.nome FROM topico t JOIN materia m ON m.id = t.materia_id "
            "ORDER BY m.tema, m.nome, t.nome")],
        "leis": [f"{l['sigla']} – {l['nome']}" + (f" (também: {l['apelidos']})" if l["apelidos"] else "")
                 for l in db.rows("SELECT sigla, nome, apelidos FROM lei ORDER BY sigla")],
    }


def tema_padrao(materia: str) -> str:
    return re.sub(r"\s*\(.*\)\s*$", "", materia).strip()


def obter_ou_criar_materia(nome: str, lei_seca: bool, tema: str = "") -> int:
    nome = nome.strip() or "Sem matéria"
    tema = tema.strip() or tema_padrao(nome)
    m = db.row("SELECT id, tema FROM materia WHERE lower(nome) = lower(?)", (nome,))
    if m:
        if not m["tema"]:
            db.get_conn().execute("UPDATE materia SET tema = ? WHERE id = ?", (tema, m["id"]))
        return m["id"]
    return db.get_conn().execute(
        "INSERT INTO materia(nome, lei_seca, tema) VALUES(?, ?, ?)", (nome, int(lei_seca), tema)
    ).lastrowid


def obter_ou_criar_topico(materia_id: int, nome: str, dispositivo_ref: str, assunto: str = "") -> tuple[int, bool]:
    nome = nome.strip() or "Geral"
    t = db.row("SELECT id FROM topico WHERE materia_id = ? AND lower(nome) = lower(?)", (materia_id, nome))
    if t:
        if assunto.strip():
            db.get_conn().execute("UPDATE topico SET assunto = ? WHERE id = ? AND assunto = ''", (assunto.strip(), t["id"]))
        return t["id"], False
    amanha = (db.hoje() + timedelta(days=1)).isoformat()
    tid = db.get_conn().execute(
        "INSERT INTO topico(materia_id, nome, dispositivo_ref, assunto, proxima_revisao, criado_em) VALUES(?,?,?,?,?,?)",
        (materia_id, nome, dispositivo_ref.strip(), assunto.strip(), amanha, db.agora()),
    ).lastrowid
    return tid, True


def _alternativas_validas(alts: list) -> list[dict]:
    out = []
    for a in alts or []:
        letra = str(a.get("letra", "")).strip().upper()[:1]
        texto = str(a.get("texto", "")).strip()
        if letra and texto:
            out.append({"letra": letra, "texto": texto})
    return out


def salvar_real(d: dict) -> dict:
    """Salva a questão confirmada no cartão. Aplica a regra de novo erro no Tec (volta para a etapa 0)."""
    alternativas = _alternativas_validas(d.get("alternativas"))
    if not d.get("enunciado", "").strip() or len(alternativas) < 2:
        raise ValueError("A questão precisa de enunciado e de pelo menos duas alternativas.")
    situacao = d.get("situacao") if d.get("situacao") in ("acertou", "errou", "nao_respondeu") else "nao_respondeu"
    gabarito = str(d.get("gabarito", "")).strip().upper()[:1]
    marcada = str(d.get("marcada", "")).strip().upper()[:1] if situacao != "nao_respondeu" else ""
    if d.get("gabarito_editado"):
        origem_gab = "usuario"
    elif situacao == "nao_respondeu":
        origem_gab = "claude_provisorio"
    else:
        origem_gab = "print"

    with db.tx() as conn:
        if d.get("topico_id"):
            t = db.row("SELECT id, materia_id FROM topico WHERE id = ?", (d["topico_id"],))
            if not t:
                raise ValueError("Tópico não encontrado.")
            topico_id, novo = t["id"], False
        else:
            materia_id = obter_ou_criar_materia(d.get("materia", ""), bool(d.get("lei_seca", True)), d.get("tema", ""))
            assunto = (d.get("assunto") or d.get("topico") or "").strip()
            topico_id, novo = obter_ou_criar_topico(materia_id, assunto, d.get("dispositivo_ref", ""), assunto)

        imagem_path = ""
        up = d.get("upload_id")
        if up:
            origem = next((p for p in (db.DATA_DIR / "tmp").glob(f"{Path(up).name}.*")), None)
            if origem:
                destino = db.DATA_DIR / "imagens" / origem.name
                shutil.move(origem, destino)
                imagem_path = destino.name

        qid = conn.execute(
            """INSERT INTO questao(topico_id, origem, enunciado, alternativas_json, gabarito, gabarito_origem,
                   dispositivo_ref, marcada_no_tec, resultado_no_tec, imagem_path, assunto, tec_codigo, tec_prova,
                   criado_em)
               VALUES(?, 'real', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (topico_id, d["enunciado"].strip(), json.dumps(alternativas, ensure_ascii=False), gabarito,
             origem_gab, d.get("dispositivo_ref", "").strip(), marcada, situacao, imagem_path,
             str(d.get("assunto", "")).strip(), str(d.get("tec_codigo", "")).strip().lstrip("#"),
             str(d.get("tec_prova", "")).strip(), db.agora()),
        ).lastrowid

        voltou = False
        if not novo and situacao == "errou":
            amanha = (db.hoje() + timedelta(days=1)).isoformat()
            conn.execute(
                "UPDATE topico SET etapa = 0, proxima_revisao = min(proxima_revisao, ?) WHERE id = ?",
                (amanha, topico_id),
            )
            voltou = True
    leis.ligar_topico(topico_id)
    return {"questao_id": qid, "topico_id": topico_id, "topico_novo": novo, "voltou_etapa_0": voltou}


def ids_vistos_recentes(topico_id: int, n_revisoes: int = 2) -> set[int]:
    sessoes = [r["sessao_id"] for r in db.rows(
        "SELECT sessao_id FROM revisao WHERE topico_id = ? ORDER BY id DESC LIMIT ?", (topico_id, n_revisoes))]
    if not sessoes:
        return set()
    marks = ",".join("?" * len(sessoes))
    return {r["questao_id"] for r in db.rows(
        f"SELECT questao_id FROM sessao_item WHERE topico_id = ? AND sessao_id IN ({marks})",
        (topico_id, *sessoes))}


def situacao_banco(topico_id: int) -> dict:
    qs = db.rows("SELECT id, origem, no_banco FROM questao WHERE topico_id = ? AND status = 'ativa'", (topico_id,))
    vistos = ids_vistos_recentes(topico_id)
    reais = sum(1 for q in qs if q["origem"] == "real")
    geradas = sum(1 for q in qs if q["origem"] == "gerada")
    novas = sum(1 for q in qs if q["origem"] == "real" and not q["no_banco"])
    frescas = sum(1 for q in qs if q["id"] not in vistos)
    return {
        "reais": reais, "geradas": geradas, "novas": novas, "frescas": frescas,
        "banco_baixo": frescas < int(config.get("limiar_banco_baixo")),
    }


def questao_publica(q: dict, com_gabarito: bool = True) -> dict:
    out = {
        "id": q["id"], "topico_id": q["topico_id"], "origem": q["origem"], "enunciado": q["enunciado"],
        "alternativas": json.loads(q["alternativas_json"]), "dispositivo_ref": q["dispositivo_ref"],
        "status": q["status"], "resultado_no_tec": q["resultado_no_tec"], "marcada_no_tec": q["marcada_no_tec"],
        "imagem": q["imagem_path"], "fonte_externa": bool(q["fonte_externa"]), "fontes": q["fontes"],
        "gabarito_origem": q["gabarito_origem"], "no_banco": bool(q["no_banco"]), "criado_em": q["criado_em"],
        "vezes_vista": q["vezes_vista"],
        "assunto": q.get("assunto", ""), "tec_codigo": q.get("tec_codigo", ""), "tec_prova": q.get("tec_prova", ""),
    }
    if com_gabarito:
        out.update({
            "gabarito": q["gabarito"], "justificativa": q["justificativa"],
            "explicacoes": json.loads(q["explicacoes_json"] or "[]"), "trecho_base": q["trecho_base"],
            "explicacao_detalhada": q["explicacao_detalhada"], "motivo_invalidacao": q["motivo_invalidacao"],
        })
    return out


def invalidar(questao_id: int, motivo: str) -> None:
    with db.tx() as conn:
        conn.execute("UPDATE questao SET status = 'invalidada', motivo_invalidacao = ? WHERE id = ?",
                     (motivo or "", questao_id))
        # na sessão aberta, a questão deixa de contar
        conn.execute(
            """UPDATE sessao_item SET invalidada = 1
               WHERE questao_id = ? AND sessao_id IN (SELECT id FROM sessao WHERE status = 'aberta')""",
            (questao_id,),
        )
