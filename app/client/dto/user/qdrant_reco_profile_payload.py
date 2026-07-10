from dataclasses import dataclass

@dataclass(slots=True)
class UserRecoProfileQdrantPayloadDTO:
    top_authors: list[str]
    top_categories: list[str]
    recent_searches: list[str]
    descriptions: list[str | None]