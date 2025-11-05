import logging
import os
import re
import time
from typing import Optional

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.errors import ServerSelectionTimeoutError

load_dotenv()
openai_client = OpenAI()
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

CLIENT = MongoClient(os.getenv("SERVER_URI"), server_api=ServerApi('1'))

class MongoDocument(BaseModel):
    category: str
    user_query: str
    sparql_query: str
    text_embedding: Optional[list[float]]


def check_doc_exists(
    category: str,
    user_query: str,
    sparql_query: str
) -> bool:
    query_collection = CLIENT.get_database("QueriesDatabase").get_collection("Queries")
    query_filter = {
            "category": category,
            "user_query": user_query,
            "sparql_query": sparql_query,
        }
    document = query_collection.find_one(query_filter)
    if document:
        return True
    else:
        return False


def prepare_docs_for_db() -> list[MongoDocument]:
    file_path = os.path.abspath("./SparqlAgent/querySparql.xlsx")
    file_path = os.path.abspath("/Users/lorenzofilitti/Desktop/SparqlAgent/querySparql.xlsx")
    df = pd.read_excel(file_path, sheet_name="Foglio1")

    try:
        docs = []
        for idx, row in df.iterrows():
            user_query = re.sub("\n", " ", row["question"])
            user_query = re.sub("\t", " ", user_query)

            s_query = re.sub("\n", " ", row["sparql_query"])
            s_query = re.sub("\t", " ", s_query)

            if not check_doc_exists(row["category"], user_query, s_query):
                docs.append(
                    MongoDocument(
                        category = row["category"],
                        user_query = user_query,
                        sparql_query = s_query,
                        text_embedding = None
                    )
                )

        logging.info(f"{len(docs)} documents collected.")
        return docs
    except Exception as e:
        logging.error(f"Error while preparing documents for the db: {e}", exc_info=True)
        return []


def generate_batches(docs: list[MongoDocument]) -> list[list[str]]:
    if docs:
        batch_size = 10
        contents = [doc.user_query for doc in docs]
        batches = []

        for i in range(0, len(contents), batch_size):
            batches.append(contents[i:i+batch_size])
        return batches
    else:
        return []


def get_embeddings(data: list[list[str]] | str) -> list[float] | list[list[float]]:
    embeddings = []
    try:
        if isinstance(data, str):
            emb = openai_client.embeddings.create(input=data, model="text-embedding-3-small", dimensions=768)
            return emb.data[0].embedding
        else:
            if data:
                for batch in data:
                    emb = openai_client.embeddings.create(input=batch, model="text-embedding-3-small", dimensions=768)
                    for item in emb.data:
                        embeddings.append(item.embedding)
                return embeddings
            else:
                return []
    except Exception as e:
        logging.error(f"Error while generating embeddings: {e}")
        return []

def add_embeddings_to_docs(docs: list[MongoDocument], embedding_list: list) -> Optional[list[MongoDocument]]:
    documents_with_emb = []
    try:
        if not docs:
            logging.info("Empty docs list")
            return None
        if not embedding_list:
            logging.info("Empty embedding list")
            return None

        for doc, embedding in zip(docs, embedding_list):
            document = MongoDocument(
                category = doc.category,
                user_query = doc.user_query,
                sparql_query = doc.sparql_query,
                text_embedding = embedding
            )
            documents_with_emb.append(document)

        return documents_with_emb
    except Exception as e:
        logging.error(f"Error while creating embeddings: {e}", exc_info=True)
        return []


def update_collection(docs: list[MongoDocument]) -> None:
    query_collection = CLIENT.get_database("QueriesDatabase").get_collection("Queries")
    try:
        if not docs:
            logging.info("Empty docs list")
            return None

        for doc in docs:
            query_filter = {
                    "category": doc.category,
                    "user_query": doc.user_query,
                    "sparql_query": doc.sparql_query,
                }
            document = query_collection.find_one(query_filter)

            if document:
                update_operation = {
                    "$set": {
                        "category": doc.category,
                        "user_query": doc.user_query,
                        "sparql_query": doc.sparql_query,
                        "text_embedding": doc.text_embedding
                    }
                    }
                query_collection.update_one(filter=query_filter, update=update_operation)
                logging.info(f"Found document with id '{document['_id']}'. Document has been updated.")

            else:
                insert_result = query_collection.insert_one(doc.model_dump())
                logging.info(f"Found new document. Document was added to the collection with id '{insert_result.inserted_id}'.")

    except Exception as e:
        logging.error(f"Error while updating collection: {e}", exc_info=True)
    finally:
        CLIENT.close()
        logging.info("MongoDB client connection closed.")


def run_vector_search(question: str, category: str) -> Optional[list[str]]:
    query_collection = CLIENT.get_database("QueriesDatabase").get_collection("Queries")
    try:
        _emb_start = time.time()
        embedded_query = get_embeddings(data=question)
        logging.info(f"Question embedding took: {time.time() - _emb_start} seconds")

        query = [{
            "$vectorSearch": {
                "exact": True,
                "filter": {"category": category},
                "index": "SparqlIndex",
                "limit": 5,
                "path": "text_embedding",
                "queryVector": embedded_query
            }
        }]
        
        query_results = query_collection.aggregate(query)
        filtered_query_results = [
            f""" 'question': {res["user_query"]}"\n'sparql_query': {res["sparql_query"]} """
            for res in query_results
        ]
        return filtered_query_results
    except ServerSelectionTimeoutError as e:
        logging.error(f"Mongo Server Timeout error (check if IP is valid): {e}")
        raise e
    except Exception as e:
        logging.error(f"Error during vector search: {e}")
        return None


def save_agent_queries(user_query: str, sparql_query: str, query_results: bool, agent_response: str):
    try:
        collection = CLIENT.get_database("QueriesDatabase").get_collection("AgentQueries")
        document = {
            "user_query": user_query,
            "sparql_query": sparql_query,
            "has_returned_results": query_results,
            "agent_response": agent_response
        }
        insert_result = collection.insert_one(document)
        logging.info(f"Added successful query to MongoDB: id = '{insert_result.inserted_id}'")
    except Exception as e:
        logging.error(f"Error while saving query results: {e}")


if __name__=="__main__":
    documents = prepare_docs_for_db()
    doc_batches = generate_batches(documents)
    embeddings = get_embeddings(data=doc_batches)
    docs_with_emb = add_embeddings_to_docs(documents, embeddings)
    if docs_with_emb:
        update_collection(docs_with_emb)
