"""
Run this script to benchmark the concurrent search performance of the FTS and vector search
via REST API endpoints.
"""
import argparse
import asyncio
import random
from pathlib import Path
from typing import Any

import aiohttp
from aiohttp.client_exceptions import ContentTypeError
from codetiming import Timer
from dotenv import load_dotenv

load_dotenv()
# Custom types
JsonBlob = dict[str, Any]


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
    headers: dict[str, str] | None,
    params: dict[str, str] | None = None,
) -> aiohttp.ClientResponse | None:
    """Helper method for async GET request with error handling for empty responses"""
    assert url is not None
    async with session.get(url, headers=headers, params=params) as response:
        try:
            response = await response.json()
            return response
        except ContentTypeError:
            return None


async def search_for_result(
    session: aiohttp.ClientSession, endpoint: str, query: str
) -> list[JsonBlob] | None:
    url = f"{endpoint}?query={query}"
    response = await async_get(session, url, headers=None)
    return response


async def main():
    if args.search == "fts":
        URL = "http://localhost:8000/fts_search"
        queries = get_query_terms("keyword_terms.txt")
    else:
        URL = "http://localhost:8000/vector_search"
        queries = get_query_terms("vector_terms.txt")

    random_choice_queries = [random.choice(queries) for _ in range(LIMIT)]

    async with aiohttp.ClientSession() as http_session:
        with Timer(text="Ran search in: {:.4f} sec"):
            tasks = [
                asyncio.create_task(search_for_result(http_session, URL, query))
                for query in random_choice_queries
            ]
            res = await asyncio.gather(*tasks)
            print(f"Finished retrieving {len(res)} {args.search} search query results")


if __name__ == "__main__":
    # fmt: off
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=37, help="Seed for random number generator")
    parser.add_argument("--limit", "-l", type=int, default=10, help="Number of search terms to randomly generate")
    parser.add_argument("--search", type=str, default="fts", help="Specify whether to do FTS or vector search")
    args = parser.parse_args()
    # fmt: on

    LIMIT = args.limit
    SEED = args.seed

    # Assert that the search type is only one of "fts" or "vector"
    assert args.search in ["fts", "vector"], "Please specify a valid search type: 'fts' or 'vector'"

    asyncio.run(main())
