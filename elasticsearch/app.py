"""
FastAPI app to serve search endpoints
"""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Query, Request
from sentence_transformers import SentenceTransformer

from elasticsearch import AsyncElasticsearch

try:
    from .config import Settings
    from .schemas.wine import SearchResult
except ImportError:
    from config import Settings
    from schemas.wine import SearchResult

EMBEDDING_DIM = 256


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
    title="REST API for wine reviews on Elasticsearch",
    description=(
        "Query from an Elasticsearch index of 130k wine reviews from the Wine Enthusiast magazine"
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# --- app ---


@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "REST API for querying Elasticsearch index of 130k wine reviews from the Wine Enthusiast magazine"
    }


# --- Search functions ---


async def _fts_search(request: Request, query: str) -> list[SearchResult] | None:
    response = await request.app.client.search(
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


async def _vector_search(request: Request, query: str) -> list[SearchResult] | None:
    query_vector = request.app.model.encode(
        f"search_query: {query.strip().lower()}",
        show_progress_bar=False,
        convert_to_numpy=True,
        truncate_dim=EMBEDDING_DIM,
    )
    if len(query_vector.shape) != 1 or query_vector.shape[0] != EMBEDDING_DIM:
        raise ValueError(
            f"Expected query embedding shape ({EMBEDDING_DIM},), got {query_vector.shape}"
        )
    response = await request.app.client.search(
        index="wines",
        size=10,
        query={
            "script_score": {
                "query": {"match_all": {}},
                "script": {
                    "source": "cosineSimilarity(params.queryVector, 'vector') + 1.0",
                    "params": {
                        "queryVector": query_vector.astype("float32", copy=False).tolist(),
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
