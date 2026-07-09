from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional

from ..config import defaults
from ..utils import ensure_defaults, parse_iso_datetime, parse_number
from .base import Parser
from .efd_icms_ipi import _classificacao_por_cfop, _operacao


def _strip_namespace(elem: ET.Element) -> None:
    if "}" in elem.tag:
        elem.tag = elem.tag.split("}", 1)[1]
    for child in list(elem):
        _strip_namespace(child)


class NfeXmlParser(Parser):
    name = "nfe_xml"

    def applicable(self, content: bytes) -> bool:
        snippet = content[:200].decode("latin-1", errors="ignore")
        return "<NFe" in snippet or "<nfeProc" in snippet

    def parse(self, path: Path, content: bytes) -> List[dict]:
        tree = ET.fromstring(content)
        _strip_namespace(tree)

        inf_nfe = tree.find("infNFe")
        if inf_nfe is None:
            inf_nfe = tree.find(".//infNFe")
        if inf_nfe is None:
            return []

        ide = inf_nfe.find("ide")
        emit = inf_nfe.find("emit")
        dest = inf_nfe.find("dest")

        chave_acesso = (inf_nfe.attrib.get("Id") or "").replace("NFe", "")
        tp_nf = ide.findtext("tpNF") if ide is not None else None
        num_doc = ide.findtext("nNF") if ide is not None else None
        dh_emi = ide.findtext("dhEmi") if ide is not None else None
        if not dh_emi and ide is not None:
            dh_emi = ide.findtext("dEmi")

        crt = emit.findtext("CRT") if emit is not None else None
        modelo = ide.findtext("mod") if ide is not None else None
        serie = ide.findtext("serie") if ide is not None else None
        id_dest = ide.findtext("idDest") if ide is not None else None
        ind_final = ide.findtext("indFinal") if ide is not None else None
        ind_pres = ide.findtext("indPres") if ide is not None else None
        mod_frete = ide.findtext("modFrete") if ide is not None else None
        status = tree.findtext(".//cStat")
        tp_emis = ide.findtext("tpEmis") if ide is not None else None

        emit_cnpj = emit.findtext("CNPJ") if emit is not None else None
        emit_cpf = emit.findtext("CPF") if emit is not None else None
        dest_cnpj = dest.findtext("CNPJ") if dest is not None else None
        dest_cpf = dest.findtext("CPF") if dest is not None else None

        uf_emit = emit.findtext("enderEmit/UF") if emit is not None else None
        uf_dest = dest.findtext("enderDest/UF") if dest is not None else None

        data_mov = parse_iso_datetime(dh_emi or "", defaults.timezone)
        regime = self._map_regime(crt)

        items: List[dict] = []
        for det in inf_nfe.findall("det"):
            num_item = det.attrib.get("nItem")
            prod = det.find("prod")
            imposto = det.find("imposto")

            cfop = prod.findtext("CFOP") if prod is not None else None
            cod_item = prod.findtext("cProd") if prod is not None else None
            descricao = prod.findtext("xProd") if prod is not None else None
            ncm = prod.findtext("NCM") if prod is not None else None
            value = parse_number(prod.findtext("vProd") if prod is not None else None) or 0.0

            icms_values = self._extract_icms(imposto)
            pis_values = self._extract_tax(imposto, "PIS")
            cofins_values = self._extract_tax(imposto, "COFINS")
            ipi_values = self._extract_tax(imposto, "IPI")
            icms_dest = self._extract_icms_uf_dest(imposto)
            cclasstrib = self._extract_cclasstrib(imposto)

            operation = _operacao("0" if tp_nf == "0" else "1", cfop)
            if operation == "Entrada":
                cnpj_participante = emit_cnpj or emit_cpf
            else:
                cnpj_participante = dest_cnpj or dest_cpf

            chassi = None
            veic_prod = prod.find("veicProd") if prod is not None else None
            if veic_prod is not None:
                chassi = veic_prod.findtext("chassi")

            item = {
                "OPERATION": operation,
                "CLASSIFICATION": _classificacao_por_cfop(cfop),
                "NCM": ncm or None,
                "DESCRIPTION": descricao or None,
                "VALUE": value,
                "PIS": pis_values.get("total", 0.0),
                "COFINS": cofins_values.get("total", 0.0),
                "IPI": ipi_values.get("total", 0.0),
                "ISS": 0.0,
                "ICMS": icms_values.get("vICMS", 0.0),
                "Origem": icms_values.get("origem"),
                "NBS": None,
                "Data_Mov": data_mov,
                "Pis_Mono": pis_values.get("monofasico", False),
                "Cofins_Mono": cofins_values.get("monofasico", False),
                "ICMS_Antec": 0.0,
                "ICMS_ST": icms_values.get("vICMSST", 0.0),
                "ICMS_DIFAL": icms_dest.get("vICMSUFDest", 0.0),
                "ICMS_RET": 0.0,
                "Outros_tributos": icms_dest.get("vFCPUFDest", 0.0),
                "Cod_Item": cod_item,
                "NUM_DOC": num_doc,
                "NUM_ITEM": num_item,
                "CFOP": cfop,
                "cclasstrib": cclasstrib,
                "cclasstrib_source": "xml-nfe" if cclasstrib else "none",
                "RegimeGeral": regime,
                "chave_acesso": chave_acesso or None,
                "modelo": modelo,
                "serie": serie,
                "status": status,
                "tpEmis": tp_emis,
                "idDest": id_dest,
                "indFinal": ind_final,
                "indPres": ind_pres,
                "modFrete": mod_frete,
                "UF_emit": uf_emit,
                "UF_dest": uf_dest,
                "CNPJ_PARTICIPANTE": cnpj_participante,
                "source_format": "NFE_XML_DET",
                "source_file": path.name,
                "source_locator": f"det[{num_item}]",
                "variavel_1": chassi,
            }
            items.append(ensure_defaults(item))

        return items

    @staticmethod
    def _extract_icms(imposto: Optional[ET.Element]) -> Dict[str, Optional[float]]:
        result: Dict[str, Optional[float]] = {"vICMS": 0.0, "vICMSST": 0.0, "origem": None}
        if imposto is None:
            return result
        icms = imposto.find("ICMS")
        if icms is None:
            return result
        for regime in list(icms):
            origem = regime.findtext("orig")
            if origem and origem.isdigit():
                result["origem"] = int(origem)
            result["vICMS"] += parse_number(regime.findtext("vICMS")) or 0.0
            result["vICMSST"] += parse_number(regime.findtext("vICMSST")) or 0.0
        return result

    @staticmethod
    def _extract_tax(imposto: Optional[ET.Element], tag: str) -> Dict[str, Optional[float]]:
        result = {"total": 0.0, "monofasico": False}
        if imposto is None:
            return result
        node = imposto.find(tag)
        if node is None:
            return result
        for child in list(node):
            value = parse_number(child.findtext(f"v{tag}"))
            if value:
                result["total"] += value
            cst = child.findtext("CST")
            if cst in {"04", "05", "06", "07"}:
                result["monofasico"] = True
        return result

    @staticmethod
    def _extract_icms_uf_dest(imposto: Optional[ET.Element]) -> Dict[str, float]:
        result = {"vICMSUFDest": 0.0, "vFCPUFDest": 0.0}
        if imposto is None:
            return result
        uf_dest = imposto.find("ICMSUFDest")
        if uf_dest is None:
            return result
        result["vICMSUFDest"] = parse_number(uf_dest.findtext("vICMSUFDest")) or 0.0
        result["vFCPUFDest"] = parse_number(uf_dest.findtext("vFCPUFDest")) or 0.0
        return result

    @staticmethod
    def _extract_cclasstrib(imposto: Optional[ET.Element]) -> Optional[str]:
        if imposto is None:
            return None
        for child in list(imposto):
            found = child.findtext("cClassTrib")
            if found:
                return found
        return None

    @staticmethod
    def _map_regime(crt: Optional[str]) -> Optional[str]:
        if crt == "1":
            return "SN"
        if crt == "2":
            return "SN-Excesso"
        if crt == "3":
            return "Regime Normal"
        return "Desconhecido"
