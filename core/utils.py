from decimal import Decimal
from zoneinfo import ZoneInfo
from datetime import datetime
from core.settings import APP_TZ, UTC_TZ

def as_decimal(v) -> Decimal:
    if v is None or v == "": return Decimal("0.00")
    s = str(v).strip()
    if "," in s and "." in s and s.rfind(",") > s.rfind("."):
        s = s.replace(".", "").replace(",", ".")
    elif "," in s and "." not in s:
        s = s.replace(",", ".")
    return Decimal(s).quantize(Decimal("0.01"))

def to_utc(dt: datetime) -> datetime:
    if dt is None: return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=APP_TZ)
    return dt.astimezone(UTC_TZ)

def utc_now() -> datetime:
    return datetime.now(tz=UTC_TZ)


