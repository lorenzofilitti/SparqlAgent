import asyncio
import os
import requests
from pydantic import BaseModel
import logfire
from bs4 import BeautifulSoup
from dotenv import load_dotenv
load_dotenv()

logfire.configure(token=os.environ.get("LOGFIRE-TOKEN"))

class WikidataResults(BaseModel):
    uri        : str | None = None
    entity_id  : str | None = None
    label      : str | None = None
    description: str | None = None


def wikidata_sync_search(uri: str) -> WikidataResults | None:

    try:
        wikidata_query_results = requests.get(uri, timeout=5).json()
        entity = list(wikidata_query_results.get("entities", "").keys())[0]

        results = WikidataResults(
            uri         = uri,
            entity_id   = entity,
            label       = wikidata_query_results.get("entities", "").get(entity, "").get("labels", "").get("en", "").get("value", ""),
            description = wikidata_query_results.get("entities", "").get(entity, "").get("descriptions", "").get("en", "").get("value", ""),
        )
        return results
    except requests.exceptions.Timeout:
        logfire.error(f"Timeout during Wikidata request for URI: {uri}")
        return None
    
    except requests.exceptions.ConnectionError:
        logfire.error(f"Connection error to Wikidata for URI: {uri}")
        return None
    
    except Exception as e:
        logfire.error(f"Unexpected error during Wikidata request: {e}")
        return None

#----------------------------------------------------------------------------------------------------------------------

class LilaResults(BaseModel):
    uri     : str = None
    heading : str = None
    
def lila_sync_search(uri: str) -> LilaResults | None:

    try:
        lila_query_results = requests.get(uri, timeout=5)
        html_content       = BeautifulSoup(lila_query_results.content, "html.parser")
        title              = html_content.find("h1")
        span_element       = title.find("span")
        heading_txt        = span_element.get_text(strip=True)

        results = LilaResults(
            uri = uri,
            heading = heading_txt
        )
        return results
    except requests.exceptions.Timeout:
        logfire.error(f"Timeout during LiLa request for URI: {uri}")
        return None
    
    except requests.exceptions.ConnectionError:
        logfire.error(f"Connection error to LiLa for URI: {uri}")
        return None
    
    except Exception as e:
        logfire.error(f"Unexpected error during LiLa request: {e}")
        return None


async def wikidata_async_search(uri:str):
    return await asyncio.to_thread(wikidata_sync_search, uri)

async def lila_async_search(uri:str):
    return await asyncio.to_thread(lila_sync_search, uri)



