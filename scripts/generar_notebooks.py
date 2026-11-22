import json
from pathlib import Path
OUT = Path(__file__).resolve().parents[1] / 'notebooks'

def nb(cells):
    blocks=[]
    for typ,content in cells:
        item={'cell_type':typ,'metadata':{},'source':content.splitlines(keepends=True)}
        if typ=='code':item.update({'execution_count':None,'outputs':[]})
        blocks.append(item)
    return {'nbformat':4,'nbformat_minor':5,'metadata':{'colab':{'name':'TESIS-RADAR'},'kernelspec':{'name':'python3','display_name':'Python 3'},'language_info':{'name':'python'}},'cells':blocks}

demo=[
('markdown','# TESIS-RADAR: demostración en Colab\n\nEste cuaderno usa primero un buscador tradicional sin modelo grande. Los registros incluidos son ficticios. No presenta resultados científicos.'),
('code','from google.colab import files\nfrom pathlib import Path\narchivos = files.upload()\n'),
('markdown','Sube el ZIP del proyecto y después ejecuta las celdas en orden.'),
('code','import zipfile, glob, os\nzip_path = glob.glob("*.zip")[0]\nwith zipfile.ZipFile(zip_path) as z: z.extractall("/content/proyecto")\ncarpeta = "/content/proyecto/TESIS_RADAR"\n%cd {carpeta}\n'),
('code','!pip -q install -r requirements.txt'),
('code','!python scripts/comprobar.py'),
('code', 'from src.fuentes import leer_catalogo\nfrom src.motor import comparar\ncatalogo = leer_catalogo("datos/demo_ficticia.csv")\npropuesta = {"titulo": "Sistema para clasificar trámites universitarios", "problema": "Los trámites se revisan manualmente"}\nresultado = comparar(propuesta, catalogo, modo="tradicional", top_k=5)\ndisplay(resultado[["titulo","indice","fuente"]])'),
('markdown','## Comparación semántica opcional\n\nLa siguiente celda descarga el modelo base. Necesita Internet. Las puntuaciones ordenan antecedentes dentro del catálogo consultado.'),
('code','!pip -q install -r requirements_modelo.txt\nfrom src.motor import cargar_modelo\nmodelo = cargar_modelo()\nresultado = comparar(propuesta, catalogo, modo="semantico", modelo=modelo, top_k=5)\ndisplay(resultado[["titulo","indice","fuente"]])'),
('markdown','Para ejecutar la interfaz Streamlit completa es más cómodo usar Windows. En Colab este cuaderno enseña el motor de comparación. No hagas afirmaciones de exactitud sin pruebas con datos reales.')
]
train=[
('markdown','# TESIS-RADAR: entrenamiento y evaluación\n\nNecesitas un CSV de pares **reales revisados por personas** con columnas grupo,texto_a,texto_b,relevante. Los pares ficticios del paquete solo prueban el procedimiento. Utiliza GPU en Entorno de ejecución > Cambiar tipo de entorno de ejecución cuando esté disponible.'),
('code','from google.colab import files\nimport zipfile, glob\nfiles.upload()\nzip_path = glob.glob("*.zip")[0]\nwith zipfile.ZipFile(zip_path) as z: z.extractall("/content/proyecto")\n%cd /content/proyecto/TESIS_RADAR'),
('code','!pip -q install -r requirements_entrenamiento.txt'),
('markdown','Sube tu archivo CSV de pares. Si solo quieres ensayar el proceso, puedes saltarte esta celda y usar datos/pares_ejemplo_ficticios.csv (no válidos como evaluación científica).'),
('code','from google.colab import files\narchivos = files.upload()\nif archivos:\n    ruta_pares = list(archivos)[0]\nelse:\n    ruta_pares = "datos/pares_ejemplo_ficticios.csv"\nprint("Datos usados:", ruta_pares)'),
('code','!python scripts/entrenar.py --datos "$ruta_pares" --salida modelos/tesis_radar_ajustado --epocas 2'),
('markdown','Compara ambos modelos usando EXACTAMENTE el mismo conjunto de pares reservados. La métrica AP es la precisión promedio de clasificación de pares, no la exactitud del ranking completo.'),
('code','!python scripts/evaluar_pares.py --datos modelos/tesis_radar_ajustado/pares_prueba_reservados.csv --modelo sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'),
('code','!python scripts/evaluar_pares.py --datos modelos/tesis_radar_ajustado/pares_prueba_reservados.csv --modelo modelos/tesis_radar_ajustado'),
('markdown','## Descargar el modelo\n\nDescarga la carpeta del modelo para usarla en la aplicación. El modelo solo está entrenado por el grupo si ejecutaste estas celdas con datos propios.'),
('code','!zip -qr tesis_radar_modelo_ajustado.zip modelos/tesis_radar_ajustado\nfiles.download("tesis_radar_modelo_ajustado.zip")')
]
for name,data in [('00_DEMOSTRACION_COLAB.ipynb',demo),('01_ENTRENAMIENTO_COLAB.ipynb',train)]:
    (OUT/name).write_text(json.dumps(nb(data),ensure_ascii=False,indent=2),encoding='utf-8')
    print(name)
