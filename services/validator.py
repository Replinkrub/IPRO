from typing import List, Dict, Any
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataValidator:
    """Validador de dados extraídos"""
    
    def __init__(self):
        self.required_fields = ['product', 'date', 'order_id', 'client', 'price', 'qty']
        self.errors = []
    
    def validate_transactions(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validar lista de transações"""
        validated = []
        self.errors = []
        
        for i, transaction in enumerate(transactions):
            try:
                validated_transaction = self._validate_transaction(transaction, i)
                if validated_transaction:
                    validated.append(validated_transaction)
            except Exception as e:
                self.errors.append(f"Erro na transação {i}: {e}")
                continue
        
        if self.errors:
            logger.warning(f"Encontrados {len(self.errors)} erros de validação")
            for error in self.errors[:10]:  # Mostrar apenas os primeiros 10 erros
                logger.warning(error)
        
        logger.info(f"Validadas {len(validated)} de {len(transactions)} transações")
        return validated
    
    def _validate_transaction(self, transaction: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Validar uma transação individual"""
        # Verificar campos obrigatórios
        for field in self.required_fields:
            if field not in transaction or transaction[field] is None:
                raise ValueError(f"Campo obrigatório '{field}' ausente")
        
        # Validar tipos e valores
        validated = {}
        
        # Produto
        validated['product'] = str(transaction['product']).strip()
        if not validated['product']:
            raise ValueError("Nome do produto não pode estar vazio")
        
        # Data
        if not isinstance(transaction['date'], datetime):
            raise ValueError("Data deve ser um objeto datetime")
        validated['date'] = transaction['date']
        
        # ID do pedido
        validated['order_id'] = str(transaction['order_id']).strip()
        if not validated['order_id']:
            raise ValueError("ID do pedido não pode estar vazio")
        
        # Cliente
        validated['client'] = str(transaction['client']).strip()
        if not validated['client']:
            raise ValueError("Nome do cliente não pode estar vazio")
        
        # Vendedor
        validated['seller'] = str(transaction.get('seller', '')).strip()
        
        # Preço
        try:
            validated['price'] = float(transaction['price'])
            if validated['price'] <= 0:
                raise ValueError("Preço deve ser maior que zero")
        except (ValueError, TypeError):
            raise ValueError("Preço deve ser um número válido")
        
        # Quantidade
        try:
            validated['qty'] = int(transaction['qty'])
            if validated['qty'] <= 0:
                raise ValueError("Quantidade deve ser maior que zero")
        except (ValueError, TypeError):
            raise ValueError("Quantidade deve ser um número inteiro válido")
        
        # Subtotal
        if 'subtotal' in transaction:
            try:
                validated['subtotal'] = float(transaction['subtotal'])
            except (ValueError, TypeError):
                validated['subtotal'] = validated['price'] * validated['qty']
        else:
            validated['subtotal'] = validated['price'] * validated['qty']
        
        # Verificar consistência do subtotal
        expected_subtotal = validated['price'] * validated['qty']
        if abs(validated['subtotal'] - expected_subtotal) > 0.01:
            logger.warning(f"Subtotal inconsistente na linha {index}: "
                         f"esperado {expected_subtotal}, encontrado {validated['subtotal']}")
            validated['subtotal'] = expected_subtotal
        
        # Campos opcionais
        validated['category'] = str(transaction.get('category', '')).strip() or None
        validated['segment'] = str(transaction.get('segment', '')).strip() or None
        validated['city'] = str(transaction.get('city', '')).strip() or None
        validated['uf'] = str(transaction.get('uf', '')).strip() or None
        
        # Custo (opcional)
        if 'cost' in transaction and transaction['cost'] is not None:
            try:
                validated['cost'] = float(transaction['cost'])
                if validated['cost'] < 0:
                    validated['cost'] = None
            except (ValueError, TypeError):
                validated['cost'] = None
        else:
            validated['cost'] = None
        
        return validated
    
    def validate_customers(self, customers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validar lista de clientes"""
        validated = []
        self.errors = []
        
        for i, customer in enumerate(customers):
            try:
                validated_customer = self._validate_customer(customer, i)
                if validated_customer:
                    validated.append(validated_customer)
            except Exception as e:
                self.errors.append(f"Erro no cliente {i}: {e}")
                continue
        
        if self.errors:
            logger.warning(f"Encontrados {len(self.errors)} erros de validação de clientes")
        
        logger.info(f"Validados {len(validated)} de {len(customers)} clientes")
        return validated
    
    def _validate_customer(self, customer: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Validar um cliente individual"""
        validated = {}
        
        # Nome (obrigatório)
        if 'name' not in customer or not customer['name']:
            raise ValueError("Nome do cliente é obrigatório")
        
        validated['name'] = str(customer['name']).strip()
        if not validated['name']:
            raise ValueError("Nome do cliente não pode estar vazio")
        
        # Campos opcionais
        validated['segment'] = str(customer.get('segment', '')).strip() or None
        validated['city'] = str(customer.get('city', '')).strip() or None
        validated['uf'] = str(customer.get('uf', '')).strip() or None
        validated['source'] = str(customer.get('source', 'upload')).strip()
        
        # Data de cadastro
        if 'created_at' in customer and customer['created_at']:
            if isinstance(customer['created_at'], datetime):
                validated['created_at'] = customer['created_at']
            else:
                validated['created_at'] = None
        else:
            validated['created_at'] = None
        
        return validated
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Retornar resumo da validação"""
        return {
            "total_errors": len(self.errors),
            "errors": self.errors
        }

