from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional

from ..utils import ensure_defaults, parse_iso_datetime, parse_number
from .base import Parser
from .nfe_xml import _strip_namespace


class NfseXmlParser(Parser):
    name = "nfse_xml"

    def applicable(self, content: bytes) -> bool:
        snippet = content[:400].decode("latin-1", errors="ignore")
        return "<CompNfse" in snippet or "<Nfse" in snippet

    def parse(self, path: Path, content: bytes) -> List[dict]:
        root = ET.fromstring(content)
        _strip_namespace(root)

        data_mov = self._first_text(root, ["DataEmissao", "Competencia"])
        data_mov_iso = parse_iso_datetime(data_mov or "", "America/Fortaleza")

        iss = parse_number(self._first_text(root, ["ValorIss"])) or 0.0
        nbs = self._first_text(root, ["CodigoNBS", "CodigoServico", "Servico/Codigo"])
        descricao = self._first_text(root, ["Servico/Discriminacao"])
        num_doc = self._first_text(root, ["Numero"])
        cnpj_prestador = self._first_text(root, ["Prestador/IdentificacaoPrestador/Cnpj", "Prestador/Endereco/Cnpj"])
        cnpj_tomador = self._first_text(root, ["Tomador/IdentificacaoTomador/CpfCnpj/Cnpj", "Tomador/IdentificacaoTomador/CpfCnpj/Cpf"])

        item = {
            "OPERATION": "Desconhecido",
            "CLASSIFICATION": "Serviço",
            "NCM": None,
            "DESCRIPTION": descricao,
            "VALUE": iss,
            "PIS": 0.0,
            "COFINS": 0.0,
            "IPI": 0.0,
            "ISS": iss,
            "ICMS": 0.0,
            "Origem": None,
            "NBS": nbs,
            "Data_Mov": data_mov_iso,
            "Pis_Mono": False,
            "Cofins_Mono": False,
            "ICMS_Antec": 0.0,
            "ICMS_ST": 0.0,
            "ICMS_DIFAL": 0.0,
            "ICMS_RET": 0.0,
            "Outros_tributos": 0.0,
            "Cod_Item": None,
            "NUM_DOC": num_doc,
            "NUM_ITEM": None,
            "CFOP": None,
            "cclasstrib": None,
            "cclasstrib_source": "none",
            "RegimeGeral": "Desconhecido",
            "CNPJ_PARTICIPANTE": cnpj_tomador or cnpj_prestador,
            "source_format": "NFSE_XML",
            "source_file": path.name,
            "source_locator": "root",
            "variavel_1": None,
        }

        return [ensure_defaults(item)]

    @staticmethod
    def _first_text(root: ET.Element, paths: List[str]) -> Optional[str]:
        for path in paths:
            node = root.find(f".//{path}")
            if node is not None and node.text:
                return node.text.strip()
        return None

