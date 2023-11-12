import argparse
import asyncio
import aiohttp
from aiohttp.client_exceptions import ContentTypeError
from pathlib import Path
from typing import Any

from codetiming import Timer
from config import Settings
from pydantic_settings import BaseSettings
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


async def fts_search(session: aiohttp.ClientSession, endpoint: str, query: str) -> list[JsonBlob] | None:
    url = f"{endpoint}?query={query}"
    response = await async_get(session, url, headers=None)
    return response


async def main(keyword_terms: list[str]):
    FTS_URL = "http://localhost:8000/fts_search"
    VECTOR_SEARCH_URL = "http://localhost:8000/vector_search"



    async with aiohttp.ClientSession() as http_session:
        with Timer(text="Ran FTS search in: {:.4f} sec"):
            if args.search == "fts":
                tasks = [asyncio.create_task(fts_search(http_session, FTS_URL, query)) for query in keyword_terms]
            else:
                tasks = [asyncio.create_task(fts_search(http_session, VECTOR_SEARCH_URL, query)) for query in keyword_terms]
            res = await asyncio.gather(*tasks)
            print(f"Finished retrieving {len(res)} {args.search} search query results from Elasticsearch")


if __name__ == "__main__":
    # fmt: off
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", "-l", type=int, default=10, help="Number of search terms to randomly generate")
    parser.add_argument("--search", "-s", type=str, default="fts", help="Specify whether to do FTS or vector search")
    args = parser.parse_args()
    # fmt: on

    # Assert that the search type is only one of "fts" or "vector"
    assert args.search in ["fts", "vector"], "Please specify a valid search type: 'fts' or 'vector'"

    # Randomize search terms for a large list
    import random

    random.seed(37)

    keyword_terms = get_keyword_terms()
    random_choice_keywords = [random.choice(keyword_terms) for _ in range(args.limit)]

    asyncio.run(main(random_choice_keywords))
