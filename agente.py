from agno.agent import Agent
from agno.models.groq import Groq
from dotenv import load_dotenv

load_dotenv()


TRANSLATION_INSTRUCTIONS = (
    "Receba um titulo de filme em portugues. "
    "Responda com o titulo oficial mais usado em ingles. "
    "Preserve numeros, simbolos, subtitulos e nomes de franquia. "
    "Nao traduza literalmente se houver um titulo oficial conhecido. "
    "Se o titulo ja estiver em ingles, repita-o. "
    "Retorne apenas o titulo, sem aspas e sem explicacoes."
)


def translate_title_to_english(
    movie_title_pt: str,
    timeout: int = 20,
) -> str:
    agent = Agent(
        model=Groq(
            id="llama-3.3-70b-versatile",
            temperature=0.1,
            timeout=timeout,
            max_retries=1,
        ),
        instructions=TRANSLATION_INSTRUCTIONS,
    )

    response = agent.run(movie_title_pt)
    translated_title = (response.content or "").strip()

    if not translated_title:
        raise ValueError("A IA nao retornou um titulo utilizavel.")

    return translated_title


if __name__ == "__main__":
    movie_title_pt = input("Digite o nome do filme em portugues: ").strip()
    translated_title = translate_title_to_english(movie_title_pt)
    print(translated_title)
