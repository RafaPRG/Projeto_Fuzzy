from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock, Thread
from time import time
from typing import Any
from uuid import uuid4

from .presentation import build_dashboard_context, friendly_error_message
from .services import analyze_movie_submission


@dataclass
class MovieJob:
    job_id: str
    movie_title: str
    status: str = "running"
    logs: list[str] = field(default_factory=list)
    result_context: dict[str, Any] | None = None
    error_message: str | None = None
    updated_at: float = field(default_factory=time)


_jobs: dict[str, MovieJob] = {}
_jobs_lock = Lock()
_JOB_TTL_SECONDS = 60 * 30


def _prune_finished_jobs() -> None:
    now = time()
    expired_job_ids = [
        job_id
        for job_id, job in _jobs.items()
        if job.status in {"success", "error"} and now - job.updated_at > _JOB_TTL_SECONDS
    ]
    for job_id in expired_job_ids:
        _jobs.pop(job_id, None)


def _append_log(job_id: str, message: str) -> None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        job.logs.append(message)
        job.updated_at = time()


def _finish_job(
    job_id: str,
    *,
    status: str,
    result_context: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        job.status = status
        job.result_context = result_context
        job.error_message = error_message
        job.updated_at = time()


def _run_job(job_id: str, movie_title: str) -> None:
    logger = lambda message: _append_log(job_id, message)
    try:
        analysis = analyze_movie_submission(movie_title, logger=logger)
    except (ImportError, ValueError) as exc:
        _finish_job(
            job_id,
            status="error",
            error_message=friendly_error_message(exc),
        )
    except Exception as exc:  # pragma: no cover - defensive async fallback
        _finish_job(
            job_id,
            status="error",
            error_message=friendly_error_message(exc),
        )
    else:
        _finish_job(
            job_id,
            status="success",
            result_context=build_dashboard_context(analysis),
        )


def start_movie_job(movie_title: str) -> str:
    job_id = uuid4().hex

    with _jobs_lock:
        _prune_finished_jobs()
        _jobs[job_id] = MovieJob(
            job_id=job_id,
            movie_title=movie_title,
            logs=[f'Iniciando busca para "{movie_title}"...'],
        )

    worker = Thread(target=_run_job, args=(job_id, movie_title), daemon=True)
    worker.start()
    return job_id


def get_movie_job(job_id: str) -> MovieJob | None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            return None
        return MovieJob(
            job_id=job.job_id,
            movie_title=job.movie_title,
            status=job.status,
            logs=list(job.logs),
            result_context=dict(job.result_context) if job.result_context is not None else None,
            error_message=job.error_message,
            updated_at=job.updated_at,
        )
