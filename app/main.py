from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import text

from .db import Base, engine, get_db
from . import models, schemas
from .auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    get_token_remaining,
)

AUTH_DOCS_DESCRIPTION = """
## Flujo de uso (Auth → Token)

1. **Obtener token JWT** (cuenta ya creada por admin o CLI):
   - `POST /login`
   - Copia `access_token`

2. **Consultar tiempo restante** del token:
   - `GET /token/remaining` (requiere `Authorization: Bearer <token>`)

3. **Probar identidad**:
   - `GET /whoami` (requiere `Authorization: Bearer <token>`)

4. **Crear usuarios** (solo admin):
   - `POST /players`

5. **Gestionar roles** (solo admin):
   - `PATCH /admin/players/{player_id}/roles`

## Vigencia del token
- El JWT expira según `JWT_EXPIRE_MINUTES` (por defecto **120 minutos**).
- Los roles se leen de la tabla `player_roles` en cada login.

Fuente:
- González-Ibáñez, R., Macías-Cáceres, J., Villalta-Paucar, M. (2025).
  LifeSync-Games: Toward a Video Game Paradigm for Promoting Responsible
  Gaming and Human Development. arXiv:2510.19691 [cs.HC].
"""

app = FastAPI(
    title="LifeSync-Games Auth Service",
    version="1.1.0",
    description=AUTH_DOCS_DESCRIPTION,
    root_path=os.getenv("LSG_AUTH_ROOT_PATH", "/lsg-auth"),
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


def get_current_player(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.Player:
    """
    Valida el JWT y retorna el Player correspondiente.
    Los roles vienen de player_roles a través de player.roles (property).
    """
    try:
        payload = decode_access_token(token)
        sub = payload.get("sub")
        if sub is None:
            raise ValueError("claim 'sub' ausente")
        player_id = int(sub)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    player = db.query(models.Player).filter(
        models.Player.id_players == player_id
    ).first()

    if player is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado.",
        )
    return player


def require_roles(allowed: List[str]):
    """
    Dependency factory para proteger endpoints por rol.

    Uso:
        @app.post("/ruta", dependencies=[Depends(require_roles(["admin"]))])

    O como parámetro para obtener el player:
        current_admin: models.Player = Depends(require_roles(["admin"]))
    """
    def _dependency(
        current_player: models.Player = Depends(get_current_player),
    ) -> models.Player:
        player_roles = current_player.roles  # List[str] desde property
        if not any(r in allowed for r in player_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code":         "INSUFFICIENT_ROLE",
                    "required_any": allowed,
                    "your_roles":   player_roles,
                },
            )
        return current_player
    return _dependency


@app.get("/health")
def healthcheck(db: Session = Depends(get_db)):
    """Healthcheck: Verifica si la API responde y la base de datos está disponible."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "ok"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"DB error: {e}",
        )


@app.post(
    "/players",
    response_model=schemas.PlayerOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear jugador",
    tags=["admin"],
)
def create_player(
    player_in: schemas.PlayerCreate,
    db: Session = Depends(get_db),
    current_admin: models.Player = Depends(require_roles(["admin"])),
):
    """
    Crea un nuevo jugador e inserta su rol inicial en player_roles.

    **Roles disponibles:** "admin"
    """
    player = models.Player(
        name          = player_in.name,
        email         = player_in.email,
        password_hash = hash_password(player_in.password),
        age           = player_in.age,
    )
    db.add(player)

    try:
        db.flush()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo crear el jugador: {e}",
        )

    role_record = models.PlayerRole(
        id_players  = player.id_players,
        role        = player_in.role or "player",
        assigned_by = current_admin.id_players,
    )
    db.add(role_record)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo crear el jugador: {e}",
        )

    db.refresh(player)
    return player


@app.post("/login", response_model=schemas.Token, tags=["auth"])
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Login OAuth2 (username = email del jugador).

    **Roles disponibles:** "player", "teacher", "researcher", "admin"
    """
    player = (
        db.query(models.Player)
        .filter(models.Player.email == form_data.username)
        .first()
    )

    if not player or not verify_password(form_data.password, player.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    active_roles = player.roles

    claims = {
        "sub":       str(player.id_players),
        "player_id": int(player.id_players),
        "email":     player.email,
        "roles":     active_roles,
        "type":      "user",
    }
    access_token = create_access_token(claims)
    return schemas.Token(access_token=access_token, token_type="bearer")


@app.get("/token/remaining", response_model=schemas.TokenRemaining, tags=["auth"])
def token_remaining(token: str = Depends(oauth2_scheme)):
    """
    Retorna los segundos restantes del token activo.
    
    **Roles disponibles:** "player", "teacher", "researcher", "admin"
    """
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
        )
    return get_token_remaining(payload)


@app.post("/token/refresh", response_model=schemas.Token, tags=["auth"])
def refresh_token(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    Renueva el token JWT sin necesidad de hacer login de nuevo.
 
    El token actual debe ser válido (no expirado).
    Retorna un nuevo token con los roles actualizados desde `player_roles`.
 
    Ideal para mantener sesión activa durante el uso prolongado del Swagger
    o en mods de videojuego que necesitan refrescar el token automáticamente.
 
    **Nota:** Si el token ya expiró, usar POST /login.
    """
    import time
 
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Token inválido o expirado. Usa POST /login para obtener uno nuevo.",
        )
 
    # Verificar que queden al menos 30 segundos (anti-spam)
    remaining = payload.get("exp", 0) - int(time.time())
    if remaining > 30:
        # Token aún vigente — renovar de todas formas (roles pueden haber cambiado)
        pass
 
    player_id = int(payload.get("sub", 0))
    player = db.query(models.Player).filter(
        models.Player.id_players == player_id
    ).first()
    if not player:
        raise HTTPException(status_code=401, detail="Usuario no encontrado.")
 
    # Leer roles ACTUALIZADOS desde player_roles (pueden haber cambiado desde el login)
    active_roles = player.roles
 
    new_token = create_access_token({
        "sub":       str(player.id_players),
        "player_id": player.id_players,
        "email":     player.email,
        "roles":     active_roles,
        "type":      "user",
    })
    return schemas.Token(access_token=new_token, token_type="bearer")
 

@app.get("/whoami", response_model=schemas.PlayerOut, tags=["auth"])
def whoami(current_player: models.Player = Depends(get_current_player)):
    """
    Devuelve información del jugador autenticado.
    El campo 'roles' contiene la lista de roles activos desde player_roles.
    """
    return current_player


@app.patch(
    "/admin/players/{player_id}/roles",
    response_model=schemas.RoleAssignResponse,
    tags=["admin"],
    summary="Asignar o revocar rol a un jugador",
)
def manage_player_role(
    player_id: int,
    body: schemas.RoleAssignRequest,
    db: Session = Depends(get_db),
    current_admin: models.Player = Depends(require_roles(["admin"])),
):
    """
    Asigna ('grant') o revoca ('revoke') un rol a un jugador.

    - **grant**: inserta una nueva fila en player_roles (idempotente si ya existe activo).
    - **revoke**: setea revoked_at = NOW() en la fila activa del rol indicado.
    - **role**: ["player", "teacher", "researcher", "admin"]

    Ejemplo:
    ```json
    { "role": "researcher", "action": "grant" }
    ```

    **Roles disponibles:** "admin"
    """
    target = db.query(models.Player).filter(
        models.Player.id_players == player_id
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="Jugador no encontrado.")

    if body.action == "grant":
        # Idempotente: si el rol ya está activo no duplicar
        already_active = any(pr.role == body.role for pr in target._roles if pr.revoked_at is None)
        if not already_active:
            db.add(models.PlayerRole(
                id_players  = player_id,
                role        = body.role,
                assigned_by = current_admin.id_players,
            ))
            db.commit()

    elif body.action == "revoke":
        for pr in target._roles:
            if pr.role == body.role and pr.revoked_at is None:
                pr.revoked_at = datetime.utcnow()
        db.commit()

    db.refresh(target)
    return schemas.RoleAssignResponse(
        status    = "ok",
        player_id = player_id,
        role      = body.role,
        action    = body.action,
    )


class RoleHistory(BaseModel):
    """Registro histórico de un rol (activo o revocado)."""
    id_player_role: int
    role:           str
    assigned_at:    Optional[datetime]
    assigned_by:    Optional[int]
    revoked_at:     Optional[datetime]
    is_active:      bool   # True si revoked_at IS NULL

@app.get(
    "/admin/players/{player_id}/roles",
    response_model=List[RoleHistory],
    tags=["admin"],
    summary="Historial de roles de un jugador",
)
def get_player_roles(
    player_id: int,
    include_revoked: bool = True,
    db: Session = Depends(get_db),
    _: models.Player = Depends(require_roles(["admin"])),
):
    """
    Devuelve el historial completo de roles de un jugador.

    - `include_revoked=true` (default): incluye roles activos e históricos.
    - `include_revoked=false`: solo roles activos (`revoked_at IS NULL`).

    Útil para auditoría de cambios de rol y para verificar el estado actual.

    cURL de ejemplo:
    ```bash
    # Roles activos de jugador 26
    curl -X GET '/lsg-auth/admin/players/26/roles?include_revoked=false' \\
      -H 'Authorization: Bearer <TOKEN_ADMIN>'

    # Historial completo (activos + revocados)
    curl -X GET '/lsg-auth/admin/players/26/roles' \\
      -H 'Authorization: Bearer <TOKEN_ADMIN>'
    ```

    **Roles disponibles:** "admin"
    """
    target = db.query(models.Player).filter(
        models.Player.id_players == player_id
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="Jugador no encontrado.")

    roles = target._roles
    if not include_revoked:
        roles = [r for r in roles if r.revoked_at is None]

    return [
        RoleHistory(
            id_player_role = pr.id_player_role,
            role           = pr.role,
            assigned_at    = pr.assigned_at,
            assigned_by    = pr.assigned_by,
            revoked_at     = pr.revoked_at,
            is_active      = pr.revoked_at is None,
        )
        for pr in sorted(roles, key=lambda r: r.assigned_at or datetime.min, reverse=True)
    ]