"""Biblioteca de leis: extração do texto do PDF, divisão em dispositivos e busca do texto-base."""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from pathlib import Path

from . import db

ROMANOS = re.compile(r"^(?=[IVXLC])M{0,3}(C[MD]|D?C{0,3})(X[CL]|L?X{0,3})(I[XV]|V?I{0,3})$")

RE_ARTIGO = re.compile(r"^Art\.?\s*(\d{1,3}(?:\.\d{3})*)\s*(?:[º°ºo]|\.)?\s*(?:-\s*([A-Z])\b)?\s*[.\-–—]?\s*(.*)$")
RE_PARAGRAFO = re.compile(r"^§\s*(\d+)\s*[º°o]?\s*(?:-\s*([A-Z])\b)?\s*[.\-–—]?\s*(.*)$")
RE_PAR_UNICO = re.compile(r"^Par[áa]grafo\s+[úu]nico\s*[.\-–—:]?\s*(.*)$", re.IGNORECASE)
RE_INCISO = re.compile(r"^([IVXLC]+)\s*(?:-\s*([A-Z])\b)?\s*[-–—]\s*(.*)$")
RE_ALINEA = re.compile(r"^([a-z])\)\s*(.*)$")


def _sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def norm_sigla(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _sem_acento(s or "").lower())


# ---------------------------------------------------------------------------
# Extração do PDF
# ---------------------------------------------------------------------------

def extrair_texto_pdf(caminho: Path) -> str:
    import pdfplumber

    paginas = []
    with pdfplumber.open(caminho) as pdf:
        for p in pdf.pages:
            paginas.append(p.extract_text() or "")
    return limpar_paginas(paginas)


def limpar_paginas(paginas: list[str]) -> str:
    """Remove cabeçalhos/rodapés repetidos e junta palavras hifenizadas na quebra de linha."""
    linhas_por_pag = [[l.strip() for l in p.splitlines()] for p in paginas]
    contagem = Counter()
    for linhas in linhas_por_pag:
        for l in set(linhas[:3] + linhas[-3:]):
            if l:
                contagem[re.sub(r"\d+", "#", l)] += 1
    limite = max(2, len(paginas) // 2)
    repetidas = {k for k, v in contagem.items() if v >= limite}
    saida = []
    for linhas in linhas_por_pag:
        for l in linhas:
            if not l or re.sub(r"\d+", "#", l) in repetidas:
                continue
            if re.fullmatch(r"\d{1,4}", l):  # número de página solto
                continue
            saida.append(l)
    texto = "\n".join(saida)
    texto = re.sub(r"(\w)-\n(\w)", r"\1\2", texto)
    return texto


# ---------------------------------------------------------------------------
# Divisão em dispositivos
# ---------------------------------------------------------------------------

def _chave_artigo(num: str, letra: str | None) -> str:
    n = num.replace(".", "")
    return f"{int(n)}{('-' + letra.upper()) if letra else ''}"


def _ref_artigo(num: str, letra: str | None) -> str:
    n = int(num.replace(".", ""))
    base = f"{n}º" if n < 10 else f"{n}"
    return f"art. {base}{('-' + letra.upper()) if letra else ''}"


def dividir_dispositivos(texto: str) -> list[dict]:
    """Divide o texto da lei em artigo › parágrafo › inciso › alínea.

    Cada dispositivo recebe `referencia` legível ("art. 5º, § 1º, II") e `chave`
    normalizada ("5|P1|II") para casar com as referências sugeridas pelo Claude.
    """
    disps: list[dict] = []
    art = par = inc = None  # (chave, ref)
    atual: dict | None = None

    def novo(nivel: str, chave: str, ref: str, texto_ini: str):
        nonlocal atual
        atual = {"nivel": nivel, "chave": chave, "referencia": ref, "artigo": art[0], "texto": texto_ini.strip()}
        disps.append(atual)

    for linha in texto.splitlines():
        l = linha.strip()
        if not l:
            continue
        m = RE_ARTIGO.match(l)
        if m:
            art = (_chave_artigo(m.group(1), m.group(2)), _ref_artigo(m.group(1), m.group(2)))
            par = inc = None
            novo("artigo", art[0], art[1], l)
            continue
        if art is None:
            continue  # preâmbulo, ementa
        m = RE_PAR_UNICO.match(l)
        if m:
            par = ("PU", "parágrafo único")
            inc = None
            novo("paragrafo", f"{art[0]}|PU", f"{art[1]}, parágrafo único", l)
            continue
        m = RE_PARAGRAFO.match(l)
        if m:
            n = int(m.group(1))
            suf = ("-" + m.group(2).upper()) if m.group(2) else ""
            par = (f"P{n}{suf}", f"§ {n}º{suf}" if n < 10 else f"§ {n}{suf}")
            inc = None
            novo("paragrafo", f"{art[0]}|{par[0]}", f"{art[1]}, {par[1]}", l)
            continue
        m = RE_INCISO.match(l)
        if m and ROMANOS.match(m.group(1)):
            suf = ("-" + m.group(2).upper()) if m.group(2) else ""
            inc = (m.group(1) + suf, m.group(1) + suf)
            base_ch = f"{art[0]}|{par[0]}" if par else art[0]
            base_ref = f"{art[1]}, {par[1]}" if par else art[1]
            novo("inciso", f"{base_ch}|{inc[0]}", f"{base_ref}, {inc[1]}", l)
            continue
        m = RE_ALINEA.match(l)
        if m and inc:
            base_ch = f"{art[0]}|{par[0]}|{inc[0]}" if par else f"{art[0]}|{inc[0]}"
            base_ref = f"{art[1]}, {par[1]}, {inc[1]}" if par else f"{art[1]}, {inc[1]}"
            novo("alinea", f"{base_ch}|{m.group(1)}", f"{base_ref}, {m.group(1)}", l)
            continue
        if atual is not None:  # continuação da linha anterior
            atual["texto"] += " " + l
    return disps


# ---------------------------------------------------------------------------
# Referências ("CF/88, art. 5º, XI")
# ---------------------------------------------------------------------------

def parse_referencia(ref: str) -> tuple[str, str]:
    """Separa a referência em (sigla_normalizada, chave). Ex.: "CF/88, art. 5º, § 1º, II" -> ("cf88", "5|P1|II")."""
    if not ref:
        return "", ""
    s = ref.replace(" ", " ")
    m = re.search(r"\bart(?:igo)?\.?\s*(\d{1,3}(?:\.\d{3})*)\s*[º°o]?\s*(?:-\s*([A-Za-z])\b)?", s, re.IGNORECASE)
    if not m:
        return norm_sigla(s), ""
    sigla = norm_sigla(s[: m.start()])
    resto = s[m.end():]
    partes = [_chave_artigo(m.group(1), m.group(2))]
    if re.search(r"par[áa]grafo\s+[úu]nico", resto, re.IGNORECASE):
        partes.append("PU")
    else:
        mp = re.search(r"§\s*(\d+)\s*[º°o]?(?:\s*-\s*([A-Za-z])\b)?", resto)
        if mp:
            partes.append(f"P{int(mp.group(1))}{('-' + mp.group(2).upper()) if mp.group(2) else ''}")
    for tok in re.split(r"[,;\s]+", resto):
        tok = tok.strip(".")
        if tok and ROMANOS.match(tok):
            partes.append(tok)
            break
    ma = re.search(r"al[íi]nea\s+[\"“']?([a-z])\b|,\s*([a-z])\)?\s*$", resto)
    if ma and len(partes) > 1 and ROMANOS.match(partes[-1]):
        partes.append(ma.group(1) or ma.group(2))
    if not sigla:
        # sigla depois do dispositivo: "art. 5º, XI, CF"
        resto_sem = re.sub(r"§\s*\d+\s*[º°o]?|par[áa]grafo\s+[úu]nico|\b[IVXLC]+\b|al[íi]nea\s+\w", "", resto)
        sigla = norm_sigla(resto_sem)
    return sigla, "|".join(partes)


def achar_lei(sigla_ou_ref: str) -> dict | None:
    alvo = norm_sigla(sigla_ou_ref)
    if not alvo:
        return None
    leis = db.rows("SELECT id, sigla, nome FROM lei")
    for l in leis:
        if norm_sigla(l["sigla"]) == alvo:
            return l
    # tolerância: "cf" casa com "cf88", "cpc" casa com "cpc2015"
    for l in leis:
        s = norm_sigla(l["sigla"])
        if s.startswith(alvo) or alvo.startswith(s):
            return l
    return None


def ligar_topico(topico_id: int) -> None:
    """Liga o tópico à lei da biblioteca pela referência do dispositivo."""
    t = db.row("SELECT dispositivo_ref FROM topico WHERE id = ?", (topico_id,))
    if not t:
        return
    sigla, chave = parse_referencia(t["dispositivo_ref"])
    lei = achar_lei(sigla) if sigla else None
    db.get_conn().execute(
        "UPDATE topico SET lei_id = ?, dispositivo_chave = ? WHERE id = ?",
        (lei["id"] if lei else None, chave, topico_id),
    )


def texto_base(topico: dict, limite: int = 12000) -> str:
    """Texto oficial do tópico: o artigo inteiro que contém o dispositivo, com o dispositivo marcado."""
    if not topico.get("lei_id") or not topico.get("dispositivo_chave"):
        return ""
    artigo = topico["dispositivo_chave"].split("|")[0]
    disps = db.rows(
        "SELECT referencia, chave, texto FROM dispositivo WHERE lei_id = ? AND artigo = ? ORDER BY ordem",
        (topico["lei_id"], artigo),
    )
    if not disps:
        return ""
    alvo = topico["dispositivo_chave"]
    linhas = []
    for d in disps:
        marca = ">>> " if (d["chave"] == alvo or d["chave"].startswith(alvo + "|")) else ""
        linhas.append(marca + d["texto"])
    texto = "\n".join(linhas)
    if len(texto) > limite:
        # artigo muito longo (ex.: art. 5º da CF): fica com o trecho em volta do dispositivo
        idx = next((i for i, l in enumerate(linhas) if l.startswith(">>> ")), 0)
        ini, fim = max(0, idx - 6), min(len(linhas), idx + 10)
        texto = "\n".join([linhas[0], "[…]"] + linhas[max(ini, 1):fim] + (["[…]"] if fim < len(linhas) else []))
    return texto


def importar_lei(nome: str, sigla: str, pdf_path: Path, texto: str) -> dict:
    """Cria ou substitui a lei e religa os tópicos pela referência."""
    disps = dividir_dispositivos(texto)
    with db.tx() as conn:
        existente = None
        for l in db.rows("SELECT id, sigla, versao FROM lei"):
            if norm_sigla(l["sigla"]) == norm_sigla(sigla):
                existente = l
        if existente:
            lei_id = existente["id"]
            conn.execute("DELETE FROM dispositivo WHERE lei_id = ?", (lei_id,))
            conn.execute(
                "UPDATE lei SET nome = ?, sigla = ?, pdf_path = ?, versao = versao + 1, enviado_em = ? WHERE id = ?",
                (nome, sigla, str(pdf_path), db.agora(), lei_id),
            )
        else:
            cur = conn.execute(
                "INSERT INTO lei(nome, sigla, pdf_path, enviado_em) VALUES(?, ?, ?, ?)",
                (nome, sigla, str(pdf_path), db.agora()),
            )
            lei_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO dispositivo(lei_id, referencia, chave, nivel, artigo, texto, ordem) VALUES(?,?,?,?,?,?,?)",
            [(lei_id, d["referencia"], d["chave"], d["nivel"], d["artigo"], d["texto"], i) for i, d in enumerate(disps)],
        )
    for t in db.rows("SELECT id FROM topico WHERE dispositivo_ref != ''"):
        ligar_topico(t["id"])
    return {"id": lei_id, "dispositivos": len(disps), "artigos": sum(1 for d in disps if d["nivel"] == "artigo")}
