"""Motor de métricas canônicas do IPRO."""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Iterable, List

import numpy as np
import pandas as pd

from services.models import CustomerAnalytics, ProductAnalytics


class MetricsCalculator:
    def __init__(self, delay_logistico: int = 20):
        self.reference_date = datetime.utcnow()
        self.delay_logistico = delay_logistico

    # ------------------------------------------------------------------
    # Clientes
    # ------------------------------------------------------------------
    def calculate_customer_rfm(self, transactions: Iterable[Dict], dataset_id: str) -> List[CustomerAnalytics]:
        df = pd.DataFrame(list(transactions))
        if df.empty:
            return []

        df['date'] = pd.to_datetime(df['date'])
        df['subtotal'] = pd.to_numeric(df['subtotal'], errors='coerce').fillna(0.0)

        resultados: List[Dict] = []
        for client, grupo in df.groupby('client'):
            grupo = grupo.sort_values('date')
            recency = int((self.reference_date - grupo['date'].max()).days)
            frequency = int(grupo['order_id'].nunique())
            monetary = float(grupo['subtotal'].sum())
            avg_ticket = monetary / frequency if frequency > 0 else 0.0
            turnover_median = self._median_turnover(grupo['date'])

            segment = self._mode_or_none(grupo.get('segment'))
            city = self._mode_or_none(grupo.get('city'))
            uf = self._mode_or_none(grupo.get('uf'))

            resultados.append(
                {
                    'dataset_id': dataset_id,
                    'client': client,
                    'recency': recency,
                    'frequency': frequency,
                    'monetary': monetary,
                    'avg_ticket': avg_ticket,
                    'gm_cliente': turnover_median,
                    'tier': 'bronze',  # placeholder, ajustado após normalização
                    'segment': segment,
                    'city': city,
                    'uf': uf,
                    'last_order': grupo['date'].max(),
                }
            )

        if not resultados:
            return []

        resultados_df = pd.DataFrame(resultados)
        weights = self._segment_weights(df)
        resultados_df['segment_weight'] = resultados_df['client'].map(weights).fillna(1.0)

        resultados_df['recency_pct'] = 1 - resultados_df['recency'].rank(pct=True, method='average')
        resultados_df['frequency_pct'] = resultados_df['frequency'].rank(pct=True, method='average')
        resultados_df['monetary_pct'] = resultados_df['monetary'].rank(pct=True, method='average')

        resultados_df['rfm_score'] = (
            0.4 * resultados_df['recency_pct']
            + 0.3 * resultados_df['frequency_pct']
            + 0.3 * resultados_df['monetary_pct']
        ) * resultados_df['segment_weight']

        resultados_df['tier'] = resultados_df['rfm_score'].apply(self._tier_from_score)

        registros = resultados_df.drop(columns=['recency_pct', 'frequency_pct', 'monetary_pct']).to_dict('records')
        return [CustomerAnalytics(**r) for r in registros]

    # ------------------------------------------------------------------
    # Produtos
    # ------------------------------------------------------------------
    def calculate_product_analytics(self, transactions: Iterable[Dict], dataset_id: str) -> List[ProductAnalytics]:
        df = pd.DataFrame(list(transactions))
        if df.empty:
            return []

        df['date'] = pd.to_datetime(df['date'])
        df['qty'] = pd.to_numeric(df['qty'], errors='coerce').fillna(0)
        df['subtotal'] = pd.to_numeric(df['subtotal'], errors='coerce').fillna(0.0)

        revenue_per_sku = df.groupby('sku')['subtotal'].sum()
        hero_threshold = revenue_per_sku.quantile(0.8) if not revenue_per_sku.empty else 0.0

        mensal = df.groupby(['sku', df['date'].dt.to_period('M')])['subtotal'].sum()

        resultados: List[ProductAnalytics] = []
        for sku, grupo in df.groupby('sku'):
            grupo = grupo.sort_values('date')
            orders = int(grupo['order_id'].nunique())
            qty = int(grupo['qty'].sum())
            revenue = float(grupo['subtotal'].sum())
            avg_ticket = revenue / orders if orders else 0.0
            turnover_median = self._median_turnover(grupo['date'])

            serie_mensal = mensal.loc[sku] if sku in mensal.index.get_level_values(0) else None
            growth_z = 0.0
            growth_yoy = 0.0
            if serie_mensal is not None:
                serie_mensal = serie_mensal.sort_index()
                valores = serie_mensal.values.astype(float)
                if valores.size >= 3:
                    media = valores[:-1].mean()
                    desvio = valores[:-1].std() or 1.0
                    growth_z = (valores[-1] - media) / desvio
                if valores.size >= 13:
                    base = valores[-13]
                    growth_yoy = ((valores[-1] - base) / max(1.0, base)) * 100

            produto = grupo.iloc[0].get('product') or sku
            resultados.append(
                ProductAnalytics(
                    dataset_id=dataset_id,
                    sku=sku,
                    product=produto,
                    orders=orders,
                    qty=qty,
                    revenue=Decimal(str(revenue)),
                    avg_ticket=Decimal(str(avg_ticket)) if orders else None,
                    turnover_median=turnover_median,
                    hero_mix=bool(revenue >= hero_threshold),
                    growth_zscore=float(growth_z),
                    growth_yoy=float(growth_yoy),
                )
            )

        return resultados

    # ------------------------------------------------------------------
    # KPIs gerais
    # ------------------------------------------------------------------
    def calculate_general_kpis(self, transactions: Iterable[Dict]) -> Dict[str, float]:
        df = pd.DataFrame(list(transactions))
        if df.empty:
            return {
                'total_revenue': 0.0,
                'total_customers': 0,
                'total_products': 0,
                'total_orders': 0,
                'avg_ticket': 0.0,
                'avg_recency': 0.0,
                'avg_frequency': 0.0,
                'ruptura_projetada_media': 0.0,
            }

        df['date'] = pd.to_datetime(df['date'])
        df['subtotal'] = pd.to_numeric(df['subtotal'], errors='coerce').fillna(0.0)

        total_revenue = float(df['subtotal'].sum())
        total_customers = int(df['client'].nunique())
        total_products = int(df['sku'].nunique())
        total_orders = int(df['order_id'].nunique())
        avg_ticket = total_revenue / total_orders if total_orders else 0.0

        customer_group = df.groupby('client')['date']
        recencies = (self.reference_date - customer_group.max()).dt.days
        frequencies = df.groupby('client')['order_id'].nunique()

        avg_recency = float(recencies.mean()) if not recencies.empty else 0.0
        avg_frequency = float(frequencies.mean()) if not frequencies.empty else 0.0

        rupturas = []
        for client, dates in customer_group:
            dates = dates.sort_values()
            giro = self._median_turnover(dates)
            ultimo = dates.max()
            projetada = ultimo + timedelta(days=giro + self.delay_logistico)
            rupturas.append((projetada - self.reference_date).days)

        ruptura_media = float(np.mean(rupturas)) if rupturas else 0.0

        periodo_inicio = df['date'].min()
        periodo_fim = df['date'].max()

        return {
            'total_revenue': total_revenue,
            'total_customers': total_customers,
            'total_products': total_products,
            'total_orders': total_orders,
            'avg_ticket': avg_ticket,
            'avg_recency': avg_recency,
            'avg_frequency': avg_frequency,
            'period_start': periodo_inicio.isoformat() if pd.notna(periodo_inicio) else None,
            'period_end': periodo_fim.isoformat() if pd.notna(periodo_fim) else None,
            'period_days': int((periodo_fim - periodo_inicio).days) if pd.notna(periodo_fim) and pd.notna(periodo_inicio) else 0,
            'ruptura_projetada_media': ruptura_media,
        }

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------
    @staticmethod
    def _mode_or_none(series: pd.Series | None):
        if series is None or series.dropna().empty:
            return None
        return series.dropna().mode().iloc[0]

    @staticmethod
    def _median_turnover(dates: pd.Series) -> float:
        dates = pd.to_datetime(dates).sort_values()
        if dates.size < 2:
            return 0.0
        diffs = dates.diff().dropna().dt.days
        if diffs.empty:
            return 0.0
        return float(diffs.median())

    def _segment_weights(self, df: pd.DataFrame) -> Dict[str, float]:
        if 'segment' not in df.columns:
            return {}
        tot = df.groupby('segment')['subtotal'].sum().dropna()
        if tot.empty:
            return {}
        total = tot.sum()
        pesos = 0.5 + (tot / total) * 0.5
        mapa = df[['client', 'segment']].drop_duplicates().set_index('client')['segment']
        return mapa.map(pesos).fillna(1.0).to_dict()

    @staticmethod
    def _tier_from_score(score: float) -> str:
        if score >= 0.85:
            return 'hero'
        if score >= 0.65:
            return 'growth'
        if score >= 0.45:
            return 'manter'
        return 'risco'
