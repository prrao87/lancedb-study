# LanceDB

The Python API for LanceDB is used to ingest the data and build the index. The following scripts are run with arguments.

## Embedding model selection

The Hugging Face [model hub](https://huggingface.co/models) is a good starting point to learn which embedding models are available, including their names and how to access them. For ease of use, the `sentence-transformers` library is used in this repo to expose the embedding models to LanceDB and generating the embeddings.

As of 2023, the following embedding models for English are exposed through the `sentence-transformers` library (in order of their performance on the [MTEB leaderboard](https://huggingface.co/spaces/mteb/leaderboard)):

| Model class | Model name | Dimensions | Sequence length
|:---:|:---|:---:|:---:
BAAI General (Flag) Embedding | `BAAI/bge-large-en-v1.5` | 1024 | 512
BAAI General (Flag) Embedding | `BAAI/bge-base-en-v1.5` | 768 | 512
Alibaba General Text Embeddings | `thenlper/gte-large` | 1024 | 512
Alibaba General Text Embeddings | `thenlper/gte-base` | 768 | 512
BAAI General (Flag) Embedding | `BAAI/bge-small-en-v1.5` | 384 | 512
Alibaba General Text Embeddings | `thenlper/gte-small` | 384 | 512
SentenceBERT | `sentence-transformers/all-MiniLM-L12-v2` | 384 | 256
SentenceBERT | `sentence-transformers/all-MiniLM-L6-v2` | 384 | 256


#### Ingest data and create FTS and ANN indexes

```sh
# Build FTS and ANN index with 4 workers for generating embeddings
python index.py --workers 4
```

```sh
# Deleting existing DB and creating a new one
python index.py --refresh --workers 4
```

#### Run sample FTS and vector search queries

```sh
python query.py
```