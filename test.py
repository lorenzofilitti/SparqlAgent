import asyncio
import aiohttp
import json
import requests
import re

def search_sync(uri):
    js_query_results = requests.get(uri).json()
    entity =[k for k in js_query_results["entities"].keys()]
    label = js_query_results["entities"][entity[0]]["labels"]["en"]
    description = js_query_results["entities"][entity[0]]["descriptions"]["en"]
    if label and description:
        return {"uri": uri, "label": label.get("value"), "description": description.get("value")}


def dbsearch2(query):
    params = {"query": query, "format": "json"}
    endpoint = "https://lila-erc.eu/sparql/lila_knowledge_base/sparql"
    res = requests.get(endpoint, params=params).json()
    result = re.findall(r"\'http.*?\'", str(res))
    sub = [re.sub("\'", "", uri) for uri in result if "wikidata" in uri]
    return sub


async def search(uri):
    return await asyncio.to_thread(search_sync, uri)

async def main()-> None:
    uri_list = dbsearch2("select ?author where {?doc a powla:Document; dcterms:creator ?author} limit 15")
    print(uri_list, "\n\n")
    result = await asyncio.gather(*[search(uri) for uri in uri_list])
    with open("wikidata.json", "w") as f:
        json.dump(result, f, indent=4)
    print(result)

asyncio.run(main())