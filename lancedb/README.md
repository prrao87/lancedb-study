# LanceDB

The Python API for LanceDB is used to ingest the data and build the index.

## Embedding model selection

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

### Ingest data and create FTS and ANN indexes

The following scripts are run with arguments.

```sh
# Ingest full dataset and build FTS and ANN index
python index.py
```

```sh
# Ingest partial dataset per limit arguemnt and build FTS and ANN index
python index.py --limit 1000
```

### Run sample FTS and vector search queries

```sh
python query.py
```

The full text search (via BM25 keyword matches) and vector search (via cosine similarity) results are shown below.

```
Full-text search result
shape: (10, 17)
┌────────┬────────┬───────────────────────────────────┬───────────────────────────────────┬───┬───────────────────────┬───────────────────────────────────┬───────────────────────────────────┬──────────┐
│ id     ┆ points ┆ title                             ┆ description                       ┆ … ┆ taster_twitter_handle ┆ to_vectorize                      ┆ vector                            ┆ score    │
│ ---    ┆ ---    ┆ ---                               ┆ ---                               ┆   ┆ ---                   ┆ ---                               ┆ ---                               ┆ ---      │
│ i64    ┆ i64    ┆ str                               ┆ str                               ┆   ┆ str                   ┆ str                               ┆ array[f32, 384]                   ┆ f64      │
╞════════╪════════╪═══════════════════════════════════╪═══════════════════════════════════╪═══╪═══════════════════════╪═══════════════════════════════════╪═══════════════════════════════════╪══════════╡
│ 125527 ┆ 88     ┆ Robert Renzoni 2016 Julia's Vine… ┆ This is a fruity, tropical rendi… ┆ … ┆ @mattkettmann         ┆ Pinot Grigio Robert Renzoni 2016… ┆ [-0.001237, 0.021784, … 0.041974… ┆ 5.901485 │
│ 127601 ┆ 83     ┆ Banrock Station 2001 Chardonnay … ┆ Good party Chard. Nothing too co… ┆ … ┆ @JoeCz                ┆ Chardonnay Banrock Station 2001 … ┆ [-0.020877, -0.015568, … 0.02873… ┆ 5.841707 │
│ 125136 ┆ 86     ┆ Pride Mountain 2010 Viognier (So… ┆ This is a powerful wine, almost … ┆ … ┆ null                  ┆ Viognier Pride Mountain 2010 Vio… ┆ [-0.000642, -0.016708, … 0.03495… ┆ 5.580855 │
│ 129608 ┆ 84     ┆ Castle Rock 2010 Chardonnay (Rus… ┆ Too oaky and forward in tropical… ┆ … ┆ null                  ┆ Chardonnay Castle Rock 2010 Char… ┆ [-0.030962, -0.0411, … 0.00888]   ┆ 5.421664 │
│ …      ┆ …      ┆ …                                 ┆ …                                 ┆ … ┆ …                     ┆ …                                 ┆ …                                 ┆ …        │
│ 126170 ┆ 88     ┆ Valle dell'Acate 2013 Zagra Gril… ┆ It opens with pretty aromas of o… ┆ … ┆ @kerinokeefe          ┆ Grillo Valle dell'Acate 2013 Zag… ┆ [-0.022173, 0.026167, … 0.020694… ┆ 5.3706   │
│ 126410 ┆ 86     ┆ Justin 2012 Chardonnay (Central … ┆ Although Chardonnay might not tr… ┆ … ┆ null                  ┆ Chardonnay Justin 2012 Chardonna… ┆ [0.001362, -0.034199, … 0.032258… ┆ 5.3706   │
│ 128804 ┆ 85     ┆ Tenute Orestiadi 2016 Molino a V… ┆ Tropical fruit aromas meld with … ┆ … ┆ @kerinokeefe          ┆ Grillo Tenute Orestiadi 2016 Mol… ┆ [-0.011769, 0.060849, … 0.02716]  ┆ 5.320488 │
│ 129690 ┆ 87     ┆ Passaggio 2011 New Generation Un… ┆ Vanilla cream, honey and tropica… ┆ … ┆ null                  ┆ Chardonnay Passaggio 2011 New Ge… ┆ [-0.013895, -0.014257, … 0.00822… ┆ 5.271303 │
└────────┴────────┴───────────────────────────────────┴───────────────────────────────────┴───┴───────────────────────┴───────────────────────────────────┴───────────────────────────────────┴──────────┘
Vector search result
shape: (10, 17)
┌────────┬────────┬───────────────────────────────────┬───────────────────────────────────┬───┬───────────────────────┬───────────────────────────────────┬───────────────────────────────────┬───────────┐
│ id     ┆ points ┆ title                             ┆ description                       ┆ … ┆ taster_twitter_handle ┆ to_vectorize                      ┆ vector                            ┆ _distance │
│ ---    ┆ ---    ┆ ---                               ┆ ---                               ┆   ┆ ---                   ┆ ---                               ┆ ---                               ┆ ---       │
│ i64    ┆ i64    ┆ str                               ┆ str                               ┆   ┆ str                   ┆ str                               ┆ array[f32, 384]                   ┆ f32       │
╞════════╪════════╪═══════════════════════════════════╪═══════════════════════════════════╪═══╪═══════════════════════╪═══════════════════════════════════╪═══════════════════════════════════╪═══════════╡
│ 125367 ┆ 88     ┆ Trapiche 2016 Costa & Pampa Char… ┆ This blend of coastal and desert… ┆ … ┆ @wineschach           ┆ Chardonnay Trapiche 2016 Costa &… ┆ [-0.012717, -0.000868, … 0.02559… ┆ 0.27347   │
│ 129111 ┆ 87     ┆ Palamà 2012 Mavro Negroamaro (Sa… ┆ Made with Negroamaro, this offer… ┆ … ┆ @kerinokeefe          ┆ Negroamaro Palamà 2012 Mavro Neg… ┆ [-0.027401, 0.019011, … 0.032753… ┆ 0.27694   │
│ 129487 ┆ 88     ┆ Herdade Grande 2012 Colheita Sel… ┆ This fruity wine boasts flavors … ┆ … ┆ @vossroger            ┆ Portuguese White Herdade Grande … ┆ [-0.011832, -0.017191, … 0.04267… ┆ 0.277972  │
│ 127491 ┆ 85     ┆ Domaines Barons de Rothschild (L… ┆ Aromas of pineapple, lemon and s… ┆ … ┆ @wineschach           ┆ Chardonnay Domaines Barons de Ro… ┆ [-0.018693, -0.015425, … 0.02040… ┆ 0.278787  │
│ …      ┆ …      ┆ …                                 ┆ …                                 ┆ … ┆ …                     ┆ …                                 ┆ …                                 ┆ …         │
│ 126003 ┆ 84     ┆ Casal do Conde 2013 White (Tejo)  ┆ This blend of Sauvignon Blanc an… ┆ … ┆ @vossroger            ┆ Portuguese White Casal do Conde … ┆ [-0.012546, 0.001385, … 0.039636… ┆ 0.292588  │
│ 128181 ┆ 86     ┆ Ochoa 2016 Calendas Garnacha Ros… ┆ Clean nectarine and red plum aro… ┆ … ┆ @wineschach           ┆ Rosado Ochoa 2016 Calendas Garna… ┆ [-0.038352, -0.027079, … 0.00070… ┆ 0.293419  │
│ 126929 ┆ 87     ┆ Paul Prieur et Fils 2014  Sancer… ┆ In this soft, ripe wine, rounded… ┆ … ┆ @vossroger            ┆ Sauvignon Blanc Paul Prieur et F… ┆ [-0.033548, 0.005416, … 0.035486… ┆ 0.293846  │
│ 126489 ┆ 86     ┆ Domaine Cheysson 2011  Chirouble… ┆ Emphasizing tannins and tight st… ┆ … ┆ @vossroger            ┆ Gamay Domaine Cheysson 2011  Chi… ┆ [-0.021621, -0.011956, … 0.03878… ┆ 0.294202  │
└────────┴────────┴───────────────────────────────────┴───────────────────────────────────┴───┴───────────────────────┴───────────────────────────────────┴───────────────────────────────────┴───────────┘
```

