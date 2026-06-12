"""
VectorStore - busca vetorial em memoria.
Encapsula a matriz de embeddings (NumPy) e a lista de chunks alinhada com ela.
Usa similaridade do cosseno via produto interno em vetores normalizados.

Tambem oferece busca HIBRIDA (search_hybrid): combina o cosseno semantico
com um cosseno lexical TF-IDF. Em corpora pequenos com vocabulario tecnico
distintivo, o lexical complementa bem o semantico (ver data/retrieval_*.json).
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np


class VectorStore:
    def __init__(self, chunks: List[Dict], embeddings: np.ndarray):
        if len(chunks) != embeddings.shape[0]:
            raise ValueError(
                f"len(chunks)={len(chunks)} difere de embeddings.shape[0]={embeddings.shape[0]}"
            )
        self.chunks = chunks
        self.embeddings = embeddings
        # Normaliza por seguranca (idempotente se ja normalizado)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        self.normalized = embeddings / np.clip(norms, 1e-12, None)
        # Indice lexical TF-IDF, construido sob demanda (so quem usa hibrido paga)
        self._tfidf = None
        self._tfidf_matrix = None

    @property
    def dim(self) -> int:
        return self.embeddings.shape[1]

    @property
    def size(self) -> int:
        return len(self.chunks)

    @classmethod
    def load(cls, chunks_path: Path, embeddings_path: Path) -> "VectorStore":
        if not chunks_path.exists() or not embeddings_path.exists():
            raise FileNotFoundError(
                f"Faltam artefatos. Rode 'python ingest.py' primeiro.\n"
                f"  chunks: {chunks_path}\n  embeddings: {embeddings_path}"
            )
        with open(chunks_path, encoding="utf-8") as f:
            chunks = json.load(f)
        embeddings = np.load(embeddings_path)
        return cls(chunks, embeddings)

    def save(self, chunks_path: Path, embeddings_path: Path) -> None:
        chunks_path.parent.mkdir(parents=True, exist_ok=True)
        with open(chunks_path, "w", encoding="utf-8") as f:
            json.dump(self.chunks, f, ensure_ascii=False, indent=2)
        np.save(embeddings_path, self.embeddings)

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> List[Dict]:
        """
        Retorna os top_k chunks mais similares.
        query_vector deve estar normalizado (cosine = dot product).
        """
        q = query_vector
        if q.ndim == 2:
            q = q[0]
        # garante normalizacao
        nq = np.linalg.norm(q)
        if nq > 0:
            q = q / nq
        scores = self.normalized @ q
        return self._top_k(scores, top_k, min_score)

    def _ensure_lexical_index(self) -> None:
        if self._tfidf is not None:
            return
        from sklearn.feature_extraction.text import TfidfVectorizer
        self._tfidf = TfidfVectorizer(
            ngram_range=(1, 2), min_df=1, max_df=0.95,
            sublinear_tf=True, lowercase=True, strip_accents="unicode",
        )
        self._tfidf_matrix = self._tfidf.fit_transform(
            [c["content"] for c in self.chunks]
        )

    def search_hybrid(
        self,
        query_text: str,
        query_vector: np.ndarray,
        top_k: int = 5,
        min_score: float = 0.0,
        alpha: float = 0.5,
    ) -> List[Dict]:
        """
        Busca hibrida: score = alpha * cos_semantico + (1 - alpha) * cos_tfidf.
        alpha=1.0 equivale a search(); alpha=0.0 e TF-IDF puro.
        Vetores TF-IDF saem L2-normalizados, entao produto interno = cosseno.
        """
        self._ensure_lexical_index()
        q = query_vector
        if q.ndim == 2:
            q = q[0]
        nq = np.linalg.norm(q)
        if nq > 0:
            q = q / nq
        sem = self.normalized @ q
        lex = (self._tfidf_matrix @ self._tfidf.transform([query_text]).T).toarray().ravel()
        scores = alpha * sem + (1.0 - alpha) * lex
        return self._top_k(scores, top_k, min_score)

    def _top_k(self, scores: np.ndarray, top_k: int, min_score: float) -> List[Dict]:
        order = np.argsort(-scores)[:top_k]
        out: List[Dict] = []
        for i in order:
            score = float(scores[i])
            if score < min_score:
                break
            c = self.chunks[i]
            out.append({
                "source": c["source"],
                "section": c["section"],
                "content": c["content"],
                "score": score,
            })
        return out
