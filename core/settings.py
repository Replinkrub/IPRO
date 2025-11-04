import os
from zoneinfo import ZoneInfo
from decimal import getcontext, ROUND_HALF_UP

APP_TZ = ZoneInfo("America/Sao_Paulo")
UTC_TZ = ZoneInfo("UTC")

# Dinheiro: 2 casas, arredondamento comercial
ctx = getcontext()
ctx.prec = 28
ctx.rounding = ROUND_HALF_UP

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "ipro")
MAX_INSERT_BATCH = int(os.getenv("MAX_INSERT_BATCH", "5000"))
CHUNK_ROWS = int(os.getenv("CHUNK_ROWS", "50000"))

