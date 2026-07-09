from __future__ import annotations

import csv
import json
import logging
import math
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, List, Tuple

from glob import glob
from zoneinfo import ZoneInfo

from .config import defaults, paths, quality_report
from .consolidator import Consolidator
from .parsers import EfdContribParser, EfdIcmsIpiParser, NfeXmlParser, NfseXmlParser
from .quality import compute_quality
from .utils import configure_logging, ensure_defaults, round_decimal

LOGGER = logging.getLogger(__name__)

CSV_HEADERS = [
    "OPERATION",
    "CLASSIFICATION",
    "NCM",
    "DESCRIPTION",
    "VALUE",
    "PIS",
    "COFINS",
    "IPI",
    "ISS",
    "ICMS",
    "Origem",
    "NBS",
    "Data Mov",
    "Pis Mono",
    "Cofins Mono",
    "ICMS Antec",
    "ICMS ST",
    "ICMS DIFAL",
    "ICMS RET",
    "Outros_tributos",
    "Cod_Item",
    "NUM_DOC",
    "NUM_ITEM",
    "CFOP",
    "cclasstrib",
    "RegimeGeral",
    "CNPJ Participante",
    "variavel_1(chassi)",
]


def _load_file(path: Path) -> bytes:
    with path.open("rb") as f:
        return f.read()


def _normalise_item(item: dict, decimals: int) -> dict:
    normalised = dict(item)
    for key, value in list(normalised.items()):
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            normalised[key] = round_decimal(value, decimals)
    return ensure_defaults(normalised)


def _format_decimal(value) -> str:
    if value is None:
        return ""
    try:
        dec = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return ""
    quantized = dec.quantize(Decimal("0.01"))
    integer_part, _, frac_part = f"{quantized:.2f}".partition(".")
    integer_part = f"{int(integer_part):,}".replace(",", ".")
    return f"{integer_part},{frac_part}"


def _format_bool(value) -> str:
    if value in (True, "true", "True", 1, "1"):
        return "Sim"
    if value in (False, "false", "False", 0, "0"):
        return "Não"
    return ""


def _format_date(value: Optional[str]) -> str:
    if not value:
        return ""
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return value


def _format_operation(value: Optional[str]) -> str:
    mapping = {"Entrada": "Entradas", "Saida": "Saídas"}
    return mapping.get(value, value or "")


def _write_json(path: Path, data) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _csv_row(item: dict) -> List[str]:
    origem_label = item.get("source_format") or item.get("Origem")
    if origem_label is None:
        origem_label = ""

    return [
        _format_operation(item.get("OPERATION")),
        item.get("CLASSIFICATION") or "",
        item.get("NCM") or "",
        item.get("DESCRIPTION") or "",
        _format_decimal(item.get("VALUE")),
        _format_decimal(item.get("PIS")),
        _format_decimal(item.get("COFINS")),
        _format_decimal(item.get("IPI")),
        _format_decimal(item.get("ISS")),
        _format_decimal(item.get("ICMS")),
        str(origem_label) if origem_label is not None else "",
        item.get("NBS") or "",
        _format_date(item.get("Data_Mov")),
        _format_bool(item.get("Pis_Mono")),
        _format_bool(item.get("Cofins_Mono")),
        _format_decimal(item.get("ICMS_Antec")),
        _format_decimal(item.get("ICMS_ST")),
        _format_decimal(item.get("ICMS_DIFAL")),
        _format_decimal(item.get("ICMS_RET")),
        _format_decimal(item.get("Outros_tributos")),
        item.get("Cod_Item") or "",
        item.get("NUM_DOC") or "",
        item.get("NUM_ITEM") or "",
        item.get("CFOP") or "",
        item.get("cclasstrib") or "",
        item.get("RegimeGeral") or "",
        (item.get("CNPJ_PARTICIPANTE") or ""),
        item.get("variavel_1") or "",
    ]


def _write_csv(path: Path, items: List[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as csvfile:
        writer = csv.writer(csvfile, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(CSV_HEADERS)
        for item in items:
            writer.writerow(_csv_row(item))


def _build_documents(items: List[dict]) -> List[dict]:
    documents: Dict[Tuple[str, str], dict] = {}
    for item in items:
        num_doc = item.get("NUM_DOC")
        if not num_doc:
            continue
        chave = item.get("chave_acesso")
        key = (chave or "", str(num_doc))
        if key not in documents:
            documents[key] = {
                "chave_acesso": chave,
                "NUM_DOC": num_doc,
                "OPERATION": item.get("OPERATION"),
                "RegimeGeral": item.get("RegimeGeral"),
                "idDest": item.get("idDest"),
                "indFinal": item.get("indFinal"),
                "indPres": item.get("indPres"),
                "UF_emit": item.get("UF_emit"),
                "UF_dest": item.get("UF_dest"),
                "modelo": item.get("modelo"),
                "serie": item.get("serie"),
                "status": item.get("status"),
                "tpEmis": item.get("tpEmis"),
                "valor_total": 0.0,
                "itens": 0,
            }
        documents[key]["valor_total"] += item.get("VALUE", 0) or 0.0
        documents[key]["itens"] += 1
    return list(documents.values())


def _collect_files() -> List[Path]:
    files: List[Path] = []
    seen = set()
    for pattern in paths.input_patterns:
        for match in glob(pattern, recursive=True):
            path = Path(match)
            if path.is_file() and path not in seen:
                seen.add(path)
                files.append(path)
    return files


def _timestamp_suffix() -> str:
    tz = ZoneInfo(defaults.timezone)
    return datetime.now(tz).strftime("%Y%m%d_%H%M%S")


def run() -> List[dict]:
    configure_logging(str(paths.log_file))
    LOGGER.info("Iniciando processamento de arquivos SPED nos padrões %s", paths.input_patterns)

    output_dir = paths.output_json.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    consolidator = Consolidator()
    possui_nfse = False
    ignored_documents = 0

    parsers = [
        EfdIcmsIpiParser(),
        EfdContribParser(),
        NfeXmlParser(),
        NfseXmlParser(),
    ]

    all_files = _collect_files()
    processed_items: List[dict] = []

    for file_path in all_files:
        if file_path.is_dir():
            continue
        raw = _load_file(file_path)
        parser = next((p for p in parsers if p.applicable(raw)), None)
        if parser is None:
            LOGGER.warning("Nenhum parser compatível para %s", file_path)
            continue
        LOGGER.info("Processando %s com parser %s", file_path.name, parser.__class__.__name__)
        items = parser.parse(file_path, raw)
        consolidator.ingest(items)
        processed_items.extend(items)
        if isinstance(parser, NfseXmlParser) and items:
            possui_nfse = True

    consolidated = consolidator.to_list()
    decimals = 2
    consolidated = [_normalise_item(item, decimals) for item in consolidated]
    documents = _build_documents(consolidated)

    suffix = _timestamp_suffix()

    _write_json(paths.output_json, consolidated)
    timestamped_json = paths.output_json.with_name(f"{paths.output_json.stem}_{suffix}{paths.output_json.suffix}")
    _write_json(timestamped_json, consolidated)

    _write_csv(paths.output_csv, consolidated)
    timestamped_csv = paths.output_csv.with_name(f"{paths.output_csv.stem}_{suffix}{paths.output_csv.suffix}")
    _write_csv(timestamped_csv, consolidated)

    _write_json(paths.output_docs_json, documents)
    timestamped_docs = paths.output_docs_json.with_name(
        f"{paths.output_docs_json.stem}_{suffix}{paths.output_docs_json.suffix}"
    )
    _write_json(timestamped_docs, documents)

    if quality_report.enabled:
        metrics = compute_quality(consolidated, documentos=documents, possui_nfse=possui_nfse, ignored_documents=ignored_documents)
        _write_json(paths.quality_json, metrics)
        timestamped_quality = paths.quality_json.with_name(
            f"{paths.quality_json.stem}_{suffix}{paths.quality_json.suffix}"
        )
        _write_json(timestamped_quality, metrics)

    LOGGER.info("Processamento concluído. %s itens consolidados.", len(consolidated))
    return consolidated


if __name__ == "__main__":
    run()

