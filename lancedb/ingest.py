"""Ingest wine-review data into LanceDB with sentence embeddings."""

from __future__ import annotations

import argparse
from functools import lru_cache
from pathlib import Path
from time import perf_counter
from typing import Any, Iterator

import lancedb
import srsly
from config import Settings
from lancedb.pydantic import pydantic_to_schema
from rich import progress
from schemas.wine import LanceModelWine, Wine
from sentence_transformers import SentenceTransformer

JsonBlob = dict[str, Any]
EMBEDDING_DIM = 256


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def chunk_iterable(item_list: list[JsonBlob], chunksize: int) -> Iterator[list[JsonBlob]]:
    for i in range(0, len(item_list), chunksize):
        yield item_list[i : i + chunksize]


def get_json_data(data_dir: Path, filename: str) -> list[JsonBlob]:
    file_path = data_dir / filename
    if not file_path.is_file():
        raise FileNotFoundError(f"No valid .jsonl.gz file found at `{file_path}`")
    return list(srsly.read_gzip_jsonl(file_path))


def validate(data: list[JsonBlob], exclude_none: bool = False) -> list[JsonBlob]:
    return [Wine(**item).model_dump(exclude_none=exclude_none) for item in data]


def format_document_text(text: str) -> str:
    return f"search_document: {text.strip().lower()}"


async def get_or_create_table(
    db: lancedb.db.AsyncConnection,
    table_name: str,
    overwrite: bool,
) -> lancedb.table.AsyncTable:
    if overwrite:
        return await db.create_table(
            table_name,
            schema=pydantic_to_schema(LanceModelWine),
            mode="overwrite",
        )

    table_names = await db.table_names()
    if table_name in table_names:
        table = await db.open_table(table_name)
        schema = await table.schema()
        vector_type = schema.field("vector").type if "vector" in schema.names else None
        existing_dim = getattr(vector_type, "list_size", None)
        if existing_dim is not None and existing_dim != EMBEDDING_DIM:
            raise ValueError(
                f"Existing table '{table_name}' has vector dim={existing_dim}, "
                f"but current ingest expects dim={EMBEDDING_DIM}. "
                "Re-run with --overwrite to recreate the table."
            )
        return table

    return await db.create_table(
        table_name,
        schema=pydantic_to_schema(LanceModelWine),
        mode="create",
    )


async def embed_batches(
    table: lancedb.table.AsyncTable,
    validated_data: list[JsonBlob],
    model: SentenceTransformer,
    chunksize: int,
) -> None:
    chunked_data = chunk_iterable(validated_data, chunksize)
    print("Adding vectors to table for ANN index...")

    total_chunks = (len(validated_data) + chunksize - 1) // chunksize
    with progress.Progress(
        "[progress.description]{task.description}",
        progress.BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        progress.TimeElapsedColumn(),
    ) as prog:
        task = prog.add_task("Vectorizing and ingesting...", total=total_chunks)
        for chunk in chunked_data:
            to_vectorize = [row.get("to_vectorize", "") for row in chunk]
            vectors = model.encode(
                [format_document_text(text) for text in to_vectorize],
                show_progress_bar=False,
                convert_to_numpy=True,
                truncate_dim=EMBEDDING_DIM,
            )
            if len(vectors.shape) != 2 or vectors.shape[1] != EMBEDDING_DIM:
                raise ValueError(
                    f"Expected embedding shape (N, {EMBEDDING_DIM}), got {vectors.shape}"
                )
            batch = [
                {
                    **row,
                    "vector": vector.astype("float32", copy=False).tolist(),
                }
                for row, vector in zip(chunk, vectors, strict=True)
            ]
            await table.add(batch, mode="append")
            prog.update(task, advance=1)


async def main() -> None:
    parser = argparse.ArgumentParser("Bulk ingest LanceDB data from wine reviews JSONL")
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=0,
        help="Limit the size of the dataset to ingest",
    )
    parser.add_argument(
        "--chunksize",
        type=int,
        default=1000,
        help="Size of each chunk to ingest",
    )
    parser.add_argument(
        "--filename",
        type=str,
        default="winemag-data-130k-v2.jsonl.gz",
        help="Name of the JSONL gzip file",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the `wines` table before ingesting",
    )
    args = parser.parse_args()

    data_dir = Path(__file__).resolve().parents[1] / "data"
    data = get_json_data(data_dir, args.filename)
    if args.limit > 0:
        data = data[: args.limit]

    if not data:
        raise ValueError("No data found in the specified file")

    settings = get_settings()
    model = SentenceTransformer(settings.embedding_model_checkpoint)

    validate_start = perf_counter()
    validated_data = validate(data, exclude_none=False)
    validate_elapsed = perf_counter() - validate_start
    print(f"Validated {len(validated_data)} rows in {validate_elapsed:.4f}s")

    db_uri = Path(__file__).resolve().parent / settings.lancedb_dir
    db = await lancedb.connect_async(str(db_uri))
    table = await get_or_create_table(db, "wines", overwrite=args.overwrite)

    ingest_start = perf_counter()
    await embed_batches(table, validated_data, model, args.chunksize)
    ingest_elapsed = perf_counter() - ingest_start
    print(f"Ingested {len(validated_data)} rows with vectors in {ingest_elapsed:.4f}s")

    db.close()
    print("Finished execution!")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
