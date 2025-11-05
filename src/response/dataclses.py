from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class Category(str, Enum):
    DOCUMENT = "document"
    CORPUS = "corpus"
    LEMMA = "lemma"
    LEXICAL_RESOURCE = "lexical_resource"
    ADJECTIVE = "adjective"
    NOUN = "noun"
    AFFIX = "affix"
    VERB = "verb"
    ETYMOLOGY = "etymology"
    INFLECTION = "inflection"
    SYNSET = "synset"
    ADVERB = "adverb"

class QuestionType(Enum):
    LILA_RELATED = "lila_related"
    GENERAL_INQUIRY = "general_inquiry"

class Intent(BaseModel):
    language: str
    category: Optional[Category]
    question_type: QuestionType

class MainAgentResponse(BaseModel):
    content: str
    sparql_query: Optional[str]
    query_results: bool

class ReformulatedQuery(BaseModel):
    reformulated_query: str

class Evaluation(BaseModel):
    explanation: str = Field(description="Detailed explanation of issues and fixes")
    is_valid: bool = Field(description="True if query is correct, False if issues found"),
    corrected_query: Optional[str] = Field(description="Fixed query if issues found, null otherwise"),  