"""Ingest wine-review data into Elasticsearch with sentence embeddings."""

import argparse
from functools import lru_cache
from pathlib import Path
from time import perf_counter
from typing import Any, Iterator

import srsly
from config import Settings
from elasticsearch.helpers import BulkIndexError
from rich import progress
from schemas.wine import Wine
from sentence_transformers import SentenceTransformer

from elasticsearch import Elasticsearch, helpers

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


def get_elastic_client(settings: Settings) -> Elasticsearch:
    return Elasticsearch(
        f"http://{settings.elastic_url}:{settings.elastic_port}",
        basic_auth=(settings.elastic_user, settings.elastic_password),
        request_timeout=300,
        max_retries=3,
        retry_on_timeout=True,
        verify_certs=False,
    )


def create_index_if_needed(client: Elasticsearch, index_alias: str, mappings_path: Path) -> None:
    elastic_config = dict(srsly.read_json(mappings_path))
    mappings = elastic_config.get("mappings")
    settings = elastic_config.get("settings")

    if client.indices.exists_alias(name=index_alias):
        print(f"Found index alias `{index_alias}`, skipping creation")
        return

    index_name = f"{index_alias}-1"
    print(f"Did not find alias `{index_alias}`, creating index `{index_name}`")
    client.indices.create(index=index_name, mappings=mappings, settings=settings)
    client.indices.put_alias(index=index_name, name=index_alias)


def get_vector_dims_for_alias(client: Elasticsearch, index_alias: str) -> int | None:
    if not client.indices.exists_alias(name=index_alias):
        return None
    mapping = client.indices.get_mapping(index=index_alias)
    for index_mapping in mapping.values():
        dims = (
            index_mapping.get("mappings", {})
            .get("properties", {})
            .get("vector", {})
            .get("dims")
        )
        if dims is not None:
            return int(dims)
    return None


def drop_alias_indices(client: Elasticsearch, index_alias: str) -> None:
    if not client.indices.exists_alias(name=index_alias):
        return
    indices = list(client.indices.get_alias(name=index_alias).keys())
    for index_name in indices:
        print(f"Deleting existing index `{index_name}` for alias `{index_alias}`")
        client.indices.delete(index=index_name)


def format_document_text(text: str) -> str:
    return f"search_document: {text.strip().lower()}"


def build_bulk_actions(
    data_chunk: list[JsonBlob],
    model: SentenceTransformer,
    index_alias: str,
) -> list[JsonBlob]:
    to_vectorize = [item.get("to_vectorize", "") for item in data_chunk]
    embeddings = model.encode(
        [format_document_text(text) for text in to_vectorize],
        show_progress_bar=False,
        convert_to_numpy=True,
        truncate_dim=EMBEDDING_DIM,
    )
    if len(embeddings.shape) != 2 or embeddings.shape[1] != EMBEDDING_DIM:
        raise ValueError(
            f"Expected embedding shape (N, {EMBEDDING_DIM}), got {embeddings.shape}"
        )

    actions: list[JsonBlob] = []
    for row, embedding in zip(data_chunk, embeddings, strict=True):
        payload = {k: v for k, v in row.items() if k != "to_vectorize"}
        payload["vector"] = embedding.astype("float32", copy=False).tolist()
        payload["_index"] = index_alias
        actions.append(payload)
    return actions


def main(args: argparse.Namespace) -> None:
    settings = get_settings()
    index_alias = settings.elastic_index_alias

    data_dir = Path(__file__).resolve().parents[1] / "data"
    data = get_json_data(data_dir, args.filename)
    if args.limit > 0:
        data = data[: args.limit]
    if not data:
        raise ValueError("No data found in the specified file")

    client = get_elastic_client(settings)
    if not client.ping():
        raise RuntimeError("Unable to connect to Elasticsearch")

    mappings_path = Path(__file__).resolve().parent / "mapping" / "mapping.json"
    if args.recreate_index:
        drop_alias_indices(client, index_alias)
    create_index_if_needed(client, index_alias, mappings_path)

    existing_dims = get_vector_dims_for_alias(client, index_alias)
    if existing_dims is not None and existing_dims != EMBEDDING_DIM:
        raise ValueError(
            f"Index alias `{index_alias}` has vector dims={existing_dims}, "
            f"but ingest now writes dims={EMBEDDING_DIM}. "
            "Re-run with --recreate-index to rebuild the index."
        )

    model = SentenceTransformer(settings.embedding_model_checkpoint)

    validate_start = perf_counter()
    validated_data = validate(data, exclude_none=False)
    validate_elapsed = perf_counter() - validate_start
    print(f"Validated {len(validated_data)} rows in {validate_elapsed:.4f}s")

    chunked_data = chunk_iterable(validated_data, args.chunksize)
    total_chunks = (len(validated_data) + args.chunksize - 1) // args.chunksize

    ingest_start = perf_counter()
    with progress.Progress(
        "[progress.description]{task.description}",
        progress.BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        progress.TimeElapsedColumn(),
    ) as prog:
        task = prog.add_task("Vectorizing and indexing...", total=total_chunks)
        for chunk in chunked_data:
            actions = build_bulk_actions(chunk, model, index_alias)
            failed = 0
            try:
                for ok, info in helpers.streaming_bulk(
                    client,
                    actions,
                    raise_on_error=True,
                ):
                    if not ok:
                        failed += 1
            except BulkIndexError as exc:
                first_error = exc.errors[0] if exc.errors else {}
                raise RuntimeError(
                    "Bulk indexing failed. First error sample: "
                    f"{first_error}"
                ) from exc
            if failed:
                raise RuntimeError(f"{failed} documents failed to index in current chunk")
            prog.update(task, advance=1)

    ingest_elapsed = perf_counter() - ingest_start
    print(f"Indexed {len(validated_data)} rows in {ingest_elapsed:.4f}s")

    client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Bulk index Elasticsearch from wine reviews JSONL")
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
        help="Size of each chunk to process",
    )
    parser.add_argument(
        "--filename",
        type=str,
        default="winemag-data-130k-v2.jsonl.gz",
        help="Name of the JSONL gzip file",
    )
    parser.add_argument(
        "--recreate-index",
        action="store_true",
        help="Delete existing indices for alias before indexing",
    )
    parsed_args = parser.parse_args()

    main(parsed_args)
