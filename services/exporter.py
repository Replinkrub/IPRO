import pandas as pd
import xlsxwriter
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExcelExporter:
    """Exportador de dados para Excel com formatação brasileira"""

    def __init__(self):
        self.date_format = "dd/mm/yyyy"
        self.currency_format = "R$ #,##0.00"
        self.number_format = "#,##0.00"
        self.percentage_format = "0.00%"

    def export_to_excel(
        self,
        file_path: str,
        transactions: List[Dict],
        customer_analytics: List[Dict],
        product_analytics: List[Dict],
        alerts: List[Dict],
        dataset_id: str,
    ):
        """Exportar dados para Excel com 5 abas"""
        try:
            # Criar workbook
            workbook = xlsxwriter.Workbook(file_path)

            # Definir formatos
            formats = self._create_formats(workbook)

            # Aba 1: Painel (KPIs)
            self._create_painel_sheet(
                workbook, formats, transactions, customer_analytics
            )

            # Aba 2: Radar Cliente
            self._create_radar_cliente_sheet(workbook, formats, customer_analytics)

            # Aba 3: Radar Produto
            self._create_radar_produto_sheet(
                workbook, formats, product_analytics, transactions
            )

            # Aba 4: Alvos Priorizados (R.I.C.O.)
            self._create_alvos_priorizados_sheet(workbook, formats, alerts)

            # Aba 5: Base Completa
            self._create_base_completa_sheet(workbook, formats, transactions)

            workbook.close()
            logger.info(f"Excel exportado com sucesso: {file_path}")

        except Exception as e:
            logger.error(f"Erro na exportação para Excel: {e}")
            raise

    def _create_formats(self, workbook):
        """Criar formatos para o Excel"""
        return {
            "header": workbook.add_format(
                {
                    "bold": True,
                    "bg_color": "#4472C4",
                    "font_color": "white",
                    "border": 1,
                    "align": "center",
                }
            ),
            "currency": workbook.add_format(
                {"num_format": self.currency_format, "border": 1}
            ),
            "date": workbook.add_format({"num_format": self.date_format, "border": 1}),
            "number": workbook.add_format(
                {"num_format": self.number_format, "border": 1}
            ),
            "percentage": workbook.add_format(
                {"num_format": self.percentage_format, "border": 1}
            ),
            "text": workbook.add_format({"border": 1, "text_wrap": True}),
            "reliability_high": workbook.add_format(
                {
                    "bg_color": "#00B050",
                    "font_color": "white",
                    "border": 1,
                    "align": "center",
                }
            ),
            "reliability_medium": workbook.add_format(
                {
                    "bg_color": "#FFC000",
                    "font_color": "black",
                    "border": 1,
                    "align": "center",
                }
            ),
            "reliability_low": workbook.add_format(
                {
                    "bg_color": "#FF0000",
                    "font_color": "white",
                    "border": 1,
                    "align": "center",
                }
            ),
        }

    def _create_painel_sheet(self, workbook, formats, transactions, customer_analytics):
        """Criar aba Painel com KPIs principais"""
        worksheet = workbook.add_worksheet("Painel")

        # Título
        worksheet.write(0, 0, "PAINEL DE KPIs - IPRO", formats["header"])
        worksheet.merge_range(0, 0, 0, 5, "PAINEL DE KPIs - IPRO", formats["header"])

        # Calcular KPIs
        df = pd.DataFrame(transactions)

        total_revenue = df["subtotal"].sum()
        total_customers = df["client"].nunique()
        total_products = df["sku"].nunique()
        total_orders = df["order_id"].nunique()
        avg_ticket = total_revenue / total_orders if total_orders > 0 else 0

        # KPIs principais
        kpis = [
            ["Receita Total", total_revenue],
            ["Total de Clientes", total_customers],
            ["Total de Produtos", total_products],
            ["Total de Pedidos", total_orders],
            ["Ticket Médio", avg_ticket],
        ]

        # Escrever KPIs
        row = 2
        worksheet.write(row, 0, "KPI", formats["header"])
        worksheet.write(row, 1, "Valor", formats["header"])

        for i, (kpi, value) in enumerate(kpis):
            row += 1
            worksheet.write(row, 0, kpi, formats["text"])
            if "Receita" in kpi or "Ticket" in kpi:
                worksheet.write(row, 1, value, formats["currency"])
            else:
                worksheet.write(row, 1, value, formats["number"])

        # RFM Summary
        if customer_analytics:
            ca_df = pd.DataFrame(customer_analytics)

            row += 3
            worksheet.write(row, 0, "ANÁLISE RFM", formats["header"])
            worksheet.merge_range(row, 0, row, 5, "ANÁLISE RFM", formats["header"])

            row += 1
            rfm_headers = ["Métrica", "Média", "Mediana", "Mín", "Máx"]
            for i, header in enumerate(rfm_headers):
                worksheet.write(row, i, header, formats["header"])

            rfm_metrics = [
                ["Recência (dias)", ca_df["recency"]],
                ["Frequência", ca_df["frequency"]],
                ["Valor Monetário", ca_df["monetary"]],
                ["Ticket Médio", ca_df["avg_ticket"]],
            ]

            for metric_name, values in rfm_metrics:
                row += 1
                worksheet.write(row, 0, metric_name, formats["text"])
                worksheet.write(row, 1, values.mean(), formats["number"])
                worksheet.write(row, 2, values.median(), formats["number"])
                worksheet.write(row, 3, values.min(), formats["number"])
                worksheet.write(row, 4, values.max(), formats["number"])

        # Ajustar largura das colunas
        worksheet.set_column(0, 0, 20)
        worksheet.set_column(1, 4, 15)

    def _create_radar_cliente_sheet(self, workbook, formats, customer_analytics):
        """Criar aba Radar Cliente"""
        worksheet = workbook.add_worksheet("Radar Cliente")

        if not customer_analytics:
            worksheet.write(0, 0, "Nenhum dado de cliente disponível", formats["text"])
            return

        # Cabeçalhos
        headers = [
            "Cliente",
            "Recência (dias)",
            "Frequência",
            "Valor Monetário",
            "Ticket Médio",
            "Giro Médio",
            "Tier",
        ]

        for i, header in enumerate(headers):
            worksheet.write(0, i, header, formats["header"])

        # Dados
        for row, customer in enumerate(customer_analytics, 1):
            worksheet.write(row, 0, customer["client"], formats["text"])
            worksheet.write(row, 1, customer["recency"], formats["number"])
            worksheet.write(row, 2, customer["frequency"], formats["number"])
            worksheet.write(row, 3, customer["monetary"], formats["currency"])
            worksheet.write(row, 4, customer["avg_ticket"], formats["currency"])
            worksheet.write(row, 5, customer["gm_cliente"], formats["number"])
            worksheet.write(row, 6, customer["tier"], formats["text"])

        # Ajustar largura das colunas
        worksheet.set_column(0, 0, 30)
        worksheet.set_column(1, 6, 15)

    def _create_radar_produto_sheet(
        self, workbook, formats, product_analytics, transactions
    ):
        """Criar aba Radar Produto"""
        worksheet = workbook.add_worksheet("Radar Produto")

        # Calcular estatísticas de produtos
        df = pd.DataFrame(transactions)
        product_stats = (
            df.groupby(["sku", "product"])
            .agg(
                {
                    "subtotal": "sum",
                    "qty": "sum",
                    "order_id": "nunique",
                    "client": "nunique",
                }
            )
            .reset_index()
        )

        # Cabeçalhos
        headers = [
            "SKU",
            "Produto",
            "Receita Total",
            "Quantidade Total",
            "Pedidos",
            "Clientes",
            "Penetração %",
        ]

        for i, header in enumerate(headers):
            worksheet.write(0, i, header, formats["header"])

        # Dados
        total_customers = df["client"].nunique()

        for row, (_, product) in enumerate(product_stats.iterrows(), 1):
            penetration = (
                (product["client"] / total_customers * 100)
                if total_customers > 0
                else 0
            )

            worksheet.write(row, 0, product["sku"], formats["text"])
            worksheet.write(row, 1, product["product"], formats["text"])
            worksheet.write(row, 2, product["subtotal"], formats["currency"])
            worksheet.write(row, 3, product["qty"], formats["number"])
            worksheet.write(row, 4, product["order_id"], formats["number"])
            worksheet.write(row, 5, product["client"], formats["number"])
            worksheet.write(row, 6, penetration, formats["percentage"])

        # Ajustar largura das colunas
        worksheet.set_column(0, 0, 15)
        worksheet.set_column(1, 1, 30)
        worksheet.set_column(2, 6, 15)

    def _create_alvos_priorizados_sheet(self, workbook, formats, alerts):
        """Criar aba Alvos Priorizados (R.I.C.O.)"""
        worksheet = workbook.add_worksheet("Alvos Priorizados")

        if not alerts:
            worksheet.write(0, 0, "Nenhum alerta disponível", formats["text"])
            return

        # Cabeçalhos
        headers = [
            "Cliente",
            "SKU",
            "Tipo",
            "Diagnóstico",
            "Ação Recomendada",
            "Confiabilidade",
            "Prazo",
        ]

        for i, header in enumerate(headers):
            worksheet.write(0, i, header, formats["header"])

        # Dados
        for row, alert in enumerate(alerts, 1):
            worksheet.write(row, 0, alert["client"], formats["text"])
            worksheet.write(row, 1, alert.get("sku", ""), formats["text"])
            worksheet.write(row, 2, alert["type"].upper(), formats["text"])
            worksheet.write(row, 3, alert["diagnosis"], formats["text"])
            worksheet.write(row, 4, alert["recommended_action"], formats["text"])

            # Formatação da confiabilidade com cores
            reliability = alert["reliability"]
            if reliability == "🔵":
                worksheet.write(row, 5, "ALTA", formats["reliability_high"])
            elif reliability == "🟡":
                worksheet.write(row, 5, "MÉDIA", formats["reliability_medium"])
            else:
                worksheet.write(row, 5, "BAIXA", formats["reliability_low"])

            worksheet.write(
                row, 6, alert.get("suggested_deadline", ""), formats["text"]
            )

        # Ajustar largura das colunas
        worksheet.set_column(0, 2, 15)
        worksheet.set_column(3, 4, 40)
        worksheet.set_column(5, 6, 15)

    def _create_base_completa_sheet(self, workbook, formats, transactions):
        """Criar aba Base Completa"""
        worksheet = workbook.add_worksheet("Base Completa")

        if not transactions:
            worksheet.write(0, 0, "Nenhuma transação disponível", formats["text"])
            return

        # Cabeçalhos
        headers = [
            "Data Emissão",
            "Pedido",
            "Cliente",
            "Vendedor",
            "SKU",
            "Produto",
            "Preço Unitário",
            "Quantidade",
            "Subtotal",
            "Categoria",
            "Segmento",
            "Cidade",
            "UF",
        ]

        for i, header in enumerate(headers):
            worksheet.write(0, i, header, formats["header"])

        # Dados (limitar a 10000 linhas para performance)
        max_rows = min(len(transactions), 10000)

        for row, transaction in enumerate(transactions[:max_rows], 1):
            worksheet.write(row, 0, transaction["date"], formats["date"])
            worksheet.write(row, 1, transaction["order_id"], formats["text"])
            worksheet.write(row, 2, transaction["client"], formats["text"])
            worksheet.write(row, 3, transaction.get("seller", ""), formats["text"])
            worksheet.write(row, 4, transaction["sku"], formats["text"])
            worksheet.write(row, 5, transaction["product"], formats["text"])
            worksheet.write(row, 6, transaction["price"], formats["currency"])
            worksheet.write(row, 7, transaction["qty"], formats["number"])
            worksheet.write(row, 8, transaction["subtotal"], formats["currency"])
            worksheet.write(row, 9, transaction.get("category", ""), formats["text"])
            worksheet.write(row, 10, transaction.get("segment", ""), formats["text"])
            worksheet.write(row, 11, transaction.get("city", ""), formats["text"])
            worksheet.write(row, 12, transaction.get("uf", ""), formats["text"])

        # Ajustar largura das colunas
        worksheet.set_column(0, 0, 12)
        worksheet.set_column(1, 1, 10)
        worksheet.set_column(2, 2, 25)
        worksheet.set_column(3, 5, 20)
        worksheet.set_column(6, 8, 12)
        worksheet.set_column(9, 12, 15)

    def export_to_csv(self, file_path: str, data: List[Dict]):
        """Exportar dados para CSV"""
        try:
            if not data:
                logger.warning("Nenhum dado para exportar")
                return

            df = pd.DataFrame(data)

            # Remover colunas MongoDB
            if "_id" in df.columns:
                df = df.drop("_id", axis=1)

            df.to_csv(file_path, index=False, encoding="utf-8-sig")
            logger.info(f"CSV exportado com sucesso: {file_path}")

        except Exception as e:
            logger.error(f"Erro na exportação para CSV: {e}")
            raise
