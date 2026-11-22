"""Prueba rápida sin Internet ni modelos grandes."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.fuentes import leer_catalogo
from src.motor import comparar

catalogo = leer_catalogo(Path(__file__).resolve().parents[1] / "datos/demo_ficticia.csv")
propuesta = {"titulo": "Clasificación de trámites universitarios con redes neuronales",
             "problema": "Clasificar solicitudes de estudiantes para mejorar la atención"}
r = comparar(propuesta, catalogo, top_k=5)
assert not r.empty
assert r.indice.between(0, 100).all()
assert r.indice.iloc[0] >= r.indice.iloc[-1]
print("Prueba básica correcta. Catálogo:", len(catalogo), "Primera coincidencia:", r.titulo.iloc[0])
print("Este control no ejecuta Sentence-BERT ni consulta OpenAlex.")
