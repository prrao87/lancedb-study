import polars as pl
from config import Settings
from sentence_transformers import SentenceTransformer

import lancedb


def fts_search(query: str) -> None:
    # In FTS, we limit to a max of 10K points to be more in line with Elasticsearch
    # fmt: off
    res = (
        tbl.search(query, vector_column_name="to_vectorize")
        .select(["id", "title", "description", "points", "price"])
        .limit(10000)
    ).to_arrow()
    df = pl.from_arrow(res).sort("points", descending=True).limit(10)
    # fmt: on
    print(f"Full-text search result\n{df}")


def vector_search(query: str) -> None:
    query_vector = MODEL.encode(query.lower())
    # fmt: off
    res = (
        tbl.search(query_vector)
        .metric("cosine")
        .nprobes(NUM_PROBES)
        .select(["id", "title", "description", "points", "price"])
        .limit(10)
    ).to_arrow()
    df = pl.from_arrow(res).sort("points", descending=True).limit(10)
    # fmt: on
    print(f"Vector search result\n{df}")


def main() -> None:
    query = "tropical fruit"
    fts_search(query)
    vector_search(query)


if __name__ == "__main__":
    # Define LanceDB client
    db = lancedb.connect("./winemag")
    tbl = db.open_table("wines")
    print(f"Obtained table of length: {len(tbl)}")

    NUM_PROBES = 20

    # Load a sentence transformer model for semantic similarity from a specified checkpoint
    model_id = Settings().embedding_model_checkpoint
    assert model_id, "Invalid embedding model checkpoint specified in .env file"
    MODEL = SentenceTransformer(model_id)

    main()
