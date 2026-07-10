from dataclasses import dataclass

@dataclass(slots=True)
class QdrantPointDTO:
    id: int | str
    vector: list[float]
    payload: dict