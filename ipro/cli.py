"""Interface de linha de comando para utilidades do IPRO."""
from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Optional

import pandas as pd

from ipro.pipeline.normalize import run_normalization

LOGGER = logging.getLogger(__name__)


def _configure_logging(verbose: bool) -> None:
    """Configura o logging básico da aplicação."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(levelname)s] %(message)s",
    )


def build_parser() -> argparse.ArgumentParser:
    """Construir o parser principal do CLI."""
    parser = argparse.ArgumentParser(
        description="Ferramentas de linha de comando para processamento IPRO.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Habilita logs em nível DEBUG.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    normalize_parser = subparsers.add_parser(
        "normalize",
        help="Normaliza relatórios de pedidos em uma Base Geral IPRO.",
    )
    normalize_parser.add_argument(
        "--input",
        required=True,
        help="Caminho para o arquivo de entrada (.xlsx).",
    )
    normalize_parser.add_argument(
        "--output",
        required=True,
        help="Caminho para salvar o arquivo normalizado (.xlsx).",
    )
    normalize_parser.add_argument(
        "--alias",
        help="CSV com aliases de SKU (colunas alias,sku).",
    )
    normalize_parser.add_argument(
        "--names",
        help="CSV com nomes canônicos de SKU (colunas sku,name).",
    )
    normalize_parser.add_argument(
        "--clients",
        help="CSV com mapeamento de clientes canônicos (colunas alias,client).",
    )
    normalize_parser.add_argument(
        "--sheet",
        help="Nome da aba a ser lida do arquivo de entrada.",
    )

    return parser


def _ensure_output_directory(path: str) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def _read_excel(path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
    try:
        return pd.read_excel(path, sheet_name=sheet_name)
    except FileNotFoundError as exc:
        LOGGER.error("Arquivo de entrada não encontrado: %s", path)
        raise SystemExit(1) from exc
    except ValueError as exc:
        LOGGER.error("Aba '%s' não encontrada em %s", sheet_name, path)
        raise SystemExit(2) from exc
    except Exception as exc:  # pragma: no cover - fallback defensivo
        LOGGER.error("Falha ao ler %s: %s", path, exc)
        raise SystemExit(3) from exc


def _save_excel(df: pd.DataFrame, path: str) -> None:
    _ensure_output_directory(path)
    try:
        df.to_excel(path, index=False)
        LOGGER.info("Arquivo salvo em %s", path)
    except FileNotFoundError as exc:
        LOGGER.error("Diretório do arquivo de saída inexistente: %s", path)
        raise SystemExit(4) from exc
    except PermissionError as exc:
        LOGGER.error("Sem permissão para escrever em %s", path)
        raise SystemExit(5) from exc
    except Exception as exc:  # pragma: no cover - fallback defensivo
        LOGGER.error("Falha ao salvar %s: %s", path, exc)
        raise SystemExit(6) from exc


def main(argv: Optional[list[str]] = None) -> int:
    """Ponto de entrada principal do CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)

    if args.command == "normalize":
        if not args.alias:
            LOGGER.warning("Nenhum arquivo de alias informado; prosseguindo sem aplicar aliases de SKU.")
        if not args.names:
            LOGGER.warning("Nenhum arquivo de nomes canônicos informado; prosseguindo sem renomear SKUs.")
        if not args.clients:
            LOGGER.warning("Nenhum arquivo de clientes canônicos informado; prosseguindo sem normalizar clientes.")

        df = _read_excel(args.input, sheet_name=args.sheet)
        normalized = run_normalization(
            df,
            sku_alias_path=args.alias,
            sku_names_path=args.names,
            client_alias_path=args.clients,
        )
        _save_excel(normalized, args.output)
        return 0

    parser.error("Nenhum comando válido informado")
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
