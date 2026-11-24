"""ZincRevise – servidor FastAPI. Escuta só em 127.0.0.1; o acesso de fora é pelo `tailscale serve`."""
from __future__ import annotations

import json
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import auth, config, db, ia, jobs, leis, questoes, sessao, stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

STATIC = db.BASE_DIR / "static"
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
MAX_UPLOAD = 40 * 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    auth.garantir_senha()
    questoes.migrar_assuntos()
    jobs.iniciar_worker()
    yield
    jobs.parar_worker()


app = FastAPI(title="ZincRevise", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

LIVRES = {"/api/auth", "/api/login"}


@app.middleware("http")
async def exigir_login(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/") and path not in LIVRES:
        if not auth.valido(request.cookies.get(auth.COOKIE)):
            return JSONResponse({"erro": "Não autenticado."}, status_code=401)
    resp = await call_next(request)
    if path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


@app.exception_handler(ia.ErroIA)
async def erro_ia(_: Request, e: ia.ErroIA):
    return JSONResponse({"erro": str(e), "pode_tentar_api": e.pode_tentar_api}, status_code=502)


@app.exception_handler(ValueError)
async def erro_valor(_: Request, e: ValueError):
    return JSONResponse({"erro": str(e)}, status_code=400)


def _json_body(request_body: bytes) -> dict:
    try:
        return json.loads(request_body or b"{}")
    except json.JSONDecodeError:
        raise ValueError("JSON inválido.")


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@app.get("/api/auth")
def estado_auth(request: Request):
    ate = auth.bloqueado_ate()
    return {"logado": auth.valido(request.cookies.get(auth.COOKIE)),
            "bloqueado_ate": ate.isoformat(timespec="minutes") if ate else None}


@app.post("/api/login")
async def login(request: Request):
    body = _json_body(await request.body())
    ate = auth.bloqueado_ate()
    if ate:
        return JSONResponse({"erro": f"Login bloqueado até {ate.strftime('%H:%M')}."}, status_code=429)
    token = auth.login(str(body.get("senha", "")))
    if not token:
        ate = auth.bloqueado_ate()
        msg = f"Senha errada. Login bloqueado até {ate.strftime('%H:%M')}." if ate else "Senha errada."
        return JSONResponse({"erro": msg}, status_code=401)
    resp = JSONResponse({"ok": True})
    resp.set_cookie(auth.COOKIE, token, max_age=10 * 365 * 24 * 3600, httponly=True, secure=True,
                    samesite="strict", path="/")
    return resp


@app.post("/api/logout")
def logout(request: Request):
    auth.logout(request.cookies.get(auth.COOKIE))
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(auth.COOKIE, path="/")
    return resp


@app.post("/api/senha")
async def trocar_senha(request: Request):
    body = _json_body(await request.body())
    nova = str(body.get("nova", ""))
    if len(nova) < 4:
        raise ValueError("A senha nova precisa ter pelo menos 4 caracteres.")
    if not auth.trocar_senha(str(body.get("atual", "")), nova):
        raise ValueError("Senha atual errada.")
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(auth.COOKIE, path="/")
    return resp


# ---------------------------------------------------------------------------
# Painel
# ---------------------------------------------------------------------------

@app.get("/api/painel")
def painel():
    teste = sessao.modo_teste()
    vencidos = sessao.topicos_com_questoes() if teste else sessao.topicos_vencidos()
    sem_questoes, com_questoes = [], []
    for t in vencidos:
        n = db.row("SELECT COUNT(*) AS n FROM questao WHERE topico_id = ? AND status = 'ativa'", (t["id"],))["n"]
        (com_questoes if n else sem_questoes).append({"id": t["id"], "nome": t["nome"], "materia": t["materia"]})
    baixos = []
    for t in db.rows("SELECT t.id, t.nome, m.nome AS materia FROM topico t JOIN materia m ON m.id = t.materia_id"):
        b = questoes.situacao_banco(t["id"])
        if b["banco_baixo"]:
            baixos.append({**t, **b})
    aberta = sessao.sessao_aberta()
    progresso = None
    if aberta:
        tot = db.row("SELECT COUNT(*) AS n, SUM(resposta IS NOT NULL OR invalidada = 1) AS r FROM sessao_item "
                     "WHERE sessao_id = ?", (aberta["id"],))
        progresso = {"total": tot["n"], "respondidas": tot["r"] or 0, "data": aberta["data"]}
    limite = 0 if teste else int(config.get("limite_diario") or 0)
    return {
        "hoje": db.hoje().isoformat(),
        "modo_teste": teste,
        "modelos": config.get("modelos"),
        "vencidos": com_questoes,
        "vencidos_na_sessao": len(com_questoes[:limite]) if limite else len(com_questoes),
        "sem_questoes": sem_questoes,
        "banco_baixo": baixos,
        "topicos_com_novas": len(jobs.topicos_com_novas()),
        "sessao_aberta": progresso,
        "proximos": sessao.proximos_dias(14),
        "jobs": jobs.listar(ativos=True),
        "totais": db.row("SELECT (SELECT COUNT(*) FROM topico) AS topicos, "
                         "(SELECT COUNT(*) FROM questao WHERE status='ativa') AS questoes, "
                         "(SELECT COUNT(*) FROM lei) AS leis"),
    }


# ---------------------------------------------------------------------------
# Cadastro de questões
# ---------------------------------------------------------------------------

@app.post("/api/ler")
async def ler(texto: str = Form(""), imagem: UploadFile | None = File(None), upload_id: str = Form(""),
              reler: bool = Form(False), modo: str = Form("")):
    caminho = None
    if imagem is not None and imagem.filename:
        ext = Path(imagem.filename).suffix.lower() or ".png"
        if ext not in IMG_EXT:
            raise ValueError("Formato de imagem não suportado.")
        dados = await imagem.read()
        if len(dados) > MAX_UPLOAD:
            raise ValueError("Imagem grande demais.")
        upload_id = uuid.uuid4().hex
        caminho = db.DATA_DIR / "tmp" / f"{upload_id}{ext}"
        caminho.write_bytes(dados)
    elif upload_id:
        upload_id = Path(upload_id).name
        caminho = next((p for p in (db.DATA_DIR / "tmp").glob(f"{upload_id}.*")), None)
        if caminho is None:
            raise ValueError("O print expirou. Cole de novo.")
    if caminho is None and not texto.strip():
        raise ValueError("Cole um print ou o texto da questão.")
    import anyio

    resultado = await anyio.to_thread.run_sync(
        lambda: ia.ler_questao(texto or None, caminho, questoes.contexto_leitura(), reler=reler,
                               modo=modo or None))
    resultado["upload_id"] = upload_id if caminho else ""
    resultado["por_texto"] = caminho is None
    # sugere tópico existente com o mesmo nome
    t = db.row("""SELECT t.id FROM topico t JOIN materia m ON m.id = t.materia_id
                  WHERE lower(m.nome) = lower(?) AND lower(t.nome) = lower(?)""",
               (resultado.get("materia", ""), resultado.get("topico", "")))
    resultado["topico_existente_id"] = t["id"] if t else None
    return resultado


@app.post("/api/questoes")
async def salvar_questao(request: Request):
    return questoes.salvar_real(_json_body(await request.body()))


@app.delete("/api/questoes/{qid}")
def apagar_questao(qid: int):
    q = db.row("SELECT origem, imagem_path FROM questao WHERE id = ?", (qid,))
    if not q:
        raise HTTPException(404)
    if q["origem"] != "real":
        raise ValueError("Questões geradas são invalidadas, não apagadas.")
    db.get_conn().execute("DELETE FROM questao WHERE id = ?", (qid,))
    if q["imagem_path"]:
        (db.DATA_DIR / "imagens" / q["imagem_path"]).unlink(missing_ok=True)
    return {"ok": True}


@app.get("/api/questoes/{qid}")
def ver_questao(qid: int):
    q = db.row("SELECT * FROM questao WHERE id = ?", (qid,))
    if not q:
        raise HTTPException(404)
    return questoes.questao_publica(q)


@app.post("/api/questoes/{qid}/invalidar")
async def invalidar(qid: int, request: Request):
    body = _json_body(await request.body())
    questoes.invalidar(qid, str(body.get("motivo", "")))
    return {"ok": True}


@app.post("/api/questoes/{qid}/explicar")
async def explicar(qid: int, request: Request):
    body = _json_body(await request.body())
    q = db.row("SELECT * FROM questao WHERE id = ?", (qid,))
    if not q:
        raise HTTPException(404)
    if q["explicacao_detalhada"] and not body.get("refazer"):
        return {"texto": q["explicacao_detalhada"]}
    pub = questoes.questao_publica(q)
    t = db.row("SELECT * FROM topico WHERE id = ?", (q["topico_id"],))
    pub["texto_base"] = leis.texto_base_ref(q["dispositivo_ref"]) or (leis.texto_base_topico(t["id"]) if t else "")
    import anyio

    texto = await anyio.to_thread.run_sync(
        lambda: ia.explicar(pub, body.get("resposta"), modo=body.get("modo") or None))
    db.get_conn().execute("UPDATE questao SET explicacao_detalhada = ? WHERE id = ?", (texto, qid))
    return {"texto": texto}


@app.get("/api/imagens/{nome}")
def imagem(nome: str):
    p = db.DATA_DIR / "imagens" / Path(nome).name
    if not p.exists():
        p = db.DATA_DIR / "tmp" / Path(nome).name
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p)


# ---------------------------------------------------------------------------
# Matérias e tópicos
# ---------------------------------------------------------------------------

@app.get("/api/materias")
def materias():
    return db.rows("SELECT * FROM materia ORDER BY nome")


@app.patch("/api/materias/{mid}")
async def editar_materia(mid: int, request: Request):
    body = _json_body(await request.body())
    if "nome" in body and str(body["nome"]).strip():
        db.get_conn().execute("UPDATE materia SET nome = ? WHERE id = ?", (str(body["nome"]).strip(), mid))
    if "lei_seca" in body:
        db.get_conn().execute("UPDATE materia SET lei_seca = ? WHERE id = ?", (int(bool(body["lei_seca"])), mid))
    return {"ok": True}


@app.get("/api/topicos")
def topicos():
    ts = db.rows(
        """SELECT t.id, t.nome, t.assunto, t.dispositivo_ref, t.etapa, t.proxima_revisao, t.ultima_revisao, t.ultima_geracao,
                  t.lei_id, t.dispositivo_chave, m.id AS materia_id, m.nome AS materia, m.tema, m.lei_seca,
                  (SELECT COUNT(*) FROM material_apoio a WHERE a.topico_id = t.id) AS materiais
           FROM topico t JOIN materia m ON m.id = t.materia_id ORDER BY m.tema, m.nome, t.nome""")
    for t in ts:
        t.update(questoes.situacao_banco(t["id"]))
        t["sem_texto_base"] = bool(t["lei_seca"]) and not leis.texto_base_topico(t["id"])
    return {"topicos": ts, "max_etapa": len(config.get("intervalos"))}


@app.get("/api/topicos/{tid}")
def topico(tid: int):
    t = db.row("""SELECT t.*, m.nome AS materia, m.tema, m.lei_seca FROM topico t JOIN materia m ON m.id = t.materia_id
                  WHERE t.id = ?""", (tid,))
    if not t:
        raise HTTPException(404)
    qs = db.rows("SELECT * FROM questao WHERE topico_id = ? ORDER BY origem DESC, id DESC", (tid,))
    lei = db.row("SELECT id, sigla, nome FROM lei WHERE id = ?", (t["lei_id"],)) if t["lei_id"] else None
    return {
        "topico": t,
        "lei": lei,
        "banco": questoes.situacao_banco(tid),
        "texto_base": leis.texto_base_topico(tid),
        "materiais": db.rows("SELECT id, nome, enviado_em, length(texto) AS tamanho FROM material_apoio "
                             "WHERE topico_id = ? ORDER BY id DESC", (tid,)),
        "questoes": [questoes.questao_publica(q) for q in qs],
        "revisoes": db.rows("SELECT * FROM revisao WHERE topico_id = ? ORDER BY id DESC LIMIT 20", (tid,)),
        "max_etapa": len(config.get("intervalos")),
    }


@app.patch("/api/topicos/{tid}")
async def editar_topico(tid: int, request: Request):
    body = _json_body(await request.body())
    conn = db.get_conn()
    if "nome" in body and str(body["nome"]).strip():
        conn.execute("UPDATE topico SET nome = ? WHERE id = ?", (str(body["nome"]).strip(), tid))
    if "assunto" in body:
        conn.execute("UPDATE topico SET assunto = ? WHERE id = ?", (str(body["assunto"]).strip(), tid))
    if "dispositivo_ref" in body:
        conn.execute("UPDATE topico SET dispositivo_ref = ? WHERE id = ?", (str(body["dispositivo_ref"]).strip(), tid))
        leis.ligar_topico(tid)
    if "materia" in body and str(body["materia"]).strip():
        mid = questoes.obter_ou_criar_materia(str(body["materia"]), True, str(body.get("tema", "")))
        conn.execute("UPDATE topico SET materia_id = ? WHERE id = ?", (mid, tid))
    if "tema" in body and str(body["tema"]).strip():
        conn.execute("UPDATE materia SET tema = ? WHERE id = (SELECT materia_id FROM topico WHERE id = ?)",
                     (str(body["tema"]).strip(), tid))
    return {"ok": True}


@app.delete("/api/topicos/{tid}")
def apagar_topico(tid: int):
    db.get_conn().execute("DELETE FROM topico WHERE id = ?", (tid,))
    return {"ok": True}


@app.post("/api/topicos/{tid}/material")
async def enviar_material(tid: int, arquivo: UploadFile = File(...), nome: str = Form("")):
    dados = await arquivo.read()
    if len(dados) > MAX_UPLOAD:
        raise ValueError("Arquivo grande demais.")
    destino = db.DATA_DIR / "materiais" / f"{uuid.uuid4().hex}.pdf"
    destino.write_bytes(dados)
    try:
        texto = leis.extrair_texto_pdf(destino)
    except Exception:
        destino.unlink(missing_ok=True)
        raise ValueError("Não consegui ler esse PDF.")
    if not texto.strip():
        raise ValueError("O PDF não tem texto selecionável (talvez seja escaneado).")
    db.get_conn().execute(
        "INSERT INTO material_apoio(topico_id, nome, pdf_path, texto, enviado_em) VALUES(?,?,?,?,?)",
        (tid, nome or arquivo.filename or "material.pdf", str(destino), texto, db.agora()))
    return {"ok": True, "caracteres": len(texto)}


@app.delete("/api/materiais/{mid}")
def apagar_material(mid: int):
    m = db.row("SELECT pdf_path FROM material_apoio WHERE id = ?", (mid,))
    if m and m["pdf_path"]:
        Path(m["pdf_path"]).unlink(missing_ok=True)
    db.get_conn().execute("DELETE FROM material_apoio WHERE id = ?", (mid,))
    return {"ok": True}


# ---------------------------------------------------------------------------
# Geração
# ---------------------------------------------------------------------------

@app.post("/api/gerar")
async def gerar(request: Request):
    body = _json_body(await request.body())
    try:
        quantidade = int(body.get("quantidade") or 0) or None
    except (TypeError, ValueError):
        raise ValueError("Quantidade inválida.")
    criados = jobs.enfileirar_geracao(body.get("topico_id"), modo=body.get("modo") or None, quantidade=quantidade)
    return {"jobs": criados}


@app.get("/api/jobs")
def listar_jobs():
    return jobs.listar()


# ---------------------------------------------------------------------------
# Sessão diária
# ---------------------------------------------------------------------------

@app.get("/api/sessao")
def sessao_atual():
    aberta = sessao.sessao_aberta()
    if aberta:
        return sessao.estado(aberta["id"])
    return {"sessao": None}


@app.get("/api/sessao/{sid}")
def ver_sessao(sid: int):
    return sessao.estado(sid)


@app.post("/api/sessao/iniciar")
def iniciar_sessao():
    return sessao.montar_sessao()


@app.post("/api/sessao/responder")
async def responder(request: Request):
    body = _json_body(await request.body())
    return sessao.responder(int(body["item_id"]), str(body.get("resposta", "")))


@app.post("/api/sessao/{sid}/concluir")
def concluir(sid: int):
    return sessao.concluir(sid)


@app.get("/api/sessoes")
def historico_sessoes():
    return db.rows(
        """SELECT s.*, (SELECT COUNT(*) FROM sessao_item i WHERE i.sessao_id = s.id AND i.invalidada = 0) AS total,
                  (SELECT COUNT(*) FROM sessao_item i WHERE i.sessao_id = s.id AND i.correta = 1 AND i.invalidada = 0)
                  AS acertos
           FROM sessao s ORDER BY s.id DESC LIMIT 60""")


# ---------------------------------------------------------------------------
# Estatísticas
# ---------------------------------------------------------------------------

@app.get("/api/estatisticas")
def estatisticas(inicio: str = "", fim: str = "", fonte: str = "app", origem: str = "todas", materias: str = ""):
    ids = [int(x) for x in materias.split(",") if x.strip().isdigit()]
    return stats.estatisticas(inicio or None, fim or None, fonte, origem, ids)


@app.get("/api/estatisticas/materias")
def estatisticas_materias():
    return stats.lista_materias()


# ---------------------------------------------------------------------------
# Biblioteca de leis
# ---------------------------------------------------------------------------

@app.get("/api/leis")
def listar_leis():
    return db.rows(
        """SELECT l.*, (SELECT COUNT(*) FROM dispositivo d WHERE d.lei_id = l.id) AS dispositivos,
                  (SELECT COUNT(*) FROM dispositivo d WHERE d.lei_id = l.id AND d.nivel = 'artigo') AS artigos,
                  (SELECT COUNT(*) FROM topico t WHERE t.lei_id = l.id) AS topicos
           FROM lei l ORDER BY l.sigla""")


@app.post("/api/leis")
async def enviar_lei(arquivo: UploadFile = File(...), nome: str = Form(...), sigla: str = Form(...)):
    if not nome.strip() or not sigla.strip():
        raise ValueError("Informe nome e sigla da lei.")
    dados = await arquivo.read()
    if len(dados) > MAX_UPLOAD:
        raise ValueError("Arquivo grande demais.")
    destino = db.DATA_DIR / "leis" / f"{leis.norm_sigla(sigla) or 'lei'}-{uuid.uuid4().hex[:8]}.pdf"
    destino.write_bytes(dados)
    import anyio

    try:
        texto = await anyio.to_thread.run_sync(lambda: leis.extrair_texto_pdf(destino))
    except Exception:
        destino.unlink(missing_ok=True)
        raise ValueError("Não consegui ler esse PDF.")
    if not texto.strip():
        destino.unlink(missing_ok=True)
        raise ValueError("O PDF não tem texto selecionável (talvez seja escaneado).")
    return await anyio.to_thread.run_sync(lambda: leis.importar_lei(nome.strip(), sigla.strip(), destino, texto))


@app.get("/api/leis/{lid}")
def ver_lei(lid: int, busca: str = ""):
    lei = db.row("SELECT * FROM lei WHERE id = ?", (lid,))
    if not lei:
        raise HTTPException(404)
    if busca.strip():
        disps = db.rows("SELECT referencia, nivel, texto FROM dispositivo WHERE lei_id = ? AND texto LIKE ? "
                        "ORDER BY ordem LIMIT 300", (lid, f"%{busca.strip()}%"))
    else:
        disps = db.rows("SELECT referencia, nivel, texto FROM dispositivo WHERE lei_id = ? ORDER BY ordem LIMIT 3000",
                        (lid,))
    return {"lei": lei, "dispositivos": disps}


@app.delete("/api/leis/{lid}")
def apagar_lei(lid: int):
    lei = db.row("SELECT pdf_path FROM lei WHERE id = ?", (lid,))
    if lei and lei["pdf_path"]:
        Path(lei["pdf_path"]).unlink(missing_ok=True)
    db.get_conn().execute("DELETE FROM lei WHERE id = ?", (lid,))
    return {"ok": True}


# ---------------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------------

@app.get("/api/config")
def ver_config():
    return config.todas_publicas()


EDITAVEIS = {"modo_ia", "claude_bin", "modelos", "intervalos", "intervalo_manutencao", "limiar_avancar",
             "limiar_repetir", "questoes_primeira", "questoes_demais", "proporcao_reais", "minimo_geradas",
             "limiar_banco_baixo", "limite_diario", "estilo_banca", "modo_teste_sessao"}


@app.put("/api/config")
async def salvar_config(request: Request):
    body = _json_body(await request.body())
    for k, v in body.items():
        if k == "api_key":
            config.set("api_key", str(v).strip())
        elif k in EDITAVEIS:
            if k == "modo_ia" and v not in ("assinatura", "api"):
                raise ValueError("Modo de IA inválido.")
            if k == "intervalos":
                if not isinstance(v, list) or not v or not all(isinstance(x, int) and x > 0 for x in v):
                    raise ValueError("Intervalos devem ser números inteiros positivos.")
            config.set(k, v)
            if k == "modo_teste_sessao" and not v:
                sessao.descartar_sessoes_teste()
    return config.todas_publicas()


@app.post("/api/config/restaurar-estilo")
def restaurar_estilo():
    config.set("estilo_banca", config.ESTILO_VUNESP)
    return config.todas_publicas()


@app.post("/api/config/testar-ia")
async def testar_ia(request: Request):
    body = _json_body(await request.body())
    import anyio

    def _teste():
        q = {"origem": "gerada", "enunciado": "Responda apenas: ok", "alternativas": [], "gabarito": "-"}
        return ia.explicar(q, None, modo=body.get("modo") or None)

    texto = await anyio.to_thread.run_sync(_teste)
    return {"ok": True, "resposta": texto[:200]}


# ---------------------------------------------------------------------------
# Front
# ---------------------------------------------------------------------------

app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})
