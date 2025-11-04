from typing import List, Dict, Any
import re
import unicodedata
from datetime import datetime
from decimal import Decimal
import logging

from services.models import Transaction
from services.database import get_db
from core.utils import as_decimal, to_utc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataNormalizer:
    """Normalizador de dados para padronização"""
    
    def __init__(self):
        self.db = get_db()
    
    def normalize_transactions(self, transactions: List[Dict[str, Any]], dataset_id: str) -> List[Transaction]:
        """Normalizar lista de transações"""
        normalized = []
        
        for transaction in transactions:
            try:
                # Normalizar cliente
                normalized_client = self._normalize_client_name(transaction['client'])
                
                # Enriquecer com dados de cadastro
                customer_data = self._get_customer_data(normalized_client)
                
                # Gerar SKU se não existir
                sku = self._generate_sku(transaction['product'])
                
                # Criar transação normalizada
                normalized_transaction = Transaction(
                    dataset_id=dataset_id,
                    date=to_utc(transaction["date"]),
                    order_id=transaction['order_id'],
                    client=normalized_client,
                    seller=transaction.get("seller"),
                    sku=sku,
                    product=transaction["product"],
                    price=as_decimal(transaction["price"]),
                    qty=int(transaction["qty"]),
                    subtotal=(as_decimal(transaction["price"]) * Decimal(transaction["qty"])).quantize(Decimal("0.01")),
                    uf=customer_data.get("uf") if customer_data else None,
                    segment=customer_data.get("segment") if customer_data else None,
                    city=customer_data.get("city") if customer_data else None
                )
                
                normalized.append(normalized_transaction)
                
            except Exception as e:
                logger.error(f"Erro ao normalizar transação: {e}")
                continue
        
        logger.info(f"Normalizadas {len(normalized)} transações")
        return normalized
    
    def _normalize_client_name(self, name: str) -> str:
        if not name:
            return ""
        s = name.lower()
        s = re.sub(r"[\W_]+", "", s) # remove caracteres não alfanuméricos
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("utf-8") # remove acentos
        return s
    
    def _get_customer_data(self, normalized_name: str) -> Dict[str, Any]:
        try:
            customer = self.db.customers.find_one({"name": normalized_name})
            if customer:
                return customer
            return {}
        except Exception as e:
            logger.warning(f"Erro ao buscar dados do cliente {normalized_name}: {e}")
            return {}
    def _generate_sku(self, product_name: str) -> str:
        if not product_name:
            return "UNKNOWN"
        s = product_name.upper()
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("utf-8")
        s = re.sub(r"[\W_]+", "", s)
        return s[:10]
    
    def _infer_category(self, product_name: str) -> str:
        return "Outros"

    def normalize_dates(self, date_str: str) -> datetime:
        try:
            if isinstance(date_str, datetime):
                return date_str
            return pd.to_datetime(date_str, dayfirst=True, errors="coerce").to_pydatetime()
        except:
            return datetime.now()

    def normalize_currency(self, value: str) -> float:
        if not value:
            return 0.0
        try:
            s = str(value).strip()
            if "," in s and "." in s and s.rfind(",") > s.rfind("."):
                s = s.replace(".", "").replace(",", ".")
            elif "," in s and "." not in s:
                s = s.replace(",", ".")
            return float(s)
        except:
            return 0.0

