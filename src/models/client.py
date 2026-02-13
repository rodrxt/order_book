from pydantic import BaseModel, EmailStr, Field, model_validator
from datetime import datetime
from typing import Optional

class Client(BaseModel):
    # Se añade automáticamente en la tabla
    id: Optional[int] = None
    client_name: str = Field(min_length = 3, max_length = 50)
    email: EmailStr 
    created_at: Optional[datetime] = None

class ClientSearch(BaseModel):
    """Creamos esta clase para búsqueda de usuarios"""
    client_name: Optional[str] = Field(default=None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None

    @model_validator(mode='after')
    def check_at_least_one(self):
        if not self.client_name and not self.email:
            raise ValueError('There must be at least one element to delete client')
        return self
    
    @property
    def nickname(self):
        parts = [self.client_name, self.email]
        return " - ".join(p for p in parts if p is not None)
