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


class PasswordChangeRequest(BaseModel):
    """Body para PATCH /admin/players/{id}/password"""
    new_password: str

    model_config = {"min_anystr_length": 8}   # Pydantic v1 compat
    # Nota: si estás en Pydantic v2, reemplazar por:
    # model_config = ConfigDict(str_min_length=8)


class RoleAssignRequest(BaseModel):
    """Body para PATCH /admin/players/{id}/roles"""
    role:   str   # player | teacher | researcher | admin | developer
    action: str   # grant | revoke


class TempPlayerOut(BaseModel):
    """Resultado por cada cuenta temporal creada."""
    id_players:      int
    email:           str
    temp_password:   str   # solo se muestra al crear, nunca después
    role:            str
    expires_at:      str   # ISO-8601


class BatchTempPlayersRequest(BaseModel):
    """Body para POST /admin/players/batch-temp"""
    count:      int = 5     # número de cuentas a crear (1-50)
    days_active: int = 7    # días de activación desde la creación
    role:       str = "player"   # rol asignado a todas las cuentas
    name_prefix: str = "test"    # prefijo del nombre: test_a1b2, test_x9y3...


class PlayerInfo(BaseModel):
    """Datos básicos del jugador incluidos en la respuesta del login."""
    id_players: int
    name:       str
    email:      str
    age:        Optional[int] = None
    roles:      list = []
    model_config = {"from_attributes": True}
 
 
class TokenWithPlayer(BaseModel):
    """
    Respuesta enriquecida de POST /login.
    Incluye el token y los datos del jugador, eliminando la necesidad
    de llamar a GET /whoami después del login.
    """
    access_token: str
    token_type:   str = "bearer"
    expires_at:   Optional[str] = None
    player:       PlayerInfo