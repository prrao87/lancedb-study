# LanceDB benchmark: Full-text and vector search performance

[LanceDB](https://github.com/lancedb/lancedb) is an open source, embedded and developer-friendly vector database. Some key features about LanceDB that make it extremely valuable are listed below, among many others listed on their GitHub repo.

* Incredibly lightweight (no DB servers to manage), because it runs entirely in-process with the application
* Extremely scalable from development to production
* Ability to perform full-text search (FTS), SQL search (via [DataFusion](https://github.com/apache/arrow-datafusion)) *and* ANN vector search
* Multi-modal data support (images, text, video, audio, point-clouds, etc.)
* Zero-copy (via [Arrow](https://github.com/apache/arrow-rs)) with automatic versioning of data on its native [Lance](https://github.com/lancedb/lance) storage format

The aim of this repo is to demonstrate the full-text and vector search features of LanceDB via an end-to-end benchmark, in which we carefully study query results and throughput.

## Dataset

The dataset used for this demo is the [Wine Reviews](https://www.kaggle.com/zynicide/wine-reviews) dataset from Kaggle, containing ~130k reviews on wines along with other metadata. The dataset is converted to a ZIP archive, and the code for this as well as the ZIP data is provided here for reference.

## Comparison

Studying the performance of any tool in isolation is a challenge, so for the sake of comparison, an Elasticsearch workflow is provided in this repo. [Elasticsearch](https://github.com/elastic/elasticsearch) is a popular Lucene-based full-text and vector search engine whose use is regularly justified for full-text (and these days, vector search), so this makes it a meaningful tool to compare LanceDB against.

## Setup

Install the dependencies in virtual environment via `requirements.txt`.

```sh
# Setup the environment for the first time
python -m venv .venv  # python -> python 3.11+

# Activate the environment (for subsequent runs)
source .venv/bin/activate

python -m pip install -r requirements.txt
```

## Embedding model

The Hugging Face [model hub](https://huggingface.co/models) is a good starting point to learn which embedding models are available, including their names and how to access them. For ease of use, the `sentence-transformers` library is used in this repo to expose the embedding models to LanceDB and generating the embeddings.

The following open source embedding models for English are exposed through the `sentence-transformers` library (in order of their performance on the [MTEB leaderboard](https://huggingface.co/spaces/mteb/leaderboard)):

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

For this study, the `BAAI/bge-small-en-v1.5` model with 384 dimensions is used.