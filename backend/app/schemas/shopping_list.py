from typing import List, Optional
from pydantic import BaseModel, Field


class ShoppingListItem(BaseModel):
    name: str
    quantity: float = Field(gt=0)
    unit: str
    category: str
    excluded: bool = False
    used_in: Optional[List[str]] = None


class ShoppingListResponse(BaseModel):
    source: str
    items: List[ShoppingListItem]


class ShoppingListUpdateItem(BaseModel):
    name: str
    quantity: float = Field(gt=0)
    excluded: bool = False


class ShoppingListUpdateRequest(BaseModel):
    items: List[ShoppingListUpdateItem]
