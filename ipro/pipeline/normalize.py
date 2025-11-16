"""Pipeline de normalização de relatórios de pedidos."""

from __future__ import annotations

import logging
import os
import unicodedata
from typing import Dict, Iterable, Optional

import pandas as pd

LOGGER = logging.getLogger(__name__)

# Colunas canônicas da Base Geral IPRO
BASE_COLUMNS = [
    "date",
    "order_id",
    "client",
    "seller",
    "sku",
    "product",
    "price",
    "qty",
    "subtotal",
    "category",
    "segment",
    "city",
    "uf",
]


def run_normalization(
    df: pd.DataFrame,
    *,
    sku_alias_path: Optional[str] = None,
    sku_names_path: Optional[str] = None,
    client_alias_path: Optional[str] = None,
) -> pd.DataFrame:
    """Executa o pipeline de normalização sobre o dataframe fornecido."""
    working_df = df.copy()
    normalized = _normalize_structure(working_df)

    sku_aliases = _load_mapping(sku_alias_path, "alias", "sku")
    if sku_aliases:
        normalized["sku"] = normalized["sku"].map(
            lambda value: sku_aliases.get(str(value).strip(), value)
        )
        LOGGER.info("Aplicados %d aliases de SKU", len(sku_aliases))
    elif sku_alias_path:
        LOGGER.warning(
            "Nenhum alias aplicado; arquivo %s vazio ou inválido.", sku_alias_path
        )

    sku_names = _load_mapping(sku_names_path, "sku", "name")
    if sku_names:
        normalized["product"] = normalized.apply(
            lambda row: sku_names.get(str(row["sku"]).strip(), row["product"]),
            axis=1,
        )
        LOGGER.info("Aplicados %d nomes canônicos de SKU", len(sku_names))
    elif sku_names_path:
        LOGGER.warning(
            "Nenhum nome canônico aplicado; arquivo %s vazio ou inválido.",
            sku_names_path,
        )

    client_aliases = _load_mapping(client_alias_path, "alias", "client")
    if client_aliases and "client" in normalized.columns:
        normalized["client"] = normalized["client"].map(
            lambda value: client_aliases.get(str(value).strip(), value)
        )
        LOGGER.info("Aplicados %d aliases de clientes", len(client_aliases))
    elif client_alias_path:
        LOGGER.warning(
            "Nenhum alias de cliente aplicado; arquivo %s vazio ou inválido.",
            client_alias_path,
        )

    # Ordenação e reindexação final
    normalized = normalized[BASE_COLUMNS]
    normalized = normalized.sort_values(
        ["date", "client", "sku"], na_position="last"
    ).reset_index(drop=True)
    return normalized


def _normalize_structure(df: pd.DataFrame) -> pd.DataFrame:
    columns_map = {
        "date": ["data", "data emissao", "emissao", "date", "data emissão"],
        "order_id": ["pedido", "order", "nota", "nf", "order id"],
        "client": ["cliente", "cliente nome", "razao", "cliente_id"],
        "seller": ["vendedor", "representante", "seller", "criador"],
        "sku": ["sku", "codigo", "código", "cod sku", "ean", "produto codigo"],
        "product": ["produto", "descricao", "descrição", "product", "item"],
        "price": ["preco", "preço", "valor unitario", "vl unit", "price"],
        "qty": ["quantidade", "qtd", "qtde", "qty"],
        "subtotal": ["subtotal", "valor total", "vl total", "total"],
        "category": ["categoria", "categoria produto"],
        "segment": ["segmento", "segment"],
        "city": ["cidade", "municipio"],
        "uf": ["uf", "estado", "sigla", "state"],
    }

    normalized_names = {_normalize_string(col): col for col in df.columns}

    result: Dict[str, pd.Series] = {}
    for target, keywords in columns_map.items():
        source_col = _find_column(normalized_names, keywords)
        if source_col:
            series = df[source_col]
            result[target] = series.copy()
        else:
            result[target] = (
                pd.Series(["" for _ in range(len(df))])
                if target not in {"price", "qty", "subtotal"}
                else pd.Series([0 for _ in range(len(df))])
            )

    # SKU extraction heuristics
    if result["sku"].eq("").all():
        combined_col = _find_column(normalized_names, ["produto", "item", "descricao"])
        if combined_col:
            sku_codes, descriptions = _split_combined_sku(df[combined_col])
            result["sku"] = sku_codes
            if result["product"].eq("").all():
                result["product"] = descriptions

    # Ensure product column is filled when only SKU column available
    if result["product"].eq("").all() and result["sku"].notna().any():
        result["product"] = result["sku"].astype(str)

    # Parse numeric columns
    result["price"] = _coerce_numeric(result["price"], float)
    result["qty"] = _coerce_numeric(result["qty"], float)
    result["subtotal"] = _coerce_numeric(result["subtotal"], float)

    # Attempt to fill subtotal when missing
    missing_subtotal = result["subtotal"].isna() | (result["subtotal"] == 0)
    computed_subtotal = result["price"].fillna(0) * result["qty"].fillna(0)
    result["subtotal"] = result["subtotal"].where(~missing_subtotal, computed_subtotal)

    # Normalize dates
    result["date"] = pd.to_datetime(result["date"], errors="coerce")

    # Clean strings
    for key in [
        "order_id",
        "client",
        "seller",
        "sku",
        "product",
        "category",
        "segment",
        "city",
        "uf",
    ]:
        result[key] = (
            result[key].astype(str).fillna("").str.strip().replace({"nan": ""})
        )

    # Final dataframe
    normalized_df = pd.DataFrame(result, columns=BASE_COLUMNS)
    return normalized_df


def _find_column(
    normalized_names: Dict[str, str], keywords: Iterable[str]
) -> Optional[str]:
    for keyword in keywords:
        normalized_keyword = _normalize_string(keyword)
        for normalized_col, original in normalized_names.items():
            if normalized_keyword in normalized_col:
                return original
    return None


def _normalize_string(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value).lower())
    return "".join(
        ch for ch in value if not unicodedata.combining(ch) and not ch.isspace()
    )


def _split_combined_sku(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    codes = []
    descriptions = []
    for value in series.fillna(""):
        text = str(value).strip()
        if not text:
            codes.append("")
            descriptions.append("")
            continue
        parts = text.split("-", 1)
        code_candidate = parts[0].strip()
        desc_candidate = parts[1].strip() if len(parts) > 1 else ""
        codes.append(code_candidate)
        descriptions.append(desc_candidate)
    return pd.Series(codes), pd.Series(descriptions)


def _coerce_numeric(series: pd.Series, dtype) -> pd.Series:
    coerced = pd.to_numeric(series, errors="coerce")
    if dtype is int:
        coerced = coerced.astype("Int64")
    return coerced


def _load_mapping(
    path: Optional[str], key_column: str, value_column: str
) -> Dict[str, str]:
    if not path:
        LOGGER.warning("Arquivo de calibração para %s não informado.", value_column)
        return {}

    if not os.path.exists(path):
        LOGGER.error("Arquivo de calibração não encontrado: %s", path)
        raise SystemExit(7)

    try:
        mapping_df = pd.read_csv(path)
    except Exception as exc:  # pragma: no cover - fallback
        LOGGER.error("Falha ao ler %s: %s", path, exc)
        raise SystemExit(8) from exc

    if mapping_df.empty or mapping_df.shape[1] < 2:
        return {}

    normalized_columns = {_normalize_string(col): col for col in mapping_df.columns}
    key = _match_column(normalized_columns, key_column)
    value = _match_column(normalized_columns, value_column)
    if not key or not value:
        LOGGER.warning("Colunas esperadas não encontradas em %s", path)
        return {}

    mapping_df = mapping_df[[key, value]].dropna()
    return {
        str(row[key]).strip(): str(row[value]).strip()
        for _, row in mapping_df.iterrows()
        if str(row[key]).strip()
    }


def _match_column(columns: Dict[str, str], expected: str) -> Optional[str]:
    normalized_expected = _normalize_string(expected)
    for normalized, original in columns.items():
        if normalized_expected in normalized:
            return original
    return None
