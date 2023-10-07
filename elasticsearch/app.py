"""
FastAPI app to serve search endpoints
"""
import warnings
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import lru_cache

from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI, HTTPException, Query, Request

from config import Settings
from schemas.wine import FullTextSearchModel


@lru_cache()
def get_settings():
    # Use lru_cache to avoid loading .env file for every request
    return Settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Async context manager for Elasticsearch connection."""
    settings = get_settings()
    username = settings.elastic_user
    password = settings.elastic_password
    port = settings.elastic_port
    service = settings.elastic_service
    print(f"Connecting to Elasticsearch at {service}:{port}")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        elastic_client = AsyncElasticsearch(
            f"http://{service}:{port}",
            basic_auth=(username, password),
            request_timeout=60,
            max_retries=3,
            retry_on_timeout=True,
            verify_certs=False,
        )
        """Async context manager for Elasticsearch connection."""
        app.client = elastic_client
        print("Successfully connected to Elasticsearch")
        yield
        await elastic_client.close()
        print("Successfully closed Elasticsearch connection")


app = FastAPI(
    title="REST API for wine reviews on Elasticsearch",
    description=(
        "Query from a Elasticsearch database of 130k wine reviews from the Wine Enthusiast magazine"
    ),
    version="0.1.0",
    lifespan=lifespan,
)


async def _fts_search(client: AsyncElasticsearch, keywords: str) -> None:
    keywords = keywords.lower()
    response = await client.search(
        index="wines",
        size=5,
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
        _source=["id", "points", "title", "description", "country", "price", "variety"],
    )
    result = response["hits"].get("hits")
    if result:
        data = [item["_source"] for item in result]
        return data
    return None


# --- app ---

@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "REST API for querying Elasticsearch database of 130k wine reviews from the Wine Enthusiast magazine"
    }


@app.get(
    "/search",
    response_model=list[FullTextSearchModel],
    response_description="Search for wines via keywords",
)
async def search_by_keywords(
    request: Request,
    terms: str = Query(
        description="Specify terms to search for in the variety, title and description"
    ),
) -> list[FullTextSearchModel] | None:
    result = await _fts_search(request.app.client, terms)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No wine with the provided terms '{terms}' found in database - please try again",
        )
    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)