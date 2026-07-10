from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData

NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s", 
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

class Base(DeclarativeBase):
    __abstract__ = True

    metadata = MetaData(
        naming_convention=NAMING_CONVENTION
    )

    def __repr__(self):
        id_val = getattr(self, "id", "n/a")
        return f"<{self.__class__.__name__} — (id={id_val})>"