"""
Treina o classificador de intencao do Academico.

Pipeline:
  TfidfVectorizer (1-2 ngrams, char_wb 3-5 opcional)
  + LogisticRegression (multinomial, lbfgs, balanceado)

Avaliacao:
  - 5-fold stratified cross-validation
  - F1-macro como metrica principal (multi-classe, classes desbalanceadas)
  - precision, recall por classe + matriz de confusao

Saidas:
  data/intent_classifier.joblib  -> pipeline treinado (sklearn)
  data/intent_metrics.json       -> relatorio das metricas (para incluir no PDF)

Como rodar:
    python -m scripts.train_intent_classifier
ou
    python scripts/train_intent_classifier.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import List, Tuple

# permite rodar com 'python scripts/train_intent_classifier.py' direto
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import (
    classification_report, confusion_matrix, f1_score, accuracy_score,
)

from core.intent_classifier import IntentClassifier, LABELS

DATA_PATH = BASE_DIR / "evaluation_data" / "intent_dataset.json"
MODEL_PATH = BASE_DIR / "data" / "intent_classifier.joblib"
METRICS_PATH = BASE_DIR / "data" / "intent_metrics.json"


def load_dataset() -> Tuple[List[str], List[str]]:
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    texts = [e["text"] for e in data["examples"]]
    labels = [e["label"] for e in data["examples"]]
    return texts, labels


def build_pipeline() -> Pipeline:
    """TF-IDF (palavra 1-2gram) + Logistic Regression multinomial."""
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95,
            sublinear_tf=True,
            lowercase=True,
            strip_accents="unicode",
        )),
        ("clf", LogisticRegression(
            C=4.0,
            max_iter=2000,
            class_weight="balanced",
            solver="lbfgs",
            random_state=42,
        )),
    ])


def main():
    print("=== Treino do classificador de intencao ===\n")
    print(f"Dataset:  {DATA_PATH.name}")
    texts, labels = load_dataset()
    n_total = len(texts)
    counts = {l: labels.count(l) for l in LABELS}
    print(f"Total:    {n_total} exemplos")
    print(f"Por classe: {counts}\n")

    pipeline = build_pipeline()

    print("Rodando 5-fold stratified cross-validation...")
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    y_pred = cross_val_predict(pipeline, texts, labels, cv=skf, n_jobs=1)

    acc = accuracy_score(labels, y_pred)
    f1_macro = f1_score(labels, y_pred, average="macro")
    f1_weighted = f1_score(labels, y_pred, average="weighted")

    print(f"\nAcuracia:    {acc:.4f}")
    print(f"F1-macro:    {f1_macro:.4f}")
    print(f"F1-weighted: {f1_weighted:.4f}\n")

    print("Relatorio por classe (cross-validation):\n")
    report_text = classification_report(
        labels, y_pred, labels=list(LABELS), digits=4
    )
    print(report_text)

    cm = confusion_matrix(labels, y_pred, labels=list(LABELS))
    print("\nMatriz de confusao (linhas = real, colunas = previsto):")
    print("        " + "  ".join(f"{l:>10}" for l in LABELS))
    for i, real in enumerate(LABELS):
        row = "  ".join(f"{int(v):>10d}" for v in cm[i])
        print(f"{real:>8}  {row}")

    # Treina pipeline final em TODO o dataset e salva
    print("\nTreinando modelo final em 100% do dataset e salvando...")
    pipeline.fit(texts, labels)
    classifier = IntentClassifier(pipeline)
    classifier.save(MODEL_PATH)
    print(f"Modelo salvo em {MODEL_PATH}")

    # Salva metricas para relatorio
    report_dict = classification_report(
        labels, y_pred, labels=list(LABELS), digits=4, output_dict=True
    )
    metrics = {
        "n_total": n_total,
        "counts_per_class": counts,
        "accuracy": acc,
        "f1_macro": f1_macro,
        "f1_weighted": f1_weighted,
        "per_class": {
            l: {
                "precision": report_dict[l]["precision"],
                "recall": report_dict[l]["recall"],
                "f1": report_dict[l]["f1-score"],
                "support": int(report_dict[l]["support"]),
            } for l in LABELS
        },
        "confusion_matrix": cm.tolist(),
        "labels": list(LABELS),
        "pipeline": "TfidfVectorizer(1,2) + LogisticRegression(C=4, balanced)",
        "cv": "StratifiedKFold(n_splits=5, shuffle=True, random_state=42)",
    }
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    print(f"Metricas salvas em {METRICS_PATH}")

    # Demonstracao com algumas predicoes
    print("\nDemonstracao (predicoes em queries fora do treino):")
    demo = [
        "qual a integral de x ao quadrado?",                # conteudo (talvez fora do dominio)
        "ja foi corrigida minha lista de pandas?",           # calendario
        "tenho prova de calculo essa semana, me ajuda",      # hibrido
        "como funciona o algoritmo k-vizinhos mais proximos?",  # conteudo
        "qual minha media na materia de logica?",            # calendario
    ]
    for q in demo:
        pred = classifier.predict(q)
        probs = classifier.predict_proba(q)
        top = " ".join(f"{l}={p:.2f}" for l, p in probs)
        print(f"  '{q}' -> {pred}  ({top})")


if __name__ == "__main__":
    main()
