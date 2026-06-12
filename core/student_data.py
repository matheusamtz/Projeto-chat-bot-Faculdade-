"""
StudentData - acesso ao banco SQLite com matriculas, atividades, notas e frequencia.
"""
from __future__ import annotations
import sqlite3
from datetime import date
from pathlib import Path
from typing import Dict, List

DIAS_SEMANA = ("segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
               "sexta-feira", "sábado", "domingo")


def data_extenso(iso: str) -> str:
    """'2026-06-17' -> '2026-06-17 (quarta-feira)'. Evita que o LLM
    precise calcular (e errar) o dia da semana."""
    try:
        d = date.fromisoformat(iso)
        return f"{iso} ({DIAS_SEMANA[d.weekday()]})"
    except (ValueError, TypeError):
        return str(iso)


class StudentData:
    def __init__(self, db_path: Path):
        if not db_path.exists():
            raise FileNotFoundError(
                f"Banco nao encontrado em {db_path}. Rode 'python seed_db.py' primeiro."
            )
        self.db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def aluno(self, aluno_id: int = 1) -> Dict:
        with self._conn() as c:
            row = c.execute("SELECT * FROM alunos WHERE id = ?", (aluno_id,)).fetchone()
            return dict(row) if row else {}

    def matriculas(self, aluno_id: int = 1) -> List[Dict]:
        with self._conn() as c:
            rows = c.execute("""
                SELECT d.codigo, d.nome, d.horario, d.carga_horaria, d.semestre
                FROM matriculas m
                JOIN disciplinas d ON d.codigo = m.disciplina_codigo
                WHERE m.aluno_id = ?
                ORDER BY d.codigo
            """, (aluno_id,)).fetchall()
            return [dict(r) for r in rows]

    def proximas_atividades(self, aluno_id: int = 1, limit: int = 20) -> List[Dict]:
        with self._conn() as c:
            rows = c.execute("""
                SELECT a.tipo, a.descricao, a.data_entrega, a.peso,
                       d.nome AS disciplina, d.codigo AS disciplina_codigo
                FROM atividades a
                JOIN matriculas m ON m.disciplina_codigo = a.disciplina_codigo
                JOIN disciplinas d ON d.codigo = a.disciplina_codigo
                WHERE m.aluno_id = ? AND a.status = 'pendente' AND a.data_entrega >= ?
                ORDER BY a.data_entrega ASC LIMIT ?
            """, (aluno_id, date.today().isoformat(), limit)).fetchall()
            return [dict(r) for r in rows]

    def notas(self, aluno_id: int = 1) -> List[Dict]:
        with self._conn() as c:
            rows = c.execute("""
                SELECT a.descricao, a.peso, n.valor, d.nome AS disciplina, d.codigo
                FROM notas n
                JOIN atividades a ON a.id = n.atividade_id
                JOIN disciplinas d ON d.codigo = a.disciplina_codigo
                WHERE n.aluno_id = ? AND n.valor IS NOT NULL
                ORDER BY a.data_entrega DESC
            """, (aluno_id,)).fetchall()
            return [dict(r) for r in rows]

    def frequencia(self, aluno_id: int = 1) -> List[Dict]:
        with self._conn() as c:
            rows = c.execute("""
                SELECT f.disciplina_codigo AS codigo, d.nome,
                       f.aulas_dadas, f.faltas, d.carga_horaria
                FROM frequencia f
                JOIN disciplinas d ON d.codigo = f.disciplina_codigo
                WHERE f.aluno_id = ?
            """, (aluno_id,)).fetchall()
            return [dict(r) for r in rows]

    def build_context(self, aluno_id: int = 1) -> str:
        """Monta o bloco textual com tudo do aluno, pronto pra injetar no prompt."""
        aluno = self.aluno(aluno_id)
        if not aluno:
            return "Aluno nao encontrado."
        parts: List[str] = []
        parts.append(f"Aluno: {aluno['nome']} | Matricula: {aluno['matricula']}")
        parts.append(f"Curso: {aluno['curso']} | Semestre atual: {aluno['semestre_atual']}o")
        parts.append("")
        parts.append("Disciplinas em que esta matriculado neste semestre:")
        for m in self.matriculas(aluno_id):
            parts.append(f"  - {m['codigo']}: {m['nome']} ({m['carga_horaria']}h, {m['horario']})")
        parts.append("")
        parts.append("Proximas atividades pendentes (ordenadas por data):")
        prox = self.proximas_atividades(aluno_id)
        if not prox:
            parts.append("  Nenhuma atividade pendente.")
        else:
            hoje = date.today()
            for p in prox:
                dias = (date.fromisoformat(p["data_entrega"]) - hoje).days
                parts.append(
                    f"  - {data_extenso(p['data_entrega'])}, daqui a {dias} dia(s): "
                    f"{p['tipo'].upper()} de {p['disciplina']} - "
                    f"{p['descricao']} (peso {int(p['peso']*100)}%)"
                )
        parts.append("")
        parts.append("Notas recebidas:")
        ns = self.notas(aluno_id)
        if not ns:
            parts.append("  Nenhuma nota lancada ainda.")
        else:
            for n in ns:
                parts.append(f"  - {n['disciplina']}: {n['descricao']} = {n['valor']}/10")
        parts.append("")
        parts.append("Frequencia:")
        for fr in self.frequencia(aluno_id):
            pct = (fr["faltas"] / fr["aulas_dadas"]) * 100 if fr["aulas_dadas"] else 0
            alerta = "  >>> ATENCAO (proximo do limite de 25%)" if pct >= 20 else ""
            parts.append(
                f"  - {fr['nome']}: {fr['faltas']}/{fr['aulas_dadas']} faltas ({pct:.1f}%){alerta}"
            )
        parts.append(f"\nData de hoje: {data_extenso(date.today().isoformat())}")
        return "\n".join(parts)
