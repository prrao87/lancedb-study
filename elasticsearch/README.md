# Elasticsearch

[Elasticsearch](https://www.elastic.co/what-is/elasticsearch) is a distributed search and analytics engine for semi-structured and unstructured data. It is the backbone of many search engines in production today via its Lucene-based full-text search capabilities.Recently, Elasticsearch also added support for vector search ANN (HNSW) index.

## Set up Elasticsearch container

Use the provided `docker-compose.yml` to initiate containers that run Elasticsearch and its dashboard utility, Kibana.

```sh
docker compose up --build
```

This compose file starts a persistent-volume Elasticsearch database and Kibana environment with the credentials specified in `.env` (make sure it's filled out with the requisite version numbers first). The services can be stopped and restarted at any time for maintenance and updates.

```sh
# Tear down the container but retain the persistent volume and its associated data
docker compose down

# Restart the container with persistent volume
docker compose up
```

## Set up `mappings.json`

A key step prior to indexing data to Elasticsearch is to specify the settings for the index. In this case, we will be creating both an FTS and a vector search (ANN) index.

The following snippet shows how this is specified in the `mapping/mappings.json` file.

```json
{
    "settings": {
        "analysis": {
            "analyzer": {
                "custom_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase"
                    ]
                }
            }
        }
    }
    "mappings": {
        "properties": {
            "id": {
                "type": "keyword"
            },
            ...
            ...
            "vector": {
                "type": "dense_vector",
                "dims": 384,
                "index": true,
                "similarity": "cosine"
            }
        }
    }
}
```

The first section under `"settings"` creates a custom analyzer that will analyzes the text in the index via its lowercased keywords. The second section under `"mappings"` defines the properties of the vector index - in this case we define a fixed-length 384-dimensional vector that will be indexed and searched via cosine similarity.

## Ingest the data

The first step is to ingest the wine reviews dataset into Elasticsearch. Data is asynchronously ingested into the Elasticsearch database through the scripts in the `scripts` directory.

```sh
# Ingest partial dataset per limit arguemnt and build FTS and ANN index
python index.py --limit 1000
```

### Run sample FTS and vector search queries

```sh
python query.py
```

* Ingesting ~130K records into Elasticsearch via its async API takes ~7 seconds (M2 Macbook Pro)
* The script first checks the database for a mapping (that tells Elasticsearch what fields to analyze and how to index them). Each index is attached to an alias, `wines`, which is used to reference all the operations downstream
  * If no existing index or alias is found, a new one is created
* The script then validates the input JSON data via [Pydantic](https://docs.pydantic.dev) and asynchronously indexes them into the database using the [`AsyncElasticsearch` client](https://elasticsearch-py.readthedocs.io/en/v8.7.0/async.html) for fastest performance

### Run sample FTS query

```sh
python query.py
```

The full text search (via BM25 keyword matches) for the terms `tropical fruit` produce the following results.

```
Full-text search result
shape: (10, 5)
┌────────┬────────┬───────────────────────────────────┬───────────────────────────────────┬────────┐
│ id     ┆ points ┆ title                             ┆ description                       ┆ price  │
│ ---    ┆ ---    ┆ ---                               ┆ ---                               ┆ ---    │
│ i64    ┆ i64    ┆ str                               ┆ str                               ┆ f64    │
╞════════╪════════╪═══════════════════════════════════╪═══════════════════════════════════╪════════╡
│ 118060 ┆ 99     ┆ Failla 2010 Estate Vineyard Char… ┆ Shows classic, full-throttle not… ┆ 44.0   │
│ 82818  ┆ 97     ┆ Kracher 2013 Grande Cuvée Trocke… ┆ The heady, pure perfume of fig r… ┆ 95.0   │
│ 122943 ┆ 97     ┆ Château Smith Haut Lafitte 2014 … ┆ Dense and beautifully ripe, this… ┆ 95.0   │
│ 1572   ┆ 96     ┆ Château Haut-Brion 2009  Pessac-… ┆ Solid, very structured, packed w… ┆ 1200.0 │
│ …      ┆ …      ┆ …                                 ┆ …                                 ┆ …      │
│ 21080  ┆ 96     ┆ Château Lafite Rothschild 2011  … ┆ The wine shows the power typical… ┆ 685.0  │
│ 23440  ┆ 96     ┆ Bouchard Père & Fils 2011  Cheva… ┆ Initially, this is a richly ripe… ┆ 315.0  │
│ 47438  ┆ 96     ┆ Williams Selyem 2010 Drake Estat… ┆ Winemaker Bob Cabral's three 201… ┆ 65.0   │
│ 47439  ┆ 96     ┆ Williams Selyem 2010 Heintz Vine… ┆ The acidity really makes this Ch… ┆ 50.0   │
└────────┴────────┴───────────────────────────────────┴───────────────────────────────────┴────────┘
```

### Run vector query

```
Vector search result
shape: (10, 5)
┌─────┬────────┬───────────────────────────────────┬───────────────────────────────────┬───────┐
│ id  ┆ points ┆ title                             ┆ description                       ┆ price │
│ --- ┆ ---    ┆ ---                               ┆ ---                               ┆ ---   │
│ i64 ┆ i64    ┆ str                               ┆ str                               ┆ f64   │
╞═════╪════════╪═══════════════════════════════════╪═══════════════════════════════════╪═══════╡
│ 346 ┆ 100    ┆ Chambers Rosewood Vineyards NV R… ┆ This wine contains some material… ┆ 350.0 │
│ 347 ┆ 98     ┆ Chambers Rosewood Vineyards NV R… ┆ This deep brown wine smells like… ┆ 350.0 │
│ 348 ┆ 97     ┆ Robert Weil 2014 Kiedrich Gräfen… ┆ Dusty, saffron-spiced earthiness… ┆ 775.0 │
│ 349 ┆ 97     ┆ Chambers Rosewood Vineyards NV G… ┆ Deep mahogany. Dried fig and bla… ┆ 100.0 │
│ …   ┆ …      ┆ …                                 ┆ …                                 ┆ …     │
│ 352 ┆ 96     ┆ Oremus 2005 Eszencia  (Tokaji)    ┆ This amber-colored Hungarian stu… ┆ 320.0 │
│ 353 ┆ 96     ┆ Rochioli 2014 South River Chardo… ┆ Citrus-kissed saltiness lies at … ┆ 68.0  │
│ 354 ┆ 96     ┆ Louis Latour 2014 Le Montrachet … ┆ This beautiful, rich wine has ye… ┆ 630.0 │
│ 355 ┆ 96     ┆ Robert Weil 2014 Kiedrich Gräfen… ┆ Whiffs of white mushroom, saffro… ┆ 365.0 │
└─────┴────────┴───────────────────────────────────┴───────────────────────────────────┴───────┘
```
