"""
Application configuration and constants extracted from the product requirements.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Sequence


@dataclass(frozen=True)
class PathsConfig:
    input_patterns: Sequence[str] = (
        "./entradas/**/*.txt",
        "./entradas/**/*.TXT",
        "./entradas/**/*.xml",
        "./entradas/**/*.XML",
        "./speds/**/*.txt",
        "./speds/**/*.TXT",
        "./speds/**/*.xml",
        "./speds/**/*.XML",
    )
    output_json: Path = Path("./saidas/itens_sped.json")
    output_docs_json: Path = Path("./saidas/documentos_sped.json")
    output_csv: Path = Path("./saidas/itens_sped.csv")
    quality_json: Path = Path("./saidas/relatorio_qualidade.json")
    log_file: Path = Path("./saidas/exec.log")


@dataclass(frozen=True)
class EncodingConfig:
    preferred: Sequence[str] = ("utf-8", "iso-8859-1")


@dataclass(frozen=True)
class InputOptionsConfig:
    ignore_nfe_cancelled: bool = True
    ignore_nfe_inutilized: bool = True
    max_file_mb: int = 250


@dataclass(frozen=True)
class XmlDetectionConfig:
    nfe_roots: Sequence[str] = ("NFe", "procNFe")
    nfse_roots: Sequence[str] = ("CompNfse", "Nfse", "InfNfse", "Servico")


@dataclass(frozen=True)
class TxtDetectionConfig:
    delimiter: str = "|"
    efd_icms_ipi_markers: Sequence[str] = (
        "|0000|",
        "|C100|",
        "|C170|",
        "|0200|",
        "|E110|",
        "|E210|",
        "|E310|",
    )
    efd_contrib_markers: Sequence[str] = (
        "|0000|",
        "|C100|",
        "|C170|",
        "|M100|",
        "|M200|",
    )


@dataclass(frozen=True)
class DefaultsConfig:
    numeric_zero_if_missing: Sequence[str] = (
        "PIS",
        "COFINS",
        "IPI",
        "ISS",
        "ICMS",
        "ICMS_Antec",
        "ICMS_ST",
        "ICMS_DIFAL",
        "ICMS_RET",
        "Outros_tributos",
    )
    null_if_missing: Sequence[str] = (
        "NCM",
        "DESCRIPTION",
        "NBS",
        "Cod_Item",
        "NUM_DOC",
        "NUM_ITEM",
        "CFOP",
        "cclasstrib",
        "cclasstrib_source",
        "RegimeGeral",
    )
    date_field: str = "Data_Mov"
    date_format_out: str = "%Y-%m-%d"
    timezone: str = "America/Fortaleza"


@dataclass(frozen=True)
class ConsolidationConfig:
    grain: str = "item"
    join_keys: Sequence[str] = (
        "NUM_DOC",
        "NUM_ITEM",
        "CFOP",
        "Cod_Item",
        "Data_Mov",
    )
    precedence: Sequence[str] = ("item_level_values", "document_totals_prorated_by_VALUE")
    fill_rules: Dict[str, str] = field(
        default_factory=lambda: {
            "iss_nbs": "ISS/NBS só vêm de NFS-e; se não houver NFS-e, manter null"
        }
    )
    decimals: int = 2


@dataclass(frozen=True)
class QualityMetric:
    name: str
    rule: str


@dataclass(frozen=True)
class QualityReportConfig:
    enabled: bool = True
    metrics: Sequence[QualityMetric] = (
        QualityMetric("pct_itens_com_NCM", "count(NCM not null) / total"),
        QualityMetric("pct_itens_com_PIS_COFINS", "count(PIS>0 or COFINS>0) / total"),
        QualityMetric("pct_itens_com_ICMS_ST", "count(ICMS_ST>0) / total"),
        QualityMetric("pct_itens_com_DIFAL", "count(ICMS_DIFAL>0) / total"),
        QualityMetric("possui_nfse", "true se pelo menos um arquivo NFS-e foi processado"),
    )


paths = PathsConfig()
encodings = EncodingConfig()
inputs = InputOptionsConfig()
xml_detection = XmlDetectionConfig()
txt_detection = TxtDetectionConfig()
defaults = DefaultsConfig()
consolidation = ConsolidationConfig()
quality_report = QualityReportConfig()

