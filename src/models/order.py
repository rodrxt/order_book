from pydantic import BaseModel, Field, model_validator
from enum import Enum
from datetime import datetime
from typing import Optional

class OrderSide(str, Enum):
    ASK = "ASK"
    BID = "BID"

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    BEST = "BEST"

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"

class Order(BaseModel):
    id: Optional[int] = None
    order_side: OrderSide
    order_type: OrderType
    quantity: int = Field(..., gt = 0)
    remaining_quantity: int = Field(..., gt = 0)
    price: Optional[float] = Field(None, gt = 0)
    ticker: str
    client_id: int
    status: OrderStatus
    created_at: Optional[datetime] = None

    @model_validator(mode='after')
    def check_price(self):
        if self.order_type not in (OrderType.MARKET,) and self.price is None:
            raise ValueError('There must be a price if the order is not a MARKET order')
        return self

