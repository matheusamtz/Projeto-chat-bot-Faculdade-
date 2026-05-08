"""
Cria o banco SQLite com schema acadêmico e popula com dados de exemplo.
Roda 1x antes de subir o servidor: python seed_db.py
"""
import os
import sqlite3
from datetime import date, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = str(BASE_DIR / "data" / "student.db")
os.makedirs(BASE_DIR / "data", exist_ok=True)

# Apaga banco anterior se existir, para sempre começar limpo
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# -------- SCHEMA --------
cur.executescript("""
CREATE TABLE alunos (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    matricula TEXT UNIQUE NOT NULL,
    curso TEXT NOT NULL,
    semestre_atual INTEGER NOT NULL,
    ano_ingresso INTEGER NOT NULL
);

CREATE TABLE disciplinas (
    codigo TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    semestre INTEGER NOT NULL,
    carga_horaria INTEGER NOT NULL,
    pre_requisito TEXT,
    horario TEXT
);

CREATE TABLE matriculas (
    id INTEGER PRIMARY KEY,
    aluno_id INTEGER NOT NULL,
    disciplina_codigo TEXT NOT NULL,
    ano INTEGER NOT NULL,
    semestre_letivo INTEGER NOT NULL,
    FOREIGN KEY(aluno_id) REFERENCES alunos(id),
    FOREIGN KEY(disciplina_codigo) REFERENCES disciplinas(codigo)
);

CREATE TABLE atividades (
    id INTEGER PRIMARY KEY,
    disciplina_codigo TEXT NOT NULL,
    tipo TEXT NOT NULL,            -- prova, trabalho, lista, projeto
    descricao TEXT NOT NULL,
    data_entrega DATE NOT NULL,
    peso REAL NOT NULL,            -- 0..1
    status TEXT NOT NULL,          -- pendente, entregue, corrigida
    FOREIGN KEY(disciplina_codigo) REFERENCES disciplinas(codigo)
);

CREATE TABLE notas (
    id INTEGER PRIMARY KEY,
    aluno_id INTEGER NOT NULL,
    atividade_id INTEGER NOT NULL,
    valor REAL,                    -- 0..10, NULL se ainda não corrigida
    FOREIGN KEY(aluno_id) REFERENCES alunos(id),
    FOREIGN KEY(atividade_id) REFERENCES atividades(id)
);

CREATE TABLE frequencia (
    id INTEGER PRIMARY KEY,
    aluno_id INTEGER NOT NULL,
    disciplina_codigo TEXT NOT NULL,
    aulas_dadas INTEGER NOT NULL,
    faltas INTEGER NOT NULL,
    FOREIGN KEY(aluno_id) REFERENCES alunos(id),
    FOREIGN KEY(disciplina_codigo) REFERENCES disciplinas(codigo)
);
""")

# -------- ALUNO --------
cur.execute(
    "INSERT INTO alunos VALUES (?, ?, ?, ?, ?, ?, ?)",
    (1, "Matheus Alves", "matheusalvesia70@gmail.com", "2025/1-CDML-0042",
     "Ciência de Dados e Machine Learning", 1, 2025),
)

# -------- DISCIPLINAS (todos os semestres do curso) --------
disciplinas = [
    # 1º
    ("ALGA",  "Álgebra Linear e Geometria Analítica", 1, 60, None,   "Qua 08:00–09:40, 10:00–10:50"),
    ("BDI",   "Banco de Dados I",                     1, 60, None,   "Sex 08:00–09:40, 10:00–10:50"),
    ("BOOTI", "Bootcamp I",                           1, 75, None,   "Atividade intensiva"),
    ("ES",    "Engenharia de Software",               1, 60, None,   "Ter 08:00–09:40, 10:00–10:50"),
    ("ICD",   "Introdução à Ciência de Dados",        1, 60, None,   "Qui 08:00–09:40, 10:00–10:50"),
    ("LP",    "Lógica de Programação",                1, 60, None,   "Seg 08:00–09:40, 10:00–10:50"),
    # 2º
    ("BDII",  "Banco de Dados II",                    2, 60, "BDI",  "Seg 08:00–09:40, 10:00–10:50"),
    ("BII",   "Business Intelligence I",              2, 60, None,   "Sex 08:00–09:40, 10:00–10:50"),
    ("CC",    "Cálculo para Computação",              2, 60, None,   "Ter 08:00–09:40, 10:00–10:50"),
    ("DCDI",  "Desenvolvimento para Ciência de Dados I", 2, 60, "LP", "Qua 08:00–09:40, 10:00–10:50"),
    ("FSC",   "Fundamentos de Segurança Cibernética", 2, 60, None,   "Qui 08:00–09:40, 10:00–10:50"),
    # 3º
    ("BDN",   "Banco de Dados NoSQL",                 3, 60, "BDI",  "Seg 08:00–09:40, 10:00–10:50"),
    ("BOOTII","Bootcamp II",                          3, 75, None,   "Atividade intensiva"),
    ("BIII",  "Business Intelligence II",             3, 60, "BII",  "Ter 08:00–09:40, 10:00–10:50"),
    ("DCDII", "Desenvolvimento para Ciência de Dados II", 3, 60, "DCDI", "Qua 08:00–09:40, 10:00–10:50"),
    ("ECD",   "Estruturas para Ciência de Dados",     3, 60, "DCDI", "Qui 08:00–09:40, 10:00–10:50"),
    ("PE",    "Probabilidade e Estatística",          3, 60, None,   ""),
    # 4º
    ("AMML",  "Aprendizagem de Máquina (Machine Learning)", 4, 75, "IA", "Ter 08:00–09:40, 10:00–10:50"),
    ("FBD",   "Fundamentos de Big Data",              4, 75, None,   "Qui 08:00–09:40, 10:00–10:50"),
    ("OACD",  "Otimização Aplicada à Ciência de Dados",4, 75, None,  "Qua 08:00–09:40, 10:00–10:50"),
    ("RI",    "Recuperação da Informação",            4, 75, None,   "Seg 08:00–09:40, 10:00–10:50"),
    # 5º
    ("APDL",  "Aprendizagem Profunda (Deep Learning)",5, 75, "AMML", "Sex 08:00–09:40, 10:00–10:50"),
    ("PI_I",  "Projeto Integrador I",                 5, 90, None,   "Qui 08:00–09:40, 10:00–10:50"),
    # 6º
    ("APS",   "Análise e Projeto de Sistemas",        6, 75, None,   "Qua 08:00–09:40, 10:00–10:50"),
    ("DSIA",  "Desenvolvimento de Sistemas de IA",    6, 75, None,   "Seg 08:00–09:40, 10:00–10:50"),
    ("PI_II", "Projeto Integrador II",                6, 90, "PI_I", "Sex 08:00–09:40, 10:00–10:50"),
    ("VD",    "Visualização de Dados",                6, 75, None,   "Ter 08:00–09:40, 10:00–10:50"),
    # 7º
    ("ED",    "Engenharia de Dados",                  7, 75, None,   "Qui 08:00–09:40, 10:00–10:50"),
    ("PLN",   "Processamento de Linguagem Natural",   7, 75, None,   "Seg 08:00–09:40, 10:00–10:50"),
    ("PI_III","Projeto Integrador III",               7, 90, "PI_II","Qua 08:00–09:40, 10:00–10:50"),
    ("SD",    "Segurança de Dados",                   7, 75, None,   "Ter 08:00–09:40, 10:00–10:50"),
]
cur.executemany(
    "INSERT INTO disciplinas VALUES (?, ?, ?, ?, ?, ?)", disciplinas
)

# -------- MATRÍCULAS DO MATHEUS (1º semestre 2025) --------
disciplinas_matriculadas = ["ALGA", "BDI", "BOOTI", "ES", "ICD", "LP"]
for cod in disciplinas_matriculadas:
    cur.execute(
        "INSERT INTO matriculas (aluno_id, disciplina_codigo, ano, semestre_letivo) VALUES (?, ?, ?, ?)",
        (1, cod, 2025, 1),
    )

# -------- ATIVIDADES (datas relativas a "hoje") --------
hoje = date.today()
def d(delta_days):
    return (hoje + timedelta(days=delta_days)).isoformat()

atividades = [
    # disciplina, tipo, descricao, data_entrega, peso, status
    ("LP",    "lista", "Lista 3 — Estruturas de repetição (while/for)", d(2),  0.10, "pendente"),
    ("ALGA",  "prova", "P1 — Vetores, matrizes e determinantes",        d(5),  0.40, "pendente"),
    ("ICD",   "trabalho", "EDA com dataset Titanic em Jupyter",         d(7),  0.30, "pendente"),
    ("BDI",   "prova", "P1 — Modelagem ER e SQL básico",                d(9),  0.40, "pendente"),
    ("ES",    "trabalho", "Diagrama de casos de uso do sistema XYZ",    d(12), 0.20, "pendente"),
    ("LP",    "prova", "P1 — Lógica e estruturas básicas",              d(15), 0.40, "pendente"),
    ("BOOTI", "projeto", "Entrega 1 — Definição de problema + dataset", d(20), 0.25, "pendente"),

    # Já entregues / corrigidas
    ("LP",   "lista", "Lista 1 — Variáveis e operadores",     d(-25), 0.05, "corrigida"),
    ("LP",   "lista", "Lista 2 — Condicionais (if/else)",     d(-15), 0.05, "corrigida"),
    ("ALGA", "lista", "Lista 1 — Vetores no plano",            d(-20), 0.05, "corrigida"),
    ("BDI",  "lista", "Lista 1 — Modelo ER",                   d(-18), 0.05, "corrigida"),
    ("ICD",  "lista", "Lista 1 — Pandas básico",               d(-10), 0.10, "corrigida"),
    ("ES",   "lista", "Lista 1 — Metodologias ágeis",          d(-22), 0.10, "corrigida"),
]
cur.executemany(
    "INSERT INTO atividades (disciplina_codigo, tipo, descricao, data_entrega, peso, status) "
    "VALUES (?, ?, ?, ?, ?, ?)", atividades,
)

# -------- NOTAS (só das atividades já corrigidas) --------
# Pega ids das atividades corrigidas e atribui notas
cur.execute("SELECT id, descricao FROM atividades WHERE status = 'corrigida'")
corrigidas = cur.fetchall()
notas_dict = {
    "Lista 1 — Variáveis e operadores": 8.5,
    "Lista 2 — Condicionais (if/else)": 9.0,
    "Lista 1 — Vetores no plano": 7.5,
    "Lista 1 — Modelo ER": 8.0,
    "Lista 1 — Pandas básico": 9.5,
    "Lista 1 — Metodologias ágeis": 8.0,
}
for aid, desc in corrigidas:
    valor = notas_dict.get(desc)
    cur.execute(
        "INSERT INTO notas (aluno_id, atividade_id, valor) VALUES (?, ?, ?)",
        (1, aid, valor),
    )

# -------- FREQUÊNCIA --------
# Considera ~12 semanas decorridas, 2 aulas por semana = 24 aulas dadas em média
frequencia = [
    ("ALGA",  24, 2),  # 8.3% de faltas
    ("BDI",   24, 0),  # zero faltas
    ("BOOTI", 10, 1),  # bootcamp tem menos encontros
    ("ES",    24, 4),  # 16.7% de faltas — atenção, próximo do limite!
    ("ICD",   24, 1),
    ("LP",    24, 3),  # 12.5% de faltas
]
for cod, aulas, faltas in frequencia:
    cur.execute(
        "INSERT INTO frequencia (aluno_id, disciplina_codigo, aulas_dadas, faltas) VALUES (?, ?, ?, ?)",
        (1, cod, aulas, faltas),
    )

conn.commit()
conn.close()

print(f"OK — banco criado em {DB_PATH}")
print("  - 1 aluno (Matheus)")
print(f"  - {len(disciplinas)} disciplinas")
print(f"  - {len(disciplinas_matriculadas)} matriculas (1º semestre)")
print(f"  - {len(atividades)} atividades")
print(f"  - {len(corrigidas)} notas")
print(f"  - {len(frequencia)} registros de frequência")
