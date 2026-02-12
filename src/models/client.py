from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional

class Client(BaseModel):
    # Se añade automáticamente en la tabla
    id: Optional[int] = None
    client_name: str = Field(min_length = 3, max_length = 50)
    email: EmailStr 
    created_at: Optional[datetime] = None
