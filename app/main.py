import os
from datetime import timedelta, datetime
import time

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import (
    verify_password,
    hash_password,
    create_access_token,
    decode_access_token,
    get_token_remaining,
)
from app.db import get_db

# Configuración
AUTH_DISABLED = os.getenv("AUTH_DISABLED", "false").lower() == "true"
ROOT_PATH     = os.getenv("LSG_AUTH_ROOT_PATH", "")

AUTH_DOCS_DESCRIPTION = """
## LSG-Auth — Servicio de Autenticación

Gestiona jugadores, roles y tokens JWT para el ecosistema LifeSync-Games.

**Flujo básico:**
1. `POST /login` con tu email y contraseña → obtén `access_token`
2. Úsalo en LSG-Core-API: botón **Authorize** → `Bearer <token>`
3. El token expira en **120 minutos**. Renuévalo con `POST /token/refresh`.

**Roles:** `player` | `teacher` | `researcher` | `admin`
"""

app = FastAPI(
    title       = "LSG-Auth",
    version     = "1.1.0",
    root_path   = ROOT_PATH,
    description = AUTH_DOCS_DESCRIPTION,
)


# ── Helpers internos ────────────────────────────────────────────────────────────

def require_roles(allowed_roles: list):
    """Dependencia: valida que el token tenga al menos uno de los roles indicados."""
    from fastapi import Security
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

    bearer = HTTPBearer(auto_error=False)

    def _check(
        credentials: HTTPAuthorizationCredentials = Security(bearer),
        db: Session = Depends(get_db),
    ):
        if AUTH_DISABLED:
            # Modo desarrollo sin BD de auth
            admin = models.Player(id_players=0, name="dev_admin", email="admin@dev")
            admin._roles = [models.PlayerRole(role="admin")]
            return admin

        if not credentials:
            raise HTTPException(status_code=401, detail="Token requerido.")

        try:
            payload = decode_access_token(credentials.credentials)
        except Exception:
            raise HTTPException(status_code=401, detail="Token inválido o expirado.")

        player_id = int(payload.get("sub", 0))
        player = db.query(models.Player).filter(
            models.Player.id_players == player_id
        ).first()
        if not player:
            raise HTTPException(status_code=401, detail="Usuario no encontrado.")

        active_roles = player.roles   # propiedad del modelo que lee player_roles
        if not any(r in allowed_roles for r in active_roles):
            raise HTTPException(
                status_code=403,
                detail=f"Se requiere uno de estos roles: {allowed_roles}",
            )
        return player

    return _check


def _get_current_player(
    credentials=None,
    db: Session = Depends(get_db),
):
    """Dependencia: cualquier rol autenticado."""
    from fastapi import Security
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    bearer = HTTPBearer()
    return None


# GET /health

@app.get("/health", tags=["health"])
def health(db: Session = Depends(get_db)):
    """Healthcheck del servicio y conexión a BD."""
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        return {"status": "ok", "db": "ok"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"DB error: {e}")


# POST /login

@app.post("/login", response_model=schemas.Token, tags=["auth"])
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db:   Session = Depends(get_db),
):
    """
    Inicio de sesión. El campo `username` debe contener el **email** del usuario.

    Retorna un JWT válido por **120 minutos**.
    """
    player = db.query(models.Player).filter(
        models.Player.email == form.username
    ).first()

    if not player or not verify_password(form.password, player.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas.")

    active_roles = player.roles
    token = create_access_token({
        "sub":       str(player.id_players),
        "player_id": player.id_players,
        "email":     player.email,
        "roles":     active_roles,
        "type":      "user",
    })
    return schemas.Token(access_token=token)


# GET /whoami

@app.get("/whoami", tags=["auth"])
def whoami(
    current: models.Player = Depends(require_roles(
        ["admin", "researcher", "teacher", "player"]
    )),
):
    """Perfil del usuario autenticado, incluyendo roles activos."""
    return {
        "id_players": current.id_players,
        "name":       current.name,
        "email":      current.email,
        "age":        current.age,
        "roles":      current.roles,
    }


# GET /token/remaining

@app.get("/token/remaining", tags=["auth"])
def token_remaining_endpoint(
    current: models.Player = Depends(require_roles(
        ["admin", "researcher", "teacher", "player"]
    )),
    credentials=None,
):
    """
    Devuelve cuántos segundos le quedan al token activo.
    Si `expires_in_seconds` llega a 0, el token ya expiró → usar `POST /login`.
    """
    # En la implementación real se decodifica el token del header
    # y se calcula el tiempo restante con get_token_remaining(payload)
    return {"expires_in_seconds": -1, "message": "Ver implementación en auth.py"}


# POST /token/refresh

@app.post("/token/refresh", response_model=schemas.Token, tags=["auth"])
def refresh_token(
    current: models.Player = Depends(require_roles(
        ["admin", "researcher", "teacher", "player"]
    )),
):
    """
    Renueva el token JWT sin necesidad de hacer login nuevamente.
    Los roles se actualizan desde la BD en el nuevo token.

    Útil para scripts y mods que necesitan sesión activa prolongada.
    """
    active_roles = current.roles
    new_token = create_access_token({
        "sub":       str(current.id_players),
        "player_id": current.id_players,
        "email":     current.email,
        "roles":     active_roles,
        "type":      "user",
    })
    return schemas.Token(access_token=new_token)


# POST /players

@app.post("/players", status_code=201, tags=["admin"])
def create_player(
    payload:       schemas.PlayerCreate,
    db:            Session = Depends(get_db),
    current_admin: models.Player = Depends(require_roles(["admin"])),
):
    """
    Crea un nuevo jugador/participante LSG.

    El primer usuario admin debe crearse desde el CLI del contenedor:
    ```
    docker compose exec app python -m app.cli_create_user --email admin@lsg.cl --role admin
    ```

    **Roles disponibles:** "admin"
    """
    existing = db.query(models.Player).filter(
        models.Player.email == payload.email
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email ya registrado.")

    valid_roles = {"player", "teacher", "researcher", "admin"}
    role = payload.role or "player"
    if role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Rol inválido. Opciones: {valid_roles}",
        )

    new_player = models.Player(
        name          = payload.name,
        email         = payload.email,
        password_hash = hash_password(payload.password),
        age           = payload.age,
    )
    db.add(new_player)
    db.flush()

    db.add(models.PlayerRole(
        id_players  = new_player.id_players,
        role        = role,
        assigned_by = current_admin.id_players,
    ))
    db.commit()
    db.refresh(new_player)

    return {
        "id_players": new_player.id_players,
        "name":       new_player.name,
        "email":      new_player.email,
        "age":        new_player.age,
        "roles":      new_player.roles,
    }


# PATCH /admin/players/{player_id}/roles

@app.patch("/admin/players/{player_id}/roles", tags=["admin"],
           summary="Asignar o revocar rol a un jugador")
def manage_player_role(
    player_id:     int,
    body:          schemas.RoleAssignRequest,
    db:            Session = Depends(get_db),
    current_admin: models.Player = Depends(require_roles(["admin"])),
):
    """
    Asigna (`grant`) o revoca (`revoke`) un rol a un jugador.

    - **grant**: idempotente — si el rol ya existe activo, no lo duplica.
    - **revoke**: marca `revoked_at = NOW()`, no borra el historial.

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

    valid_roles = {"player", "teacher", "researcher", "admin"}
    if body.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Rol inválido. Opciones: {valid_roles}")

    if body.action == "grant":
        existing = db.query(models.PlayerRole).filter(
            models.PlayerRole.id_players == player_id,
            models.PlayerRole.role       == body.role,
            models.PlayerRole.revoked_at.is_(None),
        ).first()
        if not existing:
            db.add(models.PlayerRole(
                id_players  = player_id,
                role        = body.role,
                assigned_by = current_admin.id_players,
            ))
            db.commit()

    elif body.action == "revoke":
        from sqlalchemy import func
        db.query(models.PlayerRole).filter(
            models.PlayerRole.id_players == player_id,
            models.PlayerRole.role       == body.role,
            models.PlayerRole.revoked_at.is_(None),
        ).update({"revoked_at": func.now()})
        db.commit()
    else:
        raise HTTPException(status_code=400, detail="action debe ser 'grant' o 'revoke'.")

    return {"status": "ok", "player_id": player_id, "role": body.role, "action": body.action}


# GET /admin/players/{player_id}/roles

@app.get("/admin/players/{player_id}/roles", tags=["admin"],
         summary="Historial de roles de un jugador")
def get_player_roles(
    player_id:       int,
    include_revoked: bool = True,
    db:              Session = Depends(get_db),
    _:               models.Player = Depends(require_roles(["admin"])),
):
    """
    Devuelve todos los roles (activos e históricos) de un jugador.

    - `include_revoked=true` (default): activos + revocados.
    - `include_revoked=false`: solo roles activos (`revoked_at IS NULL`).

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
        {
            "id_player_role": pr.id_player_role,
            "role":           pr.role,
            "assigned_at":    pr.assigned_at,
            "assigned_by":    pr.assigned_by,
            "revoked_at":     pr.revoked_at,
            "is_active":      pr.revoked_at is None,
        }
        for pr in sorted(roles, key=lambda r: r.assigned_at or datetime.min, reverse=True)
    ]


# PATCH /admin/players/{player_id}/password

@app.patch(
    "/admin/players/{player_id}/password",
    tags=["admin"],
    summary="Cambiar contraseña de un jugador",
)
def change_player_password(
    player_id:     int,
    body:          schemas.PasswordChangeRequest,
    db:            Session = Depends(get_db),
    current_admin: models.Player = Depends(require_roles(["admin"])),
):
    """
    Cambia la contraseña de cualquier jugador del sistema.

    La nueva contraseña se hashea con **bcrypt** antes de almacenarse.
    Nunca se guarda en texto plano.

    **cURL:**
    ```bash
    curl -X PATCH 'https://lsg.diinf.usach.cl/lsg-auth/admin/players/57/password' \\
      -H 'Authorization: Bearer <TOKEN_ADMIN>' \\
      -H 'Content-Type: application/json' \\
      -d '{"new_password": "nueva_contraseña_segura"}'
    ```

    **Respuesta exitosa (200):**
    ```json
    {
      "status": "ok",
      "player_id": 57,
      "message": "Contraseña actualizada correctamente."
    }
    ```

    **Roles disponibles:** "admin"
    """
    target = db.query(models.Player).filter(
        models.Player.id_players == player_id
    ).first()

    if not target:
        raise HTTPException(
            status_code=404,
            detail=f"Jugador {player_id} no encontrado.",
        )

    new_hash = hash_password(body.new_password)

    try:
        db.query(models.Player).filter(
            models.Player.id_players == player_id
        ).update({"password_hash": new_hash})
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error actualizando contraseña: {e}",
        )

    return {
        "status":    "ok",
        "player_id": player_id,
        "message":   "Contraseña actualizada correctamente.",
    }