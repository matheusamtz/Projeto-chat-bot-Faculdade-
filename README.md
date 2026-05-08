# Acadêmico — Chatbot RAG para o curso de CDML do CEUB

Assistente acadêmico que combina **busca semântica (RAG)** sobre o conteúdo das matérias com **dados estruturados** do aluno (calendário, notas, frequência) para responder dúvidas sobre o curso de Ciência de Dados e Machine Learning do CEUB

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
  ┌──────────────────┐       ┌────────────────────┐
  │     app.py       │──────▶│  embeddings.npy    │  (RAG)
  │   (Flask)        │       │  chunks.json       │
  │                  │──────▶│  student.db        │  (dados do aluno)
  └────────┬─────────┘       └────────────────────┘
           │ SSE stream
           ▼
       LLM via OpenRouter (gpt-4o-mini, llama-3.3, etc.)
```

A geração de embeddings roda **localmente** com `sentence-transformers` (modelo multilingual, sem custo, sem API). O **chat** usa qualquer provedor compatível com a API da OpenAI — o `.env` já vem configurado para **OpenRouter**.

Fluxo de uma mensagem: o backend gera o embedding da pergunta localmente, busca os trechos mais similares na base de conhecimento (busca vetorial em memória com numpy), monta um contexto com **dados estruturados do aluno** (matrículas, próximas atividades, notas, frequência) somados aos **trechos recuperados**, e chama o LLM com streaming. A resposta volta token a token via Server-Sent Events.

## Stack

- **Python + Flask** — backend
- **sentence-transformers** — embeddings locais (`paraphrase-multilingual-MiniLM-L12-v2`, 384 dim, ~120MB)
- **OpenRouter (cliente OpenAI compatível)** — LLM para gerar respostas (chat)
- **NumPy** — busca vetorial em memória (cosseno via produto interno)
- **SQLite** — dados estruturados do aluno
- **HTML + JS vanilla + marked.js** — frontend sem build step

## Estrutura

```
.
├── app.py                  # backend Flask (rotas /, /api/student, /api/chat)
├── ingest.py               # gera embeddings da base de conhecimento
├── embeddings.py           # camada de embeddings (local ou OpenAI)
├── seed_db.py              # cria e popula o SQLite do aluno
├── requirements.txt
├── .env                    # config real (NÃO comitar — está no .gitignore)
├── .env.example            # template documentado
├── data/
│   ├── knowledge/          # base de conhecimento (.md, um por semestre + institucional)
│   ├── chunks.json         # gerado por ingest.py
│   ├── embeddings.npy      # gerado por ingest.py
│   └── student.db          # gerado por seed_db.py
└── templates/
    └── index.html          # UI completa (CSS + JS embutidos)
```

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

### 5. Rode o servidor

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

## Como expandir

Algumas linhas de evolução fáceis de implementar:

- **Persistir o histórico** das conversas em uma tabela `conversas` no SQLite
- **Re-ranking** com `gpt-4o-mini` após o top-20 da busca vetorial, pegando os top-3 finais
- **Métricas de avaliação** do RAG (precision@k, MRR) com um conjunto fixo de perguntas anotadas — bom material para TCC
- **Comparar modelos de embedding** (`MiniLM` vs `multilingual-e5-large` vs `BGE-M3`)
- **Migrar para pgvector** quando a base crescer (vários alunos, vários semestres acumulados)
- **Adicionar autenticação** para múltiplos alunos
- **Notificações proativas** (alerta automático 3 dias antes da prova)

## Trocar para embeddings da OpenAI (opcional)

Se quiser usar embeddings da OpenAI em vez dos locais (mais qualidade, ~R$ 0,05 por ingest), edite o `.env`:

```
EMBEDDING_BACKEND=openai
OPENAI_EMBEDDING_API_KEY=sk-...           # chave OpenAI direta
OPENAI_EMBEDDING_BASE_URL=https://api.openai.com/v1
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

Depois rode `python ingest.py` de novo para regerar os embeddings.

## Custo estimado (config atual)

- Embeddings: **R$ 0** (rodam local)
- Por mensagem: ~R$ 0,002 com `gpt-4o-mini` no OpenRouter (~3.000 tokens de contexto)
- 100 mensagens/dia ≈ R$ 0,20/dia ≈ R$ 6/mês
- Com `meta-llama/llama-3.3-70b-instruct:free`: **R$ 0** (limitado a alguns rqps)

## Deploy na Vercel

A Vercel roda Python como **funções serverless** (limite de 250 MB por função). Isso muda duas coisas em relação ao desenvolvimento local:

1. **Embeddings precisam ser via OpenAI** em produção. `sentence-transformers + torch` (~1 GB) estoura o limite. Localmente continua funcionando — o `.vercelignore` mantém `requirements-dev.txt` fora do bundle.
2. **Os artefatos `data/student.db`, `data/chunks.json` e `data/embeddings.npy` precisam estar no repositório** no momento do deploy — eles são o "build" da base de conhecimento.

### 1) Pré-requisitos locais (uma única vez antes do primeiro deploy)

Você precisa de uma chave **real da OpenAI** (a do OpenRouter não serve para embeddings). Crie em https://platform.openai.com/api-keys.

No seu `.env` local, ajuste para gerar embeddings via OpenAI (a dimensão muda de 384 → 1536, então **tem que regerar**):

```env
EMBEDDING_BACKEND=openai
OPENAI_EMBEDDING_API_KEY=sk-...                 # chave OpenAI direta
OPENAI_EMBEDDING_BASE_URL=https://api.openai.com/v1
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

Depois rode:

```bash
pip install -r requirements.txt        # base (Flask, numpy, openai). Nao precisa de sentence-transformers para ingest via OpenAI.
python seed_db.py                       # gera data/student.db
python ingest.py                        # gera data/chunks.json e data/embeddings.npy via OpenAI
```

Custo do ingest: ~R$ 0,03 (≈ 30k tokens em `text-embedding-3-small`).

### 2) Suba para um repositório Git

```bash
git init
git add .
git commit -m "deploy inicial"
git remote add origin <url-do-seu-repo>
git push -u origin main
```

> O `.gitignore` já protege o `.env`. Os arquivos `data/student.db`, `data/chunks.json` e `data/embeddings.npy` **vão** para o repo de propósito — são os artefatos consumidos em runtime.

### 3) Importe na Vercel

- Em https://vercel.com/new, importe o repositório.
- **Framework Preset:** "Other" (a Vercel detecta o `vercel.json` e o runtime Python automaticamente).
- **Build/Output:** deixar em branco. O `vercel.json` cuida de tudo.

### 4) Configure as variáveis de ambiente no painel da Vercel

Em **Project Settings → Environment Variables**, adicione:

| Variável | Valor | Obs |
|---|---|---|
| `OPENAI_API_KEY` | `sk-or-v1-...` | sua chave OpenRouter (ou OpenAI direta) para o **chat** |
| `OPENAI_BASE_URL` | `https://openrouter.ai/api/v1` | ou `https://api.openai.com/v1` |
| `CHAT_MODEL` | `openai/gpt-4o-mini` | ou outro suportado pelo provedor |
| `EMBEDDING_BACKEND` | `openai` | **obrigatório** — backend local não cabe na Vercel |
| `OPENAI_EMBEDDING_API_KEY` | `sk-...` | chave **OpenAI direta** (OpenRouter não atende `/embeddings` igualzinho) |
| `OPENAI_EMBEDDING_BASE_URL` | `https://api.openai.com/v1` | |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | precisa bater com o modelo usado no ingest |

### 5) Deploy

Clique em "Deploy" — ou faça push e a Vercel deploya sozinha.

### Limitações conhecidas em serverless

- **Streaming SSE**: o runtime `@vercel/python` (AWS Lambda) tende a **bufferizar** a resposta. O front continua funcionando, mas a resposta chega "de uma vez" em vez de token a token. Se o streaming real for crítico, considere migrar essa rota para Edge Functions (Node) ou hospedar em Render/Fly.io/Railway.
- **Cold start**: a primeira requisição depois de ociosidade carrega `embeddings.npy` em memória — pode levar 2–4s. Requisições seguintes são instantâneas.
- **Filesystem read-only**: o SQLite é apenas lido (nada de gravar histórico no `student.db` em produção). Para persistir conversas, use Vercel Postgres / Neon / Turso.
- **Tamanho da função**: o bundle final fica em ~10 MB (Flask + numpy + openai + dados). Confortavelmente abaixo do limite.

### Alternativa: deploy em outras plataformas

Se quiser **manter os embeddings locais** (sem custo de OpenAI) e **streaming real**, plataformas com containers de longa duração funcionam melhor:

- **Render.com** (free tier, suporta o `requirements-dev.txt` inteiro)
- **Fly.io** (Dockerfile)
- **Railway** (idem)

Nesses casos, basta `python app.py` rodando no container — sem precisar de `vercel.json`/`api/index.py`.
