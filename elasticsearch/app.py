"""
FastAPI app to serve search endpoints
"""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import lru_cache

from config import Settings
from fastapi import FastAPI, HTTPException, Query, Request
from schemas.wine import SearchResult
from sentence_transformers import SentenceTransformer

from elasticsearch import AsyncElasticsearch


@lru_cache()
def get_settings():
    # Use lru_cache to avoid loading .env file for every request
    return Settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Async context manager for Elasticsearch connection."""
    settings = get_settings()
    app.model = SentenceTransformer(settings.embedding_model_checkpoint)

    username = settings.elastic_user
    password = settings.elastic_password
    port = settings.elastic_port
    service = settings.elastic_url
    elastic_client = AsyncElasticsearch(
        f"http://{service}:{port}",
        basic_auth=(username, password),
        request_timeout=60,
        max_retries=3,
        retry_on_timeout=True,
        verify_certs=False,
    )
    app.client = elastic_client
    print("Successfully connected to Elasticsearch")
    yield
    await elastic_client.close()
    print("Successfully closed Elasticsearch connection")


app = FastAPI(
    title="REST API for wine reviews on LanceDB",
    description=(
        "Query from a LanceDB database of 130k wine reviews from the Wine Enthusiast magazine"
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# --- app ---


@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "REST API for querying LanceDB database of 130k wine reviews from the Wine Enthusiast magazine"
    }


# --- Search functions ---


async def _fts_search(request: Request, query: str) -> list[SearchResult] | None:
    response = await request.app.client.search(
        index="wines",
        size=10_000,
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
        return [item["_source"] for item in result][:10]
    else:
        return None


async def _vector_search(request: Request, query: str) -> list[SearchResult] | None:
    query_vector = request.app.model.encode(query.lower()).tolist()
    response = await request.app.client.search(
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


# --- Endpoints ---


@app.get(
    "/fts_search",
    response_model=list[SearchResult],
    response_description="Search for wines via full-text keywords",
)
async def fts_search(
    request: Request,
    query: str = Query(
        description="Specify terms to search for in the variety, title and description"
    ),
) -> list[SearchResult] | None:
    result = await _fts_search(request, query)

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No wine with the provided terms '{query}' found in database - please try again",
        )
    return result


@app.get(
    "/vector_search",
    response_model=list[SearchResult],
    response_description="Search for wines via semantically similar terms",
)
async def vector_search(
    request: Request,
    query: str = Query(
        description="Specify terms to search for in the variety, title and description"
    ),
) -> list[SearchResult] | None:
    result = await _vector_search(request, query)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No wine with the provided terms '{query}' found in database - please try again",
        )
    return result
