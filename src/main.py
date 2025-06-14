from programs.st_interface import chat_interface
from pydantic_ai import Agent, Tool
from programs.tools import DB_search, search_similarity, get_affixes
from src.utilities.constants import SYSTEM_MESSAGE, NEW_SYSTEM_PROMPT
import os
import logfire
from dotenv import load_dotenv
from pathlib import Path

dotenv_path = Path('../.env')
load_dotenv(dotenv_path=dotenv_path)

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

    :param model: The name of the LLM. One of the models mentioned in the PydanticAI documentation.
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
        
    except Exception as e:
        logfire.error(f"An error occurred while instantiating the agent: {e}")


pyagent_chat(
    model=os.getenv("GPT-MODEL-NAME"),
    system_prompt=NEW_SYSTEM_PROMPT,
    tools=[Tool(DB_search), Tool(search_similarity), Tool(get_affixes)],
    model_settings={"temperature": 0,
                    "parallel_tool_calls": True
                    },
    retries=3,
    instrument=True,
)
