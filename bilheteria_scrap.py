from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

def get_worldwide_box_office(movie_name):
    # Configurações do Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Executa sem abrir a janela
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # 1. Acessa a página de busca
        search_url = f"https://www.boxofficemojo.com/search/?q={movie_name}"
        driver.get(search_url)

        # 2. Espera e clica no primeiro link de filme (geralmente o mais relevante)
        # O seletor abaixo busca o link dentro da lista de resultados
        first_result_selector = ".a-fixed-left-grid-col.a-col-right a.a-link-normal"
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, first_result_selector)))
        
        first_link = driver.find_element(By.CSS_SELECTOR, first_result_selector)
        first_link.click()

        # 3. Extrai o conteúdo da página com BeautifulSoup
        time.sleep(2) # Pequena pausa para garantir o load
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # 4. Busca o valor "Worldwide"
        # No Box Office Mojo, as bilheterias ficam em áreas com a classe 'a-section'
        summary_values = soup.find_all("div", class_="a-section a-spacing-none")
        
        worldwide_gross = "Não encontrado"
        
        for section in summary_values:
            text = section.get_text()
            if "Worldwide" in text:
                # O valor geralmente está em um span com a classe 'money'
                money_span = section.find("span", class_="money")
                if money_span:
                    worldwide_gross = money_span.get_text()
                    break

        return worldwide_gross

    except Exception as e:
        return f"Erro ao processar: {e}"
    finally:
        driver.quit()

# Uso
filme = input("Digite o nome do filme: ")
resultado = get_worldwide_box_office(filme)
print(f"\nBilheteria Mundial de '{filme}': {resultado}")