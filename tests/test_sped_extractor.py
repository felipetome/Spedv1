from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import pytest

from sped_extractor import config
from sped_extractor import main


SAMPLE_FILES = [
    "tests/samples/efd_icms_ipi.txt",
    "tests/samples/efd_contrib.txt",
    "tests/samples/nfe_saida_icms00.xml",
    "tests/samples/nfe_difal.xml",
    "tests/samples/nfse.xml",
]


@pytest.fixture(autouse=True)
def prepare_environment():
    entradas = Path("entradas")
    if entradas.exists():
        for child in entradas.iterdir():
            if child.is_file():
                child.unlink()
    else:
        entradas.mkdir(parents=True, exist_ok=True)

    saidas = Path("saidas")
    saidas.mkdir(parents=True, exist_ok=True)
    def clear_outputs():
        for output in [
            config.paths.output_json,
            config.paths.output_csv,
            config.paths.output_docs_json,
            config.paths.quality_json,
            config.paths.log_file,
        ]:
            if output.exists():
                output.unlink()
        for pattern in [
            "itens_sped_*.json",
            "itens_sped_*.csv",
            "documentos_sped_*.json",
            "relatorio_qualidade_*.json",
        ]:
            for generated in saidas.glob(pattern):
                generated.unlink()

    clear_outputs()

    speds = Path("speds")
    backup_dir = Path(".pytest_speds_backup")
    moved_files: list[tuple[Path, Path]] = []
    if speds.exists():
        backup_dir.mkdir(parents=True, exist_ok=True)
        for child in speds.iterdir():
            if child.is_file():
                dest = backup_dir / child.name
                if dest.exists():
                    dest.unlink()
                child.rename(dest)
                moved_files.append((child, dest))

    for sample in SAMPLE_FILES:
        dest = entradas / Path(sample).name
        shutil.copy(sample, dest)

    yield

    # Cleanup outputs produced by the test
    clear_outputs()
    for original, backup in moved_files:
        if backup.exists():
            backup.rename(original)
    if backup_dir.exists():
        try:
            backup_dir.rmdir()
        except OSError:
            pass


def load_output() -> list[dict]:
    with config.paths.output_json.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_csv() -> list[list[str]]:
    with config.paths.output_csv.open("r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        return list(reader)


def load_docs() -> list[dict]:
    with config.paths.output_docs_json.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_pipeline_generates_expected_items():
    items = main.run()
    assert config.paths.output_json.exists(), "Arquivo JSON de saída não foi criado."
    assert len(items) == 5

    # Carregar do arquivo para confirmar persistência
    stored_items = load_output()
    assert len(stored_items) == 5

    # Documentos
    assert config.paths.output_docs_json.exists(), "Arquivo JSON de documentos não foi criado."
    docs = load_docs()
    assert len(docs) == len({item["NUM_DOC"] for item in stored_items})

    # Validar campos mínimos
    for item in stored_items:
        assert item["NUM_DOC"] is not None
        assert item["VALUE"] >= 0
        assert item["OPERATION"] in {"Entrada", "Saida", "Desconhecido"}
        assert item["Data_Mov"] is None or isinstance(item["Data_Mov"], str)

    # Verificar flags monofásicos (CST 04/05)
    pis_mono_items = [item for item in stored_items if item["Pis_Mono"]]
    assert pis_mono_items, "Nenhum item marcado como monofásico para PIS."

    cofins_mono_items = [item for item in stored_items if item["Cofins_Mono"]]
    assert cofins_mono_items, "Nenhum item marcado como monofásico para COFINS."

    # Regimes
    nfe_regime_normal = next(item for item in stored_items if item["NUM_DOC"] == "98765")
    assert nfe_regime_normal["RegimeGeral"] == "Regime Normal"

    nfe_regime_sn = next(item for item in stored_items if item["NUM_DOC"] == "99999")
    assert nfe_regime_sn["RegimeGeral"] == "SN"

    # ICMS DIFAL e FCP
    assert nfe_regime_sn["ICMS_DIFAL"] == pytest.approx(3.75, rel=1e-3)
    assert nfe_regime_sn["Outros_tributos"] == pytest.approx(1.25, rel=1e-3)

    # NFSe
    nfse = next(item for item in stored_items if item["CLASSIFICATION"] == "Serviço")
    assert nfse["ISS"] == pytest.approx(500.0)
    assert nfse["NBS"] == "1.05"

    # Quality report
    assert config.paths.quality_json.exists(), "Relatório de qualidade não foi gerado."
    with config.paths.quality_json.open("r", encoding="utf-8") as f:
        metrics = json.load(f)
    assert metrics["possui_nfse"] is True
    for key in (
        "pct_itens_com_NCM",
        "pct_itens_com_PIS_COFINS",
        "pct_itens_com_ICMS_ST",
        "pct_itens_com_DIFAL",
        "pct_itens_com_chave_acesso",
        "pct_itens_com_origem",
        "pct_documentos_cancelados_ignorados",
        "duplicidade_por_chave_acesso",
    ):
        assert key in metrics

    # CSV export
    assert config.paths.output_csv.exists(), "Arquivo CSV de saída não foi criado."
    csv_rows = load_csv()
    assert csv_rows[0] == main.CSV_HEADERS
    assert len(csv_rows) == len(stored_items) + 1
    header_index = {name: idx for idx, name in enumerate(main.CSV_HEADERS)}
    primeira_linha = csv_rows[1]
    assert primeira_linha[header_index["NUM_DOC"]] == "12345"
    assert primeira_linha[header_index["VALUE"]] != ""

