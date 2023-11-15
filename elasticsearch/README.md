# Elasticsearch

[Elasticsearch](https://www.elastic.co/what-is/elasticsearch) is a distributed search and analytics engine for semi-structured and unstructured data. It is the backbone of many search engines in production today via its Lucene-based full-text search capabilities. Recently, Elasticsearch also added support for vector search ANN (HNSW) index, which is also showcased in this section.

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

## Ingest data

The first step is to ingest the wine reviews dataset into Elasticsearch. Data is asynchronously ingested into the Elasticsearch database through the scripts in the `scripts` directory.

```sh
# Ingest partial dataset per limit arguemnt and build FTS and ANN index
python index.py --limit 1000
```

## Run FastAPI app to serve query results

A FastAPI app is provided in `app.py` to serve results via FTS and vector search enndpoints, and can be run as follows.

```sh
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

The FTS endpoint can be accessed at `http://localhost:8000/fts_search` and the vector search endpoint can be accessed at `http://localhost:8000/vector_search`.

> [!NOTE]
> Make sure that the FastAPI server is running before running the following steps.

## Run serial benchmark

The first benchmark is a serial one, where a series of (randomly selected) queries are run sequentially. The FTS serial benchmark can be run as follows.

```sh
python benchmark_serial.py --search fts --limit 10
python benchmark_serial.py --search fts --limit 100
python benchmark_serial.py --search fts --limit 1000
python benchmark_serial.py --search fts --limit 10000
```

This command runs 10, 100, 1000 and 1000 FTS queries sequentially by randomly selecting any of the 10 queries from the `benchmark_queries/keyword_terms.txt`.

The vector search serial benchmark can be run as follows.

```sh
python benchmark_serial.py --search vector --limit 10
python benchmark_serial.py --search vector --limit 100
python benchmark_serial.py --search vector --limit 1000
python benchmark_serial.py --search vector --limit 10000
```

This command runs 10, 100, 1000 and 1000 vector search queries by randomly selecting any of the 10 queries from the `benchmark_queries/vector_terms.txt`.

## Run concurrent benchmark

The next benchmark is a concurrent one, where a series of (randomly selected) queries are run on multiple threads. The FTS concurrent benchmark can be run as follows.

```sh
python benchmark_concurrent.py --search fts --limit 10
python benchmark_concurrent.py --search fts --limit 100
python benchmark_concurrent.py --search fts --limit 1000
python benchmark_concurrent.py --search fts --limit 10000
```

The vector search concurrent benchmark can be run as follows.

```sh
python benchmark_concurrent.py --search vector --limit 10
python benchmark_concurrent.py --search vector --limit 100
python benchmark_concurrent.py --search vector --limit 1000
python benchmark_concurrent.py --search vector --limit 10000
```

> [!NOTE]
> Elasticsearch offers a fully non-blocking async Python client which is used in this concurrent benchmark.

## Inspect search results

A script `query.py` is provided to run the FTS and vector search benchmark queries for qualitative inspection. This script must be run while the FastAPI server that serves query results is up and running.

```sh
python query.py
```

The top result for each of the 10 FTS (via BM25) and vector search (via cosine similarity) queries are shown below.

```
# Full text search results

Query [+apple +pear]: The pear, apple and apple skin aromas are light. The palate brings just off-dry pear flavors with a full feel.
Query ["tropical fruit"]: Plump tropical fruit aromas show on the nose. A fruity but not complex palate deals short melon and tropical-fruit flavors prior to a briny finish.
Query [+citrus +almond]: Inviting aromas of butter, almond and citrus open into a rich, thickly textured wine studded with peach, almond butter and citrus pith. The slightly bitter notes echo through the finish, providing a welcome sense of balance to round mouthfeel and fatty flavors.
Query [+orange +grapefruit]: Made from Cabernet Sauvignon, this has funky, yeasty aromas of pink grapefruit and passion fruit that turn citrusy and briny if given time. On the palate, this recalls orange juice. Orange, grapefruit and generic tang proceed from the flavor profile to the finish.
Query [+full +bodied]: Produced from organically grown grapes, this wine is full of fragrant, clean red-fruit flavors. It is ripe and full bodied—perhaps too full-bodied for a really fresh rosé. It does have all the fruit, generous and with a soft aftertaste.
Query ["citrus acidity"]: This soft, ripe wine has good apricot and peach flavors alongside the crisper citrus acidity. It is spicy, fruity and ready to drink.
Query [+blueberry +mint]: Exotic aromas of cardamom, blueberry and spiced currant filter onto a fresh but wide-bodied palate with raspberry, blueberry, herb and spice flavors. The finish is intriguing due to a reprise of notes like anise, mint and herbal berry flavors.
Query [+beef +lamb]: Tarry, savory notes of dried beef, soy, charred lamb and underlying blackberry combine for a nose that screams umami. The palate carries a similar effect of grilled, lavender-covered lamb shank, black peppercorns and black sesame.
Query [+shellfish +seafood]: Really? A five-buck Oregon Riesling? It's light, lemony and tart, but it's real wine, simple and plain, yet fine with shellfish or other light seafood.
Query [+vegetable +fish]: Clean mineral notes blend nicely with fresh berry fruit, red rose and raspberry. This is a simple but genuine wine that would pair with roasted fish or vegetable risotto.
Ran search in: 0.1454 sec

--------------------------------------------------------------------------------
# Vector search results

Query [vanilla and a hint of smokiness]: Vanilla and maple aromas lead to overtly fruity red cherry flavors with a touch of sweetness and a soft texture. It's pleasant to drink for those looking for a soft touch, with very mild acidity and no tannin to speak of.
Query [rich and sweet dessert wine with balanced tartness]: This richly extracted dessert wine boasts a dark, inky appearance and aromas of exotic spice, nutmeg, cinnamon, dark chocolate, carob, roasted chestnut and mature blackberries. It is smooth, well textured and exceedingly rich on the close with loads of power, personality and persistency.
Query [cherry and plum aromas]: Earthy, herbal aromas of cherry and plum come with a funky note of wet dog fur. Hailing from a cool, wet vintage, this is showing shearing acidity and abrasiveness. Quick-hitting raspberry, plum and red-currant flavors end with edginess and snap. This is 40% each Cabernets Sauvignon and Franc, with 20% Monastrell.
Query [right balance of citrus acidity]: True to its name, this blend is tangy in acidity. Flavorwise, it's simple, with pleasant orange, peach, lemon and vanilla flavors that finish a little sweet.
Query [grassy aroma with apple and tropical fruit]: Spring flower aromas mingle with a hint of orchard fruit. On the lean, extremely simple palate, yellow apple fruit mixes with a lemon zest note.
Query [bitter with a dry aftertaste]: Even at a considerable 15 g/l of residual sugar, this wine comes across as almost dry, thanks to its crisp acidity. Scents of petrichor, green apple and lime start things off, while those razor-sharp acids show up on the finish. Drink now.
Query [sweet with a hint of chocolate and berry flavor]: A bouquet of cherry, white chocolate and juniper berry sets the stage for flavors of raspberry, blackberry, blueberry pie and baking spices. It is smooth in the mouth, with a sense of soft sweetness that is neither overpowering nor cloying, bolstered by a pervasive backbone of acidity.
Query [acidic on the palate with oak aromas]: The oaky smoke is quite powerful on the nose, which also shows vanilla dust and lime juice. The palate is anything but austere, full of toast, caramelized apples and smoked fruits. A line of citrus acidity stops it from becoming flabby, but this is definitely for the oak lovers crowd.
Query [balanced tannins and dry and fruity composition]: There is a good core of tannin here, the fruit sweet plums and ripe tannins, relatively soft and easy. Only that kernel of tannin offers some aging possibility.
Query [peppery undertones that pairs with steak or barbecued meat]: An easy red blend, this would pair well with hamburgers or grilled meats. Notes of cherry and blackberry accent the palate.
Ran search in: 0.2328 sec
```