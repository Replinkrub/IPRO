import numpy as np
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
import logging
import os

from services.models import Alert

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InsightsGenerator:
    """Gerador de insights R.I.C.O. (Ruptura, Inatividade, Crescimento, Oportunidade)"""
    
    def __init__(self):
        self.reference_date = datetime.now()
        self.ruptura_threshold = float(os.getenv("RUPTURA_JANELA_ALERTA", "0.75"))
        self.delay_logistico = int(os.getenv("DELAY_LOGISTICO_PADRAO", "20"))
    
    def generate_rico_insights(self, transactions: List[Dict[str, Any]], dataset_id: UUID) -> List[Alert]:
        """Gerar insights R.I.C.O. completos"""
        try:
            df = pd.DataFrame(transactions)
            df['date'] = pd.to_datetime(df['date'])
            
            alerts = []
            
            # Gerar alertas de Ruptura
            ruptura_alerts = self._generate_ruptura_alerts(df, dataset_id)
            alerts.extend(ruptura_alerts)
            
            # Gerar alertas de Inatividade
            inatividade_alerts = self._generate_inatividade_alerts(df, dataset_id)
            alerts.extend(inatividade_alerts)
            
            # Gerar alertas de Crescimento
            crescimento_alerts = self._generate_crescimento_alerts(df, dataset_id)
            alerts.extend(crescimento_alerts)
            
            # Gerar alertas de Oportunidade
            oportunidade_alerts = self._generate_oportunidade_alerts(df, dataset_id)
            alerts.extend(oportunidade_alerts)
            
            logger.info(f"Gerados {len(alerts)} insights R.I.C.O.")
            return alerts
            
        except Exception as e:
            logger.error(f"Erro na geração de insights: {e}")
            return []
    
    def _generate_ruptura_alerts(self, df: pd.DataFrame, dataset_id: UUID) -> List[Alert]:
        """Gerar alertas de ruptura baseados no giro médio"""
        alerts = []
        
        try:
            # Analisar por cliente-produto
            for (client, sku), group in df.groupby(['client', 'sku']):
                if len(group) < 2:
                    continue
                
                # Calcular giro médio
                dates = sorted(group['date'].unique())
                intervals = []
                for i in range(1, len(dates)):
                    interval = (dates[i] - dates[i-1]).days
                    intervals.append(interval)
                
                if not intervals:
                    continue
                
                giro_medio = np.median(intervals)
                last_purchase = dates[-1]
                days_since_last = (self.reference_date - last_purchase).days
                
                # Verificar ruptura projetada
                ruptura_threshold_days = giro_medio * self.ruptura_threshold + self.delay_logistico
                
                if days_since_last >= ruptura_threshold_days:
                    # Calcular confiabilidade
                    reliability = self._calculate_reliability(group, intervals)
                    
                    # Gerar diagnóstico e ação
                    diagnosis = f"Cliente {client} não compra {group.iloc[0]['product']} há {days_since_last} dias. Giro médio: {giro_medio:.1f} dias."
                    action = f"Contatar cliente em até 3 dias. Oferecer condições especiais ou verificar necessidade."
                    
                    alert = Alert(
                        dataset_id=dataset_id,
                        client=client,
                        sku=sku,
                        type="ruptura",
                        diagnosis=diagnosis,
                        recommended_action=action,
                        reliability=reliability,
                        suggested_deadline="3 dias"
                    )
                    
                    alerts.append(alert)
            
            logger.info(f"Gerados {len(alerts)} alertas de ruptura")
            return alerts
            
        except Exception as e:
            logger.error(f"Erro nos alertas de ruptura: {e}")
            return []
    
    def _generate_inatividade_alerts(self, df: pd.DataFrame, dataset_id: UUID) -> List[Alert]:
        """Gerar alertas de inatividade de clientes"""
        alerts = []
        
        try:
            # Analisar por cliente
            for client, group in df.groupby('client'):
                last_purchase = group['date'].max()
                days_inactive = (self.reference_date - last_purchase).days
                
                # Classificar inatividade
                if days_inactive >= 90:
                    status = "inativo antigo"
                    urgency = "🔴"
                    deadline = "1 semana"
                elif days_inactive >= 60:
                    status = "inativo recente"
                    urgency = "🟡"
                    deadline = "3 dias"
                elif days_inactive >= 30:
                    status = "em risco"
                    urgency = "🔵"
                    deadline = "2 dias"
                else:
                    continue  # Cliente ativo
                
                # Calcular estatísticas do cliente
                total_orders = group['order_id'].nunique()
                total_spent = group['subtotal'].sum()
                avg_ticket = total_spent / total_orders
                
                # Gerar diagnóstico e ação
                diagnosis = f"Cliente {client} está {status} ({days_inactive} dias). Histórico: {total_orders} pedidos, ticket médio R$ {avg_ticket:.2f}."
                
                if status == "inativo antigo":
                    action = "Campanha de reativação com desconto especial. Verificar se mudou de fornecedor."
                elif status == "inativo recente":
                    action = "Contato comercial para entender motivo da ausência. Oferecer novidades."
                else:
                    action = "Follow-up preventivo. Verificar satisfação e necessidades futuras."
                
                alert = Alert(
                    dataset_id=dataset_id,
                    client=client,
                    sku=None,
                    type="inatividade",
                    diagnosis=diagnosis,
                    recommended_action=action,
                    reliability=urgency,
                    suggested_deadline=deadline
                )
                
                alerts.append(alert)
            
            logger.info(f"Gerados {len(alerts)} alertas de inatividade")
            return alerts
            
        except Exception as e:
            logger.error(f"Erro nos alertas de inatividade: {e}")
            return []
    
    def _generate_crescimento_alerts(self, df: pd.DataFrame, dataset_id: UUID) -> List[Alert]:
        """Gerar alertas de oportunidades de crescimento"""
        alerts = []
        
        try:
            # Analisar crescimento por cliente nos últimos meses
            cutoff_date = self.reference_date - timedelta(days=90)
            recent_data = df[df['date'] >= cutoff_date]
            
            for client, group in recent_data.groupby('client'):
                if len(group) < 3:  # Precisa de pelo menos 3 compras
                    continue
                
                # Calcular tendência de crescimento
                monthly_sales = group.groupby(group['date'].dt.to_period('M'))['subtotal'].sum()
                
                if len(monthly_sales) >= 2:
                    # Calcular crescimento percentual
                    growth_rates = []
                    for i in range(1, len(monthly_sales)):
                        if monthly_sales.iloc[i-1] > 0:
                            growth = (monthly_sales.iloc[i] - monthly_sales.iloc[i-1]) / monthly_sales.iloc[i-1] * 100
                            growth_rates.append(growth)
                    
                    if growth_rates:
                        avg_growth = np.mean(growth_rates)
                        
                        # Alertar sobre crescimento significativo
                        if avg_growth > 15:  # Crescimento > 15% ao mês
                            diagnosis = f"Cliente {client} em crescimento acelerado ({avg_growth:.1f}% ao mês). Oportunidade de expansão."
                            action = "Propor aumento de linha de crédito. Oferecer produtos complementares. Negociar condições especiais para volumes maiores."
                            
                            alert = Alert(
                                dataset_id=dataset_id,
                                client=client,
                                sku=None,
                                type="crescimento",
                                diagnosis=diagnosis,
                                recommended_action=action,
                                reliability="🔵",
                                suggested_deadline="1 semana"
                            )
                            
                            alerts.append(alert)
            
            logger.info(f"Gerados {len(alerts)} alertas de crescimento")
            return alerts
            
        except Exception as e:
            logger.error(f"Erro nos alertas de crescimento: {e}")
            return []
    
    def _generate_oportunidade_alerts(self, df: pd.DataFrame, dataset_id: UUID) -> List[Alert]:
        """Gerar alertas de oportunidades de cross-sell e up-sell"""
        alerts = []
        
        try:
            # Analisar oportunidades de mix de produtos
            for client, client_data in df.groupby('client'):
                client_products = set(client_data['sku'].unique())
                
                # Encontrar produtos populares que o cliente não compra
                all_products = df['sku'].value_counts()
                top_products = set(all_products.head(10).index)  # Top 10 produtos
                
                missing_products = top_products - client_products
                
                if missing_products and len(client_products) >= 2:  # Cliente já compra pelo menos 2 produtos
                    # Calcular potencial baseado no perfil do cliente
                    client_segment = client_data['segment'].iloc[0] if 'segment' in client_data.columns else None
                    client_avg_ticket = client_data['subtotal'].mean()
                    
                    for missing_sku in list(missing_products)[:3]:  # Máximo 3 sugestões
                        product_name = df[df['sku'] == missing_sku]['product'].iloc[0]
                        
                        # Verificar se outros clientes similares compram este produto
                        if client_segment:
                            segment_clients = df[df['segment'] == client_segment]['client'].unique()
                            segment_buyers = df[(df['sku'] == missing_sku) & (df['client'].isin(segment_clients))]['client'].nunique()
                            penetration = segment_buyers / len(segment_clients) * 100 if len(segment_clients) > 0 else 0
                        else:
                            penetration = 50  # Valor padrão
                        
                        if penetration > 30:  # Produto popular no segmento
                            diagnosis = f"Cliente {client} não compra {product_name}, popular em seu segmento ({penetration:.1f}% dos clientes similares compram)."
                            action = f"Oferecer {product_name} como produto complementar. Demonstrar benefícios e fazer oferta especial."
                            
                            alert = Alert(
                                dataset_id=dataset_id,
                                client=client,
                                sku=missing_sku,
                                type="oportunidade",
                                diagnosis=diagnosis,
                                recommended_action=action,
                                reliability="🟡",
                                suggested_deadline="2 semanas"
                            )
                            
                            alerts.append(alert)
            
            logger.info(f"Gerados {len(alerts)} alertas de oportunidade")
            return alerts
            
        except Exception as e:
            logger.error(f"Erro nos alertas de oportunidade: {e}")
            return []
    
    def _calculate_reliability(self, group: pd.DataFrame, intervals: List[int]) -> str:
        """Calcular confiabilidade do insight baseado no histórico"""
        try:
            num_orders = group['order_id'].nunique()
            cv = np.std(intervals) / np.mean(intervals) if np.mean(intervals) > 0 else 1
            days_since_last = (self.reference_date - group['date'].max()).days
            
            # Critérios de confiabilidade
            if num_orders >= 4 and cv < 0.3 and days_since_last < 45:
                return "🔵"  # Alta confiabilidade
            elif num_orders >= 2 and cv <= 0.5:
                return "🟡"  # Média confiabilidade
            else:
                return "🔴"  # Baixa confiabilidade
                
        except Exception:
            return "🔴"

