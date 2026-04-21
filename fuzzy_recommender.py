from __future__ import annotations

from dataclasses import dataclass
from math import exp, log10
import re
from typing import Any, Callable


def triangular(x: float, a: float, b: float, c: float) -> float:
    if x <= a or x >= c:
        return 0.0
    if x == b:
        return 1.0
    if x < b:
        return (x - a) / (b - a)
    return (c - x) / (c - b)


def trapezoidal(x: float, a: float, b: float, c: float, d: float) -> float:
    if x < a or x > d:
        return 0.0
    if b <= x <= c:
        return 1.0
    if x < b:
        if b == a:
            return 1.0
        return (x - a) / (b - a)
    if d == c:
        return 1.0
    return (d - x) / (d - c)


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def sigmoid(x: float, midpoint: float, steepness: float) -> float:
    return 1.0 / (1.0 + exp(-steepness * (x - midpoint)))


def parse_rating(value: float | int | str) -> float:
    if isinstance(value, (int, float)):
        return float(value)

    cleaned = value.strip().replace(",", ".")
    if cleaned.upper() == "N/A" or not cleaned:
        raise ValueError("Nota IMDb indisponivel para classificacao.")

    try:
        return float(cleaned)
    except ValueError as exc:
        raise ValueError(f"Nota IMDb invalida: {value!r}") from exc


def parse_box_office(value: float | int | str) -> float:
    if isinstance(value, (int, float)):
        return float(value)

    cleaned = value.strip().replace(",", "")
    match = re.fullmatch(r"\$?([\d.]+)\s*([kmbKMB]?)", cleaned)
    if not match:
        raise ValueError(f"Bilheteria invalida: {value!r}")

    amount = float(match.group(1))
    suffix = match.group(2).lower()
    multiplier = {
        "": 1.0,
        "k": 1_000.0,
        "m": 1_000_000.0,
        "b": 1_000_000_000.0,
    }[suffix]
    return amount * multiplier


def parse_vote_count(value: float | int | str) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)

    digits = re.sub(r"[^\d]", "", value)
    if not digits:
        raise ValueError(f"Quantidade de avaliacoes invalida: {value!r}")
    return int(digits)


@dataclass(frozen=True)
class RuleHit:
    name: str
    strength: float
    output: str


@dataclass(frozen=True)
class FuzzyClassification:
    label: str
    score: float
    memberships: dict[str, dict[str, float]]
    activated_rules: list[RuleHit]


@dataclass(frozen=True)
class MovieAnalysisResult:
    original_title_pt: str
    translated_title_en: str
    imdb_result: dict[str, Any]
    box_office_result: str
    classification: FuzzyClassification


class MovieFuzzyRecommender:
    OUTPUT_CENTROIDS = {
        "perda_de_tempo": 12.0,
        "mediano": 44.0,
        "boa_experiencia": 72.0,
        "obra_prima": 92.0,
    }

    def classify(
        self,
        rating: float,
        rating_count: int | float | str,
        box_office_usd: float | int | str,
    ) -> FuzzyClassification:
        rating = clamp(parse_rating(rating), 0.0, 10.0)
        rating_count = max(parse_vote_count(rating_count), 0)
        box_office_usd = max(parse_box_office(box_office_usd), 0.0)

        memberships = {
            "rating": self._rating_memberships(rating),
            "votes": self._votes_memberships(rating_count),
            "box_office": self._box_office_memberships(box_office_usd),
        }

        rule_hits = self._evaluate_rules(rating, memberships)
        score = self._defuzzify(rule_hits)
        label = self._label_from_score(score)

        return FuzzyClassification(
            label=label,
            score=score,
            memberships=memberships,
            activated_rules=sorted(rule_hits, key=lambda hit: hit.strength, reverse=True),
        )

    def _rating_memberships(self, rating: float) -> dict[str, float]:
        return {
            "baixa": trapezoidal(rating, 0.0, 0.0, 4.0, 5.0),
            "media": triangular(rating, 4.5, 6.0, 7.2),
            "alta": triangular(rating, 6.5, 7.4, 8.2),
            "excelente": trapezoidal(rating, 7.5, 8.2, 10.0, 10.0),
        }

    def _votes_memberships(self, votes: int) -> dict[str, float]:
        log_votes = log10(votes + 1)
        return {
            "baixa": trapezoidal(log_votes, 0.0, 0.0, 3.8, 4.5),
            "media": triangular(log_votes, 4.1, 4.9, 5.7),
            "alta": triangular(log_votes, 5.3, 6.0, 6.8),
            "massiva": trapezoidal(log_votes, 6.1, 6.5, 7.4, 7.4),
        }

    def _box_office_memberships(self, box_office_usd: float) -> dict[str, float]:
        box_office_musd = box_office_usd / 1_000_000.0
        return {
            "baixa": trapezoidal(box_office_musd, 0.0, 0.0, 40.0, 140.0),
            "media": triangular(box_office_musd, 80.0, 220.0, 450.0),
            "alta": triangular(box_office_musd, 300.0, 550.0, 850.0),
            "blockbuster": sigmoid(box_office_musd, midpoint=400.0, steepness=0.01),
        }

    def _evaluate_rules(
        self,
        rating_value: float,
        memberships: dict[str, dict[str, float]],
    ) -> list[RuleHit]:
        rating = memberships["rating"]
        votes = memberships["votes"]
        box_office = memberships["box_office"]

        def strength(*values: float) -> float:
            return min(values)

        rating_high_gate = 1.0 if rating_value > 7.0 else 0.0

        rules = [
            RuleHit(
                "nota_baixa_domina",
                rating["baixa"],
                "perda_de_tempo",
            ),
            RuleHit(
                "blockbuster_sem_qualidade_nao_salva",
                max(
                    strength(rating["baixa"], box_office["alta"]),
                    strength(rating["baixa"], box_office["blockbuster"]),
                ),
                "perda_de_tempo",
            ),
            RuleHit(
                "nota_media_com_pouca_amostra",
                strength(rating["media"], votes["baixa"]),
                "mediano",
            ),
            RuleHit(
                "nota_media_consenso",
                max(
                    strength(rating["media"], votes["media"]),
                    strength(rating["media"], votes["alta"]),
                    strength(rating["media"], votes["massiva"]),
                ),
                "mediano",
            ),
            RuleHit(
                "sucesso_comercial_sem_aclamacao",
                max(
                    strength(rating["media"], box_office["alta"]),
                    strength(rating["media"], box_office["blockbuster"]),
                ),
                "mediano",
            ),
            RuleHit(
                "nota_alta_com_pouca_amostra",
                strength(rating["alta"], votes["baixa"]),
                "boa_experiencia",
            ),
            RuleHit(
                "nota_alta_com_consenso",
                max(
                    strength(rating["alta"], votes["media"]),
                    strength(rating["alta"], votes["alta"]),
                    strength(rating["alta"], votes["massiva"]),
                ),
                "boa_experiencia",
            ),
            RuleHit(
                "nota_alta_reforcada_por_bilheteria",
                max(
                    strength(rating["alta"], box_office["alta"]),
                    strength(rating["alta"], box_office["blockbuster"]),
                ),
                "boa_experiencia",
            ),
            RuleHit(
                "excelente_mas_pouca_amostra",
                strength(rating["excelente"], votes["baixa"]),
                "boa_experiencia",
            ),
            RuleHit(
                "excelente_de_nicho_com_boas_avaliacoes",
                strength(rating["excelente"], votes["media"], box_office["baixa"]),
                "boa_experiencia",
            ),
            RuleHit(
                "excelente_e_blockbuster",
                strength(rating["excelente"], box_office["blockbuster"]),
                "obra_prima",
            ),
            RuleHit(
                "excelente_e_votos_altos",
                max(
                    strength(rating["excelente"], votes["alta"]),
                    strength(rating["excelente"], votes["massiva"]),
                ),
                "obra_prima",
            ),
            RuleHit(
                "excelente_com_tracao_geral",
                max(
                    strength(rating["excelente"], votes["media"], box_office["alta"]),
                    strength(rating["excelente"], votes["alta"], box_office["media"]),
                    strength(rating["excelente"], votes["alta"], box_office["blockbuster"]),
                    strength(rating["excelente"], votes["media"], box_office["blockbuster"]),
                ),
                "obra_prima",
            ),
            RuleHit(
                "aclamado_blockbuster",
                strength(
                    rating["alta"],
                    votes["massiva"],
                    box_office["blockbuster"],
                    rating_high_gate,
                ),
                "obra_prima",
            ),
            RuleHit(
                "baixa_bilheteria_nao_pune_excelencia",
                strength(rating["excelente"], votes["alta"], box_office["baixa"]),
                "obra_prima",
            ),
            RuleHit(
                "filme_bom_de_nicho",
                max(
                    strength(rating["alta"], votes["media"], box_office["baixa"]),
                    strength(rating["excelente"], votes["baixa"], box_office["baixa"]),
                ),
                "boa_experiencia",
            ),
        ]

        return [rule for rule in rules if rule.strength > 0.01]

    def _output_memberships(self, score: float) -> dict[str, float]:
        return {
            "perda_de_tempo": trapezoidal(score, 0.0, 0.0, 22.0, 38.0),
            "mediano": triangular(score, 30.0, 46.0, 64.0),
            "boa_experiencia": triangular(score, 54.0, 70.0, 86.0),
            "obra_prima": trapezoidal(score, 76.0, 82.0, 100.0, 100.0),
        }

    def _defuzzify(self, rule_hits: list[RuleHit]) -> float:
        if not rule_hits:
            return 50.0

        numerator = 0.0
        denominator = 0.0
        for rule in rule_hits:
            centroid = self.OUTPUT_CENTROIDS[rule.output]
            numerator += rule.strength * centroid
            denominator += rule.strength
        return numerator / denominator

    def _label_from_score(self, score: float) -> str:
        labels = {
            "perda_de_tempo": "perda de tempo",
            "mediano": "mediano",
            "boa_experiencia": "boa experiencia",
            "obra_prima": "obra-prima",
        }
        output_memberships = self._output_memberships(score)
        best_output, _ = max(
            output_memberships.items(),
            key=lambda item: (item[1], self.OUTPUT_CENTROIDS[item[0]]),
        )
        return labels[best_output]


def classify_movie(
    rating: float,
    rating_count: int | float | str,
    box_office_usd: float | int | str,
) -> FuzzyClassification:
    return MovieFuzzyRecommender().classify(rating, rating_count, box_office_usd)


def resolve_lookup_title(
    movie_title_pt: str,
    translator: Callable[[str], str],
) -> str:
    try:
        translated_title = translator(movie_title_pt).strip()
    except Exception as exc:
        raise ValueError(
            f"Nao foi possivel traduzir o titulo para busca no IMDb: {exc}"
        ) from exc

    if not translated_title:
        raise ValueError("Nao foi possivel traduzir o titulo para busca no IMDb.")

    return translated_title


def analyze_movie_from_lookup_title(
    movie_title_pt: str,
    lookup_title: str,
    imdb_fetcher: Callable[[str], dict[str, Any] | str],
    box_office_fetcher: Callable[[str], str],
) -> MovieAnalysisResult:
    normalized_lookup_title = lookup_title.strip()
    if not normalized_lookup_title:
        raise ValueError("O titulo usado para busca retornou vazio.")

    imdb_result: Any = imdb_fetcher(normalized_lookup_title)
    if not isinstance(imdb_result, dict):
        imdb_message = str(imdb_result).strip()
        lowered_imdb_message = imdb_message.lower()

        if "nao encontrado" in lowered_imdb_message:
            raise ValueError("Filme nao encontrado no IMDb.")

        raise ValueError(f"Falha ao ler dados do IMDb: {imdb_message}")

    box_office_result = box_office_fetcher(normalized_lookup_title)
    if isinstance(box_office_result, str) and box_office_result.startswith("Erro"):
        raise ValueError(f"Erro ao buscar bilheteria: {box_office_result}")
    if box_office_result == "Nao encontrado":
        raise ValueError("Bilheteria nao encontrada no Box Office Mojo.")

    classification = classify_movie(
        rating=imdb_result["nota"],
        rating_count=imdb_result["num_avaliacoes"],
        box_office_usd=box_office_result,
    )

    return MovieAnalysisResult(
        original_title_pt=movie_title_pt,
        translated_title_en=normalized_lookup_title,
        imdb_result=imdb_result,
        box_office_result=box_office_result,
        classification=classification,
    )


def analyze_movie_from_portuguese_title(
    movie_title_pt: str,
    translator: Callable[[str], str],
    imdb_fetcher: Callable[[str], dict[str, Any] | str],
    box_office_fetcher: Callable[[str], str],
) -> MovieAnalysisResult:
    translated_title = translator(movie_title_pt).strip()
    if not translated_title:
        raise ValueError("A traducao do titulo retornou vazia.")

    return analyze_movie_from_lookup_title(
        movie_title_pt=movie_title_pt,
        lookup_title=translated_title,
        imdb_fetcher=imdb_fetcher,
        box_office_fetcher=box_office_fetcher,
    )


def _format_memberships(memberships: dict[str, dict[str, float]]) -> str:
    lines: list[str] = []
    for group_name, values in memberships.items():
        formatted_values = ", ".join(
            f"{label}={value:.2f}" for label, value in values.items() if value > 0
        )
        lines.append(f"{group_name}: {formatted_values or 'sem ativacao'}")
    return "\n".join(lines)


def _format_rules(rule_hits: list[RuleHit]) -> str:
    if not rule_hits:
        return "Nenhuma regra foi ativada."
    return "\n".join(
        f"- {rule.name}: forca={rule.strength:.2f}, saida={rule.output}"
        for rule in rule_hits
    )


def run_interactive() -> None:
    movie_title_pt = input("Digite o nome do filme em portugues: ").strip()
    if not movie_title_pt:
        print("Nenhum titulo foi informado.")
        return

    try:
        from agente import translate_title_to_english
        from avaliacao_scrap import get_imdb_rating_robust
        from bilheteria_scrap import get_worldwide_box_office
    except ImportError as exc:
        print(f"Erro ao importar dependencias do fluxo completo: {exc}")
        return

    print("\nTraduzindo titulo com IA...")
    try:
        lookup_title = resolve_lookup_title(
            movie_title_pt,
            translate_title_to_english,
        )
        print(f"Titulo em ingles: {lookup_title}")
    except ValueError as exc:
        print(str(exc))
        return

    try:
        print("\nConsultando IMDb e Box Office Mojo...")
        analysis = analyze_movie_from_lookup_title(
            movie_title_pt=movie_title_pt,
            lookup_title=lookup_title,
            imdb_fetcher=get_imdb_rating_robust,
            box_office_fetcher=get_worldwide_box_office,
        )
    except ValueError as exc:
        print(str(exc))
        return

    print("\n--- Dados coletados ---")
    print(f"Filme encontrado no IMDb: {analysis.imdb_result['nome']}")
    print(f"Nota IMDb: {analysis.imdb_result['nota']}")
    print(f"Quantidade de avaliacoes: {analysis.imdb_result['num_avaliacoes']}")
    print(f"Bilheteria mundial: {analysis.box_office_result}")

    print("\n--- Classificacao fuzzy ---")
    print(f"Rotulo: {analysis.classification.label}")
    print(f"Score: {analysis.classification.score:.2f}")

    print("\n--- Pertinencias ---")
    print(_format_memberships(analysis.classification.memberships))

    print("\n--- Regras ativadas ---")
    print(_format_rules(analysis.classification.activated_rules))


if __name__ == "__main__":
    run_interactive()
