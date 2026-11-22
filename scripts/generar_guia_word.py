"""Construye la guía técnica Word de TESIS-RADAR con extractos del código."""
from pathlib import Path
from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "documentacion" / "Guia_TESIS_RADAR.docx"
NAVY = "17324D"
PALE = "F1F4F6"
GRID = "D5DADF"
BLACK = RGBColor(0, 0, 0)

doc = Document()
sec = doc.sections[0]
sec.top_margin = Inches(.72)
sec.bottom_margin = Inches(.72)
sec.left_margin = Inches(.82)
sec.right_margin = Inches(.82)
sec.header_distance = Inches(.35)
sec.footer_distance = Inches(.35)

styles = doc.styles
normal = styles["Normal"]
normal.font.name = "Aptos"
normal.font.size = Pt(10.5)
normal.font.color.rgb = BLACK
normal.paragraph_format.space_after = Pt(6)
normal.paragraph_format.line_spacing = 1.12
for name, size in (("Title", 28), ("Heading 1", 17), ("Heading 2", 13), ("Heading 3", 11)):
    st = styles[name]
    st.font.name = "Aptos Display" if name != "Heading 3" else "Aptos"
    st.font.size = Pt(size)
    st.font.bold = True
    st.font.color.rgb = BLACK
    st.paragraph_format.keep_with_next = True
    st.paragraph_format.space_before = Pt(12 if name != "Title" else 0)
    st.paragraph_format.space_after = Pt(6)


def shade(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def borders(table, color=GRID, size="5"):
    tbl_pr = table._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), size)
        el.set(qn("w:color"), color)
        b.append(el)
    tbl_pr.append(b)


def set_cell_margins(cell, top=90, start=110, bottom=90, end=110):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    mar = OxmlElement("w:tcMar")
    for m, v in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        el = OxmlElement(f"w:{m}")
        el.set(qn("w:w"), str(v))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tc_pr.append(mar)


def para(text="", style=None, bold_lead=None, keep=False):
    p = doc.add_paragraph(style=style)
    if bold_lead and text.startswith(bold_lead):
        p.add_run(bold_lead).bold = True
        p.add_run(text[len(bold_lead):])
    else:
        p.add_run(text)
    if keep:
        p.paragraph_format.keep_with_next = True
    return p


def heading(text, level=1):
    return doc.add_heading(text, level=level)


def bullet(text, level=0):
    return para(text, "List Bullet" if level == 0 else "List Bullet 2")


def numbered(text):
    return para(text, "List Number")


def code(text, caption=None):
    if caption:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(caption)
        r.bold = True
        r.font.size = Pt(9)
    for line in text.strip("\n").splitlines():
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(.18)
        p.paragraph_format.right_indent = Inches(.08)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        pPr = p._p.get_or_add_pPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:fill"), PALE)
        pPr.append(shd)
        r = p.add_run(line if line else " ")
        r.font.name = "Cascadia Mono"
        r._element.rPr.rFonts.set(qn("w:ascii"), "Cascadia Mono")
        r._element.rPr.rFonts.set(qn("w:hAnsi"), "Cascadia Mono")
        r.font.size = Pt(8.2)
        r.font.color.rgb = RGBColor(30, 42, 54)
    para("")


def table(headers, rows, widths=None, font=9):
    t = doc.add_table(rows=1, cols=len(headers))
    t.autofit = False
    if widths:
        for c, w in zip(t.columns, widths):
            c.width = Inches(w)
    for i, label in enumerate(headers):
        cell = t.rows[0].cells[i]
        cell.text = label
        shade(cell, NAVY)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        set_cell_margins(cell)
        for run in cell.paragraphs[0].runs:
            run.bold = True
            run.font.color.rgb = RGBColor(255, 255, 255)
            run.font.size = Pt(font)
    for ridx, row in enumerate(rows):
        cells = t.add_row().cells
        for i, value in enumerate(row):
            cells[i].text = str(value)
            cells[i].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cells[i])
            if ridx % 2 == 1:
                shade(cells[i], "F6F8F9")
            for p in cells[i].paragraphs:
                p.paragraph_format.space_after = Pt(1)
                p.paragraph_format.line_spacing = 1.03
                for run in p.runs:
                    run.font.size = Pt(font)
                    run.font.color.rgb = BLACK
    borders(t)
    para("")
    return t


def field(run, instruction):
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for el in (begin, instr, separate, text, end):
        run._r.append(el)


# Running header and page numbering.
hp = sec.header.paragraphs[0]
hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
r = hp.add_run("TESIS-RADAR  |  GUÍA TÉCNICA")
r.font.size = Pt(8)
r.font.color.rgb = RGBColor(70, 70, 70)
fp = sec.footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
fp.add_run("Guía editable para revisión académica  ·  ").font.size = Pt(8)
field(fp.add_run(), "PAGE")


# Cover
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(86)
p.paragraph_format.space_after = Pt(10)
p.style = styles["Title"]
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run("Guía técnica de TESIS RADAR")
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(22)
r = p.add_run("Buscador de antecedentes por sección")
r.font.name = "Aptos Display"
r.font.size = Pt(16)
r.font.color.rgb = BLACK
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run("Funcionamiento, código y metodología de evaluación").font.size = Pt(12)
para("")
table(["Dato", "Descripción"], [
    ("Proyecto", "TESIS-RADAR"),
    ("Propósito", "Ayudar a localizar y ordenar antecedentes durante el planteamiento de una investigación."),
    ("Versión", "Guía ampliada en formato Word, editable."),
    ("Fecha", "21 de noviembre de 2026"),
    ("Estado del estudio", "Prototipo comprobado con catálogo ficticio; evaluación científica pendiente de datos reales y juicios humanos."),
], [1.45, 5.65])
para("El sistema compara secciones de una propuesta con registros de un catálogo y devuelve un orden de consulta. La interfaz y el modelo semántico se comprobaron con datos ficticios. El endpoint institucional, la anotación independiente y las métricas sobre tesis peruanas siguen pendientes.")
doc.add_page_break()


# Reader orientation and contents
heading("Resumen", 1)
para("TESIS-RADAR busca apoyar a estudiantes y asesores durante el planteamiento de una investigación mediante la recuperación de antecedentes comparables por problema, objetivos y metodología. El prototipo combina un buscador léxico TF-IDF con embeddings Sentence-BERT, permite ajustar pesos por sección y presenta registros ordenados, puntuaciones y términos compartidos. Hay interfaz web. En la comprobación funcional, los modos TF-IDF y semántico completaron una búsqueda con el catálogo ficticio; esto confirma el flujo de la aplicación, pero no constituye una medición del desempeño científico. La evaluación prevista compara TF-IDF, Sentence-BERT, el método híbrido y un reranker con consultas originales y parafraseadas. Aún faltan el catálogo peruano autorizado y los juicios independientes de evaluadores, así que las métricas permanecen pendientes. La cobertura dependerá de la fuente y calidad de metadatos. El modelo semántico limita cada entrada a 128 tokens y puede truncar resúmenes extensos. La puntuación sirve para ordenar antecedentes y requiere revisión humana.")
heading("En pocas palabras", 2)
para("La aplicación se probó con un modelo real y datos inventados; la comparación científica sobre tesis peruanas empezará después de confirmar la fuente y reunir las etiquetas humanas.")
doc.add_page_break()

heading("Cómo usar esta guía", 1)
para("Este documento explica el alcance de TESIS-RADAR, el flujo de la aplicación y la función de los módulos del código. Está dirigido al equipo y al profesor revisor. Puede leerse de principio a fin o consultarse por archivo cuando se necesite explicar una parte del proyecto.")
para("La primera parte describe qué hace el buscador y qué datos utiliza. Después se explican los métodos de comparación y los principales archivos de Python con fragmentos representativos. La sección experimental detalla cómo se reúnen consultas, candidatos y juicios humanos antes de calcular métricas.")
para("La conclusión actual es acotada: el prototipo completa la búsqueda de demostración en los modos TF-IDF y Sentence-BERT real. Ese recorrido confirma que la interfaz y el motor funcionan en la configuración comprobada. No permite concluir cuál método recupera mejor antecedentes, porque faltan registros reales del repositorio seleccionado y evaluaciones humanas.")
heading("Contenido", 1)
for item in [
    "1. Alcance del proyecto y relación con otras herramientas",
    "2. Recorrido completo del sistema",
    "3. Datos de entrada y procedencia",
    "4. Métodos de comparación y puntuación",
    "5. Explicación detallada del código de la aplicación",
    "6. Cosecha de metadatos OAI-PMH",
    "7. Protocolo de evaluación del ranking",
    "8. Explicación del evaluador y ajuste opcional de Sentence-BERT",
    "9. Limitaciones y uso responsable",
    "10. Estado de resultados",
    "11. Plan operativo para completar el estudio",
    "Anexos A–C. Solicitud institucional, formato de juicios y comprobación funcional",
    "Referencias",
]:
    bullet(item)


heading("1. Alcance del proyecto y relación con otras herramientas", 1)
heading("1.1 Problema que aborda", 2)
para("Durante el planteamiento de una investigación, estudiantes y asesores necesitan encontrar trabajos relacionados con el problema, los objetivos o la metodología propuesta. Los catálogos institucionales pueden diferir en vocabulario, campos disponibles y calidad de resúmenes. TESIS-RADAR permite cargar registros y ordenar los que presentan mayor similitud textual con cada sección.")
para("La salida es una lista para consulta y revisión. La cobertura queda limitada al contenido del catálogo cargado y a los metadatos de cada registro. Una ausencia en la lista no establece que no existan antecedentes fuera de esa fuente.")
heading("1.2 Comparación de alcance con Turnitin Similarity", 2)
para("La documentación de Turnitin describe un reporte que ayuda a revisar coincidencias de una entrega con materiales de sus colecciones. TESIS-RADAR se usa antes, durante el planteamiento: busca antecedentes por sección dentro de un catálogo proporcionado por el equipo. La siguiente tabla compara el momento de uso y la información de salida; no compara rendimientos ni equipara puntuaciones.")
table(["Criterio", "Turnitin Similarity", "TESIS-RADAR"], [
    ("Momento de uso", "Al revisar una entrega escrita.", "Al plantear una investigación y buscar antecedentes."),
    ("Pregunta práctica", "¿Qué partes de la entrega coinciden con fuentes de su colección?", "¿Qué registros del catálogo se relacionan con el problema, los objetivos o la metodología?"),
    ("Entrada", "Un documento enviado al servicio.", "Campos de una propuesta y un catálogo de metadatos."),
    ("Comparación", "Texto de la entrega frente a fuentes indexadas por el servicio.", "Secciones de la propuesta frente a campos de registros cargados."),
    ("Salida", "Reporte de coincidencias y puntuación de similitud.", "Ranking, similitud por sección y términos compartidos."),
    ("Fuente", "Colecciones del servicio y contenidos incorporados por instituciones.", "CSV local, OpenAlex opcional u OAI-PMH institucional cuando se confirme endpoint y política."),
], [1.25, 2.85, 3.0], font=8.7)

heading("1.3 Objetivos del prototipo", 2)
para("Objetivo general: implementar y evaluar experimentalmente un buscador de antecedentes por sección que compare propuestas de investigación con registros peruanos autorizados.", bold_lead="Objetivo general:")
for x in [
    "Importar o cosechar registros trazables con título, resumen, año, enlace e institución.",
    "Construir consultas originales y parafraseadas, y reunir juicios binarios de relevancia sin que los evaluadores vean puntuaciones o etiquetas ajenas.",
    "Comparar cuatro configuraciones: TF-IDF, Sentence-BERT, combinación híbrida y reranking con CrossEncoder.",
    "Presentar los resultados por sección en una interfaz que permita consultar las fuentes y exportar el ranking.",
]: bullet(x)
heading("1.4 Pregunta e hipótesis", 2)
para("Pregunta de investigación: ¿Un enfoque híbrido (TF-IDF + Sentence-BERT) que compara por secciones recupera antecedentes relevantes en tesis peruanas mejor que cada método por separado, incluso con propuestas parafraseadas?")
para("Hipótesis de trabajo: sobre consultas de prueba separadas, el enfoque híbrido obtendrá una mejora en alguna de las métricas de recuperación frente a por lo menos uno de los métodos individuales. Esta hipótesis permanece sin evaluar hasta ejecutar el protocolo completo. Si el híbrido no supera a los métodos individuales, ese resultado también debe reportarse.")


heading("2. Recorrido completo del sistema", 1)
para("El flujo empieza cuando el usuario ingresa el título y el texto disponible para problema, objetivos y metodología. El catálogo procede de la demostración ficticia, un CSV, una consulta opcional a OpenAlex o una futura cosecha institucional. El motor compara cada campo, calcula la puntuación de ordenamiento y devuelve los primeros resultados.")
table(["Etapa", "Qué ocurre", "Dato que pasa a la siguiente etapa"], [
    ("1. Consulta", "El formulario recoge los campos escritos y el método elegido.", "Propuesta con secciones y pesos."),
    ("2. Catálogo", "Se leen y normalizan los registros, o se consulta OpenAlex.", "Tabla con título, resumen y procedencia."),
    ("3. Comparación", "El motor calcula TF-IDF o embeddings por consulta y candidato.", "Puntuaciones por sección."),
    ("4. Ordenamiento", "Se ponderan las secciones disponibles y se ordenan registros.", "Ranking de longitud solicitada."),
    ("5. Presentación", "Se muestran el resumen, la evidencia léxica y los enlaces.", "Vista para inspección humana y exportación CSV."),
    ("6. Revisión", "Opcionalmente, el usuario registra Sí/No para cada candidato.", "Archivo local de etiquetas de interfaz."),
], [1.2, 3.3, 2.6])
heading("2.1 Componentes", 2)
table(["Componente", "Responsabilidad", "Entrada principal", "Salida principal"], [
    ("app.py", "Interfaz Streamlit y flujo de consulta.", "Propuesta, catálogo, motor y pesos.", "Resultados y descarga CSV."),
    ("src/texto.py", "Limpieza y construcción del texto conjunto.", "Campos textuales de un registro.", "Texto normalizado para comparar."),
    ("src/fuentes.py", "Importación CSV, OpenAlex y texto de PDF.", "Archivo o consulta remota.", "DataFrame normalizado."),
    ("src/motor.py", "TF-IDF, embeddings y puntaje por sección.", "Propuesta, catálogo, modelo opcional.", "DataFrame ordenado con evidencia."),
    ("src/feedback.py", "Guardar etiquetas Sí/No de la interfaz.", "Consulta, registro y respuesta.", "Fila añadida a CSV local."),
    ("scripts/cosechar_oai.py", "Cosecha reanudable de metadatos OAI-PMH.", "Endpoint, formato y repositorio.", "CSV trazable más checkpoints."),
    ("scripts/evaluar_ranking.py", "Kappa y métricas de ranking.", "Juicios humanos en CSV largo.", "Resumen y rankings por consulta."),
], [1.55, 2.4, 1.75, 1.65], font=8.3)


heading("3. Datos de entrada y procedencia", 1)
heading("3.1 Catálogo", 2)
para("El catálogo de la aplicación se normaliza a un esquema común. El campo título es obligatorio. Resumen, autor, año, enlace, fuente, institución y campos por sección son opcionales en la importación; una cosecha institucional debe guardar procedencia para cada registro.")
table(["Campo", "Uso en el proyecto"], [
    ("id", "Identificador estable del registro dentro del catálogo."),
    ("titulo", "Título que aparece en la lista y forma parte del texto comparado."),
    ("problema / objetivos / metodologia", "Campos usados para la puntuación desglosada cuando están disponibles."),
    ("resumen", "Descripción del trabajo; entra en la comparación general si no hay secciones específicas."),
    ("autor / anio", "Información bibliográfica para contextualizar el resultado."),
    ("fuente / institucion / url", "Procedencia y enlace que permiten revisar el registro original."),
    ("oai_endpoint / oai_identifier / formato_oai / fecha_obtencion", "Trazabilidad de la cosecha institucional."),
], [2.25, 4.85])
heading("3.2 Archivos de ejemplo y datos reales", 2)
para("`datos/demo_ficticia.csv` contiene ejemplos fabricados para recorrer la interfaz. No son tesis peruanas y no se usan como evidencia del estudio. La guía no presenta sus puntuaciones como resultados de recuperación.")
para("El archivo `datos/plantilla_importacion.csv` sirve para preparar un CSV manual. Para OAI-PMH, el equipo debe confirmar el endpoint, el `metadataPrefix`, cualquier `setSpec` que limite el conjunto y las reglas institucionales de reutilización. El endpoint de DSPACE-UNT no está verificado en este proyecto.")
heading("3.3 Limpieza y construcción de consulta", 2)
para("`src/texto.py` reduce secuencias de espacios, convierte valores vacíos o nulos en cadenas vacías y combina título, problema, objetivos, metodología y resumen en un único texto. Cada campo se etiqueta en mayúsculas y limita su fragmento a 3500 caracteres; el conjunto se limita a 9000 caracteres.")
code('''CAMPOS = ["titulo", "problema", "objetivos", "metodologia", "resumen"]

def texto_investigacion(row):
    partes = []
    for campo in CAMPOS:
        valor = limpio(row.get(campo, ""))
        if valor:
            partes.append(f"{campo.upper()}: {valor[:3500]}")
    return "\\n".join(partes)[:9000]''', "Fragmento de src/texto.py: combinación de campos que recibe el motor")
para("Así el método general aprovecha el contenido disponible sin exigir que cada repositorio tenga campos idénticos. Para la puntuación específica por sección, `src/motor.py` compara los campos de sección de forma separada.")


heading("4. Métodos de comparación y puntuación", 1)
heading("4.1 TF-IDF y similitud coseno", 2)
para("TF-IDF representa un texto mediante pesos de términos. Un término recibe más peso si es frecuente en un documento y menos peso si aparece en muchos documentos del conjunto. El motor usa unigramas y bigramas, ignora diferencias de acentos y pasa el texto a minúsculas. Luego calcula el coseno entre el vector de consulta y los vectores candidatos.")
para("El coseno compara la dirección de dos vectores. En este caso toma valores entre 0 y 1 debido a los vectores TF-IDF no negativos. Es útil cuando la consulta y el antecedente comparten vocabulario, pero puede perder una relación que use palabras muy diferentes.")
code('''tfidf = TfidfVectorizer(
    ngram_range=(1, 2), strip_accents="unicode",
    lowercase=True, min_df=1, max_features=35000,
)
matriz = tfidf.fit_transform([consulta] + list(textos))
puntajes = cosine_similarity(matriz[0], matriz[1:]).ravel()''', "Fragmento de src/motor.py: vectorización y comparación léxica")
heading("4.2 Sentence-BERT", 2)
para("Sentence-BERT produce vectores densos (embeddings) para textos. El modelo multilingüe del proyecto se identifica como `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`. El motor codifica consulta y registros con `normalize_embeddings=True`; el producto punto entre vectores normalizados equivale a su coseno.")
para("El coseno semántico se conserva en la columna `coseno_semantico`. Para presentar un índice entre 0 y 100, el código transforma el coseno con `(coseno + 1) / 2` y multiplica por 100. Esta escala transformada ordena los registros; no es una probabilidad.")
code('''vectores = modelo.encode(
    [consulta] + list(textos),
    normalize_embeddings=True,
    convert_to_numpy=True,
    show_progress_bar=False,
    batch_size=16,
)
cosenos = vectores[1:] @ vectores[0]''', "Fragmento de src/motor.py: embeddings normalizados y coseno")
para("La longitud máxima configurada del modelo es de 128 tokens. Los textos que exceden ese límite pueden truncarse al codificarse, por lo que el final de resúmenes largos puede no influir en la comparación. Hay que conservar esta limitación en el análisis de errores.")
heading("4.3 Comparación por secciones y promedio ponderado", 2)
para("Para cada candidato el motor calcula tres similitudes: problema, objetivos y metodología. Los pesos iniciales son 0,40, 0,35 y 0,25, respectivamente. Si una sección falta en la consulta o en el antecedente, no se puntúa para ese par; se renormalizan los pesos que sí tienen datos.")
para("La fórmula aplicada a cada registro es:")
code("S = sum(w_s * sim_s para cada sección disponible) / sum(w_s para esas secciones)", "Puntuación de ordenamiento por secciones")
para("Por ejemplo, si la metodología no está disponible en un registro, el denominador suma solo los pesos de problema y objetivos, y la combinación se divide entre 0,75. Este ajuste impide tratar un campo ausente como similitud cero. Si no hay puntuación de sección utilizable, la implementación conserva el puntaje general como respaldo.")
code('''ponderaciones = np.where(
    np.isfinite(disponibles), pesos_vector[None, :], 0.0
)
suma_pesos = ponderaciones.sum(axis=1)
combinada = np.divide(
    np.nansum(disponibles * ponderaciones, axis=1),
    suma_pesos,
    out=indices.copy(),
    where=suma_pesos > 0,
)''', "Fragmento de src/motor.py: exclusión de campos vacíos y renormalización")
heading("4.4 Evidencia de términos compartidos", 2)
para("El motor busca palabras de contenido de cuatro o más letras presentes en la consulta y en cada campo del antecedente, elimina una lista pequeña de palabras funcionales y muestra hasta seis términos por sección. Esta evidencia facilita revisar por qué dos campos comparten vocabulario, pero no es una explicación completa de la decisión ni detecta equivalencia semántica por sí misma.")
heading("4.5 CrossEncoder para reranking", 2)
para("El CrossEncoder recibe consulta y documento juntos y calcula un puntaje conjunto. Por su coste, la evaluación lo aplica después del primer ordenamiento híbrido, sobre los primeros N candidatos. El modelo configurado es `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`; su tarjeta identifica MMARCO, conjunto derivado de MS MARCO traducido a varios idiomas. Es un modelo genérico externo y no se ha adaptado a tesis peruanas.")
para("El evaluador usa el CrossEncoder únicamente para reordenar los candidatos seleccionados. Los candidatos restantes conservan su orden híbrido. La tabla de métricas debe indicar la profundidad del reranking y usar el mismo pool de juicios para todas las configuraciones.")


heading("5. Explicación detallada del código de la aplicación", 1)
heading("5.1 app.py: formulario, controles y resultados", 2)
para("El archivo define la interfaz Streamlit. La barra lateral permite elegir catálogo, motor, número de resultados y pesos de sección. El formulario recoge título, problema, objetivo, metodología y un PDF de texto seleccionable opcional. Al pulsar Analizar, el código arma el diccionario de consulta y llama a `comparar`.")
para("Entradas: campos de la propuesta, catálogo, modo y valores de los controles. Salida: una tabla ordenada que se muestra en la página, con puntuación general y por sección. También permite descargar los resultados como CSV y registrar etiquetas locales Sí/No.")
code('''propuesta = {
    "titulo": nombre,
    "problema": problema,
    "objetivos": objetivos,
    "metodologia": metodologia,
    "resumen": texto_pdf[:5000],
    "pesos_seccion": pesos_seccion,
}
modo = "tradicional" if elegir.startswith("Tradicional") else "semantico"
modelo = get_modelo(modelo_path) if modo == "semantico" else None
resultado = comparar(propuesta, registro, modo=modo,
                     modelo=modelo, top_k=top_k)''', "Fragmento de app.py: preparación de la propuesta y llamada al motor")
para("El formulario preserva el estado de la sesión entre reruns de Streamlit. En el modo semántico, `get_modelo` almacena el modelo en caché para no volver a cargarlo en cada interacción. Si la primera descarga no está disponible, la interfaz muestra un error y permite volver al modo TF-IDF.")
heading("5.2 src/texto.py: normalización de texto", 2)
para("`limpio` convierte valores nulos en texto vacío y compacta espacios. `normalizar` pasa texto a minúsculas, descompone acentos y conserva letras, números, ñ y espacios. `texto_investigacion` concatena campos con rótulos para producir la entrada general de comparación. Estas funciones no enriquecen el contenido; solo reducen diferencias de formato.")
table(["Función", "Entrada", "Salida", "Uso"], [
    ("limpio(valor)", "Valor cualquiera.", "Cadena sin espacios redundantes.", "Importación y construcción de texto."),
    ("normalizar(valor)", "Texto.", "Texto en minúsculas y sin acentos.", "Comparaciones de igualdad exacta en evaluación."),
    ("texto_investigacion(row)", "Diccionario de campos.", "Texto conjunto limitado.", "Comparación general de consulta y documento."),
    ("contar_palabras(texto)", "Texto.", "Número de tokens por expresión regular.", "Utilidad para conteos."),
], [1.5, 1.65, 2.0, 2.0], font=8.5)
heading("5.3 src/fuentes.py: CSV, OpenAlex y PDF", 2)
para("`preparar_catalogo` estandariza nombres de columnas con alias comunes, crea los campos opcionales que falten, limpia valores, descarta títulos demasiado cortos y elimina duplicados por título y enlace. `leer_catalogo` intenta UTF-8 con BOM y recurre a Latin-1 si falla la decodificación.")
para("`buscar_openalex` consulta el endpoint de obras de OpenAlex y reconstruye resúmenes que vienen como índice invertido. La conexión es opcional y puede necesitar una clave de API. OpenAlex reúne distintos tipos de obras, por lo que su respuesta no equivale automáticamente a un catálogo de tesis peruanas.")
para("`extraer_pdf` usa pypdf para extraer hasta ocho páginas de texto seleccionable. Si no encuentra contenido suficiente, indica que el documento puede requerir OCR. El proyecto no implementa OCR.")
code('''COLUMNAS = [
    "id", "titulo", "problema", "objetivos", "metodologia",
    "resumen", "autor", "anio", "fuente", "url", "institucion",
    "oai_endpoint", "oai_identifier", "fecha_obtencion", "formato_oai",
]''', "Fragmento de src/fuentes.py: esquema normalizado del catálogo")
heading("5.4 src/motor.py: coordinación de los métodos", 2)
para("`similitud_lexica` genera la representación TF-IDF y el coseno. `cargar_modelo` importa SentenceTransformer y abre el modelo indicado. `similitud_semantica` calcula embeddings y cosenos. `comparar` valida entrada y catálogo, produce la puntuación general y las puntuaciones por sección, calcula términos compartidos, ordena por el índice y devuelve los primeros `top_k` registros.")
para("Los campos que entrega la tabla de resultados incluyen `indice`, `puntaje_tfidf`, opcionalmente `coseno_semantico`, `similitud_problema`, `similitud_objetivos`, `similitud_metodologia` y `evidencia_terminos`. El índice es la puntuación que se usa para ordenar; los demás campos permiten inspeccionar componentes.")
heading("5.5 src/feedback.py: registro de revisión de interfaz", 2)
para("`guardar_etiqueta` añade una fila a un CSV local con fecha UTC, ID de consulta, título de propuesta, título e ID del documento, respuesta binaria y fuente. Crea la cabecera si el archivo no existía. Las etiquetas de interfaz no constituyen por sí solas el conjunto del experimento porque no garantizan anotación ciega, asignación de varios evaluadores ni congelamiento de juicios.")
code('''writer.writerow({
    "fecha": datetime.now(timezone.utc).isoformat(),
    "consulta_id": consulta_id,
    "titulo_propuesta": titulo_propuesta,
    "titulo_documento": documento.get("titulo", ""),
    "id_documento": documento.get("id", ""),
    "relevante": int(bool(relevante)),
    "fuente": documento.get("fuente", ""),
})''', "Fragmento de src/feedback.py: fila que se agrega al CSV")


heading("6. Cosecha de metadatos OAI-PMH", 1)
heading("6.1 Qué hace el cosechador", 2)
para("`scripts/cosechar_oai.py` se conecta a un endpoint OAI-PMH. Primero ejecuta Identify y ListMetadataFormats para comprobar que el servicio contesta y conocer el formato anunciado. Usa Sickle si está disponible; si falla, realiza las solicitudes con requests y analiza XML con la biblioteca estándar.")
para("Después solicita ListRecords, guarda únicamente registros que tienen título y descripción/resumen, extrae año, autores y un enlace cuando los metadatos lo contienen, y agrega procedencia. No descarga archivos de tesis. El protocolo admite `resumptionToken`; el script guarda cada página en JSONL y conserva el token en un archivo de estado para continuar si el proceso se interrumpe.")
heading("6.2 Funciones y archivos generados", 2)
table(["Parte", "Responsabilidad", "Salida"], [
    ("_request", "Pedir XML y convertir errores HTTP/OAI en excepciones legibles.", "Raíz XML validada."),
    ("comprobar_endpoint", "Llamar Identify y ListMetadataFormats, Sickle o fallback XML.", "Nombre y prefijos anunciados."),
    ("_map_record", "Mapear Dublin Core a columnas del catálogo y anexar procedencia.", "Diccionario de metadatos o None."),
    ("cosechar", "Seguir páginas, persistir checkpoint, deduplicar y exportar.", "CSV final, JSONL y estado JSON."),
], [1.7, 3.25, 2.2], font=8.5)
code('''if token:
    params = {"verb": "ListRecords", "resumptionToken": token}
else:
    params = {"verb": "ListRecords", "metadataPrefix": prefix}
    if set_spec:
        params["set"] = set_spec
root = _request(endpoint, params, timeout)''', "Fragmento de scripts/cosechar_oai.py: petición de la siguiente página")
para("El token se guarda después de persistir los registros de la página. Si hay que reiniciar desde el principio, se recomienda usar otra ruta de salida; el checkpoint facilita reanudar y la exportación final deduplica por identificador OAI, enlace o título.")
heading("6.3 Comandos para empezar con una muestra", 2)
para("Solo después de obtener confirmación institucional, primero prueben el endpoint con `--max-registros 50`. Revisen manualmente 20 elementos y confirmen que el resumen sea útil y la procedencia esté presente. Si todo está correcto, ejecuten la cosecha completa; guarden la respuesta escrita de la biblioteca y la política aplicable como anexo.")
code('''python scripts/cosechar_oai.py `
  --endpoint "https://ENDPOINT-CONFIRMADO/oai/request" `
  --repositorio "Nombre del repositorio" `
  --formato oai_dc `
  --max-registros 50 `
  --salida datos/muestra_oai.csv''', "Ejemplo PowerShell: reemplazar endpoint y nombre solo tras confirmarlos")
para("El cosechador no fue ejecutado en el repositorio UNT en esta revisión porque no hay URL confirmada. La política pública de DSPACE-UNT localizada es de 2021; debe consultarse a la biblioteca para confirmar vigencia y condiciones actuales antes de recolectar.")


heading("7. Protocolo de evaluación del ranking", 1)
heading("7.1 Consultas, paráfrasis y candidatos", 2)
para("El protocolo propone 40 consultas de tesis reales y una paráfrasis revisada por persona para cada consulta, lo que puede producir hasta 80 versiones consultables. Se conserva el identificador de la tesis fuente y se excluye ese documento en todos los rankings. También se eliminan duplicados exactos normalizados.")
para("Para cada consulta se reúne el top 10 de cada configuración, se deduplican los identificadores y se forma el pool que van a juzgar los evaluadores. El máximo teórico es 40 documentos por consulta; normalmente se reduce si los métodos devuelven registros compartidos. Todos los evaluadores etiquetan todos los documentos del pool, incluidos los negativos, y trabajan por separado.")
heading("7.2 Rúbrica binaria", 2)
table(["Etiqueta", "Criterio operativo sugerido"], [
    ("1 - relevante", "El trabajo aborda un problema relacionado y comparte un objetivo, una población, un método o un contexto que podría ayudar a formular o justificar la propuesta. El evaluador puede identificar el vínculo en el título/resumen disponible."),
    ("0 - no relevante", "El parecido se limita a palabras amplias o a un área general; el problema, objetivo y enfoque no aportan un antecedente pertinente para la propuesta."),
], [1.45, 5.65])
para("Antes de empezar, el equipo debe adaptar esta rúbrica con el asesor y aplicarla de la misma forma a todas las consultas. Si los datos disponibles no bastan para decidir, pueden discutir una categoría de revisión durante el entrenamiento de anotadores, pero el CSV final del protocolo requiere una etiqueta binaria adjudicada.")
heading("7.3 Acuerdo entre evaluadores y Cohen kappa", 2)
para("El archivo usa formato largo: una fila por consulta, documento y evaluador. Con dos evaluadores se calcula Cohen kappa sobre los juicios coincidentes. Con tres evaluadores se calculan kappas por pares y se reporta su resumen junto con el detalle de cada par. Un empate de mayoría se resuelve en grupo y se registra en `relevante_adjudicado`.")
para("La fórmula es κ = (pₒ - pₑ) / (1 - pₑ), donde pₒ es el acuerdo observado y pₑ el acuerdo esperado según la distribución marginal de etiquetas. Si todos los juicios de uno o ambos evaluadores caen en una sola clase, el kappa puede quedar indefinido; debe informarse ese hecho y revisar la distribución, no ocultarlo.")
heading("7.4 Desarrollo y prueba sin contaminación", 2)
para("Agrupen por consulta fuente: una versión original y su paráfrasis deben quedarse en la misma partición. La partición de desarrollo sirve para decidir ajustes de pesos o verificar el flujo; las consultas de prueba quedan intactas hasta fijar el método. La orden del proyecto deja `alpha = 0.5` establecido de antemano para la combinación híbrida. No se cambia después de observar métricas de prueba.")
para("Los pesos por sección de la evaluación se conservan iguales entre métodos y se registran en el comando. Si se modifica un peso a partir de observaciones de desarrollo, se deja constancia del cambio antes de abrir la prueba. Las cuatro configuraciones deben puntuar exactamente el mismo conjunto juzgado por consulta.")
heading("7.5 Métricas", 2)
table(["Métrica", "Qué resume", "Cómo se calcula en este proyecto"], [
    ("Recall@K", "Proporción de relevantes juzgados dentro de los primeros K.", "Relevantes en top K / total de relevantes del pool de esa consulta."),
    ("MRR", "Posición del primer documento relevante.", "Promedio de 1/rango del primer relevante en el ranking completo del pool."),
    ("nDCG@K", "Ubicación de relevantes dentro del top K frente al orden ideal.", "Ganancia acumulada descontada por posición y normalizada; con relevancia binaria usa 0/1."),
    ("Cohen kappa", "Acuerdo interevaluador ajustado por acuerdo esperado.", "Se reporta por par sobre juicios comunes; no es una métrica de ranking."),
], [1.15, 2.55, 3.4], font=8.5)
para("El pool limita la interpretación: las métricas describen cómo se ordenan los documentos juzgados. Un documento fuera del pool no tiene etiqueta de irrelevante. Por ello, el informe debe indicar número de consultas, documentos únicos juzgados, evaluadores y K.")


heading("8. Explicación de scripts/evaluar_ranking.py", 1)
heading("8.1 Validación de entrada", 2)
para("El script verifica las columnas obligatorias, que las etiquetas sean 0/1, que haya dos o tres anotadores, que cada par consulta-documento tenga al menos dos juicios y que no existan filas duplicadas para el mismo evaluador. Después excluye el documento fuente y la coincidencia de texto idéntico normalizada.")
heading("8.2 Kappa por pares y consenso", 2)
para("`kappa_pareado` transforma las filas en una tabla con un evaluador por columna y calcula kappa sobre los pares donde ambos evaluadores juzgaron el mismo elemento. `consensos` usa mayoría simple; si existe empate con dos evaluadores, exige `relevante_adjudicado` para poder continuar.")
code('''ratings = df.pivot_table(
    index=["consulta_id", "documento_id"],
    columns="anotador", values="relevante", aggfunc="first",
)
for a, b in combinations(ratings.columns, 2):
    pares = ratings[[a, b]].dropna()
    kappa = cohen_kappa_score(pares[a].astype(int), pares[b].astype(int))''', "Fragmento de scripts/evaluar_ranking.py: kappa por par de evaluadores")
heading("8.3 Métricas por consulta", 2)
code('''recall = len(relevantes.intersection(orden[:k])) / len(relevantes)
primer_rango = next(
    (i + 1 for i, ident in enumerate(orden) if ident in relevantes), None
)
mrr = 1 / primer_rango if primer_rango else 0.0
rels = [1 if ident in relevantes else 0 for ident in orden[:k]]
dcg = sum(rel / np.log2(i + 2) for i, rel in enumerate(rels))
ideal = sum(1 / np.log2(i + 2) for i in range(min(len(relevantes), k)))
ndcg = dcg / ideal if ideal else 0.0''', "Fragmento de scripts/evaluar_ranking.py: Recall, MRR y nDCG binaria")
para("Si una consulta no tiene ningún documento juzgado como relevante, el código omite sus valores de las medias de ranking y el contador de consultas evaluadas lo refleja. Esa regla debe mencionarse al presentar resultados, junto con el número de consultas omitidas.")
heading("8.4 Cuatro configuraciones y archivos de salida", 2)
para("Por cada consulta, el evaluador calcula TF-IDF y Sentence-BERT, combina sus puntuaciones con `alpha`, y opcionalmente reordena los primeros N candidatos con CrossEncoder. Produce una tabla resumen por método y tipo de consulta, otra tabla con el orden de documentos para cada consulta y un archivo con kappas por pares.")
code('''python scripts/evaluar_ranking.py `
  --datos datos/juicios.csv `
  --salida resultados/tabla_metricas.csv `
  --k 5 `
  --alpha 0.5 `
  --peso-problema 0.40 `
  --peso-objetivos 0.35 `
  --peso-metodologia 0.25 `
  --profundidad-rerank 40''', "Ejemplo PowerShell: K y profundidad deben informarse en el informe")
para("El comando anterior es una plantilla: no debe ejecutarse hasta que `datos/juicios.csv` contenga anotaciones completas, independientes y congeladas. El ejecutable descarga o carga el modelo semántico y el reranker si no están disponibles localmente.")
table(["Archivo producido", "Contenido esperado"], [
    ("tabla_metricas.csv", "Media global y por tipo de consulta, con Recall@K, MRR, nDCG@K y número de consultas válidas."),
    ("tabla_metricas_por_consulta.csv", "Orden de los documentos por cada consulta y configuración."),
    ("tabla_metricas_kappa.csv", "Detalle del acuerdo para cada par de evaluadores."),
], [2.75, 4.35])


heading("8.5 Ajuste opcional de Sentence-BERT", 2)
para("`scripts/entrenar.py` es una ruta opcional. Recibe pares texto_a/texto_b con etiqueta binaria y columna `grupo`. Usa GroupShuffleSplit para mantener separados grupos de propuestas y reserva una fracción para evaluación. La pérdida `CosineSimilarityLoss` ajusta embeddings con los pares de entrenamiento.")
para("El script comprueba que haya suficientes pares y grupos, ambas clases y una división de entrenamiento que conserve las dos etiquetas. Guarda los pares reservados en `pares_prueba_reservados.csv` y el modelo ajustado en la carpeta indicada. El conjunto reservado no se usa para entrenar.")
para("`scripts/evaluar_pares.py` mide AP y ROC-AUC en pares reservados para el modelo base y el modelo ajustado. Esas métricas responden a clasificación de pares; no reemplazan Recall@K, MRR o nDCG para la tarea de ranking. Fine-tuning solo tiene sentido si existen pares reales suficientes y se mantiene la separación por grupos.")
code('''python scripts/entrenar.py `
  --datos datos/pares_reales_revisados.csv `
  --salida modelos/tesis_radar_ajustado `
  --epocas 2

python scripts/evaluar_pares.py `
  --datos modelos/tesis_radar_ajustado/pares_prueba_reservados.csv `
  --modelo modelos/tesis_radar_ajustado''', "Comandos opcionales; los pares ficticios solo sirven para verificar el flujo")


heading("9. Limitaciones y uso responsable", 1)
for x in [
    "Cobertura: la recuperación depende de la fuente, la cantidad de registros y la calidad de título/resumen. Registros ausentes o incompletos afectan el orden.",
    "Alcance de los juicios: el pool revisado limita las métricas. Un documento no juzgado no debe tratarse automáticamente como irrelevante.",
    "Longitud: el modelo semántico tiene un máximo de 128 tokens por entrada en esta configuración y puede truncar resúmenes extensos.",
    "Dominio: el modelo Sentence-BERT es multilingüe genérico y el CrossEncoder configurado tampoco se ajustó a tesis peruanas.",
    "Paráfrasis: cada reescritura asistida por un modelo de lenguaje necesita revisión de una persona y vínculo claro con su consulta fuente.",
    "Interpretación: la puntuación es una transformación matemática usada para ordenar candidatos. No es una probabilidad.",
    "Metadatos: cosechar solo campos permitidos por la política vigente de la institución y conservar endpoint, enlace, identificador y fecha.",
    "Uso: la herramienta ayuda a localizar material para revisión académica. La decisión sobre pertinencia y calidad del antecedente corresponde al equipo asesor.",
]: bullet(x)


heading("10. Estado de resultados", 1)
para("La comprobación funcional detallada, incluidas las versiones y el alcance de la prueba, se documenta en el Anexo C.")
heading("10.1 Tabla de resultados científicos", 2)
para("Las celdas de resultado se mantienen pendientes. No existen en el proyecto un catálogo peruano cosechado y un `juicios.csv` completo con anotadores independientes; por tanto, no hay cifras válidas de rendimiento para las cuatro configuraciones.")
table(["Método", "Recall@5", "MRR", "nDCG@5"], [
    ("TF-IDF", "Pendiente", "Pendiente", "Pendiente"),
    ("Sentence-BERT", "Pendiente", "Pendiente", "Pendiente"),
    ("Híbrido (alpha = 0.5)", "Pendiente", "Pendiente", "Pendiente"),
    ("Híbrido + CrossEncoder", "Pendiente", "Pendiente", "Pendiente"),
], [2.45, 1.55, 1.4, 1.7])
para("Las puntuaciones que aparecen en el recorrido de demostración son calculadas por el prototipo sobre registros ficticios. No se copian a esta tabla porque no forman parte de una evaluación con juicios humanos.")


heading("11. Plan operativo para completar el estudio", 1)
table(["Paso", "Acción", "Evidencia para cerrar el paso"], [
    ("1. Fuente", "Consultar al asesor y a la biblioteca; confirmar endpoint, formato, set y política vigente.", "Respuesta institucional guardada y endpoint que responde Identify y ListMetadataFormats."),
    ("2. Muestra", "Cosechar hasta 50 metadatos y revisar a mano 20 registros.", "Muestra válida con resumen, enlace y procedencia."),
    ("3. Catálogo", "Cosechar el conjunto acordado; meta orientativa 2 000 a 5 000 registros.", "catalogo_real.csv con fuente y fecha por registro."),
    ("4. Consultas", "Elegir 40 tesis fuente y redactar una paráfrasis revisada para cada una.", "Archivo de consultas con ID fuente y tipo original/parafraseada."),
    ("5. Anotación", "Formar top 10 por método, deduplicar, excluir la fuente y anotar ciegamente con 2 o 3 integrantes.", "juicios.csv completo, kappa pareado y adjudicación de empates."),
    ("6. Medición", "Fijar K, alpha, pesos y profundidad de reranking; ejecutar las cuatro configuraciones.", "CSV de métricas y ranking detallado por consulta."),
    ("7. Informe", "Revisar casos de error por consulta original/parafraseada y completar resultados.", "Tabla reproducible, análisis y limitaciones."),
], [1.0, 3.45, 2.65], font=8.25)
heading("Anexos", 1)
heading("Anexo A. Solicitud a la biblioteca y estado de respuesta", 2)
para("Asunto: Consulta sobre cosecha de metadatos del repositorio institucional")
para("Estimado/a: Somos estudiantes de [curso] de la Universidad Nacional de Trujillo y desarrollamos TESIS-RADAR, un proyecto académico para buscar antecedentes por sección de una propuesta de investigación. La política pública de DSPACE-UNT que encontramos indica que los metadatos pueden reutilizarse manteniendo el identificador o enlace persistente. ¿Podrían confirmarnos si esa política continúa vigente y facilitarnos el endpoint OAI-PMH, el formato de metadatos y, si corresponde, el set recomendado para tesis? El proyecto cosecharía únicamente título, resumen, año e identificador/enlace para uso académico; no descargaría textos completos. También agradeceríamos conocer cualquier condición de uso, atribución, límite de solicitudes o restricción de redistribución aplicable. Conservaremos la respuesta y la procedencia de los registros en el informe del proyecto. Atentamente, [nombres del equipo] [curso y contacto institucional].")
para("Estado de respuesta: no recibida al preparar esta guía. Completar esta nota con la fecha y el contenido de la respuesta institucional cuando llegue; no se ha confirmado un endpoint.")
heading("Anexo B. Columnas del archivo de juicios", 2)
code('''consulta_id,consulta,consulta_origen_id,tipo_consulta,
consulta_problema,consulta_objetivos,consulta_metodologia,
documento_id,texto_documento,documento_problema,
documento_objetivos,documento_metodologia,
anotador,relevante,relevante_adjudicado''', "Encabezado de datos/plantilla_evaluacion.csv")
para("`consulta_id` identifica una versión de la consulta; `consulta_origen_id` conserva el ID de tesis que originó la consulta; `tipo_consulta` diferencia original y parafraseada. Cada pareja consulta/documento aparece una vez por anotador. `relevante_adjudicado` permanece vacío salvo cuando el grupo resuelve un empate.")
heading("Anexo C. Comprobación funcional", 2)
para("Fecha: 21 de noviembre de 2026. Se ejecutó `ACTIVAR_MODELO_WINDOWS.bat`; el modelo `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` informó carga correcta. Se abrió la interfaz y se analizó una propuesta de demostración con TF-IDF y Sentence-BERT real. Ambos modos mostraron ocho resultados a partir de 36 registros ficticios y presentaron el motor utilizado, similitud por sección, índice y términos compartidos. Se revisaron capturas de ambas vistas y no se observó un error de análisis.")
table(["Componente", "Versión observada"], [
    ("Python", "3.14.7"), ("Streamlit", "1.67.0"), ("sentence-transformers", "5.7.0"),
    ("Transformers", "5.24.0"), ("PyTorch", "2.15.0"), ("scikit-learn", "1.9.1"),
    ("pandas", "2.3.3"), ("NumPy", "2.5.5"),
], [3.0, 4.1])
para("Esta comprobación confirma el recorrido funcional con datos ficticios, no la calidad de recuperación ni el desempeño científico. La guía de inicio recomienda Python 3.11 o 3.12; se debe repetir la comprobación en la versión objetivo. Siguen pendientes OpenAlex en vivo, cosecha OAI-PMH institucional y evaluación con tesis peruanas y juicios humanos.")
heading("Referencias", 1)
refs = [
    "CONCYTEC (2026). Principales indicadores bibliométricos de la actividad científica peruana, 2018–2024. Indicadores reportados para 2024: 11 220 publicaciones científicas y 56,3 % de acceso abierto. https://repositorio.concytec.gob.pe/server/api/core/bitstreams/fcab8f8b-15da-47e5-b40a-88198594fa5d/content",
    "CONCYTEC (2025). Guía ALICIA 2.1.0: directrices para repositorios institucionales de RENARE. https://repositorio.concytec.gob.pe/bitstreams/8f39f4b3-897b-428f-a43c-2658ff23a3cd/download",
    "Turnitin (2026). Understanding the Similarity Score. https://guides.turnitin.com/hc/en-us/articles/23435833938701-Understanding-the-similarity-score",
    "Reimers, N. y Gurevych, I. (2019). Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks. EMNLP-IJCNLP. https://doi.org/10.18653/v1/D19-1410",
    "Sentence Transformers. paraphrase-multilingual-MiniLM-L12-v2, ficha del modelo; longitud máxima de secuencia indicada: 128. https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "Sentence Transformers. Computing Embeddings: Input Sequence Length. https://www.sbert.net/examples/sentence_transformer/applications/computing-embeddings/README.html",
    "Sentence Transformers. Cross-Encoder usage. https://sbert.net/docs/cross_encoder/usage/usage.html",
    "Cross-Encoder. mmarco-mMiniLMv2-L12-H384-v1, ficha del modelo. https://huggingface.co/cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
    "Järvelin, K. y Kekäläinen, J. (2002). Cumulated Gain-based Evaluation of IR Techniques. ACM TOIS, 20(4), 422–446. https://doi.org/10.1145/582415.582418",
    "Cohen, J. (1960). A Coefficient of Agreement for Nominal Scales. Educational and Psychological Measurement, 20(1), 37–46. https://doi.org/10.1177/001316446002000104",
    "Universidad Nacional de Trujillo (2021). Políticas del repositorio DSPACE-UNT, versión 0.2, pp. 6–7. La vigencia debe confirmarse con la biblioteca. https://unitru.edu.pe/webfiles/Instructivos/politicasrepositorio.pdf",
    "Open Archives Initiative. Protocol for Metadata Harvesting, Version 2.0. https://www.openarchives.org/OAI/openarchivesprotocol.html",
    "Sickle. OAI-PMH client for Python, versión 0.7.0. https://pypi.org/project/Sickle/",
]
for ref in refs:
    p = doc.add_paragraph(style="List Number")
    p.paragraph_format.space_after = Pt(5)
    p.add_run(ref)
# Core properties and save.
doc.core_properties.title = "Guía técnica de TESIS RADAR"
doc.core_properties.subject = "Funcionamiento, código y metodología de evaluación"
doc.core_properties.author = "Equipo TESIS-RADAR"
doc.core_properties.keywords = "TESIS-RADAR, buscador de antecedentes, TF-IDF, Sentence-BERT"
OUT.parent.mkdir(parents=True, exist_ok=True)
doc.save(OUT)
print(f"Generado: {OUT}")


