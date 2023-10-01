import lancedb
import polars as pl
from sentence_transformers import SentenceTransformer

from config import Settings


def embed_func(text: str, model) -> list[float]:
    return model.encode(text.lower())


def fts(query: str) -> None:
    # fmt: off
    res = (
        tbl.search(query)
        .limit(10)
        .to_arrow()
    )
    # fmt: on
    print(f"Full-text search result: {pl.from_arrow(res)}")


def vector_search(query: str) -> None:
    query_vector = embed_func(query, MODEL)
    # fmt: off
    res = (
        tbl.search(query_vector)
        .metric("cosine")
        .nprobes(NUM_PROBES)
        .limit(10)
        .to_arrow()
    )
    # fmt: on
    print(f"Vector search result: {pl.from_arrow(res)}")


def main() -> None:
    query = "tropical fruit"
    fts(query)
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
