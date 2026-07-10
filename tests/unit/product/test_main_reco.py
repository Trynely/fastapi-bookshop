import base64
import json
from unittest.mock import Mock, patch

import pytest

from app.product.dto.book.main_reco import (
    BookBlenderSlotsDTO,
    BookMainRecoCursorDTO,
)
from app.product.exception.book.invalid_reco_cursor import InvalidRecoCursorEXC
from types import SimpleNamespace

from app.product.service.infrastructure.query_handlers.book.main_reco import (
    SLOT_COUNTS,
    BookColdCandidatesProvider,
    BookMainRecoBlender,
    ColdCandidateDTO,
    FeedSlot,
    _diversified_pick,
    _weighted_sample,
)

FAKE_SECRET = "test-secret-key"


def _settings_mock():
    settings = Mock()
    settings.app.secret_key = FAKE_SECRET
    return settings


@pytest.fixture(autouse=True)
def patch_settings():
    with patch(
        "app.product.dto.book.main_reco.get_settings",
        return_value=_settings_mock(),
    ):
        yield


# --- cursor ---

def _make_cursor(**overrides) -> BookMainRecoCursorDTO:
    defaults = dict(
        session_id="a" * 32,
        seed=12345,
        page=3,
        personalized_mode="collaborative",
        personalized_offset=40,
        collaborative_offset=16,
        popular_last_score=0.5,
        popular_last_book_id=77,
        new_last_id=100,
        exploration_last_random_key=999,
    )
    defaults.update(overrides)
    return BookMainRecoCursorDTO(**defaults)


def test_cursor_roundtrip():
    cursor = _make_cursor()
    decoded = BookMainRecoCursorDTO.decode(cursor.encode())
    assert decoded == cursor


def test_cursor_roundtrip_with_nones():
    cursor = BookMainRecoCursorDTO.initial(seed=1, session_id="s")
    decoded = BookMainRecoCursorDTO.decode(cursor.encode())
    assert decoded == cursor


@pytest.mark.parametrize(
    "token",
    [
        "",
        "garbage",
        "not-base64.deadbeef",
        base64.urlsafe_b64encode(b"{}").decode(),  # без подписи
    ],
)
def test_cursor_decode_garbage_raises_400(token):
    with pytest.raises(InvalidRecoCursorEXC):
        BookMainRecoCursorDTO.decode(token)


def test_cursor_decode_tampered_payload_raises():
    token = _make_cursor().encode()
    payload, signature = token.rsplit(".", 1)

    data = json.loads(base64.urlsafe_b64decode(payload.encode()))
    data["p"] = 0  # подменяем страницу
    tampered_payload = base64.urlsafe_b64encode(
        json.dumps(data, separators=(",", ":")).encode()
    ).decode()

    with pytest.raises(InvalidRecoCursorEXC):
        BookMainRecoCursorDTO.decode(f"{tampered_payload}.{signature}")


def test_cursor_decode_invalid_fields_raises():
    cursor = _make_cursor(page=-1)
    with pytest.raises(InvalidRecoCursorEXC):
        BookMainRecoCursorDTO.decode(cursor.encode())


# --- _weighted_sample ---

def test_weighted_sample_deterministic_and_unique():
    items = list(range(100))
    weights = [float(i + 1) for i in items]

    first = _weighted_sample(items, weights, limit=10, seed=42, key_fn=lambda x: x)
    second = _weighted_sample(items, weights, limit=10, seed=42, key_fn=lambda x: x)

    assert first == second
    assert len(first) == 10
    assert len(set(first)) == 10


def test_weighted_sample_pool_exhausted_falls_back_to_order():
    items = [1, 2, 3]
    result = _weighted_sample(
        items, [1.0, 1.0, 1.0], limit=10, seed=1, key_fn=lambda x: x
    )
    assert sorted(result) == items


def test_weighted_sample_zero_weights():
    items = [1, 2, 3, 4]
    result = _weighted_sample(
        items, [0.0] * 4, limit=2, seed=7, key_fn=lambda x: x
    )
    assert len(result) == 2


# --- cold candidates ---

def _row(id, rating=None, sum_ratings=None, total_sales=None, category_id=1, author_id=1):
    return SimpleNamespace(
        id=id,
        category_id=category_id,
        author_id=author_id,
        rating=rating,
        sum_ratings=sum_ratings,
        total_sales=total_sales,
    )


def test_score_bayes_many_votes_beat_single_five_star():
    # Реалистичный пул: средний рейтинг ~3.9, иначе сглаживание
    # к среднему двух книг делает сравнение бессмысленным
    rows = [
        _row(i, rating=3.5 + (i % 10) * 0.1, sum_ratings=50)
        for i in range(10, 30)
    ]
    rows += [
        _row(1, rating=5.0, sum_ratings=1),
        _row(2, rating=4.8, sum_ratings=1000),
    ]

    scored = {c.id: c for c in BookColdCandidatesProvider._score(rows)}

    assert scored[2].quality > scored[1].quality


def test_score_handles_nulls_and_normalizes():
    rows = [
        _row(1),
        _row(2, rating=4.0, sum_ratings=10, total_sales=500),
    ]

    scored = BookColdCandidatesProvider._score(rows)

    for c in scored:
        assert 0.0 <= c.quality <= 1.0
        assert 0.0 <= c.sales <= 1.0
        assert 0.0 <= c.freshness <= 1.0


def test_score_freshness_higher_for_newer_ids():
    rows = [_row(1), _row(100)]
    scored = {c.id: c for c in BookColdCandidatesProvider._score(rows)}
    assert scored[100].freshness > scored[1].freshness


def test_cold_weights_do_not_collapse_to_freshness():
    """
        Каталог без рейтингов и продаж: перекос по новизне
        должен быть ограничен, иначе фид заливает последней
        добавленной категорией.
    """
    from app.product.service.infrastructure.query_handlers.book.main_reco import (
        _cold_quality_weight,
        _cold_sales_weight,
    )

    oldest = ColdCandidateDTO(
        id=1, category_id=1, author_id=1,
        quality=0.0, sales=0.0, freshness=0.0,
    )
    newest = ColdCandidateDTO(
        id=2, category_id=2, author_id=2,
        quality=0.0, sales=0.0, freshness=1.0,
    )

    for weight_fn in (_cold_quality_weight, _cold_sales_weight):
        ratio = weight_fn(newest) / weight_fn(oldest)
        assert ratio <= 2.0


def test_diversified_pick_respects_category_cap():
    candidates = [
        ColdCandidateDTO(
            id=i,
            category_id=7,  # все из одной категории
            author_id=i,
            quality=1.0,
            sales=1.0,
            freshness=0.5,
        )
        for i in range(30)
    ]
    # плюс альтернативные категории
    candidates += [
        ColdCandidateDTO(
            id=100 + i,
            category_id=8 + i,
            author_id=100 + i,
            quality=0.5,
            sales=0.5,
            freshness=0.5,
        )
        for i in range(10)
    ]

    weights = [1.0] * len(candidates)
    result = _diversified_pick(candidates, weights, limit=8, seed=1)

    by_id = {c.id: c for c in candidates}
    from_cat_7 = sum(1 for bid in result if by_id[bid].category_id == 7)

    assert len(result) == 8
    assert from_cat_7 <= 2


def test_diversified_pick_fills_when_caps_too_strict():
    # Все из одной категории/автора — капы невыполнимы, но страница заполняется
    candidates = [
        ColdCandidateDTO(
            id=i, category_id=1, author_id=1,
            quality=1.0, sales=1.0, freshness=0.5,
        )
        for i in range(20)
    ]

    result = _diversified_pick(candidates, [1.0] * 20, limit=8, seed=2)

    assert len(result) == 8
    assert len(set(result)) == 8


# --- blender ---

def test_blender_full_sources_respects_slot_counts():
    slots = BookBlenderSlotsDTO(
        personalized=list(range(100, 108)),
        popular=list(range(200, 206)),
        new=list(range(300, 304)),
        exploration=list(range(400, 402)),
    )

    result = BookMainRecoBlender().mix(slots, seed=42, page=0)

    assert len(result) == sum(SLOT_COUNTS.values())
    assert len(set(result)) == len(result)
    assert sum(1 for bid in result if 100 <= bid < 200) == SLOT_COUNTS[FeedSlot.PERSONALIZED]
    assert sum(1 for bid in result if 200 <= bid < 300) == SLOT_COUNTS[FeedSlot.POPULAR]


def test_blender_exhausted_source_uses_fallback_chain():
    slots = BookBlenderSlotsDTO(
        personalized=[],
        popular=list(range(200, 220)),
        new=[],
        exploration=[],
    )

    result = BookMainRecoBlender().mix(slots, seed=1, page=2)

    assert len(result) == sum(SLOT_COUNTS.values())
    assert all(200 <= bid < 220 for bid in result)


def test_blender_dedupes_across_sources():
    slots = BookBlenderSlotsDTO(
        personalized=[1, 2, 3],
        popular=[1, 2, 3],
        new=[1, 2, 3],
        exploration=[1, 2, 3],
    )

    result = BookMainRecoBlender().mix(slots, seed=5, page=0)

    assert sorted(result) == [1, 2, 3]


def test_blender_deterministic_by_seed_and_page():
    slots = BookBlenderSlotsDTO(
        personalized=list(range(8)),
        popular=list(range(10, 16)),
        new=list(range(20, 24)),
        exploration=list(range(30, 32)),
    )

    blender = BookMainRecoBlender()
    assert blender.mix(slots, seed=9, page=1) == blender.mix(slots, seed=9, page=1)
