import re
import os
from dotenv import load_dotenv
import time
from SPARQLWrapper import JSON, SPARQLWrapper2
from SPARQLWrapper.SPARQLExceptions import QueryBadFormed
import logfire
from src.programs.async_wikidata import wikidata_async_search, lila_async_search
from typing import Dict, List
from pydantic_ai.exceptions import ModelRetry
import json
import asyncio
load_dotenv()

#------------------------------------------------------------------------------------------
     
def clean_query(sprql_query):
    """
    Takes the sparql query from gpt and removes the word "sparql"
    and the characters ", ' and `
    """
    pattern = re.compile(r'(""")|(\'\'\')|(```)|(\bsparql\b)')
    clean_sparql_query = re.sub(pattern, '', sprql_query)
    logfire.info(f"Clean query {clean_sparql_query}")
    return clean_sparql_query


#------------------------------------------------------------------------------------------

def gen(txt):
    for c in txt:
        yield c
        time.sleep(0.01)

#------------------------------------------------------------------------------------------

async def DB_search(query: str) -> List[Dict[str, str]]:
        """
        Use this tool exclusively to send a sparql query and get results 
        from the Lila Knowledge base
        
        :param query: a query formatted in sparql language
        :type query: str

        :return: Results of the query from the knowledge base in json format
        :rtype: list[dict]
        """
        logfire.info(f"Input sparql query of the tool: {query}")
        router = SPARQLWrapper2(os.environ.get("LILA_ENDPOINT"))
        router.setReturnFormat(JSON)
        
        try:
            router.setQuery(clean_query(query))
            query_result = router.query()

            if query_result.bindings:
                logfire.info("Found results from the lila db")

                full_result = query_result.fullResult
                bindings = full_result["results"]["bindings"]

                logfire.info("Extracting uris...")
                wiki_pattern = re.compile(r"https?://www\.wikidata.*?\'")
                lila_pattern = re.compile(r"https?://lila-erc\.eu.*?\'")

                wikidata_uris = wiki_pattern.findall(str(bindings))
                lila_uris = lila_pattern.findall(str(bindings))
                clean_wiki_uris = [re.sub("'", "", uri) for uri in wikidata_uris]
                clean_lila_uris = [re.sub("'", "", uri) for uri in lila_uris]

                logfire.info("Searching Wikidata and LiLa...")
                wikidata_result = await asyncio.gather(*[wikidata_async_search(uri) for uri in clean_wiki_uris])
                lila_result = await asyncio.gather(*[lila_async_search(uri) for uri in clean_lila_uris])


                logfire.info("Collecting results...")
                for result in wikidata_result:  
                    bindings = re.sub(result.uri, result.label, str(bindings))
                for result in lila_result:
                    bindings = re.sub(result.uri, result.heading, str(bindings))

                lila_and_wiki_results = {
                    "status": "success",
                    "results": bindings
                }
                logfire.info("Returning results.")
                return lila_and_wiki_results

            else:
                logfire.info("Query was successful but no data was found")
                return {"status": "success",
                        "message": "No data found in the database",
                        "results": []}
            
        except QueryBadFormed as e:
            logfire.error(f"Query bad formatted. Error: {e}")
            raise ModelRetry({"status": "error", "error": str(e)}) 

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
        with open("prefixes.json", "r") as f:
            prefixes = json.load(f)
        with open("suffixes.json", "r") as f:
            suffixes = json.load(f)
        
        if type.lower() == "prefix":
            result = prefixes.get(label)
        elif type.lower() == "suffix":
            result = suffixes.get(label)
        
        logfire.info(f"Affixes tool result: {result}")
        return result
    
    except Exception as e:
        logfire.error(f"Exception caught in the get_affixes tool: {e}")
        return None
    