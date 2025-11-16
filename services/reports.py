"""Geração de relatórios PRO em Excel."""

from __future__ import annotations

from typing import Iterable, Dict, Any

import pandas as pd


class ProReportBuilder:
    def __init__(self):
        self.date_fmt = "dd/mm/yyyy"
        self.currency_fmt = "R$ #,##0.00"

    def build(
        self,
        output_path: str,
        base_completa: Iterable[Dict[str, Any]],
        clientes: Iterable[Dict[str, Any]],
        produtos: Iterable[Dict[str, Any]],
        alertas: Iterable[Dict[str, Any]],
    ) -> None:
        base_df = pd.DataFrame(list(base_completa))
        clientes_df = pd.DataFrame(list(clientes))
        alertas_df = pd.DataFrame(list(alertas))

        with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
            workbook = writer.book
            fmt_date = workbook.add_format({"num_format": self.date_fmt})
            fmt_currency = workbook.add_format({"num_format": self.currency_fmt})
            fmt_header = workbook.add_format(
                {"bold": True, "bg_color": "#1F4E78", "font_color": "white"}
            )
            fmt_text = workbook.add_format({"text_wrap": True})

            self._write_base_completa(
                base_df, writer, fmt_date, fmt_currency, fmt_header
            )
            self._write_potencial_cliente(clientes_df, writer, fmt_header, fmt_currency)
            self._write_potencial_produto_cliente(
                base_df, writer, fmt_header, fmt_currency
            )
            self._write_insights(alertas_df, writer, fmt_header, fmt_text)
            self._write_alertas(alertas_df, writer, fmt_header, fmt_text)

    def _write_base_completa(
        self, df: pd.DataFrame, writer, fmt_date, fmt_currency, fmt_header
    ):
        sheet_name = "Base Completa"
        if not df.empty:
            for col in df.columns:
                if "date" in col or "data" in col:
                    df[col] = pd.to_datetime(df[col], errors="coerce")
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        sheet = writer.sheets[sheet_name]
        sheet.freeze_panes(1, 0)
        for idx, col in enumerate(df.columns):
            sheet.write(0, idx, col, fmt_header)
            width = (
                max(12, int(df[col].astype(str).str.len().mean() * 1.3))
                if not df.empty
                else 15
            )
            sheet.set_column(
                idx, idx, width, fmt_date if "date" in col or "data" in col else None
            )
        if "subtotal" in df.columns:
            col_idx = df.columns.get_loc("subtotal")
            sheet.set_column(col_idx, col_idx, 18, fmt_currency)

    def _write_potencial_cliente(
        self, df: pd.DataFrame, writer, fmt_header, fmt_currency
    ):
        sheet_name = "Potencial do Cliente"
        if df.empty:
            df = pd.DataFrame(
                columns=[
                    "client",
                    "rfm_score",
                    "segment",
                    "avg_ticket",
                    "gm_cliente",
                    "tier",
                ]
            )
        df_to_write = df.copy()
        if "last_order" in df_to_write.columns:
            df_to_write["last_order"] = pd.to_datetime(
                df_to_write["last_order"], errors="coerce"
            )
        df_to_write.sort_values(
            by="rfm_score", ascending=False, inplace=True, na_position="last"
        )
        df_to_write.to_excel(writer, sheet_name=sheet_name, index=False)
        sheet = writer.sheets[sheet_name]
        sheet.freeze_panes(1, 0)
        for idx, col in enumerate(df_to_write.columns):
            sheet.write(0, idx, col, fmt_header)
            width = (
                max(12, int(df_to_write[col].astype(str).str.len().mean() * 1.2))
                if not df_to_write.empty
                else 15
            )
            sheet.set_column(idx, idx, width)
        for col in ["monetary", "avg_ticket"]:
            if col in df_to_write.columns:
                col_idx = df_to_write.columns.get_loc(col)
                sheet.set_column(col_idx, col_idx, 16, fmt_currency)

    def _write_potencial_produto_cliente(
        self, df: pd.DataFrame, writer, fmt_header, fmt_currency
    ):
        sheet_name = "Potencial por Produto"
        if df.empty:
            pivot = pd.DataFrame(columns=["client", "sku", "subtotal", "qty"])
        else:
            pivot = (
                df.groupby(["client", "sku"])[["subtotal", "qty"]]
                .sum()
                .reset_index()
                .sort_values(["client", "subtotal"], ascending=[True, False])
            )
        pivot.to_excel(writer, sheet_name=sheet_name, index=False)
        sheet = writer.sheets[sheet_name]
        sheet.freeze_panes(1, 0)
        for idx, col in enumerate(pivot.columns):
            sheet.write(0, idx, col, fmt_header)
            width = (
                max(12, int(pivot[col].astype(str).str.len().mean() * 1.2))
                if not pivot.empty
                else 15
            )
            sheet.set_column(
                idx, idx, width, fmt_currency if col == "subtotal" else None
            )

    def _write_insights(self, df: pd.DataFrame, writer, fmt_header, fmt_text):
        """Export actionable insights ensuring legacy schema compatibility."""
        sheet_name = "Insights_Acionaveis"

        if df.empty:
            insights = pd.DataFrame(
                columns=[
                    "client",
                    "type",
                    "insight",
                    "action",
                    "reliability",
                    "suggested_deadline",
                ]
            )
        else:
            df = df.copy()

            # Compatibilidade com schema antigo (diagnosis / recommended_action)
            if "insight" not in df.columns and "diagnosis" in df.columns:
                df["insight"] = df["diagnosis"]

            if "action" not in df.columns and "recommended_action" in df.columns:
                df["action"] = df["recommended_action"]

            # Garante que todas as colunas necessárias existem
            required_cols = [
                "client",
                "type",
                "insight",
                "action",
                "reliability",
                "suggested_deadline",
            ]
            for col in required_cols:
                if col not in df.columns:
                    df[col] = None

            insights = df[required_cols]

        insights.to_excel(writer, sheet_name=sheet_name, index=False)
        sheet = writer.sheets[sheet_name]
        sheet.freeze_panes(1, 0)

        for idx, col in enumerate(insights.columns):
            sheet.write(0, idx, col, fmt_header)
            if insights.empty:
                width = 20
            else:
                width = max(
                    15,
                    int(insights[col].astype(str).str.len().mean() * 1.1),
                )
            sheet.set_column(idx, idx, width, fmt_text)

    def _write_alertas(self, df: pd.DataFrame, writer, fmt_header, fmt_text):
        sheet_name = "Alertas RICO"
        if df.empty:
            alerts = pd.DataFrame(
                columns=[
                    "client",
                    "sku",
                    "type",
                    "insight",
                    "action",
                    "reliability",
                    "suggested_deadline",
                ]
            )
        else:
            alerts = df.copy()
        alerts.to_excel(writer, sheet_name=sheet_name, index=False)
        sheet = writer.sheets[sheet_name]
        sheet.freeze_panes(1, 0)
        for idx, col in enumerate(alerts.columns):
            sheet.write(0, idx, col, fmt_header)
            width = (
                max(12, int(alerts[col].astype(str).str.len().mean() * 1.1))
                if not alerts.empty
                else 18
            )
            sheet.set_column(idx, idx, width, fmt_text)
