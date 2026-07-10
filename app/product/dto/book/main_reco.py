import base64
import binascii
import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Literal

from app.core.config.base import get_settings
from app.product.db.postgres.models.book import BookModel
from app.product.exception.book.invalid_reco_cursor import InvalidRecoCursorEXC

PersonalizedMode = Literal["vector", "collaborative"]

_PERSONALIZED_MODES = ("vector", "collaborative")
_MAX_SESSION_ID_LEN = 64


def _sign(payload: bytes) -> str:
    secret = get_settings().app.secret_key.encode()
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()


@dataclass(slots=True)
class BookMainRecoCursorDTO:
    """
        Курсор фида. Приходит от клиента, поэтому:
        - подписан HMAC — подмена seed/page/offset/session_id невозможна;
        - любой битый токен -> InvalidRecoCursorEXC (400), а не 500.
    """

    session_id: str
    seed: int
    page: int

    personalized_mode: PersonalizedMode = "vector"
    personalized_offset: int = 0
    collaborative_offset: int = 0

    popular_last_score: float | None = None
    popular_last_book_id: int | None = None
    new_last_id: int | None = None
    exploration_last_random_key: int | None = None

    def encode(self) -> str:
        data = {
            "sid": self.session_id,
            "s":   self.seed,
            "p":   self.page,
            "pm":  self.personalized_mode,
            "po":  self.personalized_offset,
            "co":  self.collaborative_offset,
            "ps":  self.popular_last_score,
            "pb":  self.popular_last_book_id,
            "nl":  self.new_last_id,
            "er":  self.exploration_last_random_key,
        }

        payload = base64.urlsafe_b64encode(
            json.dumps(data, separators=(",", ":")).encode()
        ).decode()

        return f"{payload}.{_sign(payload.encode())}"

    @classmethod
    def decode(cls, token: str) -> "BookMainRecoCursorDTO":
        payload, _, signature = token.rpartition(".")

        if not payload or not hmac.compare_digest(
            _sign(payload.encode()),
            signature,
        ):
            raise InvalidRecoCursorEXC()

        try:
            data = json.loads(base64.urlsafe_b64decode(payload.encode()))
            cursor = cls(
                session_id=data["sid"],
                seed=data["s"],
                page=data["p"],
                personalized_mode=data.get("pm", "vector"),
                personalized_offset=data.get("po", 0),
                collaborative_offset=data.get("co", 0),
                popular_last_score=data.get("ps"),
                popular_last_book_id=data.get("pb"),
                new_last_id=data.get("nl"),
                exploration_last_random_key=data.get("er"),
            )
        except (
            binascii.Error,
            json.JSONDecodeError,
            UnicodeDecodeError,
            KeyError,
            TypeError,
            ValueError,
        ):
            raise InvalidRecoCursorEXC() from None

        cursor._validate()
        return cursor

    def _validate(self) -> None:
        is_valid = (
            isinstance(self.session_id, str)
            and 0 < len(self.session_id) <= _MAX_SESSION_ID_LEN
            and isinstance(self.seed, int)
            and isinstance(self.page, int)
            and self.page >= 0
            and self.personalized_mode in _PERSONALIZED_MODES
            and isinstance(self.personalized_offset, int)
            and self.personalized_offset >= 0
            and isinstance(self.collaborative_offset, int)
            and self.collaborative_offset >= 0
        )

        if not is_valid:
            raise InvalidRecoCursorEXC()

    @classmethod
    def initial(cls, seed: int, session_id: str) -> "BookMainRecoCursorDTO":
        return cls(session_id=session_id, seed=seed, page=0)


@dataclass(slots=True)
class BookPersonalizedRecoStatusDTO:
    mode: PersonalizedMode
    personalized_offset: int
    collaborative_offset: int


@dataclass
class BookBlenderSlotsDTO:
    personalized: list[int]
    popular: list[int]
    new: list[int]
    exploration: list[int]


@dataclass
class BookRecommendationsDTO:
    books: list[BookModel]
    next_cursor: str | None
