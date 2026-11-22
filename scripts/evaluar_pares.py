"""Compara TF-IDF y embeddings con pares reservados."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score
from src.motor import similitud_lexica, similitud_semantica, cargar_modelo


def evaluar(y, scores):
    y = np.asarray(y).astype(int)
    if len(set(y)) != 2:
        return {"AP": None, "ROC_AUC": None}
    return {"AP": round(float(average_precision_score(y, scores)), 4),
            "ROC_AUC": round(float(roc_auc_score(y, scores)), 4)}

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--datos", required=True)
    p.add_argument("--modelo", default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    args = p.parse_args()
    df = pd.read_csv(args.datos).dropna(subset=["texto_a", "texto_b", "relevante"])
    if df.empty:
        raise ValueError("Archivo sin pares etiquetados")
    left, right = df.texto_a.astype(str).tolist(), df.texto_b.astype(str).tolist()
    y = df.relevante.astype(int).tolist()
    base = [similitud_lexica(a, [b])[0] for a, b in zip(left, right)]
    # El TF-IDF para evaluar pares debe entrenarse en un vocabulario compartido.
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import paired_cosine_distances
    vec = TfidfVectorizer(ngram_range=(1, 2), strip_accents="unicode")
    mat = vec.fit_transform(left + right)
    baseline = 1 - paired_cosine_distances(mat[:len(left)], mat[len(left):])
    print("TF-IDF:", evaluar(y, baseline))
    modelo = cargar_modelo(args.modelo)
    a = modelo.encode(left, convert_to_numpy=True, normalize_embeddings=True)
    b = modelo.encode(right, convert_to_numpy=True, normalize_embeddings=True)
    semantica = np.sum(a * b, axis=1)
    print("Sentence-BERT:", evaluar(y, semantica))
    print("Estas métricas de pares no reemplazan la evaluación del ranking Recall@5 o MRR@5.")
