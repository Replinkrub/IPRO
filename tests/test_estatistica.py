from datetime import datetime

import pandas as pd
import pytest

from analytics.estatistica import (
    calcular_probabilidade_recompra,
    intervalo_confianca_giro,
    detectar_outlier_volume,
    calcular_cv_giro,
    score_sobrevivencia_bayesiana,
)


def test_calcular_probabilidade_recompra():
    datas = [
        datetime(2024, 1, 1),
        datetime(2024, 1, 15),
        datetime(2024, 2, 10),
        datetime(2024, 3, 5),
    ]
    prob = calcular_probabilidade_recompra(datas, janela_dias=40)
    assert prob == 1.0


def test_intervalo_confianca_giro():
    serie = [10, 12, 14, 16, 18]
    low, high = intervalo_confianca_giro(serie, confianca=0.8)
    assert low == pytest.approx(10.8, rel=1e-3)
    assert high == pytest.approx(17.2, rel=1e-3)


def test_detectar_outlier_volume_flags_high_values():
    serie = pd.Series([10, 11, 12, 100, 11, 9])
    mask = detectar_outlier_volume(serie, z_limite=2.0)
    assert mask.sum() == 1
    assert mask[mask].index[0] == 3


def test_calcular_cv_giro_handles_zero_mean():
    assert calcular_cv_giro([0, 0, 0]) == 0.0
    assert round(calcular_cv_giro([10, 12, 14]), 3) == 0.136


def test_score_sobrevivencia_bayesiana():
    eventos = [1, 0, 1, 1, 0, 1]
    score = score_sobrevivencia_bayesiana(eventos, alfa=1, beta=1)
    assert round(score, 2) == 0.62
