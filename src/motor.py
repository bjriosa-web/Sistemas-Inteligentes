"""Comparación tradicional y con embeddings de textos académicos."""
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .texto import texto_investigacion

SECCIONES = ("problema", "objetivos", "metodologia")

MODELO_PUBLICO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def similitud_lexica(consulta, textos):
    if not textos:
        return np.zeros(0, dtype=float)
    documentos = [consulta] + list(textos)
    if all(not d.strip() for d in documentos):
        return np.zeros(len(textos), dtype=float)
    try:
        tfidf = TfidfVectorizer(ngram_range=(1, 2), strip_accents="unicode",
                                lowercase=True, min_df=1, max_features=35000)
        matriz = tfidf.fit_transform(documentos)
        return cosine_similarity(matriz[0], matriz[1:]).ravel().clip(0, 1)
    except ValueError:
        return np.zeros(len(textos), dtype=float)


def cargar_modelo(ruta=None):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        raise RuntimeError("Falta sentence-transformers. Instala requirements_modelo.txt") from e
    return SentenceTransformer(ruta or MODELO_PUBLICO)


def similitud_semantica(consulta, textos, modelo):
    if not textos:
        return np.zeros(0, dtype=float)
    vectores = modelo.encode([consulta] + textos, normalize_embeddings=True,
                            convert_to_numpy=True, show_progress_bar=False, batch_size=16)
    return np.clip(np.asarray(vectores[1:]) @ np.asarray(vectores[0]), -1, 1)


def comparar(propuesta, catalogo, modo="tradicional", modelo=None, top_k=10):
    if catalogo.empty:
        raise ValueError("El catálogo no tiene investigaciones.")
    query = texto_investigacion(propuesta)
    if len(query.strip()) < 8:
        raise ValueError("Escribe un título o descripción de tu propuesta.")
    textos = [texto_investigacion(row) for row in catalogo.to_dict("records")]
    lexical = similitud_lexica(query, textos)
    if modo == "semantico":
        if modelo is None:
            raise ValueError("Se necesita cargar el modelo semántico.")
        semantic = similitud_semantica(query, textos, modelo)
        # Convierte coseno de [-1,1] a [0,1]; no es probabilidad.
        indices = ((semantic + 1) / 2).clip(0, 1)
    else:
        indices = lexical
    resultado = catalogo.copy()
    resultado["indice"] = np.round(indices * 100, 2)
    resultado["puntaje_tfidf"] = np.round(lexical * 100, 2)
    if modo == "semantico":
        resultado["coseno_semantico"] = np.round(semantic, 4)

    # Similitud por sección. Los campos vacíos no se comparan ni se puntúan.
    pesos = propuesta.get("pesos_seccion") or {"problema": 0.40, "objetivos": 0.35, "metodologia": 0.25}
    pesos = {s: max(0.0, float(pesos.get(s, 0))) for s in SECCIONES}
    scores = {}
    for seccion in SECCIONES:
        consulta_seccion = str(propuesta.get(seccion, "") or "").strip()
        textos_seccion = [str(row.get(seccion, "") or "").strip() for row in catalogo.to_dict("records")]
        if not consulta_seccion or not any(textos_seccion):
            scores[seccion] = np.full(len(catalogo), np.nan)
            continue
        if modo == "semantico":
            validos = [i for i, texto in enumerate(textos_seccion) if texto]
            vals = np.full(len(catalogo), np.nan)
            if validos:
                sims = similitud_semantica(consulta_seccion, [textos_seccion[i] for i in validos], modelo)
                vals[validos] = (sims + 1) / 2
            scores[seccion] = vals
        else:
            vals = np.full(len(catalogo), np.nan)
            validos = [i for i, texto in enumerate(textos_seccion) if texto]
            if validos:
                vals[validos] = similitud_lexica(consulta_seccion, [textos_seccion[i] for i in validos])
            scores[seccion] = vals
        resultado[f"similitud_{seccion}"] = np.round(scores[seccion] * 100, 2)

    disponibles = np.column_stack([scores[s] for s in SECCIONES])
    pesos_vector = np.array([pesos[s] for s in SECCIONES], dtype=float)
    ponderaciones = np.where(np.isfinite(disponibles), pesos_vector[None, :], 0.0)
    suma_pesos = ponderaciones.sum(axis=1)
    combinada = np.divide(np.nansum(disponibles * ponderaciones, axis=1), suma_pesos,
                          out=indices.copy(), where=suma_pesos > 0)
    resultado["indice"] = np.round(combinada * 100, 2)

    # Evidencia explicativa sencilla: términos de contenido compartidos entre
    # la sección consultada y cada antecedente; no sustituye revisión humana.
    import re
    stop = {"para", "como", "desde", "sobre", "entre", "hasta", "donde", "esta", "este", "estos", "estas", "una", "uno", "unos", "unas", "con", "por", "del", "las", "los", "que", "una", "mediante", "sobre", "the", "and", "with"}
    evidencia = []
    for row in catalogo.to_dict("records"):
        partes = []
        for sec in SECCIONES:
            qterms = set(re.findall(r"[a-záéíóúñ]{4,}", str(propuesta.get(sec, "") or "").lower())) - stop
            dtext = str(row.get(sec, "") or "")
            dterms = set(re.findall(r"[a-záéíóúñ]{4,}", dtext.lower())) - stop
            comunes = sorted(qterms & dterms)
            if comunes:
                partes.append(f"{sec}: " + ", ".join(comunes[:6]))
        evidencia.append("; ".join(partes) if partes else "Sin términos compartidos detectados en problema, objetivos o metodología.")
    resultado["evidencia_terminos"] = evidencia
    resultado = resultado.sort_values(by="indice", ascending=False).head(max(1, int(top_k)))
    return resultado.reset_index(drop=True)


def resumen_similitud_secciones(resultados):
    """Resume la similitud máxima observada por sección en los resultados.

    Describe únicamente los registros devueltos del catálogo consultado.
    """
    nombres = {"problema": "problema", "objetivos": "objetivos", "metodologia": "metodología"}
    salida = {}
    for key, label in nombres.items():
        col = f"similitud_{key}"
        valores = resultados[col].dropna() if col in resultados else []
        salida[label] = round(float(valores.max()), 1) if len(valores) else None
    presentes = [(k, v) for k, v in salida.items() if v is not None]
    if not presentes:
        diagnostico = "No hay datos suficientes por sección para resumir la similitud con antecedentes."
    else:
        mayor_sim = max(presentes, key=lambda x: x[1])[0]
        menor_sim = min(presentes, key=lambda x: x[1])[0]
        diagnostico = f"Mayor similitud observada en {mayor_sim}; menor similitud observada en {menor_sim}, dentro del catálogo cargado."
    return {"por_seccion": salida, "diagnostico": diagnostico}
