import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def get_imdb_rating_robust(movie_name):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    # Header mais completo para evitar bloqueios
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_argument("--lang=pt-BR")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # 1. Busca - Usando a URL de busca de títulos
        print(f"Buscando por: {movie_name}...")
        search_url = f"https://www.imdb.com/find?q={movie_name}&s=tt&ttype=ft"
        driver.get(search_url)

        # 2. ESPERA EXPLÍCITA (Até 10 segundos até o link do filme aparecer)
        # O seletor abaixo busca qualquer link que aponte para um título (ttXXXXXXX)
        wait = WebDriverWait(driver, 10)
        first_result_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/title/tt']")))
        
        # Pega a URL do primeiro filme
        movie_url = first_result_element.get_attribute("href")
        print(f"Filme encontrado! Acessando: {movie_url}")
        
        # 3. Acessa a página do filme
        driver.get(movie_url)

        # 4. Extração via JSON-LD (Continua sendo a melhor forma)
        wait.until(EC.presence_of_element_located((By.ID, "__NEXT_DATA__"))) # Espera o core do site carregar
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        script_tag = soup.find("script", type="application/ld+json")

        if script_tag:
            data = json.loads(script_tag.string)
            
            # Algumas páginas o JSON-LD é uma lista, vamos tratar isso
            if isinstance(data, list):
                data = data[0]

            rating_value = data.get("aggregateRating", {}).get("ratingValue", "N/A")
            rating_count = data.get("aggregateRating", {}).get("ratingCount", "N/A")
            
            return {
                "nome": data.get("name"),
                "nota": rating_value,
                "num_avaliacoes": rating_count
            }
        else:
            return "Script JSON-LD não encontrado na página do filme."

    except Exception as e:
        return f"Erro durante a execução: {e}"
    finally:
        driver.quit()

# Execução
filme = input("Digite o nome do filme: ")
resultado = get_imdb_rating_robust(filme)

if isinstance(resultado, dict):
    print(f"\n--- Resultado ---")
    print(f"Filme: {resultado['nome']}")
    print(f"Nota: {resultado['nota']}")
    print(f"Avaliações: {resultado['num_avaliacoes']}")
else:
    print(f"\nAviso: {resultado}")