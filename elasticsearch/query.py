"""
Run queries for full-text search and vector search and print out the results for inspection

Requires that a FastAPI server with search endpoints is running at the specified URL on port 8000
"""
import asyncio
from pathlib import Path
from typing import Any

import aiohttp
from aiohttp.client_exceptions import ContentTypeError
from codetiming import Timer

# Custom types
JsonBlob = dict[str, Any]

API_URL = "localhost"
API_PORT = 8000


def get_query_terms(filename: str) -> list[str]:
    assert filename.endswith(".txt")
    query_terms_file = Path("./benchmark_queries") / filename
    with open(query_terms_file, "r") as f:
        queries = f.readlines()
    assert queries
    result = [query.strip() for query in queries]
    return result


async def async_get(
    session: aiohttp.ClientSession,
    url: str,
    params: dict[str, str] | None = None,
) -> aiohttp.ClientResponse | None:
    """Helper method for async GET request with error handling for empty responses"""
    assert url is not None
    async with session.get(url, params=params) as response:
        try:
            response = await response.json()
            return response
        except ContentTypeError:
            return None


async def run_search(queries: list[str], url: str):
    async with aiohttp.ClientSession() as http_session:
        with Timer(text="Ran search in: {:.4f} sec"):
            tasks = [
                asyncio.create_task(async_get(http_session, url, params={"query": query}))
                for query in queries
            ]
            result = await asyncio.gather(*tasks)
            # print the first result description for each query
            for i, item in enumerate(result):
                print(f"Query [{queries[i]}]: {item[0]['description']}")


async def main():
    # FTS
    fts_endpoint = f"http://{API_URL}:{API_PORT}/fts_search"
    fts_queries = get_query_terms("keyword_terms.txt")
    await run_search(fts_queries, fts_endpoint)

    print("\n" + "-" * 80 + "\n")

    # Vector search
    vector_search_endpoint = f"http://{API_URL}:{API_PORT}/vector_search"
    vector_search_queries = get_query_terms("vector_terms.txt")
    await run_search(vector_search_queries, vector_search_endpoint)


if __name__ == "__main__":
    asyncio.run(main())
