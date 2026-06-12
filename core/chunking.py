"""
Chunking - quebra arquivos Markdown em chunks por secao (##).
Cada chunk vira uma unidade de busca para o RAG.
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import List, Dict, Tuple

MAX_CHARS_PER_CHUNK = 2200  # ~600 tokens de margem para o modelo de embedding


def split_by_section(text: str) -> List[Tuple[str, str]]:
    """Divide o texto em (titulo_secao, conteudo) usando '##' como separador."""
    parts = re.split(r"\n## ", text)
    chunks: List[Tuple[str, str]] = []
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


def smart_chunks(file_path: Path) -> List[Dict[str, str]]:
    """
    Gera chunks de um arquivo Markdown.
    Quebra primeiro por '##'. Se a secao excede MAX_CHARS_PER_CHUNK, divide em
    pedacos por paragrafos (\n\n) sem ultrapassar o limite.
    """
    raw = file_path.read_text(encoding="utf-8")
    out: List[Dict[str, str]] = []
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


def build_all_chunks(knowledge_dir: Path) -> List[Dict[str, str]]:
    """Quebra todos os .md de um diretorio em chunks."""
    md_files = sorted(knowledge_dir.glob("*.md"))
    if not md_files:
        raise FileNotFoundError(f"Nenhum .md em {knowledge_dir}/")
    all_chunks: List[Dict[str, str]] = []
    for f in md_files:
        chunks = smart_chunks(f)
        all_chunks.extend(chunks)
    return all_chunks
