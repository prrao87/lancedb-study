# LanceDB

The LanceDB Python client is used to load, index and query the data.

## Ingest data and create FTS and ANN indexes

The data ingestion and index creation can be run as follows.

```sh
# Ingest full dataset and build FTS and ANN index
python index.py
```

```sh
# Ingest partial dataset per limit argument and build FTS and ANN index
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
> Because LanceDB doesn't yet (as of this writing) have an async Python client, the concurrent benchmark is run via multi-threading in Python. This is not as efficient as pure async (non-blocking) requests as is done in Elasticsearch, but is much faster than the serial benchmark.

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
Ran search in: 1.3454 sec

--------------------------------------------------------------------------------
# Vector search results

Query [vanilla and a hint of smokiness]: Drenched in luxurious, almost sweet fruit flavors, this tempting and delicious wine is full bodied. Ripe in aromas and on the palate, it creates a vivid and warming cherry-pie effect on the senses, and is undeniably tasty.
Query [rich and sweet dessert wine with balanced tartness]: Not a lot of wood scents are showing, though the aging took place in roughly 50% new oak barrels. This has forward, pretty black fruits, juicy acids, some still-unresolved astringency, and aromatically it incorporates a nice herbal note, reminiscent of green tea. Still too young to drink, and the rating could go higher with more bottle age.
Query [cherry and plum aromas]: Part of the select group of impressive wines from this year, this wine is ripe, rich and firmly structured. Black-currant fruitiness forms the base for solid tannins and a concentrated texture. The hints of wood-aging need to soften. Drink from 2022.
Query [right balance of citrus acidity]: This straightforward wine isn't particularly Cabernet-like, but it is good and sound. With furry tannins, it has a distinct sweetness of raisins and blackberry jam, as well as lots of brambly Zinny spices. Drink up.
Query [grassy aroma with apple and tropical fruit]: This is the finest Cheval Blanc for many years. It is, quite simply, magnificent. The wine shows the greatness of Cabernet Franc in the vintage, with 57% of the variety in the blend. It is beautifully structured and perfumed, with velvety tannins, balanced acidity and swathes of black-currant and black-cherry fruits. It's well on course to becoming a legendary wine.
Query [bitter with a dry aftertaste]: The wine is firm with tannins as well as black-currant fruit. It does have a juicy edge that will develop well as it matures. Drink this potentially attractive wine from 2018.
Query [sweet with a hint of chocolate and berry flavor]: Exotic, complex and vivid aromas, rich and fulfilling fruit flavors and a hefty structure form a great package in this full-bodied and extroverted wine. The winemaker allowed wild yeast and kept 30% whole clusters in the fermentation, then aged it in neutral barrels.
Query [acidic on the palate with oak aromas]: A lovely young Cab, rich and balanced, and with the elegance you expect from this producer. Made from all 5 Bordeaux varieties, with a drop of Syrah, the wine is potent in red and black currant, blackberry and new oak flavors, with sweetly ripe tannins. Delicious now, it should develop through 2015.
Query [balanced tannins and dry and fruity composition]: A 100% varietal Pinot, this wine has a faint bouquet of ripe black cherry and blackberry, exuding full flavor and body. Smooth, the oak is low impact, providing extra weight and sustenance while remaining balanced with the fruit.
Query [peppery undertones that pairs with steak or barbecued meat]: This arresting wine has aromas of forest floor, strawberry and cola. It's light and lithe in feel yet still richly flavored with a lingering finish.
Ran search in: 0.1876 sec
```


