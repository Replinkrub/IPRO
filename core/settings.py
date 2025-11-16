import os
from decimal import ROUND_HALF_UP, getcontext
from zoneinfo import ZoneInfo

# Fusos horários padrão
APP_TZ = ZoneInfo("America/Sao_Paulo")
UTC_TZ = ZoneInfo("UTC")

# Dinheiro: 2 casas, arredondamento comercial
ctx = getcontext()
ctx.prec = 28
ctx.rounding = ROUND_HALF_UP

# Banco de dados
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "ipro")

# Processamento de datasets
MAX_INSERT_BATCH = int(os.getenv("MAX_INSERT_BATCH", "5000"))
CHUNK_ROWS = int(os.getenv("CHUNK_ROWS", "50000"))
