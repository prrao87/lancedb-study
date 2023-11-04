from typing import Any

import polars as pl
from config import Settings
from sentence_transformers import SentenceTransformer

from elasticsearch import AsyncElasticsearch

# Custom types
JsonBlob = dict[str, Any]


async def get_elastic_client() -> AsyncElasticsearch:
    settings = Settings()
    # Get environment variables
    USERNAME = settings.elastic_user
    PASSWORD = settings.elastic_password
    PORT = settings.elastic_port
    ELASTIC_URL = settings.elastic_url
    # Connect to ElasticSearch
    elastic_client = AsyncElasticsearch(
        f"http://{ELASTIC_URL}:{PORT}",
        basic_auth=(USERNAME, PASSWORD),
        request_timeout=300,
        max_retries=3,
        retry_on_timeout=True,
        verify_certs=False,
    )
    return elastic_client


async def fts_search(client: AsyncElasticsearch, query: str) -> None:
    response = await client.search(
        index="wines",
        size=10,
        query={
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query.lower(),
                            "fields": ["title", "description"],
                            "minimum_should_match": 2,
                            "fuzziness": "AUTO",
                        }
                    }
                ],
            }
        },
        sort={"points": {"order": "desc"}},
        _source=["id", "title", "description", "points", "price"],
    )
    result = response["hits"].get("hits")
    if result:
        data = [item["_source"] for item in result]
        df = pl.from_dicts(data)
        print(f"Full-text search result\n{df}")


async def vector_search(client: AsyncElasticsearch, query: str) -> None:
    query_vector = MODEL.encode(query.lower())
    response = await client.search(
        index="wines",
        size=10,
        query={
            "script_score": {
                "query": {"match_all": {}},
                "script": {
                    "source": "cosineSimilarity(params.queryVector, 'vector') + 1.0",
                    "params": {
                        "queryVector": query_vector,
                    },
                },
            }
        },
        sort={"points": {"order": "desc"}},
        _source=["id", "title", "description", "points", "price"],
    )
    result = response["hits"].get("hits")
    if result:
        data = [item["_source"] for item in result]
        df = pl.from_dicts(data)
        print(f"Full-text search result\n{df}")


async def main():
    client = await get_elastic_client()
    assert await client.ping()

    query = "tropical fruit"
    await fts_search(client, query)
    await vector_search(client, query)

    # Close client
    await client.close()


if __name__ == "__main__":
    import asyncio

    # Load a sentence transformer model for semantic similarity from a specified checkpoint
    model_id = Settings().embedding_model_checkpoint
    assert model_id, "Invalid embedding model checkpoint specified in .env file"
    MODEL = SentenceTransformer(model_id)

    asyncio.run(main())
