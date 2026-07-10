from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel
from app.product.api.responses.author.detail import AuthorDetailRESP
from app.product.api.responses.category.detail import CategoryDetailRESP
from app.product.api.responses.made_in.detail import MadeInDetailRESP
from app.product.api.responses.paper.detail import PaperTypeDetailRESP
from app.product.api.responses.review.detail import ReviewDetailRESP

class BookDetailRESP(BaseModel):
    id: int
    slug: str
    title: str
    price: Decimal
    pages: int
    quantity: int
    img: Optional[str]
    discount_percent: Optional[int]
    description: Optional[str]
    issue_year: Optional[int]
    rating: Optional[float]
    total_sales: Optional[int]
    total_ratings: Optional[int]
    sum_ratings: Optional[int]
    is_available: bool

    # relations
    author: AuthorDetailRESP
    category: CategoryDetailRESP
    paper_type: Optional[PaperTypeDetailRESP]
    made_in: Optional[MadeInDetailRESP]
    review: Optional[List[ReviewDetailRESP]] = []

    model_config = {
        "from_attributes": True
    }