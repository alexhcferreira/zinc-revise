"""Importa os PDFs da pasta "biblioteca de leis" para a Biblioteca de leis do app.

Uso (na raiz do projeto):
    .venv\\Scripts\\python scripts\\importar_biblioteca.py            # importa tudo
    .venv\\Scripts\\python scripts\\importar_biblioteca.py --simular  # só mostra o que encontraria

Reimportar uma lei com a mesma sigla substitui a versão anterior.
O edital não é lei e fica de fora.
"""
from __future__ import annotations

import shutil
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app import db, leis  # noqa: E402

PASTA = RAIZ / "biblioteca de leis"

# arquivo(s) -> nome, sigla, outros nomes usados nas referências
LEIS = [
    (["Direito Constitucional - Constituicao Federal.pdf"],
     "Constituição Federal de 1988", "CF/88", "CF, CF/1988, Constituição Federal, Constituição"),
    (["Direito Administrativo - Lei de Improbidade Administrativa.pdf"],
     "Lei de Improbidade Administrativa (Lei 8.429/1992)", "LIA",
     "Lei 8.429/1992, Lei 8.429/92, Lei de Improbidade Administrativa, Lei de Improbidade"),
    (["Direito Administrativo - Estatuto dos Funcionarios Publicos Civis de SP.pdf"],
     "Estatuto dos Funcionários Públicos Civis do Estado de SP (Lei 10.261/1968)", "Lei 10.261/68",
     "Lei 10.261/1968, Lei Estadual 10.261/1968, Estatuto dos Funcionários Públicos Civis, EFPCESP"),
    (["Direito Penal - Codigo Penal.pdf"],
     "Código Penal (Decreto-Lei 2.848/1940)", "CP", "Código Penal, Decreto-Lei 2.848/1940, DL 2.848/40"),
    (["Direito Processual Civil - Codigo de Processo Civil.pdf"],
     "Código de Processo Civil (Lei 13.105/2015)", "CPC", "CPC/2015, CPC/15, Código de Processo Civil, Lei 13.105/2015"),
    (["Direito Processual Civil - Juizados Especiais Civeis.pdf", "Direito Processual Penal - Juizados Especiais Criminais.pdf"],
     "Juizados Especiais Cíveis e Criminais (Lei 9.099/1995)", "Lei 9.099/95",
     "Lei 9.099/1995, Lei dos Juizados Especiais, Juizados Especiais Cíveis, Juizados Especiais Criminais, JECRIM"),
    (["Direito Processual Civil - Juizados Especiais da Fazenda Publica.pdf"],
     "Juizados Especiais da Fazenda Pública (Lei 12.153/2009)", "Lei 12.153/09",
     "Lei 12.153/2009, Juizados Especiais da Fazenda Pública, JEFP"),
    (["Direito Processual Penal - Codigo de Processo Penal.pdf"],
     "Código de Processo Penal (Decreto-Lei 3.689/1941)", "CPP",
     "Código de Processo Penal, Decreto-Lei 3.689/1941, DL 3.689/41"),
    (["Atualidades - Estatuto da Pessoa com Deficiencia.pdf"],
     "Estatuto da Pessoa com Deficiência (Lei 13.146/2015)", "EPD",
     "Lei 13.146/2015, Lei 13.146/15, Estatuto da Pessoa com Deficiência, LBI, Lei Brasileira de Inclusão"),
    (["Legislacao Interna - Normas da Corregedoria Geral da Justica.pdf"],
     "Normas de Serviço da Corregedoria Geral da Justiça – Tomo I", "NSCGJ",
     "Normas da Corregedoria, Normas de Serviço da Corregedoria Geral da Justiça, NSCGJ Tomo I"),
    (["Legislacao Interna - Regimento Interno do TJSP.pdf"],
     "Regimento Interno do Tribunal de Justiça de SP", "RITJSP",
     "Regimento Interno do TJSP, RI TJSP, Regimento Interno"),
    (["Legislacao Interna - Plano de Cargos e Carreiras do TJSP.pdf"],
     "Plano de Cargos e Carreiras do TJSP (LC Estadual 1.111/2010)", "LC 1.111/10",
     "LC 1.111/2010, Lei Complementar 1.111/2010, Lei Complementar Estadual 1.111/2010, Plano de Cargos e Carreiras"),
    (["Legislacao Interna - Teletrabalho no TJSP.pdf"],
     "Teletrabalho no TJSP (Resolução TJSP 850/2021)", "Res. 850/21",
     "Resolução 850/2021, Resolução TJSP 850/2021, Res. TJSP 850/2021, Teletrabalho"),
    (["Legislacao Interna - Governanca e uso do eproc.pdf"],
     "Governança e uso do eproc (Resolução TJSP 963/2025)", "Res. 963/25",
     "Resolução 963/2025, Resolução TJSP 963/2025, Res. TJSP 963/2025, eproc"),
]


def main(simular: bool) -> None:
    db.init_db()
    destino = db.DATA_DIR / "leis"
    destino.mkdir(parents=True, exist_ok=True)
    for arquivos, nome, sigla, apelidos in LEIS:
        caminhos = [PASTA / a for a in arquivos]
        faltando = [c.name for c in caminhos if not c.exists()]
        if faltando:
            print(f"!! {sigla}: arquivo não encontrado: {', '.join(faltando)}")
            continue
        texto = "\n".join(leis.extrair_texto_pdf(c) for c in caminhos)
        disps = leis.dividir_dispositivos(texto)
        artigos = [d for d in disps if d["nivel"] == "artigo"]
        repetidas = [k for k, n in Counter(d["chave"] for d in disps).items() if n > 1]
        aviso = f"  ({len(repetidas)} chaves repetidas, ex.: {repetidas[:3]})" if repetidas else ""
        faixa = f"art. {artigos[0]['artigo']} a {artigos[-1]['artigo']}" if artigos else "nenhum artigo"
        print(f"{sigla:<14} {len(artigos):>4} artigos {len(disps):>5} dispositivos  {faixa}{aviso}")
        if simular:
            continue
        pdf_final = destino / f"{leis.norm_sigla(sigla)}.pdf"
        shutil.copy(caminhos[0], pdf_final)
        leis.importar_lei(nome, sigla, pdf_final, texto, apelidos)
    if not simular:
        ligados = db.row("SELECT COUNT(*) AS n FROM topico WHERE lei_id IS NOT NULL")["n"]
        print(f"\nPronto. Assuntos ligados a alguma lei: {ligados}")


if __name__ == "__main__":
    main("--simular" in sys.argv)
