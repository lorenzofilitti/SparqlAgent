import re
from dotenv import load_dotenv
import time
from SPARQLWrapper import JSON, SPARQLWrapper2
from SPARQLWrapper.SPARQLExceptions import QueryBadFormed
import logfire
import chromadb
from chromadb.errors import ChromaError
from utilities.constants import NUMBER_SIMILARITY_RESULTS, USER_QUERY_COLLECTION_NAME, SPARQL_QUERY_COLLECTION_NAME, LILA_ENDPOINT
from typing import Dict, List
from pydantic_ai.exceptions import ModelRetry
import json
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

def DB_search(query: str) -> List[Dict[str, str]]:
        """
        Use this tool exclusively to send a sparql query and get results 
        from the Lila Knowledge base
        
        :param query: a query formatted in sparql language
        :type query: str

        :return: Results of the query from the knowledge base in json format
        :rtype: list[dict]
        """
        logfire.info(f"Input sparql query of the tool: {query}")
        router = SPARQLWrapper2(LILA_ENDPOINT)
        router.setReturnFormat(JSON)
        
        try:
            router.setQuery(clean_query(query))
            query_result = router.query()

            if query_result.bindings:
                logfire.info("Found results from the lila db")
                full_result = query_result.fullResult
                return {"status": "success",
                        "results": full_result["results"]["bindings"]}

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
        

def search_similarity(query: str):
    
    """ 
    Performs similarity search on the user queries vector db and
    outputs the corresponding sparql query (based on matching ids)
    from the sparql queries vector store.

    :param query: The user question
    :type query: str

    :return: list of matching SPARQL queries based on similarity
    :rtype: list
    """
    try:
        chroma_client = chromadb.HttpClient(host='localhost', port=8000)
        u_query_collection = chroma_client.get_collection(name=USER_QUERY_COLLECTION_NAME)
        s_query_collection = chroma_client.get_collection(name=SPARQL_QUERY_COLLECTION_NAME)

        results_1 = u_query_collection.query(
            query_texts=query,
            n_results=NUMBER_SIMILARITY_RESULTS
        )

        ids_results_1 = results_1["ids"][0]

        results_2 = s_query_collection.get(
            ids = ids_results_1
        ) 
        logfire.info(f'Successfully performed semantic search: {results_2["documents"]}')
        return {"result": "success", "content": results_2.get("documents")}
    
    except ChromaError as e:
        logfire.error(f"An error occurred while performing semantic search: {e}")
        return {"result": "error", "content": []}

    except Exception as e:
        logfire.error(f"Unexpected error during semantic search. Error: {e}")
        return {"result": "error", "content": []}


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
        with open("prefixes.json", "r") as f:
            prefixes = json.load(f)
        with open("suffixes.json", "r") as f:
            suffixes = json.load(f)
        
        if type.lower() == "prefix":
            result = prefixes.get(label)
        elif type.lower() == "suffix":
            result = suffixes.get(label)
    except Exception as e:
        logfire.error(f"Exception caught in the get_affixes tool: {e}")
    
    logfire.info(f"Affixes tool result: {result}")
    return result