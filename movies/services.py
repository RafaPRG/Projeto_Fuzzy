from __future__ import annotations

from typing import Callable

from fuzzy_recommender import (
    MovieAnalysisResult,
    analyze_movie_from_lookup_title,
    resolve_lookup_title,
)


def _emit_log(logger: Callable[[str], None] | None, message: str) -> None:
    print(message, flush=True)
    if logger is not None:
        logger(message)


def analyze_movie_submission(
    movie_title_pt: str,
    logger: Callable[[str], None] | None = None,
) -> MovieAnalysisResult:
    from agente import translate_title_to_english
    from avaliacao_scrap import get_imdb_rating_robust
    from bilheteria_scrap import get_worldwide_box_office

    _emit_log(logger, f"Traduzindo titulo para a busca: {movie_title_pt}...")
    lookup_title = resolve_lookup_title(movie_title_pt, translate_title_to_english)
    _emit_log(logger, f"Titulo em ingles encontrado: {lookup_title}")

    analysis = analyze_movie_from_lookup_title(
        movie_title_pt=movie_title_pt,
        lookup_title=lookup_title,
        imdb_fetcher=lambda title: get_imdb_rating_robust(title, logger=logger),
        box_office_fetcher=lambda title: get_worldwide_box_office(title, logger=logger),
    )
    _emit_log(logger, "Analise fuzzy concluida.")
    return analysis
