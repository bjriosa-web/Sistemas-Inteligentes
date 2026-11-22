"""Métricas de ranking para pares revisados por personas."""
import numpy as np


def metricas_ranking(relevancias, k=5):
    """Lista de listas binarias ordenadas por similitud para cada consulta."""
    k = max(1, int(k))
    recalls, precisiones, mrr = [], [], []
    for etiquetas in relevancias:
        etiquetas = [int(v) for v in etiquetas]
        n_positivos = sum(etiquetas)
        if n_positivos == 0:
            continue
        primeros = etiquetas[:k]
        recalls.append(sum(primeros) / n_positivos)
        precisiones.append(sum(primeros) / k)
        pos_primero = next((i + 1 for i, v in enumerate(primeros) if v), None)
        mrr.append(1 / pos_primero if pos_primero else 0.0)
    if not recalls:
        return {"consultas_evaluadas": 0, "recall_at_k": None, "precision_at_k": None, "mrr_at_k": None}
    return {"consultas_evaluadas": len(recalls), "recall_at_k": float(np.mean(recalls)),
            "precision_at_k": float(np.mean(precisiones)), "mrr_at_k": float(np.mean(mrr))}
