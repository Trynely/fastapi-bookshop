from pydantic import BaseModel

class CategoryBooksByAuthorNameREQT(BaseModel):
    category_slug: str
    name: str


class CategoryBooksByTitleREQT(BaseModel):
    category_slug: str
    title: str


class CategoryBooksByCountryREQT(BaseModel):
    category_slug: str
    made_in: str