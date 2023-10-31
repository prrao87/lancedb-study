import argparse
import os
import shutil
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator

import srsly
from codetiming import Timer
from config import Settings
from dotenv import load_dotenv
from rich import progress
from schemas.wine import LanceModelWine, Wine
from sentence_transformers import SentenceTransformer

import lancedb
from lancedb.pydantic import pydantic_to_schema
from lancedb.table import Table

load_dotenv()
# Custom types
JsonBlob = dict[str, Any]


class FileNotFoundError(Exception):
    pass


@lru_cache()
def get_settings():
    # Use lru_cache to avoid loading .env file for every request
    return Settings()


def chunk_iterable(item_list: list[JsonBlob], chunksize: int) -> Iterator[list[JsonBlob]]:
    """
    Break a large iterable into an iterable of smaller iterables of size `chunksize`
    """
    for i in range(0, len(item_list), chunksize):
        yield item_list[i : i + chunksize]


def get_json_data(data_dir: Path, filename: str) -> list[JsonBlob]:
    """Get all line-delimited json files (.jsonl) from a directory with a given prefix"""
    file_path = data_dir / filename
    if not file_path.is_file():
        # File may not have been uncompressed yet so try to do that first
        data = srsly.read_gzip_jsonl(file_path)
        # This time if it isn't there it really doesn't exist
        if not file_path.is_file():
            raise FileNotFoundError(f"No valid .jsonl file found in `{data_dir}`")
    else:
        data = srsly.read_gzip_jsonl(file_path)
    return data


def validate(
    data: list[JsonBlob],
    exclude_none: bool = False,
) -> list[JsonBlob]:
    validated_data = [Wine(**item).model_dump(exclude_none=exclude_none) for item in data]
    return validated_data


def embed_func(batch: list[str], model) -> list[list[float]]:
    return [model.encode(sentence.lower()) for sentence in batch]


def vectorize_text(data: list[JsonBlob]) -> list[LanceModelWine] | None:
    # Load a sentence transformer model for semantic similarity from a specified checkpoint
    model_id = get_settings().embedding_model_checkpoint
    assert model_id, "Invalid embedding model checkpoint specified in .env file"
    MODEL = SentenceTransformer(model_id)

    ids = [item["id"] for item in data]
    to_vectorize = [text.get("to_vectorize") for text in data]
    vectors = embed_func(to_vectorize, MODEL)
    try:
        data_batch = [{**d, "vector": vector} for d, vector in zip(data, vectors)]
    except Exception as e:
        print(f"{e}: Failed to add ID range {min(ids)}-{max(ids)}")
        return None
    return data_batch


def embed_batches(tbl: str, validated_data: list[JsonBlob]) -> Table:
    """Ingest embed vector batches of data via multi-processing for ANN index"""
    chunked_data = chunk_iterable(validated_data, CHUNKSIZE)
    print(f"Adding vectors to table for ANN index...")
    # Add rich progress bar
    with progress.Progress(
        "[progress.description]{task.description}",
        progress.BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        progress.TimeElapsedColumn(),
    ) as prog:
        overall_progress_task = prog.add_task(
            "Starting vectorization...", total=len(validated_data) // CHUNKSIZE
        )
        for chunk in chunked_data:
            batch = vectorize_text(chunk)
            prog.update(overall_progress_task, advance=1)
            tbl.add(batch, mode="append")


def main(tbl: Table, data: list[JsonBlob]) -> None:
    """Generate sentence embeddings and create ANN and FTS indexes"""
    with Timer(
        name="Data validation in pydantic",
        text="Validated data using Pydantic in {:.4f} sec",
    ):
        validated_data = validate(data, exclude_none=False)

    with Timer(
        name="Insert vectors in batches",
        text="Created sentence embeddings in {:.4f} sec",
    ):
        embed_batches(tbl, validated_data)
        print(f"Finished inserting {len(tbl)} vectors into LanceDB table")

    with Timer(name="Create ANN index", text="Created ANN index in {:.4f} sec"):
        print("Creating ANN index...")
        # Creating IVF-PQ index for now, as we eagerly await DiskANN
        # Choose num partitions as a power of 2 that's closest to len(dataset) // 5000
        # In this case, we have 130k datapoints, so the nearest power of 2 is 130000//5000 ~ 32)
        tbl.create_index(metric="cosine", num_partitions=32, num_sub_vectors=96)

    with Timer(name="Create FTS index", text="Created FTS index in {:.4f} sec"):
        # Create a full-text search index via Tantivy (which implements Lucene + BM25 in Rust)
        tbl.create_fts_index(["to_vectorize"])


if __name__ == "__main__":
    # fmt: off
    parser = argparse.ArgumentParser("Bulk index database from the wine reviews JSONL data")
    parser.add_argument("--limit", "-l", type=int, default=0, help="Limit the size of the dataset to load for testing purposes")
    parser.add_argument("--chunksize", type=int, default=1000, help="Size of each chunk to break the dataset into before processing")
    parser.add_argument("--filename", type=str, default="winemag-data-130k-v2.jsonl.gz", help="Name of the JSONL zip file to use")
    parser.add_argument("--workers", type=int, default=4, help="Number of workers to use for vectorization")
    args = vars(parser.parse_args())
    # fmt: on

    LIMIT = args["limit"]
    DATA_DIR = Path(__file__).parents[1] / "data"
    FILENAME = args["filename"]
    CHUNKSIZE = args["chunksize"]
    WORKERS = args["workers"]

    data = list(get_json_data(DATA_DIR, FILENAME))
    assert data, "No data found in the specified file"
    data = data[:LIMIT] if LIMIT > 0 else data

    DB_NAME = "./winemag"
    TABLE = "wines"
    if os.path.exists(DB_NAME):
        shutil.rmtree(DB_NAME)

    db = lancedb.connect(DB_NAME)
    try:
        tbl = db.create_table(TABLE, schema=pydantic_to_schema(LanceModelWine), mode="create")
    except OSError:
        tbl = db.open_table(TABLE)

    main(tbl, data)
    print("Finished execution!")
