import io
from pathlib import Path
import pandas as pd
import numpy as np
import pytest
from src.fuentes import leer_catalogo, preparar_catalogo, abstract_openalex
from src.texto import texto_investigacion, normalizar
from src.motor import comparar, similitud_lexica, similitud_semantica
from src.feedback import guardar_etiqueta
from src.evaluacion import metricas_ranking

RAIZ = Path(__file__).resolve().parents[1]


def test_catalogo_y_resultados():
    data = leer_catalogo(RAIZ / 'datos/demo_ficticia.csv')
    assert len(data) >= 30
    salida = comparar({'titulo': 'Clasificación automática de solicitudes universitarias'}, data)
    assert len(salida) == 10
    assert salida['indice'].between(0, 100).all()
    assert salida['indice'].iloc[0] >= salida['indice'].iloc[-1]


def test_no_confundir_puntuacion_plagio():
    arr = similitud_lexica('universidad estudiantes redes neuronales', ['universidad estudiantes redes neuronales', 'agua plantas bosque'])
    assert arr[0] > arr[1]


def test_csv_una_columna_obligatoria():
    with pytest.raises(ValueError):
        preparar_catalogo(pd.DataFrame({'autor':['X']}))


def test_csv_alias():
    data = preparar_catalogo(pd.DataFrame({'title':['Título de una investigación real'], 'abstract':['Texto'] }))
    assert data.iloc[0].titulo == 'Título de una investigación real'


def test_reconstruir_resumen():
    assert abstract_openalex({'tesis':[0], 'modelo':[1]}) == 'tesis modelo'


def test_datos_malformados():
    assert normalizar('Árbol, Educación!') == 'arbol educacion'
    assert 'TITULO:' in texto_investigacion({'titulo': 'Un título'})


def test_feedback(tmp_path):
    path = tmp_path / 'labels.csv'
    guardar_etiqueta(path, 'Q1', 'Propuesta', {'titulo':'Otro trabajo', 'id':'I1','fuente':'OpenAlex'}, True)
    df = pd.read_csv(path)
    assert len(df) == 1 and df.relevante.iloc[0] == 1


def test_evaluacion():
    result = metricas_ranking([[0, 1, 0, 1], [1, 0, 0, 0]], k=2)
    assert abs(result['recall_at_k'] - .75) < 1e-9
    assert result['consultas_evaluadas'] == 2


def test_semantico_con_modelo_simulado():
    class Modelo:
        def encode(self, docs, **kw):
            return np.array([[1, 0], [0.8, 0.6], [0, 1]])
    result = similitud_semantica('texto', ['uno','dos'], Modelo())
    assert result[0] > result[1]
