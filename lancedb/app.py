"""
FastAPI app to serve search endpoints
"""
import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import lru_cache, partial

import lancedb
from fastapi import FastAPI, HTTPException, Query, Request
from sentence_transformers import SentenceTransformer

from config import Settings
from schemas.wine import FullTextSearchModel, SimilaritySearchModel

model_type = "sbert"
NUM_PROBES = 20


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
    app.model_type = "sbert"
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


def _fts_search(request: Request, terms: str) -> None:
    # In FTS, we limit to a max of 10K points to be more in line with Elasticsearch
    res = (
        request.app.table.search(terms, vector_column_name="to_vectorize")
        .select(["id", "points", "title", "description", "country", "price", "variety"])
        .limit(10000)
    )
    tbl = res.to_df().head(5).to_dict(orient="records")
    if not tbl:
        return None
    return tbl


def _similarity_search(
    request: Request,
    terms: str,
) -> list[SimilaritySearchModel] | None:
    query_vector = request.app.model.encode(terms.lower())
    search_result = (
        (
            request.app.table.search(query_vector)
            .metric("cosine")
            .nprobes(NUM_PROBES)
            .select(["id", "points", "title", "description", "country", "price", "variety"])
            .limit(5)
        )
        .to_df()
        .to_dict(orient="records")
    )
    if not search_result:
        return None
    return search_result


# --- app ---


@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "REST API for querying LanceDB database of 130k wine reviews from the Wine Enthusiast magazine"
    }


@app.get(
    "/fts_search",
    response_model=list[FullTextSearchModel],
    response_description="Search for wines via full-text keywords",
)
async def fts_search(
    request: Request,
    terms: str = Query(
        description="Specify terms to search for in the variety, title and description"
    ),
) -> list[FullTextSearchModel] | None:
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, partial(_fts_search, request, terms))

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No wine with the provided terms '{terms}' found in database - please try again",
        )
    return result


@app.get(
    "/similarity_search",
    response_model=list[SimilaritySearchModel],
    response_description="Search for wines via semantically similar terms",
)
async def similarity_search(
    request: Request,
    terms: str = Query(
        description="Specify terms to search for in the variety, title and description"
    ),
) -> list[SimilaritySearchModel] | None:
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, partial(_similarity_search, request, terms))
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No wine with the provided terms '{terms}' found in database - please try again",
        )
    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
