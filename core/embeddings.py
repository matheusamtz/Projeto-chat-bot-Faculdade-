"""
Backends de embedding intercambiaveis.
  - "local"  -> sentence-transformers (multilingual, sem custo, sem API)
  - "openai" -> OpenAI text-embedding-3-small (precisa OPENAI_EMBEDDING_API_KEY)

Selecionado pela env var EMBEDDING_BACKEND no .env.
"""
from __future__ import annotations
import os
from typing import List
import numpy as np


def get_embedder():
    """Factory: devolve um objeto com .embed(list[str]) -> np.ndarray (N x D)."""
    backend = os.getenv("EMBEDDING_BACKEND", "local").lower()
    if backend == "openai":
        return _OpenAIEmbedder()
    return _LocalEmbedder()


class _LocalEmbedder:
    """Sentence-transformers local. Sem custo, sem API."""

    def __init__(self):
        from sentence_transformers import SentenceTransformer
        model_name = os.getenv(
            "LOCAL_EMBEDDING_MODEL",
            "paraphrase-multilingual-MiniLM-L12-v2",
        )
        print(f"  [embeddings] carregando '{model_name}'...")
        self.model = SentenceTransformer(model_name)
        self.dim = self.model.get_sentence_embedding_dimension()
        print(f"  [embeddings] modelo pronto, dim={self.dim}")

    def embed(self, texts: List[str]) -> np.ndarray:
        vecs = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        ).astype(np.float32)
        return vecs


class _OpenAIEmbedder:
    """OpenAI text-embedding-3-small (ou large)."""

    def __init__(self):
        from openai import OpenAI
        self.model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self.client = OpenAI(
            api_key=os.environ["OPENAI_EMBEDDING_API_KEY"],
            base_url=os.getenv("OPENAI_EMBEDDING_BASE_URL",
                               "https://api.openai.com/v1"),
        )
        self.dim = 1536 if "small" in self.model else 3072

    def embed(self, texts: List[str]) -> np.ndarray:
        out: List[List[float]] = []
        for i in range(0, len(texts), 64):
            batch = texts[i:i + 64]
            resp = self.client.embeddings.create(model=self.model, input=batch)
            out.extend([d.embedding for d in resp.data])
        m = np.array(out, dtype=np.float32)
        norms = np.linalg.norm(m, axis=1, keepdims=True)
        return m / np.clip(norms, 1e-12, None)
