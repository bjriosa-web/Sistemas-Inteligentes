"""Descarga resultados públicos de OpenAlex y crea un catálogo CSV."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.fuentes import buscar_openalex


def main():
    p = argparse.ArgumentParser(description="Obtener metadatos públicos de OpenAlex")
    p.add_argument("--consulta", required=True, help="Tema que buscarás")
    p.add_argument("--cantidad", type=int, default=50)
    p.add_argument("--solo-tesis", action="store_true")
    p.add_argument("--salida", default="datos/catalogo_openalex.csv")
    args = p.parse_args()
    df = buscar_openalex(args.consulta, args.cantidad, tipo_tesis=args.solo_tesis)
    ruta = Path(args.salida)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta, index=False, encoding="utf-8-sig")
    print(f"Guardados {len(df)} registros en {ruta}")
    print("Revisa los títulos y enlaces antes de presentarlos como antecedentes.")

if __name__ == "__main__":
    main()
