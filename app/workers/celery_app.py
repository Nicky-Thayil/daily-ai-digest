"""
Celery application instance configured with Upstash Redis broker and backend.
"""

import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    raise RuntimeError("REDIS_URL is not set in .env")

# Append SSL cert requirement directly to URL as required by Celery's Redis backend
REDIS_URL_SSL = REDIS_URL.rstrip("/") + "?ssl_cert_reqs=CERT_NONE"

celery_app = Celery(
    "ai_digest",
    broker=REDIS_URL_SSL,
    backend=REDIS_URL_SSL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    broker_connection_retry_on_startup=True,
)

celery_app.autodiscover_tasks(["app.workers"])