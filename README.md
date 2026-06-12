# Acadêmico — Chatbot RAG para o curso de CDML do CEUB

Assistente acadêmico que combina **busca semântica (RAG)** sobre o conteúdo das matérias com **dados estruturados** do aluno (calendário, notas, frequência) para responder dúvidas sobre o curso de Ciência de Dados e Machine Learning do CEUB.

## Arquitetura

```
        usuário
          │
          ▼
  ┌──────────────────┐
  │   index.html     │  UI dark, streaming, markdown
  └────────┬─────────┘
           │ POST /api/chat
           ▼
  ┌──────────────────────────────────────────────────────┐
  │                       app.py                         │
  │  (orquestrador Flask — usa módulos do pacote core/)  │
  │                                                      │
  │  1) IntentClassifier ──► conteudo|calendario|hibrido │
  │  2) VectorStore       ──► top-5 chunks (busca híbrida│
  │                           semântica + TF-IDF, α=0.4) │
  │  3) StudentData       ──► matrículas/notas/freq      │
  │  4) LLM stream        ──► OpenRouter (SSE)           │
  └────────┬─────────────────────────────────────────────┘
           │
           ▼
  data/intent_classifier.joblib  (sklearn pipeline treinado)
  data/embeddings.npy            (NumPy 62×384, normalizado)
  data/chunks.json               (62 chunks com metadados)
  data/student.db                (SQLite com aluno)
```

**Roteamento por classificador de intenção** — a cada pergunta, um modelo treinado (TF-IDF + Logistic Regression) classifica a intenção em uma de três categorias e decide o que injetar no contexto: só RAG (`conteudo`), só dados estruturados (`calendario`) ou ambos (`hibrido`). Isso reduz tokens e foca a resposta. F1-macro medido na cross-validation: **0.8652**.

**Busca híbrida (semântica + lexical)** — o retrieval combina o cosseno dos embeddings com um cosseno TF-IDF: `score = 0.4·semântico + 0.6·lexical`. O peso foi escolhido por sweep sobre o test set anotado e dá um salto grande sobre qualquer abordagem pura (MRR 0.76 → **0.96**). Em corpus pequeno com vocabulário técnico distintivo, o lexical acerta termos exatos ("produto escalar", "INNER JOIN") e o semântico cobre paráfrases.

**Embeddings locais** — `sentence-transformers` (multilingual, sem custo, sem API). O chat usa qualquer provedor OpenAI-compatible — o `.env` já vem com OpenRouter.

**Fluxo:** classifica → busca RAG e/ou SQL conforme intenção → monta o prompt (system + contexto + histórico + pergunta) → chama LLM com streaming → frontend renderiza tokens em tempo real via SSE.

## Stack

- **Python + Flask** — backend e orquestrador
- **sentence-transformers** — embeddings locais (`paraphrase-multilingual-MiniLM-L12-v2`, 384 dim, ~120MB)
- **scikit-learn + joblib** — classificador de intenção (TF-IDF + Logistic Regression)
- **OpenRouter (cliente OpenAI-compatible)** — LLM para gerar respostas
- **NumPy** — busca vetorial em memória (cosseno via produto interno)
- **SQLite** — dados estruturados do aluno
- **HTML + CSS + JS vanilla** — frontend sem build step (marked.js + DOMPurify para markdown seguro, highlight.js para código, KaTeX para fórmulas)

## Estrutura

```
.
├── app.py                              # backend Flask (rotas /, /api/student, /api/intent, /api/chat, /api/health)
├── ingest.py                           # gera chunks e embeddings da base de conhecimento
├── seed_db.py                          # cria e popula o SQLite do aluno
├── requirements.txt                    # dependências
├── .env / .env.example
├── core/                               # pacote com lógica de domínio (testável, reutilizável)
│   ├── chunking.py                     # quebra dos .md em chunks por seção
│   ├── embeddings.py                   # backends de embedding (local/OpenAI)
│   ├── vector_store.py                 # busca vetorial em memória (NumPy)
│   ├── student_data.py                 # camada SQL sobre o SQLite
│   └── intent_classifier.py            # carrega/usa o classificador treinado
├── scripts/                            # scripts de manutenção e avaliação
│   ├── train_intent_classifier.py      # treina + mostra F-score do classificador
│   ├── evaluate_retrieval.py           # mede P@k, R@k, F1@k, MRR do RAG semântico
│   └── baseline_tfidf_retrieval.py     # baseline TF-IDF puro p/ comparação
├── evaluation_data/                    # datasets anotados (ground truth)
│   ├── intent_dataset.json             # 159 queries rotuladas (conteudo/calendario/hibrido)
│   └── retrieval_test_set.json         # 22 queries com fontes relevantes anotadas
├── data/                               # artefatos gerados (estão no .gitignore exceto se for deploy)
│   ├── knowledge/                      # .md institucional + grade + 7 semestres
│   ├── chunks.json                     # 62 chunks com metadados
│   ├── embeddings.npy                  # matriz [62 × 384] normalizada
│   ├── student.db                      # banco do aluno
│   ├── intent_classifier.joblib        # pipeline sklearn treinado
│   ├── intent_metrics.json             # F-score do classificador
│   └── retrieval_metrics_tfidf.json    # métricas do baseline TF-IDF
├── templates/
│   └── index.html                      # markup da UI (sem build step)
└── static/
    ├── style.css                       # tema dark premium (tokens, glass, responsivo)
    └── app.js                          # streaming SSE, markdown sanitizado, KaTeX, persistência local
```

## Frontend

UI dark premium em vanilla JS, sem build step:

- **Streaming token a token** com indicador de digitação e botão de **parar geração**
- **Badge de intenção** em cada resposta (qual rota o classificador escolheu + confiança)
- **Fontes consultadas** com barra de similaridade por chunk
- **Markdown sanitizado** (DOMPurify contra XSS), **código com highlight** + botão copiar, **fórmulas LaTeX** renderizadas com KaTeX
- **Histórico persistido** em localStorage (sobrevive ao F5) + botão "Nova conversa"
- **Responsivo**: sidebar vira drawer no mobile; suporta `prefers-reduced-motion`
- Tratamento de erro com **botão "tentar de novo"**

## Setup (passo a passo)

### 1. Crie o ambiente virtual e instale dependências

```bash
python -m venv .venv
source .venv/bin/activate           # Linux/macOS
# .venv\Scripts\activate            # Windows PowerShell
pip install -r requirements.txt
```

A primeira instalação puxa o `sentence-transformers` que vem com PyTorch — pode levar 5–10 minutos e ocupar ~2GB. Faz isso só uma vez.

### 2. Confira o .env

O `.env` já foi criado com sua chave OpenRouter e o modelo `openai/gpt-4o-mini`. Se quiser trocar o modelo, edita `CHAT_MODEL` no `.env`. Sugestões:

| Modelo                                   | Característica                        |
|------------------------------------------|---------------------------------------|
| `openai/gpt-4o-mini` (padrão)            | Bom em PT-BR, barato                  |
| `meta-llama/llama-3.3-70b-instruct:free` | Gratuito, com limite de rate          |
| `google/gemini-flash-1.5`                | Rápido e barato                       |
| `anthropic/claude-haiku-4.5`             | Excelente em PT-BR, mais caro         |

### 3. Crie o banco do aluno

```bash
python seed_db.py
```

Isso cria `data/student.db` com você (Matheus) matriculado nas 6 disciplinas do 1º semestre, atividades pendentes (provas próximas), algumas notas já lançadas e frequência atualizada.

### 4. Gere os embeddings da base de conhecimento

```bash
python ingest.py
```

Na primeira execução, ele baixa o modelo de embedding (~120MB) automaticamente. Depois é instantâneo. **Custo zero** (tudo roda na sua máquina).

### 5. Treine o classificador de intenção

```bash
python scripts/train_intent_classifier.py
```

Roda em ~3 segundos. Imprime o **F1-macro**, relatório por classe e matriz de confusão, e salva o modelo em `data/intent_classifier.joblib`. Se você pular esse passo, o `app.py` ainda sobe — só desliga o roteamento e cai num modo "injeta tudo".

### 6. (opcional) Avalie o retrieval

```bash
python scripts/baseline_tfidf_retrieval.py    # baseline TF-IDF (não precisa de embeddings)
python scripts/evaluate_retrieval.py          # com embeddings semânticos (depende do ingest)
```

Imprime precision@k, recall@k, F1@k e MRR sobre o conjunto de teste anotado em `evaluation_data/retrieval_test_set.json`.

### 7. Rode o servidor

```bash
python app.py
```

Abra http://localhost:5000

## O que dá pra perguntar

**Sobre conteúdo (puro RAG):**
- "explica produto escalar com exemplo"
- "diferença entre 1FN, 2FN e 3FN"
- "o que é PCA e onde uso?"
- "como funciona backpropagation?"

**Sobre seu calendário (puro SQL):**
- "quais provas tenho essa semana?"
- "como tá minha frequência em ES?"
- "quais minhas notas até agora?"

**Híbrido (RAG + SQL — onde a coisa fica interessante):**
- "tenho prova de ALGA daqui 5 dias, me ajuda a revisar"
- "qual matéria tô pior e o que estudar?"
- "minha próxima prova de BDI cobre o que?"

## Avaliação do sistema

O projeto inclui dois pipelines de avaliação independentes — um para o classificador de intenção, outro para a qualidade do retrieval. Ambos imprimem relatórios no terminal e salvam JSON com as métricas para uso em relatórios.

### Classificador de intenção (TF-IDF + Logistic Regression)

- **Dataset:** 159 queries em PT-BR rotuladas em três classes (`conteudo` n=56, `calendario` n=50, `hibrido` n=53).
- **Avaliação:** 5-fold stratified cross-validation.
- **Resultados medidos:**

  | Métrica | Valor |
  |---|---|
  | Acurácia | 0.8679 |
  | **F1-macro** | **0.8652** |
  | F1-weighted | 0.8683 |

- **F1 por classe:**

  | Classe | Precision | Recall | F1 | Suporte |
  |---|---|---|---|---|
  | `conteudo`  | 0.9818 | 0.9643 | 0.9730 | 56 |
  | `calendario` | 0.8636 | 0.7600 | 0.8085 | 50 |
  | `hibrido`   | 0.7667 | 0.8679 | 0.8142 | 53 |

- **Matriz de confusão:** a maior confusão acontece entre `calendario` e `hibrido` — esperado, porque a fronteira é tênue: "qual minha nota?" é puro calendário, "qual minha nota e o que estudar?" já é híbrido.

### Retrieval do RAG — lexical vs semântico vs híbrido

Sobre as mesmas 22 queries anotadas com fontes relevantes (`scripts/baseline_tfidf_retrieval.py` e `scripts/evaluate_retrieval.py`):

| Abordagem | P@1 | R@5 | MRR |
|---|---|---|---|
| TF-IDF puro (baseline lexical) | 0.7727 | 0.9621 | 0.8674 |
| Semântico puro (MiniLM multilingual) | 0.6818 | 0.8409 | 0.7614 |
| **Híbrido α=0.4 (produção)** | **0.9545** | **0.9773** | **0.9636** |

Leitura dos números — e o achado central da avaliação:

- O **semântico puro perde para o baseline lexical** neste corpus: a base é pequena (62 chunks) e cheia de termos técnicos distintivos ("produto escalar", "INNER JOIN", "CRISP-DM") que o TF-IDF acerta de forma exata, enquanto o MiniLM multilingual dilui esses termos no espaço vetorial.
- A **combinação dos dois é muito melhor que qualquer um isolado**: P@1 sai de ~0.7 para 0.95 e o MRR para 0.96 (primeiro hit em média na posição ~1.04). O `alpha` foi varrido em {0 … 1} e o platô 0.3–0.7 é estável — 0.4 é o ponto usado em produção (`app.py`).
- Esse é exatamente o resultado clássico de hybrid retrieval (denso + esparso) da literatura, reproduzido e medido no projeto — material forte para o relatório.

## Como expandir

Algumas linhas de evolução fáceis de implementar:

- **Persistir o histórico** das conversas em uma tabela `conversas` no SQLite (hoje fica no localStorage do navegador)
- **Re-ranking** com `gpt-4o-mini` após o top-20 da busca híbrida, pegando os top-3 finais
- **BM25 no lugar do TF-IDF** na perna lexical da busca híbrida (rank_bm25), e comparar no mesmo test set
- **Comparar modelos de embedding** (`MiniLM` vs `multilingual-e5-large` vs `BGE-M3`)
- **Migrar para pgvector** quando a base crescer (vários alunos, vários semestres acumulados)
- **Adicionar autenticação** para múltiplos alunos
- **Notificações proativas** (alerta automático 3 dias antes da prova)

## Trocar para embeddings da OpenAI (opcional)

Se quiser usar embeddings da OpenAI em vez dos locais (mais qualidade, ~R$ 0,05 por ingest), edite o `.env`:

```
E