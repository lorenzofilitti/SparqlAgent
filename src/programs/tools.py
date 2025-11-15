import asyncio
import json
import os
import re
import time
from typing import Dict, List, Optional

import logfire
from dotenv import load_dotenv
from pydantic_ai.exceptions import ModelRetry
from SPARQLWrapper import JSON, SPARQLWrapper2
from SPARQLWrapper.SPARQLExceptions import QueryBadFormed
from SPARQLWrapper.SmartWrapper import Bindings

from src.programs.async_wikidata import lila_async_search, wikidata_async_search
from src.programs.parser import LilaDatabaseParser

load_dotenv()

#------------------------------------------------------------------------------------------

def clean_query(sprql_query):
    """
    Takes the sparql query from gpt and removes the word "sparql"
    and the characters ", ' and `
    """
    pattern = re.compile(r'(""")|(\'\'\')|(```)|(\bsparql\b)')
    clean_sparql_query = re.sub(pattern, '', sprql_query)
    return clean_sparql_query


#------------------------------------------------------------------------------------------

def gen(txt):
    for c in txt:
        yield c
        time.sleep(0.01)

#------------------------------------------------------------------------------------------

async def DB_search(query: str) -> Optional[List[Dict[str, str]] | Dict | str]:
        """
        Use this tool exclusively to send a sparql query and get results
        from the Lila Knowledge base

        :param query: a query formatted in sparql language
        :type query: str

        :return: Results of the query from the knowledge base in json format
        :rtype: list[dict]
        """
        logfire.info(f"Input sparql query of the tool: {query}")
        parser = LilaDatabaseParser()
        router = SPARQLWrapper2(os.environ.get("LILA_ENDPOINT"))
        router.setReturnFormat(JSON)

        try:
            router.setQuery(clean_query(query))
            query_result = router.query()

            if isinstance(query_result, Bindings) and query_result.bindings:
                logfire.info("Found results from the lila db")

                full_result = query_result.fullResult
                bindings = full_result["results"]["bindings"]

                logfire.info("Extracting uris...")
                wiki_pattern = re.compile(r"https?://www\.wikidata.*?\'")
                #lila_pattern = re.compile(r"https?://lila-erc\.eu.*?\'")

                wikidata_uris = wiki_pattern.findall(str(bindings))

                if wikidata_uris:
                    clean_wiki_uris = [re.sub("'", "", uri) for uri in wikidata_uris]

                    logfire.info("Searching Wikidata...")
                    wikidata_result = await asyncio.gather(*[wikidata_async_search(uri) for uri in clean_wiki_uris])

                    logfire.info("Collecting results...")
                    for result in wikidata_result:
                        bindings = re.sub(result.uri, f"{result.label} - {result.description}", str(bindings))
                
                lila_and_wiki_results = {
                    "status": "success",
                    "results": bindings
                }
                logfire.info("Returning results.")
                
                num_tokens = parser.count_tokens(str(lila_and_wiki_results))
                if num_tokens > 30000:
                    return f"Results were truncated because of excessive length: {str(lila_and_wiki_results)[:25000]}"
                else:
                    return lila_and_wiki_results

            else:
                logfire.info("Query was successful but no data was found")
                return {"status": "success",
                        "message": "No data found in the database",
                        "results": []}

        except QueryBadFormed as e:
            logfire.error(f"Query bad formatted. Error: {e}")
            raise ModelRetry(str(e))

        except Exception as e:
            logfire.error(f"Unexpected error occurred. Error: {e}")
            return {"status": "error", "error": str(e)}

#--------------------------------------------------------------------

def get_affixes(label: str, type: str):
    """
    tool to get affixes' named individuals to build sparql queries on affixes. Specify the label (the prefix or suffix) and the type of affix requested by the user (prefix or suffix)

    :param label: the prefix or suffix
    :type label: str

    :param type: a string indicating whether to look for a prefix or suffix
    :type type: str
    """
    try:
        logfire.info(f"Input affix in the tool: {label} of type {type}")
        with open(".test/prefixes.json", "r") as f:
            prefixes = json.load(f)
        with open(".test/suffixes.json", "r") as f:
            suffixes = json.load(f)

        if type.lower() == "prefix":
            result = prefixes.get(label)
        else: 
            result = suffixes.get(label)

        logfire.info(f"Affixes tool result: {result}")
        return result

    except Exception as e:
        logfire.error(f"Exception caught in the get_affixes tool: {e}")
        return None


def explore_classes_and_properties(identifiers: list[str]):
    parser = LilaDatabaseParser()
    results = []
    for id in identifiers:
        if "http" not in id:
            uri = None
            try:
                label = id.split(":")[1]
            except (ValueError, KeyError):
                label = label
        
            if label[0].isupper():
                concept_type = "Class"
            else:
                concept_type = "Property"
            
        else:
            label = None
            uri = id
    
        filters = []
        if uri:
            filters.append(f"FILTER(?class = <{uri}>)")
        
        if label:
            filters.append(f'FILTER(?label = "{label}")')
        
        filters_clause = "\n".join(filters)
        
        limit_clause = f"LIMIT {100}"
        
        query = f"""
        SELECT
            ?class
            ?label
            ?description
            (GROUP_CONCAT(DISTINCT ?parentClass; SEPARATOR=", ") AS ?parent_classes)
            (GROUP_CONCAT(DISTINCT ?subClass; SEPARATOR=", ") AS ?sub_classes)
        WHERE {{
            ?class a owl:{concept_type} .
            OPTIONAL {{ ?class rdfs:label ?label }}
            OPTIONAL {{ ?class rdfs:comment ?description }}
            OPTIONAL {{
                ?class rdfs:subClassOf ?parentClass.
            }}
            OPTIONAL {{
                ?subClass rdfs:subClassOf ?class
            }}
            {filters_clause}
        }}
        GROUP BY ?class ?label ?description
        ORDER BY ?class
        {limit_clause}
        """
        query_results = parser.query(query)
        parsed_results = parser.parse_results(query_results, concept_type)
        concepts = [concept.to_string_for_llm() for _, concept in parsed_results.items()]
        results.extend(concepts)
    
    return "\n\n".join(results)


if __name__ == "__main__":
    res = asyncio.run(DB_search("""
    PREFIX lilaCorpora: <http://lila-erc.eu/ontologies/lila_corpora/>
    SELECT ?lemmaLiLa ?lemmaLabel (COUNT(?token) AS ?count) WHERE {
  ?document a powla:Document .
  ?chapter a lilaCorpora:citationUnit ;
        lilaCorpora:hasRefType "Capitulum" ;
        lilaCorpora:hasCitSubUnit ?par.
  ?par powla:hasChild ?token .
  ?token lila:hasLemma ?lemmaLiLa.
  ?lemmaLiLa a lila:Lemma ;
        rdfs:label ?lemmaLabel .
} GROUP BY ?lemmaLiLa ?lemmaLabel ORDER BY DESC(?count) LIMIT 1"""))
    print(res)