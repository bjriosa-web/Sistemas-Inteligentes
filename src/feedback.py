"""Guarda la evaluación humana en un archivo local."""
import csv
from datetime import datetime, timezone
from pathlib import Path

COLUMNAS = ["fecha", "consulta_id", "titulo_propuesta", "titulo_documento", "id_documento", "relevante", "fuente"]


def guardar_etiqueta(ruta, consulta_id, titulo_propuesta, documento, relevante):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    crear = not ruta.exists()
    with ruta.open("a", newline="", encoding="utf-8-sig") as out:
        writer = csv.DictWriter(out, fieldnames=COLUMNAS)
        if crear:
            writer.writeheader()
        writer.writerow({"fecha": datetime.now(timezone.utc).isoformat(),
                         "consulta_id": consulta_id, "titulo_propuesta": titulo_propuesta,
                         "titulo_documento": documento.get("titulo", ""),
                         "id_documento": documento.get("id", ""),
                         "relevante": int(bool(relevante)), "fuente": documento.get("fuente", "")})
