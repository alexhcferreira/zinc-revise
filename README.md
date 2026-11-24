# ZincRevise

App pessoal de **revisão espaçada para concurso público**, com questões geradas pelo Claude.

Foco atual: **TJSP – Escrevente Técnico Judiciário** (banca Vunesp, prova majoritariamente de lei seca).

## A ideia em um parágrafo

O estudo principal acontece no TecConcursos. A cada questão feita lá (acertando, errando ou só lendo, com foco nas erradas), o usuário cola a questão no ZincRevise, como texto ou print. O app identifica o tópico (ex.: *Direito Constitucional › Art. 5º, XI*) e guarda a questão. Quando o usuário aperta **"Gerar questões"**, o Claude monta o banco de revisão de cada tópico: **metade questões reais** (as que o usuário enviou, preferidas) e **metade questões inéditas** no estilo da banca, todas ancoradas no texto oficial da lei, que o usuário envia em PDF. O tópico entra num ciclo de **revisão espaçada adaptativa**, parecido com o Anki. Todo dia o app monta **uma sessão única** com todos os tópicos vencidos, e o usuário responde as questões como se estivesse numa plataforma de questões.

## Fluxo de uso

```
PDFs das leis ──► Biblioteca de leis (texto oficial por artigo/inciso)
                                        │
TecConcursos ──► cola questão (texto ou print) ──► cartão de confirmação ──► questão salva no tópico
                                        │                                         │
                                        ▼                                         ▼
                      botão "Gerar questões" ──► banco do tópico: reais (copiadas) + geradas (~50/50)
                                                                                  │
     Sessão diária (todos os tópicos vencidos, embaralhados) ◄────────────────────┘
                     │
                     ▼
     Resultado por tópico ──► regra adaptativa ──► próxima data de revisão
```

## Principais decisões

| Tema | Decisão |
|---|---|
| Plataforma | App web, hospedado no PC de casa (Windows 11), acessível de qualquer computador pela internet |
| Exposição | Internet, via Tailscale Funnel na porta 8443 (`https://<pc>.<tailnet>.ts.net:8443`) |
| Acesso | Senha (troque a padrão no primeiro acesso), bloqueio de 1 h após 3 tentativas erradas do mesmo endereço |
| IA, modo padrão | Assinatura do Claude via `claude -p` (Claude Code) no PC de casa |
| IA, modo alternativo | API key própria, ativada por um botão nas configurações |
| Leitura de questões | Automática com Claude Haiku, para print e texto. Detecta pelas cores se a questão foi acertada, errada ou não respondida |
| Banco de questões | ~50% reais (enviadas pelo usuário, preferidas) + ~50% inéditas estilo Vunesp. Gerado só ao apertar **"Gerar questões"** |
| Texto da lei | PDFs oficiais enviados pelo usuário na Biblioteca de leis; geração ancorada neles |
| Agendamento | Por tópico (nível inciso/parágrafo), intervalos adaptativos, manutenção a cada 30 dias; questões sorteadas a cada revisão |
| Sessão | Uma sessão diária única, misturando todas as matérias vencidas |

## Documentação

- [Regras de negócio](REGRAS_DE_NEGOCIO.md): o que o app faz e como decide cada coisa
- [Arquitetura e infraestrutura](ARQUITETURA.md): stack, hospedagem, integração com o Claude, modelo de dados e custos

## Como rodar

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 3001
```

Abra `http://localhost:3001` (senha padrão `9993`). Os dados ficam em `data/` (banco SQLite, prints, PDFs).

Para subir sozinho no logon e publicar na internet (porta 8443, via Tailscale Funnel):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\instalar-tarefa.ps1
```

Testes: `.venv\Scripts\python -m pytest -q tests` (a IA é simulada; nenhum teste chama o Claude).

## Código

| Pasta / arquivo | O que tem |
|---|---|
| `app/main.py` | Rotas da API (FastAPI) e login |
| `app/ia.py` | Camada de IA: modo assinatura (`claude -p`) e modo API key, prompts e schemas JSON |
| `app/questoes.py` | Cadastro de questões reais, tópicos, situação do banco |
| `app/jobs.py` | Fila do "Gerar questões" (worker em thread; Batch API no modo API key) |
| `app/sessao.py` | Sessão diária: sorteio, respostas, regra adaptativa |
| `app/srs.py` | Escada de intervalos e regra adaptativa (funções puras) |
| `app/leis.py` | Biblioteca de leis: PDF → artigo › parágrafo › inciso › alínea, texto-base |
| `app/stats.py` | Estatísticas no estilo do TecConcursos |
| `static/` | Front em JS puro, sem build |

## Design

Visual de plataforma de questões: limpo, claro e organizado, com a tela de questão no mesmo formato do TecConcursos (Questão N de M, Matéria, Assunto, linha da prova com o código `#` e alternativas em linhas).

- Fonte Source Sans 3 em todo o app.
- Azul como cor principal; verde e vermelho só para acerto e erro (cores dos gráficos validadas para daltonismo).
- Menu lateral com ícones, cartões brancos com borda suave.
- Cadastro: print em cima, questão recriada embaixo.
- Organização em **Tema › Matéria › Assunto** (ex.: Direito Administrativo › Direito Administrativo (Doutrina e Leis Federais) › Dos Atos de Improbidade (arts. 9º a 11 da Lei nº 8.429/1992)). Matéria e assunto são copiados exatamente do print do Tec, e o Assunto é a unidade da revisão espaçada.
- **Modo de teste da sessão** (Configurações › Sessão diária): a sessão traz todas as questões sem mexer em etapas, datas ou estatísticas. Voltar para o normal descarta as sessões de teste.
- Três temas, escolhidos em Configurações: **Claro**, **Claro suave** e **Escuro**.

## Status

✅ Primeira versão funcional: cadastro (print ou texto), geração, sessão diária, revisão espaçada, biblioteca de leis, estatísticas, configurações e os três temas.
