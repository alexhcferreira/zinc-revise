# Arquitetura e infraestrutura – ZincRevise

## 1. Visão geral

```
 PC do serviço                         PC de casa (Windows 11, sempre ligado)
┌──────────────┐   Tailscale (tailnet)  ┌───────────────────────────────────────────┐
│  Navegador   │ ─────────────────────► │ tailscale serve :8443 (só tailnet)        │
└──────────────┘                        │        │                                  │
 PC de casa                             │        ▼                                  │
┌──────────────┐                        │ Backend ZincRevise  127.0.0.1:3001        │
│  Navegador   │ ─────────────────────► │  ├─ API REST + front estático             │
└──────────────┘                        │  ├─ SQLite (dados + fila de jobs)         │
                                        │  ├─ Biblioteca de leis (PDFs + texto)     │
                                        │  └─ Camada de IA                          │
                                        │       ├─ Assinatura → claude -p           │
                                        │       └─ API key   → Claude API (+Batch)  │
                                        │                                           │
                                        │ (Funnel :443 → :3000, sites existentes,   │
                                        │  continua igual, sem relação com este app)│
                                        └───────────────────────────────────────────┘
```

## 2. Hospedagem

| Item | Valor |
|---|---|
| Máquina | PC de casa, Windows 11 x64, sempre ligado |
| Backend | `127.0.0.1:3001`, só local; nunca escutar em `0.0.0.0` |
| Exposição | `tailscale serve --bg --https=8443 http://127.0.0.1:3001` |
| URL | `https://<nome-do-pc>.<tailnet>.ts.net:8443` |
| Visibilidade | **Só tailnet.** Não habilitar Funnel nesta porta |
| Convivência | O Funnel atual (porta 443 → `127.0.0.1:3000`, dois sites de estudo) **não é alterado** |

Por que porta separada em vez de mais um caminho no mesmo domínio:
- os sites atuais estão com **Funnel ligado**, ou seja, abertos na internet. Este app usa a assinatura do Claude e talvez uma API key, então não pode ficar público;
- não precisa mexer no programa que hoje atende a porta 3000;
- não precisa de caminho base nem de reescrita de URL.

### 2.1 Inicialização automática
- O backend sobe por uma tarefa do **Agendador de Tarefas do Windows**, acionada **ao fazer logon do usuário**.
- **Importante:** o backend precisa rodar **com o mesmo usuário do Windows** em que o Claude Code foi logado. O login do Claude Code é por usuário. Um serviço rodando como `SYSTEM` não enxergaria a assinatura.

## 3. Stack (proposta)

| Camada | Escolha | Motivo |
|---|---|---|
| Backend | Python 3.13 com FastAPI | Simples de manter rodando no Windows; bom suporte ao SDK da Anthropic |
| Banco | SQLite (arquivo local) | Um usuário só, zero administração, backup = copiar um arquivo |
| Front | HTML + JS (SPA leve), servido pelo próprio backend | Sem build complexo; funciona em qualquer navegador |
| Jobs | Fila simples em tabela SQLite + worker em thread | Execução em segundo plano do "Gerar questões" |
| PDFs | `pdfplumber` / `pypdf` para extrair texto + parser de dispositivos | Biblioteca de leis (seção 4.4) |
| IA | `claude` CLI (assinatura) ou `anthropic` SDK (API) | Ver seção 4 |

Decidido: Python + FastAPI. O PC de casa tem Python 3.13.7. Node.js foi considerado e descartado.

## 4. Camada de IA

Um único módulo com interface comum. O resto do app não sabe qual modo está ativo.

```
ClaudeProvider (interface)
 ├─ ler_questao(imagem_ou_texto, modelo) -> QuestaoExtraida   # situação, gabarito provisório, tópico sugerido
 ├─ gerar_banco(topico, texto_base, reais, n_gerar, estilo, modelo)
 │      -> {gabaritos_conferidos, [QuestaoGerada]}
 └─ explicar(questao, resposta_usuario, modelo, esforco="alto") -> texto

SubscriptionProvider  → subprocesso `claude -p`
ApiProvider           → SDK anthropic (Messages API, Batch API, prompt caching)
```

### 4.1 SubscriptionProvider (`claude -p`)
- Executa o Claude Code em modo não interativo, com o modelo da tarefa (`--model`) e saída em JSON (`--output-format json`).
- **Ambiente do subprocesso:** copiar o ambiente atual **sem `ANTHROPIC_API_KEY`**, para garantir que o uso saia da assinatura.
- **Imagens:** salvar o print num diretório temporário do app e referenciar o arquivo no prompt, liberando só a ferramenta de leitura de arquivo.
- **Caminho do executável:** configurável (`CLAUDE_BIN`). Logo após a instalação, o Windows pode não reconhecer `claude` até que se abra um novo terminal ou se faça novo logon, porque o PATH só atualiza depois. O backend deve aceitar o caminho completo do executável.
- Saída exigida em JSON com schema definido. Validar, e em caso de JSON inválido, tentar uma vez de novo.

### 4.2 ApiProvider
- Imagem enviada em base64 na Messages API.
- Geração de banco: **Batch API**, porque não precisa ser instantânea.
- **Prompt caching** para o bloco fixo (instruções do estilo da banca e texto-base do tópico).
- A key fica no banco local; ela nunca é exportada para variável de ambiente global.

### 4.3 Troca de modo
- A configuração `modo_ia` (`assinatura` | `api`) é lida **a cada chamada**. Trocar o botão vale imediatamente.
- Em falha do modo assinatura, a UI oferece "Tentar com API key". Nunca troca sozinha.

### 4.4 Biblioteca de leis
- Upload de PDF numa seção própria do app. O arquivo fica guardado em disco e o texto vai para o banco.
- Um parser divide o texto em **dispositivos** (artigo › parágrafo › inciso › alínea) pelos marcadores "Art.", "§", "I –", "a)". Quando o PDF vem bagunçado (colunas, cabeçalhos, notas de rodapé), o Haiku limpa e estrutura o trecho.
- Ao cadastrar uma questão, o tópico sugerido traz a referência do dispositivo (ex.: `CF/88, art. 5º, XI`), e o app liga o tópico ao dispositivo da biblioteca automaticamente.
- Na geração, só o texto dos dispositivos do tópico, mais vizinhos imediatos para contexto, vai no prompt. Assim o prompt fica pequeno e barato.
- Busca externa de lei só acontece se o dispositivo não estiver na biblioteca. No modo assinatura, isso usa as ferramentas web do próprio Claude Code; no modo API, a ferramenta de busca web. A origem fica registrada e aparece na tela.
- Nova versão de PDF da mesma lei substitui a anterior. Os dispositivos são religados pela referência.

### 4.5 Fluxo do botão "Gerar questões"
1. Seleciona os tópicos alvo: todos os que têm questões novas, ou só um.
2. Para cada tópico, cria um job `gerar_banco` com:
   - texto-base;
   - questões reais (inclusive as novas, como exemplo de estilo);
   - gabaritos provisórios a conferir;
   - quantidade a gerar (para chegar perto de 50/50, com mínimo configurável).
3. O worker executa os jobs. No modo API, eles vão juntos num lote da Batch API.
4. Ao terminar, as reais novas entram no banco, os gabaritos conferidos são gravados e as geradas são salvas.
5. A UI mostra o progresso. O usuário pode continuar usando o app.

## 5. Modelo de dados (rascunho)

```
materia        (id, nome)
lei            (id, nome, sigla, pdf_path, versao, enviado_em)
dispositivo    (id, lei_id, referencia, nivel[artigo|paragrafo|inciso|alinea],
                pai_id, texto, ordem)
topico         (id, materia_id, nome, etapa, proxima_revisao,
                ultima_revisao, ultima_geracao, criado_em)
topico_dispositivo (topico_id, dispositivo_id)
material_apoio (id, topico_id, nome, pdf_path, texto, enviado_em)  -- matérias sem lei seca
questao        (id, topico_id, origem[real|gerada], enunciado,
                alternativas_json, gabarito,
                gabarito_origem[print|claude_provisorio|claude_conferido|usuario],
                justificativa, dispositivo_ref,
                no_banco[0|1],              -- real entra no banco após "Gerar questões",
                                            -- mas já pode ser sorteada antes (regras 5.2, item 7)
                status[ativa|invalidada], motivo_invalidacao,
                -- só reais:
                marcada_no_tec, resultado_no_tec[acertou|errou|nao_respondeu],
                imagem_path, criado_em)
revisao        (id, topico_id, sessao_id, data, etapa_antes, etapa_depois,
                acertos, total)
sessao         (id, data, status[aberta|concluida], iniciada_em, concluida_em)
sessao_item    (id, sessao_id, questao_id, ordem, resposta, correta,
                respondida_em)
job            (id, tipo[ler_questao|gerar_banco|estruturar_pdf], payload_json,
                status[pendente|rodando|ok|erro], tentativas, erro, criado_em)
config         (chave, valor)            -- senha_hash, modo_ia, api_key, modelos…
login_tentativa(id, quando, sucesso)     -- para o bloqueio de 1 h
```

## 6. Segurança

- Backend escuta só em `127.0.0.1`. O único caminho de fora é o `tailscale serve`, que só atende a tailnet.
- Senha com hash (bcrypt ou argon2), padrão `9993`, trocável.
- 3 falhas seguidas → login bloqueado por 1 h, contado em `login_tentativa`.
- Cookie de sessão `HttpOnly`, `Secure`, `SameSite=Strict`, **sem expiração**. Vale até "Sair" ou troca de senha. A troca de senha invalida todas as sessões, porque o token está ligado a uma "versão da senha".
- A API key nunca aparece em resposta da API nem em log.
- Conteúdo vindo do Claude é renderizado como texto, nunca como HTML.

## 7. Custos estimados (modo API key)

Preços da Claude API em 23/11/2026, por milhão de tokens:

| Modelo | Entrada | Saída | Batch (entrada/saída) |
|---|---|---|---|
| Opus 5.5 | US$ 4 | US$ 20 | US$ 2 / US$ 10 |
| Sonnet 5.5 | US$ 2 | US$ 10 | US$ 1 / US$ 5 |
| Haiku 5.5 (≤100k) | US$ 0,10 | US$ 0,50 | US$ 0,05 / US$ 0,25 |

Cenário diário: 10 questões cadastradas, 3 tópicos gerados, cerca de 10 "Explicar melhor".

| Configuração | Por dia | Por mês |
|---|---|---|
| Tudo em Opus 5.5, esforço médio | ~US$ 1,20 | ~US$ 36 |
| Padrão: Haiku (leitura) + Opus Batch (geração) + Sonnet alto (explicações) | ~US$ 0,65 | ~US$ 20 |
| Igual ao padrão, com geração em Sonnet Batch | ~US$ 0,50 | ~US$ 15 |

- As **revisões em si não custam nada**: as questões já estão no banco.
- Como a geração só acontece no botão e metade do banco é de questões reais (custo zero de geração), gera-se bem menos que no desenho inicial.
- "Explicar melhor" em esforço alto é o item que mais cresce com o uso. Cada explicação gasta mais tokens de raciocínio.
- Os PDFs da biblioteca custam uma vez só, no envio, e só se precisarem de limpeza pelo Haiku.
- Os números acima são estimativas.
- Recomendado: definir um **limite mensal de gasto** no Claude Console.

No **modo assinatura** não há custo por token. O consumo sai do limite de uso do plano.

## 8. Termos de uso: por que o desenho é este

- Os termos da Anthropic permitem usar o Claude Code e o Agent SDK logados na assinatura para **uso individual comum**. Isso consome os limites do plano.
- **Não é permitido:**
  - extrair o token de login para usar em outro programa;
  - oferecer "login com Claude" a terceiros;
  - rotear requisições de outras pessoas pela assinatura.
- Por isso o ZincRevise:
  - roda **na máquina do usuário**;
  - é **usado só por ele**;
  - chama o **Claude Code oficial, sem modificações**;
  - **nunca** manipula credenciais do Claude.
- Essas regras mudaram várias vezes em 2026. A camada de IA trocável (seção 4) existe para que, se a regra mudar, baste ativar o modo API key.

Referências:
- [Legal and compliance – Claude Code Docs](https://code.claude.com/docs/en/legal-and-compliance)
- [Use the Agent SDK with your Claude plan](https://support.claude.com/en/articles/15036540-use-the-agent-sdk-with-your-claude-plan)
- [Preços da Claude API](https://platform.claude.com/docs/en/about-claude/pricing)
- [Instalação do Claude Code](https://code.claude.com/docs/en/setup)

## 9. Pré-requisitos no PC de casa

- [x] PC sempre ligado
- [x] Tailscale instalado em casa e no serviço
- [x] Claude Code instalado
- [x] `claude` logado na assinatura (rodar `claude` uma vez e fazer login no navegador). O executável está em `%USERPROFILE%\.local\bin\claude.exe` (versão 2.1.331). Usar esse caminho completo em `CLAUDE_BIN`
- [x] Python 3.13.7
- [ ] Liberar a porta 8443 no `tailscale serve`, só na tailnet
