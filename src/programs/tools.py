import re
from dotenv import load_dotenv
import time
from SPARQLWrapper import JSON, SPARQLWrapper2
from pydantic import BaseModel
import logfire
import chromadb
from chromadb.errors import ChromaError
from utilities.constants import NUMBER_SIMILARITY_REULTS, USER_QUERY_COLLECTION_NAME, SPARQL_QUERY_COLLECTION_NAME

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
class SparqlQueryModel(BaseModel):
    query: str
    model_config = {"arbitrary_types_allowed": True}


def DB_search(query: SparqlQueryModel):
        """
        Use this tool exclusively to send a sparql query and get results 
        from the Lila Knowledge base
        
        :param sparql_query: a query formatted in sparql language
        :type sparql_query: str

        :return: Results of the query from the knowledge base in json format
        :rtype: list[dict]
        """
        logfire.info(f"Input sparql query of the tool: {query}")
        router = SPARQLWrapper2("https://lila-erc.eu/sparql/lila_knowledge_base/sparql")
        router.setReturnFormat(JSON)
        router.setQuery(clean_query(query.query))
        
        try:
            query_result = router.query()

            if query_result.bindings:
                logfire.info("Found results from the lila db")
                full_result = query_result.fullResult
                return {"status": "success",
                        "results": full_result["results"]["bindings"]}

            else:
                logfire.info("No results found")
                return {"status": "success",
                        "message": "No data found. Query might be incorrect",
                        "results": []}

        except Exception as e:
            logfire.error(f"Sparql query failed. Error: {str(e)}")
            return {"status": "error",
                    "error": str(e)}
        

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
            n_results=NUMBER_SIMILARITY_REULTS
        )

        ids_results_1 = results_1["ids"][0]

        results_2 = s_query_collection.get(
            ids = ids_results_1
        ) 
        logfire.info(f"Successfully performed semantic search: {results_2["documents"]}")
        return results_2["documents"]
    
    except ChromaError as e:
        logfire.error(f"An error occurred while performing semantic search: {e}")

    return []



