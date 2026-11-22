"""TESIS-RADAR. Ejecutar con: streamlit run app.py"""
import io
import os
from pathlib import Path
import uuid
import pandas as pd
import streamlit as st

from src.fuentes import leer_catalogo, buscar_openalex, extraer_pdf
from src.motor import comparar, cargar_modelo, MODELO_PUBLICO, resumen_similitud_secciones
from src.feedback import guardar_etiqueta

RAIZ = Path(__file__).resolve().parent
st.set_page_config(page_title="TESIS-RADAR | Explorador académico", page_icon="📚", layout="wide")
st.markdown("""
<style>
.block-container{max-width:1230px;padding-top:2rem}
.hero{padding:23px 28px;background:#0e283a;border-radius:18px;color:#fff;margin-bottom:16px}
.hero h1{margin:0;color:#fff;font-size:2.35rem;letter-spacing:-.04em}
.hero p{color:#cde0e4;margin:8px 0 0}
.eyebrow{font-size:12px;color:#84ded7;letter-spacing:2px;font-weight:750}
.note{padding:12px 15px;border-radius:10px;background:#e9f4f2;color:#16343e;border-left:4px solid #189e95;margin:8px 0 17px}
.result{border:1px solid #d9e5e5;border-radius:13px;padding:14px 18px;margin-bottom:12px}
.score{font-weight:750;color:#128d86}
.small{color:#536774;font-size:13px}
</style>""", unsafe_allow_html=True)
st.markdown('<div class="hero"><div class="eyebrow">PROYECTO DE INGENIERÍA DE SISTEMAS</div><h1>TESIS-RADAR</h1><p>Explorador de similitud entre investigaciones académicas</p></div>', unsafe_allow_html=True)
st.markdown('<div class="note">TESIS-RADAR busca y ordena antecedentes según la similitud observada por sección. Revise cada registro y su fuente antes de usarlo.</div>', unsafe_allow_html=True)

@st.cache_resource(show_spinner="Cargando el modelo multilingüe...")
def get_modelo(path):
    return cargar_modelo(path or None)

with st.sidebar:
    st.header("1. Catálogo")
    fuente = st.radio("Origen de los registros", ["Datos de demostración", "Importar CSV", "Consultar OpenAlex"], label_visibility="visible")
    st.caption("ALICIA no se consulta automáticamente. Puedes incorporar registros exportados en CSV desde repositorios autorizados.")
    registro = None
    if fuente == "Datos de demostración":
        registro = leer_catalogo(RAIZ / "datos" / "demo_ficticia.csv")
        st.info("Ejemplos inventados para practicar. No representan tesis reales.")
    elif fuente == "Importar CSV":
        archivo = st.file_uploader("Archivo CSV", type=["csv"], key="catalogo")
        if archivo:
            try:
                registro = leer_catalogo(archivo)
            except Exception as exc:
                st.error(f"No se pudo leer el catálogo: {exc}")
        st.caption("Campo obligatorio: titulo. Opcionales: resumen, autor, anio, url, problema, objetivos, metodologia, fuente.")
    else:
        consulta = st.text_input("Buscar registros por tema", value="inteligencia artificial educación Perú")
        cantidad = st.number_input("Cantidad máxima", min_value=10, max_value=100, value=40, step=10)
        tesis = st.checkbox("Solo tipo tesis (menos cobertura)", value=False)
        if st.button("Buscar en OpenAlex", type="primary"):
            try:
                st.session_state["openalex"] = buscar_openalex(consulta, cantidad, tipo_tesis=tesis)
            except Exception as exc:
                st.error(str(exc))
        registro = st.session_state.get("openalex")
        st.caption("Puede requerir una clave gratuita de OpenAlex y conexión a Internet.")

    st.divider()
    st.header("2. Motor de análisis")
    elegir = st.radio("Comparación", ["Tradicional (TF-IDF)", "Semántica (Sentence-BERT)"], index=0)
    modelo_path = st.text_input("Modelo propio (opcional)", value="", placeholder="modelos/mi_modelo")
    top_k = st.slider("Resultados a mostrar", 3, 25, 8)
    st.caption("Peso para ordenar antecedentes por sección")
    pesos_seccion = {
        "problema": st.slider("Problema", 0, 100, 40, 5),
        "objetivos": st.slider("Objetivos", 0, 100, 35, 5),
        "metodologia": st.slider("Metodología", 0, 100, 25, 5),
    }
    st.divider()
    st.caption("Versión académica · Datos locales por defecto · Apoyo para búsqueda de antecedentes")

st.subheader("Escribe una propuesta de investigación")
with st.form("propuesta"):
    nombre = st.text_input("Título de la propuesta", value="Sistema de clasificación automática de solicitudes académicas")
    problema = st.text_area("Problema de investigación", height=88,
        value="Las solicitudes de estudiantes se revisan manualmente y pueden demorar en ser derivadas al área adecuada.")
    objetivos = st.text_area("Objetivo principal", height=73,
        value="Desarrollar un modelo de lenguaje para clasificar solicitudes académicas y ayudar a su derivación.")
    metodologia = st.text_area("Metodología propuesta", height=73,
        value="Usar embeddings multilingües, comparar con TF-IDF y evaluar con ejemplos etiquetados.")
    subir = st.file_uploader("O sube una propuesta en PDF con texto seleccionable (opcional)", type=["pdf"])
    enviar = st.form_submit_button("Analizar similitudes", type="primary", use_container_width=True)

if enviar:
    if registro is None or registro.empty:
        st.error("Primero carga registros académicos en el panel izquierdo.")
    else:
        texto_pdf = ""
        if subir is not None:
            try:
                texto_pdf = extraer_pdf(io.BytesIO(subir.getvalue()))
                st.info("Se extrajo texto del PDF. Se tendrá en cuenta junto con los campos escritos.")
            except Exception as exc:
                st.warning(f"El PDF no se pudo procesar: {exc}")
        propuesta = {"titulo": nombre, "problema": problema, "objetivos": objetivos,
                     "metodologia": metodologia, "resumen": texto_pdf[:5000],
                     "pesos_seccion": pesos_seccion}
        modo = "tradicional" if elegir.startswith("Tradicional") else "semantico"
        try:
            modelo = get_modelo(modelo_path) if modo == "semantico" else None
            resultado = comparar(propuesta, registro, modo=modo, modelo=modelo, top_k=top_k)
            st.session_state["resultados"] = resultado
            st.session_state["titulo_analizado"] = nombre
            st.session_state["motor_usado"] = modo
            st.session_state["consulta_id"] = str(uuid.uuid4())[:8]
        except Exception as exc:
            st.error(f"No fue posible analizar: {exc}")
            if modo == "semantico":
                st.info("Para trabajar sin conexión, selecciona 'Tradicional (TF-IDF)'.")

resultados = st.session_state.get("resultados")
if resultados is not None:
    st.divider()
    st.subheader("Investigaciones relacionadas")
    informe = resumen_similitud_secciones(resultados)
    st.markdown("### Similitud observada por sección")
    st.caption("Muestra la mayor similitud observada entre los resultados y el catálogo cargado; depende de la cobertura y calidad del catálogo.")
    m1, m2, m3 = st.columns(3)
    for col, key in zip((m1, m2, m3), ("problema", "objetivos", "metodología")):
        valor = informe["por_seccion"][key]
        col.metric(f"Similitud: {key}", f"{valor:.1f}/100" if valor is not None else "Sin datos")
    st.info(informe["diagnostico"])
    a, b, c = st.columns(3)
    a.metric("Registros comparados", len(registro) if registro is not None else "—")
    b.metric("Resultados mostrados", len(resultados))
    c.metric("Motor utilizado", "Semántico" if st.session_state.get("motor_usado") == "semantico" else "TF-IDF")
    st.caption("El índice va de 0 a 100 y es una transformación matemática de la similitud para ordenar antecedentes; no es una probabilidad.")
    csv = resultados.to_csv(index=False).encode("utf-8-sig")
    st.download_button("Exportar resultados CSV", csv, file_name="tesis_radar_resultados.csv", mime="text/csv")
    for i, fila in resultados.iterrows():
        with st.container(border=True):
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"**{i+1}. {fila['titulo']}**")
                st.caption(f"{fila['autor'] or 'Autor no informado'} · {fila['anio'] or 'Año no informado'} · {fila['fuente'] or 'Fuente no informada'}")
                detalle = fila["resumen"] or fila["problema"] or "Este registro no trae resumen. La comparación puede basarse solo en el título."
                st.write((detalle[:360] + "…") if len(detalle) > 360 else detalle)
                st.caption(f"Evidencia textual: {fila.get('evidencia_terminos', 'No disponible')}")
                secciones = [f"{nombre}: {fila.get('similitud_' + campo):.1f}%" for nombre, campo in (("Problema", "problema"), ("Objetivos", "objetivos"), ("Metodología", "metodologia")) if pd.notna(fila.get('similitud_' + campo, float('nan')))]
                if secciones:
                    st.caption("Similitud por sección · " + " · ".join(secciones))
                url = str(fila.get("url", ""))
                if url.startswith("https://") or url.startswith("http://"):
                    st.link_button("Consultar fuente", url)
            with col2:
                st.metric("Índice", f"{fila['indice']:.1f} / 100")
                st.caption(f"TF-IDF: {fila['puntaje_tfidf']:.1f}")
                colsi, colno = st.columns(2)
                if colsi.button("Sí", key=f"si_{st.session_state['consulta_id']}_{i}", help="Es un antecedente relevante"):
                    guardar_etiqueta(RAIZ / "datos" / "etiquetas_usuario.csv", st.session_state["consulta_id"],
                                    st.session_state["titulo_analizado"], fila.to_dict(), True)
                    st.toast("Revisión guardada")
                if colno.button("No", key=f"no_{st.session_state['consulta_id']}_{i}", help="No es un antecedente relevante"):
                    guardar_etiqueta(RAIZ / "datos" / "etiquetas_usuario.csv", st.session_state["consulta_id"],
                                    st.session_state["titulo_analizado"], fila.to_dict(), False)
                    st.toast("Revisión guardada")
    st.info("Los botones Sí/No guardan etiquetas para una evaluación posterior. El archivo se crea localmente en datos/etiquetas_usuario.csv.")
else:
    st.markdown("**Para comenzar:** usa el catálogo de demostración, escribe tu propuesta y presiona *Analizar similitudes*. Luego cambia al modelo semántico cuando lo hayas descargado.")
