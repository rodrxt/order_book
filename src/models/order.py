from pydantic import BaseModel, Field, field_validator
from enum import Enum
from datetime import datetime
from typing import Optional

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    BEST = "BEST"

class Order(BaseModel):
    id: Optional[int] = None
    order_side: OrderSide
    order_type: OrderType
    quantity: int = Field(..., gt = 0)
    price: float = Field(..., gt = 0)
    ticker: str
    client_id: int
    created_at: Optional[datetime] = None
