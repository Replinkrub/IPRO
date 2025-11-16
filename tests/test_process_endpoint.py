from datetime import datetime, timedelta
import os

import pandas as pd

from analytics.metrics import MetricsCalculator
from services.report_builder import (
    REPORT_SHEETS,
    build_report_dataframes,
    write_report_excel,
)


def _sample_transactions():
    base = datetime(2024, 1, 1)
    return [
        {
            "dataset_id": "ds-test",
            "product": "Produto A",
            "date": base,
            "order_id": "1",
            "client": "Cliente A",
            "seller": "Rep 1",
            "price": 10.0,
            "qty": 2,
            "subtotal": 20.0,
            "sku": "SKU-A",
            "uf": "SP",
            "segment": "Premium",
            "city": "São Paulo",
        },
        {
            "dataset_id": "ds-test",
            "product": "Produto B",
            "date": base + timedelta(days=15),
            "order_id": "2",
            "client": "Cliente B",
            "seller": "Rep 1",
            "price": 15.0,
            "qty": 1,
            "subtotal": 15.0,
            "sku": "SKU-B",
            "uf": "RJ",
            "segment": "Mid",
            "city": "Rio de Janeiro",
        },
        {
            "dataset_id": "ds-test",
            "product": "Produto A",
            "date": base + timedelta(days=40),
            "order_id": "3",
            "client": "Cliente A",
            "seller": "Rep 2",
            "price": 9.5,
            "qty": 3,
            "subtotal": 28.5,
            "sku": "SKU-A",
            "uf": "SP",
            "segment": "Premium",
            "city": "São Paulo",
        },
    ]


def test_build_report_dataframes_creates_all_tabs():
    calculator = MetricsCalculator()
    frames = build_report_dataframes(
        _sample_transactions(), "ds-test", calculator=calculator
    )

    expected_tabs = set(REPORT_SHEETS.values())
    assert set(frames.keys()) == expected_tabs

    for name, df in frames.items():
        assert isinstance(df, pd.DataFrame)
        # cada aba deve conter pelo menos uma linha com os dados de exemplo
        assert not df.empty, f"A aba {name} deveria conter dados"


def test_write_report_excel_persists_every_sheet(tmp_path):
    calculator = MetricsCalculator()
    frames = build_report_dataframes(
        _sample_transactions(), "ds-test", calculator=calculator
    )

    path = write_report_excel(frames)
    try:
        assert os.path.exists(path)
        workbook = pd.ExcelFile(path)
        assert set(workbook.sheet_names) == set(frames.keys())
    finally:
        if os.path.exists(path):
            os.unlink(path)
