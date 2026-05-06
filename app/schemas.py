from typing import Optional, List, Literal
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict

VALID_ROLES = {"player", "teacher", "researcher", "admin"}


class PlayerCreate(BaseModel):
    """
    Usado por POST /players (solo admin).
    El campo 'role' especifica el rol inicial que se inserta en player_roles.
    """
    name:     str
    email:    EmailStr
    password: str
    age:      Optional[int] = None
    role:     Optional[str] = "player"

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in VALID_ROLES:
            raise ValueError(
                f"Rol inválido: '{v}'. Valores permitidos: {sorted(VALID_ROLES)}"
            )
        return v


class PlayerLogin(BaseModel):
    email:    EmailStr
    password: str


class PlayerOut(BaseModel):
    """
    Respuesta de endpoints que devuelven datos de un jugador.
    CAMBIO: 'role' (str singular) → 'roles' (List[str]).
    from_attributes=True permite que Pydantic lea player.roles (property).
    """
    model_config = ConfigDict(from_attributes=True)

    id_players: int
    name:       str
    email:      EmailStr
    age:        Optional[int] = None
    roles:      List[str] = []


class Token(BaseModel):
    access_token: str
    token_type:   str = "bearer"


class TokenRemaining(BaseModel):
    """Respuesta de GET /token/remaining."""
    expires_in_seconds: int
    expires_at:         str              # ISO-8601 UTC
    issued_at:          Optional[str] = None

class RoleAssignRequest(BaseModel):
    """
    Usado por PATCH /admin/players/:id/roles.
    'action': grant agrega el rol, revoke lo marca como revocado.
    """
    role:   Literal["player", "teacher", "researcher", "admin"]
    action: Literal["grant", "revoke"]


class RoleAssignResponse(BaseModel):
    status:    str
    player_id: int
    role:      str
    action:    str