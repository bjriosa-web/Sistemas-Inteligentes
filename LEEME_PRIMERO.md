# TESIS-RADAR

**Proyecto universitario: búsqueda y evaluación de antecedentes por sección mediante PLN y Deep Learning**

TESIS-RADAR analiza una idea o propuesta durante su planteamiento. Busca y ordena antecedentes dentro del catálogo cargado, según la similitud por sección; cada resultado requiere revisión humana.

## ¿Qué incluye?

- Aplicación web en Streamlit (`app.py`).
- Búsqueda tradicional TF-IDF para practicar sin descargar el modelo.
- Comparación semántica con Sentence-BERT multilingüe (descarga al primer uso).
- Importación de catálogos CSV con metadatos de tesis reales.
- Conexión opcional a OpenAlex para obtener registros públicos (puede requerir API key gratuita).
- Carga de una propuesta en PDF con texto seleccionable.
- Revisión manual de coincidencias y exportación a CSV.
- Resumen de similitud observada por problema, objetivos y metodología, con términos compartidos como evidencia orientativa.
- Scripts de ajuste del modelo y evaluación, más cuadernos de Colab.
- Datos de demostración **ficticios**, identificados como tales.
- Guía técnica ampliada y editable en Word: `documentacion/Guia_TESIS_RADAR.docx`.

> **Importante:** el archivo ZIP no incluye pesos entrenados por nuestro equipo. Utiliza un modelo multilingüe previamente publicado. Para documentar una versión ajustada por el grupo, se debe ejecutar `scripts/entrenar.py` con pares etiquetados y evaluar con datos reservados. La interfaz se comprobó en TF-IDF y Sentence-BERT real con el catálogo ficticio; esto confirma el flujo, no su rendimiento sobre tesis peruanas.

## Inicio rápido para Windows

1. Descomprime el ZIP en una carpeta sencilla, por ejemplo `C:\TESIS_RADAR`.
2. Instala Python 3.11 o 3.12 y activa **Add Python to PATH**.
3. Haz doble clic en **INICIAR_WINDOWS.bat** (requiere Internet para instalar bibliotecas).
4. Abre la dirección local que indique la consola (normalmente `http://localhost:8501`).
5. Deja seleccionados **Datos de demostración** y **Tradicional (TF-IDF)**.
6. Pulsa **Analizar similitudes** para ver el primer resultado.

## Activar la búsqueda con Deep Learning

1. Cierra la aplicación.
2. Ejecuta **ACTIVAR_MODELO_WINDOWS.bat** conectado a Internet.
3. Inicia de nuevo la aplicación.
4. En el panel izquierdo selecciona **Semántica (Sentence-BERT)**.
5. Presiona **Analizar similitudes**. La primera descarga puede ser grande.

Si la descarga falla, vuelve a la búsqueda tradicional. Esa versión también permite demostrar la interfaz.

## Agregar investigaciones reales

Puedes importar un CSV con la columna `titulo` y, opcionalmente, `resumen`, `autor`, `anio`, `url`, `fuente`, `problema`, `objetivos`, `metodologia`. Existe una plantilla en `datos/plantilla_importacion.csv`.

Para descargar registros de OpenAlex desde terminal (requiere Internet):

```powershell
python scripts/descargar_openalex.py --consulta "inteligencia artificial en universidades" --cantidad 50
```

La URL o clave se pueden configurar con la variable `OPENALEX_API_KEY` si el servicio solicita una clave:

```powershell
$env:OPENALEX_API_KEY="TU_CLAVE"
python scripts/descargar_openalex.py --consulta "aprendizaje automático educación" --cantidad 50
```

**ALICIA:** no se incluye un scraper ni una API directa no verificada. Se pueden consultar registros en https://alicia.concytec.gob.pe/ e incorporar sus metadatos al CSV respetando las reglas del repositorio. OpenAlex incluye obras académicas de muchos países; no equivale a tener exclusivamente tesis peruanas.

## Entrenar nuestra propia versión

1. Reúne pares de propuestas y antecedentes etiquetados por personas: **1** = relacionado, **0** = no relacionado.
2. Guarda `datos/mis_pares.csv` usando las columnas `grupo,texto_a,texto_b,relevante` (ver plantilla).
3. Instala `requirements_entrenamiento.txt`.
4. Ejecuta:

```powershell
python scripts/entrenar.py --datos datos/mis_pares.csv --salida modelos/tesis_radar_ajustado --epocas 2
```

5. Evalúa con los pares reservados que guarda el script:

```powershell
python scripts/evaluar_pares.py --datos modelos/tesis_radar_ajustado/pares_prueba_reservados.csv --modelo modelos/tesis_radar_ajustado
```

6. Repite la evaluación usando el modelo base y compara las métricas sin cambiar los datos de prueba:

```powershell
python scripts/evaluar_pares.py --datos modelos/tesis_radar_ajustado/pares_prueba_reservados.csv
```

7. En Streamlit coloca la ruta `modelos/tesis_radar_ajustado` en el campo **Modelo propio**.

El CSV `pares_ejemplo_ficticios.csv` permite ensayar el flujo, pero **no sirve como evidencia de rendimiento en investigaciones reales**. Para el informe científico hacen falta pares de tesis reales y etiquetas revisadas por el equipo/docente.

## Pruebas automáticas

```powershell
python -m pytest -q tests
python scripts/comprobar.py
```

## Estructura rápida

| Elemento | Función |
|---|---|
| `app.py` | Interfaz web y búsqueda |
| `src/fuentes.py` | Lectura de CSV, OpenAlex y PDF |
| `src/motor.py` | TF-IDF y Sentence-BERT |
| `src/feedback.py` | Guarda evaluaciones humanas |
| `scripts/entrenar.py` | Ajusta el modelo con etiquetas propias |
| `scripts/evaluar_pares.py` | Evalúa modelos con pares reservados |
| `scripts/descargar_openalex.py` | Descarga metadatos abiertos |
| `scripts/cosechar_oai.py` | Cosecha metadatos OAI-PMH con procedencia y checkpoint reanudable |
| `scripts/evaluar_ranking.py` | Compara TF-IDF, Sentence-BERT, híbrido y reranker con etiquetas humanas |
| `datos/demo_ficticia.csv` | Catálogo simulado para practicar |
| `notebooks/` | Guías ejecutables en Colab |
| `documentacion/` | Guía Word y protocolo experimental |

El uso de `scripts/cosechar_oai.py` requiere que el equipo confirme el endpoint y la política de reutilización del repositorio. La evaluación necesita juicios humanos y excluye documento fuente/duplicado exacto; ver `documentacion/PROTOCOLO_EVALUACION.md`.

## Alcance y precauciones

- El índice de similitud es una puntuación de ordenamiento y no una probabilidad.
- Un antecedente parecido no invalida una propuesta; puede demostrar que existe literatura relacionada.
- Los títulos y resúmenes tienen menos detalle que una tesis completa; las conclusiones son orientativas.
- La similitud observada depende de la cobertura y calidad del catálogo; los vacíos de cobertura no se infieren.
- Revisa permisos y licencias de cada fuente. No se descargan tesis protegidas automáticamente.
- Evita subir documentos privados o datos personales de compañeros sin permiso.
- No cargues secretos API dentro del código ni los compartas en el ZIP.
- Si un documento es un PDF escaneado, hará falta OCR; el proyecto no lo incluye.

Fuentes técnicas: https://help.openalex.org/api/ , https://www.sbert.net/ , https://alicia.concytec.gob.pe/.
