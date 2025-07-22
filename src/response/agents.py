import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from pydantic_ai import Tool, Agent
from typing import Optional

from src.utilities.prompts import MAIN_SYSTEM_PROMPT, INTENT_PROMPT
from src.programs.tools import DB_search, get_affixes
from src.response.dataclasses import Metadata, MainAgentResponse

def intent_extractor(user_question: str, previous_exchange: list) -> Metadata:
    agent = Agent(
        model = os.environ.get("GPT-MODEL-NAME"),
        system_prompt = INTENT_PROMPT,
        instrument = True,
        result_type = Metadata
    )
    data = f"### User question: {user_question}\n\n###Previous exchange: {previous_exchange}"
    intent_response = agent.run_sync(user_prompt=data)
    return intent_response.data

def main_agent(
        user_question: str,
        sparql_queries: list[str],
        semantic_structure: list[dict], 
        message_history: Optional[dict] = None) -> MainAgentResponse:
    
    agent = Agent(
        model = os.getenv("GPT-MODEL-NAME"),
        system_prompt = MAIN_SYSTEM_PROMPT,
        instrument = True,
        tools = [Tool(DB_search), Tool(get_affixes)],
        result_type=MainAgentResponse,
        model_settings = {
            "temperature": 0,
            "parallel_tool_calls": True
            },
    )

    data = f"###Previous turn of the current conversation: {message_history}\n\n### User question: {user_question}\n\n###Semantic structure of the input user query: {semantic_structure}\n\n### Sparql query examples: {sparql_queries}"

    response = agent.run_sync(
        user_prompt=data,
        message_history=message_history
    )
    return response.data



