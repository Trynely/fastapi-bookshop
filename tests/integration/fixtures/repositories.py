import pytest
from app.product.db.postgres.repositories.sqlalchemy.book import BookSQLAlchemyREPO
from app.order.db.sqlalchemy.repositories.cart import CartItemSQLAlchemyRepository, CartSQLAlchemyRepository
from app.client.db.postgres.repositories.sqlalchemy import UserSQLAlchemyREPO

@pytest.fixture
def book_repository(db_session):
    return BookSQLAlchemyREPO(session=db_session)


@pytest.fixture
def cart_repository(db_session):
    return CartSQLAlchemyRepository(session=db_session)


@pytest.fixture
def cart_item_repository(db_session):
    return CartItemSQLAlchemyRepository(session=db_session)


@pytest.fixture
def user_repository(db_session):
    return UserSQLAlchemyREPO(session=db_session)