from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from ..config import defaults
from ..utils import ensure_defaults, parse_number, parse_sped_date
from .base import Parser


@dataclass
class C100Record:
    ind_oper: Optional[str]
    cod_part: Optional[str]
    num_doc: Optional[str]
    dt_doc: Optional[str]
    dt_e_s: Optional[str]
    modelo: Optional[str]
    serie: Optional[str]
    cod_sit: Optional[str]
    chave: Optional[str]


def _split_pipe(line: str) -> List[str]:
    parts = line.strip().split("|")
    if parts and parts[0] == "":
        parts = parts[1:]
    if parts and parts[-1] == "":
        parts = parts[:-1]
    return parts


def _classificacao_por_cfop(cfop: Optional[str]) -> str:
    if not cfop:
        return "Desconhecido"
    inicio = cfop.strip()[:1]
    if inicio in {"1", "2", "3"}:
        return "Entrada"
    if inicio in {"5", "6", "7"}:
        return "Saida"
    return "Desconhecido"


def _operacao(ind_oper: Optional[str], cfop: Optional[str]) -> str:
    if ind_oper in {"0", "1"}:
        return "Entrada" if ind_oper == "0" else "Saida"
    return _classificacao_por_cfop(cfop)


class EfdIcmsIpiParser(Parser):
    name = "efd_icms_ipi"

    def applicable(self, content: bytes) -> bool:
        return b"|C100|" in content and b"|C170|" in content

    def parse(self, path: Path, content: bytes) -> List[dict]:
        lines = self.read_lines(content)
        cod_item_lookup: Dict[str, Dict[str, Optional[str]]] = {}
        participants: Dict[str, Dict[str, Optional[str]]] = {}
        current_doc: Optional[C100Record] = None
        items: List[dict] = []

        for line_number, raw_line in enumerate(lines, start=1):
            if "|C" not in raw_line and "|0200|" not in raw_line:
                continue
            parts = _split_pipe(raw_line)
            if not parts:
                continue
            reg = parts[0].upper()

            if reg == "0150":
                cod_part = parts[1] if len(parts) > 1 else None
                if not cod_part:
                    continue
                participants[cod_part] = {
                    "name": parts[2] if len(parts) > 2 else None,
                    "cnpj": parts[3] if len(parts) > 3 else None,
                    "cpf": parts[4] if len(parts) > 4 else None,
                }
                continue

            if reg == "0200":
                cod = parts[1] if len(parts) > 1 else None
                if not cod:
                    continue
                cod_item_lookup[cod] = {
                    "DESCRIPTION": parts[2] if len(parts) > 2 else None,
                    "NCM": parts[7] if len(parts) > 7 else None,
                }
                continue

            if reg == "C100":
                ind_oper = parts[1] if len(parts) > 1 else None
                cod_part = parts[3] if len(parts) > 3 else None
                modelo = parts[4] if len(parts) > 4 else None
                cod_sit = parts[5] if len(parts) > 5 else None
                serie = parts[6] if len(parts) > 6 else None
                num_doc = parts[7] if len(parts) > 7 else None
                chave = parts[8] if len(parts) > 8 else None
                dt_doc = parts[9] if len(parts) > 9 else None
                dt_e_s = parts[10] if len(parts) > 10 else None
                current_doc = C100Record(
                    ind_oper=ind_oper,
                    cod_part=cod_part,
                    num_doc=num_doc,
                    dt_doc=dt_doc,
                    dt_e_s=dt_e_s,
                    modelo=modelo,
                    serie=serie,
                    cod_sit=cod_sit,
                    chave=chave,
                )
                continue

            if reg == "C170" and current_doc:
                cfop = parts[10] if len(parts) > 10 else None
                cod_item = parts[2] if len(parts) > 2 else None
                lookup = cod_item_lookup.get(cod_item or "", {})
                ind_oper = current_doc.ind_oper
                data_mov = (
                    parse_sped_date(current_doc.dt_e_s or "", defaults.timezone)
                    or parse_sped_date(current_doc.dt_doc or "", defaults.timezone)
                )
                cst_icms = parts[9] if len(parts) > 9 else None
                origem = None
                if cst_icms and cst_icms[0].isdigit():
                    origem = int(cst_icms[0])

                participant = participants.get(current_doc.cod_part or "", {})
                cnpj_participante = participant.get("cnpj") or participant.get("cpf")

                item = {
                    "OPERATION": _operacao(ind_oper, cfop),
                    "CLASSIFICATION": _classificacao_por_cfop(cfop),
                    "NCM": lookup.get("NCM"),
                    "DESCRIPTION": lookup.get("DESCRIPTION"),
                    "VALUE": parse_number(parts[6] if len(parts) > 6 else None) or 0.0,
                    "PIS": parse_number(parts[29] if len(parts) > 29 else None) or 0.0,
                    "COFINS": parse_number(parts[35] if len(parts) > 35 else None) or 0.0,
                    "IPI": parse_number(parts[23] if len(parts) > 23 else None) or 0.0,
                    "ISS": 0.0,
                    "ICMS": parse_number(parts[14] if len(parts) > 14 else None) or 0.0,
                    "Origem": origem,
                    "NBS": None,
                    "Data_Mov": data_mov,
                    "Pis_Mono": (parts[24] if len(parts) > 24 else None) in {"04", "05", "06", "07"},
                    "Cofins_Mono": (parts[30] if len(parts) > 30 else None) in {"04", "05", "06", "07"},
                    "ICMS_Antec": 0.0,
                    "ICMS_ST": parse_number(parts[17] if len(parts) > 17 else None) or 0.0,
                    "ICMS_DIFAL": 0.0,
                    "ICMS_RET": 0.0,
                    "Outros_tributos": 0.0,
                    "Cod_Item": cod_item,
                    "NUM_DOC": current_doc.num_doc,
                    "NUM_ITEM": parts[1] if len(parts) > 1 else None,
                    "CFOP": cfop,
                    "cclasstrib": None,
                    "cclasstrib_source": "none",
                    "RegimeGeral": "Desconhecido",
                    "chave_acesso": current_doc.chave,
                    "modelo": current_doc.modelo,
                    "serie": current_doc.serie,
                    "status": current_doc.cod_sit,
                    "CNPJ_PARTICIPANTE": cnpj_participante,
                    "source_format": "EFD_ICMS_C170",
                    "source_file": path.name,
                    "source_locator": f"line {line_number}",
                    "variavel_1": None,
                }
                items.append(ensure_defaults(item))

        return items

