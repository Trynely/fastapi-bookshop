
from dataclasses import dataclass

@dataclass(frozen=True)
class BookReviewOFUser:
    book_id: int
    user_id: int