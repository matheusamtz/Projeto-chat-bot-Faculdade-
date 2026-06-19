# Especificações da 1ª Entrega — Assistente Acadêmico "Acadêmico"

**Autor:** Matheus Alves
**Curso:** Ciência de Dados e Machine Learning — CEUB
**Data:** 2026-05-14
**Autor:** Thiago derani
**Curso:** Ads — CEUB
**Data:** 2026-05-14

---

## 1. Visão geral

"Acadêmico" é um chatbot que ajuda o aluno do curso de Ciência de Dados e Machine Learning do CEUB a tirar dúvidas sobre o conteúdo das disciplinas e a acompanhar sua vida acadêmica (próximas provas, prazos de entrega, notas e frequência). Combina duas técnicas: **Retrieval-Augmented Generation (RAG)** sobre o material textual das matérias e **consulta direta a um banco relacional** com os dados estruturados do aluno. Um LLM (modelo de linguagem) recebe esses dois contextos e gera respostas em linguagem natural via streaming.

O objetivo desta primeira entrega é demonstrar a arquitetura completa funcionando ponta a ponta: ingestão da base de conhecimento, persistência dos dados do aluno, busca semântica, integração com LLM e interface web utilizável.

---

## 2. Stack tecnológica

| Camada | Tecnologia | Função |
|---|---|---|
| Frontend | HTML + CSS + JavaScript vanilla + marked.js | Interface dark mode com chat em streaming |
| Backend | Python 3.10+ com Flask 3 | API REST (rotas `/`, `/api/student`, `/api/chat`) |
| Embeddings | sentence-transformers (`paraphrase-multilingual-MiniLM-L12-v2`, 384 dim) | Vetorização local da base de conhecimento e das queries |
| Vetor store | NumPy em memória (`embeddings.npy` + `chunks.json`) | Busca por similaridade do cosseno via produto interno |
| Dados estruturados | SQLite | Aluno, disciplinas, matrículas, atividades, notas, frequência |
| LLM (chat) | OpenRouter como gateway (modelo padrão: `openai/gpt-4o-mini`) | Geração das respostas em streaming SSE |
| Configuração | python-dotenv (`.env`) | Chaves de API e parâmetros do sistema |

---

## 3. Arquitetura

```
   USUÁRIO
      │
      ▼ digita pergunta
┌─────────────────────────┐
│       index.html        │  UI dark mode, sidebar com matérias e provas,
│  (browser, JS vanilla)  │  área de chat com streaming token a token
└────────────┬────────────┘
             │ POST /api/chat  { message, history }
             ▼
┌─────────────────────────┐         ┌───────────────────────────┐
│         app.py          │ ──────▶ │  embeddings.npy + chunks  │  (RAG)
│       (Flask)           │         │       — NumPy em RAM       │
│                         │ ──────▶ │  student.db (SQLite)       │  (dados do aluno)
│  1) embed da pergunta   │         └───────────────────────────┘
│  2) top-5 chunks (cos)  │
│  3) contexto do aluno   │ ──────▶ ┌───────────────────────────┐
│  4) chama LLM streaming │         │   LLM via OpenRouter      │
└────────────┬────────────┘         └───────────────────────────┘
             │ Server-Sent Events
             ▼
   resposta em streaming
```

### Fluxo de uma mensagem

1. O frontend envia a pergunta do usuário e o histórico recente para `/api/chat`.
2. O backend gera o embedding da pergunta usando o modelo local de sentence-transformers.
3. Compara o vetor da pergunta com todos os vetores da base (62 chunks atualmente) via produto interno em vetores normalizados — isso é matematicamente equivalente à similaridade do cosseno.
4. Seleciona os 5 trechos mais similares com score ≥ 0,20.
5. Consulta o SQLite para montar um bloco de contexto com matrículas, próximas atividades, notas e frequência do aluno.
6. Monta o prompt final com: system prompt + dados do aluno + chunks recuperados + histórico + pergunta atual.
7. Chama o LLM com `stream=True` e repassa os tokens para o frontend via Server-Sent Events.
8. Ao final, envia também as fontes consultadas (arquivo + seção + score), exibidas no UI como referências.

---

## 4. Base de conhecimento

A base é composta por **10 arquivos Markdown** organizados em `data/knowledge/`:

| Arquivo | Conteúdo | Chunks gerados |
|---|---|---|
| `institucional.md` | Sobre o CEUB, curso, regras gerais, frequência mínima, calendário | 9 |
| `grade-curricular.md` | Visão geral dos 7 semestres, pré-requisitos, trilhas temáticas | 10 |
| `processos-academicos.md` | Aprovação, trancamento, aproveitamento, TCC, 2ª chamada | 10 |
| `disciplinas-1-semestre.md` | ALGA, BDI, BOOTI, ES, ICD, LP (detalhado) | 6 |
| `disciplinas-2-semestre.md` | BDII, BII, CC, DCDI, FSC | 5 |
| `disciplinas-3-semestre.md` | BDN, BOOTII, BIII, DCDII, ECD, PE | 6 |
| `disciplinas-4-semestre.md` | AMML, FBD, OACD, RI | 4 |
| `disciplinas-5-semestre.md` | APDL, BD NoSQL, BI, PI I | 4 |
| `disciplinas-6-semestre.md` | APS, DS IA, PI II, VD | 4 |
| `disciplinas-7-semestre.md` | ED, PLN, PI III, SD | 4 |
| **Total** |  | **62 chunks** |

Cada chunk tem em média **445 caracteres** (mín 32, máx 977). A divisão é feita por seção (`##` no Markdown), com fallback para janela deslizante quando uma seção excede 2.200 caracteres.

---

## 5. Dados estruturados do aluno

O banco SQLite (`data/student.db`) tem 6 tabelas:

- **alunos** — perfil (id, nome, email, matrícula, curso, semestre atual, ano ingresso)
- **disciplinas** — catálogo completo das 31 disciplinas do curso (código, nome, semestre, carga, pré-requisito, horário)
- **matriculas** — quais disciplinas o aluno está cursando em qual semestre/ano
- **atividades** — provas, trabalhos, listas, projetos (com data, peso, status)
- **notas** — notas das atividades já corrigidas
- **frequencia** — aulas dadas e faltas por disciplina

### Snapshot atual (aluno: Matheus Alves)

- **Semestre:** 1º
- **Matriculado em:** ALGA, BDI, BOOTI, ES, ICD, LP
- **7 atividades pendentes** (próximas em ordem):
  - Lista 3 de LP (10/05, peso 10%)
  - **P1 de ALGA** (13/05, peso 40%) — vetores, matrizes, determinantes
  - Trabalho de ICD (15/05, peso 30%) — EDA com Titanic
  - **P1 de BDI** (17/05, peso 40%) — modelagem ER e SQL básico
  - Trabalho de ES (20/05, peso 20%) — diagrama de casos de uso
  - **P1 de LP** (23/05, peso 40%) — lógica e estruturas básicas
  - Entrega 1 do BOOTI (28/05, peso 25%)
- **6 notas lançadas** (listas iniciais, todas entre 7,5 e 9,5)
- **Frequência:** atenção em ES (16,7% de faltas — próximo do limite de 25%)

---

## 6. O que o chat responde — exemplos por categoria

O sistema responde **três tipos de pergunta**, classificados pela natureza do dado consultado:

### 6.1. Perguntas de CONTEÚDO (usam apenas RAG)

São dúvidas sobre o material das disciplinas. O bot busca trechos relevantes na base de conhecimento e responde com base neles.

| Pergunta do aluno | O que o bot consulta |
|---|---|
| "Explica produto escalar com exemplo" | Trechos de ALGA |
| "Diferença entre 1FN, 2FN e 3FN" | Trechos de BDI (normalização) |
| "Como funciona o CRISP-DM?" | Trechos de ICD |
| "O que é o método ágil Scrum?" | Trechos de ES |
| "Para que serve Python no curso?" | Trechos de LP e DCDI |
| "Quando vou usar cálculo no curso?" | Trechos de CC, AMML, OACD |
| "Como funciona PCA?" | Trechos de AMML/ALGA |
| "O que é RAG?" | Trechos de RI/PLN (meta — sobre o próprio sistema!) |

### 6.2. Perguntas de CALENDÁRIO/SITUAÇÃO (usam apenas SQL)

São dúvidas sobre o estado do aluno: provas marcadas, notas, frequência. O bot consulta o SQLite.

| Pergunta do aluno | Resposta esperada |
|---|---|
| "Quais provas eu tenho essa semana?" | Lista P1 de ALGA (13/05) e P1 de BDI (17/05) |
| "Como tá minha frequência em ES?" | "4 faltas em 24 aulas (16,7%) — atenção ao limite" |
| "Quais minhas notas até agora?" | Lista as 6 listas corrigidas com valores |
| "Em quais disciplinas estou matriculado?" | Lista as 6 do 1º semestre |
| "Quantas faltas posso ter em Cálculo?" | Não está matriculado em CC — bot informa isso |
| "Qual o peso da próxima entrega?" | "Lista 3 de LP, dia 10/05, peso 10%" |

### 6.3. Perguntas HÍBRIDAS (RAG + SQL — onde o sistema mostra valor real)

O bot combina dados estruturados com conteúdo da base para responder de forma personalizada.

| Pergunta do aluno | O que o bot faz |
|---|---|
| "Tenho prova de ALGA daqui 5 dias, me ajuda a revisar" | (1) Confirma data da P1 via SQL; (2) Busca em ALGA os tópicos cobrados; (3) Monta plano de revisão |
| "Qual matéria tô pior e o que estudar?" | (1) Calcula menor média via SQL; (2) Busca conteúdo da matéria; (3) Sugere estudo focado |
| "Minha próxima prova de BDI cobre o que?" | (1) SQL retorna "P1 de BDI — Modelagem ER e SQL básico"; (2) RAG traz explicação de ER e SQL básico |
| "Me dá um plano de estudos pra essa semana" | (1) SQL: 7 atividades pendentes; (2) RAG: conteúdo de cada uma; (3) Bot organiza cronograma |
| "Posso faltar amanhã em ES?" | SQL mostra 16,7% de faltas + processos-academicos.md sobre limite de 25% — bot calcula e alerta |

### 6.4. Regras que o bot segue (system prompt)

O comportamento é controlado por um system prompt explícito que define:

1. **Anti-alucinação:** "Baseie-se EXCLUSIVAMENTE no contexto fornecido. Se não houver informação suficiente, diga 'não tenho essa informação'."
2. **Datas e notas:** "NUNCA invente datas, notas, prazos ou nomes de disciplinas. Sempre cite o que está nos dados estruturados."
3. **Tom:** "Português brasileiro, acolhedor e direto, como veterano ajudando calouro."
4. **Formato:** Markdown (negrito, listas, blocos de código).
5. **Especificidade:** Sempre cita a disciplina ou a data ao responder.
6. **Pró-atividade:** Alerta sobre prazos curtos, frequência crítica, notas baixas.
7. **Fallback:** "Em dúvida, indicar procurar coordenação ou professor."

---

## 7. Funcionalidades implementadas

- [x] Chat web responsivo com dark mode
- [x] Sidebar com perfil do aluno, disciplinas matriculadas e próximas atividades coloridas por urgência (verde / amarelo / vermelho)
- [x] Streaming token a token via Server-Sent Events
- [x] Renderização Markdown nas respostas (listas, negrito, código)
- [x] Indicação visual das fontes consultadas (chunks de origem + score de similaridade)
- [x] Histórico de conversa mantido no frontend e enviado ao backend nas últimas 6 mensagens
- [x] Prompts sugeridos clicáveis na tela inicial
- [x] Atalhos: clicar em uma disciplina ou atividade gera prompt pré-preenchido
- [x] Busca vetorial em memória com filtro de score mínimo (0,20)
- [x] Backend configurável: troca de provedor LLM e modelo via `.env` sem mexer no código
- [x] Suporte a dois backends de embedding: local (sentence-transformers) e OpenAI (`text-embedding-3-small`)

---

## 8. Limitações conhecidas

- **Single-user:** todo o sistema assume um único aluno (id=1). Multiusuário exige autenticação e isolamento de dados.
- **Histórico não persistido:** as conversas só vivem na sessão do navegador. Recarregar a página perde o contexto.
- **Sem re-ranking:** a busca usa top-5 cru, sem segunda passada por LLM para reordenar. Funciona bem na base atual (62 chunks) mas pode degradar com bases maiores.
- **Sem avaliação automática:** ainda não há métricas medindo qualidade do retrieval (precision@k, MRR). Será adicionado na próxima entrega.
- **Datas codificadas no seed:** as atividades são geradas com `data_entrega` relativa a "hoje". Em um sistema real essas datas viriam do sistema acadêmico da instituição.

---

## 9. Próximos passos (entregas seguintes)

1. Persistir conversas em SQLite para manter contexto entre sessões.
2. Implementar re-ranking com o próprio LLM para melhorar precisão da busca.
3. Adicionar conjunto de teste anotado e calcular métricas de retrieval (precision@k, recall@k, MRR).
4. Comparar pelo menos 3 modelos de embedding (MiniLM, multilingual-e5-large, BGE-M3) com métricas concretas — material de estudo para Probabilidade e Estatística e Aprendizagem de Máquina.
5. Estudo de impacto da estratégia de chunking (por seção vs janela deslizante vs por unidade) na qualidade do retrieval.
6. Roteamento explícito de intenção (conteúdo / calendário / híbrido) com classificador, em vez de sempre injetar tudo no contexto.
7. Deploy em produção (Vercel ou Render) — README já traz instruções.

---

## 10. Estrutura de arquivos do projeto

```
.
├── app.py                  # backend Flask (rotas /, /api/student, /api/chat)
├── ingest.py               # gera embeddings da base de conhecimento
├── embeddings.py           # camada de embedding (local ou OpenAI)
├── seed_db.py              # cria e popula o SQLite do aluno
├── requirements.txt        # dependências Python
├── .env                    # configuração local (não vai pro repositório)
├── .env.example            # template documentado das variáveis
├── .gitignore
├── README.md               # instruções de setup e arquitetura
├── ESPECIFICACOES.md       # este documento
├── data/
│   ├── knowledge/          # 10 arquivos .md com o conteúdo das disciplinas
│   ├── chunks.json         # 62 chunks com texto e metadados
│   ├── embeddings.npy      # matriz NumPy 62×384 com vetores normalizados
│   └── student.db          # banco do aluno (6 tabelas)
└── templates/
    └── index.html          # interface completa (CSS + JS embutidos)
```

---

## 11. Como executar

```bash
python -m venv .venv
.venv\Scripts\activate                 # Windows
pip install -r requirements.txt        # ~5-10 min na primeira vez
python seed_db.py                      # popula o banco do aluno
python ingest.py                       # baixa modelo (120MB) e gera embeddings
python app.py                          # sobe em http://localhost:5000
```

O `.env` já está configurado com chave do OpenRouter e modelo `openai/gpt-4o-mini`. Para trocar de modelo, basta editar a variável `CHAT_MODEL`.
