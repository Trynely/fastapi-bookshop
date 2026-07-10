from dataclasses import asdict
import pytest_asyncio
from app.product.db.postgres.models import (
    AuthorModel,
    BookCategoryModel,
    BookModel,
    MadeInModel,
    PaperTypeModel,
    ReviewModel,
)
from app.core.config.product.test.book.dto import book_dto_test_conf
from app.core.config.product.test.category.dto import book_category_dto_test_conf
from app.core.config.product.test.author.dto import author_dto_test_conf
from app.core.config.product.test.paper.dto import paper_dto_test_conf
from app.core.config.product.test.made_in.dto import made_in_dto_test_conf
from app.core.config.product.test.review.dto import review_dto_test_conf
from app.core.config.client.test.dto import user_test_conf, user_google_test_conf, user_github_test_conf
from app.client.service.infrastructure.user.check_password import user_hash_password
from app.client.db.postgres.models import ClientModel

# product
@pytest_asyncio.fixture
async def book_category_db(db_session):
    book_category = BookCategoryModel(**asdict(book_category_dto_test_conf))

    db_session.add(book_category)
    await db_session.flush()
    await db_session.refresh(book_category)

    return book_category


@pytest_asyncio.fixture
async def author_db(db_session):
    author = AuthorModel(**asdict(author_dto_test_conf))

    db_session.add(author)
    await db_session.flush()
    await db_session.refresh(author)

    return author


@pytest_asyncio.fixture
async def paper_db(db_session):
    author = PaperTypeModel(**asdict(paper_dto_test_conf))

    db_session.add(author)
    await db_session.flush()
    await db_session.refresh(author)

    return author


@pytest_asyncio.fixture
async def made_in_db(db_session):
    author = MadeInModel(**asdict(made_in_dto_test_conf))

    db_session.add(author)
    await db_session.flush()
    await db_session.refresh(author)

    return author


@pytest_asyncio.fixture
async def review_db(db_session):
    author = ReviewModel(**asdict(review_dto_test_conf))

    db_session.add(author)
    await db_session.flush()
    await db_session.refresh(author)

    return author


@pytest_asyncio.fixture
async def book_db(
    db_session,
    book_category_db,
    author_db,
    paper_db,
    made_in_db,
):
    book = BookModel(
        **asdict(book_dto_test_conf),
        category=book_category_db,
        author=author_db,
        paper_type=paper_db,
        made_in=made_in_db,
    )

    db_session.add(book)
    await db_session.flush()
    await db_session.refresh(book)

    return book


# client
@pytest_asyncio.fixture
async def user_db(db_session):
    user = ClientModel(
        email=user_test_conf.email,
        username=user_test_conf.username,
        password=user_hash_password(user_test_conf.password),
        is_active=user_test_conf.is_active,
        oauth_provider=None,
        oauth_id=None,
    )

    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)

    return user


@pytest_asyncio.fixture
async def inactive_user_db(db_session):
    user = ClientModel(
        email=user_test_conf.email,
        username=user_test_conf.username,
        password=user_hash_password(user_test_conf.password),
        is_active=False,
        oauth_provider=None,
        oauth_id=None,
    )

    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)

    return user


@pytest_asyncio.fixture
async def google_user_db(db_session):
    user = ClientModel(
        email=user_google_test_conf.email,
        username=user_google_test_conf.username,
        password=None,
        is_active=user_google_test_conf.is_active,
        oauth_provider=user_google_test_conf.oauth_provider,
        oauth_id=user_google_test_conf.oauth_id,
    )

    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)

    return user


@pytest_asyncio.fixture
async def github_user_db(db_session):
    user = ClientModel(
        email=user_github_test_conf.email,
        username=user_github_test_conf.username,
        password=None,
        is_active=user_github_test_conf.is_active,
        oauth_provider=user_github_test_conf.oauth_provider,
        oauth_id=user_github_test_conf.oauth_id,
    )

    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)

    return user