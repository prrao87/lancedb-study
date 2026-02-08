"""Create LanceDB FTS and IVF_PQ indexes after ingestion."""

import argparse
from functools import lru_cache
from pathlib import Path
from time import perf_counter

import lancedb
from config import Settings
from lancedb.index import FTS, IvfPq


@lru_cache()
def get_settings() -> Settings:
    return Settings()


async def main() -> None:
    parser = argparse.ArgumentParser("Create LanceDB indexes")
    parser.add_argument(
        "--num-partitions",
        type=int,
        default=16,
        help="Number of IVF partitions for IVF_PQ",
    )
    parser.add_argument(
        "--num-sub-vectors",
        type=int,
        default=64,
        help="Number of PQ sub-vectors for IVF_PQ",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing indexes if they already exist",
    )
    args = parser.parse_args()

    settings = get_settings()
    db_uri = Path(__file__).resolve().parents[0] / settings.lancedb_dir
    db = await lancedb.connect_async(str(db_uri))
    table = await db.open_table("wines")

    fts_start = perf_counter()
    await table.create_index(
        "description",
        config=FTS(),
        replace=args.replace,
    )
    fts_elapsed = perf_counter() - fts_start
    print(f"Created FTS index in {fts_elapsed:.4f}s")

    ivfpq_start = perf_counter()
    await table.create_index(
        "vector",
        config=IvfPq(
            distance_type="cosine",
            num_partitions=args.num_partitions,
            num_sub_vectors=args.num_sub_vectors,
        ),
        replace=args.replace,
    )
    ivfpq_elapsed = perf_counter() - ivfpq_start
    print(
        "Created IVF_PQ index in "
        f"{ivfpq_elapsed:.4f}s "
        f"(num_partitions={args.num_partitions}, num_sub_vectors={args.num_sub_vectors})"
    )

    db.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
