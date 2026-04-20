from __future__ import annotations

from django.shortcuts import render

from .forms import MovieSearchForm
from .presentation import build_dashboard_context, friendly_error_message
from .services import analyze_movie_submission


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
