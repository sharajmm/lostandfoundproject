from pydantic import BaseModel
from typing import Optional
from datetime import date

# Used when reporting a lost/found item
class Item(BaseModel):
    item_name: str 
    description: str
    location: str
    status: Optional[str] = "Lost"   # Default is "Lost"
    date_reported: Optional[date] = None  # If not given, we'll insert today's date from backend

class UserLogin(BaseModel):
    username: str
    password: str
