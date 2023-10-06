"""
FastAPI app to serve search endpoints
"""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import lru_cache

import lancedb
from fastapi import FastAPI, HTTPException, Query, Request
from sentence_transformers import SentenceTransformer

from config import Settings
from schemas.wine import SimilaritySearch

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


def _search_by_similarity(
    request: Request,
    terms: str,
) -> list[SimilaritySearch] | None:
    query_vector = request.app.model.encode(terms.lower())
    search_result = (
        request.app.table.search(query_vector)
        .metric("cosine")
        .nprobes(NUM_PROBES)
        .select(["id", "points", "title", "description", "country", "price", "variety"])
        .limit(5)
    ).to_df().to_dict(orient="records")
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
    "/search",
    response_model=list[SimilaritySearch],
    response_description="Search for wines via semantically similar terms",
)
def search_by_similarity(
    request: Request,
    terms: str = Query(
        description="Specify terms to search for in the variety, title and description"
    ),
) -> list[SimilaritySearch] | None:
    result = _search_by_similarity(request, terms)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No wine with the provided terms '{terms}' found in database - please try again",
        )
    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)