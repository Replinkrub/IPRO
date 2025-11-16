from datetime import datetime, timedelta

from analytics.metrics import MetricsCalculator


def _sample_transactions():
    base_date = datetime(2024, 1, 1)
    return [
        {
            "dataset_id": "d1",
            "product": "Produto A",
            "sku": "SKU-A",
            "date": base_date,
            "order_id": "1",
            "client": "Cliente 1",
            "qty": 10,
            "subtotal": 100.0,
            "segment": "Premium",
        },
        {
            "dataset_id": "d1",
            "product": "Produto A",
            "sku": "SKU-A",
            "date": base_date + timedelta(days=15),
            "order_id": "2",
            "client": "Cliente 1",
            "qty": 8,
            "subtotal": 90.0,
            "segment": "Premium",
        },
        {
            "dataset_id": "d1",
            "product": "Produto B",
            "sku": "SKU-B",
            "date": base_date + timedelta(days=30),
            "order_id": "3",
            "client": "Cliente 2",
            "qty": 5,
            "subtotal": 60.0,
            "segment": "Mid",
        },
        {
            "dataset_id": "d1",
            "product": "Produto B",
            "sku": "SKU-B",
            "date": base_date + timedelta(days=60),
            "order_id": "4",
            "client": "Cliente 2",
            "qty": 5,
            "subtotal": 70.0,
            "segment": "Mid",
        },
    ]


def test_customer_giro_uses_median():
    calc = MetricsCalculator(delay_logistico=20)
    customers = calc.calculate_customer_rfm(_sample_transactions(), "d1")
    cliente1 = next(c for c in customers if c.client == "Cliente 1")
    assert cliente1.gm_cliente == 15.0


def test_rfm_score_applies_segment_weight():
    calc = MetricsCalculator(delay_logistico=20)
    customers = calc.calculate_customer_rfm(_sample_transactions(), "d1")
    scores = {c.client: c.rfm_score for c in customers}
    assert scores["Cliente 1"] > scores["Cliente 2"]


def test_product_analytics_marks_hero_mix():
    calc = MetricsCalculator(delay_logistico=20)
    products = calc.calculate_product_analytics(_sample_transactions(), "d1")
    hero = next(p for p in products if p.sku == "SKU-A")
    challenger = next(p for p in products if p.sku == "SKU-B")
    assert hero.hero_mix is True
    assert challenger.hero_mix in {False, None}


def test_general_kpis_ruptura_projection():
    calc = MetricsCalculator(delay_logistico=20)
    kpis = calc.calculate_general_kpis(_sample_transactions())
    assert "ruptura_projetada_media" in kpis
    assert isinstance(kpis["ruptura_projetada_media"], float)
