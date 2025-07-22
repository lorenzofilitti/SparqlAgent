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
    INFLECTION = "etymology"
    SYNSET = "synset"
    ADVERB = "adverb"

class QuestionType(Enum):
    LILA_RELATED = "lila_related" 
    GENERAL_INQUIRY = "general_inquiry" 

class Triple(BaseModel):
    subject: str
    property: str
    object: str

class Metadata(BaseModel):
    language: str
    category: Category
    triples: list[Triple]
    question_type: QuestionType

class MainAgentResponse(BaseModel):
    content: str
    sparql_query: Optional[str]
    query_results: Optional[bool]