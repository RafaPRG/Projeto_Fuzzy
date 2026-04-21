from __future__ import annotations

from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_POST

from .forms import MovieSearchForm
from .jobs import get_movie_job, start_movie_job
from .presentation import build_dashboard_context, friendly_error_message
from .services import analyze_movie_submission


def _render_response_panel(
    request,
    *,
    result: dict | None = None,
    error_message: str | None = None,
) -> str:
    return render_to_string(
        "movies/_response_panel.html",
        {
            "result": result,
            "error_message": error_message,
        },
        request=request,
    )


def home(request):
    result = None
    error_message = None

    if request.method == "POST":
        form = MovieSearchForm(request.POST)
        if form.is_valid():
            movie_title = form.cleaned_data["movie_title_pt"]
            try:
                analysis = analyze_movie_submission(movie_title)
            except (ImportError, ValueError) as exc:
                error_message = friendly_error_message(exc)
            except Exception as exc:  # pragma: no cover - defensive UI fallback
                error_message = friendly_error_message(exc)
            else:
                result = build_dashboard_context(analysis)
        else:
            error_message = "Digite um titulo valido antes de iniciar a busca."
    else:
        form = MovieSearchForm()

    return render(
        request,
        "movies/home.html",
        {
            "form": form,
            "result": result,
            "error_message": error_message,
        },
    )


@require_POST
def start_analysis(request):
    form = MovieSearchForm(request.POST)
    if not form.is_valid():
        return JsonResponse(
            {
                "error_message": "Digite um titulo valido antes de iniciar a busca.",
            },
            status=400,
        )

    movie_title = form.cleaned_data["movie_title_pt"]
    job_id = start_movie_job(movie_title)
    return JsonResponse({"job_id": job_id})


@require_GET
def analysis_status(request, job_id: str):
    job = get_movie_job(job_id)
    if job is None:
        return JsonResponse(
            {"error_message": "A busca nao foi encontrada ou expirou."},
            status=404,
        )

    is_done = job.status in {"success", "error"}
    payload = {
        "job_id": job.job_id,
        "status": job.status,
        "logs": job.logs,
        "done": is_done,
    }

    if job.status == "success" and job.result_context is not None:
        payload["html"] = _render_response_panel(
            request,
            result=job.result_context,
            error_message=None,
        )
    elif job.status == "error":
        payload["html"] = _render_response_panel(
            request,
            result=None,
            error_message=job.error_message,
        )

    return JsonResponse(payload)
