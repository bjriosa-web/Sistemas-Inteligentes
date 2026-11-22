"""Evalúa recuperación por consulta con juicios humanos en formato largo.

CSV requerido: consulta_id,consulta,consulta_origen_id,documento_id,
texto_documento,anotador,relevante. Una fila por evaluador y par.
"""
import argparse
from itertools import combinations
from pathlib import Path
import re
import sys
import unicodedata

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import cohen_kappa_score
from sklearn.metrics.pairwise import cosine_similarity

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.motor import cargar_modelo, MODELO_PUBLICO

REQUERIDAS = {"consulta_id", "consulta", "consulta_origen_id", "tipo_consulta", "documento_id",
              "texto_documento", "anotador", "relevante"}
SECCIONES = ("problema", "objetivos", "metodologia")


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto or "").casefold())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\W+", " ", texto, flags=re.UNICODE).strip()


def kappa_pareado(df):
    """Media de Cohen kappa en pares de anotadores sobre juicios coincidentes."""
    ratings = df.pivot_table(index=["consulta_id", "documento_id"], columns="anotador",
                             values="relevante", aggfunc="first")
    nombres = list(ratings.columns)
    valores = []
    for a, b in combinations(nombres, 2):
        pares = ratings[[a, b]].dropna()
        if len(pares):
            kappa = float(cohen_kappa_score(pares[a].astype(int), pares[b].astype(int)))
            if np.isfinite(kappa):
                valores.append({"anotador_a": a, "anotador_b": b, "pares_en_comun": len(pares), "kappa": kappa})
    return valores


def metricas(relevantes, orden, k):
    relevantes = set(relevantes)
    orden = list(orden)
    if not relevantes:
        return None
    primeros = orden[:k]
    recall = len(relevantes.intersection(primeros)) / len(relevantes)
    primer_rango = next((i + 1 for i, ident in enumerate(orden) if ident in relevantes), None)
    mrr = 1 / primer_rango if primer_rango else 0.0
    rels = [1 if ident in relevantes else 0 for ident in primeros]
    dcg = sum(rel / np.log2(i + 2) for i, rel in enumerate(rels))
    ideal = sum(1 / np.log2(i + 2) for i in range(min(len(relevantes), k)))
    return recall, mrr, dcg / ideal if ideal else 0.0


def consensos(df):
    agg = {"votos": ("relevante", "sum"), "n_anotadores": ("relevante", "count"),
           "consulta": ("consulta", "first"), "consulta_origen_id": ("consulta_origen_id", "first"),
           "texto_documento": ("texto_documento", "first")}
    if "tipo_consulta" in df:
        agg["tipo_consulta"] = ("tipo_consulta", "first")
    if "relevante_adjudicado" in df:
        agg["relevante_adjudicado"] = ("relevante_adjudicado", lambda values: next((v for v in values if str(v).strip()), ""))
    for sec in SECCIONES:
        for prefix in ("consulta_", "documento_"):
            col = prefix + sec
            if col in df:
                agg[col] = (col, "first")
    votes = df.groupby(["consulta_id", "documento_id"], as_index=False).agg(**agg)
    votes["relevante"] = (votes["votos"] * 2 > votes["n_anotadores"]).astype(int)
    ties = votes["votos"] * 2 == votes["n_anotadores"]
    if ties.any():
        if "relevante_adjudicado" not in votes or votes.loc[ties, "relevante_adjudicado"].eq("").any():
            raise ValueError("Hay empates entre evaluadores. Complete relevante_adjudicado (0/1) tras la revisión grupal.")
        adjudicado = pd.to_numeric(votes.loc[ties, "relevante_adjudicado"], errors="raise").astype(int)
        if not adjudicado.isin([0, 1]).all():
            raise ValueError("relevante_adjudicado debe ser 0 o 1")
        votes.loc[ties, "relevante"] = adjudicado
    return votes


def evaluar(path, salida, modelo_nombre, reranker_nombre, rerank_depth=100, k=5, alpha=0.5, pesos_seccion=None):
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    faltan = REQUERIDAS - set(raw.columns)
    if faltan:
        raise ValueError("Faltan columnas: " + ", ".join(sorted(faltan)))
    if "relevante_adjudicado" not in raw:
        raw["relevante_adjudicado"] = ""
    else:
        invalid = raw["relevante_adjudicado"].ne("") & ~raw["relevante_adjudicado"].isin(["0", "1"])
        if invalid.any():
            raise ValueError("relevante_adjudicado debe estar vacío, 0 o 1")
    raw["relevante"] = pd.to_numeric(raw["relevante"], errors="raise").astype(int)
    if not raw["relevante"].isin([0, 1]).all():
        raise ValueError("relevante debe ser 0 o 1")
    if raw.duplicated(["consulta_id", "documento_id", "anotador"]).any():
        raise ValueError("Hay más de un juicio para el mismo consulta-documento-anotador.")
    n_annotators = raw["anotador"].nunique()
    if n_annotators < 2 or n_annotators > 3:
        raise ValueError("El protocolo requiere 2 o 3 anotadores identificados.")
    counts = raw.groupby(["consulta_id", "documento_id"])["anotador"].nunique()
    if (counts < 2).any():
        raise ValueError("Cada par consulta-documento debe tener juicios de al menos 2 anotadores.")

    # Se excluye siempre el documento del que proviene la consulta y cualquier
    # coincidencia exacta normalizada. También se reporta cuántos juicios salen.
    df = raw.copy()
    df["_query_norm"] = df["consulta"].map(normalizar)
    df["_doc_norm"] = df["texto_documento"].map(normalizar)
    df["_self_match"] = ((df["consulta_origen_id"] != "") &
                          (df["consulta_origen_id"] == df["documento_id"])) | (df["_query_norm"] == df["_doc_norm"])
    excluidos = int(df["_self_match"].sum())
    df = df[~df["_self_match"]].drop(columns=["_query_norm", "_doc_norm", "_self_match"])
    if df.empty:
        raise ValueError("No quedan pares después de excluir consultas y duplicados exactos.")

    kappas = kappa_pareado(df)
    gold = consensos(df)
    # Asegura consistencia del texto de consulta y de cada documento dentro de IDs.
    q_agg = {"consulta": ("consulta", "first"), "consulta_origen_id": ("consulta_origen_id", "first"),
             "tipo_consulta": ("tipo_consulta", "first")}
    for sec in SECCIONES:
        col = "consulta_" + sec
        if col in gold:
            q_agg[col] = (col, "first")
    qinfo = gold.groupby("consulta_id").agg(**q_agg)
    doc_cols = ["texto_documento"] + ["documento_" + s for s in SECCIONES if "documento_" + s in gold]
    docs = gold.drop_duplicates("documento_id").set_index("documento_id")[doc_cols].to_dict("index")
    relevant_by_q = {qid: set(g.loc[g.relevante == 1, "documento_id"])
                     for qid, g in gold.groupby("consulta_id")}
    candidate_by_q = {qid: list(g.documento_id) for qid, g in gold.groupby("consulta_id")}

    model = cargar_modelo(modelo_nombre)
    reranker = None
    if reranker_nombre:
        try:
            from sentence_transformers import CrossEncoder
            reranker = CrossEncoder(reranker_nombre)
        except ImportError as exc:
            raise RuntimeError("Sentence-Transformers debe estar instalado para el reranker.") from exc

    rows = []
    per_query = {}
    for qid in qinfo.index:
        query = qinfo.loc[qid, "consulta"]
        ids = candidate_by_q.get(qid, [])
        doc_rows = [docs[d] for d in ids]
        texts = [row.get("texto_documento", "") for row in doc_rows]
        if not ids:
            continue
        weights = pesos_seccion or {"problema": 0.40, "objetivos": 0.35, "metodologia": 0.25}
        section_fields = [s for s in SECCIONES if "consulta_" + s in qinfo and "documento_" + s in gold]
        qsections = {s: str(qinfo.loc[qid].get("consulta_" + s, "") or "").strip() for s in section_fields}
        active_sections = [s for s in section_fields if qsections[s] and
                           any(str(row.get("documento_" + s, "") or "").strip() for row in doc_rows)]
        if not active_sections:
            active_sections = ["total"]
        weighted_tfidf = np.zeros(len(ids), dtype=float)
        weighted_sbert = np.zeros(len(ids), dtype=float)
        weight_totals = np.zeros(len(ids), dtype=float)
        for sec in active_sections:
            qtext = qsections[sec] if sec != "total" else query
            field = "documento_" + sec if sec != "total" else "texto_documento"
            dtexts = [str(row.get(field, "") or "").strip() for row in doc_rows]
            valid = [i for i, text in enumerate(dtexts) if text]
            weight = float(weights.get(sec, 1.0)) if sec != "total" else 1.0
            if not qtext or not valid or weight <= 0:
                continue
            lex = np.full(len(ids), np.nan)
            sem = np.full(len(ids), np.nan)
            try:
                matrix = TfidfVectorizer(ngram_range=(1, 2), strip_accents="unicode", min_df=1).fit_transform(
                    [qtext] + [dtexts[i] for i in valid])
                lex[valid] = cosine_similarity(matrix[0], matrix[1:]).ravel()
            except ValueError:
                lex[valid] = 0.0
            vectors = model.encode([qtext] + [dtexts[i] for i in valid], normalize_embeddings=True,
                                   convert_to_numpy=True, show_progress_bar=False, batch_size=32)
            sem[valid] = np.clip((vectors[1:] @ vectors[0] + 1) / 2, 0, 1)
            present = np.isfinite(lex) & np.isfinite(sem)
            weighted_tfidf[present] += weight * lex[present]
            weighted_sbert[present] += weight * sem[present]
            weight_totals[present] += weight
        tfidf = np.divide(weighted_tfidf, weight_totals, out=np.zeros(len(ids)), where=weight_totals > 0)
        sbert = np.divide(weighted_sbert, weight_totals, out=np.zeros(len(ids)), where=weight_totals > 0)
        hybrid = alpha * tfidf + (1 - alpha) * sbert
        scores = {"TF-IDF": tfidf, "Sentence-BERT": sbert, f"Híbrido (α={alpha:.2f})": hybrid}
        # El reranker reordena solo los primeros N del híbrido; el resto conserva
        # su posición relativa. Su resultado se evalúa contra los mismos juicios.
        if reranker is not None:
            order = np.argsort(-hybrid, kind="stable")
            depth = min(max(1, rerank_depth), len(order))
            selected = order[:depth]
            if active_sections != ["total"]:
                rerank_query = "\n".join(f"{sec}: {qsections[sec]}" for sec in active_sections)
                rerank_docs = ["\n".join(f"{sec}: {row.get('documento_' + sec, '')}" for sec in active_sections
                                          if str(row.get("documento_" + sec, "") or "").strip()) or texts[i]
                               for i, row in enumerate(doc_rows)]
            else:
                rerank_query, rerank_docs = query, texts
            pair_scores = reranker.predict([(rerank_query, rerank_docs[i]) for i in selected], show_progress_bar=False)
            reranked_top = selected[np.argsort(-np.asarray(pair_scores).reshape(-1), kind="stable")]
            reranked_order = list(reranked_top) + list(order[depth:])
            # Codifica solo orden, porque logits del cross-encoder y score híbrido
            # no comparten escala comparable.
            reranked = np.empty(len(ids), dtype=float)
            for rank, idx in enumerate(reranked_order):
                reranked[idx] = len(ids) - rank
            scores["Híbrido + cross-encoder reranker"] = reranked
        elif "reranker" in reranker_nombre.lower():
            raise ValueError("Especifica un nombre de modelo CrossEncoder con --reranker; deja vacío para omitir el cuarto método.")
        rels = relevant_by_q.get(qid, set())
        per_query[qid] = {}
        for method, score in scores.items():
            ranked_ids = [ids[i] for i in np.argsort(-score, kind="stable")]
            per_query[qid][method] = metricas(rels, ranked_ids, k)
            rows.append({"consulta_id": qid, "metodo": method, "n_candidatos": len(ids),
                         "tipo_consulta": qinfo.loc[qid, "tipo_consulta"],
                         "n_relevantes_consenso": len(rels), "orden_documentos": "|".join(ranked_ids)})

    summary = []
    methods = list(next(iter(per_query.values())).keys()) if per_query else []
    for method in methods:
        tipos = ["todas"] + sorted(set(qinfo["tipo_consulta"].astype(str)))
        for tipo in tipos:
            qids = [qid for qid in per_query if tipo == "todas" or str(qinfo.loc[qid, "tipo_consulta"]) == tipo]
            valid = [per_query[qid][method] for qid in qids if per_query[qid][method] is not None]
            summary.append({"metodo": method, "tipo_consulta": tipo, "consultas_evaluadas": len(valid),
                            f"Recall@{k}": round(float(np.mean([v[0] for v in valid])), 4) if valid else None,
                            "MRR": round(float(np.mean([v[1] for v in valid])), 4) if valid else None,
                            f"nDCG@{k}": round(float(np.mean([v[2] for v in valid])), 4) if valid else None})
    out = Path(salida)
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(summary).to_csv(out, index=False, encoding="utf-8-sig")
    out.with_name(out.stem + "_por_consulta.csv").write_text(pd.DataFrame(rows).to_csv(index=False), encoding="utf-8-sig")
    out.with_name(out.stem + "_kappa.csv").write_text(pd.DataFrame(kappas).to_csv(index=False), encoding="utf-8-sig")
    print(f"Excluidos por consulta fuente/duplicado exacto: {excluidos}")
    print(f"Kappa pareado medio: {np.mean([x['kappa'] for x in kappas]):.4f}" if kappas else "Kappa no calculable: faltan pares de anotadores con ambas clases.")
    print(pd.DataFrame(summary).to_string(index=False))
    print(f"Resultados guardados en {out}")


def main():
    p = argparse.ArgumentParser(description="Evalúa ranking con juicios humanos; una fila por consulta-documento-anotador.")
    p.add_argument("--datos", required=True)
    p.add_argument("--salida", default="resultados/evaluacion_ranking.csv")
    p.add_argument("--modelo", default=MODELO_PUBLICO, help="Sentence-BERT multilingüe")
    p.add_argument("--reranker", default="cross-encoder/mmarco-mMiniLMv2-L12-H384-v1", help="CrossEncoder multilingüe; usa cadena vacía para omitirlo")
    p.add_argument("--profundidad-rerank", type=int, default=100)
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--alpha", type=float, default=0.5, help="Peso TF-IDF del híbrido, entre 0 y 1")
    p.add_argument("--peso-problema", type=float, default=0.40)
    p.add_argument("--peso-objetivos", type=float, default=0.35)
    p.add_argument("--peso-metodologia", type=float, default=0.25)
    a = p.parse_args()
    if not 0 <= a.alpha <= 1:
        p.error("--alpha debe estar entre 0 y 1")
    weights = {"problema": a.peso_problema, "objetivos": a.peso_objetivos,
               "metodologia": a.peso_metodologia}
    if any(v < 0 for v in weights.values()) or sum(weights.values()) <= 0:
        p.error("Los pesos de sección deben ser no negativos y sumar más de cero")
    evaluar(a.datos, a.salida, a.modelo, a.reranker, a.profundidad_rerank, a.k, a.alpha, weights)


if __name__ == "__main__":
    main()
