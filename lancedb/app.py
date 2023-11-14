"""
FastAPI app to serve search endpoints
"""
import asyncio
from collections.abc import AsyncGenerator
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from functools import lru_cache

from config import Settings
from fastapi import FastAPI, HTTPException, Query, Request
from schemas.wine import SearchResult
from sentence_transformers import SentenceTransformer

import lancedb

executor = ThreadPoolExecutor(max_workers=8)

@lru_cache()
def get_settings():
    # Use lru_cache to avoid loading .env file for every request
    return Settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Async context manager for lancedb connection."""
    settings = get_settings()
    model_checkpoint = settings.embedding_model_checkpoint
    app.model = SentenceTransformer(model_checkpoint)
    # Define LanceDB client
    db = lancedb.connect("./winemag")
    app.table = db.open_table("wines")
    print("Successfully connected to LanceDB")
    yield
    print("Successfully closed LanceDB connection and released resources")


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


def _fts_search(request: Request, terms: str) -> list[SearchResult] | None:
    # In FTS, we limit to a max of 10K points to be more in line with Elasticsearch
    search_result = (
        request.app.table.search(terms, vector_column_name="description")
        .select(["id", "title", "description", "country", "variety", "price", "points"])
        .limit(10)
    ).to_pydantic(SearchResult)
    if not search_result:
        return None
    return search_result


def _vector_search(
    request: Request,
    terms: str,
) -> list[SearchResult] | None:
    query_vector = request.app.model.encode(terms.lower())
    search_result = (
        request.app.table.search(query_vector)
        .metric("cosine")
        .nprobes(20)
        .select(["id", "title", "description", "country", "variety", "price", "points"])
        .limit(10)
    ).to_pydantic(SearchResult)

    if not search_result:
        return None
    return search_result


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
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(executor, _fts_search, request, query)
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
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(executor, _vector_search, request, query)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No wine with the provided terms '{query}' found in database - please try again",
        )
    return result
