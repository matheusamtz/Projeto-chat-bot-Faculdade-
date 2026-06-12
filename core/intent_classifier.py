"""
IntentClassifier - classifica a intencao da pergunta do aluno em uma das tres
categorias: 'conteudo', 'calendario' ou 'hibrido'.

Usado pelo app.py para decidir como montar o contexto antes de chamar o LLM.

Modelo: TF-IDF (1-2 ngrams) + Regressao Logistica multinomial.
Persistencia: joblib (.joblib).
"""
from __future__ import annotations
from pathlib import Path
from typing import List, Tuple, Optional


LABELS = ("conteudo", "calendario", "hibrido")


class IntentClassifier:
    """Wrapper em torno do Pipeline sklearn treinado."""

    def __init__(self, pipeline=None):
        self.pipeline = pipeline

    @classmethod
    def load(cls, path: Path) -> "IntentClassifier":
        import joblib
        if not path.exists():
            raise FileNotFoundError(
                f"Classificador nao encontrado em {path}. "
                f"Rode 'python scripts/train_intent_classifier.py' primeiro."
            )
        pipe = joblib.load(path)
        return cls(pipeline=pipe)

    def save(self, path: Path) -> None:
        import joblib
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, path)

    def predict(self, query: str) -> str:
        return self.pipeline.predict([query])[0]

    def predict_proba(self, query: str) -> List[Tuple[str, float]]:
        """Retorna [(label, prob), ...] ordenado por prob desc."""
        probs = self.pipeline.predict_proba([query])[0]
        classes = self.pipeline.classes_
        pairs = sorted(zip(classes, probs), key=lambda x: -x[1])
        return [(c, float(p)) for c, p in pairs]
