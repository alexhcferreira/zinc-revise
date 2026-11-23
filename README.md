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
| Plataforma | App web, hospedado no PC de casa (Windows 11), acessado pelo Tailscale em casa e no serviço |
| Exposição | Somente na tailnet (`tailscale serve`, porta 8443). **Sem Funnel** |
| Acesso | Senha (padrão `9993`), bloqueio de 1 h após 3 tentativas erradas |
| IA, modo padrão | Assinatura do Claude via `claude -p` (Claude Code) no PC de casa |
| IA, modo alternativo | API key própria, ativada por um botão nas configurações |
| Leitura de questões | Automática com Claude Haiku, para print e texto. Detecta pelas cores se a questão foi acertada, errada ou não respondida |
| Banco de questões | ~50% reais (enviadas pelo usuário, preferidas) + ~50% inéditas estilo Vunesp. Gerado só ao apertar **"Gerar questões"** |
| Texto da lei | PDFs oficiais enviados pelo usuário na Biblioteca de leis; geração ancorada neles |
| Agendamento | Por tópico (nível inciso/parágrafo), intervalos adaptativos, manutenção a cada 30 dias; questões sorteadas a cada revisão |
| Sessão | Uma sessão diária única, misturando todas as matérias vencidas |

## Documentação

- [Regras de negócio](docs/REGRAS_DE_NEGOCIO.md): o que o app faz e como decide cada coisa
- [Arquitetura e infraestrutura](docs/ARQUITETURA.md): stack, hospedagem, integração com o Claude, modelo de dados e custos

## Status

📝 Fase de especificação. Nenhum código ainda.
