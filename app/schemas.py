from typing import Optional, Literal
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

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PasswordChangeRequest(BaseModel):
    new_password: str

    model_config = {"str_min_length": 8}


class RoleAssignRequest(BaseModel):
    role:   str
    action: Literal["grant", "revoke"]