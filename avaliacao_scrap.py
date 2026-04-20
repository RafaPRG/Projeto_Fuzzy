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
        script_tag = soup.find("script", type="application/ld+json")

        if not script_tag:
            return "Script JSON-LD nao encontrado na pagina do filme."

        data = json.loads(script_tag.string)
        if isinstance(data, list):
            data = data[0]

        return {
            "nome": data.get("name"),
            "nota": data.get("aggregateRating", {}).get("ratingValue", "N/A"),
            "num_avaliacoes": data.get("aggregateRating", {}).get("ratingCount", "N/A"),
        }
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
