"""Utilidades para gerar o Excel final do IPRO."""

from __future__ import annotations

import os
import tempfile
from decimal import Decimal
from typing import Any, Dict, List, Optional

import pandas as pd

from analytics.metrics import MetricsCalculator

REPORT_SHEETS = {
    "clients": "Identificação do Cliente",
    "history": "Histórico Comercial",
    "mix": "Inteligência de Mix",
    "relationship": "Relacional e Atendimento",
    "behavior": "Inteligência Comportamental",
}


def convert_transactions_to_records(transactions: List[Any]) -> List[Dict[str, Any]]:
    """Converter objetos Transaction (ou dicionários compatíveis) em dicts serializáveis."""
    records: List[Dict[str, Any]] = []
    for tx in transactions:
        if hasattr(tx, "dict"):
            data = tx.dict()
        elif isinstance(tx, dict):
            data = tx.copy()
        else:
            data = dict(tx)

        for field in ("price", "subtotal"):
            value = data.get(field)
            if isinstance(value, Decimal):
                data[field] = float(value)
        records.append(data)
    return records


def build_report_dataframes(
    transactions: List[Dict[str, Any]],
    dataset_id: str,
    calculator: Optional[MetricsCalculator] = None,
) -> Dict[str, pd.DataFrame]:
    """Gerar DataFrames para as cinco abas padrão do IPRO."""

    if not transactions:
        raise ValueError("Nenhuma transação normalizada disponível para gerar relatórios")

    calc = calculator or MetricsCalculator()
    tx_df = pd.DataFrame(transactions)
    if tx_df.empty:
        raise ValueError("DataFrame de transações está vazio")

    tx_df['date'] = pd.to_datetime(tx_df['date'])
    tx_df['subtotal'] = pd.to_numeric(tx_df['subtotal'], errors='coerce').fillna(0.0)
    tx_df['qty'] = pd.to_numeric(tx_df.get('qty'), errors='coerce').fillna(0)
    tx_df['order_id'] = tx_df.get('order_id').astype(str)

    customer_analytics = calc.calculate_customer_rfm(transactions, dataset_id)
    product_analytics = calc.calculate_product_analytics(transactions, dataset_id)
    general_kpis = calc.calculate_general_kpis(transactions)

    clientes_df = pd.DataFrame([c.dict() for c in customer_analytics]) if customer_analytics else pd.DataFrame(
        columns=[
            'dataset_id', 'client', 'recency', 'frequency', 'monetary', 'avg_ticket',
            'gm_cliente', 'tier', 'segment', 'city', 'uf', 'last_order', 'rfm_score',
            'segment_weight'
        ]
    )

    historico_df = (
        tx_df.assign(periodo=tx_df['date'].dt.to_period('M').dt.to_timestamp())
        .groupby('periodo')
        .agg(
            receita_total=('subtotal', 'sum'),
            pedidos=('order_id', 'nunique'),
            clientes=('client', 'nunique'),
            volume=('qty', 'sum'),
        )
        .reset_index()
    )
    historico_df['ticket_medio'] = historico_df.apply(
        lambda row: row['receita_total'] / row['pedidos'] if row['pedidos'] else 0.0,
        axis=1
    )

    mix_df = pd.DataFrame([p.dict() for p in product_analytics]) if product_analytics else pd.DataFrame(
        columns=['dataset_id', 'sku', 'product', 'orders', 'qty', 'revenue', 'avg_ticket',
                 'turnover_median', 'hero_mix', 'growth_zscore', 'growth_yoy']
    )

    if not clientes_df.empty:
        relacional_df = clientes_df[
            ['client', 'segment', 'city', 'uf', 'gm_cliente', 'recency', 'frequency', 'last_order']
        ].copy()
        relacional_df['last_order'] = pd.to_datetime(relacional_df['last_order'], errors='coerce')
        relacional_df['janela_prevista_dias'] = relacional_df['gm_cliente'].fillna(0) + calc.delay_logistico
        relacional_df['proxima_janela'] = relacional_df['last_order'] + pd.to_timedelta(
            relacional_df['janela_prevista_dias'], unit='D'
        )
    else:
        relacional_df = pd.DataFrame(
            columns=['client', 'segment', 'city', 'uf', 'gm_cliente', 'recency', 'frequency',
                     'last_order', 'janela_prevista_dias', 'proxima_janela']
        )

    behavior_rows = [
        {'indicador': 'Total de clientes', 'valor': general_kpis.get('total_customers', 0)},
        {'indicador': 'Total de SKUs', 'valor': general_kpis.get('total_products', 0)},
        {'indicador': 'Total de pedidos', 'valor': general_kpis.get('total_orders', 0)},
        {'indicador': 'Ticket médio', 'valor': round(general_kpis.get('avg_ticket', 0.0), 2)},
        {'indicador': 'Ruptura projetada média (dias)', 'valor': round(general_kpis.get('ruptura_projetada_media', 0.0), 2)},
    ]

    if not clientes_df.empty:
        tier_counts = clientes_df['tier'].value_counts()
        for tier, count in tier_counts.items():
            behavior_rows.append({'indicador': f'Clientes {tier}', 'valor': int(count)})

    comportamental_df = pd.DataFrame(behavior_rows)

    return {
        REPORT_SHEETS['clients']: clientes_df,
        REPORT_SHEETS['history']: historico_df,
        REPORT_SHEETS['mix']: mix_df,
        REPORT_SHEETS['relationship']: relacional_df,
        REPORT_SHEETS['behavior']: comportamental_df,
    }


def write_report_excel(dataframes: Dict[str, pd.DataFrame], engine: str = 'xlsxwriter') -> str:
    """Persistir DataFrames em um arquivo temporário do Excel."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    tmp_path = tmp.name
    tmp.close()

    def _write(path: str, selected_engine: str):
        def _strip_tz(df: pd.DataFrame) -> pd.DataFrame:
            df = df.copy()
            for col in df.columns:
                if pd.api.types.is_datetime64tz_dtype(df[col]):
                    df[col] = df[col].dt.tz_localize(None)
            return df

        with pd.ExcelWriter(path, engine=selected_engine) as writer:
            for sheet_name, df in dataframes.items():
                clean_df = _strip_tz(df)
                clean_df.to_excel(writer, sheet_name=sheet_name[:31], index=False)

    try:
        _write(tmp_path, engine)
    except ValueError:
        # Fallback para openpyxl caso xlsxwriter não esteja disponível no ambiente
        _write(tmp_path, 'openpyxl')

    return tmp_path


def safe_remove(path: str):
    try:
        os.unlink(path)
    except FileNotFoundError:
        return
