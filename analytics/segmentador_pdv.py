"""Segmentação vetorial de PDVs para priorização comercial."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

import pandas as pd


@dataclass
class SegmentoPDV:
    client: str
    score: float
    justificativa: str
    gatilhos: List[str]


class SegmentadorPDV:
    """Construir vetores de comportamento e pontuar PDVs."""

    def __init__(self, peso_mix: float = 0.35, peso_volume: float = 0.35, peso_frequencia: float = 0.30):
        self.peso_mix = peso_mix
        self.peso_volume = peso_volume
        self.peso_frequencia = peso_frequencia

    @staticmethod
    def _preparar_dataframe(transacoes: Iterable[Dict]) -> pd.DataFrame:
        df = pd.DataFrame(list(transacoes))
        if df.empty:
            return df
        df['date'] = pd.to_datetime(df['date'])
        df['qty'] = pd.to_numeric(df.get('qty'), errors='coerce').fillna(0)
        df['subtotal'] = pd.to_numeric(df.get('subtotal'), errors='coerce').fillna(0.0)
        return df

    def _vetor_cliente(self, dados_cliente: pd.DataFrame) -> Dict[str, float]:
        total_pedidos = dados_cliente['order_id'].nunique()
        dias = dados_cliente.sort_values('date')['date'].diff().dt.days.dropna()
        mix = dados_cliente['sku'].nunique()
        volume_total = float(dados_cliente['qty'].sum())

        giro = float(dias.median()) if not dias.empty else 0.0
        freq_mensal = total_pedidos / max(1, (dados_cliente['date'].max() - dados_cliente['date'].min()).days / 30 or 1)

        return {
            'mix': mix,
            'volume': volume_total,
            'freq': freq_mensal,
            'giro_mediano': giro,
        }

    def avaliar(self, transacoes: Iterable[Dict]) -> List[SegmentoPDV]:
        df = self._preparar_dataframe(transacoes)
        if df.empty:
            return []

        baseline = df.groupby('client').apply(self._vetor_cliente).apply(pd.Series)
        media_cluster = baseline.mean()
        mediana_mix = baseline['mix'].median()
        mediana_volume = baseline['volume'].median()

        segmentos: List[SegmentoPDV] = []
        for client, vetor in baseline.iterrows():
            normal_mix = vetor['mix'] / max(1, media_cluster['mix'])
            normal_volume = vetor['volume'] / max(1.0, media_cluster['volume'])
            normal_freq = vetor['freq'] / max(1.0, media_cluster['freq'])

            score = (
                normal_mix * self.peso_mix
                + normal_volume * self.peso_volume
                + normal_freq * self.peso_frequencia
            )

            gatilhos = []
            if vetor['mix'] < mediana_mix:
                gatilhos.append("mix abaixo do cluster")
            if vetor['volume'] < mediana_volume * 0.5:
                gatilhos.append("ausência anômala de SKU esperado")
            if vetor['giro_mediano'] > media_cluster['giro_mediano'] * 1.5:
                gatilhos.append("giro lento em relação ao cluster")

            justificativa = (
                f"Mix {vetor['mix']} SKUs, volume {vetor['volume']:.0f} itens, "
                f"freq. {vetor['freq']:.2f}/mês"
            )

            segmentos.append(
                SegmentoPDV(
                    client=client,
                    score=round(float(score), 4),
                    justificativa=justificativa,
                    gatilhos=gatilhos,
                )
            )

        segmentos.sort(key=lambda s: s.score, reverse=True)
        return segmentos


__all__ = ["SegmentadorPDV", "SegmentoPDV"]
