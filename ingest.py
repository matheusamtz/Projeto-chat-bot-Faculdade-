"""
Le os .md em data/knowledge/, quebra em chunks por secao (##),
gera embeddings (locais por padrao) e salva:
  - data/chunks.json    (texto + metadados de cada chunk)
  - data/embeddings.npy (matriz numpy [N x D] alinhada com chunks.json)

Roda 1x sempre que mudar a base de conhecimento:
    python ingest.py
"""
import re
import json
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
KNOWLEDGE_DIR = BASE_DIR / "data" / "knowledge"
CHUNKS_PATH = BASE_DIR / "data" / "chunks.json"
EMB_PATH = BASE_DIR / "data" / "embeddings.npy"

MAX_CHARS_PER_CHUNK = 2200


def split_by_section(text: str):
    parts = re.split(r"\n## ", text)
    chunks = []
    head = parts[0].strip()
    head_title = ""
    if head.startswith("# "):
        first_line, _, rest = head.partition("\n")
        head_title = first_line.lstrip("# ").strip()
        head = rest.strip()
    if head:
        chunks.append((head_title or "intro", head))
    for p in parts[1:]:
        title, _, body = p.partition("\n")
        chunks.append((title.strip(), body.strip()))
    return chunks


def smart_chunks(file_path: Path):
    raw = file_path.read_text(encoding="utf-8")
    out = []
    for section_title, body in split_by_section(raw):
        if not body:
            continue
        if len(body) <= MAX_CHARS_PER_CHUNK:
            out.append({
                "source": file_path.name,
                "section": section_title,
                "content": f"[{section_title}]\n{body}",
            })
        else:
            paragraphs = body.split("\n\n")
            buf = ""
            for para in paragraphs:
                if len(buf) + len(para) + 2 > MAX_CHARS_PER_CHUNK and buf:
                    out.append({
                        "source": file_path.name,
                        "section": section_title,
                        "content": f"[{section_title}]\n{buf.strip()}",
                    })
                    buf = ""
                buf += para + "\n\n"
            if buf.strip():
                out.append({
                    "source": file_path.name,
                    "section": section_title,
                    "content": f"[{section_title}]\n{buf.strip()}",
                })
    return out


def main():
    md_files = sorted(KNOWLEDGE_DIR.glob("*.md"))
    if not md_files:
        raise SystemExit(f"Nenhum .md encontrado em {KNOWLEDGE_DIR}/")

    all_chunks = []
    for f in md_files:
        chunks = smart_chunks(f)
        print(f"  {f.name:38s} -> {len(chunks):3d} chunks")
        all_chunks.extend(chunks)
    print(f"\nTotal: {len(all_chunks)} chunks")

    from embeddings import get_embedder
    embedder = get_embedder()

    print("Gerando embeddings...")
    texts = [c["content"] for c in all_chunks]
    embeddings = embedder.embed(texts)

    CHUNKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)
    np.save(EMB_PATH, embeddings)

    print(f"\nOK - {len(all_chunks)} chunks salvos em {CHUNKS_PATH}")
    print(f"     matriz {embeddings.shape} salva em {EMB_PATH}")


if __name__ == "__main__":
    main()
