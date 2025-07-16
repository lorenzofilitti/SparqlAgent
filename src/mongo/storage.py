import os

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

import json

pw = os.environ.get("PASSWORD")
uri = "mongodb+srv://filittilorenzo2:BkzE1BhwcZ69GJzK@sparqlagentcluster.nfe5lhw.mongodb.net/?retryWrites=true&w=majority&appName=SparqlAgentCluster"

client = MongoClient(uri, server_api=ServerApi('1'))

database = client["SparqlAgent-db"]

with open("/Users/lorenzofilitti/Desktop/SparqlAgent/suffixes.json", "r") as s:
    affixes = json.load(s)

affixes_collection = database["Affixes"]

res = affixes_collection.find({"in": {"$exists": True}})
for r in res:
    print(r)