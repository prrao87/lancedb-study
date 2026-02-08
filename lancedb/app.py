"""FastAPI app to serve LanceDB search endpoints."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import lru_cache
import os
from pathlib import Path
import warnings

# Suppress verbose Rust-side Lance warnings in API logs.
os.environ.setdefault("RUST_LOG", "error")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="lancedb")

import lancedb
from fastapi import FastAPI, HTTPException, Query, Request
from sentence_transformers import SentenceTransformer

try:
    from .config import Settings
    from .schemas.wine import SearchResult
except ImportError:
    from config import Settings
    from schemas.wine import SearchResult

RESULT_COLUMNS = ["id", "title", "description", "country", "variety", "price", "points"]
FTS_RESULT_COLUMNS = [*RESULT_COLUMNS, "_score"]
VECTOR_RESULT_COLUMNS = [*RESULT_COLUMNS, "_distance"]
EMBEDDING_DIM = 256


@lru_cache()
def get_settings() -> Settings:
    return Settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Async context manager for LanceDB connection."""
    settings = get_settings()
    app.model = SentenceTransformer(settings.embedding_model_checkpoint)
    db_uri = Path(__file__).resolve().parent / settings.lancedb_dir
    app.db = await lancedb.connect_async(str(db_uri))
    app.table = await app.db.open_table("wines")
    print("Successfully connected to LanceDB")
    yield
    app.db.close()
    print("Successfully closed LanceDB connection and released resources")


app = FastAPI(
    title="REST API for wine reviews on LanceDB",
    description=(
        "Query from a LanceDB database of 130k wine reviews from the Wine Enthusiast magazine"
    ),
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {
        "message": "REST API for querying LanceDB database of 130k wine reviews from the Wine Enthusiast magazine"
    }


async def _fts_search(request: Request, terms: str) -> list[dict[str, object]] | None:
    query = await request.app.table.search(
        terms,
        query_type="fts",
        fts_columns=["description"],
    )
    result_table = await query.select(FTS_RESULT_COLUMNS).limit(10).to_arrow()
    if result_table.num_rows == 0:
        return None
    return result_table.to_pylist()


async def _vector_search(request: Request, terms: str) -> list[dict[str, object]] | None:
    query_vector = request.app.model.encode(
        f"search_query: {terms.strip().lower()}",
        show_progress_bar=False,
        convert_to_numpy=True,
        truncate_dim=EMBEDDING_DIM,
    )
    if len(query_vector.shape) != 1 or query_vector.shape[0] != EMBEDDING_DIM:
        raise ValueError(
            f"Expected query embedding shape ({EMBEDDING_DIM},), got {query_vector.shape}"
        )
    query = await request.app.table.search(
        query_vector.astype("float32", copy=False).tolist(),
        vector_column_name="vector",
        query_type="vector",
    )
    result_table = await (
        query.distance_type("cosine")
        .nprobes(10)
        .select(VECTOR_RESULT_COLUMNS)
        .limit(10)
        .to_arrow()
    )
    if result_table.num_rows == 0:
        return None
    return result_table.to_pylist()


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
) -> list[SearchResult]:
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
) -> list[SearchResult]:
    result = await _vector_search(request, query)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No wine with the provided terms '{query}' found in database - please try again",
        )
    return result
