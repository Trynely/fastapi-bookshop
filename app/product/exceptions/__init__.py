from .book.exists import BookNotFoundERR, BookUnavailableERR
from .category.exists import BookCategoryNotFoundERR
from .author.exists import BookAuthorNotFoundERR
from .review.exists import BookReviewAlreadyExistsERR
from .review.invalid_rating import ReviewRatingInvalidERR
from .country.exists import BookMadeInNotFoundERR
from .paper.exists import BookPaperTypeNotFoundERR
from .book.reco_rate_limit import TooManyRecoFeedSessionsERR