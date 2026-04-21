import unittest
from unittest.mock import Mock

from avaliacao_scrap import _extract_imdb_from_json_ld, _extract_imdb_from_next_data, _extract_og_image
from bs4 import BeautifulSoup
from fuzzy_recommender import (
    analyze_movie_from_portuguese_title,
    classify_movie,
    parse_box_office,
    parse_rating,
    parse_vote_count,
    resolve_lookup_title,
)
from movies.presentation import friendly_error_message


class FuzzyRecommenderTests(unittest.TestCase):
    def test_masterpiece_when_rating_is_excellent_and_votes_are_high(self) -> None:
        result = classify_movie(9.1, 1_200_000, 45_000_000)

        self.assertEqual(result.label, "obra-prima")
        self.assertGreaterEqual(result.score, 85.0)

    def test_good_experience_for_well_rated_niche_movie(self) -> None:
        result = classify_movie(8.3, 18_000, 6_000_000)

        self.assertEqual(result.label, "boa experiencia")
        self.assertGreaterEqual(result.score, 60.0)
        self.assertLess(result.score, 80.0)

    def test_acclaimed_movie_reaches_masterpiece_with_high_votes(self) -> None:
        result = classify_movie(8.2, 420_000, 380_000_000)

        self.assertEqual(result.label, "obra-prima")
        self.assertGreaterEqual(result.score, 76.0)

    def test_blockbuster_with_average_rating_does_not_become_good(self) -> None:
        result = classify_movie(6.1, 900_000, 1_100_000_000)

        self.assertEqual(result.label, "mediano")
        self.assertLess(result.score, 62.0)

    def test_solid_blockbuster_stays_good_without_becoming_masterpiece(self) -> None:
        result = classify_movie(7.5, 650_000, 750_000_000)

        self.assertEqual(result.label, "boa experiencia")
        self.assertGreaterEqual(result.score, 62.0)
        self.assertLess(result.score, 76.0)

    def test_low_rating_remains_waste_of_time_even_with_big_box_office(self) -> None:
        result = classify_movie(4.8, 700_000, 950_000_000)

        self.assertEqual(result.label, "perda de tempo")
        self.assertLess(result.score, 35.0)

    def test_overlap_zone_now_resolves_to_median_without_low_rating_short_circuit(self) -> None:
        result = classify_movie(5.8, 50_000, 800_000_000)

        self.assertEqual(result.label, "mediano")
        self.assertEqual(result.score, 44.0)
        self.assertTrue(
            any(rule.name == "sucesso_comercial_sem_aclamacao" for rule in result.activated_rules)
        )

    def test_excellent_with_few_votes_is_promising_but_not_masterpiece_yet(self) -> None:
        result = classify_movie(9.0, 1_500, 3_000_000)

        self.assertEqual(result.label, "boa experiencia")
        self.assertGreaterEqual(result.score, 62.0)
        self.assertLess(result.score, 85.0)

    def test_public_and_critical_hit_can_reach_masterpiece_from_7_8_rating(self) -> None:
        result = classify_movie(7.8, 1_200_000, 2_200_000_000)

        self.assertEqual(result.label, "obra-prima")
        self.assertGreaterEqual(result.score, 80.0)

    def test_parsers_accept_scraped_formats(self) -> None:
        self.assertEqual(parse_box_office("$123.4M"), 123_400_000.0)
        self.assertEqual(parse_rating("8.7"), 8.7)
        self.assertEqual(parse_vote_count("1,234,567"), 1_234_567)

    def test_parse_rating_rejects_na(self) -> None:
        with self.assertRaisesRegex(ValueError, "indisponivel"):
            parse_rating("N/A")

    def test_classification_rejects_missing_rating(self) -> None:
        with self.assertRaisesRegex(ValueError, "indisponivel"):
            classify_movie("N/A", 1_234, 5_000_000)

    def test_portuguese_title_is_translated_before_scrapers(self) -> None:
        translator = Mock(return_value="Avengers: Endgame")
        imdb_fetcher = Mock(
            return_value={
                "nome": "Avengers: Endgame",
                "nota": "8.4",
                "num_avaliacoes": "1,300,000",
                "poster_url": "https://image.tmdb.org/mock-poster.jpg",
            }
        )
        box_office_fetcher = Mock(return_value="$2.799B")

        result = analyze_movie_from_portuguese_title(
            movie_title_pt="Vingadores: Ultimato",
            translator=translator,
            imdb_fetcher=imdb_fetcher,
            box_office_fetcher=box_office_fetcher,
        )

        translator.assert_called_once_with("Vingadores: Ultimato")
        imdb_fetcher.assert_called_once_with("Avengers: Endgame")
        box_office_fetcher.assert_called_once_with("Avengers: Endgame")
        self.assertEqual(result.translated_title_en, "Avengers: Endgame")
        self.assertEqual(result.classification.label, "obra-prima")

    def test_resolve_lookup_title_raises_when_translator_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "Nao foi possivel traduzir o titulo"):
            resolve_lookup_title(
                "Velozes e Furiosos 9",
                Mock(side_effect=RuntimeError("timeout")),
            )

    def test_resolve_lookup_title_raises_when_translation_is_empty(self) -> None:
        with self.assertRaisesRegex(ValueError, "Nao foi possivel traduzir o titulo"):
            resolve_lookup_title(
                "Velozes e Furiosos 9",
                Mock(return_value="  "),
            )

    def test_analysis_raises_specific_message_when_imdb_page_cannot_be_parsed(self) -> None:
        with self.assertRaisesRegex(ValueError, "Falha ao ler dados do IMDb"):
            analyze_movie_from_portuguese_title(
                movie_title_pt="Titanic",
                translator=Mock(return_value="Titanic"),
                imdb_fetcher=Mock(
                    return_value=(
                        "Encontramos a pagina do filme no IMDb, mas nao foi possivel extrair "
                        "nota e numero de avaliacoes."
                    )
                ),
                box_office_fetcher=Mock(return_value="$100M"),
            )

    def test_friendly_error_message_explains_when_imdb_movie_was_found_but_not_parsed(self) -> None:
        message = friendly_error_message(
            ValueError(
                "Falha ao ler dados do IMDb: Encontramos a pagina do filme no IMDb, "
                "mas nao foi possivel extrair nota e numero de avaliacoes."
            )
        )

        self.assertIn("Encontramos o filme no IMDb", message)
        self.assertIn("nao conseguimos ler nota e avaliacoes", message)

    def test_extract_imdb_from_json_ld_uses_movie_payload_instead_of_first_script(self) -> None:
        soup = BeautifulSoup(
            """
            <html>
                <head>
                    <script type="application/ld+json">
                        {"@type": "BreadcrumbList", "name": "Breadcrumb"}
                    </script>
                    <script type="application/ld+json">
                        {"@type": "Movie", "name": "Titanic", "image": "https://images.example/titanic.jpg", "aggregateRating": {"ratingValue": 7.9, "ratingCount": 1200000}}
                    </script>
                </head>
            </html>
            """,
            "html.parser",
        )

        self.assertEqual(
            _extract_imdb_from_json_ld(soup),
            {
                "nome": "Titanic",
                "nota": "7.9",
                "num_avaliacoes": "1200000",
                "poster_url": "https://images.example/titanic.jpg",
            },
        )

    def test_extract_imdb_from_next_data_as_fallback(self) -> None:
        soup = BeautifulSoup(
            """
            <html>
                <head>
                    <script id="__NEXT_DATA__" type="application/json">
                        {
                            "props": {
                                "pageProps": {
                                    "aboveTheFoldData": {
                                        "titleText": {"text": "Titanic"},
                                        "primaryImage": {"url": "https://images.example/titanic-next.jpg"},
                                        "ratingsSummary": {
                                            "aggregateRating": 7.9,
                                            "voteCount": 1200000
                                        }
                                    }
                                }
                            }
                        }
                    </script>
                </head>
            </html>
            """,
            "html.parser",
        )

        self.assertEqual(
            _extract_imdb_from_next_data(soup),
            {
                "nome": "Titanic",
                "nota": "7.9",
                "num_avaliacoes": "1200000",
                "poster_url": "https://images.example/titanic-next.jpg",
            },
        )

    def test_extract_og_image_reads_fallback_meta_tag(self) -> None:
        soup = BeautifulSoup(
            """
            <html>
                <head>
                    <meta property="og:image" content="https://images.example/titanic-og.jpg">
                </head>
            </html>
            """,
            "html.parser",
        )

        self.assertEqual(_extract_og_image(soup), "https://images.example/titanic-og.jpg")


if __name__ == "__main__":
    unittest.main()
