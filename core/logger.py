import logging, sys, uuid, os

class RequestIDFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True

logger = logging.getLogger("ipro")
handler = logging.StreamHandler(sys.stdout)
fmt = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(request_id)s | %(name)s | %(message)s"
)
handler.setFormatter(fmt)
logger.setLevel(logging.INFO if os.getenv("PRODUCTION_ENV") != "true" else logging.WARNING)


logger.addHandler(handler)
logger.addFilter(RequestIDFilter())

def new_request_id(): return str(uuid.uuid4())

