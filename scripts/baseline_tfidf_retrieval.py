"""
Baseline de retrieval usando TF-IDF.

Existe para tres motivos:
  1. Servir de baseline de comparacao com embeddings semanticos.
     "Embeddings densos so valem se baterem o TF-IDF" (Karpukhin et al. 2020).
  2. Permitir rodar a avaliacao sem precisar instalar sentence-transformers.
  3. Material de comparacao quantitativa para o relatorio (RAG semantico vs lexical).

Uso:
  python scripts/baseline_tfidf_retrieval.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from statistics import mean

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.chunking import build_all_chunks

KNOWLEDGE_DIR = BASE_DIR / "data" / "knowledge"
TEST_SET_PATH = BASE_DIR / "evaluation_data" / "retrieval_test_set.json"
METRICS_PATH = BASE_DIR / "data" / "retrieval_metrics_tfidf.json"

K_VALUES = (1, 3, 5)


def metrics_for(hits_bool, hits_unique, n_rel):
    out = {}
    for k in K_VALUES:
        p = sum(hits_bool[:k]) / k
        r = sum(hits_unique[:k]) / n_rel if n_rel else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
        out[f"P@{k}"] = p
        out[f"R@{k}"] = r
        out[f"F1@{k}"] = f1
    # Reciprocal Rank
    rr = 0.0
    for i, h in enumerate(hits_bool, 1):
        if h:
            rr = 1.0 / i
            break
    out["RR"] = rr
    return out


def main():
    print("=== Baseline TF-IDF do retrieval ===\n")
    print("Construindo chunks...")
    chunks = build_all_chunks(KNOWLEDGE_DIR)
    print(f"  {len(chunks)} chunks gerados")

    print("Vetorizando com TF-IDF (palavra 1-2gram)...")
    texts = [c["content"] for c in chunks]
    vec = TfidfVectorizer(
        ngram_range=(1, 2), min_df=1, max_df=0.95,
        sublinear_tf=True, lowercase=True, strip_accents="unicode",
    )
    M = vec.fit_transform(texts)
    print(f"  matriz {M.shape} (vocabulario={len(vec.vocabulary_)})")

    with open(TEST_SET_PATH, encoding="utf-8") as f:
        ts = json.load(f)
    queries = ts["queries"]

    Q = vec.transform([q["query"] for q in queries])
    sims = cosine_similarity(Q, M)

    rows = []
    for i, q in enumerate(queries):
        scores = sims[i]
        order = np.argsort(-scores)[:5]
        retrieved_sources = [chunks[j]["source"] for j in order]
        relevant_set = set(q["relevant_sources"])

        hits_bool = [src in relevant_set for src in retrieved_sources]
        hits_unique = []
        seen = set()
        for src in retrieved_sources:
            is_hit = src in relevant_set and src not in seen
            hits_unique.append(is_hit)
            if is_hit:
                seen.add(src)

        m = metrics_for(hits_bool, hits_unique, len(relevant_set))
        m["query"] = q["query"]
        m["relevant_sources"] = list(relevant_set)
        m["retrieved_top5"] = retrieved_sources
        m["scores_top5"] = [round(float(scores[j]), 3) for j in order]
        rows.append(m)

    agg = {"n_queries": len(rows)}
    for k in K_VALUES:
        agg[f"P@{k}"] = mean(r[f"P@{k}"] for r in rows)
        agg[f"R@{k}"] = mean(r[f"R@{k}"] for r in rows)
        agg[f"F1@{k}"] = mean(r[f"F1@{k}"] for r in rows)
    agg["MRR"] = mean(r["RR"] for r in rows)

    print("\n" + "=" * 70)
    print(f"{'Metrica':<10} {'@1':>10} {'@3':>10} {'@5':>10}")
    print("-" * 70)
    print(f"{'Precision':<10} "
          f"{agg['P@1']:>10.4f} {agg['P@3']:>10.4f} {agg['P@5']:>10.4f}")
    print(f"{'Recall':<10} "
          f"{agg['R@1']:>10.4f} {agg['R@3']:>10.4f} {agg['R@5']:>10.4f}")
    print(f"{'F1':<10} "
          f"{agg['F1@1']:>10.4f} {agg['F1@3']:>10.4f} {agg['F1@5']:>10.4f}")
    print(f"\n{'MRR':<10} {agg['MRR']:>10.4f}")
    print("=" * 70)

    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump({"aggregate": agg, "per_query": rows}, f,
                  ensure_ascii=False, indent=2)
    print(f"\nMetricas salvas em {METRICS_PATH}")
    print("\nDica: rode 'python scripts/evaluate_retrieval.py' (com embeddings semanticos)")
    print("      e compare com estes numeros - a diferenca eh o ganho do RAG semantico.")


if __name__ == "__main__":
    main()
