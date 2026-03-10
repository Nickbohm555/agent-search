from __future__ import annotations

import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Optional

from db import SessionLocal
from schemas import InternalDataLoadRequest, InternalDataLoadResponse
from services.internal_data_service import InternalDataLoadCancelled, load_internal_data

logger = logging.getLogger(__name__)


@dataclass
class InternalDataJobStatus:
    job_id: str
    status: str
    total: int = 0
    completed: int = 0
    message: str = ""
    error: Optional[str] = None
    response: Optional[InternalDataLoadResponse] = None
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None


_JOB_LOCK = threading.Lock()
_JOBS: dict[str, InternalDataJobStatus] = {}
_CANCEL_FLAGS: dict[str, threading.Event] = {}
_EXECUTOR = ThreadPoolExecutor(max_workers=2)


def start_internal_data_job(payload: InternalDataLoadRequest) -> InternalDataJobStatus:
    job_id = str(uuid.uuid4())
    status = InternalDataJobStatus(job_id=job_id, status="running", message="Starting...")
    cancel_event = threading.Event()
    with _JOB_LOCK:
        _JOBS[job_id] = status
        _CANCEL_FLAGS[job_id] = cancel_event

    _EXECUTOR.submit(_run_internal_data_job, job_id, payload)
    return status


def get_internal_data_job(job_id: str) -> Optional[InternalDataJobStatus]:
    with _JOB_LOCK:
        return _JOBS.get(job_id)


def cancel_internal_data_job(job_id: str) -> bool:
    with _JOB_LOCK:
        cancel_event = _CANCEL_FLAGS.get(job_id)
        status = _JOBS.get(job_id)
        if cancel_event is None or status is None:
            return False
        cancel_event.set()
        if status.status in {"success", "error", "cancelled"}:
            return False
        status.status = "cancelling"
        status.message = "Cancelling..."
        return True


def _run_internal_data_job(job_id: str, payload: InternalDataLoadRequest) -> None:
    status = get_internal_data_job(job_id)
    if status is None:
        return

    def progress_cb(completed: int, total: int, message: str) -> None:
        with _JOB_LOCK:
            status.completed = completed
            status.total = total
            status.message = message

    def cancel_cb() -> bool:
        with _JOB_LOCK:
            cancel_event = _CANCEL_FLAGS.get(job_id)
            return bool(cancel_event and cancel_event.is_set())

    try:
        with SessionLocal() as session:
            response = load_internal_data(payload, session, progress_cb=progress_cb, cancel_cb=cancel_cb)
        with _JOB_LOCK:
            status.status = "success"
            status.response = response
            status.finished_at = time.time()
            status.message = status.message or "Completed."
    except InternalDataLoadCancelled:
        with _JOB_LOCK:
            status.status = "cancelled"
            status.finished_at = time.time()
            status.message = "Cancelled."
    except Exception as exc:  # noqa: BLE001
        logger.exception("Internal data job failed job_id=%s", job_id)
        with _JOB_LOCK:
            status.status = "error"
            status.error = str(exc)
            status.finished_at = time.time()
            status.message = "Failed."
