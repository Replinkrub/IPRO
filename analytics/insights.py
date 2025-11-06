"""Geração de insights R.I.C.O. com enriquecimento estatístico."""
from __future__ import annotations

from datetime import datetime
from typing import Iterable, List

import numpy as np
import pandas as pd

from analytics.estatistica import (
    calcular_cv_giro,
    calcular_probabilidade_recompra,
    detectar_outlier_volume,
    intervalo_confianca_giro,
    score_sobrevivencia_bayesiana,
)
from analytics.segmentador_pdv import SegmentadorPDV
from services.models import Alert


class InsightsGenerator:
    """Gerar alertas padronizados do framework R.I.C.O."""

    def __init__(self, delay_logistico: int = 20):
        self.reference_date = datetime.utcnow()
        self.delay_logistico = delay_logistico
        self.segmentador = SegmentadorPDV()

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def generate_rico_insights(self, transactions: Iterable[Dict], dataset_id: str) -> List[Alert]:
        df = pd.DataFrame(list(transactions))
        if df.empty:
            return []

        df['date'] = pd.to_datetime(df['date'])
        df['qty'] = pd.to_numeric(df['qty'], errors='coerce').fillna(0)
        df['subtotal'] = pd.to_numeric(df['subtotal'], errors='coerce').fillna(0.0)

        segmentos = {seg.client: seg for seg in self.segmentador.avaliar(df.to_dict('records'))}

        alerts: List[Alert] = []
        alerts.extend(self._ruptura_alerts(df, dataset_id, segmentos))
        alerts.extend(self._queda_brusca_alerts(df, dataset_id, segmentos))
        alerts.extend(self._outlier_volume_alerts(df, dataset_id, segmentos))
        return alerts

    # ------------------------------------------------------------------
    # Regras de negócio
    # ------------------------------------------------------------------
    def _ruptura_alerts(self, df: pd.DataFrame, dataset_id: str, segmentos) -> List[Alert]:
        resultados: List[Alert] = []
        for (client, sku), group in df.groupby(['client', 'sku']):
            if group.shape[0] < 2:
                continue

            datas = group.sort_values('date')['date'].tolist()
            prob_recompra = calcular_probabilidade_recompra(datas, janela_dias=90)
            intervalos = [
                (datas[i] - datas[i - 1]).days
                for i in range(1, len(datas))
            ]
            if not intervalos:
                continue

            giro_mediano = float(np.median(intervalos))
            previsao = giro_mediano + self.delay_logistico
            dias_sem_compra = (self.reference_date - datas[-1]).days
            confianca = min(1.0, dias_sem_compra / max(1.0, previsao))
            reliability = self._score_para_reliability(confianca)

            ic_low, ic_high = intervalo_confianca_giro(intervalos)
            insight = (
                f"Cliente {client} sem comprar {sku} há {dias_sem_compra} dias. "
                f"Giro mediano {giro_mediano:.1f}d (IC {ic_low:.0f}-{ic_high:.0f}) e prob. recompra {prob_recompra*100:.0f}%."
            )
            gatilhos = segmentos.get(client)
            action = "Contatar cliente e reservar estoque para reposição imediata."
            if gatilhos and gatilhos.gatilhos:
                action += " Triggers: " + ", ".join(gatilhos.gatilhos)

            resultados.append(
                Alert(
                    dataset_id=dataset_id,
                    client=client,
                    sku=sku,
                    type="ruptura",
                    insight=insight,
                    action=action,
                    reliability=reliability,
                    suggested_deadline="3 dias",
                )
            )
        return resultados

    def _queda_brusca_alerts(self, df: pd.DataFrame, dataset_id: str, segmentos) -> List[Alert]:
        resultados: List[Alert] = []
        df['mes'] = df['date'].dt.to_period('M')
        mensal = df.groupby(['client', 'mes'])['subtotal'].sum().reset_index()

        for client, grupo in mensal.groupby('client'):
            if grupo.shape[0] < 3:
                continue

            grupo = grupo.sort_values('mes')
            valores = grupo['subtotal'].values.astype(float)
            media = valores[:-1].mean()
            desvio = valores[:-1].std() or 1.0
            ultimo = valores[-1]
            z_score = (ultimo - media) / desvio
            yoy = 0.0
            if grupo.shape[0] >= 13:
                yoy = ((ultimo - valores[-13]) / max(1.0, valores[-13])) * 100

            if ultimo < media and z_score <= -1.5:
                score = min(1.0, abs(z_score) / 3)
                reliability = self._score_para_reliability(score)
                insight = (
                    f"Receita de {client} caiu {((media - ultimo) / max(1.0, media))*100:.1f}% vs média. "
                    f"Z-score {z_score:.2f}, YoY {yoy:.1f}%"
                )
                gatilhos = segmentos.get(client)
                action = "Planejar ação de recuperação com ofertas direcionadas e revisão de cobertura."
                if gatilhos and gatilhos.gatilhos:
                    action += " Verificar também: " + ", ".join(gatilhos.gatilhos)

                resultados.append(
                    Alert(
                        dataset_id=dataset_id,
                        client=client,
                        sku=None,
                        type="queda_brusca",
                        insight=insight,
                        action=action,
                        reliability=reliability,
                        suggested_deadline="1 semana",
                    )
                )
        return resultados

    def _outlier_volume_alerts(self, df: pd.DataFrame, dataset_id: str, segmentos) -> List[Alert]:
        resultados: List[Alert] = []
        for (client, sku), group in df.groupby(['client', 'sku']):
            if group.shape[0] < 5:
                continue

            serie = group.sort_values('date').set_index('date')['qty']
            mask = detectar_outlier_volume(serie)
            if mask.empty or not mask.any():
                continue

            idx = mask[mask].index[-1]
            valor = float(serie.loc[idx])
            media = float(serie.mean())
            direcao = "acima" if valor > media else "abaixo"
            delta = abs(valor - media) / max(1.0, media)
            reliability = self._score_para_reliability(min(1.0, delta))
            cv = calcular_cv_giro(serie.diff().dropna())
            survival = score_sobrevivencia_bayesiana([q > 0 for q in serie.tail(6)])

            insight = (
                f"Volume {direcao} da média para {sku} (último {valor:.0f} vs média {media:.0f}). "
                f"CV giro {cv:.2f}, score sobrevivência {survival:.2f}."
            )
            gatilhos = segmentos.get(client)
            action = "Validar estoque e alinhar com time de operações/atendimento."
            if gatilhos and gatilhos.gatilhos:
                action += " Contexto: " + ", ".join(gatilhos.gatilhos)

            resultados.append(
                Alert(
                    dataset_id=dataset_id,
                    client=client,
                    sku=sku,
                    type="outlier_volume",
                    insight=insight,
                    action=action,
                    reliability=reliability,
                    suggested_deadline="48 horas",
                )
            )
        return resultados

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    @staticmethod
    def _score_para_reliability(score: float) -> str:
        if score >= 0.75:
            return "🔴"
        if score >= 0.4:
            return "🟡"
        return "🔵"

