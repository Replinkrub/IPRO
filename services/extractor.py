import pandas as pd
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from services.schema_aliases import apply_aliases, TX_ALIASES, CUSTOMER_ALIASES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataExtractor:
    """Extrator de dados de planilhas Excel"""
    
    def __init__(self):
        self.product_pattern = re.compile(r'produto:\s*(.+)', re.IGNORECASE)
    
    def extract_transactions(self, file_path: str) -> List[Dict[str, Any]]:
        """Extrair transações de relatório de pedidos.

        Este método tenta identificar automaticamente o formato do arquivo. Para
        relatórios estruturados (uma única linha de cabeçalho seguida de dados),
        utiliza o pipeline padrão com aliases e promoção de cabeçalho. Para
        relatórios não estruturados onde cada produto é apresentado em blocos com
        cabeçalhos repetidos (como nos relatórios de "Produtos por Pedido"),
        emprega um analisador linha a linha que detecta blocos "Produto:" e
        extrai transações subsequentes.
        """
        try:
            # Leia o Excel inteiro sem cabeçalho para inspecionar a estrutura
            df = pd.read_excel(file_path, header=None)
        except Exception as e:
            logger.error(f"Erro ao ler o arquivo {file_path}: {e}")
            return []

        # Se houver alguma linha que comece com "Produto:" (indicando formato em blocos),
        # use o extrator especializado. Caso contrário, caia no extrator estruturado.
        try:
            has_produto = df[0].dropna().astype(str).str.contains(r"(?i)^\s*produto").any()
        except Exception:
            has_produto = False

        if has_produto:
            try:
                return self._extract_transactions_unstructured(df)
            except Exception as e:
                logger.error(f"Erro ao extrair transações (formato não estruturado) de {file_path}: {e}")
                return []
        else:
            return self._extract_transactions_structured(file_path)


    def _extract_transactions_structured(self, file_path: str) -> List[Dict[str, Any]]:
        """Extrair transações de planilhas estruturadas com uma linha de cabeçalho.

        Este método mantém a lógica existente de chunking e aplicação de aliases para
        arquivos onde os dados são fornecidos em formato tabular simples (uma linha
        de cabeçalho seguida de linhas de dados). Inclui heurísticas para promover
        a primeira linha a cabeçalho quando necessário.
        """
        transactions: List[Dict[str, Any]] = []
        seen_transactions = set()
        try:
            for chunk in self.iter_excel_rows(file_path):
                # Aplicar alias para nomes canônicos. Caso as colunas não correspondam a
                # nenhuma chave canônica (por exemplo, se a primeira linha está como dados),
                # tente promover a primeira linha a cabeçalho.
                try:
                    chunk = apply_aliases(chunk, TX_ALIASES)
                except Exception as e:
                    logger.warning(f"Erro ao aplicar aliases: {e}")
                    # continua sem aliases, provavelmente falhará mais adiante

                # Se depois de aplicar aliases não houver colunas canônicas como 'product' ou 'client',
                # assumimos que a primeira linha é o cabeçalho e reprocessamos.
                if not any(col in chunk.columns for col in ['product','date','client','price','qty','order_id']):
                    if len(chunk) > 1:
                        header = chunk.iloc[0]
                        new_columns = [str(h).strip() if pd.notna(h) else f'col_{i}' for i, h in enumerate(header)]
                        chunk = chunk.iloc[1:].copy()
                        chunk.columns = new_columns
                        try:
                            chunk = apply_aliases(chunk, TX_ALIASES)
                        except Exception as e:
                            logger.warning(f"Erro ao aplicar aliases após promover cabeçalho: {e}")

                for _, row in chunk.iterrows():
                    try:
                        transaction = {
                            'product': row.get('product'),
                            'date': self._parse_date(row.get('date')),
                            'order_id': self._parse_ean(row.get('order_id')) if pd.notna(row.get('order_id')) else '',
                            'client': str(row.get('client')) if pd.notna(row.get('client')) else '',
                            'seller': str(row.get('seller')) if pd.notna(row.get('seller')) else '',
                            'price': self._parse_float(row.get('price')),
                            'qty': self._parse_int(row.get('qty')),
                            'subtotal': self._parse_float(row.get('subtotal'))
                        }
                        if (transaction['date'] and transaction['client'] and transaction['price'] >= 0 and transaction['qty'] != 0 and not self._is_noise_row(row)):
                            transaction_key = (transaction['date'], transaction['order_id'], transaction['product'], transaction['client'], transaction['qty'], transaction['price'])
                            if transaction_key not in seen_transactions:
                                transactions.append(transaction)
                                seen_transactions.add(transaction_key)
                    except (IndexError, ValueError) as e:
                        logger.warning(f"Erro ao processar linha: {e}")
                        continue
            logger.info(f"Extraídas {len(transactions)} transações de {file_path}")
            return transactions
        except Exception as e:
            logger.error(f"Erro ao extrair transações estruturadas de {file_path}: {e}")
            return []

    def _extract_transactions_unstructured(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Extrair transações de relatórios em blocos "Produto:".

        Este método percorre linha a linha, identificando blocos iniciados por
        "Produto: ..." seguidos por uma linha de cabeçalho (contendo termos como
        "Data Emissão", "Pedido", "Cliente" etc.) e, em seguida, as linhas de
        transações. Linhas de resumo (que não contêm data válida) são ignoradas.
        """
        transactions: List[Dict[str, Any]] = []
        seen_transactions = set()
        current_product: Optional[str] = None
        header_positions: Optional[Dict[str, int]] = None

        # Palavras‑chave para detectar cabeçalhos.  As chaves do dicionário
        # correspondem aos nomes canônicos que serão usados posteriormente (ex.: 'date'),
        # evitando divergências como 'data' vs. 'date'.
        header_keywords = {
            'date': ['data', 'data emissão', 'data emissao', 'emissão', 'emissao'],
            'order_id': ['pedido','order'],
            'client': ['cliente','cliente nome','razao'],
            'seller': ['criador','vendedor','representante'],
            'price': ['preço','preco','valor'],
            'qty': ['quantidade','qtd','qde','qtde','quant'],
            'subtotal': ['subtotal','total']
        }

        for _, row in df.iterrows():
            # Converta valores NaN para strings vazias para facilitar comparações
            row_vals = [str(x).strip() if not pd.isna(x) else '' for x in row]
            # Detecta início de bloco "Produto:"
            cell0 = row_vals[0]
            if cell0.lower().startswith('produto'):
                # Extraia o nome do produto após 'Produto:'
                match = re.search(r'produto\s*:\s*(.+)', cell0, re.IGNORECASE)
                current_product = match.group(1).strip() if match else None
                header_positions = None  # Reinicia detecção de cabeçalho para novo bloco
                continue
            # Detectar cabeçalho
            if current_product and not header_positions:
                # Verifique quantas palavras‑chave aparecem nesta linha
                lower_vals = [v.lower() for v in row_vals]
                score = 0
                for keywords in header_keywords.values():
                    if any(kw in ' '.join(lower_vals) for kw in keywords):
                        score += 1
                # Se pelo menos três categorias foram identificadas, tratamos como cabeçalho
                if score >= 3:
                    header_positions = {}
                    for idx, v in enumerate(lower_vals):
                        for canon, keywords in header_keywords.items():
                            if any(k in v for k in keywords):
                                header_positions[canon] = idx
                                break
                    continue
            # Linhas de dados
            if current_product and header_positions:
                # Se a coluna de data estiver presente, use‑a para validar se é linha de dados
                date_idx = header_positions.get('date')
                date_val = row_vals[date_idx] if date_idx is not None and date_idx < len(row_vals) else ''
                parsed_date = self._parse_date(date_val)
                if not parsed_date:
                    # Linha de resumo ou vazia; ignore
                    continue
                # Obter outros campos conforme mapeamento; use get para evitar índices fora de alcance
                def get_field(field: str) -> str:
                    idx = header_positions.get(field)
                    return row_vals[idx] if idx is not None and idx < len(row_vals) else ''

                transaction = {
                    'product': current_product,
                    'date': parsed_date,
                    'order_id': self._parse_ean(get_field('order_id')),
                    'client': str(get_field('client')),
                    'seller': str(get_field('seller')),
                    'price': self._parse_float(get_field('price')),
                    'qty': self._parse_int(get_field('qty')),
                    'subtotal': self._parse_float(get_field('subtotal'))
                }
                # Validações básicas
                if (transaction['client'] and transaction['price'] >= 0 and transaction['qty'] != 0):
                    transaction_key = (transaction['date'], transaction['order_id'], transaction['product'], transaction['client'], transaction['qty'], transaction['price'])
                    if transaction_key not in seen_transactions:
                        transactions.append(transaction)
                        seen_transactions.add(transaction_key)
        logger.info(f"Extraídas {len(transactions)} transações (unstructured) de relatório")
        return transactions
    
    def extract_customers(self, file_path: str) -> List[Dict[str, Any]]:
        """Extrair dados de cadastro de clientes"""
        try:
            customers = []
            for chunk in self.iter_excel_rows(file_path):
                # Aplicar aliases e promover cabeçalho se necessário
                try:
                    chunk = apply_aliases(chunk, CUSTOMER_ALIASES)
                except Exception as e:
                    logger.warning(f"Erro ao aplicar aliases em clientes: {e}")

                # Se não houver coluna 'client' após alias, assumir que a primeira linha é cabeçalho
                if 'client' not in chunk.columns:
                    if len(chunk) > 1:
                        header = chunk.iloc[0]
                        new_columns = [str(h).strip() if pd.notna(h) else f'col_{i}' for i, h in enumerate(header)]
                        chunk = chunk.iloc[1:].copy()
                        chunk.columns = new_columns
                        try:
                            chunk = apply_aliases(chunk, CUSTOMER_ALIASES)
                        except Exception as e:
                            logger.warning(f"Erro ao aplicar aliases em clientes após promover cabeçalho: {e}")

                for _, row in chunk.iterrows():
                    nome = str(row.get('client') or '').strip()
                    if not nome:
                        continue
                    customers.append({
                        "name": nome,
                        "cnpj": str(row.get('cnpj') or '').strip(),
                        "ie": str(row.get('ie') or '').strip(),
                        "uf": str(row.get('uf') or '').strip().upper(),
                        "city": str(row.get('city') or '').strip(),
                        "created_at": datetime.now()
                    })
            return customers
        except Exception as e:
            logger.error(f"Erro ao extrair clientes de {file_path}: {e}")
            return []
    
    def _parse_date(self, value: Any) -> Optional[datetime]:
        try:
            # Valor nulo ou NaN
            if value is None or (pd.isna(value) if 'pd' in globals() else False):
                return None
            # Já é datetime
            if isinstance(value, datetime):
                return value
            # Converter string/data para datetime, assumindo dia primeiro (formato dd/mm/YYYY)
            dt = pd.to_datetime(value, errors="coerce", dayfirst=True)
            # pd.to_datetime retorna NaT em caso de erro; trate como None
            if pd.isna(dt):
                return None
            return dt.to_pydatetime()
        except Exception:
            return None

    def _parse_float(self, value: Any) -> float:
        """Converter valores para float considerando formatos locais.

        Aceita números já numéricos, strings com ponto ou vírgula como separador decimal e
        strings com separadores de milhares. A heurística considera que se tanto vírgula
        quanto ponto estiverem presentes e a última vírgula estiver depois do último ponto,
        então a vírgula é o separador decimal e o ponto é o separador de milhares (como
        em "1.234,56"). Se houver apenas vírgula, assume‑se que ela é o separador
        decimal ("123,45" → 123.45). Caso contrário, o ponto é tratado como separador
        decimal.
        """
        if value is None or (pd.isna(value) if 'pd' in globals() else False):
            return 0.0
        try:
            # Se já é número, converta diretamente
            if isinstance(value, (int, float)):
                return float(value)
            s = str(value).strip()
            # Caso contenha tanto ponto quanto vírgula, determine qual é decimal
            if "," in s and "." in s and s.rfind(",") > s.rfind("."):
                s = s.replace(".", "").replace(",", ".")
            # Caso contenha apenas vírgula
            elif "," in s and "." not in s:
                s = s.replace(",", ".")
            # Caso contrário, mantém s (ponto como separador decimal)
            return float(s)
        except Exception:
            return 0.0

    def _parse_int(self, value: Any) -> int:
        if value is None or (pd.isna(value) if 'pd' in globals() else False):
            return 0
        try:
            # Tratar strings com vírgula/ponto como decimais e converter para int
            if isinstance(value, str):
                s = value.strip()
                if "," in s and "." in s and s.rfind(",") > s.rfind("."):
                    s = s.replace(".", "").replace(",", ".")
                elif "," in s and "." not in s:
                    s = s.replace(",", ".")
                return int(float(s))
            return int(float(value))
        except Exception:
            return 0



    def iter_excel_rows(self, file_path: str, sheet_name=0, chunksize=50000):
        """
        Ler um arquivo Excel e retornar pedaços (chunks) do DataFrame.

        Por padrão, usa a primeira linha como cabeçalho para permitir mapeamento de alias.
        Caso as colunas venham sem cabeçalho (numéricas), as funções de alias
        convertem os nomes para string internamente para evitar erros.
        Utiliza `chunksize` para permitir processamento incremental de arquivos grandes.
        """
        import pandas as pd
        # Tenta ler a planilha usando a primeira linha como cabeçalho
        # Se a planilha não tiver cabeçalho, os nomes das colunas serão numerados (0,1,2,..)
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        # Se houver linhas totalmente vazias, remove
        if df.empty:
            return
        n = df.shape[0]
        for start in range(0, n, chunksize):
            yield df.iloc[start:start+chunksize].copy()



    def _parse_ean(self, value: Any) -> str:
        if pd.isna(value):
            return ''
        s = str(value).strip()
        if re.match(r'^\d{12,14}$', s): # EAN-13 or similar
            return s
        if re.match(r'^\d+\.\d+E\+\d+$', s): # Excel scientific notation
            return str(int(float(s)))
        return s




    def _is_noise_row(self, row: pd.Series) -> bool:
        # Critérios para identificar linhas de ruído
        # Exemplo: linhas onde 'client' e 'product' são NaN, ou que contêm padrões de 'total'
        return pd.isna(row.get('client')) and pd.isna(row.get('product')) or \
               any(re.search(r'total|subtotal', str(v), re.IGNORECASE) for v in row.values)


