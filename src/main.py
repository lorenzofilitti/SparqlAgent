from programs.st_interface import chat_interface, plot_query
from pydantic_ai import Agent, Tool
from programs.tools import DB_search, search_similarity
from utilities.constants import SYSTEM_MESSAGE
import os
import logfire
from dotenv import load_dotenv

load_dotenv()

def pyagent_chat(
    model: str,
    system_prompt: str,
    tools: list[Tool],
    model_settings: dict,
    retries: int,
    instrument: bool,
):
    """
    Main function to start the chatbot.

    :param model: The name of the LLM.
    :type model: str
    :param system_prompt: The LLM's system prompt.
    :type system_prompt: str
    :param tools: The tools the Agent(LLM) will use.
    :type tools: list[Tool]
    :param model_settings: LLM settings.
    :type model_settings: dict
    :param retries: The default number of retries to allow before raising an error.
    :type retries: int
    :param instrument: Use logfire features for tracking Agent actions
    :type instrument: bool

    """
    try:
        agent = Agent(
            model=model,
            system_prompt=system_prompt,
            model_settings=model_settings,
            retries=retries,
            tools=tools,
            instrument=instrument,
        )

        chat_interface(agent)
        plot_query()
        
    except Exception as e:
        logfire.error(f"An error occurred while instantiating the agent: {e}")

pyagent_chat(
    model=os.getenv("GPT-MODEL-NAME"),
    system_prompt=SYSTEM_MESSAGE,
    tools=[Tool(DB_search), Tool(search_similarity)],
    model_settings={"temperature": 0},
    retries=1,
    instrument=True,
)
