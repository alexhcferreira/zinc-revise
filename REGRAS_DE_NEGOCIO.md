# Regras de negócio – ZincRevise

---

## 1. Glossário

| Termo | Significado |
|---|---|
| **Matéria** | Disciplina do edital. Ex.: Direito Constitucional, Língua Portuguesa |
| **Tópico** | Unidade de estudo e de agendamento dentro de uma matéria, no nível de **inciso ou parágrafo** para lei seca. Ex.: *Art. 5º, XI – inviolabilidade de domicílio*, *Crase* |
| **Questão real** | Questão feita no TecConcursos e enviada pelo usuário. É a preferida para revisão |
| **Questão gerada** | Questão inédita criada pelo Claude no estilo da banca, ancorada no tópico e no texto da lei |
| **Banco do tópico** | Conjunto de questões (reais e geradas) disponíveis para sorteio naquele tópico |
| **Biblioteca de leis** | Seção do app onde o usuário envia os PDFs oficiais das leis do edital |
| **Texto-base** | Trecho da biblioteca de leis correspondente ao tópico (os dispositivos que ele cobre) |
| **Material de apoio** | PDF opcional de teoria, ligado a um tópico de matéria que não é lei seca (ex.: Crase) |
| **Etapa** | Posição do tópico na escada de intervalos de revisão |
| **Sessão diária** | Bateria única de questões com todos os tópicos vencidos no dia |

---

## 2. Cadastro de questões

### 2.1 Entrada
- O usuário cola a questão na tela de cadastro com **Ctrl+V**.
- O app **detecta automaticamente** o tipo do conteúdo colado e manda tudo para o **Claude Haiku**:
  - **Imagem** (print do Tec): leitura completa, inclusive das cores das alternativas (seção 2.2).
  - **Texto**: o Haiku estrutura enunciado e alternativas. Texto copiado do Tec não traz gabarito nem marcação, então a questão é tratada como **não respondida** (seção 2.2).
- **Todas** as questões feitas no Tec podem ser enviadas, certas, erradas ou não respondidas. As erradas são o foco e têm prioridade no sorteio (seção 5.2).
- O cadastro **só registra a questão**. Ele não dispara geração de questões (seção 3.4).

### 2.2 Leitura automática (Haiku)
O Haiku extrai enunciado, alternativas (A–E ou Certo/Errado) e, em prints, a situação da resposta pelas **cores das alternativas**:

| O que aparece no print | Interpretação |
|---|---|
| Uma alternativa **vermelha** e outra **verde** | Usuário marcou a vermelha e **errou**; o gabarito é a verde |
| Só uma alternativa **verde**, nenhuma vermelha | Usuário marcou a verde e **acertou** |
| **Nenhuma cor** nas alternativas, ou texto colado | Usuário **não respondeu**; só enviou a questão |

Questão **não respondida**:
- o usuário **não informa** gabarito nem marcação;
- o **Claude define o gabarito** com base no texto-base do tópico, e a questão fica rotulada **"gabarito definido pelo Claude"**;
- na leitura, o Haiku sugere um gabarito provisório. Ao apertar **"Gerar questões"** (seção 3.4), o modelo de geração **confere esse gabarito** contra o texto-base e corrige se preciso;
- não conta como erro no Tec e não aciona a regra da seção 4.5.

A resposta do Haiku é um JSON estruturado, com um campo de **confiança** e observações (ex.: "tema escuro", "alternativa riscada", "print cortado").

### 2.3 Cartão de confirmação
Antes de salvar, o app mostra um cartão com o que foi extraído: enunciado, alternativas, situação, gabarito e tópico sugerido.
- Basta confirmar. O usuário **não precisa preencher nada**.
- Todos os campos podem ser editados com um clique, se ele quiser corrigir algo.
- Botão **"Reler com Sonnet"** para quando o Haiku se confundir.

### 2.4 Tópico
- O Claude **sugere matéria e tópico** a partir da questão, no nível de **inciso ou parágrafo**. Ex.: "Direito Constitucional › Art. 5º, XI".
- O usuário pode aceitar, editar ou escolher um tópico já existente, com busca por nome.
- Um tópico novo começa na etapa 0 (seção 4).
- O app liga o tópico automaticamente ao **texto-base** correspondente na biblioteca de leis (seção 2.5).

### 2.5 Biblioteca de leis (texto oficial)
- Seção própria do app onde o usuário **envia os PDFs** das leis e normas do edital (CF, CPC, Normas da Corregedoria, estatuto dos servidores de SP etc.).
- O app extrai o texto do PDF e o organiza por **artigo, parágrafo e inciso**, para cada tópico apontar exatamente para os dispositivos que cobre.
- Toda geração e toda conferência de gabarito são **ancoradas no texto-base**, e não na memória do modelo. Isso elimina o principal risco em lei seca: prazos, números e redação alterada recentemente.
- O Claude **não busca leis por fora**. A única exceção é quando ele achar necessário, por exemplo quando o dispositivo não está em nenhum PDF enviado. Nesse caso o app avisa que o texto veio de fonte externa e sugere enviar o PDF.
- Sem texto-base, o tópico mostra o aviso "sem texto-base, conferir dispositivos".
- Enviar uma versão nova do PDF de uma lei substitui a anterior. Os tópicos ligados a ela passam a usar o texto novo.

### 2.6 Matérias sem lei seca
- Língua Portuguesa, Matemática, Informática, Raciocínio Lógico e outras matérias que não são lei seca não têm texto-base.
- Nelas o tópico é um **assunto** (ex.: *Crase*, *Regra de três*), e não um dispositivo.
- A geração usa as **questões reais** do tópico e o conhecimento do Claude.
- O usuário pode anexar ao tópico um **material de apoio** opcional (PDF de teoria). Quando houver, a geração e a conferência de gabarito se ancoram nele.
- O aviso "sem texto-base" **não aparece** nessas matérias.

---

## 3. Questões do banco

### 3.1 Princípios
- O usuário tem **preferência por questões reais**, as que ele mesmo enviou do Tec. As **geradas também são bem-vindas** e completam o banco.
- O banco de cada tópico mira **metade reais e metade geradas**. Quando há poucas reais, as geradas completam.
- O app **nunca** busca questões reais na internet. As reais são só as enviadas pelo usuário.
- Toda questão gerada é rotulada **"Inédita – estilo Vunesp"**. O app **nunca** atribui banca, ano ou prova a uma questão gerada.

### 3.2 Estilo Vunesp (TJSP Escrevente)
- 5 alternativas (A–E), exatamente uma correta.
- Redação próxima da **literalidade da lei**.
- Pegadinhas típicas:
  - troca de verbo modal ("poderá" ↔ "deverá");
  - "permitido" ↔ "vedado", "salvo" ↔ "inclusive";
  - prazos, quóruns e números trocados;
  - competência atribuída ao órgão errado;
  - exceção apresentada como regra.
- As questões reais do tópico servem de **exemplo de estilo e de assunto** para a geração.
- O estilo fica num prompt configurável, preparado para outras bancas no futuro (ex.: Certo/Errado para Cebraspe).

### 3.3 Conteúdo de cada questão gerada
- Enunciado, alternativas, gabarito.
- **Justificativa** citando o dispositivo (ex.: "art. 5º, XI, CF").
- Explicação curta de **por que cada alternativa errada está errada**.
- Referência ao trecho do texto-base usado.

### 3.4 Quando gerar: botão "Gerar questões"
- **Nada é gerado automaticamente.** Gerar uma questão a cada envio encheria o banco de questões inúteis.
- A geração só acontece quando o usuário aperta **"Gerar questões"**. O botão fica:
  - na lista de tópicos: processa **todos os tópicos com questões novas** desde a última geração;
  - dentro de cada tópico: processa só aquele tópico.
- Ao apertar, para cada tópico o app:
  1. **copia para o banco** as questões reais enviadas desde a última geração;
  2. **confere o gabarito** das reais não respondidas (seção 2.2);
  3. **gera questões inéditas** em quantidade suficiente para o banco ficar perto de 50% reais e 50% geradas, com um mínimo configurável (padrão: 5 por tópico).
- **Aviso de banco baixo:** quando um tópico tem menos de **6 questões** não vistas recentemente, aparece um aviso sugerindo apertar "Gerar questões". A geração nunca é automática.
- A geração roda em segundo plano. O usuário pode continuar usando o app enquanto isso.
- **Nenhuma questão é gerada durante a sessão diária.** A sessão usa só o que já está no banco, abre na hora e não depende do Claude.

### 3.5 Questão com erro
- Botão **"Essa questão está errada"** em qualquer questão gerada, durante ou depois da sessão.
- A questão invalidada é tratada **como se não existisse**:
  - sai do banco e nunca mais é sorteada;
  - **não conta** no desempenho da revisão em que apareceu;
  - não entra em estatísticas.
- Motivo opcional: gabarito errado, ambígua, fora do tópico.

---

## 4. Agendamento (revisão espaçada)

### 4.1 Unidade
O agendamento é **por tópico**, não por questão. Assim o usuário não decora a resposta de uma questão específica: a cada revisão saem questões diferentes do mesmo assunto.

### 4.2 Escada de intervalos
| Etapa | Intervalo até a próxima revisão |
|---|---|
| 0 (cadastro) | 1 dia |
| 1 | 3 dias |
| 2 | 7 dias |
| 3 | 15 dias |
| 4 | 30 dias |
| 5 | 60 dias (só uma vez) |
| 6 – manutenção | **30 dias, para sempre** |

- Depois de cumprir o intervalo de 60 dias, o tópico entra em **manutenção** e passa a ser revisado **a cada 30 dias**.
- Os intervalos contam a partir da **data em que a revisão foi feita**, e não da data prevista.
- Valores configuráveis.

> Inspiração original do usuário: dia 1 estudo → dia 2 → dia 5 → dia 10 → dia 20 → dia 40.

### 4.3 Questões por revisão
- Primeira revisão (etapa 0 → 1): **3 questões** por tópico.
- Demais revisões: **5 questões** por tópico.
- Valores configuráveis.

### 4.4 Regra adaptativa
Ao final de cada revisão, o desempenho do tópico **naquela sessão**, desconsiderando questões invalidadas, define a etapa seguinte:

| Acerto no tópico | Efeito |
|---|---|
| **≥ 80%** | Avança uma etapa. Na manutenção, continua em manutenção |
| **50% a 79%** | Repete a etapa atual (mesmo intervalo) |
| **< 50%** | Volta para a etapa 0 (revisão em 1 dia) |

### 4.5 Novo erro no Tec num tópico já existente
Se o usuário enviar uma nova questão real **errada** num tópico que já existe, o tópico volta para a **etapa 0** (revisão em 1 dia) e a questão entra no banco com prioridade. Uma questão real **certa** ou **não respondida** não altera a etapa.

### 4.6 Atrasos
- Dias sem estudar não geram penalidade automática. Os tópicos vencidos se acumulam e entram na próxima sessão.
- Há um **limite diário de tópicos** configurável. Por padrão não há limite.
- Quando o limite está ativo e o acúmulo passa dele, a sessão prioriza os tópicos **mais atrasados** e os que têm **mais erros recentes**. Os demais passam para o dia seguinte.

---

## 5. Sessão diária

### 5.1 Composição
- **Uma sessão única** com todos os tópicos cuja próxima revisão é **hoje ou antes**, respeitando o limite diário, se houver.
- Todas as matérias misturadas, com as questões **embaralhadas**, como num simulado.

### 5.2 Sorteio de questões por tópico
1. Mira **metade reais e metade geradas** em cada tópico. Quando não há reais suficientes, as geradas completam, e vice-versa.
2. Entre as reais, têm prioridade as **erradas no Tec** e as menos revistas.
3. Evita, quando houver alternativa, questões vistas nas **últimas 2 revisões** do tópico.
4. **Repetir questões é normal.** Não há limite de quantas vezes uma questão pode voltar ao longo do tempo. A janela do item 3 só evita repetição muito próxima.
5. Nunca repete a mesma questão dentro da mesma sessão.
6. Questões invalidadas nunca entram.
7. **Tópico vencido sem banco:** se o usuário ainda não apertou "Gerar questões", as questões reais já enviadas do tópico entram na sessão mesmo assim. Se o tópico não tiver nenhuma questão, ele fica fora da sessão com o aviso "gere questões para este tópico" e continua vencido.

### 5.3 Experiência de resposta (estilo Tec)
- Uma questão por vez: o usuário marca a alternativa e confirma.
- Feedback imediato: certo ou errado, gabarito destacado, justificativa e dispositivo legal.
- Botão **"Explicar melhor"**, que chama o Claude (**Sonnet, esforço alto**) sob demanda.
- Botão **"Essa questão está errada"** (seção 3.5).

### 5.4 Fim da sessão
- Resumo por tópico: acertos/total, etapa anterior → nova etapa, próxima data.
- Resumo geral do dia.
- Lista das questões erradas na sessão, cada uma com **"Explicar melhor"** (Sonnet, esforço alto).

### 5.5 Continuidade entre dispositivos
- O estado da sessão fica no servidor. A sessão pode ser **pausada no serviço e retomada em casa**, ou o contrário.
- Uma sessão iniciada e não terminada continua aberta até ser concluída.
- A sessão aberta **mantém a composição do dia em que começou**. Tópicos que vencem nos dias seguintes não entram nela: ficam para a **próxima sessão**, que só pode começar depois que a atual for concluída.

---

## 6. Acesso e segurança

- O app fica acessível **somente pela tailnet** do usuário, sem Funnel e sem exposição pública.
- **Senha de acesso**, com valor padrão `9993`, alterável nas configurações. A senha é guardada como hash, nunca em texto puro.
- **3 tentativas erradas** bloqueiam o login por **1 hora**. O bloqueio é global, não por dispositivo: sem Funnel, só aparelhos da tailnet chegam à tela de login.
- O login **não expira**. Cada dispositivo fica logado até o usuário clicar em "Sair" ou trocar a senha. Trocar a senha desloga todos os dispositivos.
- A **API key**, quando configurada, fica **só no servidor** e nunca é enviada ao navegador. Na tela aparece mascarada (`sk-ant-…a1b2`).

---

## 7. Modos de IA

### 7.1 Modo assinatura (padrão)
- O backend chama o **Claude Code em modo não interativo** (`claude -p`) no PC de casa, logado na assinatura do usuário.
- É uso pessoal: uma pessoa, na própria máquina, dentro do uso individual comum previsto nos termos.
- Antes de cada chamada, o backend **remove `ANTHROPIC_API_KEY` do ambiente** do subprocesso. Se a variável existir, o Claude Code usa a key em vez da assinatura e passa a cobrar como API sem aviso.
- O custo é o limite de uso da assinatura, compartilhado com o uso normal do Claude.

### 7.2 Modo API key
- Nas configurações há um campo para a key e a chave **"Usar API key em vez da assinatura"**.
- A troca vale **na próxima chamada**, sem reiniciar o app.
- Neste modo:
  - geração de questões vai pela **Batch API** (50% de desconto);
  - instruções de estilo e texto-base usam **prompt caching**.

### 7.3 Modelos por tarefa (iguais nos dois modos, configuráveis)
| Tarefa | Modelo padrão | Esforço |
|---|---|---|
| Ler print ou texto colado, sugerir tópico e gabarito provisório | Claude Haiku 5.5 | baixo |
| Reler ("Reler com Sonnet") | Claude Sonnet 5.5 | baixo |
| "Gerar questões" (gerar e conferir gabaritos) | Claude Opus 5.5 | médio |
| "Explicar melhor" | Claude Sonnet 5.5 | **alto** |

### 7.4 Falhas
- Se a chamada no modo assinatura falhar (limite atingido, sessão do Claude Code expirada, `claude` não encontrado), o app mostra o erro e, se houver key configurada, oferece **"Tentar com API key"**. A troca nunca é automática.
- Gerações interrompidas ficam numa fila e podem ser retomadas.

---

## 8. Configurações do usuário

- Senha de acesso
- Modo de IA (assinatura ou API key) e a API key
- Modelo e esforço por tarefa
- Escada de intervalos e limiares da regra adaptativa
- Questões por revisão (primeira e demais)
- Proporção reais/geradas (padrão 50/50) e mínimo de geradas por tópico (padrão 5)
- Limiar do aviso de banco baixo (padrão 6)
- Limite diário de tópicos na sessão (padrão: sem limite)
- Estilo de banca (padrão: Vunesp)
