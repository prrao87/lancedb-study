"""Run fixed FTS and vector queries for qualitative inspection."""

import asyncio
from pathlib import Path
from time import perf_counter

import aiohttp
from aiohttp.client_exceptions import ContentTypeError

API_URL = "localhost"
API_PORT = 8000

QUERY_FILES = {
    "fts": "keyword_terms.txt",
    "vector": "vector_terms.txt",
}


def get_query_terms(search_type: str) -> list[str]:
    query_dir = Path(__file__).resolve().parents[1] / "bench_queries"
    query_terms_file = query_dir / QUERY_FILES[search_type]
    with open(query_terms_file, "r", encoding="utf-8") as f:
        queries = [line.strip() for line in f.readlines() if line.strip()]
    if not queries:
        raise ValueError(f"No query terms found in {query_terms_file}")
    return queries


async def async_get(
    session: aiohttp.ClientSession,
    url: str,
    params: dict[str, str] | None = None,
) -> dict | list | None:
    async with session.get(url, params=params) as response:
        if response.status != 200:
            return None
        try:
            return await response.json()
        except ContentTypeError:
            return None


async def run_search(queries: list[str], endpoint: str) -> None:
    async with aiohttp.ClientSession() as session:
        start = perf_counter()
        tasks = [
            asyncio.create_task(async_get(session, endpoint, params={"query": query}))
            for query in queries
        ]
        results = await asyncio.gather(*tasks)
        elapsed = perf_counter() - start

    for i, item in enumerate(results):
        if item:
            print(f"Query [{queries[i]}]: {item[0]['description']}")
        else:
            print(f"Query [{queries[i]}]: <no result>")
    print(f"Ran search in: {elapsed:.4f} sec")


async def main() -> None:
    fts_endpoint = f"http://{API_URL}:{API_PORT}/fts_search"
    await run_search(get_query_terms("fts"), fts_endpoint)

    print("\n" + "-" * 80 + "\n")

    vector_endpoint = f"http://{API_URL}:{API_PORT}/vector_search"
    await run_search(get_query_terms("vector"), vector_endpoint)


if __name__ == "__main__":
    asyncio.run(main())
