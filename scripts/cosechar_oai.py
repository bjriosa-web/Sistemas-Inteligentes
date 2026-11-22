"""Cosecha reanudable de metadatos por OAI-PMH; nunca descarga textos completos."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import re
import sys
import time
import xml.etree.ElementTree as ET

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

NS = {"oai": "http://www.openarchives.org/OAI/2.0/", "dc": "http://purl.org/dc/elements/1.1/"}
DC_NS = "{http://purl.org/dc/elements/1.1/}"
USER_AGENT = "TESIS-RADAR-academic-metadata-harvester/1.0 (contact: repository administrator)"


def _request(endpoint, params, timeout):
    response = requests.get(endpoint, params=params, timeout=timeout,
                            headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as exc:
        raise RuntimeError(f"La respuesta no es XML OAI-PMH válido: {exc}") from exc
    error = root.find("oai:error", NS)
    if error is not None:
        raise RuntimeError(f"Error OAI-PMH {error.get('code', '')}: {error.text or ''}")
    return root


def comprobar_endpoint(endpoint, timeout=30):
    """Comprueba Identify y formatos; Sickle se usa si está instalado, con fallback nativo."""
    try:
        from sickle import Sickle
        cliente = Sickle(endpoint, timeout=timeout)
        identify = cliente.Identify()
        formatos = list(cliente.ListMetadataFormats())
        nombre = getattr(identify, "repositoryName", "") or ""
        prefijos = [getattr(x, "metadataPrefix", "") for x in formatos]
        prefijos = [x for x in prefijos if x]
        if nombre or prefijos:
            return {"repository_name": nombre, "metadata_prefixes": prefijos, "client": "Sickle"}
    except Exception:
        pass

    ident_root = _request(endpoint, {"verb": "Identify"}, timeout)
    name_node = ident_root.find("oai:Identify/oai:repositoryName", NS)
    name = name_node.text.strip() if name_node is not None and name_node.text else ""
    formats_root = _request(endpoint, {"verb": "ListMetadataFormats"}, timeout)
    prefixes = [n.text.strip() for n in formats_root.findall("oai:ListMetadataFormats/oai:metadataFormat/oai:metadataPrefix", NS) if n.text]
    return {"repository_name": name, "metadata_prefixes": prefixes, "client": "requests+xml"}


def _texts(record, tag):
    return [n.text.strip() for n in record.findall(f".//{DC_NS}{tag}") if n.text and n.text.strip()]


def _map_record(record, endpoint, repository, obtained, prefix):
    header_id = record.find("oai:header/oai:identifier", NS)
    identifier = header_id.text.strip() if header_id is not None and header_id.text else ""
    title = " ".join(_texts(record, "title"))
    abstract = " ".join(_texts(record, "description"))
    if not title or not abstract:
        return None
    dates = _texts(record, "date")
    year = next((m.group(0) for value in dates if (m := re.search(r"(?:18|19|20|21)\d{2}", value))), "")
    identifiers = _texts(record, "identifier") + _texts(record, "relation")
    link = next((u for u in identifiers if u.startswith(("https://", "http://"))), "")
    creators = _texts(record, "creator")
    publishers = _texts(record, "publisher")
    return {
        "id": identifier,
        "titulo": title,
        "resumen": abstract,
        "autor": "; ".join(creators),
        "anio": year,
        "fuente": repository,
        "institucion": "; ".join(publishers) or repository,
        "url": link,
        "oai_endpoint": endpoint,
        "oai_identifier": identifier,
        "fecha_obtencion": obtained,
        "formato_oai": prefix,
    }


def _atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def cosechar(endpoint, salida, repository, prefix="oai_dc", set_spec="", max_records=0,
             timeout=60, pause=0.2, resume=True):
    salida = Path(salida)
    checkpoint = salida.with_suffix(salida.suffix + ".oai.jsonl")
    state = salida.with_suffix(salida.suffix + ".oai-state.json")
    info = comprobar_endpoint(endpoint, timeout)
    if prefix not in info["metadata_prefixes"]:
        raise ValueError(f"El repositorio no anuncia el formato {prefix}. Formatos: {', '.join(info['metadata_prefixes']) or '(ninguno)'}")

    token = ""
    if resume and checkpoint.exists() and state.exists():
        token = json.loads(state.read_text(encoding="utf-8")).get("resumption_token", "")
        print(f"Reanudando desde checkpoint: {checkpoint}")
    elif state.exists() and not checkpoint.exists():
        raise FileExistsError("Existe un estado de cosecha, pero no el checkpoint de registros. No se puede reanudar con seguridad.")
    elif checkpoint.exists() and not state.exists():
        print("Checkpoint sin token: se reinicia desde la primera página y se deduplican los identificadores al exportar.")

    obtained = datetime.now(timezone.utc).isoformat(timespec="seconds")
    accepted = sum(1 for _ in checkpoint.open(encoding="utf-8")) if checkpoint.exists() else 0
    while True:
        if token:
            params = {"verb": "ListRecords", "resumptionToken": token}
        else:
            params = {"verb": "ListRecords", "metadataPrefix": prefix}
            if set_spec:
                params["set"] = set_spec
        root = _request(endpoint, params, timeout)
        records = root.findall("oai:ListRecords/oai:record", NS)
        next_node = root.find("oai:ListRecords/oai:resumptionToken", NS)
        next_token = (next_node.text or "").strip() if next_node is not None else ""
        batch = []
        for record in records:
            mapped = _map_record(record, endpoint, repository, obtained, prefix)
            if mapped:
                batch.append(mapped)
        if batch:
            checkpoint.parent.mkdir(parents=True, exist_ok=True)
            with checkpoint.open("a", encoding="utf-8") as out:
                for row in batch:
                    out.write(json.dumps(row, ensure_ascii=False) + "\n")
        accepted += len(batch)
        # Guarda token únicamente después de persistir la página: una caída puede
        # repetir la última página, pero la salida final deduplica OAI identifiers.
        _atomic_json(state, {"resumption_token": next_token, "endpoint": endpoint,
                             "metadata_prefix": prefix, "updated_at": datetime.now(timezone.utc).isoformat()})
        print(f"Página procesada; {accepted} registros con título y resumen guardados.")
        if max_records and accepted >= max_records:
            print("Límite de muestra alcanzado; checkpoint guardado para reanudar.")
            break
        if not next_token:
            break
        token = next_token
        if pause > 0:
            time.sleep(pause)

    rows = []
    if checkpoint.exists():
        seen = set()
        for line in checkpoint.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            key = row.get("oai_identifier") or row.get("url") or row.get("titulo", "").casefold()
            if key and key not in seen:
                rows.append(row)
                seen.add(key)
    if not rows:
        raise ValueError("No se encontraron registros con título y resumen; revisa el formato oai_dc y el repositorio.")
    salida.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(salida, index=False, encoding="utf-8-sig")
    print(f"CSV actualizado: {salida} ({len(rows)} registros)")
    return salida


def main():
    parser = argparse.ArgumentParser(description="Cosecha solo metadatos públicos por OAI-PMH; excluye registros sin resumen.")
    parser.add_argument("--endpoint", required=True, help="URL base OAI-PMH, p. ej. https://repositorio.ejemplo.edu/oai/request")
    parser.add_argument("--repositorio", required=True, help="Nombre institucional para la procedencia")
    parser.add_argument("--formato", default="oai_dc", help="metadataPrefix anunciado por ListMetadataFormats")
    parser.add_argument("--set", dest="set_spec", default="", help="setSpec opcional anunciado por el repositorio")
    parser.add_argument("--salida", default="datos/catalogo_oai.csv")
    parser.add_argument("--max-registros", type=int, default=0, help="Límite de muestra; 0 cosecha todo")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--pausa", type=float, default=0.2, help="Segundos entre páginas")
    parser.add_argument("--reiniciar", action="store_true", help="No reanuda el token guardado; usa otro nombre de salida o elimina manualmente checkpoints previos")
    args = parser.parse_args()
    cosechar(args.endpoint, args.salida, args.repositorio, args.formato, args.set_spec,
             args.max_registros, args.timeout, args.pausa, resume=not args.reiniciar)


if __name__ == "__main__":
    main()
