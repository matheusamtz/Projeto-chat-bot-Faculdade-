"""
Avalia a qualidade do retrieval do RAG.

Para cada query do test set anotado:
  1. Gera o embedding da query.
  2. Recupera top-k chunks via VectorStore.
  3. Marca como "relevante" qualquer chunk cujo arquivo .md esta em
     relevant_sources daquela query (ground truth no nivel do arquivo).
  4. Calcula precision@k, recall@k e F1@k para k in {1, 3, 5}.
  5. Calcula MRR (Mean Reciprocal Rank) usando a posicao do primeiro hit.

Saidas:
  Stdout: relatorio formatado
  data/retrieval_metrics.json: metricas estruturadas

Pre-requisito: chunks.json e embeddings.npy ja gerados (rode 'python ingest.py').

Uso:
  python scripts/evaluate_retrieval.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from statistics import mean
from typing import List, Dict

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv()

from core.embeddings import get_embedder
from core.vector_store import VectorStore

TEST_SET_PATH = BASE_DIR / "evaluation_data" / "retrieval_test_set.json"
CHUNKS_PATH = BASE_DIR / "data" / "chunks.json"
EMB_PATH = BASE_DIR / "data" / "embeddings.npy"
METRICS_PATH = BASE_DIR / "data" / "retrieval_metrics.json"

K_VALUES = (1, 3, 5)
HYBRID_ALPHA = 0.4  # mesmo alpha usado em producao (app.py)


def precision_at_k(hits: List[bool], k: int) -> float:
    top = hits[:k]
    return sum(top) / k if top else 0.0


def recall_at_k(hits: List[bool], k: int, n_relevant: int) -> float:
    if n_relevant == 0:
        return 0.0
    return sum(hits[:k]) / n_relevant


def f1(p: float, r: float) -> float:
    if (p + r) == 0:
        return 0.0
    return 2 * p * r / (p + r)


def reciprocal_rank(hits: List[bool]) -> float:
    for i, h in enumerate(hits, 1):
        if h:
            return 1.0 / i
    return 0.0


def evaluate():
    print("=== Avaliacao do retrieval ===\n")
    with open(TEST_SET_PATH, encoding="utf-8") as f:
        ts = json.load(f)
    queries = ts["queries"]
    print(f"Test set: {len(queries)} queries anotadas")

    vs = VectorStore.load(CHUNKS_PATH, EMB_PATH)
    print(f"VectorStore: {vs.size} chunks, dim={vs.dim}\n")

    embedder = get_embedder()
    print("Gerando embeddings das queries...")
    q_texts = [q["query"] for q in queries]
    q_vecs = embedder.embed(q_texts)

    def run_eval(search_fn) -> List[Dict]:
        """Roda o protocolo de avaliacao para uma funcao de busca qualquer."""
        rows: List[Dict] = []
        for q, vec in zip(queries, q_vecs):
            results = search_fn(q["query"], vec)
            retrieved_sources = [r["source"] for r in results]
            relevant_set = set(q["relevant_sources"])
            # Recall conta arquivos distintos relevantes recuperados (hits unicos);
            # precision usa hits brutos (duplicata positiva conta).
            hits_unique = []
            seen = set()
            for src in retrieved_sources:
                is_hit = src in relevant_set and src not in seen
                hits_unique.append(is_hit)
                if is_hit:
                    seen.add(src)
            hits_bool = [src in relevant_set for src in retrieved_sources]

            n_rel = len(relevant_set)
            row = {
                "query": q["query"],
                "relevant_sources": list(relevant_set),
                "retrieved_top5": retrieved_sources,
                "scores_top5": [round(r["score"], 3) for r in results],
            }
            for k in K_VALUES:
                p = precision_at_k(hits_bool, k)
                r_ = recall_at_k(hits_unique, k, n_rel)
                row[f"P@{k}"] = p
                row[f"R@{k}"] = r_
                row[f"F1@{k}"] = f1(p, r_)
            row["RR"] = reciprocal_rank(hits_bool)
            rows.append(row)
        return rows

    def aggregate(rows: List[Dict]) -> Dict:
        agg: Dict = {"n_queries": len(rows)}
        for k in K_VALUES:
            agg[f"P@{k}"] = mean(r[f"P@{k}"] for r in rows)
            agg[f"R@{k}"] = mean(r[f"R@{k}"] for r in rows)
            agg[f"F1@{k}"] = mean(r[f"F1@{k}"] for r in rows)
        agg["MRR"] = mean(r["RR"] for r in rows)
        return agg

    def print_table(title: str, agg: Dict) -> None:
        print("=" * 70)
        print(f"{title}")
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

    print("Buscando top-5 para cada query e calculando metricas...\n")
    sem_rows = run_eval(lambda text, vec: vs.search(vec, top_k=5, min_score=0.0))
    sem_agg = aggregate(sem_rows)
    print_table("SEMANTICO PURO (cosseno de embeddings)", sem_agg)

    hyb_rows = run_eval(
        lambda text, vec: vs.search_hybrid(text, vec, top_k=5, min_score=0.0,
                                           alpha=HYBRID_ALPHA)
    )
    hyb_agg = aggregate(hyb_rows)
    print()
    print_table(f"HIBRIDO (alpha={HYBRID_ALPHA} — usado em producao)", hyb_agg)

    print(f"\nGanho do hibrido sobre o semantico puro: "
          f"P@1 {sem_agg['P@1']:.2f} -> {hyb_agg['P@1']:.2f} | "
          f"R@5 {sem_agg['R@5']:.2f} -> {hyb_agg['R@5']:.2f} | "
          f"MRR {sem_agg['MRR']:.2f} -> {hyb_agg['MRR']:.2f}")

    # Detalhamento das piores queries do hibrido (R@5 baixo)
    rows_sorted = sorted(hyb_rows, key=lambda r: r["R@5"])
    print("\nQueries com pior R@5 no hibrido (oportunidade de melhoria):\n")
    for r in rows_sorted[:5]:
        print(f"  - '{r['query']}'  R@5={r['R@5']:.2f}")
        print(f"      esperado: {r['relevant_sources']}")
        print(f"      veio:     {r['retrieved_top5']}\n")

    # Salva (chaves antigas continuam sendo o semantico, p/ compatibilidade)
    output = {
        "aggregate": sem_agg,
        "per_query": sem_rows,
        "hybrid": {"alpha": HYBRID_ALPHA, "aggregate": hyb_agg, "per_query": hyb_rows},
    }
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Metricas salvas em {METRICS_PATH}")


if __name__ == "__main__":
    evaluate()
