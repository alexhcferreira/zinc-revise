"""Testes do ZincRevise. A IA é substituída por respostas fixas (nenhuma chamada real ao Claude)."""
from __future__ import annotations

import os
import random
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture()
def app_env(tmp_path, monkeypatch):
    monkeypatch.setenv("ZINC_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ZINC_HOJE", "2026-11-23")
    from app import db

    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    db.reset_thread_conn()
    db.init_db()
    from app import auth

    auth.garantir_senha()
    yield tmp_path
    db.reset_thread_conn()


# ---------------------------------------------------------------------------
# Regras puras
# ---------------------------------------------------------------------------

CFG = {"intervalos": [1, 3, 7, 15, 30, 60], "intervalo_manutencao": 30, "limiar_avancar": 80, "limiar_repetir": 50,
       "questoes_primeira": 3, "questoes_demais": 5}


def test_escada_completa_ate_manutencao():
    from app import srs

    d = date(2026, 1, 1)
    etapa = 0
    vistos = []
    for _ in range(9):
        etapa, prox = srs.agendar(d, etapa, 5, 5, CFG)
        vistos.append(((prox - d).days, etapa))
        d = prox
    # 3, 7, 15, 30, 60 e depois manutenção a cada 30 dias para sempre
    assert [v[0] for v in vistos] == [3, 7, 15, 30, 60, 30, 30, 30, 30]
    assert vistos[-1][1] == 6


def test_regra_adaptativa():
    from app import srs

    d = date(2026, 1, 1)
    assert srs.agendar(d, 3, 4, 5, CFG) == (4, d + timedelta(days=30))   # 80% avança
    assert srs.agendar(d, 3, 3, 5, CFG) == (3, d + timedelta(days=15))   # 60% repete
    assert srs.agendar(d, 3, 2, 5, CFG) == (0, d + timedelta(days=1))    # 40% volta para a etapa 0, 1 dia
    assert srs.agendar(d, 6, 5, 5, CFG) == (6, d + timedelta(days=30))   # manutenção continua


def test_questoes_por_revisao():
    from app import srs

    assert srs.questoes_por_revisao(0, CFG) == 3
    assert srs.questoes_por_revisao(2, CFG) == 5


# ---------------------------------------------------------------------------
# Leis
# ---------------------------------------------------------------------------

TEXTO_LEI = """CONSTITUIÇÃO DA REPÚBLICA FEDERATIVA DO BRASIL
Art. 5º Todos são iguais perante a lei, sem distinção de qualquer natureza:
I - homens e mulheres são iguais em direitos e obrigações, nos termos desta Constituição;
XI - a casa é asilo inviolável do indivíduo, ninguém nela podendo penetrar sem consentimento do morador, salvo em caso
de flagrante delito ou desastre, ou para prestar socorro, ou, durante o dia, por determinação judicial;
§ 1º As normas definidoras dos direitos e garantias fundamentais têm aplicação imediata.
Art. 6º São direitos sociais a educação, a saúde.
Parágrafo único. Todo brasileiro em situação de vulnerabilidade social terá direito a uma renda básica familiar.
Art. 37. A administração pública direta e indireta obedecerá aos princípios de legalidade:
II - a investidura em cargo ou emprego público depende de aprovação prévia em concurso público;
a) primeira alínea;
Art. 1.000. Artigo grande.
"""


def test_divide_dispositivos():
    from app import leis

    d = leis.dividir_dispositivos(TEXTO_LEI)
    chaves = [x["chave"] for x in d]
    assert chaves == ["5", "5|I", "5|XI", "5|P1", "6", "6|PU", "37", "37|II", "37|II|a", "1000"]
    xi = next(x for x in d if x["chave"] == "5|XI")
    assert "flagrante delito" in xi["texto"]  # continuação de linha juntada
    assert xi["referencia"] == "art. 5º, XI"


@pytest.mark.parametrize("ref,esperado", [
    ("CF/88, art. 5º, XI", ("cf88", "5|XI")),
    ("CF, art. 5º, § 1º", ("cf", "5|P1")),
    ("CPC, art. 219, parágrafo único", ("cpc", "219|PU")),
    ("art. 37, II, alínea a, CF/88", ("cf88", "37|II|a")),
    ("Lei 8.112/90, art. 10", ("lei811290", "10")),
])
def test_parse_referencia(ref, esperado):
    from app import leis

    assert leis.parse_referencia(ref) == esperado


def test_texto_base_marca_dispositivo(app_env):
    from app import db, leis, questoes

    leis.importar_lei("Constituição Federal", "CF/88", app_env / "cf.pdf", TEXTO_LEI)
    r = questoes.salvar_real({
        "materia": "Direito Constitucional", "lei_seca": True, "topico": "Art. 5º, XI – domicílio",
        "dispositivo_ref": "CF, art. 5º, XI", "enunciado": "Sobre a casa…",
        "alternativas": [{"letra": "A", "texto": "x"}, {"letra": "B", "texto": "y"}],
        "situacao": "errou", "marcada": "A", "gabarito": "B",
    })
    t = db.row("SELECT * FROM topico WHERE id = ?", (r["topico_id"],))
    assert t["lei_id"] and t["dispositivo_chave"] == "5|XI"
    tb = leis.texto_base(t)
    assert ">>> XI - a casa é asilo inviolável" in tb
    assert "Art. 5º Todos são iguais" in tb


# ---------------------------------------------------------------------------
# Fluxo completo com a IA simulada
# ---------------------------------------------------------------------------

def _q(i, gab="A"):
    return {"enunciado": f"Questão gerada {i}", "alternativas": [{"letra": l, "texto": f"alt {l}"} for l in "ABCDE"],
            "gabarito": gab, "justificativa": "art. 5º", "dispositivo_ref": "art. 5º, XI",
            "explicacoes_erradas": [{"letra": "B", "motivo": "troca"}], "trecho_base": "a casa é asilo"}


def test_fluxo_cadastro_geracao_sessao(app_env, monkeypatch):
    from app import db, ia, jobs, questoes, sessao

    chamadas = []

    def falso_gerar(ctx, modo=None):
        chamadas.append(ctx)
        return {"gabaritos": [{"questao_id": i, "gabarito": "C", "justificativa": "conferido"} for i in ctx["conferir"]],
                "questoes": [_q(i) for i in range(ctx["n_gerar"])], "fonte_externa": False, "fontes": ""}

    monkeypatch.setattr(ia, "gerar_banco", falso_gerar)

    base = {"materia": "Direito Constitucional", "lei_seca": True, "topico": "Art. 5º, XI", "dispositivo_ref": "",
            "alternativas": [{"letra": l, "texto": l} for l in "ABCDE"]}
    r1 = questoes.salvar_real({**base, "enunciado": "Q1", "situacao": "errou", "marcada": "A", "gabarito": "B"})
    r2 = questoes.salvar_real({**base, "enunciado": "Q2", "situacao": "nao_respondeu", "gabarito": "D"})
    assert r1["topico_novo"] and not r2["topico_novo"]
    tid = r1["topico_id"]
    t = db.row("SELECT * FROM topico WHERE id = ?", (tid,))
    assert t["etapa"] == 0 and t["proxima_revisao"] == "2026-11-24"

    # nada é gerado automaticamente
    assert db.row("SELECT COUNT(*) AS n FROM questao WHERE origem = 'gerada'")["n"] == 0

    jobs.enfileirar_geracao()
    assert jobs.ciclo() is True
    ctx = chamadas[0]
    assert ctx["n_gerar"] == 5          # mínimo 5 (2 reais pediriam 2)
    assert ctx["conferir"] == [r2["questao_id"]]
    q2 = db.row("SELECT * FROM questao WHERE id = ?", (r2["questao_id"],))
    assert q2["gabarito"] == "C" and q2["gabarito_origem"] == "claude_conferido"
    assert db.row("SELECT COUNT(*) AS n FROM questao WHERE origem = 'gerada'")["n"] == 5
    assert db.row("SELECT COUNT(*) AS n FROM questao WHERE origem = 'real' AND no_banco = 0")["n"] == 0

    # amanhã: sessão com 3 questões (primeira revisão), mirando metade reais
    os.environ["ZINC_HOJE"] = "2026-11-24"
    st = sessao.montar_sessao(random.Random(1))
    itens = st["itens"]
    assert len(itens) == 3
    assert sum(1 for i in itens if i["questao"]["origem"] == "real") == 2
    assert all("gabarito" not in i["questao"] for i in itens)  # gabarito escondido antes de responder

    # nova sessão não é criada enquanto houver uma aberta
    assert sessao.montar_sessao()["sessao"]["id"] == st["sessao"]["id"]

    # responde tudo certo
    for it in itens:
        gab = db.row("SELECT gabarito FROM questao WHERE id = ?", (it["questao"]["id"],))["gabarito"]
        sessao.responder(it["item_id"], gab)
    fim = sessao.concluir(st["sessao"]["id"])
    assert fim["resumo"]["pct"] == 100
    t = db.row("SELECT * FROM topico WHERE id = ?", (tid,))
    assert t["etapa"] == 1 and t["proxima_revisao"] == "2026-11-27"

    # novo erro no Tec num tópico existente: volta para a etapa 0 (revisão em 1 dia)
    r3 = questoes.salvar_real({**base, "enunciado": "Q3", "situacao": "errou", "marcada": "C", "gabarito": "E"})
    assert r3["voltou_etapa_0"]
    t = db.row("SELECT * FROM topico WHERE id = ?", (tid,))
    assert t["etapa"] == 0 and t["proxima_revisao"] == "2026-11-25"
    # acerto no Tec não mexe na etapa
    r4 = questoes.salvar_real({**base, "enunciado": "Q4", "situacao": "acertou", "marcada": "A", "gabarito": "A"})
    assert not r4["voltou_etapa_0"]


def test_topico_sem_banco_usa_reais_e_sem_questoes_fica_fora(app_env):
    from app import db, questoes, sessao

    base = {"lei_seca": False, "alternativas": [{"letra": l, "texto": l} for l in "ABCDE"]}
    questoes.salvar_real({**base, "materia": "Língua Portuguesa", "topico": "Crase", "enunciado": "Q",
                          "situacao": "errou", "marcada": "A", "gabarito": "B"})
    # tópico vazio vencido
    mid = questoes.obter_ou_criar_materia("Matemática", False)
    tid_vazio, _ = questoes.obter_ou_criar_topico(mid, "Regra de três", "")
    os.environ["ZINC_HOJE"] = "2026-11-24"
    st = sessao.montar_sessao(random.Random(2))
    assert len(st["itens"]) == 1 and st["itens"][0]["questao"]["origem"] == "real"
    assert db.row("SELECT proxima_revisao FROM topico WHERE id = ?", (tid_vazio,))["proxima_revisao"] == "2026-11-24"


def test_invalidada_nao_conta(app_env, monkeypatch):
    from app import db, questoes, sessao

    base = {"materia": "Direito Penal", "lei_seca": True, "topico": "Art. 121", "dispositivo_ref": "",
            "alternativas": [{"letra": l, "texto": l} for l in "ABCDE"]}
    for i in range(3):
        questoes.salvar_real({**base, "enunciado": f"Q{i}", "situacao": "errou", "marcada": "A", "gabarito": "B"})
    os.environ["ZINC_HOJE"] = "2026-11-24"
    st = sessao.montar_sessao(random.Random(3))
    itens = st["itens"]
    questoes.invalidar(itens[0]["questao"]["id"], "ambígua")
    sessao.responder(itens[1]["item_id"], "B")
    sessao.responder(itens[2]["item_id"], "B")
    fim = sessao.concluir(st["sessao"]["id"])
    assert fim["resumo"]["total"] == 2 and fim["resumo"]["acertos"] == 2
    assert db.row("SELECT status FROM questao WHERE id = ?", (itens[0]["questao"]["id"],))["status"] == "invalidada"


def test_api_login_bloqueio_e_rotas(app_env, monkeypatch):
    from fastapi.testclient import TestClient

    from app import jobs
    from app.main import app

    monkeypatch.setattr(jobs, "iniciar_worker", lambda: None)
    with TestClient(app, base_url="https://testserver") as c:
        assert c.get("/api/painel").status_code == 401
        assert c.post("/api/login", json={"senha": "9993"}).status_code == 200
        assert c.get("/api/painel").status_code == 200
        r = c.get("/api/config").json()
        assert "api_key" not in r and r["modo_ia"] == "assinatura"
        c.put("/api/config", json={"api_key": "sk-ant-api03-abcdefghijklmnop1234"})
        r = c.get("/api/config").json()
        assert r["api_key_mascarada"] == "sk-ant-…1234" and "abcdefghij" not in str(r)
        assert c.get("/api/estatisticas").status_code == 200
        assert c.get("/").status_code == 200
        c.post("/api/logout")
        for _ in range(3):
            assert c.post("/api/login", json={"senha": "0000"}).status_code == 401
        r = c.post("/api/login", json={"senha": "9993"})
        assert r.status_code == 429  # bloqueado por 1 h mesmo com a senha certa


def test_assinatura_remove_api_key_do_ambiente(monkeypatch):
    from app import ia

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-x")
    env = ia._ambiente_assinatura()
    assert "ANTHROPIC_API_KEY" not in env


def test_estatisticas_por_materia(app_env):
    from app import questoes, stats

    base = {"lei_seca": True, "alternativas": [{"letra": l, "texto": l} for l in "ABCDE"], "dispositivo_ref": ""}
    questoes.salvar_real({**base, "materia": "Direito Penal", "topico": "Art. 121", "enunciado": "a", "situacao": "errou", "marcada": "A", "gabarito": "B"})
    questoes.salvar_real({**base, "materia": "Direito Penal", "topico": "Art. 155", "enunciado": "b", "situacao": "acertou", "marcada": "B", "gabarito": "B"})
    r = stats.estatisticas("2026-11-01", "2026-11-30", fonte="tec")
    assert r["geral"]["resolvidas"] == 2 and r["geral"]["acertos"] == 1
    assert r["materias"][0]["sigla"] == "DP" and len(r["materias"][0]["topicos"]) == 2
    assert stats.sigla_materia("Direito Processual Civil") == "DPC"
