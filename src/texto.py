"""Funciones simples para preparar textos y registros académicos."""
import re
import unicodedata

CAMPOS = ["titulo", "problema", "objetivos", "metodologia", "resumen"]


def limpio(valor):
    if valor is None:
        return ""
    s = str(valor)
    if s.lower() in {"nan", "none", "null"}:
        return ""
    return re.sub(r"\s+", " ", s).strip()


def normalizar(valor):
    s = unicodedata.normalize("NFKD", limpio(valor).lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9ñ ]+", " ", s)).strip()


def texto_investigacion(row):
    partes = []
    for campo in CAMPOS:
        valor = limpio(row.get(campo, ""))
        if valor:
            partes.append(f"{campo.upper()}: {valor[:3500]}")
    return "\n".join(partes)[:9000]


def contar_palabras(texto):
    return len(re.findall(r"\w+", limpio(texto)))
