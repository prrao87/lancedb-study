from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Wine(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        extra="allow",
        str_strip_whitespace=True,
    )

    id: int
    points: int
    title: str
    description: str | None
    price: float | None
    variety: str | None
    winery: str | None
    vineyard: str | None = Field(..., alias="designation")
    country: str | None
    province: str | None
    region_1: str | None
    region_2: str | None
    taster_name: str | None
    taster_twitter_handle: str | None

    @model_validator(mode="before")
    def _fill_country_unknowns(cls, values):
        "Fill in missing country values with 'Unknown', as we always want this field to be queryable"
        country = values.get("country")
        if country is None or country == "null":
            values["country"] = "Unknown"
        return values

    @model_validator(mode="before")
    def _create_id(cls, values):
        "Create an _id field because Elastic needs this to store as primary key"
        values["_id"] = values["id"]
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


class SearchResult(BaseModel):
    "Model to return search results"
    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "example": {
                "id": 374,
                "title": "Borgo Conventi 2002 I Fiori del Borgo Sauvignon Blanc (Collio)",
                "description": "Crisp, green, grassy wine with fresh acidity and herbeceous character. It is very New World with its tropical flavors and open, forward fruit.",
                "country": "Italy",
                "variety": "Sauvignon Blanc",
                "price": 15,
                "points": 88
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
