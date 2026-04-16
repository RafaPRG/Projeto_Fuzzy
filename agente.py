from agno.agent import Agent
from agno.models.groq import Groq
from dotenv import load_dotenv
from agno.tools.tavily import TavilyTools

load_dotenv()

agent = Agent(
    model = Groq(id="llama-3.3-70b-versatile",temperature=0.2),
    tools=[TavilyTools()],
    instructions=" titulo de um filme será passado em portugues, use suas ferrametas para pesquisar o titulo original em ingles. Não faça a tradução literal, retorne apenas o titulo"
)
prompt = f"""Curtindo a Vida Adoidado"""
titulo = agent.run(prompt)

print(titulo.content)
