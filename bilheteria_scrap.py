import time
from urllib.parse import quote_plus
from typing import Callable

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


def _emit_log(logger: Callable[[str], None] | None, message: str) -> None:
    print(message, flush=True)
    if logger is not None:
        logger(message)


def get_worldwide_box_office(
    movie_name: str,
    logger: Callable[[str], None] | None = None,
) -> str:
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(20)

    try:
        _emit_log(logger, f"Buscando bilheteria por: {movie_name}...")
        search_url = f"https://www.boxofficemojo.com/search/?q={quote_plus(movie_name)}"
        driver.get(search_url)

        first_result_selector = ".a-fixed-left-grid-col.a-col-right a.a-link-normal"
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, first_result_selector))
        )

        first_link = driver.find_element(By.CSS_SELECTOR, first_result_selector)
        first_link.click()

        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        summary_values = soup.find_all("div", class_="a-section a-spacing-none")

        worldwide_gross = "Nao encontrado"
        for section in summary_values:
            text = section.get_text()
            if "Worldwide" in text:
                money_span = section.find("span", class_="money")
                if money_span:
                    worldwide_gross = money_span.get_text()
                    break

        return worldwide_gross
    except Exception as exc:
        return f"Erro ao processar: {exc}"
    finally:
        driver.quit()


if __name__ == "__main__":
    movie_name = input("Digite o nome do filme: ").strip()
    result = get_worldwide_box_office(movie_name)
    print(f"\nBilheteria mundial de '{movie_name}': {result}")
