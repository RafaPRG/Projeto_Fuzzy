import json
from urllib.parse import quote_plus

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


def _iter_json_candidates(payload):
    if isinstance(payload, dict):
        yield payload

        graph_items = payload.get("@graph")
        if isinstance(graph_items, list):
            for item in graph_items:
                yield from _iter_json_candidates(item)
    elif isinstance(payload, list):
        for item in payload:
            yield from _iter_json_candidates(item)


def _normalize_imdb_payload(candidate: dict) -> dict[str, str] | None:
    aggregate = candidate.get("aggregateRating") or {}
    title_name = candidate.get("name")
    rating_value = aggregate.get("ratingValue")
    rating_count = aggregate.get("ratingCount")

    if title_name and rating_value is not None and rating_count is not None:
        return {
            "nome": str(title_name),
            "nota": str(rating_value),
            "num_avaliacoes": str(rating_count),
        }

    return None


def _extract_imdb_from_json_ld(soup: BeautifulSoup) -> dict[str, str] | None:
    for script_tag in soup.find_all("script", type="application/ld+json"):
        raw_payload = script_tag.string or script_tag.get_text(strip=True)
        if not raw_payload:
            continue

        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError:
            continue

        for candidate in _iter_json_candidates(payload):
            normalized = _normalize_imdb_payload(candidate)
            if normalized is not None:
                return normalized

    return None


def _extract_imdb_from_next_data(soup: BeautifulSoup) -> dict[str, str] | None:
    next_data_tag = soup.find("script", id="__NEXT_DATA__")
    if not next_data_tag:
        return None

    raw_payload = next_data_tag.string or next_data_tag.get_text(strip=True)
    if not raw_payload:
        return None

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        return None

    above_the_fold = (
        payload.get("props", {})
        .get("pageProps", {})
        .get("aboveTheFoldData", {})
    )
    ratings_summary = above_the_fold.get("ratingsSummary", {})
    title_name = (
        above_the_fold.get("originalTitleText", {}).get("text")
        or above_the_fold.get("titleText", {}).get("text")
    )
    rating_value = ratings_summary.get("aggregateRating")
    rating_count = ratings_summary.get("voteCount")

    if title_name and rating_value is not None and rating_count is not None:
        return {
            "nome": str(title_name),
            "nota": str(rating_value),
            "num_avaliacoes": str(rating_count),
        }

    return None


def get_imdb_rating_robust(movie_name: str) -> dict[str, str] | str:
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    chrome_options.add_argument("--lang=pt-BR")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(20)

    try:
        print(f"Buscando por: {movie_name}...")
        search_url = f"https://www.imdb.com/find?q={quote_plus(movie_name)}&s=tt&ttype=ft"
        driver.get(search_url)

        wait = WebDriverWait(driver, 10)
        first_result_element = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/title/tt']"))
        )

        movie_url = first_result_element.get_attribute("href")
        print(f"Filme encontrado! Acessando: {movie_url}")
        driver.get(movie_url)

        wait.until(EC.presence_of_element_located((By.ID, "__NEXT_DATA__")))
        soup = BeautifulSoup(driver.page_source, "html.parser")
        parsed_result = _extract_imdb_from_json_ld(soup)
        if parsed_result is not None:
            return parsed_result

        parsed_result = _extract_imdb_from_next_data(soup)
        if parsed_result is not None:
            return parsed_result

        return (
            "Encontramos a pagina do filme no IMDb, mas nao foi possivel extrair "
            "nota e numero de avaliacoes."
        )
    except Exception as exc:
        return f"Erro durante a execucao: {exc}"
    finally:
        driver.quit()


if __name__ == "__main__":
    movie_name = input("Digite o nome do filme: ").strip()
    result = get_imdb_rating_robust(movie_name)

    if isinstance(result, dict):
        print("\n--- Resultado ---")
        print(f"Filme: {result['nome']}")
        print(f"Nota: {result['nota']}")
        print(f"Avaliacoes: {result['num_avaliacoes']}")
    else:
        print(f"\nAviso: {result}")
