"""Lectura de CSV y consulta opcional de metadatos públicos."""
from pathlib import Path
import os
import re
import requests
import pandas as pd
from .texto import limpio

COLUMNAS = ["id", "titulo", "problema", "objetivos", "metodologia", "resumen", "autor", "anio", "fuente", "url",
            "institucion", "oai_endpoint", "oai_identifier", "fecha_obtencion", "formato_oai"]
ALIAS = {
    "title": "titulo", "nombre": "titulo", "name": "titulo", "abstract": "resumen",
    "description": "resumen", "descripcion": "resumen", "year": "anio",
    "publication_year": "anio", "author": "autor", "authors": "autor", "link": "url",
    "doi": "url", "source": "fuente", "objetivo": "objetivos", "methodology": "metodologia",
    "institution": "institucion", "repository": "institucion", "oai_id": "oai_identifier",
}


def preparar_catalogo(df):
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    df = df.rename(columns={k: v for k, v in ALIAS.items() if v not in df.columns})
    if "titulo" not in df.columns:
        raise ValueError("El catálogo necesita una columna 'titulo'.")
    for col in COLUMNAS:
        if col not in df.columns:
            df[col] = ""
    df = df[COLUMNAS]
    for col in COLUMNAS:
        df[col] = df[col].map(limpio)
    df = df[df.titulo.str.len() >= 8].copy()
    if df.empty:
        raise ValueError("No existen títulos utilizables en este CSV.")
    df = df.drop_duplicates(subset=["titulo", "url"], keep="first").reset_index(drop=True)
    df["id"] = [v if v else f"REG-{i+1:04d}" for i, v in enumerate(df.id)]
    return df


def leer_catalogo(archivo):
    try:
        df = pd.read_csv(archivo, encoding="utf-8-sig", dtype=str, sep=None, engine="python")
    except UnicodeDecodeError:
        df = pd.read_csv(archivo, encoding="latin1", dtype=str, sep=None, engine="python")
    return preparar_catalogo(df.fillna(""))


def abstract_openalex(indice):
    if not indice or not isinstance(indice, dict):
        return ""
    ultimo = max((max(v) for v in indice.values() if v), default=-1)
    if ultimo < 0 or ultimo > 10000:
        return ""
    palabras = [""] * (ultimo + 1)
    for palabra, posiciones in indice.items():
        for pos in posiciones:
            if isinstance(pos, int) and 0 <= pos < len(palabras):
                palabras[pos] = palabra
    return " ".join(palabras).strip()


def buscar_openalex(consulta, cantidad=40, api_key=None, tipo_tesis=False):
    """Consulta metadatos en OpenAlex, con conexión a Internet."""
    consulta = limpio(consulta)[:160]
    if len(consulta) < 3:
        raise ValueError("Escribe al menos tres letras para la búsqueda.")
    cantidad = max(1, min(int(cantidad), 100))
    params = {"search": consulta, "per-page": cantidad}
    if tipo_tesis:
        params["filter"] = "type:dissertation"
    key = api_key or os.environ.get("OPENALEX_API_KEY", "")
    if key:
        params["api_key"] = key
    try:
        res = requests.get("https://api.openalex.org/works", params=params, timeout=35,
                           headers={"User-Agent": "TesisRadarProyectoUniversitario/1.0"})
    except requests.RequestException as e:
        raise RuntimeError(f"No se pudo conectar con OpenAlex: {e}") from e
    if res.status_code in (401, 403, 429):
        raise RuntimeError("OpenAlex limitó la consulta o necesita clave API gratuita. Regístrate en openalex.org/settings/api e indica OPENALEX_API_KEY.")
    res.raise_for_status()
    rows = []
    for item in res.json().get("results", []):
        titulo = item.get("display_name") or item.get("title") or ""
        autores = ", ".join((a.get("author") or {}).get("display_name", "") for a in item.get("authorships", [])[:4])
        ident = item.get("id", "")
        url = item.get("doi") or (item.get("primary_location") or {}).get("landing_page_url") or ident
        rows.append({"id": ident.rsplit("/", 1)[-1], "titulo": titulo,
                     "resumen": abstract_openalex(item.get("abstract_inverted_index")),
                     "autor": autores, "anio": item.get("publication_year", ""),
                     "fuente": "OpenAlex", "url": url, "problema": "", "objetivos": "", "metodologia": ""})
    if not rows:
        raise ValueError("OpenAlex no devolvió investigaciones para esa consulta.")
    return preparar_catalogo(pd.DataFrame(rows))


def extraer_pdf(archivo, max_paginas=8):
    try:
        from pypdf import PdfReader
    except ImportError:
        raise RuntimeError("Instala pypdf para leer documentos PDF.")
    reader = PdfReader(archivo)
    textos = [(p.extract_text() or "") for p in reader.pages[:max_paginas]]
    contenido = "\n".join(textos)
    if len(contenido.strip()) < 80:
        raise ValueError("Este PDF no contiene texto reconocible. Si está escaneado, necesitarás OCR.")
    return contenido[:9500]
