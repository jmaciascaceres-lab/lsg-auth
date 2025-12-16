from typing import Optional
from pydantic import BaseModel, EmailStr


class PlayerCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    age: Optional[int] = None
    role: Optional[str] = "player"

class PlayerLogin(BaseModel):
    email: EmailStr
    password: str


class PlayerOut(BaseModel):
    id_players: int
    name: str
    email: EmailStr
    age: Optional[int] = None
    role: Optional[str] = "player"
    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
