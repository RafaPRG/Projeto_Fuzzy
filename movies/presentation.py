from __future__ import annotations

from typing import Any

from fuzzy_recommender import MovieAnalysisResult, parse_box_office


RULE_EXPLANATIONS = {
    "nota_baixa_domina": "A nota no IMDb caiu na faixa fraca, puxando o veredito para o lado negativo.",
    "blockbuster_sem_qualidade_nao_salva": "A bilheteria chama atencao, mas a recepcao nao sustenta uma boa recomendacao.",
    "nota_media_com_pouca_amostra": "A nota ficou morna e ainda com pouco consenso de publico.",
    "nota_media_consenso": "O filme ficou no meio-termo mesmo depois de muitas avaliacoes.",
    "sucesso_comercial_sem_aclamacao": "Fez caixa, mas a critica e o publico nao colocam o filme acima da media.",
    "nota_alta_com_pouca_amostra": "O filme parece bom, mas ainda com pouca amostragem de votos.",
    "nota_alta_com_consenso": "A nota alta se manteve mesmo com boa quantidade de avaliacoes.",
    "nota_alta_reforcada_por_bilheteria": "Boa nota e tracao comercial se combinaram a favor do filme.",
    "excelente_mas_pouca_amostra": "A nota e excelente, mas ainda sem publico suficiente para cravar um veredito maximo.",
    "excelente_de_nicho_com_boas_avaliacoes": "Mesmo sendo mais nichado, o filme sustenta uma recepcao muito forte.",
    "excelente_e_blockbuster": "O filme juntou excelencia critica com status de grande sucesso.",
    "excelente_e_votos_altos": "A nota excelente foi confirmada por um volume robusto de avaliacoes.",
    "excelente_com_tracao_geral": "O filme equilibra excelencia, alcance e consenso de publico.",
    "aclamado_blockbuster": "Sucesso massivo de publico com nota alta o bastante para entrar na elite.",
    "baixa_bilheteria_nao_pune_excelencia": "Mesmo sem bilheteria gigante, a excelencia critica manteve o veredito no topo.",
    "filme_bom_de_nicho": "Filme de nicho, mas com boa recepcao no publico certo.",
}

VERDICT_THEMES = {
    "obra-prima": {
        "headline": "Obra-prima",
        "accent": "#d7b34f",
        "glow": "rgba(215, 179, 79, 0.32)",
        "surface": "rgba(88, 137, 72, 0.16)",
        "summary": "A galera e a critica embarcaram juntas: este e o tipo de filme que vale o hype.",
    },
    "boa experiencia": {
        "headline": "Boa experiencia",
        "accent": "#5ac8b0",
        "glow": "rgba(90, 200, 176, 0.28)",
        "surface": "rgba(42, 90, 88, 0.18)",
        "summary": "Tem recepcao positiva e entrega uma sessao segura para recomendar.",
    },
    "mediano": {
        "headline": "Mediano",
        "accent": "#f1b24a",
        "glow": "rgba(241, 178, 74, 0.24)",
        "surface": "rgba(90, 70, 36, 0.18)",
        "summary": "Funciona para um publico especifico, mas nao se destaca o bastante para empolgar.",
    },
    "perda de tempo": {
        "headline": "Perda de Tempo",
        "accent": "#ff6b6b",
        "glow": "rgba(255, 107, 107, 0.24)",
        "surface": "rgba(98, 43, 43, 0.2)",
        "summary": "Nem a critica nem o consenso do publico sustentaram uma recomendacao positiva.",
    },
}

GROUP_LABELS = {
    "rating": "Nota",
    "votes": "Avaliacoes",
    "box_office": "Bilheteria",
}


def format_vote_count(value: Any) -> str:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{number:,}".replace(",", ".")


def format_compact_currency(raw_value: str) -> str:
    amount = parse_box_office(raw_value)
    suffixes = (
        (1_000_000_000.0, "bi"),
        (1_000_000.0, "mi"),
        (1_000.0, "mil"),
    )
    for threshold, suffix in suffixes:
        if amount >= threshold:
            compact = amount / threshold
            return f"US$ {compact:.1f} {suffix}".replace(".", ",")
    return f"US$ {amount:,.0f}".replace(",", ".")


def membership_rows(memberships: dict[str, dict[str, float]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group, values in memberships.items():
        rows.append(
            {
                "group": GROUP_LABELS.get(group, group.title()),
                "values": [
                    {"label": label, "value": f"{score:.2f}"}
                    for label, score in values.items()
                ],
            }
        )
    return rows


def activated_rule_rows(movie_result: MovieAnalysisResult) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for hit in movie_result.classification.activated_rules:
        rows.append(
            {
                "name": hit.name,
                "strength": f"{hit.strength:.2f}",
                "description": RULE_EXPLANATIONS.get(
                    hit.name,
                    "Esta regra ajudou a deslocar o veredito final do termometro fuzzy.",
                ),
            }
        )
    return rows


def friendly_error_message(exc: Exception) -> str:
    message = str(exc)
    lowered = message.lower()
    if "traduzir o titulo" in lowered:
        return "Nao conseguimos identificar o titulo em ingles com confianca. Tente um nome mais completo."
    if "filme nao encontrado no imdb" in lowered:
        return "Nao foi possivel localizar esse filme no IMDb agora. Confira o nome e tente novamente."
    if "falha ao ler dados do imdb" in lowered:
        return (
            "Encontramos o filme no IMDb, mas nao conseguimos ler nota e avaliacoes "
            "da pagina agora. Isso costuma acontecer quando o layout muda ou a resposta vem incompleta."
        )
    if "bilheteria nao encontrada" in lowered:
        return "Encontramos o filme, mas a bilheteria nao apareceu no Box Office Mojo."
    if "bilheteria" in lowered and "erro" in lowered:
        return "Ocorreu um problema ao consultar a bilheteria do filme."
    if "indisponivel" in lowered:
        return "Os dados do filme vieram incompletos e nao deu para classificar."
    return "Nao foi possivel concluir a analise neste momento. Tente novamente em instantes."


def build_dashboard_context(movie_result: MovieAnalysisResult) -> dict[str, Any]:
    theme = VERDICT_THEMES[movie_result.classification.label]
    score = max(0.0, min(100.0, movie_result.classification.score))
    return {
        "movie_name": movie_result.imdb_result.get("nome", movie_result.translated_title_en),
        "translated_title": movie_result.translated_title_en,
        "original_title": movie_result.original_title_pt,
        "rating": str(movie_result.imdb_result.get("nota", "N/A")),
        "vote_count": format_vote_count(movie_result.imdb_result.get("num_avaliacoes", 0)),
        "poster_url": movie_result.imdb_result.get("poster_url", ""),
        "box_office": format_compact_currency(movie_result.box_office_result),
        "raw_box_office": movie_result.box_office_result,
        "label": movie_result.classification.label,
        "headline": theme["headline"],
        "summary": theme["summary"],
        "accent": theme["accent"],
        "glow": theme["glow"],
        "surface": theme["surface"],
        "score": score,
        "score_label": f"{score:.1f}",
        "rule_rows": activated_rule_rows(movie_result),
        "membership_rows": membership_rows(movie_result.classification.memberships),
    }
