from __future__ import annotations

from typing import Dict, Iterable, List


def compute_quality(
    items: Iterable[dict],
    documentos: Iterable[dict],
    possui_nfse: bool,
    ignored_documents: int = 0,
) -> Dict[str, float | bool]:
    items_list = list(items)
    total = len(items_list) or 1

    metrics: Dict[str, float | bool] = {}
    metrics["pct_itens_com_NCM"] = sum(1 for item in items_list if item.get("NCM")) / total
    metrics["pct_itens_com_PIS_COFINS"] = (
        sum(1 for item in items_list if (item.get("PIS", 0) > 0 or item.get("COFINS", 0) > 0)) / total
    )
    metrics["pct_itens_com_ICMS_ST"] = sum(1 for item in items_list if item.get("ICMS_ST", 0) > 0) / total
    metrics["pct_itens_com_DIFAL"] = sum(1 for item in items_list if item.get("ICMS_DIFAL", 0) > 0) / total
    metrics["pct_itens_com_chave_acesso"] = sum(1 for item in items_list if item.get("chave_acesso")) / total
    metrics["pct_itens_com_origem"] = sum(1 for item in items_list if item.get("Origem") is not None) / total

    documentos_list = list(documentos)
    total_docs = len(documentos_list)
    total_docs_base = total_docs + ignored_documents
    if total_docs_base == 0:
        metrics["pct_documentos_cancelados_ignorados"] = 0.0
    else:
        metrics["pct_documentos_cancelados_ignorados"] = ignored_documents / total_docs_base

    chaves = [item.get("chave_acesso") for item in items_list if item.get("chave_acesso")]
    duplicates = len(chaves) - len(set(chaves))
    metrics["duplicidade_por_chave_acesso"] = duplicates

    metrics["possui_nfse"] = possui_nfse
    return metrics

