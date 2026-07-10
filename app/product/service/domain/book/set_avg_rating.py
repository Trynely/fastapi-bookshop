from app.product.db.postgres.models.book import BookModel

def book_avg_rating(book: BookModel, rating: int) -> None:
    book.total_ratings += 1
    book.sum_ratings += rating
    book.rating = round(book.sum_ratings / book.total_ratings, 1)