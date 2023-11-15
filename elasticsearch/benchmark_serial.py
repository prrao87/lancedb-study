"""
Run this script to benchmark the serial search performance of FTS and vector search
"""
import argparse
import random
from functools import lru_cache
from pathlib import Path
from typing import Any

from codetiming import Timer
from config import Settings
from dotenv import load_dotenv
from rich import progress
from schemas.wine import SearchResult
from sentence_transformers import SentenceTransformer

from elasticsearch import Elasticsearch

load_dotenv()
# Custom types
JsonBlob = dict[str, Any]


@lru_cache()
def get_settings():
    # Use lru_cache to avoid loading .env file for every request
    return Settings()


def get_query_terms(filename: str) -> list[str]:
    assert filename.endswith(".txt")
    query_terms_file = Path("./benchmark_queries") / filename
    with open(query_terms_file, "r") as f:
        queries = f.readlines()
    assert queries
    result = [query.strip() for query in queries]
    return result


def get_elastic_client(settings) -> Elasticsearch:
    # Get environment variables
    USERNAME = settings.elastic_user
    PASSWORD = settings.elastic_password
    PORT = settings.elastic_port
    ELASTIC_URL = settings.elastic_url
    # Connect to ElasticSearch
    elastic_client = Elasticsearch(
        f"http://{ELASTIC_URL}:{PORT}",
        basic_auth=(USERNAME, PASSWORD),
        request_timeout=300,
        max_retries=3,
        retry_on_timeout=True,
        verify_certs=False,
    )
    return elastic_client


def fts_search(client: Elasticsearch, query: str) -> list[SearchResult] | None:
    response = client.search(
        index="wines",
        size=10,
        query={
            "match": {
                "description": {
                    "query": query,
                }
            }
        },
        _source=["id", "title", "description", "country", "variety", "price", "points"],
    )
    result = response["hits"].get("hits")
    if result:
        return [item["_source"] for item in result]
    else:
        return None


def vector_search(model, client: Elasticsearch, query: str) -> list[SearchResult] | None:
    query_vector = model.encode(query.lower()).tolist()
    response = client.search(
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
        _source=["id", "title", "description", "country", "variety", "price", "points"],
    )
    result = response["hits"].get("hits")
    if result:
        return [item["_source"] for item in result]
    else:
        return None


def main():
    if args.search == "fts":
        URL = "http://localhost:8000/fts_search"
        queries = get_query_terms("keyword_terms.txt")
    else:
        URL = "http://localhost:8000/vector_search"
        queries = get_query_terms("vector_terms.txt")

    random_choice_queries = [random.choice(queries) for _ in range(LIMIT)]

    # Run the search directly on the Elasticsearch DB
    elastic_client = get_elastic_client(get_settings())
    assert elastic_client.ping()

    # Run the search directly on the Elasticsearch DB
    with Timer(name="Serial search", text="Finished search in {:.4f} sec"):
        # Add rich progress bar
        with progress.Progress(
            "[progress.description]{task.description}",
            progress.BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            progress.TimeElapsedColumn(),
        ) as prog:
            overall_progress_task = prog.add_task(
                f"Performing {args.search} search", total=len(random_choice_queries)
            )
            for query in random_choice_queries:
                if args.search == "fts":
                    _ = fts_search(elastic_client, query)
                else:
                    _ = vector_search(MODEL, elastic_client, query)
                prog.update(overall_progress_task, advance=1)


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

    # Load a sentence transformer model for semantic similarity from a specified checkpoint
    model_id = get_settings().embedding_model_checkpoint
    assert model_id, "Invalid embedding model checkpoint specified in .env file"
    MODEL = SentenceTransformer(model_id)

    main()
