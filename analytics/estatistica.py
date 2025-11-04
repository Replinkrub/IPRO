"""Módulo estatístico com funções reutilizáveis pelo motor IPRO."""
from datetime import datetime
from typing import Iterable, Sequence, Tuple

import numpy as np
import pandas as pd


def _to_series(valores: Iterable[float | int]) -> pd.Series:
    """Converter sequência em ``Series`` numérica sem NaNs."""
    if isinstance(valores, pd.Series):
        serie = pd.to_numeric(valores, errors="coerce")
    else:
        serie = pd.to_numeric(pd.Series(list(valores)), errors="coerce")
    serie = serie.dropna()
    return serie.astype(float)


def calcular_probabilidade_recompra(datas_pedidos: Sequence[datetime], janela_dias: int = 90) -> float:
    """Calcular a probabilidade de um cliente recomprar em ``janela_dias``.

    A função considera o histórico de datas de pedido (ordenadas) e calcula a
    proporção de intervalos menores ou iguais à janela informada. Em outras
    palavras, mede a recorrência histórica do cliente.
    """
    if not datas_pedidos:
        return 0.0

    datas_ordenadas = sorted(d for d in datas_pedidos if d)
    if len(datas_ordenadas) < 2:
        return 0.0

    deltas = [
        (datas_ordenadas[i] - datas_ordenadas[i - 1]).days
        for i in range(1, len(datas_ordenadas))
        if datas_ordenadas[i] and datas_ordenadas[i - 1]
    ]
    if not deltas:
        return 0.0

    hits = sum(1 for d in deltas if d <= janela_dias)
    return round(hits / len(deltas), 4)


def intervalo_confianca_giro(intervalos_dias: Iterable[float | int], confianca: float = 0.95) -> Tuple[float, float]:
    """Retornar o intervalo de confiança do giro (mediana dos intervalos).

    Utiliza o método de percentis (aproximação não paramétrica) para obter os
    limites inferior e superior, garantindo robustez mesmo com distribuições
    assimétricas.
    """
    serie = _to_series(intervalos_dias)
    if serie.empty:
        return (0.0, 0.0)

    alpha = 1 - confianca
    lower = float(np.quantile(serie, alpha / 2))
    upper = float(np.quantile(serie, 1 - alpha / 2))
    return (lower, upper)


def detectar_outlier_volume(valores: Iterable[float | int], z_limite: float = 3.0) -> pd.Series:
    """Detectar volumes fora do padrão via Z-score.

    Retorna uma série booleana onde ``True`` indica observações outliers.
    """
    serie = _to_series(valores)
    if serie.empty:
        return pd.Series(dtype=bool)

    media = serie.mean()
    desvio = serie.std(ddof=0)
    if desvio == 0 or np.isnan(desvio):
        return pd.Series([False] * len(serie), index=serie.index)

    z_scores = (serie - media) / desvio
    return z_scores.abs() > z_limite


def calcular_cv_giro(intervalos_dias: Iterable[float | int]) -> float:
    """Coeficiente de variação do giro (desvio padrão / média)."""
    serie = _to_series(intervalos_dias)
    if serie.empty:
        return 0.0
    media = serie.mean()
    if media == 0:
        return 0.0
    return float(serie.std(ddof=0) / media)


def score_sobrevivencia_bayesiana(eventos: Sequence[int | bool], alfa: float = 1.0, beta: float = 1.0) -> float:
    """Pontuar probabilidade de *sobrevivência* usando um Beta posterior.

    ``eventos`` deve conter 1 para recompra/renovação e 0 para períodos sem
    recompra. O score resultante (0-1) representa a probabilidade esperada de o
    cliente permanecer ativo no próximo ciclo.
    """
    if not eventos:
        return 0.0

    sucessos = sum(1 for e in eventos if bool(e))
    total = len(eventos)
    return round((sucessos + alfa) / (total + alfa + beta), 4)


__all__ = [
    "calcular_probabilidade_recompra",
    "intervalo_confianca_giro",
    "detectar_outlier_volume",
    "calcular_cv_giro",
    "score_sobrevivencia_bayesiana",
]
