import sys
import os
# sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from pydantic_ai import Tool, Agent
from pydantic_ai.agent import AgentRunResult
from typing import Optional

from src.utilities.prompts import MAIN_SYSTEM_PROMPT, INTENT_PROMPT, REFORMULATOR_PROMPT, EVALUATOR_PROMPT
from src.programs.tools import DB_search, get_affixes, explore_classes_and_properties
from src.response.dataclses import Intent, MainAgentResponse, ReformulatedQuery, Evaluation

def query_reformulator(user_question: str, conversation_history: list) -> ReformulatedQuery:
    agent = Agent(
        model = os.environ.get("INTENT_AGENT_MODEL"),
        system_prompt = REFORMULATOR_PROMPT,
        instrument = True,
        result_type = ReformulatedQuery,
    )
    data = f"**user_query**: {user_question}\n\n**conversation_history**: {conversation_history}"
    response = agent.run_sync(user_prompt=data)
    return response.data


def intent_extractor(user_question: str) -> Intent:
    agent = Agent(
        model = os.environ.get("INTENT_AGENT_MODEL"),
        system_prompt = INTENT_PROMPT,
        instrument = True,
        result_type = Intent,
    )
    data = f"**user_query**: {user_question}"
    response = agent.run_sync(user_prompt=data)
    return response.data


def main_agent(
    user_question: str,
    sparql_queries: Optional[list[dict]],
    conversation_history: Optional[list] = None) -> AgentRunResult[MainAgentResponse]:

    agent = Agent(
        model = os.getenv("MAIN_AGENT_MODEL"),
        system_prompt = MAIN_SYSTEM_PROMPT,
        instrument = True,
        tools = [
            Tool(DB_search, max_retries=3), 
            Tool(explore_classes_and_properties, max_retries=2), 
            Tool(get_affixes),
            Tool(evaluator)
            ],
        result_type=MainAgentResponse,
        model_settings = {
            "temperature": 0,
            "parallel_tool_calls": True
            },
    )

    data = f"###Conversation_history: {conversation_history}\n\n### User question: {user_question}\\n\n### Sparql query examples: {sparql_queries}"

    response = agent.run_sync(
        user_prompt=data
    )
    return response


def evaluator(sparql_query: str):
    agent = Agent(
        model = os.environ.get("INTENT_AGENT_MODEL"),
        system_prompt = EVALUATOR_PROMPT,
        instrument = True,
        result_type= Evaluation
    )
    data = f"**Generated sparql query**: {sparql_query}"
    response = agent.run_sync(user_prompt=data)
    data = response.data

    return f'{{"is_valid": {data.is_valid}, "explanation": {data.explanation} "corrected_query": {data.corrected_query}}}'


