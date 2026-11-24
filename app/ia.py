"""Camada de IA: um único ponto de entrada, dois modos (assinatura via `claude -p` ou API key).

O resto do app chama ler_questao / gerar_banco / explicar e não sabe qual modo está ativo.
O modo é lido a cada chamada, então trocar nas configurações vale na hora.
"""
from __future__ import annotations

import base64
import json
import mimetypes
import os
import shutil
import subprocess
import uuid
from pathlib import Path

from . import config, db


class ErroIA(Exception):
    """Falha numa chamada ao Claude. `pode_tentar_api` indica se vale oferecer a API key."""

    def __init__(self, msg: str, modo: str):
        super().__init__(msg)
        self.modo = modo
        self.pode_tentar_api = modo == "assinatura" and bool(config.get("api_key"))


# ---------------------------------------------------------------------------
# Schemas de saída
# ---------------------------------------------------------------------------

_ALTERNATIVAS = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {"letra": {"type": "string"}, "texto": {"type": "string"}},
        "required": ["letra", "texto"],
        "additionalProperties": False,
    },
}

SCHEMA_LER = {
    "type": "object",
    "properties": {
        "materia": {"type": "string"},
        "assunto": {"type": "string"},
        "tec_codigo": {"type": "string"},
        "tec_prova": {"type": "string"},
        "lei_seca": {"type": "boolean"},
        "topico": {"type": "string"},
        "dispositivo_ref": {"type": "string"},
        "lei_sigla": {"type": "string"},
        "enunciado": {"type": "string"},
        "alternativas": _ALTERNATIVAS,
        "situacao": {"type": "string", "enum": ["acertou", "errou", "nao_respondeu"]},
        "marcada": {"type": "string"},
        "gabarito": {"type": "string"},
        "confianca": {"type": "number"},
        "observacoes": {"type": "string"},
    },
    "required": [
        "materia", "assunto", "tec_codigo", "tec_prova", "lei_seca", "topico", "dispositivo_ref", "lei_sigla", "enunciado",
        "alternativas", "situacao", "marcada", "gabarito", "confianca", "observacoes",
    ],
    "additionalProperties": False,
}

SCHEMA_GERAR = {
    "type": "object",
    "properties": {
        "gabaritos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "questao_id": {"type": "integer"},
                    "gabarito": {"type": "string"},
                    "justificativa": {"type": "string"},
                },
                "required": ["questao_id", "gabarito", "justificativa"],
                "additionalProperties": False,
            },
        },
        "questoes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "enunciado": {"type": "string"},
                    "alternativas": _ALTERNATIVAS,
                    "gabarito": {"type": "string"},
                    "justificativa": {"type": "string"},
                    "dispositivo_ref": {"type": "string"},
                    "explicacoes_erradas": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"letra": {"type": "string"}, "motivo": {"type": "string"}},
                            "required": ["letra", "motivo"],
                            "additionalProperties": False,
                        },
                    },
                    "trecho_base": {"type": "string"},
                },
                "required": [
                    "enunciado", "alternativas", "gabarito", "justificativa",
                    "dispositivo_ref", "explicacoes_erradas", "trecho_base",
                ],
                "additionalProperties": False,
            },
        },
        "fonte_externa": {"type": "boolean"},
        "fontes": {"type": "string"},
    },
    "required": ["gabaritos", "questoes", "fonte_externa", "fontes"],
    "additionalProperties": False,
}

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SYSTEM_LER = """Você lê questões de concurso público coladas por um estudante (print do TecConcursos ou texto) e devolve os dados estruturados.

Regras de leitura:
- Transcreva enunciado e alternativas fielmente, sem corrigir a redação. Letras das alternativas em maiúsculas (A, B, C, D, E). Em questões Certo/Errado use as letras "C" (Certo) e "E" (Errado).
- Situação da resposta, pelas cores das alternativas no print:
  - uma alternativa vermelha e outra verde: o estudante marcou a vermelha e errou; o gabarito é a verde. situacao = "errou", marcada = letra vermelha, gabarito = letra verde.
  - só uma alternativa verde, nenhuma vermelha: o estudante acertou. situacao = "acertou", marcada = gabarito = letra verde.
  - nenhuma cor, ou conteúdo em texto: situacao = "nao_respondeu", marcada = "". Nesse caso sugira em "gabarito" a letra que você considera correta (gabarito provisório).
- Em tema escuro, alternativa riscada, print cortado ou dúvida, registre em "observacoes" e reduza "confianca" (0 a 1).

Cabeçalho do TecConcursos (copie EXATAMENTE como aparece no print, caractere por caractere, com parênteses, acentos, "nº", "º" e números; não resuma, não corrija, não reescreva):
- "materia": o texto depois de "Matéria:". Ex.: "Direito Administrativo (Doutrina e Leis Federais)".
- "assunto": o texto depois de "Assunto:". Ex.: "Dos Atos de Improbidade (arts. 9º a 11 da Lei nº 8.429/1992)".
- "tec_codigo": o número depois de "#" na linha da prova, sem o "#". Ex.: "3786935".
- "tec_prova": o restante dessa linha. Ex.: "VUNESP - 2026 - Auxiliar Administrativo (CM Nova Odessa)".
Se o cabeçalho não estiver visível (texto colado ou print cortado): em "materia" e "assunto" use o nome de uma matéria/assunto existente que corresponda, ou o nome no padrão do TecConcursos, e avise em "observacoes" que não estavam no print; "tec_codigo" e "tec_prova" ficam "".

Classificação:
- "lei_seca": true se a matéria é cobrada por texto de lei; false para Português, Matemática, Informática, Raciocínio Lógico e afins.
- "topico": a unidade de revisão, mais específica que o assunto. Em lei seca, no nível de inciso ou parágrafo, no formato "Art. 5º, XI – inviolabilidade de domicílio". Em outras matérias, o tema exato (ex.: "Crase antes de pronome"). Reaproveite um tópico existente quando for o mesmo.
- "dispositivo_ref": em lei seca, a referência completa com a sigla da lei, ex.: "CF/88, art. 5º, XI" ou "CPC, art. 219, parágrafo único". Fora de lei seca, "".
- "lei_sigla": a sigla da lei como aparece na lista de leis da biblioteca, quando houver correspondência; senão a sigla usual (ex.: "CF/88"). Fora de lei seca, "".
"""

SYSTEM_GERAR = """Você monta o banco de revisão de um tópico para um estudante de concurso público.

Você recebe: o tópico, o texto-base oficial (ou material de apoio), as questões reais que o estudante enviou e o estilo da banca.

Tarefas:
1. Conferir gabaritos: para cada questão real listada em "CONFERIR GABARITO", confirme ou corrija o gabarito com base no texto-base e escreva uma justificativa curta citando o dispositivo. Devolva em "gabaritos".
2. Gerar questões inéditas: crie exatamente a quantidade pedida, no estilo da banca, sobre o assunto do tópico. Use as questões reais como exemplo de estilo e de assunto, sem copiá-las.
   - Toda afirmação precisa estar ancorada no texto-base. Não invente prazos, números ou redação.
   - Cada questão tem uma única alternativa correta.
   - "justificativa": por que a correta está correta, citando o dispositivo (ex.: "art. 5º, XI, CF").
   - "explicacoes_erradas": para cada alternativa errada, o motivo curto do erro.
   - "trecho_base": o trecho literal do texto-base que sustenta o gabarito.
   - "dispositivo_ref": o dispositivo cobrado.
   - Varie as pegadinhas e a posição da alternativa correta.
3. "fonte_externa": true somente se precisou usar texto de lei que não estava no texto-base; nesse caso liste as fontes em "fontes". Caso contrário false e "".

Nunca atribua banca, ano ou prova às questões geradas. Escreva em português do Brasil."""

SYSTEM_EXPLICAR = """Você é um professor de cursinho para concursos, especialista em lei seca e no estilo da banca.
Explique a questão para o estudante de forma clara e didática, em português do Brasil:
- por que o gabarito está correto, citando o dispositivo;
- por que cada alternativa errada está errada, apontando a pegadinha usada;
- se o estudante errou, por que a alternativa que ele marcou é tentadora e como não cair nela de novo;
- uma dica curta de memorização, se houver uma boa.
Use parágrafos curtos e listas simples. Não use tabelas nem títulos grandes. Não use HTML."""


def prompt_ler(texto: str | None, tem_imagem: bool, materias: list[str], topicos: list[str], leis: list[str]) -> str:
    partes = []
    if tem_imagem:
        partes.append("Leia a questão no print anexado.")
    if texto:
        partes.append("Questão colada como texto:\n<<<\n" + texto.strip() + "\n>>>")
    partes.append("Matérias existentes: " + ("; ".join(materias) if materias else "(nenhuma)"))
    partes.append("Tópicos existentes (matéria › assunto › tópico):\n" + ("\n".join(topicos[:400]) if topicos else "(nenhum)"))
    partes.append("Leis na biblioteca (sigla – nome): " + ("; ".join(leis) if leis else "(nenhuma)"))
    return "\n\n".join(partes)


def prompt_gerar(ctx: dict) -> tuple[str, str]:
    """Retorna (bloco_fixo, bloco_variavel). O fixo vem primeiro para aproveitar cache."""
    fixo = [f"ESTILO DA BANCA\n{ctx['estilo']}"]
    if ctx.get("texto_base"):
        fixo.append(f"TEXTO-BASE OFICIAL ({ctx.get('dispositivo_ref') or ctx['topico']})\n<<<\n{ctx['texto_base']}\n>>>")
    elif ctx.get("material_apoio"):
        fixo.append(f"MATERIAL DE APOIO\n<<<\n{ctx['material_apoio']}\n>>>")
    elif ctx.get("lei_seca"):
        fixo.append("TEXTO-BASE: ausente na biblioteca. Use o texto da lei que você conhece com cuidado redobrado "
                    "e marque fonte_externa = true.")
    else:
        fixo.append("MATERIAL DE APOIO: nenhum. Matéria que não é lei seca: use as questões reais e seu conhecimento.")

    var = [f"MATÉRIA: {ctx['materia']}\nTÓPICO: {ctx['topico']}"]
    if ctx["reais"]:
        linhas = []
        for q in ctx["reais"]:
            alts = "\n".join(f"  {a['letra']}) {a['texto']}" for a in q["alternativas"])
            linhas.append(f"[id {q['id']}] {q['enunciado']}\n{alts}\n  Gabarito: {q['gabarito'] or '?'}")
        var.append("QUESTÕES REAIS DO ESTUDANTE (exemplos de estilo e assunto)\n" + "\n\n".join(linhas))
    if ctx["conferir"]:
        var.append("CONFERIR GABARITO das questões reais de id: " + ", ".join(str(i) for i in ctx["conferir"]))
    else:
        var.append("CONFERIR GABARITO: nenhuma (devolva gabaritos = []).")
    var.append(f"GERAR: {ctx['n_gerar']} questões inéditas.")
    return "\n\n".join(fixo), "\n\n".join(var)


def prompt_explicar(q: dict, resposta: str | None) -> str:
    alts = "\n".join(f"{a['letra']}) {a['texto']}" for a in q["alternativas"])
    partes = [f"Questão ({'real, do estudante' if q['origem'] == 'real' else 'inédita, estilo da banca'}):\n{q['enunciado']}\n{alts}",
              f"Gabarito: {q['gabarito']}"]
    if q.get("justificativa"):
        partes.append(f"Justificativa registrada: {q['justificativa']}")
    if q.get("dispositivo_ref"):
        partes.append(f"Dispositivo: {q['dispositivo_ref']}")
    if q.get("texto_base"):
        partes.append(f"Texto-base oficial:\n<<<\n{q['texto_base']}\n>>>")
    if resposta:
        partes.append(f"O estudante marcou: {resposta} ({'acertou' if resposta == q['gabarito'] else 'errou'}).")
    return "\n\n".join(partes)


# ---------------------------------------------------------------------------
# Provider: assinatura (claude -p)
# ---------------------------------------------------------------------------

def _claude_bin() -> str:
    conf = (config.get("claude_bin") or "").strip()
    if conf:
        return conf
    padrao = Path(os.environ.get("USERPROFILE", "~")).expanduser() / ".local" / "bin" / "claude.exe"
    if padrao.exists():
        return str(padrao)
    achado = shutil.which("claude")
    if achado:
        return achado
    raise ErroIA("Executável do Claude Code não encontrado. Configure o caminho em Configurações.", "assinatura")


def _ambiente_assinatura() -> dict:
    env = dict(os.environ)
    # Se a key existir no ambiente, o Claude Code passa a cobrar como API sem aviso.
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("ANTHROPIC_AUTH_TOKEN", None)
    return env


def _rodar_assinatura(tarefa: str, system: str, prompt: str, schema: dict | None,
                      imagem: Path | None = None, web: bool = False, timeout: int = 900) -> dict | str:
    modelo, esforco = config.modelo_da_tarefa(tarefa)
    work = db.DATA_DIR / "claude_work" / uuid.uuid4().hex
    work.mkdir(parents=True)
    try:
        ferramentas = []
        if imagem is not None:
            destino = work / ("questao" + imagem.suffix.lower())
            shutil.copy(imagem, destino)
            prompt = f"O print da questão está no arquivo ./{destino.name} (use a ferramenta Read para vê-lo).\n\n" + prompt
            ferramentas.append("Read")
        if web:
            ferramentas += ["WebSearch", "WebFetch"]
        cmd = [
            _claude_bin(), "-p",
            "--model", modelo,
            "--effort", esforco,
            "--output-format", "json",
            "--no-session-persistence",
            "--setting-sources", "",
            "--strict-mcp-config",
            "--disable-slash-commands",
            "--system-prompt", system,
            "--tools", ",".join(ferramentas) if ferramentas else "",
        ]
        if ferramentas:
            cmd += ["--allowedTools", ",".join(ferramentas)]
        if schema is not None:
            cmd += ["--json-schema", json.dumps(schema, ensure_ascii=False)]
        try:
            proc = subprocess.run(
                cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
                cwd=work, env=_ambiente_assinatura(), timeout=timeout,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except subprocess.TimeoutExpired:
            raise ErroIA("O Claude demorou demais para responder.", "assinatura")
        except FileNotFoundError:
            raise ErroIA("Executável do Claude Code não encontrado. Configure o caminho em Configurações.", "assinatura")
        saida = (proc.stdout or "").strip()
        try:
            dados = json.loads(saida)
        except json.JSONDecodeError:
            msg = (proc.stderr or saida or "sem saída").strip()[:500]
            raise ErroIA(f"Falha no Claude Code: {msg}", "assinatura")
        if dados.get("is_error") or dados.get("subtype") != "success":
            msg = dados.get("result") or dados.get("api_error_status") or dados.get("subtype") or "erro desconhecido"
            raise ErroIA(f"Claude Code retornou erro: {str(msg)[:500]}", "assinatura")
        if schema is not None:
            estruturado = dados.get("structured_output")
            if estruturado is None:
                try:
                    estruturado = json.loads(dados.get("result") or "")
                except json.JSONDecodeError:
                    raise ErroIA("O Claude não devolveu JSON válido.", "assinatura")
            return estruturado
        return dados.get("result") or ""
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ---------------------------------------------------------------------------
# Provider: API key
# ---------------------------------------------------------------------------

def _cliente_api():
    import anthropic

    key = config.get("api_key")
    if not key:
        raise ErroIA("Nenhuma API key configurada.", "api")
    return anthropic.Anthropic(api_key=key, max_retries=2)


def _usa_fallback(modelo: str) -> bool:
    return modelo in {"claude-opus-5-5", "claude-sonnet-5-5", "claude-fable-5-2"}


def _params_api(tarefa: str, system: str, conteudo: list, schema: dict | None, cache: bool = False) -> dict:
    modelo, esforco = config.modelo_da_tarefa(tarefa)
    output_config: dict = {"effort": esforco}
    if schema is not None:
        output_config["format"] = {"type": "json_schema", "schema": schema}
    params = {
        "model": modelo,
        "max_tokens": 32000 if tarefa == "gerar" else 16000,
        "system": system,
        "messages": [{"role": "user", "content": conteudo}],
        "output_config": output_config,
    }
    if cache:
        params["cache_control"] = {"type": "ephemeral"}
    return params


def _ler_resposta_api(msg, schema: dict | None):
    if msg.stop_reason == "refusal":
        raise ErroIA("O Claude recusou a solicitação.", "api")
    if msg.stop_reason == "max_tokens":
        raise ErroIA("A resposta do Claude foi cortada (limite de tokens).", "api")
    texto = "".join(b.text for b in msg.content if b.type == "text")
    if schema is None:
        return texto
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        raise ErroIA("O Claude não devolveu JSON válido.", "api")


def _rodar_api(tarefa: str, system: str, conteudo: list, schema: dict | None, cache: bool = False):
    import anthropic

    client = _cliente_api()
    params = _params_api(tarefa, system, conteudo, schema, cache)
    try:
        if _usa_fallback(params["model"]):
            with client.beta.messages.stream(
                **params, betas=["server-side-fallback-2026-07-01"], fallbacks="default"
            ) as stream:
                msg = stream.get_final_message()
        else:
            with client.messages.stream(**params) as stream:
                msg = stream.get_final_message()
    except anthropic.AuthenticationError:
        raise ErroIA("API key inválida.", "api")
    except anthropic.RateLimitError:
        raise ErroIA("Limite de uso da API atingido. Tente mais tarde.", "api")
    except anthropic.APIStatusError as e:
        raise ErroIA(f"Erro da API ({e.status_code}): {e.message}", "api")
    except anthropic.APIConnectionError:
        raise ErroIA("Sem conexão com a API da Anthropic.", "api")
    return _ler_resposta_api(msg, schema)


def _conteudo_api(prompt: str, imagem: Path | None = None, prefixo_cache: str | None = None) -> list:
    blocos: list = []
    if imagem is not None:
        mt = mimetypes.guess_type(imagem.name)[0] or "image/png"
        dados = base64.standard_b64encode(imagem.read_bytes()).decode()
        blocos.append({"type": "image", "source": {"type": "base64", "media_type": mt, "data": dados}})
    if prefixo_cache:
        blocos.append({"type": "text", "text": prefixo_cache, "cache_control": {"type": "ephemeral"}})
    blocos.append({"type": "text", "text": prompt})
    return blocos


# ---------------------------------------------------------------------------
# Interface comum
# ---------------------------------------------------------------------------

def modo_atual(forcar: str | None = None) -> str:
    return forcar or config.get("modo_ia") or "assinatura"


def ler_questao(texto: str | None, imagem: Path | None, contexto: dict, reler: bool = False,
                modo: str | None = None) -> dict:
    tarefa = "reler" if reler else "ler"
    prompt = prompt_ler(texto, imagem is not None, contexto["materias"], contexto["topicos"], contexto["leis"])
    if modo_atual(modo) == "api":
        return _rodar_api(tarefa, SYSTEM_LER, _conteudo_api(prompt, imagem), SCHEMA_LER)
    return _rodar_assinatura(tarefa, SYSTEM_LER, prompt, SCHEMA_LER, imagem=imagem, timeout=300)


def gerar_banco(ctx: dict, modo: str | None = None) -> dict:
    fixo, var = prompt_gerar(ctx)
    web = bool(ctx.get("lei_seca") and not ctx.get("texto_base"))
    if modo_atual(modo) == "api":
        return _rodar_api("gerar", SYSTEM_GERAR, _conteudo_api(var, prefixo_cache=fixo), SCHEMA_GERAR)
    return _rodar_assinatura("gerar", SYSTEM_GERAR, fixo + "\n\n" + var, SCHEMA_GERAR, web=web)


def params_lote_gerar(ctx: dict) -> dict:
    """Parâmetros de uma requisição da Batch API (sem fallbacks: o Batch não aceita)."""
    fixo, var = prompt_gerar(ctx)
    return _params_api("gerar", SYSTEM_GERAR, _conteudo_api(var, prefixo_cache=fixo), SCHEMA_GERAR)


def ler_resultado_lote(msg) -> dict:
    return _ler_resposta_api(msg, SCHEMA_GERAR)


def explicar(q: dict, resposta: str | None, modo: str | None = None) -> str:
    prompt = prompt_explicar(q, resposta)
    if modo_atual(modo) == "api":
        return _rodar_api("explicar", SYSTEM_EXPLICAR, _conteudo_api(prompt), None)
    return _rodar_assinatura("explicar", SYSTEM_EXPLICAR, prompt, None, timeout=600)
