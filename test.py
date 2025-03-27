import asyncio
import json
import requests
import re
from src.utilities.constants import LILA_ENDPOINT

def dbsearch2(query, endpoint):
    params = {"query": query, "format": "json"}
    res = requests.get(endpoint, params=params).json()
    result = re.findall(r"\'http.*?\'", str(res))
    raw_uris = [re.sub("'", "", uri) for uri in result if "wikidata" in uri]
    return raw_uris


def search_sync(uri):
    js_query_results = requests.get(uri).json()
    entity = [k for k in js_query_results["entities"].keys()]
    label = js_query_results["entities"][entity[0]]["labels"]["en"]
    description = js_query_results["entities"][entity[0]]["descriptions"]["en"]
    if label and description:
        return {
            "entity": entity[0],
            "label": label.get("value"),
            "description": description.get("value"),
        }


async def search_async(uri):
    return await asyncio.to_thread(search_sync, uri)


async def main() -> None:
    uri_list = dbsearch2(
        "select ?author where {?doc a powla:Document; dcterms:creator ?author} limit 5",
        endpoint=LILA_ENDPOINT
    )
    print(uri_list, "\n\n")
    result = await asyncio.gather(*[search_async(uri) for uri in uri_list])
    with open("wikidata.json", "w") as f:
        json.dump(result, f, indent=4)
    print(result)


asyncio.run(main())
