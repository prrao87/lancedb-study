from typing import Any

import polars as pl
from config import Settings

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


async def fts_search(client: AsyncElasticsearch, keywords: str) -> None:
    keywords = keywords.lower()
    response = await client.search(
        index="wines",
        size=10,
        query={
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": keywords,
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


async def main():
    client = await get_elastic_client()
    assert await client.ping()
    # Query
    query = "tropical fruit"
    fts_result = await fts_search(client, query)
    # Close client
    await client.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
