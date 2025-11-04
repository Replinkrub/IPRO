import numpy as np
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
import logging

from services.models import CustomerAnalytics, ProductAnalytics, KPIResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetricsCalculator:
    """Calculadora de métricas e KPIs"""
    
    def __init__(self):
        self.reference_date = datetime.now()
    
    def calculate_customer_rfm(self, transactions: List[Dict[str, Any]], dataset_id: str) -> List[CustomerAnalytics]:
        """Calcular RFM (Recency, Frequency, Monetary) por cliente"""
        try:
            # Converter para DataFrame e garantir colunas adicionais
            df = pd.DataFrame(transactions)
            # Converter datas para datetime
            df['date'] = pd.to_datetime(df['date'])
            # Garantir colunas segment, city, uf existam
            for col in ['segment','city','uf']:
                if col not in df.columns:
                    df[col] = None
            
            # Agrupar por cliente
            customer_metrics = []
            
            for client in df['client'].unique():
                client_data = df[df['client'] == client]
                
                # Recency: dias desde a última compra
                last_purchase = client_data['date'].max()
                recency = (self.reference_date - last_purchase).days if pd.notna(last_purchase) else -1 # Usar -1 ou outro valor para indicar que não há compras
                
                # Frequency: número de pedidos únicos
                frequency = client_data['order_id'].nunique()
                
                # Monetary: valor total gasto
                monetary = float(client_data['subtotal'].sum())

                # Ticket médio
                avg_ticket = monetary / frequency if frequency > 0 else 0.0

                # Giro médio do cliente
                gm_cliente = float(self._calculate_customer_turnover(client_data))

                # Tier do cliente
                tier = self._classify_customer_tier(recency, frequency, monetary)

                # Segmento, cidade e UF (pegar o valor mais frequente se houver mais de um)
                seg = None
                city = None
                uf = None
                if 'segment' in client_data.columns and client_data['segment'].notna().any():
                    seg = client_data['segment'].dropna().mode().iloc[0]
                if 'city' in client_data.columns and client_data['city'].notna().any():
                    city = client_data['city'].dropna().mode().iloc[0]
                if 'uf' in client_data.columns and client_data['uf'].notna().any():
                    uf = client_data['uf'].dropna().mode().iloc[0]

                customer_analytics = CustomerAnalytics(
                    dataset_id=dataset_id,
                    client=client,
                    recency=recency,
                    frequency=frequency,
                    monetary=monetary,
                    avg_ticket=avg_ticket,
                    gm_cliente=gm_cliente,
                    tier=tier,
                    segment=seg,
                    city=city,
                    uf=uf
                )
                
                customer_metrics.append(customer_analytics)
            
            logger.info(f"Calculado RFM para {len(customer_metrics)} clientes")
            return customer_metrics
            
        except Exception as e:
            logger.error(f"Erro no cálculo de RFM: {e}")
            return []
    
    def calculate_product_analytics(self, transactions: List[Dict[str, Any]], dataset_id: UUID) -> List[ProductAnalytics]:
        """Calcular analytics de produtos"""
        try:
            df = pd.DataFrame(transactions)
            df['date'] = pd.to_datetime(df['date'])
            
            product_metrics = []
            
            for sku in df['sku'].unique():
                product_data = df[df['sku'] == sku]
                
                # Giro médio do SKU global
                gm_sku = self._calculate_product_turnover(product_data)
                
                # Giro médio do SKU na base
                gm_sku_base = gm_sku  # Para simplificar, usar o mesmo valor
                
                # Giro médio por cluster (usar segmento como proxy)
                gm_cluster = self._calculate_cluster_turnover(product_data)
                
                # Coeficiente de variação do giro
                cv_giro = self._calculate_turnover_cv(product_data)
                
                # Adoção do produto
                adocao = self._calculate_product_adoption(product_data, df)
                
                product_analytics = ProductAnalytics(
                    dataset_id=dataset_id,
                    sku=sku,
                    gm_sku=gm_sku,
                    gm_sku_base=gm_sku_base,
                    gm_cluster=gm_cluster,
                    cv_giro=cv_giro,
                    adocao=adocao
                )
                
                product_metrics.append(product_analytics)
            
            logger.info(f"Calculado analytics para {len(product_metrics)} produtos")
            return product_metrics
            
        except Exception as e:
            logger.error(f"Erro no cálculo de analytics de produtos: {e}")
            return []
    
    def calculate_general_kpis(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calcular KPIs gerais"""
        try:
            df = pd.DataFrame(transactions)
            df['date'] = pd.to_datetime(df['date'])
            
            # KPIs básicos
            total_revenue = df['subtotal'].sum()
            total_customers = df['client'].nunique()
            total_products = df['sku'].nunique()
            total_orders = df['order_id'].nunique()
            
            # Ticket médio
            avg_ticket = total_revenue / total_orders if total_orders > 0 else 0
            
            # Período
            period_start = df['date'].min()
            period_end = df['date'].max()
            
            # Métricas de recência e frequência
            customer_stats = df.groupby('client').agg({
                'date': ['max', 'count'],
                'subtotal': 'sum'
            }).reset_index()
            
            customer_stats.columns = ['client', 'last_purchase', 'frequency', 'monetary']
            customer_stats['recency'] = (self.reference_date - customer_stats['last_purchase']).dt.days
            
            avg_recency = customer_stats["recency"].mean() if not customer_stats.empty else 0
            avg_frequency = customer_stats["frequency"].mean() if not customer_stats.empty else 0
            
            # KPIs de margem (se houver dados de custo)
            margin_data = {}
            if 'cost' in df.columns and df['cost'].notna().any():
                total_cost = (df['cost'] * df['qty']).sum()
                gross_margin = total_revenue - total_cost
                margin_percentage = (gross_margin / total_revenue * 100) if total_revenue > 0 else 0
                
                margin_data = {
                    "total_cost": total_cost,
                    "gross_margin": gross_margin,
                    "margin_percentage": margin_percentage
                }
            
            # KPIs de giro
            turnover_data = self._calculate_global_turnover_metrics(df)
            
            kpis = {
                "total_revenue": total_revenue,
                "total_customers": total_customers,
                "total_products": total_products,
                "total_orders": total_orders,
                "avg_ticket": avg_ticket,
                "avg_recency": avg_recency,
                "avg_frequency": avg_frequency,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "period_days": (period_end - period_start).days,
                **margin_data,
                **turnover_data
            }
            
            return kpis
            
        except Exception as e:
            logger.error(f"Erro no cálculo de KPIs gerais: {e}")
            return {}
    
    def calculate_product_ranking(self, transactions: List[Dict[str, Any]], by: str = "receita") -> List[Dict[str, Any]]:
        """Calcular ranking de produtos"""
        try:
            df = pd.DataFrame(transactions)
            
            # Agrupar por produto
            product_stats = df.groupby(['sku', 'product']).agg({
                'subtotal': 'sum',
                'qty': 'sum',
                'order_id': 'nunique',
                'client': 'nunique'
            }).reset_index()
            
            product_stats.columns = ['sku', 'product', 'revenue', 'quantity', 'orders', 'customers']
            
            # Calcular métricas adicionais
            product_stats['avg_price'] = product_stats['revenue'] / product_stats['quantity']
            product_stats['penetration'] = product_stats['customers'] / df['client'].nunique() * 100
            
            # Ordenar por critério
            if by == "receita":
                product_stats = product_stats.sort_values('revenue', ascending=False)
            elif by == "frequencia":
                product_stats = product_stats.sort_values('orders', ascending=False)
            elif by == "giro":
                # Calcular giro para cada produto
                product_stats['turnover'] = product_stats.apply(
                    lambda row: self._calculate_product_turnover(
                        df[df['sku'] == row['sku']]
                    ), axis=1
                )
                product_stats = product_stats.sort_values('turnover', ascending=True)  # Menor giro = melhor
            
            return product_stats.head(20).to_dict('records')
            
        except Exception as e:
            logger.error(f"Erro no ranking de produtos: {e}")
            return []
    
    def _calculate_customer_turnover(self, client_data: pd.DataFrame) -> float:
        """Calcular giro médio do cliente (dias entre compras)"""
        try:
            if len(client_data) < 2:
                return 0.0
            
            # Ordenar por data
            dates = sorted(client_data['date'].unique())
            
            # Calcular intervalos entre compras
            intervals = []
            for i in range(1, len(dates)):
                interval = (dates[i] - dates[i-1]).days
                intervals.append(interval)
            
            # Retornar mediana (mais robusta que média)
            return np.median(intervals) if intervals else 0.0
            
        except Exception:
            return 0.0
    
    def _calculate_product_turnover(self, product_data: pd.DataFrame) -> float:
        """Calcular giro médio do produto"""
        try:
            if len(product_data) < 2:
                return 0.0
            
            # Agrupar por cliente para calcular intervalos
            client_intervals = []
            
            for client in product_data['client'].unique():
                client_product_data = product_data[product_data['client'] == client]
                if len(client_product_data) >= 2:
                    dates = sorted(client_product_data['date'].unique())
                    for i in range(1, len(dates)):
                        interval = (dates[i] - dates[i-1]).days
                        client_intervals.append(interval)
            
            return np.median(client_intervals) if client_intervals else 0.0
            
        except Exception:
            return 0.0
    
    def _calculate_cluster_turnover(self, product_data: pd.DataFrame) -> float:
        """Calcular giro médio por cluster"""
        try:
            # Usar segmento como proxy para cluster
            if 'segment' not in product_data.columns:
                return self._calculate_product_turnover(product_data)
            
            cluster_turnovers = []
            for segment in product_data['segment'].dropna().unique():
                segment_data = product_data[product_data['segment'] == segment]
                turnover = self._calculate_product_turnover(segment_data)
                if turnover > 0:
                    cluster_turnovers.append(turnover)
            
            return np.median(cluster_turnovers) if cluster_turnovers else 0.0
            
        except Exception:
            return 0.0
    
    def _calculate_turnover_cv(self, product_data: pd.DataFrame) -> float:
        """Calcular coeficiente de variação do giro"""
        try:
            # Calcular intervalos entre compras por cliente
            all_intervals = []
            
            for client in product_data['client'].unique():
                client_data = product_data[product_data['client'] == client]
                if len(client_data) >= 2:
                    dates = sorted(client_data['date'].unique())
                    for i in range(1, len(dates)):
                        interval = (dates[i] - dates[i-1]).days
                        all_intervals.append(interval)
            
            if len(all_intervals) < 2:
                return 0.0
            
            mean_interval = np.mean(all_intervals)
            std_interval = np.std(all_intervals)
            
            return std_interval / mean_interval if mean_interval > 0 else 0.0
            
        except Exception:
            return 0.0
    
    def _calculate_product_adoption(self, product_data: pd.DataFrame, all_data: pd.DataFrame) -> float:
        """Calcular taxa de adoção do produto"""
        try:
            # Clientes únicos que compraram o produto
            product_customers = product_data['client'].nunique()
            
            # Total de clientes na base
            total_customers = all_data['client'].nunique()
            
            return (product_customers / total_customers * 100) if total_customers > 0 else 0.0
            
        except Exception:
            return 0.0
    
    def _classify_customer_tier(self, recency: int, frequency: int, monetary: float) -> str:
        """Classificar tier do cliente baseado em RFM"""
        try:
            # Lógica simplificada de classificação
            if recency <= 30 and frequency >= 5 and monetary >= 1000:
                return "🔥 Top"
            elif recency <= 60 and frequency >= 3 and monetary >= 500:
                return "⚡ Expansão"
            elif recency <= 90 and frequency >= 2:
                return "🟡 Potencial"
            else:
                return "🔴 Baixa relevância"
                
        except Exception:
            return "🔴 Baixa relevância"
    
    def _calculate_global_turnover_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calcular métricas globais de giro"""
        try:
            # Giro médio global
            all_intervals = []
            
            for client in df['client'].unique():
                client_data = df[df['client'] == client]
                if len(client_data) >= 2:
                    dates = sorted(client_data['date'].unique())
                    for i in range(1, len(dates)):
                        interval = (dates[i] - dates[i-1]).days
                        all_intervals.append(interval)
            
            if not all_intervals:
                return {"global_turnover": 0, "turnover_std": 0, "turnover_cv": 0}
            
            global_turnover = np.median(all_intervals)
            turnover_std = np.std(all_intervals)
            turnover_cv = turnover_std / global_turnover if global_turnover > 0 else 0 # Usar mediana como base para CV
            
            return {
                "global_turnover": global_turnover,
                "turnover_std": turnover_std,
                "turnover_cv": turnover_cv
            }
            
        except Exception as e:
            logger.error(f"Erro no cálculo de métricas de giro: {e}")
            return {"global_turnover": 0, "turnover_std": 0, "turnover_cv": 0}

