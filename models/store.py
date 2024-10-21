from typing import Optional
import uuid

from sqlmodel import Field, SQLModel, Relationship


class Store(SQLModel, table=True):
    id: Optional[str] = Field(primary_key=True, default_factory=lambda: uuid.uuid4().hex, index=True)
    name: str

    deals: list['Deal'] = Relationship(back_populates='store')  # noqa: F821
