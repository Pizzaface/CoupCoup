import uuid
from datetime import datetime
from enum import StrEnum
from typing import Optional

from sqlmodel import Field, SQLModel, Relationship

from models.store import Store


class DealType(StrEnum):
    PERCENT_OFF = 'PERCENT_OFF'
    AMOUNT_OFF = 'AMOUNT_OFF'
    BUY_X_GET_Y_AT_Z_PER_OFF = 'BUY_X_GET_Y_AT_Z_PER_OFF'
    BUY_X_GET_Y_AT_Z_AMO_OFF = 'BUY_X_GET_Y_AT_Z_AMO_OFF'
    BUY_X_GET_Y_FREE = 'BUY_X_GET_Y_FREE'
    BUY_X_GET_Y_AMOUNT_OFF = 'BUY_X_GET_Y_AMOUNT_OFF'
    PRICE_PER_AMOUNT = 'PRICE_PER_AMOUNT'
    SALE_PRICE = 'SALE_PRICE'
    REWARD_POINTS = 'REWARD_POINTS'
    OTHER = 'OTHER'


class Deal(SQLModel, table=True):
    id: Optional[str] = Field(primary_key=True, default_factory=lambda: uuid.uuid4().hex, index=True)

    store_id: str | None = Field(default=None, foreign_key='store.id')
    store: Store | None = Relationship(back_populates='deals')
    deal_type: DealType = Field(default=DealType.OTHER)

    brand_name: str | None = Field(default=None, alias='brand_names')
    product_name: str
    product_variety: str | None = Field(default=None)
    description: str | None = Field(default=None)

    required_purchase_quantity: int | None = Field(default=None)
    required_purchase_price: float | None = Field(default=None)

    price: float | None = Field(default=None)

    sale_price: float | None = Field(default=None)
    sale_amount_off: float | None = Field(default=None)
    sale_percent_off: float | None = Field(default=None)

    quantity_at_sale_price: int | None = Field(default=None)
    quantity_at_amount_off: int | None = Field(default=None)
    quantity_get_free: int | None = Field(default=None)
    quantity_at_percent_off: int | None = Field(default=None)

    valid_from: datetime = Field(default_factory=datetime.now)
    valid_to: datetime = Field(default_factory=datetime.now)

    requires_store_card: bool = Field(default=False)
