"""Ajusta un modelo multilingüe usando pares evaluados manualmente."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit


def ejecutar(ruta, salida, epocas=1):
    try:
        from sentence_transformers import SentenceTransformer, InputExample, losses
        from torch.utils.data import DataLoader
    except ImportError as e:
        raise RuntimeError("Instala pip install -r requirements_entrenamiento.txt") from e
    df = pd.read_csv(ruta).dropna(subset=["texto_a", "texto_b", "relevante"])
    requeridas = {"texto_a", "texto_b", "relevante", "grupo"}
    if not requeridas.issubset(df.columns):
        raise ValueError(f"El CSV debe tener estas columnas: {', '.join(sorted(requeridas))}")
    df["relevante"] = pd.to_numeric(df.relevante, errors="raise")
    if not df.relevante.between(0, 1).all():
        raise ValueError("Los valores 'relevante' deben estar entre 0 y 1")
    if len(df) < 12 or df.grupo.nunique() < 5:
        raise ValueError("Reúne al menos 12 pares y 5 grupos de propuestas distintos. Se recomiendan muchos más.")
    if df.relevante.nunique() < 2:
        raise ValueError("Se necesitan ejemplos relevantes (1) y no relevantes (0).")
    splitter = GroupShuffleSplit(n_splits=1, test_size=.25, random_state=42)
    train_idx, valid_idx = next(splitter.split(df, groups=df.grupo))
    train = df.iloc[train_idx].copy()
    val = df.iloc[valid_idx].copy()
    if train.relevante.nunique() < 2:
        raise ValueError("La división dejó entrenamiento sin ambas etiquetas; reúne más ejemplos.")
    print(f"Entrenamiento: {len(train)} pares; prueba separada: {len(val)} pares")
    # Conserva el conjunto de prueba, no se usa para entrenar.
    ruta_salida = Path(salida)
    ruta_salida.mkdir(parents=True, exist_ok=True)
    val.to_csv(ruta_salida / "pares_prueba_reservados.csv", index=False, encoding="utf-8-sig")
    (ruta_salida / "INFORMACION.txt").write_text(
        "Modelo ajustado con pares etiquetados por usuarios.\n"
        "No afirmar que los resultados son válidos sin evaluación separada.\n"
        f"Pares de entrenamiento: {len(train)}\nPares de prueba: {len(val)}\n", encoding="utf-8")
    muestras = [InputExample(texts=[str(r.texto_a), str(r.texto_b)], label=float(r.relevante))
                for r in train.itertuples(index=False)]
    modelo = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    loader = DataLoader(muestras, shuffle=True, batch_size=min(8, len(muestras)))
    modelo.fit(train_objectives=[(loader, losses.CosineSimilarityLoss(modelo))],
               epochs=max(1, int(epocas)), warmup_steps=0, output_path=str(ruta_salida), show_progress_bar=True)
    print("Pesos ajustados guardados en:", ruta_salida)
    print("Evalúa con scripts/evaluar_pares.py antes de concluir que mejoró.")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--datos", default="datos/pares_ejemplo_ficticios.csv")
    p.add_argument("--salida", default="modelos/tesis_radar_ajustado")
    p.add_argument("--epocas", type=int, default=1)
    args = p.parse_args()
    if Path(args.datos).name == "pares_ejemplo_ficticios.csv":
        print("ADVERTENCIA: estás entrenando con pares ficticios. Solo sirve para comprobar el procedimiento.")
    ejecutar(args.datos, args.salida, args.epocas)
