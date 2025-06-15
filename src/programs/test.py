from src.programs.tools import DB_search
import asyncio

res = asyncio.run(DB_search("select ?author where {?doc a powla:Document; dc:title ?title; dcterms:creator ?author} limit 5"))

print(res)