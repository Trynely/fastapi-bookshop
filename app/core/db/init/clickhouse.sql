CREATE TABLE analytics.book_popularity
(
    book_id UInt64,
    total_sales UInt64,
    wishlist UInt64,
    total_ratings UInt64,
    rating_sum Float32,
    rating_count UInt32
)
ENGINE = SummingMergeTree
ORDER BY book_id;