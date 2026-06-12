"""
Le os .md em data/knowledge/, gera chunks e embeddings e salva:
  data/chunks.json
  data/embeddings.npy

Rodar 1x sempre que mudar a base de conhecimento:
  python ingest.py
"""
from pathlib import Path
import numpy as np
from dotenv import load_dotenv

load_dotenv()

from core.chunking import build_all_chunks
from core.embeddings import get_embedder
from core.vector_store import VectorStore

BASE_DIR = Path(__file__).parent
KNOWLEDGE_DIR = BASE_DIR / "data" / "knowledge"
CHUNKS_PATH = BASE_DIR / "data" / "chunks.json"
EMB_PATH = BASE_DIR / "data" / "embeddings.npy"


def main():
    chunks = build_all_chunks(KNOWLEDGE_DIR)
    print(f"Total: {len(chunks)} chunks (de {KNOWLEDGE_DIR})\n")

    embedder = get_embedder()
    print("Gerando embeddings...")
    embeddings = embedder.embed([c["content"] for c in chunks])

    vs = VectorStore(chunks, embeddings)
    vs.save(CHUNKS_PATH, EMB_PATH)
    print(f"\nOK - {len(chunks)} chunks em {CHUNKS_PATH}")
    print(f"     matriz {embeddings.shape} em {EMB_PATH}")


if __name__ == "__main__":
    main()
