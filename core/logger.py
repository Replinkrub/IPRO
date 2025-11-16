import logging
import os
import sys
import uuid


class RequestIDFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


logger = logging.getLogger("ipro")
logger.setLevel(
    logging.INFO if os.getenv("PRODUCTION_ENV") != "true" else logging.WARNING
)

if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
    handler = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(request_id)s | %(name)s | %(message)s"
    )
    handler.setFormatter(fmt)
    logger.addHandler(handler)

if not any(isinstance(f, RequestIDFilter) for f in logger.filters):
    logger.addFilter(RequestIDFilter())


def new_request_id():
    return str(uuid.uuid4())
