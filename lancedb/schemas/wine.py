from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lancedb.pydantic import LanceModel, Vector


class Wine(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        extra="allow",
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "id": 45100,
                "points": 85,
                "title": "Balduzzi 2012 Reserva Merlot (Maule Valley)",
                "description": "Ripe in color and aromas, this chunky wine delivers heavy baked-berry and raisin aromas in front of a jammy, extracted palate. Raisin and cooked berry flavors finish plump, with earthy notes.",
                "price": 10.0,
                "variety": "Merlot",
                "winery": "Balduzzi",
                "vineyard": "Reserva",
                "country": "Chile",
                "province": "Maule Valley",
                "region_1": "null",
                "region_2": "null",
                "taster_name": "Michael Schachner",
                "taster_twitter_handle": "@wineschach",
            }
        },
    )

    id: int
    points: int
    title: str
    description: Optional[str]
    price: Optional[float]
    variety: Optional[str]
    winery: Optional[str]
    vineyard: Optional[str] = Field(..., alias="designation")
    country: Optional[str]
    province: Optional[str]
    region_1: Optional[str]
    region_2: Optional[str]
    taster_name: Optional[str]
    taster_twitter_handle: Optional[str]

    @model_validator(mode="before")
    def _fill_country_unknowns(cls, values):
        "Fill in missing country values with 'Unknown', as we always want this field to be queryable"
        country = values.get("country")
        if not country:
            values["country"] = "Unknown"
        return values

    @model_validator(mode="before")
    def _add_to_vectorize_fields(cls, values):
        "Add a field to_vectorize that will be used to create sentence embeddings"
        variety = values.get("variety", "")
        title = values.get("title", "")
        description = values.get("description", "")
        to_vectorize = list(filter(None, [variety, title, description]))
        values["to_vectorize"] = " ".join(to_vectorize).strip()
        return values


class LanceModelWine(BaseModel):
    """
    Pydantic model for LanceDB, with a vector field added for sentence embeddings
    """

    id: int
    points: int
    title: str
    description: Optional[str]
    price: Optional[float]
    variety: Optional[str]
    winery: Optional[str]
    vineyard: Optional[str] = Field(..., alias="designation")
    country: Optional[str]
    province: Optional[str]
    region_1: Optional[str]
    region_2: Optional[str]
    taster_name: Optional[str]
    taster_twitter_handle: Optional[str]
    to_vectorize: str
    vector: Vector(384)


class FullTextSearchModel(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "example": {
                "wineID": 3845,
                "country": "Italy",
                "title": "Castellinuzza e Piuca 2010  Chianti Classico",
                "description": "This gorgeous Chianti Classico boasts lively cherry, strawberry and violet aromas. The mouthwatering palate shows concentrated wild-cherry flavor layered with mint, white pepper and clove. It has fresh acidity and firm tannins that will develop complexity with more bottle age. A textbook Chianti Classico.",
                "points": 93,
                "price": 16,
                "variety": "Red Blend",
                "winery": "Castellinuzza e Piuca",
            }
        },
    )

    id: int
    title: str
    description: Optional[str]
    country: Optional[str]
    variety: Optional[str]
    price: Optional[float]
    points: Optional[int]


class SimilaritySearchModel(LanceModel):
    id: int
    title: str
    description: Optional[str]
    country: Optional[str]
    variety: Optional[str]
    points: Optional[int]
    price: Optional[float]
