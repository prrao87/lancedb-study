import argparse
import asyncio
from pathlib import Path
from typing import Any

from codetiming import Timer
from regex import B
from config import Settings
from dotenv import load_dotenv

from elasticsearch import AsyncElasticsearch

load_dotenv()
# Custom types
JsonBlob = dict[str, Any]


def get_keyword_terms() -> list[str]:
    keywords_file = Path(".") / "keyword_terms.txt"
    with open(keywords_file, "r") as f:
        keywords = f.readlines()
    assert keywords
    result = [keyword.strip() for keyword in keywords]
    return result


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


async def fts_search(client: AsyncElasticsearch, query: str) -> list[JsonBlob]:
    response = await client.search(
        index="wines",
        size=10_000,
        query={
            "match": {
                "description": {
                    "query": query,
                }
            }
        },
    )
    result = response["hits"].get("hits")
    if result:
        data = [item["_source"] for item in result][:10]
    else:
        data = {}
    return data


async def main(keyword_terms: list[str]):
    with Timer(text="Obtained Elastic client in: {:.4f} sec"):
        client = await get_elastic_client()
        assert await client.ping()

    with Timer(text="Ran FTS search in: {:.4f} sec"):
        tasks = [asyncio.create_task(fts_search(client, query)) for query in keyword_terms]
        res = await asyncio.gather(*tasks)
        print(f"Finished retrieving {len(res)} FTS query results from Elasticsearch")

    # Close client
    await client.close()


if __name__ == "__main__":
    # fmt: off
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", "-l", type=int, default=10, help="Number of search terms to randomly generate")
    args = parser.parse_args()
    # fmt: on

    # Randomize search terms for a large list
    import random

    random.seed(37)

    keyword_terms = get_keyword_terms()
    random_choice_keywords = [random.choice(keyword_terms) for _ in range(args.limit)]

    asyncio.run(main(random_choice_keywords))
