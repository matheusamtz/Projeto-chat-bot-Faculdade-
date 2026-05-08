"""
Backend Flask do chatbot acadêmico.
Arquitetura: RAG (busca vetorial em memória) + dados estruturados (SQLite) + LLM em streaming.
"""
import os
import json
import sqlite3
from datetime import date
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from flask import Flask, jsonify, request, Response, render_template
from openai import OpenAI

from embeddings import get_embedder

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
CHAT_MODEL = os.getenv("CHAT_MODEL", "openai/gpt-4o-mini")
PORT = int(os.getenv("FLASK_PORT", "5000"))

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "student.db"
CHUNKS_PATH = BASE_DIR / "data" / "chunks.json"
EMB_PATH = BASE_DIR / "data" / "embeddings.npy"

# ----------------- carga inicial -----------------
print("Carregando base de conhecimento...")
if not CHUNKS_PATH.exists() or not EMB_PATH.exists():
    raise SystemExit(
        "Embeddings nao encontrados. Rode 'python ingest.py' antes de subir o servidor."
    )
with open(CHUNKS_PATH, encoding="utf-8") as f:
    CHUNKS = json.load(f)
EMBEDDINGS = np.load(EMB_PATH)
EMB_NORM = EMBEDDINGS / np.clip(np.linalg.norm(EMBEDDINGS, axis=1, keepdims=True), 1e-12, None)
print(f"  {len(CHUNKS)} chunks carregados, matriz {EMBEDDINGS.shape}")

if not DB_PATH.exists():
    raise SystemExit("Banco SQLite nao encontrado. Rode 'python seed_db.py' primeiro.")

if not OPENAI_API_KEY:
    raise SystemExit("Defina OPENAI_API_KEY no .env.")

EMBEDDER = get_embedder()
client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

# ----------------- system prompt -----------------
SYSTEM_PROMPT = """Você é o "Acadêmico", um assistente do aluno de Ciência de Dados e Machine Learning do CEUB.

REGRAS CRÍTICAS:
1. Baseie-se EXCLUSIVAMENTE no contexto fornecido (matérias, dados do aluno, processos acadêmicos). Se não houver informação suficiente, diga claramente "não tenho essa informação".
2. NUNCA invente datas, notas, prazos ou nomes de disciplinas. Sempre cite o que está nos dados estruturados quando responder sobre calendário, frequência ou notas.
3. Responda em português brasileiro, com tom acolhedor e direto, como um veterano que ajuda calouro.
4. Use markdown para clareza: **negrito** para destaques, listas quando útil, blocos de código com ```python para exemplos.
5. Quando responder sobre conteúdo de matéria, mencione a disciplina (ex: "em ALGA você verá..."). Quando responder sobre calendário/notas, mencione a data ou disciplina específica.
6. Seja prático: se o aluno tem prova chegando, ajude a planejar revisão. Se a frequência está perto do limite, alerte. Se a nota está baixa, sugira ações.
7. Não dê palpite sobre coisas que você não tem certeza. Em dúvida, indique procurar a coordenação ou o professor.
"""


# ----------------- vector search -----------------
def embed_query(text: str) -> np.ndarray:
    v = EMBEDDER.embed([text])[0]
    return v / max(np.linalg.norm(v), 1e-12)


def vector_search(query: str, top_k: int = 5, min_score: float = 0.25):
    qv = embed_query(query)
    scores = EMB_NORM @ qv
    idx = np.argsort(-scores)[:top_k]
    out = []
    for i in idx:
        if scores[i] < min_score:
            break
        c = CHUNKS[i]
        out.append({
            "source": c["source"],
            "section": c["section"],
            "content": c["content"],
            "score": float(scores[i]),
        })
    return out


# ----------------- dados do aluno (SQLite) -----------------
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_student_context(aluno_id: int = 1) -> str:
    with db() as conn:
        aluno = conn.execute(
            "SELECT * FROM alunos WHERE id = ?", (aluno_id,)
        ).fetchone()

        matriculas = conn.execute("""
            SELECT d.codigo, d.nome, d.horario, d.carga_horaria, d.semestre
            FROM matriculas m JOIN disciplinas d ON d.codigo = m.disciplina_codigo
            WHERE m.aluno_id = ?
            ORDER BY d.codigo
        """, (aluno_id,)).fetchall()

        proximas = conn.execute("""
            SELECT a.tipo, a.descricao, a.data_entrega, a.peso, d.nome AS disciplina
            FROM atividades a
            JOIN matriculas m ON m.disciplina_codigo = a.disciplina_codigo
            JOIN disciplinas d ON d.codigo = a.disciplina_codigo
            WHERE m.aluno_id = ? AND a.status = 'pendente' AND a.data_entrega >= ?
            ORDER BY a.data_entrega ASC
        """, (aluno_id, date.today().isoformat())).fetchall()

        notas = conn.execute("""
            SELECT a.descricao, a.peso, n.valor, d.nome AS disciplina
            FROM notas n
            JOIN atividades a ON a.id = n.atividade_id
            JOIN disciplinas d ON d.codigo = a.disciplina_codigo
            WHERE n.aluno_id = ? AND n.valor IS NOT NULL
            ORDER BY a.data_entrega DESC
        """, (aluno_id,)).fetchall()

        freq = conn.execute("""
            SELECT f.disciplina_codigo, d.nome, f.aulas_dadas, f.faltas, d.carga_horaria
            FROM frequencia f JOIN disciplinas d ON d.codigo = f.disciplina_codigo
            WHERE f.aluno_id = ?
        """, (aluno_id,)).fetchall()

    parts = []
    parts.append(f"Aluno: {aluno['nome']} | Matrícula: {aluno['matricula']}")
    parts.append(f"Curso: {aluno['curso']} | Semestre atual: {aluno['semestre_atual']}º")
    parts.append("")
    parts.append("Disciplinas em que está matriculado neste semestre:")
    for m in matriculas:
        parts.append(f"  - {m['codigo']}: {m['nome']} ({m['carga_horaria']}h, {m['horario']})")
    parts.append("")
    parts.append("Próximas atividades pendentes (ordenadas por data):")
    if not proximas:
        parts.append("  Nenhuma atividade pendente.")
    else:
        for p in proximas:
            parts.append(
                f"  - {p['data_entrega']}: {p['tipo'].upper()} de {p['disciplina']} - "
                f"{p['descricao']} (peso {int(p['peso']*100)}%)"
            )
    parts.append("")
    parts.append("Notas recebidas:")
    if not notas:
        parts.append("  Nenhuma nota lançada ainda.")
    else:
        for n in notas:
            parts.append(f"  - {n['disciplina']}: {n['descricao']} = {n['valor']}/10")
    parts.append("")
    parts.append("Frequência:")
    for fr in freq:
        pct_falta = (fr["faltas"] / fr["aulas_dadas"]) * 100 if fr["aulas_dadas"] else 0
        alerta = "  >>> ATENÇÃO" if pct_falta >= 20 else ""
        parts.append(
            f"  - {fr['nome']}: {fr['faltas']}/{fr['aulas_dadas']} faltas "
            f"({pct_falta:.1f}%){alerta}"
        )

    parts.append(f"\nData de hoje: {date.today().isoformat()}")
    return "\n".join(parts)


# ----------------- Flask app -----------------
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/student")
def student():
    with db() as conn:
        aluno = dict(conn.execute("SELECT * FROM alunos WHERE id = 1").fetchone())
        matriculas = [dict(r) for r in conn.execute("""
            SELECT d.codigo, d.nome, d.horario
            FROM matriculas m JOIN disciplinas d ON d.codigo = m.disciplina_codigo
            WHERE m.aluno_id = 1 ORDER BY d.codigo
        """).fetchall()]
        proximas = [dict(r) for r in conn.execute("""
            SELECT a.tipo, a.descricao, a.data_entrega, d.nome AS disciplina,
                   d.codigo AS disciplina_codigo
            FROM atividades a
            JOIN matriculas m ON m.disciplina_codigo = a.disciplina_codigo
            JOIN disciplinas d ON d.codigo = a.disciplina_codigo
            WHERE m.aluno_id = 1 AND a.status = 'pendente' AND a.data_entrega >= ?
            ORDER BY a.data_entrega ASC LIMIT 5
        """, (date.today().isoformat(),)).fetchall()]
    return jsonify({"aluno": aluno, "matriculas": matriculas, "proximas": proximas})


@app.route("/api/chat", methods=["POST"])
def chat():
    payload = request.get_json(force=True)
    user_msg = payload.get("message", "").strip()
    history = payload.get("history", [])
    if not user_msg:
        return jsonify({"error": "mensagem vazia"}), 400

    rag_chunks = vector_search(user_msg, top_k=5, min_score=0.20)
    student_ctx = get_student_context(aluno_id=1)

    ctx_parts = []
    ctx_parts.append("===== DADOS ESTRUTURADOS DO ALUNO =====")
    ctx_parts.append(student_ctx)
    if rag_chunks:
        ctx_parts.append("\n===== TRECHOS DA BASE DE CONHECIMENTO =====")
        for i, c in enumerate(rag_chunks, 1):
            ctx_parts.append(f"--- Trecho {i} (fonte: {c['source']}, "
                             f"seção: {c['section']}, similaridade: {c['score']:.2f}) ---")
            ctx_parts.append(c["content"])
    contexto = "\n".join(ctx_parts)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + contexto},
    ]
    for h in history[-6:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": user_msg})

    def generate():
        try:
            stream = client.chat.completions.create(
                model=CHAT_MODEL,
                messages=messages,
                stream=True,
                temperature=0.4,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield f"data: {json.dumps({'delta': delta})}\n\n"
            sources = [{"source": c["source"], "section": c["section"],
                        "score": round(c["score"], 3)} for c in rag_chunks]
            yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


if __name__ == "__main__":
    print(f"Servindo em http://localhost:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=True, threaded=True)
