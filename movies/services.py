from __future__ import annotations

from fuzzy_recommender import MovieAnalysisResult, analyze_movie_from_portuguese_title


def analyze_movie_submission(movie_title_pt: str) -> MovieAnalysisResult:
    from agente import translate_title_to_english
    from avaliacao_scrap import get_imdb_rating_robust
    from bilheteria_scrap import get_worldwide_box_office

    return analyze_movie_from_portuguese_title(
        movie_title_pt=movie_title_pt,
        translator=translate_title_to_english,
        imdb_fetcher=get_imdb_rating_robust,
        box_office_fetcher=get_worldwide_box_office,
    )
