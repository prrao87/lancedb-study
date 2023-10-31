import argparse
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator

import srsly
from codetiming import Timer
from config import Settings
from dotenv import load_dotenv
from rich import progress
from schemas.wine import Wine
from sentence_transformers import SentenceTransformer

from elasticsearch import Elasticsearch, helpers

load_dotenv()
# Custom types
JsonBlob = dict[str, Any]


class FileNotFoundError(Exception):
    pass


@lru_cache()
def get_settings():
    # Use lru_cache to avoid loading .env file for every request
    return Settings()


def chunk_iterable(item_list: list[JsonBlob], chunksize: int) -> Iterator[tuple[JsonBlob, ...]]:
    """
    Break a large iterable into an iterable of smaller iterables of size `chunksize`
    """
    for i in range(0, len(item_list), chunksize):
        yield tuple(item_list[i : i + chunksize])


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


def create_index(client: Elasticsearch, index: str, mappings_path: Path) -> None:
    """Create an index associated with an alias in ElasticSearch"""
    elastic_config = dict(srsly.read_json(mappings_path))
    assert elastic_config is not None

    exists_alias = client.indices.exists_alias(name=index)
    if not exists_alias:
        print(f"Did not find index {index} in db, creating index...\n")
        #  Get settings and mappings from the mappings.json file
        mappings = elastic_config.get("mappings")
        settings = elastic_config.get("settings")
        index_name = f"{index}-1"
        try:
            client.indices.create(index=index_name, mappings=mappings, settings=settings)
            client.indices.put_alias(index=index_name, name=INDEX_ALIAS)
            # Verify that the new index has been created
            assert client.indices.exists(index=index_name)
            index_and_alias = client.indices.get_alias(index=index_name)
            print(index_and_alias)
        except Exception as e:
            print(f"Warning: Did not create index {index_name} due to exception {e}\n")
    else:
        print(f"Found index {index} in db, skipping index creation...\n")


def add_vectors_to_index(data_chunk: tuple[JsonBlob, ...], index: str) -> None:
    elastic_client = get_elastic_client(get_settings())
    assert elastic_client.ping()
    # Load a sentence transformer model for semantic similarity from a specified checkpoint
    model_id = get_settings().embedding_model_checkpoint
    assert model_id, "Invalid embedding model checkpoint specified in .env file"
    MODEL = SentenceTransformer(model_id)

    ids = [item["id"] for item in data_chunk]
    to_vectorize = [text.pop("to_vectorize") for text in data_chunk]
    vectors = [list(MODEL.encode(sentence.lower())) for sentence in to_vectorize]
    data_batch = [{**d, "vector": vector} for d, vector in zip(data_chunk, vectors)]
    for success, info in helpers.streaming_bulk(
        elastic_client,
        data_batch,
        index=index,
    ):
        if not success:
            print("A document failed:", info)


def main(data: list[JsonBlob]) -> None:
    elastic_client = get_elastic_client(get_settings())
    assert elastic_client.ping()
    create_index(elastic_client, INDEX_ALIAS, Path("mapping/mapping.json"))

    # Validate data and chunk it for ingesting in batches
    with Timer(
        name="Data validation in pydantic",
        text="Validated data using Pydantic in {:.4f} sec",
    ):
        validated_data = validate(data, exclude_none=False)

    chunked_data = chunk_iterable(validated_data, CHUNKSIZE)

    # Add rich progress bar
    with progress.Progress(
        "[progress.description]{task.description}",
        progress.BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        progress.TimeElapsedColumn(),
    ) as prog:
        overall_progress_task = prog.add_task(
            "Vectorizing the required data...", total=len(validated_data) // CHUNKSIZE
        )
        for chunk in chunked_data:
            add_vectors_to_index(chunk, INDEX_ALIAS)
            prog.update(overall_progress_task, advance=1)

    # Close Elasticsearch client
    elastic_client.close()


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

    # Specify an alias to index the data under
    INDEX_ALIAS = get_settings().elastic_index_alias
    assert INDEX_ALIAS

    data = list(get_json_data(DATA_DIR, FILENAME))
    if LIMIT > 0:
        data = data[:LIMIT]

    with Timer(name="Indexing data", text="Indexed data in {:.4f} sec"):
        if data:
            main(data)
