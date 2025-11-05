import asyncio
import os
import requests
from typing import Optional
from pydantic import BaseModel
import logfire
from bs4 import BeautifulSoup
from dotenv import load_dotenv
load_dotenv()

logfire.configure(token=os.environ.get("LOGFIRE-TOKEN"))

class WikidataResults(BaseModel):
    uri        : Optional[str] = None
    entity_id  : Optional[str] = None
    label      : Optional[str] = None
    description: Optional[str] = None


def wikidata_sync_search(uri: str) -> WikidataResults | None:
    endpoint = "https://www.wikidata.org/w/rest.php/wikibase/v1"
    headers = {
        "User-Agent": os.getenv("USER_AGENT")
    }

    try:
        target_entity = os.path.basename(uri)
        label = requests.get(f"{endpoint}/entities/items/{target_entity}/labels", headers=headers).json().get("en", None)
        description = requests.get(f"{endpoint}/entities/items/{target_entity}/descriptions", headers=headers).json().get("en", None)

        results = WikidataResults(
            uri         = uri,
            entity_id   = target_entity,
            label       = label,
            description = description,
        )
        return results

    except Exception as e:
        logfire.error(f"Unexpected error during Wikidata request: {e}")
        return None

#------------------------------------------------------------------------------------------------------------

class LilaResults(BaseModel):
    uri     : Optional[str] = None
    heading : Optional[str] = None

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

    except Exception as e:
        logfire.error(f"Unexpected error during LiLa request: {e}")
        return None


async def wikidata_async_search(uri:str):
    return await asyncio.to_thread(wikidata_sync_search, uri)

async def lila_async_search(uri:str):
    return await asyncio.to_thread(lila_sync_search, uri)
