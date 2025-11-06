import os
from pymongo import MongoClient, ASCENDING
from dotenv import load_dotenv

load_dotenv()

class Database:
    _instance = None
    _client = None
    _db = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self.connect()
    
    def connect(self):
        """Abrir conexão e garantir índices"""
        # Se já existe uma instância do banco, simplesmente retorne-a
        # Comparar explicitamente com None evita avaliação booleana de objetos Database,
        # que o PyMongo não suporta (ver NotImplementedError em bool()).
        if self._db is not None:
            return self._db
        mongo_uri = os.getenv("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.getenv("DB_NAME", "ipro")
        self._client = MongoClient(mongo_uri)
        self._db = self._client[db_name]

        # Índices essenciais
        self._db.datasets.create_index([("created_at", ASCENDING)])
        self._db.datasets.create_index([("hash", ASCENDING)], unique=True)

        self._db.transactions.create_index([("dataset_id", ASCENDING)])
        self._db.transactions.create_index([("client", ASCENDING)])
        self._db.transactions.create_index([("sku", ASCENDING)])
        self._db.transactions.create_index([("date", ASCENDING)])
        self._db.transactions.create_index([("dataset_id", ASCENDING), ("date", ASCENDING)], name="dataset_date_idx")
        self._db.transactions.create_index([("client", ASCENDING), ("sku", ASCENDING)], name="client_sku_idx")

        self._db.analytics_customer.create_index([("dataset_id", ASCENDING)])
        self._db.analytics_customer.create_index([("client", ASCENDING)])

        self._db.analytics_product.create_index([("dataset_id", ASCENDING)])
        self._db.analytics_product.create_index([("sku", ASCENDING)])

        # Evita duplicidade da mesma linha de venda
        self._db.transactions.create_index(
            [("dataset_id", ASCENDING), ("order_id", ASCENDING), ("sku", ASCENDING), ("date", ASCENDING)],
            unique=True, name="uniq_tx_dataset_order_sku_date"
        )

        # Protege reprocessamento do mesmo arquivo
        self._db.datasets.create_index([("dataset_id", ASCENDING), ("hash", ASCENDING)], unique=True, name="uniq_dataset_hash")

        return self._db

    @property
    def db(self):
        """
        Obter a instância do banco.
        Retorna a instância existente se já estiver criada; caso contrário, cria uma nova
        conexão chamando `connect()`. Comparar com None evita a avaliação booleana
        do objeto Database, que não implementa `__bool__`.
        """
        if self._db is None:
            return self.connect()
        return self._db
    
    def close(self):
        """Fechar a conexão"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None

# Instância global do banco
db_instance = Database()

def get_db():
    """Função para obter a instância do banco"""
    return db_instance.db

