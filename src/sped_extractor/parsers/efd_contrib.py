from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from ..config import defaults
from ..utils import ensure_defaults, parse_number, parse_sped_date
from .base import Parser
from .efd_icms_ipi import _classificacao_por_cfop, _operacao, _split_pipe


@dataclass
class C100Contrib:
    ind_oper: Optional[str]
    cod_part: Optional[str]
    num_doc: Optional[str]
    dt_doc: Optional[str]
    dt_e_s: Optional[str]
    modelo: Optional[str]
    serie: Optional[str]
    chave: Optional[str]


class EfdContribParser(Parser):
    name = "efd_contrib"

    def applicable(self, content: bytes) -> bool:
        raw = content
        return b"|M100|" in raw or b"|M200|" in raw or (b"|C100|" in raw and b"|C170|" in raw)

    def parse(self, path: Path, content: bytes) -> List[dict]:
        lines = self.read_lines(content)
        current_doc: Optional[C100Contrib] = None
        participants: dict[str, dict[str, Optional[str]]] = {}
        items: List[dict] = []

        for line_number, raw_line in enumerate(lines, start=1):
            if "|C" not in raw_line:
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

            if reg == "C100":
                ind_oper = parts[1] if len(parts) > 1 else None
                cod_part = parts[3] if len(parts) > 3 else None
                modelo = parts[4] if len(parts) > 4 else None
                serie = parts[6] if len(parts) > 6 else None
                num_doc = parts[7] if len(parts) > 7 else None
                chave = parts[8] if len(parts) > 8 else None
                num_doc = parts[7] if len(parts) > 7 else None
                dt_doc = parts[9] if len(parts) > 9 else None
                dt_e_s = parts[10] if len(parts) > 10 else None
                current_doc = C100Contrib(ind_oper, cod_part, num_doc, dt_doc, dt_e_s, modelo, serie, chave)
                continue

            if reg == "C170" and current_doc:
                cfop = parts[10] if len(parts) > 10 else None
                data_mov = (
                    parse_sped_date(current_doc.dt_e_s or "", defaults.timezone)
                    or parse_sped_date(current_doc.dt_doc or "", defaults.timezone)
                )
                cst_pis = parts[24] if len(parts) > 24 else None
                cst_cofins = parts[30] if len(parts) > 30 else None
                participant = participants.get(current_doc.cod_part or "", {})
                cnpj_participante = participant.get("cnpj") or participant.get("cpf")
                item = {
                    "OPERATION": _operacao(current_doc.ind_oper, cfop),
                    "CLASSIFICATION": _classificacao_por_cfop(cfop),
                    "NCM": None,
                    "DESCRIPTION": None,
                    "VALUE": parse_number(parts[6] if len(parts) > 6 else None) or 0.0,
                    "PIS": parse_number(parts[29] if len(parts) > 29 else None) or 0.0,
                    "COFINS": parse_number(parts[35] if len(parts) > 35 else None) or 0.0,
                    "IPI": 0.0,
                    "ISS": 0.0,
                    "ICMS": 0.0,
                    "Origem": None,
                    "NBS": None,
                    "Data_Mov": data_mov,
                    "Pis_Mono": cst_pis in {"04", "05", "06", "07"},
                    "Cofins_Mono": cst_cofins in {"04", "05", "06", "07"},
                    "ICMS_Antec": 0.0,
                    "ICMS_ST": 0.0,
                    "ICMS_DIFAL": 0.0,
                    "ICMS_RET": 0.0,
                    "Outros_tributos": 0.0,
                    "Cod_Item": parts[2] if len(parts) > 2 else None,
                    "NUM_DOC": current_doc.num_doc,
                    "NUM_ITEM": parts[1] if len(parts) > 1 else None,
                    "CFOP": cfop,
                    "cclasstrib": None,
                    "cclasstrib_source": "none",
                    "RegimeGeral": "Desconhecido",
                    "chave_acesso": current_doc.chave,
                    "modelo": current_doc.modelo,
                    "serie": current_doc.serie,
                    "CNPJ_PARTICIPANTE": cnpj_participante,
                    "source_format": "EFD_CONTRIB_C170",
                    "source_file": path.name,
                    "source_locator": f"line {line_number}",
                    "variavel_1": None,
                }
                items.append(ensure_defaults(item))

        return items

