from enum import Enum
from typing import Optional
from pydantic import BaseModel

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

class Metadata(BaseModel):
    language: str
    reformulated_question: str
    category: Category
    question_type: QuestionType

class MainAgentResponse(BaseModel):
    content: str
    sparql_query: Optional[str]
    query_results: bool
